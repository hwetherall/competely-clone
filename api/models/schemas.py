"""
Pydantic models for API request/response schemas.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


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


class RunDetailResponse(BaseModel):
    """Full detail of a completed run."""
    id: str
    timestamp: str
    companies: List[str]
    variables: List[str]
    grid: Dict[str, Dict[str, CellData]]
    metadata: RunMetadata
    status: RunStatus = RunStatus.COMPLETED


class RunCreateRequest(BaseModel):
    """Request to create a new research run."""
    companies: List[str] = Field(..., min_length=1, description="List of company names to analyze")
    variables: List[str] = Field(..., min_length=1, description="List of variable IDs to research")
    concurrency: int = Field(default=3, ge=1, le=10, description="Maximum concurrent tasks")
    fast_mode: bool = Field(default=False, description="Use fast mode (single iteration)")


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
