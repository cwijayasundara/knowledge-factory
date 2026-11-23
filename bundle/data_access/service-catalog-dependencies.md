---
type: Mapping
title: Service catalog dependency map
description: What the application catalog records per app — aliases, owner team, tier,
  and dependencies — and where the catalog file lives.
x-kf-kind: data_access
x-kf-owner: team:platform-observability
x-kf-review: proposed
x-kf-risk: 0
x-kf-confidence: high
generated:
  by: kf-curator/0.1.0
  at: '2026-11-22T19:22:26Z'
x-kf-flags:
- 1
sources:
- id: catalog-apps
  resource: raw:v-control/catalog/apps.yaml
  title: Raw application catalog (apps.yaml)
- id: v-control/catalog/apps.yaml
  resource: raw:v-control/catalog/apps.yaml
---
# Service catalog dependency map

The application catalog is a single YAML document, `catalog/apps.yaml` in each scenario's raw snapshot. It is the authoritative source for service topology and ownership. Each entry records:[^catalog-apps]

- `id` — the canonical application identifier (for example `edge-gateway`, `artwork-svc`).
- `aliases` — other names the app appears under (for example `artwork-svc` is also `ArtworkSvc` and `artwork`).
- `owner_team` — the owning team, for example `Team Imagery`.
- `tier` — criticality tier, 0 (most critical) to 3.
- `regions` — deployment regions.
- `kind` — `service`, `edge`, `client`, `cache`, or `datastore`.
- `dependencies` — the apps this one calls, each with a `protocol` (`http`, `grpc`, `graphql`, `memcached`, `cql`).

Example:[^catalog-apps]

```yaml
id: edge-gateway
aliases: [EdgeGateway, zuul-edge]
owner_team: Team Edge
tier: 0
kind: edge
dependencies:
- app: homepage-graphql
  protocol: http
- app: playback-api
  protocol: http
- app: search-svc
  protocol: grpc
```

To classify whether an alert on another app is same-failure or background, resolve its dependency closure from this file rather than guessing from names or timing. See [localize-degraded-call-path](../skills/localize-degraded-call-path/SKILL.md) for the procedure, and be aware that telemetry may carry aliases, not `id`s — see [trace span data](trace-span-data.md).

[^catalog-apps]: Application catalog `apps.yaml`: entries for edge-gateway, artwork-svc, artwork-metadata-svc and others with aliases, owner_team, tier, regions, kind, and dependencies with protocols.
