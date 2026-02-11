"""
Multi-Company Competitive Analysis.

Run with:
    python main.py                                    # Default: 5 companies, normal mode
    python main.py --fast                             # Fast mode (skip evaluation)
    python main.py --companies Stripe PayPal          # Custom companies
    python main.py --concurrency 5                    # Increase parallelism

Generates a 5x20 competitive analysis grid (5 companies × 20 variables = 100 research cells).
"""

import sys
import json
import asyncio
import argparse
import time
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
from typing import List, Tuple, Optional, Dict

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import logging
from agents.research_agent import ResearchAgent, ResearchResult
from agents.variable_generator import generate_variables as generate_variables_impl
from config.settings import validate_config
from config.variables import (
    VARIABLES,
    VariableDefinition,
    get_all_variable_ids,
    get_always_variables,
    get_sometimes_variables,
    get_variable,
)

# Default companies for competitive analysis
DEFAULT_COMPANIES = ["Stripe", "PayPal", "Venmo", "Apple Pay", "Cash App"]

# Configure logging
# Set to DEBUG to see query generation details, WARNING for quiet output
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Multi-company competitive analysis using research agents."
    )
    parser.add_argument(
        "--companies",
        nargs="+",
        default=DEFAULT_COMPANIES,
        help=f"List of companies to analyze (default: {', '.join(DEFAULT_COMPANIES)})"
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=3,
        help="Maximum concurrent research tasks (default: 3)"
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Fast mode: single iteration, skip evaluation"
    )
    parser.add_argument(
        "--no-dynamic-vars",
        action="store_true",
        help="Use only static variables (skip AI-generated parameters for this competitor set)"
    )
    return parser.parse_args()


def create_results_dir() -> Path:
    """Ensure results directory exists."""
    results_dir = project_root / "data" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    return results_dir


def format_time(seconds: float) -> str:
    """Format seconds into human-readable time."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


async def research_with_semaphore(
    semaphore: asyncio.Semaphore,
    agent: ResearchAgent,
    company: str,
    variable_id: str,
    task_index: int,
    total_tasks: int,
    start_time: float,
    completed_count: List[int],  # Mutable list to track progress
    variable_lookup: Optional[dict] = None,
) -> Tuple[str, str, ResearchResult]:
    """
    Execute a single research task with semaphore-based rate limiting.
    
    Args:
        semaphore: Asyncio semaphore for concurrency control
        agent: ResearchAgent instance
        company: Company name
        variable_id: Variable ID to research
        task_index: Index of this task (for progress display)
        total_tasks: Total number of tasks
        start_time: Start time of the entire run
        completed_count: Mutable list [count] for tracking completion
        
    Returns:
        Tuple of (company, variable_id, ResearchResult)
    """
    async with semaphore:
        # Print progress
        elapsed = time.time() - start_time
        completed = completed_count[0]
        
        if completed > 0:
            avg_time = elapsed / completed
            remaining = (total_tasks - completed) * avg_time
            eta = f", ETA: {format_time(remaining)}"
        else:
            eta = ""
        
        var_name = variable_id
        if variable_lookup and variable_id in variable_lookup:
            var_name = variable_lookup[variable_id].name
        print(f"[{completed + 1:3}/{total_tasks}] {company} - {var_name}...{eta}")
        
        try:
            result = await agent.research(company, variable_id)
            completed_count[0] += 1
            return (company, variable_id, result)
        except Exception as e:
            logger.error(f"Research failed for {company} - {variable_id}: {e}")
            completed_count[0] += 1
            # Return error result
            error_result = ResearchResult(
                company=company,
                variable_id=variable_id,
                variable_name=variable_id,  # Will be replaced with proper name
                concise=f"Error: {str(e)[:100]}",
                comprehensive=f"Research failed with error: {str(e)}",
                sources=[],
                confidence="none",
                iterations=0,
                total_searches=0,
                timestamp=datetime.now(timezone.utc).isoformat(),
                error=str(e),
            )
            return (company, variable_id, error_result)


async def run_multi_company_analysis(
    companies: List[str],
    concurrency: int = 3,
    fast_mode: bool = False,
    generate_vars: bool = True,
) -> dict:
    """
    Run competitive analysis across multiple companies.

    Args:
        companies: List of company names to analyze
        concurrency: Maximum concurrent research tasks
        fast_mode: If True, use fast mode (single iteration, skip evaluation)
        generate_vars: If True and len(companies) >= 2, generate dynamic parameters via LLM

    Returns:
        Tuple of (output dict, errors list)
    """
    variable_ids: List[str] = []
    variable_lookup: Optional[Dict[str, VariableDefinition]] = None
    variable_definitions: Optional[dict] = None

    if generate_vars and len(companies) >= 2:
        print("\n  Analyzing competitor set and generating smart parameters...")
        try:
            gen_result = await generate_variables_impl(companies)
            print(f"  Industry context: {gen_result.industry_context}")
            always_ids = [v.id for v in get_always_variables()]
            tier2_included = [r.variable_id for r in gen_result.tier2_recommendations if r.include]
            generated_ids = [v.id for v in gen_result.generated_variables]
            variable_ids = always_ids + tier2_included + generated_ids
            variable_lookup = {}
            for v in get_always_variables():
                variable_lookup[v.id] = v
            for var_id in tier2_included:
                variable_lookup[var_id] = get_variable(var_id)
            for v in gen_result.generated_variables:
                variable_lookup[v.id] = v
            variable_definitions = {vid: {"id": v.id, "name": v.name, "category": v.category} for vid, v in variable_lookup.items()}
            print(f"  Parameters: {len(always_ids)} always + {len(tier2_included)} contextual + {len(generated_ids)} industry-specific = {len(variable_ids)} total")
            for v in gen_result.generated_variables[:5]:
                print(f"    - {v.name}")
            if len(gen_result.generated_variables) > 5:
                print(f"    ... and {len(gen_result.generated_variables) - 5} more")
        except Exception as e:
            logger.warning("Variable generation failed, using static variables: %s", e)
            generate_vars = False

    if not variable_ids:
        variable_ids = get_all_variable_ids()
        variable_definitions = {v.id: {"id": v.id, "name": v.name, "category": v.category} for v in VARIABLES}

    print("\n" + "=" * 70)
    print("  Multi-Company Competitive Analysis")
    print("=" * 70)
    print(f"\n  Companies: {', '.join(companies)}")
    print(f"  Variables: {len(variable_ids)}")
    print(f"  Total cells: {len(companies) * len(variable_ids)}")
    print(f"  Concurrency: {concurrency}")
    print(f"  Mode: {'Fast' if fast_mode else 'Normal'}")
    print()

    if fast_mode:
        agent = ResearchAgent(
            max_iterations=1,
            min_iterations=1,
            skip_evaluation=True,
            variable_lookup=variable_lookup,
        )
    else:
        agent = ResearchAgent(variable_lookup=variable_lookup)

    semaphore = asyncio.Semaphore(concurrency)
    start_time = time.time()
    completed_count = [0]
    total_tasks = len(companies) * len(variable_ids)

    tasks = []
    task_index = 0
    for company in companies:
        for var_id in variable_ids:
            task = research_with_semaphore(
                semaphore=semaphore,
                agent=agent,
                company=company,
                variable_id=var_id,
                task_index=task_index,
                total_tasks=total_tasks,
                start_time=start_time,
                completed_count=completed_count,
                variable_lookup=variable_lookup,
            )
            tasks.append(task)
            task_index += 1

    print("Starting research...\n")
    results = await asyncio.gather(*tasks, return_exceptions=True)

    elapsed_time = time.time() - start_time
    print(f"\n  Completed in {format_time(elapsed_time)}")

    grid = {company: {} for company in companies}
    errors = []
    for result in results:
        if isinstance(result, Exception):
            errors.append(str(result))
            continue
        company, variable_id, research_result = result
        grid[company][variable_id] = research_result.to_dict()
        if research_result.error:
            errors.append(f"{company}/{variable_id}: {research_result.error}")

    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "companies": companies,
        "variables": variable_ids,
        "grid": grid,
        "metadata": {
            "total_cells": total_tasks,
            "successful_cells": total_tasks - len(errors),
            "failed_cells": len(errors),
            "elapsed_seconds": elapsed_time,
            "concurrency": concurrency,
            "fast_mode": fast_mode,
        },
    }
    if variable_definitions is not None:
        output["variable_definitions"] = variable_definitions

    return output, errors


def save_results(output: dict) -> Path:
    """
    Save results to JSON file.
    
    Args:
        output: Output dictionary with grid structure
        
    Returns:
        Path to saved file
    """
    results_dir = create_results_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"comparison_{timestamp}.json"
    filepath = results_dir / filename
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    return filepath


def print_summary(output: dict, errors: List[str]):
    """Print summary statistics."""
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    
    metadata = output["metadata"]
    companies = output["companies"]
    grid = output["grid"]
    
    print(f"\n  Results:")
    print(f"    Total cells:     {metadata['total_cells']}")
    print(f"    Successful:      {metadata['successful_cells']}")
    print(f"    Failed:          {metadata['failed_cells']}")
    print(f"    Elapsed time:    {format_time(metadata['elapsed_seconds'])}")
    
    # Per-company breakdown
    print(f"\n  Per-Company Results:")
    for company in companies:
        company_results = grid.get(company, {})
        success = sum(1 for v in company_results.values() if not v.get("error"))
        total = len(company_results)
        confidence_counts = Counter(v.get("confidence", "none") for v in company_results.values())
        high_conf = confidence_counts.get("high", 0)
        print(f"    {company:15} {success:2}/{total} successful, {high_conf} high confidence")
    
    # Errors
    if errors:
        print(f"\n  Errors ({len(errors)}):")
        for error in errors[:5]:  # Show first 5 errors
            print(f"    - {error[:70]}...")
        if len(errors) > 5:
            print(f"    ... and {len(errors) - 5} more")


async def main():
    """Main entry point."""
    args = parse_args()
    
    # Validate configuration
    print("\n" + "=" * 70)
    print("  Configuration Check")
    print("=" * 70)
    
    errors = validate_config(require_llm=True)
    if errors:
        for error in errors:
            print(f"  ERROR: {error}")
        print("\n  Please configure your .env file with:")
        print("  - SERPER_API_KEY")
        print("  - ATLAS_CLOUD_API")
        print("  - OPENROUTER_API_KEY")
        sys.exit(1)
    print("  Configuration OK")
    
    # Run analysis
    output, errors = await run_multi_company_analysis(
        companies=args.companies,
        concurrency=args.concurrency,
        fast_mode=args.fast,
        generate_vars=not args.no_dynamic_vars,
    )
    
    # Save results
    filepath = save_results(output)
    print(f"\n  Results saved to: {filepath}")
    
    # Print summary
    print_summary(output, errors)
    
    # Exit status
    success_rate = output["metadata"]["successful_cells"] / output["metadata"]["total_cells"]
    
    print("\n" + "=" * 70)
    if success_rate >= 0.95:
        print("  Analysis completed successfully!")
        sys.exit(0)
    elif success_rate >= 0.8:
        print(f"  Analysis mostly successful ({success_rate*100:.0f}% cells completed)")
        sys.exit(0)
    else:
        print(f"  Analysis had issues ({success_rate*100:.0f}% cells completed)")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
