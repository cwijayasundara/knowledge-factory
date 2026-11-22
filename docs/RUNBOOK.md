# Phase 0 runbook

Phase 0 is flag-only: agents file flags, the starved baseline is recorded, the removal list is sealed.
Exit: flags exist, baseline stored, seal committed. The curator is not run in Phase 0.

`bash scripts/phase0.sh --plan` prints every command below. Without a flag it runs the steps that call no
LLM and stops at the first one that does. `--yes` also runs the LLM steps (needs `FIREWORKS_API_KEY`, costs
money). The script deletes nothing: a seed already on disk is skipped because e2ekg's generator refuses a
non-empty output directory.

## Before you start

- `uv sync`, and `bash scripts/fetch_okf.sh` (`kf ci` needs `external/okf`).
- `uv run kf ci bundle/` exits 0 (the seed bundle).
- Seeds are fixed in code (`kf.evalx.split`): `CURATION_SEEDS` = 11, 12, 13 feed the curator (flags and
  trails); `HELDOUT_SEEDS` = 21, 22, 23 are for scoring only. They never overlap.

## Steps

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
   inside the raw output directory: never give a curator that raw directory (the curator refuses it);
   `kf curate --raw-dir` takes an as-of view prepared without it.
3. **Held-out data**, the same commands for each `HELDOUT_SEEDS` into `data_heldout/seed-N`.
4. **Write `evalx/removal.yaml`** (the owner, by hand; the script stops until it has items). Each item removes one
   exact text from one e2ekg prompt file for every LLM arm. Only knowledge that is derivable from the data may be
   removed (`why_derivable_from`). The seed bundle must not hold any removed text: it covers only severity and
   priority, team ownership and escalation, change-kind and signal-type glossary, RCA metric definitions and
   incident-process policies. Candidates for the list are service alias hints, the metric tag-name convention,
   which source to trust for what, and non-obvious investigation steps.
5. **Seal.** `uv run kf seal` writes `integration/removal.seal` (sha256 of the list). It refuses with exit 1,
   listing ids, if any removal item's text is found in a bundle file (`kf eval run --heldout` without
   `--test-run` does the same check). Commit the seal alone:
   `git add integration/removal.seal && git commit -m "chore: seal the removal list" -- integration/removal.seal`.
   From here the list must not change; `uv run kf seal --verify` must pass for every measured run.
6. **Baseline** (LLM): `uv run kf eval run --arms graph --starve --heldout --runs 3`. One run directory per seed
   under `state/evals/<stamp>/seed-N`. Record the summed scores in `state/baseline.json`
   (`uv run python -c` over `kf.evalx.runner.scores_from(<stamp dir>, "graph")`).
7. **Flag collection** (LLM): `uv run kf eval run --arms graph_kb --starve --runs 3` on the curation seeds
   (the default for `eval run`). Agents file flags through `kf_flag` into `state/flags.db`; read them with
   `uv run kf flags list`. The run is starved like the baseline: the same switch applies to both arms, and
   an unstarved agent has nothing to flag.
8. **Stop.** Do not run the curator in Phase 0.

## Checks that gate a headline

- `--test-run` marks a run as a test: it never counts toward G2.
- A scripted approver (`kf review approve --kind scripted --test-run`) is accepted only on test runs and is never
  counted toward G2.
- Nothing in `kf` or its permissions refers to the generator's answer-key directory.
