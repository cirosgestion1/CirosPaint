from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.services.assistant_async_tasks import AssistantRequestTask
from app.services.assistant_session_store import AssistantSessionStore
from app.services.assistant_settings_store import AssistantSettingsStore
from app.ui.dialogs.assistant_info_dialog import AssistantInfoDialog


class AssistantMessageBubble(QFrame):
    def __init__(self, role: str, content: str, parent=None):
        super().__init__(parent)
        self.role = role
        self.setObjectName("AssistantUserBubble" if role == "user" else "AssistantModelBubble")
        self.setMaximumWidth(760)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)

        label = QLabel(content)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        label.setStyleSheet("color: #f1f5f9; font-size: 10pt;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.addWidget(label)

        if role == "user":
            self.setStyleSheet(
                "QFrame#AssistantUserBubble { background: #2d5a45; border: 1px solid #3d755a; border-radius: 12px; }"
            )
        else:
            self.setStyleSheet(
                "QFrame#AssistantModelBubble { background: #171d27; border: 1px solid #303949; border-radius: 12px; }"
            )


class AssistantPage(QWidget):
    QUICK_PROMPTS = (
        "¿Qué grises oscuros tengo en el inventario?",
        "Busca una alternativa para esta pintura",
        "Añade una pintura a futuras compras",
        "Quiero pintar un Stormtrooper con desgaste",
    )

    IMAGE_FILTER = "Imágenes (*.png *.jpg *.jpeg *.webp *.bmp)"

    def __init__(self, gemini_service_factory: Callable | None = None):
        super().__init__()
        self.session_store = AssistantSessionStore()
        self.current_conversation_id: str | None = None
        self.attached_image_path: str | None = None
        self._message_widgets: list[QWidget] = []
        self._active_tasks: set[object] = set()
        self._busy = False
        self._gemini_service_factory = gemini_service_factory
        self._thread_pool = QThreadPool.globalInstance()
        self._build_ui()
        self.new_conversation()

    @property
    def busy(self) -> bool:
        return self._busy

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(16)
        root.addWidget(self._build_conversation_sidebar())
        root.addWidget(self._build_chat_area(), 1)

    def _build_conversation_sidebar(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("AssistantConversationPanel")
        panel.setFixedWidth(238)
        panel.setStyleSheet(
            "QFrame#AssistantConversationPanel { background: #111722; border: 1px solid #273142; border-radius: 12px; }"
        )
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("Conversaciones")
        title.setStyleSheet("font-size: 11pt; font-weight: 700; color: #f8fafc;")
        subtitle = QLabel("Temporales · no se guardan al cerrar")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #8491a5; font-size: 8.5pt;")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        new_button = QPushButton("+ Nueva conversación")
        new_button.setObjectName("PrimaryButton")
        new_button.clicked.connect(self.new_conversation)
        layout.addWidget(new_button)

        self.conversation_list = QListWidget()
        self.conversation_list.setObjectName("AssistantConversationList")
        self.conversation_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.conversation_list.currentItemChanged.connect(self._conversation_selected)
        self.conversation_list.setStyleSheet(
            "QListWidget#AssistantConversationList { background: #0d131d; color: #dce5f1; "
            "border: 1px solid #273142; border-radius: 8px; padding: 4px; }"
            "QListWidget#AssistantConversationList::item { padding: 9px 8px; border-radius: 6px; }"
            "QListWidget#AssistantConversationList::item:selected { background: #213349; color: white; }"
        )
        layout.addWidget(self.conversation_list, 1)

        delete_button = QPushButton("Eliminar conversación")
        delete_button.setObjectName("DangerCompactButton")
        delete_button.clicked.connect(self.delete_current_conversation)
        layout.addWidget(delete_button)

        info_row = QHBoxLayout()
        info_row.addStretch()
        self.info_button = QPushButton("ⓘ")
        self.info_button.setToolTip("Información sobre Ciros Assistant")
        self.info_button.setFixedSize(36, 36)
        self.info_button.setCursor(Qt.PointingHandCursor)
        self.info_button.setStyleSheet(
            "QPushButton { background: #16202d; color: #b8c7da; border: 1px solid #334155; "
            "border-radius: 18px; font-size: 15pt; font-weight: 700; padding: 0; }"
            "QPushButton:hover { background: #1e2c3d; color: #ffffff; border-color: #4b647f; }"
        )
        self.info_button.clicked.connect(self.show_assistant_info)
        info_row.addWidget(self.info_button)
        layout.addLayout(info_row)
        return panel

    def _build_chat_area(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        header = QVBoxLayout()
        title = QLabel("Ciros Assistant")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Asistente especializado en pintura de miniaturas y modelismo")
        subtitle.setObjectName("Muted")
        header.addWidget(title)
        header.addWidget(subtitle)
        layout.addLayout(header)

        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setFrameShape(QFrame.NoFrame)
        self.chat_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.chat_content = QWidget()
        self.messages_layout = QVBoxLayout(self.chat_content)
        self.messages_layout.setContentsMargins(8, 12, 8, 12)
        self.messages_layout.setSpacing(10)

        self.welcome_card = self._build_welcome_card()
        self.messages_layout.addWidget(self.welcome_card, 0, Qt.AlignHCenter)
        self.messages_layout.addStretch()

        self.chat_scroll.setWidget(self.chat_content)
        layout.addWidget(self.chat_scroll, 1)
        layout.addWidget(self._build_composer())
        return panel

    def _build_welcome_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("AssistantWelcomeCard")
        card.setMaximumWidth(780)
        card.setStyleSheet(
            "QFrame#AssistantWelcomeCard { background: #121925; border: 1px solid #2c384b; border-radius: 14px; }"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(10)

        title = QLabel("¿En qué te ayudo con tu hobby?")
        title.setStyleSheet("font-size: 15pt; font-weight: 700; color: #f8fafc;")
        body = QLabel(
            "El asistente está especializado en pintura de miniaturas, modelismo, dioramas, escenografía, aerografía y técnicas del hobby. "
            "Cuando consulte tu colección, la base de datos local de Ciros Paint será la fuente de verdad."
        )
        body.setWordWrap(True)
        body.setStyleSheet("color: #a9b6c8; line-height: 1.35;")
        layout.addWidget(title)
        layout.addWidget(body)

        quick_title = QLabel("Prueba con una consulta")
        quick_title.setStyleSheet("font-weight: 700; color: #dce5f1;")
        layout.addWidget(quick_title)

        for prompt in self.QUICK_PROMPTS:
            button = QPushButton(prompt)
            button.setObjectName("SecondaryButton")
            button.setStyleSheet("text-align: left; padding: 8px 10px;")
            button.clicked.connect(lambda _checked=False, value=prompt: self._use_quick_prompt(value))
            layout.addWidget(button)

        note = QLabel("Las conversaciones son temporales y no generan memoria persistente entre sesiones.")
        note.setWordWrap(True)
        note.setStyleSheet("color: #75859b; font-size: 8.5pt;")
        layout.addWidget(note)
        return card

    def _build_composer(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("AssistantComposer")
        frame.setStyleSheet(
            "QFrame#AssistantComposer { background: #111722; border: 1px solid #2c384b; border-radius: 12px; }"
        )
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        attachment_row = QHBoxLayout()
        self.attachment_label = QLabel("")
        self.attachment_label.setVisible(False)
        self.attachment_label.setStyleSheet(
            "background: #1d2a3a; color: #c8d6e8; border: 1px solid #344a63; border-radius: 8px; padding: 5px 8px;"
        )
        self.remove_attachment_button = QPushButton("×")
        self.remove_attachment_button.setFixedWidth(28)
        self.remove_attachment_button.setVisible(False)
        self.remove_attachment_button.clicked.connect(self.clear_attachment)
        attachment_row.addWidget(self.attachment_label)
        attachment_row.addWidget(self.remove_attachment_button)
        attachment_row.addStretch()
        layout.addLayout(attachment_row)

        self.input = QPlainTextEdit()
        self.input.setObjectName("AssistantInput")
        self.input.setPlaceholderText("Pregunta sobre pinturas, técnicas, inventario o adjunta una imagen de una pintura…")
        self.input.setFixedHeight(78)
        self.input.setStyleSheet(
            "QPlainTextEdit#AssistantInput { background: transparent; color: #f1f5f9; border: none; font-size: 10pt; padding: 2px; }"
        )
        layout.addWidget(self.input)

        actions = QHBoxLayout()
        self.attach_button = QPushButton("📎 Adjuntar imagen")
        self.attach_button.setObjectName("SecondaryButton")
        self.attach_button.setToolTip("Adjuntar una imagen a la conversación")
        self.attach_button.clicked.connect(self.attach_image)
        actions.addWidget(self.attach_button)

        self.request_status = QLabel("")
        self.request_status.setObjectName("Muted")
        self.request_status.setStyleSheet("color: #93a4bb; font-size: 8.5pt;")
        actions.addWidget(self.request_status)
        actions.addStretch()

        self.send_button = QPushButton("Enviar")
        self.send_button.setObjectName("PrimaryButton")
        self.send_button.clicked.connect(self.send_message)
        actions.addWidget(self.send_button)
        layout.addLayout(actions)
        return frame

    def show_assistant_info(self):
        AssistantInfoDialog(self).exec()

    def new_conversation(self):
        conversation = self.session_store.create()
        item = QListWidgetItem(conversation.title)
        item.setData(Qt.UserRole, conversation.id)
        self.conversation_list.addItem(item)
        self.conversation_list.setCurrentItem(item)

    def delete_current_conversation(self):
        item = self.conversation_list.currentItem()
        if item is None:
            return
        conversation_id = item.data(Qt.UserRole)
        self.session_store.delete(conversation_id)
        row = self.conversation_list.row(item)
        self.conversation_list.takeItem(row)
        if self.conversation_list.count() == 0:
            self.new_conversation()
        else:
            self.conversation_list.setCurrentRow(max(0, row - 1))

    def _conversation_selected(self, current, previous):
        if current is None:
            self.current_conversation_id = None
            self._render_messages([])
            return
        self.current_conversation_id = current.data(Qt.UserRole)
        conversation = self.session_store.get(self.current_conversation_id)
        self._render_messages(conversation.messages if conversation else [])

    def _clear_message_bubbles(self):
        for widget in self._message_widgets:
            self.messages_layout.removeWidget(widget)
            widget.deleteLater()
        self._message_widgets.clear()

    def _render_messages(self, messages):
        self._clear_message_bubbles()
        self.welcome_card.setVisible(not messages)
        for message in messages:
            bubble = AssistantMessageBubble(message.role, message.content, self.chat_content)
            alignment = Qt.AlignRight if message.role == "user" else Qt.AlignLeft
            self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble, 0, alignment)
            self._message_widgets.append(bubble)
        self._scroll_to_bottom()

    def _append_message_bubble(self, role: str, content: str):
        self.welcome_card.setVisible(False)
        bubble = AssistantMessageBubble(role, content, self.chat_content)
        alignment = Qt.AlignRight if role == "user" else Qt.AlignLeft
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble, 0, alignment)
        self._message_widgets.append(bubble)
        self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        bar = self.chat_scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _use_quick_prompt(self, prompt: str):
        self.input.setPlainText(prompt)
        self.input.setFocus()

    def attach_image(self):
        if self._busy:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Adjuntar imagen", "", self.IMAGE_FILTER)
        if not path:
            return
        self.attached_image_path = path
        self.attachment_label.setText(f"📷 {Path(path).name}")
        self.attachment_label.setToolTip(path)
        self.attachment_label.setVisible(True)
        self.remove_attachment_button.setVisible(True)

    def clear_attachment(self):
        if self._busy:
            return
        self.attached_image_path = None
        self.attachment_label.clear()
        self.attachment_label.setVisible(False)
        self.remove_attachment_button.setVisible(False)

    def send_message(self):
        if self._busy:
            return
        text = self.input.toPlainText().strip()
        image_path = self.attached_image_path
        if not text and not image_path:
            return

        api_key = AssistantSettingsStore.gemini_api_key()
        if not api_key:
            self.request_status.setText("Configura primero Gemini API en Ajustes.")
            return

        if self.current_conversation_id is None:
            self.new_conversation()
        conversation = self.session_store.get(self.current_conversation_id)
        if conversation is None:
            return
        conversation_id = conversation.id

        visible_parts = []
        if text:
            visible_parts.append(text)
        if image_path:
            visible_parts.append(f"[Imagen adjunta: {Path(image_path).name}]")
        visible_content = "\n".join(visible_parts)

        self.session_store.add_message(conversation_id, "user", visible_content)
        self._append_message_bubble("user", visible_content)
        self._rename_current_conversation(text or "Imagen de pintura")
        self.input.clear()
        self.attached_image_path = None
        self.attachment_label.clear()
        self.attachment_label.setVisible(False)
        self.remove_attachment_button.setVisible(False)
        self._set_busy(True, "Gemini está pensando…")

        task = AssistantRequestTask(
            conversation_id=conversation_id,
            api_key=api_key,
            provider_history=list(conversation.provider_history),
            user_text=text,
            image_path=image_path,
            service_factory=self._gemini_service_factory,
        )
        self._active_tasks.add(task)
        task.signals.success.connect(self._assistant_finished)
        task.signals.failure.connect(self._assistant_failed)
        task.signals.finished.connect(lambda task=task: self._release_task(task))
        self._thread_pool.start(task)

    def _assistant_finished(self, conversation_id: str, answer: str, provider_history, tool_events):
        conversation = self.session_store.get(conversation_id)
        if conversation is not None:
            conversation.provider_history = list(provider_history or [])
            self.session_store.add_message(conversation_id, "assistant", answer)
            if self.current_conversation_id == conversation_id:
                self._append_message_bubble("assistant", answer)
        self._set_busy(False, "")

    def _assistant_failed(self, conversation_id: str, code: str, message: str):
        error_text = f"⚠ {message}"
        conversation = self.session_store.get(conversation_id)
        if conversation is not None:
            self.session_store.add_message(conversation_id, "assistant", error_text)
            if self.current_conversation_id == conversation_id:
                self._append_message_bubble("assistant", error_text)
        self._set_busy(False, "")

    def _release_task(self, task):
        self._active_tasks.discard(task)

    def _set_busy(self, busy: bool, message: str):
        self._busy = bool(busy)
        self.input.setEnabled(not busy)
        self.attach_button.setEnabled(not busy)
        self.send_button.setEnabled(not busy)
        self.remove_attachment_button.setEnabled(not busy)
        self.request_status.setText(message)
        self.send_button.setText("Enviando…" if busy else "Enviar")

    def _rename_current_conversation(self, text: str):
        item = self.conversation_list.currentItem()
        if item is None:
            return
        title = " ".join(str(text or "").split())[:42] or "Nueva conversación"
        item.setText(title)
        conversation = self.session_store.get(self.current_conversation_id)
        if conversation is not None:
            conversation.title = title
