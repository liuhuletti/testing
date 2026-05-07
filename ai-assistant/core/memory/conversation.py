"""
Lyhytaikainen keskustelumuisti.

Pitää viimeisimmät N vuoroparia muistissa LLM-kutsujen välillä.
Ei tallennus levylle – istuntokohtainen.
Pitkäaikainen muisti (SQLite) lisätään myöhemmin.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from core.llm.client import Message


@dataclass
class ConversationMemoryConfig:
    max_turns: int = 10   # yksi turn = käyttäjä + assistentti


class ConversationMemory:
    """
    FIFO-puskuri keskusteluhistorialle.

    Käyttö:
        mem = ConversationMemory()
        mem.add_user("Hei!")
        mem.add_assistant("Moi.")
        history = mem.get_history()   # lista Message-objekteja
    """

    def __init__(self, config: ConversationMemoryConfig | None = None) -> None:
        self.cfg = config or ConversationMemoryConfig()
        # Deque tallentaa Message-pareja (user, assistant)
        self._turns: deque[tuple[Message, Message]] = deque(
            maxlen=self.cfg.max_turns
        )
        self._pending_user: Message | None = None

    def add_user(self, text: str) -> None:
        self._pending_user = Message(role="user", content=text)

    def add_assistant(self, text: str) -> None:
        if self._pending_user is not None:
            self._turns.append((
                self._pending_user,
                Message(role="assistant", content=text),
            ))
            self._pending_user = None

    def get_history(self) -> list[Message]:
        """Palauttaa historian litistettynä listana (ei sisällä nykyistä user-viestiä)."""
        messages: list[Message] = []
        for user_msg, asst_msg in self._turns:
            messages.append(user_msg)
            messages.append(asst_msg)
        return messages

    def clear(self) -> None:
        self._turns.clear()
        self._pending_user = None

    def __len__(self) -> int:
        return len(self._turns)
