"""
Structured data schemas for evidence-grounded research.

This module defines dataclasses for:
- EvidenceSource: A source document with scoring
- EvidencePassage: An extracted passage from a source
- Claim: A synthesized claim with citations
- ExtractedNumber: A number extracted for verification
- VerificationResult: Result of number verification
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class DiscoveryTargetProfile(BaseModel):
    """Target company/profile for competitor discovery."""
    company_name: str = Field(default="Innovera")
    description: str = ""
    website: Optional[str] = None
    industry: Optional[str] = None
    audience: Optional[str] = None
    notes: Optional[str] = None

    def to_prompt(self) -> str:
        parts = [f"Company: {self.company_name}"]
        if self.industry:
            parts.append(f"Industry: {self.industry}")
        if self.website:
            parts.append(f"Website: {self.website}")
        if self.audience:
            parts.append(f"Audience: {self.audience}")
        if self.description:
            parts.append(f"Description: {self.description}")
        if self.notes:
            parts.append(f"Notes: {self.notes}")
        return "\n".join(parts)


class CompetitorCandidate(BaseModel):
    name: str
    canonical_domain: Optional[str] = None
    framings: List[Literal["direct", "problem_sharer", "category_sharer", "adjacency"]] = []
    rationales: Dict[str, str] = {}
    evidence_urls: List[str] = []
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    discovered_at: datetime


class DiscoveryRun(BaseModel):
    id: str
    target_profile: DiscoveryTargetProfile
    framing_seeds: Dict[str, str]
    candidates: List[CompetitorCandidate] = []
    status: Literal["running", "complete", "failed"] = "running"
    created_at: datetime
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error: Optional[str] = None


@dataclass
class EvidenceSource:
    """
    A source document used as evidence.
    
    Attributes:
        source_id: Unique identifier (S1, S2, etc.)
        url: Full URL of the source
        title: Page title
        domain: Extracted domain name
        source_score: Quality score from 0-1
        is_official: Whether this is an official company source
        tier: Source tier ("official", "tier1_news", "regulatory", "general", "low_quality")
        fetched_at: When the page was fetched (if applicable)
        content_type: MIME type of the content
    """
    source_id: str
    url: str
    title: str
    domain: str
    source_score: float
    is_official: bool = False
    tier: str = "general"
    fetched_at: Optional[str] = None
    content_type: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "url": self.url,
            "title": self.title,
            "domain": self.domain,
            "source_score": self.source_score,
            "is_official": self.is_official,
            "tier": self.tier,
            "fetched_at": self.fetched_at,
            "content_type": self.content_type,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidenceSource":
        return cls(
            source_id=data.get("source_id", ""),
            url=data.get("url", ""),
            title=data.get("title", ""),
            domain=data.get("domain", ""),
            source_score=data.get("source_score", 0.0),
            is_official=data.get("is_official", False),
            tier=data.get("tier", "general"),
            fetched_at=data.get("fetched_at"),
            content_type=data.get("content_type"),
        )


@dataclass
class EvidencePassage:
    """
    An extracted passage from a source document.
    
    Attributes:
        source_id: Reference to parent EvidenceSource
        passage_id: Unique identifier within source (P1, P2, etc.)
        text: The passage text
        start_offset: Character offset in original document (optional)
        relevance_score: How relevant this passage is to the query
    """
    source_id: str
    passage_id: str
    text: str
    start_offset: Optional[int] = None
    relevance_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "passage_id": self.passage_id,
            "text": self.text,
            "start_offset": self.start_offset,
            "relevance_score": self.relevance_score,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidencePassage":
        return cls(
            source_id=data.get("source_id", ""),
            passage_id=data.get("passage_id", ""),
            text=data.get("text", ""),
            start_offset=data.get("start_offset"),
            relevance_score=data.get("relevance_score", 0.0),
        )


@dataclass
class Claim:
    """
    A synthesized claim with source citations.
    
    Attributes:
        text: The claim text
        source_ids: List of source IDs supporting this claim
        confidence: Confidence level ("high", "medium", "low")
    """
    text: str
    source_ids: List[str] = field(default_factory=list)
    confidence: str = "medium"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "source_ids": self.source_ids,
            "confidence": self.confidence,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Claim":
        return cls(
            text=data.get("text", ""),
            source_ids=data.get("source_ids", []),
            confidence=data.get("confidence", "medium"),
        )


@dataclass
class ExtractedNumber:
    """
    A number extracted from text for verification.
    
    Attributes:
        value: The raw string value (e.g., "$1.4 trillion", "42%")
        number_type: Type of number ("currency", "percentage", "count", "date", "other")
        context: Surrounding text for context
        position: Character position in original text
    """
    value: str
    number_type: str
    context: str = ""
    position: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "number_type": self.number_type,
            "context": self.context,
            "position": self.position,
        }


@dataclass
class VerificationResult:
    """
    Result of verifying a number against evidence.
    
    Attributes:
        number: The ExtractedNumber being verified
        is_supported: Whether the number was found in evidence
        supporting_passages: Passage IDs that support this number
        confidence: Confidence in the verification
    """
    number: ExtractedNumber
    is_supported: bool
    supporting_passages: List[str] = field(default_factory=list)
    confidence: str = "low"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "number": self.number.to_dict(),
            "is_supported": self.is_supported,
            "supporting_passages": self.supporting_passages,
            "confidence": self.confidence,
        }


@dataclass
class SourceScore:
    """
    Result of scoring a URL for source quality.
    
    Attributes:
        score: Overall quality score from 0-1
        domain: Extracted domain
        is_official: Whether this is an official company domain
        tier: Source tier classification
        freshness_boost: Boost applied for recent content
        penalties: List of penalties applied
    """
    score: float
    domain: str
    is_official: bool = False
    tier: str = "general"
    freshness_boost: float = 0.0
    penalties: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "domain": self.domain,
            "is_official": self.is_official,
            "tier": self.tier,
            "freshness_boost": self.freshness_boost,
            "penalties": self.penalties,
        }


@dataclass
class PageContent:
    """
    Fetched and extracted page content.
    
    Attributes:
        url: Original URL
        final_url: Final URL after redirects
        status: HTTP status code
        title: Extracted page title
        text: Extracted text content
        excerpt: Short excerpt/summary
        fetched_at: Timestamp of fetch
        content_type: MIME type
        error: Error message if fetch failed
    """
    url: str
    final_url: str = ""
    status: int = 0
    title: str = ""
    text: str = ""
    excerpt: str = ""
    fetched_at: str = ""
    content_type: str = ""
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "final_url": self.final_url,
            "status": self.status,
            "title": self.title,
            "text": self.text,
            "excerpt": self.excerpt,
            "fetched_at": self.fetched_at,
            "content_type": self.content_type,
            "error": self.error,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PageContent":
        return cls(
            url=data.get("url", ""),
            final_url=data.get("final_url", ""),
            status=data.get("status", 0),
            title=data.get("title", ""),
            text=data.get("text", ""),
            excerpt=data.get("excerpt", ""),
            fetched_at=data.get("fetched_at", ""),
            content_type=data.get("content_type", ""),
            error=data.get("error"),
        )
    
    @property
    def is_success(self) -> bool:
        """Check if the page was successfully fetched."""
        return self.status == 200 and not self.error and len(self.text) > 0


@dataclass
class EvidencePack:
    """
    A complete evidence pack for synthesis.
    
    Attributes:
        sources: List of evidence sources
        passages: List of evidence passages
        total_chars: Total character count of all passages
        avg_source_score: Average source quality score
    """
    sources: List[EvidenceSource] = field(default_factory=list)
    passages: List[EvidencePassage] = field(default_factory=list)
    total_chars: int = 0
    avg_source_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "sources": [s.to_dict() for s in self.sources],
            "passages": [p.to_dict() for p in self.passages],
            "total_chars": self.total_chars,
            "avg_source_score": self.avg_source_score,
        }
    
    def get_source_by_id(self, source_id: str) -> Optional[EvidenceSource]:
        """Get a source by its ID."""
        for source in self.sources:
            if source.source_id == source_id:
                return source
        return None
    
    def get_passages_for_source(self, source_id: str) -> List[EvidencePassage]:
        """Get all passages for a given source."""
        return [p for p in self.passages if p.source_id == source_id]
    
    def format_for_prompt(self) -> str:
        """Format the evidence pack for use in an LLM prompt."""
        lines = []
        for source in self.sources:
            lines.append(f"[{source.source_id}] {source.title} — {source.url} — (score={source.source_score:.2f})")
            for passage in self.get_passages_for_source(source.source_id):
                # Indent passages under their source
                text_preview = passage.text[:500] + "..." if len(passage.text) > 500 else passage.text
                lines.append(f"  ({passage.passage_id}) {text_preview}")
            lines.append("")
        return "\n".join(lines)


@dataclass
class SynthesisResult:
    """
    Result of the synthesis step.
    
    Attributes:
        comprehensive_markdown: The full synthesized answer with citations
        claims: List of claims with source citations
        gaps: List of information gaps identified
        raw_response: The raw LLM response (for debugging)
        parse_error: Error message if JSON parsing failed
    """
    comprehensive_markdown: str = ""
    claims: List[Claim] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)
    raw_response: str = ""
    parse_error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "comprehensive_markdown": self.comprehensive_markdown,
            "claims": [c.to_dict() for c in self.claims],
            "gaps": self.gaps,
            "raw_response": self.raw_response,
            "parse_error": self.parse_error,
        }


@dataclass 
class ResearchMetadata:
    """
    Rich metadata about the research process.
    
    Attributes:
        iterations: Number of research iterations
        searches: Total number of searches performed
        pages_fetched: Number of pages successfully fetched
        pages_failed: Number of page fetches that failed
        evidence_sources_used: Number of sources in final evidence pack
        avg_source_score: Average quality score of sources used
        model_used: Primary model used for synthesis
        total_evidence_chars: Total characters of evidence
        unsupported_numbers_found: Count of numbers not found in evidence
        verification_applied: Whether numeric verification was applied
    """
    iterations: int = 0
    searches: int = 0
    pages_fetched: int = 0
    pages_failed: int = 0
    evidence_sources_used: int = 0
    avg_source_score: float = 0.0
    model_used: str = ""
    total_evidence_chars: int = 0
    unsupported_numbers_found: int = 0
    verification_applied: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "iterations": self.iterations,
            "searches": self.searches,
            "pages_fetched": self.pages_fetched,
            "pages_failed": self.pages_failed,
            "evidence_sources_used": self.evidence_sources_used,
            "avg_source_score": self.avg_source_score,
            "model_used": self.model_used,
            "total_evidence_chars": self.total_evidence_chars,
            "unsupported_numbers_found": self.unsupported_numbers_found,
            "verification_applied": self.verification_applied,
        }
