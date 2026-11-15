# SPDX-License-Identifier: Apache-2.0
"""Compile and execute the portable gate tests without target tooling."""

from pathlib import Path
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "builds/firmware"
SOURCE = Path(__file__).with_name("host_tests.cpp")


def main() -> int:
    compiler = os.environ.get("CXX", "g++")
    if shutil.which(compiler) is None:
        print(f"ERROR: C++17 compiler not found: {compiler}", file=sys.stderr)
        return 1
    BUILD.mkdir(parents=True, exist_ok=True)
    binary = BUILD / "ctl01_command_gate_tests"
    command = [compiler, "-std=c++17", "-Wall", "-Wextra", "-Wpedantic", "-Werror",
               "-Wconversion", "-Wsign-conversion", str(SOURCE), "-o", str(binary)]
    print("+", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)
    subprocess.run([str(binary)], cwd=ROOT, check=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode) from exc
