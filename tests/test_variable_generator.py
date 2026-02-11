"""
Tests for the variable generator (Tier 2 recommendations + Tier 3 dynamic variables).
Tests parsing and structure without calling the LLM.
"""

import pytest
from agents.variable_generator import (
    _extract_result_json,
    _dict_to_variable_definition,
    Tier2Recommendation,
    VariableGenerationResult,
)
from config.variables import get_always_variables, get_sometimes_variables


SAMPLE_LLM_RESPONSE = """
Some preamble text here.

<result>
{
  "industry_context": "Commercial aviation",
  "tier2_recommendations": [
    { "variable_id": "competitive_positioning_summary", "include": true, "reason": "Relevant" },
    { "variable_id": "technology_stack", "include": false, "reason": "Not meaningful for airlines" }
  ],
  "generated_variables": [
    {
      "id": "dyn_fleet_size",
      "name": "Fleet Size",
      "category": "Operations & Infrastructure",
      "research_prompt": "Find fleet size for {company}. IN SCOPE: aircraft count.",
      "example_queries": ["{company} fleet size", "{company} aircraft count"],
      "answer_spec": ["Total fleet size", "Breakdown by type", "Source and date"],
      "key_terms": ["fleet", "aircraft", "planes"],
      "preferred_source_types": ["official", "tier1_news"],
      "max_concise_chars": 200
    }
  ]
}
</result>
"""


def test_extract_result_json():
    """Test JSON extraction from <result> tags with nested braces."""
    data = _extract_result_json(SAMPLE_LLM_RESPONSE)
    assert data["industry_context"] == "Commercial aviation"
    assert len(data["tier2_recommendations"]) == 2
    assert data["tier2_recommendations"][0]["variable_id"] == "competitive_positioning_summary"
    assert data["tier2_recommendations"][0]["include"] is True
    assert data["tier2_recommendations"][1]["variable_id"] == "technology_stack"
    assert data["tier2_recommendations"][1]["include"] is False
    assert len(data["generated_variables"]) == 1
    gen = data["generated_variables"][0]
    assert gen["id"] == "dyn_fleet_size"
    assert gen["name"] == "Fleet Size"
    assert gen["category"] == "Operations & Infrastructure"
    assert "fleet" in gen["research_prompt"]
    assert len(gen["example_queries"]) == 2
    assert gen["example_queries"][0] == "{company} fleet size"
    assert gen["max_concise_chars"] == 200


def test_extract_result_json_trailing_comma():
    """Parser strips trailing commas so JSON parses."""
    raw = "<result>\n{\"industry_context\": \"Test\", \"tier2_recommendations\": [], \"generated_variables\": []}\n</result>"
    data = _extract_result_json(raw)
    assert data["industry_context"] == "Test"
    assert data["tier2_recommendations"] == []
    assert data["generated_variables"] == []


def test_dict_to_variable_definition():
    """Test converting LLM JSON dict to VariableDefinition with tier=dynamic."""
    d = {
        "id": "dyn_fleet_size",
        "name": "Fleet Size",
        "category": "Operations",
        "research_prompt": "Find fleet for {company}.",
        "example_queries": ["{company} fleet"],
        "answer_spec": ["Fleet size"],
        "key_terms": ["fleet"],
        "preferred_source_types": ["official"],
        "max_concise_chars": 180,
    }
    v = _dict_to_variable_definition(d)
    assert v.id == "dyn_fleet_size"
    assert v.name == "Fleet Size"
    assert v.tier == "dynamic"
    assert v.max_concise_chars == 180
    assert "{company}" in v.example_queries[0]


def test_always_and_sometimes_tiers():
    """Sanity check: we have 12 always and 8 sometimes variables."""
    always = get_always_variables()
    sometimes = get_sometimes_variables()
    assert len(always) == 12
    assert len(sometimes) == 8
    always_ids = {v.id for v in always}
    sometimes_ids = {v.id for v in sometimes}
    assert always_ids & sometimes_ids == set()
    assert "unique_value_proposition" in always_ids
    assert "technology_stack" in sometimes_ids
