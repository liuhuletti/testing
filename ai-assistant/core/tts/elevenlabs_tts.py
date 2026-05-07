"""
ElevenLabs TTS – laadukas online-vaihtoehto.

Käytetään kun Piper-laatu ei riitä tai halutaan moniäänisyyttä.
Vaatii ELEVENLABS_API_KEY-ympäristömuuttujan.
"""

from __future__ import annotations

import logging
import threading

from .synthesizer import TTSConfig, TTSEngine

logger = logging.getLogger(__name__)


class ElevenLabsTTS(TTSEngine):
    """ElevenLabs streaming TTS."""

    def __init__(self, config: TTSConfig) -> None:
        self.cfg = config
        self._stop_event = threading.Event()

    def speak(self, text: str) -> None:
        if not text.strip():
            return
        logger.debug("ElevenLabs TTS: '%s'", text[:60])
        self._stop_event.clear()

        try:
            from elevenlabs import ElevenLabs, VoiceSettings
        except ImportError:
            logger.error("elevenlabs-paketti puuttuu. Asenna: pip install elevenlabs")
            return

        import sounddevice as sd

        client = ElevenLabs()
        audio_stream = client.text_to_speech.convert_as_stream(
            text=text,
            voice_id=self.cfg.elevenlabs_voice_id,
            model_id=self.cfg.elevenlabs_model,
            voice_settings=VoiceSettings(
                stability=self.cfg.elevenlabs_stability,
                similarity_boost=self.cfg.elevenlabs_similarity_boost,
            ),
            output_format="pcm_22050",  # raw PCM, 22050Hz, 16-bit mono
        )

        sample_rate = 22050
        with sd.OutputStream(samplerate=sample_rate, channels=1, dtype="int16") as stream:
            for chunk in audio_stream:
                if self._stop_event.is_set():
                    break
                if chunk:
                    import numpy as np
                    data = np.frombuffer(chunk, dtype=np.int16)
                    stream.write(data)

    def stop(self) -> None:
        self._stop_event.set()
