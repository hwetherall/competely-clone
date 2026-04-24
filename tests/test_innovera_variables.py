"""
Tests for the static Innovera lens variable set.
"""

import asyncio

from api.models import GenerateVariablesRequest
from api.routes.variables import generate_variables
from api.services.research_runner import _build_variable_lookup, INNOVERA_TAKEAWAY_ID
from config.innovera_variables import (
    get_all_innovera_variable_ids,
    get_innovera_always,
    get_innovera_variable,
)


def test_innovera_variable_set_shape():
    variables = get_innovera_always()
    ids = get_all_innovera_variable_ids()

    assert len(variables) == 7
    assert INNOVERA_TAKEAWAY_ID in ids
    assert len(ids) == len(set(ids))
    assert all(v.id.startswith("inv_") for v in variables)
    assert get_innovera_variable("inv_gtm_motion").name == "GTM Motion"
    assert "Innovera" in get_innovera_variable(INNOVERA_TAKEAWAY_ID).research_prompt


def test_innovera_generate_variables_response_is_static():
    request = GenerateVariablesRequest(
        companies=["Alpha", "Beta"],
        parameter_path="innovera",
    )
    response = asyncio.run(generate_variables(request))

    assert response.industry_context.startswith("Innovera lens")
    assert [v.id for v in response.always_variables] == get_all_innovera_variable_ids()
    assert response.tier2_recommendations == []
    assert response.generated_variables == []
    assert response.always_parameter_contexts[INNOVERA_TAKEAWAY_ID]


def test_research_runner_lookup_supports_innovera_path():
    lookup = _build_variable_lookup(
        ["inv_offer_shape", INNOVERA_TAKEAWAY_ID],
        parameter_path="innovera",
    )

    assert lookup["inv_offer_shape"].name == "Offer Shape & Scope"
    assert lookup[INNOVERA_TAKEAWAY_ID].category == "Synthesis"

