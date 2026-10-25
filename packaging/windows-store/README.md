# OM Power Control — Store MSIX candidate

This package is prepared locally for review. It has not been submitted, certified
or published. Do not distribute it as an installable release.

The production identity is reserved in Partner Center. identity.json contains
public package identifiers only; no account credentials or source RTF are copied.
Store package version 1.0.31.0 maps to application version 0.1.31. This separate
numbering starts above zero and leaves the final field zero for Store use.
The first candidate targets Windows 11 x64; Windows 10 is not enabled by this
manifest. Validation to date is on Windows 11 build 26300.

Build from the already signed portable app:

```powershell
.\scripts\build-windows-msix.ps1 -SdkBin 'C:\path\to\matching\WindowsSDK\x64'
```

The script creates a separate staging folder, audits all notices/binaries, wraps
the unchanged portable app and makes a semantically validated MSIX plus checksum
and a local build record in dist/msix. It does not sign with the Azure certificate,
install the app, submit a package, or contact an amplifier.

The Store-assigned GUID publisher differs from the portable app's Gregory Miller
signing certificate. Do not change either identity to make them appear to match.
The outer Store candidate remains unsigned; Microsoft handles package signing
after certification. The inner EXE retains its existing valid Azure signature.
The exact Store identity passed offline Sandbox startup, simulated tuning,
preferences, reinstall and uninstall using a matching temporary test signature.
WACK's package-file workflow passed twice, including DPI. The optional bundled
runtime finding is reviewed in WINDOWS-STORE-RUNTIME-REVIEW.md and retained in
reports; it does not block local Store preflight. S mode is not validated.

Normal launches default to OFFLINE SIMULATION. No hardware launch arguments are
present in the package manifest. The operator supplies/stops RF and sets drive;
the app never keys a radio or changes drive power. Hardware tests need separate
operator authorization, and none are part of this packaging work.

With Store identity, package data is expected under:
`%LOCALAPPDATA%\Packages\GregoryMiller.OMPowerControl_ry0zqgvak7bfy\LocalCache\Local\OM Power Control\`.
The exact identity/path was validated in the offline Sandbox. Uninstall removes
package data; migration/export from the portable app is not implemented.

Local capability/listing/privacy/support drafts are prepared in content/ and
the root PRIVACY.md. Remaining before submission: content approval, validated
Store-user workflow release-build acceptance (WINDOWS-STORE-LAUNCH.md), public policy URL, listing assets,
pricing/availability decisions and operator approval. Physical monitor checks remain deferred. Store
delivery and SmartScreen behavior are not established by building this candidate.

Reference: https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/msix/app-package-requirements
