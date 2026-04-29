"""
Deterministic coverage check for Innovera Commercial Deep Dive questions.
"""

from typing import Any, Dict, List

QUESTION_COVERAGE_MAP = {
    "Q1": ("inv_packaging", "tier names and what each tier includes"),
    "Q2": ("inv_pricing_mechanics", "core pricing unit"),
    "Q3": ("inv_pricing_mechanics", "starting price and typical annual contract value"),
    "Q4": ("inv_packaging", "what costs extra beyond the base package"),
    "Q5": ("inv_pricing_mechanics", "pilot or entry offer structure"),
    "Q6": ("inv_contract_structure", "upgrade and upsell triggers"),
    "Q7": ("inv_packaging", "packaging flexibility"),
    "Q8": ("inv_contract_structure", "contract term length, minimum commitment, renewal mechanics"),
    "Q9": ("inv_pricing_mechanics", "how pricing scales with usage or scope"),
    "Q10": ("inv_gtm_motion", "main revenue driver"),
}

OPAQUE_TYPES = {"consulting_firm", "opaque_enterprise_saas"}
SUBSTANTIVE_MARKERS = (
    "not disclosed",
    "opaque",
    "contact sales",
    "custom",
    "tier",
    "plan",
    "per ",
    "user",
    "usage",
    "subscription",
    "services",
    "project",
    "annual",
    "renew",
    "trial",
    "pilot",
    "minimum",
    "commitment",
    "upgrade",
    "expansion",
    "revenue driver",
)


def run_coverage_check(
    companies: List[str],
    analyses: Dict[str, Dict[str, Any]],
    competitor_profiles: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Return coverage summary and gaps for Q1-Q10."""
    profiles = competitor_profiles or {}
    gaps = []
    for company in companies:
        profile = profiles.get(company, {})
        typology = profile.get("type", "unknown") if isinstance(profile, dict) else getattr(profile, "type", "unknown")
        for qid, (parameter_id, requirement) in QUESTION_COVERAGE_MAP.items():
            report = analyses.get(parameter_id, {}) or {}
            text = _company_report_text(company, report)
            if _is_substantive(text):
                continue
            reason = "typology-driven opacity" if typology in OPAQUE_TYPES else "evidence gap"
            gaps.append({
                "company": company,
                "question": qid,
                "parameter_id": parameter_id,
                "requirement": requirement,
                "reason": reason,
                "competitor_type": typology,
            })
    total = len(companies) * len(QUESTION_COVERAGE_MAP)
    covered = max(0, total - len(gaps))
    return {
        "question_map": QUESTION_COVERAGE_MAP,
        "total_checks": total,
        "covered_checks": covered,
        "gap_count": len(gaps),
        "gaps": gaps,
    }


def typology_distribution(competitor_profiles: Dict[str, Any]) -> Dict[str, int]:
    distribution: Dict[str, int] = {}
    for profile in competitor_profiles.values():
        typology = profile.get("type", "unknown") if isinstance(profile, dict) else getattr(profile, "type", "unknown")
        distribution[typology] = distribution.get(typology, 0) + 1
    return distribution


def _company_report_text(company: str, report: Dict[str, Any]) -> str:
    chunks = [
        report.get("headline", ""),
        report.get("executive_summary", ""),
        report.get("full_report_markdown", ""),
    ]
    for row in report.get("positioning_table", []) or []:
        if str(row.get("company", "")).lower() == company.lower():
            chunks.append(" ".join(str(v) for v in row.values()))
    for ranking in report.get("rankings", []) or []:
        if str(ranking.get("company", "")).lower() == company.lower():
            chunks.append(" ".join(str(v) for v in ranking.values()))
    return " ".join(chunks).lower()


def _is_substantive(text: str) -> bool:
    if not text or len(text.strip()) < 30:
        return False
    return any(marker in text for marker in SUBSTANTIVE_MARKERS)
