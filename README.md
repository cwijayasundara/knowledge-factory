# Knowledge factory

A sample knowledge factory for agents: working agents **flag** the knowledge they were missing, a
**curator** agent turns those flags into proposed changes to a versioned knowledge **bundle**, an **eval
gate** checks the change does no harm, a **human reviews** it, and a **measurement** (G2) shows whether
the curated bundle makes agents better. Design: [docs/superpowers/specs/2026-11-22-knowledge-factory-design.md](docs/superpowers/specs/2026-11-22-knowledge-factory-design.md).
Operating steps: [docs/RUNBOOK.md](docs/RUNBOOK.md). Curator rules: [AGENTS.md](AGENTS.md) (humans only).
Animated walkthrough of the loop: open [docs/knowledge-factory.html](docs/knowledge-factory.html) in a browser (click "Show the factory", then "Play the loop").

```
working agents (e2ekg AutoRCA, arm graph_kb)
   │ kb_search / kb_read            │ kf_flag  "I could not find X"
   ▼                                ▼
bundle/  (OKF v0.3 concepts + SKILL.md)      state/flags.db  (flag queue)
   ▲                                │
   │ merge after review             ▼
kf/<run_id> branch  ◀── curator (kf curate): triage → locate → re-derive from raw → decide → write → validate
   │                                    │ judge by a different model (judge_ok, judge_unsupported)
   ├── kf eval gate  (graph_kb, starved, curation seeds: main vs branch)
   └── kf review approve  (a person who is not the removal-list author)
```

## Try it manually: three scripts

Needs `uv`, `git`, Node 20+ and a `.env` with `FIREWORKS_API_KEY=fw_...` (for LLM runs; the graph and bundle
views work without it).

```bash
scripts/setup.sh            # 1. once: Python env, OKF validator, patched e2ekg, hero knowledge graph, UI packages
scripts/start-backend.sh    # 2. terminal 1: API on http://127.0.0.1:8000 (docs at /docs)
scripts/start-frontend.sh   # 3. terminal 2: UI on http://localhost:3000
```

- `setup.sh --scenario all` ingests all 7 scenarios (slow); `--clean` rebuilds the data. It is safe to re-run and
  never re-applies the patches to an existing `external/e2ekg` (that could invalidate a G2 measurement).
- The backend serves the bundle as it is on `main` (a frozen snapshot taken at start). `KF_BUNDLE_REF=kf/<run_id>`
  serves a curator branch instead. Flags the agents file land in `state/manual/flags.db`
  (`uv run kf flags list --db state/manual/flags.db`).
- Ports: `API_PORT`, `PORT` and `API_URL` change them (see the script headers).

## Layout

| Path | What |
|---|---|
| `bundle/` | the knowledge: OKF v0.3 concepts (`domain`, `data_access`) and skills |
| `src/kf/flags` | flag queue and models |
| `src/kf/curator` | curator agent, tools, write guard, decisions, trails, raw views, ontology hand-off |
| `src/kf/review` | tiers, review, approve/merge, the gate rules |
| `src/kf/evalx` | eval runner, seed split, sealed removal list, gate run, G2 |
| `src/kf/bundle` | OKF parsing, profile, CI, read-only serving and snapshots |
| `integration/` | pins and patches for e2ekg (the agent testbed) and the OKF validator |
| `external/` | git-ignored clones of e2ekg (backend and UI) and OKF |
| `state/` | git-ignored: flags, run records, eval runs, snapshots |
| `scripts/` | the three manual-test scripts, plus `phase0.sh`, `fetch_okf.sh`, `commit_seal.sh` |

## The loop (CLI)

```bash
uv run pytest -q                         # ~380 tests, scripted model, no LLM cost
uv run kf ci bundle/                     # validate the bundle
uv run kf flags list                     # open flags
uv run kf curate --raw-dir state/raw-views/seed-11 --judge-model fireworks:accounts/fireworks/models/kimi-k3
                                         # curator (GLM) opens kf/<run_id>; the judge must be a different model
uv run kf review show kf/<run_id>        # changed files, cited sources, decisions, judge_ok, judge_unsupported
uv run kf eval gate --branch kf/<run_id> --now 2026-11-20T00:00:00+00:00
                                         # ~5 min: 3 seeds x (main, branch) run in parallel, 1 run per scenario
uv run kf review approve --branch kf/<run_id> --by <your name>
```

Reviewer rules: the approver is a person, not the removal-list author (`kf seal --verify` shows the author), and the
gate scores must be current: re-run the gate if `main` or the branch moves. The curator never writes `verified`.

## Testing the factory

1. **Code (seconds):** `uv run pytest -q`, `uv run kf ci bundle/`.
2. **Curator quality (minutes):** `kf curate --dry-run`, then a real run with a different judge model. Read
   `kf review show`: every claim should trace to a raw source; `judge_unsupported` lists what the judge rejected.
3. **Does it help (G2, long and paid):** runbook steps 13-15 on the held-out seeds, comparing the starved baseline,
   the curated bundle and the seed-only control. It passes only if the curated bundle beats the baseline by at
   least 2 top-1 scenario-runs, beats the control, and raises no trap or control false positives. The gate is only
   a no-regression check: the curation seeds already score 21/21.
4. **Safety:** the write guard, answer-key access and prompt injection through flag text are covered in
   `tests/curator/test_guard.py`.

## Status (2026-11-23)

- Built: bundle and CI, flag queue, curator with write guard and judge, tiered review and merge, eval harness
  (sealed removal list, split seeds, parallel gate, G2 verdict), e2ekg integration, the three scripts above.
- Phase 0 done: removal list sealed, `kf-seed` tagged, starved held-out baseline recorded (seeds 21-23).
- Curator branch `kf/curate-20261123T0540Z` (service map, span telemetry, commit messages): judge OK after three
  manual fix commits, gate PASS (21/21 vs 21/21). It awaits review and merge by a person.
- Not done: the G2 measurement (treatment, seed-only control, `kf eval g2`); remaining flags 4 and 7.
- Known issue: a run record can list decisions for targets that were never written, so `kf review show` can list
  more decisions than files.
