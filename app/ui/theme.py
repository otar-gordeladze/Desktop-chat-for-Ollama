"""Application-wide Qt style sheets."""
from __future__ import annotations

DARK = """
QWidget { background: #1e1f22; color: #e7e9ec; font-size: 14px; }
QMainWindow, QDialog { background: #1e1f22; }
QListWidget { background: #17181b; border: none; padding: 6px; }
QListWidget::item { padding: 10px; border-radius: 7px; }
QListWidget::item:selected { background: #34373d; }
QTextEdit, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background: #292b30; border: 1px solid #3b3f46; border-radius: 7px; padding: 7px;
}
QPushButton { background: #34373d; border: 1px solid #464a52; border-radius: 7px; padding: 7px 11px; }
QPushButton:hover { background: #40444b; }
QPushButton#sendButton { background: #4d7cff; color: white; font-weight: 600; }
QFrame#messageUser { background: #2d3956; border-radius: 10px; }
QFrame#messageAssistant { background: #25272b; border-radius: 10px; }
QLabel#statusLabel, QLabel#attachmentLabel { color: #9ba1aa; }
QSplitter::handle { background: #303238; width: 1px; }
"""

LIGHT = """
QWidget { background: #f6f7f9; color: #202124; font-size: 14px; }
QMainWindow, QDialog { background: #f6f7f9; }
QListWidget { background: #eceef2; border: none; padding: 6px; }
QListWidget::item { padding: 10px; border-radius: 7px; }
QListWidget::item:selected { background: #d7dce5; }
QTextEdit, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background: white; border: 1px solid #c9ced8; border-radius: 7px; padding: 7px;
}
QPushButton { background: white; border: 1px solid #c9ced8; border-radius: 7px; padding: 7px 11px; }
QPushButton:hover { background: #eef1f5; }
QPushButton#sendButton { background: #315fcc; color: white; font-weight: 600; }
QFrame#messageUser { background: #dce7ff; border-radius: 10px; }
QFrame#messageAssistant { background: #ffffff; border-radius: 10px; }
QLabel#statusLabel, QLabel#attachmentLabel { color: #6c737f; }
"""


def stylesheet(theme: str) -> str:
    return LIGHT if theme.lower() == "light" else DARK
