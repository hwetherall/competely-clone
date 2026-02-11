"""
V2 Executive Agent: synthesizes an executive brief from all parameter report
summaries (headlines, executive summaries, rankings). Single LLM call, Claude Opus 4.6.
"""

import json
import logging
import re
from typing import List, Dict, Any, Optional

from agents.llm_client import LLMClient
from agents.v2_schemas import ExecutiveBrief, ComparativeReport
from agents.v2_prompts import (
    EXECUTIVE_BRIEF_SYSTEM,
    EXECUTIVE_BRIEF_PROMPT,
    format_parameter_summaries_for_executive,
)
from config import settings

logger = logging.getLogger(__name__)

EXECUTIVE_MODEL = settings.EXECUTIVE_MODEL


class ExecutiveAgent:
    """
    Agent that produces the landscape-level executive brief from
    all parameter comparative reports.
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or LLMClient()

    async def synthesize_brief(
        self,
        companies_list: str,
        reports: List[ComparativeReport],
    ) -> ExecutiveBrief:
        """
        Produce ExecutiveBrief from parameter report summaries.
        Uses only headline, executive_summary, and rankings per report to stay within context.
        """
        parameter_summaries = format_parameter_summaries_for_executive(reports)
        prompt = EXECUTIVE_BRIEF_PROMPT.format(
            companies_list=companies_list,
            parameter_summaries=parameter_summaries,
        )
        try:
            response = await self.llm_client.complete_simple(
                prompt=prompt,
                system_prompt=EXECUTIVE_BRIEF_SYSTEM,
                temperature=0.5,
                max_tokens=4000,
                model_override=EXECUTIVE_MODEL,
            )
            if response and response.strip():
                parsed = self._parse_executive_json(response)
                if parsed:
                    return ExecutiveBrief(
                        brief=parsed.get("brief", ""),
                        key_themes=parsed.get("key_themes", []),
                        metadata={"model": EXECUTIVE_MODEL},
                    )
        except Exception as e:
            logger.warning(f"Executive brief failed: {e}")

        return ExecutiveBrief(
            brief="Executive brief could not be generated.",
            key_themes=[],
            metadata={"error": "synthesis_failed"},
        )

    def _parse_executive_json(self, response: str) -> Optional[Dict[str, Any]]:
        match = re.search(r'<executive_json>\s*(.*?)\s*</executive_json>', response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        return None
