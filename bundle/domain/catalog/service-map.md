---
type: Mapping
title: Service map
description: The software catalog records, per application, the other apps it calls,
  over which protocol, plus aliases, owner team, tier, regions and kind.
x-kf-kind: domain
x-kf-owner: team:platform-observability
x-kf-risk: 0
x-kf-confidence: medium
tags:
- topology
- catalog
- dependencies
sources:
- id: apps-yaml
  resource: raw:v-control/catalog/apps.yaml
  title: Software catalog (apps.yaml)
- id: v-control/catalog/apps.yaml
  resource: raw:v-control/catalog/apps.yaml
generated:
  by: kf-curator/0.1.0
  at: '2026-11-23T05:40:41Z'
x-kf-review: proposed
x-kf-flags:
- 1
---
# Service map

Each application in the software catalog declares its relationships to other applications: a dependency entry names the target `app` and the `protocol` of the call (for example, `edge-gateway` lists `homepage-graphql` over `http`, `playback-api` over `http`, and `search-svc` over `grpc`).[^apps-yaml]

Alongside dependencies, each catalog entry records:[^apps-yaml]

- `id` and `aliases` (alternate names, e.g. `edge-gateway` is also `EdgeGateway` and `zuul-edge`);
- `owner_team` (e.g. `Team Edge`);
- `tier` and `regions`;
- `kind` (e.g. `edge`, `service`, `client`, `cache`, `datastore`);
- `dependencies: []` for leaves such as caches and datastores.

Use the catalog to classify whether an alert on one app is plausibly related to an alert on another: follow the recorded relationships rather than inferring relatedness from names or timing alone. Alias lists let you match alert URIs that use non-canonical app names to catalog ids.

See [team ownership](../ownership/team-ownership.md).

[^apps-yaml]: v-control raw source `catalog/apps.yaml`.
