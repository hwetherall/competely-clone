"""
Source quality scoring for evidence-grounded research.

This module provides URL scoring to prioritize high-quality sources
and penalize low-signal sources.
"""

import re
import logging
from urllib.parse import urlparse
from typing import Optional, Set, Dict, List

from agents.schemas import SourceScore

logger = logging.getLogger(__name__)


# High-quality source patterns
TIER1_NEWS_DOMAINS: Set[str] = {
    # Major business/tech news
    "reuters.com",
    "bloomberg.com",
    "wsj.com",
    "ft.com",
    "nytimes.com",
    "washingtonpost.com",
    "economist.com",
    "forbes.com",
    "fortune.com",
    "businessinsider.com",
    "cnbc.com",
    # Tech-specific
    "techcrunch.com",
    "wired.com",
    "theverge.com",
    "arstechnica.com",
    "zdnet.com",
    "venturebeat.com",
    "protocol.com",
    "theinformation.com",
    # Industry analysts
    "gartner.com",
    "forrester.com",
    "idc.com",
    "mckinsey.com",
    "bcg.com",
    "bain.com",
    "deloitte.com",
    "pwc.com",
    "accenture.com",
    "kpmg.com",
    "ey.com",
}

# Government and regulatory sources
REGULATORY_DOMAINS: Set[str] = {
    "sec.gov",
    "ftc.gov",
    "justice.gov",
    "treasury.gov",
    "federalreserve.gov",
    "occ.gov",
    "fdic.gov",
    "finra.org",
    "europa.eu",
    "gov.uk",
}

# Low-quality sources to penalize
LOW_QUALITY_DOMAINS: Set[str] = {
    # Forums (valuable but lower signal)
    "reddit.com",
    "quora.com",
    "teamblind.com",
    "glassdoor.com",
    "indeed.com",
    # SEO content farms
    "medium.com",  # Quality varies widely
    "hubspot.com",
    "neilpatel.com",
    "semrush.com",
    "moz.com",
    # Affiliate/comparison sites
    "g2.com",
    "capterra.com",
    "trustradius.com",
    "softwareadvice.com",
    # Generic content
    "wikipedia.org",  # Good for background, but not primary source
    "investopedia.com",
}

# Very low quality - heavy penalty
VERY_LOW_QUALITY_PATTERNS: List[str] = [
    r"\.blogspot\.",
    r"wordpress\.com",
    r"\.wix\.",
    r"\.weebly\.",
    r"ehow\.com",
    r"wikihow\.com",
    r"answers\.com",
]

# Documentation subdomains that indicate official sources
DOCS_SUBDOMAINS: Set[str] = {
    "docs",
    "developer",
    "developers",
    "api",
    "support",
    "help",
    "blog",
    "newsroom",
    "press",
    "ir",  # Investor relations
    "investors",
}


def extract_domain(url: str) -> str:
    """Extract the domain from a URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Remove www. prefix
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""


def extract_base_domain(domain: str) -> str:
    """Extract the base domain (e.g., 'stripe.com' from 'docs.stripe.com')."""
    parts = domain.split(".")
    if len(parts) >= 2:
        # Handle common TLDs
        if parts[-1] in ("com", "org", "net", "io", "co", "ai", "dev", "app"):
            return ".".join(parts[-2:])
        # Handle country TLDs like .co.uk
        if len(parts) >= 3 and parts[-2] in ("co", "com", "org", "gov"):
            return ".".join(parts[-3:])
    return domain


def is_official_domain(url: str, company: str) -> bool:
    """
    Check if a URL is from the company's official domain.
    
    Args:
        url: The URL to check
        company: Company name to match against
        
    Returns:
        True if this appears to be an official company domain
    """
    domain = extract_domain(url)
    base_domain = extract_base_domain(domain)
    
    # Normalize company name for matching
    company_lower = company.lower().replace(" ", "").replace("-", "").replace("_", "")
    
    # Check if company name is in the domain
    domain_normalized = base_domain.replace(".", "").replace("-", "")
    
    # Direct match
    if company_lower in domain_normalized:
        return True
    
    # Common variations
    variations = [
        company_lower,
        company_lower + "inc",
        company_lower + "corp",
        company_lower + "hq",
    ]
    
    for var in variations:
        if var in domain_normalized:
            return True
    
    return False


def get_freshness_boost(url: str) -> float:
    """
    Calculate freshness boost based on URL patterns.
    
    Args:
        url: The URL to analyze
        
    Returns:
        Boost value (0.0 to 0.1)
    """
    # Look for year patterns in URL
    current_year = 2026  # Current year based on context
    
    if f"/{current_year}/" in url or f"-{current_year}" in url:
        return 0.1
    if f"/{current_year - 1}/" in url or f"-{current_year - 1}" in url:
        return 0.05
    if f"/{current_year - 2}/" in url or f"-{current_year - 2}" in url:
        return 0.02
    
    return 0.0


def score_url(url: str, company: str = "") -> SourceScore:
    """
    Score a URL for source quality.
    
    Args:
        url: The URL to score
        company: Optional company name for official domain detection
        
    Returns:
        SourceScore with quality assessment
    """
    domain = extract_domain(url)
    base_domain = extract_base_domain(domain)
    
    penalties: List[str] = []
    base_score = 0.5  # Start at neutral
    tier = "general"
    is_official = False
    
    # Check for official company domain
    if company and is_official_domain(url, company):
        is_official = True
        tier = "official"
        base_score = 0.9
    
    # Check for regulatory/government sources
    elif base_domain in REGULATORY_DOMAINS or domain.endswith(".gov"):
        tier = "regulatory"
        base_score = 0.95
    
    # Check for tier 1 news
    elif base_domain in TIER1_NEWS_DOMAINS:
        tier = "tier1_news"
        base_score = 0.8
    
    # Check for low quality sources
    elif base_domain in LOW_QUALITY_DOMAINS:
        tier = "low_quality"
        base_score = 0.35
        penalties.append(f"low_quality_domain:{base_domain}")
    
    # Check for very low quality patterns
    else:
        for pattern in VERY_LOW_QUALITY_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                tier = "very_low_quality"
                base_score = 0.15
                penalties.append(f"very_low_quality_pattern:{pattern}")
                break
    
    # Boost for documentation subdomains on official sites
    if is_official:
        subdomain = domain.replace(base_domain, "").rstrip(".")
        if subdomain in DOCS_SUBDOMAINS:
            base_score = min(1.0, base_score + 0.05)
    
    # Apply freshness boost
    freshness_boost = get_freshness_boost(url)
    
    # Calculate final score
    final_score = min(1.0, max(0.0, base_score + freshness_boost))
    
    # Additional penalties
    if "pdf" in url.lower():
        # PDFs are often good sources (reports, whitepapers)
        if tier in ("official", "regulatory", "tier1_news"):
            final_score = min(1.0, final_score + 0.05)
    
    # Penalize very long URLs (often SEO spam)
    if len(url) > 200:
        final_score = max(0.1, final_score - 0.1)
        penalties.append("very_long_url")
    
    return SourceScore(
        score=round(final_score, 3),
        domain=domain,
        is_official=is_official,
        tier=tier,
        freshness_boost=freshness_boost,
        penalties=penalties,
    )


def filter_by_min_score(
    urls: List[str],
    min_score: float,
    company: str = ""
) -> List[tuple]:
    """
    Filter URLs by minimum score.
    
    Args:
        urls: List of URLs to filter
        min_score: Minimum score threshold
        company: Company name for official domain detection
        
    Returns:
        List of (url, SourceScore) tuples that meet the threshold
    """
    results = []
    for url in urls:
        score = score_url(url, company)
        if score.score >= min_score:
            results.append((url, score))
    return results


def rank_urls(
    urls: List[str],
    company: str = "",
    ensure_diversity: bool = True,
    min_domains: int = 3,
    max_per_domain: int = 2
) -> List[tuple]:
    """
    Rank URLs by score with optional diversity enforcement.
    
    Args:
        urls: List of URLs to rank
        company: Company name for official domain detection
        ensure_diversity: Whether to enforce domain diversity
        min_domains: Minimum number of distinct domains to include
        max_per_domain: Maximum results from same domain (unless official)
        
    Returns:
        List of (url, SourceScore) tuples, sorted by score
    """
    # Score all URLs
    scored = [(url, score_url(url, company)) for url in urls]
    
    # Sort by score descending
    scored.sort(key=lambda x: (-x[1].score, urls.index(x[0])))
    
    if not ensure_diversity:
        return scored
    
    # Enforce diversity
    result = []
    domain_counts: Dict[str, int] = {}
    domains_seen: Set[str] = set()
    
    for url, score in scored:
        base_domain = extract_base_domain(score.domain)
        
        # Always allow official domains more results
        max_allowed = max_per_domain * 2 if score.is_official else max_per_domain
        
        current_count = domain_counts.get(base_domain, 0)
        
        if current_count < max_allowed:
            result.append((url, score))
            domain_counts[base_domain] = current_count + 1
            domains_seen.add(base_domain)
    
    # If we haven't met diversity requirements, add more from underrepresented domains
    if len(domains_seen) < min_domains:
        for url, score in scored:
            if (url, score) not in result:
                base_domain = extract_base_domain(score.domain)
                if base_domain not in domains_seen:
                    result.append((url, score))
                    domains_seen.add(base_domain)
                    if len(domains_seen) >= min_domains:
                        break
    
    return result


def get_tier_description(tier: str) -> str:
    """Get a human-readable description of a source tier."""
    descriptions = {
        "official": "Official company source",
        "regulatory": "Government/regulatory source",
        "tier1_news": "Major news/analyst source",
        "general": "General web source",
        "low_quality": "Low-signal source (forum, SEO content)",
        "very_low_quality": "Very low quality source",
    }
    return descriptions.get(tier, "Unknown source type")
