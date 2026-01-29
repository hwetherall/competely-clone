"""
Prompt templates for the research agent.

These prompts guide the LLM through the research process:
1. Query generation
2. Result evaluation
3. Answer synthesis (with citations)
4. Summarization
5. Numeric verification/fix
"""

from typing import List, Dict, Any, Optional

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
- Use specific numbers, percentages, and data points when available
- NEVER make up numbers or statistics - only use what's in the evidence"""


# =============================================================================
# Query Generation
# =============================================================================

QUERY_GENERATION_PROMPT = """Generate 3-5 Google search queries for this research task.

Company: {company}
Variable: {variable_name}
Research Goal: {research_prompt}

What must be answered:
{answer_spec}

Previous queries tried (avoid repeating these):
{previous_queries}

Missing information from previous searches:
{missing_info}

Requirements:
- Each query should be what you'd type into Google
- Include the company name "{company}" in each query
- Add years (2024, 2025, 2026) for recent data
- Target official sources, analyst reports, or news coverage
- Focus on filling the gaps in missing information
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

EVALUATION_PROMPT = """Evaluate whether the evidence provides sufficient information to answer the research question.

Company: {company}
Variable: {variable_name}
Research Goal: {research_prompt}

What must be answered:
{answer_spec}

Evidence Gathered:
{evidence_summary}

Evaluate:
1. Do we have specific, factual information about {company} for EACH item in "What must be answered"?
2. Are the sources authoritative (official website, reputable publications, regulatory filings)?
3. Is the information recent and relevant?
4. Do we have enough detail to write a comprehensive answer with citations?

Respond with a JSON object inside <evaluation_json> tags:

<evaluation_json>
{{
  "sufficient": true,
  "confidence": "high",
  "covered_topics": ["topic1", "topic2"],
  "missing": ["specific information still needed"],
  "next_queries": ["query1", "query2"]
}}
</evaluation_json>

Rules:
- "sufficient": true only if we can answer MOST of the answer_spec items with evidence
- "confidence": "high" only if sources are authoritative and information is specific
- "missing": list specific gaps, or empty array if sufficient
- "next_queries": 1-2 queries to fill gaps, or empty array if sufficient

Your evaluation:"""


# =============================================================================
# Synthesis with Citations
# =============================================================================

SYNTHESIS_PROMPT = """Based on the evidence gathered, write a comprehensive answer about {variable_name} for {company}.

Research Goal:
{research_prompt}

What must be answered:
{answer_spec}

Evidence Pack (use these source IDs in citations):
{evidence_pack}

INSTRUCTIONS:
1. Write a comprehensive answer that addresses the research goal
2. Include specific facts, numbers, and details FROM THE EVIDENCE ONLY
3. Cite sources using [S1], [S2], etc. for each factual claim
4. Do NOT make up numbers or statistics - only use what appears in the evidence
5. Acknowledge any uncertainty or gaps
6. Be 2-4 paragraphs (150-300 words)

Output your response as JSON inside <synthesis_json> tags:

<synthesis_json>
{{
  "comprehensive_markdown": "Your full answer with [S1], [S2] citations inline...",
  "claims": [
    {{"text": "Specific factual claim from the answer", "source_ids": ["S1", "S3"], "confidence": "high"}},
    {{"text": "Another claim", "source_ids": ["S2"], "confidence": "medium"}}
  ],
  "gaps": ["Information we couldn't find", "Another gap"]
}}
</synthesis_json>

Rules for claims:
- Extract 3-8 key factual claims from your answer
- Each claim MUST have at least one source_id
- confidence: "high" if directly stated in source, "medium" if inferred, "low" if uncertain

Your synthesis:"""


# =============================================================================
# Summarization
# =============================================================================

SUMMARIZE_PROMPT = """Your task is to write a concise summary for a competitive analysis table cell.

Company: {company}
Variable: {variable_name}
Maximum characters: {max_chars}

Full Analysis:
{comprehensive_answer}

INSTRUCTIONS:
- Write exactly 1 sentence (2 max if absolutely necessary)
- MUST be under {max_chars} characters
- Do NOT use any markdown formatting (no headers, no bullets, no bold)
- Do NOT start with the company name or variable name as a header
- Focus on the single most important insight or number
- Write in plain, punchy prose suitable for a table cell

EXAMPLE FORMAT:
"Generates revenue through transaction fees of 2.9% + $0.30 [S1], with custom rates for enterprise clients [S2]."

YOUR SUMMARY (1-2 sentences, under {max_chars} chars, no formatting):"""


# =============================================================================
# Tighten Summary (if over limit)
# =============================================================================

TIGHTEN_PROMPT = """The summary below is too long. Shorten it to under {max_chars} characters while keeping the most important facts.

Current summary ({current_chars} chars):
{summary}

Requirements:
- MUST be under {max_chars} characters
- Keep the most important specific facts or numbers
- Remove less critical details
- Maintain readability
- No markdown formatting

Shortened summary:"""


# =============================================================================
# Numeric Verification Fix
# =============================================================================

NUMERIC_FIX_PROMPT = """Some numbers in this text are not supported by the evidence. Please revise.

Original text:
{text}

Unsupported numbers that must be removed or qualified:
{unsupported_numbers}

Evidence passages available:
{evidence_passages}

INSTRUCTIONS:
1. Remove sentences containing unsupported numbers, OR
2. Add qualifiers like "reportedly", "estimated", "approximately" if the number seems reasonable
3. Keep all supported facts and citations intact
4. Maintain the overall structure and flow

Output ONLY the revised text (no explanation):"""


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
            snippet = item.snippet[:200] if item.snippet else ""
            lines.append(f"  {snippet}...")
    return "\n".join(lines)


def format_gathered_info_for_synthesis(gathered_info: list) -> str:
    """
    Format gathered information into a string for the synthesis prompt.
    (Legacy format - use format_evidence_pack for new evidence-based synthesis)
    
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


def format_evidence_pack(evidence_pack) -> str:
    """
    Format an EvidencePack for use in the synthesis prompt.
    
    Args:
        evidence_pack: EvidencePack object with sources and passages
        
    Returns:
        Formatted string with source IDs and passages
    """
    if hasattr(evidence_pack, 'format_for_prompt'):
        return evidence_pack.format_for_prompt()
    
    # Fallback for dict-like evidence
    lines = []
    sources = evidence_pack.get('sources', []) if isinstance(evidence_pack, dict) else []
    passages = evidence_pack.get('passages', []) if isinstance(evidence_pack, dict) else []
    
    for source in sources:
        source_id = source.get('source_id', 'S?')
        title = source.get('title', 'Unknown')
        url = source.get('url', '')
        score = source.get('source_score', 0.0)
        
        lines.append(f"[{source_id}] {title} — {url} — (score={score:.2f})")
        
        # Add passages for this source
        for passage in passages:
            if passage.get('source_id') == source_id:
                passage_id = passage.get('passage_id', 'P?')
                text = passage.get('text', '')[:500]
                if len(passage.get('text', '')) > 500:
                    text += "..."
                lines.append(f"  ({passage_id}) {text}")
        
        lines.append("")
    
    return "\n".join(lines)


def format_answer_spec(answer_spec: List[str]) -> str:
    """
    Format answer specification as a bulleted list.
    
    Args:
        answer_spec: List of items that must be answered
        
    Returns:
        Formatted bulleted list
    """
    if not answer_spec:
        return "- Answer the research question comprehensively"
    return "\n".join(f"- {item}" for item in answer_spec)


def format_evidence_summary(sources: list, passages: list) -> str:
    """
    Format a brief summary of evidence for evaluation.
    
    Args:
        sources: List of EvidenceSource objects or dicts
        passages: List of EvidencePassage objects or dicts
        
    Returns:
        Formatted summary string
    """
    lines = []
    
    for source in sources:
        if hasattr(source, 'source_id'):
            source_id = source.source_id
            title = source.title
            domain = source.domain
            score = source.source_score
        else:
            source_id = source.get('source_id', 'S?')
            title = source.get('title', 'Unknown')
            domain = source.get('domain', '')
            score = source.get('source_score', 0.0)
        
        lines.append(f"[{source_id}] {title} ({domain}) - score: {score:.2f}")
        
        # Count passages for this source
        source_passages = [p for p in passages 
                         if (p.source_id if hasattr(p, 'source_id') else p.get('source_id')) == source_id]
        if source_passages:
            # Show first passage preview
            first_passage = source_passages[0]
            text = first_passage.text if hasattr(first_passage, 'text') else first_passage.get('text', '')
            preview = text[:150] + "..." if len(text) > 150 else text
            lines.append(f"  Preview: {preview}")
            if len(source_passages) > 1:
                lines.append(f"  ({len(source_passages)} passages total)")
    
    return "\n".join(lines)


def format_unsupported_numbers(unsupported: list) -> str:
    """
    Format unsupported numbers for the fix prompt.
    
    Args:
        unsupported: List of ExtractedNumber or dict objects
        
    Returns:
        Formatted list of unsupported numbers
    """
    lines = []
    for item in unsupported:
        if hasattr(item, 'value'):
            value = item.value
            context = item.context
        else:
            value = item.get('value', '')
            context = item.get('context', '')
        
        lines.append(f"- {value}")
        if context:
            lines.append(f"  Context: ...{context}...")
    
    return "\n".join(lines)
