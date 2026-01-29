"""
Variables API routes.
"""

import sys
from pathlib import Path
from fastapi import APIRouter

# Ensure project root is in path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.variables import VARIABLES, get_variables_by_category
from api.models import VariableResponse, VariableCategoryResponse

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
