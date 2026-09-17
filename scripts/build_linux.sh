#!/usr/bin/env bash
set -euo pipefail

# Build on the oldest Linux distribution you intend to support. For the target
# requested here, build on Ubuntu 24.04 x86_64 for best compatibility.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 -m pip install --upgrade pyinstaller
pyinstaller --noconfirm --clean ollama-desktop-chat.spec

echo "Built application: $ROOT/dist/OllamaDesktopChat/OllamaDesktopChat"
