# Ollama Desktop Chat

A fully local Linux desktop chat client for Ollama, written in Python and PySide6. It provides persistent multi-chat history, pinning, renaming, deletion, per-chat model selection, streaming responses, file/image attachments, global settings, and a small plugin boundary for future modules.

Target platform: **Ubuntu 24.04**.


#to make launch files run this commands
chmod +x install.sh
./install.sh

## Features

- Fully local desktop GUI; no cloud service is required by this app.
- PySide6 / Qt 6 interface with Qt Designer `.ui` files.
- Ollama HTTP API integration with streamed `/api/chat` responses.
- Local model discovery through Ollama's `/api/tags` endpoint.
- Multiple persistent chats in SQLite.
- Pinned chats sorted above normal chats.
- Rename and delete via the chat context menu.
- Per-chat model selection.
- Global default model, light/dark theme, Ollama URL, memory budget, and temperature.
- Text, source-code, CSV, JSON, YAML, Markdown, PDF, image, and generic file attachments.
- Images are base64 encoded and added to the current Ollama user message for compatible vision models.
- Text files and PDFs are extracted and appended to the current prompt context.
- Bounded in-chat memory so very old messages can be omitted from the request while remaining stored in the database.
- Network calls run in Qt worker threads so generation does not freeze the GUI.
- Plugin manager abstraction for future optional modules.
- PyInstaller build configuration for Linux distribution.

## Project structure

```text
ollama_desktop_chat/
├── main.py
├── requirements.txt
├── README.md
├── ollama-desktop-chat.spec
├── ollama-desktop-chat.desktop
├── scripts/
│   └── build_linux.sh
└── app/
    ├── __init__.py
    ├── assets/
    │   └── README.txt
    ├── core/
    │   ├── __init__.py
    │   ├── application.py
    │   ├── chat_manager.py
    │   ├── memory.py
    │   └── plugin_manager.py
    ├── models/
    │   ├── __init__.py
    │   ├── entities.py
    │   └── settings.py
    ├── plugins/
    │   ├── __init__.py
    │   └── example_plugin.py
    ├── services/
    │   ├── __init__.py
    │   ├── file_service.py
    │   ├── ollama_service.py
    │   └── storage.py
    ├── ui/
    │   ├── __init__.py
    │   ├── main_window.py
    │   ├── message_widget.py
    │   ├── settings_dialog.py
    │   ├── theme.py
    │   ├── ui_loader.py
    │   ├── workers.py
    │   └── forms/
    │       ├── main_window.ui
    │       └── settings_dialog.ui
    └── utils/
        ├── __init__.py
        ├── logging_config.py
        └── paths.py
```

## Architecture

The app uses a small layered architecture:

- **UI (`app/ui`)**: Qt widgets, Designer forms, dialogs, rendering, and background workers.
- **Core (`app/core`)**: application use cases and orchestration. `ChatManager` owns chat operations; `ChatMemory` builds a bounded model context; `PluginManager` defines the extension boundary.
- **Models (`app/models`)**: typed dataclasses shared across layers.
- **Services (`app/services`)**: SQLite, Ollama HTTP access, and attachment extraction/storage.
- **Utils (`app/utils`)**: paths and logging.
- **Assets (`app/assets`)**: icons and other distributable static resources.
- **Plugins (`app/plugins`)**: built-in or optional extension modules.

Dependencies are composed once in `ApplicationController`. The GUI does not issue raw SQL, and the persistence layer does not know anything about Qt.

## Data storage

Runtime data is kept in the user's local data directory:

```text
~/.local/share/ollama-desktop-chat/
├── chats.sqlite3
└── attachments/
```

SQLite uses foreign keys and WAL mode. The main tables are:

- `chats`: title, selected model, pinned state, timestamps.
- `messages`: chat ID, role, content, timestamp.
- `attachments`: original filename, managed path, MIME type, size, kind.
- `settings`: global key/value preferences.

Deleting a chat removes its database messages and attachment metadata through foreign-key cascades. Managed attachment files are deliberately retained in this version to avoid accidental destructive filesystem behavior. A future garbage collector can safely delete files that are no longer referenced by any database row.

## Chat memory design

`app/core/memory.py` contains a model-independent memory implementation. All messages remain persisted, but only the newest messages fitting the configured character budget are sent to Ollama.

This is intentionally simple and predictable. Future versions can replace it with:

1. tokenizer-aware limits per model;
2. automatic summaries of older turns;
3. vector retrieval over old messages and documents;
4. user-editable system memory;
5. per-chat long-term memory policies.

## Attachment behavior

### Images

PNG, JPEG, WebP, GIF, and BMP files are copied into managed local storage and converted to base64 for the current Ollama user message. The selected Ollama model must support image input.

### Text-like files

Common source, configuration, Markdown, CSV, JSON, YAML, HTML, SQL, and plain-text files are read as UTF-8 with replacement for invalid bytes. Up to 50,000 characters per attachment are included in the prompt.

### PDFs

PDF text is extracted with `pypdf`. Scanned/image-only PDFs will normally produce little or no text because OCR is intentionally not included in this base application.

### Other binary files

The file is stored and shown as an attachment, but its contents are not injected into the prompt until a dedicated extractor plugin exists.

## Prerequisites on Ubuntu 24.04

### 1. Install Python tooling

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
```

### 2. Install and start Ollama

Install Ollama using its current Linux installation instructions, then verify that it is running. The app defaults to:

```text
http://127.0.0.1:11434
```

Pull at least one model, for example:

```bash
ollama pull gemma3
```

For image input, choose a model that supports vision.

### 3. Create a virtual environment

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run from source

```bash
source .venv/bin/activate
python main.py
```

At startup the app creates the SQLite database automatically, opens or creates a chat, and attempts to load the list of locally available Ollama models.

## Using the application

### Create and manage chats

- Click **New chat** to create a separate conversation.
- Right-click a chat for **Pin**, **Rename**, or **Delete**.
- Pinned chats are sorted above unpinned chats.
- The first real user message automatically names a new chat; you can rename it later.

### Select a model

Use the model drop-down in the chat header. The selected model is saved to that chat only. Changing the global default in Settings affects future chats, not existing ones.

Use the refresh button next to the model selector after pulling or deleting Ollama models.

### Send files and images

Click the paperclip button, select one or more files, then send the message. Attachments are copied into the application's managed data directory before the request is issued.

### Settings

The Settings dialog contains:

- default model;
- theme (`dark` or `light`);
- Ollama base URL;
- memory character budget;
- generation temperature.

All settings are stored in SQLite.

## Ollama API integration

`app/services/ollama_service.py` talks directly to Ollama using `requests`.

Primary calls:

```text
GET  /api/tags
POST /api/chat
```

The chat request sends a `model`, a chronological `messages` array, streaming enabled, and runtime generation options. Streamed JSON lines are decoded incrementally and emitted back to the Qt UI through signals.

Images are base64 encoded and added to the current user message as an `images` array.

## Threading model

Qt GUI objects remain on the main thread. Slow Ollama calls run in `QThread` workers:

- `ModelListWorker`: retrieves the available model names.
- `ChatWorker`: streams one chat response.

While a response is streaming, chat/model switching is temporarily disabled. This avoids a response updating widgets belonging to another chat.

## Plugin architecture

`PluginManager` intentionally exposes only a small `PluginContext` containing stable application services. A plugin implements:

```python
class MyPlugin:
    name = "my-plugin"

    def activate(self, context: PluginContext) -> None:
        ...
```

A future discovery layer can load plugins from:

- Python package entry points;
- a user `plugins/` directory;
- signed plugin manifests;
- a settings-controlled allow-list.

Good future plugin candidates include document extractors, RAG/vector search, prompt libraries, speech input, text-to-speech, tool calling, web search, and local automation.

## Packaging as a Linux desktop executable

PyInstaller is included as the recommended packaging route. Build the Linux bundle on Linux; PyInstaller does not cross-compile between operating systems.

### Build

```bash
source .venv/bin/activate
./scripts/build_linux.sh
```

The generated one-folder build is placed at:

```text
dist/OllamaDesktopChat/
```

Run it with:

```bash
./dist/OllamaDesktopChat/OllamaDesktopChat
```

The project uses a one-folder build first because it is easier to debug and avoids the startup extraction overhead of one-file mode.

### Optional one-file build

After verifying the one-folder package works, you can create a single executable by adapting the `.spec` file or running a command such as:

```bash
pyinstaller --clean --noconfirm --windowed --onefile \
  --add-data "app/ui/forms:app/ui/forms" \
  --add-data "app/assets:app/assets" \
  --hidden-import PySide6.QtUiTools \
  --name OllamaDesktopChat main.py
```

### Desktop launcher installation

For a per-user installation, copy the bundle somewhere stable, for example:

```bash
mkdir -p ~/.local/opt/ollama-desktop-chat
cp -a dist/OllamaDesktopChat/. ~/.local/opt/ollama-desktop-chat/
```

Then copy and edit the included launcher:

```bash
mkdir -p ~/.local/share/applications
cp ollama-desktop-chat.desktop ~/.local/share/applications/
```

Change its `Exec=` line to the absolute executable path, for example:

```text
Exec=/home/YOUR_USER/.local/opt/ollama-desktop-chat/OllamaDesktopChat
```

Then make the desktop entry executable if your desktop environment requires it:

```bash
chmod +x ~/.local/share/applications/ollama-desktop-chat.desktop
```

### Linux binary compatibility note

For broad Linux compatibility, build on the oldest Linux version you intend to support. For this project, building on Ubuntu 24.04 is appropriate when Ubuntu 24.04 is the minimum supported target.

## Development checks

Syntax-check the complete source tree:

```bash
python -m compileall -q .
```

A useful next step for a production deployment is to add `pytest`, temporary SQLite fixtures, mocked Ollama HTTP responses, and Qt UI tests using `pytest-qt`.

## Security and privacy notes

- Chat data is stored locally in SQLite.
- Attachments are copied into the user's local application data directory.
- The default Ollama URL is loopback-only.
- If you change the base URL to a remote host, prompts and attachments are sent to that host. The app does not add TLS or authentication on its own.
- Treat imported files as untrusted content. The application reads text/PDF content but never executes uploaded files.
- For shared machines, consider filesystem permissions or full-disk encryption because the SQLite database is not application-level encrypted.

## Known limitations

- Markdown is displayed as safe escaped text rather than a full Markdown renderer.
- There is no stop-generation button yet.
- No OCR is performed for scanned PDFs.
- Generic binary files are stored but not semantically parsed.
- Attachment file cleanup is conservative and not automatic.
- The memory limit is character-based, not token-based.
- The plugin registry exists, but automatic third-party discovery is intentionally not enabled yet.

## Browser-access roadmap

The desktop architecture is already separated so the service/core layer can be reused behind a web API.

### Phase 1 — Extract an application API layer

Create framework-independent use cases for:

- list/create/rename/pin/delete chats;
- list/add messages;
- upload attachments;
- list Ollama models;
- read/write settings;
- streamed generation.

The existing `StorageService`, `ChatManager`, `ChatMemory`, and `OllamaService` can remain mostly unchanged.

### Phase 2 — Add FastAPI

Recommended backend layout:

```text
web/
├── api/
│   ├── chats.py
│   ├── messages.py
│   ├── models.py
│   ├── uploads.py
│   └── settings.py
├── dependencies.py
└── server.py
```

Suggested endpoints:

```text
GET    /api/chats
POST   /api/chats
PATCH  /api/chats/{id}
DELETE /api/chats/{id}
GET    /api/chats/{id}/messages
POST   /api/chats/{id}/messages
POST   /api/chats/{id}/attachments
GET    /api/models
GET    /api/settings
PUT    /api/settings
```

For generation, use Server-Sent Events or WebSockets so browser clients receive tokens as Ollama streams them.

### Phase 3 — Add a web frontend

A React, Vue, Svelte, or lightweight server-rendered frontend can mirror the desktop UX:

- chat sidebar;
- pin/rename/delete controls;
- model selector;
- attachment upload;
- streamed assistant messages;
- settings page.

### Phase 4 — Local network access

Bind FastAPI to `127.0.0.1` by default. If LAN access is enabled later, add authentication, CSRF protections where applicable, strict upload limits, and TLS through a reverse proxy such as Caddy or Nginx.

### Phase 5 — Shared desktop/web core

Keep PySide6 as one presentation layer and the browser as another. Both should call the same core use cases rather than duplicating chat logic.

## Suggested future improvements

1. Stop/cancel generation button.
2. Markdown and syntax-highlighted code rendering.
3. Token-aware context management.
4. Summarized long-term memory.
5. RAG over uploaded folders and PDFs.
6. Model metadata/capability detection.
7. Drag-and-drop attachments.
8. Chat export/import.
9. Search across all conversations.
10. Optional encrypted database.
11. Tool/function calling.
12. Automatic plugin discovery with permissions.
13. FastAPI browser backend.
14. Automated tests and CI.
15. AppImage, Flatpak, or Debian package generation.

## License

No license is imposed by this generated project. Add the license appropriate for your intended use before redistribution.
