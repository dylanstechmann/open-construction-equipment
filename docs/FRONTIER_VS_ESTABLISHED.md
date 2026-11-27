<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Frontier versus established — 2026-11-27

This note separates reproducible host-software evidence from unresolved engineering and physical-work questions. It records agent-run checks for an AI-assisted personal hobby/learning project; it is not an owner review, engineering release, or physical validation record.

## Established: reproducible software, schema, and accounting behavior

- `python3 tools/check_all.py` completed with `ALL CHECKS PASSED — SIMULATION ONLY`. Its Python suite reported **396 tests run, OK, 10 skipped**; the skips cover unavailable optional schema/physics tooling. Wheel smoke was explicitly skipped because preinstalled pip and setuptools 77+ were unavailable, and optional OpenSCAD rendering was not run.
- The strict C++17 host suite reported **45 checks passed**. These are non-safety-rated host checks, not MCU, deployment, or independent protective-function evidence.
- The current synthetic BUNKER-01 register produces a **246 kWh modeled-only construction-energy subtotal** from eight explicit assumptions. This is arithmetic coverage, not total construction energy.
- The construction-energy export retains **14 work-package entries with unknown energy** and **BF-006 as the one fleet entry with unknown energy**. Unknown values remain `null`, not zero.
- Repeated BUNKER-01 CLI runs produce byte-identical `result.json`, `schedule.svg`, and `construction-energy.json`. The strict export schema and runtime checks retain stable source/work-package/fleet IDs, parsed-content revision fingerprints, modeled values, and explicit unknowns.

## Frontier and not established

- **Total construction energy and missing estimates:** the 246 kWh subtotal excludes unknown package and fleet energy. No total project energy, peak power, charger size, charging schedule, tariff, cost, or autonomous-readiness estimate is established.
- **Engineering adequacy:** structural, geotechnical, excavation-protection, electrical, fire, ventilation, waterproofing, drainage, lifting, confined-space, and other discipline adequacy remain unresolved specialist questions. OCE-CTL-01 remains an unvalidated concept with no real-machine actuation or field-autonomy release.
- **Fabrication readiness and permits:** no fabrication-ready design, procurement authority, site-specific release, permit, inspection, or authorization having jurisdiction acceptance is established.
- **Physical validation:** no physical inspection, construction, energization, controller flashing, machine test, or site validation has been performed. Software and accounting checks do not close any BUNKER-01 human gate.
- **Occupancy and protective use:** BUNKER-01 remains a synthetic, unoccupied, non-habitable utility-enclosure concept. No occupancy, habitation, entry, safe-room, shelter, or protective-use authorization is established.
- **Habitat sustainability:** one-time construction energy is separate from habitat daily operating demand. No habitat load balance, recurring resource sufficiency, life-support performance, or sustainability claim is established by this export.

## Update when evidence changes

Update this note whenever reproducible evidence changes: record the exact source revision, command, test counts and skips, deterministic export totals, and explicit unknowns. Move a frontier item only with durable, scope-appropriate evidence and the required named human review; never promote software consistency into engineering adequacy, fabrication readiness, permission, physical validation, occupancy, or habitat sustainability.
