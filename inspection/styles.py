APP_STYLE = """
QWidget {
    background: #11151d;
    color: #edf1f7;
    font-family: 'Segoe UI';
    font-size: 10pt;
}
QMainWindow { background: #0d1118; }
#Sidebar {
    background: #090d13;
    border-right: 1px solid #252c38;
}
#BrandTitle { font-size: 18pt; font-weight: 800; letter-spacing: 1px; }
#BrandSubtitle { color: #778397; font-size: 8.5pt; }
QPushButton#NavButton {
    text-align: left;
    padding: 11px 14px;
    border: 0;
    border-radius: 8px;
    background: transparent;
    color: #b7c0cf;
}
QPushButton#NavButton:hover { background: #171d28; color: #ffffff; }
QPushButton#NavButton:checked { background: #232b39; color: #ffffff; font-weight: 650; }
QPushButton#PrimaryButton {
    background: #e7edf7;
    color: #111720;
    border: none;
    border-radius: 8px;
    padding: 9px 14px;
    font-weight: 750;
}
QPushButton#PrimaryButton:hover { background: #ffffff; }
QPushButton#SecondaryButton {
    background: #1c2330;
    color: #dfe6f0;
    border: 1px solid #303949;
    border-radius: 8px;
    padding: 8px 12px;
}
QPushButton#SecondaryButton:hover { background: #252e3d; }
QPushButton#SecondaryButton:disabled { color: #667083; background: #151a23; border-color: #252b36; }
QPushButton#DangerButton {
    background: #301b20;
    color: #ffbdc6;
    border: 1px solid #63303a;
    border-radius: 8px;
    padding: 8px 12px;
}
QPushButton#DangerButton:disabled { color: #75535a; background: #1d1518; border-color: #392127; }
QLineEdit, QComboBox, QSpinBox, QTextEdit, QListWidget {
    background: #171d27;
    border: 1px solid #303949;
    border-radius: 7px;
    padding: 7px;
    selection-background-color: #52637d;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus, QListWidget:focus { border-color: #71829c; }
QTableWidget {
    background: #121821;
    alternate-background-color: #151c26;
    border: 1px solid #29313f;
    border-radius: 8px;
    gridline-color: #252d39;
}
QHeaderView::section {
    background: #1a212d;
    color: #aeb9c9;
    border: none;
    border-bottom: 1px solid #303949;
    padding: 8px;
    font-weight: 650;
}
QTableWidget::item { padding: 6px; }
QTableWidget::item:selected { background: #344155; }
QScrollArea { background: transparent; border: none; }
QScrollBar:vertical { background: #11151d; width: 10px; }
QScrollBar::handle:vertical { background: #333d4e; border-radius: 5px; min-height: 30px; }
QScrollBar:horizontal { background: #11151d; height: 8px; }
QScrollBar::handle:horizontal { background: #333d4e; border-radius: 4px; min-width: 30px; }
#PageTitle { font-size: 22pt; font-weight: 750; }
#Muted { color: #8d99aa; }
#Card {
    background: #171d27;
    border: 1px solid #29313f;
    border-radius: 12px;
}
#CardNumber { font-size: 24pt; font-weight: 750; }
#CardLabel { color: #98a4b5; }
#ChatPanel {
    background: #151b25;
    border: 1px solid #2c3544;
    border-radius: 12px;
}
#FilterPanel {
    background: #141a23;
    border: 1px solid #282f3c;
    border-radius: 10px;
}
#FilterTitle {
    color: #768298;
    font-size: 8pt;
    font-weight: 800;
    min-width: 42px;
}
QPushButton#FilterChip {
    background: #1a202b;
    color: #aeb8c8;
    border: 1px solid #2d3543;
    border-radius: 12px;
    padding: 4px 9px;
    font-size: 8.5pt;
}
QPushButton#FilterChip:hover { background: #232b38; color: #ffffff; }
QPushButton#FilterChip:checked {
    background: #dce5f1;
    color: #111720;
    border-color: #dce5f1;
    font-weight: 700;
}
#PaintCard {
    background: #171d27;
    border: 1px solid #29313f;
    border-radius: 10px;
}
#PaintCard:hover {
    background: #1c2430;
    border-color: #47546a;
}
#PaintCardName { font-size: 10.5pt; font-weight: 700; }
#PaintMeta { color: #8f9aad; font-size: 8.2pt; }
#PaintQuantity { font-size: 11pt; font-weight: 800; }
#StatusAvailable {
    color: #9ed5ad;
    background: #17281e;
    border: 1px solid #2f5940;
    border-radius: 9px;
    padding: 2px 7px;
    font-size: 8pt;
}
#StatusLow {
    color: #e7c984;
    background: #2a2416;
    border: 1px solid #66552a;
    border-radius: 9px;
    padding: 2px 7px;
    font-size: 8pt;
}
#StatusOut {
    color: #e4a2aa;
    background: #2a171b;
    border: 1px solid #62313a;
    border-radius: 9px;
    padding: 2px 7px;
    font-size: 8pt;
}
"""

# v0.3 additions are appended to APP_STYLE below at import time.
APP_STYLE += """
QListWidget::item {
    padding: 5px 7px;
    border-radius: 5px;
}
QListWidget::item:hover { background: #202837; }
QListWidget::item:disabled { color: #5f6978; }
"""

# v0.4: selección persistente de tarjetas y controles de cesta.
APP_STYLE += """
#PaintCard[selected=\"true\"] {
    background: #17335a;
    border: 2px solid #4b97ff;
}
#PaintCard[selected=\"true\"]:hover {
    background: #1c3b66;
    border-color: #6aadff;
}
QPushButton#CartButton {
    background: #17301f;
    color: #bde8c8;
    border: 1px solid #356c46;
    border-radius: 8px;
    padding: 8px 12px;
    font-weight: 650;
}
QPushButton#CartButton:hover { background: #1d3c28; }
QPushButton#CartButton:disabled {
    color: #58725e;
    background: #151d17;
    border-color: #26382b;
}
QCheckBox {
    spacing: 6px;
    color: #cbd4e2;
}
QCheckBox:disabled { color: #5f6978; }
"""

# v0.5: tarjetas limpias, logos de marca y controles de cantidad fiables.
APP_STYLE += """
#PaintCard {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 10px;
}
#PaintCard:hover {
    background: transparent;
    border-color: #3b4659;
}
#PaintCard[selected=\"true\"] {
    background: #17335a;
    border: 2px solid #4b97ff;
}
#PaintCard[selected=\"true\"]:hover {
    background: #1c3b66;
    border-color: #6aadff;
}
#PaintCardName {
    color: #f5f7fb;
    font-size: 10.5pt;
    font-weight: 700;
}
#PaintQuantity {
    color: #f5f7fb;
    font-size: 11pt;
    font-weight: 800;
}
#PaintMeta {
    color: #a6b0bf;
    font-size: 8.2pt;
}
#BrandLogo {
    background: transparent;
    border: none;
    color: #cfd7e4;
    font-size: 8pt;
    font-weight: 800;
}
QToolButton#SpinStepButton {
    background: #1c2330;
    color: #dfe6f0;
    border: 1px solid #303949;
    border-radius: 4px;
    min-width: 24px;
    max-width: 24px;
    min-height: 16px;
    max-height: 16px;
    padding: 0;
    font-size: 7pt;
}
QToolButton#SpinStepButton:hover { background: #2a3444; color: #ffffff; }
QToolButton#SpinStepButton:pressed { background: #344155; }
"""

# v0.6: etiquetas de pinturas sin cajas oscuras y compras operativas.
APP_STYLE += """
#PaintCardName, #PaintMeta, #PaintQuantity {
    background: transparent;
    border: none;
}
#ShoppingCellWidget, #ShoppingQuantityControl, #ShoppingBrandLogo, #ShoppingPlainCell {
    background: transparent;
    border: none;
}
QPushButton#PurchaseDoneButton {
    background: #173820;
    color: #bdf2c8;
    border: 1px solid #347147;
    border-radius: 6px;
    font-size: 13pt;
    font-weight: 800;
    padding: 0;
}
QPushButton#PurchaseDoneButton:hover { background: #20502e; color: #ffffff; }
QPushButton#PurchaseRemoveButton {
    background: #3a1b21;
    color: #ffbdc6;
    border: 1px solid #71313d;
    border-radius: 6px;
    font-size: 12pt;
    font-weight: 800;
    padding: 0;
}
QPushButton#PurchaseRemoveButton:hover { background: #52242d; color: #ffffff; }
QPushButton#OfficialLinkButton {
    background: #183a66;
    color: #d9ecff;
    border: 1px solid #3976b7;
    border-radius: 6px;
    font-size: 13pt;
    font-weight: 800;
    padding: 0;
}
QPushButton#OfficialLinkButton:hover { background: #23518a; color: #ffffff; }
QPushButton#OfficialLinkButtonUnavailable {
    background: #222833;
    color: #687385;
    border: 1px solid #333b48;
    border-radius: 6px;
    font-size: 13pt;
    font-weight: 800;
    padding: 0;
}
"""

# v0.7: Materiales comparte el lenguaje visual compacto de Pinturas.
APP_STYLE += """
#MaterialCategoryIcon, #MaterialBrandGeneric {
    background: transparent;
    border: none;
}
"""

# v0.8: Miniaturas visuales y grandes banners de universo.
APP_STYLE += """
#MiniatureGameBanner, #MiniatureFactionCard, #MiniatureUnitCard {
    background: #182130;
    border: 1px solid #344156;
    border-radius: 12px;
}
#MiniatureGameBanner:hover, #MiniatureFactionCard:hover, #MiniatureUnitCard:hover {
    border: 2px solid #72a7ef;
}
#MiniatureBannerTitle {
    background: rgba(5, 8, 13, 185);
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 50);
    border-radius: 10px;
    padding: 14px 22px;
    font-size: 25pt;
    font-weight: 850;
    letter-spacing: 1px;
}
#MiniatureFactionTitle {
    background: rgba(5, 8, 13, 190);
    color: #ffffff;
    border-radius: 8px;
    padding: 9px 12px;
    font-size: 16pt;
    font-weight: 800;
}
#MiniatureUnitName {
    background: rgba(5, 8, 13, 190);
    color: #ffffff;
    border-radius: 6px;
    padding: 4px 6px;
    font-weight: 750;
}
#MiniatureUnitCount {
    background: rgba(5, 8, 13, 230);
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 3px 6px;
    font-size: 9pt;
    font-weight: 850;
}
#MiniatureUnitRole {
    background: rgba(5, 8, 13, 180);
    color: #bfcce0;
    border-radius: 5px;
    padding: 3px 6px;
    font-size: 8.5pt;
}
#FactionIcon {
    background: rgba(5, 8, 13, 205);
    border: 1px solid #68768c;
    border-radius: 7px;
    color: #ffffff;
    font-weight: 800;
}
#MiniSummaryStat {
    background: #151d29;
    border: 1px solid #303b4e;
    border-radius: 9px;
}
#MiniSummaryNumber {
    background: transparent;
    font-size: 16pt;
    font-weight: 850;
}
#MiniSummaryLabel {
    background: transparent;
    color: #9eabbd;
    font-size: 8pt;
}
#MiniSectionTitle {
    color: #c4d2e7;
    background: transparent;
    font-size: 9pt;
    font-weight: 850;
    letter-spacing: 1px;
    padding-top: 5px;
}
"""

# v0.8.2: destructive faction action is compact and visually secondary.
APP_STYLE += """
QPushButton#DangerCompactButton {
    background: #24171b;
    color: #d9959f;
    border: 1px solid #4d2931;
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 8.5pt;
}
QPushButton#DangerCompactButton:hover { background: #301b20; color: #ffbdc6; border-color: #63303a; }
"""

# v0.8.3: direct miniature-state selector. The same semantic colours are
# reused by the number shown on every unit card.
APP_STYLE += """
QPushButton#MiniStateAll,
QPushButton#MiniStateUnassembled,
QPushButton#MiniStateAssembled,
QPushButton#MiniStatePainted,
QPushButton#MiniStateFinished {
    background: #171d27;
    border: 1px solid #3a4556;
    border-radius: 8px;
    padding: 7px 10px;
    font-size: 8.8pt;
    font-weight: 700;
}
QPushButton#MiniStateAll { color: #E5E7EB; border-color: #6B7280; }
QPushButton#MiniStateUnassembled { color: #9CA3AF; border-color: #59616D; }
QPushButton#MiniStateAssembled { color: #EAB308; border-color: #806916; }
QPushButton#MiniStatePainted { color: #3B82F6; border-color: #315F9E; }
QPushButton#MiniStateFinished { color: #22C55E; border-color: #287544; }
QPushButton#MiniStateAll:hover,
QPushButton#MiniStateUnassembled:hover,
QPushButton#MiniStateAssembled:hover,
QPushButton#MiniStatePainted:hover,
QPushButton#MiniStateFinished:hover { background: #232b38; }
QPushButton#MiniStateAll:checked { background: #E5E7EB; color: #111720; border-color: #E5E7EB; }
QPushButton#MiniStateUnassembled:checked { background: #9CA3AF; color: #111720; border-color: #9CA3AF; }
QPushButton#MiniStateAssembled:checked { background: #EAB308; color: #17130A; border-color: #EAB308; }
QPushButton#MiniStatePainted:checked { background: #3B82F6; color: #FFFFFF; border-color: #3B82F6; }
QPushButton#MiniStateFinished:checked { background: #22C55E; color: #07150C; border-color: #22C55E; }
#MiniatureUnitArt { border: none; border-radius: 10px; }
"""

# v0.9.0: tutorial search and favorites.
APP_STYLE += """
#TutorialCard {
    background: #151c27;
    border: 1px solid #2d3747;
    border-radius: 12px;
}
#TutorialCard:hover { border-color: #45566f; background: #182130; }
#TutorialThumbnail {
    background: #0c1118;
    border: 1px solid #303949;
    border-radius: 8px;
    color: #69768a;
    font-weight: 800;
}
#TutorialTitle {
    background: transparent;
    color: #f4f7fb;
    font-size: 11.5pt;
    font-weight: 800;
}
#TutorialMeta {
    background: transparent;
    color: #96a3b6;
    font-size: 8.7pt;
}
QPushButton#FavoriteStarButton {
    min-width: 42px;
    max-width: 42px;
    min-height: 36px;
    background: #1d2532;
    color: #f3c84a;
    border: 1px solid #4a5568;
    border-radius: 8px;
    font-size: 17pt;
    font-weight: 800;
    padding: 0;
}
QPushButton#FavoriteStarButton:hover { background: #293445; border-color: #7a6740; }
QPushButton#FavoriteStarButton:disabled { background: #292718; color: #f3c84a; border-color: #675d2f; }
"""
