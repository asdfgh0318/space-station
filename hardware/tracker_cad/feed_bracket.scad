// ============================================================
// Feed Arm & Quick-Swap LNB/Feed Bracket
// ============================================================
// Two parts:
//   1. Feed arm adapter - clamps to existing dish feed arm
//      (most satellite dishes come with a metal arm)
//   2. Quick-swap bracket - snap-fit holder that accepts
//      standard 40mm LNB necks or custom feed horns
//
// The quick-swap design allows tool-free switching between:
//   - Ku-band PLL LNB (12.2 GHz masers, satellite TV)
//   - L-band helicone feed (1.7 GHz HRPT, 1.4 GHz HI)
//   - Ka-band LNB (future, 22.2 GHz water masers)
// ============================================================

include <parameters.scad>;

// Feed arm clamp (fits existing dish arm, typically 18-25mm tube)
arm_tube_dia = 22;       // Existing dish feed arm tube OD
arm_clamp_length = 40;

// LNB holder
lnb_ring_height = 35;    // How much of the LNB neck we grip
lnb_ring_wall = 3;       // Wall thickness of the ring


// === FEED ARM CLAMP ===
// Clamps onto the existing dish feed support arm tube

module feed_arm_clamp() {
    outer_dia = arm_tube_dia + 2 * wall_thick + 4;

    difference() {
        union() {
            // Clamp ring
            cylinder(d = outer_dia, h = arm_clamp_length, $fn = 48);

            // Bracket extension for LNB holder attachment
            translate([outer_dia/2 - 2, -15, 0])
                cube([20, 30, arm_clamp_length]);
        }

        // Tube bore
        translate([0, 0, -eps])
            cylinder(d = arm_tube_dia + tol * 2, h = arm_clamp_length + 2 * eps, $fn = 48);

        // Clamping slit (allows squeezing around tube)
        translate([-1, -outer_dia, -eps])
            cube([2, outer_dia, arm_clamp_length + 2 * eps]);

        // Clamp bolt (M5, crosses the slit)
        for (z = [arm_clamp_length * 0.25, arm_clamp_length * 0.75]) {
            translate([-outer_dia, 0, z])
                rotate([0, 90, 0])
                cylinder(d = m5_through, h = outer_dia * 2, $fn = 16);
        }

        // LNB holder bolt holes (M4 heat-set inserts in bracket extension)
        for (z = [arm_clamp_length * 0.3, arm_clamp_length * 0.7]) {
            translate([outer_dia/2 + 10, -8, z])
                rotate([90, 0, 0])
                cylinder(d = m4_insert_hole, h = m4_insert_depth, $fn = 16);
            translate([outer_dia/2 + 10, 8, z])
                rotate([-90, 0, 0])
                cylinder(d = m4_insert_hole, h = m4_insert_depth, $fn = 16);
        }
    }
}


// === QUICK-SWAP LNB HOLDER ===
// Snap-fit ring that holds a standard 40mm LNB neck
// Spring tabs provide tool-free insertion/removal

module lnb_holder() {
    inner_r = (lnb_neck_dia + lnb_neck_tol) / 2;
    outer_r = inner_r + lnb_ring_wall;

    // Spring tab parameters
    tab_width = 8;
    tab_gap = 1.5;       // Gap behind tab for flex
    tab_depth = 2;        // How much tab protrudes inward

    difference() {
        union() {
            // Main ring
            cylinder(r = outer_r, h = lnb_ring_height, $fn = 64);

            // Mounting plate (bolts to feed arm clamp)
            translate([-outer_r - 5, -15, 0])
                cube([10, 30, lnb_ring_height]);
        }

        // LNB bore
        translate([0, 0, -eps])
            cylinder(r = inner_r, h = lnb_ring_height + 2 * eps, $fn = 64);

        // Spring tab cuts (3 tabs at 120 deg)
        for (a = [0, 120, 240]) {
            rotate([0, 0, a]) {
                // Slot on each side of the tab
                for (side = [-1, 1]) {
                    translate([0, 0, lnb_ring_height * 0.3])
                        rotate([0, 0, side * (tab_width/2 + tab_gap) * 180 / (PI * outer_r)])
                        translate([inner_r - 1, -0.5, 0])
                            cube([lnb_ring_wall + 3, 1, lnb_ring_height * 0.5]);
                }
            }
        }

        // F-connector cable exit slot (bottom)
        translate([inner_r - 2, -8, -eps])
            cube([outer_r + 5, 16, 8]);

        // Mounting holes (M4 through-holes, align with feed arm clamp)
        for (z = [lnb_ring_height * 0.3, lnb_ring_height * 0.7]) {
            translate([-outer_r - 5 + 5, -8, z])
                rotate([90, 0, 0])
                cylinder(d = m4_through, h = 5, $fn = 16);
            translate([-outer_r - 5 + 5, 8, z])
                rotate([-90, 0, 0])
                cylinder(d = m4_through, h = 5, $fn = 16);
        }
    }

    // Spring retention tabs (printed as part of the ring)
    for (a = [0, 120, 240]) {
        rotate([0, 0, a])
            translate([inner_r - tab_depth, -tab_width/2, lnb_ring_height * 0.45])
                cube([tab_depth, tab_width, lnb_ring_height * 0.15]);
    }
}


// === L-BAND HELICONE FEED ADAPTER ===
// Adapter ring that holds a 3D-printed helicone feed
// in place of the LNB. Same mounting interface.

module helicone_adapter() {
    // Helicone feed has ~50mm body diameter (varies by design)
    helicone_dia = 50;
    adapter_h = 30;

    inner_r = helicone_dia / 2 + 0.5;
    outer_r = inner_r + lnb_ring_wall;

    difference() {
        union() {
            cylinder(r = outer_r, h = adapter_h, $fn = 64);

            // Same mounting plate as LNB holder
            translate([-outer_r - 5, -15, 0])
                cube([10, 30, adapter_h]);
        }

        // Helicone body bore
        translate([0, 0, -eps])
            cylinder(r = inner_r, h = adapter_h + 2 * eps, $fn = 64);

        // Cable exit
        translate([inner_r - 2, -8, -eps])
            cube([outer_r + 5, 16, 8]);

        // Mounting holes (same pattern as LNB holder)
        for (z = [adapter_h * 0.3, adapter_h * 0.7]) {
            translate([-outer_r - 5 + 5, -8, z])
                rotate([90, 0, 0])
                cylinder(d = m4_through, h = 5, $fn = 16);
            translate([-outer_r - 5 + 5, 8, z])
                rotate([-90, 0, 0])
                cylinder(d = m4_through, h = 5, $fn = 16);
        }

        // Set screw (M3, to lock helicone in place)
        translate([outer_r + 1, 0, adapter_h/2])
            rotate([0, -90, 0])
            cylinder(d = m3_through, h = outer_r, $fn = 16);
    }
}


// === PREVIEW ===

// feed_arm_clamp();
// translate([60, 0, 0]) lnb_holder();
// translate([120, 0, 0]) helicone_adapter();
