<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# BUNKER-01 synthetic planning arithmetic

> **SYNTHETIC PLAN — CONSTRUCTION BLOCKED.** This host-only calculator supports a civilian, non-habitable utility-enclosure concept. It is not an autonomous construction capability demonstration, structural or reinforcement design, excavation plan, safe shelter, procurement list, permit package, borrow/haul decision, or approval to enter, occupy, excavate, energize, procure, or construct. No real-machine control exists.

## Inputs and provenance

`examples/bunker/synthetic-bunker01.json` is entirely AI-authored, synthetic, and unreviewed. It contains no real site evidence, prices, supplier selections, structural/reinforcement choices, or excavation design values. The nine geometry values exactly match `projects/bunker01/cad/parameters.scad` after conversion from millimetres to metres. Soil bulking, compacted/in-situ ratio, waste fractions, durations, and energy values are explicit arithmetic assumptions, not measured properties or engineering selections.

The canonical work, human-gate, and fleet sources remain:

- `projects/bunker01/construction/work-breakdown.csv`
- `projects/bunker01/construction/quality-gates.csv`
- `projects/bunker01/construction/fleet-register.csv`
- `projects/bunker01/site-inputs.json`

The loader rejects duplicate JSON keys, unknown fields, missing provenance, empty/whitespace-only strings, nonstandard numeric constants, Booleans used as numbers, non-finite values, out-of-float-range integers, invalid IDs, missing references, unsafe statuses, nonblank gate evidence, and dependency cycles. Geometry dimensions and thicknesses must be positive. Working space, drainage thickness, roof cover, and waste fractions may be zero. Soil factors and modeled energy must be positive. Every arithmetic operation is checked for non-finite results; nonzero multiplication/division underflow to zero, wall-shell cancellation for positive wall geometry, and impossible negative backfill are rejected. Register and JSON free text reject XML-illegal controls and unpaired surrogates while preserving normal Unicode. Site input top-level and nested records have exact keys, mandatory privacy/provenance strings, and explicit null/`TBD` values.

## Quantity conventions and formulas

All lengths are metres (m), areas square metres (m²), volumes cubic metres (m³), schedule hours relative hours (h), and electric energy kilowatt-hours (kWh). Define:

- `Li`, `Wi`, `Hi`: internal length, width, and clear height;
- `tw`, `tf`, `tr`: wall, floor, and roof thickness;
- `ws`: working space on **each** side;
- `dd`: gross drainage-layer thickness;
- `cr`: roof cover;
- `fb`: loose excavated-soil bulking factor;
- `rc`: compacted-to-in-situ ratio;
- `wc`, `ww`: concrete and waterproofing waste fractions.

### Geometry and concrete

```text
Le = Li + 2 tw
We = Wi + 2 tw
H  = tf + Hi + tr

Lx = Le + 2 ws
Wx = We + 2 ws
Dx = dd + H + cr
Vx = Lx Wx Dx

Vfloor = Le We tf
Vroof  = Le We tr
Vwalls = Le We Hi - Li Wi Hi
Vgross = Vfloor + Vroof + Vwalls
Vconcrete_theoretical_adjusted = Vgross (1 + wc)
```

The wall-shell convention subtracts only the clear internal volume over `Hi`. Floor and roof use the full external footprint. There are **no deductions** for the entrance, vents, sleeves, or other openings, and **no reinforcement estimate**. The adjusted concrete value is a theoretical waste-adjusted arithmetic result, **never an order quantity**.

### Drainage, displacement, backfill, and spoil

```text
Vdrainage_gross = Lx Wx dd
Vdisplacement   = Le We H
Vbackfill_nominal_compacted = Vx - Vdisplacement - Vdrainage_gross

Vspoil_loose = Vx fb
Vin_situ_required = Vbackfill_nominal_compacted / rc
Vexcess_in_situ = Vx - Vin_situ_required
Vexcess_loose_haul_off = max(0, Vexcess_in_situ) fb
Vmathematical_deficit = max(0, -Vexcess_in_situ)
```

Backfill is a **geometric nominal compacted volume**, not a compaction specification, material selection, lift/pass plan, or acceptance criterion. A negative signed excess is retained and separately exposed as a mathematical in-situ deficit; loose haul-off then evaluates to zero. This bookkeeping makes **no borrow, stockpile, reuse, disposal, or haul decision**. Drainage is the gross excavation-footprint layer with no void or material deduction.

### Waterproofing

```text
Anet = Le We + 2 (Le + We) H
Aadjusted = Anet (1 + ww)
```

Net area is the roof footprint plus all full external vertical sides over total structure height `H`. The underside is excluded. Openings, joints, laps, penetrations, and details are not deducted or designed. Adjusted area is not a procurement quantity.

## Schedule convention

The work-breakdown CSV supplies package IDs, predecessor IDs, synthetic durations, autonomy classes, and required gate IDs. The planner validates all dependencies and gate references, rejects cycles, and computes a deterministic ID-ordered topological sort.

Earliest-start critical-path arithmetic assumes **unlimited parallel branches** and adds a zero-duration hypothetical evidence node for every quality gate. A gate node's predecessors are its `relatedWorkPackages`; every requiring package depends on both its ordinary predecessors and its required gate nodes:

```text
G(g) = max(EF(d) for d in relatedWorkPackages(g)), or 0 if none
ES(p) = max(
    max(EF(d) for d in dependencies(p)),
    max(G(g) for g in requiredGateIds(p))
), or 0 with no predecessors
EF(p) = ES(p) + durationHours(p)
project synthetic duration = max(EF and G over all nodes)
```

Consequently every package start is at least as late as all ordinary predecessor finishes and all required gate evidence-completion times. Package/gate cycles—including a package requiring its own output gate—are rejected. `gateEvidenceMilestones` exposes each `hypotheticalEvidenceCompleteHour` with `gateAcceptancePerformed:false`; package rows also map their required gate IDs to those times. These are synthetic evidence-timing constraints only: **no evidence completion or gate acceptance is asserted, and every actual start remains blocked**.

The public `topologicalOrder`, package rows, and `criticalPathPackageIds` remain package-only. The implementation does not sum independent predecessor branches. Zero-duration package gates participate normally. Slack and binding-edge comparisons use exact equality or one floating-point ULP rather than a fixed absolute tolerance, so small positive slack remains nonzero. The reported critical path is one deterministic zero-slack package chain; `allZeroSlackPackageIds` separately retains every zero-slack package. Hours are relative offsets only: there are no dates, resource limits, calendars, productivity claims, site logistics, or executable construction sequence. Concurrency still requires a separately reviewed site plan.

`autonomyClassCounts` is register accounting only. `future_supervised_autonomy` and `simulation_candidate` do not indicate present physical capability or percent autonomous readiness.

## Energy convention and coverage

Only eight explicitly listed package/fleet pairs carry synthetic electric-energy assumptions. Each assumption has a basis and provenance and must reference a fleet registered for that package. The default values are:

| Package | Fleet | Modeled energy (kWh) |
|---|---|---:|
| BW-007 | BF-001 | 12 |
| BW-008 | BF-002 | 80 |
| BW-009 | BF-003 | 36 |
| BW-014 | BF-005 | 28 |
| BW-016 | BF-004 | 44 |
| BW-018 | BF-007 | 18 |
| BW-019 | BF-008 | 22 |
| BW-020 | BF-008 | 6 |
| **Modeled-only sum** | | **246** |

Every package appears in `energy.byPackage`; an unmodeled package has `null`, **not zero**. `modeledPackageIds`, `unmodeledPackageIds`, `modeledFleetIds`, and `unmodeledFleetIds` make coverage explicit. The 246 kWh sum is not total project energy. No unmodeled task/fleet energy, peak power, charger size, charging schedule, cost, tariff, date, or autonomous-readiness percentage is inferred.

## Commands and deterministic outputs

From a source checkout:

```sh
PYTHONPATH=src python3 -m open_construction_equipment bunker
PYTHONPATH=src python3 -m open_construction_equipment bunker   --input examples/bunker/synthetic-bunker01.json   --work-breakdown projects/bunker01/construction/work-breakdown.csv   --quality-gates projects/bunker01/construction/quality-gates.csv   --fleet-register projects/bunker01/construction/fleet-register.csv   --site-inputs projects/bunker01/site-inputs.json   --output-dir builds/bunker01 --json
```

After installation, use `oce bunker` with the same options and no checkout paths. Defaults resolve canonical installed resources. Controlled input/register failures print `ERROR: ...` and exit 2 without a traceback.

Outputs are ignored `builds/bunker01/result.json` and self-contained `builds/bunker01/schedule.svg`. The SVG shows package IDs, relative durations, autonomy classes, ordinary and dashed hypothetical gate-evidence connectors, zero-duration gates, and prominent blocking language. Deterministic measured label columns, wrapped names, variable row heights, compact hour formatting, a dynamic banner, and a bounded critical-path footer prevent fixed-column overlaps. Both artifacts are deterministic and contain no actual dates or locations.

The result's versioned `evidenceHandoff` is a synthetic reference manifest, not an evidence store or acceptance record. It carries canonical BW/BG IDs, package evidence statuses and gate statuses while naming the CSV registers as authoritative; it does not copy gate requirements or acceptance authority. `constructionAuthorized`, `physicalValidationPerformed`, and `humanAcceptancePerformed` remain `false`. Synthetic evidence references are separate from human acceptance and assert neither evidence completion nor gate acceptance.

Default result excerpt:

```json
{
  "constructionAuthorized": false,
  "physicalValidationPerformed": false,
  "readinessStatus": "BLOCKED_UNRESOLVED_HUMAN_GATES",
  "schedule": {
    "syntheticDurationHours": 472.0,
    "criticalPathPackageIds": ["BW-001", "BW-002", "BW-003", "BW-005", "BW-006", "BW-007", "BW-008", "BW-010", "BW-011", "BW-012", "BW-013", "BW-014", "BW-015", "BW-016", "BW-018", "BW-019", "BW-020", "BW-021", "BW-022"]
  },
  "energy": {"modeledOnlyElectricEnergy_kWh": 246.0}
}
```

## Hard gates and exclusions

Every result unconditionally states `constructionAuthorized:false`, `physicalValidationPerformed:false`, `readinessStatus:BLOCKED_UNRESOLVED_HUMAN_GATES`, and all unresolved `BG-001`–`BG-015` IDs. No input flag can override this baseline. All gate decision, reviewer, signature, and evidence fields must remain blank while unresolved; site inputs remain null/`TBD`.

Passing calculations, tests, schemas, SVG generation, or wheel smoke is software consistency evidence only. It performs no physical validation, accepts no gate, designs no protective system, resolves no permit, and authorizes no actual construction or autonomous operation.
