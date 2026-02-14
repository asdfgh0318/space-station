// ============================================================
// Involute Gear Library for 3D Printed Worm Drives
// ============================================================
// Generates:
//   - Involute spur gears (worm wheels with straight-cut teeth)
//   - Single-start worm screws
//   - Herringbone variants for reduced axial thrust
//
// Optimized for FDM 3D printing:
//   - Tooth profile slightly modified for printability
//   - Backlash parameter for clearance
//   - Designed for module 1 gears at low speed / low load
//
// Reference: Machinery's Handbook, involute gear geometry
// ============================================================

use <parameters.scad>;

// ---- Involute tooth profile functions ----

// Generate a single involute curve point
function involute_point(base_r, t) = [
    base_r * (cos(t) + t * PI / 180 * sin(t)),
    base_r * (sin(t) - t * PI / 180 * cos(t))
];

// Generate involute curve as a series of points
function involute_curve(base_r, start_t, end_t, steps=20) = [
    for (i = [0:steps])
        involute_point(base_r, start_t + (end_t - start_t) * i / steps)
];


// ---- Spur Gear (used as worm wheel) ----

module spur_gear(
    teeth,              // Number of teeth
    mod = 1,            // Module
    thickness = 10,     // Gear face width
    bore = 8,           // Center bore diameter
    pressure_angle = 20,
    backlash = 0.1,     // Extra clearance per tooth side
    hub_dia = 0,        // Hub diameter (0 = no hub)
    hub_h = 0,          // Hub height extending below gear
    keyway = false,     // D-shaft flat
    key_depth = 0.5     // D-shaft flat depth
) {
    pitch_r = teeth * mod / 2;
    base_r = pitch_r * cos(pressure_angle);
    outer_r = pitch_r + mod;
    root_r = pitch_r - 1.25 * mod;

    tooth_angle = 360 / teeth;
    // Approximate tooth thickness at pitch circle
    tooth_thick_angle = tooth_angle / 2 - backlash * 360 / (PI * pitch_r * 2);

    actual_hub_dia = hub_dia > 0 ? hub_dia : bore + wall_thick * 2;

    difference() {
        union() {
            // Gear body
            linear_extrude(height = thickness) {
                difference() {
                    // Generate gear profile
                    _gear_2d(teeth, mod, pressure_angle, backlash);

                    // Center bore
                    circle(d = bore + tol * 2);
                }
            }

            // Hub
            if (hub_h > 0) {
                translate([0, 0, -hub_h])
                    cylinder(d = actual_hub_dia, h = hub_h);
            }
        }

        // Bore through everything
        translate([0, 0, -hub_h - eps])
            cylinder(d = bore + tol * 2, h = thickness + hub_h + 2 * eps);

        // Keyway (D-shaft flat)
        if (keyway) {
            translate([bore/2 - key_depth, -bore, -hub_h - eps])
                cube([key_depth + 1, bore * 2, thickness + hub_h + 2 * eps]);
        }
    }
}

// 2D gear profile using simplified involute approximation
module _gear_2d(teeth, mod, pa, backlash) {
    pitch_r = teeth * mod / 2;
    outer_r = pitch_r + mod;
    root_r = pitch_r - 1.25 * mod;
    base_r = pitch_r * cos(pa);

    tooth_angle = 360 / teeth;

    // Simplified tooth profile using trapezoid approximation
    // More printable than pure involute, works well for low-speed FDM gears
    union() {
        circle(r = root_r);

        for (i = [0:teeth-1]) {
            rotate([0, 0, i * tooth_angle]) {
                _tooth_2d(pitch_r, outer_r, root_r, tooth_angle, backlash);
            }
        }
    }
}

module _tooth_2d(pitch_r, outer_r, root_r, tooth_angle, backlash) {
    // Tooth width at various radii
    tip_half_angle = tooth_angle * 0.15 - backlash * 180 / (PI * outer_r);
    pitch_half_angle = tooth_angle * 0.22 - backlash * 180 / (PI * pitch_r);
    root_half_angle = tooth_angle * 0.28;

    polygon([
        [root_r * cos(-root_half_angle), root_r * sin(-root_half_angle)],
        [pitch_r * cos(-pitch_half_angle), pitch_r * sin(-pitch_half_angle)],
        [outer_r * cos(-tip_half_angle), outer_r * sin(-tip_half_angle)],
        [outer_r * cos(tip_half_angle), outer_r * sin(tip_half_angle)],
        [pitch_r * cos(pitch_half_angle), pitch_r * sin(pitch_half_angle)],
        [root_r * cos(root_half_angle), root_r * sin(root_half_angle)],
    ]);
}


// ---- Worm Wheel (spur gear with throated profile) ----

module worm_wheel(
    teeth,
    mod = 1,
    face_width = 12,    // Tooth face width
    bore = 8,
    worm_dia = 12,      // Mating worm pitch diameter (for throat)
    hub_dia = 0,
    hub_h = 10,
    pressure_angle = 20,
    backlash = 0.15,
    set_screw = true,   // M3 set screw hole in hub
    keyway = true
) {
    pitch_r = teeth * mod / 2;
    worm_r = worm_dia / 2 + mod;  // Worm outer radius

    difference() {
        // Start with spur gear
        spur_gear(
            teeth = teeth,
            mod = mod,
            thickness = face_width,
            bore = bore,
            pressure_angle = pressure_angle,
            backlash = backlash,
            hub_dia = hub_dia,
            hub_h = hub_h,
            keyway = keyway
        );

        // Throat cut - concave surface matching worm curvature
        // This improves contact area between worm and wheel
        translate([pitch_r + worm_r, 0, face_width / 2])
            rotate([0, 0, 0])
            cylinder(r = worm_r, h = face_width + 2, center = true, $fn = 64);

        translate([-(pitch_r + worm_r), 0, face_width / 2])
            rotate([0, 0, 0])
            cylinder(r = worm_r, h = face_width + 2, center = true, $fn = 64);

        // Set screw hole in hub (radial M3)
        if (set_screw && hub_h > 0) {
            actual_hub = hub_dia > 0 ? hub_dia : bore + wall_thick * 2;
            translate([0, actual_hub/2 + 1, -hub_h/2])
                rotate([90, 0, 0])
                cylinder(d = m3_through, h = actual_hub, $fn = 24);
        }
    }
}


// ---- Worm Screw ----

module worm_screw(
    length = 30,        // Worm length
    pitch_dia = 12,     // Worm pitch diameter
    mod = 1,            // Module (must match wheel)
    starts = 1,         // Number of starts (1 for self-locking)
    bore = 5,           // Shaft bore (5mm for NEMA 17)
    pressure_angle = 20,
    backlash = 0.1,
    keyway = true,      // D-shaft flat for NEMA 17
    key_depth = 0.5
) {
    pitch = PI * mod * starts;  // Axial pitch
    outer_r = pitch_dia / 2 + mod;
    root_r = pitch_dia / 2 - 1.25 * mod;
    tooth_depth = outer_r - root_r;

    lead_angle = atan2(pitch, PI * pitch_dia);

    // Number of full threads
    n_turns = length / pitch;

    difference() {
        union() {
            // Worm body
            cylinder(d = pitch_dia - mod, h = length, $fn = 64);

            // Thread (helical extrusion using hull trick)
            _worm_thread(
                length = length,
                outer_r = outer_r,
                root_r = root_r,
                pitch = pitch,
                starts = starts,
                pa = pressure_angle,
                backlash = backlash
            );
        }

        // Bore
        translate([0, 0, -eps])
            cylinder(d = bore + tol * 2, h = length + 2 * eps, $fn = 32);

        // Keyway (D-shaft)
        if (keyway) {
            translate([bore/2 - key_depth, -bore, -eps])
                cube([key_depth + 1, bore * 2, length + 2 * eps]);
        }
    }
}

// Worm thread using stacked slices
module _worm_thread(length, outer_r, root_r, pitch, starts, pa, backlash) {
    steps_per_turn = 36;   // Angular resolution
    total_steps = ceil(length / pitch * steps_per_turn);
    step_z = length / total_steps;
    step_angle = 360.0 / steps_per_turn;

    tooth_half_w = pitch * 0.35 - backlash;  // Half tooth width at root
    tip_half_w = pitch * 0.15 - backlash;    // Half tooth width at tip

    for (s = [0:starts-1]) {
        start_offset_angle = s * 360 / starts;

        for (i = [0:total_steps-1]) {
            z1 = i * step_z;
            z2 = (i + 1) * step_z;
            a1 = i * step_angle + start_offset_angle;
            a2 = (i + 1) * step_angle + start_offset_angle;

            if (z1 < length && z2 <= length + step_z) {
                hull() {
                    rotate([0, 0, a1])
                        translate([0, 0, z1])
                        _thread_slice(outer_r, root_r, tooth_half_w, tip_half_w);

                    rotate([0, 0, a2])
                        translate([0, 0, z2])
                        _thread_slice(outer_r, root_r, tooth_half_w, tip_half_w);
                }
            }
        }
    }
}

// Single cross-section slice of the worm thread
module _thread_slice(outer_r, root_r, root_hw, tip_hw) {
    // Trapezoidal cross-section tooth profile
    linear_extrude(height = 0.01) {
        polygon([
            [root_r, -root_hw],
            [outer_r, -tip_hw],
            [outer_r, tip_hw],
            [root_r, root_hw],
        ]);
    }
}


// ---- Herringbone variants ----
// Split the gear in half axially with opposing helix angles
// Reduces axial thrust force on bearings

module herringbone_gear(
    teeth,
    mod = 1,
    thickness = 12,
    bore = 8,
    helix_angle = 15,    // degrees
    pressure_angle = 20,
    backlash = 0.15,
    hub_dia = 0,
    hub_h = 10
) {
    half_t = thickness / 2;
    twist = tan(helix_angle) * half_t * 360 / (PI * teeth * mod);

    difference() {
        union() {
            // Bottom half (right-hand helix)
            linear_extrude(height = half_t, twist = twist, slices = 20) {
                _gear_2d(teeth, mod, pressure_angle, backlash);
            }

            // Top half (left-hand helix)
            translate([0, 0, half_t])
                linear_extrude(height = half_t, twist = -twist, slices = 20) {
                    _gear_2d(teeth, mod, pressure_angle, backlash);
                }

            // Hub
            if (hub_h > 0) {
                actual_hub = hub_dia > 0 ? hub_dia : bore + wall_thick * 2;
                translate([0, 0, -hub_h])
                    cylinder(d = actual_hub, h = hub_h, $fn = 48);
            }
        }

        // Bore
        translate([0, 0, -hub_h - eps])
            cylinder(d = bore + tol * 2, h = thickness + hub_h + 2 * eps, $fn = 32);
    }
}


// ---- Coupler: shaft coupler for worm to motor shaft ----

module shaft_coupler(
    motor_shaft = 5,    // NEMA 17 shaft
    worm_bore = 5,      // Worm bore (same as motor shaft)
    length = 20,
    outer_dia = 16,
    clamp_slit = true   // Slit for clamping (M3 bolt)
) {
    difference() {
        cylinder(d = outer_dia, h = length, $fn = 32);

        // Through bore
        translate([0, 0, -eps])
            cylinder(d = motor_shaft + tol, h = length + 2 * eps, $fn = 24);

        // D-flat
        translate([motor_shaft/2 - 0.5, -outer_dia/2, -eps])
            cube([2, outer_dia, length + 2 * eps]);

        // Clamping slit
        if (clamp_slit) {
            translate([-outer_dia/2, -0.5, length * 0.3])
                cube([outer_dia, 1, length * 0.4]);

            // M3 clamp bolt hole
            translate([0, outer_dia/2, length * 0.5])
                rotate([90, 0, 0])
                cylinder(d = m3_through, h = outer_dia, $fn = 16);
        }
    }
}


// ---- Preview / test ----
// Uncomment to preview individual gears:

// Test: 80-tooth worm wheel for AZ axis
// worm_wheel(teeth=80, mod=1, face_width=12, bore=8, worm_dia=12, hub_h=10);

// Test: worm screw
// worm_screw(length=30, pitch_dia=12, mod=1, starts=1, bore=5);

// Test: spur gear
// spur_gear(teeth=20, mod=1, thickness=8, bore=5);

// Test: herringbone
// herringbone_gear(teeth=30, mod=1, thickness=12, bore=8, hub_h=8);
