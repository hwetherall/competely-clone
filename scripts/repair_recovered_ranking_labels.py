"""
Replace generic recovered-analysis ranking labels with meaningful labels.

This keeps the HTML cards from showing fallback labels like "Stronger saved
signal" for the repaired Size Signals, Speed-to-Market, and Takeaway sections.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


TARGET_FILES = [
    Path("data/results/v2_run_20260428_173648.json"),
    Path("data/results/checkpoint_v2_run_20260428_173648_recovery.json"),
]


LABELS = {
    "inv_size_signals": {
        "AlphaSense": "Scaled Market Intelligence Leader",
        "Aily Labs": "Enterprise Decision AI Scaler",
        "Rogo": "Finance AI Momentum Leader",
        "Gravity (Orion)": "Early Analytics Wedge",
        "Hebbia": "High-Value Finance AI Challenger",
        "Pluvo": "Early CFO Planning Wedge",
        "The Hackett Group": "Public Consulting Benchmark",
        "NexStrat AI": "Founder-Credibility Challenger",
        "NitroLens AI": "Pre-Launch Strategy AI",
        "Mindcorp": "Stealth Enterprise AI Claim",
        "EY (Ernst & Young)": "Big Four AI Scale",
        "Brightwave": "Finance Research Upstart",
        "Quantum Rise": "Consulting 2.0 Seed Player",
        "McKinsey & Company": "Incumbent Consulting Giant",
        "BCG X (Boston Consulting Group)": "Scaled AI Consulting Builder",
        "DeeCee.ai": "Thin-Signal Template Tool",
        "Rocket": "Accessible Strategy Tool",
        "Deloitte": "Big Four AI Distributor",
        "Glean": "Enterprise Work AI Scaler",
        "FICO": "Mature Decisioning Platform",
    },
    "inv_speed_to_market": {
        "AlphaSense": "Long-Cycle Category Builder",
        "Aily Labs": "Bootstrapped Enterprise Scaler",
        "Rogo": "Fastest Finance Wedge",
        "Gravity (Orion)": "Google Cloud Analytics Wedge",
        "Hebbia": "Premium Finance AI Scaler",
        "Pluvo": "CFO Planning Wedge",
        "The Hackett Group": "Incumbent Benchmark Provider",
        "NexStrat AI": "Consulting 2.0 Stealth Builder",
        "NitroLens AI": "Pre-Launch Strategy Sprint",
        "Mindcorp": "Stealth Cognition Launch",
        "EY (Ernst & Young)": "Big Four Product Rollout",
        "Brightwave": "Fast Finance Research Launch",
        "Quantum Rise": "AI Transformation Wedge",
        "McKinsey & Company": "Legacy AI Adoption",
        "BCG X (Boston Consulting Group)": "Consulting Tech-Build Arm",
        "DeeCee.ai": "Template-First Decision Tool",
        "Rocket": "Accessibility-Led Launch",
        "Deloitte": "Incumbent Venture/AI Rollout",
        "Glean": "Enterprise Search-to-AI Scaler",
        "FICO": "Long-Cycle Decisioning Incumbent",
    },
    "inv_takeaway_for_innovera": {
        "AlphaSense": "Trust and Content Architecture",
        "Aily Labs": "ROI-Led Enterprise Model",
        "Rogo": "Domain-Trust Architecture",
        "Gravity (Orion)": "Embedded Analyst Pattern",
        "Hebbia": "Precision Workflow Model",
        "Pluvo": "Mid-Market Finance Wedge",
        "The Hackett Group": "Benchmark-Plus-AI Incumbent",
        "NexStrat AI": "Consulting-Substitute Threat",
        "NitroLens AI": "Strategy-Sprint Signal",
        "Mindcorp": "Human+AI Cognition Claim",
        "EY (Ernst & Young)": "Incumbent AI Platform Push",
        "Brightwave": "Document-to-Insight Workflow",
        "Quantum Rise": "Consulting 2.0 Narrative",
        "McKinsey & Company": "Distribution and Governance Threat",
        "BCG X (Boston Consulting Group)": "Build-and-Transform Threat",
        "DeeCee.ai": "Template Accessibility Model",
        "Rocket": "Low-Friction Strategy Wedge",
        "Deloitte": "Incumbent Account Access",
        "Glean": "ROI/Partner Ecosystem Model",
        "FICO": "Governance and Decisioning Benchmark",
    },
}


def _load(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write(path: Path, data: Dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp.replace(path)


def _apply_labels(analysis: Dict[str, Any], labels: Dict[str, str]) -> int:
    changed = 0
    for ranking in analysis.get("rankings", []) or []:
        company = ranking.get("company")
        if company in labels:
            ranking["label"] = labels[company]
            changed += 1

    for row in analysis.get("positioning_table", []) or []:
        company = row.get("company")
        if company in labels:
            row["position"] = labels[company]
            changed += 1
    return changed


def repair_file(path: Path) -> None:
    data = _load(path)
    total_changed = 0
    analyses = data.get("analyses", {})
    for parameter_id, labels in LABELS.items():
        analysis = analyses.get(parameter_id)
        if not analysis:
            continue
        total_changed += _apply_labels(analysis, labels)
    _write(path, data)
    print(f"Updated {total_changed} recovered labels: {path}")


def main() -> None:
    for target in TARGET_FILES:
        repair_file(target)


if __name__ == "__main__":
    main()
