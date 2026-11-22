---
type: Convention
title: "Escalation conventions"
description: "Incidents are declared with a severity, responders are paged by rotation."
x-kf-kind: domain
x-kf-owner: team:incident-management
x-kf-review: approved
x-kf-confidence: high
tags: [escalation, ownership]
sources:
  - id: design
    resource: https://github.com/cwijayasundara/semantic_layers_v2.0/blob/9297a1e3ba24ff3c98c776ef65ca383cfe1a3b57/docs/DESIGN.md
    title: e2ekg DESIGN.md
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
# Escalation conventions

An incident is opened with a severity (see the [severity scheme](../severity/scheme.md)) and responders. Pages go out through on-call rotations and appear as page events on the incident timeline.[^design] When a page reaches the owner of an application, that team is the first responder; the owner team is found through [team ownership](team-ownership.md).

[^design]: e2ekg design, source systems (incident records, rotations).
