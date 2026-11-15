<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# OCE-CTL-01 maintenance planning — not an OEM manual

**No released machine, approved maintenance schedule, physical service, or return-to-service authorization exists.** These are proposed planning procedures for later qualified review. They do not authorize inspection by untrained people, troubleshooting by energization, controller updates, pressure release, or operation of a damaged machine.

## Proposed intervals versus obligations

Entries labeled `proposed` are learning-project placeholders for reviewing inspection needs; they are not measured service-life recommendations. Final intervals must be based on exact OEM component manuals, duty/environment, condition data, risk assessment, and current regulatory/site requirements. Where multiple valid obligations apply, the responsible released manual shall resolve the schedule without reducing mandatory safety checks. A missed inspection or unknown history is a stop condition, not a reason to reset an interval.

## Qualified work and energy control

- Maintain no machine unless its owner has authorized the work and supplied the exact configuration/manual.
- Before each use, follow the approved site walkaround/operational manual. Keep people clear and never approach a suspended load or unstable track/arm to inspect it.
- Only qualified personnel perform assigned HV, hydraulic, lifting, undercarriage, welding, safety-system and functional test tasks. Hazardous work follows safe shutdown/LOTO, every identified energy source, and **measured/physical zero-energy verification** by the approved method.
- The battery’s 96 V nominal target, LFP chemistry, low speed or key-off state does not make it safe. Account for capacitors, charger/backfeed, LV, hydraulic trapped pressure, hot components, gravity, tracks/tensioning, springs and remote restart.
- Never defeat, jumper, block or leave defeated an e-stop, interlock, guard, lock sensor, BMS protection, protective brake or load-holding device. No diagnostic may temporarily bypass a protective function unless a future, signed, independently controlled bench procedure explicitly allows it and restores/verifies it before return; it is never allowed for operation.
- Calibrated tools and released torques/fluids/limits are required. `TBD` means stop; do not substitute “standard” values.

## Files

- `service-schedule.csv`: proposed inspection/service planning and required competency.
- `service-intervals.json`: initial AI-authored machine-readable proposed intervals linked to every SVC ID; not an OEM schedule. Use `../../docs/maintenance-tooling.md` and the host `oce maintenance` command for calculations from explicit supplied records.
- `lubrication-register.csv`: possible lubrication points, specifications and fill all TBD.
- `torque-register.csv`: unresolved safety-critical joints with release/evidence sources.
- `parts-register.csv`: generic replaceable/service parts linked to the hardware BOM, no supplier numbers.
- `troubleshooting.md`: symptom triage with no bypass or live diagnostic instructions.
- `service-record-template.json`: valid JSON structure for future controlled unit records.
- `procedures/`: pre-start, LOTO, subsystem and return-to-service templates.

Use `../../manufacturing/ctl01/traceability.md` and `nonconformance.md` for evidence/deviations. The exact unit record retains actual measurements, parts/lots, instrument IDs/calibration, human reviewers, and authorized limited service-return scope. Agent-authored text never counts as physical service, inspection or owner review.
