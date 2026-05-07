"""
faster-whisper STT-wrapper.

Malli ladataan kerran ja pidetään muistissa – ei ladata uudelleen
jokaista lausumaa varten.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class TranscriberConfig:
    model: str = "small"          # tiny|base|small|medium|large-v3
    language: str = "fi"
    device: str = "auto"          # auto|cpu|cuda
    compute_type: str = "int8"    # int8|float16|float32


class Transcriber:
    """
    Muuntaa float32 numpy-arrayn (16kHz mono) tekstiksi.

    Laiska lataus: malli ladataan vasta ensimmäisellä kutsulla.
    """

    def __init__(self, config: TranscriberConfig | None = None) -> None:
        self.cfg = config or TranscriberConfig()
        self._model = None

    # ── julkinen API ──────────────────────────────────────────────────────────

    def transcribe(self, audio: np.ndarray) -> str:
        """
        Palauttaa tunnistetun tekstin tai tyhjän merkkijonon.

        Args:
            audio: float32 numpy-array, 16kHz mono, arvoalue [-1, 1]
        """
        model = self._get_model()
        segments, info = model.transcribe(
            audio,
            language=self.cfg.language,
            beam_size=5,
            vad_filter=True,           # whisper sisäinen VAD – karsii hiljaisuutta
            vad_parameters={"min_silence_duration_ms": 300},
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        logger.debug("STT: '%s' (kieli=%s, todennäköisyys=%.2f)",
                     text, info.language, info.language_probability)
        return text

    def warmup(self) -> None:
        """Lataa mallin etukäteen – kutsuttavissa käynnistyksessä."""
        logger.info("Ladataan Whisper-malli '%s'…", self.cfg.model)
        self._get_model()
        logger.info("Whisper-malli valmis.")

    # ── sisäinen ─────────────────────────────────────────────────────────────

    def _get_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel  # lazy import

            device = self._resolve_device()
            logger.info("Ladataan WhisperModel: model=%s device=%s compute=%s",
                        self.cfg.model, device, self.cfg.compute_type)
            self._model = WhisperModel(
                self.cfg.model,
                device=device,
                compute_type=self.cfg.compute_type,
            )
        return self._model

    def _resolve_device(self) -> str:
        if self.cfg.device != "auto":
            return self.cfg.device
        try:
            import torch
            return "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            return "cpu"
