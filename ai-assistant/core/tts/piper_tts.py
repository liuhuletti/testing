"""
Piper TTS – offline suomen kieli.

Piper-binääri ajetaan subprosessina: teksti syötetään stdin:iin,
WAV-data luetaan stdout:ista ja toistetaan sounddevice-kirjastolla.

Mallin lataus:
  Windows: https://huggingface.co/rhasspy/piper-voices/tree/main/fi/fi_FI/harri/medium
  Lataa: fi_FI-harri-medium.onnx + fi_FI-harri-medium.onnx.json
  Piper exe: https://github.com/rhasspy/piper/releases
"""

from __future__ import annotations

import io
import logging
import subprocess
import threading
import wave

import numpy as np
import sounddevice as sd

from .synthesizer import TTSConfig, TTSEngine

logger = logging.getLogger(__name__)


class PiperTTS(TTSEngine):
    """Offline TTS Piper-binäärillä."""

    def __init__(self, config: TTSConfig) -> None:
        self.cfg = config
        self._lock = threading.Lock()
        self._current_stream: sd.OutputStream | None = None
        self._stop_event = threading.Event()

    def speak(self, text: str) -> None:
        if not text.strip():
            return
        logger.debug("Piper TTS: '%s'", text[:60])
        self._stop_event.clear()

        audio_data, sample_rate = self._synthesize(text)
        if audio_data is None:
            return

        self._play(audio_data, sample_rate)

    def stop(self) -> None:
        self._stop_event.set()
        with self._lock:
            if self._current_stream is not None:
                try:
                    self._current_stream.stop()
                except Exception:
                    pass

    def _synthesize(self, text: str) -> tuple[np.ndarray | None, int]:
        """Kutsuu Piper-binääriä ja palauttaa (audio_float32, sample_rate)."""
        cmd = [
            self.cfg.piper_executable,
            "--model", self.cfg.piper_model,
            "--speaker", str(self.cfg.piper_speaker),
            "--length-scale", str(1.0 / max(self.cfg.piper_speed, 0.1)),
            "--output-raw",
        ]
        try:
            result = subprocess.run(
                cmd,
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=15,
            )
        except FileNotFoundError:
            logger.error(
                "Piper-binääriä ei löydy: '%s'. "
                "Lataa se ja aseta PIPER_EXECUTABLE ympäristömuuttuja.",
                self.cfg.piper_executable,
            )
            return None, 0
        except subprocess.TimeoutExpired:
            logger.error("Piper aikakatkaisu")
            return None, 0

        if result.returncode != 0:
            logger.error("Piper virhe: %s", result.stderr.decode())
            return None, 0

        # Piper tuottaa --output-raw: 16-bit signed, mono, 22050 Hz
        # (vaihtelee mallista, lue WAV-headerista jos --output-file käytössä)
        sample_rate = 22050
        raw = result.stdout
        audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        return audio, sample_rate

    def _play(self, audio: np.ndarray, sample_rate: int) -> None:
        with self._lock:
            try:
                self._current_stream = sd.OutputStream(
                    samplerate=sample_rate,
                    channels=1,
                    dtype="float32",
                )
                self._current_stream.start()
                chunk = 1024
                for i in range(0, len(audio), chunk):
                    if self._stop_event.is_set():
                        break
                    self._current_stream.write(audio[i : i + chunk])
                self._current_stream.stop()
                self._current_stream.close()
                self._current_stream = None
            except Exception as exc:
                logger.error("Toisto epäonnistui: %s", exc)
