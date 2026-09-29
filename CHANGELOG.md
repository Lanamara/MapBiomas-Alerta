# Changelog

All notable changes to this project are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed
- Rural property search follows the current API: `ruralProperty(propertyCode: ...)` instead of `carCode`, and `propertyType`/`stateAcronym` instead of the deprecated `carType`/`state` (older APIs are still detected and supported).
- Alert download by rural property uses the `propertyCodes` argument of `alerts` (`carCodes` was removed from the API).
- Summary query no longer sends `isInEmbargoedArea`, removed from the API in May 2026.
- Biome, state and municipality no longer depend on the deprecated `crossedBiomes`/`crossedStates`/`crossedCities` fields: they are requested only while the API still has them, and otherwise rebuilt from `alertIntersections` (search, summary and alert details).
- Indonesia: the region level is labelled "Província" (Provincia/Province), following the API docs.
- Detection sources whose enum name differs between the API docs and the platform (`ProdesAmz`/`ProdesAmazonia`, `ProdesCerr`/`ProdesCerrado`, `Siradx`/`SiradX`) show their friendly label either way.

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
