# Space Station v2: Unified Multi-Band Radio Telescope & Antenna Tracker

## Context

The existing `radio-telescope-plan.html` focuses on weather satellite reception + weather AI. After analyzing Eduard Mol's EUCARA 2023 presentation on detecting masers with a 1m backyard dish, we want to **expand the scope** to a unified modular system that covers everything from VHF satellites to Ku-band masers -- all with one tracker, one dish, and swappable feeds/LNBs.

**Key insight from Mol's work**: A 60-80cm dish + standard satellite TV LNB + RTL-SDR is enough to detect 12.2 GHz methanol masers and even attempt 22.2 GHz water masers. The same dish/tracker already needed for HRPT weather satellites can do radio astronomy with just a feed swap.

### Constraints
- **Budget**: Under 200 EUR total (excluding RPi 4 already owned)
- **Printer**: Ender 3 (220x220mm bed), PETG for outdoor parts
- **SDR**: RTL-SDR v3/v4 (already owned or ~25 EUR)
- **Mount**: Alt-Az (pan/tilt) -- simpler mechanics, software field rotation
- **Electronics**: Basic soldering setup, need to buy motors/drivers
- **Location**: Warsaw, Poland

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    UNIFIED TRACKER SYSTEM                     │
│                                                              │
│  ┌─────────────┐    ┌──────────────────────────────────┐     │
│  │  60-80cm     │    │  SWAPPABLE FEED/LNB MODULES     │     │
│  │  Offset Dish │◄───│                                  │     │
│  │  (recycled)  │    │  A) L-band helicone (1.7 GHz)   │     │
│  └──────┬───────┘    │     → HRPT sats, HI 21cm line   │     │
│         │            │                                  │     │
│  ┌──────┴───────┐    │  B) Ku PLL LNB (10.7-12.75 GHz) │     │
│  │  ALT-AZ      │    │     → 12.2 GHz methanol masers  │     │
│  │  TRACKER      │    │     → satellite TV signals      │     │
│  │  (fully 3D   │    │                                  │     │
│  │   printed)   │    │  C) Filtered LNA (1420 MHz)     │     │
│  └──────┬───────┘    │     → Hydrogen line mapping      │     │
│         │            │                                  │     │
│  ┌──────┴───────┐    │  D) Ka LNB (future, 18-26 GHz)  │     │
│  │  RPi 4       │    │     → 22.2 GHz water masers     │     │
│  │  + RTL-SDR   │    └──────────────────────────────────┘     │
│  │  + Python    │                                            │
│  │  + GNU Radio │    ┌──────────────────────────────────┐     │
│  └──────────────┘    │  SEPARATE FIXED ANTENNAS         │     │
│                      │  E) QFH/V-dipole (137 MHz)       │     │
│                      │     → Meteor-M LRPT (no tracker) │     │
│                      └──────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────┘
```

---

## Bill of Materials (BOM) -- Target <200 EUR

### Mechanical (Tracker -- Fully 3D Printed)
| Item | Est. Cost | Notes |
|------|-----------|-------|
| 2x NEMA 17 stepper motors (42mm, 40+ N.cm) | ~15 EUR | AliExpress, standard NEMA 17 |
| 2x TMC2209 stepper drivers (standalone) | ~8 EUR | Silent, 1/256 microstepping, wired to GPIO |
| 2x GT2 6mm timing belt (300mm loop) | ~3 EUR | AZ + EL drive belts |
| 2x GT2 16T pulley (bore 5mm, for motor) | ~2 EUR | Motor side, or 3D printed |
| 2x GT2 80T pulley (3D printed) | 0 EUR | Shaft side, 5:1 ratio |
| 2x GT2 idler bearing (for tensioning) | ~2 EUR | 608ZZ based, keeps belt tight |
| 6x 608ZZ bearings | ~3 EUR | Skateboard bearings, AZ turntable + EL shaft + idlers |
| 2x 6001ZZ bearings | ~3 EUR | Main shaft support (larger loads) |
| 1x 51107 thrust bearing (35mm) | ~3 EUR | AZ axis thrust load from dish weight |
| 2x 8mm steel rod (200mm) | ~2 EUR | EL pivot shafts (inside 3D printed frame) |
| 3D print filament (PETG, ~700g) | ~16 EUR | ALL structural parts, pulleys, housings |
| M3/M4/M5 bolt+nut assortment | ~5 EUR | For assembly, motor mount, clamps |
| 4x M5 threaded inserts (heat-set) | ~2 EUR | Strong mounting points in PETG |
| 2x 6mm diametral magnets (for AS5600) | ~1 EUR | Encoder magnets on shafts |
| **Subtotal** | **~55 EUR** | |

#### 3D Printed Parts Breakdown (all fit Ender 3 220x220mm bed)
| Part | Print Time | Infill | Notes |
|------|-----------|--------|-------|
| **AZ base ring** (2 halves, bolted) | 8h | 40% | Sits on thrust bearing, holds AZ shaft |
| **AZ 80T GT2 pulley** | 3h | 60% | On AZ shaft, belt-driven by motor |
| **AZ motor bracket + tensioner** | 2h | 40% | Mounts NEMA 17 + belt idler |
| **EL fork/yoke** (2 arms) | 6h each | 40% | U-shaped cradle, dish mounts between arms |
| **EL 80T GT2 pulley** | 3h | 60% | On EL pivot shaft, belt-driven by motor |
| **EL motor bracket + tensioner** | 2h | 40% | Mounts to yoke arm + belt idler |
| **Dish clamp arms** (2x) | 3h each | 30% | Adjustable for 60cm dish rim |
| **Feed arm + quick-swap bracket** | 3h | 30% | Holds LNB/feed at focal point, snap-fit |
| **Cable chain clips** (6x) | 0.5h | 30% | Route coax along frame |
| **Electronics box** | 3h | 25% | RPi + drivers, snap-fit lid, vent holes |
| **Tripod/pipe adapter plate** | 2h | 50% | Connects to tripod or pipe mount |
| **Total print time** | ~40h | | ~700g PETG |

#### Why Belt Drive (GT2)
- **Simple to print**: Only need pulleys, no complex gear tooth profiles
- **Efficient**: ~95% efficiency vs 40-60% for worm gears
- **Quiet**: GT2 belts are nearly silent
- **Forgiving**: Small alignment errors don't cause binding
- **Cheap**: GT2 belts cost ~1-2 EUR each
- **5:1 ratio** (16T motor → 80T shaft): At 1/16 microstepping → 0.0225 deg/step
- **Trade-off**: Not self-locking — motors must hold current to resist wind. TMC2209 reduces hold current automatically to save power. For a 60cm dish, wind load is manageable.

### RF Chain
| Item | Est. Cost | Notes |
|------|-----------|-------|
| 60-80cm offset satellite dish | 0 EUR | OLX.pl / recycled. Abundant in Poland |
| RTL-SDR v3 or v4 | 0/25 EUR | Already owned or buy one |
| Inverto Ku PLL LNB (IDLB-SINL40) | ~15 EUR | PLL stable, covers 12.2 GHz masers |
| Bias-T (for LNB 13/18V power) | ~8 EUR | Or DIY with inductor + capacitor |
| SPF5189Z wideband LNA module | ~5 EUR | For L-band (HI line, HRPT) |
| 1420 MHz bandpass filter (SAW) | ~10 EUR | For hydrogen line isolation |
| L-band helicone feed (3D printed) | ~3 EUR | Copper wire + 3D print, open source |
| F-to-SMA adapters + coax cables | ~10 EUR | For LNB connection |
| QFH antenna for 137 MHz (DIY) | ~8 EUR | Copper pipe + PVC, for Meteor-M |
| DiSEqC switch / 22kHz tone gen | ~5 EUR | For LNB band switching (low/high) |
| **Subtotal** | **~64-89 EUR** | |

### Electronics (Control)
| Item | Est. Cost | Notes |
|------|-----------|-------|
| RPi 4 (4GB) | 0 EUR | Already owned |
| 12V 5A power supply | ~8 EUR | For steppers + LNB |
| A4988/DRV8825 driver board (backup) | ~3 EUR | If TMC2209 UART is tricky |
| 2x AS5600 magnetic encoder + magnets | ~6 EUR | Position feedback, I2C |
| Limit switches (2x) | ~2 EUR | Homing reference |
| Weatherproof junction box | ~5 EUR | IP65, for outdoor electronics |
| Wire, connectors, heatshrink | ~5 EUR | Misc electronics |
| **Subtotal** | **~29 EUR** | |

### **GRAND TOTAL: ~148-173 EUR**

Fully 3D printed, belt-driven, compact design. Room left for a Ka-band LNB upgrade (~50-100 EUR) in the future for 22.2 GHz water masers.

---

## Phase Plan

### Phase 0: Software Foundation (Week 1-2)
**Build the control software stack before hardware arrives.**

Files to create:
- `tracker/controller.py` -- Stepper motor control via RPi GPIO + TMC2209
- `tracker/celestial.py` -- Coordinate transforms (RA/Dec ↔ Alt/Az), LSR velocity calc
- `tracker/scheduler.py` -- Observation scheduler (satellites, masers, HI targets)
- `tracker/config.yaml` -- Hardware config (steps/deg, gear ratios, location)
- `sdr/capture.py` -- RTL-SDR control wrapper (frequency, gain, sample rate)
- `sdr/spectral.py` -- FFT averaging, bandpass calibration, ON/OFF subtraction
- `sdr/maser.py` -- Maser-specific pipeline (Mol's method: long integration, LSR velocity)
- `web/app.py` -- FastAPI web UI for manual control + live waterfall display

Key libraries:
- `astropy` -- coordinate transforms, LSR velocity correction
- `skyfield` -- satellite tracking, ephemeris
- `pyrtlsdr` -- RTL-SDR control
- `numpy/scipy` -- FFT, signal processing
- `RPi.GPIO` or `pigpio` -- stepper pulse generation
- `FastAPI` + `websockets` -- real-time web UI

### Phase 1: VHF Weather Satellite Station (Week 2-3)
**First light -- no tracker needed.**

1. Build QFH antenna for 137 MHz (copper pipe + PVC)
2. Install SatDump on RPi 4
3. Receive first Meteor-M LRPT image
4. Set up automated capture (cron + SatDump CLI)
5. Start weather data collection pipeline (IMGW API + Open-Meteo)

### Phase 2: Mechanical Tracker Build (Week 3-6)
**The core engineering challenge -- fully 3D printed.**

#### Design Specs
- **Drive type**: GT2 belt, 16T motor pulley → 80T shaft pulley
- **AZ ratio**: 5:1 belt drive
- **EL ratio**: 5:1 belt drive
- **Resolution**: At 1/16 microstepping → 0.0225 deg/step (81 arcsec)
- **Dish beamwidth**: ~3 deg at 12 GHz, ~25 deg at 1.4 GHz → resolution is plenty
- **Load**: 60cm offset dish = ~3-4 kg → NEMA 17 with 5:1 belt handles easily
- **Position hold**: TMC2209 holding current keeps dish in place, auto-reduced when idle

#### Assembly (all parts fit 220x220mm bed, PETG)
```
                    SIDE VIEW

    Feed arm ─────── ⟍ ── LNB/Feed (snap-fit)
                    ╱
    ┌──────────────╱──────────────┐
    │          DISH (60-80cm)      │
    │      (clamped at rim)        │
    └──────────┬───────────────────┘
               │
    ┌──────────┴──────────┐
    │   EL YOKE (fork)    │ ◄── EL belt drive
    │  ┌──┐        ┌──┐   │     NEMA17 + 16T→80T GT2
    │  │  │  DISH  │  │   │     8mm steel pivot pins
    │  │  │ CLAMP  │  │   │     + 6001ZZ bearings
    │  └──┘        └──┘   │
    └──────────┬──────────┘
               │
    ┌──────────┴──────────┐
    │    AZ TURNTABLE      │ ◄── AZ belt drive
    │  608ZZ + 51107 thrust│     NEMA17 + 16T→80T GT2
    └──────────┬──────────┘
               │
    ┌──────────┴──────────┐
    │   BASE PLATE         │ ◄── Bolts to tripod/pipe
    │  (tripod adapter)    │
    └─────────────────────┘
```

#### Key Design Decisions
1. **Belt drive over worm gears**: Simpler to print, higher efficiency, quieter, more forgiving
2. **Split parts (bolted halves)**: Any part >200mm is split in half, bolted with M4
3. **Heat-set inserts**: At all critical bolting points for reusable threads in PETG
4. **Steel rods for shafts**: Only non-printed metal structural elements (8mm rods)
5. **Snap-fit feed bracket**: Tool-free LNB/feed swap in <30 seconds
6. **Cable routing**: Printed cable chain clips along yoke arm to feed point

#### Control Software (Python on RPi, no separate microcontroller)
- Direct GPIO stepper pulse generation via `pigpio` (hardware-timed DMA, jitter-free)
- AS5600 encoder feedback via I2C (closed-loop position correction)
- EasyComm2 protocol TCP server for Gpredict/SatDump compatibility
- Hamlib `rotctld` compatible interface
- PID loop for tracking: encoder reads actual position, corrects drift
- Homing routine: limit switches + encoder zero reference
- **Park/stow mode**: Auto-park dish face-down in high wind (future: anemometer input)

### Phase 3: L-band Reception (Week 6-8)
**HRPT weather satellites + Hydrogen 21cm line.**

3A: HRPT Weather Satellites
- 3D print helicone feed for 1.7 GHz
- Install SPF5189Z LNA at feed point
- Configure SatDump autotrack with rotator interface
- First tracked HRPT capture of Meteor-M or Metop

3B: Hydrogen 21cm Line
- Add 1420 MHz SAW bandpass filter after LNA
- Write spectral integration script (ON/OFF source method)
- Map galactic plane drift scan: measure HI brightness vs galactic longitude
- Calculate galactic rotation curve

### Phase 4: Ku-band Maser Detection (Week 8-12)
**Following Eduard Mol's approach for 12.2 GHz methanol masers.**

Setup:
- Mount Inverto Ku PLL LNB at dish focal point (quick-swap bracket)
- LNB downconverts 12.2 GHz → ~1.05 GHz IF (low band, horizontal pol)
- Bias-T provides 18V to LNB via coax
- 22kHz tone generator for band switching if needed
- RTL-SDR receives IF signal

Observation method (from Mol):
1. Point dish at target (W3(OH), G188.94 etc.) using celestial coordinates
2. Record SDR IQ data for long integration (30-60 min)
3. FFT with high resolution (~1 kHz bins for velocity resolution)
4. Average thousands of spectra to reduce noise floor
5. Subtract bandpass shape (OFF-source observation)
6. Convert frequency offset to LSR velocity (correct for Earth motion)

Software pipeline:
- `sdr/maser.py`: IQ capture → FFT → spectral averaging → bandpass cal → LSR velocity
- Integration with MaserDB (maserdb.net) for target catalog
- Automated observation scheduling for maser sources above horizon

First targets (brightest, from Mol's results and MaserDB):
- W3(OH) -- strong 12.2 GHz methanol maser
- Orion KL -- if above horizon from Warsaw
- W49N -- strongest known water maser (future Ka-band target)

### Phase 5: Web Dashboard & Data Pipeline (Week 10-14)
- Live waterfall/spectrum display via WebSocket
- Observation log with spectra plots
- Satellite image gallery (auto-organized)
- Target catalog with rise/set times
- Remote control interface (point dish from phone)

### Phase 6: Future Upgrades (Post v1)
- **Ka-band LNB** (~50-100 EUR): 22.2 GHz water maser detection
- **Airspy Mini** (~100 EUR): Better dynamic range, 6 MHz BW for HRPT
- **Second RTL-SDR**: Simultaneous satellite reception + monitoring
- **Weather AI**: ConvLSTM nowcasting from satellite imagery (from existing plan)
- **SatNOGS integration**: Join the global ground station network
- **OH maser at 1.6 GHz**: Needs larger dish but same L-band chain

---

## Repository Structure

```
space-station/
├── tracker/                    # Antenna tracker system
│   ├── controller.py           # Stepper motor control (RPi GPIO + pigpio)
│   ├── celestial.py            # Coord transforms, LSR velocity, sidereal time
│   ├── scheduler.py            # Multi-mode observation scheduler
│   ├── rotator_server.py       # EasyComm2 / rotctld compatible TCP server
│   ├── encoder.py              # AS5600 magnetic encoder I2C driver
│   ├── config.yaml             # Site location, gear ratios, motor params
│   └── calibrate.py            # Sun/satellite alignment calibration routine
├── sdr/                        # SDR capture and processing
│   ├── capture.py              # RTL-SDR IQ recording wrapper
│   ├── spectral.py             # FFT averaging, bandpass cal, noise reduction
│   ├── maser.py                # Maser observation pipeline (Mol method)
│   ├── hydrogen.py             # HI 21cm line specific processing
│   └── lnb.py                  # LNB control (bias-T voltage, 22kHz tone, DiSEqC)
├── web/                        # Control dashboard
│   ├── app.py                  # FastAPI backend + WebSocket
│   ├── templates/              # HTML templates
│   └── static/                 # JS waterfall display, spectrum plots
├── weather/                    # Weather satellite pipeline
│   ├── satdump_hook.py         # SatDump integration, auto-processing
│   ├── collectors/             # IMGW, Open-Meteo data collectors
│   └── pipeline.py             # Image post-processing
├── hardware/                   # CAD and build files
│   ├── tracker_cad/            # FreeCAD/Fusion 360 source files
│   ├── stl/                    # Ready-to-print STL files
│   ├── feed_designs/           # Helicone, horn antenna designs
│   └── wiring/                 # KiCad schematics, wiring diagrams
├── targets/                    # Observation target catalogs
│   ├── masers.csv              # MaserDB brightest sources for our dish size
│   ├── hydrogen_survey.csv     # Galactic plane survey grid points
│   └── satellites.tle          # TLE data (auto-updated)
├── data/                       # Observation data (gitignored)
│   ├── spectra/
│   ├── images/
│   └── logs/
├── scripts/                    # Utility scripts
│   ├── install.sh              # System setup (dependencies, udev rules)
│   └── lnb_test.py             # Quick LNB + SDR test script
├── docs/
│   ├── build_guide.md
│   ├── frequency_bands.md      # Detailed RF chain for each band
│   └── observation_guide.md    # How to observe masers, HI, sats
├── requirements.txt
├── docker-compose.yml          # Optional containerized deployment
└── README.md
```

---

## Verification Plan

### Tracker Mechanics
- [ ] Both axes rotate smoothly through full range (0-360 az, 0-90 el)
- [ ] Encoder position matches commanded position within 0.1 deg
- [ ] Homing routine repeatable to < 0.05 deg
- [ ] Dish tracks a satellite pass correctly (verify with SatDump signal strength)

### L-band (1.4-1.7 GHz)
- [ ] Receive Meteor-M HRPT with tracked dish
- [ ] Detect hydrogen 21cm line from galactic plane (ON/OFF method)
- [ ] HI spectrum shows velocity structure matching published data

### Ku-band (12.2 GHz)
- [ ] LNB bias-T delivers correct voltage (verify with multimeter)
- [ ] Receive known satellite TV transponder as signal test
- [ ] Detect W3(OH) 12.2 GHz methanol maser (long integration, ON-OFF subtraction)
- [ ] LSR velocity of detected maser matches MaserDB values

### Web Interface
- [ ] Live waterfall display updates in real-time
- [ ] Can command dish to coordinates from browser
- [ ] Observation scheduler correctly predicts source rise/set times

---

## Implementation Priority (What We Code First)

1. **`tracker/controller.py`** + **`tracker/config.yaml`** -- Get motors spinning
2. **`tracker/celestial.py`** -- Coordinate math (essential for pointing)
3. **`tracker/rotator_server.py`** -- EasyComm2 so Gpredict/SatDump can control it
4. **`sdr/capture.py`** + **`sdr/spectral.py`** -- Basic SDR capture and FFT
5. **`sdr/lnb.py`** -- LNB power control via bias-T
6. **`sdr/maser.py`** -- Maser pipeline (the exciting science part)
7. **`web/app.py`** -- Control dashboard
8. **`tracker/scheduler.py`** -- Multi-target automated scheduling
