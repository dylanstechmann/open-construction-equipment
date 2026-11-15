# SPDX-License-Identifier: Apache-2.0
"""Single offline verification entry point for a clean checkout."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


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


def main() -> int:
    require(run([sys.executable, "-m", "compileall", "-q", "src", "tests", "tools", "firmware/ctl01"]), "Python compile")
    require(run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]), "Python tests")
    validation = require(run([sys.executable, "-m", "open_construction_equipment", "validate", "--json"], capture=True), "repository validation")
    print(json.dumps(json.loads(validation), indent=2, sort_keys=True))
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
        bunker_outputs.append(((directory / "result.json").read_bytes(), (directory / "schedule.svg").read_bytes()))
    if bunker_outputs[0] != bunker_outputs[1]:
        raise RuntimeError("deterministic bunker JSON or SVG outputs differ")
    print("Deterministic BUNKER-01 result JSON and schedule SVG: byte-identical; construction BLOCKED")
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
