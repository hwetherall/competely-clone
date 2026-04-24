"""
LLM client for interacting with language models via multiple providers.

Supports:
- OpenRouter (default provider for research and synthesis models)
- Atlas Cloud (deprecated provider, opt-in via configuration)

Provides async and sync interfaces for:
- Chat completions
- Structured response parsing
- Error handling with retries
"""

import asyncio
import json as _json
import logging
from dataclasses import dataclass
from typing import AsyncIterator, Optional, List, Dict, Any, Tuple

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# Exceptions
# =============================================================================

class LLMError(Exception):
    """Base exception for LLM errors."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class TransientLLMError(LLMError):
    """Transient error that should be retried."""
    pass


class PermanentLLMError(LLMError):
    """Permanent error that should not be retried."""
    pass


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class LLMResponse:
    """Response from an LLM completion request."""
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str
    
    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "model": self.model,
            "usage": self.usage,
            "finish_reason": self.finish_reason,
        }


# =============================================================================
# LLM Client
# =============================================================================

class LLMClient:
    """
    Client for LLM completions via multiple providers.
    
    Routes requests to the appropriate provider based on the model:
    - Atlas Cloud: For explicitly configured Atlas Cloud models
    - OpenRouter: For all other models
    
    Example:
        client = LLMClient()
        response = await client.complete([
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is 2+2?"}
        ])
        print(response.content)
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """
        Initialize the LLM client.
        
        Args:
            api_key: Default API key (optional, will use provider-specific keys)
            model: Default model identifier (defaults to settings.RESEARCH_MODEL)
            base_url: Default API base URL (optional, will use provider-specific URLs)
        """
        # Default model
        self.model = model or settings.RESEARCH_MODEL
        
        # Provider configurations
        self.providers = {
            "atlascloud": {
                "api_key": settings.ATLASCLOUD_API_KEY,
                "base_url": settings.ATLASCLOUD_BASE_URL,
                "models": settings.ATLASCLOUD_MODELS,
            },
            "xai": {
                "api_key": settings.XAI_API_KEY,
                "base_url": settings.XAI_BASE_URL,
                "models": [],  # Direct xAI routing is selected by model prefix when configured.
            },
            "openrouter": {
                "api_key": settings.OPENROUTER_API_KEY,
                "base_url": settings.OPENROUTER_BASE_URL,
                "models": [],  # Default provider for all other models
            },
        }
        
        # Allow override via constructor (for backward compatibility)
        if api_key:
            self.providers["openrouter"]["api_key"] = api_key
        if base_url:
            self.providers["openrouter"]["base_url"] = base_url
        
        # Check API keys
        if self.providers["atlascloud"]["models"] and not self.providers["atlascloud"]["api_key"]:
            logger.warning("Atlas Cloud models are configured, but no Atlas Cloud API key is set.")
        if not self.providers["xai"]["api_key"] and self.model.startswith(("x-ai/", "grok-")):
            logger.warning("No xAI API key configured. xAI model calls will use OpenRouter if available.")
        if not self.providers["openrouter"]["api_key"]:
            logger.warning("No OpenRouter API key configured. OpenRouter model calls may fail.")

    @staticmethod
    def _to_xai_model(model: str) -> str:
        """Map OpenRouter-style xAI slugs to direct xAI API model ids."""
        aliases = {
            "x-ai/grok-4.1-fast": "grok-4-1-fast-non-reasoning",
            "x-ai/grok-4.1-fast:reasoning": "grok-4-1-fast-reasoning",
            "x-ai/grok-4.1-fast:non-reasoning": "grok-4-1-fast-non-reasoning",
        }
        if model in aliases:
            return aliases[model]
        if model.startswith("x-ai/"):
            return model.removeprefix("x-ai/").replace(".", "-")
        return model
    
    def _get_provider_for_model(self, model: str) -> Tuple[str, str, str]:
        """
        Get the appropriate provider configuration for a model.
        
        Args:
            model: Model identifier
            
        Returns:
            Tuple of (api_key, base_url, provider_name)
        """
        # Check if model is explicitly assigned to Atlas Cloud
        if model in self.providers["atlascloud"]["models"]:
            provider = self.providers["atlascloud"]
            return provider["api_key"], provider["base_url"], "atlascloud"

        # Prefer direct xAI for xAI models when XAI_API_KEY is configured.
        if self.providers["xai"]["api_key"] and model.startswith(("x-ai/", "grok-")):
            provider = self.providers["xai"]
            return provider["api_key"], provider["base_url"], "xai"
        
        # Default to OpenRouter for all other models
        provider = self.providers["openrouter"]
        return provider["api_key"], provider["base_url"], "openrouter"
    
    def _get_headers(self, api_key: str, provider_name: str) -> Dict[str, str]:
        """Get headers for API requests."""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        # Add OpenRouter-specific headers
        if provider_name == "openrouter":
            headers["HTTP-Referer"] = "https://github.com/competely-clone"
            headers["X-Title"] = "CompetelyClone Research Agent"
        
        return headers
    
    @retry(
        retry=retry_if_exception_type(TransientLLMError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def _execute_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute the actual API request with retry logic.
        
        Args:
            messages: List of message dicts
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            model: Model to use (defaults to self.model)
            
        Returns:
            Raw API response as dict
        """
        effective_model = model or self.model
        
        # Get provider-specific configuration
        api_key, base_url, provider_name = self._get_provider_for_model(effective_model)
        url = f"{base_url}/chat/completions"
        
        logger.debug(f"Using provider '{provider_name}' for model '{effective_model}'")
        provider_model = self._to_xai_model(effective_model) if provider_name == "xai" else effective_model
        
        payload = {
            "model": provider_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT) as client:
            try:
                response = await client.post(
                    url,
                    headers=self._get_headers(api_key, provider_name),
                    json=payload,
                )
                
                if response.status_code == 200:
                    response_json = response.json()
                    # Check if the API returned an error in the response body
                    if "error" in response_json:
                        error_info = response_json.get("error", {})
                        error_msg = error_info.get("message", str(error_info)) if isinstance(error_info, dict) else str(error_info)
                        error_code = error_info.get("code", "") if isinstance(error_info, dict) else ""
                        logger.error(
                            f"[{provider_name}] model={effective_model} returned 200 with error. "
                            f"code={error_code!r} msg={error_msg!r} "
                            f"full_error={str(response_json.get('error'))[:500]}"
                        )
                        if error_code in ("rate_limit_exceeded", "overloaded", "service_unavailable"):
                            raise TransientLLMError(f"API error: {error_msg}", status_code=429)
                        raise PermanentLLMError(f"API error: {error_msg}", status_code=response.status_code)
                    return response_json
                elif response.status_code in (429, 500, 502, 503, 504):
                    error_text = response.text[:500]
                    logger.error(
                        f"[{provider_name}] model={effective_model} HTTP {response.status_code}: {error_text}"
                    )
                    raise TransientLLMError(
                        f"Transient error {response.status_code}: {error_text}",
                        status_code=response.status_code,
                    )
                elif response.status_code in (401, 403):
                    logger.error(
                        f"[{provider_name}] model={effective_model} AUTH ERROR {response.status_code}: {response.text[:500]}"
                    )
                    raise PermanentLLMError(
                        f"Authentication error {response.status_code}. Check your {provider_name} API key.",
                        status_code=response.status_code,
                    )
                else:
                    error_text = response.text[:500]
                    logger.error(
                        f"[{provider_name}] model={effective_model} HTTP {response.status_code}: {error_text}"
                    )
                    raise PermanentLLMError(
                        f"API error {response.status_code}: {error_text}",
                        status_code=response.status_code,
                    )
                    
            except httpx.TimeoutException as e:
                raise TransientLLMError(f"Request timeout: {e}")
            except httpx.RequestError as e:
                raise TransientLLMError(f"Request error: {e}")
    
    async def complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        model_override: Optional[str] = None,
        fallback_model: Optional[str] = None,
    ) -> LLMResponse:
        """
        Send a completion request to the LLM.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            model_override: Override the default model for this request
            fallback_model: Optional fallback model to try if primary fails
            
        Returns:
            LLMResponse with generated content
            
        Raises:
            LLMError: If the request fails (and fallback also fails)
        """
        effective_model = model_override or self.model
        logger.debug(f"LLM request: {len(messages)} messages, model={effective_model}")
        
        try:
            response_data = await self._execute_completion(
                messages, temperature, max_tokens, model=effective_model
            )
        except (TransientLLMError, PermanentLLMError) as e:
            logger.error(f"LLM request failed: {e.message}")
            
            # Try fallback model if provided
            if fallback_model and fallback_model != effective_model:
                logger.info(f"Trying fallback model: {fallback_model}")
                try:
                    response_data = await self._execute_completion(
                        messages, temperature, max_tokens, model=fallback_model
                    )
                    logger.info(f"Fallback model succeeded")
                except (TransientLLMError, PermanentLLMError) as fallback_e:
                    logger.error(f"Fallback model also failed: {fallback_e.message}")
                    raise LLMError(e.message, status_code=e.status_code)
            else:
                raise LLMError(e.message, status_code=e.status_code)
        
        # Parse response
        try:
            # Log raw response structure for debugging (without full content)
            response_keys = list(response_data.keys()) if isinstance(response_data, dict) else type(response_data)
            logger.debug(f"API response keys: {response_keys}")
            
            # Check for error in response
            if "error" in response_data:
                error_info = response_data.get("error", {})
                error_msg = error_info.get("message", str(error_info)) if isinstance(error_info, dict) else str(error_info)
                raise LLMError(f"API returned error: {error_msg}")
            
            # Validate response structure
            if "choices" not in response_data:
                logger.error(f"Unexpected API response structure. Keys: {response_keys}")
                logger.error(f"Full response (truncated): {str(response_data)[:500]}")
                raise LLMError(f"Invalid API response: missing 'choices' key. Got keys: {response_keys}")
            
            choices = response_data["choices"]
            if not choices or len(choices) == 0:
                raise LLMError("API returned empty choices array")
            
            choice = choices[0]
            
            # Check for error inside the choice (some providers put errors here)
            if "error" in choice:
                error_info = choice["error"]
                error_msg = error_info.get("message", str(error_info)) if isinstance(error_info, dict) else str(error_info)
                error_code = error_info.get("code", "") if isinstance(error_info, dict) else ""
                # Check for quota/billing errors
                if "quota" in error_msg.lower() or "billing" in error_msg.lower() or error_code == "insufficient_quota":
                    raise LLMError(f"API quota exceeded: {error_msg[:200]}")
                raise LLMError(f"API error in response: {error_msg[:200]}")
            
            message = choice.get("message") or {}
            content = message.get("content") or ""
            finish_reason = choice.get("finish_reason", "unknown")
            
            # Handle case where content is still empty
            if not content:
                # Check if there's a delta (streaming response) or other content fields
                if "delta" in choice:
                    content = choice["delta"].get("content") or ""
                if not content:
                    logger.warning(f"LLM returned empty content. Choice: {choice}")
                    content = ""  # Return empty rather than failing
            
            usage = response_data.get("usage", {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            })
            
            model = response_data.get("model", self.model)
            
            logger.debug(f"LLM response: {len(content)} chars, {usage.get('total_tokens', 0)} tokens")
            
            return LLMResponse(
                content=content,
                model=model,
                usage=usage,
                finish_reason=finish_reason,
            )
            
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Failed to parse API response: {e}")
            logger.error(f"Response data (truncated): {str(response_data)[:500]}")
            raise LLMError(f"Failed to parse API response: {e}")
    
    async def complete_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        model_override: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """
        Stream completion tokens as an async generator.

        Yields content-delta strings as they arrive from the provider's
        SSE stream.  Suitable for piping into a FastAPI StreamingResponse.
        """
        effective_model = model_override or self.model
        api_key, base_url, provider_name = self._get_provider_for_model(effective_model)
        url = f"{base_url}/chat/completions"
        provider_model = self._to_xai_model(effective_model) if provider_name == "xai" else effective_model

        payload = {
            "model": provider_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        headers = self._get_headers(api_key, provider_name)

        async with httpx.AsyncClient(timeout=httpx.Timeout(settings.LLM_TIMEOUT, connect=30)) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as resp:
                if resp.status_code != 200:
                    body = await resp.aread()
                    raise LLMError(
                        f"Stream request failed ({resp.status_code}): {body[:500]}",
                        status_code=resp.status_code,
                    )
                async for raw_line in resp.aiter_lines():
                    if not raw_line.startswith("data: "):
                        continue
                    data_str = raw_line[len("data: "):]
                    if data_str.strip() == "[DONE]":
                        return
                    try:
                        chunk = _json.loads(data_str)
                    except _json.JSONDecodeError:
                        continue
                    delta = (chunk.get("choices") or [{}])[0].get("delta", {})
                    text = delta.get("content")
                    if text:
                        yield text

    def complete_sync(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """
        Synchronous wrapper for complete().
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            
        Returns:
            LLMResponse with generated content
        """
        return asyncio.run(self.complete(messages, temperature, max_tokens))
    
    async def complete_simple(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        model_override: Optional[str] = None,
        fallback_model: Optional[str] = None,
    ) -> str:
        """
        Simplified completion with just a user prompt.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            model_override: Override the default model for this request
            fallback_model: Optional fallback model to try if primary fails
            
        Returns:
            The generated content string
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = await self.complete(messages, temperature, max_tokens, model_override, fallback_model)
        return response.content
    
    def complete_simple_sync(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        model_override: Optional[str] = None,
    ) -> str:
        """Synchronous wrapper for complete_simple()."""
        return asyncio.run(
            self.complete_simple(prompt, system_prompt, temperature, max_tokens, model_override)
        )
