"""Filesystem paths used by the application."""
from __future__ import annotations

from pathlib import Path

APP_NAME = "ollama-desktop-chat"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
UI_DIR = PROJECT_ROOT / "app" / "ui" / "forms"
ASSETS_DIR = PROJECT_ROOT / "app" / "assets"


def data_dir() -> Path:
    """Return and create the per-user application data directory."""
    path = Path.home() / ".local" / "share" / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def attachments_dir() -> Path:
    """Return and create the managed attachment directory."""
    path = data_dir() / "attachments"
    path.mkdir(parents=True, exist_ok=True)
    return path


def database_path() -> Path:
    """Return the SQLite database location."""
    return data_dir() / "chats.sqlite3"
