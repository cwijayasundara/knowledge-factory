---
name: localize-degraded-call-path
description: 'Use when an error-rate or latency alert needs hop-by-hop localization:
  build the dependency closure, reconstruct call edges from raw trace spans, and compare
  per-hop health across the alert window.'
x-kf-kind: skill_card
x-kf-owner: team:platform-observability
x-kf-review: proposed
x-kf-risk: 0
sources:
- id: otlp-sample
  resource: raw:v-control/traces/otlp/1200.jsonl
  title: Raw OTLP span export sample
- id: catalog-apps
  resource: raw:v-control/catalog/apps.yaml
  title: Raw application catalog (apps.yaml)
- id: v-control/traces/otlp/1200.jsonl
  resource: raw:v-control/traces/otlp/1200.jsonl
- id: v-control/traces/zipkin/1200.jsonl
  resource: raw:v-control/traces/zipkin/1200.jsonl
- id: v-control/catalog/apps.yaml
  resource: raw:v-control/catalog/apps.yaml
generated:
  by: kf-curator/0.1.0
  at: '2026-11-22T19:21:36Z'
x-kf-flags:
- 5
---
# Localize a degraded call path

1. Read the alert's service and window. Resolve its dependency closure from the [service catalog dependency map](../../data_access/service-catalog-dependencies.md); do not guess relatedness from app names or timing.
2. Locate the raw trace span files for the window: `traces/otlp/*.jsonl` (OTLP) and `traces/zipkin/*.jsonl` (Zipkin), bucketed per minute. See [trace span data](../../data_access/trace-span-data.md).
3. Normalize names before matching: trace `service.name` values may be catalog aliases or variants (`artwork` → `artwork-svc`, `Homepage-Graphql` → `homepage-graphql`, `row-ranker-prod` → `row-ranker`, `artworkmeta` → `artwork-metadata-svc`). Matching catalog ids verbatim yields empty results that look like missing telemetry.
4. Reconstruct call edges: group spans by `traceId`, order by `parentSpanId` → `spanId` to get caller → callee hops. In Zipkin exports, `duration` is microseconds; in OTLP, subtract `startTimeUnixNano` from `endTimeUnixNano` (nanoseconds).
5. Score each hop over the window: error fraction from `status.code` 2 (OTLP) or `rpc.grpc.status_code` ≠ 0, plus p95 duration.
6. Localize the failure at the deepest hop whose error/latency degrades while upstream hops merely inherit it (an upstream span shows `status.code` 2 "upstream error" with the failing downstream hop beneath it).
7. Check what changed nearby: commits in the window are in `events/commits.log` with bracketed app names — see [commit event log](../../data_access/commit-log.md).
8. State the degraded hop, the evidence (trace ids, per-hop stats), and remaining uncertainty explicitly.
