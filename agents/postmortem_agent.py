"""
Post-Mortem Agent: synthesizes a PostMortemBrief from graveyard parameter reports.
Single LLM call using Claude Opus 4.6.
"""

import json
import logging
import re
from typing import List, Dict, Any, Optional

from agents.llm_client import LLMClient
from agents.v2_schemas import (
    PostMortemBrief,
    CautionaryNarrative,
    ComparativeReport,
)
from agents.v2_prompts import (
    POSTMORTEM_BRIEF_SYSTEM,
    POSTMORTEM_BRIEF_PROMPT,
    format_graveyard_summaries_for_postmortem,
    build_venture_context_block,
)
from config import settings

logger = logging.getLogger(__name__)

EXECUTIVE_MODEL = settings.EXECUTIVE_MODEL


class PostMortemAgent:
    """Produces the PostMortemBrief from graveyard parameter reports."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or LLMClient()

    async def synthesize_brief(
        self,
        dead_companies_list: str,
        living_companies_list: str,
        reports: List[ComparativeReport],
        industry_context: str = "",
        venture_context: str = "",
    ) -> PostMortemBrief:
        """
        Produce PostMortemBrief from graveyard parameter reports.
        """
        parameter_summaries = format_graveyard_summaries_for_postmortem(reports)
        vc_parts = build_venture_context_block(venture_context)

        prompt = POSTMORTEM_BRIEF_PROMPT.format(
            companies_list=dead_companies_list,
            living_companies_list=living_companies_list,
            industry_context=industry_context or "Unknown",
            parameter_summaries=parameter_summaries,
            venture_context_block=vc_parts["venture_context_block"],
        )

        try:
            response = await self.llm_client.complete_simple(
                prompt=prompt,
                system_prompt=POSTMORTEM_BRIEF_SYSTEM,
                temperature=0.5,
                max_tokens=8000,
                model_override=EXECUTIVE_MODEL,
            )
            if response and response.strip():
                parsed = self._parse_json(response)
                if parsed:
                    narratives = [
                        CautionaryNarrative.from_dict(n)
                        for n in parsed.get("cautionary_narratives", [])
                    ]
                    return PostMortemBrief(
                        failure_patterns=parsed.get("failure_patterns", []),
                        structural_vulnerabilities=parsed.get("structural_vulnerabilities", []),
                        cautionary_narratives=narratives,
                        survival_principles=parsed.get("survival_principles", []),
                        metadata={"model": EXECUTIVE_MODEL},
                    )
        except Exception as e:
            logger.warning(f"Post-mortem brief failed: {e}")

        return PostMortemBrief(
            failure_patterns=["Post-mortem brief could not be generated."],
            metadata={"error": "synthesis_failed"},
        )

    def _parse_json(self, response: str) -> Optional[Dict[str, Any]]:
        match = re.search(
            r'<postmortem_json>\s*(.*?)\s*</postmortem_json>',
            response,
            re.DOTALL,
        )
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        return None
