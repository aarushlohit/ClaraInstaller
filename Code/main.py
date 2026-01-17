import subprocess

def run_ps(cmd, show=False):
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", cmd],
        capture_output=True,
        text=True
    )
    if show and result.stdout:
        print(result.stdout)
    return result.returncode

print("============= OneClickFedoraInstaller =============")

# ---------------- DISK SELECTION ----------------
while True:
    print("\nAvailable disks:")
    run_ps("Get-Disk | Format-Table Number, FriendlyName, Size", show=True)

    diskNum = input("\nEnter target disk number (must contain Windows OS): ").strip()

    code = run_ps(
        "$bp = Get-Partition | Where-Object IsBoot -eq $true | Select-Object -First 1;"
        "if(!$bp){ exit 2 };"
        f"if($bp.DiskNumber -eq {diskNum}){{ exit 0 }} else {{ exit 1 }}"
    )

    if code == 0:
        print("✅ Disk verified")
        break

    print("❌ Wrong disk. Please try again.")

# ---------------- PARTITION SIZE ----------------
while True:
    try:
        sizeGB = int(input("\nEnter Linux partition size in GB (minimum 6): "))
        if sizeGB >= 6:
            break
        print("❌ Minimum size is 6GB")
    except ValueError:
        print("❌ Enter a valid number")

# ---------------- SHRINK WINDOWS (FIXED) ----------------
print("\n[INFO] Shrinking Windows OS partition...")

code = run_ps(
    "$bp = Get-Partition | Where-Object IsBoot -eq $true | Select-Object -First 1;"
    "$vol = Get-Volume -Partition $bp;"
    "$sup = Get-PartitionSupportedSize -Partition $bp;"
    f"$shrink = {sizeGB} * 1GB;"
    "$new = $vol.Size - $shrink;"
    "if($new -lt $sup.SizeMin){ exit 1 };"
    "Resize-Partition -Partition $bp -Size $new"
)

if code != 0:
    print("❌ Shrink failed (Windows limitation, not Python)")
    exit(1)

print("✔ Windows partition shrunk")

# ---------------- CREATE LINUX PARTITION ----------------
print("[INFO] Creating Linux partition...")

code = run_ps(
    f"$p = New-Partition -DiskNumber {diskNum} -Size {sizeGB}GB -AssignDriveLetter;"
    "Format-Volume -Partition $p "
    "-FileSystem NTFS "
    "-NewFileSystemLabel 'LINUXOS' "
    "-Confirm:$false"
)

if code != 0:
    print("❌ Linux partition creation failed")
    exit(1)

print(f"\n✅ SUCCESS: Linux partition created ({sizeGB} GB)")
