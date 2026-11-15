<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
**OCE-CTL-01 CONTROLLED SERVICE TEMPLATE | Revision 0.0-concept | UNRELEASED — DO NOT EXECUTE | Approvals: none | Exact unit/configuration: TBD.**

This is not an OEM manual or authorization to approach/service a machine. Future physical use requires a signed responsible-engineering/service release, applicable law/site procedures, exact released machine documentation, qualified personnel, approved tooling, and recorded evidence. Intervals are proposed unless an actual released OEM/regulatory source is recorded. Stop for any unexpected condition or `TBD`; never assume a conventional value.

Agents cannot perform physical operations, zero-energy checks, inspections, controller loads, tests, or approvals. Never defeat an e-stop, guard, interlock, sensor, BMS or load-control device. Return to service requires PR-008 and only restores the previously authorized limited configuration/scope after actual evidence and named human review.

# PR-003: Traction battery and charging service

## Scope and competence

Qualified HV/battery personnel only, with exact pack/BMS/charger manuals, site damaged-battery/fire plan, approved lifting pack support, LOTO/zero-energy procedure, suitable arc/shock protection and tools/instruments. No cell/module replacement, pack internals, programming or charging profile work is released by this document.

Heat, smoke, hissing, gas/odor, swelling, electrolyte release, collision/water damage or rapidly worsening BMS alarms require immediate site emergency/isolation specialist response, not closer inspection or charging. LFP chemistry does not remove thermal runaway or toxic-gas hazards.

## De-energized inspection pathway

1. Verify pack identity, storage/transport/service history and exact configuration. Review logs without clearing faults; distinguish BMS warnings from physically verified isolation.
2. Complete PR-002 including charger and LV sources, interlock/backfeed paths, DC link/capacitor discharge and measurement proving checks. Keep hazardous areas controlled even after measurement zero due to possible damaged cells or alternate sources.
3. Externally inspect authorized-access enclosure, mount/restraint, seals, connectors, insulation, interlock and cooling system for damage/contamination/corrosion using released criteria. Record actual observations; do not open sealed modules without separate engineering instruction.
4. Perform only the approved bonding/insulation/thermal/contactors/isolation checks with suitable calibrated equipment. Test voltage/method must protect electronics and derive from release, never a generic meter or insulation-test setting.
5. For approved mechanical part service make no assumption that component removal isolates all live portions. Maintain pack mass/CG support and cell/terminal short-circuit prevention per exact pack procedure.
6. Battery-control firmware/configuration has separate hardware-authorized requirements. Agents never flash controllers. An authorized specialist performs signed readback and independent BMS/vehicle/charger compatibility verification.
7. Reinstall barriers, disconnect/interlock/labels/coolant and mounting evidence before closure. Treat any temporary test lead or disconnected interlock as an open hold.

## Return and records

PR-008 plus responsible HV review requires actual measured results, exact cells/module/pack/charger/firmware identities and history, environ/conditions, pack support/lift/joint records and safety tests. Charging resumption is a separate approved controlled check with travel/charger interlock and compatible validated charger; never retry damaged-pack charging to determine if it works. Waste/transport/disposal involves qualified applicable channels, not ordinary scrap or electrical-waste handling.
