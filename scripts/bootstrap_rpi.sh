#!/bin/bash
# Space Station — Raspberry Pi Bootstrap Script
# Tested on: Debian Trixie (RPi OS Lite 64-bit)
# Usage: bash scripts/bootstrap_rpi.sh

set -euo pipefail

REPO_URL="https://github.com/asdfgh0318/space-station.git"
INSTALL_DIR="$HOME/space-station"

echo "========================================="
echo "  SPACE STATION — RPi Bootstrap"
echo "========================================="
echo "Hostname: $(hostname)"
echo "User:     $(whoami)"
echo "OS:       $(grep PRETTY_NAME /etc/os-release | cut -d= -f2 | tr -d '\"')"
echo ""

# Warn if hostname isn't radioteleskop
if [ "$(hostname)" != "radioteleskop" ]; then
    echo "⚠  Hostname is '$(hostname)', expected 'radioteleskop'"
    echo "   Set it with: sudo hostnamectl set-hostname radioteleskop"
    echo ""
fi

# 1. System update
echo "[1/9] System update..."
sudo apt-get update -qq
sudo apt-get upgrade -y -qq

# 2. Install packages
echo "[2/9] Installing packages..."
sudo apt-get install -y -qq \
    python3-pip python3-venv python3-dev \
    python3-lgpio \
    python3-smbus i2c-tools \
    librtlsdr-dev rtl-sdr \
    git

# Optional: pigpio/RPi.GPIO (may not exist on Trixie — don't fail)
echo "  Installing optional GPIO packages (may skip on Trixie)..."
sudo apt-get install -y -qq pigpio-tools python3-pigpio 2>/dev/null || echo "  → pigpio not available (OK)"
sudo apt-get install -y -qq python3-rpi.gpio rpi.gpio-common 2>/dev/null || echo "  → RPi.GPIO not available (OK)"

# 3. Enable I2C
echo "[3/9] Enabling I2C..."
sudo raspi-config nonint do_i2c 0

# 4. Enable USB boot
echo "[4/9] Enabling USB boot..."
sudo raspi-config nonint do_boot_rom E1 2>/dev/null || echo "  → raspi-config boot_rom not supported (OK)"

# 5. RTL-SDR udev rules
echo "[5/9] Setting up RTL-SDR..."
cat << 'UDEV' | sudo tee /etc/udev/rules.d/20-rtlsdr.rules > /dev/null
SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2838", GROUP="plugdev", MODE="0666"
SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2832", GROUP="plugdev", MODE="0666"
UDEV
sudo udevadm control --reload-rules
sudo udevadm trigger

# Blacklist DVB-T driver
echo "blacklist dvb_usb_rtl28xxu" | sudo tee /etc/modprobe.d/blacklist-rtlsdr.conf > /dev/null
echo "blacklist rtl2832" | sudo tee -a /etc/modprobe.d/blacklist-rtlsdr.conf > /dev/null

# 6. Clone or update repo
echo "[6/9] Setting up repository..."
if [ ! -d "$INSTALL_DIR" ]; then
    git clone "$REPO_URL" "$INSTALL_DIR"
else
    cd "$INSTALL_DIR"
    git pull --ff-only || echo "  → git pull failed (maybe local changes — OK)"
fi

# 7. Python virtual environment
echo "[7/9] Setting up Python environment..."
cd "$INSTALL_DIR"
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

# 8. Create start-web.sh helper
echo "[8/9] Creating ~/start-web.sh..."
cat << 'HELPER' > "$HOME/start-web.sh"
#!/bin/bash
cd ~/space-station
source .venv/bin/activate
python web/app.py "$@"
HELPER
chmod +x "$HOME/start-web.sh"

# 9. Add convenience aliases
echo "[9/9] Adding shell aliases..."
ALIAS_BLOCK='
# Space Station aliases
alias ss-update="cd ~/space-station && git pull && source .venv/bin/activate"
alias ss-start="cd ~/space-station && source .venv/bin/activate && python web/app.py"
alias ss-test="cd ~/space-station && source .venv/bin/activate && python scripts/spin_test.py"
alias ss-debug="cd ~/space-station && source .venv/bin/activate && python scripts/motor_test.py test-all"
'

if ! grep -q "Space Station aliases" "$HOME/.bashrc" 2>/dev/null; then
    echo "$ALIAS_BLOCK" >> "$HOME/.bashrc"
fi

# Smoke tests
echo ""
echo "========================================="
echo "  Smoke Tests"
echo "========================================="

# Test lgpio
if python3 -c "import lgpio; h=lgpio.gpiochip_open(0); print('OK'); lgpio.gpiochip_close(h)" 2>/dev/null; then
    echo "✓ lgpio: connected to gpiochip0"
else
    echo "✗ lgpio: cannot open gpiochip0 (may need reboot or permissions)"
fi

# Test pigpio (optional — just report status)
if python3 -c "import pigpio; pi=pigpio.pi(); c=pi.connected; pi.stop(); exit(0 if c else 1)" 2>/dev/null; then
    echo "✓ pigpio daemon: connected (optional)"
else
    echo "· pigpio daemon: not running (OK — using lgpio)"
fi

# Test I2C
if command -v i2cdetect &> /dev/null; then
    echo "✓ I2C tools: installed"
else
    echo "✗ I2C tools: not found"
fi

# Test Python deps
if source "$INSTALL_DIR/.venv/bin/activate" && python3 -c "import yaml, click, rich, fastapi" 2>/dev/null; then
    echo "✓ Python deps: OK"
else
    echo "✗ Python deps: some missing"
fi

# USB boot check
echo ""
if command -v vcgencmd &> /dev/null; then
    BOOT_ORDER=$(vcgencmd bootloader_config 2>/dev/null | grep BOOT_ORDER || echo "")
    if [ -n "$BOOT_ORDER" ]; then
        echo "Boot config: $BOOT_ORDER"
    fi
fi

echo ""
echo "========================================="
echo "  Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Reboot:     sudo reboot"
echo "  2. SSH in:     ssh $(whoami)@$(hostname).local"
echo "  3. Spin test:  cd ~/space-station && source .venv/bin/activate && python scripts/spin_test.py"
echo "  4. Web UI:     ~/start-web.sh  (then open http://$(hostname).local:8080)"
echo "  5. Debug page: http://$(hostname).local:8080/debug"
echo ""
