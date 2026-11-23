---
type: Definition
title: Commit messages
description: 'Commit content lives in the scenario events log: hash, author, date
  and subject line per commit.'
x-kf-kind: data_access
x-kf-owner: team:platform-observability
x-kf-risk: 0
x-kf-confidence: medium
tags:
- commits
- changes
- data-access
sources:
- id: commits
  resource: raw:v-control/events/commits.log
  title: Commit events log
- id: v-control/events/commits.log
  resource: raw:v-control/events/commits.log
generated:
  by: kf-curator/0.1.0
  at: '2026-11-23T05:40:34Z'
x-kf-review: proposed
x-kf-flags:
- 8
---
# Commit messages

Commit content is recorded in the scenario event log at `events/commits.log`. Each entry is a `git log`-style record with the commit hash, an `Author:` line with name and email, a `Date:` line, and an indented subject line — for example `commit b4b30bbce3d0ec974f1ecdf4a5b37f693fd04706` by Marco Rossi, dated `Tue Oct 13 18:27:00 2026 +0000`, subject `[device-proxy] Fix flaky readiness probe`.[^commits]

If a change-graph query returns commits without content, read `events/commits.log` for the author, timestamp and subject of each commit. No diffs or repository snapshots were observed in the raw sources.

[^commits]: v-control raw source `events/commits.log`.
