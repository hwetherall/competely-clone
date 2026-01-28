"""
LLM client for interacting with language models via OpenRouter.

Provides async and sync interfaces for:
- Chat completions
- Structured response parsing
- Error handling with retries
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

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
    Client for LLM completions via OpenRouter.
    
    Supports multiple models through OpenRouter's unified API.
    
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
            api_key: OpenRouter API key (defaults to settings.OPENROUTER_API_KEY)
            model: Model identifier (defaults to settings.TONGYI_MODEL)
            base_url: API base URL (defaults to settings.OPENROUTER_BASE_URL)
        """
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.model = model or settings.TONGYI_MODEL
        self.base_url = base_url or settings.OPENROUTER_BASE_URL
        
        if not self.api_key:
            logger.warning("No OpenRouter API key configured. LLM calls will fail.")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/competely-clone",
            "X-Title": "CompetelyClone Research Agent",
        }
    
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
    ) -> Dict[str, Any]:
        """
        Execute the actual API request with retry logic.
        
        Args:
            messages: List of message dicts
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Raw API response as dict
        """
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT) as client:
            try:
                response = await client.post(
                    url,
                    headers=self._get_headers(),
                    json=payload,
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code in (429, 500, 502, 503, 504):
                    error_text = response.text[:200]
                    raise TransientLLMError(
                        f"Transient error {response.status_code}: {error_text}",
                        status_code=response.status_code,
                    )
                elif response.status_code in (401, 403):
                    raise PermanentLLMError(
                        f"Authentication error {response.status_code}. Check your API key.",
                        status_code=response.status_code,
                    )
                else:
                    error_text = response.text[:200]
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
    ) -> LLMResponse:
        """
        Send a completion request to the LLM.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            
        Returns:
            LLMResponse with generated content
            
        Raises:
            LLMError: If the request fails
        """
        logger.debug(f"LLM request: {len(messages)} messages, model={self.model}")
        
        try:
            response_data = await self._execute_completion(
                messages, temperature, max_tokens
            )
        except (TransientLLMError, PermanentLLMError) as e:
            logger.error(f"LLM request failed: {e.message}")
            raise LLMError(e.message, status_code=e.status_code)
        
        # Parse response
        try:
            choice = response_data["choices"][0]
            content = choice["message"]["content"]
            finish_reason = choice.get("finish_reason", "unknown")
            
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
            
        except (KeyError, IndexError) as e:
            raise LLMError(f"Failed to parse API response: {e}")
    
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
    ) -> str:
        """
        Simplified completion with just a user prompt.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            The generated content string
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = await self.complete(messages, temperature, max_tokens)
        return response.content
    
    def complete_simple_sync(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Synchronous wrapper for complete_simple()."""
        return asyncio.run(
            self.complete_simple(prompt, system_prompt, temperature, max_tokens)
        )
