"""
Research Plan API routes for the 5-minute plan wizard.
"""

import json
import logging
import sys
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Any, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from api.models import (
    CompanyProfileSchema,
    CompanySuggestionSchema,
    ClarificationOptionSchema,
    ClarificationQuestionSchema,
    IntelligenceOptionSchema,
    IntelligenceQuestionSchema,
    IntelligenceQuestionsRequest,
    IntelligenceQuestionsResponse,
    IntelligenceFollowupRequest,
    ValidateCompaniesRequest,
    ValidateCompaniesResponse,
    SuggestCompaniesRequest,
    SuggestCompaniesResponse,
    ResearchGoalResultSchema,
    GenerateGoalRequest,
    GenerateGoalResponse,
    CompanyConfidenceSchema,
    ConfidencePreviewSchema,
    ResearchPlanSchema,
    PlanCreateRequest,
    PlanCreateResponse,
    GenerateCustomParameterRequest,
    StepClarificationsRequest,
    DynamicVariableDefinition,
    RunCreateRequest,
    RunCreateResponse,
    RunStatus,
    GraveyardCompanySchema,
    DiscoverGraveyardRequest,
    DiscoverGraveyardResponse,
)
from api.services.v2_runner import V2Runner
from agents.research_plan_agent import (
    validate_companies as agent_validate_companies,
    suggest_companies as agent_suggest_companies,
    generate_goal as agent_generate_goal,
    generate_clarifications as agent_generate_clarifications,
    generate_confidence_preview as agent_generate_confidence_preview,
    generate_custom_parameter as agent_generate_custom_parameter,
    generate_intelligence_questions as agent_generate_intelligence_questions,
    generate_intelligence_followup as agent_generate_intelligence_followup,
)

router = APIRouter()
logger = logging.getLogger(__name__)
PLANS_DIR = project_root / "data" / "plans"
RESULTS_DIR = project_root / "data" / "results"

PLANS_DIR.mkdir(parents=True, exist_ok=True)


def _company_profile_to_schema(p) -> CompanyProfileSchema:
    """Convert agent CompanyProfile to API schema."""
    return CompanyProfileSchema(
        id=p.id,
        input_name=p.input_name,
        official_name=p.official_name,
        industry=p.industry,
        description=p.description,
        headquarters=getattr(p, "headquarters", None),
        website=getattr(p, "website", None),
        ambiguity_notes=getattr(p, "ambiguity_notes", None),
        subsidiary_notes=getattr(p, "subsidiary_notes", None),
        subsidiaries=getattr(p, "subsidiaries", None) or [],
        brand_name=getattr(p, "brand_name", None),
    )


def _suggestion_to_schema(s) -> CompanySuggestionSchema:
    return CompanySuggestionSchema(
        id=s.id,
        name=s.name,
        category=s.category,
        rationale=s.rationale,
        gap_filled=s.gap_filled,
        subsidiaries=getattr(s, "subsidiaries", None) or [],
        brand_name=getattr(s, "brand_name", None),
    )


def _clarification_to_schema(q) -> ClarificationQuestionSchema:
    return ClarificationQuestionSchema(
        id=q.id,
        question=q.question,
        options=[ClarificationOptionSchema(id=o.id, label=o.label, description=o.description) for o in q.options],
        allow_free_text=q.allow_free_text,
        context=q.context,
        impacts=q.impacts,
    )


def _intelligence_question_to_schema(q) -> IntelligenceQuestionSchema:
    """Convert agent IntelligenceQuestion to API schema."""
    return IntelligenceQuestionSchema(
        id=q.id,
        question=q.question,
        options=[IntelligenceOptionSchema(id=o.id, label=o.label, description=o.description) for o in q.options],
        allow_multiple=q.allow_multiple,
        allow_free_text=q.allow_free_text,
        context=q.context,
        follow_up_hint=q.follow_up_hint,
    )


# =============================================================================
# Intelligence Questions endpoints
# =============================================================================

@router.post("/intelligence-questions", response_model=IntelligenceQuestionsResponse)
async def intelligence_questions_endpoint(request: IntelligenceQuestionsRequest):
    """Generate strategic intelligence questions for a wizard step (shown before content generation)."""
    try:
        questions = await agent_generate_intelligence_questions(request.step, request.context)
        return IntelligenceQuestionsResponse(
            questions=[_intelligence_question_to_schema(q) for q in questions],
        )
    except Exception as e:
        logger.exception("Intelligence questions generation failed")
        raise HTTPException(status_code=502, detail=f"Intelligence questions generation failed: {str(e)}")


@router.post("/intelligence-followup", response_model=IntelligenceQuestionsResponse)
async def intelligence_followup_endpoint(request: IntelligenceFollowupRequest):
    """Generate follow-up intelligence questions based on a user's answer."""
    try:
        previous = [a.model_dump() for a in request.previous_answers]
        questions = await agent_generate_intelligence_followup(
            step=request.step,
            question_id=request.question_id,
            selected_options=request.selected_options,
            context=request.context,
            previous_answers=previous,
        )
        return IntelligenceQuestionsResponse(
            questions=[_intelligence_question_to_schema(q) for q in questions],
        )
    except Exception as e:
        logger.exception("Intelligence follow-up generation failed")
        raise HTTPException(status_code=502, detail=f"Intelligence follow-up generation failed: {str(e)}")


# =============================================================================
# Step endpoints
# =============================================================================

@router.post("/validate-companies", response_model=ValidateCompaniesResponse)
async def validate_companies_endpoint(request: ValidateCompaniesRequest):
    """Step 1: Validate and profile company names using Perplexity (live web)."""
    try:
        profiles, clarifications = await agent_validate_companies(request.companies)
        return ValidateCompaniesResponse(
            companies=[_company_profile_to_schema(p) for p in profiles],
            clarifications=[_clarification_to_schema(q) for q in clarifications],
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Company validation failed: {str(e)}")


@router.post("/suggest-companies", response_model=SuggestCompaniesResponse)
async def suggest_companies_endpoint(request: SuggestCompaniesRequest):
    """Step 2: Suggest additional companies using Perplexity (with Claude fallback)."""
    context = [p.model_dump() for p in request.companies]
    intel_answers = None
    if request.intelligence_answers:
        intel_answers = [a.model_dump() for a in request.intelligence_answers]
    try:
        suggestions, clarifications = await agent_suggest_companies(context, intel_answers)
        return SuggestCompaniesResponse(
            suggestions=[_suggestion_to_schema(s) for s in suggestions],
            clarifications=[_clarification_to_schema(q) for q in clarifications],
        )
    except Exception as e:
        logger.exception("Company suggestions failed")
        detail = str(e)
        if "ERROR" in detail and len(detail) < 50:
            detail += " (Perplexity/OpenRouter may be unavailable; check OPENROUTER_API_KEY and provider status)"
        raise HTTPException(status_code=502, detail=f"Company suggestions failed: {detail}")


@router.post("/generate-goal", response_model=GenerateGoalResponse)
async def generate_goal_endpoint(request: GenerateGoalRequest):
    """Step 4: Generate research mission, key questions, hypothesis (Claude Opus)."""
    plan_context = {
        "companies": request.companies,
        "industry_context": request.industry_context,
        "parameter_summary": request.parameter_summary,
    }
    try:
        goal_result, clarifications = await agent_generate_goal(plan_context)
        return GenerateGoalResponse(
            goal=ResearchGoalResultSchema(
                mission_statement=goal_result.mission_statement,
                key_questions=goal_result.key_questions,
                hypothesis=goal_result.hypothesis,
                perspective=goal_result.perspective,
            ),
            clarifications=[_clarification_to_schema(q) for q in clarifications],
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Goal generation failed: {str(e)}")


@router.post("/generate-custom-parameter")
async def generate_custom_parameter_endpoint(request: GenerateCustomParameterRequest):
    """Generate a single variable definition from free-text description (Aurora Alpha)."""
    context = {
        "companies": request.companies,
        "industry_context": request.industry_context,
    }
    try:
        data = await agent_generate_custom_parameter(request.description, context)
        # Ensure required fields for DynamicVariableDefinition
        return DynamicVariableDefinition(
            id=data.get("id", "dyn_custom"),
            name=data.get("name", request.description[:50]),
            category=data.get("category", "Custom"),
            research_prompt=data.get("research_prompt", ""),
            example_queries=data.get("example_queries", []),
            answer_spec=data.get("answer_spec", []),
            preferred_source_types=data.get("preferred_source_types", ["official", "tier1_news"]),
            key_terms=data.get("key_terms", []),
            max_concise_chars=int(data.get("max_concise_chars", 200)),
            rationale=data.get("rationale"),
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Custom parameter generation failed: {str(e)}")


@router.post("/step-clarifications")
async def step_clarifications_endpoint(request: StepClarificationsRequest):
    """Generate clarification questions for a given step (Aurora Alpha)."""
    try:
        questions = await agent_generate_clarifications(request.step, request.context)
        return {"clarifications": [_clarification_to_schema(q) for q in questions]}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Clarification generation failed: {str(e)}")


class ConfidencePreviewRequest(BaseModel):
    """Minimal plan context for confidence preview."""
    companies: List[Any] = []  # list of {id, official_name} or str
    industry_context: str = ""


@router.post("/confidence-preview", response_model=ConfidencePreviewSchema)
async def confidence_preview_endpoint(request: ConfidencePreviewRequest):
    """Step 6: Generate research feasibility assessment (Aurora Alpha)."""
    plan = {
        "companies": request.companies,
        "industry_context": request.industry_context,
    }
    try:
        preview = await agent_generate_confidence_preview(plan)
        return ConfidencePreviewSchema(
            overall_level=preview.overall_level,
            company_confidences=[
                CompanyConfidenceSchema(
                    company_id=c.company_id,
                    company_name=c.company_name,
                    level=c.level,
                    reason=c.reason,
                )
                for c in preview.company_confidences
            ],
            warnings=preview.warnings,
            suggestions=preview.suggestions,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Confidence preview failed: {str(e)}")


# =============================================================================
# Graveyard Discovery
# =============================================================================

@router.post("/discover-graveyard", response_model=DiscoverGraveyardResponse)
async def discover_graveyard_endpoint(request: DiscoverGraveyardRequest):
    """Discover defunct companies in the sector for post-mortem intelligence."""
    from agents.graveyard_discovery_agent import discover_graveyard_companies

    try:
        companies = await discover_graveyard_companies(
            companies=request.companies,
            industry_context=request.industry_context,
            sector_hint=request.sector_hint,
        )
        return DiscoverGraveyardResponse(
            companies=[
                GraveyardCompanySchema(
                    name=c.name,
                    years_active=c.years_active,
                    peak_description=c.peak_description,
                    reason_summary=c.reason_summary,
                    confidence=c.confidence,
                )
                for c in companies
            ]
        )
    except Exception as e:
        logger.exception("Graveyard discovery failed")
        raise HTTPException(status_code=502, detail=f"Graveyard discovery failed: {str(e)}")


# =============================================================================
# Plan CRUD
# =============================================================================

def _plan_id() -> str:
    return f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


def _plan_filepath(plan_id: str) -> Path:
    return PLANS_DIR / f"{plan_id}.json"


@router.post("", response_model=PlanCreateResponse)
async def create_plan(request: PlanCreateRequest):
    """Save a new research plan (draft)."""
    plan_id = _plan_id()
    now = datetime.now(timezone.utc).isoformat()
    plan_doc = {
        "id": plan_id,
        "title": request.title,
        "status": "draft",
        "created_at": now,
        "updated_at": now,
        "companies": [p.model_dump() for p in request.companies],
        "suggested_companies": [s.model_dump() for s in request.suggested_companies],
        "accepted_suggestions": request.accepted_suggestions,
        "effective_company_names": request.effective_company_names,
        "industry_context": request.industry_context,
        "selected_variable_ids": request.selected_variable_ids,
        "dynamic_variables": [d.model_dump() for d in request.dynamic_variables],
        "parameter_contexts": request.parameter_contexts,
        "mission_statement": request.mission_statement,
        "key_questions": request.key_questions,
        "hypothesis": request.hypothesis,
        "perspective": request.perspective,
        "audience": request.audience,
        "depth": request.depth,
        "focus_companies": request.focus_companies,
        "known_context": request.known_context,
        "graveyard_enabled": request.graveyard_enabled,
        "graveyard_companies": [g.model_dump() for g in request.graveyard_companies],
        "confidence_preview": None,
        "clarification_log": [],
        "run_id": None,
    }
    with open(_plan_filepath(plan_id), "w", encoding="utf-8") as f:
        json.dump(plan_doc, f, indent=2, default=str)
    return PlanCreateResponse(plan_id=plan_id, status="draft")


def _company_display_name(c: Any) -> str:
    """Safely get display name from company (dict or string)."""
    if isinstance(c, str):
        return c
    if isinstance(c, dict):
        return c.get("official_name") or c.get("name") or ""
    return ""


@router.get("")
async def list_plans():
    """List all saved plans (newest first)."""
    try:
        PLANS_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    plans = []
    try:
        if PLANS_DIR.exists():
            for f in PLANS_DIR.glob("plan_*.json"):
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                    companies_raw = data.get("companies", [])
                    companies_list = (
                        [_company_display_name(c) for c in companies_raw]
                        if isinstance(companies_raw, list)
                        else []
                    )
                    plans.append({
                        "id": data.get("id", f.stem),
                        "title": data.get("title", "Research Plan"),
                        "status": data.get("status", "draft"),
                        "created_at": data.get("created_at", ""),
                        "updated_at": data.get("updated_at", ""),
                        "companies": companies_list,
                        "run_id": data.get("run_id"),
                    })
                except Exception:
                    continue
        plans.sort(key=lambda p: p.get("updated_at") or p.get("created_at") or "", reverse=True)
    except Exception:
        plans = []
    return {"plans": plans}


@router.get("/{plan_id}")
async def get_plan(plan_id: str):
    """Get full plan by ID."""
    filepath = _plan_filepath(plan_id)
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Plan not found: {plan_id}")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


@router.put("/{plan_id}")
async def update_plan(plan_id: str, plan: dict):
    """Update an existing plan."""
    filepath = _plan_filepath(plan_id)
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Plan not found: {plan_id}")
    plan["id"] = plan_id
    plan["updated_at"] = datetime.now(timezone.utc).isoformat()
    if "created_at" not in plan:
        with open(filepath, "r", encoding="utf-8") as f:
            existing = json.load(f)
        plan["created_at"] = existing.get("created_at", plan["updated_at"])
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, default=str)
    return {"id": plan_id, "status": plan.get("status", "draft")}


@router.post("/{plan_id}/launch", response_model=RunCreateResponse)
async def launch_plan(plan_id: str, background_tasks: BackgroundTasks):
    """Accept plan and start V2 pipeline. Plan status set to launched; run_id stored."""
    filepath = _plan_filepath(plan_id)
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Plan not found: {plan_id}")
    with open(filepath, "r", encoding="utf-8") as f:
        plan = json.load(f)

    effective = plan.get("effective_company_names")
    if effective and isinstance(effective, list) and len(effective) > 0:
        companies = effective
    else:
        companies = [c.get("official_name", c.get("name", "")) for c in plan.get("companies", [])]
        accepted = plan.get("accepted_suggestions", [])
        suggested = plan.get("suggested_companies", [])
        suggested_names = [s.get("name", "") for s in suggested if s.get("id") in accepted]
        companies = companies + suggested_names
    if not companies:
        raise HTTPException(status_code=400, detail="Plan has no companies")
    selected = plan.get("selected_variable_ids", [])
    if not selected:
        raise HTTPException(status_code=400, detail="Plan has no parameters selected")
    dynamic = plan.get("dynamic_variables", [])
    parameter_contexts = plan.get("parameter_contexts") or {}
    venture_context = plan.get("mission_statement", "")[:500]
    if plan.get("perspective") and plan["perspective"] != "neutral":
        venture_context = f"Perspective: {plan['perspective']}. {venture_context}"
    key_questions = plan.get("key_questions", [])
    if key_questions:
        venture_context += "\n\nKey questions the report must answer:\n" + "\n".join(f"- {q}" for q in key_questions[:8])
    audience = plan.get("audience", "")
    if audience:
        venture_context += f"\n\nAudience for the report: {audience}."

    run_id = f"v2_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    depth = plan.get("depth", "standard")
    concurrency = 3
    fast_mode = depth == "quick"

    progress_filepath = RESULTS_DIR / f"progress_{run_id}.json"
    total = len(companies) * len(selected)
    initial_progress = {
        "run_id": run_id,
        "status": "pending",
        "companies": companies,
        "variables": selected,
        "total": total,
        "completed": 0,
        "current": None,
        "started_at": datetime.now().isoformat(),
        "elapsed_seconds": 0,
        "recent_activity": [],
        "phase": "starting",
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(progress_filepath, "w", encoding="utf-8") as f:
        json.dump(initial_progress, f, indent=2)

    graveyard_company_names = None
    if plan.get("graveyard_enabled") and plan.get("graveyard_companies"):
        graveyard_company_names = [
            g.get("name", "") for g in plan["graveyard_companies"] if g.get("name")
        ]

    v2_runner = V2Runner()
    background_tasks.add_task(
        v2_runner.run_sync,
        run_id=run_id,
        companies=companies,
        variables=selected,
        dynamic_variables=dynamic,
        parameter_contexts=parameter_contexts,
        concurrency=concurrency,
        fast_mode=fast_mode,
        venture_context=venture_context,
        key_questions=key_questions,
        hypothesis=plan.get("hypothesis", ""),
        graveyard_companies=graveyard_company_names,
        industry_context=plan.get("industry_context", ""),
    )

    plan["status"] = "launched"
    plan["run_id"] = run_id
    plan["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, default=str)

    return RunCreateResponse(
        run_id=run_id,
        status=RunStatus.PENDING,
        message=f"Research started from plan. Monitor at /api/runs/{run_id}/status",
    )
