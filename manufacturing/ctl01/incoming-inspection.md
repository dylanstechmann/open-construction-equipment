<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Incoming inspection control

**Unreleased template — does not authorize receipt, unpackaging of hazardous goods, energization, or acceptance.** A qualified receiving organization must turn this into a site procedure before G3.

## Prerequisites and controls

Approved purchase configuration and drawing/revision; safe unloading/storage plan; competent material, HV-battery, hydraulic and metrology personnel as needed; calibrated instruments; supplier documents; preservation/environment controls; quarantine location; traceable unit traveler. Follow battery dangerous-goods and site rules without using this text as transport instructions.

## Flow

1. **Identity:** match purchase item, source, exact model/revision, serial/lot, quantity, packaging integrity and shelf-life/preservation. No substitute because dimensions appear similar.
2. **Documents:** review material/heat and process certificates, conformity records where applicable, test/safety manuals, calibrated-component records, software/firmware identity, hazardous goods and chain-of-custody documents. Verify authenticity through the approved route.
3. **Physical inspection:** only within safe competence and packaging limits; identify damage, corrosion, contamination, connector/terminal condition, seals/caps, labels, missing pieces, tampering and counterfeit indicators. Do not open sealed HV packs or pressure components unless a separate approved instruction exists.
4. **Measurements:** perform only the released sampling/characteristic plan using correct calibrated equipment. Record actual values and uncertainty where relevant, not just `OK`.
5. **Disposition:** qualified inspector signs `accepted`, `quarantined`, or `rejected`, links external evidence and releases storage location. Acceptance into stock does not release assembly.

## Special family gates

- Structural material: positive item/heat traceability and approved material certificates; maintain identity through cutting/kitting.
- Weld/filler consumables: storage/conditioning per released WPS and supplier requirements with lot/issue record.
- Fasteners: grade/coating/lot and anti-counterfeit evidence; no unreviewed mixing/replating/lubrication because torque/preload changes.
- Cells/modules/BMS/HV: model/lots/firmware and transport/storage condition; damage or error isolates item without handling beyond the approved emergency process.
- Hydraulic parts: clean sealed ports, compatible materials, clean packaging and applicable pressure documentation; preserve cleanliness until controlled assembly.
- Safety parts: exact safety component/version/manuals, diagnostic/config identity and source authenticity.

## Records and discrepancies

Record receipt ID, BOM item, PO/configuration only where lawful to retain, supplier and exact revision, lots/serials, documents, inspector, instruments, results, conditions, attachments and final approver. Place mismatches under `nonconformance.md`; agents may draft a report from data but cannot inspect or physically disposition items. Retention follows `traceability.md`.
