# CompetelyClone

A competitive analysis tool that uses parallel AI research agents to generate comprehensive competitive analysis tables with evidence-grounded synthesis.

## Overview

CompetelyClone automates competitive research by deploying parallel research agents to gather, analyze, and synthesize competitive intelligence. The tool produces structured results with both concise summaries and comprehensive analyses backed by cited evidence.

## Features

- **Evidence-Grounded Research**: Fetches actual page content, extracts relevant passages, and requires citations for all claims
- **Source Quality Scoring**: Prioritizes official company sites, regulatory filings, and tier-1 news over forums and SEO content
- **Structured Synthesis**: Outputs claims with source citations ([S1], [S2]) and identifies information gaps
- **Numeric Verification**: Detects unsupported numbers and removes or qualifies unverified statistics
- **Parallel Research**: Concurrent research tasks with smart rate limiting
- **Smart Caching**: MD5-based caching for searches and page fetches
- **Concise Summaries**: Enforced character limits (default 240 chars) for table-ready output

## Setup

1. Clone the repository

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env` and add your API keys:
   ```bash
   cp .env.example .env
   ```

5. Edit `.env` with your actual API keys:
   - `SERPER_API_KEY`: Get from https://serper.dev/
   - `ATLAS_CLOUD_API`: Get from https://atlascloud.ai/
   - `OPENROUTER_API_KEY`: Get from https://openrouter.ai/

## Usage

### Run Analysis for Specific Companies

```bash
python main.py --companies Stripe PayPal
```

### Fast Mode (Single Iteration, Skip Evaluation)

```bash
python main.py --companies Stripe --fast
```

### Full 5-Company Analysis

```bash
python main.py
```

### Run Tests

```bash
# Run all pytest tests
pytest -q

# Run specific test modules
pytest tests/test_source_scoring.py -v
pytest tests/test_verification.py -v
```

## Project Structure

```
competely-clone/
├── agents/
│   ├── research_agent.py    # Main research orchestration
│   ├── search_client.py     # Web search (Serper API) with source scoring
│   ├── llm_client.py        # LLM client (Atlas Cloud + OpenRouter)
│   ├── page_reader.py       # Page fetching and HTML extraction
│   ├── passage_selector.py  # Passage extraction for evidence
│   ├── source_scoring.py    # Source quality scoring
│   ├── verification.py      # Numeric claim verification
│   ├── schemas.py           # Data structures for evidence
│   └── prompts.py           # LLM prompts with citation formats
├── config/
│   ├── settings.py          # Configuration and environment variables
│   └── variables.py         # 20 research variable definitions
├── tests/
│   ├── test_source_scoring.py
│   ├── test_page_reader.py
│   ├── test_passage_selector.py
│   ├── test_verification.py
│   └── ...
├── data/
│   ├── cache/               # Cached search and page results
│   └── results/             # Analysis output JSON files
├── main.py                  # CLI entry point
├── .env                     # API keys (not in git)
├── .env.example             # Template for .env
├── requirements.txt         # Python dependencies
└── README.md
```

## Configuration

Key settings can be configured via environment variables or `.env`:

| Setting | Default | Description |
|---------|---------|-------------|
| `ENABLE_PAGE_FETCH` | `true` | Fetch full page content for evidence |
| `TOP_K_RESULTS_TO_FETCH` | `3` | Pages to fetch per search query |
| `MAX_PAGES_PER_CELL` | `8` | Max pages per research cell |
| `MIN_SOURCE_SCORE` | `0.35` | Minimum source quality threshold |
| `EVIDENCE_PASSAGES_PER_SOURCE` | `4` | Passages to extract per page |
| `MAX_EVIDENCE_CHARS` | `12000` | Max evidence chars per cell |
| `ENABLE_NUMERIC_VERIFICATION` | `true` | Verify numbers against evidence |
| `DEFAULT_MAX_CONCISE_CHARS` | `240` | Max chars for concise summaries |

## Output Format

Results are saved to `data/results/comparison_<timestamp>.json`:

```json
{
  "grid": {
    "Stripe": {
      "pricing_strategy": {
        "concise": "Stripe charges 2.9% + $0.30 per transaction [S1]...",
        "comprehensive": "Full analysis with [S1], [S2] citations...",
        "claims": [
          {"text": "2.9% + $0.30 per transaction", "source_ids": ["S1"], "confidence": "high"}
        ],
        "gaps": ["Enterprise pricing not disclosed"],
        "sources": [...],
        "confidence": "high",
        "metadata": {
          "pages_fetched": 6,
          "avg_source_score": 0.82,
          "verification_applied": true
        }
      }
    }
  }
}
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATOR                            │
│              (Manages parallel research tasks)                  │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
    ┌──────────┐        ┌──────────┐        ┌──────────┐
    │ Research │        │ Research │        │ Research │  ...
    │  Agent   │        │  Agent   │        │  Agent   │
    └────┬─────┘        └────┬─────┘        └────┬─────┘
         │                   │                   │
    ┌────┴─────┐        ┌────┴─────┐        ┌────┴─────┐
    │  Search  │        │  Search  │        │  Search  │
    │  + Fetch │        │  + Fetch │        │  + Fetch │
    └────┬─────┘        └────┬─────┘        └────┬─────┘
         │                   │                   │
    ┌────┴─────┐        ┌────┴─────┐        ┌────┴─────┐
    │ Evidence │        │ Evidence │        │ Evidence │
    │   Pack   │        │   Pack   │        │   Pack   │
    └────┬─────┘        └────┬─────┘        └────┬─────┘
         │                   │                   │
    ┌────┴─────┐        ┌────┴─────┐        ┌────┴─────┐
    │Synthesis │        │Synthesis │        │Synthesis │
    │+ Verify  │        │+ Verify  │        │+ Verify  │
    └──────────┘        └──────────┘        └──────────┘
```

## Deployment

To deploy the **frontend** (Next.js) to **Vercel** and the **backend** (FastAPI) to **Railway**, see **[DEPLOYMENT.md](DEPLOYMENT.md)** for step-by-step instructions, environment variables, and CORS setup.

## License

MIT
