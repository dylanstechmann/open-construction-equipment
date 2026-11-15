# SPDX-License-Identifier: Apache-2.0
"""Privacy-preserving synthetic rural geohazard screening and adaptation.

All geometry is relative to an unnamed origin. The calculations are concept
screens, not surveys, parcel recommendations, permit determinations, engineering
designs, physical validation, or authorization for construction or operation.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from enum import StrEnum
import json
import math
from pathlib import Path
import re
from typing import Any, Sequence

from .config import ConfigError, _keys, _mapping, _number, _string, load_json
from .geometry import Point, is_simple_polygon, point_in_polygon, point_segment_distance
from .physics import (
    STANDARD_GRAVITY_MPS2,
    _at_least,
    _below,
    _finite,
    _parse_provenance,
    _product,
    _sum,
    bounded_fraction,
    checked_divide,
)

PLATFORM_ID = "OCE-CTL-01"
SCOPE_ID = "BUNKER-01"
UNIT_SYSTEM_ID = "SI"
SCHEMA_VERSION = "1.0.0"


class RiskLevel(StrEnum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    UNKNOWN = "UNKNOWN"


class ScreeningDecision(StrEnum):
    RELATIVE_CANDIDATE = "RELATIVE_" + "CANDIDATE"
    ENGINEERING_REVIEW = "ENGINEERING_" + "REVIEW"
    REJECT_ON_MODELED_CONSTRAINT = "REJECT_ON_" + "MODELED_CONSTRAINT"


class PermitFinding(StrEnum):
    EXEMPTION_CANDIDATE = "EXEMPTION_" + "CANDIDATE"
    TRIGGERED = "TRIGGERED"
    AHJ_CONFIRMATION_REQUIRED = "AHJ_CONFIRMATION_" + "REQUIRED"


class ConstructionStrategy(StrEnum):
    DEEP_CUT_AND_COVER = "DEEP_CUT_AND_COVER"
    SEMI_BURIED_EARTH_BERMED_MOUND = "SEMI_BURIED_" + "EARTH_BERMED_MOUND"


class FoundationStrategy(StrEnum):
    STRIP_CONCEPT_ONLY = "STRIP_CONCEPT_" + "ONLY"
    STIFFENED_CELLULAR_RAFT_ON_GEOGRID = "STIFFENED_CELLULAR_" + "RAFT_ON_GEOGRID"
    SPECIALIST_DESIGN_TBD = "SPECIALIST_" + "DESIGN_TBD"


class AdaptationKind(StrEnum):
    SHALLOW_MOUND = "SHALLOW_MOUND"
    CELLULAR_RAFT = "CELLULAR_RAFT"
    ANTI_FLOTATION_COLLAR = "ANTI_FLOTATION_" + "COLLAR"
    REDUNDANT_SOLAR_DRAINAGE = "REDUNDANT_SOLAR_" + "DRAINAGE"
    PRIVACY_SPOIL_BERM = "PRIVACY_SPOIL_" + "BERM"
    WATERWAY_SETBACK = "WATERWAY_" + "SETBACK"
    ACCESS_REVIEW = "ACCESS_REVIEW"


class HumanDiscipline(StrEnum):
    GEOTECHNICAL = "GEOTECHNICAL"
    STRUCTURAL = "STRUCTURAL"
    EXCAVATION = "EXCAVATION"
    HYDROLOGY = "HYDROLOGY"
    ENVIRONMENTAL = "ENVIRONMENTAL"
    PERMIT_AHJ = "PERMIT_AHJ"
    ROAD_ACCESS = "ROAD_ACCESS"
    ELECTRICAL = "ELECTRICAL"
    PRIVACY_NOISE = "PRIVACY_NOISE"


@dataclass(frozen=True)
class LocalPoint:
    x_m: float
    y_m: float


@dataclass(frozen=True)
class LocalFeature:
    feature_label: str
    kind: str
    vertices_local_m: tuple[LocalPoint, ...]
    required_setback_m: float


@dataclass(frozen=True)
class KarstProfile:
    closed_depression_distance_m: float
    closed_depression_review_distance_m: float
    karst_bedrock_depth_m: float | None
    karst_depth_review_threshold_m: float
    subsidence_risk: RiskLevel


@dataclass(frozen=True)
class WaterProfile:
    groundwater_depth_m: float | None
    groundwater_review_depth_m: float
    nearest_waterway_distance_m: float | None
    nearest_wetland_distance_m: float | None
    flood_100yr_depth_m: float | None
    required_waterway_setback_m: float
    required_wetland_setback_m: float
    buoyancy_displaced_volume_m3: float
    resisting_mass_kg: float
    concrete_density_kg_m3: float
    water_density_kg_m3: float
    collar_submerged_fraction: float


@dataclass(frozen=True)
class SlopeProfile:
    slope_angle_rad: float
    expansive_clay_risk: RiskLevel
    land_shift_rate_mm_year: float
    land_shift_review_threshold_mm_year: float
    modeled_factor_of_safety: float | None
    required_factor_of_safety: float


@dataclass(frozen=True)
class ClimateProfile:
    mean_daily_insolation_kwh_m2_day: float
    minimum_insolation_kwh_m2_day: float
    winter_design_temperature_c: float
    minimum_winter_temperature_c: float
    annual_precipitation_mm: float


@dataclass(frozen=True)
class PermitProfile:
    rural_unincorporated: bool
    agricultural_accessory_candidate: bool
    nonhabitable_utility_structure: bool
    ground_disturbance_m2: float
    swppp_trigger_area_m2: float
    well_or_septic_work: bool
    new_driveway_culvert: bool
    ahj_determination_obtained: bool


@dataclass(frozen=True)
class RoadAccessProfile:
    lowest_route_axle_limit_kg: float | None
    maximum_transport_axle_load_kg: float
    minimum_overhead_clearance_m: float | None
    transport_height_m: float
    required_overhead_clearance_m: float


@dataclass(frozen=True)
class PrivacyProfile:
    nearest_sightline_distance_m: float
    receiver_target_dba: float
    ambient_dba: float
    source_dba_at_15m: float
    privacy_berm_length_m: float
    privacy_berm_cross_section_m2: float
    required_visual_screen_height_m: float
    available_compacted_spoil_m3: float


@dataclass(frozen=True)
class SiteFactors:
    features: tuple[LocalFeature, ...]
    karst: KarstProfile
    water: WaterProfile
    slope: SlopeProfile
    climate: ClimateProfile
    permits: PermitProfile
    road: RoadAccessProfile
    privacy: PrivacyProfile


@dataclass(frozen=True)
class CandidateParcel:
    anonymous_label: str
    factors: SiteFactors


@dataclass(frozen=True)
class AdaptationAssumption:
    kind: AdaptationKind
    cost_delta: float
    schedule_delta_h: float
    labor_delta_h: float
    basis: str


@dataclass(frozen=True)
class ExistingSite:
    anonymous_label: str
    factors: SiteFactors
    baseline_excavation_depth_m: float
    baseline_foundation: FoundationStrategy
    baseline_strategy: ConstructionStrategy
    baseline_cost: float
    baseline_schedule_h: float
    cost_currency: str
    anti_flotation_required_factor: float
    adaptation_assumptions: tuple[AdaptationAssumption, ...]


@dataclass(frozen=True)
class HumanGate:
    gate_id: str
    discipline: HumanDiscipline
    required_evidence: str
    status: str


@dataclass(frozen=True)
class RiskAssessment:
    domain: str
    level: RiskLevel
    metric_value: float | None
    threshold: float | None
    reason: str
    required_gate_ids: tuple[str, ...]


@dataclass(frozen=True)
class PermitAssessment:
    topic: str
    finding: PermitFinding
    reason: str
    ahj_gate_id: str


@dataclass(frozen=True)
class ParcelAssessment:
    anonymous_label: str
    decision: ScreeningDecision
    risks: tuple[RiskAssessment, ...]
    permits: tuple[PermitAssessment, ...]
    road_access_review_required: bool
    privacy_berm_volume_m3: float
    unresolved_gate_ids: tuple[str, ...]


@dataclass(frozen=True)
class ScreeningResult:
    mode: str
    parcels: tuple[ParcelAssessment, ...]
    human_gates: tuple[HumanGate, ...]
    purchase_recommendation_made: bool = False
    location_data_retained: bool = False
    physical_validation_performed: bool = False


@dataclass(frozen=True)
class CostScheduleDelta:
    adaptation_id: str
    cost_delta: float
    schedule_delta_h: float
    labor_delta_h: float
    currency: str
    basis: str


@dataclass(frozen=True)
class EngineeringAdaptation:
    adaptation_id: str
    kind: AdaptationKind
    trigger_reason: str
    construction_strategy: ConstructionStrategy
    foundation_strategy: FoundationStrategy
    anti_flotation_deadweight_volume_m3: float
    redundant_solar_sump_count: int
    privacy_berm_volume_m3: float
    delta: CostScheduleDelta
    required_gate_ids: tuple[str, ...]


@dataclass(frozen=True)
class AdaptationResult:
    mode: str
    anonymous_label: str
    adaptations: tuple[EngineeringAdaptation, ...]
    baseline_cost: float
    total_cost_delta: float
    baseline_schedule_h: float
    total_schedule_delta_h: float
    currency: str
    human_gate_ids: tuple[str, ...]
    human_gates: tuple[HumanGate, ...]
    construction_authorized: bool = False
    site_engineering_complete: bool = False
    location_data_retained: bool = False
    physical_validation_performed: bool = False


# Key matching is token based: "translation_m" and "stipulation" are safe,
# whereas "siteLatitude", "parcelId", and "street-address" are not.
_FORBIDDEN_KEY_PARTS = frozenset({
    "latitude", "longitude", "lat", "lon", "gps", "gnss", "geohash",
    "street", "address", "postcode", "postal", "zip", "apn", "assessor", "deed",
    "location", "coordinates", "coordinate", "lng",
})
_FORBIDDEN_KEY_PHRASES = (
    "plus_code", "parcel_id", "tax_id", "legal_location", "real_property_id",
    "property_id", "owner_name",
)
_PRIVATE_TEXT_PATTERNS = (
    re.compile(r"\bapn\b", re.I),
    re.compile(r"\bassessor(?:'s|s)?\b", re.I),
    re.compile(r"\bparcel[\s_-]*(?:id|identifier|number|no\.?)\b", re.I),
    re.compile(r"\btax[\s_-]*(?:id|identifier|identification(?:[\s_-]+number)?)\b", re.I),
    re.compile(r"\bdeed\b", re.I),
    re.compile(
        r"\b(?:lot|block)[\s_-]*(?:id|identifier|number|no\.?|#)"
        r"[\s:_-]*[a-z0-9-]+\b", re.I,
    ),
    re.compile(r"\b(?:lot|block)[\s_-]+\d+[a-z]?\b", re.I),
    re.compile(r"\b(?:lat|latitude|lon|lng|longitude)\s*[:=]\s*[+-]?(?:\d+(?:\.\d+)?|\.\d+)", re.I),
    re.compile(r"\b(?:gps|gnss)\b[^\n]{0,100}[+-]?\d", re.I),
    re.compile(r"\b(?:geohash|plus\s+code|open\s+location\s+code)\b", re.I),
    re.compile(r"\b[23456789CFGHJMPQRVWX]{4,}\+[23456789CFGHJMPQRVWX]{2,}\b", re.I),
    re.compile(r"[?&](?:lat|latitude|lon|lng|longitude|gps|gnss|geohash|mlat|mlon)=", re.I),
    re.compile(r"[?&](?:q|query|destination|origin)=[^&\s]*[+-]?\d+(?:\.\d+)?(?:%2C|,)", re.I),
    re.compile(
        r"\b\d{1,6}\s+(?:[A-Za-z0-9.'-]+\s+){0,5}"
        r"(?:street|st|road|rd|avenue|ave|boulevard|blvd|lane|ln|drive|dr|court|ct|"
        r"terrace|ter|parkway|pkwy|highway|hwy|way|place|pl)\b", re.I,
    ),
    re.compile(r"\bP\.?\s*O\.?\s*Box\s+\d+\b", re.I),
    re.compile(
        r"(?<![\d.])[+-]?(?:[0-8]?\d\.\d{4,}|90\.0{4,})\s*,\s*"
        r"[+-]?(?:(?:1[0-7]\d|\d?\d)\.\d{4,}|180\.0{4,})(?![\d.])",
    ),
    re.compile(r"\b[+-]?\d+(?:\.\d+)?\s*[NS]\s*[,;]\s*[+-]?\d+(?:\.\d+)?\s*[EW]\b", re.I),
)


def _normalized_key(key: str) -> str:
    value = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", key)
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    return re.sub(r"_+", "_", re.sub(r"[^A-Za-z0-9]+", "_", value)).strip("_").lower()


def reject_private_location_data(value: Any, path: str = "site") -> None:
    """Fail closed on raw location identifiers, coordinates, and postal text."""

    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ConfigError(f"{path} contains a non-string object key")
            normalized = _normalized_key(key)
            tokens = set(normalized.split("_"))
            if tokens & _FORBIDDEN_KEY_PARTS or any(
                re.search(rf"(?:^|_){re.escape(phrase)}(?:_|$)", normalized)
                for phrase in _FORBIDDEN_KEY_PHRASES
            ):
                raise ConfigError(f"{path}.{key} contains prohibited private location data")
            reject_private_location_data(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            reject_private_location_data(item, f"{path}[{index}]")
    elif isinstance(value, str):
        for pattern in _PRIVATE_TEXT_PATTERNS:
            if pattern.search(value):
                raise ConfigError(f"{path} contains prohibited location or property-identifier text")


def _boolean(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigError(f"{name} must be a boolean")
    return value


def _optional_number(data: dict[str, Any], key: str, name: str, low: float = 0,
                     strict_low: bool = False) -> float | None:
    if data[key] is None:
        return None
    return _number(data, key, name, low, strict_low=strict_low)


def _enum_value(value: Any, enum_type: type[StrEnum], name: str) -> Any:
    if not isinstance(value, str):
        raise ConfigError(f"{name} must be a string")
    try:
        return enum_type(value)
    except ValueError as exc:
        raise ConfigError(f"{name} has unsupported value {value!r}") from exc


def _point(value: Any, name: str) -> LocalPoint:
    data = _mapping(value, name)
    _keys(data, {"x_m", "y_m"}, set(), name)
    return LocalPoint(_number(data, "x_m", name), _number(data, "y_m", name))


_LINE_KINDS = frozenset({"WATERWAY", "ROAD", "SIGHTLINE"})
_AREA_KINDS = frozenset({"WETLAND", "CLOSED_" + "DEPRESSION", "STRUCTURE"})


def _validate_feature(model: LocalFeature, name: str = "feature") -> None:
    if not isinstance(model, LocalFeature):
        raise ConfigError(f"{name} must be LocalFeature")
    if not isinstance(model.feature_label, str) or re.fullmatch(r"FEATURE-[A-Z0-9-]+", model.feature_label) is None:
        raise ConfigError(f"{name}.feature_label must match FEATURE-[A-Z0-9-]+")
    if model.kind not in _LINE_KINDS | _AREA_KINDS:
        raise ConfigError(f"{name}.kind is not supported")
    if not isinstance(model.vertices_local_m, tuple):
        raise ConfigError(f"{name}.vertices_local_m must be a tuple")
    for index, vertex in enumerate(model.vertices_local_m):
        if not isinstance(vertex, LocalPoint):
            raise ConfigError(f"{name}.vertices_local_m[{index}] must be LocalPoint")
        _finite(vertex.x_m, f"{name}.vertices_local_m[{index}].x_m")
        _finite(vertex.y_m, f"{name}.vertices_local_m[{index}].y_m")
    _at_least(model.required_setback_m, 0, f"{name}.required_setback_m")
    points = tuple(Point(vertex.x_m, vertex.y_m) for vertex in model.vertices_local_m)
    if model.kind in _LINE_KINDS:
        if len(points) != 2:
            raise ConfigError(f"{name} line geometry must have exactly two vertices")
        if points[0].distance(points[1]) == 0:
            raise ConfigError(f"{name} line geometry must have nonzero length")
    else:
        if len(points) < 3 or not is_simple_polygon(points):
            raise ConfigError(f"{name} area geometry must be a simple polygon with at least three vertices")
        twice_area = abs(sum(
            start.x * end.y - end.x * start.y
            for start, end in zip(points, points[1:] + points[:1])
        ))
        if not math.isfinite(twice_area) or twice_area == 0:
            raise ConfigError(f"{name} area geometry must have finite nonzero area")


def _feature(value: Any, name: str) -> LocalFeature:
    data = _mapping(value, name)
    _keys(data, {"featureLabel", "kind", "vertices_local_m", "requiredSetback_m"}, set(), name)
    raw_vertices = data["vertices_local_m"]
    if not isinstance(raw_vertices, list):
        raise ConfigError(f"{name}.vertices_local_m must be an array")
    model = LocalFeature(
        feature_label=_string(data, "featureLabel", name),
        kind=_string(data, "kind", name),
        vertices_local_m=tuple(
            _point(item, f"{name}.vertices_local_m[{index}]") for index, item in enumerate(raw_vertices)
        ),
        required_setback_m=_number(data, "requiredSetback_m", name, 0),
    )
    _validate_feature(model, name)
    return model


def _validate_karst(model: KarstProfile) -> None:
    if not isinstance(model, KarstProfile):
        raise ConfigError("karst must be KarstProfile")
    _at_least(model.closed_depression_distance_m, 0, "closed_depression_distance_m")
    _at_least(model.closed_depression_review_distance_m, 0, "closed_depression_review_distance_m")
    if model.karst_bedrock_depth_m is not None:
        _at_least(model.karst_bedrock_depth_m, 0, "karst_bedrock_depth_m")
    _at_least(model.karst_depth_review_threshold_m, 0, "karst_depth_review_threshold_m")
    if not isinstance(model.subsidence_risk, RiskLevel):
        raise ConfigError("subsidence_risk must be RiskLevel")


def _karst(value: Any, name: str) -> KarstProfile:
    data = _mapping(value, name)
    names = {
        "closedDepressionDistance_m", "closedDepressionReviewDistance_m", "karstBedrockDepth_m",
        "karstDepthReviewThreshold_m", "subsidenceRisk",
    }
    _keys(data, names, set(), name)
    model = KarstProfile(
        _number(data, "closedDepressionDistance_m", name, 0),
        _number(data, "closedDepressionReviewDistance_m", name, 0),
        _optional_number(data, "karstBedrockDepth_m", name),
        _number(data, "karstDepthReviewThreshold_m", name, 0),
        _enum_value(data["subsidenceRisk"], RiskLevel, f"{name}.subsidenceRisk"),
    )
    _validate_karst(model)
    return model


def _validate_water(model: WaterProfile) -> None:
    if not isinstance(model, WaterProfile):
        raise ConfigError("water must be WaterProfile")
    for field_name in (
        "groundwater_depth_m", "nearest_waterway_distance_m", "nearest_wetland_distance_m",
        "flood_100yr_depth_m",
    ):
        item = getattr(model, field_name)
        if item is not None:
            _at_least(item, 0, field_name)
    for field_name in (
        "groundwater_review_depth_m", "required_waterway_setback_m", "required_wetland_setback_m",
        "buoyancy_displaced_volume_m3", "resisting_mass_kg",
    ):
        _at_least(getattr(model, field_name), 0, field_name)
    _at_least(model.concrete_density_kg_m3, 0, "concrete_density_kg_m3", strict=True)
    _at_least(model.water_density_kg_m3, 0, "water_density_kg_m3", strict=True)
    bounded_fraction(model.collar_submerged_fraction, "collar_submerged_fraction")


def _water(value: Any, name: str) -> WaterProfile:
    data = _mapping(value, name)
    names = {
        "groundwaterDepth_m", "groundwaterReviewDepth_m", "nearestWaterwayDistance_m",
        "nearestWetlandDistance_m", "flood100yrDepth_m", "requiredWaterwaySetback_m",
        "requiredWetlandSetback_m", "buoyancyDisplacedVolume_m3", "resistingMass_kg",
        "concreteDensity_kg_m3", "waterDensity_kg_m3", "collarSubmergedFraction",
    }
    _keys(data, names, set(), name)
    model = WaterProfile(
        _optional_number(data, "groundwaterDepth_m", name),
        _number(data, "groundwaterReviewDepth_m", name, 0),
        _optional_number(data, "nearestWaterwayDistance_m", name),
        _optional_number(data, "nearestWetlandDistance_m", name),
        _optional_number(data, "flood100yrDepth_m", name),
        _number(data, "requiredWaterwaySetback_m", name, 0),
        _number(data, "requiredWetlandSetback_m", name, 0),
        _number(data, "buoyancyDisplacedVolume_m3", name, 0),
        _number(data, "resistingMass_kg", name, 0),
        _number(data, "concreteDensity_kg_m3", name, 0, strict_low=True),
        _number(data, "waterDensity_kg_m3", name, 0, strict_low=True),
        _number(data, "collarSubmergedFraction", name, 0, 1),
    )
    _validate_water(model)
    return model


def _validate_slope(model: SlopeProfile) -> None:
    if not isinstance(model, SlopeProfile):
        raise ConfigError("slope must be SlopeProfile")
    _at_least(model.slope_angle_rad, 0, "slope_angle_rad")
    _below(model.slope_angle_rad, math.pi / 2, "slope_angle_rad", strict=True)
    if not isinstance(model.expansive_clay_risk, RiskLevel):
        raise ConfigError("expansive_clay_risk must be RiskLevel")
    _at_least(model.land_shift_rate_mm_year, 0, "land_shift_rate_mm_year")
    _at_least(model.land_shift_review_threshold_mm_year, 0, "land_shift_review_threshold_mm_year")
    if model.modeled_factor_of_safety is not None:
        _at_least(model.modeled_factor_of_safety, 0, "modeled_factor_of_safety", strict=True)
    _at_least(model.required_factor_of_safety, 1, "required_factor_of_safety")


def _slope(value: Any, name: str) -> SlopeProfile:
    data = _mapping(value, name)
    names = {
        "slopeAngle_rad", "expansiveClayRisk", "landShiftRate_mm_year",
        "landShiftReviewThreshold_mm_year", "modeledFactorOfSafety", "requiredFactorOfSafety",
    }
    _keys(data, names, set(), name)
    model = SlopeProfile(
        _number(data, "slopeAngle_rad", name, 0),
        _enum_value(data["expansiveClayRisk"], RiskLevel, f"{name}.expansiveClayRisk"),
        _number(data, "landShiftRate_mm_year", name, 0),
        _number(data, "landShiftReviewThreshold_mm_year", name, 0),
        _optional_number(data, "modeledFactorOfSafety", name, 0, strict_low=True),
        _number(data, "requiredFactorOfSafety", name, 1),
    )
    _validate_slope(model)
    return model


def _validate_climate(model: ClimateProfile) -> None:
    if not isinstance(model, ClimateProfile):
        raise ConfigError("climate must be ClimateProfile")
    _at_least(model.mean_daily_insolation_kwh_m2_day, 0, "mean_daily_insolation_kwh_m2_day")
    _at_least(model.minimum_insolation_kwh_m2_day, 0, "minimum_insolation_kwh_m2_day")
    _at_least(model.winter_design_temperature_c, -273.15, "winter_design_temperature_c", strict=True)
    _at_least(model.minimum_winter_temperature_c, -273.15, "minimum_winter_temperature_c", strict=True)
    _at_least(model.annual_precipitation_mm, 0, "annual_precipitation_mm")


def _climate(value: Any, name: str) -> ClimateProfile:
    data = _mapping(value, name)
    names = {
        "meanDailyInsolation_kWh_m2_day", "minimumInsolation_kWh_m2_day",
        "winterDesignTemperature_C", "minimumWinterTemperature_C", "annualPrecipitation_mm",
    }
    _keys(data, names, set(), name)
    model = ClimateProfile(
        _number(data, "meanDailyInsolation_kWh_m2_day", name, 0),
        _number(data, "minimumInsolation_kWh_m2_day", name, 0),
        _number(data, "winterDesignTemperature_C", name, -273.15, strict_low=True),
        _number(data, "minimumWinterTemperature_C", name, -273.15, strict_low=True),
        _number(data, "annualPrecipitation_mm", name, 0),
    )
    _validate_climate(model)
    return model


def _validate_permits(model: PermitProfile) -> None:
    if not isinstance(model, PermitProfile):
        raise ConfigError("permits must be PermitProfile")
    for field_name in (
        "rural_unincorporated", "agricultural_accessory_candidate", "nonhabitable_utility_structure",
        "well_or_septic_work", "new_driveway_culvert", "ahj_determination_obtained",
    ):
        _boolean(getattr(model, field_name), field_name)
    if model.ahj_determination_obtained is not False:
        raise ConfigError("ahj_determination_obtained must be false in this release")
    _at_least(model.ground_disturbance_m2, 0, "ground_disturbance_m2")
    _at_least(model.swppp_trigger_area_m2, 0, "swppp_trigger_area_m2", strict=True)


def _permits(value: Any, name: str) -> PermitProfile:
    data = _mapping(value, name)
    names = {
        "ruralUnincorporated", "agriculturalAccessoryCandidate", "nonhabitableUtilityStructure",
        "groundDisturbance_m2", "swpppTriggerArea_m2", "wellOrSepticWork", "newDrivewayCulvert",
        "ahjDeterminationObtained",
    }
    _keys(data, names, set(), name)
    model = PermitProfile(
        _boolean(data["ruralUnincorporated"], f"{name}.ruralUnincorporated"),
        _boolean(data["agriculturalAccessoryCandidate"], f"{name}.agriculturalAccessoryCandidate"),
        _boolean(data["nonhabitableUtilityStructure"], f"{name}.nonhabitableUtilityStructure"),
        _number(data, "groundDisturbance_m2", name, 0),
        _number(data, "swpppTriggerArea_m2", name, 0, strict_low=True),
        _boolean(data["wellOrSepticWork"], f"{name}.wellOrSepticWork"),
        _boolean(data["newDrivewayCulvert"], f"{name}.newDrivewayCulvert"),
        _boolean(data["ahjDeterminationObtained"], f"{name}.ahjDeterminationObtained"),
    )
    _validate_permits(model)
    return model


def _validate_road(model: RoadAccessProfile) -> None:
    if not isinstance(model, RoadAccessProfile):
        raise ConfigError("road must be RoadAccessProfile")
    if model.lowest_route_axle_limit_kg is not None:
        _at_least(model.lowest_route_axle_limit_kg, 0, "lowest_route_axle_limit_kg", strict=True)
    _at_least(model.maximum_transport_axle_load_kg, 0, "maximum_transport_axle_load_kg", strict=True)
    if model.minimum_overhead_clearance_m is not None:
        _at_least(model.minimum_overhead_clearance_m, 0, "minimum_overhead_clearance_m", strict=True)
    _at_least(model.transport_height_m, 0, "transport_height_m", strict=True)
    _at_least(model.required_overhead_clearance_m, 0, "required_overhead_clearance_m")


def _road(value: Any, name: str) -> RoadAccessProfile:
    data = _mapping(value, name)
    names = {
        "lowestRouteAxleLimit_kg", "maximumTransportAxleLoad_kg", "minimumOverheadClearance_m",
        "transportHeight_m", "requiredOverheadClearance_m",
    }
    _keys(data, names, set(), name)
    model = RoadAccessProfile(
        _optional_number(data, "lowestRouteAxleLimit_kg", name, 0, strict_low=True),
        _number(data, "maximumTransportAxleLoad_kg", name, 0, strict_low=True),
        _optional_number(data, "minimumOverheadClearance_m", name, 0, strict_low=True),
        _number(data, "transportHeight_m", name, 0, strict_low=True),
        _number(data, "requiredOverheadClearance_m", name, 0),
    )
    _validate_road(model)
    return model


def _validate_privacy(model: PrivacyProfile) -> None:
    if not isinstance(model, PrivacyProfile):
        raise ConfigError("privacy must be PrivacyProfile")
    for field_name in (
        "nearest_sightline_distance_m", "receiver_target_dba", "ambient_dba", "source_dba_at_15m",
        "privacy_berm_length_m", "privacy_berm_cross_section_m2", "required_visual_screen_height_m",
        "available_compacted_spoil_m3",
    ):
        _at_least(getattr(model, field_name), 0, field_name)


def _privacy(value: Any, name: str) -> PrivacyProfile:
    data = _mapping(value, name)
    names = {
        "nearestSightlineDistance_m", "receiverTarget_dBA", "ambient_dBA", "sourceDbaAt15m",
        "privacyBermLength_m", "privacyBermCrossSection_m2", "requiredVisualScreenHeight_m",
        "availableCompactedSpoil_m3",
    }
    _keys(data, names, set(), name)
    model = PrivacyProfile(
        _number(data, "nearestSightlineDistance_m", name, 0),
        _number(data, "receiverTarget_dBA", name, 0),
        _number(data, "ambient_dBA", name, 0),
        _number(data, "sourceDbaAt15m", name, 0),
        _number(data, "privacyBermLength_m", name, 0),
        _number(data, "privacyBermCrossSection_m2", name, 0),
        _number(data, "requiredVisualScreenHeight_m", name, 0),
        _number(data, "availableCompactedSpoil_m3", name, 0),
    )
    _validate_privacy(model)
    return model


def _validate_factors(model: SiteFactors) -> None:
    if not isinstance(model, SiteFactors):
        raise ConfigError("factors must be SiteFactors")
    if not isinstance(model.features, tuple):
        raise ConfigError("features must be a tuple")
    labels = []
    for index, feature in enumerate(model.features):
        _validate_feature(feature, f"features[{index}]")
        labels.append(feature.feature_label)
    if len(set(labels)) != len(labels):
        raise ConfigError("feature labels must be unique")
    _validate_karst(model.karst)
    _validate_water(model.water)
    _validate_slope(model.slope)
    _validate_climate(model.climate)
    _validate_permits(model.permits)
    _validate_road(model.road)
    _validate_privacy(model.privacy)


def _factors(value: Any, name: str) -> SiteFactors:
    data = _mapping(value, name)
    names = {"features", "karst", "water", "slope", "climate", "permits", "road", "privacy"}
    _keys(data, names, set(), name)
    raw_features = data["features"]
    if not isinstance(raw_features, list):
        raise ConfigError(f"{name}.features must be an array")
    model = SiteFactors(
        tuple(_feature(item, f"{name}.features[{index}]") for index, item in enumerate(raw_features)),
        _karst(data["karst"], f"{name}.karst"),
        _water(data["water"], f"{name}.water"),
        _slope(data["slope"], f"{name}.slope"),
        _climate(data["climate"], f"{name}.climate"),
        _permits(data["permits"], f"{name}.permits"),
        _road(data["road"], f"{name}.road"),
        _privacy(data["privacy"], f"{name}.privacy"),
    )
    _validate_factors(model)
    return model


def _validate_candidate(model: CandidateParcel) -> None:
    if not isinstance(model, CandidateParcel):
        raise ConfigError("candidate must be CandidateParcel")
    if not isinstance(model.anonymous_label, str) or re.fullmatch(
        r"CANDIDATE-[A-Z0-9-]+", model.anonymous_label,
    ) is None:
        raise ConfigError("anonymous_label must match CANDIDATE-[A-Z0-9-]+")
    _validate_factors(model.factors)


def _candidate(value: Any, name: str) -> CandidateParcel:
    data = _mapping(value, name)
    _keys(data, {"anonymousLabel", "factors"}, set(), name)
    model = CandidateParcel(_string(data, "anonymousLabel", name), _factors(data["factors"], f"{name}.factors"))
    _validate_candidate(model)
    return model


def _validate_existing(model: ExistingSite) -> None:
    if not isinstance(model, ExistingSite):
        raise ConfigError("site must be ExistingSite")
    if model.anonymous_label != "EXISTING-SITE":
        raise ConfigError("anonymous_label must be EXISTING-SITE")
    _validate_factors(model.factors)
    _at_least(model.baseline_excavation_depth_m, 0, "baseline_excavation_depth_m", strict=True)
    if model.baseline_foundation is not FoundationStrategy.STRIP_CONCEPT_ONLY:
        raise ConfigError("baseline_foundation must be STRIP_CONCEPT_ONLY")
    if model.baseline_strategy is not ConstructionStrategy.DEEP_CUT_AND_COVER:
        raise ConfigError("baseline_strategy must be DEEP_CUT_AND_COVER")
    _at_least(model.baseline_cost, 0, "baseline_cost")
    _at_least(model.baseline_schedule_h, 0, "baseline_schedule_h")
    if not isinstance(model.cost_currency, str) or re.fullmatch(r"[A-Z]{3}", model.cost_currency) is None:
        raise ConfigError("cost_currency must match [A-Z]{3}")
    _at_least(model.anti_flotation_required_factor, 1, "anti_flotation_required_factor")
    if not isinstance(model.adaptation_assumptions, tuple):
        raise ConfigError("adaptation_assumptions must be a tuple")
    kinds = []
    for index, assumption in enumerate(model.adaptation_assumptions):
        if not isinstance(assumption, AdaptationAssumption):
            raise ConfigError(f"adaptation_assumptions[{index}] must be AdaptationAssumption")
        if not isinstance(assumption.kind, AdaptationKind):
            raise ConfigError(f"adaptation_assumptions[{index}].kind must be AdaptationKind")
        _finite(assumption.cost_delta, f"adaptation_assumptions[{index}].cost_delta")
        _finite(assumption.schedule_delta_h, f"adaptation_assumptions[{index}].schedule_delta_h")
        _finite(assumption.labor_delta_h, f"adaptation_assumptions[{index}].labor_delta_h")
        if not isinstance(assumption.basis, str) or not assumption.basis.strip():
            raise ConfigError(f"adaptation_assumptions[{index}].basis must be non-empty")
        kinds.append(assumption.kind)
    if len(set(kinds)) != len(kinds):
        raise ConfigError("adaptation assumption kinds must be unique")


def _adaptation_assumption(value: Any, name: str) -> AdaptationAssumption:
    data = _mapping(value, name)
    names = {"kind", "costDelta", "scheduleDelta_h", "laborDelta_h", "basis"}
    _keys(data, names, set(), name)
    return AdaptationAssumption(
        _enum_value(data["kind"], AdaptationKind, f"{name}.kind"),
        _number(data, "costDelta", name),
        _number(data, "scheduleDelta_h", name),
        _number(data, "laborDelta_h", name),
        _string(data, "basis", name),
    )


def _existing(value: Any, name: str) -> ExistingSite:
    data = _mapping(value, name)
    names = {
        "anonymousLabel", "factors", "baselineExcavationDepth_m", "baselineFoundation",
        "baselineStrategy", "baselineCost", "baselineSchedule_h", "costCurrency",
        "antiFlotationRequiredFactor", "adaptationAssumptions",
    }
    _keys(data, names, set(), name)
    raw_assumptions = data["adaptationAssumptions"]
    if not isinstance(raw_assumptions, list):
        raise ConfigError(f"{name}.adaptationAssumptions must be an array")
    model = ExistingSite(
        anonymous_label=_string(data, "anonymousLabel", name),
        factors=_factors(data["factors"], f"{name}.factors"),
        baseline_excavation_depth_m=_number(data, "baselineExcavationDepth_m", name, 0, strict_low=True),
        baseline_foundation=_enum_value(
            data["baselineFoundation"], FoundationStrategy, f"{name}.baselineFoundation",
        ),
        baseline_strategy=_enum_value(data["baselineStrategy"], ConstructionStrategy, f"{name}.baselineStrategy"),
        baseline_cost=_number(data, "baselineCost", name, 0),
        baseline_schedule_h=_number(data, "baselineSchedule_h", name, 0),
        cost_currency=_string(data, "costCurrency", name),
        anti_flotation_required_factor=_number(data, "antiFlotationRequiredFactor", name, 1),
        adaptation_assumptions=tuple(
            _adaptation_assumption(item, f"{name}.adaptationAssumptions[{index}]")
            for index, item in enumerate(raw_assumptions)
        ),
    )
    _validate_existing(model)
    return model


def _validate_envelope(data: dict[str, Any]) -> None:
    constants = {
        "spdxLicenseIdentifier": "CC-BY-SA-4.0",
        "schemaVersion": SCHEMA_VERSION,
        "platform": PLATFORM_ID,
        "scope": SCOPE_ID,
        "unitSystem": UNIT_SYSTEM_ID,
    }
    for key, expected in constants.items():
        if data.get(key) != expected:
            raise ConfigError(f"site.{key} must be {expected}")
    _string(data, "analysisId", "site")
    _parse_provenance(data.get("provenance"), "site.provenance")


def parse_geohazard_input(data: dict[str, Any]) -> CandidateParcel | ExistingSite | tuple[CandidateParcel, ...]:
    """Run the privacy boundary before parsing one exact screen/adapt envelope."""

    reject_private_location_data(data)
    envelope = _mapping(data, "site")
    common = {
        "spdxLicenseIdentifier", "schemaVersion", "platform", "scope", "unitSystem", "analysisId",
        "provenance", "mode",
    }
    mode = envelope.get("mode")
    if mode == "screen":
        _keys(envelope, common | {"candidates"}, set(), "site")
    elif mode == "adapt":
        _keys(envelope, common | {"site"}, set(), "site")
    else:
        raise ConfigError("site.mode must be screen or adapt")
    _validate_envelope(envelope)
    if mode == "screen":
        raw_candidates = envelope["candidates"]
        if not isinstance(raw_candidates, list) or not raw_candidates:
            raise ConfigError("site.candidates must be a non-empty array")
        candidates = tuple(
            _candidate(item, f"site.candidates[{index}]") for index, item in enumerate(raw_candidates)
        )
        labels = [candidate.anonymous_label for candidate in candidates]
        if len(set(labels)) != len(labels):
            raise ConfigError("candidate anonymous labels must be unique")
        return candidates
    return _existing(envelope["site"], "site.site")


def load_geohazard_input(path: str | Path) -> CandidateParcel | ExistingSite | tuple[CandidateParcel, ...]:
    return parse_geohazard_input(load_json(path))


def load_geohazard_document(path: str | Path) -> dict[str, Any]:
    """Load, validate, and preserve the complete metadata-bearing JSON envelope."""

    data = load_json(path)
    parse_geohazard_input(data)
    return data


def minimum_feature_distance(feature: LocalFeature) -> float:
    """Return distance from the anonymous local structure reference point (0, 0)."""

    _validate_feature(feature)
    points = tuple(Point(vertex.x_m, vertex.y_m) for vertex in feature.vertices_local_m)
    origin = Point(0.0, 0.0)
    try:
        if len(points) == 2:
            distance = point_segment_distance(origin, points[0], points[1])
        elif point_in_polygon(origin, points):
            return 0.0
        else:
            distance = min(
                point_segment_distance(origin, start, points[(index + 1) % len(points)])
                for index, start in enumerate(points)
            )
    except (OverflowError, ValueError) as exc:
        raise ConfigError("feature distance calculation failed") from exc
    return _finite(distance, "minimum feature distance")


_GATE_SPECS = (
    ("SG-001", HumanDiscipline.GEOTECHNICAL,
     "Qualified site investigation of soil, rock, karst, groundwater, expansive soil, and movement."),
    ("SG-002", HumanDiscipline.STRUCTURAL,
     "Signed structural review of foundation, mound, collar, and load-path concepts."),
    ("SG-003", HumanDiscipline.EXCAVATION,
     "Qualified excavation and protective-system review before any ground-disturbance planning."),
    ("SG-004", HumanDiscipline.HYDROLOGY,
     "Qualified flood, groundwater, buoyancy, and drainage review with site evidence."),
    ("SG-005", HumanDiscipline.ENVIRONMENTAL,
     "Environmental review of waterways, wetlands, grading, drainage, and spoil concepts."),
    ("SG-006", HumanDiscipline.PERMIT_AHJ,
     "Written authority-having-jurisdiction determinations for every candidate permit topic."),
    ("SG-007", HumanDiscipline.ROAD_ACCESS,
     "Documented route, axle, overhead-clearance, culvert, and transport access review."),
    ("SG-008", HumanDiscipline.ELECTRICAL,
     "Qualified review of solar pumps, battery backup, wiring, controls, and failure modes."),
    ("SG-009", HumanDiscipline.PRIVACY_NOISE,
     "Qualified visual, acoustic, spoil-placement, and neighboring-receiver review."),
)
_ALL_GATE_IDS = tuple(item[0] for item in _GATE_SPECS)


def _human_gates() -> tuple[HumanGate, ...]:
    return tuple(
        HumanGate(gate_id, discipline, evidence, "UNRESOLVED")
        for gate_id, discipline, evidence in _GATE_SPECS
    )


def _risk(domain: str, level: RiskLevel, metric: float | None, threshold: float | None,
          reason: str, gates: tuple[str, ...] = ()) -> RiskAssessment:
    if level is RiskLevel.UNKNOWN and not gates:
        raise ConfigError("unknown risks must identify a required human gate")
    return RiskAssessment(domain, level, metric, threshold, reason, gates)


def assess_risks(factors: SiteFactors) -> tuple[RiskAssessment, ...]:
    """Independently evaluate all declared risk domains without averaging them."""

    _validate_factors(factors)
    karst = factors.karst
    water = factors.water
    slope = factors.slope
    climate = factors.climate
    road = factors.road
    privacy = factors.privacy
    risks = []

    close = karst.closed_depression_distance_m <= karst.closed_depression_review_distance_m
    risks.append(_risk(
        "CLOSED_DEPRESSION", RiskLevel.HIGH if close else RiskLevel.LOW,
        karst.closed_depression_distance_m, karst.closed_depression_review_distance_m,
        "Closed depression is inside the declared review distance." if close
        else "Closed depression is beyond the declared review distance; this is not a site clearance.",
        ("SG-001",) if close else (),
    ))
    if karst.karst_bedrock_depth_m is None:
        risks.append(_risk("KARST_BEDROCK", RiskLevel.UNKNOWN, None, karst.karst_depth_review_threshold_m,
                           "Karst bedrock depth is unknown.", ("SG-001",)))
    else:
        shallow = karst.karst_bedrock_depth_m <= karst.karst_depth_review_threshold_m
        risks.append(_risk(
            "KARST_BEDROCK", RiskLevel.HIGH if shallow else RiskLevel.LOW,
            karst.karst_bedrock_depth_m, karst.karst_depth_review_threshold_m,
            "Karst bedrock is at or above the declared review threshold." if shallow
            else "Karst bedrock is below the declared review threshold; intrusive review remains unresolved.",
            ("SG-001",) if shallow else (),
        ))
    risks.append(_risk(
        "SUBSIDENCE", karst.subsidence_risk, None, None,
        "Declared subsidence risk is retained without normalization.",
        ("SG-001",) if karst.subsidence_risk is not RiskLevel.LOW else (),
    ))

    if water.groundwater_depth_m is None:
        risks.append(_risk("GROUNDWATER", RiskLevel.UNKNOWN, None, water.groundwater_review_depth_m,
                           "Groundwater depth is unknown.", ("SG-001", "SG-004")))
    else:
        shallow = water.groundwater_depth_m <= water.groundwater_review_depth_m
        risks.append(_risk(
            "GROUNDWATER", RiskLevel.HIGH if shallow else RiskLevel.LOW,
            water.groundwater_depth_m, water.groundwater_review_depth_m,
            "Groundwater is at or above the declared review depth." if shallow
            else "Groundwater is below the declared review depth; seasonal monitoring remains unresolved.",
            ("SG-001", "SG-004") if shallow else (),
        ))

    for domain, distance, setback in (
        ("WATERWAY_SETBACK", water.nearest_waterway_distance_m, water.required_waterway_setback_m),
        ("WETLAND_SETBACK", water.nearest_wetland_distance_m, water.required_wetland_setback_m),
    ):
        if distance is None:
            risks.append(_risk(domain, RiskLevel.UNKNOWN, None, setback,
                               "Professional feature distance is unknown.", ("SG-005", "SG-006")))
        elif distance < setback:
            risks.append(_risk(domain, RiskLevel.HIGH, distance, setback,
                               "Declared feature distance is inside the required setback.", ("SG-005", "SG-006")))
        elif distance == setback:
            risks.append(_risk(domain, RiskLevel.LOW, distance, setback,
                               "Distance equals the modeled setback; AHJ boundary confirmation remains required.",
                               ("SG-005", "SG-006")))
        else:
            risks.append(_risk(domain, RiskLevel.LOW, distance, setback,
                               "Declared distance exceeds the modeled setback; no permit determination is made."))

    if water.flood_100yr_depth_m is None:
        risks.append(_risk("FLOOD_100YR", RiskLevel.UNKNOWN, None, 0.0,
                           "The declared flood depth is unknown.", ("SG-004", "SG-005")))
    else:
        flooded = water.flood_100yr_depth_m > 0
        risks.append(_risk(
            "FLOOD_100YR", RiskLevel.HIGH if flooded else RiskLevel.LOW,
            water.flood_100yr_depth_m, 0.0,
            "Positive synthetic flood depth requires hydrology review." if flooded
            else "Zero synthetic flood depth is only an input assumption, not a flood determination.",
            ("SG-004", "SG-005") if flooded else (),
        ))

    if slope.modeled_factor_of_safety is None:
        risks.append(_risk("SLOPE_STABILITY", RiskLevel.UNKNOWN, None, slope.required_factor_of_safety,
                           "Modeled slope factor of safety is unavailable.", ("SG-001",)))
    else:
        unstable = slope.modeled_factor_of_safety < slope.required_factor_of_safety
        risks.append(_risk(
            "SLOPE_STABILITY", RiskLevel.HIGH if unstable else RiskLevel.LOW,
            slope.modeled_factor_of_safety, slope.required_factor_of_safety,
            "Modeled slope factor of safety is below the declared requirement." if unstable
            else "Modeled slope factor of safety meets the declared synthetic threshold only.",
            ("SG-001",) if unstable else (),
        ))
    expansive = slope.expansive_clay_risk
    risks.append(_risk(
        "EXPANSIVE_CLAY", expansive, None, None,
        "Declared expansive-clay risk is retained independently.",
        ("SG-001", "SG-002") if expansive is not RiskLevel.LOW else (),
    ))
    shifting = slope.land_shift_rate_mm_year > slope.land_shift_review_threshold_mm_year
    risks.append(_risk(
        "LAND_SHIFT", RiskLevel.HIGH if shifting else RiskLevel.LOW,
        slope.land_shift_rate_mm_year, slope.land_shift_review_threshold_mm_year,
        "Land-shift rate exceeds the declared review threshold." if shifting
        else "Land-shift rate does not exceed the declared review threshold; monitoring evidence is unresolved.",
        ("SG-001", "SG-002") if shifting else (),
    ))

    low_solar = climate.mean_daily_insolation_kwh_m2_day < climate.minimum_insolation_kwh_m2_day
    risks.append(_risk(
        "SOLAR_RESOURCE", RiskLevel.MODERATE if low_solar else RiskLevel.LOW,
        climate.mean_daily_insolation_kwh_m2_day, climate.minimum_insolation_kwh_m2_day,
        "Mean insolation is below the declared concept minimum." if low_solar
        else "Mean insolation meets the declared concept minimum; production is not guaranteed.",
        ("SG-008",) if low_solar else (),
    ))
    cold = climate.winter_design_temperature_c < climate.minimum_winter_temperature_c
    risks.append(_risk(
        "WINTER_DESIGN", RiskLevel.MODERATE if cold else RiskLevel.LOW,
        climate.winter_design_temperature_c, climate.minimum_winter_temperature_c,
        "Winter design temperature is below the declared concept minimum." if cold
        else "Winter design temperature meets the declared concept minimum only.",
        ("SG-008",) if cold else (),
    ))

    if road.lowest_route_axle_limit_kg is None:
        risks.append(_risk("ROAD_AXLE", RiskLevel.UNKNOWN, road.maximum_transport_axle_load_kg, None,
                           "Lowest route axle limit is unknown.", ("SG-007",)))
    else:
        overload = road.maximum_transport_axle_load_kg > road.lowest_route_axle_limit_kg
        risks.append(_risk(
            "ROAD_AXLE", RiskLevel.HIGH if overload else RiskLevel.LOW,
            road.maximum_transport_axle_load_kg, road.lowest_route_axle_limit_kg,
            "Transport axle load exceeds the known route limit." if overload
            else "Transport axle load does not exceed the declared route limit; route approval is unresolved.",
            ("SG-007",) if overload else (),
        ))
    clearance_requirement = _sum(
        (road.transport_height_m, road.required_overhead_clearance_m), "required overhead clearance",
    )
    if road.minimum_overhead_clearance_m is None:
        risks.append(_risk("OVERHEAD_CLEARANCE", RiskLevel.UNKNOWN, None, clearance_requirement,
                           "Minimum overhead clearance is unknown.", ("SG-007",)))
    else:
        insufficient = road.minimum_overhead_clearance_m < clearance_requirement
        risks.append(_risk(
            "OVERHEAD_CLEARANCE", RiskLevel.HIGH if insufficient else RiskLevel.LOW,
            road.minimum_overhead_clearance_m, clearance_requirement,
            "Known overhead clearance is below transport height plus required clearance." if insufficient
            else "Known overhead clearance meets the synthetic geometric requirement only.",
            ("SG-007",) if insufficient else (),
        ))

    visual_review = privacy.required_visual_screen_height_m > 0
    risks.append(_risk(
        "SIGHTLINE", RiskLevel.MODERATE if visual_review else RiskLevel.LOW,
        privacy.nearest_sightline_distance_m, privacy.required_visual_screen_height_m,
        "A visual screen is requested; receiver, terrain, and spoil placement require review."
        if visual_review else "No positive visual-screen height was declared; privacy is not certified.",
        ("SG-009",) if visual_review else (),
    ))
    effective_target = max(privacy.receiver_target_dba, privacy.ambient_dba)
    exponent = (privacy.source_dba_at_15m - effective_target) / 20.0
    try:
        acoustic_distance = max(15.0, 15.0 * 10.0 ** exponent)
    except OverflowError as exc:
        raise ConfigError("acoustic geometric distance is non-finite") from exc
    acoustic_distance = _finite(acoustic_distance, "acoustic geometric distance")
    acoustic_review = privacy.nearest_sightline_distance_m < acoustic_distance
    risks.append(_risk(
        "ACOUSTIC_PRIVACY", RiskLevel.MODERATE if acoustic_review else RiskLevel.LOW,
        privacy.nearest_sightline_distance_m, acoustic_distance,
        "Receiver distance is below the free-field geometric comparison distance; this is not compliance."
        if acoustic_review else "Receiver distance exceeds the free-field geometric comparison only.",
        ("SG-009",) if acoustic_review else (),
    ))
    return tuple(risks)


def assess_permits(model: PermitProfile) -> tuple[PermitAssessment, ...]:
    """Return candidate topics; no exemption or permit is ever granted."""

    _validate_permits(model)
    conditions = (
        model.rural_unincorporated and model.agricultural_accessory_candidate
        and model.nonhabitable_utility_structure
    )
    swppp = model.ground_disturbance_m2 >= model.swppp_trigger_area_m2
    return (
        PermitAssessment(
            "RURAL_AGRICULTURAL_ACCESSORY_EXEMPTION",
            PermitFinding.EXEMPTION_CANDIDATE if conditions else PermitFinding.AHJ_CONFIRMATION_REQUIRED,
            "All three declared rural/agricultural/nonhabitable conditions support an exemption candidate only."
            if conditions else "The declared circumstances do not establish the complete exemption candidate.",
            "SG-006",
        ),
        PermitAssessment(
            "GRADING_SWPPP", PermitFinding.TRIGGERED if swppp else PermitFinding.AHJ_CONFIRMATION_REQUIRED,
            "Ground disturbance equals or exceeds the declared SWPPP trigger; grading review is triggered."
            if swppp else "Below-threshold disturbance still requires AHJ confirmation and environmental review.",
            "SG-006",
        ),
        PermitAssessment(
            "WELL_SEPTIC", PermitFinding.TRIGGERED if model.well_or_septic_work
            else PermitFinding.AHJ_CONFIRMATION_REQUIRED,
            "Well or septic work triggers specialist and AHJ topics." if model.well_or_septic_work
            else "No work was declared; AHJ scope confirmation is still required.",
            "SG-006",
        ),
        PermitAssessment(
            "DRIVEWAY_CULVERT", PermitFinding.TRIGGERED if model.new_driveway_culvert
            else PermitFinding.AHJ_CONFIRMATION_REQUIRED,
            "A new driveway culvert triggers road/drainage and AHJ topics." if model.new_driveway_culvert
            else "No new culvert was declared; AHJ scope confirmation is still required.",
            "SG-006",
        ),
        PermitAssessment(
            "AHJ_DETERMINATION", PermitFinding.AHJ_CONFIRMATION_REQUIRED,
            "No AHJ determination is accepted by this release; every candidate topic remains unresolved.",
            "SG-006",
        ),
    )


def _privacy_berm_volume(privacy: PrivacyProfile) -> float:
    requested = _product(
        privacy.privacy_berm_length_m, privacy.privacy_berm_cross_section_m2,
        name="requested privacy berm volume",
    )
    return min(requested, privacy.available_compacted_spoil_m3)


def screen_candidate_parcels(parcels: Sequence[CandidateParcel]) -> ScreeningResult:
    """Screen independent anonymous candidates without making a purchase ranking."""

    if isinstance(parcels, (str, bytes)) or not isinstance(parcels, Sequence) or not parcels:
        raise ConfigError("parcels must be a non-empty sequence")
    assessments = []
    labels = []
    for parcel in parcels:
        _validate_candidate(parcel)
        labels.append(parcel.anonymous_label)
        risks = assess_risks(parcel.factors)
        permits = assess_permits(parcel.factors.permits)
        by_domain = {risk.domain: risk for risk in risks}
        hard = any(
            by_domain[domain].level is RiskLevel.HIGH
            for domain in ("WATERWAY_SETBACK", "WETLAND_SETBACK", "ROAD_AXLE", "OVERHEAD_CLEARANCE")
        )
        review = any(risk.level in {RiskLevel.HIGH, RiskLevel.UNKNOWN} for risk in risks) or any(
            permit.finding is PermitFinding.TRIGGERED for permit in permits
        )
        decision = (
            ScreeningDecision.REJECT_ON_MODELED_CONSTRAINT if hard
            else ScreeningDecision.ENGINEERING_REVIEW if review
            else ScreeningDecision.RELATIVE_CANDIDATE
        )
        road_review = any(
            by_domain[domain].level is not RiskLevel.LOW for domain in ("ROAD_AXLE", "OVERHEAD_CLEARANCE")
        )
        assessments.append(ParcelAssessment(
            parcel.anonymous_label, decision, risks, permits, road_review,
            _privacy_berm_volume(parcel.factors.privacy), _ALL_GATE_IDS,
        ))
    if len(set(labels)) != len(labels):
        raise ConfigError("candidate anonymous labels must be unique")
    decision_rank = {
        ScreeningDecision.REJECT_ON_MODELED_CONSTRAINT: 0,
        ScreeningDecision.ENGINEERING_REVIEW: 1,
        ScreeningDecision.RELATIVE_CANDIDATE: 2,
    }
    risk_rank = {RiskLevel.LOW: 0, RiskLevel.MODERATE: 1, RiskLevel.HIGH: 2, RiskLevel.UNKNOWN: 3}

    def severity(item: ParcelAssessment) -> tuple[Any, ...]:
        highest = max(risk_rank[risk.level] for risk in item.risks)
        non_low = sum(risk.level is not RiskLevel.LOW for risk in item.risks)
        triggered = sum(permit.finding is PermitFinding.TRIGGERED for permit in item.permits)
        return decision_rank[item.decision], -highest, -non_low, -triggered, item.anonymous_label

    return ScreeningResult("screen", tuple(sorted(assessments, key=severity)), _human_gates())


def adapt_to_existing_site(site: ExistingSite) -> AdaptationResult:
    """Accumulate concept adaptations for an existing anonymous site."""

    _validate_existing(site)
    factors = site.factors
    risks = assess_risks(factors)
    by_domain = {risk.domain: risk for risk in risks}
    assumptions = {item.kind: item for item in site.adaptation_assumptions}
    construction = ConstructionStrategy.DEEP_CUT_AND_COVER
    foundation = FoundationStrategy.STRIP_CONCEPT_ONLY
    adaptations: list[EngineeringAdaptation] = []

    def append(kind: AdaptationKind, reason: str, gates: tuple[str, ...], *,
               collar_volume: float = 0.0, sump_count: int = 0, berm_volume: float = 0.0) -> None:
        if kind not in assumptions:
            raise ConfigError(f"triggered {kind.value} has no explicit AdaptationAssumption")
        assumption = assumptions[kind]
        adaptation_id = f"SA-{len(adaptations) + 1:03d}"
        delta = CostScheduleDelta(
            adaptation_id, assumption.cost_delta, assumption.schedule_delta_h, assumption.labor_delta_h,
            site.cost_currency, assumption.basis,
        )
        adaptations.append(EngineeringAdaptation(
            adaptation_id, kind, reason, construction, foundation, collar_volume, sump_count,
            berm_volume, delta, gates,
        ))

    groundwater_shallow = (
        factors.water.groundwater_depth_m is not None
        and factors.water.groundwater_depth_m < site.baseline_excavation_depth_m
    )
    karst_shallow = (
        factors.karst.karst_bedrock_depth_m is not None
        and factors.karst.karst_bedrock_depth_m < site.baseline_excavation_depth_m
    )
    high_subsidence = factors.karst.subsidence_risk is RiskLevel.HIGH
    if groundwater_shallow or karst_shallow or high_subsidence:
        construction = ConstructionStrategy.SEMI_BURIED_EARTH_BERMED_MOUND
        foundation = FoundationStrategy.SPECIALIST_DESIGN_TBD
        causes = []
        if groundwater_shallow:
            causes.append("groundwater above baseline excavation depth")
        if karst_shallow:
            causes.append("karst bedrock above baseline excavation depth")
        if high_subsidence:
            causes.append("high declared subsidence risk")
        append(
            AdaptationKind.SHALLOW_MOUND,
            "Semi-buried earth-bermed mound concept selected because " + " and ".join(causes)
            + "; specialist design is retained and no excavation plan is produced.",
            ("SG-001", "SG-002", "SG-003", "SG-004"),
        )

    if (
        factors.slope.expansive_clay_risk in {RiskLevel.MODERATE, RiskLevel.HIGH, RiskLevel.UNKNOWN}
        or factors.slope.land_shift_rate_mm_year > factors.slope.land_shift_review_threshold_mm_year
    ):
        foundation = FoundationStrategy.STIFFENED_CELLULAR_RAFT_ON_GEOGRID
        append(
            AdaptationKind.CELLULAR_RAFT,
            "Declared expansive-clay risk or land movement triggers a stiffened cellular raft/geogrid "
            "concept; geotechnical and structural design remain unresolved.",
            ("SG-001", "SG-002", "SG-003"),
        )

    water = factors.water
    anti_flotation = False
    if water.buoyancy_displaced_volume_m3 > 0:
        uplift = _product(
            water.water_density_kg_m3, STANDARD_GRAVITY_MPS2, water.buoyancy_displaced_volume_m3,
            name="anti-flotation uplift",
        )
        resisting = _product(water.resisting_mass_kg, STANDARD_GRAVITY_MPS2, name="resisting force")
        factor = checked_divide(resisting, uplift, "anti-flotation factor of safety")
        if factor < site.anti_flotation_required_factor:
            anti_flotation = True
            density_term = _sum((
                water.concrete_density_kg_m3,
                -_product(
                    site.anti_flotation_required_factor, water.collar_submerged_fraction,
                    water.water_density_kg_m3, name="submerged collar density term",
                ),
            ), "collar density denominator term")
            denominator = _product(
                STANDARD_GRAVITY_MPS2, density_term, name="collar volume denominator",
            )
            if density_term <= 0 or denominator <= 0:
                raise ConfigError(
                    "anti-flotation collar density denominator must be positive; specialist design is required",
                )
            deficit = _sum((
                _product(site.anti_flotation_required_factor, uplift, name="required resisting force"),
                -resisting,
            ), "anti-flotation resisting deficit")
            collar_volume = max(0.0, checked_divide(deficit, denominator, "collar deadweight volume"))
            append(
                AdaptationKind.ANTI_FLOTATION_COLLAR,
                "Modeled resisting/uplift factor is below the site requirement; the reported dead-weight "
                "collar volume is a synthetic arithmetic allocation, not geometry or a released design.",
                ("SG-001", "SG-002", "SG-004"),
                collar_volume=collar_volume,
            )

    water_concern = anti_flotation or any(
        by_domain[domain].level is not RiskLevel.LOW for domain in ("GROUNDWATER", "FLOOD_100YR")
    )
    if water_concern:
        append(
            AdaptationKind.REDUNDANT_SOLAR_DRAINAGE,
            "Groundwater, flood, or anti-flotation concern allocates two independent solar sump concepts "
            "with battery backup; this is not a drainage design or reliable life-safety system.",
            ("SG-001", "SG-004", "SG-005", "SG-008"), sump_count=2,
        )

    requested_berm = _product(
        factors.privacy.privacy_berm_length_m, factors.privacy.privacy_berm_cross_section_m2,
        name="requested privacy berm volume",
    )
    if requested_berm > 0 or factors.privacy.required_visual_screen_height_m > 0:
        placed = min(requested_berm, factors.privacy.available_compacted_spoil_m3)
        shortfall = _sum((requested_berm, -placed), "privacy berm shortfall")
        append(
            AdaptationKind.PRIVACY_SPOIL_BERM,
            f"Requested {requested_berm:.6f} m3 and capped placement at available compacted spoil; "
            f"shortfall {shortfall:.6f} m3. Geotechnical/privacy review precedes any placement concept.",
            ("SG-001", "SG-002", "SG-003", "SG-009"), berm_volume=placed,
        )

    if any(
        by_domain[domain].level in {RiskLevel.HIGH, RiskLevel.UNKNOWN}
        for domain in ("WATERWAY_SETBACK", "WETLAND_SETBACK")
    ):
        append(
            AdaptationKind.WATERWAY_SETBACK,
            "Waterway/wetland setback violation or unknown distance requires environmental and AHJ review; "
            "the software cannot move a real feature or grant a permit.",
            ("SG-005", "SG-006"),
        )
    if any(
        by_domain[domain].level in {RiskLevel.HIGH, RiskLevel.UNKNOWN}
        for domain in ("ROAD_AXLE", "OVERHEAD_CLEARANCE")
    ):
        append(
            AdaptationKind.ACCESS_REVIEW,
            "Known transport constraint or unknown route clearance requires road-access review before any "
            "transport concept; no route approval is made.",
            ("SG-006", "SG-007"),
        )

    total_cost = _sum((item.delta.cost_delta for item in adaptations), "total adaptation cost delta")
    total_schedule = _sum(
        (item.delta.schedule_delta_h for item in adaptations), "total adaptation schedule delta",
    )
    return AdaptationResult(
        "adapt", site.anonymous_label, tuple(adaptations), site.baseline_cost, total_cost,
        site.baseline_schedule_h, total_schedule, site.cost_currency, _ALL_GATE_IDS, _human_gates(),
    )


_UNIT_SUFFIXES = {
    "_kwh_m2_day": "_kWh_m2_day", "_kg_m3": "_kg_m3", "_m3": "_m3",
    "_m2": "_m2", "_dba": "_dBA", "_kg": "_kg", "_mm": "_mm",
    "_m": "_m", "_c": "_C", "_h": "_h",
}
_MONETARY_FIELDS = {"baseline_cost", "total_cost_delta", "cost_delta"}


def _camel(name: str) -> str:
    source_suffix, json_suffix = next(
        ((source, target) for source, target in _UNIT_SUFFIXES.items() if name.endswith(source)), ("", "")
    )
    stem = name[:-len(source_suffix)] if source_suffix else name
    parts = stem.split("_")
    return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:]) + json_suffix


def _json_value(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        converted = {}
        for field in fields(value):
            item = _json_value(getattr(value, field.name))
            if field.name in _MONETARY_FIELDS:
                item = round(item, 6)
                item = 0.0 if item == 0 else item
            converted[_camel(field.name)] = item
        return converted
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    return value


def _check_json_value(value: Any, path: str = "result") -> None:
    if isinstance(value, float):
        _finite(value, path)
    elif isinstance(value, dict):
        for key, item in value.items():
            _check_json_value(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _check_json_value(item, f"{path}[{index}]")


def _validate_result(result: ScreeningResult | AdaptationResult) -> None:
    if not isinstance(result, (ScreeningResult, AdaptationResult)):
        raise ConfigError("result must be ScreeningResult or AdaptationResult")
    gates = result.human_gates
    gate_ids = tuple(gate.gate_id for gate in gates)
    if gate_ids != tuple(sorted(gate_ids)) or len(set(gate_ids)) != len(gate_ids):
        raise ConfigError("human gates must have unique sorted identifiers")
    if any(gate.status != "UNRESOLVED" for gate in gates):
        raise ConfigError("all human gates must remain unresolved")
    if result.location_data_retained is not False or result.physical_validation_performed is not False:
        raise ConfigError("location retention and physical validation must remain false")
    if isinstance(result, ScreeningResult):
        if result.mode != "screen" or result.purchase_recommendation_made is not False:
            raise ConfigError("screen result mode and no-purchase invariants must be preserved")
        for parcel in result.parcels:
            if parcel.unresolved_gate_ids != gate_ids:
                raise ConfigError("parcel gate IDs must match the unresolved result gates")
    else:
        if result.mode != "adapt" or result.construction_authorized is not False:
            raise ConfigError("adapt result mode and no-authorization invariants must be preserved")
        if result.site_engineering_complete is not False:
            raise ConfigError("site engineering must remain incomplete")
        if result.human_gate_ids != gate_ids:
            raise ConfigError("adaptation gate IDs must match the unresolved result gates")
        expected_cost = _sum((item.delta.cost_delta for item in result.adaptations), "result cost delta")
        expected_schedule = _sum(
            (item.delta.schedule_delta_h for item in result.adaptations), "result schedule delta",
        )
        if not math.isclose(result.total_cost_delta, expected_cost, rel_tol=0, abs_tol=1e-6):
            raise ConfigError("total cost delta does not reconcile")
        if not math.isclose(result.total_schedule_delta_h, expected_schedule, rel_tol=0, abs_tol=1e-9):
            raise ConfigError("total schedule delta does not reconcile")
        for item in result.adaptations:
            if item.delta.currency != result.currency:
                raise ConfigError("adaptation delta currency must match result currency")


def geohazard_result_json(result: ScreeningResult | AdaptationResult) -> str:
    """Serialize anonymous derived results with sorted keys and finite numbers."""

    _validate_result(result)
    compatible = _json_value(result)
    _check_json_value(compatible)
    try:
        return json.dumps(
            compatible, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False,
        ) + "\n"
    except (TypeError, ValueError, OverflowError) as exc:
        raise ConfigError("geohazard result is not finite JSON") from exc


def write_geohazard_result(result: ScreeningResult | AdaptationResult, output_dir: str | Path) -> Path:
    text = geohazard_result_json(result)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / "result.json"
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


class SiteAdvisor:
    """Stateless convenience facade with no I/O, authority, or persistent state."""

    def screen(self, parcels: Sequence[CandidateParcel]) -> ScreeningResult:
        return screen_candidate_parcels(parcels)

    def adapt(self, site: ExistingSite) -> AdaptationResult:
        return adapt_to_existing_site(site)
