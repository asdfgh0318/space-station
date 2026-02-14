"""
RTL-SDR IQ capture wrapper.

Handles SDR device management, sample capture, and IQ data recording.
Supports both real-time streaming and file-based capture for long integrations.
"""

import time
import logging
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional, Generator

import numpy as np

logger = logging.getLogger(__name__)

try:
    from rtlsdr import RtlSdr
    HAS_RTLSDR = True
except ImportError:
    HAS_RTLSDR = False
    logger.warning("pyrtlsdr not installed -- SDR functions unavailable")


@dataclass
class CaptureConfig:
    """SDR capture parameters."""
    center_freq: float      # Hz
    sample_rate: float      # Hz
    gain: float             # dB
    num_samples: int = 262144  # Per read (power of 2)
    device_index: int = 0


class SDRDevice:
    """RTL-SDR device wrapper with context manager support."""

    def __init__(self, config: CaptureConfig):
        self.config = config
        self.sdr: Optional[RtlSdr] = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        self.close()

    def open(self):
        if not HAS_RTLSDR:
            logger.error("pyrtlsdr not available")
            return

        self.sdr = RtlSdr(self.config.device_index)
        self.sdr.sample_rate = self.config.sample_rate
        self.sdr.center_freq = self.config.center_freq
        self.sdr.gain = self.config.gain

        logger.info(
            f"SDR opened: freq={self.config.center_freq / 1e6:.3f} MHz, "
            f"rate={self.config.sample_rate / 1e6:.1f} MHz, "
            f"gain={self.config.gain} dB"
        )

    def close(self):
        if self.sdr:
            self.sdr.close()
            self.sdr = None

    def read_samples(self, num_samples: Optional[int] = None) -> np.ndarray:
        """Read a block of IQ samples. Returns complex64 array."""
        if not self.sdr:
            raise RuntimeError("SDR not opened")

        n = num_samples or self.config.num_samples
        samples = self.sdr.read_samples(n)
        return np.array(samples, dtype=np.complex64)

    def stream(self, duration_sec: float) -> Generator[np.ndarray, None, None]:
        """
        Stream IQ samples for a given duration.

        Yields blocks of complex64 samples.
        """
        if not self.sdr:
            raise RuntimeError("SDR not opened")

        total_samples = int(duration_sec * self.config.sample_rate)
        samples_read = 0
        block_size = self.config.num_samples

        while samples_read < total_samples:
            remaining = total_samples - samples_read
            n = min(block_size, remaining)
            yield self.read_samples(n)
            samples_read += n


def capture_to_file(
    config: CaptureConfig,
    duration_sec: float,
    output_path: str,
    format: str = "cf32",
) -> dict:
    """
    Capture IQ data to a binary file.

    Args:
        config: SDR configuration
        duration_sec: Recording duration in seconds
        output_path: Path for output file
        format: 'cf32' (complex float32) or 'cs8' (complex int8)

    Returns:
        Metadata dict with capture parameters
    """
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    metadata = {
        "center_freq": config.center_freq,
        "sample_rate": config.sample_rate,
        "gain": config.gain,
        "duration": duration_sec,
        "format": format,
        "start_time": datetime.now(timezone.utc).isoformat(),
        "file": str(output),
    }

    logger.info(f"Recording {duration_sec}s to {output}")
    start = time.time()
    total_samples = 0

    with SDRDevice(config) as sdr:
        with open(output, "wb") as f:
            for block in sdr.stream(duration_sec):
                if format == "cf32":
                    f.write(block.tobytes())
                elif format == "cs8":
                    # Convert complex float to complex int8
                    iq = np.empty(len(block) * 2, dtype=np.int8)
                    iq[0::2] = np.clip(block.real * 127, -128, 127).astype(np.int8)
                    iq[1::2] = np.clip(block.imag * 127, -128, 127).astype(np.int8)
                    f.write(iq.tobytes())

                total_samples += len(block)

    elapsed = time.time() - start
    metadata["end_time"] = datetime.now(timezone.utc).isoformat()
    metadata["total_samples"] = total_samples
    metadata["actual_duration"] = elapsed

    logger.info(f"Captured {total_samples} samples in {elapsed:.1f}s")
    return metadata


def load_iq_file(
    path: str,
    sample_rate: float,
    format: str = "cf32",
    offset_samples: int = 0,
    num_samples: Optional[int] = None,
) -> np.ndarray:
    """
    Load IQ data from a binary file.

    Args:
        path: Path to IQ file
        sample_rate: Sample rate (for metadata, not used in loading)
        format: 'cf32' or 'cs8'
        offset_samples: Skip this many samples from start
        num_samples: Read this many samples (None = all)

    Returns:
        Complex64 numpy array
    """
    if format == "cf32":
        dtype = np.complex64
        bytes_per_sample = 8
    elif format == "cs8":
        dtype = np.int8
        bytes_per_sample = 2
    else:
        raise ValueError(f"Unknown format: {format}")

    with open(path, "rb") as f:
        if offset_samples > 0:
            f.seek(offset_samples * bytes_per_sample)

        if num_samples:
            raw = f.read(num_samples * bytes_per_sample)
        else:
            raw = f.read()

    if format == "cf32":
        return np.frombuffer(raw, dtype=np.complex64)
    elif format == "cs8":
        data = np.frombuffer(raw, dtype=np.int8).astype(np.float32)
        return (data[0::2] + 1j * data[1::2]).astype(np.complex64) / 127.0


# --- CLI ---

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="SDR IQ capture")
    parser.add_argument("--freq", type=float, required=True, help="Center frequency in MHz")
    parser.add_argument("--rate", type=float, default=2.4, help="Sample rate in MHz")
    parser.add_argument("--gain", type=float, default=40.0, help="Gain in dB")
    parser.add_argument("--duration", type=float, default=10.0, help="Duration in seconds")
    parser.add_argument("--output", default="capture.cf32", help="Output file")
    args = parser.parse_args()

    config = CaptureConfig(
        center_freq=args.freq * 1e6,
        sample_rate=args.rate * 1e6,
        gain=args.gain,
    )

    meta = capture_to_file(config, args.duration, args.output)
    print(f"Saved: {meta['file']}")
    print(f"Samples: {meta['total_samples']}")
