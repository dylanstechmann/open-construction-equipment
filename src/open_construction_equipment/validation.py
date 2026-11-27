# SPDX-License-Identifier: Apache-2.0
"""Offline strict CSV/JSON integrity and cross-reference checks."""

from __future__ import annotations

import csv
import math
from pathlib import Path
import re
from typing import Any
import xml.etree.ElementTree as ET

from .bom import read_bom
from .bunker import (
    BunkerPlanInput, construction_energy_json, load_bunker_input, load_bunker_registers,
    load_bunker_site, plan_bunker,
)
from .cad_blender import (
    export_wavefront,
    generate_blender_python,
    generate_freecad_python,
    generate_mujoco_mjcf,
    generate_openscad,
    load_cad_scene,
    mesh_box,
)
from .config import ConfigError, load_json, load_mission_config, load_simulation_config
from .economics import compare_pathways, economics_result_json, load_economics_input
from .engineering import LongitudinalAnalysisInput, load_analysis_input
from .geohazard_rural import (
    adapt_to_existing_site,
    geohazard_result_json,
    load_geohazard_document,
    parse_geohazard_input,
    screen_candidate_parcels,
)
from .maintenance import load_service_history, load_service_plan
from .physics import evaluate_physics, load_physics_input, physics_result_json
from .powertrain import compare_powertrains, load_powertrain_input, powertrain_result_json
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


def validate_analysis_source_traces(root: Path, model: LongitudinalAnalysisInput) -> None:
    """Resolve every AN-LC-001A trace ID to the checked-out source registers."""

    def csv_ids(relative: str, column: str) -> set[str]:
        with (root / relative).open(newline="", encoding="utf-8") as handle:
            return {row[column] for row in csv.DictReader(handle, strict=True)}

    design_inputs = load_json(root / "hardware/ctl01/design-inputs.json")
    design_ids = {item["id"] for item in design_inputs["parameters"]}
    interface_text = (root / "hardware/ctl01/interface-control.md").read_text(encoding="utf-8")
    interface_ids = set(re.findall(r"\|\s*(IF-[A-Z]+-\d{3})\s*\|", interface_text))
    available = (
        csv_ids("hardware/ctl01/mechanical/load-case-register.csv", "load_case_id")
        | design_ids
        | csv_ids("hardware/ctl01/safety/safety-requirements.csv", "requirement_id")
        | csv_ids("hardware/ctl01/safety/hazard-register.csv", "hazard_id")
        | interface_ids
    )
    missing = set(model.trace_ids) - available
    if missing:
        raise ConfigError(f"analysis trace IDs missing from source registers: {', '.join(sorted(missing))}")
    with (root / "hardware/ctl01/mechanical/load-case-register.csv").open(newline="", encoding="utf-8") as handle:
        load_cases = {row["load_case_id"]: row for row in csv.DictReader(handle, strict=True)}
    lc001 = load_cases["LC-001"]
    if model.analysis_id not in lc001["evidence_reference"] or "partial unreviewed" not in lc001["evidence_reference"]:
        raise ConfigError("LC-001 must reference AN-LC-001A only as partial unreviewed analysis")
    if lc001["status"] != "TBD":
        raise ConfigError("LC-001 overall status must remain TBD")


def validate_bunker_cad_geometry(root: Path, model: BunkerPlanInput) -> None:
    """Source-only check: the example SI geometry must equal canonical CAD mm values."""
    cad_path = root / "projects/bunker01/cad/parameters.scad"
    text = cad_path.read_text(encoding="utf-8")
    assignments = {
        match.group(1): float(match.group(2))
        for match in re.finditer(r"(?m)^([a-z][a-z0-9_]*)\s*=\s*([0-9]+(?:\.[0-9]+)?)\s*;", text)
    }
    fields = {
        "internal_length": "internal_length_m",
        "internal_width": "internal_width_m",
        "internal_height": "internal_height_m",
        "wall_thickness": "wall_thickness_m",
        "floor_thickness": "floor_thickness_m",
        "roof_thickness": "roof_thickness_m",
        "working_space": "working_space_m",
        "drainage_layer": "drainage_layer_m",
        "roof_cover": "roof_cover_m",
    }
    for cad_name, attribute in fields.items():
        if cad_name not in assignments:
            raise ConfigError(f"CAD parameter {cad_name} is missing")
        cad_m = assignments[cad_name] / 1000.0
        example_m = getattr(model.geometry, attribute)
        if not math.isclose(cad_m, example_m, rel_tol=0.0, abs_tol=1e-12):
            raise ConfigError(f"bunker example {attribute}={example_m} does not match CAD {cad_name}={cad_m} m")


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
            # BUNKER-01 gate/handover records require future owner approval; they do
            # not attribute the current synthetic assumptions to the owner.
            required_future_approval = (
                match.group(0).lower() == "owner-approved"
                and ("UNRESOLVED" in line.upper() or "requirements and legal basis" in line.lower())
            )
            if not required_future_approval and not _NEGATION.search(line[:match.start()]):
                return True
    return False


def _provenance_files(root: Path) -> list[Path]:
    files = [root / name for name in ("AGENTS.md", "CHANGELOG.md", "LICENSE", "NOTICE.md", "README.md")]
    for directory in ("configs", "docs", "examples", "hardware", "maintenance", "manufacturing", "projects"):
        base = root / directory
        if base.is_dir():
            files.extend(path for path in base.rglob("*")
                         if path.is_file() and path.suffix.lower() in {".csv", ".json", ".md", ".scad"})
    return sorted(path for path in files if path.is_file())


def _validate_cad_scene_in_memory(scene: Any) -> tuple[str, ...]:
    """Generate every CAD representation without creating output or importing tools."""

    for body in scene.bodies:
        mesh_box(body)
    obj, mtl = export_wavefront(scene)
    blender = generate_blender_python(scene)
    mjcf = generate_mujoco_mjcf(scene)
    openscad = generate_openscad(scene)
    freecad = generate_freecad_python(scene)
    if "mtllib scene.mtl\n" not in obj:
        raise ConfigError("generated OBJ must reference scene.mtl")
    ET.fromstring(mjcf)
    compile(blender, "blender_scene.py", "exec")
    compile(freecad, "scene_freecad.py", "exec")
    for opening, closing in (("{", "}"), ("(", ")"), ("[", "]")):
        if openscad.count(opening) != openscad.count(closing):
            raise ConfigError("generated OpenSCAD delimiters are unbalanced")
    return obj, mtl, blender, mjcf, openscad, freecad


def _validate_new_schema_envelopes(root: Path) -> None:
    pairs = (
        ("physics-input.schema.json", "examples/physics/synthetic-physics.json"),
        ("cad-scene.schema.json", "examples/cad/synthetic-scene.json"),
        ("powertrain-input.schema.json", "examples/powertrain/synthetic-microgrid.json"),
        ("economics-input.schema.json", "examples/economics/synthetic-pathways.json"),
    )
    for schema_name, example_name in pairs:
        schema = load_json(root / "schemas" / schema_name)
        example = load_json(root / example_name)
        if schema.get("additionalProperties") is not False:
            raise ConfigError(f"{schema_name} must reject additional properties")
        if set(schema.get("required", ())) != set(example) or set(schema.get("properties", ())) != set(example):
            raise ConfigError(f"{schema_name} top-level envelope does not match {example_name}")
    schema = load_json(root / "schemas/geohazard-rural.schema.json")
    if schema.get("additionalProperties") is not False:
        raise ConfigError("geohazard-rural.schema.json must reject additional properties")
    for example_name in ("examples/geohazard/synthetic-screen.json", "examples/geohazard/synthetic-adapt.json"):
        example = load_json(root / example_name)
        if not set(example).issubset(schema.get("properties", {})) or not set(schema.get("required", ())).issubset(example):
            raise ConfigError(f"geohazard-rural.schema.json top-level envelope does not match {example_name}")


def _validate_tracked_openscad(root: Path) -> None:
    sources = sorted((root / "hardware/ctl01/cad").glob("*.scad")) + sorted(
        (root / "projects/bunker01/cad").glob("*.scad")
    )
    if len(sources) != 4:
        raise ConfigError(f"expected four tracked OpenSCAD sources, found {len(sources)}")
    for source in sources:
        text = source.read_text(encoding="utf-8")
        for opening, closing in (("{", "}"), ("(", ")"), ("[", "]")):
            if text.count(opening) != text.count(closing):
                raise ConfigError(f"unbalanced OpenSCAD delimiters: {source.relative_to(root)}")


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
    analysis_model = None
    try:
        analysis_model = load_analysis_input(root / "examples/analysis/synthetic-lc001.json")
    except (ConfigError, OSError) as exc:
        errors.append(f"analysis input: {exc}")
    if full_repository and analysis_model is not None:
        try:
            validate_analysis_source_traces(root, analysis_model)
        except (ConfigError, OSError, csv.Error, KeyError) as exc:
            errors.append(f"analysis source traces: {exc}")
    bunker_model = None
    bunker_registers = None
    try:
        bunker_model = load_bunker_input(root / "examples/bunker/synthetic-bunker01.json")
        bunker_registers = load_bunker_registers(
            root / "projects/bunker01/construction/work-breakdown.csv",
            root / "projects/bunker01/construction/quality-gates.csv",
            root / "projects/bunker01/construction/fleet-register.csv",
        )
        bunker_site = load_bunker_site(root / "projects/bunker01/site-inputs.json")
        bunker_result = plan_bunker(bunker_model, bunker_registers, bunker_site)
        if (bunker_result["siteKnown"] or bunker_result["constructionAuthorized"]
                or bunker_result["physicalValidationPerformed"] or bunker_result["unresolvedGateIds"] != [
                    f"BG-{number:03d}" for number in range(1, 16)
                ]):
            raise ConfigError("BUNKER-01 unresolved-gate/no-authorization invariant failed")
        construction_energy_json(bunker_result["constructionEnergy"])
        if full_repository:
            schema = load_json(root / "schemas/bunker-construction-energy.schema.json")
            export = bunker_result["constructionEnergy"]
            if (schema.get("additionalProperties") is not False
                    or set(schema.get("required", ())) != set(export)
                    or set(schema.get("properties", ())) != set(export)):
                raise ConfigError("BUNKER-01 construction-energy schema does not match the strict export envelope")
    except (ConfigError, OSError, ValueError, csv.Error, KeyError) as exc:
        errors.append(f"BUNKER-01 planning inputs/references: {exc}")
    if full_repository and bunker_model is not None:
        try:
            validate_bunker_cad_geometry(root, bunker_model)
        except (ConfigError, OSError, ValueError) as exc:
            errors.append(f"BUNKER-01 CAD geometry: {exc}")
    physics_inputs_checked = 0
    try:
        physics_result = evaluate_physics(load_physics_input(root / "examples/physics/synthetic-physics.json"))
        physics_result_json(physics_result)
        if (physics_result.physical_validation_performed or physics_result.construction_authorized
                or physics_result.operational_release or not physics_result.unresolved_human_gate_ids):
            raise ConfigError("physics unresolved-gate/no-authorization invariant failed")
        physics_inputs_checked = 1
    except (ConfigError, OSError, ValueError, OverflowError) as exc:
        errors.append(f"physics input/evaluator: {exc}")
    cad_scenes_checked = 0
    try:
        cad_scene = load_cad_scene(root / "examples/cad/synthetic-scene.json")
        generated = _validate_cad_scene_in_memory(cad_scene)
        if full_repository and generated != _validate_cad_scene_in_memory(cad_scene):
            raise ConfigError("in-memory CAD generation is not deterministic")
        cad_scenes_checked = 1
    except (ConfigError, OSError, ValueError, OverflowError, ET.ParseError, SyntaxError) as exc:
        errors.append(f"CAD scene/generators: {exc}")
    powertrain_inputs_checked = 0
    try:
        powertrain_result = compare_powertrains(load_powertrain_input(root / "examples/powertrain/synthetic-microgrid.json"))
        powertrain_result_json(powertrain_result)
        if (powertrain_result.physical_validation_performed or powertrain_result.operational_release
                or not powertrain_result.unresolved_human_gate_ids):
            raise ConfigError("powertrain unresolved-gate/no-authorization invariant failed")
        powertrain_inputs_checked = 1
    except (ConfigError, OSError, ValueError, OverflowError) as exc:
        errors.append(f"powertrain input/evaluator: {exc}")
    geohazard_screen_inputs_checked = 0
    try:
        screen_document = load_geohazard_document(root / "examples/geohazard/synthetic-screen.json")
        screen_model = parse_geohazard_input(screen_document)
        screen_result = screen_candidate_parcels(screen_model)
        screen_json = geohazard_result_json(screen_result)
        if (screen_result.purchase_recommendation_made or screen_result.location_data_retained
                or screen_result.physical_validation_performed or "verticesLocal" in screen_json
                or any(gate.status != "UNRESOLVED" for gate in screen_result.human_gates)):
            raise ConfigError("geohazard screen privacy/unresolved-gate invariant failed")
        geohazard_screen_inputs_checked = 1
    except (ConfigError, OSError, ValueError, OverflowError) as exc:
        errors.append(f"geohazard screen input/evaluator: {exc}")
    geohazard_adapt_inputs_checked = 0
    try:
        adapt_document = load_geohazard_document(root / "examples/geohazard/synthetic-adapt.json")
        adapt_model = parse_geohazard_input(adapt_document)
        adapt_result = adapt_to_existing_site(adapt_model)
        adapt_json = geohazard_result_json(adapt_result)
        if (adapt_result.construction_authorized or adapt_result.site_engineering_complete
                or adapt_result.location_data_retained or adapt_result.physical_validation_performed
                or "verticesLocal" in adapt_json or any(gate.status != "UNRESOLVED" for gate in adapt_result.human_gates)):
            raise ConfigError("geohazard adapt privacy/unresolved-gate invariant failed")
        geohazard_adapt_inputs_checked = 1
    except (ConfigError, OSError, ValueError, OverflowError) as exc:
        errors.append(f"geohazard adapt input/evaluator: {exc}")
    economics_inputs_checked = 0
    try:
        economics_result = compare_pathways(load_economics_input(root / "examples/economics/synthetic-pathways.json"))
        economics_result_json(economics_result)
        if (economics_result.quotes_obtained or economics_result.procurement_authorized
                or economics_result.physical_validation_performed):
            raise ConfigError("economics quote/procurement/no-authorization invariant failed")
        economics_inputs_checked = 1
    except (ConfigError, OSError, ValueError, OverflowError) as exc:
        errors.append(f"economics input/evaluator: {exc}")
    if full_repository:
        try:
            _validate_new_schema_envelopes(root)
            _validate_tracked_openscad(root)
        except (ConfigError, OSError, ValueError, OverflowError) as exc:
            errors.append(f"new schemas/examples/tracked OpenSCAD: {exc}")
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
        "analysisInputsChecked": 1 if analysis_model is not None else 0,
        "physicsInputsChecked": physics_inputs_checked,
        "cadScenesChecked": cad_scenes_checked,
        "powertrainInputsChecked": powertrain_inputs_checked,
        "geohazardScreenInputsChecked": geohazard_screen_inputs_checked,
        "geohazardAdaptInputsChecked": geohazard_adapt_inputs_checked,
        "economicsInputsChecked": economics_inputs_checked,
        "analysisTraceIdsChecked": len(analysis_model.trace_ids) if analysis_model is not None else 0,
        "bunkerInputsChecked": 1 if bunker_model is not None else 0,
        "bunkerWorkPackagesChecked": len(bunker_registers.packages) if bunker_registers is not None else 0,
        "bunkerGatesChecked": len(bunker_registers.gates) if bunker_registers is not None else 0,
        "bunkerFleetEntriesChecked": len(bunker_registers.fleet) if bunker_registers is not None else 0,
        "bunkerCadGeometryChecked": bool(full_repository and bunker_model is not None),
        "errors": errors,
        "physicalValidationPerformed": False,
    }
