"""
Full Column Test for Research Agent.

Run with: python tests/test_full_column.py

Tests all 20 research variables for Stripe and saves results.

Expected runtime: 10-20 minutes depending on API response times.
"""

import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime
from collections import Counter

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from agents.research_agent import ResearchAgent, ResearchResult
from config.settings import validate_config
from config.variables import VARIABLES, get_variables_by_category

# Configure logging (less verbose for full run)
logging.basicConfig(
    level=logging.WARNING,  # Only warnings and errors
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_results_dir() -> Path:
    """Ensure results directory exists."""
    results_dir = project_root / "data" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    return results_dir


def format_preview(text: str, max_len: int = 70) -> str:
    """Format text for preview display."""
    if not text:
        return "(empty)"
    # Remove newlines and collapse spaces
    clean = " ".join(text.split())
    if len(clean) > max_len:
        return clean[:max_len-3] + "..."
    return clean


async def run_full_column(company: str = "Stripe"):
    """
    Run research for all 20 variables for a given company.
    
    Args:
        company: Company name to research (default: Stripe)
        
    Returns:
        List of ResearchResult objects
    """
    print("\n" + "=" * 70)
    print(f"  Full Column Test: {company}")
    print("=" * 70)
    print(f"\n  Running all {len(VARIABLES)} research variables...")
    print(f"  Estimated time: 10-20 minutes\n")
    
    agent = ResearchAgent()
    results = []
    
    total = len(VARIABLES)
    
    for idx, variable in enumerate(VARIABLES, 1):
        print(f"[{idx:2}/{total}] {variable.name}...")
        
        try:
            result = await agent.research(company, variable.id)
            results.append(result)
            
            # Determine status
            if result.error:
                status = "Error"
            elif len(result.concise) > 20 and result.confidence != "none":
                status = "Success"
            else:
                status = "Partial"
            
            # Print result summary
            confidence = result.confidence or "none"
            iterations = result.iterations
            preview = format_preview(result.concise)
            
            print(f"       {status:8} | {confidence:6} confidence | {iterations} iterations")
            print(f"       Summary: {preview}")
            
        except Exception as e:
            print(f"       Error: {e}")
            # Create error result
            error_result = ResearchResult(
                company=company,
                variable_id=variable.id,
                variable_name=variable.name,
                concise="Error: Research failed",
                comprehensive=f"Research failed with error: {str(e)}",
                sources=[],
                confidence="none",
                iterations=0,
                total_searches=0,
                timestamp=datetime.utcnow().isoformat(),
                error=str(e),
            )
            results.append(error_result)
        
        print()  # Blank line between variables
    
    return results


def save_results(results: list, company: str) -> Path:
    """
    Save results to JSON file.
    
    Args:
        results: List of ResearchResult objects
        company: Company name for filename
        
    Returns:
        Path to saved file
    """
    results_dir = create_results_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{company.lower()}_{timestamp}.json"
    filepath = results_dir / filename
    
    # Convert results to dict
    data = {
        "company": company,
        "timestamp": datetime.utcnow().isoformat(),
        "total_variables": len(results),
        "results": [r.to_dict() for r in results]
    }
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    return filepath


def print_summary(results: list):
    """Print summary statistics."""
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    
    # Count success/fail
    success = 0
    partial = 0
    failed = 0
    
    for result in results:
        if result.error:
            failed += 1
        elif len(result.concise) > 20 and result.confidence != "none":
            success += 1
        else:
            partial += 1
    
    total = len(results)
    
    print(f"\n  Results:")
    print(f"    Success: {success}/{total} ({success/total*100:.0f}%)")
    print(f"    Partial: {partial}/{total}")
    print(f"    Failed:  {failed}/{total}")
    
    # Confidence distribution
    confidence_counts = Counter(r.confidence for r in results)
    print(f"\n  Confidence Distribution:")
    for conf in ["high", "medium", "low", "none"]:
        count = confidence_counts.get(conf, 0)
        bar = "█" * count + "░" * (total - count)
        print(f"    {conf:6}: {bar} {count}")
    
    # Average iterations
    avg_iterations = sum(r.iterations for r in results) / total
    avg_searches = sum(r.total_searches for r in results) / total
    print(f"\n  Averages:")
    print(f"    Iterations per variable: {avg_iterations:.1f}")
    print(f"    Searches per variable:   {avg_searches:.1f}")
    
    # Check for markdown in concise summaries
    markdown_issues = []
    for result in results:
        if any(marker in result.concise for marker in ["###", "**", "- ", "* "]):
            markdown_issues.append(result.variable_name)
    
    if markdown_issues:
        print(f"\n  WARNING: Markdown detected in summaries:")
        for var in markdown_issues:
            print(f"    - {var}")
    else:
        print(f"\n  Markdown check: PASSED (no formatting in summaries)")


async def main():
    """Run full column test."""
    # Check configuration
    print("\n" + "=" * 70)
    print("  Configuration Check")
    print("=" * 70)
    
    errors = validate_config(require_openrouter=True)
    if errors:
        for error in errors:
            print(f"  ERROR: {error}")
        print("\n  Please configure your .env file with:")
        print("  - SERPER_API_KEY")
        print("  - OPENROUTER_API_KEY")
        sys.exit(1)
    print("  Configuration OK")
    
    # Run full column test
    company = "Stripe"
    results = await run_full_column(company)
    
    # Save results
    filepath = save_results(results, company)
    print(f"\n  Results saved to: {filepath}")
    
    # Print summary
    print_summary(results)
    
    # Exit status
    success_count = sum(
        1 for r in results 
        if not r.error and len(r.concise) > 20 and r.confidence != "none"
    )
    
    print("\n" + "=" * 70)
    if success_count == len(results):
        print("  All variables completed successfully!")
        sys.exit(0)
    elif success_count > len(results) * 0.8:
        print(f"  Mostly successful ({success_count}/{len(results)} variables)")
        sys.exit(0)
    else:
        print(f"  Multiple failures ({len(results) - success_count}/{len(results)} issues)")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
