"""
V2 Relational Competitive Intelligence Engine - Pipeline entry point.

Runs the 4-phase pipeline: Gather -> Normalize -> Synthesize -> Executive,
then saves JSON and generates the HTML report.

Usage:
    python v2_pipeline.py --companies Stripe PayPal Square "Cash App" Venmo
    python v2_pipeline.py --companies Lime Bird Voi --fast
    python v2_pipeline.py --concurrency 5
"""

import sys
import json
import asyncio
import argparse
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import logging
from agents.gather_agent import GatherAgent
from agents.normalize_agent import NormalizeAgent
from agents.synthesis_agent import SynthesisAgent
from agents.executive_agent import ExecutiveAgent
from agents.v2_schemas import (
    IntelligenceDossier,
    NormalizedDataset,
    ComparativeReport,
    ExecutiveBrief,
    V2RunResult,
)
from agents.variable_generator import generate_variables as generate_variables_impl
from config.settings import validate_config
from config.variables import (
    VARIABLES,
    VariableDefinition,
    get_all_variable_ids,
    get_always_variables,
    get_variable,
)

logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_COMPANIES = ["Stripe", "PayPal", "Venmo", "Apple Pay", "Cash App"]


def parse_args():
    parser = argparse.ArgumentParser(
        description="V2 Relational Competitive Intelligence Engine."
    )
    parser.add_argument(
        "--companies",
        nargs="+",
        default=DEFAULT_COMPANIES,
        help=f"Companies to analyze (default: {', '.join(DEFAULT_COMPANIES)})",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=3,
        help="Max concurrent tasks (default: 3)",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Fast mode: single gather iteration, skip evaluation",
    )
    parser.add_argument(
        "--no-dynamic-vars",
        action="store_true",
        help="Use only static variables (skip AI-generated parameters)",
    )
    parser.add_argument(
        "--max-parameters",
        type=int,
        default=None,
        help="Limit number of parameters (for testing; default: all)",
    )
    return parser.parse_args()


def format_time(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds / 60:.1f}m"
    return f"{seconds / 3600:.1f}h"


def create_results_dir() -> Path:
    results_dir = project_root / "data" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    return results_dir


async def gather_one(
    semaphore: asyncio.Semaphore,
    agent: GatherAgent,
    company: str,
    variable_id: str,
    total: int,
    completed: List[int],
    start: float,
    variable_lookup: Optional[Dict[str, VariableDefinition]],
) -> tuple[str, str, IntelligenceDossier]:
    async with semaphore:
        completed[0] += 1
        n = completed[0]
        var_name = variable_lookup.get(variable_id).name if variable_lookup and variable_id in variable_lookup else variable_id
        print(f"  [Gather {n}/{total}] {company} - {var_name}...")
        try:
            dossier = await agent.gather(company, variable_id)
            return (company, variable_id, dossier)
        except Exception as e:
            logger.error(f"Gather failed {company} - {variable_id}: {e}")
            return (
                company,
                variable_id,
                IntelligenceDossier(
                    company=company,
                    parameter_id=variable_id,
                    parameter_name=var_name,
                    facts=[],
                    key_metrics={},
                    raw_passages=[],
                    sources=[],
                    confidence="none",
                    metadata={"error": str(e)},
                ),
            )


async def run_v2_analysis(
    companies: List[str],
    concurrency: int = 3,
    fast_mode: bool = False,
    generate_vars: bool = True,
    max_parameters: Optional[int] = None,
) -> V2RunResult:
    variable_ids: List[str] = []
    variable_lookup: Dict[str, VariableDefinition] = {}
    variable_definitions: Dict[str, Dict[str, Any]] = {}

    if generate_vars and len(companies) >= 2:
        print("\n  Analyzing competitor set and generating smart parameters...")
        try:
            gen_result = await generate_variables_impl(companies)
            print(f"  Industry context: {gen_result.industry_context}")
            always_ids = [v.id for v in get_always_variables()]
            tier2_included = [r.variable_id for r in gen_result.tier2_recommendations if r.include]
            generated_ids = [v.id for v in gen_result.generated_variables]
            variable_ids = always_ids + tier2_included + generated_ids
            for v in get_always_variables():
                variable_lookup[v.id] = v
            for var_id in tier2_included:
                variable_lookup[var_id] = get_variable(var_id)
            for v in gen_result.generated_variables:
                variable_lookup[v.id] = v
            variable_definitions = {vid: {"id": v.id, "name": v.name, "category": v.category} for vid, v in variable_lookup.items()}
            print(f"  Parameters: {len(variable_ids)} total")
        except Exception as e:
            logger.warning("Variable generation failed, using static: %s", e)
            generate_vars = False

    if not variable_ids:
        variable_ids = get_all_variable_ids()
        for v in VARIABLES:
            variable_lookup[v.id] = v
        variable_definitions = {v.id: {"id": v.id, "name": v.name, "category": v.category} for v in VARIABLES}

    if max_parameters is not None and len(variable_ids) > max_parameters:
        variable_ids = variable_ids[:max_parameters]
        variable_definitions = {k: v for k, v in variable_definitions.items() if k in variable_ids}

    print("\n" + "=" * 70)
    print("  V2 Relational Competitive Intelligence Engine")
    print("=" * 70)
    print(f"\n  Companies: {', '.join(companies)}")
    print(f"  Parameters: {len(variable_ids)}")
    print(f"  Mode: {'Fast' if fast_mode else 'Normal'}")
    print()

    gather_agent = GatherAgent(
        max_iterations=1 if fast_mode else 3,
        min_iterations=1,
        skip_evaluation=fast_mode,
        variable_lookup=variable_lookup,
    )
    normalize_agent = NormalizeAgent()
    synthesis_agent = SynthesisAgent(variable_lookup=variable_lookup)
    executive_agent = ExecutiveAgent()

    # Phase 1: Gather
    total_gather = len(companies) * len(variable_ids)
    semaphore = asyncio.Semaphore(concurrency)
    start_time = time.time()
    completed_count = [0]
    tasks = [
        gather_one(
            semaphore,
            gather_agent,
            company,
            var_id,
            total_gather,
            completed_count,
            start_time,
            variable_lookup,
        )
        for company in companies
        for var_id in variable_ids
    ]
    print("Phase 1: Gather\n")
    gather_results = await asyncio.gather(*tasks, return_exceptions=True)
    phase1_elapsed = time.time() - start_time
    print(f"\n  Phase 1 completed in {format_time(phase1_elapsed)}")

    intelligence: Dict[str, Dict[str, Dict[str, Any]]] = {c: {} for c in companies}
    for r in gather_results:
        if isinstance(r, Exception):
            logger.error("Gather task failed: %s", r)
            continue
        company, variable_id, dossier = r
        intelligence[company][variable_id] = dossier.to_dict()

    # Phase 2: Normalize (per parameter)
    print("\nPhase 2: Normalize\n")
    phase2_start = time.time()
    datasets: Dict[str, NormalizedDataset] = {}
    for i, var_id in enumerate(variable_ids):
        var = variable_lookup.get(var_id) or get_variable(var_id)
        research_prompt = var.research_prompt.format(company="each company")
        dossiers_by_company = {}
        for company in companies:
            d_dict = intelligence.get(company, {}).get(var_id)
            if d_dict:
                dossiers_by_company[company] = IntelligenceDossier.from_dict(d_dict)
        if dossiers_by_company:
            print(f"  [{i + 1}/{len(variable_ids)}] {var.name}...")
            datasets[var_id] = await normalize_agent.normalize(
                var_id,
                var.name,
                research_prompt,
                dossiers_by_company,
            )
        else:
            datasets[var_id] = NormalizedDataset(
                parameter_id=var_id,
                parameter_name=var.name,
                raw_dossiers={},
            )
    phase2_elapsed = time.time() - phase2_start
    print(f"\n  Phase 2 completed in {format_time(phase2_elapsed)}")

    # Phase 3: Synthesize (per parameter)
    print("\nPhase 3: Synthesize\n")
    phase3_start = time.time()
    analyses: Dict[str, Dict[str, Any]] = {}
    for i, var_id in enumerate(variable_ids):
        var = variable_lookup.get(var_id) or get_variable(var_id)
        research_prompt = var.research_prompt.format(company="each company")
        norm = datasets.get(var_id)
        if not norm or not norm.company_data:
            analyses[var_id] = ComparativeReport(
                parameter_id=var_id,
                parameter_name=var.name,
                headline="Insufficient data.",
                executive_summary="",
                confidence="none",
            ).to_dict()
            continue
        print(f"  [{i + 1}/{len(variable_ids)}] {var.name}...")
        try:
            report = await synthesis_agent.synthesize(norm, research_prompt)
            analyses[var_id] = report.to_dict()
        except Exception as e:
            logger.error("Synthesis failed for %s: %s", var_id, e)
            analyses[var_id] = ComparativeReport(
                parameter_id=var_id,
                parameter_name=var.name,
                headline="Synthesis failed.",
                executive_summary="",
                confidence="none",
            ).to_dict()
    phase3_elapsed = time.time() - phase3_start
    print(f"\n  Phase 3 completed in {format_time(phase3_elapsed)}")

    # Phase 4: Executive
    print("\nPhase 4: Executive brief\n")
    phase4_start = time.time()
    reports_for_exec = []
    for var_id in variable_ids:
        a = analyses.get(var_id)
        if a:
            reports_for_exec.append(ComparativeReport.from_dict(a))
    companies_list = ", ".join(companies)
    executive = await executive_agent.synthesize_brief(companies_list, reports_for_exec)
    phase4_elapsed = time.time() - phase4_start
    print(f"  Phase 4 completed in {format_time(phase4_elapsed)}")

    total_elapsed = time.time() - start_time
    run_id = f"v2_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    result = V2RunResult(
        run_id=run_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        companies=companies,
        parameters=variable_ids,
        parameter_definitions=variable_definitions,
        intelligence=intelligence,
        analyses=analyses,
        executive=executive.to_dict(),
        metadata={
            "phase1_elapsed_seconds": phase1_elapsed,
            "phase2_elapsed_seconds": phase2_elapsed,
            "phase3_elapsed_seconds": phase3_elapsed,
            "phase4_elapsed_seconds": phase4_elapsed,
            "total_elapsed_seconds": total_elapsed,
            "concurrency": concurrency,
            "fast_mode": fast_mode,
        },
    )
    return result


def save_v2_result(result: V2RunResult) -> Path:
    results_dir = create_results_dir()
    filepath = results_dir / f"{result.run_id}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
    print(f"\n  Results saved: {filepath}")
    return filepath


async def main():
    args = parse_args()
    print("\n" + "=" * 70)
    print("  Configuration Check")
    print("=" * 70)
    errors = validate_config(require_llm=True)
    if errors:
        for e in errors:
            print(f"  ERROR: {e}")
        sys.exit(1)
    print("  Configuration OK")

    result = await run_v2_analysis(
        companies=args.companies,
        concurrency=args.concurrency,
        fast_mode=args.fast,
        generate_vars=not args.no_dynamic_vars,
        max_parameters=args.max_parameters,
    )

    json_path = save_v2_result(result)

    # Generate HTML report
    try:
        from utils.generate_v2_report import generate_v2_html
        generate_v2_html(result.to_dict(), json_path.with_suffix(".html"))
        print(f"  HTML report: {json_path.with_suffix('.html')}")
    except Exception as e:
        logger.warning("Could not generate HTML report: %s", e)

    print("\n" + "=" * 70)
    print("  V2 pipeline complete.")
    print("=" * 70)
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
