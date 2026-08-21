from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QSize, Qt, QThreadPool, Signal
from PySide6.QtGui import QPixmap, QTextDocument
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.db.database import get_session
from app.services.assistant_async_tasks import AssistantRequestTask, MiniatureResolveTask, PaintResolveTask
from app.services.assistant_local_service import AssistantLocalService, LocalAssistantResult
from app.services.assistant_conversation_context import PaintConversationContext
from app.services.assistant_session_store import AssistantSessionStore
from app.services.assistant_settings_store import AssistantSettingsStore
from app.services.assistant_workflow_service import AssistantWorkflowEngine
from app.ui.dialogs.assistant_info_dialog import AssistantInfoDialog


class AutocompleteDialog(QDialog):
    def __init__(self, title: str, label: str, options: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(460)
        layout = QVBoxLayout(self)
        prompt = QLabel(label)
        prompt.setWordWrap(True)
        layout.addWidget(prompt)
        self.input = QLineEdit()
        self.input.setPlaceholderText("Empieza a escribir…")
        completer = QCompleter(sorted(set(options), key=str.casefold), self)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        self.input.setCompleter(completer)
        layout.addWidget(self.input)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.input.returnPressed.connect(self.accept)
        self.input.setFocus()

    @classmethod
    def get_value(cls, title: str, label: str, options: list[str], parent=None) -> str | None:
        dialog = cls(title, label, options, parent)
        if dialog.exec() != QDialog.Accepted:
            return None
        value = dialog.input.text().strip()
        return value or None


class WrappingRichLabel(QLabel):
    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        document = QTextDocument()
        document.setDefaultFont(self.font())
        document.setHtml(self.text())
        document.setTextWidth(max(1, width))
        return int(document.size().height()) + 2

    def minimumSizeHint(self) -> QSize:
        return QSize(1, self.heightForWidth(max(1, self.width())))


class QuantityDialog(QDialog):
    """Validated quantity chooser with reliable native spin controls."""

    def __init__(self, title: str, label: str, value: int, minimum: int, maximum: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        layout = QVBoxLayout(self)
        prompt = QLabel(label); prompt.setWordWrap(True); layout.addWidget(prompt)
        self.spin = QSpinBox(self)
        self.spin.setRange(int(minimum), int(maximum)); self.spin.setValue(int(value)); self.spin.setSingleStep(1)
        self.spin.setKeyboardTracking(False); self.spin.setMinimumWidth(150)
        self.spin.setStyleSheet(
            "QSpinBox { padding: 7px 28px 7px 7px; }"
            "QSpinBox::up-button, QSpinBox::down-button { width: 24px; border-left: 1px solid #303949; }"
        )
        layout.addWidget(self.spin)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); layout.addWidget(buttons)

    @classmethod
    def get_value(cls, title: str, label: str, value: int, minimum: int, maximum: int, parent=None):
        dialog = cls(title, label, value, minimum, maximum, parent)
        return (dialog.spin.value(), True) if dialog.exec() == QDialog.Accepted else (value, False)


class AssistantMessageBubble(QFrame):
    action_requested = Signal(str)

    def __init__(
        self,
        role: str,
        content: str,
        parent=None,
        *,
        image_path: str | None = None,
        metadata: dict | None = None,
    ):
        super().__init__(parent)
        self.role = role
        self.metadata = dict(metadata or {})
        self.setObjectName("AssistantUserBubble" if role == "user" else "AssistantModelBubble")
        self.setMaximumWidth(800)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 11, 14, 11)
        layout.setSpacing(8)

        if image_path:
            thumbnail = QLabel()
            pixmap = QPixmap(str(image_path))
            if not pixmap.isNull():
                thumbnail.setPixmap(pixmap.scaled(220, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                thumbnail.setToolTip(str(image_path))
                layout.addWidget(thumbnail, 0, Qt.AlignLeft)
                filename = QLabel(Path(image_path).name)
                filename.setStyleSheet("color: #a7b6c8; font-size: 8pt; background: transparent;")
                layout.addWidget(filename)

        if content:
            self.text_label = WrappingRichLabel()
            self.text_label.setWordWrap(True)
            self.text_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            self.text_label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
            self.text_label.setOpenExternalLinks(True)
            self.text_label.setTextFormat(Qt.RichText)
            self.text_label.setStyleSheet("color: #f1f5f9; font-size: 10pt; background: transparent; border: none;")
            document = QTextDocument()
            document.setDefaultStyleSheet(
                "body { color: #f1f5f9; font-family: 'Segoe UI'; font-size: 10pt; }"
                "p { margin: 0 0 5px 0; } ul, ol { margin-top: 3px; margin-bottom: 3px; }"
                "code { font-family: Consolas; }"
            )
            document.setMarkdown(content)
            self.text_label.setText(document.toHtml())
            layout.addWidget(self.text_label)
        else:
            self.text_label = QLabel("")

        self._add_structured_content(layout, self.metadata)
        self._add_actions(layout, self.metadata)

        if role == "user":
            self.setStyleSheet(
                "QFrame#AssistantUserBubble { background: #28553f; border: 1px solid #3f765c; border-radius: 13px; }"
            )
        else:
            self.setStyleSheet(
                "QFrame#AssistantModelBubble { background: #151c26; border: 1px solid #303b4b; border-radius: 13px; }"
            )

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        current_layout = self.layout()
        if current_layout is not None and current_layout.hasHeightForWidth():
            return current_layout.heightForWidth(width)
        return self.sizeHint().height()

    def set_available_width(self, available_width: int) -> None:
        """Give Qt a concrete width before deriving wrapped content height."""
        width = max(220, min(800, int(available_width * 0.92)))
        self.setFixedWidth(width)
        margins = self.layout().contentsMargins()
        content_width = max(1, width - margins.left() - margins.right())
        if isinstance(self.text_label, WrappingRichLabel):
            self.text_label.setFixedWidth(content_width)
            self.text_label.setMinimumHeight(self.text_label.heightForWidth(content_width))
        self.layout().activate()
        required_height = max(self.layout().sizeHint().height(), self.heightForWidth(width))
        self.setMinimumHeight(required_height)
        self.resize(width, required_height)

    def _add_structured_content(self, layout: QVBoxLayout, metadata: dict):
        kind = metadata.get("kind")
        data = metadata.get("data") or {}
        if kind == "paints":
            for paint in data.get("paints") or []:
                row = QFrame()
                row.setStyleSheet("QFrame { background: transparent; border: none; }")
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(2, 2, 2, 2)
                swatch = QLabel()
                swatch.setFixedSize(20, 20)
                color = str(paint.get("swatch_hex") or "#64748b")
                if not color.startswith("#"):
                    color = "#64748b"
                swatch.setStyleSheet(f"background: {color}; border: 1px solid #94a3b8; border-radius: 10px;")
                row_layout.addWidget(swatch)
                name = " ".join(part for part in (str(paint.get("brand") or ""), str(paint.get("name") or "")) if part).strip()
                detail = QLabel(name or "Pintura")
                detail.setWordWrap(True)
                detail.setStyleSheet("background: transparent; border: none; color: #e8eef7; font-weight: 600;")
                row_layout.addWidget(detail, 1)
                total = int(paint.get("total_units") or 0)
                available = int(paint.get("available_units") or 0)
                low = int(paint.get("low_units") or 0)
                if total == 0:
                    amount = "Agotada"
                elif available == 0 and low > 0:
                    amount = f"{total} · casi agotada"
                else:
                    amount = f"{total} ud."
                qty = QLabel(amount)
                qty.setWordWrap(True)
                qty.setStyleSheet("background: transparent; border: none; color: #a9cbb9;")
                row_layout.addWidget(qty)
                layout.addWidget(row)
        elif kind == "miniature_counts":
            counts = data.get("counts") or {}
            grid = QGridLayout()
            for index, status in enumerate(("Sin montar", "Montado", "Pintado", "Terminado")):
                label = QLabel(f"{status}: **{int(counts.get(status, 0) or 0)}**")
                doc = QTextDocument(); doc.setMarkdown(label.text()); label.setText(doc.toHtml()); label.setTextFormat(Qt.RichText)
                label.setStyleSheet("background: transparent; border: none; color: #dbe7f3;")
                grid.addWidget(label, index // 2, index % 2)
            layout.addLayout(grid)
        elif kind == "miniature_list":
            for item in data.get("items") or []:
                unit = item.get("unit") or {}
                counts = item.get("counts") or {}
                text = QLabel(
                    f"• {unit.get('unit_name', 'Miniatura')} — "
                    f"sin montar {counts.get('Sin montar', 0)}, montadas {counts.get('Montado', 0)}, "
                    f"pintadas {counts.get('Pintado', 0)}, terminadas {counts.get('Terminado', 0)}"
                )
                text.setWordWrap(True)
                text.setStyleSheet("background: transparent; border: none; color: #d7e2ef;")
                layout.addWidget(text)
        elif kind == "miniature_matches":
            for match in data.get("matches") or []:
                text = QLabel(f"• {match.get('unit_name', '')}")
                text.setStyleSheet("background: transparent; border: none; color: #d7e2ef;")
                layout.addWidget(text)

    def _add_actions(self, layout: QVBoxLayout, metadata: dict):
        data = metadata.get("data") or {}
        actions = data.get("actions") or []
        if not actions:
            return
        row = QHBoxLayout()
        for action in actions:
            label = str(action.get("label") or "").strip()
            action_id = str(action.get("action") or "").strip()
            if not label or not action_id:
                continue
            button = QPushButton(label)
            button.setObjectName("SecondaryButton")
            button.clicked.connect(lambda _checked=False, value=action_id: self.action_requested.emit(value))
            row.addWidget(button)
        row.addStretch()
        layout.addLayout(row)


class AssistantPage(QWidget):
    IMAGE_FILTER = "Imágenes (*.png *.jpg *.jpeg *.webp *.bmp)"

    PAINT_ACTIONS = (
        ("¿Tengo esta pintura?", "paint_find"),
        ("Pinturas de un color", "paint_color"),
        ("Agotadas / casi agotadas", "paint_depleted"),
        ("Añadir a futuras compras", "paint_future"),
        ("Marcar pintura como comprada", "paint_purchased"),
    )
    MINIATURE_ACTIONS = (
        ("¿Cuántas tengo de esta unidad?", "mini_count"),
        ("Miniaturas no terminadas", "mini_not_finished"),
        ("Miniaturas terminadas", "mini_finished"),
        ("Cambiar estado", "mini_status"),
        ("Añadir miniaturas", "mini_add"),
    )

    def __init__(self, gemini_service_factory: Callable | None = None):
        super().__init__()
        self.session_store = AssistantSessionStore()
        self.workflow_engine = AssistantWorkflowEngine()
        self._paint_contexts: dict[str, PaintConversationContext] = {}
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
        panel.setStyleSheet("QFrame#AssistantConversationPanel { background: #111722; border: 1px solid #273142; border-radius: 12px; }")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        title = QLabel("Conversaciones")
        title.setStyleSheet("font-size: 11pt; font-weight: 700; color: #f8fafc;")
        subtitle = QLabel("Temporales · no se guardan al cerrar")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #8491a5; font-size: 8.5pt;")
        layout.addWidget(title); layout.addWidget(subtitle)
        new_button = QPushButton("+ Nueva conversación")
        new_button.setObjectName("PrimaryButton"); new_button.clicked.connect(self.new_conversation)
        layout.addWidget(new_button)
        self.conversation_list = QListWidget()
        self.conversation_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.conversation_list.currentItemChanged.connect(self._conversation_selected)
        self.conversation_list.setStyleSheet(
            "QListWidget { background: #0d131d; color: #dce5f1; border: 1px solid #273142; border-radius: 8px; padding: 4px; }"
            "QListWidget::item { padding: 9px 8px; border-radius: 6px; } QListWidget::item:selected { background: #213349; color: white; }"
        )
        layout.addWidget(self.conversation_list, 1)
        delete_button = QPushButton("Eliminar conversación")
        delete_button.setObjectName("DangerCompactButton"); delete_button.clicked.connect(self.delete_current_conversation)
        layout.addWidget(delete_button)
        info_row = QHBoxLayout(); info_row.addStretch()
        self.info_button = QPushButton("ⓘ")
        self.info_button.setFixedSize(36, 36); self.info_button.setToolTip("Información sobre Ciros Assistant")
        self.info_button.setStyleSheet("QPushButton { background:#16202d;color:#b8c7da;border:1px solid #334155;border-radius:18px;font-size:15pt;font-weight:700; }")
        self.info_button.clicked.connect(self.show_assistant_info); info_row.addWidget(self.info_button)
        layout.addLayout(info_row)
        return panel

    def _build_chat_area(self) -> QWidget:
        panel = QWidget(); layout = QVBoxLayout(panel); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(12)
        title = QLabel("Ciros Assistant"); title.setObjectName("PageTitle")
        subtitle = QLabel("Consultas locales sin IA · Gemini solo cuando aporta valor"); subtitle.setObjectName("Muted")
        layout.addWidget(title); layout.addWidget(subtitle)
        self.chat_scroll = QScrollArea(); self.chat_scroll.setWidgetResizable(True); self.chat_scroll.setFrameShape(QFrame.NoFrame)
        self.chat_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.chat_content = QWidget(); self.messages_layout = QVBoxLayout(self.chat_content)
        self.messages_layout.setContentsMargins(8, 12, 8, 12); self.messages_layout.setSpacing(10)
        self.welcome_card = self._build_welcome_card(); self.messages_layout.addWidget(self.welcome_card, 0, Qt.AlignHCenter); self.messages_layout.addStretch()
        self.chat_scroll.setWidget(self.chat_content); layout.addWidget(self.chat_scroll, 1); layout.addWidget(self._build_composer())
        return panel

    def _build_welcome_card(self) -> QWidget:
        card = QFrame(); card.setObjectName("AssistantWelcomeCard"); card.setMaximumWidth(820)
        card.setStyleSheet("QFrame#AssistantWelcomeCard { background:#121925;border:1px solid #2c384b;border-radius:14px; }")
        layout = QVBoxLayout(card); layout.setContentsMargins(22, 20, 22, 20); layout.setSpacing(10)
        title = QLabel("Acciones rápidas")
        title.setStyleSheet("font-size: 15pt; font-weight: 700; color: #f8fafc;")
        body = QLabel("Estas consultas trabajan directamente con Ciros Paint y no consumen Gemini. La IA queda como respaldo para lenguaje libre o ambigüedades.")
        body.setWordWrap(True); body.setStyleSheet("color:#a9b6c8;")
        layout.addWidget(title); layout.addWidget(body)
        grid = QGridLayout(); grid.setHorizontalSpacing(12); grid.setVerticalSpacing(8)
        paint_title = QLabel("Pinturas"); paint_title.setStyleSheet("font-weight:700;color:#dce5f1;")
        mini_title = QLabel("Miniaturas"); mini_title.setStyleSheet("font-weight:700;color:#dce5f1;")
        grid.addWidget(paint_title, 0, 0); grid.addWidget(mini_title, 0, 1)
        for row, (label, action) in enumerate(self.PAINT_ACTIONS, 1):
            button = QPushButton(label); button.setObjectName("SecondaryButton"); button.setStyleSheet("text-align:left;padding:8px 10px;")
            button.clicked.connect(lambda _checked=False, value=action: self._quick_action(value)); grid.addWidget(button, row, 0)
        for row, (label, action) in enumerate(self.MINIATURE_ACTIONS, 1):
            button = QPushButton(label); button.setObjectName("SecondaryButton"); button.setStyleSheet("text-align:left;padding:8px 10px;")
            button.clicked.connect(lambda _checked=False, value=action: self._quick_action(value)); grid.addWidget(button, row, 1)
        layout.addLayout(grid)
        note = QLabel("También puedes escribir normalmente. Ciros Paint intentará resolver primero la petición de forma local.")
        note.setWordWrap(True); note.setStyleSheet("color:#75859b;font-size:8.5pt;"); layout.addWidget(note)
        return card

    def _build_composer(self) -> QWidget:
        frame = QFrame(); frame.setObjectName("AssistantComposer")
        frame.setStyleSheet("QFrame#AssistantComposer { background:#111722;border:1px solid #2c384b;border-radius:12px; }")
        layout = QVBoxLayout(frame); layout.setContentsMargins(12, 10, 12, 10); layout.setSpacing(8)
        attachment_row = QHBoxLayout()
        self.attachment_label = QLabel(""); self.attachment_label.setVisible(False)
        self.attachment_label.setStyleSheet("background:#1d2a3a;color:#c8d6e8;border:1px solid #344a63;border-radius:8px;padding:5px 8px;")
        self.remove_attachment_button = QPushButton("×"); self.remove_attachment_button.setFixedWidth(28); self.remove_attachment_button.setVisible(False)
        self.remove_attachment_button.clicked.connect(self.clear_attachment)
        attachment_row.addWidget(self.attachment_label); attachment_row.addWidget(self.remove_attachment_button); attachment_row.addStretch(); layout.addLayout(attachment_row)
        self.input = QPlainTextEdit(); self.input.setPlaceholderText("Escribe sobre pinturas o miniaturas…")
        self.input.setFixedHeight(78); self.input.setStyleSheet("QPlainTextEdit { background:transparent;color:#f1f5f9;border:none;font-size:10pt;padding:2px; }")
        layout.addWidget(self.input)
        actions = QHBoxLayout()
        self.attach_button = QPushButton("📎 Adjuntar imagen"); self.attach_button.setObjectName("SecondaryButton"); self.attach_button.clicked.connect(self.attach_image)
        actions.addWidget(self.attach_button)
        self.request_status = QLabel(""); self.request_status.setStyleSheet("color:#93a4bb;font-size:8.5pt;")
        actions.addWidget(self.request_status); actions.addStretch()
        self.send_button = QPushButton("Enviar"); self.send_button.setObjectName("PrimaryButton"); self.send_button.clicked.connect(self.send_message)
        actions.addWidget(self.send_button); layout.addLayout(actions)
        return frame

    def show_assistant_info(self):
        AssistantInfoDialog(self).exec()

    def new_conversation(self):
        conversation = self.session_store.create(); item = QListWidgetItem(conversation.title); item.setData(Qt.UserRole, conversation.id)
        self.conversation_list.addItem(item); self.conversation_list.setCurrentItem(item)

    def delete_current_conversation(self):
        item = self.conversation_list.currentItem()
        if item is None: return
        conversation_id = item.data(Qt.UserRole); self.session_store.delete(conversation_id); self._paint_contexts.pop(str(conversation_id), None); row = self.conversation_list.row(item); self.conversation_list.takeItem(row)
        if self.conversation_list.count() == 0: self.new_conversation()
        else: self.conversation_list.setCurrentRow(max(0, row - 1))

    def _conversation_selected(self, current, previous):
        if current is None:
            self.current_conversation_id = None; self._render_messages([]); return
        self.current_conversation_id = current.data(Qt.UserRole); conversation = self.session_store.get(self.current_conversation_id)
        self._render_messages(conversation.messages if conversation else [])

    def _clear_message_bubbles(self):
        for widget in self._message_widgets:
            self.messages_layout.removeWidget(widget); widget.deleteLater()
        self._message_widgets.clear()

    def _render_messages(self, messages):
        self._clear_message_bubbles(); self.welcome_card.setVisible(not messages)
        for message in messages:
            self._append_message_bubble(message.role, message.content, image_path=message.image_path, metadata=message.metadata, store_widget=True)
        self._scroll_to_bottom()

    def _append_message_bubble(self, role: str, content: str, *, image_path: str | None = None, metadata: dict | None = None, store_widget: bool = True):
        self.welcome_card.setVisible(False)
        bubble = AssistantMessageBubble(role, content, self.chat_content, image_path=image_path, metadata=metadata)
        bubble.action_requested.connect(self._quick_action)
        bubble.set_available_width(self.chat_scroll.viewport().width() - 16)
        alignment = Qt.AlignRight if role == "user" else Qt.AlignLeft
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble, 0, alignment)
        if store_widget: self._message_widgets.append(bubble)
        self._scroll_to_bottom()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "chat_scroll"):
            available = self.chat_scroll.viewport().width() - 16
            for bubble in self._message_widgets:
                if isinstance(bubble, AssistantMessageBubble):
                    bubble.set_available_width(available)

    def _scroll_to_bottom(self):
        bar = self.chat_scroll.verticalScrollBar(); bar.setValue(bar.maximum())

    def attach_image(self):
        if self._busy: return
        path, _ = QFileDialog.getOpenFileName(self, "Adjuntar imagen", "", self.IMAGE_FILTER)
        if not path: return
        self.attached_image_path = path; self.attachment_label.setText(f"📷 {Path(path).name}"); self.attachment_label.setToolTip(path)
        self.attachment_label.setVisible(True); self.remove_attachment_button.setVisible(True)

    def clear_attachment(self):
        if self._busy: return
        self.attached_image_path = None; self.attachment_label.clear(); self.attachment_label.setVisible(False); self.remove_attachment_button.setVisible(False)

    # -------------------------- local quick actions --------------------------
    def _quick_action(self, action: str):
        if self._busy: return
        conversation = self._ensure_conversation()
        with get_session() as session:
            local = self._local_service(session, conversation.id)
            if action == "paint_active_add":
                self._publish_local_request("Añadir otra", local.change_active_paint_quantity("add")); return
            if action == "paint_active_remove":
                self._publish_local_request("Quitar una", local.change_active_paint_quantity("remove")); return
            if action == "paint_active_future":
                self._publish_local_request("Añadirla a futuras compras", local.add_active_paint_to_future()); return
            if action == "paint_active_set":
                active = local._active_inventory_paint()
                if active is None:
                    self._publish_local_request("Cambiar cantidad", LocalAssistantResult("ambiguous", "Selecciona primero una pintura inequívoca.")); return
                current = local.query_service.paint_units(active)
                quantity, ok = QuantityDialog.get_value("Cambiar cantidad", "Cantidad total", current, 0, 999, self)
                if ok: self._publish_local_request(f"Ponla a {quantity}", local.change_active_paint_quantity("set", quantity))
                return
            if action == "paint_find":
                value = AutocompleteDialog.get_value("Buscar pintura", "Nombre de la pintura", local.paint_autocomplete(), self)
                if value: self._handle_local_or_resolve(f"Buscar pintura: {value}", local.find_paint(value))
            elif action == "paint_color":
                values = local.inventory_colors(); value, ok = QInputDialog.getItem(self, "Pinturas por color", "Color principal", values, 0, False)
                if ok and value: self._publish_local_request(f"Pinturas de color {value}", local.paints_by_color(value))
            elif action == "paint_depleted":
                self._publish_local_request("Pinturas agotadas o casi agotadas", local.depleted_paints())
            elif action == "paint_future":
                value = AutocompleteDialog.get_value("Futuras compras", "Pintura", local.catalog_paint_autocomplete(), self)
                if value:
                    quantity, ok = QInputDialog.getInt(self, "Futuras compras", "Cantidad", 1, 1, 99)
                    if ok: self._publish_local_request(f"Añadir {quantity} {value} a futuras compras", local.add_future_paint(value, quantity))
            elif action == "paint_purchased":
                value = AutocompleteDialog.get_value("Marcar como comprada", "Pintura", local.catalog_paint_autocomplete(), self)
                if value:
                    quantity, ok = QInputDialog.getInt(self, "Compra realizada", "Unidades compradas", 1, 1, 99)
                    if ok: self._publish_local_request(f"He comprado {quantity} {value}", local.mark_paint_purchased(value, quantity))
            elif action == "mini_count":
                value = AutocompleteDialog.get_value(
                    "Consultar miniaturas", "Unidad",
                    [unit.unit_name for unit in local.miniature_units(owned_only=True)], self,
                )
                if value: self._handle_local_or_resolve(f"Cantidad de {value}", local.miniature_counts(value))
            elif action in {"mini_not_finished", "mini_finished"}:
                selection = self._choose_game_faction(local, owned_only=True)
                if selection:
                    game_id, faction_id, label = selection; finished = action == "mini_finished"
                    request = f"Miniaturas {'terminadas' if finished else 'no terminadas'} de {label}"
                    self._publish_local_request(request, local.miniatures_by_completion(game_id, faction_id, finished))
            elif action == "mini_status":
                conversation = self._ensure_conversation()
                cid = conversation.id
                self.workflow_engine.start(cid, "mini_status")
                status, ok = QInputDialog.getItem(self, "Cambiar estado", "Nuevo estado", ["Montado", "Pintado", "Terminado"], 0, False)
                if not ok:
                    self.workflow_engine.reset(cid); return
                self.workflow_engine.set_value(cid, "target_status", status)
                owned_units = local.miniature_units(owned_only=True)
                if not owned_units:
                    self.workflow_engine.reset(cid)
                    self._publish_local_request("Cambiar estado de miniaturas", LocalAssistantResult("not_found", "No hay miniaturas en tu colección para cambiar de estado."))
                    return
                value = AutocompleteDialog.get_value(
                    "Cambiar estado", "Miniatura de tu colección",
                    [unit.unit_name for unit in owned_units], self,
                )
                if not value:
                    self.workflow_engine.reset(cid); return
                self.workflow_engine.set_value(cid, "entity", value)
                maximum = local.available_miniature_transition_count(value, status) if hasattr(local, "available_miniature_transition_count") else 999
                quantity, ok = QuantityDialog.get_value(
                    "Cambiar estado", "Cantidad", 1, 1, max(1, maximum), self
                )
                if not ok:
                    self.workflow_engine.reset(cid); return
                self.workflow_engine.set_value(cid, "quantity", quantity)
                self._handle_local_or_resolve(
                    f"Cambiar {quantity} {value} a {status}",
                    local.change_miniature_status(value, status, quantity),
                )
                self.workflow_engine.complete(cid)
            elif action == "mini_add":
                conversation = self._ensure_conversation(); cid = conversation.id
                self.workflow_engine.start(cid, "mini_add")
                selection = self._choose_game_faction(local, owned_only=False)
                if not selection:
                    self.workflow_engine.reset(cid); return
                game_id, faction_id, _label = selection
                self.workflow_engine.set_value(cid, "game", game_id)
                self.workflow_engine.set_value(cid, "faction", faction_id)
                units = local.miniature_units(game_id, faction_id, owned_only=False)
                value = AutocompleteDialog.get_value("Añadir miniaturas", "Unidad del catálogo", [unit.unit_name for unit in units], self)
                if not value:
                    self.workflow_engine.reset(cid); return
                unit, _ = local.resolve_miniature(value, inventory_only=False)
                if unit is None:
                    self.workflow_engine.reset(cid); return
                self.workflow_engine.set_value(cid, "entity", unit.unit_name)
                quantity, ok = QInputDialog.getInt(self, "Añadir miniaturas", "Cantidad", 1, 1, 999)
                if not ok:
                    self.workflow_engine.reset(cid); return
                self.workflow_engine.set_value(cid, "quantity", quantity)
                status, ok = QInputDialog.getItem(self, "Añadir miniaturas", "Estado inicial", ["Sin montar", "Montado", "Pintado", "Terminado"], 0, False)
                if not ok:
                    self.workflow_engine.reset(cid); return
                self.workflow_engine.set_value(cid, "initial_status", status)
                self._publish_local_request(f"Añadir {quantity} {unit.unit_name} como {status}", local.add_miniatures(unit, quantity, status))
                self.workflow_engine.complete(cid)

    def _choose_game_faction(self, local: AssistantLocalService, *, owned_only: bool = False):
        games = local.miniature_games(owned_only=owned_only)
        if not games: return None
        game_labels = [name for _id, name in games]; game_name, ok = QInputDialog.getItem(self, "Miniaturas", "Juego", game_labels, 0, False)
        if not ok: return None
        game_id = next(key for key, name in games if name == game_name)
        factions = local.miniature_factions(game_id, owned_only=owned_only); faction_labels = [name for _id, name in factions]
        if not factions: return None
        faction_name, ok = QInputDialog.getItem(self, "Miniaturas", "Facción", faction_labels, 0, False)
        if not ok: return None
        faction_id = next(key for key, name in factions if name == faction_name)
        return game_id, faction_id, f"{game_name} · {faction_name}"

    def _publish_local_request(self, request_text: str, result: LocalAssistantResult):
        conversation = self._ensure_conversation(); cid = conversation.id
        with get_session() as session:
            local = self._local_service(session, cid)
            if hasattr(local, "update_paint_context"):
                if hasattr(local, "update_paint_context"):
                    local.update_paint_context(result)
        self.session_store.add_message(cid, "user", request_text, metadata={"source": "local"})
        self._append_message_bubble("user", request_text, metadata={"source": "local"})
        self._rename_current_conversation(request_text)
        self._append_local_result(cid, result)

    def _append_local_result(self, conversation_id: str, result: LocalAssistantResult):
        metadata = {"source": "local", "kind": result.kind, "data": result.data, "zero_tokens": True}
        self.session_store.add_message(conversation_id, "assistant", result.message, metadata=metadata)
        if self.current_conversation_id == conversation_id:
            self._append_message_bubble("assistant", result.message, metadata=metadata)
        self.request_status.setText("Consulta local · 0 tokens Gemini")

    def _handle_local_or_resolve(self, request_text: str, result: LocalAssistantResult):
        conversation = self._ensure_conversation(); cid = conversation.id
        self.session_store.add_message(cid, "user", request_text, metadata={"source": "local"})
        self._append_message_bubble("user", request_text, metadata={"source": "local"})
        self._rename_current_conversation(request_text)
        if not result.requires_ai_resolution:
            self._append_local_result(cid, result); return
        api_key = AssistantSettingsStore.gemini_api_key()
        if not api_key:
            self._append_local_result(cid, result)
            self.request_status.setText("Nombre no resuelto · configura Gemini o usa el autocompletado")
            return
        data = result.data or {}
        candidates = list(data.get("candidates") or [])
        if not candidates:
            candidates = [item.get("unit_name", "") for item in data.get("matches") or [] if item.get("unit_name")]
        pending = {
            "conversation_id": cid,
            "entity_type": data.get("entity_type", "miniature"),
            "operation": data.get("operation", "status"),
            "raw_name": data.get("raw_name", ""),
            "target_status": data.get("target_status", ""),
            "quantity": data.get("quantity", 1),
        }
        self._start_entity_resolution(api_key, candidates, pending)

    # ------------------------------- chat send -------------------------------
    def send_message(self):
        if self._busy: return
        text = self.input.toPlainText().strip(); image_path = self.attached_image_path
        if not text and not image_path: return

        conversation = self._ensure_conversation(); cid = conversation.id

        local_result = None
        if text and not image_path:
            with get_session() as session:
                local_result = self._local_service(session, cid).try_handle_text(text)

        api_key = AssistantSettingsStore.gemini_api_key()
        if local_result is None and not api_key:
            self.request_status.setText("Esta consulta necesita Gemini. Configura primero Gemini API en Ajustes.")
            return

        visible_content = text or "Imagen adjunta"
        self.session_store.add_message(cid, "user", visible_content, image_path=image_path)
        self._append_message_bubble("user", visible_content, image_path=image_path)
        self._rename_current_conversation(text or "Imagen de pintura")
        self.input.clear(); self.attached_image_path = None; self.attachment_label.clear(); self.attachment_label.setVisible(False); self.remove_attachment_button.setVisible(False)

        if local_result is not None:
            if local_result.requires_ai_resolution:
                data = local_result.data or {}
                candidates = list(data.get("candidates") or [])
                if not candidates:
                    candidates = [item.get("unit_name", "") for item in data.get("matches") or [] if item.get("unit_name")]
                if not api_key:
                    self._append_local_result(cid, local_result); return
                pending = {
                    "conversation_id": cid,
                    "entity_type": data.get("entity_type", "miniature"),
                    "operation": data.get("operation", "status"),
                    "raw_name": data.get("raw_name", ""),
                    "target_status": data.get("target_status", ""),
                    "quantity": data.get("quantity", 1),
                }
                self._start_entity_resolution(api_key, candidates, pending)
            else:
                self._append_local_result(cid, local_result)
            return

        self._set_busy(True, "Gemini está pensando · modo de bajo consumo…")
        task = AssistantRequestTask(
            conversation_id=cid, api_key=api_key, provider_history=list(conversation.provider_history), user_text=text,
            image_path=image_path, service_factory=self._gemini_service_factory,
        )
        self._active_tasks.add(task); task.signals.success.connect(self._assistant_finished); task.signals.failure.connect(self._assistant_failed)
        task.signals.finished.connect(lambda task=task: self._release_task(task)); self._thread_pool.start(task)

    def _start_entity_resolution(self, api_key: str, candidates: list[str], pending: dict):
        entity_type = pending.get("entity_type", "miniature")
        if entity_type == "paint":
            self._set_busy(True, "Gemini interpreta únicamente el nombre de la pintura…")
            task = PaintResolveTask(api_key, pending["raw_name"], candidates, service_factory=self._gemini_service_factory)
            task.signals.success.connect(lambda resolved, usage, data=pending: self._paint_resolved(data, resolved, usage))
        else:
            self._set_busy(True, "Gemini interpreta únicamente el nombre de la miniatura…")
            task = MiniatureResolveTask(api_key, pending["raw_name"], candidates, service_factory=self._gemini_service_factory)
            task.signals.success.connect(lambda resolved, usage, data=pending: self._miniature_resolved(data, resolved, usage))
        self._active_tasks.add(task)
        task.signals.failure.connect(lambda code, message, cid=pending["conversation_id"]: self._assistant_failed(cid, code, message))
        task.signals.finished.connect(lambda task=task: self._release_task(task))
        self._thread_pool.start(task)

    def _miniature_resolved(self, pending: dict, resolved: str, usage: dict):
        cid = pending["conversation_id"]
        if not resolved:
            result = LocalAssistantResult("not_found", "Gemini no ha podido relacionar el nombre con una miniatura real de tu colección. No se ha modificado nada.")
        else:
            with get_session() as session:
                local = self._local_service(session, cid)
                if pending.get("operation") == "counts":
                    result = local.miniature_counts(resolved)
                else:
                    result = local.change_miniature_status(resolved, pending["target_status"], pending["quantity"])
        self._append_local_result(cid, result)
        self._set_busy(False, self._usage_text(usage, prefix="Gemini solo para identificar nombre"))

    def _paint_resolved(self, pending: dict, resolved: str, usage: dict):
        cid = pending["conversation_id"]
        if not resolved:
            result = LocalAssistantResult("not_found", "Gemini no ha podido relacionar el texto con una pintura real del catálogo.")
        else:
            with get_session() as session:
                local = self._local_service(session, cid)
                result = local.find_paint(resolved, allow_ai_fallback=False)
                if hasattr(local, "update_paint_context"):
                    local.update_paint_context(result)
        self._append_local_result(cid, result)
        self._set_busy(False, self._usage_text(usage, prefix="Gemini solo para identificar pintura"))

    def _assistant_finished(self, conversation_id: str, answer: str, provider_history, tool_events, usage):
        conversation = self.session_store.get(conversation_id)
        if conversation is not None:
            conversation.provider_history = list(provider_history or [])
            metadata = {"source": "gemini", "usage": dict(usage or {})}
            self.session_store.add_message(conversation_id, "assistant", answer, metadata=metadata)
            if self.current_conversation_id == conversation_id: self._append_message_bubble("assistant", answer, metadata=metadata)
        self._set_busy(False, self._usage_text(usage))

    def _assistant_failed(self, conversation_id: str, code: str, message: str):
        error_text = f"⚠ {message}"
        conversation = self.session_store.get(conversation_id)
        quota_error = str(code).startswith("quota")
        duplicate = bool(conversation and conversation.messages and conversation.messages[-1].role == "assistant" and conversation.messages[-1].content == error_text)
        if conversation is not None and not (quota_error and duplicate):
            metadata = {"source": "gemini", "error_code": code}
            self.session_store.add_message(conversation_id, "assistant", error_text, metadata=metadata)
            if self.current_conversation_id == conversation_id: self._append_message_bubble("assistant", error_text, metadata=metadata)
        self._set_busy(False, message if quota_error else "")

    @staticmethod
    def _usage_text(usage, prefix: str = "Gemini") -> str:
        usage = dict(usage or {}); total = int(usage.get("total_tokens") or 0)
        if not total: return prefix
        return (
            f"{prefix} · {total} tokens · entrada {int(usage.get('input_tokens') or 0)} · "
            f"salida {int(usage.get('output_tokens') or 0)} · pensamiento {int(usage.get('thought_tokens') or 0)}"
        )

    def _ensure_conversation(self):
        if self.current_conversation_id is None: self.new_conversation()
        conversation = self.session_store.get(self.current_conversation_id)
        if conversation is None:
            self.new_conversation(); conversation = self.session_store.get(self.current_conversation_id)
        return conversation

    def _local_service(self, session, conversation_id: str | None = None) -> AssistantLocalService:
        cid = str(conversation_id or self.current_conversation_id or "")
        context = self._paint_contexts.setdefault(cid, PaintConversationContext())
        try:
            return AssistantLocalService(session, context=context)
        except TypeError:
            return AssistantLocalService(session)

    def _release_task(self, task):
        self._active_tasks.discard(task)

    def _set_busy(self, busy: bool, message: str):
        self._busy = bool(busy); self.input.setEnabled(not busy); self.attach_button.setEnabled(not busy); self.send_button.setEnabled(not busy)
        self.remove_attachment_button.setEnabled(not busy); self.request_status.setText(message); self.send_button.setText("Enviando…" if busy else "Enviar")

    def _rename_current_conversation(self, text: str):
        item = self.conversation_list.currentItem()
        if item is None: return
        title = " ".join(str(text or "").split())[:42] or "Nueva conversación"; item.setText(title)
        conversation = self.session_store.get(self.current_conversation_id)
        if conversation is not None: conversation.title = title
