# LangChain sample / reference implementations of a "knowledge factory" or "curator agent"

Research date: 2026-11-21. Scope: official LangChain (github.com/langchain-ai, github.com/langchain-samples, langchain.com blog, docs.langchain.com) vs. community. Method: gh search repos/code across the langchain-ai org, gh api for contents and commit dates, shallow clones of open-swe and deepagents grepped for "curator|missing knowledge|knowledge factory|sleep time|consolidat", plus blog/docs fetches.

**Headline:** As of 2026-11-21 LangChain has **not** published a reference implementation of the knowledge factory as Harrison Chase describes it (flag-missing-knowledge tool, plus a scheduled curator agent reading traces/Slack/Notion, plus skills/OKF storage). The post went up today (Nov 21, 2026) and has no code. Several official repos implement **parts** of the pattern. The closest are: (1) the `deepagents/examples/llm-wiki` example (ingest/query/lint curation into Context Hub), (2) the **memory curator inside open-swe** (a curator that folds per-thread memories into a versioned workspace prompt), (3) `docs-release-watch` in langchain-ai/docs (a scheduled Managed Deep Agent with Context Hub memory), (4) `langchain-samples/deepagents-with-langsmith/agents/memory_backed_agent` (Context Hub memory plus LangSmith Engine reading traces on a schedule), and (5) OpenWiki (writes OKF v0.2 wikis from code, Notion, Slack and more, with scheduled updates).

## Q1: Do any langchain-ai repos contain a curator agent, knowledge factory, memory-consolidation / "sleep-time" agent, or skill-updating agent?

### Takeaway
No repo is named or packaged as a "knowledge factory" or "curator agent" template. Searches for `repos --owner langchain-ai knowledge` and `curator agent` return nothing. The only literal "curator" in LangChain code is the **memory curator in open-swe**. It is a real production component that adopts, supersedes or declines memories and writes them into a versioned workspace prompt, but it is embedded in the product, not offered as a sample. The nearest *sample-grade* code is `deepagents/examples/llm-wiki`.

### Cited Findings
**Official: closest matches (ranked by closeness to the pattern)**

1. **langchain-ai/open-swe: memory curator (embedded, not a sample).** Last push 2026-11-21. Repo is "An Open-Source Asynchronous Coding Agent", about 11.2k stars. — [repo](https://github.com/langchain-ai/open-swe)
   - Migration 0087: "A thread's `remember` keeps a memory: a personal one applies to the person who saved it at once, and every memory waits for the workspace's curator, which may fold what many threads learned into the workspace's prompt. Each curated prompt is kept as a new version." — [0087 migration](https://github.com/langchain-ai/open-swe/blob/main/openswe/database/migrations/versions/0087_e0605414666c_keep_memories_and_each_workspace_s_.py)
   - Memory statuses are `pending`, `held`, `adopted`, `superseded` and `declined`, where "superseded" means "fully covered by a line it wrote in the workspace's prompt". — [0089 migration](https://github.com/langchain-ai/open-swe/blob/main/openswe/database/migrations/versions/0089_5f101256cbc0_let_the_curator_supersede_a_memory.py)
   - The curator names "triggers" (paths) and writes guidance at them; `recall(path)` matches a trigger at the path or above it. — [0095](https://github.com/langchain-ai/open-swe/blob/main/openswe/database/migrations/versions/0095_05cc16abd7bf_let_the_curator_name_triggers_for_.py), [0098](https://github.com/langchain-ai/open-swe/blob/main/openswe/database/migrations/versions/0098_46f45743d6b7_make_memory_triggers_paths_and_let_the_.py)
   - The curator runs in its own thread, which is read-only to users ("The memory curator's thread is read-only."). — [openswe/threads/summary.py](https://github.com/langchain-ai/open-swe/blob/main/openswe/threads/summary.py)
   - Closeness: high on "agents flag/propose and a curator decides centrally" (a `remember` proposal is close to a flag). Lower on sources: it curates memories, not Slack/Notion/traces, and writes a workspace prompt, not SKILL.md/OKF. The README does not mention the curator.

2. **langchain-ai/deepagents: `examples/llm-wiki`.** Last commit touching it 2026-11-20 (a dependency bump). — [README](https://github.com/langchain-ai/deepagents/tree/main/examples/llm-wiki)
   - "A script-first Deep Agents example that builds a persistent wiki and syncs it through `langsmith hub` commands". It has `init`/`ingest`/`query`/`lint` modes running `create_deep_agent` in LangSmith Sandbox. Lint "reconciles contradictions, stale/superseded claims, orphan pages, missing cross-references" and reports gaps. Every run pushes a Context Hub revision "so teammates can review changes, comment, and promote versions". It also keeps an append-only `log.md`. — [README](https://github.com/langchain-ai/deepagents/tree/main/examples/llm-wiki)
   - Closeness: medium-high on curation mechanics and Context Hub storage. It has **no** flag tool, no schedule (CLI-driven), and no trace/Slack/Notion ingestion (sources are local files). Output is a wiki, not skills.

3. **langchain-ai/docs: `docs-release-watch`.** Last commit 2026-11-10. It is a "Managed Deep Agent that watches product releases and opens documentation updates". It runs on Mon/Wed/Fri cron schedules (`schedules/daily_*_check.py`), has `skills/` and `tools/`, and opens Linear tickets plus draft PRs. — [README](https://github.com/langchain-ai/docs/tree/main/docs-release-watch)
   - Its `memory.py` uses `define_memory(scope="agent")`: "`/memories/agent/AGENTS.md` is hot memory… The content lives in LangSmith Context Hub… deploys never overwrite what earlier runs learned." It also warns that shared hot memory "is a trust boundary". — [memory.py](https://github.com/langchain-ai/docs/blob/main/docs-release-watch/memory.py)
   - Closeness: medium. It is the best official **template for a scheduled background agent that maintains a knowledge artifact** (docs) using skills plus Context Hub memory. The thing it curates is public docs, not internal agent knowledge.

4. **langchain-ai/openwiki.** Created 2026-06-22, pushed 2026-11-21, about 18k stars. "OpenWiki is a CLI that writes and maintains agent documentation for your codebase". — [repo](https://github.com/langchain-ai/openwiki)
   - It emits Open Knowledge Format (OKF) v0.2 bundles (YAML front matter, `sources`, `verified`, `status`, `stale_after`, reserved `index.md`/`log.md`). Its README links the OKF spec at GoogleCloudPlatform/knowledge-catalog. — [README](https://github.com/langchain-ai/openwiki#open-knowledge-format-okf-v02)
   - Personal mode ingests from connectors ("Custom MCP, local git repositories, Notion, Gmail, X/Twitter, Web Search, and Hacker News… Slack is also available") and supports scheduled updates. It grounds facts as "Claims" against source evidence. — [README](https://github.com/langchain-ai/openwiki)
   - Closeness: medium-high on storage (OKF) and on sources (Notion/Slack), with scheduled maintenance. It has **no** agent flag tool, does not read LangSmith traces as a source ("LangSmith-only observations, are not claimed"), and produces wiki pages rather than SKILL.md.

5. **langchain-ai/deepagents: `ContextHubBackend`** (`libs/deepagents/deepagents/backends/context_hub.py`, last change 2026-10-16). "Store files in a LangSmith Hub agent repo (persistent)". It is the storage primitive a curator would write through. — [file](https://github.com/langchain-ai/deepagents/blob/main/libs/deepagents/deepagents/backends/context_hub.py)

6. **deepagents PR #7651, "add LangSmith memory agent example" (CLOSED, not merged; opened 2026-11-10).** Short-term, semantic, episodic and procedural memory. Procedural memory is `/memories/agent/AGENTS.md` on `ContextHubBackend`, and skills in Context Hub are write-denied. It has no curator. — [PR](https://github.com/langchain-ai/deepagents/pull/7651)

7. **deepagents `examples/better-harness`.** "System for autonomous harness optimization": an outer Deep Agent edits an inner agent's harness surfaces and keeps changes only if train+holdout evals improve. It is related as an eval-gated self-improvement loop, but it is not knowledge curation. — [README](https://github.com/langchain-ai/deepagents/tree/main/examples/better-harness)

8. **langchain-ai/langmem.** Pushed 2026-11-16 (only dependency bumps recently), about 1.8k stars. It contains `src/langmem/reflection.py` (`ReflectionExecutor`) and a "delayed_processing" guide, the background/"sleep-time" memory-consolidation primitive. — [repo](https://github.com/langchain-ai/langmem), [delayed processing guide](https://github.com/langchain-ai/langmem/blob/main/docs/docs/guides/delayed_processing.md)

9. **Older memory templates (not curators):** `memory-agent` (pushed 2026-11-18), `memory-template`, `langgraph-memory`, `lang-memgpt`, `long_term_memory_course`, `agents-from-scratch`. They store memories in-run and none has a scheduled curator. — [gh search](https://github.com/orgs/langchain-ai/repositories?q=memory)

10. **Deep Agents examples dir** has `deploy-gtm-agent`, `content-builder-agent`, `deep_research`, `llm-wiki`, `better-harness`, `ralph_mode` and others. A grep across the deepagents repo for curator/knowledge-factory/consolidation found no curator implementation; the only hits are evals and prompts. — [examples](https://github.com/langchain-ai/deepagents/tree/main/examples)

11. **design-agent** (created 2026-10-18) and **paid-media-agent** (created 2026-09-11) are open-source Deep Agents. design-agent has a `memory.py` and a `deep-agents-memory` skill, but code search found no curator or flag tool. — [design-agent](https://github.com/langchain-ai/design-agent), [paid-media-agent](https://github.com/langchain-ai/paid-media-agent)

12. **Skills repos:** `langchain-skills`, `langsmith-skills`, `skills-benchmarks` and `langchain-plugins` are static skill collections. None contains a skill-updating agent (based on repo listing and search; contents were not exhaustively read). — [langchain-skills](https://github.com/langchain-ai/langchain-skills), [langsmith-skills](https://github.com/langchain-ai/langsmith-skills)

### Inferences
- LangChain's internal "company harness" agents (GTM Agent, OpenSWE, Content Studio) share memory infrastructure. The open-swe curator is the concrete in-house precursor to the knowledge-factory curator: agents propose, and a single curator decides and versions the result.
- A practitioner could assemble a knowledge factory today from official parts: `docs-release-watch`'s Managed Deep Agents schedule + skills layout, llm-wiki's ingest/lint curation, `ContextHubBackend` storage, and OpenWiki's OKF output. No single repo combines them.

### Gaps
- I could not confirm when or how often the open-swe curator runs (scheduled vs. event-triggered); only migrations and a thread guard were inspected.
- The skills repos' contents were not exhaustively read.

## Q2: Is there a LangSmith Context Hub / Engine example for curating knowledge? Any OKF tooling from LangChain?

### Takeaway
Yes, partially. The Context Hub launch post links two official examples: `llm-wiki` and `memory_backed_agent`. The latter wires LangSmith Engine to read traces on a schedule against the same Context Hub repo the agent uses for memory. That is the closest official "traces into knowledge" loop, but Engine proposes fixes rather than autonomously curating skills. LangChain's OKF tooling is OpenWiki (OKF v0.2 output); the OKF format itself is a separate project.

### Cited Findings
- "Introducing LangSmith Context Hub" (Harrison Chase, May 13, 2026). It describes versioning, dev/staging/prod tags, comments, CLI `langsmith hub push/pull`, and use as a Deep Agents memory backend, and has a "Continual learning with Context Hub" section. Links: llm-wiki example and `langchain-samples/deepagents-with-langsmith/agents/memory_backed_agent`. — [blog](https://www.langchain.com/blog/introducing-context-hub)
- **memory_backed_agent** (last commit 2026-05-13): `CompositeBackend(default=StateBackend(), routes={"/memories/": ContextHubBackend(agent_name)})`. After deploy it calls `POST /v1/platform/sessions/{session_id}/issues-agent` so that "LangSmith Engine then runs on a schedule, analyzes traces, and files issues against the same Context Hub repo handle your agent uses for `/memories/`." — [README](https://github.com/langchain-samples/deepagents-with-langsmith/tree/main/agents/memory_backed_agent)
- Engine docs: Engine "analyzes your production traces to surface recurring issues, diagnose root causes, and propose fixes". It can open PRs and never merges them, and it scans "on a dynamic schedule". — [Engine docs](https://docs.langchain.com/langsmith/engine)
- Search summaries of the Engine setup docs and the Managed Deep Agents post say a connected Context Hub repo lets Engine propose fixes to instructions and skills. — [Engine setup](https://docs.langchain.com/langsmith/engine-setup), [Managed Deep Agents blog](https://www.langchain.com/blog/introducing-managed-deep-agents) (seen via search snippets only, not fetched directly)
- Harrison's post says LangSmith Engine "maintains a knowledge factory per agent" (per a fetched summary of the article). — [knowledge-factory blog](https://www.langchain.com/blog/knowledge-factory)
- Managed Deep Agents docs on Context Hub and memory. — [MDA Context Hub](https://docs.langchain.com/langsmith/python/managed-deep-agents-context-hub), [MDA memory](https://docs.langchain.com/langsmith/python/managed-deep-agents-memory), [Use the Context Hub](https://docs.langchain.com/langsmith/use-the-context-hub)
- Open deepagents PR #7542 tags Context Hub reads with provenance in traces (which skills were actually loaded). This could enable usage-aware curation. — [PR #7542](https://github.com/langchain-ai/deepagents/pull/7542) (status per search snippet: open)
- **OKF:** Harrison's post links `github.com/open-knowledge-format/open-knowledge-format` (created 2026-10-07, about 99 stars, spec v0.3). Its README calls OKF "a universal, vendor-neutral format… plain markdown files with YAML frontmatter" and says it is not tied to any framework. OpenWiki emits OKF **v0.2** and links the spec under GoogleCloudPlatform/knowledge-catalog, so the two point at different spec locations and versions. — [OKF repo](https://github.com/open-knowledge-format/open-knowledge-format), [OpenWiki README](https://github.com/langchain-ai/openwiki)

### Inferences
- Engine plus Context Hub is LangChain's productized (closed-source SaaS) answer to the "curator reads traces" half of the pattern. The memory_backed_agent sample is the only public code wiring them together.
- No LangChain example takes a flag-tool output as curator input.

### Gaps
- No public LangSmith cookbook titled "curating knowledge" was found.
- I did not verify whether Engine writes Context Hub skill changes automatically or only proposes them; docs suggest it only proposes.

## Q3: LangChain blog posts with accompanying code (memory, agents that learn, reflection, skills)?

### Takeaway
Most relevant posts are conceptual and ship no code. The knowledge-factory post itself has no repo; its only GitHub link is the OKF project. Code exists only for Context Hub (llm-wiki, memory_backed_agent) and for the Deep Agents/LangMem libraries.

### Cited Findings
- **"How to build a knowledge factory"** — Harrison Chase, Nov 21, 2026. Architecture: a flag tool for missing or incorrect knowledge; a scheduled background curator reading flags, Notion/Slack and traces and turning patterns into skills; storage can be GitHub skills, a Notion file, OKF in Context Hub, or Neo4j. It links Managed Deep Agents schedules docs and Deep Agents skills docs. **No code or reference implementation provided.** — [blog](https://www.langchain.com/blog/knowledge-factory)
- **"What We've Learned Building Proactive Agents"** — Sydney Runkle, Nov 17, 2026. Describes "dreaming": "a scheduled background job that reads through the agent's recent traces" to update memory. No code repo links; it links Deep Agents memory and MDA schedules docs. — [blog](https://www.langchain.com/blog/what-weve-learned-building-proactive-agents)
- **"How we built Agent Builder's memory system"** — Feb 21, 2026. A background reflection process and a cron job are described as *future plans*; skills are semantic memory edited in-run. No repo links. — [blog](https://www.langchain.com/blog/how-we-built-agent-builders-memory-system)
- **"Components of building a company harness"** — Harrison Chase and Caspar Broekhuizen, Oct 24, 2026. Covers location, identity, global and user memory, sandboxes and scheduled runs across GTM Agent, OpenSWE and Content Studio. No repo links. — [blog](https://www.langchain.com/blog/components-building-company-harness)
- Other relevant posts without curator code: "How to Build Memory into AI Agents" ([blog](https://www.langchain.com/blog/how-to-give-your-agent-memory)), "LangMem SDK launch" ([blog](https://www.langchain.com/blog/langmem-sdk-launch)), "Context Engineering with Deep Agents" ([blog](https://www.langchain.com/blog/context-engineering-deep-agents-remember)), "How our GTM Agent builds consistent, high-quality sales artifacts" (Nov 10, 2026, [blog](https://www.langchain.com/blog/gtm-agent-high-quality-sales-artifacts)), and the Deep Agents memory docs, which note an agent can update skills when it has write access ([docs](https://docs.langchain.com/oss/python/deepagents/memory)).

### Inferences
- Content from Nov 2026 (proactive agents, goals, knowledge factory) is converging on "scheduled background agent over traces", but published code lags the posts.

### Gaps
- I could not open the original X article; the langchain.com blog version was used instead. I did not check whether the X version differs.
- GTM Agent and Content Studio internals are not open source. The `deploy-gtm-agent` Deep Agents example exists but was not inspected for memory or curation.

## Q4: Community repos implementing Harrison's knowledge factory since the post?

### Takeaway
None found. The post is less than one day old. `gh search repos "knowledge factory" --created >=2026-11-18` returned zero results. Older, unrelated "Knowledge Factory" repos exist, plus a few loosely related curator projects.

### Cited Findings
- Zero repos matched "knowledge factory" created on or after 2026-11-18. Code search for `flag_missing_knowledge` returned one unrelated test file. — [GitHub search](https://github.com/search?q=%22knowledge+factory%22&type=repositories)
- Loosely related community repos (not LangChain, and not implementations of the post):
  - **violetfleming47/agent-knowledge-curator**: five skills for capturing institutional knowledge (knowledge mapping, reasoning frameworks, data reading guides, interpretation rules, depth control). Created 2026-06-11, pushed 2026-11-10, 1 star. It is human-guided capture with no background agent. — [repo](https://github.com/violetfleming47/agent-knowledge-curator)
  - **fvanevski/knowledge_agent**: a LangGraph agent with a "Curator" role that maintains a LightRAG knowledge base (per search summary; not inspected). — [repo](https://github.com/fvanevski/knowledge_agent)
  - **Brunimir/Knowledge-Factory**: an agentic personal knowledge management system, pushed 2026-11-15, 2 stars. The name only overlaps; it predates the post. — [repo](https://github.com/Brunimir/Knowledge-Factory)
  - **agenticnotetaking/arscontexta**: methodology docs that mention "knowledge factory". — [repo](https://github.com/agenticnotetaking/arscontexta)
  - Nebius cookbook on building an enterprise knowledge base with OpenWiki (third-party use of LangChain's OpenWiki). — [cookbook](https://dev.nebius.com/cookbook/openwiki-enterprise-knowledge-base)

### Inferences
- Community implementations will likely appear within days to weeks; re-run the searches later.

### Gaps
- GitHub code search indexes default branches only and with lag, so very new repos may be missed.
