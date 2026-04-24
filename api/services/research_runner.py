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

from agents.research_agent import ResearchAgent, ResearchResult, ResearchSource
from agents.llm_client import LLMClient
from config.innovera_profile import INNOVERA_PROFILE
from config.variables import VARIABLES, get_variable, VariableDefinition

# Results directory
RESULTS_DIR = project_root / "data" / "results"


def _build_variable_lookup(
    variable_ids: List[str],
    dynamic_variables: Optional[List[Dict[str, Any]]] = None,
    parameter_path: str = "competely",
) -> Dict[str, VariableDefinition]:
    """Build variable_id -> VariableDefinition from static config and optional dynamic definitions."""
    lookup: Dict[str, VariableDefinition] = {}
    dynamic_by_id = {d["id"]: d for d in (dynamic_variables or [])}
    static_lookups = []
    if parameter_path == "avis":
        from config.avis_variables import get_avis_variable
        static_lookups.append(get_avis_variable)
    if parameter_path == "innovera":
        from config.innovera_variables import get_innovera_variable
        static_lookups.append(get_innovera_variable)
    static_lookups.append(get_variable)

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
            for get_static_variable in static_lookups:
                try:
                    lookup[var_id] = get_static_variable(var_id)
                    break
                except ValueError:
                    continue
            if var_id not in lookup:
                raise ValueError(f"Unknown variable: {var_id}")
    return lookup


INNOVERA_TAKEAWAY_ID = "inv_takeaway_for_innovera"


def _is_innovera_takeaway_requested(variables: List[str], parameter_path: str) -> bool:
    return parameter_path == "innovera" and INNOVERA_TAKEAWAY_ID in variables


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
        parameter_path: str = "competely",
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
            parameter_path=parameter_path,
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

    async def _run_innovera_takeaway_postpass(
        self,
        companies: List[str],
        grid: Dict[str, Dict[str, Any]],
        variable_lookup: Dict[str, VariableDefinition],
        errors: List[str],
    ) -> None:
        """Create the Innovera takeaway after the evidence-bearing cells finish."""
        variable = variable_lookup[INNOVERA_TAKEAWAY_ID]
        client = LLMClient()

        for company in companies:
            self._update_progress(
                status="running",
                current={
                    "company": company,
                    "variable": variable.name,
                    "step": "Synthesizing Innovera takeaway...",
                },
            )
            try:
                prior_cells = {
                    var_id: cell
                    for var_id, cell in grid.get(company, {}).items()
                    if var_id != INNOVERA_TAKEAWAY_ID and not cell.get("error")
                }
                prompt = self._build_innovera_takeaway_prompt(company, prior_cells)
                comprehensive = await client.complete_simple(
                    prompt=prompt,
                    system_prompt=(
                        "You are a strategy partner advising Innovera. "
                        "Use only the supplied research summaries. Be concrete, action-oriented, and careful about uncertainty."
                    ),
                    temperature=0.25,
                    max_tokens=1800,
                )
                concise = await client.complete_simple(
                    prompt=(
                        f"Compress this Innovera takeaway for {company} into <= {variable.max_concise_chars} characters. "
                        "Keep the action and threat signal.\n\n"
                        f"{comprehensive}"
                    ),
                    temperature=0.2,
                    max_tokens=120,
                )
                concise = concise.strip()
                if len(concise) > variable.max_concise_chars:
                    concise = concise[: variable.max_concise_chars - 3].rstrip() + "..."

                sources = self._collect_sources(prior_cells)
                result = ResearchResult(
                    company=company,
                    variable_id=INNOVERA_TAKEAWAY_ID,
                    variable_name=variable.name,
                    concise=concise,
                    comprehensive=comprehensive.strip(),
                    sources=sources,
                    confidence="medium" if prior_cells else "low",
                    iterations=0,
                    total_searches=sum(int(c.get("total_searches", 0)) for c in prior_cells.values()),
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    metadata={"post_pass": True, "source_variables": list(prior_cells.keys())},
                )
                grid[company][INNOVERA_TAKEAWAY_ID] = result.to_dict()
                self.completed_count += 1
                self._update_progress(
                    status="running",
                    completed_result={
                        "company": company,
                        "variable": variable.name,
                        "confidence": result.confidence,
                    },
                )
            except Exception as e:
                self.completed_count += 1
                errors.append(f"{company}/{INNOVERA_TAKEAWAY_ID}: {e}")
                error_result = ResearchResult(
                    company=company,
                    variable_id=INNOVERA_TAKEAWAY_ID,
                    variable_name=variable.name,
                    concise=f"Error: {str(e)[:100]}",
                    comprehensive=f"Innovera takeaway post-pass failed: {str(e)}",
                    sources=[],
                    confidence="none",
                    iterations=0,
                    total_searches=0,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    error=str(e),
                    metadata={"post_pass": True},
                )
                grid[company][INNOVERA_TAKEAWAY_ID] = error_result.to_dict()
                self._update_progress(
                    status="running",
                    completed_result={
                        "company": company,
                        "variable": variable.name,
                        "confidence": "none",
                        "error": str(e),
                    },
                )

    @staticmethod
    def _build_innovera_takeaway_prompt(company: str, prior_cells: Dict[str, Dict[str, Any]]) -> str:
        sections = []
        for var_id, cell in prior_cells.items():
            sections.append(
                "\n".join([
                    f"## {cell.get('variable_name', var_id)}",
                    f"Concise: {cell.get('concise', '')}",
                    f"Comprehensive: {cell.get('comprehensive', '')[:4000]}",
                ])
            )
        research_block = "\n\n".join(sections) if sections else "No prior cells produced usable evidence."
        return f"""Innovera profile:
{INNOVERA_PROFILE}

Competitor: {company}

Prior Innovera-lens research:
{research_block}

Write the post-pass "Takeaway for Innovera" for this competitor. Include:
1. What Innovera should copy or test.
2. What Innovera should avoid.
3. What Innovera should worry about competitively.
4. The single next experiment Innovera should run.

Ground the answer in the supplied prior research. If evidence is missing, name the validation gap."""

    @staticmethod
    def _collect_sources(prior_cells: Dict[str, Dict[str, Any]]) -> List[ResearchSource]:
        seen_urls = set()
        sources: List[ResearchSource] = []
        for cell in prior_cells.values():
            for raw in cell.get("sources", []):
                url = raw.get("url", "")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                sources.append(ResearchSource(
                    title=raw.get("title", ""),
                    url=url,
                    snippet=raw.get("snippet", ""),
                    query=raw.get("query", ""),
                    domain=raw.get("domain", ""),
                    source_score=float(raw.get("source_score", 0.5) or 0.5),
                    is_official=bool(raw.get("is_official", False)),
                ))
                if len(sources) >= 12:
                    return sources
        return sources
    
    async def run_research(
        self,
        run_id: str,
        companies: List[str],
        variables: List[str],
        dynamic_variables: Optional[List[Dict[str, Any]]] = None,
        concurrency: int = 3,
        fast_mode: bool = False,
        parameter_path: str = "competely",
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
            parameter_path: Static parameter framework for variable lookup
        """
        self.run_id = run_id
        self.progress_file = RESULTS_DIR / f"progress_{run_id}.json"
        self.start_time = time.time()
        self.completed_count = 0
        self.total_count = len(companies) * len(variables)
        self.recent_activity = []

        variable_lookup = _build_variable_lookup(variables, dynamic_variables, parameter_path)
        takeaway_requested = _is_innovera_takeaway_requested(variables, parameter_path)
        research_variables = [
            var_id for var_id in variables
            if not (takeaway_requested and var_id == INNOVERA_TAKEAWAY_ID)
        ]

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
                for var_id in research_variables:
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

            if takeaway_requested:
                await self._run_innovera_takeaway_postpass(
                    companies=companies,
                    grid=grid,
                    variable_lookup=variable_lookup,
                    errors=errors,
                )
            
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
                    "parameter_path": parameter_path,
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
