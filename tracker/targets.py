"""Geostationary look-angle math + named target presets for the antenna tracker.

Pure math + dataclasses + click CLI. No I/O beyond reading the YAML config.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import click
import yaml
from rich.console import Console
from rich.table import Table

# Earth radius (km, WGS-84 equatorial) over GEO orbit radius (km).
_EARTH_RADIUS_KM = 6378.137
_GEO_RADIUS_KM = 42164.17
_R_RATIO = _EARTH_RADIUS_KM / _GEO_RADIUS_KM  # ≈ 0.1512

DEFAULT_CONFIG_PATH = Path("tracker/config.yaml")


@dataclass
class Target:
    key: str
    name: str
    sat_longitude: float  # deg, east positive
    band: str
    az: float | None = None  # deg true, clockwise from north, [0, 360)
    el: float | None = None  # deg, [-90, 90]


def geostationary_azel(
    site_lat_deg: float, site_lon_deg: float, sat_lon_deg: float
) -> tuple[float, float]:
    """Look-angle (azimuth_deg, elevation_deg) to a GEO sat from a ground site.

    Spherical Earth, Earth radius 6378.137 km, GEO orbit radius 42164.17 km.
    Azimuth measured clockwise from true north in [0, 360); elevation in
    [-90, 90] (negative means below horizon).

    Uses an ECEF → ENU vector transform so the result is correct in both
    hemispheres and for both east- and west-of-site satellites.
    """
    phi = math.radians(site_lat_deg)
    lam_s = math.radians(site_lon_deg)
    lam_t = math.radians(sat_lon_deg)

    cos_phi = math.cos(phi)
    sin_phi = math.sin(phi)
    cos_ls = math.cos(lam_s)
    sin_ls = math.sin(lam_s)

    # Site position in ECEF (spherical Earth).
    sx = _EARTH_RADIUS_KM * cos_phi * cos_ls
    sy = _EARTH_RADIUS_KM * cos_phi * sin_ls
    sz = _EARTH_RADIUS_KM * sin_phi

    # GEO satellite position in ECEF (equatorial plane).
    tx = _GEO_RADIUS_KM * math.cos(lam_t)
    ty = _GEO_RADIUS_KM * math.sin(lam_t)
    tz = 0.0

    dx, dy, dz = tx - sx, ty - sy, tz - sz

    # ECEF → local ENU (East, North, Up) at the site.
    east = -sin_ls * dx + cos_ls * dy
    north = -sin_phi * cos_ls * dx - sin_phi * sin_ls * dy + cos_phi * dz
    up = cos_phi * cos_ls * dx + cos_phi * sin_ls * dy + sin_phi * dz

    az_rad = math.atan2(east, north) % (2.0 * math.pi)
    el_rad = math.atan2(up, math.sqrt(east * east + north * north))

    return math.degrees(az_rad), math.degrees(el_rad)


def load_targets(config: dict) -> dict[str, Target]:
    """Build key→Target map with az/el filled from config['site'] + config['targets']."""
    site = config["site"]
    lat = float(site["latitude"])
    lon = float(site["longitude"])

    out: dict[str, Target] = {}
    for key, spec in (config.get("targets") or {}).items():
        sat_lon = float(spec["sat_longitude"])
        az, el = geostationary_azel(lat, lon, sat_lon)
        out[key] = Target(
            key=key,
            name=spec.get("name", key),
            sat_longitude=sat_lon,
            band=spec.get("band", ""),
            az=az,
            el=el,
        )
    return out


@click.group()
def cli() -> None:
    """Tracker target presets."""


@cli.command("list")
@click.option(
    "--config",
    "config_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=DEFAULT_CONFIG_PATH,
    show_default=True,
    help="Path to config YAML.",
)
def list_cmd(config_path: Path) -> None:
    """List configured GEO targets with computed look-angles."""
    if not config_path.exists():
        raise click.ClickException(f"Config file not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    targets = load_targets(config)
    site = config["site"]
    console = Console()
    console.print(
        f"Site: [bold]{site.get('name', '?')}[/bold]  "
        f"lat={site['latitude']:.4f}  lon={site['longitude']:.4f}  "
        f"elev={site.get('elevation', 0)} m"
    )

    table = Table(title="Geostationary targets")
    table.add_column("key", style="cyan")
    table.add_column("name")
    table.add_column("sat_lon", justify="right")
    table.add_column("az", justify="right")
    table.add_column("el", justify="right")
    table.add_column("visible", justify="center")

    for t in targets.values():
        visible = "✓" if (t.el is not None and t.el >= 0) else "✗"
        table.add_row(
            t.key,
            t.name,
            f"{t.sat_longitude:+.1f}°",
            f"{t.az:.2f}°" if t.az is not None else "-",
            f"{t.el:.2f}°" if t.el is not None else "-",
            visible,
        )
    console.print(table)


if __name__ == "__main__":
    cli()
