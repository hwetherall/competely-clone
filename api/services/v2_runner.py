"""
V2 pipeline runner for the API. Runs the relational competitive intelligence
pipeline with progress tracking so the frontend can poll status.
"""

import sys
import json
import asyncio
import time
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

RESULTS_DIR = project_root / "data" / "results"


def _build_variable_lookup(
    variable_ids: List[str],
    dynamic_variables: Optional[List[Dict[str, Any]]] = None,
    parameter_contexts: Optional[Dict[str, str]] = None,
):
    """Build variable_id -> VariableDefinition for V2 pipeline."""
    from dataclasses import replace
    from config.variables import VariableDefinition, get_variable

    lookup = {}
    dynamic_by_id = {d["id"]: d for d in (dynamic_variables or [])}
    for var_id in variable_ids:
        if var_id in dynamic_by_id:
            d = dynamic_by_id[var_id]
            v = VariableDefinition(
                id=d["id"],
                name=d["name"],
                category=d["category"],
                research_prompt=d["research_prompt"],
                example_queries=list(d.get("example_queries", [])),
                answer_spec=list(d.get("answer_spec", [])),
                preferred_source_types=list(d.get("preferred_source_types", [])),
                key_terms=list(d.get("key_terms", [])),
                max_concise_chars=int(d.get("max_concise_chars", 200)),
                tier="dynamic",
            )
        else:
            v = get_variable(var_id)
        if parameter_contexts and var_id in parameter_contexts and parameter_contexts[var_id]:
            v = replace(v, parameter_context=parameter_contexts[var_id])
        lookup[var_id] = v
    return lookup


class V2Runner:
    """Runs the V2 pipeline with progress file updates."""

    def __init__(self):
        self.progress_file: Optional[Path] = None
        self.run_id: str = ""
        self.start_time: float = 0
        self.started_at: str = ""

    def _update_progress(
        self,
        phase: str,
        status: str = "running",
        completed: int = 0,
        total: int = 0,
        current: Optional[str] = None,
    ):
        if not self.progress_file:
            return
        elapsed = time.time() - self.start_time
        data = {
            "run_id": self.run_id,
            "status": status,
            "phase": phase,
            "completed": completed,
            "total": total,
            "current": current,
            "elapsed_seconds": elapsed,
            "started_at": self.started_at,
        }
        try:
            with open(self.progress_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"V2 progress write failed: {e}")

    def run_sync(
        self,
        run_id: str,
        companies: List[str],
        variables: List[str],
        dynamic_variables: Optional[List[Dict[str, Any]]] = None,
        parameter_contexts: Optional[Dict[str, str]] = None,
        concurrency: int = 3,
        fast_mode: bool = False,
        venture_context: str = "",
        key_questions: Optional[List[str]] = None,
        hypothesis: str = "",
        graveyard_companies: Optional[List[str]] = None,
        industry_context: str = "",
    ):
        """Entry point for BackgroundTasks: run V2 pipeline and save result."""
        asyncio.run(self._run(
            run_id=run_id,
            companies=companies,
            variables=variables,
            dynamic_variables=dynamic_variables,
            parameter_contexts=parameter_contexts,
            concurrency=concurrency,
            fast_mode=fast_mode,
            venture_context=venture_context,
            key_questions=key_questions,
            hypothesis=hypothesis,
            graveyard_companies=graveyard_companies,
            industry_context=industry_context,
        ))

    async def _run(
        self,
        run_id: str,
        companies: List[str],
        variables: List[str],
        dynamic_variables: Optional[List[Dict[str, Any]]] = None,
        parameter_contexts: Optional[Dict[str, str]] = None,
        concurrency: int = 3,
        fast_mode: bool = False,
        venture_context: str = "",
        key_questions: Optional[List[str]] = None,
        hypothesis: str = "",
        graveyard_companies: Optional[List[str]] = None,
        industry_context: str = "",
    ):
        from v2_pipeline import (
            run_v2_analysis,
            save_v2_result,
        )
        from agents.v2_schemas import V2RunResult

        self.run_id = run_id
        self.progress_file = RESULTS_DIR / f"progress_{run_id}.json"
        self.start_time = time.time()
        self.started_at = datetime.now().isoformat()
        variable_lookup = _build_variable_lookup(
            variables, dynamic_variables, parameter_contexts
        )
        total_cells = len(companies) * len(variables)

        self._update_progress("gather", status="running", completed=0, total=total_cells, current="Starting gather...")

        def on_progress(phase: str, completed: int, total: int, current: Optional[str]) -> None:
            self._update_progress(phase, status="running", completed=completed, total=total, current=current)

        try:
            result = await run_v2_analysis(
                companies=companies,
                concurrency=concurrency,
                fast_mode=fast_mode,
                generate_vars=False,
                variable_ids_override=variables,
                variable_lookup_override=variable_lookup,
                run_id_override=run_id,
                progress_callback=on_progress,
                venture_context=venture_context,
                key_questions=key_questions,
                hypothesis=hypothesis,
                graveyard_companies=graveyard_companies,
                industry_context=industry_context,
            )
            save_v2_result(result)
            self._update_progress(
                "completed",
                status="completed",
                completed=total_cells,
                total=total_cells,
                current=None,
            )
        except Exception as e:
            self._update_progress(
                "failed",
                status="failed",
                completed=0,
                total=total_cells,
                current=str(e),
            )
            raise
