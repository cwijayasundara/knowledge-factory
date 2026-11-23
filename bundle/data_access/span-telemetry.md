---
type: Definition
title: Span telemetry
description: Per-scenario trace spans are exported as OTLP and Zipkin JSONL; per-hop
  call edges are reconstructed by joining child spans to parents via parentSpanId.
x-kf-kind: data_access
x-kf-owner: team:platform-observability
x-kf-risk: 0
x-kf-confidence: medium
tags:
- traces
- spans
- otlp
- zipkin
- data-access
sources:
- id: otlp-1217
  resource: raw:v-control/traces/otlp/1217.jsonl
  title: OTLP span export sample
- id: v-control/traces/otlp/1217.jsonl
  resource: raw:v-control/traces/otlp/1217.jsonl
generated:
  by: kf-curator/0.1.0
  at: '2026-11-23T05:40:49Z'
x-kf-review: proposed
x-kf-flags:
- 7
---
# Span telemetry

Raw scenario sources carry distributed-trace span exports under `traces/otlp/` and `traces/zipkin/`, as JSON-lines files (e.g. `traces/otlp/1217.jsonl`).[^otlp-1217]

OTLP records carry a `resource` block with `service.name`, `host.name`, `cloud.region` and `deployment.environment`, and `scopeSpans` with individual spans. Each span has `traceId`, `spanId`, `parentSpanId`, `name`, `kind`, `startTimeUnixNano`, `endTimeUnixNano`, attributes (e.g. `http.method`, `http.route`, `http.status_code`, `rpc.service`, `rpc.method`, `rpc.grpc.status_code`) and a `status` block.[^otlp-1217]

Per-hop call edges are not provided as precomputed records; reconstruct them by joining a child span to its parent span on the same `traceId` via `parentSpanId`. A single trace can span several services this way (for example, a trace containing an `edge-gateway` `POST /graphql` parent with `search-svc` and `session-svc` children).[^otlp-1217]

If a correlation tool reports no call-edge records for a window, check the raw span exports for that window before concluding that no per-hop evidence exists.

[^otlp-1217]: v-control raw source `traces/otlp/1217.jsonl`.
