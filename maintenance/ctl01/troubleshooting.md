<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# OCE-CTL-01 troubleshooting triage — future template

This table only selects a safe response and evidence owner. There is no released machine or diagnostic fault-code table. It does not authorize live measurements, access to enclosures, component replacement or a return to service. Follow site emergency rules where an immediate hazard exists.

## Universal response

If unexpected movement, electric-shock/arc indication, battery heat/gas/smoke/damage, fire, hydraulic spray, rapid drift, structural cracking or another immediate hazard is suspected: do not approach or continue troubleshooting. Only safe authorized personnel use the site emergency procedure, warn/exclude others and contact responsible local emergency resources. Do not touch the machine to retrieve records.

For non-emergency symptoms: stop use without approaching danger, have authorized staff secure/isolate/support it under `procedures/PR-002-safe-shutdown-loto.md`, record the state and exact messages without clearing history, and link a service/NCR record. Do not reset repeatedly, power-cycle indiscriminately, jumper inputs, block valves, force contactors, disable BMS, or change limits to see whether a warning clears.

| Symptom / observation | Immediate risk response | Authorized evidence collection | Prohibited shortcut / return condition |
|---|---|---|---|
| Will not enter manual ready | Keep disabled; charger/HV and control messages may indicate required protection | Qualified controls/HV review of exact configuration, event logs, physical inspection and approved de-energized checks | No holding reset, forcing ready or bypassing permissives; close root cause and restore checks |
| Travel pulls, one side loses power, or speed inconsistent | Stop under approved safe response; isolate with site controls and exclude people | Drive/brake sensor configuration and fault analysis; calibrated brake/asymmetric-drive test by approved team | Never compensate with opposite joystick; require SRS and drive/brake verification |
| Braking or holding degrades | No further travel; secure machine by engineered external means under qualified recovery plan | Brake wear/system, slope/load context, actual stopping/holding tests per release | No “one more move”; full brake and single-fault acceptance signed |
| Does not start after e-stop/interlock reset | Leave inhibited and investigate cause | Independent channel feedback, wiring/device state and logs under approved isolated procedure | Never bridge contacts or repeatedly power cycle; manually reset only once healthy per SRS |
| Lift drifts, sinks, tilts or will not hold | Keep clear of entire fall radius; use qualified engineered support/recovery not body/props | Qualified load-control/hose/cylinder inspection and safe pressure/residual-energy evidence | No reaching under arm, opening lines, increasing pressure or relying on valve alone |
| Quick attach indicates unknown/unlocked or shows damage | No lift/travel with load; exclude area and arrange controlled support | Physical engagement/wear/interface and sensor/circuit evidence from safe isolated access | Never operate to “seat” attachment or defeat indication |
| Hydraulic noise, overheating, contamination or visible leak | Stop; isolate/cool/depressurize/support under approved procedure; injection injury needs urgent medical response | Fluid/sample/filter/cooler/pump data and rated guarded inspections by hydraulic personnel | Never find leak by hand, tighten pressurized joint or add unapproved fluid |
| Pack warning, isolation fault, charge fault | Stop charging/use only by approved remote/site action; isolate area according to site plan | Pack/BMS/charger identity logs and qualified pack/HV inspection; damage requires specialist route | No bypass BMS/HVIL, charge retry or improvised pack opening; specialist disposition |
| Charging equipment damaged/wet/hot | Keep away and use site emergency/isolation route | Authorized charger/site electrical and pack compatibility review | No touch/dry-and-retry or adapter substitution |
| Track loose, damaged or repeatedly sheds debris | No travel; stabilize/exclude by qualified recovery plan | Engineered supported undercarriage/tension/wear inspection | No hand/tool access in tension/bight or unsupported raised track |
| Cracks, deformation, corrosion or elongated holes | Do not operate; retain configuration and loading history | Qualified structural inspection, NDT/load-case/safety-case review and controlled repair | No unapproved welding, drilling, grinding, plating or cosmetic fill |
| Sensor implausible/stale/intermittent | Treat data invalid; safety-related function unavailable unless SRS defines safe degraded response (TBD) | Sensor supply/signal/mechanical mounting/network timestamps using approved isolated/bench method | No offset/gain tuning to mask; calibrate and validate required function |
| Autonomy/simulation output unexpected | Current system has no physical autonomy; keep physical interface disabled | Preserve synthetic inputs, model/package/configuration and logs; review against ADR-0002 | Do not connect output to physical machine to investigate; requires new G6/G7 authority |
| Display/LV blackout or repeated reset | Prevent startup; allow only reviewed safe shutdown behavior by system | LV supply/protective supply and fault logs plus no-restart/brownout tests | Never bridge fuse or increase protection rating |
| Post-service function fails | Keep unit out of service and work order open | Reopen LOTO/NCR/test planning for exact work scope | No customer/owner use until signed PR-008 completion |

## Diagnostic evidence

Record symptom/time/configuration/operator reported by others rather than speculation; error/event raw logs, attachment/load/terrain/environment, recent parts/software/service, actual isolated measurements, part/tool IDs and photos from safe access. Separate observed facts from causal hypotheses. A cleared warning or passing simulation is not closure; signed responsible review defines regression and return-to-service evidence.
