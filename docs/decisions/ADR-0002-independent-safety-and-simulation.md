<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# ADR-0002: Independent safety chain and sim-only software boundary

- **Status:** Proposed safety architecture boundary
- **Date:** 2026-11-15
- **Deciders:** Unassigned responsible functional-safety owner; unsigned agent-drafted decision

## Context

Future autonomy and ordinary vehicle software can crash, misperceive, lose timing, receive corrupt messages, or be modified. These faults cannot be allowed to disable emergency/protective functions. Simulations also can produce plausible but unsafe conclusions if their limited fidelity is mistaken for validation. Manual-first machinery needs explicit command and energy boundaries.

## Decision

1. Provide an independent protective/e-stop chain controlling appropriately engineered actuator inhibit/isolation devices. It shall not depend on autonomy computers, cameras, main application software, or a network message to perform its protective action. Implementation, diagnostics, safety ratings, safe state per function, and reset are TBD through risk assessment.
2. Manual driving/lifting is the only contemplated physical operating mode. Ordinary/manual controls can share defined acquisition paths only after independence and fault analysis; protective action does not rely on the HMI.
3. Autonomy receives status and sensor data through bounded interfaces. Its commands cannot override interlocks or safety actions, and absence/invalidity cannot silently enable motion. There shall be no automatic restart after protective reset.
4. All autonomy work in the current phase is simulation-only. Passing tests or simulated fault injection does not constitute hardware validation or authorization to flash/energize a machine. Physical autonomy requires the later G7 gate and a new hazard/standards/site review.

## Alternatives considered

- **Software-only safety supervisor:** rejected because common computing/software faults could remove both motion control and protection.
- **Network-connected autonomy as master:** rejected as the protective architecture; status integration remains useful but not sufficient for protection.
- **Full physical autonomy immediately:** rejected because foundational hazards, machine validation, ODD and safety functions remain open.
- **Bonded manual/autonomy controller:** deferred unless independence and common-cause requirements can still be demonstrated.

## Consequences and limits

More disconnect/inhibit devices, safety I/O, wiring, diagnostics, fault analysis, and testing are needed. De-energization alone may cause rolling or load dropping, so braking/load holding and residual energy must be engineered. Independent chains do not remove common-cause electrical/mechanical hazards automatically. Cybersecurity, diagnostic coverage, response times, safe manual degradation, and recovery behavior require detailed design.

Agents cannot execute physical validation, firmware flashing or controller changes. The repository will not label physical autonomy “supported” on the basis of software presence or simulation evidence.
