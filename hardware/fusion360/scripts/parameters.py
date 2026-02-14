"""
Space Station Antenna Tracker - Shared Parameters for Fusion 360 Scripts.

All dimensions in cm (Fusion 360 internal units).
Multiply mm values by 0.1 to get cm.

Import this in every part script:
    from parameters import P
    bore_radius = P.b608_id / 2
"""


class TrackerParams:
    """All shared dimensions for the antenna tracker."""

    # --- Tolerances (cm) ---
    tol = 0.03          # General clearance
    press_tol = 0.015   # Press fit
    loose_tol = 0.05    # Loose/moving fit

    # --- Bearings (cm) ---
    # 608ZZ
    b608_id = 0.8
    b608_od = 2.2
    b608_h = 0.7

    # 6001ZZ
    b6001_id = 1.2
    b6001_od = 2.8
    b6001_h = 0.8

    # 51107 thrust bearing
    bt51107_id = 3.5
    bt51107_od = 5.2
    bt51107_h = 1.2

    # --- Rods (cm) ---
    rod_dia = 0.8       # 8mm EL pivot shafts

    # --- NEMA 17 stepper (cm) ---
    nema17_face = 4.23
    nema17_hole_sp = 3.1    # Mounting hole spacing
    nema17_hole_dia = 0.3   # M3
    nema17_boss_dia = 2.2
    nema17_boss_h = 0.2
    nema17_shaft_d = 0.5
    nema17_shaft_l = 2.4
    nema17_body_l = 4.0

    # --- Worm gear parameters (cm) ---
    gear_module = 0.1   # Module 1 in mm = 0.1 cm

    # Azimuth
    az_teeth = 80
    az_worm_starts = 1
    az_worm_length = 3.0
    az_worm_dia = 1.2       # Pitch diameter
    az_wheel_pitch_d = 8.0  # 80 * 0.1
    az_wheel_outer_d = 8.2

    # Elevation
    el_teeth = 60
    el_worm_starts = 1
    el_worm_length = 2.5
    el_worm_dia = 1.2
    el_wheel_pitch_d = 6.0
    el_wheel_outer_d = 6.2

    # --- Structure (cm) ---
    wall = 0.4
    wall_heavy = 0.6

    # AZ base
    az_base_dia = 16.0
    az_base_h = 1.5
    az_turntable_dia = 14.0
    az_turntable_h = 1.2
    az_column_dia = 5.0
    az_column_h = 8.0

    # EL yoke
    el_yoke_width = 18.0
    el_yoke_arm_w = 3.0
    el_yoke_arm_h = 20.0
    el_yoke_thick = 2.5
    el_arm_spacing_inner = 16.0

    # Pivot position
    el_pivot_z = 11.7   # 65% of arm height from base

    # --- Fasteners (cm) ---
    m3_through = 0.34
    m4_through = 0.45
    m5_through = 0.55
    m3_insert_hole = 0.40
    m4_insert_hole = 0.50
    m5_insert_hole = 0.64
    m3_cbore_dia = 0.6
    m4_cbore_dia = 0.8
    m5_cbore_dia = 1.0

    # --- LNB (cm) ---
    lnb_neck_dia = 4.0
    lnb_neck_tol = 0.1

    # --- Electronics (cm) ---
    rpi4_w = 8.5
    rpi4_l = 5.6
    rpi4_h = 2.0
    rpi4_hole_sp_w = 5.8
    rpi4_hole_sp_l = 4.9

    # --- Build volume Ender 3 (cm) ---
    max_print_x = 22.0
    max_print_y = 22.0
    max_print_z = 25.0


# Singleton instance
P = TrackerParams()
