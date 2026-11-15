<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Validation, evidence, and release

No automated check can validate heavy machinery. Repository tests validate file behavior or structured content only. The following gates govern future, separately authorized work.

## Evidence records

Each engineering result shall identify its stable ID, machine configuration/revision, objective, method, inputs and uncertainties, raw-data location and integrity, units, tool/script version for analyses, personnel and competence where physical work is involved, calibrated instrument IDs/due dates, environmental/site conditions, deviations, and conclusion. Reviewer name/signature/date/scope and unresolved actions are mandatory for a reviewed result.

AI-generated calculations, plans, and test scripts are unreviewed assistance. They cannot be evidence of inspection, signed owner approval, component conformity, or field safety. Screenshots without raw records and prose that says “tested” without data are insufficient.

## Gates

| Gate | Allowed next activity | Minimum signed acceptance (not currently met) |
|---|---|---|
| G0 concept baseline | Calculations, requirements and simulation only | Owner confirms scope, target/assumption status, source/licensing, open hazards |
| G1 engineering definition | Procure controlled bench/prototype items; no assembly authorization | Approved requirements, current standards matrix, hazard reduction, calculations, drawings/schematics, interfaces, verification plans, safety requirements |
| G2 component/bench | Controlled component tests by qualified staff | Supplier/incoming evidence, calibrated setup, bench risk assessment, approved test procedures and reviewed results; NCR disposition |
| G3 prototype manufacture | Build identified unit under released instructions | Qualified organization/personnel, material and weld/WPS/PQR controls, torque/cleanliness/HV/hydraulic plans, traceability and inspection authorization |
| G4 restricted commissioning | Energize/commission per a specific approved sequence | Completed physical inspections, isolation/stored-energy controls, precharge/HV/hydraulic plans, guarded area, emergency arrangements and signed commissioning permit |
| G5 manual operational validation | Approved unoccupied/restricted then occupied manual tests as separately legal and safe | Site/ODD approval, stability/protective structures/braking/lifting/manual controls/e-stop evidence, emergency response, trained operators, residual-risk acceptance |
| G6 research autonomy bench/simulation | Software-in-loop/hardware-in-loop without hazardous motion | Validated simulator limits, independent safety path, fault injection, command freshness/limits, revised hazard analysis |
| G7 physical autonomy trial | Only a specifically bounded test configuration | New standards/legal assessment, independent safety validation, geofence/ODD/site plan, remote/local protective functions, contingency and human authorization; prior manual release alone is insufficient |
| Maintenance return | Return only the serviced unit to its previously authorized limited state | Closed work order, zero-energy work completion, guards/interlocks restored, calibrated function checks where required, qualified reviewer sign-off |

Passing a gate does not pass later gates or authorize another configuration. A failed test stops progression; disposition and regression scope are reviewed.

## Verification methods and claims

Use inspection, analysis, simulation, demonstration, and test explicitly. A model correlation plan must accompany simulation relied upon for physical decisions. Label uncertainty, invalid ranges, negative results, and untested conditions. Releases name exact hardware/software/document revisions and limited permitted activity; they do not imply production readiness or broad certification.

## Change and release control

Review every change to structure, cell/module, BMS, drive, hydraulic component, hose routing, fastener class, safety I/O, limits, firmware, perception, attachment, material, process, or service interval for safety impact. Major changes require hazard reassessment and potentially repeat earlier gates. A release bundle includes configuration index, BoM/drawings, instructions, risk/safety case, verification matrix, NCRs/deviations, manuals, calibration and sign-offs. No such bundle exists now.

## Limits of agent activity

Agents can prepare versioned documents and run non-physical software checks only. They cannot permit their own designs to progress, witness fabrication, apply a physical tag, sign a record, inspect an isolation, verify zero energy, or conduct a field trial. Human approval must not be inferred from silence or a merged pull request.
