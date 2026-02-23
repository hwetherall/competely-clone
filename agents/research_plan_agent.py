"""
Research Plan Agent: powers the 5-minute Research Plan wizard.

Uses:
- Perplexity sonar-pro-search: company validation, company suggestions (live web)
- Llama 4 Maverick: intelligence questions (chained, pre-generation steering)
- deepseek/deepseek-v3.2: clarification questions, custom parameters, confidence preview
- Claude Opus 4.6: research goal, mission statement, key questions
"""

import json
import re
import logging
import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from agents.llm_client import LLMClient, LLMError
from config import settings

logger = logging.getLogger(__name__)

# Model aliases from config
MODEL_FAST = settings.PLAN_FAST_MODEL
MODEL_INTELLIGENCE = settings.PLAN_INTELLIGENCE_MODEL
MODEL_RESEARCH = settings.PLAN_RESEARCH_MODEL
MODEL_RESEARCH_FALLBACK = settings.PLAN_RESEARCH_FALLBACK_MODEL
MODEL_REASONING = settings.PLAN_REASONING_MODEL


# =============================================================================
# Data structures (agent-level; API maps to Pydantic)
# =============================================================================

@dataclass
class CompanyProfile:
    """Verified company profile from Step 1."""
    id: str
    input_name: str
    official_name: str
    industry: str
    description: str
    headquarters: Optional[str] = None
    website: Optional[str] = None
    ambiguity_notes: Optional[str] = None
    subsidiary_notes: Optional[str] = None  # Parent vs subsidiaries/brands (e.g. Lufthansa Group vs airline)
    subsidiaries: List[str] = field(default_factory=list)  # Structured list for checkbox UI (e.g. ["Austrian Airlines", "SWISS"])
    brand_name: Optional[str] = None  # When conglomerate: main brand only (e.g. "Lufthansa German Airlines")


@dataclass
class CompanySuggestion:
    """Suggested additional company from Step 2."""
    id: str
    name: str
    category: str  # direct_competitor | adjacent_disruptor | international | dark_horse
    rationale: str
    gap_filled: str
    subsidiaries: List[str] = field(default_factory=list)  # When group; for subsidiary selector
    brand_name: Optional[str] = None  # When group; main brand only


@dataclass
class ClarificationOption:
    """One suggested answer for a clarification question."""
    id: str
    label: str
    description: Optional[str] = None


@dataclass
class ClarificationQuestion:
    """A single clarification question with options."""
    id: str
    question: str
    options: List[ClarificationOption]
    allow_free_text: bool = True
    context: Optional[str] = None
    impacts: Optional[List[str]] = None


@dataclass
class ResearchGoalResult:
    """Output of generate_goal (Step 4)."""
    mission_statement: str
    key_questions: List[str]
    hypothesis: Optional[str] = None
    perspective: str = "neutral"


@dataclass
class CompanyConfidence:
    """Per-company data availability estimate."""
    company_id: str
    company_name: str
    level: str  # high | medium | low
    reason: str


@dataclass
class ConfidencePreview:
    """Feasibility assessment for Step 6."""
    overall_level: str
    company_confidences: List[CompanyConfidence]
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class IntelligenceOption:
    """One option for an intelligence question."""
    id: str
    label: str
    description: Optional[str] = None


@dataclass
class IntelligenceQuestion:
    """A strategic intelligence question shown before content generation."""
    id: str
    question: str
    options: List[IntelligenceOption]
    allow_multiple: bool = True
    allow_free_text: bool = True
    context: Optional[str] = None
    follow_up_hint: Optional[str] = None


@dataclass
class IntelligenceAnswer:
    """A user's answer to an intelligence question."""
    question_id: str
    question_text: str
    selected_option_ids: List[str]
    selected_labels: List[str]
    free_text: Optional[str] = None


def _extract_json_block(content: str, start_tag: str = "<result>", end_tag: str = "</result>") -> dict:
    """Extract JSON from tagged block. Handles nested braces."""
    i = content.find(start_tag)
    if i != -1:
        start = i + len(start_tag)
        j = content.find(end_tag, start)
        content = content[start:j].strip() if j != -1 else content[start:].strip()
    brace_start = content.find("{")
    if brace_start == -1:
        raise ValueError("No JSON object in response")
    depth = 0
    in_string = False
    escape = False
    quote_char = None
    end = brace_start
    for pos in range(brace_start, len(content)):
        c = content[pos]
        if escape:
            escape = False
            continue
        if c == "\\" and in_string:
            escape = True
            continue
        if not in_string:
            if c in '"\'':
                in_string = True
                quote_char = c
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    end = pos + 1
                    break
        else:
            if c == quote_char:
                in_string = False
    raw = content[brace_start:end]
    raw = re.sub(r",\s*}", "}", raw)
    raw = re.sub(r",\s*]", "]", raw)
    return json.loads(raw)


# =============================================================================
# Step 1: Company Validation (Perplexity)
# =============================================================================

VALIDATE_SYSTEM = """You are a research analyst. Given a company name, search the web and return a structured profile.
Output ONLY valid JSON inside <result>...</result> with: id (snake_case from name), input_name, official_name, industry, description (1-2 sentences), headquarters (city/country or null), website (url or null), ambiguity_notes (if the name could mean multiple companies or business units, briefly note them; otherwise null), subsidiary_notes (if the name refers to a parent/holding company with distinct brands or subsidiaries—e.g. "Lufthansa" can mean Lufthansa Group (parent) or Lufthansa the airline; list key subsidiaries/brands like Austrian Airlines, SWISS; otherwise null), subsidiaries (array of strings: official names of key subsidiaries/brands when subsidiary_notes applies, e.g. ["Austrian Airlines", "SWISS", "Eurowings"]; else empty array []), brand_name (when it is a conglomerate/group, the main flagship brand only e.g. "Lufthansa German Airlines"; else null)."""


async def validate_companies(company_names: List[str]) -> tuple[List[CompanyProfile], List[ClarificationQuestion]]:
    """
    Validate and profile each company using Perplexity (live web search).
    Then generate clarification questions using deepseek/deepseek-v3.2.
    """
    if not company_names:
        return [], []

    client = LLMClient()
    profiles: List[CompanyProfile] = []
    prompt_per_company = (
        "Search the web and identify this company. Return a JSON object inside <result>...</result> with keys: "
        "id (snake_case, e.g. stripe_inc), input_name (exactly as given), official_name, industry, description (1-2 sentences), "
        "headquarters, website, ambiguity_notes (if name is ambiguous e.g. Tesla EVs vs Energy, note options; else null), "
        "subsidiary_notes (if this is or could mean a parent company with distinct brands/subsidiaries—e.g. Lufthansa Group vs Lufthansa airline, list key brands like Austrian, SWISS; else null), "
        "subsidiaries (array of full names of key subsidiaries/brands when relevant, e.g. [\"Austrian Airlines\", \"SWISS\", \"Eurowings\"]; else []), "
        "brand_name (when conglomerate: the main flagship brand only, e.g. Lufthansa German Airlines; else null)."
    )

    async def fetch_one(name: str) -> CompanyProfile:
        content = await client.complete_simple(
            prompt=f"{prompt_per_company}\n\nCompany: {name}",
            system_prompt=VALIDATE_SYSTEM,
            temperature=0.2,
            max_tokens=1024,
            model_override=MODEL_RESEARCH,
            fallback_model=MODEL_RESEARCH_FALLBACK,
        )
        try:
            data = _extract_json_block(content)
            subs = data.get("subsidiaries")
            if not isinstance(subs, list):
                subs = [s for s in (subs.split(",") if isinstance(subs, str) else []) if s.strip()]
            return CompanyProfile(
                id=data.get("id", name.lower().replace(" ", "_")[:50]),
                input_name=data.get("input_name", name),
                official_name=data.get("official_name", name),
                industry=data.get("industry", "Unknown"),
                description=data.get("description", ""),
                headquarters=data.get("headquarters"),
                website=data.get("website"),
                ambiguity_notes=data.get("ambiguity_notes"),
                subsidiary_notes=data.get("subsidiary_notes"),
                subsidiaries=[str(s).strip() for s in subs] if subs else [],
                brand_name=data.get("brand_name"),
            )
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning("Failed to parse profile for %s: %s", name, e)
            return CompanyProfile(
                id=name.lower().replace(" ", "_")[:50],
                input_name=name,
                official_name=name,
                industry="Unknown",
                description="Could not verify; please confirm.",
                ambiguity_notes="Verification failed",
                subsidiary_notes=None,
                subsidiaries=[],
                brand_name=None,
            )

    tasks = [fetch_one(n.strip()) for n in company_names if n.strip()]
    profiles = await asyncio.gather(*tasks)

    # Generate clarification questions (deepseek/deepseek-v3.2)
    clarifications = await generate_clarifications("companies", {
        "companies": [
            {
                "input_name": p.input_name,
                "official_name": p.official_name,
                "industry": p.industry,
                "ambiguity_notes": p.ambiguity_notes,
                "subsidiary_notes": p.subsidiary_notes,
                "subsidiaries": p.subsidiaries,
            }
            for p in profiles
        ],
    })
    return list(profiles), clarifications


# =============================================================================
# Step 2: Suggest Companies (Perplexity)
# =============================================================================

SUGGEST_SYSTEM = """You are a strategy consultant. Given a set of validated competitor companies, suggest 3-7 additional companies that would make a competitive analysis more robust. Use web search to find real companies. Categories: direct_competitor, adjacent_disruptor, international, dark_horse. Output ONLY valid JSON inside <result>...</result>."""


async def suggest_companies(
    company_profiles: List[Dict[str, Any]],
    intelligence_answers: Optional[List[Dict[str, Any]]] = None,
) -> tuple[List[CompanySuggestion], List[ClarificationQuestion]]:
    """Suggest additional companies and generate clarification questions.
    
    If intelligence_answers are provided (from the intelligence questions phase),
    they are woven into the prompt to steer which types of competitors are suggested.
    """
    client = LLMClient()
    names = [p.get("official_name", p.get("name", "")) for p in company_profiles]
    industry = company_profiles[0].get("industry", "Unknown") if company_profiles else "Unknown"

    preferences_section = ""
    if intelligence_answers:
        pref_lines = []
        for a in intelligence_answers:
            labels = a.get("selected_labels", [])
            text = a.get("free_text", "")
            q_text = a.get("question_text", a.get("question_id", ""))
            answer_str = ", ".join(labels)
            if text:
                answer_str += f" ({text})" if answer_str else text
            if answer_str:
                pref_lines.append(f"- {q_text}: {answer_str}")
        if pref_lines:
            preferences_section = (
                "\n\nUser preferences from intelligence questions:\n"
                + "\n".join(pref_lines)
                + "\n\nIMPORTANT: Prioritize suggestions that match these preferences. "
                "If the user specified geographic preferences, ensure at least 60% of suggestions "
                "are from those regions. If they specified business model preferences, weight toward "
                "companies with those models. Tailor your suggestions to directly address what the user asked for."
            )

    user_prompt = f"""Set of competitors (already validated): {", ".join(names)}. Industry context: {industry}.{preferences_section}
Search the web and suggest 3-7 additional companies that would strengthen a competitive analysis. For each suggest:
- id (snake_case)
- name
- category (one of: direct_competitor, adjacent_disruptor, international, dark_horse)
- rationale (one sentence why add them)
- gap_filled (what gap this fills)

Output a single JSON object inside <result>...</result> with key "suggestions" (array of objects with id, name, category, rationale, gap_filled)."""

    content = await client.complete_simple(
        prompt=user_prompt,
        system_prompt=SUGGEST_SYSTEM,
        temperature=0.4,
        max_tokens=2048,
        model_override=MODEL_RESEARCH,
        fallback_model=MODEL_RESEARCH_FALLBACK,
    )
    suggestions: List[CompanySuggestion] = []
    try:
        data = _extract_json_block(content)
        for s in data.get("suggestions", [])[:7]:
            suggestions.append(CompanySuggestion(
                id=s.get("id", s.get("name", "").lower().replace(" ", "_")),
                name=s.get("name", ""),
                category=s.get("category", "direct_competitor"),
                rationale=s.get("rationale", ""),
                gap_filled=s.get("gap_filled", ""),
                subsidiaries=[],
                brand_name=None,
            ))
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.warning("Failed to parse suggestions: %s", e)

    # Enrich with subsidiary/brand data so Step 2 can offer brand/group/subsidiaries like Step 1
    if suggestions:
        try:
            suggestion_names = [s.name for s in suggestions]
            profiles, _ = await validate_companies(suggestion_names)
            enriched = []
            for i, s in enumerate(suggestions):
                p = profiles[i] if i < len(profiles) else None
                enriched.append(CompanySuggestion(
                    id=s.id,
                    name=s.name,
                    category=s.category,
                    rationale=s.rationale,
                    gap_filled=s.gap_filled,
                    subsidiaries=list(p.subsidiaries) if p else [],
                    brand_name=p.brand_name if p else None,
                ))
            suggestions = enriched
        except Exception as e:
            logger.warning("Could not enrich suggestions with subsidiary data: %s", e)

    clarifications = await generate_clarifications("suggestions", {
        "current_companies": names,
        "suggestions": [{"name": s.name, "category": s.category} for s in suggestions],
    })
    return suggestions, clarifications


# =============================================================================
# Clarification questions (deepseek/deepseek-v3.2)
# =============================================================================

CLARIFY_SYSTEM = """You generate 1-3 short clarification questions for a research plan wizard step. Each question has 2-4 suggested answer options. Always include an "Other" option so the user can type a custom answer. Also, ALWAYS include one option that represents the "status quo" or "default" choice (e.g. "No specific preference", "Keep broad", "Standard analysis"). Output ONLY valid JSON inside <result>...</result>. If no clarification is needed, output {"questions": []}."""


async def generate_clarifications(step: str, context: Dict[str, Any]) -> List[ClarificationQuestion]:
    """Generate clarification questions for a given step and context."""
    client = LLMClient()
    step_instructions = {
        "companies": "Focus on disambiguation (e.g. which business unit or geography) and scope. When any company has subsidiary_notes (parent vs brands/subsidiaries, e.g. Lufthansa Group vs Lufthansa airline vs Austrian/SWISS), you MUST include one clarification question so the user can choose: analyze the parent/holding only, specific subsidiaries/brands only, or both. Offer options like 'Parent/holding company only', 'Specific brands or subsidiaries (please specify)', 'Both group and key brands', and a default (e.g. 'No preference / keep as is'). Reference company names from the context.",
        "suggestions": "Ask about geography relevance, company size, or adjacent verticals. Reference the suggested companies.",
        "parameters": "Ask about B2B vs B2C weighting, regulatory focus, or pricing. Reference the parameter set.",
        "goal": "Ask about strategic intent: new entrant vs incumbent, financial vs product focus, or specific decisions this research should inform.",
    }
    instruction = step_instructions.get(step, "Ask 1-3 clarifying questions with 2-4 option buttons each, plus an Other option. Ensure one option is a 'status quo' or default choice.")

    user_prompt = f"""Step: {step}. Context (JSON): {json.dumps(context, default=str)[:3000]}
Generate 1-3 clarification questions. {instruction}
Output JSON inside <result>...</result> with key "questions": array of {{ "id": "unique_id", "question": "text", "options": [{{ "id": "opt_id", "label": "short label", "description": "optional" }}], "context": "optional why this matters" }}. Use short ids like disambig_tesla, scope_geo. For the companies step, you MUST use option id "subsidiaries_only" for the option meaning "Specific brands or subsidiaries" (exactly that id). Ensure one option is the default/status quo. If no questions needed, use "questions": []."""

    content = await client.complete_simple(
        prompt=user_prompt,
        system_prompt=CLARIFY_SYSTEM,
        temperature=0.3,
        max_tokens=1024,
        model_override=MODEL_FAST,
    )
    questions: List[ClarificationQuestion] = []
    try:
        data = _extract_json_block(content)
        for q in data.get("questions", [])[:3]:
            options = [
                ClarificationOption(
                    id=o.get("id", str(i)),
                    label=o.get("label", ""),
                    description=o.get("description"),
                )
                for i, o in enumerate(q.get("options", []))
            ]
            # Normalize option id for "Specific brands or subsidiaries" so frontend can open subsidiary modal
            if step == "companies":
                for i, o in enumerate(options):
                    if o.id == "subsidiaries_only" or (o.label and "specific brands" in o.label.lower()) or (o.label and "subsidiaries" in o.label.lower() and "both" not in o.label.lower()):
                        options[i] = ClarificationOption(id="subsidiaries_only", label=o.label, description=o.description)
                        break
            if not any(o.label.lower() == "other" for o in options):
                options.append(ClarificationOption(id="other", label="Other...", description=None))
            questions.append(ClarificationQuestion(
                id=q.get("id", f"q_{len(questions)}"),
                question=q.get("question", ""),
                options=options,
                allow_free_text=True,
                context=q.get("context"),
                impacts=q.get("impacts"),
            ))
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.warning("Failed to parse clarification questions: %s", e)
    return questions


# =============================================================================
# Intelligence Questions (Llama 4 Maverick)
# =============================================================================

INTELLIGENCE_SYSTEM = """You are a sharp associate at BCG. Your client has given you a set of companies and asked for a competitive analysis. Before diving in, you ask the ONE question that will most improve your output — like a consultant who respects the client's time but knows that a single well-placed question is worth ten pages of unfocused research.

PRINCIPLES:
- The companies the user entered ARE the strongest signal of their intent. Never ask them to confirm what is already obvious (e.g. "what industry is this?" when they entered four payment companies).
- Ask exactly 1 question per step. Not zero (you need direction), not three (you're wasting their time). The rare exception is 0 questions when the step instructions say to skip, or 2 when the step instructions say there's genuine ambiguity.
- Your question should be the one that, if answered differently, would produce a meaningfully different output. If every answer leads to roughly the same result, don't ask.
- Frame questions as a strategist would: direct, concrete, with options that represent real strategic forks.

Each question must have 3-5 concrete options grounded in the specific companies and industry. Output ONLY valid JSON inside <result>...</result>."""

INTELLIGENCE_STEP_INSTRUCTIONS = {
    "suggestions": (
        "The user has entered companies and we need to suggest additional ones to round out the set. "
        "Think of it this way: the client said 'Analyze these companies, and any others you think "
        "are appropriate.' Your job is to ask the ONE question that defines what 'appropriate' means.\n\n"
        "Generate exactly 1 question. The question should present 3-5 options that represent "
        "genuinely different directions for expanding the competitive set. Each option should lead "
        "to a meaningfully different list of suggested companies.\n\n"
        "Good framing patterns (adapt to the specific companies/industry):\n"
        "- 'When we expand the set beyond [companies], what direction matters most?'\n"
        "- 'What type of additional competitors would be most valuable for this analysis?'\n\n"
        "The options should be specific to the industry, not generic. For example:\n"
        "- For payment companies: 'Emerging BNPL/embedded finance players', 'International payment "
        "networks (Asia, LatAm)', 'Vertical-specific processors (healthcare, B2B)', 'Infrastructure "
        "layer (banking-as-a-service, card networks)'\n"
        "- For airlines: 'Low-cost carriers', 'Gulf/Asian premium carriers', 'Regional/domestic players', "
        "'Adjacent (rail, charter)'\n\n"
        "NEVER ask:\n"
        "- What industry these companies are in (obvious from the set)\n"
        "- Which features to compare (irrelevant to which companies to suggest)\n"
        "- Geographic questions as a separate question (fold geography into the main options if relevant)"
    ),
    "parameters": (
        "The user is about to select research parameters/dimensions. The system will automatically "
        "generate industry-specific parameters, so the defaults are already solid.\n\n"
        "Generate exactly 1 question about the STRATEGIC LENS for the analysis — not specific "
        "parameter categories (those are too granular), but the high-level perspective that shapes "
        "what matters. Think: what kind of comparison is this?\n\n"
        "This question MUST have allow_multiple: true — users will often want 2-3 lenses combined.\n\n"
        "Good framing: 'How should we frame this comparison?' or 'What lens matters most?'\n"
        "Options should be broad strategic perspectives, for example:\n"
        "- Product and technology (how their offerings work and differ)\n"
        "- Financial and business model mechanics (how they make money, unit economics, scale)\n"
        "- Market positioning and competitive dynamics (who's winning, where the gaps are)\n"
        "- Customer and go-to-market (who they sell to, how they acquire and retain)\n\n"
        "Adapt these to the specific industry but keep them at the STRATEGIC level, not the "
        "operational level. Never list specific parameter names as options."
    ),
    "goal": (
        "The user is about to define the research mission and key questions.\n\n"
        "Generate exactly 1 question about STRATEGIC INTENT — this is the single most important "
        "thing that shapes the entire research mission. The question is essentially: 'Why are you "
        "running this analysis?'\n\n"
        "Options should include forks like:\n"
        "- Evaluating whether to enter this market as a new venture\n"
        "- Benchmarking an existing position against competitors\n"
        "- Investment due diligence / thesis validation\n"
        "- M&A target screening\n"
        "- Understanding competitive dynamics for a specific decision\n\n"
        "Adapt options to be specific to the industry and companies provided."
    ),
    "audience": (
        "The user is configuring who will read this report.\n\n"
        "Return {\"questions\": []}. The system defaults to a balanced, professional analysis "
        "that works for most audiences. The audience step already has its own UI controls for "
        "selecting audience type and depth — intelligence questions here would be redundant."
    ),
}


def _parse_intelligence_questions(content: str) -> List[IntelligenceQuestion]:
    """Parse LLM response into IntelligenceQuestion objects."""
    questions: List[IntelligenceQuestion] = []
    try:
        data = _extract_json_block(content)
        for q in data.get("questions", [])[:3]:
            options = [
                IntelligenceOption(
                    id=o.get("id", f"opt_{i}"),
                    label=o.get("label", ""),
                    description=o.get("description"),
                )
                for i, o in enumerate(q.get("options", []))
            ]
            if not any(o.label.lower() == "other" for o in options):
                options.append(IntelligenceOption(id="other", label="Other", description="Type your own answer"))
            questions.append(IntelligenceQuestion(
                id=q.get("id", f"iq_{len(questions)}"),
                question=q.get("question", ""),
                options=options,
                allow_multiple=q.get("allow_multiple", True),
                allow_free_text=True,
                context=q.get("context"),
                follow_up_hint=q.get("follow_up_hint"),
            ))
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.warning("Failed to parse intelligence questions: %s", e)
    return questions


async def generate_intelligence_questions(
    step: str,
    context: Dict[str, Any],
) -> List[IntelligenceQuestion]:
    """
    Generate strategic intelligence questions for a wizard step.
    These are shown BEFORE content generation to steer what gets produced.
    """
    client = LLMClient()
    instruction = INTELLIGENCE_STEP_INSTRUCTIONS.get(step, "Generate 1-3 strategic questions with 3-5 options each.")

    companies_info = context.get("companies", [])
    if companies_info and isinstance(companies_info[0], dict):
        company_names = [c.get("official_name", c.get("name", "")) for c in companies_info]
        industry = companies_info[0].get("industry", "Unknown")
    elif companies_info and isinstance(companies_info[0], str):
        company_names = companies_info
        industry = context.get("industry_context", "Unknown")
    else:
        company_names = []
        industry = context.get("industry_context", "Unknown")

    user_prompt = f"""Step: {step}
Companies in the analysis: {", ".join(company_names)}
Industry context: {industry}
Additional context: {json.dumps({k: v for k, v in context.items() if k not in ("companies",)}, default=str)[:2000]}

{instruction}

IMPORTANT: If the companies and context make the intent clear, return {{"questions": []}}. Only ask when a question would materially change the output.

If you DO generate questions, output JSON inside <result>...</result> with key "questions": array of objects, each with:
- "id": unique snake_case id (e.g. "strategic_intent", "model_focus")
- "question": the question text (clear, concise)
- "options": array of {{"id": "opt_id", "label": "short label", "description": "optional one-line explanation"}}
- "allow_multiple": boolean (true if user can pick more than one)
- "context": optional string explaining why this question matters

Make options specific and grounded in the actual companies/industry. Do NOT use generic options."""

    content = await client.complete_simple(
        prompt=user_prompt,
        system_prompt=INTELLIGENCE_SYSTEM,
        temperature=0.3,
        max_tokens=1500,
        model_override=MODEL_INTELLIGENCE,
    )
    return _parse_intelligence_questions(content)


async def generate_intelligence_followup(
    step: str,
    question_id: str,
    selected_options: List[str],
    context: Dict[str, Any],
    previous_answers: List[Dict[str, Any]],
) -> List[IntelligenceQuestion]:
    """
    Generate follow-up intelligence questions based on a user's answer.
    For example, if user selected "Geographic competitors", follow up with "Which geographies?".
    Returns empty list if no follow-up is needed.
    """
    client = LLMClient()

    companies_info = context.get("companies", [])
    if companies_info and isinstance(companies_info[0], dict):
        company_names = [c.get("official_name", c.get("name", "")) for c in companies_info]
        industry = companies_info[0].get("industry", "Unknown")
    else:
        company_names = companies_info if isinstance(companies_info, list) else []
        industry = context.get("industry_context", "Unknown")

    prev_summary = ""
    for a in previous_answers:
        prev_summary += f"- {a.get('question_text', '?')}: {', '.join(a.get('selected_labels', []))}"
        if a.get("free_text"):
            prev_summary += f" ({a['free_text']})"
        prev_summary += "\n"

    user_prompt = f"""Step: {step}
Companies: {", ".join(company_names)}
Industry: {industry}

The user just answered question "{question_id}" by selecting: {selected_options}

Previous answers so far:
{prev_summary if prev_summary else "(none)"}

Decide whether a follow-up question is needed. In MOST cases, the answer is NO — return {{"questions": []}}.

The user's selection is almost always specific enough. Do NOT drill deeper just because you can.

Only generate a follow-up (maximum 1) if:
- The user selected "Other" and the free-text response is genuinely ambiguous
- The answer reveals a real fork that wasn't anticipated by the original question

NEVER follow up to ask for more granularity on a clear answer. Examples of when NOT to follow up:
- User selected a competitor type → clear, no follow-up needed
- User selected a geography → clear, do not ask about specific countries
- User selected a feature area → clear, do not ask about sub-features
- User selected a gap type → clear, proceed with it

Output JSON inside <result>...</result> with key "questions" (array, almost always empty).
Same format: id, question, options (with id, label, description), allow_multiple, context, follow_up_hint."""

    content = await client.complete_simple(
        prompt=user_prompt,
        system_prompt=INTELLIGENCE_SYSTEM,
        temperature=0.3,
        max_tokens=1500,
        model_override=MODEL_INTELLIGENCE,
    )
    return _parse_intelligence_questions(content)


# =============================================================================
# Step 4: Research Goal (Claude Opus)
# =============================================================================

GOAL_SYSTEM = """You are a strategy partner. Given a competitive set and research parameters, write a crisp research mission, 5-8 key questions the report must answer, and an optional testable hypothesis. Be specific to the companies and industry. Output ONLY valid JSON inside <result>...</result>."""


async def generate_goal(plan_context: Dict[str, Any]) -> tuple[ResearchGoalResult, List[ClarificationQuestion]]:
    """Generate research mission, key questions, and hypothesis."""
    client = LLMClient()
    companies = plan_context.get("companies", [])
    if isinstance(companies[0], dict):
        company_names = [c.get("official_name", c.get("name", "")) for c in companies]
    else:
        company_names = list(companies)
    industry = plan_context.get("industry_context", "Unknown")
    param_summary = plan_context.get("parameter_summary", "Various competitive dimensions")

    user_prompt = f"""Competitive set: {", ".join(company_names)}. Industry: {industry}. Parameters: {param_summary}.
Generate:
1. mission_statement: 2-3 sentences on what we're trying to learn and why.
2. key_questions: 5-8 specific questions the report MUST answer (array of strings).
3. hypothesis: One testable hypothesis the deep dive will confirm or challenge (string, or null).
4. perspective: "neutral" or a one-line venture/company perspective if provided.

Output JSON inside <result>...</result> with keys: mission_statement, key_questions, hypothesis, perspective."""

    content = await client.complete_simple(
        prompt=user_prompt,
        system_prompt=GOAL_SYSTEM,
        temperature=0.4,
        max_tokens=2048,
        model_override=MODEL_REASONING,
    )
    try:
        data = _extract_json_block(content)
        result = ResearchGoalResult(
            mission_statement=data.get("mission_statement", ""),
            key_questions=data.get("key_questions", []),
            hypothesis=data.get("hypothesis"),
            perspective=data.get("perspective", "neutral"),
        )
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.warning("Failed to parse goal: %s", e)
        result = ResearchGoalResult(
            mission_statement="Understand competitive positioning and white space among the selected companies.",
            key_questions=["Who leads on key dimensions?", "Where are the gaps?", "What are the main trends?"],
            hypothesis=None,
            perspective="neutral",
        )

    clarifications = await generate_clarifications("goal", {
        "mission_statement": result.mission_statement,
        "key_questions": result.key_questions[:3],
        "companies": company_names,
    })
    return result, clarifications


# =============================================================================
# Step 6: Confidence Preview (deepseek/deepseek-v3.2)
# =============================================================================

CONFIDENCE_SYSTEM = """You assess research feasibility. Given a plan (companies, parameters), output per-company data availability (high/medium/low), overall level, warnings, and suggestions. Output ONLY valid JSON inside <result>...</result>."""


async def generate_confidence_preview(plan: Dict[str, Any]) -> ConfidencePreview:
    """Generate feasibility assessment for the plan."""
    client = LLMClient()
    companies = plan.get("companies", [])
    if isinstance(companies[0], dict):
        company_list = [{"id": c.get("id", c.get("name", "")), "name": c.get("official_name", c.get("name", ""))} for c in companies]
    else:
        company_list = [{"id": str(i), "name": n} for i, n in enumerate(companies)]
    industry = plan.get("industry_context", "Unknown")

    user_prompt = f"""Plan: companies={[c['name'] for c in company_list]}, industry={industry}. Assess data availability for each company (public vs private, media coverage). Output JSON inside <result>...</result> with:
- overall_level: "high" | "medium" | "low"
- company_confidences: [{{ "company_id", "company_name", "level": "high"|"medium"|"low", "reason": "one sentence" }}]
- warnings: [ strings ]
- suggestions: [ strings ]"""

    content = await client.complete_simple(
        prompt=user_prompt,
        system_prompt=CONFIDENCE_SYSTEM,
        temperature=0.2,
        max_tokens=1024,
        model_override=MODEL_FAST,
    )
    try:
        data = _extract_json_block(content)
        confidences = [
            CompanyConfidence(
                company_id=c.get("company_id", ""),
                company_name=c.get("company_name", ""),
                level=c.get("level", "medium"),
                reason=c.get("reason", ""),
            )
            for c in data.get("company_confidences", [])
        ]
        if not confidences and company_list:
            confidences = [
                CompanyConfidence(c["id"], c["name"], "medium", "No specific assessment.")
                for c in company_list
            ]
        return ConfidencePreview(
            overall_level=data.get("overall_level", "medium"),
            company_confidences=confidences,
            warnings=data.get("warnings", []),
            suggestions=data.get("suggestions", []),
        )
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.warning("Failed to parse confidence preview: %s", e)
        return ConfidencePreview(
            overall_level="medium",
            company_confidences=[
                CompanyConfidence(c["id"], c["name"], "medium", "Assessment unavailable.")
                for c in company_list
            ],
            warnings=[],
            suggestions=[],
        )


# =============================================================================
# Custom parameter (deepseek/deepseek-v3.2)
# =============================================================================

CUSTOM_PARAM_SYSTEM = """You generate a single research variable definition for competitive analysis. Match the format: id (snake_case, prefix dyn_), name, category, research_prompt (multi-line), example_queries (4 strings with {{company}}), answer_spec (3 bullets), key_terms (6-8), preferred_source_types, max_concise_chars (200), rationale. Output ONLY valid JSON inside <result>...</result>."""


async def generate_custom_parameter(description: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a full variable definition from a free-text description."""
    client = LLMClient()
    companies = context.get("companies", [])
    industry = context.get("industry_context", "Unknown")

    user_prompt = f"""User wants to add this parameter: "{description}". Industry: {industry}. Companies: {companies}.
Generate a full research variable definition (id with dyn_ prefix, name, category, research_prompt, example_queries (4 with {{company}}), answer_spec (3), key_terms (6-8), preferred_source_types, max_concise_chars 200, rationale). Output JSON inside <result>...</result>."""

    content = await client.complete_simple(
        prompt=user_prompt,
        system_prompt=CUSTOM_PARAM_SYSTEM,
        temperature=0.3,
        max_tokens=1024,
        model_override=MODEL_FAST,
    )
    try:
        return _extract_json_block(content)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Failed to parse custom parameter: %s", e)
        return {
            "id": "dyn_custom",
            "name": description[:50],
            "category": "Custom",
            "research_prompt": f"Research the following for {{company}}: {description}",
            "example_queries": [f"{{company}} {description}", f"{{company}}"],
            "answer_spec": ["Key findings", "Sources", "Date"],
            "key_terms": description.split()[:8],
            "preferred_source_types": ["official", "tier1_news"],
            "max_concise_chars": 200,
            "rationale": "User-requested parameter.",
        }
