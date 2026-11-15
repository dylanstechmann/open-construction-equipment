<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# OCE-CTL-01 concept system architecture

## Intent and boundaries

OCE-CTL-01 is a manual-first electric compact track loader concept. The onboard protective chain must remove/inhibit hazardous actuator power and establish a reviewed safe response independently of the autonomy computer, cameras, network links, and ordinary application software. No exact safe state is assumed globally: traction, steering, lift holding, and electrical isolation require separate fault analysis.

```text
Operator controls ──────► Vehicle control unit ─────► Traction inverters ─► Left/right drives
       │                         │                    Hydraulic controller ─► Pump/valves
       │                         │                                               │
Emergency/protective devices ────┼──► Independent safety chain ─► safety-rated inhibit/contactors
       │                         │             │                                  │
       └──────── manual reset ───┘             └── status only ─► ordinary computers

Sensors ─► acquisition/gateway ─► ordinary vehicle network ─► supervisory/autonomy research (sim only)
Battery/BMS ─► independent protective limits and HV coordination ─► HV distribution
```

The diagram expresses functional independence, not a released circuit, wire implementation, or safety rating. The safety chain may monitor status from ordinary systems only where independence/fault tolerance is demonstrated. No command from autonomy shall overpower e-stop, protective limits, interlocks, or manual mode arbitration.

## Subsystems

- **Structure/interfaces:** chassis, undercarriage mounts, lift-arm pivots, guarded operator zone, future ROPS/FOPS design activity, service supports, engineered lifting/tie-down points, universal-style quick attach.
- **Traction:** two electric drives/inverters, final drives, tracks, braking/holding strategy, speed/direction command plausibility.
- **Energy:** LFP pack target, service disconnect, BMS, protective disconnects, precharge/distribution, charging, thermal conditioning, low-voltage supply.
- **Hydraulics:** motor/pump, reservoir/filtration/cooling, directional and load-control functions, lift/tilt cylinders, auxiliary circuit if later approved.
- **Control:** manual input devices, ordinary vehicle control, dedicated protective devices/logic, active/inactive state management, diagnostics and event logging.
- **Autonomy-ready interfaces:** time-stamped sensing and actuator command *boundary*, isolated from protective functions. Mechanical compute/sensor mounting and EMC/ingress requirements are TBD; “autonomy-ready” is an interface aspiration, not capability.

## Command and state model (proposal)

`DISABLED → ISOLATION_CHECKS → MANUAL_READY ↔ MANUAL_ACTIVE → CONTROLLED_STOP → DISABLED`, plus a latched `FAULT` path. Transitions, permitted motion, braking/load holding, and reset prerequisites require engineering. An e-stop or safety fault shall inhibit movement as required by its validated function and require deliberate reset; reset must not itself restart motion. Normal start requires intentional commands and permissives. Autonomy has no physical-operating state in this phase.

## Interface rules

- Every command has units, sign convention, valid range/TBD limit, freshness, timeout, source identity, and state-dependent permission before software implementation.
- Left/right and lift/tilt signs are consistent across I/O, CAD, logs, and service procedures.
- Software receives protective status but cannot self-certify it. Hardwired/rated safety paths are selected from safety design evidence.
- Energy isolation, service supports, and access controls are physical controls, not only HMI messages.
- Attachment mass/inertia/dimensions and hydraulic/electrical connections are interface inputs; no third-party interchangeability claim exists.

## Architectural decisions to resolve

Manual brake architecture, safe response to single drive faults, valve spool centers and load-holding behavior, safety controller versus hardwired relay logic, protective sensor redundancy, network partitioning, HV/LV separation, charger interlocks, recovery behavior, event retention, and cybersecurity are all TBD. Record outcomes in new ADRs and trace them to `SR-*`, `HZ-*`, and interface IDs.
