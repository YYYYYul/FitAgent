"""
Unified LLM Client for FitAgent.

All LLM calls across the entire Agent MUST go through this client.
Provides: chat(), chat_structured(), retry, timeout, and graceful fallback.

Design:
- Reads configuration from Settings (env / defaults)
- Uses OpenAI-compatible API (works with DeepSeek, OpenAI, etc.)
- Lazily initializes the underlying client to avoid errors on import
- is_available property → False when no API key → Agent runs in fallback mode
"""

import json
import re
import asyncio
from typing import Optional

from openai import AsyncOpenAI
from app.config import get_settings


class LLMClient:
    """Unified LLM client for all Agent components.

    Usage:
        client = LLMClient()
        if client.is_available:
            reply = await client.chat(messages=[...])
        else:
            # use fallback logic
    """

    def __init__(self):
        settings = get_settings()
        self._api_key = settings.LLM_API_KEY
        self._base_url = settings.LLM_BASE_URL
        self._model = settings.LLM_MODEL
        self._temperature = settings.LLM_TEMPERATURE
        self._client: Optional[AsyncOpenAI] = None

        # Timeout & retry configuration
        self.default_timeout = 30.0  # seconds
        self.max_retries = 1

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_available(self) -> bool:
        """Returns True if a real API key is configured. False → Agent runs in fallback mode."""
        return bool(self._api_key and self._api_key not in ("your-api-key-here", ""))

    @property
    def model(self) -> str:
        return self._model

    # ------------------------------------------------------------------
    # Core chat methods
    # ------------------------------------------------------------------

    async def chat(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: int = 500,
        timeout: Optional[float] = None,
    ) -> str:
        """
        Standard LLM chat completion.

        Args:
            messages: list of {"role": "...", "content": "..."}
            temperature: 0.0–2.0, defaults to config LLM_TEMPERATURE
            max_tokens: response length limit
            timeout: per-request timeout in seconds

        Returns:
            LLM response text

        Raises:
            RuntimeError: if LLM is not available (no API key)
            Exception: on network / API errors after retries exhausted
        """
        if not self.is_available:
            raise RuntimeError("LLM not available: no API key configured")

        client = self._get_client()
        temp = temperature if temperature is not None else self._temperature
        t = timeout if timeout is not None else self.default_timeout

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                response = await asyncio.wait_for(
                    client.chat.completions.create(
                        model=self._model,
                        messages=messages,
                        temperature=temp,
                        max_tokens=max_tokens,
                    ),
                    timeout=t,
                )
                return response.choices[0].message.content or ""
            except asyncio.TimeoutError:
                last_error = TimeoutError(f"LLM request timed out after {t}s")
            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    await asyncio.sleep(1.0)  # brief backoff before retry

        raise RuntimeError(f"LLM request failed after {self.max_retries + 1} attempts: {last_error}")

    async def chat_structured(
        self,
        messages: list[dict],
        output_format: str = "json_object",
        temperature: float = 0.1,
        max_tokens: int = 500,
        timeout: Optional[float] = None,
    ) -> dict:
        """
        LLM completion with structured (JSON) output.

        Used for: intent classification, workout parsing, plan generation.

        Args:
            messages: list of message dicts
            output_format: "json_object" (most APIs)
            temperature: low for structured tasks (default 0.1)
            max_tokens: response length limit
            timeout: per-request timeout

        Returns:
            Parsed JSON dict

        Raises:
            RuntimeError: if LLM is not available
            ValueError: if the response is not valid JSON
        """
        if not self.is_available:
            raise RuntimeError("LLM not available: no API key configured")

        client = self._get_client()
        t = timeout if timeout is not None else self.default_timeout

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                response = await asyncio.wait_for(
                    client.chat.completions.create(
                        model=self._model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        response_format={"type": output_format},
                    ),
                    timeout=t,
                )
                content = response.choices[0].message.content or "{}"
                return self._extract_json(content)
            except asyncio.TimeoutError:
                last_error = TimeoutError(f"LLM structured request timed out after {t}s")
            except json.JSONDecodeError:
                # JSON parse failure → retry with a correction prompt
                messages.append({"role": "user", "content": "Your previous response was not valid JSON. Please output ONLY valid JSON."})
                last_error = ValueError("Invalid JSON in LLM response")
            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    await asyncio.sleep(1.0)

        raise RuntimeError(f"LLM structured request failed after {self.max_retries + 1} attempts: {last_error}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_client(self) -> AsyncOpenAI:
        """Lazily initialize and cache the OpenAI-compatible client."""
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
                timeout=self.default_timeout,
                max_retries=0,  # we handle retries ourselves
            )
        return self._client

    @staticmethod
    def _extract_json(text: str) -> dict:
        """
        Extract JSON from LLM response text.
        Handles markdown code blocks and leading/trailing text.
        """
        text = text.strip()
        # Remove markdown code fences
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        # Try to find JSON object
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        # Fallback: try parsing the whole text
        return json.loads(text.strip())
