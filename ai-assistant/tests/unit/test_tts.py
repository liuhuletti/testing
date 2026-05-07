"""
Testit: core/tts/ (synthesizer + piper)

Ei oikeaa äänikorttia tai Piper-binääriä – kaikki mockataan.
"""

from unittest.mock import MagicMock, patch, call
import pytest

from core.tts.synthesizer import TTSConfig, TTSEngine, create_tts


class TestTTSConfig:
    def test_defaults(self):
        cfg = TTSConfig()
        assert cfg.backend == "piper"
        assert cfg.piper_speed == 1.0

    def test_custom_backend(self):
        cfg = TTSConfig(backend="elevenlabs")
        assert cfg.backend == "elevenlabs"


class TestCreateTTS:
    def test_creates_piper(self):
        from core.tts.piper_tts import PiperTTS
        engine = create_tts(TTSConfig(backend="piper"))
        assert isinstance(engine, PiperTTS)

    def test_creates_elevenlabs(self):
        from core.tts.elevenlabs_tts import ElevenLabsTTS
        engine = create_tts(TTSConfig(backend="elevenlabs"))
        assert isinstance(engine, ElevenLabsTTS)

    def test_unknown_backend_raises(self):
        with pytest.raises(ValueError, match="Tuntematon"):
            create_tts(TTSConfig(backend="tuntematon"))


class TestPiperTTS:
    def _make_engine(self):
        from core.tts.piper_tts import PiperTTS
        return PiperTTS(TTSConfig(piper_executable="piper", piper_model="test.onnx"))

    def test_speak_empty_text_is_noop(self):
        engine = self._make_engine()
        with patch("subprocess.run") as mock_run:
            engine.speak("")
            engine.speak("   ")
            mock_run.assert_not_called()

    def test_speak_calls_subprocess(self):
        engine = self._make_engine()
        import numpy as np
        dummy_audio = (np.zeros(100, dtype=np.int16).tobytes())

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = dummy_audio
        mock_result.stderr = b""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            with patch("sounddevice.OutputStream") as mock_stream_cls:
                mock_stream = MagicMock()
                mock_stream.__enter__ = MagicMock(return_value=mock_stream)
                mock_stream.__exit__ = MagicMock(return_value=False)
                mock_stream_cls.return_value = mock_stream

                engine.speak("Hei maailma")
                mock_run.assert_called_once()
                args = mock_run.call_args
                assert b"Hei maailma" in args.kwargs.get("input", b"")

    def test_speak_handles_missing_binary(self):
        engine = self._make_engine()
        with patch("subprocess.run", side_effect=FileNotFoundError):
            # ei poikkeusta ulkopuolelle
            engine.speak("testi")

    def test_speak_handles_nonzero_returncode(self):
        engine = self._make_engine()
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = b"virhe"
        with patch("subprocess.run", return_value=mock_result):
            engine.speak("testi")  # ei poikkeusta

    def test_stop_sets_stop_event(self):
        engine = self._make_engine()
        engine.stop()
        assert engine._stop_event.is_set()


class TestSpeakAsync:
    def test_speak_async_returns_thread(self):
        from core.tts.piper_tts import PiperTTS
        engine = PiperTTS(TTSConfig())
        with patch.object(engine, "speak"):
            t = engine.speak_async("testi")
            t.join(timeout=1)
            assert not t.is_alive()
