"""Background Qt workers for network-bound Ollama calls."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from app.services.ollama_service import OllamaService


class ModelListWorker(QObject):
    """Fetch models without blocking the GUI thread."""

    finished = Signal(list)
    failed = Signal(str)

    def __init__(self, service: OllamaService) -> None:
        super().__init__()
        self.service = service

    @Slot()
    def run(self) -> None:
        try:
            self.finished.emit(self.service.list_models())
        except Exception as exc:
            self.failed.emit(str(exc))


class ChatWorker(QObject):
    """Stream one assistant response from Ollama."""

    chunk = Signal(str)
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, service: OllamaService, model: str, messages: list[dict], temperature: float) -> None:
        super().__init__()
        self.service = service
        self.model = model
        self.messages = messages
        self.temperature = temperature
        self._stop_requested = False

    def stop(self) -> None:
        self._stop_requested = True

    @Slot()
    def run(self) -> None:
        try:
            result = self.service.stream_chat(
                model=self.model,
                messages=self.messages,
                temperature=self.temperature,
                on_chunk=self.chunk.emit,
                should_stop=lambda: self._stop_requested,
            )
            self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))
