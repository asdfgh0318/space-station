"""
Maser observation pipeline.

Implements Eduard Mol's method for detecting methanol and water masers
with small dishes and consumer SDR equipment:

1. Long integration IQ capture (30-60 min per source)
2. High-resolution FFT (128k points → ~18 Hz/bin at 2.4 MHz)
3. Spectral averaging (thousands of spectra → noise reduction)
4. ON/OFF source bandpass calibration
5. Frequency → LSR velocity conversion
6. Detection analysis and plotting

Reference: Mol, E. (2023). "Mini Maser Telescope", EUCARA 2023.
"""

import json
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

import numpy as np

from sdr.capture import SDRDevice, CaptureConfig, capture_to_file, load_iq_file
from sdr.spectral import (
    SpectralConfig,
    compute_spectrum,
    bandpass_calibrate,
    smooth_spectrum,
    extract_baseline,
    estimate_rms,
    power_to_db,
)

logger = logging.getLogger(__name__)


# Maser rest frequencies (Hz)
MASER_LINES = {
    "CH3OH_12GHz": 12.178e9,    # Class II methanol maser
    "CH3OH_6GHz": 6.668e9,      # Class II methanol maser
    "H2O_22GHz": 22.235e9,      # Water maser
    "OH_1612": 1.6122e9,        # OH maser (satellite line)
    "OH_1665": 1.6654e9,        # OH maser (main line)
    "OH_1667": 1.6674e9,        # OH maser (main line)
    "OH_1720": 1.7205e9,        # OH maser (satellite line)
}

# Speed of light
C_KMS = 299792.458


@dataclass
class MaserObservation:
    """Complete maser observation result."""
    source_name: str
    molecule: str
    rest_freq_hz: float
    obs_time: str
    integration_sec: float
    n_spectra: int

    # Frequency/velocity axes
    freqs_hz: np.ndarray          # IF frequencies
    rf_freqs_hz: np.ndarray       # Sky frequencies (IF + LO)
    velocities_kms: np.ndarray    # LSR velocities

    # Spectra
    on_spectrum: np.ndarray       # Calibrated ON-source
    off_spectrum: np.ndarray      # Raw OFF-source
    calibrated: np.ndarray        # (ON-OFF)/OFF

    # Detection stats
    rms_noise: float
    peak_snr: float
    peak_velocity: float
    detected: bool


def observe_maser(
    source_name: str,
    rest_freq_hz: float,
    if_center_hz: float,
    lo_freq_hz: float,
    sample_rate: float = 2.4e6,
    gain: float = 30.0,
    integration_sec: float = 1800,
    fft_size: int = 131072,
    data_dir: str = "data/spectra",
    ra_deg: float = 0.0,
    dec_deg: float = 0.0,
    site=None,
    capture_off: bool = True,
) -> MaserObservation:
    """
    Execute a complete maser observation sequence.

    Follows ON/OFF method:
    1. Record ON-source data for integration_sec
    2. Offset dish and record OFF-source for same duration
    3. Calibrate: (ON - OFF) / OFF
    4. Convert to LSR velocity

    Args:
        source_name: Target name (for logging/files)
        rest_freq_hz: Maser line rest frequency in Hz
        if_center_hz: SDR center frequency (IF after LNB)
        lo_freq_hz: LNB local oscillator frequency
        sample_rate: SDR sample rate
        gain: SDR gain
        integration_sec: Total integration per ON/OFF position
        fft_size: FFT size (larger = finer velocity resolution)
        data_dir: Directory for IQ recordings
        ra_deg: Source RA for LSR correction
        dec_deg: Source Dec for LSR correction
        site: astropy EarthLocation for LSR correction
        capture_off: If True, prompt for OFF capture. If False, use flat OFF.

    Returns:
        MaserObservation with all results
    """
    output_dir = Path(data_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    molecule = _identify_molecule(rest_freq_hz)

    logger.info(f"=== Maser Observation: {source_name} ({molecule}) ===")
    logger.info(f"Rest freq: {rest_freq_hz / 1e9:.6f} GHz")
    logger.info(f"IF center: {if_center_hz / 1e6:.3f} MHz")
    logger.info(f"LO: {lo_freq_hz / 1e9:.3f} GHz")
    logger.info(f"Integration: {integration_sec}s, FFT: {fft_size}")

    sdr_config = CaptureConfig(
        center_freq=if_center_hz,
        sample_rate=sample_rate,
        gain=gain,
    )

    spectral_config = SpectralConfig(
        fft_size=fft_size,
        overlap=0.5,
        window="hann",
        sample_rate=sample_rate,
        center_freq=if_center_hz,
    )

    # --- ON-source capture ---
    on_file = str(output_dir / f"{source_name}_{timestamp}_ON.cf32")
    logger.info(f"Capturing ON-source ({integration_sec}s)...")
    capture_to_file(sdr_config, integration_sec, on_file)

    # --- OFF-source capture ---
    if capture_off:
        off_file = str(output_dir / f"{source_name}_{timestamp}_OFF.cf32")
        logger.info(f"Capturing OFF-source ({integration_sec}s)...")
        logger.info("(Dish should be offset from source)")
        capture_to_file(sdr_config, integration_sec, off_file)
    else:
        off_file = None

    # --- Process ---
    return process_maser_data(
        on_file=on_file,
        off_file=off_file,
        source_name=source_name,
        rest_freq_hz=rest_freq_hz,
        lo_freq_hz=lo_freq_hz,
        spectral_config=spectral_config,
        ra_deg=ra_deg,
        dec_deg=dec_deg,
        site=site,
    )


def process_maser_data(
    on_file: str,
    off_file: Optional[str],
    source_name: str,
    rest_freq_hz: float,
    lo_freq_hz: float,
    spectral_config: SpectralConfig,
    ra_deg: float = 0.0,
    dec_deg: float = 0.0,
    site=None,
) -> MaserObservation:
    """
    Process captured IQ files into a maser spectrum.

    Can be used to reprocess existing captures without re-observing.
    """
    molecule = _identify_molecule(rest_freq_hz)

    # Load and compute ON spectrum
    logger.info("Processing ON-source data...")
    on_iq = load_iq_file(on_file, spectral_config.sample_rate)
    freqs, on_psd = compute_spectrum(on_iq, spectral_config)
    n_spectra_on = len(on_iq) // spectral_config.fft_size

    # Load and compute OFF spectrum (or use synthetic flat)
    if off_file:
        logger.info("Processing OFF-source data...")
        off_iq = load_iq_file(off_file, spectral_config.sample_rate)
        _, off_psd = compute_spectrum(off_iq, spectral_config)
    else:
        logger.info("No OFF data -- using median-filtered ON as bandpass estimate")
        from scipy.ndimage import median_filter
        off_psd = median_filter(on_psd, size=1024)

    # Calibrate: (ON - OFF) / OFF
    calibrated = bandpass_calibrate(on_psd, off_psd)

    # Remove residual baseline
    # Find where the maser line should be (center of band ± some range)
    center_chan = len(calibrated) // 2
    line_width_chans = len(calibrated) // 8  # Exclude central 12.5% for baseline fit
    calibrated = extract_baseline(
        calibrated,
        (center_chan - line_width_chans, center_chan + line_width_chans),
        order=3,
    )

    # Convert IF frequencies to RF (sky) frequencies
    rf_freqs = freqs + lo_freq_hz

    # Convert to LSR velocity
    velocities = np.array([
        C_KMS * (rest_freq_hz - rf) / rest_freq_hz
        for rf in rf_freqs
    ])

    # Apply LSR correction if site info available
    v_lsr_corr = 0.0
    if site is not None and (ra_deg != 0 or dec_deg != 0):
        try:
            from tracker.celestial import lsr_velocity_correction
            v_lsr_corr = lsr_velocity_correction(site, ra_deg, dec_deg)
            velocities += v_lsr_corr
            logger.info(f"LSR velocity correction: {v_lsr_corr:.3f} km/s")
        except Exception as e:
            logger.warning(f"LSR correction failed: {e}")

    # Detection statistics
    rms = estimate_rms(calibrated, exclude_center=0.25)
    peak_idx = np.argmax(np.abs(calibrated))
    peak_snr = calibrated[peak_idx] / rms if rms > 0 else 0
    peak_vel = velocities[peak_idx]
    detected = abs(peak_snr) > 5.0  # 5-sigma detection threshold

    integration_sec = len(on_iq) / spectral_config.sample_rate

    if detected:
        logger.info(f"DETECTION! Peak SNR={peak_snr:.1f} at v_LSR={peak_vel:.1f} km/s")
    else:
        logger.info(f"No detection. Peak SNR={peak_snr:.1f} (threshold: 5.0)")

    return MaserObservation(
        source_name=source_name,
        molecule=molecule,
        rest_freq_hz=rest_freq_hz,
        obs_time=datetime.now(timezone.utc).isoformat(),
        integration_sec=integration_sec,
        n_spectra=n_spectra_on,
        freqs_hz=freqs,
        rf_freqs_hz=rf_freqs,
        velocities_kms=velocities,
        on_spectrum=on_psd,
        off_spectrum=off_psd,
        calibrated=calibrated,
        rms_noise=rms,
        peak_snr=peak_snr,
        peak_velocity=peak_vel,
        detected=detected,
    )


def plot_maser_result(
    obs: MaserObservation,
    output_path: str = None,
    velocity_range: tuple[float, float] = None,
    smooth_bins: int = 0,
):
    """
    Plot maser observation result.

    Creates a publication-style plot with velocity on x-axis
    and relative power on y-axis, similar to Mol's plots.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    spectrum = obs.calibrated
    if smooth_bins > 0:
        spectrum = smooth_spectrum(spectrum, smooth_bins)

    fig, axes = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={"height_ratios": [3, 1]})

    # Main spectrum plot (velocity domain)
    ax1 = axes[0]
    ax1.plot(obs.velocities_kms, spectrum, linewidth=0.5, color="tab:blue")

    # Mark detection
    if obs.detected:
        peak_idx = np.argmax(np.abs(spectrum))
        ax1.axvline(obs.peak_velocity, color="red", linestyle="--", alpha=0.5, label=f"Peak: {obs.peak_velocity:.1f} km/s")

    # Noise level
    ax1.axhline(obs.rms_noise * 5, color="gray", linestyle=":", alpha=0.3, label=f"5σ = {obs.rms_noise * 5:.6f}")
    ax1.axhline(-obs.rms_noise * 5, color="gray", linestyle=":", alpha=0.3)
    ax1.axhline(0, color="gray", linewidth=0.5)

    ax1.set_ylabel("(ON - OFF) / OFF")
    ax1.set_title(
        f"{obs.source_name} — {obs.molecule} ({obs.rest_freq_hz / 1e9:.3f} GHz)\n"
        f"Integration: {obs.integration_sec:.0f}s | {obs.n_spectra} spectra averaged | "
        f"SNR: {obs.peak_snr:.1f} | {'DETECTED' if obs.detected else 'not detected'}"
    )
    ax1.legend(loc="upper right")
    ax1.grid(True, alpha=0.2)

    if velocity_range:
        ax1.set_xlim(velocity_range)

    # Raw spectra comparison
    ax2 = axes[1]
    ax2.plot(obs.freqs_hz / 1e6, power_to_db(obs.on_spectrum), linewidth=0.3, label="ON", alpha=0.7)
    ax2.plot(obs.freqs_hz / 1e6, power_to_db(obs.off_spectrum), linewidth=0.3, label="OFF", alpha=0.7)
    ax2.set_xlabel("IF Frequency (MHz)")
    ax2.set_ylabel("Power (dB)")
    ax2.legend()
    ax2.grid(True, alpha=0.2)

    fig.tight_layout()

    if output_path is None:
        output_path = f"{obs.source_name}_{obs.molecule}_{obs.obs_time[:10]}.png"

    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Plot saved to {output_path}")


def save_observation(obs: MaserObservation, output_dir: str = "data/spectra"):
    """Save observation results to JSON + numpy files."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    base = f"{obs.source_name}_{obs.molecule}_{obs.obs_time[:19].replace(':', '')}"

    # Save numpy arrays
    np.save(str(out / f"{base}_velocities.npy"), obs.velocities_kms)
    np.save(str(out / f"{base}_calibrated.npy"), obs.calibrated)

    # Save metadata
    meta = {
        "source_name": obs.source_name,
        "molecule": obs.molecule,
        "rest_freq_hz": obs.rest_freq_hz,
        "obs_time": obs.obs_time,
        "integration_sec": obs.integration_sec,
        "n_spectra": obs.n_spectra,
        "rms_noise": obs.rms_noise,
        "peak_snr": obs.peak_snr,
        "peak_velocity": obs.peak_velocity,
        "detected": obs.detected,
    }

    with open(out / f"{base}_meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    logger.info(f"Observation saved to {out / base}*")


def _identify_molecule(freq_hz: float) -> str:
    """Identify molecule from rest frequency."""
    for name, f in MASER_LINES.items():
        if abs(freq_hz - f) < 1e6:  # Within 1 MHz
            return name
    return f"unknown_{freq_hz / 1e6:.0f}MHz"


# --- CLI ---

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Maser observation pipeline")
    sub = parser.add_subparsers(dest="cmd")

    # Process existing IQ files
    p_proc = sub.add_parser("process", help="Process existing IQ captures")
    p_proc.add_argument("on_file", help="ON-source IQ file")
    p_proc.add_argument("--off", help="OFF-source IQ file (optional)")
    p_proc.add_argument("--source", default="unknown", help="Source name")
    p_proc.add_argument("--line", default="CH3OH_12GHz", choices=list(MASER_LINES.keys()))
    p_proc.add_argument("--lo", type=float, default=10.6, help="LO frequency in GHz")
    p_proc.add_argument("--rate", type=float, default=2.4, help="Sample rate in MHz")
    p_proc.add_argument("--fft", type=int, default=131072, help="FFT size")
    p_proc.add_argument("--freq", type=float, help="IF center freq in MHz")
    p_proc.add_argument("--smooth", type=int, default=0, help="Smoothing kernel size")
    p_proc.add_argument("--plot", default=None, help="Output plot file")

    # List known maser lines
    p_lines = sub.add_parser("lines", help="List known maser lines")

    args = parser.parse_args()

    if args.cmd == "process":
        rest = MASER_LINES[args.line]
        lo = args.lo * 1e9
        if_center = args.freq * 1e6 if args.freq else (rest - lo)

        config = SpectralConfig(
            fft_size=args.fft,
            sample_rate=args.rate * 1e6,
            center_freq=if_center,
        )

        obs = process_maser_data(
            on_file=args.on_file,
            off_file=args.off,
            source_name=args.source,
            rest_freq_hz=rest,
            lo_freq_hz=lo,
            spectral_config=config,
        )

        print(f"\nResult: {'DETECTED!' if obs.detected else 'Not detected'}")
        print(f"Peak SNR: {obs.peak_snr:.1f}")
        print(f"Peak velocity: {obs.peak_velocity:.1f} km/s")
        print(f"RMS noise: {obs.rms_noise:.8f}")

        save_observation(obs)

        if args.plot or obs.detected:
            plot_maser_result(obs, args.plot, smooth_bins=args.smooth)

    elif args.cmd == "lines":
        print(f"{'Line':<16} {'Frequency GHz':>14} {'Molecule'}")
        print("-" * 45)
        for name, freq in sorted(MASER_LINES.items(), key=lambda x: x[1]):
            mol = name.split("_")[0]
            print(f"{name:<16} {freq / 1e9:>14.6f} {mol}")

    else:
        parser.print_help()
