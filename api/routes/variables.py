"""
Variables API routes.
"""

import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException

# Ensure project root is in path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.variables import VARIABLES, get_variables_by_category, get_always_variables
from api.models import (
    VariableResponse,
    VariableCategoryResponse,
    GenerateVariablesRequest,
    VariableGenerationResponse,
    Tier2RecommendationSchema,
    DynamicVariableDefinition,
)
from agents.variable_generator import generate_variables as generate_variables_impl
from agents.llm_client import LLMError

router = APIRouter()


@router.get("", response_model=VariableCategoryResponse)
async def get_variables():
    """
    Get all research variables grouped by category.
    
    Returns variables organized into 4 categories:
    - Core Positioning & Value
    - Market & Customers
    - Product & Capability
    - Economics & Scale
    """
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
    """
    Get a flat list of all variable IDs and names.
    """
    return [
        {"id": var.id, "name": var.name, "category": var.category}
        for var in VARIABLES
    ]


@router.post("/generate", response_model=VariableGenerationResponse)
async def generate_variables(request: GenerateVariablesRequest):
    """
    Generate smart parameters based on the Set of Competitors (SoC).
    
    Analyzes the competitor list with Claude Opus 4.6 to:
    - Detect industry context
    - Recommend which Tier 2 (contextual) variables to include or exclude
    - Generate ~20 industry-specific Tier 3 variables with full research definitions
    
    Takes ~30-90 seconds (Claude Opus 4.6). Requires OPENROUTER_API_KEY.
    """
    print(f"[Variable generation] Request received for companies: {request.companies}")
    try:
        result = await generate_variables_impl(request.companies)
        print(f"[Variable generation] Done. Industry: {result.industry_context}, generated {len(result.generated_variables)} variables.")
    except ValueError as e:
        print(f"[Variable generation] Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except LLMError as e:
        print(f"[Variable generation] LLM error: {e.message}")
        raise HTTPException(status_code=502, detail=f"Variable generation failed: {e.message}")
    except Exception as e:
        print(f"[Variable generation] Error: {e}")
        raise

    always = get_always_variables()
    always_variables = [
        VariableResponse(id=v.id, name=v.name, category=v.category, description=None)
        for v in always
    ]
    tier2 = [
        Tier2RecommendationSchema(
            variable_id=r.variable_id,
            include=r.include,
            reason=r.reason,
        )
        for r in result.tier2_recommendations
    ]
    generated = [
        DynamicVariableDefinition(
            id=v.id,
            name=v.name,
            category=v.category,
            research_prompt=v.research_prompt,
            example_queries=v.example_queries,
            answer_spec=v.answer_spec,
            preferred_source_types=v.preferred_source_types,
            key_terms=v.key_terms,
            max_concise_chars=v.max_concise_chars,
        )
        for v in result.generated_variables
    ]
    return VariableGenerationResponse(
        industry_context=result.industry_context,
        always_variables=always_variables,
        tier2_recommendations=tier2,
        generated_variables=generated,
    )
