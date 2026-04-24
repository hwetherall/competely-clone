"""
Exa semantic search client.

This mirrors agents.search_client.SearchClient so discovery can use Exa
without changing downstream result handling.
"""

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from agents.search_client import (
    SearchError,
    SearchResult,
    SearchResultItem,
    TransientSearchError,
    PermanentSearchError,
)
from agents.source_scoring import score_url
from config import settings

logger = logging.getLogger(__name__)


class ExaClient:
    """
    Async Exa search client returning the shared SearchResult shape.

    Exa's current Search API uses POST /search with an x-api-key header. The
    `type` parameter defaults to settings.EXA_SEARCH_TYPE ("auto" by default).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        cache_enabled: Optional[bool] = None,
        cache_dir: Optional[Path] = None,
        base_url: Optional[str] = None,
        search_type: Optional[str] = None,
    ):
        self.api_key = api_key or settings.EXA_API_KEY
        self.cache_enabled = cache_enabled if cache_enabled is not None else settings.CACHE_ENABLED
        self.cache_dir = cache_dir or (settings.CACHE_DIR / "exa")
        self.base_url = (base_url or settings.EXA_BASE_URL).rstrip("/")
        self.search_type = search_type or settings.EXA_SEARCH_TYPE

        if self.cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        if not self.api_key:
            logger.warning("No Exa API key configured. Exa searches will fail.")

    def _get_cache_key(self, query: str, num_results: int, include_text: bool) -> str:
        raw = json.dumps(
            {
                "query": query,
                "num_results": num_results,
                "include_text": include_text,
                "type": self.search_type,
                "highlights_max_characters": settings.EXA_HIGHLIGHTS_MAX_CHARACTERS,
                "text_max_characters": settings.EXA_TEXT_MAX_CHARACTERS,
            },
            sort_keys=True,
        )
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        return self.cache_dir / f"{cache_key}.json"

    def _load_from_cache(self, query: str, num_results: int, include_text: bool) -> Optional[SearchResult]:
        if not self.cache_enabled:
            return None
        path = self._get_cache_path(self._get_cache_key(query, num_results, include_text))
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            result = SearchResult.from_dict(data)
            result.cached = True
            return result
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning("Failed to load Exa cache for query '%s': %s", query[:50], e)
            return None

    def _save_to_cache(self, result: SearchResult, num_results: int, include_text: bool) -> None:
        if not self.cache_enabled:
            return
        path = self._get_cache_path(self._get_cache_key(result.query, num_results, include_text))
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(result.to_dict(), f, indent=2)
        except OSError as e:
            logger.warning("Failed to cache Exa result for query '%s': %s", result.query[:50], e)

    def _parse_response(
        self,
        query: str,
        response_data: dict,
        search_time: float,
        company: str = "",
    ) -> SearchResult:
        items: List[SearchResultItem] = []
        for position, raw in enumerate(response_data.get("results", []), start=1):
            url = raw.get("url", "")
            score = score_url(url, company)
            snippets = []
            if raw.get("summary"):
                snippets.append(str(raw["summary"]))
            if raw.get("highlights"):
                snippets.extend(str(h) for h in raw.get("highlights", []))
            if raw.get("text") and not snippets:
                snippets.append(str(raw["text"])[:600])
            snippet = " ".join(s.strip() for s in snippets if s).strip()

            items.append(SearchResultItem(
                title=raw.get("title", "") or url,
                url=url,
                snippet=snippet,
                position=position,
                domain=score.domain,
                source_score=score.score,
                is_official=score.is_official,
                source_tier=score.tier,
            ))

        return SearchResult(
            query=query,
            items=items,
            total_results=len(items),
            search_time=search_time,
            cached=False,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    @retry(
        retry=retry_if_exception_type(TransientSearchError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def _execute_search(self, query: str, num_results: int, include_text: bool) -> dict:
        payload = {
            "query": query,
            "type": self.search_type,
            "numResults": num_results,
            "contents": {
                "highlights": {"maxCharacters": settings.EXA_HIGHLIGHTS_MAX_CHARACTERS},
            },
        }
        if include_text:
            payload["contents"]["text"] = {
                "maxCharacters": settings.EXA_TEXT_MAX_CHARACTERS,
                "verbosity": "compact",
            }

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
        }

        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            try:
                response = await client.post(f"{self.base_url}/search", headers=headers, json=payload)
            except httpx.TimeoutException as e:
                raise TransientSearchError(f"Exa request timeout: {e}", query=query)
            except httpx.RequestError as e:
                raise TransientSearchError(f"Exa request error: {e}", query=query)

        if response.status_code == 200:
            return response.json()
        if response.status_code in (429, 500, 502, 503, 504):
            raise TransientSearchError(f"Exa transient error: {response.status_code}", query=query, status_code=response.status_code)
        if response.status_code in (401, 403):
            raise PermanentSearchError("Exa authentication error. Check EXA_API_KEY.", query=query, status_code=response.status_code)
        raise PermanentSearchError(
            f"Exa API error: {response.status_code} - {response.text[:200]}",
            query=query,
            status_code=response.status_code,
        )

    async def search(
        self,
        query: str,
        num_results: int = 10,
        company: str = "",
        include_text: bool = False,
    ) -> SearchResult:
        cached = self._load_from_cache(query, num_results, include_text)
        if cached:
            if company:
                for item in cached.items:
                    score = score_url(item.url, company)
                    item.domain = score.domain
                    item.source_score = score.score
                    item.is_official = score.is_official
                    item.source_tier = score.tier
            return cached

        logger.info("Exa searching: %s...", query[:50])
        start = asyncio.get_event_loop().time()
        try:
            response_data = await self._execute_search(query, num_results, include_text)
        except (TransientSearchError, PermanentSearchError) as e:
            raise SearchError(e.message, query=query, status_code=e.status_code)
        search_time = asyncio.get_event_loop().time() - start
        result = self._parse_response(query, response_data, search_time, company)
        self._save_to_cache(result, num_results, include_text)
        return result

    def search_sync(
        self,
        query: str,
        num_results: int = 10,
        company: str = "",
        include_text: bool = False,
    ) -> SearchResult:
        return asyncio.run(self.search(query, num_results, company, include_text))

    async def search_batch(
        self,
        queries: List[str],
        num_results: int = 10,
        max_concurrent: int = 5,
        company: str = "",
        include_text: bool = False,
    ) -> List[SearchResult]:
        semaphore = asyncio.Semaphore(max_concurrent)

        async def bounded(query: str) -> SearchResult:
            async with semaphore:
                return await self.search(query, num_results, company, include_text)

        return await asyncio.gather(*(bounded(q) for q in queries), return_exceptions=True)
