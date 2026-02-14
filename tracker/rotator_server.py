"""
EasyComm2 / rotctld compatible TCP server for antenna rotator control.

Allows Gpredict, SatDump, and other Hamlib-compatible software to control
the antenna tracker over a TCP socket.

EasyComm2 Protocol:
    AZxxx.x ELyyy.y    - Set target position
    AZ EL               - Query current position (response: AZ=xxx.x EL=yyy.y)
    ML/MR/MU/MD         - Move left/right/up/down
    SA                  - Stop azimuth
    SE                  - Stop elevation
    VE                  - Request version
    IP                  - Query position

Hamlib rotctld protocol (subset):
    p                   - Get position
    P <az> <el>         - Set position
    S                   - Stop
    q                   - Quit connection

Usage:
    python rotator_server.py [--port 4533] [--config config.yaml]

    Then in Gpredict: Edit → Preferences → Interfaces → Rotators
    Add new: Host=localhost, Port=4533, Type=EasyComm2
"""

import asyncio
import logging
import signal
from pathlib import Path
from typing import Optional

from tracker.controller import AntennaTracker

logger = logging.getLogger(__name__)

DEFAULT_PORT = 4533  # Standard rotctld port


class RotatorProtocol(asyncio.Protocol):
    """Handles a single client connection."""

    def __init__(self, tracker: AntennaTracker):
        self.tracker = tracker
        self.transport: Optional[asyncio.Transport] = None
        self.buffer = b""
        self.peer = None

    def connection_made(self, transport: asyncio.Transport):
        self.transport = transport
        self.peer = transport.get_extra_info("peername")
        logger.info(f"Client connected: {self.peer}")

    def connection_lost(self, exc):
        logger.info(f"Client disconnected: {self.peer}")

    def data_received(self, data: bytes):
        self.buffer += data

        while b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            line = line.strip().decode("ascii", errors="ignore")
            if line:
                response = self._handle_command(line)
                if response is not None:
                    self.transport.write((response + "\n").encode("ascii"))

    def _handle_command(self, cmd: str) -> Optional[str]:
        """Parse and execute a rotator command."""
        cmd = cmd.strip()
        logger.debug(f"Command: '{cmd}'")

        # EasyComm2: Position set "AZxxx.x ELyyy.y"
        if cmd.startswith("AZ") and "EL" in cmd:
            parts = cmd.split()
            try:
                az = el = None
                for part in parts:
                    if part.startswith("AZ"):
                        val = part[2:]
                        if val:
                            az = float(val)
                    elif part.startswith("EL"):
                        val = part[2:]
                        if val:
                            el = float(val)

                if az is not None and el is not None:
                    # Set target position
                    self.tracker.goto(az, el, blocking=False)
                    return f"RPRT 0"
                else:
                    # Query position
                    az_pos, el_pos = self.tracker.get_position()
                    return f"AZ{az_pos:.1f} EL{el_pos:.1f}"
            except ValueError:
                return "RPRT -1"

        # EasyComm2: Query position
        if cmd in ("AZ", "AZ EL", "IP"):
            az, el = self.tracker.get_position()
            return f"AZ{az:.1f} EL{el:.1f}"

        # EasyComm2: Stop
        if cmd in ("SA", "SE", "SA SE"):
            self.tracker.stop()
            return "RPRT 0"

        # EasyComm2: Version
        if cmd == "VE":
            return "space-station-rotator v1.0"

        # Hamlib rotctld: Get position
        if cmd == "p" or cmd == "\\get_pos":
            az, el = self.tracker.get_position()
            return f"{az:.6f}\n{el:.6f}"

        # Hamlib rotctld: Set position
        if cmd.startswith("P ") or cmd.startswith("\\set_pos "):
            try:
                parts = cmd.split()
                az = float(parts[1])
                el = float(parts[2])
                self.tracker.goto(az, el, blocking=False)
                return "RPRT 0"
            except (IndexError, ValueError):
                return "RPRT -1"

        # Hamlib rotctld: Stop
        if cmd == "S" or cmd == "\\stop":
            self.tracker.stop()
            return "RPRT 0"

        # Hamlib rotctld: Get info
        if cmd == "_" or cmd == "\\get_info":
            return "space-station-rotator"

        # Hamlib rotctld: Dump state
        if cmd == "1" or cmd == "\\dump_state":
            return (
                "0\n"          # Protocol version
                "2\n"          # Rotator model (EasyComm2 = 2)
                "0\n"          # Write delay
                "0.0 360.0\n"  # AZ min/max
                "0.0 90.0\n"   # EL min/max
                "0\n"          # Status flags
            )

        # Hamlib: Quit
        if cmd == "q" or cmd == "\\quit":
            self.transport.close()
            return None

        # Unknown command
        logger.debug(f"Unknown command: '{cmd}'")
        return "RPRT -4"


async def run_server(tracker: AntennaTracker, host: str = "0.0.0.0", port: int = DEFAULT_PORT):
    """Start the rotator control TCP server."""
    loop = asyncio.get_event_loop()

    server = await loop.create_server(
        lambda: RotatorProtocol(tracker),
        host, port
    )

    addr = server.sockets[0].getsockname()
    logger.info(f"Rotator server listening on {addr[0]}:{addr[1]}")
    logger.info(f"Connect Gpredict: Host={addr[0]}, Port={addr[1]}, Type=EasyComm2")

    async with server:
        await server.serve_forever()


def main():
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s: %(message)s"
    )

    parser = argparse.ArgumentParser(description="Rotator control server (EasyComm2/rotctld)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"TCP port (default: {DEFAULT_PORT})")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address")
    parser.add_argument("--config", default=None, help="Path to tracker config.yaml")
    args = parser.parse_args()

    tracker = AntennaTracker(args.config)

    # Handle shutdown
    def shutdown(sig, frame):
        logger.info("Shutting down...")
        tracker.cleanup()
        raise SystemExit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        tracker.enable_motors()
        asyncio.run(run_server(tracker, args.host, args.port))
    finally:
        tracker.cleanup()


if __name__ == "__main__":
    main()
