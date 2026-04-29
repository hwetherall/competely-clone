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
5. Main revenue driver (Q10): subscription, usage, services, outcomes, project fees, data/API access, or another primary driver.

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
            "main revenue driver - subscription, usage, services, outcomes, or project fees (Q10)",
            "GTM lesson for Innovera",
        ],
        preferred_source_types=["official", "tier1_news"],
        key_terms=["pricing", "demo", "enterprise", "customers", "ICP", "sales", "partner", "go-to-market", "revenue", "subscription", "usage-based", "services revenue", "outcomes", "primary driver"],
        max_concise_chars=260,
        tier="always",
    ),
    VariableDefinition(
        id="inv_packaging",
        name="Packaging",
        category="Commercial Deep Dive",
        research_prompt="""Analyze how {company} packages and bundles its product offering.

Answer three things explicitly:
1. TIER CONTENTS (Q1): For each named package or tier, what features, capabilities, limits, support level, and SLAs are included?
2. ADD-ONS (Q4): What costs extra beyond the base package - paid integrations, professional services, premium support, advanced modules, training, certification?
3. FLEXIBILITY (Q7): How flexible is the packaging? Are custom bundles offered for enterprise? Is there a Custom or Enterprise tier? Is everything modular or are tiers locked?

PRIMARY SOURCE: the structured Firecrawl extract from the commercial pre-research phase if available.
SECONDARY SOURCES: Exa for customer reviews mentioning what is negotiable in practice, including G2, Vendr, Reddit, and migration posts.

If pricing or packaging is opaque, say so directly and treat opacity as the finding.""",
        example_queries=[
            "{company} pricing tiers what's included",
            "{company} add-ons paid integrations services",
            "{company} enterprise custom bundle plan",
            "{company} G2 review features locked higher tier",
        ],
        answer_spec=[
            "tier names and what each tier includes (Q1)",
            "what costs extra beyond the base package - add-ons, services, integrations (Q4)",
            "packaging flexibility - custom bundles, enterprise plans, negotiability (Q7)",
        ],
        preferred_source_types=["official", "tier1_news"],
        key_terms=["tier", "plan", "package", "include", "add-on", "module", "enterprise", "custom", "bundle", "feature", "limit"],
        max_concise_chars=240,
        tier="always",
    ),
    VariableDefinition(
        id="inv_pricing_mechanics",
        name="Pricing Mechanics",
        category="Commercial Deep Dive",
        research_prompt="""Analyze the mechanics of how {company} charges customers.

Answer four things explicitly:
1. PRICING UNIT (Q2): What is the core unit of charge? Per user/seat, per project, per usage, per outcome, flat platform fee, or hybrid?
2. STARTING PRICE & ACV (Q3): What is the published starting price? What is the typical annual contract value for a real customer?
3. PILOT/ENTRY OFFER (Q5): Is there a free trial, freemium tier, paid pilot, or POC offering? What is its structure, duration, and conversion path?
4. SCALING (Q9): How does the bill grow as the customer scales? Linear per-seat, tiered step-functions, volume discounts, or usage caps?

PRIMARY SOURCE: structured Firecrawl extract for Q2, published starting price, and Q9. ACV and pilot conversion paths usually require Exa.

If pricing is opaque, say so directly and report what can be inferred from credible evidence.""",
        example_queries=[
            "{company} pricing per user per seat per usage",
            "{company} starting price minimum",
            "{company} typical ACV annual contract value Vendr",
            "{company} free trial pilot POC",
            "{company} volume discount scale pricing",
        ],
        answer_spec=[
            "core pricing unit - per user, per project, per usage, per outcome (Q2)",
            "starting price and typical annual contract value (Q3)",
            "pilot or entry offer structure (Q5)",
            "how pricing scales with usage or scope (Q9)",
        ],
        preferred_source_types=["official", "tier1_news", "analyst"],
        key_terms=["per seat", "per user", "per usage", "per query", "ACV", "starting at", "minimum", "trial", "pilot", "POC", "volume discount", "scale", "tier"],
        max_concise_chars=300,
        tier="always",
    ),
    VariableDefinition(
        id="inv_contract_structure",
        name="Contract Structure",
        category="Commercial Deep Dive",
        research_prompt="""Analyze the contract terms and upsell mechanics of {company}'s commercial relationships.

Answer two things explicitly:
1. UPGRADE TRIGGERS (Q6): What causes a customer to expand or upgrade? Seat expansion, usage thresholds, feature gating, time-based renegotiation, success milestones? What are the mechanisms - auto-upgrade, sales-led upsell, or hard cap forcing renegotiation?
2. CONTRACT STRUCTURE (Q8): What are typical term lengths? Is there a minimum commitment? How does renewal work - auto-renew, negotiated, price uplift, early termination terms?

PRIMARY SOURCE for Q8: Firecrawl extract on terms, legal, MSA, or pricing pages.
PRIMARY SOURCE for Q6: Exa evidence from customer stories, negotiation guides, reviews, and seller content.

If contract terms are not disclosed, say so and distinguish public terms from inferred enterprise practice.""",
        example_queries=[
            "{company} terms of service contract length",
            "{company} minimum commitment seat floor",
            "{company} renewal auto-renew price uplift",
            "{company} upgrade trigger expansion playbook",
            "{company} customer expanded contract Vendr",
        ],
        answer_spec=[
            "upgrade and upsell triggers (Q6)",
            "contract term length, minimum commitment, renewal mechanics (Q8)",
        ],
        preferred_source_types=["official", "tier1_news"],
        key_terms=["contract", "term", "minimum", "commitment", "renewal", "auto-renew", "uplift", "expansion", "upgrade", "trigger", "seat floor", "MSA", "terms of service"],
        max_concise_chars=240,
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
- Packaging
- Pricing Mechanics
- Contract Structure
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

