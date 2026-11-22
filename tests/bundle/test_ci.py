import shutil
from pathlib import Path

import pytest

from kf.bundle.ci import VALIDATOR, check_links, lint_bundle, no_curator_verified, run_ci, scan_pii
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
def test_run_ci_accepts_untyped_skill_but_not_other_untyped_files(tmp_path):
    skill = concept("name: s\ndescription: d\n")
    ok = make(tmp_path, "ok", {"orders.md": concept(GOOD), "skills/s/SKILL.md": skill})
    assert run_ci(ok).ok
    bad = make(tmp_path, "bad", {"orders.md": concept(GOOD), "notes.md": "no frontmatter\n"})
    assert not run_ci(bad).ok


CUR = "generated: {by: kf-curator/0.1, at: 2026-11-22T02:00:00Z}\n"
HUM = "generated: {by: human:ana, at: 2026-11-22T02:00:00Z}\n"
VER = "verified:\n- {by: human:ana, at: 2026-11-23T00:00:00Z}\n"


def test_ci_rejects_curator_added_verified(tmp_path):
    base = make(tmp_path, "base", {"orders.md": concept(GOOD + CUR)})
    head = make(tmp_path, "head", {"orders.md": concept(GOOD + CUR + VER)})
    assert [i.check for i in no_curator_verified(head, base)] == ["no_curator_verified"]
    assert no_curator_verified(base, base) == []


def test_ci_rejects_non_human_verified_on_human_concept(tmp_path):
    base = make(tmp_path, "base", {"orders.md": concept(GOOD + HUM)})
    bot = make(tmp_path, "head", {"orders.md": concept(GOOD + HUM + "verified:\n- {by: team:bot, at: 2026-11-23T00:00:00Z}\n")})
    ok = make(tmp_path, "ok", {"orders.md": concept(GOOD + HUM + "verified:\n- {by: human:bo, at: 2026-11-23T00:00:00Z}\n")})
    assert no_curator_verified(bot, base)
    assert no_curator_verified(ok, base) == []


def test_ci_rejects_generated_by_swap(tmp_path):
    base = make(tmp_path, "base", {"orders.md": concept(GOOD + CUR)})
    swap = make(tmp_path, "swap", {"orders.md": concept(GOOD + HUM + VER)})
    issues = no_curator_verified(swap, base)
    assert issues and any("generated.by changed" in i.message for i in issues)
    only = make(tmp_path, "only", {"orders.md": concept(GOOD + HUM)})
    assert any("generated.by changed" in i.message for i in no_curator_verified(only, base))


MALFORMED = {
    "unterminated.md": "---\ntitle: x\n# no closing fence\n",
    "badyaml.md": "---\ntitle: [unclosed\n---\nbody\n",
    "notmap.md": "---\n- a\n- b\n---\nbody\n",
}


def test_malformed_frontmatter_becomes_issues_in_every_check(tmp_path):
    base = make(tmp_path, "base", {})
    b = make(tmp_path, "b", MALFORMED)
    for check, issues in (
        ("profile", lint_bundle(b, PROFILE)),
        ("links", check_links(b)),
        ("no_curator_verified", no_curator_verified(b, base)),
    ):
        assert {i.path for i in issues if i.check == check} == set(MALFORMED), check
    assert not run_ci(b, base=base).ok


@needs_validator
def test_run_ci_ok_with_human_verification(tmp_path):
    base = make(tmp_path, "base", {"orders.md": concept(GOOD + HUM)})
    ok = make(tmp_path, "ok", {"orders.md": concept(GOOD + HUM + VER)})
    assert run_ci(ok, base=base).ok
    assert not run_ci(make(tmp_path, "sw", {"orders.md": concept(GOOD + HUM + VER)}), base=make(tmp_path, "cb", {"orders.md": concept(GOOD + CUR)})).ok


@needs_validator
def test_cli_ci_exit_codes(tmp_path):
    from kf.cli import main

    good = make(tmp_path, "good", {"orders.md": concept(GOOD)})
    bad = make(tmp_path, "bad", {"orders.md": concept(GOOD, "mail ana@example.com\n")})
    assert main(["ci", str(good)]) == 0
    assert main(["ci", str(bad)]) == 1
    broken = make(tmp_path, "broken", {"x.md": MALFORMED["badyaml.md"]})
    assert main(["ci", str(broken)]) == 1
