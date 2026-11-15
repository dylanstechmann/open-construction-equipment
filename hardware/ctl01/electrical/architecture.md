<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Electrical and controls architecture — OCE-CTL-01

## Unreleased concept

A 96 V nominal LFP battery around 30 kWh is the target energy source. Dual traction inverters and one hydraulic-pump inverter are supplied through protected HV distribution. An isolated LV system supplies manual controls, safety devices, sensors, contactor control, lighting and compute interfaces. Charger, DC/DC, BMS, thermal management and service disconnect integration are TBD.

Treat the pack and connected distribution as hazardous HV. Nominal voltage alone does not define shock/arc risk or legal classification. Pack internal arrangement, operating limits, insulation/isolation strategy, contactor coordination, earthing/bonding, precharge, discharge time, creepage/clearance, short-circuit protection, enclosure, fire propagation and emergency response are open.

## Functional partitions

- **Energy protection:** cell/module sensing and BMS protection, independently engineered pack disconnect strategy, service isolation, fault containment, charger handshake and secure enclosure.
- **Actuator power:** left/right traction drives, hydraulic pump drive; regenerative/dynamic/friction braking and parked-load behavior require analysis.
- **Manual control:** deliberate operator presence/start inputs, neutral controls, direction/speed requests and lift/tilt requests. Every request is state-limited and subject to independent protective inhibits.
- **Independent safety chain:** e-stops and other risk-assessment-selected devices, safety logic, monitored outputs, contactor/torque-inhibit channels, manual reset and diagnostics. No relay/controller selection or PL/SIL is claimed.
- **LV/data:** fused branches, control network, ordinary diagnostics, sensing gateway and future simulation/autonomy data. Network availability is not the sole protective mechanism.
- **Compute/sensing reserve:** guarded supply and mount provisions only; no perception coverage, reliability, or autonomous capability is implied.

## Required electrical evidence

Current/safety analysis, complete HV/LV schematics, bonding, protection selectivity, fault tree/FMEA, HVIL strategy, conductor/fuse/contactor calculations, insulation and discharge verification, EMC/environmental validation, charger coordination, connector keying and service access must precede release. Regeneration and loss of one traction channel must not produce uncontrolled steering or loss of required stopping.

## Harness and I/O

`io-map.csv` and `harness-register.csv` define functional labels, not pinouts or fabrication details. Connector family/pins, conductor sizes, insulation/fuse ratings, shielding, lengths, clips, bend radii, sealing, splice methods and terminal torques are TBD. No harness may be built from these lists.

Safety devices require validated circuits; a status bit on an ordinary bus is not their protective path. Software timeouts are TBD and must derive from hazard response analysis. Reset may clear a latched fault only when prerequisites are safe and must never initiate motion.
