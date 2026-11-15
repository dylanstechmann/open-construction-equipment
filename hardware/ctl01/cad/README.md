<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# OCE-CTL-01 visualization-only CAD

This OpenSCAD source depicts a conceptual envelope: frame, left/right tracks, an **unrated** operator-zone frame, lift arms, quick attach and bucket. It is not manufacturing CAD, a released ROPS/FOPS design, a human-factors model, or a structural/stability model.

Only the overall-width input reflects the initial AI-authored 1.5 m concept target; owner review is pending. Other geometry is a proportional **visual display assumption** to make an identifiable machine; it is not a layout selection, cleared access path, load path, fit, tolerance, attachment interface, or manufacturing dimension. Parameters must not be copied into drawings or service limits. Editing this model can never turn a target into a released specification.

## Render with OpenSCAD

If OpenSCAD is installed, from the repository root:

```sh
mkdir -p build
openscad -o build/ctl01_concept.png --render --imgsize=1280,960   --viewall --autocenter --projection=p hardware/ctl01/cad/ctl01_concept.scad
openscad -o build/ctl01_concept.stl hardware/ctl01/cad/ctl01_concept.scad
```

The PNG is for visual review only. The STL illustrates exterior solids and is **not for fabrication**. `build/`, STL, PNG, and other generated meshes are ignored. GUI users can open `ctl01_concept.scad`, press F5 to preview and F6 to render. OpenSCAD’s [official manual](https://openscad.org/documentation.html) documents these operations.

## Parameterization and change control

`parameters.scad` uses millimetres and defines proportions from `machine_width` to avoid implying released engineering dimensions. Parameter changes affect visualization only and require no rendering output to be committed. Real mechanical design needs dated controlled drawings, mass/stability/load analyses, qualified review and requirements traceability.
