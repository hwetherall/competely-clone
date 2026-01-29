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
    """Generate HTML table from comparison data."""
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
            overflow-x: auto;
            max-width: 100%;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            border-radius: 0.5rem;
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
            z-index: 20;
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
                            <div class="text-xs text-gray-400 font-normal mt-1">{var_id}</div>
                        </td>
        """
        
        for company in companies:
            cell_data = grid.get(company, {}).get(var_id, {})
            concise = cell_data.get("concise", "No data available.")
            comprehensive = cell_data.get("comprehensive", "").replace("\n", "<br>")
            # Simple markdown to html conversion for comprehensive
            import markdown
            comprehensive_html = markdown.markdown(cell_data.get("comprehensive", ""))
            
            sources = cell_data.get("sources", [])
            confidence = cell_data.get("confidence", "unknown")
            
            # Confidence badge color
            conf_color = {
                "high": "bg-green-100 text-green-800",
                "medium": "bg-yellow-100 text-yellow-800",
                "low": "bg-red-100 text-red-800",
                "none": "bg-gray-100 text-gray-800"
            }.get(confidence, "bg-gray-100 text-gray-800")

            html += f"""
                        <td class="p-4 align-top">
                            <div class="mb-3 text-sm leading-relaxed text-gray-800">
                                {concise}
                            </div>
                            
                            <div class="flex items-center gap-2 mb-3">
                                <span class="text-xs px-2 py-0.5 rounded {conf_color} font-medium capitalize">
                                    {confidence} confidence
                                </span>
                            </div>

                            <details class="group">
                                <summary class="cursor-pointer text-blue-600 hover:text-blue-800 text-sm font-medium select-none flex items-center gap-1">
                                    <span>View Details</span>
                                    <svg class="w-4 h-4 transition-transform group-open:rotate-180" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
                                </summary>
                                <div class="mt-3 pt-3 border-t border-gray-100">
                                    <div class="prose prose-sm max-w-none text-gray-600 mb-4">
                                        {comprehensive_html}
                                    </div>
                                    
                                    {f'''
                                    <div class="bg-gray-50 p-3 rounded text-xs">
                                        <h5 class="font-semibold text-gray-700 mb-2">Sources:</h5>
                                        <ul class="space-y-1 text-gray-500 list-none pl-0">
                                            {''.join([f'<li><a href="{s["url"]}" target="_blank" class="text-blue-500 hover:underline truncate block" title="{s["title"]}">{s["title"]}</a></li>' for s in sources[:5]])}
                                        </ul>
                                    </div>
                                    ''' if sources else ''}
                                </div>
                            </details>
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
