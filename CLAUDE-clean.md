# CLAUDE.md — Synthesis Quality Pass

> Tighten the synthesis layer of the Innovera DeepDive Market Report after a review of run `v2_run_20260428_173648` surfaced five recurring weaknesses: defensive pricing, post-recovery output degradation, qualitative-only recommendations, repetition between synthesis layers, and an absent epistemic-honesty section.

---

## 1. Why this feature exists

The v2 pipeline now produces structurally sound 200-cell reports with credible evidence and good citation discipline. The remaining quality issues are all in the **synthesis** layer, not the gather layer:

1. **Pricing inference is too defensive.** When a competitor doesn't publish prices, the synthesizer collapses to "Confidential" or "Unknown" — even when EY-style leaked rate cards, federal procurement records, and trade-press benchmarks would support a defensible inferred range. This affects every consulting firm and roughly half of opaque enterprise SaaS players in the Innovera competitor set.
2. **Recovery leaves visible scars.** When the synthesizer breaks mid-run and the checkpoint system rescues the analysis (as happened with `inv_takeaway_for_innovera` on 28 April), the recovery script restores narrative content but leaves raw `evidence_summary` text in the `rationale` field of `Top Rankings` and pipeline-internal columns (`saved_fact_count`, `confidence`) in user-facing positioning tables.
3. **Recommendations don't quantify.** The synthesizer is structurally averse to numbers in the recommendations layer — no price points, no ARR targets, no probability rankings, no time horizons. A senior reader expects at least one quantified call to action per major recommendation.
4. **Synthesis layers repeat each other.** The same five lessons appear in the executive brief, in dimension-level white-space callouts, and in the Takeaway for Innovera. The Takeaway should *transcend* the dimension layer, not recapitulate it.
5. **Coverage gaps are scattered.** Each dimension's synthesis notes "Unknown" cells in passing, but no section aggregates them. A senior reader can't tell at a glance what the report *couldn't* learn, why, and what would unlock those gaps in the next run.

This feature addresses all five in one pass because they share the same underlying fix: the synthesis prompt and the post-synthesis QA layer.

---

## 2. Scope

**In scope:**
- A new "inferred-with-assumptions" output type in `EvidenceClaim` and the synthesis schema, distinct from "published" and "unknown."
- A curated benchmark dataset for consulting-firm engagement economics, used to support inference for `consulting_firm` and `opaque_enterprise_saas` typologies.
- A `quantified_recommendation` schema requiring at minimum one numeric field per recommendation (price band, ARR target, time horizon, or impact magnitude).
- A self-check pass on the Takeaway for Innovera synthesis that flags repetition with dimension-level rollups.
- A new `Coverage & Limitations` section in the rendered report, generated deterministically from gather-layer "unknown" / "not disclosed" outputs.
- A polish pass on the recovery script (`scripts/repair_takeaway_for_innovera_analysis.py` and any future per-parameter repair scripts) so post-recovery outputs match a fresh-run schema.

**Out of scope:**
- Changes to the gather layer or the Phase 2 Firecrawl extract.
- New parameters or dimensions — this is purely a synthesis-quality pass.
- The executive-brief synthesis (handled by `agents/executive_brief_agent.py`) — that layer is performing well; only dimension-level and Takeaway syntheses change.
- A full UI redesign of the report — the new Coverage section reuses the existing parameter-modal renderer.

---

## 3. The five improvements

### 3.1 Inferred-with-assumptions as a first-class output type

**Problem.** The current synthesis prompt instructs the model to "surface opacity as a finding" for consulting firms (see `agents/gather_agent.py:_attach_commercial_context`). This is correct as a *guard against fabrication* but wrong as a *synthesis posture*. It collapses two distinct epistemic states — "we have no signal" and "we have triangulation material but no published number" — into one defensive answer.

**Fix.** Introduce three explicit states for any numeric claim in the commercial parameters:

| State | When to use | Required fields |
|---|---|---|
| `published` | A primary or credible secondary source publishes the number | `value`, `source_id` |
| `inferred` | No published number, but multiple signals support a defensible range | `range_low`, `range_high`, `assumptions[]`, `method`, `confidence` |
| `unknown` | Neither published nor reliably inferable | `reason` (typology / evidence gap / pre-revenue / other) |

Add to `agents/v2_schemas.py`:

```python
@dataclass
class NumericClaim:
    """A numeric claim with explicit epistemic state."""
    state: Literal["published", "inferred", "unknown"]
    value: Optional[float] = None              # published only
    range_low: Optional[float] = None          # inferred only
    range_high: Optional[float] = None         # inferred only
    unit: str = ""                             # "USD", "USD/seat/year", etc.
    assumptions: List[str] = field(default_factory=list)
    method: str = ""                           # short methodology label
    confidence: Literal["high", "medium", "low"] = "low"
    source_ids: List[str] = field(default_factory=list)
    reason: str = ""                           # unknown only
```

**Synthesis prompt change** (in `agents/v2_prompts.py`, `SYNTHESIS_GENERATE_PROMPT` for commercial parameters):

> When asked for a price, ACV, deal size, contract value, or any other numeric commercial fact, you must produce one of three outputs: `published` (cite the source), `inferred` (state range_low, range_high, assumptions, and method — see Section 3.1.1 below), or `unknown` (state the reason). Do not collapse `inferred` into `unknown` simply because no source publishes the number. If you have benchmark data and at least two signals about scope (engagement length, team size, deal size, etc.), you must produce an `inferred` claim with explicit assumptions.

#### 3.1.1 Consulting-firm benchmark dataset

To make `inferred` claims defensible for `consulting_firm` typology competitors, add a curated benchmark file at `config/consulting_benchmarks.py`:

```python
CONSULTING_BENCHMARKS = {
    "mbb": {
        # McKinsey, BCG, Bain
        "blended_day_rate_usd": (8_000, 15_000),
        "partner_day_rate_usd": (15_000, 30_000),
        "associate_day_rate_usd": (3_000, 6_000),
        "typical_team_size": (3, 6),
        "typical_engagement_weeks": (8, 16),
        "minimum_engagement_usd": 500_000,
        "sources": [
            "USAspending.gov federal contract awards 2020-2025",
            "Source Global Research consulting market reports",
            "Kennedy/ALM Vault consulting benchmarks",
            "Glassdoor partner-track compensation data",
        ],
    },
    "big_four": {
        # EY, Deloitte, KPMG, PwC strategy practices
        "blended_day_rate_usd": (4_000, 10_000),
        "partner_day_rate_usd": (10_000, 20_000),
        "typical_team_size": (4, 8),
        "typical_engagement_weeks": (6, 20),
        "minimum_engagement_usd": 250_000,
        "anchor_data_points": [
            "EY government rate card: $675/hr list, $408 discounted (2024)",
            "EY CogniStreamer platform ACV: ~$91,105 (2024 procurement record)",
        ],
        "sources": ["GSA Schedule contract awards", "EU public procurement disclosures"],
    },
    "specialist": {
        # Hackett, ZS, Oliver Wyman, etc.
        "blended_day_rate_usd": (5_000, 12_000),
        "typical_team_size": (2, 5),
        "typical_engagement_weeks": (4, 12),
    },
}
```

This file is curated, not scraped at runtime. It is reviewed and updated quarterly. It is loaded into the gather agent's commercial context for any competitor with `type == "consulting_firm"`, so the synthesizer has benchmark anchors to triangulate against.

#### 3.1.2 How `inferred` claims render

In the positioning table:

> `Inferred $1.5M–$3M` (4-week, 4-person engagement at MBB blended day rate; medium confidence)

In narrative prose:

> A four-week MBB engagement for a US bank would land in the **$1.5M–$3M range**, assuming a 4-person team at a blended $8K–$15K day rate (Source Global Research, GSA federal contract awards). This is an order-of-magnitude floor — McKinsey and BCG engagements of this length are unusual; typical engagements run 8–12 weeks at $3M–$8M.

The `[inferred]` tag must appear inline so a careful reader can distinguish published facts from triangulated estimates.

### 3.2 Quantified recommendations layer

**Problem.** Recommendations in the executive brief and Takeaway sections are qualitatively rich but numerically empty. The Takeaway recommends "publish transparent pilot pricing" without proposing a price point, even though the report contains enough data — Glean ($50–100/user/month, $60K min ACV), Rocket ($25/month entry), Aily ($25K–$120K setup, $25M+ contracts), Rogo ($420K average ACV) — to triangulate one.

**Fix.** Add a `quantified_recommendation` schema and require at least one numeric field per recommendation:

```python
@dataclass
class QuantifiedRecommendation:
    headline: str                              # "Launch a 30-day Initiative Sprint"
    rationale: str
    numeric_targets: Dict[str, NumericClaim]   # at least one required
    time_horizon_days: int                     # explicit
    success_metric: str                        # one quantified KPI
    impact_likelihood: Literal["high", "medium", "low"]
    cost_to_implement: Literal["low", "medium", "high"]
    triangulation_source_ids: List[str]
```

For the Initiative Sprint recommendation specifically, this would force the synthesizer to land on something like:

> **Launch a 30-day Initiative Sprint** at a $50K–$80K fixed-fee pilot price (5–10% of an MBB engagement at the floor; 2–3x a Glean annual contract; below typical MBB minimum engagement). Target 8–12 paid pilots in 90 days. Conversion target: 40% pilot-to-annual (anchored on Rogo's documented +18%/+20% trial conversion lifts). Success threshold: $1.5M–$2.4M of pilot revenue plus first-year ARR signal by month 6.

**Prompt change** (in `agents/v2_prompts.py`, the synthesis prompt for `inv_takeaway_for_innovera` and the executive brief):

> Every recommendation you produce must include at least one quantified target. If you cannot produce a defensible quantified target from the evidence in this report, mark the recommendation as `qualitative_only` with a one-line reason — but this should be the exception, not the default. The report contains pricing data on at least four competitors and ACV data on at least five; use them as triangulation anchors.

### 3.3 Synthesis deduplication — Takeaway must add layers, not recap

**Problem.** By the time a reader reaches `inv_takeaway_for_innovera`, they have already seen Rogo's vertical depth, AlphaSense's content moat, Rocket's accessibility, and the consulting-substitute crowding pattern five times across the dimension-level analyses. The Takeaway currently restates these patterns rather than surfacing what they *jointly imply*.

**Fix.** A two-part change.

**Part A — prompt instruction** (in `agents/v2_prompts.py`, `INV_TAKEAWAY_SYNTHESIS_PROMPT`):

> The dimension-level rollups have already named the patterns: vertical depth wins (Rogo, Hebbia), trust architecture compounds (AlphaSense, FICO), accessibility steals attention (Rocket, DeeCee.ai), consulting-substitute language is crowding (NexStrat, NitroLens), Big Three are slow but distribution-rich (McKinsey, BCG, EY, Deloitte). **Do not restate these patterns.** Your job is to surface what they *jointly imply* — the second-order observations a senior reader cannot get from any single dimension. Specifically: cross-pattern timing (which threats materialize when), forced tradeoffs (what Innovera must give up to win which segment), and quantified bets (what the Initiative Sprint should cost, target, and convert at).

**Part B — post-synthesis self-check** in `agents/synthesis_agent.py`. After the Takeaway synthesis completes, run a deterministic check that compares the Takeaway's narrative against the concatenated dimension-level white-space and trends sections, and flags any sentence with >70% lexical overlap. The check returns a list of repetitions to a follow-up LLM call that rewrites flagged sentences with a fresh second-order observation. Cap at one rewrite pass to avoid infinite loops.

### 3.4 Coverage & Limitations section

**Problem.** The current report mentions coverage at the Commercial Coverage banner ("Total checks: 200, Covered checks: 200, Gap count: 0") and scatters "Unknown" markers across positioning tables, but never aggregates them into a single epistemic-honesty section. A senior reader can't quickly answer the question "what couldn't this report learn, and why?"

**Fix.** Add a new top-level section to the rendered report, generated deterministically from gather-layer outputs (no LLM call needed):

```markdown
## Coverage & Limitations

### What this report could not establish

| Competitor | Dimension | Question | Reason |
|---|---|---|---|
| Mindcorp | Pricing Mechanics | Starting price, ACV | Pre-revenue / no public signal |
| BCG X | Contract Structure | Term length, renewal mechanics | Consulting-firm typology — no public terms page |
| Quantum Rise | Pricing Mechanics | Pricing unit | Brand-identity collision in search results — likely conflated with crypto entity |
| ... | ... | ... | ... |

### Where we used inferred ranges

| Competitor | Field | Inferred range | Method | Confidence |
|---|---|---|---|---|
| McKinsey | Engagement price (4-week, 4-person) | $1.5M–$3M | MBB blended day rate × team size × duration | Medium |
| BCG X | Engagement price (10-week sprint) | $4M–$8M | MBB blended day rate × team size × duration | Medium |
| ... | ... | ... | ... | ... |

### What would unlock the next run

- Direct API access to Vendr or Tegus would dramatically improve ACV signal for opaque enterprise SaaS players (Hebbia, Aily Labs, Brightwave currently low-confidence).
- A USAspending.gov scraper would give us anchored consulting-firm engagement values rather than benchmark inference.
- A 30-day rerun on Mindcorp, DeeCee.ai, and NitroLens AI may surface funding announcements that reset their evidence base.
```

This section is generated by a new function `agents/coverage_renderer.py:render_coverage_and_limitations()`. It reads the existing per-cell `confidence` fields and `unknown_reasons`, groups by reason, and produces the three tables above. No new LLM calls.

The Commercial Coverage banner at the top of the report becomes redundant once this section exists; remove it.

### 3.5 Recovery polish

**Problem.** When the synthesizer breaks mid-run and a per-parameter repair script is invoked (e.g., `scripts/repair_takeaway_for_innovera_analysis.py`), the recovery preserves the saved evidence table but emits Top Rankings and Positioning Tables with raw pipeline artifacts:

- `Top Rankings` rationale field contains truncated `evidence_summary` text with embedded `[S2]` markers and trailing ellipses.
- `Positioning Table` includes pipeline-internal columns (`evidence_summary`, `saved_fact_count`, `confidence`) that should not appear in user-facing output.
- No footnote tells the reader the section was reconstructed from a checkpoint rather than synthesized from scratch.

**Fix.** Refactor recovery into a generic post-recovery polish pass at `scripts/recovery_polish.py` that any per-parameter repair script can call:

```python
def polish_recovered_synthesis(
    parameter_id: str,
    recovered_section: Dict[str, Any],
    evidence_table: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Post-process a recovered synthesis section so it matches a fresh-run schema.

    Steps:
    1. Regenerate the rationale field of every Top Rankings entry as a single
       sentence, no [S] markers, no ellipses. Use the existing label and the
       first 1-2 facts from evidence_summary as input to a single Claude call.
    2. Strip pipeline-internal columns from the positioning table:
       - Always remove: evidence_summary, saved_fact_count, confidence
       - Keep: company, position, rank, label, plus parameter-specific columns
         declared in PARAMETER_USER_FACING_COLUMNS.
    3. Append a footnote to the rendered section:
       "*This section was reconstructed from a mid-run checkpoint on
       {recovery_timestamp}. The evidence table is intact; the narrative
       and rankings were regenerated from the saved evidence."
    """
```

`PARAMETER_USER_FACING_COLUMNS` is a small registry that names the columns that should appear in each parameter's positioning table — the same columns a fresh run would render. It lives next to the parameter definitions in `config/variables.py`.

The footnote is important and non-negotiable: a careful reader should always be able to tell which sections were synthesized from scratch and which were reconstructed.

---

## 4. Where this lands in the codebase

| Concern | File(s) to touch |
|---|---|
| `NumericClaim` schema and three-state pricing | `agents/v2_schemas.py` (extend) |
| Consulting benchmark dataset | `config/consulting_benchmarks.py` (NEW) |
| Benchmark injection into gather context | `agents/gather_agent.py` (extend `_attach_commercial_context`) |
| Synthesis prompt updates (commercial parameters) | `agents/v2_prompts.py` (modify `SYNTHESIS_GENERATE_PROMPT`, `INV_TAKEAWAY_SYNTHESIS_PROMPT`) |
| `QuantifiedRecommendation` schema | `agents/v2_schemas.py` (extend) |
| Takeaway self-check repetition pass | `agents/synthesis_agent.py` (add `_check_takeaway_redundancy`) |
| Coverage renderer | `agents/coverage_renderer.py` (NEW) |
| Report renderer wiring | `utils/generate_v2_report.py` (insert Coverage section, remove old banner) |
| Generic post-recovery polish | `scripts/recovery_polish.py` (NEW) |
| Per-parameter recovery scripts | `scripts/repair_takeaway_for_innovera_analysis.py` and any future siblings — call into polish module |
| User-facing column registry | `config/variables.py` (add `PARAMETER_USER_FACING_COLUMNS`) |

No frontend changes. The new Coverage section renders inside the existing report markdown.

---

## 5. Acceptance criteria

A rerun of the 20-competitor Innovera analysis must satisfy all of the following:

1. **Pricing inference.** At least 3 of {McKinsey, BCG X, Deloitte, EY} produce an `inferred` engagement-price range with stated assumptions, method, and medium-or-better confidence. None should be flat "Confidential."
2. **Quantified recommendations.** Every recommendation in the Takeaway and executive brief contains at least one numeric target. The Initiative Sprint recommendation lands a specific pilot price band, target pilot count, and target conversion rate.
3. **Takeaway novelty.** Manual review of the Takeaway against dimension-level rollups shows ≤2 sentences with high lexical overlap. The Takeaway introduces at least three observations that don't appear in any single dimension synthesis.
4. **Coverage section present and accurate.** The new Coverage & Limitations section enumerates every "unknown" cell from the run, classified by reason, and lists every `inferred` claim with its method.
5. **Recovery polish.** A simulated mid-run failure on `inv_takeaway_for_innovera` followed by recovery produces output indistinguishable from a fresh run, except for the visible footnote indicating reconstruction.
6. **No regression.** Runtime stays within 1.2× the current baseline. Citation discipline (no fabricated `[S#]` markers) is preserved.

---

## 6. Definition of done

- [ ] `NumericClaim` and `QuantifiedRecommendation` schemas merged in `agents/v2_schemas.py`.
- [ ] `config/consulting_benchmarks.py` shipped with curated MBB / Big Four / specialist benchmarks and a documented refresh cadence.
- [ ] Synthesis prompts updated for the three commercial parameters and the Takeaway.
- [ ] `agents/coverage_renderer.py` shipped and wired into `utils/generate_v2_report.py`.
- [ ] `scripts/recovery_polish.py` shipped and called from `scripts/repair_takeaway_for_innovera_analysis.py`.
- [ ] Test fixtures cover: (a) consulting-firm with no published price → `inferred` output, (b) genuinely unknown → `unknown` output, (c) recovery polish on a synthetic checkpoint → fresh-run-equivalent output.
- [ ] One full rerun of the 20-competitor Innovera set passes all six acceptance criteria.
- [ ] Reviewer spot-check on McKinsey, BCG X, and Mindcorp confirms each takes the right epistemic posture (`inferred` for the consulting firms, `unknown` for the pre-revenue startup).

---

## 7. Open questions

- **Benchmark refresh cadence.** `consulting_benchmarks.py` is hand-curated. Quarterly is suggested but the right cadence may be annual. Worth deciding before merge so the file has a documented owner and review date in its docstring.
- **Inferred-claim rendering in the positioning table.** The proposal is `Inferred $1.5M–$3M` inline. An alternative is a separate `state` column. Inline is more compact; a separate column is more queryable. Recommend inline for v1 and revisit if the table starts looking dense.
- **Takeaway self-check loop bound.** One rewrite pass is suggested. If repetition rates stay high after one pass, consider a hard cap on Takeaway length instead — forcing brevity is often a cleaner deduplication mechanism than rewriting.
- **Coverage section vs. inline Unknown markers.** Should the inline `Unknown` cells in positioning tables remain, or should they all migrate to the Coverage section? Recommend keeping inline (so each table is self-contained) and using the Coverage section as an aggregated index, not a replacement.
- **Big Four typology overlap with `opaque_enterprise_saas`.** EY, Deloitte, etc. operate consulting *and* platform businesses (CogniStreamer, Ascend). The benchmark dataset assumes consulting-firm pricing, but their platform ACVs are SaaS-shaped. The competitor profiler may need to support a `mixed` typology that consults both the consulting and SaaS benchmark sets. Out of scope for v1; flag for follow-up.
- **Do we need a parallel `Coverage & Limitations` for the executive brief?** The brief currently summarizes only positive findings. A "what we couldn't tell you" callout at the brief level could be one short paragraph. Recommend deferring until we see how the new full-report Coverage section reads.
