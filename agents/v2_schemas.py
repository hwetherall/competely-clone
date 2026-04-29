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
class CompetitorProfile:
    """
    Commercial profile for one competitor.

    Produced once per competitor before the normal V2 gather loop and used to
    route commercial research.
    """
    competitor: str
    type: str = "unknown"
    has_pricing_page: bool = False
    has_terms_page: bool = False
    is_public: bool = False
    homepage_url: str = ""
    key_pages: Dict[str, Optional[str]] = field(default_factory=dict)
    confidence: str = "low"
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "competitor": self.competitor,
            "type": self.type,
            "has_pricing_page": self.has_pricing_page,
            "has_terms_page": self.has_terms_page,
            "is_public": self.is_public,
            "homepage_url": self.homepage_url,
            "key_pages": self.key_pages,
            "confidence": self.confidence,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CompetitorProfile":
        return cls(
            competitor=data.get("competitor", ""),
            type=data.get("type", "unknown"),
            has_pricing_page=bool(data.get("has_pricing_page", False)),
            has_terms_page=bool(data.get("has_terms_page", False)),
            is_public=bool(data.get("is_public", False)),
            homepage_url=data.get("homepage_url", ""),
            key_pages=data.get("key_pages", {}) or {},
            confidence=data.get("confidence", "low"),
            notes=data.get("notes", ""),
        )


@dataclass
class CommercialExtract:
    """Structured commercial facts extracted once per competitor."""
    competitor: str
    data: Dict[str, Any] = field(default_factory=dict)
    extracted_from_urls: List[str] = field(default_factory=list)
    pricing_disclosure: str = "opaque"
    status: str = "not_run"
    error: str = ""
    tokens_used: int = 0
    cached: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "competitor": self.competitor,
            "data": self.data,
            "extracted_from_urls": self.extracted_from_urls,
            "pricing_disclosure": self.pricing_disclosure,
            "status": self.status,
            "error": self.error,
            "tokens_used": self.tokens_used,
            "cached": self.cached,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CommercialExtract":
        return cls(
            competitor=data.get("competitor", ""),
            data=data.get("data", {}) or {},
            extracted_from_urls=list(data.get("extracted_from_urls", []) or []),
            pricing_disclosure=data.get("pricing_disclosure", "opaque"),
            status=data.get("status", "not_run"),
            error=data.get("error", ""),
            tokens_used=int(data.get("tokens_used", 0) or 0),
            cached=bool(data.get("cached", False)),
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
class WhiteSpaceOpportunity:
    """
    A structured white-space opportunity (Option B view).

    Attributes:
        opportunity: What is the gap?
        why_it_exists: What structural dynamics create this opening?
        who_is_closest: Which existing player is best positioned to capture it?
        entry_difficulty: How hard would it be to fill this gap? (Low/Medium/High)
    """
    opportunity: str = ""
    why_it_exists: str = ""
    who_is_closest: str = ""
    entry_difficulty: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "opportunity": self.opportunity,
            "why_it_exists": self.why_it_exists,
            "who_is_closest": self.who_is_closest,
            "entry_difficulty": self.entry_difficulty,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WhiteSpaceOpportunity":
        return cls(
            opportunity=data.get("opportunity", ""),
            why_it_exists=data.get("why_it_exists", ""),
            who_is_closest=data.get("who_is_closest", ""),
            entry_difficulty=data.get("entry_difficulty", ""),
        )


@dataclass
class NextStepItem:
    """
    A single next-step recommendation within a workstream bucket.

    Attributes:
        action: What to do
        rationale: Why (tied back to a finding/white space)
        priority: High / Medium / Low
    """
    action: str = ""
    rationale: str = ""
    priority: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "rationale": self.rationale,
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NextStepItem":
        return cls(
            action=data.get("action", ""),
            rationale=data.get("rationale", ""),
            priority=data.get("priority", ""),
        )


@dataclass
class ExecutiveBrief:
    """
    Landscape-level executive summary.
    Output of Phase 4 (Executive).

    Attributes:
        brief: The "30-second read" paragraph
        key_themes: Cross-cutting strategic themes
        trends: Cross-cutting directional shifts
        white_space_opportunities: Structured opportunities (Option B)
        white_space_matrix: Category-organized gaps (Option C): segment_gaps, product_gaps, business_model_gaps, geographic_gaps
        next_steps: Workstream buckets -> list of NextStepItems: investigate_further, quick_wins, strategic_bets, monitor_and_defend
        venture_context: Optional user-supplied venture description used to personalize white space and next steps
        metadata: Model, tokens, etc.
    """
    brief: str = ""
    key_themes: List[str] = field(default_factory=list)
    trends: List[str] = field(default_factory=list)
    white_space_opportunities: List[WhiteSpaceOpportunity] = field(default_factory=list)
    white_space_matrix: Dict[str, List[str]] = field(default_factory=dict)
    next_steps: Dict[str, List[NextStepItem]] = field(default_factory=dict)
    venture_context: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    # AVIS-specific analytical frameworks (empty for Competely path)
    moat_analysis_grid: List[Dict[str, Any]] = field(default_factory=list)
    threat_matrix: List[Dict[str, Any]] = field(default_factory=list)
    value_curve_assessment: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "brief": self.brief,
            "key_themes": self.key_themes,
            "trends": self.trends,
            "white_space_opportunities": [o.to_dict() for o in self.white_space_opportunities],
            "white_space_matrix": self.white_space_matrix,
            "next_steps": {
                bucket: [item.to_dict() for item in items]
                for bucket, items in self.next_steps.items()
            },
            "venture_context": self.venture_context,
            "metadata": self.metadata,
        }
        if self.moat_analysis_grid:
            d["moat_analysis_grid"] = self.moat_analysis_grid
        if self.threat_matrix:
            d["threat_matrix"] = self.threat_matrix
        if self.value_curve_assessment:
            d["value_curve_assessment"] = self.value_curve_assessment
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutiveBrief":
        return cls(
            brief=data.get("brief", ""),
            key_themes=data.get("key_themes", []),
            trends=data.get("trends", []),
            white_space_opportunities=[
                WhiteSpaceOpportunity.from_dict(o)
                for o in data.get("white_space_opportunities", [])
            ],
            white_space_matrix=data.get("white_space_matrix", {}),
            next_steps={
                bucket: [NextStepItem.from_dict(item) for item in items]
                for bucket, items in data.get("next_steps", {}).items()
            },
            venture_context=data.get("venture_context", ""),
            metadata=data.get("metadata", {}),
            moat_analysis_grid=data.get("moat_analysis_grid", []),
            threat_matrix=data.get("threat_matrix", []),
            value_curve_assessment=data.get("value_curve_assessment", {}),
        )


@dataclass
class KeyQuestionAnswer:
    """
    Answer to a key research question.
    """
    question: str
    answer: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question": self.question,
            "answer": self.answer,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KeyQuestionAnswer":
        return cls(
            question=data.get("question", ""),
            answer=data.get("answer", ""),
        )


@dataclass
class ResearchSynthesis:
    """
    Synthesis of research findings against the original plan.
    """
    key_questions_answers: List[KeyQuestionAnswer] = field(default_factory=list)
    hypothesis_validation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key_questions_answers": [a.to_dict() for a in self.key_questions_answers],
            "hypothesis_validation": self.hypothesis_validation,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResearchSynthesis":
        return cls(
            key_questions_answers=[KeyQuestionAnswer.from_dict(a) for a in data.get("key_questions_answers", [])],
            hypothesis_validation=data.get("hypothesis_validation", ""),
        )


@dataclass
class GraveyardCompany:
    """A company that has collapsed or ceased operations in the sector."""
    name: str
    years_active: str = ""
    peak_description: str = ""
    reason_summary: str = ""
    confidence: str = "medium"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "years_active": self.years_active,
            "peak_description": self.peak_description,
            "reason_summary": self.reason_summary,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraveyardCompany":
        return cls(
            name=data.get("name", ""),
            years_active=data.get("years_active", ""),
            peak_description=data.get("peak_description", ""),
            reason_summary=data.get("reason_summary", ""),
            confidence=data.get("confidence", "medium"),
        )


@dataclass
class CautionaryNarrative:
    """Per-company mini-narrative: who they were, why they failed, the lesson."""
    company: str
    peak_position: str = ""
    failure_mode: str = ""
    narrative: str = ""
    key_lesson: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "company": self.company,
            "peak_position": self.peak_position,
            "failure_mode": self.failure_mode,
            "narrative": self.narrative,
            "key_lesson": self.key_lesson,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CautionaryNarrative":
        return cls(
            company=data.get("company", ""),
            peak_position=data.get("peak_position", ""),
            failure_mode=data.get("failure_mode", ""),
            narrative=data.get("narrative", ""),
            key_lesson=data.get("key_lesson", ""),
        )


@dataclass
class RiskOverlay:
    """Links a main-report white-space opportunity to historical failure precedent."""
    white_space_opportunity: str = ""
    historical_precedent: str = ""
    risk_level: str = "Medium"
    mitigation_guidance: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "white_space_opportunity": self.white_space_opportunity,
            "historical_precedent": self.historical_precedent,
            "risk_level": self.risk_level,
            "mitigation_guidance": self.mitigation_guidance,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RiskOverlay":
        return cls(
            white_space_opportunity=data.get("white_space_opportunity", ""),
            historical_precedent=data.get("historical_precedent", ""),
            risk_level=data.get("risk_level", "Medium"),
            mitigation_guidance=data.get("mitigation_guidance", ""),
        )


@dataclass
class PostMortemBrief:
    """
    Landscape-level post-mortem intelligence report from failed companies.
    Produced by the graveyard pipeline's executive phase + merge phase.
    """
    failure_patterns: List[str] = field(default_factory=list)
    structural_vulnerabilities: List[str] = field(default_factory=list)
    cautionary_narratives: List[CautionaryNarrative] = field(default_factory=list)
    risk_overlays: List[RiskOverlay] = field(default_factory=list)
    survival_principles: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "failure_patterns": self.failure_patterns,
            "structural_vulnerabilities": self.structural_vulnerabilities,
            "cautionary_narratives": [n.to_dict() for n in self.cautionary_narratives],
            "risk_overlays": [r.to_dict() for r in self.risk_overlays],
            "survival_principles": self.survival_principles,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PostMortemBrief":
        return cls(
            failure_patterns=data.get("failure_patterns", []),
            structural_vulnerabilities=data.get("structural_vulnerabilities", []),
            cautionary_narratives=[
                CautionaryNarrative.from_dict(n)
                for n in data.get("cautionary_narratives", [])
            ],
            risk_overlays=[
                RiskOverlay.from_dict(r)
                for r in data.get("risk_overlays", [])
            ],
            survival_principles=data.get("survival_principles", []),
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
        research_synthesis: ResearchSynthesis (as dict)
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
    research_synthesis: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    graveyard_companies: List[Dict[str, Any]] = field(default_factory=list)
    graveyard_intelligence: Dict[str, Dict[str, Dict[str, Any]]] = field(default_factory=dict)
    graveyard_analyses: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    postmortem_brief: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "companies": self.companies,
            "parameters": self.parameters,
            "parameter_definitions": self.parameter_definitions,
            "intelligence": self.intelligence,
            "analyses": self.analyses,
            "executive": self.executive,
            "research_synthesis": self.research_synthesis,
            "metadata": self.metadata,
        }
        if self.graveyard_companies:
            d["graveyard_companies"] = self.graveyard_companies
        if self.graveyard_intelligence:
            d["graveyard_intelligence"] = self.graveyard_intelligence
        if self.graveyard_analyses:
            d["graveyard_analyses"] = self.graveyard_analyses
        if self.postmortem_brief:
            d["postmortem_brief"] = self.postmortem_brief
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "V2RunResult":
        return cls(
            run_id=data.get("run_id", ""),
            timestamp=data.get("timestamp", ""),
            companies=data.get("companies", []),
            parameters=data.get("parameters", []),
            parameter_definitions=data.get("parameter_definitions", {}),
            intelligence=data.get("intelligence", {}),
            analyses=data.get("analyses", {}),
            executive=data.get("executive", {}),
            research_synthesis=data.get("research_synthesis", {}),
            metadata=data.get("metadata", {}),
            graveyard_companies=data.get("graveyard_companies", []),
            graveyard_intelligence=data.get("graveyard_intelligence", {}),
            graveyard_analyses=data.get("graveyard_analyses", {}),
            postmortem_brief=data.get("postmortem_brief", {}),
        )
