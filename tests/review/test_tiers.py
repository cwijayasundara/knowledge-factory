from pathlib import Path

import pytest

from kf.bundle.profile import Profile
from kf.review.tiers import ChangedFile, Tier, classify

P = Profile(okf_version="0.3", enums={}, kinds={})


def cf(path, change="modified", before=None, after=None):
    return ChangedFile(path, change, before, after)


C = "domain/metrics/arr.md"


@pytest.mark.parametrize("path", ["index.md", "log.md"])
def test_index_and_log_are_t0(path):
    assert classify([cf(path)], profile=P) == Tier.T0


def test_empty_is_t0():
    assert classify([], profile=P) == Tier.T0


def test_usage_refresh_with_same_body_is_t0():
    before = {"body": "b", "x-kf-usage": {"reads": 1}, "status": "stable"}
    after = {"body": "b", "x-kf-usage": {"reads": 9}, "status": "stable"}
    assert classify([cf(C, before=before, after=after)], profile=P) == Tier.T0


def test_formatting_same_body_is_t0():
    before = {"body": "b", "generated": "x"}
    after = {"body": "b", "generated": "y"}
    assert classify([cf(C, before=before, after=after)], profile=P) == Tier.T0


def test_new_concept_with_source_is_t1():
    after = {"body": "b", "sources": ["raw/a.md"]}
    assert classify([cf(C, "added", None, after)], profile=P) == Tier.T1


def test_new_concept_without_sources_is_t2():
    assert classify([cf(C, "added", None, {"body": "b", "sources": []})], profile=P) == Tier.T2
    assert classify([cf(C, "added", None, {"body": "b"})], profile=P) == Tier.T2


def test_data_access_update_is_t1():
    p = "data_access/tables/orders.md"
    before, after = {"body": "a"}, {"body": "b"}
    assert classify([cf(p, before=before, after=after)], profile=P) == Tier.T1


def test_skill_edit_is_t1():
    p = "skills/triage/SKILL.md"
    assert classify([cf(p, before={"body": "a"}, after={"body": "b"})], profile=P) == Tier.T1


def test_stable_definition_edit_is_t2():
    before = {"body": "a", "status": "stable"}
    after = {"body": "b", "status": "stable"}
    assert classify([cf(C, before=before, after=after)], profile=P) == Tier.T2


def test_deprecation_is_t2():
    before = {"body": "a", "status": "stable"}
    after = {"body": "a", "status": "deprecated", "superseded_by": "x"}
    assert classify([cf(C, "deprecated", before, after)], profile=P) == Tier.T2


def test_deprecation_of_draft_is_t2():
    before = {"body": "a", "status": "draft"}
    assert classify([cf(C, "deprecated", before, before)], profile=P) == Tier.T2


def test_low_confidence_is_t2():
    after = {"body": "b", "sources": ["s"], "x-kf-confidence": "low"}
    assert classify([cf(C, "added", None, after)], profile=P) == Tier.T2


def test_editing_human_reviewed_concept_is_t2():
    before = {"body": "a", "status": "draft", "verified": {"by": "human:a"}}
    after = {"body": "b", "status": "draft"}
    assert classify([cf(C, before=before, after=after)], profile=P) == Tier.T2
    before = {"body": "a", "x-kf-review": "approved"}
    assert classify([cf(C, before=before, after={"body": "b"})], profile=P) == Tier.T2


@pytest.mark.parametrize(
    "path",
    ["kf-profile.yaml", "AGENTS.md", "CODEOWNERS", "computations/x.md", "src/kf/review/tiers.py"],
)
def test_protected_paths_are_t3(path):
    assert classify([cf(path)], profile=P) == Tier.T3


def test_removed_is_t3():
    assert classify([cf(C, "removed", {"body": "a"}, None)], profile=P) == Tier.T3


def test_mixed_takes_max():
    files = [cf("index.md"), cf(C, "added", None, {"body": "b", "sources": ["s"]}), cf("log.md")]
    assert classify(files, profile=P) == Tier.T1
    files.append(cf("kf-profile.yaml"))
    assert classify(files, profile=P) == Tier.T3


def test_tier_is_ordered():
    assert Tier.T0 < Tier.T1 < Tier.T2 < Tier.T3
