from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.services.favorite_paint_analysis_service import MIN_VISIBLE_SIMILARITY_PERCENT, PaintAnalysisResult


def _paint_label(paint) -> str:
    bits = [str(getattr(paint, "brand", "") or "").strip(), str(getattr(paint, "name", "") or "").strip()]
    code = str(getattr(paint, "code", "") or "").strip()
    range_name = str(getattr(paint, "range_name", "") or "").strip()
    if range_name:
        bits.append(range_name)
    if code:
        bits.append(code)
    return " · ".join(bit for bit in bits if bit)


def _catalog_label(paint) -> str:
    bits = [paint.brand, paint.name]
    if paint.range_name:
        bits.append(paint.range_name)
    if paint.code:
        bits.append(paint.code)
    return " · ".join(bit for bit in bits if bit)


class PaintAnalysisDialog(QDialog):
    def __init__(
        self,
        title: str,
        result: PaintAnalysisResult,
        parent=None,
        on_add_to_future_purchases: Callable[[object], str] | None = None,
    ):
        super().__init__(parent)
        self.result = result
        self.on_add_to_future_purchases = on_add_to_future_purchases
        self.setWindowTitle(f"Pinturas · {title}" if title else "Pinturas del tutorial")
        self.resize(940, 720)
        self.setMinimumSize(760, 560)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        heading = QLabel(title or "Análisis de pinturas")
        heading.setObjectName("PageTitle")
        heading.setWordWrap(True)
        root.addWidget(heading)

        explanation = QLabel(
            "Análisis determinista de la descripción pública del vídeo. "
            "Ciros Paint solo muestra productos que ha podido relacionar con su catálogo."
        )
        explanation.setObjectName("Muted")
        explanation.setWordWrap(True)
        root.addWidget(explanation)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        content = QWidget(scroll)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(2, 2, 8, 2)
        content_layout.setSpacing(14)

        if not self.result.detected:
            content_layout.addWidget(self._empty_analysis_state())
        else:
            content_layout.addWidget(self._author_section())
            content_layout.addWidget(self._matches_section())
            content_layout.addWidget(self._alternatives_section())
        content_layout.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        close_button = QPushButton("Cerrar")
        close_button.setObjectName("PrimaryButton")
        close_button.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(close_button)
        root.addLayout(row)

    def _empty_analysis_state(self) -> QFrame:
        frame = QFrame(self)
        frame.setObjectName("Card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(10)

        title = QLabel("No se han encontrado pinturas en la descripción del vídeo.")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 13pt; font-weight: 700;")
        title.setWordWrap(True)

        detail = QLabel(
            "La descripción no contiene ninguna referencia que Ciros Paint pueda identificar con suficiente seguridad en su catálogo."
        )
        detail.setObjectName("Muted")
        detail.setAlignment(Qt.AlignCenter)
        detail.setWordWrap(True)

        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(detail)
        layout.addStretch()
        return frame

    def _section(self, number: int, title: str, subtitle: str) -> tuple[QFrame, QVBoxLayout]:
        frame = QFrame(self)
        frame.setObjectName("Card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        heading = QLabel(f"{number}. {title}")
        heading.setStyleSheet("font-size: 12pt; font-weight: 700;")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("Muted")
        subtitle_label.setWordWrap(True)
        layout.addWidget(heading)
        layout.addWidget(subtitle_label)
        return frame, layout

    @staticmethod
    def _item_box() -> tuple[QFrame, QVBoxLayout]:
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background: #121925; border: 1px solid #2b3648; border-radius: 8px; }"
            "QLabel { border: none; background: transparent; }"
            "QPushButton { border-radius: 6px; }"
        )
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(6)
        return frame, layout

    def _author_section(self) -> QFrame:
        frame, layout = self._section(
            1,
            "Lo escrito por el autor",
            "Fragmentos de la descripción en los que se han identificado pinturas del catálogo.",
        )
        for line in self.result.author_lines:
            item, item_layout = self._item_box()
            text = QLabel(line)
            text.setWordWrap(True)
            text.setTextInteractionFlags(Qt.TextSelectableByMouse)
            item_layout.addWidget(text)
            layout.addWidget(item)
        return frame

    def _matches_section(self) -> QFrame:
        frame, layout = self._section(
            2,
            "Coincidencias con tu inventario",
            "Se muestran coincidencias exactas y coincidencias probables por nombre de al menos un 85 %.",
        )

        if not self.result.matches:
            empty = QLabel("No hay coincidencias de al menos un 85 % con pinturas disponibles en tu inventario.")
            empty.setObjectName("Muted")
            empty.setWordWrap(True)
            layout.addWidget(empty)
            return frame

        for match in self.result.exact_matches:
            item, item_layout = self._item_box()
            state = QLabel("✓ Coincidencia exacta · 100%")
            state.setStyleSheet("font-weight: 700; color: #88d498;")
            original = QLabel(f"Autor / catálogo: {_catalog_label(match.detected.catalog_paint)}")
            inventory = QLabel(f"Tu inventario: {_paint_label(match.inventory_paint)}")
            units = QLabel(f"Unidades: {getattr(match.inventory_paint, 'total_units', 0)}")
            units.setObjectName("Muted")
            for label in (original, inventory, units):
                label.setWordWrap(True)
            item_layout.addWidget(state)
            item_layout.addWidget(original)
            item_layout.addWidget(inventory)
            item_layout.addWidget(units)
            layout.addWidget(item)

        for match in self.result.possible_matches:
            item, item_layout = self._item_box()
            percent = round(match.name_similarity * 100)
            state = QLabel(f"≈ Posible coincidencia por nombre · {percent}%")
            state.setStyleSheet("font-weight: 700; color: #f2c879;")
            original = QLabel(f"Autor / catálogo: {_catalog_label(match.detected.catalog_paint)}")
            inventory = QLabel(f"Tu inventario: {_paint_label(match.inventory_paint)}")
            type_label = QLabel(f"Tipo compatible: {getattr(match.inventory_paint, 'paint_type', '')}")
            type_label.setObjectName("Muted")
            for label in (original, inventory, type_label):
                label.setWordWrap(True)
            item_layout.addWidget(state)
            item_layout.addWidget(original)
            item_layout.addWidget(inventory)
            item_layout.addWidget(type_label)
            layout.addWidget(item)
        return frame

    def _alternatives_section(self) -> QFrame:
        frame, layout = self._section(
            3,
            "Alternativas",
            "Solo aparecen alternativas del mismo tipo de pintura y con una similitud de color de al menos un 85 %.",
        )

        if not self.result.missing:
            empty = QLabel("No hay pinturas pendientes de alternativa.")
            empty.setObjectName("Muted")
            layout.addWidget(empty)
            return frame

        for missing in self.result.missing:
            item, item_layout = self._item_box()
            source = missing.detected.catalog_paint
            title = QLabel(f"No encontrada: {_catalog_label(source)}")
            title.setStyleSheet("font-weight: 700;")
            type_label = QLabel(f"Tipo requerido: {source.paint_type}")
            type_label.setObjectName("Muted")
            title.setWordWrap(True)
            item_layout.addWidget(title)
            item_layout.addWidget(type_label)

            if not missing.alternatives:
                none = QLabel(
                    f"No hay coincidencias de al menos un {MIN_VISIBLE_SIMILARITY_PERCENT:.0f} % para esta pintura. "
                    "¿Quieres añadirla a Futuras compras?"
                )
                none.setObjectName("Muted")
                none.setWordWrap(True)
                item_layout.addWidget(none)

                cart = QPushButton("🛒 Añadir a futuras compras")
                cart.setObjectName("PrimaryButton")
                cart.setToolTip("Añade la pintura original del tutorial a Futuras compras")
                cart.clicked.connect(lambda _checked=False, paint=source, button=cart: self._add_to_future_purchases(paint, button))
                item_layout.addWidget(cart, 0, Qt.AlignLeft)
            else:
                for index, alternative in enumerate(missing.alternatives, start=1):
                    line = QLabel(
                        f"{index}. {_paint_label(alternative.inventory_paint)}  ·  "
                        f"{alternative.similarity:.0f}% similitud  ·  ΔE {alternative.delta_e:.1f}"
                    )
                    line.setWordWrap(True)
                    item_layout.addWidget(line)
            layout.addWidget(item)
        return frame

    def _add_to_future_purchases(self, paint, button: QPushButton) -> None:
        if self.on_add_to_future_purchases is None:
            QMessageBox.warning(self, "Futuras compras", "No se ha podido conectar con Futuras compras.")
            return
        try:
            status = self.on_add_to_future_purchases(paint)
        except Exception as exc:
            QMessageBox.warning(self, "Futuras compras", f"No se ha podido añadir la pintura: {exc}")
            return

        button.setEnabled(False)
        if status == "already":
            button.setText("✓ Ya está en futuras compras")
        else:
            button.setText("✓ Añadida a futuras compras")
