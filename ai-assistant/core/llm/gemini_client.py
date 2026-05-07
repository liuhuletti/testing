"""
Gemini API -wrapper.

Sama rajapinta kuin LLMClient (chat + stream) joten main.py ei muutu.
Käyttää google-generativeai -kirjastoa.
"""

from __future__ import annotations

import logging
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
        self._model = None

    def chat(self, user_message: str, history: list[Message] | None = None) -> str:
        model = self._get_model()
        chat = model.start_chat(history=self._build_history(history or []))
        for attempt in range(self.cfg.max_retries):
            try:
                response = chat.send_message(user_message)
                return response.text
            except Exception as exc:
                logger.error("Gemini virhe: %s", exc)
                if attempt == self.cfg.max_retries - 1:
                    raise
                time.sleep(self.cfg.retry_delay_s * (2 ** attempt))
        return ""

    def stream(
        self, user_message: str, history: list[Message] | None = None
    ) -> Generator[str, None, None]:
        model = self._get_model()
        chat = model.start_chat(history=self._build_history(history or []))
        for attempt in range(self.cfg.max_retries):
            try:
                response = chat.send_message(user_message, stream=True)
                for chunk in response:
                    if chunk.text:
                        yield chunk.text
                return
            except Exception as exc:
                logger.error("Gemini stream virhe: %s", exc)
                if attempt == self.cfg.max_retries - 1:
                    raise
                time.sleep(self.cfg.retry_delay_s * (2 ** attempt))

    def _get_model(self):
        if self._model is None:
            import google.generativeai as genai
            import os
            api_key = os.getenv("GEMINI_API_KEY", "")
            if not api_key:
                raise ValueError(
                    "GEMINI_API_KEY puuttuu .env-tiedostosta"
                )
            genai.configure(api_key=api_key)
            self._model = genai.GenerativeModel(
                model_name=self.cfg.model,
                system_instruction=self.system_prompt or None,
            )
        return self._model

    def _build_history(self, history: list[Message]) -> list[dict]:
        """Muuntaa Message-listan Geminin chat-historiaformaattiin."""
        result = []
        for msg in history:
            role = "user" if msg.role == "user" else "model"
            result.append({"role": role, "parts": [msg.content]})
        return result
