"""
V2 Executive Agent: synthesizes an executive brief from all parameter report
summaries (headlines, executive summaries, rankings). Single LLM call, Claude Opus 4.6.
"""

import json
import logging
import re
from typing import List, Dict, Any, Optional

from agents.llm_client import LLMClient
from agents.v2_schemas import (
    ExecutiveBrief,
    ComparativeReport,
    WhiteSpaceOpportunity,
    NextStepItem,
)
from agents.v2_prompts import (
    EXECUTIVE_BRIEF_SYSTEM,
    EXECUTIVE_BRIEF_PROMPT,
    AVIS_EXECUTIVE_BRIEF_SYSTEM,
    AVIS_EXECUTIVE_BRIEF_PROMPT,
    format_parameter_summaries_for_executive,
    build_venture_context_block,
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
        venture_context: str = "",
        parameter_path: str = "competely",
    ) -> ExecutiveBrief:
        """
        Produce ExecutiveBrief from parameter report summaries.
        Uses headline, executive_summary, rankings, trends, and white_space per report.
        Optionally personalizes white space and next steps with venture_context.
        When parameter_path='avis', uses AVIS-specific prompts that produce
        Moat Grid, Threat Matrix, and Value Curve frameworks.
        """
        parameter_summaries = format_parameter_summaries_for_executive(reports)
        vc_parts = build_venture_context_block(venture_context)

        use_avis = parameter_path == "avis"
        system_prompt = AVIS_EXECUTIVE_BRIEF_SYSTEM if use_avis else EXECUTIVE_BRIEF_SYSTEM
        brief_template = AVIS_EXECUTIVE_BRIEF_PROMPT if use_avis else EXECUTIVE_BRIEF_PROMPT

        prompt = brief_template.format(
            companies_list=companies_list,
            parameter_summaries=parameter_summaries,
            venture_context_block=vc_parts["venture_context_block"],
            venture_ws_instruction=vc_parts["venture_ws_instruction"],
            venture_matrix_instruction=vc_parts["venture_matrix_instruction"],
            venture_ns_instruction=vc_parts["venture_ns_instruction"],
        )
        try:
            response = await self.llm_client.complete_simple(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.5,
                max_tokens=12000,
                model_override=EXECUTIVE_MODEL,
            )
            if response and response.strip():
                parsed = self._parse_executive_json(response)
                if parsed:
                    # Parse white_space_opportunities
                    ws_opps = [
                        WhiteSpaceOpportunity.from_dict(o)
                        for o in parsed.get("white_space_opportunities", [])
                    ]
                    # Parse next_steps buckets
                    raw_ns = parsed.get("next_steps", {})
                    next_steps = {
                        bucket: [NextStepItem.from_dict(item) for item in items]
                        for bucket, items in raw_ns.items()
                        if isinstance(items, list)
                    }
                    return ExecutiveBrief(
                        brief=parsed.get("brief", ""),
                        key_themes=parsed.get("key_themes", []),
                        trends=parsed.get("trends", []),
                        white_space_opportunities=ws_opps,
                        white_space_matrix=parsed.get("white_space_matrix", {}),
                        next_steps=next_steps,
                        venture_context=venture_context,
                        metadata={"model": EXECUTIVE_MODEL, "parameter_path": parameter_path},
                        moat_analysis_grid=parsed.get("moat_analysis_grid", []),
                        threat_matrix=parsed.get("threat_matrix", []),
                        value_curve_assessment=parsed.get("value_curve_assessment", {}),
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
