#!/usr/bin/env python3
"""Bench-test CLI using Waveshare HR8825 driver as backend.
DIPs all-1 required (software microstep mode).
"""
import sys, time
from pathlib import Path
import click
import yaml

# Make tracker package importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tracker.hr8825 import HR8825


def load_pins(config_path: Path):
    try:
        d = yaml.safe_load(config_path.read_text())["tracker"]
        az = d["azimuth"]; el = d["elevation"]
        return {
            1: dict(dir_pin=az["dir_pin"], step_pin=az["step_pin"],
                    enable_pin=az["enable_pin"], mode_pins=(16, 17, 20)),
            2: dict(dir_pin=el["dir_pin"], step_pin=el["step_pin"],
                    enable_pin=el["enable_pin"], mode_pins=(21, 22, 27)),
        }
    except Exception as e:
        click.echo(f"[warn] config load failed ({e}); using defaults")
        return {
            1: dict(dir_pin=13, step_pin=19, enable_pin=12, mode_pins=(16,17,20)),
            2: dict(dir_pin=24, step_pin=18, enable_pin=4,  mode_pins=(21,22,27)),
        }


@click.group()
@click.option("--config", "config_path", type=click.Path(path_type=Path),
              default=Path(__file__).resolve().parent.parent / "tracker/config.yaml")
@click.pass_context
def cli(ctx, config_path):
    ctx.obj = load_pins(Path(config_path))


@cli.command()
@click.option("--motor", type=click.IntRange(1, 2), required=True)
@click.option("--steps", type=int, required=True)
@click.option("--speed", type=float, required=True, help="Steps per second.")
@click.option("--dir", "direction", type=click.Choice(["cw", "ccw"]), required=True)
@click.option("--microstep", default="fullstep",
              type=click.Choice(["fullstep","halfstep","1/4step","1/8step","1/16step","1/32step"]))
@click.pass_context
def spin(ctx, motor, steps, speed, direction, microstep):
    pins = ctx.obj[motor]
    m = HR8825(**pins)
    m.SetMicroStep("softward", microstep)
    stepdelay = 0.5 / max(speed, 1.0)   # half-period each side of pulse
    Dir = "forward" if direction == "cw" else "backward"
    click.echo(f"motor {motor}: {steps} {microstep} steps {direction} @ {speed} sps")
    m.TurnStep(Dir=Dir, steps=steps, stepdelay=stepdelay)
    m.Stop()
    click.echo("done")


@cli.command("test-all")
@click.pass_context
def test_all(ctx):
    for motor in (1, 2):
        ctx.invoke(spin, motor=motor, steps=200, speed=100, direction="cw", microstep="fullstep")
        time.sleep(0.5)
        ctx.invoke(spin, motor=motor, steps=200, speed=100, direction="ccw", microstep="fullstep")


if __name__ == "__main__":
    cli()
