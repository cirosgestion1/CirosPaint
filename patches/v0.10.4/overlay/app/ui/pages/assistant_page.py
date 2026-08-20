from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.services.assistant_session_store import AssistantSessionStore
from app.services.assistant_settings_store import AssistantSettingsStore


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
                "QFrame#AssistantUserBubble { background: #2d5a45; border: 1px solid #3d755a; "
                "border-radius: 12px; }"
            )
        else:
            self.setStyleSheet(
                "QFrame#AssistantModelBubble { background: #171d27; border: 1px solid #303949; "
                "border-radius: 12px; }"
            )


class AssistantPage(QWidget):
    """Visual shell for the Ciros Paint assistant.

    0.10.4 intentionally provides the complete desktop UI and local visual
    state without making network calls to Gemini. The provider integration is
    kept separate from this page so it can be added without redesigning the UI.
    """

    QUICK_PROMPTS = (
        "¿Qué grises oscuros tengo en el inventario?",
        "Busca una alternativa para esta pintura",
        "Añade una pintura a futuras compras",
        "Quiero pintar un Stormtrooper con desgaste",
    )

    IMAGE_FILTER = "Imágenes (*.png *.jpg *.jpeg *.webp *.bmp)"

    def __init__(self):
        super().__init__()
        self.session_store = AssistantSessionStore()
        self.current_conversation_id: str | None = None
        self.attached_image_path: str | None = None
        self._build_ui()
        self._load_saved_key_state()
        self.new_conversation()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(16)

        root.addWidget(self._build_conversation_sidebar())
        root.addWidget(self._build_chat_area(), 1)

    def _build_conversation_sidebar(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("Card")
        panel.setFixedWidth(238)
        panel.setStyleSheet(
            "QFrame#Card { background: #111722; border: 1px solid #273142; border-radius: 12px; }"
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

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("color: #273142;")
        layout.addWidget(separator)

        capabilities_title = QLabel("Puede trabajar con")
        capabilities_title.setStyleSheet("font-weight: 700; color: #dce5f1;")
        layout.addWidget(capabilities_title)
        for text in (
            "Inventario de pinturas",
            "Stock y cantidades",
            "Alternativas por color",
            "Futuras compras",
            "Imágenes de pinturas",
        ):
            item = QLabel(f"• {text}")
            item.setStyleSheet("color: #8fa0b7; font-size: 8.5pt;")
            layout.addWidget(item)

        return panel

    def _build_chat_area(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header_text = QVBoxLayout()
        title = QLabel("Ciros Assistant")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Asistente especializado en pintura de miniaturas y modelismo")
        subtitle.setObjectName("Muted")
        header_text.addWidget(title)
        header_text.addWidget(subtitle)
        header.addLayout(header_text)
        header.addStretch()

        self.connection_badge = QLabel("Gemini · Sin configurar")
        self.connection_badge.setAlignment(Qt.AlignCenter)
        self.connection_badge.setStyleSheet(
            "background: #2a2114; color: #f5c978; border: 1px solid #5d4825; "
            "border-radius: 10px; padding: 6px 10px; font-weight: 600;"
        )
        header.addWidget(self.connection_badge)

        self.settings_button = QPushButton("⚙ Configurar Gemini")
        self.settings_button.setObjectName("SecondaryButton")
        self.settings_button.clicked.connect(self.toggle_settings_panel)
        header.addWidget(self.settings_button)
        layout.addLayout(header)

        self.settings_panel = self._build_settings_panel()
        self.settings_panel.setVisible(False)
        layout.addWidget(self.settings_panel)

        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setFrameShape(QFrame.NoFrame)
        self.chat_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.chat_content = QWidget()
        self.messages_layout = QVBoxLayout(self.chat_content)
        self.messages_layout.setContentsMargins(8, 12, 8, 12)
        self.messages_layout.setSpacing(10)
        self.messages_layout.addStretch()
        self.chat_scroll.setWidget(self.chat_content)
        layout.addWidget(self.chat_scroll, 1)

        self.welcome_card = self._build_welcome_card()
        self.messages_layout.insertWidget(0, self.welcome_card)

        layout.addWidget(self._build_composer())
        return panel

    def _build_settings_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("AssistantSettingsPanel")
        panel.setStyleSheet(
            "QFrame#AssistantSettingsPanel { background: #121a26; border: 1px solid #2b3a4f; "
            "border-radius: 10px; }"
        )
        root = QVBoxLayout(panel)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(8)

        title = QLabel("Configuración de inteligencia artificial")
        title.setStyleSheet("font-weight: 700; color: #f1f5f9;")
        description = QLabel(
            "La clave de Gemini se guarda únicamente en este ordenador, fuera del ejecutable y del repositorio GitHub."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #93a4bb;")
        root.addWidget(title)
        root.addWidget(description)

        key_row = QHBoxLayout()
        self.api_key_input = QLineEdit()
        self.api_key_input.setObjectName("GeminiApiKeyInput")
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("Pega aquí tu API Key de Gemini")
        key_row.addWidget(self.api_key_input, 1)

        self.show_key_button = QPushButton("Mostrar")
        self.show_key_button.setObjectName("SecondaryButton")
        self.show_key_button.clicked.connect(self.toggle_api_key_visibility)
        key_row.addWidget(self.show_key_button)
        root.addLayout(key_row)

        actions = QHBoxLayout()
        save = QPushButton("Guardar clave")
        save.setObjectName("PrimaryButton")
        save.clicked.connect(self.save_api_key)
        test = QPushButton("Comprobar conexión")
        test.setObjectName("SecondaryButton")
        test.clicked.connect(self.preview_connection_check)
        remove = QPushButton("Eliminar clave")
        remove.setObjectName("DangerCompactButton")
        remove.clicked.connect(self.remove_api_key)
        actions.addWidget(save)
        actions.addWidget(test)
        actions.addWidget(remove)
        actions.addStretch()
        root.addLayout(actions)

        self.settings_status = QLabel("")
        self.settings_status.setWordWrap(True)
        self.settings_status.setStyleSheet("color: #8fa0b7; font-size: 8.5pt;")
        root.addWidget(self.settings_status)
        return panel

    def _build_welcome_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("AssistantWelcomeCard")
        card.setMaximumWidth(780)
        card.setStyleSheet(
            "QFrame#AssistantWelcomeCard { background: #121925; border: 1px solid #2c384b; "
            "border-radius: 14px; }"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(10)

        title = QLabel("¿En qué te ayudo con tu hobby?")
        title.setStyleSheet("font-size: 15pt; font-weight: 700; color: #f8fafc;")
        body = QLabel(
            "El asistente está limitado a pintura de miniaturas, modelismo, dioramas, escenografía, aerografía y técnicas del hobby. "
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

        self.attachment_row = QHBoxLayout()
        self.attachment_label = QLabel("")
        self.attachment_label.setVisible(False)
        self.attachment_label.setStyleSheet(
            "background: #1d2a3a; color: #c8d6e8; border: 1px solid #344a63; "
            "border-radius: 8px; padding: 5px 8px;"
        )
        self.remove_attachment_button = QPushButton("×")
        self.remove_attachment_button.setFixedWidth(28)
        self.remove_attachment_button.setVisible(False)
        self.remove_attachment_button.clicked.connect(self.clear_attachment)
        self.attachment_row.addWidget(self.attachment_label)
        self.attachment_row.addWidget(self.remove_attachment_button)
        self.attachment_row.addStretch()
        layout.addLayout(self.attachment_row)

        self.input = QPlainTextEdit()
        self.input.setObjectName("AssistantInput")
        self.input.setPlaceholderText("Pregunta sobre pinturas, técnicas, inventario o adjunta una imagen de una pintura…")
        self.input.setFixedHeight(78)
        self.input.setStyleSheet(
            "QPlainTextEdit#AssistantInput { background: transparent; color: #f1f5f9; border: none; "
            "font-size: 10pt; padding: 2px; }"
        )
        layout.addWidget(self.input)

        actions = QHBoxLayout()
        attach = QPushButton("📎 Adjuntar imagen")
        attach.setObjectName("SecondaryButton")
        attach.setToolTip("El análisis visual se limitará exclusivamente a pinturas de modelismo")
        attach.clicked.connect(self.attach_image)
        actions.addWidget(attach)

        hint = QLabel("Imágenes: solo pinturas de modelismo")
        hint.setStyleSheet("color: #75859b; font-size: 8.5pt;")
        actions.addWidget(hint)
        actions.addStretch()

        send = QPushButton("Enviar")
        send.setObjectName("PrimaryButton")
        send.clicked.connect(self.send_message)
        actions.addWidget(send)
        layout.addLayout(actions)
        return frame

    def _load_saved_key_state(self):
        api_key = AssistantSettingsStore.gemini_api_key()
        if api_key:
            self.api_key_input.setText(api_key)
            self._set_key_badge(True)
            self.settings_status.setText("Clave guardada localmente. La conexión real con Gemini todavía no se ejecuta en 0.10.4.")
        else:
            self._set_key_badge(False)
            self.settings_status.setText("Añade una clave para dejar preparada la integración de Gemini.")

    def _set_key_badge(self, configured: bool):
        if configured:
            self.connection_badge.setText("Gemini · Clave guardada")
            self.connection_badge.setStyleSheet(
                "background: #173026; color: #8de0b1; border: 1px solid #2d6048; "
                "border-radius: 10px; padding: 6px 10px; font-weight: 600;"
            )
        else:
            self.connection_badge.setText("Gemini · Sin configurar")
            self.connection_badge.setStyleSheet(
                "background: #2a2114; color: #f5c978; border: 1px solid #5d4825; "
                "border-radius: 10px; padding: 6px 10px; font-weight: 600;"
            )

    def toggle_settings_panel(self):
        self.settings_panel.setVisible(not self.settings_panel.isVisible())

    def toggle_api_key_visibility(self):
        if self.api_key_input.echoMode() == QLineEdit.Password:
            self.api_key_input.setEchoMode(QLineEdit.Normal)
            self.show_key_button.setText("Ocultar")
        else:
            self.api_key_input.setEchoMode(QLineEdit.Password)
            self.show_key_button.setText("Mostrar")

    def save_api_key(self):
        key = self.api_key_input.text().strip()
        if not key:
            self.settings_status.setText("No hay ninguna clave que guardar.")
            self._set_key_badge(False)
            return
        AssistantSettingsStore.set_gemini_api_key(key)
        self._set_key_badge(True)
        self.settings_status.setText("Clave guardada localmente. No se ha enviado a ningún servicio externo.")

    def remove_api_key(self):
        AssistantSettingsStore.clear_gemini_api_key()
        self.api_key_input.clear()
        self._set_key_badge(False)
        self.settings_status.setText("Clave eliminada de este ordenador.")

    def preview_connection_check(self):
        if not self.api_key_input.text().strip():
            QMessageBox.information(self, "Gemini", "Primero introduce una API Key de Gemini.")
            return
        QMessageBox.information(
            self,
            "Gemini",
            "La interfaz de comprobación está preparada. La llamada real a Gemini se conectará en la siguiente implementación.",
        )

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

    def _render_messages(self, messages):
        while self.messages_layout.count() > 1:
            item = self.messages_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.welcome_card.setVisible(not messages)
        if not messages:
            self.messages_layout.insertWidget(0, self.welcome_card, 0, Qt.AlignHCenter)
            return
        self.welcome_card.setParent(self.chat_content)
        self.welcome_card.setVisible(False)
        for message in messages:
            bubble = AssistantMessageBubble(message.role, message.content, self.chat_content)
            alignment = Qt.AlignRight if message.role == "user" else Qt.AlignLeft
            self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble, 0, alignment)
        self._scroll_to_bottom()

    def _append_message_bubble(self, role: str, content: str):
        self.welcome_card.setVisible(False)
        bubble = AssistantMessageBubble(role, content, self.chat_content)
        alignment = Qt.AlignRight if role == "user" else Qt.AlignLeft
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble, 0, alignment)
        self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        bar = self.chat_scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _use_quick_prompt(self, prompt: str):
        self.input.setPlainText(prompt)
        self.input.setFocus()

    def attach_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Adjuntar imagen de una pintura", "", self.IMAGE_FILTER)
        if not path:
            return
        self.attached_image_path = path
        self.attachment_label.setText(f"📷 {Path(path).name}")
        self.attachment_label.setToolTip(path)
        self.attachment_label.setVisible(True)
        self.remove_attachment_button.setVisible(True)

    def clear_attachment(self):
        self.attached_image_path = None
        self.attachment_label.clear()
        self.attachment_label.setVisible(False)
        self.remove_attachment_button.setVisible(False)

    def send_message(self):
        text = self.input.toPlainText().strip()
        if not text and not self.attached_image_path:
            return
        if self.current_conversation_id is None:
            self.new_conversation()

        parts = []
        if text:
            parts.append(text)
        if self.attached_image_path:
            parts.append(f"[Imagen adjunta: {Path(self.attached_image_path).name}]")
        content = "\n".join(parts)

        self.session_store.add_message(self.current_conversation_id, "user", content)
        self._append_message_bubble("user", content)
        self._rename_current_conversation(text or "Imagen de pintura")
        self.input.clear()
        self.clear_attachment()

        placeholder = (
            "La interfaz del asistente ya está preparada en Ciros Paint 0.10.4. "
            "La respuesta real de Gemini y la ejecución automática de herramientas se conectarán en la siguiente capa de integración."
        )
        self.session_store.add_message(self.current_conversation_id, "assistant", placeholder)
        self._append_message_bubble("assistant", placeholder)

    def _rename_current_conversation(self, text: str):
        item = self.conversation_list.currentItem()
        if item is None:
            return
        title = " ".join(str(text or "").split())[:42] or "Nueva conversación"
        item.setText(title)
        conversation = self.session_store.get(self.current_conversation_id)
        if conversation is not None:
            conversation.title = title
