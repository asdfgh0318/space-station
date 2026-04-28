#!/usr/bin/env bash
# =============================================================================
# bootstrap_rpi.sh -- one-shot system prep for the space-station tracker
# -----------------------------------------------------------------------------
# Target: Raspberry Pi 4B running Debian Trixie 64-bit (Raspberry Pi OS Lite).
#
# What this script does:
#   * Installs APT packages for GPIO (lgpio), RTL-SDR, I2C tooling, and the
#     Python venv runtime.
#   * Pre-installs C++/CMake build deps for the upcoming inmarsat-sniffer
#     integration (see the TODO seam below) so the future submodule merge is
#     a one-command CMake build.
#   * Enables I2C (Waveshare Stepper Motor HAT (B) talks over I2C), writes
#     RTL-SDR udev rules, and blacklists the kernel DVB driver that would
#     otherwise grab the dongle.
#   * Creates a Python venv with --system-site-packages so apt-installed
#     python3-lgpio is visible inside it.
#   * Appends convenience aliases (ss-update / ss-start / ss-test / ss-debug)
#     to ~/.bashrc.
#   * Runs non-fatal smoke tests (lgpio open, Python imports, RTL-SDR USB).
#
# Idempotent: re-running will not duplicate udev/modprobe/bashrc entries.
# Best-effort: optional packages and Pi-only steps print a yellow warning and
# continue rather than aborting the whole run.
#
# Inmarsat seam: a future commit will add vendor/inmarsat-sniffer/ as a git
# submodule. The build deps below are installed up-front so that step reduces
# to `cmake -S vendor/inmarsat-sniffer -B build && cmake --build build`.
# =============================================================================

set -euo pipefail

# -----------------------------------------------------------------------------
# Variables
# -----------------------------------------------------------------------------
INSTALL_DIR=$(cd "$(dirname "$0")/.." && pwd)
VENV_DIR="$INSTALL_DIR/.venv"

if [ -t 1 ] && command -v tput >/dev/null 2>&1; then
    RED=$(tput setaf 1)
    GREEN=$(tput setaf 2)
    YELLOW=$(tput setaf 3)
    RESET=$(tput sgr0)
else
    RED=""
    GREEN=""
    YELLOW=""
    RESET=""
fi

ok()   { echo "${GREEN}[OK]${RESET} $*"; }
warn() { echo "${YELLOW}[WARN]${RESET} $*"; }
err()  { echo "${RED}[ERR]${RESET} $*"; }
info() { echo "==> $*"; }

export DEBIAN_FRONTEND=noninteractive

# -----------------------------------------------------------------------------
# Pre-flight: detect Raspberry Pi
# -----------------------------------------------------------------------------
IS_PI=0
if [ -r /proc/device-tree/model ] && grep -qi 'raspberry pi' /proc/device-tree/model 2>/dev/null; then
    IS_PI=1
    ok "Raspberry Pi detected: $(tr -d '\0' < /proc/device-tree/model)"
else
    warn "Not running on a Raspberry Pi -- continuing in dev-machine mode (skipping Pi-only steps)."
fi

# -----------------------------------------------------------------------------
# APT update + base packages
# -----------------------------------------------------------------------------
info "Updating APT package index..."
sudo apt-get update -y || warn "apt-get update returned non-zero -- continuing."

info "Installing base packages..."
sudo apt-get install -y \
    python3-lgpio python3-pip python3-venv \
    librtlsdr-dev rtl-sdr \
    i2c-tools \
    git curl jq

# pigpio-tools may be unavailable on Trixie -- best-effort.
sudo apt-get install -y pigpio-tools \
    || warn "pigpio-tools not available on this release -- skipping (lgpio is the supported path on Trixie)."

# -----------------------------------------------------------------------------
# TODO: vendor inmarsat-sniffer per docs/archive/merge_plan.html
# Pre-install C++ build deps so the future submodule build is a single CMake
# invocation. Each install is best-effort; a missing package on Trixie should
# not abort the whole bootstrap.
# -----------------------------------------------------------------------------
info "Installing inmarsat-sniffer build deps (best-effort)..."
sudo apt-get install -y cmake build-essential pkg-config \
    || warn "cmake/build-essential install failed -- inmarsat build will need manual fix-up."
sudo apt-get install -y libacars2-dev \
    || warn "libacars2-dev not found on this release -- inmarsat ACARS decode will need manual install."
sudo apt-get install -y libzmq3-dev \
    || warn "libzmq3-dev not found on this release -- inmarsat ZMQ transport will need manual install."
sudo apt-get install -y libmosquitto-dev \
    || warn "libmosquitto-dev not found on this release -- inmarsat MQTT transport will need manual install."

# -----------------------------------------------------------------------------
# Enable interfaces (Pi-only, idempotent)
# -----------------------------------------------------------------------------
if [ "$IS_PI" = "1" ] && command -v raspi-config >/dev/null 2>&1; then
    info "Enabling I2C..."
    sudo raspi-config nonint do_i2c 0 || warn "Could not enable I2C via raspi-config."
    info "Enabling USB-boot ROM (best-effort)..."
    sudo raspi-config nonint do_boot_rom E1 || warn "Could not set USB-boot ROM via raspi-config."
else
    warn "Skipping raspi-config interface tweaks (not on Pi or raspi-config missing)."
fi

# -----------------------------------------------------------------------------
# RTL-SDR udev rules + DVB blacklist
# -----------------------------------------------------------------------------
RTLSDR_RULES=/etc/udev/rules.d/20-rtlsdr.rules
if [ ! -f "$RTLSDR_RULES" ]; then
    info "Writing $RTLSDR_RULES ..."
    sudo tee "$RTLSDR_RULES" >/dev/null <<'EOF'
# RTL-SDR (Realtek RTL2832U) -- accessible to the plugdev group
SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2832", MODE="0660", GROUP="plugdev"
SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2838", MODE="0660", GROUP="plugdev"
EOF
    ok "RTL-SDR udev rules installed."
else
    ok "RTL-SDR udev rules already present -- leaving as-is."
fi

DVB_BLACKLIST=/etc/modprobe.d/rtl-sdr-blacklist.conf
if [ ! -f "$DVB_BLACKLIST" ]; then
    info "Writing $DVB_BLACKLIST ..."
    sudo tee "$DVB_BLACKLIST" >/dev/null <<'EOF'
# Prevent the kernel DVB driver from claiming the RTL-SDR dongle
blacklist dvb_usb_rtl28xxu
blacklist rtl2832
EOF
    ok "DVB blacklist installed."
else
    ok "DVB blacklist already present -- leaving as-is."
fi

info "Reloading udev..."
sudo udevadm control --reload-rules || warn "udevadm reload-rules failed."
sudo udevadm trigger || warn "udevadm trigger failed."

# -----------------------------------------------------------------------------
# Python venv
# -----------------------------------------------------------------------------
if [ ! -d "$VENV_DIR" ]; then
    info "Creating Python venv at $VENV_DIR (with --system-site-packages)..."
    python3 -m venv --system-site-packages "$VENV_DIR"
else
    ok "Python venv already exists at $VENV_DIR."
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
pip install --upgrade pip || warn "pip upgrade failed."
if [ -f "$INSTALL_DIR/requirements.txt" ]; then
    pip install -r "$INSTALL_DIR/requirements.txt" || warn "pip install -r requirements.txt failed."
else
    warn "No requirements.txt at $INSTALL_DIR -- skipping pip install."
fi
deactivate || true

# -----------------------------------------------------------------------------
# Convenience aliases (idempotent: only append if missing)
# -----------------------------------------------------------------------------
BASHRC="$HOME/.bashrc"
add_alias() {
    local name="$1"
    local body="$2"
    if [ -f "$BASHRC" ] && grep -q "alias $name=" "$BASHRC"; then
        ok "alias $name already present in ~/.bashrc"
    else
        echo "alias $name=$body" >> "$BASHRC"
        ok "added alias $name to ~/.bashrc"
    fi
}

info "Installing convenience aliases..."
add_alias ss-update "'cd $INSTALL_DIR && git pull'"
add_alias ss-start  "'cd $INSTALL_DIR && source .venv/bin/activate && python -m web.app --port 8080'"
add_alias ss-test   "'cd $INSTALL_DIR && source .venv/bin/activate && python scripts/motor_test.py --dry-run test-all'"
add_alias ss-debug  "'cd $INSTALL_DIR && source .venv/bin/activate && python -m tracker.controller --sim status'"

# -----------------------------------------------------------------------------
# Smoke tests (never abort the script)
# -----------------------------------------------------------------------------
info "Running smoke tests..."

CHECK="✓"
CROSS="✗"

if python3 -c "import lgpio; h = lgpio.gpiochip_open(0); lgpio.gpiochip_close(h)" 2>/dev/null; then
    echo "${GREEN}${CHECK}${RESET} lgpio: gpiochip0 opens cleanly"
else
    echo "${RED}${CROSS}${RESET} lgpio: could not open gpiochip0 (expected on non-Pi)"
fi

if python3 -c "import yaml, click, rich, fastapi" 2>/dev/null; then
    echo "${GREEN}${CHECK}${RESET} Python deps: yaml, click, rich, fastapi all import"
else
    echo "${RED}${CROSS}${RESET} Python deps: one or more of yaml/click/rich/fastapi failed to import"
fi

if command -v lsusb >/dev/null 2>&1 && lsusb | grep -qiE 'realtek|rtl'; then
    echo "${GREEN}${CHECK}${RESET} RTL-SDR detected on USB"
else
    echo "${RED}${CROSS}${RESET} RTL-SDR not detected on USB (plug the dongle in and re-check with lsusb)"
fi

# -----------------------------------------------------------------------------
# Final summary
# -----------------------------------------------------------------------------
cat <<EOF

${GREEN}=== Bootstrap complete ===${RESET}

Convenience aliases installed in ~/.bashrc:
  ss-update   git pull in $INSTALL_DIR
  ss-start    activate venv and launch the web UI on :8080
  ss-test     run motor_test.py in --dry-run mode
  ss-debug    run the tracker controller in --sim mode

Run:  ${YELLOW}source ~/.bashrc${RESET}   to pick the aliases up in the current shell.

EOF
