"""
Risk Overlay Agent: cross-references main ExecutiveBrief white-space opportunities
with PostMortemBrief failure patterns to produce risk overlays.
Single LLM call using Claude Opus 4.6.
"""

import json
import logging
import re
from typing import List, Dict, Any, Optional

from agents.llm_client import LLMClient
from agents.v2_schemas import (
    PostMortemBrief,
    ExecutiveBrief,
    RiskOverlay,
)
from agents.v2_prompts import (
    RISK_OVERLAY_SYSTEM,
    RISK_OVERLAY_PROMPT,
)
from config import settings

logger = logging.getLogger(__name__)

EXECUTIVE_MODEL = settings.EXECUTIVE_MODEL


class RiskOverlayAgent:
    """Merges main ExecutiveBrief + PostMortemBrief into risk overlays."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or LLMClient()

    async def generate_overlays(
        self,
        executive_brief: ExecutiveBrief,
        postmortem_brief: PostMortemBrief,
    ) -> List[RiskOverlay]:
        """
        Produce risk overlays by cross-referencing white-space opportunities
        with failure patterns.
        """
        ws_opps = executive_brief.white_space_opportunities
        if not ws_opps:
            return []

        ws_text = "\n".join(
            f"- {o.opportunity} (entry difficulty: {o.entry_difficulty})"
            for o in ws_opps
        )

        fp_text = "\n".join(
            f"- {p}" for p in postmortem_brief.failure_patterns
        ) or "No failure patterns identified."

        sv_text = "\n".join(
            f"- {v}" for v in postmortem_brief.structural_vulnerabilities
        ) or "No structural vulnerabilities identified."

        cn_text = "\n".join(
            f"- {n.company}: {n.failure_mode} — {n.key_lesson}"
            for n in postmortem_brief.cautionary_narratives
        ) or "No cautionary narratives available."

        prompt = RISK_OVERLAY_PROMPT.format(
            white_space_opportunities=ws_text,
            failure_patterns=fp_text,
            structural_vulnerabilities=sv_text,
            cautionary_summaries=cn_text,
        )

        try:
            response = await self.llm_client.complete_simple(
                prompt=prompt,
                system_prompt=RISK_OVERLAY_SYSTEM,
                temperature=0.4,
                max_tokens=6000,
                model_override=EXECUTIVE_MODEL,
            )
            if response and response.strip():
                parsed = self._parse_json(response)
                if parsed:
                    return [
                        RiskOverlay.from_dict(r)
                        for r in parsed.get("risk_overlays", [])
                    ]
        except Exception as e:
            logger.warning(f"Risk overlay generation failed: {e}")

        return []

    def _parse_json(self, response: str) -> Optional[Dict[str, Any]]:
        match = re.search(
            r'<risk_overlay_json>\s*(.*?)\s*</risk_overlay_json>',
            response,
            re.DOTALL,
        )
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        return None
