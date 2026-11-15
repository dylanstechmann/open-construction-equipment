<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Candidate standards and regulatory register

**This is an applicability research list, not a compliance matrix.** OCE-CTL-01 does not claim conformity, certification, PL, SIL, ROPS/FOPS approval, or CE/UKCA/other marking. Standards are copyrighted. Their official current editions, amendments, corrigenda, national adoptions, normative references, exclusions, and regional legal obligations must be obtained and checked by qualified reviewers before design decisions or claims. Some documents may not apply to this battery-electric compact track loader or proposed autonomy.

| Reference | Potentially relevant topic | Application question / required action | Status |
|---|---|---|---|
| ISO 12100 | Safety of machinery; risk assessment and risk reduction | Establish base risk process, intended use/misuse, three-step method, and residual-risk records | Candidate; edition/jurisdiction TBD |
| ISO 17757 | Earth-moving machinery; autonomous and semi-autonomous machine system safety | Determine scope before any autonomy development beyond simulation; derive additional ODD/site requirements | Candidate; not invoked for sim-only phase |
| ISO 19014 series | Earth-moving machinery; functional safety | Determine machine-control system safety requirements, safety-related parts, analysis, and verification approach | Candidate series; parts/editions TBD |
| ISO 20474 series | Earth-moving machinery; general and machine-specific safety requirements | Identify applicable compact loader machine part and general safety requirements | Candidate series; applicable parts TBD |
| ISO 15817 | Earth-moving machinery; remote operator control systems | Assess only if remote control is ever proposed; not a general approval for autonomy | Conditional; remote control not in scope |
| ISO 13849-1 | Safety-related parts of control systems; design principles | Evaluate where this functional-safety route is applicable alongside earth-moving-specific requirements; determine PLr and validation needs | Candidate; no PL assigned |
| ISO 13850 | Emergency stop function and principles for design | Define stop categories/performance and reset without restart based on machine risk assessment | Candidate; circuit not designed |
| ISO 4413 | Hydraulic fluid power; general rules and safety requirements | Develop hydraulic design, component, hose, isolation, cleanliness, and test requirements | Candidate; values TBD |
| ISO 3471 | Roll-over protective structures (ROPS) | Determine applicability, performance criteria, laboratory evaluation, and seat/operator-system relationships | Candidate; CAD bars are not a ROPS design |
| ISO 3449 | Falling-object protective structures (FOPS) | Determine whether FOPS is required for intended use and establish independent evaluation/test needs | Candidate; no FOPS claim |
| ISO 2867 | Earth-moving machinery access systems | Engineer steps, handholds, platforms, and service access after actual geometry is defined | Candidate; access not detailed |
| IEC 60204-1 | Electrical equipment of machines | Determine applicable electrical protection, controls, enclosures, verification, and documentation requirements | Candidate where applicable; edition/jurisdiction TBD |

## Required regulatory work

A responsible owner must identify machinery, electrical, battery, charger, EMC/radio, transport, waste/battery, occupational/site safety, fire, environmental, and lifting-equipment obligations in every intended jurisdiction. Autonomous or remote operation, public roads, hazardous atmospheres, and lifting persons introduce additional requirements outside current scope.

## Compliance evidence rules

For each applicable clause, record official edition, applicability rationale, engineering requirement, design output, verification method, evidence version, deviation, and signed competent review. A purchased standard, passing simulation, supplier declaration, or model named “ROPS” is not sufficient by itself. Never reproduce tables or text beyond legally permissible quotation; store licensed source documents outside the public tree with access metadata.
