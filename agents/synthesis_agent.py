"""
V2 Synthesis Agent: produces comparative reports per parameter with optional
iterative re-gather when evidence is insufficient. Uses Claude Opus 4.6.
"""

import json
import logging
import re
from typing import List, Dict, Any, Optional

from agents.llm_client import LLMClient
from agents.gather_agent import GatherAgent
from agents.normalize_agent import NormalizeAgent
from agents.v2_schemas import (
    NormalizedDataset,
    ComparativeReport,
    CompanyRanking,
    IntelligenceDossier,
    EvidenceSource,
)
from agents.v2_prompts import (
    SYNTHESIS_DRAFT_SYSTEM,
    SYNTHESIS_DRAFT_PROMPT,
    SYNTHESIS_EVALUATE_SYSTEM,
    SYNTHESIS_EVALUATE_PROMPT,
)
from config import settings

logger = logging.getLogger(__name__)

SYNTHESIS_MODEL = settings.SYNTHESIS_MODEL
MAX_SYNTHESIS_ITERATIONS = settings.MAX_SYNTHESIS_ITERATIONS
MAX_REGATHERS_PER_PARAMETER = settings.MAX_REGATHERS_PER_PARAMETER


def _format_dossiers_context(raw_dossiers: Dict[str, Dict[str, Any]]) -> str:
    """Format raw_dossiers into a string for synthesis prompt."""
    lines = []
    for company, d in raw_dossiers.items():
        lines.append(f"\n--- {company} ---")
        sources = d.get("sources", [])
        passages = d.get("raw_passages", [])
        for s in sources[:10]:
            sid = s.get("source_id", "?")
            title = s.get("title", "?")
            lines.append(f"  [{sid}] {title}")
        for p in passages[:15]:
            text = p.get("text", "")[:400]
            if len(p.get("text", "")) > 400:
                text += "..."
            sid = p.get("source_id", "?")
            lines.append(f"  ({sid}) {text}")
    return "\n".join(lines) if lines else "No additional context."


class SynthesisAgent:
    """
    Agent that synthesizes a comparative report from a NormalizedDataset,
    with optional iterative re-gather when the draft is insufficient.
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        gather_agent: Optional[GatherAgent] = None,
        normalize_agent: Optional[NormalizeAgent] = None,
        variable_lookup: Optional[Dict[str, Any]] = None,
    ):
        self.llm_client = llm_client or LLMClient()
        self.gather_agent = gather_agent or GatherAgent()
        self.normalize_agent = normalize_agent or NormalizeAgent()
        self.variable_lookup = variable_lookup or {}

    async def synthesize(
        self,
        normalized: NormalizedDataset,
        research_prompt: str,
    ) -> ComparativeReport:
        """
        Produce a comparative report for one parameter. May loop: draft -> evaluate ->
        re-gather -> re-normalize -> draft again, up to MAX_SYNTHESIS_ITERATIONS.
        """
        parameter_id = normalized.parameter_id
        parameter_name = normalized.parameter_name
        companies_list = ", ".join(normalized.company_data.keys()) if normalized.company_data else ""
        regather_count = 0
        draft: Optional[Dict[str, Any]] = None

        for iteration in range(MAX_SYNTHESIS_ITERATIONS):
            draft = await self._draft_report(normalized, research_prompt, companies_list)
            if not draft:
                continue
            evaluation = await self._evaluate_draft(draft, normalized)
            if evaluation.get("is_sufficient", False):
                return self._finalize_report(
                    draft,
                    normalized,
                    synthesis_iterations=iteration + 1,
                    regather_count=regather_count,
                )
            requested = evaluation.get("requested_gathers", [])
            if not requested or regather_count >= MAX_REGATHERS_PER_PARAMETER:
                break
            new_dossiers = await self._targeted_regather(
                parameter_id,
                parameter_name,
                requested,
            )
            if not new_dossiers:
                break
            normalized = await self._re_normalize(normalized, new_dossiers, research_prompt)
            regather_count += 1

        return self._finalize_report(
            draft or {},
            normalized,
            synthesis_iterations=MAX_SYNTHESIS_ITERATIONS,
            regather_count=regather_count,
            capped=True,
        )

    async def _draft_report(
        self,
        normalized: NormalizedDataset,
        research_prompt: str,
        companies_list: str,
    ) -> Optional[Dict[str, Any]]:
        """Call Claude Opus to draft the comparative report."""
        normalized_data = json.dumps(normalized.company_data, indent=2)
        dossiers_context = _format_dossiers_context(normalized.raw_dossiers)
        prompt = SYNTHESIS_DRAFT_PROMPT.format(
            parameter_name=normalized.parameter_name,
            research_prompt=research_prompt,
            companies_list=companies_list,
            normalized_data=normalized_data,
            dossiers_context=dossiers_context,
        )
        try:
            response = await self.llm_client.complete_simple(
                prompt=prompt,
                system_prompt=SYNTHESIS_DRAFT_SYSTEM,
                temperature=0.5,
                max_tokens=16000,
                model_override=SYNTHESIS_MODEL,
            )
            if response and response.strip():
                return self._parse_synthesis_json(response)
        except Exception as e:
            logger.warning(f"Synthesis draft failed: {e}")
        return None

    def _parse_synthesis_json(self, response: str) -> Optional[Dict[str, Any]]:
        match = re.search(r'<synthesis_json>\s*(.*?)\s*</synthesis_json>', response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        return None

    async def _evaluate_draft(
        self,
        draft: Dict[str, Any],
        normalized: NormalizedDataset,
    ) -> Dict[str, Any]:
        """Self-evaluate draft; return is_sufficient and optional requested_gathers."""
        headline = draft.get("headline", "")
        executive_summary = draft.get("executive_summary", "")
        rankings = draft.get("rankings", [])
        rankings_text = ", ".join(
            f"{r.get('rank')}. {r.get('company')} ({r.get('label', '')})" for r in rankings
        )
        full_report = draft.get("full_report_markdown", "")
        full_report_excerpt = full_report[:1500] + "..." if len(full_report) > 1500 else full_report
        normalized_data = json.dumps(normalized.company_data, indent=2)
        gaps_text = "\n".join(
            f"- {g.company}: {g.field_or_topic} - {g.description}"
            for g in normalized.data_gaps
        ) or "None identified."

        prompt = SYNTHESIS_EVALUATE_PROMPT.format(
            parameter_name=normalized.parameter_name,
            headline=headline,
            executive_summary=executive_summary,
            rankings_text=rankings_text,
            full_report_excerpt=full_report_excerpt,
            normalized_data=normalized_data,
            gaps_text=gaps_text,
        )
        try:
            response = await self.llm_client.complete_simple(
                prompt=prompt,
                system_prompt=SYNTHESIS_EVALUATE_SYSTEM,
                temperature=0.3,
                max_tokens=4000,
                model_override=SYNTHESIS_MODEL,
            )
            if response and response.strip():
                return self._parse_evaluate_json(response)
        except Exception as e:
            logger.warning(f"Synthesis evaluate failed: {e}")
        return {"is_sufficient": True, "requested_gathers": []}

    def _parse_evaluate_json(self, response: str) -> Dict[str, Any]:
        result = {"is_sufficient": True, "requested_gathers": []}
        match = re.search(r'<evaluate_json>\s*(.*?)\s*</evaluate_json>', response, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(1))
                result["is_sufficient"] = parsed.get("is_sufficient", True)
                result["requested_gathers"] = parsed.get("requested_gathers", [])
                return result
            except json.JSONDecodeError:
                pass
        return result

    async def _targeted_regather(
        self,
        parameter_id: str,
        parameter_name: str,
        requested_gathers: List[Dict[str, Any]],
    ) -> Dict[str, IntelligenceDossier]:
        """Run gather for each (company, query) in requested_gathers in parallel; return new dossiers by company."""
        import asyncio

        async def _single_gather(company: str, query: str) -> Optional[tuple]:
            try:
                dossier = await self.gather_agent.gather(
                    company,
                    parameter_id,
                    initial_queries=[query],
                )
                return (company, dossier)
            except Exception as e:
                logger.warning(f"Targeted re-gather failed for {company}: {e}")
                return None

        tasks = []
        for req in requested_gathers[:5]:
            company = req.get("company", "").strip()
            query = req.get("query", "").strip()
            if company and query:
                tasks.append(_single_gather(company, query))

        new_dossiers: Dict[str, IntelligenceDossier] = {}
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, tuple) and result is not None:
                    new_dossiers[result[0]] = result[1]
                elif isinstance(result, Exception):
                    logger.warning(f"Re-gather task exception: {result}")
        return new_dossiers

    async def _re_normalize(
        self,
        normalized: NormalizedDataset,
        new_dossiers: Dict[str, IntelligenceDossier],
        research_prompt: str,
    ) -> NormalizedDataset:
        """Merge new dossiers into existing and re-run normalization.

        For companies with both old and new dossiers, facts, key_metrics,
        raw_passages, and sources are combined rather than replaced, so
        the original gather data is preserved alongside the re-gather.
        """
        existing = normalized.raw_dossiers
        merged: Dict[str, IntelligenceDossier] = {}

        for company, d_dict in existing.items():
            old_dossier = IntelligenceDossier.from_dict(d_dict)
            if company in new_dossiers:
                new = new_dossiers[company]
                # Merge facts (deduplicate by claim text)
                seen_claims = {f.claim for f in old_dossier.facts}
                combined_facts = list(old_dossier.facts)
                for f in new.facts:
                    if f.claim not in seen_claims:
                        combined_facts.append(f)
                        seen_claims.add(f.claim)
                # Merge key_metrics (new values override old for same key)
                combined_metrics = {**old_dossier.key_metrics, **new.key_metrics}
                # Merge sources (deduplicate by URL)
                seen_urls = {s.url for s in old_dossier.sources}
                combined_sources = list(old_dossier.sources)
                for s in new.sources:
                    if s.url not in seen_urls:
                        combined_sources.append(s)
                        seen_urls.add(s.url)
                # Merge passages
                combined_passages = list(old_dossier.raw_passages) + list(new.raw_passages)

                merged[company] = IntelligenceDossier(
                    company=company,
                    parameter_id=old_dossier.parameter_id,
                    parameter_name=old_dossier.parameter_name,
                    facts=combined_facts,
                    key_metrics=combined_metrics,
                    raw_passages=combined_passages,
                    sources=combined_sources,
                    confidence=new.confidence if new.confidence != "none" else old_dossier.confidence,
                    metadata={**old_dossier.metadata, "regathered": True},
                )
            else:
                merged[company] = old_dossier

        # Add any companies that were only in new_dossiers (shouldn't happen normally)
        for company, dossier in new_dossiers.items():
            if company not in merged:
                merged[company] = dossier

        return await self.normalize_agent.normalize(
            normalized.parameter_id,
            normalized.parameter_name,
            research_prompt,
            merged,
        )

    def _finalize_report(
        self,
        draft: Dict[str, Any],
        normalized: NormalizedDataset,
        synthesis_iterations: int = 0,
        regather_count: int = 0,
        capped: bool = False,
    ) -> ComparativeReport:
        """Build ComparativeReport from draft and aggregate sources from dossiers."""
        rankings = [
            CompanyRanking(
                rank=r.get("rank", 0),
                company=r.get("company", ""),
                label=r.get("label", ""),
                rationale=r.get("rationale", ""),
            )
            for r in draft.get("rankings", [])
        ]
        sources: List[EvidenceSource] = []
        seen_urls = set()
        for d_dict in normalized.raw_dossiers.values():
            for s in d_dict.get("sources", []):
                url = s.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    sources.append(EvidenceSource(
                        source_id=s.get("source_id", ""),
                        url=url,
                        title=s.get("title", ""),
                        domain=s.get("domain", ""),
                        source_score=s.get("source_score", 0.5),
                        is_official=s.get("is_official", False),
                        tier=s.get("tier", "general"),
                        fetched_at=s.get("fetched_at"),
                        content_type=s.get("content_type"),
                    ))
        return ComparativeReport(
            parameter_id=normalized.parameter_id,
            parameter_name=normalized.parameter_name,
            headline=draft.get("headline", ""),
            executive_summary=draft.get("executive_summary", ""),
            rankings=rankings,
            positioning_table=draft.get("positioning_table", []),
            full_report_markdown=draft.get("full_report_markdown", ""),
            white_space=draft.get("white_space", []),
            trends=draft.get("trends", []),
            confidence=draft.get("confidence", "medium"),
            sources=sources,
            synthesis_iterations=synthesis_iterations,
            regather_count=regather_count,
        )
