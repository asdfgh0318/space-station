#!/usr/bin/env python3
"""Bench-test CLI for the two NEMA 17 steppers on the Waveshare Stepper Motor HAT (B).

Standalone: does NOT import tracker.controller. Reads tracker/config.yaml when
present, otherwise falls back to the hardcoded pin map below.
"""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import click
import yaml
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

try:
    import lgpio  # type: ignore
    _HAS_LGPIO = True
except Exception:  # pragma: no cover — dev box without lgpio
    lgpio = None  # type: ignore
    _HAS_LGPIO = False

console = Console()

# Hardcoded fallback pin map (motor 1 = AZ, motor 2 = EL).
FALLBACK_CONFIG = {
    "azimuth": {
        "step_pin": 19, "dir_pin": 13, "enable_pin": 12,
        "steps_per_rev": 200, "microstepping": 32, "gear_ratio": 1,
        "max_speed": 15.0, "acceleration": 8.0,
    },
    "elevation": {
        "step_pin": 18, "dir_pin": 24, "enable_pin": 4,
        "steps_per_rev": 200, "microstepping": 32, "gear_ratio": 1,
        "max_speed": 12.0, "acceleration": 6.0,
    },
}

STEP_PULSE_HIGH_S = 5e-6   # 5 µs
DIR_SETTLE_S = 1e-6        # 1 µs


@dataclass
class MotorCfg:
    name: str
    step_pin: int
    dir_pin: int
    enable_pin: int
    steps_per_rev: int
    microstepping: int
    gear_ratio: float
    max_speed: float       # config units (deg/s in YAML); used as steps/s default for sweep
    acceleration: float

    @property
    def steps_per_deg(self) -> float:
        return (self.steps_per_rev * self.microstepping * self.gear_ratio) / 360.0

    @property
    def max_speed_steps(self) -> float:
        """Convert config max_speed (deg/s) to steps/s for the sweep ramp."""
        return self.max_speed * self.steps_per_deg


def load_config(path: Path) -> tuple[MotorCfg, MotorCfg]:
    """Load motor configs from YAML, falling back to defaults on FileNotFoundError."""
    raw: dict
    try:
        with path.open("r") as f:
            data = yaml.safe_load(f) or {}
        raw = (data.get("tracker") or {})
        az = raw.get("azimuth") or FALLBACK_CONFIG["azimuth"]
        el = raw.get("elevation") or FALLBACK_CONFIG["elevation"]
    except FileNotFoundError:
        az = FALLBACK_CONFIG["azimuth"]
        el = FALLBACK_CONFIG["elevation"]
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to parse {path}: {e}; using fallback")
        az = FALLBACK_CONFIG["azimuth"]
        el = FALLBACK_CONFIG["elevation"]

    def build(name: str, d: dict) -> MotorCfg:
        return MotorCfg(
            name=name,
            step_pin=int(d["step_pin"]),
            dir_pin=int(d["dir_pin"]),
            enable_pin=int(d["enable_pin"]),
            steps_per_rev=int(d.get("steps_per_rev", 200)),
            microstepping=int(d.get("microstepping", 32)),
            gear_ratio=float(d.get("gear_ratio", 1)),
            max_speed=float(d.get("max_speed", 10.0)),
            acceleration=float(d.get("acceleration", 5.0)),
        )

    return build("azimuth", az), build("elevation", el)


# ---------------------------------------------------------------------------
# GPIO layer
# ---------------------------------------------------------------------------
class Gpio:
    """Tiny wrapper around lgpio with a dry-run/sim backend."""

    def __init__(self, sim: bool = False, verbose: bool = False):
        self.sim = sim or not _HAS_LGPIO
        self.verbose = verbose
        self.handle: Optional[int] = None
        self._claimed: set[int] = set()
        self.write_count: int = 0

    def open_chip(self) -> None:
        if self.sim:
            if self.verbose:
                console.print("[dim]sim: open_chip(0)[/dim]")
            return
        self.handle = lgpio.gpiochip_open(0)

    def claim_output(self, pin: int, initial: int = 0) -> None:
        if pin in self._claimed:
            return
        if self.sim:
            if self.verbose:
                console.print(f"[dim]sim: claim_output(BCM {pin})[/dim]")
        else:
            lgpio.gpio_claim_output(self.handle, pin, initial)
        self._claimed.add(pin)

    def write(self, pin: int, value: int) -> None:
        self.write_count += 1
        if self.sim:
            if self.verbose:
                console.print(f"[dim]sim: write(BCM {pin}, {value})[/dim]")
            return
        lgpio.gpio_write(self.handle, pin, value)

    def cleanup(self) -> None:
        if self.sim:
            if self.verbose:
                console.print(f"[dim]sim: cleanup ({self.write_count} writes)[/dim]")
            return
        if self.handle is not None:
            for pin in self._claimed:
                try:
                    lgpio.gpio_free(self.handle, pin)
                except Exception:
                    pass
            try:
                lgpio.gpiochip_close(self.handle)
            except Exception:
                pass
        self.handle = None
        self._claimed.clear()


# ---------------------------------------------------------------------------
# Stepping primitives
# ---------------------------------------------------------------------------
def _set_dir(gpio: Gpio, motor: MotorCfg, direction: str) -> None:
    val = 1 if direction == "cw" else 0
    gpio.write(motor.dir_pin, val)
    time.sleep(DIR_SETTLE_S)


def _enable(gpio: Gpio, motor: MotorCfg, on: bool) -> None:
    # Most stepper drivers (TMC2209/A4988) have ENABLE active-low.
    gpio.write(motor.enable_pin, 0 if on else 1)


def _pulse(gpio: Gpio, motor: MotorCfg) -> None:
    gpio.write(motor.step_pin, 1)
    time.sleep(STEP_PULSE_HIGH_S)
    gpio.write(motor.step_pin, 0)


def _trapezoid_delays(total_steps: int, target_sps: float,
                      accel_sps2: float, min_sps: float = 50.0) -> list[float]:
    """Build a per-step delay schedule (seconds between pulses) with a trap profile."""
    target_sps = max(target_sps, min_sps + 1.0)
    # Steps needed to ramp from min_sps to target_sps at accel_sps2:
    # dv = a*t  →  t_ramp = (target - min) / a
    # steps_ramp ≈ avg_speed * t_ramp = ((target+min)/2) * t_ramp
    t_ramp = (target_sps - min_sps) / max(accel_sps2, 1.0)
    steps_ramp = int(((target_sps + min_sps) / 2.0) * t_ramp)
    steps_ramp = max(1, min(steps_ramp, total_steps // 2))
    cruise = max(0, total_steps - 2 * steps_ramp)

    delays: list[float] = []
    for i in range(steps_ramp):
        f = (i + 1) / steps_ramp
        sps = min_sps + (target_sps - min_sps) * f
        delays.append(1.0 / sps)
    for _ in range(cruise):
        delays.append(1.0 / target_sps)
    for i in range(steps_ramp):
        f = 1.0 - (i + 1) / steps_ramp
        sps = min_sps + (target_sps - min_sps) * f
        delays.append(1.0 / sps)
    # Pad/trim to exact length
    while len(delays) < total_steps:
        delays.append(1.0 / target_sps)
    return delays[:total_steps]


def _step_with_progress(gpio: Gpio, motor: MotorCfg, steps: int,
                        delays: list[float], label: str,
                        show_progress: bool = True) -> None:
    if show_progress:
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total} steps"),
            TimeElapsedColumn(),
            console=console,
            transient=False,
        ) as prog:
            task = prog.add_task(label, total=steps)
            t = time.perf_counter()
            for i in range(steps):
                _pulse(gpio, motor)
                t += max(delays[i], STEP_PULSE_HIGH_S * 2)
                slack = t - time.perf_counter()
                if slack > 0:
                    time.sleep(slack)
                if (i & 0x1F) == 0 or i == steps - 1:
                    prog.update(task, completed=i + 1)
    else:
        t = time.perf_counter()
        for i in range(steps):
            _pulse(gpio, motor)
            t += max(delays[i], STEP_PULSE_HIGH_S * 2)
            slack = t - time.perf_counter()
            if slack > 0:
                time.sleep(slack)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
@click.group()
@click.option("--config", "config_path", type=click.Path(path_type=Path),
              default=Path("tracker/config.yaml"), show_default=True)
@click.option("--dry-run", is_flag=True, help="Don't touch GPIO, just log intent.")
@click.option("--verbose", "-v", is_flag=True)
@click.pass_context
def cli(ctx: click.Context, config_path: Path, dry_run: bool, verbose: bool) -> None:
    """Bench-test CLI for the two NEMA 17 steppers."""
    az, el = load_config(config_path)
    gpio = Gpio(sim=dry_run, verbose=verbose)
    try:
        gpio.open_chip()
    except Exception as e:
        console.print(f"[red]✗[/red] gpiochip open failed: {e}; switching to sim")
        gpio = Gpio(sim=True, verbose=verbose)
        gpio.open_chip()
    # Claim all pins up-front; safe to repeat.
    for m in (az, el):
        for pin in (m.step_pin, m.dir_pin, m.enable_pin):
            gpio.claim_output(pin, 0)
    # Drivers idle (disabled) at startup
    _enable(gpio, az, False)
    _enable(gpio, el, False)
    ctx.obj = {"az": az, "el": el, "gpio": gpio, "dry_run": dry_run, "verbose": verbose}
    ctx.call_on_close(gpio.cleanup)


def _pick_motor(ctx: click.Context, motor_idx: int) -> MotorCfg:
    return ctx.obj["az"] if motor_idx == 1 else ctx.obj["el"]


@cli.command()
@click.option("--motor", type=click.IntRange(1, 2), required=True)
@click.option("--steps", type=int, required=True)
@click.option("--speed", type=float, required=True, help="Steps per second.")
@click.option("--dir", "direction", type=click.Choice(["cw", "ccw"]), required=True)
@click.pass_context
def spin(ctx: click.Context, motor: int, steps: int, speed: float, direction: str) -> None:
    """Spin one motor a fixed number of microsteps."""
    m = _pick_motor(ctx, motor)
    gpio: Gpio = ctx.obj["gpio"]
    _enable(gpio, m, True)
    _set_dir(gpio, m, direction)
    accel = m.acceleration * m.steps_per_deg if m.acceleration < 1000 else m.acceleration
    delays = _trapezoid_delays(steps, speed, max(accel, 50.0))
    label = f"spin motor {motor} ({m.name}) {direction} {speed:.0f} sps"
    try:
        _step_with_progress(gpio, m, steps, delays, label)
        console.print(f"[green]✓[/green] {steps} steps done on {m.name}")
    except KeyboardInterrupt:
        console.print(f"[red]✗[/red] interrupted")
    finally:
        _enable(gpio, m, False)


@cli.command()
@click.option("--motor", type=click.IntRange(1, 2), required=True)
@click.pass_context
def sweep(ctx: click.Context, motor: int) -> None:
    """Speed ramp test: slow → max_speed → slow over ~5 seconds. Useful to find resonance."""
    m = _pick_motor(ctx, motor)
    gpio: Gpio = ctx.obj["gpio"]
    target = max(m.max_speed_steps, 200.0)
    # Build a 5s schedule: 2.5s ramp up, 2.5s ramp down (no cruise)
    duration = 5.0
    avg_sps = target / 2.0
    total_steps = int(avg_sps * duration)
    accel_sps2 = (target - 50.0) / (duration / 2.0)
    delays = _trapezoid_delays(total_steps, target, accel_sps2)
    _enable(gpio, m, True)
    _set_dir(gpio, m, "cw")
    label = f"sweep motor {motor} ({m.name}) → {target:.0f} sps"
    try:
        _step_with_progress(gpio, m, total_steps, delays, label)
        console.print(f"[green]✓[/green] sweep complete on {m.name}")
    except KeyboardInterrupt:
        console.print(f"[red]✗[/red] interrupted")
    finally:
        _enable(gpio, m, False)


@cli.command("test-all")
@click.pass_context
def test_all(ctx: click.Context) -> None:
    """Smoke test: spin each motor 200 fwd, 200 rev, then disable. Print pass/fail table."""
    gpio: Gpio = ctx.obj["gpio"]
    motors = [(1, ctx.obj["az"]), (2, ctx.obj["el"])]
    table = Table(title="motor_test: smoke test")
    table.add_column("motor", style="bold")
    table.add_column("action")
    table.add_column("status")

    overall_ok = True
    for idx, m in motors:
        for direction, label in (("cw", "200 steps cw"), ("ccw", "200 steps ccw")):
            try:
                _enable(gpio, m, True)
                _set_dir(gpio, m, direction)
                delays = _trapezoid_delays(200, 400.0, 800.0)
                _step_with_progress(gpio, m, 200, delays,
                                    f"motor {idx} {m.name} {direction}",
                                    show_progress=False)
                table.add_row(f"{idx} ({m.name})", label, "[green]✓[/green]")
            except Exception as e:
                overall_ok = False
                table.add_row(f"{idx} ({m.name})", label, f"[red]✗ {e}[/red]")
            finally:
                _enable(gpio, m, False)

    console.print(table)
    if overall_ok:
        console.print("[green]✓[/green] all motors passed")
        sys.exit(0)
    console.print("[red]✗[/red] one or more motors failed")
    sys.exit(1)


def _read_key() -> Optional[str]:
    """Read one keypress (incl. arrow escape sequences). Returns None on non-tty."""
    if not sys.stdin.isatty():
        return None
    import termios
    import tty
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            ch += sys.stdin.read(2)
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


@cli.command()
@click.pass_context
def interactive(ctx: click.Context) -> None:
    """Arrow-key control. Up/Down = motor 1, Left/Right = motor 2. q to quit."""
    if not sys.stdin.isatty():
        console.print("[red]✗[/red] interactive requires a TTY")
        sys.exit(2)
    gpio: Gpio = ctx.obj["gpio"]
    az, el = ctx.obj["az"], ctx.obj["el"]
    _enable(gpio, az, True)
    _enable(gpio, el, True)
    console.print("[bold]interactive mode[/bold] — ↑/↓ motor 1, ←/→ motor 2, q to quit")
    JOG_STEPS = 50
    JOG_SPEED = 400.0
    try:
        while True:
            key = _read_key()
            if key is None or key == "q":
                break
            mapping = {
                "\x1b[A": (az, "cw",  "motor 1 ↑"),
                "\x1b[B": (az, "ccw", "motor 1 ↓"),
                "\x1b[C": (el, "cw",  "motor 2 →"),
                "\x1b[D": (el, "ccw", "motor 2 ←"),
            }
            if key not in mapping:
                continue
            m, direction, label = mapping[key]
            _set_dir(gpio, m, direction)
            delays = _trapezoid_delays(JOG_STEPS, JOG_SPEED, 800.0)
            _step_with_progress(gpio, m, JOG_STEPS, delays, label, show_progress=False)
            console.print(f"[green]✓[/green] {label} ({JOG_STEPS} steps)")
    except KeyboardInterrupt:
        pass
    finally:
        _enable(gpio, az, False)
        _enable(gpio, el, False)
        console.print("[dim]exited interactive[/dim]")


if __name__ == "__main__":
    cli()
