"""HTTP client for the local Ollama API."""
from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Callable, Iterable

import requests


class OllamaError(RuntimeError):
    """Raised when Ollama cannot satisfy a request."""


class OllamaService:
    """Small requests-based client for /api/tags and /api/chat."""

    def __init__(self, base_url: str = "http://127.0.0.1:11434") -> None:
        self.base_url = base_url.rstrip("/")

    def set_base_url(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def list_models(self) -> list[str]:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            payload = response.json()
            return sorted(model["name"] for model in payload.get("models", []) if model.get("name"))
        except requests.RequestException as exc:
            raise OllamaError(f"Cannot connect to Ollama at {self.base_url}: {exc}") from exc

    @staticmethod
    def encode_images(paths: Iterable[Path]) -> list[str]:
        return [base64.b64encode(path.read_bytes()).decode("ascii") for path in paths]

    def stream_chat(
        self,
        *,
        model: str,
        messages: list[dict],
        temperature: float,
        on_chunk: Callable[[str], None],
        should_stop: Callable[[], bool] | None = None,
        timeout_seconds: int = 600,
    ) -> str:
        """Stream a chat completion and call ``on_chunk`` for each text fragment."""
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature},
        }
        full_text: list[str] = []
        try:
            with requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                stream=True,
                timeout=(10, timeout_seconds),
            ) as response:
                response.raise_for_status()
                for raw_line in response.iter_lines(decode_unicode=True):
                    if should_stop and should_stop():
                        break
                    if not raw_line:
                        continue
                    data = json.loads(raw_line)
                    if data.get("error"):
                        raise OllamaError(str(data["error"]))
                    chunk = data.get("message", {}).get("content", "")
                    if chunk:
                        full_text.append(chunk)
                        on_chunk(chunk)
                    if data.get("done"):
                        break
        except (requests.RequestException, json.JSONDecodeError) as exc:
            raise OllamaError(f"Ollama request failed: {exc}") from exc
        return "".join(full_text)
