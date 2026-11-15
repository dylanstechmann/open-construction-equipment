<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Engineering calculations

## Current scope and evidence boundary

The repository currently contains one executable engineering-arithmetic slice: **AN-LC-001A**, a static longitudinal load-moment calculation using three synthetic point masses and two ideal level supports. It is partial, agent-authored, and **UNREVIEWED**; acceptance is **NOT_ASSESSED**, no physical validation was performed, and [LC-001](../hardware/ctl01/mechanical/load-case-register.csv) remains **TBD**.

This calculation is not a stability rating, rated operating capacity calculation, operational pass/fail decision, structural verification, or fabrication release. It neither closes a hazard nor promotes the project out of Phase 0. Existing numeric design targets remain unvalidated concept inputs.

Read the complete model, hand arithmetic, uncertainties and exclusions in [AN-LC-001A](../hardware/ctl01/analysis/AN-LC-001A-static-longitudinal.md).

## Run and reproduce

From a source checkout:

```sh
PYTHONPATH=src python3 -m open_construction_equipment analyze \
  --input examples/analysis/synthetic-lc001.json \
  --output-dir builds/analysis/lc001 --json
```

The `--input` and `--output-dir` options have working defaults, so this is equivalent:

```sh
PYTHONPATH=src python3 -m open_construction_equipment analyze
```

After a non-editable wheel installation, `oce analyze` uses the bundled example and also works outside the source checkout. The output is ignored `builds/analysis/lc001/result.json`. It contains total mass, combined CG/resultant location, support reactions, signed moments about both supports, signed static moment margins, resultant interval inclusion, and a carefully conditioned forward zero-static-margin payload boundary. The last item is an algebraic condition only, never an allowable or recommended payload.

The result includes the full normalized input and its SHA-256 hash, `acceptanceStatus: NOT_ASSESSED`, `reviewStatus: UNREVIEWED`, `physicalValidationPerformed: false`, exclusions, and limitations. Deterministic JSON is emitted with sorted keys and no timestamps. The unified check runs it twice and compares output bytes.

Malformed input produces a controlled error and no traceback. Inputs use explicit SI values with no silent unit conversion; duplicate JSON keys, booleans as numbers, non-finite numbers, negative masses, non-positive bare-machine mass, unordered supports, missing provenance, and unknown trace IDs are rejected.

## Validation and optional schema tooling

[`schemas/engineering-analysis.schema.json`](../schemas/engineering-analysis.schema.json) is JSON Schema Draft 2020-12 for interchange. It describes status fields, exact stable analysis/trace IDs, units, and per-value synthetic provenance. Runtime loading and all calculations use only the Python standard library; **a JSON Schema package is optional and is not a runtime or test dependency**. The loader additionally enforces the cross-field requirement `frontX_m > rearX_m`.

If `jsonschema` is already available, the example and schema can be checked without changing runtime dependencies:

```sh
python3 - <<'PY'
import json
from pathlib import Path
from jsonschema import Draft202012Validator
schema = json.loads(Path('schemas/engineering-analysis.schema.json').read_text())
data = json.loads(Path('examples/analysis/synthetic-lc001.json').read_text())
Draft202012Validator.check_schema(schema)
Draft202012Validator(schema).validate(data)
print('engineering-analysis schema and example: valid')
PY
```

`oce validate` strictly loads the analysis JSON as part of generic JSON counts. In a source checkout it additionally resolves every trace ID against the design-input, load-case, hazard, safety-requirement and interface records and confirms the LC-001 evidence reference remains partial/unreviewed/TBD. Package-resource validation checks the bundled input without claiming those absent source documents were reviewed.

For the synthetic example, the main numeric results are:

| Quantity | Result |
|---|---:|
| Total mass | 2020 kg |
| Combined CG / resultant x | 0.144059405940594 m |
| Signed load moment about front support | -12993.81125 N·m |
| Signed load moment about rear support | 20682.22485 N·m |
| Minimum signed static moment margin | 12993.81125 N·m |
| Forward zero-front-margin payload boundary at x = 1.55 m | 1946.66666666667 kg |

These are outputs of hypothetical input geometry. They are not actual OCE-CTL-01 mass properties or limits, and the boundary is not a capacity result. See the analysis document for equations, support reactions, payload-boundary conditions, and all exclusions.

Software consistency checks do not establish physical correctness. Later calculations need independent hand review, source-controlled inputs with traceable provenance, documented uncertainty and acceptance criteria, and signed responsible engineering review before any physical use.
