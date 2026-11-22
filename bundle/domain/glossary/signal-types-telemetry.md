---
type: Glossary
title: "Telemetry signal types"
description: "Signal types detected from telemetry."
x-kf-kind: domain
x-kf-owner: team:platform-observability
x-kf-review: approved
x-kf-confidence: high
tags: [signal-type, glossary]
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
# Telemetry signal types

- log error: an error log pattern spike.
- metric anomaly: an anomaly on a metric series.
- slow trace: elevated latency on a trace edge.
- failed trace: elevated errors on a trace edge.
- end-to-end bottleneck: the critical-path bottleneck of an end-to-end request.
- error pattern: a recurring error pattern, chronic rather than a spike.[^architecture]

A detected signal has a severity score m / (m + m_fire), so a signal at its detector threshold scores 0.5.[^architecture]

[^architecture]: e2ekg architecture, signals and onsets and the signal type scheme.
