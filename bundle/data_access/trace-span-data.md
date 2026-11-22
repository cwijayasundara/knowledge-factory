---
type: Mapping
title: Trace span data
description: Where raw distributed-trace span data lives (OTLP and Zipkin JSONL),
  its formats, and the alias pitfall that makes id-verbatim lookups return nothing.
x-kf-kind: data_access
x-kf-owner: team:platform-observability
x-kf-review: proposed
x-kf-risk: 0
x-kf-confidence: high
generated:
  by: kf-curator/0.1.0
  at: '2026-11-22T19:22:26Z'
x-kf-flags:
- 5
sources:
- id: otlp-sample
  resource: raw:v-control/traces/otlp/1200.jsonl
  title: Raw OTLP span export sample
- id: zipkin-sample
  resource: raw:v-control/traces/zipkin/1200.jsonl
  title: Raw Zipkin span export sample
- id: v-control/traces/otlp/1200.jsonl
  resource: raw:v-control/traces/otlp/1200.jsonl
- id: v-control/traces/zipkin/1200.jsonl
  resource: raw:v-control/traces/zipkin/1200.jsonl
- id: v-control/catalog/apps.yaml
  resource: raw:v-control/catalog/apps.yaml
---
# Trace span data

Raw distributed-trace data lives under `traces/` in each scenario's raw snapshot, in two parallel exports, bucketed per minute (`traces/otlp/1200.jsonl` … `1236.jsonl`, likewise `traces/zipkin/`).[^otlp-sample][^zipkin-sample]

- **OTLP** (`traces/otlp/*.jsonl`): one [ResourceSpans] JSON object per line per service. Each span has `traceId`, `spanId`, `parentSpanId`, `name`, `kind`, `startTimeUnixNano`/`endTimeUnixNano` (nanoseconds), `attributes` (`http.method`, `http.route`, `http.status_code`, `rpc.system`, `rpc.service`, `rpc.method`, `rpc.grpc.status_code`, `db.system`, `peer.service`), and `status` (`code` 0 = ok, 2 = error, with `message` such as "upstream error").
- **Zipkin** (`traces/zipkin/*.jsonl`): one span per line with `traceId`, `id`, `parentId`, `kind` (`SERVER`/`CLIENT`), `timestamp` (microseconds), `duration` (microseconds), `localEndpoint.serviceName`, and `tags`.[^zipkin-sample]

For the v-control snapshot the buckets cover the alert window: the earliest OTLP start is `1791918002000000000` ns = 2026-10-13T19:00:02Z, and alert `radar-00200` fires at 19:07Z.[^otlp-sample]

## Alias pitfall

Trace `service.name` / `localEndpoint.serviceName` values are **not** always the catalog `id`. Observed variants:[^otlp-sample][^zipkin-sample]

| Trace name | Catalog id |
| --- | --- |
| `artwork` | `artwork-svc` |
| `Homepage-Graphql` | `homepage-graphql` |
| `row-ranker-prod` | `row-ranker` |
| `artworkmeta` | `artwork-metadata-svc` |

Lookups that match a catalog id verbatim against trace service names return nothing and look like missing telemetry. Always normalize through the catalog aliases first — see [service catalog dependency map](service-catalog-dependencies.md) and the [localize-degraded-call-path](../skills/localize-degraded-call-path/SKILL.md) procedure.

[^otlp-sample]: OTLP export: ResourceSpans with `service.name` values `edge-gateway`, `Homepage-Graphql`, `profile-svc`, `lolomo-svc`, `artwork`, `row-ranker-prod`; spans with traceId/spanId/parentSpanId, unix-nano times, http/rpc attributes, and `status.code` 2 with message "upstream error".
[^zipkin-sample]: Zipkin export: spans with `localEndpoint.serviceName` values `ratings-svc`, `artworkmeta`; microsecond `timestamp`/`duration`; tags include `rpc.grpc.status_code`, `db.system`, `peer.service`.
