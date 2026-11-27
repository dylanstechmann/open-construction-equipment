<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Synthetic powertrain and solar–hydrogen microgrid

## Evidence and operating boundary

`powertrain.py` is deterministic, standard-library-only, AI-authored trade-study
software for **OCE-CTL-01** and **BUNKER-01**. Every result is
`SIMULATED_UNREVIEWED`; physical validation and operational release remain
false. The input is synthetic, not owner- or site-supplied. All currency values
are unquoted assumptions, not tariffs, supplier quotations, procurement advice,
or a total installed-cost estimate.

The model does not certify an electrical, battery, hydrogen, combustion, fire,
acoustic, structural, pressure-system, or confined-space design. It does not
invoke hardware or calculate equipment setpoints. Energy, electrical,
hydrogen, fire, noise, and permit/AHJ reviews remain unresolved. In particular,
hydrogen production, compression, storage, and use require qualified design,
material-compatibility and embrittlement assessment, leak detection and
inspection planning, hazardous-area and ventilation analysis, fire review,
emergency planning, and applicable authorization. The hourly inspection reserve
is only a synthetic allowance and is not an inspection procedure or evidence
that inspection occurred.

## Input and deterministic output

`examples/powertrain/synthetic-microgrid.json` conforms to
`schemas/powertrain-input.schema.json` (JSON Schema Draft 2020-12). The Python
parser independently enforces exact keys, finite non-Boolean numbers, ranges,
unique task IDs, chronological relative-duration profiles, battery and hydrogen
storage bounds, an all-null or all-set electric acoustic triple, canonical
diesel-then-gasoline inputs, fixed synthetic provenance, and ISO-4217-shaped
currency labels. Optional `jsonschema` checks never become a runtime
requirement.

`compare_powertrains()` and `MicrogridSimulator.run()` independently evaluate
battery, PEMFC hydrogen, hydrogen-ICE, diesel, and gasoline paths. Each task and
each competing path starts from the configured initial battery/hydrogen state;
no depleted state leaks between tasks or paths. `powertrain_result_json()`
rejects energy-closure errors greater than `1e-9 kWh` and emits sorted,
indented UTF-8 JSON with a final LF. Monetary values are serialized to at most
six decimal places. `write_powertrain_result()` writes `result.json` only after
those checks.

## Interval load and dispatch equations

For a task with shaft energy `E_shaft`, auxiliary energy `E_aux`, shaft-to-
electric efficiency `η_shaft`, and profile intervals `dt_i`:

```
E_required = E_shaft / η_shaft + E_aux
T = Σ dt_i
E_load,i = E_required dt_i / T
E_heat,i = E_heat,demand dt_i / T
E_PV,i = E_available_DC,i η_DC_collection
```

An all-zero shaft and auxiliary input explicitly represents a zero-electrical-
energy task. The duration-proportional allocation does not silently turn a
multi-hour profile into one-hour intervals. Available PV energy is an input,
not a weather forecast or a nameplate-energy guarantee.

Every path uses collected PV directly against the interval load first. The
battery and hydrogen paths then use these rules:

1. **Surplus interval:** charge the LFP battery within its temperature-adjusted
   power and stored-energy limits. Only the remainder is eligible for hydrogen
   electrolysis and compression. Anything left is curtailed.
2. **Deficit interval:** discharge the battery within its temperature-adjusted
   power and accessible stored-energy limits. In a hydrogen path, the remaining
   deficit can withdraw stored hydrogen within reconversion-power and mass
   limits. Anything left is unserved.
3. **Fossil comparator:** after direct PV, the applicable diesel or gasoline
   generator supplies energy up to its interval power limit. Its independent
   fuel and logistics parameters are never borrowed from the other fuel.

For each task/path:

```
served = solar_direct + battery_discharge + hydrogen_electrical_output + generator_output
unserved = required - served
served + unserved = required                 (within 1e-9 kWh)
```

Each task result records `generatorOutput_kWh` at the electrical bus. Battery
and hydrogen paths report zero for this field. Before writing a result, the
serializer checks that the four electrical sources sum to served energy
within 1e-9 kWh. `solar_curtailed_kwh` is collected energy left after direct
use and all eligible storage production. No deficit is erased when a rated
power or storage limit is reached.

## Battery and DC/AC conventions

Let `SOC` be stored DC energy. On charge, grid/DC-bus input `C` adds
`C η_charge` to `SOC`. On discharge, withdrawing `D/η_discharge` from `SOC`
delivers `D` to the modeled DC work bus. The charge and discharge limits apply
to interval input and delivered output respectively. `battery_discharge_kwh`
is delivered energy, not the larger stored-side withdrawal. Charge loss is
`C(1-η_charge)` and discharge loss is
`D(1/η_discharge-1)`; each appears once.

The canonical example uses:

```
η_charge = 0.96
η_discharge = 0.96
η_AC_inverter = 0.925
η_battery,reported = 0.96 × 0.96 × 0.925 = 0.85248  (85.248%)
```

The interval simulation models direct DC work and therefore does **not** insert
an inverter into direct PV or battery-dispatch energy. The reported
`electricalRoundTripEfficiency` separately includes one AC inverter factor for
an AC-delivered battery round trip. It must not be multiplied into the DC
ledger a second time. Battery and hydrogen efficiencies are reported separately;
they are not averaged into an artificial hybrid efficiency.

### Cold derating

```
f(T) = 1                                      T >= T_reference
f(T) = max(0, 1-k_cold(T_reference-T))        T_cutoff < T < T_reference
f(T) = 0                                      T <= T_cutoff
```

The same `f` multiplies available stored energy above the minimum, remaining
charge room, maximum charge power, and maximum discharge power for that
interval. It cannot create negative capacity or a warm-weather bonus. At the
cutoff, battery charge and discharge are zero, so an unmet load remains visible.
This is a declared synthetic sensitivity curve, not a cell datasheet, BMS model,
thermal runaway assessment, or safe charging-temperature limit.

## Hydrogen production, storage, and reconversion

The sole hydrogen energy-density constant is:

```
LHV_H2 = 1000/30 = 33.333333... kWh/kg
```

When electrolyzer and compressor both draw from the same post-battery solar
surplus `E_surplus`, and `c_comp` is compression energy in kWh/kg:

```
specific_solar_input = LHV_H2/η_electrolyzer + c_comp
m_produced = E_used / specific_solar_input
E_used = m_produced × specific_solar_input
```

Production is the minimum mass allowed by surplus, electrolyzer power times
interval duration, and remaining storage capacity. The electrolyzer power cap
applies to `m LHV_H2/η_electrolyzer`; compression energy remains explicitly in
the shared-surplus denominator. If storage is full, production and associated
water demand are zero. No hydrogen can be withdrawn from an empty store.

For PEMFC or hydrogen-ICE converter efficiency `η_converter`, one AC inverter is
applied on withdrawal:

```
E_AC = m_consumed LHV_H2 η_converter η_AC_inverter
m_withdrawn <= stored mass
E_AC <= maximum_reconversion_power × dt
η_H2 = η_electrolyzer η_converter η_AC_inverter /
       (1 + η_electrolyzer c_comp/LHV_H2)
```

The canonical PEMFC chain uses `η_electrolyzer=0.70`,
`η_converter=0.50`, `η_AC_inverter=0.925`, and `c_comp=4 kWh/kg`, yielding
approximately **29.866%**, inside the intended 25–32% synthetic example range.
The hydrogen-ICE path uses its own 30% converter assumption; neither converter
efficiency is applied twice. Custom PEMFC chains outside 25–32% are retained
and generate an explicit comparison warning rather than being clamped. Power,
storage, and interval availability can make realized energy capture lower than
the nominal chain efficiency.

### Water demand

```
deionized_water_l = hydrogen_produced_kg × configured_water_l_per_kg
```

The configured range is 9–15 L/kg; the canonical assumption is 12 L/kg. This is
only the declared deionized-water input. It is not a site water balance,
stoichiometric proof, purification-system design, wastewater estimate, or
utility commitment.

### CHP and niches

For `WINTER_CHP` only:

```
recovered_heat_i = min(E_heat,i,
                       m_consumed,i LHV_H2 × CHP_recovery_fraction)
unmet_heat = heat_demand - Σ recovered_heat_i
```

Recovered heat cannot exceed either cap. It is an algebraic potentially
recoverable quantity, not a verified delivery temperature, heat exchanger
design, or usable thermal service. Other use cases recover zero modeled CHP
heat.

The higher battery round-trip efficiency ordinarily makes batteries preferable
for frequent daily cycling in this arithmetic. `daily_battery_preferred` also
requires battery served energy to be no lower and the declared battery loss rate
`1/η_battery-1` per delivered kWh to be below the corresponding PEMFC rate. The
result includes the exact efficiencies, aggregate conversion losses, and loss
rates used; it is not a universal technology ranking.

`SEASONAL_CURTAILMENT` describes a narrower niche: after direct work and
eligible battery charging, otherwise-curtailed long-duration surplus can be
stored as hydrogen. A battery being full is sufficient, but a power-limited
battery can also make surplus eligible. The ledger does not reclassify ordinary
daily throughput as seasonal value. `WINTER_CHP` can add value only when both
hydrogen consumption and coincident recoverable heat demand exist.

## Fossil fuel, logistics, noise, and exhaust

For generator output `E_gen`:

```
fuel_l = E_gen / (fuel_LHV_kWh_l × η_generator)
refill_events = max(0, ceil(fuel_l/tank_capacity_l)-1)
refill_delivery_km = refill_events × refill_delivery_round_trip_km
delivery_cost = refill_delivery_km × delivery_cost_per_km
```

Zero generator deficit means zero fuel and refills. Delivery distances are
synthetic round-trip logistics, not routes or supplier commitments. A task peak
above the applicable discharge, reconversion, or generator rating emits
`PEAK_POWER_EXCEEDED`; interval energy caps independently preserve energy
closure.

The acoustic calculation is only free-field geometric spreading:

```
L(r) = L0 - 20 log10(r/r0)
r_target = r0 × 10**((L0-L_target)/20)
```

The radius is bounded below by `r0`; target equality returns `r0`. Terrain,
barriers, ground effect, atmosphere, weather, directivity, multiple sources,
reverberation, dose, code compliance, and safe occupancy are excluded. Fossil
systems always have input-based estimates. Electric systems return `noise:
null` unless the optional measured/synthetic source triple is supplied; the
model never invents a zero-dBA electric source. Confined tasks set
`confinedSpaceReviewRequired`, and fossil confined tasks also emit
`CONFINED_EXHAUST_REVIEW` even for a small load.

CO and NOx ppm values remain source-input indicators only. They are not plume,
dispersion, dose, ventilation, exposure, or safe-entry calculations. Likewise,
`conversionLossHeat_kwh` is only an accounting residual from charge/discharge,
electrolysis/compression/reconversion, or fuel conversion. It is not a measured
infrared signature, exhaust-temperature prediction, or proof of detectability.

## CAPEX, OPEX, and reconciliation

Path-specific one-time component sets are listed in
`systemCapexByPath[].componentKeys`:

- Battery: solar and battery.
- PEMFC/H2-ICE: solar, battery, electrolyzer, hydrogen compressor, hydrogen
  storage, and only the applicable converter.
- Diesel/gasoline: solar and only the applicable generator.

For task duration `t` and service life `L`:

```
allocated_capex = path_system_capex × t/L
battery_opex = t × battery_maintenance_per_h
hydrogen_opex = water_l × water_cost_per_l
                + t × (battery_maintenance_per_h + hydrogen_inspection_per_h)
fossil_opex = fuel_l × fuel_cost_per_l + delivery_cost
              + t × ice_maintenance_per_h
```

The hydrogen inspection allowance includes synthetic leakage/embrittlement
inspection reserve, but does not discharge those reviews. Allocated task CAPEX
and unallocated one-time system CAPEX are separate labels; adding both as though
they were independent purchases would double count capital. Operating cost does
not secretly include allocated CAPEX. All paths use the same currency label,
and all costs remain synthetic and unquoted.

### Battery stock across a task

For paths with an LFP battery, each task row includes `batteryStorage` with opening and closing kWh, charging input, and combined charge/discharge losses. Opening stock plus charging input equals closing stock plus delivered battery discharge plus battery conversion loss. The generator comparators use `null` for this field. Each representative task starts from its configured opening stock.

Each path reports `solarCollected_kWh` after the declared DC collection efficiency. This total reconciles with direct solar delivery, battery charging input, hydrogen production input, and curtailed solar. Initial stored energy and generator output are external to that total.
