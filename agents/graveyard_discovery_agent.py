"""
Graveyard Discovery Agent: uses Perplexity Sonar Pro to find 5 defunct
companies in the same sector as the living competitors.

Called during the plan wizard when the user enables Post-Mortem Intelligence.
"""

import json
import re
import logging
from typing import List, Dict, Any, Optional

from agents.llm_client import LLMClient, LLMError
from agents.v2_schemas import GraveyardCompany
from config import settings

logger = logging.getLogger(__name__)

MODEL_RESEARCH = settings.PLAN_RESEARCH_MODEL
MODEL_RESEARCH_FALLBACK = settings.PLAN_RESEARCH_FALLBACK_MODEL

DISCOVERY_SYSTEM = """You are a business history researcher. Given a set of living competitors and their industry, search the web and identify 5 companies that operated in the same space but have since collapsed, gone bankrupt, ceased operations, or been forced into a distress acquisition. Focus on well-documented failures that offer meaningful lessons. Output ONLY valid JSON inside <result>...</result>."""

DISCOVERY_PROMPT = """Living competitors in scope: {companies_list}
Industry context: {industry_context}
{sector_hint_line}
Search the web and identify exactly 5 companies that:
1. Operated in the same industry or closely adjacent space as the companies above
2. Have collapsed, gone bankrupt, ceased operations, or been acquired under distress
3. Are well-documented enough that meaningful failure analysis is possible
4. Represent a DIVERSE set of failure modes (don't pick 5 companies that all failed for the same reason)

For EACH company provide:
- name: Official company name
- years_active: Approximate years of operation (e.g. "1927-2001")
- peak_description: 1-2 sentences on what they were at their peak
- reason_summary: 1-line reason for collapse
- confidence: "high" if well-documented defunct company, "medium" if somewhat uncertain, "low" if questionable

Output a single JSON object inside <result>...</result> with key "companies" (array of 5 objects).

<result>
{{
  "companies": [
    {{
      "name": "Company Name",
      "years_active": "1950-2002",
      "peak_description": "Was the largest X in Y...",
      "reason_summary": "Collapsed due to...",
      "confidence": "high"
    }}
  ]
}}
</result>

Your discovery:"""


def _extract_json_block(content: str) -> dict:
    """Extract JSON from <result>...</result> tags."""
    i = content.find("<result>")
    if i != -1:
        start = i + len("<result>")
        j = content.find("</result>", start)
        content = content[start:j].strip() if j != -1 else content[start:].strip()
    brace_start = content.find("{")
    if brace_start == -1:
        raise ValueError("No JSON object in response")
    depth = 0
    in_string = False
    escape = False
    quote_char = None
    end = brace_start
    for pos in range(brace_start, len(content)):
        c = content[pos]
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
    raw = content[brace_start:end]
    raw = re.sub(r",\s*}", "}", raw)
    raw = re.sub(r",\s*]", "]", raw)
    return json.loads(raw)


async def discover_graveyard_companies(
    companies: List[str],
    industry_context: str = "",
    sector_hint: str = "",
) -> List[GraveyardCompany]:
    """
    Use Perplexity Sonar Pro to discover 5 defunct companies in the sector.

    Args:
        companies: Living competitor names
        industry_context: Industry description (from plan wizard)
        sector_hint: Optional additional sector hint from user

    Returns:
        List of 5 GraveyardCompany objects
    """
    if not companies:
        raise ValueError("At least 1 living company required for graveyard discovery")

    client = LLMClient()
    companies_list = ", ".join(companies)
    sector_hint_line = f"Additional sector context: {sector_hint}" if sector_hint else ""

    prompt = DISCOVERY_PROMPT.format(
        companies_list=companies_list,
        industry_context=industry_context or "Unknown",
        sector_hint_line=sector_hint_line,
    )

    content = await client.complete_simple(
        prompt=prompt,
        system_prompt=DISCOVERY_SYSTEM,
        temperature=0.3,
        max_tokens=2048,
        model_override=MODEL_RESEARCH,
        fallback_model=MODEL_RESEARCH_FALLBACK,
    )

    results: List[GraveyardCompany] = []
    try:
        data = _extract_json_block(content)
        for c in data.get("companies", [])[:7]:
            results.append(GraveyardCompany(
                name=c.get("name", ""),
                years_active=c.get("years_active", ""),
                peak_description=c.get("peak_description", ""),
                reason_summary=c.get("reason_summary", ""),
                confidence=c.get("confidence", "medium"),
            ))
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.warning("Failed to parse graveyard discovery response: %s", e)

    if not results:
        raise LLMError("Graveyard discovery returned no companies")

    return results[:5]
