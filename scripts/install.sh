#!/bin/bash
# Space Station - System setup script for Raspberry Pi
# Run: chmod +x install.sh && sudo ./install.sh

set -e

echo "=== Space Station Setup ==="

# System packages
echo "Installing system packages..."
sudo apt-get update
sudo apt-get install -y \
    python3-pip python3-venv \
    pigpio python3-pigpio \
    python3-smbus i2c-tools \
    librtlsdr-dev rtl-sdr \
    git

# Enable I2C
echo "Enabling I2C..."
sudo raspi-config nonint do_i2c 0

# Enable pigpio daemon
echo "Enabling pigpio daemon..."
sudo systemctl enable pigpiod
sudo systemctl start pigpiod

# RTL-SDR udev rules (allow non-root access)
echo "Setting up RTL-SDR udev rules..."
cat << 'UDEV' | sudo tee /etc/udev/rules.d/20-rtlsdr.rules
SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2838", GROUP="plugdev", MODE="0666"
SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2832", GROUP="plugdev", MODE="0666"
UDEV
sudo udevadm control --reload-rules
sudo udevadm trigger

# Blacklist DVB-T driver (conflicts with SDR usage)
echo "Blacklisting dvb_usb_rtl28xxu..."
echo "blacklist dvb_usb_rtl28xxu" | sudo tee /etc/modprobe.d/blacklist-rtlsdr.conf
echo "blacklist rtl2832" | sudo tee -a /etc/modprobe.d/blacklist-rtlsdr.conf

# Python virtual environment
echo "Setting up Python environment..."
cd "$(dirname "$0")/.."
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "=== Setup Complete ==="
echo "Activate environment: source .venv/bin/activate"
echo "Test SDR: rtl_test -t"
echo "Test I2C: i2cdetect -y 1"
echo "Test encoder: python -m tracker.encoder --watch"
echo ""
echo "NOTE: Reboot recommended for udev and kernel module changes."
