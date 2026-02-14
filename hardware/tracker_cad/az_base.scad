// ============================================================
// Azimuth Base and Turntable Assembly
// ============================================================
// Two main parts:
//   1. Base plate (stationary) - sits on tripod or pipe mount
//   2. Turntable (rotating) - carries the elevation yoke
//
// Each is split into 2 halves for Ender 3 bed (max 220mm).
// Halves are bolted together with M4 bolts.
//
// Bearing stack: 51107 thrust bearing + 608ZZ radial bearings
// for smooth rotation under dish load.
//
// Worm wheel is attached to turntable, driven by worm on motor.
// ============================================================

include <parameters.scad>;
use <gears.scad>;

// === AZIMUTH BASE PLATE (STATIONARY) ===

module az_base_half() {
    // One half of the base plate (print 2, bolt together)

    base_r = az_base_dia / 2;
    thrust_pocket_r = bt51107_od / 2 + tol;
    thrust_pocket_depth = bt51107_h / 2 + 1;  // Bearing sits halfway in each plate
    radial_pocket_r = b608_od / 2 + tol;

    difference() {
        union() {
            // Half-circle base plate
            linear_extrude(height = az_base_h) {
                difference() {
                    // Half circle (with flat edge for bolting)
                    intersection() {
                        circle(r = base_r);
                        translate([-base_r, 0])
                            square([base_r * 2, base_r + 1]);
                    }
                }
            }

            // Bolt flanges at the split line
            for (x = [-base_r * 0.6, base_r * 0.6]) {
                translate([x, -5, 0])
                    cylinder(d = 14, h = az_base_h, $fn = 24);
            }
        }

        // Thrust bearing pocket (center, top side)
        translate([0, 0, az_base_h - thrust_pocket_depth])
            cylinder(r = thrust_pocket_r, h = thrust_pocket_depth + eps, $fn = 64);

        // Radial bearing pockets (2x 608ZZ, symmetrically placed)
        for (a = [45, 135]) {
            rotate([0, 0, a])
                translate([bt51107_od/2 + 5, 0, az_base_h - b608_h - 1])
                    cylinder(r = radial_pocket_r, h = b608_h + 1 + eps, $fn = 48);
        }

        // Center hole for wiring
        translate([0, 0, -eps])
            cylinder(d = 20, h = az_base_h + 2 * eps, $fn = 32);

        // Bolt holes along split line (M4 through-holes)
        for (x = [-base_r * 0.6, base_r * 0.6]) {
            translate([x, -5, -eps])
                cylinder(d = m4_through, h = az_base_h + 2 * eps, $fn = 16);

            // Counterbore from bottom
            translate([x, -5, -eps])
                cylinder(d = m4_cbore_dia, h = m4_cbore_depth + eps, $fn = 16);
        }

        // Tripod mounting holes (1/4-20 UNC = 6.35mm, or M6)
        // 3 holes on a 100mm circle for camera tripod plate
        for (a = [30, 90, 150]) {
            rotate([0, 0, a])
                translate([50, 0, -eps])
                    cylinder(d = 6.5, h = az_base_h + 2 * eps, $fn = 24);
        }

        // Motor mounting cutout (one side, for worm approach)
        translate([base_r - 25, -nema17_face/2 - 5, -eps])
            cube([30, nema17_face + 10, az_base_h + 2 * eps]);
    }
}


// === AZIMUTH TURNTABLE (ROTATING) ===

module az_turntable_half() {
    // One half of the turntable (print 2, bolt together)

    tt_r = az_turntable_dia / 2;
    thrust_boss_r = bt51107_id / 2 - 1;
    thrust_boss_h = bt51107_h / 2 + 1;

    difference() {
        union() {
            // Half-circle turntable plate
            linear_extrude(height = az_turntable_h) {
                intersection() {
                    circle(r = tt_r);
                    translate([-tt_r, 0])
                        square([tt_r * 2, tt_r + 1]);
                }
            }

            // Center boss (sits inside thrust bearing)
            translate([0, 0, -thrust_boss_h])
                cylinder(r = thrust_boss_r, h = thrust_boss_h, $fn = 48);

            // Column base (connects to EL yoke)
            cylinder(d = az_column_dia, h = az_turntable_h + 20, $fn = 48);

            // Bolt flanges at split line
            for (x = [-tt_r * 0.6, tt_r * 0.6]) {
                translate([x, -5, 0])
                    cylinder(d = 14, h = az_turntable_h, $fn = 24);
            }
        }

        // Worm wheel mounting ring (the gear attaches here)
        // Ring of M3 holes for bolting worm wheel
        for (a = [0:45:180]) {
            rotate([0, 0, a])
                translate([az_wheel_pitch_d/2 - 10, 0, -eps]) {
                    cylinder(d = m3_through, h = az_turntable_h + 2 * eps, $fn = 16);
                }
        }

        // Center hole for wiring
        translate([0, 0, -thrust_boss_h - eps])
            cylinder(d = 16, h = az_turntable_h + thrust_boss_h + 30, $fn = 32);

        // Bolt holes along split line
        for (x = [-tt_r * 0.6, tt_r * 0.6]) {
            translate([x, -5, -eps])
                cylinder(d = m4_through, h = az_turntable_h + 2 * eps, $fn = 16);
        }

        // Column top mounting holes (for EL yoke attachment, M5)
        for (a = [0, 90, 180, 270]) {
            rotate([0, 0, a])
                translate([az_column_dia/2 - 8, 0, az_turntable_h + 10]) {
                    // Hole from side for bolt
                    rotate([0, 0, 0])
                        translate([0, 0, 0])
                        cylinder(d = m5_insert_hole, h = m5_insert_depth, $fn = 16);
                }
        }
    }
}


// === AZ WORM WHEEL (separate part, bolts to turntable) ===

module az_worm_wheel_printable() {
    // 80-tooth worm wheel for azimuth axis
    // Bolts to turntable via M3 holes on a ring

    worm_wheel(
        teeth = az_worm_teeth,      // 80
        mod = gear_module,          // 1
        face_width = 12,
        bore = az_column_dia + loose_tol * 2,  // Fits around column
        worm_dia = az_worm_dia,
        hub_dia = az_column_dia + 12,
        hub_h = 8,
        backlash = 0.2,
        set_screw = false,
        keyway = false
    );

    // Note: This gear has a large bore to fit around the turntable column.
    // It's bolted to the turntable rather than press-fit on a shaft.
}


// === AZ WORM SCREW ===

module az_worm_printable() {
    // Single-start worm for azimuth motor
    worm_screw(
        length = az_worm_length,    // 30mm
        pitch_dia = az_worm_dia,    // 12mm
        mod = gear_module,          // 1
        starts = az_worm_starts,    // 1 (self-locking)
        bore = nema17_shaft_d,      // 5mm (NEMA 17 shaft)
        backlash = 0.15,
        keyway = true
    );
}


// === AZ MOTOR BRACKET ===

module az_motor_bracket() {
    // NEMA 17 mount that attaches to the base plate
    // Positions the motor so the worm meshes with the wheel on the turntable

    bracket_w = nema17_face + 10;
    bracket_h = nema17_face + 10;
    bracket_thick = wall_thick_heavy;

    // Worm-to-wheel center distance
    center_dist = (az_wheel_pitch_d + az_worm_dia) / 2;

    difference() {
        union() {
            // Vertical plate (motor mounts here)
            translate([-bracket_w/2, 0, 0])
                cube([bracket_w, bracket_thick, bracket_h]);

            // Base feet (bolt to base plate)
            translate([-bracket_w/2, 0, 0])
                cube([bracket_w, 30, wall_thick]);

            // Gussets for rigidity
            for (x = [-bracket_w/2, bracket_w/2 - wall_thick]) {
                translate([x, bracket_thick, 0])
                    linear_extrude(height = wall_thick)
                    polygon([[0,0], [0, 20], [20, 0]]);
            }
        }

        // NEMA 17 mounting holes
        motor_center_z = bracket_h / 2;
        translate([0, -eps, motor_center_z])
            rotate([-90, 0, 0]) {
                // Shaft hole
                cylinder(d = nema17_boss_dia + 2, h = bracket_thick + 2 * eps, $fn = 32);

                // Mounting bolts (31mm spacing, M3)
                for (dx = [-1, 1], dy = [-1, 1]) {
                    translate([dx * nema17_hole_sp/2, dy * nema17_hole_sp/2, 0])
                        cylinder(d = m3_through, h = bracket_thick + 2 * eps, $fn = 16);
                }
            }

        // Base bolt holes (M4 to base plate)
        for (x = [-bracket_w/4, bracket_w/4]) {
            translate([x, 15, -eps])
                cylinder(d = m4_through, h = wall_thick + 2 * eps, $fn = 16);
        }
    }
}


// === PREVIEW ===

// Uncomment one to preview:

// Full AZ assembly (exploded)
// color("DarkSlateGray") az_base_half();
// color("DarkSlateGray") mirror([0, 1, 0]) az_base_half();
// color("SteelBlue") translate([0, 0, az_base_h + 2]) az_turntable_half();
// color("SteelBlue") translate([0, 0, az_base_h + 2]) mirror([0, 1, 0]) az_turntable_half();
// color("Gold") translate([0, 0, az_base_h]) az_worm_wheel_printable();
// color("Orange") translate([80, 0, az_base_h + 6]) rotate([0, 90, 0]) az_worm_printable();

// Individual parts for STL export:
// az_base_half();
// az_turntable_half();
// az_worm_wheel_printable();
// az_worm_printable();
// az_motor_bracket();
