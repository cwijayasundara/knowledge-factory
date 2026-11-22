# Runbook

Phase 0 is flag-only: agents file flags, the starved baseline is recorded, the removal list is sealed.
Phase 1 is the measured run: curate, gate, blind review, then the G2 measurement. All commands run from the
repo root (`uv run kf ...`); default paths are anchored to the repo root.

`bash scripts/phase0.sh --plan` prints every Phase 0 command. Without a flag it runs the steps that call no
LLM and stops at the first one that does. `--yes` also runs the LLM steps (needs `FIREWORKS_API_KEY`, costs
money). The script deletes nothing: a seed already on disk is skipped because e2ekg's generator refuses a
non-empty output directory.

## Roles: who writes the list, who reviews

- The **list author** writes the removal list, seals it (`kf seal --author NAME`) and later opens it.
- The **reviewer** approves curator changes (`kf review approve --by NAME`) blind: on each change's cited raw
  evidence alone (`kf review show`), never seeing the list (spec 9c).
- They must be different people. `kf eval g2` is invalid if any person approval (in `state/approvals.jsonl` or as
  a `verified` stamp in the measured bundle) is by the list author.
- **Where the list lives:** outside the repo working tree, at `~/.kf/removal.yaml` (or `$KF_REMOVAL_LIST`, or
  `--list`). `kf seal` refuses a list inside the repo. The tracked `evalx/removal.template.yaml` is only a
  template. Only the seal (sha256, author, time) is committed. Each starved eval run copies the list into its own
  run dir (`state/evals/<run>/seed-N/removal.yaml`, git-ignored) before e2ekg starts; the reviewer does not open
  `~/.kf/` or `state/evals/`.

## Before you start

- `uv sync`, and `bash scripts/fetch_okf.sh` (`kf ci` needs `external/okf`).
- `uv run kf ci bundle/` exits 0 (the seed bundle). The seed bundle holds company knowledge only; definitions of
  the eval harness (metrics, traps, the scorecard) are in `docs/eval-glossary/` and are never served.
- Seeds are fixed in code (`kf.evalx.split`): `CURATION_SEEDS` = 11, 12, 13 feed the curator (flags, trails, raw
  views) and the eval gate; `HELDOUT_SEEDS` = 21, 22, 23 are for G2 scoring only. They never overlap.

## Phase 0

1. **Apply e2ekg.** `bash integration/apply.sh` clones e2ekg at `integration/E2EKG_PIN`, applies the three
   patches (kf tools, `graph_kb` arm, starve switch) and installs `kf` into its environment. It resets
   an existing `external/e2ekg` clone to the pin (tracked changes there are discarded).
2. **Curation data**, one data root per curation seed (`data_curation/seed-N`, git-ignored). Run inside
   `external/e2ekg` with absolute paths (the flags are from `e2ekg/cli.py`; `scripts/ingest.sh` fixes its paths
   to `data/`, so it is not used for per-seed roots):

   ```
   R=$PWD/data_curation/seed-N
   e2ekg generate   --scenario all --seed N --out $R/raw
   e2ekg preprocess --scenario all --raw $R/raw --out $R/processed --llm scripted
   e2ekg ledger     --scenario all --raw $R/raw --out $R/processed
   e2ekg harvest    --scenario all --proc $R/processed --out $R/graph
   e2ekg harvest    --scenario all --proc $R/processed --out $R/graph --as-of
   ```

   (`e2ekg` is `uv run e2ekg` run from `external/e2ekg`.) `--llm scripted` needs no network; use
   `PREPROCESS_LLM=fireworks` (with `--yes`) for GLM chat labels. The generator keeps its held-out answer key
   and all post-cutoff data inside the raw output directory: the curator never gets that directory. It gets an
   as-of view built by `kf raw-view` (step 9); `kf curate` refuses any other directory.
3. **Held-out data**, the same commands for each `HELDOUT_SEEDS` into `data_heldout/seed-N`.
4. **Write the removal list** (the list author, by hand; the script stops until it has items):
   `mkdir -p ~/.kf && cp evalx/removal.template.yaml ~/.kf/removal.yaml`, then edit the items. Each item removes
   one exact text from one e2ekg prompt file for every LLM arm. Only knowledge that is derivable from the data may
   be removed (`why_derivable_from`). The seed bundle must not hold any removed text: it covers only severity and
   priority, team ownership and escalation, change-kind, signal-type and fault-kind glossary, and incident-process
   policies. Candidates for the list are service alias hints, the metric tag-name convention, which source to
   trust for what, and non-obvious investigation steps. An empty list is refused.
5. **Seal.** `uv run kf seal --author NAME` writes `integration/removal.seal` (sha256, author, time). It refuses
   with exit 1 if the list is empty, inside the repo, or if any item's text is found in a bundle file
   (`kf eval run --heldout` without `--test-run` does the same checks). Commit the seal alone:
   `bash scripts/commit_seal.sh`. From here the list must not change; `uv run kf seal --verify` must pass for every
   measured run, and the seal commit must predate the first measured run (`kf eval g2` checks).
6. **Baseline** (LLM): `uv run kf eval run --arms graph --starve --heldout --runs 3`. One run directory per seed
   under `state/evals/heldout-<stamp>/seed-N`; keep the `heldout-<stamp>` path for G2 (`--starved`). There is no
   separate baseline file: `kf eval g2` reads the run directory.
7. **Flag collection** (LLM): `uv run kf eval run --arms graph_kb --starve --runs 3` on the curation seeds
   (the default for `eval run`). Agents file flags through `kf_flag` into `state/flags.db` (run ids
   `curation-<stamp>-seedN__<scenario>__graph_kb__<run>`); read them with `uv run kf flags list`. Held-out runs
   write their flags to their own run dir, never to `state/flags.db`.
8. **Stop** Phase 0 here. Before the first curator merge, tag the seed bundle commit:
   `git tag kf-seed` (the seed-only control of step 14 runs on it).

## Phase 1: curate, gate, review, measure

Ontology proposals are collected but not applied while a measurement runs (spec 9b).

9. **Raw view** for each curation seed: `uv run kf raw-view --data-root data_curation/seed-11
   --out state/raw-views/seed-11` (per scenario: e2ekg's as-of raw view, plus a marker `kf curate` checks).
   Held-out data roots are refused.
10. **Curate** (LLM): `uv run kf curate --raw-dir state/raw-views/seed-11 --trails-dir
    state/evals/curation-<stamp>/seed-11 --judge-model <a different model>`. Prints the decisions and opens
    `kf/<run_id>` with `state/runs/<run_id>.json`. Held-out trails or raw dirs are refused. `--dry-run` first is
    cheap.
11. **Gate** (LLM): `uv run kf eval gate --branch kf/<run_id>` runs `graph_kb` (starved) on the curation seeds over
    `main` and over the branch (its proposed concepts served as if approved, in a snapshot copy only) and writes
    the scores and their provenance into the run record. Exit 0 PASS, 1 FAIL. Re-run it if `main` or the branch
    moves: `kf review approve` refuses stale gate scores.
12. **Review** (the reviewer, not the list author): `uv run kf review list`, `uv run kf review show kf/<run_id>`
    (changed files, cited raw sources, decisions and rationales), then
    `uv run kf review approve --branch kf/<run_id> --by NAME` (Tier 2 needs `--second-by OTHER` or the judge) or
    `uv run kf review reject kf/<run_id> --by NAME --reason ...`. Tier 0 branches: `uv run kf review auto-merge
    --branch kf/<run_id>`. Tier 3 curator branches are refused. Repeat 9-12 until the flags are worked off.
13. **Treatment** (LLM): `uv run kf eval run --arms graph_kb --starve --heldout --runs 3` (snapshots `main` once
    for every seed) -> `state/evals/heldout-<B>`.
14. **Seed-only control** (LLM): `uv run kf eval run --arms graph_kb --starve --heldout --runs 3
    --bundle-commit kf-seed` -> `state/evals/heldout-<C>`. Same prompts and arm as the treatment on the pristine
    seed bundle, so the curator is the only difference.
15. **G2**: `uv run kf eval g2 --starved state/evals/heldout-<A> --kb state/evals/heldout-<B>
    --seed-kb state/evals/heldout-<C>` writes `reports/g2-<date>.md`. It passes only when `graph_kb` beats the
    starved arm by at least 2 top1 scenario-runs and beats the seed-only control, with no trap or control false
    positive rise. It is invalid (exit 2, no report) unless the three sets are comparable (data roots, scenarios,
    runs, per-scenario rows, one e2ekg commit, one bundle commit per kb set, a pristine ancestor seed commit),
    sealed (every run read the committed seal's list, sealed before the first run), held-out, not test runs, and
    free of scripted, test-run and list-author approvals.
16. **Open the list** (the list author) only after the G2 report is written.

## Checks that gate a headline

- `--test-run` marks a run as a test: it never counts toward G2.
- A scripted approver (`kf review approve --kind scripted --test-run`) is accepted only on test runs; its stamp
  (`human:scripted-test`) never counts as human-reviewed and makes G2 invalid.
- `kf` names the generator's answer-key directory only to deny it: the curator's read deny rules
  (`kf.curator.agent.PERMISSIONS`) and the write guard (`kf.curator.guard`) refuse any path that names it, in any
  letter case. No allow rule or default path points at it.
