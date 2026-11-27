# SPDX-License-Identifier: Apache-2.0
"""Deterministic synthetic powertrain and solar-hydrogen trade studies.

The interval ledgers in this module are transparent concept models. They do not
validate equipment, size a certified safety function, authorize energy-system
construction or operation, or calculate safe exposure to noise or exhaust.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
from enum import StrEnum
import json
import math
from pathlib import Path
import re
from typing import Any

from .config import ConfigError, _keys, _mapping, _number, _string, load_json
from .physics import (
    EvidenceStatus,
    SyntheticProvenance,
    _at_least,
    _finite,
    _parse_provenance,
    _product,
    _sum,
    _validate_provenance,
    bounded_fraction,
    checked_divide,
)

HYDROGEN_LHV_KWH_PER_KG = 1000.0 / 30.0
PLATFORM_ID = "OCE-CTL-01"
SCOPE_ID = "BUNKER-01"
UNIT_SYSTEM_ID = "SI"


class PowertrainKind(StrEnum):
    BATTERY_LFP = "BATTERY_LFP"
    SOLAR_H2_PEMFC = "SOLAR_H2_PEMFC"
    SOLAR_H2_ICE = "SOLAR_H2_ICE"
    DIESEL_ICE = "DIESEL_ICE"
    GASOLINE_ICE = "GASOLINE_ICE"


class HydrogenUseCase(StrEnum):
    DAILY_CYCLING = "DAILY_CYCLING"
    SEASONAL_CURTAILMENT = "SEASONAL_CURTAILMENT"
    WINTER_CHP = "WINTER_CHP"


class FuelKind(StrEnum):
    DIESEL = "DIESEL"
    GASOLINE = "GASOLINE"


class EnergyFinding(StrEnum):
    MODELED = "MODELED"
    UNSERVED_ENERGY = "UNSERVED_ENERGY"
    CONFINED_EXHAUST_REVIEW = "CONFINED_" + "EXHAUST_REVIEW"
    PEAK_POWER_EXCEEDED = "PEAK_POWER_EXCEEDED"
    HYDROGEN_REVIEW_REQUIRED = "HYDROGEN_REVIEW_REQUIRED"


@dataclass(frozen=True)
class SolarInterval:
    duration_h: float
    available_dc_energy_kwh: float
    ambient_temperature_c: float


@dataclass(frozen=True)
class ConstructionTask:
    task_id: str
    shaft_energy_kwh: float
    auxiliary_energy_kwh: float
    shaft_to_electric_efficiency: float
    peak_electric_power_kw: float
    recoverable_heat_demand_kwh: float
    confined_excavation: bool
    solar_profile: tuple[SolarInterval, ...]


@dataclass(frozen=True)
class PvSystem:
    nameplate_kw: float
    dc_collection_efficiency: float
    ac_inverter_efficiency: float


@dataclass(frozen=True)
class LfpBatterySystem:
    nominal_energy_kwh: float
    minimum_stored_energy_kwh: float
    maximum_stored_energy_kwh: float
    initial_stored_energy_kwh: float
    charge_efficiency: float
    discharge_efficiency: float
    maximum_charge_power_kw: float
    maximum_discharge_power_kw: float
    source_dba_at_reference_distance: float | None
    reference_distance_m: float | None
    receiver_target_dba: float | None
    cold_reference_temperature_c: float
    cold_derating_per_c: float
    cutoff_temperature_c: float


@dataclass(frozen=True)
class HydrogenSystem:
    electrolyzer_lhv_efficiency: float
    compression_energy_kwh_kg: float
    storage_capacity_kg: float
    initial_stored_kg: float
    pem_fuel_cell_lhv_efficiency: float
    h2_ice_lhv_efficiency: float
    maximum_electrolyzer_power_kw: float
    maximum_reconversion_power_kw: float
    deionized_water_l_per_kg: float
    chp_heat_recovery_fraction: float
    use_case: HydrogenUseCase


@dataclass(frozen=True)
class FuelSystem:
    fuel_kind: FuelKind
    lower_heating_value_kwh_l: float
    generator_efficiency: float
    tank_capacity_l: float
    maximum_electrical_power_kw: float
    fuel_cost_per_l: float
    refill_delivery_round_trip_km: float
    delivery_cost_per_km: float
    source_dba_at_reference_distance: float
    reference_distance_m: float
    receiver_target_dba: float
    exhaust_co_ppm: float
    exhaust_nox_ppm: float


@dataclass(frozen=True)
class MicrogridCostAssumptions:
    solar_capex: float
    battery_capex: float
    electrolyzer_capex: float
    hydrogen_compressor_capex: float
    hydrogen_storage_capex: float
    pem_fuel_cell_capex: float
    h2_ice_capex: float
    diesel_generator_capex: float
    gasoline_generator_capex: float
    service_life_h: float
    battery_maintenance_per_h: float
    hydrogen_inspection_per_h: float
    ice_maintenance_per_h: float
    deionized_water_cost_per_l: float
    currency: str


@dataclass(frozen=True)
class PowertrainInput:
    analysis_id: str
    provenance: SyntheticProvenance
    tasks: tuple[ConstructionTask, ...]
    pv: PvSystem
    battery: LfpBatterySystem
    hydrogen: HydrogenSystem
    fuels: tuple[FuelSystem, FuelSystem]
    costs: MicrogridCostAssumptions


@dataclass(frozen=True)
class NoiseEstimate:
    source_dba: float
    reference_distance_m: float
    target_dba: float
    free_field_geometric_distance_m: float
    confined_space_review_required: bool


@dataclass(frozen=True)
class TaskPathResult:
    task_id: str
    path: PowertrainKind
    required_electrical_energy_kwh: float
    served_energy_kwh: float
    unserved_energy_kwh: float
    solar_direct_kwh: float
    battery_discharge_kwh: float
    hydrogen_electrical_output_kwh: float
    hydrogen_solar_input_kwh: float
    hydrogen_produced_kg: float
    hydrogen_consumed_kg: float
    deionized_water_l: float
    solar_curtailed_kwh: float
    fuel_consumed_l: float
    refill_events: int
    recovered_heat_kwh: float
    unmet_heat_kwh: float
    electrical_round_trip_efficiency: float | None
    noise: NoiseEstimate | None
    conversion_loss_heat_kwh: float
    refill_delivery_km: float
    allocated_capex: float
    operating_cost: float
    currency: str
    findings: tuple[EnergyFinding, ...]
    generator_output_kwh: float = 0.0


@dataclass(frozen=True)
class SystemCapex:
    path: PowertrainKind
    amount: float
    currency: str
    component_keys: tuple[str, ...]


@dataclass(frozen=True)
class PowertrainResult:
    analysis_id: str
    status: EvidenceStatus
    task_results: tuple[TaskPathResult, ...]
    system_capex_by_path: tuple[SystemCapex, ...]
    hydrogen_niche: HydrogenUseCase
    daily_battery_preferred: bool
    comparison_notes: tuple[str, ...]
    unresolved_human_gate_ids: tuple[str, ...]
    physical_validation_performed: bool = False
    operational_release: bool = False


def _enum_member(enum_type: Any, value: Any, name: str) -> Any:
    if not isinstance(value, str):
        raise ConfigError(f"{name} must be a string")
    try:
        return enum_type(value)
    except ValueError as exc:
        raise ConfigError(f"{name} has unsupported value {value!r}") from exc


def _boolean(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigError(f"{name} must be Boolean")
    return value


def _validate_interval(interval: SolarInterval, name: str) -> None:
    if not isinstance(interval, SolarInterval):
        raise ConfigError(f"{name} must be SolarInterval")
    _at_least(interval.duration_h, 0, f"{name}.duration_h", strict=True)
    _at_least(interval.available_dc_energy_kwh, 0, f"{name}.available_dc_energy_kwh")
    _at_least(interval.ambient_temperature_c, -273.15, f"{name}.ambient_temperature_c", strict=True)


def _validate_task(task: ConstructionTask, name: str = "task") -> None:
    if not isinstance(task, ConstructionTask):
        raise ConfigError(f"{name} must be ConstructionTask")
    if not isinstance(task.task_id, str) or not task.task_id.strip():
        raise ConfigError(f"{name}.task_id must be a non-empty string")
    _at_least(task.shaft_energy_kwh, 0, f"{name}.shaft_energy_kwh")
    _at_least(task.auxiliary_energy_kwh, 0, f"{name}.auxiliary_energy_kwh")
    bounded_fraction(task.shaft_to_electric_efficiency, f"{name}.shaft_to_electric_efficiency")
    if task.shaft_to_electric_efficiency == 0:
        raise ConfigError(f"{name}.shaft_to_electric_efficiency must be > 0")
    _at_least(task.peak_electric_power_kw, 0, f"{name}.peak_electric_power_kw")
    _at_least(task.recoverable_heat_demand_kwh, 0, f"{name}.recoverable_heat_demand_kwh")
    _boolean(task.confined_excavation, f"{name}.confined_excavation")
    if not isinstance(task.solar_profile, tuple) or not task.solar_profile:
        raise ConfigError(f"{name}.solar_profile must be a non-empty tuple")
    for index, interval in enumerate(task.solar_profile):
        _validate_interval(interval, f"{name}.solar_profile[{index}]")
    _sum((interval.duration_h for interval in task.solar_profile), f"{name}.duration_h")


def _validate_pv(pv: PvSystem) -> None:
    if not isinstance(pv, PvSystem):
        raise ConfigError("pv must be PvSystem")
    _at_least(pv.nameplate_kw, 0, "pv.nameplate_kw", strict=True)
    for name in ("dc_collection_efficiency", "ac_inverter_efficiency"):
        bounded_fraction(getattr(pv, name), f"pv.{name}")
        if getattr(pv, name) == 0:
            raise ConfigError(f"pv.{name} must be > 0")


def _validate_battery(battery: LfpBatterySystem) -> None:
    if not isinstance(battery, LfpBatterySystem):
        raise ConfigError("battery must be LfpBatterySystem")
    _at_least(battery.nominal_energy_kwh, 0, "battery.nominal_energy_kwh", strict=True)
    _at_least(battery.minimum_stored_energy_kwh, 0, "battery.minimum_stored_energy_kwh")
    maximum = _at_least(battery.maximum_stored_energy_kwh, 0, "battery.maximum_stored_energy_kwh", strict=True)
    initial = _finite(battery.initial_stored_energy_kwh, "battery.initial_stored_energy_kwh")
    if maximum <= battery.minimum_stored_energy_kwh:
        raise ConfigError("battery.maximum_stored_energy_kwh must exceed minimum_stored_energy_kwh")
    if not battery.minimum_stored_energy_kwh <= initial <= maximum:
        raise ConfigError("battery.initial_stored_energy_kwh must lie within its stored-energy bounds")
    for name in ("charge_efficiency", "discharge_efficiency"):
        bounded_fraction(getattr(battery, name), f"battery.{name}")
        if getattr(battery, name) == 0:
            raise ConfigError(f"battery.{name} must be > 0")
    _at_least(battery.maximum_charge_power_kw, 0, "battery.maximum_charge_power_kw", strict=True)
    _at_least(battery.maximum_discharge_power_kw, 0, "battery.maximum_discharge_power_kw", strict=True)
    acoustic = (
        battery.source_dba_at_reference_distance,
        battery.reference_distance_m,
        battery.receiver_target_dba,
    )
    if any(value is None for value in acoustic) and not all(value is None for value in acoustic):
        raise ConfigError("battery acoustic source, reference distance, and receiver target must be all null or all set")
    if all(value is not None for value in acoustic):
        _at_least(acoustic[0], 0, "battery.source_dba_at_reference_distance")
        _at_least(acoustic[1], 0, "battery.reference_distance_m", strict=True)
        _at_least(acoustic[2], 0, "battery.receiver_target_dba", strict=True)
    _finite(battery.cold_reference_temperature_c, "battery.cold_reference_temperature_c")
    _at_least(battery.cold_derating_per_c, 0, "battery.cold_derating_per_c")
    _finite(battery.cutoff_temperature_c, "battery.cutoff_temperature_c")


def _validate_hydrogen(hydrogen: HydrogenSystem) -> None:
    if not isinstance(hydrogen, HydrogenSystem):
        raise ConfigError("hydrogen must be HydrogenSystem")
    for name in ("electrolyzer_lhv_efficiency", "pem_fuel_cell_lhv_efficiency", "h2_ice_lhv_efficiency"):
        bounded_fraction(getattr(hydrogen, name), f"hydrogen.{name}")
        if getattr(hydrogen, name) == 0:
            raise ConfigError(f"hydrogen.{name} must be > 0")
    _at_least(hydrogen.compression_energy_kwh_kg, 0, "hydrogen.compression_energy_kwh_kg")
    _at_least(hydrogen.storage_capacity_kg, 0, "hydrogen.storage_capacity_kg", strict=True)
    _at_least(hydrogen.initial_stored_kg, 0, "hydrogen.initial_stored_kg")
    if hydrogen.initial_stored_kg > hydrogen.storage_capacity_kg:
        raise ConfigError("hydrogen.initial_stored_kg cannot exceed storage_capacity_kg")
    _at_least(hydrogen.maximum_electrolyzer_power_kw, 0, "hydrogen.maximum_electrolyzer_power_kw", strict=True)
    _at_least(hydrogen.maximum_reconversion_power_kw, 0, "hydrogen.maximum_reconversion_power_kw", strict=True)
    if not 9.0 <= _finite(hydrogen.deionized_water_l_per_kg, "hydrogen.deionized_water_l_per_kg") <= 15.0:
        raise ConfigError("hydrogen.deionized_water_l_per_kg must be within [9, 15]")
    bounded_fraction(hydrogen.chp_heat_recovery_fraction, "hydrogen.chp_heat_recovery_fraction")
    if not isinstance(hydrogen.use_case, HydrogenUseCase):
        raise ConfigError("hydrogen.use_case must be HydrogenUseCase")


def _validate_fuel(fuel: FuelSystem, name: str = "fuel") -> None:
    if not isinstance(fuel, FuelSystem):
        raise ConfigError(f"{name} must be FuelSystem")
    if not isinstance(fuel.fuel_kind, FuelKind):
        raise ConfigError(f"{name}.fuel_kind must be FuelKind")
    _at_least(fuel.lower_heating_value_kwh_l, 0, f"{name}.lower_heating_value_kwh_l", strict=True)
    bounded_fraction(fuel.generator_efficiency, f"{name}.generator_efficiency")
    if fuel.generator_efficiency == 0:
        raise ConfigError(f"{name}.generator_efficiency must be > 0")
    for field_name in ("tank_capacity_l", "maximum_electrical_power_kw", "reference_distance_m"):
        _at_least(getattr(fuel, field_name), 0, f"{name}.{field_name}", strict=True)
    for field_name in (
        "fuel_cost_per_l", "refill_delivery_round_trip_km", "delivery_cost_per_km",
        "source_dba_at_reference_distance", "receiver_target_dba", "exhaust_co_ppm", "exhaust_nox_ppm",
    ):
        _at_least(getattr(fuel, field_name), 0, f"{name}.{field_name}")


def _validate_costs(costs: MicrogridCostAssumptions) -> None:
    if not isinstance(costs, MicrogridCostAssumptions):
        raise ConfigError("costs must be MicrogridCostAssumptions")
    for field_name in (
        "solar_capex", "battery_capex", "electrolyzer_capex", "hydrogen_compressor_capex",
        "hydrogen_storage_capex", "pem_fuel_cell_capex", "h2_ice_capex", "diesel_generator_capex",
        "gasoline_generator_capex", "battery_maintenance_per_h", "hydrogen_inspection_per_h",
        "ice_maintenance_per_h", "deionized_water_cost_per_l",
    ):
        _at_least(getattr(costs, field_name), 0, f"costs.{field_name}")
    _at_least(costs.service_life_h, 0, "costs.service_life_h", strict=True)
    if not isinstance(costs.currency, str) or re.fullmatch(r"[A-Z]{3}", costs.currency) is None:
        raise ConfigError("costs.currency must match [A-Z]{3}")


def _validate_model(model: PowertrainInput) -> None:
    if not isinstance(model, PowertrainInput):
        raise ConfigError("model must be PowertrainInput")
    if not isinstance(model.analysis_id, str) or not model.analysis_id.strip():
        raise ConfigError("analysis_id must be a non-empty string")
    _validate_provenance(model.provenance)
    if not isinstance(model.tasks, tuple) or not model.tasks:
        raise ConfigError("tasks must be a non-empty tuple")
    identifiers = []
    for index, task in enumerate(model.tasks):
        _validate_task(task, f"tasks[{index}]")
        identifiers.append(task.task_id)
    if len(set(identifiers)) != len(identifiers):
        raise ConfigError("task IDs must be unique")
    _validate_pv(model.pv)
    _validate_battery(model.battery)
    _validate_hydrogen(model.hydrogen)
    if not isinstance(model.fuels, tuple) or len(model.fuels) != 2:
        raise ConfigError("fuels must contain exactly diesel and gasoline systems")
    _validate_fuel(model.fuels[0], "fuels[0]")
    _validate_fuel(model.fuels[1], "fuels[1]")
    if tuple(fuel.fuel_kind for fuel in model.fuels) != (FuelKind.DIESEL, FuelKind.GASOLINE):
        raise ConfigError("fuels must be in canonical diesel then gasoline order")
    _validate_costs(model.costs)


def _solar_interval(value: Any, name: str) -> SolarInterval:
    data = _mapping(value, name)
    _keys(data, {"duration_h", "availableDcEnergy_kWh", "ambientTemperature_C"}, set(), name)
    return SolarInterval(
        _number(data, "duration_h", name, 0, strict_low=True),
        _number(data, "availableDcEnergy_kWh", name, 0),
        _number(data, "ambientTemperature_C", name, -273.15, strict_low=True),
    )


def _construction_task(value: Any, name: str) -> ConstructionTask:
    data = _mapping(value, name)
    required = {
        "taskId", "shaftEnergy_kWh", "auxiliaryEnergy_kWh", "shaftToElectricEfficiency",
        "peakElectricPower_kW", "recoverableHeatDemand_kWh", "confinedExcavation", "solarProfile",
    }
    _keys(data, required, set(), name)
    raw_profile = data["solarProfile"]
    if not isinstance(raw_profile, list) or not raw_profile:
        raise ConfigError(f"{name}.solarProfile must be a non-empty array")
    task = ConstructionTask(
        task_id=_string(data, "taskId", name),
        shaft_energy_kwh=_number(data, "shaftEnergy_kWh", name, 0),
        auxiliary_energy_kwh=_number(data, "auxiliaryEnergy_kWh", name, 0),
        shaft_to_electric_efficiency=_number(data, "shaftToElectricEfficiency", name, 0, 1, strict_low=True),
        peak_electric_power_kw=_number(data, "peakElectricPower_kW", name, 0),
        recoverable_heat_demand_kwh=_number(data, "recoverableHeatDemand_kWh", name, 0),
        confined_excavation=_boolean(data["confinedExcavation"], f"{name}.confinedExcavation"),
        solar_profile=tuple(_solar_interval(item, f"{name}.solarProfile[{index}]")
                            for index, item in enumerate(raw_profile)),
    )
    _validate_task(task, name)
    return task


def _pv_system(value: Any) -> PvSystem:
    data = _mapping(value, "pv")
    _keys(data, {"nameplate_kW", "dcCollectionEfficiency", "acInverterEfficiency"}, set(), "pv")
    pv = PvSystem(
        _number(data, "nameplate_kW", "pv", 0, strict_low=True),
        _number(data, "dcCollectionEfficiency", "pv", 0, 1, strict_low=True),
        _number(data, "acInverterEfficiency", "pv", 0, 1, strict_low=True),
    )
    _validate_pv(pv)
    return pv


def _nullable_number(data: dict[str, Any], key: str, name: str) -> float | None:
    if data[key] is None:
        return None
    return _number(data, key, name)


def _battery_system(value: Any) -> LfpBatterySystem:
    name = "battery"
    data = _mapping(value, name)
    required = {
        "nominalEnergy_kWh", "minimumStoredEnergy_kWh", "maximumStoredEnergy_kWh",
        "initialStoredEnergy_kWh", "chargeEfficiency", "dischargeEfficiency", "maximumChargePower_kW",
        "maximumDischargePower_kW", "sourceDbaAtReferenceDistance", "referenceDistance_m",
        "receiverTargetDba", "coldReferenceTemperature_C", "coldDerating_per_C", "cutoffTemperature_C",
    }
    _keys(data, required, set(), name)
    battery = LfpBatterySystem(
        _number(data, "nominalEnergy_kWh", name, 0, strict_low=True),
        _number(data, "minimumStoredEnergy_kWh", name, 0),
        _number(data, "maximumStoredEnergy_kWh", name, 0, strict_low=True),
        _number(data, "initialStoredEnergy_kWh", name, 0),
        _number(data, "chargeEfficiency", name, 0, 1, strict_low=True),
        _number(data, "dischargeEfficiency", name, 0, 1, strict_low=True),
        _number(data, "maximumChargePower_kW", name, 0, strict_low=True),
        _number(data, "maximumDischargePower_kW", name, 0, strict_low=True),
        _nullable_number(data, "sourceDbaAtReferenceDistance", name),
        _nullable_number(data, "referenceDistance_m", name),
        _nullable_number(data, "receiverTargetDba", name),
        _number(data, "coldReferenceTemperature_C", name),
        _number(data, "coldDerating_per_C", name, 0),
        _number(data, "cutoffTemperature_C", name),
    )
    _validate_battery(battery)
    return battery


def _hydrogen_system(value: Any) -> HydrogenSystem:
    name = "hydrogen"
    data = _mapping(value, name)
    required = {
        "electrolyzerLhvEfficiency", "compressionEnergy_kWh_kg", "storageCapacity_kg", "initialStored_kg",
        "pemFuelCellLhvEfficiency", "h2IceLhvEfficiency", "maximumElectrolyzerPower_kW",
        "maximumReconversionPower_kW", "deionizedWater_l_per_kg", "chpHeatRecoveryFraction", "useCase",
    }
    _keys(data, required, set(), name)
    hydrogen = HydrogenSystem(
        _number(data, "electrolyzerLhvEfficiency", name, 0, 1, strict_low=True),
        _number(data, "compressionEnergy_kWh_kg", name, 0),
        _number(data, "storageCapacity_kg", name, 0, strict_low=True),
        _number(data, "initialStored_kg", name, 0),
        _number(data, "pemFuelCellLhvEfficiency", name, 0, 1, strict_low=True),
        _number(data, "h2IceLhvEfficiency", name, 0, 1, strict_low=True),
        _number(data, "maximumElectrolyzerPower_kW", name, 0, strict_low=True),
        _number(data, "maximumReconversionPower_kW", name, 0, strict_low=True),
        _number(data, "deionizedWater_l_per_kg", name, 9, 15),
        _number(data, "chpHeatRecoveryFraction", name, 0, 1),
        _enum_member(HydrogenUseCase, data["useCase"], f"{name}.useCase"),
    )
    _validate_hydrogen(hydrogen)
    return hydrogen


def _fuel_system(value: Any, name: str) -> FuelSystem:
    data = _mapping(value, name)
    required = {
        "fuelKind", "lowerHeatingValue_kWh_l", "generatorEfficiency", "tankCapacity_l",
        "maximumElectricalPower_kW", "fuelCostPer_l", "refillDeliveryRoundTrip_km", "deliveryCostPer_km",
        "sourceDbaAtReferenceDistance", "referenceDistance_m", "receiverTargetDba", "exhaustCo_ppm", "exhaustNox_ppm",
    }
    _keys(data, required, set(), name)
    fuel = FuelSystem(
        _enum_member(FuelKind, data["fuelKind"], f"{name}.fuelKind"),
        _number(data, "lowerHeatingValue_kWh_l", name, 0, strict_low=True),
        _number(data, "generatorEfficiency", name, 0, 1, strict_low=True),
        _number(data, "tankCapacity_l", name, 0, strict_low=True),
        _number(data, "maximumElectricalPower_kW", name, 0, strict_low=True),
        _number(data, "fuelCostPer_l", name, 0),
        _number(data, "refillDeliveryRoundTrip_km", name, 0),
        _number(data, "deliveryCostPer_km", name, 0),
        _number(data, "sourceDbaAtReferenceDistance", name, 0),
        _number(data, "referenceDistance_m", name, 0, strict_low=True),
        _number(data, "receiverTargetDba", name, 0),
        _number(data, "exhaustCo_ppm", name, 0),
        _number(data, "exhaustNox_ppm", name, 0),
    )
    _validate_fuel(fuel, name)
    return fuel


def _cost_assumptions(value: Any) -> MicrogridCostAssumptions:
    name = "costs"
    data = _mapping(value, name)
    required = {
        "solarCapex", "batteryCapex", "electrolyzerCapex", "hydrogenCompressorCapex",
        "hydrogenStorageCapex", "pemFuelCellCapex", "h2IceCapex", "dieselGeneratorCapex",
        "gasolineGeneratorCapex", "serviceLife_h", "batteryMaintenancePer_h", "hydrogenInspectionPer_h",
        "iceMaintenancePer_h", "deionizedWaterCostPer_l", "currency",
    }
    _keys(data, required, set(), name)
    costs = MicrogridCostAssumptions(
        *(_number(data, key, name, 0) for key in (
            "solarCapex", "batteryCapex", "electrolyzerCapex", "hydrogenCompressorCapex",
            "hydrogenStorageCapex", "pemFuelCellCapex", "h2IceCapex", "dieselGeneratorCapex",
            "gasolineGeneratorCapex",
        )),
        _number(data, "serviceLife_h", name, 0, strict_low=True),
        *(_number(data, key, name, 0) for key in (
            "batteryMaintenancePer_h", "hydrogenInspectionPer_h", "iceMaintenancePer_h", "deionizedWaterCostPer_l",
        )),
        _string(data, "currency", name),
    )
    _validate_costs(costs)
    return costs


def parse_powertrain_input(data: dict[str, Any]) -> PowertrainInput:
    """Parse and validate the exact synthetic microgrid input envelope."""

    _mapping(data, "powertrain")
    required = {
        "spdxLicenseIdentifier", "schemaVersion", "platform", "scope", "unitSystem", "analysisId",
        "provenance", "tasks", "pv", "battery", "hydrogen", "fuels", "costs",
    }
    _keys(data, required, set(), "powertrain")
    constants = {
        "spdxLicenseIdentifier": "CC-BY-SA-4.0",
        "schemaVersion": "1.0.0",
        "platform": PLATFORM_ID,
        "scope": SCOPE_ID,
        "unitSystem": UNIT_SYSTEM_ID,
    }
    for key, expected in constants.items():
        if data[key] != expected:
            raise ConfigError(f"powertrain.{key} must be {expected}")
    raw_tasks = data["tasks"]
    if not isinstance(raw_tasks, list) or not raw_tasks:
        raise ConfigError("powertrain.tasks must be a non-empty array")
    raw_fuels = data["fuels"]
    if not isinstance(raw_fuels, list) or len(raw_fuels) != 2:
        raise ConfigError("powertrain.fuels must contain exactly two entries")
    model = PowertrainInput(
        analysis_id=_string(data, "analysisId", "powertrain"),
        provenance=_parse_provenance(data["provenance"], "powertrain.provenance"),
        tasks=tuple(_construction_task(item, f"tasks[{index}]") for index, item in enumerate(raw_tasks)),
        pv=_pv_system(data["pv"]),
        battery=_battery_system(data["battery"]),
        hydrogen=_hydrogen_system(data["hydrogen"]),
        fuels=(
            _fuel_system(raw_fuels[0], "fuels[0]"),
            _fuel_system(raw_fuels[1], "fuels[1]"),
        ),
        costs=_cost_assumptions(data["costs"]),
    )
    _validate_model(model)
    return model


def load_powertrain_input(path: str | Path) -> PowertrainInput:
    return parse_powertrain_input(load_json(path))


def battery_temperature_factor(temperature_c: float, battery: LfpBatterySystem) -> float:
    """Return the declared cold capacity/power factor, with no warmth bonus."""

    _validate_battery(battery)
    temperature = _finite(temperature_c, "temperature_c")
    if temperature >= battery.cold_reference_temperature_c:
        return 1.0
    if temperature <= battery.cutoff_temperature_c:
        return 0.0
    delta = _sum((battery.cold_reference_temperature_c, -temperature), "battery cold delta")
    return bounded_fraction(max(0.0, _sum((
        1.0, -_product(battery.cold_derating_per_c, delta, name="battery cold derating"),
    ), "battery temperature factor")), "battery_temperature_factor")


def _converter_efficiency(system: HydrogenSystem, converter: PowertrainKind) -> float:
    if converter is PowertrainKind.SOLAR_H2_PEMFC:
        return system.pem_fuel_cell_lhv_efficiency
    if converter is PowertrainKind.SOLAR_H2_ICE:
        return system.h2_ice_lhv_efficiency
    raise ConfigError("converter must be SOLAR_H2_PEMFC or SOLAR_H2_ICE")


def hydrogen_round_trip_efficiency(
    system: HydrogenSystem, inverter_efficiency: float, converter: PowertrainKind,
) -> float:
    """Return net AC output divided by shared electrolyzer/compressor solar input."""

    _validate_hydrogen(system)
    bounded_fraction(inverter_efficiency, "inverter_efficiency")
    if inverter_efficiency == 0:
        raise ConfigError("inverter_efficiency must be > 0")
    converter_efficiency = _converter_efficiency(system, converter)
    numerator = _product(
        system.electrolyzer_lhv_efficiency, converter_efficiency, inverter_efficiency,
        name="hydrogen round-trip numerator",
    )
    denominator = _sum((1.0, checked_divide(
        _product(system.electrolyzer_lhv_efficiency, system.compression_energy_kwh_kg,
                 name="electrolyzer-compression product"),
        HYDROGEN_LHV_KWH_PER_KG, "hydrogen compression denominator",
    )), "hydrogen round-trip denominator")
    return bounded_fraction(checked_divide(numerator, denominator, "hydrogen_round_trip_efficiency"),
                            "hydrogen_round_trip_efficiency")


def estimate_free_field_noise(
    source_dba: float, reference_distance_m: float, target_dba: float, confined: bool,
) -> NoiseEstimate:
    """Estimate only geometric spreading to a target level, never compliance."""

    source = _at_least(source_dba, 0, "source_dba")
    reference = _at_least(reference_distance_m, 0, "reference_distance_m", strict=True)
    target = _at_least(target_dba, 0, "target_dba")
    _boolean(confined, "confined")
    if target >= source:
        radius = reference
    else:
        exponent = checked_divide(_sum((source, -target), "noise level difference"), 20.0, "noise exponent")
        try:
            ratio = _finite(math.pow(10.0, exponent), "noise distance ratio")
        except OverflowError as exc:
            raise ConfigError("calculation produced a non-finite noise distance") from exc
        radius = _product(reference, ratio, name="free_field_geometric_distance_m")
    return NoiseEstimate(source, reference, target, max(reference, radius), confined)


def _required_electrical_energy(task: ConstructionTask) -> float:
    return _sum((checked_divide(task.shaft_energy_kwh, task.shaft_to_electric_efficiency,
                                "shaft electrical energy"), task.auxiliary_energy_kwh),
                "required_electrical_energy_kwh")


def _task_duration(task: ConstructionTask) -> float:
    return _sum((interval.duration_h for interval in task.solar_profile), "task duration_h")


def _interval_load(total: float, interval: SolarInterval, duration_h: float, name: str) -> float:
    return _product(total, checked_divide(interval.duration_h, duration_h, f"{name} duration fraction"), name=name)


def _charge_battery(
    stored_kwh: float, surplus_kwh: float, duration_h: float, temperature_factor: float,
    battery: LfpBatterySystem,
) -> tuple[float, float, float]:
    room = _product(max(0.0, _sum((battery.maximum_stored_energy_kwh, -stored_kwh),
                                  "battery charge room")), temperature_factor, name="derated battery charge room")
    power_limit = _product(battery.maximum_charge_power_kw, temperature_factor, duration_h,
                           name="battery charge interval limit")
    capacity_input = checked_divide(room, battery.charge_efficiency, "battery charge capacity input")
    charge_input = min(surplus_kwh, power_limit, capacity_input)
    stored_gain = _product(charge_input, battery.charge_efficiency, name="battery stored charge")
    new_stored = _sum((stored_kwh, stored_gain), "battery stored energy")
    loss = _sum((charge_input, -stored_gain), "battery charge loss")
    return new_stored, _sum((surplus_kwh, -charge_input), "remaining solar surplus"), loss


def _discharge_battery(
    stored_kwh: float, deficit_kwh: float, duration_h: float, temperature_factor: float,
    battery: LfpBatterySystem,
) -> tuple[float, float, float]:
    accessible = _product(max(0.0, _sum((stored_kwh, -battery.minimum_stored_energy_kwh),
                                        "battery accessible stored energy")), temperature_factor,
                          name="derated battery accessible energy")
    storage_output = _product(accessible, battery.discharge_efficiency, name="battery storage-limited output")
    power_limit = _product(battery.maximum_discharge_power_kw, temperature_factor, duration_h,
                           name="battery discharge interval limit")
    output = min(deficit_kwh, storage_output, power_limit)
    withdrawn = checked_divide(output, battery.discharge_efficiency, "battery stored-energy withdrawal")
    new_stored = _sum((stored_kwh, -withdrawn), "battery stored energy")
    loss = _sum((withdrawn, -output), "battery discharge loss")
    return new_stored, output, loss


def _electric_noise(task: ConstructionTask, battery: LfpBatterySystem) -> NoiseEstimate | None:
    if battery.source_dba_at_reference_distance is None:
        return None
    return estimate_free_field_noise(
        battery.source_dba_at_reference_distance,
        battery.reference_distance_m,
        battery.receiver_target_dba,
        task.confined_excavation,
    )


def _findings(
    unserved: float, peak_exceeded: bool, *, hydrogen: bool = False, confined_exhaust: bool = False,
) -> tuple[EnergyFinding, ...]:
    findings = [EnergyFinding.MODELED]
    if unserved > 1e-12:
        findings.append(EnergyFinding.UNSERVED_ENERGY)
    if peak_exceeded:
        findings.append(EnergyFinding.PEAK_POWER_EXCEEDED)
    if confined_exhaust:
        findings.append(EnergyFinding.CONFINED_EXHAUST_REVIEW)
    if hydrogen:
        findings.append(EnergyFinding.HYDROGEN_REVIEW_REQUIRED)
    return tuple(findings)


def simulate_battery_path(
    task: ConstructionTask, pv: PvSystem, battery: LfpBatterySystem, costs: MicrogridCostAssumptions,
) -> TaskPathResult:
    """Dispatch direct collected PV, then LFP charge/discharge, per interval."""

    _validate_task(task)
    _validate_pv(pv)
    _validate_battery(battery)
    _validate_costs(costs)
    required = _required_electrical_energy(task)
    duration = _task_duration(task)
    stored = battery.initial_stored_energy_kwh
    discharge_power_limits = []
    direct_values, discharge_values, curtailed_values, loss_values = [], [], [], []
    for interval in task.solar_profile:
        load = _interval_load(required, interval, duration, "interval electric load")
        collected = _product(interval.available_dc_energy_kwh, pv.dc_collection_efficiency,
                             name="collected solar energy")
        direct = min(load, collected)
        deficit = _sum((load, -direct), "interval electric deficit")
        surplus = _sum((collected, -direct), "interval solar surplus")
        factor = battery_temperature_factor(interval.ambient_temperature_c, battery)
        discharge_power_limits.append(_product(
            battery.maximum_discharge_power_kw, factor, name="temperature-derated battery discharge power",
        ))
        if surplus > 0:
            stored, surplus, charge_loss = _charge_battery(stored, surplus, interval.duration_h, factor, battery)
        else:
            charge_loss = 0.0
        if deficit > 0:
            stored, discharge, discharge_loss = _discharge_battery(
                stored, deficit, interval.duration_h, factor, battery,
            )
        else:
            discharge, discharge_loss = 0.0, 0.0
        direct_values.append(direct)
        discharge_values.append(discharge)
        curtailed_values.append(surplus)
        loss_values.extend((charge_loss, discharge_loss))
    solar_direct = _sum(direct_values, "solar_direct_kwh")
    battery_discharge = _sum(discharge_values, "battery_discharge_kwh")
    served = _sum((solar_direct, battery_discharge), "served_energy_kwh")
    unserved = max(0.0, _sum((required, -served), "unserved_energy_kwh"))
    return TaskPathResult(
        task.task_id, PowertrainKind.BATTERY_LFP, required, served, unserved, solar_direct,
        battery_discharge, 0.0, 0.0, 0.0, 0.0, 0.0,
        _sum(curtailed_values, "solar_curtailed_kwh"), 0.0, 0, 0.0,
        task.recoverable_heat_demand_kwh,
        _product(battery.charge_efficiency, battery.discharge_efficiency, pv.ac_inverter_efficiency,
                 name="battery electrical round-trip efficiency"),
        _electric_noise(task, battery), _sum(loss_values, "conversion_loss_heat_kwh"),
        0.0, 0.0, 0.0, costs.currency,
        _findings(unserved, task.peak_electric_power_kw > min(discharge_power_limits)),
    )


def simulate_hydrogen_path(
    task: ConstructionTask, pv: PvSystem, battery: LfpBatterySystem, hydrogen: HydrogenSystem,
    converter: PowertrainKind, costs: MicrogridCostAssumptions,
) -> TaskPathResult:
    """Dispatch PV/battery first and use residual solar or deficits for hydrogen."""

    _validate_task(task)
    _validate_pv(pv)
    _validate_battery(battery)
    _validate_hydrogen(hydrogen)
    _validate_costs(costs)
    converter_efficiency = _converter_efficiency(hydrogen, converter)
    required = _required_electrical_energy(task)
    duration = _task_duration(task)
    stored_kwh = battery.initial_stored_energy_kwh
    stored_kg = hydrogen.initial_stored_kg
    specific_solar_input = _sum((checked_divide(
        HYDROGEN_LHV_KWH_PER_KG, hydrogen.electrolyzer_lhv_efficiency, "electrolyzer specific energy",
    ), hydrogen.compression_energy_kwh_kg), "hydrogen specific solar input")
    ac_per_kg = _product(HYDROGEN_LHV_KWH_PER_KG, converter_efficiency, pv.ac_inverter_efficiency,
                         name="hydrogen AC output per kilogram")
    direct_values, battery_values, hydrogen_values, solar_h2_values = [], [], [], []
    produced_values, consumed_values, curtailed_values, loss_values, heat_values = [], [], [], [], []
    for interval in task.solar_profile:
        load = _interval_load(required, interval, duration, "interval electric load")
        heat_demand = _interval_load(task.recoverable_heat_demand_kwh, interval, duration, "interval heat demand")
        collected = _product(interval.available_dc_energy_kwh, pv.dc_collection_efficiency,
                             name="collected solar energy")
        direct = min(load, collected)
        deficit = _sum((load, -direct), "interval electric deficit")
        surplus = _sum((collected, -direct), "interval solar surplus")
        factor = battery_temperature_factor(interval.ambient_temperature_c, battery)
        charge_loss = discharge_loss = 0.0
        battery_output = hydrogen_output = produced = consumed = solar_for_h2 = recovered = 0.0
        if surplus > 0:
            stored_kwh, surplus, charge_loss = _charge_battery(
                stored_kwh, surplus, interval.duration_h, factor, battery,
            )
            storage_room = max(0.0, _sum((hydrogen.storage_capacity_kg, -stored_kg), "hydrogen storage room"))
            mass_by_surplus = checked_divide(surplus, specific_solar_input, "hydrogen mass from solar surplus")
            electrolyzer_energy_limit = _product(hydrogen.maximum_electrolyzer_power_kw, interval.duration_h,
                                                name="electrolyzer interval energy limit")
            mass_by_power = checked_divide(electrolyzer_energy_limit,
                                           checked_divide(HYDROGEN_LHV_KWH_PER_KG,
                                                          hydrogen.electrolyzer_lhv_efficiency,
                                                          "electrolyzer specific energy"),
                                           "hydrogen mass from electrolyzer power")
            produced = min(mass_by_surplus, mass_by_power, storage_room)
            solar_for_h2 = _product(produced, specific_solar_input, name="hydrogen_solar_input_kwh")
            surplus = _sum((surplus, -solar_for_h2), "residual curtailed solar")
            stored_kg = _sum((stored_kg, produced), "stored hydrogen mass")
            chemical_energy = _product(produced, HYDROGEN_LHV_KWH_PER_KG, name="produced hydrogen LHV energy")
            electrolyzer_input = _product(produced, checked_divide(
                HYDROGEN_LHV_KWH_PER_KG, hydrogen.electrolyzer_lhv_efficiency, "electrolyzer specific energy",
            ), name="electrolyzer input")
            loss_values.extend((_sum((electrolyzer_input, -chemical_energy), "electrolyzer conversion loss"),
                                _product(produced, hydrogen.compression_energy_kwh_kg,
                                         name="compression energy loss")))
        if deficit > 0:
            stored_kwh, battery_output, discharge_loss = _discharge_battery(
                stored_kwh, deficit, interval.duration_h, factor, battery,
            )
            deficit = _sum((deficit, -battery_output), "post-battery electric deficit")
            mass_by_deficit = checked_divide(deficit, ac_per_kg, "hydrogen mass required by deficit")
            mass_by_power = checked_divide(
                _product(hydrogen.maximum_reconversion_power_kw, interval.duration_h,
                         name="reconversion interval energy limit"),
                ac_per_kg, "hydrogen mass allowed by reconversion power",
            )
            consumed = min(stored_kg, mass_by_deficit, mass_by_power)
            hydrogen_output = _product(consumed, ac_per_kg, name="hydrogen_electrical_output_kwh")
            stored_kg = _sum((stored_kg, -consumed), "stored hydrogen mass")
            thermal_input = _product(consumed, HYDROGEN_LHV_KWH_PER_KG, name="hydrogen thermal input")
            loss_values.append(_sum((thermal_input, -hydrogen_output), "hydrogen reconversion loss"))
            if hydrogen.use_case is HydrogenUseCase.WINTER_CHP:
                recovered = min(heat_demand, _product(
                    thermal_input, hydrogen.chp_heat_recovery_fraction, name="recoverable CHP heat",
                ))
        direct_values.append(direct)
        battery_values.append(battery_output)
        hydrogen_values.append(hydrogen_output)
        solar_h2_values.append(solar_for_h2)
        produced_values.append(produced)
        consumed_values.append(consumed)
        curtailed_values.append(surplus)
        heat_values.append(recovered)
        loss_values.extend((charge_loss, discharge_loss))
    solar_direct = _sum(direct_values, "solar_direct_kwh")
    battery_discharge = _sum(battery_values, "battery_discharge_kwh")
    hydrogen_output = _sum(hydrogen_values, "hydrogen_electrical_output_kwh")
    served = _sum((solar_direct, battery_discharge, hydrogen_output), "served_energy_kwh")
    unserved = max(0.0, _sum((required, -served), "unserved_energy_kwh"))
    produced_total = _sum(produced_values, "hydrogen_produced_kg")
    recovered_total = _sum(heat_values, "recovered_heat_kwh")
    return TaskPathResult(
        task.task_id, converter, required, served, unserved, solar_direct, battery_discharge,
        hydrogen_output, _sum(solar_h2_values, "hydrogen_solar_input_kwh"), produced_total,
        _sum(consumed_values, "hydrogen_consumed_kg"),
        _product(produced_total, hydrogen.deionized_water_l_per_kg, name="deionized_water_l"),
        _sum(curtailed_values, "solar_curtailed_kwh"), 0.0, 0, recovered_total,
        _sum((task.recoverable_heat_demand_kwh, -recovered_total), "unmet_heat_kwh"),
        hydrogen_round_trip_efficiency(hydrogen, pv.ac_inverter_efficiency, converter),
        _electric_noise(task, battery), _sum(loss_values, "conversion_loss_heat_kwh"),
        0.0, 0.0, 0.0, costs.currency,
        _findings(unserved, task.peak_electric_power_kw > hydrogen.maximum_reconversion_power_kw, hydrogen=True),
    )


def simulate_fuel_path(
    task: ConstructionTask, pv: PvSystem, fuel: FuelSystem, path: PowertrainKind,
    costs: MicrogridCostAssumptions,
) -> TaskPathResult:
    """Run a PV-first fossil-generator comparator with independent logistics."""

    _validate_task(task)
    _validate_pv(pv)
    _validate_fuel(fuel)
    _validate_costs(costs)
    expected = ((PowertrainKind.DIESEL_ICE, FuelKind.DIESEL),
                (PowertrainKind.GASOLINE_ICE, FuelKind.GASOLINE))
    if (path, fuel.fuel_kind) not in expected:
        raise ConfigError("fuel kind must match the requested generator path")
    required = _required_electrical_energy(task)
    duration = _task_duration(task)
    direct_values, generated_values, fuel_values, curtailed_values, loss_values = [], [], [], [], []
    for interval in task.solar_profile:
        load = _interval_load(required, interval, duration, "interval electric load")
        collected = _product(interval.available_dc_energy_kwh, pv.dc_collection_efficiency,
                             name="collected solar energy")
        direct = min(load, collected)
        deficit = _sum((load, -direct), "interval electric deficit")
        generated = min(deficit, _product(fuel.maximum_electrical_power_kw, interval.duration_h,
                                         name="generator interval energy limit"))
        fuel_used = checked_divide(generated, _product(
            fuel.lower_heating_value_kwh_l, fuel.generator_efficiency, name="generator electrical energy per litre",
        ), "fuel_consumed_l")
        direct_values.append(direct)
        generated_values.append(generated)
        fuel_values.append(fuel_used)
        curtailed_values.append(_sum((collected, -direct), "solar_curtailed_kwh"))
        loss_values.append(_sum((_product(fuel_used, fuel.lower_heating_value_kwh_l,
                                          name="fuel chemical input"), -generated), "generator conversion loss"))
    solar_direct = _sum(direct_values, "solar_direct_kwh")
    generated_total = _sum(generated_values, "generator electrical output")
    served = _sum((solar_direct, generated_total), "served_energy_kwh")
    unserved = max(0.0, _sum((required, -served), "unserved_energy_kwh"))
    fuel_total = _sum(fuel_values, "fuel_consumed_l")
    refill_events = max(0, math.ceil(checked_divide(fuel_total, fuel.tank_capacity_l, "tank fill count")) - 1)
    delivery_km = _product(refill_events, fuel.refill_delivery_round_trip_km, name="refill_delivery_km")
    return TaskPathResult(
        task.task_id, path, required, served, unserved, solar_direct, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
        _sum(curtailed_values, "solar_curtailed_kwh"), fuel_total, refill_events, 0.0,
        task.recoverable_heat_demand_kwh, None,
        estimate_free_field_noise(fuel.source_dba_at_reference_distance, fuel.reference_distance_m,
                                  fuel.receiver_target_dba, task.confined_excavation),
        _sum(loss_values, "conversion_loss_heat_kwh"), delivery_km, 0.0, 0.0, costs.currency,
        _findings(unserved, task.peak_electric_power_kw > fuel.maximum_electrical_power_kw,
                  confined_exhaust=task.confined_excavation),
        generator_output_kwh=generated_total,
    )


def _capex_components(path: PowertrainKind) -> tuple[str, ...]:
    components = {
        PowertrainKind.BATTERY_LFP: ("solar_capex", "battery_capex"),
        PowertrainKind.SOLAR_H2_PEMFC: (
            "solar_capex", "battery_capex", "electrolyzer_capex", "hydrogen_compressor_capex",
            "hydrogen_storage_capex", "pem_fuel_cell_capex",
        ),
        PowertrainKind.SOLAR_H2_ICE: (
            "solar_capex", "battery_capex", "electrolyzer_capex", "hydrogen_compressor_capex",
            "hydrogen_storage_capex", "h2_ice_capex",
        ),
        PowertrainKind.DIESEL_ICE: ("solar_capex", "diesel_generator_capex"),
        PowertrainKind.GASOLINE_ICE: ("solar_capex", "gasoline_generator_capex"),
    }
    if not isinstance(path, PowertrainKind):
        raise ConfigError("path must be PowertrainKind")
    return components[path]


def allocate_task_cost(
    path: PowertrainKind, duration_h: float, task_result: TaskPathResult, model: PowertrainInput,
) -> tuple[float, float]:
    """Return life-prorated CAPEX and separate task operating cost."""

    _validate_model(model)
    if not isinstance(task_result, TaskPathResult) or task_result.path is not path:
        raise ConfigError("task_result must be a TaskPathResult for the requested path")
    duration = _at_least(duration_h, 0, "duration_h")
    components = _capex_components(path)
    capex = _sum((getattr(model.costs, key) for key in components), "system CAPEX")
    allocated = _product(capex, checked_divide(duration, model.costs.service_life_h, "service-life fraction"),
                         name="allocated_capex")
    costs = model.costs
    if path is PowertrainKind.BATTERY_LFP:
        operating = _product(costs.battery_maintenance_per_h, duration, name="battery maintenance")
    elif path in (PowertrainKind.SOLAR_H2_PEMFC, PowertrainKind.SOLAR_H2_ICE):
        operating = _sum((
            _product(task_result.deionized_water_l, costs.deionized_water_cost_per_l, name="water cost"),
            _product(costs.battery_maintenance_per_h, duration, name="battery maintenance"),
            _product(costs.hydrogen_inspection_per_h, duration, name="hydrogen inspection reserve"),
        ), "hydrogen operating_cost")
    else:
        fuel = model.fuels[0] if path is PowertrainKind.DIESEL_ICE else model.fuels[1]
        operating = _sum((
            _product(task_result.fuel_consumed_l, fuel.fuel_cost_per_l, name="fuel cost"),
            _product(task_result.refill_delivery_km, fuel.delivery_cost_per_km, name="delivery cost"),
            _product(costs.ice_maintenance_per_h, duration, name="ICE maintenance"),
        ), "fuel operating_cost")
    return _finite(allocated, "allocated_capex"), _finite(operating, "operating_cost")


def _finalize_costs(task: ConstructionTask, result: TaskPathResult, model: PowertrainInput) -> TaskPathResult:
    allocated, operating = allocate_task_cost(result.path, _task_duration(task), result, model)
    return replace(result, allocated_capex=allocated, operating_cost=operating)


def _path_results(results: tuple[TaskPathResult, ...], path: PowertrainKind) -> list[TaskPathResult]:
    return [result for result in results if result.path is path]


def compare_powertrains(model: PowertrainInput) -> PowertrainResult:
    """Evaluate all five paths independently from the same configured states."""

    _validate_model(model)
    paths = (
        PowertrainKind.BATTERY_LFP,
        PowertrainKind.SOLAR_H2_PEMFC,
        PowertrainKind.SOLAR_H2_ICE,
        PowertrainKind.DIESEL_ICE,
        PowertrainKind.GASOLINE_ICE,
    )
    results = []
    for task in model.tasks:
        initial = (
            simulate_battery_path(task, model.pv, model.battery, model.costs),
            simulate_hydrogen_path(task, model.pv, model.battery, model.hydrogen,
                                   PowertrainKind.SOLAR_H2_PEMFC, model.costs),
            simulate_hydrogen_path(task, model.pv, model.battery, model.hydrogen,
                                   PowertrainKind.SOLAR_H2_ICE, model.costs),
            simulate_fuel_path(task, model.pv, model.fuels[0], PowertrainKind.DIESEL_ICE, model.costs),
            simulate_fuel_path(task, model.pv, model.fuels[1], PowertrainKind.GASOLINE_ICE, model.costs),
        )
        results.extend(_finalize_costs(task, result, model) for result in initial)
    result_tuple = tuple(results)
    system_capex = tuple(SystemCapex(
        path,
        _sum((getattr(model.costs, key) for key in _capex_components(path)), "system CAPEX"),
        model.costs.currency,
        _capex_components(path),
    ) for path in paths)
    battery_results = _path_results(result_tuple, PowertrainKind.BATTERY_LFP)
    pem_results = _path_results(result_tuple, PowertrainKind.SOLAR_H2_PEMFC)
    battery_efficiency = battery_results[0].electrical_round_trip_efficiency
    hydrogen_efficiency = pem_results[0].electrical_round_trip_efficiency
    battery_losses = _sum((item.conversion_loss_heat_kwh for item in battery_results), "battery comparison losses")
    hydrogen_losses = _sum((item.conversion_loss_heat_kwh for item in pem_results), "hydrogen comparison losses")
    battery_served = _sum((item.served_energy_kwh for item in battery_results), "battery served energy")
    hydrogen_served = _sum((item.served_energy_kwh for item in pem_results), "hydrogen served energy")
    battery_loss_rate = checked_divide(1.0, battery_efficiency, "battery loss-rate reciprocal") - 1.0
    hydrogen_loss_rate = checked_divide(1.0, hydrogen_efficiency, "hydrogen loss-rate reciprocal") - 1.0
    daily_preferred = bool(
        battery_efficiency > hydrogen_efficiency
        and battery_served >= hydrogen_served
        and battery_loss_rate < hydrogen_loss_rate
    )
    notes = [
        "All energy, cost, logistics, acoustic, and emissions inputs are synthetic, AI-authored, unquoted assumptions.",
        "Battery dispatch is DC-bus arithmetic; its reported system round-trip separately includes charge, discharge, and one AC inverter factor.",
        "Hydrogen round-trip includes shared-surplus electrolysis, compression, one converter efficiency, and one AC inverter factor; unlike paths are not averaged.",
        f"Daily arithmetic: battery round-trip={battery_efficiency:.6f}, PEMFC round-trip={hydrogen_efficiency:.6f}, "
        f"battery conversion losses={battery_losses:.6f} kWh, PEMFC-path conversion losses={hydrogen_losses:.6f} kWh, "
        f"loss rates per delivered kWh={battery_loss_rate:.6f}/{hydrogen_loss_rate:.6f}; "
        f"daily_battery_preferred={str(daily_preferred).lower()} and is not procurement advice.",
        "Allocated task CAPEX is a service-life fraction; systemCapexByPath is a separate unallocated one-time total and is not double-counted.",
        "Conversion-loss heat is an accounting residual only, not a measured infrared signature or a usable-heat guarantee.",
        "Fossil CO/NOx inputs remain source indicators; no plume, dose, ventilation, exposure, or confined-space safe-entry result is calculated.",
    ]
    if not 0.25 <= hydrogen_efficiency <= 0.32:
        notes.append(
            f"WARNING: configured PEMFC electrical round-trip {hydrogen_efficiency:.6f} is outside the 25-32% example range; values were not clamped."
        )
    if model.battery.source_dba_at_reference_distance is None:
        notes.append("Electric acoustic output is null because no measured source triple was supplied; low noise or thermal signature is not inferred.")
    if model.hydrogen.use_case is HydrogenUseCase.DAILY_CYCLING:
        notes.append("DAILY_CYCLING: compare the declared battery and hydrogen efficiencies and losses; battery preference is arithmetic, not universal advice.")
    elif model.hydrogen.use_case is HydrogenUseCase.SEASONAL_CURTAILMENT:
        captured = _sum((item.hydrogen_solar_input_kwh for item in pem_results), "seasonal captured solar")
        notes.append(
            f"SEASONAL_CURTAILMENT: hydrogen captured {captured:.6f} kWh only after direct load and eligible battery charging; "
            "the niche applies to otherwise-curtailed surplus, not routine battery replacement."
        )
    else:
        recovered = _sum((item.recovered_heat_kwh for item in pem_results), "winter CHP heat")
        notes.append(
            f"WINTER_CHP: recovered heat is capped by interval demand and hydrogen LHV input times recovery fraction; modeled total={recovered:.6f} kWh."
        )
    return PowertrainResult(
        analysis_id=model.analysis_id,
        status=EvidenceStatus.SIMULATED_UNREVIEWED,
        task_results=result_tuple,
        system_capex_by_path=system_capex,
        hydrogen_niche=model.hydrogen.use_case,
        daily_battery_preferred=daily_preferred,
        comparison_notes=tuple(notes),
        unresolved_human_gate_ids=(
            "EN-ENERGY-001", "EN-ELECTRICAL-001", "EN-HYDROGEN-001",
            "EN-FIRE-001", "EN-NOISE-001", "EN-AHJ-001",
        ),
    )


_UNIT_SUFFIXES = {
    "_kwh": "_kWh", "_kw": "_kW", "_kg": "_kg", "_km": "_km",
    "_l": "_l", "_m": "_m", "_dba": "_dBA",
}
_MONETARY_FIELDS = {"allocated_capex", "operating_cost", "amount"}


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
        result = {}
        for field in fields(value):
            item = _json_value(getattr(value, field.name))
            if field.name in _MONETARY_FIELDS:
                item = round(item, 6)
                item = 0.0 if item == 0 else item
            result[_camel(field.name)] = item
        return result
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    return value


def _validate_result(result: PowertrainResult) -> None:
    if not isinstance(result, PowertrainResult):
        raise ConfigError("result must be PowertrainResult")
    if (result.status != EvidenceStatus.SIMULATED_UNREVIEWED or not result.unresolved_human_gate_ids
            or result.physical_validation_performed is not False or result.operational_release is not False):
        raise ConfigError("powertrain results must remain simulated/unreviewed with unresolved human gates")
    for item in result.task_results:
        if not isinstance(item, TaskPathResult):
            raise ConfigError("task_results must contain TaskPathResult values")
        required = _finite(item.required_electrical_energy_kwh, "required_electrical_energy_kwh")
        served = _finite(item.served_energy_kwh, "served_energy_kwh")
        unserved = _finite(item.unserved_energy_kwh, "unserved_energy_kwh")
        closure = abs(_sum((served, unserved, -required), "energy closure residual"))
        if closure > 1e-9:
            raise ConfigError(f"task {item.task_id} path {item.path} violates 1e-9 kWh energy closure")
        source_flows = (
            item.solar_direct_kwh, item.battery_discharge_kwh,
            item.hydrogen_electrical_output_kwh, item.generator_output_kwh,
        )
        for flow in source_flows:
            _at_least(flow, 0, "electrical source delivery")
        total_delivery = _sum(source_flows, "electrical source delivery")
        if abs(total_delivery - served) > 1e-9:
            raise ConfigError(f"task {item.task_id} path {item.path} violates 1e-9 kWh source balance")
        _finite(item.conversion_loss_heat_kwh, "conversion_loss_heat_kwh")
        _finite(item.refill_delivery_km, "refill_delivery_km")
        _finite(item.allocated_capex, "allocated_capex")
        _finite(item.operating_cost, "operating_cost")
    for capex in result.system_capex_by_path:
        _at_least(capex.amount, 0, "system CAPEX amount")


def powertrain_result_json(result: PowertrainResult) -> str:
    """Serialize canonical JSON after enforcing every task's energy closure."""

    _validate_result(result)
    compatible = _json_value(result)
    return json.dumps(compatible, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"


def write_powertrain_result(result: PowertrainResult, output_dir: str | Path) -> Path:
    text = powertrain_result_json(result)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / "result.json"
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


class MicrogridSimulator:
    """Stateless convenience facade with no persistent storage or hardware I/O."""

    def run(self, model: PowertrainInput) -> PowertrainResult:
        return compare_powertrains(model)
