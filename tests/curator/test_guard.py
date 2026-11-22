import os

import pytest

from kf.curator.guard import WriteDenied, WriteGuard


def test_guard_blocks_raw_and_answers():
    for p in ["raw/slack/x.json", "bundle/computations/a.md", "kf-profile.yaml", "../x", "data/raw/_answers/hero.json"]:
        with pytest.raises(WriteDenied):
            WriteGuard.default().check(p)


@pytest.mark.parametrize("p", [
    "AGENTS.md", "CODEOWNERS", "src/kf/review/tiers.py", "bundle/curator/prompt.md", "/etc/passwd",
    "bundle/../../x", "data/raw/x.json", "x/_answers",
])
def test_guard_blocks_protected_paths(p):
    with pytest.raises(WriteDenied):
        WriteGuard.default().check(p)


def test_guard_allows_bundle_concepts():
    WriteGuard.default().check("bundle/domain/refund.md")
    WriteGuard.default().check("bundle/skills/report/SKILL.md")


def test_guard_blocks_symlink_out_of_root(tmp_path):
    root, outside = tmp_path / "root", tmp_path / "outside"
    (root / "bundle").mkdir(parents=True)
    outside.mkdir()
    os.symlink(outside, root / "bundle" / "link")
    guard = WriteGuard.default(root=root)
    guard.check("bundle/ok.md")
    with pytest.raises(WriteDenied):
        guard.check("bundle/link/x.md")
