import asyncio
import json
import sys
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.research_agent import ResearchAgent
from config.variables import get_variable
from config import settings
from utils.generate_table import generate_html, generate_csv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def regenerate_summaries(file_path):
    """Regenerate concise summaries for an existing result file."""
    path = Path(file_path)
    if not path.exists():
        print(f"File not found: {path}")
        return

    print(f"Loading results from: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    agent = ResearchAgent()
    companies = data.get("companies", [])
    grid = data.get("grid", {})
    
    total_cells = 0
    updated_cells = 0
    
    print("\nRegenerating summaries...")
    
    for company in companies:
        if company not in grid:
            continue
            
        for variable_id, cell_data in grid[company].items():
            total_cells += 1
            comprehensive = cell_data.get("comprehensive", "")
            
            if not comprehensive:
                continue
                
            # Get updated max chars from variable definition
            try:
                variable = get_variable(variable_id)
                max_chars = variable.max_concise_chars
            except ValueError:
                max_chars = settings.DEFAULT_MAX_CONCISE_CHARS
            
            print(f"  [{company}] {variable_id} (max {max_chars} chars)...", end="\r")
            
            # Generate new summary
            new_concise = await agent._summarize(
                company=company,
                variable_name=cell_data.get("variable_name", variable_id),
                comprehensive=comprehensive,
                max_chars=max_chars
            )
            
            # Update cell
            cell_data["concise"] = new_concise
            updated_cells += 1
            
        # Save progress after each company
        print(f"\nSaving progress after {company}...")
        new_filename = path.stem + "_refined" + path.suffix
        new_path = path.parent / new_filename
        
        with open(new_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            
    print(f"\n\nUpdated {updated_cells}/{total_cells} cells.")
    
    # Save new JSON (final)
    new_filename = path.stem + "_refined" + path.suffix
    new_path = path.parent / new_filename
    
    # Update timestamp
    data["timestamp"] = datetime.utcnow().isoformat()
    
    with open(new_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    
    print(f"Saved refined results to: {new_path}")
    
    # Generate outputs
    html_path = new_path.with_suffix(".html")
    csv_path = new_path.with_suffix(".csv")
    
    generate_html(data, html_path)
    generate_csv(data, csv_path)
    
    print(f"Generated HTML: {html_path}")
    print(f"Generated CSV: {csv_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Find latest if not provided
        results_dir = Path("data/results")
        files = list(results_dir.glob("comparison_*.json"))
        if not files:
            print("No comparison files found.")
            sys.exit(1)
        latest_file = max(files, key=lambda p: p.stat().st_mtime)
        file_path = latest_file
    else:
        file_path = sys.argv[1]
        
    asyncio.run(regenerate_summaries(file_path))
