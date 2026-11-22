"""kf curate refuses a flag queue that belongs to held-out data (spec 9b)."""

import json

import pytest

from kf import cli
from kf.curator import agent


@pytest.fixture
def called(monkeypatch):
    calls = []
    monkeypatch.setattr(agent, "run_curation", lambda **kw: calls.append(kw))
    return calls


def heldout_run_db(tmp_path):
    run = tmp_path / "state" / "evals" / "heldout-X" / "seed-21"
    (run / "state").mkdir(parents=True)
    (run / "kf_run.json").write_text(json.dumps({"heldout": True}))
    return run / "state" / "flags.db"


@pytest.mark.parametrize("where", ["sink", "root", "running"])
def test_curate_refuses_a_heldout_flag_db(tmp_path, called, capsys, where):
    db = {"sink": lambda: heldout_run_db(tmp_path),
          "root": lambda: tmp_path / "data_heldout" / "seed-21" / "flags.db",
          "running": lambda: tmp_path / "state" / "evals" / "heldout-Y" / "seed-21" / "state" / "flags.db"}[where]()
    rc = cli.main(["curate", "--raw-dir", str(tmp_path / "view"), "--db", str(db), "--repo", str(tmp_path)])
    assert rc == 2 and "held-out" in capsys.readouterr().err and called == []
