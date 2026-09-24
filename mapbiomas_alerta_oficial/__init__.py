# -*- coding: utf-8 -*-
"""Plugin entry point for MapBiomas Alerta Oficial."""


def classFactory(iface):
    """Create the plugin's main instance for QGIS."""

    from .plugin import MapBiomasAlertaOficialPlugin

    return MapBiomasAlertaOficialPlugin(iface)
