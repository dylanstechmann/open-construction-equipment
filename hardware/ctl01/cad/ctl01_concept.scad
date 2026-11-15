// SPDX-License-Identifier: CERN-OHL-S-2.0
// OCE-CTL-01 CONCEPT ENVELOPE ONLY.
// NOT fabrication CAD, NOT structurally validated, NOT a ROPS/FOPS design,
// NOT a compatible quick-attach drawing, and NOT a performance model.

include <parameters.scad>

$fn = visual_detail;

module beam_between(p1, p2, width) {
    dx = p2[0] - p1[0];
    dy = p2[1] - p1[1];
    dz = p2[2] - p1[2];
    horizontal = sqrt(dx * dx + dy * dy);
    length = sqrt(horizontal * horizontal + dz * dz);
    translate(p1)
        rotate([0, -atan2(dz, horizontal), atan2(dy, dx)])
            cube([length, width, width], center = true);
}

module track_module(side = 1) {
    y = side * (machine_width - track_width) / 2;
    color("DimGray") {
        translate([-track_length / 2, y - track_width / 2, 0])
            cube([track_length, track_width, track_height]);
        // Visible wheel/end forms embedded in the simplified track envelope.
        for (x = [-track_length * 0.34, 0, track_length * 0.34]) {
            translate([x, y, track_height * 0.48])
                rotate([90, 0, 0])
                    cylinder(d = wheel_diameter, h = wheel_width, center = true);
        }
    }
    color("DarkSlateGray")
        translate([-track_length * 0.30, y, track_height * 0.70])
            rotate([90, 0, 0])
                cylinder(d = wheel_diameter * 0.36, h = wheel_width * 1.05, center = true);
}

module chassis_frame() {
    color("Silver")
        translate([-frame_length / 2, -frame_width / 2, frame_bottom])
            cube([frame_length, frame_width, frame_height]);
    color("RoyalBlue")
        translate([-frame_length * 0.43, -battery_width / 2, frame_bottom + frame_height])
            cube([battery_length, battery_width, battery_height]);
    // No battery enclosure construction, protection, or mounting is designed here.
}

module operator_zone() {
    base_z = operator_zone_base;
    top_z = base_z + operator_zone_height;
    x0 = -operator_zone_length * 0.25;
    x1 = x0 + operator_zone_length;
    y0 = -operator_zone_width / 2;
    y1 = operator_zone_width / 2;
    // UNRATED operator-zone visual posts. Not released ROPS/FOPS geometry.
    color("Gold") {
        for (x = [x0, x1], y = [y0, y1]) {
            translate([x - post_width / 2, y - post_width / 2, base_z])
                cube([post_width, post_width, operator_zone_height]);
        }
        translate([x0 - post_width / 2, y0 - post_width / 2, top_z])
            cube([operator_zone_length + post_width, operator_zone_width + post_width, roof_height]);
    }
    color("Black") {
        seat_x = (x0 + x1) / 2;
        translate([seat_x - machine_width * 0.07, -machine_width * 0.08, base_z + machine_width * 0.07])
            cube([machine_width * 0.14, machine_width * 0.16, machine_width * 0.06]);
        translate([seat_x - machine_width * 0.08, -machine_width * 0.08, base_z + machine_width * 0.13])
            cube([machine_width * 0.035, machine_width * 0.16, machine_width * 0.22]);
        translate([seat_x + machine_width * 0.06, -machine_width * 0.19, base_z + machine_width * 0.12])
            cube([machine_width * 0.025, machine_width * 0.38, machine_width * 0.07]);
    }
}

module lift_arm(side = 1) {
    offset_y = side * frame_width * 0.49;
    rear = [arm_rear[0], offset_y, arm_rear[2]];
    elbow = [(arm_rear[0] + arm_front[0]) * 0.48, offset_y, arm_front[2] + machine_width * 0.12];
    front = [arm_front[0], offset_y, arm_front[2]];
    color("DarkOrange") {
        beam_between(rear, elbow, arm_width);
        beam_between(elbow, front, arm_width);
        translate(rear)
            rotate([90, 0, 0])
                cylinder(d = arm_width * 1.7, h = arm_width * 1.3, center = true);
        translate(front)
            rotate([90, 0, 0])
                cylinder(d = arm_width * 1.4, h = arm_width * 1.3, center = true);
    }
    // Silver actuator is a visual mechanism hint, not a sized hydraulic cylinder.
    color("LightGray")
        beam_between([rear[0], offset_y, frame_bottom + frame_height * 0.45], elbow, arm_width * 0.40);
}

module quick_attach() {
    // Universal-STYLE visual marker only; mating geometry and retention are TBD.
    color("FireBrick")
        translate([arm_front[0], -quick_attach_width / 2, arm_front[2] - quick_attach_height * 0.50])
            rotate([0, -8, 0])
                cube([quick_attach_thickness, quick_attach_width, quick_attach_height]);
}

module bucket() {
    x = arm_front[0] + quick_attach_thickness * 0.25;
    y = -bucket_width / 2;
    z = arm_front[2] - quick_attach_height * 0.50 - bucket_height * 0.35;
    color("Sienna") {
        // Open-top scoop assembled from display solids; no weldment or wear geometry.
        translate([x, y, z])
            cube([bucket_depth, bucket_width, bucket_wall]);
        translate([x, y, z])
            rotate([0, -10, 0])
                cube([bucket_wall, bucket_width, bucket_height]);
        translate([x + bucket_depth * 0.88, y, z])
            cube([bucket_depth * 0.12, bucket_width, bucket_wall * 0.65]);
        for (side_y = [y, y + bucket_width - bucket_wall]) {
            translate([x, side_y, z])
                cube([bucket_depth, bucket_wall, bucket_height * 0.72]);
        }
    }
}

module oce_ctl01_concept() {
    track_module(-1);
    track_module(1);
    chassis_frame();
    operator_zone();
    lift_arm(-1);
    lift_arm(1);
    quick_attach();
    bucket();
}

oce_ctl01_concept();
