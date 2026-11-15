<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# OCE-CTL-01 pre-release safety case

**Status:** preliminary argument structure; no claim has been demonstrated and no safety integrity level, performance level, or certification has been assigned.

**Primary safety claim:** before any OCE-CTL-01 machine is operated, a competent responsible engineering team shall demonstrate, using current requirements and objective evidence, that risks have been reduced as far as required by the applicable jurisdiction and that no unacceptable residual risk remains. This claim is **open**.

## Scope and limits

The concept includes battery charging/storage, manual travel and steering, dual traction drives, electro-hydraulic lift/tilt, a universal-style quick attach, normal servicing, transport/support, foreseeable misuse, and eventual research autonomy. Autonomy is limited to simulation in this phase. No operational, emergency-response, road-use, lifting-personnel, demolition, explosive-atmosphere, or carrying-people use case is authorized.

The machine is not considered safe merely because it is electric, low-speed, sensor-equipped, manually operable, or equipped with an emergency stop. Stored electrical/hydraulic/gravitational energy, fire, runaway motion, dropping loads, crush zones, and unstable attachments remain hazards.

## Argument and required evidence

| Claim ID | Safety argument element | Evidence required before acceptance | Current state |
|---|---|---|---|
| SC-01 | Intended use and reasonably foreseeable misuse are bounded | Signed operational design domain, user/service analysis, site/jurisdiction review | Open; narrative only |
| SC-02 | Hazards are systematically identified and traceable | Reviewed risk assessment using applicable ISO 12100 process; severity/exposure/avoidance rationale; `HZ-*` coverage | Open; seed register only |
| SC-03 | Inherently safe design is prioritized over controls and warnings | Calculations and design reviews for stability, structure, braking, containment, access, isolation, and attachment retention | Open |
| SC-04 | Every safety function has allocated requirements independent of supervisory autonomy | Function definitions, safe states, demand rates, systematic capability and PLr/SIL rationale where applicable, fault analysis, architecture and independence review | Open; `SR-*` proposals only |
| SC-05 | Manual and emergency protective functions remain effective on autonomy/sensor/computer faults | Independently reviewed schematics, interface FMEA, wired/safety-rated architecture evidence and fault-injection tests | Open |
| SC-06 | Structural and stability risks are controlled | Released load cases; material/weld substantiation; ROPS/FOPS evaluation and test where applicable; static/dynamic stability and retention evidence | Open |
| SC-07 | Electrical energy and charging risks are controlled | Cell-to-pack review, BMS failure analysis, isolation/contactors/precharge/interlocks, protective earthing, enclosure, thermal propagation, charger and emergency-response evidence | Open |
| SC-08 | Hydraulic/gravitational energy cannot cause unacceptable movement or exposure | Hose routing/burst assessment, load-holding/lowering behavior, cleanliness/material compatibility, guarded pressure testing, supported raised-arm service design evidence | Open |
| SC-09 | Manufacturing preserves design intent | Approved drawings/WPS/PQR/weld maps, qualified personnel, calibrated tools, incoming/process inspection, NCR closure and unit traceability | Open; templates only |
| SC-10 | Service maintains the safety case | Approved OEM-like manual derived from released design, LOTO/stored-energy verification, diagnostic and periodic function tests, records | Open; proposed procedures |
| SC-11 | Residual risk and warnings are acceptable and communicated | Residual-risk review, labels/manual/access design evidence, training/competence and PPE analysis | Open |
| SC-12 | Lifecycle changes and field feedback cannot silently invalidate safety | Configuration/change control, incident reporting, service evidence, reapproval triggers | Open |

## Minimum strategy

1. Identify current legal and consensus-standard requirements with qualified specialists. See `standards-register.md`; do not infer compliance from its presence.
2. Reduce hazards by design before adding protective control devices or information for use.
3. Implement an e-stop/isolation/protective chain independent from ordinary computing and autonomy, with a defined safe state and manual reset behavior. Exact architecture and safety ratings are TBD.
4. Keep the traction and hydraulic actuators inhibited until manual mode, permissives, and the protective chain are healthy. Never use a software “ready” flag as the only protection.
5. Decouple supervisory autonomy from safety implementation and require a separate hazard analysis before physical autonomy research.
6. Validate progressively in simulation, component/bench conditions, restrained and unoccupied test arrangements, then approved manual-machine testing. Gate every transition.

## Residual-risk and emergency considerations

A future manual must address safe charging location, damaged/thermal-event battery isolation, fire response based on responsible fire-safety advice, load/arm support, lockout at every energy source, recovery/towing, attachment security, slopes/terrain, bystanders, reduced visibility, and defeat-resistant interlocks. It must not prescribe universal emergency actions without competent review of the final battery and site design.

## Safety-case ownership

Only an identified responsible engineering owner may accept this safety case. Each accepted claim needs evidence references, versions, reviewers, dates, limitations, and unresolved actions. AI agents may draft mappings and analyze supplied evidence but cannot approve risk, physically inspect anything, or sign a claim.
