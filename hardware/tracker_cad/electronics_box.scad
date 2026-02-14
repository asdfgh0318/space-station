// ============================================================
// Electronics Enclosure
// ============================================================
// Weatherproof(ish) box for mounting on the tracker, containing:
//   - Raspberry Pi 4
//   - 2x TMC2209 stepper driver boards
//   - Power distribution (12V in, 5V for RPi via buck converter)
//   - Connectors panel (USB, Ethernet, SMA, motor cables)
//
// Snap-fit lid for easy access. Ventilation slots.
// Mounts to the AZ base or turntable column.
// ============================================================

include <parameters.scad>;

// Box dimensions (internal)
box_inner_w = 100;       // Width (X)
box_inner_l = 90;        // Length (Y) -- RPi 85mm + margin
box_inner_h = 40;        // Height (Z) -- RPi 20mm + drivers + wiring
box_wall = wall_thick;   // 4mm

// Derived
box_outer_w = box_inner_w + 2 * box_wall;
box_outer_l = box_inner_l + 2 * box_wall;
box_outer_h = box_inner_h + box_wall;  // No top wall (lid covers)

// Lid
lid_h = 8;
lid_lip = 2;             // Overlap lip depth


// === BOX (bottom half) ===

module electronics_box() {
    difference() {
        union() {
            // Outer shell
            translate([-box_outer_w/2, -box_outer_l/2, 0])
                cube([box_outer_w, box_outer_l, box_outer_h]);
        }

        // Inner cavity
        translate([-box_inner_w/2, -box_inner_l/2, box_wall])
            cube([box_inner_w, box_inner_l, box_inner_h + eps]);

        // Lid snap-fit groove (inside top edge)
        translate([-box_inner_w/2 - 0.5, -box_inner_l/2 - 0.5, box_outer_h - lid_lip])
            cube([box_inner_w + 1, box_inner_l + 1, lid_lip + eps]);

        // --- Connector cutouts ---

        // USB-C (RPi power) + Ethernet -- one end
        translate([-box_outer_w/2 - eps, -20, box_wall + 5])
            cube([box_wall + 2 * eps, 40, 18]);

        // Motor cable exits (2x, opposite end)
        for (y = [-15, 15]) {
            translate([box_outer_w/2 - box_wall - eps, y - 6, box_wall + 5])
                cube([box_wall + 2 * eps, 12, 12]);
        }

        // SMA cable pass-through (for SDR coax)
        translate([0, box_outer_l/2 - box_wall - eps, box_wall + box_inner_h/2])
            rotate([-90, 0, 0])
            cylinder(d = 8, h = box_wall + 2 * eps, $fn = 24);

        // Ventilation slots (sides)
        for (side = [-1, 1]) {
            for (i = [0:4]) {
                translate([side * (box_outer_w/2 - box_wall - eps),
                           -box_outer_l/4 + i * 12,
                           box_wall + 8])
                    cube([box_wall + 2 * eps, 8, 2]);
            }
        }

        // Ventilation slots (bottom)
        for (x = [-30, -10, 10, 30]) {
            translate([x - 4, -box_outer_l/4, -eps])
                cube([8, box_outer_l/2, box_wall + 2 * eps]);
        }

        // Mounting holes (M4, sides, for attaching to tracker)
        for (y = [-box_outer_l/4, box_outer_l/4]) {
            // Left side
            translate([-box_outer_w/2 - eps, y, box_outer_h/2])
                rotate([0, 90, 0])
                cylinder(d = m4_through, h = box_wall + 2 * eps, $fn = 16);
            // Right side
            translate([box_outer_w/2 - box_wall - eps, y, box_outer_h/2])
                rotate([0, 90, 0])
                cylinder(d = m4_through, h = box_wall + 2 * eps, $fn = 16);
        }
    }

    // --- Internal standoffs ---

    // RPi 4 mounting posts (M2.5 holes, 58x49mm pattern)
    rpi_offset_x = -box_inner_w/2 + 10;
    rpi_offset_y = -box_inner_l/2 + 8;
    standoff_h = 5;

    for (dx = [0, rpi4_hole_sp_w], dy = [0, rpi4_hole_sp_l]) {
        translate([rpi_offset_x + dx, rpi_offset_y + dy, box_wall]) {
            difference() {
                cylinder(d = 6, h = standoff_h, $fn = 16);
                translate([0, 0, -eps])
                    cylinder(d = 2.7, h = standoff_h + 2 * eps, $fn = 12);
            }
        }
    }

    // TMC2209 driver mounting area (next to RPi)
    // Just raised platforms, drivers attach with double-sided tape or clips
    translate([box_inner_w/2 - 25, -box_inner_l/2 + 5, box_wall])
        cube([20, 25, 2]);
    translate([box_inner_w/2 - 25, box_inner_l/2 - 30, box_wall])
        cube([20, 25, 2]);
}


// === LID ===

module electronics_lid() {
    difference() {
        union() {
            // Top plate
            translate([-box_outer_w/2, -box_outer_l/2, 0])
                cube([box_outer_w, box_outer_l, box_wall]);

            // Lip (fits inside box top edge)
            translate([-box_inner_w/2 + 0.3, -box_inner_l/2 + 0.3, -lid_lip])
                cube([box_inner_w - 0.6, box_inner_l - 0.6, lid_lip]);
        }

        // Ventilation holes in lid
        for (x = [-30, -10, 10, 30]) {
            for (y = [-25, 0, 25]) {
                translate([x, y, -eps])
                    cylinder(d = 4, h = box_wall + 2 * eps, $fn = 12);
            }
        }

        // Cable management clip holes
        for (x = [-box_outer_w/4, box_outer_w/4]) {
            translate([x, 0, -eps])
                cylinder(d = 3, h = box_wall + 2 * eps, $fn = 12);
        }
    }

    // Snap-fit bumps (flex tabs that click into box)
    for (side_x = [-1, 1]) {
        translate([side_x * (box_inner_w/2 - 1), 0, -lid_lip])
            cube([1.5, 10, 2], center = true);
    }
}


// === CABLE CHAIN CLIP ===
// Small clip that attaches to the tracker frame to route coax cable

module cable_clip(cable_dia = 7) {
    // RG6 coax is ~6.8mm
    clip_w = cable_dia + 2 * 2;  // 2mm walls
    clip_h = cable_dia + 4;
    clip_l = 10;

    difference() {
        union() {
            // Body
            translate([-clip_w/2, 0, 0])
                cube([clip_w, clip_l, clip_h]);

            // Mounting tab
            translate([-clip_w/2 - 5, 0, 0])
                cube([clip_w + 10, clip_l, 3]);
        }

        // Cable channel
        translate([0, -eps, clip_h - cable_dia/2 - 1])
            rotate([-90, 0, 0])
            cylinder(d = cable_dia + 0.5, h = clip_l + 2 * eps, $fn = 24);

        // Entry slit (cable snaps in from top)
        translate([-1, -eps, clip_h - cable_dia/2 - 1])
            cube([2, clip_l + 2 * eps, cable_dia]);

        // Mounting bolt hole (M3)
        translate([clip_w/2 + 2, clip_l/2, -eps])
            cylinder(d = m3_through, h = 5, $fn = 12);
        translate([-(clip_w/2 + 2), clip_l/2, -eps])
            cylinder(d = m3_through, h = 5, $fn = 12);
    }
}


// === PREVIEW ===

// electronics_box();
// translate([0, 0, box_outer_h + 5]) electronics_lid();
// translate([80, 0, 0]) cable_clip();
