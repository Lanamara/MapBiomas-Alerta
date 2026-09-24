# -*- coding: utf-8 -*-
"""MapBiomas Alerta GraphQL v2 API client."""

import json
import re
import os
import tempfile
import atexit
import time
from datetime import datetime

from qgis.PyQt.QtCore import QEventLoop, QTimer, QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest
from qgis.core import Qgis, QgsGeometry, QgsMessageLog, QgsNetworkAccessManager


class ApiAuthenticationError(RuntimeError):
    pass


class QueryCancelledError(RuntimeError):
    pass


class MapBiomasApiClient:
    PERIOD_DETECTION = "detection"
    PERIOD_PUBLICATION = "publication"
    TIMEOUT_MILLISECONDS = 120000
    IMAGE_TIMEOUT_MILLISECONDS = 30000
    # Initial page size. This does not cap the total amount: ``download_alerts``
    # keeps paginating until it receives exactly the ``metadata.totalCount``
    # reported by the API.
    PAGE_SIZE = 1000
    # Pages requested at the same time once the first page has told us the
    # total. Kept low on purpose so the API isn't flooded (HTTP 429).
    PARALLEL_PAGES = 3
    ANALYTIC_FIELDS = {
        "crossedBiomesArea": ("BiomaAreaHa", True),
        "crossedStatesArea": ("EstadoAreaHa", True),
        "crossedCitiesArea": ("MunicAreaHa", True),
        "crossedConservationUnits": ("UnidConserv", False),
        "crossedConservationUnitsArea": ("UCAreaHa", True),
        "crossedIndigenousLands": ("TerraIndig", False),
        "crossedIndigenousLandsArea": ("TIAreaHa", True),
        "crossedSettlements": ("Assentamento", False),
        "crossedSettlementsArea": ("AssentArea", True),
        "crossedQuilombos": ("Quilombo", False),
        "crossedQuilombosArea": ("QuilombArea", True),
        "crossedBiosphereReserves": ("ReservaBio", False),
        "crossedBiosphereReservesArea": ("ResBioArea", True),
        "crossedForestManagementsActivities": ("ManFlorest", False),
        "crossedForestManagementsArea": ("ManFlorArea", True),
        "crossedFederalProtectedAreaIntegralProtections": ("ProtIntegral", False),
        "crossedFederalProtectedAreaIntegralProtectionsArea": ("ProtIntArea", True),
        "crossedFederalProtectedAreaSustainableUses": ("UsoSustent", False),
        "crossedFederalProtectedAreaSustainableUsesArea": ("UsoSustArea", True),
        "crossedPermanentProtectedArea": ("APPAreaHa", True),
        "crossedPermanentProtectedAreaTotal": ("APPQtd", True),
        "crossedLegalReservesArea": ("RLAreaHa", True),
        "crossedLegalReservesTotal": ("RLQtd", True),
        "crossedSpecialTerritories": ("TerrEspecial", False),
        "crossedSpecialTerritoriesArea": ("TerrEspArea", True),
        "ruralPropertiesCodes": ("ImovelCod", False),
        "ruralPropertiesTotal": ("ImovelQtd", True),
        "crossedGeoparks": ("Geoparque", False),
        "crossedGeoparksArea": ("GeoparqueArea", True),
        "crossedMunicipalityProtectedAreaIntegralProtections": (
            "ProtMunIntegral", False,
        ),
        "crossedMunicipalityProtectedAreaIntegralProtectionsArea": (
            "ProtMunIntArea", True,
        ),
        "crossedMunicipalityProtectedAreaSustainableUses": (
            "UsoMunSust", False,
        ),
        "crossedMunicipalityProtectedAreaSustainableUsesArea": (
            "UsoMunSustArea", True,
        ),
        "crossedStateProtectedAreaIntegralProtections": (
            "ProtEstIntegral", False,
        ),
        "crossedStateProtectedAreaIntegralProtectionsArea": (
            "ProtEstIntArea", True,
        ),
        "crossedStateProtectedAreaSustainableUses": ("UsoEstSust", False),
        "crossedStateProtectedAreaSustainableUsesArea": (
            "UsoEstSustArea", True,
        ),
    }
    AREA_MAP_FIELDS = {
        "crossedForestManagementsList": ("ManFlorest", "ManFlorestAreas"),
        "crossedPermanentProtectedAreaList": ("APP", "APPAreas"),
        "crossedLegalReservesList": ("ReservaLegal", "RLAreas"),
        # These 4 fields exist in the schema but aren't publicly documented;
        # supported_analytic_fields() filters via live introspection, so a
        # nonexistent name is simply ignored, with no risk of breaking the query.
        "crossedIndigenousLandsList": ("TerraIndig", "TerraIndigAreas"),
        "crossedSettlementsList": ("Assentamento", "AssentamentoAreas"),
        "crossedQuilombosList": ("Quilombo", "QuilomboAreas"),
        "crossedConservationUnitsList": ("UnidConserv", "UnidConservAreas"),
        # Biosphere Reserve and Geopark have no "...List" variant in the
        # schema (only crossedBiosphereReserves/Area/Ids and
        # crossedGeoparks/Area/Ids exist) — so they get no per-territory
        # area breakdown when an alert crosses more than one.
    }
    # Per the platform itself (a note shown on the alert report), the
    # crossing list counts each declaration's area individually, WITHOUT
    # removing overlaps between different declarations — so the sum of
    # individual values for Conservation Unit/Indigenous Land/Settlement/
    # Quilombo/Biosphere Reserve/Geopark/Permanent Protected Area/Legal
    # Reserve can legitimately EXCEED the aggregate total when the crossed
    # territories overlap each other. That's why the consistency check
    # below (AREA_MAP_AUTHORITATIVE_TOTALS) is just an informational log
    # warning — it never discards the individual values, which keep being
    # shown normally even when the sum diverges.
    #
    # The API doesn't expose a list with each Conservation Unit's
    # individual area (unlike Biome/State/City). But each Conservation
    # Unit also appears, separately, in one of the 6 sublayers below
    # (integral protection x sustainable use, per federal/state/municipal
    # sphere — SNUC classification). When each sublayer resolves to
    # exactly 1 name, the per-unit breakdown can be reconstructed by
    # crossing those 6 sublayers. Used only as a fallback when
    # crossedConservationUnitsList (above) isn't available — see
    # reconcile_conservation_unit_areas().
    CONSERVATION_UNIT_SUBLAYERS = (
        (
            "crossedFederalProtectedAreaIntegralProtections",
            "crossedFederalProtectedAreaIntegralProtectionsArea",
        ),
        (
            "crossedFederalProtectedAreaSustainableUses",
            "crossedFederalProtectedAreaSustainableUsesArea",
        ),
        (
            "crossedStateProtectedAreaIntegralProtections",
            "crossedStateProtectedAreaIntegralProtectionsArea",
        ),
        (
            "crossedStateProtectedAreaSustainableUses",
            "crossedStateProtectedAreaSustainableUsesArea",
        ),
        (
            "crossedMunicipalityProtectedAreaIntegralProtections",
            "crossedMunicipalityProtectedAreaIntegralProtectionsArea",
        ),
        (
            "crossedMunicipalityProtectedAreaSustainableUses",
            "crossedMunicipalityProtectedAreaSustainableUsesArea",
        ),
    )
    # Of the keys above, only these have an equivalent total-area (Float)
    # field in the API schema to check against. crossedForestManagementsList
    # is of type [String!] — names only, no per-item area — so it never
    # produces an area map (the parser requires name+area pairs in an object).
    AREA_MAP_AUTHORITATIVE_TOTALS = {
        "crossedPermanentProtectedAreaList": "crossedPermanentProtectedArea",
        "crossedLegalReservesList": "crossedLegalReservesArea",
        "crossedIndigenousLandsList": "crossedIndigenousLandsArea",
        "crossedSettlementsList": "crossedSettlementsArea",
        "crossedQuilombosList": "crossedQuilombosArea",
        "crossedConservationUnitsList": "crossedConservationUnitsArea",
    }
    TERRITORY_AREA_PAIRS = {
        "Bioma": ("BiomaAreaHa", "BiomaAreas"),
        "Estado": ("EstadoAreaHa", "EstadoAreas"),
        "Municipio": ("MunicAreaHa", "MunicAreas"),
        "UnidConserv": ("UCAreaHa", "UnidConservAreas"),
        "TerraIndig": ("TIAreaHa", "TerraIndigAreas"),
        "Assentamento": ("AssentArea", "AssentamentoAreas"),
        "Quilombo": ("QuilombArea", "QuilomboAreas"),
        "ReservaBio": ("ResBioArea", "ReservaBioAreas"),
        "ManFlorest": ("ManFlorArea", "ManFlorestAreas"),
        "ProtIntegral": ("ProtIntArea", "ProtIntegralAreas"),
        "UsoSustent": ("UsoSustArea", "UsoSustentAreas"),
        "APP": ("APPAreaHa", "APPAreas"),
        "ReservaLegal": ("RLAreaHa", "RLAreas"),
        "TerrEspecial": ("TerrEspArea", "TerrEspecialAreas"),
        "Geoparque": ("GeoparqueArea", "GeoparqueAreas"),
        "ProtMunIntegral": ("ProtMunIntArea", "ProtMunIntegralAreas"),
        "UsoMunSust": ("UsoMunSustArea", "UsoMunSustAreas"),
        "ProtEstIntegral": ("ProtEstIntArea", "ProtEstIntegralAreas"),
        "UsoEstSust": ("UsoEstSustArea", "UsoEstSustAreas"),
    }
    CROSSING_OPTIONS = (
        ("crossedConservationUnits", "Unidades de Conservação (todas)"),
        (
            "crossedFederalProtectedAreaIntegralProtections",
            "Proteção integral federal",
        ),
        (
            "crossedFederalProtectedAreaSustainableUses",
            "Uso sustentável federal",
        ),
        (
            "crossedStateProtectedAreaIntegralProtections",
            "Proteção integral estadual",
        ),
        (
            "crossedStateProtectedAreaSustainableUses",
            "Uso sustentável estadual",
        ),
        (
            "crossedMunicipalityProtectedAreaIntegralProtections",
            "Proteção integral municipal",
        ),
        (
            "crossedMunicipalityProtectedAreaSustainableUses",
            "Uso sustentável municipal",
        ),
        ("crossedIndigenousLands", "Terras Indígenas"),
        ("crossedSettlements", "Assentamentos"),
        ("crossedQuilombos", "Territórios quilombolas"),
        ("crossedBiosphereReserves", "Reservas da Biosfera"),
        ("crossedForestManagementsArea", "Manejo florestal"),
        ("crossedPermanentProtectedArea", "APP"),
        ("crossedLegalReservesArea", "Reserva Legal"),
        ("crossedSpecialTerritories", "Territórios especiais"),
        ("ruralPropertiesTotal", "Imóveis rurais"),
    )

    # Counters from the API's statistical summary (QuerySummary) used to
    # confirm, with real data, whether the currently connected country
    # actually has alerts crossing that category — unlike schema
    # introspection (supported_analytic_fields), which only confirms the
    # field NAME exists (the schema is the same for all countries; a
    # counter at zero is a real sign of no data, not a query limitation).
    # Not every CROSSING_OPTIONS category has a matching counter — the
    # ones that don't (Biosphere Reserves, Quilombola, SNUC subdivisions,
    # Special Territory) are left out of the automatic check and handled
    # separately in country_config.py.
    CROSSING_AVAILABILITY_COUNTS = {
        "conservationUnitsCount": "crossedConservationUnits",
        "indigenousLandCount": "crossedIndigenousLands",
        "settlementsCount": "crossedSettlements",
        "ruralPropertiesCount": "ruralPropertiesTotal",
        "forestManagementsCount": "crossedForestManagementsArea",
        "legalReservesCount": "crossedLegalReservesArea",
        "permanentProtectedAreasCount": "crossedPermanentProtectedArea",
    }

    # Superset of CROSSING_AVAILABILITY_COUNTS: every count field in
    # QuerySummary that ALERTS_SUMMARY_QUERY used to request
    # unconditionally before this fix. actionsCount/riverSourcesCount
    # aren't crossing categories (not in
    # CROSSING_AVAILABILITY_COUNTS), but are likewise counters that may
    # not exist outside Brazil — just ONE missing was enough to fail the
    # whole query with a GraphQL error. See supported_summary_fields().
    SUMMARY_COUNT_FIELDS = tuple(CROSSING_AVAILABILITY_COUNTS) + (
        # authorizedAreasCount intentionally not requested: authorizations
        # (like embargoes) are only shown in the platform's alert report.
        "riverSourcesCount",  # actionsCount: shown only in the report
    )

    def supported_summary_fields(self):
        """Introspects the QuerySummary schema (type of the "summary" field
        inside alerts{}), same as supported_analytic_fields() does for
        AlertData. Only requests the SUMMARY_COUNT_FIELDS counters that
        actually exist in this country's schema — avoids a single
        nonexistent field failing the whole query with a GraphQL error.

        If the intersection comes back empty with no exception, logs the
        real fields introspection found, for comparison against
        SUMMARY_COUNT_FIELDS."""
        if self._supported_summary_fields is not None:
            return self._supported_summary_fields
        query = """
            query QuerySummaryFields {
              __type(name: "QuerySummary") {
                fields { name }
              }
            }
        """
        try:
            data = self.graphql(query)
            type_info = data.get("__type")
            if type_info is None:
                raise RuntimeError(
                    "O schema desta API não tem um tipo chamado "
                    "\"QuerySummary\" — o nome do tipo do campo "
                    "summary{} pode ser diferente aqui."
                )
            available = {
                item.get("name")
                for item in (type_info.get("fields") or [])
            }
            self._supported_summary_fields = [
                field for field in self.SUMMARY_COUNT_FIELDS
                if field in available
            ]
            if not self._supported_summary_fields:
                # None of the expected counters showed up in the schema —
                # log the real available fields, for comparison against
                # SUMMARY_COUNT_FIELDS.
                QgsMessageLog.logMessage(
                    "QuerySummary exists at {}, but none of the "
                    "expected counters ({}) was found. Available "
                    "fields: {}".format(
                        self.endpoint,
                        sorted(self.SUMMARY_COUNT_FIELDS),
                        sorted(available),
                    ),
                    "MapBiomas Alerta Oficial",
                    Qgis.Warning,
                )
        except Exception as error:
            self._supported_summary_fields = None
            QgsMessageLog.logMessage(
                "Failed to query the QuerySummary schema at {}: "
                "{}".format(self.endpoint, error),
                "MapBiomas Alerta Oficial",
                Qgis.Warning,
            )
        return self._supported_summary_fields or []

    def discover_intersection_types(self, sample_size=300):
        """Samples a real set of alerts (wide date range, no crossing
        filter) and collects which crossing types (alertIntersections)
        actually appear for the connected country.

        Unlike crossing_availability() (which checks a fixed, known set
        of QuerySummary counters, covering only categories used in
        Brazil), this method observes real data through the
        alertIntersections field — so it also discovers categories
        configurable per country/initiative with no equivalent
        `crossed*` field.

        Caches the result per instance (one sampling per connected
        country/session)."""
        if self._discovered_intersection_types is not None:
            return self._discovered_intersection_types
        self.intersection_discovery_error = None
        if not self.supports_alert_intersections():
            self._discovered_intersection_types = []
            return self._discovered_intersection_types
        query = """
            query DiscoverIntersectionTypes(
              $page: Int, $limit: Int,
              $startDate: BaseDate, $endDate: BaseDate
            ) {
              alerts(
                page: $page, limit: $limit,
                startDate: $startDate, endDate: $endDate
              ) {
                collection {
                  __ALERT_INTERSECTIONS__
                }
              }
            }
        """.replace(
            "__ALERT_INTERSECTIONS__",
            self.ALERT_INTERSECTIONS_DISCOVERY_FIELDS,
        )
        try:
            data = self.graphql(query, {
                "page": 1,
                "limit": sample_size,
                "startDate": "2018-01-01",
                "endDate": "2030-12-31",
            })
            collected = {}
            for alert in (
                (data.get("alerts") or {}).get("collection") or []
            ):
                for entry in alert.get("alertIntersections") or []:
                    type_key = entry.get("type")
                    if not type_key:
                        continue
                    total_area = entry.get("totalAreaHa")
                    if total_area in (None, 0, 0.0):
                        continue
                    label = str(entry.get("name") or type_key)
                    collected.setdefault(str(type_key), label)
            self._discovered_intersection_types = sorted(
                collected.items(), key=lambda item: item[1]
            )
        except Exception as error:
            # Don't cache on failure (e.g. session not yet authenticated
            # during a country/language switch): an exception here doesn't
            # mean "sampled and found nothing", so the next call should
            # retry.
            self.intersection_discovery_error = str(error)
            QgsMessageLog.logMessage(
                "Could not sample crossing types "
                "(alertIntersections) at {}: {}".format(
                    self.endpoint, error
                ),
                "MapBiomas Alerta Oficial",
                Qgis.Warning,
            )
            return []
        return self._discovered_intersection_types

    def crossing_availability(self):
        """Checks with real data — via the API's own statistical summary
        counters — which CROSSING_AVAILABILITY_COUNTS categories actually
        have alerts for the currently connected country. Runs a single
        wide query (2018-2030, no other filters) and caches the result on
        this instance (one check per country/session, not per search).

        Uses its OWN minimal query (not the whole ALERTS_SUMMARY_QUERY),
        requesting only the counters confirmed by introspection via
        supported_summary_fields() — see the comment there for why."""
        if self._crossing_availability is not None:
            return self._crossing_availability
        availability = {}
        self.crossing_availability_error = None
        all_safe_fields = self.supported_summary_fields()
        # supported_summary_fields() covers SUMMARY_COUNT_FIELDS (a
        # superset, also used by alerts_statistics()) — here only the
        # actual crossing categories matter.
        safe_fields = [
            field for field in all_safe_fields
            if field in self.CROSSING_AVAILABILITY_COUNTS
        ]
        if self._supported_summary_fields is None:
            # Real failure checking the schema (e.g. session not yet
            # authenticated during a country/language switch) — not
            # "confirmed there's nothing", so don't cache. The next call
            # (e.g. right after login_api() finishes) redoes the check
            # instead of reusing an incorrect empty result.
            self.crossing_availability_error = (
                "Não foi possível confirmar os contadores de "
                "cruzamento (sessão não autenticada ou falha de "
                "conexão no momento da checagem)."
            )
            return availability
        if not safe_fields:
            # Different from the case above: introspection RAN
            # successfully, it's just that none of the expected counters
            # exist in the schema — this result is genuine, safe to
            # cache. supported_summary_fields() already logged the real
            # list of fields found, for future investigation.
            self.crossing_availability_error = (
                "Nenhum contador de cruzamento confirmado no schema "
                "QuerySummary desta API."
            )
            self._crossing_availability = availability
            return availability
        query = (
            "query CrossingAvailability(\n"
            "  $startDate: BaseDate, $endDate: BaseDate,\n"
            "  $dateType: DateTypes!\n"
            ") {\n"
            "  alerts(\n"
            "    startDate: $startDate, endDate: $endDate,\n"
            "    dateType: $dateType\n"
            "  ) {\n"
            "    summary {\n"
            "      " + "\n      ".join(safe_fields) + "\n"
            "    }\n"
            "  }\n"
            "}"
        )
        try:
            data = self.graphql(
                query,
                {
                    "startDate": "2018-01-01",
                    "endDate": "2030-12-31",
                    "dateType": "DetectedAt",
                },
            )
            summary = (data.get("alerts") or {}).get("summary") or {}
            for count_field in safe_fields:
                crossing_field = self.CROSSING_AVAILABILITY_COUNTS[
                    count_field
                ]
                try:
                    availability[crossing_field] = (
                        float(summary.get(count_field) or 0) > 0
                    )
                except (TypeError, ValueError):
                    availability[crossing_field] = False
        except Exception as error:
            self.crossing_availability_error = str(error)
            QgsMessageLog.logMessage(
                "Could not check which crossings have real "
                "data for {}: {}".format(
                    self.country.get("name", "?"), error
                ),
                "MapBiomas Alerta Oficial",
                Qgis.Warning,
            )
            # Same reason as the introspection block above: a failure
            # here (network, session not yet authenticated, etc.) isn't
            # a "confirmed there's nothing" — don't cache, to allow a
            # retry the next time populate_crossing_options() runs.
            return {}
        self._crossing_availability = availability
        return availability

    LOGIN_MUTATION = """
        mutation SignIn($email: String!, $password: String!) {
          signIn(email: $email, password: $password) { token }
        }
    """

    ALERTS_QUERY = """
        query Alerts(
          $page: Int, $limit: Int, $startDate: BaseDate,
          $endDate: BaseDate, $dateType: DateTypes,
          $startSize: Float, $endSize: Float,
          $sources: [SourceTypes!], $alertCodes: [ID!],
          $carCodes: [ID!], $boundingBox: [Float!],
          $territoryIds: [Int!] = [], $territoryCategory: String,
          $statusName: String,
          $sortField: AlertSortField, $sortDirection: SortDirection
        ) {
          alerts(
            page: $page, limit: $limit,
            startDate: $startDate, endDate: $endDate,
            dateType: $dateType, startSize: $startSize, endSize: $endSize,
            sources: $sources, alertCodes: $alertCodes, carCodes: $carCodes,
            boundingBox: $boundingBox,
            territoryIds: $territoryIds,
            territoryCategory: $territoryCategory,
            statusName: $statusName,
            sortField: $sortField, sortDirection: $sortDirection
          ) {
            collection {
              alertCode
              areaHa
              detectedAt
              publishedAt
              geometryWkt
              sources
              crossedBiomes
              crossedStates
              crossedCities
              imageAcquiredBeforeAt
              imageAcquiredAfterAt
              __ALERT_INTERSECTIONS__
              __ANALYTIC_FIELDS__
            }
            metadata {
              currentPage
              totalCount
              totalPages
            }
          }
        }
    """

    # Query provided by the MapBiomas Alerta Platform team. The same
    # arguments are kept without fallback or substitution. The rankings
    # documented in the ``alerts`` result complete the summary without any
    # local reconstruction of areas by city, state or biome.
    ALERTS_SUMMARY_QUERY = """
        query GetAlertsSummary(
          $alertCodes: [ID!] = [], $propertyCodes: [ID!] = [],
          $startDate: BaseDate, $endDate: BaseDate,
          $dateType: DateTypes!, $startSize: Float = 0.0,
          $endSize: Float = 9999999.0, $territoryIds: [Int!] = [],
          $territoryCategory: String, $sources: [SourceTypes!],
          $intersectWithCar: Boolean, $isInEmbargoedArea: Boolean,
          $isInAuthorizedArea: Boolean,
          $deforestationClasses: [DeforestationTypes!] = [All],
          $actionTypesIds: [Int!] = [], $boundingBox: [Float!]
        ) {
          alerts(
            alertCodes: $alertCodes, propertyCodes: $propertyCodes,
            startDate: $startDate, endDate: $endDate,
            dateType: $dateType, startSize: $startSize, endSize: $endSize,
            territoryIds: $territoryIds,
            territoryCategory: $territoryCategory, sources: $sources,
            intersectWithCar: $intersectWithCar,
            isInEmbargoedArea: $isInEmbargoedArea,
            isInAuthorizedArea: $isInAuthorizedArea,
            deforestationClasses: $deforestationClasses,
            actionTypesIds: $actionTypesIds, boundingBox: $boundingBox
          ) {
            summary {
              total
              area
              averageDeforestationSpeed
              biggestDeforestationSpeed
              biggestDeforestationSpeedAlert {
                alertCode
                crossedCities
                crossedStates
                __typename
              }
              __SUMMARY_COUNT_FIELDS__
              boundingBox {
                simplified
                __typename
              }
              alertsByYear {
                year
                value
                __typename
              }
              alertsByMonth {
                date
                value
                __typename
              }
              deforestationAreaByYear {
                year
                value
                __typename
              }
              deforestationAreaByMonth {
                date
                value
                __typename
              }
              biggestAlertArea
              biggestAlert {
                alertCode
                crossedCities
                crossedStates
                __typename
              }
              lowestAlertArea
              lowestAlert {
                alertCode
                crossedCities
                crossedStates
                __typename
              }
              __typename
            }
            rankingByBiome {
              alertsTotal
              areaTotal
              biome
              __typename
            }
            rankingByCity {
              alertsTotal
              areaTotal
              city
              __typename
            }
            rankingByState {
              alertsTotal
              areaTotal
              state
              __typename
            }
            __typename
          }
        }
    """

    ALERT_DETAIL_QUERY = """
        query AlertDetail($alertCode: Int!) {
          alert(alertCode: $alertCode) {
            alertCode
            geometryWkt
            areaHa
            detectedAt
            publishedAt
            sources
            crossedBiomes
            crossedBiomesList
            crossedStates
            crossedStatesList
            crossedCities
            crossedCitiesList
            imageAcquiredBeforeAt
            imageAcquiredAfterAt
            publishedImages {
              reference
              acquiredAt
              constellation
              satellite
              url
              urlMedium
            }
            __ALERT_INTERSECTIONS__
            __ANALYTIC_FIELDS__
          }
        }
    """

    RURAL_PROPERTY_QUERY = """
        query RuralProperty($carCode: String!) {
          ruralProperty(carCode: $carCode) {
            propertyCode
            areaHa
            state
            __RURAL_PROPERTY_FIELDS__
            alerts {
              alertCode
            }
          }
        }
    """

    # carType (CAR classification) and stateAcronym (Brazilian state
    # abbreviation) are conventions of Brazilian legislation — not
    # confirmed in other countries, which may have a rural property
    # registry with a different structure (e.g. "Terreno de Predio Rural"
    # in Colombia). Only included in the query if introspection confirms
    # they exist.
    RURAL_PROPERTY_OPTIONAL_FIELDS = ("carType", "stateAcronym")

    def supported_rural_property_fields(self):
        if self._supported_rural_property_fields is not None:
            return self._supported_rural_property_fields
        query = """
            query RuralPropertyFields {
              __type(name: "RuralProperty") {
                fields { name }
              }
            }
        """
        try:
            data = self.graphql(query)
            type_info = data.get("__type")
            if type_info is None:
                # Type name not confirmed by introspection — no way to
                # be sure, but this doesn't block the query: it just
                # omits the optional fields.
                self._supported_rural_property_fields = []
                return self._supported_rural_property_fields
            available = {
                item.get("name")
                for item in (type_info.get("fields") or [])
            }
            self._supported_rural_property_fields = [
                field for field in self.RURAL_PROPERTY_OPTIONAL_FIELDS
                if field in available
            ]
        except Exception as error:
            self._supported_rural_property_fields = None
            QgsMessageLog.logMessage(
                "Failed to query the RuralProperty schema at {}: "
                "{}".format(self.endpoint, error),
                "MapBiomas Alerta Oficial",
                Qgis.Warning,
            )
            return []
        return self._supported_rural_property_fields

    def __init__(self, country):
        self.country = dict(country)
        self.endpoint = country.get("api_url", "")
        self.CRS = country.get("api_crs", "EPSG:4326")
        self.token = None
        self._supported_analytic_fields = None
        self._supports_alert_intersections = None
        # Cache of the check for which crossing categories have real data
        # (not just the field name existing in the schema) for the
        # connected country — see crossing_availability().
        self._crossing_availability = None
        self.crossing_availability_error = None
        self._discovered_intersection_types = None
        self.intersection_discovery_error = None
        self._supported_summary_fields = None
        self.analytic_fields_error = None
        self._supported_rural_property_fields = None
        self._source_types = None
        self._territory_options = None
        self._rural_property_cache = {}
        self._image_host_failures = {}
        self._active_replies = []
        self._cancel_requested = False

    @property
    def authenticated(self):
        return bool(self.token)

    def login(self, email, password):
        email = str(email or "").strip()
        password = str(password or "")
        if not email or not password:
            raise ValueError("Informe o e-mail e a senha.")

        data = self.graphql(
            self.LOGIN_MUTATION,
            {"email": email, "password": password},
            authenticated=False,
        )
        token = data.get("signIn", {}).get("token")
        if not token:
            raise RuntimeError("A API não retornou um token de acesso.")
        self.token = token
        return True

    def logout(self):
        self.token = None

    def download_alerts(
        self,
        start_date,
        end_date,
        period_type=PERIOD_DETECTION,
        alert_code=None,
        alert_codes=None,
        property_codes=None,
        minimum_area=0.0,
        sources=None,
        bbox=None,
        territory_ids=None,
        territory_category=None,
        crossing_field=None,
        crossing_mode="all",
        include_analytics=True,
        fetch_statistics=True,
        precomputed_statistics=None,
        progress_callback=None,
    ):
        self._cancel_requested = False
        if not self.authenticated:
            raise RuntimeError("Faça login na API antes de buscar alertas.")

        variables = {
            "limit": self.PAGE_SIZE,
            "startSize": float(minimum_area or 0),
            "endSize": 9999999.0,
            "statusName": "published",
            "sortField": "ALERT_CODE",
            "sortDirection": "ASC",
            "territoryIds": [int(value) for value in (territory_ids or [])],
            "territoryCategory": territory_category,
            "dateType": (
                "PublishedAt"
                if period_type == self.PERIOD_PUBLICATION
                else "DetectedAt"
            ),
        }
        if start_date and end_date:
            variables.update({
                "startDate": start_date,
                "endDate": end_date,
            })
        if alert_code:
            variables["alertCodes"] = [str(alert_code)]
        elif alert_codes:
            variables["alertCodes"] = [str(code) for code in alert_codes]
        if property_codes:
            variables["carCodes"] = [str(code) for code in property_codes]
        if sources:
            variables["sources"] = list(sources)
        if bbox is not None:
            variables["boundingBox"] = [float(value) for value in bbox]

        features = []
        skipped_geometry_codes = []
        seen_alert_codes = set()
        server_feature_count = 0
        server_area_total = 0.0
        filtered_feature_count = 0
        page = 1
        total_pages = 1
        expected_total_count = None
        downloaded_pages = 0
        api_statistics = {}
        if fetch_statistics:
            if precomputed_statistics is not None:
                # Already fetched before the geometry, for the "large
                # query" warning in main_dialog.py — avoids repeating the
                # same summary query here.
                api_statistics = precomputed_statistics
            else:
                if progress_callback is not None:
                    progress_callback(0, 0, "summary")
                api_statistics = self.alerts_statistics(
                    alert_codes=(
                        [] if property_codes else (
                            [str(alert_code)] if alert_code else alert_codes
                        )
                    ),
                    property_codes=property_codes,
                    start_date=start_date,
                    end_date=end_date,
                    period_type=period_type,
                    minimum_area=minimum_area,
                    sources=sources,
                    bbox=bbox,
                    territory_ids=territory_ids,
                    territory_category=territory_category,
                )

        needs_crossing_fields = (
            crossing_mode in ("with", "without") and bool(crossing_field)
        )
        supported_fields = set(
            self.supported_analytic_fields()
            if include_analytics or needs_crossing_fields
            else []
        )
        analytic_fields = []
        if include_analytics:
            analytic_fields.extend((
                "crossedBiomesList",
                "crossedStatesList",
                "crossedCitiesList",
            ))
            analytic_fields.extend(
                field for field in (
                    list(self.ANALYTIC_FIELDS) + list(self.AREA_MAP_FIELDS)
                )
                if field in supported_fields
                and field not in (
                    "ruralPropertiesCodes", "ruralPropertiesTotal"
                )
            )
        is_new_style_crossing_field = (
            isinstance(crossing_field, str)
            and crossing_field.startswith("intersection:")
        )
        if (
            needs_crossing_fields
            and crossing_field != "__any__"
            and not is_new_style_crossing_field
        ):
            if crossing_field in supported_fields:
                analytic_fields.append(crossing_field)
            companion = crossing_field + "Area"
            if companion in supported_fields:
                analytic_fields.append(companion)
        elif (
            needs_crossing_fields
            and crossing_field == "__any__"
            and not self.supports_alert_intersections()
        ):
            # If the API already supports alertIntersections, "any
            # crossing" is resolved entirely by has_any_intersection() on
            # that field — no need (or sense) to request the old crossed*
            # fields here.
            analytic_fields.extend(
                field for field, _label in self.CROSSING_OPTIONS
                if field in supported_fields
            )
        analytic_fields = list(dict.fromkeys(analytic_fields))
        # Pages already downloaded ahead of time (page number -> data).
        # Page 1 always goes alone: it gives totalCount and may renegotiate
        # the page size. After that, up to PARALLEL_PAGES are fetched at
        # once, but still processed strictly in order below, so every
        # validation keeps working exactly as before.
        prefetched_pages = {}
        while True:
            if self._cancel_requested:
                self._cancel_requested = False
                raise QueryCancelledError("Consulta cancelada pelo usuário.")
            variables["page"] = page
            if progress_callback is not None:
                progress_callback(page, total_pages, "download")
            query = self.query_with_analytic_fields(
                self.ALERTS_QUERY,
                analytic_fields,
                include_intersections=(
                    include_analytics or needs_crossing_fields
                ),
            )
            if page in prefetched_pages:
                data = prefetched_pages.pop(page)
            elif page > 1 and total_pages > page:
                last_page = min(total_pages, page + self.PARALLEL_PAGES - 1)
                page_numbers = list(range(page, last_page + 1))
                batch_variables = [
                    dict(variables, page=number) for number in page_numbers
                ]
                for number, page_data in zip(
                    page_numbers, self.graphql_many(query, batch_variables)
                ):
                    prefetched_pages[number] = page_data
                data = prefetched_pages.pop(page)
            else:
                data = self.graphql(query, variables)
            result = data.get("alerts", {})
            batch = result.get("collection", [])
            metadata = result.get("metadata") or {}

            metadata_total = metadata.get("totalCount")
            if metadata_total is None:
                raise RuntimeError(
                    "A API não informou metadata.totalCount; não é "
                    "possível garantir que todos os alertas foram recebidos."
                )
            metadata_total = int(metadata_total)
            if expected_total_count is None:
                expected_total_count = metadata_total
            elif metadata_total != expected_total_count:
                raise RuntimeError(
                    "A quantidade total informada pela API mudou durante a "
                    "paginação ({} para {}). Refaça a consulta.".format(
                        expected_total_count,
                        metadata_total,
                    )
                )

            metadata_pages = int(metadata.get("totalPages") or 0)
            returned_count = len(batch)

            # Some API configurations accept the requested pagination limit
            # but return a smaller page. When totalPages was computed with
            # the requested limit, stopping based on that field loses
            # records. We renegotiate the actually-returned page size
            # before processing the first page.
            if (
                page == 1
                and expected_total_count > returned_count > 0
                and metadata_pages > 0
            ):
                pages_for_returned_size = (
                    expected_total_count + returned_count - 1
                ) // returned_count
                if metadata_pages < pages_for_returned_size:
                    requested_size = int(variables.get("limit") or 0)
                    if returned_count >= requested_size:
                        raise RuntimeError(
                            "A paginação informada pela API é inconsistente."
                        )
                    variables["limit"] = returned_count
                    total_pages = pages_for_returned_size
                    continue

            downloaded_pages += 1
            unique_batch = []
            for alert in batch:
                alert_code_value = str(alert.get("alertCode") or "")
                if alert_code_value and alert_code_value in seen_alert_codes:
                    continue
                if alert_code_value:
                    seen_alert_codes.add(alert_code_value)
                unique_batch.append(alert)
            server_feature_count += len(unique_batch)
            for alert in unique_batch:
                try:
                    server_area_total += float(alert.get("areaHa") or 0)
                except (TypeError, ValueError):
                    pass
            page_size = int(variables.get("limit") or returned_count or 1)
            if expected_total_count:
                effective_pages = (
                    expected_total_count + page_size - 1
                ) // page_size
                total_pages = max(page, metadata_pages, effective_pages)
            else:
                total_pages = max(page, metadata_pages)

            # Validate, filter and convert each page immediately. Besides using
            # less memory, this distributes the CPU work across the download
            # and removes the long, apparently idle step after the last page.
            self.validate_downloaded_alerts(
                unique_batch,
                start_date,
                end_date,
                period_type,
                alert_code,
                minimum_area,
            )
            if crossing_mode in ("with", "without"):
                filtered_batch = []
                is_new_style = (
                    isinstance(crossing_field, str)
                    and crossing_field.startswith("intersection:")
                )
                # Hoisted out of the per-alert loop: it's a cached value
                # (no network cost), but there's no reason to re-evaluate
                # the same condition hundreds/thousands of times.
                intersections_supported = self.supports_alert_intersections()
                for alert in unique_batch:
                    if crossing_field == "__any__":
                        has_crossing = (
                            self.has_any_intersection(alert)
                            if intersections_supported
                            else any(
                                self.has_crossing(alert.get(field))
                                for field, _label in self.CROSSING_OPTIONS
                                if field in supported_fields
                            )
                        )
                    elif is_new_style:
                        type_key = crossing_field.split(":", 1)[1]
                        has_crossing = self.has_intersection_type(
                            alert, type_key
                        )
                    else:
                        has_crossing = self.has_crossing(
                            alert.get(crossing_field)
                        )
                    if (
                        (crossing_mode == "with" and has_crossing)
                        or (crossing_mode == "without" and not has_crossing)
                    ):
                        filtered_batch.append(alert)
            else:
                filtered_batch = unique_batch
            filtered_feature_count += len(filtered_batch)
            page_document, page_skipped_codes = self.to_geojson(
                filtered_batch, period_type, return_stats=True
            )
            features.extend(page_document.get("features") or [])
            skipped_geometry_codes.extend(page_skipped_codes)
            if progress_callback is not None:
                progress_callback(page, total_pages, "process")
            if server_feature_count == expected_total_count:
                break
            if server_feature_count > expected_total_count:
                raise RuntimeError(
                    "A API entregou mais alertas do que metadata.totalCount. "
                    "A consulta foi interrompida para evitar dados incorretos."
                )
            if not batch:
                raise RuntimeError(
                    "A API interrompeu a paginação após {} de {} "
                    "alerta(s). Nenhuma camada incompleta foi criada.".format(
                        server_feature_count,
                        expected_total_count,
                    )
                )
            if not unique_batch:
                raise RuntimeError(
                    "A API repetiu uma página sem entregar novos alertas "
                    "({} de {}). Nenhuma camada incompleta foi criada.".format(
                        server_feature_count,
                        expected_total_count,
                    )
                )
            page += 1

        if server_feature_count != expected_total_count:
            raise RuntimeError(
                "A API informou {} alerta(s), mas entregou {}. Nenhuma "
                "camada incompleta foi criada.".format(
                    expected_total_count,
                    server_feature_count,
                )
            )
        if fetch_statistics:
            summary = (api_statistics or {}).get("summary") or {}
            summary_total = summary.get("total")
            if summary_total is None:
                raise RuntimeError(
                    "A consulta estatística da plataforma não informou o "
                    "total de alertas. Nenhuma camada foi criada sem essa "
                    "validação."
                )
            if int(summary_total) != expected_total_count:
                raise RuntimeError(
                    "Os resultados da própria API divergiram: o resumo da "
                    "plataforma informou {} alerta(s), enquanto a paginação "
                    "informou {}. Nenhuma camada incorreta foi criada.".format(
                        int(summary_total),
                        expected_total_count,
                    )
                )
            summary_area = summary.get("area")
            if summary_area is not None:
                try:
                    summary_area = float(summary_area)
                except (TypeError, ValueError) as error:
                    raise RuntimeError(
                        "A consulta estatística retornou uma área inválida."
                    ) from error
                if round(summary_area, 1) != round(server_area_total, 1):
                    raise RuntimeError(
                        "Os resultados da própria API divergiram: o resumo "
                        "da plataforma informou {:.1f} ha, mas a soma dos "
                        "alertas recebidos foi {:.1f} ha. Nenhuma camada "
                        "incorreta foi criada.".format(
                            summary_area,
                            server_area_total,
                        )
                    )
        document = {"type": "FeatureCollection", "features": features}
        loaded_feature_count = len(features)
        skipped_geometry_count = len(skipped_geometry_codes)
        if progress_callback is not None:
            progress_callback(total_pages, total_pages, "finalize")
        output_path = self.save_temporary_geojson(document)
        return {
            "path": output_path,
            "api_feature_count": filtered_feature_count,
            "feature_count": loaded_feature_count,
            "skipped_geometry_count": skipped_geometry_count,
            "skipped_geometry_codes": skipped_geometry_codes,
            "server_feature_count": server_feature_count,
            "pages": downloaded_pages,
            "pagination_warning": None,
            "api_statistics": api_statistics or {},
        }

    def alerts_statistics(
        self,
        alert_codes=None,
        property_codes=None,
        start_date=None,
        end_date=None,
        period_type=PERIOD_DETECTION,
        minimum_area=0.0,
        sources=None,
        bbox=None,
        territory_ids=None,
        territory_category=None,
    ):
        """Returns the platform summary without downloading the alerts."""
        variables = {
            "alertCodes": [str(code) for code in (alert_codes or [])],
            "propertyCodes": [str(code) for code in (property_codes or [])],
            "startDate": start_date,
            "endDate": end_date,
            "dateType": (
                "PublishedAt"
                if period_type == self.PERIOD_PUBLICATION
                else "DetectedAt"
            ),
            "startSize": float(minimum_area or 0),
            "endSize": 9999999.0,
            "territoryIds": [int(value) for value in (territory_ids or [])],
            "territoryCategory": territory_category,
            "sources": list(sources or ["All"]),
            "intersectWithCar": None,
            "isInEmbargoedArea": None,
            "isInAuthorizedArea": None,
            "deforestationClasses": ["All"],
            "actionTypesIds": [],
            "boundingBox": (
                [float(value) for value in bbox] if bbox is not None else None
            ),
        }
        query = self.ALERTS_SUMMARY_QUERY.replace(
            "__SUMMARY_COUNT_FIELDS__",
            "\n".join(self.supported_summary_fields()),
        )
        data = self.graphql(query, variables)
        result = data.get("alerts") or {}
        return {
            "summary": result.get("summary") or {},
            "rankingByBiome": result.get("rankingByBiome") or [],
            "rankingByCity": result.get("rankingByCity") or [],
            "rankingByState": result.get("rankingByState") or [],
        }

    @classmethod
    def validate_downloaded_alerts(
        cls,
        alerts,
        start_date,
        end_date,
        period_type,
        alert_code,
        minimum_area,
    ):
        start = cls.parse_date(start_date)
        end = cls.parse_date(end_date)
        date_field = (
            "publishedAt"
            if period_type == cls.PERIOD_PUBLICATION
            else "detectedAt"
        )
        for alert in alerts:
            code = str(alert.get("alertCode") or "")
            reference = cls.parse_date(alert.get(date_field))
            if (
                start is not None
                and end is not None
                and (
                    reference is None
                    or reference < start
                    or reference > end
                )
            ):
                raise RuntimeError(
                    "A API devolveu o alerta {} fora do período solicitado."
                    .format(code or "sem código")
                )
            try:
                area = float(alert.get("areaHa") or 0)
            except (TypeError, ValueError):
                area = 0.0
            if area + 1e-9 < float(minimum_area or 0):
                raise RuntimeError(
                    "A API devolveu o alerta {} abaixo da área mínima."
                    .format(code or "sem código")
                )
            if alert_code and code != str(alert_code):
                raise RuntimeError(
                    "A API devolveu um código diferente do solicitado."
                )

    def alert_details(self, alert_code):
        data = self.graphql(
            self.query_with_analytic_fields(self.ALERT_DETAIL_QUERY),
            {"alertCode": int(alert_code)},
        )
        alert = data.get("alert")
        if not alert:
            raise RuntimeError("A API não encontrou o alerta informado.")
        return alert

    TERRITORY_OPTIONS_QUERY = """
        query TerritoryOptions {
          territoryOptions {
            category
            categoryName
            territories { id name }
          }
        }
    """

    def wms_layer_names(self, wms_url):
        """Names published by the map server (GetCapabilities), cached."""
        cache = getattr(self, "_wms_layer_names", None)
        if cache is None:
            cache = self._wms_layer_names = {}
        if wms_url in cache:
            return cache[wms_url]
        from qgis.core import QgsBlockingNetworkRequest

        request = QgsBlockingNetworkRequest()
        error = request.get(QNetworkRequest(QUrl(
            wms_url + "?service=WMS&version=1.3.0&request=GetCapabilities"
        )))
        if error != QgsBlockingNetworkRequest.ErrorCode.NoError:
            raise RuntimeError(request.errorMessage() or "GetCapabilities")
        content = bytes(request.reply().content()).decode(
            "utf-8", errors="replace"
        )
        names = set(re.findall(r"<Name>\s*([^<\s]+)\s*</Name>", content))
        cache[wms_url] = names
        return names

    TERRITORY_ID_FIELDS = ("id", "territoryId", "value", "code", "key")
    TERRITORY_NAME_FIELDS = (
        "name", "label", "text", "territoryName", "description", "title",
    )

    def _type_fields(self, type_name):
        try:
            data = self._type_fields_query(type_name)
        except RuntimeError:
            return []
        return (data.get("__type") or {}).get("fields") or []

    def _type_fields_query(self, type_name):
        return self.graphql(
            "query { __type(name: %s) { fields { name type { name kind "
            "ofType { name kind ofType { name kind ofType { name kind } } } "
            "} } } }" % json.dumps(type_name)
        )

    @staticmethod
    def _named_type(type_info):
        while type_info and not type_info.get("name"):
            type_info = type_info.get("ofType")
        return (type_info or {}).get("name")

    def territory_options(self):
        """Territory categories of the platform (territoryOptions), cached
        per client/country. The documentation doesn't list the fields of
        each territory, so they are discovered by introspection first
        (asking for a field that doesn't exist fails the whole query)."""
        if self._territory_options is not None:
            return self._territory_options
        item_type = "TerritoryOption"
        for field in self._type_fields("TerritoryCategory"):
            if field.get("name") == "territories":
                item_type = self._named_type(field.get("type")) or item_type
        item_fields = {
            field.get("name") for field in self._type_fields(item_type)
        }
        id_field = next(
            (name for name in self.TERRITORY_ID_FIELDS if name in item_fields),
            None,
        )
        name_field = next(
            (name for name in self.TERRITORY_NAME_FIELDS if name in item_fields),
            None,
        )
        if id_field is None and item_fields:
            raise RuntimeError(
                "campos de território não reconhecidos: {}".format(
                    ", ".join(sorted(item_fields))
                )
            )
        if id_field is not None:
            attempts = [(id_field, name_field)]
        else:
            # Introspection disabled on the server: try the usual shapes.
            attempts = [
                ("id", "name"), ("value", "label"), ("id", "label"),
                ("code", "name"), ("id", None),
            ]
        data = None
        last_error = None
        for id_field, name_field in attempts:
            wanted = [id_field] + ([name_field] if name_field else [])
            try:
                data = self.graphql(
                    "query TerritoryOptions { territoryOptions { category "
                    "categoryName territories { %s } } }" % " ".join(wanted)
                )
                break
            except RuntimeError as error:
                last_error = error
        if data is None:
            raise RuntimeError(str(last_error))
        options = []
        for option in data.get("territoryOptions") or []:
            options.append({
                "category": option.get("category"),
                "categoryName": option.get("categoryName"),
                "territories": [
                    {
                        "id": item.get(id_field),
                        "name": item.get(name_field) if name_field else None,
                    }
                    for item in (option.get("territories") or [])
                ],
            })
        self._territory_options = options
        QgsMessageLog.logMessage(
            "territoryOptions: {} category(ies) ({})".format(
                len(options),
                ", ".join(
                    str(o.get("category") or o.get("categoryName"))
                    for o in options
                ),
            ),
            "MapBiomas Alerta Oficial",
            Qgis.Info,
        )
        return self._territory_options

    def biome_territories(self):
        """(category, [(id, name), ...], error) for the biome category.
        ``error`` explains why the list is empty, for the panel's hint."""
        try:
            options = self.territory_options()
        except Exception as error:
            QgsMessageLog.logMessage(
                "territoryOptions unavailable: {}".format(error),
                "MapBiomas Alerta Oficial",
                Qgis.Warning,
            )
            return None, [], str(error)
        for option in options:
            key = "{} {}".format(
                option.get("category") or "", option.get("categoryName") or ""
            ).casefold()
            if "biom" not in key:
                continue
            territories = []
            for item in option.get("territories") or []:
                try:
                    territory_id = int(item.get("id"))
                except (TypeError, ValueError):
                    continue
                territories.append(
                    (territory_id, str(item.get("name") or territory_id))
                )
            if not territories:
                return None, [], "a categoria de bioma veio sem territórios"
            return option.get("category"), sorted(
                territories, key=lambda value: value[1]
            ), None
        return None, [], "a API não tem categoria de bioma ({})".format(
            ", ".join(
                str(o.get("categoryName") or o.get("category"))
                for o in options
            ) or "nenhuma categoria"
        )

    def rural_property(self, property_code):
        code = str(property_code or "").strip()
        if not code:
            return {}
        if code not in self._rural_property_cache:
            query = self.RURAL_PROPERTY_QUERY.replace(
                "__RURAL_PROPERTY_FIELDS__",
                "\n".join(self.supported_rural_property_fields()),
            )
            data = self.graphql(
                query,
                {"carCode": code},
            )
            self._rural_property_cache[code] = data.get("ruralProperty") or {}
        return self._rural_property_cache[code]

    @staticmethod
    def has_crossing(value):
        if value is None:
            return False
        if isinstance(value, (list, tuple, dict, str)):
            return bool(value)
        try:
            return float(value) > 0
        except (TypeError, ValueError):
            return bool(value)

    @staticmethod
    def has_intersection_type(alert, type_key):
        """Checks, within the new alertIntersections field, whether an
        entry of the requested type (type_key) with a real crossing exists
        (totalAreaHa > 0 or at least one territory in names) — used by the
        "Crossing type" filter when the API already supports the new
        mechanism (see ALERT_INTERSECTIONS_FIELDS)."""
        for entry in alert.get("alertIntersections") or []:
            if entry.get("type") != type_key:
                continue
            total_area = entry.get("totalAreaHa")
            if total_area not in (None, 0, 0.0):
                return True
            if entry.get("names"):
                return True
        return False

    @staticmethod
    def has_any_intersection(alert):
        for entry in alert.get("alertIntersections") or []:
            total_area = entry.get("totalAreaHa")
            if total_area not in (None, 0, 0.0):
                return True
            if entry.get("names"):
                return True
        return False

    ALERT_INTERSECTIONS_FIELDS = """
        alertIntersections {
          type
          name
          names
          codes
          category
          totalAreaHa
          units {
            code
            name
            areaHa
            crossAreaHa
            version
          }
        }
    """

    # Lean version, without the "units" breakdown (which can have several
    # entries per crossing type) — used only by discover_intersection_types()'s
    # sampling, which only needs to find out WHICH types exist, not the
    # full per-territory breakdown. Requesting ALERT_INTERSECTIONS_FIELDS
    # (with units) for a sample of hundreds of alerts would produce an
    # unnecessarily heavy response for this purpose.
    ALERT_INTERSECTIONS_DISCOVERY_FIELDS = """
        alertIntersections {
          type
          name
          category
          totalAreaHa
        }
    """

    def query_with_analytic_fields(
        self, query, fields=None, include_intersections=True
    ):
        if fields is None:
            fields = self.supported_analytic_fields()
        query = query.replace(
            "__ANALYTIC_FIELDS__",
            "\n".join(fields),
        )
        # alertIntersections is the new, unified field that the API's own
        # documentation recommends in place of the crossed* fields
        # (marked as deprecated) — only included in the query if
        # introspection confirms it exists in this country AND the caller
        # actually needs it (include_intersections=False avoids the extra
        # weight on searches that use neither crossing nor full analytics,
        # even if the country supports it).
        query = query.replace(
            "__ALERT_INTERSECTIONS__",
            self.ALERT_INTERSECTIONS_FIELDS
            if include_intersections and self.supports_alert_intersections()
            else "",
        )
        return query

    def supported_analytic_fields(self):
        if self._supported_analytic_fields is not None:
            return self._supported_analytic_fields
        query = """
            query AlertDataFields {
              __type(name: "AlertData") {
                fields { name }
              }
            }
        """
        try:
            data = self.graphql(query)
            available = {
                item.get("name")
                for item in (
                    data.get("__type", {}).get("fields") or []
                )
            }
            self._supported_analytic_fields = [
                field for field in (
                    list(self.ANALYTIC_FIELDS) + list(self.AREA_MAP_FIELDS)
                )
                if field in available
            ]
            # alertIntersections is the new, unified field the API itself
            # recommends using in place of the crossed* fields (marked as
            # deprecated in the official docs —
            # https://docs.api.alerta.mapbiomas.org/sobre-a-api/
            # consulta-de-cruzamentos). Reuses the same AlertData
            # introspection done above, instead of a separate query.
            self._supports_alert_intersections = (
                "alertIntersections" in available
            )
            self.analytic_fields_error = None
        except Exception as error:
            self._supported_analytic_fields = None
            self._supports_alert_intersections = None
            self.analytic_fields_error = str(error)
            QgsMessageLog.logMessage(
                "Failed to query analytic fields at {}: {}".format(
                    self.endpoint, error
                ),
                "MapBiomas Alerta Oficial",
                Qgis.Warning,
            )
        return self._supported_analytic_fields or []

    def supports_alert_intersections(self):
        """True if this API's schema already has the unified
        alertIntersections field (recommended replacement for the
        crossed* fields, see comment above). Calls
        supported_analytic_fields() if it hasn't run yet, since both use
        the same AlertData introspection."""
        if self._supports_alert_intersections is None:
            self.supported_analytic_fields()
        return bool(self._supports_alert_intersections)

    def source_types(self):
        if self._source_types is not None:
            return self._source_types
        query = """
            query SourceTypes {
              __type(name: "SourceTypes") {
                enumValues { name description }
              }
            }
        """
        data = self.graphql(query)
        values = data.get("__type", {}).get("enumValues") or []
        self._source_types = [
            (
                item.get("name"),
                item.get("description") or item.get("name"),
            )
            for item in values
            if item.get("name") and item.get("name") != "All"
        ]
        return self._source_types

    def download_image(self, url, authenticated=False):
        """Downloads a published image, following redirects."""
        image_url = QUrl(str(url))
        if image_url.isRelative():
            image_url = QUrl(
                self.country.get("platform_url", self.endpoint)
            ).resolved(image_url)
        image_host = image_url.host()
        failed_at = self._image_host_failures.get(image_host)
        if failed_at is not None and time.monotonic() - failed_at < 60:
            raise RuntimeError(
                "O servidor de imagens está temporariamente indisponível."
            )
        request = QNetworkRequest(image_url)
        request.setRawHeader(b"Accept", b"image/*")
        request.setRawHeader(
            b"User-Agent",
            b"MapBiomas-Alert-Analytics-QGIS",
        )
        platform_url = str(self.country.get("platform_url") or "").rstrip("/")
        if platform_url:
            request.setRawHeader(b"Origin", platform_url.encode("utf-8"))
            request.setRawHeader(
                b"Referer",
                (platform_url + "/").encode("utf-8"),
            )
        try:
            request.setAttribute(
                QNetworkRequest.Attribute.RedirectPolicyAttribute,
                QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy,
            )
        except AttributeError:
            pass
        if authenticated and self.token:
            request.setRawHeader(
                b"Authorization",
                ("Bearer " + self.token).encode("utf-8"),
            )
        reply = QgsNetworkAccessManager.instance().get(request)
        event_loop = QEventLoop()
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(event_loop.quit)
        reply.finished.connect(event_loop.quit)
        timer.start(self.IMAGE_TIMEOUT_MILLISECONDS)
        event_loop.exec()
        if timer.isActive():
            timer.stop()
        if not reply.isFinished():
            reply.abort()
            reply.deleteLater()
            self._image_host_failures[image_host] = time.monotonic()
            raise RuntimeError("O servidor de imagens não respondeu em 30 segundos.")
        data = bytes(reply.readAll())
        error = reply.error()
        message = reply.errorString()
        status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        reply.deleteLater()
        # A 2xx status with a non-empty body means the image actually
        # arrived, even if Qt also reports a network error (see the
        # same situation in graphql() above).
        succeeded = bool(data) and status and 200 <= int(status) < 300
        if not succeeded and (error or not data):
            if any(
                marker in str(message).casefold()
                for marker in ("expir", "timeout", "timed out")
            ):
                self._image_host_failures[image_host] = time.monotonic()
            raise RuntimeError(
                "Não foi possível baixar a imagem (HTTP {}): {}".format(
                    status or "?",
                    message,
                )
            )
        self._image_host_failures.pop(image_host, None)
        return data

    def graphql(self, query, variables=None, authenticated=True):
        return self.graphql_many(query, [variables], authenticated)[0]

    def graphql_many(self, query, variables_list, authenticated=True):
        """Sends one POST per variables dict at the same time and waits for
        all of them in a single event loop (on the UI thread, like before).
        Returns the data dicts in the same order; the first failing reply
        raises exactly as a single graphql() call would."""
        if authenticated and not self.token:
            raise RuntimeError("A sessão da API não está autenticada.")
        manager = QgsNetworkAccessManager.instance()
        replies = [
            manager.post(
                self._graphql_request(authenticated),
                json.dumps(
                    {"query": query, "variables": variables or {}},
                    ensure_ascii=False,
                ).encode("utf-8"),
            )
            for variables in variables_list
        ]
        self._active_replies = list(replies)
        event_loop = QEventLoop()
        timer = QTimer()
        timer.setSingleShot(True)
        state = {"timed_out": False}

        def check_done():
            if all(reply.isFinished() for reply in replies):
                event_loop.quit()

        def timeout():
            state["timed_out"] = True
            for reply in replies:
                if not reply.isFinished():
                    reply.abort()
            event_loop.quit()

        timer.timeout.connect(timeout)
        for reply in replies:
            reply.finished.connect(check_done)
        timer.start(self.TIMEOUT_MILLISECONDS)
        if not all(reply.isFinished() for reply in replies):
            event_loop.exec()
        self._active_replies = []
        if timer.isActive():
            timer.stop()
        try:
            return [
                self._parse_graphql_reply(
                    reply, state["timed_out"], authenticated
                )
                for reply in replies
            ]
        finally:
            for reply in replies:
                reply.deleteLater()

    def _graphql_request(self, authenticated):
        request = QNetworkRequest(QUrl(self.endpoint))
        request.setHeader(
            QNetworkRequest.KnownHeaders.ContentTypeHeader,
            "application/json",
        )
        request.setRawHeader(b"Accept", b"application/json")
        request.setRawHeader(
            b"User-Agent",
            b"MapBiomas-Alert-Analytics-QGIS",
        )
        if authenticated:
            request.setRawHeader(
                b"Authorization",
                ("Bearer " + self.token).encode("utf-8"),
            )
        return request

    def _parse_graphql_reply(self, reply, timed_out, authenticated):
        response = bytes(reply.readAll()).decode("utf-8", errors="replace")
        network_error = reply.error()
        error_message = reply.errorString()
        status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)

        if self._cancel_requested:
            self._cancel_requested = False
            raise QueryCancelledError("Consulta cancelada pelo usuário.")
        if timed_out:
            raise RuntimeError("A consulta à API excedeu 120 segundos.")
        if status == 401:
            self.logout()
            raise ApiAuthenticationError(
                "A sessão expirou ou as credenciais são inválidas. "
                "Entre novamente na API."
            )
        if status == 403:
            raise RuntimeError("A API recusou o acesso (HTTP 403).")
        if status == 429:
            raise RuntimeError(
                "O limite de requisições da API foi atingido (HTTP 429). "
                "Aguarde e tente novamente."
            )
        if status and int(status) >= 500:
            raise RuntimeError(
                "A API está temporariamente indisponível (HTTP {}).".format(
                    status
                )
            )

        # A 2xx status with a parseable JSON body means the request
        # actually succeeded, even if Qt also reports a network_error
        # (some servers close the connection right after sending the
        # body, which Qt can flag as an error despite the full response
        # having already arrived). Trust the HTTP response over that
        # flag; only fall back to it when there's no usable body.
        document = None
        if status and 200 <= int(status) < 300 and response:
            try:
                document = json.loads(response)
            except json.JSONDecodeError:
                document = None

        if document is None:
            if network_error:
                raise RuntimeError(
                    "Erro de rede{}: {}".format(
                        " (HTTP {})".format(status) if status else "",
                        error_message,
                    )
                )
            try:
                document = json.loads(response)
            except json.JSONDecodeError as error:
                raise RuntimeError(
                    "A API retornou uma resposta inválida."
                ) from error

        errors = document.get("errors") or []
        if errors:
            messages = [
                item.get("message", "Erro não informado")
                for item in errors
            ]
            joined = "\n".join(messages)
            lowered = joined.casefold()
            if authenticated and any(
                term in lowered
                for term in ("unauth", "token", "jwt", "expired", "expir")
            ):
                self.logout()
                raise ApiAuthenticationError(
                    "A sessão da API expirou. Entre novamente."
                )
            raise RuntimeError(joined)
        return document.get("data") or {}

    def cancel_current_request(self):
        self._cancel_requested = True
        for reply in list(getattr(self, "_active_replies", [])):
            if not reply.isFinished():
                reply.abort()

    @staticmethod
    def to_geojson(
        alerts,
        period_type=PERIOD_DETECTION,
        return_stats=False,
    ):
        features = []
        skipped_geometry_codes = []
        for alert in alerts:
            geometry = QgsGeometry.fromWkt(alert.get("geometryWkt") or "")
            if geometry.isNull() or geometry.isEmpty():
                skipped_geometry_codes.append(
                    str(alert.get("alertCode") or "no code")
                )
                continue
            source_values = MapBiomasApiClient.value_list(
                alert.get("sources")
            )
            images = sorted(
                alert.get("publishedImages") or [],
                key=lambda item: str(item.get("acquiredAt") or ""),
            )
            before_image = images[0] if images else {}
            after_image = images[-1] if len(images) > 1 else {}
            properties = {
                "CodeAlerta": str(alert.get("alertCode") or ""),
                "AreaHa": alert.get("areaHa"),
                "DataDetec": alert.get("detectedAt"),
                "PubImg": alert.get("publishedAt"),
                "ImgAntes": (
                    before_image.get("acquiredAt")
                    or alert.get("imageAcquiredBeforeAt")
                ),
                "TipoAntes": MapBiomasApiClient.image_type(before_image),
                "ImgDepois": (
                    after_image.get("acquiredAt")
                    or alert.get("imageAcquiredAfterAt")
                ),
                "TipoDepois": MapBiomasApiClient.image_type(after_image),
                "Fonte": MapBiomasApiClient.join_values(source_values),
                "Bioma": MapBiomasApiClient.join_values(
                    alert.get("crossedBiomes")
                ),
                "Estado": MapBiomasApiClient.join_values(
                    alert.get("crossedStates")
                ),
                "Municipio": MapBiomasApiClient.join_values(
                    alert.get("crossedCities")
                ),
                "BiomaAreas": MapBiomasApiClient.territory_areas_json(
                    alert.get("crossedBiomesList")
                ),
                "EstadoAreas": MapBiomasApiClient.territory_areas_json(
                    alert.get("crossedStatesList")
                ),
                "MunicAreas": MapBiomasApiClient.territory_areas_json(
                    alert.get("crossedCitiesList")
                ),
                "BiomaAreaHa": MapBiomasApiClient.territory_area_total(
                    alert.get("crossedBiomesList")
                ),
                "EstadoAreaHa": MapBiomasApiClient.territory_area_total(
                    alert.get("crossedStatesList")
                ),
                "MunicAreaHa": MapBiomasApiClient.territory_area_total(
                    alert.get("crossedCitiesList")
                ),
            }
            reconciled_uc_areas = (
                MapBiomasApiClient.reconcile_conservation_unit_areas(alert)
            )
            if reconciled_uc_areas:
                properties["UnidConservAreas"] = json.dumps(
                    reconciled_uc_areas, ensure_ascii=False,
                    separators=(",", ":"),
                )
            # The per-territory breakdown (BiomaAreas/EstadoAreas/MunicAreas)
            # is reconstructed by parsing opaque BaseJSON fields
            # (crossedBiomesList/crossedStatesList/crossedCitiesList),
            # whose internal format isn't guaranteed by the schema. The
            # alert's official total (crossedBiomesArea/crossedStatesArea/
            # crossedCitiesArea) is reliable; here we check whether the
            # breakdown sum matches that total, to detect (instead of
            # silently assuming) a possible format mismatch.
            for category_label, names_field, total_field, api_area_field in (
                ("Bioma", "crossedBiomes", "BiomaAreaHa", "crossedBiomesArea"),
                ("Estado", "crossedStates", "EstadoAreaHa", "crossedStatesArea"),
                ("Municipio", "crossedCities", "MunicAreaHa", "crossedCitiesArea"),
            ):
                authoritative = alert.get(api_area_field)
                if authoritative is None:
                    continue
                try:
                    authoritative = float(authoritative)
                except (TypeError, ValueError):
                    continue
                territory_names = MapBiomasApiClient.value_list(
                    alert.get(names_field)
                )
                if len(territory_names) <= 1:
                    # With a single territory there's no breakdown to
                    # check; the total is already that territory's area.
                    continue
                divided_sum = properties.get(total_field) or 0.0
                tolerance = max(0.01, 0.005 * authoritative)
                if abs(float(divided_sum) - authoritative) > tolerance:
                    QgsMessageLog.logMessage(
                        (
                            "Alert {}: the split by {} does not match the "
                            "total area reported by the API ({:.4f} ha "
                            "summed vs. {:.4f} ha official). This alert's "
                            "individual values for {} may be "
                            "incorrect.".format(
                                alert.get("alertCode") or "no code",
                                category_label,
                                float(divided_sum),
                                authoritative,
                                category_label,
                            )
                        ),
                        "MapBiomas Alerta Oficial",
                        Qgis.Warning,
                    )
            detected = MapBiomasApiClient.parse_date(alert.get("detectedAt"))
            published = MapBiomasApiClient.parse_date(alert.get("publishedAt"))
            reference = (
                published
                if period_type == MapBiomasApiClient.PERIOD_PUBLICATION
                else detected
            ) or detected or published
            properties["Ano"] = reference.year if reference else None
            properties["Mes"] = reference.month if reference else None
            properties["AnoMes"] = (
                reference.strftime("%Y-%m") if reference else ""
            )
            for api_field, (output_field, numeric) in (
                MapBiomasApiClient.ANALYTIC_FIELDS.items()
            ):
                if api_field not in alert:
                    continue
                value = alert.get(api_field)
                properties[output_field] = (
                    value
                    if numeric
                    else MapBiomasApiClient.join_values(value)
                )
                if not numeric:
                    area_map = MapBiomasApiClient.territory_areas_json(value)
                    if area_map:
                        properties["{}Areas".format(output_field)] = area_map
            for api_field, (label_field, area_field) in (
                MapBiomasApiClient.AREA_MAP_FIELDS.items()
            ):
                area_map = MapBiomasApiClient.territory_areas_json(
                    alert.get(api_field), category_hint=label_field
                )
                if not area_map:
                    continue
                properties[area_field] = area_map
                parsed_area_map = json.loads(area_map)
                properties[label_field] = "; ".join(parsed_area_map.keys())
                # Unlike Biome/State/City (non-overlapping partitions),
                # the platform itself warns that the crossing list counts
                # each declaration (Conservation Unit, Indigenous Land,
                # Settlement, Quilombo, Biosphere Reserve, Geopark,
                # Permanent Protected Area, Legal Reserve) individually,
                # WITHOUT removing overlaps between different
                # declarations. So the sum can legitimately exceed the
                # total when the crossed territories overlap — that's not
                # an error. This log is purely informational (it never
                # discards the individual values, which keep being used).
                authoritative_field = (
                    MapBiomasApiClient.AREA_MAP_AUTHORITATIVE_TOTALS.get(
                        api_field
                    )
                )
                if authoritative_field and len(parsed_area_map) > 1:
                    authoritative = alert.get(authoritative_field)
                    try:
                        authoritative = (
                            float(authoritative)
                            if authoritative is not None
                            else None
                        )
                    except (TypeError, ValueError):
                        authoritative = None
                    if authoritative is not None:
                        divided_sum = sum(parsed_area_map.values())
                        tolerance = max(0.01, 0.005 * authoritative)
                        if abs(divided_sum - authoritative) > tolerance:
                            QgsMessageLog.logMessage(
                                (
                                    "Alert {}: the sum of the split by {} "
                                    "({:.4f} ha) differs from the total "
                                    "reported by the API ({:.4f} ha). This "
                                    "can be normal when the crossed "
                                    "territories of this category overlap "
                                    "each other (the platform does not "
                                    "remove overlaps between "
                                    "declarations); individual values "
                                    "are still shown.".format(
                                        alert.get("alertCode")
                                        or "no code",
                                        label_field,
                                        divided_sum,
                                        authoritative,
                                    )
                                ),
                                "MapBiomas Alerta Oficial",
                                Qgis.Info,
                            )
            for label_field, (total_field, area_field) in (
                MapBiomasApiClient.TERRITORY_AREA_PAIRS.items()
            ):
                if properties.get(area_field):
                    continue
                labels = MapBiomasApiClient.value_list(
                    properties.get(label_field)
                )
                if len(labels) != 1:
                    continue
                try:
                    total = float(properties.get(total_field) or 0)
                except (TypeError, ValueError):
                    continue
                if total > 0:
                    properties[area_field] = json.dumps(
                        {labels[0]: total}, ensure_ascii=False,
                        separators=(",", ":"),
                    )
            alert_intersections = alert.get("alertIntersections")
            if alert_intersections:
                # New, unified field (see ALERT_INTERSECTIONS_FIELDS) —
                # stored as raw JSON, one per alert, also covering the
                # per-country configurable crossing types that the
                # crossed*/AREA_MAP_FIELDS fields above never capture.
                # Available in the "Full attribute table" and used as the
                # basis for the chart grouping by crossing type.
                properties["CruzamentosJson"] = json.dumps(
                    [
                        {
                            "type": entry.get("type"),
                            "name": entry.get("name"),
                            "totalAreaHa": entry.get("totalAreaHa"),
                            "names": entry.get("names") or [],
                        }
                        for entry in alert_intersections
                        if entry.get("totalAreaHa") not in (None, 0, 0.0)
                        or entry.get("names")
                    ],
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            features.append(
                {
                    "type": "Feature",
                    "geometry": json.loads(geometry.asJson()),
                    "properties": properties,
                }
            )
        document = {"type": "FeatureCollection", "features": features}
        if return_stats:
            return document, skipped_geometry_codes
        return document

    @staticmethod
    def reconcile_conservation_unit_areas(alert):
        """Fallback for when crossedConservationUnitsList (confirmed to
        exist in the API, added to AREA_MAP_FIELDS) came back empty for
        the alert. Tries to reconstruct each crossed Conservation Unit's
        individual area by crossing the 6 integral protection/sustainable
        use sublayers (federal/state/municipal). Only returns a result
        when it covers exactly the same names as
        crossedConservationUnits and the sum matches the official total
        area (crossedConservationUnitsArea) — otherwise returns None, and
        the alert stays without a per-unit breakdown (instead of a
        partial or incorrect one). Since AREA_MAP_FIELDS is processed
        after this method in to_geojson(), the direct field takes
        priority and overrides this result whenever it's available."""
        uc_names = set(
            MapBiomasApiClient.value_list(alert.get("crossedConservationUnits"))
        )
        if len(uc_names) <= 1:
            # No ambiguity to resolve; the single-name fallback already
            # handles this case elsewhere.
            return None
        authoritative = alert.get("crossedConservationUnitsArea")
        try:
            authoritative = (
                float(authoritative) if authoritative is not None else None
            )
        except (TypeError, ValueError):
            authoritative = None
        if authoritative is None:
            return None

        candidate = {}
        for names_field, area_field in (
            MapBiomasApiClient.CONSERVATION_UNIT_SUBLAYERS
        ):
            names = MapBiomasApiClient.value_list(alert.get(names_field))
            if len(names) != 1:
                # Ambiguous sublayer (0 or 2+ names) can't be used to
                # assign an area to a specific name.
                continue
            name = names[0]
            if name not in uc_names:
                # Name outside this alert's general Conservation Unit
                # list; shouldn't happen, but we skip it as a safeguard.
                continue
            try:
                area = float(alert.get(area_field))
            except (TypeError, ValueError):
                continue
            candidate[name] = candidate.get(name, 0.0) + area

        if set(candidate.keys()) != uc_names:
            # We didn't cover all crossed names; an incomplete breakdown
            # isn't published.
            return None
        divided_sum = sum(candidate.values())
        tolerance = max(0.01, 0.005 * authoritative)
        if abs(divided_sum - authoritative) > tolerance:
            return None
        return candidate

    @staticmethod
    def join_values(value):
        if value is None:
            return ""
        if not isinstance(value, (list, tuple)):
            return str(value)
        labels = []
        for item in value:
            if isinstance(item, dict):
                label = (
                    item.get("name")
                    or item.get("value")
                    or item.get("label")
                    or item.get("code")
                )
                labels.append(str(label if label is not None else item))
            else:
                labels.append(str(item))
        # Canonical, unambiguous separator for multivalued fields. A comma
        # could be part of a territory's own name.
        return "; ".join(labels)

    @staticmethod
    def value_list(value):
        if value is None:
            return []
        if isinstance(value, (list, tuple)):
            result = []
            for item in value:
                rendered = MapBiomasApiClient.join_values([item]).strip()
                if rendered:
                    result.append(rendered)
            return result
        text = str(value).strip()
        if not text:
            return []
        try:
            decoded = json.loads(text)
        except (TypeError, ValueError, json.JSONDecodeError):
            decoded = None
        if isinstance(decoded, list):
            return MapBiomasApiClient.value_list(decoded)
        # Read compatibility: new layers use ';', while previously
        # generated layers used a comma.
        separator = ";" if ";" in text else "," if "," in text else None
        if separator is None:
            return [text]
        return [item.strip() for item in text.split(separator) if item.strip()]

    @staticmethod
    def territory_areas_json(value, category_hint=None):
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except (TypeError, ValueError):
                return ""

        result = {}

        def add(name, area):
            name = str(name or "").strip()
            if not name:
                return
            try:
                result[name] = result.get(name, 0.0) + float(area)
            except (TypeError, ValueError):
                return

        def visit(item):
            if isinstance(item, list):
                for child in item:
                    visit(child)
                return
            if not isinstance(item, dict):
                return

            name = next(
                (
                    item.get(key)
                    for key in (
                        "name", "label", "territoryName",
                        "city", "state", "biome",
                    )
                    if item.get(key) not in (None, "")
                ),
                None,
            )
            territory = item.get("territory")
            if name is None and isinstance(territory, dict):
                name = next(
                    (
                        territory.get(key)
                        for key in ("name", "label", "city", "state", "biome")
                        if territory.get(key) not in (None, "")
                    ),
                    None,
                )
            area = next(
                (
                    item.get(key)
                    for key in (
                        "areaHa", "area_ha", "area",
                        "crossedArea", "intersectionArea", "alertArea",
                        # Format of Permanent Protected Area/Legal Reserve
                        # items (crossedPermanentProtectedAreaList/
                        # crossedLegalReservesList): comes in snake_case,
                        # doesn't match the camelCase keys above.
                        "intersection_area",
                    )
                    if item.get(key) is not None
                ),
                None,
            )
            if name is None:
                # No readable name (only id + version + area): use the id
                # as identifier, but never let the version become a
                # separate "territory" (see generic fallback below).
                id_key = next(
                    (key for key in item if key.endswith("_id")), None
                )
                if id_key is not None and item.get(id_key) is not None:
                    name = "{} {}".format(category_hint or "Área", item[id_key])
            if name is not None and area is not None:
                add(name, area)
                return
            if any(key.endswith("_version") for key in item):
                # Item recognized as the id/version/area format, but with
                # no usable name or area (e.g. a version without
                # intersection_area) — better to show nothing than show
                # the version as if it were an area.
                return

            for key, child in item.items():
                if isinstance(child, (int, float, str)):
                    add(key, child)
                elif isinstance(child, (dict, list)):
                    visit(child)

        visit(value)
        return (
            json.dumps(result, ensure_ascii=False, separators=(",", ":"))
            if result
            else ""
        )

    @staticmethod
    def territory_area_total(value):
        """Return the numeric sum represented by a territory-area mapping."""
        document = MapBiomasApiClient.territory_areas_json(value)
        if not document:
            return 0.0
        try:
            values = json.loads(document)
        except (TypeError, ValueError, json.JSONDecodeError):
            return 0.0
        total = 0.0
        for area in values.values() if isinstance(values, dict) else []:
            try:
                total += float(area or 0)
            except (TypeError, ValueError):
                continue
        return total

    @staticmethod
    def image_type(image):
        values = [
            str(image.get(key) or "").strip()
            for key in ("constellation", "satellite")
        ]
        return " / ".join(value.upper() for value in values if value)

    @staticmethod
    def parse_date(value):
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value)[:10])
        except ValueError:
            return None

    @staticmethod
    def save_temporary_geojson(document):
        temporary_file = tempfile.NamedTemporaryFile(
            prefix="mapbiomas_alertas_api_",
            suffix=".geojson",
            delete=False,
        )
        path = temporary_file.name
        temporary_file.close()
        try:
            with open(path, "w", encoding="utf-8") as output:
                json.dump(document, output, ensure_ascii=False)
        except Exception:
            if os.path.exists(path):
                os.remove(path)
            raise
        atexit.register(MapBiomasApiClient.remove_temporary_file, path)
        return path

    @staticmethod
    def remove_temporary_file(path):
        if path and os.path.exists(path):
            try:
                os.remove(path)
                return True
            except OSError:
                return False
        return True
