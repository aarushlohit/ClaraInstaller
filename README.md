# Clara Desktop Installer

Dual-boot installer for **Clara Desktop Linux** from Windows, supporting both **UEFI** and **legacy BIOS** firmware.

## How It Works

```
┌──────────────────────────────────────────────────────────────┐
│  1. Detect firmware (UEFI / BIOS)                             │
│  2. Select target disk (must contain Windows)                 │
│  3. Shrink Windows partition to free space                   │
│  4. Create & format new Linux partition (NTFS)               │
│  5. Download Ubuntu ISO (or use a local one)                 │
│  6. Extract ISO to partition via Mount-DiskImage + robocopy  │
│  7. Write bootloader:                                        │
│     ├─ UEFI → copy EFI file, create BCD OSLOADER entry       │
│     └─ BIOS → bootsect PBR + active flag, BCD BOOTSECTOR     │
│  8. Set boot priority & prompt reboot                        │
└──────────────────────────────────────────────────────────────┘
```

## Requirements

- **OS**: Windows 8 / 10 / 11
- **Privileges**: Administrator (run as admin)
- **Disk**: NTFS system drive with ≥10 GB free space
- **Internet**: Optional — ISO can be provided locally

## Usage

```cmd
# Run as Administrator
python main.py
```

Follow the prompts:
1. Select the disk containing your Windows installation
2. Enter desired Linux partition size (minimum 10 GB)
3. Choose ISO source (download or local file)
4. Confirm reboot when prompted

### Silent / Unattended

This tool is interactive only. For automated deployment, modify `main.py` constants:
- `DEFAULT_ISO_URL`
- `PARTITION_LABEL`
- `MIN_SIZE_GB`
- `BOOT_DESC`

## Project Structure

```
├── Code/
│   ├── main.py          # Installer logic (single file)
│   └── test_main.py     # Test suite (55 tests)
├── LICENSE
├── README.md
├── CONTRIBUTING.md
├── SECURITY.md
├── CODE_OF_CONDUCT.md
└── CHANGELOG.md
```

## Why PowerShell? Why no 7-Zip?

Windows provides native ISO mounting via `Mount-DiskImage`. Using it avoids:
- Downloading external binaries (7zr.exe)
- Dependency on `py7zr` (which does not support ISO 9660)
- Runtime failures when the download server is unavailable

The entire tool runs with **zero external dependencies** beyond what ships with Windows.

## License

This project is open source. You may use, modify, and distribute it freely — including for enterprise use — as long as you **do not claim original authorship or white-label it**. See [LICENSE](LICENSE) for details.
