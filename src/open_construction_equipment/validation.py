# SPDX-License-Identifier: Apache-2.0
"""Offline strict CSV/JSON integrity and cross-reference checks."""

from __future__ import annotations

import csv
import math
from pathlib import Path
import re
from typing import Any

from .bom import read_bom
from .config import ConfigError, load_json, load_mission_config, load_simulation_config
from .maintenance import load_service_history, load_service_plan
from .resources import default_data_root, is_source_repository

IGNORED_PARTS = {".git", ".venv", "venv", "builds", "__pycache__"}
_OWNER_ATTRIBUTION = re.compile(
    r"\bowner(?:[- ](?:provided|supplied|authored|approved)|\s+concept\s+target)\b", re.IGNORECASE)
_NEGATION = re.compile(r"\b(?:not|never|without|no|false)\b[^.;\n]*$", re.IGNORECASE)


def repository_root() -> Path:
    return default_data_root()


def _files(root: Path, suffix: str) -> list[Path]:
    return sorted(path for path in root.rglob(f"*{suffix}") if not IGNORED_PARTS.intersection(path.relative_to(root).parts))


def _service_ids(root: Path) -> set[str]:
    path = root / "maintenance/ctl01/service-schedule.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        return {row["service_id"] for row in csv.DictReader(handle, strict=True)}


def _validate_design_inputs(value: dict[str, Any]) -> None:
    parameters = value.get("parameters")
    if not isinstance(parameters, list):
        raise ValueError("design-inputs parameters must be an array")
    for index, parameter in enumerate(parameters):
        if not isinstance(parameter, dict):
            raise ValueError(f"design-inputs parameter {index} must be an object")
        number = parameter.get("value")
        if isinstance(number, (int, float)) and not isinstance(number, bool):
            try:
                finite = math.isfinite(float(number))
            except (OverflowError, ValueError):
                finite = False
            if not finite:
                raise ValueError(f"design-inputs parameter {parameter.get('id', index)} value must be finite")


def _false_owner_attribution(text: str) -> bool:
    for line in text.splitlines():
        for match in _OWNER_ATTRIBUTION.finditer(line):
            if not _NEGATION.search(line[:match.start()]):
                return True
    return False


def _provenance_files(root: Path) -> list[Path]:
    files = [root / name for name in ("AGENTS.md", "CHANGELOG.md", "LICENSE", "NOTICE.md", "README.md")]
    for directory in ("configs", "docs", "examples", "hardware", "maintenance", "manufacturing"):
        base = root / directory
        if base.is_dir():
            files.extend(path for path in base.rglob("*")
                         if path.is_file() and path.suffix.lower() in {".csv", ".json", ".md", ".scad"})
    return sorted(path for path in files if path.is_file())


def validate_repository(root: str | Path | None = None) -> dict[str, Any]:
    explicit_root = root is not None
    root = Path(root) if explicit_root else default_data_root()
    full_repository = explicit_root or is_source_repository(root)
    errors: list[str] = []
    json_files, csv_files = _files(root, ".json"), _files(root, ".csv")
    for path in json_files:
        try:
            value = load_json(path)
            if path == root / "hardware/ctl01/design-inputs.json":
                _validate_design_inputs(value)
        except (ConfigError, ValueError) as exc:
            errors.append(f"{path.relative_to(root)}: {exc}")
    for path in csv_files:
        try:
            with path.open(newline="", encoding="utf-8") as handle:
                reader = csv.reader(handle, strict=True)
                header = next(reader)
                if not header or any(not name for name in header) or len(set(header)) != len(header):
                    raise ValueError("empty or duplicate CSV headers")
                for line, row in enumerate(reader, 2):
                    if len(row) != len(header):
                        raise ValueError(f"row {line} has {len(row)} columns, expected {len(header)}")
        except (OSError, csv.Error, StopIteration, ValueError) as exc:
            errors.append(f"{path.relative_to(root)}: {exc}")
    try:
        service_ids = _service_ids(root)
        if len(service_ids) != 20:
            raise ValueError(f"expected 20 stable SVC IDs, found {len(service_ids)}")
        load_service_plan(root / "maintenance/ctl01/service-intervals.json", service_ids)
        load_service_history(root / "examples/maintenance/synthetic-service-history.json", service_ids)
        schedule_path = root / "maintenance/ctl01/service-schedule.csv"
        with schedule_path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle, strict=True))
        # Filename identities are PR-001 through PR-008, independent of descriptions.
        available_procedures = {match.group(0) for path in (root / "maintenance/ctl01/procedures").glob("*.md")
                                if (match := re.match(r"PR-\d{3}", path.name))}
        for row in rows:
            for procedure in row["linked_procedure"].split(";"):
                if procedure not in available_procedures:
                    raise ValueError(f"{row['service_id']} references missing {procedure}")
    except (OSError, csv.Error, ConfigError, ValueError, KeyError) as exc:
        errors.append(f"maintenance cross-references: {exc}")
    try:
        load_simulation_config(root / "configs/ctl01.simulation.json")
        load_mission_config(root / "examples/missions/synthetic-yard.json")
    except ConfigError as exc:
        errors.append(f"simulation inputs: {exc}")
    try:
        read_bom(root / "hardware/ctl01/bom/ctl01-bom.csv")
    except ConfigError as exc:
        errors.append(f"BOM: {exc}")
    if full_repository:
        for path in _provenance_files(root):
            try:
                if _false_owner_attribution(path.read_text(encoding="utf-8")):
                    errors.append(f"{path.relative_to(root)}: false owner-supplied/provided attribution remains")
            except OSError as exc:
                errors.append(f"{path.relative_to(root)}: {exc}")
        license_path = root / "LICENSE"
        try:
            if re.search(r"no\s+software\s+package\s+is\s+included", license_path.read_text(encoding="utf-8"), re.IGNORECASE):
                errors.append("LICENSE: stale no-software-package statement remains")
        except OSError as exc:
            errors.append(f"LICENSE: {exc}")
    scope = "source-repository" if full_repository else "package-resources"
    return {
        "status": "passed" if not errors else "failed",
        "validationScope": scope,
        "fullRepositoryValidation": full_repository,
        "root": str(root),
        "jsonFilesChecked": len(json_files),
        "csvFilesChecked": len(csv_files),
        "serviceIdsChecked": 20,
        "errors": errors,
        "physicalValidationPerformed": False,
    }
