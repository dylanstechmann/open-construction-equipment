<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Synthetic host-only examples

No file contains real site coordinates, bystander data, a physical machine record or operational authorization. Analysis geometry is hypothetical and agent-authored, not OpenSCAD-derived or owner-supplied. The mission uses dimensionless-site Cartesian coordinates expressed in metres. Service examples explicitly state that no maintenance, event, inspection, measurement or approval occurred.

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

# Proposed, non-OEM maintenance calculations from synthetic supplied history.
PYTHONPATH=src python3 -m open_construction_equipment maintenance \
  --plan maintenance/ctl01/service-intervals.json \
  --records examples/maintenance/synthetic-service-history.json --json
```

The analysis result and default mission result/SVG are deterministic. AN-LC-001A is partial synthetic arithmetic with acceptance `NOT_ASSESSED`, not a stability, capacity, or operational verdict. Expected default mission termination is `succeeded` / `GOAL_REACHED`; mission result and SVG are deterministic. `no_path`, `stopped`, and `timeout` are explicit non-success outcomes. `synthetic-service-record.json` illustrates incomplete controlled-record semantics; the two files under `examples/maintenance/` illustrate explicit synthetic work-entry linkage used by the history. None can return equipment to service.
