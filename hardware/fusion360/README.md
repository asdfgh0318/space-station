# Fusion 360 VM Setup for Antenna Tracker CAD

Fusion 360 runs on Windows and macOS only. This directory contains a provisioning script for setting up a Windows 11 VM on a Linux host using VirtualBox.

## Prerequisites

- VirtualBox 7.0+ installed on the host
- VT-x/VMX enabled in BIOS (verify with `grep -c vmx /proc/cpuinfo`)
- At least 8GB RAM available (the VM uses 6GB by default)
- At least 55GB free disk space (50GB dynamic VDI + Windows + Fusion 360)
- A Windows 11 ISO image

## Getting a Windows 11 ISO

Download the official ISO from Microsoft:

https://www.microsoft.com/software-download/windows11

Select "Download Windows 11 Disk Image (ISO)" and choose your language. The download is approximately 5-6GB. You do not need a product key to install and use Windows 11 -- you can skip the activation step during setup. The only limitation is cosmetic (watermark and disabled personalization settings).

## Quick Start

```bash
# Make the script executable (already done if you cloned the repo)
chmod +x setup_vm.sh

# Create the VM with an ISO attached
./setup_vm.sh /path/to/Win11_23H2_English_x64.iso

# Or create the VM first, attach the ISO later
./setup_vm.sh
VBoxManage storageattach "Fusion360-VM" --storagectl "SATA" \
  --port 1 --type dvddrive --medium /path/to/Win11.iso

# Start the VM
VBoxManage startvm "Fusion360-VM"
```

## What the Script Does

The `setup_vm.sh` script creates a VirtualBox VM with these settings:

| Setting | Value |
|---|---|
| RAM | 6GB |
| CPUs | 4 |
| Disk | 50GB dynamic VDI |
| Graphics | VBoxSVGA, 128MB VRAM, 3D acceleration on |
| Firmware | EFI (required for Windows 11) |
| TPM | 2.0 (required for Windows 11) |
| Secure Boot | Enabled |
| Network | NAT with RDP port forwarding (3389) |
| USB | xHCI (USB 3.0) |
| Clipboard | Bidirectional |
| Drag and Drop | Bidirectional |
| Shared Folder | `hardware/` directory mounted as `H:` in guest |

## Installing Windows 11

1. Start the VM. It will boot from the ISO.
2. Follow the Windows installer.
3. When asked for a product key, click "I don't have a product key".
4. Select Windows 11 Pro or Windows 11 Home.
5. Choose "Custom: Install Windows only" and select the virtual disk.
6. Complete the out-of-box experience (OOBE). If it insists on a Microsoft account and you want a local account, disconnect the network (Shift+F10 -> `ipconfig /release`) before proceeding, or use `oobe\bypassnro` in the command prompt.

## Installing VirtualBox Guest Additions

Guest Additions are required for shared folders, clipboard integration, and better graphics performance. Install them after Windows is running:

1. In the VirtualBox menu bar: **Devices -> Insert Guest Additions CD image...**
2. Open File Explorer in the VM. Navigate to the mounted CD drive.
3. Run `VBoxWindowsAdditions.exe` as Administrator.
4. Follow the installer. Accept the driver installation prompts.
5. Reboot the VM when prompted.

After reboot:
- The shared folder appears as drive `H:` in File Explorer.
- Bidirectional clipboard and drag-and-drop are active.
- Display resolution adjusts to the VM window size.

## Installing Fusion 360

Fusion 360 is free for personal and hobby use.

1. Open a browser inside the VM.
2. Go to: https://www.autodesk.com/products/fusion-360/personal
3. Download the Fusion 360 installer.
4. Run the installer and sign in with (or create) an Autodesk account.
5. When prompted, select the **Personal Use** license.

Installation takes 5-15 minutes depending on network speed.

## Running the Tracker Scripts

The `scripts/` directory contains two files:

- `parameters.py` -- shared dimensions for all tracker parts (bearings, steppers, structure)
- `generate_tracker.py` -- Fusion 360 API script that generates the full antenna tracker assembly

### Setting Up the Script Path

The shared folder mounts the `hardware/` directory as `H:` in the VM. The scripts are located at:

```
H:\fusion360\scripts\generate_tracker.py
H:\fusion360\scripts\parameters.py
```

### Running in Fusion 360

1. Open Fusion 360. Create a new design (or open an existing one).
2. Go to **Utilities -> Scripts and Add-Ins** (or press Shift+S).
3. In the Scripts tab, click the green **+** (Add) button next to "My Scripts".
4. Navigate to `H:\fusion360\scripts` and select the `generate_tracker.py` file.
5. The script appears in the list. Select it and click **Run**.
6. A dialog confirms generation. Click OK.
7. All tracker parts are created as separate components in the Browser panel.

### Editing Parameters

To change dimensions (bearing sizes, wall thickness, etc.):

1. Edit `parameters.py` on the host machine (or in the VM via the shared folder).
2. Re-run `generate_tracker.py` in Fusion 360.
3. The script reads the updated parameters and regenerates all parts.

## Exporting STEP Files

STEP files are the standard interchange format for CAD. To export from Fusion 360:

1. In the Browser panel, right-click the component you want to export.
2. Select **Save As STL** for 3D printing, or for STEP:
   - **File -> Export** (or right-click the component -> **Save As**).
   - Choose format: **STEP Files (*.step, *.stp)**.
   - Save to `H:\fusion360\specs\` or `H:\stl\` as appropriate.
3. The exported files appear on the host machine in the corresponding directory under `hardware/`.

To export the entire assembly as a single STEP file:
1. Right-click the top-level "Antenna Tracker Assembly" component.
2. **Save As** -> STEP format.

## Performance Notes

Running Fusion 360 in a VM is workable but not as smooth as a native installation. Here are the settings that matter most:

**3D acceleration is critical.** The setup script enables VBoxSVGA with 3D acceleration and 128MB VRAM. Without 3D acceleration, Fusion 360's viewport will be extremely slow or may not render at all.

**RAM.** The VM is configured with 6GB. Fusion 360 itself needs 2-4GB. If you find it swapping, you can increase to 8GB if your host has headroom:
```bash
VBoxManage modifyvm "Fusion360-VM" --memory 8192
```

**CPU cores.** 4 cores is adequate for modeling and script execution. Rendering and simulation benefit from more cores but those are not needed for this project.

**Disk I/O.** The dynamic VDI grows as needed. If performance is sluggish, consider placing the VDI on an SSD. You can also pre-allocate the disk:
```bash
VBoxManage modifymedium disk "/path/to/Fusion360-VM.vdi" --compact
```

**Guest Additions driver.** Make sure VirtualBox Guest Additions are installed. The WDDM graphics driver from Guest Additions is what enables 3D acceleration in the guest.

## Alternative: Native Installation

If you have access to a Windows or macOS machine with Fusion 360 already installed, you can skip the VM entirely:

1. Copy (or clone) the `hardware/fusion360/scripts/` directory to the native machine.
2. Open Fusion 360 and run the scripts as described above.
3. Export STEP/STL files and copy them back.

This gives better performance than a VM. The scripts have no dependencies beyond the Fusion 360 API -- just `generate_tracker.py` and `parameters.py` in the same directory.

## Troubleshooting

**VM won't boot / "FATAL: No bootable medium found"**
- Make sure the Windows 11 ISO is attached. Check with:
  ```bash
  VBoxManage showvminfo "Fusion360-VM" | grep "SATA (1, 0)"
  ```

**Windows 11 installer says "This PC can't run Windows 11"**
- The setup script enables TPM 2.0 and Secure Boot. If you still see this error, make sure you are using VirtualBox 7.0 or later.

**Shared folder not visible in guest**
- Confirm Guest Additions are installed.
- Check that the shared folder exists:
  ```bash
  VBoxManage showvminfo "Fusion360-VM" | grep "hardware"
  ```
- Try manually mounting in the guest: open cmd as Administrator and run:
  ```cmd
  net use H: \\vboxsvr\hardware
  ```

**Fusion 360 viewport is black or extremely slow**
- Verify 3D acceleration is enabled:
  ```bash
  VBoxManage showvminfo "Fusion360-VM" | grep -i "3d"
  ```
- Make sure Guest Additions are installed (the WDDM driver is required).
- In Fusion 360, go to Preferences -> General -> Graphics driver and try switching between DirectX and OpenGL.

**generate_tracker.py fails with ImportError for parameters**
- Confirm both `generate_tracker.py` and `parameters.py` are in the same directory.
- If running from the shared folder, Fusion 360 may have trouble with UNC paths. Copy the scripts to a local folder (e.g., `C:\FusionScripts\`) and run from there.

## Deleting the VM

To remove the VM and reclaim disk space:
```bash
VBoxManage unregistervm "Fusion360-VM" --delete
```

This deletes the VM configuration and the VDI disk image.
