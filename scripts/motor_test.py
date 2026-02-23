#!/usr/bin/env python3
"""
motor_test.py — Bench test CLI for Waveshare Stepper Motor HAT (B)
Two NEMA 17 motors: Motor 1 = Azimuth, Motor 2 = Elevation

Usage:
    python scripts/motor_test.py --help
    python scripts/motor_test.py --dry-run test-all
    python scripts/motor_test.py spin --motor 1 --steps 200 --speed 100 --dir cw
    python scripts/motor_test.py sweep --motor 1 --min-speed 50 --max-speed 500
    python scripts/motor_test.py interactive
"""

import os
import sys
import time
import signal
import curses
import pathlib

import click
import yaml
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.panel import Panel
from rich import box

# ---------------------------------------------------------------------------
# GPIO bootstrap — graceful fallback when not on RPi
# ---------------------------------------------------------------------------

DRY_RUN = False  # overridden by --dry-run flag before any command runs

HAS_LGPIO = False
HAS_GPIO = False
_chip = None

try:
    import lgpio
    HAS_LGPIO = True
except ImportError:
    try:
        import RPi.GPIO as GPIO
        HAS_GPIO = True
    except ImportError:
        pass

console = Console()

# ---------------------------------------------------------------------------
# Default pin assignments (fallback if config not found)
# ---------------------------------------------------------------------------

DEFAULTS = {
    1: {"step": 19, "dir": 13, "enable": 12, "name": "Azimuth"},
    2: {"step": 18, "dir": 24, "enable": 4,  "name": "Elevation"},
}

# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

def load_config() -> dict:
    """Load tracker/config.yaml relative to this script's project root."""
    script_dir = pathlib.Path(__file__).resolve().parent
    config_path = script_dir.parent / "tracker" / "config.yaml"
    if not config_path.exists():
        console.print(
            f"[yellow]Config not found at {config_path} — using hardcoded pin defaults[/yellow]"
        )
        return {}
    try:
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    except Exception as exc:
        console.print(f"[yellow]Failed to parse config: {exc} — using defaults[/yellow]")
        return {}


def build_motor_map(cfg: dict) -> dict:
    """
    Return motor_map[motor_id] = {step, dir, enable, name}
    Uses config values when available, falls back to DEFAULTS.
    """
    motors = dict(DEFAULTS)  # start from defaults

    tracker = cfg.get("tracker", {})
    az = tracker.get("azimuth", {})
    el = tracker.get("elevation", {})

    if az.get("step_pin"):
        motors[1] = {
            "step":   az["step_pin"],
            "dir":    az["dir_pin"],
            "enable": az["enable_pin"],
            "name":   "Azimuth",
        }
    if el.get("step_pin"):
        motors[2] = {
            "step":   el["step_pin"],
            "dir":    el["dir_pin"],
            "enable": el["enable_pin"],
            "name":   "Elevation",
        }

    return motors

# ---------------------------------------------------------------------------
# GPIO helpers
# ---------------------------------------------------------------------------

def _hw_available():
    return not DRY_RUN and (HAS_LGPIO or HAS_GPIO)


def setup_gpio(motors: dict):
    global _chip
    if not _hw_available():
        return
    if HAS_LGPIO:
        _chip = lgpio.gpiochip_open(0)
        for m in motors.values():
            lgpio.gpio_claim_output(_chip, m["step"], 0)
            lgpio.gpio_claim_output(_chip, m["dir"], 0)
            lgpio.gpio_claim_output(_chip, m["enable"], 1)  # HIGH = disabled
    else:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        for m in motors.values():
            GPIO.setup(m["step"],   GPIO.OUT, initial=GPIO.LOW)
            GPIO.setup(m["dir"],    GPIO.OUT, initial=GPIO.LOW)
            GPIO.setup(m["enable"], GPIO.OUT, initial=GPIO.HIGH)


def cleanup_gpio():
    global _chip
    if not _hw_available():
        return
    try:
        if HAS_LGPIO and _chip is not None:
            lgpio.gpiochip_close(_chip)
            _chip = None
        elif HAS_GPIO:
            GPIO.cleanup()
    except Exception:
        pass


def enable_motor(motor: dict, enabled: bool = True):
    if not _hw_available():
        return
    val = 0 if enabled else 1  # Active LOW
    if HAS_LGPIO:
        lgpio.gpio_write(_chip, motor["enable"], val)
    else:
        GPIO.output(motor["enable"], GPIO.LOW if enabled else GPIO.HIGH)


def set_direction(motor: dict, clockwise: bool):
    if not _hw_available():
        return
    val = 1 if clockwise else 0
    if HAS_LGPIO:
        lgpio.gpio_write(_chip, motor["dir"], val)
    else:
        GPIO.output(motor["dir"], GPIO.HIGH if clockwise else GPIO.LOW)


def pulse_step(step_pin: int, delay: float):
    """Send one step pulse then wait for the inter-step delay."""
    if not _hw_available():
        time.sleep(delay)
        return
    if HAS_LGPIO:
        lgpio.gpio_write(_chip, step_pin, 1)
        time.sleep(0.000002)
        lgpio.gpio_write(_chip, step_pin, 0)
        time.sleep(delay)
    else:
        GPIO.output(step_pin, GPIO.HIGH)
        time.sleep(0.000002)
        GPIO.output(step_pin, GPIO.LOW)
        time.sleep(delay)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def print_pin_table(motors: dict):
    """Print a Rich table of pin assignments."""
    table = Table(
        title="GPIO Pin Assignments (BCM)",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Motor", style="bold")
    table.add_column("Axis",  style="cyan")
    table.add_column("STEP",  justify="right")
    table.add_column("DIR",   justify="right")
    table.add_column("ENABLE",justify="right")

    for mid, m in motors.items():
        table.add_row(
            str(mid),
            m["name"],
            str(m["step"]),
            str(m["dir"]),
            str(m["enable"]),
        )
    console.print(table)


def resolve_motor(motor_id: int, motors: dict) -> dict:
    if motor_id not in motors:
        console.print(f"[red]Unknown motor ID {motor_id}. Valid: {list(motors.keys())}[/red]")
        sys.exit(1)
    return motors[motor_id]


def do_spin(motor: dict, steps: int, speed: float, clockwise: bool,
            progress=None, task_id=None) -> int:
    """
    Spin motor for `steps` pulses at `speed` steps/sec.
    Returns number of steps actually executed.
    """
    delay = 1.0 / speed
    enable_motor(motor, True)
    set_direction(motor, clockwise)

    executed = 0
    try:
        for _ in range(steps):
            pulse_step(motor["step"], delay)
            executed += 1
            if progress is not None and task_id is not None:
                progress.update(task_id, advance=1)
    finally:
        enable_motor(motor, False)

    return executed

# ---------------------------------------------------------------------------
# Click group with --dry-run global option
# ---------------------------------------------------------------------------

@click.group()
@click.option("--dry-run", is_flag=True, default=False,
              help="Print actions without touching GPIO.")
@click.pass_context
def cli(ctx, dry_run):
    """Bench test CLI for Waveshare Stepper Motor HAT (B)."""
    global DRY_RUN
    DRY_RUN = dry_run
    ctx.ensure_object(dict)

    cfg = load_config()
    ctx.obj["motors"] = build_motor_map(cfg)

    if DRY_RUN:
        console.print(Panel("[yellow]DRY-RUN mode — no GPIO will be touched[/yellow]",
                            expand=False))
    elif not HAS_GPIO and not HAS_LGPIO:
        console.print(Panel(
            "[yellow]No GPIO library available — running in implicit dry-run mode[/yellow]",
            expand=False,
        ))

# ---------------------------------------------------------------------------
# spin command
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--motor",  "-m", type=int, default=1, show_default=True,
              help="Motor number (1=AZ, 2=EL).")
@click.option("--steps",  "-n", type=int, default=200, show_default=True,
              help="Number of steps to run.")
@click.option("--speed",  "-s", type=float, default=100.0, show_default=True,
              help="Speed in steps/sec.")
@click.option("--dir",    "-d", "direction",
              type=click.Choice(["cw", "ccw"], case_sensitive=False),
              default="cw", show_default=True,
              help="Rotation direction.")
@click.pass_context
def spin(ctx, motor, steps, speed, direction):
    """Spin a motor N steps at a given speed."""
    motors = ctx.obj["motors"]
    m = resolve_motor(motor, motors)
    clockwise = direction.lower() == "cw"

    console.print(f"\n[bold]Spinning Motor {motor} ({m['name']})[/bold]")
    print_pin_table({motor: m})
    console.print(
        f"  Steps: [cyan]{steps}[/cyan]   "
        f"Speed: [cyan]{speed}[/cyan] steps/s   "
        f"Direction: [cyan]{direction.upper()}[/cyan]"
    )

    setup_gpio(motors)

    def _cleanup(sig=None, frame=None):
        cleanup_gpio()
        console.print("\n[yellow]Interrupted — GPIO cleaned up.[/yellow]")
        sys.exit(0)

    signal.signal(signal.SIGINT, _cleanup)

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[cyan]{task.completed}/{task.total}[/cyan] steps"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"Motor {motor} {direction.upper()}", total=steps
            )
            executed = do_spin(m, steps, speed, clockwise, progress, task)

        console.print(f"[green]Done. Executed {executed}/{steps} steps.[/green]\n")
    finally:
        cleanup_gpio()

# ---------------------------------------------------------------------------
# sweep command
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--motor",     "-m", type=int,   default=1,   show_default=True)
@click.option("--min-speed", type=float, default=50.0,  show_default=True,
              help="Minimum speed (steps/sec).")
@click.option("--max-speed", type=float, default=500.0, show_default=True,
              help="Maximum speed (steps/sec).")
@click.option("--steps-per-level", type=int, default=200, show_default=True,
              help="Steps to run at each speed level.")
@click.option("--levels",    type=int, default=10,  show_default=True,
              help="Number of speed levels in ramp.")
@click.pass_context
def sweep(ctx, motor, min_speed, max_speed, steps_per_level, levels):
    """Ramp speed from min to max and back, 200 steps at each level."""
    motors = ctx.obj["motors"]
    m = resolve_motor(motor, motors)

    if min_speed <= 0 or max_speed <= 0 or min_speed >= max_speed:
        console.print("[red]Invalid speed range. Need 0 < min-speed < max-speed.[/red]")
        sys.exit(1)

    # Build ramp: up then back down
    step_size = (max_speed - min_speed) / max(levels - 1, 1)
    ramp_up   = [min_speed + i * step_size for i in range(levels)]
    ramp_down = list(reversed(ramp_up[:-1]))
    speeds    = ramp_up + ramp_down

    total_steps = steps_per_level * len(speeds)

    console.print(f"\n[bold]Speed sweep — Motor {motor} ({m['name']})[/bold]")
    print_pin_table({motor: m})
    console.print(
        f"  Speed range: [cyan]{min_speed}[/cyan] → [cyan]{max_speed}[/cyan] → "
        f"[cyan]{min_speed}[/cyan] steps/s over {len(speeds)} levels"
    )
    console.print(f"  Steps per level: [cyan]{steps_per_level}[/cyan]   "
                  f"Total steps: [cyan]{total_steps}[/cyan]")

    setup_gpio(motors)

    def _cleanup(sig=None, frame=None):
        cleanup_gpio()
        console.print("\n[yellow]Interrupted — GPIO cleaned up.[/yellow]")
        sys.exit(0)

    signal.signal(signal.SIGINT, _cleanup)

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[cyan]{task.completed}/{task.total}[/cyan] steps"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            overall = progress.add_task("Sweep", total=total_steps)

            for spd in speeds:
                progress.update(
                    overall,
                    description=f"[bold]{spd:6.1f}[/bold] steps/s"
                )
                do_spin(m, steps_per_level, spd, clockwise=True,
                        progress=progress, task_id=overall)

        console.print(f"[green]Sweep complete.[/green]\n")
    finally:
        cleanup_gpio()

# ---------------------------------------------------------------------------
# test-all command
# ---------------------------------------------------------------------------

@cli.command("test-all")
@click.pass_context
def test_all(ctx):
    """Smoke test: spin each motor 100 steps CW then CCW, report pass/fail."""
    motors = ctx.obj["motors"]

    console.print("\n[bold]Smoke Test — All Motors[/bold]")
    print_pin_table(motors)
    console.print()

    setup_gpio(motors)

    results = {}

    def _cleanup(sig=None, frame=None):
        cleanup_gpio()
        console.print("\n[yellow]Interrupted — GPIO cleaned up.[/yellow]")
        sys.exit(0)

    signal.signal(signal.SIGINT, _cleanup)

    try:
        for mid, m in motors.items():
            console.print(f"[bold]Motor {mid} ({m['name']})[/bold]")
            passed = True
            for direction, clockwise in [("CW", True), ("CCW", False)]:
                try:
                    with Progress(
                        SpinnerColumn(),
                        TextColumn(f"  {direction}"),
                        BarColumn(bar_width=30),
                        TextColumn("[cyan]{task.completed}/{task.total}[/cyan]"),
                        console=console,
                        transient=True,
                    ) as progress:
                        task = progress.add_task(direction, total=100)
                        executed = do_spin(m, 100, 100.0, clockwise, progress, task)

                    if executed == 100:
                        console.print(f"  {direction}: [green]PASS[/green] (100 steps)")
                    else:
                        console.print(f"  {direction}: [red]FAIL[/red] ({executed}/100 steps)")
                        passed = False
                except Exception as exc:
                    console.print(f"  {direction}: [red]ERROR[/red] — {exc}")
                    passed = False

            results[mid] = passed
            console.print()

    finally:
        cleanup_gpio()

    # Summary table
    summary = Table(title="Results", box=box.SIMPLE_HEAVY, show_header=True,
                    header_style="bold")
    summary.add_column("Motor", style="bold")
    summary.add_column("Axis")
    summary.add_column("Result")

    all_passed = True
    for mid, passed in results.items():
        name   = motors[mid]["name"]
        status = "[green]PASS[/green]" if passed else "[red]FAIL[/red]"
        summary.add_row(str(mid), name, status)
        if not passed:
            all_passed = False

    console.print(summary)
    if all_passed:
        console.print("[green bold]All motors passed.[/green bold]\n")
    else:
        console.print("[red bold]Some motors failed — check connections.[/red bold]\n")
        sys.exit(1)

# ---------------------------------------------------------------------------
# interactive command
# ---------------------------------------------------------------------------

def run_interactive(stdscr, motors: dict):
    """Curses-based interactive motor control."""
    curses.cbreak()
    curses.noecho()
    stdscr.keypad(True)
    stdscr.nodelay(True)       # non-blocking getch
    curses.curs_set(0)

    # Colour pairs
    if curses.has_colors():
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN,  curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_CYAN,   curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_RED,    curses.COLOR_BLACK)
        GREEN  = curses.color_pair(1)
        YELLOW = curses.color_pair(2)
        CYAN   = curses.color_pair(3)
        RED    = curses.color_pair(4)
    else:
        GREEN = YELLOW = CYAN = RED = curses.A_NORMAL

    BOLD = curses.A_BOLD

    m1 = motors[1]
    m2 = motors[2]
    enable_motor(m1, True)
    enable_motor(m2, True)

    steps = {1: 0, 2: 0}   # cumulative step counters (signed)
    BASE_SPEED   = 200      # steps/sec normal
    FAST_SPEED   = 2000     # steps/sec with Shift
    STEPS_BURST  = 1        # steps per keypress

    def draw(status_msg=""):
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        row = 0

        title = " Interactive Motor Control "
        stdscr.addstr(row, max(0, (w - len(title)) // 2),
                      title, BOLD | CYAN)
        row += 2

        stdscr.addstr(row, 2, "Controls:", BOLD)
        row += 1
        controls = [
            ("Left / Right arrows", f"Motor 1 ({m1['name']}) CW / CCW"),
            ("Up / Down arrows",    f"Motor 2 ({m2['name']}) UP / DOWN"),
            ("Hold SHIFT",          "10× speed"),
            ("Q",                   "Quit"),
        ]
        for key, desc in controls:
            stdscr.addstr(row, 4, f"{key:<25}", YELLOW | BOLD)
            stdscr.addstr(row, 4 + 25, desc)
            row += 1

        row += 1
        stdscr.addstr(row, 2, "Step counts:", BOLD)
        row += 1
        stdscr.addstr(row, 4,
                      f"Motor 1 ({m1['name']:9s}): {steps[1]:+7d} steps",
                      GREEN | BOLD)
        row += 1
        stdscr.addstr(row, 4,
                      f"Motor 2 ({m2['name']:9s}): {steps[2]:+7d} steps",
                      GREEN | BOLD)
        row += 2

        if status_msg:
            stdscr.addstr(row, 2, status_msg[:w - 3], CYAN)
            row += 1

        # DRY-RUN banner
        if DRY_RUN or not HAS_GPIO:
            msg = " DRY-RUN: no GPIO pulses "
            stdscr.addstr(h - 2, max(0, (w - len(msg)) // 2), msg,
                          RED | BOLD)

        stdscr.refresh()

    draw("Ready. Press arrow keys to move motors.")

    while True:
        key = stdscr.getch()

        if key == -1:
            time.sleep(0.01)
            continue

        # Quit
        if key in (ord("q"), ord("Q")):
            break

        # Detect shift via curses KEY constants
        # curses reports shifted arrows as separate keycodes on most terminals
        motor_id  = None
        clockwise = None
        fast      = False

        if key == curses.KEY_LEFT:
            motor_id, clockwise = 1, True
        elif key == curses.KEY_RIGHT:
            motor_id, clockwise = 1, False
        elif key == curses.KEY_UP:
            motor_id, clockwise = 2, True
        elif key == curses.KEY_DOWN:
            motor_id, clockwise = 2, False
        # Shifted arrow keys (terminal dependent; common xterm codes)
        elif key == 393:  # Shift+Left
            motor_id, clockwise, fast = 1, True, True
        elif key == 402:  # Shift+Right
            motor_id, clockwise, fast = 1, False, True
        elif key == 337:  # Shift+Up
            motor_id, clockwise, fast = 2, True, True
        elif key == 336:  # Shift+Down
            motor_id, clockwise, fast = 2, False, True
        else:
            draw()
            continue

        speed  = FAST_SPEED if fast else BASE_SPEED
        target = motors[motor_id]
        set_direction(target, clockwise)

        burst = STEPS_BURST * (10 if fast else 1)
        pulse_step(target["step"], 1.0 / speed)
        steps[motor_id] += burst if clockwise else -burst

        speed_label = f"{'FAST' if fast else 'NORM'} {speed} steps/s"
        axis_label  = f"Motor {motor_id} ({'CW' if clockwise else 'CCW'})"
        draw(f"{axis_label}  [{speed_label}]")

    enable_motor(m1, False)
    enable_motor(m2, False)


@cli.command()
@click.pass_context
def interactive(ctx):
    """Terminal keyboard control: arrows to move motors, Q to quit."""
    motors = ctx.obj["motors"]

    console.print("\n[bold]Interactive Motor Control[/bold]")
    print_pin_table(motors)
    console.print("Entering curses UI — press [bold]Q[/bold] to quit.\n")

    setup_gpio(motors)

    def _cleanup(sig=None, frame=None):
        cleanup_gpio()
        sys.exit(0)

    signal.signal(signal.SIGINT, _cleanup)

    try:
        curses.wrapper(run_interactive, motors)
    finally:
        cleanup_gpio()

    console.print("[green]Interactive session ended. GPIO cleaned up.[/green]\n")

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli(obj={})
