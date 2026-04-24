"""
Tests for M4 competitor discovery backend.
"""

import asyncio
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import BackgroundTasks

from agents.competitor_discovery_agent import (
    CompetitorDiscoveryAgent,
    _extract_result_json,
    _required_candidates_for_target,
    load_discovery_run,
    save_discovery_run,
)
from agents.schemas import CompetitorCandidate, DiscoveryRun, DiscoveryTargetProfile, PageContent
from agents.search_client import SearchResult, SearchResultItem
from api.models import DiscoveryCreateRequest, DiscoveryPromoteRequest, RunStatus
from api.routes.discovery import create_discovery, promote_discovery


class FakeLLM:
    async def complete_simple(self, prompt: str, **kwargs) -> str:
        if "Generate 3-5 semantic web search queries" in prompt:
            return '<result>{"queries": ["AI decision intelligence competitors", "strategy AI platform"]}</result>'
        if "Framing: Direct" in prompt:
            return """
            <result>{"candidates":[
              {"name":"Alpha AI","canonical_domain":"alpha.ai","rationale":"AI-native decision platform.","evidence_urls":["https://alpha.ai"],"confidence":0.8},
              {"name":"Beta Strategy","canonical_domain":"beta.com","rationale":"Competes in strategy tooling.","evidence_urls":["https://beta.com"],"confidence":0.7}
            ]}</result>
            """
        return """
        <result>{"candidates":[
          {"name":"Alpha AI","canonical_domain":"alpha.ai","rationale":"Also appears in another framing.","evidence_urls":["https://alpha.ai/about"],"confidence":0.65}
        ]}</result>
        """


class FakeSearch:
    async def search_batch(self, queries, num_results=10, max_concurrent=5, company="", include_text=False):
        return [
            SearchResult(
                query=q,
                items=[
                    SearchResultItem(title="Alpha AI", url="https://alpha.ai", snippet="Alpha", position=1),
                    SearchResultItem(title="Beta", url="https://beta.com", snippet="Beta", position=2),
                ],
                total_results=2,
                search_time=0.1,
                cached=False,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            for q in queries
        ]


class FakePages:
    async def fetch_batch(self, urls, max_concurrent=5, use_cache=True):
        return [
            PageContent(
                url=url,
                final_url=url,
                status=200,
                title=f"Page {i}",
                text=f"Extracted content for {url}",
                fetched_at=datetime.now(timezone.utc).isoformat(),
                content_type="text/markdown",
            )
            for i, url in enumerate(urls)
        ]


def test_extract_result_json_with_tags():
    data = _extract_result_json('noise <result>{"queries":["a","b"]}</result>')
    assert data == {"queries": ["a", "b"]}


def test_merge_and_rank_dedupes_across_framings():
    agent = CompetitorDiscoveryAgent(llm_client=FakeLLM(), search_client=FakeSearch(), page_client=FakePages())
    candidates = agent.merge_and_rank([
        {
            "name": "Alpha AI Inc.",
            "canonical_domain": "alpha.ai",
            "framings": ["direct"],
            "rationales": {"direct": "Direct match"},
            "evidence_urls": ["https://alpha.ai"],
            "confidence": 0.8,
        },
        {
            "name": "Alpha AI",
            "canonical_domain": "alpha.ai",
            "framings": ["category_sharer"],
            "rationales": {"category_sharer": "Category shape"},
            "evidence_urls": ["https://alpha.ai/about"],
            "confidence": 0.6,
        },
    ])

    assert len(candidates) == 1
    assert candidates[0].canonical_domain == "alpha.ai"
    assert set(candidates[0].framings) == {"direct", "category_sharer"}
    assert len(candidates[0].evidence_urls) == 2


def test_merge_and_rank_dedupes_required_candidate_by_name_without_domain():
    agent = CompetitorDiscoveryAgent(llm_client=FakeLLM(), search_client=FakeSearch(), page_client=FakePages())
    candidates = agent.merge_and_rank([
        {
            "name": "Rocket",
            "canonical_domain": None,
            "framings": ["direct"],
            "rationales": {"direct": "Live discovery found Rocket."},
            "evidence_urls": [],
            "confidence": 0.6,
        },
        *_required_candidates_for_target(
            DiscoveryTargetProfile(company_name="Innovera", description="AI decision platform")
        ),
    ])

    rocket_candidates = [candidate for candidate in candidates if candidate.name == "Rocket"]
    assert len(rocket_candidates) == 1
    assert rocket_candidates[0].canonical_domain == "rocket.new"
    assert set(rocket_candidates[0].framings) == {"direct", "category_sharer", "adjacency"}


def test_required_rocket_candidate_is_available_for_innovera_discovery():
    required = _required_candidates_for_target(
        DiscoveryTargetProfile(company_name="Innovera", description="AI decision platform")
    )

    assert any(candidate["name"] == "Rocket" for candidate in required)
    rocket = next(candidate for candidate in required if candidate["name"] == "Rocket")
    assert rocket["canonical_domain"] == "rocket.new"
    assert "https://www.rocket.new/" in rocket["evidence_urls"]


def test_discovery_run_with_fakes_persists(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        import agents.competitor_discovery_agent as module

        monkeypatch.setattr(module, "DISCOVERY_DIR", Path(tmpdir))
        agent = CompetitorDiscoveryAgent(llm_client=FakeLLM(), search_client=FakeSearch(), page_client=FakePages())
        run = asyncio.run(agent.run(
            target_profile=DiscoveryTargetProfile(company_name="Innovera", description="AI decision platform"),
            max_candidates=10,
            run_id="discovery_test",
        ))

        assert run.status == "complete"
        assert any(candidate.name == "Rocket" for candidate in run.candidates)
        assert len(run.candidates) >= 2
        loaded = load_discovery_run("discovery_test")
        assert loaded.status == "complete"
        assert loaded.candidates[0].name


def test_discovery_api_create_writes_initial_run(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        import agents.competitor_discovery_agent as agent_module
        import api.routes.discovery as route_module

        monkeypatch.setattr(agent_module, "DISCOVERY_DIR", Path(tmpdir))

        def fake_run_discovery_sync(**kwargs):
            return None

        monkeypatch.setattr(route_module, "run_discovery_sync", fake_run_discovery_sync)
        response = asyncio.run(create_discovery(DiscoveryCreateRequest(max_candidates=10), BackgroundTasks()))

        assert response.status == "running"
        loaded = load_discovery_run(response.discovery_run_id)
        assert loaded.status == "running"


def test_discovery_promote_creates_pending_run(monkeypatch):
    with tempfile.TemporaryDirectory() as discovery_tmp, tempfile.TemporaryDirectory() as results_tmp:
        import agents.competitor_discovery_agent as agent_module
        import api.routes.discovery as route_module
        from api.services.research_runner import ResearchRunner

        monkeypatch.setattr(agent_module, "DISCOVERY_DIR", Path(discovery_tmp))
        monkeypatch.setattr(route_module, "RESULTS_DIR", Path(results_tmp))
        monkeypatch.setattr(ResearchRunner, "run_research_sync", lambda self, **kwargs: None)

        run = DiscoveryRun(
            id="discovery_done",
            target_profile=DiscoveryTargetProfile(company_name="Innovera", description="AI decision platform"),
            framing_seeds={},
            candidates=[
                CompetitorCandidate(
                    name="Alpha AI",
                    canonical_domain="alpha.ai",
                    framings=["direct"],
                    rationales={"direct": "Direct"},
                    evidence_urls=["https://alpha.ai"],
                    confidence=0.8,
                    discovered_at=datetime.now(timezone.utc),
                )
            ],
            status="complete",
            created_at=datetime.now(timezone.utc),
        )
        save_discovery_run(run)

        response = asyncio.run(promote_discovery(
            "discovery_done",
            DiscoveryPromoteRequest(selected_names=["Alpha AI"], fast_mode=True),
            BackgroundTasks(),
        ))

        assert response.status == RunStatus.PENDING
        assert response.companies == ["Alpha AI"]
        assert (Path(results_tmp) / f"progress_{response.run_id}.json").exists()
