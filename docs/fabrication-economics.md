<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Fabrication, startup, maintenance, rental, and hybrid economics

## Scope and evidence boundary

`open_construction_equipment.economics` is a deterministic, standard-library-only trade-study calculator for one synthetic project. It compares selected OCE-CTL-01 fabrication/tooling assumptions with commercial-rural-rental *scenario inputs* for the BUNKER-01 concept. It does not alter the canonical BOM, estimate a market price, select a supplier, or resolve any engineering or site gate.

All currency amounts are AI-authored, synthetic, finite `float` values in the envelope's three-letter `currency` label. The example uses `USD` only as an accounting unit. **No amount is a quote, tariff, owner-supplied requirement, measured cost, or procurement recommendation.** Results always remain `SIMULATED_UNREVIEWED`, with `quotesObtained`, `procurementAuthorized`, and `physicalValidationPerformed` set to `false`.

Each selected item and adaptation must have an explicit input record. Missing references, duplicate IDs, mismatched currencies, unsupported pathway assignments, non-finite values, and excessive labor requirements fail rather than becoming zero-cost assumptions. Monetary values are rounded to six decimal places only in JSON presentation; calculations and break-even arithmetic use the unrounded line items.

## Input and pathway policies

The strict envelope identifies the tooling, fabrication, labor-role, rental, site-adaptation, evaluation-hour, and policy assumptions. `appliesTo` limits where an item may be used, and each policy separately selects item IDs:

- **DIY (`diy`)** selects owned tooling and/or fabrication items and cannot select rentals. Selected tooling and fabrication records must permit DIY.
- **RENTAL (`rental`)** selects rental items and cannot select owned tooling or fabrication. Selected rental records must permit RENTAL.
- **HYBRID (`hybrid`)** must select at least one owned tooling/fabrication item and at least one rental item. Both groups must permit HYBRID.

Any pathway can select declared `CostScheduleDelta` adaptations by ID. This reuse keeps the economics scenario compatible with `geohazard_rural` without importing or modifying canonical BOM data. Only each delta's `costDelta` enters the monetary total. Its schedule and labor deltas remain available to the site workflow; the economics model does not silently price those hours again.

## Cost model

For a pathway at nonnegative operating horizon \(H\), each emitted line has the affine form

\[
C_j(H) = F_j + V_j H.
\]

The pathway total is \(C(H)=\sum_j C_j(H)\). Accumulation uses `math.fsum`, with checked finite multiplication and division. The result's summary fields reconcile to these lines within \(10^{-6}\) currency units before serialization.

### Selected startup tooling and ownership

Only tooling selected by the policy is charged. For tooling item \(i\),

\[
F_{tooling} = \sum_i startupCapex_i,
\qquad
V_{tooling} = \sum_i \left(maintenancePer_{h,i} +
\frac{startupCapex_i}{serviceLife_{h,i}}\right).
\]

Startup CAPEX therefore remains at zero operating hours, while maintenance and the linear replacement/life reserve start at zero. This is not depreciation, tax, residual-value, or accounting advice.

DIY and HYBRID also allocate the declared annual fixed ownership amount by use:

\[
V_{ownership}=\frac{annualFixedOwnershipCost}{ownershipHoursPerYear}.
\]

The allocation appears in `WEAR_MAINTENANCE`; it is not an additional up-front cash charge. RENTAL does not receive owned-tooling, fabrication, annual-ownership, or owned-microgrid charges.

### Fabrication material, components, and labor

For each selected fabrication item \(i\) with quantity \(q_i\),

\[
F_{material}=\sum_i q_i\,unitMaterialCost_i,
\qquad
F_{component}=\sum_i q_i\,unitComponentCost_i,
\]

\[
L=\sum_i q_i\,laborHoursPerUnit_i,
\qquad
F_{labor}=L\,ratePer_h,
\]

where the rate is resolved only from `fabricationLaborRole`. `L` must not exceed that role's `availableHours_h`; the calculator does not invent more time, workers, overtime, or a different wage. Labor is a **one-project fixed amount**, not multiplied by the operating-hour horizon. Other configured roles do not enter unless explicitly selected as the fabrication role.

Selected fabrication items also contribute their declared `hourlyWearReserve` to the variable wear/maintenance line. That hourly reserve is distinct from quantity-scaled fabrication labor and startup materials/components.

### Rental lifecycle proration, mobilization, wear, and energy

Each rental declares `HOUR`, `DAY_8H`, or `WEEK_40H`, corresponding respectively to \(u=1\), \(8\), or \(40\) operating hours solely for this synthetic lifecycle model:

\[
V_{rental,i}=\frac{ratePerBillingUnit_i}{u_i},
\qquad
R_i(H)=ratePerBillingUnit_i\frac{H}{u_i}.
\]

Delivery is a fixed one-project amount independent of \(H\):

\[
F_{mobilization}=\sum_i deliveryPerMobilization_i\,mobilizationsPerProject_i.
\]

Rental energy is \(E_i(H)=fuelOrEnergyPer_{h,i}H\). If `hourlyWearReserveIncluded` is `true`, the separate reserve must be zero and no additional wear is charged. Otherwise the declared reserve is added once per operating hour. This explicit switch prevents double counting without treating unknown wear as free.

**Linear proration is not an invoice.** It assumes fractional lifecycle use of hourly, eight-hour-day, and forty-hour-week rates. Actual rental agreements can impose whole-unit minimums, calendar-time charges, overtime, damage waivers, deposits, insurance, taxes, availability constraints, cleaning, fuel rules, delivery windows, and remobilization fees. A real comparison requires externally obtained, current human/vendor quotations and contract terms entered as new reviewed assumptions; the software neither obtains nor fabricates them.

DIY and HYBRID add `ownedMicrogridEnergyCostPer_h * H`. HYBRID adds both owned and selected rental energy assumptions. At \(H=0\), prorated rental, all hourly wear/maintenance, annual-ownership allocation, and energy are zero, but startup tooling, fabrication, one-project labor, mobilization, and selected site deltas remain.

### Site adaptation and negative totals

The fixed `SITE_ADAPTATION` line is the sum of selected signed `costDelta` values:

\[
F_{site}=\sum_k costDelta_k.
\]

A negative delta can represent a scenario saving, but the complete adapted `totalCost` must remain nonnegative at every requested evaluation. A negative total aborts for human correction; it is not clipped to zero or presented as a credit. Sensitivity studies should change explicit assumptions and rerun all horizons rather than editing a result or relying on a single crossing.

## Break-even interpretation

For two pathways, aggregate the unrounded lines into \(C_L(H)=F_L+V_LH\) and \(C_R(H)=F_R+V_RH\). If \(V_L\ne V_R\), the candidate is

\[
H_* = \frac{F_R-F_L}{V_L-V_R}.
\]

Only a finite, strictly positive crossing with nonnegative totals is reported. The result labels the lower-cost path at zero hours and at a probe above the crossing. If slopes are equal, there is no finite crossing: equal fixed costs produce an exact tie everywhere, while different fixed costs leave one path cheaper everywhere. A zero or negative candidate is not converted into a fictitious positive duration.

A break-even point is only where these two synthetic affine totals are equal. It does not include unconfigured risk, schedule value, financing, tax, resale, downtime, availability, quality, safety, engineering acceptance, or procurement feasibility, and it is not a recommendation.

## Worked synthetic example

`examples/economics/synthetic-pathways.json` evaluates 0, 80, 250, 600, and 1200 hours. All three rental records are deliberately selected together in RENTAL to expose all three billing formulas; this is a transparent arithmetic scenario, not a claim that one project should rent three machines.

The DIY policy selects both tools and both fabrication records:

| Component | Synthetic amount |
|---|---:|
| Startup tooling CAPEX | 7,500 |
| Materials | 12,000 |
| Components | 4,000 |
| 120 fabrication hours at 45/hour | 5,400 |
| Selected site delta | 1,100 |
| **Fixed total \(F_{DIY}\)** | **30,000** |

Its hourly amount is 4.00 ownership + 7.75 tooling life/maintenance + 1.50 fabrication wear + 6.00 owned energy = **19.25/hour**.

RENTAL has 1,600 mobilization plus a 1,400 site delta, so \(F_{RENTAL}=3,000\). Its prorated rental is 181.75/hour, energy is 17.00/hour, and only the week item's separate 0.50/hour wear is charged, giving \(V_{RENTAL}=199.25\).

HYBRID selects the fixture and attachment, plus the day and week rentals. Its 7,300 owned setup, 800 mobilization, and 400 site delta give \(F_{HYBRID}=8,500\). Its hourly amount is 12.75 owned/ownership + 64.00 day-rental/energy + 28.50 week-rental/energy/wear = **105.25/hour**.

Consequently:

| Comparison | Positive break-even |
|---|---:|
| DIY ↔ RENTAL | \((3,000-30,000)/(19.25-199.25)=150\) hours |
| DIY ↔ HYBRID | \((8,500-30,000)/(19.25-105.25)=250\) hours |
| RENTAL ↔ HYBRID | \((8,500-3,000)/(199.25-105.25)\approx58.510638\) hours |

At 250 hours, DIY and HYBRID both total **34,812.50** in synthetic currency units. These equalities demonstrate only the stated arithmetic.

## Running and verifying

From the repository root, the module API can be exercised without optional dependencies:

```sh
PYTHONPATH=src python3 -c 'from open_construction_equipment.economics import compare_pathways, economics_result_json, load_economics_input; print(economics_result_json(compare_pathways(load_economics_input("examples/economics/synthetic-pathways.json"))), end="")'
```

The accompanying `schemas/economics-input.schema.json` is Draft 2020-12 interchange documentation. Runtime parsing remains hand-written and dependency-free; `jsonschema` is optional for additional tests. No calculation performs physical validation, authorizes fabrication or procurement, releases a site, or approves equipment operation.
