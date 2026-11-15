# SPDX-License-Identifier: Apache-2.0
"""Strict BOM reading and quantity/criticality summaries."""

from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from .config import ConfigError

REQUIRED_BOM_COLUMNS = ("item_id", "subsystem", "item_name", "quantity", "unit", "make_buy",
                        "specification_or_selection_criteria", "safety_critical", "lifecycle_status")


def _quantity(value: Decimal) -> int | float:
    return int(value) if value == value.to_integral_value() else float(value)


def read_bom(path: str | Path) -> list[dict[str, str]]:
    source = Path(path)
    try:
        with source.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle, strict=True)
            if tuple(reader.fieldnames or ()) != REQUIRED_BOM_COLUMNS:
                raise ConfigError(f"BOM columns must be exactly {', '.join(REQUIRED_BOM_COLUMNS)}")
            rows = list(reader)
    except (OSError, csv.Error) as exc:
        raise ConfigError(f"cannot read BOM {source}: {exc}") from exc
    if not rows:
        raise ConfigError("BOM must contain items")
    seen: set[str] = set()
    for line, row in enumerate(rows, 2):
        if None in row or any(value is None for value in row.values()):
            raise ConfigError(f"BOM row {line} has wrong column count")
        item_id = row["item_id"].strip()
        if not item_id or item_id in seen:
            raise ConfigError(f"BOM row {line} has empty or duplicate item_id")
        seen.add(item_id)
        try:
            quantity = Decimal(row["quantity"])
        except InvalidOperation as exc:
            raise ConfigError(f"BOM row {line} quantity is not numeric") from exc
        if not quantity.is_finite() or quantity <= 0:
            raise ConfigError(f"BOM row {line} quantity must be positive and finite")
        if row["safety_critical"] not in ("yes", "no"):
            raise ConfigError(f"BOM row {line} safety_critical must be yes or no")
        for column in ("subsystem", "item_name", "unit", "make_buy", "specification_or_selection_criteria", "lifecycle_status"):
            if not row[column].strip():
                raise ConfigError(f"BOM row {line} has empty {column}")
    return rows


def summarize_bom(path: str | Path) -> dict[str, Any]:
    rows = read_bom(path)
    subsystems: dict[str, dict[str, Any]] = {}
    criticality = {"yes": {"items": 0, "quantity": Decimal(0)}, "no": {"items": 0, "quantity": Decimal(0)}}
    total = Decimal(0)
    for row in rows:
        quantity = Decimal(row["quantity"])
        total += quantity
        subsystem = subsystems.setdefault(row["subsystem"], {"items": 0, "quantity": Decimal(0), "safetyCriticalItems": 0})
        subsystem["items"] += 1
        subsystem["quantity"] += quantity
        if row["safety_critical"] == "yes":
            subsystem["safetyCriticalItems"] += 1
        criticality[row["safety_critical"]]["items"] += 1
        criticality[row["safety_critical"]]["quantity"] += quantity
    return {
        "platform": "OCE-CTL-01",
        "source": str(path),
        "status": "CONCEPT_UNRELEASED_NOT_PROCUREMENT_AUTHORITY",
        "itemCount": len(rows),
        "totalQuantity": _quantity(total),
        "bySubsystem": {name: {**values, "quantity": _quantity(values["quantity"])} for name, values in sorted(subsystems.items())},
        "bySafetyCriticality": {name: {**values, "quantity": _quantity(values["quantity"])} for name, values in criticality.items()},
        "notice": "Quantities aggregate mixed units for concept accounting only; they are not a physical parts count or purchase instruction.",
    }
