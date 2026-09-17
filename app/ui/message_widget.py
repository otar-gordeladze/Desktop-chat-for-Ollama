"""Reusable message bubble widget."""
from __future__ import annotations

import html

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from app.models.entities import Message


class MessageWidget(QFrame):
    """Simple selectable, word-wrapped message bubble."""

    def __init__(self, message: Message, parent=None) -> None:
        super().__init__(parent)
        self.message_id = message.id
        self.setObjectName("messageUser" if message.role == "user" else "messageAssistant")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        role = QLabel("You" if message.role == "user" else "Assistant")
        role.setStyleSheet("font-weight: 600;")
        self.content = QLabel()
        self.content.setWordWrap(True)
        # Disabled text interaction during streaming to prevent Qt timer crashes
        self.content.setTextFormat(Qt.PlainText)
        self.content.setTextInteractionFlags(Qt.NoTextInteraction)
        self.content.setOpenExternalLinks(True)
        self.set_content(message.content)
        layout.addWidget(role)
        layout.addWidget(self.content)
        if message.attachments:
            names = ", ".join(a.original_name for a in message.attachments)
            attachment_label = QLabel(f"Attachments: {html.escape(names)}")
            attachment_label.setObjectName("muted")
            attachment_label.setWordWrap(True)
            layout.addWidget(attachment_label)

    def set_content(self, text: str) -> None:
        self.content.setText(text or "...")
        self.update()

    def enable_selection(self) -> None:
        self.content.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
