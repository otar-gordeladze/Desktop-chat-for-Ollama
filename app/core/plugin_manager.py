"""Minimal plugin registry for future optional modules."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class Plugin(Protocol):
    """Interface implemented by optional application plugins."""

    name: str

    def activate(self, context: "PluginContext") -> None:
        """Register actions/services with the running application."""


@dataclass(slots=True)
class PluginContext:
    """Stable objects deliberately exposed to plugins."""

    main_window: object
    storage: object
    chat_manager: object


class PluginManager:
    """Registers and activates plugins without coupling them to core startup."""

    def __init__(self) -> None:
        self._plugins: list[Plugin] = []

    def register(self, plugin: Plugin) -> None:
        self._plugins.append(plugin)

    def activate_all(self, context: PluginContext) -> None:
        for plugin in self._plugins:
            plugin.activate(context)
