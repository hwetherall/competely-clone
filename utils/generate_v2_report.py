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


def _build_chat_widget(run_id: str) -> str:
    """Return self-contained HTML/CSS/JS for the floating chat widget."""
    import html as _h
    safe_run_id = _h.escape(run_id)
    # NOTE: this string is *not* inside an f-string template with doubled
    # braces, so normal JS brace syntax works here.
    return f'''
<!-- ======== Chat-with-results widget ======== -->
<style>
#chatFab {{
    position: fixed; bottom: 1.5rem; right: 1.5rem; z-index: 200;
    width: 3.25rem; height: 3.25rem; border-radius: 9999px;
    background: linear-gradient(135deg, #4f46e5, #6366f1);
    color: white; border: none; cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    box-shadow: 0 4px 14px rgba(79,70,229,.45);
    transition: transform .2s, box-shadow .2s;
}}
#chatFab:hover {{ transform: scale(1.08); box-shadow: 0 6px 20px rgba(79,70,229,.55); }}
#chatPanel {{
    position: fixed; bottom: 5.5rem; right: 1.5rem; z-index: 200;
    width: 420px; max-width: calc(100vw - 2rem); height: 560px; max-height: calc(100vh - 7rem);
    background: white; border-radius: 1rem; overflow: hidden;
    box-shadow: 0 25px 60px -12px rgba(0,0,0,.3);
    display: flex; flex-direction: column;
    transition: opacity .25s, transform .25s;
}}
#chatPanel.hidden {{ opacity: 0; pointer-events: none; transform: translateY(12px) scale(.97); }}
#chatMessages {{
    flex: 1; overflow-y: auto; padding: 1rem; display: flex; flex-direction: column; gap: .75rem;
}}
#chatMessages .msg-user {{
    align-self: flex-end; max-width: 80%; background: #4f46e5; color: white;
    padding: .5rem .85rem; border-radius: .85rem .85rem .2rem .85rem;
    font-size: .875rem; line-height: 1.45; word-break: break-word;
}}
#chatMessages .msg-assistant {{
    align-self: flex-start; max-width: 88%; background: #f1f5f9; color: #1e293b;
    padding: .65rem .85rem; border-radius: .85rem .85rem .85rem .2rem;
    font-size: .875rem; line-height: 1.55; word-break: break-word;
}}
#chatMessages .msg-assistant p {{ margin-bottom: .45rem; }}
#chatMessages .msg-assistant p:last-child {{ margin-bottom: 0; }}
#chatMessages .msg-assistant strong {{ font-weight: 600; color: #0f172a; }}
#chatMessages .msg-assistant ul, #chatMessages .msg-assistant ol {{ padding-left: 1.25rem; margin-bottom: .45rem; }}
#chatMessages .msg-assistant li {{ margin-bottom: .2rem; }}
#chatMessages .msg-assistant code {{
    background: #e2e8f0; padding: .1rem .35rem; border-radius: .25rem; font-size: .82rem;
}}
#chatMessages .msg-assistant table {{ border-collapse: collapse; width: 100%; margin: .5rem 0; font-size: .82rem; }}
#chatMessages .msg-assistant th, #chatMessages .msg-assistant td {{
    border: 1px solid #e2e8f0; padding: .3rem .5rem; text-align: left;
}}
#chatMessages .msg-assistant th {{ background: #f8fafc; font-weight: 600; }}
#chatMessages .msg-system {{
    align-self: center; color: #94a3b8; font-size: .78rem; font-style: italic; text-align: center;
}}
#chatInputBar {{
    border-top: 1px solid #e2e8f0; padding: .65rem .85rem; display: flex; gap: .5rem; background: #fafbfc;
}}
#chatInput {{
    flex: 1; border: 1px solid #e2e8f0; border-radius: .65rem; padding: .5rem .75rem;
    font-size: .875rem; outline: none; font-family: inherit; resize: none;
    min-height: 2.25rem; max-height: 6rem;
}}
#chatInput:focus {{ border-color: #818cf8; box-shadow: 0 0 0 2px rgba(129,140,248,.25); }}
#chatSendBtn {{
    background: #4f46e5; color: white; border: none; border-radius: .65rem;
    padding: 0 .85rem; cursor: pointer; font-size: .875rem; font-weight: 500;
    white-space: nowrap; transition: background .15s;
}}
#chatSendBtn:hover {{ background: #4338ca; }}
#chatSendBtn:disabled {{ opacity: .5; cursor: not-allowed; }}
@media print {{ #chatFab, #chatPanel {{ display: none !important; }} }}
@media (max-width: 480px) {{ #chatPanel {{ width: calc(100vw - 1rem); right: .5rem; bottom: 5rem; height: calc(100vh - 6rem); }} #chatFab {{ bottom: 1rem; right: 1rem; }} }}
</style>

<button id="chatFab" class="no-print" title="Chat with your results" aria-label="Open chat">
    <svg width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/>
    </svg>
</button>

<div id="chatPanel" class="hidden no-print" data-run-id="{safe_run_id}">
    <div style="background:linear-gradient(135deg,#1e293b,#0f172a);color:white;padding:.85rem 1rem;display:flex;align-items:center;justify-content:space-between;">
        <div style="display:flex;align-items:center;gap:.5rem;">
            <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/></svg>
            <span style="font-weight:600;font-size:.9rem;">Chat with your results</span>
        </div>
        <button onclick="toggleChat()" style="background:none;border:none;color:#94a3b8;cursor:pointer;padding:4px;" title="Close chat">
            <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
        </button>
    </div>
    <div id="chatMessages">
        <div class="msg-system">Ask anything about this competitive intelligence report.</div>
    </div>
    <div id="chatInputBar">
        <textarea id="chatInput" placeholder="Ask a question..." rows="1"></textarea>
        <button id="chatSendBtn" onclick="sendChatMessage()">Send</button>
    </div>
</div>

<script>
(function() {{
    var CHAT_API_BASE = "http://localhost:8000/api/chat";
    var panel = document.getElementById("chatPanel");
    var fab = document.getElementById("chatFab");
    var input = document.getElementById("chatInput");
    var sendBtn = document.getElementById("chatSendBtn");
    var messagesEl = document.getElementById("chatMessages");
    var runId = panel.getAttribute("data-run-id");
    var history = [];
    var streaming = false;

    /* Move scroll-to-top button up when FAB is visible */
    var scrollBtn = document.getElementById("scrollTopBtn");
    if (scrollBtn) scrollBtn.style.bottom = "5rem";

    window.toggleChat = function() {{
        panel.classList.toggle("hidden");
        if (!panel.classList.contains("hidden")) {{
            input.focus();
        }}
    }};
    fab.addEventListener("click", window.toggleChat);

    /* Auto-resize textarea */
    input.addEventListener("input", function() {{
        this.style.height = "auto";
        this.style.height = Math.min(this.scrollHeight, 96) + "px";
    }});
    input.addEventListener("keydown", function(e) {{
        if (e.key === "Enter" && !e.shiftKey) {{
            e.preventDefault();
            sendChatMessage();
        }}
    }});

    function scrollToBottom() {{
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }}

    function appendMessage(role, html) {{
        var div = document.createElement("div");
        div.className = "msg-" + role;
        div.innerHTML = html;
        messagesEl.appendChild(div);
        scrollToBottom();
        return div;
    }}

    /* Lightweight markdown → HTML (handles bold, italic, lists, code, tables) */
    function mdToHtml(md) {{
        if (!md) return "";
        var s = md;
        // Code blocks
        s = s.replace(/```([\\s\\S]*?)```/g, function(_, c) {{
            return "<pre style='background:#f1f5f9;padding:.5rem;border-radius:.375rem;overflow-x:auto;font-size:.82rem;'><code>" + escapeHtml(c.trim()) + "</code></pre>";
        }});
        // Inline code
        s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
        // Bold
        s = s.replace(/\\*\\*(.+?)\\*\\*/g, "<strong>$1</strong>");
        // Italic
        s = s.replace(/(?<![*])\\*(?![*])(.+?)(?<![*])\\*(?![*])/g, "<em>$1</em>");
        // Tables
        s = s.replace(/((?:^\\|.+\\|\\s*$\\n?)+)/gm, function(table) {{
            var rows = table.trim().split("\\n").filter(function(r) {{ return r.trim() && !/^\\|[\\s-:|]+\\|$/.test(r); }});
            if (rows.length === 0) return table;
            var html = "<table>";
            rows.forEach(function(row, idx) {{
                var cells = row.split("|").filter(function(c,i,a) {{ return i > 0 && i < a.length - 1; }});
                var tag = idx === 0 ? "th" : "td";
                html += "<tr>" + cells.map(function(c) {{ return "<" + tag + ">" + c.trim() + "</" + tag + ">"; }}).join("") + "</tr>";
            }});
            html += "</table>";
            return html;
        }});
        // Unordered lists
        s = s.replace(/^([ \\t]*)[-*]\\s+(.+)$/gm, "$1<li>$2</li>");
        s = s.replace(/((?:<li>.*<\\/li>\\s*)+)/g, "<ul>$1</ul>");
        // Ordered lists
        s = s.replace(/^([ \\t]*)\\d+\\.\\s+(.+)$/gm, "$1<li>$2</li>");
        // Headings
        s = s.replace(/^#### (.+)$/gm, "<h4 style='font-weight:600;font-size:.9rem;margin:.6rem 0 .3rem;'>$1</h4>");
        s = s.replace(/^### (.+)$/gm, "<h3 style='font-weight:600;font-size:.95rem;margin:.7rem 0 .35rem;'>$1</h3>");
        s = s.replace(/^## (.+)$/gm, "<h2 style='font-weight:600;font-size:1rem;margin:.8rem 0 .4rem;border-bottom:1px solid #e2e8f0;padding-bottom:.2rem;'>$1</h2>");
        // Paragraphs (double newline)
        s = s.replace(/\\n\\n+/g, "</p><p>");
        s = "<p>" + s + "</p>";
        s = s.replace(/<p><\\/p>/g, "");
        // Clean up nested block issues
        s = s.replace(/<p>(<(?:h[2-4]|ul|ol|table|pre))/g, "$1");
        s = s.replace(/(<\\/(?:h[2-4]|ul|ol|table|pre)>)<\\/p>/g, "$1");
        return s;
    }}

    window.sendChatMessage = function() {{
        if (streaming) return;
        var text = input.value.trim();
        if (!text) return;
        input.value = "";
        input.style.height = "auto";

        appendMessage("user", escapeHtml(text));
        history.push({{ role: "user", content: text }});

        var assistantDiv = appendMessage("assistant", "<span style='color:#94a3b8;'>Thinking...</span>");
        streaming = true;
        sendBtn.disabled = true;

        var accum = "";
        fetch(CHAT_API_BASE + "/" + encodeURIComponent(runId), {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{ message: text, history: history.slice(0, -1) }})
        }}).then(function(resp) {{
            if (!resp.ok) throw new Error("Chat API error " + resp.status);
            var reader = resp.body.getReader();
            var decoder = new TextDecoder();
            var buf = "";

            function read() {{
                return reader.read().then(function(result) {{
                    if (result.done) {{
                        if (accum) history.push({{ role: "assistant", content: accum }});
                        streaming = false;
                        sendBtn.disabled = false;
                        return;
                    }}
                    buf += decoder.decode(result.value, {{ stream: true }});
                    var lines = buf.split("\\n");
                    buf = lines.pop();
                    lines.forEach(function(line) {{
                        if (!line.startsWith("data: ")) return;
                        var payload = line.slice(6);
                        if (payload === "[DONE]") return;
                        try {{
                            var obj = JSON.parse(payload);
                            if (obj.error) {{
                                assistantDiv.innerHTML = "<span style='color:#ef4444;'>Error: " + escapeHtml(obj.error) + "</span>";
                                streaming = false;
                                sendBtn.disabled = false;
                                return;
                            }}
                            if (obj.token) {{
                                accum += obj.token;
                                assistantDiv.innerHTML = mdToHtml(accum);
                                scrollToBottom();
                            }}
                        }} catch(e) {{}}
                    }});
                    return read();
                }});
            }}
            return read();
        }}).catch(function(err) {{
            assistantDiv.innerHTML = "<span style='color:#ef4444;'>Connection error: " + escapeHtml(err.message) + ". Make sure the backend is running on localhost:8000.</span>";
            streaming = false;
            sendBtn.disabled = false;
        }});
    }};
}})();
</script>
'''


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

    _avatar_colors = ["#6366f1", "#0891b2", "#059669", "#d97706", "#dc2626", "#7c3aed", "#db2777", "#2563eb"]
    def _avatar_color(idx):
        return _avatar_colors[idx % len(_avatar_colors)]

    companies = data.get("companies", [])
    parameters = data.get("parameters", [])
    parameter_definitions = data.get("parameter_definitions", {})
    analyses = data.get("analyses", {})
    executive = data.get("executive", {})
    metadata = data.get("metadata", {})
    parameter_path = metadata.get("parameter_path", "competely")
    is_avis = parameter_path == "avis"

    # Graveyard / Post-Mortem Intelligence data
    postmortem = data.get("postmortem_brief", {})
    graveyard_cos = data.get("graveyard_companies", [])
    graveyard_analyses = data.get("graveyard_analyses", {})
    has_graveyard = bool(postmortem and postmortem.get("failure_patterns"))

    risk_overlay_map = {}
    for ro in postmortem.get("risk_overlays", []):
        risk_overlay_map[ro.get("white_space_opportunity", "")] = ro

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

    # Add graveyard analyses to modal_data for deep-dive modals
    for gy_pid, gy_a in graveyard_analyses.items():
        gy_full_md = gy_a.get("full_report_markdown", "")
        gy_full_md_bolded = bold_lead_in_markdown(gy_full_md)
        gy_full_html = markdown.markdown(gy_full_md_bolded, extensions=["extra"]) if gy_full_md else "<p>No full report.</p>"
        gy_full_html = bold_lead_in_html(gy_full_html)
        gy_ws_raw = gy_a.get("white_space", []) or []
        gy_tr_raw = gy_a.get("trends", []) or []
        modal_data[gy_pid] = {
            "parameter_name": gy_a.get("parameter_name", gy_pid),
            "executive_summary": gy_a.get("executive_summary", ""),
            "positioning_table": gy_a.get("positioning_table", []),
            "full_report_html": gy_full_html,
            "white_space": gy_ws_raw,
            "white_space_display": [bold_lead(w) for w in gy_ws_raw],
            "trends": gy_tr_raw,
            "trends_display": [bold_lead(t) for t in gy_tr_raw],
            "sources": gy_a.get("sources", []),
            "confidence": gy_a.get("confidence", "unknown"),
        }

    brief = executive.get("brief", "No executive brief generated.")

    def extract_tldr(text, max_sentences=2):
        """Pull the first 1-2 sentences as a TL;DR / BLUF."""
        import re
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text.strip())
        tldr_parts = sentences[:max_sentences]
        return " ".join(tldr_parts).strip()

    def bold_company_names(escaped_html, company_list):
        """Wrap known company names in <strong> tags (single-pass, longest-match)."""
        import re
        _legal_suffixes = re.compile(
            r',?\s*\b(Inc\.?|LLC|Ltd\.?|Co\.?|Corp\.?|Corporation|Incorporated|Company|Stores|Entertainment)\b[.,]*\s*',
            re.IGNORECASE,
        )
        names = set()
        for c in company_list:
            clean = _legal_suffixes.sub("", c).strip().rstrip(",. ")
            clean = re.sub(r'\.\w+$', '', clean)
            if clean and len(clean) > 2:
                names.add(clean)
            first_word = clean.split()[0] if clean else ""
            if first_word and len(first_word) > 3 and first_word != clean:
                names.add(first_word)
        escaped_names = sorted(
            [html_escape.escape(n) for n in names], key=len, reverse=True
        )
        alt = "|".join(re.escape(n) for n in escaped_names)
        if not alt:
            return escaped_html
        pattern = re.compile(r'(?<!\w)(' + alt + r')(?!\w)')
        # Single pass: only bold text outside of HTML tags
        parts = re.split(r'(<[^>]*>)', escaped_html)
        for i, part in enumerate(parts):
            if not part.startswith("<"):
                parts[i] = pattern.sub(r'<strong>\1</strong>', part)
        return "".join(parts)

    brief_tldr = extract_tldr(brief)
    brief_rest = brief[len(brief_tldr):].strip() if brief_tldr != brief else ""

    key_themes = executive.get("key_themes", [])
    trends = executive.get("trends", [])
    ws_opportunities = executive.get("white_space_opportunities", [])
    ws_matrix = executive.get("white_space_matrix", {})
    next_steps = executive.get("next_steps", {})
    venture_context = executive.get("venture_context", "")
    typology_distribution = metadata.get("typology_distribution", {}) or {}
    coverage_check = metadata.get("coverage_check", {}) or {}
    commercial_summary_html = ""
    if typology_distribution or coverage_check:
        typology_badges = "".join(
            f'<span class="inline-flex items-center rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700">{html_escape.escape(str(k).replace("_", " ").title())}: {int(v)}</span>'
            for k, v in typology_distribution.items()
        )
        coverage_line = ""
        gaps_html = ""
        if coverage_check:
            covered = coverage_check.get("covered_checks", 0)
            total = coverage_check.get("total_checks", 0)
            gap_count = coverage_check.get("gap_count", 0)
            coverage_line = f'<p class="text-sm text-slate-600">{covered} of {total} commercial question checks covered. {gap_count} gaps surfaced.</p>'
            gaps = coverage_check.get("gaps", []) or []
            if gaps:
                rows = "".join(
                    "<tr class='border-b border-slate-100'>"
                    f"<td class='px-3 py-2'>{html_escape.escape(str(g.get('company', '')))}</td>"
                    f"<td class='px-3 py-2'>{html_escape.escape(str(g.get('question', '')))}</td>"
                    f"<td class='px-3 py-2'>{html_escape.escape(str(g.get('reason', '')))}</td>"
                    "</tr>"
                    for g in gaps[:30]
                )
                gaps_html = (
                    "<div class='mt-4 overflow-x-auto rounded-lg border border-slate-200'>"
                    "<table class='min-w-full text-xs'><thead><tr class='bg-slate-50 text-slate-600'>"
                    "<th class='px-3 py-2 text-left font-semibold'>Company</th>"
                    "<th class='px-3 py-2 text-left font-semibold'>Question</th>"
                    "<th class='px-3 py-2 text-left font-semibold'>Reason</th>"
                    f"</tr></thead><tbody>{rows}</tbody></table></div>"
                )
        commercial_summary_html = f"""
    <section id="commercial-deep-dive" class="mb-12 animate-fade-in">
        <div class="rounded-xl border border-slate-200 bg-white shadow-sm p-6 md:p-8">
            <h2 class="text-2xl font-display font-bold text-slate-900 mb-4">Commercial Deep Dive</h2>
            {f'<div class="mb-4 flex flex-wrap gap-2">{typology_badges}</div>' if typology_badges else ''}
            {coverage_line}
            {gaps_html}
        </div>
    </section>
        """

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

    # Key themes: scannable headline + smaller detail text
    themes_html = ""
    if key_themes:
        theme_cards = []
        for t in key_themes:
            if ":" in t:
                idx = t.index(":")
                headline = t[:idx].strip()
                detail = t[idx + 1:].strip()
                theme_cards.append(
                    f'<div class="rounded-lg border border-slate-200 bg-white p-4 border-l-4 border-l-indigo-500 hover:border-l-indigo-600 hover:shadow-sm transition-all">'
                    f'<h4 class="font-semibold text-slate-900 text-sm mb-1.5">{html_escape.escape(headline)}</h4>'
                    f'<p class="text-xs text-slate-500 leading-relaxed">{html_escape.escape(detail)}</p>'
                    f'</div>'
                )
            else:
                theme_cards.append(
                    f'<div class="rounded-lg border border-slate-200 bg-white p-4 border-l-4 border-l-indigo-500 hover:border-l-indigo-600 hover:shadow-sm transition-all">'
                    f'<p class="text-sm text-slate-700 leading-relaxed">{html_escape.escape(t)}</p>'
                    f'</div>'
                )
        themes_html = '<div class="grid gap-3 sm:grid-cols-2">' + "".join(theme_cards) + '</div>'

    # Company short-name + avatar color mapping for impact pills
    import re as _re
    _legal_sfx = _re.compile(
        r',?\s*\b(Inc\.?|LLC|Ltd\.?|Co\.?|Corp\.?|Corporation|Incorporated|Company|Stores|Entertainment)\b[.,]*\s*',
        _re.IGNORECASE,
    )
    _generic_words = {"wholesale", "holdings", "group", "enterprises", "industries", "international", "services"}
    company_pill_info = []  # [(search_pattern, display_name, initial, color_hex)]
    for ci, c in enumerate(companies):
        clean = _legal_sfx.sub("", c).strip().rstrip(",. ")
        clean = _re.sub(r'\.\w+$', '', clean)
        words = clean.split() if clean else [c]
        first_word = words[0]
        display = first_word if len(words) > 1 and words[-1].lower() in _generic_words else (clean or c)
        search_key = first_word.lower()
        company_pill_info.append((search_key, display, display[0], _avatar_color(ci)))

    def detect_company_pills(text):
        pills = []
        text_lower = text.lower()
        for search_key, display, initial, color in company_pill_info:
            if _re.search(r'(?<!\w)' + _re.escape(search_key) + r'(?!\w)', text_lower):
                pills.append(
                    f'<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium text-white" '
                    f'style="background:{color}">{html_escape.escape(initial)}&nbsp;{html_escape.escape(display)}</span>'
                )
        return "".join(pills)

    # Trends section - numbered cards with company impact pills
    trends_html = ""
    if trends:
        card_items = []
        for i, t in enumerate(trends, 1):
            pills = detect_company_pills(t)
            pills_row = f'<div class="flex flex-wrap gap-1.5 mt-2.5">{pills}</div>' if pills else ""
            card_items.append(
                f'<div class="flex gap-4 rounded-lg bg-gradient-to-r from-slate-50 to-white border border-slate-200 p-4 items-start">'
                f'<span class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-indigo-700 font-semibold text-sm">{i}</span>'
                f'<div class="flex-1">'
                f'<p class="text-sm text-slate-700 leading-relaxed">{bold_lead(t)}</p>'
                f'{pills_row}'
                f'</div>'
                f'</div>'
            )
        trends_html = '<div class="space-y-3">' + "".join(card_items) + '</div>'

    # White Space Opportunities (Option B) - numbered circle badge + colored sidebar stripe
    stripe_color = {"Low": "border-l-emerald-500", "Medium": "border-l-amber-500", "High": "border-l-rose-500"}
    risk_badge_colors = {
        "High": ("bg-rose-50 border-rose-200", "text-rose-700 bg-rose-100 border-rose-200"),
        "Medium": ("bg-amber-50 border-amber-200", "text-amber-700 bg-amber-100 border-amber-200"),
        "Low": ("bg-emerald-50 border-emerald-200", "text-emerald-700 bg-emerald-100 border-emerald-200"),
    }

    difficulty_badge = {
        "High": "text-rose-700 bg-rose-50 border-rose-200",
        "Medium": "text-amber-700 bg-amber-50 border-amber-200",
        "Low": "text-emerald-700 bg-emerald-50 border-emerald-200",
    }

    ws_opps_html = ""
    if ws_opportunities:
        ws_opps_html = '<div class="space-y-4">'
        for i, opp in enumerate(ws_opportunities, 1):
            opportunity = html_escape.escape(opp.get("opportunity", ""))
            opp_raw = opp.get("opportunity", "")
            why_raw = opp.get("why_it_exists", "")
            why = html_escape.escape(why_raw)
            closest = html_escape.escape(opp.get("who_is_closest", ""))
            difficulty = opp.get("entry_difficulty", "")
            stripe = stripe_color.get(difficulty, "border-l-slate-400")
            diff_cls = difficulty_badge.get(difficulty, "text-slate-600 bg-slate-50 border-slate-200")

            # Extract first sentence as preview for "Why it exists"
            why_sentences = _re.split(r'(?<=[.!?])\s+(?=[A-Z])', why_raw.strip())
            why_preview = html_escape.escape(why_sentences[0]) if why_sentences else why
            why_has_more = len(why_sentences) > 1

            # Company pills from the full card text
            full_text = opp_raw + " " + opp.get("why_it_exists", "") + " " + opp.get("who_is_closest", "")
            pills = detect_company_pills(full_text)

            matched_overlay = None
            for ro_key, ro_val in risk_overlay_map.items():
                if opp_raw and opp_raw in ro_key:
                    matched_overlay = ro_val
                    break

            ws_opps_html += (
                f'<div class="rounded-lg border border-slate-200 bg-white {stripe} border-l-4 overflow-hidden">'
                f'<div class="p-5">'
                # Title row with number badge, title, and difficulty badge inline
                f'<div class="flex items-start gap-3 mb-3">'
                f'<span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-white font-bold text-sm">{i}</span>'
                f'<div class="flex-1 min-w-0">'
                f'<div class="flex items-start justify-between gap-3">'
                f'<h4 class="font-semibold text-slate-900 text-base leading-snug">{opportunity}</h4>'
                f'<span class="shrink-0 px-2.5 py-0.5 rounded-full text-xs font-semibold border {diff_cls}">{html_escape.escape(difficulty)} Difficulty</span>'
                f'</div>'
                f'</div>'
                f'</div>'
            )

            # "Why it exists" with truncation
            if why_has_more:
                uid = f"ws-why-{i}"
                ws_opps_html += (
                    f'<div class="pl-12 mb-3">'
                    f'<p class="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Why it exists</p>'
                    f'<p class="text-sm text-slate-600 leading-relaxed" id="{uid}-preview">{why_preview} '
                    f'<button onclick="document.getElementById(\'{uid}-preview\').style.display=\'none\';document.getElementById(\'{uid}-full\').style.display=\'block\';" '
                    f'class="text-indigo-600 hover:text-indigo-700 font-medium text-sm">Show more</button></p>'
                    f'<div id="{uid}-full" style="display:none">'
                    f'<p class="text-sm text-slate-600 leading-relaxed">{why} '
                    f'<button onclick="document.getElementById(\'{uid}-full\').style.display=\'none\';document.getElementById(\'{uid}-preview\').style.display=\'block\';" '
                    f'class="text-indigo-600 hover:text-indigo-700 font-medium text-sm">Show less</button></p>'
                    f'</div>'
                    f'</div>'
                )
            else:
                ws_opps_html += (
                    f'<div class="pl-12 mb-3">'
                    f'<p class="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Why it exists</p>'
                    f'<p class="text-sm text-slate-600 leading-relaxed">{why}</p>'
                    f'</div>'
                )

            # "Best positioned" as a highlighted row with company pills
            ws_opps_html += (
                f'<div class="ml-12 rounded-lg bg-slate-50 border border-slate-100 px-4 py-3 flex flex-col gap-2">'
                f'<div class="flex items-start gap-2">'
                f'<svg class="w-4 h-4 text-indigo-500 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">'
                f'<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"/></svg>'
                f'<p class="text-sm text-slate-700"><span class="font-medium text-slate-900">Best positioned:</span> {closest}</p>'
                f'</div>'
            )
            if pills:
                ws_opps_html += f'<div class="flex flex-wrap gap-1.5">{pills}</div>'
            ws_opps_html += '</div>'

            ws_opps_html += '</div>'  # close p-5

            if matched_overlay:
                rl = matched_overlay.get("risk_level", "Medium")
                panel_cls, badge_cls = risk_badge_colors.get(rl, ("bg-slate-50 border-slate-200", "text-slate-700 bg-slate-100 border-slate-200"))
                precedent = html_escape.escape(matched_overlay.get("historical_precedent", ""))
                mitigation = html_escape.escape(matched_overlay.get("mitigation_guidance", ""))
                ws_opps_html += (
                    f'<details class="border-t border-slate-100 group/risk">'
                    f'<summary class="px-5 py-3 text-sm font-medium text-slate-500 cursor-pointer hover:bg-slate-50 transition-colors flex items-center gap-2">'
                    f'<svg class="w-4 h-4 text-slate-400 shrink-0 transition-transform group-open/risk:rotate-90" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>'
                    f'<span>Historical Risk Assessment</span>'
                    f'<span class="ml-auto px-2.5 py-0.5 rounded-full text-xs font-semibold border {badge_cls}">{html_escape.escape(rl)} Risk</span>'
                    f'</summary>'
                    f'<div class="px-5 pb-5 pt-1">'
                    f'<div class="grid md:grid-cols-2 gap-4">'
                    f'<div class="rounded-lg {panel_cls} border p-4">'
                    f'<p class="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Historical Precedent</p>'
                    f'<p class="text-sm text-slate-700 leading-relaxed">{precedent}</p>'
                    f'</div>'
                    f'<div class="rounded-lg bg-slate-50 border border-slate-200 p-4">'
                    f'<p class="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Mitigation Guidance</p>'
                    f'<p class="text-sm text-slate-700 leading-relaxed">{mitigation}</p>'
                    f'</div>'
                    f'</div>'
                    f'</div>'
                    f'</details>'
                )

            ws_opps_html += '</div>'
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
                for j, item in enumerate(items):
                    action = html_escape.escape(item.get("action", ""))
                    rationale = html_escape.escape(item.get("rationale", ""))
                    priority = item.get("priority", "")
                    dot = pri_dot.get(priority, "bg-slate-400")
                    rid = f"ns-{key}-{j}"
                    next_steps_html += (
                        f'<div class="rounded-lg border border-slate-100 bg-slate-50/50 p-4 cursor-pointer hover:border-slate-300 transition-colors" '
                        f'onclick="var el=document.getElementById(\'{rid}\');el.style.display=el.style.display===\'none\'?\'block\':\'none\'">'
                        f'<div class="flex items-start gap-3">'
                        f'<span class="mt-1.5 h-2 w-2 shrink-0 rounded-full {dot}"></span>'
                        f'<p class="text-sm font-medium text-slate-900 flex-1">{action}</p>'
                        f'<svg class="w-4 h-4 text-slate-400 shrink-0 mt-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>'
                        f'</div>'
                        f'<p id="{rid}" class="text-xs text-slate-500 pl-5 mt-2" style="display:none">{rationale}</p>'
                        f'</div>'
                    )
                next_steps_html += '</div></div>'
        next_steps_html += '</div>'

    # =========================================================================
    # AVIS-specific analytical frameworks
    # =========================================================================
    avis_frameworks_html = ""
    if is_avis:
        avis_parts = []

        # --- Moat Analysis Grid ---
        moat_grid = executive.get("moat_analysis_grid", [])
        if moat_grid:
            moat_type_labels = {
                "brand": ("Brand", "indigo"),
                "data": ("Data", "emerald"),
                "switching_costs": ("Switching Costs", "violet"),
                "ip_patents": ("IP & Patents", "blue"),
                "network_effects": ("Network Effects", "amber"),
                "regulatory": ("Regulatory", "rose"),
                "scale_economies": ("Scale Economies", "cyan"),
            }
            strength_colors = {
                "Strong": "bg-emerald-100 text-emerald-800 border-emerald-200",
                "Moderate": "bg-amber-100 text-amber-800 border-amber-200",
                "Weak": "bg-rose-100 text-rose-800 border-rose-200",
                "None": "bg-slate-100 text-slate-500 border-slate-200",
            }
            durability_colors = {
                "High": "bg-emerald-600",
                "Medium": "bg-amber-500",
                "Low": "bg-rose-500",
            }

            avis_parts.append(
                '<details class="print-expand border-t border-slate-200" id="moat-grid">'
                '<summary class="p-6 font-semibold text-slate-800 cursor-pointer hover:bg-slate-50 transition-colors">'
                'AVIS: Moat Analysis Grid</summary>'
                '<div class="px-6 pb-6 pt-2">'
                '<p class="text-sm text-slate-500 mb-4">Defensibility assessment across 7 moat dimensions per competitor.</p>'
                '<div class="space-y-4">'
            )
            for entry in moat_grid:
                co = html_escape.escape(entry.get("company", ""))
                dur = entry.get("overall_durability", "Medium")
                dur_dot = durability_colors.get(dur, "bg-slate-400")
                dur_rationale = html_escape.escape(entry.get("durability_rationale", ""))
                sources = entry.get("moat_sources", {})

                moat_cells = ""
                for mtype, (label, _color) in moat_type_labels.items():
                    src = sources.get(mtype, {})
                    if isinstance(src, dict):
                        strength = src.get("strength", "None")
                        detail = html_escape.escape(src.get("detail", ""))
                    else:
                        strength = str(src) if src else "None"
                        detail = ""
                    cls = strength_colors.get(strength, strength_colors["None"])
                    moat_cells += (
                        f'<div class="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">'
                        f'<span class="text-sm text-slate-600 font-medium">{label}</span>'
                        f'<div class="flex items-center gap-2">'
                        f'<span class="px-2 py-0.5 rounded-full text-xs font-semibold border {cls}">{html_escape.escape(strength)}</span>'
                        f'</div>'
                        f'</div>'
                    )
                    if detail:
                        moat_cells += f'<p class="text-xs text-slate-500 pb-2 -mt-1 pl-2">{detail}</p>'

                avis_parts.append(
                    f'<div class="rounded-xl border border-slate-200 bg-white overflow-hidden">'
                    f'<div class="bg-slate-800 px-5 py-3 flex items-center justify-between">'
                    f'<h4 class="font-semibold text-white">{co}</h4>'
                    f'<div class="flex items-center gap-2">'
                    f'<span class="h-2.5 w-2.5 rounded-full {dur_dot}"></span>'
                    f'<span class="text-xs text-slate-300 font-medium">{html_escape.escape(dur)} Durability</span>'
                    f'</div></div>'
                    f'<div class="p-5">{moat_cells}'
                    f'<p class="text-xs text-slate-500 mt-3 italic">{dur_rationale}</p>'
                    f'</div></div>'
                )
            avis_parts.append('</div></div></details>')

        # --- Threat Matrix ---
        threat_matrix = executive.get("threat_matrix", [])
        if threat_matrix:
            avis_parts.append(
                '<details class="print-expand border-t border-slate-200" id="threat-matrix">'
                '<summary class="p-6 font-semibold text-slate-800 cursor-pointer hover:bg-slate-50 transition-colors">'
                'AVIS: Threat Matrix</summary>'
                '<div class="px-6 pb-6 pt-2">'
                '<p class="text-sm text-slate-500 mb-4">Head-to-head competitive risk assessment per company.</p>'
                '<div class="grid gap-4 md:grid-cols-2">'
            )
            for entry in threat_matrix:
                co = html_escape.escape(entry.get("company", ""))
                beats = entry.get("beats_others_on", [])
                loses = entry.get("loses_to_others_on", [])
                biggest = html_escape.escape(entry.get("biggest_threat_from", ""))
                stealth = html_escape.escape(entry.get("stealth_threats", ""))

                beats_html = "".join(
                    f'<span class="inline-block px-2 py-0.5 rounded-full text-xs bg-emerald-100 text-emerald-800 border border-emerald-200 mr-1 mb-1">{html_escape.escape(b)}</span>'
                    for b in beats
                )
                loses_html = "".join(
                    f'<span class="inline-block px-2 py-0.5 rounded-full text-xs bg-rose-100 text-rose-800 border border-rose-200 mr-1 mb-1">{html_escape.escape(l)}</span>'
                    for l in loses
                )

                avis_parts.append(
                    f'<div class="rounded-xl border border-slate-200 bg-white p-5">'
                    f'<h4 class="font-semibold text-slate-900 mb-3">{co}</h4>'
                    f'<div class="space-y-2 text-sm">'
                    f'<div><span class="text-xs font-semibold text-slate-500 uppercase">Wins on:</span><div class="mt-1">{beats_html or "<span class=\'text-slate-400 text-xs\'>None identified</span>"}</div></div>'
                    f'<div><span class="text-xs font-semibold text-slate-500 uppercase">Loses on:</span><div class="mt-1">{loses_html or "<span class=\'text-slate-400 text-xs\'>None identified</span>"}</div></div>'
                    f'<div class="pt-2 border-t border-slate-100"><span class="text-xs font-semibold text-slate-500 uppercase">Biggest threat:</span><p class="text-xs text-slate-600 mt-0.5">{biggest}</p></div>'
                )
                if stealth and stealth.lower() != "none identified":
                    avis_parts.append(
                        f'<div><span class="text-xs font-semibold text-amber-600 uppercase">Stealth threats:</span>'
                        f'<p class="text-xs text-slate-600 mt-0.5">{stealth}</p></div>'
                    )
                avis_parts.append('</div></div>')

            avis_parts.append('</div></div></details>')

        # --- Value Curve Assessment ---
        value_curve = executive.get("value_curve_assessment", {})
        dimensions = value_curve.get("dimensions", [])
        scores = value_curve.get("company_scores", {})
        if dimensions and scores:
            parity = value_curve.get("parity_zones", [])
            diff = value_curve.get("differentiation_zones", [])
            ws_dims = value_curve.get("white_space_dimensions", [])

            # Build HTML table
            header_cells = '<th class="border border-slate-200 p-2 bg-slate-100 text-xs font-semibold text-slate-600">Dimension</th>'
            for co in companies:
                header_cells += f'<th class="border border-slate-200 p-2 bg-slate-100 text-xs font-semibold text-slate-600">{html_escape.escape(co)}</th>'

            body_rows = ""
            score_colors = {5: "bg-emerald-500", 4: "bg-emerald-400", 3: "bg-amber-400", 2: "bg-orange-400", 1: "bg-rose-400"}
            for dim in dimensions:
                dim_cls = ""
                if dim in ws_dims:
                    dim_cls = " bg-rose-50"
                elif dim in diff:
                    dim_cls = " bg-indigo-50"
                elif dim in parity:
                    dim_cls = " bg-slate-50"

                body_rows += f'<tr class="{dim_cls}"><td class="border border-slate-200 p-2 text-sm font-medium text-slate-700">{html_escape.escape(dim)}</td>'
                for co in companies:
                    co_scores = scores.get(co, {})
                    score = co_scores.get(dim, "—")
                    if isinstance(score, (int, float)):
                        bg = score_colors.get(int(score), "bg-slate-300")
                        body_rows += f'<td class="border border-slate-200 p-2 text-center"><span class="inline-flex h-7 w-7 items-center justify-center rounded-full text-white text-xs font-bold {bg}">{score}</span></td>'
                    else:
                        body_rows += f'<td class="border border-slate-200 p-2 text-center text-slate-400 text-sm">{html_escape.escape(str(score))}</td>'
                body_rows += '</tr>'

            legend_items = []
            if parity:
                legend_items.append(f'<span class="inline-block px-2 py-0.5 rounded bg-slate-100 text-xs text-slate-600 border border-slate-200">Parity zones: {", ".join(html_escape.escape(p) for p in parity[:3])}</span>')
            if diff:
                legend_items.append(f'<span class="inline-block px-2 py-0.5 rounded bg-indigo-50 text-xs text-indigo-700 border border-indigo-200">Differentiation: {", ".join(html_escape.escape(d) for d in diff[:3])}</span>')
            if ws_dims:
                legend_items.append(f'<span class="inline-block px-2 py-0.5 rounded bg-rose-50 text-xs text-rose-700 border border-rose-200">White space: {", ".join(html_escape.escape(w) for w in ws_dims[:3])}</span>')
            legend_html = " ".join(legend_items) if legend_items else ""

            avis_parts.append(
                '<details class="print-expand border-t border-slate-200" id="value-curve">'
                '<summary class="p-6 font-semibold text-slate-800 cursor-pointer hover:bg-slate-50 transition-colors">'
                'AVIS: Feature &amp; Value Curve</summary>'
                '<div class="px-6 pb-6 pt-2">'
                '<p class="text-sm text-slate-500 mb-2">Scores from 1 (laggard) to 5 (leader) across key competitive dimensions.</p>'
                f'<div class="flex flex-wrap gap-2 mb-4">{legend_html}</div>'
                '<div class="overflow-x-auto">'
                f'<table class="min-w-full border border-slate-200 text-sm"><thead><tr>{header_cells}</tr></thead><tbody>{body_rows}</tbody></table>'
                '</div></div></details>'
            )

        if avis_parts:
            avis_frameworks_html = "\n".join(avis_parts)

    # Post-Mortem Intelligence section — comprehensive redesign
    postmortem_html = ""
    if has_graveyard:
        pm = []

        # --- Dark header with company roster ---
        co_badges = "".join(
            f'<span class="px-3 py-1 rounded-full text-xs font-medium bg-white/10 text-slate-300 border border-white/20">'
            f'{html_escape.escape(c.get("name", "") if isinstance(c, dict) else str(c))}</span>'
            for c in graveyard_cos
        )
        pm.append(
            '<section id="postmortem" class="mb-12 animate-fade-in">'
            '<div class="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">'
            '<div class="bg-gradient-to-br from-slate-800 via-slate-900 to-slate-800 px-6 py-8 md:px-8">'
            '<div class="flex items-start gap-3 mb-3">'
            '<svg class="w-7 h-7 text-rose-400 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">'
            '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" '
            'd="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/>'
            '</svg>'
            '<div>'
            '<h2 class="text-2xl font-display font-bold text-white mb-1">Post-Mortem Intelligence</h2>'
            f'<p class="text-slate-400 text-sm">What {len(graveyard_cos)} failed competitors reveal about the risks ahead</p>'
            '</div>'
            '</div>'
            f'<div class="flex flex-wrap gap-2 mt-4">{co_badges}</div>'
            '</div>'
        )

        # --- Stat summary bar ---
        fp_count = len(postmortem.get("failure_patterns", []))
        sv_count = len(postmortem.get("structural_vulnerabilities", []))
        cn_count = len(postmortem.get("cautionary_narratives", []))
        ro_count = len(postmortem.get("risk_overlays", []))
        sp_count = len(postmortem.get("survival_principles", []))
        pm.append(
            '<div class="grid grid-cols-2 md:grid-cols-5 gap-px bg-slate-200 border-b border-slate-200">'
            f'<div class="bg-slate-50 px-4 py-3 text-center"><p class="text-xl font-bold text-slate-900">{cn_count}</p><p class="text-xs text-slate-500 font-medium">Case Studies</p></div>'
            f'<div class="bg-slate-50 px-4 py-3 text-center"><p class="text-xl font-bold text-slate-900">{fp_count}</p><p class="text-xs text-slate-500 font-medium">Failure Patterns</p></div>'
            f'<div class="bg-slate-50 px-4 py-3 text-center"><p class="text-xl font-bold text-slate-900">{sv_count}</p><p class="text-xs text-slate-500 font-medium">Vulnerabilities</p></div>'
            f'<div class="bg-slate-50 px-4 py-3 text-center"><p class="text-xl font-bold text-slate-900">{ro_count}</p><p class="text-xs text-slate-500 font-medium">Risk Overlays</p></div>'
            f'<div class="bg-slate-50 px-4 py-3 text-center"><p class="text-xl font-bold text-slate-900">{sp_count}</p><p class="text-xs text-slate-500 font-medium">Survival Rules</p></div>'
            '</div>'
        )

        pm.append('<div class="p-6 md:p-8">')

        # --- Cautionary Narratives (hero content — the stories that stick) ---
        cn = postmortem.get("cautionary_narratives", [])
        if cn:
            pm.append(
                '<div class="mb-10">'
                '<h3 class="text-lg font-display font-semibold text-slate-800 mb-1">Cautionary Narratives</h3>'
                '<p class="text-sm text-slate-500 mb-6">The stories behind each failure &mdash; from peak to collapse</p>'
                '<div class="space-y-6">'
            )
            for n in cn:
                co = html_escape.escape(n.get("company", ""))
                fm = html_escape.escape(n.get("failure_mode", ""))
                pp = html_escape.escape(n.get("peak_position", ""))
                narr = html_escape.escape(n.get("narrative", ""))
                lesson = html_escape.escape(n.get("key_lesson", ""))

                pm.append(
                    f'<div class="rounded-xl border border-slate-200 overflow-hidden hover:shadow-md transition-shadow">'
                    f'<div class="bg-gradient-to-r from-slate-800 to-slate-700 px-5 py-4 flex items-center justify-between">'
                    f'<h4 class="font-semibold text-white text-base">{co}</h4>'
                    f'<span class="text-xs px-3 py-1 rounded-full bg-rose-500/20 text-rose-300 font-medium border border-rose-500/30">{fm}</span>'
                    f'</div>'
                )
                if pp:
                    pm.append(
                        f'<div class="px-5 py-3 bg-slate-50 border-b border-slate-200">'
                        f'<p class="text-sm text-slate-600"><span class="font-medium text-slate-500">At their peak:</span> {pp}</p>'
                        f'</div>'
                    )
                if narr:
                    pm.append(
                        f'<div class="px-5 py-4">'
                        f'<p class="text-sm text-slate-700 leading-relaxed">{narr}</p>'
                        f'</div>'
                    )
                if lesson:
                    pm.append(
                        f'<div class="mx-5 mb-5 rounded-lg bg-amber-50 border border-amber-200 p-4">'
                        f'<div class="flex gap-3">'
                        f'<svg class="w-5 h-5 text-amber-500 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">'
                        f'<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" '
                        f'd="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>'
                        f'</svg>'
                        f'<p class="text-sm text-amber-900 leading-relaxed"><strong>Key lesson:</strong> {lesson}</p>'
                        f'</div>'
                        f'</div>'
                    )
                pm.append('</div>')
            pm.append('</div></div>')

        # --- Failure Patterns (collapsible, rose-tinted cards) ---
        fp = postmortem.get("failure_patterns", [])
        if fp:
            pm.append(
                '<details class="mb-8 group" open>'
                '<summary class="flex items-center gap-2 cursor-pointer mb-4 select-none">'
                '<svg class="w-5 h-5 text-rose-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">'
                '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>'
                '</svg>'
                f'<h3 class="text-lg font-display font-semibold text-slate-800">Failure Patterns</h3>'
                f'<span class="text-xs text-slate-400 ml-1">({len(fp)} identified)</span>'
                '</summary>'
                '<div class="space-y-3">'
            )
            for p in fp:
                pm.append(
                    f'<div class="rounded-lg border border-rose-100 bg-rose-50/50 p-4 border-l-4 border-l-rose-400">'
                    f'<p class="text-sm text-slate-700 leading-relaxed">{bold_lead(p)}</p>'
                    f'</div>'
                )
            pm.append('</div></details>')

        # --- Structural Vulnerabilities (collapsible, amber-tinted cards) ---
        sv = postmortem.get("structural_vulnerabilities", [])
        if sv:
            pm.append(
                '<details class="mb-8 group" open>'
                '<summary class="flex items-center gap-2 cursor-pointer mb-4 select-none">'
                '<svg class="w-5 h-5 text-amber-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">'
                '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" '
                'd="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/>'
                '</svg>'
                f'<h3 class="text-lg font-display font-semibold text-slate-800">Structural Vulnerabilities</h3>'
                f'<span class="text-xs text-slate-400 ml-1">({len(sv)} identified)</span>'
                '</summary>'
                '<div class="space-y-3">'
            )
            for v in sv:
                pm.append(
                    f'<div class="rounded-lg border border-amber-100 bg-amber-50/50 p-4 border-l-4 border-l-amber-400">'
                    f'<p class="text-sm text-slate-700 leading-relaxed">{bold_lead(v)}</p>'
                    f'</div>'
                )
            pm.append('</div></details>')

        # --- Survival Principles (numbered, emerald-accented takeaway cards) ---
        sp = postmortem.get("survival_principles", [])
        if sp:
            pm.append(
                '<div class="mb-8">'
                '<div class="flex items-center gap-2 mb-4">'
                '<svg class="w-5 h-5 text-emerald-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">'
                '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" '
                'd="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>'
                '</svg>'
                '<h3 class="text-lg font-display font-semibold text-slate-800">Survival Principles</h3>'
                '</div>'
                '<div class="space-y-3">'
            )
            for i, p in enumerate(sp, 1):
                pm.append(
                    f'<div class="flex gap-4 rounded-lg bg-gradient-to-r from-emerald-50 to-white border border-emerald-100 p-4 items-start">'
                    f'<span class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-emerald-600 text-white font-bold text-sm">{i}</span>'
                    f'<p class="text-sm text-slate-700 leading-relaxed flex-1">{bold_lead(p)}</p>'
                    f'</div>'
                )
            pm.append('</div></div>')

        pm.append('</div>')  # close p-6 md:p-8

        # --- Graveyard Deep-Dive: parameter analysis cards with modals ---
        if graveyard_analyses:
            gy_param_ids = list(graveyard_analyses.keys())
            gy_cards = '<div class="grid gap-4 md:grid-cols-2">'
            for gpid in gy_param_ids:
                ga = graveyard_analyses[gpid]
                g_headline = html_escape.escape(ga.get("headline", "No headline."))
                g_rankings = ga.get("rankings") or []
                g_rank_lines = "".join(
                    f'<div class="text-sm text-slate-600 py-1 px-2 rounded {"bg-slate-50" if r.get("rank", 0) % 2 == 0 else ""}">'
                    f'{r.get("rank")}. {html_escape.escape(r.get("company", ""))}'
                    + (f' &mdash; <span class="text-slate-500">{html_escape.escape(r.get("label", ""))}</span>' if r.get("label") else "")
                    + "</div>"
                    for r in g_rankings[:6]
                )
                g_conf = ga.get("confidence", "unknown")
                g_dot = conf_dot.get(g_conf, "bg-slate-400")
                g_esc_id = html_escape.escape(gpid).replace("'", "\\'")
                g_rank_display = g_rank_lines if g_rank_lines else '<div class="text-sm text-slate-400">No rankings</div>'
                g_btn = f"<button onclick=\"openParamModal('{g_esc_id}')\" class=\"w-full rounded-lg bg-slate-700 px-4 py-2.5 text-sm font-medium text-white hover:bg-slate-800 transition-colors\">Read Full Analysis</button>"
                gy_cards += (
                    f'<div class="group rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition-all duration-200 hover:shadow-lg hover:border-slate-300 hover:-translate-y-0.5">'
                    f'<div class="flex items-start gap-3 mb-2">'
                    f'<span class="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full {g_dot}" title="{g_conf} confidence"></span>'
                    f'<h3 class="font-semibold text-slate-900 flex-1">{html_escape.escape(ga.get("parameter_name", gpid))}</h3>'
                    f'</div>'
                    f'<p class="text-sm text-slate-700 mb-4 leading-relaxed pl-5">{g_headline}</p>'
                    f'<div class="space-y-0.5 mb-4 pl-5">{g_rank_display}</div>'
                    f'{g_btn}'
                    f'</div>'
                )
            gy_cards += '</div>'

            pm.append(
                '<details class="border-t border-slate-200 print-expand">'
                '<summary class="p-6 font-semibold text-slate-800 cursor-pointer hover:bg-slate-50 transition-colors flex items-center gap-2">'
                '<svg class="w-5 h-5 text-slate-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">'
                '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" '
                'd="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>'
                '</svg>'
                f'<span>Graveyard Deep-Dive &mdash; {len(gy_param_ids)} Failure Parameters Analyzed</span>'
                '</summary>'
                f'<div class="px-6 pb-6 pt-2">{gy_cards}</div>'
                '</details>'
            )

        pm.append('</div></section>')
        postmortem_html = "\n".join(pm)

    total_time = metadata.get("total_elapsed_seconds", 0)
    time_str = f"{total_time:.0f}s" if total_time < 60 else f"{total_time / 60:.1f}m"
    num_companies = len(companies)
    num_params = len(parameters)
    conf_counts = {}
    for a in analyses.values():
        c = a.get("confidence", "unknown")
        conf_counts[c] = conf_counts.get(c, 0) + 1
    dominant_conf = max(conf_counts, key=conf_counts.get) if conf_counts else "medium"

    # Hero header variables
    stats_grid_cols = "md:grid-cols-5" if has_graveyard else "md:grid-cols-4"
    graveyard_stat_html = ""
    if has_graveyard:
        graveyard_stat_html = (
            f'<div class="rounded-lg bg-white/5 border border-white/10 p-4 backdrop-blur-sm">'
            f'<p class="text-slate-400 text-xs font-semibold uppercase tracking-wider mb-1">Graveyard</p>'
            f'<p class="text-2xl font-bold text-rose-400">{len(graveyard_cos)}</p>'
            f'</div>'
        )

    venture_hero_html = ""
    if venture_context:
        venture_hero_html = (
            f'<details class="mt-6 rounded-lg bg-amber-500/20 border border-amber-400/50 group/vc print-expand">'
            f'<summary class="px-4 py-3 cursor-pointer flex items-center gap-2 select-none">'
            f'<svg class="w-4 h-4 text-amber-300 shrink-0 transition-transform group-open/vc:rotate-90" fill="none" stroke="currentColor" viewBox="0 0 24 24">'
            f'<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>'
            f'<span class="text-xs font-semibold text-amber-200 uppercase tracking-wide">Venture Context</span>'
            f'<span class="text-amber-300/60 text-xs ml-1">— Research context and key questions driving this analysis</span>'
            f'</summary>'
            f'<div class="px-4 pb-4 pt-1 border-t border-amber-400/30">'
            f'<p class="text-amber-50 text-sm leading-relaxed">{html_escape.escape(venture_context)}</p>'
            f'</div>'
            f'</details>'
        )

    run_id = data.get("run_id", "")
    chat_widget_html = _build_chat_widget(run_id)

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
            <h1 class="font-display text-4xl md:text-5xl font-bold tracking-tight mb-2">{"AVIS " if is_avis else ""}Competitive Intelligence Report</h1>
            <p class="text-slate-300 text-base mb-6">{datetime.now().strftime("%B %d, %Y at %H:%M")}</p>
            <div class="flex flex-wrap gap-2 mb-6">
                {"".join(f'<span class="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-medium bg-white/10 border border-white/30 backdrop-blur-sm"><span class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold" style="background:{_avatar_color(i)};color:white">{html_escape.escape(c[:1].upper())}</span>{html_escape.escape(c)}</span>' for i, c in enumerate(companies))}
            </div>
            <!-- Key stats row -->
            <div class="grid grid-cols-2 {stats_grid_cols} gap-4 mb-2">
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
                {graveyard_stat_html}
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
            {f'<a href="#commercial-deep-dive" class="nav-link px-4 py-2 rounded-lg text-sm font-medium text-slate-600 hover:text-indigo-600 hover:bg-indigo-50 transition-colors">Commercial</a>' if commercial_summary_html else ""}
            {'<a href="#moat-grid" class="nav-link px-4 py-2 rounded-lg text-sm font-medium text-slate-600 hover:text-indigo-600 hover:bg-indigo-50 transition-colors">Moat Grid</a><a href="#threat-matrix" class="nav-link px-4 py-2 rounded-lg text-sm font-medium text-slate-600 hover:text-indigo-600 hover:bg-indigo-50 transition-colors">Threat Matrix</a><a href="#value-curve" class="nav-link px-4 py-2 rounded-lg text-sm font-medium text-slate-600 hover:text-indigo-600 hover:bg-indigo-50 transition-colors">Value Curve</a>' if is_avis and avis_frameworks_html else ""}
            {'<a href="#postmortem" class="nav-link px-4 py-2 rounded-lg text-sm font-medium text-slate-600 hover:text-indigo-600 hover:bg-indigo-50 transition-colors">Post-Mortem</a>' if postmortem_html else ""}
            <a href="#parameter-analysis" class="nav-link px-4 py-2 rounded-lg text-sm font-medium text-slate-600 hover:text-indigo-600 hover:bg-indigo-50 transition-colors">Parameter Analysis</a>
        </div>
    </nav>

<div class="max-w-6xl mx-auto px-6 py-10">

    <section id="executive-brief" class="mb-12 animate-fade-in">
        <div class="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
            <div class="p-6 md:p-8">
                <h2 class="text-2xl font-display font-bold text-slate-900 mb-4">Executive Brief</h2>

                <!-- TL;DR / BLUF -->
                <div class="rounded-lg bg-indigo-50 border border-indigo-200 p-5 mb-6">
                    <div class="flex items-start gap-3">
                        <span class="shrink-0 mt-0.5 flex h-7 w-7 items-center justify-center rounded-full bg-indigo-600 text-white">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
                        </span>
                        <div>
                            <p class="text-xs font-semibold text-indigo-600 uppercase tracking-wider mb-1">Bottom Line</p>
                            <p class="text-base font-medium text-slate-900 leading-relaxed">{bold_company_names(html_escape.escape(brief_tldr), companies)}</p>
                        </div>
                    </div>
                </div>

                <!-- Full brief: collapsible -->
                {f"""<details class="mb-6 group/brief print-expand">
                    <summary class="flex items-center gap-2 cursor-pointer select-none text-sm font-medium text-indigo-600 hover:text-indigo-700 transition-colors">
                        <svg class="w-4 h-4 shrink-0 transition-transform group-open/brief:rotate-90" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
                        Read full analysis
                    </summary>
                    <div class="mt-4 pl-4 border-l-4 border-slate-200">
                        <p class="text-sm text-slate-600 leading-relaxed whitespace-pre-line">{bold_company_names(html_escape.escape(brief), companies)}</p>
                    </div>
                </details>""" if brief_rest else f"""<div class="mb-6 pl-4 border-l-4 border-slate-200">
                    <p class="text-sm text-slate-600 leading-relaxed whitespace-pre-line">{bold_company_names(html_escape.escape(brief), companies)}</p>
                </div>"""}

                {f'<div class="mb-4"><h3 class="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-4">Key Themes</h3>{themes_html}</div>' if themes_html else ""}
            </div>
            {f'<details class="print-expand border-t border-slate-200" id="trends"><summary class="p-6 font-semibold text-slate-800 cursor-pointer hover:bg-slate-50 transition-colors">Trends</summary><div class="details-content px-6 pb-6 pt-2">{trends_html}</div></details>' if trends_html else ""}
            {f'<details class="print-expand border-t border-slate-200" id="white-space"><summary class="p-6 font-semibold text-slate-800 cursor-pointer hover:bg-slate-50 transition-colors">White Space &mdash; Strategic Opportunities</summary><div class="details-content px-6 pb-6 pt-2">{ws_opps_html}</div></details>' if ws_opps_html else ""}
            {f'<details class="print-expand border-t border-slate-200" id="white-space-matrix"><summary class="p-6 font-semibold text-slate-800 cursor-pointer hover:bg-slate-50 transition-colors">White Space &mdash; Gap Matrix</summary><div class="details-content px-6 pb-6 pt-2">{ws_matrix_html}</div></details>' if ws_matrix_html else ""}
            {f'<details class="print-expand border-t border-slate-200" id="next-steps"><summary class="p-6 font-semibold text-slate-800 cursor-pointer hover:bg-slate-50 transition-colors">Next Steps</summary><div class="details-content px-6 pb-6 pt-2">{next_steps_html}</div></details>' if next_steps_html else ""}
            {avis_frameworks_html}
        </div>
    </section>

    {commercial_summary_html}

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

<!-- Scroll-to-top button -->
<button id="scrollTopBtn" onclick="window.scrollTo({{top:0,behavior:'smooth'}})"
    class="no-print fixed bottom-6 right-6 z-50 hidden h-11 w-11 items-center justify-center rounded-full bg-slate-800 text-white shadow-lg hover:bg-indigo-600 transition-all duration-200 hover:scale-110"
    title="Back to top" aria-label="Scroll to top">
    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7"/></svg>
</button>

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
    var sectionIds = ["executive-brief", "trends", "white-space", "next-steps", "commercial-deep-dive", "postmortem", "parameter-analysis"];
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

/* Scroll-to-top button visibility */
(function() {{
    var btn = document.getElementById("scrollTopBtn");
    if (!btn) return;
    window.addEventListener("scroll", function() {{
        if (window.scrollY > 400) {{ btn.classList.remove("hidden"); btn.classList.add("flex"); }}
        else {{ btn.classList.add("hidden"); btn.classList.remove("flex"); }}
    }});
}})();

/* Print: expand all collapsible sections before printing */
window.addEventListener("beforeprint", function() {{
    document.querySelectorAll("details.print-expand").forEach(function(d) {{ d.setAttribute("open", ""); }});
}});
</script>
{chat_widget_html}
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
