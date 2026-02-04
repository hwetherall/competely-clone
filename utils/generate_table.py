import json
import sys
from pathlib import Path
from datetime import datetime

def load_latest_result(file_path=None):
    """Load the most recent comparison JSON file or a specific file."""
    if file_path:
        target_file = Path(file_path)
        if not target_file.exists():
            print(f"Error: File not found: {target_file}")
            sys.exit(1)
        print(f"Loading results from: {target_file}")
        with open(target_file, "r", encoding="utf-8") as f:
            return json.load(f), target_file

    results_dir = Path("data/results")
    files = list(results_dir.glob("comparison_*.json"))
    if not files:
        print("No comparison results found.")
        sys.exit(1)
    
    # Sort by modification time, newest first
    latest_file = max(files, key=lambda p: p.stat().st_mtime)
    print(f"Loading results from: {latest_file}")
    
    with open(latest_file, "r", encoding="utf-8") as f:
        return json.load(f), latest_file

def generate_html(data, output_path):
    """Generate HTML table from comparison data with modal popups."""
    import markdown
    import html as html_escape
    
    companies = data.get("companies", [])
    variables = data.get("variables", [])
    grid = data.get("grid", {})
    
    # Get variable display names (from the first company's data)
    var_names = {}
    first_company = companies[0]
    if first_company in grid:
        for var_id in variables:
            if var_id in grid[first_company]:
                var_names[var_id] = grid[first_company][var_id].get("variable_name", var_id)
            else:
                var_names[var_id] = var_id

    # Build modal data for JavaScript
    modal_data = {}
    for company in companies:
        modal_data[company] = {}
        for var_id in variables:
            cell_data = grid.get(company, {}).get(var_id, {})
            comprehensive_html = markdown.markdown(cell_data.get("comprehensive", ""))
            sources = cell_data.get("sources", [])
            gaps = cell_data.get("gaps", [])
            metadata = cell_data.get("metadata", {})
            confidence = cell_data.get("confidence", "unknown")
            
            modal_data[company][var_id] = {
                "variable_name": var_names.get(var_id, var_id),
                "comprehensive": comprehensive_html,
                "sources": sources,
                "gaps": gaps,
                "metadata": metadata,
                "confidence": confidence
            }

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Competitive Analysis: {", ".join(companies)}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .prose h3 {{ font-size: 1.25rem; font-weight: 600; margin-top: 1rem; margin-bottom: 0.5rem; }}
        .prose h4 {{ font-size: 1.1rem; font-weight: 600; margin-top: 0.75rem; margin-bottom: 0.5rem; }}
        .prose p {{ margin-bottom: 0.75rem; }}
        .prose ul {{ list-style-type: disc; padding-left: 1.5rem; margin-bottom: 0.75rem; }}
        .prose li {{ margin-bottom: 0.25rem; }}
        .prose strong {{ font-weight: 600; }}
        
        /* Custom scrollbar for table */
        .table-container {{
            overflow: auto;
            max-width: 100%;
            max-height: calc(100vh - 200px);
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            border-radius: 0.5rem;
        }}
        
        /* Sticky header row */
        thead tr {{
            position: sticky;
            top: 0;
            z-index: 30;
            background-color: #f3f4f6;
        }}
        
        /* Sticky first column */
        th:first-child, td:first-child {{
            position: sticky;
            left: 0;
            background-color: white;
            z-index: 10;
            border-right: 2px solid #e5e7eb;
        }}
        th:first-child {{
            z-index: 40;
            background-color: #f3f4f6;
        }}
        
        /* Modal styles */
        .modal-overlay {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: rgba(0, 0, 0, 0.5);
            z-index: 100;
            justify-content: center;
            align-items: center;
            padding: 1rem;
        }}
        .modal-overlay.active {{
            display: flex;
        }}
        .modal-content {{
            background: white;
            border-radius: 0.75rem;
            max-width: 800px;
            width: 100%;
            max-height: 90vh;
            overflow-y: auto;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
        }}
        
        /* Source card styles */
        .source-card {{
            border-left: 4px solid #3b82f6;
            padding: 0.75rem;
            margin-bottom: 0.75rem;
            background-color: #f9fafb;
            border-radius: 0 0.375rem 0.375rem 0;
        }}
        .source-card.official {{
            border-left-color: #10b981;
        }}
        
        /* Collapsible section styles */
        .section-toggle {{
            cursor: pointer;
            user-select: none;
        }}
        .section-toggle:hover {{
            background-color: #f3f4f6;
        }}
    </style>
</head>
<body class="bg-gray-50 text-gray-900 font-sans p-4 md:p-8">

    <div class="max-w-[1800px] mx-auto">
        <header class="mb-8">
            <h1 class="text-3xl font-bold text-gray-900 mb-2">Competitive Analysis Report</h1>
            <p class="text-gray-600">Generated on {datetime.now().strftime('%B %d, %Y at %H:%M')}</p>
            <div class="mt-4 flex flex-wrap gap-2">
                {'''
                '''.join([f'<span class="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">{company}</span>' for company in companies])}
            </div>
        </header>

        <div class="table-container bg-white border border-gray-200">
            <table class="min-w-full border-collapse">
                <thead>
                    <tr class="bg-gray-100 border-b border-gray-200">
                        <th class="p-4 text-left font-bold text-gray-700 w-64 min-w-[200px]">Variable</th>
                        {'''
                        '''.join([f'<th class="p-4 text-left font-bold text-gray-700 min-w-[300px]">{company}</th>' for company in companies])}
                    </tr>
                </thead>
                <tbody class="divide-y divide-gray-200">
    """

    for var_id in variables:
        var_name = var_names.get(var_id, var_id)
        html += f"""
                    <tr class="hover:bg-gray-50 transition-colors">
                        <td class="p-4 font-semibold text-gray-800 bg-gray-50 align-top">
                            {var_name}
                        </td>
        """
        
        for company in companies:
            cell_data = grid.get(company, {}).get(var_id, {})
            concise = cell_data.get("concise", "No data available.")
            confidence = cell_data.get("confidence", "unknown")
            
            # Confidence badge color
            conf_color = {
                "high": "bg-green-100 text-green-800",
                "medium": "bg-yellow-100 text-yellow-800",
                "low": "bg-red-100 text-red-800",
                "none": "bg-gray-100 text-gray-800"
            }.get(confidence, "bg-gray-100 text-gray-800")
            
            # Escape company and var_id for JavaScript
            escaped_company = html_escape.escape(company).replace("'", "\\'")
            escaped_var_id = html_escape.escape(var_id).replace("'", "\\'")

            html += f"""
                        <td class="p-4 align-top">
                            <div class="mb-3 text-sm leading-relaxed text-gray-800">
                                {concise}
                            </div>

                            <button 
                                onclick="openModal('{escaped_company}', '{escaped_var_id}')"
                                class="cursor-pointer text-blue-600 hover:text-blue-800 text-sm font-medium flex items-center gap-1 bg-transparent border-none p-0"
                            >
                                <span>View Details</span>
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
                                </svg>
                            </button>
                        </td>
            """
        html += "</tr>"

    html += """
                </tbody>
            </table>
        </div>
        
        <footer class="mt-8 text-center text-gray-500 text-sm">
            <p>Generated by CompetelyClone AI Agent</p>
        </footer>
    </div>

    <!-- Modal Overlay -->
    <div id="modalOverlay" class="modal-overlay" onclick="closeModalOnOverlay(event)">
        <div class="modal-content" onclick="event.stopPropagation()">
            <div class="sticky top-0 bg-white border-b border-gray-200 p-4 flex justify-between items-center rounded-t-xl">
                <div>
                    <h2 id="modalTitle" class="text-xl font-bold text-gray-900"></h2>
                    <p id="modalSubtitle" class="text-sm text-gray-500"></p>
                </div>
                <button onclick="closeModal()" class="text-gray-400 hover:text-gray-600 p-2 rounded-full hover:bg-gray-100">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
            
            <div class="p-4 space-y-4">
                <!-- Confidence Badge -->
                <div id="modalConfidence" class="flex items-center gap-2"></div>
                
                <!-- Full Information Section (expanded by default) -->
                <details open class="border border-gray-200 rounded-lg overflow-hidden">
                    <summary class="section-toggle p-4 font-semibold text-gray-800 flex items-center justify-between">
                        <span>Full Information</span>
                        <svg class="w-5 h-5 text-gray-500 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                        </svg>
                    </summary>
                    <div id="modalComprehensive" class="p-4 pt-0 prose prose-sm max-w-none text-gray-600 border-t border-gray-100"></div>
                </details>
                
                <!-- Sources Section (collapsed by default) -->
                <details class="border border-gray-200 rounded-lg overflow-hidden">
                    <summary class="section-toggle p-4 font-semibold text-gray-800 flex items-center justify-between">
                        <span>Sources</span>
                        <svg class="w-5 h-5 text-gray-500 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                        </svg>
                    </summary>
                    <div id="modalSources" class="p-4 pt-0 border-t border-gray-100"></div>
                </details>
                
                <!-- Gaps Identified Section (collapsed by default) -->
                <details class="border border-gray-200 rounded-lg overflow-hidden">
                    <summary class="section-toggle p-4 font-semibold text-gray-800 flex items-center justify-between">
                        <span>Gaps Identified</span>
                        <svg class="w-5 h-5 text-gray-500 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                        </svg>
                    </summary>
                    <div id="modalGaps" class="p-4 pt-0 border-t border-gray-100"></div>
                </details>
                
                <!-- Metadata Section (collapsed by default) -->
                <details class="border border-gray-200 rounded-lg overflow-hidden">
                    <summary class="section-toggle p-4 font-semibold text-gray-800 flex items-center justify-between">
                        <span>Metadata</span>
                        <svg class="w-5 h-5 text-gray-500 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                        </svg>
                    </summary>
                    <div id="modalMetadata" class="p-4 pt-0 border-t border-gray-100"></div>
                </details>
            </div>
        </div>
    </div>

    <script>
    // Modal data embedded from Python
    const modalData = """ + json.dumps(modal_data, ensure_ascii=False) + """;
    
    function openModal(company, varId) {
        const data = modalData[company]?.[varId];
        if (!data) return;
        
        // Set title
        document.getElementById('modalTitle').textContent = data.variable_name;
        document.getElementById('modalSubtitle').textContent = company;
        
        // Set confidence badge
        const confColors = {
            'high': 'bg-green-100 text-green-800',
            'medium': 'bg-yellow-100 text-yellow-800',
            'low': 'bg-red-100 text-red-800',
            'none': 'bg-gray-100 text-gray-800'
        };
        const confColor = confColors[data.confidence] || 'bg-gray-100 text-gray-800';
        document.getElementById('modalConfidence').innerHTML = `
            <span class="text-xs px-2 py-0.5 rounded ${confColor} font-medium capitalize">
                ${data.confidence} confidence
            </span>
        `;
        
        // Set comprehensive content
        document.getElementById('modalComprehensive').innerHTML = data.comprehensive || '<p class="text-gray-400">No detailed information available.</p>';
        
        // Set sources with numbering (S1, S2, etc.)
        const sourcesHtml = data.sources && data.sources.length > 0 
            ? data.sources.map((s, idx) => `
                <div class="source-card ${s.is_official ? 'official' : ''}">
                    <div class="flex items-start gap-2">
                        <span class="flex-shrink-0 bg-blue-100 text-blue-800 text-xs font-bold px-2 py-0.5 rounded">S${idx + 1}</span>
                        <div class="flex-1">
                            <a href="${escapeHtml(s.url)}" target="_blank" rel="noopener noreferrer" 
                               class="font-medium text-blue-600 hover:text-blue-800 hover:underline block mb-1">
                                ${escapeHtml(s.title)}
                            </a>
                            <div class="flex items-center gap-2 text-xs mb-1">
                                <span class="px-1.5 py-0.5 rounded ${s.is_official ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}">
                                    ${s.is_official ? 'Official' : 'Third-party'}
                                </span>
                                <span class="text-gray-400">${escapeHtml(s.domain)}</span>
                            </div>
                            ${s.snippet ? `<p class="text-xs text-gray-500 mt-1">${escapeHtml(s.snippet)}</p>` : ''}
                        </div>
                    </div>
                </div>
            `).join('')
            : '<p class="text-gray-400 text-sm">No sources available.</p>';
        document.getElementById('modalSources').innerHTML = sourcesHtml;
        
        // Set gaps (Gaps Identified)
        const gapsHtml = data.gaps && data.gaps.length > 0
            ? `<ul class="space-y-2">
                ${data.gaps.map(gap => `
                    <li class="flex items-start gap-2 text-sm text-gray-600">
                        <svg class="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
                        </svg>
                        <span>${escapeHtml(gap)}</span>
                    </li>
                `).join('')}
               </ul>`
            : '<p class="text-gray-400 text-sm">No confidence gaps identified.</p>';
        document.getElementById('modalGaps').innerHTML = gapsHtml;
        
        // Set metadata (2 rows of 3 items)
        const meta = data.metadata || {};
        const metadataHtml = Object.keys(meta).length > 0
            ? `<div class="grid grid-cols-3 gap-3 text-sm">
                ${meta.iterations !== undefined ? `<div><span class="text-gray-500">Iterations:</span> <span class="font-medium">${meta.iterations}</span></div>` : ''}
                ${meta.searches !== undefined ? `<div><span class="text-gray-500">Searches:</span> <span class="font-medium">${meta.searches}</span></div>` : ''}
                ${meta.pages_fetched !== undefined ? `<div><span class="text-gray-500">Pages Fetched:</span> <span class="font-medium">${meta.pages_fetched}</span></div>` : ''}
                ${meta.evidence_sources_used !== undefined ? `<div><span class="text-gray-500">Evidence Sources:</span> <span class="font-medium">${meta.evidence_sources_used}</span></div>` : ''}
                ${meta.verification_applied !== undefined ? `<div><span class="text-gray-500">Verified:</span> <span class="font-medium">${meta.verification_applied ? 'Yes' : 'No'}</span></div>` : ''}
                ${meta.model_used ? `<div><span class="text-gray-500">Model:</span> <span class="font-medium text-xs">${escapeHtml(meta.model_used)}</span></div>` : ''}
               </div>`
            : '<p class="text-gray-400 text-sm">No metadata available.</p>';
        document.getElementById('modalMetadata').innerHTML = metadataHtml;
        
        // Show modal
        document.getElementById('modalOverlay').classList.add('active');
        document.body.style.overflow = 'hidden';
    }
    
    function closeModal() {
        document.getElementById('modalOverlay').classList.remove('active');
        document.body.style.overflow = '';
    }
    
    function closeModalOnOverlay(event) {
        if (event.target.id === 'modalOverlay') {
            closeModal();
        }
    }
    
    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // Close modal on Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeModal();
        }
    });
    </script>
</body>
</html>
    """
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML table generated: {output_path}")

import csv

def generate_csv(data, output_path):
    """Generate CSV table from comparison data."""
    companies = data.get("companies", [])
    variables = data.get("variables", [])
    grid = data.get("grid", {})
    
    # Get variable display names
    var_names = {}
    first_company = companies[0]
    if first_company in grid:
        for var_id in variables:
            if var_id in grid[first_company]:
                var_names[var_id] = grid[first_company][var_id].get("variable_name", var_id)
            else:
                var_names[var_id] = var_id

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow(["Variable"] + companies)
        
        # Rows
        for var_id in variables:
            var_name = var_names.get(var_id, var_id)
            row = [var_name]
            for company in companies:
                cell_data = grid.get(company, {}).get(var_id, {})
                concise = cell_data.get("concise", "No data available.")
                row.append(concise)
            writer.writerow(row)
    
    print(f"CSV table generated: {output_path}")

if __name__ == "__main__":
    # Ensure markdown is installed
    try:
        import markdown
    except ImportError:
        print("Installing markdown package...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "markdown"])
        import markdown

    # Check for command line argument
    file_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    data, json_path = load_latest_result(file_path)
    
    # Generate HTML
    output_html = json_path.with_suffix(".html")
    generate_html(data, output_html)
    
    # Generate CSV
    output_csv = json_path.with_suffix(".csv")
    generate_csv(data, output_csv)
