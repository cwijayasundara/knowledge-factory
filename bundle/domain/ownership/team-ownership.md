---
type: Convention
title: "Team ownership"
description: "Every application in the catalog has an owner team."
x-kf-kind: domain
x-kf-owner: team:platform-observability
x-kf-review: approved
x-kf-confidence: high
tags: [ownership, team]
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
# Team ownership

Every application in the software catalog records an owner team, a tier and its regions.[^architecture] Teams have a stable slug derived from the owner name, for example "Team Bedrock" becomes team-bedrock.[^architecture] Ownership questions, such as which incidents touched applications owned by a team, are answered from the owner team recorded in the catalog.[^design]

See [escalation conventions](escalation.md).

[^architecture]: e2ekg architecture, scenario model and URI scheme.
[^design]: e2ekg design, competency questions.
