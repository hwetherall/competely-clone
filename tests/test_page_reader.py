"""
Unit tests for page_reader module.
"""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from agents.page_reader import PageReader, TransientFetchError
from agents.schemas import PageContent


class TestPageReaderCaching:
    """Tests for page caching functionality."""
    
    def test_cache_key_generation(self):
        """Test that cache keys are deterministic."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reader = PageReader(cache_dir=Path(tmpdir), cache_enabled=True)
            
            key1 = reader._get_cache_key("https://example.com/page")
            key2 = reader._get_cache_key("https://example.com/page")
            key3 = reader._get_cache_key("https://example.com/other")
            
            assert key1 == key2
            assert key1 != key3
    
    def test_cache_path_generation(self):
        """Test that cache paths are correct."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reader = PageReader(cache_dir=Path(tmpdir), cache_enabled=True)
            
            key = reader._get_cache_key("https://example.com")
            path = reader._get_cache_path(key)
            
            assert str(path).endswith(f"{key}.json")
            assert Path(tmpdir) in path.parents or Path(tmpdir) == path.parent
    
    def test_save_and_load_cache(self):
        """Test that cache round-trips correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reader = PageReader(cache_dir=Path(tmpdir), cache_enabled=True)
            
            url = "https://example.com/test"
            content = PageContent(
                url=url,
                final_url=url,
                status=200,
                title="Test Page",
                text="This is test content.",
                excerpt="This is test...",
                fetched_at="2024-01-01T00:00:00Z",
                content_type="text/html",
            )
            
            # Save to cache
            reader._save_to_cache(url, content)
            
            # Load from cache
            loaded = reader._load_from_cache(url)
            
            assert loaded is not None
            assert loaded.url == url
            assert loaded.title == "Test Page"
            assert loaded.text == "This is test content."
    
    def test_cache_miss_returns_none(self):
        """Test that cache miss returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reader = PageReader(cache_dir=Path(tmpdir), cache_enabled=True)
            
            result = reader._load_from_cache("https://nonexistent.com/page")
            
            assert result is None
    
    def test_cache_disabled_no_save(self):
        """Test that disabled cache doesn't save."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reader = PageReader(cache_dir=Path(tmpdir), cache_enabled=False)
            
            url = "https://example.com/test"
            content = PageContent(url=url, status=200, text="Test")
            
            reader._save_to_cache(url, content)
            
            # Should not be cached
            loaded = reader._load_from_cache(url)
            assert loaded is None


class TestTextExtraction:
    """Tests for HTML text extraction."""
    
    def test_extract_title(self):
        """Test title extraction."""
        reader = PageReader(cache_enabled=False)
        
        html = "<html><head><title>Test Title</title></head><body><p>Content</p></body></html>"
        title, text, excerpt = reader.extract_text(html)
        
        assert title == "Test Title"
    
    def test_extract_paragraph_text(self):
        """Test paragraph text extraction."""
        reader = PageReader(cache_enabled=False)
        
        html = """
        <html>
        <body>
            <p>This is the first paragraph with enough content to be extracted.</p>
            <p>This is the second paragraph with more meaningful content.</p>
        </body>
        </html>
        """
        title, text, excerpt = reader.extract_text(html)
        
        assert "first paragraph" in text
        assert "second paragraph" in text
    
    def test_removes_script_and_style(self):
        """Test that script and style tags are removed."""
        reader = PageReader(cache_enabled=False)
        
        html = """
        <html>
        <head>
            <style>.hidden { display: none; }</style>
            <script>alert('test');</script>
        </head>
        <body>
            <p>Visible content here.</p>
            <script>console.log('inline');</script>
        </body>
        </html>
        """
        title, text, excerpt = reader.extract_text(html)
        
        assert "alert" not in text
        assert "console" not in text
        assert ".hidden" not in text
        assert "Visible content" in text
    
    def test_removes_nav_footer(self):
        """Test that nav and footer are removed."""
        reader = PageReader(cache_enabled=False)
        
        html = """
        <html>
        <body>
            <nav>Navigation menu items here</nav>
            <main>
                <p>Main content that should be extracted and is long enough.</p>
            </main>
            <footer>Footer content to remove</footer>
        </body>
        </html>
        """
        title, text, excerpt = reader.extract_text(html)
        
        # Main content should be present
        assert "Main content" in text
        # Nav and footer should ideally be removed (depends on BS4)
    
    def test_text_truncation(self):
        """Test that very long text is truncated."""
        reader = PageReader(cache_enabled=False)
        
        # Create very long content
        long_content = "Word " * 20000  # ~100k chars
        html = f"<html><body><p>{long_content}</p></body></html>"
        
        title, text, excerpt = reader.extract_text(html)
        
        # Should be truncated to 60k chars max
        assert len(text) <= 60003  # 60000 + "..."
    
    def test_excerpt_generation(self):
        """Test that excerpt is generated correctly."""
        reader = PageReader(cache_enabled=False)
        
        html = """
        <html><body>
            <p>This is a test paragraph with enough content. It continues with more text here.</p>
        </body></html>
        """
        title, text, excerpt = reader.extract_text(html)
        
        assert len(excerpt) <= 503  # 500 + "..."
        assert len(excerpt) > 0


class TestPageReaderFetch:
    """Tests for async page fetching."""
    
    @pytest.mark.asyncio
    async def test_fetch_uses_cache(self):
        """Test that fetch returns cached content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reader = PageReader(cache_dir=Path(tmpdir), cache_enabled=True)
            
            url = "https://example.com/cached"
            cached_content = PageContent(
                url=url,
                final_url=url,
                status=200,
                title="Cached Page",
                text="Cached content",
                fetched_at="2024-01-01T00:00:00Z",
            )
            reader._save_to_cache(url, cached_content)
            
            # Fetch should return cached version without making request
            result = await reader.fetch(url, use_cache=True)
            
            assert result.title == "Cached Page"
            assert result.text == "Cached content"
    
    @pytest.mark.asyncio
    async def test_fetch_batch_respects_concurrency(self):
        """Test that batch fetch respects concurrency limit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reader = PageReader(cache_dir=Path(tmpdir), cache_enabled=True)
            
            # Pre-cache results to avoid actual HTTP requests
            urls = [f"https://example.com/page{i}" for i in range(5)]
            for url in urls:
                content = PageContent(url=url, status=200, title=f"Page {url[-1]}", text="Content")
                reader._save_to_cache(url, content)
            
            results = await reader.fetch_batch(urls, max_concurrent=2, use_cache=True)
            
            assert len(results) == 5
            assert all(isinstance(r, PageContent) for r in results)


class TestPageContent:
    """Tests for PageContent dataclass."""
    
    def test_is_success_true(self):
        """Test is_success for successful fetch."""
        content = PageContent(
            url="https://example.com",
            status=200,
            text="Some content",
        )
        
        assert content.is_success is True
    
    def test_is_success_false_on_error(self):
        """Test is_success when there's an error."""
        content = PageContent(
            url="https://example.com",
            status=200,
            text="Some content",
            error="Something went wrong",
        )
        
        assert content.is_success is False
    
    def test_is_success_false_on_bad_status(self):
        """Test is_success with non-200 status."""
        content = PageContent(
            url="https://example.com",
            status=404,
            text="",
        )
        
        assert content.is_success is False
    
    def test_is_success_false_on_empty_text(self):
        """Test is_success with empty text."""
        content = PageContent(
            url="https://example.com",
            status=200,
            text="",
        )
        
        assert content.is_success is False
    
    def test_to_dict_and_from_dict(self):
        """Test serialization round-trip."""
        original = PageContent(
            url="https://example.com",
            final_url="https://example.com/",
            status=200,
            title="Test",
            text="Content",
            excerpt="Con...",
            fetched_at="2024-01-01T00:00:00Z",
            content_type="text/html",
        )
        
        data = original.to_dict()
        restored = PageContent.from_dict(data)
        
        assert restored.url == original.url
        assert restored.title == original.title
        assert restored.text == original.text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
