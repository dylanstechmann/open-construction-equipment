<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# AN-LC-001A — static longitudinal load-moment arithmetic

**Status:** agent-authored, partial, synthetic, and **UNREVIEWED**.<br>
**Acceptance:** **NOT_ASSESSED**.<br>
**Physical validation performed:** **false**.<br>
**Scope:** deterministic two-dimensional static equilibrium only. This is not a stability rating, rated operating capacity calculation, operational pass/fail assessment, or fabrication release.

## Purpose and trace

AN-LC-001A is a narrow software-checked vertical slice for [LC-001](../mechanical/load-case-register.csv). LC-001 remains `TBD`; the register identifies this document only as partial unreviewed analysis. It does not close any requirement or hazard.

The stable trace IDs below were checked against the existing source records:

| ID | Existing source | Relevance / remaining gap |
|---|---|---|
| DI-MASS-001 | [design inputs](../design-inputs.json) | Operating-mass target context; its 2200 kg value is **not** imported into this synthetic example. |
| DI-ROC-001 | [design inputs](../design-inputs.json) | Capacity target context; its 500 kg target is neither an input nor a derived result here. |
| SR-006 | [safety requirements](../safety/safety-requirements.csv) | Stability/structure/hydraulic derivation remains required and unverified. |
| HZ-005 | [hazard register](../safety/hazard-register.csv) | Tipover hazard remains open and unassessed. |
| IF-MEC-001 | [interface control](../interface-control.md) | Chassis/track reactions and alignment remain TBD. |
| IF-MEC-002 | [interface control](../interface-control.md) | Lift-arm pivot reactions, motion and retention remain TBD. |
| IF-MEC-003 | [interface control](../interface-control.md) | Attachment moment, engagement and retention remain TBD. |
| IF-MEC-004 | [interface control](../interface-control.md) | Attachment mass/CG envelope and lock remain TBD. |

Every numeric input in [`examples/analysis/synthetic-lc001.json`](../../../examples/analysis/synthetic-lc001.json) carries its own provenance object and trace IDs. All eight values are hypothetical and agent-authored for arithmetic demonstration. None was extracted from OpenSCAD, measured, supplied by the owner, or released as machine geometry. The 180 kg synthetic payload is not a capacity claim.

## Model and free-body/support idealization

Three point masses represent the bare machine, attachment, and payload. They have masses \(m_i\) in kg and longitudinal centers of gravity \(x_i\) in metres. Two ideal supports lie on a level, rigid support line at rear coordinate \(r\) and front coordinate \(f\), with \(f > r\). Vertical downward forces \(W_i=m_i g\) act at the point-mass locations; algebraic upward support reactions \(R_r\) and \(R_f\) act at \(r\) and \(f\).

```text
              machine          attachment       payload
                W_m ↓              W_a ↓            W_p ↓
--------|---------------|--------------|---------------|--------  +x forward
        r               Combined CG / resultant       f
        ↑ R_r                                         ↑ R_f
```

The drawing is schematic rather than machine geometry. Actual distributed track contact, terrain, attachment load paths, and hydraulic forces are replaced by this deliberately limited abstraction. The vertical gravity resultant acts through the combined CG, so `resultantX_m` equals `combinedCgX_m` in this model. There are no lateral degrees of freedom.

The implementation uses conventional standard gravity \(g=9.80665\ \mathrm{m/s^2}\), a defined conversion constant rather than a measured local gravitational value. This cancels from the CG, resultant-location, and payload-boundary equations, but not from newton or newton-metre outputs.

## Sign convention and equations

The x axis is positive forward and all input lengths are metres. Signed load moment about support \(s\) is positive toward forward x:

\[
M_s = g \sum_i m_i(x_i-s)\quad (\mathrm{N\,m}).
\]

Total mass, mass-weighted combined CG, and vertical resultant location are:

\[
M=\sum_i m_i,\qquad x_{CG}=\frac{\sum_i m_i x_i}{M},\qquad x_R=x_{CG}.
\]

With support span \(L=f-r\), static vertical force and moment equilibrium give:

\[
R_f=\frac{Mg(x_R-r)}{L},\qquad R_r=\frac{Mg(f-x_R)}{L}.
\]

These algebraic reactions are reported without clamping. A negative value means that the simplified support would need to pull down; it is not modeled as retained contact.

For this report, the front static moment margin is minus the signed front load moment and the rear static moment margin is the signed rear load moment:

\[
B_f=-M_f=Mg(f-x_R),\qquad B_r=M_r=Mg(x_R-r),
\]
\[
B_{min}=\min(B_f,B_r).
\]

These are signed single-case arithmetic quantities, **not allowable moments or evidence of a stability margin against a criterion**. No safety factor is applied. The location-only boolean is true exactly when \(r \le x_R \le f\); equality at either support is included.

### Forward zero-static-margin payload boundary

Holding the supplied payload load center \(x_p\) fixed and keeping machine and attachment unchanged, the unscaled front equilibrium term is:

\[
A_0=m_m(x_m-f)+m_a(x_a-f).
\]

A finite positive forward boundary is reported only if \(x_p-f>0\) and \(A_0<0\). Then \(B_f=0\) occurs at:

\[
m_{p,0}=\frac{-A_0}{x_p-f}>0.
\]

Otherwise `payloadMass_kg` is `null` and `reason` explains why no finite positive forward boundary exists. A baseline with zero front margin therefore yields `null`, not a misleading zero payload capacity. A load center at or behind the front support also yields `null`. The reported boundary is solely an algebraic zero-margin condition for the fixed inputs; it is not a recommended load, an allowable payload, or a rated capacity.

## Worked arithmetic for the synthetic example

Inputs are \(m_m=1600\ \mathrm{kg}\), \(x_m=-0.15\ \mathrm m\); \(m_a=240\ \mathrm{kg}\), \(x_a=1.05\ \mathrm m\); \(m_p=180\ \mathrm{kg}\), \(x_p=1.55\ \mathrm m\); \(r=-0.90\ \mathrm m\); and \(f=0.80\ \mathrm m\). Thus \(L=1.70\ \mathrm m\).

\[
M=1600+240+180=2020\ \mathrm{kg},
\]
\[
\sum m_i x_i=1600(-0.15)+240(1.05)+180(1.55)
=-240+252+279=291\ \mathrm{kg\,m},
\]
\[
x_R=x_{CG}=291/2020=0.144059405940594\ \mathrm m.
\]

About the front support:

\[
1600(-0.15-0.80)+240(1.05-0.80)+180(1.55-0.80)
=-1520+60+135=-1325\ \mathrm{kg\,m},
\]
\[
M_f=9.80665(-1325)=-12993.81125\ \mathrm{N\,m}.
\]

About the rear support:

\[
1600(-0.15+0.90)+240(1.05+0.90)+180(1.55+0.90)
=1200+468+441=2109\ \mathrm{kg\,m},
\]
\[
M_r=9.80665(2109)=20682.22485\ \mathrm{N\,m}.
\]

Consequently, \(B_f=12993.81125\ \mathrm{N\,m}\), \(B_r=20682.22485\ \mathrm{N\,m}\), and \(B_{min}=12993.81125\ \mathrm{N\,m}\). The algebraic reactions are:

\[
R_f=20682.22485/1.70=12166.0146176471\ \mathrm N,
\qquad R_r=12993.81125/1.70=7643.41838235294\ \mathrm N.
\]

Their unrounded sum is \(2020g=19809.433\ \mathrm N\). For the forward boundary:

\[
A_0=1600(-0.15-0.80)+240(1.05-0.80)=-1460\ \mathrm{kg\,m},
\]
\[
m_{p,0}=1460/(1.55-0.80)=1946.66666666667\ \mathrm{kg}.
\]

The example has `resultantWithinSupportInterval: true`; this records only coordinate inclusion and is not operational acceptance. Displayed arithmetic above is independently hand-rearranged; serialized IEEE-754 double-precision results may differ in the final decimal digits. No rounding is used to establish a decision or threshold.

## Assumptions and uncertainty

- The machine, attachment, and payload are rigid point masses with fixed, exactly supplied CG coordinates; lift-arm geometry and load paths do not change.
- Gravity is vertical, the support line is level and rigid, and only two ideal longitudinal support reactions exist.
- Static equilibrium is assumed with no acceleration, impact, tire/track deformation, contact redistribution, friction requirement, or lateral behavior.
- Input values are invented synthetic numbers with no tolerance distribution, calibration record, dimensional chain, supplier certificate, or measurement uncertainty. Floating-point reproducibility is not engineering uncertainty quantification.
- Local gravity, mass tolerances, CG uncertainty, attachment uncertainty, support-contact uncertainty, and sensitivity to those variations are unassessed.
- Source-register links establish context only. They do not transform target or assumption values into reviewed evidence.

A real engineering assessment would require reviewed geometry and mass properties, explicit uncertainty/sensitivity treatment, contact and load-path models, applicable methods and acceptance criteria, and signed responsible review. None is inferred here.

## Exact reproduction

From a source checkout with Python 3.11+:

```sh
PYTHONPATH=src python3 -m open_construction_equipment analyze \
  --input examples/analysis/synthetic-lc001.json \
  --output-dir builds/analysis/lc001 --json
```

From a non-editable wheel installation, the same bundled default input works away from the checkout:

```sh
oce analyze --json
```

The command writes deterministic `result.json` to `builds/analysis/lc001` by default. The file includes the full normalized input, a SHA-256 hash of the compact canonical normalized input, arithmetic outputs, exclusions, and limitations. It has no wall-clock data. `python3 tools/check_all.py` runs the analysis twice and requires byte-identical JSON.

## Exclusions and limitations

This analysis excludes slope and cross-slope; braking, acceleration and turning; terrain compliance, track slip and changing support contact; dynamic/impact/transient loads; structural strength, deflection, buckling and fatigue; hydraulic capacity, pressure and load-holding behavior; attachment retention/interface strength; standards tipping definitions; protective-structure performance; safety factors; and operational release. It does not establish stability, rated operating capacity, structural adequacy, hydraulic adequacy, fatigue life, standards compliance, safety, or readiness to build/operate.

See [engineering calculations](../../../docs/engineering-calculations.md), [engineering status](../../../docs/engineering-status.md), and [validation and release](../../../docs/validation-and-release.md). Agent execution and passing software tests are partial software-arithmetic evidence only, never physical validation or owner engineering review.
