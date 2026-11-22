---
type: Policy
title: "Policy: confirming a root cause"
description: "A correct top-1 chain is confirmed only after a person approves it."
x-kf-kind: domain
x-kf-owner: team:incident-management
x-kf-review: approved
x-kf-confidence: high
tags: [policy, incident]
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
# Policy: confirming a root cause

A causal chain is confirmed when it is top-1 correct and a person approved it. Correct is not enough: the approval stands in for the ground truth a real incident would not have. Withdrawing an approval withdraws the learned pattern built from it.[^architecture]

[^architecture]: e2ekg architecture, flywheel.
