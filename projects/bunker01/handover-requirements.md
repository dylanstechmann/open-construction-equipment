<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# BUNKER-01 handover requirements

**Current handover status: NOT AVAILABLE.** All gates are unresolved, all signature/evidence fields are blank, and no construction, inspection, commissioning or physical validation has occurred. This checklist defines future evidence; it is not a certificate or release.

## Acceptance package

The owner and responsible authorities must define the exact configuration and evidence index. The package is expected to include:

1. **Requirements and legal basis:** owner-approved actual use, equipment/contents and load inventory, explicit non-habitable/no-occupancy classification, foreseeable misuse, property authorization, AHJ/code register, permits and required final approvals.
2. **Site basis:** controlled survey and datum, geotechnical report and groundwater data, competent soil classification, utility locates/closeouts, drainage/flood/environmental/archaeological/contamination records and site-specific risk assessments.
3. **Released design:** signed structural/geotechnical/civil calculations, drawings and reinforcement/embed/joint schedules; concrete and durability requirements; excavation protective-system and temporary-work records; electrical, grounding/lightning, ventilation, fire, access/egress, security, networking and lighting designs as applicable.
4. **Construction genealogy:** approved suppliers/materials, concrete batching/placement and cure records, reinforcement/formwork/embed inspections, waterproofing/drainage evidence, backfill/compaction results, worker/competent-person inspections, nonconformances and their signed dispositions.
5. **Commissioning:** calibrated electrical/grounding/isolation tests; ventilation and atmospheric-system verification; fire detection/alarm/suppression results as applicable; normal/emergency lighting; network/sensor failure tests; door/escape/security coordination; loss-of-power, water and communications scenarios.
6. **As-built and asset data:** independent survey, deviations, concealed-work references, penetration and utility maps, equipment manuals, warranties where supplied, software/firmware/configuration identities, sensor/calibration register and maintenance access limitations.
7. **Safety and operation controls:** residual-risk register, non-habitable/use restrictions, prohibited contents, authorized maintenance-entry process, confined-space classification and program where applicable, emergency/rescue/flood/fire plans, utility and isolation information, security-versus-escape review and bystander controls.
8. **Maintenance and change control:** approved inspection/monitoring plan and intervals, acceptance thresholds, records system, spare/consumable list, qualified assessment responsibilities, modification triggers, mothballing/abandonment plan and end-of-life responsibilities.

## Gate reconciliation

Every applicable gate in [`construction/quality-gates.csv`](construction/quality-gates.csv) must have a dated decision by the identified responsible human authority, a scoped signature/approval, and an immutable reference to actual evidence. At minimum the handover reviewer must reconcile:

- `BG-001`–`BG-007`: use, legal/site, utilities, geotechnical, structural, excavation and environmental prerequisites;
- `BG-008`–`BG-012`: lifting, preplacement, concrete/cure, waterproofing/drainage and backfill physical evidence;
- `BG-013`–`BG-014`: integrated discipline commissioning, final authority acceptance and complete maintenance handover; and
- `BG-015`: final written non-habitable equipment/storage classification and entry/use restrictions.

A gate is not satisfied by a package named after it, a completed CSV row, a simulation, a photograph without context, a supplier claim, an AI summary or a repository merge. Unresolved or failed gates prevent the associated next activity. Conditional acceptance, if legally permitted, must state exact limitations, corrective work and responsible deadlines without implying unrestricted use.

## Autonomous construction evidence remains separate

No autonomous construction capability is handed over by this baseline. Any future fleet trial needs its own machine release, operational design domain, independent safety functions, real-site perception/dynamics validation, human supervision, bystander exclusion, geofencing and recovery/emergency evidence under the [OCE validation process](../../docs/validation-and-release.md). Missing excavator, hauler, compactor, concrete-placement and site-safety systems must remain visible as gaps rather than being replaced by labels in a schedule.

## Controlled evidence and privacy

The public repository may contain only a non-sensitive index. Actual private location, coordinates, property records, credentials, security vulnerabilities, personal information and signatures must remain in controlled storage. Each index entry should identify the controlled record, revision, integrity/hash method, source, raw-data location, physical configuration, author, reviewer, date, scope and limitations without exposing the restricted content.

## Use acceptance statement to complete later

The eventual statement must name the exact site, approved equipment/storage use, prohibited occupancy and protective claims, configuration, authorized service activities, entry restrictions, unresolved limitations and responsible approvals. Until then the controlling status is **no construction, no entry, no occupancy, no autonomous operation, and no protective-use claim**.
