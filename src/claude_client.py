"""
Anthropic Claude API client for STEWARD.

Thin wrapper that handles:
- Text and vision (image) calls
- Exponential backoff on rate limits
- Typed exceptions for auth and connectivity failures
"""

import base64
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Union

import anthropic

from src.config import settings

logger = logging.getLogger(__name__)

MAX_RETRIES = 4
INITIAL_BACKOFF = 6  # seconds — longer for large scanned document payloads


class ClaudeAuthError(Exception):
    """Raised when the API key is missing or invalid."""


class ClaudeConnectionError(Exception):
    """Raised when the API cannot be reached."""


@dataclass
class ClaudeResponse:
    """API response with text and token usage."""
    text: str
    input_tokens: int = 0
    output_tokens: int = 0


class ClaudeClient:
    """
    Wrapper around the Anthropic API.

    Usage:
        client = ClaudeClient()
        text = client.generate("Summarise this document: ...")
        text = client.generate_with_images("Extract info", image_paths=[...])
    """

    def __init__(self) -> None:
        if not settings.has_api_key:
            raise ClaudeAuthError(
                "Anthropic API key missing. Copy .env.example to .env and set ANTHROPIC_API_KEY."
            )
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        model: str = "",
        max_tokens: int = 2048,
    ) -> ClaudeResponse:
        """Send a text prompt. Returns ClaudeResponse with text + token counts."""
        model = model or settings.extraction_model
        messages = [{"role": "user", "content": prompt}]
        return self._call(model, messages, system_prompt, max_tokens)

    def generate_with_images(
        self,
        prompt: str,
        image_paths: list[Path],
        system_prompt: str = "",
        model: str = "",
        max_tokens: int = 2048,
    ) -> ClaudeResponse:
        """Send a prompt with images (scanned docs). Returns ClaudeResponse."""
        model = model or settings.extraction_model
        content: list[dict] = []

        for img_path in image_paths:
            img_bytes = img_path.read_bytes()
            b64 = base64.standard_b64encode(img_bytes).decode("utf-8")
            media_type = "image/png" if img_path.suffix.lower() == ".png" else "image/jpeg"
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": media_type, "data": b64},
            })

        content.append({"type": "text", "text": prompt})
        messages = [{"role": "user", "content": content}]
        return self._call(model, messages, system_prompt, max_tokens)

    def generate_chat(
        self,
        messages: list[dict],
        system_prompt: str = "",
        model: str = "",
        max_tokens: int = 1024,
    ) -> ClaudeResponse:
        """
        Multi-turn chat: pass a full messages list (role/content dicts).
        Lets Claude see the full conversation history natively.
        """
        model = model or settings.query_model
        return self._call(model, messages, system_prompt, max_tokens)

    def _call(
        self,
        model: str,
        messages: list[dict],
        system_prompt: str,
        max_tokens: int,
    ) -> ClaudeResponse:
        """Internal: call the API with retry/backoff. Returns ClaudeResponse."""
        backoff = INITIAL_BACKOFF
        last_error: Exception = RuntimeError("Unknown error")

        for attempt in range(MAX_RETRIES):
            try:
                kwargs: dict = {
                    "model": model,
                    "max_tokens": max_tokens,
                    "messages": messages,
                }
                if system_prompt:
                    kwargs["system"] = system_prompt

                response = self._client.messages.create(**kwargs)
                return ClaudeResponse(
                    text=response.content[0].text,
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                )

            except anthropic.AuthenticationError as e:
                raise ClaudeAuthError(f"Invalid API key: {e}") from e

            except anthropic.RateLimitError as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    logger.warning("Rate limited. Retrying in %ds...", backoff)
                    time.sleep(backoff)
                    backoff *= 2

            except anthropic.APIConnectionError as e:
                # Includes timeouts and dropped connections — retry with backoff
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    logger.warning("Connection/timeout error. Retrying in %ds… (%s)", backoff, e)
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    raise ClaudeConnectionError(f"Cannot reach Anthropic API: {e}") from e

            except anthropic.APIStatusError as e:
                if e.status_code >= 500 and attempt < MAX_RETRIES - 1:
                    last_error = e
                    logger.warning("Server error %d. Retrying in %ds...", e.status_code, backoff)
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    raise

        raise ClaudeConnectionError(f"Failed after {MAX_RETRIES} attempts: {last_error}") from last_error
