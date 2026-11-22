# Engineering Patterns for a Production Curator-Agent Pipeline (files + git-backed knowledge base)

Scope note: research conducted 2026-11-21. Primary sources preferred (LangChain docs/blog, Anthropic engineering, Claude Code docs, GitHub docs, OKF spec, arXiv). Where only vendor/secondary sources were available this is flagged.

## Context: what Harrison Chase's "How to build a knowledge factory" actually prescribes (anchor for the design)

### Takeaway
The post (Nov 21, 2026) defines a loop of (1) consumer agents flagging gaps via a tool, (2) a scheduled background curator agent reading flags, agent traces and raw sources, and (3) a storage layer he calls "the least important thing" (OKF in LangSmith Context Hub is one named option). It does not prescribe pipeline stages, review gates, or eval methods, so those must be designed from other sources below.

### Cited Findings
- Author/date: Harrison Chase, LangChain blog, published 2026-11-21; premise "the missing bit is not better models, it's not just more context - it's better knowledge." — [LangChain blog: How to build a knowledge factory](https://www.langchain.com/blog/knowledge-factory)
- Three knowledge types: Skills (how to do work), Domain knowledge (how the business works; "goes stale slowly but is often incomplete or wrong"), Data-access guidance (where current info lives; advises against duplicating sources of truth that are already complete and current). — [LangChain blog](https://www.langchain.com/blog/knowledge-factory)
- Components: Flagging (agents "at a minimum report what is wrong" via a tool, optionally suggesting a correction); Curator agent (runs on a schedule, reads Notion/Slack, reviews agent traces to codify patterns into skills, works through flags); Storage (skill-format files in GitHub, a Notion page, OKF format in LangSmith Context Hub, or a Neo4j graph). — [LangChain blog](https://www.langchain.com/blog/knowledge-factory)
- Consumer agents should NOT maintain knowledge themselves: it "will cause it to become unruly and full of contradictions." — [LangChain blog](https://www.langchain.com/blog/knowledge-factory)
- Worked example: agent notices a renamed BigQuery column, works around it and flags it; a finance lead corrects formatting in a live session; overnight the curator reads the flag + trace and updates two skills (data-fetching and report-drafting). — [LangChain blog](https://www.langchain.com/blog/knowledge-factory)
- The post does not describe a formal approval gate before curator changes take effect. — [LangChain blog](https://www.langchain.com/blog/knowledge-factory)
- Recommends starting with "one recurring workflow"; "The goal isn't to document everything before agents can start working." — [LangChain blog](https://www.langchain.com/blog/knowledge-factory)
- Precursor post "Wiki Memory" (Chase, 2026-06-30): raw sources (logs, notes, code, docs, Slack, transcripts) are too noisy; an agent compresses them into a persistent, structured, inspectable file-based layer; files win because they are "inspectable, editable, versionable"; wikis suit durable domain knowledge but are a poor fit for short-term conversation state, user preferences, or high-frequency event logs. Examples: DeepWiki (Cognition), AutoWiki (Factory), LLM Wiki (Karpathy). — [LangChain blog: Wiki Memory](https://www.langchain.com/blog/wiki-memory)
- "The hardest part of the intelligence layer is figuring out what to remember"; memory fails at both extremes (nothing vs. overly granular). — [LangChain: New context engineering challenges in late 2026](https://www.langchain.com/blog/context-engineering-challenges-late-2026)

### Inferences
- The design gap left by the post (review gates, dedup/conflict handling, evals, governance) is exactly where git/PR workflows and OKF trust fields fit naturally.

### Gaps
- The X post itself (x.com/hwchase17/status/2124181216719151585) was not fetched directly (X blocks automated fetches); the blog version was used. The fetched URL was /blog/knowledge-factory (the /blog/how-to-build-a-knowledge-factory URL returned 404).

## Pipeline stages: connectors, change detection, extraction, dedup/merge, conflict detection, summarization, linking, indexing

### Takeaway
The best-documented reference pattern is Karpathy's "LLM Wiki" (raw/ immutable sources -> wiki/ LLM-maintained pages -> schema doc; operations ingest/query/lint with index.md and log.md), plus memory-system techniques for the hard parts: Mem0-style ADD/UPDATE/DELETE/NOOP reconciliation against retrieved neighbors, Graphiti-style bi-temporal invalidation instead of deletion, and conservative entity resolution (prefer creating a duplicate over a bad merge).

### Cited Findings
- LLM Wiki (gist created 2026-04-04): three layers - raw sources (immutable; LLM reads but never edits), the wiki (LLM-generated summaries, entity/concept pages, comparisons, overview), and the schema (CLAUDE.md/AGENTS.md defining structure, conventions, workflows). — [Karpathy LLM Wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- Ingest: read source, write summary page, update index, revise related entity/concept pages, log change; "one source may touch 10 to 15 pages." Query: answer with citations, file useful answers back into wiki. Lint: periodic checks for contradictions, stale claims, orphan pages, missing cross-references, gaps. — [Karpathy gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- index.md (catalog: link + one-line summary per page, read first on queries) works at ~100 sources / hundreds of pages without embeddings; log.md is append-only with a parseable heading prefix (date, operation, title). Directories raw/ and wiki/, raw/assets/ for attachments; whole wiki is a git repo. — [Karpathy gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- Mem0 reconciliation: for each candidate fact, retrieve the most similar existing memories, then an LLM chooses ADD (no equivalent exists), UPDATE (complements/corrects/refreshes), DELETE (contradicted), or NOOP; graph variant Mem0g marks conflicting relationships invalid rather than deleting. — [Dwarves Memo: Mem0 breakdown](https://memo.d.foundation/breakdown/mem0) (secondary source summarizing the Mem0 paper)
- Graphiti: data ingested as discrete "episodes" (preserves provenance); bi-temporal edges; contradictions handled by "temporal edge invalidation" preserving history; hybrid search = vector + BM25 + graph traversal (no LLM reranking). — [Graphiti overview (Zep docs)](https://help.getzep.com/graphiti/getting-started/overview)
- Zep paper separates event-time validity from ingestion-time transactional lifetimes; outdated edges get an invalid_at timestamp rather than deletion. — [Zep paper on emergentmind](https://www.emergentmind.com/papers/2501.13956) (arXiv 2501.13956; via search summary)
- Hindsight entity resolution: weighted score over name similarity, co-occurrence and recency with a 0.6 merge threshold; creates a new entity when unsure "since a duplicate is easier to recover from than a bad merge"; v0.8.0 reportedly cut duplicate observations from ~30% to ~1%. — [Hindsight blog: Entity Resolution in Agent Memory](https://hindsight.vectorize.io/blog/2026/06/29/entity-resolution-agent-memory) (vendor blog, via search summary)
- Contextual chunk enrichment for indexing: prepend 50-100 tokens of LLM-generated document context to each chunk before embedding and BM25; failure rate (1-recall@20) 5.7% baseline -> 3.7% contextual embeddings (-35%) -> 2.9% + contextual BM25 (-49%) -> 1.9% with reranking (-67%); ~$1.02 per million document tokens with prompt caching. — [Anthropic: Contextual Retrieval](https://www.anthropic.com/news/contextual-retrieval)
- Change detection / event-driven refresh: vendor guidance recommends lineage tracking that detects upstream source changes and triggers re-certification. — [Atlan: LLM KB freshness](https://atlan.com/know/llm-knowledge-base-freshness-scoring/) (vendor blog)

### Inferences
- A concrete stage list for implementation: connectors -> raw/ snapshot (immutable, content-hashed) -> change detection (hash/updated_at diff, webhook or cursor) -> claim/entity extraction into a staging area -> retrieve-neighbors + LLM reconcile (ADD/UPDATE/DEPRECATE/NOOP) -> conflict detection (new claim contradicts current claim => mark old superseded, or open a "conflict" review item) -> page synthesis -> link + index regeneration -> PR.
- Mapping to OKF: "DELETE" should become status: deprecated + superseded_by (OKF) rather than file removal, mirroring Graphiti invalidation; history is retained in git.
- Treat curator outputs as bulk multi-page diffs (10-15 pages per source per Karpathy), which argues for one PR per ingest batch with a generated summary.

### Gaps
- No primary-source benchmark found comparing dedup/merge strategies for markdown-page knowledge bases specifically (memory-system numbers are for vector/graph memory).
- Hindsight's "How we solved memory conflicts" post content could not be retrieved.
- No authoritative source found on connector frameworks for Slack/tickets/transcripts specifically for this use; not researched in depth.

## Git-as-database: PR-based review of agent edits, CI validation, branch protection

### Takeaway
GitHub provides all needed controls: agents (Claude Code GitHub Action on a cron, or Copilot cloud agent) work on their own branch and open PRs; rulesets enforce required approvals, CODEOWNERS review, status checks (schema lint, link check), signed commits and path restrictions; Copilot's mitigations (single-branch push, requester cannot self-approve, workflows don't run until approved) are a good template for curator-agent guardrails.

### Cited Findings
- claude-code-action@v1 runs Claude Code in GitHub Actions; responds to @claude or runs a prompt on any event incl. schedule; built on the Claude Agent SDK. — [Claude Code docs: GitHub Actions](https://code.claude.com/docs/en/github-actions)
- Scheduled example from docs (verbatim): ```yaml
on:
  schedule:
    - cron: "0 9 * * *"
jobs:
  report:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      issues: read
      id-token: write
    steps:
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: "Generate a summary of yesterday's commits and open issues"
          claude_args: |
            --model claude-opus-5-5
            --allowedTools "mcp__github__list_commits,mcp__github__list_issues"
``` — [Claude Code docs](https://code.claude.com/docs/en/github-actions)
- GitHub App permissions relied on: Contents RW, Issues RW, Pull requests RW; secrets ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN; CLAUDE.md in repo root defines rules Claude follows when creating PRs. Review workflow can run a plugin skill (e.g. code-review) with --comment to post inline comments; Claude skips draft/closed PRs. — [Claude Code docs](https://code.claude.com/docs/en/github-actions)
- Copilot cloud agent protections: pushes only to a single branch (new copilot/ branch unless started from an existing PR), branch protections and required checks still apply; only users with write access can trigger; "workflows are not triggered until Copilot cloud agent's code is reviewed"; internet access firewalled; requester cannot approve the agent's PR; commits are signed and co-authored by the requesting developer. — [GitHub Docs: Risks and mitigations](https://docs.github.com/en/copilot/concepts/agents/coding-agent/risks-and-mitigations)
- Copilot coding agent: one branch and one PR per task; Actions-based sessions stop after 59 minutes; rulesets can block it unless granted bypass. — [GitHub Docs: About coding agent](https://docs.github.com/en/copilot/concepts/agents/coding-agent/about-coding-agent)
- Rulesets: require PR; 0-10 required approvals; dismiss stale approvals on new commits or require approval from someone other than last pusher; require code owner review; required status checks (strict/loose, can restrict to a specific GitHub App); require signed commits; linear history; bypass list by role/team/App; restrict file paths (fnmatch, up to 200 entries). — [GitHub Docs: Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
- CODEOWNERS in .github/, root, or docs/; gitignore-style patterns; last matching pattern wins; any one listed owner satisfies; protect /.github/CODEOWNERS itself; must be on the PR base branch. — [GitHub Docs: About code owners](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)
- Common docs CI pattern: markdownlint-cli2 + lychee link checker, plus weekly scheduled link checks; one example pins lychee 0.24.2 with SHA-256 verification. — [example PRs found via search, e.g. selfkin/standards#61](https://github.com/selfkin/standards/pull/61) (community repos; pattern evidence only)
- OKF ships a validator script: skills/okf-generate/scripts/validate.py. — [OKF repo](https://github.com/open-knowledge-format/open-knowledge-format)

### Inferences
- Recommended layout: curator bot opens PRs from curator/<run-id> branches; ruleset on main requires (a) status checks: OKF validate.py + JSON-Schema frontmatter lint + lychee + PII scan + LLM-judge check, (b) CODEOWNERS approval per domain directory (e.g. /finance/ @org/finance-owners), (c) dismiss stale approvals, (d) the bot is NOT on the bypass list; low-risk paths (e.g. typo/links/index regeneration) can be auto-merged via a separate ruleset or merge automation.
- Because OKF tolerates broken links (consumers MUST accept them), link-checking is a producer-side policy choice in CI, not a spec requirement.

### Gaps
- Did not find a primary source for a JSON-Schema-based frontmatter linter tool commonly used in CI (search returned almost nothing on frontmatter schema validation specifically).
- Merge queue specifics were not covered by the fetched rulesets page.

## Agent frameworks: LangGraph/deepagents, LangSmith evals, Claude Agent SDK, MCP

### Takeaway
deepagents gives the curator a virtual filesystem with pluggable backends (route /kb/ to a real git checkout, scratch to state, memories to a store, or OKF bundles to LangSmith Context Hub with commit-per-write), per-tool human-in-the-loop interrupts, and path-level permissions; the Claude Agent SDK gives equivalent control via hooks (PreToolUse deny/modify), permissions, subagents, and skills; Agent Skills (SKILL.md) are the natural format for the "skills" knowledge type.

### Cited Findings
- deepagents backends: StateBackend (thread-scoped scratch, default), FilesystemBackend(root_dir, virtual_mode=True) (real files; virtual_mode blocks .., ~, absolute paths; can use ripgrep for grep), LocalShellBackend (adds execute, unsandboxed), StoreBackend(namespace=lambda rt: ...) (LangGraph BaseStore, cross-thread; pass store to create_deep_agent), ContextHubBackend("my-agent") (LangSmith Context Hub; each write creates a Hub commit with parent_commit; on conflict re-pull and retry), CompositeBackend(default=StateBackend(), routes={"/memories/": StoreBackend(...)}) with longest-prefix routing; sandbox backends add execute. — [LangChain docs: deepagents Backends](https://docs.langchain.com/oss/python/deepagents/backends)
- deepagents permissions example: permissions=[FilesystemPermission(operations=["write"], paths=["/policies/**"], mode="deny")], evaluated before the backend; policy hooks by subclassing/wrapping a backend. — [deepagents Backends](https://docs.langchain.com/oss/python/deepagents/backends)
- Warning: FilesystemBackend grants real read/write; virtual_mode gives no protection once shell access is enabled. — [deepagents Backends](https://docs.langchain.com/oss/python/deepagents/backends)
- HITL: interrupt_on={"remove_file": True, "fetch_file": False, "notify_email": {"allowed_decisions": ["approve","reject"]}}; decisions approve/edit/reject/respond; checkpointer required; resume with agent.invoke(Command(resume={"decisions": decisions}), config=config) using the same thread_id; each subagent can override interrupt_on; tools can call interrupt() directly. — [LangChain docs: deepagents human-in-the-loop](https://docs.langchain.com/oss/python/deepagents/human-in-the-loop)
- LangGraph stores persist application data across threads; compile with graph = builder.compile(checkpointer=checkpointer, store=store). — [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- LangSmith evaluation: offline (datasets, reference outputs; regression tests/backtesting) vs online (on tracing projects via automated rules; production monitoring); evaluator types human (annotation queues), code, LLM-as-judge (reference-free or reference-based), decision model, pairwise; feedback keys key/score/value/comment; pytest and Vitest/Jest integrations; annotation queues export to datasets. — [LangSmith Evaluation concepts](https://docs.langchain.com/langsmith/evaluation-concepts)
- Claude Agent SDK exposes Claude Code's built-in tools, hooks, subagents, MCP, permissions, sessions (resume/fork), skills/commands/memory loaded from .claude/, plugins; Python and TypeScript. — [Claude Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview)
- Hooks: events PreToolUse, PostToolUse, subagent start/stop, etc.; matcher like "Write|Edit"; callback returns hookSpecificOutput with permissionDecision "deny" and reason, or modifies inputs; use cases include blocking unauthorized file access, audit logging, sanitizing data, requiring human approval. Example registers ClaudeAgentOptions(hooks={"PreToolUse": [HookMatcher(matcher="Write|Edit", hooks=[protect_env_files])]}). — [Claude Agent SDK: Hooks](https://code.claude.com/docs/en/agent-sdk/hooks)
- Agent Skills (2025-10-16): directory with SKILL.md whose YAML frontmatter requires name and description; progressive disclosure (only name+description preloaded; full SKILL.md then linked files loaded on demand); bundled scripts run deterministically without loading into context; install only from trusted sources. — [Anthropic: Equipping agents with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- MCP serving example: Basic Memory serves markdown files (frontmatter title/type/permalink/tags; "[category]" observations; typed [[relations]]) over MCP with tools bm_write/bm_read/bm_edit/bm_move/bm_delete, bm_search/bm_list/bm_find, bm_context, bm_schema_infer/validate/diff; tools carry read-only/destructive/idempotent hints; files are source of truth with a SQLite (or Postgres) index; hybrid FTS + FastEmbed vector search, optional cross-encoder reranker. — [basic-memory GitHub](https://github.com/basicmachines-co/basic-memory)

### Inferences
- Curator implementation option A (LangChain stack): create_deep_agent with CompositeBackend(default=StateBackend(), routes={"/kb/": FilesystemBackend(root_dir=<git worktree>, virtual_mode=True), "/raw/": read-only backend}), FilesystemPermission deny on writes to /raw/** and governance paths, subagents per stage (extractor, reconciler, page-writer, linter), interrupt_on for delete/deprecate tools, run as a scheduled deep agent, and push a branch + PR at the end. Option B (Anthropic stack): claude-code-action on cron or Agent SDK worker with PreToolUse hooks enforcing path policy and --allowedTools allowlist.
- For consumer-agent serving, an MCP server exposing read-only search/read/flag tools (a "flag_knowledge_issue" tool implements Chase's flagging component) over the OKF bundle mirrors Basic Memory's design; keep write tools off the consumer-facing server.

### Gaps
- Did not retrieve primary docs for LangSmith "scheduled managed deep agents" or Context Hub APIs beyond the ContextHubBackend description.
- LangGraph Store semantic-search config (index/embed/dims) was not on the fetched page (lives in the Stores guide, not fetched).

## Retrieval/serving: hybrid search, agentic file navigation vs vector RAG, llms.txt indexes

### Takeaway
Evidence favors a hybrid: give agents an index file plus grep/ls/read for just-in-time navigation (Anthropic's recommendation and Claude Code's practice), add BM25+vector (contextualized, reranked) when the corpus outgrows an index; recent arXiv work shows the grep-vs-vector winner depends on harness and delivery mode, so evaluate retrieval inside the actual consumer harness.

### Cited Findings
- Anthropic (2025-09-29): agents should "dynamically load data into context at runtime using tools," keep lightweight references (paths), use progressive disclosure; hybrid strategy - "retrieving some data up front for speed, and pursuing further autonomous exploration at its discretion"; Claude Code loads CLAUDE.md up front and uses glob/grep just-in-time; sub-agents explore with tens of thousands of tokens but return ~1,000-2,000 tokens; structured note-taking (e.g. NOTES.md) persisted outside context. — [Anthropic: Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- "Is Grep All You Need?" (arXiv 2605.15184, 2026-05-14, PwC authors; 116-question LongMemEval-S subset): with inline results grep beat vector for all 10 harness-model pairs (largest 86.2% vs 62.9%, narrowest Claude Code+Opus 4.6 76.7% vs 75.0%); with file-based/programmatic delivery vector won 5 of 10; harness swap moved Opus 4.6 from 93.1% to 76.7%, as large as swapping retrievers; authors limit claims to conversational memory QA and suggest hybrid policies. — [arXiv 2605.15184](https://arxiv.org/html/2605.15184v1)
- Secondhand claim that Claude Code dropped an early local vector-DB RAG approach because agentic search worked better (attributed to Boris Cherny on HN) - not verified from a primary source. — [vadim.blog](https://vadim.blog/claude-code-no-indexing/) (secondary)
- llms.txt: H1 project name is the only required element; optional blockquote summary, detail sections, H2 file-list sections of [name](url): notes, and an "Optional" H2 for skippable links; markdown variants at page.md / page.html.md; discovery via rel="alternate" type="text/markdown" and rel="describedby"; file at /llms.txt or any subpath, most specific applies. The fetched spec page does not define llms-full.txt. — [llmstxt.org](https://llmstxt.org/)
- OKF index.md: optional per directory, auto-generated for progressive disclosure; bulleted links grouped under headings, entries SHOULD include the concept's description; only bundle-root index.md may have frontmatter (okf_version, title, description, license); regeneration MUST preserve root frontmatter. — [OKF SPEC.md](https://raw.githubusercontent.com/open-knowledge-format/open-knowledge-format/main/SPEC.md)
- Graphiti hybrid = vector + BM25 + graph traversal; Basic Memory hybrid = FTS + vector + optional cross-encoder; contextual retrieval reduces retrieval failures by up to 67%. — [Graphiti](https://help.getzep.com/graphiti/getting-started/overview); [basic-memory](https://github.com/basicmachines-co/basic-memory); [Anthropic Contextual Retrieval](https://www.anthropic.com/news/contextual-retrieval)

### Inferences
- OKF's index.md is structurally very close to llms.txt (headings + link lists with descriptions); a CI step can emit /llms.txt from the bundle-root index for external consumers at near-zero cost.
- Recommended serving tiers: (1) index.md + grep/read for agents with file access; (2) MCP server with search (BM25+vector over contextualized chunks) for remote agents; (3) SKILL.md packaging for procedural knowledge.

### Gaps
- No head-to-head benchmark on curated markdown KBs (vs. code or conversations) was found.

## Quality: provenance/citation, confidence, freshness/TTL, KB quality metrics, LLM-as-judge for edits

### Takeaway
OKF v0.3 already encodes most quality metadata natively: sources[] with ids for per-claim footnote attribution, generated/verified events yielding a computed trust tier (unverified / machine-confirmed / human-reviewed), status/superseded_by lifecycle, and stale_after ("check again, not false"). Evaluation can be built on LangSmith offline (golden Q&A datasets) + online (LLM-judge rules on curator traces) + annotation queues; standardized KB-quality metrics were not found in primary sources.

### Cited Findings
- OKF v0.3: only type is required; optional title, description, resource, tags; extension keys allowed (SHOULD use x-<producer>-<name>), consumers MUST NOT reject unknown keys. — [OKF SPEC.md](https://raw.githubusercontent.com/open-knowledge-format/open-knowledge-format/main/SPEC.md)
- Provenance: sources[] entries require resource (URL, in-bundle path, or non-followable scope descriptor); optional id, title, author, usage_count, last_modified; usage_window {from,to}; per-claim attribution via markdown footnote whose label equals a sources[].id. — [OKF SPEC.md](https://raw.githubusercontent.com/open-knowledge-format/open-knowledge-format/main/SPEC.md)
- Trust: generated: { by: reference_agent/gemini-2.5-pro, at: "2026-06-20T22:53:05Z" }; verified: list of {by, at} events (e.g. { by: "human:ahormati", at: "2026-06-25T09:00:00Z" }); only events with at >= generated.at count; tiers unverified / machine-confirmed (non-human only) / human-reviewed (any human:<id>). — [OKF SPEC.md](https://raw.githubusercontent.com/open-knowledge-format/open-knowledge-format/main/SPEC.md)
- Lifecycle: status draft|stable|deprecated (absent = stable); superseded_by path; stale_after absolute instant, stale when now >= stale_after, "Stale means check again, not false"; unparseable stale_after MUST NOT be treated as fresh; timestamps RFC 3339 or full-date. — [OKF SPEC.md](https://raw.githubusercontent.com/open-knowledge-format/open-knowledge-format/main/SPEC.md)
- Attested Computation concepts (runtime required, typed parameters, deterministic attester - "Attesters are deterministic code, not LLMs"); agents may supply parameter values only and must not edit the computation. — [OKF SPEC.md](https://raw.githubusercontent.com/open-knowledge-format/open-knowledge-format/main/SPEC.md)
- OKF maturity: v0.3, Apache-2.0, ~99 stars / 29 commits at fetch time, reference agent CLI (enrich, visualize) described as proof of concept. — [OKF repo](https://github.com/open-knowledge-format/open-knowledge-format)
- Re-verification: vendor guidance - per-document maximum age before re-verification plus lineage-triggered re-certification; re-index cadence by document criticality rather than one global schedule. — [Atlan: LLM KB freshness scoring](https://atlan.com/know/llm-knowledge-base-freshness-scoring/); [Atlan: staleness](https://atlan.com/know/llm-knowledge-base-staleness/) (vendor content; treat as practitioner opinion)
- LangSmith supports LLM-as-judge (reference-free/reference-based, few-shot improves accuracy), pairwise comparison, online automated rules on traces, annotation queues with rubrics and multi-reviewer reservations. — [LangSmith evaluation concepts](https://docs.langchain.com/langsmith/evaluation-concepts)
- Karpathy's lint operation (contradictions, stale claims, orphans, missing cross-refs) is a ready-made checklist for automated quality passes. — [Karpathy gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)

### Inferences
- Confidence scoring: OKF has no numeric confidence field; use an extension key (e.g. x-kf-confidence) or derive confidence from trust tier + source count/credibility + recency; keep the spec-native trust tier as the authoritative signal.
- Re-verification schedule: set stale_after per type (e.g. data-access guidance short TTL, policies medium, definitions long), a nightly job lists stale concepts and enqueues curator re-verification; a re-verification that confirms content appends a verified event (machine) without bumping generated.at, preserving the tier logic.
- Suggested KB metrics (design proposals, not sourced standards): citation coverage (% claims with footnote to sources[].id), human-reviewed ratio, stale ratio, orphan/broken-link counts, contradiction count from lint, flag resolution time, and downstream task success on a golden dataset (LangSmith offline experiments comparing KB versions).
- LLM-as-judge for edits: run as a required PR status check scoring faithfulness-to-cited-source, no-unsupported-claims, and style; use pairwise (old vs new page) judging for UPDATE edits.

### Gaps
- No primary source found defining standardized evaluation metrics for knowledge-base quality; metrics above are inferred.
- No published calibration data on LLM-judge accuracy for KB edit review was found.

## Governance: access control/PII, ownership, approval tiers by risk

### Takeaway
Governance can be layered from existing primitives: CODEOWNERS + rulesets for ownership and approval tiers, path-restricted pushes and bot-not-in-bypass-list for agent containment, agent-side path permissions/hooks (deepagents FilesystemPermission, Agent SDK PreToolUse) as defense in depth, per-user/tenant namespaces for store-backed memory, and a PII scanner in CI. Direct sources on approval-tier design for knowledge bases were not found.

### Cited Findings
- Copilot's model (requester can't self-approve; only write-access users trigger; comments from others never passed to agent; workflows gated until review; firewall; signed co-authored commits) — [GitHub Docs: Risks and mitigations](https://docs.github.com/en/copilot/concepts/agents/coding-agent/risks-and-mitigations)
- Rulesets: required approvals 0-10, code owner review, restrict file paths, bypass list by role/team/App, approval from someone other than last pusher. — [GitHub Docs: rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
- CODEOWNERS per path with team owners; protect the CODEOWNERS file itself. — [GitHub Docs: code owners](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)
- deepagents StoreBackend namespaces per user/assistant/thread; legacy default shares storage across all users of an assistant - "Set a factory for multi-user deployments." — [deepagents Backends](https://docs.langchain.com/oss/python/deepagents/backends)
- Agent SDK hooks can block unauthorized file access, sanitize data, audit-log tool calls, and require human approval. — [Claude Agent SDK hooks](https://code.claude.com/docs/en/agent-sdk/hooks)
- OKF consumers MUST NOT read paths resolving outside the bundle root and do not follow symlinks leaving it; dotfiles are outside the bundle. — [OKF SPEC.md](https://raw.githubusercontent.com/open-knowledge-format/open-knowledge-format/main/SPEC.md)
- Chase: storage is "the least important thing"; data-access guidance should point to sources of truth rather than duplicate them. — [LangChain blog](https://www.langchain.com/blog/knowledge-factory)

### Inferences
- Approval tiers (proposal): Tier 0 auto-merge (index regeneration, link fixes, stale_after refresh with machine verification); Tier 1 single domain-owner approval (new/updated concepts with cited sources); Tier 2 owner + second reviewer (deprecations, contradictions resolved, policy/finance/security paths, Attested Computation changes); enforce via separate rulesets / CODEOWNERS paths plus a CI-computed risk label.
- Access control: because git repos are all-or-nothing for read, split sensitive domains into separate OKF bundles/repos rather than relying on in-repo ACLs; "data access guidance" pattern avoids copying restricted data into the KB at all.
- PII: run a scanner (e.g. Microsoft Presidio) on raw/ ingestion and as a PR check; redact before claims leave staging.

### Gaps
- Presidio docs page returned a redirect (now at data-privacy-stack.github.io/presidio); API details not captured.
- No primary source found on risk-tiered approval schemes specifically for agent-curated knowledge bases; tiers above are design inference.
