---
type: Definition
title: "Severity scheme"
description: "The closed set of incident severities and their ordering."
x-kf-kind: domain
x-kf-owner: team:incident-management
x-kf-review: approved
x-kf-confidence: high
tags: [severity, priority]
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
# Severity scheme

Incident severity is a closed value: classifiers pick one concept from the scheme and never invent a new string.[^architecture]

| Severity | Meaning |
|---|---|
| [SEV1](sev1.md) | Critical, widespread member impact |
| [SEV2](sev2.md) | Major impact on a key experience |
| [SEV3](sev3.md) | Minor or contained impact |

Priority follows severity: a lower number is higher priority, so SEV1 outranks SEV2, which outranks SEV3. Severity is recorded on the incident record; every new version of the record carries its own time, so the severity as known at a given moment can be queried.[^architecture]

[^architecture]: e2ekg architecture, closed SKOS schemes and incident record versions.
