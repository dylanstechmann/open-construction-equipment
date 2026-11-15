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
    sources = sorted((ROOT / "hardware/ctl01/cad").glob("*.scad"))
    for source in sources:
        text = source.read_text(encoding="utf-8")
        for opening, closing in (("{", "}"), ("(", ")"), ("[", "]")):
            if text.count(opening) != text.count(closing):
                raise RuntimeError(f"static OpenSCAD delimiter check failed: {source}")
    if shutil.which("openscad") is None:
        return f"OpenSCAD unavailable; {len(sources)} sources passed static delimiter checks; rendering not run (optional)."
    return "OpenSCAD is installed but rendering is not required by the offline gate; static checks passed."


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
