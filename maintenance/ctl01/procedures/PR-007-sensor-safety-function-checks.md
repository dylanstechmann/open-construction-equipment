<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
**OCE-CTL-01 CONTROLLED SERVICE TEMPLATE | Revision 0.0-concept | UNRELEASED — DO NOT EXECUTE | Approvals: none | Exact unit/configuration: TBD.**

This is not an OEM manual or authorization to approach/service a machine. Future physical use requires a signed responsible-engineering/service release, applicable law/site procedures, exact released machine documentation, qualified personnel, approved tooling, and recorded evidence. Intervals are proposed unless an actual released OEM/regulatory source is recorded. Stop for any unexpected condition or `TBD`; never assume a conventional value.

Agents cannot perform physical operations, zero-energy checks, inspections, controller loads, tests, or approvals. Never defeat an e-stop, guard, interlock, sensor, BMS or load-control device. Return to service requires PR-008 and only restores the previously authorized limited configuration/scope after actual evidence and named human review.

# PR-007: Sensors and safety-function checks

## Scope and competence

Qualified controls/electrical/functional-safety staff only, under exact SRS and released test procedure. Technician tasks include approved calibrated sensor checks, independent channel/wiring review and actual functional response tests. This is not permission to actuate machinery: de-energized, bench, restrained or operational stages require their specific G4/G5 authorization and site controls.

There are no current calibrated scaling factors, timeouts, stop distances, accepted PL/SIL or fault-code thresholds. Never create them for a service test. Keep the research/autonomy interface physically disabled; sim-only software is not safety evidence. Agents cannot administer physical fault injection or flash devices.

## Controlled plan and sequence

1. Verify unit, sensor and safety-device identities, hardware/software/config revisions, calibration status and previous faults. Review which functions are safety-related, required safe states and independent paths against the current SRS.
2. Establish PR-002 or the separately approved controlled test state with bystanders outside every movement/load/electrical hazard. Inventory test equipment and temporary signals; no operational interlock bypass.
3. Perform physical inspection of mounts, alignment, mechanical linkages, connectors/seals, cable routing, protective devices, e-stops, contactors/actuator inhibits and guards before electrical diagnostics.
4. Use calibrated references and released methods to compare sensor output/scaling across required operating points, record actual input and output/uncertainty, and verify friction/stiction/mechanical drift where relevant. Do not adjust to match an expected display without documented cause and calibration.
5. Exercise each safety function and channel/fault combination as specified: e-stop, access/presence/charger interlocks, neutral/start, invalid/stale input, one drive fail, supply loss, contactor mismatch and load-control interactions. Record the **actual physical response/timing** by approved measurement, not just a fault log.
6. Verify reset requires healthy prerequisite and deliberate action and never causes movement by itself. Verify software/autonomy messages cannot supersede protection and safe braking/load holding are established for each relevant state.
7. Restore all leads, covers, config write protection and diagnostic ports; independently compare final readback and calibrations to source. An alarm silence or successful self-test is insufficient.

## Return gate

PR-008 plus functional-safety approval defines any regression after sensor, wiring, brake/drive, hydraulic, BMS, device or firmware changes. Record expected criterion source, actual result, units/time base, instrument IDs, conditions, raw traces, config and named reviewer. Any unexplained failure keeps the unit isolated.
