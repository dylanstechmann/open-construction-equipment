<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Repository validation

Run the complete offline gate from a clean checkout:

```sh
python3 tools/check_all.py
# equivalent
make check
```

It performs:

1. Python bytecode compilation for source, tests and tools.
2. All standard-library `unittest` unit/integration/CLI tests.
3. Recursive strict JSON parsing (duplicate keys and nonstandard constants rejected), finite design-input values, and strict CSV header/row-width/unterminated-record checks, excluding VCS, environments, caches and generated `builds/`.
4. Strict simulation/mission loading, BOM validation, stable service-ID and procedure-link cross-references, combined maintenance chronology, and broad rejection of stale misattribution to the owner without rejecting explicit negations.
5. Two default synthetic demos with byte comparison of JSON and SVG reports.
6. Strict C++17 compilation and host gate tests.
7. A clean offline non-editable wheel build/install smoke test when setuptools 77+ is already available. The test uses no index or dependency downloads, installs into a temporary virtual environment, runs all four default commands away from the checkout, and verifies packaged licenses/NOTICE. If the build backend is absent the unified gate prints an explicit skip; `tools/wheel_smoke.py --require-build-tools` turns that condition into an error.
8. Static OpenSCAD delimiter checks. OpenSCAD rendering is optional; if the executable is absent the gate reports rendering unavailable and continues.

The command needs Python 3.11+ and a C++17 compiler, uses no network and has no hardware side effects. `make test`, `make validate`, `make demo`, `make firmware-test` and `make wheel-smoke` expose individual groups. The required-wheel-smoke target honestly requires preinstalled setuptools 77+ and pip; it does not download them.

CI (`.github/workflows/ci.yml`) runs the same gate on Python 3.11 and 3.12, checks the local build backend, and requires the offline wheel smoke with read-only repository permissions, concurrency cancellation and a job timeout. It has no secrets, dependency-download step, publishing, releases, controller tools or deployment.

From a non-editable wheel, runtime data is installed under `share/open-construction-equipment`. In that mode `oce validate` checks the four bundled JSON files, two CSV files, procedure links and semantic loaders, and reports `validationScope: package-resources`; it does **not** claim full source-repository validation. Full repository checks and provenance scanning require a checkout or explicit `--root`. All license texts and NOTICE are installed under `dist-info/licenses`, preserving the relative `LICENSES/` references.

Validation establishes software/data consistency only. It does not establish mechanical/electrical/hydraulic correctness, standards compliance, physical safety or maintenance evidence.
