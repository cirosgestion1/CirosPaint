from __future__ import annotations

import os
import subprocess

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.config import DATA_DIR, DATABASE_PATH
from app.core.settings_store import SettingsStore
from app.services.assistant_settings_store import AssistantSettingsStore


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()

        title = QLabel("Ajustes")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Configuración local de Ciros Paint.")
        subtitle.setObjectName("Muted")

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(14)
        root.addWidget(title)
        root.addWidget(subtitle)
        root.addWidget(self._build_database_card())
        root.addWidget(self._build_youtube_card())
        root.addWidget(self._build_gemini_card())
        root.addStretch()

    def _build_database_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        title = QLabel("Base de datos local")
        title.setStyleSheet("font-weight: 700; font-size: 12pt;")
        description = QLabel(
            "Ciros Paint guarda el inventario y la información de la aplicación en esta ubicación local."
        )
        description.setWordWrap(True)
        description.setObjectName("Muted")

        path = QLabel(str(DATABASE_PATH))
        path.setTextInteractionFlags(path.textInteractionFlags() | 1)
        path.setWordWrap(True)
        path.setStyleSheet("font-family: Consolas, monospace; color: #cbd5e1;")

        self.open_data_button = QPushButton("Abrir ubicación")
        self.open_data_button.setObjectName("SecondaryButton")
        self.open_data_button.clicked.connect(self._open_database_location)

        row = QHBoxLayout()
        row.addWidget(path, 1)
        row.addWidget(self.open_data_button)

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addLayout(row)
        return card

    def _build_youtube_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        title = QLabel("YouTube Data API")
        title.setStyleSheet("font-weight: 700; font-size: 12pt;")
        description = QLabel(
            "Necesaria para el Buscador de tutoriales. La clave se guarda en los datos locales de Ciros Paint y nunca dentro del ejecutable."
        )
        description.setWordWrap(True)
        description.setObjectName("Muted")

        self.youtube_api_key_input = QLineEdit(SettingsStore.youtube_api_key())
        self.youtube_api_key_input.setEchoMode(QLineEdit.Password)
        self.youtube_api_key_input.setPlaceholderText("Pega aquí tu clave de YouTube Data API")

        self.youtube_show_key = QCheckBox("Mostrar clave")
        self.youtube_show_key.toggled.connect(self._toggle_youtube_key_visibility)

        save = QPushButton("Guardar clave")
        save.setObjectName("PrimaryButton")
        save.clicked.connect(self._save_youtube_key)

        self.youtube_status = QLabel("")
        self.youtube_status.setObjectName("Muted")

        row = QHBoxLayout()
        row.addWidget(self.youtube_show_key)
        row.addStretch()
        row.addWidget(save)

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(self.youtube_api_key_input)
        layout.addLayout(row)
        layout.addWidget(self.youtube_status)
        return card

    def _build_gemini_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        title = QLabel("Gemini API")
        title.setStyleSheet("font-weight: 700; font-size: 12pt;")
        description = QLabel(
            "Clave utilizada por Ciros Assistant. Se guarda únicamente en este ordenador, fuera del ejecutable y del repositorio GitHub."
        )
        description.setWordWrap(True)
        description.setObjectName("Muted")

        key_row = QHBoxLayout()
        self.gemini_api_key_input = QLineEdit(AssistantSettingsStore.gemini_api_key())
        self.gemini_api_key_input.setEchoMode(QLineEdit.Password)
        self.gemini_api_key_input.setPlaceholderText("Pega aquí tu API Key de Gemini")
        key_row.addWidget(self.gemini_api_key_input, 1)

        self.gemini_show_key_button = QPushButton("Mostrar")
        self.gemini_show_key_button.setObjectName("SecondaryButton")
        self.gemini_show_key_button.clicked.connect(self._toggle_gemini_key_visibility)
        key_row.addWidget(self.gemini_show_key_button)

        actions = QHBoxLayout()
        save = QPushButton("Guardar clave")
        save.setObjectName("PrimaryButton")
        save.clicked.connect(self._save_gemini_key)

        test = QPushButton("Comprobar conexión")
        test.setObjectName("SecondaryButton")
        test.clicked.connect(self._preview_gemini_connection_check)

        remove = QPushButton("Eliminar clave")
        remove.setObjectName("DangerCompactButton")
        remove.clicked.connect(self._remove_gemini_key)

        actions.addWidget(save)
        actions.addWidget(test)
        actions.addWidget(remove)
        actions.addStretch()

        self.gemini_status = QLabel("")
        self.gemini_status.setWordWrap(True)
        self.gemini_status.setObjectName("Muted")
        self._refresh_gemini_status()

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addLayout(key_row)
        layout.addLayout(actions)
        layout.addWidget(self.gemini_status)
        return card

    def _open_database_location(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        try:
            if os.name == "nt" and DATABASE_PATH.exists():
                subprocess.Popen(["explorer.exe", "/select,", str(DATABASE_PATH)])
                return
            if os.name == "nt":
                subprocess.Popen(["explorer.exe", str(DATA_DIR)])
                return
        except OSError:
            pass
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(DATA_DIR)))

    def _toggle_youtube_key_visibility(self, visible: bool):
        self.youtube_api_key_input.setEchoMode(QLineEdit.Normal if visible else QLineEdit.Password)

    def _save_youtube_key(self):
        key = self.youtube_api_key_input.text().strip()
        SettingsStore.set_youtube_api_key(key)
        self.youtube_status.setText("Clave guardada localmente." if key else "Clave eliminada.")

    def _toggle_gemini_key_visibility(self):
        visible = self.gemini_api_key_input.echoMode() == QLineEdit.Password
        self.gemini_api_key_input.setEchoMode(QLineEdit.Normal if visible else QLineEdit.Password)
        self.gemini_show_key_button.setText("Ocultar" if visible else "Mostrar")

    def _save_gemini_key(self):
        key = self.gemini_api_key_input.text().strip()
        if not key:
            self.gemini_status.setText("No hay ninguna clave que guardar.")
            return
        AssistantSettingsStore.set_gemini_api_key(key)
        self.gemini_status.setText("Clave guardada localmente. No se ha enviado a ningún servicio externo.")

    def _remove_gemini_key(self):
        AssistantSettingsStore.clear_gemini_api_key()
        self.gemini_api_key_input.clear()
        self.gemini_status.setText("Clave eliminada de este ordenador.")

    def _preview_gemini_connection_check(self):
        if not self.gemini_api_key_input.text().strip():
            QMessageBox.information(self, "Gemini", "Primero introduce una API Key de Gemini.")
            return
        QMessageBox.information(
            self,
            "Gemini",
            "La interfaz de comprobación está preparada. La llamada real a Gemini se conectará en la siguiente implementación.",
        )

    def _refresh_gemini_status(self):
        if AssistantSettingsStore.gemini_api_key():
            self.gemini_status.setText(
                "Clave guardada localmente. La conexión real con Gemini todavía no se ejecuta en Ciros Paint 0.10.5."
            )
        else:
            self.gemini_status.setText("Añade una clave para dejar preparada la integración de Gemini.")
