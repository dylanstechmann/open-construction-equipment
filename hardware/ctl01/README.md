<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# OCE-CTL-01 hardware concept

**Unvalidated concept; not fabrication data.** No drawing, register, model, or BOM line is released. Physical values are targets or TBD; a selected generic category is not a supplier approval. No structural capacity, ROPS/FOPS performance, attachment compatibility, battery safety, stopping performance, hydraulic rating, or functional-safety integrity has been demonstrated.

## Contents

- `design-inputs.json`: machine-readable targets, assumptions, and TBD decisions with verification needs.
- `system-breakdown.csv`: functional product structure and owner roles (currently unassigned).
- `interface-control.md`: conceptual mechanical/electrical/fluid/data boundaries and change controls.
- `mechanical/`: architecture and preliminary load-case register.
- `electrical/`: energy/control architecture, preliminary I/O and harness records.
- `hydraulic/`: fluid-power architecture and conceptual hose/circuit register.
- `safety/`: seed hazard and safety-requirement registers; both require competent review.
- `bom/ctl01-bom.csv`: generic make/buy plan with no manufacturer part numbers or prices.
- `cad/`: parameterized OpenSCAD envelope/assembly visualization only.

## Architecture baseline

The concept is a 1.5 m-wide-target, battery-electric compact track loader. Two electric traction drives support skid steering; an electric hydraulic pump powers lift/tilt; the operator uses manual controls; safety-related inhibit/isolation functions are independent from supervisory/autonomy computing. The coupler is universal-*style*, not certified or engineered for universal attachment interchange. See root README for numerical targets and documentation status rules.

## Design workflow

1. Confirm intended use, operational design domain, applicable law/standards, and owners.
2. Resolve hazard and safety requirements (`HZ-*`, `SR-*`) alongside load cases and interfaces (`IF-*`).
3. Derive sizing from analyzed duty cycles and supplier evidence. Replace `TBD` only in reviewed engineering releases, never from CAD appearance.
4. Maintain configuration links between BOM items, drawings/schematics (not yet created), firmware (not yet created), work instructions, inspection, and service records.
5. Verify through `../../docs/validation-and-release.md`. No agent may authorize procurement, fabrication, energization, or operation.

The 96 V nominal target does not make the battery harmless. This repository treats traction battery and connected distribution as hazardous HV pending final electrical classification and applicable rules.
