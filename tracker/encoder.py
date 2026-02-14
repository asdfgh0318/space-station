"""
AS5600 magnetic rotary encoder driver.

The AS5600 is a 12-bit contactless magnetic position sensor that
communicates via I2C. We use two of them for closed-loop position
feedback on both tracker axes.

Hardware: 6mm diametral magnet on each axis shaft, AS5600 board nearby.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import smbus2
    HAS_I2C = True
except ImportError:
    HAS_I2C = False
    logger.warning("smbus2 not installed -- encoder functions unavailable")


# AS5600 registers
RAW_ANGLE_H = 0x0C
RAW_ANGLE_L = 0x0D
ANGLE_H = 0x0E
ANGLE_L = 0x0F
STATUS = 0x0B
AGC = 0x1A
MAGNITUDE_H = 0x1B
MAGNITUDE_L = 0x1C
CONF_H = 0x07
CONF_L = 0x08


class AS5600:
    """AS5600 12-bit magnetic encoder driver."""

    def __init__(self, bus: int = 1, address: int = 0x36):
        self.address = address
        self.bus_num = bus
        self.bus: Optional[smbus2.SMBus] = None
        self._offset = 0.0  # degrees

        if HAS_I2C:
            try:
                self.bus = smbus2.SMBus(bus)
                logger.info(f"AS5600 on bus {bus} addr 0x{address:02X}")
            except Exception as e:
                logger.warning(f"I2C init failed: {e}")
                self.bus = None

    def read_raw_angle(self) -> int:
        """Read raw 12-bit angle value (0-4095)."""
        if not self.bus:
            return 0
        h = self.bus.read_byte_data(self.address, RAW_ANGLE_H)
        l = self.bus.read_byte_data(self.address, RAW_ANGLE_L)
        return ((h & 0x0F) << 8) | l

    def read_angle_degrees(self) -> float:
        """Read angle in degrees (0-360), with offset applied."""
        raw = self.read_raw_angle()
        deg = (raw / 4096.0) * 360.0
        return (deg - self._offset) % 360.0

    def set_zero(self):
        """Set current position as zero reference."""
        self._offset = (self.read_raw_angle() / 4096.0) * 360.0
        logger.info(f"Encoder zero set at offset {self._offset:.2f} deg")

    def read_status(self) -> dict:
        """Read magnet status and signal strength."""
        if not self.bus:
            return {"connected": False}

        status = self.bus.read_byte_data(self.address, STATUS)
        agc = self.bus.read_byte_data(self.address, AGC)
        mag_h = self.bus.read_byte_data(self.address, MAGNITUDE_H)
        mag_l = self.bus.read_byte_data(self.address, MAGNITUDE_L)
        magnitude = ((mag_h & 0x0F) << 8) | mag_l

        magnet_detected = bool(status & 0x20)
        magnet_too_strong = bool(status & 0x08)
        magnet_too_weak = bool(status & 0x10)

        return {
            "connected": True,
            "magnet_detected": magnet_detected,
            "magnet_too_strong": magnet_too_strong,
            "magnet_too_weak": magnet_too_weak,
            "agc": agc,
            "magnitude": magnitude,
            "angle_deg": self.read_angle_degrees(),
        }

    def close(self):
        if self.bus:
            self.bus.close()


if __name__ == "__main__":
    import argparse
    import time

    parser = argparse.ArgumentParser(description="AS5600 encoder test")
    parser.add_argument("--bus", type=int, default=1)
    parser.add_argument("--addr", type=lambda x: int(x, 0), default=0x36)
    parser.add_argument("--watch", action="store_true", help="Continuously print angle")
    args = parser.parse_args()

    enc = AS5600(args.bus, args.addr)
    status = enc.read_status()
    print(f"Status: {status}")

    if args.watch:
        try:
            while True:
                print(f"\rAngle: {enc.read_angle_degrees():>8.2f} deg", end="", flush=True)
                time.sleep(0.1)
        except KeyboardInterrupt:
            print()

    enc.close()
