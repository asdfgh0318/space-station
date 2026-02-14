"""
LNB (Low Noise Block downconverter) control.

Handles:
- Bias-T voltage control (13V/18V) for LNB power and polarization selection
- 22kHz tone generation for high/low band switching
- DiSEqC commands (future)
- IF frequency calculation from RF frequency and LO

For satellite TV LNBs used in radio astronomy:
- 13V = Vertical polarization, 18V = Horizontal polarization
- No 22kHz tone = Low band (LO = 9.75 GHz for Ku-band)
- 22kHz tone = High band (LO = 10.6 GHz for Ku-band)
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

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


@dataclass
class LNBConfig:
    """LNB hardware configuration."""
    model: str
    type: str           # "PLL" or "DRO"
    lo_low: float       # Hz -- low band local oscillator
    lo_high: float      # Hz -- high band local oscillator
    switch_freq: float  # Hz -- boundary between low and high band
    noise_figure: float # dB


@dataclass
class LNBState:
    """Current LNB operating state."""
    powered: bool = False
    voltage: float = 0.0       # 0, 13, or 18
    tone_22khz: bool = False   # False = low band, True = high band
    polarization: str = "off"  # "vertical", "horizontal", "off"
    band: str = "low"          # "low" or "high"
    lo_frequency: float = 0.0  # Current LO frequency in Hz


class LNBController:
    """
    Controls LNB power and band selection.

    Hardware options:
    1. GPIO-controlled relay/MOSFET for 13V/18V switching
    2. External bias-T with voltage selector
    3. Satellite TV switch (DiSEqC)

    For simplest setup: Use a commercial bias-T that provides 13V or 18V
    to the coax, controlled by GPIO switching between two voltage rails.
    """

    # GPIO pins for LNB control (configurable)
    POWER_PIN = 16          # Enable/disable LNB power
    VOLTAGE_SELECT_PIN = 20  # Low = 13V, High = 18V
    TONE_PIN = 21           # 22kHz tone output (needs hardware oscillator)

    def __init__(self, config_path: str = None, pi=None):
        if config_path is None:
            config_path = str(Path(__file__).parent.parent / "tracker" / "config.yaml")

        with open(config_path) as f:
            cfg = yaml.safe_load(f)

        self.lnb_configs: dict[str, LNBConfig] = {}
        for name, lnb_cfg in cfg.get("lnb", {}).items():
            self.lnb_configs[name] = LNBConfig(
                model=lnb_cfg.get("model", name),
                type=lnb_cfg.get("type", "PLL"),
                lo_low=lnb_cfg["lo_low"],
                lo_high=lnb_cfg["lo_high"],
                switch_freq=lnb_cfg.get("switch_freq", 11700e6),
                noise_figure=lnb_cfg.get("noise_figure", 0.5),
            )

        self.state = LNBState()
        self.pi = pi
        self._setup_pins()

    def _setup_pins(self):
        if self.pi:
            self.pi.set_mode(self.POWER_PIN, pigpio.OUTPUT)
            self.pi.set_mode(self.VOLTAGE_SELECT_PIN, pigpio.OUTPUT)
            self.pi.set_mode(self.TONE_PIN, pigpio.OUTPUT)
            self.pi.write(self.POWER_PIN, 0)  # Off initially
        elif HAS_GPIO:
            GPIO.setup(self.POWER_PIN, GPIO.OUT, initial=GPIO.LOW)
            GPIO.setup(self.VOLTAGE_SELECT_PIN, GPIO.OUT, initial=GPIO.LOW)
            GPIO.setup(self.TONE_PIN, GPIO.OUT, initial=GPIO.LOW)

    def power_on(self, voltage: float = 18.0):
        """
        Power on the LNB at specified voltage.

        Args:
            voltage: 13.0 for vertical pol, 18.0 for horizontal pol
        """
        if voltage not in (13.0, 18.0):
            raise ValueError("Voltage must be 13.0 (V-pol) or 18.0 (H-pol)")

        high_voltage = voltage >= 18.0

        if self.pi:
            self.pi.write(self.VOLTAGE_SELECT_PIN, 1 if high_voltage else 0)
            self.pi.write(self.POWER_PIN, 1)
        elif HAS_GPIO:
            GPIO.output(self.VOLTAGE_SELECT_PIN, GPIO.HIGH if high_voltage else GPIO.LOW)
            GPIO.output(self.POWER_PIN, GPIO.HIGH)
        else:
            logger.info(f"[SIM] LNB power ON at {voltage}V")

        self.state.powered = True
        self.state.voltage = voltage
        self.state.polarization = "horizontal" if high_voltage else "vertical"
        logger.info(f"LNB powered at {voltage}V ({self.state.polarization})")

    def power_off(self):
        """Turn off LNB power."""
        if self.pi:
            self.pi.write(self.POWER_PIN, 0)
            self.pi.write(self.TONE_PIN, 0)
        elif HAS_GPIO:
            GPIO.output(self.POWER_PIN, GPIO.LOW)
            GPIO.output(self.TONE_PIN, GPIO.LOW)
        else:
            logger.info("[SIM] LNB power OFF")

        self.state.powered = False
        self.state.voltage = 0
        self.state.polarization = "off"
        self.state.tone_22khz = False
        self.state.band = "low"
        logger.info("LNB powered off")

    def set_tone(self, enable: bool):
        """
        Enable/disable 22kHz tone for band selection.

        Note: The actual 22kHz tone generation needs a hardware oscillator
        circuit on the GPIO pin, or use a dedicated satellite switch.
        pigpio can generate the tone directly using hardware PWM.
        """
        if self.pi:
            if enable:
                # pigpio can generate 22kHz directly!
                self.pi.hardware_PWM(self.TONE_PIN, 22000, 500000)  # 22kHz, 50% duty
            else:
                self.pi.hardware_PWM(self.TONE_PIN, 0, 0)
        elif HAS_GPIO:
            # Software PWM fallback (less precise but works)
            if enable:
                logger.warning("22kHz tone via software PWM -- consider pigpio for accuracy")
            # Would need a thread-based PWM here
        else:
            logger.info(f"[SIM] 22kHz tone {'ON' if enable else 'OFF'}")

        self.state.tone_22khz = enable
        self.state.band = "high" if enable else "low"
        logger.info(f"22kHz tone {'enabled' if enable else 'disabled'} (band: {self.state.band})")

    def configure_for_frequency(
        self,
        rf_freq_hz: float,
        lnb_name: str = "inverto_ku_pll",
        polarization: str = "horizontal",
    ) -> float:
        """
        Configure LNB for a specific RF frequency and return the IF frequency.

        Automatically selects the correct band (LO) and polarization voltage.

        Args:
            rf_freq_hz: Target RF frequency in Hz
            lnb_name: Name of LNB config to use
            polarization: "horizontal" (18V) or "vertical" (13V)

        Returns:
            IF frequency in Hz (what the SDR should be tuned to)
        """
        if lnb_name not in self.lnb_configs:
            raise ValueError(f"Unknown LNB: {lnb_name}. Available: {list(self.lnb_configs.keys())}")

        lnb = self.lnb_configs[lnb_name]

        # Select band based on RF frequency
        if rf_freq_hz < lnb.switch_freq:
            lo = lnb.lo_low
            use_tone = False
        else:
            lo = lnb.lo_high
            use_tone = True

        if_freq = rf_freq_hz - lo

        # Check IF is within SDR range
        if if_freq < 0:
            raise ValueError(
                f"IF frequency {if_freq / 1e6:.1f} MHz is negative! "
                f"RF {rf_freq_hz / 1e6:.1f} MHz is below LO {lo / 1e6:.1f} MHz"
            )
        if if_freq > 1766e6:  # RTL-SDR max
            logger.warning(
                f"IF frequency {if_freq / 1e6:.1f} MHz exceeds RTL-SDR range (1766 MHz). "
                f"May need different LO or SDR."
            )

        # Apply settings
        voltage = 18.0 if polarization == "horizontal" else 13.0
        self.power_on(voltage)
        self.set_tone(use_tone)

        self.state.lo_frequency = lo

        logger.info(
            f"LNB configured: RF={rf_freq_hz / 1e6:.3f} MHz → "
            f"IF={if_freq / 1e6:.3f} MHz (LO={lo / 1e6:.0f} MHz, "
            f"band={'high' if use_tone else 'low'}, pol={polarization})"
        )

        return if_freq

    def rf_to_if(self, rf_freq_hz: float) -> float:
        """Convert RF frequency to IF using current LO setting."""
        return rf_freq_hz - self.state.lo_frequency

    def if_to_rf(self, if_freq_hz: float) -> float:
        """Convert IF frequency to RF using current LO setting."""
        return if_freq_hz + self.state.lo_frequency

    def get_status(self) -> dict:
        return {
            "powered": self.state.powered,
            "voltage": self.state.voltage,
            "polarization": self.state.polarization,
            "band": self.state.band,
            "tone_22khz": self.state.tone_22khz,
            "lo_frequency_mhz": self.state.lo_frequency / 1e6,
        }


# Convenience functions for common setups

def setup_12ghz_maser(lnb: LNBController) -> float:
    """
    Configure for 12.178 GHz methanol maser observation.

    Returns IF frequency for SDR tuning.
    """
    # 12.178 GHz methanol maser (Class II)
    rf = 12.178e9
    return lnb.configure_for_frequency(rf, "inverto_ku_pll", "horizontal")


def setup_satellite_tv_test(lnb: LNBController, transponder_freq_mhz: float = 11778.0) -> float:
    """
    Configure for satellite TV transponder (signal test).

    Default: Astra 19.2E, transponder at 11778 MHz (strong, easy to find).
    """
    rf = transponder_freq_mhz * 1e6
    return lnb.configure_for_frequency(rf, "inverto_ku_pll", "horizontal")


# --- CLI ---

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="LNB control")
    parser.add_argument("--freq", type=float, help="RF frequency in GHz to configure for")
    parser.add_argument("--lnb", default="inverto_ku_pll", help="LNB config name")
    parser.add_argument("--pol", default="horizontal", choices=["horizontal", "vertical"])
    parser.add_argument("--off", action="store_true", help="Power off LNB")
    parser.add_argument("--maser", action="store_true", help="Configure for 12.2 GHz maser")
    args = parser.parse_args()

    ctrl = LNBController()

    if args.off:
        ctrl.power_off()
    elif args.maser:
        if_freq = setup_12ghz_maser(ctrl)
        print(f"Tune SDR to: {if_freq / 1e6:.3f} MHz")
    elif args.freq:
        if_freq = ctrl.configure_for_frequency(args.freq * 1e9, args.lnb, args.pol)
        print(f"Tune SDR to: {if_freq / 1e6:.3f} MHz")
    else:
        print(ctrl.get_status())
