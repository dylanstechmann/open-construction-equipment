# SPDX-License-Identifier: Apache-2.0
"""Synthetic BUNKER-01 quantity, dependency-schedule and energy accounting.

This is deterministic host-side arithmetic for a civilian non-habitable utility
 enclosure concept. It is not structural/excavation design, a procurement or
 borrow/haul decision, a permit package, or authorization for any physical work.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
import heapq
import html
import json
import math
from pathlib import Path
import re
import textwrap
from typing import Any, Iterable

from .config import ConfigError, _keys, _mapping, _number, _string, load_json

PROJECT_ID = "BUNKER-01"
READINESS_STATUS_ID = "BLOCKED_UNRESOLVED_HUMAN_GATES"
ALLOWED_AUTONOMY_CLASSES = (
    "future_supervised_autonomy",
    "human_gate",
    "simulation_candidate",
    "specialist",
)
_WORK_HEADER = [
    "id", "name", "dependencies", "durationHours", "autonomyClass", "fleetRole",
    "requiredGateIds", "evidenceStatus",
]
_GATE_HEADER = [
    "gateId", "name", "relatedWorkPackages", "requiredEvidence", "acceptanceAuthority",
    "status", "decisionDate", "reviewer", "signature", "evidenceReference",
]
_FLEET_HEADER = [
    "fleetId", "role", "platformOrSystem", "intendedFutureWorkPackages", "availability",
    "currentCapability", "capabilityGaps", "energyModelLinkage", "humanControlAndEvidenceRequired",
]
_ID_PATTERNS = {
    "work package": re.compile(r"BW-\d{3}\Z"),
    "quality gate": re.compile(r"BG-\d{3}\Z"),
    "fleet": re.compile(r"BF-\d{3}\Z"),
}


@dataclass(frozen=True)
class Provenance:
    source_type: str
    statement: str
    ai_authored: bool
    owner_supplied: bool
    site_supplied: bool
    physical_validation_performed: bool


@dataclass(frozen=True)
class Geometry:
    internal_length_m: float
    internal_width_m: float
    internal_height_m: float
    wall_thickness_m: float
    floor_thickness_m: float
    roof_thickness_m: float
    working_space_m: float
    drainage_layer_m: float
    roof_cover_m: float
    provenance: Provenance


@dataclass(frozen=True)
class SoilModel:
    loose_bulking_factor: float
    compacted_to_in_situ_ratio: float
    provenance: Provenance


@dataclass(frozen=True)
class WasteModel:
    concrete_waste_fraction: float
    waterproofing_waste_fraction: float
    provenance: Provenance


@dataclass(frozen=True)
class EnergyAssumption:
    package_id: str
    fleet_id: str
    electric_energy_kwh: float
    basis: str
    provenance: Provenance


@dataclass(frozen=True)
class BunkerPlanInput:
    synthetic_notice: str
    provenance: Provenance
    geometry: Geometry
    soil: SoilModel
    waste: WasteModel
    energy_assumptions: tuple[EnergyAssumption, ...]


@dataclass(frozen=True)
class WorkPackage:
    package_id: str
    name: str
    dependencies: tuple[str, ...]
    duration_hours: float
    autonomy_class: str
    fleet_role: str
    required_gate_ids: tuple[str, ...]
    evidence_status: str


@dataclass(frozen=True)
class QualityGate:
    gate_id: str
    name: str
    related_work_packages: tuple[str, ...]
    required_evidence: str
    acceptance_authority: str
    status: str


@dataclass(frozen=True)
class FleetEntry:
    fleet_id: str
    role: str
    platform_or_system: str
    intended_work_packages: tuple[str, ...]
    availability: str
    current_capability: str
    capability_gaps: str
    energy_model_linkage: str
    human_control_and_evidence_required: str


@dataclass(frozen=True)
class BunkerRegisters:
    packages: tuple[WorkPackage, ...]
    gates: tuple[QualityGate, ...]
    fleet: tuple[FleetEntry, ...]


@dataclass(frozen=True)
class SiteStatus:
    site_known: bool
    construction_authorized: bool
    physical_validation_performed: bool
    status: str


def _xml_string(value: Any, name: str) -> str:
    result = _string({"value": value}, "value", name)
    for character in result:
        codepoint = ord(character)
        if not (codepoint in (0x09, 0x0A, 0x0D) or 0x20 <= codepoint <= 0xD7FF
                or 0xE000 <= codepoint <= 0xFFFD or 0x10000 <= codepoint <= 0x10FFFF):
            raise ConfigError(f"{name} contains an XML-illegal control character or unpaired surrogate")
    return result


def _provenance(value: Any, name: str) -> Provenance:
    data = _mapping(value, name)
    required = {
        "sourceType", "statement", "aiAuthored", "ownerSupplied", "siteSupplied",
        "physicalValidationPerformed",
    }
    _keys(data, required, set(), name)
    if data["sourceType"] != "SYNTHETIC_AGENT_AUTHORED":
        raise ConfigError(f"{name}.sourceType must be SYNTHETIC_AGENT_AUTHORED")
    if data["aiAuthored"] is not True:
        raise ConfigError(f"{name}.aiAuthored must be true")
    for key in ("ownerSupplied", "siteSupplied", "physicalValidationPerformed"):
        if data[key] is not False:
            raise ConfigError(f"{name}.{key} must be false")
    return Provenance("SYNTHETIC_AGENT_AUTHORED", _xml_string(data["statement"], name), True, False, False, False)


def _provenance_json(value: Provenance) -> dict[str, Any]:
    return {
        "sourceType": value.source_type,
        "statement": value.statement,
        "aiAuthored": value.ai_authored,
        "ownerSupplied": value.owner_supplied,
        "siteSupplied": value.site_supplied,
        "physicalValidationPerformed": value.physical_validation_performed,
    }


def parse_bunker_input(data: dict[str, Any]) -> BunkerPlanInput:
    """Strictly parse one synthetic SI input; authorization cannot be enabled."""
    required = {
        "spdxLicenseIdentifier", "schemaVersion", "projectId", "planStatus", "unitSystem",
        "siteKnown", "constructionAuthorized", "physicalValidationPerformed", "syntheticNotice",
        "provenance", "geometry", "soilModel", "wasteModel", "energyAssumptions",
    }
    _keys(data, required, set(), "bunker plan")
    constants = {
        "spdxLicenseIdentifier": "CC-BY-SA-4.0",
        "schemaVersion": "1.0.0",
        "projectId": PROJECT_ID,
        "planStatus": "SYNTHETIC_UNREVIEWED",
        "unitSystem": "SI",
    }
    for key, expected in constants.items():
        if data[key] != expected:
            raise ConfigError(f"bunker plan.{key} must be {expected}")
    for key in ("siteKnown", "constructionAuthorized", "physicalValidationPerformed"):
        if data[key] is not False:
            raise ConfigError(f"bunker plan.{key} must be false; no input can authorize physical work")

    raw_geometry = _mapping(data["geometry"], "geometry")
    geometry_fields = {
        "internalLength_m", "internalWidth_m", "internalHeight_m", "wallThickness_m",
        "floorThickness_m", "roofThickness_m", "workingSpace_m", "drainageLayer_m", "roofCover_m",
    }
    _keys(raw_geometry, geometry_fields | {"provenance"}, set(), "geometry")
    positive = ("internalLength_m", "internalWidth_m", "internalHeight_m", "wallThickness_m",
                "floorThickness_m", "roofThickness_m")
    nonnegative = ("workingSpace_m", "drainageLayer_m", "roofCover_m")
    values = {
        key: _number(raw_geometry, key, "geometry", 0, strict_low=key in positive)
        for key in geometry_fields
    }
    geometry = Geometry(
        values["internalLength_m"], values["internalWidth_m"], values["internalHeight_m"],
        values["wallThickness_m"], values["floorThickness_m"], values["roofThickness_m"],
        values["workingSpace_m"], values["drainageLayer_m"], values["roofCover_m"],
        _provenance(raw_geometry["provenance"], "geometry.provenance"),
    )

    raw_soil = _mapping(data["soilModel"], "soilModel")
    _keys(raw_soil, {"looseBulkingFactor", "compactedToInSituRatio", "provenance"}, set(), "soilModel")
    soil = SoilModel(
        _number(raw_soil, "looseBulkingFactor", "soilModel", 0, strict_low=True),
        _number(raw_soil, "compactedToInSituRatio", "soilModel", 0, strict_low=True),
        _provenance(raw_soil["provenance"], "soilModel.provenance"),
    )
    raw_waste = _mapping(data["wasteModel"], "wasteModel")
    _keys(raw_waste, {"concreteWasteFraction", "waterproofingWasteFraction", "provenance"}, set(), "wasteModel")
    waste = WasteModel(
        _number(raw_waste, "concreteWasteFraction", "wasteModel", 0),
        _number(raw_waste, "waterproofingWasteFraction", "wasteModel", 0),
        _provenance(raw_waste["provenance"], "wasteModel.provenance"),
    )

    raw_energy = data["energyAssumptions"]
    if not isinstance(raw_energy, list):
        raise ConfigError("energyAssumptions must be an array")
    assumptions: list[EnergyAssumption] = []
    pairs: set[tuple[str, str]] = set()
    for index, item in enumerate(raw_energy):
        name = f"energyAssumptions[{index}]"
        entry = _mapping(item, name)
        _keys(entry, {"packageId", "fleetId", "electricEnergy_kWh", "basis", "provenance"}, set(), name)
        package_id = _identifier(entry, "packageId", "work package", name)
        fleet_id = _identifier(entry, "fleetId", "fleet", name)
        pair = (package_id, fleet_id)
        if pair in pairs:
            raise ConfigError(f"duplicate energy assumption for {package_id}/{fleet_id}")
        pairs.add(pair)
        assumptions.append(EnergyAssumption(
            package_id,
            fleet_id,
            _number(entry, "electricEnergy_kWh", name, 0, strict_low=True),
            _xml_string(entry["basis"], f"{name}.basis"),
            _provenance(entry["provenance"], f"{name}.provenance"),
        ))
    return BunkerPlanInput(
        _xml_string(data["syntheticNotice"], "bunker plan.syntheticNotice"),
        _provenance(data["provenance"], "bunker plan.provenance"),
        geometry,
        soil,
        waste,
        tuple(assumptions),
    )


def load_bunker_input(path: str | Path) -> BunkerPlanInput:
    return parse_bunker_input(load_json(path))


def _identifier(data: dict[str, Any], key: str, kind: str, name: str) -> str:
    value = _string(data, key, name)
    if not _ID_PATTERNS[kind].fullmatch(value):
        raise ConfigError(f"{name}.{key} is not a valid {kind} ID")
    return value


def _csv_rows(path: str | Path, expected_header: list[str]) -> list[dict[str, str]]:
    source = Path(path)
    try:
        with source.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle, strict=True)
            if reader.fieldnames != expected_header:
                raise ConfigError(f"{source} CSV header does not match the canonical register")
            rows = list(reader)
            for line, row in enumerate(rows, 2):
                if None in row or any(value is None for value in row.values()):
                    raise ConfigError(f"{source} row {line} has the wrong column count")
    except (OSError, csv.Error) as exc:
        raise ConfigError(f"cannot load {source}: {exc}") from exc
    if not rows:
        raise ConfigError(f"{source} must contain register rows")
    return rows


def _csv_string(row: dict[str, str], key: str, context: str, *, blank: bool = False) -> str:
    value = row.get(key)
    if value is None or (not blank and not value.strip()) or (blank and value is None):
        raise ConfigError(f"{context}.{key} must be a non-empty string" if not blank else f"{context}.{key} is missing")
    result = value.strip()
    return _xml_string(result, context) if result else result


def _ids(value: str, kind: str, context: str, *, blank: bool = False) -> tuple[str, ...]:
    if not value and blank:
        return ()
    parts = value.split(";")
    if any(not part.strip() for part in parts):
        raise ConfigError(f"{context} contains an empty ID")
    result: list[str] = []
    for part in parts:
        item = part.strip()
        if not _ID_PATTERNS[kind].fullmatch(item):
            raise ConfigError(f"{context} contains invalid {kind} ID {item}")
        if item in result:
            raise ConfigError(f"{context} contains duplicate ID {item}")
        result.append(item)
    return tuple(result)


def load_work_breakdown(path: str | Path) -> tuple[WorkPackage, ...]:
    packages: list[WorkPackage] = []
    seen: set[str] = set()
    for index, row in enumerate(_csv_rows(path, _WORK_HEADER), 2):
        context = f"work-breakdown row {index}"
        package_id = _identifier(row, "id", "work package", context)
        if package_id in seen:
            raise ConfigError(f"duplicate work package ID {package_id}")
        seen.add(package_id)
        raw_duration = _csv_string(row, "durationHours", context)
        try:
            duration = _number({"value": float(raw_duration)}, "value", context, 0)
        except (ValueError, OverflowError) as exc:
            if isinstance(exc, ConfigError):
                raise
            raise ConfigError(f"{context}.durationHours must be a finite nonnegative number") from exc
        autonomy = _csv_string(row, "autonomyClass", context)
        if autonomy not in ALLOWED_AUTONOMY_CLASSES:
            raise ConfigError(f"{package_id} has unsupported autonomyClass {autonomy}")
        evidence = _csv_string(row, "evidenceStatus", context)
        if evidence not in {"CONCEPT_ONLY", "TBD"}:
            raise ConfigError(f"{package_id} evidenceStatus must remain CONCEPT_ONLY or TBD")
        packages.append(WorkPackage(
            package_id,
            _csv_string(row, "name", context),
            _ids(_csv_string(row, "dependencies", context, blank=True), "work package", f"{package_id}.dependencies", blank=True),
            duration,
            autonomy,
            _csv_string(row, "fleetRole", context),
            _ids(_csv_string(row, "requiredGateIds", context, blank=True), "quality gate", f"{package_id}.requiredGateIds", blank=True),
            evidence,
        ))
    by_id = {package.package_id: package for package in packages}
    for package in packages:
        for dependency in package.dependencies:
            if dependency not in by_id:
                raise ConfigError(f"{package.package_id} references missing dependency {dependency}")
            if dependency == package.package_id:
                raise ConfigError(f"{package.package_id} cannot depend on itself")
    _topological_order(by_id)
    return tuple(packages)


def load_quality_gates(path: str | Path) -> tuple[QualityGate, ...]:
    gates: list[QualityGate] = []
    seen: set[str] = set()
    for index, row in enumerate(_csv_rows(path, _GATE_HEADER), 2):
        context = f"quality-gates row {index}"
        gate_id = _identifier(row, "gateId", "quality gate", context)
        if gate_id in seen:
            raise ConfigError(f"duplicate quality gate ID {gate_id}")
        seen.add(gate_id)
        if _csv_string(row, "status", context) != "UNRESOLVED":
            raise ConfigError(f"{gate_id} status must remain UNRESOLVED")
        for key in ("decisionDate", "reviewer", "signature", "evidenceReference"):
            if _csv_string(row, key, context, blank=True):
                raise ConfigError(f"{gate_id}.{key} must be blank while the gate is unresolved")
        gates.append(QualityGate(
            gate_id,
            _csv_string(row, "name", context),
            _ids(_csv_string(row, "relatedWorkPackages", context), "work package", f"{gate_id}.relatedWorkPackages"),
            _csv_string(row, "requiredEvidence", context),
            _csv_string(row, "acceptanceAuthority", context),
            "UNRESOLVED",
        ))
    return tuple(gates)


def load_fleet_register(path: str | Path) -> tuple[FleetEntry, ...]:
    fleet: list[FleetEntry] = []
    seen: set[str] = set()
    for index, row in enumerate(_csv_rows(path, _FLEET_HEADER), 2):
        context = f"fleet-register row {index}"
        fleet_id = _identifier(row, "fleetId", "fleet", context)
        if fleet_id in seen:
            raise ConfigError(f"duplicate fleet ID {fleet_id}")
        seen.add(fleet_id)
        availability = _csv_string(row, "availability", context)
        if availability not in {"concept", "missing", "external_specialist_required"}:
            raise ConfigError(f"{fleet_id} has unsafe or unsupported availability {availability}")
        fleet.append(FleetEntry(
            fleet_id,
            _csv_string(row, "role", context),
            _csv_string(row, "platformOrSystem", context),
            _ids(_csv_string(row, "intendedFutureWorkPackages", context), "work package", f"{fleet_id}.intendedFutureWorkPackages"),
            availability,
            _csv_string(row, "currentCapability", context),
            _csv_string(row, "capabilityGaps", context),
            _csv_string(row, "energyModelLinkage", context),
            _csv_string(row, "humanControlAndEvidenceRequired", context),
        ))
    return tuple(fleet)


def load_bunker_registers(
    work_breakdown: str | Path,
    quality_gates: str | Path,
    fleet_register: str | Path,
) -> BunkerRegisters:
    packages = load_work_breakdown(work_breakdown)
    gates = load_quality_gates(quality_gates)
    fleet = load_fleet_register(fleet_register)
    package_ids = {package.package_id for package in packages}
    gate_ids = {gate.gate_id for gate in gates}
    for package in packages:
        missing = set(package.required_gate_ids) - gate_ids
        if missing:
            raise ConfigError(f"{package.package_id} references missing gates: {', '.join(sorted(missing))}")
    for gate in gates:
        missing = set(gate.related_work_packages) - package_ids
        if missing:
            raise ConfigError(f"{gate.gate_id} references missing related packages: {', '.join(sorted(missing))}")
    for entry in fleet:
        missing = set(entry.intended_work_packages) - package_ids
        if missing:
            raise ConfigError(f"{entry.fleet_id} references missing intended packages: {', '.join(sorted(missing))}")
    _combined_topological_order(_combined_dependencies(
        {package.package_id: package for package in packages},
        {gate.gate_id: gate for gate in gates},
    ))
    return BunkerRegisters(packages, gates, fleet)


def load_bunker_site(path: str | Path) -> SiteStatus:
    data = load_json(path)
    required_top = {
        "spdxLicenseIdentifier", "schemaVersion", "projectId", "status", "siteKnown",
        "constructionAuthorized", "physicalValidationPerformed", "locationPrivacy", "provenance",
        "requiredInputs",
    }
    _keys(data, required_top, set(), "site inputs")
    constants = {
        "spdxLicenseIdentifier": "CC-BY-SA-4.0",
        "schemaVersion": "1.0.0",
        "projectId": PROJECT_ID,
        "status": "CONCEPT_UNREVIEWED",
    }
    for key, expected in constants.items():
        if data[key] != expected:
            raise ConfigError(f"site inputs.{key} must be {expected}")
    for key in ("siteKnown", "constructionAuthorized", "physicalValidationPerformed"):
        if data[key] is not False:
            raise ConfigError(f"site inputs.{key} must be false")
    _string(data, "locationPrivacy", "site inputs")
    _string(data, "provenance", "site inputs")
    required = _mapping(data["requiredInputs"], "site inputs.requiredInputs")
    if not required:
        raise ConfigError("site inputs.requiredInputs must not be empty")
    for key, raw in required.items():
        if not isinstance(key, str) or not key.strip():
            raise ConfigError("site input IDs must be non-empty strings")
        name = f"site inputs.requiredInputs.{key}"
        item = _mapping(raw, name)
        _keys(item, {"value", "status", "reason", "evidenceReference"}, set(), name)
        if item["value"] is not None or item["status"] != "TBD" or item["evidenceReference"] is not None:
            raise ConfigError(f"site input {key} must remain null/TBD with no evidence reference")
        _string(item, "reason", name)
    return SiteStatus(False, False, False, "CONCEPT_UNREVIEWED")


def _finite(value: float, name: str) -> float:
    if not math.isfinite(value):
        raise ConfigError(f"bunker calculation produced non-finite {name}")
    return 0.0 if value == 0 else value


def _sum(values: Iterable[float], name: str) -> float:
    try:
        return _finite(math.fsum(values), name)
    except OverflowError as exc:
        raise ConfigError(f"bunker calculation produced non-finite {name}") from exc


def _product(left: float, right: float, name: str) -> float:
    try:
        result = _finite(left * right, name)
    except OverflowError as exc:
        raise ConfigError(f"bunker calculation produced non-finite {name}") from exc
    if left != 0 and right != 0 and result == 0:
        raise ConfigError(f"bunker calculation underflowed nonzero {name} to zero")
    return result


def _divide(numerator: float, denominator: float, name: str) -> float:
    if denominator <= 0 or not math.isfinite(denominator):
        raise ConfigError(f"bunker calculation has invalid denominator for {name}")
    try:
        result = _finite(numerator / denominator, name)
    except (OverflowError, ZeroDivisionError) as exc:
        raise ConfigError(f"bunker calculation produced non-finite {name}") from exc
    if numerator != 0 and result == 0:
        raise ConfigError(f"bunker calculation underflowed nonzero {name} to zero")
    return result


def calculate_quantities(model: BunkerPlanInput) -> dict[str, Any]:
    """Apply the documented gross geometric conventions with checked arithmetic."""
    g = model.geometry
    external_length = _sum((g.internal_length_m, _product(2, g.wall_thickness_m, "wall thickness")), "external length")
    external_width = _sum((g.internal_width_m, _product(2, g.wall_thickness_m, "wall thickness")), "external width")
    structure_height = _sum((g.floor_thickness_m, g.internal_height_m, g.roof_thickness_m), "structure height")
    excavation_length = _sum((external_length, _product(2, g.working_space_m, "working space")), "excavation length")
    excavation_width = _sum((external_width, _product(2, g.working_space_m, "working space")), "excavation width")
    excavation_depth = _sum((g.drainage_layer_m, structure_height, g.roof_cover_m), "excavation depth")
    external_footprint = _product(external_length, external_width, "external footprint")
    excavation_footprint = _product(excavation_length, excavation_width, "excavation footprint")
    excavation_volume = _product(excavation_footprint, excavation_depth, "excavation volume")
    floor = _product(external_footprint, g.floor_thickness_m, "floor concrete")
    roof = _product(external_footprint, g.roof_thickness_m, "roof concrete")
    external_shell = _product(external_footprint, g.internal_height_m, "external wall shell")
    clear_internal = _product(_product(g.internal_length_m, g.internal_width_m, "internal footprint"), g.internal_height_m, "clear internal volume")
    walls = _finite(external_shell - clear_internal, "wall-shell concrete")
    if walls <= 0:
        raise ConfigError("positive wall geometry collapsed to non-positive wall-shell concrete")
    gross_concrete = _sum((floor, roof, walls), "gross concrete")
    drainage = _product(excavation_footprint, g.drainage_layer_m, "drainage gross volume")
    displacement = _product(external_footprint, structure_height, "enclosure displacement")
    backfill = _finite(excavation_volume - displacement - drainage, "nominal backfill")
    if backfill < 0:
        raise ConfigError("impossible geometry: nominal backfill is negative")
    if backfill == 0 and (g.working_space_m > 0 or g.roof_cover_m > 0):
        raise ConfigError("positive backfill geometry collapsed to zero through floating-point cancellation")
    loose_spoil = _product(excavation_volume, model.soil.loose_bulking_factor, "loose excavated spoil")
    required_in_situ = _divide(backfill, model.soil.compacted_to_in_situ_ratio, "in-situ equivalent backfill")
    excess_in_situ = _finite(excavation_volume - required_in_situ, "excess in-situ soil")
    excess_loose = _product(max(0.0, excess_in_situ), model.soil.loose_bulking_factor, "excess loose haul-off")
    mathematical_deficit = _finite(max(0.0, -excess_in_situ), "mathematical in-situ deficit")
    vertical_sides = _product(_product(2, _sum((external_length, external_width), "external perimeter"), "external perimeter"), structure_height, "vertical waterproofing")
    waterproof_net = _sum((external_footprint, vertical_sides), "net waterproofing")
    waterproof_adjusted = _product(waterproof_net, _sum((1, model.waste.waterproofing_waste_fraction), "waterproofing waste multiplier"), "adjusted waterproofing")
    concrete_adjusted = _product(gross_concrete, _sum((1, model.waste.concrete_waste_fraction), "concrete waste multiplier"), "adjusted concrete")
    return {
        "geometry": {
            "externalLength_m": external_length,
            "externalWidth_m": external_width,
            "totalStructureHeight_m": structure_height,
            "externalFootprint_m2": external_footprint,
            "excavationLength_m": excavation_length,
            "excavationWidth_m": excavation_width,
            "excavationDepth_m": excavation_depth,
            "excavationFootprint_m2": excavation_footprint,
            "excavationVolume_m3": excavation_volume,
            "enclosureDisplacement_m3": displacement,
        },
        "concrete": {
            "floorVolume_m3": floor,
            "roofVolume_m3": roof,
            "wallShellVolume_m3": walls,
            "grossVolume_m3": gross_concrete,
            "theoreticalAdjustedVolume_m3": concrete_adjusted,
            "orderQuantity": False,
            "convention": "Gross floor + roof + external wall shell less clear internal wall volume; no opening deductions or reinforcement estimate.",
        },
        "earthworks": {
            "drainageLayerGrossVolume_m3": drainage,
            "nominalCompactedBackfillVolume_m3": backfill,
            "looseExcavatedSpoilVolume_m3": loose_spoil,
            "inSituEquivalentRequiredForBackfill_m3": required_in_situ,
            "excessInSituVolume_m3": excess_in_situ,
            "excessLooseHaulOffVolume_m3": excess_loose,
            "mathematicalInSituDeficitVolume_m3": mathematical_deficit,
            "borrowOrHaulDecisionMade": False,
            "convention": "Backfill = excavation - enclosure displacement - gross drainage. This geometric nominal is not a compaction specification; a negative excess is only a mathematical deficit, not a borrow decision.",
        },
        "waterproofing": {
            "netArea_m2": waterproof_net,
            "wasteAdjustedArea_m2": waterproof_adjusted,
            "convention": "Roof footprint plus all external vertical sides over total structure height; underside excluded and openings not deducted.",
        },
    }


def _topological_order(packages: dict[str, WorkPackage]) -> tuple[WorkPackage, ...]:
    dependents: dict[str, list[str]] = {package_id: [] for package_id in packages}
    indegree: dict[str, int] = {}
    for package_id, package in packages.items():
        indegree[package_id] = len(package.dependencies)
        for dependency in package.dependencies:
            if dependency not in packages:
                raise ConfigError(f"{package_id} references missing dependency {dependency}")
            dependents[dependency].append(package_id)
    ready = [package_id for package_id, degree in indegree.items() if degree == 0]
    heapq.heapify(ready)
    ordered: list[WorkPackage] = []
    while ready:
        package_id = heapq.heappop(ready)
        ordered.append(packages[package_id])
        for dependent in sorted(dependents[package_id]):
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                heapq.heappush(ready, dependent)
    if len(ordered) != len(packages):
        cyclic = sorted(package_id for package_id, degree in indegree.items() if degree > 0)
        raise ConfigError(f"work-breakdown dependency cycle detected involving: {', '.join(cyclic)}")
    return tuple(ordered)


def _package_node(package_id: str) -> str:
    return f"package:{package_id}"


def _gate_node(gate_id: str) -> str:
    return f"gate:{gate_id}"


def _combined_dependencies(
    packages: dict[str, WorkPackage], gates: dict[str, QualityGate]
) -> dict[str, tuple[str, ...]]:
    dependencies: dict[str, tuple[str, ...]] = {}
    for package_id, package in packages.items():
        missing = set(package.required_gate_ids) - gates.keys()
        if missing:
            raise ConfigError(f"{package_id} references missing gates: {', '.join(sorted(missing))}")
        dependencies[_package_node(package_id)] = tuple(
            [_package_node(dependency) for dependency in package.dependencies]
            + [_gate_node(gate_id) for gate_id in package.required_gate_ids]
        )
    for gate_id, gate in gates.items():
        missing = set(gate.related_work_packages) - packages.keys()
        if missing:
            raise ConfigError(f"{gate_id} references missing related packages: {', '.join(sorted(missing))}")
        dependencies[_gate_node(gate_id)] = tuple(
            _package_node(package_id) for package_id in gate.related_work_packages
        )
    return dependencies


def _combined_topological_order(dependencies: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    successors: dict[str, list[str]] = {node: [] for node in dependencies}
    indegree: dict[str, int] = {}
    for node, predecessors in dependencies.items():
        indegree[node] = len(predecessors)
        for predecessor in predecessors:
            if predecessor not in dependencies:
                raise ConfigError(f"{node} references missing package/gate node {predecessor}")
            successors[predecessor].append(node)
    ready = [node for node, degree in indegree.items() if degree == 0]
    heapq.heapify(ready)
    ordered: list[str] = []
    while ready:
        node = heapq.heappop(ready)
        ordered.append(node)
        for successor in sorted(successors[node]):
            indegree[successor] -= 1
            if indegree[successor] == 0:
                heapq.heappush(ready, successor)
    if len(ordered) != len(dependencies):
        cyclic = sorted(node for node, degree in indegree.items() if degree > 0)
        raise ConfigError(f"package/gate dependency cycle detected involving: {', '.join(cyclic)}")
    return tuple(ordered)


def _time_equal(left: float, right: float) -> bool:
    """Compare CPM times exactly or within one representable float step."""
    if left == right:
        return True
    return abs(left - right) <= max(math.ulp(left), math.ulp(right))


def calculate_schedule(registers: BunkerRegisters) -> dict[str, Any]:
    packages = {package.package_id: package for package in registers.packages}
    gates = {gate.gate_id: gate for gate in registers.gates}
    package_order = _topological_order(packages)
    dependencies = _combined_dependencies(packages, gates)
    combined_order = _combined_topological_order(dependencies)
    durations = {
        node: (packages[node.removeprefix("package:")].duration_hours if node.startswith("package:") else 0.0)
        for node in dependencies
    }
    starts: dict[str, float] = {}
    finishes: dict[str, float] = {}
    for node in combined_order:
        start = max((finishes[dependency] for dependency in dependencies[node]), default=0.0)
        finish = _sum((start, durations[node]), f"{node} earliest finish")
        starts[node], finishes[node] = start, finish

    gate_milestones = [
        {
            "gateId": gate.gate_id,
            "name": gate.name,
            "relatedWorkPackages": list(gate.related_work_packages),
            "hypotheticalEvidenceCompleteHour": finishes[_gate_node(gate.gate_id)],
            "status": "UNRESOLVED",
            "gateAcceptancePerformed": False,
        }
        for gate in sorted(gates.values(), key=lambda item: item.gate_id)
    ]
    rows: list[dict[str, Any]] = []
    for package in package_order:
        node = _package_node(package.package_id)
        rows.append({
            "packageId": package.package_id,
            "name": package.name,
            "dependencies": list(package.dependencies),
            "durationHours": package.duration_hours,
            "autonomyClass": package.autonomy_class,
            "requiredGateIds": list(package.required_gate_ids),
            "requiredGateEvidenceCompleteHours": {
                gate_id: finishes[_gate_node(gate_id)] for gate_id in package.required_gate_ids
            },
            "earliestStartHour": starts[node],
            "earliestFinishHour": finishes[node],
        })
    duration = max(finishes.values(), default=0.0)
    successors: dict[str, list[str]] = {node: [] for node in dependencies}
    for node, predecessors in dependencies.items():
        for predecessor in predecessors:
            successors[predecessor].append(node)
    latest_start: dict[str, float] = {}
    for node in reversed(combined_order):
        latest_finish = min((latest_start[successor] for successor in successors[node]), default=duration)
        latest_start[node] = _finite(latest_finish - durations[node], f"{node} latest start")
    critical_nodes = {
        node for node in dependencies if _time_equal(latest_start[node], starts[node])
    }

    def terminal_package(node: str) -> bool:
        if not node.startswith("package:"):
            return False
        for successor in successors[node]:
            if successor.startswith("package:") or successors[successor]:
                return False
        return True

    terminals = sorted(node for node in critical_nodes if terminal_package(node))
    combined_path: list[str] = []
    if terminals:
        current = terminals[0]
        combined_path.append(current)
        while dependencies[current]:
            candidates = sorted(
                (
                    dependency for dependency in dependencies[current]
                    if dependency in critical_nodes and _time_equal(finishes[dependency], starts[current])
                ),
                key=lambda node: (not node.startswith("package:"), node),
            )
            if not candidates:
                raise ConfigError(f"cannot derive a consistent critical path at {current}")
            current = candidates[0]
            combined_path.append(current)
        combined_path.reverse()
    critical_packages = sorted(
        node.removeprefix("package:") for node in critical_nodes if node.startswith("package:")
    )
    path = [node.removeprefix("package:") for node in combined_path if node.startswith("package:")]
    counts = {name: 0 for name in ALLOWED_AUTONOMY_CLASSES}
    for package in packages.values():
        counts[package.autonomy_class] += 1
    return {
        "topologicalOrder": [package.package_id for package in package_order],
        "packages": rows,
        "gateEvidenceMilestones": gate_milestones,
        "syntheticDurationHours": duration,
        "criticalPathPackageIds": path,
        "allZeroSlackPackageIds": critical_packages,
        "autonomyClassCounts": counts,
        "convention": "Earliest-start CPM with unlimited parallel branches and zero-duration hypothetical gate-evidence nodes. Package starts satisfy ordinary and gate-evidence predecessors. No gate acceptance occurred; actual starts remain blocked. Hours are relative synthetic durations, never dates.",
    }


def calculate_energy(model: BunkerPlanInput, registers: BunkerRegisters) -> dict[str, Any]:
    packages = {package.package_id: package for package in registers.packages}
    fleet = {entry.fleet_id: entry for entry in registers.fleet}
    assumptions: list[dict[str, Any]] = []
    package_totals: dict[str, float] = {}
    fleet_totals: dict[str, float] = {}
    for assumption in model.energy_assumptions:
        if assumption.package_id not in packages:
            raise ConfigError(f"energy assumption references missing package {assumption.package_id}")
        if assumption.fleet_id not in fleet:
            raise ConfigError(f"energy assumption references missing fleet {assumption.fleet_id}")
        if assumption.package_id not in fleet[assumption.fleet_id].intended_work_packages:
            raise ConfigError(f"{assumption.fleet_id} is not registered for intended package {assumption.package_id}")
        package_totals[assumption.package_id] = _sum(
            (package_totals.get(assumption.package_id, 0.0), assumption.electric_energy_kwh),
            f"{assumption.package_id} modeled energy",
        )
        fleet_totals[assumption.fleet_id] = _sum(
            (fleet_totals.get(assumption.fleet_id, 0.0), assumption.electric_energy_kwh),
            f"{assumption.fleet_id} modeled energy",
        )
        assumptions.append({
            "packageId": assumption.package_id,
            "fleetId": assumption.fleet_id,
            "electricEnergy_kWh": assumption.electric_energy_kwh,
            "basis": assumption.basis,
            "provenance": _provenance_json(assumption.provenance),
        })
    modeled_packages = set(package_totals)
    modeled_fleet = set(fleet_totals)
    return {
        "assumptions": assumptions,
        "modeledOnlyElectricEnergy_kWh": _sum(package_totals.values(), "modeled energy total"),
        "byPackage": [
            {"packageId": package_id, "electricEnergy_kWh": package_totals.get(package_id)}
            for package_id in sorted(packages)
        ],
        "byFleet": [
            {"fleetId": fleet_id, "electricEnergy_kWh": fleet_totals[fleet_id]}
            for fleet_id in sorted(fleet_totals)
        ],
        "modeledPackageIds": sorted(modeled_packages),
        "unmodeledPackageIds": sorted(set(packages) - modeled_packages),
        "modeledFleetIds": sorted(modeled_fleet),
        "unmodeledFleetIds": sorted(set(fleet) - modeled_fleet),
        "projectEnergyEstimateAvailable": False,
        "coverageNotice": "Unmodeled packages and fleets have no energy estimate (null), not zero energy. The sum covers listed assumptions only and is not total project energy.",
        "exclusions": [
            "total project energy", "peak power", "charger sizing", "charging schedule", "cost", "tariffs",
            "calendar dates", "percent autonomous readiness", "unmodeled task or fleet energy inference",
        ],
    }


def _evidence_handoff(registers: BunkerRegisters) -> dict[str, Any]:
    """Reference canonical IDs without turning synthetic evidence into acceptance."""
    return {
        "schemaVersion": "1.0.0",
        "exportType": "SYNTHETIC_EVIDENCE_HANDOFF",
        "status": "SYNTHETIC_UNREVIEWED",
        "constructionAuthorized": False,
        "physicalValidationPerformed": False,
        "humanAcceptancePerformed": False,
        "canonicalRegisters": {
            "workBreakdown": "projects/bunker01/construction/work-breakdown.csv",
            "qualityGates": "projects/bunker01/construction/quality-gates.csv",
        },
        "workPackages": [
            {
                "packageId": package.package_id,
                "requiredGateIds": list(package.required_gate_ids),
                "evidenceStatus": package.evidence_status,
            }
            for package in registers.packages
        ],
        "qualityGates": [
            {"gateId": gate.gate_id, "status": gate.status}
            for gate in registers.gates
        ],
        "notice": "Canonical CSV registers remain authoritative. Synthetic evidence references are separate from human acceptance; no evidence completion or gate acceptance is asserted.",
    }


def plan_bunker(model: BunkerPlanInput, registers: BunkerRegisters, site: SiteStatus) -> dict[str, Any]:
    """Return a blocked synthetic plan regardless of any input authorization flag."""
    if site.site_known or site.construction_authorized or site.physical_validation_performed:
        raise ConfigError("BUNKER-01 site status cannot authorize or claim physical validation")
    unresolved = tuple(sorted(gate.gate_id for gate in registers.gates if gate.status == "UNRESOLVED"))
    if len(unresolved) != len(registers.gates) or not unresolved:
        raise ConfigError("every BUNKER-01 human gate must remain unresolved")
    schedule = calculate_schedule(registers)
    energy = calculate_energy(model, registers)
    package_energy = {row["packageId"]: row["electricEnergy_kWh"] for row in energy["byPackage"]}
    for package in schedule["packages"]:
        package["modeledElectricEnergy_kWh"] = package_energy[package["packageId"]]
    return {
        "schemaVersion": "1.0.0",
        "projectId": PROJECT_ID,
        "scope": "CIVILIAN_NON_HABITABLE_UTILITY_ENCLOSURE",
        "siteKnown": False,
        "constructionAuthorized": False,
        "physicalValidationPerformed": False,
        "readinessStatus": READINESS_STATUS_ID,
        "unresolvedGateIds": list(unresolved),
        "syntheticPlanningOnly": True,
        "planningNotice": "Schedule and energy are synthetic planning only. No construction, excavation, entry, occupancy, procurement, physical autonomy, or real-machine control is authorized.",
        "syntheticNotice": model.synthetic_notice,
        "provenance": _provenance_json(model.provenance),
        "evidenceHandoff": _evidence_handoff(registers),
        "quantityConventions": {
            "units": "SI: metres, square metres, cubic metres, hours and kWh",
            "concrete": "Gross geometric volumes only; no entrance, vent or other opening deductions and no reinforcement estimate. Waste-adjusted concrete is theoretical, never an order quantity.",
            "backfill": "Geometric nominal compacted volume = excavation - enclosure displacement - gross drainage; not a compaction specification.",
            "soil": "Loose spoil = excavation * loose bulking. In-situ required = nominal backfill / compacted-to-in-situ ratio. Signed excess = excavation - required; loose excess = max(0, excess) * bulking. Negative excess is a mathematical deficit only; no borrow/haul decision is made.",
            "waterproofing": "Roof footprint + full external vertical sides over total structure height; underside excluded and openings not deducted.",
        },
        "quantities": calculate_quantities(model),
        "schedule": schedule,
        "energy": energy,
        "exclusions": [
            "structural or reinforcement design", "excavation protective-system or work plan", "safe shelter or occupancy approval",
            "procurement or order quantities", "permit package", "real site data or prices", "supplier selection",
            "physical readiness or autonomous construction capability demonstration", "real-machine control",
        ],
    }


def bunker_result_json(result: dict[str, Any]) -> str:
    return json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"


def _svg_number(value: float) -> str:
    if isinstance(value, bool) or not math.isfinite(value):
        raise ConfigError("SVG coordinate must be finite")
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    return text or "0"


def _svg_hour(value: float) -> str:
    if isinstance(value, bool) or not math.isfinite(value):
        raise ConfigError("SVG hour must be finite")
    return format(value, ".12g")


def schedule_svg(result: dict[str, Any]) -> str:
    """Render a deterministic, self-contained relative-hour Gantt/dependency view."""
    schedule = result["schedule"]
    packages = schedule["packages"]
    duration = schedule["syntheticDurationHours"]
    name_wrap = 44
    labels = {
        package["packageId"]: (
            f'{package["packageId"]} | {package["autonomyClass"]} | '
            f'{_svg_hour(package["durationHours"])} h'
        )
        for package in packages
    }
    wrapped_names = {
        package["packageId"]: textwrap.wrap(
            package["name"], width=name_wrap, break_long_words=True, break_on_hyphens=False
        ) or [""]
        for package in packages
    }
    label_column_width = max((len(label) for label in labels.values()), default=40) * 8 + 30
    name_x = 25 + label_column_width
    name_column_width = name_wrap * 7 + 25
    left = name_x + name_column_width + 30
    timeline_width = 1000
    width = max(1600, left + timeline_width + 130)
    top = 190
    row_heights = {
        package["packageId"]: max(36, len(wrapped_names[package["packageId"]]) * 13 + 16)
        for package in packages
    }
    height = top + sum(row_heights.values()) + 70
    scale = timeline_width / duration if duration > 0 else 0.0

    def x(hour: float) -> float:
        return left + hour * scale

    positions: dict[str, tuple[float, WorkPackage | dict[str, Any]]] = {}
    y = float(top)
    for package in packages:
        row_height = row_heights[package["packageId"]]
        positions[package["packageId"]] = (y + row_height / 2, package)
        y += row_height
    gate_milestones = {gate["gateId"]: gate for gate in schedule["gateEvidenceMilestones"]}
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">BUNKER-01 synthetic schedule — construction blocked</title>',
        '<desc id="desc">Relative-hour package and hypothetical gate-evidence dependencies. No gate acceptance occurred. All gates are unresolved and all actual starts remain blocked. No dates, locations, physical readiness, or authorization.</desc>',
        '<style>text{font-family:monospace;fill:#16202a}.title{font-size:25px;font-weight:bold;fill:#9b1c1c}.sub{font-size:15px}.label{font-size:12px}.small{font-size:10px}.bar{stroke:#16202a;stroke-width:1}.dep{stroke:#6b7280;stroke-width:1;fill:none}.gatedep{stroke:#9333ea;stroke-width:1;stroke-dasharray:4 3;fill:none}.grid{stroke:#d1d5db;stroke-width:1}</style>',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        f'<rect data-role="banner" x="15" y="15" width="{width - 30}" height="96" fill="#fee2e2" stroke="#9b1c1c" stroke-width="3"/>',
        '<text class="title" x="35" y="45">SYNTHETIC PLAN — CONSTRUCTION BLOCKED</text>',
        '<text class="sub" x="35" y="70">BUNKER-01 | ALL HUMAN GATES UNRESOLVED | NO PHYSICAL VALIDATION | NO DATES OR LOCATIONS</text>',
        '<text class="sub" x="35" y="94">Gate evidence is hypothetical timing only; acceptance not performed; every actual start remains blocked.</text>',
        '<text class="sub" x="25" y="140">Work package / autonomy class / duration h</text>',
        f'<text class="sub" x="{name_x}" y="140">Wrapped package name</text>',
        f'<text data-role="timeline-heading" class="sub" x="{left}" y="140">Earliest relative hours</text>',
        f'<text class="small" x="{left}" y="157">Unlimited parallel branches; synthetic only</text>',
    ]
    tick_count = 5
    for index in range(tick_count + 1):
        hour = duration * (index / tick_count)
        xpos = x(hour)
        lines.append(f'<line data-role="timeline-grid" class="grid" x1="{_svg_number(xpos)}" y1="174" x2="{_svg_number(xpos)}" y2="{height - 45}"/>')
        lines.append(f'<text class="small" x="{_svg_number(xpos)}" y="168" text-anchor="middle">{html.escape(_svg_hour(hour))}</text>')
    for package in packages:
        center, _ = positions[package["packageId"]]
        for dependency in package["dependencies"]:
            if dependency not in positions:
                continue
            dependency_y, predecessor = positions[dependency]
            start_x = x(package["earliestStartHour"])
            end_x = x(predecessor["earliestFinishHour"])
            lines.append(
                f'<path class="dep" d="M {_svg_number(end_x)} {_svg_number(dependency_y)} L {_svg_number(start_x)} {_svg_number(dependency_y)} L {_svg_number(start_x)} {_svg_number(center)}"/>'
            )
        for gate_id in package["requiredGateIds"]:
            gate = gate_milestones[gate_id]
            producer_id = gate["relatedWorkPackages"][-1]
            producer_y = positions[producer_id][0]
            gate_x = x(gate["hypotheticalEvidenceCompleteHour"])
            start_x = x(package["earliestStartHour"])
            lines.append(
                f'<path class="gatedep" d="M {_svg_number(gate_x)} {_svg_number(producer_y)} L {_svg_number(start_x)} {_svg_number(producer_y)} L {_svg_number(start_x)} {_svg_number(center)}"/>'
            )
    colors = {
        "human_gate": "#dc2626",
        "specialist": "#60a5fa",
        "future_supervised_autonomy": "#f59e0b",
        "simulation_candidate": "#34d399",
    }
    for package in packages:
        package_id = package["packageId"]
        center, _ = positions[package_id]
        start = x(package["earliestStartHour"])
        finish = x(package["earliestFinishHour"])
        escaped_id = html.escape(package_id, quote=True)
        color = colors[package["autonomyClass"]]
        lines.append(
            f'<text data-role="package-label" data-package-id="{escaped_id}" class="label" x="25" '
            f'y="{_svg_number(center + 4)}">{html.escape(labels[package_id], quote=True)}</text>'
        )
        name_lines = wrapped_names[package_id]
        first_baseline = center - (len(name_lines) - 1) * 6 + 4
        spans = "".join(
            f'<tspan x="{name_x}" y="{_svg_number(first_baseline + index * 13)}">{html.escape(name_line, quote=True)}</tspan>'
            for index, name_line in enumerate(name_lines)
        )
        lines.append(f'<text data-role="package-name" data-package-id="{escaped_id}" class="small">{spans}</text>')
        if package["durationHours"] == 0:
            points = f"{_svg_number(start)},{_svg_number(center - 8)} {_svg_number(start + 8)},{_svg_number(center)} {_svg_number(start)},{_svg_number(center + 8)} {_svg_number(start - 8)},{_svg_number(center)}"
            lines.append(f'<polygon points="{points}" fill="{color}" stroke="#16202a"/>')
        else:
            lines.append(f'<rect class="bar" x="{_svg_number(start)}" y="{_svg_number(center - 9)}" width="{_svg_number(max(1.0, finish - start))}" height="18" fill="{color}"/>')
        lines.append(f'<text class="small" x="{_svg_number(finish + 10)}" y="{_svg_number(center + 4)}">{_svg_hour(package["earliestStartHour"])}–{_svg_hour(package["earliestFinishHour"])}</text>')
    critical_count = len(schedule["criticalPathPackageIds"])
    lines.append(f'<text class="sub" x="25" y="{height - 20}">Synthetic duration: {html.escape(_svg_hour(duration))} h | Critical path: {critical_count} packages (see result.json) | NOT AN EXECUTABLE CONSTRUCTION SCHEDULE</text>')
    lines.append('</svg>')
    return "\n".join(lines) + "\n"


def write_bunker_outputs(result: dict[str, Any], output_dir: str | Path) -> tuple[Path, Path]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    result_path = destination / "result.json"
    svg_path = destination / "schedule.svg"
    result_text = bunker_result_json(result)
    svg_text = schedule_svg(result)
    result_path.write_text(result_text, encoding="utf-8", newline="\n")
    svg_path.write_text(svg_text, encoding="utf-8", newline="\n")
    return result_path, svg_path
