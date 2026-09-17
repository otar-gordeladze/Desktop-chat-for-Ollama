#!/bin/bash
set -e

echo "Setting up Ollama Desktop Chat..."

# 1. Create and configure the virtual environment
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
pip install -r requirements.txt

# 2. Get the current directory path dynamically
APP_DIR=$(pwd)
SHORTCUT_PATH="$HOME/.local/share/applications/ollama-desktop-chat.desktop"

# 3. Generate the desktop shortcut with the user's specific paths
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

# 4. Make it executable
chmod +x "$SHORTCUT_PATH"

echo ""
echo "Installation complete!"
echo "You can now launch 'Ollama Desktop Chat' from your application menu."