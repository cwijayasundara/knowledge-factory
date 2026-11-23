---
okf_version: "0.3"
title: Knowledge Factory bundle
description: Seed bundle for the knowledge factory (incident process, severities, glossary).
---

# Contents

- [Commit event log](data_access/commit-log.md): Where raw source-control commit content lives and what it records — hash, author, UTC date and a bracketed-app one-line message.
- [Service catalog dependency map](data_access/service-catalog-dependencies.md): What the application catalog records per app — aliases, owner team, tier, and dependencies — and where the catalog file lives.
- [Trace span data](data_access/trace-span-data.md): Where raw distributed-trace span data lives (OTLP and Zipkin JSONL), its formats, and the alias pitfall that makes id-verbatim lookups return nothing.
- [Commit messages](data_access/commit-messages.md): Commit content lives in the scenario events log: hash, author, date and subject line per commit.
- [Span telemetry](data_access/span-telemetry.md): Per-scenario trace spans are exported as OTLP JSONL; per-hop call edges are reconstructed by joining child spans to parents via parentSpanId.
- [Service map](domain/catalog/service-map.md): The software catalog records, per application, the other apps it calls, over which protocol, plus aliases, owner team, tier, regions and kind.
- [Change kind: Client release](domain/glossary/change-kind-client-release.md): Client release: A device client release.
- [Change kind: Commit](domain/glossary/change-kind-commit.md): Commit: A source control commit.
- [Change kind: Config change](domain/glossary/change-kind-config-change.md): Config change: A dynamic property change.
- [Change kind: Deployment](domain/glossary/change-kind-deployment.md): Deployment: A server-side version rollout.
- [Change kind: Experiment allocation](domain/glossary/change-kind-experiment-allocation.md): Experiment allocation: An A/B allocation change.
- [Change kind: Scaling](domain/glossary/change-kind-scaling.md): Scaling: An autoscaling capacity change.
- [Change kinds](domain/glossary/change-kinds.md): The six closed kinds of change a system records.
- [Fault kinds](domain/glossary/fault-kinds.md): The closed set of fault kinds, plus none when nothing is at fault.
- [Declared signal types](domain/glossary/signal-types-declared.md): Signal types that are declared events, not detections.
- [Telemetry signal types](domain/glossary/signal-types-telemetry.md): Signal types detected from telemetry.
- [Signal types](domain/glossary/signal-types.md): The thirteen signal types a correlation engine reasons over.
- [Escalation conventions](domain/ownership/escalation.md): Incidents are declared with a severity, responders are paged by rotation.
- [Incident roles](domain/ownership/incident-roles.md): Who takes part in an incident: owners, responders, mitigators.
- [Team ownership](domain/ownership/team-ownership.md): Every application in the catalog has an owner team.
- [Policy: confirming a root cause](domain/policies/confirmed-chain.md): A leading causal chain is confirmed only after a person approves it.
- [Policy: hypotheses carry evidence](domain/policies/hypotheses-carry-evidence.md): Every hypothesis cites its evidence, because hypotheses can be wrong.
- [Policy: incident record versions](domain/policies/incident-record-versions.md): Incident records keep every version; the latest is current.
- [Severity scheme](domain/severity/scheme.md): The closed set of incident severities and their ordering.
- [SEV1](domain/severity/sev1.md): SEV1: Critical, widespread member impact.
- [SEV2](domain/severity/sev2.md): SEV2: Major impact on a key experience.
- [SEV3](domain/severity/sev3.md): SEV3: Minor or contained impact.
- [classify-incident-severity](skills/classify-incident-severity/SKILL.md): Use when asked to label an incident SEV1, SEV2 or SEV3 or to order incidents by priority.
- [escalate-incident](skills/escalate-incident/SKILL.md): Use when an incident needs paging, a responder or an owner team contacted.
- [localize-degraded-call-path](skills/localize-degraded-call-path/SKILL.md): Use when an error-rate or latency alert needs hop-by-hop localization: build the dependency closure, reconstruct call edges from raw trace spans, and compare per-hop health across the alert window.
