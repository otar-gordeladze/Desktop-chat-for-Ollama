"""Typed application settings."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AppSettings:
    """Global preferences loaded from persistent storage."""

    default_model: str = "llama3.2"
    theme: str = "dark"
    ollama_base_url: str = "http://127.0.0.1:11434"
    memory_char_budget: int = 32000
    temperature: float = 0.7
