"""
Variables API routes.
"""

import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.variables import VARIABLES, get_variables_by_category, get_always_variables
from config.avis_variables import get_avis_always, get_avis_sometimes
from config.innovera_variables import get_innovera_always
from api.models import (
    VariableResponse,
    VariableCategoryResponse,
    GenerateVariablesRequest,
    VariableGenerationResponse,
    Tier2RecommendationSchema,
    DynamicVariableDefinition,
)
from agents.variable_generator import generate_variables as generate_variables_impl
from agents.avis_variable_generator import generate_avis_variables as generate_avis_variables_impl
from agents.llm_client import LLMError

router = APIRouter()


@router.get("", response_model=VariableCategoryResponse)
async def get_variables():
    """Get all research variables grouped by category."""
    categories_dict = get_variables_by_category()
    result = {}
    for category_name, variables in categories_dict.items():
        result[category_name] = [
            VariableResponse(
                id=var.id,
                name=var.name,
                category=var.category,
                description=var.research_prompt[:200] + "..." if len(var.research_prompt) > 200 else var.research_prompt
            )
            for var in variables
        ]
    return VariableCategoryResponse(categories=result)


@router.get("/list")
async def list_variables():
    """Get a flat list of all variable IDs and names."""
    return [
        {"id": var.id, "name": var.name, "category": var.category}
        for var in VARIABLES
    ]


@router.post("/generate", response_model=VariableGenerationResponse)
async def generate_variables(request: GenerateVariablesRequest):
    """
    Generate smart parameters based on the Set of Competitors (SoC).
    Supports three paths: 'competely' (product comparison), 'avis' (investment
    thesis), and 'innovera' (Innovera-tuned business model deep dive).
    """
    path = getattr(request, "parameter_path", "competely") or "competely"
    print(f"[Variable generation] Path: {path}, companies: {request.companies}, profiles: {request.company_profiles}")

    if path == "avis":
        return await _generate_avis(request)
    if path == "innovera":
        return _generate_innovera(request)
    return await _generate_competely(request)


async def _generate_competely(request: GenerateVariablesRequest) -> VariableGenerationResponse:
    """Competely path: product-comparison focused parameter generation."""
    try:
        result = await generate_variables_impl(request.companies, request.company_profiles)
        print(f"[Competely] Done. Industry: {result.industry_context}, generated {len(result.generated_variables)} variables.")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LLMError as e:
        raise HTTPException(status_code=502, detail=f"Variable generation failed: {e.message}")

    always = get_always_variables()
    always_variables = [
        VariableResponse(id=v.id, name=v.name, category=v.category, description=None)
        for v in always
    ]
    tier2 = [
        Tier2RecommendationSchema(
            variable_id=r.variable_id, include=r.include, reason=r.reason,
        )
        for r in result.tier2_recommendations
    ]
    generated = [
        DynamicVariableDefinition(
            id=v.id, name=v.name, category=v.category,
            research_prompt=v.research_prompt,
            example_queries=v.example_queries,
            answer_spec=v.answer_spec,
            preferred_source_types=v.preferred_source_types,
            key_terms=v.key_terms,
            max_concise_chars=v.max_concise_chars,
            rationale=result.generated_variable_rationales.get(v.id) or None,
        )
        for v in result.generated_variables
    ]
    return VariableGenerationResponse(
        industry_context=result.industry_context,
        always_variables=always_variables,
        always_parameter_contexts=result.always_parameter_contexts,
        tier2_recommendations=tier2,
        generated_variables=generated,
    )


async def _generate_avis(request: GenerateVariablesRequest) -> VariableGenerationResponse:
    """AVIS path: investment-thesis focused parameter generation."""
    try:
        result = await generate_avis_variables_impl(request.companies, request.company_profiles)
        print(f"[AVIS] Done. Industry: {result.industry_context}, generated {len(result.generated_variables)} variables.")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LLMError as e:
        raise HTTPException(status_code=502, detail=f"AVIS variable generation failed: {e.message}")

    always = get_avis_always()
    always_variables = [
        VariableResponse(id=v.id, name=v.name, category=v.category, description=None)
        for v in always
    ]
    tier2 = [
        Tier2RecommendationSchema(
            variable_id=r.variable_id, include=r.include, reason=r.reason,
        )
        for r in result.tier2_recommendations
    ]
    generated = [
        DynamicVariableDefinition(
            id=v.id, name=v.name, category=v.category,
            research_prompt=v.research_prompt,
            example_queries=v.example_queries,
            answer_spec=v.answer_spec,
            preferred_source_types=v.preferred_source_types,
            key_terms=v.key_terms,
            max_concise_chars=v.max_concise_chars,
            rationale=result.generated_variable_rationales.get(v.id) or None,
        )
        for v in result.generated_variables
    ]
    return VariableGenerationResponse(
        industry_context=result.industry_context,
        always_variables=always_variables,
        always_parameter_contexts=result.always_parameter_contexts,
        tier2_recommendations=tier2,
        generated_variables=generated,
    )


def _generate_innovera(request: GenerateVariablesRequest) -> VariableGenerationResponse:
    """Innovera path: fixed Zamir-requested deep-dive lens."""
    always = get_innovera_always()
    always_variables = [
        VariableResponse(id=v.id, name=v.name, category=v.category, description=None)
        for v in always
    ]
    contexts = {
        "inv_offer_shape": "Shows whether a competitor has a narrower or faster package Innovera can learn from.",
        "inv_gtm_motion": "Reveals how competitors sell decision intelligence, AI research, and blended consulting offers.",
        "inv_packaging": "Answers what is bundled, what costs extra, and where packaging is flexible or opaque.",
        "inv_pricing_mechanics": "Captures pricing unit, starting price, ACV signals, pilot offers, and scaling mechanics.",
        "inv_contract_structure": "Surfaces upgrade triggers, term length, commitments, renewal mechanics, and opaque contract norms.",
        "inv_client_engagement": "Compares onboarding, cadence, and human touchpoints against Innovera's expert-in-the-loop model.",
        "inv_ai_human_blend": "Tests whether consulting firms and AI-native platforms are ahead or behind on AI plus human delivery.",
        "inv_size_signals": "Anchors threat level with revenue, customers, funding, headcount, and adoption evidence.",
        "inv_speed_to_market": "Identifies the wedge and execution pattern behind smaller, faster-to-market offers.",
        "inv_takeaway_for_innovera": "Synthesizes what Innovera should copy, avoid, monitor, or test next.",
    }
    return VariableGenerationResponse(
        industry_context="Innovera lens: AI-native decision intelligence, market research, competitive analysis, and blended AI plus human consulting.",
        always_variables=always_variables,
        always_parameter_contexts=contexts,
        tier2_recommendations=[],
        generated_variables=[],
    )
