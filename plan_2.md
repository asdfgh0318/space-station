# plan_2 — Rebuild from scratch with inmarsat seams

## Context

The user is re-running the workflow from `first_prompt.md`: generate a plan → user
approves → GitHub issues → subagents in worktrees → user tests → commit. The previous
plan (`plan_1.md`) was executed at commit `bd0c259` and produced the current
`tracker/` + `web/` + `scripts/` + `requirements.txt`.

The user now wants a clean rebuild that bakes in **architectural seams for the
upcoming `inmarsat-sniffer` integration** (analyzed in `merge_plan.html`), without
actually pulling in the GPL-3.0 C binary yet. After this rebuild lands, the inmarsat
merge becomes a small, additive PR rather than a refactor.

Canonical sources of truth:
- `tech_stack.md` — Waveshare Stepper Motor HAT (B), NEMA 17, RTL-SDR, GUI control
- `tracker/config.yaml` (current) — 1:1 GT2 belt, 32× microstepping, Warsaw site
- `merge_plan.html` — target architecture for inmarsat sidecar

(Project memory is stale on the drive choice — it still says TMC2209 + 5:1. Will
update memory after the rebuild lands.)

---

## Scope

**Wipe:**
- `tracker/` (controller.py, config.yaml, __init__.py)
- `web/` (app.py, __init__.py)
- `scripts/` (bootstrap_rpi.sh, motor_test.py, spin_test.py)
- `requirements.txt`

**Move to `docs/archive/`:**
- `plan_1.md`
- `merge_plan.html`

**Keep untouched:**
- All `.stl`, `.STEP`, `.gcode`, `.pb`, `.pdf`, `.svg`, `.exe`
- `tech_stack.md`, `first_prompt.md`, `aplikacja_wok_rezydencja.md`, `README.md`
- `radio-telescope-plan.html`, `radio-telescope-plan.pdf`, `radio-telescope-plan-images/`
- `banner.svg`, `.gitignore`, `.git/`

**No code from `alphafox02/inmarsat-sniffer` enters this repo in this plan.**

---

## Target tree after rebuild

```
space-station/
├── tracker/
│   ├── __init__.py
│   ├── config.yaml          # HAT + bands + targets + sniffer seams
│   ├── controller.py        # lgpio motor control, ~300 LOC
│   ├── targets.py           # geostationary AZ/EL math, presets — STUB
│   └── sniffer.py           # subprocess supervisor placeholder — STUB
├── web/
│   ├── __init__.py
│   └── app.py               # FastAPI, jog UI, scaffolded "Inmarsat" tab — placeholder
├── scripts/
│   ├── bootstrap_rpi.sh     # OS bring-up + inmarsat build deps (no clone yet)
│   └── motor_test.py        # CLI bench tester
├── vendor/
│   └── .gitkeep             # reserved slot for inmarsat-sniffer submodule (later)
├── docs/
│   └── archive/
│       ├── plan_1.md
│       └── merge_plan.html
├── plan_2.md                # copy of this plan, committed at root
├── requirements.txt
├── tech_stack.md            (kept)
├── first_prompt.md          (kept)
├── README.md                (kept)
└── [all hardware assets kept]
```

---

## Tasks (one GitHub issue per task)

### Task 0 — Clean repo, archive old plans
- `git rm -r tracker/ web/ scripts/ requirements.txt`
- `mkdir -p docs/archive vendor`
- `git mv plan_1.md docs/archive/plan_1.md`
- `git mv merge_plan.html docs/archive/merge_plan.html`
- `touch vendor/.gitkeep`
- Verify with `git status` that only the targeted files moved/deleted
- **No commit yet** — gate on user testing per `first_prompt.md`

### Task 1 — `tracker/config.yaml` (with inmarsat seams)
Layout based on the current config but reorganized so future band/target/sniffer
config lives in well-named blocks instead of dormant `lnb:` and `sdr:` stubs:

```yaml
site:        # Warsaw 52.2297, 21.0122, 100m elevation
tracker:     # alt-az, driver: waveshare_hat_b, az/el axes (HAT pins, 1:1 belt, 32× µstep)
bands:                          # NEW — band profiles
  l_band:                       # 1525–1559 MHz Inmarsat
    enabled: false
    sample_rate: 2400000
    gain: 40.0
    notes: "Direct RTL-SDR, no LO/LNB"
  ku_band:                      # 10–12 GHz dish + LNB (future)
    enabled: false
    lnb:
      model: "Inverto IDLB-SINL40"
      lo_low: 9750000000
      lo_high: 10600000000
      switch_freq: 11700000000
      gpio:
        power_pin: 23
        voltage_select_pin: 25
        tone_pin: 26
targets:                        # NEW — geostationary presets, computed AZ/EL
  alphasat_25e:
    name: "Inmarsat 4F2 / Alphasat (25°E)"
    sat_longitude: 25.0
    band: "l_band"
  inmarsat_4f3_98w:
    name: "Inmarsat 4F3 (98°W)"
    sat_longitude: -98.0
    band: "l_band"
sniffer:                        # NEW — sidecar config, dormant until merge
  enabled: false
  binary_path: "vendor/inmarsat-sniffer/build/inmarsat-sniffer"
  feed_udp_port: 5000
  skip_c_channel: true          # Pi 4 default per upstream README
  web_port: 8888                # sniffer's own UI (iframed in our dashboard)
```

### Task 2 — `tracker/controller.py`
Same shape and quality as the current implementation (lgpio backend, trapezoidal
accel, click CLI, sim mode), built fresh:
- `StepperAxis` — step/dir/enable via lgpio
- `AntennaTracker` — two-axis orchestration, position state, jog/goto/home/park
- CLI: `status`, `goto az el`, `home`, `park`, `step --motor az/el --count N --dir cw/ccw`
- Sim fallback when lgpio unavailable
- ~300–400 LOC

### Task 3 — `tracker/targets.py` (STUB module)
Pure math, no I/O, no SDR, no submodule yet:
- `geostationary_azel(site_lat, site_lon, sat_lon) -> (az_deg, el_deg)`
  Standard formula: spherical geometry from observer to GEO arc.
- `load_targets(config) -> dict[name, Target]`
- `Target.dataclass(name, sat_longitude, band, az, el)`
- CLI smoke test: `python -m tracker.targets list` prints AZ/EL for each preset
  from current site coords (Warsaw → Alphasat ≈ 165°/27°).
- ~80 LOC. No subprocess, no SDR.

### Task 4 — `tracker/sniffer.py` (STUB module)
Placeholder for the future subprocess supervisor:
- `class SnifferSidecar` with `start()`, `stop()`, `status()`, `is_running()`
  All methods raise `NotImplementedError("inmarsat-sniffer not vendored yet — see docs/archive/merge_plan.html")` for now,
  so any caller sees a clear error.
- `SnifferStatus` dataclass (`pid`, `running`, `last_decode_at`, `decode_count`)
  defined now so the API is stable.
- ~40 LOC. Importable, doesn't crash, doesn't pretend to work.

### Task 5 — `scripts/motor_test.py`
Same scope as current implementation:
- `spin --motor 1/2 --steps N --speed S --dir cw/ccw`
- `sweep --motor N` — speed ramp
- `test-all` — both motors smoke test
- `interactive` — terminal arrow keys
- `--dry-run` flag, click + rich, reads `tracker/config.yaml`

### Task 6 — `scripts/bootstrap_rpi.sh`
Same structure as current Trixie bootstrap, plus inmarsat build deps preinstalled
so the future merge is a one-command `cmake && make`:

```bash
# Existing (motor + Python venv)
sudo apt install -y python3-lgpio python3-pip python3-venv pigpio-tools \
                    librtlsdr-dev rtl-sdr i2c-tools
# NEW — for future inmarsat-sniffer build
sudo apt install -y cmake build-essential pkg-config \
                    libacars2-dev libzmq3-dev libmosquitto-dev
```
- RTL-SDR udev rules + DVB blacklist (kept)
- I2C / USB-boot enablement (kept)
- Aliases: `ss-update`, `ss-start`, `ss-test`, `ss-debug` (kept)
- Smoke tests: lgpio connect, Python deps import, RTL-SDR detection
- Adds a TODO comment near the inmarsat deps pointing at `merge_plan.html`

### Task 7 — `web/app.py`
Same dashboard scope as today, plus a scaffolded "Inmarsat" tab:
- All current motor-control endpoints (`/api/jog`, `/api/goto`, `/api/home`,
  `/api/park`, `/api/motors/{enable,disable}`, `/api/stop`, `/api/set-limit`)
- `/ws` live position WebSocket
- Retro-terminal styling
- **NEW**: tab switcher in UI between "Tracker" (current) and "Inmarsat"
- **NEW**: `/api/sniffer/status` returns `{enabled: false, reason: "stub — see merge_plan"}`
- **NEW**: Inmarsat tab shows a "not configured yet — pending hardware/integration"
  placeholder card linking to `docs/archive/merge_plan.html`
- ~500–600 LOC

### Task 8 — `requirements.txt`
Same minimal set as today — no new deps for the sniffer stubs:
```
lgpio
fastapi
uvicorn[standard]
websockets
pyyaml
click
rich
numpy
```

### Task 9 — Save plan + write README hook
- Copy this plan file to repo root as `plan_2.md`
- Add a one-line section in `README.md` linking to `plan_2.md` and the
  archived `merge_plan.html` (README is currently essentially empty)

---

## Execution method (per `first_prompt.md`)

1. ☐ User approves this plan (via `ExitPlanMode`)
2. ☐ Create one GitHub issue per task (Task 0–9) with `gh issue create`
3. ☐ Spawn parallel subagents in **isolated git worktrees** — Tasks 1–8 are
   independent enough for parallel execution; Task 0 must run first; Task 9 last
4. ☐ User runs verification on RPi + bench
5. ☐ Only after user confirms tests pass, merge worktrees and commit

**Do not commit anything until the user has tested on hardware.**

---

## Verification

Run on the dev machine first:
- `python -c "from tracker.controller import AntennaTracker; AntennaTracker.from_config('tracker/config.yaml')"` — imports clean in sim mode
- `python -m tracker.targets list` — prints AZ/EL for Alphasat 25°E from Warsaw
  (expected: AZ ≈ 165°, EL ≈ 27°). Acts as numerical regression on the math.
- `python -c "from tracker.sniffer import SnifferSidecar; SnifferSidecar().status()"` — raises `NotImplementedError` cleanly
- `python scripts/motor_test.py test-all --dry-run` — no errors, both motors enumerated
- `uvicorn web.app:app --port 8080` → open browser → "Tracker" and "Inmarsat" tabs
  both render; Inmarsat tab shows the placeholder card
- `bash -n scripts/bootstrap_rpi.sh` — script parses, no syntax errors

Run on RPi (user does this on the bench):
- `bash scripts/bootstrap_rpi.sh` — completes without errors, all deps installed
- `python scripts/motor_test.py test-all` — both motors spin
- `python -m web.app --port 8080` → browser → arrow keys move motors
- Endpoint wizard saves limits to `config.yaml`

After the user signs off:
- Commit Task 0–9 as a single atomic rebuild commit (or one commit per task —
  user's call at commit time)
- Update memory: drive choice is HAT + 1:1, not TMC2209 + 5:1
- Push to `origin/main`

---

## What this plan does NOT do (deferred)

These are explicitly out-of-scope for this rebuild and belong to the inmarsat merge PR:
- Cloning `alphafox02/inmarsat-sniffer` as a submodule
- Building the C binary
- Writing the actual subprocess supervision logic
- UDP/MQTT decode listener
- Live decode WebSocket channel
- Iframe of the sniffer's :8888 UI
- L-band feed hardware acquisition decision
- Project root LICENSE selection (still no LICENSE file — to be settled before
  pulling in GPL-3.0 code, **before** the merge PR, not in this rebuild)

The seams in this plan make those changes additive, not invasive.
