---
type: Policy
title: "Policy: incident record versions"
description: "Incident records keep every version; the latest is current."
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
# Policy: incident record versions

Each version of an incident record keeps its own time, so the incident as known at a moment can be queried. The current affected service is the latest one filed; earlier values are kept as previously affected.[^architecture]

See the [severity scheme](../severity/scheme.md) for the severity field.

[^architecture]: e2ekg architecture, identity correction history.
