from __future__ import annotations

from PySide6.QtCore import Qt, QStringListModel
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)

from app.constants import COLOR_FAMILIES, COLOR_SWATCHES, PAINT_BRANDS, PAINT_TYPES
from app.services.paint_catalog_service import CatalogPaint, PaintCatalogService, infer_color_tags


class PaintDialog(QDialog):
    def __init__(self, parent=None, paint=None):
        super().__init__(parent)
        self.setWindowTitle("Editar pintura" if paint else "Añadir pintura")
        self.setMinimumWidth(570)
        self._swatch_hex = "#8B929C"
        self._catalog = PaintCatalogService()
        self._catalog_display_map: dict[str, CatalogPaint] = {}
        self._loading = True
        self._applying_catalog = False

        self.brand = QComboBox()
        self.brand.addItems(PAINT_BRANDS)
        self.brand.currentTextChanged.connect(self._brand_changed)

        self.name = QLineEdit()
        self.name.setPlaceholderText("Empieza a escribir: Ice Yellow, Abaddon Black…")
        self.name.editingFinished.connect(self._try_apply_exact_name)

        self._completer_model = QStringListModel(self)
        self._completer = QCompleter(self._completer_model, self)
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchContains)
        self._completer.setCompletionMode(QCompleter.PopupCompletion)
        self._completer.setMaxVisibleItems(12)
        self._completer.activated[str].connect(self._catalog_suggestion_selected)
        self.name.setCompleter(self._completer)

        self.catalog_hint = QLabel()
        self.catalog_hint.setObjectName("Muted")
        self.catalog_hint.setWordWrap(True)

        self.code = QLineEdit()
        self.range_name = QLineEdit()

        self.paint_type = QComboBox()
        self.paint_type.addItems(PAINT_TYPES)

        self.primary_color = QComboBox()
        self.primary_color.addItems(COLOR_FAMILIES)
        self.primary_color.currentTextChanged.connect(self._primary_color_changed)

        self.complementary_colors = QListWidget()
        self.complementary_colors.setMaximumHeight(145)
        for color in COLOR_FAMILIES:
            item = QListWidgetItem(color)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.complementary_colors.addItem(item)

        self.swatch_preview = QLabel()
        self.swatch_preview.setFixedSize(28, 28)
        self.swatch_preview.setToolTip("Muestra aproximada del color")
        self.swatch_button = QPushButton("Elegir color…")
        self.swatch_button.setObjectName("SecondaryButton")
        self.swatch_button.clicked.connect(self._choose_swatch)
        swatch_row = QHBoxLayout()
        swatch_row.addWidget(self.swatch_preview)
        swatch_row.addWidget(self.swatch_button)
        swatch_row.addStretch()

        self.available_units = QSpinBox()
        self.available_units.setRange(0, 999)
        self.available_units.setValue(1)
        self.low_units = QSpinBox()
        self.low_units.setRange(0, 999)
        self.low_units.setValue(0)

        self.notes = QTextEdit()
        self.notes.setMaximumHeight(90)

        form = QFormLayout()
        form.addRow("Marca *", self.brand)
        form.addRow("Nombre *", self.name)
        form.addRow("", self.catalog_hint)
        form.addRow("Código", self.code)
        form.addRow("Gama", self.range_name)
        form.addRow("Tipo *", self.paint_type)
        form.addRow("Color principal *", self.primary_color)
        form.addRow("Colores complementarios", self.complementary_colors)
        form.addRow("Muestra de color", swatch_row)
        form.addRow("Botes disponibles", self.available_units)
        form.addRow("Botes casi agotados", self.low_units)
        form.addRow("Notas", self.notes)

        helper = QLabel(
            "El catálogo rellena automáticamente código, gama, tipo y una propuesta de color. "
            "Todos esos datos se pueden corregir manualmente antes de guardar."
        )
        helper.setWordWrap(True)
        helper.setObjectName("Muted")

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(helper)
        layout.addWidget(buttons)

        if paint:
            legacy_brands = {
                "ak": "AK Interactive",
                "ak interactive": "AK Interactive",
                "vallejo": "Vallejo",
                "citadel": "Citadel",
                "games workshop": "Citadel",
            }
            brand_value = legacy_brands.get((paint.brand or "").strip().casefold(), paint.brand)
            if brand_value not in PAINT_BRANDS:
                brand_value = "Vallejo"
            self.brand.setCurrentText(brand_value)
            self.name.setText(paint.name)
            self.code.setText(paint.code or "")
            self.range_name.setText(paint.range_name or "")
            self.paint_type.setCurrentText(paint.paint_type)
            self.primary_color.setCurrentText(paint.primary_color or "Otro")
            self._set_complementary_colors(paint.complementary_colors)
            self.available_units.setValue(paint.available_units)
            self.low_units.setValue(paint.low_units)
            self.notes.setPlainText(paint.notes or "")
            self._swatch_hex = paint.swatch_hex or COLOR_SWATCHES.get(paint.primary_color or "Otro", "#8B929C")
        else:
            self.brand.setCurrentText(PAINT_BRANDS[0])
            self._sync_default_swatch(self.primary_color.currentText())

        self._loading = False
        self._brand_changed(self.brand.currentText())
        self._sync_primary_complement_choices()
        self._update_swatch_preview()

    def _brand_changed(self, brand: str):
        items = self._catalog.for_brand(brand)
        self._catalog_display_map = {item.display_name: item for item in items}
        self._completer_model.setStringList(list(self._catalog_display_map.keys()))
        if items:
            self.catalog_hint.setText(
                f"Catálogo local: {len(items)} referencias de {brand}. Escribe parte del nombre y elige una sugerencia."
            )
        else:
            self.catalog_hint.setText("No hay catálogo local para esta marca; puedes introducir los datos manualmente.")

    def _catalog_suggestion_selected(self, display_text: str):
        item = self._catalog_display_map.get(display_text)
        if item:
            self._apply_catalog_item(item)

    def _try_apply_exact_name(self):
        typed = self.name.text().strip()
        if not typed:
            return
        matches = [item for item in self._catalog.for_brand(self.brand.currentText()) if item.name.casefold() == typed.casefold()]
        if len(matches) == 1:
            self._apply_catalog_item(matches[0])

    def _apply_catalog_item(self, item: CatalogPaint):
        self._applying_catalog = True
        try:
            self.name.setText(item.name)
            self.code.setText(item.code or "")
            self.range_name.setText(item.range_name or "")
            if item.paint_type in PAINT_TYPES:
                self.paint_type.setCurrentText(item.paint_type)
            if item.swatch_hex:
                self._swatch_hex = item.swatch_hex
            primary, complements = infer_color_tags(item.name, item.swatch_hex, item.range_name)
            if primary in COLOR_FAMILIES:
                self.primary_color.setCurrentText(primary)
            self._set_complementary_colors(complements)
            self._sync_primary_complement_choices()
            self._update_swatch_preview()
        finally:
            self._applying_catalog = False

    def _primary_color_changed(self, color_name: str):
        if not self._loading and not self._applying_catalog:
            self._sync_default_swatch(color_name)
        self._sync_primary_complement_choices()

    def _sync_default_swatch(self, color_name: str):
        self._swatch_hex = COLOR_SWATCHES.get(color_name, "#8B929C")
        self._update_swatch_preview()

    def _choose_swatch(self):
        chosen = QColorDialog.getColor(QColor(self._swatch_hex), self, "Color aproximado de la pintura")
        if chosen.isValid():
            self._swatch_hex = chosen.name()
            self._update_swatch_preview()

    def _update_swatch_preview(self):
        if not hasattr(self, "swatch_preview"):
            return
        self.swatch_preview.setStyleSheet(
            f"background:{self._swatch_hex}; border:1px solid #5b6678; border-radius:14px;"
        )

    def _sync_primary_complement_choices(self):
        if not hasattr(self, "complementary_colors"):
            return
        primary = self.primary_color.currentText()
        for i in range(self.complementary_colors.count()):
            item = self.complementary_colors.item(i)
            if item.text() == primary:
                item.setCheckState(Qt.Unchecked)
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            else:
                item.setFlags(item.flags() | Qt.ItemIsEnabled)

    def _set_complementary_colors(self, colors: list[str]):
        wanted = set(colors)
        for i in range(self.complementary_colors.count()):
            item = self.complementary_colors.item(i)
            item.setCheckState(Qt.Checked if item.text() in wanted else Qt.Unchecked)

    def _selected_complements(self) -> list[str]:
        primary = self.primary_color.currentText()
        return [
            self.complementary_colors.item(i).text()
            for i in range(self.complementary_colors.count())
            if self.complementary_colors.item(i).checkState() == Qt.Checked
            and self.complementary_colors.item(i).text() != primary
        ]

    def _validate_and_accept(self):
        if not self.name.text().strip():
            QMessageBox.warning(self, "Datos incompletos", "El nombre es obligatorio.")
            return
        self.accept()

    def data(self) -> dict:
        return {
            "brand": self.brand.currentText(),
            "name": self.name.text().strip(),
            "code": self.code.text().strip() or None,
            "range_name": self.range_name.text().strip() or None,
            "paint_type": self.paint_type.currentText(),
            "primary_color": self.primary_color.currentText(),
            "complementary_colors": self._selected_complements(),
            "swatch_hex": self._swatch_hex,
            "available_units": self.available_units.value(),
            "low_units": self.low_units.value(),
            "notes": self.notes.toPlainText().strip() or None,
        }
