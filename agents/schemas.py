from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class EvidenceSource:
    """A source used in research with scoring."""
    source_id: str  # e.g., "S1"
    url: str
    title: str
    domain: str
    source_score: float
    fetched_at: str  # ISO timestamp
    status: str = "success"  # success, error, cached

@dataclass
class EvidencePassage:
    """A specific passage extracted from a source."""
    source_id: str
    passage_id: str  # e.g., "P1"
    text: str
    relevance_score: float = 0.0
    start_offset: int = 0

@dataclass
class Claim:
    """A specific claim made in the synthesis."""
    text: str
    source_ids: List[str]
    confidence: str  # "high", "medium", "low"
    verification_status: str = "unverified"  # unverified, verified, refuted
