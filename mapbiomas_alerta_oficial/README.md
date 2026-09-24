# MapBiomas Alerta Oficial

Official QGIS plugin of MapBiomas Alerta. It uses the MapBiomas Alerta GraphQL API (v2) to search, analyze and export validated deforestation alerts for Brazil, Bolivia, Colombia, Peru and Indonesia, with an interface in Portuguese, Spanish and English.

## Requirements

- QGIS 3.22 or later (QGIS 4 compatible).
- Internet access.
- An account on the MapBiomas Alerta platform of the country you want to query.

## Usage

1. Open the panel from the toolbar icon or **Plugins › MapBiomas Alerta Oficial**.
2. Accept the country's information notice.
3. Choose the country and language, then sign in under **API access**.
4. In **Filters**, choose the area of interest (whole country, biome, vector layer, coordinate, alert code or, in Brazil, CAR code) and the period, then click **Search alerts**.
5. Explore the results in **Statistics**, **Charts** and **Details**, and export them from **Statistics**, **Charts** or **Layers**.

## Files

| File | Purpose |
|---|---|
| `__init__.py` | QGIS entry point (`classFactory`). |
| `plugin.py` | Toolbar icon, menu entry and dock creation. |
| `main_dialog.py` | Dock panel: filters, search, statistics, charts, details and exports. |
| `api_client.py` | MapBiomas Alerta GraphQL API client (authentication, queries, pagination). |
| `country_config.py` | Per-country endpoints, sources and labels. |
| `translations.py` | Spanish and English translations of the interface (Portuguese is the source language). |
| `notices.py` | Information notice shown for each country. |

## Documentation and support

- Source code, user guides and issue tracker: https://github.com/mapbiomas/alert_QGIS_plugin
- Support: suporte.alerta@mapbiomas.org

## License

GNU General Public License v2.0 or later. See `LICENSE.txt`.
