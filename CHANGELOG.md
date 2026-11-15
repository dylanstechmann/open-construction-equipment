<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Changelog

All notable changes are recorded here. Dates document repository activity, not physical validation or a machine release.

## [Unreleased]

### Added — 2026-11-15

- Unreleased BUNKER-01 documentation/design baseline under `projects/bunker01/`: civilian non-habitable utility-enclosure scope, null/TBD real-site inputs, architecture and hazard boundaries, official reference starting points, 22 dependency-linked synthetic work packages, 15 unresolved human gates, honest electric-fleet gaps, a conceptual unpriced BOM, maintenance/handover requirements and self-contained synthetic OpenSCAD visualization. A subsequent software change in this release adds the executable synthetic planner described below; no construction, entry, occupancy, protective use or physical autonomy is authorized.
- BUNKER-01 standard-library immutable SI planning models, strict synthetic example/schema, checked gross quantity formulas, deterministic DAG earliest-start/critical-path scheduling, autonomy-class accounting, selected package/fleet energy coverage, blocked result JSON and self-contained schedule SVG.
- `oce bunker` source/wheel defaults, canonical installed project registers/site data, dual-run JSON/SVG byte comparison, source CAD agreement validation and comprehensive quantity/schedule/energy/CLI/packaging tests.
- AN-LC-001A deterministic static longitudinal load-moment arithmetic with immutable SI inputs, mandatory per-value synthetic provenance, stable source-register trace IDs, strict schema/runtime loading, complete normalized-input hashing, explicit exclusions and no operational acceptance verdict.
- `oce analyze` with source/wheel defaults, deterministic ignored `builds/analysis/lc001/result.json`, controlled input errors, dual-run byte comparison, installed-wheel smoke coverage, worked equations, uncertainty and reproduction documentation.
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
- Canonical wheel-installed runtime data for all six default CLI commands, package-scoped validation, full dist-info license/NOTICE payloads, modern PEP 639 metadata, and clean offline wheel smoke tooling.

### Fixed — 2026-11-15

- Independent BUNKER-01 review: required gates now constrain CPM starts through zero-duration hypothetical evidence nodes with combined package/gate cycle detection, explicit evidence-completion timing, unchanged package-only ordering/critical path, and no acceptance implication.
- Replaced fixed slack tolerance with one-ULP comparisons; rejected nonzero arithmetic underflow and positive wall-shell cancellation; enforced exact site-input envelopes and XML-legal register/JSON text.
- Reworked BUNKER-01 SVG with dynamic columns, wrapped names, variable rows/banner and bounded footer; expanded static OpenSCAD checks to all four hardware/project sources; renamed the fixed readiness status constant with an `_ID` suffix without scanner suppressions.

- CI now provisions pinned `setuptools==80.9.0` on both Python matrix jobs before diagnostics and required offline wheel smoke; local runtime/tests and post-provisioning builds remain offline.
- Shared numeric loading now reports out-of-float-range integers as controlled input errors, and engineering schema notice/provenance strings reject whitespace-only values consistently with runtime loading.
- Checked every continuous planned segment and exact endpoint connector against inflated geometry; retained diagonal-corner protection, added visible grid connections, safe same-cell behavior and immediate exact-goal success.
- Corrected exact ±90° rotation-only tracking, reversal braking/acceleration selection and bounded partial-step mission duration.
- Added sharp-corner segment-capped lookahead, vertex slowdown and align-before-translation behavior; the original yaw=0 coarse-grid detour now succeeds with sampled clearance while retaining honest tracking-error limitations.
- Rejected invalid C++ gate limits, duplicate/nonstandard JSON, malformed CSV, non-finite design inputs, self-intersecting fences, inconsistent maintenance chronology, missing rationale and UTC arithmetic overflow with controlled errors.
- Corrected CAD/interface provenance and stale license wording; expanded false-attribution and stale-license validation.

### Validation

- `python3 tools/check_all.py` runs Python compilation, 208 Python unit/integration/CLI tests (140 preserved + 68 BUNKER-01), repository/config/CSV/BOM checks, two byte-identical deterministic demos, two byte-identical AN-LC-001A analyses, two byte-identical BUNKER-01 JSON/SVG plans, 45 strict C++17 host checks and clean offline wheel build/install smoke when setuptools 77+ is preinstalled. Four OpenSCAD sources receive static checks; rendering is optional and not required.
- `tools/wheel_smoke.py --require-build-tools` verifies the non-editable wheel and all six installed default commands from a clean temporary directory with no dependency downloads; installed validation is explicitly package-scoped.
- Software results are simulated/agent-run consistency evidence only. AN-LC-001A and BUNKER-01 arithmetic do not constitute design verification; BUNKER-01 remains blocked by all 15 unresolved human gates; no physical inspection, fabrication, energization, controller flashing, deployment or machine test has been performed.
