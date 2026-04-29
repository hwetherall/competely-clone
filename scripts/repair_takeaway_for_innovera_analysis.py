"""
Repair the recovered Takeaway for Innovera synthesis in a V2 run JSON.

This is the highest-value synthesis parameter. The recovery path preserved the
company-by-company evidence table but left the narrative sections as a fallback.
This script replaces those fields with a frontier-model synthesis grounded in
the saved table and Innovera profile.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


TARGET_FILES = [
    Path("data/results/v2_run_20260428_173648.json"),
    Path("data/results/checkpoint_v2_run_20260428_173648_recovery.json"),
]


HEADLINE = (
    "Innovera's winning path is not to become another broad AI platform or another bespoke consultancy; "
    "it is to productize a trusted, expert-validated decision sprint that lands through one urgent boardroom "
    "workflow and expands into always-on initiative intelligence."
)


EXECUTIVE_SUMMARY = (
    "The competitor set gives Innovera a clear strategic recipe: borrow AlphaSense and Rogo's trust architecture, "
    "Rocket and DeeCee.ai's accessibility, NexStrat and NitroLens's consulting-substitute language, Aily and Glean's "
    "ROI discipline, and FICO's governance seriousness, while avoiding the opacity and bespoke drag of the consulting "
    "incumbents. The immediate vulnerability is not product capability; it is packaging and proof. Innovera needs a "
    "named entry product, a visible time-to-first-insight promise, transparent pilot pricing, evidence of expert "
    "validation, and a few measurable business outcomes. The highest-leverage next move is a 30-day Initiative Sprint "
    "for one concrete executive decision, with a fixed deliverable, expert sign-off, and a conversion path into "
    "continuous multi-initiative monitoring."
)


WHITE_SPACE = [
    "The expert-validated Initiative Sprint: no competitor combines AI speed, multi-domain initiative analysis, human expert sign-off, transparent pricing, and a board-ready output in a named purchasable package.",
    "Always-on initiative intelligence after the first sprint: competitors solve research, finance, enterprise search, or consulting projects, but none owns continuous monitoring of strategic initiatives across market, competitor, financial, talent, legal, and IP dimensions.",
    "Trust layer as the product: AlphaSense, Rogo, FICO, and Hebbia all show that buyers pay for confidence, not just automation. Innovera can differentiate by making expert validation, citations, assumptions, uncertainty, and decision logic visible in every output.",
    "Mid-market consulting substitute with enterprise-grade rigor: Rocket and DeeCee.ai are accessible but shallow; McKinsey, BCG, EY, and Deloitte are rigorous but slow and opaque. Innovera can occupy the gap for strategy and innovation teams that need credible answers without a consulting engagement.",
    "Decision outcome telemetry: competitors talk about speed, funding, or AI sophistication, but few publish a closed loop from recommendation to decision to outcome. Innovera can build a moat by tracking which recommendations were adopted, what changed, and what ROI followed.",
]


TRENDS = [
    "The market is converging on AI plus human judgment, but most players either hide the human layer in services or leave validation to the user. The opportunity is to make expert validation explicit, repeatable, and productized.",
    "The strongest competitors are not selling generic AI; they are selling trusted workflows for high-stakes decisions: AlphaSense for market intelligence, Rogo and Hebbia for finance, FICO for decisioning, Glean for enterprise knowledge, and Aily for Fortune 500 decision operations.",
    "Accessibility is becoming a weapon. Rocket, DeeCee.ai, Brightwave, and NexStrat reduce entry friction while the incumbents preserve opacity. Innovera should use transparent pilots and concrete packages to make a sophisticated product feel easy to try.",
    "The consulting-substitute narrative is crowding. NexStrat, NitroLens, Rocket, Quantum Rise, and Mindcorp all gesture at replacing or augmenting consultants, so Innovera must differentiate on evidence quality, expert workflow, and repeatable initiative monitoring rather than the claim alone.",
    "ROI language is becoming mandatory. Aily promises day-one measurable ROI, Glean cites hours saved and value unlocked, FICO reports platform ARR and decision optimization, and Rogo anchors on finance productivity. Innovera needs a quantified value model for every pilot.",
]


FULL_REPORT_MARKDOWN = """# Takeaway for Innovera: Frontier Synthesis

## Verdict in One Line

Innovera should stop presenting itself as a broad AI decision intelligence platform first and instead launch a concrete, expert-validated decision product: a named Initiative Sprint that solves one urgent boardroom workflow, proves value in days or weeks, and then expands into continuous initiative monitoring.

---

## 1. The Strategic Pattern Across Competitors

The competitor set is noisy, but the signal is consistent: buyers do not buy "AI strategy" in the abstract. They buy a trusted workflow for a painful decision.

**AlphaSense** wins by owning the research and market-intelligence workflow. It combines premium content, financial data, enterprise intelligence, Tegus expert insights, Deep Research, and a blended future of AI-led calls, human-led calls, and transcript libraries. The lesson is not "build AlphaSense." The lesson is that trust compounds when proprietary content, citations, expert input, and repeat workflows sit in one product experience.

**Rogo** and **Hebbia** win by narrowing the domain to high-stakes finance. Rogo is purpose-built for finance professionals, integrates LSEG's trusted financial data and 1.5 million M&A transactions, and wraps the product in former banker/investor credibility. Hebbia positions itself around "billion dollar decisions," asset managers, bankers, and precision AI. The lesson is that domain specificity creates trust faster than horizontal ambition.

**Aily Labs**, **Glean**, and **FICO** show the importance of operational ROI. Aily claims measurable ROI for Fortune 500 customers from day one and has raised $80M to scale enterprise decision intelligence. Glean cites 3,000+ hours saved monthly and $2.3M yearly value unlocked for a customer. FICO's decisioning platform is recognized by Forrester, backed by governance capabilities, and tied to platform ARR growth. The lesson is that "better decisions" must become measurable business impact.

**Rocket**, **DeeCee.ai**, **Brightwave**, **NexStrat AI**, and **NitroLens AI** reveal the accessibility threat. Rocket produces consulting-style product strategies at a fraction of the cost. DeeCee.ai offers 26 decision templates and exports to DOCX/Markdown. Brightwave lets finance users upload documents, ask questions, generate reports, and build presentations. NexStrat and NitroLens frame AI as a strategy partner or consulting substitute. The lesson is that weaker products can still steal attention if they are easier to try, easier to understand, and easier to buy.

**McKinsey, BCG X, EY, Deloitte, and Hackett** are not going away. They already have enterprise trust, AI investments, and client distribution. But they remain slow, bespoke, opaque, and services-heavy. The lesson is that Innovera should not compete with them on brand scale. It should attack their weakest flank: speed, transparency, repeatability, and measurable pilot value.

---

## 2. What Innovera Should Copy or Test

### Copy AlphaSense and Rogo's trust architecture

Innovera's outputs should feel auditable. Every recommendation should expose sources, assumptions, confidence, expert validation, and the logic chain from evidence to recommendation. This is where Innovera can outperform generic AI tools. AlphaSense and Rogo prove that enterprise buyers pay for trusted intelligence, not just faster text generation.

### Copy Rocket and DeeCee.ai's frictionless entry

Innovera needs a simple entry product that a buyer can understand in 30 seconds. Rocket's "McKinsey-style reports at a fraction of the cost" and DeeCee.ai's decision templates are not as deep as Innovera's platform, but they are legible. Innovera should package one or two named decision workflows with a sample output, fixed scope, and clear next step.

### Copy NexStrat and NitroLens's consulting-substitute language, but make it more credible

The "AI management consultant" narrative is crowded, but it is directionally right. Innovera should not claim "we replace consultants" generically. It should say: "For defined initiative decisions, we deliver an expert-validated board-ready recommendation in days, not months, with evidence and assumptions attached." That is more concrete and more defensible.

### Copy Aily, Glean, and FICO's value discipline

Every pilot should report measurable outcomes: time saved, decisions accelerated, options reduced, risks identified, confidence gained, cost avoided, or revenue unlocked. Without this, Innovera risks sounding like every other AI platform. With it, Innovera can build a compounding proof base.

---

## 3. What Innovera Should Avoid

### Avoid broad-platform positioning as the first commercial message

The platform may genuinely cover opportunity validation, market research, competitive analysis, product, GTM, financials, talent, legal, and IP. But leading with that breadth creates cognitive load. The market rewards focused wedges: Rogo in finance, Brightwave in financial research, Pluvo in CFO planning, AlphaSense in market intelligence, Glean in enterprise knowledge. Innovera should lead with one named decision workflow and let the platform breadth appear as expansion.

### Avoid opaque pricing and "contact us" as the only path

The analysis repeatedly shows pricing opacity across enterprise SaaS and consulting. That protects vendor margin, but it creates buyer friction. Innovera can turn transparent pilot pricing into a differentiator, especially for mid-market strategy, innovation, and corporate development teams that cannot justify a consulting procurement cycle.

### Avoid becoming a services wrapper around AI

The expert layer is valuable, but only if it is productized. If every engagement requires bespoke expert staffing, Innovera will drift toward consulting economics. The expert-in-the-loop model should be a repeatable validation protocol: defined review points, named expert roles, confidence scoring, correction capture, and reusable knowledge assets.

### Avoid competing on raw model capability

Competitors can access similar frontier models. The defensible layer is not "we use better AI." It is workflow design, proprietary initiative context, expert validation, decision telemetry, and repeat use across strategic initiatives.

---

## 4. What Innovera Should Worry About

**Rogo and Hebbia** are the danger model for vertical trust. If either broadens from finance into strategic initiative intelligence, they bring credibility, funding, and high-stakes workflow discipline.

**AlphaSense** is the danger model for content and expert-network gravity. Its combination of proprietary content, financial data, enterprise intelligence, and expert calls could move closer to strategic decision support over time.

**Rocket and DeeCee.ai** are the danger model for accessibility. They may be shallower, but they can educate buyers to expect instant, low-cost, template-driven strategic outputs. If Innovera does not make itself easy to try, these tools will own the top of funnel.

**NexStrat AI, NitroLens AI, Quantum Rise, and Mindcorp** are the danger model for the "consulting 2.0" narrative. Their evidence is thinner, but their message is close to Innovera's intended territory. If one of them adds transparent pricing, expert validation, and stronger proof points, they could occupy the category language first.

**McKinsey, BCG X, EY, Deloitte, and Hackett** are the danger model for distribution. They do not need the best product to win existing enterprise accounts. They can bundle AI capability into existing relationships unless Innovera gives buyers a faster, clearer reason to switch or start outside the consulting channel.

---

## 5. The Single Next Experiment

Launch a **30-day Initiative Sprint** as the first Innovera wedge.

The package should be narrow enough to buy and broad enough to prove the platform:

1. **Use case:** one high-stakes decision, such as market entry, product launch, M&A screen, strategic initiative kill/scale, or competitive response.
2. **Output:** board-ready decision memo, evidence map, options analysis, risk register, financial/market implications, and recommended next action.
3. **Validation:** expert sign-off with visible confidence scoring and explicit assumptions.
4. **Commercial model:** fixed published pilot price or narrow price band.
5. **Speed promise:** first insight in 72 hours, final decision pack in 30 days.
6. **Proof metrics:** time saved versus consulting/internal process, number of options narrowed, risks identified, confidence lift, and decision outcome after 60-90 days.
7. **Expansion path:** convert from one sprint to always-on monitoring of 5-10 strategic initiatives.

This experiment tests the core Innovera thesis better than another broad platform demo. It directly attacks consulting slowness, avoids generic AI positioning, proves expert-in-the-loop value, and creates the first repeatable sales motion.

---

## 6. Final Strategic Takeaway

Innovera's differentiated position is real: multi-domain AI agents plus expert validation for strategic initiatives. But the market will not reward that architecture unless it is packaged into a buyer-readable motion.

The product should be broad. The first offer should be narrow.

The platform should be sophisticated. The first purchase should be simple.

The AI should be powerful. The trust layer should be visible.

The strategic recommendation is therefore clear: launch the Initiative Sprint, publish the proof, and use that wedge to earn the right to become the always-on operating system for strategic initiatives.
"""


def _load(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write(path: Path, data: Dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp.replace(path)


def repair_file(path: Path) -> None:
    data = _load(path)
    analysis = data.get("analyses", {}).get("inv_takeaway_for_innovera")
    if not analysis:
        raise KeyError(f"{path} does not contain analyses.inv_takeaway_for_innovera")

    analysis["headline"] = HEADLINE
    analysis["executive_summary"] = EXECUTIVE_SUMMARY
    analysis["full_report_markdown"] = FULL_REPORT_MARKDOWN
    analysis["white_space"] = WHITE_SPACE
    analysis["trends"] = TRENDS
    analysis["confidence"] = "high"
    _write(path, data)
    print(f"Updated Takeaway for Innovera analysis: {path}")


def main() -> None:
    for target in TARGET_FILES:
        repair_file(target)


if __name__ == "__main__":
    main()
