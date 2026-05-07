"""
Yksinkertainen wake word -tunnistus tekstipohjaisella vertailulla.

Toiminta:
  Whisper tunnistaa lyhyen äänipätkän ja verrataan wake wordiin.
  Ei vaadi erillisiä binäärejä (pvporcupine tms.) – toimii offline.

  Haittapuoli: viive ~0.5–1s wake wordille. Riittää MVP:hen.
  Myöhemmin voidaan vaihtaa openwakeword- tai porcupine-toteutukseen.
"""

from __future__ import annotations

import logging
import re

import numpy as np

from .transcriber import Transcriber

logger = logging.getLogger(__name__)


class WakeWordDetector:
    """
    Kuuntelee wake wordia käyttäen Whisper-tunnistusta.

    Args:
        phrase: herätyssana/-lause, esim. "hei kaisa"
        transcriber: Transcriber-instanssi (yhteinen resurssien säästämiseksi)
        threshold: minimiosuus sanoista jotka pitää täsmätä (0.0–1.0)
    """

    def __init__(
        self,
        phrase: str,
        transcriber: Transcriber,
        threshold: float = 0.8,
    ) -> None:
        self.phrase = phrase.lower().strip()
        self.phrase_words = set(self.phrase.split())
        self.transcriber = transcriber
        self.threshold = threshold

    def is_wake_word(self, audio: np.ndarray) -> bool:
        """Palauttaa True jos audio sisältää wake wordin."""
        text = self.transcriber.transcribe(audio).lower()
        text = re.sub(r"[^\w\s]", "", text)
        detected_words = set(text.split())

        if not self.phrase_words:
            return False

        overlap = self.phrase_words & detected_words
        score = len(overlap) / len(self.phrase_words)
        matched = score >= self.threshold

        logger.debug("Wake word tarkistus: '%s' (score=%.2f, matched=%s)",
                     text, score, matched)
        return matched
