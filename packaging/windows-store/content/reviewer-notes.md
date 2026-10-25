# Certification reviewer notes — local draft

Application: OM Power Control by Gregory Miller. Store identity
GregoryMiller.OMPowerControl; package version 1.0.31.0; application version 0.1.31.
No Store upload or submission has occurred.

## Access and prerequisites

No app account, credentials, subscription, amplifier or radio is needed to test
the default simulated interface. Use Windows 11 x64 with Microsoft Edge WebView2
Evergreen Runtime already installed. Python is bundled. The app runs as the
interactive standard user, without administrator elevation.

Ordinary package/Start-menu activation opens OFFLINE SIMULATION. No amplifier
network socket is opened in this mode, saved hardware auto-connect is ignored,
and DX Caliber sharing is disabled. Keep this mode for certification exploration;
do not connect test equipment or supply real RF.

## Offline test sequence

1. Launch the app normally. Verify SIMULATION in the window/UI and the warning
   that data is synthetic. The simulated amplifier starts in Standby.
2. Switch between full and compact views. Simulation labeling and simulated RF
   controls remain visible. Check stay-on-top and the secondary-meter selector.
3. Select Go to Operate, then Auto-tune and confirm. Wait for the simulated
   WAITING FOR INPUT POWER state.
4. Click Simulated RF on. A successful simulated tune completes in about four
   seconds and reports successful tuning/save. These are synthetic readings;
   no physical RF or amplifier is involved.
5. Click Simulated RF off, dismiss the result and return to simulated Standby.
6. Optionally use the simulator's unexpected reply, lost telemetry and connection
   lost scenarios to inspect error states. Start each case from a fresh simulated
   session. Faults are not successful tunes.
7. Change a display preference, close the app and reopen it. Check that the
   preference returns and simulation remains the startup mode. Uninstall removes
   the tested package's application data; reinstall starts with defaults.

## Purpose of restricted capability

runFullTrust supports the packaged Win32 Python/Windows Forms/WebView2 desktop
architecture, local HTTP UI, native DPI/window APIs, per-user files and explicitly
authorized amplifier TCP communication. See the separately prepared explanation.
It is not a request for administrator execution, driver installation or a service.

## Local pre-submission results and limitations

The exact-identity package passed offline installation, real WebView2/UI/DPI,
simulated tuning/save/RF release, preference/reopen and uninstall checks.
Package-file WACK completed twice with overall PASS and all required tests
passing. Use the package-file workflow for local reproduction; installed-identity
analysis showed a DPI-parser error for the unchanged EXE's WindowsApps path.

The optional Blocked executables finding identifies CPython/PyInstaller runtime
process APIs and command-like strings in bundled runtimes. It was reviewed and
retained as informational, not suppressed. A bounded offline process trace saw
only expected WebView2 descendants. See WINDOWS-STORE-RUNTIME-REVIEW.md for the
exact binary evidence and limits; S mode compatibility is not claimed.

Previously operator-authorized Mac/Windows hardware tests are separate from this
offline certification exercise. Actual RF tuning requires an OM-3501A, an
experienced operator and their RF/drive control. The app never keys the radio or
sets drive power. Hardware tests are not requested in these reviewer notes.

The Connection mode workflow in WINDOWS-STORE-LAUNCH.md passed offline simulation
handoff tests in an isolated Store-identity build. Reviewers can inspect/cancel
hardware choices without connecting; applying a mode reopens disconnected. Do
not click Connect in a hardware mode during offline checks. Older signed artifacts
do not yet contain this change. New-candidate acceptance, listing assets and the
public privacy URL still need review. These notes do not claim Store approval.
