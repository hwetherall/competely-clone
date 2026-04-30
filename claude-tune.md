# CLAUDE.md — Innovera Finetune

> Tighten the system's understanding of Innovera so the synthesis layer stops grading Innovera against borrowed rubrics. Three changes ship together: a structured rewrite of `config/innovera_profile.py`, a depth-of-reasoning instruction added to the synthesis prompts, and a swap to Claude Opus 4.7 for the synthesis tier.

---

## 1. Why this feature exists

Run `v2_run_20260428_173648` produced an executive summary that closed with this sentence:

> Innovera occupies a structurally advantaged middle position … but this advantage is invisible to buyers because Innovera lacks a published entry price, a time-to-first-insight metric, a documented onboarding journey, and any quantified ROI claims.

Four claims, four different failure modes:

1. **"No published entry price"** — true factually, but framed as a deficit when it is a deliberate strategic posture. Innovera will not pursue seat-based or per-user pricing.
2. **"No time-to-first-insight metric"** — hallucinated importance. The metric is a frame imported from the seat-priced AI SaaS cohort and does not apply to engagement-based decision intelligence.
3. **"No documented onboarding journey"** — factually wrong. Innovera has a high-touch consultative onboarding process.
4. **"No quantified ROI claims"** — factually wrong as framed. ROI quantification is a roadmap item pending deployed-customer outcome data; the synthesizer should not be inventing its absence as a bullet-point deficit.

The single root cause: `config/innovera_profile.py` is a one-paragraph affirmative description with no negative space, no anti-frame, and no synthesis-time guardrails. The synthesizer fills the gaps by pattern-matching to "good enterprise software" and grading Innovera against the nearest available rubric (which, given the competitor set, is the AI SaaS rubric).

Separately, Zamir's "research could go deeper" feedback points at a different layer of the same problem: the synthesizer stops at first-order claims and does not produce the second-order implications a senior reader expects. The pricing-inference work in the previous Synthesis Quality Pass partially addressed this for one parameter; this feature generalizes it.

This file specifies three changes that together resolve both issues.

---

## 2. Scope

**In scope:**
- Full rewrite of `config/innovera_profile.py` into a five-section structured profile.
- A depth-of-reasoning instruction added to the dimension-level rollup, white-space, and executive synthesis prompts.
- Swap from Claude Sonnet 4.6 to Claude Opus 4.7 at the synthesis tier (gather/extraction stays on Sonnet).

**Out of scope:**
- Adding more sources or doubling search volume. Zamir's "go deeper" was explicitly resolved as depth-of-reasoning, not depth-of-field. Source breadth is good enough; what we do with sources is not.
- Adding new dimensions or parameters. The Innovera variable set is correct; the issue is synthesis quality on the existing set.
- Changes to gather agent or Phase 2 Firecrawl extract. Those layers are performing.
- A post-synthesis validator scanning for hallucinated absences. Belt-and-braces option that we will only build if the profile rewrite alone does not get us to clean output. Flagged in §9.

---

## 3. Change 1 — Structured Innovera profile

Replace `config/innovera_profile.py` in full with the version below. The structure is deliberate: identity first, then deliberate non-pursuits, then affirmed capabilities, then roadmap items, then explicit synthesis-time rules. The synthesizer reads these sections in order, and the rules in Section 5 reference Sections 2–3b by number.

```python
"""
Default Innovera profile used by Innovera-specific prompts.

Structure is deliberate. The synthesis-time rules in Section 5 reference
Sections 2, 3a, and 3b by number — do not renumber without updating the
prompts in agents/v2_prompts.py that reference them.

Owner: Zamir + product. Review cadence: quarterly, or whenever Innovera's
positioning or shipped capabilities change.
"""

INNOVERA_PROFILE = """\
# Innovera — Profile for Synthesis

## 1. Identity

Innovera is an AI-native decision intelligence platform. It helps organizations
make high-stakes business decisions under uncertainty by simulating outcomes,
pressure-testing assumptions, and producing investment-grade recommendations.

The core mechanism is the digital twin of a business initiative — a simulated
replica composed of specialized AI agents, validated by domain experts, that
explores possible futures before a decision is made. Innovera's outputs are
decision-ready artifacts (investment-grade reports, ranked options, execution
roadmaps, portfolio dashboards) — not chatbot answers, not BI dashboards, not
raw analytics.

Use cases the platform serves:
  - Market Entry
  - Investment / M&A / Venture Diligence
  - New Product or Venture
  - Vendor or Technology Selection

## 2. Strategic Posture — What Innovera Deliberately Is Not

These are positioning choices, not gaps. The synthesizer must not frame any of
the below as deficits.

  - Not pursuing seat-based or per-user pricing, now or in the future.
    Innovera's commercial model is engagement- and outcome-based, mirroring how
    strategic decisions are actually procured.
  - Not a BI tool, dashboard product, or analytics platform. Backward-looking
    analytics ("what happened?") is explicitly out of scope. Innovera answers
    "what should we do next, and how?"
  - Not a chatbot or thin LLM wrapper. The product is a multi-agent system with
    framework-driven structure, expert validation, and synthesis layers —
    defensibility lives in workflow design, not raw model capability.
  - Not optimized for a "time-to-first-insight" metric. Decision-grade outputs
    over weeks of engagement are the unit of value. Latency-to-response is not
    a meaningful KPI for this product.
  - Not competing on cheaper, faster consulting alone. The wedge is decision
    quality plus AI-native scale, with consulting-substitute economics as a
    downstream consequence.

## 3a. Current Capabilities — Affirmed

The synthesizer must not claim Innovera lacks any of the below.

  - Documented onboarding journey. Onboarding is high-touch and consultative:
    prospect calls (Zoom and in-person) to map the decision context,
    stakeholders, and desired output before agent work begins. This is the
    deliberate model for engagement-based decision work, not the absence of
    self-serve onboarding.
  - Expert validation network. Innovera maintains a standing network of
    hundreds of subject-matter experts who review agent outputs at key
    decision points. Most experts are top-of-field practitioners. Areas of
    particular depth: energy, manufacturing, education, banking and finance.
  - Multi-domain agent coverage. Specialized agents cover ten domains:
      1.  Opportunity Validation
      2.  Market Research
      3.  Competitor Research
      4.  Go-to-Market
      5.  Business Model
      6.  Unit Economics
      7.  Finance and Operations
      8.  Team and Talent
      9.  Legal and IP
      10. Product and Technology
  - Hybrid AI-plus-human protocol. Agents do structured analysis; experts
    validate and challenge outputs at defined review points; results meet
    consultant-grade quality.

## 3b. Roadmap — Not Yet Shipped

The synthesizer should frame these as roadmap items, not deficits, and should
not lead with them in any executive summary.

  - Quantified ROI claims. Pending sufficient deployed-customer outcome data.
    Innovera will publish ROI numbers when there is real customer proof to
    anchor them.

## 4. Strategic Constraints

  - Target buyer: corporate innovators, strategy teams, and executives at the
    enterprise level. Innovera is not a freemium-to-PLG product and will not be
    benchmarked against tools that are.
  - Commercial model: engagement-based, with deal sizes reflective of the
    strategic value of the decision being made. Not seat-counted. Not
    usage-metered.
  - Quality bar: McKinsey-grade output. Comparisons to seat-priced AI tools
    (Glean, Rocket) on commercial structure are category errors.

## 5. Synthesis Instructions

These rules govern any claim the synthesizer makes about Innovera.

  1. Before claiming Innovera lacks any capability, check Sections 3a and 3b.
     If the capability appears in 3a, do not claim its absence — affirm it.
     If it appears in 3b, frame it as roadmap, not deficit, and do not lead
     with it in any executive summary.
  2. Do not import frames from adjacent cohorts and apply them to Innovera as
     evaluation rubrics. Published entry pricing, free trials,
     time-to-first-insight, freemium tiers, and self-serve onboarding are
     evaluation frames for seat-priced AI SaaS — not for engagement-based
     decision intelligence platforms. Section 2 lists Innovera's deliberate
     non-pursuits; treat each as a positive positioning choice when it
     appears in synthesis.
  3. Use Section 1's use-case categories (Market Entry, M&A, New Product,
     Vendor Selection) as Innovera's evaluation frame, not generic
     enterprise-software-quality-bars. When comparing Innovera to a competitor,
     ask whether the competitor serves these use cases at decision-grade
     quality — not whether it has a cheaper entry point.
"""
```

A note on Section 3b: ROI is the only roadmap item we have explicit confirmation of. If other capabilities are in flight (a published security posture, a partner ecosystem, a self-serve tier under consideration), they should be added to 3b before merge — same risk profile as ROI.

---

## 4. Change 2 — Depth-of-reasoning instruction

The synthesizer currently produces evidence → first-order claim and stops. Going deeper means evidence → first-order claim → second-order implication. This is a prompt-layer change, not a structural one.

Add the block below to `agents/v2_prompts.py` and inject it into the synthesis prompts for: dimension-level rollups, white-space callouts, the Takeaway for Innovera, and the executive brief. Do **not** apply it at the individual cell level — cells should stay focused on their specific question.

```python
DEPTH_OF_REASONING_INSTRUCTION = """
For each major claim in your output, produce a second-order implication
immediately after the claim. The structure is:

  [Evidence-grounded first-order claim about the competitor or market.]
  [Second-order implication: what this claim means for the buyer, the
   market, or Innovera over the next 12-24 months.]

The implication must not restate the claim. It must answer one of:
  - Vulnerability: what does this expose the competitor to?
  - Opportunity: what does this enable that the competitor is not yet doing?
  - Trajectory: what does this predict about the competitor's path?
  - Innovera-specific: what does this mean for how Innovera should compete?

Implications are not optional. A first-order claim without a second-order
implication is shallow synthesis and should be revised before output. Keep
each implication to one or two sentences — do not over-elaborate.

Worked example.

  Shallow:
    "AlphaSense's moat is its content licensing - its enterprise customers
    pay primarily for access to expert-call transcripts and broker research."

  With second-order implication:
    "AlphaSense's moat is its content licensing - its enterprise customers
    pay primarily for access to expert-call transcripts and broker research.
    [Vulnerability:] This moat is rentable, not built - any well-capitalized
    foundation-model lab or financial data incumbent can license the same
    content at the same price. AlphaSense's vertical-first defensibility
    therefore has a finite half-life and depends on staying ahead on workflow
    integration faster than capital crowds in."
"""
```

Two operational notes. First, this will lengthen synthesis outputs by roughly 30–50%. That is the point. The executive summary should grow from one dense paragraph to two — one of claims, one of implications — or to a single paragraph where each claim carries its implication inline. Second, the instruction must be paired with a length cap on the implication itself (one or two sentences); without a cap the model will over-elaborate and the implications become longer than the claims.

For the Takeaway for Innovera specifically, this instruction supersedes the deduplication rule in the previous Synthesis Quality Pass. The deduplication rule said "do not restate dimension-level patterns." This instruction says "for every claim, produce an implication." Together they force the Takeaway to be implication-dense, which is what Zamir is asking for.

---

## 5. Change 3 — Model upgrade for synthesis tier

The current pipeline runs Claude Sonnet 4.6 across all phases. Sonnet is correct for gather and extraction (fast, cheap, accurate enough). It is the bottleneck on synthesis depth, where the upgrade to Opus 4.7 has measurable headroom.

Tier the model selection by phase:

```python
# config/settings.py
GATHER_MODEL    = "claude-sonnet-4-6"   # unchanged
EXTRACT_MODEL   = "claude-sonnet-4-6"   # unchanged
SYNTHESIS_MODEL = "claude-opus-4-7"     # NEW — dimension-level + white-space
TAKEAWAY_MODEL  = "claude-opus-4-7"     # NEW — Innovera-specific synthesis
EXECUTIVE_MODEL = "claude-opus-4-7"     # NEW — executive brief
```

Files that need to read from these new variables rather than a single hardcoded model: `agents/synthesis_agent.py`, `agents/executive_brief_agent.py`, and the Takeaway-specific synthesis path (currently in `agents/synthesis_agent.py` or wherever `inv_takeaway_for_innovera` is dispatched).

**Cost and latency flags.** Opus is materially more expensive per token than Sonnet (roughly 5× at current API pricing) and roughly 1.5–2× slower at typical synthesis-prompt lengths. For a 200-cell run with synthesis at three layers (dimension, Takeaway, executive), the marginal cost per run will increase. The depth-of-reasoning instruction in Change 2 also increases output token count, compounding this. Expected end-to-end runtime: 1.4–1.6× the current Sonnet baseline. Worth confirming the budget posture before merge.

A possible compromise if cost is a concern: keep Sonnet 4.6 for dimension-level rollups (200 cells × 20 competitors = many calls) and use Opus 4.7 only for the Takeaway and executive brief (1 of each per run). This captures most of the depth benefit at a fraction of the marginal cost. Recommendation: start with Opus across all three synthesis layers for one run, evaluate the quality lift, and downshift dimension-level synthesis to Sonnet if the lift there is marginal.

---

## 6. Where this lands in the codebase

| Concern | File(s) to touch |
|---|---|
| Profile rewrite | `config/innovera_profile.py` (replace in full) |
| Depth-of-reasoning prompt block | `agents/v2_prompts.py` (add `DEPTH_OF_REASONING_INSTRUCTION`) |
| Inject depth instruction into dimension synthesis | `agents/synthesis_agent.py` |
| Inject depth instruction into Takeaway synthesis | `agents/synthesis_agent.py` (Takeaway path) |
| Inject depth instruction into executive brief | `agents/executive_brief_agent.py` |
| Model selection per tier | `config/settings.py` + every call site that reads the model name |
| Doc update | `CLAUDE.md` (the original Commercial Deep Dive doc) — add a §15 entry noting the Opus upgrade |

No frontend changes. No new schemas. No new phases.

---

## 7. Acceptance criteria

A rerun of the 20-competitor Innovera analysis with the same competitor set as `v2_run_20260428_173648` must satisfy all of the following.

1. **No hallucinated deficits in the executive summary.** None of the four claims that closed the previous summary may reappear as a deficit. Specifically, the rerun must not assert that Innovera "lacks a published entry price" (it must instead frame this as a strategic posture if mentioned at all), must not reference a "time-to-first-insight metric" as an evaluation rubric for Innovera, must not claim Innovera lacks a documented onboarding journey, and must not lead with the absence of quantified ROI as a bullet-point deficit.
2. **Profile facts are surfaced where appropriate.** The expert network's hundreds-scale and depth in energy / manufacturing / education / banking-finance must appear in at least one synthesis layer that discusses Innovera's defensibility. The ten-domain agent coverage must appear by name in any dimension synthesis discussing breadth-of-capability.
3. **Second-order implications are present.** Manual review of the executive brief, Takeaway, and three randomly sampled dimension rollups must confirm each major claim carries an implication of one of the four types (vulnerability / opportunity / trajectory / Innovera-specific). A run that produces only first-order claims fails this criterion regardless of how good the claims are.
4. **Model tiering is correct.** Logs confirm Sonnet 4.6 was used for gather and extraction; Opus 4.7 was used for dimension synthesis, Takeaway, and executive brief.
5. **Runtime within bound.** End-to-end runtime ≤1.6× the previous baseline.
6. **No regression.** Citation discipline preserved (no fabricated `[S#]` markers). Coverage section from the Synthesis Quality Pass still renders correctly. The pricing-inference capability still produces `inferred` ranges for consulting firms.

---

## 8. Definition of done

- [ ] `config/innovera_profile.py` replaced with the five-section version. Owner and review cadence documented in the module docstring.
- [ ] `DEPTH_OF_REASONING_INSTRUCTION` added to `agents/v2_prompts.py` and injected into the four target prompts.
- [ ] Model selection moved behind tiered config variables. Every call site updated.
- [ ] One full rerun of the 20-competitor Innovera set passes all six acceptance criteria.
- [ ] A side-by-side diff of the previous run's executive summary and the new run's executive summary is reviewed by Zamir before merge. The new summary should read as observably deeper, not just longer.

---

## 9. Open questions

- **Post-synthesis hallucinated-absence validator.** A regex/keyword scan for "Innovera lacks", "Innovera doesn't", "Innovera is missing", "Innovera has no" with profile-aware validation. Recommend not building this until we see whether the profile rewrite alone gets us to clean output. If the rerun still produces 1–2 hallucinated absences, the validator becomes the right next move.
- **Cost ceiling.** Worth confirming with finance whether the 1.4–1.6× runtime and roughly 4–5× model spend per run is acceptable before this becomes the default configuration. If not, the dimension-synthesis-on-Sonnet compromise from §5 is the fallback.
- **Profile drift over time.** Section 3a will go stale as Innovera ships new capabilities (the ROI numbers in Section 3b being the most likely first migration). The module docstring names a quarterly review cadence — worth deciding whether that lives on the eng team's calendar or Zamir's.
- **Whether to expose the profile to other Innovera-lens runs.** Currently `INNOVERA_PROFILE` is loaded by Innovera-specific prompts only. If the discovery agent or future analyses want to use the same structured profile, the loader should be lifted into a small accessor function rather than passed as a string. Not blocking; flag for the next refactor.
- **Length cap on implications.** Recommended one to two sentences per implication, pinned in the prompt. Worth re-checking after the first rerun whether the cap is holding or if the model is drifting toward over-elaboration.