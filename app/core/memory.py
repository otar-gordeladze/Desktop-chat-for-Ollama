"""Conversation-memory construction for Ollama requests."""
from __future__ import annotations

from app.models.entities import Message


class ChatMemory:
    """Build a bounded chronological context from persisted chat messages.

    Ollama expects a list of role/content message dictionaries. The memory
    implementation keeps the newest messages that fit within a configurable
    character budget. This is intentionally model-agnostic; it can later be
    replaced by a tokenizer-aware or summarization-based implementation.
    """

    def __init__(self, char_budget: int = 32000) -> None:
        self.char_budget = max(2000, char_budget)

    def build(self, messages: list[Message]) -> list[dict]:
        selected: list[Message] = []
        used = 0
        for message in reversed(messages):
            cost = len(message.content) + 32
            if selected and used + cost > self.char_budget:
                break
            selected.append(message)
            used += cost
        selected.reverse()
        return [{"role": m.role, "content": m.content} for m in selected]
