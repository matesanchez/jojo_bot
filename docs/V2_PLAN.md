# JoJo Bot v2.0 — Nurix Knowledge Hub

**Status:** Draft plan (April 2026) — for review, not yet ratified
**Author:** Mateo de los Rios (with AI co-drafting)
**Supersedes:** v1.0 scope, which shipped as the "Cytiva ÄKTA / Protein Purification Expert"
**Target v2.0 pitch:** *JoJo Bot, the Nurix Knowledge Hub — a self-maintaining internal wiki that reads SharePoint, the Public Drive, and NurixNet, then answers any Nurix question with grounded citations, rich outputs, and a compounding memory.*

---

## 1. Executive summary

v1.0 of JoJo Bot is a competent but narrow RAG wrapper: 232 ÄKTA/Cytiva PDFs + Nurix SOPs in ChromaDB, Claude Sonnet on top, a Next.js chat UI, and a self-contained Windows .exe distribution. It works well for what it is, but it has a ceiling. Each user's ChromaDB is a private silo, chunks are retrieved in isolation, and Jojo can only answer what a single retrieval pass finds. It is not, in any structural sense, a *knowledge system*.

v2.0 flips that model. Instead of a vector store that the LLM searches on every query, v2.0 maintains a **persistent, LLM-authored wiki** — a directory of interlinked Markdown files compiled from Nurix source systems. The LLM does the bookkeeping (reading new sources, updating entity pages, flagging contradictions, writing summaries, filing outputs) so that answers to future questions land on *already-synthesized* knowledge rather than raw chunks. Explorations you run today become wiki pages tomorrow. The system compounds.

Karpathy's `llm-wiki` gist frames the core pattern; farzaa's `wiki` skill gives us a proven command surface; Ars Contexta contributes a fresh-context-per-phase subagent architecture; graphify provides the graph layer and token-reduction benchmark; tig-monorepo inspires the modular repo layout we'll use to keep components swappable. Obsidian is explicitly *not* a dependency — we re-create its essential features (graph view, backlinks, live preview, Marp rendering) inside the JoJo Bot frontend so the entire user experience lives in one app.

Deployment is hybrid: Phase 1–4 ship as a single-user local app (same distribution model as v1.0), with the wiki synced to OneDrive/SharePoint so the team sees a shared vault. A later phase promotes the ingest/compile pipeline to a Nurix-hosted server so clients become thin.

---

## 2. Design principles (non-negotiable)

These are the invariants we'll protect across every phase. When trade-offs come up later, re-read this section first.

1. **The wiki is plain Markdown.** No DB, no proprietary format, no vendor lock-in. A scientist with VS Code and `git` can read and edit the wiki forever, even if JoJo Bot disappears tomorrow.
2. **The LLM owns the wiki.** Humans curate sources and ask questions; the LLM writes, updates, backlinks, and maintains the pages. Manual edits are allowed but rare — they are treated as user feedback that the linter reconciles.
3. **Every claim traces to a source.** Every wiki page has a frontmatter `sources:` array pointing at raw-entry IDs (SharePoint doc IDs, NurixNet URLs, etc.). No untraceable claims.
4. **EXTRACTED vs INFERRED is always labeled** (graphify's convention). A wiki edge or claim is either drawn directly from a source (`EXTRACTED`) or a reasoned inference (`INFERRED` with a confidence score). Users always know what Jojo *read* vs what it *guessed*.
5. **Raw is immutable.** Once pulled from SharePoint/NurixNet into `raw/`, the snapshot is read-only. Re-syncs create new versioned snapshots; they don't overwrite history.
6. **Fresh context per phase.** Following Ars Contexta's `/ralph` pattern, each pipeline phase (ingest, compile, lint, Q&A synthesis) runs in its own subagent with a clean context window. Long-running maintenance never gets starved by history.
7. **Outputs file back into the wiki.** A presentation, an analysis, a comparison table — if you asked for it, it's likely valuable. The output is written as a new wiki page (or as a new section of an existing page) unless you opt out.
8. **Security before scale.** Nurix PII, trade secrets, and regulated data (GxP, CTA, clinical) never leave the user's machine or Nurix-approved infrastructure. The Claude API is the only external call, and it uses a vetted enterprise contract.
9. **Small is beautiful.** Until the wiki exceeds ~500 articles or ~1M tokens, we do *not* reach for RAG/embeddings. We rely on index-first navigation (karpathy's approach). RAG is added only when measured necessary (Phase 4 includes the escalation criteria).
10. **JoJo Bot is one app.** The user does everything — chat, browse wiki, view graph, render slides, review raw — inside the JoJo Bot window. Obsidian, VS Code, PowerPoint are optional external editors but never required.

---

## 3. Reference architecture

### 3.1 Three logical layers (from karpathy, adapted)

```
+------------------------------------------------------------------+
|                           USER (Mateo)                           |
|   asks questions, curates sources, reviews outputs, occasional   |
|   manual edit or approval of wiki changes                        |
+------------------------------------------------------------------+
                               | chat / IDE tab
                               v
+------------------------------------------------------------------+
|                        JoJo Bot v2.0 (app)                       |
|  Next.js frontend  <->  FastAPI backend  <->  Claude API         |
|   - Chat tab               - REST + SSE         (Sonnet + Opus)  |
|   - Wiki IDE tab           - Subagent runner                     |
|   - Raw tab                - Pipeline engine                     |
|   - Graph tab              - Linter worker                       |
+------------------------------------------------------------------+
                               |
                               v
+------------------------------------------------------------------+
|                         Three data layers                        |
|                                                                  |
|   raw/        immutable snapshots from source systems            |
|   wiki/       LLM-authored Markdown, the compiled knowledge      |
|   schema/     CLAUDE.md-equivalent config: conventions, taxonomy |
|                                                                  |
+------------------------------------------------------------------+
                               |
                               v
+------------------------------------------------------------------+
|                        Source systems                            |
|   SharePoint sites  |  Public Drive (SMB/OneDrive)  |  NurixNet  |
|   Teams/Outlook*    |  Asana*  |  Benchling*  |  GitHub (dev)*   |
|                                                                  |
|   * stretch — phased in once the core is proven                  |
+------------------------------------------------------------------+
```

### 3.2 Repo layout (inspired by tig-monorepo's modular split)

tig-monorepo's value here is not the protocol domain — it's the discipline of splitting one repo into a handful of small, swappable crates (`tig-algorithms`, `tig-protocol`, `tig-runtime`, `tig-verifier`, `tig-benchmarker`). We mirror that: each piece of v2.0 becomes its own Python package so we can swap implementations (e.g. replace the SharePoint connector with a Box connector) without touching the rest.

```
jojo_bot/
├── CHANGELOG.md
├── README.md
├── docs/
│   ├── V2_PLAN.md            # <- this document
│   ├── WIKI_SCHEMA.md        # conventions the LLM must follow
│   ├── ADR/                  # architecture decision records
│   └── runbooks/             # operational procedures
├── schema/                   # schema layer (the "constitution")
│   ├── CLAUDE.md             # top-level instructions for all LLM calls
│   ├── wiki_schema.md        # page taxonomy, frontmatter, writing standards
│   ├── ingest_rules.md       # per-source parsing + redaction rules
│   └── taxonomy.yaml         # directory taxonomy (programs, targets, assays…)
├── raw/                      # immutable source snapshots  (.gitignored)
│   ├── sharepoint/
│   │   └── <site-id>/<doc-id>/<version>.md
│   ├── drive/
│   ├── nurixnet/
│   └── _index.json           # manifest of every raw file + sha256 + source URL
├── wiki/                     # LLM-authored compiled wiki (.gitignored but
│   │                         #   synced to OneDrive/SharePoint for sharing)
│   ├── _index.md             # content-oriented master index
│   ├── _log.md               # append-only chronological log
│   ├── _backlinks.json       # reverse link index
│   ├── _absorb_log.json      # which raw entries have been absorbed
│   ├── _graph.json           # god-node graph (graphify-style)
│   ├── programs/             # Nurix programs (CELMoDs, DACs, …)
│   ├── targets/              # BTK, IRAK4, CK1α, …
│   ├── assays/
│   ├── proteins/
│   ├── methods/              # purification, expression, crystallography
│   ├── SOPs/
│   ├── instruments/
│   ├── people/               # scientists, departments, external collaborators
│   ├── concepts/             # degraders, E3 ligases, ternary complex, …
│   ├── decisions/
│   ├── outputs/              # Q&A outputs filed back into the wiki
│   └── archive/              # deprecated or superseded articles
├── packages/                 # the "crates" — each installable separately
│   ├── jojo_ingest/          # source connectors + raw/ writer
│   ├── jojo_compile/         # raw → wiki compilation (absorb loop)
│   ├── jojo_qa/              # index-first retrieval + synthesis
│   ├── jojo_output/          # Marp, matplotlib, docx, PDF renderers
│   ├── jojo_lint/            # health checks, imputation, contradiction finder
│   ├── jojo_graph/           # god-node graph + community detection
│   └── jojo_core/             # shared utilities: claude client, tokens, types
├── src/
│   ├── backend/              # FastAPI — orchestrator for the packages above
│   └── frontend/             # Next.js — chat + IDE tabs
└── tests/
```

The `packages/` split is the key discipline borrowed from tig-monorepo: each package has its own tests, its own README, its own public API, and can be used as a CLI (`python -m jojo_ingest sharepoint --site …`). This is how we avoid a 50-file "main.py" and how we keep the codebase hackable for a team of 1–3.

### 3.3 The schema layer (the "constitution")

Taken straight from karpathy and Ars Contexta: there is a top-level `schema/CLAUDE.md` that every LLM call reads first. It declares conventions, the absorption loop, the writing tone (Wikipedia-flat, no peacock words), the frontmatter format, the directory taxonomy, and the anti-cramming / anti-thinning rules from farzaa. It is the single most important file in the repo. If you change nothing else but `CLAUDE.md`, you change how the whole system behaves. This is where v2.0's personality lives.

---

## 4. The v1.0 → v2.0 delta

| Concern | v1.0 | v2.0 |
| --- | --- | --- |
| Sources | 232 Cytiva PDFs + Nurix SOPs, hand-uploaded | SharePoint + Public Drive + NurixNet, auto-synced |
| Storage | ChromaDB vector store, opaque | `raw/` + `wiki/` Markdown, human-readable |
| Retrieval | Vector search + web fallback | Index-first (karpathy), RAG as escalation |
| Answer grounding | Per-query retrieval | Pre-compiled wiki pages → much higher signal |
| Outputs | Chat text + protocol `.docx` | Markdown, Marp, matplotlib, docx, pptx filed back into wiki |
| Maintenance | Manual doc upload | Periodic auto-lint, contradiction detection, gap-filling |
| Scope | Protein purification | Any Nurix knowledge — programs, targets, assays, SOPs, people |
| App window | Chat-only | Chat + Wiki IDE + Raw browser + Graph view |
| Distribution | Standalone .exe, per-user ChromaDB | Standalone .exe (unchanged) + OneDrive-synced wiki; later, optional shared server |

---

## 5. Phase roadmap

Each phase below has: goal, deliverables, architectural detail, tech choices, cross-walk to the reference repos, risks, and an exit criterion. Phases 1–4 are the MVP. Phase 0 is scoping/prep. Phases 5–7 are post-MVP, and 8 is exploratory.

### Phase 0 — Foundation & prep (weeks 0–2)

**Goal.** Decide the open architectural questions, set up the scaffolding, and get IT conversations moving before coding starts.

**Deliverables.**
- `schema/CLAUDE.md` v0: first pass at the constitution, taxonomy, writing standards (adapted from farzaa + Ars Contexta).
- `schema/wiki_schema.md`: page templates, frontmatter spec, length targets.
- `schema/taxonomy.yaml`: first-draft directory structure (programs, targets, assays, methods, proteins, concepts, SOPs, people, instruments, decisions, outputs, archive). This will evolve.
- `docs/ADR/0001-wiki-over-rag.md`: architecture decision record explaining why we're choosing LLM-compiled wiki over pure RAG. Cites karpathy's gist as the design source.
- `docs/ADR/0002-monorepo-split.md`: explains the `packages/` layout and rationale (tig-monorepo influence).
- IT ticket filed for Microsoft Graph API app registration (SharePoint + OneDrive scopes) *and* a fallback plan if IT blocks it.
- Repo scaffolding: `packages/jojo_core`, `packages/jojo_ingest`, empty `raw/`, empty `wiki/`, test harness, CI (GitHub Actions) that runs linters and tests.
- Budget model: estimated Claude API spend per week for ingest + compile + Q&A + lint at three corpus sizes (100, 500, 2000 raw docs).

**Key decisions to lock now.**
- **Wiki storage location.** Default: `%USERPROFILE%\OneDrive - Nurix Therapeutics\JojoBot\wiki\`. Puts it under OneDrive so team members auto-share the vault without a server. Fallback: local-only, user can manually publish.
- **Raw storage location.** Same pattern — under OneDrive by default, so that if five people run JoJo Bot they all share one `raw/` corpus and don't re-download.
- **Model routing.** Default: Claude Sonnet 4.6 for compile/ingest/Q&A; Claude Opus 4.6 for lint/reweave/breakdown passes (deeper reasoning); Haiku 4.5 for simple classification/routing. Codify in `jojo_core/claude_client.py`.
- **Secrets.** No change from v1.0 — API key lives in `%APPDATA%\JojoBot\config.json`. Graph API client secret stored the same way, encrypted with DPAPI.

**Risks & mitigations.**
- *Risk: IT refuses Graph API access.* Mitigation: Phase 1 supports a "user-local sync" fallback using OneDrive Files On-Demand — Jojo reads from `%OneDrive%\…` on disk instead of the Graph API. Slower and misses SharePoint sites not synced locally, but unblocks development.
- *Risk: Nurix data can't go to Anthropic under normal T&Cs.* Mitigation: confirm the Nurix/Anthropic enterprise MSA covers the relevant data classes (GxP, confidential R&D). If not, scope Phase 1 to non-regulated sources only and escalate to Legal.

**Exit criterion.** Schema files reviewed by Mateo + 1 scientist for domain sanity; IT ticket acknowledged; monorepo compiles and tests pass CI.

---

### Phase 1 — Data ingest: building `raw/` (weeks 2–8)

**Goal.** For every source system, produce a connector that writes idempotent, versioned Markdown snapshots into `raw/<source>/<id>/<version>.md`. No LLM work yet — ingest is mechanical.

**Deliverables — connectors.**

| Connector | Auth | What it does | Libraries |
| --- | --- | --- | --- |
| `jojo_ingest sharepoint` | MS Graph OAuth (client-credential if app-only; device-code if user) | Walks site → document libraries → files; converts .docx / .xlsx / .pptx / .pdf → Markdown; writes one `.md` per file with full frontmatter | `msgraph-core`, `mammoth` (docx→md), `openpyxl`, `python-pptx`, `PyMuPDF` (reuse from v1.0) |
| `jojo_ingest drive` | SMB + local path fallback | Same as SharePoint but over the shared drive mount. Handles pdfs, office docs, images, `.txt` | `smbprotocol`, `watchdog` for change detection |
| `jojo_ingest nurixnet` | Session cookie or basic auth (see below) | Crawls NurixNet article index, renders each page, strips nav/chrome, converts HTML → Markdown, downloads images locally | `httpx`, `trafilatura` (content extraction), `html2text`, `playwright` fallback for JS-heavy pages |
| `jojo_ingest teams` *(stretch)* | MS Graph | Captures channel messages + meeting transcripts where allowed | `msgraph` |
| `jojo_ingest benchling` *(stretch)* | Benchling API | Pulls entry notebooks, protocols, assay results | `benchling-sdk` |
| `jojo_ingest asana` *(stretch)* | Asana API | Project and task descriptions for program context | `asana` |

**Core design decisions.**

- **One raw file = one logical source entry.** A 30-page PDF is one raw file. A SharePoint `.xlsx` with ten sheets is one raw file (ten sections). A Confluence-style NurixNet article is one raw file.
- **Idempotency.** Running ingest twice must produce the same `raw/`. Each file hashes to a stable ID (sha256 of canonicalized content). If a re-sync finds the content unchanged, no new file is written. If content changed, a new version is written next to the old (never overwrite), and `_index.json` records the version history.
- **Frontmatter is mandatory.** Every raw file has YAML frontmatter with `id`, `source_type`, `source_url`, `source_id`, `title`, `author`, `created`, `modified`, `fetched`, `sha256`, `language`, `tags`, `redacted_fields` (if any).
- **Redaction at ingest.** A small pre-LLM regex pass flags PII/PHI/HIPAA patterns (SSNs, DOBs, patient IDs) and writes them as `[REDACTED:pii]` with a pointer to the original location. This keeps us out of trouble even before Legal reviews data categories.
- **`raw/_index.json`.** Mechanical manifest listing every raw file. Purpose: the compile phase reads this to know what exists; the IDE tab renders it as a browsable tree; `kb_manifest.json` from v1.0 is retired in favor of this.

**NurixNet → Markdown (the hardest one).**

- First pass: try `trafilatura` + `html2text` on each article URL. Works for ~80% of static pages.
- Second pass for JS-heavy pages: headless Chromium via Playwright, wait for network-idle, then extract.
- Image handling: download to `raw/nurixnet/<article-id>/assets/` and rewrite `<img src="...">` to relative paths. This matches karpathy's "download images locally" tip and avoids broken URLs later.
- Crawl discipline: respect a seed list + robots.txt. Maintain a `nurixnet_seen.json` with last-fetched timestamp so incremental crawls only re-pull changed articles.

**Incremental sync.**

- Daily scheduled task (using `mcp__scheduled-tasks__create_scheduled_task` or Windows Task Scheduler) kicks off `jojo_ingest --incremental`. Each connector exposes a `since <iso-date>` flag.
- The ingest step emits a *change manifest* (`raw/_changes/<yyyy-mm-dd>.json`): new files, updated files, deleted files. This manifest feeds Phase 2's incremental compile loop.

**Frontend (Raw tab in JoJo Bot).**

- Tree view of `raw/` with search box.
- Click a file → renders the `.md` preview on the right, with source URL, fetch date, sha256, "open original in browser".
- "Re-sync this folder" button → calls `POST /api/ingest/resync` with a path prefix.
- Status bar shows last sync time per connector, failure counts, pending items.

**Cross-walk to references.**
- farzaa's `/wiki ingest` command shape — we adopt the "one `.md` per entry with YAML frontmatter" output format verbatim.
- karpathy's "Obsidian Web Clipper + local images" tip — we implement the download-images-locally discipline in the ingest step itself, so no manual clipping is needed.
- graphify's `.graphifyignore` pattern — we adopt an analogous `.jojoignore` to exclude noisy folders (build artifacts, generated reports, drafts) from both ingest and compile.

**Risks & mitigations.**
- *Risk: Graph API rate limits.* Mitigation: exponential backoff + delta queries; cache ETags; stagger sites.
- *Risk: PII leakage through a missed redaction.* Mitigation: two-layer defense — regex at ingest + LLM-assisted classification in compile, with a human-review queue for anything flagged.
- *Risk: NurixNet is fragile to re-design.* Mitigation: encapsulate HTML selectors in `packages/jojo_ingest/nurixnet/selectors.py` with good tests; ship a "fallback to raw HTML" mode so we never lose content.

**Effort.** 3–5 weeks for a working SharePoint + Drive + NurixNet with a solid Raw tab in the UI. Teams/Benchling/Asana connectors are each 1–2 additional weeks and can be phased in post-MVP.

**Exit criterion.** `raw/` has ≥ 100 files from ≥ 2 connectors, ingest is idempotent, the Raw tab renders files and shows change history, daily incremental sync runs unattended for 1 week.

---

### Phase 2 — Wiki compilation: the absorb loop (weeks 8–16)

**Goal.** Compile `raw/` into `wiki/` — a coherent, interlinked Markdown knowledge base written entirely by the LLM. This is the beating heart of v2.0.

**The absorb loop** (adapted from farzaa's skill and karpathy's gist).

```
for each unabsorbed raw file, chronologically (or by user priority):
    1. read the file + frontmatter
    2. read wiki/_index.md and wiki/_backlinks.json
    3. match the entry against existing articles
    4. for each touched article: re-read it, decide what new dimension
       this entry adds, update or create the article
    5. for any new entity that meets the threshold, create a stub
       article (≥ 15 lines, or defer)
    6. update _absorb_log.json; append an entry to wiki/_log.md
    7. every 15 entries: rebuild _index.md, _backlinks.json, _graph.json,
       run a quality audit, split any articles > 150 lines
```

**Fresh context per phase (Ars Contexta).** Every file in the absorb loop runs in its own subagent with a clean context window. Long-running compiles never degrade as the conversation grows. The orchestrator just holds the queue; each subagent returns a structured handoff (which files were touched, which new articles created, what open questions remain).

**Scale control.**
- At < 200 raw files: full compile is fast enough to run end-to-end (single night).
- At 200–2000: incremental compile is the default — only files listed in the latest change manifest are absorbed; affected articles are re-read and updated.
- At > 2000: we add a "triage" pre-pass where Haiku classifies each new raw file's relevance (a/b/c) and only a/b files enter the absorb loop. c-files are indexed in `raw/_index.json` but not absorbed (they're still searchable via Q&A escalation).

**Taxonomy — the directory structure.**

Directories emerge from data (farzaa's principle — don't pre-create). We start with a Nurix-specific seed taxonomy in `schema/taxonomy.yaml` and let the LLM evolve it during `/wiki reorganize` passes. First-draft seed:

| Directory | Contents | Who it's for |
| --- | --- | --- |
| `programs/` | Nurix drug programs (NX-1607, NX-5948, …) | Discovery, clinical, BD |
| `targets/` | Protein targets (BTK, IRAK4, CDK2, CELMoDs, …) | Discovery |
| `modalities/` | Degrader classes (DAC, MGD, LYTAC, …) | Discovery |
| `assays/` | In-vitro and in-vivo assay SOPs + results | Biology, DMPK |
| `proteins/` | Protein reagents (constructs, tags, expression systems) | Protein sciences |
| `methods/` | Purification, expression, crystallography, screening | Protein sciences (this is v1.0's home base) |
| `instruments/` | ÄKTA, Biacore, Octet, LC/MS, structural biology kit | Labs |
| `SOPs/` | Operating procedures (includes v1.0's existing SOPs) | Everyone |
| `concepts/` | Ternary complex, hook effect, cooperativity, etc. | Discovery, MedChem |
| `people/` | Nurix scientists + key collaborators (with consent rules) | Everyone |
| `decisions/` | Program go/no-go, chemistry pivots, platform choices | Leadership |
| `outputs/` | Answers filed back from Q&A sessions | Everyone |
| `archive/` | Superseded articles with tombstones pointing at replacements | Audit |

**Page template** (codified in `schema/wiki_schema.md`).

```yaml
---
title: BTK
type: target
created: 2026-04-22
last_updated: 2026-04-22
aliases: ["Bruton's Tyrosine Kinase", "BTK kinase"]
related: ["[[Programs/NX-5948]]", "[[Modalities/DAC]]", "[[Assays/TR-FRET]]"]
sources:
  - { id: "sp:sites/discovery/docs/btk-target-review.docx@v3", type: extracted }
  - { id: "nn:articles/btk-biology-primer", type: extracted }
  - { id: "inferred:web-search-2026-04-15", type: inferred, confidence: 0.7 }
confidence: 0.9
last_lint: 2026-04-22
---

# BTK

{one-paragraph lead — what BTK is in Nurix's world}

## Biology
{...}

## Programs at Nurix
{...}

## Key assays
{...}

## Open questions
{...}

## Timeline
| Date | Event | Source |
|------|-------|--------|

## Backlinks
{auto-generated by rebuild_index}
```

**Writing standards** (adapted from farzaa — these are critical).
- Tone: Wikipedia-flat, encyclopedic, factual. No peacock words ("groundbreaking", "pioneering"). No em dashes.
- Length targets: stub 15–30 lines; standard article 40–120 lines; split at 150.
- Quote discipline: ≤ 2 direct quotes from a source per article; the article is neutral, the source quotes carry the voice.
- Every claim has a source in `sources:`. Unsourced claims are linted out.
- Anti-cramming: if you're adding a 3rd paragraph on a sub-topic to an existing article, that sub-topic is its own article. Anti-thinning: if you're creating a stub, it must clear 15 lines or wait until more material arrives.

**Checkpoints (every 15 absorbs).**
1. Rebuild `_index.md` with all articles and `aliases:`.
2. Rebuild `_backlinks.json` (script scans `[[wikilinks]]`).
3. Rebuild `_graph.json` — god-node graph (see Phase 4 for details).
4. New-article audit: how many new articles in the last 15 absorbs? If zero, we're cramming; flag for review.
5. Quality audit: re-read 3 most-updated articles end-to-end; rewrite any that read like a chronological dump.
6. Tombstone sweep: if an article was superseded, move it to `archive/` with a `redirect_to:` field.

**Cross-walk to references.**
- farzaa's `/wiki absorb` loop + checkpoints + anti-cramming rules — adopted wholesale.
- karpathy's "single source touches 10–15 wiki pages" observation — our default compile budget per raw file is ~12 page touches; prompt enforces it.
- Ars Contexta's `/reduce` → `/reflect` → `/reweave` → `/verify` pipeline — we use this as the stage ordering inside each checkpoint (reduce extracts, reflect finds connections, reweave updates older pages, verify checks schema compliance).

**Deliverables.**
- `packages/jojo_compile` with CLI: `jojo_compile absorb [--range last-30-days|all|<manifest>]`, `jojo_compile rebuild-index`, `jojo_compile reorganize`.
- Orchestrator service in backend that runs the loop asynchronously and streams progress over SSE to the frontend.
- First "real" wiki run: absorb the v1.0 corpus (232 Cytiva PDFs + Nurix SOPs) and validate that the Wiki IDE tab renders a browseable knowledge base.

**Risks & mitigations.**
- *Risk: LLM hallucinates wiki content that isn't in sources.* Mitigation: every paragraph the LLM writes must cite at least one source ID; post-absorb verifier script greps for unsourced sentences and re-prompts.
- *Risk: token spend balloons.* Mitigation: budget caps per absorb job with hard kill; incremental compile over rebuilds; Haiku triage for c-priority files.
- *Risk: compile drifts from the schema.* Mitigation: `jojo_lint schema` runs in CI and on every checkpoint; ADRs are updated when drift is intentional.

**Effort.** 6–8 weeks. The absorb loop logic is ~1 week. Making it robust, well-prompted, and quality-controlled against real Nurix docs is the other 5–7 weeks.

**Exit criterion.** From a fresh `raw/` of 200+ docs, a full compile produces a wiki that passes these checks: every article has sources, `_index.md` lists every article with aliases, `_backlinks.json` matches a manual spot-check, ≥ 3 domain reviewers judge the top-10 articles as "accurate and useful".

---

### Phase 3 — JoJo Bot IDE: wiki, raw, graph tabs (weeks 10–18, in parallel with Phase 2)

**Goal.** Re-create the essential Obsidian experience — wiki browser, graph view, backlinks, live preview, Marp rendering — entirely inside the JoJo Bot app, so the user never needs an external editor.

**Tab layout** (Next.js app router, with `frontend/src/app/(tabs)/<tab>/page.tsx`).

| Tab | What it does |
| --- | --- |
| **Chat** (existing) | Ask questions, get grounded answers with citations and follow-ups |
| **Wiki** | Full IDE over `wiki/`: file tree, Markdown preview, Markdown source view, frontmatter editor, wikilink auto-complete, read-only by default, "request edit from Jojo" button |
| **Raw** | File tree over `raw/`, preview of any source, link to source URL, re-sync controls, change history |
| **Graph** | Interactive graph visualization of the wiki (see Phase 4's god-node graph); click a node to open the article |
| **Logs** | Tail `_log.md`, absorb queue status, lint queue status, cost counter, recent Claude calls with token counts |

**Tech choices.**
- Markdown rendering: `react-markdown` + `remark-gfm` + `remark-wiki-link` + `rehype-highlight` + `rehype-mathjax`. Pure client-side, no server calls per page.
- Graph view: `react-force-graph-2d` (d3-force + HTML5 canvas). Community colors from Leiden partition in `_graph.json`.
- Frontmatter editor: controlled React form generated from the Pydantic frontmatter schema in `jojo_core`.
- Marp rendering: `@marp-team/marp-core` in a Web Worker → SVG slides; left pane shows the Markdown, right pane the rendered slides, arrow-key navigation.
- matplotlib / plotly: renders inside the chat or wiki page via a sandboxed iframe; images saved to `wiki/outputs/<query-id>/assets/` so they persist.
- Graph state: `zustand` for client state, SSE streams from backend for live updates during long-running compiles/lints.

**The "request edit from Jojo" flow.**
- The Wiki tab is read-only by default.
- If the user wants to change an article, they click "Request edit", type a natural-language instruction ("This section about BTK Y551 should mention the Nurix-specific construct"), hit submit.
- Backend turns this into a targeted edit prompt, Jojo reads the article and adjacent articles, proposes a diff, the UI shows a side-by-side diff with accept/reject.
- Accepted diffs are written to disk with a commit via `git`.
- Rejected diffs are logged in `wiki/_log.md` as a negative signal that feeds future lints.

**Direct manual edits.**
- Allowed (the wiki is plain files, after all). If the user edits `wiki/targets/BTK.md` directly in a text editor, the next lint pass reconciles: Jojo re-reads the article, confirms the changes against sources, and either keeps them, amends them, or flags a contradiction for review.

**Git integration.**
- `wiki/` is a git repo. Every compile/lint/edit is a commit. Users get time-travel and blame for free. Hooks (Ars Contexta-style): `post-commit` auto-pushes to the shared OneDrive; `pre-commit` runs `jojo_lint schema` to prevent schema violations.

**Cross-walk to references.**
- karpathy's "Obsidian is the IDE, LLM is the programmer" — we rebuild the IDE inside JoJo Bot so Obsidian isn't required.
- Ars Contexta's hooks pattern — we adopt the SessionStart / PostToolUse / Stop equivalents inside the JoJo Bot runtime.
- graphify's interactive HTML graph export — we embed an always-live version of that graph inside the Graph tab.

**Deliverables.**
- Four new tabs with full functionality.
- Diff review UI for Jojo-proposed edits.
- Marp preview pane.
- Updated `build-package.bat` so the .exe bundles everything.

**Risks & mitigations.**
- *Risk: implementing a "light Obsidian" balloons scope.* Mitigation: ship an MVP per-tab (read-only wiki browser first, then graph, then editor) and feature-flag the rest.
- *Risk: the Graph tab is slow at 500+ nodes.* Mitigation: paginate by community; only render top-2 communities at full detail, rest as summary nodes.

**Effort.** 6–8 weeks, run in parallel with Phase 2 so the two phases converge together.

**Exit criterion.** A new user can open JoJo Bot, browse the entire wiki, see the graph, request a Jojo-written edit, accept it, and see the resulting diff in git — all without ever opening another application.

---

### Phase 4 — Q&A engine: index-first, escalate to RAG (weeks 16–22)

**Goal.** Make JoJo Bot dramatically better at answering hard, multi-hop Nurix questions by leaning on the compiled wiki first.

**The retrieval strategy (in order)**:

1. **Index-first** (karpathy's default). For each incoming question, the LLM first reads `wiki/_index.md` (which lists every article + aliases + 1-line summaries). It picks the 3–8 most-relevant articles, reads them in full, follows `[[wikilinks]]` and `related:` 1–2 hops deep as needed, and synthesizes an answer. This works remarkably well up to a few hundred articles — the index is typically 2k–10k tokens, which Sonnet/Opus can digest in under a second.
2. **Graph-assisted navigation** (graphify influence). For questions that touch "connectedness" — *"what's the relationship between BTK and CK1α?"* — the LLM reads `_graph.json` first, finds the shortest paths and shared communities between the two nodes, then reads only the articles on those paths. Dramatically reduces tokens vs full index reads.
3. **Raw fallback**. If the index-first + graph pass doesn't find the answer, Jojo reads `raw/_index.json` and pulls in the relevant raw files. This is the "we missed compiling something important" path. The miss is logged; a subsequent compile picks up the gap.
4. **Web search fallback** (v1.0's behavior, preserved). If it's not in `wiki/` or `raw/`, fall back to web search (Claude's built-in tool). Results are cited as `source_type: web` and optionally filed back into the wiki.
5. **Escalation to vector RAG** (deferred). We add a vector index *only* when we measure the wiki exceeds index-first's working limit (rough thresholds: >500 articles, >~1M tokens of active wiki, or p95 answer latency > 8s). The existing ChromaDB from v1.0 is repurposed here. The trigger is measured, not speculative.

**Synthesis prompt structure.**

```
<system>
  [CLAUDE.md constitution]
  [wiki_schema.md]
</system>

<user>
  Question: {user_question}

  Relevant wiki (already filtered to ~5-8 articles + backlinks):
  {articles}

  If you need more, you may request:
  - read_wiki(path): read another wiki page by path
  - read_raw(id): read a raw source by ID (use sparingly)
  - web_search(query): fallback to web (last resort)

  Answer in Markdown. Cite sources inline as [[page]] or [raw:id].
  Confidence: state where you're extrapolating vs. quoting.
  Follow-ups: propose 3 next questions that are worth asking.
  File-back: if the answer contains novel synthesis, propose a wiki
  page to file it under.
</user>
```

**Everything files back.** After every Q&A, if the answer is longer than ~200 words of novel synthesis, Jojo proposes a new file in `wiki/outputs/<date>-<slug>.md` or an update to an existing article. User approves in the UI. Accepted outputs join the wiki and influence future answers. This is the "compounding" loop.

**Cross-walk to references.**
- karpathy's "index-first works surprisingly well at moderate scale" — our MVP Q&A stops here. No RAG infrastructure until measured.
- graphify's `graph.json` + `query` / `path` / `explain` commands — we build equivalents (`POST /api/query`, `/api/path`, `/api/explain`) into the backend and expose them in the Chat tab.
- farzaa's `/wiki query` rules (never read raw entries unless necessary; don't guess; query is read-only) — adopted as prompt-level constraints.

**Deliverables.**
- `packages/jojo_qa` with REST endpoints: `/api/query`, `/api/path`, `/api/explain`, `/api/file-back`.
- Chat UI updated to show confidence, sources, follow-ups, and a "file this back" button.
- Benchmark harness: a set of 50 canonical Nurix questions with expert-approved answers; we measure accuracy, token spend, and latency at each corpus size to trigger the RAG escalation intelligently.

**Effort.** 3–4 weeks for the index-first + graph-assisted path, plus ongoing prompt tuning.

**Exit criterion.** On the 50-question benchmark: ≥ 80% answers rated "correct and well-cited" by 2+ domain reviewers, p95 latency < 8s, mean token cost per question < $0.20 at 500-article corpus size.

---

### Phase 5 — Rich outputs: markdown, slides, charts, docs (weeks 20–26)

**Goal.** Answers come back in whatever format the user asks for, rendered live in the app, and filed back into the wiki when useful.

**Output formats.**

| Format | Rendering | File-back path |
| --- | --- | --- |
| Markdown | native preview in the Chat/Wiki tab | `wiki/outputs/<date>-<slug>.md` |
| Marp slides | `@marp-team/marp-core` Web Worker → SVG carousel; arrow keys to navigate | `wiki/outputs/<date>-<slug>.marp.md` |
| Tables (comparison) | Markdown table rendered in chat; toggle to view as CSV / download as .xlsx | `wiki/outputs/<date>-<slug>.md` (table inline) |
| Diagrams (Mermaid) | native Mermaid rendering | inline in parent output |
| matplotlib charts | backend runs the LLM-generated Python in a sandboxed subprocess, returns PNG; image written under `wiki/outputs/<date>-<slug>/assets/` | article references the local path |
| Plotly interactive | same as matplotlib, returned as HTML fragment | same |
| Word (`.docx`) | via the `docx` skill; protocol-like outputs | stored in `wiki/outputs/<slug>/` and linked from a wiki article |
| PowerPoint (`.pptx`) | via the `pptx` skill | same |
| PDF | via the `pdf` skill | same |

**Sandboxing for matplotlib.** We run LLM-generated plotting code in a subprocess with:
- A resource limit (CPU 30s, RAM 512MB).
- A bind-mounted `/tmp/jojo_plot/` working dir that's erased per run.
- No network. No file access outside the working dir.
- Allowlist of imports (`numpy`, `pandas`, `matplotlib`, `seaborn`, `plotly`). Anything else fails.

**File-back UX.**
- Every output renders with a "File this" button.
- User confirms destination (default proposed by Jojo), types optional extra tags, hits save.
- File lands in `wiki/outputs/`, gets indexed in the next compile checkpoint, and starts contributing to future Q&A.

**Cross-walk to references.**
- karpathy gist explicitly calls out Marp + matplotlib outputs and the "file outputs back" principle — directly implemented.
- Ars Contexta's schema-driven notes — we reuse the template system so every output has consistent frontmatter.
- Existing JoJo Bot `docx`/`pptx`/`pdf`/`xlsx` skills — all leveraged rather than re-implemented.

**Deliverables.**
- `packages/jojo_output` with renderers and the sandboxed Python executor.
- Chat tab: format selector, file-back confirmation modal.
- Wiki tab: outputs directory renders differently (shows render preview + source + "re-render" button).

**Effort.** 4–6 weeks, mostly in frontend polish and matplotlib sandboxing.

**Exit criterion.** A user can ask "make me slides comparing NX-1607 and NX-5948", see them render, click "file this", and find the .marp.md in `wiki/outputs/` that's now citable by future questions.

---

### Phase 6 — Linting & health checks (weeks 24–30)

**Goal.** Periodically sweep the wiki for contradictions, missing data, orphans, stale claims, and new-article candidates. Keep the wiki compounding, not decaying.

**Lint passes** (adapted from karpathy's "Lint" operation and farzaa's `/wiki cleanup` + `/wiki breakdown`).

| Check | Implementation | Action when triggered |
| --- | --- | --- |
| **Schema validation** | Pydantic schema over frontmatter; `jojo_lint schema` | File written to `wiki/_schema_violations.md`; CI gate |
| **Orphans** | Articles with 0 inbound backlinks | Flag in `_log.md`; suggest merges in next reorganize |
| **Stubs** | Articles < 15 lines older than 30 days | Spawn a `/wiki breakdown` sub-pass to fill in |
| **Contradictions** | Opus pass over pairs of articles that share a subject; look for incompatible claims | Open a `decisions/` stub with both positions; require human arbitration |
| **Stale claims** | Articles whose sources are all > 18 months old | Suggest a web-search + wiki-update |
| **Missing data** | Frontmatter fields marked `unknown:` | Spawn a web-search or a new ingest job to fill |
| **Broken wikilinks** | `[[…]]` pointing at non-existent files | Fix automatically (closest-alias match) or convert to a stub |
| **Missing article candidates** | Concrete-noun scan across articles (farzaa's concrete noun test) | Rank by reference count; propose top-N for creation |
| **Bloated articles** | > 150 lines | Propose a split along the most natural thematic seam |
| **Quote budget** | > 2 direct quotes in an article | Re-write to paraphrase with citations |
| **Cost anomalies** | Unusually-expensive compile/lint runs | Slack alert to Mateo |

**Cadence.**
- Nightly (scheduled): schema, orphans, stubs, broken wikilinks, bloat, quote budget.
- Weekly (Opus): contradictions, stale claims, missing data, new-article candidates.
- On-demand: user can trigger any lint from the Logs tab.

**Parallel subagents** (Ars Contexta + farzaa). Each lint check runs as a batch of 5 parallel subagents processing a partition of the wiki, each with a fresh context window. Results merge in the orchestrator.

**Human-in-the-loop for high-risk fixes.**
- Any *deletion* requires human approval.
- Any change to a `decisions/` article requires approval.
- Any contradiction resolution requires approval.
- Everything else (wikilink fixes, formatting, source re-citation) is auto-applied.

**Cross-walk to references.**
- karpathy's "Lint" section — direct 1:1.
- farzaa's `/wiki cleanup` (Phase 1 context, Phase 2 per-article subagents, Phase 3 integration) — structure adopted.
- Ars Contexta's `/verify`, `/reweave`, `/rethink` — we map our lints onto these conceptual phases.

**Deliverables.**
- `packages/jojo_lint` with pluggable check registry.
- Scheduled task integration (reuse `mcp__scheduled-tasks__*` or Windows Task Scheduler).
- Logs tab surfaces lint history, failures, and pending approvals.

**Effort.** 4–6 weeks.

**Exit criterion.** Nightly lints run unattended for 2 weeks with < 5% false-positive rate on a sample reviewed by Mateo. Weekly Opus pass produces actionable contradiction/gap reports that Mateo acts on.

---

### Phase 7 — Shared server mode (weeks 28–34, optional)

**Goal.** Promote the single-user local model to a shared Nurix server so the entire company queries one authoritative wiki, without sacrificing the simple .exe experience for individual users.

**Architecture change.**
- A new backend service (`jojo_server`) runs on a Nurix-internal VM. It holds the authoritative `raw/` + `wiki/`, runs the ingest/compile/lint schedules, and exposes the same REST API as the local backend.
- The .exe becomes a thin client: same Next.js frontend, but `API_BASE_URL` points at the server. Offline mode falls back to the local copy.
- Auth: Azure AD / Nurix SSO. Every API call carries a user token; ingest scopes are checked per-user (no one sees SharePoint they don't already have access to).
- Wiki is served read-mostly; compile/lint run centrally.

**New concerns introduced.**
- Access control per article (inherited from source access).
- Concurrent edit conflicts.
- Multi-tenant model routing (per-org API key if we outgrow the single-MSA setup).
- DR/backup of the shared `raw/` + `wiki/`.

**Exit criterion.** Three Nurix teams in active daily use, server uptime ≥ 99%, p95 query latency < 4s, access-control audit passes.

---

### Phase 8 (exploratory) — Synthetic data + fine-tuning (weeks 34+, research)

**Goal.** Bake Nurix knowledge into model weights (instead of or in addition to context windows) so JoJo Bot can answer instantly, cheaper, and even when the wiki isn't in-context.

**Approach (high-level — *this is research, not a committed plan*).**

1. **Synthetic dataset generation.** Use the compiled wiki as a source of ground truth. For every article, generate:
   - 5–10 Q&A pairs grounded in that article's content (Sonnet + verifier).
   - 2–3 "synthesize" tasks that require combining the article with its backlinks.
   - A "chain-of-thought" explanation for each answer, with inline `[[wikilink]]` citations.
   - Adversarial / counterfactual variants (contradictions, missing info).
2. **Filter & verify.** Run a separate verifier model on every generated pair; reject anything that doesn't round-trip against its source article. This is how we keep the dataset honest.
3. **Fine-tune options** (in increasing cost / capability):
   - **Prompt caching + system prompt injection** of the wiki `_index.md` and top-N hub articles. Cheapest, no training.
   - **Retrieval-augmented fine-tuning** of a small open model (Llama-3.1-8B, Mistral) on the synthetic dataset so a local model can answer "easy" questions without calling Claude at all. Useful for latency and cost at scale.
   - **Claude custom model** (if Anthropic offers a suitable program by the time we're ready). Largest capability jump but highest cost.
4. **Eval suite.** Use the 50-question Nurix benchmark from Phase 4, plus a held-out 500-question expansion, to measure the fine-tuned vs. base model.

**Risks.**
- Data contamination: any PII/PHI/trade-secret in the wiki becomes training data. Must scrub before training; legal review mandatory.
- Model drift: Nurix knowledge changes monthly; the fine-tuned model is stale the moment it's trained. Mitigation: hybrid (small fine-tuned model for classification + routing; wiki-in-context for authoritative answers).
- ROI: at current Claude API costs, fine-tuning may not pay off until query volume is very high. Do the math before committing.

**Status.** Research-only until Phases 1–6 are stable and corpus is large enough to justify.

---

## 6. Cross-cutting concerns

### 6.1 Security & compliance

- **Data classification.** Every raw file gets a classification tag at ingest (`public | internal | confidential | regulated`). Regulated data (GxP, CTA, clinical, HIPAA) never leaves the Nurix network — for those sources, compile and Q&A run against local wiki only; Claude calls are made only with redacted content. Redaction rules live in `schema/ingest_rules.md`.
- **PII/PHI redaction.** Regex pass at ingest + LLM classification in compile, with audit log.
- **MSA coverage.** Confirm the Nurix/Anthropic MSA covers the data classes we plan to send. Flag any gap to Legal in Phase 0.
- **Secrets.** No hard-coded secrets. `%APPDATA%\JojoBot\config.json` (DPAPI-encrypted) for keys.
- **Audit log.** Every LLM call, every wiki write, every source fetch is logged with user, timestamp, token count, and cost. Exportable for compliance.
- **Access control.** In Phase 1–6 (local mode): the user's wiki only contains what their user account could access. In Phase 7 (server mode): per-article ACLs inherited from source system permissions.

### 6.2 Governance & human-in-the-loop

- The wiki is LLM-owned but human-reviewed. Every new article created during absorb is flagged `review_pending: true` in frontmatter; scientists (via the Wiki tab) can mark it `approved: true` or request a rewrite. Approved articles no longer surface in review queues but remain subject to lints.
- Contradictions always require human arbitration.
- A simple `review` queue in the Logs tab shows pending articles, sorted by hub-centrality (high-traffic articles get reviewed first).
- An owner is assigned per directory (e.g. `targets/` owner = Discovery lead). The owner gets a weekly digest of changes.

### 6.3 Observability, cost, and telemetry

- Per-run token counts streamed into `wiki/_log.md` and a SQLite metrics DB (`jojobot.db`, reused from v1.0).
- Cost dashboard in the Logs tab: today / week / month spend, broken down by operation (ingest, compile, lint, Q&A).
- Alerts: Slack / email when spend exceeds a per-user or per-day cap.
- Token reduction benchmark (graphify style): measure "tokens to answer a canonical question, wiki-path vs raw-path", publish quarterly.

### 6.4 Testing strategy

- `jojo_core`: unit tests for types, schema validation, Claude client retries.
- `jojo_ingest`: golden-file tests for each connector (fixture HTML/docx → expected Markdown).
- `jojo_compile`: snapshot tests on the absorb loop (small raw corpus → expected wiki pages; manual diff review).
- `jojo_qa`: 50-question benchmark runs nightly in CI; regressions fail the build.
- `jojo_lint`: property-based tests (e.g. "after lint, every wikilink resolves").
- `jojo_output`: rendering tests (e.g. `.marp.md` renders to a known number of slides).
- End-to-end smoke test: from a fixture `raw/`, run ingest → compile → lint → Q&A → output and assert the output matches a golden file.

### 6.5 Documentation & onboarding

- `docs/V2_PLAN.md` — this file.
- `docs/ADR/` — architectural decisions, one file per call.
- `docs/runbooks/` — operational procedures (how to re-sync SharePoint, how to run a manual compile, how to resolve a contradiction).
- `docs/ONBOARDING.md` — 15-minute "how to run Jojo Bot v2.0 for the first time" for a new scientist.

---

## 7. Timeline & milestones

**Assumption:** 1 core developer (Mateo) + occasional domain reviewers. Adjust ×0.7 if you add a second developer.

| Phase | Weeks | Gate |
| --- | --- | --- |
| 0 — Foundation & prep | 0–2 | Schema + repo scaffolding + IT ticket filed |
| 1 — Ingest (SharePoint + Drive + NurixNet) | 2–8 | 100+ docs in raw/, daily sync green, Raw tab live |
| 2 — Compile (absorb loop) | 8–16 | v1.0 corpus compiled into wiki, checkpoint audit passes |
| 3 — IDE tabs (Wiki + Raw + Graph + Logs) | 10–18 (parallel) | All 4 tabs functional, edit-via-Jojo diff flow working |
| 4 — Q&A (index-first + graph-assisted) | 16–22 | 50-question benchmark ≥ 80% correct |
| 5 — Outputs (Marp + plots + docx/pptx) | 20–26 | File-back loop working end-to-end |
| 6 — Linting (nightly + weekly Opus) | 24–30 | 2 weeks of unattended lints, < 5% FP rate |
| 7 — Shared server (optional) | 28–34 | 3 teams in daily use, 99% uptime |
| 8 — Synthetic data + fine-tuning (research) | 34+ | Go/no-go based on eval numbers |

**Critical path:** 0 → 1 → 2 → 4. Phase 3 and 5 run in parallel with 2 and 4. Phase 6 can start as soon as 2 is producing a real wiki.

**MVP ship target:** end of Phase 4 (~22 weeks / ~5 months from start). That's the v2.0 release candidate: ingest + compile + IDE + Q&A. Phases 5 and 6 can ship as point releases (v2.1, v2.2).

---

## 8. Budget

Assumptions: Claude Sonnet 4.6 @ ~$3/M in, $15/M out; Opus @ ~$15/M in, $75/M out; Haiku @ ~$0.8/M in, $4/M out (substitute current rates at implementation time).

| Activity | Estimate |
| --- | --- |
| One-time compile of ~2000 raw files → wiki | ~$150–$400 |
| Daily incremental compile (~20 changed files/day) | ~$5–$15/day |
| Weekly Opus lint pass over 500-article wiki | ~$20–$50/pass |
| Q&A per question (index-first, 500-article wiki) | ~$0.05–$0.20 |
| Per-user monthly baseline (20 Q/day + daily ingest) | ~$50–$150/month |
| Team of 20 users monthly | ~$1000–$3000/month |

Exact numbers depend heavily on corpus size and query complexity. Phase 0 deliverable includes a spreadsheet with three scenarios so budgeting can track reality. Build cost controls and per-user caps from day one.

---

## 9. Risks & mitigations (consolidated)

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| IT blocks Graph API access | Medium | High | Ship the OneDrive-files-on-disk fallback first; Graph API is an upgrade, not a blocker. |
| Nurix/Anthropic MSA doesn't cover regulated data | Medium | High | Phase 1 scoped to non-regulated sources; Legal review during Phase 0. |
| LLM hallucinates wiki content | High without controls | High | Mandatory inline source citations + verifier pass + nightly lint. |
| Token spend runs away | Medium | Medium | Hard budget caps per job; Haiku triage; incremental over full compiles; cost dashboard with alerts. |
| Users edit the wiki and break schema | Medium | Medium | pre-commit hook runs `jojo_lint schema`; lint auto-fix or flag. |
| Scope creep (the "light Obsidian" problem) | High | Medium | Phase 3 has feature flags; every tab ships MVP first, polish second. |
| Wiki quality varies by domain | Medium | High | Per-directory reviewers; review queue; weekly Opus lint catches staleness. |
| NurixNet HTML structure changes | Medium | Low | Selectors are quarantined in one module with tests; fallback to raw-HTML mode. |
| Compile loop drifts from schema over time | Medium | Medium | Lint-in-CI; ADRs for every intentional drift. |
| Obsidian replacement is harder than expected | Medium | Medium | Keep "open `wiki/` in Obsidian" as a documented escape hatch; the wiki is just files. |
| Single developer leaves / vacation | Medium | High | Documentation discipline (ADRs + runbooks); schema + code + tests form the full design. |

---

## 10. Success metrics (what "v2.0 worked" looks like)

- **Coverage.** 10+ Nurix programs have compiled wiki articles; ≥ 1000 wiki articles total.
- **Freshness.** 95%+ of articles are reconciled to sources modified in the last 30 days.
- **Correctness.** 50-question benchmark ≥ 80% "correct and well-cited".
- **Adoption.** ≥ 20 Nurix scientists use JoJo Bot v2.0 at least weekly by month 6 post-launch.
- **Compounding.** ≥ 30% of answered questions result in a filed-back wiki page; those pages are subsequently cited in future answers (measurable via backlinks).
- **Cost.** Mean cost per answered question ≤ $0.20; monthly infra + API spend ≤ $3k for a 20-user team at steady state.
- **Token efficiency.** Published quarterly token-reduction benchmark (graphify style); target ≥ 10× reduction on 500-article corpus versus raw-file baseline.

---

## 11. Open questions / decisions deferred

These are things we intentionally do *not* lock in Phase 0; they will resolve during Phase 1–2 with real data.

1. **Graph layer: do we use graphify's Leiden community detection directly, or roll a simpler heuristic for the `_graph.json`?** Probably use graphify-the-tool as a CLI dependency first, and replace with custom code only if licensing or accuracy becomes a concern.
2. **Do we adopt qmd for search inside the wiki as the corpus grows?** Likely yes (it's cheap, local, MCP-ready), but only when we hit the index-first ceiling.
3. **Multi-user editing conflicts (Phase 7).** CRDT? Git-merge-driver? Server-side lock? Defer until Phase 7 planning.
4. **"Nurix in model weights" approach in Phase 8 — open-source fine-tune vs Anthropic custom model vs prompt-cache only.** Wait for corpus + query-volume data.
5. **Do we build a connector for Benchling, Asana, Teams, Outlook? If yes, in what order?** Defer until end of Phase 2; the absorb loop's quality on core sources tells us if additional sources are worth the effort.
6. **Synthetic data & fine-tuning legal review.** Will need a fresh pass with Legal because training data has different rules than Q&A data under most MSAs.

---

## 12. Appendix A — Cross-walk to external references

How each reference maps into this plan, so we're not "overly relying" on any one — we borrow selectively.

**`karpathy/llm-wiki` (gist).**
- Core architectural pattern: raw / wiki / schema three-layer. → Section 3.
- Operations: Ingest / Query / Lint. → Phases 1, 4, 6.
- `_index.md` + `_log.md` special files. → Section 3.2 + Phase 2 deliverables.
- "LLM writes, user curates" principle. → Principle #2.
- "Outputs file back" loop. → Phase 4, Phase 5.
- Note on avoiding RAG until necessary. → Principle #9 + Phase 4 escalation rule.

**`farzaa/personal-wiki-skill` (gist).**
- Command surface: `ingest | absorb | query | cleanup | breakdown | status | rebuild-index | reorganize`. → Phase 2 + 6 CLIs.
- The absorption loop with checkpoints every 15 entries. → Phase 2.
- Anti-cramming / anti-thinning rules. → Design principles + schema.
- Writing standards (Wikipedia-flat, no peacock words, quote budget, length targets). → `schema/wiki_schema.md`.
- Parallel subagents for cleanup and breakdown. → Phase 6.
- Directory taxonomy philosophy ("directories emerge from the data"). → `schema/taxonomy.yaml`.

**`agenticnotetaking/arscontexta` (GitHub).**
- Three-space architecture (self / notes / ops). → Adapted as schema/ / wiki/ / raw/_changes + runtime queues.
- 6 Rs pipeline (Record → Reduce → Reflect → Reweave → Verify → Rethink). → Mapped onto the compile checkpoint stages.
- Fresh-context-per-phase via subagents (`/ralph`). → Phase 2 orchestrator architecture.
- Hooks (SessionStart / PostToolUse / Stop). → Git hooks + backend worker hooks.
- Research-backed kernel primitives as a design-rigor discipline. → ADRs.
- Explicit "derivation, not templating" philosophy. → Our `schema/CLAUDE.md` is the derivation engine.

**`safishamsi/graphify` (GitHub).**
- `graph.json` as a persistent, token-efficient navigation layer over raw files. → `wiki/_graph.json`.
- EXTRACTED vs INFERRED edge tagging with confidence scores. → Mandatory in wiki frontmatter and graph edges.
- God nodes + community detection (Leiden). → Graph tab features.
- Multimodal (code / docs / PDFs / images / video). → Phase 1 ingest multimodal support; Whisper transcription in stretch.
- Token reduction benchmark as a KPI. → Section 10.
- MCP server exposure of the graph. → Phase 4 stretch; wiki + graph as an MCP server for other Nurix tools.
- Always-on hook that points agents at the graph first. → Analogous prompt discipline in Q&A.

**`tig-foundation/tig-monorepo` (GitHub).**
- The domain is unrelated (algorithmic proof-of-work) but the monorepo structure is useful. → Section 3.2 `packages/` split with small, swappable crates (ingest, compile, qa, output, lint, graph, core) mirrors the `tig-algorithms` / `tig-runtime` / `tig-verifier` / `tig-benchmarker` split.
- Benchmarker discipline (measurable performance, swappable runtime). → Our 50-question benchmark harness in Phase 4 and the token-reduction benchmark in Section 10.
- Clean CLI-per-crate ergonomics. → Every package has `python -m jojo_* <cmd>`.

---

## 13. Appendix B — Glossary

- **Raw.** Immutable snapshot of a source document pulled into `raw/<source>/<id>/<version>.md`. Never edited after creation.
- **Wiki.** LLM-authored Markdown knowledge base in `wiki/`. Compiled from `raw/`. The "compounding artifact".
- **Schema.** The constitution: `CLAUDE.md`, `wiki_schema.md`, `taxonomy.yaml`. What the LLM reads first on every operation.
- **Absorb.** The act of reading a raw entry and updating/creating wiki articles to reflect it.
- **Lint.** Periodic integrity checks over the wiki (contradictions, orphans, staleness, schema).
- **Index-first.** Retrieval strategy where the LLM reads `wiki/_index.md` first and picks 3–8 articles to read in full, rather than calling a vector DB.
- **God node.** A highly-connected wiki article that many other articles link to — usually a target, program, or key concept.
- **EXTRACTED / INFERRED.** Source-attribution tags on every claim and edge. EXTRACTED means "directly from a source"; INFERRED means "reasoned inference" with a confidence score.
- **File-back.** The act of saving a Q&A output into the wiki so future queries can cite it.
- **Checkpoint.** Every 15 absorbs (or per user config), the compile loop rebuilds indices and runs a quality audit.
- **Fresh-context-per-phase.** Each pipeline phase runs in a subagent with an empty context window; prevents context-length degradation during long runs.

---

*End of plan. Next step: review, leave comments in-line (this is a plain Markdown file — edit it or open a PR), and once ratified, archive this copy as `docs/ADR/0000-v2-roadmap.md` and switch to a living `docs/V2_STATUS.md` that tracks progress against the phases above.*
