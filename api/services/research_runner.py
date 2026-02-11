"""
Research runner service that wraps the existing research agent
with progress tracking for the API.
"""

import sys
import json
import asyncio
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

# Ensure project root is in path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from agents.research_agent import ResearchAgent, ResearchResult
from config.variables import VARIABLES, get_variable, VariableDefinition

# Results directory
RESULTS_DIR = project_root / "data" / "results"


def _build_variable_lookup(
    variable_ids: List[str],
    dynamic_variables: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, VariableDefinition]:
    """Build variable_id -> VariableDefinition from static config and optional dynamic definitions."""
    lookup: Dict[str, VariableDefinition] = {}
    dynamic_by_id = {d["id"]: d for d in (dynamic_variables or [])}
    for var_id in variable_ids:
        if var_id in dynamic_by_id:
            d = dynamic_by_id[var_id]
            lookup[var_id] = VariableDefinition(
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
            lookup[var_id] = get_variable(var_id)
    return lookup


class ResearchRunner:
    """
    Service for running research with progress tracking.
    
    Writes progress to a JSON file that can be polled by the API.
    """
    
    def __init__(self):
        self.progress_file: Path = None
        self.run_id: str = None
        self.start_time: float = 0
        self.completed_count: int = 0
        self.total_count: int = 0
        self.recent_activity: List[dict] = []
    
    def run_research_sync(
        self,
        run_id: str,
        companies: List[str],
        variables: List[str],
        dynamic_variables: Optional[List[Dict[str, Any]]] = None,
        concurrency: int = 3,
        fast_mode: bool = False,
    ):
        """
        Synchronous wrapper for run_research to use with BackgroundTasks.
        """
        asyncio.run(self.run_research(
            run_id=run_id,
            companies=companies,
            variables=variables,
            dynamic_variables=dynamic_variables,
            concurrency=concurrency,
            fast_mode=fast_mode,
        ))
    
    def _update_progress(
        self,
        status: str = "running",
        current: dict = None,
        completed_result: dict = None,
    ):
        """Update the progress file with current state."""
        if not self.progress_file:
            return
        
        elapsed = time.time() - self.start_time
        
        # Calculate ETA
        estimated_remaining = None
        if self.completed_count > 0:
            avg_time = elapsed / self.completed_count
            remaining_tasks = self.total_count - self.completed_count
            estimated_remaining = avg_time * remaining_tasks
        
        # Add to recent activity if we have a completed result
        if completed_result:
            self.recent_activity.append({
                "company": completed_result.get("company", ""),
                "variable": completed_result.get("variable", ""),
                "confidence": completed_result.get("confidence", "none"),
                "timestamp": datetime.now().isoformat(),
                "status": "completed" if not completed_result.get("error") else "failed",
            })
            # Keep only last 20 activity items
            self.recent_activity = self.recent_activity[-20:]
        
        progress_data = {
            "run_id": self.run_id,
            "status": status,
            "total": self.total_count,
            "completed": self.completed_count,
            "current": current,
            "elapsed_seconds": elapsed,
            "estimated_remaining_seconds": estimated_remaining,
            "recent_activity": self.recent_activity,
        }
        
        try:
            with open(self.progress_file, "w", encoding="utf-8") as f:
                json.dump(progress_data, f, indent=2)
        except Exception as e:
            print(f"Failed to update progress file: {e}")
    
    async def _research_with_progress(
        self,
        semaphore: asyncio.Semaphore,
        agent: ResearchAgent,
        company: str,
        variable_id: str,
        variable_lookup: Dict[str, VariableDefinition],
    ) -> tuple:
        """Execute a single research task with progress updates."""
        async with semaphore:
            # Update progress with current task
            variable = variable_lookup[variable_id]
            self._update_progress(
                status="running",
                current={
                    "company": company,
                    "variable": variable.name,
                    "step": "Researching...",
                },
            )
            
            try:
                result = await agent.research(company, variable_id)
                self.completed_count += 1
                
                # Update progress with completed result
                self._update_progress(
                    status="running",
                    completed_result={
                        "company": company,
                        "variable": variable.name,
                        "confidence": result.confidence,
                    },
                )
                
                return (company, variable_id, result)
            except Exception as e:
                self.completed_count += 1
                
                # Create error result
                error_result = ResearchResult(
                    company=company,
                    variable_id=variable_id,
                    variable_name=variable.name,
                    concise=f"Error: {str(e)[:100]}",
                    comprehensive=f"Research failed with error: {str(e)}",
                    sources=[],
                    confidence="none",
                    iterations=0,
                    total_searches=0,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    error=str(e),
                )
                
                # Update progress with error
                self._update_progress(
                    status="running",
                    completed_result={
                        "company": company,
                        "variable": variable.name,
                        "confidence": "none",
                        "error": str(e),
                    },
                )
                
                return (company, variable_id, error_result)
    
    async def run_research(
        self,
        run_id: str,
        companies: List[str],
        variables: List[str],
        dynamic_variables: Optional[List[Dict[str, Any]]] = None,
        concurrency: int = 3,
        fast_mode: bool = False,
    ):
        """
        Run research across companies and variables with progress tracking.

        Args:
            run_id: Unique identifier for this run
            companies: List of company names
            variables: List of variable IDs
            dynamic_variables: Optional list of full definitions for dynamic (Tier 3) variables
            concurrency: Max concurrent tasks
            fast_mode: Use fast mode (single iteration)
        """
        self.run_id = run_id
        self.progress_file = RESULTS_DIR / f"progress_{run_id}.json"
        self.start_time = time.time()
        self.completed_count = 0
        self.total_count = len(companies) * len(variables)
        self.recent_activity = []

        variable_lookup = _build_variable_lookup(variables, dynamic_variables)

        # Initialize progress
        self._update_progress(status="running")

        try:
            # Create agent with variable lookup so dynamic variables are resolved
            if fast_mode:
                agent = ResearchAgent(
                    max_iterations=1,
                    min_iterations=1,
                    skip_evaluation=True,
                    variable_lookup=variable_lookup,
                )
            else:
                agent = ResearchAgent(variable_lookup=variable_lookup)

            # Create semaphore for rate limiting
            semaphore = asyncio.Semaphore(concurrency)

            # Create all tasks
            tasks = []
            for company in companies:
                for var_id in variables:
                    task = self._research_with_progress(
                        semaphore=semaphore,
                        agent=agent,
                        company=company,
                        variable_id=var_id,
                        variable_lookup=variable_lookup,
                    )
                    tasks.append(task)
            
            # Execute all tasks
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Build grid structure
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
            
            # Build output; include variable_definitions for dynamic variables so UI can display names
            elapsed_time = time.time() - self.start_time
            variable_definitions = {
                var_id: {
                    "id": v.id,
                    "name": v.name,
                    "category": v.category,
                }
                for var_id, v in variable_lookup.items()
            }
            output = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "companies": companies,
                "variables": variables,
                "variable_definitions": variable_definitions,
                "grid": grid,
                "metadata": {
                    "total_cells": self.total_count,
                    "successful_cells": self.total_count - len(errors),
                    "failed_cells": len(errors),
                    "elapsed_seconds": elapsed_time,
                    "concurrency": concurrency,
                    "fast_mode": fast_mode,
                },
            }
            
            # Save results
            result_filepath = RESULTS_DIR / f"{run_id}.json"
            with open(result_filepath, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
            
            # Update progress to completed
            self._update_progress(status="completed")
            
            # Clean up progress file (optional - keep for history)
            # self.progress_file.unlink(missing_ok=True)
            
        except Exception as e:
            # Update progress to failed
            self._update_progress(status="failed")
            raise
