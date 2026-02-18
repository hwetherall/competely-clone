"""
AVIS Competitive Analysis variable definitions.

Derived from the AVIS framework (Innovera's constitution, Chapter 4: Competitive Analysis).
Organized around 8 AVIS comparison categories rather than the Competely product-comparison lens.

The AVIS path evaluates the competitive *environment* through an investment-thesis lens:
Can a new venture win here? What are the moats? Where is the whitespace?
"""

from config.variables import VariableDefinition


# =============================================================================
# Tier 1: Always included (core AVIS dimensions)
# =============================================================================

AVIS_ALWAYS: list[VariableDefinition] = [

    # --- 1. Product Capability ---
    VariableDefinition(
        id="avis_product_capability",
        name="Product Capability",
        category="Product Capability",
        research_prompt="""Assess {company}'s product capability across four sub-dimensions:

1. Feature breadth & depth: How wide is the feature set? How deep is each feature vs. competitors?
2. UX quality: Is the product praised or criticized for usability, design, onboarding, speed?
3. Scalability: Can the product handle enterprise-scale or high-volume usage? Any known limits?
4. Integrations: How many third-party integrations exist? Is there an API or marketplace?

IN SCOPE: Product reviews (G2, Capterra), feature comparison pages, engineering blog posts, customer testimonials about product quality.
NOT IN SCOPE: Pricing (covered separately), marketing claims without evidence, team size.""",
        example_queries=[
            "{company} product features review",
            "{company} G2 reviews UX scalability",
            "{company} integrations API marketplace",
            "{company} product comparison vs competitors",
        ],
        answer_spec=[
            "feature breadth (number of core capabilities)",
            "UX quality signals (review scores, NPS, praise/criticism)",
            "scalability evidence (enterprise clients, volume handled)",
        ],
        preferred_source_types=["official", "tier1_news", "analyst"],
        key_terms=["features", "UX", "usability", "scalability", "integrations", "API", "G2", "review"],
        max_concise_chars=240,
        tier="always",
    ),

    # --- 2. Business Model ---
    VariableDefinition(
        id="avis_business_model",
        name="Business Model & Margin Profile",
        category="Business Model",
        research_prompt="""Analyze {company}'s business model through the AVIS lens:

1. Pricing structure: What are the pricing tiers, models (subscription, transaction fee, freemium, usage-based)?
2. Revenue streams: How diversified are revenue sources? Any secondary monetization (data, ads, services)?
3. Gross margin profile: What is the gross margin (or estimated margin)? Is the business capital-light or capital-heavy?

IN SCOPE: Pricing pages, SEC filings, analyst estimates, funding announcements with revenue hints, investor presentations.
NOT IN SCOPE: Competitor comparison (handled elsewhere), product features (separate parameter).""",
        example_queries=[
            "{company} pricing plans cost",
            "{company} business model revenue streams",
            "{company} gross margin profitability",
            "{company} annual report financials",
        ],
        answer_spec=[
            "pricing model type and tiers",
            "primary and secondary revenue streams",
            "gross margin estimate or profitability signals",
        ],
        preferred_source_types=["official", "regulatory", "tier1_news"],
        key_terms=["pricing", "revenue", "margin", "subscription", "freemium", "monetization", "profitability"],
        max_concise_chars=240,
        tier="always",
    ),

    # --- 3. Market Traction ---
    VariableDefinition(
        id="avis_market_traction",
        name="Market Traction & Retention",
        category="Market Traction",
        research_prompt="""Assess {company}'s market traction using AVIS metrics:

1. Revenue scale: What is the reported or estimated annual revenue?
2. User base & adoption: How many users, customers, or accounts? Growth rate?
3. Client quality: Are there notable client logos, case studies, or enterprise references?
4. Churn & net retention: What is the churn rate? Net dollar retention? Any signals of customer stickiness?

IN SCOPE: Earnings reports, press releases, customer lists, G2/Capterra review counts, LinkedIn employee count as proxy.
NOT IN SCOPE: Market size (separate), product features (separate).""",
        example_queries=[
            "{company} revenue annual report",
            "{company} number of customers users",
            "{company} customer logos case studies",
            "{company} churn rate net retention",
        ],
        answer_spec=[
            "revenue figure and time period",
            "user/customer count and growth",
            "churn or net retention data",
        ],
        preferred_source_types=["regulatory", "tier1_news", "official"],
        key_terms=["revenue", "users", "customers", "churn", "retention", "growth", "ARR", "MRR"],
        max_concise_chars=240,
        tier="always",
    ),

    # --- 4. Funding & Ownership ---
    VariableDefinition(
        id="avis_funding_ownership",
        name="Funding & Ownership",
        category="Funding & Ownership",
        research_prompt="""Map {company}'s capital structure and ownership:

1. Capital raised: Total funding to date, latest round size and valuation.
2. Investor quality: Who are the backers? Any tier-1 VCs (Sequoia, A16Z, etc.) or strategic investors?
3. Ownership structure: Is it VC-backed, PE-owned, founder-controlled, or publicly traded? Any strategic investors with operational synergies?

IN SCOPE: Crunchbase, PitchBook data, SEC filings, press releases about funding rounds.
NOT IN SCOPE: Revenue (covered in Market Traction), product details.""",
        example_queries=[
            "{company} funding raised investors",
            "{company} Crunchbase funding rounds",
            "{company} valuation latest round",
            "{company} investors backers ownership",
        ],
        answer_spec=[
            "total funding raised and latest round",
            "key investors and their tier",
            "ownership type (VC/PE/public/founder-led)",
        ],
        preferred_source_types=["tier1_news", "official", "regulatory"],
        key_terms=["funding", "raised", "investors", "valuation", "round", "series", "ownership", "Crunchbase"],
        max_concise_chars=240,
        tier="always",
    ),

    # --- 5. Go-to-Market Engine ---
    VariableDefinition(
        id="avis_gtm_engine",
        name="Go-to-Market Engine",
        category="Go-to-Market Engine",
        research_prompt="""Evaluate {company}'s go-to-market strategy:

1. Sales model: Direct sales, channel/partner sales, self-serve/PLG, or hybrid?
2. Target motion: Enterprise top-down, SMB bottom-up, consumer viral, or developer-led?
3. Distribution channels: What channels drive customer acquisition (organic, paid, partnerships, marketplace)?
4. CAC/LTV signals: Any evidence of customer acquisition cost efficiency or lifetime value? Free trial conversion rates?

IN SCOPE: Job postings (sales team structure), pricing page (self-serve signals), partner pages, case studies, LinkedIn sales headcount.
NOT IN SCOPE: Pricing specifics (covered in Business Model), product features.""",
        example_queries=[
            "{company} go to market strategy",
            "{company} sales model enterprise vs self-serve",
            "{company} partner channel program",
            "{company} customer acquisition strategy growth",
        ],
        answer_spec=[
            "primary sales motion (direct/PLG/channel)",
            "target customer motion (enterprise/SMB/consumer)",
            "distribution channels and partnership signals",
        ],
        preferred_source_types=["official", "tier1_news"],
        key_terms=["go-to-market", "sales", "PLG", "enterprise", "self-serve", "channel", "partner", "acquisition"],
        max_concise_chars=240,
        tier="always",
    ),

    # --- 6. IP & Defensibility ---
    VariableDefinition(
        id="avis_ip_defensibility",
        name="IP & Defensibility",
        category="IP & Defensibility",
        research_prompt="""Assess {company}'s competitive moats and defensibility:

1. Patents & IP: How many patents filed/granted? Any proprietary algorithms or trade secrets?
2. Data moats: Does the company have unique data assets that improve with scale?
3. Switching costs: What makes it hard for customers to leave (data lock-in, workflow integration, training)?
4. Regulatory licenses: Any regulatory approvals, certifications, or compliance requirements that serve as barriers?

IN SCOPE: Patent databases, regulatory filings, product architecture documentation, customer reviews mentioning lock-in.
NOT IN SCOPE: Brand (separate), network effects (separate sometimes parameter).""",
        example_queries=[
            "{company} patents intellectual property",
            "{company} proprietary technology moat",
            "{company} customer switching costs lock-in",
            "{company} regulatory certifications licenses",
        ],
        answer_spec=[
            "patent count and key IP areas",
            "data moat or proprietary advantage",
            "switching cost mechanisms",
        ],
        preferred_source_types=["regulatory", "official", "tier1_news"],
        key_terms=["patent", "IP", "proprietary", "moat", "switching cost", "lock-in", "regulatory", "certification"],
        max_concise_chars=240,
        tier="always",
    ),

    # --- 7. Team & Leadership ---
    VariableDefinition(
        id="avis_team_leadership",
        name="Team & Leadership",
        category="Team & Leadership",
        research_prompt="""Evaluate {company}'s team and leadership quality:

1. Founder background: What is the founding team's track record? Serial entrepreneurs, domain experts, or first-timers?
2. Executive quality: Key hires, notable additions (CTO from Google, CFO with IPO experience)?
3. Turnover signals: Any executive departures, leadership changes, or Glassdoor red flags?
4. Hiring velocity: Is the company actively hiring? In what functions (engineering, sales, etc.)? Growth signals from LinkedIn headcount.

IN SCOPE: LinkedIn profiles, Glassdoor, press releases about executive hires, job postings.
NOT IN SCOPE: Company culture opinions, product decisions (separate).""",
        example_queries=[
            "{company} founders background leadership",
            "{company} executive team key hires",
            "{company} Glassdoor reviews leadership",
            "{company} hiring jobs growth LinkedIn",
        ],
        answer_spec=[
            "founder credentials and track record",
            "notable executive hires or departures",
            "hiring velocity and growth signals",
        ],
        preferred_source_types=["official", "tier1_news"],
        key_terms=["founder", "CEO", "CTO", "executive", "leadership", "hire", "Glassdoor", "LinkedIn", "team"],
        max_concise_chars=240,
        tier="always",
    ),

    # --- 8. Positioning & Alpha ---
    VariableDefinition(
        id="avis_positioning_alpha",
        name="Positioning & Competitive Alpha",
        category="Positioning & Differentiation",
        research_prompt="""Determine {company}'s strategic positioning and competitive alpha:

1. Unique positioning: How does the company position itself relative to competitors? Premium, budget, niche, platform?
2. Competitive alpha: What is the venture's functional or experiential advantage over alternatives? What do customers consistently praise?
3. Whitespace claim: Is the company claiming underserved territory? What whitespace is unclaimed or weakly defended?

IN SCOPE: Marketing pages, "Why Us" sections, analyst comparisons, customer reviews highlighting advantages, competitive teardowns.
NOT IN SCOPE: Detailed feature lists (covered in Product Capability), pricing (covered in Business Model).""",
        example_queries=[
            "{company} competitive advantage positioning",
            "{company} vs competitors comparison",
            "{company} unique value differentiation",
            "why choose {company} over alternatives",
        ],
        answer_spec=[
            "market positioning (premium/mid/niche/platform)",
            "primary competitive alpha (what they win on)",
            "whitespace being claimed",
        ],
        preferred_source_types=["official", "tier1_news", "analyst"],
        key_terms=["positioning", "advantage", "differentiation", "alpha", "whitespace", "unique", "vs"],
        max_concise_chars=240,
        tier="always",
    ),

    # --- 9. Competitive Landscape Framing ---
    VariableDefinition(
        id="avis_competitive_landscape",
        name="Competitive Landscape Framing",
        category="Competitive Landscape",
        research_prompt="""Map {company}'s competitive landscape using three AVIS framings:

1. Problem-defined: Who else solves the same core problem for the same customer?
2. Category-defined: Who plays in the same vertical or horizontal category?
3. Adjacency-defined: Who could pivot into this space given capabilities (platforms, capital, IP)?

For each framing, identify 2-4 competitors or potential competitors.

IN SCOPE: Industry reports, analyst landscape maps, Gartner/Forrester mentions, competitive comparison articles.
NOT IN SCOPE: Deep analysis of each competitor (this parameter maps the landscape; other parameters analyze depth).""",
        example_queries=[
            "{company} competitors landscape market map",
            "{company} competitive alternatives industry",
            "{company} Gartner Magic Quadrant category",
            "who competes with {company} adjacent markets",
        ],
        answer_spec=[
            "problem-defined competitors (2-4 names)",
            "category-defined competitors (2-4 names)",
            "adjacency threats (who could enter from adjacent space)",
        ],
        preferred_source_types=["analyst", "tier1_news"],
        key_terms=["competitor", "landscape", "market map", "alternative", "Gartner", "adjacent", "category"],
        max_concise_chars=280,
        tier="always",
    ),

    # --- 10. Vulnerability & Threat Assessment ---
    VariableDefinition(
        id="avis_vulnerability_threats",
        name="Vulnerability & Threat Assessment",
        category="Risk of Displacement",
        research_prompt="""Assess where {company} is most vulnerable to competitive displacement:

1. Head-to-head weaknesses: On which dimensions do competitors beat {company}? (speed, price, features, brand, etc.)
2. Replicability: How easily can a well-funded competitor replicate {company}'s current solution?
3. Emerging threats: Are there stealth startups, new entrants, or adjacent players gaining traction?
4. External risks: What events (M&A, regulation, platform shifts) could dramatically reshape the landscape?

IN SCOPE: Customer complaints (G2 negative reviews), analyst risk assessments, emerging competitor coverage, regulatory news.
NOT IN SCOPE: Internal operational risks (this focuses on external competitive threats).""",
        example_queries=[
            "{company} weaknesses customer complaints",
            "{company} competitive threats risks",
            "{company} G2 negative reviews limitations",
            "{company} disruption risk new entrants",
        ],
        answer_spec=[
            "key competitive weaknesses (where others win)",
            "replicability assessment (easy/moderate/hard to copy)",
            "emerging threats and external risks",
        ],
        preferred_source_types=["tier1_news", "analyst"],
        key_terms=["weakness", "vulnerability", "threat", "risk", "disrupt", "complaint", "limitation", "entrant"],
        max_concise_chars=240,
        tier="always",
    ),
]


# =============================================================================
# Tier 2: Sometimes included (contextual AVIS dimensions)
# =============================================================================

AVIS_SOMETIMES: list[VariableDefinition] = [

    VariableDefinition(
        id="avis_exit_readiness",
        name="Exit Readiness",
        category="Exit Readiness",
        research_prompt="""Assess {company}'s exit readiness and strategic positioning for transactions:

1. IPO potential: Is the company on an IPO track? Any S-1 filings, IPO rumors, or SPAC discussions?
2. M&A signals: Has {company} been involved in M&A discussions (as acquirer or target)?
3. Strategic interest: Which larger players might be interested in acquiring {company}, and why?

IN SCOPE: SEC filings, M&A news, analyst speculation, strategic fit analysis.
NOT IN SCOPE: Current financial performance (covered in Market Traction).""",
        example_queries=[
            "{company} IPO plans filing",
            "{company} acquisition target M&A",
            "{company} strategic buyers interest",
            "{company} exit valuation rumors",
        ],
        answer_spec=[
            "IPO readiness signals",
            "M&A activity or interest",
            "potential strategic acquirers",
        ],
        preferred_source_types=["tier1_news", "regulatory"],
        key_terms=["IPO", "acquisition", "M&A", "exit", "strategic", "SPAC", "filing", "valuation"],
        max_concise_chars=200,
        tier="sometimes",
    ),

    VariableDefinition(
        id="avis_deal_comps",
        name="Deal & Transaction Comps",
        category="Exit Readiness",
        research_prompt="""Research precedent transactions and deal comps relevant to {company}'s space:

1. Past transactions: What acquisitions have happened in this space? At what valuations?
2. Deal rationale: Why did those deals happen? (talent, technology, customer base, market access?)
3. Benchmark valuation: What revenue multiples or valuation benchmarks are typical?

IN SCOPE: Crunchbase M&A data, PitchBook, press coverage of deals, Capital IQ.
NOT IN SCOPE: {company}'s own valuation (covered in Funding & Ownership).""",
        example_queries=[
            "{company} industry acquisitions deals",
            "{company} sector M&A transactions valuations",
            "{company} comparable deal precedent",
            "{company} space acquisition revenue multiples",
        ],
        answer_spec=[
            "notable precedent transactions (names, dates, values)",
            "deal rationale and strategic fit",
            "valuation benchmark multiples",
        ],
        preferred_source_types=["tier1_news", "regulatory"],
        key_terms=["acquisition", "deal", "transaction", "valuation", "multiple", "M&A", "precedent", "comps"],
        max_concise_chars=200,
        tier="sometimes",
    ),

    VariableDefinition(
        id="avis_regulatory_landscape",
        name="Regulatory Landscape",
        category="IP & Defensibility",
        research_prompt="""Analyze the regulatory environment affecting {company}:

1. Regulatory requirements: What licenses, certifications, or compliance requirements apply?
2. Regulatory moat: Do compliance requirements create barriers to entry for new competitors?
3. Regulatory risk: Are there pending regulations that could help or hurt {company}?

IN SCOPE: Industry regulations, compliance certifications, regulatory filings, legal news.
NOT IN SCOPE: General corporate governance, internal policies.""",
        example_queries=[
            "{company} regulatory compliance requirements",
            "{company} industry regulations licenses",
            "{company} regulatory risk pending legislation",
            "{company} certifications compliance barriers",
        ],
        answer_spec=[
            "key regulatory requirements",
            "regulatory barriers to entry",
            "pending regulatory changes",
        ],
        preferred_source_types=["regulatory", "tier1_news"],
        key_terms=["regulation", "compliance", "license", "certification", "regulatory", "legislation", "barrier"],
        max_concise_chars=200,
        tier="sometimes",
    ),

    VariableDefinition(
        id="avis_network_effects",
        name="Network Effects & Platform Dynamics",
        category="IP & Defensibility",
        research_prompt="""Evaluate whether {company} benefits from network effects or platform dynamics:

1. Direct network effects: Does the product become more valuable as more users join (e.g., social, marketplace)?
2. Indirect network effects: Does a growing user base attract complementary participants (e.g., developers, content creators)?
3. Platform lock-in: Does {company} operate as a platform with third-party ecosystem dependencies?
4. Data flywheel: Does more usage generate data that improves the product (e.g., AI, recommendations)?

IN SCOPE: Product architecture analysis, marketplace dynamics, developer ecosystem, data strategy.
NOT IN SCOPE: General product features (covered in Product Capability).""",
        example_queries=[
            "{company} network effects platform",
            "{company} marketplace ecosystem dynamics",
            "{company} developer platform API ecosystem",
            "{company} data flywheel AI advantage",
        ],
        answer_spec=[
            "type of network effects (direct/indirect/none)",
            "platform ecosystem strength",
            "data flywheel or compounding advantage",
        ],
        preferred_source_types=["analyst", "tier1_news"],
        key_terms=["network effect", "platform", "ecosystem", "marketplace", "flywheel", "lock-in", "two-sided"],
        max_concise_chars=200,
        tier="sometimes",
    ),

    VariableDefinition(
        id="avis_adjacency_threats",
        name="Adjacency Threats",
        category="Risk of Displacement",
        research_prompt="""Identify adjacency threats to {company} — players who could pivot into this space:

1. Big-tech encroachment: Could a FAANG-scale company launch a competing product using existing distribution?
2. Adjacent startups: Are there well-funded startups in adjacent categories building overlapping capabilities?
3. Vertical integration risk: Could {company}'s customers or suppliers move into its space?
4. Platform risk: Is {company} dependent on a platform (AWS, Shopify, Salesforce) that could compete?

IN SCOPE: Industry analysis, platform dependency mapping, adjacent market coverage.
NOT IN SCOPE: Direct competitors (covered in Competitive Landscape).""",
        example_queries=[
            "{company} adjacency threat big tech",
            "{company} platform risk dependency",
            "{company} vertical integration threat",
            "could Google Amazon compete with {company}",
        ],
        answer_spec=[
            "big-tech encroachment risk",
            "adjacent startup threats",
            "platform dependency risks",
        ],
        preferred_source_types=["tier1_news", "analyst"],
        key_terms=["adjacent", "encroachment", "platform risk", "vertical integration", "FAANG", "compete", "pivot"],
        max_concise_chars=200,
        tier="sometimes",
    ),

    VariableDefinition(
        id="avis_brand_equity",
        name="Brand Equity & Perception",
        category="Positioning & Differentiation",
        research_prompt="""Assess {company}'s brand strength and market perception:

1. Brand recognition: How well-known is the brand within its target market?
2. Customer sentiment: What is the overall sentiment? NPS scores, review ratings, social media tone?
3. Thought leadership: Is the company seen as a thought leader (conference keynotes, publications, media mentions)?
4. Brand promise vs. reality: Is there a gap between marketing claims and customer experience?

IN SCOPE: G2/Capterra ratings, social media sentiment, conference presence, media mentions.
NOT IN SCOPE: Product features (separate), pricing (separate).""",
        example_queries=[
            "{company} brand reputation perception",
            "{company} G2 Capterra rating NPS",
            "{company} thought leadership conference",
            "{company} customer sentiment reviews social",
        ],
        answer_spec=[
            "brand recognition level",
            "customer sentiment (ratings, NPS)",
            "thought leadership presence",
        ],
        preferred_source_types=["official", "tier1_news"],
        key_terms=["brand", "reputation", "NPS", "sentiment", "review", "perception", "thought leader", "conference"],
        max_concise_chars=200,
        tier="sometimes",
    ),

    VariableDefinition(
        id="avis_switching_costs",
        name="Customer Switching Costs",
        category="IP & Defensibility",
        research_prompt="""Analyze the switching costs customers face when leaving {company}:

1. Technical switching costs: Data migration complexity, integration dependencies, API lock-in.
2. Operational switching costs: Retraining staff, workflow disruption, process redesign.
3. Psychological switching costs: Brand trust, relationship inertia, fear of the unknown.
4. Contractual barriers: Long-term contracts, early termination fees, volume commitments.

IN SCOPE: Customer reviews mentioning migration, competitor "switch from X" pages, contract terms.
NOT IN SCOPE: Product features (separate), pricing (separate).""",
        example_queries=[
            "{company} migration switching costs",
            "switch from {company} to competitor",
            "{company} data export migration guide",
            "{company} contract terms lock-in period",
        ],
        answer_spec=[
            "technical switching barriers",
            "operational switching costs",
            "contractual lock-in mechanisms",
        ],
        preferred_source_types=["official", "tier1_news"],
        key_terms=["switching cost", "migration", "lock-in", "contract", "export", "vendor", "sticky", "retention"],
        max_concise_chars=200,
        tier="sometimes",
    ),

    VariableDefinition(
        id="avis_talent_competition",
        name="Talent Competition & Culture",
        category="Team & Leadership",
        research_prompt="""Assess {company}'s position in the talent war:

1. Hiring velocity: How many open positions? In which functions? Is hiring accelerating or decelerating?
2. Talent attraction: Does the company attract top talent? Glassdoor ratings, employer brand?
3. Engineering culture: Is the company known for technical excellence? Open-source contributions, tech blog?
4. Retention signals: Any mass departures, layoff rounds, or culture concerns?

IN SCOPE: Job postings, Glassdoor, LinkedIn data, tech blog, open-source repos.
NOT IN SCOPE: Executive bios (covered in Team & Leadership).""",
        example_queries=[
            "{company} hiring jobs open positions",
            "{company} Glassdoor employer rating culture",
            "{company} engineering blog open source",
            "{company} layoffs departures retention",
        ],
        answer_spec=[
            "open positions count and functions",
            "Glassdoor rating and culture signals",
            "talent retention or attrition signals",
        ],
        preferred_source_types=["official", "tier1_news"],
        key_terms=["hiring", "jobs", "Glassdoor", "culture", "engineering", "open source", "layoff", "retention"],
        max_concise_chars=200,
        tier="sometimes",
    ),
]


# =============================================================================
# Combined list and helpers
# =============================================================================

AVIS_VARIABLES: list[VariableDefinition] = AVIS_ALWAYS + AVIS_SOMETIMES


def get_avis_always() -> list[VariableDefinition]:
    return list(AVIS_ALWAYS)


def get_avis_sometimes() -> list[VariableDefinition]:
    return list(AVIS_SOMETIMES)


def get_avis_variable(variable_id: str) -> VariableDefinition:
    for v in AVIS_VARIABLES:
        if v.id == variable_id:
            return v
    raise ValueError(f"Unknown AVIS variable: {variable_id}")


def get_all_avis_variable_ids() -> list[str]:
    return [v.id for v in AVIS_VARIABLES]
