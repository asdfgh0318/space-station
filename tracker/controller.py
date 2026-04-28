"""Two-axis stepper controller for the alt-az antenna tracker.

Drives the Waveshare Stepper Motor HAT (B) on a Raspberry Pi 4B via lgpio.
On dev machines without lgpio (or when --sim is requested), a no-op GPIO
shim is used so position math, CLI, and tests still run.
"""

from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import click
import yaml
from rich.console import Console
from rich.table import Table

try:
    import lgpio  # type: ignore
    _HAS_LGPIO = True
except ImportError:
    lgpio = None  # type: ignore
    _HAS_LGPIO = False


# Pulse / setup timings for typical step/dir drivers (TMC2209-class).
_STEP_PULSE_S = 2e-6      # STEP high pulse width
_DIR_SETUP_S = 5e-6       # DIR-to-STEP setup time
_MIN_STEP_INTERVAL_S = 1e-4  # 100 µs floor between rising edges


# --------------------------------------------------------------------------- #
# GPIO backends
# --------------------------------------------------------------------------- #


class _LgpioBackend:
    """Thin wrapper over lgpio so the rest of the module is backend-agnostic."""

    mode = "real"

    def __init__(self, chip: int = 0) -> None:
        self._handle = lgpio.gpiochip_open(chip)
        self._claimed: set[int] = set()

    def claim_output(self, pin: int, initial: int = 0) -> None:
        if pin in self._claimed:
            return
        lgpio.gpio_claim_output(self._handle, pin, initial)
        self._claimed.add(pin)

    def write(self, pin: int, level: int) -> None:
        lgpio.gpio_write(self._handle, pin, level)

    def close(self) -> None:
        if self._handle is not None:
            try:
                lgpio.gpiochip_close(self._handle)
            finally:
                self._handle = None


class _SimGpio:
    """Position-state-only GPIO. Records writes, performs no I/O."""

    mode = "sim"

    def __init__(self) -> None:
        self.levels: dict[int, int] = {}

    def claim_output(self, pin: int, initial: int = 0) -> None:
        self.levels[pin] = initial

    def write(self, pin: int, level: int) -> None:
        self.levels[pin] = level

    def close(self) -> None:
        self.levels.clear()


# --------------------------------------------------------------------------- #
# Single-axis controller
# --------------------------------------------------------------------------- #


@dataclass
class StepperAxis:
    name: str
    step_pin: int
    dir_pin: int
    enable_pin: int
    steps_per_rev: int
    microstepping: int
    gear_ratio: float
    max_speed: float          # deg/s
    acceleration: float       # deg/s²
    min_angle: float
    max_angle: float
    gpio: Any = None
    position_deg: float = 0.0
    enabled: bool = False
    _stop_flag: threading.Event = field(default_factory=threading.Event, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def __post_init__(self) -> None:
        if self.gpio is None:
            self.gpio = _SimGpio()
        self.gpio.claim_output(self.step_pin, 0)
        self.gpio.claim_output(self.dir_pin, 0)
        self.gpio.claim_output(self.enable_pin, 1)  # active-low: 1 = disabled

    # ---- conversions ----

    @property
    def total_steps_per_rev(self) -> int:
        return int(self.steps_per_rev * self.microstepping * self.gear_ratio)

    @property
    def degrees_per_step(self) -> float:
        return 360.0 / self.total_steps_per_rev

    @property
    def position_steps(self) -> int:
        return int(round(self.position_deg / self.degrees_per_step))

    # ---- enable line ----

    def enable(self) -> None:
        self.gpio.write(self.enable_pin, 0)
        self.enabled = True

    def disable(self) -> None:
        self.gpio.write(self.enable_pin, 1)
        self.enabled = False

    # ---- motion primitives ----

    def step(self, direction: int) -> None:
        if direction not in (+1, -1):
            raise ValueError("direction must be +1 or -1")
        self.gpio.write(self.dir_pin, 1 if direction > 0 else 0)
        time.sleep(_DIR_SETUP_S)
        self.gpio.write(self.step_pin, 1)
        time.sleep(_STEP_PULSE_S)
        self.gpio.write(self.step_pin, 0)
        self.position_deg += direction * self.degrees_per_step

    def stop(self) -> None:
        self._stop_flag.set()

    def move_steps(self, n_steps: int, direction: int) -> None:
        """Trapezoidal velocity profile, sleep-paced between steps."""
        if n_steps <= 0:
            return
        with self._lock:
            self._stop_flag.clear()
            if not self.enabled:
                self.enable()

            v_max = self.max_speed / self.degrees_per_step       # steps/s
            accel = self.acceleration / self.degrees_per_step    # steps/s²
            v_max = max(v_max, 1.0)
            accel = max(accel, 1.0)

            ramp_steps = min(int(v_max * v_max / (2.0 * accel)), n_steps // 2)
            cruise_steps = n_steps - 2 * ramp_steps

            for i in range(n_steps):
                if self._stop_flag.is_set():
                    return
                if i < ramp_steps:
                    v = math.sqrt(2.0 * accel * (i + 1))
                elif i < ramp_steps + cruise_steps:
                    v = v_max
                else:
                    remaining = n_steps - i
                    v = math.sqrt(2.0 * accel * max(remaining, 1))
                v = min(max(v, 1.0), v_max)
                interval = max(1.0 / v, _MIN_STEP_INTERVAL_S)
                self.step(direction)
                time.sleep(max(interval - _STEP_PULSE_S - _DIR_SETUP_S, 0.0))

    def goto_deg(self, target_deg: float) -> None:
        target = max(self.min_angle, min(self.max_angle, target_deg))
        delta_deg = target - self.position_deg
        n_steps = int(round(abs(delta_deg) / self.degrees_per_step))
        if n_steps == 0:
            return
        direction = +1 if delta_deg > 0 else -1
        self.move_steps(n_steps, direction)
        # Snap to commanded value to avoid rounding drift across many moves.
        self.position_deg = target

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "position_deg": round(self.position_deg, 4),
            "position_steps": self.position_steps,
            "enabled": self.enabled,
            "min_angle": self.min_angle,
            "max_angle": self.max_angle,
            "max_speed": self.max_speed,
            "degrees_per_step": round(self.degrees_per_step, 6),
        }


# --------------------------------------------------------------------------- #
# Two-axis orchestration
# --------------------------------------------------------------------------- #


class AntennaTracker:
    def __init__(
        self,
        azimuth: StepperAxis,
        elevation: StepperAxis,
        config: dict[str, Any],
        gpio: Any,
    ) -> None:
        self.az = azimuth
        self.el = elevation
        self.config = config
        self.gpio = gpio

    # ---- factory ----

    @classmethod
    def from_config(
        cls,
        path: str | Path,
        gpio_backend: str = "auto",
    ) -> AntennaTracker:
        cfg_path = Path(path)
        with cfg_path.open("r", encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh)

        tracker_cfg = cfg["tracker"]
        gpio = cls._make_gpio(gpio_backend)

        az_cfg = tracker_cfg["azimuth"]
        el_cfg = tracker_cfg["elevation"]
        az = cls._build_axis("azimuth", az_cfg, gpio)
        el = cls._build_axis("elevation", el_cfg, gpio)
        return cls(az, el, cfg, gpio)

    @staticmethod
    def _make_gpio(backend: str) -> Any:
        if backend == "sim":
            return _SimGpio()
        if backend == "real":
            if not _HAS_LGPIO:
                raise RuntimeError("lgpio not available — install lgpio or use sim mode")
            return _LgpioBackend()
        # auto
        if _HAS_LGPIO:
            try:
                return _LgpioBackend()
            except Exception:
                return _SimGpio()
        return _SimGpio()

    @staticmethod
    def _build_axis(name: str, c: dict[str, Any], gpio: Any) -> StepperAxis:
        return StepperAxis(
            name=name,
            step_pin=int(c["step_pin"]),
            dir_pin=int(c["dir_pin"]),
            enable_pin=int(c["enable_pin"]),
            steps_per_rev=int(c["steps_per_rev"]),
            microstepping=int(c["microstepping"]),
            gear_ratio=float(c["gear_ratio"]),
            max_speed=float(c["max_speed"]),
            acceleration=float(c["acceleration"]),
            min_angle=float(c["min_angle"]),
            max_angle=float(c["max_angle"]),
            gpio=gpio,
        )

    # ---- motion ----

    def goto(self, az_deg: float, el_deg: float) -> None:
        threads = [
            threading.Thread(target=self.az.goto_deg, args=(az_deg,), daemon=True),
            threading.Thread(target=self.el.goto_deg, args=(el_deg,), daemon=True),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    def home(self) -> None:
        """Naive home: drive both axes to 0,0 in software (no limit switch yet)."""
        self.goto(self.az.min_angle, self.el.min_angle)
        self.az.position_deg = 0.0
        self.el.position_deg = 0.0

    def park(self) -> None:
        tcfg = self.config.get("tracker", {})
        az_park = float(tcfg.get("park_azimuth", 0.0))
        el_park = float(tcfg.get("park_elevation", 90.0))
        self.goto(az_park, el_park)

    def stop(self) -> None:
        self.az.stop()
        self.el.stop()

    def enable_all(self) -> None:
        self.az.enable()
        self.el.enable()

    def disable_all(self) -> None:
        self.az.disable()
        self.el.disable()

    def status(self) -> dict[str, Any]:
        return {
            "az": self.az.to_dict(),
            "el": self.el.to_dict(),
            "mode": getattr(self.gpio, "mode", "unknown"),
        }

    def close(self) -> None:
        self.disable_all()
        self.gpio.close()


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


_DEFAULT_CONFIG = "tracker/config.yaml"


def _backend(sim: bool) -> str:
    return "sim" if sim else "auto"


def _load(config: str, sim: bool) -> AntennaTracker:
    return AntennaTracker.from_config(config, gpio_backend=_backend(sim))


def _render_status(tracker: AntennaTracker) -> None:
    s = tracker.status()
    console = Console()
    table = Table(title=f"Antenna tracker status (mode={s['mode']})")
    table.add_column("axis", style="bold cyan")
    table.add_column("position (deg)", justify="right")
    table.add_column("position (steps)", justify="right")
    table.add_column("enabled", justify="center")
    table.add_column("range", justify="right")
    table.add_column("deg/step", justify="right")
    for key in ("az", "el"):
        a = s[key]
        table.add_row(
            a["name"],
            f"{a['position_deg']:.4f}",
            f"{a['position_steps']}",
            "yes" if a["enabled"] else "no",
            f"[{a['min_angle']:.0f}, {a['max_angle']:.0f}]",
            f"{a['degrees_per_step']:.6f}",
        )
    console.print(table)


@click.group()
@click.option("--config", default=_DEFAULT_CONFIG, show_default=True,
              help="Path to tracker config YAML.")
@click.option("--sim", is_flag=True, help="Force simulation GPIO backend.")
@click.pass_context
def cli(ctx: click.Context, config: str, sim: bool) -> None:
    """Alt-az antenna tracker control."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = config
    ctx.obj["sim"] = sim


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show current axis state."""
    tracker = _load(ctx.obj["config"], ctx.obj["sim"])
    _render_status(tracker)
    tracker.close()


@cli.command()
@click.argument("az", type=float)
@click.argument("el", type=float)
@click.pass_context
def goto(ctx: click.Context, az: float, el: float) -> None:
    """Move to (AZ, EL) in degrees."""
    tracker = _load(ctx.obj["config"], ctx.obj["sim"])
    tracker.enable_all()
    tracker.goto(az, el)
    _render_status(tracker)
    tracker.close()


@cli.command()
@click.pass_context
def home(ctx: click.Context) -> None:
    """Home both axes."""
    tracker = _load(ctx.obj["config"], ctx.obj["sim"])
    tracker.enable_all()
    tracker.home()
    _render_status(tracker)
    tracker.close()


@cli.command()
@click.pass_context
def park(ctx: click.Context) -> None:
    """Move to park position."""
    tracker = _load(ctx.obj["config"], ctx.obj["sim"])
    tracker.enable_all()
    tracker.park()
    _render_status(tracker)
    tracker.close()


@cli.command()
@click.option("--motor", type=click.Choice(["az", "el"]), required=True)
@click.option("--count", type=int, required=True, help="Number of microsteps.")
@click.option("--dir", "direction", type=click.Choice(["cw", "ccw"]), default="cw",
              show_default=True)
@click.pass_context
def step(ctx: click.Context, motor: str, count: int, direction: str) -> None:
    """Pulse N microsteps on one motor."""
    tracker = _load(ctx.obj["config"], ctx.obj["sim"])
    axis = tracker.az if motor == "az" else tracker.el
    axis.enable()
    axis.move_steps(count, +1 if direction == "cw" else -1)
    _render_status(tracker)
    tracker.close()


@cli.command()
@click.pass_context
def stop(ctx: click.Context) -> None:
    """Disable drivers and stop motion."""
    tracker = _load(ctx.obj["config"], ctx.obj["sim"])
    tracker.stop()
    tracker.disable_all()
    _render_status(tracker)
    tracker.close()


if __name__ == "__main__":
    cli(obj={})
