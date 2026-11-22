---
type: Definition
title: "RCA metric scorecard"
description: "How RCA quality metrics are read together."
x-kf-kind: domain
x-kf-owner: team:rca-evaluation
x-kf-review: approved
x-kf-confidence: high
tags: [metric, rca, slo]
sources:
  - id: architecture
    resource: https://github.com/cwijayasundara/semantic_layers_v2.0/blob/9297a1e3ba24ff3c98c776ef65ca383cfe1a3b57/docs/ARCHITECTURE.md
    title: e2ekg ARCHITECTURE.md
  - id: design
    resource: https://github.com/cwijayasundara/semantic_layers_v2.0/blob/9297a1e3ba24ff3c98c776ef65ca383cfe1a3b57/docs/DESIGN.md
    title: e2ekg DESIGN.md
generated:
  by: seed/1
  at: '2026-11-22T00:00:00Z'
verified:
  - by: human:seed-owner
    at: '2026-11-22T00:00:00Z'
---
# RCA metric scorecard

Root cause analysis is scored against a held-out answer key.[^design] The metrics are [top1](top1.md), [top3](top3.md), [trap rate](trap.md), [evidence precision](evidence-precision.md) and [control false positive](control-false-positive.md).

Evidence checking is transitive: a cited item counts when it, or anything it cites or derives from, reaches key evidence.[^architecture] Accuracy goes up when top1 rises; safety is worse when trap rate or control false positives rise.

[^design]: e2ekg design, evals.
[^architecture]: e2ekg architecture, evaluation harness.
