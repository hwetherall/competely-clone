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

# Model configuration: use specialized models for different tasks
RESEARCH_MODEL = settings.RESEARCH_MODEL  # Tongyi DeepResearch for agentic tasks
SUMMARIZE_MODEL = settings.SUMMARIZE_MODEL  # Fast model for summarization


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
        skip_evaluation: bool = False,
    ):
        """
        Initialize the research agent.
        
        Args:
            search_client: SearchClient instance (creates new if not provided)
            llm_client: LLMClient instance (creates new if not provided)
            max_iterations: Maximum research iterations (default from settings)
            min_iterations: Minimum iterations before checking sufficiency
            skip_evaluation: If True, skip LLM evaluation step (faster but less thorough)
        """
        self.search_client = search_client or SearchClient()
        self.llm_client = llm_client or LLMClient()
        self.max_iterations = max_iterations or settings.MAX_RESEARCH_ITERATIONS
        self.min_iterations = min_iterations or settings.MIN_RESEARCH_ITERATIONS
        self.skip_evaluation = skip_evaluation
    
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
                
                # Step 3: Evaluate if we have enough information (skip if flag set)
                if state.iteration >= self.min_iterations and not self.skip_evaluation:
                    evaluation = await self._evaluate_results(state)
                    state.is_sufficient = evaluation.get("sufficient", False)
                    state.confidence = evaluation.get("confidence", "low")
                    
                    if state.is_sufficient:
                        logger.info(f"Sufficient information gathered after {state.iteration} iterations")
                        break
                    else:
                        logger.info(f"Need more information. Missing: {evaluation.get('missing', 'unknown')}")
                elif self.skip_evaluation:
                    # In fast mode, assume medium confidence and move on
                    state.confidence = "medium"
                    state.is_sufficient = True
                    logger.info(f"Fast mode: skipping evaluation after {state.iteration} iterations")
                    break
            
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
            
            # Use FAST model for query generation - reasoning models waste tokens
            # on "thinking" and often return empty content. Query generation is
            # a simple task that doesn't need deep reasoning.
            response = await self.llm_client.complete_simple(
                prompt=prompt,
                system_prompt=RESEARCH_SYSTEM_PROMPT,
                temperature=0.7,
                max_tokens=1000,  # Queries are short, don't need many tokens
                model_override=SUMMARIZE_MODEL,  # Use fast model, NOT reasoning model
            )
            
            # Handle empty or None response
            if not response:
                logger.warning("LLM returned empty response for query generation. Using fallback.")
                return [
                    f"{company} {variable.name} 2024",
                    f"{company} {variable.name} analysis",
                ]
            
            # Parse queries from response - handle reasoning models that include thinking
            queries = self._extract_search_queries(response, company)
            
            # Ensure we have at least some queries
            if not queries:
                logger.warning("No queries extracted from LLM response. Using fallback.")
                return [
                    f"{company} {variable.name} 2024",
                    f"{company} {variable.name} analysis",
                ]
            
            return queries[:5]  # Limit to 5 queries per iteration
            
        except LLMError as e:
            logger.warning(f"LLM query generation failed: {e}. Using fallback queries.")
            # Fallback: generate basic queries
            return [
                f"{company} {variable.name} 2024",
                f"{company} {variable.name} analysis",
            ]
        except Exception as e:
            logger.error(f"Unexpected error in query generation: {e}. Using fallback queries.")
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
            
            # Use FAST model for evaluation - reasoning models waste tokens on
            # "thinking" and often return empty content. Evaluation is a
            # structured task that doesn't need deep reasoning.
            response = await self.llm_client.complete_simple(
                prompt=prompt,
                system_prompt=RESEARCH_SYSTEM_PROMPT,
                temperature=0.3,  # Lower temperature for more consistent evaluation
                max_tokens=1000,  # Evaluation responses are short
                model_override=SUMMARIZE_MODEL,  # Use fast model, NOT reasoning model
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
            
            # Use research model for synthesis - needs more tokens for deep reasoning
            # Falls back to summarize model if research model is unavailable
            response = await self.llm_client.complete_simple(
                prompt=prompt,
                system_prompt=RESEARCH_SYSTEM_PROMPT,
                temperature=0.5,
                max_tokens=4000,  # More tokens for comprehensive synthesis
                model_override=RESEARCH_MODEL,
                fallback_model=SUMMARIZE_MODEL,
            )
            
            # Handle empty response
            if not response or not response.strip():
                logger.warning("LLM returned empty synthesis. Using fallback.")
                snippets = [info.get("snippet", "") for info in state.gathered_info[:5]]
                return f"Research on {state.variable.name} for {state.company}:\n\n" + "\n\n".join(snippets)
            
            return response.strip()
            
        except LLMError as e:
            logger.error(f"LLM synthesis failed: {e}")
            # Fallback: return raw snippets
            snippets = [info.get("snippet", "") for info in state.gathered_info[:5]]
            return f"Research on {state.variable.name} for {state.company}:\n\n" + "\n\n".join(snippets)
        except Exception as e:
            logger.error(f"Unexpected error in synthesis: {e}")
            snippets = [info.get("snippet", "") for info in state.gathered_info[:5]]
            return f"Research on {state.variable.name} for {state.company}:\n\n" + "\n\n".join(snippets)
    
    async def _summarize(self, company: str, variable_name: str, comprehensive: str) -> str:
        """
        Summarize comprehensive answer into concise version.
        
        Uses a fast model for summarization since this is a simple task.
        
        Args:
            company: Company name
            variable_name: Variable name
            comprehensive: The comprehensive answer to summarize
            
        Returns:
            Concise summary (1-3 sentences, plain text)
        """
        # Dedicated system prompt for summarization (no markdown)
        summarize_system_prompt = """You are a concise business analyst writing table cells for competitive analysis.
Your output must be plain text only - no markdown formatting, no headers, no bullets, no bold.
Write clear, factual prose with specific numbers when available."""

        try:
            prompt = SUMMARIZE_PROMPT.format(
                company=company,
                variable_name=variable_name,
                comprehensive_answer=comprehensive,
            )
            
            # Use fast summarization model - doesn't need deep reasoning
            response = await self.llm_client.complete_simple(
                prompt=prompt,
                system_prompt=summarize_system_prompt,
                temperature=0.3,
                max_tokens=300,
                model_override=SUMMARIZE_MODEL,
            )
            
            # Handle None or empty response
            if not response:
                logger.warning("LLM returned None/empty for summarization, using fallback")
                return self._create_fallback_summary(comprehensive)
            
            # Clean any markdown that may have slipped through
            result = self._clean_markdown(response.strip())
            
            # If result is too short after cleaning, use fallback
            if not result or len(result) < 20:
                logger.warning("LLM returned empty/short summary, using fallback")
                return self._create_fallback_summary(comprehensive)
            
            return result
            
        except LLMError as e:
            logger.error(f"LLM summarization failed: {e}")
            return self._create_fallback_summary(comprehensive)
        except Exception as e:
            logger.error(f"Unexpected error in summarization: {e}")
            return self._create_fallback_summary(comprehensive)
    
    def _extract_search_queries(self, response: str, company: str) -> List[str]:
        """
        Extract search queries from LLM response.
        
        Handles reasoning models (like Tongyi DeepResearch) that include thinking
        in their response. First looks for <queries> tags, then falls back to
        filtering heuristics.
        
        Args:
            response: Raw LLM response text
            company: Company name (queries should contain this)
            
        Returns:
            List of clean search queries
        """
        queries = []
        
        # First, try to extract from <queries> tags
        queries_match = re.search(r'<queries>\s*(.*?)\s*</queries>', response, re.DOTALL | re.IGNORECASE)
        if queries_match:
            queries_text = queries_match.group(1)
            for line in queries_text.strip().split("\n"):
                line = line.strip().strip('"\'')
                line = re.sub(r"^[\d\.\-\*\)\•]+\s*", "", line)  # Remove prefixes
                if line and 10 < len(line) < 100:
                    queries.append(line)
            if queries:
                logger.debug(f"Extracted {len(queries)} queries from <queries> tags")
                return queries
        
        # Fallback: filter out reasoning text
        # Patterns that indicate reasoning/thinking text (not queries)
        reasoning_patterns = [
            r'^(we |i |let\'s |okay|the |this |these |to |for |here |now |first|based on)',
            r'(should|would|could|need to|want to|trying to|looking for)',
            r'(previously|already|avoid|cover|highlight|emphasize)',
            r'^(key points|official|investor|how they|what makes)',
            r'[:]{1}$',  # Lines ending with colon (likely headers)
            r'^\d+\.\s+[A-Z]',  # Numbered reasoning steps like "1. First we..."
        ]
        
        for line in response.strip().split("\n"):
            line = line.strip()
            
            # Skip empty, very short, or very long lines
            if not line or len(line) < 10 or len(line) > 100:
                continue
            
            # Skip lines that look like reasoning/thinking
            is_reasoning = False
            for pattern in reasoning_patterns:
                if re.search(pattern, line.lower()):
                    is_reasoning = True
                    break
            
            if is_reasoning:
                continue
            
            # Clean up the line
            line = re.sub(r"^[\d\.\-\*\)\•]+\s*", "", line)
            line = re.sub(r"^(Search\s+for\s+|Query:\s*)", "", line, flags=re.IGNORECASE)
            line = line.strip('"\'')
            
            if len(line) < 10:
                continue
            
            # Prefer queries that contain the company name
            if company.lower() in line.lower():
                queries.insert(0, line)
            else:
                queries.append(line)
        
        # Final fallback: extract any line with company name
        if len(queries) < 2:
            logger.warning(f"Query extraction found only {len(queries)} queries, using fallback")
            fallback_queries = []
            for line in response.strip().split("\n"):
                line = line.strip().strip('"\'')
                line = re.sub(r"^[\d\.\-\*\)\•]+\s*", "", line)
                if company.lower() in line.lower() and 10 < len(line) < 80:
                    if line and line not in fallback_queries:
                        fallback_queries.append(line)
            if fallback_queries:
                queries = fallback_queries[:5]
        
        return queries

    def _clean_markdown(self, text: str) -> str:
        """
        Strip all markdown formatting from text.
        
        Removes:
        - # headers
        - **bold** and *italic*
        - Bullet points (-, *, •)
        - Numbered lists
        - Multiple newlines
        
        Args:
            text: Text potentially containing markdown
            
        Returns:
            Clean plain text
        """
        if not text:
            return text
        
        # Remove markdown headers (# ## ### etc.)
        cleaned = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        
        # Remove **bold** formatting
        cleaned = re.sub(r'\*\*([^*]+)\*\*', r'\1', cleaned)
        
        # Remove *italic* formatting
        cleaned = re.sub(r'\*([^*]+)\*', r'\1', cleaned)
        
        # Remove __bold__ formatting
        cleaned = re.sub(r'__([^_]+)__', r'\1', cleaned)
        
        # Remove _italic_ formatting
        cleaned = re.sub(r'_([^_]+)_', r'\1', cleaned)
        
        # Remove bullet points at start of lines (-, *, •)
        cleaned = re.sub(r'^\s*[\-\*\•]\s+', '', cleaned, flags=re.MULTILINE)
        
        # Remove numbered lists (1. 2. etc.)
        cleaned = re.sub(r'^\s*\d+\.\s+', '', cleaned, flags=re.MULTILINE)
        
        # Collapse multiple newlines to single space
        cleaned = re.sub(r'\n\s*\n', ' ', cleaned)
        
        # Replace remaining newlines with spaces
        cleaned = re.sub(r'\n', ' ', cleaned)
        
        # Collapse multiple spaces
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        return cleaned.strip()

    def _create_fallback_summary(self, comprehensive: str) -> str:
        """
        Create a fallback summary from comprehensive text.
        
        Extracts 2-3 sentences (up to ~300 chars) from the clean text.
        
        Args:
            comprehensive: The comprehensive text to summarize
            
        Returns:
            Plain text summary (1-3 sentences)
        """
        # First, clean any markdown formatting
        clean_text = self._clean_markdown(comprehensive)
        
        if not clean_text:
            return "No information available."
        
        # Split into sentences and collect meaningful ones
        sentences = re.split(r'(?<=[.!?])\s+', clean_text)
        result_sentences = []
        total_length = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            # Skip fragments shorter than 20 chars
            if len(sentence) < 20:
                continue
            
            # Check if adding this sentence would exceed our limit (~300 chars)
            if total_length + len(sentence) > 300 and result_sentences:
                break
            
            result_sentences.append(sentence)
            total_length += len(sentence) + 1  # +1 for space
            
            # Stop after 3 sentences
            if len(result_sentences) >= 3:
                break
        
        if result_sentences:
            result = ' '.join(result_sentences)
            # Ensure it ends with punctuation
            if not result.endswith(('.', '!', '?')):
                result += '.'
            return result
        
        # Last resort: truncate clean text
        if len(clean_text) > 150:
            return clean_text[:147] + "..."
        return clean_text
    
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
