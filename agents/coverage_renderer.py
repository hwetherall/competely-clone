"""
Deterministic renderer for the "Coverage & Limitations" section of the
DeepDive Market Report.

Aggregates three views from the run JSON, with no LLM calls:
  1. What this report could not establish (the unknown cells, classified by reason)
  2. Where we used inferred ranges (the inferred numeric claims)
  3. What would unlock the next run (templated guidance based on observed gaps)

The output is a self-contained HTML <section> string ready to be slotted
into utils/generate_v2_report.py.
"""

from __future__ import annotations

import html as _html
import re
from typing import Any, Dict, Iterable, List, Tuple


# --- Data extraction -----------------------------------------------------

# Patterns that indicate a positioning-table cell is reporting an unknown.
_UNKNOWN_MARKERS = (
    "unknown",
    "n/a",
    "not disclosed",
    "not available",
    "not published",
    "confidential",
)

# Patterns that indicate an inferred numeric claim.
_INFERRED_MARKERS = (
    "[inferred]",
    "(inferred",
    "inferred ",
)


def _is_unknown_cell(value: Any) -> bool:
    if value is None:
        return False
    text = str(value).strip().lower()
    if not text:
        return False
    return any(m in text for m in _UNKNOWN_MARKERS)


def _is_inferred_cell(value: Any) -> bool:
    if value is None:
        return False
    text = str(value).strip().lower()
    return any(m in text for m in _INFERRED_MARKERS)


def _classify_unknown_reason(
    company: str,
    field: str,
    cell_text: str,
    competitor_type: str,
) -> str:
    text = (cell_text or "").lower()
    if competitor_type == "consulting_firm":
        return "Consulting-firm typology — no public terms page"
    if competitor_type == "opaque_enterprise_saas":
        return "Opaque enterprise SaaS — contact-sales only"
    if "pre-revenue" in text or "pre revenue" in text or "stealth" in text:
        return "Pre-revenue / no public signal"
    if "brand" in text and ("collision" in text or "conflated" in text):
        return "Brand-identity collision in search results"
    if "evidence gap" in text:
        return "Evidence gap — no source surfaced"
    return "Evidence gap"


def _competitor_type(profiles: Dict[str, Any], company: str) -> str:
    p = profiles.get(company) or {}
    if isinstance(p, dict):
        return p.get("type", "unknown")
    return getattr(p, "type", "unknown")


def collect_unknown_rows(
    analyses: Dict[str, Dict[str, Any]],
    parameter_definitions: Dict[str, Dict[str, Any]],
    competitor_profiles: Dict[str, Any],
) -> List[Dict[str, str]]:
    """One row per (company, parameter, field) cell that reports unknown."""
    rows: List[Dict[str, str]] = []
    for parameter_id, analysis in (analyses or {}).items():
        param_def = (parameter_definitions or {}).get(parameter_id, {}) or {}
        param_name = param_def.get("name", parameter_id)
        for entry in analysis.get("positioning_table", []) or []:
            company = str(entry.get("company", "")).strip()
            if not company:
                continue
            ctype = _competitor_type(competitor_profiles, company)
            for field, value in entry.items():
                if field in {"company", "position", "rank", "label", "trend"}:
                    continue
                if _is_unknown_cell(value):
                    rows.append({
                        "company": company,
                        "dimension": param_name,
                        "question": _humanise_field(field),
                        "reason": _classify_unknown_reason(company, field, str(value), ctype),
                    })
    return rows


def collect_inferred_rows(
    analyses: Dict[str, Dict[str, Any]],
    parameter_definitions: Dict[str, Dict[str, Any]],
) -> List[Dict[str, str]]:
    """One row per (company, parameter, field) cell that reports an inferred range."""
    rows: List[Dict[str, str]] = []
    for parameter_id, analysis in (analyses or {}).items():
        param_def = (parameter_definitions or {}).get(parameter_id, {}) or {}
        param_name = param_def.get("name", parameter_id)
        for entry in analysis.get("positioning_table", []) or []:
            company = str(entry.get("company", "")).strip()
            if not company:
                continue
            for field, value in entry.items():
                if not _is_inferred_cell(value):
                    continue
                method, confidence = _parse_inferred_method(str(value))
                rows.append({
                    "company": company,
                    "field": _humanise_field(field) + f" ({param_name})",
                    "inferred_range": _extract_range(str(value)),
                    "method": method,
                    "confidence": confidence,
                })
    return rows


def _humanise_field(field: str) -> str:
    return field.replace("_", " ").strip().capitalize() if field else field


_RANGE_RE = re.compile(r"\$?\s*[\d.,]+\s*(?:[KMB]|[a-z]+)?\s*[–—\-]\s*\$?\s*[\d.,]+\s*(?:[KMB]|[a-z]+)?", re.IGNORECASE)


def _extract_range(text: str) -> str:
    match = _RANGE_RE.search(text)
    if match:
        return match.group(0).strip()
    return text.strip()[:80]


def _parse_inferred_method(text: str) -> Tuple[str, str]:
    """Pull the method/confidence parenthetical, e.g. (... ; medium confidence)."""
    paren = re.search(r"\(([^)]*)\)", text)
    if not paren:
        return ("", "")
    inner = paren.group(1)
    confidence = ""
    for level in ("high", "medium", "low"):
        if f"{level} confidence" in inner.lower():
            confidence = level.capitalize()
            break
    method = inner
    if confidence:
        method = re.sub(rf"[;,]?\s*{confidence.lower()} confidence", "", method, flags=re.IGNORECASE).strip(" ;,")
    return (method.strip(), confidence)


# --- Rendering -----------------------------------------------------------

def _table_html(headers: Iterable[str], rows: Iterable[Iterable[str]]) -> str:
    head_html = "".join(
        f"<th class='px-3 py-2 text-left font-semibold'>{_html.escape(h)}</th>" for h in headers
    )
    body_rows: List[str] = []
    for row in rows:
        cells = "".join(f"<td class='px-3 py-2'>{_html.escape(str(v))}</td>" for v in row)
        body_rows.append(f"<tr class='border-b border-slate-100'>{cells}</tr>")
    body_html = "".join(body_rows) or "<tr><td class='px-3 py-2 text-slate-400' colspan='99'>None.</td></tr>"
    return (
        "<div class='mt-4 overflow-x-auto rounded-lg border border-slate-200'>"
        "<table class='min-w-full text-xs'>"
        f"<thead><tr class='bg-slate-50 text-slate-600'>{head_html}</tr></thead>"
        f"<tbody>{body_html}</tbody></table></div>"
    )


def _unlock_guidance(
    unknown_rows: List[Dict[str, str]],
    inferred_rows: List[Dict[str, str]],
) -> List[str]:
    items: List[str] = []
    typology_count: Dict[str, int] = {}
    for r in unknown_rows:
        typology_count[r["reason"]] = typology_count.get(r["reason"], 0) + 1
    if typology_count.get("Opaque enterprise SaaS — contact-sales only", 0) >= 3:
        items.append(
            "Direct API access to Vendr or Tegus would dramatically improve ACV signal "
            "for opaque enterprise SaaS players."
        )
    if typology_count.get("Consulting-firm typology — no public terms page", 0) >= 3:
        items.append(
            "A USAspending.gov scraper would give us anchored consulting-firm engagement "
            "values rather than benchmark inference."
        )
    if typology_count.get("Pre-revenue / no public signal", 0) >= 1:
        items.append(
            "A 30-day rerun on pre-revenue competitors may surface funding announcements "
            "that reset their evidence base."
        )
    if inferred_rows:
        items.append(
            f"{len(inferred_rows)} cells were filled by triangulated `inferred` ranges; "
            "validating each against a primary source would lift confidence to high."
        )
    if not items:
        items.append("No major coverage gaps detected — next run can focus on depth, not breadth.")
    return items


def render_coverage_and_limitations(
    analyses: Dict[str, Dict[str, Any]],
    parameter_definitions: Dict[str, Dict[str, Any]],
    competitor_profiles: Dict[str, Any] | None = None,
) -> str:
    """Return a self-contained HTML <section> for Coverage & Limitations.

    Returns an empty string if there are no unknowns or inferred claims to render.
    """
    profiles = competitor_profiles or {}
    unknown_rows = collect_unknown_rows(analyses or {}, parameter_definitions or {}, profiles)
    inferred_rows = collect_inferred_rows(analyses or {}, parameter_definitions or {})
    if not unknown_rows and not inferred_rows:
        return ""

    unknown_table = _table_html(
        ["Competitor", "Dimension", "Question", "Reason"],
        ((r["company"], r["dimension"], r["question"], r["reason"]) for r in unknown_rows[:80]),
    )
    inferred_table = _table_html(
        ["Competitor", "Field", "Inferred range", "Method", "Confidence"],
        ((r["company"], r["field"], r["inferred_range"], r["method"], r["confidence"]) for r in inferred_rows[:80]),
    )
    unlock_items = "".join(f"<li>{_html.escape(item)}</li>" for item in _unlock_guidance(unknown_rows, inferred_rows))

    return f"""
    <section id="coverage-limitations" class="mb-12 animate-fade-in">
        <div class="rounded-xl border border-slate-200 bg-white shadow-sm p-6 md:p-8">
            <h2 class="text-2xl font-display font-bold text-slate-900 mb-2">Coverage &amp; Limitations</h2>
            <p class="text-sm text-slate-600 mb-4">What this report could not establish, where we used inferred ranges, and what would unlock the next run.</p>

            <h3 class="text-sm font-semibold text-slate-500 uppercase tracking-wider mt-6 mb-2">What this report could not establish</h3>
            {unknown_table}

            <h3 class="text-sm font-semibold text-slate-500 uppercase tracking-wider mt-6 mb-2">Where we used inferred ranges</h3>
            {inferred_table}

            <h3 class="text-sm font-semibold text-slate-500 uppercase tracking-wider mt-6 mb-2">What would unlock the next run</h3>
            <ul class="list-disc pl-6 text-sm text-slate-700 space-y-1">{unlock_items}</ul>
        </div>
    </section>
    """
