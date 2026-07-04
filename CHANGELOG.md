# Changelog

## [1.1.0] — 2026-07-04

### Added
- BIOS firmware support (`detect_firmware`, `configure_bios_boot`)
- PowerShell-native ISO extraction (`Mount-DiskImage` + `robocopy`)
- Graceful fallback when `bootsect.exe` is unavailable
- 15 additional unit tests (55 total)

### Removed
- `SEVENZIP_URL` constant and `ensure_7zip()` function
- `py7zr` / `7zr.exe` dependency and download logic

### Changed
- `add_bcd_entry()` now accepts a `firmware` parameter
- `main()` auto-detects firmware and branches accordingly
- ISO extraction no longer requires external binaries

## [1.0.0] — 2026-06-?? (Initial)

### Added
- UEFI-based dual-boot installation
- Windows partition shrink
- Linux partition creation (NTFS)
- ISO download with fallback to BITS transfer
- 7zr.exe-based ISO extraction
- BCD boot entry creation (OSLOADER)
- Boot priority management
- Reboot prompt
