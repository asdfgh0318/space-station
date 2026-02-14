"""
Multi-target observation scheduler.

Manages a queue of observation targets:
- Satellite passes (from TLE, time-critical)
- Maser sources (from catalog, needs long integration)
- Hydrogen line survey points (from grid)
- Calibration sources (periodic)

Priority system:
1. Satellite passes (time-critical, short duration)
2. Calibration sources (needed periodically)
3. Maser observations (long integration, flexible timing)
4. HI survey (lowest priority, gap filler)
"""

import logging
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml

from tracker.celestial import (
    load_site,
    load_maser_catalog,
    radec_to_altaz,
    source_rise_set,
)

logger = logging.getLogger(__name__)


class ObsType(Enum):
    SATELLITE = "satellite"
    MASER = "maser"
    HYDROGEN = "hydrogen"
    CALIBRATION = "calibration"
    MANUAL = "manual"


class ObsStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Observation:
    """A scheduled observation."""
    id: int
    name: str
    obs_type: ObsType
    priority: int           # Lower = higher priority

    # Pointing
    ra_deg: float = 0.0
    dec_deg: float = 0.0
    az_deg: float = 0.0     # Pre-computed or for manual
    el_deg: float = 0.0

    # Timing
    start_time: Optional[datetime] = None   # None = as soon as possible
    end_time: Optional[datetime] = None
    duration_sec: float = 60.0

    # RF settings
    frequency_hz: float = 0.0
    band: str = ""          # Config band name
    molecule: str = ""

    # Status
    status: ObsStatus = ObsStatus.PENDING
    notes: str = ""

    # Results
    data_file: str = ""


@dataclass
class SchedulerState:
    """Current scheduler state."""
    running: bool = False
    current_obs: Optional[Observation] = None
    queue: list[Observation] = field(default_factory=list)
    completed: list[Observation] = field(default_factory=list)
    next_id: int = 1


class ObservationScheduler:
    """
    Manages observation queue and automated scheduling.

    Usage:
        scheduler = ObservationScheduler()
        scheduler.add_maser_targets()          # Load from catalog
        scheduler.add_satellite_passes()       # From TLE predictions
        schedule = scheduler.get_tonight()     # Get tonight's plan
    """

    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = str(Path(__file__).parent / "config.yaml")

        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        self.site = load_site(config_path)
        self.state = SchedulerState()
        self.min_elevation = 10.0  # degrees

    def add_observation(self, obs: Observation) -> int:
        """Add an observation to the queue. Returns observation ID."""
        obs.id = self.state.next_id
        self.state.next_id += 1
        self.state.queue.append(obs)
        self.state.queue.sort(key=lambda o: (o.priority, o.start_time or datetime.max.replace(tzinfo=timezone.utc)))
        logger.info(f"Added observation #{obs.id}: {obs.name} ({obs.obs_type.value})")
        return obs.id

    def add_maser_targets(
        self,
        min_elevation: float = 10.0,
        integration_sec: float = 1800,
        max_targets: int = 10,
    ) -> int:
        """
        Add observable maser targets from the catalog.

        Only adds targets currently above min_elevation.
        Returns number of targets added.
        """
        targets = load_maser_catalog()
        now = datetime.now(timezone.utc)
        added = 0

        for t in targets:
            if t["frequency_mhz"] == 0:  # Skip continuum calibrators
                continue

            az, el = radec_to_altaz(t["ra_deg"], t["dec_deg"], self.site, now)

            if el < min_elevation:
                continue

            # Determine band config
            freq_hz = t["frequency_mhz"] * 1e6
            band = self._freq_to_band(freq_hz)
            if band is None:
                continue  # Can't observe this frequency with current hardware

            obs = Observation(
                id=0,
                name=t["name"],
                obs_type=ObsType.MASER,
                priority=30,  # Medium priority
                ra_deg=t["ra_deg"],
                dec_deg=t["dec_deg"],
                az_deg=az,
                el_deg=el,
                duration_sec=integration_sec,
                frequency_hz=freq_hz,
                band=band,
                molecule=t["molecule"],
                notes=f"Peak flux: {t['peak_flux_jy']} Jy, v_LSR: {t['vlsr_km_s']} km/s",
            )

            self.add_observation(obs)
            added += 1

            if added >= max_targets:
                break

        logger.info(f"Added {added} maser targets from catalog")
        return added

    def add_calibration(
        self,
        source_name: str = "Cas A",
        duration_sec: float = 300,
    ) -> int:
        """Add a calibration observation."""
        targets = load_maser_catalog()
        cal = next((t for t in targets if t["name"] == source_name), None)

        if cal is None:
            logger.error(f"Calibration source {source_name} not in catalog")
            return -1

        now = datetime.now(timezone.utc)
        az, el = radec_to_altaz(cal["ra_deg"], cal["dec_deg"], self.site, now)

        if el < self.min_elevation:
            logger.warning(f"{source_name} is below horizon (el={el:.1f})")
            return -1

        obs = Observation(
            id=0,
            name=source_name,
            obs_type=ObsType.CALIBRATION,
            priority=10,  # High priority
            ra_deg=cal["ra_deg"],
            dec_deg=cal["dec_deg"],
            az_deg=az,
            el_deg=el,
            duration_sec=duration_sec,
            notes="Continuum calibration source",
        )

        return self.add_observation(obs)

    def add_hydrogen_survey_point(
        self,
        galactic_l: float,
        galactic_b: float = 0.0,
        duration_sec: float = 300,
    ) -> int:
        """Add a hydrogen 21cm survey observation at galactic coordinates."""
        from tracker.celestial import galactic_to_altaz
        from astropy.coordinates import SkyCoord, Galactic
        from astropy import units as u

        now = datetime.now(timezone.utc)

        # Convert galactic to equatorial
        gc = SkyCoord(l=galactic_l * u.deg, b=galactic_b * u.deg, frame="galactic")
        eq = gc.icrs

        az, el = galactic_to_altaz(galactic_l, galactic_b, self.site, now)

        if el < self.min_elevation:
            return -1

        obs = Observation(
            id=0,
            name=f"HI_l{galactic_l:.0f}_b{galactic_b:.0f}",
            obs_type=ObsType.HYDROGEN,
            priority=50,  # Low priority
            ra_deg=eq.ra.deg,
            dec_deg=eq.dec.deg,
            az_deg=az,
            el_deg=el,
            duration_sec=duration_sec,
            frequency_hz=1420405751.768,
            band="hydrogen_21cm",
            molecule="HI",
            notes=f"Galactic l={galactic_l}, b={galactic_b}",
        )

        return self.add_observation(obs)

    def get_next(self) -> Optional[Observation]:
        """Get the next pending observation."""
        now = datetime.now(timezone.utc)

        for obs in self.state.queue:
            if obs.status != ObsStatus.PENDING:
                continue

            # Check time constraints
            if obs.start_time and obs.start_time > now:
                continue

            if obs.end_time and obs.end_time < now:
                obs.status = ObsStatus.SKIPPED
                continue

            # Recheck elevation
            az, el = radec_to_altaz(obs.ra_deg, obs.dec_deg, self.site, now)
            if el < self.min_elevation:
                continue

            # Update current pointing
            obs.az_deg = az
            obs.el_deg = el

            return obs

        return None

    def start_observation(self, obs_id: int):
        """Mark an observation as active."""
        for obs in self.state.queue:
            if obs.id == obs_id:
                obs.status = ObsStatus.ACTIVE
                self.state.current_obs = obs
                logger.info(f"Starting observation #{obs_id}: {obs.name}")
                return

    def complete_observation(self, obs_id: int, data_file: str = ""):
        """Mark an observation as completed."""
        for obs in self.state.queue:
            if obs.id == obs_id:
                obs.status = ObsStatus.COMPLETED
                obs.data_file = data_file
                self.state.completed.append(obs)
                if self.state.current_obs and self.state.current_obs.id == obs_id:
                    self.state.current_obs = None
                logger.info(f"Completed observation #{obs_id}: {obs.name}")
                return

    def get_schedule(self) -> list[dict]:
        """Get the current schedule as a list of dicts."""
        return [
            {
                "id": obs.id,
                "name": obs.name,
                "type": obs.obs_type.value,
                "priority": obs.priority,
                "status": obs.status.value,
                "az": round(obs.az_deg, 2),
                "el": round(obs.el_deg, 2),
                "duration_sec": obs.duration_sec,
                "band": obs.band,
                "molecule": obs.molecule,
                "notes": obs.notes,
            }
            for obs in self.state.queue
        ]

    def _freq_to_band(self, freq_hz: float) -> Optional[str]:
        """Map an RF frequency to a configured band name."""
        bands = self.config.get("sdr", {}).get("bands", {})

        # Check Ku-band masers
        if 10.7e9 <= freq_hz <= 12.75e9:
            return "ku_12ghz_maser"

        # Check L-band
        if 1.4e9 <= freq_hz <= 1.72e9:
            return "hydrogen_21cm"

        # Check 6.7 GHz (needs C-band LNB -- not in basic config)
        if 6.6e9 <= freq_hz <= 6.7e9:
            return None  # Not supported with Ku LNB

        return None


# --- CLI ---

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Observation scheduler")
    sub = parser.add_subparsers(dest="cmd")

    # Show tonight's observable targets
    p_tonight = sub.add_parser("tonight", help="Show observable targets tonight")
    p_tonight.add_argument("--min-el", type=float, default=10.0)

    # Generate HI survey schedule
    p_hi = sub.add_parser("hi-survey", help="Generate hydrogen line survey schedule")
    p_hi.add_argument("--step", type=float, default=10.0, help="Galactic longitude step")

    # Show full schedule
    p_sched = sub.add_parser("schedule", help="Show current schedule")

    args = parser.parse_args()
    scheduler = ObservationScheduler()

    if args.cmd == "tonight":
        n = scheduler.add_maser_targets(min_elevation=args.min_el)
        scheduler.add_calibration("Cas A")
        scheduler.add_calibration("Cyg A")

        schedule = scheduler.get_schedule()
        print(f"\n{'ID':>3} {'Name':<20} {'Type':<12} {'AZ':>7} {'EL':>7} {'Band':<18} {'Status'}")
        print("-" * 85)
        for s in schedule:
            print(
                f"{s['id']:>3} {s['name']:<20} {s['type']:<12} "
                f"{s['az']:>7.1f} {s['el']:>7.1f} {s['band']:<18} {s['status']}"
            )

    elif args.cmd == "hi-survey":
        count = 0
        for l in range(0, 360, int(args.step)):
            obs_id = scheduler.add_hydrogen_survey_point(float(l))
            if obs_id > 0:
                count += 1
        print(f"Added {count} HI survey points")

        schedule = scheduler.get_schedule()
        for s in schedule:
            print(f"  {s['name']}: AZ={s['az']:.1f} EL={s['el']:.1f}")

    elif args.cmd == "schedule":
        schedule = scheduler.get_schedule()
        if not schedule:
            print("Schedule is empty. Run 'tonight' or add targets first.")
        for s in schedule:
            print(f"#{s['id']} [{s['status']}] {s['name']} ({s['type']}) AZ={s['az']} EL={s['el']}")

    else:
        parser.print_help()
