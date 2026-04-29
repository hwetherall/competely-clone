"""
Repair the recovered Size Signals synthesis in a V2 run JSON.

The recovery path preserved the Size Signals table but left the narrative
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
    "The size-signal landscape splits into three leagues: scaled incumbents with billions in services revenue, "
    "venture-backed AI platforms with credible ARR and funding momentum, and thin-signal startups that are still "
    "closer to proof-of-market than scaled companies."
)


EXECUTIVE_SUMMARY = (
    "The strongest size signals belong to AlphaSense, Glean, Rogo, Aily Labs, Hebbia, FICO, and the large consulting "
    "incumbents, but those signals mean different things: AlphaSense and Glean show SaaS-scale ARR and valuations, "
    "Rogo and Hebbia show premium AI funding momentum, Aily Labs shows a concentrated enterprise contract model, "
    "and EY/BCG/Deloitte/McKinsey show massive distribution without SaaS-like transparency. The middle of the market "
    "is a cohort of early AI strategy and research challengers with $5M-$21M funding rounds, waitlists, small teams, "
    "or founder-credibility signals rather than durable revenue evidence. For Innovera, the opening is not to out-scale "
    "the incumbents immediately, but to look more commercially legible than the startups and more focused than the "
    "consultancies: publish a credible traction narrative, show usage/customer proof, and anchor the company against "
    "the AI-native challengers rather than the Big Four balance sheets."
)


WHITE_SPACE = [
    "Transparent traction scoreboard for AI strategy buyers: most early competitors disclose either funding or anecdotes, not a buyer-readable view of ARR, customer count, active usage, time-to-value, and retention. Innovera can create trust by publishing a simple evidence-backed momentum dashboard before the category standardizes.",
    "Mid-market decision intelligence between $5M seed startups and Big Four scale: the field jumps from tiny or opaque AI-native challengers to $14B-$50B consulting incumbents. A credible, focused provider with clear customer proof can own the gap for buyers who want more trust than a seed-stage tool and more speed than a consulting firm.",
    "Proof-of-usage as a differentiator: AlphaSense, Rogo, Rocket, and Glean have the strongest adoption signals, while many peers rely on funding announcements or founder credentials. Innovera can compete by documenting usage intensity, repeat workflows, and decision outcomes rather than only logos.",
    "Investor-backed but commercially disciplined positioning: many AI-native firms advertise fresh capital but little revenue quality. A bootstrapped or capital-efficient Innovera story with named use cases and gross-margin discipline would stand out against the funding-heavy narrative.",
    "Consulting-firm displacement wedge for companies below enterprise scale: Big Four and MBB players have immense revenue and headcount but weak productized access. Innovera can target teams too small or too impatient for those firms with a measurable, packaged decision-intelligence offer.",
]


TRENDS = [
    "ARR and usage signals are replacing generic funding as the strongest proof of scale: AlphaSense's $500M+ ARR, Glean's $100M-$200M+ ARR signals, Rogo's 25,000+ daily active users, and Rocket's reported $4.5M ARR shortly after launch are more strategically useful than headline funding alone.",
    "The AI-native cohort is bifurcating into premium enterprise platforms and narrow wedge products: AlphaSense, Glean, Rogo, Hebbia, and Aily Labs are raising large rounds and selling into enterprise, while Rocket, Brightwave, Pluvo, Gravity, NitroLens, and NexStrat are still proving repeatability through smaller teams, seed rounds, or founder-led credibility.",
    "Large consultancies have scale but not size-signal clarity for the specific AI decision-intelligence offer: EY, BCG, Deloitte, McKinsey, and Hackett disclose revenue or headcount at the firm level, yet those numbers blur the actual traction of their AI-native decision products.",
    "Customer-count and penetration metrics are becoming the most persuasive adoption proof: AlphaSense's 7,000+ customers and S&P penetration, FICO's thousands of businesses in 80+ countries, Rocket's 10K customers, and Glean's Fortune 500 traction are easier for buyers to interpret than valuation marks.",
    "Several 'Consulting 2.0' challengers remain credibility-led rather than traction-led: NexStrat, NitroLens, Mindcorp, DeeCee.ai, and Quantum Rise lean on founder background, waitlists, or broad market narratives because public revenue, customer, and retention signals are still thin.",
]


FULL_REPORT_MARKDOWN = """# Size Signals: State of the Nation

## Verdict in One Line

This market is not one competitive set by scale. It is three different scale games running at once: billion-dollar consulting incumbents with productized AI ambitions, AI-native enterprise platforms with meaningful ARR and venture momentum, and early challengers whose public proof is still mostly funding, founder pedigree, or anecdotal customer traction.

---

## 1. The Scale Map

The clearest leaders on raw scale are not the AI startups. They are the consulting and analytics incumbents: EY reports US$53.2B in FY2025 revenue, BCG reports $14.4B with 22 consecutive years of growth, McKinsey still has roughly 60,000 employees even after reported headcount pressure, Deloitte has global scale plus explicit venture commitments, FICO has a mature platform ARR base, and The Hackett Group has quarterly revenue visibility in the $70M+ range. These companies can fund AI capability, absorb enterprise procurement complexity, and cross-sell through existing client relationships. Their weakness is that firm-level scale does not equal product-level traction. A buyer can see that EY or BCG is huge; they cannot easily see how much market pull exists for the specific AI decision-intelligence product.

The second league is where the most relevant AI-native competition sits. AlphaSense is the benchmark: more than $500M in ARR, 7,000+ customers, 70% S&P 500 penetration, 90% S&P 100 penetration, and a valuation that moved from $1.8B to $4B while also acquiring Tegus for $930M. That is the most complete size signal in the field because it combines revenue, customers, enterprise penetration, valuation, and M&A. Glean is similarly credible, with $150M Series F funding at a $7.2B valuation, $100M+ ARR after Series E, more recent $200M+ ARR signals, Fortune 500 traction, and 10,000+ Glean:GO participants. Rogo is smaller but highly strategic: more than $165M raised, a $750M valuation, 25+ customer firms, and 25,000+ daily active users. Hebbia has $130M Series B funding at roughly a $700M valuation, 15x revenue growth over 18 months, $13M profitable revenue, and a remarkable $7M ARR added in 24 hours. Aily Labs adds a different model: $101M total funding, $80M latest round, $28.6M ARR mid-2025, 500% customer growth, thousands of users, and roughly 260 employees.

The third league is the early and thin-signal cohort. Brightwave has useful funding momentum: $6M seed, $15M Series A, and $21M raised in seven months. Gravity/Orion has $10M total funding, including a $7M seed. Pluvo has a $5M seed and investor-customer overlap. Rocket has a $15M seed, a 50-person team, reported $4.5M ARR within 16 weeks, and 10K customers, which is one of the strongest early commercial velocity signals. Quantum Rise has a $15M seed and an 8,355-follower LinkedIn footprint. NexStrat, NitroLens, Mindcorp, and DeeCee.ai are materially weaker on hard metrics: their public evidence emphasizes founder backgrounds, waitlists, product iterations, stealth revenue claims, or broad market narratives rather than revenue, retention, or customer-scale proof.

---

## 2. What Counts as a Strong Size Signal

Funding alone is not enough. A $100M round can indicate market belief, but it does not tell a buyer whether the product is becoming embedded in workflows. The strongest signals in this data set combine at least two of four elements:

1. Revenue quality: AlphaSense's $500M+ ARR, Glean's $100M-$200M+ ARR signals, FICO's $263.6M platform ARR, and Rocket's reported $4.5M ARR shortly after launch are more useful than funding announcements because they imply recurring willingness to pay.
2. Customer adoption: AlphaSense's 7,000+ customers and S&P penetration, FICO's thousands of businesses across 80+ countries, Rocket's 10K customers, and Rogo's 25,000+ daily active users show real usage surface area.
3. Capital momentum: Rogo's $75M Series C, Hebbia's $130M Series B, Glean's $150M Series F, Aily's $80M round, and Brightwave's $21M in seven months indicate investor conviction and runway.
4. Organizational capacity: Aily's 260 employees, Rocket's 50-person team, and McKinsey's 60,000-employee base tell different stories about delivery capacity, but only matter when paired with evidence of product demand.

By this standard, AlphaSense and Glean are the most complete AI-native scale stories. Rogo and Hebbia are high-conviction enterprise AI challengers with strong momentum but less public revenue detail. Aily is potentially significant but concentrated: the evidence points to large enterprise contracts and rapid user/customer growth rather than broad-market penetration. Rocket is the most interesting early outlier because it combines low entry pricing, reported ARR velocity, a 50-person team, and a large customer count. Most other startups are still evidence-thin.

---

## 3. Incumbents vs AI-Native Challengers

The incumbents win on balance-sheet credibility. EY, BCG, Deloitte, McKinsey, FICO, and Hackett can survive long sales cycles and reassure conservative buyers. But their size signals are often too broad. EY's $53.2B revenue tells us the firm is massive, not whether EY.ai has repeatable market traction. BCG's $14.4B revenue and 25% AI revenue-share signal are powerful, but they do not reveal whether BCG X behaves like a scalable product business. McKinsey's 25,000 AI agents and 60,000 employees show internal transformation, while reported headcount decline and flatlined five-year growth suggest pressure on the old model. Deloitte's public facts and venture commitment show investment capacity, not product-market proof.

The AI-native challengers win on signal specificity. AlphaSense, Glean, Rogo, Hebbia, Aily, and Rocket expose numbers that map more directly to product adoption: ARR, active users, customers, valuation, funding, and usage. That makes them more useful benchmarks for Innovera than the consulting firms. Innovera does not need to match EY's revenue to be credible. It needs to show the kind of product-level traction buyers can understand: customer count, repeat usage, time-to-first-value, renewal behavior, and decision outcomes.

---

## 4. Winners, Watchlist, and Weak Signals

**Most complete size signal: AlphaSense.** It has the full stack: ARR, customers, enterprise penetration, valuation, and M&A. It is the standard for what a scaled AI intelligence platform looks like.

**Most valuable enterprise AI momentum: Glean.** Its $7.2B valuation and $100M-$200M+ ARR signals position it as a serious enterprise AI platform, even if its use case is broader workplace AI rather than strategy-specific decision intelligence.

**Most strategically relevant challenger: Rogo.** Its $165M+ funding, $750M valuation, 25+ customer firms, and 25,000+ daily active users show strong traction in a high-value vertical. It is narrower than Innovera, but its adoption signals are sharper.

**Most compelling early velocity: Rocket.** A $15M seed, 50-person team, reported $4.5M ARR in 16 weeks, and 10K customers suggest strong demand at the accessible end of the market. It may lack depth, but the size signals say the wedge is working.

**Most concentrated enterprise model: Aily Labs.** $101M total funding, $28.6M ARR, 500% customer growth, thousands of active users, and 260 employees suggest genuine enterprise traction. But the model appears concentrated around large deployments rather than broad accessibility.

**Most evidence-thin challengers: DeeCee.ai, NitroLens AI, Mindcorp, NexStrat AI.** Each has some credibility marker: founder background, waitlist activity, stealth revenue claims, product iterations, or templates. None yet shows the combination of revenue, customers, funding, and usage needed to be considered scaled.

---

## 5. Implications for Innovera

The size-signal story should shape how Innovera positions itself. The wrong benchmark is Big Four revenue. No buyer expects a challenger to look like EY or Deloitte. The right benchmark is legibility: can Innovera show enough traction evidence to look more credible than the thin-signal startups, while staying more focused and accessible than the incumbents?

That means Innovera should publish a traction narrative that is deliberately buyer-readable. The minimum credible scoreboard should include: number of active customers or pilots, number of completed initiative analyses, median time-to-first-insight, repeat usage or renewal signals, average workflow depth, expert-validation volume, and one or two quantified business outcomes. If the company cannot publish revenue, it can still publish usage and proof-of-value. That would immediately differentiate it from NexStrat, NitroLens, Mindcorp, DeeCee.ai, Quantum Rise, and many opaque AI-native players.

The biggest opportunity is to make trust feel measurable. The market is crowded with funding announcements and consulting pedigree. It is less crowded with operational proof. If Innovera can show that its digital twins move from question to validated decision faster than consulting firms and with more confidence than AI-only tools, it does not need to win the scale argument on headcount or funding. It can win it on momentum, repeatability, and evidence quality.
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
    analysis = data.get("analyses", {}).get("inv_size_signals")
    if not analysis:
        raise KeyError(f"{path} does not contain analyses.inv_size_signals")

    analysis["headline"] = HEADLINE
    analysis["executive_summary"] = EXECUTIVE_SUMMARY
    analysis["full_report_markdown"] = FULL_REPORT_MARKDOWN
    analysis["white_space"] = WHITE_SPACE
    analysis["trends"] = TRENDS
    analysis["confidence"] = "medium"
    _write(path, data)
    print(f"Updated Size Signals analysis: {path}")


def main() -> None:
    for target in TARGET_FILES:
        repair_file(target)


if __name__ == "__main__":
    main()
