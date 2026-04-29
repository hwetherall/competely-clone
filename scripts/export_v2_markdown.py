"""
Export a V2 run JSON into a readable Markdown report.

Usage:
    python scripts/export_v2_markdown.py data/results/v2_run_20260428_173648.json
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List


def _load_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _clean(text: Any) -> str:
    if text is None:
        return ""
    return str(text).strip()


def _one_line(text: Any) -> str:
    return re.sub(r"\s+", " ", _clean(text))


def _fmt_date(value: str) -> str:
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%B %d, %Y")
    except ValueError:
        return value


def _escape_cell(value: Any) -> str:
    text = _one_line(value)
    text = text.replace("|", "\\|")
    return text or "-"


def _heading_for_param(param_id: str, definitions: Dict[str, Dict[str, Any]]) -> str:
    definition = definitions.get(param_id, {})
    name = definition.get("name", param_id)
    category = definition.get("category", "Uncategorized")
    return f"{name} ({category})"


def _bullet_list(items: Iterable[Any], empty: str = "None noted.") -> List[str]:
    cleaned = [_one_line(item) for item in items if _one_line(item)]
    if not cleaned:
        return [empty]
    return [f"- {item}" for item in cleaned]


def _render_positioning_table(rows: List[Dict[str, Any]], max_columns: int = 6) -> List[str]:
    if not rows:
        return ["No positioning table available."]

    preferred = ["company", "position", "trend", "evidence_summary", "key_metrics", "confidence"]
    keys = [key for key in preferred if any(key in row for row in rows)]
    for row in rows:
        for key in row.keys():
            if key not in keys:
                keys.append(key)
            if len(keys) >= max_columns:
                break
        if len(keys) >= max_columns:
            break

    lines = [
        "| " + " | ".join(keys) + " |",
        "| " + " | ".join("---" for _ in keys) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_escape_cell(row.get(key, "")) for key in keys) + " |")
    return lines


def _render_rankings(rankings: List[Dict[str, Any]], limit: int = 10) -> List[str]:
    if not rankings:
        return ["No ranking available."]
    lines = []
    for item in rankings[:limit]:
        rank = item.get("rank", "")
        company = item.get("company", "")
        label = item.get("label", "")
        rationale = item.get("rationale", "")
        prefix = f"{rank}. {company}" if rank else company
        detail = " - ".join(part for part in [_one_line(label), _one_line(rationale)] if part)
        lines.append(f"- **{prefix}**: {detail}" if detail else f"- **{prefix}**")
    return lines


def _render_sources(sources: List[Dict[str, Any]], limit: int = 12) -> List[str]:
    if not sources:
        return ["No sources listed."]
    lines = []
    seen: set[str] = set()
    for source in sources:
        url = _clean(source.get("url"))
        title = _one_line(source.get("title")) or url or source.get("source_id", "Source")
        if not url or url in seen:
            continue
        seen.add(url)
        tier = _one_line(source.get("tier"))
        label = f"{title} ({tier})" if tier else title
        lines.append(f"- [{label}]({url})")
        if len(lines) >= limit:
            break
    return lines or ["No source URLs listed."]


def export_markdown(data: Dict[str, Any]) -> str:
    run_id = data.get("run_id", "v2_run")
    timestamp = _fmt_date(data.get("timestamp", ""))
    companies = data.get("companies", [])
    parameters = data.get("parameters", [])
    definitions = data.get("parameter_definitions", {})
    analyses = data.get("analyses", {})
    executive = data.get("executive", {})
    metadata = data.get("metadata", {})
    coverage = metadata.get("coverage_check", {})
    research_synthesis = data.get("research_synthesis", {})

    lines: List[str] = [
        "# Innovera Competitive Intelligence Report",
        "",
        f"**Run ID:** `{run_id}`",
        f"**Generated:** {timestamp or 'Unknown'}",
        f"**Companies covered:** {len(companies)}",
        f"**Research dimensions:** {len(parameters)}",
        "",
        "## Executive Brief",
        "",
        _clean(executive.get("brief")) or "No executive brief available.",
        "",
    ]

    if executive.get("key_themes"):
        lines.extend(["### Key Themes", "", *_bullet_list(executive.get("key_themes", [])), ""])
    if executive.get("trends"):
        lines.extend(["### Cross-Market Trends", "", *_bullet_list(executive.get("trends", [])), ""])

    opportunities = executive.get("white_space_opportunities", []) or []
    if opportunities:
        lines.extend(["### White-Space Opportunities", ""])
        for item in opportunities:
            opportunity = _one_line(item.get("opportunity"))
            why = _one_line(item.get("why_it_exists"))
            closest = _one_line(item.get("who_is_closest"))
            difficulty = _one_line(item.get("entry_difficulty"))
            lines.append(f"- **{opportunity or 'Opportunity'}**: {why}")
            if closest or difficulty:
                lines.append(f"  Closest player: {closest or 'Unknown'}; entry difficulty: {difficulty or 'Unknown'}.")
        lines.append("")

    next_steps = executive.get("next_steps", {}) or {}
    if next_steps:
        lines.extend(["### Recommended Next Steps", ""])
        for bucket, items in next_steps.items():
            if not items:
                continue
            title = bucket.replace("_", " ").title()
            lines.append(f"**{title}**")
            for item in items:
                action = _one_line(item.get("action"))
                rationale = _one_line(item.get("rationale"))
                priority = _one_line(item.get("priority"))
                lines.append(f"- {action} ({priority or 'Priority TBD'}): {rationale}")
            lines.append("")

    lines.extend([
        "## Scope",
        "",
        "### Companies",
        "",
        ", ".join(companies),
        "",
        "### Dimensions",
        "",
    ])
    for param_id in parameters:
        lines.append(f"- {_heading_for_param(param_id, definitions)}")
    lines.append("")

    if coverage:
        lines.extend([
            "## Commercial Coverage",
            "",
            f"- Total checks: {coverage.get('total_checks', 'n/a')}",
            f"- Covered checks: {coverage.get('covered_checks', 'n/a')}",
            f"- Gap count: {coverage.get('gap_count', 'n/a')}",
            "",
        ])

    if research_synthesis:
        lines.extend(["## Research Synthesis", ""])
        for qa in research_synthesis.get("key_questions_answers", []) or []:
            lines.extend([
                f"### {_one_line(qa.get('question'))}",
                "",
                _clean(qa.get("answer")) or "No answer available.",
                "",
            ])
        hypothesis = _clean(research_synthesis.get("hypothesis_validation"))
        if hypothesis:
            lines.extend(["### Hypothesis Validation", "", hypothesis, ""])

    lines.extend(["## Findings By Dimension", ""])
    for param_id in parameters:
        analysis = analyses.get(param_id, {}) or {}
        lines.extend([
            f"### {_heading_for_param(param_id, definitions)}",
            "",
            f"**Headline:** {_clean(analysis.get('headline')) or 'No headline available.'}",
            "",
            f"**Executive Summary:** {_clean(analysis.get('executive_summary')) or 'No summary available.'}",
            "",
            "**Top Rankings**",
            "",
            *_render_rankings(analysis.get("rankings", []), limit=10),
            "",
        ])

        trends = analysis.get("trends", []) or []
        if trends:
            lines.extend(["**Trends**", "", *_bullet_list(trends), ""])
        white_space = analysis.get("white_space", []) or []
        if white_space:
            lines.extend(["**White Space**", "", *_bullet_list(white_space), ""])

        lines.extend(["**Positioning Table**", "", *_render_positioning_table(analysis.get("positioning_table", [])), ""])

        full_report = _clean(analysis.get("full_report_markdown"))
        if full_report:
            lines.extend(["**Detailed Narrative**", "", full_report, ""])

        lines.extend(["**Selected Sources**", "", *_render_sources(analysis.get("sources", [])), ""])

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a V2 run JSON to Markdown")
    parser.add_argument("json_path", help="Path to V2 run JSON")
    parser.add_argument("--output", help="Optional Markdown output path")
    args = parser.parse_args()

    json_path = Path(args.json_path)
    data = _load_json(json_path)
    output_path = Path(args.output) if args.output else json_path.with_suffix(".md")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(export_markdown(data), encoding="utf-8")
    print(f"V2 Markdown report written: {output_path}")


if __name__ == "__main__":
    main()
