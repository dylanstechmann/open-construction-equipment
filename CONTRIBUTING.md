<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Contributing

Contributions are welcome as learning-oriented engineering inputs, not as claims that OCE-CTL-01 is buildable or safe.

## Start safely

Read `AGENTS.md`, `docs/safety-case.md`, `docs/validation-and-release.md`, and any related ADR. Discuss changes to targets, protective functions, mechanical/electrical/hydraulic interfaces, or safety requirements before extending dependent material. Never submit credentials, proprietary supplier material, copied standards text, or unlicensed third-party designs.

## What to submit

- Clearly identified targets, assumptions, calculations, references, and unresolved decisions.
- Traceable hazard/requirement/interface changes with stable IDs and consistent CSV/JSON.
- Constructive documentation, review comments, and openly licensed conceptual designs.
- Simulation evidence labeled with model/version, inputs, limitations, and agent-run status. Preserve the simulation-only boundary, deterministic behavior, explicit safety reason codes and no-auto-resume semantics; add behavioral tests for changes.
- Physical evidence only when genuinely collected under an approved activity by qualified people, including raw records, calibrated equipment details, conditions, deviations, and sign-off. Do not fabricate or retrospectively invent evidence.

## Change checklist

1. Preserve the concept/not-ready warning until the formal release process changes it.
2. Update affected registers, ADRs, traceability links, and the changelog.
3. Mark unresolved manufacturing values `TBD`; give selection/derivation criteria instead of guesses.
4. Run `python3 tools/check_all.py` after software/data changes (or the focused `make test`, `make validate`, `make demo`, `make firmware-test`, and `make wheel-smoke`). It needs no network or hardware and covers Python compilation/tests, repository integrity, deterministic demo output, C++17 host tests and (when setuptools 77+ is preinstalled) clean offline wheel build/install smoke. Describe exact commands/results in the change description. OpenSCAD rendering remains optional.
5. Add appropriate SPDX identifiers: Apache-2.0 for software, CERN-OHL-S-2.0 for hardware designs, CC-BY-SA-4.0 for documentation/media.
6. Identify AI-assisted work and distinguish it from personally completed review/testing.

By contributing, you agree your original contribution is provided under the repository license applicable to its file type. A pull request or merged change is not signed engineering approval or a machine release. No contribution may instruct an agent to energize machinery, flash a controller, defeat an interlock, or undertake field operations.

See `CODE_OF_CONDUCT.md` for participation expectations and `SECURITY.md` for sensitive reporting.
