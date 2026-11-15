<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# BUNKER-01 — civilian utility enclosure concept

> **CONCEPT ONLY — NOT FOR CONSTRUCTION, EXCAVATION, ENTRY, OCCUPANCY, OR PROTECTIVE USE.** BUNKER-01 is an AI-assisted reference project for a possible **cut-and-cover reinforced-concrete, non-habitable utility enclosure**. No real site has been selected or investigated. No engineer, authority having jurisdiction (AHJ), owner, competent excavation person, or other responsible human has approved this baseline. Do not build from these artifacts.

## Vision and boundary

The owner's prompt is: **“Electric open source full auto construction. Need a bunker.”** This project interprets “bunker” strictly as a civilian equipment/storage enclosure, with electric open-source autonomous construction as a long-term research goal. It is not a military or weapons project.

The target use is limited to future, separately approved **non-habitable equipment or storage**. The following are outside the current design and are prohibited claims or uses:

- current occupancy, sleeping, habitation, approved underground occupancy, or use as a storm safe room;
- blast, ballistic, CBRN (chemical, biological, radiological, nuclear), military, or weapons protection;
- shelter from tornadoes, hurricanes, floods, fire, or other emergencies;
- excavation, concrete work, energization, autonomous machine operation, or entry based on this concept; and
- structural capacity, waterproofing performance, air quality, fire resistance, security, egress, code compliance, or service-life claims.

A later approved design could permit a defined equipment/storage use only after real-site inputs, qualified engineering, permits, inspections, and all applicable [quality gates](construction/quality-gates.csv) are resolved by named responsible humans. Even then, the use classification would be explicit and limited; “non-habitable” does not mean safe to enter.

## Baseline contents

| Artifact | Purpose |
|---|---|
| [Requirements](requirements.md) | Scope, exclusions, open owner decisions, and synthetic-value provenance |
| [Site inputs](site-inputs.json) | Required real-world evidence; every value is `null`/`TBD`, with private location excluded from the repository |
| [Architecture](architecture.md) | Concept systems and interfaces, not selected construction details |
| [Safety](safety.md) | Hazard register narrative, specialist responsibilities, entry/excavation prohibitions, emergency and abandonment boundaries |
| [References](references.md) | Official starting points for later qualified applicability review |
| [Work breakdown](construction/work-breakdown.csv) | Stable planning packages `BW-001`–`BW-022`; source for the synthetic relative-hour model, never an executable construction schedule |
| [Quality gates](construction/quality-gates.csv) | Unresolved human gates `BG-001`–`BG-015` |
| [Fleet register](construction/fleet-register.csv) | Honest current/future equipment roles and capability gaps |
| [Concept BOM](bom/bunker01-bom.csv) | Unpriced, unresolved material/equipment categories, not a procurement list |
| [CAD concept](cad/README.md) | Self-contained OpenSCAD visualization with AI-authored geometric assumptions |
| [Synthetic planning input](../../examples/bunker/synthetic-bunker01.json) | CAD-matched geometry, explicit soil/waste factors and eight selected energy assumptions |
| [Planning arithmetic](../../docs/bunker-planning.md) | Exact quantity/schedule/energy conventions, commands, outputs and exclusions |
| [Maintenance](maintenance.md) | Future inspection/monitoring and record needs, without approved intervals |
| [Handover requirements](handover-requirements.md) | Evidence needed before any limited acceptance; currently absent |

## Planning conventions

- Work-package dependencies are semicolon-separated predecessor IDs; an empty field means no predecessor. Every listed predecessor must be complete before the dependent package can be planned. `requiredGateIds` lists human gates that must be **accepted before that package starts**, using the same semicolon convention. The calculator additionally models zero-duration hypothetical evidence nodes whose predecessors are each gate’s `relatedWorkPackages`; package earliest starts respect both ordinary and evidence-node predecessors. `hypotheticalEvidenceCompleteHour` is timing arithmetic only, `gateAcceptancePerformed` remains false, and all actual starts remain blocked. Gates are not implied complete by finishing a package. In the gate register, `relatedWorkPackages` identifies the evidence-producing/review activity; it does not mean that activity may start before its own prerequisites.
- `durationHours` is an AI-authored synthetic planning assumption, or `0` for a gate/acceptance activity. It is not a quotation, productivity estimate, resource-loaded schedule, or authorization. Dependencies form an acyclic graph; concurrency still requires a separate site plan.
- `autonomyClass` values are `human_gate`, `specialist`, `future_supervised_autonomy`, and `simulation_candidate`. The latter two describe research possibilities only, not present physical capability or permission. Specialist packages remain specialist work even if a machine could assist in the future.
- BOM quantities remain `TBD` unless explicitly marked `calculated_example_only`; the calculator does not release or populate the BOM. CAD values are fixed synthetic visualization inputs consumed by the calculator, not engineering selections.
- All gates are `UNRESOLVED`, with blank decision/signature/evidence fields. AI agents cannot accept a gate, inspect a physical condition, sign a record, authorize excavation or entry, or change the use classification.

## Relationship to OCE-CTL-01

OCE-CTL-01 remains a separate, unvalidated compact-track-loader concept. Its host-only simulation and synthetic energy assumptions can inform future planning research, but the current CTL is **not an excavator, hauler, compactor, concrete pump, lifting appliance, survey instrument, confined-space safety system, or certified autonomous construction fleet**. See the [fleet register](construction/fleet-register.csv). Any physical machine or autonomy work requires the existing [OCE release process](../../docs/validation-and-release.md) in addition to BUNKER-01 gates.

## Current status and next decisions

`siteKnown`, `constructionAuthorized`, and `physicalValidationPerformed` are all `false`. The owner must first resolve intended use, occupancy prohibition, jurisdiction/location handling, design life, dimensions, equipment loads, security, fire, water, power, communications, and budget with qualified advisers. Actual private address or coordinates must stay outside this public repository.

## Host-only calculator usage

From the repository root, run `PYTHONPATH=src python3 -m open_construction_equipment bunker --output-dir builds/bunker01 --json`, or run `oce bunker` after installation. Optional `--input`, `--work-breakdown`, `--quality-gates`, `--fleet-register`, and `--site-inputs` paths default to the canonical resources. The command writes deterministic `result.json` and self-contained `schedule.svg` under `builds/bunker01/`.

The default result is 109.5 m³ excavation, 17.6625 m³ gross concrete, 18.545625 m³ theoretical waste-adjusted concrete (not an order quantity), 57.0375 m³ geometric nominal compacted backfill, 136.875 m³ loose spoil, 57.65625 m³ excess loose haul-off bookkeeping, 62.95 m² net waterproofing, and 69.245 m² waste-adjusted waterproofing. The relative synthetic duration is 472 h with critical path `BW-001 → BW-002 → BW-003 → BW-005 → BW-006 → BW-007 → BW-008 → BW-010 → BW-011 → BW-012 → BW-013 → BW-014 → BW-015 → BW-016 → BW-018 → BW-019 → BW-020 → BW-021 → BW-022`. Eight selected energy assumptions sum to 246 kWh; 14 packages and BF-006 are explicitly unmodeled, not zero-energy. See [exact formulas and conventions](../../docs/bunker-planning.md).

These outputs are discussion, requirements refinement, and non-physical arithmetic only. They are not suitable for ordering, excavation, construction, autonomous operation, entry, occupancy, protective use, procurement, permitting, or safety decisions. Every result retains `constructionAuthorized:false`, `physicalValidationPerformed:false`, and `BLOCKED_UNRESOLVED_HUMAN_GATES`; no option can override that baseline.
