from __future__ import annotations

from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget

from app.services.inventory_service import InventoryService


class StatCard(QFrame):
    def __init__(self, label: str):
        super().__init__()
        self.setObjectName("Card")
        self.number = QLabel("0")
        self.number.setObjectName("CardNumber")
        caption = QLabel(label)
        caption.setObjectName("CardLabel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.addWidget(self.number)
        layout.addWidget(caption)


class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()
        title = QLabel("Inicio")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Resumen rápido de Ciros Paint.")
        subtitle.setObjectName("Muted")

        self.paint_card = StatCard("Pinturas diferentes")
        self.paint_units_card = StatCard("Botes totales")
        self.restock_card = StatCard("Pinturas a reponer")
        self.shopping_card = StatCard("Pendientes de compra")

        cards = QGridLayout()
        cards.setSpacing(14)
        cards.addWidget(self.paint_card, 0, 0)
        cards.addWidget(self.paint_units_card, 0, 1)
        cards.addWidget(self.restock_card, 1, 0)
        cards.addWidget(self.shopping_card, 1, 1)

        info = QFrame()
        info.setObjectName("Card")
        info_layout = QVBoxLayout(info)
        info_title = QLabel("Ciros Paint 0.8.3.1")
        info_title.setStyleSheet("font-size: 14pt; font-weight: 700;")
        info_text = QLabel(
            "Inventario de pinturas rediseñado para colecciones grandes: tarjetas compactas, filtros combinables, "
            "colores principales/complementarios y reposición automática por estado real de stock."
        )
        info_text.setWordWrap(True)
        info_text.setObjectName("Muted")
        info_layout.addWidget(info_title)
        info_layout.addWidget(info_text)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(4)
        layout.addLayout(cards)
        layout.addWidget(info)
        layout.addStretch()

    def refresh(self):
        data = InventoryService.counts()
        self.paint_card.number.setText(str(data["paint_products"]))
        self.paint_units_card.number.setText(str(data["paint_units"]))
        self.restock_card.number.setText(str(data["paint_restock"]))
        self.shopping_card.number.setText(str(data["shopping"]))

