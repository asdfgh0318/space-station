"""
Antenna tracker stepper motor controller.

Controls two NEMA 17 steppers via TMC2209 drivers for alt-az dish tracking.
Uses pigpio for hardware-timed pulse generation (jitter-free on RPi).
Falls back to RPi.GPIO with software timing when pigpio is unavailable.
"""

import time
import math
import threading
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

# Try pigpio first (hardware-timed, best for tracking), fall back to GPIO
try:
    import pigpio
    HAS_PIGPIO = True
except ImportError:
    HAS_PIGPIO = False
    try:
        import RPi.GPIO as GPIO
        HAS_GPIO = True
    except ImportError:
        HAS_GPIO = False
        logger.warning("No GPIO library available -- running in simulation mode")


@dataclass
class AxisConfig:
    """Configuration for a single axis (azimuth or elevation)."""
    gear_ratio: int
    steps_per_rev: int
    microstepping: int
    min_angle: float
    max_angle: float
    max_speed: float        # deg/s
    acceleration: float     # deg/s^2
    step_pin: int
    dir_pin: int
    enable_pin: int
    home_switch_pin: int
    home_offset: float
    encoder_i2c_address: int
    encoder_i2c_bus: int

    @property
    def steps_per_degree(self) -> float:
        """Total microsteps to move one degree."""
        total_steps_per_rev = self.steps_per_rev * self.microstepping * self.gear_ratio
        return total_steps_per_rev / 360.0

    @property
    def degrees_per_step(self) -> float:
        return 1.0 / self.steps_per_degree

    @property
    def resolution_arcsec(self) -> float:
        return self.degrees_per_step * 3600.0


@dataclass
class TrackerState:
    """Current state of the tracker."""
    az_position: float = 0.0    # degrees
    el_position: float = 0.0    # degrees
    az_target: float = 0.0
    el_target: float = 0.0
    is_tracking: bool = False
    is_slewing: bool = False
    is_homed: bool = False
    is_parked: bool = False
    motors_enabled: bool = False


class StepperAxis:
    """Controls a single stepper motor axis with acceleration profile."""

    def __init__(self, name: str, config: AxisConfig, pi=None):
        self.name = name
        self.config = config
        self.pi = pi  # pigpio instance
        self.position_steps: int = 0
        self._moving = False
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        self._setup_pins()
        logger.info(
            f"{name} axis: {config.steps_per_degree:.1f} steps/deg, "
            f"resolution {config.resolution_arcsec:.1f} arcsec"
        )

    def _setup_pins(self):
        if self.pi:
            self.pi.set_mode(self.config.step_pin, pigpio.OUTPUT)
            self.pi.set_mode(self.config.dir_pin, pigpio.OUTPUT)
            self.pi.set_mode(self.config.enable_pin, pigpio.OUTPUT)
            self.pi.set_mode(self.config.home_switch_pin, pigpio.INPUT)
            self.pi.set_pull_up_down(self.config.home_switch_pin, pigpio.PUD_UP)
            # Start with motors disabled
            self.pi.write(self.config.enable_pin, 1)  # TMC2209: HIGH = disabled
        elif HAS_GPIO:
            GPIO.setup(self.config.step_pin, GPIO.OUT)
            GPIO.setup(self.config.dir_pin, GPIO.OUT)
            GPIO.setup(self.config.enable_pin, GPIO.OUT)
            GPIO.setup(self.config.home_switch_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.output(self.config.enable_pin, GPIO.HIGH)

    @property
    def position_degrees(self) -> float:
        return self.position_steps / self.config.steps_per_degree

    @position_degrees.setter
    def position_degrees(self, deg: float):
        self.position_steps = int(deg * self.config.steps_per_degree)

    def enable(self):
        if self.pi:
            self.pi.write(self.config.enable_pin, 0)  # LOW = enabled
        elif HAS_GPIO:
            GPIO.output(self.config.enable_pin, GPIO.LOW)

    def disable(self):
        if self.pi:
            self.pi.write(self.config.enable_pin, 1)
        elif HAS_GPIO:
            GPIO.output(self.config.enable_pin, GPIO.HIGH)

    def _step_pulse(self, delay_us: int):
        """Generate a single step pulse."""
        if self.pi:
            self.pi.gpio_trigger(self.config.step_pin, 10, 1)  # 10us pulse
            # pigpio.gpio_trigger is non-blocking, delay handled by caller
        elif HAS_GPIO:
            GPIO.output(self.config.step_pin, GPIO.HIGH)
            time.sleep(0.00001)  # 10us
            GPIO.output(self.config.step_pin, GPIO.LOW)

    def _set_direction(self, forward: bool):
        val = 1 if forward else 0
        if self.pi:
            self.pi.write(self.config.dir_pin, val)
        elif HAS_GPIO:
            GPIO.output(self.config.dir_pin, val if forward else not val)

    def move_to(self, target_deg: float, blocking: bool = True) -> Optional[threading.Thread]:
        """
        Move to target position with trapezoidal acceleration profile.

        Args:
            target_deg: Target position in degrees
            blocking: If True, wait for move to complete

        Returns:
            Thread object if non-blocking, None if blocking
        """
        target_deg = max(self.config.min_angle, min(self.config.max_angle, target_deg))

        if blocking:
            self._execute_move(target_deg)
            return None
        else:
            self._stop_event.clear()
            t = threading.Thread(target=self._execute_move, args=(target_deg,), daemon=True)
            t.start()
            return t

    def _execute_move(self, target_deg: float):
        """Execute a move with trapezoidal velocity profile."""
        with self._lock:
            self._moving = True

            target_steps = int(target_deg * self.config.steps_per_degree)
            delta_steps = target_steps - self.position_steps

            if delta_steps == 0:
                self._moving = False
                return

            self._set_direction(delta_steps > 0)
            time.sleep(0.001)  # Direction setup time

            total_steps = abs(delta_steps)
            step_sign = 1 if delta_steps > 0 else -1

            # Calculate acceleration profile in step domain
            # max_speed in steps/sec
            max_speed_sps = self.config.max_speed * self.config.steps_per_degree
            accel_sps2 = self.config.acceleration * self.config.steps_per_degree

            # Steps to accelerate to max speed
            accel_steps = int(max_speed_sps ** 2 / (2 * accel_sps2))

            if accel_steps > total_steps // 2:
                # Triangular profile -- never reach max speed
                accel_steps = total_steps // 2

            decel_start = total_steps - accel_steps

            # Execute steps
            current_speed = max(accel_sps2 * 0.01, 100)  # Start speed (avoid div/0)

            for step_num in range(total_steps):
                if self._stop_event.is_set():
                    break

                # Calculate delay for this step
                if step_num < accel_steps:
                    # Accelerating
                    current_speed = math.sqrt(2 * accel_sps2 * (step_num + 1))
                    current_speed = min(current_speed, max_speed_sps)
                elif step_num >= decel_start:
                    # Decelerating
                    steps_remaining = total_steps - step_num
                    current_speed = math.sqrt(2 * accel_sps2 * steps_remaining)
                    current_speed = max(current_speed, 100)  # Minimum speed

                delay = 1.0 / current_speed

                self._step_pulse(int(delay * 1e6))
                self.position_steps += step_sign

                # Sleep for step interval (minus pulse time)
                sleep_time = delay - 0.00001
                if sleep_time > 0:
                    time.sleep(sleep_time)

            self._moving = False

    def stop(self):
        """Emergency stop."""
        self._stop_event.set()
        while self._moving:
            time.sleep(0.001)

    def home(self) -> bool:
        """
        Home the axis using limit switch.

        Moves slowly toward home switch, stops when triggered,
        then backs off slightly and sets position.
        """
        logger.info(f"Homing {self.name} axis...")

        # Move toward home at slow speed
        home_speed = 0.5  # deg/s
        step_delay = 1.0 / (home_speed * self.config.steps_per_degree)

        self._set_direction(False)  # Move toward 0
        time.sleep(0.001)

        max_home_steps = int(self.config.max_angle * self.config.steps_per_degree * 1.1)

        for _ in range(max_home_steps):
            if self._stop_event.is_set():
                return False

            # Check home switch
            if self.pi:
                switch_state = self.pi.read(self.config.home_switch_pin)
            elif HAS_GPIO:
                switch_state = GPIO.input(self.config.home_switch_pin)
            else:
                # Simulation: pretend we hit home after some steps
                switch_state = 0

            if switch_state == 0:  # Active low
                # Found home, back off a bit
                self._set_direction(True)
                time.sleep(0.001)
                for _ in range(int(0.5 * self.config.steps_per_degree)):
                    self._step_pulse(int(step_delay * 1e6 * 2))
                    time.sleep(step_delay * 2)

                self.position_steps = int(self.config.home_offset * self.config.steps_per_degree)
                logger.info(f"{self.name} homed at {self.config.home_offset} deg")
                return True

            self._step_pulse(int(step_delay * 1e6))
            self.position_steps -= 1
            time.sleep(step_delay)

        logger.error(f"{self.name} homing failed -- switch not found")
        return False

    @property
    def is_moving(self) -> bool:
        return self._moving


class AntennaTracker:
    """
    Two-axis antenna tracker controller.

    Manages azimuth and elevation axes, provides high-level pointing commands,
    and runs a tracking loop for satellite/celestial source following.
    """

    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = str(Path(__file__).parent / "config.yaml")

        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        self.state = TrackerState()
        self._tracking_thread: Optional[threading.Thread] = None
        self._tracking_stop = threading.Event()
        self._target_callback = None  # Function returning (az, el) for tracking

        # Initialize pigpio if available
        self.pi = None
        if HAS_PIGPIO:
            try:
                self.pi = pigpio.pi()
                if not self.pi.connected:
                    logger.warning("pigpio daemon not running, falling back to GPIO")
                    self.pi = None
            except Exception as e:
                logger.warning(f"pigpio init failed: {e}")
                self.pi = None

        if not self.pi and not HAS_GPIO:
            logger.warning("Running in SIMULATION mode -- no GPIO available")

        # Create axis controllers
        az_cfg = self._parse_axis_config(self.config["tracker"]["azimuth"])
        el_cfg = self._parse_axis_config(self.config["tracker"]["elevation"])

        self.az = StepperAxis("azimuth", az_cfg, self.pi)
        self.el = StepperAxis("elevation", el_cfg, self.pi)

    def _parse_axis_config(self, cfg: dict) -> AxisConfig:
        return AxisConfig(
            gear_ratio=cfg["gear_ratio"],
            steps_per_rev=cfg["steps_per_rev"],
            microstepping=cfg["microstepping"],
            min_angle=cfg["min_angle"],
            max_angle=cfg["max_angle"],
            max_speed=cfg["max_speed"],
            acceleration=cfg["acceleration"],
            step_pin=cfg["step_pin"],
            dir_pin=cfg["dir_pin"],
            enable_pin=cfg["enable_pin"],
            home_switch_pin=cfg["home_switch_pin"],
            home_offset=cfg["home_offset"],
            encoder_i2c_address=cfg["encoder_i2c_address"],
            encoder_i2c_bus=cfg["encoder_i2c_bus"],
        )

    def enable_motors(self):
        self.az.enable()
        self.el.enable()
        self.state.motors_enabled = True
        logger.info("Motors enabled")

    def disable_motors(self):
        self.az.disable()
        self.el.disable()
        self.state.motors_enabled = False
        logger.info("Motors disabled")

    def home(self) -> bool:
        """Home both axes sequentially (elevation first, then azimuth)."""
        self.enable_motors()

        el_ok = self.el.home()
        if not el_ok:
            return False

        az_ok = self.az.home()
        if not az_ok:
            return False

        self.state.is_homed = True
        self._update_state()
        logger.info("Both axes homed successfully")
        return True

    def goto(self, az: float, el: float, blocking: bool = True):
        """
        Slew to a specific azimuth/elevation position.

        Args:
            az: Target azimuth (0-360 degrees, 0=North, 90=East)
            el: Target elevation (0-90 degrees, 0=horizon)
            blocking: Wait for move to complete
        """
        self.state.az_target = az
        self.state.el_target = el
        self.state.is_slewing = True

        logger.info(f"Slewing to AZ={az:.2f} EL={el:.2f}")

        if blocking:
            # Move both axes simultaneously using threads
            az_thread = self.az.move_to(az, blocking=False)
            el_thread = self.el.move_to(el, blocking=False)
            if az_thread:
                az_thread.join()
            if el_thread:
                el_thread.join()
        else:
            self.az.move_to(az, blocking=False)
            self.el.move_to(el, blocking=False)

        self.state.is_slewing = False
        self._update_state()

    def park(self):
        """Park the dish in safe position."""
        park_az = self.config["tracker"]["park_azimuth"]
        park_el = self.config["tracker"]["park_elevation"]
        logger.info(f"Parking at AZ={park_az} EL={park_el}")
        self.stop_tracking()
        self.goto(park_az, park_el)
        self.disable_motors()
        self.state.is_parked = True

    def stop(self):
        """Emergency stop all motion."""
        self.stop_tracking()
        self.az.stop()
        self.el.stop()
        self.state.is_slewing = False
        self._update_state()
        logger.warning("Emergency stop!")

    def start_tracking(self, target_callback):
        """
        Start continuous tracking of a moving target.

        Args:
            target_callback: Function that returns (az, el) tuple
                             for the current target position.
                             Called repeatedly at tracking_interval.
        """
        self.stop_tracking()
        self._target_callback = target_callback
        self._tracking_stop.clear()
        self._tracking_thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self._tracking_thread.start()
        self.state.is_tracking = True
        logger.info("Tracking started")

    def stop_tracking(self):
        """Stop the tracking loop."""
        if self._tracking_thread and self._tracking_thread.is_alive():
            self._tracking_stop.set()
            self._tracking_thread.join(timeout=5)
            self.state.is_tracking = False
            logger.info("Tracking stopped")

    def _tracking_loop(self):
        """Main tracking loop -- updates position at regular intervals."""
        interval = self.config["tracker"]["tracking_interval"]
        tolerance = self.config["tracker"]["position_tolerance"]

        while not self._tracking_stop.is_set():
            try:
                target_az, target_el = self._target_callback()

                # Check if we need to move
                az_error = abs(target_az - self.az.position_degrees)
                el_error = abs(target_el - self.el.position_degrees)

                if az_error > tolerance or el_error > tolerance:
                    self.state.az_target = target_az
                    self.state.el_target = target_el

                    # Move both axes (non-blocking, let them run in parallel)
                    self.az.move_to(target_az, blocking=False)
                    self.el.move_to(target_el, blocking=False)

            except Exception as e:
                logger.error(f"Tracking error: {e}")

            self._tracking_stop.wait(interval)

    def _update_state(self):
        """Update the tracker state from axis positions."""
        self.state.az_position = self.az.position_degrees
        self.state.el_position = self.el.position_degrees

    def get_position(self) -> tuple[float, float]:
        """Get current (azimuth, elevation) in degrees."""
        self._update_state()
        return (self.state.az_position, self.state.el_position)

    def get_status(self) -> dict:
        """Get full tracker status as a dictionary."""
        self._update_state()
        return {
            "az_position": round(self.state.az_position, 4),
            "el_position": round(self.state.el_position, 4),
            "az_target": round(self.state.az_target, 4),
            "el_target": round(self.state.el_target, 4),
            "is_tracking": self.state.is_tracking,
            "is_slewing": self.state.is_slewing,
            "is_homed": self.state.is_homed,
            "is_parked": self.state.is_parked,
            "motors_enabled": self.state.motors_enabled,
            "az_resolution_arcsec": round(self.az.config.resolution_arcsec, 2),
            "el_resolution_arcsec": round(self.el.config.resolution_arcsec, 2),
        }

    def cleanup(self):
        """Clean up GPIO resources."""
        self.stop()
        self.disable_motors()
        if self.pi:
            self.pi.stop()
        elif HAS_GPIO:
            GPIO.cleanup()


# --- CLI for testing ---

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Antenna tracker motor test")
    parser.add_argument("--config", default=None, help="Path to config.yaml")
    parser.add_argument("--goto", nargs=2, type=float, metavar=("AZ", "EL"), help="Slew to position")
    parser.add_argument("--home", action="store_true", help="Home both axes")
    parser.add_argument("--park", action="store_true", help="Park the dish")
    parser.add_argument("--status", action="store_true", help="Print current status")
    args = parser.parse_args()

    tracker = AntennaTracker(args.config)

    try:
        if args.home:
            tracker.home()
        elif args.goto:
            tracker.enable_motors()
            tracker.goto(args.goto[0], args.goto[1])
        elif args.park:
            tracker.park()

        if args.status or not any([args.home, args.goto, args.park]):
            import json
            print(json.dumps(tracker.get_status(), indent=2))
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        tracker.cleanup()
