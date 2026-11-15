<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# OCE-CTL-01 preliminary interface control document

All interfaces are conceptual and controlled by `IF-*` entries. Numeric targets are initial AI-authored values with owner review pending, not owner-supplied requirements; unresolved values are TBD. This is not a supplier drawing, mating-attachment guarantee, harness pinout, or hydraulic port specification.

| ID | Boundary | Provider → consumer | Concept content | Verification required / status |
|---|---|---|---|---|
| IF-MEC-001 | Chassis ↔ track module | Structure ↔ undercarriage | Reaction loads, alignment, retention, removal | Load cases, tolerances, braking/shock loads and drawing TBD |
| IF-MEC-002 | Chassis ↔ lift-arm pivots | Chassis ↔ arms | Reactions, synchronized motion, retention, lubrication | Fatigue/wear/joint analysis and geometry TBD |
| IF-MEC-003 | Arms ↔ quick attach | Loader ↔ coupler | Attachment moment, engagement/retention, access | Geometry, retention and misuse verification TBD; no compatibility claim |
| IF-MEC-004 | Coupler ↔ attachment | Coupler ↔ attachment | Mass/CG/inertia envelope and mechanical lock | Each attachment requires assessed ICD; all TBD |
| IF-MEC-005 | Battery enclosure ↔ chassis | Pack ↔ structure | Restraint, lifting, isolation, thermal separation, impact | Pack and mount review TBD |
| IF-MEC-006 | Operator zone ↔ body | Structure ↔ operator | ROPS/FOPS, restraint, access, visibility, guards | Qualified protective-system/human-factors engineering TBD |
| IF-MEC-007 | Raised arms ↔ service support | Arms ↔ support fixture | Positive support independent of hydraulics | Rated support design and procedure TBD |
| IF-HV-001 | Pack ↔ HV distribution | BMS/pack ↔ contactor box | Limits, isolation, interlock, precharge | Complete HV schematic, protection and FMEA TBD |
| IF-HV-002 | HV distribution ↔ traction drives | PDU ↔ two inverters | Power, discharge, enable/inhibit | Protection/braking and independence review TBD |
| IF-HV-003 | HV distribution ↔ pump inverter | PDU ↔ hydraulic drive | Pump power and protective inhibit | Duty, regeneration and safety response TBD |
| IF-HV-004 | Charger ↔ pack | External equipment ↔ pack | Communication, isolation, interlocks, connector/environment | Charger/site review TBD |
| IF-LV-001 | HV system ↔ LV supply | DC/DC ↔ LV bus | Regulated supply, isolation, bonding, backup safety loads | Load and loss-of-supply analysis TBD |
| IF-LV-002 | Manual controls ↔ VCU | Operator ↔ control | Diagnostic requests, neutral/presence | Pinout/ranges/freshness/stopping requirements TBD |
| IF-SAF-001 | Protective devices ↔ safety chain | E-stop/interlocks ↔ outputs | Independent monitored protective path/manual reset | Safety requirements specification and validation TBD |
| IF-SAF-002 | Safety chain ↔ power actuators | Protective logic ↔ drives/contactors/valves | Required safe response per state | Safe-state, fault and restart tests TBD |
| IF-DAT-001 | Sensors ↔ ordinary control | Acquisition ↔ VCU | Timestamped state, identity, units, range, validity | Communication matrix/fault response TBD |
| IF-DAT-002 | Ordinary control ↔ research software | VCU ↔ sim subscriber | Read-only telemetry initially; synthetic commands only | No physical autonomy channel authorized |
| IF-HYD-001 | Pump group ↔ valve assembly | Pump/tank ↔ valves | Pressure/return flow, filtration, thermal conditions | Circuit and duty analysis TBD |
| IF-HYD-002 | Valve/load controls ↔ lift cylinders | Valves ↔ lift actuator | Raise/lower, load holding, trapped pressure | Hose-burst/descent and isolation validation TBD |
| IF-HYD-003 | Valve/load controls ↔ tilt cylinders | Valves ↔ tilt actuation | Curl/dump and load retention | Circuit/geometry/load analysis TBD |
| IF-THM-001 | Heat sources ↔ cooling | Battery/drives/hydraulics ↔ cooling | Heat loads, fluid boundaries, environment limits | Thermal architecture/fault strategy TBD |
| IF-SRV-001 | Machine ↔ service equipment | Isolation/test ports ↔ tools | Controlled isolation, zero-energy checks, diagnostics | Qualified service design/released procedure TBD |

## Coordinate and change conventions

Origin, axes, signs, datums, message IDs and units must be assigned before detailed design. Documentation uses descriptive left/right from the seated operator only as a proposal, not a software contract. Interface changes require hazard analysis plus updates to design inputs, registers, CAD, manufacturing and maintenance artifacts. No physical interface may be inferred from visual OpenSCAD alignment.
