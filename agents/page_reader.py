import asyncio
import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import settings

logger = logging.getLogger(__name__)

class PageReader:
    """
    Fetches and extracts text from web pages.
    """
    
    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or settings.CACHE_DIR / "pages"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

    def _get_cache_path(self, url: str) -> Path:
        url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{url_hash}.json"

    async def fetch(self, url: str) -> Dict[str, Any]:
        """
        Fetch a URL and return extracted content.
        Checks cache first.
        """
        cache_path = self._get_cache_path(url)
        
        if settings.CACHE_ENABLED and cache_path.exists():
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Basic validation of cached data
                if data.get("url") == url and "text" in data:
                    logger.debug(f"Page cache hit: {url}")
                    return data
            except Exception as e:
                logger.warning(f"Failed to read page cache for {url}: {e}")

        # Fetch fresh
        try:
            result = await self._fetch_url(url)
            
            # Cache result
            if settings.CACHE_ENABLED and result["status"] == "success":
                try:
                    with open(cache_path, "w", encoding="utf-8") as f:
                        json.dump(result, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    logger.warning(f"Failed to write page cache for {url}: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return {
                "url": url,
                "status": "error",
                "error": str(e),
                "fetched_at": datetime.utcnow().isoformat(),
                "text": "",
                "title": ""
            }

    @retry(
        retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException, httpx.HTTPStatusError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _fetch_url(self, url: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0, headers=self.headers) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            content_type = response.headers.get("content-type", "").lower()
            final_url = str(response.url)
            
            if "text/html" not in content_type:
                return {
                    "url": url,
                    "final_url": final_url,
                    "status": "skipped",
                    "content_type": content_type,
                    "fetched_at": datetime.utcnow().isoformat(),
                    "text": "",
                    "title": ""
                }

            # Parse HTML
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Remove junk
            for tag in soup(["script", "style", "nav", "footer", "iframe", "noscript", "svg", "header"]):
                tag.decompose()
                
            title = soup.title.string.strip() if soup.title else ""
            
            # Extract text
            text = soup.get_text(separator="\n\n")
            
            # Clean text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            # Cap length
            if len(text) > 60000:
                text = text[:60000] + "... (truncated)"
            
            return {
                "url": url,
                "final_url": final_url,
                "status": "success",
                "content_type": content_type,
                "fetched_at": datetime.utcnow().isoformat(),
                "title": title,
                "text": text
            }
