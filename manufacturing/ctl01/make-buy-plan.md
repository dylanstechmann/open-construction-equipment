<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Make/buy and supplier quality plan

**Status:** proposal for OCE-CTL-01; no supplier has been approached, selected, audited, or qualified.

## Decision criteria

For each BOM line record lifecycle volume/skills, safety function, design ownership, geometric/material IP and CERN-OHL-S-2.0 duties, tooling/capital need, process capability, supplier evidence, service/spares availability, dangerous-energy risk, end-of-life path, and total lifecycle support. No price target is assumed. “Buy” does not transfer system responsibility; “make” does not grant permission to use unreleased geometry.

| Family | Proposal | Required release evidence |
|---|---|---|
| Chassis, arms, guards | Make only by qualified fabricator with controlled drawings | Material traceability, WPS/PQR, qualified welders, weld maps/NDT, dimensional report, repair approval |
| ROPS/FOPS system | Specialist make/buy decision; do not treat ordinary fabrication as sufficient | Applicable standards and configuration-specific analysis/test, restraint/seat integration and independent acceptance |
| Tracks, final drives, motors, inverters | Buy/integrate from technically qualified source | Exact model/datasheet revision, duty/load/braking/protective inhibit details, declarations, interface approval and spares |
| Cells/modules and BMS | Prefer qualified pack/component source unless separately competent pack process is released | Cell lots, transport and abuse evidence, BMS safety manual, charger compatibility, thermal and emergency design, traceability |
| Contactors/protection/HV distribution | Buy protected components; integrate under qualified HV engineering | Fault current/selectivity/isolation, connection/release drawings, insulation/discharge verification and quality records |
| Pump/valves/cylinders/hoses | Buy selected components; controlled assembly | Circuit/loads/duty, load-holding behavior, certified hose assembly competence, fluid/cleanliness/pressure records |
| Harnesses | Controlled make under approved harness design or specialist buy | Schematics/pinout, conductor/terminal/sealing specs, workmanship, continuity/isolation and 100% visual checks |
| Controls/safety devices | Buy suitable components with safety manuals where required | SRS allocation, fault/reaction behavior, independence, configuration/version management and validation evidence |
| Bucket/quick attach | Make/buy after interface and stability analysis | Attachment mass/CG envelope, weld/retention/wear design, engagement misuse tests and no unbounded compatibility claim |
| Thermal/cooling/service equipment | Buy/integrate | Thermal load cases, fluid compatibility, rating/calibration, safe service access and support validation |

## Supplier approval flow

`Technical requirement → evidence screening → quality/legal/license review → sample/incoming plan → controlled approval → purchase configuration lock → incoming acceptance → performance/field feedback`.

Require source identity, exact immutable part/revision, material and process certificates where applicable, conformity/inspection evidence, calibration where supplied, software/firmware identity, safety manuals, storage/lifetime conditions, transport restrictions, counterfeit avoidance, obsolescence and change notification. Supplier certificates are verified inputs, not automatic machine conformity.

No supplier substitution is neutral. Review structure, mass/CG, thermal/electrical loads, duty/rating, firmware, diagnostics, safety function, interfaces, cleanliness, tooling and regulatory effects. Quarantine an unauthorized change through `nonconformance.md`.

## Release checklist

A responsible buyer/engineer signs an approved source record tied to BOM item and unit/serial. Reviewer roles, acceptance evidence and open actions remain retained per `traceability.md`. This learning-project BOM intentionally has no fake manufacturer numbers, prices or lead times.
