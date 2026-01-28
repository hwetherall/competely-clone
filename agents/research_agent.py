"""
Research Agent for competitive analysis.

This agent performs iterative research on a (Company, Variable) pair:
1. Generate search queries based on the variable definition
2. Search and gather results using the SearchClient
3. Evaluate if gathered information is sufficient
4. Refine queries and search more if needed
5. Synthesize comprehensive answer using LLM
6. Create concise summary for table display
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime

from agents.search_client import SearchClient, SearchResult
from agents.llm_client import LLMClient, LLMError
from agents.prompts import (
    RESEARCH_SYSTEM_PROMPT,
    QUERY_GENERATION_PROMPT,
    EVALUATION_PROMPT,
    SYNTHESIS_PROMPT,
    SUMMARIZE_PROMPT,
    format_search_results_for_evaluation,
    format_gathered_info_for_synthesis,
)
from config.variables import VariableDefinition, get_variable
from config import settings

logger = logging.getLogger(__name__)


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


@dataclass
class ResearchResult:
    """Complete result of a research task."""
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
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "company": self.company,
            "variable_id": self.variable_id,
            "variable_name": self.variable_name,
            "concise": self.concise,
            "comprehensive": self.comprehensive,
            "sources": [
                {"title": s.title, "url": s.url, "snippet": s.snippet, "query": s.query}
                for s in self.sources
            ],
            "confidence": self.confidence,
            "iterations": self.iterations,
            "total_searches": self.total_searches,
            "timestamp": self.timestamp,
            "error": self.error,
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


# =============================================================================
# Research Agent
# =============================================================================

class ResearchAgent:
    """
    Agent that performs iterative research for competitive analysis.
    
    The research flow:
    1. Start with example queries from the variable definition
    2. Search and gather results
    3. Evaluate if we have enough information
    4. If not, generate refined queries using LLM and search again
    5. Synthesize all gathered information into a comprehensive answer
    6. Summarize into a concise version for table display
    
    Example:
        agent = ResearchAgent()
        result = await agent.research("Stripe", "unique_value_proposition")
        print(result.concise)
        print(result.comprehensive)
    """
    
    def __init__(
        self,
        search_client: Optional[SearchClient] = None,
        llm_client: Optional[LLMClient] = None,
        max_iterations: Optional[int] = None,
        min_iterations: Optional[int] = None,
    ):
        """
        Initialize the research agent.
        
        Args:
            search_client: SearchClient instance (creates new if not provided)
            llm_client: LLMClient instance (creates new if not provided)
            max_iterations: Maximum research iterations (default from settings)
            min_iterations: Minimum iterations before checking sufficiency
        """
        self.search_client = search_client or SearchClient()
        self.llm_client = llm_client or LLMClient()
        self.max_iterations = max_iterations or settings.MAX_RESEARCH_ITERATIONS
        self.min_iterations = min_iterations or settings.MIN_RESEARCH_ITERATIONS
    
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
                
                # Step 2: Execute searches
                for query in queries:
                    if query not in state.queries_tried:
                        try:
                            result = await self.search_client.search(query, num_results=10)
                            state.queries_tried.append(query)
                            state.search_results.append(result)
                            state.gathered_info.extend(self._extract_info(result))
                            logger.debug(f"Search '{query[:40]}...' returned {result.total_results} results")
                        except Exception as e:
                            logger.warning(f"Search failed for '{query[:40]}...': {e}")
                            continue
                
                # Step 3: Evaluate if we have enough information
                if state.iteration >= self.min_iterations:
                    evaluation = await self._evaluate_results(state)
                    state.is_sufficient = evaluation.get("sufficient", False)
                    state.confidence = evaluation.get("confidence", "low")
                    
                    if state.is_sufficient:
                        logger.info(f"Sufficient information gathered after {state.iteration} iterations")
                        break
                    else:
                        logger.info(f"Need more information. Missing: {evaluation.get('missing', 'unknown')}")
            
            # Step 4: Synthesize comprehensive answer
            comprehensive = await self._synthesize(state)
            
            # Step 5: Create concise summary
            concise = await self._summarize(state.company, variable.name, comprehensive)
            
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
    
    async def _generate_queries(self, state: ResearchState) -> List[str]:
        """
        Generate search queries for the current iteration.
        
        On first iteration, uses example queries from the variable definition.
        On subsequent iterations, uses LLM to generate refined queries.
        
        Args:
            state: Current research state
            
        Returns:
            List of search queries to execute
        """
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
                previous_queries="\n".join(f"- {q}" for q in state.queries_tried) or "None yet",
            )
            
            response = await self.llm_client.complete_simple(
                prompt=prompt,
                system_prompt=RESEARCH_SYSTEM_PROMPT,
                temperature=0.7,
                max_tokens=500,
            )
            
            # Parse queries from response (one per line)
            queries = []
            for line in response.strip().split("\n"):
                line = line.strip()
                # Skip empty lines and lines that look like numbering
                if line and not line.startswith("#") and len(line) > 5:
                    # Remove common prefixes like "1.", "- ", etc.
                    line = re.sub(r"^[\d\.\-\*\)]+\s*", "", line)
                    # Remove "Search for" prefix that LLMs sometimes add
                    line = re.sub(r"^(Search\s+for\s+)", "", line, flags=re.IGNORECASE)
                    # Remove surrounding quotes
                    line = line.strip('"\'')
                    # Skip if too short after cleaning
                    if line and len(line) > 5:
                        queries.append(line)
            
            return queries[:5]  # Limit to 5 queries per iteration
            
        except LLMError as e:
            logger.warning(f"LLM query generation failed: {e}. Using fallback queries.")
            # Fallback: generate basic queries
            return [
                f"{company} {variable.name} 2024",
                f"{company} {variable.name} analysis",
            ]
    
    async def _evaluate_results(self, state: ResearchState) -> Dict[str, Any]:
        """
        Evaluate if gathered information is sufficient.
        
        Uses LLM to analyze the search results against the research goal.
        
        Args:
            state: Current research state
            
        Returns:
            Dict with 'sufficient' (bool), 'confidence' (str), 'missing' (str)
        """
        if not state.search_results:
            return {"sufficient": False, "confidence": "low", "missing": "No search results yet"}
        
        try:
            prompt = EVALUATION_PROMPT.format(
                company=state.company,
                variable_name=state.variable.name,
                research_prompt=state.variable.research_prompt.format(company=state.company),
                search_results=format_search_results_for_evaluation(state.search_results[-3:]),  # Last 3 searches
            )
            
            response = await self.llm_client.complete_simple(
                prompt=prompt,
                system_prompt=RESEARCH_SYSTEM_PROMPT,
                temperature=0.3,  # Lower temperature for more consistent evaluation
                max_tokens=500,
            )
            
            # Parse structured response
            result = {
                "sufficient": False,
                "confidence": "low",
                "missing": "",
                "suggested_queries": [],
            }
            
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
                    result["missing"] = line.split(":", 1)[1].strip()
                elif line.upper().startswith("SUGGESTED_QUERIES:"):
                    queries = line.split(":", 1)[1].strip()
                    if queries.lower() != "none":
                        result["suggested_queries"] = [q.strip() for q in queries.split(",")]
            
            return result
            
        except LLMError as e:
            logger.warning(f"LLM evaluation failed: {e}. Assuming insufficient.")
            return {"sufficient": False, "confidence": "low", "missing": "Evaluation failed"}
    
    async def _synthesize(self, state: ResearchState) -> str:
        """
        Synthesize gathered information into a comprehensive answer.
        
        Uses LLM to write a structured answer based on all gathered information.
        
        Args:
            state: Current research state
            
        Returns:
            Comprehensive answer string (2-4 paragraphs)
        """
        if not state.gathered_info:
            return f"Unable to find sufficient information about {state.variable.name} for {state.company}."
        
        try:
            prompt = SYNTHESIS_PROMPT.format(
                company=state.company,
                variable_name=state.variable.name,
                research_prompt=state.variable.research_prompt.format(company=state.company),
                gathered_information=format_gathered_info_for_synthesis(state.gathered_info),
            )
            
            response = await self.llm_client.complete_simple(
                prompt=prompt,
                system_prompt=RESEARCH_SYSTEM_PROMPT,
                temperature=0.5,
                max_tokens=1500,
            )
            
            return response.strip()
            
        except LLMError as e:
            logger.error(f"LLM synthesis failed: {e}")
            # Fallback: return raw snippets
            snippets = [info.get("snippet", "") for info in state.gathered_info[:5]]
            return f"Research on {state.variable.name} for {state.company}:\n\n" + "\n\n".join(snippets)
    
    async def _summarize(self, company: str, variable_name: str, comprehensive: str) -> str:
        """
        Summarize comprehensive answer into concise version.
        
        Args:
            company: Company name
            variable_name: Variable name
            comprehensive: The comprehensive answer to summarize
            
        Returns:
            Concise summary (1-3 sentences)
        """
        try:
            prompt = SUMMARIZE_PROMPT.format(
                company=company,
                variable_name=variable_name,
                comprehensive_answer=comprehensive,
            )
            
            response = await self.llm_client.complete_simple(
                prompt=prompt,
                system_prompt=RESEARCH_SYSTEM_PROMPT,
                temperature=0.3,
                max_tokens=200,
            )
            
            result = response.strip()
            
            # If LLM returned empty, use fallback
            if not result or len(result) < 10:
                logger.warning("LLM returned empty summary, using fallback")
                return self._create_fallback_summary(comprehensive)
            
            return result
            
        except LLMError as e:
            logger.error(f"LLM summarization failed: {e}")
            return self._create_fallback_summary(comprehensive)
    
    def _create_fallback_summary(self, comprehensive: str) -> str:
        """Create a fallback summary from comprehensive text."""
        # Try to extract first meaningful sentence
        sentences = comprehensive.split(".")
        for sentence in sentences:
            sentence = sentence.strip()
            # Skip empty or very short sentences
            if len(sentence) > 20:
                # Clean up markdown formatting
                sentence = re.sub(r"\*\*([^*]+)\*\*", r"\1", sentence)
                sentence = re.sub(r"\*([^*]+)\*", r"\1", sentence)
                return sentence + "."
        
        # Last resort: truncate comprehensive
        clean = re.sub(r"\*\*([^*]+)\*\*", r"\1", comprehensive[:150])
        return clean + "..."
    
    def _extract_info(self, search_result: SearchResult) -> List[Dict[str, Any]]:
        """
        Extract relevant information from a search result.
        
        Args:
            search_result: SearchResult from the search client
            
        Returns:
            List of dicts with title, url, snippet, query
        """
        info_list = []
        for item in search_result.items:
            info_list.append({
                "title": item.title,
                "url": item.url,
                "snippet": item.snippet,
                "query": search_result.query,
            })
        return info_list
    
    def _build_sources(self, state: ResearchState) -> List[ResearchSource]:
        """
        Build deduplicated list of sources from gathered information.
        
        Args:
            state: Current research state
            
        Returns:
            List of ResearchSource objects
        """
        seen_urls = set()
        sources = []
        
        for info in state.gathered_info:
            url = info.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                sources.append(ResearchSource(
                    title=info.get("title", "Unknown"),
                    url=url,
                    snippet=info.get("snippet", "")[:200],
                    query=info.get("query", ""),
                ))
        
        return sources[:10]  # Limit to top 10 sources
