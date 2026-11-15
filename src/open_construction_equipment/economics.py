# SPDX-License-Identifier: Apache-2.0
"""Synthetic fabrication, maintenance, startup, and pathway economics.

Every amount is an explicit, unquoted assumption. Linear lifecycle proration is
an arithmetic trade-study device, not a rental invoice, procurement recommendation,
physical validation, or authorization to fabricate, construct, or operate.
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
from .geohazard_rural import CostScheduleDelta
from .physics import (
    PLATFORM_ID,
    SCOPE_ID,
    UNIT_SYSTEM_ID,
    EvidenceStatus,
    SyntheticProvenance,
    _at_least,
    _finite,
    _parse_provenance,
    _product,
    _sum,
    _validate_provenance,
    checked_divide,
)

SCHEMA_VERSION = "1.0.0"


class AcquisitionPathway(StrEnum):
    DIY = "diy"
    RENTAL = "rental"
    HYBRID = "hybrid"


class CostCategory(StrEnum):
    TOOLING = "TOOLING"
    FABRICATION_MATERIAL = "FABRICATION_MATERIAL"
    FABRICATION_COMPONENT = "FABRICATION_COMPONENT"
    LABOR = "LABOR"
    RENTAL = "RENTAL"
    MOBILIZATION = "MOBILIZATION"
    WEAR_MAINTENANCE = "WEAR_MAINTENANCE"
    ENERGY = "ENERGY"
    SITE_ADAPTATION = "SITE_ADAPTATION"


class RentalBillingUnit(StrEnum):
    HOUR = "HOUR"
    DAY_8H = "DAY_8H"
    WEEK_40H = "WEEK_40H"


@dataclass(frozen=True)
class ToolingItem:
    item_id: str
    startup_capex: float
    service_life_h: float
    maintenance_per_h: float
    applies_to: tuple[AcquisitionPathway, ...]


@dataclass(frozen=True)
class FabricationItem:
    item_id: str
    quantity: float
    unit_material_cost: float
    unit_component_cost: float
    labor_hours_per_unit: float
    hourly_wear_reserve: float
    applies_to: tuple[AcquisitionPathway, ...]


@dataclass(frozen=True)
class LaborRate:
    role: str
    rate_per_h: float
    available_hours: float


@dataclass(frozen=True)
class RentalItem:
    item_id: str
    billing_unit: RentalBillingUnit
    rate_per_billing_unit: float
    delivery_per_mobilization: float
    mobilizations_per_project: int
    fuel_or_energy_per_h: float
    hourly_wear_reserve: float
    hourly_wear_reserve_included: bool
    applies_to: tuple[AcquisitionPathway, ...]


@dataclass(frozen=True)
class PathwayPolicy:
    pathway: AcquisitionPathway
    owned_item_ids: tuple[str, ...]
    rental_item_ids: tuple[str, ...]
    site_adaptation_ids: tuple[str, ...]


@dataclass(frozen=True)
class EconomicsInput:
    analysis_id: str
    currency: str
    provenance: SyntheticProvenance
    tooling: tuple[ToolingItem, ...]
    fabrication: tuple[FabricationItem, ...]
    labor_rates: tuple[LaborRate, ...]
    rentals: tuple[RentalItem, ...]
    fabrication_labor_role: str
    evaluation_hours: tuple[float, ...]
    annual_fixed_ownership_cost: float
    ownership_hours_per_year: float
    owned_microgrid_energy_cost_per_h: float
    site_adaptations: tuple[CostScheduleDelta, ...]
    policies: tuple[PathwayPolicy, ...]


@dataclass(frozen=True)
class CostLine:
    category: CostCategory
    fixed_cost: float
    variable_cost_per_h: float
    basis: str


@dataclass(frozen=True)
class PathwayCost:
    pathway: AcquisitionPathway
    operating_hours: float
    currency: str
    lines: tuple[CostLine, ...]
    shop_startup_tooling_capex: float
    fabrication_cost: float
    labor_hours: float
    labor_cost: float
    rental_cost: float
    wear_maintenance_cost: float
    energy_cost: float
    site_adaptation_cost: float
    total_cost: float


@dataclass(frozen=True)
class BreakEvenResult:
    left_path: AcquisitionPathway
    right_path: AcquisitionPathway
    lower_cost_path_below: AcquisitionPathway | None
    lower_cost_path_above: AcquisitionPathway | None
    operating_hours: float | None
    is_exact_tie_everywhere: bool
    reason: str


@dataclass(frozen=True)
class EconomicsResult:
    analysis_id: str
    status: EvidenceStatus
    pathway_costs: tuple[PathwayCost, ...]
    break_even: tuple[BreakEvenResult, ...]
    currency: str
    quotes_obtained: bool = False
    procurement_authorized: bool = False
    physical_validation_performed: bool = False


_BILLING_HOURS = {
    RentalBillingUnit.HOUR: 1.0,
    RentalBillingUnit.DAY_8H: 8.0,
    RentalBillingUnit.WEEK_40H: 40.0,
}
_OWNED_PATHWAYS = frozenset({AcquisitionPathway.DIY, AcquisitionPathway.HYBRID})
_RENTAL_PATHWAYS = frozenset({AcquisitionPathway.RENTAL, AcquisitionPathway.HYBRID})
_PATHWAY_ORDER = (
    AcquisitionPathway.DIY,
    AcquisitionPathway.RENTAL,
    AcquisitionPathway.HYBRID,
)
_BREAK_EVEN_PAIRS = (
    (AcquisitionPathway.DIY, AcquisitionPathway.RENTAL),
    (AcquisitionPathway.DIY, AcquisitionPathway.HYBRID),
    (AcquisitionPathway.RENTAL, AcquisitionPathway.HYBRID),
)


def _boolean(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigError(f"{name} must be a boolean")
    return value


def _enum_member(enum_type: type[StrEnum], value: Any, name: str) -> Any:
    if not isinstance(value, str):
        raise ConfigError(f"{name} must be a string")
    try:
        return enum_type(value)
    except ValueError as exc:
        raise ConfigError(f"{name} has unsupported value {value!r}") from exc


def _nonempty_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{name} must be a non-empty string")
    return value


def _pathways(value: Any, allowed: frozenset[AcquisitionPathway], name: str) -> tuple[AcquisitionPathway, ...]:
    if not isinstance(value, list) or not value:
        raise ConfigError(f"{name} must be a non-empty array")
    pathways = tuple(
        _enum_member(AcquisitionPathway, item, f"{name}[{index}]")
        for index, item in enumerate(value)
    )
    if len(set(pathways)) != len(pathways):
        raise ConfigError(f"{name} must contain unique pathways")
    if any(pathway not in allowed for pathway in pathways):
        raise ConfigError(f"{name} contains a pathway not allowed for this item")
    return pathways


def _validate_tooling(item: ToolingItem, name: str = "tooling") -> None:
    if not isinstance(item, ToolingItem):
        raise ConfigError(f"{name} must be ToolingItem")
    _nonempty_text(item.item_id, f"{name}.item_id")
    _at_least(item.startup_capex, 0, f"{name}.startup_capex")
    _at_least(item.service_life_h, 0, f"{name}.service_life_h", strict=True)
    _at_least(item.maintenance_per_h, 0, f"{name}.maintenance_per_h")
    _validate_applies_to(item.applies_to, _OWNED_PATHWAYS, f"{name}.applies_to")


def _validate_fabrication(item: FabricationItem, name: str = "fabrication") -> None:
    if not isinstance(item, FabricationItem):
        raise ConfigError(f"{name} must be FabricationItem")
    _nonempty_text(item.item_id, f"{name}.item_id")
    _at_least(item.quantity, 0, f"{name}.quantity", strict=True)
    _at_least(item.unit_material_cost, 0, f"{name}.unit_material_cost")
    _at_least(item.unit_component_cost, 0, f"{name}.unit_component_cost")
    _at_least(item.labor_hours_per_unit, 0, f"{name}.labor_hours_per_unit")
    _at_least(item.hourly_wear_reserve, 0, f"{name}.hourly_wear_reserve")
    _validate_applies_to(item.applies_to, _OWNED_PATHWAYS, f"{name}.applies_to")


def _validate_labor_rate(item: LaborRate, name: str = "labor_rate") -> None:
    if not isinstance(item, LaborRate):
        raise ConfigError(f"{name} must be LaborRate")
    _nonempty_text(item.role, f"{name}.role")
    _at_least(item.rate_per_h, 0, f"{name}.rate_per_h")
    _at_least(item.available_hours, 0, f"{name}.available_hours", strict=True)


def _validate_rental(item: RentalItem, name: str = "rental") -> None:
    if not isinstance(item, RentalItem):
        raise ConfigError(f"{name} must be RentalItem")
    _nonempty_text(item.item_id, f"{name}.item_id")
    if not isinstance(item.billing_unit, RentalBillingUnit):
        raise ConfigError(f"{name}.billing_unit must be RentalBillingUnit")
    _at_least(item.rate_per_billing_unit, 0, f"{name}.rate_per_billing_unit")
    _at_least(item.delivery_per_mobilization, 0, f"{name}.delivery_per_mobilization")
    if isinstance(item.mobilizations_per_project, bool) or not isinstance(item.mobilizations_per_project, int):
        raise ConfigError(f"{name}.mobilizations_per_project must be an integer")
    _at_least(item.mobilizations_per_project, 0, f"{name}.mobilizations_per_project")
    _at_least(item.fuel_or_energy_per_h, 0, f"{name}.fuel_or_energy_per_h")
    _at_least(item.hourly_wear_reserve, 0, f"{name}.hourly_wear_reserve")
    if not isinstance(item.hourly_wear_reserve_included, bool):
        raise ConfigError(f"{name}.hourly_wear_reserve_included must be a boolean")
    if item.hourly_wear_reserve_included and item.hourly_wear_reserve != 0:
        raise ConfigError(f"{name} included wear requires a zero separate hourly reserve")
    _validate_applies_to(item.applies_to, _RENTAL_PATHWAYS, f"{name}.applies_to")


def _validate_applies_to(
    value: Any,
    allowed: frozenset[AcquisitionPathway],
    name: str,
) -> None:
    if not isinstance(value, tuple) or not value:
        raise ConfigError(f"{name} must be a non-empty tuple")
    if any(not isinstance(item, AcquisitionPathway) for item in value):
        raise ConfigError(f"{name} must contain AcquisitionPathway values")
    if len(set(value)) != len(value) or any(item not in allowed for item in value):
        raise ConfigError(f"{name} contains duplicate or unauthorized pathways")


def _tooling(value: Any, name: str) -> ToolingItem:
    data = _mapping(value, name)
    _keys(data, {"itemId", "startupCapex", "serviceLife_h", "maintenancePer_h", "appliesTo"}, set(), name)
    item = ToolingItem(
        item_id=_string(data, "itemId", name),
        startup_capex=_number(data, "startupCapex", name, 0),
        service_life_h=_number(data, "serviceLife_h", name, 0, strict_low=True),
        maintenance_per_h=_number(data, "maintenancePer_h", name, 0),
        applies_to=_pathways(data["appliesTo"], _OWNED_PATHWAYS, f"{name}.appliesTo"),
    )
    _validate_tooling(item, name)
    return item


def _fabrication(value: Any, name: str) -> FabricationItem:
    data = _mapping(value, name)
    required = {
        "itemId", "quantity", "unitMaterialCost", "unitComponentCost", "laborHoursPerUnit",
        "hourlyWearReserve", "appliesTo",
    }
    _keys(data, required, set(), name)
    item = FabricationItem(
        item_id=_string(data, "itemId", name),
        quantity=_number(data, "quantity", name, 0, strict_low=True),
        unit_material_cost=_number(data, "unitMaterialCost", name, 0),
        unit_component_cost=_number(data, "unitComponentCost", name, 0),
        labor_hours_per_unit=_number(data, "laborHoursPerUnit", name, 0),
        hourly_wear_reserve=_number(data, "hourlyWearReserve", name, 0),
        applies_to=_pathways(data["appliesTo"], _OWNED_PATHWAYS, f"{name}.appliesTo"),
    )
    _validate_fabrication(item, name)
    return item


def _labor_rate(value: Any, name: str) -> LaborRate:
    data = _mapping(value, name)
    _keys(data, {"role", "ratePer_h", "availableHours_h"}, set(), name)
    item = LaborRate(
        role=_string(data, "role", name),
        rate_per_h=_number(data, "ratePer_h", name, 0),
        available_hours=_number(data, "availableHours_h", name, 0, strict_low=True),
    )
    _validate_labor_rate(item, name)
    return item


def _rental(value: Any, name: str) -> RentalItem:
    data = _mapping(value, name)
    required = {
        "itemId", "billingUnit", "ratePerBillingUnit", "deliveryPerMobilization",
        "mobilizationsPerProject", "fuelOrEnergyPer_h", "hourlyWearReserve",
        "hourlyWearReserveIncluded", "appliesTo",
    }
    _keys(data, required, set(), name)
    mobilizations = data["mobilizationsPerProject"]
    if isinstance(mobilizations, bool) or not isinstance(mobilizations, int):
        raise ConfigError(f"{name}.mobilizationsPerProject must be an integer")
    item = RentalItem(
        item_id=_string(data, "itemId", name),
        billing_unit=_enum_member(RentalBillingUnit, data["billingUnit"], f"{name}.billingUnit"),
        rate_per_billing_unit=_number(data, "ratePerBillingUnit", name, 0),
        delivery_per_mobilization=_number(data, "deliveryPerMobilization", name, 0),
        mobilizations_per_project=mobilizations,
        fuel_or_energy_per_h=_number(data, "fuelOrEnergyPer_h", name, 0),
        hourly_wear_reserve=_number(data, "hourlyWearReserve", name, 0),
        hourly_wear_reserve_included=_boolean(
            data["hourlyWearReserveIncluded"], f"{name}.hourlyWearReserveIncluded",
        ),
        applies_to=_pathways(data["appliesTo"], _RENTAL_PATHWAYS, f"{name}.appliesTo"),
    )
    _validate_rental(item, name)
    return item


def _invalid_string(name: str) -> str:
    raise ConfigError(f"{name} must be a non-empty string")


def _string_tuple(value: Any, name: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ConfigError(f"{name} must be an array")
    result = tuple(
        item if isinstance(item, str) and item.strip() else _invalid_string(f"{name}[{index}]")
        for index, item in enumerate(value)
    )
    if len(set(result)) != len(result):
        raise ConfigError(f"{name} must contain unique IDs")
    return result


def _policy(value: Any, name: str) -> PathwayPolicy:
    data = _mapping(value, name)
    _keys(data, {"pathway", "ownedItemIds", "rentalItemIds", "siteAdaptationIds"}, set(), name)
    return PathwayPolicy(
        pathway=_enum_member(AcquisitionPathway, data["pathway"], f"{name}.pathway"),
        owned_item_ids=_string_tuple(data["ownedItemIds"], f"{name}.ownedItemIds"),
        rental_item_ids=_string_tuple(data["rentalItemIds"], f"{name}.rentalItemIds"),
        site_adaptation_ids=_string_tuple(data["siteAdaptationIds"], f"{name}.siteAdaptationIds"),
    )


def _adaptation(value: Any, name: str) -> CostScheduleDelta:
    data = _mapping(value, name)
    required = {"adaptationId", "costDelta", "scheduleDelta_h", "laborDelta_h", "currency", "basis"}
    _keys(data, required, set(), name)
    return CostScheduleDelta(
        adaptation_id=_string(data, "adaptationId", name),
        cost_delta=_number(data, "costDelta", name),
        schedule_delta_h=_number(data, "scheduleDelta_h", name),
        labor_delta_h=_number(data, "laborDelta_h", name),
        currency=_string(data, "currency", name),
        basis=_string(data, "basis", name),
    )


def _array(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ConfigError(f"{name} must be an array")
    return value


def parse_economics_input(data: dict[str, Any]) -> EconomicsInput:
    """Parse the exact synthetic economics envelope and all cross-references."""

    envelope = _mapping(data, "economics")
    required = {
        "spdxLicenseIdentifier", "schemaVersion", "platform", "scope", "unitSystem", "analysisId",
        "currency", "provenance", "tooling", "fabrication", "laborRates", "rentals",
        "fabricationLaborRole", "evaluationHours_h", "annualFixedOwnershipCost",
        "ownershipHoursPerYear", "ownedMicrogridEnergyCostPer_h", "siteAdaptations", "policies",
    }
    _keys(envelope, required, set(), "economics")
    constants = {
        "spdxLicenseIdentifier": "CC-BY-SA-4.0",
        "schemaVersion": SCHEMA_VERSION,
        "platform": PLATFORM_ID,
        "scope": SCOPE_ID,
        "unitSystem": UNIT_SYSTEM_ID,
    }
    for key, expected in constants.items():
        if envelope[key] != expected:
            raise ConfigError(f"economics.{key} must be {expected}")
    raw_hours = _array(envelope["evaluationHours_h"], "economics.evaluationHours_h")
    if not raw_hours:
        raise ConfigError("economics.evaluationHours_h must be a non-empty array")
    hours = tuple(sorted(
        _number({"hours": value}, "hours", f"economics.evaluationHours_h[{index}]", 0)
        for index, value in enumerate(raw_hours)
    ))
    if len(set(hours)) != len(hours):
        raise ConfigError("economics.evaluationHours_h must contain unique values")
    model = EconomicsInput(
        analysis_id=_string(envelope, "analysisId", "economics"),
        currency=_string(envelope, "currency", "economics"),
        provenance=_parse_provenance(envelope["provenance"], "economics.provenance"),
        tooling=tuple(
            _tooling(item, f"economics.tooling[{index}]")
            for index, item in enumerate(_array(envelope["tooling"], "economics.tooling"))
        ),
        fabrication=tuple(
            _fabrication(item, f"economics.fabrication[{index}]")
            for index, item in enumerate(_array(envelope["fabrication"], "economics.fabrication"))
        ),
        labor_rates=tuple(
            _labor_rate(item, f"economics.laborRates[{index}]")
            for index, item in enumerate(_array(envelope["laborRates"], "economics.laborRates"))
        ),
        rentals=tuple(
            _rental(item, f"economics.rentals[{index}]")
            for index, item in enumerate(_array(envelope["rentals"], "economics.rentals"))
        ),
        fabrication_labor_role=_string(envelope, "fabricationLaborRole", "economics"),
        evaluation_hours=hours,
        annual_fixed_ownership_cost=_number(envelope, "annualFixedOwnershipCost", "economics", 0),
        ownership_hours_per_year=_number(envelope, "ownershipHoursPerYear", "economics", 0, strict_low=True),
        owned_microgrid_energy_cost_per_h=_number(
            envelope, "ownedMicrogridEnergyCostPer_h", "economics", 0,
        ),
        site_adaptations=tuple(
            _adaptation(item, f"economics.siteAdaptations[{index}]")
            for index, item in enumerate(_array(envelope["siteAdaptations"], "economics.siteAdaptations"))
        ),
        policies=tuple(
            _policy(item, f"economics.policies[{index}]")
            for index, item in enumerate(_array(envelope["policies"], "economics.policies"))
        ),
    )
    _validate_model(model)
    return model


def load_economics_input(path: str | Path) -> EconomicsInput:
    return parse_economics_input(load_json(path))


def _unique_ids(values: tuple[str, ...], name: str) -> None:
    if len(set(values)) != len(values):
        raise ConfigError(f"{name} must contain unique IDs")


def _validate_policy(policy: PathwayPolicy, name: str = "policy") -> None:
    if not isinstance(policy, PathwayPolicy):
        raise ConfigError(f"{name} must be PathwayPolicy")
    if not isinstance(policy.pathway, AcquisitionPathway):
        raise ConfigError(f"{name}.pathway must be AcquisitionPathway")
    for field_name in ("owned_item_ids", "rental_item_ids", "site_adaptation_ids"):
        value = getattr(policy, field_name)
        if not isinstance(value, tuple):
            raise ConfigError(f"{name}.{field_name} must be a tuple")
        for index, item in enumerate(value):
            _nonempty_text(item, f"{name}.{field_name}[{index}]")
        _unique_ids(value, f"{name}.{field_name}")
    if policy.pathway is AcquisitionPathway.DIY and policy.rental_item_ids:
        raise ConfigError(f"{name}: DIY cannot contain rental items")
    if policy.pathway is AcquisitionPathway.RENTAL and policy.owned_item_ids:
        raise ConfigError(f"{name}: RENTAL cannot contain owned fabrication or tooling")
    if policy.pathway is AcquisitionPathway.HYBRID and not (
        policy.owned_item_ids and policy.rental_item_ids
    ):
        raise ConfigError(f"{name}: HYBRID requires both owned and rental items")


def _validate_adaptation(item: CostScheduleDelta, currency: str, name: str) -> None:
    if not isinstance(item, CostScheduleDelta):
        raise ConfigError(f"{name} must be CostScheduleDelta")
    _nonempty_text(item.adaptation_id, f"{name}.adaptation_id")
    _finite(item.cost_delta, f"{name}.cost_delta")
    _finite(item.schedule_delta_h, f"{name}.schedule_delta_h")
    _finite(item.labor_delta_h, f"{name}.labor_delta_h")
    _nonempty_text(item.basis, f"{name}.basis")
    if item.currency != currency:
        raise ConfigError(f"{name}.currency must match the economics currency")


def _validate_policy_references(model: EconomicsInput, policy: PathwayPolicy, name: str) -> None:
    owned = {item.item_id: item for item in (*model.tooling, *model.fabrication)}
    rentals = {item.item_id: item for item in model.rentals}
    adaptations = {item.adaptation_id: item for item in model.site_adaptations}
    for item_id in policy.owned_item_ids:
        if item_id not in owned:
            raise ConfigError(f"{name}.owned_item_ids references unknown item {item_id!r}")
        if policy.pathway not in owned[item_id].applies_to:
            raise ConfigError(f"{name} is not authorized by item {item_id!r} applies_to")
    for item_id in policy.rental_item_ids:
        if item_id not in rentals:
            raise ConfigError(f"{name}.rental_item_ids references unknown item {item_id!r}")
        if policy.pathway not in rentals[item_id].applies_to:
            raise ConfigError(f"{name} is not authorized by item {item_id!r} applies_to")
    for adaptation_id in policy.site_adaptation_ids:
        if adaptation_id not in adaptations:
            raise ConfigError(f"{name}.site_adaptation_ids references unknown item {adaptation_id!r}")


def _labor_rate_for(model: EconomicsInput) -> LaborRate:
    matches = tuple(item for item in model.labor_rates if item.role == model.fabrication_labor_role)
    if len(matches) != 1:
        raise ConfigError("fabrication_labor_role must resolve to exactly one labor rate")
    return matches[0]


def _check_policy_labor(model: EconomicsInput, policy: PathwayPolicy) -> None:
    labor_rate = _labor_rate_for(model)
    labor_hours = _sum(
        (
            _product(item.quantity, item.labor_hours_per_unit, name=f"{item.item_id} labor hours")
            for item in _selected_fabrication(model, policy)
        ),
        "selected fabrication labor hours",
    )
    if labor_hours > labor_rate.available_hours:
        raise ConfigError(
            f"{policy.pathway.value} fabrication labor hours exceed available_hours for {labor_rate.role!r}",
        )


def _validate_model(model: EconomicsInput) -> None:
    if not isinstance(model, EconomicsInput):
        raise ConfigError("model must be EconomicsInput")
    _nonempty_text(model.analysis_id, "analysis_id")
    if not isinstance(model.currency, str) or re.fullmatch(r"[A-Z]{3}", model.currency) is None:
        raise ConfigError("currency must match [A-Z]{3}")
    _validate_provenance(model.provenance)
    for field_name in (
        "tooling", "fabrication", "labor_rates", "rentals", "evaluation_hours", "site_adaptations", "policies",
    ):
        if not isinstance(getattr(model, field_name), tuple):
            raise ConfigError(f"{field_name} must be a tuple")
    for index, item in enumerate(model.tooling):
        _validate_tooling(item, f"tooling[{index}]")
    for index, item in enumerate(model.fabrication):
        _validate_fabrication(item, f"fabrication[{index}]")
    for index, item in enumerate(model.labor_rates):
        _validate_labor_rate(item, f"labor_rates[{index}]")
    for index, item in enumerate(model.rentals):
        _validate_rental(item, f"rentals[{index}]")
    owned_ids = tuple(item.item_id for item in (*model.tooling, *model.fabrication))
    _unique_ids(owned_ids, "owned item IDs")
    _unique_ids(tuple(item.item_id for item in model.rentals), "rental item IDs")
    _unique_ids(tuple(item.role for item in model.labor_rates), "labor roles")
    _unique_ids(tuple(item.adaptation_id for item in model.site_adaptations), "site adaptation IDs")
    for index, item in enumerate(model.site_adaptations):
        _validate_adaptation(item, model.currency, f"site_adaptations[{index}]")
    _nonempty_text(model.fabrication_labor_role, "fabrication_labor_role")
    _labor_rate_for(model)
    if not model.evaluation_hours:
        raise ConfigError("evaluation_hours must be non-empty")
    for index, hours in enumerate(model.evaluation_hours):
        _at_least(hours, 0, f"evaluation_hours[{index}]")
    if len(set(model.evaluation_hours)) != len(model.evaluation_hours):
        raise ConfigError("evaluation_hours must be unique")
    if tuple(sorted(model.evaluation_hours)) != model.evaluation_hours:
        raise ConfigError("evaluation_hours must be sorted")
    _at_least(model.annual_fixed_ownership_cost, 0, "annual_fixed_ownership_cost")
    _at_least(model.ownership_hours_per_year, 0, "ownership_hours_per_year", strict=True)
    _at_least(model.owned_microgrid_energy_cost_per_h, 0, "owned_microgrid_energy_cost_per_h")
    if len(model.policies) != 3:
        raise ConfigError("policies must contain exactly DIY, RENTAL, and HYBRID")
    for index, policy in enumerate(model.policies):
        name = f"policies[{index}]"
        _validate_policy(policy, name)
        _validate_policy_references(model, policy, name)
        _check_policy_labor(model, policy)
    pathways = tuple(policy.pathway for policy in model.policies)
    if set(pathways) != set(_PATHWAY_ORDER) or len(set(pathways)) != len(pathways):
        raise ConfigError("policies must contain exactly one of each pathway")


def _selected_tooling(model: EconomicsInput, policy: PathwayPolicy) -> tuple[ToolingItem, ...]:
    selected = set(policy.owned_item_ids)
    return tuple(item for item in model.tooling if item.item_id in selected)


def _selected_fabrication(model: EconomicsInput, policy: PathwayPolicy) -> tuple[FabricationItem, ...]:
    selected = set(policy.owned_item_ids)
    return tuple(item for item in model.fabrication if item.item_id in selected)


def fabrication_totals(
    model: EconomicsInput,
    pathway: AcquisitionPathway,
) -> tuple[float, float, float, float]:
    """Return material, component, one-project labor hours, and selected tooling CAPEX."""

    if not isinstance(model, EconomicsInput):
        raise ConfigError("model must be EconomicsInput")
    pathway = _enum_member(AcquisitionPathway, pathway, "pathway")
    matches = tuple(policy for policy in model.policies if policy.pathway is pathway)
    if len(matches) != 1:
        raise ConfigError(f"exactly one {pathway.value} policy is required")
    policy = matches[0]
    _validate_policy(policy)
    _validate_policy_references(model, policy, pathway.value)
    fabrication = _selected_fabrication(model, policy)
    tooling = _selected_tooling(model, policy)
    material = _sum(
        (_product(item.quantity, item.unit_material_cost, name=f"{item.item_id} material") for item in fabrication),
        "fabrication material cost",
    )
    component = _sum(
        (_product(item.quantity, item.unit_component_cost, name=f"{item.item_id} component") for item in fabrication),
        "fabrication component cost",
    )
    labor_hours = _sum(
        (_product(item.quantity, item.labor_hours_per_unit, name=f"{item.item_id} labor") for item in fabrication),
        "fabrication labor hours",
    )
    tooling_capex = _sum((item.startup_capex for item in tooling), "startup tooling CAPEX")
    return material, component, labor_hours, tooling_capex


def rental_cost(item: RentalItem, operating_hours: float) -> tuple[float, float, float]:
    """Prorate one rental linearly and return rental, mobilization, and energy."""

    _validate_rental(item)
    hours = _at_least(operating_hours, 0, "operating_hours")
    unit_hours = _BILLING_HOURS[item.billing_unit]
    rental = _product(
        item.rate_per_billing_unit,
        checked_divide(hours, unit_hours, "rental lifecycle hours"),
        name="prorated rental cost",
    )
    mobilization = _product(
        item.delivery_per_mobilization, item.mobilizations_per_project,
        name="one-project mobilization cost",
    )
    energy = _product(item.fuel_or_energy_per_h, hours, name="rental fuel or energy cost")
    return rental, mobilization, energy


def _line(category: CostCategory, fixed: float, variable: float, basis: str) -> CostLine:
    return CostLine(
        category,
        _finite(fixed, f"{category.value} fixed cost"),
        _at_least(variable, 0, f"{category.value} variable cost"),
        basis,
    )


def evaluate_pathway(
    model: EconomicsInput,
    policy: PathwayPolicy,
    operating_hours: float,
) -> PathwayCost:
    """Evaluate one complete affine pathway cost without display rounding."""

    _validate_model(model)
    _validate_policy(policy)
    if policy not in model.policies:
        raise ConfigError("policy must be one of the model's declared policies")
    hours = _at_least(operating_hours, 0, "operating_hours")
    pathway = policy.pathway
    material, component, labor_hours, tooling_capex = fabrication_totals(model, pathway)
    _check_policy_labor(model, policy)
    labor_rate = _labor_rate_for(model)
    labor_cost = _product(labor_hours, labor_rate.rate_per_h, name="one-project fabrication labor cost")

    selected_tooling = _selected_tooling(model, policy)
    selected_fabrication = _selected_fabrication(model, policy)
    tooling_variable = _sum(
        (
            _sum((
                item.maintenance_per_h,
                checked_divide(item.startup_capex, item.service_life_h, f"{item.item_id} replacement reserve"),
            ), f"{item.item_id} tooling hourly reserve")
            for item in selected_tooling
        ),
        "tooling maintenance and replacement reserve",
    )
    fabrication_wear = _sum(
        (item.hourly_wear_reserve for item in selected_fabrication), "fabrication hourly wear reserve",
    )
    ownership_variable = 0.0
    owned_energy_variable = 0.0
    if pathway in _OWNED_PATHWAYS:
        ownership_variable = checked_divide(
            model.annual_fixed_ownership_cost, model.ownership_hours_per_year,
            "fixed ownership allocation per operating hour",
        )
        owned_energy_variable = model.owned_microgrid_energy_cost_per_h

    selected_ids = set(policy.rental_item_ids)
    selected_rentals = tuple(item for item in model.rentals if item.item_id in selected_ids)
    rental_parts = tuple(rental_cost(item, hours) for item in selected_rentals)
    rental_amount = _sum((part[0] for part in rental_parts), "prorated rental cost")
    mobilization_fixed = _sum((part[1] for part in rental_parts), "rental mobilization cost")
    rental_energy = _sum((part[2] for part in rental_parts), "rental energy cost")
    rental_variable = _sum(
        (
            checked_divide(item.rate_per_billing_unit, _BILLING_HOURS[item.billing_unit], f"{item.item_id} hourly rental")
            for item in selected_rentals
        ),
        "rental variable cost per hour",
    )
    rental_energy_variable = _sum(
        (item.fuel_or_energy_per_h for item in selected_rentals), "rental energy cost per hour",
    )
    rental_wear_variable = _sum(
        (0.0 if item.hourly_wear_reserve_included else item.hourly_wear_reserve for item in selected_rentals),
        "separate rental hourly wear reserve",
    )
    wear_variable = _sum(
        (ownership_variable, tooling_variable, fabrication_wear, rental_wear_variable),
        "wear and maintenance variable cost",
    )
    energy_variable = _sum((owned_energy_variable, rental_energy_variable), "energy variable cost")
    owned_energy = _product(owned_energy_variable, hours, name="owned microgrid energy cost")
    energy_amount = _sum((owned_energy, rental_energy), "energy cost")
    wear_amount = _product(wear_variable, hours, name="wear and maintenance cost")

    adaptation_by_id = {item.adaptation_id: item for item in model.site_adaptations}
    adaptation_fixed = _sum(
        (adaptation_by_id[item_id].cost_delta for item_id in policy.site_adaptation_ids),
        "selected site adaptation cost delta",
    )
    lines = (
        _line(CostCategory.TOOLING, tooling_capex, 0.0, "Selected shop startup tooling CAPEX; synthetic and unquoted."),
        _line(CostCategory.FABRICATION_MATERIAL, material, 0.0, "Quantity times unit material cost for selected items."),
        _line(
            CostCategory.FABRICATION_COMPONENT, component, 0.0,
            "Quantity times unit component cost for selected items.",
        ),
        _line(CostCategory.LABOR, labor_cost, 0.0, "One-project selected fabrication hours times the named role rate."),
        _line(CostCategory.RENTAL, 0.0, rental_variable, "Linear lifecycle rental proration; not an invoice or quote."),
        _line(
            CostCategory.MOBILIZATION, mobilization_fixed, 0.0,
            "Delivery per mobilization times declared one-project mobilizations.",
        ),
        _line(
            CostCategory.WEAR_MAINTENANCE, 0.0, wear_variable,
            "Ownership allocation, tooling life/maintenance, fabrication wear, and separate rental wear reserves.",
        ),
        _line(CostCategory.ENERGY, 0.0, energy_variable, "Owned microgrid and rental fuel/energy hourly assumptions."),
        _line(
            CostCategory.SITE_ADAPTATION, adaptation_fixed, 0.0,
            "Selected signed synthetic CostScheduleDelta amounts; no supplier quote or site authorization.",
        ),
    )
    total = _sum(
        (
            _sum((line.fixed_cost, _product(line.variable_cost_per_h, hours, name="line variable cost")), "line cost")
            for line in lines
        ),
        "pathway total cost",
    )
    result = PathwayCost(
        pathway=pathway,
        operating_hours=hours,
        currency=model.currency,
        lines=lines,
        shop_startup_tooling_capex=tooling_capex,
        fabrication_cost=_sum((material, component), "fabrication cost"),
        labor_hours=labor_hours,
        labor_cost=labor_cost,
        rental_cost=rental_amount,
        wear_maintenance_cost=wear_amount,
        energy_cost=energy_amount,
        site_adaptation_cost=adaptation_fixed,
        total_cost=total,
    )
    return _validated_cost(result)


def _fixed_variable_totals(cost: PathwayCost) -> tuple[float, float]:
    fixed = _sum((line.fixed_cost for line in cost.lines), "fixed cost total")
    variable = _sum((line.variable_cost_per_h for line in cost.lines), "variable cost total")
    return fixed, variable


def _category_amount(cost: PathwayCost, category: CostCategory) -> float:
    lines = tuple(line for line in cost.lines if line.category is category)
    return _sum(
        (
            _sum((line.fixed_cost, _product(line.variable_cost_per_h, cost.operating_hours, name="category cost")), "line")
            for line in lines
        ),
        f"{category.value} amount",
    )


def _close(left: float, right: float, tolerance: float = 1e-6) -> bool:
    return math.isclose(left, right, rel_tol=0, abs_tol=tolerance)


def _validated_cost(cost: PathwayCost) -> PathwayCost:
    if not isinstance(cost, PathwayCost):
        raise ConfigError("cost must be PathwayCost")
    if not isinstance(cost.pathway, AcquisitionPathway):
        raise ConfigError("cost.pathway must be AcquisitionPathway")
    _at_least(cost.operating_hours, 0, "cost.operating_hours")
    if not isinstance(cost.currency, str) or re.fullmatch(r"[A-Z]{3}", cost.currency) is None:
        raise ConfigError("cost.currency must match [A-Z]{3}")
    if not isinstance(cost.lines, tuple) or not cost.lines:
        raise ConfigError("cost.lines must be a non-empty tuple")
    categories = []
    for index, line in enumerate(cost.lines):
        if not isinstance(line, CostLine) or not isinstance(line.category, CostCategory):
            raise ConfigError(f"cost.lines[{index}] must be a CostLine with a CostCategory")
        _finite(line.fixed_cost, f"cost.lines[{index}].fixed_cost")
        _at_least(line.variable_cost_per_h, 0, f"cost.lines[{index}].variable_cost_per_h")
        _nonempty_text(line.basis, f"cost.lines[{index}].basis")
        if line.category is not CostCategory.SITE_ADAPTATION:
            _at_least(line.fixed_cost, 0, f"cost.lines[{index}].fixed_cost")
        categories.append(line.category)
    if len(set(categories)) != len(categories):
        raise ConfigError("cost line categories must be unique")
    fixed, variable = _fixed_variable_totals(cost)
    expected_total = _sum((fixed, _product(variable, cost.operating_hours, name="total variable cost")), "total cost")
    _finite(cost.total_cost, "cost.total_cost")
    if cost.total_cost < 0:
        raise ConfigError("negative adapted pathway total requires human correction")
    if not _close(cost.total_cost, expected_total):
        raise ConfigError("pathway total does not reconcile with its unrounded cost lines")
    expected = {
        "shop_startup_tooling_capex": _category_amount(cost, CostCategory.TOOLING),
        "fabrication_cost": _sum((
            _category_amount(cost, CostCategory.FABRICATION_MATERIAL),
            _category_amount(cost, CostCategory.FABRICATION_COMPONENT),
        ), "fabrication cost"),
        "labor_cost": _category_amount(cost, CostCategory.LABOR),
        "rental_cost": _category_amount(cost, CostCategory.RENTAL),
        "wear_maintenance_cost": _category_amount(cost, CostCategory.WEAR_MAINTENANCE),
        "energy_cost": _category_amount(cost, CostCategory.ENERGY),
        "site_adaptation_cost": _category_amount(cost, CostCategory.SITE_ADAPTATION),
    }
    for field_name, expected_value in expected.items():
        value = _finite(getattr(cost, field_name), f"cost.{field_name}")
        if not _close(value, expected_value):
            raise ConfigError(f"cost.{field_name} does not reconcile with its cost lines")
    _at_least(cost.labor_hours, 0, "cost.labor_hours")
    return cost


def _cheaper(left_value: float, right_value: float, left: AcquisitionPathway, right: AcquisitionPathway):
    if left_value < right_value:
        return left
    if right_value < left_value:
        return right
    return None


def break_even(left: PathwayCost, right: PathwayCost) -> BreakEvenResult:
    """Find the unique positive crossing of two unrounded affine cost models."""

    _validated_cost(left)
    _validated_cost(right)
    if left.operating_hours != right.operating_hours:
        raise ConfigError("break-even inputs must use equal operating_hours")
    if left.currency != right.currency:
        raise ConfigError("break-even inputs must use the same currency")
    if left.pathway is right.pathway:
        raise ConfigError("break-even inputs must describe different pathways")
    fixed_left, variable_left = _fixed_variable_totals(left)
    fixed_right, variable_right = _fixed_variable_totals(right)
    below = _cheaper(fixed_left, fixed_right, left.pathway, right.pathway)
    if variable_left == variable_right:
        if fixed_left == fixed_right:
            return BreakEvenResult(
                left.pathway, right.pathway, None, None, None, True,
                "Fixed and variable costs are identical; the pathways tie everywhere.",
            )
        above = below
        return BreakEvenResult(
            left.pathway, right.pathway, below, above, None, False,
            "Variable costs are equal; the lower fixed-cost pathway is cheaper everywhere.",
        )
    numerator = _sum((fixed_right, -fixed_left), "break-even fixed-cost difference")
    denominator = _sum((variable_left, -variable_right), "break-even variable-cost difference")
    crossing = checked_divide(numerator, denominator, "break-even operating hours")
    above_probe = _sum((crossing, max(1.0, abs(crossing))), "above-crossing probe hours")
    left_above = _sum((fixed_left, _product(variable_left, above_probe, name="left above cost")), "left above cost")
    right_above = _sum((fixed_right, _product(variable_right, above_probe, name="right above cost")), "right above cost")
    above = _cheaper(left_above, right_above, left.pathway, right.pathway)
    if crossing <= 0:
        return BreakEvenResult(
            left.pathway, right.pathway, below, above, None, False,
            "The affine crossing is not at positive operating hours; no positive break-even is reported.",
        )
    left_crossing = _sum((fixed_left, _product(variable_left, crossing, name="left crossing cost")), "left crossing cost")
    right_crossing = _sum((fixed_right, _product(variable_right, crossing, name="right crossing cost")), "right crossing cost")
    if left_crossing < 0 or right_crossing < 0:
        return BreakEvenResult(
            left.pathway, right.pathway, below, above, None, False,
            "The candidate crossing produces a negative adapted total and is rejected for human correction.",
        )
    return BreakEvenResult(
        left.pathway, right.pathway, below, above, crossing, False,
        "Positive affine crossing; both pathway totals are nonnegative and equal at the reported hours.",
    )


def compare_pathways(model: EconomicsInput) -> EconomicsResult:
    """Evaluate canonical pathway/hour ordering and all three pairwise crossings."""

    _validate_model(model)
    policies = {policy.pathway: policy for policy in model.policies}
    costs = tuple(
        evaluate_pathway(model, policies[pathway], hours)
        for pathway in _PATHWAY_ORDER
        for hours in model.evaluation_hours
    )
    zero_costs = {
        pathway: evaluate_pathway(model, policies[pathway], 0.0)
        for pathway in _PATHWAY_ORDER
    }
    crossings = tuple(
        break_even(zero_costs[left], zero_costs[right])
        for left, right in _BREAK_EVEN_PAIRS
    )
    return EconomicsResult(
        analysis_id=model.analysis_id,
        status=EvidenceStatus.SIMULATED_UNREVIEWED,
        pathway_costs=costs,
        break_even=crossings,
        currency=model.currency,
    )


_MONETARY_FIELDS = frozenset({
    "fixed_cost", "variable_cost_per_h", "shop_startup_tooling_capex", "fabrication_cost", "labor_cost",
    "rental_cost", "wear_maintenance_cost", "energy_cost", "site_adaptation_cost", "total_cost",
})


def _camel(name: str) -> str:
    suffix = "_h" if name.endswith("_h") else ""
    stem = name[:-2] if suffix else name
    parts = stem.split("_")
    return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:]) + suffix


def _json_value(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        converted = {}
        for field in fields(value):
            item = _json_value(getattr(value, field.name))
            if field.name in _MONETARY_FIELDS:
                item = round(_finite(item, field.name), 6)
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


def _validate_result(result: EconomicsResult) -> None:
    if not isinstance(result, EconomicsResult):
        raise ConfigError("result must be EconomicsResult")
    _nonempty_text(result.analysis_id, "result.analysis_id")
    if result.status is not EvidenceStatus.SIMULATED_UNREVIEWED:
        raise ConfigError("result status must remain SIMULATED_UNREVIEWED")
    if not isinstance(result.currency, str) or re.fullmatch(r"[A-Z]{3}", result.currency) is None:
        raise ConfigError("result.currency must match [A-Z]{3}")
    if (
        result.quotes_obtained is not False
        or result.procurement_authorized is not False
        or result.physical_validation_performed is not False
    ):
        raise ConfigError("quotes, procurement authorization, and physical validation must remain false")
    if not isinstance(result.pathway_costs, tuple) or not isinstance(result.break_even, tuple):
        raise ConfigError("pathway_costs and break_even must be tuples")
    expected_order = tuple(
        (pathway, hours)
        for pathway in _PATHWAY_ORDER
        for hours in sorted({cost.operating_hours for cost in result.pathway_costs if cost.pathway is pathway})
    )
    actual_order = tuple((cost.pathway, cost.operating_hours) for cost in result.pathway_costs)
    if actual_order != expected_order or len(set(actual_order)) != len(actual_order):
        raise ConfigError("pathway costs must be unique and ordered by pathway then operating hours")
    for cost in result.pathway_costs:
        _validated_cost(cost)
        if cost.currency != result.currency:
            raise ConfigError("every pathway currency must match the result currency")
    actual_pairs = tuple((item.left_path, item.right_path) for item in result.break_even)
    if actual_pairs != _BREAK_EVEN_PAIRS:
        raise ConfigError("break-even pairs must be DIY/RENTAL, DIY/HYBRID, then RENTAL/HYBRID")
    for item in result.break_even:
        if not isinstance(item, BreakEvenResult):
            raise ConfigError("break_even entries must be BreakEvenResult")
        _nonempty_text(item.reason, "break_even.reason")
        if item.operating_hours is not None:
            _at_least(item.operating_hours, 0, "break_even.operating_hours", strict=True)
        if item.is_exact_tie_everywhere and item.operating_hours is not None:
            raise ConfigError("an exact tie everywhere cannot have one crossing")


def economics_result_json(result: EconomicsResult) -> str:
    """Serialize validated results with six-place monetary rounding and canonical JSON."""

    _validate_result(result)
    compatible = _json_value(result)
    _check_json_value(compatible)
    try:
        return json.dumps(
            compatible, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False,
        ) + "\n"
    except (TypeError, ValueError, OverflowError) as exc:
        raise ConfigError("economics result is not finite JSON") from exc


def write_economics_result(result: EconomicsResult, output_dir: str | Path) -> Path:
    text = economics_result_json(result)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / "result.json"
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


class PathwayEvaluator:
    """Stateless convenience facade with no I/O, persistence, or procurement path."""

    def run(self, model: EconomicsInput) -> EconomicsResult:
        return compare_pathways(model)
