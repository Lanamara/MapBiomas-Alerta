# -*- coding: utf-8 -*-
"""Catalog of countries and services used by the plugin.

A country should only be marked enabled once its endpoint and attribute
schema have been verified. This lets the UI track MapBiomas Alerta's
expansion without scattering conditionals through the code.
"""

# Fields that are Brazil-specific *by definition* — terms from
# Brazilian law and public administration with no equivalent elsewhere
# (quilombola is a category under Brazilian law; the federal/state/
# municipal protection split comes from SNUC; "Amazônia Legal" and
# "MATOPIBA" are Brazilian government-defined regions). No live
# verification is needed since these are impossible elsewhere by
# construction, not just unlikely. The GraphQL schema itself can't be
# used to detect this (it's identical across countries), so this list
# must stay explicit. For everything else, availability is checked
# against real data via MapBiomasApiClient.crossing_availability()
# (API summary counters, e.g. conservationUnitsCount) rather than
# guessed from the schema.
BRAZIL_ONLY_CROSSING_FIELDS = (
    "crossedQuilombos",
    "crossedFederalProtectedAreaIntegralProtections",
    "crossedFederalProtectedAreaSustainableUses",
    "crossedStateProtectedAreaIntegralProtections",
    "crossedStateProtectedAreaSustainableUses",
    "crossedMunicipalityProtectedAreaIntegralProtections",
    "crossedMunicipalityProtectedAreaSustainableUses",
    "crossedSpecialTerritories",
)

# Not Brazil-specific, but no API summary counter exists to confirm
# them elsewhere (see MapBiomasApiClient.CROSSING_AVAILABILITY_COUNTS).
# Restricted to Brazil until a verification method exists.
UNVERIFIABLE_CROSSING_FIELDS = (
    "crossedBiosphereReserves",
)

COMMON_FIELDS = {
    "alert_code": "CodeAlerta",
    "source": "Fonte",
    "biome": "Bioma",
    "region": "Estado",
    "municipality": "Municipio",
    "area": "AreaHa",
    "detection_year": "AnoDetec",
    "detection_date": "DataDetec",
    "publication_date": "PubImg",
    "geometry": "geom",
}

COUNTRIES = {
    "BR": {
        "name": "Brasil",
        "platform": "MapBiomas Alerta Brasil",
        "platform_url": "https://plataforma.alerta.mapbiomas.org/",
        "enabled": True,
        "api_url": "https://plataforma.alerta.mapbiomas.org/api/v2/graphql",
        "api_crs": "EPSG:4326",
        # Empty = nothing excluded; every category in
        # MapBiomasApiClient.CROSSING_OPTIONS is available (already
        # confirmed against Brazil's API during development).
        "crossing_fields_exclude": (),
        # UI labels for the two administrative levels the API always
        # returns (internal fields "Estado"/"Municipio", which don't
        # change name — only the text shown to the user varies by
        # country).
        "region_label": "Estado",
        "municipality_label": "Município",
        # Not every country has a rural property registry integrated
        # with the platform — see the note under "CO" below about the
        # CAR/cadastre search.
        "has_rural_property_search": True,
        # Quick view: published alerts rendered by the platform's
        # GeoServer (WMS), with no polygon download. Only Brazil has a
        # published (non-staging) layer there; other countries leave these
        # keys out and the option stays hidden.
        "wms_url": "https://maps.alerta.mapbiomas.org/geoserver/wms",
        # Candidates in order of preference, with whether each one has a
        # "biome" attribute for filtering. The plugin checks the server's
        # GetCapabilities and uses the first one actually published.
        "wms_layers": (
            ("mapbiomas-alertas:mv_qgis_published_alerts_snap_to_grid", True),
            ("mapbiomas-alertas:dashboard-alerts", False),
        ),
        # Approximate extent (EPSG:4326) to frame the quick view.
        "extent": (-74.0, -34.0, -34.5, 5.5),
        "sources": (
            ("DeterbAmazonia", "DETERB Amazônia"),
            ("DeterCerrado", "DETER Cerrado"),
            ("DeterPantanal", "DETER Pantanal"),
            ("Glad", "GLAD"),
            ("IefMg", "IEF-MG"),
            ("InemaBa", "INEMA-BA"),
            ("ProdesAmazonia", "PRODES Amazônia"),
            ("ProdesCerrado", "PRODES Cerrado"),
            ("ProdesMataAtlantica", "PRODES Mata Atlântica"),
            ("ProdesPampa", "PRODES Pampa"),
            ("ProdesPantanal", "PRODES Pantanal"),
            ("ProdesCaatinga", "PRODES Caatinga"),
            ("Sad", "SAD"),
            ("SadCaatinga", "SAD Caatinga"),
            ("SadCerrado", "SAD Cerrado"),
            ("SadMataAtlantica", "SAD Mata Atlântica"),
            ("SadPampa", "SAD Pampa"),
            ("SadPantanal", "SAD Pantanal"),
            ("SipamSar", "SIPAM-SAR"),
            ("SiradX", "SIRAD X"),
            ("SosAtlas", "SOS Atlas"),
            ("SosInpe", "SOS/INPE"),
        ),
        "fields": COMMON_FIELDS,
    },
    "BO": {
        "name": "Bolívia",
        "platform": "MapBiomas Alerta Bolívia",
        "platform_url": "https://plataforma.bolivia.alerta.mapbiomas.org/",
        "enabled": True,
        "api_url": "https://plataforma.bolivia.alerta.mapbiomas.org/api/v2/graphql",
        "api_crs": "EPSG:4326",
        # Excludes Brazil-only and unverifiable fields; everything else
        # is discovered via introspection.
        "crossing_fields_exclude": (
            BRAZIL_ONLY_CROSSING_FIELDS + UNVERIFIABLE_CROSSING_FIELDS
        ),
        # Confirmed via Bolivia's official data dictionary.
        "region_label": "Departamento",
        "municipality_label": "Município",
        # No rural property registry integrated with Bolivia's platform.
        "has_rural_property_search": False,
        "sources": (
            ("Fan", "FAN"),
            ("Glad", "GLAD"),
        ),
        "fields": COMMON_FIELDS,
    },
    "CO": {
        "name": "Colômbia",
        "platform": "MapBiomas Alerta Colômbia",
        "platform_url": "https://plataforma.colombia.alerta.mapbiomas.org/",
        "enabled": True,
        "api_url": "https://plataforma.colombia.alerta.mapbiomas.org/api/v2/graphql",
        "api_crs": "EPSG:4326",
        # Same logic as "BO" above.
        "crossing_fields_exclude": (
            BRAZIL_ONLY_CROSSING_FIELDS + UNVERIFIABLE_CROSSING_FIELDS
        ),
        # Confirmed via Colombia's official data dictionary.
        "region_label": "Departamento",
        "municipality_label": "Município",
        # Cadastre-code search (ruralProperty query) is not equivalent
        # to Brazil's here — disabled until confirmed.
        "has_rural_property_search": False,
        "sources": (
            ("Dist", "DIST"),
            ("Gaia", "GAIA"),
            ("GladL", "GLAD-L"),
            ("GladS", "GLAD-S"),
            ("Ideam", "IDEAM"),
            ("JjFast", "JJ-FAST"),
            ("Luca", "LUCA"),
            ("Radd", "RADD"),
        ),
        "fields": COMMON_FIELDS,
    },
    "PE": {
        "name": "Peru",
        "platform": "MapBiomas Alerta Peru",
        "platform_url": "https://plataforma.peru.alerta.mapbiomas.org/",
        "enabled": True,
        "api_url": "https://plataforma.peru.alerta.mapbiomas.org/api/v2/graphql",
        "api_crs": "EPSG:4326",
        # Same logic as "BO"/"CO" above.
        "crossing_fields_exclude": (
            BRAZIL_ONLY_CROSSING_FIELDS + UNVERIFIABLE_CROSSING_FIELDS
        ),
        # "Departamento" confirmed; the sub-level ("Município") is an
        # approximation — Peru has Provincia and Distrito below it and
        # it's unclear which the API field actually fills.
        "region_label": "Departamento",
        "municipality_label": "Município",
        "has_rural_property_search": False,
        "sources": (
            ("Geobosque", "GEOBOSQUE"),
            ("Glad", "GLAD"),
        ),
        "fields": COMMON_FIELDS,
    },
    "ID": {
        "name": "Indonésia",
        "platform": "MapBiomas Alerta Indonésia",
        "platform_url": "https://platform.idn.alerta.mapbiomas.org/",
        "enabled": True,
        "api_url": "https://platform.idn.alerta.mapbiomas.org/api/v2/graphql",
        "api_crs": "EPSG:4326",
        # Same logic as "BO"/"CO" above.
        "crossing_fields_exclude": (
            BRAZIL_ONLY_CROSSING_FIELDS + UNVERIFIABLE_CROSSING_FIELDS
        ),
        # Administrative division unconfirmed for Indonesia — default
        # labels kept rather than risk the wrong term.
        "region_label": "Estado",
        "municipality_label": "Município",
        "has_rural_property_search": False,
        "sources": (
            ("Glad", "GLAD"),
        ),
        "fields": COMMON_FIELDS,
    },
}


def country_items():
    """Return countries in the order shown in the UI."""
    return tuple(COUNTRIES.items())


def country_config(code):
    """Return a defensively copied config for the given country code."""
    source = COUNTRIES.get(code)
    if source is None:
        raise ValueError("Unrecognized country: {}".format(code))

    config = dict(source)
    if "fields" in source:
        config["fields"] = dict(source["fields"])
    config["code"] = code
    return config
