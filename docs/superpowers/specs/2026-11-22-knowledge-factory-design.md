# Knowledge factory for AutoRCA: design

Status: draft for approval (reviewer question settled). Date: 2026-11-22.
Source report: `reports/Knowledge factory and curator agent design.md` (this repo). Consumer: the e2ekg / AutoRCA project (https://github.com/cwijayasundara/semantic_layers_v2.0).

## 1. Intent

Build a working reference implementation of Harrison Chase's "knowledge factory" loop, using AutoRCA as its first working agent. AutoRCA flags knowledge that is missing or wrong, one scheduled curator turns those flags into reviewed knowledge, and the working agent reads the result. The point is to show, on a measurable task, that curated knowledge improves an agent, and to keep the factory reusable for other agents later.

The factory lives in this repo (`knowledge_factory_v1.0`). e2ekg is a separate repo, used as an external dependency and changed only through four small patches (section 6).

## 2. Goals, non-goals, anti-goals

Goals
- G1. One end-to-end loop that runs from a command line: eval run, flags, curator run, review, merged knowledge, eval re-run.
- G2. A measured result: the `graph_kb` arm beats the `graph` arm on e2ekg's existing scorer, with the curator as the only thing that changed.
- G3. The report's governance model, kept: working agents never write knowledge, one curator writes, humans approve by risk tier.
- G4. Reusable: nothing in the factory core knows about observability. e2ekg-specific code is confined to an adapter.

Non-goals
- Production hosting, multi-tenant access control, a UI, or Slack/Notion connectors (the report's Phase 2-3). Real connectors are replaced by e2ekg's generated raw data.
- Replacing e2ekg's own ontology curator (`ontology_evolve/propose.py`). We reuse its gate (section 5).
- A vector store. Retrieval is index + grep/read, per the report.

Anti-goals (would make this a failure even if it runs)
- A1. The curator or the working agent ever reads the held-out answer key (`data/raw/_answers`). That would make G2 meaningless.
- A2. Working agents write knowledge directly.
- A3. A gain that comes from tuning the prompts to the test scenarios rather than from curated knowledge.
- A4. Knowledge stored in two places (a skill that copies a definition instead of linking to it).

## 3. Constraints and facts about the consumer

- AutoRCA is a DeepAgents commander plus 7 specialists (topology, change, metrics, logs, traces, alerts_incidents, history) over a read-only as-of RDF store, on GLM via Fireworks. Its knowledge today is its prompts (`agent/prompts/*.md`) and the graph. Its findings live in memory and are discarded after each run.
- e2ekg already has: `e2ekg eval` (resumable arms, scored against the answer key by `evals/score.py`: top1, top3, trap, control false positive, evidence precision), 7 scenarios including `v-control` (no root cause; the agent should abstain), and two proto-curators: `ontology_evolve/propose.py` (mine gaps, LLM proposes Turtle, additive-only gate with CQ + SHACL, human moves the file) and `flywheel/adapt.py` (human-approved root causes become priors).
- **Headroom risk.** e2ekg's own experiments record the graph arm and the raw-files arm both at or near 100% top-1 at default scale. A curator cannot show a gain on a task the agent already solves. The design therefore needs a deliberately knowledge-starved baseline (section 7).
- The factory must run on a laptop with a Fireworks key; no cloud services are required for the core loop.

## 4. Approaches considered

1. **Separate repo with a thin patch to e2ekg (chosen).** This repo holds bundle, flag queue, curator, CI and review. e2ekg gets a flag tool, a read-only knowledge tool and a new eval arm. Trade-off: two repos to keep in sync. Chosen because it keeps the factory reusable and keeps the working agent read-only by construction.
2. Build inside e2ekg as a `kf/` package. Simplest wiring, reuses the gate directly, but welds the factory to e2ekg's layout.
3. Grow e2ekg's existing proto-curators. Least new code, but skips OKF and SKILL.md and curates only ontology-shaped knowledge.

Borrowed from 2 and 3 despite choosing 1: the additive-only gate idea and `adapt.py`'s recorded-approval pattern.

## 5. Design

### 5.1 Parts

| Part | What it is | Notes |
|---|---|---|
| Knowledge bundle | A git-tracked directory `bundle/` of OKF v0.3 concepts (domain, data-access) plus standard SKILL.md skills | Layout and `x-kf-*` extension keys as in the report. `main` is what agents read. |
| Flag queue | SQLite file (`state/flags.db`) | Operational state, deliberately outside the bundle. Status machine borrowed from open-swe: open, triaged, in_review, resolved, declined, duplicate, held. |
| `kf_flag` tool | Python tool added to AutoRCA's commander and specialists | Schema from the report (kind, summary required; the rest optional). The handler, not the model, attaches agent, run id, scenario, timestamp, and rate-limits per run. Writes only to the queue. |
| Knowledge read tool | Read-only `kb_search` / `kb_read` over a mounted bundle snapshot | Index first, then grep/read. Serves only current knowledge by default (status stable, not past `stale_after`, review not proposed). |
| Curator | A scheduled DeepAgents agent (`kf curate`) | Stages as in the report: collect, triage, locate, re-derive from raw, reconcile (ADD/UPDATE/DEPRECATE/NOOP/ESCALATE), write on a branch, validate, propose. Never adds a `verified` entry. No deletes; deprecate with `superseded_by`. |
| Review and CI | Local git branches per curator run, a `kf review` CLI, and a CI script (`kf ci`) | The CLI stands in for pull requests; the tier rules and CI checks are the same ones a GitHub setup would enforce, so moving to real PRs later is a change of transport only. |
| Eval harness | `kf eval` wraps `e2ekg eval` with the new arm and a stored baseline | The merge gate: a Tier 1+ change merges only if the eval score is not worse than `main`. |

### 5.2 Knowledge placement rules
- How to do something (procedure, report format, investigation order) goes in a SKILL.md. What is true (a definition, an alias, a source-to-field mapping, a prior) goes in an OKF concept. Skills link to concepts and never copy them (anti-goal A4).
- Skills stay untyped SKILL.md files so standard loaders read them; they are governed by git history and ownership rules, not OKF frontmatter.

### 5.3 Review tiers (adapted from the report)
- Tier 0: index regeneration, link repair, formatting. Auto-merge after CI.
- Tier 1: new concepts with at least one cited raw source; data-access updates backed by a schema or catalog diff. One human approval plus the eval gate.
- Tier 2: changing a definition or prior, deprecations, anything contradicting human-reviewed content, anything with low confidence. Human approval plus the eval gate; the approval must be a second reviewer if more than one is configured, otherwise the single reviewer plus an LLM-judge check by a different model.
- Tier 3: `kf-profile.yaml`, the curator prompt, tier rules. Humans only; the curator may file a flag but not a diff.
- At merge, CI appends `verified: {by: human:<approver>, at: <merge time>}`. The approver id comes from the review command's argument, never from git config.

### 5.4 Trust and security rules
- Flags, traces and raw snapshots are untrusted input to the curator (data, never instructions). The ingest step has no write access to the bundle.
- Tool permissions, not prompt rules, enforce: the curator cannot write to `raw/`, `bundle/computations/`, the profile file or the tier rules.
- The curator and the agents run against the as-of view only. Nothing in the factory has the path `data/raw/_answers` in any permission list (anti-goal A1). Human approval in `kf review` plays the role the answer key plays in the eval, the same convention e2ekg's `flywheel/adapt.py` uses.
- The curator's LLM-judge and the model that wrote a change must differ, because same-model review is circular.

### 5.5 Ontology path
Where a flag implies the ontology is missing a concept (for example an uncovered error template), the curator does not write Turtle itself. It files the need into e2ekg's existing `propose.py` flow, whose additive-only gate and CQ/SHACL checks stay authoritative. This keeps one review story for both kinds of knowledge.

## 6. Changes to e2ekg (kept minimal, kept as patches)
1. `kf_flag` tool registered on the commander and specialists.
2. Read-only `kb_search` / `kb_read` tool, mounted from a bundle snapshot path.
3. A `graph_kb` eval arm: identical to `graph` except it has tools 1 and 2.
4. A "knowledge-starved" switch (config flag, same for both arms) that removes the items on the fixed removal list from prompts and catalog hints (section 7). This is a fourth patch; the reviewer pointed out that without it the comparison is confounded. *(my call, added after review)*
These live as a patch set in this repo (`integration/e2ekg-patches/`) applied to a pinned e2ekg commit, so the dependency is explicit.

## 7. Measuring it

- **Baseline with headroom.** Because AutoRCA is near ceiling today, the experiment starts from a *knowledge-starved* baseline: a defined, documented list of pieces of knowledge removed from the agent's prompts and catalog (candidates: service alias hints, the `nf.app|app|service` tag-name convention, which source to trust for what, the investigation procedure's non-obvious steps). The removal list is fixed before the first run and committed, so the gain cannot be tuned afterwards (anti-goal A3).
- **Success criterion (G2).** On the chosen scenarios, `graph_kb` after curation scores a higher top1 than the starved `graph` arm, with no increase in trap rate or control false positives. Several runs per scenario, because the agents are stochastic.
- **Curator metrics.** Flag-to-resolution time, share of flags declined or held, review acceptance rate, revert rate, and flag recurrence (the same flag returning after a resolved change is the clearest failure signal).
- **Corpus metrics.** Citation coverage, human-reviewed ratio, stale ratio, orphan and broken links.

## 8. Phases

- Phase 0, flag-only: patches 1-3, flag queue, a small hand-written seed bundle, CI, the starved baseline recorded. Exit: agents file flags; baseline score stored.
- Phase 1, curator in review mode: the 8-stage curator over flags and raw deltas; every change goes through `kf review`. Exit: reviewed changes merged; `graph_kb` re-run shows the first measurable change.
- Phase 2, traces and tiers: curator also reads run trails (e2ekg `trail.py` output); Tier 0 auto-merge; eval gate required.
- Phase 3 is out of scope for this build (second workflow, separate bundles per audience, hosted scheduling), noted so the layout does not preclude it.

## 9. Decisions I made (not yet confirmed by you)
- Local git branches and a CLI replace GitHub pull requests for now (no remote exists for this repo).
- SQLite for the flag queue; OKF v0.3 pinned; skills as plain SKILL.md.
- The curator runs on a DeepAgents agent using Fireworks GLM, same stack as AutoRCA; the judge model is a different one, chosen by the builder.
- e2ekg is pinned to a commit and patched from this repo, not forked.

## 9b. Calls made after the builder review (mine; check them)
- **Removal list is limited to knowledge derivable from raw/as-of data** (aliases visible in catalog and logs, tag-name conventions, source-of-truth hints). Anything not derivable is not removed, so the curator is never asked to produce what it cannot know. *(Answers: is the removed knowledge recoverable.)*
- **Train/test split.** e2ekg's generator is seeded. Curation (flags, trails) runs on scenarios generated from curation seeds; scoring runs on separate held-out seeds of the same scenario families, including `v-control`. No scenario that feeds the curator is used to score it.
- **Seed bundle must be disjoint from the removal list.** `graph_kb` starts from the seed bundle; the `graph` baseline gets no bundle. Both use the starved prompts.
- **Ontology frozen during measurement.** Ontology proposals via `propose.py` are collected but not applied while a measurement is running, so the only changed variable is the bundle. Applying them is a separate, later experiment.
- **Eval gate numbers (defaults, tunable):** 3 runs per arm per scenario; a Tier 1+ change fails the gate if top1 drops by more than one run's worth on the gate scenarios or if trap rate or control false positives rise; G2 passes when held-out top1 for `graph_kb` exceeds the starved `graph` by at least 2 scenario-runs and no safety metric rises. Cost and time budget are checked after the first Phase 0 run.
- **Frozen bundle snapshot per eval run**, tagged with the commit; a curator merge during a run never reaches that run.

## 9c. Reviewer (decided by the owner)
- **Headline result (G2): a real person reviews, blind.** The reviewer is not shown the removal list and reviews each curator change on its cited raw evidence alone. The removal list is committed in a sealed form (a hash is committed up front; the list itself is opened only after the measured run) so the blindness is auditable.
- **Tests and CI: a scripted approver.** `kf review` accepts an approver id; a scripted approver (`human:scripted-test`) is allowed only when the run is marked as a test run, and its approvals are never counted toward G2 or the human-reviewed ratio. A headline measurement that contains any scripted approval is invalid, and `kf eval` refuses to report it as G2.
- Consequence for the builder: `kf review` must record approver kind (person or scripted) on every approval, and the sealed-removal-list step is part of Phase 0.

## 10. Left to the builder
Exact module layout and CLI flags; the starved-baseline removal list (within the rule that it is fixed up front); concrete CI checks beyond `validate.py --strict` and the profile lint; `stale_after` defaults per concept kind; curator prompt wording; which scenarios and how many runs per arm.
