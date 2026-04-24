"""
Graveyard Variable Generator: analyzes a set of defunct companies and generates
4-6 failure-focused research parameters, following the VariableGenerator pattern.
"""

import json
import re
import logging
from typing import List, Dict, Any

from config.variables import VariableDefinition
from config import settings
from agents.llm_client import LLMClient, LLMError

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a corporate failure analyst and business historian. Your task is to analyze a set of defunct companies and generate failure-focused research parameters that will help a competitive intelligence team understand WHY these companies failed and what lessons to draw.

Each parameter should be specific enough that a research agent can gather structured evidence for each defunct company."""


def _build_prompt(
    dead_companies: List[str],
    industry_context: str,
    living_companies: List[str],
) -> str:
    dead_list = ", ".join(dead_companies)
    living_list = ", ".join(living_companies) if living_companies else "N/A"

    return f"""Defunct companies to analyze: {dead_list}
Industry context: {industry_context}
Living competitors (for reference, do NOT generate parameters about these): {living_list}

Generate exactly 5 failure-focused research parameters for analyzing WHY these defunct companies failed. Each parameter must enable a research agent to gather structured evidence per company.

Think about these dimensions:
- What was the primary cause of failure? (financial, competitive, regulatory, technology disruption, mismanagement)
- What was the trajectory from peak to collapse? How fast did it happen?
- What strategic decisions accelerated the decline?
- What structural industry vulnerabilities does this failure expose?
- What lessons should a new entrant internalize?

For EACH parameter, provide a full research definition:

1. id: snake_case, prefix with gy_ (e.g. gy_primary_failure_mode)
2. name: Short display name
3. category: "Failure Analysis"
4. research_prompt: Multi-line instructions for a research agent. Be explicit about scope.
   Use {{company}} as placeholder for the company name.
5. example_queries: Exactly 4 search query strings with {{company}} placeholder.
6. answer_spec: Exactly 3 bullet points the research must answer.
7. key_terms: 6-8 keywords for passage selection.
8. preferred_source_types: List like ["tier1_news", "academic", "official"]
9. max_concise_chars: 200

Output a single JSON object inside <result>...</result>:

<result>
{{
  "generated_variables": [
    {{
      "id": "gy_primary_failure_mode",
      "name": "Primary Failure Mode",
      "category": "Failure Analysis",
      "research_prompt": "Identify the primary cause of {{company}}'s collapse...\\n\\nIN SCOPE: ...\\n\\nNOT IN SCOPE: ...",
      "example_queries": ["{{company}} bankruptcy cause", "{{company}} why did it fail", "{{company}} collapse reason", "{{company}} shutdown"],
      "answer_spec": ["Primary cause of failure", "Contributing factors", "Timeline of decline"],
      "key_terms": ["bankruptcy", "collapse", "failure", "shutdown", "decline", "insolvency"],
      "preferred_source_types": ["tier1_news", "academic"],
      "max_concise_chars": 200
    }}
  ]
}}
</result>

Generate exactly 5 parameters. Now output the JSON:"""


def _extract_result_json(content: str) -> dict:
    """Extract JSON from <result>...</result> tags, or fall back to bare JSON."""
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
    """Convert a dict to VariableDefinition with tier='dynamic'."""
    return VariableDefinition(
        id=d["id"],
        name=d["name"],
        category=d.get("category", "Failure Analysis"),
        research_prompt=d["research_prompt"],
        example_queries=list(d.get("example_queries", [])),
        answer_spec=list(d.get("answer_spec", [])),
        preferred_source_types=list(d.get("preferred_source_types", ["tier1_news", "academic"])),
        key_terms=list(d.get("key_terms", [])),
        max_concise_chars=int(d.get("max_concise_chars", 200)),
        tier="dynamic",
    )


async def generate_graveyard_variables(
    dead_companies: List[str],
    industry_context: str = "",
    living_companies: List[str] = None,
) -> List[VariableDefinition]:
    """
    Generate 4-6 failure-focused research parameters for graveyard analysis.

    Args:
        dead_companies: Names of defunct companies
        industry_context: Industry description
        living_companies: Living competitors (for context)

    Returns:
        List of VariableDefinition objects for the graveyard pipeline
    """
    if not dead_companies:
        raise ValueError("At least 1 defunct company required")

    client = LLMClient()
    model = settings.VARIABLE_GENERATOR_MODEL
    fallback_model = settings.VARIABLE_GENERATOR_FALLBACK_MODEL
    prompt = _build_prompt(dead_companies, industry_context or "Unknown", living_companies or [])

    logger.info("Generating graveyard variables with model: %s", model)
    content = await client.complete_simple(
        prompt=prompt,
        system_prompt=SYSTEM_PROMPT,
        temperature=0.3,
        max_tokens=8000,
        model_override=model,
        fallback_model=fallback_model,
    )

    data = _extract_result_json(content)

    variables: List[VariableDefinition] = []
    for g in data.get("generated_variables", []):
        try:
            v = _dict_to_variable_definition(g)
            variables.append(v)
        except (KeyError, TypeError) as e:
            logger.warning("Skipping malformed graveyard variable: %s", e)
            continue

    if not variables:
        raise LLMError("Graveyard variable generation returned no variables")

    return variables[:6]
