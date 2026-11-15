<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
**OCE-CTL-01 CONTROLLED SERVICE TEMPLATE | Revision 0.0-concept | UNRELEASED — DO NOT EXECUTE | Approvals: none | Exact unit/configuration: TBD.**

This is not an OEM manual or authorization to approach/service a machine. Future physical use requires a signed responsible-engineering/service release, applicable law/site procedures, exact released machine documentation, qualified personnel, approved tooling, and recorded evidence. Intervals are proposed unless an actual released OEM/regulatory source is recorded. Stop for any unexpected condition or `TBD`; never assume a conventional value.

Agents cannot perform physical operations, zero-energy checks, inspections, controller loads, tests, or approvals. Never defeat an e-stop, guard, interlock, sensor, BMS or load-control device. Return to service requires PR-008 and only restores the previously authorized limited configuration/scope after actual evidence and named human review.

# PR-008: Post-service return-to-service

## Purpose and prerequisites

A qualified review gate after **every** service intervention, even when no fault was found. Return can only restore a specific unit to its previously authorized limited state; it cannot approve a new machine, attachment, operating domain, load/speed rating, software function, repair design, or autonomy. Those require the applicable engineering/release gates.

The lead reviewer must have exact work order, unit genealogy, configuration deviations/NCRs, released limits, qualified staff/test records, physical access and independence appropriate to risk. An AI-generated checklist or completed repository JSON never constitutes review.

## Completion flow

1. Reconcile work requested versus work actually performed plus discovered conditions. Record all removed/replaced/repaired components by ID/lot, actual calibrated torque/fit/electrical/hydraulic/cleanliness measurements and old/new software configuration where applicable.
2. Inspect that all required tasks are complete and no open NCR/concession lacks explicit authorized disposition. There must be no original cause merely hidden by reset, cleaning, charging or replacement.
3. Account for every tool, lockout device per site policy, cap, fastener, test lead, bypass, temporary jumper/hose, support and removed guard. Remove service items only at the authorized restoration stage and verify protective devices are reinstated; no interlock is left defeated.
4. Inspect structural retention, brake/holding, pack/HV enclosures and service disconnects, LV/HV connections and fuses, hydraulic fittings/guards/fluid levels/cleanliness, quick attachment/arm supports, tracks, labels and access equipment. Validate all actual joint values against released criteria using calibrated tools where specified.
5. Conduct the exact risk-assessed post-service test scope with controlled site/permit: no-restart/neutral, e-stops/interlocks, independent channels, brake/traction, hydraulic load holding/controlled lower, sensor calibration, charger inhibition and alarms. Repeat affected regression tests for any part/configuration substitution.
6. If any test or inspection fails, stop, restore the appropriate isolation/LOTO and reopen NCR/work order. Do not release a “monitor only” known safety issue without competent documented risk and release process.
7. Update unit configuration, maintenance due basis and retained raw evidence independently; do not erase earlier operating hours or history to accommodate late work. Preserve original observations and append signed corrections.

## Authorized release record

A named qualified service reviewer—and responsible engineer for safety/design/configuration changes—signs actual scope, machine/unit ID, current configuration, evidence references, conditions/limitations, next service obligations and date/time. Return authorization `false` remains until those approvals exist. Notify responsible operators/site only after locks/exclusion are formally managed and communication is complete.

Minimum status words stay explicit: physical `inspected` / `measured` evidence exists separately; `reviewed` identifies reviewer and exact scope; `released` means only a stated activity. No simulation, merged record or prior approval can be substituted for these actual human checks.
