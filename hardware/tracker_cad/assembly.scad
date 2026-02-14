// ============================================================
// SPACE STATION - Full Tracker Assembly
// ============================================================
// Complete view of all 3D printed parts + hardware in position.
// Use this to verify fit and visualize the complete tracker.
//
// Render in OpenSCAD: F5 for preview, F6 for full render
// Recommend: View → Animate for exploded view
// ============================================================

include <parameters.scad>;
use <gears.scad>;
use <az_base.scad>;
use <el_yoke.scad>;
use <dish_clamp.scad>;
use <feed_bracket.scad>;
use <electronics_box.scad>;

// === Assembly configuration ===
explode = 0;             // Set 0-30 for exploded view spacing (mm)
show_dish = true;        // Show phantom dish outline
show_hardware = true;    // Show bearings, rods, motors (as phantoms)
show_electronics = true; // Show electronics box

// Current dish pointing (for visualization)
dish_az = 0;             // Azimuth angle (degrees)
dish_el = 45;            // Elevation angle (degrees)


// === ASSEMBLY ===

module full_assembly() {

    // ---- AZ BASE (stationary) ----
    color("DimGray", 0.9) {
        az_base_half();
        mirror([0, 1, 0]) az_base_half();
    }

    // Thrust bearing (phantom)
    if (show_hardware) {
        color("Silver", 0.5)
            translate([0, 0, az_base_h - bt51107_h/2])
            difference() {
                cylinder(d = bt51107_od, h = bt51107_h, $fn = 48);
                translate([0, 0, -eps])
                    cylinder(d = bt51107_id, h = bt51107_h + 2 * eps, $fn = 48);
            }
    }

    // ---- AZ TURNTABLE (rotates) ----
    rotate([0, 0, dish_az]) {

        translate([0, 0, az_base_h + explode]) {
            color("SteelBlue", 0.9) {
                az_turntable_half();
                mirror([0, 1, 0]) az_turntable_half();
            }

            // AZ Worm Wheel
            color("Gold", 0.8)
                translate([0, 0, -3])
                az_worm_wheel_printable();
        }

        // AZ Column (part of turntable, rises up)
        turntable_top = az_base_h + az_turntable_h + explode;

        // ---- AZ MOTOR + WORM ----
        if (show_hardware) {
            motor_z = az_base_h + 6;  // Worm center height
            worm_wheel_r = az_wheel_pitch_d / 2;
            worm_center_x = worm_wheel_r + az_worm_dia/2;

            // Motor body (phantom NEMA 17)
            color("DarkSlateGray", 0.4)
                translate([worm_center_x, 0, motor_z])
                rotate([0, 90, 0])
                translate([0, 0, 5]) {
                    // Motor body
                    cube([nema17_face, nema17_face, nema17_body_l], center = true);
                }

            // Worm screw
            color("Orange", 0.9)
                translate([worm_center_x, 0, motor_z])
                rotate([0, -90, 0])
                translate([0, 0, -az_worm_length/2])
                az_worm_printable();
        }

        // AZ Motor bracket
        color("Tomato", 0.8)
            translate([az_wheel_pitch_d/2 + az_worm_dia/2 + 8, 0, az_base_h])
            az_motor_bracket();

        // ---- EL YOKE ----
        yoke_base_z = turntable_top + az_column_h + explode * 2;

        translate([0, 0, yoke_base_z]) {

            // Yoke base
            color("CornflowerBlue", 0.9)
                el_yoke_base();

            base_h_local = 20;  // el_yoke_base height
            arm_x = arm_spacing_inner/2 + arm_thickness/2;

            // Right arm (worm wheel side)
            color("CadetBlue", 0.9) {
                translate([arm_x, 0, base_h_local + explode])
                    el_yoke_arm_lower(mirror_side = false);
                translate([arm_x, 0, base_h_local + arm_height/2 + explode * 2])
                    el_yoke_arm_upper(mirror_side = false);
            }

            // Left arm (mirror)
            color("CadetBlue", 0.9) {
                translate([-arm_x, 0, base_h_local + explode])
                    el_yoke_arm_lower(mirror_side = true);
                translate([-arm_x, 0, base_h_local + arm_height/2 + explode * 2])
                    el_yoke_arm_upper(mirror_side = true);
            }

            // ---- PIVOT ROD (8mm steel) ----
            pivot_abs_z = base_h_local + pivot_z;

            if (show_hardware) {
                color("Silver", 0.7)
                    translate([0, 0, pivot_abs_z])
                    rotate([0, 90, 0])
                    cylinder(d = rod_dia, h = arm_spacing_inner + arm_thickness * 2 + 20,
                             center = true, $fn = 24);
            }

            // ---- EL WORM WHEEL (on pivot rod) ----
            color("Gold", 0.8)
                translate([arm_x + arm_thickness/2 + 5, 0, pivot_abs_z])
                rotate([90, 0, 0])
                translate([0, 0, -5])
                el_worm_wheel_printable();

            // EL Motor bracket
            color("Tomato", 0.8)
                translate([arm_x + arm_thickness/2 + 2, 0, pivot_abs_z - 25])
                rotate([0, 0, 90])
                el_motor_bracket();

            // ---- EL MOTOR + WORM ----
            if (show_hardware) {
                el_motor_z = pivot_abs_z;
                el_worm_x = arm_x + arm_thickness/2 + el_wheel_pitch_d/2 + el_worm_dia/2 + 5;

                color("DarkSlateGray", 0.4)
                    translate([el_worm_x + 25, 0, el_motor_z])
                    rotate([0, -90, 0])
                    cube([nema17_face, nema17_face, nema17_body_l], center = true);

                color("Orange", 0.9)
                    translate([el_worm_x, 0, el_motor_z])
                    rotate([0, 90, 0])
                    translate([0, 0, -el_worm_length/2])
                    el_worm_printable();
            }

            // ---- DISH (rotating on EL axis) ----
            rotate([0, 0, 0])  // EL rotation would be around X axis at pivot
            translate([0, 0, pivot_abs_z]) {

                // Pivot clamps (2x, on rod)
                color("MediumSeaGreen", 0.9) {
                    translate([0, 0, 0])
                        rotate([0, 90, 0])
                        translate([-15, 0, -50])
                        pivot_clamp();
                    translate([0, 0, 0])
                        rotate([0, 90, 0])
                        translate([-15, 0, 20])
                        pivot_clamp();
                }

                // Dish clamps (2x)
                color("LimeGreen", 0.9) {
                    translate([-40, 30, 20 + explode])
                        rotate([dish_el - 90, 0, 0])
                        dish_clamp();
                    translate([40, 30, 20 + explode])
                        rotate([dish_el - 90, 0, 0])
                        dish_clamp();
                }

                // Phantom dish
                if (show_dish) {
                    dish_dia = 700;  // 70cm
                    color("White", 0.15)
                        translate([0, 0, 40])
                        rotate([dish_el - 90, 0, 0])
                        translate([0, 0, 100])  // Offset dish geometry
                        scale([1, 1, 0.15])
                        sphere(d = dish_dia, $fn = 32);
                }

                // Feed bracket (at focal point, approximate)
                color("Coral", 0.9)
                    translate([0, 0, 30])
                    rotate([dish_el - 90, 0, 0])
                    translate([0, -250, 0])  // Approximate focal distance
                    rotate([90, 0, 0]) {
                        feed_arm_clamp();
                        translate([35, 0, 0])
                            lnb_holder();
                    }
            }
        }

        // ---- ELECTRONICS BOX ----
        if (show_electronics) {
            color("DarkOliveGreen", 0.8)
                translate([0, -80, az_base_h + az_turntable_h + 20])
                electronics_box();
        }
    }
}


// ==== RENDER ====
full_assembly();


// ==== INDIVIDUAL PART EXPORT GUIDE ====
// To export STL for each part, uncomment ONE at a time
// and render with F6, then File → Export as STL
//
// --- AZ axis ---
// az_base_half();              // Print 2x (mirror one)
// az_turntable_half();         // Print 2x (mirror one)
// az_worm_wheel_printable();   // Print 1x, 60% infill
// az_worm_printable();         // Print 1x, 80% infill
// az_motor_bracket();          // Print 1x
//
// --- EL axis ---
// el_yoke_base();              // Print 1x
// el_yoke_arm_lower(false);    // Print 1x (right, worm side)
// el_yoke_arm_lower(true);     // Print 1x (left, mirror)
// el_yoke_arm_upper(false);    // Print 1x (right)
// el_yoke_arm_upper(true);     // Print 1x (left)
// el_worm_wheel_printable();   // Print 1x, 60% infill
// el_worm_printable();         // Print 1x, 80% infill
// el_motor_bracket();          // Print 1x
// pivot_clamp();               // Print 2x
//
// --- Accessories ---
// dish_clamp();                // Print 2x
// feed_arm_clamp();            // Print 1x
// lnb_holder();                // Print 1x per LNB type
// helicone_adapter();          // Print 1x (for L-band feed)
// electronics_box();           // Print 1x
// electronics_lid();           // Print 1x
// cable_clip();                // Print 6x
//
// TOTAL: ~22 parts, ~45 hours print time, ~800g PETG
