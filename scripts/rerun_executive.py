"""
Re-run ONLY Phase 4 (Executive Brief) on an existing V2 run JSON.
Adds the new executive brief sections (trends, white space, next steps)
without re-running the full pipeline.

Usage:
    python scripts/rerun_executive.py data/results/v2_run_20260211_212502.json --venture-context "Low cost airline..."
"""

import sys
import json
import asyncio
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.executive_agent import ExecutiveAgent
from agents.v2_schemas import ComparativeReport


async def rerun_executive(json_path: str, venture_context: str = ""):
    """Load existing run, re-run executive brief, save updated JSON + HTML."""
    target = Path(json_path)
    if not target.is_absolute():
        target = project_root / target

    if not target.exists():
        print(f"ERROR: File not found: {target}")
        sys.exit(1)

    print(f"Loading: {target}")
    with open(target, "r", encoding="utf-8") as f:
        data = json.load(f)

    companies = data.get("companies", [])
    parameters = data.get("parameters", [])
    analyses = data.get("analyses", {})

    # Build ComparativeReport objects from existing analyses
    reports = []
    for param_id in parameters:
        a = analyses.get(param_id)
        if a:
            reports.append(ComparativeReport.from_dict(a))

    companies_list = ", ".join(companies)
    print(f"Companies: {companies_list}")
    print(f"Parameters: {len(reports)}")
    if venture_context:
        print(f"Venture context: {venture_context[:100]}...")
    else:
        print("Venture context: (none)")

    # Run executive agent
    print("\nRunning executive brief synthesis...")
    agent = ExecutiveAgent()
    executive = await agent.synthesize_brief(
        companies_list=companies_list,
        reports=reports,
        venture_context=venture_context,
    )

    # Update data
    data["executive"] = executive.to_dict()
    print(f"\nExecutive brief generated:")
    print(f"  - Brief: {len(executive.brief)} chars")
    print(f"  - Key themes: {len(executive.key_themes)}")
    print(f"  - Trends: {len(executive.trends)}")
    print(f"  - White space opportunities: {len(executive.white_space_opportunities)}")
    print(f"  - White space matrix categories: {len(executive.white_space_matrix)}")
    print(f"  - Next steps buckets: {len(executive.next_steps)}")

    # Save updated JSON
    with open(target, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\nJSON updated: {target}")

    # Re-generate HTML
    from utils.generate_v2_report import generate_v2_html
    html_path = target.with_suffix(".html")
    generate_v2_html(data, html_path)
    print(f"HTML updated: {html_path}")
    print("\nDone!")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Re-run executive brief on existing V2 run")
    parser.add_argument("json_path", help="Path to V2 run JSON file")
    parser.add_argument("--venture-context", default="", help="Optional venture context")
    args = parser.parse_args()
    asyncio.run(rerun_executive(args.json_path, args.venture_context))
