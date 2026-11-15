<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Geohazard, waterways, land shifting, rural permits, and privacy

`open_construction_equipment.geohazard_rural` is an AI-assisted, standard-library
trade-study module. It evaluates anonymous synthetic inputs in SI units. It is not
a survey, geotechnical or structural design, hydrologic study, acoustic
certification, purchase recommendation, permit determination, or authorization
to excavate, place spoil, transport equipment, occupy a structure, or operate a
drainage system.

The two canonical inputs are:

- `examples/geohazard/synthetic-screen.json` (`mode: screen`): independent
  `CANDIDATE-*` labels and varied synthetic factors; and
- `examples/geohazard/synthetic-adapt.json` (`mode: adapt`): one `EXISTING-SITE`
  with explicit synthetic adaptation cost/schedule/labor assumptions.

`schemas/geohazard-rural.schema.json` describes Draft 2020-12 interchange. The
runtime parser is stricter where JSON Schema cannot prove uniqueness,
self-intersection, privacy, finite arithmetic, or cross-field invariants. The
schema is not a substitute for the parser.

## Privacy threat model

The privacy boundary assumes that accidentally supplied real-world identifiers
could reveal a person, household, property, work site, or neighboring receiver.
It therefore fails closed **before typed parsing, calculation, or report
creation**. `reject_private_location_data` recursively scans object keys, array
items, and every raw string.

Forbidden key tokens include latitude/longitude, `lat`/`lon`, GPS/GNSS,
geohashes, plus codes, street or postal fields, APN/assessor/deed references,
parcel/tax/legal-location identifiers, and real-property identifiers. Matching
uses underscore, punctuation, and camelCase token boundaries. Consequently
`siteLatitude`, `parcelId`, and `legalLocation` fail, while `translation_m`,
`platform`, and ordinary words containing those letters do not produce an
arbitrary-substring false positive.

Raw strings are also checked for textual coordinate assignments, GPS/GNSS
values, geolocation URL queries, coordinate pairs, plus codes, and common postal
street forms. This is deliberately conservative rather than a promise that all
possible private information can be detected. A caller must remove or protect
private source material before invoking the module; generated anonymity is not
anonymization of a real dataset.

Accepted location-adjacent vocabulary is limited in purpose:

- `anonymousLabel`, restricted to `CANDIDATE-[A-Z0-9-]+` or exactly
  `EXISTING-SITE`;
- `featureLabel`, restricted to `FEATURE-[A-Z0-9-]+`;
- `vertices_local_m`, whose points contain only relative `x_m` and `y_m`; and
- explicitly declared relative distances, heights, depths, setbacks, and
  clearances.

The unnamed local origin `(0, 0)` is the conceptual structure reference, not a
geodetic coordinate. Negative local coordinates are valid. A waterway, road, or
sightline has exactly two vertices; wetland, closed-depression, and structure
areas have at least three vertices forming a finite, nonzero, simple polygon.
Labels and vertices never identify authoritative boundaries.

Reports contain anonymous labels, derived distances/metrics, decisions, gates,
and adaptation arithmetic only. They do **not** contain source vertices, raw
feature narratives, envelope metadata, official identifiers, or private source
strings. `locationDataRetained` is always false. Strict unknown-key rejection
also prevents authorization, reviewer, resolution, and evidence-completion
fields from being smuggled through an input.

## Local geometry and independent risks

`minimum_feature_distance` computes the Euclidean distance from `(0, 0)` to a
line segment or polygon boundary. A point inside or on an area returns zero.
This is local geometric arithmetic, not a measured professional feature
distance. `WaterProfile` professional distances remain independently declared;
a null waterway/wetland distance remains `UNKNOWN` rather than being replaced by
invented geometry.

`assess_risks` emits one assessment per domain. No aggregate score can average
away a high or unknown domain.

| Domain | Review or high condition |
|---|---|
| Closed depression | Distance is `<=` its review distance. |
| Karst bedrock | Depth is `<=` its review threshold; null is unknown. |
| Subsidence | The declared LOW/MODERATE/HIGH/UNKNOWN level is retained. |
| Groundwater | Depth is `<=` its review depth; null is unknown. |
| Waterway/wetland | Distance `<` required setback is a modeled hard violation; null is unknown. Equality is not a violation, but still requires environmental/AHJ confirmation. |
| Flood | Positive declared 100-year depth requires review; null is unknown. |
| Slope | Modeled factor of safety `<` required value; null is unknown. |
| Expansive clay | The declared risk level remains independent. |
| Land shifting | Rate `>` the declared annual review threshold. |
| Solar resource | Mean daily insolation `<` declared minimum. |
| Winter design | Design temperature `<` declared minimum. |
| Road axle | Known transport axle load `>` lowest known route limit; null limit is unknown. |
| Overhead access | Clearance `<` transport height + required clearance; null is unknown. |
| Sightline | Positive requested visual-screen height requires privacy/noise review. |

The acoustic comparison uses the declared 15 m source level and the greater of
receiver target and ambient levels:

```text
r = max(15 m, 15 m * 10 ** ((source_dBA_at_15m - max(target_dBA, ambient_dBA)) / 20))
```

A nearest receiver/sightline distance below `r` requires review. This inverse
square free-field geometric comparison does not model terrain, barriers,
reflection, weather, spectra, tonality, duration, background uncertainty, or a
legal noise limit. It never establishes compliance.

## Mode A: candidate screening

Each candidate is evaluated independently, including its permits and privacy
berm cap:

```text
requested_berm_m3 = privacyBermLength_m * privacyBermCrossSection_m2
reported_berm_m3 = min(requested_berm_m3, availableCompactedSpoil_m3)
```

Decisions have deliberately narrow meanings:

- `REJECT_ON_MODELED_CONSTRAINT`: a declared waterway/wetland distance is inside
  its required setback, known axle load exceeds the route limit, or known
  overhead clearance is insufficient. Unknown values are not treated as hard
  rejections.
- `ENGINEERING_REVIEW`: any high or unknown risk, or any triggered permit topic,
  remains. This includes conditions that cannot be converted into a simple hard
  geometric constraint.
- `RELATIVE_CANDIDATE`: none of those review/reject conditions fired in the
  synthetic model. This still is not approval, suitability, a recommendation,
  or permission to buy.

Ordering is deterministic: decision severity, explicit risk severity ranks,
counts of non-low risks and triggered permit topics, then anonymous label. It is
a triage order, not a value or preference score. Every candidate retains every
unresolved gate, and `purchaseRecommendationMade` is always false.

## Mode B: adaptation of an existing site

Mode B does not reject the parcel or pretend that added cost resolves a hazard.
Adaptations receive sequential `SA-001`, `SA-002`, ... identifiers in the fixed
trigger order below. Each triggered kind must have exactly one declared
`AdaptationAssumption`; a missing one aborts the entire calculation. No zero
cost, zero delay, density, volume, mass, or geometry is silently invented.

| Order/kind | Trigger and modeled result |
|---|---|
| `SHALLOW_MOUND` | Known groundwater or karst depth is **less than** baseline excavation depth, or declared subsidence is HIGH. Selects `SEMI_BURIED_EARTH_BERMED_MOUND`, retains specialist design, and emits no excavation plan. Multiple causes create only one adaptation. |
| `CELLULAR_RAFT` | Expansive clay is MODERATE/HIGH/UNKNOWN, or land shift exceeds its threshold. Replaces the baseline strip concept with `STIFFENED_CELLULAR_RAFT_ON_GEOGRID`; geotechnical and structural gates stay open. |
| `ANTI_FLOTATION_COLLAR` | Positive supplied displaced volume gives resisting/uplift factor below the site requirement. Reports only a synthetic dead-weight volume. Zero displaced volume does not produce infinity or a collar trigger. |
| `REDUNDANT_SOLAR_DRAINAGE` | Anti-flotation triggers or groundwater/flood is not LOW (including UNKNOWN). Allocates two independent solar sump concepts with battery backup. The count `2` is not hydraulic sizing, verified redundancy, or a reliable life-safety system. |
| `PRIVACY_SPOIL_BERM` | Positive requested berm volume or requested screen height. Reports `min(request, available spoil)` and includes any shortfall in the reason. It never conjures spoil or authorizes placement/compaction. |
| `WATERWAY_SETBACK` | Waterway/wetland violation or unknown distance. Requests environmental/AHJ review; the software cannot move a feature. |
| `ACCESS_REVIEW` | Axle/clearance violation or unknown. Requires route review and grants no transport approval. |

Signed assumption deltas are retained on each adaptation in adaptation-ID
order. `totalCostDelta` and `totalScheduleDelta_h` are finite sums of those original values. Labor deltas
remain line items. Currency comes from the parent site and every delta must
match it. These are unquoted synthetic assumptions, not supplier prices or an
approved budget/schedule.

### Anti-flotation collar arithmetic

For supplied synthetic displaced volume `V`, water density `rho_w`, resisting
mass `m`, required factor `FS_req`, concrete density `rho_c`, and collar
submerged fraction `f`:

```text
U = rho_w * g * V
R = m * g
g = 9.80665 m/s2
additional_collar_volume = max(0, (FS_req*U - R) /
    (g * (rho_c - FS_req*f*rho_w)))
```

The denominator accounts for both collar mass and its specified displaced-water
fraction. A nonpositive denominator raises `ConfigError` for specialist
correction; the module never returns an infinite collar volume. No collar
geometry, reinforcement, concrete mix, released mass, safe installation method,
or structural adequacy is inferred.

## Rural permit exemption candidates versus triggers

Rural unincorporated status, agricultural-accessory candidacy, and nonhabitable
utility use together can produce only the named
`RURAL_AGRICULTURAL_ACCESSORY_EXEMPTION` finding with value
`EXEMPTION_CANDIDATE`. It is not an exemption. Every assessment set also contains
`AHJ_DETERMINATION = AHJ_CONFIRMATION_REQUIRED`; `ahjDeterminationObtained` must
be false in this release.

| Topic | Declared circumstance | Finding |
|---|---|---|
| Rural agricultural accessory | All three candidate conditions true | `EXEMPTION_CANDIDATE`, still requiring written AHJ determination |
| Grading/SWPPP | Ground disturbance `>=` declared trigger area (equality included) | `TRIGGERED` |
| Well/septic | Well or septic work true | `TRIGGERED` for specialist/AHJ review |
| Driveway culvert | New driveway culvert true | `TRIGGERED` for road/drainage/AHJ review |
| Any topic without a positive trigger | Input below threshold or false | `AHJ_CONFIRMATION_REQUIRED`; never an automatic exemption |
| Overall determination | Always | `AHJ_CONFIRMATION_REQUIRED` |

Other obligations can apply regardless of these flags. Local zoning, building,
floodplain, wetland, waterway, erosion-control, health, utility, road, fire,
environmental and other authorities make their own determinations from actual
evidence. The permit matrix is a review checklist, not legal advice.

## Required unresolved human gates

Every result carries sorted `SG-001` through `SG-009` records with status
`UNRESOLVED`, no reviewer/signature/completion fields, and matching gate-ID
lists. Physical validation and site-engineering completion remain false;
construction authorization remains false where that field applies.

| Gate | Discipline | Required evidence scope |
|---|---|---|
| SG-001 | Geotechnical | Qualified soil, rock, karst, groundwater, expansive-soil, and movement investigation |
| SG-002 | Structural | Signed foundation, mound, collar, and load-path review |
| SG-003 | Excavation | Qualified excavation and protective-system review before ground disturbance |
| SG-004 | Hydrology | Site flood, groundwater, buoyancy, and drainage review |
| SG-005 | Environmental | Waterway, wetland, grading, drainage, and spoil review |
| SG-006 | Permit/AHJ | Written AHJ determinations for all candidate topics |
| SG-007 | Road access | Route, axle, overhead, culvert, and transport review |
| SG-008 | Electrical | Qualified solar-pump, battery, wiring, control, and failure-mode review |
| SG-009 | Privacy/noise | Visual, acoustic, receiver, and spoil-placement review |

Results are deterministic frozen-dataclass transformations with canonical,
sorted, finite JSON. Successful software completion never closes a human gate
or converts a modeled finding into evidence of safety.
