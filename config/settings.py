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

# =============================================================================
# Serper API Configuration
# =============================================================================

SERPER_BASE_URL: str = "https://google.serper.dev/search"

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

# =============================================================================
# Retry Configuration
# =============================================================================

MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
RETRY_DELAY: float = float(os.getenv("RETRY_DELAY", "1.0"))

# =============================================================================
# Validation
# =============================================================================

def validate_config() -> list[str]:
    """
    Validate that required configuration is present.
    
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    if not SERPER_API_KEY:
        errors.append("SERPER_API_KEY is not set. Please add it to your .env file.")
    
    # OPENROUTER_API_KEY is optional for search layer, required later
    # if not OPENROUTER_API_KEY:
    #     errors.append("OPENROUTER_API_KEY is not set.")
    
    return errors


def ensure_directories() -> None:
    """Create necessary directories if they don't exist."""
    if CACHE_ENABLED:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)


# Auto-create directories on import
ensure_directories()
