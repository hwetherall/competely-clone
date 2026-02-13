"""
Configuration settings for CompetelyClone.

Loads environment variables from .env file and provides
centralized configuration for the entire application.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
# Look for .env in the project root (parent of config/)
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# =============================================================================
# API Keys
# =============================================================================

SERPER_API_KEY: str = os.getenv("SERPER_API_KEY", "")
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
ATLASCLOUD_API_KEY: str = os.getenv("ATLAS_CLOUD_API", "")
JINA_READER_API_KEY: str = os.getenv("JINA_READER_API_KEY", "")

# =============================================================================
# Serper API Configuration
# =============================================================================

SERPER_BASE_URL: str = "https://google.serper.dev/search"

# =============================================================================
# Atlas Cloud Configuration (Primary provider for Tongyi DeepResearch)
# =============================================================================

ATLASCLOUD_BASE_URL: str = "https://api.atlascloud.ai/v1"

# Primary research model - Tongyi DeepResearch is specialized for agentic research
# See: https://tongyi-agent.github.io/blog/introducing-tongyi-deep-research/
# Using Atlas Cloud as the provider for better reliability
RESEARCH_MODEL: str = os.getenv("RESEARCH_MODEL", "Alibaba-NLP/Tongyi-DeepResearch-30B-A3B")

# =============================================================================
# OpenRouter Configuration (Secondary provider for fallback/summarization)
# =============================================================================

OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

# Fast model for summarization (doesn't need agentic capabilities)
# Using OpenRouter for this model
SUMMARIZE_MODEL: str = os.getenv("SUMMARIZE_MODEL", "deepseek/deepseek-v3.2")

# Variable generator: fast model for strategic parameter generation (OpenRouter)
VARIABLE_GENERATOR_MODEL: str = os.getenv(
    "VARIABLE_GENERATOR_MODEL", "moonshotai/kimi-k2.5"
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

# Claude Opus 4.6 for synthesis and executive reasoning (OpenRouter)
SYNTHESIS_MODEL: str = os.getenv("SYNTHESIS_MODEL", "anthropic/claude-opus-4.6")
EXECUTIVE_MODEL: str = os.getenv("EXECUTIVE_MODEL", "anthropic/claude-opus-4.6")

# Synthesis phase: max iterations of draft -> evaluate -> re-gather -> re-normalize
MAX_SYNTHESIS_ITERATIONS: int = int(os.getenv("MAX_SYNTHESIS_ITERATIONS", "3"))
MAX_REGATHERS_PER_PARAMETER: int = int(os.getenv("MAX_REGATHERS_PER_PARAMETER", "2"))

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
    
    if not SERPER_API_KEY:
        errors.append("SERPER_API_KEY is not set. Please add it to your .env file.")
    
    if require_llm:
        # Check Atlas Cloud for research model
        if not ATLASCLOUD_API_KEY:
            errors.append("ATLAS_CLOUD_API is not set. Please add it to your .env file.")
        
        # Check OpenRouter for summarize model (optional fallback)
        if not OPENROUTER_API_KEY:
            errors.append("OPENROUTER_API_KEY is not set (needed for summarization fallback). Please add it to your .env file.")
    
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
        "atlascloud_api_key_set": bool(ATLASCLOUD_API_KEY),
        "atlascloud_api_key_prefix": ATLASCLOUD_API_KEY[:10] + "..." if ATLASCLOUD_API_KEY else None,
        "openrouter_base_url": OPENROUTER_BASE_URL,
        "openrouter_api_key_set": bool(OPENROUTER_API_KEY),
        "openrouter_api_key_prefix": OPENROUTER_API_KEY[:10] + "..." if OPENROUTER_API_KEY else None,
        "serper_api_key_set": bool(SERPER_API_KEY),
        "jina_reader_api_key_set": bool(JINA_READER_API_KEY),
        "jina_reader_base_url": JINA_READER_BASE_URL,
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
