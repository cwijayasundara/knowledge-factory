# Prior Art: Agent-Maintained / LLM-Curated Knowledge Bases (for a Knowledge Factory + Curator Agent)

Research date: 2026-11-21. Scope: 2024-2026 material. Primary sources preferred; secondary sources are flagged.

## Q1. Karpathy's "LLM Wiki" and "compile knowledge rather than RAG" patterns

### Takeaway
Karpathy's LLM Wiki (a GitHub gist, 4 Apr 2026) is the reference pattern: immutable raw sources -> an LLM-owned, interlinked Markdown wiki -> a schema/conventions file, run through three operations (ingest, query, lint), with an index.md catalog and an append-only log.md. It is an idea file, not a product, and dozens of community implementations exist. Critics document real failure modes (stored hallucinations, drift, summary degradation, lint circularity), and the community has proposed specific fixes.

### Cited Findings
- The gist was created 4 Apr 2026. Its core idea is that, instead of retrieving from raw docs at query time, an LLM builds and maintains a persistent, interlinked Markdown wiki: "the wiki is a persistent, compounding artifact." — [Karpathy gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- It has three layers. (1) Raw sources are "immutable" and act as the source of truth; the LLM reads them but never modifies them. (2) The wiki holds summaries, entity and concept pages, comparisons and an overview; the LLM owns it and the human reads it. (3) The schema (CLAUDE.md / AGENTS.md) defines structure, conventions and workflows, and is what "makes the LLM a disciplined wiki maintainer rather than a generic chatbot". Human and LLM evolve the schema together. — [Karpathy gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- Operations:
  - **Ingest:** read the source, discuss takeaways, write a summary page, update the index, revise related entity and concept pages, append to the log. "A single source might touch 10-15 wiki pages." Karpathy prefers to ingest one source at a time, with supervision.
  - **Query:** answer with citations. Good answers get filed back into the wiki as new pages.
  - **Lint:** check for contradictions, stale claims superseded by newer sources, orphan pages, missing concept pages, missing cross-references, and data gaps.

  — [Karpathy gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- index.md is a content catalog that the LLM reads first. The gist says this works at roughly 100 sources and hundreds of pages without embedding-based RAG. log.md is an append-only chronological record with parseable prefixes such as `## [date] ingest | Title`. — [Karpathy gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- The gist does not specify a citation format or a verification process. — [Karpathy gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- Human role: curate sources, direct analysis, ask questions. "You never (or rarely) write the wiki yourself." Analogy: "Obsidian is the IDE; the LLM is the programmer; the wiki is the codebase." — [Karpathy gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- Community implementations include:
  - wpzero/karpathy-llm-wiki: an agent skill with raw/ -> wiki/, cited answers and lint. — [GitHub](https://github.com/wpzero/karpathy-llm-wiki)
  - Astro-Han/karpathy-llm-wiki: Agent Skills for Claude Code, Cursor and Codex. — [GitHub](https://github.com/Astro-Han/karpathy-llm-wiki)
  - lucasastorian/llmwiki: a web app that uses Claude via MCP. — [GitHub](https://github.com/lucasastorian/llmwiki)
  - ddsyasas/llm-wiki: a local-first Next.js app. — [GitHub](https://github.com/ddsyasas/llm-wiki)
  - TrueHOOHA: uses skills "to enforce workflow rigidity and mitigate agent behavioral deviation". — [GitHub](https://github.com/TrueHOOHA/LLM-Wiki-Skilled)
- A catalog of documented criticisms and mitigations (community repo, secondary but detailed):
  - **Consensus smoothing:** the compiler erases tensions and minority views. Mitigation: extract facts rather than summarize, label claim types, and use adversarial advocate/judge roles.
  - **Context poisoning:** errors in derived pages spread through links. Mitigation: immutable raw sources, claim-level provenance, source hashes, a status lifecycle (draft -> archived), spot-checks against raw sources, and git-diff review of agent writes.
  - **Iterative summary degradation:** "Don't rewrite summaries of summaries"; re-derive from raw sources instead.
  - **Drift:** separate ingest from scheduled reconciliation, and track orphan rate, page age, missing provenance and a contradiction queue.
  - **Token burn:** cheap models for extraction and strong ones for synthesis, content hashes to skip recompilation, incremental lint.
  - **Prompt injection via ingested content:** treat sources as data, least privilege, write only to staging, review before promotion. "Prompt rules are not a security boundary; tool permissions are."
  - **Governance:** expand autonomy gradually (read-only -> flag-only -> PR writes) and gate trusted pages with code-owner review.
  - **Benchmark vacuum:** build local evals (retrieval hit rate, answer reuse, cost vs. baseline, drift, random-page review).

  — [po4yka/llm-wiki-skills criticism-and-mitigations](https://github.com/po4yka/llm-wiki-skills/blob/main/docs/criticism-and-mitigations.md)
- A review notes that lint "relies on the same model to detect its own errors — a circularity problem". — [tekai.dev review](https://tekai.dev/catalog/llm-wiki-pattern) (secondary; seen via search snippet only)

### Inferences
- The LLM Wiki is effectively a "compiler" architecture: raw sources are the source code, wiki pages are build artifacts, and the schema is the build config. That maps cleanly onto a knowledge factory, with the curator agent as the compiler plus linter.
- The gist leaves provenance, verification, status lifecycle and concurrency unspecified. A production knowledge factory has to add these, and the community mitigations (claim-level provenance, status states, PR-style review, staging area) are the obvious ways to fill the gaps.
- "Re-derive from raw, never summarize summaries" is the most important rule for avoiding self-reinforcing degradation.

### Gaps
- I found no rigorous public benchmark of the LLM Wiki pattern against RAG. The critics' "benchmark vacuum" point stands.
- Karpathy has published no official reference implementation.

## Q2. Agent memory systems: consolidation, contradiction, decay

### Takeaway
The major memory systems handle contradictions in three different ways:
- **Overwrite or delete:** early Mem0, LangMem profiles.
- **Invalidate with time bounds, keeping history:** Zep/Graphiti, Mem0g.
- **Append-only, resolved at retrieval:** Mem0 v3, 2026.

Consolidation is moving to asynchronous background agents (Letta sleep-time, LangMem background manager, Letta reflection/defrag). Memory storage is converging on git-versioned files (Letta Context Repositories, Anthropic memory tool, Skills).

### Cited Findings
**Letta (MemGPT)**
- Sleep-time agents (21 Apr 2025): a sleep-time-enabled setup creates a primary agent, which has no core-memory editing tools, and a sleep-time agent that holds the memory-editing tools and rewrites the primary agent's memory blocks asynchronously. The two can use different models (fast primary, larger and slower sleep-time). The stated motivation is that MemGPT's incremental memory formation "can become messy and disorganized over time". Run frequency is configurable as a token-cost trade-off. — [Letta blog](https://www.letta.com/blog/sleep-time-compute/)
- The sleep-time compute paper (Lin, Snell, Wang, Packer, Wooders, Stoica, Gonzalez; 17 Apr 2025) reports about 5x less test-time compute for the same accuracy on Stateful GSM-Symbolic and AIME, up to 13% and 18% accuracy gains, and 2.5x lower cost per query when sleep-time work is amortized across related queries. — [arXiv:2504.13171](https://arxiv.org/abs/2504.13171)
- Context Repositories (12 Feb 2026), git-backed memory in Letta Code:
  - Every memory change is auto-committed with an informative message.
  - Subagents work in isolated git worktrees and merge back.
  - The file tree is always in the prompt, with per-file frontmatter (progressive disclosure); system/ files are always loaded.
  - A "Reflection" skill is a background sleep-time process that saves important information from recent conversations.
  - A "Defragmentation" skill backs up memory, then splits, merges and restructures it into a hierarchy of 15-25 focused files.

  — [Letta blog: Context Repositories](https://www.letta.com/blog/context-repositories/)

**Zep / Graphiti**
- Graphiti has three subgraphs:
  - **Episode subgraph:** raw inputs, kept non-lossy. Episodic edges link facts to their sources, which gives provenance.
  - **Semantic entity subgraph:** resolved entities and fact edges.
  - **Community subgraph:** label-propagation clusters with summaries, updated incrementally and with periodic full refreshes.

  — [Zep paper arXiv:2501.13956](https://arxiv.org/html/2501.13956)
- It uses a bi-temporal model: T is the real-world validity timeline and T' is the ingestion timeline. Each edge records created/expired times and valid/invalid times. Relative dates are resolved against the message timestamp. — [arXiv:2501.13956](https://arxiv.org/html/2501.13956)
- Deduplication and contradiction handling:
  - Entity resolution uses embedding cosine similarity plus full-text candidates, then an LLM duplicate judgment, which merges names and updates summaries.
  - Edge dedup is restricted to edges between the same entity pair.
  - For contradictions, an LLM compares the new edge with related edges. When they overlap in time, the old edge's invalid time is set to the new edge's valid time. "Newer information takes priority", and history is retained.

  — [arXiv:2501.13956](https://arxiv.org/html/2501.13956)
- Benchmarks:
  - On LongMemEval with gpt-4o, accuracy went from 60.2% to 71.2% and latency from 28.9 s to 2.58 s, using about 1.6k context tokens instead of about 115k.
  - Single-session-assistant questions declined (-17.7% with gpt-4o).
  - The authors acknowledge weaknesses in the DMR benchmark.

  — [arXiv:2501.13956](https://arxiv.org/html/2501.13956)

**Mem0**
- The 2025 paper uses extraction followed by an update phase. For each candidate fact it retrieves the top-10 similar memories, and an LLM tool call chooses ADD / UPDATE / DELETE / NOOP. The graph variant (Mem0g) marks conflicting relations invalid instead of deleting them. Results on LoCoMo (LLM-judge): Mem0 66.88%, Mem0g 68.44%, best RAG about 61%, full context 72.90%. The paper claims about 91% lower p95 latency than full context. — [Mem0 paper arXiv:2504.19413](https://arxiv.org/html/2504.19413v1)
- New algorithm (v3, April 2026 per secondary sources):
  - A single LLM call that is **ADD-only**: "changed facts are stored alongside the old ones rather than overwriting them".
  - Recency and relevance are handled by retrieval ranking, and the page describes no explicit staleness flag.
  - Graph memory was removed from the OSS SDK; it is now a feature of the Mem0 Platform.
  - Reported results: LoCoMo 71.4 -> 91.6, LongMemEval 67.8 -> 93.4, with extraction latency roughly halved.

  — [Mem0 OSS migration v2->v3](https://docs.mem0.ai/migration/oss-v2-to-v3)
- The README reports different figures (92.5 LoCoMo / 94.4 LongMemEval), which "reflect Mem0's managed platform, which includes proprietary optimizations" (via search summary). To manage volume, users must rely on expiration dates or the delete API. — [Mem0 platform migration](https://docs.mem0.ai/migration/platform-v2-to-v3); the numbers conflict with the [OSS migration doc](https://docs.mem0.ai/migration/oss-v2-to-v3), so they are vendor-reported and unverified.

**LangMem / LangGraph store (LangChain)**
- There are three memory types: semantic (facts, stored as a profile or a collection), episodic (successful interactions as examples) and procedural (system-prompt rules refined from feedback). — [LangMem conceptual guide](https://langchain-ai.github.io/langmem/concepts/conceptual_guide/)
- Storage comes in two shapes:
  - **Collections:** many records, where new information is reconciled by "deleting or invalidating outdated memories, or by updating and consolidating them". Over-extraction hurts precision and under-extraction hurts recall.
  - **Profiles:** a single schema-bound document that is updated in place.

  — [LangMem conceptual guide](https://langchain-ai.github.io/langmem/concepts/conceptual_guide/)
- Writes happen either in the hot path (immediate, adds latency) or in the background (reflect after the conversation ends; delayed but higher recall). Retrieval blends similarity with importance and "strength", which depends on how recently and frequently a memory was used. That is a decay signal. — [LangMem conceptual guide](https://langchain-ai.github.io/langmem/concepts/conceptual_guide/)

**Anthropic memory tool / Skills**
- The memory tool (type memory_20250818) is stable and client-side. Claude issues file operations under /memories and the application stores them. Claude "automatically checks its memory directory before starting a task". It pairs with context editing and compaction: "memory preserves the information that must survive summarization." — [Claude docs: Memory tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool)
- The docs' security and hygiene guidance:
  - Strip sensitive data before writes.
  - Cap file sizes.
  - **"Periodically delete memory files that haven't been accessed in a long time"** (expiration).
  - Validate paths strictly against traversal.

  — [Claude docs: Memory tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool)
- The docs recommend a multi-session pattern: an initializer session sets up a progress log and checklist, later sessions read them first, and each session updates the log before it ends. — [Claude docs: Memory tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool)
- Anthropic reported that memory tool plus context editing improved performance by 39% over baseline (context editing alone: 29%), with an 84% token reduction in a 100-turn eval. These are internal figures. — [Claude blog: context management](https://www.claude.com/blog/context-management) (via search summary)
- Skills use three-level progressive disclosure: name and description in frontmatter, then the SKILL.md body when relevant, then referenced files only when needed. — [Anthropic Complete Guide to Building Skills (PDF)](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf) (via search summary; size limits conflict across sources)

**Cognee**
- Cognee runs an ECL (Extract, Cognify, Load) pipeline: classify -> permission check -> chunk -> LLM entity and relation extraction -> summarize -> embed. A post-ingest "Memify" step reportedly cleans stale nodes, adds associations and reweights memories without a full rebuild. — [Cognee blog](https://www.cognee.ai/blog/fundamentals/how-cognee-builds-ai-memory) (vendor; details unverified)

**OpenAI ChatGPT memory**
- It has two parts: saved memories (explicit facts the user can view and delete) and reference chat history (not browsable per entry). How the chat-history mechanism works (RAG vs. an injected summary) is disputed across third-party sources. — [memx.app](https://memx.app/blog/chatgpt-reference-chat-history-vs-saved-memories/) (secondary; I found no OpenAI primary doc this round)

**Surveys**
- "Memory in the Age of AI Agents" (Dec 2025, rev. Jan 2026, 47 authors) proposes a taxonomy:
  - **Forms:** token-level / parametric / latent.
  - **Functions:** factual / experiential / working.
  - **Dynamics:** formation, evolution (consolidation, updating, forgetting) and retrieval.

  It calls the field fragmented and names trustworthiness and multi-agent memory as frontiers. — [arXiv:2512.13564](https://arxiv.org/abs/2512.13564)
- Other 2026 work targets forgetting specifically, e.g. FadeMem (biologically inspired forgetting). — [arXiv:2601.18642](https://arxiv.org/pdf/2601.18642) (title only, not reviewed)

### Inferences
- For a curator agent, the Graphiti model (invalidate, don't delete; bi-temporal valid_from/valid_to plus recorded_at) is the most defensible way to handle contradictions. Mem0 v3's ADD-only approach shows that some vendors push resolution to read time, but that leaves stale facts in place, which is a poor fit for an authoritative knowledge base.
- The sleep-time split (a fast reader/answerer agent plus a slower curator agent that owns all writes) is a direct template for "knowledge factory worker vs. curator".
- Letta's git-backed memory with worktrees per subagent, auto-commits and periodic defrag, together with Anthropic's file-based memory, suggests that a Markdown + frontmatter + git store (such as OKF-style files) is now mainstream, not exotic.
- Decay signals already in use include recency/frequency "strength" (LangMem), expiry of unaccessed files (Anthropic), expiration dates (Mem0) and periodic review intervals (Guru, Q3).

### Gaps
- I could not confirm from a primary source the reported Letta Code "dreaming" naming or OpenAI's internal memory mechanism.
- I found no primary docs on how LangMem profiles resolve conflicting fields.

## Q3. Enterprise knowledge curation: Guru, Glean, Notion, Confluence, KCS

### Takeaway
Enterprise tools keep knowledge trustworthy through ownership plus a verification lifecycle: a named verifier, review intervals, verified/unverified states, and edits that trigger re-verification. AI agents increasingly run the verification. KCS adds a demand-driven process: capture in the workflow, "reuse is review", and a separate Evolve loop for content health.

### Cited Findings
- **Guru:**
  - Every card has a verifier (a person or a group). If someone else edits a card, it becomes unverified and a verification request is sent.
  - Review intervals are 30/60/90 days, 6 months, 1 year, or "does not expire".
  - Trust states are Verified, Unverified, or no status. External sources (Drive, Confluence) default to no status.
  - Agents can be restricted to answer only from verified content.

  — [Guru help: verification](https://help.getguru.com/docs/verifying-and-unverifying-cards)
- **Guru Knowledge Agents' automated verification:**
  - Agents review eligible content daily. External sources are reviewed only after they have been used in an answer.
  - Unverify rules run before verify rules, with a 7-day cooldown.
  - Rules are behavioral (feedback, views, expert input) or content-based (AI analysis of text, dates, topic).
  - A Quality Log records each decision with a confidence level and reasons.
  - A content rule can flag near-duplicates by meaning and unverify the card, citing the duplicate.
  - Since Jan 2026, auto-verify is on by default and auto-unverify is off.

  — [Guru help](https://help.getguru.com/docs/verifying-and-unverifying-cards)
- **Notion** has page verification: important pages can be marked official for a period or indefinitely, and verified pages can be surfaced as trusted results in search and AI. — [eesel.ai comparison](https://www.eesel.ai/blog/best-ai-tools-for-knowledge-base-management) (secondary via search summary)
- A vendor critique (from a competitor) says agents reading Notion or Confluence get pages "in whatever state your team last left them, with no verification workflow and no conflict resolution". — [Unblocked blog](https://getunblocked.com/blog/best-knowledge-base-ai-agents/) (biased source)
- **Glean:**
  - Builds a permissions-aware enterprise knowledge graph (people, teams, projects, tickets, files) that agents use for disambiguation, planning and memory.
  - Combines graph signals (ownership, usage) with vector and lexical retrieval.
  - Launched Enterprise Graph and a third-generation Assistant in Sept 2025.

  — [Glean blog: Enterprise Graph launch](https://www.glean.com/blog/live-fall-25-main); [Glean blog: enterprise context](https://www.glean.com/blog/from-enterprise-search-to-enterprise-context-what-ai-agents-actually-need) (vendor)
- **Confluence / Atlassian Rovo:** agents and Studio build research and summary agents within Confluence, respecting Atlassian permissions. I found no comparable verification feature. — [eesel.ai](https://www.eesel.ai/blog/best-ai-tools-for-knowledge-base-management) (secondary)
- **KCS v6** (Consortium for Service Innovation):
  - Solve Loop: Capture, Structure, Reuse, Improve.
  - Evolve Loop: Content Health, Process Integration, Performance Assessment, Leadership & Communication.
  - Techniques include "Reuse is Review" (4.1), "KCS Article State" (5.2), archiving, health indicators, and a roles/licensing model (7.1).
  - Principles: "Knowledge is best managed at the point of creation, in the context of demand"; set goals on outcomes, not activities; avoid over-engineering.

  — [KCS v6 Practices Guide summary](https://library.serviceinnovation.org/KCS/KCS_v6/KCS_v6_Practices_Guide/041)
- KCS has reportedly been rebranded "Knowledge-Centered Success", and sources conflict on whether v6 is still current. — [Consortium library](https://library.serviceinnovation.org/KCS); [Wikipedia](https://en.wikipedia.org/wiki/Knowledge-centered_support)

### Inferences
- The patterns to copy for a curator agent:
  - Per-page owner/verifier.
  - Review interval fields (a TTL in frontmatter).
  - An edit that invalidates verification.
  - Unverify rules evaluated before verify rules.
  - A decision log with confidence and reasons.
  - An answer agent that can be restricted to verified content.
- KCS's "reuse is review" and demand-driven improvement suggest the factory should prioritize curation by query traffic, re-checking the pages that are actually used rather than linting everything equally. That echoes Guru's "external sources reviewed after use in an answer".
- The KCS licensing model (contributors earn rights to publish directly) is analogous to graduated agent autonomy (draft -> flag -> PR -> auto-publish).

### Gaps
- I did not retrieve the KCS article-state definitions (e.g., Work in Progress / Not Validated / Validated / Archived). The full guide PDF is at https://www.serviceinnovation.org/included/docs/KCS_v6_Practices_Guide_2023_06_08.pdf but was not reviewed.
- I found no primary Notion or Atlassian docs on verification or AI curation this round.

## Q4. GraphRAG, LightRAG and knowledge-graph construction pipelines

### Takeaway
GraphRAG is a heavyweight pipeline (chunk -> extract entities, relations and claims -> Leiden communities -> bottom-up community reports) that later gained an incremental update command. LightRAG was designed for incremental merging. LazyGraphRAG defers all LLM work to query time, at about 0.1% of GraphRAG's indexing cost. The core trade-off is precomputed synthesis (expensive and stale-prone) vs. lazy synthesis (cheap but repeated per query).

### Cited Findings
- **GraphRAG indexing:** the corpus is split into TextUnits (which provide fine-grained references); entities, relationships and key claims are extracted; hierarchical Leiden clustering is run; community reports are generated bottom-up. Query modes include DRIFT search. — [Microsoft GraphRAG docs](https://microsoft.github.io/graphrag/)
- **GraphRAG 1.0** (16 Dec 2024) added an `update` CLI command that computes deltas between an existing index and new content and merges them. The post notes that new content can change community structure enough to require recomputing much of an index, and that LLM caching makes re-runs "significantly faster and cheaper". — [MSR blog: GraphRAG 1.0](https://www.microsoft.com/en-us/research/blog/moving-to-graphrag-1-0-streamlining-ergonomics-for-developers-and-users/)
- **LazyGraphRAG** (25 Nov 2024):
  - Indexing cost is equal to vector RAG and about 0.1% of GraphRAG's, because it uses NLP noun-phrase extraction and co-occurrence graphs instead of LLM summarization. It "defers all LLM use until query time".
  - Results: quality comparable to GraphRAG Global Search at more than 700x lower query cost on global queries. At 4% of GraphRAG's query cost it outperformed all competitors.
  - These are the authors' evaluations (5,590 AP articles, 100 synthetic queries).

  — [MSR blog: LazyGraphRAG](https://www.microsoft.com/en-us/research/blog/lazygraphrag-setting-a-new-standard-for-quality-and-cost/)
- **LightRAG:** dual-level (low and high) retrieval over graph plus vectors, with an "incremental update algorithm that ensures the timely integration of new data". — [arXiv:2410.05779](https://arxiv.org/abs/2410.05779)
- Secondary summaries say GraphRAG's community design forced complete reconstruction when data was added, while LightRAG merges new nodes and edges. — [alphaXiv overview](https://www.alphaxiv.org/overview/2410.05779) (secondary; predates or ignores GraphRAG 1.0's update command, so partly outdated)
- **Zep/Graphiti** (Q2) is an incremental, temporally aware KG-construction pipeline with LLM entity resolution and edge invalidation, and with episodes kept as provenance. — [arXiv:2501.13956](https://arxiv.org/html/2501.13956)

### Inferences
- For a knowledge factory, the GraphRAG/LightRAG extraction stages (chunk -> entity/relation/claim extraction -> resolution -> community summaries) map to "compile" steps, and community reports resemble LLM-Wiki overview/topic pages.
- The LazyGraphRAG result is a caution: precompiling everything is costly. Compile eagerly only where reuse is high (KCS demand signal), and synthesize lazily elsewhere.
- Keeping TextUnit/episode IDs on every extracted claim, as GraphRAG and Graphiti both do, is the standard way to preserve provenance.

### Gaps
- I did not verify the current GraphRAG 2.x incremental-update API; third-party sources conflict.
- I did not review LightRAG's own benchmark numbers.

## Q5. Documented failure modes and mitigations

### Takeaway
The documented risks are:
- Stored or propagated hallucinations (context poisoning).
- Degradation from summarizing summaries.
- Drift and staleness.
- Duplication.
- Consensus smoothing.
- Memory poisoning through ordinary queries.
- Distribution collapse when models consume their own outputs.

Mitigations converge on: immutable raw sources plus claim-level provenance; invalidate-not-delete with temporal validity; staged writes with human or PR review and graduated autonomy; verification states with TTLs; dedup rules; tool-permission security boundaries; and local evals.

### Cited Findings
- **Model collapse:** "indiscriminate use of model-generated content in training causes irreversible defects", and tails of the original distribution disappear. Shown for LLMs, VAEs and GMMs. — [Shumailov et al., Nature 631, 2024](https://www.nature.com/articles/s41586-024-07566-y)
- Follow-up work finds that accumulating real data alongside synthetic data, rather than replacing it, avoids collapse. — [Nature news](https://www.nature.com/articles/d41586-024-02355-z); see also [arXiv:2410.12954](https://arxiv.org/html/2410.12954v2) (commentary; not deeply reviewed)
- **Memory injection (MINJA):** an attacker with query-only access can plant malicious records in an agent's memory bank, using bridging steps and progressive shortening, so that the records are later retrieved for victim queries. — [arXiv:2503.03704](https://arxiv.org/abs/2503.03704)
- Early versions report injection success above 95% and attack success above 70% (via search summary). A 2026 follow-up says these figures came from idealized conditions, and cites MINJA's finding that defenses such as Llama Guard and memory sanitization were largely ineffective. — [arXiv:2601.05504](https://arxiv.org/abs/2601.05504) (secondhand characterization)
- **LLM-Wiki-specific failure modes** and their mitigations (see Q1 list): context poisoning, summary degradation, drift, consensus smoothing, prompt injection, token burn and the benchmark vacuum. — [po4yka/llm-wiki-skills](https://github.com/po4yka/llm-wiki-skills/blob/main/docs/criticism-and-mitigations.md)
- **Contradiction and staleness handling in production systems:** Graphiti invalidates with time bounds and retains history ([arXiv:2501.13956](https://arxiv.org/html/2501.13956)). Mem0g marks invalid rather than deleting ([arXiv:2504.19413](https://arxiv.org/html/2504.19413v1)). Mem0 v3 keeps both old and new facts and relies on ranking ([Mem0 docs](https://docs.mem0.ai/migration/oss-v2-to-v3)).
- **Messy memory over time:** Letta states that incremental memory formation becomes "messy and disorganized", and its mitigations are sleep-time rewriting ([Letta](https://www.letta.com/blog/sleep-time-compute/)) and defragmentation into 15-25 focused files with a backup first ([Letta Context Repositories](https://www.letta.com/blog/context-repositories/)).
- **Audit trail:** git auto-commits on every memory change, and merge-conflict resolution for concurrent writers. — [Letta Context Repositories](https://www.letta.com/blog/context-repositories/)
- **Duplication:** Graphiti dedups with embeddings plus full-text candidates and an LLM judge ([arXiv:2501.13956](https://arxiv.org/html/2501.13956)). Guru flags semantic near-duplicates and unverifies them, citing the duplicate ([Guru](https://help.getguru.com/docs/verifying-and-unverifying-cards)).
- **Stale knowledge:** Guru uses review intervals and agent auto-unverify ([Guru](https://help.getguru.com/docs/verifying-and-unverifying-cards)). Anthropic advises deleting long-unaccessed memory files ([Claude docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool)).
- **Sensitive data and path safety** in agent-written stores: strip sensitive data before write and validate canonical paths. — [Claude docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool)
- **Benchmarks for memory:** LoCoMo and LongMemEval are the de facto memory benchmarks. Zep notes that DMR has design weaknesses, and its memory regressed on single-session-assistant questions. — [arXiv:2501.13956](https://arxiv.org/html/2501.13956); [arXiv:2504.19413](https://arxiv.org/html/2504.19413v1)

### Inferences (design lessons for the knowledge factory / curator agent)
1. **Three-tier store:**
   - immutable raw/ (hashed, append-only);
   - compiled knowledge pages (agent-owned, with claim-level citations to raw IDs);
   - schema/policy files.

   Never let the agent cite its own compiled pages as primary evidence; always re-derive from raw (this guards against the collapse and poisoning loops).
2. **Bi-temporal claims:** valid_from/valid_to plus recorded_at. Contradictions mark the old claim superseded and link it to the new one; nothing is deleted (Graphiti).
3. **Split reader and curator:** the answerer is read-only, and a background curator (sleep-time) owns all writes, dedup, merge/split (defrag) and lint.
4. **Lifecycle states** (draft -> unverified -> verified -> stale -> superseded/archived), with an owner and review_interval per page. Edits reset verification. Unverify rules run first. Every curator decision is logged with confidence and reasons (Guru Quality Log).
5. **Git as audit and concurrency:** curator writes land as commits or PRs on branches/worktrees. Autonomy is graduated (flag-only -> PR -> auto-merge for low-risk classes), mirroring the KCS licensing model.
6. **Demand-driven curation:** prioritize re-verification by query usage ("reuse is review"), and compile lazily for low-traffic areas (LazyGraphRAG cost lesson).
7. **Security:** treat ingested content as untrusted data; do untrusted ingest without network or shell access and write it to staging; enforce boundaries through tool permissions rather than prompt rules (MINJA, prompt injection).
8. **Evals from day one:** retrieval hit rate, citation faithfulness (spot-check claims against raw), contradiction-queue size, orphan rate, page age, duplication rate, cost per ingest, and regressions on held-out Q&A (LoCoMo/LongMemEval-style).

### Gaps
- I found no published production post-mortems quantifying hallucination contamination rates in LLM-maintained wikis.
- I found no studies of "model collapse" specifically for retrieval stores (as opposed to training). Applying it to self-written docs is an analogy, not demonstrated evidence.
- I did not verify the original MINJA metrics from the paper body.
