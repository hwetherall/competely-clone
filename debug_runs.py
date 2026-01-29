import sys
import json
from pathlib import Path

# Setup path
project_root = Path.cwd()
sys.path.insert(0, str(project_root))

RESULTS_DIR = project_root / "data" / "results"

print(f"Checking {RESULTS_DIR}")

runs = []

# Check completed
print("\nScanning completed runs:")
for filepath in RESULTS_DIR.glob("comparison_*.json"):
    if "_refined" in filepath.name:
        continue
    print(f"Found: {filepath.name}")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            print(f"  - Loaded valid JSON")
    except Exception as e:
        print(f"  - Error: {e}")

# Check progress
print("\nScanning progress runs:")
for filepath in RESULTS_DIR.glob("progress_*.json"):
    print(f"Found: {filepath.name}")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            print(f"  - Loaded valid JSON")
            print(f"  - Status: {data.get('status')}")
    except Exception as e:
        print(f"  - Error: {e}")
