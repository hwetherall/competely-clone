"""
V2 HTML Report Generator.

Produces a parameter-centric report: executive brief at top, parameter analysis
cards with expandable deep-dive modals. Self-contained HTML with Tailwind CDN.
"""

import json
import sys
from pathlib import Path
from datetime import datetime


def load_v2_result(file_path=None):
    """
    Load a V2 run JSON file. If file_path is None, find the latest v2_run_*.json
    in data/results.
    Returns (data dict, path).
    """
    if file_path is not None:
        target = Path(file_path)
        if not target.is_absolute():
            target = Path(__file__).parent.parent / target
        if not target.exists():
            raise FileNotFoundError(f"V2 result not found: {target}")
        with open(target, "r", encoding="utf-8") as f:
            return json.load(f), target

    results_dir = Path(__file__).parent.parent / "data" / "results"
    files = list(results_dir.glob("v2_run_*.json"))
    if not files:
        raise FileNotFoundError("No v2_run_*.json files found in data/results")
    latest = max(files, key=lambda p: p.stat().st_mtime)
    with open(latest, "r", encoding="utf-8") as f:
        return json.load(f), latest


def generate_v2_html(data, output_path):
    """Generate parameter-centric HTML report with executive brief and parameter cards."""
    try:
        import markdown
    except ImportError:
        raise ImportError(
            "The 'markdown' package is required for V2 HTML reports. "
            "Install it with: pip install markdown"
        )
    import html as html_escape

    def bold_lead(s):
        """Bold the main point (text before the first colon) for readability."""
        if not s or ":" not in s:
            return html_escape.escape(s)
        idx = s.index(":")
        lead = s[:idx].strip()
        tail = s[idx:]  # ": rest of text" including colon and original spacing
        return f'<strong>{html_escape.escape(lead)}</strong>{html_escape.escape(tail)}'

    def bold_lead_in_markdown(md):
        """In each line, bold the phrase before the first colon (main point) for readability."""
        if not md:
            return md
        lines = md.split("\n")
        result = []
        for line in lines:
            # Don't modify markdown headings (# ## ###) or list markers
            stripped = line.lstrip()
            if stripped.startswith("#") or stripped.startswith("- ") or stripped.startswith("* "):
                result.append(line)
                continue
            if ":" in line:
                idx = line.index(":")
                lead = line[:idx].strip()
                tail = line[idx:]
                # Skip if lead looks like link text, URL, or already bold; keep lead short
                if (
                    lead
                    and "[" not in lead
                    and "http" not in lead.lower()
                    and not lead.startswith("*")
                    and not lead.endswith("*")
                    and len(lead) < 120
                ):
                    line = "**" + lead + "**" + tail
            result.append(line)
        return "\n".join(result)

    def bold_lead_in_html(html_content):
        """In each <p> block, bold the phrase immediately before the first colon (main point) for readability."""
        if not html_content or "<p>" not in html_content:
            return html_content
        import re
        # Match inner content of each <p>...</p> (DOTALL so newlines included)
        def process_paragraph(m):
            inner = m.group(1)
            # Greedy: match the 10–120 chars immediately before ": " so we bold the lead-in phrase, not the whole paragraph
            def repl(m2):
                lead = m2.group(1).strip()
                if not lead or "**" in lead:
                    return m2.group(0)
                return "<strong>" + lead + "</strong>: "
            new_inner = re.sub(
                r"([^<>*]{10,120}): ",
                repl,
                inner,
                count=1,
            )
            return "<p>" + new_inner + "</p>"
        return re.sub(r"<p>(.*?)</p>", process_paragraph, html_content, flags=re.DOTALL)

    companies = data.get("companies", [])
    parameters = data.get("parameters", [])
    parameter_definitions = data.get("parameter_definitions", {})
    analyses = data.get("analyses", {})
    executive = data.get("executive", {})
    metadata = data.get("metadata", {})

    def param_name(pid):
        return parameter_definitions.get(pid, {}).get("name", pid)

    def param_category(pid):
        return parameter_definitions.get(pid, {}).get("category", "")

    # Build modal data: param_id -> { ... } for deep-dive
    modal_data = {}
    for param_id in parameters:
        a = analyses.get(param_id, {})
        full_md = a.get("full_report_markdown", "")
        full_md_bolded = bold_lead_in_markdown(full_md)
        if full_md:
            # Use 'extra' for proper headings, tables, fenced code, definition lists, etc.
            full_html = markdown.markdown(full_md_bolded, extensions=["extra"])
        else:
            full_html = "<p>No full report.</p>"
        full_html = bold_lead_in_html(full_html)
        positioning = a.get("positioning_table", [])
        sources = a.get("sources", [])
        white_space_raw = a.get("white_space", [])
        trends_raw = a.get("trends", [])
        modal_data[param_id] = {
            "parameter_name": param_name(param_id),
            "executive_summary": a.get("executive_summary", ""),
            "positioning_table": positioning,
            "full_report_html": full_html,
            "white_space": white_space_raw,
            "white_space_display": [bold_lead(w) for w in white_space_raw],
            "trends": trends_raw,
            "trends_display": [bold_lead(t) for t in trends_raw],
            "sources": sources,
            "confidence": a.get("confidence", "unknown"),
        }

    brief = executive.get("brief", "No executive brief generated.")
    key_themes = executive.get("key_themes", [])
    trends = executive.get("trends", [])
    ws_opportunities = executive.get("white_space_opportunities", [])
    ws_matrix = executive.get("white_space_matrix", {})
    next_steps = executive.get("next_steps", {})
    venture_context = executive.get("venture_context", "")

    # Parameter cards HTML (grouped by category)
    by_category = {}
    for pid in parameters:
        cat = param_category(pid) or "Other"
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(pid)

    conf_dot = {"high": "bg-emerald-500", "medium": "bg-amber-500", "low": "bg-rose-500"}
    cards_html = ""
    for cat in sorted(by_category.keys()):
        cards_html += f'<div class="mb-8 animate-fade-in"><h2 class="text-lg font-semibold text-slate-800 mb-4 pb-2 border-b-2 border-indigo-500 w-fit">{html_escape.escape(cat)}</h2><div class="grid gap-4 md:grid-cols-2">'
        for param_id in by_category[cat]:
            a = analyses.get(param_id, {})
            headline = a.get("headline", "No headline.")
            rankings = a.get("rankings") or []
            rank_lines = "".join(
                f'<div class="text-sm text-slate-600 py-1 px-2 rounded {"bg-slate-50" if r.get("rank", 0) % 2 == 0 else ""}">{r.get("rank")}. {html_escape.escape(r.get("company", ""))}'
                + (f' — <span class="text-slate-500">{html_escape.escape(r.get("label", ""))}</span>' if r.get("label") else "")
                + "</div>"
                for r in rankings[:6]
            )
            conf = a.get("confidence", "unknown")
            dot_cls = conf_dot.get(conf, "bg-slate-400")
            escaped_id = html_escape.escape(param_id).replace("'", "\\'")
            cards_html += f"""
            <div class="group rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition-all duration-200 hover:shadow-lg hover:border-indigo-200 hover:-translate-y-0.5">
                <div class="flex items-start gap-3 mb-2">
                    <span class="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full {dot_cls}" title="{conf} confidence" role="img" aria-label="{conf} confidence"></span>
                    <h3 class="font-semibold text-slate-900 flex-1">{html_escape.escape(param_name(param_id))}</h3>
                </div>
                <p class="text-sm text-slate-700 mb-4 leading-relaxed pl-5">{html_escape.escape(headline)}</p>
                <div class="space-y-0.5 mb-4 pl-5">{rank_lines or '<div class="text-sm text-slate-400">No rankings</div>'}</div>
                <button onclick="openParamModal('{escaped_id}')" class="w-full rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 transition-colors">Read Full Analysis</button>
            </div>
            """
        cards_html += "</div></div>"

    # Key themes as horizontal pill/tag cards (colored left border)
    themes_html = ""
    if key_themes:
        themes_html = '<div class="grid gap-3 sm:grid-cols-2">' + "".join(
            f'<div class="flex rounded-lg border border-slate-200 bg-white p-4 border-l-4 border-l-indigo-500 hover:border-l-indigo-600 transition-colors"><p class="text-sm text-slate-700 leading-relaxed">{bold_lead(t)}</p></div>'
            for t in key_themes
        ) + '</div>'

    # Trends section - numbered cards with gradient
    trends_html = ""
    if trends:
        trends_html = '<div class="space-y-3">' + "".join(
            f'<div class="flex gap-4 rounded-lg bg-gradient-to-r from-slate-50 to-white border border-slate-200 p-4 items-start">'
            f'<span class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-indigo-700 font-semibold text-sm">{i}</span>'
            f'<p class="text-sm text-slate-700 leading-relaxed flex-1">{bold_lead(t)}</p>'
            f'</div>'
            for i, t in enumerate(trends, 1)
        ) + '</div>'

    # White Space Opportunities (Option B) - numbered circle badge + colored sidebar stripe
    stripe_color = {"Low": "border-l-emerald-500", "Medium": "border-l-amber-500", "High": "border-l-rose-500"}
    ws_opps_html = ""
    if ws_opportunities:
        ws_opps_html = '<div class="space-y-4">'
        for i, opp in enumerate(ws_opportunities, 1):
            opportunity = html_escape.escape(opp.get("opportunity", ""))
            why = html_escape.escape(opp.get("why_it_exists", ""))
            closest = html_escape.escape(opp.get("who_is_closest", ""))
            difficulty = opp.get("entry_difficulty", "")
            stripe = stripe_color.get(difficulty, "border-l-slate-400")
            ws_opps_html += (
                f'<div class="flex rounded-lg border border-slate-200 bg-white {stripe} border-l-4 overflow-hidden">'
                f'<div class="p-5 flex-1">'
                f'<div class="flex items-start gap-3 mb-3">'
                f'<span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-white font-bold text-sm">{i}</span>'
                f'<h4 class="font-semibold text-slate-900 text-base leading-snug pt-0.5">{opportunity}</h4>'
                f'</div>'
                f'<p class="text-sm text-slate-600 mb-2 pl-12"><span class="font-medium text-slate-700">Why it exists:</span> {why}</p>'
                f'<p class="text-sm text-slate-600 pl-12"><span class="font-medium text-slate-700">Best positioned:</span> {closest}</p>'
                f'</div>'
                f'<div class="w-20 shrink-0 flex items-center justify-center py-4 bg-slate-100 border-l border-slate-200"><span class="text-xs font-semibold text-slate-600 uppercase">{html_escape.escape(difficulty)}</span></div>'
                f'</div>'
            )
        ws_opps_html += '</div>'

    # White Space Matrix (Option C) - icons, color, count badge
    matrix_meta = {
        "segment_gaps": ("Segment Gaps", "Customer segments nobody serves well", "indigo", '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"/></svg>'),
        "product_gaps": ("Product Gaps", "Capabilities or features nobody offers", "emerald", '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/></svg>'),
        "business_model_gaps": ("Business Model Gaps", "Monetization approaches nobody has tried", "violet", '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>'),
        "geographic_gaps": ("Geographic Gaps", "Markets or regions nobody addresses", "amber", '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0h.5a2.5 2.5 0 002.5-2.5V3.935M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-5 0a4 4 0 11-8 0 4 4 0 018 0z"/></svg>'),
    }
    ws_matrix_html = ""
    has_matrix = any(ws_matrix.get(k) for k in matrix_meta)
    if has_matrix:
        ws_matrix_html = '<div class="grid gap-4 md:grid-cols-2">'
        for key in matrix_meta:
            label, desc, color_key, icon_svg = matrix_meta[key]
            items = ws_matrix.get(key, [])
            if items:
                tc = {"indigo": "text-indigo-600", "emerald": "text-emerald-600", "violet": "text-violet-600", "amber": "text-amber-600"}.get(color_key, "text-slate-600")
                bc = {"indigo": "bg-indigo-50", "emerald": "bg-emerald-50", "violet": "bg-violet-50", "amber": "bg-amber-50"}.get(color_key, "bg-slate-50")
                bl = {"indigo": "border-l-indigo-500", "emerald": "border-l-emerald-500", "violet": "border-l-violet-500", "amber": "border-l-amber-500"}.get(color_key, "border-l-slate-400")
                bdr = {"indigo": "border-indigo-200", "emerald": "border-emerald-200", "violet": "border-violet-200", "amber": "border-amber-200"}.get(color_key, "border-slate-200")
                count = len(items)
                items_html = "".join(f'<li class="text-sm text-slate-600 leading-relaxed">{html_escape.escape(item)}</li>' for item in items)
                ws_matrix_html += (
                    f'<div class="rounded-lg border border-slate-200 bg-white p-5 border-l-4 {bl}">'
                    f'<div class="flex items-center justify-between mb-2 -ml-1">'
                    f'<div class="flex items-center gap-2 {tc}">'
                    f'<span>{icon_svg}</span>'
                    f'<h4 class="font-semibold text-slate-800">{label}</h4>'
                    f'</div>'
                    f'<span class="rounded-full px-2.5 py-0.5 text-xs font-semibold {tc} {bc} border {bdr}">{count} gaps</span>'
                    f'</div>'
                    f'<p class="text-xs text-slate-500 mb-3">{desc}</p>'
                    f'<ul class="list-disc pl-5 space-y-2">{items_html}</ul>'
                    f'</div>'
                )
        ws_matrix_html += '</div>'

    # Next Steps - SVG icons, left-border accent, dot-style priority
    next_step_icons = {
        "investigate_further": '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>',
        "quick_wins": '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>',
        "strategic_bets": '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"/></svg>',
        "monitor_and_defend": '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/></svg>',
    }
    bucket_labels = {
        "investigate_further": ("Investigate Further", "Needs deeper research before acting", "border-l-blue-500 text-blue-700"),
        "quick_wins": ("Quick Wins", "Low-effort, high-signal actions achievable in weeks", "border-l-emerald-500 text-emerald-700"),
        "strategic_bets": ("Strategic Bets", "Bigger moves with outsized payoff", "border-l-violet-500 text-violet-700"),
        "monitor_and_defend": ("Monitor & Defend", "Competitive moves to watch", "border-l-amber-500 text-amber-700"),
    }
    pri_dot = {"High": "bg-rose-500", "Medium": "bg-amber-500", "Low": "bg-emerald-500"}
    has_next_steps = any(next_steps.get(k) for k in bucket_labels)
    next_steps_html = ""
    if has_next_steps:
        next_steps_html = '<div class="grid gap-4 md:grid-cols-2">'
        for key, (label, desc, accent_class) in bucket_labels.items():
            items = next_steps.get(key, [])
            icon = next_step_icons.get(key, "")
            if items:
                next_steps_html += f'<div class="rounded-lg border border-slate-200 bg-white p-5 border-l-4 {accent_class.split()[0]}">'
                next_steps_html += f'<div class="flex items-center gap-2 mb-1 {accent_class.split()[-1]}">'
                next_steps_html += f'<span>{icon}</span>'
                next_steps_html += f'<h4 class="font-semibold">{label}</h4>'
                next_steps_html += '</div>'
                next_steps_html += f'<p class="text-xs text-slate-500 mb-4">{desc}</p>'
                next_steps_html += '<div class="space-y-3">'
                for item in items:
                    action = html_escape.escape(item.get("action", ""))
                    rationale = html_escape.escape(item.get("rationale", ""))
                    priority = item.get("priority", "")
                    dot = pri_dot.get(priority, "bg-slate-400")
                    next_steps_html += (
                        f'<div class="rounded-lg border border-slate-100 bg-slate-50/50 p-4">'
                        f'<div class="flex items-start gap-3 mb-2">'
                        f'<span class="mt-1.5 h-2 w-2 shrink-0 rounded-full {dot}"></span>'
                        f'<p class="text-sm font-medium text-slate-900 flex-1">{action}</p>'
                        f'</div>'
                        f'<p class="text-xs text-slate-500 pl-5">{rationale}</p>'
                        f'</div>'
                    )
                next_steps_html += '</div></div>'
        next_steps_html += '</div>'

    # Post-Mortem Intelligence section
    postmortem = data.get("postmortem_brief", {})
    graveyard_cos = data.get("graveyard_companies", [])
    postmortem_html = ""
    if postmortem and postmortem.get("failure_patterns"):
        pm_parts = []
        pm_parts.append(
            '<section id="postmortem" class="mb-12 animate-fade-in">'
            '<div class="rounded-xl border border-slate-300 bg-slate-50 shadow-sm overflow-hidden">'
            '<div class="p-6 md:p-8">'
            '<h2 class="text-2xl font-display font-bold text-slate-800 mb-2">Post-Mortem Intelligence</h2>'
            f'<p class="text-sm text-slate-500 mb-6">Lessons from {len(graveyard_cos)} failed companies in this sector</p>'
        )
        # Failure patterns
        fp = postmortem.get("failure_patterns", [])
        if fp:
            pm_parts.append('<div class="mb-6"><h3 class="text-sm font-semibold text-slate-600 uppercase tracking-wider mb-3">Failure Patterns</h3><div class="space-y-2">')
            for p in fp:
                pm_parts.append(f'<div class="flex gap-2 text-sm text-slate-700"><span class="text-red-500 font-bold shrink-0">!</span><span>{html_escape.escape(p)}</span></div>')
            pm_parts.append('</div></div>')
        # Structural vulnerabilities
        sv = postmortem.get("structural_vulnerabilities", [])
        if sv:
            pm_parts.append('<div class="mb-6"><h3 class="text-sm font-semibold text-slate-600 uppercase tracking-wider mb-3">Structural Vulnerabilities</h3><div class="space-y-2">')
            for v in sv:
                pm_parts.append(f'<div class="flex gap-2 text-sm text-slate-600"><span class="text-amber-500 shrink-0">&#x26A0;</span><span>{html_escape.escape(v)}</span></div>')
            pm_parts.append('</div></div>')
        # Cautionary narratives
        cn = postmortem.get("cautionary_narratives", [])
        if cn:
            pm_parts.append('<div class="mb-6"><h3 class="text-sm font-semibold text-slate-600 uppercase tracking-wider mb-3">Cautionary Narratives</h3><div class="space-y-4">')
            for n in cn:
                co = html_escape.escape(n.get("company", ""))
                fm = html_escape.escape(n.get("failure_mode", ""))
                pp = html_escape.escape(n.get("peak_position", ""))
                narr = html_escape.escape(n.get("narrative", ""))
                lesson = html_escape.escape(n.get("key_lesson", ""))
                fm_badge = f'<span class="text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-600">{fm}</span>' if fm else ""
                pp_line = f'<p class="text-sm text-slate-600 mb-1"><strong>At their peak:</strong> {pp}</p>' if pp else ""
                narr_line = f'<p class="text-sm text-slate-600 mb-2">{narr}</p>' if narr else ""
                lesson_line = f'<p class="text-sm text-slate-800 bg-slate-50 rounded p-2 border border-slate-200"><strong>Key lesson:</strong> {lesson}</p>' if lesson else ""
                pm_parts.append(
                    f'<div class="rounded-lg border border-slate-200 bg-white p-4">'
                    f'<div class="flex items-start justify-between mb-2"><h4 class="font-semibold text-slate-900 text-sm">{co}</h4>'
                    f'{fm_badge}'
                    f'</div>'
                    f'{pp_line}'
                    f'{narr_line}'
                    f'{lesson_line}'
                    f'</div>'
                )
            pm_parts.append('</div></div>')
        # Survival principles
        sp = postmortem.get("survival_principles", [])
        if sp:
            pm_parts.append('<div><h3 class="text-sm font-semibold text-slate-600 uppercase tracking-wider mb-3">Survival Principles</h3><ol class="list-decimal list-inside space-y-2">')
            for p in sp:
                pm_parts.append(f'<li class="text-sm text-slate-700">{html_escape.escape(p)}</li>')
            pm_parts.append('</ol></div>')
        pm_parts.append('</div></div></section>')
        postmortem_html = "\n".join(pm_parts)

    total_time = metadata.get("total_elapsed_seconds", 0)
    time_str = f"{total_time:.0f}s" if total_time < 60 else f"{total_time / 60:.1f}m"
    num_companies = len(companies)
    num_params = len(parameters)
    conf_counts = {}
    for a in analyses.values():
        c = a.get("confidence", "unknown")
        conf_counts[c] = conf_counts.get(c, 0) + 1
    dominant_conf = max(conf_counts, key=conf_counts.get) if conf_counts else "medium"

    # Hero header with venture context integrated
    venture_hero_html = ""
    if venture_context:
        venture_hero_html = (
            f'<div class="mt-6 p-4 rounded-lg bg-amber-500/20 border border-amber-400/50">'
            f'<p class="text-xs font-semibold text-amber-200 uppercase tracking-wide mb-1">Venture Context</p>'
            f'<p class="text-amber-50 text-sm leading-relaxed">{html_escape.escape(venture_context)}</p>'
            f'</div>'
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>V2 Competitive Intelligence: {html_escape.escape(", ".join(companies))}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        html {{ scroll-behavior: smooth; }}
        body {{ font-family: 'Inter', system-ui, sans-serif; }}
        .font-display {{ font-family: 'Playfair Display', Georgia, serif; }}
        .prose p {{ margin-bottom: 0.75rem; }}
        .prose h1 {{ font-size: 1.5rem; font-weight: 700; margin-top: 1.5rem; margin-bottom: 0.75rem; color: #0f172a; }}
        .prose h2 {{ font-size: 1.25rem; font-weight: 600; margin-top: 1.25rem; margin-bottom: 0.5rem; color: #1e293b; border-bottom: 1px solid #e2e8f0; padding-bottom: 0.25rem; }}
        .prose h3 {{ font-size: 1.1rem; font-weight: 600; margin-top: 1rem; margin-bottom: 0.5rem; color: #334155; }}
        .prose h4 {{ font-size: 1rem; font-weight: 600; margin-top: 0.75rem; margin-bottom: 0.375rem; color: #475569; }}
        .prose ul {{ list-style-type: disc; padding-left: 1.5rem; margin-bottom: 0.75rem; }}
        .prose ol {{ list-style-type: decimal; padding-left: 1.5rem; margin-bottom: 0.75rem; }}
        .prose li {{ margin-bottom: 0.25rem; }}
        .prose table {{ border-collapse: collapse; width: 100%; margin-bottom: 1rem; }}
        .prose th, .prose td {{ border: 1px solid #e2e8f0; padding: 0.5rem 0.75rem; text-align: left; }}
        .prose th {{ background: #f1f5f9; font-weight: 600; }}
        .prose strong {{ font-weight: 600; color: #0f172a; }}
        .prose em {{ font-style: italic; }}
        @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(8px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        .animate-fade-in {{ animation: fadeIn 0.4s ease-out forwards; }}
        .modal-overlay {{ display: none; position: fixed; inset: 0; background: rgba(15,23,42,0.6); backdrop-filter: blur(4px); z-index: 100; justify-content: center; align-items: center; padding: 1rem; }}
        .modal-overlay.active {{ display: flex; }}
        .modal-content {{ background: white; border-radius: 1rem; max-width: 1000px; width: 100%; max-height: 90vh; overflow: hidden; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.35); display: flex; flex-direction: column; }}
        .modal-tab {{ display: none; padding: 1.5rem; overflow-y: auto; flex: 1; }}
        .modal-tab.active {{ display: block; }}
        @media print {{
            .no-print {{ display: none !important; }}
            details {{ display: block !important; }}
            details summary {{ margin-bottom: 0.5rem; font-weight: 600; }}
            details > *:not(summary) {{ display: block !important; visibility: visible !important; }}
            body {{ background: white; color: #1e293b; }}
            .shadow-sm, .shadow-md, .shadow-lg {{ box-shadow: none !important; }}
            a {{ color: #4f46e5; }}
            header {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
        }}
    </style>
    <script>
        tailwind.config = {{ theme: {{ extend: {{ fontFamily: {{ sans: ['Inter', 'system-ui', 'sans-serif'], display: ['Playfair Display', 'Georgia', 'serif'] }} }} }} }};
    </script>
</head>
<body class="bg-slate-100 text-slate-900 antialiased">

<div class="min-h-screen">
    <!-- Hero Header -->
    <header class="bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white px-6 py-10 md:px-12 md:py-14">
        <div class="max-w-6xl mx-auto">
            <h1 class="font-display text-4xl md:text-5xl font-bold tracking-tight mb-2">Relational Competitive Intelligence Report</h1>
            <p class="text-slate-300 text-base mb-6">{datetime.now().strftime("%B %d, %Y at %H:%M")}</p>
            <div class="flex flex-wrap gap-2 mb-6">
                {"".join(f'<span class="px-4 py-1.5 rounded-full text-sm font-medium bg-white/10 border border-white/30 backdrop-blur-sm">{html_escape.escape(c)}</span>' for c in companies)}
            </div>
            <!-- Key stats row -->
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-2">
                <div class="rounded-lg bg-white/5 border border-white/10 p-4 backdrop-blur-sm">
                    <p class="text-slate-400 text-xs font-semibold uppercase tracking-wider mb-1">Companies</p>
                    <p class="text-2xl font-bold text-white">{num_companies}</p>
                </div>
                <div class="rounded-lg bg-white/5 border border-white/10 p-4 backdrop-blur-sm">
                    <p class="text-slate-400 text-xs font-semibold uppercase tracking-wider mb-1">Parameters</p>
                    <p class="text-2xl font-bold text-white">{num_params}</p>
                </div>
                <div class="rounded-lg bg-white/5 border border-white/10 p-4 backdrop-blur-sm">
                    <p class="text-slate-400 text-xs font-semibold uppercase tracking-wider mb-1">Confidence</p>
                    <p class="text-2xl font-bold text-white capitalize">{dominant_conf}</p>
                </div>
                <div class="rounded-lg bg-white/5 border border-white/10 p-4 backdrop-blur-sm">
                    <p class="text-slate-400 text-xs font-semibold uppercase tracking-wider mb-1">Duration</p>
                    <p class="text-2xl font-bold text-white">{time_str}</p>
                </div>
            </div>
            {venture_hero_html}
        </div>
    </header>

    <!-- Sticky Nav -->
    <nav id="stickyNav" class="no-print sticky top-0 z-50 bg-white/90 backdrop-blur-md border-b border-slate-200 shadow-sm">
        <div class="max-w-6xl mx-auto px-6 py-3 flex flex-wrap gap-2 justify-center">
            <a href="#executive-brief" class="nav-link px-4 py-2 rounded-lg text-sm font-medium text-slate-600 hover:text-indigo-600 hover:bg-indigo-50 transition-colors">Executive Brief</a>
            <a href="#trends" class="nav-link px-4 py-2 rounded-lg text-sm font-medium text-slate-600 hover:text-indigo-600 hover:bg-indigo-50 transition-colors">Trends</a>
            <a href="#white-space" class="nav-link px-4 py-2 rounded-lg text-sm font-medium text-slate-600 hover:text-indigo-600 hover:bg-indigo-50 transition-colors">White Space</a>
            <a href="#next-steps" class="nav-link px-4 py-2 rounded-lg text-sm font-medium text-slate-600 hover:text-indigo-600 hover:bg-indigo-50 transition-colors">Next Steps</a>
            {'<a href="#postmortem" class="nav-link px-4 py-2 rounded-lg text-sm font-medium text-slate-600 hover:text-indigo-600 hover:bg-indigo-50 transition-colors">Post-Mortem</a>' if postmortem_html else ""}
            <a href="#parameter-analysis" class="nav-link px-4 py-2 rounded-lg text-sm font-medium text-slate-600 hover:text-indigo-600 hover:bg-indigo-50 transition-colors">Parameter Analysis</a>
        </div>
    </nav>

<div class="max-w-6xl mx-auto px-6 py-10">

    <section id="executive-brief" class="mb-12 animate-fade-in">
        <div class="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
            <div class="p-6 md:p-8">
                <h2 class="text-2xl font-display font-bold text-slate-900 mb-6">Executive Brief</h2>
                <div class="pl-4 border-l-4 border-indigo-500 mb-8">
                    <p class="text-lg text-slate-700 leading-relaxed whitespace-pre-line">{html_escape.escape(brief)}</p>
                </div>
                {f'<div class="mb-8"><h3 class="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-4">Key Themes</h3>{themes_html}</div>' if themes_html else ""}
            </div>
            {f'<details class="print-expand border-t border-slate-200" id="trends"><summary class="p-6 font-semibold text-slate-800 cursor-pointer hover:bg-slate-50 transition-colors">Trends</summary><div class="details-content px-6 pb-6 pt-2">{trends_html}</div></details>' if trends_html else ""}
            {f'<details class="print-expand border-t border-slate-200" id="white-space"><summary class="p-6 font-semibold text-slate-800 cursor-pointer hover:bg-slate-50 transition-colors">White Space &mdash; Strategic Opportunities</summary><div class="details-content px-6 pb-6 pt-2">{ws_opps_html}</div></details>' if ws_opps_html else ""}
            {f'<details class="print-expand border-t border-slate-200" id="white-space-matrix"><summary class="p-6 font-semibold text-slate-800 cursor-pointer hover:bg-slate-50 transition-colors">White Space &mdash; Gap Matrix</summary><div class="details-content px-6 pb-6 pt-2">{ws_matrix_html}</div></details>' if ws_matrix_html else ""}
            {f'<details class="print-expand border-t border-slate-200" id="next-steps"><summary class="p-6 font-semibold text-slate-800 cursor-pointer hover:bg-slate-50 transition-colors">Next Steps</summary><div class="details-content px-6 pb-6 pt-2">{next_steps_html}</div></details>' if next_steps_html else ""}
        </div>
    </section>

    {postmortem_html}

    <section id="parameter-analysis" class="mb-12 animate-fade-in">
        <h2 class="text-2xl font-display font-bold text-slate-900 mb-6">Parameter Analysis</h2>
        {cards_html}
    </section>

    <footer class="text-center text-slate-500 text-sm py-8 border-t border-slate-200 mt-12">
        <p>Generated by V2 Relational Competitive Intelligence Engine</p>
    </footer>
</div>
</div>

<div id="paramModalOverlay" class="modal-overlay" onclick="closeParamModalOnOverlay(event)">
    <div class="modal-content" role="dialog" aria-modal="true" aria-labelledby="paramModalTitle" onclick="event.stopPropagation()">
        <div class="flex-none bg-gradient-to-r from-slate-900 to-slate-800 text-white px-6 py-4 flex justify-between items-center">
            <div class="flex items-center gap-3">
                <h2 id="paramModalTitle" class="text-xl font-display font-bold"></h2>
                <span id="paramModalConfidence" class="text-slate-300 text-sm"></span>
            </div>
            <button onclick="closeParamModal()" class="text-slate-400 hover:text-white p-2 rounded-lg hover:bg-white/10 transition-colors" title="Close (Esc)">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
            </button>
        </div>
        <div class="flex-none border-b border-slate-200 bg-slate-50 px-4 flex gap-1 overflow-x-auto">
            <button type="button" class="modal-tab-btn px-4 py-3 text-sm font-medium text-slate-600 hover:text-indigo-600 border-b-2 border-transparent hover:border-indigo-300 whitespace-nowrap" data-tab="summary">Summary</button>
            <button type="button" class="modal-tab-btn px-4 py-3 text-sm font-medium text-slate-600 hover:text-indigo-600 border-b-2 border-transparent hover:border-indigo-300 whitespace-nowrap" data-tab="positioning">Positioning</button>
            <button type="button" class="modal-tab-btn px-4 py-3 text-sm font-medium text-slate-600 hover:text-indigo-600 border-b-2 border-transparent hover:border-indigo-300 whitespace-nowrap" data-tab="analysis">Full Analysis</button>
            <button type="button" class="modal-tab-btn px-4 py-3 text-sm font-medium text-slate-600 hover:text-indigo-600 border-b-2 border-transparent hover:border-indigo-300 whitespace-nowrap" data-tab="themes">White Space &amp; Trends</button>
            <button type="button" class="modal-tab-btn px-4 py-3 text-sm font-medium text-slate-600 hover:text-indigo-600 border-b-2 border-transparent hover:border-indigo-300 whitespace-nowrap" data-tab="sources">Sources</button>
        </div>
        <div class="flex-1 overflow-hidden flex flex-col">
            <div id="modal-tab-summary" class="modal-tab active"></div>
            <div id="modal-tab-positioning" class="modal-tab"></div>
            <div id="modal-tab-analysis" class="modal-tab"></div>
            <div id="modal-tab-themes" class="modal-tab"></div>
            <div id="modal-tab-sources" class="modal-tab"></div>
        </div>
    </div>
</div>

<script>
const modalData = {json.dumps(modal_data, ensure_ascii=False).replace("</", "<\\/")};

function escapeHtml(text) {{
    if (!text) return "";
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}}

function boldLeadHtml(text) {{
    if (!text) return "";
    const i = text.indexOf(":");
    if (i === -1) return escapeHtml(text);
    const lead = text.slice(0, i).trim();
    const tail = text.slice(i);
    return "<strong>" + escapeHtml(lead) + "</strong>" + escapeHtml(tail);
}}

function safeUrl(url) {{
    if (!url) return "#";
    return /^https?:\\/\\//.test(url) ? url : "#";
}}

function setModalTab(tabName) {{
    document.querySelectorAll(".modal-tab").forEach(el => el.classList.remove("active"));
    document.querySelectorAll(".modal-tab-btn").forEach(el => {{
        el.classList.remove("border-indigo-600", "text-indigo-600");
        el.classList.add("border-transparent");
    }});
    const tabEl = document.getElementById("modal-tab-" + tabName);
    const btnEl = document.querySelector(".modal-tab-btn[data-tab='" + tabName + "']");
    if (tabEl) tabEl.classList.add("active");
    if (btnEl) {{ btnEl.classList.add("border-indigo-600", "text-indigo-600"); btnEl.classList.remove("border-transparent"); }}
}}

function openParamModal(paramId) {{
    const d = modalData[paramId];
    if (!d) return;
    const overlay = document.getElementById("paramModalOverlay");
    document.getElementById("paramModalTitle").textContent = d.parameter_name;
    document.getElementById("paramModalConfidence").textContent = d.confidence + " confidence";
    document.getElementById("modal-tab-summary").innerHTML = "<p class='text-slate-700 leading-relaxed'>" + escapeHtml(d.executive_summary || "\u2014") + "</p>";
    const table = d.positioning_table;
    if (table && table.length) {{
        const keys = Object.keys(table[0]);
        let tableHtml = "<table class='min-w-full border border-slate-200 text-sm'><thead><tr>";
        keys.forEach(k => tableHtml += "<th class='border border-slate-200 p-2 bg-slate-100 font-semibold'>" + escapeHtml(k) + "</th>");
        tableHtml += "</tr></thead><tbody>";
        table.forEach(row => {{
            tableHtml += "<tr>";
            keys.forEach(k => tableHtml += "<td class='border border-slate-200 p-2'>" + escapeHtml(String(row[k] != null ? row[k] : "")) + "</td>");
            tableHtml += "</tr>";
        }});
        tableHtml += "</tbody></table>";
        document.getElementById("modal-tab-positioning").innerHTML = tableHtml;
    }} else {{
        document.getElementById("modal-tab-positioning").innerHTML = "<p class='text-slate-400'>No table.</p>";
    }}
    document.getElementById("modal-tab-analysis").innerHTML = "<div class='prose prose-sm max-w-none text-slate-600'>" + (d.full_report_html || "<p>No report.</p>") + "</div>";
    let themesHtml = "";
    const wsList = (d.white_space_display && d.white_space_display.length) ? d.white_space_display : (d.white_space || []).map(boldLeadHtml);
    if (wsList.length) {{
        themesHtml += "<p class='font-semibold text-slate-800 mb-2'>White space</p><ul class='list-disc pl-5 space-y-1 text-slate-600'>" + wsList.map(w => "<li class='leading-relaxed'>" + w + "</li>").join("") + "</ul>";
    }}
    const trendsList = (d.trends_display && d.trends_display.length) ? d.trends_display : (d.trends || []).map(boldLeadHtml);
    if (trendsList.length) {{
        themesHtml += "<p class='font-semibold text-slate-800 mt-4 mb-2'>Trends</p><ul class='list-disc pl-5 space-y-1 text-slate-600'>" + trendsList.map(t => "<li class='leading-relaxed'>" + t + "</li>").join("") + "</ul>";
    }}
    document.getElementById("modal-tab-themes").innerHTML = themesHtml || "<p class='text-slate-400'>\u2014</p>";
    const sources = d.sources || [];
    document.getElementById("modal-tab-sources").innerHTML = sources.length
        ? sources.map(function(s) {{
            const url = safeUrl(s.url);
            return "<div class='border-l-4 border-indigo-500 pl-3 py-2 mb-2 bg-slate-50 rounded-r'>"
                + "<a href='" + escapeHtml(url) + "' target='_blank' rel='noopener noreferrer' class='font-medium text-indigo-600 hover:text-indigo-700'>" + escapeHtml(s.title || s.url) + "</a>"
                + "<span class='text-xs text-slate-500 ml-2'>" + escapeHtml(s.domain || "") + "</span></div>";
        }}).join("")
        : "<p class='text-slate-400'>No sources.</p>";
    setModalTab("summary");
    overlay.classList.add("active");
    document.body.style.overflow = "hidden";
    setTimeout(function() {{ var cb = overlay.querySelector("button"); if (cb) cb.focus(); }}, 100);
}}

document.querySelectorAll(".modal-tab-btn").forEach(btn => {{
    btn.addEventListener("click", () => setModalTab(btn.getAttribute("data-tab")));
}});

function closeParamModal() {{
    document.getElementById("paramModalOverlay").classList.remove("active");
    document.body.style.overflow = "";
}}

function closeParamModalOnOverlay(e) {{
    if (e.target.id === "paramModalOverlay") closeParamModal();
}}

document.addEventListener("keydown", e => {{ if (e.key === "Escape") closeParamModal(); }});

/* Focus trap — keep Tab cycling inside the open modal */
document.getElementById("paramModalOverlay").addEventListener("keydown", function(e) {{
    if (e.key !== "Tab") return;
    var modal = this.querySelector(".modal-content");
    var focusable = modal.querySelectorAll("button, [href], input, select, textarea, [tabindex]:not([tabindex='-1'])");
    if (!focusable.length) return;
    var first = focusable[0], last = focusable[focusable.length - 1];
    if (e.shiftKey && document.activeElement === first) {{ e.preventDefault(); last.focus(); }}
    else if (!e.shiftKey && document.activeElement === last) {{ e.preventDefault(); first.focus(); }}
}});

/* Nav: auto-open collapsed <details> when clicking nav links */
document.querySelectorAll(".nav-link").forEach(function(link) {{
    link.addEventListener("click", function(e) {{
        var targetId = this.getAttribute("href").substring(1);
        var target = document.getElementById(targetId);
        if (target && target.tagName === "DETAILS" && !target.open) {{
            target.setAttribute("open", "");
        }}
    }});
}});

/* Active nav highlighting via IntersectionObserver */
(function() {{
    var navLinks = document.querySelectorAll(".nav-link");
    var sectionIds = ["executive-brief", "trends", "white-space", "next-steps", "parameter-analysis"];
    function clearActive() {{ navLinks.forEach(function(l) {{ l.classList.remove("text-indigo-600", "bg-indigo-50"); }}); }}
    function setActive(id) {{
        clearActive();
        var idx = sectionIds.indexOf(id);
        if (idx >= 0 && navLinks[idx]) navLinks[idx].classList.add("text-indigo-600", "bg-indigo-50");
    }}
    if ("IntersectionObserver" in window) {{
        var visible = {{}};
        var observer = new IntersectionObserver(function(entries) {{
            entries.forEach(function(entry) {{
                visible[entry.target.id] = entry.isIntersecting;
            }});
            for (var i = sectionIds.length - 1; i >= 0; i--) {{
                var id = sectionIds[i];
                if (!visible[id]) continue;
                var el = document.getElementById(id);
                if (el && el.tagName === "DETAILS" && !el.open) continue;
                setActive(id);
                return;
            }}
        }}, {{ rootMargin: "-80px 0px -60% 0px" }});
        sectionIds.forEach(function(id) {{
            var el = document.getElementById(id);
            if (el) observer.observe(el);
        }});
    }}
}})();

/* Print: expand all collapsible sections before printing */
window.addEventListener("beforeprint", function() {{
    document.querySelectorAll("details.print-expand").forEach(function(d) {{ d.setAttribute("open", ""); }});
}});
</script>
</body>
</html>
"""

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"V2 HTML report written: {out}")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        data, json_path = load_v2_result(path)
        html_path = json_path.with_suffix(".html") if hasattr(json_path, "with_suffix") else Path(str(json_path).replace(".json", ".html"))
        generate_v2_html(data, html_path)
    except FileNotFoundError as e:
        print(e)
        sys.exit(1)
