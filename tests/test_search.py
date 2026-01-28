"""
Manual test script for the SearchClient.

Run with: python tests/test_search.py

This script tests:
1. Basic search functionality with 5 relevant queries
2. Cache functionality (second run of same query should be cached)
3. Result structure and formatting
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from agents.search_client import SearchClient, SearchError
from config.settings import validate_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Test queries relevant to competitive analysis
TEST_QUERIES = [
    "Stripe unique value proposition",
    "Venmo market share 2024",
    "Apple Pay number of users",
    "Cash App business model revenue",
    "PayPal vs Stripe comparison",
]


def print_separator(title: str = "") -> None:
    """Print a visual separator."""
    if title:
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}")
    else:
        print("-" * 60)


def print_result(result) -> None:
    """Print a search result in a readable format."""
    print(f"\nQuery: {result.query}")
    print(f"Results: {result.total_results} | Time: {result.search_time:.2f}s | Cached: {result.cached}")
    print(f"Timestamp: {result.timestamp}")
    print_separator()
    
    for i, item in enumerate(result.items[:5], 1):  # Show top 5 results
        print(f"\n  [{i}] {item.title}")
        print(f"      URL: {item.url}")
        print(f"      {item.snippet[:150]}..." if len(item.snippet) > 150 else f"      {item.snippet}")


def test_basic_search(client: SearchClient) -> bool:
    """Test basic search functionality with all test queries."""
    print_separator("TEST 1: Basic Search Functionality")
    
    all_passed = True
    
    for query in TEST_QUERIES:
        try:
            print(f"\nSearching: '{query}'...")
            result = client.search_sync(query, num_results=10)
            print_result(result)
            
            if result.total_results == 0:
                print(f"  WARNING: No results returned for '{query}'")
                
        except SearchError as e:
            print(f"\n  FAILED: {e.message}")
            all_passed = False
        except Exception as e:
            print(f"\n  ERROR: Unexpected error - {e}")
            all_passed = False
    
    return all_passed


def test_caching(client: SearchClient) -> bool:
    """Test that caching works correctly."""
    print_separator("TEST 2: Caching Functionality")
    
    test_query = TEST_QUERIES[0]  # Use first query
    
    try:
        # First search (might already be cached from test 1)
        print(f"\nFirst search for: '{test_query}'")
        result1 = client.search_sync(test_query, num_results=10)
        print(f"  Cached: {result1.cached}")
        
        # Second search (should definitely be cached now)
        print(f"\nSecond search for: '{test_query}'")
        result2 = client.search_sync(test_query, num_results=10)
        print(f"  Cached: {result2.cached}")
        
        if result2.cached:
            print("\n  SUCCESS: Second search returned cached result")
            return True
        else:
            print("\n  FAILED: Second search was not cached")
            return False
            
    except SearchError as e:
        print(f"\n  FAILED: {e.message}")
        return False
    except Exception as e:
        print(f"\n  ERROR: Unexpected error - {e}")
        return False


def test_result_structure(client: SearchClient) -> bool:
    """Test that results have the expected structure."""
    print_separator("TEST 3: Result Structure Validation")
    
    test_query = TEST_QUERIES[0]
    
    try:
        result = client.search_sync(test_query, num_results=5)
        
        # Check SearchResult fields
        checks = [
            ("query", hasattr(result, "query") and result.query == test_query),
            ("items", hasattr(result, "items") and isinstance(result.items, list)),
            ("total_results", hasattr(result, "total_results") and isinstance(result.total_results, int)),
            ("search_time", hasattr(result, "search_time") and isinstance(result.search_time, float)),
            ("cached", hasattr(result, "cached") and isinstance(result.cached, bool)),
            ("timestamp", hasattr(result, "timestamp") and isinstance(result.timestamp, str)),
        ]
        
        all_passed = True
        for field_name, passed in checks:
            status = "OK" if passed else "FAIL"
            print(f"  {field_name}: {status}")
            if not passed:
                all_passed = False
        
        # Check SearchResultItem fields (if we have results)
        if result.items:
            item = result.items[0]
            item_checks = [
                ("item.title", hasattr(item, "title") and isinstance(item.title, str)),
                ("item.url", hasattr(item, "url") and isinstance(item.url, str)),
                ("item.snippet", hasattr(item, "snippet") and isinstance(item.snippet, str)),
                ("item.position", hasattr(item, "position") and isinstance(item.position, int)),
            ]
            
            print("\n  SearchResultItem fields:")
            for field_name, passed in item_checks:
                status = "OK" if passed else "FAIL"
                print(f"    {field_name}: {status}")
                if not passed:
                    all_passed = False
        
        return all_passed
        
    except SearchError as e:
        print(f"\n  FAILED: {e.message}")
        return False
    except Exception as e:
        print(f"\n  ERROR: Unexpected error - {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("  CompetelyClone Search Layer Tests")
    print("="*60)
    
    # Validate configuration
    print_separator("Configuration Check")
    errors = validate_config()
    if errors:
        for error in errors:
            print(f"  ERROR: {error}")
        print("\n  Please configure your .env file and try again.")
        print("  Copy .env.example to .env and add your API keys.")
        sys.exit(1)
    print("  Configuration OK")
    
    # Initialize client
    client = SearchClient()
    
    # Run tests
    results = {
        "Basic Search": test_basic_search(client),
        "Caching": test_caching(client),
        "Result Structure": test_result_structure(client),
    }
    
    # Summary
    print_separator("TEST SUMMARY")
    all_passed = True
    for test_name, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("  All tests PASSED!")
        sys.exit(0)
    else:
        print("  Some tests FAILED. Check output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
