"""
Variable definitions for competitive analysis.

Each variable defines what information to research about a company,
including the research prompt and example search queries.
"""

from dataclasses import dataclass
from typing import List, Dict


@dataclass
class VariableDefinition:
    """Definition of a research variable."""
    id: str                    # e.g., "unique_value_proposition"
    name: str                  # e.g., "Unique Value Proposition"
    category: str              # e.g., "Core Positioning & Value"
    research_prompt: str       # Detailed instructions for researching this variable
    example_queries: List[str] # Example search queries to help the agent


# =============================================================================
# Variable Definitions - The 20 Research Variables
# =============================================================================

VARIABLES: List[VariableDefinition] = [
    # -------------------------------------------------------------------------
    # Core Positioning & Value (5 variables)
    # -------------------------------------------------------------------------
    VariableDefinition(
        id="unique_value_proposition",
        name="Unique Value Proposition",
        category="Core Positioning & Value",
        research_prompt="""Identify {company}'s primary unique value proposition - the single most compelling reason customers choose it over alternatives.

Look for:
- Official taglines and mission statements
- "About Us" or "Why Us" pages
- Investor presentations or pitch decks
- How they describe themselves vs competitors
- Customer testimonials highlighting key benefits

Summarize the core promise they make to customers in a clear, specific way.""",
        example_queries=[
            "{company} unique value proposition",
            "{company} why choose us",
            "{company} company mission",
            "what makes {company} different"
        ]
    ),
    
    VariableDefinition(
        id="positioning",
        name="Positioning",
        category="Core Positioning & Value",
        research_prompt="""Determine how {company} positions itself in the market.

Consider:
- Are they the premium option, affordable choice, or middle-market?
- Do they position as innovator, reliable incumbent, or disruptor?
- What market segment do they target (enterprise, SMB, consumer)?
- How do they want to be perceived vs competitors?

Look at marketing language, pricing strategy, and target audience signals.""",
        example_queries=[
            "{company} market positioning",
            "{company} target market",
            "{company} brand strategy",
            "how {company} competes"
        ]
    ),
    
    VariableDefinition(
        id="competitive_positioning_summary",
        name="Competitive Positioning Summary",
        category="Core Positioning & Value",
        research_prompt="""Summarize how {company} differentiates from its main competitors.

Find:
- Comparison pages on their website
- Analyst reports comparing them to competitors
- Review sites that compare alternatives
- Their messaging about what makes them better

Focus on concrete differentiators, not just marketing claims.""",
        example_queries=[
            "{company} vs competitors",
            "{company} competitive advantage",
            "{company} comparison",
            "why {company} over alternatives"
        ]
    ),
    
    VariableDefinition(
        id="differentiation",
        name="Differentiation",
        category="Core Positioning & Value",
        research_prompt="""List the specific features, capabilities, or attributes that make {company} different from competitors.

Focus on:
- Unique features not offered by others
- Technical capabilities or patents
- Business model differences
- Service or support differentiators
- Ecosystem or integration advantages

Prioritize concrete, verifiable differences.""",
        example_queries=[
            "{company} unique features",
            "{company} key differentiators",
            "{company} competitive features",
            "what {company} does differently"
        ]
    ),
    
    VariableDefinition(
        id="brand_promise",
        name="Brand Promise",
        category="Core Positioning & Value",
        research_prompt="""Identify {company}'s brand promise - the emotional or functional commitment they make to customers.

Look at:
- Mission and vision statements
- Brand taglines and slogans
- "Our Promise" or values pages
- How they describe customer outcomes
- Brand guidelines if publicly available""",
        example_queries=[
            "{company} brand promise",
            "{company} mission statement",
            "{company} our values",
            "{company} customer commitment"
        ]
    ),
    
    # -------------------------------------------------------------------------
    # Market & Customers (5 variables)
    # -------------------------------------------------------------------------
    VariableDefinition(
        id="target_customer_personas",
        name="Target Customer Personas",
        category="Market & Customers",
        research_prompt="""Identify 2-3 primary customer personas that {company} targets.

Include for each:
- Job title or role
- Company size or type
- Industry vertical
- Key pain points they solve
- Use case or buying trigger

Look at case studies, testimonials, and marketing targeting.""",
        example_queries=[
            "{company} customer case studies",
            "{company} who uses",
            "{company} ideal customer",
            "{company} testimonials"
        ]
    ),
    
    VariableDefinition(
        id="customer_segmentation",
        name="Customer Segmentation",
        category="Market & Customers",
        research_prompt="""How does {company} segment its customers?

Look for:
- Pricing tiers (SMB, Mid-Market, Enterprise)
- Industry-specific solutions
- Geographic segmentation
- Product lines for different segments
- Self-serve vs sales-assisted tiers""",
        example_queries=[
            "{company} pricing tiers",
            "{company} enterprise vs startup",
            "{company} customer segments",
            "{company} plans pricing"
        ]
    ),
    
    VariableDefinition(
        id="users",
        name="Users",
        category="Market & Customers",
        research_prompt="""Who are the day-to-day users of {company}'s product and how many are there?

Find:
- User roles (developers, finance teams, consumers, etc.)
- Total user count or active accounts
- Growth trends in user base
- User demographics if available""",
        example_queries=[
            "{company} number of users",
            "{company} active accounts",
            "{company} user statistics",
            "how many people use {company}"
        ]
    ),
    
    VariableDefinition(
        id="buyers",
        name="Buyers",
        category="Market & Customers",
        research_prompt="""Who makes the purchasing decision for {company}'s product?

Identify:
- Decision-maker titles (CFO, CTO, individual consumer)
- How this differs from end users
- Buying committee composition for B2B
- Purchase triggers and evaluation criteria""",
        example_queries=[
            "{company} buyer persona",
            "{company} who buys",
            "{company} decision maker",
            "{company} purchasing process"
        ]
    ),
    
    VariableDefinition(
        id="use_cases",
        name="Use Cases",
        category="Market & Customers",
        research_prompt="""List the primary use cases for {company}'s product.

Find:
- Main problems customers solve
- Specific workflows or tasks enabled
- Industry-specific applications
- Integration use cases

Look at documentation, case studies, and feature pages.""",
        example_queries=[
            "{company} use cases",
            "{company} what can you do",
            "{company} solutions",
            "{company} how businesses use"
        ]
    ),
    
    # -------------------------------------------------------------------------
    # Product & Capability (5 variables)
    # -------------------------------------------------------------------------
    VariableDefinition(
        id="key_features",
        name="Key Features",
        category="Product & Capability",
        research_prompt="""List the 5-7 most important features of {company}'s core product.

Focus on:
- Features highlighted on homepage
- Capabilities that drive purchasing decisions
- Features mentioned in reviews and comparisons
- Core functionality vs nice-to-haves

Use official product pages and feature lists.""",
        example_queries=[
            "{company} features",
            "{company} product capabilities",
            "{company} what does it do",
            "{company} key functionality"
        ]
    ),
    
    VariableDefinition(
        id="advanced_features",
        name="Advanced Features",
        category="Product & Capability",
        research_prompt="""Identify advanced or enterprise-grade features that {company} offers.

Look for:
- Features in higher pricing tiers
- Enterprise-only capabilities
- Advanced security or compliance features
- API and developer features
- Customization options""",
        example_queries=[
            "{company} enterprise features",
            "{company} advanced capabilities",
            "{company} pro features",
            "{company} API features"
        ]
    ),
    
    VariableDefinition(
        id="integrations",
        name="Integrations",
        category="Product & Capability",
        research_prompt="""List the major integrations and partnerships {company} offers.

Find:
- Native integrations with popular tools
- API and webhook capabilities
- Marketplace or app store
- Strategic partnerships
- Platform ecosystem connections""",
        example_queries=[
            "{company} integrations",
            "{company} apps marketplace",
            "{company} connects with",
            "{company} API partners"
        ]
    ),
    
    VariableDefinition(
        id="technology_stack",
        name="Technology Stack",
        category="Product & Capability",
        research_prompt="""What is known about {company}'s technology stack?

Look for:
- Engineering blog posts
- Job postings mentioning technologies
- Technical documentation
- Conference talks by engineers
- Open source contributions""",
        example_queries=[
            "{company} tech stack",
            "{company} engineering blog",
            "{company} technology",
            "{company} built with"
        ]
    ),
    
    VariableDefinition(
        id="product_roadmap",
        name="Product Roadmap",
        category="Product & Capability",
        research_prompt="""Find publicly available information about {company}'s product roadmap.

Look for:
- Recent feature releases
- Announced upcoming features
- Public roadmap pages
- Conference announcements
- Investor presentation mentions""",
        example_queries=[
            "{company} roadmap",
            "{company} new features 2024",
            "{company} product updates",
            "{company} whats new"
        ]
    ),
    
    # -------------------------------------------------------------------------
    # Economics & Scale (5 variables)
    # -------------------------------------------------------------------------
    VariableDefinition(
        id="business_models",
        name="Business Models",
        category="Economics & Scale",
        research_prompt="""Describe {company}'s business model and how they make money.

Identify:
- Revenue streams (transaction fees, subscriptions, freemium, etc.)
- Pricing model type
- Monetization strategy
- Unit economics if available""",
        example_queries=[
            "{company} business model",
            "{company} how they make money",
            "{company} revenue model",
            "{company} pricing model"
        ]
    ),
    
    VariableDefinition(
        id="pricing_strategy",
        name="Pricing Strategy",
        category="Economics & Scale",
        research_prompt="""Analyze {company}'s pricing strategy.

Find:
- Specific pricing tiers and costs
- Fee structures
- Free tier or trial offerings
- Enterprise pricing approach
- Pricing psychology (transparent vs sales-driven)""",
        example_queries=[
            "{company} pricing",
            "{company} cost",
            "{company} fees",
            "{company} plans"
        ]
    ),
    
    VariableDefinition(
        id="market_share",
        name="Market Share",
        category="Economics & Scale",
        research_prompt="""Find {company}'s market share in their primary market.

Look for:
- Analyst reports with market share data
- Industry publications
- Earnings call mentions
- Relative ranking vs competitors
- Transaction volume comparisons if applicable

Include the source and methodology when available.""",
        example_queries=[
            "{company} market share",
            "{company} market position",
            "{company} industry ranking",
            "{company} vs competitors market"
        ]
    ),
    
    VariableDefinition(
        id="market_size",
        name="Market Size",
        category="Economics & Scale",
        research_prompt="""What is the size of the market {company} operates in?

Find:
- TAM (Total Addressable Market)
- SAM (Serviceable Addressable Market)
- Market growth rates
- Industry forecasts

Look for analyst reports, investor presentations, and industry publications.""",
        example_queries=[
            "{company} market size",
            "{company} TAM",
            "digital payments market size",
            "{company} industry size"
        ]
    ),
    
    VariableDefinition(
        id="estimated_revenue",
        name="Estimated Revenue",
        category="Economics & Scale",
        research_prompt="""Find {company}'s estimated or reported annual revenue.

For public companies:
- Latest SEC filings
- Earnings reports
- Annual reports

For private companies:
- Funding announcements with revenue hints
- Analyst estimates
- Press coverage with figures

Always note the time period and source.""",
        example_queries=[
            "{company} revenue",
            "{company} annual revenue",
            "{company} earnings",
            "{company} financial results"
        ]
    ),
]


# =============================================================================
# Helper Functions
# =============================================================================

def get_variable(variable_id: str) -> VariableDefinition:
    """
    Get a variable definition by ID.
    
    Args:
        variable_id: The variable ID (e.g., "unique_value_proposition")
        
    Returns:
        The VariableDefinition
        
    Raises:
        ValueError: If the variable ID is not found
    """
    for var in VARIABLES:
        if var.id == variable_id:
            return var
    raise ValueError(f"Unknown variable: {variable_id}")


def get_variables_by_category() -> Dict[str, List[VariableDefinition]]:
    """
    Group variables by their category.
    
    Returns:
        Dictionary mapping category names to lists of variables
    """
    categories: Dict[str, List[VariableDefinition]] = {}
    for var in VARIABLES:
        if var.category not in categories:
            categories[var.category] = []
        categories[var.category].append(var)
    return categories


def get_all_variable_ids() -> List[str]:
    """Get list of all variable IDs."""
    return [var.id for var in VARIABLES]


def get_all_variable_names() -> List[str]:
    """Get list of all variable names."""
    return [var.name for var in VARIABLES]
