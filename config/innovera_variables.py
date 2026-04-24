"""
Innovera-tuned competitive deep-dive variable definitions.

This lens follows Zamir's ask: identify AI-native partial competitors,
understand how they operate and sell, track AI plus human consulting models,
and extract practical business-model lessons for Innovera.
"""

from config.innovera_profile import INNOVERA_PROFILE
from config.variables import VariableDefinition


INNOVERA_ALWAYS: list[VariableDefinition] = [
    VariableDefinition(
        id="inv_offer_shape",
        name="Offer Shape & Scope",
        category="Offer Model",
        research_prompt=f"""Analyze {{company}}'s offer shape in relation to Innovera.

Innovera context:
{INNOVERA_PROFILE}

Assess:
1. One-line offer: What does the company sell, in plain terms?
2. Problem scope: Which strategic, market research, competitive analysis, or decision workflows does it cover?
3. Engagement shape: Is it a report, software platform, expert service, subscription, project, API, or hybrid?
4. Speed and packaging: Is the offer smaller, faster, narrower, or easier to buy than a traditional consulting engagement?

IN SCOPE: Official product pages, pricing/packaging pages, case studies, demos, product launch posts, credible customer stories.
NOT IN SCOPE: Generic AI hype, unrelated product lines, or claims without evidence.

End with what the offer shape implies for Innovera's own packaging.""",
        example_queries=[
            "{company} product offering AI market research strategy",
            "{company} platform consulting service case study",
            "{company} pricing package subscription report",
            "{company} product demo competitive analysis market intelligence",
        ],
        answer_spec=[
            "one-line offer and artifact type",
            "problems and workflows covered",
            "speed or packaging lesson for Innovera",
        ],
        preferred_source_types=["official", "tier1_news", "analyst"],
        key_terms=["offer", "platform", "report", "subscription", "strategy", "market research", "competitive analysis", "workflow"],
        max_concise_chars=260,
        tier="always",
    ),
    VariableDefinition(
        id="inv_gtm_motion",
        name="GTM Motion",
        category="Go-to-Market",
        research_prompt=f"""Analyze how {{company}} goes to market, with emphasis on what Innovera can learn.

Innovera context:
{INNOVERA_PROFILE}

Assess:
1. Sales model: enterprise sales, self-serve, product-led, consulting-led, partner-led, founder-led, or hybrid.
2. ICP and buyer: target roles, company sizes, industries, and budget owners.
3. Deal shape: pricing signals, deal size, free trial/demo motion, procurement friction, and time-to-first-customer if available.
4. Channels: content, thought leadership, partnerships, marketplaces, events, expert networks, or outbound.

IN SCOPE: Pricing pages, demo CTAs, case studies, customer pages, partner pages, job postings, founder interviews.
NOT IN SCOPE: Product feature detail unless it directly shapes sales motion.

End with one practical GTM lesson for Innovera.""",
        example_queries=[
            "{company} pricing enterprise demo sales model",
            "{company} target customers case studies strategy teams",
            "{company} go to market founder interview",
            "{company} partners customers AI consulting platform",
        ],
        answer_spec=[
            "primary sales model and channels",
            "ICP, buyer, and deal-size signals",
            "GTM lesson for Innovera",
        ],
        preferred_source_types=["official", "tier1_news"],
        key_terms=["pricing", "demo", "enterprise", "customers", "ICP", "sales", "partner", "go-to-market"],
        max_concise_chars=260,
        tier="always",
    ),
    VariableDefinition(
        id="inv_client_engagement",
        name="Client Engagement Model",
        category="Client Engagement",
        research_prompt=f"""Research how {{company}} engages clients before, during, and after delivery.

Innovera context:
{INNOVERA_PROFILE}

Assess:
1. Onboarding: demo, workshop, data ingestion, expert interview, pilot, proof of concept, or immediate self-serve use.
2. Delivery cadence: one-time project, recurring deliverables, dashboard access, weekly advisory, continuous monitoring, or embedded workflow.
3. Human touch: account team, experts, analysts, consultants, community, customer success, or pure software support.
4. Success measurement: ROI claims, business outcomes, decision quality, time saved, revenue impact, or adoption metrics.

IN SCOPE: Case studies, service pages, implementation pages, testimonials, customer success materials.
NOT IN SCOPE: Internal team structure unless it affects client engagement.

End with what Innovera should copy, avoid, or test in client engagement.""",
        example_queries=[
            "{company} customer onboarding implementation",
            "{company} case study client engagement",
            "{company} customer success AI platform",
            "{company} consulting engagement model deliverables",
        ],
        answer_spec=[
            "onboarding and delivery cadence",
            "human touchpoints and support model",
            "engagement lesson for Innovera",
        ],
        preferred_source_types=["official", "tier1_news"],
        key_terms=["onboarding", "implementation", "customer success", "deliverables", "pilot", "workflow", "expert", "ROI"],
        max_concise_chars=260,
        tier="always",
    ),
    VariableDefinition(
        id="inv_ai_human_blend",
        name="AI / Human Blend",
        category="Operating Model",
        research_prompt=f"""Determine how {{company}} blends AI automation with human expertise.

Innovera context:
{INNOVERA_PROFILE}

Assess:
1. Automation layer: which research, analysis, data extraction, synthesis, or decision-support tasks appear AI-driven?
2. Human layer: consultants, analysts, subject matter experts, validators, customer success, or human-in-the-loop review.
3. Defensibility: whether the human layer improves trust, data quality, workflow adoption, proprietary insight, or merely adds cost.
4. Direction of travel: is the company becoming more AI-native, more service-heavy, or more blended over time?

IN SCOPE: Product architecture pages, AI methodology pages, hiring signals, service descriptions, executive interviews, credible press.
NOT IN SCOPE: Vague "AI-powered" claims without evidence of where humans or AI act.

End with whether Innovera looks ahead, behind, or differentiated on AI/human blend.""",
        example_queries=[
            "{company} AI human in the loop experts analysts",
            "{company} AI methodology market research consulting",
            "{company} consultants AI platform service",
            "{company} analyst workflow artificial intelligence",
        ],
        answer_spec=[
            "AI-automated tasks",
            "human roles in the delivery model",
            "implication for Innovera's AI/human blend",
        ],
        preferred_source_types=["official", "tier1_news", "analyst"],
        key_terms=["AI", "human-in-the-loop", "expert", "analyst", "consultant", "automation", "validation", "workflow"],
        max_concise_chars=280,
        tier="always",
    ),
    VariableDefinition(
        id="inv_size_signals",
        name="Size Signals",
        category="Scale & Funding",
        research_prompt="""Estimate {company}'s size and momentum using the best available public signals.

Assess:
1. Revenue or ARR: reported figure, estimate, or credible proxy, with date and source.
2. Client base: number of customers, notable logos, usage/adoption metrics, or case-study depth.
3. Headcount and hiring: employee count, hiring velocity, sales/engineering mix if visible.
4. Funding: total raised, latest round, investors, valuation if available.

IN SCOPE: Funding announcements, Crunchbase/PitchBook references when available, official customer pages, LinkedIn/headcount signals, annual reports for public companies.
NOT IN SCOPE: Unsupported database estimates without caveats.

Be explicit about uncertainty and distinguish reported facts from estimates.""",
        example_queries=[
            "{company} revenue ARR customers funding",
            "{company} funding raised latest round investors",
            "{company} customers logos headcount",
            "{company} LinkedIn employees revenue estimate",
        ],
        answer_spec=[
            "revenue/ARR or clearly labeled proxy",
            "client count, logos, or adoption signals",
            "funding, valuation, and headcount signals",
        ],
        preferred_source_types=["tier1_news", "official", "regulatory"],
        key_terms=["revenue", "ARR", "customers", "funding", "valuation", "employees", "headcount", "investors"],
        max_concise_chars=280,
        tier="always",
    ),
    VariableDefinition(
        id="inv_speed_to_market",
        name="Speed-to-Market Playbook",
        category="Speed & Execution",
        research_prompt=f"""Reconstruct {{company}}'s speed-to-market pattern and what it suggests for Innovera.

Innovera context:
{INNOVERA_PROFILE}

Assess:
1. Timeline: founding date, launch date, first notable customer, first funding, Series A or material scale milestone.
2. Wedge: the narrow initial use case, audience, geography, vertical, or workflow used to enter the market.
3. Acceleration levers: founder network, data access, partnerships, content, expert marketplace, incumbent distribution, or technical breakthrough.
4. Market learning: whether the company shipped a smaller/faster offer Innovera can learn from.

IN SCOPE: Founder interviews, launch announcements, funding stories, product changelogs, customer wins, archived history pages.
NOT IN SCOPE: Current size without a timeline.

End with a concrete speed-to-market playbook Innovera could test.""",
        example_queries=[
            "{company} founded launched first customers",
            "{company} startup story Series A launch",
            "{company} first customer funding timeline",
            "{company} product launch market research AI",
        ],
        answer_spec=[
            "timeline from founding to traction",
            "initial wedge and acceleration levers",
            "speed-to-market playbook for Innovera",
        ],
        preferred_source_types=["tier1_news", "official"],
        key_terms=["founded", "launch", "first customer", "Series A", "timeline", "wedge", "traction", "partnership"],
        max_concise_chars=280,
        tier="always",
    ),
    VariableDefinition(
        id="inv_takeaway_for_innovera",
        name="Takeaway for Innovera",
        category="Synthesis",
        research_prompt=f"""Synthesize what Innovera should learn from {{company}}.

Innovera context:
{INNOVERA_PROFILE}

This is a synthesis parameter. Use the available evidence from the other Innovera-lens dimensions when present:
- Offer Shape & Scope
- GTM Motion
- Client Engagement Model
- AI / Human Blend
- Size Signals
- Speed-to-Market Playbook

Answer as a practical action paragraph for Innovera:
1. What to copy or test.
2. What to avoid.
3. What to worry about competitively.
4. The single next experiment Innovera should run because of this competitor.

Do not invent facts. If supporting evidence is thin, state what must be validated next.""",
        example_queries=[
            "{company} strategy AI consulting platform customers",
            "{company} business model AI market research",
            "{company} go to market AI strategy platform",
            "{company} competitors Innovera alternative",
        ],
        answer_spec=[
            "what Innovera should copy or test",
            "what Innovera should avoid or monitor",
            "single next experiment for Innovera",
        ],
        preferred_source_types=["official", "tier1_news", "analyst"],
        key_terms=["lesson", "strategy", "business model", "go-to-market", "AI", "consulting", "platform", "customers"],
        max_concise_chars=300,
        tier="always",
    ),
]


INNOVERA_VARIABLES: list[VariableDefinition] = list(INNOVERA_ALWAYS)


def get_innovera_always() -> list[VariableDefinition]:
    return list(INNOVERA_ALWAYS)


def get_innovera_variable(variable_id: str) -> VariableDefinition:
    for v in INNOVERA_VARIABLES:
        if v.id == variable_id:
            return v
    raise ValueError(f"Unknown Innovera variable: {variable_id}")


def get_all_innovera_variable_ids() -> list[str]:
    return [v.id for v in INNOVERA_VARIABLES]


def get_innovera_variable_ids_before_takeaway() -> list[str]:
    return [v.id for v in INNOVERA_VARIABLES if v.id != "inv_takeaway_for_innovera"]

