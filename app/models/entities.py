"""Domain entities shared across storage, services, and UI."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

Role = Literal["system", "user", "assistant"]


@dataclass(slots=True)
class Chat:
    """A conversation and its per-chat model selection."""

    id: int
    title: str
    model: str
    pinned: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(slots=True)
class Attachment:
    """Metadata for a file copied into application-managed storage."""

    id: int | None
    message_id: int | None
    original_name: str
    stored_path: Path
    mime_type: str
    size_bytes: int
    kind: Literal["image", "text", "pdf", "file"] = "file"


@dataclass(slots=True)
class Message:
    """A persisted chat message."""

    id: int
    chat_id: int
    role: Role
    content: str
    created_at: datetime | None = None
    attachments: list[Attachment] = field(default_factory=list)
