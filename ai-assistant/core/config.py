"""
Keskitetty konfiguraation lataus.

Lataa settings.yaml + .env ja palauttaa tyypitetyt config-objektit
jokaiselle core-moduulille.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

from core.llm.client import LLMConfig
from core.llm.prompt_builder import PersonalityConfig
from core.router.router import RouterConfig
from core.speech.listener import ListenerConfig
from core.speech.transcriber import TranscriberConfig
from core.tts.synthesizer import TTSConfig

logger = logging.getLogger(__name__)

SETTINGS_PATH = Path("config/settings.yaml")


def load_settings() -> dict:
    load_dotenv()
    if not SETTINGS_PATH.exists():
        logger.warning("settings.yaml puuttuu, käytetään oletuksia")
        return {}
    with SETTINGS_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def build_listener_config(settings: dict) -> ListenerConfig:
    s = settings.get("speech", {})
    vad = s.get("vad", {})
    ww = s.get("wake_word", {})
    return ListenerConfig(
        sample_rate=s.get("sample_rate", 16000),
        aggressiveness=vad.get("aggressiveness", 2),
        silence_threshold_ms=vad.get("silence_threshold_ms", 800),
        max_recording_s=vad.get("max_recording_s", 30),
        wake_word=ww.get("phrase") if ww.get("enabled") else None,
        wake_word_timeout_s=ww.get("timeout_s", 10),
        input_device=s.get("input_device", None),
    )


def build_transcriber_config(settings: dict) -> TranscriberConfig:
    s = settings.get("speech", {})
    return TranscriberConfig(
        model=os.getenv("WHISPER_MODEL", s.get("model", "small")),
        language=s.get("language", "fi"),
        device=s.get("device", "auto"),
        compute_type=s.get("compute_type", "int8"),
    )


def build_tts_config(settings: dict) -> TTSConfig:
    s = settings.get("tts", {})
    piper = s.get("piper", {})
    el = s.get("elevenlabs", {})
    backend = os.getenv("TTS_BACKEND", s.get("backend", "piper"))
    return TTSConfig(
        backend=backend,
        piper_executable=os.getenv("PIPER_EXECUTABLE", piper.get("executable", "piper")),
        piper_model=os.getenv("PIPER_MODEL", piper.get("model", "fi_FI-harri-medium.onnx")),
        piper_speaker=piper.get("speaker", 0),
        piper_speed=piper.get("speed", 1.0),
        elevenlabs_voice_id=os.getenv("ELEVENLABS_VOICE_ID", el.get("voice_id", "")),
        elevenlabs_model=el.get("model", "eleven_multilingual_v2"),
        elevenlabs_stability=el.get("stability", 0.5),
        elevenlabs_similarity_boost=el.get("similarity_boost", 0.75),
        output_device=s.get("output_device", None),
    )


def build_llm_config(settings: dict) -> LLMConfig:
    import os
    s = settings.get("llm", {})
    backend = os.getenv("LLM_BACKEND", "claude").lower()
    default_model = "gemini-2.0-flash" if backend == "gemini" else "claude-sonnet-4-6"
    return LLMConfig(
        model=s.get("model", default_model),
        max_tokens=s.get("max_tokens", 1024),
        temperature=s.get("temperature", 1.0),
    )


def build_router_config(settings: dict) -> RouterConfig:
    s = settings.get("router", {})
    return RouterConfig(
        confidence_threshold=s.get("confidence_threshold", 0.6),
    )
