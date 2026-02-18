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
from typing import List, Dict, Any, Optional, Callable

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import logging
from agents.gather_agent import GatherAgent
from agents.normalize_agent import NormalizeAgent
from agents.synthesis_agent import SynthesisAgent
from agents.research_synthesis_agent import ResearchSynthesisAgent
from agents.executive_agent import ExecutiveAgent
from agents.postmortem_agent import PostMortemAgent
from agents.risk_overlay_agent import RiskOverlayAgent
from agents.v2_schemas import (
    IntelligenceDossier,
    NormalizedDataset,
    ComparativeReport,
    ExecutiveBrief,
    PostMortemBrief,
    GraveyardCompany,
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
    variable_lookup: Optional[Dict[str, VariableDefinition]],
    progress_callback: Optional[Callable[[str, int, int, Optional[str]], None]] = None,
) -> tuple[str, str, IntelligenceDossier]:
    var_name = variable_lookup.get(variable_id).name if variable_lookup and variable_id in variable_lookup else variable_id
    async with semaphore:
        n = completed[0] + 1
        print(f"  [Gather {n}/{total}] {company} - {var_name}...")
        try:
            dossier = await agent.gather(company, variable_id)
            completed[0] += 1
            if progress_callback:
                progress_callback("gather", completed[0], total, f"{company} - {var_name}")
            return (company, variable_id, dossier)
        except Exception as e:
            completed[0] += 1
            if progress_callback:
                progress_callback("gather", completed[0], total, f"{company} - {var_name}")
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
    variable_ids_override: Optional[List[str]] = None,
    variable_lookup_override: Optional[Dict[str, VariableDefinition]] = None,
    run_id_override: Optional[str] = None,
    progress_callback: Optional[Callable[[str, int, int, Optional[str]], None]] = None,
    venture_context: str = "",
    key_questions: Optional[List[str]] = None,
    hypothesis: str = "",
    graveyard_companies: Optional[List[str]] = None,
    industry_context: str = "",
    parameter_path: str = "competely",
) -> V2RunResult:
    variable_ids: List[str] = []
    variable_lookup: Dict[str, VariableDefinition] = {}
    variable_definitions: Dict[str, Dict[str, Any]] = {}

    if variable_ids_override is not None and variable_lookup_override is not None:
        variable_ids = list(variable_ids_override)
        variable_lookup = dict(variable_lookup_override)
        variable_definitions = {vid: {"id": v.id, "name": v.name, "category": v.category} for vid, v in variable_lookup.items()}
    elif generate_vars and len(companies) >= 2:
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
    research_synthesis_agent = ResearchSynthesisAgent()
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
            variable_lookup,
            progress_callback,
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

    # Phase 2: Normalize (per parameter, parallel)
    if progress_callback:
        progress_callback("normalize", total_gather, total_gather, "Starting normalize...")
    print("\nPhase 2: Normalize\n")
    phase2_start = time.time()
    datasets: Dict[str, NormalizedDataset] = {}

    async def normalize_one(var_id: str, idx: int) -> tuple[str, NormalizedDataset]:
        var = variable_lookup.get(var_id) or get_variable(var_id)
        research_prompt = var.research_prompt.format(company="each company")
        dossiers_by_company = {}
        for company in companies:
            d_dict = intelligence.get(company, {}).get(var_id)
            if d_dict:
                dossiers_by_company[company] = IntelligenceDossier.from_dict(d_dict)
        if dossiers_by_company:
            print(f"  [{idx + 1}/{len(variable_ids)}] {var.name}...")
            result = await normalize_agent.normalize(
                var_id,
                var.name,
                research_prompt,
                dossiers_by_company,
                parameter_context=getattr(var, "parameter_context", None),
            )
            return (var_id, result)
        return (var_id, NormalizedDataset(
            parameter_id=var_id,
            parameter_name=var.name,
            raw_dossiers={},
        ))

    norm_sem = asyncio.Semaphore(concurrency)

    async def normalize_one_throttled(var_id: str, idx: int) -> tuple[str, NormalizedDataset]:
        async with norm_sem:
            return await normalize_one(var_id, idx)

    norm_results = await asyncio.gather(
        *(normalize_one_throttled(vid, i) for i, vid in enumerate(variable_ids)),
        return_exceptions=True,
    )
    for r in norm_results:
        if isinstance(r, Exception):
            logger.error("Normalize task failed: %s", r)
            continue
        var_id, dataset = r
        datasets[var_id] = dataset
    phase2_elapsed = time.time() - phase2_start
    print(f"\n  Phase 2 completed in {format_time(phase2_elapsed)}")

    # Phase 3: Synthesize (per parameter)
    if progress_callback:
        progress_callback("synthesize", total_gather, total_gather, "Starting synthesize...")
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
            report = await synthesis_agent.synthesize(
                norm,
                research_prompt,
                parameter_context=getattr(var, "parameter_context", None),
            )
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

    # Phase 3.5: Research Synthesis
    if progress_callback:
        progress_callback("research_synthesis", total_gather, total_gather, "Synthesizing research findings...")
    print("\nPhase 3.5: Research Synthesis\n")
    phase35_start = time.time()
    
    reports_for_synthesis = []
    for var_id in variable_ids:
        a = analyses.get(var_id)
        if a:
            reports_for_synthesis.append(ComparativeReport.from_dict(a))
            
    companies_list = ", ".join(companies)
    research_synthesis = await research_synthesis_agent.synthesize(
        companies_list, 
        reports_for_synthesis, 
        key_questions or [], 
        hypothesis
    )
    phase35_elapsed = time.time() - phase35_start
    print(f"  Phase 3.5 completed in {format_time(phase35_elapsed)}")

    # Phase 4: Executive
    if progress_callback:
        progress_callback("executive", total_gather, total_gather, "Generating executive brief...")
    print("\nPhase 4: Executive brief\n")
    phase4_start = time.time()
    reports_for_exec = []
    for var_id in variable_ids:
        a = analyses.get(var_id)
        if a:
            reports_for_exec.append(ComparativeReport.from_dict(a))
    companies_list = ", ".join(companies)
    executive = await executive_agent.synthesize_brief(companies_list, reports_for_exec, venture_context=venture_context, parameter_path=parameter_path)
    phase4_elapsed = time.time() - phase4_start
    print(f"  Phase 4 completed in {format_time(phase4_elapsed)}")

    # =========================================================================
    # Graveyard Track (if enabled)
    # =========================================================================
    gy_companies_data: List[Dict[str, Any]] = []
    gy_intelligence: Dict[str, Dict[str, Dict[str, Any]]] = {}
    gy_analyses: Dict[str, Dict[str, Any]] = {}
    postmortem_dict: Dict[str, Any] = {}
    gy_elapsed = 0.0

    if graveyard_companies and len(graveyard_companies) > 0:
        from agents.graveyard_variable_generator import generate_graveyard_variables

        gy_start = time.time()
        print("\n" + "=" * 70)
        print("  Graveyard Track: Post-Mortem Intelligence")
        print("=" * 70)

        # Phase 0G: Generate graveyard variables
        if progress_callback:
            progress_callback("graveyard_vars", 0, 0, "Generating failure-focused parameters...")
        print("\n  Phase 0G: Generating graveyard parameters...")
        try:
            gy_vars = await generate_graveyard_variables(
                dead_companies=graveyard_companies,
                industry_context=industry_context,
                living_companies=companies,
            )
            gy_variable_ids = [v.id for v in gy_vars]
            gy_variable_lookup: Dict[str, VariableDefinition] = {v.id: v for v in gy_vars}
            print(f"  Generated {len(gy_variable_ids)} graveyard parameters")
        except Exception as e:
            logger.warning("Graveyard variable generation failed: %s", e)
            gy_variable_ids = []
            gy_variable_lookup = {}

        if gy_variable_ids:
            # Phase 1G: Gather (graveyard)
            gy_gather_total = len(graveyard_companies) * len(gy_variable_ids)
            gy_completed_count = [0]
            if progress_callback:
                progress_callback("graveyard_gather", 0, gy_gather_total, "Starting graveyard gather...")
            print(f"\n  Phase 1G: Gather ({gy_gather_total} tasks)\n")

            gy_gather_agent = GatherAgent(
                max_iterations=1 if fast_mode else 2,
                min_iterations=1,
                skip_evaluation=fast_mode,
                variable_lookup=gy_variable_lookup,
            )

            gy_tasks = [
                gather_one(
                    semaphore,
                    gy_gather_agent,
                    company,
                    var_id,
                    gy_gather_total,
                    gy_completed_count,
                    gy_variable_lookup,
                    lambda phase, c, t, cur: progress_callback("graveyard_gather", c, t, cur) if progress_callback else None,
                )
                for company in graveyard_companies
                for var_id in gy_variable_ids
            ]
            gy_gather_results = await asyncio.gather(*gy_tasks, return_exceptions=True)

            gy_intelligence = {c: {} for c in graveyard_companies}
            for r in gy_gather_results:
                if isinstance(r, Exception):
                    logger.error("Graveyard gather task failed: %s", r)
                    continue
                company, variable_id, dossier = r
                gy_intelligence[company][variable_id] = dossier.to_dict()

            # Phase 2G: Normalize (graveyard)
            if progress_callback:
                progress_callback("graveyard_normalize", 0, len(gy_variable_ids), "Normalizing graveyard data...")
            print("\n  Phase 2G: Normalize (graveyard)\n")

            gy_datasets: Dict[str, NormalizedDataset] = {}
            normalize_agent_gy = NormalizeAgent()

            async def gy_normalize_one(var_id: str, idx: int) -> tuple[str, NormalizedDataset]:
                var = gy_variable_lookup[var_id]
                research_prompt = var.research_prompt.format(company="each company")
                dossiers_by_company = {}
                for company in graveyard_companies:
                    d_dict = gy_intelligence.get(company, {}).get(var_id)
                    if d_dict:
                        dossiers_by_company[company] = IntelligenceDossier.from_dict(d_dict)
                if dossiers_by_company:
                    print(f"    [{idx + 1}/{len(gy_variable_ids)}] {var.name}...")
                    result = await normalize_agent_gy.normalize(
                        var_id, var.name, research_prompt, dossiers_by_company
                    )
                    return (var_id, result)
                return (var_id, NormalizedDataset(
                    parameter_id=var_id, parameter_name=var.name, raw_dossiers={},
                ))

            gy_norm_sem = asyncio.Semaphore(concurrency)

            async def gy_normalize_throttled(var_id: str, idx: int):
                async with gy_norm_sem:
                    return await gy_normalize_one(var_id, idx)

            gy_norm_results = await asyncio.gather(
                *(gy_normalize_throttled(vid, i) for i, vid in enumerate(gy_variable_ids)),
                return_exceptions=True,
            )
            for r in gy_norm_results:
                if isinstance(r, Exception):
                    logger.error("Graveyard normalize failed: %s", r)
                    continue
                var_id, dataset = r
                gy_datasets[var_id] = dataset

            # Phase 3G: Synthesize (graveyard, failure-lens)
            if progress_callback:
                progress_callback("graveyard_synthesize", 0, len(gy_variable_ids), "Synthesizing failure patterns...")
            print("\n  Phase 3G: Synthesize (graveyard)\n")

            from agents.synthesis_agent import SynthesisAgent as GySynthAgent
            gy_synthesis_agent = GySynthAgent(variable_lookup=gy_variable_lookup)
            # Override prompts for failure lens
            import agents.v2_prompts as gy_prompts
            original_draft_sys = gy_prompts.SYNTHESIS_DRAFT_SYSTEM
            original_draft_prompt = gy_prompts.SYNTHESIS_DRAFT_PROMPT
            gy_prompts.SYNTHESIS_DRAFT_SYSTEM = gy_prompts.GRAVEYARD_SYNTHESIS_DRAFT_SYSTEM
            gy_prompts.SYNTHESIS_DRAFT_PROMPT = gy_prompts.GRAVEYARD_SYNTHESIS_DRAFT_PROMPT

            for i, var_id in enumerate(gy_variable_ids):
                var = gy_variable_lookup[var_id]
                research_prompt = var.research_prompt.format(company="each company")
                norm = gy_datasets.get(var_id)
                if not norm or not norm.company_data:
                    gy_analyses[var_id] = ComparativeReport(
                        parameter_id=var_id, parameter_name=var.name,
                        headline="Insufficient data.", executive_summary="", confidence="none",
                    ).to_dict()
                    continue
                print(f"    [{i + 1}/{len(gy_variable_ids)}] {var.name}...")
                try:
                    report = await gy_synthesis_agent.synthesize(norm, research_prompt)
                    gy_analyses[var_id] = report.to_dict()
                except Exception as e:
                    logger.error("Graveyard synthesis failed for %s: %s", var_id, e)
                    gy_analyses[var_id] = ComparativeReport(
                        parameter_id=var_id, parameter_name=var.name,
                        headline="Synthesis failed.", executive_summary="", confidence="none",
                    ).to_dict()

            # Restore original prompts
            gy_prompts.SYNTHESIS_DRAFT_SYSTEM = original_draft_sys
            gy_prompts.SYNTHESIS_DRAFT_PROMPT = original_draft_prompt

            # Phase 4G: Post-Mortem Brief
            if progress_callback:
                progress_callback("postmortem_brief", 0, 0, "Generating post-mortem brief...")
            print("\n  Phase 4G: Post-Mortem Brief\n")

            postmortem_agent = PostMortemAgent()
            gy_reports = [
                ComparativeReport.from_dict(a) for a in gy_analyses.values() if a
            ]
            dead_list = ", ".join(graveyard_companies)
            living_list = ", ".join(companies)
            pm_brief = await postmortem_agent.synthesize_brief(
                dead_companies_list=dead_list,
                living_companies_list=living_list,
                reports=gy_reports,
                industry_context=industry_context,
                venture_context=venture_context,
            )

            # Phase 5: Risk Overlay Merge
            if progress_callback:
                progress_callback("risk_overlay", 0, 0, "Generating risk overlays...")
            print("\n  Phase 5: Risk Overlay Merge\n")

            overlay_agent = RiskOverlayAgent()
            risk_overlays = await overlay_agent.generate_overlays(executive, pm_brief)
            pm_brief.risk_overlays = risk_overlays
            postmortem_dict = pm_brief.to_dict()

            gy_companies_data = [
                {"name": c} for c in graveyard_companies
            ]

            gy_elapsed = time.time() - gy_start
            print(f"\n  Graveyard track completed in {format_time(gy_elapsed)}")

    total_elapsed = time.time() - start_time
    run_id = run_id_override or f"v2_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    result = V2RunResult(
        run_id=run_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        companies=companies,
        parameters=variable_ids,
        parameter_definitions=variable_definitions,
        intelligence=intelligence,
        analyses=analyses,
        executive=executive.to_dict(),
        research_synthesis=research_synthesis.to_dict(),
        metadata={
            "phase1_elapsed_seconds": phase1_elapsed,
            "phase2_elapsed_seconds": phase2_elapsed,
            "phase3_elapsed_seconds": phase3_elapsed,
            "phase35_elapsed_seconds": phase35_elapsed,
            "phase4_elapsed_seconds": phase4_elapsed,
            "graveyard_elapsed_seconds": gy_elapsed,
            "total_elapsed_seconds": total_elapsed,
            "concurrency": concurrency,
            "fast_mode": fast_mode,
            "graveyard_enabled": bool(graveyard_companies),
            "parameter_path": parameter_path,
        },
        graveyard_companies=gy_companies_data,
        graveyard_intelligence=gy_intelligence,
        graveyard_analyses=gy_analyses,
        postmortem_brief=postmortem_dict,
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
