# Space Station Antenna Tracker -- Part Dimension Specification Sheet

**Project:** 3D-Printed Radio Telescope Antenna Tracker
**Revision:** 1.0
**Date:** 2026-02-14
**Material:** PETG (all printed parts)
**Printer:** Ender 3 (220 x 220 x 250 mm build volume)
**Units:** All dimensions in millimeters unless noted otherwise.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Bill of Materials -- Purchased Hardware](#2-bill-of-materials----purchased-hardware)
3. [General Print Settings](#3-general-print-settings)
4. [Tolerance Reference](#4-tolerance-reference)
5. [Fastener Hole Reference](#5-fastener-hole-reference)
6. [Part Specifications -- AZ Axis](#6-part-specifications----az-axis)
7. [Part Specifications -- EL Axis](#7-part-specifications----el-axis)
8. [Part Specifications -- Accessories](#8-part-specifications----accessories)
9. [Cross-Section Diagrams](#9-cross-section-diagrams)
10. [Assembly Order Checklist](#10-assembly-order-checklist)

---

## 1. Overview

This tracker is a two-axis (azimuth / elevation) worm-gear-driven antenna positioner
designed to hold a 550--850 mm offset satellite dish. It uses self-locking single-start
worm drives on both axes (80:1 AZ, 60:1 EL) driven by NEMA 17 steppers with TMC2209
silent drivers. The structure is entirely 3D printed in PETG, with steel rod pivots,
standard bearings, and heat-set threaded inserts for all fastener points.

**Total printed parts:** 22 (some printed multiple times)
**Estimated print time:** ~45 hours
**Estimated filament:** ~800 g PETG
**Assembled weight (without dish):** approximately 2.5 kg printed parts + 1 kg hardware

---

## 2. Bill of Materials -- Purchased Hardware

### Bearings

| Item | Specification | Qty | Dimensions (ID x OD x H) | Notes |
|------|--------------|-----|--------------------------|-------|
| Thrust bearing | 51107 | 1 | 35 x 52 x 12 | AZ axis main load bearing |
| Radial bearing | 608ZZ | 2 | 8 x 22 x 7 | AZ axis radial support |
| Radial bearing | 6001ZZ | 4 | 12 x 28 x 8 | EL pivot (2 per arm) |

### Shafts and Rods

| Item | Specification | Qty | Dimensions | Notes |
|------|--------------|-----|-----------|-------|
| Steel rod | 8mm precision ground | 1 | 8 dia x 240 long | EL pivot shaft, cut to length |

### Motors

| Item | Specification | Qty | Dimensions | Notes |
|------|--------------|-----|-----------|-------|
| Stepper motor | NEMA 17, 40mm body | 2 | 42.3 x 42.3 x 40 body, 5mm D-shaft x 24mm | 1.5-1.8A rated, 40+ N-cm |

### Electronics

| Item | Specification | Qty | Notes |
|------|--------------|-----|-------|
| Raspberry Pi 4 | Model B, 2GB+ | 1 | 85 x 56 mm, mount holes 58 x 49 mm |
| TMC2209 driver | StepStick form factor | 2 | 15.3 x 20.3 x 15 mm (with heatsink) |
| AS5600 encoder | Breakout board | 1-2 | 20 x 25 mm board, 6mm diametral magnet |
| 6mm magnet | Diametral (not axial) | 1-2 | 6 dia x 3 H | For AS5600 encoder |
| Buck converter | 12V to 5V, 3A+ | 1 | Powers RPi from 12V supply |
| 12V power supply | 5A+ | 1 | Barrel jack or Anderson connector |

### Fasteners -- Bolts (Socket Head Cap Screws, Stainless Steel)

| Item | Qty | Notes |
|------|-----|-------|
| M3 x 8 SHCS | 20 | Motor mounting (8 for 2 motors), encoder mount, misc |
| M3 x 12 SHCS | 8 | EL motor bracket-to-arm, cable clips |
| M3 x 6 grub screw | 2 | Worm wheel set screws, helicone adapter |
| M4 x 12 SHCS | 12 | Base halves joining, arm-to-base, motor bracket base |
| M4 x 16 SHCS | 8 | Arm upper-to-lower, pivot clamp bolt |
| M4 x 20 SHCS | 4 | Feed arm clamp-to-LNB bracket |
| M5 x 16 SHCS | 8 | Column-to-yoke base, pivot clamp dish mount |
| M5 x 20 SHCS | 4 | Dish clamp through-bolts |
| M5 x 30 SHCS | 2 | Dish rim clamping bolts (need length for jaw) |
| M5 x 25 SHCS | 2 | Feed arm clamp bolts |
| M2.5 x 6 SHCS | 4 | RPi mounting |

### Fasteners -- Heat-Set Inserts (Brass, Knurled)

| Item | Insert Hole Dia | Depth | Qty | Notes |
|------|----------------|-------|-----|-------|
| M3 heat-set insert | 4.0 | 5 | 18 | Motor mounts, encoder, cable clips, set screws |
| M4 heat-set insert | 5.0 | 6 | 20 | Arm joints, base splits, motor bracket, feed clamp, pivot clamp |
| M5 heat-set insert | 6.4 | 7 | 12 | Column top, pivot clamp dish mount, dish clamps |

### Fasteners -- Nuts and Washers

| Item | Qty | Notes |
|------|-----|-------|
| M5 nut | 6 | Dish clamp adjustment slots, feed arm clamp |
| M4 nut | 4 | Spare / backup for through-bolt joints |
| M3 nut | 4 | Spare |
| M5 flat washer | 10 | Under bolt heads on adjustment slots |
| M4 flat washer | 8 | Under bolt heads at joints |

### Miscellaneous

| Item | Qty | Notes |
|------|-----|-------|
| RG6 coaxial cable | ~3 m | 6.8 mm OD, from LNB to SDR |
| 4-conductor cable | ~2 m | 22 AWG, for stepper motors |
| Rubber strip (2mm) | 1 | For dish clamp grip pads |
| Camera tripod | 1 | With standard 1/4-20 or 3/8-16 mount |

---

## 3. General Print Settings

| Parameter | Value |
|-----------|-------|
| Material | PETG |
| Nozzle | 0.4 mm |
| Layer height | 0.2 mm |
| First layer height | 0.3 mm |
| Extrusion width | 0.45 mm |
| Print speed | 40-50 mm/s (walls), 60 mm/s (infill) |
| Bed temperature | 75-80 C |
| Nozzle temperature | 235-245 C |
| Part cooling fan | 30-50% |
| Default infill | 30% gyroid |
| Default walls | 4 perimeters (approx 1.8 mm) |
| Default top/bottom | 5 layers (1.0 mm) |
| Seam position | Rear or sharpest corner |

**Infill overrides** are noted per-part where structural loads demand higher density.

---

## 4. Tolerance Reference

These tolerances are calibrated for a well-tuned Ender 3 with PETG:

| Fit Type | Tolerance | Use |
|----------|----------|-----|
| General clearance | +0.3 mm on each side | Through-holes, loose assemblies |
| Press fit | +0.15 mm on each side | Bearing pockets, inserts before heat |
| Loose / sliding | +0.5 mm on each side | Rotating interfaces, worm around column |

For bearing pockets: Hole diameter = bearing OD + 2 x 0.15 mm (press fit).
For shaft bores: Hole diameter = shaft OD + 2 x 0.3 mm (general) or + 2 x 0.5 mm (loose sliding).

---

## 5. Fastener Hole Reference

### Through-Holes (clearance)

| Fastener | Nominal | Hole Diameter |
|----------|---------|--------------|
| M3 | 3.0 | 3.4 |
| M4 | 4.0 | 4.5 |
| M5 | 5.0 | 5.5 |
| M8 | 8.0 | 8.5 |

### Heat-Set Insert Holes

| Fastener | Insert Hole Dia | Insert Depth |
|----------|----------------|-------------|
| M3 | 4.0 | 5.0 |
| M4 | 5.0 | 6.0 |
| M5 | 6.4 | 7.0 |

### Counterbore Dimensions (Socket Head Cap Screws)

| Fastener | Counterbore Dia | Counterbore Depth |
|----------|----------------|------------------|
| M3 | 6.0 | 3.5 |
| M4 | 8.0 | 4.5 |
| M5 | 10.0 | 5.5 |

---

## 6. Part Specifications -- AZ Axis

### Part 1: AZ Base Half

| Property | Value |
|----------|-------|
| **Filename** | `az_base_half.stl` |
| **Quantity** | 2 (one mirrored) |
| **Infill** | 30% gyroid |
| **Print orientation** | Flat side down (split face on bed) |
| **Supports** | Yes -- for bearing pockets and counterbores |
| **Estimated time** | 3.5 h each |
| **Estimated weight** | 55 g each |

**Overall Dimensions:**
- Shape: half-circle, 160 mm diameter (80 mm radius) x 15 mm height
- Bolt flanges extend ~7 mm below the split line at +/- 48 mm from center

**Critical Dimensions:**

| Feature | Dimension | Tolerance |
|---------|----------|-----------|
| Outer diameter | 160.0 | +/- 0.5 |
| Height | 15.0 | +/- 0.2 |
| Thrust bearing pocket (top face) | 52.3 dia x 7.0 deep | Pocket dia: 52.0 + 0.3 (press fit) |
| 608ZZ radial bearing pockets (2x) | 22.3 dia x 8.0 deep | At 45 deg and 135 deg on R=31 mm circle |
| Center wiring hole | 20.0 dia, through | +/- 0.5 (non-critical) |
| Split-line bolt holes (2x) | M4 through (4.5 dia) | At +/- 48 mm from center, 5 mm from flat edge |
| Split-line counterbores (bottom) | 8.0 dia x 4.5 deep | Aligned with M4 through-holes |
| Tripod mount holes (3x) | 6.5 dia, through | On 100 mm diameter circle at 30, 90, 150 deg |
| Motor cutout (one half only) | 30 x 52.3 mm, through | At outer edge for worm motor approach |

**Assembly Notes:**
- Print two copies. Mirror one in slicer (flip on Y axis).
- The flat split face must be clean and flat; sand if needed.
- Insert 608ZZ bearings into pockets (light press fit; use a drop of thin CA glue if loose).
- Place 51107 thrust bearing in the center pocket.
- Join halves with 2x M4 x 12 bolts through the flange holes.
- Tripod holes are 6.5 mm for 1/4-20 UNC camera mount bolts (6.35 mm).

---

### Part 2: AZ Turntable Half

| Property | Value |
|----------|-------|
| **Filename** | `az_turntable_half.stl` |
| **Quantity** | 2 (one mirrored) |
| **Infill** | 30% gyroid |
| **Print orientation** | Flat side down (column pointing up) |
| **Supports** | Minimal -- for thrust boss underside |
| **Estimated time** | 3 h each |
| **Estimated weight** | 50 g each |

**Overall Dimensions:**
- Shape: half-circle, 140 mm diameter x 12 mm plate height
- Center column: 50 mm diameter, rises 20 mm above the plate (32 mm total from plate bottom)
- Thrust boss (underside): 33 mm diameter x 7 mm deep

**Critical Dimensions:**

| Feature | Dimension | Tolerance |
|---------|----------|-----------|
| Plate outer diameter | 140.0 | +/- 0.5 |
| Plate height | 12.0 | +/- 0.2 |
| Column diameter | 50.0 | +/- 0.3 |
| Column height above plate | 20.0 | +/- 0.5 |
| Thrust boss diameter (underside) | 33.0 (= 35 - 2) | Must slip inside 51107 ID (35 mm) |
| Thrust boss depth | 7.0 | Engages thrust bearing |
| Worm wheel M3 mounting holes | 3.4 dia, on R=30 mm circle, every 45 deg | 5 holes visible per half |
| Center wiring hole | 16.0 dia, through column + boss | +/- 0.5 |
| Split-line bolt holes (2x) | M4 through (4.5 dia) | At +/- 42 mm from center |
| M5 column-top insert holes (4x) | 6.4 dia x 7.0 deep | At 0/90/180/270 deg, R=17 mm from center |

**Assembly Notes:**
- Print two copies. Mirror one in slicer.
- Thrust boss must rotate freely inside the 51107 bearing inner race. Test fit before assembly.
- The column is integral -- both halves together form the full 50 mm cylinder.
- Install M5 heat-set inserts into the 4 column-top holes (for EL yoke base attachment).
- The worm wheel bolts to the ring of M3 holes on the turntable face.
- Join halves with 2x M4 x 12 bolts.

---

### Part 3: AZ Worm Wheel

| Property | Value |
|----------|-------|
| **Filename** | `az_worm_wheel.stl` |
| **Quantity** | 1 |
| **Infill** | 60% gyroid |
| **Print orientation** | Flat face down (teeth pointing up), or teeth-up for better tooth quality |
| **Supports** | No |
| **Estimated time** | 4 h |
| **Estimated weight** | 45 g |

**Overall Dimensions:**
- Outer diameter (tooth tips): 82.0 mm
- Pitch diameter: 80.0 mm
- Face width (tooth height): 12.0 mm
- Hub below gear: 8.0 mm tall, 62.0 mm diameter
- Total height: 20.0 mm (12 mm gear + 8 mm hub)

**Critical Dimensions:**

| Feature | Dimension | Tolerance |
|---------|----------|-----------|
| Number of teeth | 80 | Exact (generated by OpenSCAD) |
| Module | 1.0 | -- |
| Pressure angle | 20 deg | -- |
| Pitch diameter | 80.0 | +/- 0.2 |
| Outer diameter (tip) | 82.0 | +/- 0.3 |
| Root diameter | 77.5 (= 80 - 2x1.25) | +/- 0.3 |
| Face width | 12.0 | +/- 0.2 |
| Center bore | 51.0 (50 + 2x0.5 loose tol) | Must clear the 50 mm column |
| Hub diameter | 62.0 | -- |
| Hub height | 8.0 | -- |
| M3 bolt holes (mounting ring) | 3.4 dia, on R=30 mm circle | Match turntable pattern |
| Throat radius (concave cut) | 8.0 (= worm outer radius) | Improves worm contact |
| Gear backlash | 0.2 mm | Per-side clearance for smooth mesh |

**Assembly Notes:**
- This gear has a LARGE bore (51 mm) because it fits around the turntable column.
- It bolts to the turntable top face via M3 screws through the mounting ring.
- After bolting, verify the worm screw meshes with light backlash. Adjust worm motor bracket position if needed.
- Print at 60% infill for tooth strength. Consider 100% for the outer 8 mm (tooth zone) using modifier meshes.

---

### Part 4: AZ Worm Screw

| Property | Value |
|----------|-------|
| **Filename** | `az_worm_screw.stl` |
| **Quantity** | 1 |
| **Infill** | 80% gyroid |
| **Print orientation** | Horizontal (axis along X or Y), with supports |
| **Supports** | Yes -- under the thread profile |
| **Estimated time** | 1 h |
| **Estimated weight** | 8 g |

**Overall Dimensions:**
- Length: 30.0 mm
- Outer diameter (thread tip): 14.0 mm (= 12 + 2x1.0)
- Root diameter: 9.5 mm (= 12 - 2x1.25)
- Bore: 5.6 mm (5.0 + 2x0.3 for D-shaft)

**Critical Dimensions:**

| Feature | Dimension | Tolerance |
|---------|----------|-----------|
| Length | 30.0 | +/- 0.3 |
| Pitch diameter | 12.0 | +/- 0.15 (critical for mesh) |
| Outer diameter | 14.0 | +/- 0.2 |
| Axial pitch | 3.14 (= pi x 1 x 1) | Must match wheel module |
| Starts | 1 (single-start) | Self-locking |
| Bore diameter | 5.6 | Must slide onto NEMA 17 D-shaft |
| Keyway (D-flat) depth | 0.5 | Matches NEMA 17 shaft flat |
| Backlash | 0.15 per tooth side | -- |

**Assembly Notes:**
- This is the most dimensionally critical part. Print slowly (30 mm/s) with good cooling.
- Verify it slides onto the NEMA 17 shaft snugly but without excessive force.
- The keyway (D-flat) prevents rotation on the shaft. If too loose, use a drop of Loctite.
- Test mesh with the worm wheel before final assembly: rotate by hand, checking for smooth engagement with minimal binding.

---

### Part 5: AZ Motor Bracket

| Property | Value |
|----------|-------|
| **Filename** | `az_motor_bracket.stl` |
| **Quantity** | 1 |
| **Infill** | 40% gyroid |
| **Print orientation** | Vertical plate upright (base feet on bed) |
| **Supports** | Yes -- for gussets and motor boss hole |
| **Estimated time** | 1.5 h |
| **Estimated weight** | 25 g |

**Overall Dimensions:**
- Motor plate: 52.3 x 6.0 x 52.3 mm (W x D x H)
- Base feet: 52.3 x 30.0 x 4.0 mm
- Gussets: 20 x 20 mm triangular, 4 mm thick, both sides

**Critical Dimensions:**

| Feature | Dimension | Tolerance |
|---------|----------|-----------|
| NEMA 17 boss clearance hole | 24.0 dia (22 + 2 clearance) | Center of plate |
| NEMA 17 bolt holes (4x) | M3 through (3.4 dia), 31.0 spacing | Square pattern, 45 deg rotated |
| Bracket thickness | 6.0 (heavy wall) | +/- 0.3 |
| Base bolt holes (2x) | M4 through (4.5 dia) | At +/- 13 mm from center, 15 mm from plate |
| Worm-to-wheel center distance | 46.0 (= (80+12)/2) | Set by bracket position on base |

**Assembly Notes:**
- The bracket bolts to the AZ base plate with 2x M4 bolts through the base feet.
- Worm center distance from the wheel axis is critical: 46 mm (half of pitch dia sum).
- The bracket may need shimming (+/- 0.5 mm) to achieve correct mesh depth.
- Install NEMA 17 with 4x M3 x 8 bolts. Shaft points toward the worm wheel.
- Gussets provide lateral rigidity. Print them with good layer adhesion (high temp, low speed).

---

## 7. Part Specifications -- EL Axis

### Part 6: EL Yoke Base

| Property | Value |
|----------|-------|
| **Filename** | `el_yoke_base.stl` |
| **Quantity** | 1 |
| **Infill** | 40% gyroid |
| **Print orientation** | Flat on bed (base plate face down) |
| **Supports** | Minimal -- for weight-reduction hexagonal pockets |
| **Estimated time** | 3 h |
| **Estimated weight** | 55 g |

**Overall Dimensions:**
- Base plate: 210 x 60 x 20 mm (width x depth x height)
  - Width = arm_spacing_inner (160) + 2 x arm_thickness (25) = 210 mm
- Arm stubs: 25 x 30 x 35 mm, extending up from each end (15 mm above base top)

**Critical Dimensions:**

| Feature | Dimension | Tolerance |
|---------|----------|-----------|
| Base width | 210.0 | +/- 0.5 |
| Base depth | 60.0 | +/- 0.5 |
| Base height | 20.0 | +/- 0.3 |
| Arm stub spacing (center-to-center) | 185.0 (= 160 + 25) | +/- 0.3 |
| M5 column mount holes (4x) | 5.5 dia through | On 17 mm radius at 0/90/180/270 deg |
| Center wiring hole | 18.0 dia, through | +/- 0.5 |
| Arm stub M4 insert holes (4x total) | 5.0 dia x 6.0 deep | 2 per stub, at +/- 7.5 mm from arm center |
| Weight reduction pockets (2x) | 30.0 dia hex, through top | At +/- 40 mm from center |

**Assembly Notes:**
- This is the main structural cross-piece. Print with 40% infill for stiffness.
- Bolts to the AZ turntable column top via 4x M5 x 16 bolts into the column heat-set inserts.
- Install M4 heat-set inserts into the top of each arm stub for lower arm attachment.
- The 18 mm center hole allows motor and encoder wiring to pass through from the AZ column.

---

### Part 7: EL Yoke Arm Lower Right

| Property | Value |
|----------|-------|
| **Filename** | `el_yoke_arm_lower_right.stl` |
| **Quantity** | 1 |
| **Infill** | 40% gyroid |
| **Print orientation** | Upright (long axis vertical), wide face on bed |
| **Supports** | Minimal -- for weight slot and motor mount holes |
| **Estimated time** | 2 h |
| **Estimated weight** | 25 g |

**Overall Dimensions:**
- 25 x 30 x 90 mm (thickness x width x height)

**Critical Dimensions:**

| Feature | Dimension | Tolerance |
|---------|----------|-----------|
| Arm thickness | 25.0 | +/- 0.3 |
| Arm width | 30.0 | +/- 0.3 |
| Arm height (lower half) | 90.0 | +/- 0.3 |
| Bottom M4 through-holes (2x) | 4.5 dia | At +/- 7.5 mm from center, bottom face |
| Top M4 insert holes (2x) | 5.0 dia x 6.0 deep | At +/- 7.5 mm from center, top face |
| Weight reduction slot | 17 x 15 x 50 mm | Centered, from 20 mm to 70 mm height |
| Motor mount holes (outside face) | M3 inserts (4.0 dia x 5.0 deep) | 31 mm square pattern + 24 mm boss clearance |

**Assembly Notes:**
- This is the RIGHT arm (worm wheel / motor side).
- The outside face has NEMA 17 mounting holes for the EL motor bracket.
- Bolts to the yoke base arm stub (bottom) with 2x M4 x 16 through the bottom holes into the base inserts.
- Install M4 heat-set inserts in the top face for upper arm attachment.
- Install M3 heat-set inserts in the outside face for motor bracket mounting.

---

### Part 8: EL Yoke Arm Lower Left

| Property | Value |
|----------|-------|
| **Filename** | `el_yoke_arm_lower_left.stl` |
| **Quantity** | 1 |
| **Infill** | 40% gyroid |
| **Print orientation** | Same as right arm |
| **Supports** | Minimal |
| **Estimated time** | 1.5 h |
| **Estimated weight** | 22 g |

**Overall Dimensions:**
- Same as Part 7: 25 x 30 x 90 mm

**Critical Dimensions:**
- Same as Part 7 EXCEPT:
  - NO motor mount holes on outside face
  - Weight reduction slot is identical

**Assembly Notes:**
- Mirror of Part 7. If your slicer does not auto-mirror from the mirrored STL, flip on the X axis.
- Bolts to the left arm stub on the yoke base.
- Install M4 heat-set inserts in the top face only.

---

### Part 9: EL Yoke Arm Upper Right

| Property | Value |
|----------|-------|
| **Filename** | `el_yoke_arm_upper_right.stl` |
| **Quantity** | 1 |
| **Infill** | 40% gyroid |
| **Print orientation** | Upright (long axis vertical) |
| **Supports** | Yes -- for bearing pockets and rod through-hole |
| **Estimated time** | 2.5 h |
| **Estimated weight** | 28 g |

**Overall Dimensions:**
- 25 x 30 x 90 mm (thickness x width x height)

**Critical Dimensions:**

| Feature | Dimension | Tolerance |
|---------|----------|-----------|
| Arm dimensions | 25 x 30 x 90 mm | Same as lower arms |
| Bottom M4 through-holes (2x) | 4.5 dia | At +/- 7.5 mm from center |
| 6001ZZ bearing pockets (2x) | 28.6 dia x 8.3 deep | From both faces at pivot height |
| Pivot height (from bottom of upper arm) | 27.0 (= 117 - 90 = pivot_z - split_z) | Critical: 65% of 180 mm total - 90 mm split = 27 mm |
| 8mm rod through-hole | 9.0 dia (8 + 2x0.5) | Between the two bearing pockets |
| AS5600 encoder pocket (outer face) | 20 x 25 x 3 mm recess | Adjacent to bearing on right side |
| Weight reduction slot | 17 x 15 x ~32 mm | Upper portion of arm |

**Assembly Notes:**
- This is the RIGHT upper arm (encoder / worm wheel side).
- Press-fit 6001ZZ bearings into both pockets. They should be snug. If loose, use thin CA glue.
- The 8mm rod passes through both bearings and extends to the left arm.
- Mount the AS5600 breakout board in the pocket (glue or M2 screws). Align the magnet on the rod.
- Bolts to the lower right arm via 2x M4 x 16 bolts into the lower arm top inserts.

---

### Part 10: EL Yoke Arm Upper Left

| Property | Value |
|----------|-------|
| **Filename** | `el_yoke_arm_upper_left.stl` |
| **Quantity** | 1 |
| **Infill** | 40% gyroid |
| **Print orientation** | Same as right arm |
| **Supports** | Yes -- for bearing pockets and rod hole |
| **Estimated time** | 2 h |
| **Estimated weight** | 25 g |

**Overall Dimensions:**
- Same as Part 9: 25 x 30 x 90 mm

**Critical Dimensions:**
- Same as Part 9 EXCEPT:
  - NO AS5600 encoder pocket
  - Bearing pockets and rod hole are identical

**Assembly Notes:**
- Mirror of Part 9.
- Press-fit 6001ZZ bearings into both pockets.
- The 8mm rod passes through these bearings from the right arm.

---

### Part 11: EL Worm Wheel

| Property | Value |
|----------|-------|
| **Filename** | `el_worm_wheel.stl` |
| **Quantity** | 1 |
| **Infill** | 60% gyroid |
| **Print orientation** | Flat face down, hub up (or hub down for better tooth overhang) |
| **Supports** | No |
| **Estimated time** | 2 h |
| **Estimated weight** | 18 g |

**Overall Dimensions:**
- Outer diameter (tooth tips): 62.0 mm
- Pitch diameter: 60.0 mm
- Face width: 10.0 mm
- Hub: 20.0 mm diameter x 8.0 mm tall
- Total height: 18.0 mm (10 mm gear + 8 mm hub)

**Critical Dimensions:**

| Feature | Dimension | Tolerance |
|---------|----------|-----------|
| Number of teeth | 60 | Exact |
| Module | 1.0 | -- |
| Pressure angle | 20 deg | -- |
| Pitch diameter | 60.0 | +/- 0.2 |
| Outer diameter (tip) | 62.0 | +/- 0.3 |
| Root diameter | 57.5 | +/- 0.3 |
| Face width | 10.0 | +/- 0.2 |
| Bore | 8.6 (8 + 2x0.3) | Must fit on 8 mm rod with light clearance |
| Hub diameter | 20.0 | -- |
| Hub height | 8.0 | -- |
| M3 set screw hole (radial) | 3.4 dia through hub wall | Locks wheel to rod |
| Throat radius | 8.0 | Matches worm outer radius |
| Gear backlash | 0.2 mm per side | -- |

**Assembly Notes:**
- Slides onto the 8mm pivot rod on the right arm side, outside the bearing.
- Lock in position with an M3 x 6 grub screw through the radial set screw hole.
- The worm wheel must be axially positioned so its tooth face aligns with the worm screw.
- Verify free rotation of the pivot rod in the bearings before locking the wheel.

---

### Part 12: EL Worm Screw

| Property | Value |
|----------|-------|
| **Filename** | `el_worm_screw.stl` |
| **Quantity** | 1 |
| **Infill** | 80% gyroid |
| **Print orientation** | Horizontal (axis along X or Y), with supports |
| **Supports** | Yes -- under thread profile |
| **Estimated time** | 45 min |
| **Estimated weight** | 6 g |

**Overall Dimensions:**
- Length: 25.0 mm
- Outer diameter (thread tip): 14.0 mm
- Root diameter: 9.5 mm
- Bore: 5.6 mm

**Critical Dimensions:**

| Feature | Dimension | Tolerance |
|---------|----------|-----------|
| Length | 25.0 | +/- 0.3 |
| Pitch diameter | 12.0 | +/- 0.15 (critical) |
| Outer diameter | 14.0 | +/- 0.2 |
| Axial pitch | 3.14 | Must match wheel module |
| Starts | 1 | Self-locking |
| Bore | 5.6 | Fits NEMA 17 D-shaft |
| Keyway depth | 0.5 | -- |

**Assembly Notes:**
- Identical bore and keyway to AZ worm screw; only length and matching wheel differ.
- Print slowly for dimensional accuracy on the thread profile.
- Test mesh with EL worm wheel by hand before committing to the assembly.

---

### Part 13: EL Motor Bracket

| Property | Value |
|----------|-------|
| **Filename** | `el_motor_bracket.stl` |
| **Quantity** | 1 |
| **Infill** | 40% gyroid |
| **Print orientation** | Plate flat on bed, standoff feet pointing up |
| **Supports** | Yes -- for motor boss clearance hole |
| **Estimated time** | 1.5 h |
| **Estimated weight** | 20 g |

**Overall Dimensions:**
- Motor plate: 50.3 x 6.0 x 50.3 mm (W x D x H)
- Standoff feet: 10 x 15 mm, at +/- 12.5 mm from center

**Critical Dimensions:**

| Feature | Dimension | Tolerance |
|---------|----------|-----------|
| NEMA 17 boss hole | 24.0 dia | Center of plate |
| NEMA 17 bolt holes (4x) | M3 through (3.4 dia), 31.0 spacing | Square pattern |
| Plate thickness | 6.0 (heavy wall) | +/- 0.3 |
| Standoff feet length | 15.0 | Sets worm-to-wheel center distance |
| Mounting bolt holes (2x) | M3 through (3.4 dia) | In standoff feet, through to arm |
| Worm-to-wheel center dist | 36.0 (= (60+12)/2) | Set by standoff length + arm face |

**Assembly Notes:**
- Bolts to the outside face of the right lower yoke arm via the M3 inserts.
- Standoff feet create the spacing needed for correct worm mesh depth.
- If mesh is too tight or too loose, print shims or file the standoff feet.
- Motor shaft passes through the boss hole; worm screw attaches to shaft on the inside.

---

### Part 14: Pivot Clamp

| Property | Value |
|----------|-------|
| **Filename** | `pivot_clamp.stl` |
| **Quantity** | 2 |
| **Infill** | 40% gyroid |
| **Print orientation** | Rod channel facing up (clamp slit vertical) |
| **Supports** | Yes -- for rod channel overhang |
| **Estimated time** | 1 h each |
| **Estimated weight** | 12 g each |

**Overall Dimensions:**
- 30 x 40 x 25 mm (width x length x height)

**Critical Dimensions:**

| Feature | Dimension | Tolerance |
|---------|----------|-----------|
| Overall | 30 x 40 x 25 mm | +/- 0.3 |
| Rod channel | 8.3 dia (8 + 0.3) | Running through at Z = 12.5 mm (center height) |
| Clamping slit | 1.0 mm wide, from rod channel to top | Allows clamping force |
| M4 clamp bolt hole (top) | 4.5 dia, vertical | Crosses the slit to squeeze clamp shut |
| M5 dish mount insert holes (2x, bottom) | 6.4 dia x 7.0 deep | At +/- 10 mm along length, bottom face |

**Assembly Notes:**
- Slides onto the 8mm rod between the yoke arms.
- Position along the rod to match dish clamp attachment points.
- Tighten M4 bolt to clamp onto the rod (slit closes, gripping the rod).
- Dish clamps bolt to the bottom M5 inserts.
- Install M5 heat-set inserts before assembly.

---

## 8. Part Specifications -- Accessories

### Part 15: Dish Clamp

| Property | Value |
|----------|-------|
| **Filename** | `dish_clamp.stl` |
| **Quantity** | 2 |
| **Infill** | 40% gyroid |
| **Print orientation** | Jaw down on bed |
| **Supports** | Yes -- for rim slot overhang |
| **Estimated time** | 1.5 h each |
| **Estimated weight** | 20 g each |

**Overall Dimensions:**
- Main body: 40 x 60 x 25 mm (width x length x height)
- Jaw extension: adds 8 mm below (total height with jaw: 33 mm)

**Critical Dimensions:**

| Feature | Dimension | Tolerance |
|---------|----------|-----------|
| Body | 40 x 60 x 25 mm | +/- 0.5 |
| Jaw height | 8.0 below body | -- |
| Rim slot width | 5.0 (= 3 mm rim + 2 mm clearance) | Must accept dish rim material |
| Rim slot depth | 15.0 | Dish rim slides in this far |
| Rubber pad recess | 4 x 50 x 2 mm inside slot | Glue 2 mm rubber strip for grip |
| M5 clamping bolt hole | 5.5 dia, horizontal | Squeezes rim slot shut |
| Adjustment slots (2x) | 5.5 mm wide x 20 mm long | Vertical through body + jaw |
| Slot center spacing | 20 mm (at +/- 10 mm from center) | For M5 bolts to pivot clamp |

**Assembly Notes:**
- Two clamps grip opposite sides of the dish rim.
- Slide dish rim into the rim slot, then tighten the M5 clamping bolt to grip.
- Adjustment slots allow repositioning for different dish diameters (550-850 mm range).
- Bolt to pivot clamp M5 inserts using the adjustment slots.
- Glue a 2 mm rubber strip into the pad recess for non-slip grip.

---

### Part 16: Feed Arm Clamp

| Property | Value |
|----------|-------|
| **Filename** | `feed_arm_clamp.stl` |
| **Quantity** | 1 |
| **Infill** | 40% gyroid |
| **Print orientation** | Clamp ring horizontal (axis vertical) |
| **Supports** | Yes -- for clamping slit and bracket extension |
| **Estimated time** | 1.5 h |
| **Estimated weight** | 18 g |

**Overall Dimensions:**
- Clamp ring: 34 mm OD (22 + 2x4 + 2 clearance) x 40 mm long
- Bracket extension: 20 x 30 mm, extends radially from ring

**Critical Dimensions:**

| Feature | Dimension | Tolerance |
|---------|----------|-----------|
| Tube bore | 22.6 dia (22 + 2x0.3) | Must slide over 22 mm feed arm tube |
| Ring outer diameter | ~34 | Calculated: 22 + 2x4 + 4 = 34 |
| Clamp length | 40.0 | +/- 0.5 |
| Clamping slit | 2.0 mm wide, full length | Along one side for clamping action |
| M5 clamp bolt holes (2x) | 5.5 dia, horizontal crossing slit | At 25% and 75% height |
| M4 LNB bracket insert holes (4x) | 5.0 dia x 6.0 deep | In bracket extension, 2 per side |

**Assembly Notes:**
- Slides over the existing dish feed arm tube (typically 22 mm aluminum).
- Tighten 2x M5 bolts across the clamping slit to grip the tube.
- Install M4 heat-set inserts in the bracket extension for LNB holder attachment.
- The bracket extension provides the mounting face for the LNB holder or helicone adapter.

---

### Part 17: LNB Holder

| Property | Value |
|----------|-------|
| **Filename** | `lnb_holder.stl` |
| **Quantity** | 1 per LNB type |
| **Infill** | 30% gyroid |
| **Print orientation** | Ring vertical (axis horizontal on bed) |
| **Supports** | Yes -- for spring tab slots |
| **Estimated time** | 1 h |
| **Estimated weight** | 12 g |

**Overall Dimensions:**
- Ring: 47 mm OD x 35 mm height
  - Inner diameter: 41 mm bore (40 + 1 tolerance)
  - Wall: 3 mm
- Mounting plate: 10 x 30 mm, extends from ring

**Critical Dimensions:**

| Feature | Dimension | Tolerance |
|---------|----------|-----------|
| LNB bore diameter | 41.0 (40 + 1.0 tol) | Must accept 40 mm LNB neck |
| Ring wall thickness | 3.0 | -- |
| Ring outer diameter | 47.0 | -- |
| Ring height | 35.0 | +/- 0.5 |
| Spring tabs (3x at 120 deg) | 8 mm wide, 2 mm protrusion inward | At 45% height, spanning 15% of ring height |
| Tab flex slots | 1.5 mm gap behind each tab edge | Allow spring action |
| F-connector exit slot (bottom) | 16 x 8 mm cutout | For coax cable exit |
| M4 mounting holes (4x) | 4.5 dia through | Match feed arm clamp insert pattern |

**Assembly Notes:**
- Push LNB neck into the ring; spring tabs click to retain it.
- To remove: gently spread the ring and pull the LNB out.
- Bolts to the feed arm clamp bracket extension with 4x M4 bolts.
- F-connector cable exits through the bottom slot.
- Print one holder per LNB type you plan to use (Ku-band, Ka-band, etc.).

---

### Part 18: Helicone Adapter

| Property | Value |
|----------|-------|
| **Filename** | `helicone_adapter.stl` |
| **Quantity** | 1 |
| **Infill** | 30% gyroid |
| **Print orientation** | Ring vertical (axis horizontal) |
| **Supports** | Minimal |
| **Estimated time** | 1 h |
| **Estimated weight** | 14 g |

**Overall Dimensions:**
- Ring: 56 mm OD x 30 mm height (larger bore than LNB holder)
  - Inner diameter: 51 mm bore (50 + 1.0 tolerance)
  - Wall: 3 mm

**Critical Dimensions:**

| Feature | Dimension | Tolerance |
|---------|----------|-----------|
| Helicone bore diameter | 51.0 (50 + 1.0 tol) | Accepts ~50 mm helicone body |
| Ring outer diameter | ~56 | -- |
| Ring height | 30.0 | +/- 0.5 |
| M3 set screw (radial) | 3.4 dia through wall | Locks helicone in position |
| Cable exit slot | 16 x 8 mm | Bottom cutout |
| M4 mounting holes (4x) | 4.5 dia through | Same pattern as LNB holder |
| Mounting plate | 10 x 30 mm | Same as LNB holder |

**Assembly Notes:**
- Same mounting interface as the LNB holder (bolts to feed arm clamp).
- Helicone feed slides in; tighten M3 set screw to lock.
- Used for L-band (1.4 GHz hydrogen line, 1.7 GHz HRPT) observations.

---

### Part 19: Electronics Box

| Property | Value |
|----------|-------|
| **Filename** | `electronics_box.stl` |
| **Quantity** | 1 |
| **Infill** | 30% gyroid |
| **Print orientation** | Open top facing up |
| **Supports** | Yes -- for connector cutouts and ventilation slots |
| **Estimated time** | 4 h |
| **Estimated weight** | 65 g |

**Overall Dimensions:**
- Outer: 108 x 98 x 44 mm (W x L x H)
- Inner cavity: 100 x 90 x 40 mm
- Wall thickness: 4 mm (sides and bottom)

**Critical Dimensions:**

| Feature | Dimension | Tolerance |
|---------|----------|-----------|
| Outer dimensions | 108 x 98 x 44 mm | +/- 0.5 |
| Inner cavity | 100 x 90 x 40 mm | +/- 0.3 |
| Wall thickness | 4.0 all sides and bottom | +/- 0.2 |
| RPi standoffs (4x) | 6.0 dia x 5.0 tall, M2.5 holes (2.7 dia) | Pattern: 58 x 49 mm, offset 10 mm from left, 8 mm from front |
| TMC2209 platforms (2x) | 20 x 25 x 2 mm raised pads | Right side of cavity, front and rear |
| Lid snap-fit groove | 1.0 mm recess, 2 mm deep, inside top perimeter | For lid lip to engage |
| USB/Ethernet cutout (left wall) | 40 x 18 mm | At 5 mm above floor |
| Motor cable cutouts (2x, right wall) | 12 x 12 mm each | At +/- 15 mm from center, 5 mm above floor |
| SMA pass-through (rear wall) | 8.0 dia | Center of rear wall, mid-height |
| Ventilation slots (sides, 5x per side) | 8 x 2 mm | Starting 8 mm above floor, 12 mm spacing |
| Ventilation slots (bottom, 4x) | 8 x 45 mm | At -30, -10, +10, +30 mm from center |
| M4 side mounting holes (4x) | 4.5 dia through side walls | 2 per side, at +/- L/4 from center, mid-height |

**Assembly Notes:**
- Mount RPi 4 on the standoffs with 4x M2.5 x 6 screws (standoffs have 2.7 mm holes).
- TMC2209 boards sit on the raised platforms; secure with double-sided thermal tape or printed clips.
- Route wiring through the connector cutouts. Use cable glands or silicone for weather sealing.
- Mount box to the tracker using M4 bolts through the side mounting holes.
- Bottom ventilation allows passive airflow. Orient the box so bottom vents are not blocked.

---

### Part 20: Electronics Lid

| Property | Value |
|----------|-------|
| **Filename** | `electronics_lid.stl` |
| **Quantity** | 1 |
| **Infill** | 30% gyroid |
| **Print orientation** | Top face down on bed (lip pointing up) |
| **Supports** | No |
| **Estimated time** | 1 h |
| **Estimated weight** | 18 g |

**Overall Dimensions:**
- Top plate: 108 x 98 x 4 mm (matches box outer)
- Snap-fit lip: 99.4 x 89.4 x 2 mm (inner dims - 0.6 mm clearance)

**Critical Dimensions:**

| Feature | Dimension | Tolerance |
|---------|----------|-----------|
| Top plate | 108 x 98 x 4 mm | Must match box outer exactly |
| Lip dimensions | 99.4 x 89.4 x 2.0 mm | 0.3 mm clearance per side from inner cavity |
| Ventilation holes (12x) | 4.0 dia | 4x3 grid at 20 mm spacing |
| Cable management holes (2x) | 3.0 dia | At +/- 27 mm from center |
| Snap-fit bumps (2x) | 1.5 x 10 x 2 mm tabs | On side edges of lip, flex outward to click |

**Assembly Notes:**
- Press lid onto box; snap-fit bumps click into the groove.
- Pull straight up to remove (bumps flex inward).
- For outdoor use, add a bead of silicone around the lip seam.

---

### Part 21: Cable Clip

| Property | Value |
|----------|-------|
| **Filename** | `cable_clip.stl` |
| **Quantity** | 6 |
| **Infill** | 30% gyroid |
| **Print orientation** | Flat (mounting tab on bed) |
| **Supports** | No |
| **Estimated time** | 15 min each |
| **Estimated weight** | 3 g each |

**Overall Dimensions:**
- Body: 11 x 10 x 11 mm (width x length x height)
  - Width = 7 mm cable + 2x2 mm wall = 11 mm
  - Height = 7 mm cable + 4 mm = 11 mm
- Mounting tab: 21 x 10 x 3 mm (extends 5 mm each side beyond body)

**Critical Dimensions:**

| Feature | Dimension | Tolerance |
|---------|----------|-----------|
| Cable channel | 7.5 dia (7.0 + 0.5) | Sized for RG6 coax (6.8 mm) |
| Channel center height | 6.5 mm from tab top | Cable sits slightly recessed |
| Entry slit | 2.0 mm wide, top of channel to top of body | Cable snaps in from top |
| M3 mounting holes (2x) | 3.4 dia through tab | At +/- 7.5 mm from body center |
| Tab thickness | 3.0 | -- |

**Assembly Notes:**
- Snap RG6 coax cable into the clip from the top (slit opens, cable pushes in, slit closes).
- Mount to the tracker frame or yoke arms with M3 screws into heat-set inserts or self-tapping screws into pilot holes.
- Use 6 clips to route coax from the LNB, along the dish arm, through the elevation pivot area, down the column, and to the electronics box.

---

### Part 22: Tripod Adapter

This is integrated into the AZ Base Half (Part 1) as the 3x tripod mounting holes on the 100 mm diameter bolt circle. No separate part is required.

| Feature | Dimension | Notes |
|---------|----------|-------|
| Hole pattern | 3x holes at 30, 90, 150 deg on 100 mm dia circle | In the base plate |
| Hole diameter | 6.5 mm | Accepts 1/4-20 UNC (6.35 mm) camera tripod bolts |
| Compatibility | Standard camera tripod quick-release plates | Use with 1/4-20 to 3/8-16 adapter if needed |

---

## 9. Cross-Section Diagrams

### 9.1 AZ Bearing Stack (Vertical Cross-Section Through Center)

This shows how the base, thrust bearing, and turntable are stacked:

```
                    |<--- 50mm --->|
                    |   AZ Column  |
                    |  (turntable) |
        ============+=============+============
        |           |  M5 inserts |           |   ^
        |    AZ Turntable Plate (140mm dia)   |   | 12mm
        |           |             |           |   v
        +-----------+------+------+-----------+
                    | Boss |                      ^
                    | 33mm |                      | 7mm thrust boss
                    | dia  |                      v
        ............|......|......................
        :   ////////|======|========\\\\\\\\  :   ^
        :   // 51107 Thrust Bearing (52mm) \\ :   | 12mm bearing
        :   \\\\\\\\|======|========////////  :   v
        ............|......|......................
        |           | 20mm |                  |   ^
        |           | hole |                  |   |
        |      AZ Base Plate (160mm dia)      |   | 15mm
        |           |      |                  |   |
        |  [608ZZ]  |      |       [608ZZ]    |   v
        +===========+======+==================+
             ///                      \\\
            / Tripod mount holes (6.5mm) \
           /   on 100mm dia circle        \


    Legend:
        ====    Printed PETG part boundary
        ////    Bearing (steel)
        ....    Interface / contact surface
        [   ]   Bearing pocket
```

**Vertical Stack Dimensions:**

| Layer | Component | Height | Running Total |
|-------|-----------|--------|--------------|
| Bottom | AZ Base Plate | 15.0 | 0 to 15 |
| | Thrust bearing pocket (in base top) | 7.0 deep | Top of base down |
| Middle | 51107 Thrust Bearing | 12.0 | Splits between base and turntable |
| | Thrust boss (in turntable bottom) | 7.0 tall | Below turntable plate |
| Top | AZ Turntable Plate | 12.0 | Above bearing stack |
| | AZ Column | 80.0 above plate | 27 to 107 (from base bottom) |

**Radial Layout:**

| Feature | Radius (from center) |
|---------|---------------------|
| Center wiring hole | 0 -- 10 (base: 10mm R, turntable: 8mm R) |
| Thrust bearing ID | 17.5 |
| Thrust boss | 16.5 (= 35/2 - 1) |
| Thrust bearing OD | 26.0 |
| Thrust bearing pocket | 26.15 (26 + 0.15 press tol) |
| 608ZZ bearing pockets | Center at ~31 mm radius, at 45 and 135 deg |
| Worm wheel bolt ring | 30.0 |
| Turntable edge | 70.0 |
| Base edge | 80.0 |
| Tripod holes | 50.0 |

---

### 9.2 EL Pivot Assembly (Horizontal Cross-Section at Pivot Height, Looking Down)

This shows the 8mm rod passing through both yoke arms with bearings, the worm wheel, and motor:

```
                          EL Motor
                          (NEMA 17)
                            |  |
                            |  |
                      +-----+--+-----+
                      | Motor Bracket |
                      +-----+--+-----+
                            |  |
                      Worm  |  |
                      Screw |  | 5mm shaft
                            |  |
    Left Arm               \|  |/              Right Arm
    (mirror)            ~~~~+--+~~~~          (worm side)
                        ~ EL Worm  ~
    +--------+          ~ Wheel 62 ~          +--------+
    |        |          ~ dia OD   ~          |        |
    | 25x30  |          ~~~~+--+~~~~          | 25x30  |
    |  PETG  |              |  |              |  PETG  |
    |        |   +----+  +--+--+--+  +----+   |        |
    |[6001ZZ]|===|brg |==|  8mm   |==|brg |===|[6001ZZ]|
    |  28dia |   |8x28|  | steel  |  |8x28|   |  28dia |
    |  pocket|   +----+  |  rod   |  +----+   |  pocket|
    |        |           +--------+            |   +AS  |
    |        |                                 |   5600 |
    +--------+                                 +--------+
    |<-25mm->|  |<------- 160mm -------->|     |<-25mm->|
    |        |<------------ 210mm ------------->|       |


    Legend:
        [    ]  Bearing pocket (press-fit)
        brg     6001ZZ bearing (12 ID x 28 OD x 8 H)
        ====    8mm steel rod (continuous)
        ~~~~    Worm wheel teeth
        AS5600  Magnetic encoder board (right arm, outer face)
```

**Key Dimensions:**

| Feature | Dimension |
|---------|----------|
| Arm inner spacing | 160 mm |
| Arm outer spacing (total yoke width) | 210 mm |
| Arm cross-section | 25 x 30 mm |
| 8mm rod total length needed | ~240 mm (210 + margin) |
| Bearing pocket depth per side | 8.3 mm (bearing width + tolerance) |
| Rod-to-bearing fit | 12 mm ID bearing on 8 mm rod (use sleeve or tight tolerance) |
| Worm wheel position | Outside right arm bearing |
| Worm-to-wheel center distance | 36 mm (= (60+12)/2) |
| Pivot height from yoke base bottom | 137 mm (= 20 base + 117 pivot_z) |
| Pivot height along arm | 117 mm (= 65% of 180 mm) |

**Note on 6001ZZ / 8mm rod interface:** The 6001ZZ bearing has a 12 mm inner bore, but
the pivot rod is 8 mm. Use a printed or machined sleeve (12 mm OD, 8 mm ID) or select
bearings with 8 mm bore (such as 608ZZ at 22 mm OD, which is smaller). The current
design uses 6001ZZ for its larger outer race (better load distribution in the printed
pocket). A press-fit sleeve should be included or the rod stepped up to 12 mm.

---

### 9.3 Worm Gear Mesh (Side View, AZ Shown -- EL is Similar)

```
                         Worm Screw
                   (on NEMA 17 shaft, horizontal)

                         pitch dia 12mm
                        |<--------->|
                   _____|___     ___|_____
                  /  // | \\\   /// | \\  \       ^
                 |  //  |  \\\ ///  |  \\  |      |
                 | //   |   \\X//   |   \\ |   14mm outer dia
                 | \\   |   //X\\   |   // |      |
                 |  \\  |  /// \\\\\ |  //  |      |
                  \__\\_|_///   \\\\_|_//  /       v
                        |  3.14mm   |
                        |  pitch    |
                        |           |
    ----Center----------|-----------|----------Center----
    distance            |           |           distance
    46mm (AZ)           |           |           36mm (EL)
    or 36mm (EL)        |           |
                        |           |
         _______________v___________v_______________
        /           Worm Wheel (top view)           \
       /              80mm pitch dia (AZ)            \
      |               60mm pitch dia (EL)             |
      |                                               |
      |    Teeth: 80 (AZ) or 60 (EL)                 |
      |    Module: 1                                  |
      |    Face width: 12mm (AZ) or 10mm (EL)        |
      |                                               |
       \                                             /
        \___________________________________________/


    Key mesh parameters:
        Module (m)        = 1.0 mm
        Pressure angle    = 20 deg
        Backlash          = 0.15-0.20 mm per side

    AZ axis:                      EL axis:
        Worm wheel teeth  = 80        Worm wheel teeth  = 60
        Gear ratio        = 80:1      Gear ratio        = 60:1
        Wheel pitch dia   = 80mm      Wheel pitch dia   = 60mm
        Wheel outer dia   = 82mm      Wheel outer dia   = 62mm
        Wheel root dia    = 77.5mm    Wheel root dia    = 57.5mm
        Worm pitch dia    = 12mm      Worm pitch dia    = 12mm
        Worm outer dia    = 14mm      Worm outer dia    = 14mm
        Worm length       = 30mm      Worm length       = 25mm
        Center distance   = 46mm      Center distance   = 36mm
        Axial pitch       = 3.14mm    Axial pitch       = 3.14mm
        Lead angle        = ~4.8 deg  Lead angle        = ~4.8 deg
        Self-locking      = YES       Self-locking      = YES
```

**Self-Locking Note:** With a lead angle of approximately 4.8 degrees and a printed
PETG-on-PETG friction coefficient of roughly 0.3-0.4, the worm drive is firmly
self-locking. This means the dish will hold position when the motors are unpowered.
Apply a thin layer of white lithium grease to the worm threads for smooth operation
and reduced wear.

---

## 10. Assembly Order Checklist

Follow this order for a clean build. Do not skip ahead -- each step depends on the previous.

### Phase 1: Prepare All Parts

- [ ] Print all 22 parts (verify dimensions of critical features with calipers)
- [ ] Clean up all parts: remove supports, file/sand split faces, clear all holes
- [ ] Test-fit all bearings in their pockets (should be snug press fit)
- [ ] Test-fit 8mm rod through 6001ZZ bearings
- [ ] Test-mesh both worm/wheel pairs by hand (should rotate smoothly)
- [ ] Install ALL heat-set inserts while parts are accessible:
  - [ ] AZ turntable column top: 4x M5 inserts
  - [ ] EL yoke base arm stubs: 4x M4 inserts (2 per stub)
  - [ ] EL lower arm tops: 4x M4 inserts (2 per arm, both arms)
  - [ ] EL lower right arm outside face: 4x M3 inserts (motor mount)
  - [ ] Pivot clamps: 4x M5 inserts (2 per clamp, bottom face)
  - [ ] Feed arm clamp bracket: 4x M4 inserts
  - [ ] Electronics box: RPi standoffs already have M2.5 holes (no inserts needed)

### Phase 2: AZ Axis Assembly

- [ ] 2.1 Join AZ base halves with 2x M4 x 12 bolts
- [ ] 2.2 Press 608ZZ bearings into base pockets (2x)
- [ ] 2.3 Place 51107 thrust bearing in base center pocket
- [ ] 2.4 Join AZ turntable halves with 2x M4 x 12 bolts
- [ ] 2.5 Set turntable boss into thrust bearing inner race (test rotation: should spin freely)
- [ ] 2.6 Bolt AZ worm wheel to turntable face (M3 x 8 screws through mounting ring)
- [ ] 2.7 Attach AZ motor bracket to base plate (2x M4 x 12 bolts through bracket feet)
- [ ] 2.8 Mount NEMA 17 motor to AZ bracket (4x M3 x 8 bolts)
- [ ] 2.9 Slide AZ worm screw onto motor shaft (keyway aligned with D-flat)
- [ ] 2.10 Adjust bracket position until worm meshes with wheel (light contact, minimal backlash)
- [ ] 2.11 Tighten all AZ bolts; verify smooth 360-degree rotation by hand

### Phase 3: EL Yoke Assembly

- [ ] 3.1 Bolt EL yoke base to AZ turntable column top (4x M5 x 16 into column inserts)
- [ ] 3.2 Bolt lower right arm to right yoke base stub (2x M4 x 16)
- [ ] 3.3 Bolt lower left arm to left yoke base stub (2x M4 x 16)
- [ ] 3.4 Press 6001ZZ bearings into upper right arm pockets (2x)
- [ ] 3.5 Press 6001ZZ bearings into upper left arm pockets (2x)
- [ ] 3.6 Bolt upper right arm to lower right arm (2x M4 x 16)
- [ ] 3.7 Bolt upper left arm to lower left arm (2x M4 x 16)
- [ ] 3.8 Slide 8mm steel rod through left arm bearings, across to right arm bearings
- [ ] 3.9 Slide EL worm wheel onto rod (right side, outside right arm bearing)
- [ ] 3.10 Lock worm wheel with M3 x 6 grub screw
- [ ] 3.11 Mount AS5600 board in right arm pocket; glue magnet to rod end
- [ ] 3.12 Bolt EL motor bracket to right arm outside face (M3 x 12 into arm inserts)
- [ ] 3.13 Mount NEMA 17 motor to EL bracket (4x M3 x 8)
- [ ] 3.14 Slide EL worm screw onto motor shaft
- [ ] 3.15 Adjust EL bracket until worm meshes with wheel correctly
- [ ] 3.16 Verify smooth elevation rotation by hand (~+/- 90 degrees)

### Phase 4: Dish Mounting

- [ ] 4.1 Slide 2x pivot clamps onto 8mm rod (position between yoke arms)
- [ ] 4.2 Tighten pivot clamp M4 bolts to grip rod
- [ ] 4.3 Bolt dish clamps to pivot clamp M5 inserts (M5 x 20 through adjustment slots)
- [ ] 4.4 Slide dish rim into clamp rim slots
- [ ] 4.5 Tighten dish clamp M5 clamping bolts to grip rim
- [ ] 4.6 Adjust dish balance: slide clamps along rod and along adjustment slots until dish is balanced on the pivot axis

### Phase 5: Feed System

- [ ] 5.1 Slide feed arm clamp onto dish feed arm tube
- [ ] 5.2 Tighten 2x M5 clamp bolts
- [ ] 5.3 Bolt LNB holder (or helicone adapter) to feed arm clamp bracket (4x M4 x 20)
- [ ] 5.4 Insert LNB into holder (spring tabs click)
- [ ] 5.5 Connect RG6 coax from LNB F-connector through the exit slot

### Phase 6: Electronics

- [ ] 6.1 Mount RPi 4 in electronics box (4x M2.5 x 6 screws on standoffs)
- [ ] 6.2 Place TMC2209 drivers on raised platforms (secure with tape)
- [ ] 6.3 Wire stepper motor cables through motor cutouts
- [ ] 6.4 Wire power (12V in, buck converter for 5V RPi)
- [ ] 6.5 Connect AS5600 encoder(s) via I2C
- [ ] 6.6 Route RG6 coax to SDR through SMA pass-through
- [ ] 6.7 Snap lid onto box
- [ ] 6.8 Mount electronics box to tracker frame (2x M4 bolts through side holes)

### Phase 7: Cable Management

- [ ] 7.1 Route coax cable from LNB along dish arm, through elevation area, down column
- [ ] 7.2 Install 6x cable clips along the route (M3 screws)
- [ ] 7.3 Leave service loops at both axes to allow rotation without cable strain
- [ ] 7.4 Mount tracker on tripod via base plate tripod holes

### Phase 8: Commissioning

- [ ] 8.1 Power on; verify motor drivers initialize (no error LEDs)
- [ ] 8.2 Test AZ rotation: command small moves, verify smooth motion
- [ ] 8.3 Test EL rotation: command small moves, verify smooth motion
- [ ] 8.4 Verify encoder readings track motor commands
- [ ] 8.5 Calibrate: point at a known satellite (e.g., Astra 19.2E) and zero the encoders
- [ ] 8.6 Run a tracking test: command a satellite pass and verify the dish follows

---

## Appendix A: Print Time and Filament Estimates

| Part | Qty | Time Each | Total Time | Weight Each | Total Weight |
|------|-----|-----------|------------|-------------|-------------|
| AZ Base Half | 2 | 3.5 h | 7.0 h | 55 g | 110 g |
| AZ Turntable Half | 2 | 3.0 h | 6.0 h | 50 g | 100 g |
| AZ Worm Wheel | 1 | 4.0 h | 4.0 h | 45 g | 45 g |
| AZ Worm Screw | 1 | 1.0 h | 1.0 h | 8 g | 8 g |
| AZ Motor Bracket | 1 | 1.5 h | 1.5 h | 25 g | 25 g |
| EL Yoke Base | 1 | 3.0 h | 3.0 h | 55 g | 55 g |
| EL Lower Arm R | 1 | 2.0 h | 2.0 h | 25 g | 25 g |
| EL Lower Arm L | 1 | 1.5 h | 1.5 h | 22 g | 22 g |
| EL Upper Arm R | 1 | 2.5 h | 2.5 h | 28 g | 28 g |
| EL Upper Arm L | 1 | 2.0 h | 2.0 h | 25 g | 25 g |
| EL Worm Wheel | 1 | 2.0 h | 2.0 h | 18 g | 18 g |
| EL Worm Screw | 1 | 0.75 h | 0.75 h | 6 g | 6 g |
| EL Motor Bracket | 1 | 1.5 h | 1.5 h | 20 g | 20 g |
| Pivot Clamp | 2 | 1.0 h | 2.0 h | 12 g | 24 g |
| Dish Clamp | 2 | 1.5 h | 3.0 h | 20 g | 40 g |
| Feed Arm Clamp | 1 | 1.5 h | 1.5 h | 18 g | 18 g |
| LNB Holder | 1 | 1.0 h | 1.0 h | 12 g | 12 g |
| Helicone Adapter | 1 | 1.0 h | 1.0 h | 14 g | 14 g |
| Electronics Box | 1 | 4.0 h | 4.0 h | 65 g | 65 g |
| Electronics Lid | 1 | 1.0 h | 1.0 h | 18 g | 18 g |
| Cable Clip | 6 | 0.25 h | 1.5 h | 3 g | 18 g |
| **TOTALS** | | | **~49 h** | | **~696 g** |

*Note: Estimates assume 0.2 mm layer height, 30-40% infill default, 50 mm/s average
speed. Actual times vary by slicer settings and printer calibration. Add 15-20% margin
for failed prints, test pieces, and calibration prints.*

---

## Appendix B: Ender 3 Bed Fit Check

All parts must fit within 220 x 220 mm. Critical large parts:

| Part | Footprint on Bed | Fits? |
|------|-----------------|-------|
| AZ Base Half | 160 x 87 mm (half circle + flanges) | Yes |
| AZ Turntable Half | 140 x 77 mm | Yes |
| AZ Worm Wheel | 82 x 82 mm | Yes |
| EL Yoke Base | 210 x 60 mm | Yes (just fits at 210 mm, diagonally if needed) |
| EL Arm (any) | 25 x 30 mm (if printed upright) | Yes |
| Electronics Box | 108 x 98 mm | Yes |

The EL Yoke Base at 210 mm width is the tightest fit. If it does not fit on your
specific printer (some Ender 3 variants have slightly smaller usable area due to clips),
rotate it diagonally on the bed (210 mm diagonal of a 220 mm bed works with ~7 mm
margin per side).

---

*End of Part Dimension Specification Sheet*
