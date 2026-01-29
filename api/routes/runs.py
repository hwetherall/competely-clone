"""
Runs API routes for managing research runs.
"""

import sys
import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks

# Ensure project root is in path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from api.models import (
    RunListItem,
    RunDetailResponse,
    RunCreateRequest,
    RunCreateResponse,
    RunProgressResponse,
    RunStatus,
    CellData,
    SourceData,
    RunMetadata,
    ProgressData,
    CurrentTask,
    ActivityItem,
    ConfidenceLevel,
)
from api.services import ResearchRunner

router = APIRouter()

# Results directory
RESULTS_DIR = project_root / "data" / "results"


def get_run_id_from_filename(filename: str) -> str:
    """Extract run ID from filename (e.g., comparison_20260128_163249.json -> comparison_20260128_163249)."""
    return filename.replace(".json", "")


def parse_result_file(filepath: Path) -> Optional[dict]:
    """Load and parse a result JSON file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


@router.get("", response_model=List[RunListItem])
async def list_runs():
    """
    List all research runs (completed and in-progress).
    
    Returns runs sorted by creation time (newest first).
    """
    runs = []
    
    # Scan results directory for comparison files
    if RESULTS_DIR.exists():
        for filepath in RESULTS_DIR.glob("comparison_*.json"):
            # Skip refined files
            if "_refined" in filepath.name:
                continue
                
            data = parse_result_file(filepath)
            if not data:
                continue
            
            run_id = get_run_id_from_filename(filepath.name)
            companies = data.get("companies", [])
            variables = data.get("variables", [])
            metadata = data.get("metadata", {})
            timestamp = data.get("timestamp", "")
            
            # Determine status
            total_cells = len(companies) * len(variables)
            successful = metadata.get("successful_cells", total_cells)
            
            runs.append(RunListItem(
                id=run_id,
                companies=companies,
                variables=variables,
                status=RunStatus.COMPLETED,
                created_at=timestamp,
                completed_at=timestamp,
                total_cells=total_cells,
                successful_cells=successful,
            ))
    
    # Check for in-progress runs
    for filepath in RESULTS_DIR.glob("progress_*.json"):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                progress = json.load(f)
            
            run_id = filepath.stem.replace("progress_", "")
            
            # Only add if not already in completed runs
            if not any(r.id == run_id for r in runs):
                runs.append(RunListItem(
                    id=run_id,
                    companies=progress.get("companies", []),
                    variables=progress.get("variables", []),
                    status=RunStatus.RUNNING if progress.get("status") == "running" else RunStatus.PENDING,
                    created_at=progress.get("started_at", ""),
                    total_cells=progress.get("total", 0),
                    successful_cells=progress.get("completed", 0),
                ))
        except Exception:
            continue
    
    # Sort by created_at descending
    runs.sort(key=lambda r: r.created_at, reverse=True)
    
    return runs


@router.get("/{run_id}", response_model=RunDetailResponse)
async def get_run(run_id: str):
    """
    Get full details for a specific run.
    
    Returns the complete research grid with all cell data.
    """
    filepath = RESULTS_DIR / f"{run_id}.json"
    
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    
    data = parse_result_file(filepath)
    if not data:
        raise HTTPException(status_code=500, detail="Failed to parse run data")
    
    # Convert grid data to proper schema
    grid = {}
    raw_grid = data.get("grid", {})
    
    for company, variables in raw_grid.items():
        grid[company] = {}
        for var_id, cell_data in variables.items():
            # Convert sources
            sources = [
                SourceData(
                    title=s.get("title", ""),
                    url=s.get("url", ""),
                    snippet=s.get("snippet"),
                    query=s.get("query"),
                    domain=s.get("domain"),
                    source_score=s.get("source_score"),
                    is_official=s.get("is_official"),
                )
                for s in cell_data.get("sources", [])
            ]
            
            # Map confidence
            confidence_str = cell_data.get("confidence", "none").lower()
            try:
                confidence = ConfidenceLevel(confidence_str)
            except ValueError:
                confidence = ConfidenceLevel.NONE
            
            grid[company][var_id] = CellData(
                company=cell_data.get("company", company),
                variable_id=cell_data.get("variable_id", var_id),
                variable_name=cell_data.get("variable_name", var_id),
                concise=cell_data.get("concise", ""),
                comprehensive=cell_data.get("comprehensive", ""),
                sources=sources,
                confidence=confidence,
                iterations=cell_data.get("iterations", 0),
                total_searches=cell_data.get("total_searches", 0),
                timestamp=cell_data.get("timestamp"),
                error=cell_data.get("error"),
                metadata=cell_data.get("metadata"),
            )
    
    # Build metadata
    raw_metadata = data.get("metadata", {})
    metadata = RunMetadata(
        total_cells=raw_metadata.get("total_cells", len(data.get("companies", [])) * len(data.get("variables", []))),
        successful_cells=raw_metadata.get("successful_cells", 0),
        failed_cells=raw_metadata.get("failed_cells", 0),
        elapsed_seconds=raw_metadata.get("elapsed_seconds", 0),
        concurrency=raw_metadata.get("concurrency", 3),
        fast_mode=raw_metadata.get("fast_mode", False),
    )
    
    return RunDetailResponse(
        id=run_id,
        timestamp=data.get("timestamp", ""),
        companies=data.get("companies", []),
        variables=data.get("variables", []),
        grid=grid,
        metadata=metadata,
        status=RunStatus.COMPLETED,
    )


@router.get("/{run_id}/status", response_model=RunProgressResponse)
async def get_run_status(run_id: str):
    """
    Get progress status for a run.
    
    Used for polling during active runs.
    """
    # First check if run is completed
    result_filepath = RESULTS_DIR / f"{run_id}.json"
    if result_filepath.exists():
        data = parse_result_file(result_filepath)
        if data:
            metadata = data.get("metadata", {})
            total = metadata.get("total_cells", 0)
            
            return RunProgressResponse(
                run_id=run_id,
                status=RunStatus.COMPLETED,
                progress=ProgressData(completed=total, total=total),
                elapsed_seconds=metadata.get("elapsed_seconds", 0),
                estimated_remaining_seconds=0,
                recent_activity=[],
            )
    
    # Check for progress file
    progress_filepath = RESULTS_DIR / f"progress_{run_id}.json"
    if progress_filepath.exists():
        try:
            with open(progress_filepath, "r", encoding="utf-8") as f:
                progress = json.load(f)
            
            # Parse current task
            current = None
            if progress.get("current"):
                current = CurrentTask(
                    company=progress["current"].get("company", ""),
                    variable=progress["current"].get("variable", ""),
                    step=progress["current"].get("step"),
                )
            
            # Parse activity
            activity = [
                ActivityItem(
                    company=a.get("company", ""),
                    variable=a.get("variable", ""),
                    confidence=a.get("confidence", "none"),
                    timestamp=a.get("timestamp", ""),
                    status=a.get("status", "completed"),
                )
                for a in progress.get("recent_activity", [])[-10:]  # Last 10 items
            ]
            
            status_str = progress.get("status", "pending")
            try:
                status = RunStatus(status_str)
            except ValueError:
                status = RunStatus.PENDING
            
            return RunProgressResponse(
                run_id=run_id,
                status=status,
                progress=ProgressData(
                    completed=progress.get("completed", 0),
                    total=progress.get("total", 0),
                    current=current,
                ),
                elapsed_seconds=progress.get("elapsed_seconds", 0),
                estimated_remaining_seconds=progress.get("estimated_remaining_seconds"),
                recent_activity=activity,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to read progress: {str(e)}")
    
    raise HTTPException(status_code=404, detail=f"No progress data found for run: {run_id}")


@router.post("", response_model=RunCreateResponse)
async def create_run(request: RunCreateRequest, background_tasks: BackgroundTasks):
    """
    Start a new research run.
    
    The research runs in the background and progress can be monitored
    via the /runs/{run_id}/status endpoint.
    """
    # Validate variables exist
    from config.variables import get_all_variable_ids
    valid_variables = get_all_variable_ids()
    
    invalid_vars = [v for v in request.variables if v not in valid_variables]
    if invalid_vars:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid variables: {', '.join(invalid_vars)}"
        )
    
    # Generate run ID
    run_id = f"comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Initialize progress file
    progress_filepath = RESULTS_DIR / f"progress_{run_id}.json"
    initial_progress = {
        "run_id": run_id,
        "status": "pending",
        "companies": request.companies,
        "variables": request.variables,
        "total": len(request.companies) * len(request.variables),
        "completed": 0,
        "current": None,
        "started_at": datetime.now().isoformat(),
        "elapsed_seconds": 0,
        "recent_activity": [],
    }
    
    with open(progress_filepath, "w", encoding="utf-8") as f:
        json.dump(initial_progress, f, indent=2)
    
    # Start background task
    runner = ResearchRunner()
    background_tasks.add_task(
        runner.run_research_sync,
        run_id=run_id,
        companies=request.companies,
        variables=request.variables,
        concurrency=request.concurrency,
        fast_mode=request.fast_mode,
    )
    
    return RunCreateResponse(
        run_id=run_id,
        status=RunStatus.PENDING,
        message=f"Research started. Monitor progress at /api/runs/{run_id}/status",
    )
