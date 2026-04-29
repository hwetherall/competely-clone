"""
Curated benchmark dataset for consulting-firm engagement economics.

Used by the gather agent to inject anchoring data into commercial context for
competitors with `consulting_firm` typology. The synthesizer then has
defensible ranges to triangulate against when no published price exists,
producing `inferred` numeric claims rather than collapsing to `unknown`.

This file is hand-curated. Refresh cadence: quarterly.
Owner: synthesis-quality workstream.
Last reviewed: 2026-04-29.

Numeric ranges are stored as (low, high) tuples in USD, except where unit
is specified by the field name (weeks, headcount). Sources document where
each range is anchored — they are not guarantees that an automated scraper
verified the value at runtime.
"""

from typing import Dict, Any


CONSULTING_BENCHMARKS: Dict[str, Dict[str, Any]] = {
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
        "sources": [
            "GSA Schedule contract awards",
            "EU public procurement disclosures",
        ],
    },
    "specialist": {
        # Hackett, ZS, Oliver Wyman, etc.
        "blended_day_rate_usd": (5_000, 12_000),
        "typical_team_size": (2, 5),
        "typical_engagement_weeks": (4, 12),
    },
}


# Map common firm names -> benchmark bucket. Used by the gather agent to
# pick the right benchmark set when a competitor profile is classified
# as `consulting_firm` but doesn't carry a tier label.
FIRM_TO_BUCKET: Dict[str, str] = {
    "mckinsey": "mbb",
    "mckinsey & company": "mbb",
    "bcg": "mbb",
    "bcg x": "mbb",
    "boston consulting group": "mbb",
    "bain": "mbb",
    "bain & company": "mbb",
    "ey": "big_four",
    "ernst & young": "big_four",
    "deloitte": "big_four",
    "kpmg": "big_four",
    "pwc": "big_four",
    "pricewaterhousecoopers": "big_four",
    "hackett": "specialist",
    "the hackett group": "specialist",
    "zs": "specialist",
    "zs associates": "specialist",
    "oliver wyman": "specialist",
}


def benchmark_for_firm(firm_name: str, default_bucket: str = "mbb") -> Dict[str, Any]:
    """Return the benchmark dict for a named firm.

    Falls back to `default_bucket` (MBB by default) when the firm isn't in
    FIRM_TO_BUCKET — most unknown consulting firms cluster nearer MBB rates
    than Big Four boutiques, but callers can override.
    """
    key = (firm_name or "").strip().lower()
    bucket = FIRM_TO_BUCKET.get(key, default_bucket)
    return {"bucket": bucket, **CONSULTING_BENCHMARKS.get(bucket, {})}
