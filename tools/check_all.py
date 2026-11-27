# SPDX-License-Identifier: Apache-2.0
"""Single offline verification entry point for a clean checkout."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(command), flush=True)
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(filter(None, (str(ROOT / "src"), env.get("PYTHONPATH"))))
    return subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=capture, check=False)


def require(result: subprocess.CompletedProcess[str], label: str) -> str:
    if result.returncode != 0:
        if result.stdout:
            print(result.stdout, file=sys.stderr)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        raise RuntimeError(f"{label} failed with exit {result.returncode}")
    return result.stdout


def static_openscad_check() -> str:
    sources = sorted((ROOT / "hardware/ctl01/cad").glob("*.scad")) + sorted((ROOT / "projects/bunker01/cad").glob("*.scad"))
    for source in sources:
        text = source.read_text(encoding="utf-8")
        for opening, closing in (("{", "}"), ("(", ")"), ("[", "]")):
            if text.count(opening) != text.count(closing):
                raise RuntimeError(f"static OpenSCAD delimiter check failed: {source}")
    if shutil.which("openscad") is None:
        return f"OpenSCAD unavailable; {len(sources)} sources passed static delimiter checks; rendering not run (optional)."
    return f"OpenSCAD is installed but rendering is not required by the offline gate; {len(sources)} sources passed static delimiter checks."


def run_twice_and_compare(
    command: list[str], artifact_names: tuple[str, ...], label: str
) -> tuple[bytes, ...]:
    """Run one JSON command in isolated directories and compare every artifact."""

    runs: list[tuple[bytes, ...]] = []
    for suffix in ("a", "b"):
        directory = ROOT / "builds/check" / f"{label}-{suffix}"
        expanded = [part.replace("{output}", str(directory)) for part in command]
        stdout = require(run(expanded, capture=True), f"{label} {suffix}")
        result_path = directory / "result.json"
        if not result_path.is_file() or result_path.read_bytes() != stdout.encode("utf-8"):
            raise RuntimeError(f"{label} {suffix} result.json does not match JSON stdout")
        payloads = tuple((directory / name).read_bytes() for name in artifact_names)
        runs.append(payloads)
    if runs[0] != runs[1]:
        raise RuntimeError(f"deterministic {label} outputs differ")
    print(f"Deterministic {label}: {', '.join(artifact_names)} byte-identical")
    return runs[0]


def run_json_twice(command: list[str], label: str) -> str:
    """Run a stdout-only JSON command twice and compare exact encoded bytes."""
    outputs = []
    for suffix in ("a", "b"):
        stdout = require(run(command, capture=True), f"{label} {suffix}")
        json.loads(stdout)
        outputs.append(stdout.encode("utf-8"))
    if outputs[0] != outputs[1]:
        raise RuntimeError(f"deterministic {label} stdout JSON differs")
    print(f"Deterministic {label} stdout JSON: byte-identical")
    return outputs[0].decode("utf-8")


def validate_generated_cad_sources(scene, output_dir: Path | None = None) -> None:
    """Check pure/emitted CAD text without importing or executing external tools."""

    from open_construction_equipment.cad_blender import (
        export_wavefront,
        generate_blender_python,
        generate_freecad_python,
        generate_mujoco_mjcf,
        generate_openscad,
    )

    obj, mtl = export_wavefront(scene)
    generated = {
        "scene.obj": obj,
        "scene.mtl": mtl,
        "blender_scene.py": generate_blender_python(scene),
        "ctl01_bunker_physics.xml": generate_mujoco_mjcf(scene),
        "scene.scad": generate_openscad(scene),
        "scene_freecad.py": generate_freecad_python(scene),
    }
    if output_dir is not None:
        for name, expected in generated.items():
            if (output_dir / name).read_text(encoding="utf-8") != expected:
                raise RuntimeError(f"emitted CAD content differs from pure generator: {name}")
    if "mtllib scene.mtl\n" not in generated["scene.obj"]:
        raise RuntimeError("generated OBJ lacks mtllib scene.mtl")
    ET.fromstring(generated["ctl01_bunker_physics.xml"])
    compile(generated["blender_scene.py"], "blender_scene.py", "exec")
    compile(generated["scene_freecad.py"], "scene_freecad.py", "exec")
    openscad = generated["scene.scad"]
    for opening, closing in (("{", "}"), ("(", ")"), ("[", "]")):
        if openscad.count(opening) != openscad.count(closing):
            raise RuntimeError("generated scene.scad has unbalanced delimiters")


def main() -> int:
    require(run([sys.executable, "-m", "compileall", "-q", "src", "tests", "tools", "firmware/ctl01"]), "Python compile")
    require(run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]), "Python tests")
    validation = run_json_twice(
        [sys.executable, "-m", "open_construction_equipment", "validate", "--json"], "validate",
    )
    print(json.dumps(json.loads(validation), indent=2, sort_keys=True))
    for command_name in ("maintenance", "bom"):
        run_json_twice(
            [sys.executable, "-m", "open_construction_equipment", command_name, "--json"], command_name,
        )
    outputs = []
    for name in ("demo-a", "demo-b"):
        directory = ROOT / "builds/check" / name
        result = require(run([sys.executable, "-m", "open_construction_equipment", "simulate", "--output-dir", str(directory), "--json"], capture=True), f"demo {name}")
        report = json.loads(result)
        if report["status"] != "succeeded":
            raise RuntimeError(f"demo {name} did not succeed: {report['finalReasons']}")
        outputs.append(((directory / "result.json").read_bytes(), (directory / "trajectory.svg").read_bytes()))
        print(f"Demo {name}: {report['status']}; {report['metrics']['duration_s']:.1f} s; goal error {report['metrics']['finalGoalError_m']:.3f} m")
    if outputs[0] != outputs[1]:
        raise RuntimeError("deterministic demo outputs differ")
    print("Deterministic demo JSON and SVG: byte-identical")
    analysis_outputs = []
    for name in ("analysis-a", "analysis-b"):
        directory = ROOT / "builds/check" / name
        result = require(run([sys.executable, "-m", "open_construction_equipment", "analyze",
                              "--output-dir", str(directory), "--json"], capture=True), f"analysis {name}")
        report = json.loads(result)
        if (report["analysisId"] != "AN-LC-001A" or report["acceptanceStatus"] != "NOT_ASSESSED"
                or report["reviewStatus"] != "UNREVIEWED" or report["physicalValidationPerformed"]):
            raise RuntimeError(f"analysis {name} has an invalid identity/status")
        analysis_outputs.append((directory / "result.json").read_bytes())
    if analysis_outputs[0] != analysis_outputs[1]:
        raise RuntimeError("deterministic analysis outputs differ")
    print("Deterministic AN-LC-001A result JSON: byte-identical; UNREVIEWED; acceptance NOT_ASSESSED")
    bunker_outputs = []
    for name in ("bunker-a", "bunker-b"):
        directory = ROOT / "builds/check" / name
        result = require(run([sys.executable, "-m", "open_construction_equipment", "bunker",
                              "--output-dir", str(directory), "--json"], capture=True), f"bunker {name}")
        report = json.loads(result)
        if (report["projectId"] != "BUNKER-01" or report["constructionAuthorized"]
                or report["physicalValidationPerformed"]
                or report["readinessStatus"] != "BLOCKED_UNRESOLVED_HUMAN_GATES"
                or len(report["unresolvedGateIds"]) != 15):
            raise RuntimeError(f"bunker {name} has an invalid identity/status")
        energy_path = directory / "construction-energy.json"
        if not energy_path.is_file():
            raise RuntimeError(f"bunker {name} did not write construction-energy.json")
        energy_report = json.loads(energy_path.read_text(encoding="utf-8"))
        unknown_packages = [row for row in energy_report["workPackages"] if row["estimateStatus"] == "UNKNOWN"]
        unknown_fleet = [row for row in energy_report["fleet"] if row["estimateStatus"] == "UNKNOWN"]
        if (energy_report != report["constructionEnergy"]
                or energy_report["modeledOnlySubtotal_kWh"] != 246
                or len(energy_report["assumptions"]) != 8 or len(unknown_packages) != 14
                or len(unknown_fleet) != 1 or unknown_fleet[0]["fleetId"] != "BF-006"
                or any(row["electricEnergy_kWh"] is not None for row in unknown_packages + unknown_fleet)
                or energy_report["habitatDailyOperatingDemandIncluded"]):
            raise RuntimeError(f"bunker {name} has invalid construction-energy coverage or scope")
        bunker_outputs.append((
            (directory / "result.json").read_bytes(), (directory / "schedule.svg").read_bytes(),
            energy_path.read_bytes(),
        ))
    if bunker_outputs[0] != bunker_outputs[1]:
        raise RuntimeError("deterministic bunker JSON, SVG or construction-energy outputs differ")
    print("Deterministic BUNKER-01 result JSON, schedule SVG and construction-energy JSON: byte-identical; "
          "246 kWh modeled subtotal; 14 package and one fleet unknowns; construction BLOCKED")
    physics_payloads = run_twice_and_compare(
        [sys.executable, "-m", "open_construction_equipment", "physics", "--output-dir", "{output}", "--json"],
        ("result.json",), "physics",
    )
    physics = json.loads(physics_payloads[0])
    if (physics["status"] != "SIMULATED_UNREVIEWED" or physics["physicalValidationPerformed"]
            or physics["constructionAuthorized"] or physics["operationalRelease"]
            or not physics["unresolvedHumanGateIds"]):
        raise RuntimeError("physics result has invalid simulated/unresolved status")
    cad_names = (
        "scene.obj", "scene.mtl", "blender_scene.py", "ctl01_bunker_physics.xml",
        "scene.scad", "scene_freecad.py", "result.json",
    )
    cad_payloads = run_twice_and_compare(
        [sys.executable, "-m", "open_construction_equipment", "export-cad", "--output-dir", "{output}", "--json"],
        cad_names, "export-cad",
    )
    cad_manifest = json.loads(cad_payloads[-1])
    if (cad_manifest["status"] != "SIMULATED_UNREVIEWED" or cad_manifest["physicalValidationPerformed"]
            or cad_manifest["fabricationRelease"] or cad_manifest["externalToolExecutionPerformed"]):
        raise RuntimeError("CAD manifest has invalid simulated/unreleased status")
    cad_dir = ROOT / "builds/check/export-cad-a"
    for index, artifact in enumerate(cad_manifest["artifacts"]):
        payload = cad_payloads[index]
        if (artifact["filename"] != cad_names[index] or artifact["sizeBytes"] != len(payload)
                or artifact["sha256"] != hashlib.sha256(payload).hexdigest()):
            raise RuntimeError(f"CAD manifest hash/size mismatch: {artifact['filename']}")
    from open_construction_equipment.cad_blender import external_tool_report, load_cad_scene
    validate_generated_cad_sources(load_cad_scene(ROOT / "examples/cad/synthetic-scene.json"), cad_dir)
    powertrain_payloads = run_twice_and_compare(
        [sys.executable, "-m", "open_construction_equipment", "powertrain", "--output-dir", "{output}", "--json"],
        ("result.json",), "powertrain",
    )
    powertrain = json.loads(powertrain_payloads[0])
    if (powertrain["status"] != "SIMULATED_UNREVIEWED" or powertrain["physicalValidationPerformed"]
            or powertrain["operationalRelease"] or not powertrain["unresolvedHumanGateIds"]):
        raise RuntimeError("powertrain result has invalid simulated/unresolved status")
    for task in powertrain["taskResults"]:
        if abs(task["servedEnergy_kWh"] + task["unservedEnergy_kWh"] - task["requiredElectricalEnergy_kWh"]) > 1e-9:
            raise RuntimeError(f"powertrain energy closure failed: {task['taskId']} {task['path']}")
    for mode in ("screen", "adapt"):
        payloads = run_twice_and_compare(
            [sys.executable, "-m", "open_construction_equipment", "site", "--mode", mode,
             "--output-dir", "{output}", "--json"],
            ("result.json",), f"geohazard-{mode}",
        )
        report_text = payloads[0].decode("utf-8")
        report = json.loads(report_text)
        if (report["mode"] != mode or report["locationDataRetained"] or report["physicalValidationPerformed"]
                or "verticesLocal" in report_text or any(gate["status"] != "UNRESOLVED" for gate in report["humanGates"])):
            raise RuntimeError(f"site {mode} privacy/unresolved-gate invariant failed")
        if mode == "screen" and report["purchaseRecommendationMade"]:
            raise RuntimeError("site screen made a purchase recommendation")
        if mode == "adapt" and (report["constructionAuthorized"] or report["siteEngineeringComplete"]):
            raise RuntimeError("site adapt made an authorization/completion claim")
    economics_payloads = run_twice_and_compare(
        [sys.executable, "-m", "open_construction_equipment", "economics", "--output-dir", "{output}", "--json"],
        ("result.json",), "economics",
    )
    economics = json.loads(economics_payloads[0])
    if (economics["status"] != "SIMULATED_UNREVIEWED" or economics["quotesObtained"]
            or economics["procurementAuthorized"] or economics["physicalValidationPerformed"]):
        raise RuntimeError("economics result has invalid unquoted/unauthorized status")
    for cost in economics["pathwayCosts"]:
        line_total = sum(line["fixedCost"] + line["variableCostPer_h"] * cost["operatingHours"] for line in cost["lines"])
        if abs(line_total - cost["totalCost"]) > 1e-6:
            raise RuntimeError(f"economics line-item closure failed: {cost['pathway']} {cost['operatingHours']}")
    print("Generated CAD XML/Python/OpenSCAD checks passed; external tools not executed:", json.dumps(external_tool_report(), sort_keys=True))
    require(run([sys.executable, "firmware/ctl01/run_host_tests.py"]), "firmware host tests")
    require(run([sys.executable, "tools/wheel_smoke.py"]), "offline wheel smoke")
    print(static_openscad_check())
    print("ALL CHECKS PASSED — SIMULATION ONLY; no physical validation performed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError) as exc:
        print(f"CHECK FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
