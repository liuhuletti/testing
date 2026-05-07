"""
Testit: core/llm/client.py

Anthropic API mock → ei oikeita API-kutsuja.
"""

from unittest.mock import MagicMock, patch, PropertyMock
import pytest

from core.llm.client import LLMClient, LLMConfig, Message


def make_client(system_prompt: str = "Olet Kaisa.") -> LLMClient:
    return LLMClient(LLMConfig(model="claude-sonnet-4-6", max_tokens=100), system_prompt)


class TestLLMConfig:
    def test_defaults(self):
        cfg = LLMConfig()
        assert cfg.model == "claude-sonnet-4-6"
        assert cfg.max_tokens == 1024
        assert cfg.temperature == 1.0
        assert cfg.max_retries == 3


class TestBuildMessages:
    def test_no_history(self):
        client = make_client()
        msgs = client._build_messages("Hei", [])
        assert len(msgs) == 1
        assert msgs[0] == {"role": "user", "content": "Hei"}

    def test_with_history(self):
        client = make_client()
        history = [
            Message(role="user", content="Aiempi"),
            Message(role="assistant", content="Vastaus"),
        ]
        msgs = client._build_messages("Uusi", history)
        assert len(msgs) == 3
        assert msgs[-1] == {"role": "user", "content": "Uusi"}

    def test_empty_history(self):
        client = make_client()
        msgs = client._build_messages("kysymys", [])
        assert msgs == [{"role": "user", "content": "kysymys"}]


class TestChat:
    def test_chat_returns_text(self):
        client = make_client()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Hei, olen Kaisa.")]

        with patch.object(client._client.messages, "create", return_value=mock_response):
            result = client.chat("Moi")
        assert result == "Hei, olen Kaisa."

    def test_chat_passes_system_prompt(self):
        client = make_client("Olet testi-assistentti.")
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="ok")]

        with patch.object(client._client.messages, "create", return_value=mock_response) as mock_create:
            client.chat("testi")
            call_kwargs = mock_create.call_args.kwargs
            system = call_kwargs.get("system", [])
            assert any("Olet testi-assistentti." in s.get("text", "") for s in system)

    def test_chat_retries_on_rate_limit(self):
        client = make_client()
        client.cfg.retry_delay_s = 0  # nopeat testit

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="ok")]

        # Käytetään client._client.messages.create-mockin side_effect-ketjua
        # Ensimmäinen kutsu nostaa RateLimitError, toinen palauttaa vastauksen.
        import anthropic as ant
        RateLimitError = ant.RateLimitError

        call_count = 0
        def side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                # Nostetaan poikkeus suoraan clientin omalla luokalla
                exc = RateLimitError.__new__(RateLimitError)
                Exception.__init__(exc, "rate limit")
                raise exc
            return mock_response

        with patch.object(client._client.messages, "create", side_effect=side_effect):
            result = client.chat("testi")
        assert result == "ok"
        assert call_count == 2

    def test_no_system_prompt_empty_system(self):
        client = LLMClient(LLMConfig(), system_prompt="")
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="ok")]

        with patch.object(client._client.messages, "create", return_value=mock_response) as mock_create:
            client.chat("testi")
            system = mock_create.call_args.kwargs.get("system", [])
            assert system == []


class TestStream:
    def test_stream_yields_tokens(self):
        client = make_client()
        tokens = ["Hei", " maailma", "!"]

        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)
        mock_stream.text_stream = iter(tokens)

        with patch.object(client._client.messages, "stream", return_value=mock_stream):
            result = list(client.stream("Hei"))
        assert result == tokens

    def test_stream_empty_response(self):
        client = make_client()
        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)
        mock_stream.text_stream = iter([])

        with patch.object(client._client.messages, "stream", return_value=mock_stream):
            result = list(client.stream("Hei"))
        assert result == []
