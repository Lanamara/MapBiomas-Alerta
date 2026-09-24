# -*- coding: utf-8 -*-

import os

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon

try:
    # Qt6: QAction lives in QtGui.
    from qgis.PyQt.QtGui import QAction
except ImportError:
    # Qt5: QAction lives in QtWidgets.
    from qgis.PyQt.QtWidgets import QAction

from .main_dialog import MapBiomasAlertDock


class MapBiomasAlertaOficialPlugin:
    def __init__(self, iface):
        self.iface = iface
        directory = os.path.dirname(os.path.abspath(__file__))
        self.icon_path = os.path.join(directory, "icon.png")
        self.plugin_name = "MapBiomas Alerta Oficial"
        self.action = None
        self.dock_widget = None

    def initGui(self):
        self.action = QAction(
            QIcon(self.icon_path),
            self.plugin_name,
            self.iface.mainWindow(),
        )
        self.action.setObjectName("MapBiomasAlertaOficialAction")
        self.action.setToolTip("Abrir o MapBiomas Alerta Oficial")
        self.action.setStatusTip(
            "Consultar e analisar alertas do MapBiomas no QGIS"
        )
        self.action.triggered.connect(self.run)
        self.iface.addPluginToMenu(self.plugin_name, self.action)
        self.iface.addToolBarIcon(self.action)

    def run(self):
        if self.dock_widget is None:
            self.dock_widget = MapBiomasAlertDock(self.iface)
            self.dock_widget.closing_plugin.connect(self.on_dock_closed)
            self.iface.addDockWidget(
                Qt.DockWidgetArea.RightDockWidgetArea, self.dock_widget
            )
        self.dock_widget.show()
        self.dock_widget.raise_()
        self.dock_widget.activateWindow()

    def on_dock_closed(self):
        if self.dock_widget is not None:
            self.dock_widget.deleteLater()
            self.dock_widget = None

    def unload(self):
        if self.dock_widget is not None:
            try:
                self.dock_widget.shutdown()
                self.iface.removeDockWidget(self.dock_widget)
                self.dock_widget.deleteLater()
            except (RuntimeError, AttributeError):
                pass
            self.dock_widget = None

        if self.action is None:
            return
        try:
            self.iface.removePluginMenu(self.plugin_name, self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action.triggered.disconnect(self.run)
            self.action.deleteLater()
        except (TypeError, RuntimeError, AttributeError):
            pass
        self.action = None
