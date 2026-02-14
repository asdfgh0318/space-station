// ============================================================
// Dish Clamp - Adjustable satellite dish rim clamp
// ============================================================
// Clamps to the rim of a 60-80cm offset satellite dish.
// Two clamps grip the dish rim and bolt to the pivot cross-bar.
// Adjustable via slotted bolt holes to accommodate different
// dish sizes and offset geometries.
// ============================================================

include <parameters.scad>;

// Clamp dimensions
clamp_length = 60;       // Along dish rim
clamp_width = 40;        // Perpendicular to rim
clamp_height = 25;       // Total height
rim_slot_width = dish_rim_thick + 2;  // Slot for dish rim material
rim_slot_depth = 15;     // How far the rim slides in

// Adjustment slot for different dish diameters
slot_length = 20;        // M5 bolt slides along this


module dish_clamp() {
    difference() {
        union() {
            // Main body
            translate([-clamp_width/2, -clamp_length/2, 0])
                cube([clamp_width, clamp_length, clamp_height]);

            // Rim grip jaw (bottom, wraps around dish rim)
            translate([-clamp_width/2, -clamp_length/2, -8])
                cube([clamp_width, clamp_length, 8]);
        }

        // Dish rim slot (the dish edge slides in here)
        translate([-clamp_width/2 - eps, -clamp_length/2 - eps, clamp_height - rim_slot_depth])
            cube([rim_slot_width + eps, clamp_length + 2 * eps, rim_slot_depth + eps]);

        // Clamping bolt hole (M5, squeezes the rim slot shut)
        translate([rim_slot_width + 5, 0, clamp_height/2])
            rotate([0, 90, 0])
            cylinder(d = m5_through, h = clamp_width, $fn = 16);

        // Adjustment slot (elongated hole for mounting bolt)
        // This allows sliding the clamp along the cross-bar
        translate([clamp_width/4, 0, -8 - eps])
            hull() {
                translate([0, -slot_length/2, 0])
                    cylinder(d = m5_through, h = 8 + clamp_height + 2 * eps, $fn = 16);
                translate([0, slot_length/2, 0])
                    cylinder(d = m5_through, h = 8 + clamp_height + 2 * eps, $fn = 16);
            }

        // Second adjustment slot
        translate([-clamp_width/4, 0, -8 - eps])
            hull() {
                translate([0, -slot_length/2, 0])
                    cylinder(d = m5_through, h = 8 + clamp_height + 2 * eps, $fn = 16);
                translate([0, slot_length/2, 0])
                    cylinder(d = m5_through, h = 8 + clamp_height + 2 * eps, $fn = 16);
            }

        // Rubber pad pocket (glue rubber strip here for grip)
        translate([-clamp_width/2 + 1, -clamp_length/2 + 5, clamp_height - rim_slot_depth + 1])
            cube([rim_slot_width - 1, clamp_length - 10, 2]);
    }
}


// Print 2 of these (one for each side of dish)
// dish_clamp();
