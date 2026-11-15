<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Synthetic host-only examples

No file contains real site coordinates, bystander data, a physical machine record or operational authorization. Analysis geometry is hypothetical and agent-authored. BUNKER-01 example geometry exactly matches its canonical visualization CAD parameters after mm-to-m conversion; neither is a structural or excavation design. The mission uses dimensionless-site Cartesian coordinates expressed in metres. Service examples explicitly state that no maintenance, event, inspection, measurement or approval occurred.

From the repository root with Python 3.11+:

```sh
# Deterministic obstacle-avoidance demo; writes ignored builds/demo/.
PYTHONPATH=src python3 -m open_construction_equipment simulate

# Complete structured result and explicit report destination.
PYTHONPATH=src python3 -m open_construction_equipment simulate \
  --config configs/ctl01.simulation.json \
  --mission examples/missions/synthetic-yard.json \
  --output-dir builds/yard --json

# Unreviewed AN-LC-001A arithmetic; writes ignored builds/analysis/lc001/.
PYTHONPATH=src python3 -m open_construction_equipment analyze \
  --input examples/analysis/synthetic-lc001.json \
  --output-dir builds/analysis/lc001 --json

# Blocked BUNKER-01 synthetic quantities, relative schedule and selected energy assumptions.
PYTHONPATH=src python3 -m open_construction_equipment bunker \
  --input examples/bunker/synthetic-bunker01.json \
  --output-dir builds/bunker01 --json

# Proposed, non-OEM maintenance calculations from synthetic supplied history.
PYTHONPATH=src python3 -m open_construction_equipment maintenance \
  --plan maintenance/ctl01/service-intervals.json \
  --records examples/maintenance/synthetic-service-history.json --json
```

## v0.5.0 synthetic inputs

| Input | Command and default ignored output | Scope |
|---|---|---|
| `physics/synthetic-physics.json` | `oce physics` → `builds/physics/result.json` | Unreviewed terramechanics, bearing, slope, buoyancy, curing and weather screening arithmetic. |
| `cad/synthetic-scene.json` | `oce export-cad` → `builds/cad/` | Local synthetic boxes, materials and relative-time animation exported as six OBJ/MTL, Blender, MJCF, OpenSCAD and FreeCAD artifacts plus a manifest; no external application is run. |
| `powertrain/synthetic-microgrid.json` | `oce powertrain` → `builds/powertrain/result.json` | Battery, solar-hydrogen and fossil-path interval energy, storage, water, logistics, acoustic/exhaust indicators and synthetic costs. |
| `geohazard/synthetic-screen.json` | `oce site --mode screen` → `builds/geohazard/screen/result.json` | Relative comparison of multiple anonymous candidates; never a purchase recommendation. |
| `geohazard/synthetic-adapt.json` | `oce site --mode adapt` → `builds/geohazard/adapt/result.json` | As-is-site concept adaptations and signed synthetic deltas; never construction authorization or completed engineering. |
| `economics/synthetic-pathways.json` | `oce economics` → `builds/economics/result.json` | Explicit unquoted DIY, rental and hybrid lifecycle assumptions and break-even arithmetic. |

To substitute site information, preserve the exact schema and replace only synthetic assumptions with **anonymous labels and local relative metre coordinates from an arbitrary unnamed origin**. Do not insert GPS/GNSS coordinates, latitude/longitude, geohashes, URLs with geolocation queries, street addresses, postcodes, assessor/APN/parcel/tax/deed identifiers, legal-location descriptions, or real-property identifiers. Privacy validation is recursive and fails before output creation. Professional unknowns remain `null`/`UNKNOWN`; do not invent distances, capacities, field evidence, costs, or resolved gates.

All v0.5.0 commands accept `--input` and `--output-dir`; `site` chooses its input and output defaults from `--mode`. For example:

```sh
PYTHONPATH=src python3 -m open_construction_equipment physics --json
PYTHONPATH=src python3 -m open_construction_equipment export-cad --json
PYTHONPATH=src python3 -m open_construction_equipment powertrain --json
PYTHONPATH=src python3 -m open_construction_equipment site --mode screen --json
PYTHONPATH=src python3 -m open_construction_equipment site --mode adapt --json
PYTHONPATH=src python3 -m open_construction_equipment economics --json
```

The analysis result, default mission result/SVG, BUNKER-01 result/schedule SVG, and every v0.5.0 result/CAD artifact are deterministic. BUNKER-01 unmodeled energy is `null`, never zero; its 246 kWh subtotal covers eight explicit assumptions only and is not total project energy. Every BUNKER-01 result remains construction-blocked with all human gates unresolved. AN-LC-001A is partial synthetic arithmetic with acceptance `NOT_ASSESSED`, not a stability, capacity, or operational verdict. Expected default mission termination is `succeeded` / `GOAL_REACHED`; mission result and SVG are deterministic. `no_path`, `stopped`, and `timeout` are explicit non-success outcomes. `synthetic-service-record.json` illustrates incomplete controlled-record semantics; the two files under `examples/maintenance/` illustrate explicit synthetic work-entry linkage used by the history. None can return equipment to service.
