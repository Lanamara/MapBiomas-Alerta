# Contributing

Thank you for helping improve MapBiomas Alerta Oficial.

## Reporting problems

Open an issue using the **Bug report** template. Include the plugin and QGIS versions, the country, the filters used and, if possible, a screenshot of the panel and of the QGIS log (**View › Panels › Log Messages**, tab "MapBiomas Alerta Oficial").

## Development setup

1. Clone the repository.
2. Link or copy the `mapbiomas_alerta_oficial` folder into your QGIS profile plugins folder:
   - Windows: `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`
   - Linux: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
   - macOS: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
3. Restart QGIS and enable the plugin under **Plugins › Manage and Install Plugins… › Installed**. The [Plugin Reloader](https://plugins.qgis.org/plugins/plugin_reloader/) plugin helps while editing.

## Code guidelines

- Code, comments, docstrings, log messages and repository documentation are written in **English**.
- Interface texts are written in Portuguese in the code and wrapped in `self.tr(...)`; add the Spanish and English versions to `translations.py`.
- Keep Qt5/Qt6 compatibility (QGIS 3 and 4): use scoped enums such as `Qt.AlignmentFlag.AlignCenter`.
- Use QGIS network classes (`QgsBlockingNetworkRequest`, `QgsNetworkAccessManager`) instead of `requests` or `urllib`.
- Do not add binaries or generated files to the plugin folder.
- Country-specific settings belong in `country_config.py`, not in scattered conditionals.

## Before opening a pull request

```bash
pip install pyflakes bandit
python -m pyflakes mapbiomas_alerta_oficial scripts
python -m bandit -q -r mapbiomas_alerta_oficial scripts
python scripts/package_plugin.py
```

All three commands must finish without errors. The same checks run automatically on GitHub for every push and pull request.
