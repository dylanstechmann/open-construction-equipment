<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Changelog

All notable changes are recorded here. Dates document repository activity, not physical validation or a machine release.

## [Unreleased]

### Added — 2026-11-15

- Initial OCE-CTL-01 concept baseline, lifecycle governance, multi-license notices, and AI-assisted-project disclosure.
- Engineering status, architecture, pre-release safety case, standards/references registers, terminology, release gates, and ADRs 0001–0002.
- Conceptual hardware registers, 40+ item make/buy BOM, and parameterized visualization-only OpenSCAD envelope.
- Unreleased manufacturing process/work-instruction templates with quality, traceability, qualified-personnel, and evidence gates.
- Proposed maintenance schedules, service registers, procedures, and synthetic non-operational service record example.
- Phase 2 standard-library Python package and `oce` CLI with strict SI configuration, polygon/circular geometry, inflated deterministic 8-connected A*, bounded pure pursuit, latching supervisory gate and explicit kinematic-only simulation.
- Deterministic synthetic-yard mission with structured JSON, self-contained SVG, event/termination reporting and obstacle-clearance integration tests under ignored `builds/`.
- Proposed machine-readable intervals for all SVC IDs, explicit synthetic service-history/record examples, due/overdue calculations, BOM summaries and repository cross-reference validation.
- Portable non-safety-rated C++17 host command gate with strict compilation and 45 host checks; unified offline `tools/check_all.py`, Makefile and Python 3.11/3.12 CI.
- Software/maintenance/firmware/validation documentation and corrected provenance: numeric targets are initial AI-authored concepts with owner review pending, not owner-supplied values.
- Canonical wheel-installed runtime data for all four default CLI commands, package-scoped validation, full dist-info license/NOTICE payloads, modern PEP 639 metadata, and clean offline wheel smoke tooling.

### Fixed — 2026-11-15

- Checked every continuous planned segment and exact endpoint connector against inflated geometry; retained diagonal-corner protection, added visible grid connections, safe same-cell behavior and immediate exact-goal success.
- Corrected exact ±90° rotation-only tracking, reversal braking/acceleration selection and bounded partial-step mission duration.
- Added sharp-corner segment-capped lookahead, vertex slowdown and align-before-translation behavior; the original yaw=0 coarse-grid detour now succeeds with sampled clearance while retaining honest tracking-error limitations.
- Rejected invalid C++ gate limits, duplicate/nonstandard JSON, malformed CSV, non-finite design inputs, self-intersecting fences, inconsistent maintenance chronology, missing rationale and UTC arithmetic overflow with controlled errors.
- Corrected CAD/interface provenance and stale license wording; expanded false-attribution and stale-license validation.

### Validation

- `python3 tools/check_all.py` runs Python compilation, 107 Python unit/integration/CLI tests, repository/config/CSV/BOM checks, two byte-identical deterministic demos, 45 strict C++17 host checks and clean offline wheel build/install smoke when setuptools 77+ is preinstalled. OpenSCAD rendering is optional and not required.
- `tools/wheel_smoke.py --require-build-tools` verifies the non-editable wheel and all four installed default commands from a clean temporary directory with no dependency downloads; installed validation is explicitly package-scoped.
- Software results are simulated/agent-run consistency evidence only. No calculations constitute design verification; no physical inspection, fabrication, energization, controller flashing, deployment or machine test has been performed.
