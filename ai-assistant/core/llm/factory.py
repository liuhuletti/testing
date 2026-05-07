"""
LLM-backendin valinta konfiguraation perusteella.
"""

from __future__ import annotations

import os
import logging

from .client import LLMClient, LLMConfig

logger = logging.getLogger(__name__)


def create_llm_client(config: LLMConfig | None = None, system_prompt: str = ""):
    """
    Palauttaa oikean LLM-clientin ympäristömuuttujan perusteella.

    LLM_BACKEND=gemini  → GeminiClient
    LLM_BACKEND=claude  → LLMClient (oletus)
    """
    cfg = config or LLMConfig()
    backend = os.getenv("LLM_BACKEND", "claude").lower()

    if backend == "gemini":
        from .gemini_client import GeminiClient
        logger.info("LLM-backend: Gemini (%s)", cfg.model)
        return GeminiClient(cfg, system_prompt)

    logger.info("LLM-backend: Claude (%s)", cfg.model)
    return LLMClient(cfg, system_prompt)
