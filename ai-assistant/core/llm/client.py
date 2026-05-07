"""
Claude API -wrapper.

Ominaisuudet:
  - Streaming-vastaukset matalalle viiveelle
  - Prompt-välimuisti (cache_control) tokenien säästämiseksi
  - Yhteinen virhekäsittely uudelleenyrityksellä
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Generator, Iterator

import anthropic

logger = logging.getLogger(__name__)

# Mallien nimet selkeästi yhdessä paikassa
DEFAULT_MODEL = "claude-sonnet-4-6"


@dataclass
class LLMConfig:
    model: str = DEFAULT_MODEL
    max_tokens: int = 1024
    temperature: float = 1.0
    max_retries: int = 3
    retry_delay_s: float = 1.0


@dataclass
class Message:
    role: str    # "user" | "assistant"
    content: str


class LLMClient:
    """
    Claude API -asiakas.

    Käyttö:
        client = LLMClient(config, system_prompt="Olet Kaisa…")
        response = client.chat("Mikä on tänään?", history)

    Streaming:
        for token in client.stream("Kerro vitsi.", history):
            print(token, end="", flush=True)
    """

    def __init__(
        self,
        config: LLMConfig | None = None,
        system_prompt: str = "",
    ) -> None:
        self.cfg = config or LLMConfig()
        self.system_prompt = system_prompt
        self._client = anthropic.Anthropic()

    # ── julkinen API ──────────────────────────────────────────────────────────

    def chat(self, user_message: str, history: list[Message] | None = None) -> str:
        """Lähettää viestin ja palauttaa koko vastauksen."""
        messages = self._build_messages(user_message, history or [])
        return self._call_with_retry(messages)

    def stream(
        self, user_message: str, history: list[Message] | None = None
    ) -> Generator[str, None, None]:
        """
        Streaming-generator: tuottaa tokeneita sitä mukaa kun ne saapuvat.
        Mahdollistaa TTS:n aloittamisen ennen kuin koko vastaus on valmis.
        """
        messages = self._build_messages(user_message, history or [])
        yield from self._stream_with_retry(messages)

    # ── sisäinen ─────────────────────────────────────────────────────────────

    def _build_messages(
        self, user_message: str, history: list[Message]
    ) -> list[dict]:
        msgs = [{"role": m.role, "content": m.content} for m in history]
        msgs.append({"role": "user", "content": user_message})
        return msgs

    def _call_with_retry(self, messages: list[dict]) -> str:
        for attempt in range(self.cfg.max_retries):
            try:
                response = self._client.messages.create(
                    model=self.cfg.model,
                    max_tokens=self.cfg.max_tokens,
                    temperature=self.cfg.temperature,
                    system=[
                        {
                            "type": "text",
                            "text": self.system_prompt,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ] if self.system_prompt else [],
                    messages=messages,
                )
                return response.content[0].text
            except anthropic.RateLimitError:
                wait = self.cfg.retry_delay_s * (2 ** attempt)
                logger.warning("Rate limit, odotetaan %.1fs…", wait)
                time.sleep(wait)
            except anthropic.APIError as exc:
                logger.error("API-virhe: %s", exc)
                if attempt == self.cfg.max_retries - 1:
                    raise
                time.sleep(self.cfg.retry_delay_s)
        return ""

    def _stream_with_retry(self, messages: list[dict]) -> Iterator[str]:
        for attempt in range(self.cfg.max_retries):
            try:
                with self._client.messages.stream(
                    model=self.cfg.model,
                    max_tokens=self.cfg.max_tokens,
                    temperature=self.cfg.temperature,
                    system=[
                        {
                            "type": "text",
                            "text": self.system_prompt,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ] if self.system_prompt else [],
                    messages=messages,
                ) as stream:
                    for text in stream.text_stream:
                        yield text
                return
            except anthropic.RateLimitError:
                wait = self.cfg.retry_delay_s * (2 ** attempt)
                logger.warning("Rate limit (stream), odotetaan %.1fs…", wait)
                time.sleep(wait)
            except anthropic.APIError as exc:
                logger.error("API-virhe (stream): %s", exc)
                if attempt == self.cfg.max_retries - 1:
                    raise
                time.sleep(self.cfg.retry_delay_s)
