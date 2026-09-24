# Changelog

All notable changes to this project are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-09

First public release in the QGIS Plugin Repository.

### Added
- Support for Brazil, Bolivia, Colombia, Peru and Indonesia, each with its own API endpoint, detection sources, labels and information notice.
- Interface in Portuguese, Spanish and English, including exported file names.
- Areas of interest: whole country, biome, vector layer, coordinate, alert code and rural property CAR code (Brazil only).
- Filters: detection or publication period (up to one year), quick date ranges, minimum area, detection sources with matching rule, and territorial/environmental crossings.
- Search progress bar with cancel button; official summary shown before the download finishes.
- Summary cards: total alerts, deforested area, daily average, largest/smallest alert, highest speed, municipality with the largest area, overlaps and analyzed period.
- Statistical analysis with bar, pie and line charts, count/sum/average, specific value, category limit and an enlarged chart window.
- Alert details: metadata, crossings, crossed rural properties, other alerts on the same property, before/after satellite images and link to the platform report.
- Exports: attribute table (CSV, XLSX), layer (GeoPackage, Shapefile), chart (PNG), chart alerts (CSV, GeoPackage, Shapefile, including the compared field) and summary (XLSX).
- Result layers named after the area of interest and period, e.g. `Alertas - Cerrado, 01/01/2025 a 30/07/2025` (Portuguese interface).
- Step-by-step user guides for each country.
