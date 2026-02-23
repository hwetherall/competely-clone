"""
Chat context builder for the "Chat with Results" feature.

Builds a two-tier context from a V2 run JSON:
  - Tier 1 (condensed): always included in the system prompt
  - Tier 2 (selective): appended per-message when the user asks about
    specific companies or parameters
"""

import re
from typing import Dict, List, Optional


def build_condensed_context(data: dict) -> str:
    """
    Build a condensed markdown summary of the entire run for the system prompt.

    Includes: companies, parameter definitions, executive brief, key themes,
    trends, white-space opportunities, next steps, per-parameter summaries
    (headline + executive_summary + rankings + confidence), and post-mortem
    highlights.  Targets ~20-30 K tokens.
    """
    parts: list[str] = []

    companies = data.get("companies", [])
    parameters = data.get("parameters", [])
    param_defs = data.get("parameter_definitions", {})
    analyses = data.get("analyses", {})
    executive = data.get("executive", {})
    postmortem = data.get("postmortem_brief", {})
    graveyard_cos = data.get("graveyard_companies", [])
    graveyard_analyses = data.get("graveyard_analyses", {})

    # -- Header --
    parts.append("# Competitive Intelligence Report\n")
    parts.append(f"**Companies analyzed:** {', '.join(companies)}\n")
    parts.append(f"**Parameters analyzed ({len(parameters)}):** "
                 + ", ".join(param_defs.get(p, {}).get("name", p) for p in parameters)
                 + "\n")

    # -- Executive brief --
    brief = executive.get("brief", "")
    if brief:
        parts.append("## Executive Brief\n")
        parts.append(brief + "\n")

    # -- Key themes --
    themes = executive.get("key_themes", [])
    if themes:
        parts.append("## Key Themes\n")
        for i, t in enumerate(themes, 1):
            parts.append(f"{i}. {t}")
        parts.append("")

    # -- Trends --
    trends = executive.get("trends", [])
    if trends:
        parts.append("## Trends\n")
        for i, t in enumerate(trends, 1):
            parts.append(f"{i}. {t}")
        parts.append("")

    # -- White-space opportunities --
    ws = executive.get("white_space_opportunities", [])
    if ws:
        parts.append("## White-Space Opportunities\n")
        for i, opp in enumerate(ws, 1):
            parts.append(
                f"{i}. **{opp.get('opportunity', '')}** "
                f"(difficulty: {opp.get('entry_difficulty', '?')})\n"
                f"   Why: {opp.get('why_it_exists', '')}\n"
                f"   Closest: {opp.get('who_is_closest', '')}"
            )
        parts.append("")

    # -- Next steps --
    next_steps = executive.get("next_steps", {})
    if next_steps:
        parts.append("## Next Steps\n")
        for bucket, items in next_steps.items():
            if not items:
                continue
            label = bucket.replace("_", " ").title()
            parts.append(f"### {label}\n")
            for item in items:
                action = item.get("action", "")
                rationale = item.get("rationale", "")
                priority = item.get("priority", "")
                parts.append(f"- [{priority}] {action}")
                if rationale:
                    parts.append(f"  Rationale: {rationale}")
        parts.append("")

    # -- Per-parameter summaries --
    parts.append("## Parameter Summaries\n")
    for pid in parameters:
        a = analyses.get(pid, {})
        name = param_defs.get(pid, {}).get("name", pid)
        cat = param_defs.get(pid, {}).get("category", "")
        headline = a.get("headline", "")
        exec_sum = a.get("executive_summary", "")
        conf = a.get("confidence", "unknown")
        rankings = a.get("rankings", [])

        parts.append(f"### {name} ({cat}) — confidence: {conf}\n")
        if headline:
            parts.append(f"**Headline:** {headline}\n")
        if exec_sum:
            parts.append(f"{exec_sum}\n")
        if rankings:
            parts.append("Rankings:")
            for r in rankings:
                lbl = f" — {r['label']}" if r.get("label") else ""
                parts.append(f"  {r.get('rank')}. {r.get('company', '')}{lbl}")
            parts.append("")

    # -- Post-mortem highlights --
    if postmortem:
        parts.append("## Post-Mortem Intelligence\n")
        gy_names = [
            c.get("name", str(c)) if isinstance(c, dict) else str(c)
            for c in graveyard_cos
        ]
        if gy_names:
            parts.append(f"**Failed companies studied:** {', '.join(gy_names)}\n")

        fp = postmortem.get("failure_patterns", [])
        if fp:
            parts.append("### Failure Patterns\n")
            for p in fp:
                parts.append(f"- {p}")
            parts.append("")

        sv = postmortem.get("structural_vulnerabilities", [])
        if sv:
            parts.append("### Structural Vulnerabilities\n")
            for v in sv:
                parts.append(f"- {v}")
            parts.append("")

        sp = postmortem.get("survival_principles", [])
        if sp:
            parts.append("### Survival Principles\n")
            for i, p in enumerate(sp, 1):
                parts.append(f"{i}. {p}")
            parts.append("")

        cn = postmortem.get("cautionary_narratives", [])
        if cn:
            parts.append("### Cautionary Narratives\n")
            for n in cn:
                parts.append(
                    f"- **{n.get('company', '')}** ({n.get('failure_mode', '')}): "
                    f"{n.get('narrative', '')[:300]}…\n"
                    f"  Key lesson: {n.get('key_lesson', '')}"
                )
            parts.append("")

    # -- Graveyard parameter summaries --
    if graveyard_analyses:
        parts.append("## Graveyard Parameter Summaries\n")
        for gpid, ga in graveyard_analyses.items():
            name = ga.get("parameter_name", gpid)
            headline = ga.get("headline", "")
            exec_sum = ga.get("executive_summary", "")
            conf = ga.get("confidence", "unknown")
            parts.append(f"### {name} — confidence: {conf}\n")
            if headline:
                parts.append(f"**Headline:** {headline}\n")
            if exec_sum:
                parts.append(f"{exec_sum}\n")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Tier 2: selective retrieval
# ---------------------------------------------------------------------------

_LEGAL_SUFFIXES = re.compile(
    r",?\s*\b(Inc\.?|LLC|Ltd\.?|Co\.?|Corp\.?|Corporation|"
    r"Incorporated|Company|Stores|Entertainment)\b[.,]*\s*",
    re.IGNORECASE,
)


def _normalize(text: str) -> str:
    return _LEGAL_SUFFIXES.sub("", text).strip().rstrip(",. ").lower()


def _build_search_keys(companies: List[str]) -> Dict[str, str]:
    """Map lowercase search keys → original company name."""
    keys: Dict[str, str] = {}
    for c in companies:
        keys[c.lower()] = c
        clean = _normalize(c)
        if clean:
            keys[clean] = c
            first = clean.split()[0]
            if first and len(first) > 3:
                keys[first] = c
    return keys


def _detect_companies(query: str, companies: List[str]) -> List[str]:
    q_lower = query.lower()
    search_keys = _build_search_keys(companies)
    matched = set()
    for key, original in search_keys.items():
        if re.search(r"(?<!\w)" + re.escape(key) + r"(?!\w)", q_lower):
            matched.add(original)
    return list(matched)


def _detect_parameters(
    query: str,
    parameters: List[str],
    param_defs: Dict[str, dict],
) -> List[str]:
    q_lower = query.lower()
    matched = []
    for pid in parameters:
        pdef = param_defs.get(pid, {})
        name = pdef.get("name", pid).lower()
        if name in q_lower or pid.replace("_", " ") in q_lower:
            matched.append(pid)
    return matched


def get_relevant_sections(
    data: dict,
    query: str,
    history: Optional[List[Dict[str, str]]] = None,
) -> str:
    """
    Return full-depth context for companies/parameters mentioned in the query.

    Scans the latest few messages in *history* as well so follow-up questions
    that use pronouns ("tell me more about them") still retrieve context from
    the entity mentioned a turn or two earlier.
    """
    companies = data.get("companies", [])
    parameters = data.get("parameters", [])
    param_defs = data.get("parameter_definitions", {})
    intelligence = data.get("intelligence", {})
    analyses = data.get("analyses", {})
    graveyard_analyses = data.get("graveyard_analyses", {})
    graveyard_cos = data.get("graveyard_companies", [])

    combined_text = query
    if history:
        recent = history[-4:]
        combined_text += " " + " ".join(m.get("content", "") for m in recent)

    matched_cos = _detect_companies(combined_text, companies)
    gy_names = [
        c.get("name", str(c)) if isinstance(c, dict) else str(c)
        for c in graveyard_cos
    ]
    matched_gy = _detect_companies(combined_text, gy_names)
    matched_params = _detect_parameters(combined_text, parameters, param_defs)
    gy_param_ids = list(graveyard_analyses.keys())
    matched_gy_params = _detect_parameters(combined_text, gy_param_ids, {
        pid: {"name": ga.get("parameter_name", pid)}
        for pid, ga in graveyard_analyses.items()
    })

    if not matched_cos and not matched_params and not matched_gy and not matched_gy_params:
        return ""

    parts: list[str] = []
    parts.append("---\n## Additional Detail (retrieved for this question)\n")

    # Full analysis markdown for matched parameters
    for pid in matched_params:
        a = analyses.get(pid, {})
        name = param_defs.get(pid, {}).get("name", pid)
        full_md = a.get("full_report_markdown", "")
        if full_md:
            parts.append(f"### Full Analysis: {name}\n")
            parts.append(full_md[:8000])
            parts.append("")

        sources = a.get("sources", [])
        if sources:
            parts.append(f"#### Sources for {name}\n")
            for s in sources[:10]:
                title = s.get("title", s.get("url", ""))
                url = s.get("url", "")
                parts.append(f"- [{title}]({url})")
            parts.append("")

    # Intelligence facts for matched companies
    for co in matched_cos:
        co_intel = intelligence.get(co, {})
        if not co_intel:
            continue
        parts.append(f"### Intelligence Facts: {co}\n")
        count = 0
        for pid, cell in co_intel.items():
            if count > 40:
                break
            facts = cell.get("facts", [])
            if facts:
                pname = param_defs.get(pid, {}).get("name", pid)
                parts.append(f"**{pname}:**")
                for f in facts[:5]:
                    claim = f.get("claim", "")
                    parts.append(f"- {claim}")
                    count += 1
        parts.append("")

    # Graveyard analyses for matched graveyard params
    for gpid in matched_gy_params:
        ga = graveyard_analyses.get(gpid, {})
        full_md = ga.get("full_report_markdown", "")
        if full_md:
            parts.append(f"### Graveyard Analysis: {ga.get('parameter_name', gpid)}\n")
            parts.append(full_md[:6000])
            parts.append("")

    return "\n".join(parts)
