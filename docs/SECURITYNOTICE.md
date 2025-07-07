# Security Notice – Antivirus False-Positive Flags on GestureSesh Executable  
**Date:** 2025-07-06

## Description
Some antivirus engines (e.g., Microsoft Defender, Avast, AVG) may flag the Windows `.exe` build of **GestureSesh** as malware or *“Trojan:Win32/Wacatac.C!ml”*, even though the application is safe.  
The alerts are **false positives** caused by the PyInstaller bootloader. PyInstaller is occasionally abused by threat actors, so several AV vendors treat any binary that contains its generic bootloader as suspicious [[1]](#1-pyinstaller-maintainers-on-recurring-av-false-positives-github-issue-6754) [[2]](#2-discussion-of-pyinstaller-false-positives-on-stack-overflow).

## Affected Versions
| Platform | Package Type | Status |
|----------|--------------|--------|
| Windows  | `GestureSesh-*.exe` built with PyInstaller (< v0.5.0 and ≥ v0.5.0) | **Affected** – may trigger AV flags |
| macOS / Linux | `.app`, `.dmg`, or ELF binaries | Not affected |

## Mitigation / Work-arounds
1. **Verify the official checksum** (see the release assets for SHA-256 hashes).  
2. **Whitelist / allow-list** the executable in your antivirus product.  
3. **Submit the file as “false positive”** to your AV vendor’s portal (links below). After enough reports, vendors typically update their signatures.  
4. Always download releases only from the this repo's Releases page or from [https://gesturesesh.com/](https://gesturesesh.com)

| Vendor | False-Positive Submission URL |
|--------|------------------------------|
| Microsoft Defender | <https://www.microsoft.com/wdsi/filesubmission> |
| Avast / AVG | <https://www.avast.com/false-positive-file-form.php> |
| Others | Check vendor website |

## 📅 Disclosure Timeline
| Date | Event |
|------|-------|
| 2025-07-01 | User report of AV flag on v0.5.0 Windows build |
| 2025-07-04 | Internal replication and investigation completed |
| 2025-07-06 | Public disclosure via this notice |

## Reporting & Contact
If you believe you have found a genuine security vulnerability in GestureSesh, **please do not open a public issue.**  
Instead, email **security@gesturesesh.com** with details (CVE, PoC, affected version). 

## References
1. PyInstaller maintainers on recurring AV false positives: [GitHub Issue #6754](https://github.com/pyinstaller/pyinstaller/issues/6754)
2. Discussion of PyInstaller false positives on [Stack Overflow](https://stackoverflow.com/questions/43777106/program-made-with-pyinstaller-now-seen-as-a-trojan-horse-by-avg)