---
type: Glossary
title: "Fault kinds"
description: "The closed set of fault kinds, plus none when nothing is at fault."
x-kf-kind: domain
x-kf-owner: team:platform-observability
x-kf-review: approved
x-kf-confidence: high
tags: [fault-kind, glossary]
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
# Fault kinds

- capacity reduction: serving capacity was cut, for example an autoscaler minimum lowered.
- bad deploy: a deployment introduced a defect.
- cache eviction storm: mass cache eviction pushed load onto backends.
- DB hot partition: a database partition became a hotspot.
- certificate expiry: an expired certificate broke TLS connections.
- retry storm: synchronized client retries amplified load.
- none: nothing is at fault; there is no root cause.[^architecture]

[^architecture]: e2ekg architecture, scenario model fault kinds.
