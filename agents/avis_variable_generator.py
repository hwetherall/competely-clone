"""
AVIS Variable Generator: analyzes the Set of Competitors through the
AVIS Competitive Analysis framework (Innovera constitution, Chapter 4).

Uses the same tier structure as the Competely generator:
- Tier 1 (always): 10 AVIS core parameters with per-run context
- Tier 2 (sometimes): 8 AVIS contextual parameters with include/exclude
- Tier 3 (dynamic): 10 industry-specific parameters generated through the AVIS lens

The key difference: AVIS parameters focus on investment-thesis dimensions
(moats, funding, GTM, team, exit readiness) rather than product comparison.
"""

import asyncio
import json
import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any

from config.avis_variables import get_avis_always, get_avis_sometimes
from config.variables import VariableDefinition
from config import settings
from agents.llm_client import LLMClient, LLMError

logger = logging.getLogger(__name__)


@dataclass
class AvisTier2Recommendation:
    variable_id: str
    include: bool
    reason: str


@dataclass
class AvisVariableGenerationResult:
    tier2_recommendations: List[AvisTier2Recommendation]
    generated_variables: List[VariableDefinition]
    generated_variable_rationales: Dict[str, str]
    always_parameter_contexts: Dict[str, str]
    industry_context: str


# =============================================================================
# AVIS-specific prompt
# =============================================================================

SYSTEM_PROMPT = """You are a senior analyst at a top-tier venture capital firm (A16Z, Sequoia, or Benchmark) conducting due diligence on a competitive landscape. Your analytical framework is AVIS (Chapter 4: Competitive Analysis), which evaluates competitors through 8 strategic lenses:

1. Product Capability — Feature breadth/depth, UX, scalability, integrations
2. Business Model — Pricing structure, revenue streams, gross margin profile
3. Market Traction — Revenue, user base, client logos, churn, net retention
4. Funding & Ownership — Capital raised, backers, strategic investors
5. Go-to-Market Engine — Direct vs indirect sales, self-serve vs enterprise, CAC/LTV
6. IP & Defensibility — Patents, data moats, switching costs, regulatory licenses
7. Team & Leadership — Founder background, exec turnover, hiring velocity
8. Exit Readiness — IPO potential, past M&A discussions, interest from strategics

Your goal: determine whether the market has whitespace for a new venture, where defensible positions exist, and what structural dynamics shape the competitive environment.

CRITICAL INSTRUCTION: You must strictly adhere to the provided Set of Competitors (SoC). Do NOT mention, use as examples, or allude to any companies that are NOT in the provided list."""

METADATA_MAX_TOKENS = 4500
DYNAMIC_MAX_TOKENS = 9500


def _build_avis_prompt_context(companies: List[str], company_profiles: List[str] = ["public_mature"]) -> str:
    companies_str = ", ".join(companies)

    profile_contexts = []
    if "public_mature" in company_profiles:
        profile_contexts.append("- Public / Mature: Emphasize financials, market share, moat durability, exit comps.")
    if "public_emerging" in company_profiles:
        profile_contexts.append("- Public / Emerging: Emphasize growth metrics, unit economics, path to profitability, GTM velocity.")
    if "private_venture" in company_profiles:
        profile_contexts.append("- Private / Venture: Emphasize founder quality, funding trajectory, product velocity, hiring signals.")
    if "private_established" in company_profiles:
        profile_contexts.append("- Private / Established: Emphasize IP, certifications, B2B reputation, supply chain, longevity.")

    profile_instruction = "\n".join(profile_contexts)
    mixed_instruction = ""
    if len(company_profiles) > 1:
        mixed_instruction = "The set includes a MIX of company profiles. Ensure parameters cover relevant signals for ALL types."

    return f"""Set of Competitors (SoC): {companies_str}
Company Profiles: {", ".join(company_profiles)}

IMPORTANT: These companies fit the following profiles:
{profile_instruction}
{mixed_instruction}

CRITICAL: Restrict your entire response ONLY to the companies listed above. Do NOT mention any other companies."""


def _build_avis_metadata_prompt(companies: List[str], company_profiles: List[str] = ["public_mature"]) -> str:
    sometimes = get_avis_sometimes()
    sometimes_list = "\n".join(f"- {v.id} ({v.name}): {v.category}" for v in sometimes)

    always = get_avis_always()
    always_list = "\n".join(f"- {v.id} ({v.name}): {v.category}" for v in always)

    return f"""{_build_avis_prompt_context(companies, company_profiles)}

---

PART 0 — Always-included parameter contexts (AVIS Tier 1)
The following AVIS parameters are always included. For each one, provide a one-line parameter_context explaining why this dimension matters when comparing THIS specific SoC through the AVIS investment lens (e.g. "Funding trajectories reveal who has runway to outspend on GTM and R&D.").

Always-included AVIS parameters:
{always_list}

Output a JSON object mapping each variable id to a one-line context string.

---

PART 1 — Industry context
In one short sentence, name the industry or market this SoC belongs to.

---

PART 2 — Tier 2 (contextual AVIS parameters)
For each of the following contextual AVIS parameters, decide INCLUDE or EXCLUDE for this SoC and give a one-line reason. Think about what an investor would care about for THIS specific set:

{sometimes_list}

Output your response as a single JSON object inside <result>...</result> tags:

<result>
{{
  "always_parameter_contexts": {{
    "avis_product_capability": "Context sentence...",
    "avis_business_model": "Context sentence..."
  }},
  "industry_context": "Your one sentence here",
  "tier2_recommendations": [
    {{ "variable_id": "avis_exit_readiness", "include": true, "reason": "Relevant because..." }},
    {{ "variable_id": "avis_deal_comps", "include": false, "reason": "Not relevant because..." }}
  ]
}}
</result>

Generate always_parameter_contexts for EVERY always-included variable. Generate tier2_recommendations for EVERY sometimes variable. Do not include any additional keys. Now output the JSON:"""


def _build_avis_dynamic_prompt(companies: List[str], company_profiles: List[str] = ["public_mature"]) -> str:
    return f"""{_build_avis_prompt_context(companies, company_profiles)}

Generate exactly 10 NEW parameters that would be highly revealing when analyzing this competitive landscape through the AVIS investment lens. These should complement (not duplicate) the Tier 1 and Tier 2 parameters above.

Focus on dimensions an investor or strategic buyer would need to assess:
- Structural market dynamics (consolidation trends, winner-take-all dynamics, fragmentation)
- Hidden competitive advantages or vulnerabilities
- Go-to-market efficiency signals
- Moat durability under different scenarios
- Customer economics that reveal long-term viability

For EACH generated parameter provide a full research definition:

1. research_prompt: Multi-line instructions. Be explicit about IN SCOPE and NOT IN SCOPE.
2. example_queries: Exactly 4 Google search query strings. Use {{company}} as placeholder.
3. answer_spec: Exactly 3 bullet points the research must answer.
4. key_terms: 6-8 keywords for passage selection.
5. id: snake_case with dyn_avis_ prefix (e.g. dyn_avis_consolidation_trend).
6. name: Short display name.
7. category: One of the 8 AVIS categories, or "Market Dynamics", "Customer Economics", "Strategic Positioning".
8. preferred_source_types: List like ["official", "tier1_news", "regulatory"].
9. max_concise_chars: 200 unless a different limit is better.
10. rationale: One sentence explaining why this parameter matters for this SoC from an investment perspective.

Output your response as a single JSON object inside <result>...</result> tags:

<result>
{{
  "generated_variables": [
    {{
      "id": "dyn_avis_consolidation_trend",
      "name": "Consolidation Trend",
      "category": "Market Dynamics",
      "research_prompt": "Detailed instructions...",
      "example_queries": ["{{company}} market consolidation", "..."],
      "answer_spec": ["Point 1", "Point 2", "Point 3"],
      "key_terms": ["consolidation", "M&A", "..."],
      "preferred_source_types": ["tier1_news", "analyst"],
      "max_concise_chars": 200,
      "rationale": "Why this matters for this SoC..."
    }}
  ]
}}
</result>

Generate exactly 10 generated_variables. Do not include any additional keys. Now output the JSON:"""


def _extract_result_json(content: str) -> dict:
    start_tag = "<result>"
    end_tag = "</result>"
    i = content.find(start_tag)
    if i != -1:
        start = i + len(start_tag)
        j = content.find(end_tag, start)
        raw_block = content[start:j].strip() if j != -1 else content[start:].strip()
    else:
        logger.warning("<result> tags not found in LLM response; attempting bare JSON extraction")
        raw_block = content.strip()
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
    raw = re.sub(r",\s*}", "}", raw)
    raw = re.sub(r",\s*]", "]", raw)
    return json.loads(raw)


def _dict_to_variable_definition(d: Dict[str, Any]) -> VariableDefinition:
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


def _parse_metadata_result(data: Dict[str, Any]) -> tuple[str, Dict[str, str], List[AvisTier2Recommendation]]:
    industry_context = data.get("industry_context", "Unknown industry")
    always_parameter_contexts: Dict[str, str] = {}
    for k, v in data.get("always_parameter_contexts", {}).items():
        if isinstance(k, str) and isinstance(v, str):
            always_parameter_contexts[k] = v.strip()

    tier2_recommendations: List[AvisTier2Recommendation] = []
    for rec in data.get("tier2_recommendations", []):
        tier2_recommendations.append(AvisTier2Recommendation(
            variable_id=rec["variable_id"],
            include=bool(rec.get("include", True)),
            reason=str(rec.get("reason", "")),
        ))
    return industry_context, always_parameter_contexts, tier2_recommendations


def _parse_generated_variables(data: Dict[str, Any]) -> tuple[List[VariableDefinition], Dict[str, str]]:
    generated_variables: List[VariableDefinition] = []
    generated_variable_rationales: Dict[str, str] = {}
    for g in data.get("generated_variables", []):
        try:
            v = _dict_to_variable_definition(g)
            generated_variables.append(v)
            generated_variable_rationales[v.id] = str(g.get("rationale", "")).strip()
        except (KeyError, TypeError) as e:
            logger.warning("Skipping malformed AVIS generated variable: %s", e)
            continue
    return generated_variables, generated_variable_rationales


# =============================================================================
# Main API
# =============================================================================

async def generate_avis_variables(
    companies: List[str],
    company_profiles: List[str] = ["public_mature"],
) -> AvisVariableGenerationResult:
    """
    Analyze the Set of Competitors through the AVIS lens and return
    Tier 2 recommendations + 10 generated Tier 3 variable definitions.
    """
    if len(companies) < 2:
        raise ValueError("At least 2 companies required for AVIS variable generation")

    client = LLMClient()
    model = settings.VARIABLE_GENERATOR_MODEL
    metadata_prompt = _build_avis_metadata_prompt(companies, company_profiles)
    dynamic_prompt = _build_avis_dynamic_prompt(companies, company_profiles)

    print(f"[AVIS variable generation] Calling split prompts via {model}...")
    logger.info("Calling split AVIS variable generator prompts via model: %s", model)
    metadata_content, dynamic_content = await asyncio.gather(
        client.complete_simple(
            prompt=metadata_prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=METADATA_MAX_TOKENS,
            model_override=model,
        ),
        client.complete_simple(
            prompt=dynamic_prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=DYNAMIC_MAX_TOKENS,
            model_override=model,
        ),
    )
    print("[AVIS variable generation] Split LLM responses received, parsing...")

    metadata = _extract_result_json(metadata_content)
    dynamic = _extract_result_json(dynamic_content)
    industry_context, always_parameter_contexts, tier2_recommendations = _parse_metadata_result(metadata)
    generated_variables, generated_variable_rationales = _parse_generated_variables(dynamic)

    return AvisVariableGenerationResult(
        tier2_recommendations=tier2_recommendations,
        generated_variables=generated_variables,
        generated_variable_rationales=generated_variable_rationales,
        always_parameter_contexts=always_parameter_contexts,
        industry_context=industry_context,
    )
