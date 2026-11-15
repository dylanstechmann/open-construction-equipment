// SPDX-License-Identifier: CERN-OHL-S-2.0
// BUNKER-01 synthetic geometric concept parameters; NOT FOR CONSTRUCTION.
// Units: millimetres. Every value is AI-authored and unreviewed.
// These are visualization/calculator-example assumptions, NOT structural
// selections, code clearances, safe excavation parameters, or released sizes.

internal_length = 4000;   // Synthetic internal length: 4.0 m.
internal_width = 3000;    // Synthetic internal width: 3.0 m.
internal_height = 2400;   // Synthetic internal height: 2.4 m.
wall_thickness = 250;     // Geometric display only: 0.25 m; not structural design.
floor_thickness = 250;    // Geometric display only: 0.25 m; not structural design.
roof_thickness = 300;     // Geometric display only: 0.30 m; not structural design.
working_space = 750;      // Display envelope only: 0.75 m; not safe excavation clearance.
drainage_layer = 200;     // Display zone only: 0.20 m; not a drainage design.
roof_cover = 500;         // Display zone only: 0.50 m; not approved cover depth.

// Display proportions introduce no released opening or ventilation dimensions.
entrance_opening_width = internal_width * 0.30;
entrance_opening_height = internal_height * 0.80;
vent_path_radius = internal_height * 0.04;
visual_detail = 32;
