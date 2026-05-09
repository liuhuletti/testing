"""
Mikrofonin kuuntelu + VAD (Voice Activity Detection).

Toiminta:
  1. Kuuntelee mikrofonia jatkuvasti pienissä 30ms paloissa.
  2. webrtcvad tunnistaa sisältääkö pala puhetta.
  3. Kun puhe alkaa, kerätään audio puskuriin.
  4. Kun hiljaisuus kestää silence_threshold_ms, palataan valmis audio.
"""

from __future__ import annotations

import collections
import logging
import time
from dataclasses import dataclass, field
from typing import Generator

import numpy as np
import sounddevice as sd
import webrtcvad

logger = logging.getLogger(__name__)

# webrtcvad tukee vain näitä näytteenottotaajuuksia
SUPPORTED_RATES = (8000, 16000, 32000, 48000)
# webrtcvad kehyskoot: 10, 20 tai 30 ms
FRAME_MS = 30


@dataclass
class ListenerConfig:
    sample_rate: int = 16000
    aggressiveness: int = 2          # 0–3
    silence_threshold_ms: int = 800
    max_recording_s: float = 30.0
    wake_word: str | None = None
    wake_word_timeout_s: float = 10.0
    input_device: int | None = None  # None = järjestelmän oletus

    def __post_init__(self) -> None:
        if self.sample_rate not in SUPPORTED_RATES:
            raise ValueError(f"sample_rate oltava yksi: {SUPPORTED_RATES}")
        if self.aggressiveness not in range(4):
            raise ValueError("aggressiveness oltava 0–3")


class AudioListener:
    """
    Kuuntelee mikrofonia ja palauttaa lausumia numpy float32 -arraynä.

    Käyttö:
        listener = AudioListener(ListenerConfig())
        audio = listener.listen()        # blokkaa kunnes lausuma valmis
    """

    def __init__(self, config: ListenerConfig | None = None) -> None:
        self.cfg = config or ListenerConfig()
        self._vad = webrtcvad.Vad(self.cfg.aggressiveness)
        self._frame_bytes = int(self.cfg.sample_rate * FRAME_MS / 1000) * 2  # int16

    # ── julkinen API ──────────────────────────────────────────────────────────

    def listen(self) -> np.ndarray:
        """Blokkaa ja palauttaa yhden lausuman float32-arraynä (16kHz mono)."""
        logger.debug("Kuunnellaan…")
        raw = self._collect_speech()
        audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        logger.debug("Lausuma kerätty: %.1f s", len(audio) / self.cfg.sample_rate)
        return audio

    def listen_stream(self) -> Generator[np.ndarray, None, None]:
        """Generaattori: tuottaa lausumia loputtomasti."""
        while True:
            yield self.listen()

    # ── sisäinen toteutus ─────────────────────────────────────────────────────

    def _collect_speech(self) -> bytes:
        """
        Kerää yhden lausuman raakatavuina (PCM int16).

        Algoritmi:
          - Pidetään liukuva ikkuna (padding_frames) ennen puhealkua
            jotta sanan alku ei leikkaudu.
          - Kun puhe havaittu, kerätään puhepuhetta kunnes hiljaisuus
            ylittää silence_threshold_ms.
        """
        frame_size = self._frame_bytes // 2  # näytteet per kehys
        silence_frames_needed = int(
            self.cfg.silence_threshold_ms / FRAME_MS
        )
        # Esiääni puskuri (400ms) – tallentaa hetken ennen puheen alkua
        padding_frames = int(400 / FRAME_MS)
        ring = collections.deque(maxlen=padding_frames)

        triggered = False
        voiced_frames: list[bytes] = []
        silence_count = 0
        start_time = time.monotonic()

        with sd.RawInputStream(
            samplerate=self.cfg.sample_rate,
            blocksize=frame_size,
            dtype="int16",
            channels=1,
            device=self.cfg.input_device,
        ) as stream:
            while True:
                raw_frame, _ = stream.read(frame_size)
                frame_bytes = bytes(raw_frame)

                if len(frame_bytes) < self._frame_bytes:
                    continue

                is_speech = self._is_speech(frame_bytes)

                if not triggered:
                    ring.append(frame_bytes)
                    if is_speech:
                        triggered = True
                        logger.debug("Puhe alkoi")
                        voiced_frames.extend(ring)
                        ring.clear()
                else:
                    voiced_frames.append(frame_bytes)
                    if is_speech:
                        silence_count = 0
                    else:
                        silence_count += 1
                        if silence_count >= silence_frames_needed:
                            logger.debug("Hiljaisuus havaittu, lausuma valmis")
                            break

                # turvaraja
                if time.monotonic() - start_time > self.cfg.max_recording_s:
                    logger.warning("Max tallennusaika ylitetty")
                    break

        return b"".join(voiced_frames)

    def _is_speech(self, frame: bytes) -> bool:
        try:
            return self._vad.is_speech(frame, self.cfg.sample_rate)
        except Exception:
            return False
