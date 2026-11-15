<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
**CONTROL TEMPLATE:** OCE-CTL-01 | Revision 0.0-concept | Status **UNRELEASED — DO NOT EXECUTE** | Unit applicability and effective date: TBD | Approvals: none.

Physical use requires a completed document-specific release signed by the named responsible engineer and quality/site authorities. Instructions below are sequence and evidence requirements, not authorization or fabrication parameters. Any `TBD`, missing prerequisite, unexpected condition or nonconformance is a **STOP/HOLD**. Agents may prepare records but cannot perform physical steps, inspect, load hardware, apply energy, sign gates, or substitute simulation for physical verification.

### Required evidence and acceptance rule
Record actual results with unit IDs, drawing/process revisions, personnel and qualification, dates, equipment IDs/calibration where applicable, raw evidence, deviations, NCRs and named reviewers. `OK` alone is not sufficient where measurable characteristics are required. Acceptance comes only from each referenced released specification; this template provides no numerical manufacturing settings.

# WI-080: Final commissioning and release-to-validation

## Scope and mandatory prerequisites

This is a **planning template for an on-site commissioning permit, not a start-up sequence**. It cannot be executed absent a physical machine and signed G4 permit. Required accepted unit genealogy, closed prior gates, approved exact configuration and test method, responsible engineering/commissioning lead, qualified HV/hydraulic/drive/control testers, trained emergency/site personnel, controlled exclusion and observation area, fire/spill/response resources, calibrated data acquisition, stop/recovery/LOTO methods, reviewed site weather/ground conditions and explicit residual-risk acceptance.

Commissioning needs distinct, separately signed permits for electrical energization, traction/motion and hydraulic/load stages; permission for one does not imply another. All targets (500 kg, 6 km/h etc.) are prohibited as automatic test settings. Tests begin with the smallest justified exposure defined by the approved plan, and a test must stop on unexpected movement, sensor fault, isolation/interlock defect, leak, thermal warning, tool/control communication anomaly or any unsafe condition.

## Controlled planning and execution flow

1. Verify physical configuration and as-built evidence against signed release, all guards/covers/labels/access/supports, attachment lock, service disconnect, braking/Load holding and independent protective chain. Inspect instruments and emergency arrangements in person.
2. Hold configuration/site briefing with named command authority, stop authority, observers, communications and retreat paths. No lone commissioning; no remote agent as safety observer.
3. Before any energy stage, establish LOTO transitions and zero-energy verification. Release only the authorized subsystem, then collect actual electrical states and protective responses per the approved test record.
4. Verify e-stops, interlocks, reset/no-restart, contactor/inhibit feedback and invalid/stale command response using staged test methods. Do not assume torque-off means safe or command ordinary software to certify the independent chain.
5. Conduct separate traction and hydraulic stages using only signed procedures. Establish parking/stopping and asymmetric-drive fault behavior before speed/stability exploration; verify unloaded implement/load holding and controlled lowering before any rated-load investigation.
6. After every stage, restore safe isolation where required, review raw measurements and deviations, and obtain the named hold-point release before continuing. Any design or configuration change triggers regression/safety review.
7. Finish by shutting down and isolating under approved conditions, recording stored-energy state, securing the unit and preserving incident/service information.

## Final gate and evidence

**H1:** physical unit/site/personnel readiness. **H2:** each discrete energy/motion/load stage. **H3 final:** named responsible engineer signs only a precisely bounded next activity or rejection after reviewing raw records, NCRs, residual risks and configuration. Passing commissioning is not production certification or autonomous authorization. No commissioning has occurred here; agents contribute no witness/inspection/release evidence.
