import shutil
from pathlib import Path

import pytest

from kf.bundle.ci import VALIDATOR, lint_bundle, run_ci, scan_pii
from kf.bundle.profile import Profile

ROOT = Path(__file__).resolve().parents[2]
PROFILE = Profile.load(ROOT / "kf-profile.yaml")

INDEX = '---\nokf_version: "0.3"\ntitle: B\ndescription: d\n---\n\n# Contents\n'


def concept(front: str, body: str = "# Body\n") -> str:
    return f"---\n{front}---\n{body}"


GOOD = (
    "type: Table\ntitle: Orders\ndescription: Orders table.\nx-kf-kind: data_access\nx-kf-owner: team:data\n"
    "x-kf-review: approved\nx-kf-risk: 1\nx-kf-confidence: high\n"
)


def make(tmp_path: Path, name: str, files: dict[str, str]) -> Path:
    b = tmp_path / name
    b.mkdir()
    (b / "index.md").write_text(INDEX)
    for rel, text in files.items():
        (b / rel).parent.mkdir(parents=True, exist_ok=True)
        (b / rel).write_text(text)
    return b


def test_profile_loads_kinds_and_ttl():
    assert set(PROFILE.kinds) == {"domain", "data_access", "skill_card"}
    assert all(k.stale_after_days > 0 for k in PROFILE.kinds.values())


def test_lint_passes_good_concept(tmp_path):
    b = make(tmp_path, "b", {"orders.md": concept(GOOD)})
    assert lint_bundle(b, PROFILE) == []


def test_ci_flags_missing_required_profile_key(tmp_path):
    b = make(tmp_path, "b", {"orders.md": concept(GOOD.replace("x-kf-owner: team:data\n", ""))})
    issues = lint_bundle(b, PROFILE)
    assert [i.check for i in issues] == ["profile"] and "x-kf-owner" in issues[0].message


def test_lint_rejects_bad_enum_and_kind(tmp_path):
    b = make(tmp_path, "b", {
        "a.md": concept(GOOD.replace("risk: 1", "risk: 7")),
        "c.md": concept(GOOD.replace("approved", "maybe")),
        "d.md": concept(GOOD.replace("data_access", "other")),
    })
    assert {i.path for i in lint_bundle(b, PROFILE)} == {"a.md", "c.md", "d.md"}


def test_lint_rejects_typed_skill(tmp_path):
    b = make(tmp_path, "b", {"skills/s/SKILL.md": concept("name: s\ndescription: d\ntype: Skill\n")})
    assert len(lint_bundle(b, PROFILE)) == 1


def test_ci_pii_scan_flags_email(tmp_path):
    b = make(tmp_path, "b", {"orders.md": concept(GOOD, "Contact ana@example.com\n")})
    assert [i.check for i in scan_pii(b)] == ["pii"]


def test_ci_pii_scan_flags_phone_and_key(tmp_path):
    b = make(tmp_path, "b", {"a.md": concept(GOOD, "call 415-555-0134\n"), "c.md": concept(GOOD, "sk-abcdefghijklmnopqrstuvwx\n")})
    assert {i.path for i in scan_pii(b)} == {"a.md", "c.md"}


needs_validator = pytest.mark.skipif(not VALIDATOR.is_file(), reason="run scripts/fetch_okf.sh")


@needs_validator
def test_run_ci_ok_on_clean_bundle(tmp_path):
    b = make(tmp_path, "b", {"orders.md": concept(GOOD)})
    assert run_ci(b).ok


@needs_validator
def test_run_ci_reports_validator_and_broken_link(tmp_path):
    b = make(tmp_path, "b", {"orders.md": concept(GOOD, "see [x](missing.md)\n")})
    r = run_ci(b)
    assert not r.ok and "links" in {i.check for i in r.issues}


@needs_validator
def test_ci_rejects_curator_added_verified(tmp_path):
    gen = "generated: {by: kf-curator/0.1, at: 2026-11-22T02:00:00Z}\n"
    base = make(tmp_path, "base", {"orders.md": concept(GOOD + gen)})
    head = make(tmp_path, "head", {"orders.md": concept(
        GOOD + gen + "verified:\n- {by: human:ana, at: 2026-11-23T00:00:00Z}\n")})
    r = run_ci(head, base=base)
    assert "no_curator_verified" in {i.check for i in r.issues}
    assert run_ci(base, base=base).ok


@needs_validator
def test_ci_rejects_non_human_verified_on_human_concept(tmp_path):
    gen = "generated: {by: human:ana, at: 2026-11-22T02:00:00Z}\n"
    base = make(tmp_path, "base", {"orders.md": concept(GOOD + gen)})
    head = make(tmp_path, "head", {"orders.md": concept(
        GOOD + gen + "verified:\n- {by: team:bot, at: 2026-11-23T00:00:00Z}\n")})
    assert "no_curator_verified" in {i.check for i in run_ci(head, base=base).issues}
    ok = make(tmp_path, "ok", {"orders.md": concept(
        GOOD + gen + "verified:\n- {by: human:bo, at: 2026-11-23T00:00:00Z}\n")})
    assert run_ci(ok, base=base).ok


@needs_validator
def test_cli_ci_exit_codes(tmp_path):
    from kf.cli import main

    good = make(tmp_path, "good", {"orders.md": concept(GOOD)})
    bad = make(tmp_path, "bad", {"orders.md": concept(GOOD, "mail ana@example.com\n")})
    assert main(["ci", str(good)]) == 0
    assert main(["ci", str(bad)]) == 1
