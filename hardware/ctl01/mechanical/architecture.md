<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Mechanical architecture — OCE-CTL-01

## Concept

A welded/bolted chassis carries the battery, traction drives, pump group, operator station, and lift-arm pivots. Left/right track modules transmit traction via final drives. Front lift arms support a detachable coupler and bucket. A guard/operator zone reserves a future ROPS/FOPS engineering activity; the visual frame in CAD has **no protective-structure rating**.

All load paths, member sections, plate thicknesses, joint types, materials, weld sizes, fastener grades, fits, pin diameters, bushing materials, tolerances, corrosion allowances, and manufacturing dimensions are **TBD**. No mass properties or dimensions in the envelope model support structural calculations.

## Functional requirements (proposed)

- Maintain traction, battery, lift, operator, and attachment loads within an allowable path under defined static/dynamic/fatigue cases.
- Provide support points for raised arms, suspended components, recovery, transport tie-down and lifting only after engineering and marking; none is currently released.
- Protect pinch zones, hot surfaces, rotating drives, and battery/HV equipment while enabling safe maintenance.
- Provide positive attachment retention with state indication appropriate to risk and prevent unintended release under defined faults. Universal compatibility is not claimed.
- Keep service items accessible without unsupported elevated loads or unnecessary energy exposure.

## Stability and structure inputs

No rated-capacity inference may be drawn from 500 kg alone. Required inputs include combined machine CG/inertia; payload/attachment CG; track contact; slope/turning/braking; lift-arm range; hydraulic limits; drive reactions; quick-attach moment; transport; misuse; fatigue cycles; weld stress; corrosion; and applicable stability/protective-structure methods. `load-case-register.csv` contains the unresolved cases. [AN-LC-001A](../analysis/AN-LC-001A-static-longitudinal.md) supplies only partial, agent-authored, unreviewed static longitudinal arithmetic for synthetic inputs; LC-001 remains `TBD` and no capacity or stability rating follows.

## Mechanical decisions pending

| Decision | Required evidence | Release output |
|---|---|---|
| Chassis and lift-arm sections/joints | Static/fatigue/buckling calculations; materials; weld and manufacturing review | Controlled drawings, analysis and weld maps |
| Pivot/retention system | Bearing pressure, pin shear/bending, wear, lubrication and retention review | Pin/bushing specification and service limits |
| Final drive and track selection | Duty cycle, shock, soil/thermal/braking loads, supplier data | Approved interface drawing and braking/holding analysis |
| ROPS/FOPS and restraint/access | Applicability, current standards, structural evaluation and tests where required | Independently reviewed protective-system design and test evidence |
| Coupler/attachment interface | Geometry, engagement/retention, load moment, unintended release, attachment mass envelope | Controlled ICD; no broad compatibility statement |
| Battery enclosure/mounting | Crash/vibration/environmental loads, thermal event response, service handling | Released enclosure/mount and installation instructions |

Do not fabricate from `cad/ctl01_concept.scad`. Its proportions are display choices, not fit, clearance, access, or human-factors validation.
