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
    # Settlements (INCRA), Legal Reserve and APP come from Brazil's
    # Forest Code / land reform — confirmed Brazil-only by the MapBiomas
    # Alerta team.
    "crossedSettlements",
    "crossedLegalReservesArea",
    "crossedPermanentProtectedArea",
    # Conservation Units (SNUC) and forest management plans: the API
    # counters are 0 in every other country (checked in the sandboxes of
    # Bolivia, Colombia, Peru and Indonesia) — protected areas there come
    # through alertIntersections under their own national categories.
    "crossedConservationUnits",
    "crossedForestManagementsArea",
)

# Brazilian crossings not offered in the plugin (crossing filter, charts,
# overlap summary): forest management, APP, Legal Reserve and geoparks
# (river sources are also hidden, see HIDDEN_INTERSECTION_HINTS).
HIDDEN_BRAZIL_CROSSING_FIELDS = (
    "crossedForestManagementsArea",
    "crossedPermanentProtectedArea",
    "crossedLegalReservesArea",
    "crossedGeoparks",
)

# Same categories in the alertIntersections mechanism: the Brazilian type
# keys weren't confirmed in the sandbox, so they're matched by these
# fragments of the type key or label (case-insensitive).
HIDDEN_INTERSECTION_HINTS = (
    "FOREST_MANAGEMENT", "MANEJO",
    "PERMANENT_PROTECT", "PRESERVACAO_PERMANENTE", "PRESERVAÇÃO PERMANENTE",
    "LEGAL_RESERVE", "RESERVA_LEGAL", "RESERVA LEGAL",
    "GEOPARK", "GEOPARQUE",
    "RIVER_SOURCE", "NASCENTE", "NACIENTE",
)

# Rural property registry: Brazil (CAR) and Colombia (cadastre) only,
# as confirmed by the MapBiomas Alerta team.
NO_RURAL_REGISTRY_CROSSING_FIELDS = (
    "ruralPropertiesTotal",
)

# Not Brazil-specific, but no API summary counter exists to confirm
# them elsewhere (see MapBiomasApiClient.CROSSING_AVAILABILITY_COUNTS).
# Restricted to Brazil until a verification method exists — neither
# shows up in the alertIntersections of the other countries either.
UNVERIFIABLE_CROSSING_FIELDS = (
    "crossedBiosphereReserves",
    "crossedGeoparks",
)

# Legacy crossed*/…List fields (layer columns) of the Brazil-only
# categories above. Outside Brazil they're not requested, so the layer
# doesn't carry columns that can only ever be empty there.
BRAZIL_ONLY_ANALYTIC_FIELDS = (
    # Outside Brazil indigenous territories come through the country's
    # own crossing types (Resguardo Indígena, Comunidad Nativa…); the
    # legacy field would repeat them under a Brazilian label.
    "crossedIndigenousLands",
    "crossedIndigenousLandsArea",
    "crossedIndigenousLandsList",
    "crossedConservationUnits",
    "crossedConservationUnitsArea",
    "crossedConservationUnitsList",
    "crossedSettlements",
    "crossedSettlementsArea",
    "crossedSettlementsList",
    "crossedQuilombos",
    "crossedQuilombosArea",
    "crossedQuilombosList",
    "crossedBiosphereReserves",
    "crossedBiosphereReservesArea",
    "crossedForestManagementsActivities",
    "crossedForestManagementsArea",
    "crossedForestManagementsList",
    "crossedFederalProtectedAreaIntegralProtections",
    "crossedFederalProtectedAreaIntegralProtectionsArea",
    "crossedFederalProtectedAreaSustainableUses",
    "crossedFederalProtectedAreaSustainableUsesArea",
    "crossedStateProtectedAreaIntegralProtections",
    "crossedStateProtectedAreaIntegralProtectionsArea",
    "crossedStateProtectedAreaSustainableUses",
    "crossedStateProtectedAreaSustainableUsesArea",
    "crossedMunicipalityProtectedAreaIntegralProtections",
    "crossedMunicipalityProtectedAreaIntegralProtectionsArea",
    "crossedMunicipalityProtectedAreaSustainableUses",
    "crossedMunicipalityProtectedAreaSustainableUsesArea",
    "crossedPermanentProtectedArea",
    "crossedPermanentProtectedAreaTotal",
    "crossedPermanentProtectedAreaList",
    "crossedLegalReservesArea",
    "crossedLegalReservesTotal",
    "crossedLegalReservesList",
    "crossedSpecialTerritories",
    "crossedSpecialTerritoriesArea",
    "crossedGeoparks",
    "crossedGeoparksArea",
)

NO_RURAL_REGISTRY_ANALYTIC_FIELDS = (
    "ruralPropertiesCodes",
    "ruralPropertiesTotal",
)

# Labels for the alertIntersections types of each country. The API's
# "name" field holds the data source (e.g. "IBC", "SERNANP", "ANA"),
# not a label, so the plugin needs its own. Terms are the ones used in
# each country and aren't translated with the panel language. Types
# confirmed in the sandbox of each country (sample of 300 alerts); an
# unknown type falls back to its own key.
# Territorial context types: they cross (nearly) every alert, so they're
# kept as crossings (filter, Details tab) but left out of the overlap
# summary count.
INTERSECTION_CONTEXT_TYPES = frozenset((
    "COUNTRY",
    "DEPARTMENT",
    "PROVINCE",
    "DISTRICT",
    "MUNICIPALITY",
    "REGION",
    "BIOME",
    "ECOREGION",
    "ECOZONE",
    "ISLAND",
    "WATERSHED",
    "WATERSHED_LEVEL_1",
    "WATERSHED_LEVEL_2",
    "WATERSHED_LEVEL_3",
    "WATERSHED_LEVEL_4",
))

INTERSECTION_LABELS_PE = {
    "COUNTRY": "País",
    "DEPARTMENT": "Departamento",
    "PROVINCE": "Provincia",
    "DISTRICT": "Distrito",
    "AMAZONIA_REGION": "Región Amazónica",
    "ECOZONE": "Ecozona",
    "WATERSHED_LEVEL_1": "Cuenca hidrográfica (nivel 1)",
    "WATERSHED_LEVEL_2": "Cuenca hidrográfica (nivel 2)",
    "WATERSHED_LEVEL_3": "Cuenca hidrográfica (nivel 3)",
    "WATERSHED_LEVEL_4": "Cuenca hidrográfica (nivel 4)",
    "NATURAL_PROTECTED_AREA": "Área Natural Protegida",
    "BUFFER_ZONE": "Zona de Amortiguamiento",
    "NATIVE_TITLED_COMMUNITY": "Comunidad Nativa Titulada",
    "TITLED_PEASANT_COMMUNITY": "Comunidad Campesina Titulada",
    "INDIGENOUS_RESERVE": "Reserva Indígena",
    "TITLE_OR_EXPANSION_REQUEST": "Solicitud de Titulación o Ampliación",
}
INTERSECTION_LABELS_BO = {
    "COUNTRY": "País",
    "DEPARTMENT": "Departamento",
    "MUNICIPALITY": "Municipio",
    "REGION": "Región",
    "BIOME": "Bioma",
    "ECOREGION": "Ecorregión",
    "NATIONAL_PROTECTED_AREA": "Área Protegida Nacional",
    "SUBNATIONAL_PROTECTED_AREA": "Área Protegida Subnacional",
    "INDIGENOUS_TERRITORY": "Territorio Indígena",
    "RAMSAR_SITE": "Sitio Ramsar",
}
INTERSECTION_LABELS_CO = {
    "COUNTRY": "País",
    "DEPARTMENT": "Departamento",
    "MUNICIPALITY": "Municipio",
    "REGION": "Región",
    "BIOME": "Bioma",
    "WATERSHED_LEVEL_1": "Cuenca hidrográfica (nivel 1)",
    "WATERSHED_LEVEL_2": "Cuenca hidrográfica (nivel 2)",
    "WATERSHED_LEVEL_3": "Cuenca hidrográfica (nivel 3)",
    "NATIONAL_NATURAL_PROTECTED_AREA": "Área Natural Protegida Nacional",
    "DEPARTMENTAL_NATURAL_PROTECTED_AREA": (
        "Área Natural Protegida Departamental"
    ),
    "INDIGENOUS_RESERVE": "Resguardo Indígena",
    "COMMUNITY_COUNCIL": "Consejo Comunitario",
    "FOREST_RESERVE": "Reserva Forestal",
    "PEASANT_RESERVE_ZONE": "Zona de Reserva Campesina",
    "RAMSAR_SITES": "Sitio Ramsar",
    "TPR": "Catastro Rural",
    "RAISG_LIMIT": "Límite Amazónico (RAISG)",
    "CHOCO_BIOGEOGRAPHIC": "Chocó Biogeográfico",
    "TROPICAL_DRY_FOREST": "Bosque Seco Tropical",
}
INTERSECTION_LABELS_ID = {
    "PROVINCE": "Province",
    "DISTRICT": "District",
    "ISLAND": "Island",
    "WATERSHED": "Watershed",
    "NATIONAL_PARK": "National Park",
    "FOREST_MORATORIUM": "Forest Moratorium Area",
    "KEY_BIODIVERSITY_AREA": "Key Biodiversity Area",
}

def intersection_group_fields(labels):
    """[(type, field, label)] for the crossing types that get their own
    layer columns (names, total area and per-territory areas), so charts
    can compare territories of each type. Context types (country,
    department, watersheds…) are left out, as in the overlap summary.
    Fields are numbered in table order (Cz01, Cz02…) to stay short and
    stable for Shapefile exports."""
    items = [
        (type_key, label) for type_key, label in (labels or {}).items()
        if type_key not in INTERSECTION_CONTEXT_TYPES
    ]
    return [
        (type_key, "Cz%02d" % (index + 1), label)
        for index, (type_key, label) in enumerate(items)
    ]


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
        # Left out of the crossing filter and the charts (decided with
        # the MapBiomas Alerta team).
        "crossing_fields_exclude": HIDDEN_BRAZIL_CROSSING_FIELDS,
        # Embargoes, authorizations and inspection actions are only
        # crossed in Brazil (none in the alertIntersections of the other
        # countries): the "check them in the report" note only shows here.
        "has_embargo_crossings": True,
        "analytic_fields_exclude": (),
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
            + NO_RURAL_REGISTRY_CROSSING_FIELDS
        ),
        "analytic_fields_exclude": (
            BRAZIL_ONLY_ANALYTIC_FIELDS
            + NO_RURAL_REGISTRY_ANALYTIC_FIELDS
        ),
        "intersection_labels": INTERSECTION_LABELS_BO,
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
        "analytic_fields_exclude": (
            BRAZIL_ONLY_ANALYTIC_FIELDS
        ),
        "intersection_labels": INTERSECTION_LABELS_CO,
        # Confirmed via Colombia's official data dictionary.
        "region_label": "Departamento",
        "municipality_label": "Município",
        # Cadastre-code search: the ruralProperty query takes Colombia's
        # 30-digit Número Predial Nacional (confirmed in the sandbox,
        # e.g. 851250001000000140014000000000). The layer is called
        # "Catastro Rural" there (label of the TPR intersection type).
        "has_rural_property_search": True,
        "rural_property_code_pattern": r"\d{30}",
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
            + NO_RURAL_REGISTRY_CROSSING_FIELDS
        ),
        "analytic_fields_exclude": (
            BRAZIL_ONLY_ANALYTIC_FIELDS
            + NO_RURAL_REGISTRY_ANALYTIC_FIELDS
        ),
        "intersection_labels": INTERSECTION_LABELS_PE,
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
            + NO_RURAL_REGISTRY_CROSSING_FIELDS
        ),
        "analytic_fields_exclude": (
            BRAZIL_ONLY_ANALYTIC_FIELDS
            + NO_RURAL_REGISTRY_ANALYTIC_FIELDS
        ),
        "intersection_labels": INTERSECTION_LABELS_ID,
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
