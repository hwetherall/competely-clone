"""
Research Agent for competitive analysis with evidence-grounded synthesis.

This agent performs iterative research on a (Company, Variable) pair:
1. Generate search queries based on the variable definition
2. Search and gather results using the SearchClient
3. Fetch and extract content from top pages
4. Build evidence packs with passages
5. Evaluate if gathered evidence is sufficient
6. Synthesize comprehensive answer with citations
7. Verify numeric claims against evidence
8. Create concise summary for table display
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

from agents.search_client import SearchClient, SearchResult, SearchResultItem
from agents.llm_client import LLMClient, LLMError
from agents.prompts import (
    RESEARCH_SYSTEM_PROMPT,
    QUERY_GENERATION_PROMPT,
    EVALUATION_PROMPT,
    SYNTHESIS_PROMPT,
    SUMMARIZE_PROMPT,
    TIGHTEN_PROMPT,
    NUMERIC_FIX_PROMPT,
    format_search_results_for_evaluation,
    format_gathered_info_for_synthesis,
    format_evidence_pack,
    format_answer_spec,
    format_evidence_summary,
)
from agents.schemas import (
    EvidenceSource,
    EvidencePassage,
    EvidencePack,
    Claim,
    SynthesisResult,
    ResearchMetadata,
    PageContent,
)
from agents.page_reader import PageReader, get_page_reader, create_page_reader
from agents.passage_selector import select_passages_for_variable, merge_passages
from agents.source_scoring import score_url, rank_urls, extract_domain
from agents.verification import (
    extract_numbers,
    verify_numbers_against_evidence,
    should_reduce_confidence,
    format_unsupported_for_fix,
)
from config.variables import VariableDefinition, get_variable
from config import settings

logger = logging.getLogger(__name__)

# Model configuration
RESEARCH_MODEL = settings.RESEARCH_MODEL
SUMMARIZE_MODEL = settings.SUMMARIZE_MODEL
SUMMARIZE_FALLBACK_MODEL = settings.SUMMARIZE_FALLBACK_MODEL


def create_search_client() -> SearchClient:
    """Create the configured search client for research workflows."""
    provider = settings.SEARCH_PROVIDER.lower()
    if provider == "exa":
        from agents.exa_client import ExaClient

        return ExaClient()
    if provider == "hybrid":
        logger.warning("SEARCH_PROVIDER=hybrid is not implemented for research yet; using Serper.")
    return SearchClient()


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ResearchSource:
    """A source used in research."""
    title: str
    url: str
    snippet: str
    query: str
    domain: str = ""
    source_score: float = 0.5
    is_official: bool = False


@dataclass
class ResearchResult:
    """Complete result of a research task with evidence-grounded synthesis."""
    company: str
    variable_id: str
    variable_name: str
    concise: str
    comprehensive: str
    sources: List[ResearchSource]
    confidence: str
    iterations: int
    total_searches: int
    timestamp: str
    error: Optional[str] = None
    # New fields for evidence-grounded research
    claims: List[Dict[str, Any]] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "company": self.company,
            "variable_id": self.variable_id,
            "variable_name": self.variable_name,
            "concise": self.concise,
            "comprehensive": self.comprehensive,
            "sources": [
                {
                    "title": s.title,
                    "url": s.url,
                    "snippet": s.snippet,
                    "query": s.query,
                    "domain": s.domain,
                    "source_score": s.source_score,
                    "is_official": s.is_official,
                }
                for s in self.sources
            ],
            "confidence": self.confidence,
            "iterations": self.iterations,
            "total_searches": self.total_searches,
            "timestamp": self.timestamp,
            "error": self.error,
            "claims": self.claims,
            "gaps": self.gaps,
            "metadata": self.metadata,
        }


@dataclass
class ResearchState:
    """Internal state during research process."""
    company: str
    variable: VariableDefinition
    queries_tried: List[str] = field(default_factory=list)
    search_results: List[SearchResult] = field(default_factory=list)
    gathered_info: List[Dict[str, Any]] = field(default_factory=list)
    iteration: int = 0
    is_sufficient: bool = False
    confidence: str = "low"
    missing_info: List[str] = field(default_factory=list)
    # New fields for evidence-grounded research
    evidence_sources: List[EvidenceSource] = field(default_factory=list)
    evidence_passages: List[EvidencePassage] = field(default_factory=list)
    pages_fetched: int = 0
    pages_failed: int = 0
    synthesis_result: Optional[SynthesisResult] = None


# =============================================================================
# Research Agent
# =============================================================================

class ResearchAgent:
    """
    Agent that performs iterative research with evidence-grounded synthesis.
    
    The research flow:
    1. Start with example queries from the variable definition
    2. Search and gather results with source scoring
    3. Fetch top pages and extract passages
    4. Build evidence pack for synthesis
    5. Evaluate if we have enough evidence
    6. Synthesize all gathered information with citations
    7. Verify numeric claims against evidence
    8. Summarize into a concise version (max chars enforced)
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
        enable_verification: Optional[bool] = None,
        variable_lookup: Optional[Dict[str, VariableDefinition]] = None,
    ):
        """
        Initialize the research agent.

        Args:
            search_client: SearchClient instance (creates new if not provided)
            llm_client: LLMClient instance (creates new if not provided)
            page_reader: PageReader instance (uses singleton if not provided)
            max_iterations: Maximum research iterations
            min_iterations: Minimum iterations before checking sufficiency
            skip_evaluation: If True, skip LLM evaluation step
            enable_page_fetch: Override for page fetching (default from settings)
            enable_verification: Override for numeric verification (default from settings)
            variable_lookup: Optional dict of variable_id -> VariableDefinition for dynamic variables
        """
        self.search_client = search_client or create_search_client()
        self.llm_client = llm_client or LLMClient()
        self.page_reader = page_reader or get_page_reader()
        self.max_iterations = max_iterations or settings.MAX_RESEARCH_ITERATIONS
        self.min_iterations = min_iterations or settings.MIN_RESEARCH_ITERATIONS
        self.skip_evaluation = skip_evaluation
        self.enable_page_fetch = enable_page_fetch if enable_page_fetch is not None else settings.ENABLE_PAGE_FETCH
        self.enable_verification = enable_verification if enable_verification is not None else settings.ENABLE_NUMERIC_VERIFICATION
        self.variable_lookup = variable_lookup
    
    async def research(
        self,
        company: str,
        variable_id: str,
    ) -> ResearchResult:
        """
        Perform research on a company for a specific variable.
        
        Args:
            company: Company name (e.g., "Stripe", "PayPal")
            variable_id: Variable ID (e.g., "unique_value_proposition")
            
        Returns:
            ResearchResult with comprehensive and concise answers
        """
        if self.variable_lookup and variable_id in self.variable_lookup:
            variable = self.variable_lookup[variable_id]
        else:
            variable = get_variable(variable_id)
        state = ResearchState(company=company, variable=variable)
        
        logger.info(f"Starting research: {company} - {variable.name}")
        
        try:
            # Main research loop
            while state.iteration < self.max_iterations:
                state.iteration += 1
                logger.info(f"Research iteration {state.iteration}/{self.max_iterations}")
                
                # Step 1: Generate search queries
                queries = await self._generate_queries(state)
                logger.debug(f"Generated {len(queries)} queries")
                
                # Step 2: Execute searches with company context for source scoring
                for query in queries:
                    if query not in state.queries_tried:
                        try:
                            result = await self.search_client.search(
                                query,
                                num_results=10,
                                company=company,
                            )
                            state.queries_tried.append(query)
                            state.search_results.append(result)
                            state.gathered_info.extend(self._extract_info(result))
                            logger.debug(f"Search '{query[:40]}...' returned {result.total_results} results")
                        except Exception as e:
                            logger.warning(f"Search failed for '{query[:40]}...': {e}")
                            continue
                
                # Step 3: Fetch pages and build evidence (if enabled)
                if self.enable_page_fetch and state.search_results:
                    await self._fetch_and_build_evidence(state)
                
                # Step 4: Evaluate if we have enough information
                if state.iteration >= self.min_iterations and not self.skip_evaluation:
                    evaluation = await self._evaluate_results(state)
                    state.is_sufficient = evaluation.get("sufficient", False)
                    state.confidence = evaluation.get("confidence", "low")
                    state.missing_info = evaluation.get("missing", [])
                    
                    if state.is_sufficient:
                        logger.info(f"Sufficient information gathered after {state.iteration} iterations")
                        break
                    else:
                        logger.info(f"Need more information. Missing: {state.missing_info}")
                elif self.skip_evaluation:
                    state.confidence = "medium"
                    state.is_sufficient = True
                    logger.info(f"Fast mode: skipping evaluation after {state.iteration} iterations")
                    break
            
            # Step 5: Synthesize comprehensive answer with citations
            synthesis_result = await self._synthesize(state)
            state.synthesis_result = synthesis_result
            comprehensive = synthesis_result.comprehensive_markdown or self._fallback_synthesis(state)
            
            # Step 6: Verify numeric claims (if enabled)
            if self.enable_verification and state.evidence_passages:
                comprehensive, verification_reduced = await self._verify_and_fix(
                    comprehensive, state
                )
                if verification_reduced:
                    state.confidence = "low"
            
            # Step 7: Create concise summary with length enforcement
            max_chars = variable.max_concise_chars or settings.DEFAULT_MAX_CONCISE_CHARS
            concise = await self._summarize(
                state.company,
                variable.name,
                comprehensive,
                max_chars,
            )
            
            # Build metadata
            metadata = self._build_metadata(state)
            
            # Build final result
            return ResearchResult(
                company=company,
                variable_id=variable_id,
                variable_name=variable.name,
                concise=concise,
                comprehensive=comprehensive,
                sources=self._build_sources(state),
                confidence=state.confidence,
                iterations=state.iteration,
                total_searches=len(state.search_results),
                timestamp=datetime.utcnow().isoformat(),
                claims=[c.to_dict() for c in synthesis_result.claims] if synthesis_result.claims else [],
                gaps=synthesis_result.gaps or [],
                metadata=metadata,
            )
            
        except Exception as e:
            logger.error(f"Research failed for {company} - {variable.name}: {e}")
            return ResearchResult(
                company=company,
                variable_id=variable_id,
                variable_name=variable.name,
                concise=f"Error: Unable to complete research",
                comprehensive=f"Research failed due to an error: {str(e)}",
                sources=[],
                confidence="none",
                iterations=state.iteration,
                total_searches=len(state.search_results),
                timestamp=datetime.utcnow().isoformat(),
                error=str(e),
            )
    
    def research_sync(self, company: str, variable_id: str) -> ResearchResult:
        """Synchronous wrapper for research()."""
        return asyncio.run(self.research(company, variable_id))
    
    async def _fetch_and_build_evidence(self, state: ResearchState) -> None:
        """
        Fetch top pages and build evidence pack.
        
        Uses Jina Reader (when available) to extract clean content from web pages,
        which provides better quality text than raw HTML parsing.
        
        Args:
            state: Current research state
        """
        # Collect URLs to fetch from recent search results
        urls_to_fetch = []
        seen_urls = set()
        
        for result in state.search_results:
            # Rank items by score with diversity
            ranked_items = sorted(
                result.items,
                key=lambda x: (-x.source_score, x.position)
            )
            
            for item in ranked_items[:settings.TOP_K_RESULTS_TO_FETCH]:
                if item.url not in seen_urls and item.source_score >= settings.MIN_SOURCE_SCORE:
                    urls_to_fetch.append(item)
                    seen_urls.add(item.url)
        
        # Limit total pages
        urls_to_fetch = urls_to_fetch[:settings.MAX_PAGES_PER_CELL]
        
        if not urls_to_fetch:
            return
        
        # Log fetch mode
        fetch_mode = self.page_reader.fetch_mode if hasattr(self.page_reader, 'fetch_mode') else 'unknown'
        logger.info(f"Fetching {len(urls_to_fetch)} pages (mode: {fetch_mode})")
        print(f"  ? Fetching {len(urls_to_fetch)} web pages for evidence...", end="\r")
        
        # Fetch pages concurrently
        page_contents = await self.page_reader.fetch_batch(
            [item.url for item in urls_to_fetch],
            max_concurrent=settings.MAX_CONCURRENT_PAGE_FETCHES,
        )
        
        # Log fetch results
        success_count = sum(1 for p in page_contents if p.is_success)
        total_chars = sum(len(p.text) for p in page_contents if p.is_success)
        print(f"  + Fetched {success_count}/{len(urls_to_fetch)} pages ({total_chars:,} chars total)   ")
        
        # Build evidence sources and passages
        source_counter = len(state.evidence_sources) + 1
        
        for item, page_content in zip(urls_to_fetch, page_contents):
            if page_content.is_success:
                state.pages_fetched += 1
                
                # Create evidence source
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
                
                # Extract passages for this variable
                passages = select_passages_for_variable(
                    text=page_content.text,
                    company=state.company,
                    key_terms=state.variable.key_terms,
                    answer_spec=state.variable.answer_spec,
                    max_passages=settings.EVIDENCE_PASSAGES_PER_SOURCE,
                )
                
                # Assign source_id to passages
                for passage in passages:
                    passage.source_id = source_id
                    state.evidence_passages.append(passage)
                
                source_counter += 1
            else:
                state.pages_failed += 1
                logger.debug(f"Failed to fetch {item.url}: {page_content.error}")
        
        # Merge passages to fit within limit
        state.evidence_passages = merge_passages(
            state.evidence_passages,
            max_total_chars=settings.MAX_EVIDENCE_CHARS,
        )
    
    async def _generate_queries(self, state: ResearchState) -> List[str]:
        """Generate search queries for the current iteration."""
        company = state.company
        variable = state.variable
        
        if state.iteration == 1:
            # First iteration: use example queries with company substituted
            queries = [
                q.format(company=company) for q in variable.example_queries
            ]
            return queries
        
        # Subsequent iterations: use LLM to generate refined queries
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
                fallback_model=SUMMARIZE_FALLBACK_MODEL,
            )
            
            if not response:
                logger.warning("LLM returned empty response for query generation. Using fallback.")
                return self._fallback_queries(company, variable.name)
            
            queries = self._extract_search_queries(response, company)
            
            if not queries:
                logger.warning("No queries extracted from LLM response. Using fallback.")
                return self._fallback_queries(company, variable.name)
            
            return queries[:5]
            
        except LLMError as e:
            logger.warning(f"LLM query generation failed: {e}. Using fallback queries.")
            return self._fallback_queries(company, variable.name)
        except Exception as e:
            logger.error(f"Unexpected error in query generation: {e}. Using fallback queries.")
            return self._fallback_queries(company, variable.name)
    
    def _fallback_queries(self, company: str, variable_name: str) -> List[str]:
        """Generate fallback queries when LLM fails."""
        return [
            f"{company} {variable_name} 2024",
            f"{company} {variable_name} analysis",
        ]
    
    async def _evaluate_results(self, state: ResearchState) -> Dict[str, Any]:
        """Evaluate if gathered evidence is sufficient."""
        if not state.search_results:
            return {"sufficient": False, "confidence": "low", "missing": ["No search results yet"]}
        
        # Use evidence summary if we have evidence, else use search results
        if state.evidence_sources and state.evidence_passages:
            evidence_summary = format_evidence_summary(
                state.evidence_sources,
                state.evidence_passages,
            )
        else:
            evidence_summary = format_search_results_for_evaluation(state.search_results[-3:])
        
        prompt = EVALUATION_PROMPT.format(
            company=state.company,
            variable_name=state.variable.name,
            research_prompt=state.variable.research_prompt.format(company=state.company),
            answer_spec=format_answer_spec(state.variable.answer_spec),
            evidence_summary=evidence_summary,
        )
        
        # Try reasoning model first, then fast model
        for model, model_name in [(RESEARCH_MODEL, "Reasoning"), (SUMMARIZE_MODEL, "Fast")]:
            try:
                print(f"  ? Evaluating results ({model_name} Model)...", end="\r")
                response = await self.llm_client.complete_simple(
                    prompt=prompt,
                    system_prompt=RESEARCH_SYSTEM_PROMPT,
                    temperature=0.3,
                    max_tokens=16000 if model == RESEARCH_MODEL else 10000,
                    model_override=model,
                    fallback_model=SUMMARIZE_FALLBACK_MODEL if model == SUMMARIZE_MODEL else None,
                )
                
                if response and response.strip():
                    print(f"  + Evaluation complete ({model_name} Model)   ")
                    return self._parse_evaluation_json(response)
                
                if model == RESEARCH_MODEL:
                    print(f"  ! {model_name} model returned empty. Switching to Fast Model...")
                    logger.warning(f"{model_name} model returned empty evaluation. Falling back.")
                    
            except Exception as e:
                if model == RESEARCH_MODEL:
                    print(f"  ! {model_name} model failed. Switching to Fast Model...")
                    logger.warning(f"{model_name} model evaluation failed: {e}. Falling back.")
                else:
                    print(f"  x Evaluation failed completely.")
                    logger.warning(f"Fast model evaluation failed: {e}. Assuming insufficient.")
        
        return {"sufficient": False, "confidence": "low", "missing": ["Evaluation failed"]}
    
    def _parse_evaluation_json(self, response: str) -> Dict[str, Any]:
        """Parse evaluation response, handling both JSON and legacy formats."""
        result = {
            "sufficient": False,
            "confidence": "low",
            "missing": [],
            "next_queries": [],
        }
        
        # Try to extract JSON from <evaluation_json> tags
        json_match = re.search(r'<evaluation_json>\s*(.*?)\s*</evaluation_json>', response, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group(1))
                result["sufficient"] = parsed.get("sufficient", False)
                result["confidence"] = parsed.get("confidence", "low")
                result["missing"] = parsed.get("missing", [])
                result["next_queries"] = parsed.get("next_queries", [])
                return result
            except json.JSONDecodeError:
                logger.debug("Failed to parse evaluation JSON, falling back to text parsing")
        
        # Fallback: parse legacy text format
        for line in response.strip().split("\n"):
            line = line.strip()
            if line.upper().startswith("SUFFICIENT:"):
                value = line.split(":", 1)[1].strip().lower()
                result["sufficient"] = value in ("yes", "true", "1")
            elif line.upper().startswith("CONFIDENCE:"):
                value = line.split(":", 1)[1].strip().lower()
                if value in ("high", "medium", "low"):
                    result["confidence"] = value
            elif line.upper().startswith("MISSING:"):
                missing_text = line.split(":", 1)[1].strip()
                if missing_text.lower() != "none":
                    result["missing"] = [missing_text]
        
        return result
    
    async def _synthesize(self, state: ResearchState) -> SynthesisResult:
        """Synthesize gathered information into a comprehensive answer with citations."""
        if not state.gathered_info and not state.evidence_passages:
            return SynthesisResult(
                comprehensive_markdown=f"Unable to find sufficient information about {state.variable.name} for {state.company}.",
                claims=[],
                gaps=["No information gathered"],
            )
        
        # Build evidence pack for synthesis
        if state.evidence_sources and state.evidence_passages:
            evidence_pack = EvidencePack(
                sources=state.evidence_sources,
                passages=state.evidence_passages,
                total_chars=sum(len(p.text) for p in state.evidence_passages),
                avg_source_score=sum(s.source_score for s in state.evidence_sources) / len(state.evidence_sources) if state.evidence_sources else 0,
            )
            evidence_text = evidence_pack.format_for_prompt()
        else:
            # Fallback to legacy format if no evidence pack
            evidence_text = format_gathered_info_for_synthesis(state.gathered_info)
        
        prompt = SYNTHESIS_PROMPT.format(
            company=state.company,
            variable_name=state.variable.name,
            research_prompt=state.variable.research_prompt.format(company=state.company),
            answer_spec=format_answer_spec(state.variable.answer_spec),
            evidence_pack=evidence_text,
        )
        
        # Try reasoning model first, then fast model
        for model, model_name in [(RESEARCH_MODEL, "Reasoning"), (SUMMARIZE_MODEL, "Fast")]:
            try:
                print(f"  ? Synthesizing answer ({model_name} Model)...", end="\r")
                response = await self.llm_client.complete_simple(
                    prompt=prompt,
                    system_prompt=RESEARCH_SYSTEM_PROMPT,
                    temperature=0.5,
                    max_tokens=16000 if model == RESEARCH_MODEL else 4000,
                    model_override=model,
                    fallback_model=SUMMARIZE_FALLBACK_MODEL if model == SUMMARIZE_MODEL else None,
                )
                
                if response and response.strip():
                    print(f"  + Synthesis complete ({model_name} Model)    ")
                    return self._parse_synthesis_json(response)
                
                if model == RESEARCH_MODEL:
                    print(f"  ! {model_name} model returned empty. Switching to Fast Model...")
                    logger.warning(f"{model_name} model returned empty synthesis. Falling back.")
                    
            except Exception as e:
                if model == RESEARCH_MODEL:
                    print(f"  ! {model_name} model failed. Switching to Fast Model...")
                    logger.warning(f"{model_name} model synthesis failed: {e}. Falling back.")
                else:
                    print(f"  x Synthesis failed completely.")
                    logger.error(f"Fast model synthesis failed: {e}")
        
        # Final fallback
        return SynthesisResult(
            comprehensive_markdown=self._fallback_synthesis(state),
            claims=[],
            gaps=["Synthesis failed"],
            parse_error="All synthesis attempts failed",
        )
    
    def _parse_synthesis_json(self, response: str) -> SynthesisResult:
        """Parse synthesis response, handling both JSON and plain text."""
        # Try to extract JSON from <synthesis_json> tags
        json_match = re.search(r'<synthesis_json>\s*(.*?)\s*</synthesis_json>', response, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group(1))
                claims = []
                for c in parsed.get("claims", []):
                    claims.append(Claim(
                        text=c.get("text", ""),
                        source_ids=c.get("source_ids", []),
                        confidence=c.get("confidence", "medium"),
                    ))
                return SynthesisResult(
                    comprehensive_markdown=parsed.get("comprehensive_markdown", ""),
                    claims=claims,
                    gaps=parsed.get("gaps", []),
                    raw_response=response,
                )
            except json.JSONDecodeError as e:
                logger.debug(f"Failed to parse synthesis JSON: {e}")
        
        # Fallback: use response as comprehensive text
        return SynthesisResult(
            comprehensive_markdown=response.strip(),
            claims=[],
            gaps=[],
            raw_response=response,
            parse_error="Could not parse JSON, using raw response",
        )
    
    def _fallback_synthesis(self, state: ResearchState) -> str:
        """Create fallback synthesis from snippets."""
        snippets = [info.get("snippet", "") for info in state.gathered_info[:5]]
        return f"Research on {state.variable.name} for {state.company}:\n\n" + "\n\n".join(snippets)
    
    async def _verify_and_fix(
        self,
        comprehensive: str,
        state: ResearchState,
    ) -> Tuple[str, bool]:
        """
        Verify numeric claims and fix unsupported ones.
        
        Returns:
            Tuple of (possibly fixed text, whether confidence was reduced)
        """
        numbers = extract_numbers(comprehensive)
        if not numbers:
            return comprehensive, False
        
        results, unsupported = verify_numbers_against_evidence(
            numbers,
            state.evidence_passages,
        )
        
        if not unsupported:
            return comprehensive, False
        
        confidence_reduced = should_reduce_confidence(results)
        
        # If too many unsupported numbers, try to fix
        if len(unsupported) >= 2:
            try:
                fix_prompt = NUMERIC_FIX_PROMPT.format(
                    text=comprehensive,
                    unsupported_numbers=format_unsupported_for_fix(unsupported),
                    evidence_passages="\n".join(p.text[:200] for p in state.evidence_passages[:5]),
                )
                
                fixed = await self.llm_client.complete_simple(
                    prompt=fix_prompt,
                    system_prompt="You are a careful editor. Remove or qualify unsupported claims.",
                    temperature=0.3,
                    max_tokens=4000,
                    model_override=SUMMARIZE_MODEL,
                    fallback_model=SUMMARIZE_FALLBACK_MODEL,
                )
                
                if fixed and fixed.strip():
                    logger.info(f"Fixed {len(unsupported)} unsupported numbers in synthesis")
                    return fixed.strip(), confidence_reduced
                    
            except Exception as e:
                logger.warning(f"Failed to fix unsupported numbers: {e}")
        
        return comprehensive, confidence_reduced
    
    async def _summarize(
        self,
        company: str,
        variable_name: str,
        comprehensive: str,
        max_chars: int,
    ) -> str:
        """Summarize comprehensive answer with length enforcement."""
        summarize_system_prompt = """You are a concise business analyst writing table cells for competitive analysis.
Your output must be plain text only - no markdown formatting, no headers, no bullets, no bold.
Write clear, factual prose with specific numbers when available."""

        try:
            prompt = SUMMARIZE_PROMPT.format(
                company=company,
                variable_name=variable_name,
                max_chars=max_chars,
                comprehensive_answer=comprehensive,
            )
            
            response = await self.llm_client.complete_simple(
                prompt=prompt,
                system_prompt=summarize_system_prompt,
                temperature=0.3,
                max_tokens=500,
                model_override=SUMMARIZE_MODEL,
                fallback_model=SUMMARIZE_FALLBACK_MODEL,
            )
            
            if not response:
                logger.warning("LLM returned None/empty for summarization, using fallback")
                return self._create_fallback_summary(comprehensive, max_chars)
            
            result = self._clean_markdown(response.strip())
            
            # If still too long, run tighten pass
            if len(result) > max_chars:
                result = await self._tighten_summary(result, max_chars)
            
            if not result or len(result) < 20:
                logger.warning("LLM returned empty/short summary, using fallback")
                return self._create_fallback_summary(comprehensive, max_chars)
            
            return result
            
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            return self._create_fallback_summary(comprehensive, max_chars)
    
    async def _tighten_summary(self, summary: str, max_chars: int) -> str:
        """Run a second pass to shorten an over-long summary."""
        try:
            prompt = TIGHTEN_PROMPT.format(
                max_chars=max_chars,
                current_chars=len(summary),
                summary=summary,
            )
            
            response = await self.llm_client.complete_simple(
                prompt=prompt,
                system_prompt="You are a concise editor. Shorten text while keeping key facts.",
                temperature=0.3,
                max_tokens=300,
                model_override=SUMMARIZE_MODEL,
                fallback_model=SUMMARIZE_FALLBACK_MODEL,
            )
            
            if response:
                result = self._clean_markdown(response.strip())
                if len(result) <= max_chars:
                    return result
        except Exception as e:
            logger.warning(f"Tighten pass failed: {e}")
        
        # Hard truncation as last resort
        return summary[:max_chars - 3] + "..."
    
    def _extract_search_queries(self, response: str, company: str) -> List[str]:
        """Extract search queries from LLM response."""
        queries = []
        
        # First, try to extract from <queries> tags
        queries_match = re.search(r'<queries>\s*(.*?)\s*</queries>', response, re.DOTALL | re.IGNORECASE)
        if queries_match:
            queries_text = queries_match.group(1)
            for line in queries_text.strip().split("\n"):
                line = line.strip().strip('"\'')
                line = re.sub(r"^[\d\.\-\*\)\•]+\s*", "", line)
                if line and 10 < len(line) < 100:
                    queries.append(line)
            if queries:
                return queries
        
        # Fallback: filter out reasoning text
        reasoning_patterns = [
            r'^(we |i |let\'s |okay|the |this |these |to |for |here |now |first|based on)',
            r'(should|would|could|need to|want to|trying to|looking for)',
            r'[:]{1}$',
        ]
        
        for line in response.strip().split("\n"):
            line = line.strip()
            if not line or len(line) < 10 or len(line) > 100:
                continue
            
            is_reasoning = any(re.search(p, line.lower()) for p in reasoning_patterns)
            if is_reasoning:
                continue
            
            line = re.sub(r"^[\d\.\-\*\)\•]+\s*", "", line)
            line = line.strip('"\'')
            
            if len(line) < 10:
                continue
            
            if company.lower() in line.lower():
                queries.insert(0, line)
            else:
                queries.append(line)
        
        return queries
    
    def _clean_markdown(self, text: str) -> str:
        """Strip all markdown formatting from text."""
        if not text:
            return text
        
        cleaned = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        cleaned = re.sub(r'\*\*([^*]+)\*\*', r'\1', cleaned)
        cleaned = re.sub(r'\*([^*]+)\*', r'\1', cleaned)
        cleaned = re.sub(r'__([^_]+)__', r'\1', cleaned)
        cleaned = re.sub(r'_([^_]+)_', r'\1', cleaned)
        cleaned = re.sub(r'^\s*[\-\*\•]\s+', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'^\s*\d+\.\s+', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'\n\s*\n', ' ', cleaned)
        cleaned = re.sub(r'\n', ' ', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        return cleaned.strip()
    
    def _create_fallback_summary(self, comprehensive: str, max_chars: int = 240) -> str:
        """Create a fallback summary from comprehensive text."""
        clean_text = self._clean_markdown(comprehensive)
        
        if not clean_text:
            return "No information available."
        
        sentences = re.split(r'(?<=[.!?])\s+', clean_text)
        result_sentences = []
        total_length = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20:
                continue
            
            if total_length + len(sentence) > max_chars and result_sentences:
                break
            
            result_sentences.append(sentence)
            total_length += len(sentence) + 1
            
            if len(result_sentences) >= 3:
                break
        
        if result_sentences:
            result = ' '.join(result_sentences)
            if not result.endswith(('.', '!', '?')):
                result += '.'
            if len(result) > max_chars:
                result = result[:max_chars - 3] + "..."
            return result
        
        if len(clean_text) > max_chars:
            return clean_text[:max_chars - 3] + "..."
        return clean_text
    
    def _extract_info(self, search_result: SearchResult) -> List[Dict[str, Any]]:
        """Extract relevant information from a search result."""
        info_list = []
        for item in search_result.items:
            info_list.append({
                "title": item.title,
                "url": item.url,
                "snippet": item.snippet,
                "query": search_result.query,
                "domain": item.domain,
                "source_score": item.source_score,
                "is_official": item.is_official,
            })
        return info_list
    
    def _build_sources(self, state: ResearchState) -> List[ResearchSource]:
        """Build deduplicated list of sources from gathered information."""
        seen_urls = set()
        sources = []
        
        # Prefer evidence sources if available
        if state.evidence_sources:
            for src in state.evidence_sources:
                if src.url not in seen_urls:
                    seen_urls.add(src.url)
                    sources.append(ResearchSource(
                        title=src.title,
                        url=src.url,
                        snippet="",
                        query="",
                        domain=src.domain,
                        source_score=src.source_score,
                        is_official=src.is_official,
                    ))
        
        # Add from gathered info
        for info in state.gathered_info:
            url = info.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                sources.append(ResearchSource(
                    title=info.get("title", "Unknown"),
                    url=url,
                    snippet=info.get("snippet", "")[:200],
                    query=info.get("query", ""),
                    domain=info.get("domain", ""),
                    source_score=info.get("source_score", 0.5),
                    is_official=info.get("is_official", False),
                ))
        
        # Sort by score descending
        sources.sort(key=lambda x: -x.source_score)
        return sources[:10]
    
    def _build_metadata(self, state: ResearchState) -> Dict[str, Any]:
        """Build rich metadata about the research process."""
        avg_score = 0.0
        if state.evidence_sources:
            avg_score = sum(s.source_score for s in state.evidence_sources) / len(state.evidence_sources)
        
        return {
            "iterations": state.iteration,
            "searches": len(state.search_results),
            "pages_fetched": state.pages_fetched,
            "pages_failed": state.pages_failed,
            "evidence_sources_used": len(state.evidence_sources),
            "evidence_passages_count": len(state.evidence_passages),
            "avg_source_score": round(avg_score, 3),
            "total_evidence_chars": sum(len(p.text) for p in state.evidence_passages),
            "model_used": RESEARCH_MODEL,
            "verification_applied": self.enable_verification,
            "page_fetch_enabled": self.enable_page_fetch,
        }
