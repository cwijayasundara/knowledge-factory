---
type: Table
title: Commit event log
description: Where raw source-control commit content lives and what it records — hash,
  author, UTC date and a bracketed-app one-line message.
x-kf-kind: data_access
x-kf-owner: team:platform-observability
x-kf-review: proposed
x-kf-risk: 0
x-kf-confidence: high
generated:
  by: kf-curator/0.1.0
  at: '2026-11-22T19:22:20Z'
x-kf-flags:
- 8
sources:
- id: commits-log
  resource: raw:v-control/events/commits.log
  title: Raw commit event log
- id: v-control/events/commits.log
  resource: raw:v-control/events/commits.log
---
# Commit event log

Commit content lives in `events/commits.log` in each scenario's raw snapshot, a git-style log. Each entry has the commit hash, author name and email, a UTC `Date:` line, and an indented one-line message that names the affected app in square brackets:[^commits-log]

```
commit b4b30bbce3d0ec974f1ecdf4a5b37f693fd04706
Author: Marco Rossi
Date:   Tue Oct 13 18:27:00 2026 +0000

    [device-proxy] Fix flaky readiness probe
```

Correlating the bracketed app name and commit time with an alert window answers "what changed and when" even when a change graph shows commits with an empty `what` field. Diffs are not part of the log; only the message line. Map the app name to its catalog entry via the [service catalog dependency map](service-catalog-dependencies.md).

[^commits-log]: commits.log entries for 2026-10-13 18:27–19:08 UTC: `[device-proxy] Fix flaky readiness probe`, `[pricing-svc] Log upstream status on fallback`, `[device-cache] Add hedged-request metrics`, `[device-proxy] Bump grpc-java to 1.68.1`.
 1.68.1`.
