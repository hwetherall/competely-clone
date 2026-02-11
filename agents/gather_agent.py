"""
V2 Gather Agent: lightweight research that collects structured facts per (company, parameter).

Reuses SearchClient, PageReader, PassageSelector from V1. Does NOT synthesize prose;
outputs IntelligenceDossier with facts and key_metrics for downstream normalization.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple

from agents.search_client import SearchClient, SearchResult
from agents.llm_client import LLMClient, LLMError
from agents.prompts import (
    RESEARCH_SYSTEM_PROMPT,
    QUERY_GENERATION_PROMPT,
    EVALUATION_PROMPT,
    format_answer_spec,
    format_evidence_summary,
)
from agents.schemas import EvidenceSource, EvidencePassage, EvidencePack
from agents.page_reader import PageReader, get_page_reader
from agents.passage_selector import select_passages_for_variable, merge_passages
from agents.v2_schemas import IntelligenceDossier, FactItem
from agents.v2_prompts import (
    GATHER_FACT_EXTRACTION_SYSTEM,
    GATHER_FACT_EXTRACTION_PROMPT,
)
from config.variables import VariableDefinition, get_variable
from config import settings

logger = logging.getLogger(__name__)

RESEARCH_MODEL = settings.RESEARCH_MODEL
SUMMARIZE_MODEL = settings.SUMMARIZE_MODEL


@dataclass
class GatherState:
    """Internal state during gather process."""
    company: str
    variable: VariableDefinition
    queries_tried: List[str] = field(default_factory=list)
    search_results: List[SearchResult] = field(default_factory=list)
    evidence_sources: List[EvidenceSource] = field(default_factory=list)
    evidence_passages: List[EvidencePassage] = field(default_factory=list)
    pages_fetched: int = 0
    pages_failed: int = 0
    iteration: int = 0
    is_sufficient: bool = False
    confidence: str = "low"
    missing_info: List[str] = field(default_factory=list)


class GatherAgent:
    """
    Agent that gathers raw intelligence for one (company, parameter) pair.
    Outputs structured facts and key_metrics (IntelligenceDossier), not prose.
    """

    def __init__(
        self,
        search_client: Optional[SearchClient] = None,
        llm_client: Optional[LLMClient] = None,
        page_reader: Optional[PageReader] = None,
        max_iterations: Optional[int] = None,
        min_iterations: Optional[int] = None,
        skip_evaluation: bool = False,
        enable_page_fetch: Optional[bool] = None,
        variable_lookup: Optional[Dict[str, VariableDefinition]] = None,
    ):
        self.search_client = search_client or SearchClient()
        self.llm_client = llm_client or LLMClient()
        self.page_reader = page_reader or get_page_reader()
        self.max_iterations = max_iterations or settings.MAX_RESEARCH_ITERATIONS
        self.min_iterations = min_iterations or settings.MIN_RESEARCH_ITERATIONS
        self.skip_evaluation = skip_evaluation
        self.enable_page_fetch = (
            enable_page_fetch if enable_page_fetch is not None else settings.ENABLE_PAGE_FETCH
        )
        self.variable_lookup = variable_lookup or {}

    async def gather(
        self,
        company: str,
        variable_id: str,
        initial_queries: Optional[List[str]] = None,
    ) -> IntelligenceDossier:
        """
        Gather intelligence for one company and one parameter.
        Returns an IntelligenceDossier with facts and key_metrics.

        If initial_queries is provided, use them for the first iteration and
        run at most 1 iteration (for targeted re-gather from synthesis).
        """
        variable = self._get_variable(variable_id)
        state = GatherState(company=company, variable=variable)
        max_iters = 1 if initial_queries is not None else self.max_iterations

        try:
            while state.iteration < max_iters:
                state.iteration += 1
                if initial_queries is not None and state.iteration == 1:
                    queries = initial_queries
                else:
                    queries = await self._generate_queries(state)
                for query in queries:
                    if query not in state.queries_tried:
                        try:
                            result = await self.search_client.search(
                                query, num_results=10, company=company
                            )
                            state.queries_tried.append(query)
                            state.search_results.append(result)
                        except Exception as e:
                            logger.warning(f"Search failed for '{query[:40]}...': {e}")

                if self.enable_page_fetch and state.search_results:
                    await self._fetch_and_build_evidence(state)

                if state.iteration >= self.min_iterations and not self.skip_evaluation:
                    evaluation = await self._evaluate_results(state)
                    state.is_sufficient = evaluation.get("sufficient", False)
                    state.confidence = evaluation.get("confidence", "low")
                    state.missing_info = evaluation.get("missing", [])
                    if state.is_sufficient:
                        break
                elif self.skip_evaluation:
                    state.confidence = "medium"
                    state.is_sufficient = True
                    break

            facts, key_metrics = await self._extract_facts(state)
            metadata = {
                "iterations": state.iteration,
                "searches": len(state.search_results),
                "pages_fetched": state.pages_fetched,
                "pages_failed": state.pages_failed,
                "evidence_sources_used": len(state.evidence_sources),
                "evidence_passages_count": len(state.evidence_passages),
            }
            return IntelligenceDossier(
                company=company,
                parameter_id=variable_id,
                parameter_name=variable.name,
                facts=facts,
                key_metrics=key_metrics,
                raw_passages=state.evidence_passages,
                sources=state.evidence_sources,
                confidence=state.confidence,
                metadata=metadata,
            )
        except Exception as e:
            logger.error(f"Gather failed for {company} - {variable.name}: {e}")
            return IntelligenceDossier(
                company=company,
                parameter_id=variable_id,
                parameter_name=variable.name,
                facts=[],
                key_metrics={},
                raw_passages=[],
                sources=[],
                confidence="none",
                metadata={"error": str(e)},
            )

    def _get_variable(self, variable_id: str) -> VariableDefinition:
        if variable_id in self.variable_lookup:
            return self.variable_lookup[variable_id]
        return get_variable(variable_id)

    async def _generate_queries(self, state: GatherState) -> List[str]:
        company = state.company
        variable = state.variable
        if state.iteration == 1:
            return [q.format(company=company) for q in variable.example_queries]
        try:
            prompt = QUERY_GENERATION_PROMPT.format(
                company=company,
                variable_name=variable.name,
                research_prompt=variable.research_prompt.format(company=company),
                answer_spec=format_answer_spec(variable.answer_spec),
                previous_queries="\n".join(f"- {q}" for q in state.queries_tried) or "None yet",
                missing_info="\n".join(f"- {m}" for m in state.missing_info) if state.missing_info else "None identified",
            )
            response = await self.llm_client.complete_simple(
                prompt=prompt,
                system_prompt=RESEARCH_SYSTEM_PROMPT,
                temperature=0.7,
                max_tokens=1000,
                model_override=SUMMARIZE_MODEL,
            )
            if not response:
                return self._fallback_queries(company, variable.name)
            queries = self._extract_search_queries(response, company)
            return queries[:5] if queries else self._fallback_queries(company, variable.name)
        except Exception:
            return self._fallback_queries(company, variable.name)

    def _fallback_queries(self, company: str, variable_name: str) -> List[str]:
        return [
            f"{company} {variable_name} 2024",
            f"{company} {variable_name} analysis",
        ]

    def _extract_search_queries(self, response: str, company: str) -> List[str]:
        queries = []
        match = re.search(r'<queries>\s*(.*?)\s*</queries>', response, re.DOTALL | re.IGNORECASE)
        if match:
            for line in match.group(1).strip().split("\n"):
                line = line.strip().strip('"\'')
                line = re.sub(r"^[\d\.\-\*\)\•]+\s*", "", line)
                if line and 10 < len(line) < 100:
                    queries.append(line)
            if queries:
                return queries
        for line in response.strip().split("\n"):
            line = line.strip()
            if not line or len(line) < 10 or len(line) > 100:
                continue
            line = re.sub(r"^[\d\.\-\*\)\•]+\s*", "", line).strip('"\'')
            if len(line) >= 10 and company.lower() in line.lower():
                queries.insert(0, line)
            elif len(line) >= 10:
                queries.append(line)
        return queries

    async def _fetch_and_build_evidence(self, state: GatherState) -> None:
        urls_to_fetch = []
        seen_urls = set()
        for result in state.search_results:
            ranked = sorted(
                result.items,
                key=lambda x: (-x.source_score, x.position),
            )
            for item in ranked[:settings.TOP_K_RESULTS_TO_FETCH]:
                if item.url not in seen_urls and item.source_score >= settings.MIN_SOURCE_SCORE:
                    urls_to_fetch.append(item)
                    seen_urls.add(item.url)
        urls_to_fetch = urls_to_fetch[:settings.MAX_PAGES_PER_CELL]
        if not urls_to_fetch:
            return

        page_contents = await self.page_reader.fetch_batch(
            [item.url for item in urls_to_fetch],
            max_concurrent=settings.MAX_CONCURRENT_PAGE_FETCHES,
        )
        source_counter = len(state.evidence_sources) + 1
        for item, page_content in zip(urls_to_fetch, page_contents):
            if page_content.is_success:
                state.pages_fetched += 1
                source_id = f"S{source_counter}"
                source = EvidenceSource(
                    source_id=source_id,
                    url=item.url,
                    title=page_content.title or item.title,
                    domain=item.domain,
                    source_score=item.source_score,
                    is_official=item.is_official,
                    tier=item.source_tier,
                    fetched_at=page_content.fetched_at,
                    content_type=page_content.content_type,
                )
                state.evidence_sources.append(source)
                passages = select_passages_for_variable(
                    text=page_content.text,
                    company=state.company,
                    key_terms=state.variable.key_terms,
                    answer_spec=state.variable.answer_spec,
                    max_passages=settings.EVIDENCE_PASSAGES_PER_SOURCE,
                )
                for passage in passages:
                    passage.source_id = source_id
                    state.evidence_passages.append(passage)
                source_counter += 1
            else:
                state.pages_failed += 1
        state.evidence_passages = merge_passages(
            state.evidence_passages,
            max_total_chars=settings.MAX_EVIDENCE_CHARS,
        )

    async def _evaluate_results(self, state: GatherState) -> Dict[str, Any]:
        if not state.search_results:
            return {"sufficient": False, "confidence": "low", "missing": ["No search results yet"]}
        if state.evidence_sources and state.evidence_passages:
            evidence_summary = format_evidence_summary(
                state.evidence_sources,
                state.evidence_passages,
            )
        else:
            from agents.prompts import format_search_results_for_evaluation
            evidence_summary = format_search_results_for_evaluation(state.search_results[-3:])
        prompt = EVALUATION_PROMPT.format(
            company=state.company,
            variable_name=state.variable.name,
            research_prompt=state.variable.research_prompt.format(company=state.company),
            answer_spec=format_answer_spec(state.variable.answer_spec),
            evidence_summary=evidence_summary,
        )
        try:
            response = await self.llm_client.complete_simple(
                prompt=prompt,
                system_prompt=RESEARCH_SYSTEM_PROMPT,
                temperature=0.3,
                max_tokens=4000,
                model_override=SUMMARIZE_MODEL,
            )
            if response and response.strip():
                return self._parse_evaluation_json(response)
        except Exception as e:
            logger.warning(f"Evaluation failed: {e}")
        return {"sufficient": False, "confidence": "low", "missing": ["Evaluation failed"]}

    def _parse_evaluation_json(self, response: str) -> Dict[str, Any]:
        result = {"sufficient": False, "confidence": "low", "missing": []}
        match = re.search(r'<evaluation_json>\s*(.*?)\s*</evaluation_json>', response, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(1))
                result["sufficient"] = parsed.get("sufficient", False)
                result["confidence"] = parsed.get("confidence", "low")
                result["missing"] = parsed.get("missing", [])
                return result
            except json.JSONDecodeError:
                pass
        return result

    async def _extract_facts(self, state: GatherState) -> Tuple[List[FactItem], Dict[str, str]]:
        """Call LLM to extract structured facts and key_metrics from evidence."""
        facts: List[FactItem] = []
        key_metrics: Dict[str, str] = {}
        if not state.evidence_passages and not state.evidence_sources:
            return facts, key_metrics
        evidence_pack = EvidencePack(
            sources=state.evidence_sources,
            passages=state.evidence_passages,
            total_chars=sum(len(p.text) for p in state.evidence_passages),
            avg_source_score=(
                sum(s.source_score for s in state.evidence_sources) / len(state.evidence_sources)
                if state.evidence_sources else 0
            ),
        )
        evidence_text = evidence_pack.format_for_prompt()
        prompt = GATHER_FACT_EXTRACTION_PROMPT.format(
            company=state.company,
            parameter_name=state.variable.name,
            research_prompt=state.variable.research_prompt.format(company=state.company),
            evidence_text=evidence_text,
        )
        try:
            response = await self.llm_client.complete_simple(
                prompt=prompt,
                system_prompt=GATHER_FACT_EXTRACTION_SYSTEM,
                temperature=0.3,
                max_tokens=4000,
                model_override=SUMMARIZE_MODEL,
            )
            if response and response.strip():
                parsed = self._parse_fact_extraction_json(response)
                if parsed:
                    facts = [FactItem.from_dict(f) for f in parsed.get("facts", [])]
                    key_metrics = parsed.get("key_metrics") or {}
        except Exception as e:
            logger.warning(f"Fact extraction failed: {e}")
        return facts, key_metrics

    def _parse_fact_extraction_json(self, response: str) -> Optional[Dict[str, Any]]:
        match = re.search(r'<fact_extraction_json>\s*(.*?)\s*</fact_extraction_json>', response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        return None
