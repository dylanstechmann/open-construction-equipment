<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# OCE-CTL-01 engineering status

**Baseline date:** 2026-11-15<br>
**Lifecycle:** Phase 0 — concept.<br>
**Physical release:** none. No prototype has been built, reviewed, or tested by this project.

## Evidence summary

| Area | Available now | Not established |
|---|---|---|
| Mission | Learning reference for open, maintainable electric compact track loader development | Production requirements, legal operating domain, user acceptance |
| Performance | Approximate numeric targets in `hardware/ctl01/design-inputs.json`; AN-LC-001A provides partial unreviewed synthetic static arithmetic | Capacity, stability, gradeability, endurance, braking distance, speed control, lifting performance |
| Mechanical | System decomposition, conceptual interfaces, non-fabrication envelope model, AN-LC-001A static longitudinal arithmetic | Detailed geometry, stress/fatigue life, section sizes, material/weld releases, ROPS/FOPS performance |
| Electrical | 96 V nominal LFP target, dual-drive/pump concept, independent protective-chain intent | Complete schematics, fault analysis, battery safety evidence, EMC, insulation coordination, charger integration |
| Hydraulic | Electro-hydraulic lift/tilt target and preliminary function/hose registers | Pressure/flow, component sizing, load holding, hose specification, thermal balance, validated flushing criteria |
| Controls/safety | Manual supervisory concept, independent safety-chain intent, seed I/O/hazards, non-certified Python/C++ host gate references | Safety requirements specification, PL/SIL allocation, circuit design, independent diagnostics, validated physical stopping and reset behavior |
| Manufacturing | Controlled process templates and evidence requirements | Supplier/PPI approvals, released drawings, qualified WPS/PQR, actual inspections or conformance records |
| Maintenance | Proposed intervals and safe-work planning | OEM/regulatory schedules, service limits, validated procedures, released torque/lubricant values |
| Autonomy | Simulation-first ADR plus host-only deterministic A*, pure pursuit, supervisory and unicycle-reference implementation | External perception, validated dynamics, real-time integration, fail-safe physical autonomy and field validation |
| Standards | Candidate applicability register | Current-edition purchase/review, jurisdiction analysis, conformity assessment/certification |

## Status vocabulary for registers

- `target`: desired value or behavior with no verification implied.
- `assumption`: provisional input; the consequence of being wrong must be examined.
- `TBD`: unresolved and must not be inferred or substituted during manufacture/service.
- `calculated`: reproducible engineering analysis exists; still not physical proof.
- `simulated`: executable model result with recorded model/version and limitations.
- `measured`: physical result tied to calibrated equipment, conditions, and raw evidence.
- `inspected`: a named competent person physically examined a specific item/unit.
- `reviewed`: identified qualified reviewer signed a specific version and scope.
- `released`: responsible owner authorized a defined configuration for an explicitly limited next activity; never a blanket safety statement.

These terms do not form an automatic ladder. Calculation does not imply measurement; measurement does not imply review; review of one component does not release the machine.

## Immediate engineering prerequisites

1. Establish operational design domain, intended attachments, foreseeable misuse, applicable jurisdiction, and current standards editions.
2. Complete risk assessment and a requirements specification with traceable safe states and acceptance criteria.
3. Resolve stability/load paths, protective structure strategy, structural/fatigue analysis, attachment interface engineering, and support/lifting points.
4. Resolve battery/charging safety, isolation/contactors, drive/braking behavior, hydraulics/load holding, thermal management, and service isolation.
5. Only then produce detailed drawings and controlled prototype plans for signed review. Keep all `TBD` physical settings unresolved in this phase.

No error found by later review should be hidden; update the affected target, hazard, requirement, and decision records together.

## Phase 2 host software evidence

The `oce` host CLI supports `validate`, `simulate`, `analyze`, `bunker`, `maintenance`, and `bom`. The default synthetic yard produces deterministic JSON/SVG under ignored `builds/`; unit, integration, CLI and C++ host tests run through `python3 tools/check_all.py`. AN-LC-001A adds byte-identical deterministic analysis JSON with acceptance `NOT_ASSESSED` and review `UNREVIEWED`; it is not a stability rating or ROC calculation. These are agent-run software consistency results, not physical validation or signed owner review. The simulator is a documented kinematic approximation, and the service intervals remain proposed non-OEM values.

See `simulation.md`, `autonomy.md`, `engineering-calculations.md`, `maintenance-tooling.md`, `firmware.md`, and `repository-validation.md` for exact boundaries and commands. No ROS 2, hardware I/O, target image, controller flashing or deployment integration is present.

## BUNKER-01 documentation/design baseline — unreleased

`projects/bunker01/` adds a separate Phase 0 reference concept for a civilian **non-habitable** cut-and-cover reinforced-concrete utility enclosure. Its baseline contains requirements, architecture and safety boundaries; a real-site input register whose values are all null/TBD; unresolved human quality gates; synthetic work planning; honest fleet gaps; a conceptual BOM; visualization-only CAD; and maintenance/handover requirements. `oce bunker` now adds deterministic host-only quantity, earliest-start dependency, critical-path, autonomy-class accounting and selected-energy arithmetic using the canonical registers and CAD-matched synthetic example. It writes blocked JSON/SVG with explicit hypothetical gate-evidence timing (`gateAcceptancePerformed:false`), validates source CAD agreement, and runs from source or an installed wheel. See [BUNKER-01 planning](bunker-planning.md).

This is not an autonomous construction capability demonstration, structural design, excavation plan, safe shelter, procurement list, permit package, or physical readiness result. Unmodeled energy is `null`, not zero; the modeled-only subtotal is not project energy. No schedule date, total project energy, peak power, charger sizing, cost, supplier, borrow/haul decision, or percent autonomous readiness is produced.

No real site, permit, structural design, protective system, utility clearance, inspection, construction authorization, physical validation or use approval exists. Current occupancy, habitation, sleeping, storm-shelter/safe-room use, blast/ballistic/CBRN claims and construction from concept artifacts are prohibited. All nine CAD geometry values and all work durations are AI-authored synthetic assumptions, not engineering selections. OCE-CTL-01 cannot currently excavate, compact, pour/pump concrete or perform specialist work. See the [BUNKER-01 baseline](../projects/bunker01/README.md), its [safety boundaries](../projects/bunker01/safety.md), and [site-input status](../projects/bunker01/site-inputs.json).
