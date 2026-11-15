<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# BUNKER-01 maintenance and monitoring concept

**No facility exists and no maintenance plan is approved.** This is a list of future requirements, not permission to inspect by entry, operate equipment, disturb electrical systems, or perform rescue. Approved intervals, acceptance limits and procedures must be derived from the released design, actual equipment, site exposure, law, manufacturer instructions and qualified risk assessment. No numeric interval is invented here.

## Access and service boundary

Prefer non-entry and external inspection where the released design permits. Any human entry requires a current assessment of structural condition, excavation/ground stability where relevant, utilities, water, atmosphere, ventilation, fire, egress, entrapment and security. Applicable confined-space classification, testing, ventilation, attendants, permits and rescue arrangements must be completed by responsible humans. A previous inspection, ventilation fan, open door, sensor reading or non-habitable label never provides blanket entry authorization.

Only qualified persons may service electrical, fire, ventilation, structural, drainage or lifting-related systems within their competence. Lockout/tagout and stored-energy controls require system-specific approved procedures. No live electrical work, battery intervention, structural repair, drain entry or confined-space rescue is described or authorized here.

## Inspection and monitoring agenda

| Area | Observe and record | Qualified escalation triggers to define |
|---|---|---|
| Structure | Cracks, spalling, corrosion signs, deformation, joint movement, impact, water-related deterioration and changes around openings | Crack/movement mapping and structural review criteria based on released design; restrict use and entry for suspected instability |
| Settlement and surroundings | Survey references, floor/structure level changes, ground movement, erosion, sinkage, adjacent features and surface drainage | Geotechnical/structural thresholds, changed loading/groundwater and nearby excavation or construction |
| Leaks and moisture | Dampness, active leaks, efflorescence, condensation, corrosion, mold-like growth, humidity trends and previous repair condition | Source diagnosis, electrical isolation assessment, material/health review and waterproofing/structural repair design |
| Drainage and flood protection | Surface flow, outfalls, cleanouts, blockage, backflow, sediment, pumps/alarms if installed, discharge impact and power-loss state | Civil/environmental assessment for changed discharge, flooding, repeated blockage, pump/alarm failure or erosion |
| Waterproofing and penetrations | Accessible membrane/protection condition, joints, seals, sleeves, waterstop evidence and concealed-work records | Designer/manufacturer inspection and repair requirements; no uncontrolled coring or cutting |
| Ventilation and atmosphere | Air terminals, airflow indications, fans, dampers, filters, noise/vibration, sensor status, calibration and alarm history | Mechanical/industrial-hygiene review for deterioration, unknown odors/gases, sensor faults or changed contents/use |
| Electrical and charging | Enclosures, routing, labeling, protection, grounding/bonding records, isolation, moisture effects, charger/BMS records and test history | Qualified electrician and fire specialist for damage, water exposure, trips, heat, battery/charger alarms or modification |
| Fire and life safety | Detection/alarm/suppression equipment if installed, fire stopping, contents inventory, responder information and test records | Fire/life-safety review after faults, changed contents/charging, impairments, discharge or any fire event |
| Door access security and escape | Door/frame, seals, hardware, interior escape release, guards, access route, lighting, tamper evidence and rescue access | Immediate control of entrapment/egress defects; security changes require life-safety review |
| Lighting network and sensors | Normal/emergency lighting, communications, sensor health, cybersecurity updates, time sync, power loss and alarm delivery | Restore required life-safety functions under approved procedures; investigate stale, absent or contradictory data |
| Fleet service interfaces | Charging location, isolation, exclusion zones, positioning infrastructure, recovery points and autonomous-system logs | Separate OCE and site safety review before connecting, moving, updating or testing any autonomous system |

## Monitoring, alarms and calibration

The future design must define which measurements are informational and which support a safety function. Safety functions cannot depend solely on ordinary networking, AI classification, remote commands or the OCE host supervisor. Each instrument needs identity, range, location, calibration/bump-test requirements as applicable, raw records, alarm/threshold rationale, failure behavior and responsible reviewer. Thresholds remain TBD.

Event-based review is required after flooding, fire, impact, utility strike, ground movement, significant modification, prolonged shutdown or other released-design triggers. This does not establish a numeric inspection frequency. Routine and periodic intervals must later be assigned by the responsible designer/owner using actual obligations and degradation mechanisms.

## Records and periodic qualified assessment

Maintain a controlled asset register, approved configuration, as-builts, inspection dates and scope, photographs, measurements, instrument/calibration identity, environmental conditions, alarms, entry/permits where applicable, defects, nonconformances, repairs, isolation/return-to-service evidence and named reviewers. Preserve raw data rather than only dashboards. Keep private location, access credentials, security details and signatures outside the public repository with non-sensitive evidence references.

A qualified periodic assessment must review changes in use, contents, loads, nearby work, climate/water exposure, reliability, incidents and applicable requirements. It must explicitly confirm or revise the non-habitable use and entry controls. Missed records cannot be reconstructed as physical evidence.

## Autonomous-system service boundaries

BUNKER-01 maintenance records do not service or release OCE-CTL-01. The separate [OCE maintenance boundary](../../maintenance/ctl01/README.md) and release process still apply. Software updates, sensor replacement, battery/charger changes, map/geofence edits or repaired propulsion require configuration control and renewed safety review. Agents may analyze supplied logs but cannot verify isolation, inspect a machine, perform a physical test or sign a return to service.

## Mothballing and deterioration

The maintenance plan must preserve the approved [mothballing/abandonment strategy](safety.md#mothballing-and-safe-abandonment), including energy and hazardous-content control, water management, unauthorized-entry prevention, environmental obligations and emergency information. Suspending monitoring or ventilation is itself a design change requiring review. A mothballed structure remains potentially hazardous and requires a fresh qualified assessment before reopening or entry.
