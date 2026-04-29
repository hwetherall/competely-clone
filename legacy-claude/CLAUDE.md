# CLAUDE.md — Commercial Deep Dive Feature

> Build context for the Innovera Search "Commercial Deep Dive" feature, which expands the Innovera DeepDive Market Report from 7 to 17 questions and re-architects the web research pipeline to use Firecrawl, Exa, and Serper+Jina according to their epistemic strengths rather than as substitutes.

---

## 1. Why this feature exists

V1 of the Innovera DeepDive Market Report answers 7 high-level questions about a competitor's positioning, traction, and market presence. A senior leader has requested 10 additional questions covering pricing, packaging, contracts, and revenue model — operational sales-intel that V1 does not surface today.

Rather than naïvely appending 10 more research cells, this feature does two things at once:

1. **Adds a Commercial Deep Dive layer** — three new parameters (Packaging, Pricing Mechanics, Contract Structure) plus an extension to the existing `business_models` parameter, jointly covering all 10 new questions.
2. **Fixes the underutilized Firecrawl integration** — Firecrawl is currently used only for competitor discovery (Phase 0) and then ignored. This feature introduces a dedicated structured-extract phase that brings Firecrawl back into the workflow where it belongs.

These two problems share the same solution: most of the new questions are answered by *structured data on the competitor's own pricing/terms pages* — which is exactly what Firecrawl Extract is built for, and exactly what Serper+Jina struggles with.

---

## 2. Scope

**In scope:**
- 3 new `VariableDefinition` blocks: `packaging`, `pricing_mechanics`, `contract_structure`
- 1 extension to the existing `business_models` variable to cover Q10 (primary revenue driver)
- A new pre-research phase: **Competitor Profiling** (typology classification + URL inventory)
- A new pre-research phase: **Structured Extract** (Firecrawl `/extract` against pricing & terms pages, conditional on typology)
- Routing rules so per-cell research loops use the right tool for the question
- Explicit handling for opaque-pricing and consulting-firm competitors

**Out of scope (for this iteration):**
- Changes to Phase 0 competitor discovery (Firecrawl Search stays as-is)
- Wider competitor analysis use cases — this build is **Innovera Search only**
- Replacing the existing Exa-based gather agent — Exa stays, but its role is reframed
- New UI surfaces — these parameters render in the existing parameter modal

---

## 3. Architectural overview

The pipeline grows from 4 phases to 6. The new phases (1 and 2) run *between* Discovery and the existing per-cell research loop.

```
Phase 0 — Discovery              [unchanged]   Firecrawl Search → ~20 competitors
Phase 1 — Competitor Profiling   [NEW]         Firecrawl /map + LLM classification → typology per competitor
Phase 2 — Structured Extract     [NEW]         Firecrawl /extract → schema-bound pricing/contract data (conditional)
Phase 3 — Per-cell Research      [unchanged*]  Gather → Normalize → Synthesize, with new routing rules
Phase 4 — Executive Synthesis    [unchanged]
Phase 5 — Report Render          [unchanged]
```

\* Phase 3's gather agent gains routing logic but its overall shape is preserved.

The key insight: **Phases 1 and 2 run once per competitor and their output is shared across all four pricing-related parameters**. This avoids the V1 anti-pattern where every cell re-discovers the same pricing page.

---

## 4. Tool roles — Firecrawl vs Exa vs Serper+Jina

These tools are not substitutes. They answer fundamentally different *kinds* of questions:

| Tool | Epistemic role | Best at |
|---|---|---|
| **Firecrawl Extract** | "What did the company *say about itself*?" | Pricing tables, ToS clauses, packaging matrices, customer logo lists |
| **Exa** | "What does the *smart internet* say about them?" | Analyst takes, Reddit/Vendr/Tegus signals, customer sentiment, ACV leaks |
| **Serper + Jina** | "What does *Google* know about them right now?" | Funding announcements, leadership changes, recent press, SEC filings |

**Routing principle:** structured/published facts → Firecrawl. Inferred/multi-source facts → Exa. Time-sensitive/news → Serper. Never run all three on the same query expecting better answers — you'll just get three slightly different versions of the same Wikipedia paragraph.

---

## 5. Competitor typology (Phase 1 output)

The classification produced in Phase 1 is the **routing key** for everything downstream. Without it, a uniform pipeline fails on roughly half of Innovera's competitor set, which mixes:

- Transparent-pricing SaaS (Airtable, Bardeen, parts of Glean)
- Opaque enterprise SaaS (AlphaSense, Hebbia, Rogo, Aera, Aily, Palantir)
- Consulting firms with no pricing pages (BCG, McKinsey, Hackett, HBR Strategy Lab)
- Tiny startups with minimal web presence (Rocket, Earthena, Lobo, Qualitate, NexStrat, DeeCee, Omniscient)

### Schema

```python
{
  "competitor": "AlphaSense",
  "type": "opaque_enterprise_saas",   # see enum below
  "has_pricing_page": False,
  "has_terms_page": True,
  "is_public": False,
  "key_pages": {
    "pricing": None,
    "terms": "https://www.alpha-sense.com/terms-of-service/",
    "about": "https://www.alpha-sense.com/about/",
    "customers": "https://www.alpha-sense.com/customers/",
  },
  "confidence": "high",
}
```

### Type enum

| Type | Description | Example |
|---|---|---|
| `transparent_saas` | Public pricing page with tiers | Airtable, Bardeen |
| `opaque_enterprise_saas` | "Contact sales" SaaS, no published prices | AlphaSense, Palantir |
| `consulting_firm` | Project-based, no pricing page | BCG, McKinsey |
| `early_stage_startup` | <Series B, may lack ToS or pricing | Rocket, Lobo |
| `unknown` | Profiling failed or site too thin | — |

### Surfacing to user
The typology distribution is shown in the report header before research begins, e.g. *"You've got 4 consulting firms and 6 opaque enterprise vendors — pricing intel will be limited for these and will lean on Exa for triangulation."* This sets the right expectation up front.

---

## 6. The 10 new questions → parameter mapping (coverage contract)

Every question must be answered inside one parameter's `answer_spec`. This is the contract that guarantees the senior leader gets all 10 answers.

| # | Question | Parameter | Answer source |
|---|---|---|---|
| Q1 | What's in each package/tier? | `packaging` | Firecrawl Extract |
| Q2 | Core pricing unit (per user/project/usage/outcome) | `pricing_mechanics` | Firecrawl Extract |
| Q3 | Starting price + typical ACV | `pricing_mechanics` | Firecrawl (start price) + Exa (ACV) |
| Q4 | What costs extra (add-ons, services, integrations) | `packaging` | Firecrawl Extract |
| Q5 | Pilot or entry offer | `pricing_mechanics` | Firecrawl + Exa |
| Q6 | Upgrade / upsell triggers | `contract_structure` | Exa |
| Q7 | Packaging flexibility (custom bundles, enterprise) | `packaging` | Firecrawl + Exa |
| Q8 | Contract structure (term, minimum, renewal) | `contract_structure` | Firecrawl Extract (ToS) |
| Q9 | How pricing scales with usage / scope | `pricing_mechanics` | Firecrawl Extract |
| Q10 | Main revenue driver | `business_models` (extended) | Exa + Serper |

A final cross-parameter completeness check (post-synthesis) maps each Q-number to the parameter that should have answered it and flags any gap.

---

## 7. The four `VariableDefinition` blocks

Drop into `config/variables.py`. Schema matches existing `VariableDefinition` dataclass.

### 7.1 Packaging

```python
VariableDefinition(
    id="packaging",
    name="Packaging",
    category="Commercial Deep Dive",
    research_prompt="""Analyze how {company} packages and bundles its product offering.

Answer three things explicitly:
1. TIER CONTENTS (Q1): For each named package or tier, what features, capabilities, limits,
   support level, and SLAs are included?
2. ADD-ONS (Q4): What costs extra beyond the base package — paid integrations, professional
   services, premium support, advanced modules, training, certification?
3. FLEXIBILITY (Q7): How flexible is the packaging? Are custom bundles offered for enterprise?
   Is there a "Custom" or "Enterprise" tier? Is everything modular or are tiers locked?

PRIMARY SOURCE: the structured Firecrawl extract from Phase 2 if available.
SECONDARY SOURCES: Exa for customer reviews mentioning what's actually negotiable in practice
(G2, Vendr, Reddit, "switch from X" blog posts).""",
    example_queries=[
        "{company} pricing tiers what's included",
        "{company} add-ons paid integrations services",
        "{company} enterprise custom bundle plan",
        "{company} G2 review what features are locked behind higher tier",
    ],
    answer_spec=[
        "tier names and what each tier includes (Q1)",
        "what costs extra beyond the base package — add-ons, services, integrations (Q4)",
        "packaging flexibility — custom bundles, enterprise plans, negotiability (Q7)",
    ],
    preferred_source_types=["official", "tier1_news"],
    key_terms=[
        "tier", "plan", "package", "include", "add-on", "module",
        "enterprise", "custom", "bundle", "feature", "limit",
    ],
    max_concise_chars=240,
    tier="always",
),
```

### 7.2 Pricing Mechanics

```python
VariableDefinition(
    id="pricing_mechanics",
    name="Pricing Mechanics",
    category="Commercial Deep Dive",
    research_prompt="""Analyze the mechanics of how {company} charges customers.

Answer four things explicitly:
1. PRICING UNIT (Q2): What is the core unit of charge? Per user/seat, per project, per usage
   (API calls, GB, queries), per outcome, flat platform fee, or hybrid?
2. STARTING PRICE & ACV (Q3): What is the published starting price? What is the typical annual
   contract value (ACV) for a real customer (from Vendr, Tegus, earnings, analyst notes)?
3. PILOT/ENTRY OFFER (Q5): Is there a free trial, freemium tier, paid pilot, or POC offering?
   What's its structure, duration, and conversion path?
4. SCALING (Q9): How does the bill grow as the customer scales? Linear per-seat? Tiered with
   step-functions? Volume discounts? Usage caps?

PRIMARY SOURCE: the structured Firecrawl extract from Phase 2 if available (covers Q2, starting
price portion of Q3, and Q9 well). Q3 ACV and Q5 conversion paths usually require Exa.""",
    example_queries=[
        "{company} pricing per user per seat per usage",
        "{company} starting price minimum",
        "{company} typical ACV annual contract value Vendr",
        "{company} free trial pilot POC",
        "{company} volume discount scale pricing",
    ],
    answer_spec=[
        "core pricing unit — per user, per project, per usage, per outcome (Q2)",
        "starting price and typical annual contract value (Q3)",
        "pilot or entry offer structure (Q5)",
        "how pricing scales with usage or scope (Q9)",
    ],
    preferred_source_types=["official", "tier1_news", "analyst"],
    key_terms=[
        "per seat", "per user", "per usage", "per query", "ACV",
        "starting at", "minimum", "trial", "pilot", "POC",
        "volume discount", "scale", "tier",
    ],
    max_concise_chars=300,
    tier="always",
),
```

### 7.3 Contract Structure

```python
VariableDefinition(
    id="contract_structure",
    name="Contract Structure",
    category="Commercial Deep Dive",
    research_prompt="""Analyze the contract terms and upsell mechanics of {company}'s commercial
relationships.

Answer two things explicitly:
1. UPGRADE TRIGGERS (Q6): What causes a customer to expand or upgrade? Seat expansion, usage
   thresholds, feature gating, time-based renegotiation, success-based milestones? What are the
   actual mechanisms — auto-upgrade, sales-led upsell, hard cap forcing renegotiation?
2. CONTRACT STRUCTURE (Q8): What are typical term lengths (monthly, annual, multi-year)?
   Is there a minimum commitment (seat floor, dollar floor)? How does renewal work — auto-renew,
   negotiated, price-uplift on renewal? Early termination terms?

PRIMARY SOURCE for Q8: Firecrawl Extract on the Terms of Service / MSA page (Phase 2 schema
includes these fields).
PRIMARY SOURCE for Q6: Exa — upgrade triggers are rarely published; they leak through customer
blog posts, Vendr negotiation guides, and seller LinkedIn content.""",
    example_queries=[
        "{company} terms of service contract length",
        "{company} minimum commitment seat floor",
        "{company} renewal auto-renew price uplift",
        "{company} upgrade trigger expansion playbook",
        "{company} customer expanded contract Vendr",
    ],
    answer_spec=[
        "upgrade and upsell triggers (Q6)",
        "contract term length, minimum commitment, renewal mechanics (Q8)",
    ],
    preferred_source_types=["official", "tier1_news"],
    key_terms=[
        "contract", "term", "minimum", "commitment", "renewal",
        "auto-renew", "uplift", "expansion", "upgrade", "trigger",
        "seat floor", "MSA", "terms of service",
    ],
    max_concise_chars=240,
    tier="always",
),
```

### 7.4 Extension to existing `business_models`

The existing `business_models` variable already covers revenue streams. Extend its `answer_spec` and `key_terms` to make Q10 ("main revenue driver") an explicit, separately-callable-out item:

```python
# In the existing business_models VariableDefinition, update:
answer_spec=[
    "primary revenue streams",
    "pricing model type",
    "monetization strategy",
    "main revenue driver — subscription, usage, services, or outcomes (Q10)",  # NEW
],
key_terms=[
    "revenue", "business model", "monetization", "fees",
    "subscription", "transaction", "usage-based", "services revenue",  # extended
    "outcomes", "primary driver",                                       # NEW
],
```

No new parameter, no new research cell — Q10 rides on the existing `business_models` cell. This is the lighter-weight choice and avoids paying twice for overlapping output.

---

## 8. The shared Firecrawl Extract schema (Phase 2)

**One schema, one call per competitor**, hitting whichever of {pricing page, terms page, plans page} the Phase 1 typology says exists. Cached and shared across `packaging`, `pricing_mechanics`, and `contract_structure`.

```python
COMMERCIAL_EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        # --- Packaging fields (Q1, Q4, Q7) ---
        "tiers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "starting_price": {"type": "string"},  # "$29/user/month" or "Contact sales"
                    "billing_unit": {"type": "string"},
                    "included_features": {"type": "array", "items": {"type": "string"}},
                    "limits": {"type": "string"},          # "5 seats max", "1000 queries/mo"
                    "is_custom_or_enterprise": {"type": "boolean"},
                },
            },
        },
        "add_ons": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "price": {"type": "string"},
                    "type": {"type": "string"},  # "integration", "service", "module", "support"
                },
            },
        },
        "packaging_flexibility": {"type": "string"},  # narrative — custom bundles allowed?

        # --- Pricing Mechanics fields (Q2, Q3-start, Q5, Q9) ---
        "primary_pricing_unit": {
            "type": "string",
            "enum": ["per_user", "per_project", "per_usage", "per_outcome",
                     "flat_platform", "hybrid", "opaque"],
        },
        "starting_price_published": {"type": "string"},
        "free_trial": {"type": "string"},        # "14 days", "freemium", "paid pilot", "none"
        "scaling_model": {"type": "string"},     # narrative — how bill grows

        # --- Contract Structure fields (Q8, partially) ---
        "contract_term_options": {"type": "array", "items": {"type": "string"}},
        "minimum_commitment": {"type": "string"},
        "renewal_mechanics": {"type": "string"}, # auto-renew, uplift, etc.

        # --- Meta / disclosure ---
        "pricing_disclosure": {
            "type": "string",
            "enum": ["fully_published", "partial", "opaque"],
        },
        "extracted_from_urls": {"type": "array", "items": {"type": "string"}},
    },
}
```

**Cost rationale:** one Firecrawl Extract call per competitor, ~$0.01–0.03 per call depending on page count. For 20 competitors, total Phase 2 cost is roughly $0.20–0.60. Compare to running three separate scrapes per parameter per competitor (~$1.80+). One mega-schema is the obvious win.

---

## 9. Per-typology routing matrix

This is the rule the gather agent uses to decide which tool to use for each (competitor × parameter) cell.

| Competitor type | Packaging | Pricing Mechanics | Contract Structure | Existing parameters |
|---|---|---|---|---|
| `transparent_saas` | Firecrawl extract (cached) + Exa for sentiment | Firecrawl extract + Exa for ACV | Firecrawl extract on ToS + Exa for upgrade triggers | Existing routing |
| `opaque_enterprise_saas` | Exa-led (Vendr/G2/Tegus) + Firecrawl ToS extract for partial signal | Exa-led for ACV/unit; Firecrawl on ToS for term/minimum | Firecrawl ToS extract + Exa for triggers | Existing routing |
| `consulting_firm` | **Bracket and skip detailed scrape.** Note "project-based, fully opaque" as the finding. Exa for engagement-size benchmarks. | Same — note "project-based fee, $X–$Y from industry data" | Same — note "engagement-letter based, no published terms" | Existing routing |
| `early_stage_startup` | Best-effort Firecrawl if pricing page exists, otherwise mark "pre-pricing / unpublished" | Same | Same — often no public ToS | Existing routing |

**Important:** for `consulting_firm` and pricing-opaque competitors, the *finding itself* — "fully opaque, project-based" — is the answer. The synthesis must not pretend to know what isn't published. Surface opacity as data, not as a gap.

---

## 10. Synthesis with mixed sources

When Sonnet 4.6 synthesizes a cell, it receives clearly-labeled blocks:

```
=== STRUCTURED EXTRACT (Firecrawl, source-of-truth for published facts) ===
{json_extract}
=== SEMANTIC EVIDENCE (Exa) ===
[E1] {snippet} — {url}
[E2] ...
=== NEWS / FILINGS (Serper+Jina) ===
[S1] {snippet} — {url}
...
```

Synthesis rules:
1. When Firecrawl extract and Exa disagree on a published fact (e.g. starting price), Firecrawl wins — it's the company's own statement.
2. When Firecrawl extract is silent and Exa carries the answer (typical for ACV, upgrade triggers), cite Exa with normal `[E#]` citations.
3. When *both* are silent, the answer is "not disclosed" — never invent a number.
4. The cell's `confidence` field reflects coverage: `high` when Firecrawl extract is rich and Exa corroborates, `medium` when only one source has it, `low` when both are thin.

---

## 11. Where this lands in the codebase

| Concern | File(s) to touch |
|---|---|
| New variable definitions | `config/variables.py` (add 3, extend 1) |
| Phase 1 — Competitor Profiling | `agents/competitor_profiler.py` (NEW) |
| Phase 2 — Structured Extract | `agents/commercial_extractor.py` (NEW) |
| Routing inside gather | `agents/gather_agent.py` (add typology-aware router) |
| Synthesis source-mixing | `agents/synthesis_agent.py` + `agents/v2_prompts.py` |
| Pipeline wiring | `v2_pipeline.py` (insert Phases 1 & 2 after Discovery) |
| Schema for typology output | `agents/v2_schemas.py` (add `CompetitorProfile`) |
| Schema for extract output | `agents/v2_schemas.py` (add `CommercialExtract`) |
| Coverage check | `agents/coverage_check.py` (NEW — maps Q1–Q10 to parameters and verifies) |
| Frontend parameter list | `frontend/components/runs/VariableSelector.tsx` (add Commercial Deep Dive category) |

The new phases run sequentially after Discovery and *before* the parallel research loop. Both phases parallelize across competitors (~20-way fan-out). Expected added latency: 30–60s for a 20-competitor run.

---

## 12. Coverage check (must-pass before render)

After all syntheses complete and before the executive brief runs, a deterministic check confirms every Q1–Q10 has been addressed:

```python
QUESTION_COVERAGE_MAP = {
    "Q1": ("packaging", "tier names and what each tier includes"),
    "Q2": ("pricing_mechanics", "core pricing unit"),
    "Q3": ("pricing_mechanics", "starting price and typical annual contract value"),
    "Q4": ("packaging", "what costs extra beyond the base package"),
    "Q5": ("pricing_mechanics", "pilot or entry offer structure"),
    "Q6": ("contract_structure", "upgrade and upsell triggers"),
    "Q7": ("packaging", "packaging flexibility"),
    "Q8": ("contract_structure", "contract term length, minimum commitment, renewal mechanics"),
    "Q9": ("pricing_mechanics", "how pricing scales with usage or scope"),
    "Q10": ("business_models", "main revenue driver"),
}
```

For each (competitor × question) pair, the check inspects whether the parameter's synthesis substantively addresses the answer-spec line. Failures don't block the report but are surfaced in a "coverage gaps" section so the user knows exactly which questions came back empty for which competitors — and *why* (typology-driven opacity vs. genuine evidence gap).

---

## 13. Open questions / future work

- **Multi-page Firecrawl extracts.** Some competitors split pricing across multiple pages (plans page + add-ons page + enterprise page). Phase 2 should support N-URL extracts into a single schema. Currently assumes 1–2 pages per competitor.
- **Refresh cadence.** Pricing pages change. Cached Phase 2 results should expire after ~30 days for active competitors. Need a TTL strategy.
- **Vendr / Tegus integration.** ACV signal (Q3) is currently scraped via Exa from public Vendr/Tegus blog content. If Innovera has direct API access to either, that would dramatically improve ACV accuracy.
- **Comparison view.** Once the four parameters are populated for 20 competitors, there's an obvious cross-competitor comparison table waiting to be built. Out of scope for this iteration but worth noting.
- **Consulting-firm benchmarks.** For BCG/McKinsey/Hackett, project-fee benchmarks could be sourced from a curated internal dataset rather than Exa scraping. Future enhancement.

---

## 14. Stack reference

- **LLM:** Claude Sonnet 4.6 (synthesis, classification, query generation)
- **Web search & discovery:** Firecrawl Search (Phase 0), Firecrawl `/map` and `/extract` (Phases 1–2)
- **Semantic web research:** Exa (Phase 3, primary for inferred/multi-source questions)
- **News & filings search:** Serper + Jina Reader (Phase 3, primary for time-sensitive)
- **Pipeline:** existing V2 relational engine in `v2_pipeline.py`

---

## 15. Definition of done

- [ ] 3 new `VariableDefinition` blocks merged into `config/variables.py` and selectable in the parameter UI
- [ ] `business_models` extension live and verified to surface Q10
- [ ] Phase 1 (Competitor Profiling) runs for all 20 competitors and produces typed `CompetitorProfile` records
- [ ] Phase 2 (Structured Extract) runs conditionally per typology and caches `CommercialExtract` records
- [ ] Gather agent routes per the matrix in §9
- [ ] Synthesis prompts accept and label the three source types correctly
- [ ] Coverage check runs and surfaces per-question/per-competitor gaps
- [ ] Report renders the new parameters in a "Commercial Deep Dive" section
- [ ] End-to-end run on the 20-competitor Innovera set completes in <2× the V1 runtime
- [ ] Manual spot-check on 3 competitors of different typologies (e.g. Airtable, AlphaSense, McKinsey) confirms each typology's expected behavior
