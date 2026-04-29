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
{takeaway_addendum}
INSTRUCTIONS:
1. Write a headline (1-2 sentences) that captures the main competitive verdict.
2. Write an executive_summary (2-3 sentences).
3. Produce rankings: an ordered list of companies (best to worst or leader to laggard) with a short label and one-line rationale for each.
4. Build a positioning_table: list of objects, one per company, with keys for each schema field plus "position" (e.g. "Premium", "Value Leader") and "trend" if evident.
5. Write full_report_markdown: a 1000-2000 word narrative that compares all players, identifies leaders/laggards, trends, outliers, and white space. Use [S1], [S2] citations.
6. List white_space: 2-5 unoccupied strategic opportunities or underserved segments.
7. List trends: 2-5 directional observations (e.g. "Race to zero on base fees").
8. Set confidence: "high", "medium", or "low" based on evidence strength.

Commercial Deep Dive source rules:
- Blocks labeled STRUCTURED EXTRACT are Firecrawl extracts from official pages; use them as source-of-truth for published pricing, package, and contract facts.
- Exa/search evidence is for inferred or market-observed facts such as ACV, upgrade triggers, negotiation flexibility, and customer sentiment.
- If official extract and search evidence disagree about a published fact, prefer the official extract and note the discrepancy only if material.
- Surface opacity as data, especially for consulting firms and contact-sales enterprise vendors.

Three-state pricing (epistemic posture):
- When asked for a price, ACV, deal size, contract value, or any other numeric commercial fact, you must place it in one of three states:
  * `published`: a primary or credible secondary source publishes the number. Cite the source_id.
  * `inferred`: no published number, but multiple signals (benchmarks + scope evidence) support a defensible range. State range_low, range_high, the assumptions you used, and a short methodology label.
  * `unknown`: neither published nor reliably inferable. State the reason (typology / pre-revenue / evidence gap / brand-collision).
- Do NOT collapse `inferred` into `unknown` simply because no source publishes the number. If the STRUCTURED EXTRACT contains a `consulting_benchmark` block AND you have at least two signals about scope (engagement length, team size, deal size), you must produce an `inferred` claim.
- When you produce an inferred numeric, render it inline in prose and tables with the `[inferred]` tag and the range, e.g. `Inferred $1.5M–$3M [inferred] (4-week, 4-person engagement at MBB blended day rate; medium confidence)`. A careful reader must be able to distinguish published facts from triangulated estimates.

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
  "confidence": "high",
  "quantified_recommendations": [
    {{
      "headline": "Launch a 30-day Initiative Sprint",
      "rationale": "...",
      "numeric_targets": {{
        "pilot_price_usd": {{"state": "inferred", "range_low": 50000, "range_high": 80000, "unit": "USD", "method": "5-10% of MBB engagement floor; 2-3x Glean annual contract", "confidence": "medium", "source_ids": ["S1", "S2"]}}
      }},
      "time_horizon_days": 90,
      "success_metric": "8-12 paid pilots and 40% pilot-to-annual conversion",
      "impact_likelihood": "high",
      "cost_to_implement": "medium",
      "triangulation_source_ids": ["S1", "S2", "S3"]
    }}
  ]
}}
</synthesis_json>

(quantified_recommendations is REQUIRED only for parameter_id == inv_takeaway_for_innovera; omit it otherwise.)

Your report:"""


# =============================================================================
# Takeaway addendum (injected only for parameter_id == "inv_takeaway_for_innovera")
# =============================================================================

INV_TAKEAWAY_ADDENDUM = """
TAKEAWAY-SPECIFIC RULES (this is the Takeaway for Innovera; the dimension-level rollups have already been written):

1. Do not restate the patterns the dimension layer has already named. The dimension rollups have already established:
   - Vertical depth wins (Rogo, Hebbia)
   - Trust architecture compounds (AlphaSense, FICO)
   - Accessibility steals attention (Rocket, DeeCee.ai)
   - Consulting-substitute language is crowding (NexStrat, NitroLens)
   - Big Three are slow but distribution-rich (McKinsey, BCG, EY, Deloitte)
   Your job is to surface what these patterns *jointly imply* — second-order observations a senior reader cannot get from any single dimension. Specifically: cross-pattern timing (which threats materialise when), forced tradeoffs (what Innovera must give up to win which segment), and quantified bets.

2. Every recommendation in this Takeaway must include at least one quantified target — a price band, ARR target, time horizon, target conversion rate, or impact magnitude. The report contains pricing data on at least four competitors and ACV data on at least five (e.g. Glean $50–100/user/month + $60K min ACV; Rocket $25/month entry; Aily $25K–$120K setup, $25M+ contracts; Rogo ~$420K average ACV). Use them as triangulation anchors.
   - For the Initiative Sprint specifically: land a fixed-fee pilot price band, a target pilot count over 90 days, a target pilot-to-annual conversion rate, and a 6-month revenue threshold.
   - If you cannot produce a defensible quantified target from the evidence, mark the recommendation as `qualitative_only` with a one-line reason. This must be the exception, not the default.

3. Render the recommendations as `quantified_recommendations`: an array alongside the standard fields. Each entry has headline, rationale, numeric_targets (object with at least one NumericClaim-shaped value), time_horizon_days, success_metric, impact_likelihood, cost_to_implement.
"""


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
# Phase 3.5: Research Synthesis
# =============================================================================

RESEARCH_SYNTHESIS_SYSTEM = """You are a lead research analyst. Your job is to answer the specific key questions defined in the original research plan and validate the initial hypothesis based on the gathered intelligence. You must be evidence-based, citing findings from the parameter reports."""

RESEARCH_SYNTHESIS_PROMPT = """Synthesize the research findings to answer the original key questions and validate the hypothesis.

Companies in scope: {companies_list}

Research Plan:
Hypothesis: {hypothesis}
Key Questions:
{key_questions_list}

Parameter Reports (Findings):
{parameter_summaries}

INSTRUCTIONS:
1. For each Key Question, provide a comprehensive answer (3-5 sentences) based on the findings in the parameter reports. Cite specific metrics or rankings where relevant.
2. Validate the Hypothesis: explicitly state if it was supported, partially supported, or refuted by the data. Explain why in 3-5 sentences.

Output your response as JSON inside <research_synthesis_json> tags:

<research_synthesis_json>
{{
  "key_questions_answers": [
    {{
      "question": "Original question text...",
      "answer": "Comprehensive answer based on findings..."
    }},
    ...
  ],
  "hypothesis_validation": "The hypothesis was [supported/refuted] because..."
}}
</research_synthesis_json>

Your research synthesis:"""


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
# Graveyard: Phase 3G - Failure-Lens Synthesis
# =============================================================================

GRAVEYARD_SYNTHESIS_DRAFT_SYSTEM = """You are a senior competitive intelligence analyst specializing in corporate failure analysis. Your task is to write a comparative "Post-Mortem" report examining multiple defunct companies on one failure dimension. You must identify common patterns, structural root causes, and actionable lessons for new entrants. Be specific and evidence-based. Cite source IDs when referencing facts."""

GRAVEYARD_SYNTHESIS_DRAFT_PROMPT = """Write a failure-focused comparative analysis for the parameter: {parameter_name}.
{parameter_context_line}
Parameter context: {research_prompt}

Defunct companies being analyzed: {companies_list}

Normalized comparison data:
{normalized_data}

Additional context from dossiers (source IDs and passages):
{dossiers_context}

INSTRUCTIONS:
1. Write a headline (1-2 sentences) that captures the dominant failure pattern across these companies.
2. Write an executive_summary (2-3 sentences) explaining what this dimension reveals about why companies in this space fail.
3. Produce rankings: order companies from most instructive failure to least, with a label (e.g. "Cautionary Example", "Partial Failure") and a one-line rationale for each.
4. Build a positioning_table: list of objects, one per company, with keys for each schema field plus "failure_mode" (e.g. "Financial Collapse", "Competitive Displacement") and "time_to_collapse" if evident.
5. Write full_report_markdown: a 800-1500 word narrative that compares all companies' failures on this dimension, identifies patterns, root causes, and lessons. Use [S1], [S2] citations.
6. List failure_patterns: 2-5 recurring failure modes or structural weaknesses visible across these companies.
7. List lessons: 2-5 actionable takeaways a new entrant should internalize.
8. Set confidence: "high", "medium", or "low" based on evidence strength.

Output your response as JSON inside <synthesis_json> tags:

<synthesis_json>
{{
  "headline": "One or two sentence failure pattern verdict.",
  "executive_summary": "Two to three sentence summary.",
  "rankings": [
    {{"rank": 1, "company": "Company A", "label": "Most Instructive", "rationale": "..."}},
    {{"rank": 2, "company": "Company B", "label": "Cautionary Example", "rationale": "..."}}
  ],
  "positioning_table": [
    {{"company": "Company A", "failure_mode": "Financial Collapse", "field1": "value", "field2": "value", "time_to_collapse": "3 years"}}
  ],
  "full_report_markdown": "Full narrative with citations...",
  "white_space": ["Failure pattern 1", "Failure pattern 2"],
  "trends": ["Lesson 1", "Lesson 2"],
  "confidence": "high"
}}
</synthesis_json>

Note: Use "white_space" for failure_patterns and "trends" for lessons to maintain schema compatibility.

Your report:"""


# =============================================================================
# Graveyard: Phase 4G - Post-Mortem Brief
# =============================================================================

POSTMORTEM_BRIEF_SYSTEM = """You are a strategy advisor distilling failure intelligence for C-Suite consumption. Your job is to synthesize parameter-level failure reports from defunct companies into a compelling cautionary brief with failure patterns, structural vulnerabilities, per-company narratives, and survival principles for new entrants. Be concise, specific, and actionable."""

POSTMORTEM_BRIEF_PROMPT = """Synthesize a post-mortem intelligence brief from the following failure analyses of defunct companies.

Defunct companies analyzed: {companies_list}
Living competitors in scope: {living_companies_list}
Industry context: {industry_context}

Parameter reports (headline + executive summary + failure patterns + lessons per parameter):
{parameter_summaries}
{venture_context_block}
INSTRUCTIONS:
Produce ALL of the following sections:

1. **failure_patterns**: 3-6 recurring failure modes that appear across multiple defunct companies and parameters. Each should be a substantive sentence (e.g. "Over-expansion into premium segments without sufficient load factor guarantees led to fatal cash flow spirals").

2. **structural_vulnerabilities**: 3-5 industry-level structural risks that the failures expose. These are not company-specific but reveal fragilities in the market itself (e.g. "The airline industry's high fixed-cost structure means even small revenue shortfalls cascade into insolvency within 18-24 months").

3. **cautionary_narratives**: One mini-narrative per defunct company. For EACH, provide:
   - "company": Company name
   - "peak_position": What they were at their peak (1-2 sentences)
   - "failure_mode": Primary category of failure
   - "narrative": 3-5 sentence story of rise and fall
   - "key_lesson": One-line takeaway

4. **survival_principles**: 4-7 distilled rules-of-thumb for avoiding the same fate. Frame as affirmative guidance (e.g. "Maintain 6+ months of operating reserves before expanding into new routes" not "Don't run out of money").

Output your response as JSON inside <postmortem_json> tags:

<postmortem_json>
{{
  "failure_patterns": ["Pattern 1", "Pattern 2"],
  "structural_vulnerabilities": ["Vulnerability 1", "Vulnerability 2"],
  "cautionary_narratives": [
    {{
      "company": "Company A",
      "peak_position": "Was the largest X in Y...",
      "failure_mode": "Financial Collapse",
      "narrative": "Founded in 19XX, Company A grew to...",
      "key_lesson": "One-line takeaway."
    }}
  ],
  "survival_principles": ["Principle 1", "Principle 2"]
}}
</postmortem_json>

Your post-mortem brief:"""


# =============================================================================
# Phase 5: Risk Overlay Merge
# =============================================================================

RISK_OVERLAY_SYSTEM = """You are a risk analyst. Your job is to cross-reference white-space opportunities identified in a competitive analysis with failure patterns from defunct companies in the same space. For each opportunity, identify whether historical failures suggest heightened risk and provide mitigation guidance."""

RISK_OVERLAY_PROMPT = """Cross-reference these white-space opportunities with the post-mortem failure intelligence to produce risk overlays.

White-space opportunities from the main competitive analysis:
{white_space_opportunities}

Failure patterns from defunct companies:
{failure_patterns}

Structural vulnerabilities:
{structural_vulnerabilities}

Cautionary narratives (summaries):
{cautionary_summaries}

INSTRUCTIONS:
For EACH white-space opportunity, determine if any historical failure pattern is relevant. Produce a risk overlay with:
- "white_space_opportunity": The opportunity text (verbatim from input)
- "historical_precedent": Which defunct company/failure pattern is relevant and why (2-3 sentences). If no precedent exists, say "No direct historical precedent identified."
- "risk_level": "High", "Medium", or "Low" based on how closely a past failure maps to this opportunity
- "mitigation_guidance": Actionable advice to avoid the historical pitfall (1-2 sentences)

Output your response as JSON inside <risk_overlay_json> tags:

<risk_overlay_json>
{{
  "risk_overlays": [
    {{
      "white_space_opportunity": "The exact opportunity text...",
      "historical_precedent": "Pan Am attempted a similar strategy in 1980...",
      "risk_level": "High",
      "mitigation_guidance": "Ensure minimum 70% load factor commitment before..."
    }}
  ]
}}
</risk_overlay_json>

Your risk overlays:"""


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


def format_graveyard_summaries_for_postmortem(reports: list) -> str:
    """Format graveyard parameter reports for the post-mortem brief prompt."""
    lines = []
    for r in reports:
        if hasattr(r, "to_dict"):
            d = r.to_dict()
        else:
            d = r
        name = d.get("parameter_name", d.get("parameter_id", "?"))
        headline = d.get("headline", "")
        summary = d.get("executive_summary", "")
        # white_space holds failure_patterns, trends holds lessons (schema reuse)
        failure_patterns = d.get("white_space", [])
        lessons = d.get("trends", [])
        fp_str = ", ".join(failure_patterns[:5]) if failure_patterns else "None identified"
        lessons_str = ", ".join(lessons[:5]) if lessons else "None identified"
        lines.append(
            f"\n### {name}\nHeadline: {headline}\nSummary: {summary}"
            f"\nFailure patterns: {fp_str}\nLessons: {lessons_str}"
        )
    return "\n".join(lines) if lines else "No reports."


# =============================================================================
# AVIS Path: Executive Brief with AVIS Analytical Frameworks
# =============================================================================

AVIS_EXECUTIVE_BRIEF_SYSTEM = """You are a senior VC partner synthesizing a competitive landscape analysis using the AVIS framework (Innovera, Chapter 4: Competitive Analysis). Your output must include the standard executive brief PLUS three AVIS-specific analytical frameworks: a Moat Analysis Grid, a Threat Matrix, and a Feature & Value Curve assessment. Be concise, specific, and actionable. Frame everything through the lens of: can a new venture win here?"""

AVIS_EXECUTIVE_BRIEF_PROMPT = """Synthesize an AVIS executive brief from the following parameter-level competitive analyses.

Companies in scope: {companies_list}

Parameter reports (headline + executive summary + top rankings + trends + white space per parameter):
{parameter_summaries}
{venture_context_block}
INSTRUCTIONS:
Produce ALL of the following sections. The first 6 sections follow the standard format; sections 7-9 are AVIS-specific analytical frameworks.

1. **brief**: A single paragraph (4-8 sentences) answering: What is the overall competitive landscape? Who leads where? Is there room for a new entrant? What are the structural dynamics?

2. **key_themes**: 3-6 cross-cutting strategic themes spanning multiple AVIS dimensions.

3. **trends**: 3-7 directional shifts — what is CHANGING and WHERE things are headed.

4. **white_space_opportunities**: 3-7 structured opportunities. For EACH:
   - "opportunity": The unoccupied position or underserved gap
   - "why_it_exists": Structural dynamics creating this opening
   - "who_is_closest": Which existing player is best positioned
   - "entry_difficulty": "Low", "Medium", or "High"
   {venture_ws_instruction}

5. **white_space_matrix**: Categorize ALL gaps:
   - "segment_gaps": Customer segments nobody serves well
   - "product_gaps": Capabilities nobody offers
   - "business_model_gaps": Monetization approaches nobody has tried
   - "geographic_gaps": Markets nobody addresses
   {venture_matrix_instruction}

6. **next_steps**: Actionable recommendations in workstream buckets:
   - "investigate_further": Things needing deeper research
   - "quick_wins": Low-effort, high-signal actions
   - "strategic_bets": Bigger moves with outsized payoff
   - "monitor_and_defend": Competitive moves to watch
   Each item: {{"action": "...", "rationale": "...", "priority": "High"/"Medium"/"Low"}}
   {venture_ns_instruction}

7. **moat_analysis_grid**: For EACH company, assess defensibility sources. Array of objects:
   - "company": Company name
   - "moat_sources": Object mapping moat type to assessment:
     - "brand": "Strong" / "Moderate" / "Weak" / "None" + one-line explanation
     - "data": same format
     - "switching_costs": same format
     - "ip_patents": same format
     - "network_effects": same format
     - "regulatory": same format
     - "scale_economies": same format
   - "overall_durability": "High" / "Medium" / "Low"
   - "durability_rationale": One sentence on whether this moat will hold over 3-5 years

8. **threat_matrix**: Head-to-head risk assessment. Array of objects, one per company:
   - "company": Company name
   - "beats_others_on": List of dimensions where this company wins (e.g. ["pricing", "brand trust"])
   - "loses_to_others_on": List of dimensions where competitors win
   - "biggest_threat_from": Which specific competitor is the biggest threat and why (one sentence)
   - "stealth_threats": Any emerging or non-obvious threats (one sentence, or "None identified")

9. **value_curve_assessment**: Feature/value curve comparison. Object with:
   - "dimensions": List of 6-10 comparison dimensions most relevant to this space (e.g. "Price competitiveness", "Enterprise readiness", "UX quality")
   - "company_scores": Object mapping company name to object mapping dimension to score (1-5, where 5 is leader)
   - "parity_zones": List of dimensions where most competitors cluster (low differentiation)
   - "differentiation_zones": List of dimensions where companies diverge significantly
   - "white_space_dimensions": Dimensions where NO company scores above 3 (unserved needs)

Output your response as JSON inside <executive_json> tags:

<executive_json>
{{
  "brief": "...",
  "key_themes": ["..."],
  "trends": ["..."],
  "white_space_opportunities": [...],
  "white_space_matrix": {{...}},
  "next_steps": {{...}},
  "moat_analysis_grid": [
    {{
      "company": "Company A",
      "moat_sources": {{
        "brand": {{"strength": "Strong", "detail": "..."}},
        "data": {{"strength": "Moderate", "detail": "..."}},
        "switching_costs": {{"strength": "Weak", "detail": "..."}},
        "ip_patents": {{"strength": "None", "detail": "..."}},
        "network_effects": {{"strength": "Strong", "detail": "..."}},
        "regulatory": {{"strength": "None", "detail": "..."}},
        "scale_economies": {{"strength": "Moderate", "detail": "..."}}
      }},
      "overall_durability": "High",
      "durability_rationale": "..."
    }}
  ],
  "threat_matrix": [
    {{
      "company": "Company A",
      "beats_others_on": ["dimension1", "dimension2"],
      "loses_to_others_on": ["dimension3"],
      "biggest_threat_from": "Company B poses the greatest threat because...",
      "stealth_threats": "..."
    }}
  ],
  "value_curve_assessment": {{
    "dimensions": ["Price", "UX", "Enterprise readiness", "..."],
    "company_scores": {{
      "Company A": {{"Price": 3, "UX": 5, "Enterprise readiness": 4}},
      "Company B": {{"Price": 5, "UX": 3, "Enterprise readiness": 2}}
    }},
    "parity_zones": ["dimension where everyone is similar"],
    "differentiation_zones": ["dimension with high variance"],
    "white_space_dimensions": ["dimension nobody serves well"]
  }}
}}
</executive_json>

Your AVIS executive brief:"""


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
