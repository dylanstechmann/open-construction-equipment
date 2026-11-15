<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Optional external CAD and physics tools

The required offline test suite uses only Python's standard library. It does not
install, import, render, or execute Blender, OpenSCAD, FreeCAD, MuJoCo, CadQuery,
or `jsonschema`. Tool availability never changes generated artifacts, hashes, or
their unreviewed status. The commands below are **manual, opt-in local checks**
performed by a user in a suitable isolated working environment.

## Version and purpose matrix

| Tool | Optional target | Manual purpose | Required offline dependency? |
| --- | --- | --- | --- |
| Blender 4.x | `4 <= major < 5` | Execute the generated scene script, inspect meshes/materials/animation, optionally save a user-selected `.blend`. | No |
| OpenSCAD | Locally supported stable release | Parse or render `scene.scad`; export only to a user-selected path. | No |
| FreeCAD | Locally supported stable release with Python console/`FreeCADCmd` | Execute `scene_freecad.py` and inspect `Part::Box` geometry in mm. | No |
| MuJoCo 3.x | Python package `mujoco>=3.2,<4` | Headlessly load and briefly step the initial-state MJCF. | No |
| CadQuery 2.x | Python package `cadquery>=2.5,<3` | Optional independent local mesh/geometry experiments; not used by the exporter. | No |
| jsonschema 4.x | Python package `jsonschema>=4.23,<5` | Check both Draft 2020-12 schemas and validate example envelopes. | No |

Install optional Python packages only in an isolated environment chosen by the
user, using the user's normal package-management and network policies. The core
project retains `dependencies = []`; offline verification never downloads these
packages. Blender, OpenSCAD, and FreeCAD are applications, not pip runtime
requirements.

## Generate artifacts without external tools

From the repository, Wave 1's Python API can generate the ignored `builds/cad/`
artifacts without importing any optional application:

```sh
PYTHONPATH=src /home/vscode/.local/bin/python3.12 -c 'from open_construction_equipment.cad_blender import export_scene, load_cad_scene, write_cad_export_result; result = export_scene(load_cad_scene("examples/cad/synthetic-scene.json"), "builds/cad"); write_cad_export_result(result, "builds/cad")'
```

The command performs arithmetic and local file output only. It does not imply
that any external application has parsed or simulated the result.

## Blender 4.x

```sh
blender --background --python builds/cad/blender_scene.py
```

The generated script has a Blender 4.x major-version guard, creates mesh and
material data, sets box collision shapes and rigid-body modes, and inserts
relative-time keyframes. Saving is disabled unless the user explicitly sets an
output path:

```sh
OCE_BLENDER_OUTPUT=/user-selected/output/scene.blend blender --background --python builds/cad/blender_scene.py
```

Use a disposable Blender scene/profile for inspection. The script adds objects
to the current scene; it does not validate engineering geometry or create a
manufacturing release. Generated Python is compile-checked by required tests but
is not imported by them.

## OpenSCAD

```sh
openscad -o /user-selected/output/scene.csg builds/cad/scene.scad
```

A user may select another supported output extension. Rendering/export is never
part of the required gate. OpenSCAD dimensions and placements are millimetres;
colors are metadata/visualization aids, not material specifications.

## FreeCAD

Use the executable name supplied by the local installation:

```sh
FreeCADCmd builds/cad/scene_freecad.py
```

or:

```sh
freecadcmd builds/cad/scene_freecad.py
```

The generated script imports FreeCAD only when manually run inside FreeCAD. It
creates centered `Part::Box` objects in millimetres and records kind, physics
mode, and mass as synthetic metadata. It does not generate released drawings,
mesh tolerances, weld definitions, or fabrication instructions.

## MuJoCo 3.x headless loading

In an isolated environment that already contains the optional `physics` extra:

```sh
python -c 'import mujoco; model = mujoco.MjModel.from_xml_path("builds/cad/ctl01_bunker_physics.xml"); data = mujoco.MjData(model); mujoco.mj_step(model, data); print(model.nbody, data.time)'
```

A zero-step load can instead print model counts without calling `mj_step`. The
MJCF needs no OBJ mesh dependency. Its plane, primitive boxes, inertial values,
gravity, and timestep support an initial-state software smoke check only.
Animation is metadata, not a controller. Restitution is retained as synthetic
metadata rather than represented as a calibrated contact model. Successful XML
loading or stepping is not physical fidelity validation, a stability rating, or
permission to operate equipment.

## Optional schema and mesh checks

With `jsonschema` already available, tests use
`Draft202012Validator.check_schema()` and validate valid/invalid examples. When
it is absent, those checks skip. CadQuery can be used in separate local
experiments to inspect imported meshes, but it is not needed to generate OBJ,
OpenSCAD, FreeCAD, Blender, or MJCF content. Required mesh tests independently
check topology, outward normals, OBJ indices, and deterministic bytes.

`external_tool_report()` uses `shutil.which()` to report capability paths for
`blender`, `openscad`, `freecadcmd`/`FreeCADCmd`, and Python. It does not execute
those binaries or query versions. An available executable is only a capability
hint, not evidence of a completed check.

## Evidence and release boundary after manual checks

A successful parser, renderer, CAD-kernel import, or physics step establishes
only software interoperability for the supplied synthetic scene. It supplies no
site survey, geotechnical evidence, structural review, contact-model calibration,
manufacturing tolerance review, hazard closure, or physical test record. Update
no evidence status automatically. Qualified human review, signed evidence,
site/AHJ decisions, and all unresolved gates remain necessary outside this
software. Never interpret these commands as excavation, occupancy, confined-space
entry, energization, equipment-operation, procurement, or fabrication approval.
