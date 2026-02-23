import os
import time
import threading
import yaml
import click

try:
    import lgpio
    HAS_LGPIO = True
except ImportError:
    HAS_LGPIO = False

try:
    import pigpio
    HAS_PIGPIO = True
except ImportError:
    HAS_PIGPIO = False

# Try connecting to pigpio daemon
_pi = None
if HAS_PIGPIO:
    _pi = pigpio.pi()
    if not _pi.connected:
        _pi.stop()
        _pi = None
        HAS_PIGPIO = False

# GPIO chip handle for lgpio
_chip = None
if not HAS_PIGPIO and HAS_LGPIO:
    try:
        _chip = lgpio.gpiochip_open(0)
    except Exception:
        HAS_LGPIO = False
        _chip = None

SIMULATION = not HAS_PIGPIO and not HAS_LGPIO
if HAS_PIGPIO:
    BACKEND = "pigpio"
elif HAS_LGPIO:
    BACKEND = "lgpio"
else:
    BACKEND = "simulation"

# ---------------------------------------------------------------------------
# GPIO helpers
# ---------------------------------------------------------------------------

_claimed_pins = set()

def _gpio_setup_output(pin):
    if SIMULATION:
        return
    if HAS_PIGPIO:
        _pi.set_mode(pin, pigpio.OUTPUT)
    else:
        if pin not in _claimed_pins:
            lgpio.gpio_claim_output(_chip, pin, 0)
            _claimed_pins.add(pin)


def _gpio_setup_input_pullup(pin):
    if SIMULATION:
        return
    if HAS_PIGPIO:
        _pi.set_mode(pin, pigpio.INPUT)
        _pi.set_pull_up_down(pin, pigpio.PUD_UP)
    else:
        if pin not in _claimed_pins:
            lgpio.gpio_claim_input(_chip, pin, lgpio.SET_PULL_UP)
            _claimed_pins.add(pin)


def _gpio_write(pin, value):
    if SIMULATION:
        return
    if HAS_PIGPIO:
        _pi.write(pin, value)
    else:
        lgpio.gpio_write(_chip, pin, value)


def _gpio_read(pin):
    if SIMULATION:
        return 1
    if HAS_PIGPIO:
        return _pi.read(pin)
    else:
        return lgpio.gpio_read(_chip, pin)


def _gpio_cleanup():
    if SIMULATION:
        return
    if HAS_PIGPIO:
        global _pi
        if _pi is not None:
            _pi.stop()
            _pi = None
    else:
        global _chip
        if _chip is not None:
            lgpio.gpiochip_close(_chip)
            _chip = None


# ---------------------------------------------------------------------------
# Trapezoidal acceleration helpers
# ---------------------------------------------------------------------------

MIN_STEP_SPEED = 100  # steps/s — starting speed for ramp


def _build_delay_profile(total_steps, max_step_speed, accel_steps_per_s2):
    """
    Return list of per-step delays (seconds) for a trapezoidal profile.
    accel_steps_per_s2 is already in steps/s^2.
    """
    if total_steps == 0:
        return []

    start_speed = min(MIN_STEP_SPEED, max_step_speed)
    # Steps to ramp from start_speed to max_step_speed
    ramp_steps = int((max_step_speed ** 2 - start_speed ** 2) / (2 * accel_steps_per_s2))
    ramp_steps = max(1, ramp_steps)

    # If not enough room for full ramp, cut ramp short
    half = total_steps // 2
    ramp_steps = min(ramp_steps, half)

    delays = []

    for i in range(total_steps):
        if i < ramp_steps:
            # Ramp up
            speed = (start_speed ** 2 + 2 * accel_steps_per_s2 * i) ** 0.5
        elif i >= total_steps - ramp_steps:
            # Ramp down (mirror of ramp up)
            steps_from_end = total_steps - 1 - i
            speed = (start_speed ** 2 + 2 * accel_steps_per_s2 * steps_from_end) ** 0.5
        else:
            speed = max_step_speed

        speed = max(speed, start_speed)
        speed = min(speed, max_step_speed)
        delays.append(1.0 / speed)

    return delays


# ---------------------------------------------------------------------------
# StepperAxis
# ---------------------------------------------------------------------------

class StepperAxis:
    def __init__(self, name, cfg):
        self.name = name
        self.gear_ratio = cfg.get("gear_ratio", 1)
        self.steps_per_rev = cfg.get("steps_per_rev", 200)
        self.microstepping = cfg.get("microstepping", 16)
        self.min_angle = cfg.get("min_angle", 0.0)
        self.max_angle = cfg.get("max_angle", 360.0)
        self.max_speed = cfg.get("max_speed", 10.0)   # deg/s
        self.acceleration = cfg.get("acceleration", 5.0)  # deg/s^2

        self.step_pin = cfg["step_pin"]
        self.dir_pin = cfg["dir_pin"]
        self.enable_pin = cfg["enable_pin"]
        self.home_switch_pin = cfg.get("home_switch_pin", None)
        self.home_switch_enabled = cfg.get("home_switch_enabled", False)
        self.home_offset = cfg.get("home_offset", 0.0)

        self._position_steps = 0
        self._enabled = False
        self._lock = threading.Lock()
        self._stop_event = threading.Event()

        self._setup_pins()

    # ------------------------------------------------------------------
    @property
    def steps_per_degree(self):
        return (self.steps_per_rev * self.microstepping * self.gear_ratio) / 360.0

    @property
    def position_deg(self):
        with self._lock:
            return self._position_steps / self.steps_per_degree

    @property
    def position_steps(self):
        with self._lock:
            return self._position_steps

    # ------------------------------------------------------------------
    def _setup_pins(self):
        _gpio_setup_output(self.step_pin)
        _gpio_setup_output(self.dir_pin)
        _gpio_setup_output(self.enable_pin)

        # Start disabled
        _gpio_write(self.enable_pin, 1)  # HIGH = disabled (active-low)

        if self.home_switch_enabled and self.home_switch_pin is not None:
            _gpio_setup_input_pullup(self.home_switch_pin)

        if SIMULATION:
            print(f"[SIM] {self.name}: pins set up (STEP={self.step_pin} DIR={self.dir_pin} EN={self.enable_pin})")

    def enable(self):
        _gpio_write(self.enable_pin, 0)  # LOW = enabled
        self._enabled = True
        if SIMULATION:
            print(f"[SIM] {self.name}: enabled")

    def disable(self):
        _gpio_write(self.enable_pin, 1)  # HIGH = disabled
        self._enabled = False
        if SIMULATION:
            print(f"[SIM] {self.name}: disabled")

    # ------------------------------------------------------------------
    def step(self, count, direction=1):
        """
        Move count steps in direction (1=CW, -1=CCW).
        Uses pigpio wave generation if available, else RPi.GPIO with sleep.
        """
        if count <= 0:
            return

        self._stop_event.clear()

        # Set direction pin: HIGH=CW, LOW=CCW
        dir_level = 1 if direction >= 0 else 0
        _gpio_write(self.dir_pin, dir_level)
        time.sleep(0.000005)  # direction setup time

        max_step_speed = self.max_speed * self.steps_per_degree
        accel_steps = self.acceleration * self.steps_per_degree
        delays = _build_delay_profile(count, max_step_speed, accel_steps)

        if SIMULATION:
            total_time = sum(delays)
            print(f"[SIM] {self.name}: {count} steps dir={'CW' if direction>=0 else 'CCW'} "
                  f"~{total_time:.2f}s  pos_after={self._position_steps + direction*count}")
            with self._lock:
                self._position_steps += direction * count
            return

        if HAS_PIGPIO:
            self._step_pigpio(count, direction, delays)
        else:
            self._step_gpio(count, direction, delays)

    def _step_gpio(self, count, direction, delays):
        step_pin = self.step_pin
        for i, delay in enumerate(delays):
            if self._stop_event.is_set():
                break
            _gpio_write(step_pin, 1)
            time.sleep(0.000002)
            _gpio_write(step_pin, 0)
            time.sleep(max(delay - 0.000002, 0.000001))
            with self._lock:
                self._position_steps += direction

    def _step_pigpio(self, count, direction, delays):
        pi = _get_pi()
        step_pin = self.step_pin

        # pigpio wave-based stepping — batch into chunks to avoid wave size limits
        CHUNK = 256
        steps_done = 0

        for chunk_start in range(0, count, CHUNK):
            if self._stop_event.is_set():
                break

            chunk_delays = delays[chunk_start: chunk_start + CHUNK]
            pulses = []
            for delay in chunk_delays:
                # HIGH for 2μs, then LOW for remainder
                high_us = 2
                total_us = max(int(delay * 1_000_000), high_us + 1)
                low_us = total_us - high_us

                pulses.append(pigpio.pulse(1 << step_pin, 0, high_us))
                pulses.append(pigpio.pulse(0, 1 << step_pin, low_us))

            pi.wave_clear()
            pi.wave_add_generic(pulses)
            wid = pi.wave_create()
            if wid < 0:
                # Fallback to sleep-based for this chunk
                for delay in chunk_delays:
                    if self._stop_event.is_set():
                        break
                    pi.write(step_pin, 1)
                    time.sleep(0.000002)
                    pi.write(step_pin, 0)
                    time.sleep(max(delay - 0.000002, 0.000001))
                    with self._lock:
                        self._position_steps += direction
                continue

            pi.wave_send_once(wid)
            while pi.wave_tx_busy():
                if self._stop_event.is_set():
                    pi.wave_tx_stop()
                    break
                time.sleep(0.001)

            pi.wave_delete(wid)
            steps_done = min(chunk_start + len(chunk_delays), count)
            with self._lock:
                self._position_steps += direction * len(chunk_delays)

    # ------------------------------------------------------------------
    def move_to(self, angle):
        angle = max(self.min_angle, min(self.max_angle, angle))
        target_steps = int(round(angle * self.steps_per_degree))

        with self._lock:
            current = self._position_steps

        delta = target_steps - current
        if delta == 0:
            return

        direction = 1 if delta > 0 else -1
        self.step(abs(delta), direction)

    # ------------------------------------------------------------------
    def home(self):
        if self.home_switch_enabled and self.home_switch_pin is not None:
            self.enable()
            # Move toward home (negative direction) until switch triggers
            while _gpio_read(self.home_switch_pin) != 0:
                if self._stop_event.is_set():
                    return
                self.step(10, -1)
                time.sleep(0.01)

            with self._lock:
                self._position_steps = int(round(self.home_offset * self.steps_per_degree))

            if SIMULATION:
                print(f"[SIM] {self.name}: homed via switch, offset={self.home_offset}")
        else:
            with self._lock:
                self._position_steps = int(round(self.home_offset * self.steps_per_degree))
            if SIMULATION:
                print(f"[SIM] {self.name}: homed (no switch), position set to {self.home_offset} deg")

    def stop(self):
        self._stop_event.set()

    # ------------------------------------------------------------------
    def get_position(self):
        return self.position_deg

    def get_status(self):
        return {
            "name": self.name,
            "position_deg": round(self.position_deg, 4),
            "position_steps": self.position_steps,
            "enabled": self._enabled,
            "min_angle": self.min_angle,
            "max_angle": self.max_angle,
            "steps_per_degree": round(self.steps_per_degree, 4),
        }


# ---------------------------------------------------------------------------
# AntennaTracker
# ---------------------------------------------------------------------------

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")


class AntennaTracker:
    def __init__(self, config_path=None):
        path = config_path or CONFIG_PATH
        with open(path, "r") as f:
            raw = yaml.safe_load(f)

        cfg = raw["tracker"]
        self.az = StepperAxis("azimuth", cfg["azimuth"])
        self.el = StepperAxis("elevation", cfg["elevation"])
        self.park_az = cfg.get("park_azimuth", 0.0)
        self.park_el = cfg.get("park_elevation", 90.0)
        self.STEPS_PER_DEG_AZ = self.az.steps_per_degree
        self.STEPS_PER_DEG_EL = self.el.steps_per_degree
        self.jog_size_deg = 1.0
        self._config_path = path

    def enable(self):
        self.az.enable()
        self.el.enable()

    def disable(self):
        self.az.disable()
        self.el.disable()

    def goto(self, az, el):
        self.enable()
        # Move both axes concurrently
        t_az = threading.Thread(target=self.az.move_to, args=(az,), daemon=True)
        t_el = threading.Thread(target=self.el.move_to, args=(el,), daemon=True)
        t_az.start()
        t_el.start()
        t_az.join()
        t_el.join()

    def home(self):
        t_az = threading.Thread(target=self.az.home, daemon=True)
        t_el = threading.Thread(target=self.el.home, daemon=True)
        t_az.start()
        t_el.start()
        t_az.join()
        t_el.join()

    def park(self):
        self.goto(self.park_az, self.park_el)

    def stop(self):
        self.az.stop()
        self.el.stop()

    def jog(self, axis, steps, direction):
        ax = self.az if axis == "az" else self.el
        ax.enable()
        d = 1 if direction == "cw" else -1
        ax.step(steps, d)

    def get_status(self):
        return {
            "azimuth": self.az.get_status(),
            "elevation": self.el.get_status(),
            "backend": BACKEND,
            "simulation": SIMULATION,
            "bench_mode": True,
            "steps_per_deg_az": self.STEPS_PER_DEG_AZ,
            "steps_per_deg_el": self.STEPS_PER_DEG_EL,
        }

    def get_config(self):
        return {
            "azimuth": self.az.get_status(),
            "elevation": self.el.get_status(),
            "park_az": self.park_az,
            "park_el": self.park_el,
        }

    @property
    def limits(self):
        return {
            "az_min": self.az.min_angle, "az_max": self.az.max_angle,
            "el_min": self.el.min_angle, "el_max": self.el.max_angle,
        }

    def set_limit(self, axis, limit, value):
        ax = self.az if axis == "az" else self.el
        if limit == "min":
            ax.min_angle = value
        else:
            ax.max_angle = value

    def cleanup(self):
        self.disable()
        _gpio_cleanup()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@click.group()
@click.pass_context
def cli(ctx):
    ctx.ensure_object(dict)
    ctx.obj["tracker"] = AntennaTracker()


@cli.command()
@click.pass_context
def status(ctx):
    st = ctx.obj["tracker"].get_status()
    az = st["azimuth"]
    el = st["elevation"]
    click.echo(f"Backend : {st['backend']}")
    click.echo(f"AZ      : {az['position_deg']:.4f} deg  ({az['position_steps']} steps)  "
               f"enabled={az['enabled']}")
    click.echo(f"EL      : {el['position_deg']:.4f} deg  ({el['position_steps']} steps)  "
               f"enabled={el['enabled']}")


@cli.command()
@click.option("--az", required=True, type=float, help="Target azimuth in degrees")
@click.option("--el", required=True, type=float, help="Target elevation in degrees")
@click.pass_context
def goto(ctx, az, el):
    tracker = ctx.obj["tracker"]
    click.echo(f"Moving to AZ={az} EL={el}")
    tracker.goto(az, el)
    tracker.disable()
    st = tracker.get_status()
    click.echo(f"Done — AZ={st['azimuth']['position_deg']:.4f} EL={st['elevation']['position_deg']:.4f}")


@cli.command(name="home")
@click.pass_context
def home_cmd(ctx):
    tracker = ctx.obj["tracker"]
    click.echo("Homing both axes...")
    tracker.home()
    tracker.disable()
    click.echo("Homed.")


@cli.command()
@click.pass_context
def park(ctx):
    tracker = ctx.obj["tracker"]
    click.echo(f"Parking at AZ={tracker.park_az} EL={tracker.park_el}")
    tracker.park()
    tracker.disable()
    click.echo("Parked.")


@cli.command(name="step")
@click.option("--motor", required=True, type=click.Choice(["az", "el"]),
              help="Which motor to move")
@click.option("--count", required=True, type=int, help="Number of steps")
@click.option("--dir", "direction", default="cw", type=click.Choice(["cw", "ccw"]),
              help="Direction: cw or ccw")
@click.pass_context
def step_cmd(ctx, motor, count, direction):
    tracker = ctx.obj["tracker"]
    axis = tracker.az if motor == "az" else tracker.el
    dir_val = 1 if direction == "cw" else -1
    axis.enable()
    click.echo(f"Stepping {motor} {count} steps {direction.upper()}")
    axis.step(count, dir_val)
    axis.disable()
    click.echo(f"Done — position: {axis.position_deg:.4f} deg")


@cli.command(name="enable")
@click.pass_context
def enable_cmd(ctx):
    ctx.obj["tracker"].enable()
    click.echo("Motors enabled.")


@cli.command(name="disable")
@click.pass_context
def disable_cmd(ctx):
    ctx.obj["tracker"].disable()
    click.echo("Motors disabled.")


if __name__ == "__main__":
    cli()
