<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
**CONTROL TEMPLATE:** OCE-CTL-01 | Revision 0.0-concept | Status **UNRELEASED — DO NOT EXECUTE** | Unit applicability and effective date: TBD | Approvals: none.

Physical use requires a completed document-specific release signed by the named responsible engineer and quality/site authorities. Instructions below are sequence and evidence requirements, not authorization or fabrication parameters. Any `TBD`, missing prerequisite, unexpected condition or nonconformance is a **STOP/HOLD**. Agents may prepare records but cannot perform physical steps, inspect, load hardware, apply energy, sign gates, or substitute simulation for physical verification.

### Required evidence and acceptance rule
Record actual results with unit IDs, drawing/process revisions, personnel and qualification, dates, equipment IDs/calibration where applicable, raw evidence, deviations, NCRs and named reviewers. `OK` alone is not sufficient where measurable characteristics are required. Acceptance comes only from each referenced released specification; this template provides no numerical manufacturing settings.

# WI-050: LV and protective-circuit harness

## Scope and mandatory prerequisites

Covers future harness fabrication, routing and de-energized checks after release of complete schematics, pinout, communication and wire schedules. Required exact connector/conductor/terminal family with supplier tooling, insulation and environmental ratings, branch protection, circuit segregation, safety chain independence, mirrored assembly-perspective drawings, calibrated continuity/bonding/appropriate test instruments and trained harness/electrical technicians.

All lengths, gauges, terminal crimps, shield termination, fuse values, splice methods, connector keys/pins, seal plugs, clips, clearances, bend radii and test limits are TBD until release. Functional IO/harness registers alone are not a build package.

## Controlled sequence

1. Verify source authenticity, component/lot identity and pinout revision. Independently reconcile safety device channels and protected outputs with SRS; ordinary network status cannot substitute for a protective path.
2. Build on a controlled board from the released wire schedule using matched terminal tools and approved workmanship inspections. Preserve labels at both ends and maintain branch/fuse/segregation identity.
3. Record required crimp/terminal verification results, tool/die and lots. Do not untwist, resolder, splice or replace conductors without applicable released instructions.
4. Route with HV/LV/safety segregation, hydraulic/heat/abrasion clearances, strain relief, drip/ingress control and service access. Preserve moving-arm/track/steering clearances throughout designed motion (later verified under approved conditions).
5. Perform all released de-energized point-to-point, unintended connection, shield/bond and isolation checks. Record actual results by circuit, not a green self-test only. Connector-dependent sensitive electronics are disconnected unless an approved test says otherwise.
6. Verify interlock and protective-chain circuits pin-for-pin against independent review; temporary simulator loads and functional tests are confined to an approved bench procedure.
7. Secure, cap/close housings and inspect for tools/debris. Energization remains a separate hold.

## Gates and retained records

**H1:** released harness design/source/tooling. **H2:** fabrication workmanship and terminal evidence. **H3:** installed routing and 100% required electrical records before system connection/energization. Retain wire/harness serial/revision, lots, actual test values, instrument calibration, physical inspection/photos, NCR/rework and electrical/functional-safety sign-off.
