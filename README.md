<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Open Construction Equipment (OCE)

> **CONCEPT ONLY — NOT READY TO BUILD OR OPERATE.** Open Construction Equipment is a personal hobby and learning project. Nothing here is a validated machine design, fabrication release, certified protective structure, validated safety function, or declaration of standards compliance. Do not fabricate, energize, lift, tow, or operate equipment from this material. All dimensions, capacities, masses, voltages, speeds, intervals, and architecture choices are unvalidated targets or assumptions unless an evidence record explicitly says otherwise. Qualified engineers and technicians must complete the applicable design, risk, manufacturing, inspection, test, and legal review before any physical work.

OCE publishes lifecycle information and host-only learning tools for the **OCE-CTL-01** reference concept: a battery-electric compact track loader with dual electric traction drives, electro-hydraulic lift/tilt, a universal-*style* quick attach interface, manual controls, an independent safety-chain intent, and an autonomy-ready sensing/control boundary. “Style” denotes an interface concept only; attachment interchangeability is unvalidated.

**Software boundary:** every executable is **SIMULATION/CALCULATION-ONLY and host-testable**. There is no real actuation, hardware I/O, controller flashing, deployment mechanism or bypass of the independent protective chain. The Python supervisor and C++ gate are ordinary non-certified reference logic, not safety functions.

**Second reference concept:** [BUNKER-01](projects/bunker01/README.md) is a civilian, non-habitable cut-and-cover utility-enclosure documentation/design baseline. It is not a habitable bunker, storm safe room, protective structure, excavation plan, or construction release. No occupancy, blast/ballistic/CBRN protection, site safety, physical autonomous construction, or code compliance is claimed.

## Reference design targets — not released specifications

The numeric targets below were **initially authored by an AI implementation prompt; owner review is pending**. They were not supplied as owner-approved requirements.

| Topic | Current target or assumption | Status |
|---|---|---|
| Operating mass | approximately 2,200 kg | Initial AI-authored unvalidated target |
| Rated operating capacity | 500 kg target | Unvalidated; stability, structure, hydraulics and standards assessment TBD |
| Energy storage | 96 V nominal LFP, approximately 30 kWh | Initial AI-authored architecture target; integration and safe limits TBD |
| Traction | two 15 kW electric motors | Target envelope; gearing, thermal limits and braking TBD |
| Hydraulic pump | 10 kW electric drive | Target envelope; pressure, flow, cooling and controls TBD |
| Width | approximately 1.5 m | Envelope target only, not a manufacturing dimension |
| Manual travel | 6 km/h maximum | Unvalidated target; stopping behavior and stability TBD |
| Simulated autonomy travel | 0.8 m/s maximum | Synthetic assumption only; no physical capability claim |

No manufacturing dimensions, weld sizes, fastener torques, hydraulic pressure settings, structural thicknesses, or ROPS/FOPS compliance claims are released. Those values are **TBD pending calculations, supplier data, applicable standards, risk assessment, and signed responsible engineering review**.

## Quickstart — host tools only

Requirements: Python 3.11 or newer; a C++17 compiler for firmware host tests. Python runtime and tests use only the standard library.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
oce --help
oce validate
oce simulate
oce analyze
oce bunker
oce maintenance
oce bom
oce physics
oce export-cad
oce powertrain
oce site --mode screen
oce site --mode adapt
oce economics
make check
```

The same defaults work after a non-editable wheel install: runtime data is discovered from the installation's `share/open-construction-equipment` directory. In that mode `oce validate` explicitly reports package-resource validation, not a full source-checkout validation. `python tools/wheel_smoke.py --require-build-tools` verifies a clean offline build/install using preinstalled setuptools 77+ and pip, without downloading dependencies.

An installation-free alternative is:

```sh
PYTHONPATH=src python3 -m open_construction_equipment simulate
PYTHONPATH=src python3 -m open_construction_equipment analyze
PYTHONPATH=src python3 -m open_construction_equipment bunker
PYTHONPATH=src python3 -m open_construction_equipment physics
PYTHONPATH=src python3 -m open_construction_equipment export-cad
PYTHONPATH=src python3 -m open_construction_equipment powertrain
PYTHONPATH=src python3 -m open_construction_equipment site --mode screen
PYTHONPATH=src python3 -m open_construction_equipment site --mode adapt
PYTHONPATH=src python3 -m open_construction_equipment economics
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 tools/check_all.py
```

The deterministic default demo plans around two circular obstacles in a synthetic rectangular yard. Expected console summary:

```text
Simulation status: succeeded (GOAL_REACHED)
Goal error: 0.293 m; duration: 25.9 s
Reports: .../builds/demo/result.json and .../builds/demo/trajectory.svg
```

The JSON contains structured termination/event data, paths and metrics; the SVG is self-contained. Reports go under ignored `builds/`. See [examples](examples/README.md), [simulation](docs/simulation.md) and [autonomy](docs/autonomy.md).

`oce analyze` additionally runs AN-LC-001A, an unreviewed static longitudinal load-moment calculation on explicitly synthetic inputs. It writes deterministic `builds/analysis/lc001/result.json`; the sample total mass is 2020 kg and resultant x is 0.144059405940594 m. Acceptance remains `NOT_ASSESSED`: this is neither a stability rating nor a capacity result. See [engineering calculations](docs/engineering-calculations.md).

`oce bunker` runs blocked BUNKER-01 synthetic quantity/dependency/energy arithmetic and writes deterministic `builds/bunker01/result.json`, `construction-energy.json` plus `schedule.svg`. The default geometric excavation is 109.5 m³, gross concrete is 17.6625 m³, relative duration is 472 h, and the eight-assumption energy subtotal is 246 kWh. These are not order quantities, total project energy, an excavation/structural design, or an executable construction schedule. All 15 human gates remain unresolved. See [BUNKER-01 planning](docs/bunker-planning.md).

## v0.5.0 deterministic trade studies and interchange

All eleven CLI commands work from source defaults and from an installed wheel. The v0.5.0 additions write only ignored `builds/` outputs and return `SIMULATED_UNREVIEWED` results; threshold findings and unresolved gates do not constitute acceptance, physical validation, construction, procurement, or operational release.

- **`oce physics`** evaluates transparent track/soil, bearing, infinite-slope, buoyancy, concrete-maturity, and weather-derating screens. These are simplified arithmetic models, not finite-element/CFD analysis, concrete acceptance, or an equipment rating. Output: `builds/physics/result.json`. See [multi-physics and CAD](docs/multiphysics-and-cad.md).
- **`oce export-cad`** writes `scene.obj`, `scene.mtl`, `blender_scene.py`, `ctl01_bunker_physics.xml` (MuJoCo MJCF), `scene.scad`, `scene_freecad.py`, and their `result.json` manifest under `builds/cad/`. Geometry is generated natively without importing Blender, FreeCAD, OpenSCAD, MuJoCo, or a CAD kernel. Running those applications is a separate manual opt-in; generated geometry and scripts are not released manufacturing CAD or physical simulation evidence. See [external tools](docs/cad-external-tools.md).
- **`oce powertrain`** compares LFP battery, solar-hydrogen PEMFC/H2-ICE, diesel, and gasoline paths using interval energy/mass ledgers, cold derating, curtailment, water/CHP, fuel logistics, noise/exhaust indicators, and allocated versus one-time costs. It does not design an electrical/hydrogen system, establish ventilation or safe entry, or authorize equipment operation. Output: `builds/powertrain/result.json`. See [powertrain microgrid](docs/powertrain-microgrid.md).
- **`oce site --mode screen`** compares anonymous candidate parcels; **`--mode adapt`** derives concept adaptations and signed cost/schedule deltas for one anonymous existing site. Inputs fail closed on GPS/GNSS, latitude/longitude, geohashes, addresses, assessor/APN/parcel identifiers, and similar real-location data. Use only anonymous labels and local relative metres. Outputs under `builds/geohazard/{screen,adapt}/` omit raw feature vertices, retain no location data, make no purchase/permit decision, and leave all human gates unresolved. See [rural geohazards and privacy](docs/geohazard-rural.md).
- **`oce economics`** compares DIY, rental, and hybrid pathways across tooling, fabrication, labor, wear, rental proration, energy, and selected site adaptations, with break-even operating hours. Every amount is synthetic and unquoted; results are not supplier prices or procurement authorization. Output: `builds/economics/result.json`. See [fabrication economics](docs/fabrication-economics.md).

Core runtime remains `dependencies = []`. Optional extras `cad` (`cadquery`), `physics` (`mujoco`), and `schema` (`jsonschema`) support only local inspection/validation experiments. They are not needed to build, install, run any CLI command, or pass offline tests; `tools/check_all.py` never installs or executes them. Blender, OpenSCAD, and FreeCAD remain separate optional applications.

## Repository guide

- [`src/open_construction_equipment/`](src/open_construction_equipment/) — strict config loaders, geometry, A*, pure pursuit, supervisor, kinematic simulator, mission, maintenance, BOM, deterministic engineering, BUNKER-01 planning, multi-physics, CAD/interchange, microgrid, privacy-safe geohazard, economics, validation and CLI modules.
- [`configs/`](configs/ctl01.simulation.json) and [`schemas/`](schemas/) — explicit simulation assumptions and interchange schemas; internal runtime validation needs no schema package.
- [`examples/`](examples/README.md) — synthetic yard, analysis, BUNKER-01 planning, service history, multi-physics, CAD scene, microgrid, anonymous geohazard and lifecycle-economics envelopes only.
- [`firmware/ctl01/`](firmware/ctl01/) — portable non-safety-rated C++17 command-gate reference and host tests.
- [`tests/`](tests/) and [`tools/check_all.py`](tools/check_all.py) — offline unit/integration/CLI tests and unified verification.
- [`docs/`](docs/engineering-status.md) — status, architecture, safety case, algorithms, engineering calculations, maintenance tooling, standards and decisions.
- [`hardware/ctl01/`](hardware/ctl01/README.md) — concept breakdown, interfaces, BOM, hazards and visualization-only OpenSCAD.
- [`manufacturing/ctl01/`](manufacturing/ctl01/README.md) — **unreleased controlled templates**, not permission to fabricate.
- [`maintenance/ctl01/`](maintenance/ctl01/README.md) — **proposed** service planning and procedures, not an OEM manual.
- [`projects/bunker01/`](projects/bunker01/README.md) — **BUNKER-01 concept-only** civilian non-habitable utility enclosure requirements, null site-input register, safety/architecture, human gates, fleet gaps, conceptual BOM and synthetic visualization CAD; host-only synthetic quantity/schedule software is available through `oce bunker`; no construction or entry is authorized.

## Lifecycle map

| Phase | Purpose | Exit evidence | Current state |
|---|---|---|---|
| 0. Concept and scope | Establish targets, interfaces, hazards and licensing | Traceable concept baseline; no physical readiness implied | **Current repository phase** |
| 1. Engineering definition | Calculations, supplier selection, drawings and verification plans | Signed design reviews and controlled prerelease artifacts | Not started/released |
| 2. Component and bench verification | Controlled non-operational part/function verification | Calibrated records and reviewed deviations | Not performed |
| 3. Prototype manufacturing | Build only from released instructions by qualified personnel | Traceability and physical inspections | Not authorized |
| 4. Manual machine validation | Progressive protective/manual function validation | Approved plans, measured evidence and signed release | Not authorized |
| 5. Autonomy investigation | Simulation first; separately gated later research | Simulation is not physical validation | **Host reference simulation only** |

A target cannot become “measured,” “reviewed,” or “released” through documentation or passing simulation. See [validation and release](docs/validation-and-release.md).

## Safety and contribution boundaries

Read the [pre-release safety case](docs/safety-case.md), [hazard register](hardware/ctl01/safety/hazard-register.csv), [ADR-0002](docs/decisions/ADR-0002-independent-safety-and-simulation.md), and [contributing guide](CONTRIBUTING.md). Manual controls and independent protection are intended to keep supervisory autonomy out of the sole protective path. A simulation never authorizes energizing hardware, flashing controllers or a field trial. A far-future ROS 2 or real-machine integration would still require the engineering, validated dynamics/perception, independent protection, legal/site and signed-review work described in the new software documents; no deployment instructions are supplied.

## AI-assisted project status

AI coding/research agents have assisted with repository structure, documentation, conceptual registers, visualization, simulation software and host tests. This is transparent assistance, not evidence of engineering competency, human approval, manufacture, inspection or physical testing. Agent-run analyses are not personally performed owner review. No person has reviewed or approved a physical machine design. External standards and publications retain their own copyrights and licenses.

## Licensing

Original software is offered under **Apache-2.0**, original hardware designs under **CERN-OHL-S-2.0**, and original documentation/media under **CC-BY-SA-4.0**, as scoped in [`LICENSE`](LICENSE). Full license texts are under [`LICENSES/`](LICENSES/) and are included with NOTICE in installed wheels under `dist-info/licenses`. Sharing source does not make hardware safe, certified or suitable for any purpose. See [`NOTICE.md`](NOTICE.md).
