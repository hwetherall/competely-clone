"""
Firecrawl page extraction client.

This mirrors PageReader's public fetch/fetch_batch shape and returns PageContent
so discovery can use richer extraction without changing downstream code.
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

from agents.page_reader import TransientFetchError
from agents.schemas import PageContent
from config import settings

logger = logging.getLogger(__name__)


class PermanentFirecrawlError(Exception):
    """Raised for non-retryable Firecrawl errors."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class FirecrawlClient:
    """Async Firecrawl scrape client returning PageContent."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        cache_dir: Optional[Path] = None,
        cache_enabled: Optional[bool] = None,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
        max_content_length: Optional[int] = None,
    ):
        self.api_key = api_key or settings.FIRECRAWL_API_KEY
        self.cache_dir = cache_dir or (settings.CACHE_DIR / "firecrawl")
        self.cache_enabled = cache_enabled if cache_enabled is not None else settings.CACHE_ENABLED
        self.base_url = (base_url or settings.FIRECRAWL_BASE_URL).rstrip("/")
        self.timeout = timeout or settings.FIRECRAWL_TIMEOUT
        self.max_content_length = max_content_length or settings.FIRECRAWL_MAX_CONTENT_LENGTH

        if self.cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        if not self.api_key:
            logger.warning("No Firecrawl API key configured. Firecrawl scrapes will fail.")

    def _get_cache_key(self, url: str) -> str:
        return hashlib.md5(url.encode("utf-8")).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        return self.cache_dir / f"{cache_key}.json"

    def _load_from_cache(self, url: str) -> Optional[PageContent]:
        if not self.cache_enabled:
            return None
        path = self._get_cache_path(self._get_cache_key(url))
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return PageContent.from_dict(json.load(f))
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning("Failed to load Firecrawl cache for URL '%s': %s", url[:50], e)
            return None

    def _save_to_cache(self, url: str, content: PageContent) -> None:
        if not self.cache_enabled:
            return
        path = self._get_cache_path(self._get_cache_key(url))
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(content.to_dict(), f, indent=2, ensure_ascii=False)
        except OSError as e:
            logger.warning("Failed to cache Firecrawl page '%s': %s", url[:50], e)

    def _parse_response(self, url: str, response_data: dict, status_code: int = 200) -> PageContent:
        if response_data.get("success") is False:
            return PageContent(
                url=url,
                status=status_code,
                fetched_at=datetime.now(timezone.utc).isoformat(),
                error=str(response_data.get("error", "Firecrawl scrape failed")),
            )

        data = response_data.get("data", response_data)
        metadata = data.get("metadata", {}) if isinstance(data, dict) else {}
        text = (
            data.get("markdown")
            or data.get("content")
            or data.get("text")
            or data.get("html")
            or ""
        )
        if len(text) > self.max_content_length:
            text = text[: self.max_content_length] + "..."
        excerpt = text[:500].strip()
        if len(text) > 500:
            last_period = excerpt.rfind(".")
            excerpt = excerpt[: last_period + 1] if last_period > 200 else excerpt + "..."

        return PageContent(
            url=url,
            final_url=metadata.get("sourceURL") or metadata.get("url") or url,
            status=status_code,
            title=metadata.get("title", ""),
            text=text,
            excerpt=excerpt,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            content_type="text/markdown" if data.get("markdown") else "text/plain",
        )

    @retry(
        retry=retry_if_exception_type(TransientFetchError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def _execute_scrape(self, url: str) -> dict:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "url": url,
            "formats": ["markdown"],
            "onlyMainContent": True,
            "timeout": self.timeout * 1000,
            "removeBase64Images": True,
            "blockAds": True,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(f"{self.base_url}/scrape", headers=headers, json=payload)
            except httpx.TimeoutException as e:
                raise TransientFetchError(f"Firecrawl timeout fetching {url}: {e}")
            except httpx.RequestError as e:
                raise TransientFetchError(f"Firecrawl request error fetching {url}: {e}")

        if response.status_code == 200:
            return response.json()
        if response.status_code in (429, 500, 502, 503, 504):
            raise TransientFetchError(f"Firecrawl transient error {response.status_code} for {url}")
        if response.status_code in (401, 403):
            raise PermanentFirecrawlError("Firecrawl authentication error. Check FIRECRAWL_API_KEY.", response.status_code)
        raise PermanentFirecrawlError(
            f"Firecrawl API error {response.status_code}: {response.text[:200]}",
            response.status_code,
        )

    async def fetch(self, url: str, use_cache: bool = True) -> PageContent:
        if use_cache:
            cached = self._load_from_cache(url)
            if cached:
                return cached
        try:
            data = await self._execute_scrape(url)
            result = self._parse_response(url, data, 200)
        except PermanentFirecrawlError as e:
            result = PageContent(
                url=url,
                status=e.status_code or 0,
                fetched_at=datetime.now(timezone.utc).isoformat(),
                error=e.message,
            )
        except TransientFetchError as e:
            result = PageContent(
                url=url,
                fetched_at=datetime.now(timezone.utc).isoformat(),
                error=str(e),
            )
        if use_cache:
            self._save_to_cache(url, result)
        return result

    def fetch_sync(self, url: str, use_cache: bool = True) -> PageContent:
        return asyncio.run(self.fetch(url, use_cache=use_cache))

    async def fetch_batch(
        self,
        urls: List[str],
        max_concurrent: int = 5,
        use_cache: bool = True,
    ) -> List[PageContent]:
        semaphore = asyncio.Semaphore(max_concurrent)

        async def bounded(url: str) -> PageContent:
            async with semaphore:
                return await self.fetch(url, use_cache=use_cache)

        results = await asyncio.gather(*(bounded(u) for u in urls), return_exceptions=True)
        processed: List[PageContent] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed.append(PageContent(
                    url=urls[i],
                    fetched_at=datetime.now(timezone.utc).isoformat(),
                    error=str(result),
                ))
            else:
                processed.append(result)
        return processed

