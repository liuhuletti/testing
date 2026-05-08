"""
Gemini API -wrapper.

Sama rajapinta kuin LLMClient (chat + stream) joten main.py ei muutu.
Käyttää google-genai -kirjastoa.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Generator

logger = logging.getLogger(__name__)

from .client import LLMConfig, Message


class GeminiClient:
    """
    Google Gemini -asiakas.

    Käyttö:
        client = GeminiClient(config, system_prompt="Olet Kaisa.")
        response = client.chat("Moi", history)
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
        self._client = None

    def chat(self, user_message: str, history: list[Message] | None = None) -> str:
        client = self._get_client()
        for attempt in range(self.cfg.max_retries):
            try:
                chat = client.chats.create(
                    model=self.cfg.model,
                    history=self._build_history(history or []),
                    config=self._gen_config(),
                )
                response = chat.send_message(user_message)
                return response.text or ""
            except Exception as exc:
                logger.error("Gemini virhe: %s", exc)
                if attempt == self.cfg.max_retries - 1:
                    raise
                time.sleep(self.cfg.retry_delay_s * (2 ** attempt))
        return ""

    def stream(
        self, user_message: str, history: list[Message] | None = None
    ) -> Generator[str, None, None]:
        client = self._get_client()
        for attempt in range(self.cfg.max_retries):
            try:
                chat = client.chats.create(
                    model=self.cfg.model,
                    history=self._build_history(history or []),
                    config=self._gen_config(),
                )
                for chunk in chat.send_message_stream(user_message):
                    if chunk.text:
                        yield chunk.text
                return
            except Exception as exc:
                logger.error("Gemini stream virhe: %s", exc)
                if attempt == self.cfg.max_retries - 1:
                    raise
                time.sleep(self.cfg.retry_delay_s * (2 ** attempt))

    def _get_client(self):
        if self._client is None:
            from google import genai
            api_key = os.getenv("GEMINI_API_KEY", "")
            if not api_key:
                raise ValueError("GEMINI_API_KEY puuttuu .env-tiedostosta")
            self._client = genai.Client(api_key=api_key)
        return self._client

    def _gen_config(self):
        from google.genai import types
        config = {"max_output_tokens": self.cfg.max_tokens}
        if self.system_prompt:
            config["system_instruction"] = self.system_prompt
        return types.GenerateContentConfig(**config)

    def _build_history(self, history: list[Message]) -> list[dict]:
        result = []
        for msg in history:
            role = "user" if msg.role == "user" else "model"
            result.append({"role": role, "parts": [{"text": msg.content}]})
        return result
