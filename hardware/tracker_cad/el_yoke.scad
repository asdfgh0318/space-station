// ============================================================
// Elevation Yoke (Fork) Assembly
// ============================================================
// U-shaped fork that:
//   - Bolts to the AZ turntable column on the bottom
//   - Has two arms with 8mm rod pivot through bearings
//   - Dish clamps attach to the pivot cross-bar
//   - Worm wheel on one arm, motor bracket on the other
//
// The yoke arms are the tallest parts -- each arm is split
// into upper and lower halves to fit the Ender 3 bed.
// ============================================================

include <parameters.scad>;
use <gears.scad>;

// --- Yoke arm parameters ---
arm_spacing_inner = 160;    // Inner distance between arms (dish fits between)
arm_thickness = el_yoke_thick;  // 25mm
arm_height = 180;           // Total arm height (split at 90mm for printing)
arm_width = el_yoke_arm_w;  // 30mm

// Pivot bearing position
pivot_z = arm_height * 0.65;   // Pivot point above yoke base
pivot_bearing_type = "6001";    // 6001ZZ for main pivot

// Base plate that bolts to AZ column
base_width = arm_spacing_inner + 2 * arm_thickness;
base_depth = 60;
base_height = 20;


// === YOKE BASE (connects arms, bolts to AZ column) ===

module el_yoke_base() {
    // The bottom cross-piece connecting both arms
    // This part bolts onto the AZ turntable column top

    difference() {
        union() {
            // Main base block
            translate([-base_width/2, -base_depth/2, 0])
                cube([base_width, base_depth, base_height]);

            // Arm stubs (lower portion of each arm grows from here)
            for (side = [-1, 1]) {
                translate([side * (arm_spacing_inner/2 + arm_thickness/2), 0, 0])
                    translate([-arm_thickness/2, -arm_width/2, 0])
                    cube([arm_thickness, arm_width, base_height + 15]);
            }
        }

        // AZ column mounting holes (M5, pattern matches turntable top)
        for (a = [0, 90, 180, 270]) {
            rotate([0, 0, a])
                translate([az_column_dia/2 - 8, 0, -eps])
                    cylinder(d = m5_through, h = base_height + 2 * eps, $fn = 16);
        }

        // Center clearance hole (wiring)
        translate([0, 0, -eps])
            cylinder(d = 18, h = base_height + 2 * eps, $fn = 32);

        // Bolt holes for arm attachment (arms bolt onto these stubs)
        for (side = [-1, 1]) {
            x = side * (arm_spacing_inner/2 + arm_thickness/2);
            for (dy = [-arm_width/4, arm_width/4]) {
                translate([x, dy, base_height + 5]) {
                    // Vertical M4 holes with heat-set inserts
                    cylinder(d = m4_insert_hole, h = m4_insert_depth + eps, $fn = 16);
                }
            }
        }

        // Weight reduction pockets
        for (side = [-1, 1]) {
            translate([side * 40, 0, wall_thick])
                cylinder(d = 30, h = base_height, $fn = 6);
        }
    }
}


// === YOKE ARM (lower half) ===

module el_yoke_arm_lower(mirror_side = false) {
    // Lower half of one yoke arm
    // Bolts to base stubs (bottom) and upper arm half (top)

    split_z = arm_height / 2;  // Split point

    difference() {
        // Arm body
        translate([-arm_thickness/2, -arm_width/2, 0])
            cube([arm_thickness, arm_width, split_z]);

        // Bottom: M4 bolt holes to base stubs
        for (dy = [-arm_width/4, arm_width/4]) {
            translate([0, dy, -eps])
                cylinder(d = m4_through, h = 15, $fn = 16);
        }

        // Top: M4 heat-set inserts for upper arm connection
        for (dy = [-arm_width/4, arm_width/4]) {
            translate([0, dy, split_z - m4_insert_depth])
                cylinder(d = m4_insert_hole, h = m4_insert_depth + eps, $fn = 16);
        }

        // Weight reduction slot
        translate([-arm_thickness/2 + wall_thick, -arm_width/4, 20])
            cube([arm_thickness - 2 * wall_thick, arm_width/2, split_z - 40]);

        // Worm gear motor bracket mounting (only on one side)
        if (!mirror_side) {
            // NEMA 17 motor mount holes on the outside face
            translate([arm_thickness/2 - eps, 0, split_z - 30])
                rotate([0, 90, 0]) {
                    for (dx = [-nema17_hole_sp/2, nema17_hole_sp/2],
                         dy = [-nema17_hole_sp/2, nema17_hole_sp/2]) {
                        translate([dx, dy, 0])
                            cylinder(d = m3_insert_hole, h = m3_insert_depth, $fn = 16);
                    }
                    // Shaft clearance
                    cylinder(d = nema17_boss_dia + 2, h = wall_thick + 2 * eps, $fn = 32);
                }
        }
    }
}


// === YOKE ARM (upper half) ===

module el_yoke_arm_upper(mirror_side = false) {
    // Upper half of one yoke arm
    // Contains the pivot bearing pocket for the 8mm rod

    split_z = arm_height / 2;
    upper_h = arm_height - split_z;
    pivot_local_z = pivot_z - split_z;  // Pivot position relative to this part

    difference() {
        // Arm body
        translate([-arm_thickness/2, -arm_width/2, 0])
            cube([arm_thickness, arm_width, upper_h]);

        // Bottom: M4 bolt holes to lower arm
        for (dy = [-arm_width/4, arm_width/4]) {
            translate([0, dy, -eps])
                cylinder(d = m4_through, h = 10, $fn = 16);
        }

        // Pivot bearing pocket (6001ZZ: 12mm ID, 28mm OD, 8mm wide)
        translate([0, 0, pivot_local_z])
            rotate([90, 0, 0])
            translate([0, 0, -arm_width/2 - eps])
                cylinder(d = b6001_od + tol * 2, h = b6001_h + tol, $fn = 48);

        // Bearing retention lip clearance (from other side)
        translate([0, 0, pivot_local_z])
            rotate([90, 0, 0])
            translate([0, 0, arm_width/2 - b6001_h - tol])
                cylinder(d = b6001_od + tol * 2, h = b6001_h + tol + eps, $fn = 48);

        // 8mm rod through-hole (between bearings)
        translate([0, 0, pivot_local_z])
            rotate([90, 0, 0])
            translate([0, 0, -arm_width - eps])
                cylinder(d = rod_dia + loose_tol * 2, h = arm_width * 3, $fn = 32);

        // AS5600 encoder mount pocket (on worm wheel side)
        if (!mirror_side) {
            translate([0, arm_width/2 - 3, pivot_local_z])
                rotate([90, 0, 0]) {
                    // Board mount holes
                    translate([-as5600_board_w/2, -eps, 0])
                        cube([as5600_board_w, as5600_board_l, as5600_board_h + 1]);
                }
        }

        // Weight reduction
        translate([-arm_thickness/2 + wall_thick, -arm_width/4, upper_h * 0.5])
            cube([arm_thickness - 2 * wall_thick, arm_width/2, upper_h * 0.35]);
    }
}


// === EL WORM WHEEL ===

module el_worm_wheel_printable() {
    // 60-tooth worm wheel for elevation axis
    // Mounts on the 8mm pivot rod (one side of the dish)

    worm_wheel(
        teeth = el_worm_teeth,      // 60
        mod = gear_module,          // 1
        face_width = 10,
        bore = rod_dia,             // 8mm pivot rod
        worm_dia = el_worm_dia,     // 12mm
        hub_dia = 20,
        hub_h = 8,
        backlash = 0.2,
        set_screw = true,           // M3 grub screw to lock on rod
        keyway = false
    );
}


// === EL WORM SCREW ===

module el_worm_printable() {
    worm_screw(
        length = el_worm_length,    // 25mm
        pitch_dia = el_worm_dia,    // 12mm
        mod = gear_module,          // 1
        starts = el_worm_starts,    // 1 (self-locking)
        bore = nema17_shaft_d,      // 5mm NEMA 17
        backlash = 0.15,
        keyway = true
    );
}


// === EL MOTOR BRACKET ===

module el_motor_bracket() {
    // NEMA 17 mount that attaches to the outside of one yoke arm
    // Positions motor so worm meshes with EL worm wheel

    bracket_thick = wall_thick_heavy;
    plate_w = nema17_face + 8;
    plate_h = nema17_face + 8;

    // Center distance between worm and wheel
    center_dist = (el_wheel_pitch_d + el_worm_dia) / 2;

    difference() {
        union() {
            // Motor mounting plate
            translate([-plate_w/2, 0, -plate_h/2])
                cube([plate_w, bracket_thick, plate_h]);

            // Standoff feet (create the correct center distance)
            for (dx = [-plate_w/4, plate_w/4]) {
                translate([dx, bracket_thick, -plate_h/4])
                    cube([10, 15, plate_h/2]);
            }
        }

        // NEMA 17 holes
        translate([0, -eps, 0])
            rotate([-90, 0, 0]) {
                cylinder(d = nema17_boss_dia + 2, h = bracket_thick + 2 * eps, $fn = 32);
                for (dx = [-1, 1], dy = [-1, 1]) {
                    translate([dx * nema17_hole_sp/2, dy * nema17_hole_sp/2, 0])
                        cylinder(d = m3_through, h = bracket_thick + 2 * eps, $fn = 16);
                }
            }

        // Mounting bolt holes (to yoke arm)
        for (dx = [-plate_w/4, plate_w/4]) {
            translate([dx, bracket_thick + 5, 0])
                rotate([-90, 0, 0])
                cylinder(d = m3_through, h = 20, $fn = 16);
        }
    }
}


// === PIVOT CROSS-BAR ===
// The 8mm steel rod spans between the two yoke arms.
// This printed part clamps around the rod and provides
// mounting points for the dish clamps.

module pivot_clamp() {
    // Clamps onto 8mm rod, provides dish mounting surface
    clamp_l = 40;
    clamp_w = 30;
    clamp_h = 25;

    difference() {
        union() {
            // Main block
            translate([-clamp_w/2, -clamp_l/2, 0])
                cube([clamp_w, clamp_l, clamp_h]);
        }

        // Rod channel (8mm)
        translate([0, -clamp_l/2 - eps, clamp_h/2])
            rotate([-90, 0, 0])
            cylinder(d = rod_dia + tol, h = clamp_l + 2 * eps, $fn = 32);

        // Clamping slit
        translate([-0.5, -clamp_l/2 - eps, clamp_h/2])
            cube([1, clamp_l + 2 * eps, clamp_h/2 + eps]);

        // Clamp bolt (M4, vertical through slit)
        translate([0, 0, clamp_h - eps])
            cylinder(d = m4_through, h = 5, $fn = 16);

        // Dish clamp bolt holes (M5, from top)
        for (dy = [-clamp_l/4, clamp_l/4]) {
            translate([0, dy, -eps])
                cylinder(d = m5_insert_hole, h = m5_insert_depth, $fn = 16);
        }
    }
}


// === PREVIEW ===

// Uncomment to preview:

// Assembled yoke (exploded view)
/*
color("SteelBlue") el_yoke_base();

// Left arm
color("CadetBlue") translate([-(arm_spacing_inner/2 + arm_thickness/2), 0, base_height])
    el_yoke_arm_lower(mirror_side = true);
color("LightSteelBlue") translate([-(arm_spacing_inner/2 + arm_thickness/2), 0, base_height + arm_height/2 + 2])
    el_yoke_arm_upper(mirror_side = true);

// Right arm (worm wheel side)
color("CadetBlue") translate([(arm_spacing_inner/2 + arm_thickness/2), 0, base_height])
    el_yoke_arm_lower(mirror_side = false);
color("LightSteelBlue") translate([(arm_spacing_inner/2 + arm_thickness/2), 0, base_height + arm_height/2 + 2])
    el_yoke_arm_upper(mirror_side = false);

// Worm wheel (on right arm pivot)
color("Gold") translate([(arm_spacing_inner/2 + arm_thickness/2 + 15), 0, base_height + pivot_z])
    rotate([90, 0, 0]) el_worm_wheel_printable();

// 8mm rod (steel, not printed)
color("Silver") translate([0, 0, base_height + pivot_z])
    rotate([0, 90, 0])
    cylinder(d = rod_dia, h = arm_spacing_inner + arm_thickness * 2 + 20, center = true, $fn = 24);
*/

// Individual parts for STL export:
// el_yoke_base();
// el_yoke_arm_lower(mirror_side = false);
// el_yoke_arm_lower(mirror_side = true);
// el_yoke_arm_upper(mirror_side = false);
// el_yoke_arm_upper(mirror_side = true);
// el_worm_wheel_printable();
// el_worm_printable();
// el_motor_bracket();
// pivot_clamp();
