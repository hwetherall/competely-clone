"""
Unit tests for the isolated Exa and Firecrawl clients.
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from agents.exa_client import ExaClient
from agents.gather_agent import create_search_client as create_gather_search_client
from agents.research_agent import create_search_client as create_research_search_client
from agents.firecrawl_client import FirecrawlClient
from agents.search_client import SearchResult
from agents.schemas import PageContent


class TestExaClient:
    def test_search_provider_factories_use_exa(self, monkeypatch):
        monkeypatch.setattr("config.settings.SEARCH_PROVIDER", "exa")
        assert isinstance(create_research_search_client(), ExaClient)
        assert isinstance(create_gather_search_client(), ExaClient)

    def test_parse_response_to_search_result(self):
        client = ExaClient(api_key="test", cache_enabled=False)
        data = {
            "requestId": "req_123",
            "searchType": "neural",
            "results": [
                {
                    "title": "Alpha",
                    "url": "https://alpha.example/page",
                    "summary": "Summary text.",
                    "highlights": ["Relevant highlight."],
                },
                {
                    "title": "Beta",
                    "url": "https://beta.example/page",
                    "text": "Long page text used as a fallback snippet.",
                },
            ],
        }

        result = client._parse_response("decision intelligence", data, 0.25, company="Alpha")

        assert isinstance(result, SearchResult)
        assert result.query == "decision intelligence"
        assert result.total_results == 2
        assert result.items[0].title == "Alpha"
        assert "Summary text" in result.items[0].snippet
        assert "Relevant highlight" in result.items[0].snippet
        assert result.items[1].position == 2

    def test_cache_round_trip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            client = ExaClient(api_key="test", cache_enabled=True, cache_dir=Path(tmpdir))
            result = client._parse_response(
                "query",
                {"results": [{"title": "One", "url": "https://example.com", "summary": "Snippet"}]},
                0.1,
            )

            client._save_to_cache(result, num_results=10, include_text=False)
            loaded = client._load_from_cache("query", num_results=10, include_text=False)

            assert loaded is not None
            assert loaded.cached is True
            assert loaded.items[0].url == "https://example.com"

    def test_execute_search_sends_exa_shape(self, monkeypatch):
        client = ExaClient(api_key="test-key", cache_enabled=False, base_url="https://api.exa.ai")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_http_client

        monkeypatch.setattr("agents.exa_client.httpx.AsyncClient", MagicMock(return_value=mock_context))

        asyncio.run(client._execute_search("AI strategy", num_results=7, include_text=True))
        call = mock_http_client.post.call_args
        assert call.args[0] == "https://api.exa.ai/search"
        assert call.kwargs["headers"]["x-api-key"] == "test-key"
        assert call.kwargs["json"]["query"] == "AI strategy"
        assert call.kwargs["json"]["numResults"] == 7
        assert call.kwargs["json"]["type"] == "auto"
        assert call.kwargs["json"]["contents"]["highlights"]["maxCharacters"] == 4000
        assert "text" in call.kwargs["json"]["contents"]
        assert call.kwargs["json"]["contents"]["text"]["maxCharacters"] == 20000
        assert call.kwargs["json"]["contents"]["text"]["verbosity"] == "compact"


class TestFirecrawlClient:
    def test_parse_response_to_page_content(self):
        client = FirecrawlClient(api_key="test", cache_enabled=False)
        data = {
            "success": True,
            "data": {
                "markdown": "# Test Page\n\nThis is useful extracted content.",
                "metadata": {
                    "title": "Test Page",
                    "sourceURL": "https://example.com/final",
                },
            },
        }

        result = client._parse_response("https://example.com", data)

        assert isinstance(result, PageContent)
        assert result.is_success
        assert result.title == "Test Page"
        assert result.final_url == "https://example.com/final"
        assert "useful extracted content" in result.text
        assert result.content_type == "text/markdown"

    def test_parse_failure_response(self):
        client = FirecrawlClient(api_key="test", cache_enabled=False)
        result = client._parse_response(
            "https://example.com",
            {"success": False, "error": "Could not scrape"},
            status_code=400,
        )

        assert result.is_success is False
        assert result.status == 400
        assert "Could not scrape" in result.error

    def test_cache_round_trip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            client = FirecrawlClient(api_key="test", cache_enabled=True, cache_dir=Path(tmpdir))
            content = PageContent(
                url="https://example.com",
                final_url="https://example.com",
                status=200,
                title="Cached",
                text="Cached content",
                fetched_at="2026-01-01T00:00:00Z",
            )

            client._save_to_cache(content.url, content)
            loaded = client._load_from_cache(content.url)

            assert loaded is not None
            assert loaded.title == "Cached"
            assert loaded.text == "Cached content"

    def test_execute_scrape_sends_firecrawl_shape(self, monkeypatch):
        client = FirecrawlClient(
            api_key="test-key",
            cache_enabled=False,
            base_url="https://api.firecrawl.dev/v2",
            timeout=60,
        )
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "data": {"markdown": "ok"}}

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_http_client

        monkeypatch.setattr("agents.firecrawl_client.httpx.AsyncClient", MagicMock(return_value=mock_context))

        asyncio.run(client._execute_scrape("https://example.com"))
        call = mock_http_client.post.call_args
        assert call.args[0] == "https://api.firecrawl.dev/v2/scrape"
        assert call.kwargs["headers"]["Authorization"] == "Bearer test-key"
        assert call.kwargs["json"]["url"] == "https://example.com"
        assert call.kwargs["json"]["formats"] == ["markdown"]
        assert call.kwargs["json"]["onlyMainContent"] is True

    def test_map_sends_firecrawl_shape(self, monkeypatch):
        client = FirecrawlClient(api_key="test-key", cache_enabled=False, base_url="https://api.firecrawl.dev/v2")
        client._post_json = AsyncMock(return_value={"success": True, "links": []})

        result = asyncio.run(client.map("https://example.com", search="pricing", limit=25, use_cache=False))

        assert result["success"] is True
        call = client._post_json.call_args
        assert call.args[0] == "map"
        assert call.args[1]["url"] == "https://example.com"
        assert call.args[1]["search"] == "pricing"
        assert call.args[1]["limit"] == 25

    def test_start_extract_sends_firecrawl_shape(self):
        client = FirecrawlClient(api_key="test-key", cache_enabled=False)
        client._post_json = AsyncMock(return_value={"success": True, "id": "extract-1"})
        schema = {"type": "object", "properties": {"price": {"type": "string"}}}

        result = asyncio.run(client.start_extract(["https://example.com/pricing"], schema, "Extract pricing"))

        assert result["id"] == "extract-1"
        call = client._post_json.call_args
        assert call.args[0] == "extract"
        assert call.args[1]["urls"] == ["https://example.com/pricing"]
        assert call.args[1]["schema"] == schema
        assert call.args[1]["showSources"] is True
        assert call.args[1]["scrapeOptions"]["formats"] == ["markdown"]

    def test_extract_polls_status(self):
        client = FirecrawlClient(api_key="test-key", cache_enabled=False)
        client.start_extract = AsyncMock(return_value={"success": True, "id": "extract-1"})
        client.get_extract_status = AsyncMock(return_value={
            "success": True,
            "status": "completed",
            "data": {"pricing_disclosure": "partial"},
            "tokensUsed": 123,
        })

        result = asyncio.run(client.extract(
            ["https://example.com/pricing"],
            {"type": "object"},
            "Extract pricing",
            use_cache=False,
            poll_interval=0,
            max_polls=1,
        ))

        assert result["status"] == "completed"
        assert result["data"]["pricing_disclosure"] == "partial"
        client.get_extract_status.assert_awaited_once_with("extract-1")
