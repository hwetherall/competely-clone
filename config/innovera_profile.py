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
