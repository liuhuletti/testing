"""
Pytest-konfiguraatio ja yhteiset fixturet.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

# Lisätään projektin juuri Python-polkuun
sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Stub-moduulit joita ei asenneta CI:ssä ────────────────────────────────────

def _stub(name: str) -> MagicMock:
    m = MagicMock()
    m.__name__ = name
    sys.modules[name] = m
    return m


# Stub sounddevice jos ei asennettuna (CI)
if "sounddevice" not in sys.modules:
    _stub("sounddevice")

# Stub webrtcvad
if "webrtcvad" not in sys.modules:
    stub = _stub("webrtcvad")
    stub.Vad.return_value = MagicMock(is_speech=MagicMock(return_value=False))

# Stub faster_whisper
if "faster_whisper" not in sys.modules:
    fw = _stub("faster_whisper")
    fw.WhisperModel = MagicMock()

# Stub anthropic perusrakenne
if "anthropic" not in sys.modules:
    ant = _stub("anthropic")
    ant.Anthropic = MagicMock()
    ant.RateLimitError = type("RateLimitError", (Exception,), {})
    ant.APIError = type("APIError", (Exception,), {})


# ── Yhteiset fixturet ─────────────────────────────────────────────────────────

@pytest.fixture
def dummy_audio() -> np.ndarray:
    """1 sekunnin hiljaisuus 16kHz."""
    return np.zeros(16000, dtype=np.float32)


@pytest.fixture
def sample_rate() -> int:
    return 16000
