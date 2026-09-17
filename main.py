"""Application entry point for Ollama Desktop Chat."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.core.application import ApplicationController
from app.utils.logging_config import configure_logging


def main() -> int:
    """Start the Qt application and return the process exit code."""
    configure_logging()
    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("Ollama Desktop Chat")
    qt_app.setOrganizationName("LocalAI")

    controller = ApplicationController(qt_app)
    controller.start()
    return qt_app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
