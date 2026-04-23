"""
Page fetching and HTML extraction for evidence-grounded research.

This module provides async page fetching with:
- Jina Reader integration for clean content extraction (primary method)
- Direct HTML fetching as fallback
- Retry/backoff for transient errors
- Caching to data/cache/pages/
- HTML text extraction using BeautifulSoup (for fallback)
"""

import asyncio
import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any, Literal

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from agents.schemas import PageContent
from config import settings

logger = logging.getLogger(__name__)

# Jina Reader mode options
FetchMode = Literal["jina", "direct", "auto"]

# Try to import BeautifulSoup
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    logger.warning("beautifulsoup4 not installed. HTML extraction will be limited.")


# Maximum text length to extract from a page
MAX_TEXT_LENGTH = 60000

# Tags to remove from HTML before extraction
TAGS_TO_REMOVE = [
    "script", "style", "nav", "footer", "aside", "header",
    "noscript", "iframe", "svg", "canvas", "form",
    "button", "input", "select", "textarea",
]

# User agent for requests
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class TransientFetchError(Exception):
    """Raised for retryable fetch errors (429, 5xx, timeouts)."""
    pass


class PermanentFetchError(Exception):
    """Raised for non-retryable fetch errors (404, 403, etc.)."""
    pass


class PageReader:
    """
    Async page fetcher with Jina Reader integration and HTML extraction.
    
    Jina Reader is the primary method for fetching clean content from web pages.
    It handles JavaScript rendering, removes boilerplate, and extracts the main content.
    Direct fetching with BeautifulSoup is available as a fallback.
    """
    
    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        cache_enabled: bool = True,
        timeout: int = 30,
        max_retries: int = 3,
        fetch_mode: FetchMode = "auto",
    ):
        """
        Initialize the PageReader.
        
        Args:
            cache_dir: Directory for page cache (default: data/cache/pages)
            cache_enabled: Whether to use caching
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            fetch_mode: How to fetch pages:
                - "jina": Always use Jina Reader
                - "direct": Always use direct HTTP fetch with BeautifulSoup
                - "auto": Use Jina Reader if available, fall back to direct
        """
        self.cache_dir = cache_dir or (settings.CACHE_DIR / "pages")
        self.cache_enabled = cache_enabled
        self.timeout = timeout
        self.max_retries = max_retries
        self.fetch_mode = fetch_mode
        
        # Jina Reader configuration
        self.jina_base_url = settings.JINA_READER_BASE_URL
        self.jina_api_key = settings.JINA_READER_API_KEY
        self.jina_timeout = settings.JINA_READER_TIMEOUT
        self.jina_max_content_length = settings.JINA_READER_MAX_CONTENT_LENGTH
        
        # Ensure cache directory exists
        if self.cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Log configuration
        if self.fetch_mode == "jina" or (self.fetch_mode == "auto" and self.jina_api_key):
            logger.info(f"PageReader initialized with Jina Reader (API key: {'set' if self.jina_api_key else 'not set'})")
        else:
            logger.info("PageReader initialized with direct fetch mode")
    
    def _get_cache_key(self, url: str) -> str:
        """Generate MD5 hash of URL for cache key."""
        return hashlib.md5(url.encode("utf-8")).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """Get the cache file path for a key."""
        return self.cache_dir / f"{cache_key}.json"
    
    def _load_from_cache(self, url: str) -> Optional[PageContent]:
        """
        Attempt to load a cached page.
        
        Args:
            url: The URL to look up
            
        Returns:
            Cached PageContent or None if not found
        """
        if not self.cache_enabled:
            return None
        
        cache_key = self._get_cache_key(url)
        cache_path = self._get_cache_path(cache_key)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            result = PageContent.from_dict(data)
            logger.debug(f"Cache hit for URL: {url[:50]}...")
            return result
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Failed to load cache for URL '{url[:50]}...': {e}")
            return None
    
    def _save_to_cache(self, url: str, content: PageContent) -> None:
        """
        Save page content to cache.
        
        Args:
            url: The URL
            content: The PageContent to cache
        """
        if not self.cache_enabled:
            return
        
        cache_key = self._get_cache_key(url)
        cache_path = self._get_cache_path(cache_key)
        
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(content.to_dict(), f, indent=2, ensure_ascii=False)
            logger.debug(f"Cached page: {url[:50]}...")
        except IOError as e:
            logger.warning(f"Failed to cache page '{url[:50]}...': {e}")
    
    def _extract_text_with_bs4(self, html: str) -> tuple:
        """
        Extract text from HTML using BeautifulSoup.
        
        Args:
            html: Raw HTML content
            
        Returns:
            Tuple of (title, text, excerpt)
        """
        soup = BeautifulSoup(html, "html.parser")
        
        # Extract title
        title = ""
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True)
        
        # Remove unwanted tags
        for tag_name in TAGS_TO_REMOVE:
            for tag in soup.find_all(tag_name):
                tag.decompose()
        
        # Extract text from remaining content
        # Prioritize main content areas
        main_content = soup.find("main") or soup.find("article") or soup.find("body")
        
        if main_content:
            # Get text from paragraphs, headings, and list items
            text_elements = main_content.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "td", "th", "span", "div"])
            
            paragraphs = []
            seen_text = set()
            
            for elem in text_elements:
                text = elem.get_text(separator=" ", strip=True)
                # Deduplicate and filter short lines
                if text and len(text) > 20 and text not in seen_text:
                    seen_text.add(text)
                    paragraphs.append(text)
            
            full_text = "\n\n".join(paragraphs)
        else:
            full_text = soup.get_text(separator="\n", strip=True)
        
        # Clean up whitespace
        full_text = re.sub(r'\n{3,}', '\n\n', full_text)
        full_text = re.sub(r' {2,}', ' ', full_text)
        
        # Truncate if too long
        if len(full_text) > MAX_TEXT_LENGTH:
            full_text = full_text[:MAX_TEXT_LENGTH] + "..."
        
        # Create excerpt (first ~500 chars)
        excerpt = full_text[:500].strip()
        if len(full_text) > 500:
            # Try to end at a sentence boundary
            last_period = excerpt.rfind(".")
            if last_period > 200:
                excerpt = excerpt[:last_period + 1]
            else:
                excerpt += "..."
        
        return title, full_text, excerpt
    
    def _extract_text_fallback(self, html: str) -> tuple:
        """
        Extract text from HTML using regex (fallback if BS4 not available).
        
        Args:
            html: Raw HTML content
            
        Returns:
            Tuple of (title, text, excerpt)
        """
        # Extract title
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else ""
        
        # Remove script and style tags
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove all HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        
        # Decode HTML entities
        text = re.sub(r'&nbsp;', ' ', text)
        text = re.sub(r'&amp;', '&', text)
        text = re.sub(r'&lt;', '<', text)
        text = re.sub(r'&gt;', '>', text)
        text = re.sub(r'&quot;', '"', text)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Truncate if too long
        if len(text) > MAX_TEXT_LENGTH:
            text = text[:MAX_TEXT_LENGTH] + "..."
        
        # Create excerpt
        excerpt = text[:500].strip()
        if len(text) > 500:
            excerpt += "..."
        
        return title, text, excerpt
    
    def extract_text(self, html: str) -> tuple:
        """
        Extract text from HTML.
        
        Args:
            html: Raw HTML content
            
        Returns:
            Tuple of (title, text, excerpt)
        """
        if BS4_AVAILABLE:
            return self._extract_text_with_bs4(html)
        else:
            return self._extract_text_fallback(html)
    
    async def _fetch_url_jina(self, url: str, client: httpx.AsyncClient) -> PageContent:
        """
        Fetch a URL using Jina Reader for clean content extraction.
        
        Jina Reader handles:
        - JavaScript-rendered content
        - Boilerplate removal (headers, footers, ads)
        - Clean markdown/text extraction
        
        Args:
            url: The URL to fetch
            client: httpx AsyncClient instance
            
        Returns:
            PageContent with extracted data
        """
        # Jina Reader URL format: https://r.jina.ai/{url}
        jina_url = f"{self.jina_base_url}{url}"
        
        headers = {
            "Accept": "application/json",  # Request JSON response
        }
        
        # Add API key if available (enables higher rate limits)
        if self.jina_api_key:
            headers["Authorization"] = f"Bearer {self.jina_api_key}"
        
        try:
            response = await client.get(
                jina_url,
                headers=headers,
                timeout=self.jina_timeout,
            )
            
            # Check for transient errors
            if response.status_code in (429, 500, 502, 503, 504):
                raise TransientFetchError(f"Jina Reader HTTP {response.status_code} for {url}")
            
            # Check for permanent errors
            if response.status_code in (401, 403, 404, 410):
                return PageContent(
                    url=url,
                    status=response.status_code,
                    fetched_at=datetime.now(timezone.utc).isoformat(),
                    error=f"Jina Reader HTTP {response.status_code}",
                )
            
            # Parse response - Jina Reader can return JSON or plain text
            content_type = response.headers.get("content-type", "")
            
            if "application/json" in content_type:
                # JSON response format
                try:
                    data = response.json()
                    
                    # Handle Jina's JSON response structure
                    # It typically has: {data: {url, title, content, ...}}
                    result_data = data.get("data", data)
                    
                    title = result_data.get("title", "")
                    text = result_data.get("content", "") or result_data.get("text", "")
                    final_url = result_data.get("url", url)
                    
                    # Truncate if too long
                    if len(text) > self.jina_max_content_length:
                        text = text[:self.jina_max_content_length] + "..."
                    
                    # Create excerpt
                    excerpt = text[:500].strip()
                    if len(text) > 500:
                        last_period = excerpt.rfind(".")
                        if last_period > 200:
                            excerpt = excerpt[:last_period + 1]
                        else:
                            excerpt += "..."
                    
                    return PageContent(
                        url=url,
                        final_url=final_url,
                        status=200,
                        title=title,
                        text=text,
                        excerpt=excerpt,
                        fetched_at=datetime.now(timezone.utc).isoformat(),
                        content_type="text/markdown",  # Jina returns markdown
                    )
                    
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Failed to parse Jina JSON response: {e}")
                    # Fall through to plain text handling
            
            # Plain text/markdown response
            text = response.text
            
            # Try to extract title from markdown (first # heading)
            title_match = re.search(r'^#\s+(.+)$', text, re.MULTILINE)
            title = title_match.group(1) if title_match else ""
            
            # Truncate if too long
            if len(text) > self.jina_max_content_length:
                text = text[:self.jina_max_content_length] + "..."
            
            # Create excerpt
            excerpt = text[:500].strip()
            if len(text) > 500:
                excerpt += "..."
            
            return PageContent(
                url=url,
                final_url=url,
                status=200,
                title=title,
                text=text,
                excerpt=excerpt,
                fetched_at=datetime.now(timezone.utc).isoformat(),
                content_type="text/markdown",
            )
            
        except httpx.TimeoutException:
            raise TransientFetchError(f"Jina Reader timeout fetching {url}")
        except httpx.ConnectError as e:
            raise TransientFetchError(f"Jina Reader connection error: {e}")
        except Exception as e:
            logger.warning(f"Jina Reader error for {url}: {e}")
            raise TransientFetchError(f"Jina Reader error: {e}")
    
    @retry(
        retry=retry_if_exception_type(TransientFetchError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def _fetch_url(self, url: str, client: httpx.AsyncClient) -> PageContent:
        """
        Fetch a single URL with retry logic.
        
        Args:
            url: The URL to fetch
            client: httpx AsyncClient instance
            
        Returns:
            PageContent with fetched data
            
        Raises:
            TransientFetchError: For retryable errors
            PermanentFetchError: For non-retryable errors
        """
        try:
            response = await client.get(
                url,
                follow_redirects=True,
                timeout=self.timeout,
            )
            
            # Check for transient errors (should retry)
            if response.status_code in (429, 500, 502, 503, 504):
                raise TransientFetchError(f"HTTP {response.status_code} for {url}")
            
            # Check for permanent errors (should not retry)
            if response.status_code in (401, 403, 404, 410):
                return PageContent(
                    url=url,
                    final_url=str(response.url),
                    status=response.status_code,
                    fetched_at=datetime.now(timezone.utc).isoformat(),
                    error=f"HTTP {response.status_code}",
                )
            
            # Success
            content_type = response.headers.get("content-type", "")
            
            # Only process HTML content
            if "text/html" not in content_type.lower():
                return PageContent(
                    url=url,
                    final_url=str(response.url),
                    status=response.status_code,
                    content_type=content_type,
                    fetched_at=datetime.now(timezone.utc).isoformat(),
                    error=f"Non-HTML content type: {content_type}",
                )
            
            # Extract text from HTML
            html = response.text
            title, text, excerpt = self.extract_text(html)
            
            return PageContent(
                url=url,
                final_url=str(response.url),
                status=response.status_code,
                title=title,
                text=text,
                excerpt=excerpt,
                fetched_at=datetime.now(timezone.utc).isoformat(),
                content_type=content_type,
            )
            
        except httpx.TimeoutException:
            raise TransientFetchError(f"Timeout fetching {url}")
        except httpx.ConnectError as e:
            raise TransientFetchError(f"Connection error fetching {url}: {e}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (429, 500, 502, 503, 504):
                raise TransientFetchError(f"HTTP {e.response.status_code} for {url}")
            return PageContent(
                url=url,
                status=e.response.status_code,
                fetched_at=datetime.now(timezone.utc).isoformat(),
                error=str(e),
            )
    
    async def fetch(
        self,
        url: str,
        use_cache: bool = True,
        force_mode: Optional[FetchMode] = None,
    ) -> PageContent:
        """
        Fetch a single URL using Jina Reader (primary) or direct fetch (fallback).
        
        Args:
            url: The URL to fetch
            use_cache: Whether to use/update cache
            force_mode: Override the default fetch mode for this request
            
        Returns:
            PageContent with fetched data
        """
        # Check cache first
        if use_cache and self.cache_enabled:
            cached = self._load_from_cache(url)
            if cached is not None:
                return cached
        
        # Determine which fetch mode to use
        mode = force_mode or self.fetch_mode
        
        # For "auto" mode, prefer Jina Reader
        use_jina = mode == "jina" or (mode == "auto")
        use_direct = mode == "direct"
        
        result = None
        
        async with httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        ) as client:
            # Try Jina Reader first (unless direct mode is forced)
            if use_jina and not use_direct:
                try:
                    result = await self._fetch_url_jina(url, client)
                    if result.is_success:
                        logger.debug(f"Jina Reader success for {url[:50]}... ({len(result.text)} chars)")
                    else:
                        logger.warning(f"Jina Reader returned error for {url[:50]}...: {result.error}")
                        # Reset result to try fallback
                        if mode == "auto":
                            result = None
                except TransientFetchError as e:
                    logger.warning(f"Jina Reader transient error for {url[:50]}...: {e}")
                    if mode == "auto":
                        result = None  # Try fallback
                    else:
                        result = PageContent(
                            url=url,
                            fetched_at=datetime.now(timezone.utc).isoformat(),
                            error=f"Jina Reader error: {e}",
                        )
                except Exception as e:
                    logger.warning(f"Jina Reader unexpected error for {url[:50]}...: {e}")
                    if mode == "auto":
                        result = None  # Try fallback
                    else:
                        result = PageContent(
                            url=url,
                            fetched_at=datetime.now(timezone.utc).isoformat(),
                            error=f"Jina Reader error: {e}",
                        )
            
            # Fallback to direct fetch if Jina failed or direct mode is set
            if result is None or (not result.is_success and mode == "auto"):
                logger.debug(f"Using direct fetch for {url[:50]}...")
                try:
                    result = await self._fetch_url(url, client)
                except TransientFetchError as e:
                    logger.warning(f"Failed to fetch {url} after retries: {e}")
                    result = PageContent(
                        url=url,
                        fetched_at=datetime.now(timezone.utc).isoformat(),
                        error=str(e),
                    )
                except Exception as e:
                    logger.error(f"Unexpected error fetching {url}: {e}")
                    result = PageContent(
                        url=url,
                        fetched_at=datetime.now(timezone.utc).isoformat(),
                        error=str(e),
                    )
        
        # Cache the result (even failures, to avoid repeated attempts)
        if use_cache and self.cache_enabled:
            self._save_to_cache(url, result)
        
        return result
    
    async def fetch_batch(
        self,
        urls: List[str],
        max_concurrent: int = 5,
        use_cache: bool = True,
        force_mode: Optional[FetchMode] = None,
    ) -> List[PageContent]:
        """
        Fetch multiple URLs concurrently with bounded concurrency.
        
        Args:
            urls: List of URLs to fetch
            max_concurrent: Maximum concurrent requests
            use_cache: Whether to use/update cache
            force_mode: Override the default fetch mode for all requests
            
        Returns:
            List of PageContent results (same order as input)
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def fetch_with_semaphore(url: str) -> PageContent:
            async with semaphore:
                return await self.fetch(url, use_cache=use_cache, force_mode=force_mode)
        
        tasks = [fetch_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error PageContent
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(PageContent(
                    url=urls[i],
                    fetched_at=datetime.now(timezone.utc).isoformat(),
                    error=str(result),
                ))
            else:
                processed_results.append(result)
        
        # Log batch summary
        success_count = sum(1 for r in processed_results if r.is_success)
        logger.info(f"Batch fetch complete: {success_count}/{len(urls)} successful")
        
        return processed_results
    
    def fetch_sync(
        self,
        url: str,
        use_cache: bool = True,
        force_mode: Optional[FetchMode] = None,
    ) -> PageContent:
        """
        Synchronous wrapper for fetch().
        
        Args:
            url: The URL to fetch
            use_cache: Whether to use/update cache
            force_mode: Override the default fetch mode
            
        Returns:
            PageContent with fetched data
        """
        return asyncio.run(self.fetch(url, use_cache=use_cache, force_mode=force_mode))


# Singleton instance
_page_reader: Optional[PageReader] = None


def get_page_reader(fetch_mode: FetchMode = "auto") -> PageReader:
    """
    Get or create the singleton PageReader instance.
    
    Args:
        fetch_mode: Default fetch mode ("jina", "direct", or "auto")
        
    Returns:
        PageReader instance
    """
    global _page_reader
    if _page_reader is None:
        _page_reader = PageReader(
            cache_enabled=settings.CACHE_ENABLED,
            timeout=settings.PAGE_FETCH_TIMEOUT,
            fetch_mode=fetch_mode,
        )
    return _page_reader


def create_page_reader(
    cache_enabled: bool = True,
    fetch_mode: FetchMode = "auto",
) -> PageReader:
    """
    Create a new PageReader instance (not singleton).
    
    Use this when you need a PageReader with custom settings.
    
    Args:
        cache_enabled: Whether to enable caching
        fetch_mode: Fetch mode ("jina", "direct", or "auto")
        
    Returns:
        New PageReader instance
    """
    return PageReader(
        cache_enabled=cache_enabled,
        timeout=settings.PAGE_FETCH_TIMEOUT,
        fetch_mode=fetch_mode,
    )
