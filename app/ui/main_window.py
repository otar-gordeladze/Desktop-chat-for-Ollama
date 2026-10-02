"""Main desktop window controller."""

from __future__ import annotations
from pathlib import Path


import os
import tempfile
import time
import json

from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtCore import QObject, QThread, Qt, Slot, QEvent
from PySide6.QtGui import QAction, QKeySequence, QShortcut, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QInputDialog,
)

from app.core.chat_manager import ChatManager
from app.core.memory import ChatMemory
from app.models.entities import Attachment, Chat, Message
from app.models.settings import AppSettings
from app.services.ollama_service import OllamaService
from app.services.storage import StorageService
from app.ui.message_widget import MessageWidget
from app.ui.settings_dialog import SettingsDialog
from app.ui.ui_loader import load_ui
from app.ui.workers import ChatWorker, ModelListWorker
from app.utils.paths import UI_DIR


class MainWindowController(QObject):
    """Coordinates user interaction while delegating business logic to services."""

    def __init__(
        self,
        storage: StorageService,
        chat_manager: ChatManager,
        ollama: OllamaService,
        settings: AppSettings,
        apply_theme_callback,
    ) -> None:
        super().__init__()
        loaded = load_ui(UI_DIR / "main_window.ui")
        assert isinstance(loaded, QMainWindow)
        self.window = loaded
        self.storage = storage
        self.chat_manager = chat_manager
        self.ollama = ollama
        self.settings = settings
        self.apply_theme_callback = apply_theme_callback
        
        self.current_chat: Chat | None = None
        self._generating_chat_id: int | None = None  # Tracks which chat is currently generating in background
        self.pending_attachments: list[Attachment] = []
        self.models: list[str] = []
        self._model_thread: QThread | None = None
        self._model_worker: ModelListWorker | None = None
        self._chat_thread: QThread | None = None
        self._chat_worker: ChatWorker | None = None
        self._assistant_widget: MessageWidget | None = None
        self._assistant_message: Message | None = None
        self._stream_text = ""

        self.chat_list = self.window.findChild(QListWidget, "chatList")
        self.new_chat_button = self.window.findChild(QPushButton, "newChatButton")
        self.settings_button = self.window.findChild(QPushButton, "settingsButton")
        self.model_combo = self.window.findChild(QComboBox, "modelCombo")
        icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "icon.jpeg"))
        self.window.setWindowIcon(QIcon(icon_path))
        self.refresh_models_button = self.window.findChild(QPushButton, "refreshModelsButton")
        self.title_label = self.window.findChild(QLabel, "chatTitleLabel")
        self.message_edit = self.window.findChild(QTextEdit, "messageEdit")
        self.attach_button = self.window.findChild(QPushButton, "attachButton")
        self.send_button = self.window.findChild(QPushButton, "sendButton")
        self.attachment_label = self.window.findChild(QLabel, "attachmentLabel")
        self.status_label = self.window.findChild(QLabel, "statusLabel")

        # Grab the old scroll area and figure out exactly where it lives in the UI
        old_scroll = self.window.findChild(QScrollArea, "messageScrollArea")
        parent_layout = old_scroll.parentWidget().layout()
        
        # Create the new WebEngine View
        self.web_view = QWebEngineView(self.window)
        
        # --- NEW: Fix the Layout Proportions ---
        from PySide6.QtWidgets import QSizePolicy
        self.web_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.message_edit.setMaximumHeight(130)  
        # ----------------------------------------
        
        self.web_view.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        self.web_view.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "chat_engine.html"))
        self.web_view.setUrl(f"file:///{template_path}")
        
        # Swap the old scroll area with our new web engine inside the exact same layout space
        parent_layout.replaceWidget(old_scroll, self.web_view)
        old_scroll.hide()

        self._connect_signals()
        self._set_initial_sizes()
        self.current_font_size = 14
        self._setup_zoom()
        self.message_edit.installEventFilter(self)

    def _connect_signals(self) -> None:
        self.new_chat_button.clicked.connect(self.create_chat)
        self.settings_button.clicked.connect(self.open_settings)
        self.chat_list.currentItemChanged.connect(self._chat_selected)
        self.chat_list.customContextMenuRequested.connect(self._chat_context_menu)
        self.model_combo.currentTextChanged.connect(self._model_changed)
        self.refresh_models_button.clicked.connect(self.refresh_models)
        self.attach_button.clicked.connect(self.choose_attachments)
        self.send_button.clicked.connect(self.send_message)

    def _set_initial_sizes(self) -> None:
        splitter = self.window.findChild(QWidget, "mainSplitter")
        if hasattr(splitter, "setSizes"):
            splitter.setSizes([270, 900])

    def show(self) -> None:
        self.refresh_models()
        # Wait for the web engine to boot before rendering messages
        self.web_view.loadFinished.connect(
            lambda: self.reload_chat_list(select_chat_id=self.chat_manager.ensure_initial_chat(self.settings.default_model).id)
        )
        self.window.show()

    def reload_chat_list(self, select_chat_id: int | None = None) -> None:
        self.chat_list.blockSignals(True)
        self.chat_list.clear()
        selected_item = None
        for chat in self.storage.list_chats():
            prefix = "📌 " if chat.pinned else ""
            item = QListWidgetItem(f"{prefix}{chat.title}")
            item.setData(Qt.UserRole, chat.id)
            item.setToolTip(f"Model: {chat.model}")
            self.chat_list.addItem(item)
            if chat.id == select_chat_id:
                selected_item = item
        self.chat_list.blockSignals(False)
        if selected_item:
            self.chat_list.setCurrentItem(selected_item)
        elif self.chat_list.count():
            self.chat_list.setCurrentRow(0)

    def create_chat(self) -> None:
        chat = self.chat_manager.new_chat(self.settings.default_model)
        self.reload_chat_list(select_chat_id=chat.id)
        self.message_edit.setFocus()

    def _chat_selected(self, current: QListWidgetItem | None, previous: QListWidgetItem | None) -> None:
        del previous
        if not current:
            return
        chat_id = int(current.data(Qt.UserRole))
        chat = self.storage.get_chat(chat_id)
        if not chat:
            return

        # Prevent wiping the active chat widget when the sidebar refreshes
        if self.current_chat and self.current_chat.id == chat.id:
            self.title_label.setText(chat.title)
            return

        self.current_chat = chat
        self.title_label.setText(chat.title)
        self._sync_model_combo(chat.model)
        self.pending_attachments.clear()
        self._update_attachment_label()
        
        # Render the messages for the newly selected chat
        self._render_messages(self.storage.list_messages(chat.id))

        # Re-bind streaming widget if returning to the generating chat
        if self._generating_chat_id == chat.id and self.messages_layout.count() > 1:
            item = self.messages_layout.itemAt(self.messages_layout.count() - 2)
            if item and item.widget():
                w = item.widget()
                if isinstance(w, MessageWidget):
                    self._assistant_widget = w
                    self._assistant_widget.set_content(self._stream_text)
        else:
            self._assistant_widget = None

    def _chat_context_menu(self, pos) -> None:
        item = self.chat_list.itemAt(pos)
        if not item:
            return
        chat = self.storage.get_chat(int(item.data(Qt.UserRole)))
        if not chat:
            return
        menu = QMenu(self.window)
        pin_action = QAction("Unpin" if chat.pinned else "Pin", menu)
        rename_action = QAction("Rename", menu)
        delete_action = QAction("Delete", menu)
        menu.addAction(pin_action)
        menu.addAction(rename_action)
        menu.addSeparator()
        menu.addAction(delete_action)
        chosen = menu.exec(self.chat_list.mapToGlobal(pos))
        if chosen == pin_action:
            self.chat_manager.toggle_pin(chat)
            self.reload_chat_list(select_chat_id=chat.id)
        elif chosen == rename_action:
            title, ok = QInputDialog.getText(self.window, "Rename chat", "Chat name:", text=chat.title)
            if ok and title.strip():
                self.chat_manager.rename(chat.id, title)
                self.reload_chat_list(select_chat_id=chat.id)
        elif chosen == delete_action:
            answer = QMessageBox.question(
                self.window,
                "Delete chat",
                f'Delete "{chat.title}" and its message history?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer == QMessageBox.Yes:
                self.chat_manager.delete(chat.id)
                replacement = self.chat_manager.ensure_initial_chat(self.settings.default_model)
                self.reload_chat_list(select_chat_id=replacement.id)

    def refresh_models(self) -> None:
        if self._model_thread and self._model_thread.isRunning():
            return
        self.status_label.setText("Loading Ollama models…")
        thread = QThread(self.window)
        worker = ModelListWorker(self.ollama)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._models_loaded)
        worker.failed.connect(self._models_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self._model_thread = thread
        self._model_worker = worker
        thread.finished.connect(self._on_model_thread_finished)
        thread.start()

    def _on_model_thread_finished(self) -> None:
        self._model_thread = None
        self._model_worker = None

    def _models_loaded(self, models: list[str]) -> None:
        self.models = models
        current = self.current_chat.model if self.current_chat else self.settings.default_model
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        self.model_combo.addItems(models)
        if current and self.model_combo.findText(current) < 0:
            self.model_combo.addItem(current)
        self.model_combo.setCurrentText(current)
        self.model_combo.blockSignals(False)
        self.status_label.setText(f"Ollama connected — {len(models)} model(s)")

    def _models_failed(self, error: str) -> None:
        current = self.current_chat.model if self.current_chat else self.settings.default_model
        self._sync_model_combo(current)
        self.status_label.setText("Ollama unavailable")
        QMessageBox.warning(self.window, "Ollama connection", error)

    def _sync_model_combo(self, model: str) -> None:
        self.model_combo.blockSignals(True)
        if self.model_combo.findText(model) < 0:
            self.model_combo.addItem(model)
        self.model_combo.setCurrentText(model)
        self.model_combo.blockSignals(False)

    def _model_changed(self, model: str) -> None:
        if self.current_chat and model.strip():
            self.chat_manager.set_model(self.current_chat.id, model)
            self.current_chat = self.storage.get_chat(self.current_chat.id)

    def choose_attachments(self) -> None:
        names, _ = QFileDialog.getOpenFileNames(
            self.window,
            "Attach files",
            str(Path.home()),
            "Supported files (*.txt *.md *.py *.json *.yaml *.yml *.csv *.pdf *.png *.jpg *.jpeg *.webp *.gif *.bmp);;All files (*)",
        )
        if not names:
            return
        try:
            self.pending_attachments.extend(self.chat_manager.import_attachments([Path(name) for name in names]))
            self._update_attachment_label()
        except Exception as exc:
            QMessageBox.critical(self.window, "Attachment error", str(exc))

    def _update_attachment_label(self) -> None:
        if not self.pending_attachments:
            self.attachment_label.setText("")
            return
        self.attachment_label.setText("Attached: " + ", ".join(a.original_name for a in self.pending_attachments))

    def send_message(self) -> None:
        # 1. If currently generating, act as a STOP button
        if self._chat_thread and self._chat_thread.isRunning():
            if self._chat_worker:
                self._chat_worker.stop()
                self.send_button.setEnabled(False)
                self.send_button.setText("Stopping…")
            return

        # 2. Otherwise, act as a normal SEND button
        if not self.current_chat:
            return

        if self._chat_worker:
            try:
                self._chat_worker.chunk.disconnect()
            except Exception:
                pass
            self._chat_worker.stop()
            
        raw_text = self.message_edit.toPlainText().strip()

        if not raw_text and not self.pending_attachments:
            return

        self._generating_chat_id = self.current_chat.id

        display_text = raw_text or "[Attachments]"
        attachments = list(self.pending_attachments)
        prompt_text = self.chat_manager.augment_user_content(display_text, attachments)
        user_message = self.chat_manager.add_user_message(self.current_chat.id, display_text, attachments)

        messages = self.storage.list_messages(self.current_chat.id)
        memory = ChatMemory(self.settings.memory_char_budget).build(messages)
        if memory:
            memory[-1]["content"] = prompt_text
            image_paths = [a.stored_path for a in attachments if a.kind == "image"]
            if image_paths:
                memory[-1]["images"] = self.ollama.encode_images(image_paths)

        assistant_message = self.chat_manager.add_assistant_placeholder(self.current_chat.id)
        
        # Send text directly to WebEngine instead of old widgets
        safe_user = json.dumps(user_message.content)
        self.web_view.page().runJavaScript(f"addMessage('user', {safe_user});")
        self.web_view.page().runJavaScript("addMessage('assistant', 'Thinking...');")
        
        self._assistant_message = assistant_message
        self._stream_text = ""

        self.message_edit.clear()
        self.pending_attachments.clear()
        self._update_attachment_label()
        self._set_generating(True)
        self.status_label.setText(f"Generating with {self.current_chat.model}…")

        thread = QThread(self.window)
        worker = ChatWorker(
            self.ollama,
            self.current_chat.model,
            memory,
            self.settings.temperature,
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.chunk.connect(self._on_stream_chunk)
        worker.finished.connect(self._on_stream_finished)
        worker.failed.connect(self._on_stream_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self._chat_thread = thread
        self._chat_worker = worker
        thread.finished.connect(self._on_chat_thread_finished)
        thread.start()
        self.reload_chat_list(select_chat_id=self.current_chat.id)

    @Slot(str)
    def _on_stream_chunk(self, chunk: str) -> None:
        self._stream_text += chunk
        if self.current_chat and self.current_chat.id == self._generating_chat_id:
            safe_text = json.dumps(self._stream_text)
            self.web_view.page().runJavaScript(f"updateCurrentMessage({safe_text});")

    @Slot(str)
    def _on_stream_finished(self, final_text: str) -> None:
        # NEW: Catch empty responses from broken custom models
        text = final_text or self._stream_text or "⚠️️ *Model returned an empty response. Try switching to a standard official model.*"
        
        if self._assistant_message:
            self.storage.update_message_content(self._assistant_message.id, text)
            
        if self.current_chat and self.current_chat.id == self._generating_chat_id:
            safe_text = json.dumps(text)
            self.web_view.page().runJavaScript(f"updateCurrentMessage({safe_text});")
            
        self.status_label.setText("Ready")
        self._set_generating(False)
        self._generating_chat_id = None
        self._chat_worker = None
        self._assistant_message = None
        self.message_edit.setFocus()

    @Slot(str)
    def _on_stream_failed(self, error: str) -> None:
        failure_text = f"[Error: {error}]"
        if self._assistant_message:
            self.storage.update_message_content(self._assistant_message.id, failure_text)
            
        if self.current_chat and self.current_chat.id == self._generating_chat_id:
            safe_text = json.dumps(failure_text)
            self.web_view.page().runJavaScript(f"updateCurrentMessage({safe_text});")
            
        self.status_label.setText("Request failed")
        self._set_generating(False)
        self._generating_chat_id = None
        self._chat_worker = None
        self._assistant_message = None
        QMessageBox.warning(self.window, "Ollama error", error)

    def _on_chat_thread_finished(self) -> None:
        self._chat_thread = None

    def _set_generating(self, generating: bool) -> None:
        if generating:
            self.send_button.setText("Stop")
            self.send_button.setStyleSheet("background: #d9534f; color: white; font-weight: 600;")
        else:
            self.send_button.setText("Send")
            self.send_button.setStyleSheet("")
            self.send_button.setEnabled(True)

        self.chat_list.setEnabled(True)  # Allow navigating between chats during generation!
        self.new_chat_button.setEnabled(not generating)
        self.model_combo.setEnabled(not generating)
        self.refresh_models_button.setEnabled(not generating)
        self.attach_button.setEnabled(not generating)
        self.settings_button.setEnabled(not generating)

    def _render_messages(self, messages: list[Message]) -> None:
        self.web_view.page().runJavaScript("clearChat();")
        for message in messages:
            safe_text = json.dumps(message.content or "")
            role = "user" if message.role == "user" else "assistant"
            self.web_view.page().runJavaScript(f"addMessage('{role}', {safe_text});")

    def _append_message_widget(self, message: Message) -> MessageWidget:
        widget = MessageWidget(message, self.window)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, widget)
        self._scroll_to_bottom()
        return widget

    def _scroll_to_bottom(self) -> None:
        sb = self.scroll_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.settings, self.models, self.window)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.settings = dialog.values()
        self.storage.save_settings(self.settings)
        self.ollama.set_base_url(self.settings.ollama_base_url)
        self.apply_theme_callback(self.settings.theme)
        self._apply_zoom()
        self.refresh_models()

    def _setup_zoom(self) -> None:
        QShortcut(QKeySequence.ZoomIn, self.window, self.zoom_in)
        QShortcut(QKeySequence.ZoomOut, self.window, self.zoom_out)
        QShortcut("Ctrl+0", self.window, self.reset_zoom)
        
        # Intercept scroll wheel on the new web view
        self._original_wheel_event = self.web_view.wheelEvent
        self.web_view.wheelEvent = self._handle_scroll_wheel

    def _handle_scroll_wheel(self, event) -> None:
        if event.modifiers() == Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
        else:
            self._original_wheel_event(event)

    def zoom_in(self) -> None:
        self.current_font_size = min(36, self.current_font_size + 1)
        self._apply_zoom()

    def zoom_out(self) -> None:
        self.current_font_size = max(10, self.current_font_size - 1)
        self._apply_zoom()

    def reset_zoom(self) -> None:
        self.current_font_size = 14
        self._apply_zoom()

    def _apply_zoom(self) -> None:
        from app.ui.theme import stylesheet
        self.window.setStyleSheet(stylesheet(self.settings.theme, self.current_font_size))
        
        # Calculate web zoom based on standard font size 14
        zoom_multiplier = self.current_font_size / 14.0
        self.web_view.setZoomFactor(zoom_multiplier)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched == self.message_edit and event.type() == QEvent.KeyPress:
            
            # --- NEW: Intercept Ctrl+V for Images ---
            if event.key() == Qt.Key_V and (event.modifiers() & Qt.ControlModifier or event.modifiers() & Qt.MetaModifier):
                clipboard = QApplication.clipboard()
                mime_data = clipboard.mimeData()
                
                # Check if the clipboard contains a screenshot/image
                if mime_data.hasImage():
                    image = clipboard.image()
                    
                    # Save the image to your system's temp folder
                    temp_dir = tempfile.gettempdir()
                    file_name = f"pasted_image_{int(time.time())}.png"
                    temp_path = os.path.join(temp_dir, file_name)
                    image.save(temp_path)
                    
                    # Automatically attach it to the UI using the chat manager
                    try:
                        new_attachments = self.chat_manager.import_attachments([Path(temp_path)])
                        self.pending_attachments.extend(new_attachments)
                        self._update_attachment_label()
                    except Exception as exc:
                        print(f"Failed to attach pasted image: {exc}")
                    
                    # Return True to block the default text-paste behavior
                    return True 
            
            # --- EXISTING: Enter & Shift+Enter Logic ---
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                if event.modifiers() & Qt.ShiftModifier:
                    return False
                else:
                    # Only allow Enter to send if we are NOT currently generating
                    if not (self._chat_thread and self._chat_thread.isRunning()):
                        self.send_message()
                    return True
                    
        return super().eventFilter(watched, event)