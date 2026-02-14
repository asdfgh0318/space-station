// ============================================================
// Space Station Antenna Tracker - Shared Parameters
// ============================================================
// All dimensions in mm unless noted otherwise.
// Designed for Ender 3 (220x220mm bed) printing in PETG.
// ============================================================

// --- Print tolerances ---
// Adjust these based on your printer's calibration
tol         = 0.3;    // General clearance tolerance
press_tol   = 0.15;   // Press-fit tolerance (tighter)
loose_tol   = 0.5;    // Loose fit (moving parts)

// Layer height for calculations (typical PETG)
layer_h     = 0.2;

// --- Bearings ---
// 608ZZ (skateboard bearing)
b608_id     = 8;
b608_od     = 22;
b608_h      = 7;

// 6001ZZ (main shaft bearing)
b6001_id    = 12;
b6001_od    = 28;
b6001_h     = 8;

// 51107 thrust bearing (AZ axis)
bt51107_id  = 35;
bt51107_od  = 52;
bt51107_h   = 12;

// --- Steel rods ---
rod_dia     = 8;       // EL pivot shafts

// --- NEMA 17 stepper ---
nema17_face     = 42.3;
nema17_hole_sp  = 31;      // Hole center-to-center spacing
nema17_hole_dia = 3;       // M3 mounting holes
nema17_boss_dia = 22;      // Center boss diameter
nema17_boss_h   = 2;       // Center boss height
nema17_shaft_d  = 5;       // Shaft diameter
nema17_shaft_l  = 24;      // Shaft length
nema17_body_l   = 40;      // Motor body length (40mm variant)

// --- Worm gear parameters ---
// Module 1, pressure angle 20 deg
gear_module     = 1;       // Gear module (tooth size)
pressure_angle  = 20;      // Standard pressure angle

// Azimuth worm gear
az_worm_teeth   = 80;      // Worm wheel teeth (= gear ratio for single-start)
az_worm_starts  = 1;       // Single-start worm (self-locking)
az_worm_length  = 30;      // Worm screw length
az_worm_dia     = 12;      // Worm pitch diameter

// Elevation worm gear
el_worm_teeth   = 60;
el_worm_starts  = 1;
el_worm_length  = 25;
el_worm_dia     = 12;

// --- Gear derived dimensions ---
az_wheel_pitch_d = az_worm_teeth * gear_module;  // 80mm pitch dia
az_wheel_outer_d = az_wheel_pitch_d + 2 * gear_module;  // 82mm
el_wheel_pitch_d = el_worm_teeth * gear_module;  // 60mm pitch dia
el_wheel_outer_d = el_wheel_pitch_d + 2 * gear_module;  // 62mm

// Worm pitch = pi * module * starts
az_worm_pitch   = PI * gear_module * az_worm_starts;  // 3.14mm
el_worm_pitch   = PI * gear_module * el_worm_starts;

// --- Structural dimensions ---
wall_thick      = 4;       // Minimum wall thickness for PETG structural parts
wall_thick_heavy = 6;      // Heavy-duty walls (load-bearing)

// AZ base
az_base_dia     = 160;     // Base plate outer diameter
az_base_h       = 15;      // Base plate height
az_turntable_dia = 140;    // Turntable plate diameter
az_turntable_h  = 12;      // Turntable height
az_column_dia   = 50;      // Central column connecting AZ to EL
az_column_h     = 80;      // Column height

// EL yoke
el_yoke_width   = 180;     // Distance between yoke arms (outer)
el_yoke_arm_w   = 30;      // Yoke arm width (cross-section)
el_yoke_arm_h   = 200;     // Yoke arm height
el_yoke_thick   = 25;      // Yoke arm thickness

// Dish interface
dish_clamp_max_dia = 850;  // Max dish rim diameter
dish_clamp_min_dia = 550;  // Min dish rim diameter
dish_clamp_width   = 40;   // Clamp width
dish_rim_thick     = 3;    // Dish rim material thickness (typical sat dish)

// Feed arm
feed_arm_length = 400;     // Approximate focal length of 60-80cm offset dish
feed_arm_dia    = 25;      // Feed arm tube outer diameter

// LNB holder (standard 40mm LNB neck)
lnb_neck_dia    = 40;
lnb_neck_tol    = 1;       // Extra clearance for snap-fit

// --- Fasteners ---
// Heat-set insert holes (for M3, M4, M5)
m3_insert_hole  = 4.0;     // Hole for M3 heat-set insert
m3_insert_depth = 5;
m4_insert_hole  = 5.0;
m4_insert_depth = 6;
m5_insert_hole  = 6.4;
m5_insert_depth = 7;

// Through-holes
m3_through      = 3.4;
m4_through      = 4.5;
m5_through      = 5.5;
m8_through      = 8.5;

// Counterbore for socket head cap screws
m3_cbore_dia    = 6;
m3_cbore_depth  = 3.5;
m4_cbore_dia    = 8;
m4_cbore_depth  = 4.5;
m5_cbore_dia    = 10;
m5_cbore_depth  = 5.5;

// --- AS5600 encoder ---
as5600_board_w  = 20;      // Typical breakout board width
as5600_board_l  = 25;
as5600_board_h  = 2;
as5600_magnet_d = 6;       // Diametral magnet diameter
as5600_magnet_h = 3;       // Magnet height
as5600_sense_dist = 2;     // Air gap between magnet and sensor

// --- Electronics ---
rpi4_w          = 85;
rpi4_l          = 56;
rpi4_h          = 20;      // With heatsink
rpi4_hole_sp_w  = 58;      // Mounting hole spacing (width)
rpi4_hole_sp_l  = 49;      // Mounting hole spacing (length)

// TMC2209 driver board (StepStick form factor)
tmc_w           = 15.3;
tmc_l           = 20.3;
tmc_h           = 15;      // With heatsink

// --- Ender 3 build volume constraint ---
max_print_x     = 220;
max_print_y     = 220;
max_print_z     = 250;

// --- Helper ---
$fn = 64;  // Default facets for circles (increase for final render)

// Tiny value for clean boolean operations
eps = 0.01;
