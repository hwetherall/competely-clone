"""
Search client for web searches using the Serper API.

This module provides a robust search client with:
- Async HTTP requests using httpx
- MD5-based query caching
- Retry logic with exponential backoff
- Structured result parsing
- Source quality scoring
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from config import settings
from agents.source_scoring import score_url, extract_domain

# Configure logging
logger = logging.getLogger(__name__)


# =============================================================================
# Exceptions
# =============================================================================

class SearchError(Exception):
    """Custom exception for search-related errors."""
    
    def __init__(self, message: str, query: str = "", status_code: Optional[int] = None):
        self.message = message
        self.query = query
        self.status_code = status_code
        super().__init__(self.message)


class TransientSearchError(SearchError):
    """Transient error that should be retried."""
    pass


class PermanentSearchError(SearchError):
    """Permanent error that should not be retried."""
    pass


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class SearchResultItem:
    """A single search result item with source quality scoring."""
    title: str
    url: str
    snippet: str
    position: int
    # New fields for source quality
    domain: str = ""
    source_score: float = 0.5
    is_official: bool = False
    source_tier: str = "general"


@dataclass
class SearchResult:
    """Complete search result with metadata."""
    query: str
    items: List[SearchResultItem]
    total_results: int
    search_time: float
    cached: bool
    timestamp: str
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "query": self.query,
            "items": [asdict(item) for item in self.items],
            "total_results": self.total_results,
            "search_time": self.search_time,
            "cached": self.cached,
            "timestamp": self.timestamp,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "SearchResult":
        """Create from dictionary (for cache loading)."""
        items = []
        for item_data in data["items"]:
            # Handle both old and new format cache entries
            item = SearchResultItem(
                title=item_data.get("title", ""),
                url=item_data.get("url", ""),
                snippet=item_data.get("snippet", ""),
                position=item_data.get("position", 0),
                domain=item_data.get("domain", ""),
                source_score=item_data.get("source_score", 0.5),
                is_official=item_data.get("is_official", False),
                source_tier=item_data.get("source_tier", "general"),
            )
            items.append(item)
        return cls(
            query=data["query"],
            items=items,
            total_results=data["total_results"],
            search_time=data["search_time"],
            cached=data["cached"],
            timestamp=data["timestamp"],
        )


# =============================================================================
# Search Client
# =============================================================================

class SearchClient:
    """
    Async search client wrapping the Serper API.
    
    Features:
    - Async HTTP requests with httpx
    - Query result caching
    - Automatic retry with exponential backoff
    - Structured result parsing
    
    Example:
        client = SearchClient()
        result = await client.search("Stripe unique value proposition")
        for item in result.items:
            print(f"{item.title}: {item.url}")
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        cache_enabled: Optional[bool] = None,
        cache_dir: Optional[Path] = None,
    ):
        """
        Initialize the search client.
        
        Args:
            api_key: Serper API key (defaults to settings.SERPER_API_KEY)
            cache_enabled: Whether to cache results (defaults to settings.CACHE_ENABLED)
            cache_dir: Directory for cache files (defaults to settings.CACHE_DIR)
        """
        self.api_key = api_key or settings.SERPER_API_KEY
        self.cache_enabled = cache_enabled if cache_enabled is not None else settings.CACHE_ENABLED
        self.cache_dir = cache_dir or settings.CACHE_DIR
        self.base_url = settings.SERPER_BASE_URL
        
        # Ensure cache directory exists
        if self.cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Validate API key
        if not self.api_key:
            logger.warning("No Serper API key configured. Searches will fail.")
    
    def _get_cache_key(self, query: str) -> str:
        """Generate MD5 hash of query for cache key."""
        return hashlib.md5(query.encode("utf-8")).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """Get the file path for a cache entry."""
        return self.cache_dir / f"{cache_key}.json"
    
    def _load_from_cache(self, query: str) -> Optional[SearchResult]:
        """
        Attempt to load a cached result.
        
        Args:
            query: The search query
            
        Returns:
            Cached SearchResult or None if not found
        """
        if not self.cache_enabled:
            return None
        
        cache_key = self._get_cache_key(query)
        cache_path = self._get_cache_path(cache_key)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            result = SearchResult.from_dict(data)
            result.cached = True
            logger.debug(f"Cache hit for query: {query[:50]}...")
            return result
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Failed to load cache for query '{query[:50]}...': {e}")
            return None
    
    def _save_to_cache(self, result: SearchResult) -> None:
        """
        Save a search result to cache.
        
        Args:
            result: The search result to cache
        """
        if not self.cache_enabled:
            return
        
        cache_key = self._get_cache_key(result.query)
        cache_path = self._get_cache_path(cache_key)
        
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(result.to_dict(), f, indent=2)
            logger.debug(f"Cached result for query: {result.query[:50]}...")
        except IOError as e:
            logger.warning(f"Failed to cache result for query '{result.query[:50]}...': {e}")
    
    def _parse_response(
        self,
        query: str,
        response_data: dict,
        search_time: float,
        company: str = "",
    ) -> SearchResult:
        """
        Parse Serper API response into structured SearchResult.
        
        Args:
            query: The original search query
            response_data: Raw response from Serper API
            search_time: Time taken for the search
            company: Optional company name for official domain detection
            
        Returns:
            Structured SearchResult with source quality scores
        """
        items = []
        organic_results = response_data.get("organic", [])
        
        for result in organic_results:
            url = result.get("link", "")
            
            # Score the source quality
            source_score_result = score_url(url, company)
            
            item = SearchResultItem(
                title=result.get("title", ""),
                url=url,
                snippet=result.get("snippet", ""),
                position=result.get("position", 0),
                domain=source_score_result.domain,
                source_score=source_score_result.score,
                is_official=source_score_result.is_official,
                source_tier=source_score_result.tier,
            )
            items.append(item)
        
        return SearchResult(
            query=query,
            items=items,
            total_results=len(items),
            search_time=search_time,
            cached=False,
            timestamp=datetime.utcnow().isoformat(),
        )
    
    @retry(
        retry=retry_if_exception_type(TransientSearchError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def _execute_search(self, query: str, num_results: int) -> dict:
        """
        Execute the actual API request with retry logic.
        
        Args:
            query: Search query
            num_results: Number of results to request
            
        Returns:
            Raw API response as dict
            
        Raises:
            TransientSearchError: For retryable errors (429, 500, 502, 503, 504)
            PermanentSearchError: For non-retryable errors (401, 403, etc.)
        """
        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }
        
        payload = {
            "q": query,
            "num": num_results,
        }
        
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            try:
                response = await client.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                )
                
                # Handle different status codes
                if response.status_code == 200:
                    return response.json()
                elif response.status_code in (429, 500, 502, 503, 504):
                    # Transient errors - retry
                    raise TransientSearchError(
                        f"Transient error: {response.status_code}",
                        query=query,
                        status_code=response.status_code,
                    )
                elif response.status_code in (401, 403):
                    # Auth errors - don't retry
                    raise PermanentSearchError(
                        f"Authentication error: {response.status_code}. Check your API key.",
                        query=query,
                        status_code=response.status_code,
                    )
                else:
                    # Other errors - don't retry
                    raise PermanentSearchError(
                        f"API error: {response.status_code} - {response.text[:200]}",
                        query=query,
                        status_code=response.status_code,
                    )
                    
            except httpx.TimeoutException as e:
                raise TransientSearchError(
                    f"Request timeout: {e}",
                    query=query,
                )
            except httpx.RequestError as e:
                raise TransientSearchError(
                    f"Request error: {e}",
                    query=query,
                )
    
    async def search(
        self,
        query: str,
        num_results: int = 10,
        company: str = "",
    ) -> SearchResult:
        """
        Perform a web search with source quality scoring.
        
        This method will:
        1. Check cache first
        2. If not cached, call Serper API
        3. Parse and structure the response with source scores
        4. Cache the result
        5. Return the structured result
        
        Args:
            query: The search query
            num_results: Number of results to return (default: 10)
            company: Optional company name for official domain detection
            
        Returns:
            SearchResult with structured search results and source scores
            
        Raises:
            SearchError: If the search fails after retries
        """
        # Check cache first
        cached_result = self._load_from_cache(query)
        if cached_result:
            # Re-score cached results if company is provided (scores may differ)
            if company:
                for item in cached_result.items:
                    source_score_result = score_url(item.url, company)
                    item.domain = source_score_result.domain
                    item.source_score = source_score_result.score
                    item.is_official = source_score_result.is_official
                    item.source_tier = source_score_result.tier
            return cached_result
        
        # Execute search
        logger.info(f"Searching: {query[:50]}...")
        start_time = asyncio.get_event_loop().time()
        
        try:
            response_data = await self._execute_search(query, num_results)
        except (TransientSearchError, PermanentSearchError) as e:
            logger.error(f"Search failed for '{query[:50]}...': {e.message}")
            raise SearchError(e.message, query=query, status_code=e.status_code)
        
        end_time = asyncio.get_event_loop().time()
        search_time = end_time - start_time
        
        # Parse response with source scoring
        result = self._parse_response(query, response_data, search_time, company)
        
        # Cache result
        self._save_to_cache(result)
        
        logger.info(f"Search complete: {result.total_results} results in {search_time:.2f}s")
        return result
    
    def search_sync(
        self,
        query: str,
        num_results: int = 10,
        company: str = "",
    ) -> SearchResult:
        """
        Synchronous wrapper for the search method.
        
        Useful for testing and simple scripts.
        
        Args:
            query: The search query
            num_results: Number of results to return (default: 10)
            company: Optional company name for official domain detection
            
        Returns:
            SearchResult with structured search results
        """
        return asyncio.run(self.search(query, num_results, company))
    
    async def search_batch(
        self,
        queries: List[str],
        num_results: int = 10,
        max_concurrent: int = 5,
        company: str = "",
    ) -> List[SearchResult]:
        """
        Perform multiple searches with concurrency control.
        
        Args:
            queries: List of search queries
            num_results: Number of results per query
            max_concurrent: Maximum concurrent requests
            company: Optional company name for official domain detection
            
        Returns:
            List of SearchResults (in same order as queries)
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def bounded_search(query: str) -> SearchResult:
            async with semaphore:
                return await self.search(query, num_results, company)
        
        tasks = [bounded_search(q) for q in queries]
        return await asyncio.gather(*tasks, return_exceptions=True)
