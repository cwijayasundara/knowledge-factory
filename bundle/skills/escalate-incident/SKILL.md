---
name: "escalate-incident"
description: "Use when an incident needs paging, a responder or an owner team contacted."
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
# Escalate an incident

1. Confirm the incident's severity with [classify-incident-severity](../classify-incident-severity/SKILL.md).
2. Find the owner team of each affected application: see [team ownership](../../domain/ownership/team-ownership.md).
3. Follow the [escalation conventions](../../domain/ownership/escalation.md): page the rotation and add responders to the record.
4. Record each change of affected service as a new version of the incident record: [incident record versions](../../domain/policies/incident-record-versions.md).
