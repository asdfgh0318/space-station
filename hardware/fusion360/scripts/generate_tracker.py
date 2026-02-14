"""
Space Station Antenna Tracker - Fusion 360 Part Generator

Run this as a Fusion 360 Script:
  1. In Fusion 360: Utilities → Scripts and Add-Ins → + (Add) → navigate to this file
  2. Select the script → Run
  3. Each part is generated as a separate component in the active design

Or run individual part functions from the Fusion 360 Python console.

All geometry uses the Fusion 360 API (adsk.core, adsk.fusion).
Dimensions from parameters.py (all in cm, Fusion internal units).
"""

import math
import traceback

import adsk.core
import adsk.fusion

# If running as script, parameters.py should be in same directory
# If not found, define inline
try:
    from parameters import P
except ImportError:
    # Inline fallback - same values
    class P:
        tol = 0.03; press_tol = 0.015; loose_tol = 0.05
        b608_id = 0.8; b608_od = 2.2; b608_h = 0.7
        b6001_id = 1.2; b6001_od = 2.8; b6001_h = 0.8
        bt51107_id = 3.5; bt51107_od = 5.2; bt51107_h = 1.2
        rod_dia = 0.8
        nema17_face = 4.23; nema17_hole_sp = 3.1; nema17_hole_dia = 0.3
        nema17_boss_dia = 2.2; nema17_boss_h = 0.2; nema17_shaft_d = 0.5
        nema17_body_l = 4.0
        gear_module = 0.1
        az_teeth = 80; az_worm_length = 3.0; az_worm_dia = 1.2
        az_wheel_pitch_d = 8.0; az_wheel_outer_d = 8.2
        el_teeth = 60; el_worm_length = 2.5; el_worm_dia = 1.2
        el_wheel_pitch_d = 6.0; el_wheel_outer_d = 6.2
        wall = 0.4; wall_heavy = 0.6
        az_base_dia = 16.0; az_base_h = 1.5
        az_turntable_dia = 14.0; az_turntable_h = 1.2
        az_column_dia = 5.0; az_column_h = 8.0
        el_arm_spacing_inner = 16.0; el_yoke_arm_w = 3.0
        el_yoke_thick = 2.5; el_pivot_z = 11.7
        m3_through = 0.34; m4_through = 0.45; m5_through = 0.55
        m3_insert_hole = 0.40; m4_insert_hole = 0.50; m5_insert_hole = 0.64
        m3_cbore_dia = 0.6; m4_cbore_dia = 0.8; m5_cbore_dia = 1.0
        lnb_neck_dia = 4.0; lnb_neck_tol = 0.1
        rpi4_w = 8.5; rpi4_l = 5.6; rpi4_h = 2.0
        rpi4_hole_sp_w = 5.8; rpi4_hole_sp_l = 4.9


def run(context):
    """Main entry point when run as Fusion 360 script."""
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        design = app.activeProduct

        if not design:
            ui.messageBox("No active design. Please create or open a design first.")
            return

        rootComp = design.rootComponent

        # Generate all parts as sub-components
        ui.messageBox(
            "Space Station Tracker Generator\n\n"
            "This will create all tracker parts as components.\n"
            "Each part will be a separate component you can edit.\n\n"
            "Click OK to generate.",
            "Space Station"
        )

        # Create main assembly occurrence
        tracker_occ = rootComp.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        tracker_comp = tracker_occ.component
        tracker_comp.name = "Antenna Tracker Assembly"

        # Generate each part
        _generate_az_base(tracker_comp)
        _generate_az_turntable(tracker_comp)
        _generate_az_worm_wheel(tracker_comp)
        _generate_el_yoke_base(tracker_comp)
        _generate_el_yoke_arm(tracker_comp, "Right")
        _generate_el_yoke_arm(tracker_comp, "Left")
        _generate_nema17_bracket(tracker_comp, "AZ Motor Bracket")
        _generate_nema17_bracket(tracker_comp, "EL Motor Bracket")
        _generate_dish_clamp(tracker_comp)
        _generate_lnb_holder(tracker_comp)
        _generate_electronics_box(tracker_comp)
        _generate_pivot_clamp(tracker_comp)

        ui.messageBox(
            "All parts generated!\n\n"
            "Each part is a separate component in the Browser panel.\n"
            "You can edit sketches and features parametrically.\n\n"
            "Tip: Right-click a component → 'Open' to edit in isolation.",
            "Space Station"
        )

    except Exception:
        if ui:
            ui.messageBox(f"Error:\n{traceback.format_exc()}")


# ==================================================================
# Part generators
# ==================================================================

def _new_component(parent, name):
    """Create a new sub-component and return (component, sketches helper)."""
    occ = parent.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    comp = occ.component
    comp.name = name
    return comp


def _circle_sketch(comp, plane, cx, cy, radius):
    """Helper: create a circle on a sketch."""
    sketch = comp.sketches.add(plane)
    circles = sketch.sketchCurves.sketchCircles
    center = adsk.core.Point3D.create(cx, cy, 0)
    circles.addByCenterRadius(center, radius)
    return sketch


def _rect_sketch(comp, plane, x, y, w, h):
    """Helper: create a rectangle on a sketch."""
    sketch = comp.sketches.add(plane)
    lines = sketch.sketchCurves.sketchLines
    p1 = adsk.core.Point3D.create(x, y, 0)
    p2 = adsk.core.Point3D.create(x + w, y + h, 0)
    lines.addTwoPointRectangle(p1, p2)
    return sketch


# ---- AZ BASE PLATE ----

def _generate_az_base(parent):
    comp = _new_component(parent, "AZ Base Plate")
    xy = comp.xYConstructionPlane

    # Main circular plate
    sk = _circle_sketch(comp, xy, 0, 0, P.az_base_dia / 2)
    prof = sk.profiles.item(0)
    ext = comp.features.extrudeFeatures
    ext_input = ext.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    ext_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(P.az_base_h))
    base_ext = ext.add(ext_input)

    # Thrust bearing pocket (top, center)
    sk2 = _circle_sketch(comp, comp.xYConstructionPlane, 0, 0,
                          P.bt51107_od / 2 + P.tol)
    prof2 = sk2.profiles.item(0)
    pocket_depth = P.bt51107_h / 2 + 0.1
    ext_input2 = ext.createInput(prof2, adsk.fusion.FeatureOperations.CutFeatureOperation)
    ext_input2.setDistanceExtent(False, adsk.core.ValueInput.createByReal(pocket_depth))
    ext_input2.startExtent = adsk.fusion.FromEntityStartDefinition.create(
        base_ext.endFaces.item(0), adsk.core.ValueInput.createByReal(0))
    ext.add(ext_input2)

    # Center wiring hole
    sk3 = _circle_sketch(comp, xy, 0, 0, 1.0)  # 20mm dia = 1.0cm radius
    prof3 = sk3.profiles.item(0)
    ext_input3 = ext.createInput(prof3, adsk.fusion.FeatureOperations.CutFeatureOperation)
    ext_input3.setDistanceExtent(True, adsk.core.ValueInput.createByReal(P.az_base_h + 0.1))
    ext.add(ext_input3)

    # Tripod mounting holes (3x M6 on 100mm = 10cm diameter circle)
    sk4 = comp.sketches.add(xy)
    for angle_deg in [30, 90, 150]:
        a = math.radians(angle_deg)
        cx = 5.0 * math.cos(a)
        cy = 5.0 * math.sin(a)
        sk4.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(cx, cy, 0), 0.325)  # M6 through = 6.5mm

    for i in range(sk4.profiles.count):
        prof4 = sk4.profiles.item(i)
        # Only cut the small circles, not the whole sketch
        if prof4.areaProperties().area < 1.0:
            ext_input4 = ext.createInput(prof4, adsk.fusion.FeatureOperations.CutFeatureOperation)
            ext_input4.setDistanceExtent(True, adsk.core.ValueInput.createByReal(P.az_base_h + 0.1))
            ext.add(ext_input4)

    return comp


# ---- AZ TURNTABLE ----

def _generate_az_turntable(parent):
    comp = _new_component(parent, "AZ Turntable")
    xy = comp.xYConstructionPlane

    # Turntable disk
    sk = _circle_sketch(comp, xy, 0, 0, P.az_turntable_dia / 2)
    prof = sk.profiles.item(0)
    ext = comp.features.extrudeFeatures
    ext_input = ext.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    ext_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(P.az_turntable_h))
    ext.add(ext_input)

    # Central column rising up (connects to EL yoke)
    sk2 = _circle_sketch(comp, xy, 0, 0, P.az_column_dia / 2)
    prof2 = sk2.profiles.item(0)
    ext_input2 = ext.createInput(prof2, adsk.fusion.FeatureOperations.JoinFeatureOperation)
    ext_input2.setDistanceExtent(False, adsk.core.ValueInput.createByReal(P.az_turntable_h + P.az_column_h))
    ext.add(ext_input2)

    # Thrust bearing boss (extends below turntable)
    boss_r = P.bt51107_id / 2 - 0.1
    sk3 = comp.sketches.add(xy)
    sk3.sketchCurves.sketchCircles.addByCenterRadius(
        adsk.core.Point3D.create(0, 0, 0), boss_r)
    # This sketch has 2 profiles (ring and inner circle) - get the annular one
    # For simplicity, just create a separate extrude downward
    prof3 = sk3.profiles.item(0)
    ext_input3 = ext.createInput(prof3, adsk.fusion.FeatureOperations.JoinFeatureOperation)
    ext_input3.setDistanceExtent(True, adsk.core.ValueInput.createByReal(P.bt51107_h / 2 + 0.1))
    ext.add(ext_input3)

    # Center wiring hole
    sk4 = _circle_sketch(comp, xy, 0, 0, 0.8)
    prof4 = sk4.profiles.item(0)
    ext_input4 = ext.createInput(prof4, adsk.fusion.FeatureOperations.CutFeatureOperation)
    total_h = P.az_turntable_h + P.az_column_h + P.bt51107_h
    ext_input4.setDistanceExtent(True, adsk.core.ValueInput.createByReal(total_h + 0.2))
    ext.add(ext_input4)

    return comp


# ---- AZ WORM WHEEL (simplified) ----

def _generate_az_worm_wheel(parent):
    """Generate a simplified worm wheel (cylinder with teeth represented as outer ring)."""
    comp = _new_component(parent, "AZ Worm Wheel (80T M1)")
    xy = comp.xYConstructionPlane

    face_width = 1.2  # 12mm

    # Outer diameter (tip circle)
    sk = _circle_sketch(comp, xy, 0, 0, P.az_wheel_outer_d / 2)
    # Inner bore (fits around column)
    bore_r = P.az_column_dia / 2 + P.loose_tol
    sk.sketchCurves.sketchCircles.addByCenterRadius(
        adsk.core.Point3D.create(0, 0, 0), bore_r)

    # Get the annular profile
    prof = None
    for i in range(sk.profiles.count):
        p = sk.profiles.item(i)
        area = p.areaProperties().area
        # The ring profile (not the bore)
        if area > 1.0:
            prof = p
            break

    if prof is None:
        prof = sk.profiles.item(0)

    ext = comp.features.extrudeFeatures
    ext_input = ext.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    ext_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(face_width))
    ext.add(ext_input)

    # Hub below
    hub_h = 1.0
    sk2 = comp.sketches.add(xy)
    sk2.sketchCurves.sketchCircles.addByCenterRadius(
        adsk.core.Point3D.create(0, 0, 0), P.az_column_dia / 2 + 0.6)
    sk2.sketchCurves.sketchCircles.addByCenterRadius(
        adsk.core.Point3D.create(0, 0, 0), bore_r)

    for i in range(sk2.profiles.count):
        p = sk2.profiles.item(i)
        if p.areaProperties().area > 0.5 and p.areaProperties().area < 20:
            ext_input2 = ext.createInput(p, adsk.fusion.FeatureOperations.JoinFeatureOperation)
            ext_input2.setDistanceExtent(True, adsk.core.ValueInput.createByReal(hub_h))
            ext.add(ext_input2)
            break

    # NOTE: Actual gear teeth should be cut using Fusion 360's built-in
    # Spur Gear add-in or the GF Gear Generator add-in from the store.
    # This generates the blank with correct diameters.

    return comp


# ---- EL YOKE BASE ----

def _generate_el_yoke_base(parent):
    comp = _new_component(parent, "EL Yoke Base")
    xy = comp.xYConstructionPlane

    base_w = P.el_arm_spacing_inner + 2 * P.el_yoke_thick
    base_d = 6.0  # 60mm
    base_h = 2.0  # 20mm

    # Main base block
    sk = _rect_sketch(comp, xy, -base_w / 2, -base_d / 2, base_w, base_d)
    prof = sk.profiles.item(0)
    ext = comp.features.extrudeFeatures
    ext_input = ext.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    ext_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(base_h))
    ext.add(ext_input)

    # Arm stubs on each side
    for side in [-1, 1]:
        x = side * (P.el_arm_spacing_inner / 2 + P.el_yoke_thick / 2) - P.el_yoke_thick / 2
        sk2 = _rect_sketch(comp, xy, x, -P.el_yoke_arm_w / 2, P.el_yoke_thick, P.el_yoke_arm_w)
        prof2 = sk2.profiles.item(0)
        ext_input2 = ext.createInput(prof2, adsk.fusion.FeatureOperations.JoinFeatureOperation)
        ext_input2.setDistanceExtent(False, adsk.core.ValueInput.createByReal(base_h + 1.5))
        ext.add(ext_input2)

    # Column mounting holes (M5, 4x)
    sk3 = comp.sketches.add(xy)
    for angle_deg in [0, 90, 180, 270]:
        a = math.radians(angle_deg)
        cx = (P.az_column_dia / 2 - 0.8) * math.cos(a)
        cy = (P.az_column_dia / 2 - 0.8) * math.sin(a)
        sk3.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(cx, cy, 0), P.m5_through / 2)

    for i in range(sk3.profiles.count):
        p = sk3.profiles.item(i)
        if p.areaProperties().area < 0.5:
            ext_input3 = ext.createInput(p, adsk.fusion.FeatureOperations.CutFeatureOperation)
            ext_input3.setDistanceExtent(True, adsk.core.ValueInput.createByReal(base_h + 0.1))
            ext.add(ext_input3)

    # Center wiring hole
    sk4 = _circle_sketch(comp, xy, 0, 0, 0.9)
    prof4 = sk4.profiles.item(0)
    ext_input4 = ext.createInput(prof4, adsk.fusion.FeatureOperations.CutFeatureOperation)
    ext_input4.setDistanceExtent(True, adsk.core.ValueInput.createByReal(base_h + 0.1))
    ext.add(ext_input4)

    return comp


# ---- EL YOKE ARM ----

def _generate_el_yoke_arm(parent, side_name="Right"):
    comp = _new_component(parent, f"EL Yoke Arm ({side_name})")
    xy = comp.xYConstructionPlane

    arm_h = 18.0  # Full arm height (will be split for printing)
    thick = P.el_yoke_thick
    width = P.el_yoke_arm_w

    # Arm body
    sk = _rect_sketch(comp, xy, -thick / 2, -width / 2, thick, width)
    prof = sk.profiles.item(0)
    ext = comp.features.extrudeFeatures
    ext_input = ext.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    ext_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(arm_h))
    ext.add(ext_input)

    # Pivot bearing pocket (6001ZZ at pivot height)
    # Create on the XZ plane at pivot height
    pivot_local_z = P.el_pivot_z - 2.0  # Relative to arm base (yoke base height offset)

    # Bearing pocket from one side
    bodies = comp.bRepBodies
    if bodies.count > 0:
        # Create a construction plane at pivot height
        planes = comp.constructionPlanes
        plane_input = planes.createInput()
        offset = adsk.core.ValueInput.createByReal(pivot_local_z)
        plane_input.setByOffset(xy, offset)
        pivot_plane = planes.add(plane_input)

        # Bearing hole on the pivot plane - actually we need it through the arm width
        # Create it as a hole feature through the Y-axis direction
        sk_pivot = comp.sketches.add(comp.xZConstructionPlane)
        # Position the circle at the pivot height
        sk_pivot.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(0, pivot_local_z, 0),
            P.b6001_od / 2 + P.tol)

        for i in range(sk_pivot.profiles.count):
            p = sk_pivot.profiles.item(i)
            if p.areaProperties().area < 1.0:
                ext_input_p = ext.createInput(p, adsk.fusion.FeatureOperations.CutFeatureOperation)
                ext_input_p.setDistanceExtent(True, adsk.core.ValueInput.createByReal(width + 0.2))
                ext.add(ext_input_p)

    # Weight reduction slot (rectangular pocket)
    sk_slot = _rect_sketch(comp, xy,
                           -thick / 2 + P.wall, -width / 4,
                           thick - 2 * P.wall, width / 2)
    prof_slot = sk_slot.profiles.item(0)
    ext_slot = ext.createInput(prof_slot, adsk.fusion.FeatureOperations.CutFeatureOperation)
    ext_slot.setDistanceExtent(False, adsk.core.ValueInput.createByReal(arm_h * 0.5))
    # Start from partway up
    ext.add(ext_slot)

    return comp


# ---- NEMA 17 MOTOR BRACKET ----

def _generate_nema17_bracket(parent, name="Motor Bracket"):
    comp = _new_component(parent, name)
    xy = comp.xYConstructionPlane

    plate_w = P.nema17_face + 1.0  # 52.3mm
    plate_h = P.nema17_face + 1.0
    thick = P.wall_heavy

    # Vertical mounting plate
    sk = _rect_sketch(comp, xy, -plate_w / 2, 0, plate_w, plate_h)
    prof = sk.profiles.item(0)
    ext = comp.features.extrudeFeatures
    ext_input = ext.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    ext_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(thick))
    ext.add(ext_input)

    # Base foot
    sk2 = _rect_sketch(comp, xy, -plate_w / 2, -3.0, plate_w, 3.0 + thick)
    prof2 = sk2.profiles.item(0)
    ext_input2 = ext.createInput(prof2, adsk.fusion.FeatureOperations.JoinFeatureOperation)
    ext_input2.setDistanceExtent(False, adsk.core.ValueInput.createByReal(P.wall))
    ext.add(ext_input2)

    # Motor shaft hole (center of plate)
    motor_cy = plate_h / 2
    sk3 = comp.sketches.add(xy)
    sk3.sketchCurves.sketchCircles.addByCenterRadius(
        adsk.core.Point3D.create(0, motor_cy, 0),
        P.nema17_boss_dia / 2 + 0.1)

    for i in range(sk3.profiles.count):
        p = sk3.profiles.item(i)
        if p.areaProperties().area < 2.0:
            ext_cut = ext.createInput(p, adsk.fusion.FeatureOperations.CutFeatureOperation)
            ext_cut.setDistanceExtent(True, adsk.core.ValueInput.createByReal(thick + 0.1))
            ext.add(ext_cut)

    # NEMA 17 mounting holes (M3, 31mm spacing)
    sk4 = comp.sketches.add(xy)
    for dx in [-1, 1]:
        for dy in [-1, 1]:
            cx = dx * P.nema17_hole_sp / 2
            cy = motor_cy + dy * P.nema17_hole_sp / 2
            sk4.sketchCurves.sketchCircles.addByCenterRadius(
                adsk.core.Point3D.create(cx, cy, 0), P.m3_through / 2)

    for i in range(sk4.profiles.count):
        p = sk4.profiles.item(i)
        if p.areaProperties().area < 0.2:
            ext_cut2 = ext.createInput(p, adsk.fusion.FeatureOperations.CutFeatureOperation)
            ext_cut2.setDistanceExtent(True, adsk.core.ValueInput.createByReal(thick + 0.1))
            ext.add(ext_cut2)

    return comp


# ---- DISH CLAMP ----

def _generate_dish_clamp(parent):
    comp = _new_component(parent, "Dish Clamp (print 2x)")
    xy = comp.xYConstructionPlane

    clamp_l = 6.0
    clamp_w = 4.0
    clamp_h = 2.5
    rim_slot_w = 0.5   # 5mm for dish rim

    # Main body
    sk = _rect_sketch(comp, xy, -clamp_w / 2, -clamp_l / 2, clamp_w, clamp_l)
    prof = sk.profiles.item(0)
    ext = comp.features.extrudeFeatures
    ext_input = ext.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    ext_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(clamp_h))
    ext.add(ext_input)

    # Lower jaw
    sk2 = _rect_sketch(comp, xy, -clamp_w / 2, -clamp_l / 2, clamp_w, clamp_l)
    prof2 = sk2.profiles.item(0)
    ext_input2 = ext.createInput(prof2, adsk.fusion.FeatureOperations.JoinFeatureOperation)
    ext_input2.setDistanceExtent(True, adsk.core.ValueInput.createByReal(0.8))
    ext.add(ext_input2)

    # Rim slot (cut from one side)
    sk3 = _rect_sketch(comp, xy, -clamp_w / 2 - 0.01, -clamp_l / 2 - 0.01,
                        rim_slot_w + 0.01, clamp_l + 0.02)
    prof3 = sk3.profiles.item(0)
    ext_input3 = ext.createInput(prof3, adsk.fusion.FeatureOperations.CutFeatureOperation)
    ext_input3.setDistanceExtent(False, adsk.core.ValueInput.createByReal(1.5))
    ext_input3.startExtent = adsk.fusion.FromEntityStartDefinition.create(
        ext.item(0).endFaces.item(0), adsk.core.ValueInput.createByReal(0))
    ext.add(ext_input3)

    return comp


# ---- LNB HOLDER ----

def _generate_lnb_holder(parent):
    comp = _new_component(parent, "LNB Quick-Swap Holder")
    xy = comp.xYConstructionPlane

    inner_r = (P.lnb_neck_dia + P.lnb_neck_tol) / 2
    wall = 0.3
    outer_r = inner_r + wall
    height = 3.5  # 35mm

    # Outer ring
    sk = comp.sketches.add(xy)
    sk.sketchCurves.sketchCircles.addByCenterRadius(
        adsk.core.Point3D.create(0, 0, 0), outer_r)
    sk.sketchCurves.sketchCircles.addByCenterRadius(
        adsk.core.Point3D.create(0, 0, 0), inner_r)

    # Get ring profile
    for i in range(sk.profiles.count):
        p = sk.profiles.item(i)
        area = p.areaProperties().area
        if 0.5 < area < 10:
            ext = comp.features.extrudeFeatures
            ext_input = ext.createInput(p, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
            ext_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(height))
            ext.add(ext_input)
            break

    # Mounting plate (side tab)
    sk2 = _rect_sketch(comp, xy, -outer_r - 0.5, -1.5, 1.0, 3.0)
    prof2 = sk2.profiles.item(0)
    ext2 = comp.features.extrudeFeatures
    ext_input2 = ext2.createInput(prof2, adsk.fusion.FeatureOperations.JoinFeatureOperation)
    ext_input2.setDistanceExtent(False, adsk.core.ValueInput.createByReal(height))
    ext2.add(ext_input2)

    return comp


# ---- ELECTRONICS BOX ----

def _generate_electronics_box(parent):
    comp = _new_component(parent, "Electronics Box")
    xy = comp.xYConstructionPlane

    inner_w = 10.0
    inner_l = 9.0
    inner_h = 4.0
    wall = P.wall

    outer_w = inner_w + 2 * wall
    outer_l = inner_l + 2 * wall
    outer_h = inner_h + wall

    # Outer box
    sk = _rect_sketch(comp, xy, -outer_w / 2, -outer_l / 2, outer_w, outer_l)
    prof = sk.profiles.item(0)
    ext = comp.features.extrudeFeatures
    ext_input = ext.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    ext_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(outer_h))
    ext.add(ext_input)

    # Inner cavity (shell operation would be ideal, but manual cut is simpler)
    sk2 = _rect_sketch(comp, xy, -inner_w / 2, -inner_l / 2, inner_w, inner_l)
    prof2 = sk2.profiles.item(0)
    ext_input2 = ext.createInput(prof2, adsk.fusion.FeatureOperations.CutFeatureOperation)
    ext_input2.setDistanceExtent(False, adsk.core.ValueInput.createByReal(inner_h))
    ext_input2.startExtent = adsk.fusion.FromEntityStartDefinition.create(
        ext.item(0).endFaces.item(0), adsk.core.ValueInput.createByReal(0))
    ext.add(ext_input2)

    return comp


# ---- PIVOT CLAMP ----

def _generate_pivot_clamp(parent):
    comp = _new_component(parent, "Pivot Clamp (print 2x)")
    xy = comp.xYConstructionPlane

    clamp_l = 4.0
    clamp_w = 3.0
    clamp_h = 2.5

    # Main block
    sk = _rect_sketch(comp, xy, -clamp_w / 2, -clamp_l / 2, clamp_w, clamp_l)
    prof = sk.profiles.item(0)
    ext = comp.features.extrudeFeatures
    ext_input = ext.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    ext_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(clamp_h))
    ext.add(ext_input)

    # Rod channel (8mm, through the length)
    sk2 = comp.sketches.add(comp.xZConstructionPlane)
    sk2.sketchCurves.sketchCircles.addByCenterRadius(
        adsk.core.Point3D.create(0, clamp_h / 2, 0),
        P.rod_dia / 2 + P.tol / 2)

    for i in range(sk2.profiles.count):
        p = sk2.profiles.item(i)
        if p.areaProperties().area < 0.5:
            ext_input2 = ext.createInput(p, adsk.fusion.FeatureOperations.CutFeatureOperation)
            ext_input2.setDistanceExtent(True, adsk.core.ValueInput.createByReal(clamp_l + 0.2))
            ext.add(ext_input2)

    # Clamp slit (vertical cut for clamping force)
    sk3 = _rect_sketch(comp, xy, -0.05, -clamp_l / 2 - 0.01, 0.1, clamp_l + 0.02)
    prof3 = sk3.profiles.item(0)
    ext_input3 = ext.createInput(prof3, adsk.fusion.FeatureOperations.CutFeatureOperation)
    ext_input3.setDistanceExtent(False, adsk.core.ValueInput.createByReal(clamp_h / 2 + 0.1))
    start_face = ext.item(0).endFaces.item(0)
    ext_input3.startExtent = adsk.fusion.FromEntityStartDefinition.create(
        start_face, adsk.core.ValueInput.createByReal(0))
    ext.add(ext_input3)

    return comp
