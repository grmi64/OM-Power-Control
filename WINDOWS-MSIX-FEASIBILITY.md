# Windows Store/MSIX feasibility — 2026-10-24

**Result: local MSIX packaging is technically feasible without an application
code rewrite.** This is a Windows 11 Sandbox result, not Store certification,
Store-delivery testing, or a resolution of the portable ZIP's SmartScreen warning.

## Prototype

The existing Azure-signed portable app from merged main a914b5e was copied into
an MSIX payload. Its EXE, Python runtime, Python.NET/CLR loader, HTML/JavaScript,
WebView2 SDK files and notices were unchanged. The payload passed the existing
offline notice audit (55 notice/source files, 78 binary fingerprints).

The package uses a distinct OMPowerControl.Feasibility identity, x64 architecture,
packagedClassicApp/mediumIL activation, and runFullTrust. This is a normal desktop
process with package identity, not an AppContainer. The minimum manifest target
is Windows 10 build 19041; only Windows 11 build 26300 was tested.

MakeAppx semantic validation passed using Microsoft.Windows.SDK.BuildTools
10.0.28000.2705. Matching SDK SignTool and Appx signing dependencies signed and
verified both local test packages with the existing Azure profile and RFC 3161
timestamps. No Store package was submitted; Azure signing sends a digest, not
a Store submission. No test certificate or trusted-root change was needed.

## Observed offline results

All app tests ran in a fresh Sandbox configured with networking disabled and
zero network adapters. No amplifier endpoint was supplied or probed.

| Check | Result |
|---|---|
| Installation | Signed MSIX installed under WindowsApps; registration status Ok |
| Actual package identity | Queried from the activated process; matched installed package |
| Python.NET / WebView2 | Actual packaged WebView2 window loaded; no code or DLL patch |
| DPI / native bridge | PerMonitorV2, actual HWND DPI/minimum, native notification and bridge checks passed |
| UI simulation | Built-in full/compact, stay-on-top, tuning/save, simulated RF release and dismiss/disconnect smoke passed |
| Clean exit | Smoke and lifecycle launches exited with code 0 |
| Preferences | Secondary meter saved and restored after close/reopen |
| Update | Local 0.1.31.0 -> 0.1.31.1 update retained family identity and saved preference |
| Updated process | Actual identity changed to the expected updated package full name |
| Uninstall | Package unregistered; package-specific app data removed |
| Reinstall | Default meter restored; no stale saved preference |
| No-argument activation | Defaulted to simulation, simulated Standby, RF off, sharing disabled |
| Single-reader guard namespace | Unpackaged test process could open the active packaged app's named reader mutex |

Windows redirected app data to:
`%LOCALAPPDATA%\Packages\OMPowerControl.Feasibility_p09vee0wej578\LocalCache\Local\OM Power Control\`.
That family name is specific to this local prototype. The existing portable data
location and installed production app on the host were not changed. The package
was removed from the guest after testing.

## Store/release work still required

- Reserve a real Store identity and apply Partner Center's identity/publisher to
  production packaging. The current Azure certificate matches the local prototype
  publisher; Store identity/signing must be handled through the Store workflow.
- Use Store-compliant production versioning. The fourth-field increment above
  exercised local sideload updates only; it is not a Store versioning recommendation.
- Review/justify runFullTrust, prepare listing/privacy/support information, and
  run Windows App Certification Kit checks. Approval has not been established.
- Turn the reference layout into a repeatable production build and signing flow.
- Recheck standard-user installation and Store-managed delivery/update behavior
  with the actual Store identity. No Windows versions beyond the tested guest are
  validated by this feasibility run.
- Document package-specific diagnostics, uninstall data removal, and any future
  migration from portable settings. No migration was implemented or tested.
- Keep physical monitor checks deferred as previously agreed. No live amplifier
  or LAN telemetry testing occurred; missing-PTTOFF recovery remains replay-only.
- This sideload test does not demonstrate warning-free installation of an
  Internet-marked MSIX or SmartScreen behavior for the GitHub ZIP.

The Store's eventual approval and distribution remain separate decisions. Do not
publish these prototype identities/packages as the Windows release.

## Evidence and reproducibility

`packaging/msix-feasibility/AppxManifest.xml.in` preserves the validated layout
with publisher/version placeholders. Private tool provenance, payload, signed
packages, helpers and consolidated results are under `.tmp/msix-feasibility/`.
Guest results are `msix-install.json`, `msix-smoke.json`, `msix-smoke.log`,
`msix-lifecycle.json`, and `msix-default-launch.json` in the ignored Sandbox
results folder. The latter explicitly verifies default simulation and visibility
of the reader mutex across package contexts.

Original portable EXE SHA-256 remains
`344b9dd684aea9a92b598d11a220bfb3aeb30d965421de5be467769ad7933ef1`;
original ZIP remains
`14b7b5108c3a785e4cba29cf3ef06af889b539119d1de73c1a29946a0446fdfb`.

References: [Manual MSIX layout](https://learn.microsoft.com/en-us/windows/msix/desktop/desktop-to-uwp-manual-conversion),
[packaged desktop behavior](https://learn.microsoft.com/en-us/windows/msix/desktop/desktop-to-uwp-behind-the-scenes),
[package activation API](https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nf-shobjidl_core-iapplicationactivationmanager-activateapplication),
[restricted capabilities](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/app-capability-declarations),
and [Store package/version requirements](https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/package-version-numbering).

No amplifier connection, operating/tuning/power command, radio keying, drive
adjustment, Store registration/submission, GitHub publication or host MSIX
installation occurred. Local test packages were signed with the existing service;
no new signing subscription or purchase was made. New source artifacts/results
remain local and uncommitted.
