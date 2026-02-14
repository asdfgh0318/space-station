"""
Celestial coordinate transforms and astronomical calculations.

Handles:
- RA/Dec to Alt/Az conversion for pointing the dish
- LSR velocity correction for maser/HI spectral work
- Satellite position from TLE via skyfield
- Source rise/set/transit time calculations
"""

import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
from astropy import units as u
from astropy.coordinates import (
    SkyCoord,
    EarthLocation,
    AltAz,
    Galactic,
    ICRS,
)
from astropy.time import Time
import yaml

# Speed of light
C_KMS = 299792.458  # km/s


def load_site(config_path: str = None) -> EarthLocation:
    """Load observer site from config."""
    if config_path is None:
        config_path = str(Path(__file__).parent / "config.yaml")

    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    site = cfg["site"]
    return EarthLocation(
        lat=site["latitude"] * u.deg,
        lon=site["longitude"] * u.deg,
        height=site["elevation"] * u.m,
    )


def radec_to_altaz(
    ra_deg: float,
    dec_deg: float,
    site: EarthLocation,
    time: Optional[datetime] = None,
) -> tuple[float, float]:
    """
    Convert RA/Dec (J2000) to Alt/Az for the observer.

    Args:
        ra_deg: Right ascension in degrees
        dec_deg: Declination in degrees
        site: Observer location
        time: Observation time (UTC). Defaults to now.

    Returns:
        (azimuth, altitude) in degrees. Az: 0=N, 90=E, 180=S, 270=W
    """
    if time is None:
        time = datetime.now(timezone.utc)

    obs_time = Time(time)
    altaz_frame = AltAz(obstime=obs_time, location=site)

    coord = SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg, frame="icrs")
    altaz = coord.transform_to(altaz_frame)

    return (altaz.az.deg, altaz.alt.deg)


def galactic_to_altaz(
    l_deg: float,
    b_deg: float,
    site: EarthLocation,
    time: Optional[datetime] = None,
) -> tuple[float, float]:
    """Convert Galactic coordinates to Alt/Az."""
    if time is None:
        time = datetime.now(timezone.utc)

    obs_time = Time(time)
    altaz_frame = AltAz(obstime=obs_time, location=site)

    coord = SkyCoord(l=l_deg * u.deg, b=b_deg * u.deg, frame="galactic")
    altaz = coord.transform_to(altaz_frame)

    return (altaz.az.deg, altaz.alt.deg)


def parse_ra_dec(ra_str: str, dec_str: str) -> tuple[float, float]:
    """
    Parse RA/Dec from sexagesimal strings to degrees.

    Args:
        ra_str: "HH:MM:SS.S" or "HHhMMmSS.Ss"
        dec_str: "+DD:MM:SS.S" or "+DDdMMmSS.Ss"

    Returns:
        (ra_degrees, dec_degrees)
    """
    coord = SkyCoord(ra_str, dec_str, unit=(u.hourangle, u.deg))
    return (coord.ra.deg, coord.dec.deg)


def lsr_velocity_correction(
    site: EarthLocation,
    ra_deg: float,
    dec_deg: float,
    time: Optional[datetime] = None,
) -> float:
    """
    Calculate the velocity correction to convert topocentric
    frequency to LSR (Local Standard of Rest) velocity.

    This is essential for maser and HI line work -- the observed
    frequency is Doppler-shifted by Earth's motion.

    Args:
        site: Observer location
        ra_deg: Source RA (J2000)
        dec_deg: Source Dec (J2000)
        time: Observation time (UTC)

    Returns:
        v_correction in km/s. Add this to topocentric velocity to get LSR.
    """
    if time is None:
        time = datetime.now(timezone.utc)

    obs_time = Time(time)
    source = SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg, frame="icrs")

    # Get the radial velocity correction from observer to LSR
    # This accounts for Earth rotation, orbital motion, and solar motion
    v_corr = source.radial_velocity_correction(
        kind="barycentric", obstime=obs_time, location=site
    )

    # Convert barycentric correction to LSR
    # Solar motion toward apex: l=56.24, b=22.54, v=16.5 km/s (Schönrich 2012)
    # Standard solar motion components (U, V, W) = (11.1, 12.24, 7.25) km/s
    solar_apex = SkyCoord(l=56.24 * u.deg, b=22.54 * u.deg, frame="galactic")
    solar_apex_icrs = solar_apex.icrs

    # Project solar motion onto source direction
    cos_angle = (
        math.sin(math.radians(dec_deg)) * math.sin(math.radians(solar_apex_icrs.dec.deg))
        + math.cos(math.radians(dec_deg)) * math.cos(math.radians(solar_apex_icrs.dec.deg))
        * math.cos(math.radians(ra_deg - solar_apex_icrs.ra.deg))
    )
    v_solar = 16.5 * cos_angle  # km/s, projected solar motion toward source

    return v_corr.to(u.km / u.s).value + v_solar


def freq_to_velocity(
    freq_hz: float,
    rest_freq_hz: float,
) -> float:
    """
    Convert observed frequency to radial velocity (radio convention).

    v = c * (f_rest - f_obs) / f_rest

    Args:
        freq_hz: Observed frequency in Hz
        rest_freq_hz: Rest frequency of the line in Hz

    Returns:
        Velocity in km/s (positive = receding)
    """
    return C_KMS * (rest_freq_hz - freq_hz) / rest_freq_hz


def velocity_to_freq(
    velocity_kms: float,
    rest_freq_hz: float,
) -> float:
    """
    Convert radial velocity to observed frequency (radio convention).

    f_obs = f_rest * (1 - v/c)
    """
    return rest_freq_hz * (1.0 - velocity_kms / C_KMS)


def source_rise_set(
    ra_deg: float,
    dec_deg: float,
    site: EarthLocation,
    min_elevation: float = 10.0,
    time: Optional[datetime] = None,
) -> dict:
    """
    Calculate rise, transit, and set times for a celestial source.

    Args:
        ra_deg: Source RA (J2000)
        dec_deg: Source Dec (J2000)
        site: Observer location
        min_elevation: Minimum elevation to consider "risen" (degrees)
        time: Start time for search (defaults to now)

    Returns:
        Dict with 'rises', 'transits', 'sets' datetimes and 'max_elevation'
    """
    if time is None:
        time = datetime.now(timezone.utc)

    lat = site.lat.deg

    # Maximum elevation at transit
    max_el = 90.0 - abs(lat - dec_deg)

    if max_el < min_elevation:
        return {
            "rises": None,
            "transits": None,
            "sets": None,
            "max_elevation": max_el,
            "visible": False,
        }

    # Check if source is circumpolar
    is_circumpolar = dec_deg > (90.0 - lat + min_elevation) if lat > 0 else \
                     dec_deg < (-90.0 - lat - min_elevation)

    if is_circumpolar:
        # Find transit time
        obs_time = Time(time)
        lst = obs_time.sidereal_time("apparent", longitude=site.lon).deg
        ha = lst - ra_deg
        if ha < -180:
            ha += 360
        if ha > 180:
            ha -= 360
        hours_to_transit = -ha / 15.0  # Convert degrees to hours
        if hours_to_transit < 0:
            hours_to_transit += 24.0

        from datetime import timedelta
        transit_time = time + timedelta(hours=hours_to_transit)

        return {
            "rises": None,
            "transits": transit_time,
            "sets": None,
            "max_elevation": max_el,
            "visible": True,
            "circumpolar": True,
        }

    # For non-circumpolar sources, find rise/set by hour angle
    # cos(HA) = (sin(el) - sin(lat)*sin(dec)) / (cos(lat)*cos(dec))
    cos_ha = (
        (math.sin(math.radians(min_elevation))
         - math.sin(math.radians(lat)) * math.sin(math.radians(dec_deg)))
        / (math.cos(math.radians(lat)) * math.cos(math.radians(dec_deg)))
    )

    if abs(cos_ha) > 1:
        return {
            "rises": None,
            "transits": None,
            "sets": None,
            "max_elevation": max_el,
            "visible": False,
        }

    ha_deg = math.degrees(math.acos(cos_ha))

    # Transit time
    obs_time = Time(time)
    lst = obs_time.sidereal_time("apparent", longitude=site.lon).deg
    ha_now = lst - ra_deg
    if ha_now < -180:
        ha_now += 360
    if ha_now > 180:
        ha_now -= 360
    hours_to_transit = -ha_now / 15.0
    if hours_to_transit < 0:
        hours_to_transit += 24.0

    from datetime import timedelta
    transit_time = time + timedelta(hours=hours_to_transit)
    rise_time = transit_time - timedelta(hours=ha_deg / 15.0)
    set_time = transit_time + timedelta(hours=ha_deg / 15.0)

    return {
        "rises": rise_time,
        "transits": transit_time,
        "sets": set_time,
        "max_elevation": max_el,
        "visible": True,
        "circumpolar": False,
    }


def load_maser_catalog(catalog_path: str = None) -> list[dict]:
    """
    Load the maser target catalog.

    Returns list of dicts with keys: name, ra_deg, dec_deg, frequency_mhz,
    molecule, peak_flux_jy, vlsr_km_s, notes
    """
    if catalog_path is None:
        catalog_path = str(Path(__file__).parent.parent / "targets" / "masers.csv")

    targets = []
    with open(catalog_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split(",")
            if len(parts) < 8:
                continue

            name = parts[0]
            ra_str = parts[1]
            dec_str = parts[2]

            try:
                ra_deg, dec_deg = parse_ra_dec(ra_str, dec_str)
            except Exception:
                continue

            targets.append({
                "name": name,
                "ra_deg": ra_deg,
                "dec_deg": dec_deg,
                "frequency_mhz": float(parts[3]),
                "molecule": parts[4],
                "peak_flux_jy": float(parts[5]),
                "vlsr_km_s": float(parts[6]),
                "notes": parts[7] if len(parts) > 7 else "",
            })

    return targets


# --- CLI for testing ---

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Celestial coordinate tools")
    sub = parser.add_subparsers(dest="cmd")

    # Convert RA/Dec to Alt/Az
    p_convert = sub.add_parser("convert", help="RA/Dec to Alt/Az")
    p_convert.add_argument("ra", help="RA (e.g. '02:27:04.1')")
    p_convert.add_argument("dec", help="Dec (e.g. '+61:52:22')")

    # Show maser catalog visibility
    p_catalog = sub.add_parser("catalog", help="Show maser catalog visibility")
    p_catalog.add_argument("--min-el", type=float, default=10.0, help="Minimum elevation")

    # LSR velocity correction
    p_lsr = sub.add_parser("lsr", help="LSR velocity correction")
    p_lsr.add_argument("ra", help="RA")
    p_lsr.add_argument("dec", help="Dec")

    args = parser.parse_args()
    site = load_site()
    now = datetime.now(timezone.utc)

    if args.cmd == "convert":
        ra_deg, dec_deg = parse_ra_dec(args.ra, args.dec)
        az, alt = radec_to_altaz(ra_deg, dec_deg, site)
        print(f"RA/Dec: {args.ra} {args.dec}")
        print(f"Alt/Az: AZ={az:.4f} EL={alt:.4f}")
        print(f"{'ABOVE' if alt > 0 else 'BELOW'} horizon")

        info = source_rise_set(ra_deg, dec_deg, site)
        if info["visible"]:
            print(f"Max elevation: {info['max_elevation']:.1f} deg")
            if info.get("circumpolar"):
                print("Circumpolar (always visible)")
            else:
                print(f"Rises:    {info['rises']}")
                print(f"Transits: {info['transits']}")
                print(f"Sets:     {info['sets']}")

    elif args.cmd == "catalog":
        targets = load_maser_catalog()
        print(f"{'Source':<20} {'Mol.':<6} {'Freq MHz':<10} {'AZ':>8} {'EL':>8} {'Max EL':>8} {'Flux Jy':>8}")
        print("-" * 80)
        for t in targets:
            az, el = radec_to_altaz(t["ra_deg"], t["dec_deg"], site)
            info = source_rise_set(t["ra_deg"], t["dec_deg"], site, args.min_el)
            max_el = info["max_elevation"]
            marker = "*" if el > args.min_el else " "
            print(
                f"{marker}{t['name']:<19} {t['molecule']:<6} {t['frequency_mhz']:<10.0f} "
                f"{az:>8.2f} {el:>8.2f} {max_el:>8.1f} {t['peak_flux_jy']:>8.0f}"
            )

    elif args.cmd == "lsr":
        ra_deg, dec_deg = parse_ra_dec(args.ra, args.dec)
        v_corr = lsr_velocity_correction(site, ra_deg, dec_deg)
        print(f"LSR velocity correction: {v_corr:.3f} km/s")
        print(f"For HI line (1420.406 MHz):")
        rest = 1420405751.768
        shifted = velocity_to_freq(-v_corr, rest)
        print(f"  Topocentric freq offset: {(shifted - rest) / 1e3:.3f} kHz")

    else:
        parser.print_help()
