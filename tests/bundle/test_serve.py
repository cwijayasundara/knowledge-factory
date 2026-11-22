import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from kf.bundle.serve import current_concepts, kb_read, kb_search, snapshot

NOW = datetime(2026, 6, 1, tzinfo=UTC)


def put(b: Path, rel: str, front: str = "", body: str = "# Body\n") -> None:
    p = b / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"---\ntitle: T {rel}\ndescription: d\n{front}---\n{body}")


def test_empty_bundle(tmp_path):
    assert kb_search(tmp_path, "arr", now=NOW) == []
    assert "not found" in kb_read(tmp_path, "domain/x.md", now=NOW)


def test_stale_not_served_as_current(tmp_path):
    put(tmp_path, "domain/old.md", 'stale_after: "2026-01-01T00:00:00Z"\n')
    put(tmp_path, "domain/new.md", 'stale_after: "2027-01-01T00:00:00Z"\n')
    assert [c.path for c in current_concepts(tmp_path, now=NOW)] == ["domain/new.md"]
    assert "not current" in kb_read(tmp_path, "domain/old.md", now=NOW)


def test_draft_proposed_deprecated_not_current(tmp_path):
    put(tmp_path, "a.md", "status: draft\n")
    put(tmp_path, "b.md", "x-kf-review: proposed\n")
    put(tmp_path, "c.md", "status: deprecated\n")
    put(tmp_path, "d.md", "x-kf-review: approved\n")
    assert [c.path for c in current_concepts(tmp_path, now=NOW)] == ["d.md"]


def test_review_gate_in_review_rejected_and_absent(tmp_path):
    put(tmp_path, "ir.md", "x-kf-review: in_review\n", "# Body\nzebra\n")
    put(tmp_path, "rj.md", "x-kf-review: rejected\n", "# Body\nzebra\n")
    put(tmp_path, "none.md", "", "# Body\nzebra\n")
    put(tmp_path, "ok.md", "x-kf-review: approved\n", "# Body\nzebra\n")
    assert sorted(c.path for c in current_concepts(tmp_path, now=NOW)) == ["none.md", "ok.md"]
    assert sorted(h.path for h in kb_search(tmp_path, "zebra", now=NOW)) == ["none.md", "ok.md"]
    assert "not current" in kb_read(tmp_path, "ir.md", now=NOW)
    assert "not current" in kb_read(tmp_path, "rj.md", now=NOW)


@pytest.mark.parametrize("target", ["../x", "/../x", "a/../../x.md"])
def test_superseded_by_traversal_returns_message(tmp_path, target):
    put(tmp_path, "a.md", f"status: deprecated\nsuperseded_by: {target}\n")
    assert "invalid superseded_by" in kb_read(tmp_path, "a.md", now=NOW)


def test_superseded_by_absolute_path_returns_message(tmp_path):
    put(tmp_path, "a.md", "status: deprecated\nsuperseded_by: C:/etc/passwd\n")
    assert "invalid superseded_by" in kb_read(tmp_path, "a.md", now=NOW)


def test_superseded_target_malformed_does_not_raise(tmp_path):
    put(tmp_path, "a.md", "status: deprecated\nsuperseded_by: b.md\n")
    (tmp_path / "b.md").write_text("---\ntitle: [unclosed\n")
    assert "unreadable concept b.md" in kb_read(tmp_path, "a.md", now=NOW)
    (tmp_path / "c.md").write_text("---\nnever closed\n")
    assert "unreadable" in kb_read(tmp_path, "c.md", now=NOW)


def test_superseded_followed_and_cycle_terminates(tmp_path):
    put(tmp_path, "a.md", "status: deprecated\nsuperseded_by: /b.md\n")
    put(tmp_path, "b.md", "", "# Real answer\n")
    out = kb_read(tmp_path, "a.md", now=NOW)
    assert "superseded by b.md" in out and "Real answer" in out
    put(tmp_path, "x.md", "status: deprecated\nsuperseded_by: y.md\n")
    put(tmp_path, "y.md", "status: deprecated\nsuperseded_by: x.md\n")
    assert "cycle" in kb_read(tmp_path, "x.md", now=NOW)


def test_superseded_chain_limited_to_five_hops(tmp_path):
    for i in range(8):
        put(tmp_path, f"c{i}.md", f"status: deprecated\nsuperseded_by: c{i + 1}.md\n")
    put(tmp_path, "c8.md")
    assert "longer than 5 hops" in kb_read(tmp_path, "c0.md", now=NOW)
    assert "# Body" in kb_read(tmp_path, "c3.md", now=NOW)  # 5 hops


def test_deprecated_dangling_target(tmp_path):
    put(tmp_path, "a.md", "status: deprecated\nsuperseded_by: gone.md\n")
    assert "not found" in kb_read(tmp_path, "a.md", now=NOW)


@pytest.mark.parametrize("bad", ["../secrets", "/etc/passwd", "a/../../x.md"])
def test_path_traversal_rejected(tmp_path, bad):
    with pytest.raises(ValueError):
        kb_read(tmp_path, bad, now=NOW)


def test_human_reviewed_only_filters(tmp_path):
    put(tmp_path, "h.md", 'generated: {by: agent, at: "2026-01-01T00:00:00Z"}\nverified:\n  - {by: "human:a", at: "2026-02-01T00:00:00Z"}\n')
    put(tmp_path, "m.md")
    assert [c.path for c in current_concepts(tmp_path, now=NOW, human_reviewed_only=True)] == ["h.md"]
    assert len(current_concepts(tmp_path, now=NOW)) == 2


def test_search_index_first_then_grep(tmp_path):
    (tmp_path / "index.md").write_text("# Contents\n- [Gross](/domain/g.md): net revenue retention\n")
    put(tmp_path, "domain/g.md", "", "# G\nnothing\n")
    put(tmp_path, "domain/a.md", "", "# A\nretention retention retention\n")
    put(tmp_path, "domain/stale.md", 'stale_after: "2026-01-01T00:00:00Z"\n', "retention\n")
    hits = kb_search(tmp_path, "retention", now=NOW)
    assert [h.path for h in hits] == ["domain/g.md", "domain/a.md"]
    assert "retention" in hits[1].snippet
    assert len(kb_search(tmp_path, "retention", now=NOW, limit=1)) == 1


def git(b, *a):
    subprocess.run(["git", "-C", str(b), "-c", "user.name=t", "-c", "user.email=t@t", *a], check=True, capture_output=True)


def test_snapshot_is_frozen(tmp_path):
    b = tmp_path / "bundle"
    put(b, "domain/x.md", "", "original\n")
    git(b, "init", "-q")
    git(b, "add", ".")
    git(b, "commit", "-qm", "c1")
    sha = subprocess.run(["git", "-C", str(b), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    snap = snapshot(b, tmp_path / "snaps", commit=sha)
    assert snap == tmp_path / "snaps" / sha
    put(b, "domain/x.md", "", "edited\n")
    put(b, "domain/new.md")
    assert "original" in (snap / "domain/x.md").read_text()
    assert not (snap / "domain/new.md").exists()
    assert "original" in kb_read(snap, "domain/x.md", now=NOW)


def _repo(tmp_path):
    b = tmp_path / "work" / "bundle"
    put(b, "domain/x.md", "", "original\n")
    git(b, "init", "-q")
    git(b, "add", ".")
    git(b, "commit", "-qm", "c1")
    sha = subprocess.run(["git", "-C", str(b), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    return b, sha


def test_snapshot_bad_ref_and_traversal(tmp_path):
    b, _ = _repo(tmp_path)
    dest = tmp_path / "snaps"
    victim = tmp_path / "victim"
    victim.mkdir()
    (victim / "keep.txt").write_text("k")
    for bad in ["nope", "..", "../victim", "", "-x"]:
        with pytest.raises(ValueError):
            snapshot(b, dest, commit=bad)
    assert (victim / "keep.txt").exists() and (tmp_path / "work").exists()
    assert not dest.exists()  # nothing created for an invalid ref


def test_snapshot_ref_name_yields_sha_dir(tmp_path):
    b, sha = _repo(tmp_path)
    snap = snapshot(b, tmp_path / "snaps", commit="HEAD")
    assert snap.name == sha
    assert (snap / "domain/x.md").exists()
    assert snapshot(b, tmp_path / "snaps", commit=sha) == snap  # re-snapshot replaces cleanly


def test_snapshot_failure_leaves_no_partial_dir(tmp_path):
    b, sha = _repo(tmp_path)
    dest = tmp_path / "snaps"
    snap = snapshot(b, dest, commit=sha)
    with pytest.raises(ValueError):
        snapshot(b, dest, commit="deadbeef" * 5)
    assert [p.name for p in dest.iterdir()] == [sha]  # no partial or temp dirs; good snapshot untouched
    assert (snap / "domain/x.md").exists()
