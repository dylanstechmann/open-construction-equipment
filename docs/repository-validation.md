<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Repository validation

Run the complete local offline gate from a clean checkout:

```sh
python3 tools/check_all.py
# equivalent
make check
```

It performs:

1. Python bytecode compilation for source, tests and tools.
2. All standard-library `unittest` unit/integration/CLI tests.
3. Recursive strict JSON parsing (duplicate keys and nonstandard constants rejected), finite design-input values, and strict CSV header/row-width/unterminated-record checks, excluding VCS, environments, caches and generated `builds/`. The synthetic analysis and BUNKER-01 JSON are included in these generic counts without any inference of physical validity.
4. Strict simulation/mission and AN-LC-001A loading, per-value analysis provenance, stable analysis identity/trace IDs, BOM validation, stable service-ID and procedure-link cross-references, combined maintenance chronology, and broad rejection of stale misattribution to the owner without rejecting explicit negations. Full source validation resolves analysis traces against actual design-input, load-case, hazard, safety-requirement and interface records and keeps LC-001 partial/unreviewed/TBD.
5. Strict BUNKER-01 input/register/site loading, DAG/gate/fleet/energy references, unresolved-gate and blank-evidence invariants, false site/authorization flags, and blocked output status. Source-only validation also requires exact example-to-CAD geometry agreement; package validation honestly cannot perform that source-document check.
6. Two default synthetic demos with byte comparison of JSON and SVG reports.
7. Two AN-LC-001A analyses with byte-identical deterministic result JSON, `acceptanceStatus: NOT_ASSESSED`, `reviewStatus: UNREVIEWED`, and `physicalValidationPerformed: false`.
8. Two BUNKER-01 plans with byte-identical result JSON and schedule SVG, all 15 gates unresolved, and construction blocked.
9. Strict C++17 compilation and host gate tests.
10. A clean offline non-editable wheel build/install smoke test when setuptools 77+ is already available. The test uses no index or dependency downloads, installs into a temporary virtual environment, runs all six default commands away from the checkout (including installed analysis and bunker planning), and verifies packaged licenses/NOTICE, bunker outputs, and shared data. If the build backend is absent or too old, the local unified gate prints an explicit skip; `tools/wheel_smoke.py --require-build-tools` turns that condition into an error. Wheel validation is never weakened into an import-only check.
11. Static OpenSCAD delimiter checks for both `hardware/ctl01/cad/*.scad` and `projects/bunker01/cad/*.scad` (four sources). OpenSCAD rendering is optional; if the executable is absent the gate reports rendering unavailable and continues.

The local command needs Python 3.11+ and a C++17 compiler, uses no network, and has no hardware side effects. Project runtime and tests have no third-party runtime dependencies. JSON Schema tooling is optional; runtime analysis validation is implemented with the standard library. `make test`, `make validate`, `make demo`, `make firmware-test` and `make wheel-smoke` expose individual groups. The required-wheel-smoke target honestly requires preinstalled setuptools 77+ and pip; locally it does not download them.

CI (`.github/workflows/ci.yml`) runs the same gate on Python 3.11 and 3.12 with read-only repository permissions, concurrency cancellation and a job timeout. Before the tooling diagnostic, offline gate, and separately required wheel smoke, **each matrix job explicitly downloads and installs only the pinned build provision `setuptools==80.9.0`**. The diagnostic reads `importlib.metadata.version("setuptools")`. After this explicit provisioning step, source/tests and wheel build/smoke remain offline with no index or dependency downloads. CI has no secrets, publishing, releases, controller tools or deployment. Local behavior is intentionally unchanged when build tools are absent: the local gate may skip only the optional wheel smoke with an explicit message, while every other check still runs.

From a non-editable wheel, runtime data is installed under `share/open-construction-equipment`. In that mode `oce validate` checks the bundled input JSON/CSV files, procedure links and semantic loaders, including analysis and BUNKER-01 resources, and reports `validationScope: package-resources`; it does **not** claim full source-repository validation, CAD/example comparison, or source-document trace review. Full repository checks, source-register trace resolution, schemas, and provenance scanning require a checkout or explicit `--root`. All license texts and NOTICE are installed under `dist-info/licenses`, preserving the relative `LICENSES/` references.

Validation establishes software/data consistency and reproducible arithmetic only. It does not establish mechanical/electrical/hydraulic correctness, stability, capacity, standards compliance, physical safety, physical validity, or maintenance evidence.
