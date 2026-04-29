"""
Repair the recovered Speed-to-Market Playbook synthesis in a V2 run JSON.

The recovery path preserved the Speed-to-Market table but left the narrative
sections as a checkpoint fallback. This script replaces the narrative fields
with a synthesized analysis grounded in the saved positioning table.
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
    "The fastest go-to-market paths in this landscape do not come from broad platform launches; "
    "they come from narrow wedges, founder-market fit, and a proof loop that converts early users into "
    "capital, credibility, and repeatable enterprise pilots."
)


EXECUTIVE_SUMMARY = (
    "Speed-to-market patterns split into four archetypes: long-cycle category builders like AlphaSense and FICO, "
    "enterprise AI scalers like Glean, Rogo, Hebbia, and Aily Labs, focused wedge startups like Brightwave, Pluvo, "
    "Gravity/Orion, Rocket, and Quantum Rise, and consulting incumbents that move quickly only through existing client "
    "distribution. The strongest modern playbooks are Rocket's reported launch-to-ARR velocity, Rogo's 2022 founding to "
    "$165M+ funding and 25,000+ daily users, Brightwave's four-month customer ramp to $120B+ AUM coverage, Aily's eight-week "
    "first product and three-year bootstrap, and Glean's three-year ARR scale with 100+ connectors. For Innovera, the lesson "
    "is to avoid launching as a broad decision-intelligence platform; the faster path is a named, repeatable boardroom "
    "workflow with a measurable pilot, visible time-to-first-insight, and a narrow customer wedge that can later expand into "
    "the full multi-agent platform."
)


WHITE_SPACE = [
    "A named boardroom workflow wedge: competitors either launch broad AI platforms or narrow vertical tools; there is room for an Innovera package around one urgent executive workflow such as market-entry memo, initiative kill/scale decision, M&A screen, or board strategy pack.",
    "Time-to-first-insight as the headline launch metric: Aily's eight-week first product, Rogo's sub-five-month path to seven-digit ARR, Rocket's 16-week ARR signal, and Brightwave's four-month customer ramp show buyers respond to speed; Innovera should publish a measurable first-insight clock.",
    "Pilot-to-proof launch system for mid-market strategy teams: NexStrat, NitroLens, and Brightwave show that structured pilots work, but none owns a rigorous, expert-validated pilot format for strategic decisions with before/after success metrics.",
    "Founder-led credibility converted into repeatable GTM assets: many challengers lean on ex-consultant or domain-founder background; Innovera can turn expert credibility into public templates, benchmark reports, and reusable decision playbooks instead of leaving it as biography.",
    "Portfolio-level expansion after a narrow wedge: most fast movers start narrow and stay narrow; Innovera can use one workflow as the land motion and then expand into continuous monitoring of multiple strategic initiatives.",
]


TRENDS = [
    "The fastest AI-native players sequence wedge first, platform second: Rogo starts in finance, Brightwave in financial research, Gravity/Orion in Looker/Google Cloud analytics, Pluvo in CFO planning, and Rocket in prompt-to-report strategy outputs.",
    "Capital is following proof loops rather than pure product vision: Rogo's rapid Seed-to-Series C path, Hebbia's Series A-to-Series B jump, Glean's ARR acceleration, and Brightwave's $21M raised in seven months all pair funding with visible adoption or workflow traction.",
    "Consulting incumbents have distribution speed but product-launch drag: EY, Deloitte, BCG X, McKinsey, and Hackett can push AI into existing accounts quickly, but their market-facing launch motions remain relationship-led, opaque, and slower to self-serve.",
    "Founder-market fit is a recurring accelerator: AlphaSense emerged from investment-banking research pain, Rogo from finance workflows, Aily from pharma/enterprise decision bottlenecks, NexStrat and NitroLens from consulting experience, and Rocket from startup/product-building friction.",
    "The new launch unit is a proof-of-value sprint, not a generic demo: NexStrat's POC, NitroLens's 2-3 session Strategy Sprint, Brightwave's immediate trial, and Rogo's trial conversion evidence show that the launch motion is compressing from enterprise sales pitch to measurable pilot.",
]


FULL_REPORT_MARKDOWN = """# Speed-to-Market Playbook: State of the Nation

## Verdict in One Line

The fastest companies in this set did not win by launching everything at once. They found a narrow, high-pain wedge, wrapped it in founder credibility or domain expertise, proved value with early users, and then used funding or enterprise logos to expand the surface area.

---

## 1. The Four Speed Archetypes

The first archetype is the **long-cycle category builder**. AlphaSense and FICO are the clearest examples. AlphaSense launched in 2011 from a founder's investment-banking frustration with PDF-heavy market research and spent years compounding content, workflow, and enterprise trust before becoming a $500M+ ARR market intelligence platform. FICO is the extreme incumbent case: founded in 1956 with $400 from each founder, first bank-card scoring system in 1970, broad bureau availability by 1991, and mortgage adoption in 1995. These are not models Innovera can copy for speed, but they show what compounding category infrastructure looks like when it works.

The second archetype is the **enterprise AI scaler**. Glean, Rogo, Hebbia, and Aily Labs all show a compressed version of category building. Glean raised $100M Series C in 2022, built around enterprise search and workplace knowledge, then expanded into Glean Chat and low-code/no-code generative AI with 100+ connectors and a reported three-year path to $100M ARR. Rogo was founded in 2022, raised seed in early 2024, raised Series A in October 2024, then reached a $75M Series C with more than $165M total funding, more than 25,000 daily users, and a sub-five-month path to seven-digit ARR. Hebbia founded in 2020 and moved from $30M Series A to $130M Series B and a $700M valuation while processing more than one billion pages. Aily Labs founded in 2020, built its first product in eight weeks, bootstrapped for three years, then scaled from Series A to an $80M Series B while growing from 3 to 300+ employees.

The third archetype is the **focused wedge startup**. Brightwave launched an AI financial research assistant, secured $6M seed funding, reached a customer base managing more than $120B AUM in four months, then raised $15M Series A and $21M total within seven months. Pluvo founded in 2024 and raised $5M around an AI-native finance planning wedge for CFOs and growth-stage businesses. Gravity/Orion tied its launch to Google Cloud, Looker, Gemini, and the specific use case of autonomous customer analytics. Quantum Rise entered through AI transformation and automation services, with a $15M seed and early customer signal around dunnhumby. Rocket is the most explicit speed case: a low-friction prompt-to-report strategy product with reported $15M seed funding, hundreds of G2 reviews, and evidence from the Size Signals section of $4.5M ARR in 16 weeks.

The fourth archetype is the **incumbent distribution play**. EY, Deloitte, McKinsey, BCG X, and Hackett can move AI into the market quickly because they already own enterprise relationships. EY can unveil Competitive Edge or Studio+ into an existing client base. Deloitte can launch Deloitte Ventures and route AI offers through consulting teams. BCG X can stand up a tech-build division on top of the BCG brand. McKinsey can scale Lilli and other AI tools internally. But these are not fast self-serve launches. They are relationship-led rollouts that depend on existing accounts, partner access, and long procurement paths.

---

## 2. What Actually Accelerates Speed

Across the table, four acceleration levers recur.

**Founder-market fit.** AlphaSense came from the founder's lived pain in investment banking research. Rogo is built around finance workflows by founders close to the domain. Aily Labs emerged from enterprise decision bottlenecks experienced in pharma and large-company environments. NexStrat and NitroLens use former consultant credibility. Rocket uses startup/product-builder friction. The lesson is that speed improves when the first use case is not abstract.

**A narrow first wedge.** The fastest modern players do not start with "decision intelligence for everyone." They start with finance research, CFO planning, Looker analytics, market intelligence search, enterprise knowledge search, or strategy report generation. This matters for Innovera because the platform is broad by architecture. A broad architecture still needs a narrow commercial entry point.

**Proof before platform expansion.** Brightwave's four-month customer ramp, Rogo's daily users and fast ARR milestone, Glean's connector expansion and ARR path, and Aily's eight-week first product all show the same pattern: prove one repeatable workflow, then raise capital or expand scope. The strongest launches create a visible proof loop early enough that sales, fundraising, and recruiting reinforce each other.

**Pilot mechanics.** NexStrat's product-development-in-stealth with early users, NitroLens's 2-3 session Strategy Sprint, Brightwave's immediate trial, and Rogo's documented trial conversion lift all point to a market where the launch motion is no longer a generic demo. It is a scoped proof-of-value sprint that produces a tangible artifact and a conversion conversation.

---

## 3. Winners, Watchlist, and Laggards

**Best modern speed playbook: Rogo.** Founded in 2022, moving through seed, Series A, and Series C in rapid sequence, with more than $165M raised, more than 25,000 daily users, and sub-five-month seven-digit ARR, Rogo is the strongest example of domain wedge plus enterprise pull.

**Best enterprise expansion playbook: Glean.** Glean's speed comes from connectors, deployment infrastructure, and expansion from search into chat and custom generative AI. The three-year path to $100M ARR and 100+ connectors shows how infrastructure breadth can become GTM velocity once the first enterprise wedge works.

**Best first-product velocity: Aily Labs.** An eight-week first product, three years bootstrapped, then Series A and Series B momentum show a disciplined build-before-scale pattern. The risk is that enterprise complexity may slow repeatability, but the initial speed signal is strong.

**Best early wedge proof: Brightwave.** Four months to a customer base spanning $120B+ AUM, 4x revenue growth, and $21M raised in seven months show unusually fast early financial-research traction.

**Best accessibility-led launch: Rocket.** Rocket's prompt-to-report workflow is less deep than enterprise competitors, but its speed, low-friction entry, customer count, and reported early ARR make it dangerous at the bottom of the market.

**Watchlist: Pluvo, Gravity/Orion, Quantum Rise, NexStrat.** Each has a plausible wedge, but the evidence is still early. Pluvo has a CFO/finance wedge and $5M seed. Gravity has a Google Cloud/Looker wedge. Quantum Rise has AI transformation plus acquisition-led capability. NexStrat has consulting credibility and a year-plus development cycle with early users.

**Laggards by speed-to-market clarity: DeeCee.ai, Mindcorp, NitroLens.** They may have useful products, but their public speed signals are too thin: templates, stealth emergence, waitlists, founder claims, or small social proof do not yet show repeatable market velocity.

---

## 4. Implications for Innovera

Innovera's risk is not product breadth. It is launch breadth. The platform's multi-agent architecture can support many use cases, but the market evidence says buyers respond faster to one named workflow with a concrete output than to a broad "AI decision intelligence platform" claim.

The practical playbook is to pick a single high-urgency wedge and make the launch measurable. Good candidates are: a market-entry board memo, an M&A target screen, a new-product launch decision, a strategic initiative kill/scale review, or an investor-ready competitive landscape. The wedge should have a promised time-to-first-insight, a fixed pilot package, and a sample output buyers can understand before talking to sales.

The second requirement is to convert expert credibility into assets. NexStrat and NitroLens lean on ex-consultant biographies; Innovera should go further by publishing reusable playbooks, benchmark reports, anonymized before/after examples, and a visible expert-validation method. That turns credibility from a founder story into a GTM machine.

The third requirement is expansion design. The wedge should not be a dead-end service package. It should land the customer inside the broader Innovera operating model: one initiative becomes five monitored initiatives, then a portfolio-level decision layer, then recurring strategic intelligence. That is how Innovera can copy the speed of wedge startups without giving up the breadth of its platform.
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
    analysis = data.get("analyses", {}).get("inv_speed_to_market")
    if not analysis:
        raise KeyError(f"{path} does not contain analyses.inv_speed_to_market")

    analysis["headline"] = HEADLINE
    analysis["executive_summary"] = EXECUTIVE_SUMMARY
    analysis["full_report_markdown"] = FULL_REPORT_MARKDOWN
    analysis["white_space"] = WHITE_SPACE
    analysis["trends"] = TRENDS
    analysis["confidence"] = "medium"
    _write(path, data)
    print(f"Updated Speed-to-Market analysis: {path}")


def main() -> None:
    for target in TARGET_FILES:
        repair_file(target)


if __name__ == "__main__":
    main()
