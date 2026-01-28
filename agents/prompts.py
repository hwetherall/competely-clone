"""
Prompt templates for the research agent.

These prompts guide the LLM through the research process:
1. Query generation
2. Result evaluation
3. Answer synthesis
4. Summarization
"""

# =============================================================================
# System Prompts
# =============================================================================

RESEARCH_SYSTEM_PROMPT = """You are a competitive intelligence research agent. Your task is to gather accurate, specific information about companies for competitive analysis.

Guidelines:
- Be factual and cite specific sources when possible
- Distinguish between facts, estimates, and opinions
- If information is uncertain, say so
- Focus on recent information (prefer 2024-2025 data)
- Be concise but comprehensive
- Use specific numbers, percentages, and data points when available"""


# =============================================================================
# Query Generation
# =============================================================================

QUERY_GENERATION_PROMPT = """Generate 3-5 Google search queries for this research task.

Company: {company}
Variable: {variable_name}
Research Goal: {research_prompt}

Previous queries tried (avoid repeating these):
{previous_queries}

Requirements:
- Each query should be what you'd type into Google
- Include the company name "{company}" in each query
- Add years (2024, 2025) for recent data
- Target official sources, analyst reports, or news coverage
- Keep each query under 60 characters

OUTPUT FORMAT: Output the queries between <queries> tags, one per line:

<queries>
{company} payment processing fees 2024
{company} vs competitors comparison
{company} official documentation features
</queries>

Generate your queries now:"""


# =============================================================================
# Result Evaluation
# =============================================================================

EVALUATION_PROMPT = """Evaluate whether the search results provide sufficient information to answer the research question.

Company: {company}
Variable: {variable_name}
Research Goal: {research_prompt}

Search Results Summary:
{search_results}

Questions to consider:
1. Do the results contain specific, factual information about {company}?
2. Are the sources authoritative (official website, reputable publications)?
3. Is the information recent and relevant?
4. Do we have enough detail to write a comprehensive answer?

Respond in EXACTLY this format:
SUFFICIENT: [yes/no]
CONFIDENCE: [high/medium/low]
MISSING: [what specific information is still needed, or "none" if sufficient]
SUGGESTED_QUERIES: [1-2 additional queries to try, or "none" if sufficient]"""


# =============================================================================
# Synthesis
# =============================================================================

SYNTHESIS_PROMPT = """Based on the research gathered, write a comprehensive answer about {variable_name} for {company}.

Research Goal:
{research_prompt}

Information Gathered:
{gathered_information}

Write a comprehensive, well-structured answer that:
1. Directly addresses the research goal
2. Includes specific facts, numbers, and details where available
3. Notes the sources of key information
4. Acknowledges any uncertainty or gaps
5. Is 2-4 paragraphs long (150-300 words)

Important: Focus on {company} specifically. If information is not available, say so rather than making assumptions.

Comprehensive Answer:"""


# =============================================================================
# Summarization
# =============================================================================

SUMMARIZE_PROMPT = """Your task is to write a concise summary for a competitive analysis table cell.

Company: {company}
Variable: {variable_name}

Full Analysis:
{comprehensive_answer}

INSTRUCTIONS:
- Write exactly 1-3 sentences
- Do NOT use any markdown formatting (no headers, no bullets, no bold)
- Do NOT start with the company name or variable name as a header
- Include the most important specific facts or numbers
- Write in plain prose suitable for a table cell

EXAMPLE FORMAT:
"The company generates revenue primarily through transaction fees of 2.9% + $0.30 per transaction, with additional fees for international cards. Enterprise customers negotiate custom rates."

YOUR SUMMARY (1-3 sentences, no formatting):"""


# =============================================================================
# Helper Functions
# =============================================================================

def format_search_results_for_evaluation(search_results: list) -> str:
    """
    Format search results into a string for the evaluation prompt.
    
    Args:
        search_results: List of SearchResult objects
        
    Returns:
        Formatted string with search results
    """
    lines = []
    for i, result in enumerate(search_results, 1):
        lines.append(f"\n--- Search {i}: '{result.query}' ---")
        for item in result.items[:5]:  # Top 5 results per search
            lines.append(f"• {item.title}")
            lines.append(f"  URL: {item.url}")
            lines.append(f"  {item.snippet[:200]}...")
    return "\n".join(lines)


def format_gathered_info_for_synthesis(gathered_info: list) -> str:
    """
    Format gathered information into a string for the synthesis prompt.
    
    Args:
        gathered_info: List of dicts with title, url, snippet, query
        
    Returns:
        Formatted string with gathered information
    """
    lines = []
    seen_urls = set()
    
    for info in gathered_info:
        url = info.get("url", "")
        if url in seen_urls:
            continue
        seen_urls.add(url)
        
        lines.append(f"\nSource: {info.get('title', 'Unknown')}")
        lines.append(f"URL: {url}")
        lines.append(f"Content: {info.get('snippet', '')}")
    
    return "\n".join(lines)
