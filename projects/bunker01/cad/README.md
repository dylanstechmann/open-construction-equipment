<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# BUNKER-01 visualization-only CAD

> **NOT FOR CONSTRUCTION, EXCAVATION, ENTRY, OCCUPANCY, OR PROTECTIVE USE.** This self-contained OpenSCAD model depicts a civilian non-habitable utility-enclosure concept. It is not structural CAD, a released design, a bill-of-material source, a safe excavation/support layout, or evidence of code compliance.

## Exact synthetic parameters

`parameters.scad` uses **millimetres**. All values are AI-authored geometric assumptions and must remain consistent with the requirements and any later synthetic calculator example.

| OpenSCAD parameter | Value | Meaning and limitation |
|---|---:|---|
| `internal_length` | 4000 mm (4.0 m) | Internal display length |
| `internal_width` | 3000 mm (3.0 m) | Internal display width |
| `internal_height` | 2400 mm (2.4 m) | Internal display height; not a code clearance |
| `wall_thickness` | 250 mm (0.25 m) | Display solid only; **not a structural selection** |
| `floor_thickness` | 250 mm (0.25 m) | Display solid only; **not a structural selection** |
| `roof_thickness` | 300 mm (0.30 m) | Display solid only; **not a structural selection** |
| `working_space` | 750 mm (0.75 m) | Excavation-envelope display allowance; **not safe working clearance, slope, shoring, or access design** |
| `drainage_layer` | 200 mm (0.20 m) | Display drainage zone; **not material, hydraulic, or excavation design** |
| `roof_cover` | 500 mm (0.50 m) | Display cover depth; **not structural cover, frost depth, or protection claim** |

Opening and vent-path display geometry is derived proportionally, not engineered. The model includes floor/walls/roof, an entrance void, schematic vent pathways, a drainage zone, translucent roof cover and excavation envelope. It deliberately contains **no reinforcement details**, concrete specification, joints, shoring, safe slopes, stairs, door hardware, pipe sizing or electrical details.

## Viewer options

At the top of `bunker01_concept.scad`:

- `cutaway = true` omits one side wall and removes part of the roof for visibility.
- `exploded = true` separates roof/cover/service-path visuals; `explode_offset` is only a display offset.
- `show_excavation_envelope`, `show_drainage_zone`, and `show_roof_cover` toggle translucent context.

Changing a viewer option or parameter affects only visualization. It does not release any physical value.

## Optional local rendering

If OpenSCAD is already installed, from the repository root:

```sh
mkdir -p builds/bunker01-cad
openscad -o builds/bunker01-cad/bunker01_concept.png --render --imgsize=1280,960 --viewall --autocenter --projection=p projects/bunker01/cad/bunker01_concept.scad
```

Do not install software solely for this baseline. Generated images/meshes are not deliverables and no STL is recommended: this geometry is not for fabrication. The [official OpenSCAD manual](https://openscad.org/documentation.html) documents primitives, CSG operations and preview/render commands. Static delimiter validation does not prove that geometry renders or is physically meaningful.
