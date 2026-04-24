"""
Variable generator: analyzes the Set of Competitors (SoC) and produces
contextual parameter recommendations using a strategic LLM (e.g. deepseek-v3.2).

- Tier 2: include/exclude recommendations for "sometimes" variables
- Tier 3: industry-specific dynamic variables with full research definitions
"""

import asyncio
import json
import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any

from config.variables import VariableDefinition, get_sometimes_variables, get_always_variables
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
    generated_variable_rationales: Dict[str, str]  # variable id -> rationale for Tier 3
    always_parameter_contexts: Dict[str, str]  # variable id -> one-line context for Tier 1
    industry_context: str


# =============================================================================
# Prompt
# =============================================================================

SYSTEM_PROMPT = """You are a seasoned VC at A16Z or a Partner at BCG. Your task is to analyze a set of competitor companies (the "Set of Competitors" or SoC) and recommend which research parameters to use for a competitive analysis, plus generate 10 new industry-specific parameters.

The ultimate purpose of this analysis is to determine whether or not this space has any white space or availability for a new venture to enter it.

Be precise and strategic. Avoid parameters that would be meaningless or absurd for the industry (e.g., "Technology Stack" for an airline is wrong; "Fleet Size" for a SaaS company is wrong). Focus on parameters that uncover competitive white space.

CRITICAL INSTRUCTION: You must strictly adhere to the provided Set of Competitors (SoC). Do NOT mention, use as examples, or allude to any companies that are NOT in the provided list. Your analysis and rationales must be based ONLY on the companies explicitly listed in the SoC."""

METADATA_MAX_TOKENS = 5000
DYNAMIC_MAX_TOKENS = 10000


def _build_prompt_context(companies: List[str], company_profiles: List[str] = ["public_mature"]) -> str:
    """Shared company/profile context for split variable-generation prompts."""
    companies_list = ", ".join(companies)

    profile_contexts = []
    if "public_mature" in company_profiles:
        profile_contexts.append("- Public / Mature: Focus on financials, market share, analyst ratings, regulatory risk.")
    if "public_emerging" in company_profiles:
        profile_contexts.append("- Public / Emerging: Focus on growth metrics, unit economics, path to profitability, market disruption.")
    if "private_venture" in company_profiles:
        profile_contexts.append("- Private / Venture: Focus on founder background, tech stack, hiring velocity, social signal, product velocity.")
    if "private_established" in company_profiles:
        profile_contexts.append("- Private / Established: Focus on patents, trade shows, supply chain, certifications, longevity, B2B reputation.")

    profile_instruction = "\n".join(profile_contexts)
    mixed_instruction = ""
    if len(company_profiles) > 1:
        mixed_instruction = (
            "The set includes a MIX of company profiles. Ensure parameters cover relevant signals for ALL types "
            "(e.g. financial transparency for public firms AND operational signals for private ones)."
        )

    return f"""Set of Competitors (SoC): {companies_list}
Company Profiles: {", ".join(company_profiles)}

IMPORTANT: The companies in this set fit the following profiles:
{profile_instruction}

{mixed_instruction}

CRITICAL: Restrict your entire response (including rationales, parameter contexts, and examples) ONLY to the companies listed above. Do NOT mention any other companies."""


def _build_metadata_prompt(companies: List[str], company_profiles: List[str] = ["public_mature"]) -> str:
    sometimes = get_sometimes_variables()
    sometimes_list = "\n".join(f"- {v.id} ({v.name})" for v in sometimes)
    always = get_always_variables()
    always_list = "\n".join(f"- {v.id} ({v.name})" for v in always)

    return f"""{_build_prompt_context(companies, company_profiles)}

---

PART 0 — Always-included parameters context
The following parameters are always included in every analysis. For each one, provide a one-line parameter_context that explains why this dimension matters when comparing this specific SoC (e.g. for UVP: "How each player positions its core promise shapes where white space remains.").

Always-included parameters:
{always_list}

Output a JSON object that maps each variable id to a one-line string. You will include this in the full JSON under "always_parameter_contexts".

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

Output your response as a single JSON object inside <result>...</result> tags. Use this exact structure (no trailing commas):

<result>
{{
  "always_parameter_contexts": {{
    "unique_value_proposition": "How each player positions its core promise shapes where white space remains.",
    "positioning": "Market segment and positioning reveal premium vs value gaps in the set."
  }},
  "industry_context": "Your one sentence here",
  "tier2_recommendations": [
    {{ "variable_id": "competitive_positioning_summary", "include": true, "reason": "Relevant for any competitive set" }},
    {{ "variable_id": "technology_stack", "include": false, "reason": "Not meaningful for airlines" }}
  ]
}}
</result>

Generate always_parameter_contexts for EVERY always-included variable listed in PART 0. Generate tier2_recommendations for EVERY sometimes variable listed above. Do not include any additional keys. Now output the JSON:"""


def _build_dynamic_prompt(companies: List[str], company_profiles: List[str] = ["public_mature"]) -> str:
    return f"""{_build_prompt_context(companies, company_profiles)}

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
10. rationale: One sentence explaining why this parameter is relevant for this specific SoC (e.g. "Gojek and Grab are super-apps; Uber/Lyft are not; this dimension reveals diversification strategy."). This will be shown to the user so they understand why the parameter was suggested.

Output a single JSON object inside <result>...</result> with key "generated_variables". Use this exact structure (no trailing commas):

<result>
{{
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
      "max_concise_chars": 200,
      "rationale": "Fleet size and composition directly affect capacity and cost structure; comparing these highlights operational scale and investment priorities across the set."
    }}
  ]
}}
</result>

Generate exactly 10 generated_variables. Do not include any additional keys. Now output the JSON:"""


def _extract_result_json(content: str) -> dict:
    """Extract JSON from <result>...</result> tags, or fall back to bare JSON."""
    start_tag = "<result>"
    end_tag = "</result>"
    i = content.find(start_tag)
    if i != -1:
        start = i + len(start_tag)
        j = content.find(end_tag, start)
        if j == -1:
            raw_block = content[start:].strip()
        else:
            raw_block = content[start:j].strip()
    else:
        logger.warning("<result> tags not found in LLM response; attempting bare JSON extraction")
        raw_block = content.strip()
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


def _parse_metadata_result(data: Dict[str, Any]) -> tuple[str, Dict[str, str], List[Tier2Recommendation]]:
    """Parse metadata response into industry context, always contexts, and tier-2 recommendations."""
    industry_context = data.get("industry_context", "Unknown industry")
    always_parameter_contexts: Dict[str, str] = {}
    for k, v in data.get("always_parameter_contexts", {}).items():
        if isinstance(k, str) and isinstance(v, str):
            always_parameter_contexts[k] = v.strip()

    tier2_recommendations: List[Tier2Recommendation] = []
    for rec in data.get("tier2_recommendations", []):
        tier2_recommendations.append(Tier2Recommendation(
            variable_id=rec["variable_id"],
            include=bool(rec.get("include", True)),
            reason=str(rec.get("reason", "")),
        ))
    return industry_context, always_parameter_contexts, tier2_recommendations


def _parse_generated_variables(data: Dict[str, Any]) -> tuple[List[VariableDefinition], Dict[str, str]]:
    """Parse generated-variable response into typed definitions and rationales."""
    generated_variables: List[VariableDefinition] = []
    generated_variable_rationales: Dict[str, str] = {}
    for g in data.get("generated_variables", []):
        try:
            v = _dict_to_variable_definition(g)
            generated_variables.append(v)
            generated_variable_rationales[v.id] = str(g.get("rationale", "")).strip()
        except (KeyError, TypeError) as e:
            logger.warning("Skipping malformed generated variable: %s", e)
            continue
    return generated_variables, generated_variable_rationales


# =============================================================================
# Main API
# =============================================================================

async def generate_variables(companies: List[str], company_profiles: List[str] = ["public_mature"]) -> VariableGenerationResult:
    """
    Analyze the Set of Competitors and return Tier 2 recommendations plus
    ~20 generated Tier 3 variable definitions.

    Args:
        companies: List of company names (e.g. ["United Airlines", "Delta", "Lufthansa"])
        company_profiles: List of profiles (e.g. ["public_mature", "private_established"])

    Returns:
        VariableGenerationResult with tier2_recommendations, generated_variables, industry_context

    Raises:
        LLMError: If the model call or parsing fails
    """
    if len(companies) < 2:
        raise ValueError("At least 2 companies required for variable generation")

    client = LLMClient()
    model = settings.VARIABLE_GENERATOR_MODEL
    fallback_model = settings.VARIABLE_GENERATOR_FALLBACK_MODEL
    metadata_prompt = _build_metadata_prompt(companies, company_profiles)
    dynamic_prompt = _build_dynamic_prompt(companies, company_profiles)

    print(f"[Variable generation] Calling split prompts via {model}...")
    logger.info("Calling split variable generator prompts via model: %s", model)
    metadata_content, dynamic_content = await asyncio.gather(
        client.complete_simple(
            prompt=metadata_prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=METADATA_MAX_TOKENS,
            model_override=model,
            fallback_model=fallback_model,
        ),
        client.complete_simple(
            prompt=dynamic_prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=DYNAMIC_MAX_TOKENS,
            model_override=model,
            fallback_model=fallback_model,
        ),
    )
    print("[Variable generation] Split LLM responses received, parsing...")

    metadata = _extract_result_json(metadata_content)
    dynamic = _extract_result_json(dynamic_content)
    industry_context, always_parameter_contexts, tier2_recommendations = _parse_metadata_result(metadata)
    generated_variables, generated_variable_rationales = _parse_generated_variables(dynamic)

    return VariableGenerationResult(
        tier2_recommendations=tier2_recommendations,
        generated_variables=generated_variables,
        generated_variable_rationales=generated_variable_rationales,
        always_parameter_contexts=always_parameter_contexts,
        industry_context=industry_context,
    )
