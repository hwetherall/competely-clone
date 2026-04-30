"""
Pydantic models for API request/response schemas.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

from agents.schemas import CompetitorCandidate, DiscoveryRun, DiscoveryTargetProfile


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# =============================================================================
# Variable Schemas
# =============================================================================

class VariableResponse(BaseModel):
    """Single variable definition."""
    id: str
    name: str
    category: str
    description: Optional[str] = None


class VariableCategoryResponse(BaseModel):
    """Variables grouped by category."""
    categories: Dict[str, List[VariableResponse]]


class GenerateVariablesRequest(BaseModel):
    """Request to generate smart parameters from a set of competitors."""
    companies: List[str] = Field(..., min_length=2, description="List of company names (Set of Competitors)")
    company_profiles: List[str] = Field(
        default=["public_mature"],
        description="List of selected company profiles (e.g. 'public_mature', 'private_venture')",
    )
    parameter_path: str = Field(
        default="competely",
        description="Which parameter framework to use: 'competely', 'avis', or 'innovera'",
    )


class Tier2RecommendationSchema(BaseModel):
    """Whether to include a 'sometimes' variable for this competitor set."""
    variable_id: str
    include: bool
    reason: str


class DynamicVariableDefinition(BaseModel):
    """Full definition for a dynamically generated variable (Tier 3)."""
    id: str
    name: str
    category: str
    research_prompt: str
    example_queries: List[str] = []
    answer_spec: List[str] = []
    preferred_source_types: List[str] = []
    key_terms: List[str] = []
    max_concise_chars: int = 200
    rationale: Optional[str] = None


class VariableGenerationResponse(BaseModel):
    """Response from POST /api/variables/generate."""
    industry_context: str
    always_variables: List[VariableResponse] = Field(
        default_factory=list,
        description="Tier 1 variables (always included) for display",
    )
    always_parameter_contexts: Dict[str, str] = Field(
        default_factory=dict,
        description="Tier 1 variable id -> one-line context for why this dimension matters for this SoC",
    )
    tier2_recommendations: List[Tier2RecommendationSchema] = []
    generated_variables: List[DynamicVariableDefinition] = Field(
        default_factory=list,
        description="Tier 3 industry-specific variables with full definitions",
    )


# =============================================================================
# Discovery Schemas
# =============================================================================

class DiscoveryCreateRequest(BaseModel):
    """Request to start a competitor discovery run."""
    target_profile: Optional[DiscoveryTargetProfile] = None
    framing_seeds: Optional[Dict[str, str]] = None
    max_candidates: int = Field(default=20, ge=10, le=30)


class DiscoveryCreateResponse(BaseModel):
    discovery_run_id: str
    status: str = "running"


class DiscoveryRunResponse(DiscoveryRun):
    """Discovery run response."""
    pass


class DiscoveryManualCandidatesRequest(BaseModel):
    """Replace the manual-additions list on a discovery run."""
    names: List[str] = Field(default_factory=list)


class DiscoveryPromoteRequest(BaseModel):
    """Promote selected discovery candidates into a standard research run."""
    selected_names: List[str] = Field(..., min_length=1)
    variables: Optional[List[str]] = None
    dynamic_variables: Optional[List[DynamicVariableDefinition]] = None
    parameter_contexts: Optional[Dict[str, str]] = None
    version: Optional[str] = "v1"
    fast_mode: bool = False
    concurrency: int = Field(default=3, ge=1, le=10)
    parameter_path: str = "innovera"


class DiscoveryPromoteResponse(BaseModel):
    run_id: str
    status: RunStatus
    companies: List[str]


# =============================================================================
# Source Schemas
# =============================================================================

class SourceData(BaseModel):
    """Source citation data."""
    title: str
    url: str
    snippet: Optional[str] = None
    query: Optional[str] = None
    domain: Optional[str] = None
    source_score: Optional[float] = None
    is_official: Optional[bool] = None


# =============================================================================
# Cell Data Schemas
# =============================================================================

class CellData(BaseModel):
    """Data for a single research cell (company x variable)."""
    company: str
    variable_id: str
    variable_name: str
    concise: str
    comprehensive: str
    sources: List[SourceData] = []
    confidence: ConfidenceLevel = ConfidenceLevel.NONE
    iterations: int = 0
    total_searches: int = 0
    timestamp: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# =============================================================================
# Run Schemas
# =============================================================================

class RunMetadata(BaseModel):
    """Metadata about a research run."""
    total_cells: int
    successful_cells: int
    failed_cells: int
    elapsed_seconds: float
    concurrency: int = 3
    fast_mode: bool = False


class RunListItem(BaseModel):
    """Summary of a run for listing."""
    id: str
    companies: List[str]
    variables: List[str]
    status: RunStatus
    created_at: str
    completed_at: Optional[str] = None
    total_cells: int
    successful_cells: Optional[int] = None
    version: Optional[str] = Field(default="v1", description="'v1' or 'v2'")


class RunDetailResponse(BaseModel):
    """Full detail of a completed run (V1 grid)."""
    id: str
    timestamp: str
    companies: List[str]
    variables: List[str]
    grid: Dict[str, Dict[str, CellData]]
    metadata: RunMetadata
    status: RunStatus = RunStatus.COMPLETED
    version: Optional[str] = Field(default="v1", description="'v1' or 'v2'")


class RunDetailV2Response(BaseModel):
    """Full detail of a completed V2 relational run."""
    id: str
    timestamp: str
    companies: List[str]
    parameters: List[str]
    parameter_definitions: Dict[str, Dict[str, Any]]
    executive: Dict[str, Any]
    analyses: Dict[str, Dict[str, Any]]
    metadata: Dict[str, Any]
    status: RunStatus = RunStatus.COMPLETED
    version: str = "v2"


class GraveyardCompanySchema(BaseModel):
    """A discovered defunct company for post-mortem intelligence."""
    name: str
    years_active: str = ""
    peak_description: str = ""
    reason_summary: str = ""
    confidence: str = "medium"


class DiscoverGraveyardRequest(BaseModel):
    """Request to discover defunct companies in a sector."""
    companies: List[str] = Field(..., min_length=1, description="Living competitor names")
    industry_context: str = ""
    sector_hint: str = ""


class DiscoverGraveyardResponse(BaseModel):
    """Response with discovered defunct companies."""
    companies: List[GraveyardCompanySchema] = []


class RunCreateRequest(BaseModel):
    """Request to create a new research run."""
    companies: List[str] = Field(..., min_length=1, description="List of company names to analyze")
    variables: List[str] = Field(..., min_length=1, description="List of variable IDs to research")
    dynamic_variables: Optional[List[DynamicVariableDefinition]] = Field(
        default=None,
        description="Full definitions for dynamic (Tier 3) variables when selected",
    )
    concurrency: int = Field(default=3, ge=1, le=10, description="Maximum concurrent tasks")
    fast_mode: bool = Field(default=False, description="Use fast mode (single iteration)")
    version: Optional[str] = Field(default="v1", description="Pipeline version: 'v1' (grid) or 'v2' (relational)")
    venture_context: Optional[str] = Field(
        default=None,
        description="Optional venture description to personalize white space analysis and next steps in the executive brief",
    )
    parameter_contexts: Optional[Dict[str, str]] = Field(
        default=None,
        description="Optional variable id -> one-line context for each parameter (from variable generation); used by V2 pipeline to guide gather/normalize/synthesis.",
    )
    key_questions: Optional[List[str]] = Field(
        default=None,
        description="List of key questions to answer in the synthesis phase",
    )
    hypothesis: Optional[str] = Field(
        default=None,
        description="Hypothesis to validate in the synthesis phase",
    )
    graveyard_companies: Optional[List[str]] = Field(
        default=None,
        description="List of defunct company names for post-mortem intelligence analysis",
    )
    industry_context: Optional[str] = Field(
        default=None,
        description="Industry context for graveyard analysis",
    )
    parameter_path: Optional[str] = Field(
        default="competely",
        description="Parameter framework used for static variable lookup: 'competely', 'avis', or 'innovera'",
    )


class RunCreateResponse(BaseModel):
    """Response after starting a new run."""
    run_id: str
    status: RunStatus
    message: str


# =============================================================================
# Progress Schemas
# =============================================================================

class CurrentTask(BaseModel):
    """Currently executing task."""
    company: str
    variable: str
    step: Optional[str] = None


class ActivityItem(BaseModel):
    """Recent activity log item."""
    company: str
    variable: str
    confidence: str
    timestamp: str
    status: str = "completed"


class ProgressData(BaseModel):
    """Progress information."""
    completed: int
    total: int
    current: Optional[CurrentTask] = None


class RunProgressResponse(BaseModel):
    """Progress status for an ongoing run."""
    run_id: str
    status: RunStatus
    progress: ProgressData
    elapsed_seconds: float
    estimated_remaining_seconds: Optional[float] = None
    recent_activity: List[ActivityItem] = []


# =============================================================================
# Research Plan Schemas
# =============================================================================

class CompanyProfileSchema(BaseModel):
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
    subsidiaries: List[str] = []  # Structured list for subsidiary selector UI
    brand_name: Optional[str] = None  # When conglomerate: main brand only (e.g. Lufthansa German Airlines)


class CompanySuggestionSchema(BaseModel):
    """Suggested additional company from Step 2."""
    id: str
    name: str
    category: str
    rationale: str
    gap_filled: str
    subsidiaries: List[str] = []
    brand_name: Optional[str] = None


class ClarificationOptionSchema(BaseModel):
    """One suggested answer for a clarification question."""
    id: str
    label: str
    description: Optional[str] = None


class ClarificationQuestionSchema(BaseModel):
    """A single clarification question with options."""
    id: str
    question: str
    options: List[ClarificationOptionSchema]
    allow_free_text: bool = True
    context: Optional[str] = None
    impacts: Optional[List[str]] = None


class IntelligenceOptionSchema(BaseModel):
    """One option for an intelligence question."""
    id: str
    label: str
    description: Optional[str] = None


class IntelligenceQuestionSchema(BaseModel):
    """A strategic intelligence question shown before content generation."""
    id: str
    question: str
    options: List[IntelligenceOptionSchema]
    allow_multiple: bool = True
    allow_free_text: bool = True
    context: Optional[str] = None
    follow_up_hint: Optional[str] = None


class IntelligenceAnswerSchema(BaseModel):
    """A user's answer to an intelligence question."""
    question_id: str
    question_text: str = ""
    selected_option_ids: List[str] = []
    selected_labels: List[str] = []
    free_text: Optional[str] = None


class IntelligenceQuestionsRequest(BaseModel):
    """Request to generate intelligence questions for a wizard step."""
    step: str
    context: Dict[str, Any] = Field(default_factory=dict)


class IntelligenceQuestionsResponse(BaseModel):
    """Response containing intelligence questions."""
    questions: List[IntelligenceQuestionSchema] = []


class IntelligenceFollowupRequest(BaseModel):
    """Request to get follow-up questions after answering an intelligence question."""
    step: str
    question_id: str
    selected_options: List[str] = []
    context: Dict[str, Any] = Field(default_factory=dict)
    previous_answers: List[IntelligenceAnswerSchema] = []


class ValidateCompaniesRequest(BaseModel):
    """Request for Step 1: validate company names."""
    companies: List[str] = Field(..., min_length=1)


class ValidateCompaniesResponse(BaseModel):
    """Response from Step 1."""
    companies: List[CompanyProfileSchema]
    clarifications: List[ClarificationQuestionSchema] = []


class SuggestCompaniesRequest(BaseModel):
    """Request for Step 2: suggest additional companies."""
    companies: List[CompanyProfileSchema] = Field(..., min_length=1)
    intelligence_answers: Optional[List[IntelligenceAnswerSchema]] = None


class SuggestCompaniesResponse(BaseModel):
    """Response from Step 2."""
    suggestions: List[CompanySuggestionSchema]
    clarifications: List[ClarificationQuestionSchema] = []


class ResearchGoalResultSchema(BaseModel):
    """Output of Step 4: research goal generation."""
    mission_statement: str
    key_questions: List[str] = []
    hypothesis: Optional[str] = None
    perspective: str = "neutral"


class GenerateGoalRequest(BaseModel):
    """Request for Step 4: generate research goal."""
    companies: List[Any] = Field(default_factory=list)  # CompanyProfileSchema or str
    industry_context: str = ""
    parameter_summary: Optional[str] = None


class GenerateGoalResponse(BaseModel):
    """Response from Step 4."""
    goal: ResearchGoalResultSchema
    clarifications: List[ClarificationQuestionSchema] = []


class CompanyConfidenceSchema(BaseModel):
    """Per-company data availability estimate."""
    company_id: str
    company_name: str
    level: str
    reason: str


class ConfidencePreviewSchema(BaseModel):
    """Feasibility assessment for Step 6."""
    overall_level: str
    company_confidences: List[CompanyConfidenceSchema] = []
    warnings: List[str] = []
    suggestions: List[str] = []


class ClarificationAnswerSchema(BaseModel):
    """One user answer to a clarification question (for audit log)."""
    question_id: str
    option_id: Optional[str] = None
    free_text: Optional[str] = None


class ResearchPlanSchema(BaseModel):
    """Full research plan document."""
    id: str
    title: str
    status: str = "draft"  # draft | accepted | launched | completed
    created_at: str
    updated_at: str

    companies: List[CompanyProfileSchema] = []
    suggested_companies: List[CompanySuggestionSchema] = []
    accepted_suggestions: List[str] = []

    industry_context: str = ""
    parameter_path: str = "competely"  # "competely" | "avis" | "innovera"
    selected_variable_ids: List[str] = []
    dynamic_variables: List[DynamicVariableDefinition] = []
    parameter_contexts: Dict[str, str] = {}

    mission_statement: str = ""
    key_questions: List[str] = []
    hypothesis: Optional[str] = None
    perspective: str = "neutral"

    audience: str = "general"
    depth: str = "standard"  # quick | standard | deep
    focus_companies: List[str] = []
    known_context: Optional[str] = None

    graveyard_enabled: bool = False
    graveyard_companies: List[GraveyardCompanySchema] = []

    confidence_preview: Optional[ConfidencePreviewSchema] = None
    clarification_log: List[ClarificationAnswerSchema] = []
    run_id: Optional[str] = None


class PlanCreateRequest(BaseModel):
    """Request to save a new plan (full plan payload)."""
    title: str = "Research Plan"
    companies: List[CompanyProfileSchema] = []
    suggested_companies: List[CompanySuggestionSchema] = []
    accepted_suggestions: List[str] = []
    effective_company_names: Optional[List[str]] = None
    industry_context: str = ""
    parameter_path: str = "competely"
    selected_variable_ids: List[str] = []
    dynamic_variables: List[DynamicVariableDefinition] = []
    parameter_contexts: Dict[str, str] = {}
    mission_statement: str = ""
    key_questions: List[str] = []
    hypothesis: Optional[str] = None
    perspective: str = "neutral"
    audience: str = "general"
    depth: str = "standard"
    focus_companies: List[str] = []
    known_context: Optional[str] = None
    graveyard_enabled: bool = False
    graveyard_companies: List[GraveyardCompanySchema] = []


class PlanCreateResponse(BaseModel):
    """Response after saving a plan."""
    plan_id: str
    status: str = "draft"


class GenerateCustomParameterRequest(BaseModel):
    """Request to generate a single custom parameter from free text."""
    description: str
    companies: List[str] = []
    industry_context: str = ""


class StepClarificationsRequest(BaseModel):
    """Request to generate clarification questions for a step."""
    step: str
    context: Dict[str, Any] = Field(default_factory=dict)
