# Harrison Chase — "How to build a knowledge factory" (X post + X Article, 21 Nov 2026)

**Retrieval note (read first):** The post *and the full text of the attached X Article* were retrieved verbatim via the fxtwitter JSON API (https://api.fxtwitter.com/hwchase17/status/2124181216719151585), which returns the article's rich-text blocks, link map and image URLs. All quotes marked "Article" below are verbatim from that payload. The three article diagrams were downloaded from pbs.twimg.com and transcribed. Replies to the post itself (97 replies, 37 quotes) could **not** be fetched; reply/critique material below comes from a *separate, earlier* Nov 19 thread surfaced only via search snippets (secondary, lower confidence). A LangChain-blog copy of the same article exists (listed as "Related content", dated Nov 21 2026) but its page could not be fetched directly.

**Post metadata** — [Post](https://x.com/hwchase17/status/2124181216719151585); via [fxtwitter API](https://api.fxtwitter.com/hwchase17/status/2124181216719151585):
- Author: Harrison Chase (@hwchase17), posted Sat 21 Nov 2026 16:40:42 UTC.
- Post text (verbatim): "all our agents at langchain (internal GTM & content agents, LangSmith Engine) have a learning loop with similar pieces / wrote about what we think makes up a \"knowledge factory\"" + link to [X Article 2124180107669766144](https://x.com/i/article/2124180107669766144).
- Article title: "How to build a knowledge factory". Engagement at retrieval (~5.5h after posting): 134,796 views, 1,043 likes, 2,794 bookmarks, 89 reposts, 97 replies, 37 quotes. (Bookmarks ≈ 2.7x likes — a "save for reference" signal.)

---

## Q1. What exactly is a "knowledge factory" per Harrison Chase? What problem does it solve?

### Takeaway
A knowledge factory is "the system" that collects, curates and maintains a representation of a company's tacit, scattered operating knowledge so it can be passed to agents as context; Chase argues the bottleneck for enterprise AI is not models or more context but *better knowledge*.

### Cited Findings
- Problem statement (verbatim): "In order to make AI work for your company, the missing bit is not better models, it's not just more context - it's better knowledge. It's knowledge of how your company works, what standards for operating you have in place, where data is stored and how it's accessed." — [Article](https://x.com/i/article/2124180107669766144) (via [fxtwitter](https://api.fxtwitter.com/hwchase17/status/2124181216719151585))
- Tacit knowledge (verbatim): "Your most efficient employees have this knowledge in their head. They know who to talk to, where to go to answer questions, why you do things in a particular way. That knowledge is often tacit, implicit, scattered - sometimes present only in their head, sometimes scattered across a variety of documents." — [Article](https://x.com/i/article/2124180107669766144)
- Definition (verbatim): "In order to make AI work for your company, you need to collect, curate, and maintain a representation of that knowledge to pass to agents. The system that helps you do that is what we're calling a knowledge factory." — [Article](https://x.com/i/article/2124180107669766144)
- Context vs knowledge (verbatim): "Context is what an agent has available when doing a task. Knowledge is the reusable understanding we maintain so it can do that task correctly: what a metric means, which source to trust, or how we handle a particular situation. Sometimes written down, often not." / "A knowledge factory turns scattered documents and experience into knowledge that can become context for future work." — [Article](https://x.com/i/article/2124180107669766144)
- Knowledge is not *all* context (verbatim): "So knowledge is a form of context that the agent will get, but it's often not (and shouldn't be) the only context the agent gets. Other types of context you already ingest/store reliably, and that can just be provided directly to the agent." — [Article](https://x.com/i/article/2124180107669766144). The "context" link points to LangChain's [context engineering post](https://www.langchain.com/blog/context-engineering-for-agents).
- Analogy to software factories (verbatim): "The idea of software factories has risen sharply over the past year and a half. The idea is that rather than having your best engineers actually build software, they should build the factory (the systems) to help everyone at the company build software more efficiently… General knowledge work is now following a similar path. Agents are good enough to make presentations, launch videos, do outbound… But in order for them to accomplish those tasks they need all that tacit, implicit, scattered knowledge." — [Article](https://x.com/i/article/2124180107669766144). (Related: LangChain's own software-factory write-up by Brace Sproul, [X article](https://x.com/BraceSproul/article/2078558852921094253) — surfaced by search, not read.)
- Where to invest (verbatim): "That is where you should devote resources. You need to build that knowledge, and more importantly a factory to collect, curate and maintain that knowledge. That is what will let you outsource more general knowledge tasks to agents." — [Article](https://x.com/i/article/2124180107669766144)
- Conclusion (verbatim): "The goal isn't to document everything before agents can start working. It's to build a system where doing the work reveals what knowledge is missing, and resolving those gaps makes future work better. Start with one recurring workflow, inspect where agents struggle, and close that loop." — [Article](https://x.com/i/article/2124180107669766144)
- Internal usage claim: "Our internal GTM and content studio agents are powered by a knowledge factory. LangSmith Engine (our agent that runs over traces and suggests fixes) maintains a knowledge factory per agent as well." — [Article](https://x.com/i/article/2124180107669766144); linked: [GTM agent post](https://www.langchain.com/blog/how-we-built-langchains-gtm-agent), [design agent post](https://www.langchain.com/blog/design-agent), [LangSmith Engine](https://www.langchain.com/langsmith/engine).

### Inferences
- The core design principle is *emergent, work-driven* knowledge capture ("doing the work reveals what knowledge is missing") rather than up-front documentation projects.
- "Knowledge factory" is a framing/pattern, not a named product; LangChain's commercial angle is Context Hub + LangSmith (traces/Engine) + managed deep-agent schedules, and the article ends with a sales CTA ("we can help").
- "Per agent" knowledge factory in LangSmith Engine implies the pattern scales down to a single agent's memory, not only a company-wide knowledge base.

### Gaps
- No quantitative results (accuracy gains, volume of flags, curator cadence metrics) are given in the article.

---

## Q2. What components/stages does he describe (ingestion, extraction, curation, storage, retrieval, feedback)?

### Takeaway
Chase defines (a) three *types* of knowledge — Skills, Domain knowledge, Data access guidance — and (b) three *factory* pieces — agent flagging, a background curator agent, and a (deliberately unopinionated) storage layer — wired into a loop where curated knowledge is fed back to working agents as context.

### Cited Findings
**Knowledge types (verbatim, with diagram 1):**
- "How to do the work — Skills. Procedures, instructions, and scripts for accomplishing tasks the way your company expects." Elaboration: "Often times, these were never written down before (instead passed coworker to coworker). You should strive to write them down." — [Article](https://x.com/i/article/2124180107669766144)
- "How the business works — Domain knowledge. Definitions, policies, and facts about your products, customers, competitors, and organization." Elaboration: "knowledge that does not go stale frequently… often information that was written down - but was usually incomplete (or incorrect) just due to the sheer amount of knowledge here." — [Article](https://x.com/i/article/2124180107669766144)
- "Where to get current information — Data access guidance. Which sources to use, what data lives where, and how to query it." Elaboration: "You should have a good data strategy (Snowflake, Databricks, etc)… If the source of truth of data is there already, and it's complete and up to date - there's no need to maintain a separate copy. Rather, the new thing you'll want to maintain is clear instructions on what data lives where and how to query it." — [Article](https://x.com/i/article/2124180107669766144)
- Diagram 1 (transcribed from [image](https://pbs.twimg.com/media/HXqawXSbYAABTuC.jpg)): three cards — **Skills / How to do the work** → SKILL.md "Reports in LangChain style" → stored in *GitHub*; **Domain knowledge / How the business works** → Wiki page "How we calculate ARR" → *Company wiki*; **Data access guidance / Where to get current information** → Query guide "Revenue: BigQuery and Salesforce" → *Context Hub*.

**Factory pieces (verbatim):**
- Framing: "Don't try to maintain it manually - that's a herculean effort. Rather, you will want to create a system for maintaining it." — [Article](https://x.com/i/article/2124180107669766144)
- (1) "A way for agents to flag missing knowledge: One of the best ways to learn what pieces of knowledge are missing is to have agents flag it as they are working. If they are asked to do something, and can't find information, or find information that they discover is wrong - they should flag it! Give the agent a tool to at a minimum report what is wrong, and optionally suggest the correct update." — [Article](https://x.com/i/article/2124180107669766144)
- (2) "The curator agent: an agent to update, curate, and maintain this knowledge" (see Q3). — [Article](https://x.com/i/article/2124180107669766144)
- (3) "Storage for the knowledge: In some ways, this is actually the least important thing. You can store this knowledge in skill format in GitHub. In a single file in Notion. In OKF format in LangSmith Context Hub. In a knowledge graph in Neo4j. The curator agent should know how to interact with all of these formats (not that hard). In other ways, this is the least explored area. How do you represent memory? As an industry, we've converged on skills for 'procedural memory'. For more semantic memory, a different standard will likely emerge (OKF?). It is early and no standard has yet emerged - so it's probably best to not be too prescriptive or overly complicate what this format should look like." — [Article](https://x.com/i/article/2124180107669766144). Links in this paragraph: [deepagents skills docs](https://docs.langchain.com/oss/python/deepagents/skills), [OKF repo](https://github.com/open-knowledge-format/open-knowledge-format), [Context Hub intro](https://www.langchain.com/blog/introducing-context-hub), [memory post](https://www.langchain.com/blog/how-to-give-your-agent-memory).
- Diagram 2 (transcribed from [image](https://pbs.twimg.com/media/HXqazU-bIAAhZzt.jpg)): **Agents doing work** → *Flags (missing or wrong knowledge)* and → *Agent traces*; **Raw sources (Notion and Slack)**; Flags + Agent traces + Raw sources → **Curator agent ("Runs in the background on a cadence")** → *Updates* → **Knowledge store (Skills, Domain knowledge, Data access guidance)** → *As context* → back to Agents doing work.

**End-to-end example (revenue report), verbatim highlights:**
- Base context: "the raw revenue numbers, stored in BigQuery and Salesforce." Knowledge: "Skills: how to create reports in LangChain style. These are stored in GitHub in the standard skills format." / "Long duration knowledge: the way we calculate ARR. This is stored in a company wiki." / "How to access quickly changing knowledge: how to access that raw data in BigQuery/Salesforce. These are also just stored as skills, but this time in Context Hub." — [Article](https://x.com/i/article/2124180107669766144)
- Run: "Maybe it notices that we renamed a column in BigQuery. It figures out the correct column on the fly. It uses its tool it has to report issues to flag this, and suggest the proper column name." — [Article](https://x.com/i/article/2124180107669766144)
- Human-in-the-loop: "After it creates the report, our finance lead works synchronously with the agent to fix a few formatting issues, including telling it to use a new header we now need to use for all LangChain documents." — [Article](https://x.com/i/article/2124180107669766144)
- Curation: "That night, the curator agent sees the flagged issue. It also inspects the traces of the agent and notices this back and forth with our finance lead. It updates the relevant skills accordingly (to use the new column when fetching data, and to use the new header when drafting report)." — [Article](https://x.com/i/article/2124180107669766144)
- Diagram 3 (transcribed from [image](https://pbs.twimg.com/media/HXqa3cWbMAAyfJO.jpg)): Agent run (Revenue report; BigQuery renamed column; "Flag with a suggested fix") → Finance lead (After the report; request "New header for all LangChain documents") → Curator agent (That night; reads Agent flag + Trace with the finance lead) → Two skills updated (Data fetching: new column; Report drafting: new header).

### Inferences
- Mapping to the requested stage vocabulary: *ingestion* = curator reading raw sources (Notion, Slack) + traces + flags; *extraction/curation* = curator agent; *storage* = format-agnostic store (GitHub skills / Notion / Context Hub OKF / Neo4j); *retrieval* = knowledge loaded "as context" (implicitly via skills progressive disclosure / Context Hub backend); *feedback* = in-run flag tool + traces of human corrections.
- Note an interesting nuance: the article's revenue example stores data-access guidance as *skills in Context Hub*, while the storage paragraph mentions *OKF in Context Hub* — i.e., Context Hub is presented as the home for both procedural (skills) and semantic (OKF) knowledge.
- Retrieval/serving and conflict resolution between knowledge types are not specified — left to the implementer.

### Gaps
- No schema for the "flag" tool (fields, severity, dedup) is given; only "at a minimum report what is wrong, and optionally suggest the correct update."
- No explicit retrieval mechanism, eval strategy, or versioning/rollback policy is described *in the article* (Context Hub's own docs cover versioning — see Q4).

---

## Q3. What does the curator agent do, and how is human review involved?

### Takeaway
The curator is a separate, background agent run on a schedule that reads raw sources, agent traces and agent-raised flags, and writes updates to the knowledge store; Chase explicitly separates "flagging" (done by working agents) from "fixing" (done by the curator) to prevent contradictory, unruly knowledge. Humans appear as sources of corrections captured in traces; an explicit human approval gate for curator writes is **not** described in the article.

### Cited Findings
- Full curator paragraph (verbatim): "This knowledge should not be kept up to date manually - too much work. And it should not be kept up to date solely by the agents that use it - they are great at flagging what's wrong or missing, but fixing it requires deep understanding of the underlying knowledge and other sources of data. Asking agents - who are mainly trying to accomplish their own goals - to properly update and maintain this knowledge will cause it to become unruly and full of contradictions. Rather - you will want a curator agent that runs in the background, on some cadence, to update this knowledge. It should have access to all the raw sources of data (Notion, Slack, etc) where this knowledge may be scattered. It should have access to agent traces, so it can see how people are trying to use agents and codify that into skills. It should have access to the things that agents have flagged as wrong (the above section)." — [Article](https://x.com/i/article/2124180107669766144)
- "Runs in the background, on some cadence" links to [Managed Deep Agents schedules](https://docs.langchain.com/langsmith/python/managed-deep-agents-schedules); "agent traces" links to [LangSmith Observability](https://www.langchain.com/langsmith/observability). — [Article link map via fxtwitter](https://api.fxtwitter.com/hwchase17/status/2124181216719151585)
- Human role in the article: humans correct the agent synchronously (finance lead), and the curator mines those traces ("notices this back and forth with our finance lead") to update skills. — [Article](https://x.com/i/article/2124180107669766144)
- Related LangChain writing on review: Context Hub lets "teammates can review, comment, and promote versions" of context; every change is versioned (commits, rollback, tagging). — [Introducing LangSmith Context Hub, H. Chase, 13 May 2026](https://www.langchain.com/blog/introducing-context-hub) (via WebFetch summary)
- Related loop: "capture traces, analyze traces, and update memory" — traces as evidence, LangSmith Engine finds recurring issues, approved changes stored in Context Hub, "future runs load it back into the agent". Design principles: "Not everything should be a memory update"; "Make sure future runs actually read the update!"; protect behaviour-shaping memory updates with evals. — [How To Give Your Agent Memory, J. Broekhuizen, 24 Jun 2026](https://www.langchain.com/blog/how-to-give-your-agent-memory)
- Company-harness post: human review of agent output happens in Slack for one-offs, but for backlogs "it's not a fun experience at all to track those from Slack messages", so LangChain built a custom review UI for GTM-agent emails; memory is split into "Global memory" and "User memory", and "Agents decide which facts they want to remember to which level of memory." — [The five components of building a 'company harness', H. Chase & C. Broekhuizen, 24 Oct 2026](https://www.langchain.com/blog/components-building-company-harness)

### Inferences
- The separation "users flag / curator fixes" is the key architectural decision — analogous to a single-writer pattern that keeps one consistent author over the corpus.
- Human approval of curator edits is implied by LangChain's tooling (Context Hub versioning/promote, Engine "approved changes") but not stated in the knowledge-factory article; a design should add an explicit review gate (e.g., PR-style diffs) — which OKF's `verified`/trust-tier fields directly support (see Q5).
- The curator needs read access to many systems (Notion, Slack, traces, data warehouse) and write access to the store — a meaningful permissions/security surface the article does not discuss.

### Gaps
- Curator cadence specifics (nightly is the only example), conflict-resolution strategy, dedup of flags, and how the curator decides between editing a skill vs. domain doc vs. data guide are not specified.

---

## Q4. Which LangChain products or open-source projects does he reference? Any linked blog post?

### Takeaway
The article links ~12 resources: LangSmith Engine, LangSmith Observability (traces), Managed Deep Agents schedules, Deep Agents skills, LangSmith Context Hub, the OKF GitHub repo, and LangChain blog posts on context engineering, GTM agent, design agent, agent memory, and the "company harness".

### Cited Findings
Link map extracted verbatim from the article entity map — [fxtwitter payload](https://api.fxtwitter.com/hwchase17/status/2124181216719151585):
- Context engineering: https://www.langchain.com/blog/context-engineering-for-agents
- GTM agent: https://www.langchain.com/blog/how-we-built-langchains-gtm-agent
- Content studio / design agent: https://www.langchain.com/blog/design-agent
- LangSmith Engine ("our agent that runs over traces and suggests fixes"): https://www.langchain.com/langsmith/engine
- Curator cadence → Managed Deep Agents schedules: https://docs.langchain.com/langsmith/python/managed-deep-agents-schedules
- Agent traces → LangSmith Observability: https://www.langchain.com/langsmith/observability
- Skill format → Deep Agents skills: https://docs.langchain.com/oss/python/deepagents/skills
- OKF → https://github.com/open-knowledge-format/open-knowledge-format
- LangSmith Context Hub → https://www.langchain.com/blog/introducing-context-hub
- Memory → https://www.langchain.com/blog/how-to-give-your-agent-memory
- "We've built this at LangChain" → https://www.langchain.com/blog/components-building-company-harness
- Contact sales → https://www.langchain.com/contact-sales
- Context Hub facts: "a place to store, version, and collaborate on the files that define how agents behave"; "many agent failures come from missing, stale, or poorly managed context"; AGENTS.md and Skills "have become a useful convention for procedural memory" but lack "a shared spec for versioning them, tagging them by environment, or making them portable"; describes an "LLM wiki" pattern where an agent "creates a folder of files that future agents can reference"; LangChain working with Elastic, MongoDB, Pinecone, Redis on "an open standard for agent memory". — [Introducing LangSmith Context Hub](https://www.langchain.com/blog/introducing-context-hub)
- Context Hub mechanics (search summary, secondary): every change creates a commit with rollback/tagging; SDK push/pull of agent and skill repos; Deep Agents can use it via a `ContextHubBackend`; sandboxes can mount Context Hub repos read-only. — [Context Hub docs (Managed Deep Agents)](https://docs.langchain.com/langsmith/python/managed-deep-agents-context-hub), [Manage contexts with the SDK](https://docs.langchain.com/langsmith/manage-contexts-sdk)
- A LangChain blog version titled "How to build a knowledge factory" by Harrison Chase, dated Nov 21 2026 (~6 min read), is listed as related content; its hero image alt-text: "scattered messages and notes feed through a press and come out as a stack of SKILL.md files." — [company-harness post related-content](https://www.langchain.com/blog/components-building-company-harness); also listed on [The Art of Loop Engineering](https://www.langchain.com/blog/the-art-of-loop-engineering)

### Inferences
- The LangChain stack implied for a knowledge factory: Deep Agents (curator + working agents, skills), LangSmith tracing (evidence), LangSmith Engine (trace analysis), Managed Deep Agents schedules (curator cadence), Context Hub (versioned store; OKF/skills).
- LangGraph is not mentioned explicitly in the article (Deep Agents is built on it, but that is background knowledge, not from the post).

### Gaps
- The blog-hosted copy's exact URL was not confirmed (likely langchain.com/blog/... slug); not fetched.
- Whether Context Hub has native OKF validation/rendering is unconfirmed — the article says "In OKF format in LangSmith Context Hub", but a search found no Context Hub docs mentioning OKF.

---

## Q5. What did notable replies/quote-tweets add or critique? (and: is OKF a good fit?)

### Takeaway
Replies to the Nov 21 post could not be retrieved. A related Nov 19 teaser thread drew a pushback from Snowflake CEO Sridhar Ramaswamy ("most companies don't need a knowledge factory") and a reply from Chase citing inconsistent revenue definitions; these come only from search snippets. OKF (v0.3) — which Chase floats as a possible semantic-memory standard — supplies exactly the provenance/trust/freshness/lifecycle fields a curator-maintained corpus needs.

### Cited Findings
**Replies (secondary, low confidence — search snippets only, not fetched):**
- Nov 19 Chase post (as quoted in search results): "saas runs on software, so everyone is building a software factory / the hardest part of building agents is the context (or knowledge that they have) / if youre building agents, you should be building a knowledge factory" — via web search snippet referencing [@RamaswmySridhar profile page](https://x.com/RamaswmySridhar) and [@swyx profile page](https://x.com/swyx)
- Sridhar Ramaswamy (@RamaswmySridhar, X bio: CEO @snowflake): "agree, one edit: most companies don't need a knowledge factory." — same snippet source; not independently verified
- Chase reply (reported via a swyx post): "having inconsistent ways to define revenue is exactly why you'd need knowledge factory for your company! centralize tacit or implicit knowledge, make those readily available to everyone"; swyx reportedly added that companies must fix conflicting definitions first and agents make the problem costlier faster. — same snippet source; secondhand

**OKF (Open Knowledge Format) facts — primary:**
- "OKF is a universal, vendor-neutral format for representing knowledge as plain markdown files with YAML frontmatter. It is not tied to any particular agent, framework, model provider, or serving system." Bundles live in git, so "knowledge curation becomes a normal software-engineering activity." Auto-generated `index.md` gives "progressive disclosure"; concepts link via markdown links ("graph-shaped, not just tree-shaped"). Ships Agent Skills `okf-generate` and `okf-consume` installable as a Claude Code plugin. — [OKF README](https://github.com/open-knowledge-format/open-knowledge-format)
- Spec v0.3 motivation (verbatim): "Agents write and maintain the corpus continuously. When agents generate most concepts, a consumer needs answers…: provenance, trust, freshness, lifecycle, attestation." Only required frontmatter key is `type`. — [OKF SPEC.md v0.3](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
- Trust: `generated: {by, at}` and `verified: [{by, at}]`; actors `human:`, `team:`, `process:`, or `<producer>/<version>`. Tiers: unverified / machine-confirmed / human-reviewed; a verification is current only if `at >= generated.at` — "When an agent rewrites a concept after a human review, the human did not read the new text. Thus the concept is not human-reviewed until a human confirms it again." — [SPEC §5.2–5.3, §7](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
- Provenance: `sources` with `resource`, `id`, `author`, `usage_count`, `last_modified`; per-claim attribution via footnotes keyed to source ids. Lifecycle: `status: draft|stable|deprecated`, `superseded_by`, `stale_after` (absolute instant). Reserved `index.md` (directory listing/bundle metadata incl. `okf_version`) and `log.md` (dated change history). Extension keys `x-<producer>-<name>`. — [SPEC §3, §5, §8, §9](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
- `SKILL.md`, `README.md`, `AGENTS.md` without `type` frontmatter are explicitly allowed inside a bundle and are skipped as non-concepts. — [SPEC §3.2](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
- Attested Computation concepts (`runtime`, `parameters`, `executor`, `attester`): the agent "MAY only supply values for the declared parameters… MUST NOT write or edit the computation"; worked example is a revenue SQL computation with `verified: {by: "human:…"}` and `stale_after`. — [SPEC §10](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
- Origin: OKF is described as a Google Cloud-originated spec (earlier versions in GoogleCloudPlatform/knowledge-catalog; coverage June 2026). — [MarkTechPost, 16 Jun 2026](https://www.marktechpost.com/2026/06/16/google-cloud-introduces-open-knowledge-format-okf-a-vendor-neutral-markdown-spec-for-giving-ai-agents-curated-context/); [GoogleCloudPlatform/knowledge-catalog SPEC](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) (search results; not read in full)

### Inferences
- OKF maps cleanly onto Chase's taxonomy for **Domain knowledge** (type: Metric/Policy/Playbook/Glossary) and **Data access guidance** (type: BigQuery Table/Reference with `resource`, Schema/Examples sections, Attested Computations for sanctioned metrics like ARR). **Skills** are best kept as standard `SKILL.md` (Chase: industry "converged on skills for procedural memory"); OKF tolerates SKILL.md files inside a bundle, or an executor can point to a skill (`executor.resource`).
- OKF's `generated`/`verified` split directly encodes the curator-vs-human review gap left open in the article: curator writes set `generated.by: curator-agent/<ver>` and `status: draft`; human approval appends `verified: human:<id>`; `log.md` records each curator run; `stale_after` drives the curator's re-check queue; `superseded_by` handles renames (e.g., the renamed BigQuery column example).
- Chase himself is non-committal ("OKF?", "best to not be too prescriptive"), so adopting OKF is consistent with his advice as long as the curator remains format-agnostic.
- Ramaswamy's "most companies don't need" critique (if accurate) suggests scoping: start with one recurring workflow, as the article's conclusion also advises.

### Gaps
- Direct replies/quote-tweets to the Nov 21 post (97 replies / 37 quotes) were not retrievable (X requires login; fxtwitter returns no replies). The Nov 19 exchange is known only from search-engine snippets — treat as unverified.
- No evidence found of LangSmith Context Hub having native OKF tooling despite the article's phrasing.
