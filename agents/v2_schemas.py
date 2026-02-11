"""
V2 Relational Competitive Intelligence Engine - Data schemas.

Defines dataclasses for:
- FactItem: A single structured fact extracted during gather
- IntelligenceDossier: Per-company, per-parameter gathered intelligence
- DataGap: Missing data identified during normalization
- NormalizedDataset: Parameter-level normalized comparison data
- CompanyRanking: One company's rank and label in a parameter report
- ComparativeReport: Full comparative analysis per parameter
- ExecutiveBrief: Landscape-level executive summary
- V2RunResult: Complete V2 run output
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from agents.schemas import EvidenceSource, EvidencePassage


@dataclass
class FactItem:
    """
    A single structured fact extracted from evidence during gather phase.

    Attributes:
        claim: The factual claim text
        source_id: Reference to EvidenceSource (e.g. S1, S2)
        confidence: high, medium, or low
    """
    claim: str
    source_id: str = ""
    confidence: str = "medium"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim": self.claim,
            "source_id": self.source_id,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FactItem":
        return cls(
            claim=data.get("claim", ""),
            source_id=data.get("source_id", ""),
            confidence=data.get("confidence", "medium"),
        )


@dataclass
class IntelligenceDossier:
    """
    Gathered intelligence for one (company, parameter) pair.
    Output of Phase 1 (Gather).

    Attributes:
        company: Company name
        parameter_id: Variable/parameter ID
        parameter_name: Human-readable parameter name
        facts: Structured factual extractions
        key_metrics: Key-value metrics (e.g. base_rate -> "2.9% + 30c")
        raw_passages: Evidence passages (reuse EvidencePassage)
        sources: Evidence sources (reuse EvidenceSource)
        confidence: high, medium, or low
        metadata: Searches, pages fetched, iterations, etc.
    """
    company: str
    parameter_id: str
    parameter_name: str
    facts: List[FactItem] = field(default_factory=list)
    key_metrics: Dict[str, str] = field(default_factory=dict)
    raw_passages: List[EvidencePassage] = field(default_factory=list)
    sources: List[EvidenceSource] = field(default_factory=list)
    confidence: str = "low"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "company": self.company,
            "parameter_id": self.parameter_id,
            "parameter_name": self.parameter_name,
            "facts": [f.to_dict() for f in self.facts],
            "key_metrics": self.key_metrics,
            "raw_passages": [p.to_dict() for p in self.raw_passages],
            "sources": [s.to_dict() for s in self.sources],
            "confidence": self.confidence,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IntelligenceDossier":
        return cls(
            company=data.get("company", ""),
            parameter_id=data.get("parameter_id", ""),
            parameter_name=data.get("parameter_name", ""),
            facts=[FactItem.from_dict(f) for f in data.get("facts", [])],
            key_metrics=data.get("key_metrics", {}),
            raw_passages=[EvidencePassage.from_dict(p) for p in data.get("raw_passages", [])],
            sources=[EvidenceSource.from_dict(s) for s in data.get("sources", [])],
            confidence=data.get("confidence", "low"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class DataGap:
    """
    A gap in data identified during normalization.

    Attributes:
        company: Company for which data is missing
        field_or_topic: Schema field or topic that is missing
        description: Human-readable description of the gap
    """
    company: str
    field_or_topic: str
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "company": self.company,
            "field_or_topic": self.field_or_topic,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DataGap":
        return cls(
            company=data.get("company", ""),
            field_or_topic=data.get("field_or_topic", ""),
            description=data.get("description", ""),
        )


@dataclass
class NormalizedDataset:
    """
    Normalized comparison data for one parameter across all companies.
    Output of Phase 2 (Normalize).

    Attributes:
        parameter_id: Variable/parameter ID
        parameter_name: Human-readable parameter name
        schema_fields: Comparison dimensions (e.g. base_rate, enterprise_rate)
        company_data: company -> {field: value}
        data_gaps: Identified gaps
        raw_dossiers: Preserved dossiers for synthesis context (serialized as dicts)
    """
    parameter_id: str
    parameter_name: str
    schema_fields: List[str] = field(default_factory=list)
    company_data: Dict[str, Dict[str, str]] = field(default_factory=dict)
    data_gaps: List[DataGap] = field(default_factory=list)
    raw_dossiers: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parameter_id": self.parameter_id,
            "parameter_name": self.parameter_name,
            "schema_fields": self.schema_fields,
            "company_data": self.company_data,
            "data_gaps": [g.to_dict() for g in self.data_gaps],
            "raw_dossiers": self.raw_dossiers,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NormalizedDataset":
        return cls(
            parameter_id=data.get("parameter_id", ""),
            parameter_name=data.get("parameter_name", ""),
            schema_fields=data.get("schema_fields", []),
            company_data=data.get("company_data", {}),
            data_gaps=[DataGap.from_dict(g) for g in data.get("data_gaps", [])],
            raw_dossiers=data.get("raw_dossiers", {}),
        )


@dataclass
class CompanyRanking:
    """
    One company's rank and label in a parameter report.

    Attributes:
        rank: 1-based rank
        company: Company name
        label: Short label (e.g. "SMB Price Leader")
        rationale: One-line rationale
    """
    rank: int
    company: str
    label: str = ""
    rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rank": self.rank,
            "company": self.company,
            "label": self.label,
            "rationale": self.rationale,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CompanyRanking":
        return cls(
            rank=data.get("rank", 0),
            company=data.get("company", ""),
            label=data.get("label", ""),
            rationale=data.get("rationale", ""),
        )


@dataclass
class ComparativeReport:
    """
    Full comparative analysis for one parameter.
    Output of Phase 3 (Synthesize).

    Attributes:
        parameter_id: Variable/parameter ID
        parameter_name: Human-readable parameter name
        headline: 1-2 sentence verdict
        executive_summary: 2-3 sentences
        rankings: Ordered list of company rankings
        positioning_table: List of dicts (company -> field -> value)
        full_report_markdown: 1000-2000 word narrative
        white_space: Unoccupied strategic opportunities
        trends: Directional observations
        confidence: high, medium, or low
        sources: Aggregated evidence sources
        synthesis_iterations: Number of synthesis loops
        regather_count: Number of re-gather rounds
    """
    parameter_id: str
    parameter_name: str
    headline: str = ""
    executive_summary: str = ""
    rankings: List[CompanyRanking] = field(default_factory=list)
    positioning_table: List[Dict[str, Any]] = field(default_factory=list)
    full_report_markdown: str = ""
    white_space: List[str] = field(default_factory=list)
    trends: List[str] = field(default_factory=list)
    confidence: str = "medium"
    sources: List[EvidenceSource] = field(default_factory=list)
    synthesis_iterations: int = 0
    regather_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parameter_id": self.parameter_id,
            "parameter_name": self.parameter_name,
            "headline": self.headline,
            "executive_summary": self.executive_summary,
            "rankings": [r.to_dict() for r in self.rankings],
            "positioning_table": self.positioning_table,
            "full_report_markdown": self.full_report_markdown,
            "white_space": self.white_space,
            "trends": self.trends,
            "confidence": self.confidence,
            "sources": [s.to_dict() for s in self.sources],
            "synthesis_iterations": self.synthesis_iterations,
            "regather_count": self.regather_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ComparativeReport":
        return cls(
            parameter_id=data.get("parameter_id", ""),
            parameter_name=data.get("parameter_name", ""),
            headline=data.get("headline", ""),
            executive_summary=data.get("executive_summary", ""),
            rankings=[CompanyRanking.from_dict(r) for r in data.get("rankings", [])],
            positioning_table=data.get("positioning_table", []),
            full_report_markdown=data.get("full_report_markdown", ""),
            white_space=data.get("white_space", []),
            trends=data.get("trends", []),
            confidence=data.get("confidence", "medium"),
            sources=[EvidenceSource.from_dict(s) for s in data.get("sources", [])],
            synthesis_iterations=data.get("synthesis_iterations", 0),
            regather_count=data.get("regather_count", 0),
        )


@dataclass
class ExecutiveBrief:
    """
    Landscape-level executive summary.
    Output of Phase 4 (Executive).

    Attributes:
        brief: The "30-second read" paragraph
        key_themes: Cross-cutting strategic themes
        metadata: Model, tokens, etc.
    """
    brief: str = ""
    key_themes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "brief": self.brief,
            "key_themes": self.key_themes,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutiveBrief":
        return cls(
            brief=data.get("brief", ""),
            key_themes=data.get("key_themes", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class V2RunResult:
    """
    Complete V2 run output for persistence and report generation.

    Attributes:
        run_id: Unique run identifier
        timestamp: ISO timestamp
        companies: List of company names
        parameters: List of parameter IDs
        parameter_definitions: param_id -> {id, name, category}
        intelligence: company -> param_id -> IntelligenceDossier (as dict)
        analyses: param_id -> ComparativeReport (as dict)
        executive: ExecutiveBrief (as dict)
        metadata: Phase-level stats, duration, etc.
    """
    run_id: str
    timestamp: str
    companies: List[str]
    parameters: List[str]
    parameter_definitions: Dict[str, Dict[str, Any]]
    intelligence: Dict[str, Dict[str, Dict[str, Any]]]
    analyses: Dict[str, Dict[str, Any]]
    executive: Dict[str, Any]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "companies": self.companies,
            "parameters": self.parameters,
            "parameter_definitions": self.parameter_definitions,
            "intelligence": self.intelligence,
            "analyses": self.analyses,
            "executive": self.executive,
            "metadata": self.metadata,
        }
