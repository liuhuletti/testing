"""
Testit: core/speech/wake_word.py
"""

from unittest.mock import MagicMock
import numpy as np
import pytest

from core.speech.wake_word import WakeWordDetector


def make_audio() -> np.ndarray:
    return np.zeros(16000, dtype=np.float32)


def make_detector(phrase: str = "hei kaisa", threshold: float = 0.8) -> WakeWordDetector:
    mock_transcriber = MagicMock()
    return WakeWordDetector(phrase, mock_transcriber, threshold)


class TestWakeWordDetector:
    def test_exact_match(self):
        det = make_detector("hei kaisa")
        det.transcriber.transcribe.return_value = "hei kaisa"
        assert det.is_wake_word(make_audio()) is True

    def test_partial_match_above_threshold(self):
        det = make_detector("hei kaisa", threshold=0.5)
        det.transcriber.transcribe.return_value = "hei"  # 1/2 = 0.5 >= 0.5
        assert det.is_wake_word(make_audio()) is True

    def test_partial_match_below_threshold(self):
        det = make_detector("hei kaisa tyttö", threshold=0.8)
        det.transcriber.transcribe.return_value = "hei"  # 1/3 = 0.33 < 0.8
        assert det.is_wake_word(make_audio()) is False

    def test_no_match(self):
        det = make_detector("hei kaisa")
        det.transcriber.transcribe.return_value = "mikä on sää"
        assert det.is_wake_word(make_audio()) is False

    def test_case_insensitive(self):
        det = make_detector("hei kaisa")
        det.transcriber.transcribe.return_value = "HEI KAISA"
        assert det.is_wake_word(make_audio()) is True

    def test_punctuation_stripped(self):
        det = make_detector("hei kaisa")
        det.transcriber.transcribe.return_value = "hei, kaisa!"
        assert det.is_wake_word(make_audio()) is True

    def test_empty_phrase(self):
        mock_transcriber = MagicMock()
        det = WakeWordDetector("", mock_transcriber)
        mock_transcriber.transcribe.return_value = "hei kaisa"
        assert det.is_wake_word(make_audio()) is False

    def test_extra_words_around_wake_word(self):
        det = make_detector("hei kaisa", threshold=0.8)
        det.transcriber.transcribe.return_value = "öh hei kaisa mitä"
        assert det.is_wake_word(make_audio()) is True
