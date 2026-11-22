---
name: "classify-incident-severity"
description: "Use when asked to label an incident SEV1, SEV2 or SEV3 or to order incidents by priority."
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
# Classify incident severity

1. Read the impact statement on the incident record.
2. Pick exactly one severity from the [severity scheme](../../domain/severity/scheme.md): [SEV1](../../domain/severity/sev1.md) for critical widespread impact, [SEV2](../../domain/severity/sev2.md) for major impact on a key experience, [SEV3](../../domain/severity/sev3.md) for minor or contained impact.
3. Normalize surface forms such as "SEV 2" or "SEV-2" to the closed value.
4. Order incidents by severity, lowest number first.
