# -*- coding: utf-8 -*-
"""
Main interface of MapBiomas Alerta Oficial.

Allows querying alerts by:

- detection date;
- publication date;
- alert code;
- minimum area;
- source;
- area of interest.

The GraphQL API's result is converted to GeoJSON and opened by QGIS
using the OGR provider.
"""

import csv
import html
import json
import os
import re
import unicodedata
import zipfile


def xml_text_escape(text):
    """Escapes &, < and > for text written into the XLSX XML parts."""
    return html.escape(str(text), quote=False)
from datetime import date, datetime

from qgis.PyQt.QtCore import (
    Qt,
    QSize,
    QDate,
    QDateTime,
    QEvent,
    QRectF,
    QTimer,
    QUrl,
    QMetaType,
    QStandardPaths,
    pyqtSignal,
)
from qgis.PyQt.QtGui import (
    QColor,
    QDesktopServices,
    QDoubleValidator,
    QFont,
    QImage,
    QPainter,
    QPalette,
    QPixmap,
    QCursor,
    QStandardItem,
)
from qgis.PyQt.QtWidgets import (
    QApplication,
    QButtonGroup,
    QBoxLayout,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDockWidget,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTabBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QToolButton,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsAuthMethodConfig,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsFeatureRequest,
    QgsField,
    QgsFillSymbol,
    QgsGeometry,
    QgsMapLayerType,
    QgsMessageLog,
    QgsPointXY,
    QgsProject,
    QgsRasterLayer,
    QgsRectangle,
    QgsSingleSymbolRenderer,
    QgsSpatialIndex,
    QgsSettings,
    QgsVectorLayer,
    QgsVectorFileWriter,
    QgsWkbTypes,
)
from qgis.gui import QgsMapToolIdentify

from .api_client import (
    ApiAuthenticationError,
    MapBiomasApiClient,
    QueryCancelledError,
)
from .country_config import country_config, country_items
from .translations import (
    LANGUAGES,
    DEFAULT_LANGUAGE_BY_COUNTRY,
    README_FILENAME_SUFFIX,
    CROSSINGS_README_TEXT,
    Translator,
)
from .notices import NOTICE_BY_COUNTRY


RESULT_LAYER_PREFIX = "MapBiomas Alerta"


class QuickViewUnavailable(Exception):
    """The map server can't serve this search; download instead."""

# Informational notes (Portuguese text = translation key).
ALERT_IN_PROPERTY_NOTE = (
    "Atenção: é exibido o alerta inteiro que cruza o imóvel, e não "
    "apenas a parte do alerta dentro do imóvel. Para ver a área do "
    "alerta dentro do imóvel, abra o laudo na plataforma."
)
QUICK_VIEW_HELP = (
    "Mostra os alertas no mapa direto do servidor da plataforma, com as "
    "estatísticas da API, sem baixar os polígonos. Os polígonos só são "
    "baixados, automaticamente, quando você exporta, gera um gráfico ou "
    "abre os detalhes de um alerta. Com filtro de fonte ou de "
    "cruzamento, a busca baixa os polígonos direto."
)
SUMMARY_NOTICE = (
    "Este resumo varia de acordo com os filtros selecionados. Com filtro "
    "de fonte ou de cruzamento, o resumo oficial da plataforma não "
    "corresponde ao que é baixado: os números passam a ser calculados a "
    "partir da camada, e média diária, maior velocidade e sobreposições "
    "ficam indisponíveis."
)
NOT_SHOWN_CROSSINGS_NOTE = (
    "Cruzamentos com embargos, autorizações e ações de fiscalização não "
    "são exibidos no plugin. Consulte-os no laudo do alerta na plataforma."
)

# One source of truth for every territorial area calculation.  ``category``
# is the normalized category stored outside the result layer; ``map_field``
# holds exact per-territory intersections when the API supplies them; and
# ``numeric_fields`` lists the only values that may be aggregated safely.
TERRITORIAL_AREA_GROUPS = {
    "municipio": ("Municipio", "MunicAreas", {"areaha", "area_ha", "area"}),
    "municipality": ("Municipio", "MunicAreas", {"areaha", "area_ha", "area"}),
    "estado": ("Estado", "EstadoAreas", {"areaha", "area_ha", "area"}),
    "state": ("Estado", "EstadoAreas", {"areaha", "area_ha", "area"}),
    "bioma": ("Bioma", "BiomaAreas", {"areaha", "area_ha", "area"}),
    "biome": ("Bioma", "BiomaAreas", {"areaha", "area_ha", "area"}),
    "unidconserv": ("UnidConserv", "UnidConservAreas", {"ucareaha"}),
    "terraindig": ("TerraIndig", "TerraIndigAreas", {"tiareaha"}),
    "assentamento": ("Assentamento", "AssentamentoAreas", {"assentarea"}),
    "quilombo": ("Quilombo", "QuilomboAreas", {"quilombarea"}),
    "reservabio": ("ReservaBio", "ReservaBioAreas", {"resbioarea"}),
    "manflorest": ("ManFlorest", "ManFlorestAreas", {"manflorarea"}),
    "protintegral": ("ProtIntegral", "ProtIntegralAreas", {"protintarea"}),
    "usosustent": ("UsoSustent", "UsoSustentAreas", {"usosustarea"}),
    "app": ("APP", "APPAreas", {"appareaha"}),
    "reservalegal": ("ReservaLegal", "RLAreas", {"rlareaha"}),
    "terrespecial": ("TerrEspecial", "TerrEspecialAreas", {"terresparea"}),
    "geoparque": ("Geoparque", "GeoparqueAreas", {"geoparquearea"}),
    "protmunintegral": (
        "ProtMunIntegral", "ProtMunIntegralAreas", {"protmunintarea"},
    ),
    "usomunsust": ("UsoMunSust", "UsoMunSustAreas", {"usomunsustarea"}),
    "protestintegral": (
        "ProtEstIntegral", "ProtEstIntegralAreas", {"protestintarea"},
    ),
    "usoestsust": ("UsoEstSust", "UsoEstSustAreas", {"usoestsustarea"}),
}

ATTRIBUTE_FIELD_ALIASES = {
    "Assentamento": "Assentamentos cruzados (separados por ;)",
    "AssentArea": "Área total cruzada em assentamentos (ha)",
    "AssentamentoAreas": "Área individual por assentamento (JSON em ha)",
    "TerraIndig": "Terras indígenas cruzadas (separadas por ;)",
    "TIAreaHa": "Área total cruzada em terras indígenas (ha)",
    "TerraIndigAreas": "Área individual por terra indígena (JSON em ha)",
    "UnidConserv": "Unidades de conservação cruzadas (separadas por ;)",
    "UCAreaHa": "Área total cruzada em unidades de conservação (ha)",
    "UnidConservAreas": "Área individual por unidade de conservação (JSON em ha)",
    "Quilombo": "Territórios quilombolas cruzados (separados por ;)",
    "QuilombArea": "Área total cruzada em territórios quilombolas (ha)",
    "QuilomboAreas": "Área individual por quilombo (JSON em ha)",
    "SelTerrCat": "Categoria da camada territorial selecionada",
    "SelTerrs": "Territórios selecionados cruzados (separados por ;)",
    "SelTerrAreas": "Interseção por território selecionado (JSON em ha)",
}

TERRITORY_DISPLAY_NAMES = {
    "Bioma": "bioma",
    "Estado": "estado",
    "Municipio": "município",
    "UnidConserv": "unidade de conservação",
    "TerraIndig": "terra indígena",
    "Assentamento": "assentamento",
    "Quilombo": "território quilombola",
    "ReservaBio": "reserva da biosfera",
    "ManFlorest": "manejo florestal",
    "ProtIntegral": "proteção integral federal",
    "UsoSustent": "uso sustentável federal",
    "APP": "área de preservação permanente",
    "ReservaLegal": "reserva legal",
    "TerrEspecial": "território especial",
    "Geoparque": "geoparque",
    "ProtMunIntegral": "proteção integral municipal",
    "UsoMunSust": "uso sustentável municipal",
    "ProtEstIntegral": "proteção integral estadual",
    "UsoEstSust": "uso sustentável estadual",
}
for _territory_field, (_total_field, _area_map_field) in (
    MapBiomasApiClient.TERRITORY_AREA_PAIRS.items()
):
    _display_name = TERRITORY_DISPLAY_NAMES.get(
        _territory_field, _territory_field
    )
    ATTRIBUTE_FIELD_ALIASES.setdefault(
        _territory_field,
        "{}(s) cruzado(s), separado(s) por ;".format(_display_name.capitalize()),
    )
    ATTRIBUTE_FIELD_ALIASES.setdefault(
        _total_field,
        "Área total cruzada em {} (ha)".format(_display_name),
    )
    ATTRIBUTE_FIELD_ALIASES.setdefault(
        _area_map_field,
        "Área individual por {} (JSON em ha)".format(_display_name),
    )


class DetailImageLabel(QLabel):
    """Fits the whole image inside a fixed-height area."""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._source_pixmap = QPixmap()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(240)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_image(self, pixmap):
        self._source_pixmap = QPixmap(pixmap)
        self._fit_image()

    def clear_image(self):
        self._source_pixmap = QPixmap()
        self.clear()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_image()

    def _fit_image(self):
        if self._source_pixmap.isNull():
            return
        available = self.contentsRect().size()
        if available.width() <= 0 or available.height() <= 0:
            return
        self.setPixmap(
            self._source_pixmap.scaled(
                available,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )


class MultiLayerIdentifyTool(QgsMapToolIdentify):
    featureIdentified = pyqtSignal(object, object)

    def __init__(self, canvas, layers):
        super().__init__(canvas)
        self.layers = list(layers)

    def canvasReleaseEvent(self, event):
        # QMouseEvent.x()/y() no longer exist under Qt6 (QGIS 4 and the
        # Qt6 builds of 3.x); pixelPoint() is available on every QGIS 3.x.
        point = event.pixelPoint()
        results = self.identify(
            point.x(), point.y(), self.layers, QgsMapToolIdentify.TopDownAll
        )
        if results:
            result = results[0]
            self.featureIdentified.emit(result.mLayer, result.mFeature)


class AutoFitPushButton(QPushButton):
    """Button that keeps its text fully visible in narrow panels or
    longer translations, wrapping into up to 2 lines by character
    count (never mid-word) instead of relying on Qt's own text
    measurement. Font-fitting via sizeHint() is kept as a fallback."""

    MAX_CHARS_PER_LINE = 16

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_size = self.font().pointSizeF()
        self._base_point_size = base_size if base_size > 0 else 9.0
        self._min_point_size = 6.5
        self._fitting = False

    @classmethod
    def wrap_text(cls, text):
        """Wraps text into at most 2 lines, breaking only at spaces.
        Finds the smallest line width (starting from the longest word)
        that still fits the text in 2 lines, rather than using a fixed
        width that could overflow to 3."""
        if len(text) <= cls.MAX_CHARS_PER_LINE or " " not in text:
            return text
        words = text.split(" ")
        lower_bound = max(cls.MAX_CHARS_PER_LINE, max(len(w) for w in words))
        best_lines = None
        for target in range(lower_bound, len(text) + 1):
            lines = cls._greedy_wrap(words, target)
            if len(lines) <= 2:
                best_lines = lines
                break
        if best_lines is None:
            best_lines = cls._greedy_wrap(words, len(text))
        return "\n".join(best_lines)

    @staticmethod
    def _greedy_wrap(words, target):
        lines = []
        current = ""
        for word in words:
            candidate = (current + " " + word).strip()
            if len(candidate) <= target or not current:
                current = candidate
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    def setText(self, text):
        super().setText(self.wrap_text(text))
        self._fit_font()
        # The first time the text changes (e.g. while the panel is being
        # built), the button may not yet have its final layout width —
        # redo the fit once Qt finishes processing the pending layout.
        QTimer.singleShot(0, self._fit_font)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_font()

    def showEvent(self, event):
        super().showEvent(event)
        self._fit_font()

    def _fit_font(self):
        if self._fitting:
            return
        text = self.text()
        if not text:
            return
        target_width = self.width()
        if target_width <= 0:
            return
        self._fitting = True
        try:
            # Extra reinforcement on top of the line wrap (see wrap_text):
            # uses the button's own sizeHint(), which already accounts for
            # the style/theme's actual padding — more reliable than
            # estimating the available width manually.
            font = self.font()
            size = self._base_point_size
            while size > self._min_point_size:
                font.setPointSizeF(size)
                self.setFont(font)
                if self.sizeHint().width() <= target_width:
                    break
                size -= 0.5
            else:
                font.setPointSizeF(self._min_point_size)
                self.setFont(font)
        finally:
            self._fitting = False


class FocusComboBox(QComboBox):
    """Prevents the selected option from changing just by scrolling the panel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event):
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


class FocusDateEdit(QDateEdit):
    def wheelEvent(self, event):
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


class FocusDoubleSpinBox(QDoubleSpinBox):
    def wheelEvent(self, event):
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


class FocusSpinBox(QSpinBox):
    def wheelEvent(self, event):
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


class CheckableComboBox(FocusComboBox):
    selectionChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        # "default_text" can be replaced from outside (main_dialog.py sets
        # it with self.tr(...) and updates it again in retranslate_ui) —
        # this class is a generic widget with no direct access to the
        # main panel's translator.
        self.default_text = "Todas as fontes"
        self.lineEdit().setPlaceholderText(self.default_text)
        self.view().pressed.connect(self.toggle_item)
        self.view().viewport().installEventFilter(self)

    def eventFilter(self, watched, event):
        if (
            watched is self.view().viewport()
            and event.type() == QEvent.Type.MouseButtonRelease
        ):
            return True
        return super().eventFilter(watched, event)

    def add_check_item(self, label, value):
        item = QStandardItem(label)
        item.setData(value, Qt.ItemDataRole.UserRole)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        item.setData(Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
        self.model().appendRow(item)

    def toggle_item(self, index):
        item = self.model().itemFromIndex(index)
        item.setCheckState(
            Qt.CheckState.Unchecked if item.checkState() == Qt.CheckState.Checked else Qt.CheckState.Checked
        )
        self.update_text()
        self.selectionChanged.emit()

    def checked_data(self):
        return [
            self.model().item(row).data(Qt.ItemDataRole.UserRole)
            for row in range(self.model().rowCount())
            if self.model().item(row).checkState() == Qt.CheckState.Checked
        ]

    def checked_labels(self):
        return [
            self.model().item(row).text()
            for row in range(self.model().rowCount())
            if self.model().item(row).checkState() == Qt.CheckState.Checked
        ]

    def update_text(self):
        labels = self.checked_labels()
        text = ", ".join(labels) if labels else self.default_text
        self.lineEdit().setText(text)
        self.setToolTip(text)

    def clear_checks(self):
        for row in range(self.model().rowCount()):
            self.model().item(row).setCheckState(Qt.CheckState.Unchecked)
        self.update_text()
        self.selectionChanged.emit()


class TwoColumnForm(QGridLayout):
    """Drop-in for the QFormLayout.addRow(label, field) calls of the chart
    configuration: fields go two per row, each label above its field
    (proposal v2)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._count = 0
        self.setContentsMargins(0, 0, 0, 0)
        self.setHorizontalSpacing(10)
        self.setVerticalSpacing(3)
        self.setColumnStretch(0, 1)
        self.setColumnStretch(1, 1)

    def addRow(self, label, field):
        row = (self._count // 2) * 2
        column = self._count % 2
        self.addWidget(label, row, column)
        self.addWidget(field, row + 1, column)
        self._count += 1


class MirrorLabel(QLabel):
    """QLabel that reports every setText(), so the v2 summary cards can
    mirror the values update_result_summary() already writes."""

    def __init__(self, text="", on_change=None, parent=None):
        super().__init__(text, parent)
        self._on_change = on_change

    def setText(self, text):
        super().setText(text)
        if self._on_change is not None:
            self._on_change()


class ReadableTabBar(QTabBar):
    def tabSizeHint(self, index):
        size = super().tabSizeHint(index)
        text_width = self.fontMetrics().horizontalAdvance(
            self.tabText(index)
        )
        size.setWidth(max(size.width(), text_width + 18))
        return size

    def minimumTabSizeHint(self, index):
        # Lets the tabs shrink together so all of them fit in the dock.
        size = super().minimumTabSizeHint(index)
        size.setWidth(min(size.width(), 48))
        return size


class ResponsiveTabWidget(QTabWidget):
    """Allows the tabs to shrink; each page manages its own scrolling."""

    def minimumSizeHint(self):
        return QSize(0, 120)


class HelpIconLabel(QLabel):
    """Info balloon independent of QGIS's dark theme."""

    def __init__(self, help_text, parent=None):
        super().__init__("ⓘ", parent)
        self.popup = QLabel(None, Qt.WindowType.ToolTip)
        self.set_help_text(help_text)
        self.popup.setWordWrap(True)
        self.popup.setMaximumWidth(430)
        self.popup.setMargin(8)
        self.popup.setStyleSheet(
            "QLabel { background-color: #FFFFFF; color: #000000; "
            "border: 1px solid #7F8C85; font-weight: 700; }"
        )

    def set_help_text(self, help_text):
        """Updates the balloon's content — used both on creation and to
        retranslate when the language (or country, in some cases)
        changes after the icon has already been created."""
        self.popup.setText("<b>{}</b>".format(html.escape(help_text)))

    def enterEvent(self, event):
        self._reposition_and_show()
        super().enterEvent(event)

    def _screen_available_rect(self):
        cursor_pos = QCursor.pos()
        screen = QApplication.screenAt(cursor_pos)
        if screen is None and hasattr(self, "screen"):
            screen = self.screen()
        if screen is None:
            screen = QApplication.primaryScreen()
        if screen is None:
            return None
        return screen.availableGeometry()

    def _reposition_and_show(self):
        # The balloon is its own window (Qt.WindowType.ToolTip), so it must be
        # repositioned in screen coordinates, not panel coordinates. Its
        # max width is capped to a fraction of the available screen so it
        # never exceeds the screen itself on small monitors or a
        # non-maximized QGIS window.
        available = self._screen_available_rect()
        if available is not None:
            max_width = max(220, min(430, int(available.width() * 0.45)))
            self.popup.setMaximumWidth(max_width)
        self.popup.adjustSize()
        cursor_pos = QCursor.pos()
        x = cursor_pos.x() + 14
        y = cursor_pos.y() + 14
        if available is not None:
            x, y = self._clamp_to_rect(
                x, y, self.popup.width(), self.popup.height(), available
            )
        self.popup.move(x, y)
        self.popup.show()
        # adjustSize()/width()/height() may not reflect the window's final
        # geometry on every platform before it is actually shown (borders/
        # decorations are only resolved by the window manager after
        # show()). So fix the position again based on the real, already-
        # shown geometry — this ensures the balloon is never clipped, even
        # when the first calculation (before show()) was inaccurate.
        if available is not None:
            frame = self.popup.frameGeometry()
            x2, y2 = self._clamp_to_rect(
                frame.x(), frame.y(), frame.width(), frame.height(),
                available,
            )
            if (x2, y2) != (frame.x(), frame.y()):
                self.popup.move(x2, y2)

    @staticmethod
    def _clamp_to_rect(x, y, width, height, rect):
        x = min(x, rect.right() - width)
        x = max(x, rect.left())
        y = min(y, rect.bottom() - height)
        y = max(y, rect.top())
        return x, y

    def leaveEvent(self, event):
        self.popup.hide()
        super().leaveEvent(event)


class BarChartWidget(QLabel):
    """Chart rasterized outside QGIS's paintEvent cycle."""

    COLORS = (
        "#832413", "#d57a35", "#e4b64a", "#4c7a58", "#3c718c",
        "#76558b", "#b45c78", "#7d6b55", "#68a5a1", "#a6a64c",
        # Up to 20 categories without repeating a color (pie legends with
        # "Categorias exibidas" above 10 used to reuse the first colors).
        "#c9503a", "#f0a05a", "#8fae5d", "#2f5d73", "#a98bc2",
        "#e38fa9", "#b59b7a", "#3f8f8a", "#d9c46a", "#5c4633",
    )
    OTHERS_COLOR = "#9AA19C"

    def slice_color(self, index, label):
        if str(label).startswith(("Outros", "Otros", "Others")):
            return QColor(self.OTHERS_COLOR)
        return QColor(self.COLORS[index % len(self.COLORS)])

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = []
        self._chart_type = "bar"
        self._integer_values = False
        self._value_suffix = ""
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        # The chart lives inside a scrollable area; its drawing width must
        # not become the minimum width of the whole dock.
        self.setMinimumSize(0, 280)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

    def set_items(self, items):
        self._items = list(items)
        self.render_chart()

    def set_chart_type(self, chart_type):
        self._chart_type = chart_type
        self.render_chart()

    def set_value_format(self, integer_values=False, suffix=""):
        self._integer_values = integer_values
        self._value_suffix = suffix
        self.render_chart()

    def format_value(self, value):
        if self._integer_values:
            text = "{:,.0f}".format(value).replace(",", ".")
        else:
            text = ("{:,.1f}".format(value).replace(",", "_")
                    .replace(".", ",").replace("_", "."))
        return "{}{}".format(text, self._value_suffix)

    def render_chart(self):
        categories = list(dict.fromkeys(item[0] for item in self._items))
        comparison = bool(self._items and len(self._items[0]) == 3)
        category_width = 280 if comparison else 190
        width = max(760 if comparison else 620,
                    category_width * len(categories))
        if self._chart_type == "pie":
            height = max(300, 60 + len(self._items) * 24)
        else:
            height = 340 if comparison else 300
        self.resize(width, height)
        self.setMinimumHeight(height)
        # Render at the screen pixel density while keeping logical dimensions.
        scale = max(1.0, float(self.devicePixelRatioF()))
        image = QImage(
            max(1, int(round(width * scale))),
            max(1, int(round(height * scale))),
            QImage.Format.Format_ARGB32,
        )
        image.fill(QColor("#ffffff"))
        painter = QPainter()
        if not painter.begin(image):
            self.clear()
            return
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
            painter.scale(scale, scale)
            if not self._items:
                painter.setPen(QColor("#66736b"))
                painter.drawText(image.rect(), Qt.AlignmentFlag.AlignCenter,
                                 "Faça uma consulta para gerar o gráfico.")
            elif self._chart_type == "pie":
                self.paint_pie_image(painter, width, height)
            else:
                self.paint_cartesian_image(painter, width, height)
        finally:
            painter.end()
        pixmap = QPixmap.fromImage(image)
        pixmap.setDevicePixelRatio(scale)
        self.setPixmap(pixmap)

    def paint_cartesian_image(self, painter, image_width, image_height):
        comparison = len(self._items[0]) == 3
        series = list(dict.fromkeys(
            item[2] for item in self._items if len(item) == 3
        ))
        left = 58
        right = 24
        top = 48 if comparison else 24
        bottom = 96
        width = max(1, image_width - left - right)
        height = max(1, image_height - top - bottom)
        maximum = max(float(item[1] or 0) for item in self._items) or 1.0
        categories = list(dict.fromkeys(item[0] for item in self._items))
        slot = width / max(1, len(categories))
        group_width = slot * (0.80 if comparison else 0.72)
        bar_width = group_width / max(1, len(series) if comparison else 1)
        painter.setPen(QColor("#cbd4ce"))
        painter.drawLine(left, top + height, left + width, top + height)
        points = []
        for item in self._items:
            label, value = item[0], float(item[1] or 0)
            category_index = categories.index(label)
            series_index = series.index(item[2]) if comparison else 0
            x = left + category_index * slot + (slot - group_width) / 2 + series_index * bar_width
            # Keep a dedicated band above the tallest bar for its value.
            value_band = 30
            drawable_height = max(1, height - value_band)
            bar_height = max(0.0, drawable_height * value / maximum)
            y = top + height - bar_height
            color = QColor(self.COLORS[series_index % 2])
            if self._chart_type == "line":
                points.append((x + bar_width / 2, y))
            else:
                painter.fillRect(int(x), int(y), max(1, int(bar_width)),
                                 max(0, int(bar_height)), color)
            painter.setPen(QColor("#24342b"))
            value_text = self.format_value(value)
            value_width = max(
                int(bar_width),
                painter.fontMetrics().horizontalAdvance(value_text) + 12,
            )
            value_x = int(x + (bar_width - value_width) / 2)
            painter.drawText(
                value_x,
                max(top, int(y) - 22),
                value_width,
                20,
                Qt.AlignmentFlag.AlignCenter,
                value_text,
            )
            if series_index == 0:
                painter.drawText(int(left + category_index * slot), top + height + 6,
                                 max(1, int(slot)), 58,
                                 Qt.AlignmentFlag.AlignHCenter | Qt.TextFlag.TextWordWrap, str(label))
        if comparison:
            legend_x = left
            for index, name in enumerate(series):
                legend_y = 10
                legend_text = str(name)
                text_width = painter.fontMetrics().horizontalAdvance(
                    legend_text
                )
                painter.fillRect(
                    int(legend_x), legend_y + 2, 14, 14,
                    QColor(self.COLORS[index % 2]),
                )
                painter.drawText(
                    int(legend_x) + 22,
                    legend_y,
                    max(1, text_width + 6),
                    20,
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    legend_text,
                )
                legend_x += text_width + 52
        if self._chart_type == "line" and points:
            painter.setPen(QColor("#832413"))
            for first, second in zip(points, points[1:]):
                painter.drawLine(int(first[0]), int(first[1]), int(second[0]), int(second[1]))
            painter.setBrush(QColor("#832413"))
            for x, y in points:
                painter.drawEllipse(int(x - 4), int(y - 4), 8, 8)

    def paint_pie_image(self, painter, width, height):
        total = sum(float(item[1] or 0) for item in self._items)
        if total <= 0:
            return
        diameter = min(height - 50, width * 0.54)
        pie_rect = QRectF(18, 22, diameter, diameter)
        start_angle = 90 * 16
        for index, item in enumerate(self._items):
            value = float(item[1] or 0)
            span = int(-360 * 16 * value / total)
            painter.setBrush(self.slice_color(index, item[0]))
            painter.setPen(QColor("#ffffff"))
            painter.drawPie(pie_rect, start_angle, span)
            start_angle += span
        legend_x = int(pie_rect.right() + 22)
        painter.setPen(QColor("#24342b"))
        for index, item in enumerate(self._items):
            label, value = item[0], float(item[1] or 0)
            y = 24 + index * 24
            painter.fillRect(legend_x, y, 14, 14,
                             self.slice_color(index, label))
            painter.drawText(legend_x + 20, y - 2, max(90, width - legend_x - 10),
                             20, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                             "{} — {}".format(label, self.format_value(value)))


class CollapsibleSection(QWidget):
    """
    Collapsible section of the interface.
    """

    def __init__(
        self,
        title,
        expanded=True,
        parent=None,
    ):
        super().__init__(parent)

        self.toggle_button = QToolButton()
        self.toggle_button.setObjectName(
            "sectionButton"
        )
        self.toggle_button.setText(
            title.upper()
        )
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(expanded)
        self.toggle_button.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        self.toggle_button.setArrowType(
            Qt.ArrowType.DownArrow
            if expanded
            else Qt.ArrowType.RightArrow
        )
        self.toggle_button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.toggle_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        title_font = self.toggle_button.font()
        title_font.setBold(True)
        self.toggle_button.setFont(title_font)

        self.content_widget = QWidget()
        self.content_widget.setObjectName(
            "sectionContent"
        )
        self.content_widget.setVisible(
            expanded
        )

        self.content_layout = QVBoxLayout(
            self.content_widget
        )
        self.content_layout.setContentsMargins(
            16,
            10,
            16,
            16,
        )
        self.content_layout.setSpacing(9)

        card = QFrame()
        card.setObjectName(
            "sectionCard"
        )

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        card_layout.setSpacing(0)
        # The title button sits inside its own QHBoxLayout (instead of
        # going straight into card_layout) to leave room for an optional
        # help icon in the header — see add_help_icon().
        self.header_layout = QHBoxLayout()
        self.header_layout.setContentsMargins(0, 0, 0, 0)
        self.header_layout.setSpacing(4)
        self.header_layout.addWidget(
            self.toggle_button
        )
        # One-line summary of the section's choices, shown only while the
        # section is collapsed (proposal v2), so a closed section still
        # tells what it is filtering.
        self.summary_label = QLabel("")
        self.summary_label.setObjectName("sectionSummaryLabel")
        self.summary_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self.summary_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.summary_label.setVisible(False)
        self.header_layout.addWidget(self.summary_label, 1)
        card_layout.addLayout(
            self.header_layout
        )
        card_layout.addWidget(
            self.content_widget
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        layout.addWidget(card)

        self.toggle_button.clicked.connect(
            self.toggle_content
        )

    def add_help_icon(self, icon):
        """Adds a help icon ("i") next to the section title, for
        sections with no specific field to attach it to."""
        icon.setStyleSheet(
            "color: #59666b; font-size: 10px; font-weight: 700; "
            "background: transparent;"
        )
        icon.setFixedWidth(20)
        self.header_layout.addWidget(icon)

    def set_summary(self, text):
        self._summary_text = text or ""
        self.summary_label.setToolTip(self._summary_text)
        self._refresh_summary()

    def _refresh_summary(self):
        text = getattr(self, "_summary_text", "")
        collapsed = not self.toggle_button.isChecked()
        width = max(40, self.summary_label.width() - 8)
        self.summary_label.setText(
            self.summary_label.fontMetrics().elidedText(
                text, Qt.TextElideMode.ElideRight, width
            )
        )
        self.summary_label.setVisible(bool(text) and collapsed)
        if collapsed and text and not getattr(self, "_summary_pending", False):
            # The label only gets its real width after this layout pass.
            self._summary_pending = True
            QTimer.singleShot(0, self._refresh_summary_later)

    def _refresh_summary_later(self):
        self._summary_pending = False
        text = getattr(self, "_summary_text", "")
        width = max(40, self.summary_label.width() - 8)
        self.summary_label.setText(
            self.summary_label.fontMetrics().elidedText(
                text, Qt.TextElideMode.ElideRight, width
            )
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if getattr(self, "_summary_text", ""):
            self._refresh_summary()

    def toggle_content(
        self,
        checked,
    ):
        self.content_widget.setVisible(
            checked
        )
        self._refresh_summary()

        self.toggle_button.setArrowType(
            Qt.ArrowType.DownArrow
            if checked
            else Qt.ArrowType.RightArrow
        )

    def set_expanded(self, expanded):
        self.toggle_button.blockSignals(True)
        self.toggle_button.setChecked(expanded)
        self.toggle_button.blockSignals(False)
        self.toggle_content(expanded)

    def add_widget(
        self,
        widget,
    ):
        self.content_layout.addWidget(
            widget
        )

    def add_layout(
        self,
        layout,
    ):
        self.content_layout.addLayout(
            layout
        )


class MapBiomasAlertDockWidget(QDockWidget):
    """
    Main panel of the plugin.
    """

    closing_plugin = pyqtSignal()
    # Above this, the search shows a warning (non-blocking) that it may
    # take a while — see update_search_progress/search_alerts. Downloading
    # the geometry of many alerts is what costs the most, both in wait
    # time and in load on the API.
    LARGE_SEARCH_WARNING_THRESHOLD = 5000
    # Hard limit on the search period — above this, the search is blocked
    # and the person needs to shrink the interval or run more than one
    # search (one per year, for instance). 366 instead of 365 so it
    # doesn't block an "exactly 1 year" period that falls on a leap year.
    MAX_SEARCH_PERIOD_DAYS = 366

    def __init__(
        self,
        iface=None,
        parent=None,
    ):
        self.iface = iface

        if (
            parent is None
            and iface is not None
        ):
            parent = iface.mainWindow()

        super().__init__(
            "MapBiomas Alerta Oficial",
            parent,
        )

        self.setObjectName(
            "MapBiomasAlertaOficialDockWidget"
        )

        self.setMinimumWidth(270)
        # A minimum height helps QGIS avoid squeezing the panel to the
        # point where the search button (fixed at the bottom, outside the
        # scrollable area) gets almost entirely clipped by the window edge
        # on short screens.
        self.setMinimumHeight(420)
        self.resize(self.preferred_width(), 720)
        self.responsive_forms = []
        self._compact_height = False
        self._responsive_geometry_pending = False
        self._responsive_geometry_passes = 0

        self.plugin_directory = (
            os.path.dirname(
                os.path.abspath(__file__)
            )
        )

        self.icon_path = os.path.join(
            self.plugin_directory,
            "icon.png",
        )

        self.api_client = MapBiomasApiClient(
            country_config("BR")
        )

        self.current_result_layer_id = None
        self.result_layer_ids = []
        self.result_contexts = {}
        self.result_temporary_files = {}
        self.territory_rows_by_layer = {}
        # Tracks which territorial categories have already been normalized
        # (JSON decoded, rows built) per layer — see
        # normalize_territory_area_rows(). Lets us compute only the
        # category(ies) actually requested instead of always recomputing
        # all ~18 categories at once.
        self.territory_categories_done = {}
        # QGIS message bar item used to mirror the search progress (see
        # update_search_progress/show_progress_message) — the bar sits at
        # the top of the window, outside the panel, so the text is never
        # clipped due to screen height.
        self._progress_message_item = None
        # Cache of the already computed rows of the "Query layer
        # comparison" table (total, largest alert, municipality...).
        # Without this, every new search would recompute all existing
        # layers in the session from scratch, not just the new one.
        # Result layers are immutable once created, so the cache never
        # goes stale; it's only invalidated when the layer is removed.
        self.layer_comparison_cache = {}
        # Alert code → feature id index, per layer — used by
        # feature_by_alert_code() to avoid repeated linear search (e.g.
        # once per "other alerts on the same property" card).
        self.alert_code_index_by_layer = {}
        self.alert_order_by_layer = {}
        self.alert_position_by_layer = {}
        # Plugin's own translation system (independent of QGIS's locale)
        # — see translations.py. self._language_locked becomes True as
        # soon as the person manually picks a language, so switching
        # country afterward doesn't override that choice.
        self.migrate_legacy_settings()
        self.translator = Translator("pt")
        self._language_locked = False
        self._translatable_widgets = []
        self.project_signals_connected = False
        self._shutdown_complete = False
        self.identify_tool = None
        self.current_detail_alert_code = None
        self.same_property_cache = None
        self.same_property_related_loaded = False
        self.related_alert_layer_id = None
        self._chart_processing = False

        self.setup_ui()
        self.apply_styles()
        self.connect_signals()
        self.connect_project_signals()

        self.update_platform()
        self.refresh_vector_layers()
        self.update_area_controls()
        self.update_result_controls()
        self.update_responsive_layout()
        QTimer.singleShot(0, self.fit_to_screen)

    def tr(self, text, *format_args):
        """Shortcut for self.translator.tr — used throughout the interface."""
        return self.translator.tr(text, *format_args)

    def register_translatable(
        self, widget, text, setter="setText", *format_args, transform=None
    ):
        """Applies the current translation to a widget and keeps a
        reference to reapply it when the language changes (see
        retranslate_ui). `text` is always in Portuguese — it's the
        translation lookup key. `transform`, if given, runs on top of
        the translated text (e.g. str.upper for CollapsibleSection
        titles)."""
        translated = self.tr(text, *format_args)
        if transform is not None:
            translated = transform(translated)
        getattr(widget, setter)(translated)
        self._translatable_widgets.append(
            (widget, text, setter, format_args, transform)
        )
        return widget

    def update_top_municipality_title(self):
        if not hasattr(self, "top_municipality_title"):
            return
        if not hasattr(self, "api_client"):
            return
        municipality_label = self.tr(self.api_client.country.get(
            "municipality_label", "Município"
        ))
        self.top_municipality_title.setText(
            self.tr("{} com maior área", municipality_label)
        )

    def comparison_table_header_labels(self):
        municipality_label = self.tr(self.api_client.country.get(
            "municipality_label", "Município"
        ))
        return [
            self.tr("Camada"),
            self.tr("Alertas"),
            self.tr("Área total"),
            self.tr("Maior alerta"),
            self.tr("Código"),
            self.tr(
                "{} com maior área", municipality_label
            ),
            self.tr("Tipo de data"),
            self.tr("Período"),
        ]

    def retranslate_ui(self):
        """Reapplies the current translation to every registered widget —
        called when the person switches the language via the plugin's
        selector."""
        if hasattr(self, "_translatable_tab_titles"):
            self.apply_tab_translations()
        if hasattr(self, "_translatable_combo_items"):
            self.apply_combo_item_translations()
        if hasattr(self, "_comparison_table_headers") or hasattr(
            self, "layer_comparison_table"
        ):
            self.layer_comparison_table.setHorizontalHeaderLabels(
                self.comparison_table_header_labels()
            )
        self.update_top_municipality_title()
        if hasattr(self, "crossing_field_combo") and hasattr(
            self, "api_client"
        ):
            # The crossing combo is rebuilt from scratch (it's not a
            # static text widget), so it needs to be redone to apply the
            # new language. WARNING: this runs during the country/language
            # switch (update_platform), possibly BEFORE login actually
            # finishes — if the session isn't authenticated yet,
            # crossing_availability() tries and fails, but it does not
            # cache that result (see the comment there), so the following
            # call to populate_crossing_options() from login_api(), once
            # authenticated, works normally.
            self.populate_crossing_options()
        for entry in self._translatable_widgets:
            widget, text, setter, format_args, transform = entry
            try:
                translated = self.tr(text, *format_args)
                if transform is not None:
                    translated = transform(translated)
                getattr(widget, setter)(translated)
            except RuntimeError:
                # Widget already destroyed (e.g. tab recreated) — skip.
                continue
        # Buttons whose text changes based on state (can't be covered by
        # the static fixed-text registration alone).
        if hasattr(self, "toggle_password_button"):
            self.toggle_password_button.setText(
                self.tr(
                    "Ocultar"
                    if self.toggle_password_button.isChecked()
                    else "Mostrar"
                )
            )
        if hasattr(self, "accept_notice_button"):
            accepted = (
                self.country_notice_accepted()
                if hasattr(self, "country_notice_accepted")
                else False
            )
            self.accept_notice_button.setText(
                self.tr("NOTA ACEITA")
                if accepted
                else self.tr("LI E CONCORDO")
            )
        if hasattr(self, "source_combo"):
            self.source_combo.default_text = self.tr("Todas as fontes")
            self.source_combo.update_text()
        if hasattr(self, "api_access_help_icon"):
            self.update_api_access_help_text()

    def update_api_access_help_text(self):
        """Builds the "Acesso à API" help icon's text — it depends both
        on the language (explanatory text) and on the selected country
        (sign-up link), so it's called separately on language change
        (retranslate_ui) and on country change (update_platform),
        instead of using register_translatable (which only reacts to
        language changes)."""
        platform_url = self.api_client.country.get("platform_url") or ""
        text = self.tr(
            "Para acessar a API é necessário ter um login cadastrado "
            "na plataforma MapBiomas Alerta do país selecionado. Se "
            "ainda não tiver uma conta, cadastre-se no site oficial "
            "antes de entrar aqui."
        )
        if platform_url:
            text += "\n\n" + self.tr("Acesse: {}", platform_url)
        self.api_access_help_icon.set_help_text(text)

    def refresh_dynamic_texts(self):
        """Texts set once in Portuguese (details placeholders, vector layer
        prompt) follow the current language too."""
        if (
            hasattr(self, "detail_status_label")
            and getattr(self, "current_detail_alert_code", None) is None
        ):
            try:
                self.clear_alert_details()
            except (RuntimeError, AttributeError):
                pass
        if hasattr(self, "vector_layer_combo") and self.vector_layer_combo.count():
            if self.vector_layer_combo.itemData(0) is None:
                self.vector_layer_combo.setItemText(
                    0, self.tr("Selecione uma camada vetorial")
                )

    def on_language_changed(self):
        language = self.language_combo.currentData()
        if not language:
            return
        self._language_locked = True
        self.translator.set_language(language)
        self.retranslate_ui()
        # Texts built on the fly (area hint, search button, section
        # summaries) are refreshed too, not only the registered widgets.
        if hasattr(self, "area_country_radio"):
            self.update_area_controls()
        if hasattr(self, "search_button"):
            self.update_auth_controls()
        self.refresh_dynamic_texts()
        # The chart field menus (and so the column names of the chart
        # exports) follow the new language too.
        layer = self.result_layer() if hasattr(self, "chart_group_combo") else None
        if layer is not None:
            try:
                self.populate_chart_fields(layer)
            except (RuntimeError, AttributeError):
                pass
        for button_name in ("notice_shortcut_button", "expand_chart_button"):
            button = getattr(self, button_name, None)
            if button is not None:
                button.setMinimumWidth(0)
                button.setMinimumWidth(button.sizeHint().width())
        if hasattr(self, "update_responsive_layout"):
            self.update_responsive_layout()

    def preferred_width(self):
        """Return a compact width scaled to the monitor's available space."""
        try:
            available_width = self.screen().availableGeometry().width()
        except (AttributeError, RuntimeError):
            available_width = 1920
        return max(280, min(340, int(available_width * 0.17)))

    def fit_to_screen(self):
        """Apply the responsive width after QGIS has docked the widget."""
        target_width = self.preferred_width()
        parent = (
            self.iface.mainWindow()
            if self.iface is not None else self.parentWidget()
        )
        try:
            parent.resizeDocks([self], [target_width], Qt.Orientation.Horizontal)
        except (AttributeError, RuntimeError):
            self.resize(target_width, self.height())

    def setup_ui(self):
        container = QWidget()
        self.main_container = container
        container.setObjectName(
            "mainContainer"
        )
        container.setMinimumWidth(0)
        container.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)

        self.setWidget(container)

        root_layout = QVBoxLayout(
            container
        )
        self.root_layout = root_layout
        root_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        root_layout.setSpacing(0)

        self.vertical_splitter = QSplitter(Qt.Orientation.Vertical)
        self.vertical_splitter.setChildrenCollapsible(False)
        self.vertical_splitter.setHandleWidth(0)
        root_layout.addWidget(self.vertical_splitter)

        self.create_header(self.vertical_splitter)
        self.create_tabs(self.vertical_splitter)
        self.vertical_splitter.setStretchFactor(0, 0)
        self.vertical_splitter.setStretchFactor(1, 1)

    def create_header(
        self,
        parent_layout,
    ):
        header = QFrame()
        self.header_frame = header
        header.setObjectName(
            "headerFrame"
        )
        header.setMinimumWidth(0)
        header.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(header)
        layout.setContentsMargins(
            14,
            6,
            14,
            8,
        )
        layout.setSpacing(2)

        self.logo_label = QLabel()
        self.logo_label.setObjectName(
            "logoLabel"
        )
        self.logo_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.logo_label.setMinimumHeight(
            46
        )

        if os.path.exists(
            self.icon_path
        ):
            pixmap = QPixmap(
                self.icon_path
            )

            if not pixmap.isNull():
                self.logo_label.setPixmap(
                    pixmap.scaled(
                        46,
                        46,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
            else:
                self.logo_label.hide()
        else:
            self.logo_label.hide()

        self.title_label = QLabel(
            "MapBiomas Alerta\nOficial"
        )
        self.title_label.setObjectName(
            "titleLabel"
        )
        self.title_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.title_label.setWordWrap(
            True
        )
        self.title_label.setStyleSheet(
            "color: #832413; font-size: 16px; font-weight: 700;"
        )
        title_font = self.title_label.font()
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        title_palette = self.title_label.palette()
        title_palette.setColor(QPalette.ColorRole.WindowText, QColor("#832413"))
        self.title_label.setPalette(title_palette)

        self.subtitle_label = QLabel(
            "Consulta e análise de alertas "
            "de desmatamento no QGIS"
        )
        self.register_translatable(
            self.subtitle_label,
            "Consulta e análise de alertas de desmatamento no QGIS",
        )
        self.subtitle_label.setObjectName(
            "subtitleLabel"
        )
        self.subtitle_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.subtitle_label.setWordWrap(
            True
        )

        brand_layout = QHBoxLayout()
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(8)
        brand_layout.addStretch()
        brand_layout.addWidget(self.logo_label)
        brand_layout.addWidget(self.title_label)
        brand_layout.addStretch()
        layout.addLayout(brand_layout)
        layout.addWidget(
            self.subtitle_label
        )

        selectors = QFormLayout()
        self.header_selectors_form = selectors
        self.responsive_forms.append(selectors)
        selectors.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        selectors.setContentsMargins(
            0,
            4,
            0,
            0,
        )
        selectors.setHorizontalSpacing(
            14
        )
        selectors.setVerticalSpacing(
            4
        )

        self.country_combo = FocusComboBox()
        for code, config in country_items():
            self.country_combo.addItem(
                config["name"],
                code,
            )
            self.register_combo_item(
                self.country_combo,
                self.country_combo.count() - 1,
                config["name"],
            )

        self.platform_value_label = QLabel()
        self.platform_value_label.setObjectName(
            "platformValueLabel"
        )
        self.platform_value_label.setWordWrap(
            True
        )

        self.country_field_label = QLabel("Country")
        self.country_field_label.setStyleSheet("font-weight: 700;")
        country_font = self.country_field_label.font()
        country_font.setBold(True)
        self.country_field_label.setFont(country_font)
        # "Country" and "Language" (right below) are intentionally fixed
        # in English, without going through self.tr() — they're the only
        # two labels the person needs to recognize BEFORE picking a
        # language. If they defaulted to Portuguese, someone who only
        # reads Spanish or English would have no way to even find the
        # language selector to switch it. Same logic already used for the
        # language names in the combo ("Português"/"Español"/"English",
        # each written in its own language).
        selectors_grid = QGridLayout()
        selectors_grid.setContentsMargins(0, 4, 0, 0)
        selectors_grid.setHorizontalSpacing(10)
        selectors_grid.setVerticalSpacing(3)
        selectors_grid.addWidget(self.country_field_label, 0, 0)
        selectors_grid.addWidget(self.country_combo, 1, 0)

        self.language_combo = FocusComboBox()
        for code, name in LANGUAGES:
            self.language_combo.addItem(name, code)
        self.language_combo.currentIndexChanged.connect(
            self.on_language_changed
        )
        self.language_field_label = QLabel("Language")
        self.language_field_label.setStyleSheet("font-weight: 700;")
        language_font = self.language_field_label.font()
        language_font.setBold(True)
        self.language_field_label.setFont(language_font)
        selectors_grid.addWidget(self.language_field_label, 0, 1)
        selectors_grid.addWidget(self.language_combo, 1, 1)
        selectors_grid.setColumnStretch(0, 1)
        selectors_grid.setColumnStretch(1, 1)
        layout.addLayout(selectors_grid)

        self.notice_shortcut_button = AutoFitPushButton("NOTA INFORMATIVA")
        self.register_translatable(
            self.notice_shortcut_button, "NOTA INFORMATIVA"
        )
        self.notice_shortcut_button.setToolTip(
            self.tr(
                "Consultar novamente a nota informativa do país "
                "selecionado."
            )
        )
        self.register_translatable(
            self.notice_shortcut_button,
            "Consultar novamente a nota informativa do país selecionado.",
            "setToolTip",
        )
        self.notice_shortcut_button.setObjectName("linkButton")
        self.notice_shortcut_button.setFlat(True)
        self.notice_shortcut_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.notice_shortcut_button.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        platform_container = QWidget()
        platform_container.setMinimumWidth(0)
        platform_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight, platform_container)
        self.platform_layout = platform_layout
        platform_layout.setContentsMargins(0, 0, 0, 0)
        platform_layout.setSpacing(8)
        platform_layout.addWidget(self.platform_value_label, 1)
        platform_layout.addWidget(self.notice_shortcut_button)
        self.platform_field_label = QLabel("Plataforma")
        self.platform_field_label.setStyleSheet("font-weight: 700;")
        platform_font = self.platform_field_label.font()
        platform_font.setBold(True)
        self.platform_field_label.setFont(platform_font)
        self.register_translatable(self.platform_field_label, "Plataforma")
        self.platform_field_label.setVisible(False)
        selectors.addRow(platform_container)

        layout.addLayout(selectors)

        self.login_section = CollapsibleSection(
            "Acesso à API",
            expanded=True,
        )
        self.register_translatable(
            self.login_section.toggle_button,
            "Acesso à API",
            transform=str.upper,
        )
        self.api_access_help_icon = HelpIconLabel("")
        self.api_access_help_icon.setAccessibleName("Informação")
        self.api_access_help_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.login_section.add_help_icon(self.api_access_help_icon)
        # This icon's text depends on the country (sign-up link) in
        # addition to the language — unlike the other help icons, which
        # only change with the language. That's why it doesn't use
        # register_translatable directly; update_api_access_help_text()
        # is called both on language change (on_language_changed) and on
        # country change (update_platform), building the final text on
        # the spot.
        self.update_api_access_help_text()
        self.login_section.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self.login_section.content_widget.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self.login_section.toggle_button.toggled.connect(
            lambda _checked: QTimer.singleShot(
                0, self.update_responsive_layout
            )
        )
        self.login_section.content_layout.setContentsMargins(10, 6, 10, 8)
        self.login_section.content_layout.setSpacing(5)
        self.login_form_widget = QWidget()
        self.login_form_widget.setMinimumWidth(0)
        self.login_form_widget.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        login_form = QFormLayout(self.login_form_widget)
        self.login_form = login_form
        self.responsive_forms.append(login_form)
        login_form.setContentsMargins(0, 0, 0, 0)
        login_form.setHorizontalSpacing(8)
        login_form.setVerticalSpacing(4)
        login_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        self.email_edit = QLineEdit()
        self.email_edit.setMinimumWidth(0)
        self.email_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.email_edit.setPlaceholderText("E-mail da conta MapBiomas Alerta")
        self.register_translatable(
            self.email_edit,
            "E-mail da conta MapBiomas Alerta",
            "setPlaceholderText",
        )
        self.password_edit = QLineEdit()
        self.password_edit.setMinimumWidth(0)
        self.password_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("Senha")
        self.register_translatable(
            self.password_edit, "Senha", "setPlaceholderText"
        )
        self.toggle_password_button = QToolButton()
        self.toggle_password_button.setText(self.tr("Mostrar"))
        self.toggle_password_button.setCheckable(True)
        self.toggle_password_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_password_button.setToolTip("Mostrar/ocultar senha")
        self.register_translatable(
            self.toggle_password_button,
            "Mostrar/ocultar senha",
            "setToolTip",
        )
        self.toggle_password_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.toggle_password_button.toggled.connect(
            self.toggle_password_visibility
        )
        password_row_widget = QWidget()
        password_row_widget.setMinimumWidth(0)
        password_row_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        password_row_layout = QHBoxLayout(password_row_widget)
        password_row_layout.setContentsMargins(0, 0, 0, 0)
        password_row_layout.setSpacing(4)
        password_row_layout.addWidget(self.password_edit)
        password_row_layout.addWidget(self.toggle_password_button)
        email_field_label = QLabel("E-mail")
        self.register_translatable(email_field_label, "E-mail")
        password_field_label = QLabel("Senha")
        self.register_translatable(password_field_label, "Senha")
        login_form.addRow(email_field_label, self.email_edit)
        login_form.addRow(password_field_label, password_row_widget)
        self.login_section.add_widget(self.login_form_widget)

        self.remember_login_checkbox = QCheckBox(
            "Salvar acesso no QGIS"
        )
        self.register_translatable(
            self.remember_login_checkbox, "Salvar acesso no QGIS"
        )
        self.remember_login_checkbox.setMinimumWidth(0)
        self.remember_login_checkbox.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed
        )
        self.remember_login_checkbox.setToolTip(
            "As credenciais serão protegidas pelo Gerenciador "
            "de Autenticação do QGIS."
        )
        self.register_translatable(
            self.remember_login_checkbox,
            "As credenciais serão protegidas pelo Gerenciador "
            "de Autenticação do QGIS.",
            "setToolTip",
        )
        self.login_section.add_widget(self.remember_login_checkbox)

        login_buttons = QHBoxLayout()
        self.login_buttons_layout = login_buttons
        self.login_button = AutoFitPushButton("ENTRAR NA API")
        self.register_translatable(self.login_button, "ENTRAR NA API")
        self.logout_button = QPushButton("SAIR")
        self.register_translatable(self.logout_button, "SAIR")
        self.login_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.logout_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.logout_button.setEnabled(False)
        login_buttons.addWidget(self.login_button)
        login_buttons.addWidget(self.logout_button)
        self.login_section.add_layout(login_buttons)

        self.login_status_label = QLabel("API desconectada")
        self.register_translatable(
            self.login_status_label, "API desconectada"
        )
        self.login_status_label.setObjectName("informationLabel")
        self.login_status_label.setStyleSheet("font-weight: 700;")
        api_font = self.login_status_label.font()
        api_font.setBold(True)
        self.login_status_label.setFont(api_font)
        layout.addWidget(self.login_status_label)
        layout.addWidget(self.login_section)

        parent_layout.addWidget(header)

    def create_tabs(
        self,
        parent_layout,
    ):
        self.tabs = ResponsiveTabWidget()
        self.tabs.setTabBar(ReadableTabBar(self.tabs))
        self.tabs.setObjectName(
            "mainTabs"
        )
        self.tabs.setMinimumWidth(0)
        self.tabs.setMinimumHeight(120)
        self.tabs.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.tabs.setDocumentMode(
            True
        )
        # Every tab visible at once (no scroll arrows); tabs share the
        # width and only elide text on very narrow docks.
        self.tabs.tabBar().setUsesScrollButtons(False)
        self.tabs.tabBar().setElideMode(Qt.TextElideMode.ElideRight)
        self.tabs.tabBar().setExpanding(True)

        self.notice_tab = self.make_scrollable_tab(
            self.create_notice_tab()
        )

        self.filters_tab = (
            self.create_filters_tab()
        )

        self.layers_tab = self.make_scrollable_tab(
            self.create_layers_tab()
        )

        self.results_tab = self.make_scrollable_tab(
            self.create_results_tab()
        )

        self.details_tab = self.make_scrollable_tab(
            self.create_details_tab()
        )

        self.charts_tab = self.make_scrollable_tab(
            self.create_charts_tab()
        )

        self.tabs.addTab(
            self.notice_tab,
            "Nota informativa",
        )

        self.tabs.addTab(
            self.filters_tab,
            "Filtros",
        )

        self.tabs.addTab(
            self.layers_tab,
            "Camadas",
        )

        self.tabs.addTab(self.results_tab, "Estatísticas")
        self.tabs.addTab(self.charts_tab, "Gráficos")
        self.tabs.addTab(self.details_tab, "Detalhes")

        self._translatable_tab_titles = [
            (self.tabs, self.notice_tab, "Nota informativa"),
            (self.tabs, self.filters_tab, "Filtros"),
            (self.tabs, self.layers_tab, "Camadas"),
            (self.tabs, self.results_tab, "Estatísticas"),
            (self.tabs, self.charts_tab, "Gráficos"),
            (self.tabs, self.details_tab, "Detalhes"),
        ]
        self.apply_tab_translations()

        parent_layout.addWidget(self.tabs)

    def apply_tab_translations(self):
        for tab_widget, page, text in getattr(
            self, "_translatable_tab_titles", []
        ):
            index = tab_widget.indexOf(page)
            if index >= 0:
                tab_widget.setTabText(index, self.tr(text))

    def create_notice_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)

        title = QLabel("Nota informativa")
        title.setObjectName("tabTitleLabel")
        self.register_translatable(title, "Nota informativa")
        layout.addWidget(title)

        self.notice_country_label = QLabel()
        self.notice_country_label.setObjectName("informationTitleLabel")
        layout.addWidget(self.notice_country_label)

        self.notice_browser = QTextBrowser()
        self.notice_browser.setOpenExternalLinks(True)
        self.notice_browser.setReadOnly(True)
        # The tab sits inside a QScrollArea (see make_scrollable_tab,
        # applied by whoever creates this tab), ensuring the checkbox and
        # the "LI E CONCORDO" button remain reachable by scrolling on
        # small screens. The minimum height here keeps the notice
        # comfortable to read.
        self.notice_browser.setMinimumHeight(220)
        layout.addWidget(self.notice_browser, 1)

        self.notice_checkbox = QCheckBox(
            "Li e compreendi esta nota informativa."
        )
        self.register_translatable(
            self.notice_checkbox, "Li e compreendi esta nota informativa."
        )
        self.notice_checkbox.setMinimumWidth(0)
        self.notice_checkbox.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.notice_checkbox)

        self.accept_notice_button = AutoFitPushButton("LI E CONCORDO")
        self.accept_notice_button.setEnabled(False)
        layout.addWidget(self.accept_notice_button)
        return tab

    @staticmethod
    def make_scrollable_tab(content):
        scroll = QScrollArea()
        scroll.setMinimumWidth(0)
        scroll.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # The content follows the dock's width. A 500 px minimum used to force
        # horizontal scrolling and mess up the controls on smaller monitors.
        content.setMinimumWidth(0)
        content.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        scroll.setWidget(content)
        return scroll

    def create_filters_tab(self):
        tab = QWidget()

        tab_layout = QVBoxLayout(
            tab
        )
        tab_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.filters_scroll = QScrollArea()
        self.filters_scroll.setObjectName("filtersScroll")
        self.filters_scroll.setWidgetResizable(
            True
        )
        self.filters_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )
        self.filters_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.filters_scroll.setFrameShape(
            QFrame.Shape.NoFrame
        )

        content = QWidget()
        content.setMinimumWidth(0)
        content.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        content.setObjectName(
            "scrollContent"
        )

        layout = QVBoxLayout(
            content
        )
        layout.setContentsMargins(
            14,
            14,
            14,
            18,
        )
        layout.setSpacing(12)

        self.area_section = self.create_area_section()
        self.period_section = self.create_period_section()
        self.filter_section = self.create_filter_section()
        self.crossing_section = self.create_crossing_section()
        layout.addWidget(self.area_section)
        layout.addWidget(self.period_section)
        layout.addWidget(self.filter_section)
        layout.addWidget(self.crossing_section)

        self.search_button = AutoFitPushButton(
            "BUSCAR ALERTAS"
        )
        self.search_button.setObjectName(
            "searchButton"
        )
        self.search_button.setMinimumHeight(
            38
        )
        self.search_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.search_button.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        # The stylesheet applied directly on the button takes precedence
        # over QGIS's global themes and keeps the primary action red in
        # every state, including during the search.
        self.search_button.setStyleSheet(
            "QPushButton {"
            " background-color: #832413; color: white; border: none;"
            " border-radius: 6px; font-size: 13px; font-weight: 700;"
            " padding: 4px 12px; min-height: 32px;"
            "}"
            "QPushButton:hover { background-color: #9B2C1B; }"
            "QPushButton:pressed { background-color: #6F1E10; }"
            "QPushButton:disabled {"
            " background-color: #6F1E10; color: #F7EDEA; border: none;"
            "}"
        )

        layout.addStretch()

        self.filters_scroll.setWidget(content)

        tab_layout.addWidget(
            self.filters_scroll
        )

        actions_frame = QFrame()
        actions_frame.setObjectName("filterActionsFrame")
        self.filter_actions_frame = actions_frame
        actions_layout = QVBoxLayout(actions_frame)
        actions_layout.setContentsMargins(14, 8, 14, 10)
        actions_layout.setSpacing(6)

        self.filter_summary_label = QLabel()
        self.filter_summary_label.setObjectName("filterSummaryLabel")
        self.filter_summary_label.setWordWrap(True)
        actions_layout.addWidget(self.filter_summary_label)

        buttons_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self.filter_buttons_layout = buttons_layout
        self.clear_filters_button = QPushButton("LIMPAR")
        self.register_translatable(self.clear_filters_button, "LIMPAR")
        self.clear_filters_button.setObjectName("clearFiltersButton")
        self.cancel_search_button = QPushButton("CANCELAR")
        self.register_translatable(self.cancel_search_button, "CANCELAR")
        self.clear_filters_button.setMinimumWidth(82)
        self.clear_filters_button.setMinimumHeight(38)
        self.cancel_search_button.setMinimumWidth(82)
        self.cancel_search_button.setMinimumHeight(38)
        self.search_button.setMinimumWidth(145)
        self.filter_secondary_action_stack = QStackedWidget()
        self.filter_secondary_action_stack.setMinimumWidth(82)
        self.filter_secondary_action_stack.setMinimumHeight(38)
        self.filter_secondary_action_stack.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self.filter_secondary_action_stack.addWidget(
            self.clear_filters_button
        )
        self.filter_secondary_action_stack.addWidget(
            self.cancel_search_button
        )
        self.filter_secondary_action_stack.setCurrentWidget(
            self.clear_filters_button
        )
        buttons_layout.setSpacing(8)
        self.quick_view_checkbox = QCheckBox(
            "Visualização rápida no mapa"
        )
        self.register_translatable(
            self.quick_view_checkbox,
            "Visualização rápida no mapa",
        )
        self.quick_view_checkbox.setChecked(False)
        self._quick_view_state = None
        self.register_translatable(
            self.quick_view_checkbox, QUICK_VIEW_HELP, "setToolTip"
        )
        self.quick_view_checkbox.setVisible(False)
        actions_layout.addWidget(self.quick_view_checkbox)

        buttons_layout.addWidget(self.filter_secondary_action_stack)
        buttons_layout.addWidget(self.search_button, 1)
        actions_layout.addLayout(buttons_layout)

        self.download_full_button = AutoFitPushButton(
            "BAIXAR ALERTAS COMPLETOS"
        )
        self.register_translatable(
            self.download_full_button, "BAIXAR ALERTAS COMPLETOS"
        )
        self.download_full_button.setMinimumHeight(34)
        # No separate download button — polygons are fetched on demand
        # (export, chart, details), see ensure_full_layer().
        self.download_full_button.setVisible(False)
        tab_layout.addWidget(actions_frame)

        return tab

    def create_area_section(self):
        section = CollapsibleSection(
            "1. Área de Interesse",
            expanded=True,
        )
        self.register_translatable(
            section.toggle_button, "1. Área de Interesse", transform=str.upper
        )
        area_help_icon = HelpIconLabel(
            self.tr(
                "Define o recorte espacial da busca: todo o país "
                "selecionado, uma camada vetorial já carregada, um "
                "ponto por coordenadas, um alerta específico pelo "
                "código, ou um imóvel rural pelo código do cadastro."
            )
        )
        self.register_translatable(
            area_help_icon,
            "Define o recorte espacial da busca: todo o país "
            "selecionado, uma camada vetorial já carregada, um ponto "
            "por coordenadas, um alerta específico pelo código, ou um "
            "imóvel rural pelo código do cadastro.",
            "set_help_text",
        )
        area_help_icon.setAccessibleName("Informação")
        area_help_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        section.add_help_icon(area_help_icon)

        self.area_country_radio = QRadioButton(
            "Todo o país selecionado"
        )
        # Short label (two per row); the full text stays as tooltip.
        self.register_translatable(self.area_country_radio, "Todo o país")
        self.register_translatable(self.area_country_radio, "Todo o país selecionado", "setToolTip")

        self.area_layer_radio = QRadioButton(
            "Extensão de uma camada vetorial"
        )
        # Short label (two per row); the full text stays as tooltip.
        self.register_translatable(self.area_layer_radio, "Camada vetorial")
        self.register_translatable(self.area_layer_radio, "Extensão de uma camada vetorial", "setToolTip")

        self.area_coordinates_radio = QRadioButton(
            "Informar coordenadas (um ponto)"
        )
        # Short label (two per row); the full text stays as tooltip.
        self.register_translatable(self.area_coordinates_radio, "Coordenada (ponto)")
        self.register_translatable(self.area_coordinates_radio, "Informar coordenadas (um ponto)", "setToolTip")

        self.area_alert_code_radio = QRadioButton(
            "Buscar por código do alerta"
        )
        # Short label (two per row); the full text stays as tooltip.
        self.register_translatable(self.area_alert_code_radio, "Código do alerta")
        self.register_translatable(self.area_alert_code_radio, "Buscar por código do alerta", "setToolTip")

        self.area_biome_radio = QRadioButton("Bioma")
        self.register_translatable(self.area_biome_radio, "Bioma")
        self.register_translatable(
            self.area_biome_radio,
            "Um ou mais biomas, sem precisar carregar uma camada vetorial.",
            "setToolTip",
        )

        self.area_car_radio = QRadioButton(
            "Buscar por imóvel rural (CAR)"
        )
        # Short label (two per row); the full text stays as tooltip.
        self.register_translatable(self.area_car_radio, "Imóvel rural (CAR)")
        self.register_translatable(self.area_car_radio, "Buscar por imóvel rural (CAR)", "setToolTip")

        self.area_button_group = QButtonGroup(
            self
        )
        self.area_button_group.setExclusive(
            True
        )

        area_buttons = (
            self.area_country_radio,
            self.area_layer_radio,
            self.area_coordinates_radio,
            self.area_alert_code_radio,
            self.area_car_radio,
        )
        area_buttons = (
            (area_buttons[0], self.area_biome_radio) + tuple(area_buttons[1:])
        )

        area_grid = QGridLayout()
        area_grid.setContentsMargins(0, 0, 0, 0)
        area_grid.setHorizontalSpacing(10)
        area_grid.setVerticalSpacing(6)
        self.area_grid = area_grid
        self.area_grid_buttons = list(area_buttons)
        self._area_grid_columns = None
        for button in area_buttons:
            self.area_button_group.addButton(
                button
            )
        self.layout_area_buttons(2)
        section.add_layout(area_grid)

        self.area_country_radio.setChecked(True)

        self.country_area_information_label = QLabel()
        self.country_area_information_label.setObjectName("informationLabel")
        self.country_area_information_label.setWordWrap(True)
        section.add_widget(self.country_area_information_label)

        self.biome_frame = QFrame()
        biome_layout = QVBoxLayout(self.biome_frame)
        biome_layout.setContentsMargins(0, 0, 0, 0)
        biome_layout.setSpacing(4)
        self.biome_combo = CheckableComboBox()
        self.biome_combo.default_text = self.tr("Selecione um ou mais biomas")
        self.register_translatable(
            self.biome_combo.lineEdit(),
            "Selecione um ou mais biomas",
            "setPlaceholderText",
        )
        self.biome_category = None
        self._biome_available = False
        biome_layout.addWidget(
            self.create_help_field(
                self.biome_combo,
                "Limita a busca aos biomas escolhidos. O recorte é feito pela "
                "própria API da plataforma, com contagem e área exatas.",
            )
        )
        self.biome_hint_label = QLabel(
            self.tr("Entre na API para carregar a lista de biomas.")
        )
        self.register_translatable(
            self.biome_hint_label,
            "Entre na API para carregar a lista de biomas.",
        )
        self.biome_hint_label.setObjectName("informationLabel")
        self.biome_hint_label.setWordWrap(True)
        biome_layout.addWidget(self.biome_hint_label)
        section.add_widget(self.biome_frame)

        self.alert_code_frame = QFrame()
        alert_code_layout = QVBoxLayout(self.alert_code_frame)
        alert_code_layout.setContentsMargins(0, 0, 0, 0)
        self.alert_code_edit = QLineEdit()
        self.alert_code_edit.setPlaceholderText("Código numérico do alerta")
        self.register_translatable(
            self.alert_code_edit,
            "Código numérico do alerta",
            "setPlaceholderText",
        )
        alert_code_form = QFormLayout()
        self.responsive_forms.append(alert_code_form)
        alert_code_field_label = QLabel("Código do alerta")
        self.register_translatable(
            alert_code_field_label, "Código do alerta"
        )
        alert_code_form.addRow(
            alert_code_field_label,
            self.create_help_field(
                self.alert_code_edit,
                "Consulta um alerta específico pelo código da plataforma. "
                "Quando preenchido, o código substitui o recorte espacial.",
            ),
        )
        alert_code_layout.addLayout(alert_code_form)
        self.alert_code_validation_label = QLabel()
        self.alert_code_validation_label.setWordWrap(True)
        self.alert_code_validation_label.setObjectName("informationLabel")
        self.alert_code_validation_label.setStyleSheet("color: #B3261E;")
        self.alert_code_validation_label.setVisible(False)
        alert_code_layout.addWidget(self.alert_code_validation_label)
        section.add_widget(self.alert_code_frame)

        self.car_code_frame = QFrame()
        car_code_layout = QVBoxLayout(self.car_code_frame)
        car_code_layout.setContentsMargins(0, 0, 0, 0)
        self.car_code_edit = QLineEdit()
        self.car_code_edit.setPlaceholderText(
            "Código completo do CAR/SICAR"
        )
        self.register_translatable(
            self.car_code_edit,
            "Código completo do CAR/SICAR",
            "setPlaceholderText",
        )
        car_code_form = QFormLayout()
        self.responsive_forms.append(car_code_form)
        car_code_field_label = QLabel("Código do CAR")
        self.register_translatable(car_code_field_label, "Código do CAR")
        car_code_form.addRow(
            car_code_field_label,
            self.create_help_field(
                self.car_code_edit,
                "Busca todos os alertas vinculados ao imóvel rural, "
                "usando o código de cadastro (CAR/SICAR) no padrão "
                "UF-0000000-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX (ex.: "
                "PE-2610905-7821EE203D0441D699AA58725AC25249). "
                "Segundo a documentação oficial da API, essa busca só "
                "retorna resultado para imóveis que já têm pelo menos "
                "um alerta — um código válido mas sem nenhum alerta "
                "não gera erro, só não aparece nada.",
            ),
        )
        self.car_validation_label = QLabel()
        self.car_validation_label.setWordWrap(True)
        self.car_validation_label.setObjectName("informationLabel")
        car_code_layout.addWidget(self.car_validation_label)
        car_code_layout.addLayout(car_code_form)
        self.car_scope_note_label = QLabel(ALERT_IN_PROPERTY_NOTE)
        self.car_scope_note_label.setWordWrap(True)
        self.car_scope_note_label.setObjectName("informationLabel")
        self.car_scope_note_label.setStyleSheet(
            "color: #C0392B; font-weight: 700;"
        )
        self.register_translatable(
            self.car_scope_note_label, ALERT_IN_PROPERTY_NOTE
        )
        car_code_layout.addWidget(self.car_scope_note_label)
        section.add_widget(self.car_code_frame)

        self.vector_layer_combo = FocusComboBox()
        self.vector_layer_combo.setIconSize(QSize(16, 16))
        self.vector_layer_field = self.create_help_field(
            self.vector_layer_combo,
            "Camada vetorial já carregada no QGIS cuja geometria define o "
            "recorte da busca.",
        )
        section.add_widget(self.vector_layer_field)


        self.layer_information_label = QLabel()
        self.layer_information_label.setObjectName(
            "informationLabel"
        )
        self.layer_information_label.setWordWrap(
            True
        )

        section.add_widget(
            self.layer_information_label
        )

        self.coordinates_frame = QFrame()
        self.coordinates_frame.setObjectName(
            "coordinatesFrame"
        )

        coordinates_layout = QVBoxLayout(
            self.coordinates_frame
        )
        coordinates_layout.setContentsMargins(
            12,
            10,
            12,
            12,
        )
        coordinates_layout.setSpacing(8)

        coordinates_title = QLabel(
            "COORDENADAS — UM PONTO"
        )
        coordinates_title.setObjectName(
            "coordinatesTitle"
        )
        self.register_translatable(
            coordinates_title, "COORDENADAS — UM PONTO"
        )

        coordinates_layout.addWidget(
            coordinates_title
        )

        coordinate_form = QFormLayout()
        self.responsive_forms.append(coordinate_form)

        self.longitude_edit = QLineEdit()
        self.longitude_edit.setPlaceholderText(
            self.tr("Ex.: -47.9292")
        )
        self.register_translatable(
            self.longitude_edit, "Ex.: -47.9292", "setPlaceholderText"
        )

        self.latitude_edit = QLineEdit()
        self.latitude_edit.setPlaceholderText(
            self.tr("Ex.: -15.7801")
        )
        self.register_translatable(
            self.latitude_edit, "Ex.: -15.7801", "setPlaceholderText"
        )

        self.longitude_edit.setValidator(
            QDoubleValidator(
                -180.0,
                180.0,
                8,
                self.longitude_edit,
            )
        )

        self.latitude_edit.setValidator(
            QDoubleValidator(
                -90.0,
                90.0,
                8,
                self.latitude_edit,
            )
        )

        longitude_label = QLabel("Longitude")
        self.register_translatable(longitude_label, "Longitude")
        coordinate_form.addRow(
            longitude_label,
            self.longitude_edit,
        )

        latitude_label = QLabel("Latitude")
        self.register_translatable(latitude_label, "Latitude")
        coordinate_form.addRow(
            latitude_label,
            self.latitude_edit,
        )

        coordinates_layout.addLayout(
            coordinate_form
        )

        coordinate_information = QLabel(
            "Sistema de referência: "
            "WGS 84 (EPSG:4326)"
        )
        coordinate_information.setObjectName(
            "informationLabel"
        )
        self.register_translatable(
            coordinate_information,
            "Sistema de referência: WGS 84 (EPSG:4326)",
        )

        coordinates_layout.addWidget(
            coordinate_information
        )

        section.add_widget(
            self.coordinates_frame
        )

        return section

    def register_combo_item(self, combo, index, text):
        """Registers a combo box item's text for retranslation."""
        combo.setItemText(index, self.tr(text))
        if not hasattr(self, "_translatable_combo_items"):
            self._translatable_combo_items = []
        self._translatable_combo_items.append((combo, index, text))

    def apply_combo_item_translations(self):
        for combo, index, text in getattr(
            self, "_translatable_combo_items", []
        ):
            try:
                combo.setItemText(index, self.tr(text))
            except RuntimeError:
                continue

    def create_period_section(self):
        section = CollapsibleSection(
            "2. Período",
            expanded=True,
        )
        self.register_translatable(
            section.toggle_button, "2. Período", transform=str.upper
        )

        form = QFormLayout()
        self.responsive_forms.append(form)

        self.period_type_combo = FocusComboBox()

        self.period_type_combo.addItem(
            "Data de detecção",
            MapBiomasApiClient
            .PERIOD_DETECTION,
        )
        self.register_combo_item(self.period_type_combo, 0, "Data de detecção")

        self.period_type_combo.addItem(
            "Data de publicação",
            MapBiomasApiClient
            .PERIOD_PUBLICATION,
        )
        self.register_combo_item(
            self.period_type_combo, 1, "Data de publicação"
        )

        self.start_date_edit = FocusDateEdit()
        self.start_date_edit.setCalendarPopup(
            True
        )
        self.start_date_edit.setDisplayFormat(
            "dd/MM/yyyy"
        )
        self.start_date_edit.setDate(
            QDate.currentDate()
            .addMonths(-1)
        )

        self.end_date_edit = FocusDateEdit()
        self.end_date_edit.setCalendarPopup(
            True
        )
        self.end_date_edit.setDisplayFormat(
            "dd/MM/yyyy"
        )
        self.end_date_edit.setDate(
            QDate.currentDate()
        )

        filter_by_label = QLabel("Filtrar por")
        self.register_translatable(filter_by_label, "Filtrar por")
        form.addRow(
            filter_by_label,
            self.create_help_field(
                self.period_type_combo,
                "Define se o período se aplica à detecção ou à publicação.",
            ),
        )

        # Start and end dates side by side, plus quick ranges.
        dates_widget = QWidget()
        dates_grid = QGridLayout(dates_widget)
        dates_grid.setContentsMargins(0, 0, 0, 0)
        dates_grid.setHorizontalSpacing(10)
        dates_grid.setVerticalSpacing(3)
        start_date_label = QLabel("Data inicial")
        self.register_translatable(start_date_label, "Data inicial")
        end_date_label = QLabel("Data final")
        self.register_translatable(end_date_label, "Data final")
        self.register_translatable(
            self.start_date_edit, "Primeiro dia incluído na consulta.",
            "setToolTip",
        )
        self.register_translatable(
            self.end_date_edit, "Último dia incluído na consulta.",
            "setToolTip",
        )
        dates_grid.addWidget(start_date_label, 0, 0)
        dates_grid.addWidget(end_date_label, 0, 1)
        dates_grid.addWidget(self.start_date_edit, 1, 0)
        dates_grid.addWidget(self.end_date_edit, 1, 1)
        dates_grid.setColumnStretch(0, 1)
        dates_grid.setColumnStretch(1, 1)
        form.addRow(dates_widget)

        quick_layout = QHBoxLayout()
        quick_layout.setContentsMargins(0, 0, 0, 0)
        quick_layout.setSpacing(6)
        for text, days in (
            ("Últimos 30 dias", 30),
            ("90 dias", 90),
            ("Este ano", None),
        ):
            button = QPushButton(text)
            button.setObjectName("chipButton")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.register_translatable(button, text)
            button.clicked.connect(
                lambda _checked=False, value=days: self.set_quick_period(value)
            )
            quick_layout.addWidget(button)
        form.addRow(quick_layout)

        self.period_validation_label = QLabel()
        self.period_validation_label.setWordWrap(True)
        self.period_validation_label.setObjectName("informationLabel")
        self.period_validation_label.setStyleSheet("color: #B3261E;")
        form.addRow(self.period_validation_label)
        self.start_date_edit.dateChanged.connect(self.validate_search_period)
        self.end_date_edit.dateChanged.connect(self.validate_search_period)

        section.add_layout(
            form
        )

        return section

    def create_filter_section(self):
        section = CollapsibleSection(
            "3. Filtros",
            expanded=True,
        )
        self.register_translatable(
            section.toggle_button, "3. Filtros", transform=str.upper
        )

        form = QFormLayout()
        self.responsive_forms.append(form)

        self.minimum_area_spin = (
            FocusDoubleSpinBox()
        )
        self.minimum_area_spin.setRange(
            0.0,
            999999999.0,
        )
        self.minimum_area_spin.setDecimals(
            2
        )
        self.minimum_area_spin.setSuffix(
            " ha"
        )

        self.source_combo = CheckableComboBox()
        self.source_combo.default_text = self.tr("Todas as fontes")
        self.register_translatable(
            self.source_combo.lineEdit(),
            "Todas as fontes",
            "setPlaceholderText",
        )
        self.selected_sources_label = QLabel("Todas as fontes")
        self.register_translatable(
            self.selected_sources_label, "Todas as fontes"
        )
        self.selected_sources_label.setWordWrap(True)
        self.selected_sources_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.selected_sources_label.setStyleSheet(
            "color: #59666b; padding: 2px 0 6px 0;"
        )
        self.source_mode_combo = FocusComboBox()
        self.source_mode_combo.addItem(
            "Qualquer fonte selecionada", "any"
        )
        self.register_combo_item(
            self.source_mode_combo, 0, "Qualquer fonte selecionada"
        )
        self.source_mode_combo.addItem(
            "Todas selecionadas juntas", "all"
        )
        self.register_combo_item(
            self.source_mode_combo, 1, "Todas selecionadas juntas"
        )
        self.source_mode_combo.addItem(
            "Combinação exata", "exact"
        )
        self.register_combo_item(
            self.source_mode_combo, 2, "Combinação exata"
        )

        minimum_area_label = QLabel("Área mínima")
        self.register_translatable(minimum_area_label, "Área mínima")
        form.addRow(
            minimum_area_label,
            self.create_help_field(
                self.minimum_area_spin,
                "Exclui alertas menores que a área informada, em hectares.",
            ),
        )

        sources_label = QLabel("Fontes")
        self.register_translatable(sources_label, "Fontes")
        form.addRow(
            sources_label,
            self.create_help_field(
                self.source_combo,
                "Selecione uma ou mais fontes de detecção disponibilizadas pela API.",
            ),
        )
        selected_label = QLabel("Selecionadas")
        self.register_translatable(selected_label, "Selecionadas")
        form.addRow(
            selected_label,
            self.selected_sources_label,
        )
        source_rule_label = QLabel("Regra das fontes")
        self.register_translatable(source_rule_label, "Regra das fontes")
        form.addRow(
            source_rule_label,
            self.create_help_field(
                self.source_mode_combo,
                "Define se basta qualquer fonte, se todas devem estar presentes "
                "ou se a combinação deve ser exata.",
            ),
        )
        section.add_layout(
            form
        )

        return section

    def create_crossing_section(self):
        section = CollapsibleSection(
            "4. Cruzamentos",
            expanded=False,
        )
        self.register_translatable(
            section.toggle_button, "4. Cruzamentos", transform=str.upper
        )
        form = QFormLayout()
        self.responsive_forms.append(form)
        self.crossing_field_combo = FocusComboBox()
        self.crossing_field_combo.addItem(
            "Conecte-se à API para consultar as opções",
            None,
        )
        self.register_combo_item(
            self.crossing_field_combo,
            0,
            "Conecte-se à API para consultar as opções",
        )
        self.crossing_field_combo.setEnabled(False)
        self.crossing_mode_combo = FocusComboBox()
        self.crossing_mode_combo.addItem(
            "Todos os alertas",
            "all",
        )
        self.register_combo_item(
            self.crossing_mode_combo, 0, "Todos os alertas"
        )
        self.crossing_mode_combo.addItem(
            "Somente alertas com cruzamento",
            "with",
        )
        self.register_combo_item(
            self.crossing_mode_combo, 1, "Somente alertas com cruzamento"
        )
        self.crossing_mode_combo.addItem(
            "Somente alertas sem cruzamento",
            "without",
        )
        self.register_combo_item(
            self.crossing_mode_combo, 2, "Somente alertas sem cruzamento"
        )
        crossing_type_label = QLabel("Tipo")
        self.register_translatable(crossing_type_label, "Tipo")
        form.addRow(
            crossing_type_label,
            self.create_help_field(
                self.crossing_field_combo,
                "Base territorial ou ambiental usada para verificar cruzamentos.",
            ),
        )
        crossing_condition_label = QLabel("Condição")
        self.register_translatable(crossing_condition_label, "Condição")
        form.addRow(
            crossing_condition_label,
            self.create_help_field(
                self.crossing_mode_combo,
                "Inclui todos os alertas ou somente os que têm ou não têm cruzamento.",
            ),
        )
        self.include_analytics_checkbox = QCheckBox(
            "Incluir dados de cruzamento territorial na camada"
        )
        self.register_translatable(
            self.include_analytics_checkbox,
            "Incluir dados de cruzamento territorial na camada",
        )
        self.include_analytics_checkbox.setChecked(True)
        self.include_analytics_checkbox.setToolTip(
            "Desmarque para buscas mais rápidas quando você não precisa "
            "dos detalhes de cruzamento (Unidade de Conservação, Terra "
            "Indígena, Assentamento etc.) — o filtro de Cruzamentos "
            "continua funcionando normalmente mesmo desmarcado. Com a "
            "opção desmarcada, a aba Detalhes de cada alerta continua "
            "mostrando os cruzamentos normalmente (ela já consulta "
            "isso à parte, por alerta), mas a exportação 'Tabela de "
            "atributos completa', 'Cruzamentos territoriais' e o "
            "gráfico 'Áreas por tipo de cruzamento' ficam indisponíveis "
            "para essa camada — refaça a busca com a opção marcada se "
            "precisar deles depois."
        )
        self.register_translatable(
            self.include_analytics_checkbox,
            "Desmarque para buscas mais rápidas quando você não precisa "
            "dos detalhes de cruzamento (Unidade de Conservação, Terra "
            "Indígena, Assentamento etc.) — o filtro de Cruzamentos "
            "continua funcionando normalmente mesmo desmarcado. Com a "
            "opção desmarcada, a aba Detalhes de cada alerta continua "
            "mostrando os cruzamentos normalmente (ela já consulta "
            "isso à parte, por alerta), mas a exportação 'Tabela de "
            "atributos completa', 'Cruzamentos territoriais' e o "
            "gráfico 'Áreas por tipo de cruzamento' ficam indisponíveis "
            "para essa camada — refaça a busca com a opção marcada se "
            "precisar deles depois.",
            "setToolTip",
        )
        form.addRow(self.include_analytics_checkbox)
        section.add_layout(form)
        return section

    def create_layers_tab(self):
        tab = QWidget()

        layout = QVBoxLayout(tab)
        layout.setContentsMargins(
            12,
            12,
            12,
            12,
        )
        layout.setSpacing(10)

        title = QLabel(
            "Camada de alertas"
        )
        title.setObjectName(
            "tabTitleLabel"
        )
        title_font = title.font()
        title_font.setBold(True)
        title.setFont(title_font)
        self.register_translatable(title, "Camada de alertas")

        self.layers_status_label = QLabel(
            self.tr("Nenhuma consulta realizada.")
        )
        self.layers_status_label.setObjectName(
            "emptyStateLabel"
        )
        self.layers_status_label.setWordWrap(
            True
        )
        self.analysis_layer_combo = FocusComboBox()
        self.analysis_layer_combo.setToolTip(
            "Escolha qual camada de consulta alimenta o gráfico."
        )
        self.register_translatable(
            self.analysis_layer_combo,
            "Escolha qual camada de consulta alimenta o gráfico.",
            "setToolTip",
        )
        self.layers_inventory_label = QLabel(
            self.tr("Nenhuma camada filtrada.")
        )
        self.layers_inventory_label.setWordWrap(True)
        self.layers_inventory_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.open_table_button = QPushButton(
            "Abrir tabela de atributos"
        )
        self.register_translatable(
            self.open_table_button, "Abrir tabela de atributos"
        )

        self.remove_layer_button = QPushButton(
            "Remover camada"
        )
        self.register_translatable(
            self.remove_layer_button, "Remover camada"
        )

        csv_export_title = QLabel("Exportar tabela de atributos")
        csv_export_title.setObjectName("tabTitleLabel")
        csv_export_title_font = csv_export_title.font()
        csv_export_title_font.setBold(True)
        csv_export_title.setFont(csv_export_title_font)
        self.register_translatable(
            csv_export_title, "Exportar tabela de atributos"
        )
        csv_export_label = QLabel("Conteúdo do arquivo")
        self.register_translatable(csv_export_label, "Conteúdo do arquivo")
        self.csv_export_mode_combo = FocusComboBox()
        self.csv_export_mode_combo.addItem(
            "Informações principais", "main"
        )
        self.register_combo_item(
            self.csv_export_mode_combo, 0, "Informações principais"
        )
        self.csv_export_mode_combo.addItem(
            "Tabela de atributos completa", "full"
        )
        self.register_combo_item(
            self.csv_export_mode_combo, 1, "Tabela de atributos completa"
        )
        csv_export_mode_help = (
            "Existem 2 formatos porque cada um responde uma pergunta "
            "diferente:\n\n"
            "• Informações principais — 1 linha por alerta, só os "
            "campos essenciais (código, área, data, bioma/estado/"
            "município). O jeito mais simples de olhar a lista de "
            "alertas.\n\n"
            "• Tabela de atributos completa — 1 linha por alerta, com "
            "TODOS os campos da camada. A divisão de área por "
            "território (UC, TI, assentamento etc.) vem dentro de "
            "colunas com texto em JSON, então cada alerta ainda ocupa "
            "só 1 linha, mesmo cruzando vários territórios."
        )
        self.csv_export_mode_combo.setToolTip(self.tr(csv_export_mode_help))
        self.register_translatable(
            self.csv_export_mode_combo, csv_export_mode_help, "setToolTip"
        )
        csv_export_row = self.create_help_field(
            self.csv_export_mode_combo, self.tr(csv_export_mode_help)
        )
        self.layers_export_csv_button = AutoFitPushButton(
            "TABELA DE ATRIBUTOS (CSV)"
        )
        self.register_translatable(
            self.layers_export_csv_button, "TABELA DE ATRIBUTOS (CSV)"
        )
        # This tab exports the full attribute table; the "main
        # information" CSV moved to the Statistics tab.
        csv_export_label.setVisible(False)
        csv_export_row.setVisible(False)
        self.csv_export_mode_combo.setCurrentIndex(
            self.csv_export_mode_combo.findData("full")
        )
        self.layers_export_csv_button.setEnabled(False)

        # The attribute table also goes to XLSX, and the whole layer
        # (geometry + attributes) to GeoPackage or Shapefile.
        def export_button(text):
            button = AutoFitPushButton(text)
            self.register_translatable(button, text)
            button.setEnabled(False)
            return button

        self.layers_export_xlsx_button = export_button(
            "TABELA DE ATRIBUTOS (XLSX)"
        )
        self.layers_export_gpkg_button = export_button("CAMADA (GPKG)")
        self.layers_export_shp_button = export_button("CAMADA (SHP)")
        table_buttons = QHBoxLayout()
        table_buttons.addWidget(self.layers_export_csv_button)
        table_buttons.addWidget(self.layers_export_xlsx_button)
        layer_export_title = QLabel("Exportar camada (com geometria)")
        layer_export_title.setObjectName("tabTitleLabel")
        layer_export_title.setFont(csv_export_title_font)
        self.register_translatable(
            layer_export_title, "Exportar camada (com geometria)"
        )
        layer_buttons = QHBoxLayout()
        layer_buttons.addWidget(self.layers_export_gpkg_button)
        layer_buttons.addWidget(self.layers_export_shp_button)

        layout.addWidget(title)
        layout.addWidget(
            self.layers_status_label
        )
        layout.addWidget(self.layers_inventory_label)
        layout.addWidget(csv_export_title)
        layout.addWidget(csv_export_label)
        layout.addWidget(csv_export_row)
        layout.addLayout(table_buttons)
        layout.addSpacing(6)
        layout.addWidget(layer_export_title)
        layout.addLayout(layer_buttons)
        layout.addStretch()
        self.open_table_button.setVisible(False)
        self.remove_layer_button.setVisible(False)

        return tab

    def create_results_tab(self):
        tab = QWidget()

        layout = QVBoxLayout(tab)
        layout.setContentsMargins(
            12,
            12,
            12,
            12,
        )
        layout.setSpacing(10)

        title = QLabel(
            "Resumo da consulta"
        )
        title.setObjectName(
            "tabTitleLabel"
        )
        self.register_translatable(title, "Resumo da consulta")

        layout.addWidget(title)
        title_font = title.font()
        title_font.setBold(True)
        title.setFont(title_font)

        self.result_status_label = QLabel(
            "Faça uma consulta para "
            "visualizar os resultados."
        )
        self.register_translatable(
            self.result_status_label,
            "Faça uma consulta para visualizar os resultados.",
        )
        self.result_status_label.setObjectName(
            "emptyStateLabel"
        )
        self.result_status_label.setWordWrap(
            True
        )

        self.layer_comparison_title = self.create_information_title(
            "Comparação das camadas de consulta"
        )
        self.layer_comparison_table = QTableWidget()
        self.layer_comparison_table.setColumnCount(8)
        self.layer_comparison_table.setHorizontalHeaderLabels(
            self.comparison_table_header_labels()
        )
        self.layer_comparison_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.layer_comparison_table.setAlternatingRowColors(True)
        self.layer_comparison_table.setMinimumHeight(170)
        self.layer_comparison_table.horizontalHeader().setStretchLastSection(
            True
        )
        self.layer_comparison_title.setVisible(False)
        self.layer_comparison_table.setVisible(False)

        self.alert_count_value = MirrorLabel("—", self.sync_result_cards)
        self.alert_count_value.setObjectName(
            "resultValueLabel"
        )

        self.total_area_value = MirrorLabel("—", self.sync_result_cards)
        self.total_area_value.setObjectName(
            "resultValueLabel"
        )
        self.largest_alert_value = MirrorLabel("—", self.sync_result_cards)
        self.largest_alert_value.setObjectName("resultTextValueLabel")
        self.largest_alert_code_value = MirrorLabel(
            "—", self.sync_result_cards
        )
        self.largest_alert_code_value.setObjectName("resultTextValueLabel")
        self.largest_alert_location_value = MirrorLabel("—", self.sync_result_cards)
        self.largest_alert_location_value.setObjectName("resultTextValueLabel")
        self.largest_alert_location_value.setWordWrap(True)
        self.top_municipality_value = MirrorLabel("—", self.sync_result_cards)
        self.top_municipality_value.setObjectName("resultTextValueLabel")
        self.top_municipality_value.setWordWrap(True)

        # Extra fields from the API's official statistical summary
        # (alertsSummary query), mirroring the cards shown on the
        # platform. They're only filled in when the query matches exactly
        # the filters the API accepts (api_statistics_exact); there's no
        # way to recompute them locally from the downloaded layer.
        self.lowest_alert_value = MirrorLabel("—", self.sync_result_cards)
        self.lowest_alert_value.setObjectName("resultTextValueLabel")
        self.lowest_alert_code_value = MirrorLabel("—", self.sync_result_cards)
        self.lowest_alert_code_value.setObjectName("resultTextValueLabel")
        self.lowest_alert_location_value = MirrorLabel("—", self.sync_result_cards)
        self.lowest_alert_location_value.setObjectName("resultTextValueLabel")
        self.lowest_alert_location_value.setWordWrap(True)

        self.deforestation_speed_value = MirrorLabel("—", self.sync_result_cards)
        self.deforestation_speed_value.setObjectName("resultTextValueLabel")
        self.deforestation_speed_value.setWordWrap(True)

        self.overlap_counts_value = MirrorLabel("—", self.sync_result_cards)
        self.overlap_counts_value.setObjectName("resultTextValueLabel")
        self.overlap_counts_value.setWordWrap(True)

        self.period_type_value = MirrorLabel("—", self.sync_result_cards)
        self.period_type_value.setObjectName(
            "resultTextValueLabel"
        )

        self.period_result_value = MirrorLabel("—", self.sync_result_cards)
        self.period_result_value.setObjectName(
            "resultTextValueLabel"
        )

        layout.addWidget(title)

        layout.addWidget(
            self.result_status_label
        )
        # Key numbers as cards at the top of the tab. The labels are
        # the same ones update_result_summary() already fills.
        # Search progress, shown while the polygons download (v3).
        self.search_progress_frame = QFrame()
        self.search_progress_frame.setObjectName("statCard")
        self.search_progress_frame.setStyleSheet(
            "QFrame#statCard { background-color: white; border: 1px "
            "solid #D7DDD9; border-radius: 8px; }"
        )
        progress_layout = QVBoxLayout(self.search_progress_frame)
        progress_layout.setContentsMargins(12, 10, 12, 10)
        progress_layout.setSpacing(6)
        self.search_progress_label = QLabel(self.tr("Baixando os alertas..."))
        self.search_progress_label.setStyleSheet(
            "font-weight: 700; border: none;"
        )
        from qgis.PyQt.QtWidgets import QProgressBar
        self.search_progress_bar = QProgressBar()
        self.search_progress_bar.setTextVisible(False)
        self.search_progress_bar.setFixedHeight(8)
        self.search_progress_bar.setStyleSheet(
            "QProgressBar { background: #EEE6E3; border: none; "
            "border-radius: 4px; } QProgressBar::chunk { background: "
            "#832413; border-radius: 4px; }"
        )
        self.search_progress_note = QLabel(
            self.tr(
                "Os números abaixo já são os oficiais da plataforma para "
                "estes filtros. A camada aparece no mapa ao terminar."
            )
        )
        self.search_progress_note.setWordWrap(True)
        self.search_progress_note.setStyleSheet(
            "color: #59666b; font-size: 11px; border: none;"
        )
        self.progress_cancel_button = QPushButton(self.tr("CANCELAR"))
        self.register_translatable(self.progress_cancel_button, "CANCELAR")
        self.progress_cancel_button.clicked.connect(
            lambda: self.api_client.cancel_current_request()
        )
        progress_layout.addWidget(self.search_progress_label)
        progress_layout.addWidget(self.search_progress_bar)
        progress_layout.addWidget(self.search_progress_note)
        progress_layout.addWidget(self.progress_cancel_button)
        self.search_progress_frame.setVisible(False)
        layout.addWidget(self.search_progress_frame)

        self.summary_notice_label = QLabel(SUMMARY_NOTICE)
        self.register_translatable(self.summary_notice_label, SUMMARY_NOTICE)
        self.summary_notice_label.setWordWrap(True)
        self.summary_notice_label.setStyleSheet(
            "background: #FBF1EE; color: #6F1E10; border-radius: 6px; "
            "padding: 8px 10px; font-size: 11px;"
        )
        layout.addWidget(self.summary_notice_label)

        self.result_cards_widget = QWidget()
        cards_grid = QGridLayout(self.result_cards_widget)
        cards_grid.setContentsMargins(0, 0, 0, 0)
        cards_grid.setHorizontalSpacing(8)
        cards_grid.setVerticalSpacing(8)
        self.result_card_values = {}
        # (title, key, row, column, column span); 6-column grid: the
        # first row has 3 cards, the others 2.
        card_specs = (
            ("Total de alertas", "count", 0, 0, 2),
            ("Área desmatada (ha)", "area", 0, 2, 2),
            ("Média diária (ha/dia)", "avg", 0, 4, 2),
            ("Maior desmatamento", "biggest", 1, 0, 3),
            ("Maior velocidade", "speed", 1, 3, 3),
            ("Menor alerta", "lowest", 2, 0, 3),
            ("Município com maior área", "city", 2, 3, 3),
            ("Sobreposições (nº de alertas)", "overlaps", 3, 0, 6),
            ("Período analisado", "period", 4, 0, 6),
        )
        for card_title, key, row, column, span in card_specs:
            card = QFrame()
            card.setObjectName("statCard")
            # Inline too: some QGIS UI themes override the dock stylesheet.
            card.setStyleSheet(
                "QFrame#statCard { background-color: white; border: 1px "
                "solid #D7DDD9; border-radius: 8px; }"
            )
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(8, 7, 8, 7)
            card_layout.setSpacing(1)
            card_title_label = QLabel(self.tr(card_title))
            card_title_label.setWordWrap(True)
            card_title_label.setStyleSheet(
                "color: #24342b; font-size: 11px; font-weight: 700; "
                "border: none;"
            )
            self._translatable_widgets.append(
                (card_title_label, card_title, "setText", (), None)
            )
            value_label = QLabel("—")
            value_label.setWordWrap(True)
            value_label.setTextFormat(Qt.TextFormat.RichText)
            value_label.setStyleSheet("border: none;")
            if key in ("count", "area", "avg", "biggest", "speed", "lowest",
                       "city"):
                card_title_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
                value_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            card_layout.addWidget(card_title_label)
            card_layout.addWidget(value_label)
            self.result_card_values[key] = value_label
            cards_grid.addWidget(card, row, column, 1, span)
        for column in range(6):
            cards_grid.setColumnStretch(column, 1)
        layout.addWidget(self.result_cards_widget)
        layout.addWidget(self.layer_comparison_title)
        layout.addWidget(self.layer_comparison_table)

        layout.addWidget(
            self.create_information_title("Alertas encontrados")
        )

        layout.addWidget(
            self.alert_count_value
        )

        layout.addWidget(
            self.create_information_title("Área total")
        )

        layout.addWidget(
            self.total_area_value
        )
        layout.addWidget(self.create_information_title("Maior alerta"))
        layout.addWidget(self.largest_alert_value)
        layout.addWidget(
            self.create_information_title("Código do maior alerta")
        )
        layout.addWidget(self.largest_alert_code_value)
        layout.addWidget(
            self.create_information_title("Local do maior alerta")
        )
        layout.addWidget(self.largest_alert_location_value)
        self.top_municipality_title = self.create_information_title(
            "Município com maior área"
        )
        # This title is updated by update_top_municipality_title()
        # (language + country), not by the generic retranslation
        # mechanism — remove the generic registration so it doesn't
        # revert to the fixed "Município" text on every language switch.
        if self._translatable_widgets and (
            self._translatable_widgets[-1][0] is self.top_municipality_title
        ):
            self._translatable_widgets.pop()
        layout.addWidget(self.top_municipality_title)
        layout.addWidget(self.top_municipality_value)

        layout.addWidget(self.create_information_title("Menor alerta"))
        layout.addWidget(self.lowest_alert_value)
        layout.addWidget(
            self.create_information_title("Código do menor alerta")
        )
        layout.addWidget(self.lowest_alert_code_value)
        layout.addWidget(
            self.create_information_title("Local do menor alerta")
        )
        layout.addWidget(self.lowest_alert_location_value)

        layout.addWidget(
            self.create_information_title("Velocidade de desmatamento")
        )
        layout.addWidget(self.deforestation_speed_value)

        layout.addWidget(
            self.create_information_title(
                "Sobreposições com áreas protegidas e institucionais"
            )
        )
        layout.addWidget(self.overlap_counts_value)

        layout.addWidget(
            self.create_information_title("Tipo de data")
        )

        layout.addWidget(
            self.period_type_value
        )

        layout.addWidget(
            self.create_information_title("Período analisado")
        )

        layout.addWidget(
            self.period_result_value
        )

        self.export_summary_button = AutoFitPushButton(
            "EXPORTAR RESUMO (XLSX)"
        )
        self.register_translatable(
            self.export_summary_button, "EXPORTAR RESUMO (XLSX)"
        )
        self.export_summary_button.setEnabled(False)
        layout.addWidget(self.export_summary_button)
        self.export_main_csv_button = AutoFitPushButton(
            "EXPORTAR INFORMAÇÕES PRINCIPAIS (CSV)"
        )
        self.register_translatable(
            self.export_main_csv_button,
            "EXPORTAR INFORMAÇÕES PRINCIPAIS (CSV)",
        )
        self.export_main_csv_button.setToolTip(
            self.tr(
                "Uma linha por alerta, só os campos essenciais: código, "
                "área, datas, fonte, bioma, estado e município."
            )
        )
        self.export_main_csv_button.setEnabled(False)
        self.export_main_csv_button.clicked.connect(
            self.with_full_layer(lambda: self.export_filtered_csv("main"))
        )
        self.export_main_csv_button.setVisible(False)

        visible_widgets = {
            title,
            self.summary_notice_label,
            self.search_progress_frame,
            self.result_cards_widget,
            self.layer_comparison_title,
            self.layer_comparison_table,
            self.export_summary_button,
        }
        for index in range(layout.count()):
            widget = layout.itemAt(index).widget()
            if widget is not None and widget not in visible_widgets:
                widget.setVisible(False)

        analysis_title = QLabel("Análises estatísticas")
        analysis_title.setObjectName("tabTitleLabel")
        analysis_title_font = analysis_title.font()
        analysis_title_font.setBold(True)
        analysis_title.setFont(analysis_title_font)
        self.register_translatable(analysis_title, "Análises estatísticas")
        layout.addWidget(analysis_title)
        layout.addWidget(self.create_chart_analysis_panel())

        layout.addStretch()

        return tab

    def create_chart_analysis_panel(self):
        """Creates the analysis configuration shown in the Statistics tab."""
        panel = QFrame()
        panel.setObjectName("sectionCard")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Only one layer is analysed. The comparison combo still
        # exists (hidden, always "Não comparar") so the chart code that
        # reads it keeps working unchanged.
        layer_form = QVBoxLayout()
        layer_form.setSpacing(3)
        layer1_label = QLabel("Camada")
        self.register_translatable(layer1_label, "Camada")
        layer_form.addWidget(layer1_label)
        layer_form.addWidget(self.analysis_layer_combo)
        self.comparison_layer_combo = FocusComboBox(panel)
        self.comparison_layer_combo.addItem("Não comparar", None)
        self.register_combo_item(
            self.comparison_layer_combo, 0, "Não comparar"
        )
        self.comparison_layer_combo.setVisible(False)
        layout.addLayout(layer_form)

        chart_form = TwoColumnForm()
        self.chart_type_combo = FocusComboBox()
        self.chart_type_combo.addItem("Barras", "bar")
        self.register_combo_item(self.chart_type_combo, 0, "Barras")
        self.chart_type_combo.addItem("Pizza", "pie")
        self.register_combo_item(self.chart_type_combo, 1, "Pizza")
        self.chart_type_combo.addItem("Linha", "line")
        self.register_combo_item(self.chart_type_combo, 2, "Linha")
        self.chart_group_combo = FocusComboBox()
        self.chart_metric_combo = FocusComboBox()
        self.chart_metric_combo.addItem("Número de registros", "count")
        self.register_combo_item(
            self.chart_metric_combo, 0, "Número de registros"
        )
        self.chart_metric_combo.addItem("Soma", "sum")
        self.register_combo_item(self.chart_metric_combo, 1, "Soma")
        self.chart_metric_combo.addItem("Média", "average")
        self.register_combo_item(self.chart_metric_combo, 2, "Média")
        self.chart_value_combo = FocusComboBox()
        self.chart_value_combo.setEnabled(False)
        self.chart_source_mode_combo = FocusComboBox()
        self.chart_source_mode_combo.addItem("Separar cada fonte", "split")
        self.register_combo_item(
            self.chart_source_mode_combo, 0, "Separar cada fonte"
        )
        self.chart_source_mode_combo.addItem(
            "Agrupar pela combinação", "combination"
        )
        self.register_combo_item(
            self.chart_source_mode_combo, 1, "Agrupar pela combinação"
        )
        self.chart_category_combo = FocusComboBox()
        self.chart_category_combo.addItem("Todos os valores", None)
        self.register_combo_item(
            self.chart_category_combo, 0, "Todos os valores"
        )
        self.chart_limit_spin = FocusSpinBox()
        self.chart_limit_spin.setRange(3, 20)
        self.chart_limit_spin.setValue(10)
        chart_type_label = QLabel("Tipo de gráfico")
        self.register_translatable(chart_type_label, "Tipo de gráfico")
        chart_form.addRow(
            chart_type_label,
            self.create_help_field(
                self.chart_type_combo,
                "Define a forma de exibição do resultado na aba Gráficos.",
            ),
        )
        chart_group_label = QLabel("Campo para comparar")
        self.register_translatable(
            chart_group_label, "Campo para comparar"
        )
        chart_form.addRow(
            chart_group_label,
            self.create_help_field(
                self.chart_group_combo,
                "Agrupa os alertas pelo atributo escolhido. A opção "
                "'Áreas por tipo de cruzamento' compara a soma, em hectares, "
                "de cada sobreposição territorial informada pela API; como "
                "os tipos podem se sobrepor, as barras não representam "
                "parcelas exclusivas da área total.",
            ),
        )
        chart_metric_label = QLabel("Cálculo")
        self.register_translatable(chart_metric_label, "Cálculo")
        chart_form.addRow(
            chart_metric_label,
            self.create_help_field(
                self.chart_metric_combo,
                "Escolhe entre contagem, soma ou média do campo numérico.",
            ),
        )
        chart_value_label = QLabel("Campo numérico")
        self.register_translatable(chart_value_label, "Campo numérico")
        chart_form.addRow(
            chart_value_label,
            self.create_help_field(
                self.chart_value_combo,
                "Atributo usado nos cálculos de soma e média.",
            ),
        )
        chart_source_label = QLabel("Fontes múltiplas")
        self.register_translatable(chart_source_label, "Fontes múltiplas")
        chart_form.addRow(
            chart_source_label,
            self.create_help_field(
                self.chart_source_mode_combo,
                "Separa cada fonte ou mantém a combinação registrada no alerta.",
            ),
        )
        chart_category_label = QLabel("Valor específico")
        self.register_translatable(
            chart_category_label, "Valor específico"
        )
        chart_form.addRow(
            chart_category_label,
            self.create_help_field(
                self.chart_category_combo,
                "Restringe o gráfico a uma categoria do campo de comparação.",
            ),
        )
        chart_limit_label = QLabel("Categorias exibidas")
        self.register_translatable(
            chart_limit_label, "Categorias exibidas"
        )
        chart_form.addRow(
            chart_limit_label,
            self.create_help_field(
                self.chart_limit_spin,
                "Limita quantos grupos do ranking aparecem no gráfico.",
            ),
        )
        layout.addLayout(chart_form)

        self.chart_status_label = QLabel(
            "<b>Status:</b> Aguardando configuração."
        )
        self.register_translatable(
            self.chart_status_label,
            "<b>Status:</b> Aguardando configuração.",
        )
        self.chart_status_label.setWordWrap(True)
        self.chart_status_label.setObjectName("emptyStateLabel")
        self.apply_chart_button = QPushButton("APLICAR ANÁLISE")
        self.register_translatable(
            self.apply_chart_button, "APLICAR ANÁLISE"
        )
        self.apply_chart_button.setObjectName("primaryButton")
        self.apply_chart_button.setMinimumHeight(42)
        layout.addWidget(self.chart_status_label)
        layout.addWidget(self.apply_chart_button)
        return panel

    def sync_result_cards(self):
        """Mirrors the summary labels (filled by update_result_summary and
        apply_api_summary) into the platform-style cards."""
        cards = getattr(self, "result_card_values", None)
        if not cards:
            return

        def big(value, color="#C0392B", size=19):
            return (
                '<span style="font-size:{}px; font-weight:700; color:{};">'
                "{}</span>".format(size, color, html.escape(value or "—"))
            )

        def small(value):
            value = (value or "").strip()
            if not value or value == "—":
                return ""
            return (
                '<br><span style="font-size:11px; font-weight:700; '
                'color:#C0392B;">{}</span>'.format(html.escape(value))
            )

        area_text = self.total_area_value.text().replace(" ha", "")
        cards["count"].setText(big(self.alert_count_value.text()))
        cards["area"].setText(big(area_text))
        speed = getattr(self, "_speed_values", {}) or {}
        if self.deforestation_speed_value.text() in ("", "—"):
            speed = {}
        cards["avg"].setText(big(speed.get("average") or "—"))
        code = self.largest_alert_code_value.text()
        cards["biggest"].setText(
            big(self.largest_alert_value.text(), size=17)
            + small(
                " · ".join(
                    part for part in (
                        self.tr("alerta {}", code) if code not in ("", "—") else "",
                        self.largest_alert_location_value.text()
                        if self.largest_alert_location_value.text() != "—"
                        else "",
                    ) if part
                )
            )
        )
        cards["speed"].setText(
            big(speed.get("biggest") or "—", size=17)
            + small(speed.get("biggest_location") or "")
        )
        lowest_code = self.lowest_alert_code_value.text()
        cards["lowest"].setText(
            big(self.lowest_alert_value.text(), size=17)
            + small(
                " · ".join(
                    part for part in (
                        self.tr("alerta {}", lowest_code)
                        if lowest_code not in ("", "—") else "",
                        self.lowest_alert_location_value.text()
                        if self.lowest_alert_location_value.text() != "—"
                        else "",
                    ) if part
                )
            )
        )
        city_text = self.top_municipality_value.text()
        city_name, _sep, city_area = city_text.partition(" — ")
        cards["city"].setText(
            big(city_name or "—", size=15) + small(city_area)
        )
        overlaps = self.overlap_counts_value.text()
        overlap_lines = []
        for line in (overlaps or "").splitlines():
            name, sep, value = line.rpartition(": ")
            if sep and value.strip().replace(".", "").isdigit():
                overlap_lines.append(
                    "<b>{}:</b> <b style=\"color:#C0392B;\">{}</b>".format(
                        html.escape(name), html.escape(value)
                    )
                )
            else:
                overlap_lines.append(html.escape(line))
        cards["overlaps"].setText(
            (
                "<br>".join(overlap_lines)
                if overlaps and overlaps != "—" else "—"
            )
            + '<br><b style="color:#C0392B; font-size:12px;">{}</b>'.format(
                html.escape(
                    self.tr(
                        "Embargos, autorizações e ações de fiscalização: "
                        "consulte o laudo na plataforma."
                    )
                )
            )
        )
        period = self.period_result_value.text()
        period_type = self.period_type_value.text()
        cards["period"].setText(
            '<b style="color:#C0392B;">{}</b>'.format(html.escape(
                " · ".join(
                    part for part in (period_type, period)
                    if part and part != "—"
                ) or "—"
            ))
        )

    def create_information_title(self, text):
        label = QLabel(self.tr(text))
        label.setObjectName("resultInformationTitle")
        font = label.font()
        font.setBold(True)
        label.setFont(font)
        self._translatable_widgets.append((label, text, "setText", (), None))
        return label

    def create_help_field(self, field, help_text):
        container = QWidget()
        container.setMaximumWidth(650)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        icon = HelpIconLabel(self.tr(help_text))
        # Register the icon in the retranslation mechanism (same one used
        # by other widgets), so the help balloon's text updates when the
        # language is switched with the panel already open.
        self.register_translatable(icon, help_text, "set_help_text")
        icon.setAccessibleName("Informação")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedWidth(20)
        icon.setStyleSheet(
            "color: #59666b; font-size: 10px; font-weight: 700; "
            "background: transparent;"
        )
        layout.addWidget(field, 1)
        layout.addWidget(icon)
        return container

    def create_details_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 14, 14, 18)
        layout.setSpacing(10)

        title = QLabel("Detalhes do alerta")
        title.setObjectName("tabTitleLabel")
        title_font = title.font()
        title_font.setBold(True)
        title.setFont(title_font)
        self.register_translatable(title, "Detalhes do alerta")
        self.detail_status_label = QLabel(
            self.tr(
                "Identifique um alerta no mapa para consultar "
                "imagens e detalhes."
            )
        )
        self.detail_status_label.setObjectName("emptyStateLabel")
        self.detail_status_label.setWordWrap(True)

        self.identify_alert_button = AutoFitPushButton(
            "IDENTIFICAR ALERTA NO MAPA"
        )
        self.register_translatable(
            self.identify_alert_button, "IDENTIFICAR ALERTA NO MAPA"
        )
        self.identify_alert_button.setEnabled(False)

        self.detail_metadata_label = QLabel("—")
        self.detail_metadata_label.setWordWrap(True)
        self.detail_metadata_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.detail_intersections_label = QLabel(
            self.initial_intersections_text()
        )
        self.detail_intersections_label.setWordWrap(True)
        self.detail_intersections_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.detail_intersections_label.setObjectName("emptyStateLabel")
        self.detail_crossing_combo = FocusComboBox()
        self.detail_crossing_combo.setEnabled(False)
        self.detail_crossing_combo.setVisible(False)
        self.crossed_properties_label = QLabel(
            self.initial_properties_text()
        )
        self.crossed_properties_label.setWordWrap(True)
        self.crossed_properties_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.same_crossing_button = AutoFitPushButton(
            self.tr("OUTROS ALERTAS NOS MESMOS IMÓVEIS: {}", 0)
        )
        self.same_crossing_button.setEnabled(False)
        self.same_crossing_button.setVisible(True)
        self.same_crossing_status_label = QLabel("")
        self.same_crossing_status_label.setObjectName("emptyStateLabel")
        self.same_crossing_status_label.setWordWrap(True)
        self.same_crossing_status_label.setVisible(False)
        self.same_crossing_list = QListWidget()
        self.same_crossing_list.setMinimumHeight(120)
        self.same_crossing_list.setVisible(False)
        # Card for the selected alert itself (before/after images) —
        # intentionally kept separate from the "other alerts on the same
        # property" block. "FECHAR ALERTAS RELACIONADOS" must close only
        # the OTHER alerts; the selected alert's images stay visible at
        # all times, regardless of that button.
        self.selected_alert_container = QWidget()
        self.selected_alert_layout = QVBoxLayout(
            self.selected_alert_container
        )
        self.selected_alert_layout.setContentsMargins(0, 0, 0, 0)
        self.selected_alert_layout.setSpacing(10)
        self.same_property_scroll = QScrollArea()
        self.same_property_scroll.setWidgetResizable(True)
        self.same_property_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.same_property_scroll.setVisible(False)
        self.same_property_scroll.setMinimumHeight(360)
        self.close_same_property_button = AutoFitPushButton(
            self.tr("FECHAR ALERTAS RELACIONADOS")
        )
        self.close_same_property_button.setVisible(False)
        self.same_property_container = QWidget()
        self.same_property_layout = QVBoxLayout(
            self.same_property_container
        )
        self.same_property_layout.setContentsMargins(0, 0, 0, 0)
        self.same_property_layout.setSpacing(10)
        self.same_property_scroll.setWidget(self.same_property_container)

        images_layout = QHBoxLayout()
        self.details_images_layout = images_layout
        self.before_frame, self.before_title_label, self.before_image_label = (
            self.create_image_card("Imagem antes")
        )
        self.after_frame, self.after_title_label, self.after_image_label = (
            self.create_image_card("Imagem depois")
        )
        images_layout.addWidget(self.before_frame)
        images_layout.addWidget(self.after_frame)
        self.before_frame.setVisible(False)
        self.after_frame.setVisible(False)

        self.open_report_button = AutoFitPushButton(
            "ABRIR LAUDO NA PLATAFORMA"
        )
        self.register_translatable(
            self.open_report_button, "ABRIR LAUDO NA PLATAFORMA"
        )
        self.open_report_button.setEnabled(False)
        navigation = QHBoxLayout()
        self.detail_navigation_layout = navigation
        self.previous_alert_button = QPushButton("ANTERIOR")
        self.register_translatable(self.previous_alert_button, "ANTERIOR")
        self.next_alert_button = QPushButton("PRÓXIMO")
        self.register_translatable(self.next_alert_button, "PRÓXIMO")
        self.previous_alert_button.setEnabled(False)
        self.next_alert_button.setEnabled(False)
        navigation.addWidget(self.previous_alert_button)
        navigation.addWidget(self.next_alert_button)

        self.identify_alert_button.setObjectName("dashedButton")
        layout.addWidget(title)
        layout.addWidget(self.detail_status_label)
        layout.addWidget(self.identify_alert_button)
        layout.addWidget(self.detail_metadata_label)
        # Crossings and crossed properties each in their own card.
        crossings_card = QFrame()
        crossings_card.setObjectName("sectionCard")
        crossings_card.setStyleSheet(
            "QFrame#sectionCard { background-color: white; border: 1px "
            "solid #D7DDD9; border-radius: 8px; }"
        )
        crossings_layout = QVBoxLayout(crossings_card)
        crossings_layout.setContentsMargins(10, 8, 10, 10)
        crossings_layout.addWidget(self.detail_intersections_label)
        layout.addWidget(crossings_card)
        properties_card = QFrame()
        properties_card.setObjectName("sectionCard")
        properties_card.setStyleSheet(
            "QFrame#sectionCard { background-color: white; border: 1px "
            "solid #D7DDD9; border-radius: 8px; }"
        )
        properties_layout = QVBoxLayout(properties_card)
        properties_layout.setContentsMargins(10, 8, 10, 10)
        properties_layout.setSpacing(6)
        properties_layout.addWidget(
            self.create_information_title("Imóveis cruzados pelo alerta")
        )
        properties_layout.addWidget(self.crossed_properties_label)
        properties_layout.addWidget(self.detail_crossing_combo)
        properties_layout.addWidget(
            self.create_information_title("Outros alertas nos mesmos imóveis")
        )
        properties_layout.addWidget(self.same_crossing_button)
        layout.addWidget(properties_card)
        layout.addWidget(self.same_crossing_status_label)
        layout.addWidget(self.close_same_property_button)
        layout.addWidget(self.selected_alert_container)
        layout.addWidget(self.same_property_scroll)
        layout.addLayout(images_layout)
        # Images and actions are presented in the cards of the single
        # scrollable list, including for the initially identified alert.
        layout.addStretch()
        return tab

    def initial_intersections_text(self):
        return (
            "<b>{}</b><br>{}<br><b style=\"color:#C0392B;\">{}</b>".format(
                self.tr("Cruzamentos territoriais e ambientais"),
                self.tr("Selecione um alerta para consultar os cruzamentos."),
                self.tr(NOT_SHOWN_CROSSINGS_NOTE),
            )
        )

    def initial_properties_text(self):
        return "{}<br><b style=\"color:#C0392B;\">{}</b>".format(
            self.tr("Selecione um alerta para ver os imóveis cruzados."),
            html.escape(self.tr(ALERT_IN_PROPERTY_NOTE)),
        )

    def create_image_card(self, title):
        frame = QFrame()
        frame.setObjectName("coordinatesFrame")
        layout = QVBoxLayout(frame)
        title_label = QLabel(self.tr(title))
        title_label.setObjectName("coordinatesTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = title_label.font()
        title_font.setBold(True)
        title_label.setFont(title_font)
        self._translatable_widgets.append(
            (title_label, title, "setText", (), None)
        )
        image_label = DetailImageLabel(self.tr("Sem imagem"))
        image_label.setWordWrap(True)
        image_label.setStyleSheet(
            "background: #ffffff; border: 1px solid #ccd5cf;"
        )
        layout.addWidget(title_label)
        layout.addWidget(image_label)
        return frame, title_label, image_label

    def create_charts_tab(self):
        tab = QWidget()

        layout = QVBoxLayout(tab)
        layout.setContentsMargins(
            12,
            12,
            12,
            12,
        )

        title = QLabel(
            "Gráficos"
        )
        title.setObjectName(
            "tabTitleLabel"
        )
        self.register_translatable(title, "Gráficos")

        chart_title_row = QHBoxLayout()
        chart_title_row.addWidget(title, 1)
        self.chart_title_row = chart_title_row
        layout.addLayout(chart_title_row)
        self.chart_widget = BarChartWidget()
        self.chart_scroll = QScrollArea()
        self.chart_scroll.setWidgetResizable(False)
        self.chart_scroll.setMinimumWidth(0)
        self.chart_scroll.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.chart_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.chart_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.chart_scroll.setMinimumHeight(310)
        self.chart_scroll.setWidget(self.chart_widget)
        self.chart_note_label = QLabel(
            self.tr("Os dez maiores grupos são exibidos.")
        )
        self.chart_note_label.setObjectName("informationLabel")

        export_buttons = QHBoxLayout()
        self.chart_export_layout = export_buttons
        self.export_chart_button = AutoFitPushButton("GRÁFICO (PNG)")
        self.register_translatable(self.export_chart_button, "GRÁFICO (PNG)")
        self.export_csv_button = AutoFitPushButton("ALERTAS DO GRÁFICO (CSV)")
        self.register_translatable(
            self.export_csv_button, "ALERTAS DO GRÁFICO (CSV)"
        )
        self.export_gpkg_button = AutoFitPushButton("ALERTAS DO GRÁFICO (GPKG)")
        self.register_translatable(
            self.export_gpkg_button, "ALERTAS DO GRÁFICO (GPKG)"
        )
        self.export_shp_button = AutoFitPushButton("ALERTAS DO GRÁFICO (SHP)")
        self.register_translatable(
            self.export_shp_button, "ALERTAS DO GRÁFICO (SHP)"
        )
        self.chart_export_note = QLabel(
            self.tr(
                "As exportações desta aba seguem o recorte da análise "
                "(campo e valor escolhidos). A tabela completa da camada é "
                "exportada na aba Camadas."
            )
        )
        self.register_translatable(
            self.chart_export_note,
            "As exportações desta aba seguem o recorte da análise (campo e "
            "valor escolhidos). A tabela completa da camada é exportada na "
            "aba Camadas.",
        )
        self.chart_export_note.setWordWrap(True)
        self.chart_export_note.setObjectName("informationLabel")
        self.expand_chart_button = QPushButton("⤢ AMPLIAR")
        self.register_translatable(self.expand_chart_button, "⤢ AMPLIAR")
        self.expand_chart_button.setObjectName("expandChartButton")
        # Inline style: the QGIS theme overrides the dock stylesheet.
        self.expand_chart_button.setStyleSheet(
            "QPushButton { color: #C0392B; font-weight: 700; "
            "background: #FFFFFF; border: 2px solid #C0392B; "
            "border-radius: 4px; padding: 4px 10px; }"
            "QPushButton:hover { background: #FDECEA; }"
            "QPushButton:disabled { color: #B9A9A7; border-color: #D9CBC9; }"
        )
        self.expand_chart_button.setToolTip(
            self.tr("Abre o gráfico numa janela maior, com todas as categorias.")
        )
        self.register_translatable(
            self.expand_chart_button,
            "Abre o gráfico numa janela maior, com todas as categorias.",
            "setToolTip",
        )
        self.chart_title_row.addWidget(self.expand_chart_button)
        export_buttons.addWidget(self.export_chart_button)
        export_buttons.addWidget(self.export_csv_button)
        vector_export_buttons = QHBoxLayout()
        self.vector_export_layout = vector_export_buttons
        vector_export_buttons.addWidget(self.export_gpkg_button)
        vector_export_buttons.addWidget(self.export_shp_button)

        layout.addWidget(self.chart_scroll)
        layout.addWidget(self.chart_note_label)
        layout.addWidget(self.chart_export_note)
        layout.addLayout(export_buttons)
        layout.addLayout(vector_export_buttons)
        layout.addStretch()

        return tab

    def connect_signals(self):
        self.notice_checkbox.toggled.connect(
            self.accept_notice_button.setEnabled
        )
        self.accept_notice_button.clicked.connect(
            self.accept_country_notice
        )
        self.notice_shortcut_button.clicked.connect(
            self.show_country_notice
        )
        self.tabs.currentChanged.connect(
            self.handle_main_tab_changed
        )
        self.country_combo.currentIndexChanged.connect(
            self.update_platform
        )

        area_buttons = (
            self.area_country_radio,
            self.area_layer_radio,
            self.area_coordinates_radio,
            self.area_alert_code_radio,
            self.area_car_radio,
        )

        for button in area_buttons:
            button.toggled.connect(
                self.update_area_controls
            )

        self.vector_layer_combo.currentIndexChanged.connect(
            self.update_selected_layer_information
        )
        self.vector_layer_combo.currentIndexChanged.connect(
            self.update_filter_summary
        )
        self.longitude_edit.textChanged.connect(
            self.update_filter_summary
        )
        self.latitude_edit.textChanged.connect(
            self.update_filter_summary
        )

        self.search_button.clicked.connect(
            self.handle_search_action
        )
        self.download_full_button.clicked.connect(self.download_full_alerts)
        self.clear_filters_button.clicked.connect(
            self.clear_filters
        )
        self.cancel_search_button.clicked.connect(
            lambda: self.api_client.cancel_current_request()
        )
        self.period_type_combo.currentIndexChanged.connect(
            self.update_filter_summary
        )
        self.start_date_edit.dateChanged.connect(
            self.update_filter_summary
        )
        self.end_date_edit.dateChanged.connect(
            self.update_filter_summary
        )
        self.alert_code_edit.textChanged.connect(
            self.update_filter_summary
        )
        self.alert_code_edit.textChanged.connect(
            self.clear_alert_code_validation
        )
        self.car_code_edit.textChanged.connect(
            self.update_filter_summary
        )
        self.car_code_edit.textChanged.connect(
            self.validate_car_code
        )
        self.minimum_area_spin.valueChanged.connect(
            self.update_filter_summary
        )
        self.source_combo.selectionChanged.connect(
            self.update_filter_summary
        )
        self.biome_combo.selectionChanged.connect(self.update_filter_summary)
        self.area_biome_radio.toggled.connect(self.update_area_controls)
        self.source_combo.selectionChanged.connect(
            self.update_selected_sources_label
        )
        self.source_mode_combo.currentIndexChanged.connect(
            self.update_filter_summary
        )
        self.crossing_field_combo.currentIndexChanged.connect(
            self.update_filter_summary
        )
        self.crossing_mode_combo.currentIndexChanged.connect(
            self.update_filter_summary
        )

        self.open_table_button.clicked.connect(
            self.with_full_layer(self.open_result_table)
        )

        self.remove_layer_button.clicked.connect(
            self.remove_result_layer
        )
        self.layers_export_csv_button.clicked.connect(
            self.with_full_layer(lambda: self.export_filtered_csv("full"))
        )
        self.layers_export_xlsx_button.clicked.connect(
            self.with_full_layer(self.export_attribute_table_xlsx)
        )
        self.layers_export_gpkg_button.clicked.connect(
            self.with_full_layer(lambda: self.export_vector_layer("GPKG"))
        )
        self.layers_export_shp_button.clicked.connect(
            self.with_full_layer(
                lambda: self.export_vector_layer("ESRI Shapefile")
            )
        )
        self.analysis_layer_combo.currentIndexChanged.connect(
            self.change_analysis_layer
        )
        self.comparison_layer_combo.currentIndexChanged.connect(
            self.change_comparison_layer
        )
        self.export_summary_button.clicked.connect(
            self.with_full_layer(self.export_result_summary)
        )

        self.apply_chart_button.clicked.connect(
            self.with_full_layer(self.apply_chart_analysis)
        )
        self.chart_metric_combo.currentIndexChanged.connect(
            self.update_chart_configuration_controls
        )
        self.chart_group_combo.currentIndexChanged.connect(
            self.update_chart_configuration_controls
        )
        self.chart_type_combo.currentIndexChanged.connect(
            self.mark_chart_configuration_pending
        )
        self.chart_value_combo.currentIndexChanged.connect(
            self.mark_chart_configuration_pending
        )
        self.chart_source_mode_combo.currentIndexChanged.connect(
            self.mark_chart_configuration_pending
        )
        self.chart_category_combo.currentIndexChanged.connect(
            self.mark_chart_configuration_pending
        )
        self.chart_limit_spin.valueChanged.connect(
            self.mark_chart_configuration_pending
        )
        self.export_chart_button.clicked.connect(
            self.export_chart_png
        )
        self.export_csv_button.clicked.connect(
            self.with_full_layer(
                lambda: self.export_filtered_csv("main", chart_filter=True)
            )
        )
        self.expand_chart_button.clicked.connect(self.open_chart_window)
        self.export_gpkg_button.clicked.connect(
            self.with_full_layer(
                lambda: self.export_vector_layer("GPKG", chart_filter=True)
            )
        )
        self.export_shp_button.clicked.connect(
            self.with_full_layer(
                lambda: self.export_vector_layer(
                    "ESRI Shapefile", chart_filter=True
                )
            )
        )
        self.identify_alert_button.clicked.connect(
            self.with_full_layer(self.activate_alert_identification)
        )
        self.open_report_button.clicked.connect(
            self.open_current_alert_report
        )
        self.previous_alert_button.clicked.connect(
            lambda: self.navigate_alert(-1)
        )
        self.next_alert_button.clicked.connect(
            lambda: self.navigate_alert(1)
        )
        self.same_crossing_button.clicked.connect(
            self.show_same_crossing_alerts
        )
        self.close_same_property_button.clicked.connect(
            self.close_same_property_view
        )
        self.detail_crossing_combo.currentIndexChanged.connect(
            self.update_same_property_button
        )
        self.same_crossing_list.itemActivated.connect(
            self.open_same_crossing_alert
        )

        self.login_button.clicked.connect(self.login_api)
        self.logout_button.clicked.connect(self.logout_api)
        self.password_edit.returnPressed.connect(self.login_api)
        self.remember_login_checkbox.toggled.connect(
            self.handle_remember_login_changed
        )

    def connect_project_signals(self):
        if self.project_signals_connected:
            return

        project = QgsProject.instance()

        project.layersAdded.connect(
            self.refresh_vector_layers
        )

        project.layersRemoved.connect(self.handle_project_layers_removed)

        self.project_signals_connected = True

    def disconnect_project_signals(self):
        if not self.project_signals_connected:
            return

        project = QgsProject.instance()

        try:
            project.layersAdded.disconnect(
                self.refresh_vector_layers
            )
        except (
            TypeError,
            RuntimeError,
        ):
            pass

        try:
            project.layersRemoved.disconnect(self.handle_project_layers_removed)
        except (
            TypeError,
            RuntimeError,
        ):
            pass

        self.project_signals_connected = False

    def handle_project_layers_removed(self, layer_ids):
        for layer_id in layer_ids:
            self.cleanup_result_temporary_file(layer_id)
            self.territory_rows_by_layer.pop(layer_id, None)
            self.territory_categories_done.pop(layer_id, None)
            self.layer_comparison_cache.pop(layer_id, None)
            self.alert_code_index_by_layer.pop(layer_id, None)
            self.alert_order_by_layer.pop(layer_id, None)
            self.alert_position_by_layer.pop(layer_id, None)
        self.refresh_vector_layers()

    def refresh_vector_layers(
        self,
        *args,
    ):
        previous_id = (
            self.vector_layer_combo
            .currentData()
        )

        self.vector_layer_combo.blockSignals(
            True
        )

        self.vector_layer_combo.clear()

        self.vector_layer_combo.addItem(
            self.tr("Selecione uma camada vetorial"),
            None,
        )

        layers = []

        for layer in (
            QgsProject.instance()
            .mapLayers()
            .values()
        ):
            if (
                layer.type()
                == QgsMapLayerType.VectorLayer
                and layer.id() not in self.result_layer_ids
            ):
                layers.append(layer)

        layers.sort(
            key=lambda layer: (
                layer.name().lower()
            )
        )

        selected_index = 0

        for layer in layers:
            self.vector_layer_combo.addItem(
                layer.name(),
                layer.id(),
            )

            if layer.id() == previous_id:
                selected_index = (
                    self.vector_layer_combo.count()
                    - 1
                )

        self.vector_layer_combo.setCurrentIndex(
            selected_index
        )

        self.vector_layer_combo.blockSignals(
            False
        )
        if hasattr(self, "analysis_layer_combo"):
            self.refresh_analysis_layers()

        self.update_area_controls()

    def selected_vector_layer(self):
        layer_id = (
            self.vector_layer_combo
            .currentData()
        )

        if not layer_id:
            return None

        layer = (
            QgsProject.instance()
            .mapLayer(layer_id)
        )

        if (
            layer is None
            or layer.type()
            != QgsMapLayerType.VectorLayer
        ):
            return None

        return layer

    def update_selected_layer_information(
        self,
    ):
        using_layer = self.area_layer_radio.isChecked()

        if not using_layer:
            self.layer_information_label.hide()
            return

        self.layer_information_label.show()

        layer = self.selected_vector_layer()

        if layer is None:
            self.layer_information_label.setText(
                self.tr("Selecione uma camada vetorial.")
            )
            return

        self.layer_information_label.setText(
            self.tr(
                "{} feição(ões) na camada.",
                layer.featureCount(),
            )
        )

    def update_area_controls(self):
        use_country = self.area_country_radio.isChecked()
        use_layer = self.area_layer_radio.isChecked()

        use_coordinates = (
            self.area_coordinates_radio
            .isChecked()
        )
        use_alert_code = self.area_alert_code_radio.isChecked()
        use_car = self.area_car_radio.isChecked()
        exclusive_mode = use_coordinates or use_alert_code or use_car

        self.vector_layer_field.setVisible(use_layer)
        self.biome_frame.setVisible(self.area_biome_radio.isChecked())

        self.layer_information_label.setVisible(
            use_layer
        )
        self.coordinates_frame.setVisible(use_coordinates)
        self.alert_code_frame.setVisible(use_alert_code)
        self.car_code_frame.setVisible(use_car)
        self.country_area_information_label.setVisible(use_country)
        self.period_section.setEnabled(not exclusive_mode)
        self.filter_section.setEnabled(not exclusive_mode)
        self.crossing_section.setEnabled(not exclusive_mode)
        self.period_section.set_expanded(not exclusive_mode)
        self.filter_section.set_expanded(not exclusive_mode)
        if exclusive_mode:
            self.crossing_section.set_expanded(False)
        if use_country:
            self.country_area_information_label.setText(
                self.tr(
                    "A consulta abrangerá todo o {}. Use período, área "
                    "mínima e fontes para limitar o volume.",
                    self.country_combo.currentText(),
                )
            )

        self.update_selected_layer_information()
        if hasattr(self, "filter_summary_label"):
            self.update_filter_summary()
        self.validate_search_period()

    def update_selected_sources_label(self, *args):
        labels = self.source_combo.checked_labels()
        self.selected_sources_label.setText(
            ", ".join(labels) if labels else self.tr("Todas as fontes")
        )

    def clear_alert_code_validation(self, *args):
        if hasattr(self, "alert_code_validation_label"):
            self.alert_code_validation_label.clear()
            self.alert_code_validation_label.setVisible(False)

    def validate_search_period(self, *args):
        """Shows the period warning directly in the panel (near the date
        fields), instead of QGIS's message bar — more discreet and in
        the right context, since it's a form validation, not a system
        event."""
        if not hasattr(self, "period_validation_label"):
            return
        exclusive_search = (
            self.area_coordinates_radio.isChecked()
            or self.area_alert_code_radio.isChecked()
            or self.area_car_radio.isChecked()
        )
        if exclusive_search:
            self.period_validation_label.clear()
            self.period_validation_label.setVisible(False)
            return
        start_date = self.start_date_edit.date()
        end_date = self.end_date_edit.date()
        if start_date > end_date:
            self.period_validation_label.setText(
                self.tr("A data inicial não pode ser posterior à data final.")
            )
            self.period_validation_label.setVisible(True)
        elif start_date.daysTo(end_date) > self.MAX_SEARCH_PERIOD_DAYS:
            self.period_validation_label.setText(
                self.tr(
                    "O período selecionado tem mais de 1 ano. Reduza o "
                    "intervalo de datas — se precisar de um período "
                    "maior, faça mais de uma busca (uma para cada ano, "
                    "por exemplo)."
                )
            )
            self.period_validation_label.setVisible(True)
        else:
            self.period_validation_label.clear()
            self.period_validation_label.setVisible(False)

    def validate_car_code(self, *args, show_empty=False):
        original_code = self.car_code_edit.text()
        code = re.sub(
            r"\s+", "",
            original_code.strip().upper()
            .replace("–", "-")
            .replace("—", "-"),
        )
        if not code:
            if show_empty:
                self.car_validation_label.setText(
                    self.tr("Informe o código do imóvel rural.")
                )
            else:
                self.car_validation_label.clear()
            self.car_code_edit.setStyleSheet("")
            return not show_empty
        if self.country_combo.currentData() != "BR":
            self.car_validation_label.setText(
                self.tr(
                    "A validação do formato depende do cadastro do "
                    "país selecionado."
                )
            )
            self.car_code_edit.setStyleSheet("")
            return True
        valid = bool(re.fullmatch(r"[A-Z]{2}-\d{7}-[A-F0-9]{32}", code))
        if valid:
            if code != original_code:
                self.car_code_edit.blockSignals(True)
                self.car_code_edit.setText(code)
                self.car_code_edit.blockSignals(False)
            self.car_validation_label.setText(
                self.tr("Formato do código CAR válido.")
            )
            self.car_code_edit.setStyleSheet("")
        else:
            self.car_validation_label.setText(
                self.tr(
                    "Formato inválido. Use UF-0000000-"
                    "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX."
                )
            )
            self.car_code_edit.setStyleSheet("border: 1px solid #B3261E;")
        return valid

    def update_section_summaries(self, area_text):
        """Texts shown on the right of each Filters section while it is
        collapsed (v2)."""
        if not hasattr(self, "crossing_section"):
            return
        self.area_section.set_summary(area_text)
        self.period_section.set_summary(
            "{} · {} – {}".format(
                self.period_type_combo.currentText(),
                self.start_date_edit.date().toString("dd/MM/yyyy"),
                self.end_date_edit.date().toString("dd/MM/yyyy"),
            )
        )
        filter_parts = []
        filter_parts.append(
            self.tr("área ≥ {} ha", self.format_decimal(
                self.minimum_area_spin.value()
            ))
        )
        sources = self.source_combo.checked_labels()
        filter_parts.append(
            ", ".join(sources) if sources else self.tr("Todas as fontes")
        )
        self.filter_section.set_summary(" · ".join(filter_parts))
        crossing_parts = [self.crossing_mode_combo.currentText()]
        if self.crossing_mode_combo.currentData() != "all":
            crossing_parts.append(self.crossing_field_combo.currentText())
        crossing_parts.append(
            self.tr("com dados de cruzamento")
            if self.include_analytics_checkbox.isChecked()
            else self.tr("sem dados de cruzamento")
        )
        self.crossing_section.set_summary(" · ".join(crossing_parts))

    def update_filter_summary(self, *args):
        if not hasattr(self, "filter_summary_label"):
            return

        if self.area_country_radio.isChecked():
            area = self.tr("Todo o {}", self.country_combo.currentText())
        elif self.area_biome_radio.isChecked():
            names = self.biome_combo.checked_labels()
            area = ", ".join(names) if names else self.tr("Bioma")
        elif self.area_layer_radio.isChecked():
            area = self.vector_layer_combo.currentText() or self.tr(
                "Camada vetorial"
            )
        elif self.area_alert_code_radio.isChecked():
            code = self.alert_code_edit.text().strip()
            area = self.tr(
                "Código do alerta{}",
                " {}".format(code) if code else "",
            )
        elif self.area_car_radio.isChecked():
            car_code = self.car_code_edit.text().strip()
            area = self.tr(
                "Imóvel rural{}",
                " {}".format(car_code) if car_code else "",
            )
        else:
            longitude = self.longitude_edit.text().strip()
            latitude = self.latitude_edit.text().strip()
            area = (
                "{}, {}".format(longitude, latitude)
                if longitude and latitude
                else self.tr("Coordenadas")
            )

        if (
            self.area_coordinates_radio.isChecked()
            or self.area_alert_code_radio.isChecked()
            or self.area_car_radio.isChecked()
        ):
            self.filter_summary_label.setText(
                self.tr(
                    "{} · {} · sem filtros adicionais",
                    self.country_combo.currentText(), area,
                )
            )
            return

        sources = self.source_combo.checked_data()
        source_text = (
            self.tr(
                "{} fonte(s) — {}",
                len(sources), self.source_mode_combo.currentText(),
            )
            if sources
            else self.tr("Todas as fontes")
        )
        self.update_section_summaries(area)
        extras = []
        if self.minimum_area_spin.value() > 0:
            extras.append(
                self.tr(
                    "mín. {} ha",
                    self.format_decimal(self.minimum_area_spin.value()),
                )
            )
        if self.crossing_mode_combo.currentData() != "all":
            extras.append(
                "{} — {}".format(
                    self.crossing_mode_combo.currentText(),
                    self.crossing_field_combo.currentText(),
                )
            )
        summary = self.tr(
            "{} · {} · {} a {} · {}",
            self.country_combo.currentText(),
            area,
            self.start_date_edit.date().toString("dd/MM/yyyy"),
            self.end_date_edit.date().toString("dd/MM/yyyy"),
            source_text,
        )
        if extras:
            summary += " · " + " · ".join(extras)
        self.filter_summary_label.setText(summary)

    def layout_area_buttons(self, columns):
        """Area-of-interest options two per row, or one per row in very
        narrow docks."""
        if columns == self._area_grid_columns:
            return
        self._area_grid_columns = columns
        for button in self.area_grid_buttons:
            self.area_grid.removeWidget(button)
        for index, button in enumerate(self.area_grid_buttons):
            self.area_grid.addWidget(
                button, index // columns, index % columns
            )
        self.area_grid.setColumnStretch(0, 1)
        self.area_grid.setColumnStretch(1, 1 if columns == 2 else 0)

    def set_quick_period(self, days):
        """Quick ranges of the Period section: last N days, or the current
        year so far (days=None)."""
        today = QDate.currentDate()
        if days is None:
            start = QDate(today.year(), 1, 1)
        else:
            start = today.addDays(-(int(days) - 1))
        self.end_date_edit.setDate(today)
        self.start_date_edit.setDate(start)

    def clear_filters(self):
        if (
            self.identify_tool is not None
            and self.iface is not None
            and self.iface.mapCanvas().mapTool() is self.identify_tool
        ):
            self.iface.mapCanvas().unsetMapTool(self.identify_tool)
        self.identify_tool = None
        self.remove_all_result_layers()
        self.area_country_radio.setChecked(True)
        self.period_type_combo.setCurrentIndex(0)
        self.end_date_edit.setDate(QDate.currentDate())
        self.start_date_edit.setDate(QDate.currentDate().addMonths(-1))
        self.alert_code_edit.clear()
        self.car_code_edit.clear()
        self.minimum_area_spin.setValue(0)
        self.source_combo.clear_checks()
        if hasattr(self, "biome_combo"):
            self.biome_combo.clear_checks()
        self.source_mode_combo.setCurrentIndex(0)
        self.crossing_mode_combo.setCurrentIndex(0)
        if self.crossing_field_combo.count():
            self.crossing_field_combo.setCurrentIndex(0)
        self.longitude_edit.clear()
        self.latitude_edit.clear()
        self.update_area_controls()
        self.update_filter_summary()

    def get_search_bbox(self):
        target_crs = (
            QgsCoordinateReferenceSystem(
                self.api_client.CRS
            )
        )

        if self.area_country_radio.isChecked():
            return None

        if self.area_biome_radio.isChecked():
            # Clipped by the API through territoryIds, not by a rectangle.
            return None

        if self.area_layer_radio.isChecked():
            layer = self.selected_vector_layer()

            if layer is None:
                raise ValueError(
                    "Selecione uma camada vetorial."
                )

            rectangle = layer.extent()

            return self.transform_rectangle(
                rectangle,
                layer.crs(),
                target_crs,
            )

        if self.area_coordinates_radio.isChecked():
            longitude_text = (
                self.longitude_edit.text()
                .strip()
                .replace(",", ".")
            )

            latitude_text = (
                self.latitude_edit.text()
                .strip()
                .replace(",", ".")
            )

            if (
                not longitude_text
                or not latitude_text
            ):
                raise ValueError(
                    "Informe a longitude "
                    "e a latitude."
                )

            longitude = float(
                longitude_text
            )

            latitude = float(
                latitude_text
            )

            if not -180 <= longitude <= 180:
                raise ValueError(
                    "A longitude deve estar "
                    "entre -180 e 180."
                )

            if not -90 <= latitude <= 90:
                raise ValueError(
                    "A latitude deve estar "
                    "entre -90 e 90."
                )

            margin = 0.001

            rectangle = QgsRectangle(
                longitude - margin,
                latitude - margin,
                longitude + margin,
                latitude + margin,
            )

            return self.transform_rectangle(
                rectangle,
                QgsCoordinateReferenceSystem(
                    "EPSG:4326"
                ),
                target_crs,
            )

        return None

    def vector_area_geometry(self, target_crs):
        """Merges the area-of-interest layer's geometries in the requested CRS."""
        if not self.area_layer_radio.isChecked():
            return None

        layer = self.selected_vector_layer()
        if layer is None:
            raise ValueError("Selecione uma camada vetorial.")

        coordinate_transform = None
        if layer.crs() != target_crs:
            coordinate_transform = QgsCoordinateTransform(
                layer.crs(),
                target_crs,
                QgsProject.instance(),
            )

        geometries = []
        for feature in layer.getFeatures():
            if not feature.hasGeometry():
                continue
            geometry = QgsGeometry(feature.geometry())
            if geometry.isEmpty():
                continue
            if coordinate_transform is not None:
                geometry.transform(coordinate_transform)
            geometries.append(geometry)

        if not geometries:
            raise ValueError(
                "A camada selecionada não possui geometrias válidas."
            )

        area_geometry = QgsGeometry.unaryUnion(geometries)
        if area_geometry.isNull() or area_geometry.isEmpty():
            raise ValueError(
                "Não foi possível construir a área de interesse."
            )
        return area_geometry

    def filter_layer_by_vector_area(self, layer):
        """Keeps only alerts that actually intersect the vector layer."""
        area_geometry = self.vector_area_geometry(layer.crs())
        if area_geometry is None:
            return layer

        # The area-of-interest geometry (e.g. a biome's outline) can have
        # tens of thousands of vertices. Testing .intersects()/
        # .intersection() of every alert against this full geometry
        # without preparation is the main reason the query used to hang
        # for several minutes at the "FINALIZANDO" step when the area of
        # interest is complex and there are many alerts — each call
        # redoes the geometry's internal indexing from scratch. A
        # prepared QgsGeometryEngine does that indexing once and reuses
        # it across every subsequent test (typically an order of
        # magnitude faster for complex geometries).
        engine = QgsGeometry.createGeometryEngine(area_geometry.constGet())
        engine.prepareGeometry()

        candidate_request = QgsFeatureRequest().setFilterRect(
            area_geometry.boundingBox()
        )
        matching_ids = []
        processed = 0
        for feature in layer.getFeatures(candidate_request):
            if (
                feature.hasGeometry()
                and engine.intersects(feature.geometry().constGet())
            ):
                matching_ids.append(feature.id())
            processed += 1
            if processed % 200 == 0:
                # Keeps the UI responsive during large queries instead of
                # freezing QGIS until processing finishes.
                QgsApplication.processEvents()

        filtered_layer = layer.materialize(
            QgsFeatureRequest().setFilterFids(matching_ids)
        )
        filtered_layer.setName(layer.name())

        if not filtered_layer.isValid():
            raise RuntimeError(
                "Não foi possível aplicar a interseção "
                "com a camada vetorial."
            )
        filtered_layer.dataProvider().addAttributes(
            [
                QgsField("IntAreaHa", QMetaType.Type.Double, len=20, prec=4),
                QgsField("IntPct", QMetaType.Type.Double, len=10, prec=2),
            ]
        )
        filtered_layer.updateFields()
        area_index = filtered_layer.fields().indexOf("IntAreaHa")
        percent_index = filtered_layer.fields().indexOf("IntPct")
        official_area_field = self.find_existing_field(
            filtered_layer, ["AreaHa", "area_ha", "area"]
        )
        equal_area_crs = QgsCoordinateReferenceSystem("EPSG:6933")
        transform = QgsCoordinateTransform(
            filtered_layer.crs(), equal_area_crs, QgsProject.instance()
        )
        changes = {}
        processed = 0
        for feature in filtered_layer.getFeatures():
            processed += 1
            if processed % 200 == 0:
                QgsApplication.processEvents()
            geometry = feature.geometry()
            official_area = (
                float(feature[official_area_field] or 0)
                if official_area_field
                else 0
            )
            # The most expensive step here isn't the boolean test
            # (.intersects/.contains, which the prepared geometry
            # resolves fast) — it's .intersection() itself, which
            # actually clips the polygon against an area-of-interest
            # geometry with many thousands of vertices (a biome's
            # outline, for instance). Since an alert's polygon is tiny by
            # comparison, the vast majority fall ENTIRELY inside the area
            # of interest — in that case the "intersection" is the alert
            # itself, with no clipping needed. We only call .intersection()
            # (and the reprojection/measurement that follows) for the
            # alert that actually crosses the area-of-interest boundary —
            # a minority. This avoids the heaviest work for most alerts
            # in any query.
            if engine.contains(geometry.constGet()):
                intersection_area = official_area
                if intersection_area <= 0:
                    measured = QgsGeometry(geometry)
                    measured.transform(transform)
                    intersection_area = measured.area() / 10000.0
            else:
                intersection_abstract = engine.intersection(
                    geometry.constGet()
                )
                intersection = (
                    QgsGeometry(intersection_abstract)
                    if intersection_abstract is not None
                    else QgsGeometry()
                )
                if intersection.isNull() or intersection.isEmpty():
                    continue
                intersection.transform(transform)
                intersection_area = intersection.area() / 10000.0
            changes[feature.id()] = {
                area_index: intersection_area,
                percent_index: (
                    min(100.0, intersection_area * 100.0 / official_area)
                    if official_area > 0 else None
                ),
            }
        filtered_layer.dataProvider().changeAttributeValues(changes)
        return filtered_layer

    TERRITORY_CATEGORY_CHOICES = (
        ("", "Detectar automaticamente"),
        ("TerraIndig", "Terra indígena"),
        ("UnidConserv", "Unidade de conservação"),
        ("Assentamento", "Assentamento"),
        ("Quilombo", "Território quilombola"),
        ("Municipio", "Município"),
        ("Estado", "Estado / departamento"),
        ("Bioma", "Bioma"),
    )

    def area_layer_territory_category(self, layer):
        """Category chosen by the user for the area-of-interest layer, or
        the automatic guess when left on "Detectar automaticamente"."""
        return self.selected_territory_category(layer)

    @classmethod
    def selected_territory_category(cls, layer):
        """Identifies the territorial category of the chosen vector layer.

        The layer NAME is checked before the field names: a layer of
        indigenous lands usually also carries a municipality/state column,
        and matching on fields first labelled every TI crossing as
        "Municipio". Short abbreviations (TI, UC) only count as whole
        words of the name."""
        if layer is None:
            return ""
        name_words = {
            cls.normalize_source_name(word)
            for word in re.split(r"[^0-9A-Za-zÀ-ÿ]+", layer.name())
            if word
        }
        word_aliases = (
            (("ti", "tis", "funai"), "TerraIndig"),
            (("uc", "ucs", "snuc"), "UnidConserv"),
        )
        for aliases, category in word_aliases:
            if name_words & set(aliases):
                return category
        name_signature = cls.normalize_source_name(layer.name())
        field_signature = cls.normalize_source_name(
            " ".join(field.name() for field in layer.fields())
        )
        categories = (
            (("assent",), "Assentamento"),
            (("terraindig", "indigenous", "indigena"), "TerraIndig"),
            (("quilomb",), "Quilombo"),
            (("unidadeconserv", "unidconserv", "conservationunit"),
             "UnidConserv"),
            (("reservabio", "biosfera"), "ReservaBio"),
            (("manejoflorest", "forestmanagement"), "ManFlorest"),
            (("protecaointegral", "protintegral"), "ProtIntegral"),
            (("usosustent", "sustainableuse"), "UsoSustent"),
            (("reservalegal", "legalreserve"), "ReservaLegal"),
            (("territorioespecial", "terrespecial"), "TerrEspecial"),
            (("geoparque", "geopark"), "Geoparque"),
            (("municip", "cidade", "city"), "Municipio"),
            (("estado", "state"), "Estado"),
            (("bioma", "biome"), "Bioma"),
        )
        for signature in (name_signature, field_signature):
            for aliases, category in categories:
                if any(alias in signature for alias in aliases):
                    return category
        return ""

    @classmethod
    def territory_label_from_feature(cls, layer, feature, category):
        """Gets a territorial feature's name without mixing up its neighbors."""
        category_candidates = {
            "Assentamento": ("assentamento", "nomeassentamento"),
            "TerraIndig": (
                "terraindigena", "nometi", "terindig", "terrainom",
                "terrai_nom", "nome_ti",
            ),
            "Quilombo": ("quilombo", "nomequilombo"),
            "UnidConserv": ("unidadeconservacao", "nomeuc", "unidconserv"),
            "Municipio": ("municipio", "nomemunicipio", "cidade"),
            "Estado": ("estado", "nomeestado", "uf"),
            "Bioma": ("bioma", "nomebioma"),
        }
        candidates = category_candidates.get(category, ()) + (
            "territorio", "territory", "nome", "name", "nm", "label",
        )
        available = {
            cls.normalize_source_name(field.name()): field.name()
            for field in layer.fields()
        }
        for candidate in candidates:
            field_name = available.get(cls.normalize_source_name(candidate))
            if not field_name:
                continue
            values = MapBiomasApiClient.value_list(feature[field_name])
            for value in values or [feature[field_name]]:
                label = cls.format_area_label(value)
                if label:
                    return label
        return "{} — feição {}".format(
            cls.format_area_label(layer.name()) or "Território",
            feature.id(),
        )

    def populate_selected_area_territory_rows(self, result_layer):
        """Computes alert ∩ each selected territory, in hectares."""
        if not self.area_layer_radio.isChecked():
            return []
        source_layer = self.selected_vector_layer()
        category = self.area_layer_territory_category(source_layer)
        if source_layer is None or not category:
            return []

        source_transform = None
        if source_layer.crs() != result_layer.crs():
            source_transform = QgsCoordinateTransform(
                source_layer.crs(), result_layer.crs(), QgsProject.instance()
            )
        geometries = {}
        engines = {}
        labels = {}
        spatial_index = QgsSpatialIndex()
        for source_feature in source_layer.getFeatures():
            if not source_feature.hasGeometry():
                continue
            geometry = QgsGeometry(source_feature.geometry())
            if geometry.isNull() or geometry.isEmpty():
                continue
            if source_transform is not None:
                geometry.transform(source_transform)
            indexed_feature = QgsFeature()
            indexed_feature.setId(source_feature.id())
            indexed_feature.setGeometry(geometry)
            spatial_index.addFeature(indexed_feature)
            geometries[source_feature.id()] = geometry
            # Prepare each territory's geometry once here (reused by all
            # alerts afterward) — the same pattern used in
            # filter_layer_by_vector_area: testing "contains" with a
            # prepared geometry is fast, and most alerts sit entirely
            # within a single territory, so it avoids the full geometric
            # clip (.intersection), which is the really expensive part of
            # this computation.
            engine = QgsGeometry.createGeometryEngine(geometry.constGet())
            engine.prepareGeometry()
            engines[source_feature.id()] = engine
            labels[source_feature.id()] = self.territory_label_from_feature(
                source_layer, source_feature, category
            )

        code_field = self.find_existing_field(
            result_layer, ["CodeAlerta", "alertCode", "codigo"]
        )
        if not geometries or code_field is None:
            return []
        equal_area_crs = QgsCoordinateReferenceSystem("EPSG:6933")
        area_transform = QgsCoordinateTransform(
            result_layer.crs(), equal_area_crs, QgsProject.instance()
        )
        rows = []
        processed = 0
        for alert in result_layer.getFeatures():
            processed += 1
            if processed % 200 == 0:
                QgsApplication.processEvents()
            if not alert.hasGeometry():
                continue
            alert_geometry = alert.geometry()
            alert_area_ha = None
            for territory_id in spatial_index.intersects(
                alert_geometry.boundingBox()
            ):
                if engines[territory_id].contains(
                    alert_geometry.constGet()
                ):
                    if alert_area_ha is None:
                        measured = QgsGeometry(alert_geometry)
                        measured.transform(area_transform)
                        alert_area_ha = measured.area() / 10000.0
                    area_ha = alert_area_ha
                else:
                    intersection_abstract = engines[territory_id].intersection(
                        alert_geometry.constGet()
                    )
                    intersection = (
                        QgsGeometry(intersection_abstract)
                        if intersection_abstract is not None
                        else QgsGeometry()
                    )
                    if intersection.isNull() or intersection.isEmpty():
                        continue
                    measured = QgsGeometry(intersection)
                    measured.transform(area_transform)
                    area_ha = measured.area() / 10000.0
                if area_ha > 0:
                    rows.append((
                        str(alert[code_field] or ""),
                        category,
                        labels[territory_id],
                        area_ha,
                    ))
        if rows:
            self.territory_rows_by_layer[result_layer.id()] = rows
            for name, length in (
                ("SelTerrCat", 50),
                ("SelTerrs", 0),
                ("SelTerrAreas", 0),
            ):
                if result_layer.fields().indexOf(name) < 0:
                    result_layer.dataProvider().addAttributes([
                        QgsField(name, QMetaType.Type.QString, len=length)
                    ])
            result_layer.updateFields()
            field_indexes = {
                name: result_layer.fields().indexOf(name)
                for name in ("SelTerrCat", "SelTerrs", "SelTerrAreas")
            }
            areas_by_code = {}
            for code, _row_category, territory, area_ha in rows:
                code_areas = areas_by_code.setdefault(code, {})
                code_areas[territory] = (
                    code_areas.get(territory, 0.0) + float(area_ha)
                )
            changes = {}
            for alert in result_layer.getFeatures():
                code = str(alert[code_field] or "")
                area_map = areas_by_code.get(code)
                if not area_map:
                    continue
                changes[alert.id()] = {
                    field_indexes["SelTerrCat"]: category,
                    field_indexes["SelTerrs"]: "; ".join(
                        sorted(area_map, key=str.casefold)
                    ),
                    field_indexes["SelTerrAreas"]: json.dumps(
                        area_map, ensure_ascii=False, separators=(",", ":")
                    ),
                }
            result_layer.dataProvider().changeAttributeValues(changes)
            self.apply_attribute_aliases(
                result_layer, self.api_client.country
            )
        return rows

    def filter_layer_by_coordinate(self, layer):
        if not self.area_coordinates_radio.isChecked():
            return layer
        longitude = float(
            self.longitude_edit.text().strip().replace(",", ".")
        )
        latitude = float(
            self.latitude_edit.text().strip().replace(",", ".")
        )
        point = QgsGeometry.fromPointXY(QgsPointXY(longitude, latitude))
        source_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        if layer.crs() != source_crs:
            transform = QgsCoordinateTransform(
                source_crs,
                layer.crs(),
                QgsProject.instance(),
            )
            point.transform(transform)

        matching_ids = [
            feature.id()
            for feature in layer.getFeatures(
                QgsFeatureRequest().setFilterRect(point.boundingBox())
            )
            if feature.hasGeometry() and feature.geometry().intersects(point)
        ]
        filtered = layer.materialize(
            QgsFeatureRequest().setFilterFids(matching_ids)
        )
        filtered.setName(layer.name())
        if not filtered.isValid():
            raise RuntimeError(
                "Não foi possível aplicar o filtro pelo ponto informado."
            )
        return filtered

    def filter_layer_by_sources(self, layer):
        selected_groups = [
            self.source_name_aliases(value)
            for value in self.source_combo.checked_data()
        ]
        if not selected_groups:
            return layer

        source_field = self.find_existing_field(
            layer, ["Fonte", "sources"]
        )
        if not source_field:
            return layer

        mode = self.source_mode_combo.currentData()
        matching_ids = []
        for feature in layer.getFeatures():
            available = {
                self.normalize_source_name(item)
                for item in MapBiomasApiClient.value_list(
                    feature[source_field]
                )
                if item.strip()
            }
            if self.sources_match(available, selected_groups, mode):
                matching_ids.append(feature.id())

        filtered = layer.materialize(
            QgsFeatureRequest().setFilterFids(matching_ids)
        )
        filtered.setName(layer.name())
        if not filtered.isValid():
            raise RuntimeError("Não foi possível aplicar o filtro de fontes.")
        return filtered

    @staticmethod
    def sources_match(available, selected_groups, mode):
        selected_matches = [
            bool(group & available)
            for group in selected_groups
        ]
        if mode == "any":
            return any(selected_matches)
        if not all(selected_matches):
            return False
        if mode != "exact":
            return True
        return all(
            any(source in group for group in selected_groups)
            for source in available
        )

    @staticmethod
    def normalize_source_name(value):
        text = unicodedata.normalize(
            "NFKD",
            str(value or ""),
        ).encode("ascii", "ignore").decode("ascii")
        return "".join(character for character in text.lower() if character.isalnum())

    @classmethod
    def source_name_aliases(cls, value):
        normalized = cls.normalize_source_name(value)
        aliases = {
            "prodesamazonia": {"prodesamazonia", "prodesamz"},
            "prodescerrado": {"prodescerrado", "prodescerr"},
        }
        return aliases.get(normalized, {normalized})

    @staticmethod
    def transform_rectangle(
        rectangle,
        source_crs,
        target_crs,
    ):
        if (
            rectangle is None
            or rectangle.isEmpty()
        ):
            raise ValueError(
                "A área de interesse está vazia."
            )

        if source_crs == target_crs:
            transformed = rectangle
        else:
            coordinate_transform = (
                QgsCoordinateTransform(
                    source_crs,
                    target_crs,
                    QgsProject.instance(),
                )
            )

            transformed = (
                coordinate_transform
                .transformBoundingBox(
                    rectangle
                )
            )

        return (
            transformed.xMinimum(),
            transformed.yMinimum(),
            transformed.xMaximum(),
            transformed.yMaximum(),
        )

    def handle_search_action(self):
        """Searches alerts, or leads the user to login when disconnected."""
        if not self.api_client.country.get("enabled"):
            self.show_warning(self.tr("O serviço ainda não está configurado."))
            return
        if not self.api_client.authenticated:
            self.login_section.set_expanded(True)
            self.login_status_label.setText(
                self.tr("Informe e-mail e senha para acessar a API.")
            )
            self.update_responsive_layout()
            QTimer.singleShot(0, self.focus_login_field)
            return
        self.search_alerts()

    def focus_login_field(self):
        """Places the cursor in the next required API-access field."""
        target = (
            self.email_edit
            if not self.email_edit.text().strip()
            else self.password_edit
        )
        target.setFocus(Qt.FocusReason.OtherFocusReason)
        target.selectAll()

    def search_alerts(self, force_full=False):
        if not self.country_notice_accepted():
            self.tabs.setCurrentWidget(self.notice_tab)
            self.show_warning(
                self.tr(
                    "Leia e aceite a nota informativa antes de buscar alertas."
                )
            )
            return
        config = country_config(
            self.country_combo.currentData()
        )
        if not config.get("enabled"):
            self.show_warning(
                config.get(
                    "status",
                    "O país ainda não possui serviço de dados configurado.",
                )
            )
            return

        if not self.api_client.authenticated:
            self.show_warning(
                self.tr(
                    "Entre na API MapBiomas Alerta antes de realizar a "
                    "consulta."
                )
            )
            return

        start_date = (
            self.start_date_edit.date()
        )

        end_date = (
            self.end_date_edit.date()
        )

        exclusive_search = (
            self.area_coordinates_radio.isChecked()
            or self.area_alert_code_radio.isChecked()
            or self.area_car_radio.isChecked()
        )

        # The visual warning already shows up directly in the panel, near
        # the date fields (validate_search_period, connected to the date
        # change) — here we just actually block the search, without
        # repeating the warning on the QGIS message bar.
        self.validate_search_period()
        if not exclusive_search and start_date > end_date:
            return

        if (
            not exclusive_search
            and start_date.daysTo(end_date) > self.MAX_SEARCH_PERIOD_DAYS
        ):
            return

        alert_code = (
            self.alert_code_edit.text().strip()
            if self.area_alert_code_radio.isChecked()
            else ""
        )

        if self.area_alert_code_radio.isChecked() and not alert_code:
            self.alert_code_validation_label.setText(
                self.tr("Informe o código do alerta.")
            )
            self.alert_code_validation_label.setVisible(True)
            return

        car_code = (
            self.car_code_edit.text().strip().upper()
            if self.area_car_radio.isChecked()
            else ""
        )
        if self.area_car_radio.isChecked() and not car_code:
            self.validate_car_code(show_empty=True)
            return
        if self.area_car_radio.isChecked() and not self.validate_car_code(
            show_empty=True
        ):
            return
        if self.area_car_radio.isChecked():
            car_code = self.car_code_edit.text().strip().upper()

        if (
            alert_code
            and not alert_code.isdigit()
        ):
            self.show_warning(
                self.tr(
                    "O código do alerta deve conter somente números."
                )
            )
            return

        period_type = (
            self.period_type_combo
            .currentData()
        )

        selected_sources = (
            [] if exclusive_search else self.source_combo.checked_data()
        )
        sources_for_api = (
            ["All"] if not selected_sources else list(selected_sources)
        )
        server_equivalent_area = bool(
            alert_code
            or car_code
            or self.area_country_radio.isChecked()
            or self.area_biome_radio.isChecked()
        )
        if (
            self.area_biome_radio.isChecked()
            and not self.selected_biome_filter()[0]
        ):
            self.show_warning(
                self.tr("Selecione ao menos um bioma para a busca.")
            )
            return
        server_equivalent_sources = bool(
            not selected_sources
            or self.source_mode_combo.currentData() == "any"
        )
        api_statistics_exact = bool(
            server_equivalent_area
            and server_equivalent_sources
            and (
                exclusive_search
                or self.crossing_mode_combo.currentData() == "all"
            )
        )
        # Filters the map server can't apply (source, crossing) simply go
        # straight to the full download — no blocking message.
        quick_view = (
            not force_full
            and bool(config.get("wms_url") and config.get("wms_layers"))
            and self.quick_view_checkbox.isChecked()
            and not exclusive_search
            and not selected_sources
            and self.crossing_mode_combo.currentData() == "all"
        )

        self.set_search_busy(True)
        temporary_path = None

        if quick_view:
            try:
                if self.run_quick_view(
                    config, start_date, end_date, period_type
                ):
                    self.set_search_busy(False)
                    return
            except QuickViewUnavailable as error:
                self.show_progress_message(
                    self.tr(
                        "Visualização rápida indisponível ({}). Baixando os "
                        "alertas pela API.",
                        self.tr(str(error)),
                    )
                )
            except QueryCancelledError as error:
                self.show_warning(self.tr(str(error)))
                self.set_search_busy(False)
                return
            except ApiAuthenticationError as error:
                self.handle_api_authentication_error(error)
                self.set_search_busy(False)
                return
            except Exception as error:
                self.show_error(self.tr(str(error)))
                self.set_search_busy(False)
                return

        try:
            alert_codes = None
            if car_code:
                property_summary = self.api_client.rural_property(car_code)
                if property_summary:
                    canonical_code = str(
                        property_summary.get("propertyCode") or car_code
                    ).strip().upper()
                    self.car_code_edit.blockSignals(True)
                    self.car_code_edit.setText(canonical_code)
                    self.car_code_edit.blockSignals(False)
                    self.car_code_edit.setStyleSheet("")
                    self.car_validation_label.setText(
                        self.tr("Código CAR reconhecido pela API.")
                    )
                alert_codes = [
                    alert.get("alertCode")
                    for alert in (property_summary.get("alerts") or [])
                    if alert.get("alertCode")
                ]
                if not alert_codes:
                    self.show_warning(
                        self.tr(
                            "Não existe imóvel com o código informado ou "
                            "ele não possui alertas."
                        )
                    )
                    return
            bbox = None if alert_code else self.get_search_bbox()
            territory_ids, territory_category, _biomes = (
                (None, None, []) if exclusive_search
                else self.selected_biome_filter()
            )
            # Exclusive searches (by alert code, by CAR, or by
            # coordinate) used not to send startDate/endDate, since the
            # chosen filter is already exact on its own. Except that
            # combination (alertCodes or carCodes with NO date at all) is
            # exactly what caused HTTP 500 in real-world tests — both for
            # alert-code and CAR search. Sending a very wide date range
            # here doesn't change which alerts come back (the chosen
            # filter is still exact), it just avoids that suspicious
            # combination.
            wide_date_range = (
                ("2018-01-01", "2030-12-31") if exclusive_search else (None, None)
            )

            # Before downloading the full geometry (which costs the most,
            # both in wait time and load on the API), query just the
            # count — the same summary query that already ran later, but
            # moved up here so a non-blocking warning can be shown.
            # Doesn't run for exclusive searches (alert code, CAR,
            # coordinate), which are already small by nature.
            precomputed_statistics = None
            if not exclusive_search:
                self.update_search_progress(0, 0, "summary")
                try:
                    precomputed_statistics = self.api_client.alerts_statistics(
                        start_date=start_date.toString("yyyy-MM-dd"),
                        end_date=end_date.toString("yyyy-MM-dd"),
                        period_type=period_type,
                        minimum_area=self.minimum_area_spin.value(),
                        sources=sources_for_api,
                        bbox=bbox,
                        territory_ids=territory_ids,
                        territory_category=territory_category,
                    )
                except Exception:
                    precomputed_statistics = None
                self.show_early_summary(
                    precomputed_statistics,
                    start_date,
                    end_date,
                    period_type,
                    approximate=self.area_layer_radio.isChecked(),
                    exact=api_statistics_exact,
                )
                estimated_total = (
                    (precomputed_statistics or {})
                    .get("summary", {})
                    .get("total")
                )
                if (
                    estimated_total is not None
                    and estimated_total > self.LARGE_SEARCH_WARNING_THRESHOLD
                ):
                    self.show_progress_message(
                        self.tr(
                            "Esta busca deve retornar aproximadamente {} "
                            "alertas e pode demorar um pouco. Períodos "
                            "mais curtos deixam a busca mais rápida.",
                            self.format_integer(estimated_total),
                        )
                    )

            download_result = (
                self.api_client
                .download_alerts(
                    start_date=(
                        wide_date_range[0]
                        if exclusive_search
                        else start_date.toString("yyyy-MM-dd")
                    ),
                    end_date=(
                        wide_date_range[1]
                        if exclusive_search
                        else end_date.toString("yyyy-MM-dd")
                    ),
                    period_type=period_type,
                    alert_code=(
                        alert_code or None
                    ),
                    # For CAR, pagination uses carCodes directly. The list
                    # obtained above only serves to validate that the
                    # property has alerts and doesn't need to be resent to
                    # the API.
                    alert_codes=(None if car_code else alert_codes),
                    property_codes=([car_code] if car_code else None),
                    minimum_area=(
                        0 if exclusive_search
                        else self.minimum_area_spin.value()
                    ),
                    sources=sources_for_api,
                    bbox=bbox,
                    territory_ids=territory_ids,
                    territory_category=territory_category,
                    crossing_field=(
                        None if exclusive_search
                        else self.crossing_field_combo.currentData()
                    ),
                    crossing_mode=(
                        "all" if exclusive_search
                        else self.crossing_mode_combo.currentData()
                    ),
                    include_analytics=(
                        self.include_analytics_checkbox.isChecked()
                    ),
                    fetch_statistics=api_statistics_exact,
                    precomputed_statistics=precomputed_statistics,
                    progress_callback=self.update_search_progress,
                )
            )
            temporary_path = download_result["path"]

            if download_result.get("feature_count", 0) == 0 and exclusive_search:
                MapBiomasApiClient.remove_temporary_file(temporary_path)
                temporary_path = None
                self.show_warning(
                    self.tr("Não existe alerta com o código informado.")
                    if self.area_alert_code_radio.isChecked()
                    else (
                        self.tr("O imóvel informado não possui alertas.")
                        if self.area_car_radio.isChecked()
                        else self.tr(
                            "Não existe alerta na coordenada indicada."
                        )
                    )
                )
                return

            layer_name = (
                self.create_result_layer_name(
                    None if exclusive_search else start_date,
                    None if exclusive_search else end_date,
                    alert_code,
                    period_type,
                )
            )

            result_layer = QgsVectorLayer(
                download_result["path"],
                layer_name,
                "ogr",
            )

            if not result_layer.isValid():
                raise RuntimeError(
                    "O QGIS recebeu o GeoJSON, "
                    "mas não conseguiu abri-lo."
                )

            if not alert_code:
                result_layer = self.filter_layer_by_vector_area(
                    result_layer
                )
                result_layer = self.filter_layer_by_coordinate(result_layer)
            if not exclusive_search:
                result_layer = self.filter_layer_by_sources(result_layer)

            result_layer.setName(
                self.create_result_layer_name(
                    None if exclusive_search else start_date,
                    None if exclusive_search else end_date,
                    alert_code,
                    period_type,
                    area_label=self.area_interest_label(result_layer),
                    car_code=car_code,
                )
            )

            if result_layer.featureCount() == 0 and exclusive_search:
                MapBiomasApiClient.remove_temporary_file(temporary_path)
                temporary_path = None
                if self.area_alert_code_radio.isChecked():
                    self.show_warning(
                        self.tr("Não existe alerta com o código informado.")
                    )
                elif self.area_car_radio.isChecked():
                    self.show_warning(
                        self.tr("O imóvel informado não possui alertas.")
                    )
                else:
                    self.show_warning(
                        self.tr("Não existe alerta na coordenada indicada.")
                    )
                return

            self.apply_result_style(
                result_layer, self.api_client.country
            )

            self.remove_quick_view_layer()
            QgsProject.instance().addMapLayer(
                result_layer
            )

            self.current_result_layer_id = (
                result_layer.id()
            )
            self.result_layer_ids.append(result_layer.id())
            self.result_temporary_files[result_layer.id()] = temporary_path
            temporary_path = None
            self.result_contexts[result_layer.id()] = {
                "start_date": None if exclusive_search else QDate(
                    start_date.year(), start_date.month(), start_date.day()
                ),
                "end_date": None if exclusive_search else QDate(
                    end_date.year(), end_date.month(), end_date.day()
                ),
                "period_type": period_type,
                "query_mode": (
                    "car" if car_code else
                    "alert_code" if alert_code else
                    "coordinates" if self.area_coordinates_radio.isChecked()
                    else "standard"
                ),
                "car_code": car_code or None,
                "api_statistics": download_result.get("api_statistics") or {},
                "api_statistics_exact": api_statistics_exact,
                "has_analytics": self.include_analytics_checkbox.isChecked(),
            }
            self.populate_selected_area_territory_rows(result_layer)
            # Full normalization (all ~18 territorial categories) is now
            # on demand — normalize_territory_area_rows(categories=...)
            # only computes what each screen actually needs, when it
            # needs it (e.g. only "Municipio" for the summary below;
            # UC/TI/Assentamento/etc. only if the user picks them in the
            # chart or exports crossings). This avoids decoding JSON for
            # ~18 categories on every large query when the user may never
            # even look at most of them.
            self.refresh_analysis_layers()

            self.update_result_summary(
                result_layer,
                None if exclusive_search else start_date,
                None if exclusive_search else end_date,
                period_type,
            )
            if self.crossing_mode_combo.currentData() != "all":
                self.result_status_label.setText(
                    self.tr(
                        "Consulta concluída. {} de {} alerta(s) atendem "
                        "à condição de cruzamento.",
                        self.format_integer(result_layer.featureCount()),
                        self.format_integer(
                            download_result["server_feature_count"]
                        ),
                    )
                )

            warnings = []
            if download_result.get("pagination_warning"):
                warnings.append(download_result["pagination_warning"])
            skipped = int(download_result.get("skipped_geometry_count") or 0)
            if skipped:
                warnings.append(
                    self.tr(
                        "{} alerta(s) foram ignorados por não possuírem "
                        "geometria válida.",
                        self.format_integer(skipped),
                    )
                )
                QgsMessageLog.logMessage(
                    "Alerts skipped because of invalid geometry: {}".format(
                        ", ".join(
                            download_result.get("skipped_geometry_codes") or []
                        )
                    ),
                    "MapBiomas Alerta Oficial",
                    Qgis.Warning,
                )
            if warnings:
                self.result_status_label.setText(
                    self.tr("Consulta carregada com ressalvas. ")
                    + " ".join(warnings)
                )
                self.show_warning(" ".join(warnings))

            self.update_result_controls()

            self.refresh_vector_layers()

            self.tabs.setCurrentWidget(
                self.results_tab
            )

            if (
                result_layer.featureCount()
                > 0
            ):
                self.zoom_to_result_layer()

            self.show_success(
                self.tr(
                    "{} alerta(s) carregado(s).",
                    self.format_integer(
                        result_layer.featureCount()
                    ),
                )
            )

        except QueryCancelledError as error:
            if temporary_path:
                MapBiomasApiClient.remove_temporary_file(temporary_path)
            self.show_warning(self.tr(str(error)))
        except ApiAuthenticationError as error:
            if temporary_path:
                MapBiomasApiClient.remove_temporary_file(temporary_path)
            self.handle_api_authentication_error(error)
        except Exception as error:
            if temporary_path:
                MapBiomasApiClient.remove_temporary_file(temporary_path)
            self.set_search_busy(False)
            self.show_error(
                self.tr(str(error))
            )

        finally:
            self.set_search_busy(False)
            QTimer.singleShot(
                0,
                lambda: self.set_search_busy(False),
            )

    @staticmethod
    def quick_view_cql(
        start_date, end_date, period_type, minimum_area, bbox, biomes=()
    ):
        """CQL filter for the GeoServer layer, mirroring the API filters
        the quick view supports (period, minimum area, rectangle)."""
        date_field = (
            "published_at"
            if period_type == MapBiomasApiClient.PERIOD_PUBLICATION
            else "detected_at"
        )
        parts = [
            "{} BETWEEN '{}' AND '{}'".format(
                date_field,
                start_date.toString("yyyy-MM-dd"),
                end_date.toString("yyyy-MM-dd"),
            )
        ]
        if minimum_area and float(minimum_area) > 0:
            parts.append("area_ha >= {:.4f}".format(float(minimum_area)))
        if biomes:
            # "biome" may list several names for an alert on a boundary.
            parts.append("({})".format(" OR ".join(
                "biome ILIKE '%{}%'".format(str(name).replace("'", "''"))
                for name in biomes
            )))
        if bbox is not None:
            parts.append(
                "BBOX(geom, {}, {}, {}, {})".format(
                    *[float(value) for value in bbox]
                )
            )
        return " AND ".join(parts)

    @staticmethod
    def quick_view_uri(wms_url, wms_layer, cql):
        """QGIS WMS provider URI. The CQL goes inside the url= value, so
        characters that would break the provider's own key=value&... list
        or GeoServer's comma-separated parameters are percent-encoded."""
        cql_encoded = (
            cql.replace("%", "%25")
            .replace("&", "%26")
            .replace(",", "%2C")
            .replace(" ", "%20")
            .replace("'", "%27")
        )
        return (
            "contextualWMSLegend=0&crs=EPSG:3857&dpiMode=7&format=image/png"
            "&layers={}&styles=&tilePixelRatio=0&url={}?CQL_FILTER%3D{}"
        ).format(wms_layer, wms_url, cql_encoded)

    def run_quick_view(self, config, start_date, end_date, period_type):
        """Adds a WMS layer filtered like the search, plus the API
        summary, without downloading any polygon. Returns True when the
        quick view was shown; raises QuickViewUnavailable when the map
        server can't serve this search (the caller then downloads)."""
        bbox = self.get_search_bbox()
        minimum_area = self.minimum_area_spin.value()
        biome_ids, biome_category, biome_names = self.selected_biome_filter()
        layer_name_on_server, supports_biome = self.pick_quick_view_layer(
            config
        )
        if biome_names and not supports_biome:
            raise QuickViewUnavailable(
                "a camada do servidor não permite filtrar por bioma"
            )
        self.update_search_progress(0, 0, "summary")
        statistics = self.api_client.alerts_statistics(
            start_date=start_date.toString("yyyy-MM-dd"),
            end_date=end_date.toString("yyyy-MM-dd"),
            period_type=period_type,
            minimum_area=minimum_area,
            sources=["All"],
            bbox=bbox,
            territory_ids=biome_ids,
            territory_category=biome_category,
        )
        summary = statistics.get("summary") or {}
        total = summary.get("total")
        if total == 0:
            self.show_warning(
                self.tr("Nenhum alerta encontrado para os filtros informados.")
            )
            return True

        cql = self.quick_view_cql(
            start_date, end_date, period_type, minimum_area, bbox,
            biome_names,
        )
        uri = self.quick_view_uri(config["wms_url"], layer_name_on_server, cql)
        # Same request as a plain URL, so it can be opened in a browser
        # when the map looks empty (see the QGIS log panel).
        QgsMessageLog.logMessage(
            "Quick view — test in a browser: {}?service=WMS&"
            "version=1.1.1&request=GetMap&layers={}&styles=&srs=EPSG:4326&"
            "bbox={}&width=800&height=800&format=image/png&CQL_FILTER={}".format(
                config["wms_url"], layer_name_on_server,
                ",".join(str(v) for v in (
                    bbox or config.get("extent") or (-180, -90, 180, 90)
                )),
                QUrl.toPercentEncoding(cql).data().decode(),
            ),
            "MapBiomas Alerta Oficial",
            Qgis.Info,
        )
        total_text = self.format_integer(total) if total is not None else "?"
        layer_name = "{} — {} ({})".format(
            self.create_result_layer_name(start_date, end_date, "", period_type),
            self.tr("visualização rápida"),
            total_text,
        )
        wms_layer = QgsRasterLayer(uri, layer_name, "wms")
        if not wms_layer.isValid():
            raise QuickViewUnavailable(
                "o servidor de mapas não respondeu"
            )
        self.remove_quick_view_layer()
        QgsProject.instance().addMapLayer(wms_layer)
        self._quick_view_state = {
            "layer_id": wms_layer.id(),
            "total": total,
            "area": summary.get("area"),
            "start_date": start_date,
            "end_date": end_date,
            "period_type": period_type,
        }
        extent = bbox or config.get("extent")
        if self.iface is not None and extent is not None:
            transform = QgsCoordinateTransform(
                QgsCoordinateReferenceSystem(self.api_client.CRS),
                self.iface.mapCanvas().mapSettings().destinationCrs(),
                QgsProject.instance(),
            )
            self.iface.mapCanvas().setExtent(
                transform.transformBoundingBox(QgsRectangle(*extent))
            )
            self.iface.mapCanvas().refresh()

        # Statistics tab: the API summary is exact for this search.
        self.alert_count_value.setText(total_text)
        self.total_area_value.setText(
            self.tr("{} ha", self.format_decimal(summary.get("area") or 0))
        )
        self.largest_alert_value.setText("—")
        self.largest_alert_code_value.setText("—")
        self.period_result_value.setText(
            "{} {} {}".format(
                start_date.toString("dd/MM/yyyy"),
                self.tr("até"),
                end_date.toString("dd/MM/yyyy"),
            )
        )
        self.update_result_controls()
        try:
            self.update_chart_configuration_controls()
        except Exception as error:  # the summary must still be shown
            QgsMessageLog.logMessage(
                "Could not refresh the chart controls: {}".format(error),
                "MapBiomas Alerta Oficial",
                Qgis.Warning,
            )

        message = self.tr(
            "{} alerta(s), {} ha — mostrados no mapa sem baixar os "
            "polígonos. Eles serão baixados automaticamente se você "
            "exportar, gerar um gráfico ou abrir os detalhes de um alerta. "
            "Alertas pequenos podem não aparecer em escalas muito "
            "pequenas: aproxime o mapa.",
            total_text,
            self.format_decimal(summary.get("area") or 0),
        )
        if bbox is not None and self.area_layer_radio.isChecked():
            message += " " + self.tr(
                "No mapa rápido, o recorte pela camada é aproximado "
                "(retângulo da camada)."
            )
        self.show_success(message)
        return True

    def pick_quick_view_layer(self, config):
        """First candidate layer the map server really publishes, as
        (name, supports_biome_filter). Raises QuickViewUnavailable."""
        try:
            published = self.api_client.wms_layer_names(config["wms_url"])
        except Exception as error:
            raise QuickViewUnavailable(str(error)) from error
        for name, supports_biome in config.get("wms_layers") or ():
            if name in published:
                return name, supports_biome
        raise QuickViewUnavailable(
            "nenhuma camada de alertas publicada no servidor de mapas"
        )

    def remove_quick_view_layer(self):
        state = self._quick_view_state
        self._quick_view_state = None
        if state and state.get("layer_id"):
            if QgsProject.instance().mapLayer(state["layer_id"]) is not None:
                QgsProject.instance().removeMapLayer(state["layer_id"])

    def ensure_full_layer(self):
        """Actions that need the polygons (export, chart, details) call
        this first: after a quick view, it downloads the full layer for
        the same filters and replaces the map-server layer."""
        layer = self.result_layer()
        if layer is not None and layer.isValid():
            return True
        if self._quick_view_state is None:
            return False
        self.show_progress_message(
            self.tr("Baixando os polígonos dos alertas para esta ação...")
        )
        self.search_alerts(force_full=True)
        layer = self.result_layer()
        return layer is not None and layer.isValid()

    def with_full_layer(self, action):
        def run(*_args):
            if self.ensure_full_layer():
                action()
        return run

    def download_full_alerts(self):
        """Runs the same search again, downloading the full layer."""
        self.quick_view_checkbox.setChecked(False)
        self.download_full_button.setVisible(False)
        self.search_alerts()

    def set_search_busy(self, busy):
        self.search_button.setText(
            self.tr("BAIXANDO...") if busy else self.tr("BUSCAR ALERTAS")
        )
        if not busy:
            self.search_button.setToolTip("")
            if self.iface is not None and self._progress_message_item is not None:
                try:
                    self.iface.messageBar().popWidget(
                        self._progress_message_item
                    )
                except RuntimeError:
                    pass
                self._progress_message_item = None
        self.search_button.setEnabled(
            False
            if busy
            else bool(self.api_client.country.get("enabled"))
        )
        self.clear_filters_button.setEnabled(not busy)
        self.cancel_search_button.setEnabled(busy)
        if not busy and hasattr(self, "search_progress_frame"):
            self.search_progress_frame.setVisible(False)
        self.filter_secondary_action_stack.setCurrentWidget(
            self.cancel_search_button if busy else self.clear_filters_button
        )

    def show_early_summary(
        self, statistics, start_date, end_date, period_type,
        approximate=False, exact=True,
    ):
        """Right after the summary query: official numbers in the
        Statistics tab, plus the download progress (v3)."""
        if not statistics or not (exact or approximate):
            return
        summary = statistics.get("summary") or {}
        if not summary:
            return
        for label in (
            self.largest_alert_value, self.largest_alert_code_value,
            self.largest_alert_location_value, self.top_municipality_value,
            self.lowest_alert_value, self.lowest_alert_code_value,
            self.lowest_alert_location_value, self.deforestation_speed_value,
            self.overlap_counts_value,
        ):
            label.setText("—")
        self.period_type_value.setText(
            self.tr("Data de publicação")
            if period_type == MapBiomasApiClient.PERIOD_PUBLICATION
            else self.tr("Data de detecção")
        )
        self.period_result_value.setText(
            self.tr(
                "{} até {}",
                start_date.toString("dd/MM/yyyy"),
                end_date.toString("dd/MM/yyyy"),
            )
        )
        self._summary_period_days = start_date.daysTo(end_date) + 1
        self.apply_api_summary(statistics)
        self.search_progress_note.setText(
            self.tr(
                "Números da plataforma para o retângulo da camada; ao "
                "terminar, são recalculados com o recorte exato."
            )
            if approximate else self.tr(
                "Os números abaixo já são os oficiais da plataforma para "
                "estes filtros. A camada aparece no mapa ao terminar."
            )
        )
        self.search_progress_frame.setVisible(True)
        self.result_cards_widget.setVisible(True)
        index = self.tabs.indexOf(self.results_tab)
        if index >= 0:
            self.tabs.setTabEnabled(index, True)
            self.tabs.setCurrentIndex(index)
        QgsApplication.processEvents()

    def update_search_progress(self, page, total_pages, stage="download"):
        labels = {
            "summary": "CONSULTANDO RESUMO...",
            "download": "BAIXANDO {}/{}...",
            "process": "PROCESSANDO {}/{}...",
            "finalize": "FINALIZANDO...",
        }
        template = labels.get(stage, labels["download"])
        status_text = (
            self.tr(template, page, total_pages)
            if "{}" in template else self.tr(template)
        )
        self.search_button.setText(status_text)
        # The button is intentionally fixed outside the scrollable area
        # (it needs to stay clickable throughout the whole search), so on
        # a short screen the text — and sometimes almost the whole button
        # — can get clipped by the QGIS window edge (when it's not
        # maximized). The tooltip guarantees the full text on hover; the
        # QGIS message bar (top of the window, outside the panel) mirrors
        # the same text on every update, since it's the only reliable way
        # to follow progress when the button itself is nearly invisible.
        self.search_button.setToolTip(status_text)
        self.show_progress_message(status_text)
        if hasattr(self, "search_progress_bar"):
            if stage == "summary":
                self.search_progress_bar.setRange(0, 0)
            else:
                self.search_progress_bar.setRange(0, max(1, total_pages) * 2)
                done = (page - 1) * 2 + (2 if stage == "process" else 1)
                if stage == "finalize":
                    done = max(1, total_pages) * 2
                self.search_progress_bar.setValue(max(0, done))
            self.search_progress_label.setText(
                self.tr(
                    "Baixando os alertas… página {} de {}", page, total_pages
                )
                if stage in ("download", "process") and total_pages
                else status_text.capitalize()
            )
        QgsApplication.processEvents()

    def show_progress_message(self, text):
        if self.iface is None:
            return
        bar = self.iface.messageBar()
        if self._progress_message_item is not None:
            bar.popWidget(self._progress_message_item)
        self._progress_message_item = bar.createMessage(
            "MapBiomas Alerta Oficial", text
        )
        bar.pushWidget(self._progress_message_item, Qgis.Info)

    @staticmethod
    def format_area_label(value):
        text = re.sub(r"\s+", " ", str(value or "")).strip(" -—_|,;")
        if not text or text == "—" or text.isdigit():
            return ""
        if text.isupper() and len(text) > 3:
            text = text.title()
        return text[:60].rstrip()

    @classmethod
    def area_label_from_layer(cls, layer, include_generic_names=True):
        """Gets a single representative territorial name from the layer."""
        if layer is None or not layer.isValid():
            return ""
        candidate_groups = [
            ("bioma", "biome", "nmbioma", "nomebioma"),
            ("estado", "state", "uf", "nmuf", "nomeestado"),
            ("municipio", "municipality", "cidade", "city", "nomemunicipio"),
            ("territorio", "territory", "categoria", "category"),
        ]
        if include_generic_names:
            candidate_groups.append(("nome", "name", "nm", "label"))
        fields = {
            cls.normalize_source_name(field.name()): field.name()
            for field in layer.fields()
        }
        for candidates in candidate_groups:
            field_name = next(
                (fields.get(candidate) for candidate in candidates
                 if fields.get(candidate)),
                None,
            )
            if not field_name:
                continue
            field_index = layer.fields().indexOf(field_name)
            labels = {}
            for raw_value in layer.uniqueValues(field_index, 3):
                values = MapBiomasApiClient.value_list(raw_value) or [raw_value]
                for value in values:
                    label = cls.format_area_label(value)
                    if label:
                        labels.setdefault(label.casefold(), label)
                    if len(labels) > 1:
                        break
                if len(labels) > 1:
                    break
            if len(labels) == 1:
                return next(iter(labels.values()))
        return ""

    def area_interest_label(self, result_layer=None):
        """Names the clip without confusing its content with the area of interest."""
        if self.area_country_radio.isChecked():
            return self.format_area_label(self.country_combo.currentText())
        if self.area_alert_code_radio.isChecked():
            return ""
        if self.area_car_radio.isChecked():
            return ""
        if self.area_coordinates_radio.isChecked():
            longitude = self.longitude_edit.text().strip()
            latitude = self.latitude_edit.text().strip()
            if longitude and latitude:
                return self.tr("Coordenada {}, {}", longitude, latitude)
            return self.tr("Coordenadas")
        if self.area_biome_radio.isChecked():
            names = self.biome_combo.checked_labels()
            return ", ".join(names) if names else self.tr("Bioma")
        if self.area_layer_radio.isChecked():
            source_layer = self.selected_vector_layer()
            source_label = self.area_label_from_layer(source_layer)
            if source_label:
                return source_label
            result_label = self.area_label_from_layer(
                result_layer, include_generic_names=False
            )
            if result_label:
                return result_label
            if source_layer is not None:
                layer_name = re.sub(r"[_-]+", " ", source_layer.name())
                return self.format_area_label(layer_name)
            return "Área selecionada"
        return ""

    def create_result_layer_name(
        self,
        start_date,
        end_date,
        alert_code,
        period_type,
        area_label=None,
        car_code=None,
    ):
        """Result layer name: "<Alerts> - <area of interest>, <period>",
        e.g. "Alertas - Cerrado, 01/01/2025 a 30/07/2025" in Portuguese."""
        prefix = self.tr("Alertas")
        if alert_code:
            return "{} - {}".format(
                prefix, self.tr("alerta {}", alert_code)
            )
        if car_code:
            return "{} - CAR {}".format(prefix, car_code)
        if start_date is None or end_date is None:
            return "{} - {}".format(
                prefix, area_label or self.tr("Coordenadas")
            )
        period = self.tr(
            "{} a {}",
            start_date.toString("dd/MM/yyyy"),
            end_date.toString("dd/MM/yyyy"),
        )
        if area_label:
            return "{} - {}, {}".format(prefix, area_label, period)
        return "{} - {}".format(prefix, period)

    @staticmethod
    def apply_result_style(
        layer,
        country=None,
    ):
        MapBiomasAlertDockWidget.apply_attribute_aliases(layer, country)
        if layer.geometryType() != 2:
            return

        symbol = QgsFillSymbol.createSimple(
            {
                "color": "131,36,19,90",
                "outline_color": "131,36,19,255",
                "outline_width": "0.6",
            }
        )

        layer.setRenderer(
            QgsSingleSymbolRenderer(
                symbol
            )
        )

        layer.triggerRepaint()

    @staticmethod
    def apply_attribute_aliases(layer, country=None):
        """Sets field aliases so the table distinguishes aggregate
        totals from individual areas. "Estado"/"Municipio" are internal
        field names — the shown alias uses the connected country's own
        term (e.g. "Departamento") when `country` is given."""
        if layer is None:
            return
        aliases = dict(ATTRIBUTE_FIELD_ALIASES)
        if country:
            region_label = str(
                country.get("region_label", "Estado")
            ).lower()
            municipality_label = str(
                country.get("municipality_label", "Município")
            ).lower()
            aliases["Estado"] = (
                "{}(s) cruzado(s), separado(s) por ;".format(
                    region_label.capitalize()
                )
            )
            aliases["EstadoAreas"] = (
                "Área individual por {} (JSON em ha)".format(region_label)
            )
            aliases["Municipio"] = (
                "{}(s) cruzado(s), separado(s) por ;".format(
                    municipality_label.capitalize()
                )
            )
            aliases["MunicAreas"] = (
                "Área individual por {} (JSON em ha)".format(
                    municipality_label
                )
            )
        for field_name, alias in aliases.items():
            field_index = layer.fields().indexOf(field_name)
            if field_index >= 0:
                layer.setFieldAlias(field_index, alias)

    def result_layer(self):
        if not self.current_result_layer_id:
            return None

        return (
            QgsProject.instance()
            .mapLayer(
                self.current_result_layer_id
            )
        )

    def refresh_analysis_layers(self):
        """Sincroniza a lista de consultas preservadas no projeto."""
        project = QgsProject.instance()
        self.result_layer_ids = [
            layer_id for layer_id in self.result_layer_ids
            if project.mapLayer(layer_id) is not None
        ]
        self.result_contexts = {
            layer_id: context
            for layer_id, context in self.result_contexts.items()
            if layer_id in self.result_layer_ids
        }
        if self.current_result_layer_id not in self.result_layer_ids:
            self.current_result_layer_id = (
                self.result_layer_ids[-1] if self.result_layer_ids else None
            )
        self.analysis_layer_combo.blockSignals(True)
        self.analysis_layer_combo.clear()
        selected_index = -1
        for layer_id in self.result_layer_ids:
            layer = project.mapLayer(layer_id)
            self.analysis_layer_combo.addItem(layer.name(), layer_id)
            if layer_id == self.current_result_layer_id:
                selected_index = self.analysis_layer_combo.count() - 1
        if selected_index >= 0:
            self.analysis_layer_combo.setCurrentIndex(selected_index)
        self.analysis_layer_combo.blockSignals(False)
        if hasattr(self, "comparison_layer_combo"):
            previous_comparison = self.comparison_layer_combo.currentData()
            self.comparison_layer_combo.blockSignals(True)
            self.comparison_layer_combo.clear()
            self.comparison_layer_combo.addItem("Não comparar", None)
            for layer_id in self.result_layer_ids:
                if layer_id == self.current_result_layer_id:
                    continue
                layer = project.mapLayer(layer_id)
                if layer is not None:
                    self.comparison_layer_combo.addItem(layer.name(), layer_id)
            comparison_index = self.comparison_layer_combo.findData(
                previous_comparison
            )
            self.comparison_layer_combo.setCurrentIndex(
                comparison_index if comparison_index >= 0 else 0
            )
            self.comparison_layer_combo.setEnabled(
                self.comparison_layer_combo.count() > 1
            )
            self.comparison_layer_combo.blockSignals(False)
        self.update_layer_comparison()
        self.update_layers_inventory()
        self.update_analysis_tab_availability()
        if hasattr(self, "apply_chart_button"):
            self.update_chart_configuration_controls()

    def update_layers_inventory(self):
        project = QgsProject.instance()
        lines = []
        for index, layer_id in enumerate(self.result_layer_ids, 1):
            layer = project.mapLayer(layer_id)
            if layer is None:
                continue
            context = self.result_contexts.get(layer_id, {})
            start_date = context.get("start_date")
            end_date = context.get("end_date")
            period = (
                self.tr(
                    "{} a {}",
                    start_date.toString("dd/MM/yyyy"),
                    end_date.toString("dd/MM/yyyy"),
                )
                if start_date is not None and end_date is not None
                else self.tr("sem período adicional")
            )
            lines.append(
                self.tr(
                    "{}. {} | {} | {} alerta(s)",
                    index,
                    layer.name(),
                    period,
                    self.format_integer(layer.featureCount()),
                )
            )
        count = len(lines)
        self.layers_status_label.setText(
            self.tr("{} camada(s) filtrada(s).", count)
            if count else self.tr("Nenhuma camada filtrada.")
        )
        self.layers_inventory_label.setText(
            "\n".join(lines) if lines
            else self.tr("Nenhuma consulta realizada.")
        )

    def update_layer_comparison(self):
        project = QgsProject.instance()
        layers = [
            project.mapLayer(layer_id) for layer_id in self.result_layer_ids
            if project.mapLayer(layer_id) is not None
        ]
        visible = len(layers) > 0
        # The per-layer table is no longer shown (the summary cards
        # replace it; comparing layers is done in the chart). It is kept
        # hidden because the XLSX statistics export reads it.
        self.layer_comparison_title.setVisible(False)
        self.layer_comparison_table.setVisible(False)
        self.layer_comparison_table.setRowCount(len(layers) if visible else 0)
        if not visible:
            return

        for row, layer in enumerate(layers):
            cached = self.layer_comparison_cache.get(layer.id())
            if cached is None:
                area_field = self.find_existing_field(
                    layer,
                    ["IntAreaHa", "AreaHa", "areaha", "area_ha", "area"],
                )
                code_field = self.find_existing_field(
                    layer, ["CodeAlerta", "alertCode", "codigo"]
                )
                total_area = 0.0
                largest_area = 0.0
                largest_code = "—"
                largest_feature_id = None
                if area_field:
                    for feature in layer.getFeatures():
                        try:
                            area = float(feature[area_field] or 0)
                        except (TypeError, ValueError):
                            continue
                        total_area += area
                        if area > largest_area:
                            largest_area = area
                            largest_code = (
                                str(feature[code_field])
                                if code_field else "—"
                            )
                            largest_feature_id = feature.id()
                municipality = (
                    self.municipality_ranking_text(layer, area_field)
                    if area_field
                    else "—"
                )
                cached = {
                    "feature_count": layer.featureCount(),
                    "total_area": total_area,
                    "largest_area": largest_area,
                    "largest_code": largest_code,
                    "largest_feature_id": largest_feature_id,
                    "area_field": area_field,
                    "municipality": municipality,
                }
                self.layer_comparison_cache[layer.id()] = cached

            context = self.result_contexts.get(layer.id(), {})
            period_type = context.get("period_type")
            start_date = context.get("start_date")
            end_date = context.get("end_date")
            date_type = (
                self.tr("Não aplicado")
                if start_date is None or end_date is None
                else (
                    self.tr("Publicação")
                    if period_type == MapBiomasApiClient.PERIOD_PUBLICATION
                    else self.tr("Detecção")
                )
            )
            period = (
                "{} a {}".format(
                    start_date.toString("dd/MM/yyyy"),
                    end_date.toString("dd/MM/yyyy"),
                )
                if start_date is not None and end_date is not None
                else "—"
            )
            values = [
                layer.name(),
                self.format_integer(cached["feature_count"]),
                "{} ha".format(self.format_decimal(cached["total_area"])),
                "{} ha".format(self.format_decimal(cached["largest_area"])),
                cached["largest_code"],
                cached["municipality"],
                date_type,
                period,
            ]
            for column, value in enumerate(values):
                self.layer_comparison_table.setItem(
                    row, column, QTableWidgetItem(str(value))
                )
        self.layer_comparison_table.resizeColumnsToContents()

    def change_analysis_layer(self, *args):
        layer_id = self.analysis_layer_combo.currentData()
        if not layer_id:
            return
        self.current_result_layer_id = layer_id
        layer = self.result_layer()
        context = self.result_contexts.get(layer_id, {})
        if layer is not None and context:
            self.update_result_summary(
                layer,
                context["start_date"],
                context["end_date"],
                context["period_type"],
            )
        self.clear_alert_details()
        self.update_result_controls()
        if layer is not None and self.iface is not None:
            self.iface.setActiveLayer(layer)
        self.refresh_analysis_layers()
        if layer is not None:
            self.populate_chart_fields(layer)

    def change_comparison_layer(self, *args):
        # Selecting a layer only changes the pending configuration. It must
        # not aggregate features or render while a QComboBox signal is active.
        if hasattr(self, "chart_note_label"):
            self.chart_note_label.setText(
                self.tr("Configuração alterada. Clique em APLICAR ANÁLISE.")
            )
        self.update_chart_configuration_controls()

    def mark_chart_configuration_pending(self, *args):
        if self._chart_processing:
            return
        if self.chart_analysis_available():
            self.chart_status_label.setText(
                self.tr(
                    "<b>Status:</b> Configuração alterada. Clique em "
                    "<b>APLICAR ANÁLISE</b>."
                )
            )
        else:
            self.chart_status_label.setText(
                self.tr(
                    "<b>Status:</b> Selecione uma camada com pelo menos "
                    "dois alertas."
                )
            )

    def chart_analysis_available(self):
        primary = self.result_layer()
        if primary is None or primary.featureCount() <= 0:
            return False
        second_id = self.comparison_layer_combo.currentData()
        second = (
            QgsProject.instance().mapLayer(second_id) if second_id else None
        )
        return (
            primary.featureCount() >= 2
            or (second is not None and second.featureCount() > 0)
        )

    def update_chart_configuration_controls(self, *args):
        """Update widgets without aggregating features or rendering a chart."""
        comparing = bool(self.comparison_layer_combo.currentData())
        group_key = str(
            self.chart_group_combo.currentData() or ""
        ).lower()
        is_source_group = group_key in ("fonte", "sources")
        is_crossing_area_group = group_key == "__crossing_area_type__"

        # Multivalued territorial fields cannot receive the whole alert area.
        # Municipality, state and biome are safe only with the allocation maps
        # returned by the API and only for the alert area field.
        allowed_numeric = None
        if group_key in TERRITORIAL_AREA_GROUPS:
            _category, map_field, valid_numeric = (
                TERRITORIAL_AREA_GROUPS[group_key]
            )
            map_available = all(
                (
                    map_field.lower() in {
                        field.name().lower() for field in candidate.fields()
                    }
                    or not valid_numeric.isdisjoint({
                        field.name().lower() for field in candidate.fields()
                    })
                )
                for candidate in self.chart_layers()
            )
            allowed_numeric = (
                valid_numeric if map_available else set()
            )

        compatible_rows = []
        value_model = self.chart_value_combo.model()
        for row in range(self.chart_value_combo.count()):
            field_key = str(
                self.chart_value_combo.itemData(row) or ""
            ).lower()
            compatible = (
                allowed_numeric is None or field_key in allowed_numeric
            )
            self.chart_value_combo.view().setRowHidden(row, not compatible)
            item = value_model.item(row)
            if item is not None:
                item.setEnabled(compatible)
            if compatible:
                compatible_rows.append(row)

        current_value_row = self.chart_value_combo.currentIndex()
        if current_value_row not in compatible_rows:
            self.chart_value_combo.blockSignals(True)
            self.chart_value_combo.setCurrentIndex(
                compatible_rows[0] if compatible_rows else -1
            )
            self.chart_value_combo.blockSignals(False)

        has_numeric = bool(compatible_rows)
        metric_model = self.chart_metric_combo.model()
        for row in range(self.chart_metric_combo.count()):
            metric = self.chart_metric_combo.itemData(row)
            compatible = (
                metric == "sum"
                if is_crossing_area_group
                else metric == "count" or has_numeric
            )
            self.chart_metric_combo.view().setRowHidden(row, not compatible)
            item = metric_model.item(row)
            if item is not None:
                item.setEnabled(compatible)
        if is_crossing_area_group:
            self.chart_metric_combo.blockSignals(True)
            self.chart_metric_combo.setCurrentIndex(
                self.chart_metric_combo.findData("sum")
            )
            self.chart_metric_combo.blockSignals(False)
        elif not has_numeric and self.chart_metric_combo.currentData() != "count":
            self.chart_metric_combo.blockSignals(True)
            self.chart_metric_combo.setCurrentIndex(
                self.chart_metric_combo.findData("count")
            )
            self.chart_metric_combo.blockSignals(False)

        type_model = self.chart_type_combo.model()
        for row in range(self.chart_type_combo.count()):
            chart_type = self.chart_type_combo.itemData(row)
            compatible = not comparing or chart_type == "bar"
            self.chart_type_combo.view().setRowHidden(row, not compatible)
            item = type_model.item(row)
            if item is not None:
                item.setEnabled(compatible)
        if comparing and self.chart_type_combo.currentData() != "bar":
            self.chart_type_combo.blockSignals(True)
            self.chart_type_combo.setCurrentIndex(
                self.chart_type_combo.findData("bar")
            )
            self.chart_type_combo.blockSignals(False)

        calculation = self.chart_metric_combo.currentData()
        self.chart_value_combo.setEnabled(
            calculation != "count" and has_numeric and not is_crossing_area_group
        )
        # Source splitting is meaningful only for a single result layer.
        self.chart_source_mode_combo.setEnabled(
            not comparing and is_source_group
        )
        self.apply_chart_button.setEnabled(
            (
                self.chart_analysis_available()
                or bool(getattr(self, "_quick_view_state", None))
            )
            and not self._chart_processing
        )
        self.mark_chart_configuration_pending()

    def apply_chart_analysis(self, *args):
        """Validate the two layers and render the chart once."""
        layer = self.result_layer()
        if layer is None or not self.chart_analysis_available():
            self.chart_status_label.setText(
                self.tr(
                    "<b>Status:</b> A análise exige pelo menos dois "
                    "alertas."
                )
            )
            self.show_warning(
                self.tr(
                    "Selecione uma camada com pelo menos dois alertas."
                )
            )
            return

        started_at = datetime.now()
        self._chart_processing = True
        self.apply_chart_button.setEnabled(False)
        self.apply_chart_button.setText(self.tr("PROCESSANDO ANÁLISE..."))
        self.chart_status_label.setText(
            self.tr("<b>Status:</b> Processando os registros das camadas...")
        )
        QgsApplication.processEvents()
        try:
            # The field lists are rebuilt from the actual intersection of the
            # selected layers only when the user confirms the analysis.
            self.populate_chart_fields(layer)
            if self.chart_group_combo.count() <= 0:
                self.chart_widget.set_items([])
                self.chart_status_label.setText(
                    self.tr(
                        "<b>Status:</b> Concluída sem campos analíticos "
                        "comuns."
                    )
                )
                self.show_warning(
                    self.tr(
                        "As camadas não possuem campos analíticos comuns."
                    )
                )
                return
            calculation = self.chart_metric_combo.currentData()
            if calculation != "count" and self.chart_value_combo.count() <= 0:
                self.chart_metric_combo.setCurrentIndex(
                    self.chart_metric_combo.findData("count")
                )
            self.update_chart_configuration_controls()
            self.refresh_chart_categories()
            self.update_chart()
            categories = len({
                item[0] for item in self.chart_widget._items
            })
            elapsed = (datetime.now() - started_at).total_seconds()
            if categories:
                status = self.tr(
                    "<b>Status:</b> Análise concluída — {} camada(s), "
                    "{} categoria(s), {:.1f} segundo(s).",
                    len(self.chart_layers()), categories, elapsed,
                )
            else:
                status = self.tr(
                    "<b>Status:</b> Análise concluída, mas a configuração "
                    "selecionada não produziu dados para o gráfico."
                )
            self.chart_status_label.setText(status)
            if categories:
                self.tabs.setCurrentWidget(self.charts_tab)
        except Exception as error:
            self.chart_widget.set_items([])
            self.chart_status_label.setText(
                self.tr("<b>Status:</b> Falha ao executar a análise.")
            )
            self.show_warning(
                self.tr("Não foi possível aplicar a análise: {}", error)
            )
        finally:
            self._chart_processing = False
            self.apply_chart_button.setEnabled(
                self.chart_analysis_available()
            )
            self.apply_chart_button.setText(self.tr("APLICAR ANÁLISE"))

    def chart_layers(self):
        project = QgsProject.instance()
        layers = []
        primary = self.result_layer()
        if primary is not None:
            layers.append(primary)
        if hasattr(self, "comparison_layer_combo"):
            second_id = self.comparison_layer_combo.currentData()
            second = project.mapLayer(second_id) if second_id else None
            if second is not None and all(second.id() != item.id() for item in layers):
                layers.append(second)
        return layers[:2]

    def chart_layer_label(self, layer):
        context = self.result_contexts.get(layer.id(), {})
        start = context.get("start_date")
        end = context.get("end_date")
        if start is not None and end is not None:
            return "{} a {}".format(
                start.toString("dd/MM/yyyy"), end.toString("dd/MM/yyyy")
            )
        return layer.name()

    def result_query_mode(self, layer):
        """Return the spatial/search mode that produced a result layer."""
        if layer is None:
            return "standard"
        context = self.result_contexts.get(layer.id(), {})
        mode = str(context.get("query_mode") or "").strip().lower()
        if mode:
            return mode
        # Compatibility with result layers created before query_mode existed.
        name = str(layer.name() or "").upper()
        if " — CAR " in name or " - CAR " in name:
            return "car"
        if "ALERTA " in name and any(char.isdigit() for char in name):
            return "alert_code"
        return "standard"

    def chart_field_matrix(self, layers):
        """Fields that produce meaningful analyses for the selected searches."""
        modes = {self.result_query_mode(layer) for layer in layers}
        if "alert_code" in modes:
            return set(), set()
        if modes.intersection({"car", "coordinates"}):
            # A CAR or point already fixes the territory. Municipality, state,
            # biome and territorial crossings would repeat the same context.
            return (
                {"fonte", "sources", "ano", "mes", "anomes"},
                {"areaha", "intareaha", "intpct"},
            )
        return (
            {
                "fonte", "sources", "bioma", "biome", "estado", "state",
                "municipio", "municipality", "ano", "mes", "anomes",
                "unidconserv", "terraindig", "assentamento", "quilombo",
                "reservabio", "manflorest", "protintegral", "usosustent",
                "app", "reservalegal", "terrespecial", "geoparque",
                "protmunintegral", "usomunsust", "protestintegral",
                "usoestsust",
            },
            {
                "areaha", "intareaha", "intpct", "ucareaha",
                "tiareaHa".lower(),
                "assentarea", "quilombarea", "resbioarea", "manflorarea",
                "protintarea", "usosustarea", "appareaha", "appqtd",
                "rlareaha", "rlqtd", "terresparea", "imovelqtd",
                "geoparquearea", "protmunintarea", "usomunsustarea",
                "protestintarea", "usoestsustarea",
            },
        )

    @staticmethod
    def crossing_area_chart_fields():
        return (
            ("UCAreaHa", "Unidades de Conservação (todas)"),
            ("TIAreaHa", "Terras Indígenas"),
            ("AssentArea", "Assentamentos"),
            ("QuilombArea", "Territórios quilombolas"),
            ("ResBioArea", "Reservas da Biosfera"),
            ("ManFlorArea", "Manejo florestal"),
            ("ProtIntArea", "Proteção integral"),
            ("UsoSustArea", "Uso sustentável"),
            ("APPAreaHa", "APP"),
            ("RLAreaHa", "Reserva Legal"),
            ("TerrEspArea", "Territórios especiais"),
            ("GeoparqueArea", "Geoparques"),
            ("ProtMunIntArea", "Proteção integral municipal"),
            ("UsoMunSustArea", "Uso sustentável municipal"),
            ("ProtEstIntArea", "Proteção integral estadual"),
            ("UsoEstSustArea", "Uso sustentável estadual"),
        )

    @staticmethod
    def normalized_chart_category(value):
        text = " ".join(str(value or "").split()).casefold()
        return unicodedata.normalize("NFKD", text).encode(
            "ascii", "ignore"
        ).decode("ascii")

    def municipality_ranking_text(self, layer, area_field_name):
        # The municipality split (MunicAreas/MunicAreaHa) is computed by the
        # API over the alert's TOTAL area — never over "IntAreaHa" (the area
        # clipped by the area-of-interest layer, when one is used). Passing
        # "IntAreaHa" here would make the safety check in
        # territorial_area_totals reject it for field mismatch, showing
        # "unavailable" even though the API provided the split — the issue
        # isn't missing data, it's querying with the wrong area field. That's
        # why this specific ranking always uses the alert's total area field,
        # regardless of which field the rest of the panel is displaying.
        territorial_value_field = (
            self.find_existing_field(layer, ["AreaHa", "area_ha", "area"])
            or area_field_name
        )
        api_totals = self.api_statistics_totals(
            layer,
            "Municipio",
            "sum",
            territorial_value_field,
            None,
        )
        if api_totals:
            municipality, area = max(
                api_totals.items(), key=lambda item: item[1]
            )
            return "{} — {} ha".format(
                municipality,
                self.format_decimal(area),
            )
        result = self.territorial_area_totals(
            layer,
            "Municipio",
            territorial_value_field,
        )
        if not isinstance(result, tuple):
            return self.tr(
                "Indisponível: a API não detalhou a área por {}",
                self.tr(self.api_client.country.get(
                    "municipality_label", "Município"
                )).lower(),
            )
        totals, _counts = result
        if not totals:
            return "—"
        municipality, area = max(totals.items(), key=lambda item: item[1])
        return "{} — {} ha".format(
            municipality,
            self.format_decimal(area),
        )

    def update_result_summary(
        self,
        layer,
        start_date,
        end_date,
        period_type,
    ):
        count = layer.featureCount()
        total_area = 0.0
        largest_area = 0.0
        largest_feature = None

        area_field_name = (
            self.find_existing_field(
                layer,
                [
                    "IntAreaHa",
                    "AreaHa",
                    "areaha",
                    "area_ha",
                    "area",
                ],
            )
        )

        if area_field_name:
            municipality_field = self.find_existing_field(
                layer, ["Municipio", "municipality"]
            )
            # The layer comparison table (update_layer_comparison, called by
            # refresh_analysis_layers right before this method in the normal
            # flow) already scanned this same layer to compute the exact same
            # numbers. Reuse that result instead of scanning the whole layer
            # again — just look up the largest-alert feature (O(1), not O(n)).
            cached = self.layer_comparison_cache.get(layer.id())
            if cached is not None and cached.get("area_field") == area_field_name:
                total_area = cached["total_area"]
                largest_area = cached["largest_area"]
                if cached.get("largest_feature_id") is not None:
                    fetched = layer.getFeature(cached["largest_feature_id"])
                    if fetched.isValid():
                        largest_feature = fetched
            else:
                for feature in layer.getFeatures():
                    value = feature[
                        area_field_name
                    ]

                    try:
                        area = float(value or 0)
                        total_area += area
                        if largest_feature is None or area > largest_area:
                            largest_area = area
                            largest_feature = feature
                    except (
                        TypeError,
                        ValueError,
                    ):
                        pass

        self.alert_count_value.setText(
            self.format_integer(
                count
            )
        )

        # These fields only exist in the API's official statistics summary
        # (alertsSummary query); there is no way to derive them from the
        # downloaded layer. They keep the "unavailable" text until they are
        # filled in further below, when the query is "server-exact".
        no_api_summary_text = self.tr(
            "Disponível apenas quando a consulta é equivalente à da "
            "plataforma (sem recorte manual do mapa, todas as fontes e "
            "sem filtro de cruzamento)."
        )
        self._speed_values = {}
        self.lowest_alert_value.setText("—")
        self.lowest_alert_code_value.setText("—")
        self.lowest_alert_location_value.setText("—")
        self.deforestation_speed_value.setText(no_api_summary_text)
        self.overlap_counts_value.setText(no_api_summary_text)

        if area_field_name:
            self.largest_alert_value.setText(
                "{} ha".format(self.format_decimal(largest_area))
            )
            if largest_feature is not None:
                code_field = self.find_existing_field(
                    layer, ["CodeAlerta", "alertCode", "codigo"]
                )
                state_field = self.find_existing_field(
                    layer, ["Estado", "state"]
                )
                biome_field = self.find_existing_field(
                    layer, ["Bioma", "biome"]
                )
                self.largest_alert_code_value.setText(
                    str(largest_feature[code_field] or "—")
                    if code_field
                    else "—"
                )
                location_parts = []
                for field_name in (
                    municipality_field,
                    state_field,
                    biome_field,
                ):
                    if field_name:
                        field_value = str(
                            largest_feature[field_name] or ""
                        ).strip()
                        if field_value and field_value not in location_parts:
                            location_parts.append(field_value)
                self.largest_alert_location_value.setText(
                    " — ".join(location_parts)
                    if location_parts
                    else "—"
                )
            else:
                self.largest_alert_code_value.setText("—")
                self.largest_alert_location_value.setText("—")
            self.top_municipality_value.setText(
                self.municipality_ranking_text(layer, area_field_name)
            )
        else:
            self.largest_alert_value.setText("—")
            self.largest_alert_code_value.setText("—")
            self.largest_alert_location_value.setText("—")
            self.top_municipality_value.setText("—")

        if area_field_name:
            self.total_area_value.setText(
                "{} ha".format(
                    self.format_decimal(
                        total_area
                    )
                )
            )
        else:
            self.total_area_value.setText(
                self.tr("Campo de área não encontrado")
            )

        if start_date is None or end_date is None:
            period_type_text = self.tr("Não aplicado")
        elif (
            period_type
            == MapBiomasApiClient
            .PERIOD_PUBLICATION
        ):
            period_type_text = self.tr(
                "Data de publicação"
            )
        else:
            period_type_text = self.tr(
                "Data de detecção"
            )

        self.period_type_value.setText(
            period_type_text
        )

        self.period_result_value.setText(
            self.tr("Não aplicado")
            if start_date is None or end_date is None
            else self.tr(
                "{} até {}",
                start_date.toString("dd/MM/yyyy"),
                end_date.toString("dd/MM/yyyy"),
            )
        )

        context = self.result_contexts.get(layer.id(), {})
        if context.get("api_statistics_exact"):
            self._summary_period_days = (
                start_date.daysTo(end_date) + 1
                if start_date is not None and end_date is not None else None
            )
            self.apply_api_summary(context.get("api_statistics") or {})

        self.populate_chart_fields(layer)
        if hasattr(self, "chart_note_label"):
            self.chart_note_label.setText(
                self.tr("Escolha as opções e clique em APLICAR ANÁLISE.")
            )

        if count > 0:
            self.result_status_label.setText(
                self.tr("Consulta concluída com sucesso.")
            )

        else:
            self.result_status_label.setText(
                self.tr(
                    "A consulta foi concluída, mas nenhum alerta foi "
                    "encontrado."
                )
            )


    def apply_api_summary(self, statistics):
        """Writes the platform's official summary (GetAlertsSummary) into
        the summary labels/cards. Used right after the summary query, while
        the polygons still download, and again when the layer is ready."""
        summary = (statistics or {}).get("summary") or {}
        if not summary:
            return
        self.alert_count_value.setText(
            self.format_integer(summary.get("total") or 0)
        )
        self.total_area_value.setText(
            "{} ha".format(self.format_decimal(summary.get("area") or 0))
        )
        self.largest_alert_value.setText(
            "{} ha".format(
                self.format_decimal(summary.get("biggestAlertArea") or 0)
            )
        )
        biggest = summary.get("biggestAlert") or {}
        self.largest_alert_code_value.setText(
            str(biggest.get("alertCode") or "—")
        )
        location = []
        for value in (
            MapBiomasApiClient.join_values(biggest.get("crossedCities")),
            MapBiomasApiClient.join_values(biggest.get("crossedStates")),
        ):
            if value and value not in location:
                location.append(value)
        self.largest_alert_location_value.setText(
            " — ".join(location) if location else "—"
        )
        cities = statistics.get("rankingByCity") or []
        if cities:
            top = max(
                cities,
                key=lambda item: float(item.get("areaTotal") or 0),
            )
            self.top_municipality_value.setText(
                "{} — {} ha".format(
                    top.get("city") or "—",
                    self.format_decimal(top.get("areaTotal") or 0),
                )
            )

        # Smallest alert (same card shown on the platform).
        self.lowest_alert_value.setText(
            "{} ha".format(
                self.format_decimal(summary.get("lowestAlertArea") or 0)
            )
        )
        lowest = summary.get("lowestAlert") or {}
        self.lowest_alert_code_value.setText(
            str(lowest.get("alertCode") or "—")
        )
        lowest_location = []
        for value in (
            MapBiomasApiClient.join_values(lowest.get("crossedCities")),
            MapBiomasApiClient.join_values(lowest.get("crossedStates")),
        ):
            if value and value not in lowest_location:
                lowest_location.append(value)
        self.lowest_alert_location_value.setText(
            " — ".join(lowest_location) if lowest_location else "—"
        )

        # Deforestation speed (query average and the alert with the
        # highest individually observed speed).
        average_speed = summary.get("averageDeforestationSpeed")
        biggest_speed = summary.get("biggestDeforestationSpeed")
        speed_lines = []
        if average_speed is not None:
            speed_lines.append(
                self.tr(
                    "Média da consulta: {} ha/dia",
                    self.format_decimal(average_speed),
                )
            )
        if biggest_speed is not None:
            speed_alert = summary.get(
                "biggestDeforestationSpeedAlert"
            ) or {}
            speed_location = []
            for value in (
                MapBiomasApiClient.join_values(
                    speed_alert.get("crossedCities")
                ),
                MapBiomasApiClient.join_values(
                    speed_alert.get("crossedStates")
                ),
            ):
                if value and value not in speed_location:
                    speed_location.append(value)
            speed_code = speed_alert.get("alertCode")
            speed_detail = self.tr(
                "Maior velocidade: {} ha/dia",
                self.format_decimal(biggest_speed),
            )
            extra = []
            if speed_code:
                extra.append(self.tr("alerta {}", speed_code))
            if speed_location:
                extra.append(" — ".join(speed_location))
            if extra:
                speed_detail += " ({})".format(", ".join(extra))
            speed_lines.append(speed_detail)
        self.deforestation_speed_value.setText(
            "\n".join(speed_lines) if speed_lines else "—"
        )

        # Overlap counts with protected and institutional areas
        # (same totals shown on the platform).
        overlap_fields = (
            ("conservationUnitsCount", "Unidades de Conservação"),
            ("indigenousLandCount", "Terras Indígenas"),
            ("settlementsCount", "Assentamentos"),
            ("legalReservesCount", "Reservas Legais"),
            (
                "permanentProtectedAreasCount",
                "Áreas de Preservação Permanente",
            ),
            ("forestManagementsCount", "Manejo Florestal"),
            ("riverSourcesCount", "Nascentes de Rios"),
            ("ruralPropertiesCount", "Imóveis Rurais (CAR)"),
            # actionsCount (inspection actions) is not shown: like
            # embargoes and authorizations, it's checked in the report.
        )
        overlap_lines = []
        for field_name, label in overlap_fields:
            field_value = summary.get(field_name)
            if field_value is not None:
                overlap_lines.append(
                    "{}: {}".format(
                        self.tr(label),
                        self.format_integer(field_value),
                    )
                )
        self.overlap_counts_value.setText(
            "\n".join(overlap_lines) if overlap_lines else "—"
        )

        average_speed = summary.get("averageDeforestationSpeed")
        biggest_speed = summary.get("biggestDeforestationSpeed")
        speed_alert = summary.get("biggestDeforestationSpeedAlert") or {}
        speed_location = [
            value for value in (
                MapBiomasApiClient.join_values(speed_alert.get("crossedCities")),
                MapBiomasApiClient.join_values(speed_alert.get("crossedStates")),
            ) if value
        ]
        days = getattr(self, "_summary_period_days", None)
        area = summary.get("area")
        if days and area is not None:
            # Same definition as the platform's "Média diária": deforested
            # area divided by the days of the searched period.
            average_speed = float(area) / days
        self._speed_values = {
            "average": (
                self.format_decimal(average_speed)
                if average_speed is not None else "—"
            ),
            "biggest": (
                self.tr("{} ha/dia", self.format_decimal(biggest_speed))
                if biggest_speed is not None else "—"
            ),
            "biggest_location": " — ".join(dict.fromkeys(speed_location)),
        }
        self.sync_result_cards()

    @staticmethod
    def find_existing_field(
        layer,
        candidates,
    ):
        available_fields = {
            field.name().lower():
            field.name()
            for field in layer.fields()
        }

        for candidate in candidates:
            field_name = (
                available_fields.get(
                    candidate.lower()
                )
            )

            if field_name:
                return field_name

        return None

    def populate_chart_fields(self, layer):
        """Shows only analytic fields common to the selected layers."""
        field_labels = {
            "AreaHa": "Área do alerta (ha)",
            "IntAreaHa": "Área na camada de interesse (ha)",
            "IntPct": "Percentual na camada de interesse (%)",
            "UnidConserv": "Unidade de Conservação",
            "UCAreaHa": "Área em Unidade de Conservação (ha)",
            "TerraIndig": "Terra Indígena",
            "TIAreaHa": "Área em Terra Indígena (ha)",
            "Assentamento": "Assentamento",
            "AssentArea": "Área em assentamento (ha)",
            "Quilombo": "Território quilombola",
            "QuilombArea": "Área quilombola (ha)",
            "ReservaBio": "Reserva da Biosfera",
            "ResBioArea": "Área em Reserva da Biosfera (ha)",
            "ManFlorest": "Manejo florestal",
            "ManFlorArea": "Área de manejo (ha)",
            "ProtIntegral": "Proteção integral federal",
            "ProtIntArea": "Área de proteção integral (ha)",
            "UsoSustent": "Uso sustentável federal",
            "UsoSustArea": "Área de uso sustentável (ha)",
            "APPAreaHa": "Área de APP (ha)",
            "APP": "Área de Preservação Permanente",
            "APPQtd": "Quantidade de APPs",
            "RLAreaHa": "Área de Reserva Legal (ha)",
            "ReservaLegal": "Reserva Legal",
            "RLQtd": "Quantidade de Reservas Legais",
            "TerrEspecial": "Território especial",
            "TerrEspArea": "Área em território especial (ha)",
            "Geoparque": "Geoparque",
            "GeoparqueArea": "Área em geoparque (ha)",
            "ProtMunIntegral": "Proteção integral municipal",
            "ProtMunIntArea": "Área de proteção integral municipal (ha)",
            "UsoMunSust": "Uso sustentável municipal",
            "UsoMunSustArea": "Área de uso sustentável municipal (ha)",
            "ProtEstIntegral": "Proteção integral estadual",
            "ProtEstIntArea": "Área de proteção integral estadual (ha)",
            "UsoEstSust": "Uso sustentável estadual",
            "UsoEstSustArea": "Área de uso sustentável estadual (ha)",
            "ImovelQtd": "Quantidade de imóveis rurais",
            "Fonte": "Fonte",
            "Bioma": "Bioma",
            "Ano": "Ano",
            "Mes": "Mês",
            "AnoMes": "Ano e mês",
        }
        # "Estado"/"Municipio" are the internal field names (they don't
        # change per country), but the text shown in the chart menu must
        # reflect the term used by the connected country (e.g. "Departamento"
        # in Colombia/Bolivia/Peru instead of "Estado").
        field_labels["Estado"] = self.tr(self.api_client.country.get(
            "region_label", "Estado"
        ))
        field_labels["Municipio"] = self.tr(self.api_client.country.get(
            "municipality_label", "Município"
        ))
        previous_group = self.chart_group_combo.currentData()
        previous_value = self.chart_value_combo.currentData()
        self.chart_group_combo.blockSignals(True)
        self.chart_value_combo.blockSignals(True)
        self.chart_group_combo.clear()
        self.chart_value_combo.clear()

        layers = self.chart_layers() or [layer]
        group_fields, numeric_fields = self.chart_field_matrix(layers)
        comparing = len(layers) > 1
        common = None
        for candidate_layer in layers:
            names = {field.name().lower() for field in candidate_layer.fields()}
            common = names if common is None else common.intersection(names)
        common = common or set()

        for field in layer.fields():
            key = field.name().lower()
            if key not in common:
                continue
            label = field_labels.get(field.name(), field.name())
            if key in group_fields and not (
                comparing and key in ("fonte", "sources")
            ) and all(
                self.layer_field_has_values(
                    candidate_layer, field.name(), numeric=False
                )
                for candidate_layer in layers
            ):
                self.chart_group_combo.addItem(self.tr(label), field.name())
            if (
                field.isNumeric()
                and key in numeric_fields
                and all(
                    self.layer_field_has_values(
                        candidate_layer, field.name(), numeric=True
                    )
                    for candidate_layer in layers
                )
            ):
                self.chart_value_combo.addItem(self.tr(label), field.name())

        crossing_area_available = any(
            all(
                self.layer_field_has_values(candidate_layer, field_name, numeric=True)
                for candidate_layer in layers
            )
            for field_name, _label in self.crossing_area_chart_fields()
        ) or all(
            self.layer_field_has_values(
                candidate_layer, "CruzamentosJson", numeric=False
            )
            for candidate_layer in layers
        )
        if crossing_area_available:
            self.chart_group_combo.addItem(
                self.tr("Áreas por tipo de cruzamento"),
                "__crossing_area_type__",
            )

        group_index = self.chart_group_combo.findData(previous_group)
        if group_index < 0:
            preferred = self.find_existing_field(
                layer, ["Municipio", "Estado", "Bioma", "Fonte"]
            )
            group_index = self.chart_group_combo.findData(preferred)
        self.chart_group_combo.setCurrentIndex(max(0, group_index))

        value_index = self.chart_value_combo.findData(previous_value)
        if value_index < 0:
            area_field = self.find_existing_field(
                layer, ["IntAreaHa", "AreaHa", "area_ha", "area"]
            )
            value_index = self.chart_value_combo.findData(area_field)
        self.chart_value_combo.setCurrentIndex(max(0, value_index))
        self.chart_group_combo.blockSignals(False)
        self.chart_value_combo.blockSignals(False)
        has_numeric = self.chart_value_combo.count() > 0
        model = self.chart_metric_combo.model()
        for row in range(self.chart_metric_combo.count()):
            metric = self.chart_metric_combo.itemData(row)
            model.item(row).setEnabled(metric == "count" or has_numeric)
        if not has_numeric and self.chart_metric_combo.currentData() != "count":
            self.chart_metric_combo.setCurrentIndex(
                self.chart_metric_combo.findData("count")
            )
        self.update_chart_configuration_controls()
        self.refresh_chart_categories()
        modes = {self.result_query_mode(item) for item in layers}
        if hasattr(self, "chart_note_label"):
            if "car" in modes:
                self.chart_note_label.setText(
                    self.tr(
                        "Consulta por CAR: somente tempo, fontes e "
                        "métricas de área com dados válidos podem ser "
                        "analisados."
                    )
                )
            elif "coordinates" in modes:
                self.chart_note_label.setText(
                    self.tr(
                        "Consulta por coordenada: somente tempo, fontes "
                        "e métricas de área com dados válidos podem ser "
                        "analisados."
                    )
                )

    def layer_field_has_values(self, layer, field_name, numeric=False):
        """Check whether a field contains at least one analyzable value."""
        candidate_field = self.find_existing_field(layer, [field_name])
        if candidate_field is None:
            return False
        for feature in layer.getFeatures():
            value = feature[candidate_field]
            if value in (None, ""):
                continue
            if numeric:
                try:
                    float(value)
                    return True
                except (TypeError, ValueError):
                    continue
            text = str(value).strip()
            if text and text.casefold() not in (
                "não informado", "nao informado", "null", "[]", "{}"
            ):
                return True
        return False

    def feature_group_labels(self, layer, feature, group_field):
        field_key = str(group_field or "").lower()
        source_fields = ("fonte", "sources")
        geographic_fields = (
            "estado", "municipio", "bioma", "states", "cities", "biomes",
        )
        crossing_fields = (
            "unidconserv", "terraindig", "assentamento", "quilombo",
            "reservabio", "autorizacao", "manflorest", "protintegral",
            "usosustent", "terrespecial", "app", "reservalegal",
            "geoparque", "protmunintegral", "usomunsust",
            "protestintegral", "usoestsust",
        )
        split_fields = geographic_fields + crossing_fields

        if field_key in source_fields:
            source_field = self.find_existing_field(
                layer, ["Fonte", "sources"]
            )
            raw_value = feature[source_field] if source_field else ""
            values = MapBiomasApiClient.value_list(raw_value)
            if self.chart_source_mode_combo.currentData() == "combination":
                return [
                    " + ".join(sorted(values, key=str.casefold))
                    if values
                    else "Não informado"
                ]
            return values or ["Não informado"]

        raw_value = feature[group_field]
        if field_key in crossing_fields:
            values = MapBiomasApiClient.value_list(raw_value)
            # "Sem cruzamento" (not "Não informado"): an empty field here
            # means the alert doesn't cross that territorial category, not
            # that data that should exist is missing.
            return values or [self.tr("Sem cruzamento")]
        if field_key in split_fields:
            values = MapBiomasApiClient.value_list(raw_value)
            return values or ["Não informado"]
        return [
            self.csv_safe_value(raw_value)
            if raw_value not in (None, "")
            else "Não informado"
        ]

    def refresh_chart_categories(self, *args):
        layer = self.result_layer()
        group_field = self.chart_group_combo.currentData()
        previous = self.chart_category_combo.currentData()
        self.chart_category_combo.blockSignals(True)
        self.chart_category_combo.clear()
        self.chart_category_combo.addItem("Todos os valores", None)

        if layer is not None and group_field:
            values = set()
            definition = TERRITORIAL_AREA_GROUPS.get(
                str(group_field).lower()
            )
            value_field = str(self.chart_value_combo.currentData() or "").lower()
            use_area_rows = bool(
                definition
                and self.chart_metric_combo.currentData() != "count"
                and value_field in definition[2]
            )
            for candidate_layer in self.chart_layers():
                if use_area_rows:
                    category = definition[0]
                    self.normalize_territory_area_rows(
                        candidate_layer, categories=[category]
                    )
                    values.update(
                        territory
                        for _code, row_category, territory, _area in
                        self.territory_rows_by_layer.get(
                            candidate_layer.id(), []
                        )
                        if row_category.casefold() == category.casefold()
                    )
                    continue
                candidate_group_field = self.find_existing_field(
                    candidate_layer, [group_field]
                )
                if candidate_group_field is None:
                    continue
                for feature in candidate_layer.getFeatures():
                    values.update(
                        self.feature_group_labels(
                            candidate_layer, feature, candidate_group_field
                        )
                    )
            for value in sorted(values, key=str.casefold):
                self.chart_category_combo.addItem(value, value)

        index = self.chart_category_combo.findData(previous)
        self.chart_category_combo.setCurrentIndex(index if index >= 0 else 0)
        self.chart_category_combo.blockSignals(False)

    @staticmethod
    def decoded_area_map(value):
        if not value:
            return {}
        try:
            document = json.loads(str(value))
        except (TypeError, ValueError):
            return {}
        if not isinstance(document, dict):
            return {}
        result = {}
        for label, area in document.items():
            try:
                result[str(label)] = float(area)
            except (TypeError, ValueError):
                continue
        return result

    def normalize_territory_area_rows(self, source_layer, categories=None):
        """Compute normalized territory areas on demand and cache them.

        When `categories` is given, only those are processed — decoding
        JSON for all ~18 territorial categories on every large query is
        costly, and most only matter if the user looks at that specific
        one (a chart, a crossings export). `categories=None` computes
        all of them, for exports that need everything anyway. Categories
        already computed for the same layer are never reprocessed.
        """
        code_field = self.find_existing_field(
            source_layer, ["CodeAlerta", "alertCode", "codigo"]
        )
        if code_field is None:
            return []

        done = self.territory_categories_done.setdefault(
            source_layer.id(), set()
        )
        requested = (
            None if categories is None
            else {str(category).casefold() for category in categories}
        )
        if requested is not None and requested.issubset(done):
            return self.territory_rows_by_layer.get(source_layer.id(), [])
        pending = (
            None if requested is None else (requested - done)
        )

        map_fields = [
            field.name() for field in source_layer.fields()
            if field.name().lower().endswith("areas")
            and field.name().casefold() != "selterrareas"
        ]
        categories_by_map_field = {
            definition[1].casefold(): definition[0]
            for definition in TERRITORIAL_AREA_GROUPS.values()
        }
        if pending is not None:
            map_fields = [
                field_name for field_name in map_fields
                if categories_by_map_field.get(
                    field_name.casefold(),
                    (field_name[:-5] or field_name).casefold(),
                ) in pending
            ]
        pair_items = list(MapBiomasApiClient.TERRITORY_AREA_PAIRS.items())
        if pending is not None:
            pair_items = [
                (category, fields) for category, fields in pair_items
                if category.casefold() in pending
            ]
        # `find_existing_field` rebuilds a dict of all layer fields on every
        # call. Field names don't change per feature, so resolving them once
        # here — instead of for each feature x each pending category — avoids
        # a cost that scaled with the number of alerts and was one of the
        # main reasons the query used to hang for several minutes at the
        # "FINALIZANDO" step on large layers.
        resolved_category_fields = {}
        for category, (total_field, _area_field) in pair_items:
            total_name = self.find_existing_field(
                source_layer, [total_field]
            )
            if total_name is None:
                continue
            label_name = self.find_existing_field(
                source_layer, [category]
            )
            resolved_category_fields[category] = (total_name, label_name)
        if not map_fields and not resolved_category_fields:
            # None of the pending categories exist in this layer; there's
            # nothing to do, but mark it done so it isn't retried on every
            # call.
            if pending is not None:
                done.update(pending)
            return self.territory_rows_by_layer.get(source_layer.id(), [])
        # Rows that already exist were measured by geometry over the area of
        # interest layer. They take precedence over aggregate totals returned
        # by the API for the same category.
        rows = list(self.territory_rows_by_layer.get(source_layer.id(), []))
        exact_categories = {row[1].casefold() for row in rows}
        processed = 0
        for feature in source_layer.getFeatures():
            processed += 1
            if processed % 500 == 0:
                QgsApplication.processEvents()
            code = str(feature[code_field] or "")
            normalized_categories = set()
            for field_name in map_fields:
                area_map = self.decoded_area_map(feature[field_name])
                category = categories_by_map_field.get(
                    field_name.casefold(), field_name[:-5] or field_name
                )
                if category.casefold() in exact_categories:
                    continue
                for territory, area in area_map.items():
                    rows.append((code, category, territory, float(area)))
                    normalized_categories.add(category.casefold())
            for category, (total_field, _area_field) in pair_items:
                if category.casefold() in normalized_categories:
                    continue
                if category.casefold() in exact_categories:
                    continue
                resolved = resolved_category_fields.get(category)
                if resolved is None:
                    continue
                total_name, label_name = resolved
                try:
                    total = float(feature[total_name] or 0)
                except (TypeError, ValueError):
                    continue
                if total <= 0:
                    continue
                labels = (
                    MapBiomasApiClient.value_list(feature[label_name])
                    if label_name is not None else []
                )
                # A category total can only be attributed to one territory
                # when the response contains exactly one name. With two or
                # more names, the API doesn't provide the individual split
                # here.
                if len(labels) == 1:
                    rows.append((code, category, labels[0], total))
        self.territory_rows_by_layer[source_layer.id()] = rows
        if pending is not None:
            done.update(pending)
        else:
            done.update(
                category.casefold()
                for category in MapBiomasApiClient.TERRITORY_AREA_PAIRS
            )
        return rows

    def territorial_area_totals(
        self,
        layer,
        group_field,
        value_field,
        selected_category=None,
    ):
        definition = TERRITORIAL_AREA_GROUPS.get(
            str(group_field or "").lower()
        )
        if definition is None:
            return None
        category, area_map_field, valid_numeric = definition
        if str(value_field or "").lower() not in valid_numeric:
            return False

        # Prefer the normalized rows created when the result layer is loaded.
        # They preserve exact API allocations or intersections measured over
        # each feature of the selected area. Only computes the actually
        # requested category (not all of them), since this function is
        # called every time the user switches the chart field or checks the
        # summary.
        self.normalize_territory_area_rows(layer, categories=[category])
        if layer.id() in self.territory_rows_by_layer:
            totals = {}
            counts = {}
            for _code, row_category, territory, area in (
                self.territory_rows_by_layer[layer.id()]
            ):
                if row_category.casefold() != category.casefold():
                    continue
                if (
                    selected_category is not None
                    and territory != selected_category
                ):
                    continue
                totals[territory] = totals.get(territory, 0.0) + float(area)
                counts[territory] = counts.get(territory, 0) + 1
            return totals, counts

        has_area_map = layer.fields().indexOf(area_map_field) >= 0

        totals = {}
        counts = {}
        for feature in layer.getFeatures():
            labels = self.feature_group_labels(layer, feature, group_field)
            labels = [
                label for label in labels
                if label not in ("Não informado", self.tr("Sem cruzamento"))
            ]
            area_map = (
                self.decoded_area_map(feature[area_map_field])
                if has_area_map else {}
            )
            if area_map:
                # The allocation map is authoritative; textual label fields can
                # vary in punctuation/casing and must not invalidate valid data.
                allocations = area_map
            elif len(labels) == 1:
                try:
                    allocations = {
                        labels[0]: float(feature[value_field] or 0)
                    }
                except (TypeError, ValueError):
                    continue
            else:
                continue

            for label, area in allocations.items():
                if selected_category is not None and label != selected_category:
                    continue
                totals[label] = totals.get(label, 0.0) + area
                counts[label] = counts.get(label, 0) + 1
        return totals, counts

    def api_statistics_totals(
        self, layer, group_field, calculation, value_field, selected_category
    ):
        """Use server aggregates only when they exactly match the layer query."""
        context = self.result_contexts.get(layer.id(), {})
        if not context.get("api_statistics_exact") or selected_category is not None:
            return None
        statistics = context.get("api_statistics") or {}
        summary = statistics.get("summary") or {}
        group_key = str(group_field or "").lower()
        value_key = str(value_field or "").lower()
        if calculation == "count":
            series_prefix = "alerts"
            ranking_value = "alertsTotal"
        elif calculation == "sum" and value_key in ("areaha", "area_ha", "area"):
            series_prefix = "deforestationArea"
            ranking_value = "areaTotal"
        else:
            return None

        if group_key in ("ano", "mes", "anomes"):
            series_name = (
                series_prefix + "ByYear"
                if group_key == "ano"
                else series_prefix + "ByMonth"
            )
            totals = {}
            for item in summary.get(series_name) or []:
                raw_label = item.get("year") if group_key == "ano" else item.get("date")
                if raw_label in (None, ""):
                    continue
                label = str(raw_label)
                if group_key == "mes":
                    parsed = MapBiomasApiClient.parse_date(label)
                    label = str(parsed.month) if parsed else label
                elif group_key == "anomes":
                    parsed = MapBiomasApiClient.parse_date(label)
                    label = parsed.strftime("%Y-%m") if parsed else label[:7]
                try:
                    totals[label] = totals.get(label, 0.0) + float(
                        item.get("value") or 0
                    )
                except (TypeError, ValueError):
                    continue
            return totals if totals else None

        ranking_definitions = {
            "municipio": ("rankingByCity", "city"),
            "municipality": ("rankingByCity", "city"),
            "estado": ("rankingByState", "state"),
            "state": ("rankingByState", "state"),
            "bioma": ("rankingByBiome", "biome"),
            "biome": ("rankingByBiome", "biome"),
        }
        definition = ranking_definitions.get(group_key)
        if definition is None:
            return None
        collection_name, label_name = definition
        totals = {}
        for item in statistics.get(collection_name) or []:
            label = str(item.get(label_name) or "").strip()
            if not label:
                continue
            try:
                totals[label] = float(item.get(ranking_value) or 0)
            except (TypeError, ValueError):
                continue
        return totals if totals else None

    def update_chart(self):
        """Agrega a camada pelos campos escolhidos na tabela de atributos."""
        layer = self.result_layer()
        if layer is None or not hasattr(self, "chart_widget"):
            if hasattr(self, "chart_widget"):
                self.chart_widget.set_items([])
            return

        group_field = self.chart_group_combo.currentData()
        calculation = self.chart_metric_combo.currentData()
        value_field = self.chart_value_combo.currentData()
        is_crossing_area_group = str(group_field).lower() == "__crossing_area_type__"
        if is_crossing_area_group:
            calculation = "sum"
        self.chart_value_combo.setEnabled(
            calculation != "count" and not is_crossing_area_group
        )
        is_source_group = str(group_field).lower() in (
            "fonte", "sources"
        )
        self.chart_source_mode_combo.setEnabled(
            is_source_group and not bool(
                self.comparison_layer_combo.currentData()
            )
        )
        self.chart_widget.set_chart_type(
            self.chart_type_combo.currentData()
        )
        suffix = ""
        if is_crossing_area_group:
            suffix = " ha"
        elif (
            calculation != "count"
            and value_field
            and "(ha)" in self.chart_value_combo.currentText().lower()
        ):
            suffix = " ha"
        elif (
            calculation != "count"
            and value_field
            and "(%)" in self.chart_value_combo.currentText()
        ):
            suffix = " %"
        self.chart_widget.set_value_format(
            integer_values=(calculation == "count"),
            suffix=suffix,
        )

        if not group_field:
            self.chart_widget.set_items([])
            self.chart_note_label.setText(
                self.tr(
                    "Selecione um campo da tabela para realizar a "
                    "comparação."
                )
            )
            return
        if calculation != "count" and not value_field and not is_crossing_area_group:
            self.chart_widget.set_items([])
            self.chart_note_label.setText(
                self.tr(
                    "A camada não possui campos numéricos para este "
                    "cálculo."
                )
            )
            return

        selected_category = self.chart_category_combo.currentData()
        multivalued_groups = {
            "municipio", "municipality", "estado", "state",
            "bioma", "biome", "unidconserv", "terraindig",
            "assentamento", "quilombo", "reservabio", "autorizacao",
            "manflorest", "protintegral", "usosustent", "terrespecial",
            "app", "reservalegal", "geoparque", "protmunintegral",
            "usomunsust", "protestintegral", "usoestsust",
        }
        def aggregate(candidate_layer):
            totals = {}
            counts = {}
            territorial = None
            if is_crossing_area_group:
                # New, unified field (CruzamentosJson, see to_geojson in
                # api_client.py) has exclusive priority when present — the
                # legacy fields below represent the SAME intersections (the
                # API still returns both while the crossed* fields aren't
                # removed), so summing both together would duplicate each
                # intersection's area under two different labels.
                json_field = self.find_existing_field(
                    candidate_layer, ["CruzamentosJson"]
                )
                if json_field is not None and self.layer_field_has_values(
                    candidate_layer, "CruzamentosJson", numeric=False
                ):
                    for feature in candidate_layer.getFeatures():
                        raw = feature[json_field]
                        if not raw:
                            continue
                        try:
                            entries = json.loads(raw)
                        except (TypeError, ValueError):
                            continue
                        for entry in entries or []:
                            label = str(
                                entry.get("name") or entry.get("type") or ""
                            ).strip()
                            if not label:
                                continue
                            try:
                                area = float(entry.get("totalAreaHa") or 0)
                            except (TypeError, ValueError):
                                continue
                            if area > 0:
                                totals[label] = totals.get(label, 0.0) + area
                    return totals, "crossing_area"
                for field_name, label in self.crossing_area_chart_fields():
                    candidate_field = self.find_existing_field(
                        candidate_layer, [field_name]
                    )
                    if candidate_field is None:
                        continue
                    total = 0.0
                    for feature in candidate_layer.getFeatures():
                        try:
                            total += float(feature[candidate_field] or 0)
                        except (TypeError, ValueError):
                            continue
                    if total > 0:
                        totals[label] = total
                return totals, "crossing_area"
            candidate_group_field = self.find_existing_field(
                candidate_layer, [group_field]
            )
            candidate_value_field = (
                self.find_existing_field(candidate_layer, [value_field])
                if value_field else None
            )
            if candidate_group_field is None:
                return None, None
            if calculation != "count" and candidate_value_field is None:
                return None, None
            api_totals = self.api_statistics_totals(
                candidate_layer,
                candidate_group_field,
                calculation,
                candidate_value_field,
                selected_category,
            )
            if api_totals is not None:
                return api_totals, "api"
            if calculation != "count":
                territorial = self.territorial_area_totals(
                    candidate_layer, candidate_group_field,
                    candidate_value_field,
                    selected_category,
                )
            if (
                calculation != "count"
                and (
                    territorial is False
                    or (
                        territorial is None
                        and str(candidate_group_field).lower()
                        in multivalued_groups
                    )
                )
            ):
                return None, territorial
            if isinstance(territorial, tuple):
                totals, counts = territorial
            else:
                for feature in candidate_layer.getFeatures():
                    if calculation == "count":
                        value = 1.0
                    else:
                        try:
                            value = float(feature[candidate_value_field] or 0)
                        except (TypeError, ValueError):
                            continue
                    labels = self.feature_group_labels(
                        candidate_layer, feature, candidate_group_field
                    )
                    if selected_category is not None:
                        labels = [
                            label for label in labels
                            if label == selected_category
                        ]
                    for label in labels:
                        totals[label] = totals.get(label, 0.0) + value
                        counts[label] = counts.get(label, 0) + 1
            if calculation == "average":
                totals = {
                    label: total / counts[label]
                    for label, total in totals.items() if counts[label]
                }
            return totals, territorial

        layers = self.chart_layers()
        comparison = len(layers) == 2
        type_model = self.chart_type_combo.model()
        for row in range(self.chart_type_combo.count()):
            chart_type = self.chart_type_combo.itemData(row)
            type_model.item(row).setEnabled(
                not comparison or chart_type == "bar"
            )
        if comparison and self.chart_type_combo.currentData() != "bar":
            self.chart_type_combo.blockSignals(True)
            self.chart_type_combo.setCurrentIndex(
                self.chart_type_combo.findData("bar")
            )
            self.chart_type_combo.blockSignals(False)
            self.chart_widget.set_chart_type("bar")

        aggregated = []
        territorial_result = None
        for candidate_layer in layers:
            totals, territorial = aggregate(candidate_layer)
            if totals is None:
                self.chart_widget.set_items([])
                self.chart_note_label.setText(
                    self.tr(
                        "Esta combinação não pode ser calculada com "
                        "precisão com os campos fornecidos pela API. "
                        "Use Número de registros."
                    )
                )
                return
            territorial_result = territorial
            aggregated.append((candidate_layer, totals))

        if comparison:
            display_labels = {}
            normalized_aggregated = []
            for candidate_layer, totals in aggregated:
                normalized_totals = {}
                for category, value in totals.items():
                    key = self.normalized_chart_category(category)
                    if not key:
                        continue
                    display_labels.setdefault(key, str(category).strip())
                    normalized_totals[key] = (
                        normalized_totals.get(key, 0.0) + value
                    )
                normalized_aggregated.append(
                    (candidate_layer, normalized_totals)
                )
            categories = set(display_labels)
            category_totals = {
                category: sum(
                    totals.get(category, 0)
                    for _, totals in normalized_aggregated
                )
                for category in categories
            }
            ordered_categories = sorted(
                categories, key=lambda item: category_totals[item], reverse=True
            )[:self.chart_limit_spin.value()]
            items = []
            for category in ordered_categories:
                for candidate_layer, totals in normalized_aggregated:
                    items.append((
                        display_labels[category],
                        totals.get(category, 0.0),
                        self.chart_layer_label(candidate_layer),
                    ))
            all_items = items
        else:
            totals = aggregated[0][1] if aggregated else {}
            if calculation == "average":
                pass
            chronological_field = str(group_field).lower()
            chronological = (
                self.chart_type_combo.currentData() == "line"
                and chronological_field in ("anomes", "ano", "mes")
            )
            if chronological and chronological_field in ("ano", "mes"):
                def sort_key(item):
                    try:
                        return 0, int(float(item[0]))
                    except (TypeError, ValueError):
                        return 1, str(item[0])
            elif chronological:
                sort_key = lambda item: item[0]
            else:
                sort_key = lambda item: item[1]
            all_items = sorted(
                totals.items(), key=sort_key, reverse=not chronological,
            )
            limit = self.chart_limit_spin.value()
            items = all_items[:limit]
            # Same rule for bars and pie (they used to differ): the N-1
            # largest groups plus "Outros" with the rest, so both charts
            # show the same groups and the same total.
            if not chronological and len(all_items) > limit:
                items = all_items[:max(1, limit - 1)]
                others = all_items[max(1, limit - 1):]
                items.append((
                    self.tr("Outros ({} grupos)", len(others)),
                    sum(value for _, value in others),
                ))
        self.chart_widget.set_items(items)
        calculation_label = self.chart_metric_combo.currentText()
        value_label = (
            ""
            if calculation == "count"
            else self.tr(" de {}", value_field)
        )
        notes = []
        if territorial_result == "crossing_area":
            notes.append(
                self.tr(
                    "Cada barra soma a área numérica informada pela API "
                    "para o respectivo tipo de cruzamento. Os tipos "
                    "podem se sobrepor; não some as barras como se "
                    "fossem área exclusiva."
                )
            )
        elif territorial_result == "api":
            notes.append(
                self.tr(
                    "Resultado agregado pela API para os mesmos filtros "
                    "da camada."
                )
            )
        elif isinstance(territorial_result, tuple):
            notes.append(
                self.tr(
                    "Áreas individualizadas por território apenas "
                    "quando há alocação exata na API ou interseção "
                    "geométrica com cada feição da camada selecionada."
                )
            )
        elif (
            str(group_field).lower() in ("fonte", "sources")
            and self.chart_source_mode_combo.currentData() == "split"
        ):
            notes.append(
                self.tr(
                    "Alertas com múltiplas fontes aparecem uma vez em "
                    "cada fonte; a soma das categorias pode superar o "
                    "total da consulta."
                )
            )
        elif str(group_field).lower() in multivalued_groups:
            notes.append(
                self.tr(
                    "Um alerta pode aparecer em mais de uma categoria "
                    "territorial."
                )
            )
        self.chart_note_label.setText(
            self.tr(
                "{}: {}{} por {}{}. Exibindo {} grupo(s). {}",
                (
                    self.tr("Comparação entre duas camadas")
                    if comparison else self.tr("Ranking")
                ),
                calculation_label,
                value_label,
                (
                    self.tr("tipo de cruzamento")
                    if is_crossing_area_group else group_field
                ),
                (
                    self.tr(" — filtro: {}", selected_category)
                    if selected_category is not None
                    else ""
                ),
                len(items),
                " ".join(notes),
            )
        )

        return None

    SETTINGS_PREFIX = "MapBiomasAlertaOficial"
    LEGACY_SETTINGS_PREFIX = "MapBiomasAlertAnalytics"

    @classmethod
    def migrate_legacy_settings(cls):
        """Copies settings saved under the plugin's old name (accepted
        notices, saved-login references, last export folder) to the new
        prefix once, then removes the old group, so renaming doesn't make
        anyone accept the notices or log in again."""
        settings = QgsSettings()
        settings.beginGroup(cls.LEGACY_SETTINGS_PREFIX)
        legacy_keys = settings.allKeys()
        values = {key: settings.value(key) for key in legacy_keys}
        settings.endGroup()
        if not values:
            return
        for key, value in values.items():
            new_key = "{}/{}".format(cls.SETTINGS_PREFIX, key)
            if not settings.contains(new_key):
                settings.setValue(new_key, value)
        settings.remove(cls.LEGACY_SETTINGS_PREFIX)

    EXPORT_DIR_SETTINGS_KEY = "MapBiomasAlertaOficial/last_export_dir"

    def default_export_dir(self):
        """Last folder used for an export, or the user's Documents.

        Passing a bare file name to QFileDialog makes it start in the
        process working directory, which for QGIS on Windows is often the
        install folder or the drive root — places users can't write to."""
        saved = str(QgsSettings().value(self.EXPORT_DIR_SETTINGS_KEY, "") or "")
        if saved and os.path.isdir(saved):
            return saved
        documents = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DocumentsLocation
        )
        if documents and os.path.isdir(documents):
            return documents
        return os.path.expanduser("~")

    def ask_export_path(self, title, default_name, filter_text, extension):
        """Save dialog that starts in a writable folder, enforces the
        extension, refuses folders without write permission and remembers
        the chosen folder for the next export (of any type)."""
        start_path = os.path.join(self.default_export_dir(), default_name)
        while True:
            path, _ = QFileDialog.getSaveFileName(
                self, self.tr(title), start_path, filter_text
            )
            if not path:
                return None
            if not path.lower().endswith(extension):
                path += extension
            folder = os.path.dirname(path) or "."
            if self.folder_is_writable(folder):
                QgsSettings().setValue(self.EXPORT_DIR_SETTINGS_KEY, folder)
                return path
            self.show_error(
                self.tr(
                    "Sem permissão para gravar em:\n{}\n\nEscolha outra "
                    "pasta (por exemplo, Documentos ou Área de Trabalho).",
                    folder,
                )
            )
            start_path = os.path.join(self.default_export_dir(), default_name)

    @staticmethod
    def folder_is_writable(folder):
        # os.access() is unreliable on Windows (it ignores ACLs, e.g. the
        # drive root), so actually try to create a file there.
        if not os.path.isdir(folder):
            return False
        probe = os.path.join(folder, ".mapbiomas_write_test.tmp")
        try:
            with open(probe, "w", encoding="utf-8"):
                pass
            os.remove(probe)
            return True
        except OSError:
            return False

    def open_chart_window(self):
        """Shows the current chart in its own resizable window, with every
        category visible (the panel keeps a fixed-height preview)."""
        if not self.chart_widget._items:
            self.show_warning(self.tr("Não há gráfico para exibir."))
            return
        from qgis.PyQt.QtWidgets import QDialog

        dialog = QDialog(self)
        dialog.setWindowTitle(
            "MapBiomas Alerta Oficial — {}".format(self.tr("Gráfico"))
        )
        dialog.setWindowFlags(
            dialog.windowFlags()
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowMinimizeButtonHint
        )
        layout = QVBoxLayout(dialog)
        chart = BarChartWidget()
        chart._chart_type = self.chart_widget._chart_type
        chart._integer_values = self.chart_widget._integer_values
        chart._value_suffix = self.chart_widget._value_suffix
        chart.set_items(self.chart_widget._items)
        scroll = QScrollArea()
        scroll.setWidgetResizable(False)
        scroll.setWidget(chart)
        layout.addWidget(scroll, 1)
        note = QLabel(self.chart_note_label.text())
        note.setWordWrap(True)
        note.setObjectName("informationLabel")
        layout.addWidget(note)
        buttons = QHBoxLayout()
        export_button = QPushButton(self.tr("EXPORTAR GRÁFICO PNG"))
        export_button.clicked.connect(self.export_chart_png)
        close_button = QPushButton(self.tr("FECHAR"))
        close_button.clicked.connect(dialog.accept)
        buttons.addStretch()
        buttons.addWidget(export_button)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)
        available = self._screen_rect_for_dialog()
        width = chart.width() + 60
        height = chart.height() + 130
        if available is not None:
            width = min(width, int(available.width() * 0.9))
            height = min(height, int(available.height() * 0.9))
        dialog.resize(max(640, width), max(420, height))
        dialog.exec()

    def _screen_rect_for_dialog(self):
        screen = self.screen() if hasattr(self, "screen") else None
        if screen is None:
            screen = QApplication.primaryScreen()
        return screen.availableGeometry() if screen is not None else None

    def export_chart_png(self):
        """Exports the chart with context, period, legend and branding."""
        layer = self.result_layer()
        if layer is None or layer.featureCount() <= 0:
            self.show_warning(self.tr("Não há gráfico para exportar."))
            return

        path = self.ask_export_path(
            "Exportar gráfico",
            self.export_file_name("GRÁFICO", ".png"),
            "Imagem PNG (*.png)",
            ".png",
        )
        if not path:
            return

        layers = self.chart_layers()
        chart_width = max(1000, self.chart_widget.width())
        chart_height = max(310, self.chart_widget.height())
        header_height = 155
        footer_height = 70
        image = QImage(
            chart_width + 60,
            header_height + chart_height + footer_height,
            QImage.Format.Format_ARGB32,
        )
        image.fill(QColor("#ffffff"))
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(16)
        painter.setFont(title_font)
        painter.setPen(QColor("#832413"))
        logo = QPixmap(self.icon_path)
        title_x = 30
        if not logo.isNull():
            logo = logo.scaled(
                46, 46, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            painter.drawPixmap(30, 10, logo)
            title_x += logo.width() + 10
        painter.drawText(title_x, 42, "MapBiomas Alerta Oficial")

        body_font = QFont()
        body_font.setPointSize(10)
        painter.setFont(body_font)
        painter.setPen(QColor("#24342b"))
        description = "{} | {} | {}".format(
            self.chart_group_combo.currentText(),
            self.chart_metric_combo.currentText(),
            self.chart_value_combo.currentText()
            if self.chart_metric_combo.currentData() != "count"
            else "Número de alertas",
        )
        painter.drawText(30, 70, description)
        y = 94
        for index, candidate_layer in enumerate(layers, 1):
            context = self.result_contexts.get(candidate_layer.id(), {})
            start = context.get("start_date")
            end = context.get("end_date")
            period = (
                "{} a {}".format(
                    start.toString("dd/MM/yyyy"), end.toString("dd/MM/yyyy")
                ) if start is not None and end is not None else "sem período"
            )
            painter.drawText(
                30, y,
                "Camada {}: {} | Período: {}".format(
                    index, candidate_layer.name(), period
                ),
            )
            y += 22

        painter.save()
        painter.translate(30, header_height)
        chart_pixmap = self.chart_widget.pixmap()
        if chart_pixmap is not None and not chart_pixmap.isNull():
            painter.drawPixmap(0, 0, chart_pixmap)
        painter.restore()
        painter.setFont(body_font)
        painter.drawText(
            30, header_height + chart_height + 28,
            self.chart_note_label.text(),
        )
        painter.drawText(
            30, header_height + chart_height + 52,
            self.tr(
                "Exportado em {}",
                QDate.currentDate().toString("dd/MM/yyyy"),
            ),
        )
        painter.end()

        if not image.save(path, "PNG"):
            self.show_error(self.tr("Não foi possível salvar o arquivo PNG."))
            return
        self.show_success(
            self.tr("Gráfico exportado para:\n{}", path), file_path=path
        )

    def territory_export_data(self, layer_ids=None, include_layer=True):
        project = QgsProject.instance()
        selected_ids = layer_ids or list(self.result_layer_ids)
        headers = ["Camada", "CodeAlerta", "Categoria", "Territorio", "AreaHa"]
        rows = []
        for layer_id in selected_ids:
            layer = project.mapLayer(layer_id)
            layer_name = layer.name() if layer is not None else layer_id
            for code, category, territory, area in (
                self.territory_rows_by_layer.get(layer_id) or []
            ):
                rows.append([layer_name, code, category, territory, area])
        if not include_layer:
            headers = headers[1:]
            rows = [row[1:] for row in rows]
        return headers, rows

    @classmethod
    def write_csv_table(cls, path, headers, rows):
        # Same serialization as the main CSV export (decimal comma): raw
        # floats like 1871.043602 were read by Excel pt-BR as
        # 1.871.043.602 in the crossings table.
        with open(path, "w", encoding="utf-8-sig", newline="") as output:
            writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)
            writer.writerow(headers)
            writer.writerows(
                [cls.csv_export_value(value) for value in row] for row in rows
            )


    def write_crossings_readme(self, path):
        text = CROSSINGS_README_TEXT.get(
            self.translator.language, CROSSINGS_README_TEXT["pt"]
        )
        try:
            with open(path, "w", encoding="utf-8") as output:
                output.write(text)
            return True
        except (OSError, PermissionError):
            return False

    def summary_export_rows(self):
        """The "Resumo da consulta" as (indicator, value) rows."""
        speed = getattr(self, "_speed_values", {}) or {}

        def joined(*parts):
            return " · ".join(
                str(part) for part in parts if part and str(part) != "—"
            ) or "—"

        rows = [
            [self.tr("Filtros"), self.filter_summary_label.text()],
            [self.tr("Total de alertas"), self.alert_count_value.text()],
            [self.tr("Área desmatada (ha)"),
             self.total_area_value.text().replace(" ha", "")],
            [self.tr("Média diária (ha/dia)"), speed.get("average") or "—"],
            [self.tr("Maior desmatamento"), joined(
                self.largest_alert_value.text(),
                self.largest_alert_code_value.text(),
                self.largest_alert_location_value.text(),
            )],
            [self.tr("Maior velocidade"), joined(
                speed.get("biggest"), speed.get("biggest_location"),
            )],
            [self.tr("Menor alerta"), joined(
                self.lowest_alert_value.text(),
                self.lowest_alert_code_value.text(),
                self.lowest_alert_location_value.text(),
            )],
            [self.tr("Município com maior área"),
             self.top_municipality_value.text()],
        ]
        for line in self.overlap_counts_value.text().splitlines():
            name, sep, value = line.rpartition(": ")
            if sep:
                rows.append([name, value])
        rows.append([self.tr("Tipo de data"), self.period_type_value.text()])
        rows.append(
            [self.tr("Período analisado"), self.period_result_value.text()]
        )
        rows.append([
            self.tr("Observação"),
            self.tr(
                "Embargos, autorizações e ações de fiscalização: consulte "
                "o laudo na plataforma."
            ),
        ])
        return rows

    def export_result_summary(self):
        if self.alert_count_value.text() in ("", "—"):
            self.show_warning(self.tr("Não há resumo para exportar."))
            return

        path = self.ask_export_path(
            "Exportar resumo",
            self.export_file_name("RESUMO", ".xlsx"),
            "Planilha Excel (*.xlsx)",
            ".xlsx",
        )
        if not path:
            return
        sheets = [(
            "Resumo",
            [self.tr("Indicador"), self.tr("Valor")],
            self.summary_export_rows(),
        )]
        headers = [
            self.layer_comparison_table.horizontalHeaderItem(column).text()
            for column in range(self.layer_comparison_table.columnCount())
        ]
        rows = [
            [
                (
                    self.layer_comparison_table.item(row, column).text()
                    if self.layer_comparison_table.item(row, column)
                    else ""
                )
                for column in range(self.layer_comparison_table.columnCount())
            ]
            for row in range(self.layer_comparison_table.rowCount())
        ]
        if rows:
            sheets.append(("Camadas", headers, rows))
        try:
            self.write_xlsx_sheets(path, sheets)
        except (OSError, PermissionError) as error:
            self.show_error(
                self.tr("Não foi possível exportar a tabela:\n{}", error)
            )
            return

        self.show_success(
            self.tr("Resumo exportado para:\n{}", path), file_path=path
        )

    @staticmethod
    def write_xlsx(path, headers, rows):
        MainDialog.write_xlsx_sheets(
            path, [("Estatísticas", headers, rows)]
        )

    @staticmethod
    def write_xlsx_sheets(path, sheets):
        worksheet_files = {}
        workbook_entries = []
        relationship_entries = []
        content_overrides = []
        for sheet_index, (sheet_name, headers, rows) in enumerate(sheets, 1):
            data = [headers] + rows
            sheet_rows = []
            for row_index, row in enumerate(data, 1):
                cells = []
                for column_index, value in enumerate(row, 1):
                    column = ""
                    number = column_index
                    while number:
                        number, remainder = divmod(number - 1, 26)
                        column = chr(65 + remainder) + column
                    if (
                        isinstance(value, (int, float))
                        and not isinstance(value, bool)
                        and value == value
                        and value not in (float("inf"), float("-inf"))
                    ):
                        cells.append(
                            '<c r="{}{}"><v>{}</v></c>'.format(
                                column, row_index, repr(value)
                            )
                        )
                        continue
                    text = "" if value is None else str(value)
                    # XML 1.0 forbids most control characters; Excel caps
                    # a cell at 32,767 characters.
                    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
                    cells.append(
                        '<c r="{}{}" t="inlineStr"><is><t xml:space="preserve">'
                        "{}</t></is></c>".format(
                            column, row_index, xml_text_escape(text[:32767])
                        )
                    )
                sheet_rows.append(
                    '<row r="{}">{}</row>'.format(row_index, "".join(cells))
                )
            worksheet_files[
                "xl/worksheets/sheet{}.xml".format(sheet_index)
            ] = (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<worksheet xmlns="http://schemas.openxmlformats.org/'
                'spreadsheetml/2006/main"><sheetData>{}</sheetData></worksheet>'
            ).format("".join(sheet_rows))
            safe_name = str(sheet_name or "Planilha")[:31]
            workbook_entries.append(
                '<sheet name="{}" sheetId="{}" r:id="rId{}"/>'.format(
                    xml_text_escape(safe_name), sheet_index, sheet_index
                )
            )
            relationship_entries.append(
                '<Relationship Id="rId{}" Type="http://schemas.openxmlformats.org/'
                'officeDocument/2006/relationships/worksheet" '
                'Target="worksheets/sheet{}.xml"/>'.format(
                    sheet_index, sheet_index
                )
            )
            content_overrides.append(
                '<Override PartName="/xl/worksheets/sheet{}.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.'
                'spreadsheetml.worksheet+xml"/>'.format(sheet_index)
            )
        files = {
            "[Content_Types].xml": (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/'
                '2006/content-types"><Default Extension="rels" '
                'ContentType="application/vnd.openxmlformats-package.'
                'relationships+xml"/><Default Extension="xml" '
                'ContentType="application/xml"/><Override '
                'PartName="/xl/workbook.xml" ContentType="application/vnd.'
                'openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                '{}</Types>'.format("".join(content_overrides))
            ),
            "_rels/.rels": (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/'
                'package/2006/relationships"><Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                'relationships/officeDocument" Target="xl/workbook.xml"/>'
                '</Relationships>'
            ),
            "xl/workbook.xml": (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<workbook xmlns="http://schemas.openxmlformats.org/'
                'spreadsheetml/2006/main" xmlns:r="http://schemas.'
                'openxmlformats.org/officeDocument/2006/relationships">'
                '<sheets>{}</sheets></workbook>'.format(
                    "".join(workbook_entries)
                )
            ),
            "xl/_rels/workbook.xml.rels": (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/'
                'package/2006/relationships">{}</Relationships>'.format(
                    "".join(relationship_entries)
                )
            ),
        }
        files.update(worksheet_files)
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as workbook:
            for name, content in files.items():
                workbook.writestr(name, content.encode("utf-8"))

    def choose_csv_export_mode(self):
        """Asks which detail level to use for the single generated CSV."""
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Question)
        dialog.setWindowTitle(self.tr("Exportar dados CSV"))
        dialog.setText(self.tr("Qual conteúdo você deseja exportar?"))
        dialog.setInformativeText(
            self.tr(
                "Será criado somente um arquivo CSV com a opção escolhida."
            )
        )
        main_button = dialog.addButton(
            self.tr("INFORMAÇÕES PRINCIPAIS"), QMessageBox.ButtonRole.AcceptRole
        )
        full_button = dialog.addButton(
            self.tr("TABELA DE ATRIBUTOS COMPLETA"), QMessageBox.ButtonRole.ActionRole
        )
        dialog.addButton(QMessageBox.StandardButton.Cancel)
        dialog.exec()
        clicked = dialog.clickedButton()
        if clicked is main_button:
            return "main"
        if clicked is full_button:
            return "full"
        return None

    def main_csv_fields(self, layer):
        """Seleciona e nomeia os campos essenciais de cada alerta."""
        preferred = (
            (self.tr("Código do alerta"), ("CodeAlerta", "alertCode", "codigo")),
            (self.tr("Área (ha)"), ("AreaHa", "areaHa", "area_ha", "area")),
            (self.tr("Data de detecção"), ("DataDetec", "detectedAt")),
            (self.tr("Data de publicação"), ("PubImg", "publishedAt")),
            (self.tr("Fonte"), ("Fonte", "sources")),
            (self.tr("Bioma"), ("Bioma", "crossedBiomes")),
            (
                self.tr(self.api_client.country.get("region_label", "Estado")),
                ("Estado", "crossedStates"),
            ),
            (
                self.tr(self.api_client.country.get(
                    "municipality_label", "Município"
                )),
                ("Municipio", "crossedCities"),
            ),
        )
        available = {
            field.name().casefold(): field.name() for field in layer.fields()
        }
        selected = []
        for label, candidates in preferred:
            field_name = next(
                (
                    available.get(candidate.casefold())
                    for candidate in candidates
                    if available.get(candidate.casefold())
                ),
                None,
            )
            if field_name:
                selected.append((label, field_name))
        return selected

    def chart_filtered_layer(self):
        """(layer, kept alert codes, description) with only the alerts of
        the current chart analysis: the chosen "Valor específico", or — for
        a territorial field — the alerts that actually cross it. Returns
        (None, None, None) when no analysis was applied yet."""
        layer = self.result_layer()
        if layer is None or not self.chart_widget._items:
            return None, None, None
        group_field = self.chart_group_combo.currentData()
        category = self.chart_category_combo.currentData()
        code_field = self.find_existing_field(
            layer, ["CodeAlerta", "alertCode", "codigo"]
        )
        empty_labels = {
            self.tr("Sem cruzamento"), "Sem cruzamento", "Não informado",
        }
        keep_ids, keep_codes = [], set()
        for feature in layer.getFeatures():
            try:
                labels = self.feature_group_labels(layer, feature, group_field)
            except (KeyError, ValueError, TypeError):
                labels = None
            if labels is None:
                keep = True
            elif category is not None:
                keep = category in labels
            else:
                keep = any(label not in empty_labels for label in labels)
            if keep:
                keep_ids.append(feature.id())
                if code_field:
                    keep_codes.add(str(feature[code_field] or ""))
        filtered = layer.materialize(QgsFeatureRequest().setFilterFids(keep_ids))
        filtered.setName(layer.name())
        description = "{}{}".format(
            self.chart_group_combo.currentText(),
            " = {}".format(category) if category is not None else "",
        )
        return filtered, keep_codes, description

    def export_file_name(self, button_text, extension):
        """Default file name built from the (translated) button text, e.g.
        "ALERTAS DO GRÁFICO" -> mapbiomas_alerta_alertas_do_grafico.csv."""
        text = self.tr(button_text)
        text = re.sub(r"\(.*?\)", " ", text)
        text = unicodedata.normalize("NFKD", text).encode(
            "ascii", "ignore"
        ).decode("ascii")
        words = re.findall(r"[a-z0-9]+", text.lower())
        if words and words[0] in ("exportar", "export"):
            words = words[1:]
        slug = "_".join(words) or "dados"
        return "mapbiomas_alerta_{}{}".format(slug, extension)

    def full_export_fields(self, layer):
        """(header, field) for every field of the layer. "Estado" and
        "Municipio" are internal names — the header uses the connected
        country's term (e.g. "Departamento" in Colombia/Bolivia/Peru)."""
        region_label = self.tr(self.api_client.country.get("region_label", "Estado"))
        municipality_label = self.tr(self.api_client.country.get(
            "municipality_label", "Município"
        ))
        header_overrides = {
            "Estado": region_label,
            "EstadoAreas": "{}Areas".format(region_label),
            "Municipio": municipality_label,
            "MunicAreas": "{}Areas".format(municipality_label),
        }
        return [
            (header_overrides.get(field.name(), field.name()), field.name())
            for field in layer.fields()
        ]

    def chart_export_columns(self, layer, already_exported):
        """Extra CSV columns for the chart exports: the "Campo para
        comparar" with the same names shown in the chart (e.g. the names
        of the Indigenous Lands) and, for sum/average, the numeric field.
        Works for any country — it only uses the fields the chart offers."""
        columns = []
        exported = {str(name).lower() for name in already_exported}
        group_field = self.chart_group_combo.currentData()
        category = self.chart_category_combo.currentData()
        empty_labels = {
            self.tr("Sem cruzamento"), "Sem cruzamento", "Não informado",
        }
        # Column name = the analysis chosen in "Campo para comparar" (as
        # shown in the menu, already in the country's terms/language). If
        # that field is already in the file, it isn't duplicated.
        header = self.chart_group_combo.currentText()
        if group_field == "__crossing_area_type__":
            area_fields = [
                (field_name, label, self.tr(label))
                for field_name, label in self.crossing_area_chart_fields()
                if layer.fields().indexOf(field_name) >= 0
            ]

            def crossing_types(feature, area_fields=area_fields):
                parts = []
                for field_name, raw_label, label in area_fields:
                    if category is not None and category not in (
                        raw_label, label
                    ):
                        continue
                    try:
                        area = float(feature[field_name] or 0)
                    except (TypeError, ValueError):
                        continue
                    if area > 0:
                        parts.append("{}: {} ha".format(
                            label, "{:.2f}".format(area).replace(".", ",")
                        ))
                return "; ".join(parts)

            if area_fields:
                columns.append((header, crossing_types))
        elif (
            group_field
            and layer.fields().indexOf(group_field) >= 0
            and str(group_field).lower() not in exported
        ):
            def group_value(feature, group_field=group_field):
                try:
                    labels = self.feature_group_labels(
                        layer, feature, group_field
                    )
                except (KeyError, ValueError, TypeError):
                    return ""
                labels = [
                    label for label in (labels or [])
                    if label not in empty_labels
                ]
                if category is not None and category in labels:
                    return category
                return "; ".join(labels)

            columns.append((header, group_value))
        value_field = self.chart_value_combo.currentData()
        if (
            self.chart_metric_combo.currentData() != "count"
            and value_field
            and layer.fields().indexOf(value_field) >= 0
            and str(value_field).lower() not in exported
        ):
            columns.append((
                self.chart_value_combo.currentText(),
                lambda feature, value_field=value_field: feature[value_field],
            ))
        return columns

    def export_attribute_table_xlsx(self):
        """Full attribute table of the current layer as an XLSX sheet."""
        layer = self.result_layer()
        if layer is None or layer.featureCount() <= 0:
            self.show_warning(self.tr("Não há dados filtrados para exportar."))
            return
        export_fields = self.full_export_fields(layer)
        if not export_fields:
            self.show_warning(self.tr("A camada não possui campos para exportar."))
            return
        path = self.ask_export_path(
            "Exportar dados filtrados",
            self.export_file_name("TABELA DE ATRIBUTOS", ".xlsx"),
            "Planilha Excel (*.xlsx)",
            ".xlsx",
        )
        if not path:
            return

        def cell(value):
            if value is None:
                return ""
            is_null = getattr(value, "isNull", None)
            if callable(is_null) and not isinstance(value, (QDate, QDateTime)):
                try:
                    if is_null():
                        return ""
                except TypeError:
                    pass
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return value
            if isinstance(value, (QDate, QDateTime, date, datetime)):
                return self.csv_safe_value(value)
            text = str(value)
            if text == "NULL":
                return ""
            return self.csv_safe_value(text).lstrip("'") if text[:1] != "'" else text

        rows = [
            [cell(feature[field_name]) for _label, field_name in export_fields]
            for feature in layer.getFeatures()
        ]
        try:
            self.write_xlsx_sheets(path, [(
                self.tr("Tabela de atributos"),
                [label for label, _field in export_fields],
                rows,
            )])
        except (OSError, PermissionError) as error:
            self.show_error(
                self.tr("Não foi possível exportar o arquivo:\n{}", error)
            )
            return
        self.show_success(
            self.tr(
                "{} registro(s) — {} — exportado(s) para:\n{}",
                self.format_integer(layer.featureCount()),
                self.tr("tabela de atributos completa"),
                path,
            ),
            file_path=path,
        )

    def export_filtered_csv(self, export_mode=None, chart_filter=False):
        """Exports a single CSV at the detail level the user chose."""
        layer = self.result_layer()
        if chart_filter:
            layer, _codes, _description = self.chart_filtered_layer()
            if layer is None:
                self.show_warning(
                    self.tr(
                        "Aplique uma análise para exportar os alertas do "
                        "gráfico."
                    )
                )
                return
        if layer is None or layer.featureCount() <= 0:
            self.show_warning(self.tr("Não há dados filtrados para exportar."))
            return

        if export_mode not in ("main", "full"):
            export_mode = self.choose_csv_export_mode()
        if export_mode is None:
            return

        # Column getters: (header, callable(feature) -> value).
        extra_columns = []
        if export_mode == "main":
            export_fields = self.main_csv_fields(layer)
            default_name = self.export_file_name(
                "INFORMAÇÕES PRINCIPAIS", ".csv"
            )
            content_label = self.tr("informações principais")
            if chart_filter:
                extra_columns = self.chart_export_columns(
                    layer, [field_name for _label, field_name in export_fields]
                )
                default_name = self.export_file_name(
                    "ALERTAS DO GRÁFICO", ".csv"
                )
                content_label = self.tr("alertas do gráfico")
        else:
            export_fields = self.full_export_fields(layer)
            default_name = self.export_file_name(
                "TABELA DE ATRIBUTOS", ".csv"
            )
            content_label = self.tr("tabela de atributos completa")
        if not export_fields:
            self.show_warning(self.tr("A camada não possui campos para exportar."))
            return

        path = self.ask_export_path(
            "Exportar dados filtrados",
            default_name,
            "Arquivo CSV (*.csv)",
            ".csv",
        )
        if not path:
            return

        try:
            with open(
                path,
                "w",
                encoding="utf-8-sig",
                newline="",
            ) as output:
                writer = csv.writer(
                    output,
                    delimiter=";",
                    quoting=csv.QUOTE_MINIMAL,
                )
                writer.writerow(
                    [label for label, _field in export_fields]
                    + [label for label, _getter in extra_columns]
                )
                for feature in layer.getFeatures():
                    writer.writerow(
                        [
                            self.csv_export_value(feature[field_name])
                            for _label, field_name in export_fields
                        ]
                        + [
                            self.csv_export_value(getter(feature))
                            for _label, getter in extra_columns
                        ]
                    )
        except (OSError, PermissionError) as error:
            self.show_error(
                self.tr("Não foi possível exportar o CSV:\n{}", error)
            )
            return

        message = self.tr(
            "{} registro(s) — {} — exportado(s) para:\n{}",
            self.format_integer(layer.featureCount()),
            content_label,
            path,
        )
        self.show_success(message, file_path=path)

    def export_vector_layer(self, driver_name, chart_filter=False):
        layer = self.result_layer()
        source_layer = layer
        kept_codes = None
        if chart_filter:
            layer, kept_codes, _description = self.chart_filtered_layer()
            if layer is None:
                self.show_warning(
                    self.tr(
                        "Aplique uma análise para exportar os alertas do "
                        "gráfico."
                    )
                )
                return
        if layer is None or layer.featureCount() <= 0:
            self.show_warning(self.tr("Não há dados filtrados para exportar."))
            return

        is_gpkg = driver_name == "GPKG"
        extension = ".gpkg" if is_gpkg else ".shp"
        filter_text = (
            "GeoPackage (*.gpkg)"
            if is_gpkg
            else "Shapefile (*.shp)"
        )
        path = self.ask_export_path(
            "Exportar camada",
            self.export_file_name(
                "ALERTAS DO GRÁFICO" if chart_filter else "CAMADA", extension
            ),
            filter_text,
            extension,
        )
        if not path:
            return

        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = driver_name
        options.fileEncoding = "UTF-8"
        if is_gpkg:
            options.layerName = "alertas"

        result = QgsVectorFileWriter.writeAsVectorFormatV3(
            layer,
            path,
            QgsProject.instance().transformContext(),
            options,
        )
        if result[0] != QgsVectorFileWriter.NoError:
            self.show_error(
                self.tr("Não foi possível exportar a camada:\n{}", result[1])
            )
            return

        # The export needs all territorial categories, not just the one(s)
        # already computed on demand up to this point.
        # Crossing rows live under the original layer's id (the chart cut
        # is a temporary copy); keep only the exported alerts.
        self.normalize_territory_area_rows(source_layer)
        crossing_headers, crossing_rows = self.territory_export_data(
            [source_layer.id()], include_layer=False
        )
        if kept_codes is not None:
            crossing_rows = [
                row for row in crossing_rows if str(row[0]) in kept_codes
            ]
        crossing_csv_path = None
        if crossing_rows and is_gpkg:
            crossing_layer = self.territory_memory_layer(crossing_rows)
            crossing_options = QgsVectorFileWriter.SaveVectorOptions()
            crossing_options.driverName = "GPKG"
            crossing_options.fileEncoding = "UTF-8"
            crossing_options.layerName = "cruzamentos"
            crossing_options.actionOnExistingFile = (
                QgsVectorFileWriter.CreateOrOverwriteLayer
            )
            crossing_result = QgsVectorFileWriter.writeAsVectorFormatV3(
                crossing_layer,
                path,
                QgsProject.instance().transformContext(),
                crossing_options,
            )
            if crossing_result[0] != QgsVectorFileWriter.NoError:
                self.show_error(
                    self.tr(
                        "A camada espacial foi exportada, mas a tabela "
                        "de cruzamentos falhou:\n{}",
                        crossing_result[1],
                    )
                )
                return
        elif crossing_rows and not is_gpkg:
            # Shapefile can't hold a second table inside the same file (nor
            # long field names, like "TerraIndigAreas", without truncating).
            # Instead of losing this information, we generate the same
            # crossings table (long format: one intersection per row) as an
            # auxiliary CSV alongside the .shp — the same data source used
            # for the GeoPackage's internal table.
            crossing_csv_path = path[: -len(extension)] + "_cruzamentos.csv"
            try:
                self.write_csv_table(
                    crossing_csv_path, crossing_headers, crossing_rows
                )
            except (OSError, PermissionError) as error:
                self.show_error(
                    self.tr(
                        "A camada espacial foi exportada, mas o CSV de "
                        "cruzamentos falhou:\n{}",
                        error,
                    )
                )
                return

        message = self.tr("Camada exportada para:\n{}", path)
        readme_path = None
        if crossing_rows:
            readme_suffix = README_FILENAME_SUFFIX.get(
                self.translator.language, "LEIA-ME"
            )
            readme_path = (
                path[: -len(extension)] + "_{}.txt".format(readme_suffix)
            )
            self.write_crossings_readme(readme_path)
            if is_gpkg:
                message += self.tr(
                    "\n\nCruzamentos: tabela interna 'cruzamentos' no "
                    "GeoPackage."
                )
            elif crossing_csv_path:
                message += self.tr(
                    "\n\nCruzamentos (formato longo, um por linha): {}",
                    crossing_csv_path,
                )
            if readme_path:
                message += self.tr(
                    "\n\nVeja {} para entender a diferença entre as "
                    "tabelas (a de cruzamentos tem muito mais linhas — "
                    "isso é esperado).",
                    readme_path,
                )
        if not is_gpkg:
            dictionary_path = self.write_shapefile_field_dictionary(
                layer, path, extension
            )
            if dictionary_path:
                message += self.tr(
                    "\n\nO Shapefile corta nomes de campos em 10 "
                    "caracteres. A correspondência entre o nome cortado "
                    "e o nome completo de cada campo está em:\n{}\n\n"
                    "Use GeoPackage para manter os nomes completos.",
                    dictionary_path,
                )
            else:
                message += self.tr(
                    "\n\nObservação: o Shapefile limita nomes de campos. "
                    "Use GeoPackage quando precisar preservar melhor a "
                    "estrutura."
                )
        self.show_success(message, file_path=path)

    def write_shapefile_field_dictionary(self, source_layer, shp_path, extension):
        """Writes <name>_campos.csv mapping each truncated Shapefile field
        back to its full name and description. Returns the CSV path, or
        None when no field was renamed (or the file couldn't be written).

        The truncated names are read back from the written file instead of
        predicted, since GDAL also de-duplicates them (TerraIndig,
        TerraInd_1, ...)."""
        written = QgsVectorLayer(shp_path, "shp_check", "ogr")
        if not written.isValid():
            return None
        source_fields = source_layer.fields()
        written_names = written.fields().names()
        if len(written_names) != source_fields.count():
            return None
        rows = []
        any_renamed = False
        for index, short_name in enumerate(written_names):
            full_name = source_fields.at(index).name()
            any_renamed = any_renamed or short_name != full_name
            alias = source_layer.attributeAlias(index) or ATTRIBUTE_FIELD_ALIASES.get(
                full_name, ""
            )
            rows.append([short_name, full_name, alias])
        if not any_renamed:
            return None
        dictionary_path = shp_path[: -len(extension)] + "_campos.csv"
        try:
            self.write_csv_table(
                dictionary_path,
                [
                    self.tr("Campo no Shapefile"),
                    self.tr("Nome completo"),
                    self.tr("Descrição"),
                ],
                rows,
            )
        except OSError:
            return None
        return dictionary_path

    @staticmethod
    def territory_memory_layer(rows):
        table = QgsVectorLayer("None", "cruzamentos", "memory")
        provider = table.dataProvider()
        provider.addAttributes([
            QgsField("CodeAlerta", QMetaType.Type.QString, len=30),
            QgsField("Categoria", QMetaType.Type.QString, len=50),
            QgsField("Territorio", QMetaType.Type.QString, len=200),
            QgsField("AreaHa", QMetaType.Type.Double, len=20, prec=6),
        ])
        table.updateFields()
        features = []
        for row in rows:
            feature = QgsFeature(table.fields())
            feature.setAttributes(row)
            features.append(feature)
        provider.addFeatures(features)
        return table

    @staticmethod
    def csv_safe_value(value):
        """Converts values and avoids accidental formulas when opened in Excel."""
        if value is None:
            return ""
        if isinstance(value, QDateTime):
            return value.date().toString("dd/MM/yyyy")
        if isinstance(value, QDate):
            return value.toString("dd/MM/yyyy")
        if isinstance(value, (datetime, date)):
            return value.strftime("%d/%m/%Y")
        text = str(value)
        try:
            if len(text) >= 10 and text[4] == "-" and text[7] == "-":
                return datetime.strptime(text[:10], "%Y-%m-%d").strftime(
                    "%d/%m/%Y"
                )
        except ValueError:
            pass
        if text.startswith(("=", "+", "-", "@")):
            return "'" + text
        return text

    @classmethod
    def csv_export_value(cls, value):
        """Serializa decimais para planilhas configuradas em pt-BR."""
        if isinstance(value, float):
            return str(value).replace(".", ",")
        return cls.csv_safe_value(value)

    def update_result_controls(self):
        layer = self.result_layer()

        enabled = (
            layer is not None
            and layer.isValid()
        ) or bool(getattr(self, "_quick_view_state", None))

        self.open_table_button.setEnabled(
            enabled
        )

        self.remove_layer_button.setEnabled(
            enabled
        )

        self.export_chart_button.setEnabled(enabled)
        self.export_csv_button.setEnabled(enabled)
        self.layers_export_csv_button.setEnabled(enabled)
        self.layers_export_xlsx_button.setEnabled(enabled)
        self.layers_export_gpkg_button.setEnabled(enabled)
        self.layers_export_shp_button.setEnabled(enabled)
        self.export_gpkg_button.setEnabled(enabled)
        self.export_shp_button.setEnabled(enabled)
        self.export_summary_button.setEnabled(enabled)
        if hasattr(self, "export_main_csv_button"):
            self.export_main_csv_button.setEnabled(enabled)
        self.identify_alert_button.setEnabled(enabled)
        self.update_analysis_tab_availability()

        if not enabled:
            if hasattr(self, "chart_widget"):
                self.chart_widget.set_items([])

            self.alert_count_value.setText(
                "—"
            )

            self.total_area_value.setText(
                "—"
            )

            self.period_type_value.setText(
                "—"
            )

            self.period_result_value.setText(
                "—"
            )
            self.clear_alert_details()

    def update_analysis_tab_availability(self):
        """Enable analysis tabs according to the loaded feature counts."""
        if not hasattr(self, "tabs") or not self.country_notice_accepted():
            return
        project = QgsProject.instance()
        layers = [
            project.mapLayer(layer_id) for layer_id in self.result_layer_ids
            if project.mapLayer(layer_id) is not None
            and project.mapLayer(layer_id).isValid()
        ]
        nonempty_layers = [
            layer for layer in layers if layer.featureCount() > 0
        ]
        has_data = bool(nonempty_layers)
        chart_available = (
            any(layer.featureCount() >= 2 for layer in nonempty_layers)
            or len(nonempty_layers) >= 2
        )
        quick = getattr(self, "_quick_view_state", None)
        if quick and not layers:
            # Quick view: tabs stay usable; their actions download the
            # polygons on demand (ensure_full_layer).
            layers = [None]
            has_data = bool(quick.get("total"))
            chart_available = (quick.get("total") or 0) >= 2

        availability = (
            (self.layers_tab, bool(layers),
             "Disponível após carregar uma camada de consulta."),
            (self.results_tab, has_data,
             "Estatísticas exigem ao menos um alerta."),
            (self.details_tab, has_data,
             "Detalhes exigem ao menos um alerta."),
            (self.charts_tab, chart_available,
             "Gráficos exigem ao menos dois alertas ou duas camadas "
             "compatíveis."),
        )
        for tab, enabled, explanation in availability:
            index = self.tabs.indexOf(tab)
            if index < 0:
                continue
            self.tabs.setTabEnabled(index, enabled)
            self.tabs.setTabToolTip(index, "" if enabled else explanation)

        self.export_chart_button.setEnabled(chart_available)
        self.identify_alert_button.setEnabled(has_data)
        if (
            self.tabs.currentWidget() in (
                self.results_tab, self.details_tab, self.charts_tab
            )
            and not self.tabs.isTabEnabled(
                self.tabs.indexOf(self.tabs.currentWidget())
            )
        ):
            self.tabs.setCurrentWidget(self.filters_tab)

    def activate_alert_identification(self):
        """Enables identify mode across all of the plugin's layers."""
        if self.iface is None:
            self.show_warning(self.tr("Não há camada de alertas disponível."))
            return
        project = QgsProject.instance()
        layers = [
            project.mapLayer(layer_id) for layer_id in self.result_layer_ids
            if project.mapLayer(layer_id) is not None
        ]
        if not layers:
            self.show_warning(self.tr("Não há camada de alertas disponível."))
            return

        canvas = self.iface.mapCanvas()
        if (
            self.identify_tool is not None
            and canvas.mapTool() is self.identify_tool
        ):
            self.detail_status_label.setText(
                self.tr(
                    "A identificação está ativa. Clique em outro alerta "
                    "no mapa."
                )
            )
            return
        self.previous_map_tool = canvas.mapTool()
        self.identify_tool = MultiLayerIdentifyTool(canvas, layers)
        self.identify_tool.featureIdentified.connect(
            self.show_identified_feature
        )
        canvas.setMapTool(self.identify_tool)
        self.detail_status_label.setText(
            self.tr(
                "Clique em um alerta de qualquer camada criada pelo "
                "plugin."
            )
        )
        self.tabs.setCurrentWidget(self.details_tab)

    def show_identified_feature(self, layer, feature):
        if layer is None or layer.id() not in self.result_layer_ids:
            return
        self.current_result_layer_id = layer.id()
        index = self.analysis_layer_combo.findData(layer.id())
        if index >= 0:
            self.analysis_layer_combo.blockSignals(True)
            self.analysis_layer_combo.setCurrentIndex(index)
            self.analysis_layer_combo.blockSignals(False)
        if self.iface is not None:
            self.iface.setActiveLayer(layer)
        self.show_alert_feature_details(feature)

    def show_alert_feature_details(self, feature):
        """Consulta e apresenta imagens do alerta identificado."""
        layer = self.result_layer()
        if layer is None:
            return

        code_field = self.find_existing_field(
            layer, ["CodeAlerta", "alertCode", "codigo"]
        )
        if not code_field:
            self.show_error(
                self.tr(
                    "A camada não possui o código necessário para "
                    "consultar o alerta."
                )
            )
            return

        alert_code = feature[code_field]
        if alert_code is None:
            self.show_warning(self.tr("O alerta selecionado não possui código."))
            return

        layer.selectByIds([feature.id()])
        self.current_detail_alert_code = str(alert_code)
        self.detail_status_label.setText(
            self.tr("Carregando detalhes do alerta {}...", alert_code)
        )
        self.open_report_button.setEnabled(False)

        try:
            details = self.api_client.alert_details(alert_code)
            self.display_alert_details(details)
            self.tabs.setCurrentWidget(self.details_tab)
        except ApiAuthenticationError as error:
            self.detail_status_label.setText(
                self.tr("A sessão expirou antes de carregar o alerta.")
            )
            self.handle_api_authentication_error(error)
        except Exception as error:
            self.detail_status_label.setText(
                self.tr("Não foi possível carregar o alerta.")
            )
            self.show_error(self.tr(str(error)))

    def display_alert_details(self, details):
        code = details.get("alertCode")
        area = details.get("areaHa") or 0
        sources = MapBiomasApiClient.join_values(details.get("sources"))
        biomes = MapBiomasApiClient.join_values(details.get("crossedBiomes"))
        states = MapBiomasApiClient.join_values(details.get("crossedStates"))
        cities = MapBiomasApiClient.join_values(details.get("crossedCities"))
        self.current_detail_alert_code = str(code)
        self.detail_status_label.setText(
            self.tr("Alerta {} carregado.", code)
        )
        detail_rows = [
            (self.tr("Área"), "{} ha".format(self.format_decimal(area))),
            (self.tr("Detecção"), details.get("detectedAt") or "—"),
            (self.tr("Publicação"), details.get("publishedAt") or "—"),
            (self.tr("Fonte(s)"), sources or "—"),
            (self.tr("Bioma(s)"), biomes or "—"),
            (
                "{}(s)".format(
                    self.tr(self.api_client.country.get("region_label", "Estado"))
                ),
                states or "—",
            ),
            (
                "{}(s)".format(
                    self.tr(self.api_client.country.get(
                        "municipality_label", "Município"
                    ))
                ),
                cities or "—",
            ),
        ]
        self.detail_metadata_label.setText(
            "<br>".join(
                "<b>{}:</b> {}".format(
                    html.escape(str(label)),
                    html.escape(str(value)),
                )
                for label, value in detail_rows
            )
        )
        intersections = []
        alert_intersections = details.get("alertIntersections") or []
        if alert_intersections:
            # New, unified field (see comment in
            # api_client.py/ALERT_INTERSECTIONS_FIELDS) — each item already
            # represents a whole intersection type, with the label (name)
            # already ready and translated by the API itself, the crossed
            # territory names and the total area. This also captures
            # country-specific intersection types (configurable per
            # initiative) that the legacy crossed* fields never exposed.
            for entry in alert_intersections:
                type_label = str(
                    entry.get("name") or entry.get("type") or ""
                ).strip()
                if not type_label:
                    continue
                total_area = entry.get("totalAreaHa")
                names = entry.get("names") or []
                rendered_names = (
                    MapBiomasApiClient.join_values(names) if names else ""
                )
                parts = []
                if total_area not in (None, 0, 0.0):
                    parts.append(
                        "{} ha".format(self.format_decimal(total_area))
                    )
                if rendered_names:
                    parts.append(rendered_names)
                rendered = " — ".join(parts) if parts else "—"
                intersections.append(
                    "<b>{}:</b> {}".format(
                        html.escape(type_label), html.escape(rendered)
                    )
                )
        intersection_labels = {}
        if not intersections:
            # Fallback: schema not yet migrated to alertIntersections on
            # this API, or the alert returned no new entries — try the
            # legacy crossed* fields (deprecated, but still working while
            # the API doesn't remove them).
            intersection_labels = {
            "crossedConservationUnits": "Unidades de Conservação",
            "crossedConservationUnitsArea": "Área em Unidade de Conservação",
            "crossedIndigenousLands": "Terras Indígenas",
            "crossedIndigenousLandsArea": "Área em Terra Indígena",
            "crossedSettlements": "Assentamentos",
            "crossedSettlementsArea": "Área em assentamentos",
            "crossedQuilombos": "Territórios quilombolas",
            "crossedQuilombosArea": "Área quilombola",
            "crossedBiosphereReserves": "Reservas da Biosfera",
            "crossedBiosphereReservesArea": "Área em Reserva da Biosfera",
            "crossedForestManagementsActivities": "Manejo florestal",
            "crossedForestManagementsArea": "Área de manejo",
            "crossedFederalProtectedAreaIntegralProtections": "Proteção integral federal",
            "crossedFederalProtectedAreaIntegralProtectionsArea": "Área de proteção integral",
            "crossedFederalProtectedAreaSustainableUses": "Uso sustentável federal",
            "crossedFederalProtectedAreaSustainableUsesArea": "Área de uso sustentável",
            "crossedPermanentProtectedArea": "Área de Preservação Permanente",
            "crossedPermanentProtectedAreaTotal": "APPs",
            "crossedLegalReservesArea": "Área de Reserva Legal",
            "crossedLegalReservesTotal": "Reservas Legais",
            "crossedSpecialTerritories": "Territórios especiais",
            "crossedSpecialTerritoriesArea": "Área em território especial",
            }
            area_fields = {
                name for name in intersection_labels
                if name.endswith("Area")
            }
            area_fields.add("crossedPermanentProtectedArea")
            for field_name, label in intersection_labels.items():
                value = details.get(field_name)
                if value in (None, "", [], 0, 0.0):
                    continue
                if field_name in area_fields:
                    rendered = "{} ha".format(self.format_decimal(value))
                elif isinstance(value, (list, tuple)):
                    rendered = MapBiomasApiClient.join_values(value)
                else:
                    rendered = str(value)
                if rendered:
                    intersections.append(
                        "<b>{}:</b> {}".format(
                            html.escape(self.tr(label)),
                            html.escape(str(rendered)),
                        )
                    )
        crossings_note = (
            "<br><b style=\"color:#C0392B;\">{}</b>".format(
                self.tr(NOT_SHOWN_CROSSINGS_NOTE)
            )
        )
        crossings_title = "<b>{}</b><br>".format(
            self.tr("Cruzamentos territoriais e ambientais")
        )
        if intersections:
            self.detail_intersections_label.setText(
                crossings_title
                + "<br>".join(intersections)
                + crossings_note
            )
        else:
            # Considered "supported" if the API has alertIntersections
            # (new mechanism) OR at least one legacy crossed* field
            # (deprecated mechanism, but still valid) — only falls back to
            # the "no compatible fields" message if neither exists in this
            # API's schema.
            supported = (
                self.api_client.supports_alert_intersections()
                or self.api_client.supported_analytic_fields()
            )
            message = self.tr(
                "Nenhum cruzamento territorial ou ambiental (Unidade "
                "de Conservação, Terra Indígena, Assentamento etc.) "
                "foi registrado para este alerta. Imóveis rurais "
                "cruzados aparecem em uma seção própria, logo abaixo."
                if supported
                else
                "A API deste país não disponibilizou campos de "
                "cruzamento compatíveis."
            )
            self.detail_intersections_label.setText(
                crossings_title
                + message
                + crossings_note
            )
        self.populate_detail_crossings(details, intersection_labels)

        # The selected alert's images live in their own card
        # (selected_alert_layout/selected_alert_container), separate from
        # the "other alerts on the same property" block — this keeps them
        # visible even if the user closes the other related alerts.
        self.open_report_button.setEnabled(True)
        layer = self.result_layer()
        self.previous_alert_button.setEnabled(False)
        self.next_alert_button.setEnabled(False)
        self.clear_same_property_cards()
        self.clear_selected_alert_card()
        if layer is not None:
            feature = self.feature_by_alert_code(layer, str(code))
            if feature is not None:
                self.selected_alert_layout.addWidget(
                    self.create_information_title("Alerta selecionado")
                )
                self.selected_alert_layout.addWidget(
                    self.create_same_property_card(layer, feature)
                )
                self.selected_alert_container.setVisible(True)

    def populate_detail_crossings(self, details, labels):
        self.same_property_cache = None
        self.same_crossing_status_label.clear()
        self.same_crossing_status_label.setVisible(False)
        self.detail_crossing_combo.blockSignals(True)
        self.detail_crossing_combo.clear()
        value = MapBiomasApiClient.join_values(
            details.get("ruralPropertiesCodes")
        )
        seen = set()
        for item_value in MapBiomasApiClient.value_list(value):
            normalized = item_value.casefold()
            if normalized in seen:
                continue
            seen.add(normalized)
            self.detail_crossing_combo.addItem(
                self.tr("Imóvel rural — {}", item_value),
                ("ImovelCod", item_value),
            )
        available = self.detail_crossing_combo.count() > 0
        self.detail_crossing_combo.setEnabled(available)
        self.detail_crossing_combo.blockSignals(False)
        property_codes = [
            self.detail_crossing_combo.itemData(index)[1]
            for index in range(self.detail_crossing_combo.count())
        ]
        if property_codes:
            self.crossed_properties_label.setText(
                "<b>{}</b><br>{}<br><b style=\"color:#C0392B;\">{}</b>".format(
                    self.tr(
                        "{} imóvel(is) cruzado(s)", len(property_codes)
                    ),
                    "<br>".join(
                        "• {}".format(html.escape(str(code)))
                        for code in property_codes
                    ),
                    html.escape(self.tr(ALERT_IN_PROPERTY_NOTE)),
                )
            )
        elif not self.api_client.country.get(
            "has_rural_property_search", True
        ):
            self.crossed_properties_label.setText(
                self.tr(
                    "Este país não possui cadastro de imóveis rurais "
                    "integrado à plataforma."
                )
            )
        else:
            self.crossed_properties_label.setText(
                self.tr("Nenhum imóvel rural informado para este alerta.")
            )
        self.update_same_property_button()
        self.same_crossing_list.clear()
        self.same_crossing_list.setVisible(False)
        self.clear_same_property_cards()
        self.same_property_scroll.setVisible(False)

    def feature_by_alert_code(self, layer, alert_code):
        if layer is None:
            return None
        code_field = self.find_existing_field(
            layer, ["CodeAlerta", "alertCode", "codigo"]
        )
        if not code_field:
            return None
        # Code->id index built once per layer and reused (same one used by
        # navigate_alert) — each subsequent lookup is O(1) instead of a
        # linear scan over the whole layer.
        index, _order = self._ensure_alert_index(layer, code_field)
        feature_id = index.get(str(alert_code))
        if feature_id is None:
            return None
        feature = layer.getFeature(feature_id)
        return feature if feature.isValid() else None

    def set_same_property_progress(self, message, button_text):
        """Mostra imediatamente o andamento das consultas relacionadas."""
        self.same_crossing_button.setEnabled(False)
        self.same_crossing_button.setText(button_text)
        self.same_crossing_status_label.setText(message)
        self.same_crossing_status_label.setVisible(True)
        QgsApplication.processEvents()

    def update_same_property_button(self):
        property_count = self.detail_crossing_combo.count()
        if property_count and self.same_property_cache is None:
            self.set_same_property_progress(
                self.tr(
                    "Consultando os imóveis relacionados ao alerta..."
                ),
                self.tr("CONSULTANDO OUTROS ALERTAS..."),
            )
        groups = self.same_property_alert_groups(show_progress=True)
        count = sum(len(group["alerts"]) for group in groups)
        self.same_crossing_button.setEnabled(count > 0)
        self.same_crossing_button.setText(
            self.tr("VER {} OUTRO(S) ALERTA(S) E SUAS IMAGENS", count)
            if count
            else self.tr("OUTROS ALERTAS NOS MESMOS IMÓVEIS: {}", 0)
        )
        self.same_crossing_status_label.clear()
        self.same_crossing_status_label.setVisible(False)

    def same_property_alert_groups(self, show_progress=False):
        """Return unique related alerts grouped by rural property."""
        if self.same_property_cache is not None:
            return self.same_property_cache
        property_codes = [
            self.detail_crossing_combo.itemData(index)[1]
            for index in range(self.detail_crossing_combo.count())
        ]
        groups = []
        seen_alerts = set()
        total_properties = len(property_codes)
        for property_index, property_code in enumerate(property_codes, 1):
            if show_progress:
                self.set_same_property_progress(
                    "Consultando imóvel {} de {}: {}".format(
                        property_index, total_properties, property_code
                    ),
                    "CONSULTANDO IMÓVEL {}/{}...".format(
                        property_index, total_properties
                    ),
                )
            try:
                summary = self.api_client.rural_property(property_code)
            except Exception as error:
                QgsMessageLog.logMessage(
                    "Failed to query rural property {}: {}".format(
                        property_code, error
                    ),
                    "MapBiomas Alerta Oficial",
                    Qgis.Warning,
                )
                continue
            alerts = []
            for alert in summary.get("alerts") or []:
                code = str(alert.get("alertCode") or "").strip()
                if (
                    not code
                    or code == str(self.current_detail_alert_code or "")
                    or code in seen_alerts
                ):
                    continue
                seen_alerts.add(code)
                alerts.append(alert)
            if alerts:
                groups.append({
                    "property_code": property_code,
                    "summary": summary,
                    "alerts": alerts,
                })
        self.same_property_cache = groups
        return groups

    def clear_same_property_cards(self):
        self.same_property_related_loaded = False
        if hasattr(self, "close_same_property_button"):
            self.close_same_property_button.setVisible(False)
        while self.same_property_layout.count():
            item = self.same_property_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def clear_selected_alert_card(self):
        """Clears only the selected alert's card (before/after images).
        Kept separate from clear_same_property_cards(): this one runs
        when switching alerts, while that one is also called by
        close_same_property_view() and must not touch this card."""
        if not hasattr(self, "selected_alert_layout"):
            return
        self.selected_alert_container.setVisible(False)
        while self.selected_alert_layout.count():
            item = self.selected_alert_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def close_same_property_view(self):
        """Hides the box without destroying cards, images or loaded state."""
        self.same_property_scroll.setVisible(False)
        self.close_same_property_button.setVisible(False)
        if self.related_alert_layer_id:
            QgsProject.instance().removeMapLayer(self.related_alert_layer_id)
            self.related_alert_layer_id = None
        if self.same_property_related_loaded:
            self.same_crossing_button.setEnabled(True)
            self.same_crossing_button.setText(
                self.tr("REABRIR OUTROS ALERTAS E SUAS IMAGENS")
            )

    def create_same_property_card(self, layer, feature):
        code_field = self.find_existing_field(
            layer, ["CodeAlerta", "alertCode", "codigo"]
        )
        area_field = self.find_existing_field(
            layer, ["IntAreaHa", "AreaHa", "areaHa"]
        )
        city_field = self.find_existing_field(
            layer, ["Municipio", "municipality"]
        )
        code = str(feature[code_field]) if code_field else str(feature.id())
        area = float(feature[area_field] or 0) if area_field else 0.0

        card = QFrame()
        card.setObjectName("coordinatesFrame")
        layout = QVBoxLayout(card)
        title = self.create_information_title("Alerta {}".format(code))
        layout.addWidget(title)
        location = str(feature[city_field] or "—") if city_field else "—"
        metadata = QLabel(
            "<b>{}:</b> {} ha &nbsp;&nbsp; "
            "<b>{}:</b> {}".format(
                self.tr("Área do alerta"),
                self.format_decimal(area),
                self.tr(self.api_client.country.get(
                    "municipality_label", "Município"
                )),
                html.escape(location),
            )
        )
        metadata.setWordWrap(True)
        layout.addWidget(metadata)

        images_layout = QHBoxLayout()
        before_frame, before_title, before_label = self.create_image_card(
            "Imagem antes"
        )
        after_frame, after_title, after_label = self.create_image_card(
            "Imagem depois"
        )
        images_layout.addWidget(before_frame)
        images_layout.addWidget(after_frame)
        layout.addLayout(images_layout)

        actions = QHBoxLayout()
        open_button = AutoFitPushButton("ABRIR LAUDO NA PLATAFORMA")
        self.register_translatable(
            open_button, "ABRIR LAUDO NA PLATAFORMA"
        )
        map_button = AutoFitPushButton("VER NO MAPA")
        self.register_translatable(map_button, "VER NO MAPA")
        open_button.clicked.connect(
            lambda _checked=False, alert_code=code:
            self.open_alert_report(alert_code)
        )
        map_button.clicked.connect(
            lambda _checked=False, selected_layer=layer, selected=feature:
            self.open_related_alert_feature(selected_layer, selected)
        )
        actions.addWidget(open_button)
        actions.addWidget(map_button)
        layout.addLayout(actions)

        try:
            details = self.api_client.alert_details(code)
            images = sorted(
                details.get("publishedImages") or [],
                key=lambda value: str(value.get("acquiredAt") or ""),
            )
            referenced = {
                str(value.get("reference") or "").strip().casefold(): value
                for value in images if value.get("reference")
            }
            before = referenced.get("before") or (images[0] if images else None)
            after = referenced.get("after") or (
                images[-1] if len(images) > 1 else None
            )
            self.load_detail_image(
                before, before_label, before_title, "Imagem antes",
                details.get("imageAcquiredBeforeAt"),
            )
            self.load_detail_image(
                after, after_label, after_title, "Imagem depois",
                details.get("imageAcquiredAfterAt"),
            )
        except Exception as error:
            before_label.setText(
                self.tr("Não foi possível carregar as imagens.")
            )
            after_label.setText(self.tr(str(error)))
        return card

    def create_same_property_api_card(self, layer, alert):
        code = str(alert.get("alertCode") or "—")
        try:
            if not alert.get("publishedImages") or not alert.get("geometryWkt"):
                details = self.api_client.alert_details(code)
                alert = dict(alert)
                alert.update(details)
        except Exception as error:
            QgsMessageLog.logMessage(
                "Could not complete alert {}: {}".format(
                    code, error
                ),
                "MapBiomas Alerta Oficial", Qgis.Warning,
            )
        try:
            area = float(alert.get("areaHa") or 0)
        except (TypeError, ValueError):
            area = 0.0
        card = QFrame()
        card.setObjectName("coordinatesFrame")
        layout = QVBoxLayout(card)
        layout.addWidget(self.create_information_title("Alerta {}".format(code)))
        metadata = QLabel(
            "<b>{}:</b> {} ha &nbsp;&nbsp; "
            "<b>{}:</b> {} &nbsp;&nbsp; "
            "<b>{}:</b> {}".format(
                self.tr("Área do alerta"),
                self.format_decimal(area),
                self.tr("Detecção"),
                html.escape(str(alert.get("detectedAt") or "—")[:10]),
                self.tr("Publicação"),
                html.escape(str(alert.get("publishedAt") or "—")[:10]),
            )
        )
        metadata.setWordWrap(True)
        layout.addWidget(metadata)

        images_layout = QHBoxLayout()
        before_frame, before_title, before_label = self.create_image_card(
            "Imagem antes"
        )
        after_frame, after_title, after_label = self.create_image_card(
            "Imagem depois"
        )
        images_layout.addWidget(before_frame)
        images_layout.addWidget(after_frame)
        layout.addLayout(images_layout)
        images = sorted(
            alert.get("publishedImages") or [],
            key=lambda value: str(value.get("acquiredAt") or ""),
        )
        referenced = {
            str(value.get("reference") or "").strip().casefold(): value
            for value in images if value.get("reference")
        }
        before = referenced.get("before") or (images[0] if images else None)
        after = referenced.get("after") or (
            images[-1] if len(images) > 1 else None
        )
        self.load_detail_image(
            before, before_label, before_title, "Imagem antes",
            alert.get("imageAcquiredBeforeAt"),
        )
        self.load_detail_image(
            after, after_label, after_title, "Imagem depois",
            alert.get("imageAcquiredAfterAt"),
        )

        feature_layer, feature = self.feature_and_layer_by_alert_code(code)
        geometry = QgsGeometry.fromWkt(str(alert.get("geometryWkt") or ""))
        has_api_geometry = not geometry.isNull() and not geometry.isEmpty()
        actions = QHBoxLayout()
        open_button = AutoFitPushButton("ABRIR LAUDO NA PLATAFORMA")
        self.register_translatable(
            open_button, "ABRIR LAUDO NA PLATAFORMA"
        )
        map_button = AutoFitPushButton("VER NO MAPA")
        self.register_translatable(map_button, "VER NO MAPA")
        open_button.clicked.connect(
            lambda _checked=False, alert_code=code:
            self.open_alert_report(alert_code)
        )
        map_button.setEnabled(feature is not None or has_api_geometry)
        map_button.setToolTip(
            self.tr("Centralizar este alerta no mapa.")
            if feature is not None or has_api_geometry
            else self.tr("A API não retornou a geometria deste alerta.")
        )
        if feature is not None:
            map_button.clicked.connect(
                lambda _checked=False, selected_layer=feature_layer,
                selected=feature:
                self.open_related_alert_feature(selected_layer, selected)
            )
        elif has_api_geometry:
            map_button.clicked.connect(
                lambda _checked=False, alert_code=code,
                selected_geometry=geometry:
                self.show_related_alert_geometry(
                    alert_code, selected_geometry
                )
            )
        actions.addWidget(open_button)
        actions.addWidget(map_button)
        layout.addLayout(actions)
        return card

    def open_related_alert_feature(self, layer, feature):
        """Centers the alert without replacing the open cards and images."""
        if layer is None or feature is None:
            return
        tree_node = QgsProject.instance().layerTreeRoot().findLayer(layer.id())
        if tree_node is not None:
            tree_node.setItemVisibilityChecked(True)
        if self.iface is not None:
            self.iface.setActiveLayer(layer)
        self.center_alert_on_map(layer, feature)

    def center_related_alert_geometry(self, geometry):
        """Centers on an API geometry that isn't present in the layers."""
        if self.iface is None or geometry is None:
            return
        if geometry.isNull() or geometry.isEmpty():
            return
        extent = geometry.boundingBox()
        source_crs = QgsCoordinateReferenceSystem(self.api_client.CRS)
        project_crs = QgsProject.instance().crs()
        if source_crs.isValid() and source_crs != project_crs:
            transform = QgsCoordinateTransform(
                source_crs, project_crs, QgsProject.instance()
            )
            extent = transform.transformBoundingBox(extent)
        extent.scale(1.35)
        canvas = self.iface.mapCanvas()
        canvas.setExtent(extent)
        canvas.refresh()

    def show_related_alert_geometry(self, alert_code, geometry):
        """Exibe e seleciona no mapa o alerta relacionado retornado pela API."""
        if geometry is None or geometry.isNull() or geometry.isEmpty():
            return
        project = QgsProject.instance()
        if self.related_alert_layer_id:
            previous = project.mapLayer(self.related_alert_layer_id)
            if previous is not None:
                project.removeMapLayer(previous.id())
            self.related_alert_layer_id = None

        source_crs = QgsCoordinateReferenceSystem(self.api_client.CRS)
        geometry_name = QgsWkbTypes.displayString(geometry.wkbType())
        related_layer = QgsVectorLayer(
            "{}?crs={}".format(geometry_name, source_crs.authid()),
            "MapBiomas Alerta — relacionado {}".format(alert_code),
            "memory",
        )
        if not related_layer.isValid():
            self.center_related_alert_geometry(geometry)
            return
        related_layer.dataProvider().addAttributes([
            QgsField("CodeAlerta", QMetaType.Type.QString, len=30),
        ])
        related_layer.updateFields()
        feature = QgsFeature(related_layer.fields())
        feature.setAttributes([str(alert_code)])
        feature.setGeometry(QgsGeometry(geometry))
        related_layer.dataProvider().addFeature(feature)
        related_layer.updateExtents()
        self.apply_result_style(related_layer, self.api_client.country)
        project.addMapLayer(related_layer)
        self.related_alert_layer_id = related_layer.id()
        stored_feature = next(related_layer.getFeatures(), None)
        if stored_feature is None:
            return
        if self.iface is not None:
            self.iface.setActiveLayer(related_layer)
        self.center_alert_on_map(related_layer, stored_feature)

    def feature_and_layer_by_alert_code(self, alert_code):
        project = QgsProject.instance()
        for layer_id in self.result_layer_ids:
            candidate_layer = project.mapLayer(layer_id)
            if candidate_layer is None:
                continue
            feature = self.feature_by_alert_code(candidate_layer, alert_code)
            if feature is not None:
                return candidate_layer, feature
        return None, None

    def show_same_crossing_alerts(self):
        layer = self.result_layer()
        if self.same_property_related_loaded:
            self.same_property_scroll.setVisible(True)
            self.close_same_property_button.setVisible(True)
            self.same_crossing_button.setEnabled(False)
            self.same_crossing_button.setText(
                self.tr("OUTROS ALERTAS E IMAGENS ADICIONADOS ABAIXO")
            )
            self.same_crossing_status_label.setText(
                self.tr(
                    "Os alertas relacionados e suas imagens já estão "
                    "carregados."
                )
            )
            self.same_crossing_status_label.setVisible(True)
            return
        if layer is None:
            self.same_crossing_status_label.setText(
                self.tr(
                    "Não há uma camada de alertas disponível para esta "
                    "consulta."
                )
            )
            self.same_crossing_status_label.setVisible(True)
            return

        self.set_same_property_progress(
            self.tr(
                "Preparando a consulta dos alertas e das imagens..."
            ),
            self.tr("PROCESSANDO OUTROS ALERTAS..."),
        )
        groups = self.same_property_alert_groups(show_progress=True)
        if not groups:
            self.update_same_property_button()
            self.same_crossing_status_label.setText(
                self.tr(
                    "Nenhum outro alerta foi encontrado nos mesmos "
                    "imóveis."
                )
            )
            self.same_crossing_status_label.setVisible(True)
            return

        # Remove only the trailing spacer; keep the selected alert card.
        if self.same_property_layout.count():
            last_index = self.same_property_layout.count() - 1
            last_item = self.same_property_layout.itemAt(last_index)
            if last_item is not None and last_item.spacerItem() is not None:
                self.same_property_layout.takeAt(last_index)

        self.same_property_layout.addWidget(
            self.create_information_title("Outros alertas encontrados")
        )
        scope_note = QLabel(self.tr(ALERT_IN_PROPERTY_NOTE))
        scope_note.setWordWrap(True)
        scope_note.setObjectName("informationLabel")
        scope_note.setStyleSheet("color: #C0392B; font-weight: 700;")
        self.same_property_layout.addWidget(scope_note)

        total_alerts = sum(len(group["alerts"]) for group in groups)
        processed_alerts = 0
        for group in groups:
            summary = group["summary"]
            alerts = group["alerts"]
            property_code = group["property_code"]
            section = CollapsibleSection(
                self.tr(
                    "Imóvel {} — {} outro(s) alerta(s)",
                    property_code, len(alerts),
                ),
                expanded=True,
            )
            property_text = QLabel(
                "<b>{}:</b> {} &nbsp;&nbsp; "
                "<b>{}:</b> {} ha &nbsp;&nbsp; "
                "<b>{}:</b> {}".format(
                    self.tr("Tipo"),
                    html.escape(str(summary.get("carType") or "—")),
                    self.tr("Área do imóvel"),
                    self.format_decimal(summary.get("areaHa") or 0),
                    self.tr(self.api_client.country.get("region_label", "Estado")),
                    html.escape(str(summary.get("state") or "—")),
                )
            )
            property_text.setWordWrap(True)
            section.content_layout.addWidget(property_text)
            # Add the section before loading its cards so each alert shows
            # up as soon as it's ready, instead of all at once at the end
            # (with 2+ alerts it looked like only one had been found).
            self.same_property_layout.addWidget(section)
            self.same_property_scroll.setVisible(True)
            for alert in alerts:
                processed_alerts += 1
                alert_code = str(alert.get("alertCode") or "—")
                self.set_same_property_progress(
                    self.tr(
                        "Carregando alerta {} de {} (código {}) e suas "
                        "imagens...",
                        processed_alerts, total_alerts, alert_code,
                    ),
                    self.tr(
                        "CARREGANDO ALERTA {}/{}...",
                        processed_alerts, total_alerts,
                    ),
                )
                section.content_layout.addWidget(
                    self.create_same_property_api_card(layer, alert)
                )
                QgsApplication.processEvents()

        self.same_property_layout.addStretch()
        self.same_property_scroll.setVisible(True)
        self.same_property_related_loaded = True
        self.close_same_property_button.setVisible(True)
        self.same_crossing_button.setEnabled(False)
        self.same_crossing_button.setText(
            self.tr("OUTROS ALERTAS E IMAGENS ADICIONADOS ABAIXO")
        )
        self.same_crossing_status_label.setText(
            self.tr(
                "Processamento concluído: {} outro(s) alerta(s) e suas "
                "imagens foram carregados.",
                total_alerts,
            )
        )
        self.same_crossing_status_label.setVisible(True)

    def open_same_crossing_alert(self, item):
        layer = self.result_layer()
        if layer is None:
            return
        feature = next(
            layer.getFeatures(
                QgsFeatureRequest().setFilterFid(item.data(Qt.ItemDataRole.UserRole))
            ),
            None,
        )
        if feature is None:
            return
        self.center_alert_on_map(layer, feature)
        self.show_alert_feature_details(feature)

    def load_detail_image(
        self,
        image,
        image_label,
        title_label,
        title,
        fallback_date,
    ):
        image_label.clear_image()
        date = (image or {}).get("acquiredAt") or fallback_date or "—"
        constellation = str(
            (image or {}).get("constellation") or ""
        ).strip()
        satellite = str((image or {}).get("satellite") or "").strip()
        sensor = " / ".join(
            value for value in (constellation, satellite) if value
        )
        title_label.setText(
            "<b>{}</b><br>{}{}".format(
                html.escape(self.tr(str(title))),
                html.escape(str(date)[:10]),
                (
                    " — {}".format(html.escape(sensor.upper()))
                    if sensor
                    else ""
                ),
            )
        )
        urls = []
        # The platform and the official plugin use the original image as the
        # primary source; some thumbnails may be just placeholders.
        for field_name in ("url", "urlMedium"):
            value = (image or {}).get(field_name)
            if value and value not in urls:
                urls.append(value)
        if not urls:
            image_label.setText(
                self.tr("Imagem não disponibilizada pela API.")
            )
            return

        last_error = None
        image_server_timeout = False
        for url in urls:
            for authenticated in (False, True):
                try:
                    data = self.api_client.download_image(
                        url,
                        authenticated=authenticated,
                    )
                    pixmap = QPixmap()
                    if not pixmap.loadFromData(data):
                        raise RuntimeError(
                            self.tr("Formato de imagem não reconhecido.")
                        )
                    image_label.set_image(pixmap)
                    return
                except Exception as error:
                    last_error = error
                    error_text = str(error).casefold()
                    if any(
                        marker in error_text
                        for marker in (
                            "expir", "timeout", "não respondeu",
                            "temporariamente indisponível",
                        )
                    ):
                        image_server_timeout = True
                        break
            if image_server_timeout:
                break
        if last_error:
            image_label.setText(
                self.tr(
                    "O servidor de imagens não respondeu. "
                    "Tente novamente mais tarde."
                )
                if image_server_timeout
                else str(last_error)
            )

    def clear_alert_details(self):
        self.current_detail_alert_code = None
        self.same_property_cache = None
        if not hasattr(self, "detail_status_label"):
            return
        self.detail_status_label.setText(
            self.tr(
                "Identifique um alerta no mapa para consultar imagens "
                "e detalhes."
            )
        )
        self.detail_metadata_label.setText("—")
        self.detail_intersections_label.setText(
            self.initial_intersections_text()
        )
        self.detail_crossing_combo.clear()
        self.detail_crossing_combo.setEnabled(False)
        self.crossed_properties_label.setText(
            self.tr(
                "Este país não possui cadastro de imóveis rurais "
                "integrado à plataforma."
            )
            if not self.api_client.country.get(
                "has_rural_property_search", True
            )
            else self.initial_properties_text()
        )
        self.same_crossing_button.setEnabled(False)
        self.same_crossing_button.setText(
            self.tr("OUTROS ALERTAS NOS MESMOS IMÓVEIS: {}", 0)
        )
        self.same_crossing_status_label.clear()
        self.same_crossing_status_label.setVisible(False)
        self.same_crossing_list.clear()
        self.same_crossing_list.setVisible(False)
        self.clear_same_property_cards()
        self.clear_selected_alert_card()
        self.same_property_scroll.setVisible(False)
        self.before_title_label.setText(self.tr("Imagem antes"))
        self.after_title_label.setText(self.tr("Imagem depois"))
        self.before_image_label.clear_image()
        self.after_image_label.clear_image()
        self.before_image_label.setText(self.tr("Sem imagem"))
        self.after_image_label.setText(self.tr("Sem imagem"))
        self.open_report_button.setEnabled(False)
        self.previous_alert_button.setEnabled(False)
        self.next_alert_button.setEnabled(False)

    def _ensure_alert_index(self, layer, code_field):
        """Builds (once per layer) the code→id index and feature order,
        reused by feature_by_alert_code() and navigate_alert() to avoid
        a linear layer scan on every identify/next/previous click."""
        code_index = self.alert_code_index_by_layer.get(layer.id())
        order = self.alert_order_by_layer.get(layer.id())
        if code_index is not None and order is not None:
            return code_index, order
        code_index = {}
        order = []
        for feature in layer.getFeatures():
            order.append(feature.id())
            code_index[str(feature[code_field])] = feature.id()
        self.alert_code_index_by_layer[layer.id()] = code_index
        self.alert_order_by_layer[layer.id()] = order
        self.alert_position_by_layer[layer.id()] = {
            feature_id: position
            for position, feature_id in enumerate(order)
        }
        return code_index, order

    def navigate_alert(self, offset):
        layer = self.result_layer()
        if layer is None or not self.current_detail_alert_code:
            return
        code_field = self.find_existing_field(
            layer, ["CodeAlerta", "alertCode", "codigo"]
        )
        if not code_field:
            return
        code_index, order = self._ensure_alert_index(layer, code_field)
        if not order:
            return
        current_id = code_index.get(self.current_detail_alert_code)
        position_by_id = self.alert_position_by_layer.get(layer.id(), {})
        index = position_by_id.get(current_id, 0)
        feature_id = order[(index + offset) % len(order)]
        feature = layer.getFeature(feature_id)
        if not feature.isValid():
            return
        self.center_alert_on_map(layer, feature)
        self.show_alert_feature_details(feature)

    def center_alert_on_map(self, layer, feature):
        if self.iface is None or not feature.hasGeometry():
            return
        for layer_id in self.result_layer_ids:
            candidate = QgsProject.instance().mapLayer(layer_id)
            if candidate is not None:
                candidate.removeSelection()
        layer.selectByIds([feature.id()])
        extent = feature.geometry().boundingBox()
        project_crs = QgsProject.instance().crs()
        if layer.crs() != project_crs:
            transform = QgsCoordinateTransform(
                layer.crs(), project_crs, QgsProject.instance()
            )
            extent = transform.transformBoundingBox(extent)
        extent.scale(1.35)
        canvas = self.iface.mapCanvas()
        QgsProject.instance().setSelectionColor(QColor("#FFD400"))
        canvas.setExtent(extent)
        canvas.refresh()

    def open_current_alert_report(self):
        if not self.current_detail_alert_code:
            return
        self.open_alert_report(self.current_detail_alert_code)

    def open_alert_report(self, alert_code):
        base_url = self.api_client.country.get("platform_url", "")
        url = "{}alerta/{}".format(
            base_url.rstrip("/") + "/",
            alert_code,
        )
        QDesktopServices.openUrl(QUrl(url))

    def zoom_to_result_layer(self):
        layer = self.result_layer()

        if (
            layer is None
            or self.iface is None
        ):
            return

        if layer.featureCount() <= 0:
            self.show_warning(
                "A camada não possui alertas."
            )
            return

        self.iface.setActiveLayer(
            layer
        )

        self.iface.zoomToActiveLayer()

    def open_result_table(self):
        layer = self.result_layer()

        if (
            layer is None
            or self.iface is None
        ):
            return

        self.iface.showAttributeTable(
            layer
        )

    def remove_result_layer(
        self,
        show_message=True,
    ):
        if (
            self.identify_tool is not None
            and self.iface is not None
            and self.iface.mapCanvas().mapTool() is self.identify_tool
        ):
            self.iface.mapCanvas().unsetMapTool(self.identify_tool)
        self.identify_tool = None

        layer = self.result_layer()
        layer_id = layer.id() if layer is not None else self.current_result_layer_id
        if layer_id:
            self.territory_rows_by_layer.pop(layer_id, None)
            self.territory_categories_done.pop(layer_id, None)
            self.layer_comparison_cache.pop(layer_id, None)
            self.alert_code_index_by_layer.pop(layer_id, None)
            self.alert_order_by_layer.pop(layer_id, None)
            self.alert_position_by_layer.pop(layer_id, None)

        if layer is not None:
            QgsProject.instance().removeMapLayer(
                layer.id()
            )
            self.result_layer_ids = [
                layer_id for layer_id in self.result_layer_ids
                if layer_id != layer.id()
            ]
            self.result_contexts.pop(layer.id(), None)
        if layer_id:
            self.cleanup_result_temporary_file(layer_id)

        self.current_result_layer_id = (
            self.result_layer_ids[-1] if self.result_layer_ids else None
        )
        self.refresh_analysis_layers()

        if self.current_result_layer_id:
            self.change_analysis_layer()
        else:
            self.result_status_label.setText(
                self.tr("Faça uma consulta para visualizar as estatísticas.")
            )

        self.update_result_controls()

        self.refresh_vector_layers()

        if show_message:
            self.show_success(
                "A camada foi removida."
            )

    def remove_all_result_layers(self):
        project = QgsProject.instance()
        for layer_id in list(self.result_layer_ids):
            self.territory_rows_by_layer.pop(layer_id, None)
            self.territory_categories_done.pop(layer_id, None)
            self.layer_comparison_cache.pop(layer_id, None)
            self.alert_code_index_by_layer.pop(layer_id, None)
            self.alert_order_by_layer.pop(layer_id, None)
            self.alert_position_by_layer.pop(layer_id, None)
            layer = project.mapLayer(layer_id)
            if layer is not None:
                layer.removeSelection()
                project.removeMapLayer(layer_id)
        self.result_layer_ids = []
        self.result_contexts = {}
        self.remove_quick_view_layer()
        for layer_id in list(self.result_temporary_files):
            self.cleanup_result_temporary_file(layer_id)
        self.current_result_layer_id = None
        self.refresh_analysis_layers()
        self.update_result_controls()
        if self.iface is not None:
            canvas = self.iface.mapCanvas()
            canvas.clearCache()
            if hasattr(canvas, "refreshAllLayers"):
                canvas.refreshAllLayers()
            canvas.refresh()

    def cleanup_result_temporary_file(self, layer_id):
        path = self.result_temporary_files.pop(layer_id, None)
        if path and not MapBiomasApiClient.remove_temporary_file(path):
            QgsMessageLog.logMessage(
                "Could not remove the temporary file: {}".format(path),
                "MapBiomas Alerta Oficial",
                Qgis.Warning,
            )

    def update_platform(self):
        config = country_config(
            self.country_combo.currentData()
        )
        if self.api_client.country.get("code") != config.get("code"):
            self.remove_all_result_layers()
            self.api_client = MapBiomasApiClient(config)

        # Only suggest the country's default language if the person hasn't
        # already picked a language manually via the selector — after the
        # first manual switch, their choice is respected even when the
        # country changes.
        if not self._language_locked:
            suggested = DEFAULT_LANGUAGE_BY_COUNTRY.get(
                config.get("code"), "pt"
            )
            if suggested != self.translator.language:
                self.translator.set_language(suggested)
                self.retranslate_ui()
                self.refresh_dynamic_texts()
            index = self.language_combo.findData(suggested)
            if index >= 0:
                self.language_combo.blockSignals(True)
                self.language_combo.setCurrentIndex(index)
                self.language_combo.blockSignals(False)

        enabled = bool(config.get("enabled"))
        platform_text = config["platform"]
        if not enabled:
            platform_text += "\n" + config.get("status", "Serviço não configurado.")
        self.platform_value_label.setText(platform_text)
        self.populate_sources(config)
        self.reset_crossing_options()
        if hasattr(self, "api_access_help_icon"):
            self.update_api_access_help_text()

        # Not every country has a rural property registry integrated with
        # the platform (see "has_rural_property_search" in
        # country_config.py). Hide the option in other countries instead of
        # leaving available a search that would have no data to return.
        has_rural_property = bool(
            config.get("has_rural_property_search", True)
        )
        self.area_car_radio.setVisible(has_rural_property)
        # The map-server quick view is no longer offered (it didn't
        # apply the search filters). Every search builds the real layer.
        has_quick_view = False
        self.quick_view_checkbox.setVisible(has_quick_view)
        if not has_quick_view:
            self.quick_view_checkbox.setChecked(False)
            self.download_full_button.setVisible(False)
        if not has_rural_property and self.area_car_radio.isChecked():
            self.area_country_radio.setChecked(True)

        self.update_auth_controls()
        if enabled and not self.api_client.authenticated:
            self.login_status_label.setText(self.tr("API desconectada"))
            self.restore_saved_login()
        elif not enabled:
            self.login_status_label.setText(
                self.tr("API indisponível para {}", config["name"])
            )
        self.update_area_controls()
        self.update_country_notice()
        if hasattr(self, "layer_comparison_table"):
            self.layer_comparison_table.setHorizontalHeaderLabels(
                self.comparison_table_header_labels()
            )
        self.update_top_municipality_title()

    def notice_settings_key(self):
        code = str(self.country_combo.currentData() or "")
        notice = NOTICE_BY_COUNTRY.get(code, {})
        version = str(notice.get("version") or "1")
        return "MapBiomasAlertaOficial/notice/{}/{}".format(code, version)

    def country_notice_accepted(self):
        value = QgsSettings().value(self.notice_settings_key(), False)
        return value is True or str(value).lower() in ("1", "true", "yes")

    def update_country_notice(self):
        code = str(self.country_combo.currentData() or "")
        config = country_config(code)
        notice = NOTICE_BY_COUNTRY.get(code, {})
        self.notice_country_label.setText(config.get("platform", code))
        notice_html = notice.get(
            "html",
            "<p>{}</p>".format(
                self.tr(
                    "Não há nota informativa configurada para este país."
                )
            ),
        )
        notice_url = str(notice.get("url") or "")
        if notice_url:
            notice_html += (
                "<hr><p><a href=\"{}\"><b>{}</b></a></p>"
            ).format(
                html.escape(notice_url, quote=True),
                self.tr(
                    "ACESSAR A NOTA INFORMATIVA COMPLETA NA PLATAFORMA"
                ),
            )
        self.notice_browser.setHtml(notice_html)
        accepted = self.country_notice_accepted()
        self.notice_checkbox.blockSignals(True)
        self.notice_checkbox.setChecked(accepted)
        self.notice_checkbox.blockSignals(False)
        self.notice_checkbox.setEnabled(not accepted)
        self.accept_notice_button.setEnabled(not accepted)
        self.accept_notice_button.setText(
            self.tr("NOTA ACEITA") if accepted else self.tr("LI E CONCORDO")
        )
        for index in range(self.tabs.count()):
            self.tabs.setTabEnabled(
                index,
                accepted or self.tabs.widget(index) is self.notice_tab,
            )
        notice_index = self.tabs.indexOf(self.notice_tab)
        if notice_index >= 0 and hasattr(self.tabs.tabBar(), "setTabVisible"):
            self.tabs.tabBar().setTabVisible(notice_index, not accepted)
        if not accepted:
            self.tabs.setCurrentWidget(self.notice_tab)
        else:
            self.update_analysis_tab_availability()

    def show_country_notice(self):
        notice_index = self.tabs.indexOf(self.notice_tab)
        if notice_index < 0:
            return
        if hasattr(self.tabs.tabBar(), "setTabVisible"):
            self.tabs.tabBar().setTabVisible(notice_index, True)
        self.tabs.setCurrentWidget(self.notice_tab)

    def handle_main_tab_changed(self, index):
        if not self.country_notice_accepted():
            return
        notice_index = self.tabs.indexOf(self.notice_tab)
        if notice_index >= 0 and index != notice_index:
            if hasattr(self.tabs.tabBar(), "setTabVisible"):
                self.tabs.tabBar().setTabVisible(notice_index, False)

    def accept_country_notice(self):
        if not self.notice_checkbox.isChecked():
            return
        QgsSettings().setValue(self.notice_settings_key(), True)
        self.update_country_notice()
        self.tabs.setCurrentWidget(self.filters_tab)

    def populate_sources(self, config):
        """Populates the known detection sources for the selected country."""
        self.source_combo.blockSignals(True)
        self.source_combo.clear()
        for source_value, source_label in config.get("sources", ()):
            self.source_combo.add_check_item(source_label, source_value)
        self.source_combo.update_text()
        self.source_combo.blockSignals(False)
        self.update_selected_sources_label()

    def populate_sources_from_api(self):
        config = country_config(self.country_combo.currentData())
        configured_labels = dict(config.get("sources", ()))
        try:
            source_types = self.api_client.source_types()
        except Exception:
            source_types = config.get("sources", ())
        self.source_combo.blockSignals(True)
        self.source_combo.clear()
        for source_value, _description in source_types:
            self.source_combo.add_check_item(
                configured_labels.get(source_value, source_value),
                source_value,
            )
        self.source_combo.update_text()
        self.source_combo.blockSignals(False)
        self.update_selected_sources_label()
        self.update_filter_summary()

    def populate_biome_options(self):
        """Fills the biome filter from the API's territoryOptions. Hidden
        when the country's API has no biome category."""
        category, territories, error = self.api_client.biome_territories()
        self.biome_category = category
        self.biome_combo.blockSignals(True)
        self.biome_combo.clear()
        for territory_id, name in territories:
            self.biome_combo.add_check_item(name, territory_id)
        self.biome_combo.update_text()
        self.biome_combo.blockSignals(False)
        available = bool(category and territories)
        self._biome_available = available
        self.biome_combo.setEnabled(available)
        self.biome_hint_label.setVisible(not available)
        if not available:
            self.biome_hint_label.setText(
                self.tr(
                    "Não foi possível carregar a lista de biomas da API ({}). "
                    "Use uma camada vetorial do bioma como área de interesse.",
                    error or "—",
                )
            )

    def selected_biome_filter(self):
        """(territory_ids, category, names) for the API, or (None, None, [])."""
        if (
            not self.area_biome_radio.isChecked()
            or not self.biome_category
            or not getattr(self, "_biome_available", False)
        ):
            return None, None, []
        ids = self.biome_combo.checked_data()
        if not ids:
            return None, None, []
        return ids, self.biome_category, self.biome_combo.checked_labels()

    def reset_crossing_options(self):
        self.crossing_field_combo.blockSignals(True)
        self.crossing_field_combo.clear()
        self.crossing_field_combo.addItem(
            "Conecte-se à API para consultar as opções",
            None,
        )
        self.crossing_field_combo.setEnabled(False)
        self.crossing_field_combo.blockSignals(False)
        self.crossing_mode_combo.setCurrentIndex(0)

    @staticmethod
    def crossing_field_label(field):
        """Generates a readable label for a dynamically discovered
        "crossed*" field with no known translation in CROSSING_OPTIONS
        (e.g. "crossedConsejosComunitarios" -> "Consejos Comunitarios")."""
        name = field
        if name.startswith("crossed"):
            name = name[len("crossed"):]
        words = re.findall(r"[A-Z][a-z0-9]*|[A-Z]+(?![a-z])|[a-z0-9]+", name)
        return " ".join(words) if words else field

    def populate_crossing_options(self):
        supported = set(self.api_client.supported_analytic_fields())
        is_brazil = self.api_client.country.get("code") == "BR"
        # Schema introspection (supported_analytic_fields) only confirms
        # that the field NAME exists — the GraphQL schema is the same for
        # every country, so that alone doesn't differentiate countries.
        # That's why:
        #
        # 1) Fields that are Brazil-specific by definition (quilombola,
        #    SNUC subdivisions, special territory) are always excluded
        #    outside Brazil — they can't exist by definition, so no live
        #    check is needed.
        # 2) Fields with no API counter to verify (Biosphere Reserve) are
        #    also kept restricted to Brazil as a precaution.
        # 3) The other known fields (MapBiomasApiClient.CROSSING_OPTIONS)
        #    only appear outside Brazil if
        #    MapBiomasApiClient.crossing_availability() confirms, with real
        #    data (counters from the API's own statistics summary), that
        #    that country has at least one alert in the category — the
        #    field existing in the schema isn't enough.
        # 4) Dynamic discovery of "crossed*" fields outside the known list
        #    stays limited to Brazil: since the schema is identical for
        #    every country, this discovery can only find generic Brazil
        #    fields (e.g. "crossedGeoparks"), never a category exclusive to
        #    another country without real-data verification behind it.
        excluded_fields = set(
            self.api_client.country.get("crossing_fields_exclude") or ()
        )
        known_fields = dict(MapBiomasApiClient.CROSSING_OPTIONS)
        if self.api_client.supports_alert_intersections():
            # Mechanism recommended by the API documentation instead of the
            # crossed* fields (deprecated — see ALERT_INTERSECTIONS_FIELDS).
            # Discovers intersection types by sampling real alerts, instead
            # of relying on a fixed list of field names — so it automatically
            # covers country-configurable categories with no known crossed*
            # equivalent.
            discovered_types = self.api_client.discover_intersection_types()
            options = [
                ("intersection:{}".format(type_key), label)
                for type_key, label in discovered_types
            ]
        elif is_brazil:
            options = [
                (field, label)
                for field, label in MapBiomasApiClient.CROSSING_OPTIONS
                if field in supported and field not in excluded_fields
            ]
            discovered = sorted(
                field for field in supported
                if field.startswith("crossed")
                and field not in known_fields
                and field not in excluded_fields
                and not field.endswith((
                    "Area", "Ids", "List", "Total", "Categories",
                    "Activities",
                ))
            )
            options.extend(
                (field, self.crossing_field_label(field))
                for field in discovered
            )
        else:
            availability = self.api_client.crossing_availability()
            verifiable_fields = set(
                MapBiomasApiClient.CROSSING_AVAILABILITY_COUNTS.values()
            )
            options = []
            for field, label in MapBiomasApiClient.CROSSING_OPTIONS:
                if field not in supported or field in excluded_fields:
                    continue
                if field in verifiable_fields:
                    # Only included if the matching counter in the
                    # statistics summary confirms real data (> 0) — if the
                    # check itself failed (empty dict), show nothing for
                    # this category instead of risking showing something
                    # unconfirmed.
                    if availability.get(field):
                        options.append((field, label))
                # Known fields with no counter (and not in
                # UNVERIFIABLE_CROSSING_FIELDS nor in
                # crossing_fields_exclude) shouldn't exist in the list
                # anymore, but as a safety net, if one shows up, it isn't
                # included outside Brazil without verification.
        self.crossing_field_combo.blockSignals(True)
        self.crossing_field_combo.clear()
        if options:
            self.crossing_field_combo.addItem(
                self.tr("Qualquer cruzamento disponível"),
                "__any__",
            )
            for field, label in options:
                self.crossing_field_combo.addItem(self.tr(label), field)
            self.crossing_field_combo.setEnabled(True)
            self.crossing_mode_combo.setEnabled(True)
        else:
            introspection_error = self.api_client.analytic_fields_error
            availability_error = getattr(
                self.api_client, "crossing_availability_error", None
            )
            discovery_error = getattr(
                self.api_client, "intersection_discovery_error", None
            )
            if introspection_error:
                status_text = self.tr(
                    "Não foi possível consultar os cruzamentos"
                )
            elif discovery_error:
                status_text = self.tr(
                    "Não foi possível verificar os cruzamentos "
                    "disponíveis para {} — tente novamente mais tarde.",
                    self.country_combo.currentText(),
                )
            elif availability_error and not is_brazil:
                # Different from "confirmed absent": the real-data check
                # (crossing_availability) failed or came back in an
                # unexpected shape — we can't trust that there really is no
                # intersection at all, only that it couldn't be checked.
                status_text = self.tr(
                    "Não foi possível verificar os cruzamentos "
                    "disponíveis para {} — tente novamente mais tarde.",
                    self.country_combo.currentText(),
                )
            else:
                status_text = self.tr(
                    "Nenhum cruzamento disponível nesta API"
                )
            self.crossing_field_combo.addItem(status_text, None)
            self.crossing_field_combo.setEnabled(False)
            self.crossing_mode_combo.setCurrentIndex(0)
            self.crossing_mode_combo.setEnabled(False)
        self.crossing_field_combo.blockSignals(False)
        self.update_filter_summary()

    def toggle_password_visibility(self, checked):
        self.password_edit.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        )
        self.toggle_password_button.setText(
            self.tr("Ocultar" if checked else "Mostrar")
        )

    def login_api(self, silent=False, credentials=None):
        """Authenticates the current session without persisting the password or token."""
        self.login_button.setEnabled(False)
        self.login_status_label.setText(self.tr("Conectando à API..."))
        if credentials is None:
            email = self.email_edit.text().strip()
            password = self.password_edit.text()
        else:
            email, password = credentials
        self.password_edit.clear()
        self.toggle_password_button.setChecked(False)
        try:
            self.api_client.login(
                email,
                password,
            )
            self.populate_sources_from_api()
            self.populate_biome_options()
            self.populate_crossing_options()
            if not self.api_client.authenticated:
                raise ApiAuthenticationError(
                    self.api_client.analytic_fields_error
                    or self.tr("A sessão da API expirou. Entre novamente.")
                )
            if self.remember_login_checkbox.isChecked():
                if not self.save_api_credentials(email, password):
                    self.remember_login_checkbox.blockSignals(True)
                    self.remember_login_checkbox.setChecked(False)
                    self.remember_login_checkbox.blockSignals(False)
                    if not silent:
                        self.show_warning(
                            self.tr(
                                "O login foi realizado, mas o QGIS não "
                                "conseguiu salvar as credenciais no "
                                "Gerenciador de Autenticação."
                            )
                        )
            self.login_status_label.setText(
                self.tr("API conectada como {}", email)
            )
            self.login_section.set_expanded(False)
            if not silent:
                self.show_success(self.tr("Login realizado com sucesso."))
        except Exception as error:
            self.api_client.logout()
            self.login_status_label.setText(
                self.tr("Falha no login automático")
                if silent
                else self.tr("Falha na autenticação")
            )
            if not silent:
                self.show_error(self.tr(str(error)))
        finally:
            self.update_auth_controls()

    def handle_api_authentication_error(self, error):
        self.api_client.logout()
        self.password_edit.clear()
        self.toggle_password_button.setChecked(False)
        self.login_status_label.setText(self.tr("Sessão expirada"))
        self.login_section.set_expanded(True)
        self.update_auth_controls()
        self.show_error(self.tr(str(error)))

    def logout_api(self):
        """Ends the token; saved credentials remain if that option is on."""
        self.api_client.logout()
        self.password_edit.clear()
        self.toggle_password_button.setChecked(False)
        self.login_status_label.setText(self.tr("API desconectada"))
        self.login_section.set_expanded(True)
        self.reset_crossing_options()
        self.update_auth_controls()

    def auth_settings_key(self):
        country_code = self.api_client.country.get("code", "default")
        return "MapBiomasAlertaOficial/authcfg/{}".format(country_code)

    def save_api_credentials(self, email, password):
        """Saves credentials in QGIS's secure authentication store."""
        auth_manager = QgsApplication.authManager()
        settings = QgsSettings()
        auth_id = str(settings.value(self.auth_settings_key(), "") or "")

        if auth_id:
            config = QgsAuthMethodConfig()
            if auth_manager.loadAuthenticationConfig(auth_id, config, True):
                config.setConfig("username", email)
                config.setConfig("password", password)
                if auth_manager.updateAuthenticationConfig(config):
                    return True

        config = QgsAuthMethodConfig()
        config.setName(
            "MapBiomas Alerta Oficial — {}".format(
                self.api_client.country.get("name", "API")
            )
        )
        config.setMethod("Basic")
        config.setConfig("username", email)
        config.setConfig("password", password)
        if not auth_manager.storeAuthenticationConfig(config):
            return False

        settings.setValue(self.auth_settings_key(), config.id())
        return True

    def restore_saved_login(self):
        """Recupera credenciais do QGIS e tenta autenticar automaticamente."""
        settings = QgsSettings()
        auth_id = str(settings.value(self.auth_settings_key(), "") or "")
        if not auth_id:
            return

        config = QgsAuthMethodConfig()
        if not QgsApplication.authManager().loadAuthenticationConfig(
            auth_id, config, True
        ):
            settings.remove(self.auth_settings_key())
            return

        email = config.config("username")
        password = config.config("password")
        if not email or not password:
            return

        self.remember_login_checkbox.blockSignals(True)
        self.remember_login_checkbox.setChecked(True)
        self.remember_login_checkbox.blockSignals(False)
        self.email_edit.setText(email)
        self.login_api(silent=True, credentials=(email, password))

    def forget_saved_login(self):
        """Removes only the configuration created by this plugin."""
        settings = QgsSettings()
        auth_id = str(settings.value(self.auth_settings_key(), "") or "")
        if auth_id:
            QgsApplication.authManager().removeAuthenticationConfig(auth_id)
        settings.remove(self.auth_settings_key())

    def handle_remember_login_changed(self, checked):
        if not checked:
            self.forget_saved_login()

    def update_auth_controls(self):
        config_enabled = bool(
            self.api_client.country.get("enabled")
        )
        authenticated = self.api_client.authenticated
        self.login_button.setEnabled(config_enabled and not authenticated)
        self.logout_button.setEnabled(authenticated)
        self.email_edit.setEnabled(config_enabled and not authenticated)
        self.password_edit.setEnabled(config_enabled and not authenticated)
        self.remember_login_checkbox.setEnabled(
            config_enabled and not authenticated
        )
        self.search_button.setEnabled(config_enabled)

        if not config_enabled:
            self.search_button.setText(
                self.tr("SERVIÇO AINDA NÃO CONFIGURADO")
            )
        elif not authenticated:
            self.search_button.setText(self.tr("FAÇA LOGIN PARA BUSCAR"))
        else:
            self.search_button.setText(self.tr("BUSCAR ALERTAS"))

        if hasattr(self, "login_section"):
            self.login_section.set_expanded(not authenticated)
        if hasattr(self, "responsive_forms"):
            self.update_responsive_layout()

    @staticmethod
    def format_integer(value):
        return "{:,}".format(
            int(value)
        ).replace(
            ",",
            ".",
        )

    @staticmethod
    def format_decimal(value):
        text = "{:,.1f}".format(
            float(value)
        )

        return (
            text
            .replace(",", "_")
            .replace(".", ",")
            .replace("_", ".")
        )

    def show_success(
        self,
        message,
        file_path=None,
    ):
        if self.iface is None:
            return
        bar = self.iface.messageBar()
        if not file_path:
            bar.pushMessage(
                "MapBiomas Alerta Oficial",
                message,
                level=Qgis.Success,
                duration=5,
            )
            return
        # When the message points to an exported file, add an "ABRIR PASTA"
        # button instead of leaving the path as plain text (which isn't
        # clickable) — opens the folder directly in the system's file
        # explorer.
        item = bar.createMessage("MapBiomas Alerta Oficial", message)
        open_folder_button = QPushButton(self.tr("ABRIR PASTA"))
        open_folder_button.setCursor(Qt.CursorShape.PointingHandCursor)
        open_folder_button.clicked.connect(
            lambda: self.open_containing_folder(file_path)
        )
        item.layout().addWidget(open_folder_button)
        bar.pushWidget(item, Qgis.Success, 8)

    @staticmethod
    def open_containing_folder(file_path):
        folder = os.path.dirname(file_path)
        if folder:
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    def show_warning(
        self,
        message,
    ):
        if self.iface is not None:
            self.iface.messageBar().pushMessage(
                "MapBiomas Alerta Oficial",
                message,
                level=Qgis.Warning,
                duration=8,
            )
        else:
            QMessageBox.warning(
                self,
                "MapBiomas Alerta Oficial",
                message,
            )

    def show_error(
        self,
        message,
    ):
        if self.iface is not None:
            self.iface.messageBar().pushMessage(
                "MapBiomas Alerta Oficial",
                message,
                level=Qgis.Critical,
                duration=10,
            )

        QMessageBox.critical(
            self,
            "MapBiomas Alerta Oficial",
            message,
        )

    def apply_styles(self):
        tooltip_palette = QPalette()
        tooltip_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#FFFFFF"))
        tooltip_palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#000000"))
        QToolTip.setPalette(tooltip_palette)
        self.setStyleSheet(
            """
            QDockWidget {
                background-color: #F5F6F5;
                color: #263238;
            }

            QDockWidget::title {
                background-color: #263238;
                color: white;
                padding: 8px;
                font-weight: bold;
            }

            #mainContainer,
            #scrollContent {
                background-color: #F5F6F5;
            }

            #headerFrame {
                background-color: white;
                border-bottom: 1px solid #D9DEDA;
            }

            #logoLabel {
                background-color: transparent;
                border: none;
            }

            #titleLabel {
                color: #832413;
                font-size: 16px;
                font-weight: 700;
            }

            QToolTip {
                background-color: #FFFFFF;
                color: #263238;
                border: 1px solid #BFC9C3;
                padding: 6px;
                font-weight: bold;
            }

            #subtitleLabel {
                color: #65716B;
                font-size: 10px;
            }

            #headerFrame #sectionButton {
                min-height: 30px;
                font-size: 12px;
            }

            #filtersScroll QScrollBar:vertical {
                background: #E1E6E3;
                width: 15px;
                margin: 2px;
                border-radius: 7px;
            }

            #filtersScroll QScrollBar::handle:vertical {
                background: #832413;
                min-height: 42px;
                border-radius: 6px;
            }

            #filtersScroll QScrollBar::handle:vertical:hover {
                background: #A43826;
            }

            #filtersScroll QScrollBar::add-line:vertical,
            #filtersScroll QScrollBar::sub-line:vertical {
                height: 0px;
            }

            #filtersScroll QScrollBar::add-page:vertical,
            #filtersScroll QScrollBar::sub-page:vertical {
                background: transparent;
            }

            #platformValueLabel {
                color: #832413;
                font-weight: 700;
            }

            QLabel {
                color: #34413B;
            }

            QComboBox,
            QLineEdit,
            QDateEdit,
            QDoubleSpinBox,
            QSpinBox {
                min-height: 35px;
                padding: 3px 8px;
                background-color: white;
                border: 1px solid #C8D0CB;
                border-radius: 5px;
                selection-background-color: #832413;
            }

            QComboBox:focus,
            QLineEdit:focus,
            QDateEdit:focus,
            QDoubleSpinBox:focus,
            QSpinBox:focus {
                border: 1px solid #832413;
            }

            QComboBox:disabled,
            QLineEdit:disabled,
            QDateEdit:disabled,
            QDoubleSpinBox:disabled,
            QSpinBox:disabled {
                background-color: #EEF0EE;
                color: #929B96;
            }

            QTabWidget::pane {
                border: none;
                background-color: #F5F6F5;
            }

            QTabBar::tab {
                background-color: #EBEEEC;
                color: #832413;
                padding: 7px 4px;
                border: none;
                border-bottom: 3px solid transparent;
            }

            QTabBar::tab:selected {
                background-color: white;
                color: #832413;
                border-bottom: 3px solid #832413;
            }

            #sectionCard {
                background-color: white;
                border: 1px solid #D7DDD9;
                border-radius: 6px;
            }

            #sectionContent {
                background-color: white;
            }

            #sectionButton {
                min-height: 42px;
                padding: 0 13px;
                background-color: white;
                color: #832413;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 700;
                text-align: left;
            }

            #sectionButton:hover {
                background-color: #F8F1F0;
            }

            QPushButton {
                min-height: 32px;
                padding: 4px 12px;
                background-color: white;
                color: #34413B;
                border: 1px solid #C8D0CB;
                border-radius: 5px;
            }

            QPushButton:hover {
                background-color: #F8F1F0;
                border-color: #832413;
            }

            QPushButton:disabled {
                background-color: #ECEFED;
                color: #9AA49E;
                border-color: #D7DDD9;
            }

            #searchButton {
                background-color: #832413;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 700;
            }

            #searchButton:hover {
                background-color: #9B2C1B;
            }

            #searchButton:pressed {
                background-color: #6F1E10;
                color: white;
            }

            #searchButton:disabled {
                background-color: #6F1E10;
                color: #F7EDEA;
                border: none;
            }

            #filterActionsFrame {
                background-color: white;
                border-top: 1px solid #D7DDD9;
            }

            #filterSummaryLabel {
                color: #59665F;
                font-size: 10px;
                font-weight: 600;
            }

            #clearFiltersButton {
                min-width: 76px;
                color: #832413;
                font-weight: 700;
            }

            QRadioButton {
                min-height: 30px;
                spacing: 8px;
            }

            QRadioButton::indicator {
                width: 17px;
                height: 17px;
                border-radius: 9px;
            }

            QRadioButton::indicator:unchecked {
                background-color: white;
                border: 1px solid #832413;
            }

            QRadioButton::indicator:checked {
                background-color: #832413;
                border: 4px solid white;
            }

            #coordinatesFrame {
                background-color: #FAFAFA;
                border: 1px solid #D7DDD9;
                border-radius: 5px;
            }

            #coordinatesTitle,
            #tabTitleLabel {
                color: #832413;
                font-weight: 700;
            }

            #tabTitleLabel {
                font-size: 12px;
            }

            #informationLabel {
                color: #77817C;
                font-size: 10px;
            }

            #emptyStateLabel {
                padding: 18px;
                color: #77837D;
                background-color: white;
                border: 1px dashed #C5CEC8;
                border-radius: 6px;
            }

            #sectionSummaryLabel {
                color: #59666b;
                font-size: 11px;
                padding-right: 10px;
                background: transparent;
            }

            QPushButton#linkButton {
                color: #832413;
                background: transparent;
                border: none;
                text-decoration: underline;
                font-weight: 600;
                padding: 2px 0;
            }

            QPushButton#chipButton {
                background: white;
                color: #24342b;
                border: 1px solid #C9C2B6;
                border-radius: 11px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: 400;
            }

            QPushButton#chipButton:hover {
                border-color: #832413;
                color: #832413;
            }

            QPushButton#outlineButton,
            QPushButton#dashedButton {
                background: white;
                color: #832413;
                border: 1px solid #832413;
                border-radius: 6px;
                padding: 5px 10px;
                font-weight: 700;
            }

            QPushButton#dashedButton {
                border-style: dashed;
            }

            QPushButton#outlineButton:disabled,
            QPushButton#dashedButton:disabled {
                color: #B8A9A5;
                border-color: #D8CDCA;
            }

            #statCard {
                background-color: white;
                border: 1px solid #D7DDD9;
                border-radius: 8px;
            }

            #statCardTitle {
                color: #59666b;
                font-size: 11px;
            }

            #statCardValue {
                color: #832413;
                font-size: 20px;
                font-weight: 700;
            }

            #statCardText {
                color: #24342b;
                font-size: 12px;
                font-weight: 700;
            }

            #resultValueLabel {
                color: #832413;
                font-size: 20px;
                font-weight: 700;
                padding-bottom: 8px;
            }

            #resultTextValueLabel {
                color: #832413;
                font-size: 13px;
                font-weight: 700;
                padding-bottom: 8px;
            }

            QScrollBar:vertical {
                background-color: #F1F2F1;
                width: 11px;
            }

            QScrollBar::handle:vertical {
                background-color: #B6BDB9;
                min-height: 25px;
                border-radius: 5px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #832413;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0;
            }
            """
        )
        for widget_type in (
            QComboBox, QLineEdit, QDateEdit, QDoubleSpinBox, QSpinBox
        ):
            for widget in self.findChildren(widget_type):
                widget.setMaximumWidth(620)
                widget.setMinimumWidth(0)
                widget.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
                if isinstance(widget, QComboBox):
                    widget.setSizeAdjustPolicy(
                        QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
                    )
                    widget.setMinimumContentsLength(8)

        for button in self.findChildren(QPushButton):
            button.setMinimumWidth(0)
            button.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)

        # Compact buttons keep their natural width (the generic loop
        # above makes every push button shrinkable to zero).
        for button_name in ("notice_shortcut_button", "expand_chart_button"):
            button = getattr(self, button_name, None)
            if button is not None:
                button.setSizePolicy(
                    QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
                )
                button.setMinimumWidth(button.sizeHint().width())
        for button in self.findChildren(QPushButton, "chipButton"):
            button.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
            )

        font = QFont()
        font.setPointSize(11)

        self.setFont(font)
        tab_font = QFont(font)
        tab_font.setPointSize(10)
        tab_font.setBold(True)
        self.tabs.tabBar().setFont(tab_font)
        self.tabs.tabBar().updateGeometry()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "responsive_forms"):
            self.update_responsive_layout()

    def update_responsive_layout(self):
        narrow = self.width() < 560
        very_narrow = self.width() < 390
        compact_height = self.height() < 850 or very_narrow

        row_policy = (
            QFormLayout.RowWrapPolicy.WrapAllRows
            if narrow
            else QFormLayout.RowWrapPolicy.DontWrapRows
        )
        for form in self.responsive_forms:
            form.setRowWrapPolicy(row_policy)
            form.setFieldGrowthPolicy(
                QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
            )
            form.invalidate()

        if hasattr(self, "login_form_widget"):
            self.login_form_widget.setMinimumHeight(0)
            self.login_form_widget.setMaximumHeight(16777215)
            self.login_form.activate()
            form_height = self.login_form.sizeHint().height()
            self.login_form_widget.setFixedHeight(form_height)
            self.login_form_widget.updateGeometry()

        direction = (
            QBoxLayout.Direction.TopToBottom
            if narrow
            else QBoxLayout.Direction.LeftToRight
        )
        for layout_name in (
            "details_images_layout",
        ):
            layout = getattr(self, layout_name, None)
            if layout is not None:
                layout.setDirection(direction)

        # The primary action must stay next to LIMPAR/CANCELAR even in
        # narrow docks, following the plugin's visual pattern.
        if hasattr(self, "filter_buttons_layout"):
            self.filter_buttons_layout.setDirection(QBoxLayout.Direction.LeftToRight)

        if hasattr(self, "login_buttons_layout"):
            self.login_buttons_layout.setDirection(
                QBoxLayout.Direction.LeftToRight
            )

        if hasattr(self, "login_button"):
            self.login_button.setText(
                self.tr("ENTRAR") if very_narrow else self.tr("ENTRAR NA API")
            )

        if hasattr(self, "area_grid"):
            self.layout_area_buttons(1 if self.width() < 400 else 2)

        # Navigation and export buttons stay side by side (2 x 2 grid
        # for exports) and the platform line stays on one line.
        for layout_name in (
            "detail_navigation_layout",
            "chart_export_layout",
            "vector_export_layout",
            "platform_layout",
        ):
            layout = getattr(self, layout_name, None)
            if layout is not None:
                layout.setDirection(QBoxLayout.Direction.LeftToRight)

        if hasattr(self, "remember_login_checkbox"):
            self.remember_login_checkbox.setText(
                self.tr("Salvar acesso")
                if very_narrow
                else (
                    self.tr("Salvar acesso no QGIS")
                    if narrow
                    else self.tr("Manter acesso salvo neste perfil do QGIS")
                )
            )

        if hasattr(self, "login_section"):
            content = self.login_section.content_widget
            content.setMinimumHeight(0)
            content.setMaximumHeight(16777215)
            self.login_section.setMinimumHeight(0)
            self.login_section.setMaximumHeight(16777215)
            self.login_section.content_layout.invalidate()
            self.login_section.content_layout.activate()
            if content.isVisible():
                content_height = (
                    self.login_section.content_layout.sizeHint().height()
                )
                content.setFixedHeight(content_height)
                self.login_section.setFixedHeight(
                    self.login_section.toggle_button.sizeHint().height()
                    + content_height
                )
            else:
                self.login_section.setFixedHeight(
                    self.login_section.toggle_button.sizeHint().height()
                )

        for widget_name in (
            "main_container",
            "header_frame",
            "login_section",
            "tabs",
        ):
            widget = getattr(self, widget_name, None)
            if widget is not None:
                widget.updateGeometry()

        if compact_height != self._compact_height:
            self._compact_height = compact_height
            if hasattr(self, "subtitle_label"):
                self.subtitle_label.setVisible(not compact_height)

        if hasattr(self, "header_frame"):
            self.header_frame.setMinimumHeight(0)
            self.header_frame.setMaximumHeight(16777215)
            self.header_frame.layout().invalidate()
            self.header_frame.layout().activate()
            if not self._responsive_geometry_pending:
                self._responsive_geometry_pending = True
                self._responsive_geometry_passes = 0
                QTimer.singleShot(
                    0, self.finalize_responsive_geometry
                )

    def finalize_responsive_geometry(self):
        """Syncs the header after Qt finishes its layout pass."""
        if not hasattr(self, "header_frame"):
            self._responsive_geometry_pending = False
            return
        self._responsive_geometry_passes += 1
        self.header_frame.setMinimumHeight(0)
        self.header_frame.setMaximumHeight(16777215)
        self.header_frame.layout().invalidate()
        self.header_frame.layout().activate()
        required_height = (
            self.header_frame.layout().sizeHint().height()
        )
        self.header_frame.setFixedHeight(required_height)
        self.header_frame.updateGeometry()
        if hasattr(self, "vertical_splitter"):
            remaining_height = max(
                120,
                self.vertical_splitter.height() - required_height,
            )
            self.vertical_splitter.setSizes(
                [required_height, remaining_height]
            )
        if hasattr(self, "main_container"):
            self.main_container.layout().invalidate()
            self.main_container.layout().activate()
        if self._responsive_geometry_passes < 3:
            QTimer.singleShot(0, self.finalize_responsive_geometry)
        else:
            self._responsive_geometry_pending = False

    def shutdown(self):
        if self._shutdown_complete:
            return
        self._shutdown_complete = True
        self.api_client.cancel_current_request()
        if (
            self.identify_tool is not None
            and self.iface is not None
            and self.iface.mapCanvas().mapTool() is self.identify_tool
        ):
            self.iface.mapCanvas().unsetMapTool(self.identify_tool)
        self.identify_tool = None
        self.related_alert_layer_id = None
        self.disconnect_project_signals()
        # Closing the panel keeps the searched layers on the map. Their
        # temporary GeoJSON files are only deleted when QGIS exits (atexit
        # in api_client), so the layers keep rendering. Before, closing
        # removed them — and the quick-view WMS layer, which wasn't
        # tracked, was the only one left behind.

    def closeEvent(
        self,
        event,
    ):
        self.shutdown()
        self.closing_plugin.emit()
        event.accept()


# Compatibility with the existing plugin.py.
MapBiomasAlertDock = MapBiomasAlertDockWidget
MainDialog = MapBiomasAlertDockWidget
MainDockWidget = MapBiomasAlertDockWidget
MapBiomasAlertaOficialDockWidget = (
    MapBiomasAlertDockWidget
)
