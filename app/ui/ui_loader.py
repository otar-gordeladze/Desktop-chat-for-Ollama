"""Helper for loading Qt Designer .ui files."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QFile
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget


def load_ui(path: Path, parent: QWidget | None = None) -> QWidget:
    """Load and return a Qt Designer UI file."""
    qfile = QFile(str(path))
    if not qfile.open(QFile.ReadOnly):
        raise RuntimeError(f"Could not open UI file: {path}")
    try:
        widget = QUiLoader().load(qfile, parent)
    finally:
        qfile.close()
    if widget is None:
        raise RuntimeError(f"Could not load UI file: {path}")
    return widget
