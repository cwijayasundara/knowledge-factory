---
type: Glossary
title: "Declared signal types"
description: "Signal types that are declared events, not detections."
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
# Declared signal types

- alert: an alert firing.
- incident: an incident opened.
- deployment: a deployment or client release.
- config change: a dynamic property change.
- experiment: an experiment allocation change.
- autoscaling: an autoscaling event.
- commit: a source control commit.[^architecture]

Changes, alerts and incidents are declared events and carry severity 1.[^architecture]

[^architecture]: e2ekg architecture, signals and onsets.
