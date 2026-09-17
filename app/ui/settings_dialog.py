"""Settings dialog controller."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QLineEdit, QSpinBox
)

from app.models.settings import AppSettings
from app.ui.ui_loader import load_ui
from app.utils.paths import UI_DIR


class SettingsDialog:
    """Thin controller around the Qt Designer settings form."""

    def __init__(self, settings: AppSettings, models: list[str], parent=None) -> None:
        self.dialog = load_ui(UI_DIR / "settings_dialog.ui", parent)
        assert isinstance(self.dialog, QDialog)
        self.default_model = self.dialog.findChild(QComboBox, "defaultModelCombo")
        self.theme = self.dialog.findChild(QComboBox, "themeCombo")
        self.url = self.dialog.findChild(QLineEdit, "urlEdit")
        self.memory = self.dialog.findChild(QSpinBox, "memorySpin")
        self.temperature = self.dialog.findChild(QDoubleSpinBox, "temperatureSpin")
        self.buttons = self.dialog.findChild(QDialogButtonBox, "buttonBox")

        self.default_model.addItems(models)
        if self.default_model.findText(settings.default_model) < 0:
            self.default_model.addItem(settings.default_model)
        self.default_model.setCurrentText(settings.default_model)
        self.theme.setCurrentText(settings.theme)
        self.url.setText(settings.ollama_base_url)
        self.memory.setValue(settings.memory_char_budget)
        self.temperature.setValue(settings.temperature)
        self.buttons.accepted.connect(self.dialog.accept)
        self.buttons.rejected.connect(self.dialog.reject)

    def exec(self) -> int:
        return self.dialog.exec()

    def values(self) -> AppSettings:
        return AppSettings(
            default_model=self.default_model.currentText().strip(),
            theme=self.theme.currentText().strip(),
            ollama_base_url=self.url.text().strip() or "http://127.0.0.1:11434",
            memory_char_budget=self.memory.value(),
            temperature=self.temperature.value(),
        )
