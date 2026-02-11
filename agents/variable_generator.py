"""
Variable generator: analyzes the Set of Competitors (SoC) and produces
contextual parameter recommendations using a strategic LLM (Claude Opus 4.6).

- Tier 2: include/exclude recommendations for "sometimes" variables
- Tier 3: ~20 industry-specific dynamic variables with full research definitions
"""

import json
import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any

from config.variables import VariableDefinition, get_sometimes_variables
from config import settings
from agents.llm_client import LLMClient, LLMError

logger = logging.getLogger(__name__)


# =============================================================================
# Data structures
# =============================================================================

@dataclass
class Tier2Recommendation:
    """Whether to include a 'sometimes' variable for this competitor set."""
    variable_id: str
    include: bool
    reason: str


@dataclass
class VariableGenerationResult:
    """Result of generate_variables(): Tier 2 recommendations + generated Tier 3 variables."""
    tier2_recommendations: List[Tier2Recommendation]
    generated_variables: List[VariableDefinition]
    industry_context: str


# =============================================================================
# Prompt
# =============================================================================

SYSTEM_PROMPT = """You are a seasoned VC at A16Z or a Partner at BCG. Your task is to analyze a set of competitor companies (the "Set of Competitors" or SoC) and recommend which research parameters to use for a competitive analysis, plus generate 10 new industry-specific parameters.

The ultimate purpose of this analysis is to determine whether or not this space has any white space or availability for a new venture to enter it.

Be precise and strategic. Avoid parameters that would be meaningless or absurd for the industry (e.g., "Technology Stack" for an airline is wrong; "Fleet Size" for a SaaS company is wrong). Focus on parameters that uncover competitive white space."""


def _build_user_prompt(companies: List[str]) -> str:
    sometimes = get_sometimes_variables()
    sometimes_list = "\n".join(
        f"- {v.id} ({v.name})" for v in sometimes
    )
    companies_list = ", ".join(companies)

    return f"""Set of Competitors (SoC): {companies_list}

---

PART 1 — Industry context
In one short sentence, name the industry or market this SoC belongs to (e.g., "Commercial aviation", "Digital payments / fintech", "EdTech / online learning"). This will be shown to the user.

---

PART 2 — Tier 2 (contextual) variables
We have a list of "sometimes included" parameters that are useful for some industries (e.g. SaaS) but not others. For each one, decide INCLUDE or EXCLUDE for this SoC and give a one-line reason.

Sometimes-included variables:
{sometimes_list}

For each variable, output:
- variable_id: the id from the list above
- include: true or false
- reason: one line explaining why it is or isn't relevant for this SoC

---

PART 3 — Tier 3 (dynamically generated) variables
Generate exactly 10 NEW parameters that would be highly relevant when comparing these specific competitors to find market white space. Think like a strategy consultant: what would an investor want to know to spot an opportunity for a new entrant?

Examples by industry:
- Airlines: Route network gaps, customer satisfaction vs price, loyalty program lock-in, fleet age/efficiency, ancillary revenue innovation.
- Fintech: Underserved customer segments, hidden fee structures, integration friction, speed of settlement, compliance burden for users.
- EdTech: Completion rates vs cost, credential value in job market, instructor quality, B2B vs B2C focus gaps.

For EACH generated parameter you MUST provide a full research definition so a research agent can run searches and synthesize answers without ambiguity. A common failure mode is vagueness. So for each parameter:

1. research_prompt: Multi-line instructions. Be explicit about what IS in scope and what is NOT. Write as if briefing a junior analyst who might confuse this with something similar.
2. example_queries: Exactly 4 Google search query strings. Use {{company}} as placeholder for the company name (e.g. "{{company}} fleet size 2024").
3. answer_spec: Exactly 3 bullet points that the research must answer.
4. key_terms: 6-8 keywords for passage selection (e.g. "fleet", "aircraft", "routes").
5. id: snake_case identifier (e.g. dyn_fleet_size, dyn_route_network). Prefix with dyn_
6. name: Short display name (e.g. "Fleet Size").
7. category: One of a few categories you use to group them (e.g. "Operations & Infrastructure", "Customer Experience", "Financials").
8. preferred_source_types: List like ["official", "tier1_news", "regulatory"] as appropriate.
9. max_concise_chars: 200 unless a different limit is better.

Output your response as a single JSON object inside <result>...</result> tags. Use this exact structure (no trailing commas):

<result>
{{
  "industry_context": "Your one sentence here",
  "tier2_recommendations": [
    {{ "variable_id": "competitive_positioning_summary", "include": true, "reason": "Relevant for any competitive set" }},
    {{ "variable_id": "technology_stack", "include": false, "reason": "Not meaningful for airlines" }}
  ],
  "generated_variables": [
    {{
      "id": "dyn_fleet_size",
      "name": "Fleet Size",
      "category": "Operations & Infrastructure",
      "research_prompt": "Find the number of aircraft in {{company}}'s fleet.\\n\\nIN SCOPE: Total aircraft count, fleet composition (narrow-body vs wide-body), recent fleet orders or retirements.\\n\\nNOT IN SCOPE: Passenger capacity in seats, number of routes, or employee count. Focus only on aircraft/assets.",
      "example_queries": ["{{company}} fleet size", "{{company}} number of aircraft", "{{company}} fleet 2024", "{{company}} aircraft count"],
      "answer_spec": ["Total fleet size (number of aircraft)", "Breakdown by type if available", "Source and date of data"],
      "key_terms": ["fleet", "aircraft", "planes", "narrow-body", "wide-body", "orders", "retirement"],
      "preferred_source_types": ["official", "tier1_news"],
      "max_concise_chars": 200
    }}
  ]
}}
</result>

Generate tier2_recommendations for EVERY sometimes variable listed above. Generate exactly 10 generated_variables. Now output the JSON:"""


def _extract_result_json(content: str) -> dict:
    """Extract JSON from <result>...</result> tags. Handles nested braces."""
    start_tag = "<result>"
    end_tag = "</result>"
    i = content.find(start_tag)
    if i == -1:
        raise ValueError("Could not find <result> in LLM response")
    start = i + len(start_tag)
    j = content.find(end_tag, start)
    if j == -1:
        raw_block = content[start:].strip()
    else:
        raw_block = content[start:j].strip()
    # Find first { and then match braces to get full JSON
    brace_start = raw_block.find("{")
    if brace_start == -1:
        raise ValueError("No JSON object in result block")
    depth = 0
    in_string = False
    escape = False
    quote_char = None
    end = brace_start
    for pos in range(brace_start, len(raw_block)):
        c = raw_block[pos]
        if escape:
            escape = False
            continue
        if c == "\\" and in_string:
            escape = True
            continue
        if not in_string:
            if c in '"\'':
                in_string = True
                quote_char = c
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    end = pos + 1
                    break
        else:
            if c == quote_char:
                in_string = False
    raw = raw_block[brace_start:end]
    # Fix common JSON issues: trailing commas
    raw = re.sub(r",\s*}", "}", raw)
    raw = re.sub(r",\s*]", "]", raw)
    return json.loads(raw)


def _dict_to_variable_definition(d: Dict[str, Any]) -> VariableDefinition:
    """Convert a dict (from LLM JSON) to VariableDefinition with tier='dynamic'."""
    return VariableDefinition(
        id=d["id"],
        name=d["name"],
        category=d["category"],
        research_prompt=d["research_prompt"],
        example_queries=list(d["example_queries"]),
        answer_spec=list(d.get("answer_spec", [])),
        preferred_source_types=list(d.get("preferred_source_types", ["official", "tier1_news"])),
        key_terms=list(d.get("key_terms", [])),
        max_concise_chars=int(d.get("max_concise_chars", 200)),
        tier="dynamic",
    )


# =============================================================================
# Main API
# =============================================================================

async def generate_variables(companies: List[str]) -> VariableGenerationResult:
    """
    Analyze the Set of Competitors and return Tier 2 recommendations plus
    ~20 generated Tier 3 variable definitions.

    Args:
        companies: List of company names (e.g. ["United Airlines", "Delta", "Lufthansa"])

    Returns:
        VariableGenerationResult with tier2_recommendations, generated_variables, industry_context

    Raises:
        LLMError: If the model call or parsing fails
    """
    if len(companies) < 2:
        raise ValueError("At least 2 companies required for variable generation")

    client = LLMClient()
    model = settings.VARIABLE_GENERATOR_MODEL
    prompt = _build_user_prompt(companies)

    print(f"[Variable generation] Calling {model} (this may take 30-90 seconds)...")
    logger.info("Calling variable generator model: %s", model)
    content = await client.complete_simple(
        prompt=prompt,
        system_prompt=SYSTEM_PROMPT,
        temperature=0.3,
        max_tokens=16000,
        model_override=model,
    )
    print("[Variable generation] LLM response received, parsing...")

    data = _extract_result_json(content)

    industry_context = data.get("industry_context", "Unknown industry")

    tier2_recommendations: List[Tier2Recommendation] = []
    for rec in data.get("tier2_recommendations", []):
        tier2_recommendations.append(Tier2Recommendation(
            variable_id=rec["variable_id"],
            include=bool(rec.get("include", True)),
            reason=str(rec.get("reason", "")),
        ))

    generated_variables: List[VariableDefinition] = []
    for g in data.get("generated_variables", []):
        try:
            generated_variables.append(_dict_to_variable_definition(g))
        except (KeyError, TypeError) as e:
            logger.warning("Skipping malformed generated variable: %s", e)
            continue

    return VariableGenerationResult(
        tier2_recommendations=tier2_recommendations,
        generated_variables=generated_variables,
        industry_context=industry_context,
    )
