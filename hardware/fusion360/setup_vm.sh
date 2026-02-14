#!/usr/bin/env bash
#
# setup_vm.sh - Create a Windows 11 VirtualBox VM for running Fusion 360
#
# Prerequisites:
#   - VirtualBox 7.0+ installed with VBoxManage on PATH
#   - VMX/VT-x enabled in BIOS
#   - A Windows 11 ISO (download from https://www.microsoft.com/software-download/windows11)
#   - At least 55GB free disk space
#
# Usage:
#   ./setup_vm.sh [path-to-windows11.iso]
#
# If no ISO path is given, the VM is created without an ISO attached.
# You can attach it later via VirtualBox GUI or:
#   VBoxManage storageattach "Fusion360-VM" --storagectl "SATA" \
#     --port 1 --type dvddrive --medium /path/to/Win11.iso

set -euo pipefail

# ============================================================
# Configuration
# ============================================================
VM_NAME="Fusion360-VM"
VM_DIR="$HOME/VirtualBox VMs/${VM_NAME}"
DISK_SIZE_MB=51200          # 50GB dynamic VDI
RAM_MB=6144                 # 6GB RAM (leaves ~17GB for host from 23GB total)
VRAM_MB=128                 # Maximum VRAM for 3D acceleration
CPUS=4
OS_TYPE="Windows11_64"

# Project paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARDWARE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Optional: ISO path from argument
ISO_PATH="${1:-}"

# ============================================================
# Preflight checks
# ============================================================
if ! command -v VBoxManage &>/dev/null; then
    echo "ERROR: VBoxManage not found. Is VirtualBox installed and on PATH?"
    exit 1
fi

# Check if VM already exists
if VBoxManage showvminfo "$VM_NAME" &>/dev/null; then
    echo "ERROR: VM '$VM_NAME' already exists."
    echo "  To delete and recreate: VBoxManage unregistervm '$VM_NAME' --delete"
    exit 1
fi

if [ -n "$ISO_PATH" ] && [ ! -f "$ISO_PATH" ]; then
    echo "ERROR: ISO file not found: $ISO_PATH"
    exit 1
fi

echo "============================================"
echo " Creating VM: $VM_NAME"
echo " RAM: ${RAM_MB}MB | CPUs: $CPUS | Disk: $((DISK_SIZE_MB / 1024))GB"
echo " VRAM: ${VRAM_MB}MB | 3D Acceleration: on"
echo "============================================"
echo ""

# ============================================================
# Create and register VM
# ============================================================
echo "[1/8] Creating VM..."
VBoxManage createvm --name "$VM_NAME" --ostype "$OS_TYPE" --register

# ============================================================
# General settings
# ============================================================
echo "[2/8] Configuring general settings..."
VBoxManage modifyvm "$VM_NAME" \
    --memory "$RAM_MB" \
    --cpus "$CPUS" \
    --vram "$VRAM_MB" \
    --graphicscontroller vmsvga \
    --accelerate3d on \
    --firmware efi \
    --nested-hw-virt on \
    --pae on \
    --ioapic on \
    --hwvirtex on \
    --clipboard-mode bidirectional \
    --draganddrop bidirectional \
    --mouse usbtablet \
    --audio-driver pulse \
    --audio-enabled on \
    --audio-out on \
    --usb-xhci on

# Windows 11 requires TPM 2.0 and Secure Boot
echo "       Enabling TPM 2.0..."
VBoxManage modifyvm "$VM_NAME" --tpm-type 2.0

# Note: --secure-boot not available in VirtualBox 7.0.x
# Windows 11 install works fine with just TPM 2.0 in VBox 7.0+

# ============================================================
# Storage: SATA controller + VDI + DVD
# ============================================================
echo "[3/8] Creating storage..."
VBoxManage storagectl "$VM_NAME" --name "SATA" --add sata --controller IntelAhci --portcount 2

# Create dynamic VDI
VDI_PATH="${VM_DIR}/${VM_NAME}.vdi"
VBoxManage createmedium disk --filename "$VDI_PATH" --size "$DISK_SIZE_MB" --format VDI --variant Standard

# Attach disk
VBoxManage storageattach "$VM_NAME" --storagectl "SATA" --port 0 --device 0 --type hdd --medium "$VDI_PATH"

# Attach ISO if provided
if [ -n "$ISO_PATH" ]; then
    echo "       Attaching ISO: $ISO_PATH"
    VBoxManage storageattach "$VM_NAME" --storagectl "SATA" --port 1 --device 0 --type dvddrive --medium "$ISO_PATH"
else
    echo "       No ISO provided. Attach one before first boot:"
    echo "       VBoxManage storageattach \"$VM_NAME\" --storagectl \"SATA\" --port 1 --type dvddrive --medium /path/to/Win11.iso"
fi

# ============================================================
# Network: NAT with RDP port forwarding
# ============================================================
echo "[4/8] Configuring network..."
VBoxManage modifyvm "$VM_NAME" \
    --nic1 nat \
    --nat-pf1 "rdp,tcp,,3389,,3389"

# ============================================================
# Shared folder: hardware directory
# ============================================================
echo "[5/8] Setting up shared folder..."
VBoxManage sharedfolder add "$VM_NAME" \
    --name "hardware" \
    --hostpath "$HARDWARE_DIR" \
    --automount \
    --auto-mount-point "H:"

echo "       Shared folder: $HARDWARE_DIR -> H: (in guest)"

# ============================================================
# Boot order
# ============================================================
echo "[6/8] Setting boot order..."
VBoxManage modifyvm "$VM_NAME" \
    --boot1 dvd \
    --boot2 disk \
    --boot3 none \
    --boot4 none

# ============================================================
# Display settings
# ============================================================
echo "[7/8] Configuring display..."
VBoxManage modifyvm "$VM_NAME" \
    --monitor-count 1

# Set a reasonable default resolution via extra data
VBoxManage setextradata "$VM_NAME" "CustomVideoMode1" "1920x1080x32"

# ============================================================
# Summary
# ============================================================
echo "[8/8] Done."
echo ""
echo "============================================"
echo " VM '$VM_NAME' created successfully"
echo "============================================"
echo ""
echo " VM location:    ${VM_DIR}"
echo " Disk:           ${VDI_PATH} (${DISK_SIZE_MB}MB dynamic)"
echo " Shared folder:  ${HARDWARE_DIR} -> H: in guest"
echo ""
echo "============================================"
echo " NEXT STEPS (manual)"
echo "============================================"
echo ""
echo " 1. ATTACH ISO (if not provided above):"
echo "    VBoxManage storageattach \"$VM_NAME\" --storagectl \"SATA\" \\"
echo "      --port 1 --type dvddrive --medium /path/to/Win11.iso"
echo ""
echo " 2. START THE VM:"
echo "    VBoxManage startvm \"$VM_NAME\""
echo "    Or open VirtualBox GUI and click Start."
echo ""
echo " 3. INSTALL WINDOWS 11:"
echo "    - Follow the Windows installer."
echo "    - When asked for a product key, click 'I don't have a product key'."
echo "    - Select Windows 11 Pro or Home."
echo "    - Complete OOBE setup."
echo ""
echo " 4. INSTALL GUEST ADDITIONS (after Windows boots):"
echo "    - In VirtualBox menu: Devices -> Insert Guest Additions CD image"
echo "    - Run VBoxWindowsAdditions.exe from the mounted CD in the guest"
echo "    - Reboot the VM"
echo "    - This enables: shared folders, clipboard, drag-and-drop, better graphics"
echo ""
echo " 5. INSTALL FUSION 360:"
echo "    - In the VM, open a browser and go to:"
echo "      https://www.autodesk.com/products/fusion-360/personal"
echo "    - Download the Fusion 360 installer (free for personal/hobby use)"
echo "    - Run the installer and sign in with an Autodesk account"
echo ""
echo " 6. RUN THE TRACKER SCRIPTS:"
echo "    - In Fusion 360: Utilities -> Scripts and Add-Ins -> + (Add)"
echo "    - Navigate to H:\\fusion360\\scripts"
echo "    - Select generate_tracker.py and click Run"
echo "    - See README.md for details"
echo ""
echo " 7. DETACH ISO AFTER INSTALL:"
echo "    VBoxManage storageattach \"$VM_NAME\" --storagectl \"SATA\" \\"
echo "      --port 1 --type dvddrive --medium emptydrive"
echo ""
