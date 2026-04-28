# Innovera Tuning Plan

Working branch: `claude/plan-innovera-tuning-R8aiu`

## 1. Goal

Tune the Competely-clone pipeline for Innovera's actual competitor landscape. Two pillars:

- **Pillar A — Deeper competitor discovery.** A new stage that produces a ranked list of 10–30 candidates across four framings (Direct, Problem-Sharer, Category-Sharer, Adjacency), seeded with Innovera-specific context (AI-native decision platforms, consulting firms adopting blended AI+human, Big 4 / trading houses as adjacencies).
- **Pillar B — Research stack upgrade.** Retire the Tongyi-DeepResearch backend (non-Chinese-provider constraint + fine-tuned lock-in). Move the `RESEARCH_MODEL` to `anthropic/claude-sonnet-4.6`. Add Exa for semantic discovery and Firecrawl for deep page extraction. Keep Serper and Jina Reader as fallbacks during rollout.

A third supporting pillar falls out of Zamir's transcript: a new Innovera-tuned deep-dive variable set that captures what he actually asked for — business model, GTM motion, client engagement, size/funding, and "what can Innovera learn from a smaller/faster offer."

---

## 2. What Zamir asked for (source of truth)

From the transcript:

1. Find AI-native partial competitors eating part of Innovera's pie (market research, competitive analysis, strategy). Understand their business model, how they operate and sell, how they engage clients, and their size (revenue, clients, funding raised).
2. Track consulting firms that are moving to a blended AI + human model — are they catching up, are we ahead, by how much?
3. Use the findings not just defensively but to refine Innovera's own business model — spot smaller, faster-to-market offers worth learning from.

Every framing prompt and every new deep-dive variable below must trace back to one of those three.

---

## 3. What Innovera is (for prompt seeding)

AI-native decision intelligence platform. Core premise: AI and fast-moving markets expand options faster than leadership can judge them. Builds "digital twins" of initiatives via specialized agents (opportunity validation, market research, competitive analysis, product/tech, GTM, financials, talent, legal, IP) — AI analysis + expert-in-the-loop validation. Sells into corporate innovators, strategy teams, and executives. Substitutes for large consulting-team engagements, delivered faster.

This text will live in `config/innovera_profile.py` and be injected into every framing prompt.

---

## 4. Pillar A — Competitor Discovery

### 4.1 Framings (generic, with Innovera defaults)

| Framing | Definition | Innovera seed examples |
|---|---|---|
| **Direct** | Same problem, same solution | Other AI-native decision/strategy platforms, other "digital twin of initiative" products |
| **Problem-Sharer** | Same problem (strategic decisions under uncertainty), different solution | Consulting firms (McKinsey QuantumBlack, BCG X, Bain Vector, Accenture Song), internal strategy tools, expert networks (GLG, Third Bridge) |
| **Category-Sharer** | Different problem, same solution shape (multi-agent AI over enterprise knowledge) | AI research agents (Glean, Hebbia, Rogo), AI analyst platforms for other verticals, AI market-research tools |
| **Adjacency** | Has capital / tech / distribution to pivot in | Big 4 investing in internal AI (Deloitte GenAI practice), foundation-model labs moving into agents, CRMs/ERPs adding decision layers (Salesforce, Palantir), sovereign / trading houses with data + capital |

All four framings remain generic in code — Innovera seeds are just the default value of a `framing_seeds` dict, overridable per run.

### 4.2 Architecture

New module: `agents/competitor_discovery_agent.py`

- **One async function per framing** — `discover_direct()`, `discover_problem_sharers()`, `discover_category_sharers()`, `discover_adjacency()`. Each:
  1. Takes the target-company profile + framing-specific seed prompt.
  2. Calls Claude Sonnet 4.6 to expand into 3–5 neural-search queries tailored to that framing.
  3. Fans out to Exa (`neural` mode) for candidate URLs.
  4. Firecrawl extracts structured content from the top hits.
  5. Claude Sonnet 4.6 extracts candidate companies + one-line rationale per framing.
- **Run all four in parallel**, then merge.
- **Dedupe + rank**: normalize company names (lowercase, strip Inc./Ltd., resolve domain), group duplicates across framings (a company may legitimately appear in more than one — keep all framings it matched), score by `(mention_count × framing_weight × evidence_quality)`, return top N (default 20, user-configurable 10–30).

### 4.3 Data model

```python
# agents/schemas.py (new dataclasses, pydantic where the frontend needs them)

class CompetitorCandidate(BaseModel):
    name: str
    canonical_domain: str | None
    framings: list[Literal["direct", "problem_sharer", "category_sharer", "adjacency"]]
    rationales: dict[str, str]  # framing -> one-line why
    evidence_urls: list[str]
    confidence: float  # 0.0–1.0
    discovered_at: datetime

class DiscoveryRun(BaseModel):
    id: str
    target_profile: CompanyProfile
    framing_seeds: dict[str, str]
    candidates: list[CompetitorCandidate]
    status: Literal["running", "complete", "failed"]
    created_at: datetime
```

Persist as JSON under `data/discovery/<run_id>.json` (matches the pattern `data/cache/` already uses).

### 4.4 API surface

- `POST /api/discovery` — body: `{target_profile, framing_seeds?, max_candidates?}` → `{discovery_run_id}`. Kicks off async task (follow existing `api/routes/runs.py:60+` pattern).
- `GET /api/discovery/{id}` — poll for status + results.
- `POST /api/discovery/{id}/promote` — body: `{selected_names: [...]}` → creates a standard Run with those as the X axis, handing off to `/api/runs` machinery unchanged.

### 4.5 UX

New route: `frontend/app/discovery/new/page.tsx` and `frontend/app/discovery/[id]/page.tsx`.

Flow:
1. User fills target-company profile (prefilled for Innovera from `config/innovera_profile.py`).
2. Optional: edit the four framing seeds.
3. Submits → discovery runs (~30–90s; stream status per framing).
4. Results screen: grouped-by-framing table with checkboxes. Companies that match multiple framings show all tags. User prunes to 10–30.
5. "Run analysis" button → promotes selection to `/runs/new` with companies pre-populated and parameter choice (AVIS / Innovera / generated) as next step.

The existing `/runs/new` flow is **not removed** — discovery is a new front door, not a replacement.

### 4.6 Files to add/modify

- **Add**: `agents/competitor_discovery_agent.py`, `agents/schemas.py` (or extend existing), `config/innovera_profile.py`, `config/framings.py`, `api/routes/discovery.py`
- **Modify**: `api/main.py` (register new router), `frontend/app/discovery/new/page.tsx` (new), `frontend/app/discovery/[id]/page.tsx` (new), `frontend/app/runs/new/page.tsx` (accept pre-populated companies via query param)

---

## 5. Pillar B — Research stack upgrade

### 5.1 Model swap: Tongyi → Claude Sonnet 4.6

Small, contained change — the routing already exists.

- `config/settings.py:41` — change default: `RESEARCH_MODEL = os.getenv("RESEARCH_MODEL", "anthropic/claude-sonnet-4.6")`.
- `agents/llm_client.py:119` — remove the Tongyi model from the `atlascloud` provider's `models` list (or empty it, so nothing routes there by default). Keep the Atlas Cloud provider wired so a user can opt back in via env var if needed.
- `agents/llm_client.py:355–362` — remove the Tongyi-specific "reasoning field fallback" path. It's dead code for Sonnet and adds risk of masking real empty responses.
- `.env.example` — update default.
- `config/settings.py:163–187` — `validate_config` no longer requires `ATLAS_CLOUD_API` when `RESEARCH_MODEL` is an OpenRouter model.

Deprecate but don't delete Atlas Cloud wiring for one release so rollback is a one-line env change.

### 5.2 Exa for semantic search

New client: `agents/exa_client.py` mirroring `agents/search_client.py`'s interface so it's drop-in.

- Env: `EXA_API_KEY`.
- Used initially **only in discovery** (Pillar A) where neural search is most valuable — the existing research-agent loop keeps Serper.
- Add a `SEARCH_PROVIDER` env var (`serper` | `exa` | `hybrid`). In `hybrid` mode the research agent runs both and deduplicates URLs — worth trying on the Innovera benchmark once Pillar A lands.

### 5.3 Firecrawl for extraction

New client: `agents/firecrawl_client.py` mirroring `agents/page_reader.py`'s interface.

- Env: `FIRECRAWL_API_KEY`.
- Use for discovery-stage extraction (richer structured output — Firecrawl returns markdown + metadata + links).
- Gate with `PAGE_READER = "jina" | "firecrawl"` env; default stays `jina` for the research loop until we benchmark.

### 5.4 Settings additions (`config/settings.py`)

```python
EXA_API_KEY = os.getenv("EXA_API_KEY", "")
EXA_BASE_URL = "https://api.exa.ai"
SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "serper")  # serper|exa|hybrid
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")
FIRECRAWL_BASE_URL = "https://api.firecrawl.dev/v1"
PAGE_READER = os.getenv("PAGE_READER", "jina")  # jina|firecrawl
DISCOVERY_MODEL = os.getenv("DISCOVERY_MODEL", "anthropic/claude-sonnet-4.6")
DISCOVERY_MAX_CANDIDATES = int(os.getenv("DISCOVERY_MAX_CANDIDATES", "20"))
```

---

## 6. Pillar C — Innovera-tuned deep-dive variables

New file `config/innovera_variables.py`, parallel to `config/avis_variables.py`. Reuses the `VariableDefinition` schema so no run-engine changes.

Dimensions (every one traces to Zamir's asks):

| ID | Name | What it captures | Maps to Zamir |
|---|---|---|---|
| `inv_offer_shape` | Offer Shape & Scope | One-line offer, problems covered, engagement length, artifact type (report / platform / subscription) | "smaller offer penetrating market faster" |
| `inv_gtm_motion` | GTM Motion | Sales model, ICP, deal size, channels, time-to-first-customer | Zamir: "how they sell" |
| `inv_client_engagement` | Client Engagement Model | Onboarding, expert-in-the-loop vs pure-AI, cadence of deliverables, success measurement | Zamir: "how they engage with their clients" |
| `inv_ai_human_blend` | AI / Human Blend | % AI automation vs human expert, where humans are in the loop, defensibility of the human layer | Zamir: "blended model between people and AI" |
| `inv_size_signals` | Size Signals | Revenue (or estimate), client count, notable logos, headcount, funding raised, last round | Zamir: "how big they are … revenue or client base … how much money they raised" |
| `inv_speed_to_market` | Speed-to-Market Playbook | Time from founding to first paying customer, to Series A, to material revenue | Zamir: "penetrating the market faster" |
| `inv_takeaway_for_innovera` | Takeaway for Innovera | Synthesis cell: what Innovera should copy, avoid, or be worried about from this competitor | Zamir: "learn from them … align our own business model" |

The last row is the most important and the most novel: it's a reasoning synthesis that takes the other six cells' outputs plus Innovera's profile and writes a concrete action-oriented paragraph. Implement it as a post-pass after the other six cells resolve for a given competitor (similar pattern to `v2_pipeline.py`).

Selectable in the run-creation UI alongside AVIS: radio button "Innovera lens" → loads this variable set.

---

## 7. Execution order

Five milestones; each is independently shippable and reviewable.

1. **M1 — Model swap (½ day).** Pillar B §5.1 only. Tongyi → Claude Sonnet 4.6. Run one existing analysis end-to-end to confirm no regression.
2. **M2 — Innovera variable set (1 day).** Pillar C. Ship `config/innovera_variables.py` + UI toggle. Run against one existing set of competitors to sanity-check prompts.
3. **M3 — Exa + Firecrawl clients (1 day).** Build the two clients in isolation with unit-level smoke tests. No integration yet.
4. **M4 — Discovery agent (2–3 days).** Pillar A §4.1–4.4. Backend only. Validate via API calls with curl before touching frontend.
5. **M5 — Discovery UI (1–2 days).** Pillar A §4.5. Frontend route, handoff into `/runs/new`.

Stop-and-review gate after M1, M2, and M4 — they are the points where I'd most want your eyes before continuing.

---

## 8. Open questions (flag, don't resolve yet)

- **Exa pricing at discovery scale.** 4 framings × ~5 queries × ~10 results = ~200 URLs per discovery run before dedup. Need to confirm this fits your Exa plan and set a per-run cap.
- **Firecrawl vs Jina for the research loop.** Deferred — M3 adds Firecrawl only for discovery. Whether to switch the whole research loop is a separate decision once we can benchmark.
- **Adjacency framing quality.** This is the hardest framing to get right — "who *could* enter" is genuinely a reasoning task, not a retrieval task. If M4 shows the adjacency output is weak, the fix is probably a two-pass Claude prompt (generate capability hypotheses → instantiate companies) rather than more search.
- **Persisting discovery runs in a DB.** For now JSON files under `data/discovery/`, matching the existing cache pattern. If Innovera usage stays steady we should migrate to whatever store `/api/runs` uses — worth confirming what that is before M4.
- **Who owns the Innovera profile text.** `config/innovera_profile.py` will hard-code the description from §3. If Innovera's positioning changes, Zamir (or you) should edit that file — flag in the PR.

---

## 9. Non-goals for this round

- Replacing AVIS — it stays. Innovera-lens is additive.
- Rewriting the synthesis / verification loop in `agents/research_agent.py` — the model swap is the only change that touches it.
- Benchmark harness comparing Claude vs GPT-5 vs Gemini Deep Research — out of scope; revisit only if M1 quality is disappointing.
- Generalizing the framing seeds to arbitrary industries — defaults ship Innovera-tuned; refactor once a second customer needs it.
