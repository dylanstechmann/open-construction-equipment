# SPDX-License-Identifier: Apache-2.0
"""Build/install a non-editable wheel offline and test its installed CLI."""

from __future__ import annotations

import argparse
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
        simulation = json.loads(_run([str(oce), "simulate", "--json"], cwd=run_dir, env=installed_env))
        if simulation["status"] != "succeeded":
            raise RuntimeError(f"installed default simulation failed: {simulation['finalReasons']}")
        if not (run_dir / "builds/demo/result.json").is_file() or not (run_dir / "builds/demo/trajectory.svg").is_file():
            raise RuntimeError("installed simulation did not write default reports in the clean working directory")
        maintenance = json.loads(_run([str(oce), "maintenance", "--json"], cwd=run_dir, env=installed_env))
        if maintenance["summary"]["total"] != 20:
            raise RuntimeError("installed maintenance data is incomplete")
        bom = json.loads(_run([str(oce), "bom", "--json"], cwd=run_dir, env=installed_env))
        if bom["itemCount"] != 63:
            raise RuntimeError("installed BOM data is incomplete")
        print(f"Wheel: {wheel.name}")
        print(f"Installed validation: {validation['status']} ({validation['validationScope']}; "
              f"{validation['jsonFilesChecked']} JSON, {validation['csvFilesChecked']} CSV)")
        print(f"Installed demo: {simulation['status']}; duration {simulation['metrics']['duration_s']:.3f} s; "
              f"goal error {simulation['metrics']['finalGoalError_m']:.3f} m")
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
