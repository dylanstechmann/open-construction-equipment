<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# ADR-0001: Battery-electric compact track loader reference

- **Status:** Proposed concept direction
- **Date:** 2026-11-15
- **Deciders:** Unassigned responsible engineering owner; this agent-drafted ADR is not signed approval

## Context

The project needs one bounded reference platform connecting mechanical, electrical, hydraulic, manufacturing, maintenance, and future supervised-autonomy learning. A compact track loader provides meaningful traction, stability, attachment, load-holding, access, and protective-structure problems. Its apparent simplicity must not hide substantial energy and worksite risk.

## Decision

Use **OCE-CTL-01**, a concept-only battery-electric compact track loader with dual electric traction drives, electro-hydraulic lift/tilt, a universal-style quick attach interface, manual controls, independent safety chain, and autonomy-ready data/sensing boundary. Initial nonbinding targets are approximately 2,200 kg operating mass, 500 kg ROC, 96 V nominal LFP around 30 kWh, two 15 kW traction motors, 10 kW hydraulic pump, 1.5 m width, and 6 km/h maximum manual travel. Every value remains an unvalidated target; no geometry or setting is released for manufacture.

## Alternatives considered

- **Battery-electric mini-excavator:** useful hydraulic case but adds swing, more complex stability and hose routing.
- **Diesel compact track loader:** mature reference architecture but introduces fuel, combustion, emissions, and additional thermal/noise systems not needed for this first learning platform.
- **Wheeled electric skid steer:** simpler driveline packaging but different ground-pressure, steering, tire, and stability problems.
- **Autonomy-first mobile platform:** lowers sensing/software scope ambiguity but would avoid core construction-machine load/hydraulic challenges.

## Consequences

Electric actuation supports separate traction/pump control and avoids engine integration, but HV/LV isolation, pack/BMS/charger safety, thermal propagation, EMC, braking and service disconnects become critical. Tracks require undercarriage durability, debris management, steering-load, track retention and towing analysis. Electro-hydraulics retains high-pressure fluid and suspended-load risks. “Universal-style” does not establish attachment compatibility; mass envelope, geometry, retention, couplings, and load moments require engineering.

## Required follow-up

Quantify duty cycles/ODD, attachments/load centers, stability and structural cases, energy/thermal balance, drive/braking faults, pump/valve/load holding, protective structures, access, and maintenance. Confirm targets only through signed analyses and applicable physical evidence. If constraints invalidate electric CTL feasibility, revise this ADR rather than silently preserving targets.
