# Windows 0.1.31 preview â€” release candidate

Status: local candidate only; not approved for public release. Application code
is from merged main f5451a35b1104cc70ced414e3d294a4e0a5f16aa (PR #3).

## Changes

- Windows x64 portable desktop app using the existing Python backend and
  HTML/JavaScript interface with a WebView2 wrapper. Python is bundled.
- Preserves automatic tuning, configurable readings, compact view and stay on top.
- Ordinary launches use offline simulation, with separate simulation settings.
  Real amplifier access requires an explicit hardware launch mode.
- Shared Mac/Windows reconnect and RF-state fixes; stale or uncertain RF state
  retains command guards. Operating commands are not automatically retried.
- Clear missing-WebView2 guidance, per-user preferences, and native PerMonitorV2
  sizing and DPI-change handling.

The operator supplies and stops RF and sets drive power. The app never keys a
radio or adjusts its drive power. Stop stops amplifier tuning only.

## Installation

Extract the entire ZIP into a local folder; keep `_internal` beside
`OM Power Control.exe`. Run the EXE for offline simulation. Windows x64 and
Microsoft Edge WebView2 Evergreen Runtime are required. Windows 11 is tested;
other Windows versions have not been validated. See README-Windows.txt for
runtime guidance and separately authorized hardware launch modes.

## Validation and limits

- Offline suite: 170 Python tests passed, six expected skips; five JavaScript
  suites passed. Packaged simulation includes tune/save/RF release and DPI checks.
- Prior Sandbox checks include standard-user operation, failure scenarios,
  saved preferences and missing-runtime handling using a process-local override.
- Operator-authorized Mac and Windows hardware auto-tunes passed with explicit
  PTTOFF. Missing-PTTOFF recovery is verified by offline replay only.
- Physical multiple-monitor and mixed-DPI movement checks remain pending.
- An actually runtime-free Windows installation, other Windows builds, and
  Internet-download reputation have not been validated.
- OM-3501A is the only command-enabled model; other model labels are monitoring
  only. Simulation does not establish real-equipment timing or protections.

## Publication gates

Trusted Windows code signing is REQUIRED by the operator before publication.
The local candidate EXE is now signed through Azure Artifact Signing Basic
using the Public Trust profile ompowerrelease, publisher Gregory Miller.
Host and fresh offline Sandbox signature verification passed with a Microsoft
RFC 3161 timestamp. The signed candidate passed packaged simulation acceptance.
Physical multiple-monitor tests remain deferred; publication is not yet approved.
Do not disable Windows protections or treat a self-signed certificate as trusted
publisher signing. Signing does not guarantee that reputation warnings disappear.

For every subsequent build, sign the final EXE with SHA-256 and an RFC 3161
timestamp, verify the publisher and signature on a clean Windows system, then
recreate the ZIP/checksum and repeat offline acceptance on that exact artifact.
Keep credentials outside the repo. Do not modify the EXE after signing.

Dependency-notice audit completed on 2026-10-24 for the pinned Windows bundle.
The proxy_tools BSD source license and conflicting MIT metadata are both
preserved. Exact WebView2 SDK licenses/NOTICE and missing packaging/vendor
notices are included, with corresponding source for MPL validation modules.
The offline packaging audit rejects notice omissions and dependency/binary drift.
See ThirdPartyNotices/windows/README.txt and inventory.json.

No GitHub release, tag, upload, installer, or signing purchase is authorized by
this preparation work. See WINDOWS-VALIDATION.md for detailed evidence.
