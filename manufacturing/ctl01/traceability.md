<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# OCE-CTL-01 traceability and evidence retention

**Status:** proposed system; no unit serial, genealogy, or inspection record currently exists.

## Unit record

Assign a unique machine/unit ID only after authorized manufacture. Its controlled traveler links the exact document/BOM/drawing/schematic/software revisions to:

- incoming receipt, supplier, immutable component identity, lots/serials, material heats, battery cell/module and firmware identities;
- fabrication work orders, stations, qualified personnel identity/qualification validity, WPS/PQR revisions, weld map and individual welder/weld relationships;
- filler/consumable lots, calibrated process/inspection tools, dimensional results and NDT reports;
- coating batch/process/environment measurements and accepted repairs;
- safety-critical fastener/joint ID, actual tool result/curve where supported, lubrication condition, operator and independent witness where required;
- harness board/revision, conductor/terminal lots, electrical checks and terminal operations;
- hydraulic hose/cylinder/valve identity, cleaning/foreign-material controls, fluid and flush filter lots, actual cleanliness and pressure-test results;
- service isolation authorizations and evidence, with personnel identity protected appropriately;
- controller hardware, immutable software package/hash, configuration/schema, calibrations and authorized personnel performing a later physical load;
- all hold/witness/review results, open/closed NCRs, engineering deviations, final commissioning records and signed release scope.

`OK`, `passed`, `tested` or an unchecked box is insufficient where actual values/evidence are required. Never supply synthetic or retrospective values to complete a missing record. Missing evidence is an NCR/gate stop.

## Integrity and privacy

Use immutable revision identifiers, controlled append-only corrections, timestamps and accountability. Corrections preserve original value/entry, reason, author, date, reviewer and affected unit; no overwrites. Restrict personal qualification/private signatures and sensitive supplier records while retaining an auditable reference for authorized reviewers. Credentials or keys belong in approved secret storage, never this repository or service-record examples.

Public open-source design records and controlled unit evidence may live in separate suitable systems. This phase creates no database and claims no immutable implementation.

## Retention and changes

Before release, the owner shall approve a retention schedule based on safety criticality, expected machine life, applicable law/contracts and incident recall needs. Identify record owner, format, backup/restore verification, readability/migration, access control, and disposal authorization. At minimum preserve every active unit’s safety genealogy and unresolved NCRs; no active-unit record should be silently purged.

Any service part substitution, repair, controller update or configuration change updates genealogy and triggers safety/return-to-service review. Trace the service record to the exact prior/new configuration; never rely on the marketing name OCE-CTL-01 alone.
