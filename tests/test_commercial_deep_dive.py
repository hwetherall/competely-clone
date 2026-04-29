import asyncio

from agents.commercial_extractor import CommercialExtractor
from agents.competitor_profiler import CompetitorProfiler
from agents.coverage_check import run_coverage_check
from agents.gather_agent import GatherAgent
from agents.schemas import EvidenceSource, EvidencePassage
from agents.v2_schemas import CompetitorProfile, CommercialExtract
from config.innovera_variables import get_innovera_variable


class FakeSearchClient:
    async def search(self, query, num_results=10, company=""):
        from agents.search_client import SearchResult, SearchResultItem

        return SearchResult(
            query=query,
            items=[
                SearchResultItem(
                    title=f"{company} official",
                    url=f"https://{company.lower().replace(' ', '')}.com/",
                    snippet="Official site",
                    position=1,
                    is_official=True,
                    source_score=0.95,
                    source_tier="official",
                )
            ],
            total_results=1,
            search_time=0.1,
            cached=False,
            timestamp="2026-01-01T00:00:00",
        )


class FakeFirecrawlClient:
    def __init__(self, links=None, extract_data=None):
        self.links = links or []
        self.extract_data = extract_data or {}

    async def map(self, url, search="", limit=100, use_cache=True):
        return {"success": True, "links": self.links}

    async def extract(self, urls, schema, prompt, use_cache=True, cache_ttl_days=30, poll_interval=2.0, max_polls=30):
        return {
            "success": True,
            "status": "completed",
            "data": self.extract_data,
            "tokensUsed": 10,
        }


def test_profiler_classifies_transparent_saas():
    profiler = CompetitorProfiler(
        search_client=FakeSearchClient(),
        firecrawl_client=FakeFirecrawlClient(links=[
            {"url": "https://airtable.com/pricing", "title": "Pricing"},
            {"url": "https://airtable.com/terms", "title": "Terms"},
        ]),
    )

    profile = asyncio.run(profiler.profile_company("Airtable"))

    assert profile.type == "transparent_saas"
    assert profile.has_pricing_page is True
    assert profile.has_terms_page is True


def test_profiler_classifies_opaque_and_consulting():
    opaque = CompetitorProfiler(
        search_client=FakeSearchClient(),
        firecrawl_client=FakeFirecrawlClient(links=[
            {"url": "https://alphasense.com/terms", "title": "Terms"},
            {"url": "https://alphasense.com/customers", "title": "Customers"},
        ]),
    )
    consulting = CompetitorProfiler(
        search_client=FakeSearchClient(),
        firecrawl_client=FakeFirecrawlClient(links=[
            {"url": "https://mckinsey.com/capabilities", "title": "Capabilities"},
        ]),
    )

    assert asyncio.run(opaque.profile_company("AlphaSense")).type == "opaque_enterprise_saas"
    assert asyncio.run(consulting.profile_company("McKinsey")).type == "consulting_firm"


def test_profiler_classifies_early_stage_when_site_is_thin():
    profiler = CompetitorProfiler(
        search_client=FakeSearchClient(),
        firecrawl_client=FakeFirecrawlClient(links=[
            {"url": "https://lobo.ai/about", "title": "About"},
        ]),
    )

    profile = asyncio.run(profiler.profile_company("Lobo"))

    assert profile.type == "early_stage_startup"


def test_extractor_skips_consulting_and_extracts_saas():
    consulting_profile = CompetitorProfile(competitor="BCG", type="consulting_firm")
    extract = asyncio.run(CommercialExtractor().extract_for_profile(consulting_profile))

    assert extract.status == "skipped"
    assert extract.pricing_disclosure == "opaque"

    saas_profile = CompetitorProfile(
        competitor="Airtable",
        type="transparent_saas",
        key_pages={"pricing": "https://airtable.com/pricing", "terms": "https://airtable.com/terms"},
    )
    extractor = CommercialExtractor(firecrawl_client=FakeFirecrawlClient(
        extract_data={
            "pricing_disclosure": "fully_published",
            "starting_price_published": "$20/user/month",
            "extracted_from_urls": ["https://airtable.com/pricing"],
        }
    ))
    saas_extract = asyncio.run(extractor.extract_for_profile(saas_profile))

    assert saas_extract.status == "completed"
    assert saas_extract.data["starting_price_published"] == "$20/user/month"


def test_gather_seeds_commercial_extract(monkeypatch):
    variable = get_innovera_variable("inv_packaging")
    profile = CompetitorProfile(competitor="BCG", type="consulting_firm", homepage_url="https://bcg.com/")
    extract = CommercialExtract(
        competitor="BCG",
        data={"pricing_disclosure": "opaque", "structured_finding": "project-based pricing not disclosed"},
        pricing_disclosure="opaque",
        status="skipped",
    )
    agent = GatherAgent(
        search_client=FakeSearchClient(),
        variable_lookup={variable.id: variable},
        competitor_profiles={"BCG": profile},
        commercial_extracts={"BCG": extract},
        skip_evaluation=True,
        enable_page_fetch=False,
    )

    async def fake_extract_facts(state):
        return [], {}

    monkeypatch.setattr(agent, "_extract_facts", fake_extract_facts)
    dossier = asyncio.run(agent.gather("BCG", "inv_packaging"))

    assert dossier.sources[0].source_id == "C1"
    assert "STRUCTURED EXTRACT" in dossier.raw_passages[0].text
    assert dossier.metadata["competitor_profile"]["type"] == "consulting_firm"
    assert dossier.metadata["commercial_extract"]["pricing_disclosure"] == "opaque"


def test_coverage_check_distinguishes_opacity_from_gap():
    companies = ["BCG", "Airtable"]
    profiles = {
        "BCG": {"type": "consulting_firm"},
        "Airtable": {"type": "transparent_saas"},
    }
    analyses = {
        "inv_packaging": {
            "headline": "BCG pricing is opaque; Airtable has published tiers.",
            "positioning_table": [
                {"company": "BCG", "packaging": "opaque project-based"},
                {"company": "Airtable", "packaging": "tiered plans"},
            ],
        }
    }

    result = run_coverage_check(companies, analyses, profiles)

    assert result["gap_count"] > 0
    assert any(g["company"] == "BCG" and g["reason"] == "typology-driven opacity" for g in result["gaps"])
    assert any(g["company"] == "Airtable" and g["reason"] == "evidence gap" for g in result["gaps"])
