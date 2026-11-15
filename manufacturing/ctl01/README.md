<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# OCE-CTL-01 manufacturing controls — unreleased templates

These documents describe a future quality system, not a released manufacturing package or authorization to fabricate. No material has been procured, no weld made, no unit assembled, and no inspection performed.

## Control block for every manufacturing document

Before physical use, the responsible owner must populate: document ID/revision, machine configuration, released drawing/BOM references, prepared-by/reviewed-by/approved-by named roles and signatures with dates, effective unit/serial range, site, legal requirements, evidence-retention rule, and change history. Current implied metadata is `revision: 0.0-concept`, `status: unreleased template`, and `approvals: none`.

### Authority rules

- `R` review point: objective records require review before routine progression.
- `W` witness point: designated quality/engineering representative is offered the opportunity to witness; absence handling must be defined in the released plan.
- `H` hold point: work **must stop** until the specified authorized person signs acceptance. Editing or merging a document is not release.
- An AI agent cannot sign a point, inspect or handle hardware, release a nonconformance, load a physical controller, or energize/commission a machine.

## Process prerequisites

Only proceed after `../../docs/validation-and-release.md` G1/G2/G3 acceptance appropriate to the activity. Required foundation includes released drawings/schematics and material/components; approved make/buy plan; supplier evidence; hazard/site approvals; qualified welders and electrical/hydraulic technicians; applicable WPS/PQR and weld maps; calibrated tools; controlled lifting/support equipment; isolation/LOTO; hydraulic flush and pressure-test plan; software/configuration release; and a unit traveler with traceability and signed final responsible-engineering review.

No numeric manufacturing parameter is provided. Weld size/current/sequence, dimensions/tolerances, coatings, fastener torque, conductor/terminal settings, HV test voltage/discharge time, hydraulic pressure/cleanliness/flush settings, and software limits must come from the released engineering package. `TBD` means **stop**, not choose a typical value.

## Files

- `make-buy-plan.md`: sourcing and technical-review strategy.
- `process-plan.csv`: conceptual operation flow with gates and evidence records.
- `tooling-register.csv`: tooling capabilities and calibration/qualification requirements, no selected tools.
- `quality-control-plan.csv`: proposed characteristics, acceptance sources, and quality gates.
- `incoming-inspection.md`: supplier/material acceptance before storage or use.
- `traceability.md`: unit genealogy and evidence handling.
- `nonconformance.md`: containment, disposition, and escalation.
- `work-instructions/`: controlled template sequence from frame through commissioning.

The maintenance directory has no authority to alter manufacturing requirements. Any discovered process risk feeds the hazard register, safety case, process FMEA (yet to be created), and signed change review.
