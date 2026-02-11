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
    import markdown
    import html as html_escape

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
        full_html = markdown.markdown(full_md) if full_md else "<p>No full report.</p>"
        positioning = a.get("positioning_table", [])
        sources = a.get("sources", [])
        modal_data[param_id] = {
            "parameter_name": param_name(param_id),
            "executive_summary": a.get("executive_summary", ""),
            "positioning_table": positioning,
            "full_report_html": full_html,
            "white_space": a.get("white_space", []),
            "trends": a.get("trends", []),
            "sources": sources,
            "confidence": a.get("confidence", "unknown"),
        }

    brief = executive.get("brief", "No executive brief generated.")
    key_themes = executive.get("key_themes", [])

    # Parameter cards HTML (grouped by category)
    by_category = {}
    for pid in parameters:
        cat = param_category(pid) or "Other"
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(pid)

    cards_html = ""
    for cat in sorted(by_category.keys()):
        cards_html += f'<div class="mb-6"><h2 class="text-lg font-semibold text-gray-700 mb-3">{html_escape.escape(cat)}</h2><div class="grid gap-4 md:grid-cols-2">'
        for param_id in by_category[cat]:
            a = analyses.get(param_id, {})
            headline = a.get("headline", "No headline.")
            rankings = a.get("rankings", [])
            rank_lines = "".join(
                f'<li class="text-sm text-gray-600">{r.get("rank")}. {html_escape.escape(r.get("company", ""))}'
                + (f' — {html_escape.escape(r.get("label", ""))}' if r.get("label") else "")
                + "</li>"
                for r in rankings[:6]
            )
            conf = a.get("confidence", "unknown")
            conf_class = {"high": "bg-green-100 text-green-800", "medium": "bg-yellow-100 text-yellow-800", "low": "bg-red-100 text-red-800"}.get(conf, "bg-gray-100 text-gray-800")
            escaped_id = html_escape.escape(param_id).replace("'", "\\'")
            cards_html += f"""
            <div class="border border-gray-200 rounded-lg p-4 bg-white shadow-sm hover:shadow-md transition-shadow">
                <div class="flex items-start justify-between gap-2 mb-2">
                    <h3 class="font-semibold text-gray-900">{html_escape.escape(param_name(param_id))}</h3>
                    <span class="text-xs px-2 py-0.5 rounded {conf_class}">{conf}</span>
                </div>
                <p class="text-sm text-gray-700 mb-3 leading-relaxed">{html_escape.escape(headline)}</p>
                <ol class="list-decimal list-inside text-sm text-gray-600 mb-3">{rank_lines or "<li>No rankings</li>"}</ol>
                <button onclick="openParamModal('{escaped_id}')" class="text-blue-600 hover:text-blue-800 text-sm font-medium">Read Full Analysis</button>
            </div>
            """
        cards_html += "</div></div>"

    # Themes list
    themes_html = ""
    if key_themes:
        themes_html = "<ul class=\"list-disc pl-5 space-y-1 text-sm text-gray-600\">" + "".join(f"<li>{html_escape.escape(t)}</li>" for t in key_themes) + "</ul>"

    total_time = metadata.get("total_elapsed_seconds", 0)
    time_str = f"{total_time:.0f}s" if total_time < 60 else f"{total_time / 60:.1f}m"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>V2 Competitive Intelligence: {html_escape.escape(", ".join(companies))}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .prose p {{ margin-bottom: 0.75rem; }}
        .prose ul {{ list-style-type: disc; padding-left: 1.5rem; }}
        .prose table {{ border-collapse: collapse; width: 100%; }}
        .prose th, .prose td {{ border: 1px solid #e5e7eb; padding: 0.5rem 0.75rem; text-align: left; }}
        .prose th {{ background: #f3f4f6; font-weight: 600; }}
        .modal-overlay {{ display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 100; justify-content: center; align-items: center; padding: 1rem; }}
        .modal-overlay.active {{ display: flex; }}
        .modal-content {{ background: white; border-radius: 0.75rem; max-width: 900px; width: 100%; max-height: 90vh; overflow-y: auto; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25); }}
    </style>
</head>
<body class="bg-gray-50 text-gray-900 font-sans p-4 md:p-8">

<div class="max-w-6xl mx-auto">
    <header class="mb-8">
        <h1 class="text-3xl font-bold text-gray-900 mb-2">Relational Competitive Intelligence Report</h1>
        <p class="text-gray-600">Generated {datetime.now().strftime("%B %d, %Y at %H:%M")} · {time_str} total</p>
        <div class="mt-2 flex flex-wrap gap-2">
            {"".join(f'<span class="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm">{html_escape.escape(c)}</span>' for c in companies)}
        </div>
    </header>

    <section class="mb-10 p-6 bg-white border border-gray-200 rounded-xl shadow-sm">
        <h2 class="text-xl font-bold text-gray-900 mb-3">Executive Brief</h2>
        <p class="text-gray-700 leading-relaxed whitespace-pre-line">{html_escape.escape(brief)}</p>
        {f'<div class="mt-4"><h3 class="text-sm font-semibold text-gray-700 mb-2">Key themes</h3>{themes_html}</div>' if themes_html else ""}
    </section>

    <section class="mb-8">
        <h2 class="text-xl font-bold text-gray-900 mb-4">Parameter Analysis</h2>
        {cards_html}
    </section>

    <footer class="text-center text-gray-500 text-sm py-6">
        <p>Generated by V2 Relational Competitive Intelligence Engine</p>
    </footer>
</div>

<div id="paramModalOverlay" class="modal-overlay" onclick="closeParamModalOnOverlay(event)">
    <div class="modal-content" onclick="event.stopPropagation()">
        <div class="sticky top-0 bg-white border-b border-gray-200 p-4 flex justify-between items-center rounded-t-xl">
            <h2 id="paramModalTitle" class="text-xl font-bold text-gray-900"></h2>
            <button onclick="closeParamModal()" class="text-gray-400 hover:text-gray-600 p-2 rounded-full hover:bg-gray-100">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
            </button>
        </div>
        <div class="p-4 space-y-4">
            <div id="paramModalConfidence" class="flex items-center gap-2"></div>
            <details open class="border border-gray-200 rounded-lg overflow-hidden">
                <summary class="p-4 font-semibold text-gray-800 cursor-pointer">Executive Summary</summary>
                <div id="paramModalSummary" class="p-4 pt-0 border-t border-gray-100 text-gray-600"></div>
            </details>
            <details class="border border-gray-200 rounded-lg overflow-hidden">
                <summary class="p-4 font-semibold text-gray-800 cursor-pointer">Positioning Table</summary>
                <div id="paramModalTable" class="p-4 pt-0 border-t border-gray-100 overflow-x-auto"></div>
            </details>
            <details open class="border border-gray-200 rounded-lg overflow-hidden">
                <summary class="p-4 font-semibold text-gray-800 cursor-pointer">Full Analysis</summary>
                <div id="paramModalReport" class="p-4 pt-0 border-t border-gray-100 prose prose-sm max-w-none text-gray-600"></div>
            </details>
            <details class="border border-gray-200 rounded-lg overflow-hidden">
                <summary class="p-4 font-semibold text-gray-800 cursor-pointer">White Space &amp; Trends</summary>
                <div id="paramModalThemes" class="p-4 pt-0 border-t border-gray-100 text-gray-600"></div>
            </details>
            <details class="border border-gray-200 rounded-lg overflow-hidden">
                <summary class="p-4 font-semibold text-gray-800 cursor-pointer">Sources</summary>
                <div id="paramModalSources" class="p-4 pt-0 border-t border-gray-100"></div>
            </details>
        </div>
    </div>
</div>

<script>
const modalData = {json.dumps(modal_data, ensure_ascii=False)};

function openParamModal(paramId) {{
    const d = modalData[paramId];
    if (!d) return;
    document.getElementById("paramModalTitle").textContent = d.parameter_name;
    const confColors = {{ high: "bg-green-100 text-green-800", medium: "bg-yellow-100 text-yellow-800", low: "bg-red-100 text-red-800" }};
    document.getElementById("paramModalConfidence").innerHTML = "<span class=\"text-xs px-2 py-0.5 rounded \" + (confColors[d.confidence] || "bg-gray-100 text-gray-800") + "\">" + d.confidence + " confidence</span>";
    document.getElementById("paramModalSummary").textContent = d.executive_summary || "—";
    const table = d.positioning_table;
    if (table && table.length) {{
        const keys = Object.keys(table[0]);
        let tableHtml = "<table class=\"min-w-full border border-gray-200 text-sm\"><thead><tr>";
        keys.forEach(k => tableHtml += "<th class=\"border border-gray-200 p-2 bg-gray-100\">" + escapeHtml(k) + "</th>");
        tableHtml += "</tr></thead><tbody>";
        table.forEach(row => {{
            tableHtml += "<tr>";
            keys.forEach(k => tableHtml += "<td class=\"border border-gray-200 p-2\">" + escapeHtml(String(row[k] != null ? row[k] : "")) + "</td>");
            tableHtml += "</tr>";
        }});
        tableHtml += "</tbody></table>";
        document.getElementById("paramModalTable").innerHTML = tableHtml;
    }} else {{
        document.getElementById("paramModalTable").innerHTML = "<p class=\"text-gray-400\">No table.</p>";
    }}
    document.getElementById("paramModalReport").innerHTML = d.full_report_html || "<p>No report.</p>";
    let themesHtml = "";
    if (d.white_space && d.white_space.length) {{
        themesHtml += "<p class=\"font-medium text-gray-700 mt-2\">White space</p><ul class=\"list-disc pl-5\">" + d.white_space.map(w => "<li>" + escapeHtml(w) + "</li>").join("") + "</ul>";
    }}
    if (d.trends && d.trends.length) {{
        themesHtml += "<p class=\"font-medium text-gray-700 mt-2\">Trends</p><ul class=\"list-disc pl-5\">" + d.trends.map(t => "<li>" + escapeHtml(t) + "</li>").join("") + "</ul>";
    }}
    document.getElementById("paramModalThemes").innerHTML = themesHtml || "—";
    const sources = d.sources || [];
    document.getElementById("paramModalSources").innerHTML = sources.length ? sources.map((s, i) => "<div class=\"border-l-4 border-blue-500 pl-3 py-2 mb-2 bg-gray-50\"><a href=\"" + escapeHtml(s.url) + "\" target=\"_blank\" class=\"font-medium text-blue-600\">" + escapeHtml(s.title || s.url) + "</a><span class=\"text-xs text-gray-500 ml-2\">" + escapeHtml(s.domain || "") + "</span></div>").join("") : "<p class=\"text-gray-400\">No sources.</p>";
    document.getElementById("paramModalOverlay").classList.add("active");
    document.body.style.overflow = "hidden";
}}

function closeParamModal() {{
    document.getElementById("paramModalOverlay").classList.remove("active");
    document.body.style.overflow = "";
}}

function closeParamModalOnOverlay(e) {{
    if (e.target.id === "paramModalOverlay") closeParamModal();
}}

function escapeHtml(text) {{
    if (!text) return "";
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}}

document.addEventListener("keydown", e => {{ if (e.key === "Escape") closeParamModal(); }});
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
