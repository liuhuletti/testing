"""
Testit: core/memory/conversation.py
"""

import pytest

from core.memory.conversation import ConversationMemory, ConversationMemoryConfig
from core.llm.client import Message


class TestConversationMemory:
    def test_empty_history(self):
        mem = ConversationMemory()
        assert mem.get_history() == []
        assert len(mem) == 0

    def test_add_turn(self):
        mem = ConversationMemory()
        mem.add_user("Moi")
        mem.add_assistant("Hei")
        history = mem.get_history()
        assert len(history) == 2
        assert history[0].role == "user"
        assert history[0].content == "Moi"
        assert history[1].role == "assistant"
        assert history[1].content == "Hei"

    def test_multiple_turns(self):
        mem = ConversationMemory()
        mem.add_user("Mikä on sää?")
        mem.add_assistant("Aurinkoista.")
        mem.add_user("Entä huomenna?")
        mem.add_assistant("Pilvistä.")
        history = mem.get_history()
        assert len(history) == 4
        assert len(mem) == 2

    def test_max_turns_fifo(self):
        mem = ConversationMemory(ConversationMemoryConfig(max_turns=2))
        for i in range(3):
            mem.add_user(f"kysymys {i}")
            mem.add_assistant(f"vastaus {i}")
        # Vain 2 viimeisintä turn pitäisi olla
        history = mem.get_history()
        assert len(mem) == 2
        assert history[0].content == "kysymys 1"
        assert history[2].content == "kysymys 2"

    def test_clear(self):
        mem = ConversationMemory()
        mem.add_user("Hei")
        mem.add_assistant("Moi")
        mem.clear()
        assert mem.get_history() == []
        assert len(mem) == 0

    def test_user_without_assistant_not_stored(self):
        mem = ConversationMemory()
        mem.add_user("Hei")
        # Ei add_assistant-kutsua → ei tallenneta
        assert len(mem) == 0
        assert mem.get_history() == []

    def test_history_not_include_pending_user(self):
        mem = ConversationMemory()
        mem.add_user("Aiempi")
        mem.add_assistant("Vastaus")
        mem.add_user("Nykyinen kysymys")  # tätä ei pitäisi olla historiassa
        history = mem.get_history()
        assert len(history) == 2
        assert all(m.content != "Nykyinen kysymys" for m in history)

    def test_message_types(self):
        mem = ConversationMemory()
        mem.add_user("kysymys")
        mem.add_assistant("vastaus")
        history = mem.get_history()
        assert all(isinstance(m, Message) for m in history)
