<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# BUNKER-01 concept architecture

**Status:** AI-authored functional decomposition only. No system below is sized, coordinated, code-reviewed, released, or physically validated. The architecture does not authorize entry, excavation, procurement, installation, charging, or autonomous work.

## System context

The reference arrangement is a buried or partially buried **cut-and-cover reinforced-concrete utility enclosure** with one conceptual entrance, service penetrations, external drainage/waterproofing zones, and backfill/roof cover. The only target use is future approved non-habitable equipment/storage. Internal layout, door hardware, stairs/ladder/ramp, number of exits, structural system, joints and all service ratings remain TBD.

The [OpenSCAD model](cad/bunker01_concept.scad) shows spatial relationships, not reinforcement or construction details. Its exact synthetic geometric assumptions are recorded in [requirements](requirements.md#synthetic-geometric-baseline) and [CAD parameters](cad/parameters.scad).

## Functional boundaries

| System | Concept intent | Required future design and explicit limits |
|---|---|---|
| Enclosure and support | Floor, walls and roof form a durable utility envelope; ground and water loads are carried by a site-specific structure. | Geotechnical/structural engineers must resolve bearing, settlement, sliding, overturning, uplift, load combinations, crack/durability control, joints, reinforcement and concrete. No capacity is inferred from CAD thicknesses. |
| Entrance and access | A wall opening marks a possible access route and maintainable equipment path. | Opening/header, door, threshold, landing, stairs/ladder/ramp, guarding, accessibility, ventilation interactions, security, escape and rescue require specialist/AHJ design. One shown opening is not an approved egress strategy; a second exit may be required. |
| Drainage | External drainage zone and pathways allow a future designed collection/discharge system; roof/surface water is considered separately. | Civil/geotechnical inputs must establish lawful outfall, backflow, filtration, inspectability, pump/backup needs and failure consequences. A perforated path in CAD neither guarantees gravity drainage nor prevents flooding. |
| Waterproofing and water management | A continuous, repairable external barrier concept coordinates with joints, penetrations, drainage and structure. | Designer/manufacturer must select compatible systems, preparation, detailing, protection, testing and acceptance. Waterproofing is not a substitute for hydrostatic/uplift design or flood-safe siting. |
| Ventilation and atmosphere | Conceptual separated air pathways support future ventilation and environmental monitoring. | Mechanical/industrial-hygiene/fire specialists must determine air source, rates, distribution, pressure interactions, moisture, radon/methane/contaminants, noise, power loss, dampers and alarms. Natural openings or fans do not certify breathable air or confined-space entry. |
| Electrical and charging | Future grounded/bonded power distribution, isolation, protected routing, monitoring and maintainable service equipment. | Licensed/qualified electrical designers must calculate loads/faults, protection, selective coordination, earthing, equipotential bonding, residual-current/other required protection, wet-location suitability, isolation and testing. Preferring charging outside the enclosure is a design question, not a decision; no indoor charging is currently approved. |
| Networking and controls | Non-safety monitoring, maintenance records and optional isolated communications pathways. | Define cybersecurity, data ownership, power/communications loss, alarming and manual service access. Networked sensors, remote stop commands and autonomy messages are not independent life-safety functions. |
| Fire detection and response | Detection/alarm zones and responder information may support an engineered fire strategy. | Fire specialist/AHJ must assess actual batteries, chargers, stored materials, ignition sources, fire resistance, detection, notification, suppression, smoke control, access and emergency response. A detector alone does not control battery thermal runaway or make entry safe. |
| Grounding, bonding and lightning | Coordinate structure, electrical service, equipment, metallic piping and any required external protection. | Electrical/lightning specialists must assess applicable risk and design/test the complete system. Reinforcing steel is not automatically an approved grounding or lightning system. |
| Lighting | Maintainable normal service lighting and possible emergency/wayfinding lighting. | Required illuminance, emergency duration, switching, wet/dark-location suitability and loss-of-power behavior are TBD by code/risk assessment. Lighting does not authorize occupancy. |
| Security | Controlled access, tamper awareness and privacy-preserving event records. | Security design must preserve required escape and rescue, avoid hidden entrapment, address forced-entry/vandalism only as civilian property risks, and keep sensitive layouts/credentials out of the repository. No blast/ballistic function is included. |
| Maintainability | Accessible cleanouts, sensors, isolation points, replaceable equipment, inspection surfaces and record identifiers. | Resolve safe access, isolation, lifting, confined-space classification, spare parts, diagnostic ports and work clearances before concealment. Do not route services where later work would undermine structure or waterproofing. |
| Future fit-out | Reserved, documented service routes and removable equipment mounting zones. | No sleeping, sanitation-for-habitation, workshop, fuel storage, battery chemistry/quantity, shelving load or occupancy fit-out is approved. Each change triggers structural/fire/electrical/ventilation/use review. |

## Construction-stage interfaces

Temporary works, formwork, falsework, reinforcement, lifting, embeds, placement and curing are separate engineered systems. The permanent enclosure cannot be assumed to support construction loads. Preplacement review must reconcile released structural, waterproofing, drainage, electrical, ventilation and access details before concealment. Any conflict remains open until responsible designers resolve it.

Cut-and-cover sequencing depends on engineered excavation support and surface-water controls. Backfill material, placement and compaction must not damage walls, roof, waterproofing, drainage or utilities and must follow released inspection/testing requirements. The work-breakdown CSV is a dependency sketch, not a method statement.

## Fleet and autonomy interface

The long-term vision is an electric, open-source construction fleet with supervised research autonomy. The site would need separately engineered positioning, communications, charging, geofencing, exclusion zones, independent protective functions, rescue/recovery, loss-of-signal behavior and human control. Existing OCE-CTL-01 simulation cannot perceive a real excavation, detect utilities or people reliably, certify ground conditions, install support, place concrete, compact backfill or approve its own actions.

No autonomous fleet may share space with unprotected people or bystanders. Any future trial needs an approved operational design domain, current hazard analysis, competent site supervision, legal permission and physical validation under both the BUNKER-01 and OCE release processes.

## Information handover

Each future released subsystem needs unique configuration references, calculations, drawings, material/component records, inspections, tests, deviations, as-builts, residual risks, maintenance limits and named approvals. The public concept retains only non-sensitive indexes; controlled records must preserve private location, credentials and signatures without implying that absent evidence exists.
