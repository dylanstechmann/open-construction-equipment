# SPDX-License-Identifier: Apache-2.0
"""Deterministic, unreviewed static longitudinal load-moment arithmetic.

This module contains no stability rating, capacity calculation, operational
acceptance decision, or fabrication release. Runtime validation is deliberately
standard-library only; the JSON Schema is an optional interchange artifact.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from .config import ConfigError, _keys, _mapping, _number, _string, load_json

ANALYSIS_ID = "AN-LC-001A"
ANALYSIS_TYPE_ID = "STATIC_LONGITUDINAL_LOAD_MOMENT"
ANALYSIS_STATUS_ID = "AGENT_AUTHORED_UNREVIEWED"
STANDARD_GRAVITY_MPS2 = 9.80665
EXPECTED_TRACE_IDS = (
    "LC-001",
    "DI-MASS-001",
    "DI-ROC-001",
    "SR-006",
    "HZ-005",
    "IF-MEC-001",
    "IF-MEC-002",
    "IF-MEC-003",
    "IF-MEC-004",
)

EXCLUSIONS = (
    "slope and cross-slope",
    "braking acceleration and turning",
    "terrain compliance track slip and support-contact variability",
    "dynamic impact and transient load effects",
    "structural strength deflection buckling and fatigue",
    "hydraulic capacity pressure and load-holding behavior",
    "attachment retention and interface strength",
    "standards tipping definitions and rated operating capacity determination",
    "safety factors and protective-structure performance",
    "physical validation and operational release",
)

LIMITATIONS = (
    "Two-dimensional vertical-gravity point-mass equilibrium on a level rigid support line only.",
    "Support reactions are algebraic static resultants; negative reactions indicate loss of contact in the simplified model, not an operational outcome.",
    "The zero-margin payload boundary is a mathematical condition for the fixed supplied geometry, not a capacity, operating limit, or recommendation.",
    "Inputs are synthetic and unreviewed; results have no physical-evidence status.",
)


@dataclass(frozen=True)
class ValueProvenance:
    """Synthetic origin and source-register trace for one numeric input."""

    source_type: str
    statement: str
    cad_derived: bool
    owner_supplied: bool
    trace_ids: tuple[str, ...]


@dataclass(frozen=True)
class EngineeringValue:
    """One scalar with an explicit SI unit and mandatory provenance."""

    value: float
    unit: str
    provenance: ValueProvenance


@dataclass(frozen=True)
class PointMass:
    """A point mass and its longitudinal center of gravity."""

    mass: EngineeringValue
    cg_x: EngineeringValue


@dataclass(frozen=True)
class LongitudinalAnalysisInput:
    """Immutable, fully normalized input for AN-LC-001A."""

    analysis_id: str
    trace_ids: tuple[str, ...]
    synthetic_notice: str
    machine: PointMass
    attachment: PointMass
    payload: PointMass
    rear_support_x: EngineeringValue
    front_support_x: EngineeringValue


def _provenance(value: Any, name: str) -> ValueProvenance:
    data = _mapping(value, f"{name}.provenance")
    required = {"sourceType", "statement", "cadDerived", "ownerSupplied", "traceIds"}
    _keys(data, required, set(), f"{name}.provenance")
    if data["sourceType"] != "SYNTHETIC_AGENT_AUTHORED":
        raise ConfigError(f"{name}.provenance.sourceType must be SYNTHETIC_AGENT_AUTHORED")
    if data["cadDerived"] is not False or data["ownerSupplied"] is not False:
        raise ConfigError(f"{name}.provenance must explicitly deny CAD derivation and owner supply")
    raw_ids = data["traceIds"]
    if not isinstance(raw_ids, list) or not raw_ids:
        raise ConfigError(f"{name}.provenance.traceIds must be a non-empty array")
    trace_ids: list[str] = []
    for index, trace_id in enumerate(raw_ids):
        if not isinstance(trace_id, str) or trace_id not in EXPECTED_TRACE_IDS:
            raise ConfigError(f"{name}.provenance.traceIds[{index}] is not a recognized analysis trace ID")
        if trace_id in trace_ids:
            raise ConfigError(f"{name}.provenance.traceIds contains duplicate {trace_id}")
        trace_ids.append(trace_id)
    return ValueProvenance(
        "SYNTHETIC_AGENT_AUTHORED",
        _string(data, "statement", f"{name}.provenance"),
        False,
        False,
        tuple(trace_ids),
    )


def _quantity(value: Any, name: str, unit: str, *, positive: bool = False) -> EngineeringValue:
    data = _mapping(value, name)
    _keys(data, {"value", "unit", "provenance"}, set(), name)
    minimum = 0 if unit == "kg" else None
    number = _number(data, "value", name, minimum, strict_low=positive)
    if data["unit"] != unit:
        raise ConfigError(f"{name}.unit must be {unit}; no units conversion is performed")
    return EngineeringValue(number, unit, _provenance(data["provenance"], name))


def _point_mass(value: Any, name: str, *, mass_positive: bool = False) -> PointMass:
    data = _mapping(value, name)
    _keys(data, {"mass_kg", "cgX_m"}, set(), name)
    return PointMass(
        _quantity(data["mass_kg"], f"{name}.mass_kg", "kg", positive=mass_positive),
        _quantity(data["cgX_m"], f"{name}.cgX_m", "m"),
    )


def parse_analysis_input(data: dict[str, Any]) -> LongitudinalAnalysisInput:
    """Strictly validate one AN-LC-001A JSON object without unit conversion."""

    required = {
        "spdxLicenseIdentifier", "schemaVersion", "platform", "analysisId", "analysisType",
        "analysisStatus", "acceptanceStatus", "reviewStatus", "physicalValidationPerformed",
        "syntheticNotice", "unitSystem", "coordinateConvention", "traceIds", "inputs",
    }
    _keys(data, required, set(), "engineering analysis")
    constants = {
        "spdxLicenseIdentifier": "CERN-OHL-S-2.0",
        "schemaVersion": "1.0.0",
        "platform": "OCE-CTL-01",
        "analysisId": ANALYSIS_ID,
        "analysisType": ANALYSIS_TYPE_ID,
        "analysisStatus": ANALYSIS_STATUS_ID,
        "acceptanceStatus": "NOT_ASSESSED",
        "reviewStatus": "UNREVIEWED",
        "unitSystem": "SI",
        "coordinateConvention": "x_forward_m_front_x_greater_than_rear_x",
    }
    for key, expected in constants.items():
        if data[key] != expected:
            raise ConfigError(f"engineering analysis.{key} must be {expected}")
    if data["physicalValidationPerformed"] is not False:
        raise ConfigError("engineering analysis.physicalValidationPerformed must be false")
    trace_ids = data["traceIds"]
    if not isinstance(trace_ids, list) or any(not isinstance(item, str) for item in trace_ids):
        raise ConfigError("engineering analysis.traceIds must be an array of strings")
    if tuple(trace_ids) != EXPECTED_TRACE_IDS:
        raise ConfigError(
            "engineering analysis.traceIds must exactly contain the stable AN-LC-001A IDs in canonical order"
        )
    synthetic_notice = _string(data, "syntheticNotice", "engineering analysis")
    inputs = _mapping(data["inputs"], "inputs")
    _keys(inputs, {"machine", "attachment", "payload", "supports"}, set(), "inputs")
    supports = _mapping(inputs["supports"], "inputs.supports")
    _keys(supports, {"rearX_m", "frontX_m"}, set(), "inputs.supports")
    model = LongitudinalAnalysisInput(
        ANALYSIS_ID,
        EXPECTED_TRACE_IDS,
        synthetic_notice,
        _point_mass(inputs["machine"], "inputs.machine", mass_positive=True),
        _point_mass(inputs["attachment"], "inputs.attachment"),
        _point_mass(inputs["payload"], "inputs.payload"),
        _quantity(supports["rearX_m"], "inputs.supports.rearX_m", "m"),
        _quantity(supports["frontX_m"], "inputs.supports.frontX_m", "m"),
    )
    if model.front_support_x.value <= model.rear_support_x.value:
        raise ConfigError("inputs.supports.frontX_m.value must be greater than rearX_m.value")
    for point_name, point in (("machine", model.machine), ("attachment", model.attachment), ("payload", model.payload)):
        for quantity in (point.mass, point.cg_x):
            if not set(quantity.provenance.trace_ids).issubset(model.trace_ids):
                raise ConfigError(f"inputs.{point_name} provenance contains an untraced ID")
    return model


def load_analysis_input(path: str | Path) -> LongitudinalAnalysisInput:
    """Load strict JSON, including duplicate-key and non-finite-number rejection."""

    return parse_analysis_input(load_json(path))


def _normalized_provenance(provenance: ValueProvenance) -> dict[str, Any]:
    return {
        "sourceType": provenance.source_type,
        "statement": provenance.statement,
        "cadDerived": provenance.cad_derived,
        "ownerSupplied": provenance.owner_supplied,
        "traceIds": list(provenance.trace_ids),
    }


def _normalized_quantity(quantity: EngineeringValue) -> dict[str, Any]:
    return {
        "value": quantity.value,
        "unit": quantity.unit,
        "provenance": _normalized_provenance(quantity.provenance),
    }


def _normalized_point_mass(point: PointMass) -> dict[str, Any]:
    return {"mass_kg": _normalized_quantity(point.mass), "cgX_m": _normalized_quantity(point.cg_x)}


def normalized_analysis_input(model: LongitudinalAnalysisInput) -> dict[str, Any]:
    """Return the complete canonical input representation used for hashing."""

    return {
        "spdxLicenseIdentifier": "CERN-OHL-S-2.0",
        "schemaVersion": "1.0.0",
        "platform": "OCE-CTL-01",
        "analysisId": model.analysis_id,
        "analysisType": ANALYSIS_TYPE_ID,
        "analysisStatus": ANALYSIS_STATUS_ID,
        "acceptanceStatus": "NOT_ASSESSED",
        "reviewStatus": "UNREVIEWED",
        "physicalValidationPerformed": False,
        "syntheticNotice": model.synthetic_notice,
        "unitSystem": "SI",
        "coordinateConvention": "x_forward_m_front_x_greater_than_rear_x",
        "traceIds": list(model.trace_ids),
        "inputs": {
            "machine": _normalized_point_mass(model.machine),
            "attachment": _normalized_point_mass(model.attachment),
            "payload": _normalized_point_mass(model.payload),
            "supports": {
                "rearX_m": _normalized_quantity(model.rear_support_x),
                "frontX_m": _normalized_quantity(model.front_support_x),
            },
        },
    }


def _finite(value: float, name: str) -> float:
    if not math.isfinite(value):
        raise ConfigError(f"calculation produced a non-finite {name}")
    return 0.0 if value == 0 else value


def _sum(values: tuple[float, ...], name: str) -> float:
    try:
        return _finite(math.fsum(values), name)
    except OverflowError as exc:
        raise ConfigError(f"calculation produced a non-finite {name}") from exc


def _product(left: float, right: float, name: str) -> float:
    return _finite(left * right, name)


def calculate_static_longitudinal(model: LongitudinalAnalysisInput) -> dict[str, Any]:
    """Calculate signed static quantities; deliberately emit no operational verdict."""

    points = (model.machine, model.attachment, model.payload)
    masses = tuple(point.mass.value for point in points)
    coordinates = tuple(point.cg_x.value for point in points)
    total_mass = _sum(masses, "total mass")
    if total_mass <= 0:
        raise ConfigError("total mass must be positive")
    mass_moment = _sum(tuple(_product(mass, x, "mass moment") for mass, x in zip(masses, coordinates)), "mass moment")
    combined_cg = _finite(mass_moment / total_mass, "combined CG")
    rear_x, front_x = model.rear_support_x.value, model.front_support_x.value
    support_span = _finite(front_x - rear_x, "support span")
    gravity = STANDARD_GRAVITY_MPS2

    # Positive signed support moment acts from the support toward +x (forward).
    front_mass_moment = _sum(
        tuple(_product(mass, x - front_x, "front mass moment") for mass, x in zip(masses, coordinates)),
        "front mass moment",
    )
    rear_mass_moment = _sum(
        tuple(_product(mass, x - rear_x, "rear mass moment") for mass, x in zip(masses, coordinates)),
        "rear mass moment",
    )
    front_margin = _product(-front_mass_moment, gravity, "front static moment margin")
    rear_margin = _product(rear_mass_moment, gravity, "rear static moment margin")
    front_reaction = _finite(rear_margin / support_span, "front support reaction")
    rear_reaction = _finite(front_margin / support_span, "rear support reaction")

    # Holding the payload load center fixed, solve front static margin = 0.
    # baseline signed moment + payload_mass * (payload_x - front_x) = 0 in kg*m units.
    base_front_mass_moment = _sum(
        tuple(
            _product(point.mass.value, point.cg_x.value - front_x, "baseline front mass moment")
            for point in (model.machine, model.attachment)
        ),
        "baseline front mass moment",
    )
    payload_arm = model.payload.cg_x.value - front_x
    boundary_mass: float | None = None
    boundary_reason: str | None
    if payload_arm <= 0:
        boundary_reason = "Payload load center is not forward of the front support; no forward boundary is defined."
    elif base_front_mass_moment >= 0:
        boundary_reason = (
            "Machine-plus-attachment front static margin is zero or negative; no finite positive forward boundary "
            "exists from the modeled baseline."
        )
    else:
        candidate = -base_front_mass_moment / payload_arm
        if math.isfinite(candidate) and candidate > 0:
            boundary_mass = candidate
            boundary_reason = None
        else:
            boundary_reason = "Boundary arithmetic did not produce a finite positive payload mass."

    normalized = normalized_analysis_input(model)
    canonical_input = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return {
        "analysisId": model.analysis_id,
        "analysisType": ANALYSIS_TYPE_ID,
        "analysisStatus": ANALYSIS_STATUS_ID,
        "acceptanceStatus": "NOT_ASSESSED",
        "reviewStatus": "UNREVIEWED",
        "physicalValidationPerformed": False,
        "traceIds": list(model.trace_ids),
        "inputSha256": hashlib.sha256(canonical_input.encode("utf-8")).hexdigest(),
        "normalizedInput": normalized,
        "model": {
            "gravity_mps2": gravity,
            "coordinateConvention": "x_forward_m_front_x_greater_than_rear_x",
            "supportMomentSignConvention": "positive_from_support_toward_forward_x",
            "resultantWithinSupportIntervalDefinition": "rearX_m <= resultantX_m <= frontX_m; boundaries included",
        },
        "results": {
            "totalMass_kg": total_mass,
            "combinedCgX_m": combined_cg,
            "resultantX_m": combined_cg,
            "supportSpan_m": support_span,
            "supportReactions_N": {"front": front_reaction, "rear": rear_reaction},
            "signedLoadMoments_Nm": {
                "aboutFrontSupport": _product(front_mass_moment, gravity, "front load moment"),
                "aboutRearSupport": _product(rear_mass_moment, gravity, "rear load moment"),
            },
            "staticMomentMargins_Nm": {
                "front": front_margin,
                "rear": rear_margin,
                "minimum": min(front_margin, rear_margin),
            },
            "resultantWithinSupportInterval": rear_x <= combined_cg <= front_x,
            "forwardZeroStaticMarginPayloadBoundary": {
                "condition": "FRONT_SUPPORT_STATIC_MOMENT_MARGIN_EQUALS_ZERO",
                "fixedPayloadLoadCenterX_m": model.payload.cg_x.value,
                "payloadMass_kg": boundary_mass,
                "reason": boundary_reason,
            },
        },
        "exclusions": list(EXCLUSIONS),
        "limitations": list(LIMITATIONS),
    }


def analysis_result_json(result: dict[str, Any]) -> str:
    """Serialize a result deterministically, rejecting nonstandard JSON numbers."""

    return json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"


def write_analysis_result(result: dict[str, Any], output_dir: str | Path) -> Path:
    """Write only the deterministic result artifact under the selected directory."""

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / "result.json"
    path.write_text(analysis_result_json(result), encoding="utf-8", newline="\n")
    return path
