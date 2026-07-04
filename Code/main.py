import subprocess
import os
import sys
import tempfile
import re
import shutil

ISO_FILENAME = "clara-desktop.iso"
DEFAULT_ISO_URL = "https://releases.ubuntu.com/24.04/ubuntu-24.04.1-desktop-amd64.iso"
PARTITION_LABEL = "LINUXOS"
MIN_SIZE_GB = 10
BOOT_DESC = "Clara Desktop Linux"
FIRMWARE_UEFI = "UEFI"
FIRMWARE_BIOS = "BIOS"

ADK_DOWNLOAD_URL = "https://go.microsoft.com/fwlink/?linkid=2271338"
ADK_INSTALLER = "adksetup.exe"
ADK_BOOTSECT_PATHS = [
    r"C:\Program Files (x86)\Windows Kits\10\Assessment and Deployment Kit\Deployment Tools\amd64\bootsect.exe",
    r"C:\Program Files (x86)\Windows Kits\10\Assessment and Deployment Kit\Deployment Tools\x86\bootsect.exe",
    r"C:\Program Files\Windows Kits\10\Assessment and Deployment Kit\Deployment Tools\amd64\bootsect.exe",
    r"C:\Program Files\Windows Kits\10\Assessment and Deployment Kit\Deployment Tools\x86\bootsect.exe",
]


def run_ps(cmd, show=False):
    full_cmd = f'powershell -Command "{cmd}"'
    result = subprocess.run(
        ["cmd.exe", "/c", full_cmd],
        capture_output=True,
        text=True
    )
    if show and result.stdout:
        print(result.stdout)
    return result.returncode, result.stdout, result.stderr


def run_cmd(cmd, show=False):
    result = subprocess.run(
        ["cmd.exe", "/c", cmd],
        capture_output=True,
        text=True
    )
    if show and result.stdout:
        print(result.stdout)
    return result.returncode, result.stdout, result.stderr


def get_ps_output(cmd):
    full_cmd = f'powershell -Command "{cmd}"'
    result = subprocess.run(
        ["cmd.exe", "/c", full_cmd],
        capture_output=True,
        text=True
    )
    return result.stdout.strip()


def select_disk():
    while True:
        print("\nAvailable disks:")
        run_ps("Get-Disk | Format-Table Number, FriendlyName, Size", show=True)

        raw = input("\nEnter target disk number (must contain Windows OS): ").strip()
        if not raw.isdigit():
            print("❌ Enter a valid disk number")
            continue

        code, _, _ = run_ps(
            "$bp = Get-Partition | Where-Object IsBoot -eq $true;"
            "if(!$bp){ exit 2 };"
            f"if($bp.DiskNumber -eq {raw}){{ exit 0 }} else {{ exit 1 }}"
        )

        if code == 0:
            print("✅ Disk verified")
            return int(raw)

        print("❌ Wrong disk. Please try again.")


def select_size():
    while True:
        try:
            sizeGB = int(input(f"\nEnter Linux partition size in GB (minimum {MIN_SIZE_GB}): "))
            if sizeGB >= MIN_SIZE_GB:
                return sizeGB
            print(f"❌ Minimum size is {MIN_SIZE_GB}GB")
        except ValueError:
            print("❌ Enter a valid number")


def shrink_windows(sizeGB):
    print("\n[INFO] Shrinking Windows OS partition...")
    code, _, _ = run_ps(
        "$bp = Get-Partition | Where-Object IsBoot -eq $true;"
        "$vol = Get-Volume -Partition $bp;"
        "$sup = Get-PartitionSupportedSize -Partition $bp;"
        f"$new = $vol.Size - {sizeGB}GB;"
        "if($new -lt $sup.SizeMin){ exit 1 };"
        "Resize-Partition -Partition $bp -Size $new"
    )

    if code != 0:
        print("❌ Shrink failed (Windows limitation)")
        sys.exit(1)

    print("✔ Windows partition shrunk")


def get_partition_drive_letter(diskNum):
    output = get_ps_output(
        f"$last = Get-Partition -DiskNumber {diskNum} | "
        "Sort-Object PartitionNumber | Select-Object -Last 1; "
        "$last.DriveLetter"
    )
    return output.strip()


def create_linux_partition(diskNum, sizeGB):
    print("[INFO] Creating Linux partition...")
    code, _, _ = run_ps(
        f"$p = New-Partition -DiskNumber {diskNum} -Size {sizeGB}GB -AssignDriveLetter;"
        "Format-Volume -Partition $p "
        "-FileSystem NTFS "
        f"-NewFileSystemLabel '{PARTITION_LABEL}' "
        "-Confirm:$false"
    )

    if code != 0:
        print("❌ Linux partition creation failed")
        sys.exit(1)

    drive_letter = get_partition_drive_letter(diskNum)
    if not drive_letter:
        drive_letter = PARTITION_LABEL

    print(f"✔ Linux partition created as {drive_letter}:")
    return drive_letter


def select_iso_source():
    print("\n[ISO SOURCE]")
    print("  1) Provide a local ISO file path")
    print("  2) Download from a URL (default: Ubuntu 24.04)")
    choice = input("\nChoose (1 or 2, default 2): ").strip()

    if choice == "1":
        while True:
            path = input("Enter full path to ISO file: ").strip().strip('"')
            if os.path.exists(path):
                print(f"✔ Using local ISO: {path}")
                return path
            print("❌ File not found at that path")
    else:
        url = input("Enter download URL (or press Enter for default Ubuntu 24.04): ").strip()
        if not url:
            url = DEFAULT_ISO_URL
        print(f"✔ Using URL: {url}")
        return url


def download_iso(source):
    if os.path.exists(source):
        size_mb = os.path.getsize(source) // (1024 * 1024)
        print(f"✔ Using local ISO ({size_mb} MB)")
        return source

    print("\n[INFO] Downloading Clara Desktop ISO...")
    iso_path = os.path.join(tempfile.gettempdir(), ISO_FILENAME)

    if os.path.exists(iso_path):
        size_mb = os.path.getsize(iso_path) // (1024 * 1024)
        if size_mb > 100:
            print(f"✔ ISO already exists ({size_mb} MB)")
            return iso_path
        print("Partial download found, re-downloading...")
        os.remove(iso_path)

    ps_script = (
        f"$url = '{source}'; "
        f"$out = '{iso_path}'; "
        "Write-Host 'Downloading Clara Desktop (this may take a while)...'; "
        "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; "
        "try { "
        "Invoke-WebRequest -Uri $url -OutFile $out -UseBasicParsing -TimeoutSec 3600; "
        "} catch { "
        "Import-Module BitsTransfer -ErrorAction SilentlyContinue; "
        "if(Get-Command Start-BitsTransfer -ErrorAction SilentlyContinue) { "
        "Start-BitsTransfer -Source $url -Destination $out; "
        "} else { exit 1 } "
        "}"
    )
    code, out, err = run_ps(ps_script, show=True)
    if code != 0:
        print("❌ ISO download failed")
        print(f"   Error: {err[:200] if err else 'Unknown'}")
        sys.exit(1)

    size_mb = os.path.getsize(iso_path) // (1024 * 1024)
    print(f"✔ ISO downloaded ({size_mb} MB)")
    return iso_path


def extract_iso(iso_path, drive_letter):
    print(f"\n[INFO] Extracting ISO to drive {drive_letter}:\\...")
    target = f"{drive_letter}:\\"

    script = (
        "$ErrorActionPreference = 'Stop'; "
        f"$img = Mount-DiskImage -ImagePath '{iso_path}' -PassThru; "
        "$dl = ($img | Get-Volume).DriveLetter; "
        "if (-not $dl) { exit 1 }; "
        f"robocopy '$dl`:\" \"{target}\" /E /COPYALL /R:1 /W:1 > `$null; "
        f"$rc = $LASTEXITCODE; "
        f"Dismount-DiskImage -ImagePath '{iso_path}'; "
        "if ($rc -ge 8) { exit 1 } else { exit 0 }"
    )
    code, _, _ = run_ps(script)

    if code != 0:
        print("❌ ISO extraction failed")
        return False

    print("✔ ISO extracted successfully")
    return True


def detect_firmware():
    code, out, _ = run_ps("(Get-FirmwareType).ToString()")
    if code != 0:
        return FIRMWARE_BIOS
    out = out.strip()
    return FIRMWARE_UEFI if out == FIRMWARE_UEFI else FIRMWARE_BIOS


def locate_efi_file(drive_letter):
    candidates = [
        f"{drive_letter}:\\EFI\\ubuntu\\shimx64.efi",
        f"{drive_letter}:\\EFI\\BOOT\\BOOTX64.EFI",
        f"{drive_letter}:\\efi\\boot\\bootx64.efi",
        f"{drive_letter}:\\EFI\\ubuntu\\grubx64.efi",
    ]
    for path in candidates:
        if os.path.exists(path):
            rel = path.split(":", 1)[1]
            return rel
    return None


def configure_efi_boot(drive_letter):
    print("\n[INFO] Configuring EFI boot files...")

    efi_dir = f"{drive_letter}:\\efi\\boot"
    run_cmd(f'if not exist "{efi_dir}" mkdir "{efi_dir}"')

    efi_rel = locate_efi_file(drive_letter)
    if efi_rel:
        src = f"{drive_letter}:{efi_rel}"
        dst = f"{efi_dir}\\bootx64.efi"
        run_cmd(f'copy /y "{src}" "{dst}"')
        print(f"✔ EFI file copied: {efi_rel} → efi\\boot\\bootx64.efi")
    else:
        run_ps(
            f"Get-ChildItem -Path '{drive_letter}:\\' -Recurse -Filter '*.efi' "
            "| Select-Object -First 5 FullName | Format-Table -AutoSize",
            show=True
        )
        print("⚠ No EFI file found. Boot may need manual configuration.")


def _add_adk_to_path():
    for p in ADK_BOOTSECT_PATHS:
        if os.path.isfile(p):
            d = os.path.dirname(p)
            if d not in os.environ.get("PATH", ""):
                os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
            return True
    return False


def ensure_bootsect():
    if shutil.which("bootsect.exe") or shutil.which("bootsect"):
        return True

    if _add_adk_to_path():
        if shutil.which("bootsect.exe") or shutil.which("bootsect"):
            return True

    print("\n⚠ bootsect.exe not found.")
    print("  Required for BIOS boot sector writing.")
    print(f"  Windows ADK Deployment Tools (~2 GB) will be installed.")
    resp = input("Install Windows ADK Deployment Tools? (Y/n): ").strip().lower()
    if resp == 'n':
        print("⚠ Skipping ADK install. Fallback: partition active flag only.")
        return False

    installer = os.path.join(tempfile.gettempdir(), ADK_INSTALLER)
    print(f"\n[INFO] Downloading ADK setup...")
    rc, _, err = run_cmd(f'curl -L "{ADK_DOWNLOAD_URL}" -o "{installer}"')
    if rc != 0:
        print(f"❌ Download failed: {err.strip()}")
        return False

    print("[INFO] Installing Windows ADK Deployment Tools...")
    rc, _, err = run_cmd(f'"{installer}" /quiet /features OptionId.DeploymentTools /norestart')
    try:
        os.remove(installer)
    except OSError:
        pass

    if rc != 0:
        print(f"❌ ADK install failed (exit {rc})")
        return False

    if _add_adk_to_path():
        print("✔ bootsect.exe installed and ready")
        return True

    print("⚠ ADK installed but bootsect.exe not found in expected path")
    return False


def _run_bootsect(drive_letter):
    rc, _, _ = run_cmd(f"bootsect /nt60 {drive_letter}: /force")
    return rc == 0


def _set_partition_active_by_letter(drive_letter):
    script = (
        f"$v = Get-Volume -DriveLetter {drive_letter}; "
        "if (-not $v) { exit 1 }; "
        "$p = $v | Get-Partition; "
        "if (-not $p) { exit 1 }; "
        "Set-Partition -Partition $p -IsActive $true; exit 0"
    )
    rc, _, _ = run_ps(script)
    return rc == 0


def configure_bios_boot(drive_letter):
    print("\n[INFO] Configuring BIOS boot...")

    ensure_bootsect()
    bootsect_ok = _run_bootsect(drive_letter)
    active_ok = _set_partition_active_by_letter(drive_letter)

    if bootsect_ok:
        print("✔ Boot sector written")
    else:
        print("⚠ bootsect.exe not available; partition set active")

    if active_ok:
        print("✔ Partition set as active")
    else:
        print("⚠ Could not set partition active")

    return bootsect_ok or active_ok


def add_bcd_entry(drive_letter, firmware):
    print("[INFO] Adding boot entry to Windows Boot Manager...")

    app_type = "OSLOADER" if firmware == FIRMWARE_UEFI else "BOOTSECTOR"
    rc, out, _ = run_cmd(
        f'bcdedit /create /d "{BOOT_DESC}" /application {app_type}'
    )

    guid = None
    for line in out.splitlines():
        m = re.search(r'\{[0-9a-f\-]+\}', line)
        if m:
            guid = m.group(0)
            break

    if not guid:
        print("❌ Failed to create BCD entry")
        return None

    commands = [
        f'bcdedit /set {guid} device partition={drive_letter}:',
        f'bcdedit /set {guid} description "{BOOT_DESC}"',
        f'bcdedit /displayorder {guid} /addlast',
    ]

    if firmware == FIRMWARE_UEFI:
        efi_rel = locate_efi_file(drive_letter) or "\\EFI\\boot\\bootx64.efi"
        commands.insert(1, f'bcdedit /set {guid} path "{efi_rel}"')
        commands.append(f'bcdedit /set {guid} locale en-US')
        commands.append(f'bcdedit /set {guid} osdevice partition={drive_letter}:')
        commands.append(f'bcdedit /set {guid} bootmenupolicy Legacy')

    for c in commands:
        run_cmd(c)

    print(f"✔ Boot entry added: {BOOT_DESC}")
    return guid


def set_boot_priority(guid):
    print("[INFO] Setting boot priority...")
    run_cmd(f'bcdedit /default {guid}')
    run_cmd("bcdedit /timeout 15")
    print("✔ Boot order updated")


def prompt_reboot():
    print("\n" + "=" * 50)
    print("✅  INSTALLATION COMPLETE")
    print("=" * 50)
    print("Clara Desktop Linux has been prepared on your system.")
    print("The bootloader is configured to boot into Clara Desktop.")
    print("\n⚠  Save all your work before rebooting!")
    print("=" * 50)

    resp = input("\nReboot now? (y/N): ").strip().lower()
    if resp == 'y':
        print("Rebooting in 5 seconds...")
        run_cmd('shutdown /r /t 5 /c "Rebooting to Clara Desktop Linux installer"')
    else:
        print("You can reboot later to begin installation.")


def main():
    print("============= Clara Desktop Installer =============")
    print("This tool will install Clara Desktop alongside Windows.\n")

    firmware = detect_firmware()
    print(f"✔ Detected firmware: {firmware}")

    diskNum = select_disk()
    sizeGB = select_size()
    shrink_windows(sizeGB)
    drive_letter = create_linux_partition(diskNum, sizeGB)
    iso_source = select_iso_source()
    iso_path = download_iso(iso_source)
    extract_iso(iso_path, drive_letter)

    if firmware == FIRMWARE_UEFI:
        configure_efi_boot(drive_letter)
    else:
        configure_bios_boot(drive_letter)

    guid = add_bcd_entry(drive_letter, firmware)
    if guid:
        set_boot_priority(guid)
    prompt_reboot()


if __name__ == "__main__":
    main()
