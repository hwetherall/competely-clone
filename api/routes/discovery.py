"""
Competitor discovery API routes.
"""

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from agents.competitor_discovery_agent import (
    load_discovery_run,
    run_discovery_sync,
    save_discovery_run,
)
from agents.schemas import DiscoveryRun, DiscoveryTargetProfile
from api.models import (
    DiscoveryCreateRequest,
    DiscoveryCreateResponse,
    DiscoveryRunResponse,
    DiscoveryPromoteRequest,
    DiscoveryPromoteResponse,
    RunStatus,
)
from api.services import ResearchRunner
from api.services.v2_runner import V2Runner
from config.innovera_profile import INNOVERA_PROFILE
from config.innovera_variables import get_all_innovera_variable_ids
from config.framings import DEFAULT_FRAMING_SEEDS

router = APIRouter()
RESULTS_DIR = project_root / "data" / "results"


def _default_target_profile() -> DiscoveryTargetProfile:
    return DiscoveryTargetProfile(
        company_name="Innovera",
        description=INNOVERA_PROFILE,
        industry="AI-native decision intelligence",
        audience="Corporate innovators, strategy teams, and executives",
    )


@router.post("", response_model=DiscoveryCreateResponse)
async def create_discovery(request: DiscoveryCreateRequest, background_tasks: BackgroundTasks):
    """Start a competitor discovery run in the background."""
    target_profile = request.target_profile or _default_target_profile()
    # Create the durable run id here so the client can poll immediately.
    run_id = f"discovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    save_discovery_run(DiscoveryRun(
        id=run_id,
        target_profile=target_profile,
        framing_seeds={**DEFAULT_FRAMING_SEEDS, **(request.framing_seeds or {})},
        candidates=[],
        status="running",
        created_at=datetime.now(timezone.utc),
    ))
    background_tasks.add_task(
        run_discovery_sync,
        target_profile=target_profile,
        framing_seeds=request.framing_seeds,
        max_candidates=request.max_candidates,
        run_id=run_id,
    )
    return DiscoveryCreateResponse(discovery_run_id=run_id, status="running")


@router.get("/{discovery_id}", response_model=DiscoveryRunResponse)
async def get_discovery(discovery_id: str):
    """Get discovery run status and results."""
    try:
        return load_discovery_run(discovery_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Discovery run not found: {discovery_id}")


@router.post("/{discovery_id}/promote", response_model=DiscoveryPromoteResponse)
async def promote_discovery(
    discovery_id: str,
    request: DiscoveryPromoteRequest,
    background_tasks: BackgroundTasks,
):
    """Promote selected candidates into a normal research run."""
    try:
        discovery = load_discovery_run(discovery_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Discovery run not found: {discovery_id}")
    if discovery.status != "complete":
        raise HTTPException(status_code=400, detail=f"Discovery run is not complete: {discovery.status}")

    known_names = {c.name for c in discovery.candidates}
    selected = []
    for name in request.selected_names:
        clean = name.strip()
        if clean and clean not in selected:
            selected.append(clean)
    if not selected:
        raise HTTPException(status_code=400, detail="No selected company names provided.")
    unknown = [name for name in selected if name not in known_names]
    if unknown:
        raise HTTPException(status_code=400, detail=f"Selected names are not in discovery results: {', '.join(unknown)}")

    variables = request.variables or get_all_innovera_variable_ids()
    use_v2 = (request.version or "v1") == "v2"
    run_id = f"v2_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}" if use_v2 else f"comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    progress_filepath = RESULTS_DIR / f"progress_{run_id}.json"
    total = len(selected) * len(variables)
    with open(progress_filepath, "w", encoding="utf-8") as f:
        json.dump({
            "run_id": run_id,
            "status": "pending",
            "companies": selected,
            "variables": variables,
            "total": total,
            "completed": 0,
            "current": None,
            "started_at": datetime.now().isoformat(),
            "elapsed_seconds": 0,
            "recent_activity": [],
            **({"phase": "starting"} if use_v2 else {}),
        }, f, indent=2)

    dynamic_var_dicts = [d.model_dump() for d in request.dynamic_variables] if request.dynamic_variables else None
    if use_v2:
        v2_runner = V2Runner()
        background_tasks.add_task(
            v2_runner.run_sync,
            run_id=run_id,
            companies=selected,
            variables=variables,
            dynamic_variables=dynamic_var_dicts,
            parameter_contexts=request.parameter_contexts,
            concurrency=request.concurrency,
            fast_mode=request.fast_mode,
            venture_context="",
            key_questions=None,
            hypothesis="",
            graveyard_companies=None,
            industry_context=discovery.target_profile.industry or "",
            parameter_path=request.parameter_path,
        )
    else:
        runner = ResearchRunner()
        background_tasks.add_task(
            runner.run_research_sync,
            run_id=run_id,
            companies=selected,
            variables=variables,
            dynamic_variables=dynamic_var_dicts,
            concurrency=request.concurrency,
            fast_mode=request.fast_mode,
            parameter_path=request.parameter_path,
        )

    return DiscoveryPromoteResponse(run_id=run_id, status=RunStatus.PENDING, companies=selected)
