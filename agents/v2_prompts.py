"""
V2 Relational Competitive Intelligence Engine - Prompt templates.

Prompts for:
1. Gather: fact extraction from evidence (structured JSON, no prose)
2. Normalize: common schema + gap identification per parameter
3. Synthesize: draft comparative report
4. Synthesize: self-evaluate draft and optionally request re-gather
5. Executive: landscape brief from all parameter summaries
"""

# =============================================================================
# Phase 1: Gather - Fact Extraction
# =============================================================================

GATHER_FACT_EXTRACTION_SYSTEM = """You are a competitive intelligence analyst. Your task is to extract structured facts from evidence passages. Output ONLY valid JSON. Do not write prose or explanations. Every fact must cite a source_id from the evidence."""

GATHER_FACT_EXTRACTION_PROMPT = """Extract structured facts about {company} for the research dimension: {parameter_name}.
{parameter_context_line}
Research goal: {research_prompt}

Evidence (source IDs like [S1], [S2] appear in the passages):
{evidence_text}

INSTRUCTIONS:
1. Extract 5-15 discrete factual claims that answer the research goal.
2. For each fact, note which source_id (e.g. S1, S2) it comes from.
3. If the parameter has measurable metrics (prices, percentages, counts), extract them as key_metrics.
4. Set confidence to "high" only when the fact is directly stated in a passage; "medium" when inferred; "low" when uncertain.

Output your response as JSON inside <fact_extraction_json> tags:

<fact_extraction_json>
{{
  "facts": [
    {{"claim": "Exact factual claim from evidence", "source_id": "S1", "confidence": "high"}},
    {{"claim": "Another claim", "source_id": "S2", "confidence": "medium"}}
  ],
  "key_metrics": {{
    "metric_name": "value",
    "another_metric": "value"
  }}
}}
</fact_extraction_json>

Rules:
- Only include facts that appear in the evidence. Do not invent data.
- key_metrics can be empty {{}} if there are no clear numeric/structured metrics.
- Use the exact source_id strings from the evidence (e.g. S1, S2, S3).

Your extraction:"""


# =============================================================================
# Phase 2: Normalize
# =============================================================================

NORMALIZE_SYSTEM = """You are a competitive intelligence analyst. Your job is to normalize company dossiers for one parameter into a common comparison schema so that companies can be compared side-by-side. Output only valid JSON."""

NORMALIZE_PROMPT = """Normalize the following company dossiers for the parameter: {parameter_name}.
{parameter_context_line}
Parameter context: {research_prompt}

Dossiers (one per company):
{dossiers_text}

INSTRUCTIONS:
1. Identify 4-10 schema_fields that allow fair comparison across all companies (e.g. base_rate, enterprise_pricing, free_tier, key_differentiator).
2. For each company, map their facts and key_metrics into these schema_fields. Use "N/A" or "Unknown" where data is missing.
3. List data_gaps: for each company/field where information is missing or weak, add an entry with company, field_or_topic, and a short description.

Output your response as JSON inside <normalize_json> tags:

<normalize_json>
{{
  "schema_fields": ["field1", "field2", "field3"],
  "company_data": {{
    "Company A": {{"field1": "value", "field2": "value"}},
    "Company B": {{"field1": "value", "field2": "N/A"}}
  }},
  "data_gaps": [
    {{"company": "Company B", "field_or_topic": "field2", "description": "No public data on enterprise pricing"}}
  ]
}}
</normalize_json>

Rules:
- Every company in the dossiers must appear in company_data.
- Every schema_field must have a value (or N/A) for each company.
- data_gaps should list only meaningful gaps that would improve the comparison if filled.

Your normalization:"""


# =============================================================================
# Phase 3: Synthesize - Draft Report
# =============================================================================

SYNTHESIS_DRAFT_SYSTEM = """You are a senior competitive intelligence analyst. Your task is to write a comparative "State of the Nation" report that compares multiple companies on one dimension. You must compare companies AGAINST each other, declare winners and losers, identify trends and white space. Be specific and evidence-based. Cite source IDs when referencing facts."""

SYNTHESIS_DRAFT_PROMPT = """Write a comparative analysis report for the parameter: {parameter_name}.
{parameter_context_line}
Parameter context: {research_prompt}

Companies being compared: {companies_list}

Normalized comparison data:
{normalized_data}

Additional context from dossiers (source IDs and passages):
{dossiers_context}

INSTRUCTIONS:
1. Write a headline (1-2 sentences) that captures the main competitive verdict.
2. Write an executive_summary (2-3 sentences).
3. Produce rankings: an ordered list of companies (best to worst or leader to laggard) with a short label and one-line rationale for each.
4. Build a positioning_table: list of objects, one per company, with keys for each schema field plus "position" (e.g. "Premium", "Value Leader") and "trend" if evident.
5. Write full_report_markdown: a 1000-2000 word narrative that compares all players, identifies leaders/laggards, trends, outliers, and white space. Use [S1], [S2] citations.
6. List white_space: 2-5 unoccupied strategic opportunities or underserved segments.
7. List trends: 2-5 directional observations (e.g. "Race to zero on base fees").
8. Set confidence: "high", "medium", or "low" based on evidence strength.

Output your response as JSON inside <synthesis_json> tags:

<synthesis_json>
{{
  "headline": "One or two sentence verdict.",
  "executive_summary": "Two to three sentence summary.",
  "rankings": [
    {{"rank": 1, "company": "Company A", "label": "Leader", "rationale": "..."}},
    {{"rank": 2, "company": "Company B", "label": "Challenger", "rationale": "..."}}
  ],
  "positioning_table": [
    {{"company": "Company A", "position": "Premium", "field1": "value", "field2": "value", "trend": "Stable"}}
  ],
  "full_report_markdown": "Full narrative with citations...",
  "white_space": ["Opportunity 1", "Opportunity 2"],
  "trends": ["Trend 1", "Trend 2"],
  "confidence": "high"
}}
</synthesis_json>

Your report:"""


# =============================================================================
# Phase 3: Synthesize - Self-Evaluate (decide if re-gather needed)
# =============================================================================

SYNTHESIS_EVALUATE_SYSTEM = """You are a quality assurance analyst for competitive intelligence. Your job is to evaluate whether a draft comparative report has sufficient evidence to support its claims. If critical gaps exist, specify targeted re-gather requests (which company, what specific information to search for)."""

SYNTHESIS_EVALUATE_PROMPT = """Evaluate this draft comparative report for the parameter: {parameter_name}.

Draft report (excerpts):
- Headline: {headline}
- Executive summary: {executive_summary}
- Rankings: {rankings_text}
- Key claims in full report: {full_report_excerpt}

Normalized data available:
{normalized_data}

Data gaps that were already identified:
{gaps_text}

INSTRUCTIONS:
1. Decide if the report is sufficient: can we stand behind the rankings and key comparative claims with the evidence we have?
2. If yes, set is_sufficient to true and leave requested_gathers empty.
3. If no, set is_sufficient to false and list 1-5 targeted re-gather requests. Each request should specify:
   - company: which company
   - query: a specific Google-style search query to find the missing information
   - rationale: why this is needed for the comparison

Output your response as JSON inside <evaluate_json> tags:

<evaluate_json>
{{
  "is_sufficient": true,
  "confidence": "high",
  "reasoning": "One sentence explanation.",
  "requested_gathers": [
    {{"company": "Company B", "query": "Company B enterprise pricing 2024", "rationale": "Need enterprise rate to compare with others"}}
  ]
}}
</evaluate_json>

Rules:
- requested_gathers should be empty if is_sufficient is true.
- Each query in requested_gathers should be a concrete search query (under 80 chars), not a vague topic.
- Maximum 5 requested_gathers per evaluation.

Your evaluation:"""


# =============================================================================
# Phase 4: Executive Brief
# =============================================================================

EXECUTIVE_BRIEF_SYSTEM = """You are a strategy advisor summarizing a competitive landscape for the C-Suite. Your job is to distill multiple parameter-level reports into one compelling executive brief with cross-cutting themes, trends, white-space analysis (from two independent lenses), and actionable next steps. Be concise, specific, and actionable."""

EXECUTIVE_BRIEF_PROMPT = """Synthesize an executive brief from the following parameter-level competitive analyses.

Companies in scope: {companies_list}

Parameter reports (headline + executive summary + top rankings + trends + white space per parameter):
{parameter_summaries}
{venture_context_block}
INSTRUCTIONS:
Produce ALL of the following sections:

1. **brief**: A single paragraph (4-8 sentences) that a busy executive can read in 30 seconds. It should answer: What is the overall competitive landscape? Who leads where? What are the biggest strategic takeaways?

2. **key_themes**: 3-6 cross-cutting strategic themes that span multiple parameters (e.g. "Platform convergence", "Race to transparency in pricing").

3. **trends**: 3-7 cross-cutting DIRECTIONAL SHIFTS — not what IS true today, but what is CHANGING and WHERE things are headed. Synthesize from the parameter-level trends into landscape-level shifts. Each trend should describe a direction of movement (e.g. "Loyalty programs are evolving from flight rewards into full financial ecosystems").

4. **white_space_opportunities**: 3-7 structured strategic opportunities. For EACH opportunity provide:
   - "opportunity": What is the unoccupied position or underserved gap?
   - "why_it_exists": What structural dynamics create this opening?
   - "who_is_closest": Which existing player is best positioned to capture it?
   - "entry_difficulty": "Low", "Medium", or "High"
   {venture_ws_instruction}

5. **white_space_matrix**: Organize ALL identified white spaces into a category matrix with these exact keys:
   - "segment_gaps": Customer segments nobody serves well
   - "product_gaps": Capabilities or features nobody offers
   - "business_model_gaps": Monetization approaches nobody has tried
   - "geographic_gaps": Markets or regions nobody is addressing
   Each key maps to a list of 1-5 short descriptions. This is an INDEPENDENT view from white_space_opportunities — it should categorize ALL gaps, not just restate the opportunities.
   {venture_matrix_instruction}

6. **next_steps**: Actionable recommendations organized into workstream buckets. Each bucket is a key mapping to a list of items. Each item has "action", "rationale", and "priority" ("High"/"Medium"/"Low"). Use these exact bucket keys:
   - "investigate_further": Things that need deeper research before acting
   - "quick_wins": Low-effort, high-signal actions achievable in weeks
   - "strategic_bets": Bigger moves requiring commitment but with outsized payoff
   - "monitor_and_defend": Competitive moves to watch that could disrupt positioning
   Include 1-4 items per bucket.
   {venture_ns_instruction}

Output your response as JSON inside <executive_json> tags:

<executive_json>
{{
  "brief": "Your 4-8 sentence executive paragraph...",
  "key_themes": ["Theme 1", "Theme 2"],
  "trends": ["Trend 1: directional shift description...", "Trend 2: ..."],
  "white_space_opportunities": [
    {{"opportunity": "...", "why_it_exists": "...", "who_is_closest": "...", "entry_difficulty": "Medium"}}
  ],
  "white_space_matrix": {{
    "segment_gaps": ["Gap 1", "Gap 2"],
    "product_gaps": ["Gap 1"],
    "business_model_gaps": ["Gap 1"],
    "geographic_gaps": ["Gap 1"]
  }},
  "next_steps": {{
    "investigate_further": [{{"action": "...", "rationale": "...", "priority": "High"}}],
    "quick_wins": [{{"action": "...", "rationale": "...", "priority": "High"}}],
    "strategic_bets": [{{"action": "...", "rationale": "...", "priority": "Medium"}}],
    "monitor_and_defend": [{{"action": "...", "rationale": "...", "priority": "High"}}]
  }}
}}
</executive_json>

Your executive brief:"""


# =============================================================================
# Helpers for formatting
# =============================================================================

def format_dossiers_for_normalize(dossiers_by_company: dict) -> str:
    """Format company dossiers into a string for the normalize prompt."""
    lines = []
    for company, dossier in dossiers_by_company.items():
        if hasattr(dossier, "to_dict"):
            d = dossier.to_dict()
        else:
            d = dossier
        facts_str = "\n".join(f"  - {f.get('claim', f)}" for f in d.get("facts", []))
        metrics_str = ", ".join(f"{k}: {v}" for k, v in d.get("key_metrics", {}).items()) or "None"
        lines.append(f"\n--- {company} ---\nFacts:\n{facts_str}\nKey metrics: {metrics_str}")
    return "\n".join(lines) if lines else "No dossiers provided."


def format_parameter_summaries_for_executive(reports: list) -> str:
    """Format parameter report summaries for the executive brief prompt, including trends and white space."""
    lines = []
    for r in reports:
        if hasattr(r, "to_dict"):
            d = r.to_dict()
        else:
            d = r
        name = d.get("parameter_name", d.get("parameter_id", "?"))
        headline = d.get("headline", "")
        summary = d.get("executive_summary", "")
        rankings = d.get("rankings", [])
        rank_str = ", ".join(f"{x.get('rank')}. {x.get('company')} ({x.get('label', '')})" for x in rankings[:5])
        trends = d.get("trends", [])
        trends_str = ", ".join(trends[:5]) if trends else "None identified"
        white_space = d.get("white_space", [])
        ws_str = ", ".join(white_space[:5]) if white_space else "None identified"
        lines.append(
            f"\n### {name}\nHeadline: {headline}\nSummary: {summary}\nRankings: {rank_str}"
            f"\nTrends: {trends_str}\nWhite space: {ws_str}"
        )
    return "\n".join(lines) if lines else "No reports."


def build_venture_context_block(venture_context: str) -> dict:
    """Build the venture context block and per-section instructions for the executive prompt."""
    if not venture_context or not venture_context.strip():
        return {
            "venture_context_block": "",
            "venture_ws_instruction": "",
            "venture_matrix_instruction": "",
            "venture_ns_instruction": "",
        }
    vc = venture_context.strip()
    return {
        "venture_context_block": (
            f"\n--- VENTURE CONTEXT ---\n"
            f"The user is evaluating this competitive landscape from the perspective of a specific venture:\n"
            f"{vc}\n"
            f"Use this context to personalize white space analysis and next steps. "
            f"Frame opportunities and recommendations in terms of what THIS venture should prioritize.\n"
            f"---\n"
        ),
        "venture_ws_instruction": (
            "Frame opportunities through the lens of the user's venture context above. "
            "Which gaps are most relevant to THEIR specific venture?"
        ),
        "venture_matrix_instruction": (
            "Prioritize gaps that are most relevant to the user's venture context above."
        ),
        "venture_ns_instruction": (
            "Tailor recommendations specifically to the user's venture described above. "
            "What should THEY investigate, what are THEIR quick wins, THEIR strategic bets?"
        ),
    }
