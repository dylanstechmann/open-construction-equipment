# SPDX-License-Identifier: Apache-2.0
"""Deterministic synthetic multi-physics screening arithmetic.

The equations in this module are transparent, deliberately limited trade-study
models. They are not finite-element analyses, design checks, safety functions,
physical validation, or authorization for construction or equipment operation.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from enum import StrEnum
import json
import math
from pathlib import Path
import re
from typing import Any

from .config import ConfigError, _keys, _mapping, _number, _string, load_json

STANDARD_GRAVITY_MPS2 = 9.80665
GAS_CONSTANT_J_MOL_K = 8.31446261815324
SOURCE_TYPE_ID = "SYNTHETIC_AGENT_AUTHORED"
PLATFORM_ID = "OCE-CTL-01"
SCOPE_ID = "BUNKER-01"
UNIT_SYSTEM_ID = "SI"


class EvidenceStatus(StrEnum):
    SIMULATED_UNREVIEWED = "SIMULATED_" + "UNREVIEWED"


class WeatherStopCondition(StrEnum):
    COLD_THRESHOLD = "COLD_THRESHOLD"
    HOT_THRESHOLD = "HOT_THRESHOLD"
    PRECIPITATION_THRESHOLD = "PRECIPITATION_" + "THRESHOLD"
    WIND_THRESHOLD = "WIND_THRESHOLD"


class ScreeningFlag(StrEnum):
    WITHIN_MODEL_ASSUMPTION = "WITHIN_MODEL_" + "ASSUMPTION"
    THRESHOLD_EXCEEDED = "THRESHOLD_EXCEEDED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True)
class SyntheticProvenance:
    source_type: str
    statement: str
    ai_authored: bool
    owner_supplied: bool
    site_supplied: bool
    physical_validation_performed: bool


@dataclass(frozen=True)
class TrackContact:
    length_m: float
    width_m: float
    normal_load_n: float


@dataclass(frozen=True)
class TerramechanicsInput:
    track: TrackContact
    soil_cohesion_kpa: float
    soil_friction_angle_rad: float
    soil_stiffness_kpa_per_m: float
    rolling_resistance_coefficient: float
    traction_efficiency: float
    slope_angle_rad: float
    maximum_modeled_sinkage_m: float


@dataclass(frozen=True)
class BearingInput:
    foundation_length_m: float
    foundation_width_m: float
    vertical_service_load_n: float
    allowable_bearing_pressure_kpa: float
    required_factor_of_safety: float


@dataclass(frozen=True)
class SlopeInput:
    slope_angle_rad: float
    cohesion_kpa: float
    friction_angle_rad: float
    soil_unit_weight_kn_m3: float
    vertical_slice_height_m: float
    pore_pressure_ratio: float
    required_factor_of_safety: float


@dataclass(frozen=True)
class BuoyancyInput:
    displaced_water_volume_m3: float
    resisting_mass_kg: float
    water_density_kg_m3: float
    required_factor_of_safety: float


@dataclass(frozen=True)
class TemperatureInterval:
    duration_h: float
    mean_temperature_c: float


@dataclass(frozen=True)
class ConcreteCuringInput:
    intervals: tuple[TemperatureInterval, ...]
    datum_temperature_c: float
    reference_temperature_c: float
    activation_energy_j_mol: float
    target_equivalent_age_h: float


@dataclass(frozen=True)
class WeatherSample:
    temperature_c: float
    precipitation_mm_h: float
    wind_speed_mps: float


@dataclass(frozen=True)
class WeatherLimits:
    minimum_temperature_c: float
    maximum_temperature_c: float
    cold_reference_temperature_c: float
    cold_derating_per_c: float
    maximum_precipitation_mm_h: float
    maximum_wind_speed_mps: float


@dataclass(frozen=True)
class PhysicsInput:
    analysis_id: str
    provenance: SyntheticProvenance
    terramechanics: TerramechanicsInput
    bearing: BearingInput
    slope: SlopeInput
    buoyancy: BuoyancyInput
    curing: ConcreteCuringInput
    weather: WeatherSample
    weather_limits: WeatherLimits
    required_human_gate_ids: tuple[str, ...]


@dataclass(frozen=True)
class TerramechanicsResult:
    contact_pressure_kpa: float
    sinkage_m: float
    maximum_shear_stress_kpa: float
    available_thrust_n: float
    rolling_resistance_n: float
    grade_resistance_n: float
    net_tractive_margin_n: float
    sinkage_flag: ScreeningFlag


@dataclass(frozen=True)
class BearingResult:
    applied_pressure_kpa: float
    allowable_pressure_kpa: float
    factor_of_safety: float
    utilization: float
    threshold_flag: ScreeningFlag


@dataclass(frozen=True)
class SlopeResult:
    driving_stress_kpa: float
    resisting_stress_kpa: float
    factor_of_safety: float
    threshold_flag: ScreeningFlag


@dataclass(frozen=True)
class BuoyancyResult:
    uplift_n: float
    resisting_n: float
    factor_of_safety: float | None
    additional_resisting_mass_kg: float
    threshold_flag: ScreeningFlag


@dataclass(frozen=True)
class CuringResult:
    nurse_saul_maturity_c_h: float
    arrhenius_equivalent_age_h: float
    target_equivalent_age_h: float
    target_reached: bool


@dataclass(frozen=True)
class WeatherDeratingResult:
    temperature_factor: float
    precipitation_factor: float
    wind_factor: float
    combined_available_fraction: float
    stop_conditions: tuple[WeatherStopCondition, ...]


@dataclass(frozen=True)
class PhysicsResult:
    analysis_id: str
    status: EvidenceStatus
    provenance: SyntheticProvenance
    terramechanics: TerramechanicsResult
    bearing: BearingResult
    slope: SlopeResult
    buoyancy: BuoyancyResult
    curing: CuringResult
    weather: WeatherDeratingResult
    unresolved_human_gate_ids: tuple[str, ...]
    physical_validation_performed: bool = False
    construction_authorized: bool = False
    operational_release: bool = False


def _finite(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{name} must be a finite number")
    try:
        result = float(value)
    except (OverflowError, TypeError, ValueError) as exc:
        raise ConfigError(f"{name} must be a finite number") from exc
    if not math.isfinite(result):
        raise ConfigError(f"{name} must be finite")
    return 0.0 if result == 0 else result


def _product(*values: float, name: str) -> float:
    result = 1.0
    nonzero = True
    for value in values:
        number = _finite(value, name)
        nonzero = nonzero and number != 0
        result *= number
        if not math.isfinite(result):
            raise ConfigError(f"calculation produced a non-finite {name}")
        if nonzero and result == 0:
            raise ConfigError(f"calculation underflowed nonzero {name}")
    return 0.0 if result == 0 else result


def _sum(values: Any, name: str) -> float:
    try:
        return _finite(math.fsum(values), name)
    except (OverflowError, ValueError) as exc:
        raise ConfigError(f"calculation produced a non-finite {name}") from exc


def _at_least(value: float, minimum: float, name: str, *, strict: bool = False) -> float:
    number = _finite(value, name)
    if number < minimum or (strict and number <= minimum):
        relation = ">" if strict else ">="
        raise ConfigError(f"{name} must be {relation} {minimum}")
    return number


def _below(value: float, maximum: float, name: str, *, strict: bool = False) -> float:
    number = _finite(value, name)
    if number > maximum or (strict and number >= maximum):
        relation = "<" if strict else "<="
        raise ConfigError(f"{name} must be {relation} {maximum}")
    return number


def bounded_fraction(value: float, name: str) -> float:
    """Validate a modeled fraction without silently clipping invalid arithmetic."""

    number = _finite(value, name)
    if not 0.0 <= number <= 1.0:
        raise ConfigError(f"{name} must be within [0, 1]")
    return number


def checked_divide(numerator: float, denominator: float, name: str) -> float:
    """Perform checked finite division, rejecting zero and nonzero underflow."""

    top = _finite(numerator, f"{name} numerator")
    bottom = _finite(denominator, f"{name} denominator")
    if bottom == 0:
        raise ConfigError(f"{name} denominator must be nonzero")
    result = _finite(top / bottom, name)
    if top != 0 and result == 0:
        raise ConfigError(f"calculation underflowed nonzero {name}")
    return result


def _validate_provenance(model: SyntheticProvenance, name: str = "provenance") -> None:
    if not isinstance(model, SyntheticProvenance):
        raise ConfigError(f"{name} must be SyntheticProvenance")
    if model.source_type != SOURCE_TYPE_ID:
        raise ConfigError(f"{name}.sourceType must be {SOURCE_TYPE_ID}")
    if not isinstance(model.statement, str) or not model.statement.strip():
        raise ConfigError(f"{name}.statement must be a non-empty string")
    if model.ai_authored is not True or model.owner_supplied is not False or model.site_supplied is not False:
        raise ConfigError(f"{name} must declare AI authorship and deny owner/site supply")
    if model.physical_validation_performed is not False:
        raise ConfigError(f"{name}.physicalValidationPerformed must be false")


def _parse_provenance(value: Any, name: str = "provenance") -> SyntheticProvenance:
    data = _mapping(value, name)
    required = {
        "sourceType", "statement", "aiAuthored", "ownerSupplied", "siteSupplied",
        "physicalValidationPerformed",
    }
    _keys(data, required, set(), name)
    model = SyntheticProvenance(
        source_type=_string(data, "sourceType", name),
        statement=_string(data, "statement", name),
        ai_authored=data["aiAuthored"],
        owner_supplied=data["ownerSupplied"],
        site_supplied=data["siteSupplied"],
        physical_validation_performed=data["physicalValidationPerformed"],
    )
    _validate_provenance(model, name)
    return model


def _validate_track(model: TrackContact, name: str = "track") -> None:
    if not isinstance(model, TrackContact):
        raise ConfigError(f"{name} must be TrackContact")
    _at_least(model.length_m, 0, f"{name}.length_m", strict=True)
    _at_least(model.width_m, 0, f"{name}.width_m", strict=True)
    _at_least(model.normal_load_n, 0, f"{name}.normal_load_n", strict=True)


def _validate_terramechanics(model: TerramechanicsInput) -> None:
    if not isinstance(model, TerramechanicsInput):
        raise ConfigError("model must be TerramechanicsInput")
    _validate_track(model.track)
    _at_least(model.soil_cohesion_kpa, 0, "soil_cohesion_kpa")
    _at_least(model.soil_friction_angle_rad, 0, "soil_friction_angle_rad")
    _below(model.soil_friction_angle_rad, math.pi / 2, "soil_friction_angle_rad", strict=True)
    _at_least(model.soil_stiffness_kpa_per_m, 0, "soil_stiffness_kpa_per_m", strict=True)
    _at_least(model.rolling_resistance_coefficient, 0, "rolling_resistance_coefficient")
    bounded_fraction(model.traction_efficiency, "traction_efficiency")
    if model.traction_efficiency == 0:
        raise ConfigError("traction_efficiency must be > 0")
    _at_least(model.slope_angle_rad, 0, "slope_angle_rad")
    _below(model.slope_angle_rad, math.pi / 2, "slope_angle_rad", strict=True)
    _at_least(model.maximum_modeled_sinkage_m, 0, "maximum_modeled_sinkage_m")


def _validate_bearing(model: BearingInput) -> None:
    if not isinstance(model, BearingInput):
        raise ConfigError("model must be BearingInput")
    for name in ("foundation_length_m", "foundation_width_m", "vertical_service_load_n",
                 "allowable_bearing_pressure_kpa"):
        _at_least(getattr(model, name), 0, name, strict=True)
    _at_least(model.required_factor_of_safety, 1, "required_factor_of_safety")


def _validate_slope(model: SlopeInput) -> None:
    if not isinstance(model, SlopeInput):
        raise ConfigError("model must be SlopeInput")
    _at_least(model.slope_angle_rad, 0, "slope_angle_rad", strict=True)
    _below(model.slope_angle_rad, math.pi / 2, "slope_angle_rad", strict=True)
    _at_least(model.cohesion_kpa, 0, "cohesion_kpa")
    _at_least(model.friction_angle_rad, 0, "friction_angle_rad")
    _below(model.friction_angle_rad, math.pi / 2, "friction_angle_rad", strict=True)
    _at_least(model.soil_unit_weight_kn_m3, 0, "soil_unit_weight_kn_m3", strict=True)
    _at_least(model.vertical_slice_height_m, 0, "vertical_slice_height_m", strict=True)
    bounded_fraction(model.pore_pressure_ratio, "pore_pressure_ratio")
    _at_least(model.required_factor_of_safety, 1, "required_factor_of_safety")


def _validate_buoyancy(model: BuoyancyInput) -> None:
    if not isinstance(model, BuoyancyInput):
        raise ConfigError("model must be BuoyancyInput")
    _at_least(model.displaced_water_volume_m3, 0, "displaced_water_volume_m3")
    _at_least(model.resisting_mass_kg, 0, "resisting_mass_kg")
    _at_least(model.water_density_kg_m3, 0, "water_density_kg_m3", strict=True)
    _at_least(model.required_factor_of_safety, 1, "required_factor_of_safety")


def _validate_curing(model: ConcreteCuringInput) -> None:
    if not isinstance(model, ConcreteCuringInput) or not isinstance(model.intervals, tuple) or not model.intervals:
        raise ConfigError("curing.intervals must be a non-empty tuple")
    for index, interval in enumerate(model.intervals):
        if not isinstance(interval, TemperatureInterval):
            raise ConfigError(f"curing.intervals[{index}] must be TemperatureInterval")
        _at_least(interval.duration_h, 0, f"curing.intervals[{index}].duration_h", strict=True)
        _at_least(interval.mean_temperature_c, -273.15,
                  f"curing.intervals[{index}].mean_temperature_c", strict=True)
    _at_least(model.datum_temperature_c, -273.15, "datum_temperature_c", strict=True)
    _at_least(model.reference_temperature_c, -273.15, "reference_temperature_c", strict=True)
    _at_least(model.activation_energy_j_mol, 0, "activation_energy_j_mol", strict=True)
    _at_least(model.target_equivalent_age_h, 0, "target_equivalent_age_h")


def _validate_weather(sample: WeatherSample, limits: WeatherLimits) -> None:
    if not isinstance(sample, WeatherSample) or not isinstance(limits, WeatherLimits):
        raise ConfigError("weather and weather_limits must use their declared dataclasses")
    _at_least(sample.temperature_c, -273.15, "weather.temperature_c", strict=True)
    _at_least(sample.precipitation_mm_h, 0, "weather.precipitation_mm_h")
    _at_least(sample.wind_speed_mps, 0, "weather.wind_speed_mps")
    minimum = _finite(limits.minimum_temperature_c, "weather_limits.minimum_temperature_c")
    maximum = _finite(limits.maximum_temperature_c, "weather_limits.maximum_temperature_c")
    reference = _finite(limits.cold_reference_temperature_c, "weather_limits.cold_reference_temperature_c")
    if not minimum < maximum:
        raise ConfigError("weather_limits minimum_temperature_c must be below maximum_temperature_c")
    if reference < minimum:
        raise ConfigError("weather_limits cold_reference_temperature_c must be >= minimum_temperature_c")
    _at_least(limits.cold_derating_per_c, 0, "weather_limits.cold_derating_per_c")
    _at_least(limits.maximum_precipitation_mm_h, 0, "weather_limits.maximum_precipitation_mm_h")
    _at_least(limits.maximum_wind_speed_mps, 0, "weather_limits.maximum_wind_speed_mps")


def _track(value: Any, name: str) -> TrackContact:
    data = _mapping(value, name)
    _keys(data, {"length_m", "width_m", "normalLoad_N"}, set(), name)
    return TrackContact(
        _number(data, "length_m", name, 0, strict_low=True),
        _number(data, "width_m", name, 0, strict_low=True),
        _number(data, "normalLoad_N", name, 0, strict_low=True),
    )


def _terramechanics(value: Any) -> TerramechanicsInput:
    name = "terramechanics"
    data = _mapping(value, name)
    required = {
        "track", "soilCohesion_kPa", "soilFrictionAngle_rad", "soilStiffness_kPa_per_m",
        "rollingResistanceCoefficient", "tractionEfficiency", "slopeAngle_rad",
        "maximumModeledSinkage_m",
    }
    _keys(data, required, set(), name)
    model = TerramechanicsInput(
        _track(data["track"], f"{name}.track"),
        _number(data, "soilCohesion_kPa", name, 0),
        _number(data, "soilFrictionAngle_rad", name, 0, math.pi / 2),
        _number(data, "soilStiffness_kPa_per_m", name, 0, strict_low=True),
        _number(data, "rollingResistanceCoefficient", name, 0),
        _number(data, "tractionEfficiency", name, 0, 1, strict_low=True),
        _number(data, "slopeAngle_rad", name, 0, math.pi / 2),
        _number(data, "maximumModeledSinkage_m", name, 0),
    )
    _validate_terramechanics(model)
    return model


def _bearing(value: Any) -> BearingInput:
    name = "bearing"
    data = _mapping(value, name)
    required = {
        "foundationLength_m", "foundationWidth_m", "verticalServiceLoad_N",
        "allowableBearingPressure_kPa", "requiredFactorOfSafety",
    }
    _keys(data, required, set(), name)
    model = BearingInput(
        _number(data, "foundationLength_m", name, 0, strict_low=True),
        _number(data, "foundationWidth_m", name, 0, strict_low=True),
        _number(data, "verticalServiceLoad_N", name, 0, strict_low=True),
        _number(data, "allowableBearingPressure_kPa", name, 0, strict_low=True),
        _number(data, "requiredFactorOfSafety", name, 1),
    )
    _validate_bearing(model)
    return model


def _slope(value: Any) -> SlopeInput:
    name = "slope"
    data = _mapping(value, name)
    required = {
        "slopeAngle_rad", "cohesion_kPa", "frictionAngle_rad", "soilUnitWeight_kN_m3",
        "verticalSliceHeight_m", "porePressureRatio", "requiredFactorOfSafety",
    }
    _keys(data, required, set(), name)
    model = SlopeInput(
        _number(data, "slopeAngle_rad", name, 0, math.pi / 2, strict_low=True),
        _number(data, "cohesion_kPa", name, 0),
        _number(data, "frictionAngle_rad", name, 0, math.pi / 2),
        _number(data, "soilUnitWeight_kN_m3", name, 0, strict_low=True),
        _number(data, "verticalSliceHeight_m", name, 0, strict_low=True),
        _number(data, "porePressureRatio", name, 0, 1),
        _number(data, "requiredFactorOfSafety", name, 1),
    )
    _validate_slope(model)
    return model


def _buoyancy(value: Any) -> BuoyancyInput:
    name = "buoyancy"
    data = _mapping(value, name)
    required = {"displacedWaterVolume_m3", "resistingMass_kg", "waterDensity_kg_m3", "requiredFactorOfSafety"}
    _keys(data, required, set(), name)
    model = BuoyancyInput(
        _number(data, "displacedWaterVolume_m3", name, 0),
        _number(data, "resistingMass_kg", name, 0),
        _number(data, "waterDensity_kg_m3", name, 0, strict_low=True),
        _number(data, "requiredFactorOfSafety", name, 1),
    )
    _validate_buoyancy(model)
    return model


def _curing(value: Any) -> ConcreteCuringInput:
    name = "curing"
    data = _mapping(value, name)
    required = {
        "intervals", "datumTemperature_C", "referenceTemperature_C", "activationEnergy_J_mol",
        "targetEquivalentAge_h",
    }
    _keys(data, required, set(), name)
    raw_intervals = data["intervals"]
    if not isinstance(raw_intervals, list) or not raw_intervals:
        raise ConfigError("curing.intervals must be a non-empty array")
    intervals = []
    for index, item in enumerate(raw_intervals):
        interval_name = f"curing.intervals[{index}]"
        interval = _mapping(item, interval_name)
        _keys(interval, {"duration_h", "meanTemperature_C"}, set(), interval_name)
        intervals.append(TemperatureInterval(
            _number(interval, "duration_h", interval_name, 0, strict_low=True),
            _number(interval, "meanTemperature_C", interval_name, -273.15, strict_low=True),
        ))
    model = ConcreteCuringInput(
        tuple(intervals),
        _number(data, "datumTemperature_C", name, -273.15, strict_low=True),
        _number(data, "referenceTemperature_C", name, -273.15, strict_low=True),
        _number(data, "activationEnergy_J_mol", name, 0, strict_low=True),
        _number(data, "targetEquivalentAge_h", name, 0),
    )
    _validate_curing(model)
    return model


def _weather(value: Any) -> WeatherSample:
    data = _mapping(value, "weather")
    _keys(data, {"temperature_C", "precipitation_mm_h", "windSpeed_mps"}, set(), "weather")
    return WeatherSample(
        _number(data, "temperature_C", "weather", -273.15, strict_low=True),
        _number(data, "precipitation_mm_h", "weather", 0),
        _number(data, "windSpeed_mps", "weather", 0),
    )


def _weather_limits(value: Any) -> WeatherLimits:
    name = "weatherLimits"
    data = _mapping(value, name)
    required = {
        "minimumTemperature_C", "maximumTemperature_C", "coldReferenceTemperature_C",
        "coldDerating_per_C", "maximumPrecipitation_mm_h", "maximumWindSpeed_mps",
    }
    _keys(data, required, set(), name)
    model = WeatherLimits(
        _number(data, "minimumTemperature_C", name),
        _number(data, "maximumTemperature_C", name),
        _number(data, "coldReferenceTemperature_C", name),
        _number(data, "coldDerating_per_C", name, 0),
        _number(data, "maximumPrecipitation_mm_h", name, 0),
        _number(data, "maximumWindSpeed_mps", name, 0),
    )
    _validate_weather(WeatherSample(0.0, 0.0, 0.0), model)
    return model


def parse_physics_input(data: dict[str, Any]) -> PhysicsInput:
    """Parse the exact synthetic physics envelope and all nested SI models."""

    _mapping(data, "physics")
    required = {
        "spdxLicenseIdentifier", "schemaVersion", "platform", "scope", "unitSystem", "analysisId",
        "provenance", "terramechanics", "bearing", "slope", "buoyancy", "curing", "weather",
        "weatherLimits", "requiredHumanGateIds",
    }
    _keys(data, required, set(), "physics")
    constants = {
        "spdxLicenseIdentifier": "CC-BY-SA-4.0",
        "schemaVersion": "1.0.0",
        "platform": PLATFORM_ID,
        "scope": SCOPE_ID,
        "unitSystem": UNIT_SYSTEM_ID,
    }
    for key, expected in constants.items():
        if data[key] != expected:
            raise ConfigError(f"physics.{key} must be {expected}")
    raw_gates = data["requiredHumanGateIds"]
    if not isinstance(raw_gates, list) or not raw_gates:
        raise ConfigError("physics.requiredHumanGateIds must be a non-empty array")
    gates: list[str] = []
    for index, gate in enumerate(raw_gates):
        if not isinstance(gate, str) or re.fullmatch(r"PG-\d{3}", gate) is None:
            raise ConfigError(f"physics.requiredHumanGateIds[{index}] must match PG-\\d{{3}}")
        if gate in gates:
            raise ConfigError(f"physics.requiredHumanGateIds contains duplicate {gate}")
        gates.append(gate)
    return PhysicsInput(
        analysis_id=_string(data, "analysisId", "physics"),
        provenance=_parse_provenance(data["provenance"], "physics.provenance"),
        terramechanics=_terramechanics(data["terramechanics"]),
        bearing=_bearing(data["bearing"]),
        slope=_slope(data["slope"]),
        buoyancy=_buoyancy(data["buoyancy"]),
        curing=_curing(data["curing"]),
        weather=_weather(data["weather"]),
        weather_limits=_weather_limits(data["weatherLimits"]),
        required_human_gate_ids=tuple(gates),
    )


def load_physics_input(path: str | Path) -> PhysicsInput:
    return parse_physics_input(load_json(path))


def calculate_terramechanics(model: TerramechanicsInput) -> TerramechanicsResult:
    """Apply the two-equal-track pressure/sinkage and Mohr-Coulomb screen."""

    _validate_terramechanics(model)
    area_one = _product(model.track.length_m, model.track.width_m, name="one-track contact area")
    total_normal = _product(2.0, model.track.normal_load_n, name="total normal load")
    pressure = checked_divide(total_normal, _product(2.0, area_one, 1000.0, name="pressure denominator"),
                              "contact_pressure_kpa")
    sinkage = checked_divide(pressure, model.soil_stiffness_kpa_per_m, "sinkage_m")
    shear = _sum((model.soil_cohesion_kpa,
                  _product(pressure, math.tan(model.soil_friction_angle_rad), name="frictional shear")),
                 "maximum_shear_stress_kpa")
    thrust = _product(2.0, area_one, 1000.0, shear, model.traction_efficiency, name="available_thrust_n")
    rolling = _product(model.rolling_resistance_coefficient, total_normal,
                       math.cos(model.slope_angle_rad), name="rolling_resistance_n")
    grade = _product(total_normal, math.sin(model.slope_angle_rad), name="grade_resistance_n")
    margin = _sum((thrust, -rolling, -grade), "net_tractive_margin_n")
    flag = (ScreeningFlag.THRESHOLD_EXCEEDED if sinkage > model.maximum_modeled_sinkage_m
            else ScreeningFlag.WITHIN_MODEL_ASSUMPTION)
    return TerramechanicsResult(pressure, sinkage, shear, thrust, rolling, grade, margin, flag)


def calculate_bearing(model: BearingInput) -> BearingResult:
    _validate_bearing(model)
    area = _product(model.foundation_length_m, model.foundation_width_m, name="foundation area")
    applied = checked_divide(model.vertical_service_load_n, _product(area, 1000.0, name="bearing denominator"),
                             "applied_pressure_kpa")
    factor = checked_divide(model.allowable_bearing_pressure_kpa, applied, "bearing factor_of_safety")
    utilization = checked_divide(applied, model.allowable_bearing_pressure_kpa, "bearing utilization")
    flag = (ScreeningFlag.WITHIN_MODEL_ASSUMPTION
            if factor >= model.required_factor_of_safety else ScreeningFlag.THRESHOLD_EXCEEDED)
    return BearingResult(applied, model.allowable_bearing_pressure_kpa, factor, utilization, flag)


def calculate_slope(model: SlopeInput) -> SlopeResult:
    _validate_slope(model)
    beta = model.slope_angle_rad
    normal_total = _product(model.soil_unit_weight_kn_m3, model.vertical_slice_height_m,
                            math.cos(beta), math.cos(beta), name="total normal stress")
    driving = _product(model.soil_unit_weight_kn_m3, model.vertical_slice_height_m,
                       math.sin(beta), math.cos(beta), name="driving_stress_kpa")
    pore = _product(model.pore_pressure_ratio, normal_total, name="pore pressure")
    effective = _sum((normal_total, -pore), "effective normal stress")
    resisting = _sum((model.cohesion_kpa,
                      _product(effective, math.tan(model.friction_angle_rad), name="frictional resistance")),
                     "resisting_stress_kpa")
    factor = checked_divide(resisting, driving, "slope factor_of_safety")
    flag = (ScreeningFlag.WITHIN_MODEL_ASSUMPTION
            if factor >= model.required_factor_of_safety else ScreeningFlag.THRESHOLD_EXCEEDED)
    return SlopeResult(driving, resisting, factor, flag)


def calculate_buoyancy(model: BuoyancyInput) -> BuoyancyResult:
    _validate_buoyancy(model)
    resisting = _product(model.resisting_mass_kg, STANDARD_GRAVITY_MPS2, name="resisting_n")
    if model.displaced_water_volume_m3 == 0:
        return BuoyancyResult(0.0, resisting, None, 0.0, ScreeningFlag.NOT_APPLICABLE)
    uplift = _product(model.water_density_kg_m3, STANDARD_GRAVITY_MPS2,
                      model.displaced_water_volume_m3, name="uplift_n")
    factor = checked_divide(resisting, uplift, "buoyancy factor_of_safety")
    deficit = _sum((_product(model.required_factor_of_safety, uplift, name="required resisting force"),
                    -resisting), "resisting force deficit")
    additional = max(0.0, checked_divide(deficit, STANDARD_GRAVITY_MPS2, "additional_resisting_mass_kg"))
    flag = (ScreeningFlag.WITHIN_MODEL_ASSUMPTION
            if factor >= model.required_factor_of_safety else ScreeningFlag.THRESHOLD_EXCEEDED)
    return BuoyancyResult(uplift, resisting, factor, additional, flag)


def calculate_concrete_curing(model: ConcreteCuringInput) -> CuringResult:
    _validate_curing(model)
    reference_k = _sum((model.reference_temperature_c, 273.15), "reference absolute temperature")
    maturity_terms = []
    age_terms = []
    for index, interval in enumerate(model.intervals):
        temperature_k = _sum((interval.mean_temperature_c, 273.15), "interval absolute temperature")
        maturity_terms.append(_product(
            _sum((interval.mean_temperature_c, -model.datum_temperature_c), "temperature difference"),
            interval.duration_h, name=f"maturity interval {index}",
        ))
        reciprocal_delta = _sum((checked_divide(1.0, temperature_k, "interval reciprocal temperature"),
                                 -checked_divide(1.0, reference_k, "reference reciprocal temperature")),
                                "reciprocal temperature difference")
        exponent = _product(-model.activation_energy_j_mol / GAS_CONSTANT_J_MOL_K,
                            reciprocal_delta, name=f"Arrhenius exponent {index}")
        try:
            factor = _finite(math.exp(exponent), f"Arrhenius factor {index}")
        except OverflowError as exc:
            raise ConfigError(f"calculation produced a non-finite Arrhenius factor {index}") from exc
        age_terms.append(_product(interval.duration_h, factor, name=f"equivalent age interval {index}"))
    maturity = _sum(maturity_terms, "nurse_saul_maturity_c_h")
    equivalent_age = _sum(age_terms, "arrhenius_equivalent_age_h")
    return CuringResult(maturity, equivalent_age, model.target_equivalent_age_h,
                        equivalent_age >= model.target_equivalent_age_h)


def derate_weather(sample: WeatherSample, limits: WeatherLimits) -> WeatherDeratingResult:
    _validate_weather(sample, limits)
    cold_delta = max(0.0, _sum((limits.cold_reference_temperature_c, -sample.temperature_c), "cold delta"))
    cold_factor = max(0.0, _sum((1.0, -_product(limits.cold_derating_per_c, cold_delta,
                                                  name="cold derating")), "cold factor"))
    if sample.temperature_c > limits.maximum_temperature_c:
        span = max(1.0, _sum((limits.maximum_temperature_c, -limits.minimum_temperature_c), "temperature span"))
        hot_factor = max(0.0, _sum((1.0, -checked_divide(
            _sum((sample.temperature_c, -limits.maximum_temperature_c), "hot delta"), span, "hot derating")),
            "hot factor"))
    else:
        hot_factor = 1.0
    temperature_factor = bounded_fraction(min(cold_factor, hot_factor), "temperature_factor")

    if limits.maximum_precipitation_mm_h > 0:
        precipitation_factor = max(0.0, _sum((1.0, -checked_divide(
            sample.precipitation_mm_h, limits.maximum_precipitation_mm_h, "precipitation derating")),
            "precipitation factor"))
    else:
        precipitation_factor = 1.0 if sample.precipitation_mm_h == 0 else 0.0
    if limits.maximum_wind_speed_mps > 0:
        wind_factor = max(0.0, _sum((1.0, -checked_divide(
            sample.wind_speed_mps, limits.maximum_wind_speed_mps, "wind derating")), "wind factor"))
    else:
        wind_factor = 1.0 if sample.wind_speed_mps == 0 else 0.0
    precipitation_factor = bounded_fraction(precipitation_factor, "precipitation_factor")
    wind_factor = bounded_fraction(wind_factor, "wind_factor")
    combined = bounded_fraction(_product(temperature_factor, precipitation_factor, wind_factor,
                                         name="combined_available_fraction"), "combined_available_fraction")
    stops = []
    if sample.temperature_c < limits.minimum_temperature_c:
        stops.append(WeatherStopCondition.COLD_THRESHOLD)
    if sample.temperature_c > limits.maximum_temperature_c:
        stops.append(WeatherStopCondition.HOT_THRESHOLD)
    if sample.precipitation_mm_h > limits.maximum_precipitation_mm_h:
        stops.append(WeatherStopCondition.PRECIPITATION_THRESHOLD)
    if sample.wind_speed_mps > limits.maximum_wind_speed_mps:
        stops.append(WeatherStopCondition.WIND_THRESHOLD)
    return WeatherDeratingResult(temperature_factor, precipitation_factor, wind_factor, combined, tuple(stops))


def evaluate_physics(model: PhysicsInput) -> PhysicsResult:
    if not isinstance(model, PhysicsInput):
        raise ConfigError("model must be PhysicsInput")
    if not isinstance(model.analysis_id, str) or not model.analysis_id.strip():
        raise ConfigError("analysis_id must be a non-empty string")
    _validate_provenance(model.provenance)
    if not isinstance(model.required_human_gate_ids, tuple) or not model.required_human_gate_ids:
        raise ConfigError("required_human_gate_ids must be a non-empty tuple")
    if len(set(model.required_human_gate_ids)) != len(model.required_human_gate_ids):
        raise ConfigError("required_human_gate_ids must be unique")
    if any(not isinstance(gate, str) or re.fullmatch(r"PG-\d{3}", gate) is None
           for gate in model.required_human_gate_ids):
        raise ConfigError("required_human_gate_ids must contain only PG-\\d{3} values")
    return PhysicsResult(
        analysis_id=model.analysis_id,
        status=EvidenceStatus.SIMULATED_UNREVIEWED,
        provenance=model.provenance,
        terramechanics=calculate_terramechanics(model.terramechanics),
        bearing=calculate_bearing(model.bearing),
        slope=calculate_slope(model.slope),
        buoyancy=calculate_buoyancy(model.buoyancy),
        curing=calculate_concrete_curing(model.curing),
        weather=derate_weather(model.weather, model.weather_limits),
        unresolved_human_gate_ids=model.required_human_gate_ids,
    )


_UNIT_SUFFIX_MAP = {
    "_kpa_per_m": "_kPa_per_m", "_kn_m3": "_kN_m3", "_kg_m3": "_kg_m3",
    "_j_mol": "_J_mol", "_mm_h": "_mm_h", "_mps2": "_mps2", "_per_c": "_per_C",
    "_c_h": "_C_h", "_m3": "_m3", "_kpa": "_kPa", "_mps": "_mps", "_rad": "_rad",
    "_kg": "_kg", "_m": "_m", "_n": "_N", "_c": "_C", "_h": "_h",
}


def _camel(name: str) -> str:
    source_suffix, json_suffix = next(
        ((source, target) for source, target in _UNIT_SUFFIX_MAP.items() if name.endswith(source)), ("", "")
    )
    stem = name[:-len(source_suffix)] if source_suffix else name
    parts = stem.split("_")
    return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:]) + json_suffix


def _json_compatible(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {_camel(field.name): _json_compatible(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, tuple):
        return [_json_compatible(item) for item in value]
    if isinstance(value, list):
        return [_json_compatible(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_compatible(item) for key, item in value.items()}
    return value


def physics_result_json(result: PhysicsResult) -> str:
    if not isinstance(result, PhysicsResult):
        raise ConfigError("result must be PhysicsResult")
    if (result.status != EvidenceStatus.SIMULATED_UNREVIEWED
            or result.physical_validation_performed is not False
            or result.construction_authorized is not False
            or result.operational_release is not False
            or not result.unresolved_human_gate_ids):
        raise ConfigError("physics results must remain simulated/unreviewed with unresolved human gates and no release")
    return json.dumps(_json_compatible(result), indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"


def write_physics_result(result: PhysicsResult, output_dir: str | Path) -> Path:
    text = physics_result_json(result)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / "result.json"
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


class PhysicsSimulator:
    """Stateless convenience facade; no hardware, persistent state, or release path."""

    def run(self, model: PhysicsInput) -> PhysicsResult:
        return evaluate_physics(model)
