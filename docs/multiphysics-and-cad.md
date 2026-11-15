<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Synthetic multi-physics and CAD interchange

## Scope and evidence boundary

`physics.py` and `cad_blender.py` are standard-library, deterministic, AI-authored
trade-study software for **OCE-CTL-01** and **BUNKER-01**. Every result is
`SIMULATED_UNREVIEWED`. Inputs are synthetic, not owner- or site-supplied, and no
physical validation has occurred. Threshold flags are arithmetic screening
findings only: they are not `PASS`, `SAFE`, `RELEASED`, a rated capacity, or a
construction decision. Human `PG-nnn` gates remain unresolved. Physical
validation, construction authorization, operational release, and fabrication
release remain false.

The physics model is not a coupled finite-element, computational-fluid-dynamics,
soil-structure, stability, drainage, concrete-strength, or weather-safety solver.
The CAD model is a visualization and initial-state interchange, not surveyed
geometry, manufacturing CAD, or released fabrication data. No module invokes an
actuator or an external CAD/physics application.

## Inputs and deterministic API

- `examples/physics/synthetic-physics.json` conforms to
  `schemas/physics-input.schema.json`.
- `examples/cad/synthetic-scene.json` conforms to
  `schemas/cad-scene.schema.json`.
- Both schemas use JSON Schema Draft 2020-12. The schemas are optional
  interchange checks; the Python parsers independently enforce exact keys,
  types, ranges, provenance, references, and cross-field rules.
- `load_physics_input()` / `parse_physics_input()` and `load_cad_scene()` /
  `parse_cad_scene()` reject duplicate JSON keys, non-finite numbers, Boolean
  numbers, unknown fields, and invalid references before calculation.
- `evaluate_physics()` (or the stateless `PhysicsSimulator.run()`) returns frozen
  result dataclasses. `physics_result_json()` emits sorted, indented, UTF-8 JSON
  with a final LF. `write_physics_result()` writes only `result.json` beneath a
  selected output directory.
- `export_scene()` (or `CadExporter.export()`) generates all six CAD artifacts in
  memory, hashes their bytes, stages temporary files in the selected directory,
  and then replaces regular destination files. It refuses symlink destinations.
  `write_cad_export_result()` separately writes the manifest `result.json`.

Typical ignored output directories are `builds/physics/` and `builds/cad/`.
Generated files are not tracked source artifacts. Repeating the same input and
export produces byte-identical content; no clock, randomness, network, locale,
absolute repository path, or optional-package discovery enters the artifacts.

## Units and coordinates

Canonical runtime geometry uses SI metres, seconds, kilograms, newtons, kPa,
kN/m³, radians, and degrees Celsius as explicitly named in each field. JSON
combines camelCase names with unit suffixes such as `foundationLength_m`,
`verticalServiceLoad_N`, and `soilCohesion_kPa`. Boolean values are not numeric
inputs. Arithmetic rejects non-finite intermediates, zero denominators, and
nonzero underflow rather than silently clamping them.

CAD coordinates are local, relative, right-handed **x/y/z metres**, with z up and
yaw about +z. They are not georeferenced. GPS/GNSS, address, parcel, and similar
location keys are rejected. A box center is its geometric center; `size_m`
contains full x/y/z edge lengths. Each box has eight yaw-rotated vertices and
twelve outward-wound triangles. OBJ indices are one-based across all bodies.
OpenSCAD and FreeCAD convert metres to millimetres once; OBJ and MJCF retain
metres. MJCF uses radians and local coordinates.

## Screening equations

### Two-track terramechanics

For one track of length `L`, width `B`, and normal load `N_track`, there are two
equal tracks:

```
A_one = L B
W = 2 N_track
p_kPa = W / (2 A_one 1000)
z = p_kPa / K
τ_max = c + p_kPa tan(φ)
F_t = 2 A_one 1000 τ_max η
F_rr = C_rr W cos(β)
F_g = W sin(β)
margin = F_t - F_rr - F_g
```

`K` is the declared linear pressure-sinkage stiffness in kPa/m. This is a linear
sinkage and Mohr-Coulomb screen, not general Bekker-Wong applicability. The
sinkage flag is `THRESHOLD_EXCEEDED` only when `z` is greater than the supplied
maximum; equality remains within the model assumption. Signed negative margin
is preserved and is not a drawbar or stability rating.

### Bearing screen

```
q_kPa = V / (L B 1000)
FS = q_allow / q
utilization = q / q_allow
```

The allowable pressure is an external synthetic geotechnical assumption, not a
capacity calculated by this software. `FS >= requiredFS` is within the model
assumption; lower values exceed the screening threshold. Service load and all
geometry are strictly positive.

### Infinite homogeneous planar slope

With soil unit weight `γ` in kN/m³, vertical slice height `H`, slope angle `β`,
cohesion `c`, friction angle `φ`, and pore-pressure ratio `r_u`:

```
σ_n = γ H cos²(β)
τ_d = γ H sin(β) cos(β)
u = r_u σ_n
τ_r = c + (σ_n - u) tan(φ)
FS = τ_r / τ_d
```

kN/m² and kPa are dimensionally equivalent. The equivalent expression is
`c/(γH sinβ cosβ) + (1-r_u)tanφ/tanβ`. This approximation excludes complex
geometry, transient seepage, layered soils, reinforcement, and a professional
slope-stability assessment. Threshold equality is within the model assumption.

### Buoyancy screen

Using standard gravity `g = 9.80665 m/s²`:

```
U = ρ_water g V_displaced
R = m_resisting g
FS = R / U                       when U > 0
additional_mass = max(0, (FS_required U - R) / g)
```

Zero displaced volume produces `factorOfSafety: null`, zero additional mass, and
`NOT_APPLICABLE`, never JSON infinity. Additional mass is an algebraic deficit,
not a prescribed deadweight or anti-flotation design.

### Concrete temperature history

For chronological relative intervals `dt_i` at mean temperature `T_i`:

```
M_Nurse-Saul = Σ (T_i - T_datum) dt_i
T_K = T_C + 273.15
t_eq = Σ dt_i exp[-Ea/R (1/T_i,K - 1/T_ref,K)]
R = 8.31446261815324 J/(mol K)
```

Negative Nurse-Saul contributions remain in the raw diagnostic. Arrhenius age
uses absolute temperature. `targetReached` compares only `t_eq` with the supplied
synthetic target. It does not infer strength, stripping, formwork removal,
loading, curing acceptance, or authorization.

### Relative weather derating

```
cold = max(0, 1 - k_cold max(0, T_ref - T))
hot = max(0, 1 - (T - T_max)/max(1, T_max-T_min))   if T > T_max, else 1
temperatureFactor = min(cold, hot)
precipitationFactor = max(0, 1-p/p_max)              if p_max > 0
windFactor = max(0, 1-v/v_max)                       if v_max > 0
combined = temperatureFactor precipitationFactor windFactor
```

Zero precipitation/wind maxima produce factor zero for any nonzero sample and one
for a zero sample. Temperature below minimum, temperature above maximum,
precipitation above its maximum, and wind above its maximum add stop conditions
in that order. Hard-threshold equality does not itself add a stop condition.
These are synthetic productivity fractions, not safe/unsafe weather verdicts,
and fractional derating cannot override a stop condition.

## Generated CAD files

`export_scene()` writes exactly these six fixed basenames:

| File | Content |
| --- | --- |
| `scene.obj` | Wavefront vertices and outward triangles in metres; references exactly `scene.mtl`. |
| `scene.mtl` | Named diffuse/alpha materials plus roughness/metallic metadata comments; no textures. |
| `blender_scene.py` | Self-contained Blender 4.x scene generator with materials, meshes, rigid/kinematic settings, relative-time animation, and optional explicit save. |
| `ctl01_bunker_physics.xml` | Self-contained MuJoCo MJCF with ground plane, primitive boxes, initial poses, inertial values, and `freejoint` only on rigid bodies. |
| `scene.scad` | Parametric colored boxes and transforms in millimetres. |
| `scene_freecad.py` | FreeCAD `Part::Box` generator with centered placements, millimetres, and synthetic metadata. |

`result.json` contains the ordered artifact names, media types, SHA-256 hashes,
and byte sizes, not its own hash. Animation appears as actual Blender keyframes;
MJCF contains only initial poses and animation metadata comments, with no
actuator/controller claim. Static MJCF bodies have no free joint, rigid bodies
have one, and kinematic bodies are marked `mocap` without a free joint.

See [cad-external-tools.md](cad-external-tools.md) for manual, optional tool
commands and the validation boundary.
