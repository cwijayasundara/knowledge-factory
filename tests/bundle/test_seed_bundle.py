"""The served seed bundle holds company knowledge only: nothing that describes the eval harness
(metrics, traps, control scenarios, scorecards), so the graph_kb arm learns nothing about its own test
(spec 9b, anti-goal A3). Eval-harness definitions live in docs/eval-glossary/, which is never served."""

import os
import re
from pathlib import Path

import pytest

from kf.bundle.ci import VALIDATOR, run_ci

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "bundle"
EVAL_WORDS = re.compile(
    r"\btop-?[13]\b|\btrap|scorecard|false positive|control scenario|answer[- ]key|held-out|red herring"
    r"|evidence precision|stochastic arm|\bscored\b",
    re.IGNORECASE,
)


def test_seed_bundle_describes_no_eval_harness():
    hits = []
    for f in sorted(BUNDLE.rglob("*")):
        if f.is_file():
            for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                if EVAL_WORDS.search(line):
                    hits.append(f"{f.relative_to(ROOT)}:{n}: {line.strip()[:80]}")
    assert hits == []


def test_eval_glossary_is_outside_the_bundle():
    assert (ROOT / "docs" / "eval-glossary" / "domain" / "metrics" / "top1.md").is_file()
    assert not (BUNDLE / "domain" / "metrics").exists()
    assert not (BUNDLE / "skills" / "read-rca-scorecard").exists()


def test_seed_bundle_passes_ci():
    if not VALIDATOR.is_file():
        if os.environ.get("CI"):
            pytest.fail(f"OKF validator missing at {VALIDATOR} (CI is set)")
        pytest.skip(f"OKF validator missing at {VALIDATOR}")
    report = run_ci(BUNDLE)
    assert report.ok, [(i.check, i.path, i.message) for i in report.issues]
