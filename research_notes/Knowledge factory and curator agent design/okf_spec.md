# Open Knowledge Format (OKF): technical summary for use as a knowledge-factory storage format

What I read: `SPEC.md` **v0.3** on `main` of [open-knowledge-format/open-knowledge-format](https://github.com/open-knowledge-format/open-knowledge-format). The last commit was 2026-11-18 ("Update SPEC.md", amir.hormati). I also read the README, CONTRIBUTING, the two agent skills, the validator, the GCP connector doc, the example bundles, and the issues in this repo and in the deprecated GoogleCloudPlatform repo. Research date: 2026-11-21. Field names below are copied exactly from the spec.

## 1. Purpose, maturity/version, license, maintainers, adoption

### Takeaway
OKF is a Google Cloud spec, created in June 2026, for storing organizational knowledge as "a directory of Markdown files with YAML frontmatter". It is at v0.3 (pre-1.0, so minor versions can still break things) and Apache-2.0. Two Google engineers effectively maintain it. It is attracting a lot of attention and a fast-growing set of community tools, but there is no independent evidence of large production deployments.

### Cited Findings
- Purpose: "OKF is an open format for *knowledge*: the metadata, context, and curated insight about data and systems… People write it, agents generate it, organizations exchange it, and people and agents consume it." It is "intentionally minimal… no schema registry, no central authority, and no required tools." — [SPEC.md §intro](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
- Motivation is explicitly about agent-maintained corpora: "Agents **write and maintain the corpus continuously**". When agents generate most concepts, consumers need provenance, trust, freshness, lifecycle and attestation, and OKF makes these "first-class". — [SPEC.md §1](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
- Non-goals: no fixed taxonomy of concept types, no prescribed storage/serving/query infrastructure, no replacement of domain schemas (Avro, Protobuf, OpenAPI), and no packaging standard for executor/attester code. — [SPEC.md §1](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
- Timeline:
  - v0.1 was published 2026-06-12 by Sam McVeety and Amir Hormati (Google Cloud Data Cloud). It "formalizes the LLM-wiki pattern" from Karpathy's gist, and the blog says "The answer to this problem isn't another knowledge service. You need a **format**". — [Google Cloud blog, v0.1](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing)
  - v0.2 (July 2026) added trust signals. Secondary sources disagree on the exact date: [dev.to](https://dev.to/amananandrai/googles-open-knowledge-format-from-a-karpathy-tweet-to-a-spec-and-what-the-evidence-says-ol8) says July 24, other search results say July 25.
  - v0.3 was announced 2026-11-19. — [Google Cloud blog, v0.3](https://cloud.google.com/blog/products/data-analytics/introducing-okf-v0-3)
- Governance move: v0.3 moved the spec "out of the Google Cloud Platform GitHub org into a standalone organization… to make cross-organization collaboration easier". — [Google Cloud blog, v0.3](https://cloud.google.com/blog/products/data-analytics/introducing-okf-v0-3)
  - The old repo [GoogleCloudPlatform/open-knowledge-format](https://github.com/GoogleCloudPlatform/open-knowledge-format) (1,568 stars, 101 forks) is now marked "deprecated", and development has moved to the new org. — [old repo README](https://github.com/GoogleCloudPlatform/open-knowledge-format)
  - Earlier, the spec lived under `GoogleCloudPlatform/knowledge-catalog/okf`. — [heise](https://www.heise.de/en/news/Open-Knowledge-Format-AI-Knowledge-as-Markdown-Files-11332310.html)
- Versioning policy: "Before 1.0, a minor version MAY contain breaking changes". "From 1.0, a minor version contains only backward-compatible additions". v0.3 has two breaking changes:
  - path fields without a leading `/` now resolve relative to their own file;
  - only current verifications count toward trust tiers.
  — [SPEC.md §12, §13.1](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
- License: the repo is Apache-2.0 ([repo metadata](https://github.com/open-knowledge-format/open-knowledge-format)). Contributions require a Google CLA (cla.developers.google.com). Spec changes are "held to a higher bar", so you open an issue first. — [CONTRIBUTING.md](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/CONTRIBUTING.md)
- Maintainers: only two contributors appear, firat-elbey (16 commits) and amirhormati (13). Skill frontmatter says `publisher: google`. The new repo has 99 stars, 11 forks and 3 open issues/PRs (as of 2026-11-21). — [GitHub API, repo contributors](https://github.com/open-knowledge-format/open-knowledge-format/graphs/contributors); [okf-generate SKILL.md](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/skills/okf-generate/SKILL.md)
- Google product integration: Knowledge Catalog ingests OKF. — [Google Cloud blog, v0.1](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing)
  - The repo's connector doc says the kcmd round-trip carries only seven frontmatter keys (`title`, `description`, `tags`, `resource`, `type`, `generated`, `sources`) plus the body.
  - It also says "Renames orphan catalog state… no merge story", "No entry-level access control", and "Scale is untested beyond the 14-file demo".
  — [connectors/gcp-knowledge-catalog.md](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/connectors/gcp-knowledge-catalog.md)
- Community adoption signals, found by GitHub search on 2026-11-21:
  - scaccogatto/okf-skills (455 stars), zosmaai/pi-llm-wiki (634 stars, "Native OKF v0.2"), openknowledge-sh/openknowledge CLI (78), W4G1/okf Rust toolkit (32), oak-invest/kiso ("Publishing engine, MCP server and Java library", 57), OWOX/models (91), GoogleCloudPlatform/knowledge-compiler (5 stars, v1.3.0, "Karpathy's compiled LLM-Wiki pattern", `x-kc-*` extensions). — [GitHub search](https://github.com/search?q=open+knowledge+format&type=repositories); [knowledge-compiler README](https://github.com/GoogleCloudPlatform/knowledge-compiler)
  - BundleDex says it lists "440+ OKF bundles". This is a self-reported number. — [awesome-okf](https://github.com/linyiru/awesome-okf)
- No adopters were named in the v0.3 announcement. — [Google Cloud blog, v0.3](https://cloud.google.com/blog/products/data-analytics/introducing-okf-v0-3)
- Effectiveness evidence is thin.
  - Google's launch materials "include no benchmarks".
  - In one homelab test (about 200 files, 44 questions), adding OKF frontmatter alone made no measurable difference. Restructuring to one concept per file plus an index roughly halved startup tokens (16,237 to 8,505) and cut cost by about 30%.
  - An SSRN RAG study found no retrieval gain once a methodology bug was fixed.
  — [dev.to analysis (secondary)](https://dev.to/amananandrai/googles-open-knowledge-format-from-a-karpathy-tweet-to-a-spec-and-what-the-evidence-says-ol8)

### Inferences
- OKF has real backing (Google Cloud product integration, an RFC-2119-style spec) and is moving fast: three versions in about five months. Expect more breaking minor releases before 1.0.
- Governance is nominally neutral but in practice Google-run: a Google CLA, two Google maintainers, and `publisher: google`.
- Most of OKF's value for us is the structure it imposes: small, linked, indexed concept files with trust metadata. It does not show retrieval-accuracy gains on its own.

### Gaps
- I found no independent production case studies with scale numbers. Star counts are popularity, not usage.
- The exact v0.2 release date conflicts between secondary sources, and I did not fetch the v0.2 Google blog post.

## 2. File/document structure (verbatim fields and examples)

### Takeaway
A bundle is a directory tree. Each concept is one `.md` file with YAML 1.2 frontmatter. The concept's ID is its path without `.md`. The only required key is `type`, and the type vocabulary is open. `index.md` and `log.md` are reserved filenames.

### Cited Findings
- Layout: an optional root `index.md` (directory listing and bundle metadata), an optional `log.md`, concept `.md` files, assets (non-.md files), and nested subdirectories, each with its own index. Git is "RECOMMENDED". — [SPEC.md §3](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
- Concept ID: "The path of the concept's file within the bundle, with the `.md` suffix removed." Paths are case-sensitive. — [SPEC.md §2, §6](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
- Which files are concepts:
  - A `.md` file whose frontmatter has a non-empty `type` is a concept.
  - A `.md` file without frontmatter or without `type` is skipped. This is how README.md, AGENTS.md and SKILL.md can coexist in a bundle.
  - Non-`.md` files are assets.
  - Dot-files are excluded.
  — [SPEC.md §3.2](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
- Frontmatter syntax rules:
  - The file must start with exactly `---`.
  - Frontmatter must be a YAML 1.2 core-schema mapping, with no duplicate keys.
  - Values that look like numbers or booleans SHOULD be quoted.
  - Custom YAML tags SHOULD NOT be used.
  - A producer that edits a file SHOULD NOT re-serialize values it did not change.
  — [SPEC.md §4](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
- Core keys:
  - `type` (REQUIRED). Examples: `BigQuery Table`, `API Endpoint`, `Metric`, `Playbook`, `Reference`, `Attested Computation`. "Consumers MUST accept unknown types."
  - Optional: `title`, `description` (one sentence), `resource` (a URI for the underlying asset), `tags` (a YAML list).
  - "A concept that has only `type` is fully conformant."
  — [SPEC.md §4.1](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
- Extensions: producers may add keys at any level, including inside `sources` entries, `generated`, and so on. Consumers MUST NOT reject unknown keys. A producer that edits a file "MUST keep the keys that it does not know". Producers SHOULD name their own keys `x-<producer>-<name>`, for example `x-acme-owner`. — [SPEC.md §4.1](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
- Body:
  - CommonMark plus GFM tables and `[^label]` footnotes.
  - Conventional headings: `# Schema`, `# Examples`, `# Computation`. No body section is required.
  — [SPEC.md §4.2](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
- Example concept, abbreviated from SPEC §4.4:
```yaml
---
type: Playbook
title: "Incident response: data freshness alert"
description: Steps to triage a freshness alert on the orders pipeline.
tags: [oncall, incident]
generated: { by: "human:ahormati", at: "2026-04-12T09:00:00Z" }
---
```
  — [SPEC.md §4.4](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
- Bundle metadata lives only in the root `index.md`: `okf_version: "0.3"`, `title`, `description` (which an agent uses "to select a bundle"), and `license` (SPDX or a path). Index files below the root have no frontmatter. "A producer that regenerates `index.md` MUST keep the existing frontmatter". — [SPEC.md §8, §8.1](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
- Index entry format: `* [Title](relative-url) - short description`, grouped under headings. Index files exist for "progressive disclosure". — [SPEC.md §8](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
- `log.md`:
  - Has no frontmatter.
  - Date headings MUST be `## YYYY-MM-DD`, newest first.
  - Entries are prose. A leading bold word such as `**Update**`, `**Creation**` or `**Deprecation**` is a convention, not a requirement.
  — [SPEC.md §9](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
- Example taxonomy: the example bundles organize concepts by directory (`tables/`, `metrics/`, `computations/`, `policies/`, `skills/`, `attesters/`, `references/joins/`, `datasets/`). The okf-generate skill suggests `datasets/`, `tables/`, `metrics/`, `computations/`, `policies/`, `playbooks/`, `references/`. — [repo tree](https://github.com/open-knowledge-format/open-knowledge-format/tree/main/bundles); [okf-generate SKILL.md](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/skills/okf-generate/SKILL.md)
- Conformance is deliberately weak. A bundle conforms if every frontmatter block parses as a YAML mapping and `index.md`/`log.md` follow §8/§9. — [SPEC.md §11.1](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
- Consumers MUST NOT reject a bundle for missing optional fields, unknown types, unknown keys, broken links, or missing `index.md`. — [SPEC.md §11.2](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)

### Inferences
- The format maps directly onto a "one fact or entity per file" curator design: directories serve as taxonomy, `index.md` serves as a routing table for agents, and `log.md` serves as a changelog.
- Because conformance is so weak, the factory needs its own stricter profile: required keys per `type` and a fixed type vocabulary, enforced in CI on top of `validate.py --strict`.

### Gaps
- The spec has no per-type schemas and no JSON Schema for frontmatter. I found no JSON Schema file in the repo tree.

## 3. Provenance, versioning, confidence, freshness, relationships, taxonomy, access control

### Takeaway
OKF is strongest on provenance (`sources` plus footnotes keyed by id), trust (`generated`/`verified`, from which consumers derive trust tiers) and lifecycle (`status`, `superseded_by`, `stale_after`).

It deliberately has:
- no confidence score;
- no typed relations;
- no per-concept version number (git provides history);
- no access control.

### Cited Findings
- **Provenance (`sources`)**:
  - Each entry has `resource` (REQUIRED: a URL, an in-bundle path, or a scope descriptor such as `all queries in BigQuery project X`).
  - Optional keys: `id`, `title`, and the credibility signals `author` (an actor), `usage_count` and `last_modified`.
  - A sibling key `usage_window: { from, to }` gives the period for each `usage_count`.
  - "OKF does not store a credibility score" because a score is "subjective… not portable… becomes stale".
  — [SPEC.md §5.1](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
- **Per-claim attribution**: `claim.[^ga4-schema]`, where the footnote label equals a `sources[].id`. It uses ids rather than positions "because agents rewrite these documents frequently". — [SPEC.md §5.1](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
- **Lineage**: there is no dedicated lineage field. An in-bundle `sources[].resource` is a graph edge, and credibility can propagate recursively. "Deeper lineage… is out of scope for v0.3." — [SPEC.md §5.1](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
- **`generated`**: `generated: { by: reference_agent/gemini-2.5-pro, at: "2026-06-20T22:53:05Z" }`.
  - `by` is REQUIRED in `generated`.
  - `at` is "the last meaningful change to the content". "A trivial edit (format, whitespace, link repair) does not change `generated.at`."
  — [SPEC.md §5.2](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
- **`verified`**: a list of `{ by, at }` events, both keys REQUIRED. A bare mapping is allowed and counts as one event. — [SPEC.md §5.2](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
- **Trust tiers**: an event is "current" when its `at` >= `generated.at`.
  - No current event: **unverified**.
  - Current events only from non-`human:` actors: **machine-confirmed**.
  - Any current `human:<id>` event: **human-reviewed**.
  - "When an agent rewrites a concept after a human review… the concept is not human-reviewed until a human confirms it again."
  - "Trust tiers are advisory signals, not access control."
  — [SPEC.md §5.3](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
- **Actors**: `<producer>/<version>` for tools, or `<scheme>:<id>` with the schemes `human:`, `team:` and `process:`. Unknown schemes count as non-human. A `team:` verifier yields only machine-confirmed. — [SPEC.md §7](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
- **Lifecycle (`status`)**:
  - `status: draft | stable | deprecated`. If absent, the status is `stable`.
  - An unknown value is "not `stable`" and is excluded by current-knowledge filters.
  - `superseded_by` is one path to the replacement concept, meaningful only with `deprecated`.
  - To retire, rename or move a concept, keep the file (or leave a deprecated stub at the old path) with `superseded_by`.
  — [SPEC.md §5.4](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
- **Freshness**:
  - `stale_after: "2026-09-23T00:00:00Z"` is an absolute instant, not a TTL. Stale means "must check the content again", not false.
  - "Omit `stale_after` when no review date is known. Do not invent one."
  - An unparseable value is never fresh.
  — [SPEC.md §5.5](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
- **Timestamps**: RFC 3339 date-time with an offset, or a full-date meaning 00:00 UTC. The timestamp keys are `generated.at`, `verified[].at`, `stale_after`, `sources[].last_modified`, `usage_window.from` and `usage_window.to`. — [SPEC.md §5](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
- **Verification vs attestation**: `verified` confirms that the *definition* still matches policy (per document, slow, recorded in the bundle). Attestation confirms that a single *run* used the sanctioned computation (runtime, not recorded in the bundle). — [SPEC.md §10.6](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
- **Attested Computation** (`type: Attested Computation`):
  - `runtime` (REQUIRED).
  - `parameters`: a list of `{ name, type, required }`.
  - `computation`: a path, or else the first fenced block under a `Computation` heading.
  - `executor: { resource, receipt: [...] }` and `attester: { resource }`, where the attester is deterministic code with no LLM that returns `{ok, reason}`.
  - "The agent MUST NOT write or edit the computation."
  — [SPEC.md §10.2–10.5](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
- **Relationships**:
  - A link "asserts an untyped, directed relationship". Only the directory tree implies parent/child structure.
  - `[[wikilinks]]` are not OKF links.
  - Broken links MUST be accepted ("knowledge that nobody has written yet").
  - The bundle graph consists of links plus path fields that resolve to concepts.
  — [SPEC.md §2, §6.1, §6.4](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
- **Link resolution**: a value with a scheme is a URL. A value starting with `/` resolves from the bundle root. Anything else resolves from the containing file's directory. Values must be percent-encoded. — [SPEC.md §6](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
- **Taxonomy**: `tags` is the only cross-cutting categorization. There is no tag-index file format. Type values are not centrally registered. — [SPEC.md §3.1, §4.1](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
- **Versioning of content**: there is no per-concept version or revision field. Git is the RECOMMENDED distribution for "history, attribution, and diffs". — [SPEC.md §3](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
  - Open proposals in the old repo: optional `revision` and `digest` fields on `sources` entries (#46, #45), and a "`revised` or `edited` key" (#28, 16 comments). — [GCP repo issues](https://github.com/GoogleCloudPlatform/open-knowledge-format/issues)
- **Access control**:
  - None in the spec. Trust tiers are "not access control". — [SPEC.md §5.3](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
  - The Knowledge Catalog connector has "No entry-level access control". — [connector doc](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/connectors/gcp-knowledge-catalog.md)
  - Open issue #32: "Partial visibility of sources when a bundle is read across a trust boundary — drop, redact, or reveal?" — [GCP repo issues](https://github.com/GoogleCloudPlatform/open-knowledge-format/issues)
- **Deferred items**: typed relationships, validity windows, source-drift signals, a `refuted` verification event, and the attestation runtime protocol. "Use extension keys until the community agrees on one form." — [SPEC.md §12.2](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)

### Inferences
- Trust-tier semantics fit a curator agent well. Agent rewrites automatically demote human-reviewed content to machine-confirmed. That gives a natural, mechanical signal that a concept needs re-review.
- Confidence has to be an extension key, for example `x-kf-confidence`, or derived from source signals.
- Access control has to come from repository or directory partitioning: separate bundles per audience, filesystem or git permissions, or a serving layer.

### Gaps
- The spec does not address multi-tenant permissions, PII handling, or redaction.

## 4. Tooling

### Takeaway
The official tooling is:
- a Python validator;
- two Agent Skills (okf-generate and okf-consume) installable in Claude Code, Codex and Antigravity;
- a proof-of-concept Google ADK + Gemini reference agent, with BigQuery and web passes;
- a static graph viewer;
- a Knowledge Catalog push/pull connector.

Community tools add MCP servers, linters, and CLIs in Rust and Java.

### Cited Findings
- **Validator**: `python3 scripts/validate.py <bundle-root>` with `--json` and `--strict`. It needs Python 3.9+ and PyYAML. — [okf-generate SKILL.md](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/skills/okf-generate/SKILL.md)
  - Error codes include E002 (frontmatter not a YAML mapping), E004 (frontmatter in a non-root index), E005/E006 (log.md format), and E007 (duplicate keys).
  - Warning codes include W108 (footnote has no matching source id), W110 (tags not a list), W111 (Attested Computation without runtime), W115 (broken link), W120 (not a concept), and W125 (missing okf_version).
  - Info codes include I201 (stale) and I204 (no current verification).
  — [validate.py](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/skills/okf-generate/scripts/validate.py)
- **okf-generate skill rules**:
  - "Write only what a source supports".
  - Set `generated.by` to your own actor (`claude-code/<model>`).
  - "Do not add a `verified` entry to content that you generated in this run". Add a `human:<id>` entry only when that person confirmed the content and gave their id ("Never infer an id from… git configuration").
  - "Never write the computation of an Attested Computation".
  - Keep unknown keys and `verified` history.
  - Show the planned tree to the user when writing more than 10 files.
  — [okf-generate SKILL.md](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/skills/okf-generate/SKILL.md)
- **okf-consume skill**:
  - Uses `scripts/scan.py` with the filters `--type`, `--tag`, `--grep`, `--current`, `--stale`, `--deprecated` and `--unverified`.
  - Reports trust tier, status and staleness for every concept it uses.
  — [okf-consume SKILL.md](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/skills/okf-consume/SKILL.md)
- **Install**: `/plugin marketplace add open-knowledge-format/open-knowledge-format`, then `/plugin install okf@open-knowledge-format` (Claude Code). The Codex and Antigravity equivalents are also in the README. — [README](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/README.md)
- **Reference agent**: `python -m reference_agent enrich --source bq --dataset … --web-seed-file … --out …`.
  - It runs a BigQuery-metadata pass, then a web-crawl pass with a `--web-max-pages` cap and an allowed-hosts filter.
  - It depends on `google-adk>=2.0`.
  - `visualize` renders a single-file Cytoscape.js `viz.html`.
  — [README](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/README.md); [pyproject.toml](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/pyproject.toml)
- **Knowledge Catalog connector**: `kcmd` push/pull. "Treat git as authoritative: push on merge, don't pull into a tracked bundle." — [connector doc](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/connectors/gcp-knowledge-catalog.md)
- **Community MCP and linting**:
  - okft: `okft lint` plus `okft serve`, an MCP server with the tools `okf_overview`, `okf_read`, `okf_search` and `okf_list`. It targets OKF v0.1 and is Apache-2.0. — [okft repo](https://github.com/PoorvaJ-WW/okft)
  - knowledge-compiler: `vault-lint`, `vault-query` (BM25), `vault-graph`, and `--migrate-v03`. — [knowledge-compiler](https://github.com/GoogleCloudPlatform/knowledge-compiler)
  - kiso: Java library and MCP server. — [oak-invest/kiso](https://github.com/oak-invest/kiso)
- The awesome-okf list says Google's Knowledge Catalog enrichment toolbox includes "a server that exposes a Markdown fileset as an MCP server". This is a secondary source, and I did not verify it. — [awesome-okf](https://github.com/linyiru/awesome-okf)

### Inferences
- For a Claude-based curator, the official okf-generate and okf-consume skills plus `validate.py --strict` in CI are a ready-made baseline.
- Community MCP servers lag the spec (many target v0.1/v0.2), so expect to write or patch a v0.3-aware MCP server.

### Gaps
- There is no official MCP server in the OKF repo, and no official SDK on PyPI or npm. `reference-agent` is a local package only.

## 5. Gaps and limitations for an agent-curation workflow

### Takeaway
OKF covers lifecycle (`draft`/`stable`/`deprecated`, `superseded_by`), re-review triggers (verification currency, `stale_after`) and a consumer-side conflict precedence. It does not cover:
- review workflow states beyond `draft`;
- typed contradiction or support relations;
- refutation;
- multi-writer merge semantics;
- confidence;
- access control.

### Cited Findings
- **Conflict resolution**: the okf-consume skill (not the spec) defines a precedence, where the first difference decides:
  1. status (a current concept beats a deprecated one or one with an unknown status);
  2. trust tier;
  3. freshness;
  4. the later `generated.at`.

  The consumer then reports the conflict, and shows both answers if nothing decides. — [okf-consume trust.md](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/skills/okf-consume/references/trust.md)
- **Review status**: the only states are `draft` ("Not yet reviewed") and `stable`. Review evidence is the `verified` events. There is no proposed / in-review / rejected state. — [SPEC.md §5.4](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
- **Deprecation**: keep the file, set `status: deprecated`, and add `superseded_by`. — [SPEC.md §5.4](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
  - The example `metrics/gross-margin-legacy.md` keeps its definition and `verified` history, adds a `# Deprecated` body section, and `log.md` records the deprecation. — [acme_retail bundle](https://github.com/open-knowledge-format/open-knowledge-format/tree/main/bundles/acme_retail)
- **Typed relations / contradictions**: deferred in the spec (§12.2). — [SPEC.md §12.2](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
  - Open issue #11 proposes `relations: [{ type: supported_by|contradicted_by|qualified_by, target, kind: conflict|change_over_time|exception|disagreement, evidence, note }]`. — [issue #11](https://github.com/open-knowledge-format/open-knowledge-format/issues/11)
  - Old-repo issue #30, "Evolve OKF into a machine-readable knowledge graph using typed relationships", has 10 comments. — [GCP repo issues](https://github.com/GoogleCloudPlatform/open-knowledge-format/issues)
- **Self-verification loophole**: old-repo #60 says "a `verified` event by the same producer as `generated.by` yields 'machine-confirmed'; consider discounting self-verification". — [GCP repo issues](https://github.com/GoogleCloudPlatform/open-knowledge-format/issues)
- **Parallel or partial production**: old-repo #26 says "reserved filenames collide on merge, and a regenerated bundle-root `index.md` may drop `okf_version`". This matters for multiple curator agents writing in parallel. — [GCP repo issues](https://github.com/GoogleCloudPlatform/open-knowledge-format/issues)
- **Other open proposals relevant to curation** (old repo):
  - `generated.with_skills` (#64);
  - `priority`/`scope` routing hints (#52);
  - a `sections` registry for sub-file addressing (#51);
  - a `language` field (#49).
  — [GCP repo issues](https://github.com/GoogleCloudPlatform/open-knowledge-format/issues)
- **Catalog sync**: "Renames orphan catalog state, deletes leave entries behind, and there is no merge story." — [connector doc](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/connectors/gcp-knowledge-catalog.md)
- **Third-party critique**: no access control, advisory-only freshness, shallow validation, and a young ecosystem. — [dev.to (secondary)](https://dev.to/amananandrai/googles-open-knowledge-format-from-a-karpathy-tweet-to-a-spec-and-what-the-evidence-says-ol8)

### Inferences
- A knowledge factory can stay OKF-conformant if it adds a namespaced extension profile:
  - `x-kf-review: proposed|in_review|approved|rejected`;
  - `x-kf-owner`;
  - `x-kf-confidence`;
  - `x-kf-relations` (modelled on the issue #11 shape, for forward compatibility);
  - `x-kf-refuted`.
- Put the curator workflow in git PRs (branch, change, `validate.py`, human review, merge), and write the human `verified` event at merge time.
- Run per-bundle writers, or serialize regeneration of `index.md`/`log.md`, to avoid the merge collisions in #26.

### Gaps
- No spec guidance exists on concurrent agent writers or locking.

## 6. Comparison with alternatives

### Takeaway
OKF is essentially "Karpathy's LLM wiki / an Obsidian vault plus a standardized trust and lifecycle frontmatter vocabulary". Compared with:
- **llms.txt**: OKF is richer, and per-concept rather than per-site.
- **AGENTS.md/skills**: OKF is complementary; those files can live inside a bundle as non-concepts.
- **JSON-LD/RDF and knowledge graphs**: OKF is much less semantically expressive, since links are untyped.

### Cited Findings
- **Karpathy LLM wiki**: OKF "formalizes the LLM-wiki pattern into a portable, interoperable format". The blog lists Obsidian vaults wired to agents, AGENTS.md/CLAUDE.md files, index.md/log.md repos and "metadata as code" repositories as bespoke, non-interoperating precedents. — [Google Cloud blog, v0.1](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing)
- **Obsidian**:
  - OKF ships no UI and expects Obsidian, Notion, MkDocs, Hugo and Jekyll to render bundles. — [README](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/README.md)
  - `[[wikilinks]]` "are not links in OKF", so Obsidian-style vaults need link conversion (knowledge-compiler offers `--portable-links`). — [SPEC.md §6.1](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md); [knowledge-compiler](https://github.com/GoogleCloudPlatform/knowledge-compiler)
- **AGENTS.md / SKILL.md / README.md**: these can sit inside a bundle without breaking it, because files without `type` are skipped. Executors can be "A Skill, a script, or a container". — [Google Cloud blog, v0.3](https://cloud.google.com/blog/products/data-analytics/introducing-okf-v0-3); [SPEC.md §10.2](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
- **Domain schemas (Avro/Protobuf/OpenAPI)**: OKF "*refers to* them. It does not replace them." The `usecases/` folder hosts pairing guides. — [SPEC.md §1](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md); [README](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/README.md)
- **Knowledge graphs / RDF**:
  - Typed relationships are deferred, and links are untyped. — [SPEC.md §12.2](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
  - Hacker News commenters argued "You can't represent knowledge well without a graph format showing labeled relationships between entities", raised RDF/OWL as prior art, and criticized YAML fragility. — [HN discussion](https://news.ycombinator.com/item?id=48517735)
- **llms.txt, MCP, ARD**: awesome-okf lists llms.txt (a per-site Markdown file for LLMs), MCP (a transport) and Agentic Resource Discovery (ARD: "OKF packages knowledge; ARD finds it"). — [awesome-okf](https://github.com/linyiru/awesome-okf)

### Inferences
- If you need machine-reasoned typed relations or ontologies, use OKF as the authored source of truth and compile a graph (Neo4j/RDF) from frontmatter and links as a derived index. Don't adopt JSON-LD as primary storage.
- llms.txt and OKF are compatible: an llms.txt can point at the bundle's root `index.md`.
- For an org knowledge factory, OKF's advantages over plain Obsidian or Karpathy wikis are:
  - spec-defined trust tiers;
  - deprecation forwarding;
  - staleness;
  - per-claim citations;
  - a validator and official agent skills.

  These are exactly the curation controls a bare wiki lacks.

### Gaps
- I found no formal, spec-authored comparison with JSON-LD/schema.org or llms.txt. The comparisons above are mine or come from community sources.
