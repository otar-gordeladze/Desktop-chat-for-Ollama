"""Example plugin showing the extension boundary.

This module is not enabled by default. A future plugin loader can discover
modules via entry points or a plugins directory and register them with the
PluginManager.
"""
from __future__ import annotations

from app.core.plugin_manager import PluginContext


class ExamplePlugin:
    """Minimal plugin implementation used as developer documentation."""

    name = "example"

    def activate(self, context: PluginContext) -> None:
        # Example: add menu actions, subscribe to application events, or expose
        # a service. Keep direct dependencies on internals to a minimum.
        del context
