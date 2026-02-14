"""
Spectral processing for radio telescope observations.

Core signal processing: FFT averaging, bandpass calibration,
ON/OFF source subtraction, and spectral smoothing.
Used by both maser detection and hydrogen line observations.
"""

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
from scipy import signal as sig

logger = logging.getLogger(__name__)


@dataclass
class SpectralConfig:
    """Configuration for spectral processing."""
    fft_size: int = 65536       # FFT points
    overlap: float = 0.5        # Fraction overlap between FFT windows
    window: str = "hann"        # Window function
    sample_rate: float = 2.4e6  # Hz
    center_freq: float = 0.0    # Hz (for frequency axis)


def compute_spectrum(
    iq_data: np.ndarray,
    config: SpectralConfig,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Compute averaged power spectrum from IQ data.

    Uses Welch's method: windowed FFT segments, averaged together.
    This reduces noise by sqrt(N_segments) compared to single FFT.

    Args:
        iq_data: Complex64 IQ samples
        config: Spectral processing config

    Returns:
        (frequencies_hz, power_spectrum) where power is in linear scale
    """
    n_fft = config.fft_size
    step = int(n_fft * (1.0 - config.overlap))

    # Window function
    window = sig.get_window(config.window, n_fft)
    window_power = np.sum(window ** 2) / n_fft

    # Segment and process
    n_segments = max(1, (len(iq_data) - n_fft) // step + 1)
    psd_acc = np.zeros(n_fft, dtype=np.float64)

    for i in range(n_segments):
        start = i * step
        segment = iq_data[start:start + n_fft]

        if len(segment) < n_fft:
            break

        # Apply window
        windowed = segment * window

        # FFT (complex → complex)
        spectrum = np.fft.fftshift(np.fft.fft(windowed))

        # Power spectral density
        psd_acc += np.abs(spectrum) ** 2

    # Average
    psd = psd_acc / (n_segments * n_fft * window_power * config.sample_rate)

    # Frequency axis
    freqs = np.fft.fftshift(np.fft.fftfreq(n_fft, 1.0 / config.sample_rate))
    freqs += config.center_freq

    return freqs, psd


def power_to_db(power: np.ndarray) -> np.ndarray:
    """Convert linear power to dB scale."""
    return 10 * np.log10(np.maximum(power, 1e-30))


def db_to_power(db: np.ndarray) -> np.ndarray:
    """Convert dB to linear power."""
    return 10 ** (db / 10)


def bandpass_calibrate(
    on_spectrum: np.ndarray,
    off_spectrum: np.ndarray,
) -> np.ndarray:
    """
    ON/OFF bandpass calibration.

    Removes the frequency-dependent gain shape of the receiver chain.
    Result is (ON - OFF) / OFF, giving relative excess power at each freq.
    This is the standard radio astronomy calibration technique.

    For ideal noise-free case, result = T_source / T_sys at each frequency.

    Args:
        on_spectrum: Power spectrum with source in beam
        off_spectrum: Power spectrum with source out of beam

    Returns:
        Calibrated spectrum (dimensionless, ~T_source/T_sys)
    """
    # Avoid division by zero
    off_safe = np.maximum(off_spectrum, 1e-30)
    return (on_spectrum - off_spectrum) / off_safe


def smooth_spectrum(
    spectrum: np.ndarray,
    kernel_size: int = 5,
    method: str = "boxcar",
) -> np.ndarray:
    """
    Smooth a spectrum to reduce noise.

    Args:
        spectrum: Input spectrum array
        kernel_size: Smoothing kernel width in bins
        method: 'boxcar' (running average) or 'gaussian'

    Returns:
        Smoothed spectrum
    """
    if method == "boxcar":
        kernel = np.ones(kernel_size) / kernel_size
    elif method == "gaussian":
        kernel = sig.windows.gaussian(kernel_size, std=kernel_size / 4)
        kernel /= kernel.sum()
    else:
        raise ValueError(f"Unknown smoothing method: {method}")

    return np.convolve(spectrum, kernel, mode="same")


def freq_to_channel(freq_hz: float, freqs: np.ndarray) -> int:
    """Find the closest channel index for a given frequency."""
    return int(np.argmin(np.abs(freqs - freq_hz)))


def extract_baseline(
    spectrum: np.ndarray,
    line_channels: tuple[int, int],
    order: int = 3,
) -> np.ndarray:
    """
    Fit and subtract a polynomial baseline, excluding line channels.

    Useful for removing residual bandpass slope after ON/OFF calibration.

    Args:
        spectrum: Input spectrum
        line_channels: (start, end) channel range to exclude from fit
        order: Polynomial order for baseline fit

    Returns:
        Baseline-subtracted spectrum
    """
    n = len(spectrum)
    x = np.arange(n)
    mask = np.ones(n, dtype=bool)
    mask[line_channels[0]:line_channels[1]] = False

    # Fit polynomial to non-line channels
    coeffs = np.polyfit(x[mask], spectrum[mask], order)
    baseline = np.polyval(coeffs, x)

    return spectrum - baseline


def estimate_rms(spectrum: np.ndarray, exclude_center: float = 0.2) -> float:
    """
    Estimate RMS noise level from spectrum edges.

    Excludes the central portion where a line might be present.

    Args:
        spectrum: Input spectrum (calibrated)
        exclude_center: Fraction of band to exclude from center

    Returns:
        RMS noise estimate
    """
    n = len(spectrum)
    exclude_half = int(n * exclude_center / 2)
    center = n // 2

    mask = np.ones(n, dtype=bool)
    mask[center - exclude_half:center + exclude_half] = False

    return float(np.std(spectrum[mask]))


def integrate_spectra(
    spectra_list: list[np.ndarray],
    weights: Optional[list[float]] = None,
) -> np.ndarray:
    """
    Average multiple spectra together (weighted or uniform).

    This is the key to detecting weak signals: averaging N spectra
    reduces noise by sqrt(N) while signal stays constant.

    Args:
        spectra_list: List of spectrum arrays (all same length)
        weights: Optional weights (e.g., based on system temperature)

    Returns:
        Averaged spectrum
    """
    if weights is None:
        return np.mean(spectra_list, axis=0)

    weights = np.array(weights)
    weights /= weights.sum()

    result = np.zeros_like(spectra_list[0])
    for spectrum, w in zip(spectra_list, weights):
        result += spectrum * w

    return result


def spectral_kurtosis(
    spectra_list: list[np.ndarray],
) -> np.ndarray:
    """
    Compute spectral kurtosis for RFI detection.

    Pure noise has kurtosis = 1. RFI shows kurtosis >> 1.
    Use to create a channel mask for excluding RFI-contaminated bins.

    Args:
        spectra_list: List of power spectra

    Returns:
        Kurtosis estimate per frequency channel
    """
    stack = np.array(spectra_list)
    n = stack.shape[0]

    mean = np.mean(stack, axis=0)
    mean_sq = np.mean(stack ** 2, axis=0)

    # Spectral kurtosis estimator
    sk = ((n + 1) / (n - 1)) * (n * mean_sq / (mean ** 2 + 1e-30) - 1)

    return sk


# --- CLI ---

if __name__ == "__main__":
    import argparse
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from sdr.capture import load_iq_file

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Spectral analysis of IQ files")
    parser.add_argument("input", help="Input IQ file (cf32 format)")
    parser.add_argument("--rate", type=float, default=2.4, help="Sample rate in MHz")
    parser.add_argument("--freq", type=float, default=0, help="Center freq in MHz")
    parser.add_argument("--fft", type=int, default=65536, help="FFT size")
    parser.add_argument("--output", default="spectrum.png", help="Output plot file")
    args = parser.parse_args()

    iq = load_iq_file(args.input, args.rate * 1e6)
    logger.info(f"Loaded {len(iq)} samples")

    config = SpectralConfig(
        fft_size=args.fft,
        sample_rate=args.rate * 1e6,
        center_freq=args.freq * 1e6,
    )

    freqs, psd = compute_spectrum(iq, config)
    psd_db = power_to_db(psd)

    rms = estimate_rms(psd_db)
    logger.info(f"Noise RMS: {rms:.2f} dB")

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(freqs / 1e6, psd_db, linewidth=0.5)
    ax.set_xlabel("Frequency (MHz)")
    ax.set_ylabel("Power (dB)")
    ax.set_title(f"Spectrum: {args.input}")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(args.output, dpi=150)
    logger.info(f"Plot saved to {args.output}")
