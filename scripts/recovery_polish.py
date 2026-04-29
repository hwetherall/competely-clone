"""
Generic post-recovery polish for synthesis sections rebuilt from a checkpoint.

Per-parameter recovery scripts call into this module so that recovered
output matches a fresh-run schema:

  1. Regenerate the `rationale` field of every Top Rankings entry as a
     single sentence (no [S] markers, no ellipses, no truncated
     evidence_summary).
  2. Strip pipeline-internal columns from the positioning table
     (evidence_summary, saved_fact_count, confidence) and keep only the
     columns declared in PARAMETER_USER_FACING_COLUMNS for the parameter.
  3. Append a footnote indicating the section was reconstructed from a
     checkpoint, so a careful reader can always tell which sections were
     synthesized from scratch and which were recovered.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from config.variables import (
    PIPELINE_INTERNAL_COLUMNS,
    get_user_facing_columns,
)


_S_MARKER_RE = re.compile(r"\[S\d+\]")
_ELLIPSIS_RE = re.compile(r"\.{3,}|…")
_WS_RE = re.compile(r"\s+")
RECOVERY_FOOTNOTE_MARKER = "<!-- recovery-polish-footnote -->"


# --- Public API ----------------------------------------------------------

def polish_recovered_synthesis(
    parameter_id: str,
    recovered_section: Dict[str, Any],
    evidence_table: Optional[Dict[str, Any]] = None,
    recovery_timestamp: Optional[str] = None,
    rationale_rewriter: Optional[Callable[[str, str, str], str]] = None,
) -> Dict[str, Any]:
    """Post-process a recovered synthesis section so it matches a fresh-run schema.

    Args:
        parameter_id:        e.g. "inv_takeaway_for_innovera"
        recovered_section:   the analyses[parameter_id] dict from the checkpoint
        evidence_table:      the saved per-company evidence table; passed to the
                             rewriter so it has facts to work from
        recovery_timestamp:  ISO timestamp; defaults to now
        rationale_rewriter:  optional callable(label, evidence_summary, company)
                             returning a single-sentence rationale. If omitted,
                             a deterministic sanitiser is used (no LLM call).

    Returns the polished section. Mutates a copy, does not modify the input.
    """
    polished = dict(recovered_section)
    timestamp = recovery_timestamp or datetime.utcnow().strftime("%Y-%m-%d")
    rewriter = rationale_rewriter or _default_rationale_rewriter

    polished["rankings"] = _regenerate_rankings(
        recovered_section.get("rankings", []) or [],
        evidence_table or {},
        rewriter,
    )
    polished["positioning_table"] = _strip_internal_columns(
        recovered_section.get("positioning_table", []) or [],
        parameter_id,
    )
    polished["full_report_markdown"] = _append_recovery_footnote(
        recovered_section.get("full_report_markdown", "") or "",
        timestamp,
    )
    polished.setdefault("metadata", {})
    if isinstance(polished["metadata"], dict):
        polished["metadata"]["recovered_from_checkpoint"] = True
        polished["metadata"]["recovery_timestamp"] = timestamp
    return polished


# --- Step 1: rankings rationale ------------------------------------------

def _regenerate_rankings(
    rankings: List[Dict[str, Any]],
    evidence_table: Dict[str, Any],
    rewriter: Callable[[str, str, str], str],
) -> List[Dict[str, Any]]:
    new_rankings: List[Dict[str, Any]] = []
    for entry in rankings:
        cleaned = dict(entry)
        company = str(entry.get("company", ""))
        label = str(entry.get("label", ""))
        rationale = str(entry.get("rationale", ""))
        if _looks_like_pipeline_artifact(rationale):
            evidence_summary = _evidence_summary_for(evidence_table, company)
            try:
                cleaned["rationale"] = rewriter(label, evidence_summary, company).strip()
            except Exception:
                cleaned["rationale"] = _sanitise_rationale(rationale, label, evidence_summary)
        else:
            cleaned["rationale"] = _sanitise_rationale(rationale, label, "")
        new_rankings.append(cleaned)
    return new_rankings


def _looks_like_pipeline_artifact(text: str) -> bool:
    if not text:
        return False
    return bool(_S_MARKER_RE.search(text)) or bool(_ELLIPSIS_RE.search(text))


def _evidence_summary_for(evidence_table: Dict[str, Any], company: str) -> str:
    """Pick the first 1-2 facts/passages we have for a company."""
    if not evidence_table:
        return ""
    by_company = evidence_table.get("by_company") or evidence_table
    entry = (by_company or {}).get(company) or {}
    facts = entry.get("facts") or []
    if facts:
        first = " ".join(str(f.get("claim", "") if isinstance(f, dict) else f) for f in facts[:2])
        if first:
            return first
    return str(entry.get("evidence_summary", ""))[:400]


def _sanitise_rationale(rationale: str, label: str, evidence_summary: str) -> str:
    """Deterministic fallback when no LLM rewriter is provided."""
    base = rationale or evidence_summary or label
    base = _S_MARKER_RE.sub("", base)
    base = _ELLIPSIS_RE.sub(" ", base)
    base = _WS_RE.sub(" ", base).strip(" -—,;:")
    if not base:
        return label or ""
    # Keep to a single sentence.
    sentences = re.split(r"(?<=[.!?])\s+", base)
    out = sentences[0].strip()
    if not out.endswith((".", "!", "?")):
        out += "."
    return out


def _default_rationale_rewriter(label: str, evidence_summary: str, company: str) -> str:
    """No-LLM default that produces a plausible single sentence."""
    if evidence_summary:
        return _sanitise_rationale(evidence_summary, label, "")
    if label:
        return f"{company}: {label}."
    return f"{company} ranked from saved evidence."


# --- Step 2: strip pipeline-internal columns ----------------------------

def _strip_internal_columns(
    table: List[Dict[str, Any]],
    parameter_id: str,
) -> List[Dict[str, Any]]:
    keep = set(get_user_facing_columns(parameter_id))
    drop = set(PIPELINE_INTERNAL_COLUMNS)
    cleaned: List[Dict[str, Any]] = []
    for row in table:
        if not isinstance(row, dict):
            continue
        new_row: Dict[str, Any] = {}
        for k, v in row.items():
            if k in drop:
                continue
            if keep and k not in keep:
                continue
            new_row[k] = v
        # If the keep filter dropped everything, fall back to dropping internals only.
        if not new_row:
            new_row = {k: v for k, v in row.items() if k not in drop}
        cleaned.append(new_row)
    return cleaned


# --- Step 3: footnote ----------------------------------------------------

def _append_recovery_footnote(markdown: str, timestamp: str) -> str:
    if RECOVERY_FOOTNOTE_MARKER in markdown:
        return markdown
    footnote = (
        f"\n\n---\n\n"
        f"{RECOVERY_FOOTNOTE_MARKER}\n"
        f"*This section was reconstructed from a mid-run checkpoint on "
        f"{timestamp}. The evidence table is intact; the narrative and "
        f"rankings were regenerated from the saved evidence.*\n"
    )
    return markdown.rstrip() + footnote
