"""High-level chat use cases."""
from __future__ import annotations

from pathlib import Path

from app.models.entities import Attachment, Chat, Message
from app.services.file_service import FileService
from app.services.storage import StorageService


class ChatManager:
    """Coordinates chat persistence, naming, pinning, and attachments."""

    def __init__(self, storage: StorageService, files: FileService) -> None:
        self.storage = storage
        self.files = files

    def ensure_initial_chat(self, default_model: str) -> Chat:
        chats = self.storage.list_chats()
        return chats[0] if chats else self.storage.create_chat("New chat", default_model)

    def new_chat(self, default_model: str) -> Chat:
        return self.storage.create_chat("New chat", default_model)

    def rename(self, chat_id: int, title: str) -> None:
        cleaned = " ".join(title.split()).strip()
        if cleaned:
            self.storage.rename_chat(chat_id, cleaned[:120])

    def toggle_pin(self, chat: Chat) -> None:
        self.storage.set_chat_pinned(chat.id, not chat.pinned)

    def delete(self, chat_id: int) -> None:
        # Attachment files are intentionally retained for safety in this simple
        # version. A future garbage collector can remove unreferenced files.
        self.storage.delete_chat(chat_id)

    def set_model(self, chat_id: int, model: str) -> None:
        if model.strip():
            self.storage.set_chat_model(chat_id, model.strip())

    def add_user_message(
        self,
        chat_id: int,
        text: str,
        pending_attachments: list[Attachment],
    ) -> Message:
        message = self.storage.add_message(chat_id, "user", text)
        message.attachments = self.storage.add_attachments(message.id, pending_attachments)
        self._auto_title(chat_id, text)
        return message

    def add_assistant_placeholder(self, chat_id: int) -> Message:
        return self.storage.add_message(chat_id, "assistant", "")

    def import_attachments(self, paths: list[Path]) -> list[Attachment]:
        return [self.files.import_file(path) for path in paths]

    def augment_user_content(self, text: str, attachments: list[Attachment]) -> str:
        """Append textual attachment contents to the user prompt context."""
        sections = [text.strip()]
        for attachment in attachments:
            if attachment.kind in {"text", "pdf", "file"}:
                extracted = self.files.extract_text(attachment)
                sections.append(
                    f"\n--- Attached file: {attachment.original_name} ---\n{extracted}\n--- End attachment ---"
                )
        return "\n".join(section for section in sections if section).strip()

    def _auto_title(self, chat_id: int, text: str) -> None:
        chat = self.storage.get_chat(chat_id)
        if not chat or chat.title != "New chat":
            return
        first_line = " ".join(text.strip().split())
        if first_line:
            title = first_line[:48] + ("…" if len(first_line) > 48 else "")
            self.storage.rename_chat(chat_id, title)
