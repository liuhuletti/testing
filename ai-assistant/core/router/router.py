"""
Intent-reititin.

Tunnistaa käyttäjän intention tekstistä ja ohjaa pyyynnön oikealle moduulille.
MVP-toteutus: avainsanapohjainen tunnistus.
Myöhemmin: LLM-pohjainen intentio-tunnistus paremmalla tarkkuudella.

Moduulit rekisteröivät itsensä routerille käynnistyksen yhteydessä.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Callable

logger = logging.getLogger(__name__)


@dataclass
class Intent:
    name: str                  # moduulin nimi, esim. "calendar"
    confidence: float          # 0.0–1.0
    params: dict = field(default_factory=dict)  # tunnistetut parametrit


@dataclass
class RouterConfig:
    confidence_threshold: float = 0.6


@dataclass
class ModuleHandler:
    name: str
    keywords: list[str]           # suomenkieliset avainsanat
    handler: Callable[[str, dict], str]
    description: str = ""


class Router:
    """
    Reittaa käyttäjän viestin oikealle moduulille.

    Käyttö:
        router = Router(config)
        router.register(ModuleHandler("calendar", ["kalenteri", ...], handle_fn))
        result = router.route("Lisää kalenteri tapaaminen huomenna")

    Moduulin lisäys tulevaisuudessa:
        1. Luo modules/uusi_moduuli/
        2. Kutsu router.register() käynnistyksessä
        → ei tarvitse koskea routerin koodiin
    """

    def __init__(self, config: RouterConfig | None = None) -> None:
        self.cfg = config or RouterConfig()
        self._handlers: list[ModuleHandler] = []

    # ── rekisteröinti ─────────────────────────────────────────────────────────

    def register(self, handler: ModuleHandler) -> None:
        self._handlers.append(handler)
        logger.debug("Moduuli rekisteröity: '%s' (%d avainsanaa)",
                     handler.name, len(handler.keywords))

    def unregister(self, name: str) -> None:
        self._handlers = [h for h in self._handlers if h.name != name]

    # ── reititys ──────────────────────────────────────────────────────────────

    def detect_intent(self, text: str) -> Intent:
        """
        Tunnistaa intention – ei aja moduulia.
        Palauttaa Intent(name="general", confidence=0.0) jos ei osumaa.
        """
        normalized = text.lower().strip()
        best_handler: ModuleHandler | None = None
        best_score = 0.0

        for handler in self._handlers:
            score = self._score(normalized, handler.keywords)
            if score > best_score:
                best_score = score
                best_handler = handler

        if best_handler and best_score >= self.cfg.confidence_threshold:
            logger.debug("Intent: '%s' (%.2f)", best_handler.name, best_score)
            return Intent(name=best_handler.name, confidence=best_score)

        logger.debug("Ei moduulia – general LLM (paras=%.2f)", best_score)
        return Intent(name="general", confidence=0.0)

    def route(self, text: str) -> str | None:
        """
        Reittaa viestin moduulille ja palauttaa vastauksen.
        Palauttaa None jos intentio on "general" (LLM käsittelee itse).
        """
        intent = self.detect_intent(text)
        if intent.name == "general":
            return None

        handler = self._find_handler(intent.name)
        if handler is None:
            return None

        try:
            return handler.handler(text, intent.params)
        except Exception as exc:
            logger.error("Moduuli '%s' kaatui: %s", intent.name, exc)
            return None

    def list_modules(self) -> list[str]:
        return [h.name for h in self._handlers]

    # ── sisäinen ─────────────────────────────────────────────────────────────

    def _score(self, text: str, keywords: list[str]) -> float:
        """Palauttaa suhteellisen osuma-arvon 0–1."""
        if not keywords:
            return 0.0
        hits = sum(
            1 for kw in keywords
            if re.search(r"\b" + re.escape(kw) + r"\b", text)
        )
        return hits / len(keywords)

    def _find_handler(self, name: str) -> ModuleHandler | None:
        return next((h for h in self._handlers if h.name == name), None)
