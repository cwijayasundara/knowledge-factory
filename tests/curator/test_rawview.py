"""kf raw-view builds the curator's as-of raw sources; kf curate accepts only such a view and never
held-out data (spec 5.4, 9b)."""

import json
import subprocess
from pathlib import Path

import pytest

from kf.cli import main
from kf.curator import rawview
from kf.curator.guard import WriteGuard
from kf.curator.tools import CuratorError, CuratorTools, check_raw_dir


def data_root(tmp_path, name="data_curation"):
    root = tmp_path / name / "seed-11"
    for s in ("hero", "v-control"):
        (root / "raw" / s).mkdir(parents=True)
        (root / "raw" / s / "logs.txt").write_text("before\nafter\n")
        h = root / "graph" / s / "as_of"
        h.mkdir(parents=True)
        (h / "harvest.json").write_text(json.dumps({"as_of": "2026-06-01T12:00:00+00:00"}))
    (root / "raw" / "_answers").mkdir()
    (root / "raw" / "_answers" / "hero.json").write_text("{}")
    return root


def fake_builder(calls):
    def build(raw, proc, as_of, dest):
        calls.append((raw, proc, as_of, dest))
        dest.mkdir(parents=True)
        (dest / "logs.txt").write_text("before\n")
    return build


def test_build_view_writes_each_scenario_and_the_marker(tmp_path):
    calls = []
    out = rawview.build_view(data_root(tmp_path), tmp_path / "view", builder=fake_builder(calls))
    assert sorted(p.name for p in out.iterdir()) == [rawview.MARKER, "hero", "v-control"]
    assert [c[0].name for c in calls] == ["hero", "v-control"]  # never the answer key
    assert all(c[1].parent.name == "processed" for c in calls)
    meta = json.loads((out / rawview.MARKER).read_text())
    assert meta["as_of"]["hero"] == "2026-06-01T12:00:00+00:00" and rawview.is_raw_view(out)
    check_raw_dir(out)


def test_build_view_refuses_held_out_data(tmp_path):
    with pytest.raises(rawview.RawViewError, match="held-out"):
        rawview.build_view(data_root(tmp_path, "data_heldout"), tmp_path / "view", builder=fake_builder([]))


def test_build_view_needs_the_as_of_harvest(tmp_path):
    root = data_root(tmp_path)
    (root / "graph" / "hero" / "as_of" / "harvest.json").unlink()
    with pytest.raises(rawview.RawViewError, match="harvest"):
        rawview.build_view(root, tmp_path / "view", builder=fake_builder([]))


def test_e2ekg_builder_runs_ensure_raw_view_in_e2ekg(tmp_path, monkeypatch):
    e2ekg = tmp_path / "e2ekg"
    e2ekg.mkdir()
    (e2ekg / "pyproject.toml").write_text("")
    seen = {}

    def run(cmd, **kw):
        seen.update(cmd=cmd, **kw)
        return subprocess.CompletedProcess(cmd, 0, "", "")
    monkeypatch.setattr(subprocess, "run", run)
    from datetime import datetime

    rawview.e2ekg_builder(e2ekg)(Path("/r"), Path("/p"), datetime.fromisoformat("2026-06-01T12:00:00+00:00"),
                                 Path("/d"))
    assert seen["cmd"][:4] == ["uv", "run", "python", "-c"] and "ensure_raw_view" in seen["cmd"][4]
    assert seen["cmd"][5:] == ["/r", "/p", "2026-06-01T12:00:00+00:00", "/d"] and seen["cwd"] == e2ekg
    with pytest.raises(rawview.RawViewError, match="apply.sh"):
        rawview.e2ekg_builder(tmp_path / "none")(Path("/r"), Path("/p"), datetime.now(), Path("/d"))


def test_kf_raw_view_cli(tmp_path, monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(rawview, "e2ekg_builder", lambda d: fake_builder(calls))
    root = data_root(tmp_path)
    assert main(["raw-view", "--data-root", str(root), "--out", str(tmp_path / "v"), "--scenarios", "hero"]) == 0
    assert [c[0].name for c in calls] == ["hero"] and rawview.is_raw_view(tmp_path / "v")
    assert main(["raw-view", "--data-root", str(data_root(tmp_path, "data_heldout")), "--out",
                 str(tmp_path / "v2")]) == 2
    assert "held-out" in capsys.readouterr().err


def test_curator_refuses_a_raw_dir_that_is_not_an_as_of_view(tmp_path):
    d = tmp_path / "raw"
    (d / "wiki").mkdir(parents=True)
    with pytest.raises(CuratorError, match="kf raw-view"):
        check_raw_dir(d)
    rawview.mark(d, {})
    check_raw_dir(d)


def test_curator_refuses_held_out_raw_dirs(tmp_path):
    d = tmp_path / "data_heldout" / "seed-21" / "view"
    d.mkdir(parents=True)
    rawview.mark(d, {})
    with pytest.raises(CuratorError, match="held-out"):
        check_raw_dir(d)


@pytest.mark.parametrize("kind", ["under-heldout-root", "heldout-eval-run"])
def test_curator_refuses_held_out_trails(repo, queue, raw_dir, tmp_path, kind):
    if kind == "under-heldout-root":
        trails = tmp_path / "data_heldout" / "seed-21" / "evals"
        trails.mkdir(parents=True)
    else:
        trails = tmp_path / "state" / "evals" / "heldout-x" / "seed-21"
        trails.mkdir(parents=True)
        (trails / "kf_run.json").write_text(json.dumps({"heldout": True}))
    with pytest.raises(CuratorError, match="held-out"):
        CuratorTools(repo, "kf/r1", queue, raw_dir, WriteGuard.default(), state_dir=tmp_path / "st",
                     trails_dir=trails)


def test_curator_accepts_curation_trails(repo, queue, raw_dir, tmp_path):
    trails = tmp_path / "state" / "evals" / "curation-x" / "seed-11"
    trails.mkdir(parents=True)
    (trails / "kf_run.json").write_text(json.dumps({"heldout": False}))
    CuratorTools(repo, "kf/r1", queue, raw_dir, WriteGuard.default(), state_dir=tmp_path / "st", trails_dir=trails)
