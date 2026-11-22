---
type: Policy
title: "Policy: repeat stochastic runs"
description: "One run per stochastic arm proves nothing; use repeated runs."
x-kf-kind: domain
x-kf-owner: team:rca-evaluation
x-kf-review: approved
x-kf-confidence: high
tags: [policy, rca, slo]
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
# Policy: repeat stochastic runs

A single run of a stochastic arm is not enough to rank arms or to draw a conclusion. Repeat each arm and scenario at least three times before comparing results.[^architecture]

[^architecture]: e2ekg architecture, evaluation harness: "one run per stochastic arm proves nothing".
