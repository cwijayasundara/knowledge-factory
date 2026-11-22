---
name: "read-rca-scorecard"
description: "Use when reporting or comparing RCA evaluation results."
x-kf-kind: skill_card
x-kf-owner: team:incident-management
x-kf-review: approved
x-kf-risk: 0
sources:
  - id: architecture
    resource: https://github.com/cwijayasundara/semantic_layers_v2.0/blob/9297a1e3ba24ff3c98c776ef65ca383cfe1a3b57/docs/ARCHITECTURE.md
    title: e2ekg ARCHITECTURE.md
generated:
  by: seed/1
  at: '2026-11-22T00:00:00Z'
verified:
  - by: human:seed-owner
    at: '2026-11-22T00:00:00Z'
---
# Read an RCA scorecard

1. Report [top1](../../domain/metrics/top1.md) and [top3](../../domain/metrics/top3.md) per arm.
2. Report the safety metrics next to them: [trap rate](../../domain/metrics/trap.md) and [control false positive](../../domain/metrics/control-false-positive.md). A rise in either is a regression even when top1 improves.
3. Add [evidence precision](../../domain/metrics/evidence-precision.md) for the top hypothesis.
4. Only compare arms over repeated runs: [repeat runs](../../domain/policies/repeat-runs.md).
