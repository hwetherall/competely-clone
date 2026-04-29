"""
Structured commercial extraction for Innovera Commercial Deep Dive.

Runs once per competitor after profiling and before per-cell research.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from agents.firecrawl_client import FirecrawlClient
from agents.v2_schemas import CommercialExtract, CompetitorProfile

logger = logging.getLogger(__name__)

COMMERCIAL_PARAMETER_IDS = {"inv_packaging", "inv_pricing_mechanics", "inv_contract_structure", "inv_gtm_motion"}

COMMERCIAL_EXTRACT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "tiers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "starting_price": {"type": "string"},
                    "billing_unit": {"type": "string"},
                    "included_features": {"type": "array", "items": {"type": "string"}},
                    "limits": {"type": "string"},
                    "is_custom_or_enterprise": {"type": "boolean"},
                },
            },
        },
        "add_ons": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "price": {"type": "string"},
                    "type": {"type": "string"},
                },
            },
        },
        "packaging_flexibility": {"type": "string"},
        "primary_pricing_unit": {
            "type": "string",
            "enum": ["per_user", "per_project", "per_usage", "per_outcome", "flat_platform", "hybrid", "opaque"],
        },
        "starting_price_published": {"type": "string"},
        "free_trial": {"type": "string"},
        "scaling_model": {"type": "string"},
        "contract_term_options": {"type": "array", "items": {"type": "string"}},
        "minimum_commitment": {"type": "string"},
        "renewal_mechanics": {"type": "string"},
        "pricing_disclosure": {
            "type": "string",
            "enum": ["fully_published", "partial", "opaque"],
        },
        "extracted_from_urls": {"type": "array", "items": {"type": "string"}},
    },
}

COMMERCIAL_EXTRACT_PROMPT = """Extract commercial packaging, pricing, and contract data from these official pages.

Rules:
- Treat the company's own pages as the source of truth for published facts.
- If a price, term, trial, or limit is not stated, write "not disclosed" rather than guessing.
- Preserve "Contact sales" and opaque-pricing language as evidence.
- Include only information found on the supplied URLs.
"""


class CommercialExtractor:
    """Run Firecrawl Extract for commercial pages selected by the profiler."""

    def __init__(self, firecrawl_client: Optional[FirecrawlClient] = None):
        self.firecrawl_client = firecrawl_client or FirecrawlClient()

    async def extract_for_companies(
        self,
        profiles: Dict[str, CompetitorProfile],
        max_concurrent: int = 5,
    ) -> Dict[str, CommercialExtract]:
        semaphore = asyncio.Semaphore(max_concurrent)

        async def bounded(company: str, profile: CompetitorProfile) -> tuple[str, CommercialExtract]:
            async with semaphore:
                return company, await self.extract_for_profile(profile)

        tasks = [bounded(company, profile) for company, profile in profiles.items()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        extracts: Dict[str, CommercialExtract] = {}
        for result in results:
            if isinstance(result, Exception):
                logger.warning("Commercial extract task failed: %s", result)
                continue
            company, extract = result
            extracts[company] = extract
        return extracts

    async def extract_for_profile(self, profile: CompetitorProfile) -> CommercialExtract:
        company = profile.competitor
        if profile.type == "consulting_firm":
            return self._opaque_extract(
                company,
                "Consulting firms usually sell project-based work through bespoke statements of work; detailed public package/pricing scrape skipped.",
            )
        urls = self._urls_for_profile(profile)
        if not urls:
            return self._opaque_extract(
                company,
                "No pricing, package, terms, or legal URLs were found during profiling.",
            )
        try:
            result = await self.firecrawl_client.extract(
                urls=urls,
                schema=COMMERCIAL_EXTRACT_SCHEMA,
                prompt=COMMERCIAL_EXTRACT_PROMPT,
                use_cache=True,
                cache_ttl_days=30,
            )
            data = result.get("data") or {}
            if not isinstance(data, dict):
                data = {}
            extracted_urls = data.get("extracted_from_urls") or urls
            return CommercialExtract(
                competitor=company,
                data=data,
                extracted_from_urls=[str(u) for u in extracted_urls],
                pricing_disclosure=data.get("pricing_disclosure", "opaque"),
                status=result.get("status", "completed" if result.get("success") else "failed"),
                error=str(result.get("error", "")),
                tokens_used=int(result.get("tokensUsed", 0) or 0),
                cached=bool(result.get("_cached", False)),
            )
        except Exception as e:
            logger.warning("Commercial extraction failed for %s: %s", company, e)
            return CommercialExtract(
                competitor=company,
                data={"pricing_disclosure": "opaque", "extraction_error": str(e)},
                extracted_from_urls=urls,
                pricing_disclosure="opaque",
                status="failed",
                error=str(e),
            )

    def _urls_for_profile(self, profile: CompetitorProfile) -> List[str]:
        pages = profile.key_pages or {}
        urls = []
        for key in ("pricing", "terms", "about", "customers"):
            url = pages.get(key)
            if url and url not in urls:
                urls.append(url)
        return urls[:4]

    def _opaque_extract(self, company: str, reason: str) -> CommercialExtract:
        return CommercialExtract(
            competitor=company,
            data={
                "pricing_disclosure": "opaque",
                "structured_finding": reason,
                "tiers": [],
                "add_ons": [],
                "primary_pricing_unit": "opaque",
                "starting_price_published": "not disclosed",
            },
            pricing_disclosure="opaque",
            status="skipped",
        )


def commercial_phases_required(parameter_path: str, variable_ids: List[str]) -> bool:
    return parameter_path == "innovera" and bool(COMMERCIAL_PARAMETER_IDS.intersection(variable_ids))
