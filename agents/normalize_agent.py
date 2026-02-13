"""
V2 Normalize Agent: takes N company dossiers for one parameter and produces
a NormalizedDataset with a common comparison schema and identified data gaps.
"""

import json
import logging
import re
from typing import List, Dict, Any, Optional

from agents.llm_client import LLMClient
from agents.v2_schemas import (
    NormalizedDataset,
    IntelligenceDossier,
    DataGap,
)
from agents.v2_prompts import (
    NORMALIZE_SYSTEM,
    NORMALIZE_PROMPT,
    format_dossiers_for_normalize,
)
from config import settings

logger = logging.getLogger(__name__)

SUMMARIZE_MODEL = settings.SUMMARIZE_MODEL


class NormalizeAgent:
    """
    Agent that normalizes per-company dossiers for one parameter into
    a common schema for comparative synthesis.
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or LLMClient()

    async def normalize(
        self,
        parameter_id: str,
        parameter_name: str,
        research_prompt: str,
        dossiers_by_company: Dict[str, IntelligenceDossier],
    ) -> NormalizedDataset:
        """
        Produce a NormalizedDataset for one parameter from N company dossiers.

        Args:
            parameter_id: Variable/parameter ID
            parameter_name: Human-readable name
            research_prompt: Parameter research context (with {company} already substituted or generic)
            dossiers_by_company: company -> IntelligenceDossier

        Returns:
            NormalizedDataset with schema_fields, company_data, data_gaps
        """
        if not dossiers_by_company:
            return NormalizedDataset(
                parameter_id=parameter_id,
                parameter_name=parameter_name,
                schema_fields=[],
                company_data={},
                data_gaps=[],
                raw_dossiers={},
            )

        dossiers_text = format_dossiers_for_normalize(dossiers_by_company)
        prompt = NORMALIZE_PROMPT.format(
            parameter_name=parameter_name,
            research_prompt=research_prompt,
            dossiers_text=dossiers_text,
        )
        try:
            response = await self.llm_client.complete_simple(
                prompt=prompt,
                system_prompt=NORMALIZE_SYSTEM,
                temperature=0.3,
                max_tokens=8000,
                model_override=SUMMARIZE_MODEL,
            )
            if response and response.strip():
                parsed = self._parse_normalize_json(response)
                if parsed:
                    schema_fields = parsed.get("schema_fields", [])
                    company_data = parsed.get("company_data", {})
                    gaps_data = parsed.get("data_gaps", [])
                    data_gaps = [
                        DataGap(
                            company=g.get("company", ""),
                            field_or_topic=g.get("field_or_topic", ""),
                            description=g.get("description", ""),
                        )
                        for g in gaps_data
                    ]
                    raw_dossiers = {
                        c: d.to_dict() if hasattr(d, "to_dict") else d
                        for c, d in dossiers_by_company.items()
                    }
                    return NormalizedDataset(
                        parameter_id=parameter_id,
                        parameter_name=parameter_name,
                        schema_fields=schema_fields,
                        company_data=company_data,
                        data_gaps=data_gaps,
                        raw_dossiers=raw_dossiers,
                    )
        except Exception as e:
            logger.warning(f"Normalize failed for {parameter_id}: {e}")

        raw_dossiers = {
            c: d.to_dict() if hasattr(d, "to_dict") else d
            for c, d in dossiers_by_company.items()
        }
        return NormalizedDataset(
            parameter_id=parameter_id,
            parameter_name=parameter_name,
            schema_fields=[],
            company_data={c: {} for c in dossiers_by_company},
            data_gaps=[],
            raw_dossiers=raw_dossiers,
        )

    def _parse_normalize_json(self, response: str) -> Optional[Dict[str, Any]]:
        match = re.search(r'<normalize_json>\s*(.*?)\s*</normalize_json>', response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError as e:
                logger.debug(f"Failed to parse normalize JSON: {e}")
        return None
