"""
Test script for the Research Agent.

Run with: python tests/test_research_agent.py

Tests:
1. Single research task (Stripe + Unique Value Proposition)
2. Query generation
3. Full research flow
4. Output structure validation
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from agents.research_agent import ResearchAgent, ResearchResult
from agents.llm_client import LLMClient
from config.settings import validate_config
from config.variables import get_variable, VARIABLES

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def print_separator(title: str = "") -> None:
    """Print a visual separator."""
    if title:
        print(f"\n{'='*70}")
        print(f"  {title}")
        print(f"{'='*70}")
    else:
        print("-" * 70)


def print_result(result: ResearchResult) -> None:
    """Print a research result in a readable format."""
    print(f"\nCompany: {result.company}")
    print(f"Variable: {result.variable_name}")
    print(f"Iterations: {result.iterations}")
    print(f"Total Searches: {result.total_searches}")
    print(f"Confidence: {result.confidence}")
    print(f"Timestamp: {result.timestamp}")
    
    if result.error:
        print(f"\nERROR: {result.error}")
        return
    
    print_separator()
    print("\nCONCISE SUMMARY:")
    print(result.concise)
    
    print_separator()
    print("\nCOMPREHENSIVE ANALYSIS:")
    # Show first 800 chars to keep output manageable
    if len(result.comprehensive) > 800:
        print(result.comprehensive[:800] + "...")
    else:
        print(result.comprehensive)
    
    print_separator()
    print(f"\nSOURCES ({len(result.sources)} total):")
    for i, src in enumerate(result.sources[:5], 1):
        print(f"  [{i}] {src.title[:60]}...")
        print(f"      {src.url}")


def test_single_research():
    """Test a single research task: Stripe + Unique Value Proposition."""
    print_separator("TEST 1: Single Research Task")
    print("\nResearching: Stripe - Unique Value Proposition")
    print("This may take 30-60 seconds...\n")
    
    agent = ResearchAgent()
    result = agent.research_sync("Stripe", "unique_value_proposition")
    
    print_result(result)
    
    # Validate result structure
    print_separator()
    print("\nRESULT STRUCTURE VALIDATION:")
    checks = [
        ("company", result.company == "Stripe"),
        ("variable_id", result.variable_id == "unique_value_proposition"),
        ("variable_name", result.variable_name == "Unique Value Proposition"),
        ("concise (non-empty)", len(result.concise) > 10),
        ("comprehensive (non-empty)", len(result.comprehensive) > 50),
        ("sources (has some)", len(result.sources) > 0),
        ("confidence (valid)", result.confidence in ("high", "medium", "low", "none")),
        ("iterations (positive)", result.iterations > 0),
    ]
    
    all_passed = True
    for check_name, passed in checks:
        status = "OK" if passed else "FAIL"
        print(f"  {check_name}: {status}")
        if not passed:
            all_passed = False
    
    return all_passed


def test_llm_connection():
    """Test that LLM connection works."""
    print_separator("TEST 2: LLM Connection Test")
    
    try:
        client = LLMClient()
        response = client.complete_simple_sync(
            prompt="What is 2+2? Reply with just the number.",
            temperature=0.1,
            max_tokens=10,
        )
        print(f"  LLM Response: {response.strip()}")
        print("  LLM Connection: OK")
        return True
    except Exception as e:
        print(f"  LLM Error: {e}")
        print("  LLM Connection: FAILED")
        return False


def test_variable_definitions():
    """Test that variable definitions are properly loaded."""
    print_separator("TEST 3: Variable Definitions")
    
    print(f"  Total variables defined: {len(VARIABLES)}")
    
    # Test getting a specific variable
    try:
        var = get_variable("market_share")
        print(f"  Sample variable: {var.name}")
        print(f"  Category: {var.category}")
        print(f"  Example queries: {len(var.example_queries)}")
        print("  Variable Definitions: OK")
        return True
    except Exception as e:
        print(f"  Error: {e}")
        print("  Variable Definitions: FAILED")
        return False


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("  CompetelyClone Research Agent Tests")
    print("="*70)
    
    # Check configuration
    print_separator("Configuration Check")
    errors = validate_config(require_openrouter=True)
    if errors:
        for error in errors:
            print(f"  ERROR: {error}")
        print("\n  Please configure your .env file with both API keys:")
        print("  - SERPER_API_KEY")
        print("  - OPENROUTER_API_KEY")
        sys.exit(1)
    print("  Configuration OK")
    
    # Run tests
    results = {}
    
    # Test 1: Variable definitions (no API needed)
    results["Variable Definitions"] = test_variable_definitions()
    
    # Test 2: LLM connection
    results["LLM Connection"] = test_llm_connection()
    
    # Test 3: Full research (only if LLM works)
    if results["LLM Connection"]:
        results["Single Research"] = test_single_research()
    else:
        print_separator("TEST 3: Single Research - SKIPPED (LLM not working)")
        results["Single Research"] = False
    
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
