# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| latest  | ✅                 |
| older   | ❌                 |

Only the most recent release receives security patches.

## Reporting a Vulnerability

If you discover a security vulnerability in Clara Desktop Installer, please report it privately.

**Do not** open a public GitHub issue.

Instead, email **aarush.lohit@example.com** (replace with actual contact) with:

- Description of the vulnerability
- Steps to reproduce
- Affected versions
- Any proof-of-concept if available

You will receive an acknowledgment within **48 hours**, and a fix timeline within **5 business days**.

## Scope

This tool runs with **administrator privileges** and directly manipulates:
- Disk partitions
- Boot configuration (BCD)
- System firmware boot entries

By design, it requires elevated access — but this also means vulnerabilities could be abused for privilege escalation or data destruction. All input validation and error handling is critical.

## Security Considerations for Users

- **Always download from the official repository.** Unofficial copies may contain malicious modifications.
- **Verify checksums** if available in the release notes.
- **Run only on trusted hardware.** The tool modifies boot configuration and partitions.
- **Back up your data** before running the installer.
