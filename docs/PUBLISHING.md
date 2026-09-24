# Publishing a release

This document describes how to publish MapBiomas Alerta Oficial on GitHub and in the official QGIS Plugin Repository (https://plugins.qgis.org), so users can install it directly from **Plugins › Manage and Install Plugins…**.

## 1. Requirements checklist

The QGIS Plugin Repository approves plugins that meet the rules below. This repository already complies with all of them:

| Requirement | Where |
|---|---|
| Metadata with name, qgisMinimumVersion, description, about, version, author, email | `mapbiomas_alerta_oficial/metadata.txt` |
| Links to a public code repository, issue tracker and homepage | `repository`, `tracker`, `homepage` in `metadata.txt` |
| GPLv2-or-later compatible license, included in the package | `LICENSE` and `mapbiomas_alerta_oficial/LICENSE.txt` |
| English description and minimal documentation | `metadata.txt`, `README.md`, `docs/user-guides/` |
| Version in dotted notation | `version=1.0.0` |
| No binaries, no `__pycache__`, `.git` or hidden folders in the ZIP | enforced by `scripts/package_plugin.py` |
| Package smaller than 20 MB, single top-level folder | enforced by `scripts/package_plugin.py` (about 0.2 MB) |
| Name and folder without the word "plugin" | `MapBiomas Alerta Oficial` / `mapbiomas_alerta_oficial` |
| Cross-platform, network access through QGIS classes | Python only; uses `QgsBlockingNetworkRequest` |
| QGIS 4 compatibility flag | `qgisMaximumVersion=4.99` |
| Same code in the repository and in the ZIP | the ZIP is built from `mapbiomas_alerta_oficial/` |

## 2. Publish the source code on GitHub

The metadata points to `https://github.com/mapbiomas/alert_QGIS_plugin`. The repository must exist and be **public** before uploading to plugins.qgis.org. If a different address is used, update `repository`, `tracker` and `homepage` in `metadata.txt` and the links in `README.md`.

With Git installed:

```bash
git clone https://github.com/mapbiomas/alert_QGIS_plugin.git
# copy the contents of this folder into the cloned folder, then:
cd alert_QGIS_plugin
git add .
git commit -m "Release 1.0.0"
git push origin main
git tag v1.0.0
git push origin v1.0.0
```

Without Git: on the repository page, use **Add file › Upload files**, drag every file and folder of this package (keep the folder structure), write a commit message and click **Commit changes**. Then create the tag in **Releases › Draft a new release › Choose a tag › v1.0.0**.

When the `v1.0.0` tag is pushed, the **Check and package** workflow (`.github/workflows/package.yml`) runs the checks, builds `mapbiomas_alerta_oficial.1.0.0.zip` and attaches it to the GitHub release. The workflow needs **Settings › Actions › General › Workflow permissions** set to **Read and write permissions**.

## 3. Build the ZIP locally (optional)

```bash
python scripts/package_plugin.py
```

The file is written to `dist/mapbiomas_alerta_oficial.<version>.zip`. It is the same file the GitHub workflow produces.

## 4. Upload to plugins.qgis.org

1. Create an **OSGeo ID** (free) at https://www.osgeo.org/community/getting-started-osgeo/osgeo_userid/ if you don't have one. It is the login for plugins.qgis.org.
2. Sign in at https://plugins.qgis.org with the OSGeo ID.
3. Open **Upload a plugin** (https://plugins.qgis.org/plugins/add/).
4. Select `mapbiomas_alerta_oficial.1.0.0.zip` and submit.
5. The site validates the metadata and runs an automatic security scan. Fix any reported issue and upload again if needed.
6. The first version of a new plugin is reviewed by volunteer approvers. This usually takes from a few hours to a few days.
7. After approval, the plugin appears for everyone in **Plugins › Manage and Install Plugins… › All**.

Tip: once the plugin page exists on plugins.qgis.org, add the other maintainers (for example, a second MapBiomas account) as owners of the plugin, so more than one person can publish updates.

## 5. Publishing a new version

1. Update `version` and `changelog` in `mapbiomas_alerta_oficial/metadata.txt` (for example, `1.0.1`). The version must always increase.
2. Add the changes to `CHANGELOG.md`.
3. Commit, push and create the tag `v<version>` (the workflow builds the ZIP).
4. On plugins.qgis.org, open the plugin page, click **Add version** and upload the new ZIP. The new version goes through the same security scan and, depending on the account's permissions, may wait for approval again.
5. Users are notified by QGIS and can update under **Plugins › Manage and Install Plugins… › Upgradeable**.

## 6. Testing a package before publishing

In QGIS, use **Plugins › Manage and Install Plugins… › Install from ZIP** with the file from `dist/`. If an older test copy installed from a ZIP with a different folder name (for example `mapbiomas_alert_analytics`) is present, uninstall it first under **Installed**, so the two copies don't run side by side.
