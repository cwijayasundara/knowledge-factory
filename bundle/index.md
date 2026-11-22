---
okf_version: "0.3"
title: Knowledge Factory bundle
description: Seed bundle for the knowledge factory (incident process, severities, glossary, RCA metrics).
---

# Contents

- [SEV1](domain/severity/sev1.md): SEV1: Critical, widespread member impact.
- [SEV2](domain/severity/sev2.md): SEV2: Major impact on a key experience.
- [SEV3](domain/severity/sev3.md): SEV3: Minor or contained impact.
- [Severity scheme](domain/severity/scheme.md): The closed set of incident severities and their ordering.
- [Change kind: Deployment](domain/glossary/change-kind-deployment.md): Deployment: A server-side version rollout.
- [Change kind: Config change](domain/glossary/change-kind-config-change.md): Config change: A dynamic property change.
- [Change kind: Scaling](domain/glossary/change-kind-scaling.md): Scaling: An autoscaling capacity change.
- [Change kind: Experiment allocation](domain/glossary/change-kind-experiment-allocation.md): Experiment allocation: An A/B allocation change.
- [Change kind: Commit](domain/glossary/change-kind-commit.md): Commit: A source control commit.
- [Change kind: Client release](domain/glossary/change-kind-client-release.md): Client release: A device client release.
- [Change kinds](domain/glossary/change-kinds.md): The six closed kinds of change a system records.
- [Signal types](domain/glossary/signal-types.md): The thirteen signal types a correlation engine reasons over.
- [Telemetry signal types](domain/glossary/signal-types-telemetry.md): Signal types detected from telemetry.
- [Declared signal types](domain/glossary/signal-types-declared.md): Signal types that are declared events, not detections.
- [Fault kinds](domain/glossary/fault-kinds.md): The closed set of fault kinds, plus none for control scenarios.
- [Metric: top1](domain/metrics/top1.md): The true root cause is the first hypothesis. In the control scenario, a correct abstention counts.
- [Metric: top3](domain/metrics/top3.md): The true root cause is among the first three hypotheses.
- [Metric: trap rate](domain/metrics/trap.md): The share of runs where a planted red herring was picked as the number one hypothesis.
- [Metric: evidence precision](domain/metrics/evidence-precision.md): The share of the top hypothesis's cited evidence that reaches answer-key evidence.
- [Metric: control false positive](domain/metrics/control-false-positive.md): A run that claimed a root cause in the scenario that has none.
- [RCA metric scorecard](domain/metrics/scorecard.md): How RCA quality metrics are read together.
- [Policy: repeat stochastic runs](domain/policies/repeat-runs.md): One run per stochastic arm proves nothing; use repeated runs.
- [Policy: confirming a root cause](domain/policies/confirmed-chain.md): A correct top-1 chain is confirmed only after a person approves it.
- [Policy: hypotheses carry evidence](domain/policies/hypotheses-carry-evidence.md): Every hypothesis cites its evidence, because hypotheses can be wrong.
- [Policy: incident record versions](domain/policies/incident-record-versions.md): Incident records keep every version; the latest is current.
- [Team ownership](domain/ownership/team-ownership.md): Every application in the catalog has an owner team.
- [Escalation conventions](domain/ownership/escalation.md): Incidents are declared with a severity, responders are paged by rotation.
- [Incident roles](domain/ownership/incident-roles.md): Who takes part in an incident: owners, responders, mitigators.
- [classify-incident-severity](skills/classify-incident-severity/SKILL.md): Use when asked to label an incident SEV1, SEV2 or SEV3 or to order incidents by priority.
- [escalate-incident](skills/escalate-incident/SKILL.md): Use when an incident needs paging, a responder or an owner team contacted.
- [read-rca-scorecard](skills/read-rca-scorecard/SKILL.md): Use when reporting or comparing RCA evaluation results.
