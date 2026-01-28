"""Configuration module for CompetelyClone."""

from .settings import (
    SERPER_API_KEY,
    OPENROUTER_API_KEY,
    CACHE_ENABLED,
    CACHE_DIR,
    SERPER_BASE_URL,
    OPENROUTER_BASE_URL,
    TONGYI_MODEL,
    MAX_RESEARCH_ITERATIONS,
    MIN_RESEARCH_ITERATIONS,
    LLM_TIMEOUT,
    validate_config,
)

__all__ = [
    "SERPER_API_KEY",
    "OPENROUTER_API_KEY",
    "CACHE_ENABLED",
    "CACHE_DIR",
    "SERPER_BASE_URL",
    "OPENROUTER_BASE_URL",
    "TONGYI_MODEL",
    "MAX_RESEARCH_ITERATIONS",
    "MIN_RESEARCH_ITERATIONS",
    "LLM_TIMEOUT",
    "validate_config",
]
