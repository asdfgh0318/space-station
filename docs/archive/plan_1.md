# Step 1: Bench Motor Control via Waveshare Stepper Motor HAT (B)

## Context

Starting fresh. The user has a Raspberry Pi 4B with a Waveshare Stepper Motor HAT (B) and 2x NEMA 17 steppers on the bench. Old Phase 0 code (written for TMC2209 standalone drivers) is being deleted — we start over with the Waveshare HAT approach.

- `tech_stack.md` is the north star
- Belt drive: 1:1, 20T GT2 pulleys on both ends
- Microstepping: DIP switches only (no software control)
- Resolution at 1/16: 200 × 16 × 1 = 3200 microsteps/rev → 0.1125°/step
- Credentials in `tech_stack.md` — leave as-is

---

## Tasks

### 0. Clean repo — delete old code & docs
**Delete these directories entirely:**
- `tracker/` — old TMC2209 controller code
- `sdr/` — SDR capture/processing
- `web/` — old FastAPI dashboard
- `weather/` — empty collectors
- `targets/` — maser catalog (will recreate if needed)
- `scripts/` — old install script
- `hardware/` — outdated CAD (worm gear), specs, wiring
- `docs/` — old project plan & research
- `data/` — empty data dirs

**Delete these files:**
- `requirements.txt` — will recreate for new stack

**Keep:**
- All `.stl`, `.gcode`, `.STEP` files
- `.pb` files (raw data)
- `tech_stack.md`, `first_prompt.md`
- `README.md`, `banner.svg`, `.gitignore`
- `aplikacja_wok_rezydencja.md`
- PDFs (`Eucara2023...`, `radio-telescope-plan.pdf`)
- `radio-telescope-plan-images/`
- `Windows11InstallationAssistant.exe`

### 1. Create `tracker/config.yaml` — HAT pin mapping + belt drive
- Waveshare HAT (B) GPIO pins (STEP/DIR/ENABLE only, no mode pins):
  - Motor 1 (AZ): STEP=19, DIR=13, ENABLE=12
  - Motor 2 (EL): STEP=18, DIR=24, ENABLE=4
- Belt drive 1:1, 20T GT2 pulleys, 200 steps/rev, 1/16 microstepping
- `home_switch_enabled: false` for bench mode
- Site: Warsaw coordinates
- Pin mapping to be verified against Waveshare wiki during implementation

### 2. Create `tracker/controller.py` — motor controller for Waveshare HAT (B)
Fresh, lean motor controller (~300 LOC) built for the HAT:
- `StepperAxis` class: step/dir/enable GPIO control via pigpio (RPi.GPIO fallback)
- `AntennaTracker` class: two-axis control, position tracking
- Trapezoidal acceleration profiles
- Bench mode: skip homing when no limit switches
- CLI: `--status`, `--goto az el`, `--home`, `--park`, `--steps motor count`

### 3. Create `scripts/motor_test.py` — bench test CLI
Standalone test tool (~200 LOC) using `click` + `rich`:
- `spin --motor 1 --steps 200 --speed 100 --dir cw`
- `sweep --motor 1` — speed ramp test
- `test-all` — smoke test both motors
- `interactive` — arrow keys control in terminal
- `--dry-run` for testing without GPIO
- Loads pins from `tracker/config.yaml`

### 4. Create `web/app.py` — GUI control panel
Fresh web dashboard (~400 LOC) with FastAPI:
- **Position display**: current az/el in degrees + step count
- **Keyboard control**: Arrow keys = jog, Shift+Arrow = fast jog, Space = stop
- **Jog pad**: visual arrow buttons + step size selector (0.01°–45°)
- **Motor enable/disable** toggle
- **Endpoint wizard**: capture current position as axis limit, save to config
- **Bench mode indicator**: shows when homing switches are disconnected
- WebSocket live position updates

### 5. Create `scripts/bootstrap_rpi.sh` — RPi setup script
Bootstrap script (~100 LOC) for fresh RPi OS:
- Install system packages (pigpio, i2c-tools, rtl-sdr, etc.)
- Enable I2C, start pigpiod
- Clone repo / git pull
- Python venv + requirements
- Convenience aliases: `ss-update`, `ss-start`, `ss-test`
- Smoke test (pigpio connection)

### 6. Create `requirements.txt` — fresh dependencies
Only what's needed for the HAT motor control + web UI:
- pigpio, RPi.GPIO (motor control)
- fastapi, uvicorn, websockets (web UI)
- pyyaml (config)
- click, rich (CLI tools)
- numpy (if needed for calculations)

---

## Files Summary

| File | Action | Scope |
|------|--------|-------|
| `tracker/`, `sdr/`, `web/`, etc. | Delete | Clean old code |
| `tracker/config.yaml` | New | HAT config |
| `tracker/controller.py` | New | ~300 LOC |
| `scripts/motor_test.py` | New | ~200 LOC |
| `web/app.py` | New | ~400 LOC |
| `scripts/bootstrap_rpi.sh` | New | ~100 LOC |
| `requirements.txt` | New | Fresh deps |

---

## Execution Method (from first_prompt.md)

1. **This plan** → user approves
2. **Create GitHub issues** — one per task (0–6)
3. **Execute in worktree** — launch subagents in isolated worktrees to implement each task
4. **User tests** on the bench (RPi + HAT + motors)
5. **Commit only after testing passes**

---

## Verification

1. **On dev machine**: `python scripts/motor_test.py test-all --dry-run` — no errors
2. **On RPi**: `bash scripts/bootstrap_rpi.sh` — all deps installed
3. **On RPi**: `python scripts/motor_test.py test-all` — both motors spin
4. **On RPi**: `python -m web.app --port 8080` → open browser → arrow keys move motors
5. **On RPi**: endpoint wizard saves limits to config.yaml
