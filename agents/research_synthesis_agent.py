import json
import logging
import re
from typing import List, Dict, Any, Optional

from agents.llm_client import LLMClient
from agents.v2_schemas import (
    ResearchSynthesis,
    KeyQuestionAnswer,
    ComparativeReport,
)
from agents.v2_prompts import (
    RESEARCH_SYNTHESIS_SYSTEM,
    RESEARCH_SYNTHESIS_PROMPT,
    format_parameter_summaries_for_executive,
)
from config import settings

logger = logging.getLogger(__name__)

EXECUTIVE_MODEL = settings.EXECUTIVE_MODEL

class ResearchSynthesisAgent:
    """
    Agent that synthesizes research findings to answer key questions and validate hypothesis.
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or LLMClient()

    async def synthesize(
        self,
        companies_list: str,
        reports: List[ComparativeReport],
        key_questions: List[str],
        hypothesis: str,
    ) -> ResearchSynthesis:
        """
        Produce ResearchSynthesis from parameter report summaries.
        """
        if not key_questions and not hypothesis:
             return ResearchSynthesis(key_questions_answers=[], hypothesis_validation="")

        parameter_summaries = format_parameter_summaries_for_executive(reports)
        
        key_questions_list = "\n".join([f"{i+1}. {q}" for i, q in enumerate(key_questions)])

        prompt = RESEARCH_SYNTHESIS_PROMPT.format(
            companies_list=companies_list,
            hypothesis=hypothesis or "None provided.",
            key_questions_list=key_questions_list or "None provided.",
            parameter_summaries=parameter_summaries,
        )
        
        try:
            response = await self.llm_client.complete_simple(
                prompt=prompt,
                system_prompt=RESEARCH_SYNTHESIS_SYSTEM,
                temperature=0.5,
                max_tokens=4000,
                model_override=EXECUTIVE_MODEL,
            )
            
            if response and response.strip():
                parsed = self._parse_json(response)
                if parsed:
                    answers = [
                        KeyQuestionAnswer.from_dict(a)
                        for a in parsed.get("key_questions_answers", [])
                    ]
                    return ResearchSynthesis(
                        key_questions_answers=answers,
                        hypothesis_validation=parsed.get("hypothesis_validation", ""),
                    )
        except Exception as e:
            logger.warning(f"Research synthesis failed: {e}")

        return ResearchSynthesis(
            key_questions_answers=[],
            hypothesis_validation="Research synthesis could not be generated.",
        )

    def _parse_json(self, response: str) -> Optional[Dict[str, Any]]:
        match = re.search(r'<research_synthesis_json>\s*(.*?)\s*</research_synthesis_json>', response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        return None
