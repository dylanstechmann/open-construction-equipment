// SPDX-License-Identifier: CERN-OHL-S-2.0
// BUNKER-01 CIVILIAN NON-HABITABLE UTILITY ENCLOSURE — CONCEPT ONLY.
// NOT FOR CONSTRUCTION, EXCAVATION, ENTRY, OCCUPANCY, OR PROTECTIVE USE.
// No reinforcement, structural capacity, egress, ventilation, waterproofing,
// drainage, safe slope, support system, or code compliance is designed here.

include <parameters.scad>

$fn = visual_detail;

// Viewer options only; none changes the engineering status.
cutaway = true;
exploded = false;
show_excavation_envelope = true;
show_drainage_zone = true;
show_roof_cover = true;
explode_offset = 600; // Display separation only, not a physical clearance.

outer_length = internal_length + 2 * wall_thickness;
outer_width = internal_width + 2 * wall_thickness;
roof_bottom = floor_thickness + internal_height;
roof_top = roof_bottom + roof_thickness;
excavation_length = outer_length + 2 * working_space;
excavation_width = outer_width + 2 * working_space;
excavation_depth = drainage_layer + floor_thickness + internal_height + roof_thickness + roof_cover;
display_overlap = 1; // CSG display aid only; not a tolerance.

module floor_panel() {
    color("LightGray")
        translate([-outer_length / 2, -outer_width / 2, 0])
            cube([outer_length, outer_width, floor_thickness]);
}

module side_wall(side = 1) {
    color("Silver")
        translate([-outer_length / 2,
                   side < 0 ? -outer_width / 2 : internal_width / 2,
                   floor_thickness])
            cube([outer_length, wall_thickness, internal_height]);
}

module rear_wall() {
    color("Silver")
        translate([internal_length / 2, -internal_width / 2, floor_thickness])
            cube([wall_thickness, internal_width, internal_height]);
}

module front_wall_with_opening() {
    // The opening is a display void only. Header, door and egress are undesigned.
    color("Silver")
        difference() {
            translate([-outer_length / 2, -internal_width / 2, floor_thickness])
                cube([wall_thickness, internal_width, internal_height]);
            translate([-outer_length / 2 - display_overlap,
                       -entrance_opening_width / 2,
                       floor_thickness])
                cube([wall_thickness + 2 * display_overlap,
                      entrance_opening_width,
                      entrance_opening_height]);
        }
}

module roof_panel() {
    translate([0, 0, exploded ? explode_offset : 0])
        color("DarkGray")
            difference() {
                translate([-outer_length / 2, -outer_width / 2, roof_bottom])
                    cube([outer_length, outer_width, roof_thickness]);
                if (cutaway)
                    translate([0, -outer_width / 2 - display_overlap,
                               roof_bottom - display_overlap])
                        cube([outer_length / 2 + display_overlap,
                              outer_width / 2 + display_overlap,
                              roof_thickness + 2 * display_overlap]);
            }
}

module drainage_zone() {
    if (show_drainage_zone) {
        color([0.20, 0.55, 0.85, 0.45]) {
            translate([-outer_length / 2 - drainage_layer,
                       -outer_width / 2 - drainage_layer,
                       -drainage_layer])
                cube([outer_length + 2 * drainage_layer,
                      outer_width + 2 * drainage_layer,
                      drainage_layer]);
            for (side = [-1, 1])
                translate([-outer_length / 2 - drainage_layer,
                           side < 0 ? -outer_width / 2 - drainage_layer : outer_width / 2,
                           0])
                    cube([outer_length + 2 * drainage_layer,
                          drainage_layer,
                          floor_thickness + internal_height]);
        }
    }
}

module vent_pathways() {
    // Cyan solids mark service routes, not selected ducts, airflow or safe air.
    color([0.0, 0.85, 0.85, 0.70])
        for (x = [-internal_length * 0.30, internal_length * 0.30])
            translate([x, internal_width * 0.25, roof_bottom - internal_height * 0.15])
                cylinder(r = vent_path_radius,
                         h = internal_height * 0.15 + roof_thickness + roof_cover +
                             (exploded ? 2 * explode_offset : 0));
}

module cover_zone() {
    if (show_roof_cover)
        translate([0, 0, exploded ? 2 * explode_offset : 0])
            color([0.62, 0.48, 0.28, 0.35])
                translate([-outer_length / 2, -outer_width / 2, roof_top])
                    cube([outer_length, outer_width, roof_cover]);
}

module excavation_envelope() {
    if (show_excavation_envelope)
        color([0.65, 0.65, 0.65, 0.12])
            translate([-excavation_length / 2, -excavation_width / 2, -drainage_layer])
                cube([excavation_length, excavation_width, excavation_depth]);
}

module concept_label() {
    color("FireBrick")
        translate([-outer_length / 2, -outer_width / 2 - working_space * 0.55,
                   roof_top + roof_cover + (exploded ? 2 * explode_offset : 0)])
            linear_extrude(height = 1)
                text("BUNKER-01 CONCEPT — NOT FOR CONSTRUCTION", size = 170);
}

module bunker01_concept() {
    excavation_envelope();
    drainage_zone();
    floor_panel();
    rear_wall();
    front_wall_with_opening();
    side_wall(-1);
    if (!cutaway)
        side_wall(1);
    roof_panel();
    vent_pathways();
    cover_zone();
    concept_label();
}

bunker01_concept();
