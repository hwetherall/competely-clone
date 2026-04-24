"""
Configuration settings for CompetelyClone.

Loads environment variables from .env file and provides
centralized configuration for the entire application.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env and .env.local files.
# Look for them in the project root (parent of config/). Local values override
# shared defaults so developer-only keys can live outside the committed sample.
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / ".env.local", override=True)

# =============================================================================
# API Keys
# =============================================================================

SERPER_API_KEY: str = os.getenv("SERPER_API_KEY", "")
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
XAI_API_KEY: str = os.getenv("XAI_API_KEY", "")
ATLASCLOUD_API_KEY: str = os.getenv("ATLAS_CLOUD_API", "")
JINA_READER_API_KEY: str = os.getenv("JINA_READER_API_KEY", "")
EXA_API_KEY: str = os.getenv("EXA_API_KEY", "")
FIRECRAWL_API_KEY: str = os.getenv("FIRECRAWL_API_KEY", "")

# =============================================================================
# Serper API Configuration
# =============================================================================

SERPER_BASE_URL: str = "https://google.serper.dev/search"

# Exa semantic search configuration
EXA_BASE_URL: str = os.getenv("EXA_BASE_URL", "https://api.exa.ai")
EXA_SEARCH_TYPE: str = os.getenv("EXA_SEARCH_TYPE", "auto")
EXA_HIGHLIGHTS_MAX_CHARACTERS: int = int(os.getenv("EXA_HIGHLIGHTS_MAX_CHARACTERS", "4000"))
EXA_TEXT_MAX_CHARACTERS: int = int(os.getenv("EXA_TEXT_MAX_CHARACTERS", "20000"))
SEARCH_PROVIDER: str = os.getenv("SEARCH_PROVIDER", "serper")  # serper|exa|hybrid

# =============================================================================
# Atlas Cloud Configuration (deprecated research provider)
# =============================================================================

ATLASCLOUD_BASE_URL: str = "https://api.atlascloud.ai/v1"

# Primary research model (OpenRouter by default)
RESEARCH_MODEL: str = os.getenv("RESEARCH_MODEL", "anthropic/claude-sonnet-4.6")

_atlascloud_models_env = os.getenv("ATLAS_CLOUD_MODELS", "")
ATLASCLOUD_MODELS: list[str] = [
    model.strip()
    for model in _atlascloud_models_env.split(",")
    if model.strip()
]
if not ATLASCLOUD_MODELS and RESEARCH_MODEL.startswith("Alibaba-NLP/"):
    ATLASCLOUD_MODELS = [RESEARCH_MODEL]

# =============================================================================
# OpenRouter Configuration (Secondary provider for fallback/summarization)
# =============================================================================

OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
XAI_BASE_URL: str = os.getenv("XAI_BASE_URL", "https://api.x.ai/v1")

# Fast model for summarization (doesn't need agentic capabilities)
# Uses direct xAI when XAI_API_KEY is set; otherwise falls back to OpenRouter routing.
SUMMARIZE_MODEL: str = os.getenv("SUMMARIZE_MODEL", "x-ai/grok-4.1-fast")
SUMMARIZE_FALLBACK_MODEL: str = os.getenv("SUMMARIZE_FALLBACK_MODEL", RESEARCH_MODEL)

# Variable generator: fast model for strategic parameter generation.
VARIABLE_GENERATOR_MODEL: str = os.getenv(
    "VARIABLE_GENERATOR_MODEL", "x-ai/grok-4.1-fast"
)
VARIABLE_GENERATOR_FALLBACK_MODEL: str = os.getenv(
    "VARIABLE_GENERATOR_FALLBACK_MODEL", SUMMARIZE_FALLBACK_MODEL
)

# Legacy alias for backward compatibility (defaults to RESEARCH_MODEL)
TONGYI_MODEL: str = os.getenv("TONGYI_MODEL", RESEARCH_MODEL)

# =============================================================================
# Caching Configuration
# =============================================================================

CACHE_ENABLED: bool = os.getenv("CACHE_ENABLED", "true").lower() == "true"
CACHE_DIR: Path = PROJECT_ROOT / "data" / "cache"

# =============================================================================
# Rate Limiting Configuration
# =============================================================================

MAX_CONCURRENT_REQUESTS: int = int(os.getenv("MAX_CONCURRENT_REQUESTS", "5"))
REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "120"))

# =============================================================================
# Retry Configuration
# =============================================================================

MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
RETRY_DELAY: float = float(os.getenv("RETRY_DELAY", "1.0"))

# =============================================================================
# Research Agent Configuration
# =============================================================================

MAX_RESEARCH_ITERATIONS: int = int(os.getenv("MAX_RESEARCH_ITERATIONS", "3"))
MIN_RESEARCH_ITERATIONS: int = int(os.getenv("MIN_RESEARCH_ITERATIONS", "2"))

# =============================================================================
# Evidence-Grounded Research Configuration
# =============================================================================

# Page fetching
ENABLE_PAGE_FETCH: bool = os.getenv("ENABLE_PAGE_FETCH", "true").lower() == "true"
TOP_K_RESULTS_TO_FETCH: int = int(os.getenv("TOP_K_RESULTS_TO_FETCH", "3"))
MAX_PAGES_PER_CELL: int = int(os.getenv("MAX_PAGES_PER_CELL", "8"))
PAGE_FETCH_TIMEOUT: int = int(os.getenv("PAGE_FETCH_TIMEOUT", "15"))
MAX_CONCURRENT_PAGE_FETCHES: int = int(os.getenv("MAX_CONCURRENT_PAGE_FETCHES", "5"))

# Jina Reader Configuration
# Jina Reader extracts clean content from web pages
# Docs: https://jina.ai/reader/
JINA_READER_BASE_URL: str = os.getenv("JINA_READER_BASE_URL", "https://r.jina.ai/")
JINA_READER_TIMEOUT: int = int(os.getenv("JINA_READER_TIMEOUT", "30"))
JINA_READER_MAX_CONTENT_LENGTH: int = int(os.getenv("JINA_READER_MAX_CONTENT_LENGTH", "50000"))

# Firecrawl page extraction configuration
FIRECRAWL_BASE_URL: str = os.getenv("FIRECRAWL_BASE_URL", "https://api.firecrawl.dev/v2")
FIRECRAWL_TIMEOUT: int = int(os.getenv("FIRECRAWL_TIMEOUT", "60"))
FIRECRAWL_MAX_CONTENT_LENGTH: int = int(os.getenv("FIRECRAWL_MAX_CONTENT_LENGTH", "50000"))
PAGE_READER: str = os.getenv("PAGE_READER", "jina")  # jina|firecrawl

# Source scoring
MIN_SOURCE_SCORE: float = float(os.getenv("MIN_SOURCE_SCORE", "0.35"))

# Evidence passage selection
EVIDENCE_PASSAGES_PER_SOURCE: int = int(os.getenv("EVIDENCE_PASSAGES_PER_SOURCE", "4"))
MAX_EVIDENCE_CHARS: int = int(os.getenv("MAX_EVIDENCE_CHARS", "12000"))
ENABLE_LLM_PASSAGE_SELECTION: bool = os.getenv("ENABLE_LLM_PASSAGE_SELECTION", "false").lower() == "true"

# Numeric verification
ENABLE_NUMERIC_VERIFICATION: bool = os.getenv("ENABLE_NUMERIC_VERIFICATION", "true").lower() == "true"

# Default max characters for concise summaries (can be overridden per variable)
DEFAULT_MAX_CONCISE_CHARS: int = int(os.getenv("DEFAULT_MAX_CONCISE_CHARS", "240"))

# =============================================================================
# V2 Pipeline Configuration (Relational Competitive Intelligence Engine)
# =============================================================================

# Claude Sonnet 4.6 for synthesis and executive reasoning (OpenRouter)
SYNTHESIS_MODEL: str = os.getenv("SYNTHESIS_MODEL", "anthropic/claude-sonnet-4.6")
EXECUTIVE_MODEL: str = os.getenv("EXECUTIVE_MODEL", "anthropic/claude-sonnet-4.6")

# Synthesis phase: max iterations of draft -> evaluate -> re-gather -> re-normalize
MAX_SYNTHESIS_ITERATIONS: int = int(os.getenv("MAX_SYNTHESIS_ITERATIONS", "3"))
MAX_REGATHERS_PER_PARAMETER: int = int(os.getenv("MAX_REGATHERS_PER_PARAMETER", "2"))

# =============================================================================
# Chat with Results (interactive report chat, via OpenRouter)
# =============================================================================

CHAT_MODEL: str = os.getenv("CHAT_MODEL", "x-ai/grok-4.1-fast")

# =============================================================================
# Research Plan Wizard Models (all via OpenRouter)
# =============================================================================

# Fast tasks: clarification Qs, custom params, confidence preview
PLAN_FAST_MODEL: str = os.getenv("PLAN_FAST_MODEL", "deepseek/deepseek-v4-flash")
# Intelligence questions: fast chained questions to steer downstream generation
PLAN_INTELLIGENCE_MODEL: str = os.getenv(
    "PLAN_INTELLIGENCE_MODEL", "meta-llama/llama-4-maverick"
)
# Research tasks: company validation, company suggestions (live web)
PLAN_RESEARCH_MODEL: str = os.getenv("PLAN_RESEARCH_MODEL", "perplexity/sonar-pro-search")
# Fallback for research tasks when Perplexity fails (:online enables web search)
PLAN_RESEARCH_FALLBACK_MODEL: str = os.getenv(
    "PLAN_RESEARCH_FALLBACK_MODEL", "openai/gpt-5.2:online"
)
# Heavy reasoning: research goal, mission, key questions
PLAN_REASONING_MODEL: str = os.getenv("PLAN_REASONING_MODEL", "anthropic/claude-sonnet-4.6")

# Discovery stage configuration
DISCOVERY_MODEL: str = os.getenv("DISCOVERY_MODEL", "anthropic/claude-sonnet-4.6")
DISCOVERY_MAX_CANDIDATES: int = int(os.getenv("DISCOVERY_MAX_CANDIDATES", "20"))

# =============================================================================
# Validation
# =============================================================================

def validate_config(require_llm: bool = False) -> list[str]:
    """
    Validate that required configuration is present.
    
    Args:
        require_llm: If True, also validate LLM API keys (Atlas Cloud and/or OpenRouter)
    
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    search_provider = SEARCH_PROVIDER.lower()

    if search_provider not in ("serper", "exa", "hybrid"):
        errors.append("SEARCH_PROVIDER must be one of: serper, exa, hybrid.")

    if search_provider in ("serper", "hybrid") and not SERPER_API_KEY:
        errors.append("SERPER_API_KEY is not set. Please add it to your .env file.")

    if search_provider in ("exa", "hybrid") and not EXA_API_KEY:
        errors.append("EXA_API_KEY is not set. Please add it to your .env file.")
    
    if require_llm:
        research_uses_atlascloud = RESEARCH_MODEL in ATLASCLOUD_MODELS

        if research_uses_atlascloud and not ATLASCLOUD_API_KEY:
            errors.append("ATLAS_CLOUD_API is not set for the configured Atlas Cloud research model. Please add it to your .env file.")

        if not OPENROUTER_API_KEY:
            errors.append("OPENROUTER_API_KEY is not set. Please add it to your .env file.")
    
    return errors


def get_config_info() -> dict:
    """
    Get configuration information for debugging.
    
    Returns:
        Dict with non-sensitive configuration info
    """
    return {
        "research_model": RESEARCH_MODEL,
        "summarize_model": SUMMARIZE_MODEL,
        "atlascloud_base_url": ATLASCLOUD_BASE_URL,
        "atlascloud_models": ATLASCLOUD_MODELS,
        "atlascloud_api_key_set": bool(ATLASCLOUD_API_KEY),
        "atlascloud_api_key_prefix": ATLASCLOUD_API_KEY[:10] + "..." if ATLASCLOUD_API_KEY else None,
        "openrouter_base_url": OPENROUTER_BASE_URL,
        "openrouter_api_key_set": bool(OPENROUTER_API_KEY),
        "openrouter_api_key_prefix": OPENROUTER_API_KEY[:10] + "..." if OPENROUTER_API_KEY else None,
        "xai_base_url": XAI_BASE_URL,
        "xai_api_key_set": bool(XAI_API_KEY),
        "serper_api_key_set": bool(SERPER_API_KEY),
        "exa_api_key_set": bool(EXA_API_KEY),
        "exa_search_type": EXA_SEARCH_TYPE,
        "search_provider": SEARCH_PROVIDER,
        "jina_reader_api_key_set": bool(JINA_READER_API_KEY),
        "jina_reader_base_url": JINA_READER_BASE_URL,
        "firecrawl_api_key_set": bool(FIRECRAWL_API_KEY),
        "firecrawl_base_url": FIRECRAWL_BASE_URL,
        "page_reader": PAGE_READER,
        "enable_page_fetch": ENABLE_PAGE_FETCH,
        "cache_enabled": CACHE_ENABLED,
        "llm_timeout": LLM_TIMEOUT,
    }


def ensure_directories() -> None:
    """Create necessary directories if they don't exist."""
    if CACHE_ENABLED:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)


# Auto-create directories on import
ensure_directories()
