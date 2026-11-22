---
type: Glossary
title: "Change kinds"
description: "The six closed kinds of change a system records."
x-kf-kind: domain
x-kf-owner: team:platform-observability
x-kf-review: approved
x-kf-confidence: high
tags: [change-kind, glossary]
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
# Change kinds

A change is anything that altered the running system. There are six kinds, and the value is always one of them.[^architecture]

- [Deployment](change-kind-deployment.md): A server-side version rollout.
- [Config change](change-kind-config-change.md): A dynamic property change.
- [Scaling](change-kind-scaling.md): An autoscaling capacity change.
- [Experiment allocation](change-kind-experiment-allocation.md): An A/B allocation change.
- [Commit](change-kind-commit.md): A source control commit.
- [Client release](change-kind-client-release.md): A device client release.

Changes are identified by the opaque id of the system that recorded them (a deploy execution id, a property change id, a scaling activity id, an allocation id or a git sha).[^architecture]

[^architecture]: e2ekg architecture, change kinds and change identity.
