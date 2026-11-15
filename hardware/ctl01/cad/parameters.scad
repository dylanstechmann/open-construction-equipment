// SPDX-License-Identifier: CERN-OHL-S-2.0
// OCE-CTL-01 concept visualization parameters; NOT fabrication dimensions.
// Units: mm. All proportions except machine_width target are display assumptions.

machine_width = 1500; // Initial AI-authored target, owner review pending: approximately 1.5 m overall width.

// Display-only proportions. These are NOT engineered sizes or clearances.
track_length = machine_width * 1.28;
track_width = machine_width * 0.18;
track_height = machine_width * 0.43;
wheel_diameter = track_height * 0.66;
wheel_width = track_width * 0.82;
frame_length = machine_width * 1.15;
frame_width = machine_width * 0.60;
frame_height = machine_width * 0.22;
frame_bottom = track_height * 0.75;
operator_zone_length = machine_width * 0.52;
operator_zone_width = machine_width * 0.51;
operator_zone_height = machine_width * 0.80;
operator_zone_base = frame_bottom + frame_height;
post_width = machine_width * 0.025; // Visual marker; absolutely not a ROPS member size.
roof_height = machine_width * 0.035; // Visual envelope only; not protective structure.
arm_width = machine_width * 0.065;
arm_rear = [-frame_length * 0.38, 0, frame_bottom + frame_height * 0.85];
arm_front = [frame_length * 0.54, 0, frame_bottom + frame_height * 1.55];
quick_attach_width = machine_width * 0.69;
quick_attach_height = machine_width * 0.25;
quick_attach_thickness = machine_width * 0.025;
bucket_width = machine_width * 0.83;
bucket_depth = machine_width * 0.48;
bucket_height = machine_width * 0.34;
bucket_wall = machine_width * 0.018; // Plate display thickness only; not released.
battery_length = machine_width * 0.54;
battery_width = machine_width * 0.52;
battery_height = machine_width * 0.32;
visual_detail = 24; // Mesh smoothness only; no engineering significance.
