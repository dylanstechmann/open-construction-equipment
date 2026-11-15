<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
**CONTROL TEMPLATE:** OCE-CTL-01 | Revision 0.0-concept | Status **UNRELEASED — DO NOT EXECUTE** | Unit applicability and effective date: TBD | Approvals: none.

Physical use requires a completed document-specific release signed by the named responsible engineer and quality/site authorities. Instructions below are sequence and evidence requirements, not authorization or fabrication parameters. Any `TBD`, missing prerequisite, unexpected condition or nonconformance is a **STOP/HOLD**. Agents may prepare records but cannot perform physical steps, inspect, load hardware, apply energy, sign gates, or substitute simulation for physical verification.

### Required evidence and acceptance rule
Record actual results with unit IDs, drawing/process revisions, personnel and qualification, dates, equipment IDs/calibration where applicable, raw evidence, deviations, NCRs and named reviewers. `OK` alone is not sufficient where measurable characteristics are required. Acceptance comes only from each referenced released specification; this template provides no numerical manufacturing settings.

# WI-070: Future software loading and configuration

## Scope and mandatory prerequisites

Template for a later authorized controls engineer/technician and independent verifier. **Only simulation-only host reference software exists; no validated physical control/firmware load package exists, and agents are forbidden from flashing controllers or powering equipment.** Physical work requires approved software release, exact controller/inverter/BMS/safety-device hardware compatibility and supplier programming instructions, separate bench/commissioning risk assessment, physical isolation of actuators as designed, cybersecurity/access control, backup/recovery and an immutable package manifest with hashes/config schema.

A simulation result cannot approve firmware/config. Parameters including drive/brake limits, speed maps, command timeouts, hydraulic limits, BMS limits, interlocks, sensor scaling, safety logic and network IDs must be independently controlled engineering values rather than copied concept targets. The protective chain must not depend on a GUI or firmware self-test alone.

## Controlled sequence — after separate human authorization only

1. Verify unit/device serials and hardware/revision compatibility against the released manifest. Record configuration before changes, with rollback and service replacement process.
2. Establish the approved safe physical state under an isolation/motion permit, control area access and verify independent protective paths are in their required test state without operational bypass.
3. Authorized staff validate package source, signatures/hashes offline, programmer/tool version and write-access control; preserve an auditable session identity without logging credentials.
4. Load only using the separately released device supplier procedure. Never act on agent-initiated commands; abort communications or identity anomalies without improvised cycling of machine power.
5. Read back and independently verify controller identity, package/hash, parameter set/schema and calibration values against signed source. Unreadable devices require additional controlled evidence, not assumed success.
6. Execute de-energized/bench checks of I/O mapping, sensor validity, neutral, stale data, reset/no restart and command plausibility before any staged actuator permit. Verify no invalid physical autonomy command path.
7. Independent reviewer closes commissioning prerequisites and returns the physical configuration to its controlled state.

## Gates and retained records

**H1:** exact human-authorized package/device/safe setup. **H2:** independent readback and configuration acceptance. **H3:** separate motion/energization permit with physical inspection. Record immutable package, device, old/new config, calibration, actual results, authorized performer/witness, NCRs and final responsible controls/safety sign-off. No loading is performed or claimed in this repository phase.
