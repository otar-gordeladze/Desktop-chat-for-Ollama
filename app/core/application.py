"""Top-level dependency composition for the desktop application."""
from __future__ import annotations

from PySide6.QtWidgets import QApplication

from app.core.chat_manager import ChatManager
from app.core.plugin_manager import PluginContext, PluginManager
from app.services.file_service import FileService
from app.services.ollama_service import OllamaService
from app.services.storage import StorageService
from app.ui.main_window import MainWindowController
from app.ui.theme import stylesheet
from app.utils.paths import database_path


class ApplicationController:
    """Constructs services once and owns the application-wide dependencies."""

    def __init__(self, qt_app: QApplication) -> None:
        self.qt_app = qt_app
        self.storage = StorageService(database_path())
        self.settings = self.storage.get_settings()
        self.file_service = FileService()
        self.chat_manager = ChatManager(self.storage, self.file_service)
        self.ollama = OllamaService(self.settings.ollama_base_url)
        self.plugins = PluginManager()
        self.main_window = MainWindowController(
            storage=self.storage,
            chat_manager=self.chat_manager,
            ollama=self.ollama,
            settings=self.settings,
            apply_theme_callback=self.apply_theme,
        )

    def start(self) -> None:
        self.apply_theme(self.settings.theme)
        self.main_window.show()
        self.plugins.activate_all(
            PluginContext(
                main_window=self.main_window,
                storage=self.storage,
                chat_manager=self.chat_manager,
            )
        )

    def apply_theme(self, theme: str) -> None:
        self.qt_app.setStyleSheet(stylesheet(theme))
