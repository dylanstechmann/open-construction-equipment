# SPDX-License-Identifier: Apache-2.0
"""Build/install a non-editable wheel offline and test its installed CLI."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import venv
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def _run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> str:
    print("+", " ".join(map(str, command)), flush=True)
    result = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False)
    if result.returncode:
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        raise RuntimeError(f"command failed with exit {result.returncode}: {command[0]}")
    return result.stdout


def _build_tools() -> str | None:
    try:
        importlib.metadata.version("pip")
        version = importlib.metadata.version("setuptools")
    except importlib.metadata.PackageNotFoundError:
        return None
    try:
        parts = tuple(int(part) for part in version.split(".")[:2])
    except ValueError:
        parts = (0, 0)
    if parts < (77, 0):
        return None
    return version


def check_installed_new_commands(run_dir: Path, oce: Path, env: dict[str, str]) -> None:
    """Exercise all five v0.5.0 commands, including both site modes."""

    commands = (
        (("physics",), "builds/physics/result.json"),
        (("export-cad",), "builds/cad/result.json"),
        (("powertrain",), "builds/powertrain/result.json"),
        (("site", "--mode", "screen"), "builds/geohazard/screen/result.json"),
        (("site", "--mode", "adapt"), "builds/geohazard/adapt/result.json"),
        (("economics",), "builds/economics/result.json"),
    )
    reports = {}
    for arguments, relative_result in commands:
        report_text = _run([str(oce), *arguments, "--json"], cwd=run_dir, env=env)
        result_path = run_dir / relative_result
        if not result_path.is_file() or result_path.read_text(encoding="utf-8") != report_text:
            raise RuntimeError(f"installed {arguments[0]} result.json does not match stdout")
        reports[arguments] = json.loads(report_text)
    cad = reports[("export-cad",)]
    cad_dir = run_dir / "builds/cad"
    expected = (
        "scene.obj", "scene.mtl", "blender_scene.py", "ctl01_bunker_physics.xml",
        "scene.scad", "scene_freecad.py",
    )
    if tuple(artifact["filename"] for artifact in cad["artifacts"]) != expected:
        raise RuntimeError("installed CAD manifest has wrong artifact names/order")
    for artifact in cad["artifacts"]:
        payload = (cad_dir / artifact["filename"]).read_bytes()
        if len(payload) != artifact["sizeBytes"] or hashlib.sha256(payload).hexdigest() != artifact["sha256"]:
            raise RuntimeError(f"installed CAD artifact hash/size mismatch: {artifact['filename']}")
    if "mtllib scene.mtl\n" not in (cad_dir / "scene.obj").read_text(encoding="utf-8"):
        raise RuntimeError("installed CAD OBJ lacks its scene.mtl reference")
    screen = reports[("site", "--mode", "screen")]
    adapt = reports[("site", "--mode", "adapt")]
    if screen["purchaseRecommendationMade"] or adapt["constructionAuthorized"]:
        raise RuntimeError("installed site commands made a prohibited decision")
    if reports[("economics",)]["procurementAuthorized"] or reports[("powertrain",)]["operationalRelease"]:
        raise RuntimeError("installed economics/powertrain made a prohibited release")
    print("Installed v0.5.0 commands: physics, export-cad, powertrain, site screen/adapt, economics passed")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-build-tools", action="store_true",
                        help="fail instead of reporting a skip when setuptools >=77 is unavailable")
    args = parser.parse_args(argv)
    setuptools_version = _build_tools()
    if setuptools_version is None:
        message = "WHEEL SMOKE SKIPPED: preinstalled pip and setuptools >=77 required for offline PEP 517 build"
        if args.require_build_tools:
            print(f"ERROR: {message}", file=sys.stderr)
            return 2
        print(message)
        return 0
    print(f"Offline build backend: setuptools {setuptools_version}; no dependency downloads")
    env = os.environ.copy()
    env["PIP_NO_INDEX"] = "1"
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    env["PYTHONNOUSERSITE"] = "1"
    with tempfile.TemporaryDirectory(prefix="oce-wheel-smoke-") as directory:
        work = Path(directory)
        source = work / "source"
        ignore = shutil.ignore_patterns(".git", ".venv", "venv", "builds", "__pycache__", "*.egg-info")
        shutil.copytree(ROOT, source, ignore=ignore)
        (work / "build").mkdir()
        (work / "dist").mkdir()
        _run([sys.executable, "-m", "pip", "wheel", "--no-index", "--no-deps", "--no-build-isolation",
              "--wheel-dir", str(work / "dist"), str(source)], cwd=work / "build", env=env)
        wheels = list((work / "dist").glob("*.whl"))
        if len(wheels) != 1:
            raise RuntimeError(f"expected one wheel, found {len(wheels)}")
        wheel = wheels[0]
        with zipfile.ZipFile(wheel) as archive:
            names = set(archive.namelist())
            license_dirs = {name.split(".dist-info/licenses/")[0] + ".dist-info/licenses"
                            for name in names if ".dist-info/licenses/" in name}
            if len(license_dirs) != 1:
                raise RuntimeError("wheel lacks one conventional dist-info/licenses directory")
            license_dir = license_dirs.pop()
            for relative in ("LICENSE", "NOTICE.md", "LICENSES/Apache-2.0.txt",
                             "LICENSES/CERN-OHL-S-2.0.txt", "LICENSES/CC-BY-SA-4.0.txt"):
                member = f"{license_dir}/{relative}"
                if member not in names or archive.read(member) != (ROOT / relative).read_bytes():
                    raise RuntimeError(f"wheel license payload missing or stale: {relative}")
            if not any(name.endswith(".data/data/share/open-construction-equipment/configs/ctl01.simulation.json")
                       for name in names):
                raise RuntimeError("wheel lacks installed shared simulation data")
            if not any(name.endswith(".data/data/share/open-construction-equipment/examples/analysis/synthetic-lc001.json")
                       for name in names):
                raise RuntimeError("wheel lacks installed synthetic analysis input")
            required_bunker_data = (
                "examples/bunker/synthetic-bunker01.json",
                "projects/bunker01/construction/work-breakdown.csv",
                "projects/bunker01/construction/quality-gates.csv",
                "projects/bunker01/construction/fleet-register.csv",
                "projects/bunker01/site-inputs.json",
            )
            for relative in required_bunker_data:
                suffix = f".data/data/share/open-construction-equipment/{relative}"
                if not any(name.endswith(suffix) for name in names):
                    raise RuntimeError(f"wheel lacks installed BUNKER-01 resource: {relative}")
            required_v050_data = (
                "examples/physics/synthetic-physics.json",
                "examples/cad/synthetic-scene.json",
                "examples/powertrain/synthetic-microgrid.json",
                "examples/geohazard/synthetic-screen.json",
                "examples/geohazard/synthetic-adapt.json",
                "examples/economics/synthetic-pathways.json",
            )
            for relative in required_v050_data:
                suffix = f".data/data/share/open-construction-equipment/{relative}"
                if not any(name.endswith(suffix) for name in names):
                    raise RuntimeError(f"wheel lacks installed v0.5.0 resource: {relative}")
        target = work / "venv"
        venv.EnvBuilder(with_pip=False, clear=True, symlinks=True).create(target)
        python = target / "bin/python"
        oce = target / "bin/oce"
        # Use the already-available outer pip; ensurepip is not a build dependency.
        _run([sys.executable, "-m", "pip", "--python", str(python),
              "install", "--no-index", "--no-deps", str(wheel)], cwd=work, env=env)
        run_dir = work / "clean-run"
        run_dir.mkdir()
        installed_env = env.copy()
        installed_env.pop("PYTHONPATH", None)
        validation = json.loads(_run([str(oce), "validate", "--json"], cwd=run_dir, env=installed_env))
        if validation["status"] != "passed" or validation["validationScope"] != "package-resources" or validation["fullRepositoryValidation"]:
            raise RuntimeError(f"installed package validation has wrong result/scope: {validation}")
        new_counters = (
            "physicsInputsChecked", "cadScenesChecked", "powertrainInputsChecked",
            "geohazardScreenInputsChecked", "geohazardAdaptInputsChecked", "economicsInputsChecked",
        )
        if any(validation.get(counter) != 1 for counter in new_counters):
            raise RuntimeError(f"installed package validation did not check every v0.5.0 input: {validation}")
        simulation = json.loads(_run([str(oce), "simulate", "--json"], cwd=run_dir, env=installed_env))
        if simulation["status"] != "succeeded":
            raise RuntimeError(f"installed default simulation failed: {simulation['finalReasons']}")
        if not (run_dir / "builds/demo/result.json").is_file() or not (run_dir / "builds/demo/trajectory.svg").is_file():
            raise RuntimeError("installed simulation did not write default reports in the clean working directory")
        analysis = json.loads(_run([str(oce), "analyze", "--json"], cwd=run_dir, env=installed_env))
        if (analysis["analysisId"] != "AN-LC-001A" or analysis["acceptanceStatus"] != "NOT_ASSESSED"
                or analysis["reviewStatus"] != "UNREVIEWED" or analysis["physicalValidationPerformed"]):
            raise RuntimeError(f"installed analysis has wrong identity/status: {analysis}")
        analysis_path = run_dir / "builds/analysis/lc001/result.json"
        if not analysis_path.is_file() or json.loads(analysis_path.read_text(encoding="utf-8")) != analysis:
            raise RuntimeError("installed analysis did not write matching default deterministic output")
        bunker = json.loads(_run([str(oce), "bunker", "--json"], cwd=run_dir, env=installed_env))
        if (bunker["projectId"] != "BUNKER-01" or bunker["constructionAuthorized"]
                or bunker["physicalValidationPerformed"]
                or bunker["readinessStatus"] != "BLOCKED_UNRESOLVED_HUMAN_GATES"
                or len(bunker["unresolvedGateIds"]) != 15):
            raise RuntimeError(f"installed bunker plan has wrong identity/status: {bunker}")
        bunker_json = run_dir / "builds/bunker01/result.json"
        bunker_svg = run_dir / "builds/bunker01/schedule.svg"
        if not bunker_json.is_file() or json.loads(bunker_json.read_text(encoding="utf-8")) != bunker:
            raise RuntimeError("installed bunker planner did not write matching deterministic JSON")
        if not bunker_svg.is_file() or "SYNTHETIC PLAN — CONSTRUCTION BLOCKED" not in bunker_svg.read_text(encoding="utf-8"):
            raise RuntimeError("installed bunker planner did not write blocked schedule SVG")
        bunker_energy_path = run_dir / "builds/bunker01/construction-energy.json"
        if not bunker_energy_path.is_file():
            raise RuntimeError("installed bunker planner did not write construction-energy JSON")
        bunker_energy = json.loads(bunker_energy_path.read_text(encoding="utf-8"))
        unknown_packages = [row for row in bunker_energy["workPackages"] if row["estimateStatus"] == "UNKNOWN"]
        unknown_fleet = [row for row in bunker_energy["fleet"] if row["estimateStatus"] == "UNKNOWN"]
        if (bunker_energy != bunker["constructionEnergy"] or bunker_energy["modeledOnlySubtotal_kWh"] != 246
                or len(unknown_packages) != 14 or len(unknown_fleet) != 1
                or any(row["electricEnergy_kWh"] is not None for row in unknown_packages + unknown_fleet)
                or bunker_energy["habitatDailyOperatingDemandIncluded"]):
            raise RuntimeError("installed bunker construction-energy export has invalid coverage or scope")
        maintenance = json.loads(_run([str(oce), "maintenance", "--json"], cwd=run_dir, env=installed_env))
        if maintenance["summary"]["total"] != 20:
            raise RuntimeError("installed maintenance data is incomplete")
        bom = json.loads(_run([str(oce), "bom", "--json"], cwd=run_dir, env=installed_env))
        if bom["itemCount"] != 63:
            raise RuntimeError("installed BOM data is incomplete")
        check_installed_new_commands(run_dir, oce, installed_env)
        _run([str(python), "-c",
              "import importlib.util; assert all(importlib.util.find_spec(name) is None "
              "for name in ('cadquery', 'mujoco', 'jsonschema'))"],
             cwd=run_dir, env=installed_env)
        print(f"Wheel: {wheel.name}")
        print(f"Installed validation: {validation['status']} ({validation['validationScope']}; "
              f"{validation['jsonFilesChecked']} JSON, {validation['csvFilesChecked']} CSV)")
        print(f"Installed demo: {simulation['status']}; duration {simulation['metrics']['duration_s']:.3f} s; "
              f"goal error {simulation['metrics']['finalGoalError_m']:.3f} m")
        print(f"Installed analysis: {analysis['analysisId']}; resultant x {analysis['results']['resultantX_m']:.6f} m; "
              f"acceptance {analysis['acceptanceStatus']}")
        print(f"Installed BUNKER-01: {bunker['schedule']['syntheticDurationHours']:g} synthetic h; "
              f"{bunker['energy']['modeledOnlyElectricEnergy_kWh']:g} modeled-only kWh; construction BLOCKED")
        print(f"Installed maintenance/BOM: {maintenance['summary']['total']} service items; {bom['itemCount']} BOM items")
        print("Wheel licenses/NOTICE: complete and byte-identical to source")
        print("WHEEL SMOKE PASSED — clean non-editable install, offline commands, simulation only.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"WHEEL SMOKE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
