import subprocess
import sys
import os

def run_powershell(command):
    """Execute a PowerShell command and return exit code and output."""
    result = subprocess.run(
        ["powershell", "-Command", command],
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout.strip()

def get_windows_disk():
    """Find the disk number containing Windows OS."""
    code, disk_number = run_powershell(
        "$bp = Get-Partition | Where-Object IsBoot -eq $true;"
        "if(!$bp){exit 1};"
        "Write-Output $bp.DiskNumber"
    )
    
    if code != 0:
        print("ERROR: Cannot detect Windows OS disk")
        sys.exit(1)
    
    return disk_number

def select_target_disk(windows_disk):
    """Prompt user to select the target disk."""
    while True:
        run_powershell("Get-Disk | Format-Table Number, FriendlyName, Size")
        selected_disk = input("Enter target disk number (must contain Windows OS): ").strip()
        
        if selected_disk == windows_disk:
            return selected_disk
        
        print("❌ Wrong disk. Try again.")

def get_partition_size():
    """Prompt user for Linux partition size in GB."""
    while True:
        try:
            size_gb = int(input("Enter Linux partition size in GB (minimum 6): "))
            if size_gb >= 6:
                return size_gb
            print("❌ Minimum size is 6GB")
        except ValueError:
            print("❌ Enter a valid number")

def shrink_windows_partition(size_gb):
    """Shrink Windows partition to make room for Linux."""
    print("[INFO] Shrinking Windows OS partition...")
    
    code, _ = run_powershell(
        "$bp = Get-Partition | Where-Object IsBoot -eq $true;"
        "$vol = Get-Volume -Partition $bp;"
        "$sup = Get-PartitionSupportedSize -Partition $bp;"
        f"$new = $vol.Size - {size_gb}GB;"
        "if($new -lt $sup.SizeMin){exit 1};"
        "Resize-Partition -Partition $bp -Size $new"
    )
    
    if code != 0:
        print("ERROR: Shrink failed")
        sys.exit(1)
    
    print("✔ Windows partition shrunk")

def create_linux_partition(disk, size_gb):
    """Create a new partition for Linux."""
    print("[INFO] Creating Linux partition...")
    
    code, _ = run_powershell(
        f"$p = New-Partition -DiskNumber {disk} -Size {size_gb}GB -AssignDriveLetter;"
        "Format-Volume -Partition $p -FileSystem NTFS "
        "-NewFileSystemLabel 'LINUXOS' -Confirm:$false"
    )
    
    if code != 0:
        print("ERROR: Failed to create Linux partition")
        sys.exit(1)
    
    print("✔ Linux partition created (LINUXOS)")

def get_iso_path():
    """Prompt user for ISO file path."""
    while True:
        iso_path = input("Enter FULL path of Linux ISO: ").strip('"')
        
        if os.path.exists(iso_path):
            return iso_path
        
        print("❌ ISO not found. Try again.")

def get_linux_drive():
    """Find the drive letter of the LINUXOS partition."""
    code, drive_letter = run_powershell(
        "$v = Get-Volume -FileSystemLabel 'LINUXOS';"
        "if(!$v){exit 1};"
        "Write-Output ($v.DriveLetter + ':\\\\')"
    )
    
    if code != 0:
        print("ERROR: LINUXOS partition not found")
        sys.exit(1)
    
    return drive_letter

def mount_iso(iso_path):
    """Mount the ISO file."""
    print("[INFO] Mounting ISO...")
    code, _ = run_powershell(f"Mount-DiskImage -ImagePath '{iso_path}'")
    
    if code != 0:
        print("ERROR: Failed to mount ISO")
        sys.exit(1)

def get_iso_drive(iso_path):
    """Get the drive letter of the mounted ISO."""
    code, drive_letter = run_powershell(
        f"(Get-DiskImage -ImagePath '{iso_path}' | Get-Volume).DriveLetter"
    )
    return drive_letter + ":\\"

def copy_iso_contents(iso_drive, linux_drive):
    """Copy ISO contents to Linux partition."""
    print("[INFO] Copying ISO contents to LINUXOS partition...")
    
    code, _ = run_powershell(
        f"robocopy '{iso_drive}' '{linux_drive}' /E /R:1 /W:1 > $null;"
        "if($LASTEXITCODE -ge 8){exit 1}else{exit 0}"
    )
    
    if code != 0:
        print("ERROR: Copy failed")
        sys.exit(1)

def verify_installation(linux_drive):
    """Verify that EFI folder was copied successfully."""
    code, _ = run_powershell(f"if(Test-Path '{linux_drive}EFI'){{exit 0}}else{{exit 1}}")
    
    if code != 0:
        print("ERROR: Verification failed")
        sys.exit(1)

# Main execution
if __name__ == "__main__":
    print("============= OneClickFedoraInstaller (Python) =============")
    
    windows_disk = get_windows_disk()
    print(f"[INFO] Windows OS detected on Disk {windows_disk}")
    
    target_disk = select_target_disk(windows_disk)
    partition_size = get_partition_size()
    
    shrink_windows_partition(partition_size)
    create_linux_partition(target_disk, partition_size)
    
    iso_path = get_iso_path()
    linux_drive = get_linux_drive()
    print(f"[INFO] Linux partition mounted at {linux_drive}")
    
    mount_iso(iso_path)
    iso_drive = get_iso_drive(iso_path)
    
    copy_iso_contents(iso_drive, linux_drive)
    
    run_powershell(f"Dismount-DiskImage -ImagePath '{iso_path}'")
    verify_installation(linux_drive)
    
    print("\n✅ SUCCESS: ISO copied to LINUXOS partition")
    print("Stage-1 complete. Ready for Stage-2 (boot redirection).")
