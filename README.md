<p align="center">
  <img src="banner.svg" alt="space-station banner" width="100%">
</p>

# space-station

Multi-band radio telescope and antenna tracker — Raspberry Pi 4B + Waveshare Stepper Motor HAT (B) + 2× NEMA 17 + RTL-SDR. Fully 3D-printed alt-az mount, FastAPI dashboard, swappable RF feeds.

## Documentation

- **[`tech_stack.md`](tech_stack.md)** — north star: hardware stack and credentials
- **[`plan_2.md`](plan_2.md)** — active rebuild plan (current)
- **[`docs/archive/plan_1.md`](docs/archive/plan_1.md)** — historical Phase 1 plan
- **[`docs/archive/merge_plan.html`](docs/archive/merge_plan.html)** — upcoming `inmarsat-sniffer` integration plan

## Quick start

```bash
# On the Raspberry Pi (Debian Trixie)
bash scripts/bootstrap_rpi.sh
source ~/.bashrc
ss-test           # smoke-test motors (dry-run)
ss-start          # FastAPI dashboard on :8080
```

## Layout

```
tracker/      motor controller, geostationary look-angle math, sniffer stub
web/          FastAPI dashboard with Tracker + Inmarsat tabs
scripts/      bootstrap + bench test CLI
vendor/       reserved for inmarsat-sniffer submodule (not yet vendored)
docs/archive/ historical plans and integration design
```
