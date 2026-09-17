"""SQLite persistence layer for chats, messages, attachments, and settings."""
from __future__ import annotations

import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Iterable

from app.models.entities import Attachment, Chat, Message
from app.models.settings import AppSettings


class StorageService:
    """Thread-safe SQLite repository with a deliberately small API surface."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=20)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def _initialize(self) -> None:
        schema = """
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            model TEXT NOT NULL,
            pinned INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
            role TEXT NOT NULL CHECK(role IN ('system','user','assistant')),
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
            original_name TEXT NOT NULL,
            stored_path TEXT NOT NULL,
            mime_type TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            kind TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id, id);
        CREATE INDEX IF NOT EXISTS idx_chats_pinned_updated ON chats(pinned, updated_at);
        """
        with self._lock, self._connect() as conn:
            conn.executescript(schema)

    @staticmethod
    def _dt(value: str | None) -> datetime | None:
        return datetime.fromisoformat(value) if value else None

    def create_chat(self, title: str, model: str) -> Chat:
        now = datetime.now().isoformat(timespec="seconds")
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO chats(title, model, pinned, created_at, updated_at) VALUES(?,?,?,?,?)",
                (title, model, 0, now, now),
            )
            chat_id = int(cur.lastrowid)
        return Chat(chat_id, title, model, False, self._dt(now), self._dt(now))

    def list_chats(self) -> list[Chat]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM chats ORDER BY pinned DESC, updated_at DESC, id DESC"
            ).fetchall()
        return [self._row_to_chat(row) for row in rows]

    def get_chat(self, chat_id: int) -> Chat | None:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM chats WHERE id=?", (chat_id,)).fetchone()
        return self._row_to_chat(row) if row else None

    def rename_chat(self, chat_id: int, title: str) -> None:
        self._update_chat(chat_id, "title", title)

    def set_chat_model(self, chat_id: int, model: str) -> None:
        self._update_chat(chat_id, "model", model)

    def set_chat_pinned(self, chat_id: int, pinned: bool) -> None:
        self._update_chat(chat_id, "pinned", 1 if pinned else 0)

    def _update_chat(self, chat_id: int, column: str, value: object) -> None:
        allowed = {"title", "model", "pinned"}
        if column not in allowed:
            raise ValueError(f"Unsupported chat column: {column}")
        now = datetime.now().isoformat(timespec="seconds")
        with self._lock, self._connect() as conn:
            conn.execute(
                f"UPDATE chats SET {column}=?, updated_at=? WHERE id=?",
                (value, now, chat_id),
            )

    def touch_chat(self, chat_id: int) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        with self._lock, self._connect() as conn:
            conn.execute("UPDATE chats SET updated_at=? WHERE id=?", (now, chat_id))

    def delete_chat(self, chat_id: int) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM chats WHERE id=?", (chat_id,))

    def add_message(self, chat_id: int, role: str, content: str) -> Message:
        now = datetime.now().isoformat(timespec="seconds")
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO messages(chat_id, role, content, created_at) VALUES(?,?,?,?)",
                (chat_id, role, content, now),
            )
            conn.execute("UPDATE chats SET updated_at=? WHERE id=?", (now, chat_id))
            message_id = int(cur.lastrowid)
        return Message(message_id, chat_id, role, content, self._dt(now))  # type: ignore[arg-type]

    def update_message_content(self, message_id: int, content: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("UPDATE messages SET content=? WHERE id=?", (content, message_id))

    def list_messages(self, chat_id: int) -> list[Message]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM messages WHERE chat_id=? ORDER BY id ASC", (chat_id,)
            ).fetchall()
            message_ids = [int(row["id"]) for row in rows]
            attachment_map: dict[int, list[Attachment]] = {mid: [] for mid in message_ids}
            if message_ids:
                placeholders = ",".join("?" * len(message_ids))
                arows = conn.execute(
                    f"SELECT * FROM attachments WHERE message_id IN ({placeholders}) ORDER BY id",
                    message_ids,
                ).fetchall()
                for row in arows:
                    attachment_map[int(row["message_id"])].append(self._row_to_attachment(row))
        return [
            Message(
                id=int(row["id"]),
                chat_id=int(row["chat_id"]),
                role=row["role"],
                content=row["content"],
                created_at=self._dt(row["created_at"]),
                attachments=attachment_map[int(row["id"])],
            )
            for row in rows
        ]

    def add_attachments(self, message_id: int, attachments: Iterable[Attachment]) -> list[Attachment]:
        saved: list[Attachment] = []
        with self._lock, self._connect() as conn:
            for item in attachments:
                cur = conn.execute(
                    """INSERT INTO attachments
                    (message_id, original_name, stored_path, mime_type, size_bytes, kind)
                    VALUES(?,?,?,?,?,?)""",
                    (
                        message_id,
                        item.original_name,
                        str(item.stored_path),
                        item.mime_type,
                        item.size_bytes,
                        item.kind,
                    ),
                )
                item.id = int(cur.lastrowid)
                item.message_id = message_id
                saved.append(item)
        return saved

    def get_settings(self) -> AppSettings:
        defaults = AppSettings()
        with self._lock, self._connect() as conn:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
        values = {row["key"]: row["value"] for row in rows}
        return AppSettings(
            default_model=values.get("default_model", defaults.default_model),
            theme=values.get("theme", defaults.theme),
            ollama_base_url=values.get("ollama_base_url", defaults.ollama_base_url),
            memory_char_budget=int(values.get("memory_char_budget", defaults.memory_char_budget)),
            temperature=float(values.get("temperature", defaults.temperature)),
        )

    def save_settings(self, settings: AppSettings) -> None:
        items = {
            "default_model": settings.default_model,
            "theme": settings.theme,
            "ollama_base_url": settings.ollama_base_url,
            "memory_char_budget": str(settings.memory_char_budget),
            "temperature": str(settings.temperature),
        }
        with self._lock, self._connect() as conn:
            conn.executemany(
                "INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                items.items(),
            )

    def _row_to_chat(self, row: sqlite3.Row) -> Chat:
        return Chat(
            id=int(row["id"]),
            title=row["title"],
            model=row["model"],
            pinned=bool(row["pinned"]),
            created_at=self._dt(row["created_at"]),
            updated_at=self._dt(row["updated_at"]),
        )

    @staticmethod
    def _row_to_attachment(row: sqlite3.Row) -> Attachment:
        return Attachment(
            id=int(row["id"]),
            message_id=int(row["message_id"]),
            original_name=row["original_name"],
            stored_path=Path(row["stored_path"]),
            mime_type=row["mime_type"],
            size_bytes=int(row["size_bytes"]),
            kind=row["kind"],
        )
