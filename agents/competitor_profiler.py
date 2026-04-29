"""
Competitor commercial profiling for the Innovera V2 path.

This phase runs once per competitor before per-parameter research. It resolves a
homepage, maps likely commercial URLs, and produces the typology key used by the
commercial deep-dive parameters.
"""

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from agents.firecrawl_client import FirecrawlClient
from agents.search_client import SearchClient
from agents.v2_schemas import CompetitorProfile

logger = logging.getLogger(__name__)

CONSULTING_TERMS = {
    "bcg",
    "bain",
    "mckinsey",
    "deloitte",
    "pwc",
    "ey",
    "kpmg",
    "hackett",
    "hbr",
    "gartner",
    "forrester",
}


def _domain(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    return host[4:] if host.startswith("www.") else host


def _url_contains(url: str, *needles: str) -> bool:
    value = url.lower()
    return any(n in value for n in needles)


def _pick_url(links: List[Dict[str, Any]], *needles: str) -> Optional[str]:
    for link in links:
        url = str(link.get("url") or "")
        title = str(link.get("title") or "")
        haystack = f"{url} {title}".lower()
        if any(n in haystack for n in needles):
            return url
    return None


class CompetitorProfiler:
    """Build typology profiles for competitor commercial research."""

    def __init__(
        self,
        search_client: Optional[SearchClient] = None,
        firecrawl_client: Optional[FirecrawlClient] = None,
    ):
        self.search_client = search_client or SearchClient()
        self.firecrawl_client = firecrawl_client or FirecrawlClient()

    async def profile_companies(
        self,
        companies: List[str],
        max_concurrent: int = 5,
    ) -> Dict[str, CompetitorProfile]:
        semaphore = asyncio.Semaphore(max_concurrent)

        async def bounded(company: str) -> tuple[str, CompetitorProfile]:
            async with semaphore:
                return company, await self.profile_company(company)

        results = await asyncio.gather(*(bounded(c) for c in companies), return_exceptions=True)
        profiles: Dict[str, CompetitorProfile] = {}
        for result in results:
            if isinstance(result, Exception):
                logger.warning("Competitor profiling task failed: %s", result)
                continue
            company, profile = result
            profiles[company] = profile
        return profiles

    async def profile_company(self, company: str) -> CompetitorProfile:
        homepage = await self._resolve_homepage(company)
        if not homepage:
            return CompetitorProfile(
                competitor=company,
                type="unknown",
                confidence="low",
                notes="Could not resolve official homepage.",
            )
        links = await self._map_homepage(homepage)
        key_pages = self._select_key_pages(homepage, links)
        profile_type = self._classify(company, links, key_pages)
        confidence = "high" if links and profile_type != "unknown" else "medium" if homepage else "low"
        return CompetitorProfile(
            competitor=company,
            type=profile_type,
            has_pricing_page=bool(key_pages.get("pricing")),
            has_terms_page=bool(key_pages.get("terms")),
            is_public=self._looks_public_company(company, links),
            homepage_url=homepage,
            key_pages=key_pages,
            confidence=confidence,
            notes=f"Profiled from {len(links)} mapped URLs.",
        )

    async def _resolve_homepage(self, company: str) -> str:
        try:
            result = await self.search_client.search(f"{company} official website", num_results=5, company=company)
            for item in result.items:
                url = item.url
                if item.is_official or self._looks_like_company_domain(company, url):
                    return self._origin(url)
            if result.items:
                return self._origin(result.items[0].url)
        except Exception as e:
            logger.warning("Homepage resolution failed for %s: %s", company, e)
        return ""

    async def _map_homepage(self, homepage: str) -> List[Dict[str, Any]]:
        try:
            result = await self.firecrawl_client.map(homepage, limit=200, use_cache=True)
            links = result.get("links") or []
            normalized = []
            for link in links:
                if isinstance(link, dict) and link.get("url"):
                    normalized.append(link)
                elif isinstance(link, str) and link:
                    normalized.append({"url": link, "title": ""})
            return normalized
        except Exception as e:
            logger.warning("Firecrawl map failed for %s: %s", homepage, e)
            return []

    def _select_key_pages(self, homepage: str, links: List[Dict[str, Any]]) -> Dict[str, Optional[str]]:
        return {
            "pricing": _pick_url(links, "pricing", "plans", "packages", "tiers") or None,
            "terms": _pick_url(links, "terms", "tos", "terms-of-service", "legal", "msa") or None,
            "about": _pick_url(links, "about", "company") or homepage,
            "customers": _pick_url(links, "customers", "case-studies", "case_studies", "clients") or None,
        }

    def _classify(self, company: str, links: List[Dict[str, Any]], key_pages: Dict[str, Optional[str]]) -> str:
        normalized = re.sub(r"[^a-z0-9]+", " ", company.lower())
        if any(term in normalized.split() or term in normalized for term in CONSULTING_TERMS):
            return "consulting_firm"
        if key_pages.get("pricing"):
            return "transparent_saas"
        if key_pages.get("terms"):
            return "opaque_enterprise_saas"
        if len(links) <= 4:
            return "early_stage_startup"
        if links:
            return "opaque_enterprise_saas"
        return "unknown"

    def _looks_public_company(self, company: str, links: List[Dict[str, Any]]) -> bool:
        haystack = " ".join(str(l.get("url", "")) for l in links).lower()
        return "investor" in haystack or "sec.gov" in haystack or "annual-report" in haystack

    def _looks_like_company_domain(self, company: str, url: str) -> bool:
        cleaned = re.sub(r"[^a-z0-9]", "", company.lower())
        domain = re.sub(r"[^a-z0-9]", "", _domain(url).split(".")[0])
        return bool(cleaned and (cleaned in domain or domain in cleaned))

    def _origin(self, url: str) -> str:
        parsed = urlparse(url if url.startswith(("http://", "https://")) else f"https://{url}")
        return f"{parsed.scheme}://{parsed.netloc}/"
