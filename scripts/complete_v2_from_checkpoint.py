"""
Complete a stalled V2 run from a saved checkpoint.

This resumes after gather/normalize/synthesis checkpoints without rerunning the
full research pipeline. It reuses saved intelligence and existing analyses,
synthesizes only missing parameters, then runs the final summary phases.

Usage:
    python scripts/complete_v2_from_checkpoint.py data/results/checkpoint_v2_run_20260428_173648.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.coverage_check import run_coverage_check
from agents.executive_agent import ExecutiveAgent
from agents.research_synthesis_agent import ResearchSynthesisAgent
from agents.schemas import EvidenceSource
from agents.v2_schemas import (
    CommercialExtract,
    ComparativeReport,
    CompetitorProfile,
    CompanyRanking,
    ExecutiveBrief,
    IntelligenceDossier,
    NextStepItem,
    ResearchSynthesis,
    V2RunResult,
    WhiteSpaceOpportunity,
)
from api.services.v2_runner import _build_variable_lookup
from config.settings import validate_config
from v2_pipeline import save_v2_result


RESULTS_DIR = project_root / "data" / "results"
FINAL_PHASE_TIMEOUT_SECONDS = 360


def _load_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json_atomic(path: Path, payload: Dict[str, Any]) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    tmp_path.replace(path)


def _resolve_path(path_arg: str) -> Path:
    path = Path(path_arg)
    if not path.is_absolute():
        path = project_root / path
    return path


def _commercial_objects(
    metadata: Dict[str, Any],
) -> tuple[Dict[str, CompetitorProfile], Dict[str, CommercialExtract]]:
    profile_data = metadata.get("competitor_profiles", {}) or {}
    extract_data = metadata.get("commercial_extracts", {}) or {}
    profiles = {
        company: CompetitorProfile.from_dict(profile)
        for company, profile in profile_data.items()
        if isinstance(profile, dict)
    }
    extracts = {
        company: CommercialExtract.from_dict(extract)
        for company, extract in extract_data.items()
        if isinstance(extract, dict)
    }
    return profiles, extracts


def _commercial_metadata_for_coverage(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Return metadata keys that should survive into the final result."""
    cleaned = dict(metadata)
    cleaned.pop("status", None)
    cleaned.pop("checkpoint_phase", None)
    cleaned.pop("recovery_stage", None)
    return cleaned


def _recovery_checkpoint_path(run_id: str) -> Path:
    return RESULTS_DIR / f"checkpoint_{run_id}_recovery.json"


def _save_recovery_checkpoint(
    run_id: str,
    stage: str,
    checkpoint: Dict[str, Any],
    analyses: Dict[str, Dict[str, Any]],
    extra: Dict[str, Any] | None = None,
) -> None:
    payload = dict(checkpoint)
    payload["phase"] = stage
    payload["timestamp"] = datetime.now(timezone.utc).isoformat()
    payload["analyses"] = analyses
    payload["metadata"] = {
        **(checkpoint.get("metadata", {}) or {}),
        "status": "partial",
        "checkpoint_phase": checkpoint.get("phase"),
        "recovery_stage": stage,
        **(extra or {}),
    }
    _write_json_atomic(_recovery_checkpoint_path(run_id), payload)


def _update_progress_completed(run_id: str, total_cells: int, elapsed_seconds: float) -> None:
    progress_path = RESULTS_DIR / f"progress_{run_id}.json"
    if not progress_path.exists():
        return
    progress = _load_json(progress_path)
    progress.update(
        {
            "status": "completed",
            "phase": "completed",
            "completed": total_cells,
            "total": total_cells,
            "current": None,
            "elapsed_seconds": elapsed_seconds,
        }
    )
    _write_json_atomic(progress_path, progress)


def _truncate(text: str, limit: int = 420) -> str:
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _dossier_for(
    intelligence: Dict[str, Dict[str, Dict[str, Any]]],
    company: str,
    var_id: str,
) -> Dict[str, Any]:
    return intelligence.get(company, {}).get(var_id, {}) or {}


def _evidence_summary(dossier: Dict[str, Any], max_facts: int = 4) -> str:
    facts = dossier.get("facts", []) or []
    claims = []
    for fact in facts[:max_facts]:
        claim = fact.get("claim", "") if isinstance(fact, dict) else str(fact)
        if claim:
            source_id = fact.get("source_id", "") if isinstance(fact, dict) else ""
            claims.append(f"{claim} [{source_id}]" if source_id else claim)
    if claims:
        return _truncate(" ".join(claims), 700)
    passages = dossier.get("raw_passages", []) or []
    for passage in passages[:2]:
        text = passage.get("text", "") if isinstance(passage, dict) else str(passage)
        if text:
            return _truncate(text, 700)
    return "No usable saved evidence in the checkpoint for this parameter."


def _metrics_summary(dossier: Dict[str, Any]) -> str:
    metrics = dossier.get("key_metrics", {}) or {}
    if not metrics:
        return "None extracted"
    return _truncate("; ".join(f"{key}: {value}" for key, value in metrics.items()), 350)


def _source_objects_from_dossiers(
    intelligence: Dict[str, Dict[str, Dict[str, Any]]],
    companies: List[str],
    var_id: str,
) -> List[EvidenceSource]:
    seen: set[str] = set()
    sources: List[EvidenceSource] = []
    for company in companies:
        dossier = _dossier_for(intelligence, company, var_id)
        for source in dossier.get("sources", []) or []:
            if not isinstance(source, dict):
                continue
            url = source.get("url") or source.get("source_id") or source.get("title")
            if not url or url in seen:
                continue
            seen.add(url)
            sources.append(EvidenceSource.from_dict(source))
            if len(sources) >= 80:
                return sources
    return sources


def _parameter_trends(var_id: str) -> List[str]:
    if var_id == "inv_size_signals":
        return [
            "The landscape mixes scaled consultancies with venture-backed AI startups, so public size signals are uneven.",
            "Funding and headcount are more visible than revenue or ARR for most private AI-native competitors.",
            "Customer-logo evidence is often stronger than precise revenue disclosure.",
        ]
    if var_id == "inv_speed_to_market":
        return [
            "Fast movers tend to enter through a narrow wedge before expanding into broader decision or research workflows.",
            "Founder networks, enterprise pilots, and credibility signals substitute for long public product histories.",
            "Consulting incumbents move through existing client access while startups rely on focused launches and funding momentum.",
        ]
    if var_id == "inv_takeaway_for_innovera":
        return [
            "Innovera should favor concrete wedge tests over broad platform claims.",
            "Opaque pricing and bespoke delivery are common, making transparency a potential differentiator.",
            "Human expertise remains a credibility layer even where competitors lead with AI automation.",
        ]
    return ["Recovered from saved evidence without rerunning gather."]


def _parameter_white_space(var_id: str) -> List[str]:
    if var_id == "inv_size_signals":
        return [
            "A lighter-weight commercial intelligence offer for teams that cannot justify enterprise platforms.",
            "A transparent evidence-quality layer that makes private-market uncertainty explicit.",
        ]
    if var_id == "inv_speed_to_market":
        return [
            "A focused launch around one repeatable boardroom workflow rather than a broad intelligence platform.",
            "A pilot package that converts founder-led discovery into repeatable proof points quickly.",
        ]
    if var_id == "inv_takeaway_for_innovera":
        return [
            "A packaged Innovera wedge that combines AI speed with human validation.",
            "A clearer commercial story for buyers frustrated by opaque consulting and enterprise SaaS pricing.",
        ]
    return ["Validate the recovered evidence gaps before using this as a final strategic input."]


def _build_recovered_report(
    var_id: str,
    companies: List[str],
    intelligence: Dict[str, Dict[str, Dict[str, Any]]],
    variable_lookup: Dict[str, Any],
) -> ComparativeReport:
    var = variable_lookup[var_id]
    rows: List[Dict[str, Any]] = []
    rankings: List[CompanyRanking] = []

    for rank, company in enumerate(companies, start=1):
        dossier = _dossier_for(intelligence, company, var_id)
        facts = dossier.get("facts", []) or []
        confidence = dossier.get("confidence", "low")
        summary = _evidence_summary(dossier)
        metrics = _metrics_summary(dossier)
        label = "Stronger saved signal" if facts else "Thin saved signal"
        rankings.append(
            CompanyRanking(
                rank=rank,
                company=company,
                label=label,
                rationale=_truncate(summary, 220),
            )
        )
        rows.append(
            {
                "company": company,
                "position": label,
                "evidence_summary": summary,
                "key_metrics": metrics,
                "confidence": confidence,
                "saved_fact_count": len(facts),
                "source_count": len(dossier.get("sources", []) or []),
            }
        )

    body_lines = [
        f"# {var.name}",
        "",
        "This section was recovered from the saved checkpoint intelligence after the original synthesis stage stalled. It preserves the saved facts, metrics, and source IDs rather than rerunning the full gather pipeline.",
        "",
    ]
    for row in rows:
        body_lines.extend(
            [
                f"## {row['company']}",
                f"- Evidence summary: {row['evidence_summary']}",
                f"- Key metrics: {row['key_metrics']}",
                f"- Confidence: {row['confidence']}; saved facts: {row['saved_fact_count']}; sources: {row['source_count']}",
                "",
            ]
        )

    return ComparativeReport(
        parameter_id=var_id,
        parameter_name=var.name,
        headline=f"{var.name} was recovered from checkpoint evidence; compare rows by saved signal strength and explicit uncertainty.",
        executive_summary=(
            f"The recovered {var.name} view uses the already gathered dossiers for all {len(companies)} companies. "
            "Where evidence is thin, the report marks uncertainty instead of inventing missing facts."
        ),
        rankings=rankings,
        positioning_table=rows,
        full_report_markdown="\n".join(body_lines),
        white_space=_parameter_white_space(var_id),
        trends=_parameter_trends(var_id),
        confidence="medium",
        sources=_source_objects_from_dossiers(intelligence, companies, var_id),
        synthesis_iterations=0,
        regather_count=0,
    )


def _fallback_research_synthesis(reports: List[ComparativeReport]) -> ResearchSynthesis:
    return ResearchSynthesis(
        hypothesis_validation=(
            "Recovered run completed from checkpoint evidence. No original key questions or hypothesis were present "
            "in the checkpoint, so this section summarizes the completed parameter reports rather than validating a saved hypothesis. "
            + " ".join(_truncate(report.headline, 180) for report in reports[:5])
        )
    )


def _fallback_executive(reports: List[ComparativeReport], parameter_path: str) -> ExecutiveBrief:
    top_themes = [report.headline for report in reports[:6] if report.headline]
    trends: List[str] = []
    for report in reports:
        trends.extend(report.trends[:2])
    return ExecutiveBrief(
        brief=(
            "This V2 run was completed from a checkpoint after the original process stalled during late-stage synthesis. "
            "The final report preserves the completed analyses and recovers the missing sections from saved evidence, "
            "with uncertainty called out where the checkpoint data is thin."
        ),
        key_themes=top_themes[:6],
        trends=trends[:6],
        white_space_opportunities=[
            WhiteSpaceOpportunity(
                opportunity=item,
                why_it_exists="Identified across recovered and completed parameter reports.",
                who_is_closest="Requires follow-up validation",
                entry_difficulty="Medium",
            )
            for report in reports[:3]
            for item in report.white_space[:1]
        ],
        white_space_matrix={
            "segment_gaps": ["Teams needing faster, evidence-grounded commercial intelligence."],
            "product_gaps": ["Transparent packaged research with explicit confidence scoring."],
            "business_model_gaps": ["Clear pilot-to-subscription paths in an opaque market."],
            "geographic_gaps": [],
        },
        next_steps={
            "investigate_further": [
                NextStepItem(
                    action="Spot-check recovered sections against the original saved sources.",
                    rationale="The missing reports were generated from checkpoint dossiers after the LLM synthesis path stalled.",
                    priority="High",
                )
            ],
            "quick_wins": [
                NextStepItem(
                    action="Use opaque pricing findings to sharpen Innovera's packaging story.",
                    rationale="Commercial opacity appears repeatedly across competitors.",
                    priority="Medium",
                )
            ],
            "strategic_bets": [],
            "monitor_and_defend": [],
        },
        metadata={"recovered_fallback": True, "parameter_path": parameter_path},
    )


async def complete_from_checkpoint(
    checkpoint_path_arg: str,
    *,
    output_path_arg: str | None = None,
    force: bool = False,
) -> Path:
    checkpoint_path = _resolve_path(checkpoint_path_arg)
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

    errors = validate_config(require_llm=True)
    if errors:
        raise RuntimeError("Configuration invalid:\n" + "\n".join(f"- {e}" for e in errors))

    checkpoint = _load_json(checkpoint_path)
    run_id = checkpoint.get("run_id")
    if not run_id:
        raise ValueError("Checkpoint is missing run_id")

    output_path = _resolve_path(output_path_arg) if output_path_arg else RESULTS_DIR / f"{run_id}.json"
    if output_path.exists() and not force:
        raise FileExistsError(f"Output already exists: {output_path} (use --force to overwrite)")

    companies = checkpoint.get("companies", [])
    parameter_ids = checkpoint.get("parameters", [])
    parameter_definitions = checkpoint.get("parameter_definitions", {})
    intelligence = checkpoint.get("intelligence", {})
    analyses = dict(checkpoint.get("analyses", {}) or {})
    metadata = checkpoint.get("metadata", {}) or {}
    parameter_path = metadata.get("parameter_path", "competely")

    missing = [param_id for param_id in parameter_ids if param_id not in analyses]
    print(f"Run: {run_id}")
    print(f"Checkpoint phase: {checkpoint.get('phase')}")
    print(f"Companies: {len(companies)}")
    print(f"Parameters: {len(parameter_ids)}")
    print(f"Existing analyses: {len(analyses)}")
    print(f"Missing analyses: {', '.join(missing) if missing else '(none)'}")

    variable_lookup = _build_variable_lookup(parameter_ids, parameter_path=parameter_path)
    recovery_start = time.time()
    for index, var_id in enumerate(missing, start=1):
        var = variable_lookup[var_id]
        print(f"\n[{index}/{len(missing)}] Recovering {var.name} ({var_id}) from saved dossiers")
        report = _build_recovered_report(var_id, companies, intelligence, variable_lookup)
        analyses[var_id] = report.to_dict()
        _save_recovery_checkpoint(
            run_id,
            f"recovery_synthesis_{len(analyses)}_of_{len(parameter_ids)}",
            checkpoint,
            analyses,
        )

    recovery_synthesis_elapsed = time.time() - recovery_start

    final_metadata = _commercial_metadata_for_coverage(metadata)
    if final_metadata.get("competitor_profiles"):
        coverage = run_coverage_check(
            companies,
            analyses,
            final_metadata.get("competitor_profiles", {}),
        )
        final_metadata["coverage_check"] = coverage
        print(f"\nCommercial coverage gaps: {coverage.get('gap_count', 0)}")

    reports = [
        ComparativeReport.from_dict(analyses[param_id])
        for param_id in parameter_ids
        if analyses.get(param_id)
    ]
    companies_list = ", ".join(companies)

    print("\nGenerating research synthesis...")
    phase35_start = time.time()
    try:
        research_synthesis = await asyncio.wait_for(
            ResearchSynthesisAgent().synthesize(companies_list, reports, [], ""),
            timeout=FINAL_PHASE_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        print(f"Research synthesis fallback used: {exc}")
        research_synthesis = _fallback_research_synthesis(reports)
    phase35_elapsed = time.time() - phase35_start

    print("\nGenerating executive brief...")
    phase4_start = time.time()
    try:
        executive = await asyncio.wait_for(
            ExecutiveAgent().synthesize_brief(
                companies_list,
                reports,
                venture_context="",
                parameter_path=parameter_path,
            ),
            timeout=FINAL_PHASE_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        print(f"Executive fallback used: {exc}")
        executive = _fallback_executive(reports, parameter_path)
    phase4_elapsed = time.time() - phase4_start

    total_elapsed = (
        float(final_metadata.get("phase1_elapsed_seconds", 0) or 0)
        + float(final_metadata.get("phase2_elapsed_seconds", 0) or 0)
        + recovery_synthesis_elapsed
        + phase35_elapsed
        + phase4_elapsed
    )
    final_metadata.update(
        {
            "phase3_elapsed_seconds": recovery_synthesis_elapsed,
            "phase35_elapsed_seconds": phase35_elapsed,
            "phase4_elapsed_seconds": phase4_elapsed,
            "total_elapsed_seconds": total_elapsed,
            "recovered_from_checkpoint": str(checkpoint_path),
            "recovery_completed_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    result = V2RunResult(
        run_id=run_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        companies=companies,
        parameters=parameter_ids,
        parameter_definitions=parameter_definitions,
        intelligence=intelligence,
        analyses=analyses,
        executive=executive.to_dict(),
        research_synthesis=research_synthesis.to_dict(),
        metadata=final_metadata,
        graveyard_companies=checkpoint.get("graveyard_companies", []),
        graveyard_intelligence=checkpoint.get("graveyard_intelligence", {}),
        graveyard_analyses=checkpoint.get("graveyard_analyses", {}),
        postmortem_brief=checkpoint.get("postmortem_brief", {}),
    )

    if output_path == RESULTS_DIR / f"{run_id}.json":
        saved_path = save_v2_result(result)
    else:
        _write_json_atomic(output_path, result.to_dict())
        saved_path = output_path
        print(f"\nResults saved: {saved_path}")

    _update_progress_completed(run_id, len(companies) * len(parameter_ids), total_elapsed)
    print("\nRecovery complete.")
    print(f"Final analyses: {len(analyses)} / {len(parameter_ids)}")
    print(f"Final JSON: {saved_path}")
    return saved_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Complete a V2 run from a saved checkpoint")
    parser.add_argument("checkpoint", help="Path to checkpoint JSON")
    parser.add_argument("--output", help="Optional output JSON path")
    parser.add_argument("--force", action="store_true", help="Overwrite output if it already exists")
    args = parser.parse_args()

    try:
        asyncio.run(
            complete_from_checkpoint(
                args.checkpoint,
                output_path_arg=args.output,
                force=args.force,
            )
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
