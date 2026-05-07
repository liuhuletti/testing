"""
TTS-abstraktiokerros.

Käyttö:
    engine = create_tts(settings)
    engine.speak("Hei, olen Kaisa.")
    engine.speak_async("Käsittelen pyyntöäsi…")  # ei-blokkaava
"""

from __future__ import annotations

import logging
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TTSConfig:
    backend: str = "piper"
    # Piper
    piper_executable: str = "piper"
    piper_model: str = "fi_FI-harri-medium.onnx"
    piper_speaker: int = 0
    piper_speed: float = 1.0
    # ElevenLabs
    elevenlabs_voice_id: str = ""
    elevenlabs_model: str = "eleven_multilingual_v2"
    elevenlabs_stability: float = 0.5
    elevenlabs_similarity_boost: float = 0.75


class TTSEngine(ABC):
    """Yhteinen rajapinta kaikille TTS-backendaineille."""

    @abstractmethod
    def speak(self, text: str) -> None:
        """Puhuu tekstin ääneen – blokkaa kunnes valmis."""

    def speak_async(self, text: str) -> threading.Thread:
        """Puhuu tekstin erillisessä säikeessä."""
        t = threading.Thread(target=self.speak, args=(text,), daemon=True)
        t.start()
        return t

    def stop(self) -> None:
        """Keskeyttää meneillään olevan puheen (toteutus backendissä)."""


def create_tts(config: TTSConfig | None = None) -> TTSEngine:
    """Factory: palauttaa oikean TTS-backendin."""
    cfg = config or TTSConfig()
    if cfg.backend == "piper":
        from .piper_tts import PiperTTS
        return PiperTTS(cfg)
    if cfg.backend == "elevenlabs":
        from .elevenlabs_tts import ElevenLabsTTS
        return ElevenLabsTTS(cfg)
    raise ValueError(f"Tuntematon TTS-backend: '{cfg.backend}'")
