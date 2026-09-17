#!/usr/bin/env bash
set -e

APP_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
SHORTCUT_DIR="$HOME/.local/share/applications"
SHORTCUT_PATH="$SHORTCUT_DIR/ollama-desktop-chat.desktop"

echo "Configuring Ollama Desktop Chat in: $APP_DIR"

# 1. Check for and install required system packages (Ubuntu/Debian)
if command -v apt &> /dev/null; then
    if ! dpkg -s libxcb-cursor0 &> /dev/null || ! dpkg -s python3-venv &> /dev/null; then
        echo "Missing required system packages (libxcb-cursor0 or python3-venv)."
        echo "Requesting administrator permission to install them..."
        sudo apt update && sudo apt install -y libxcb-cursor0 python3-venv python3-pip
    fi
fi

# 2. Create the virtual environment if it does not exist
if [ ! -d "$APP_DIR/.venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$APP_DIR/.venv" || {
        echo "Error: Failed to create venv."
        exit 1
    }
fi

# 3. Install dependencies
echo "Installing requirements..."
"$APP_DIR/.venv/bin/python" -m pip install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

# 4. Create the desktop launcher dynamically
mkdir -p "$SHORTCUT_DIR"

cat <<EOF > "$SHORTCUT_PATH"
[Desktop Entry]
Version=1.0
Type=Application
Name=Ollama Desktop Chat
Comment=Local AI Chat Client
Exec=$APP_DIR/.venv/bin/python $APP_DIR/main.py
Path=$APP_DIR
Icon=utilities-terminal
Terminal=false
Categories=Utility;Chat;
EOF

chmod +x "$SHORTCUT_PATH"
update-desktop-database "$SHORTCUT_DIR" 2>/dev/null || true

echo ""
echo "Setup complete! Open 'Ollama Desktop Chat' from your application menu."