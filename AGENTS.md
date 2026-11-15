<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Agent instructions — Open Construction Equipment

The `/workspace/AGENTS.md` rules apply. This is an independent personal hobby/learning repository; keep visible AI assistance, preserve Git history/configuration, protect credentials, and do not add employment, hiring, résumé, or solo-authorship framing. One coding agent edits this working tree at a time. Do not register containers or modify any other repository.

## Ownership and layout

- Root and `docs/`: lifecycle governance, concept boundaries, standards pointers, decisions, evidence vocabulary, and simulation/software documentation.
- `hardware/ctl01/`: conceptual OCE-CTL-01 design inputs, interfaces, registers, BOM, and CERN-OHL-S-2.0 OpenSCAD source.
- `manufacturing/ctl01/`: unreleased process templates and quality gates, not permission to fabricate.
- `maintenance/ctl01/`: proposed service planning and machine-readable non-OEM intervals, not an OEM service manual.
- `src/open_construction_equipment/`: Python 3.11+ standard-library simulation, planning, supervisory, maintenance, BOM and CLI reference code.
- `configs/`, `schemas/`, `examples/`: strict synthetic simulation inputs, interchange schemas and non-operational examples. Generated reports belong in ignored `builds/`.
- `tests/`, `tools/check_all.py`: offline Python unit/integration/CLI tests and the unified check.
- `firmware/ctl01/`: non-safety-rated portable C++17 host gate and tests, with no MCU/deployment integration.

Use the exact platform identifier **OCE-CTL-01** and stable requirement, hazard, interface, BOM, load-case, service and work-instruction IDs. Keep CSV headers/row widths valid and JSON machine-readable. Prefer cross-links and IDs over copied requirements. Preserve meaningful data; do not replace unfinished work with empty placeholders. Numeric concept targets are initial AI-authored values with owner review pending, not owner-supplied requirements.

## Safety boundaries

All outputs are concept-only and unvalidated. Distinguish `target`, `assumption`, `TBD`, `simulated`, `measured`, `reviewed`, and `released`. Never promote evidence status without durable provenance and required signed human review. Do not invent dimensions, pressures, torque values, weld parameters, protective-structure performance, tests, certifications, prices, supplier part numbers, or compatibility. Do not reproduce proprietary standards text or claim compliance from a citation.

**Agents never energize machinery, flash controllers, commission batteries/hydraulics, perform physical operations, direct someone to bypass a guard/interlock, or represent simulations/calculations as physical validation.** Executables are simulation-only host tools with no hardware I/O or deployment bypass. Python/C++ supervisory gates are not certified safety functions or substitutes for independent protection. Any future real-machine work requires qualified personnel, signed responsible engineering review, approved procedures, jurisdiction/site authorization, and a new hazard analysis.

## Review and provenance expectations

1. Read the relevant safety case, ADRs, design inputs, and procedure prerequisites before editing.
2. Keep manual control and independent protective functions separate from supervisory/autonomy commands; protect fail-safe behavior, latching and command arbitration. Safety events must not be hidden to obtain mission success.
3. Cite verifiable primary/official sources. Record uncertainty and access dates; never fabricate references or attribute AI-proposed values to the owner.
4. Physical tests require measured values, units, equipment identities/calibration, conditions, raw data, witnesses where required, and named signed reviewers. Agent-produced text/simulation is not such a record.
5. Parse changed JSON/CSV with standard-library tools. OpenSCAD rendering is optional; static checks must not install it or make it mandatory.
6. Run `python3 tools/check_all.py` (or `make check`) after software/data changes. It runs Python tests, repository validation, two deterministic demos, strict C++17 host tests and offline wheel smoke (with an explicit skip if setuptools 77+ is unavailable) without network access. Report exact results and unavailable optional rendering.
7. Keep runtime dependency-light (standard library), deterministic and SI-unit explicit. Add behavioral regression tests for changed planner, tracker, supervisor, maintenance or CLI semantics.
8. Before ending, inspect `git status --short` and report limitations. Do not commit, push, tag, or create releases unless the owner explicitly asks in a separate instruction.
