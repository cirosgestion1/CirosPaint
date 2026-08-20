from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QScrollArea, QVBoxLayout, QWidget


class AssistantInfoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Información de Ciros Assistant")
        self.resize(760, 680)
        self.setMinimumSize(620, 520)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        title = QLabel("Ciros Assistant")
        title.setObjectName("PageTitle")
        root.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(6, 4, 12, 8)
        content_layout.setSpacing(14)

        summary_title = QLabel("¿Qué puede hacer?")
        summary_title.setStyleSheet("font-size: 13pt; font-weight: 700;")
        summary = QLabel(
            "Ciros Assistant es un asistente especializado en pintura de miniaturas y modelismo. "
            "Puede consultar tu colección de pinturas, comprobar cantidades, buscar alternativas, gestionar futuras compras "
            "y ayudarte con técnicas, colores y procesos de pintura.\n\n"
            "Cuando una pregunta dependa de las pinturas que tienes, tu inventario de Ciros Paint será siempre la fuente de información principal."
        )
        summary.setWordWrap(True)
        summary.setTextInteractionFlags(Qt.TextSelectableByMouse)
        summary.setStyleSheet(
            "background: #151d29; border: 1px solid #334155; border-radius: 10px; "
            "padding: 14px; color: #e2e8f0;"
        )
        content_layout.addWidget(summary_title)
        content_layout.addWidget(summary)

        sections = (
            (
                "Consultar tu inventario de pinturas",
                "Puedes preguntarle directamente por las pinturas que tienes guardadas en Ciros Paint.\n\n"
                "Por ejemplo:\n"
                "• ¿Qué grises oscuros tengo?\n"
                "• ¿Tengo algún rojo de Vallejo?\n"
                "• ¿Cuántas unidades me quedan de esta pintura?\n\n"
                "El asistente podrá consultar nombres, marcas, gamas, códigos, tipos de pintura, colores y cantidades disponibles.",
            ),
            (
                "Buscar alternativas",
                "Si necesitas una pintura que no tienes, el asistente podrá comprobar si existe una alternativa adecuada dentro de tu propio inventario.\n\n"
                "Ciros Paint realizará la comparación utilizando la información real de las pinturas y su similitud de color, "
                "en lugar de dejar que la IA invente equivalencias.\n\n"
                "Por ejemplo:\n• No tengo esta pintura de Citadel. ¿Tengo algo parecido?",
            ),
            (
                "Gestionar pinturas y cantidades",
                "El asistente podrá ayudarte a modificar tu inventario mediante lenguaje natural. Podrás indicar que has comprado una pintura, "
                "añadir unidades o actualizar la cantidad total que tienes.\n\n"
                "Por ejemplo:\n"
                "• He comprado dos unidades de Neutral Grey.\n"
                "• Ahora tengo tres botes de esta pintura.\n\n"
                "Si una petición puede interpretarse de varias maneras o existen varias pinturas que podrían coincidir, "
                "el asistente te pedirá aclaración antes de modificar tus datos.",
            ),
            (
                "Futuras compras",
                "También podrá consultar y gestionar las pinturas que quieras comprar más adelante.\n\n"
                "Por ejemplo:\n"
                "• Añade esta pintura a futuras compras.\n"
                "• ¿Qué pinturas tengo pendientes de comprar?\n\n"
                "Ciros Paint evitará crear entradas duplicadas cuando una pintura ya esté registrada.",
            ),
            (
                "Ayuda con pintura y modelismo",
                "Puedes utilizar el asistente para resolver dudas sobre pintura de miniaturas, aerografía, pincel, imprimación, luces, sombras, "
                "degradados, desgaste, suciedad, óxido, escenografía, dioramas y otras técnicas relacionadas con el hobby.\n\n"
                "También puede ayudarte a plantear esquemas de color o procesos de pintura paso a paso.\n\n"
                "Por ejemplo:\n"
                "• Quiero pintar un Stormtrooper con bastante desgaste.\n"
                "• ¿Cómo harías unas luces sobre una armadura negra?",
            ),
            (
                "Analizar imágenes",
                "Podrás adjuntar imágenes relacionadas con pinturas para utilizarlas durante una conversación con el asistente.\n\n"
                "Esta función permitirá complementar una consulta escrita con información visual cuando sea útil.",
            ),
            (
                "Cómo utiliza tus datos",
                "Las conversaciones del asistente son temporales. Cada conversación mantiene su propio contexto mientras Ciros Paint está abierto, "
                "pero no se crea una memoria permanente de tus conversaciones.\n\n"
                "Tu inventario local sigue siendo la referencia para cualquier consulta sobre las pinturas que realmente posees.\n\n"
                "Si el asistente no puede determinar con seguridad qué pintura o qué modificación quieres realizar, te preguntará antes de cambiar información de tu colección.",
            ),
        )

        for heading, body in sections:
            heading_label = QLabel(heading)
            heading_label.setStyleSheet("font-size: 11.5pt; font-weight: 700; color: #f1f5f9;")
            body_label = QLabel(body)
            body_label.setWordWrap(True)
            body_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            body_label.setStyleSheet("color: #b8c4d4;")
            content_layout.addWidget(heading_label)
            content_layout.addWidget(body_label)

        content_layout.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
