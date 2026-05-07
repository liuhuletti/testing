"""
Testit: core/speech/transcriber.py

Testausstrategia:
  - WhisperModel mock → ei ladata mallia levyltä
  - Testataan logiikka: konfiguraatio, lazy loading, device-valinta
  - Ei integraatiotestiä (vaatisi GPU/CPU + mallin latauksen)
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from core.speech.transcriber import Transcriber, TranscriberConfig


def make_dummy_audio(seconds: float = 1.0, sample_rate: int = 16000) -> np.ndarray:
    return np.zeros(int(seconds * sample_rate), dtype=np.float32)


class TestTranscriberConfig:
    def test_defaults(self):
        cfg = TranscriberConfig()
        assert cfg.model == "small"
        assert cfg.language == "fi"
        assert cfg.device == "auto"
        assert cfg.compute_type == "int8"

    def test_custom(self):
        cfg = TranscriberConfig(model="large-v3", device="cuda")
        assert cfg.model == "large-v3"
        assert cfg.device == "cuda"


class TestTranscriber:
    def _make_mock_model(self, text: str = "hei maailma"):
        segment = MagicMock()
        segment.text = text
        info = MagicMock()
        info.language = "fi"
        info.language_probability = 0.99
        model = MagicMock()
        model.transcribe.return_value = ([segment], info)
        return model

    def test_transcribe_returns_text(self):
        t = Transcriber()
        mock_model = self._make_mock_model("hei maailma")
        t._model = mock_model

        audio = make_dummy_audio()
        result = t.transcribe(audio)
        assert result == "hei maailma"

    def test_transcribe_strips_whitespace(self):
        t = Transcriber()
        mock_model = self._make_mock_model("  terve  ")
        t._model = mock_model
        assert t.transcribe(make_dummy_audio()) == "terve"

    def test_transcribe_joins_multiple_segments(self):
        seg1 = MagicMock()
        seg1.text = " hei"
        seg2 = MagicMock()
        seg2.text = " maailma"
        info = MagicMock()
        info.language = "fi"
        info.language_probability = 0.9

        t = Transcriber()
        t._model = MagicMock()
        t._model.transcribe.return_value = ([seg1, seg2], info)

        result = t.transcribe(make_dummy_audio())
        assert result == "hei maailma"

    def test_transcribe_empty_segments(self):
        info = MagicMock()
        info.language = "fi"
        info.language_probability = 0.1
        t = Transcriber()
        t._model = MagicMock()
        t._model.transcribe.return_value = ([], info)
        assert t.transcribe(make_dummy_audio()) == ""

    @patch("core.speech.transcriber.WhisperModel", create=True)
    def test_lazy_load_calls_whisper(self, MockWhisper):
        with patch.dict("sys.modules", {"faster_whisper": MagicMock(WhisperModel=MockWhisper)}):
            t = Transcriber(TranscriberConfig(model="tiny", device="cpu"))
            t._get_model()
            MockWhisper.assert_called_once_with("tiny", device="cpu", compute_type="int8")

    def test_model_loaded_only_once(self):
        t = Transcriber()
        mock_model = self._make_mock_model()
        t._model = mock_model

        t.transcribe(make_dummy_audio())
        t.transcribe(make_dummy_audio())
        # _model ei muuttunut → ladattu vain kerran
        assert t._model is mock_model

    def test_resolve_device_cpu_without_torch(self):
        t = Transcriber(TranscriberConfig(device="auto"))
        with patch.dict("sys.modules", {"torch": None}):
            device = t._resolve_device()
        assert device == "cpu"

    def test_resolve_device_explicit(self):
        t = Transcriber(TranscriberConfig(device="cpu"))
        assert t._resolve_device() == "cpu"
