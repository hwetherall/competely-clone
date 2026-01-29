"""Quick integration test for Jina Reader with Research Agent."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.research_agent import ResearchAgent
from agents.page_reader import create_page_reader


async def test_jina_page_reader():
    """Test Jina Reader standalone."""
    print("=" * 60)
    print("Testing Jina Reader (Standalone)")
    print("=" * 60)
    
    reader = create_page_reader(cache_enabled=False, fetch_mode="auto")
    print(f"PageReader mode: {reader.fetch_mode}")
    print(f"Jina URL: {reader.jina_base_url}")
    print(f"Jina API key set: {bool(reader.jina_api_key)}")
    
    # Test with a real URL
    test_url = "https://stripe.com/docs/payments"
    print(f"\nFetching: {test_url}")
    
    result = await reader.fetch(test_url, use_cache=False)
    
    print(f"\nResult:")
    print(f"  Status: {result.status}")
    print(f"  Success: {result.is_success}")
    print(f"  Title: {result.title}")
    print(f"  Content length: {len(result.text):,} chars")
    if result.error:
        print(f"  Error: {result.error}")
    else:
        print(f"  Excerpt: {result.excerpt[:200]}...")
    
    return result.is_success


async def test_research_with_jina():
    """Test Research Agent with Jina Reader."""
    print("\n" + "=" * 60)
    print("Testing Research Agent with Jina Reader")
    print("=" * 60)
    
    agent = ResearchAgent(
        max_iterations=1,
        min_iterations=1,
        skip_evaluation=True,
    )
    
    print(f"PageReader mode: {agent.page_reader.fetch_mode}")
    print(f"Page fetch enabled: {agent.enable_page_fetch}")
    print()
    
    # Run a quick research task
    result = await agent.research("Stripe", "unique_value_proposition")
    
    print(f"\nResult:")
    print(f"  Confidence: {result.confidence}")
    print(f"  Iterations: {result.iterations}")
    print(f"  Sources: {len(result.sources)}")
    
    if result.metadata:
        print(f"  Pages fetched: {result.metadata.get('pages_fetched', 0)}")
        print(f"  Pages failed: {result.metadata.get('pages_failed', 0)}")
        print(f"  Evidence chars: {result.metadata.get('total_evidence_chars', 0):,}")
    
    print(f"\nConcise ({len(result.concise)} chars):")
    print(f"  {result.concise}")
    
    print(f"\nComprehensive preview ({len(result.comprehensive)} chars total):")
    print(f"  {result.comprehensive[:500]}...")
    
    return result


async def main():
    # Test standalone Jina Reader
    jina_ok = await test_jina_page_reader()
    
    if not jina_ok:
        print("\n[WARNING] Jina Reader test failed, but continuing...")
    
    # Test full research flow
    result = await test_research_with_jina()
    
    print("\n" + "=" * 60)
    print("Integration Test Complete!")
    print("=" * 60)
    
    if result.metadata and result.metadata.get("pages_fetched", 0) > 0:
        print("\n[SUCCESS] Research Agent successfully used Jina Reader to fetch web content.")
    else:
        print("\n[INFO] Research completed but no pages were fetched.")


if __name__ == "__main__":
    asyncio.run(main())
