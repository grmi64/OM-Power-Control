# runFullTrust justification — final local copy

For Gregory Miller's OM Power Control Store package,
GregoryMiller.OMPowerControl, version 1.0.31.0. Prepared for review only;
not submitted. The following text is intended for the restricted-capability
explanation, subject to the fields presented in Partner Center.

## Proposed explanation

OM Power Control is an independent desktop application for monitoring and
operator-controlled operation of an OM Power OM-3501A amateur-radio amplifier.
It packages an existing Python backend and HTML/JavaScript interface in a native
Windows desktop host using pywebview, Python.NET, Windows Forms and Microsoft
Edge WebView2. It requires runFullTrust to run this existing Win32 desktop
architecture as a packagedClassicApp at medium integrity, using the signed
bundled executable and Python/native runtime libraries.

The Connection mode selector can reopen the same packaged executable with
validated mode/endpoint arguments, without a shell, and always disconnected.
The desktop process hosts the UI's HTTP service on 127.0.0.1, maintains a named
mutex to prevent simultaneous local reader processes, stores per-user settings,
window preferences, WebView2 profile data and diagnostics, and uses native Windows
window/DPI APIs. When the operator explicitly launches a hardware access mode,
the backend communicates by TCP with the amplifier address/port supplied by the
operator. An optional, disabled-by-default loopback integration can expose
readings and selected amplifier controls to DX Caliber on the same PC.

The app runs as the interactive standard user. It does not require administrator
elevation, install drivers or services, or register a scheduled task or startup
entry. It does not provide arbitrary shell-command execution or download and
execute user-supplied code. The bundled desktop and WebView2 runtimes are needed
to preserve the existing interface and protocol implementation.

Ordinary launches of this candidate use clearly labeled offline simulation,
with no amplifier connection. Live hardware use requires a separate explicit
hardware access mode. The operator supplies/stops tuning RF and sets drive power;
the app never keys a radio or changes its drive power. In a permitted hardware
mode the app can issue amplifier operating, power or tuning commands, subject to
its mode restrictions and confirmation/state guards. These functions must not be
described as telemetry-only. Closing the app closes communication; it does not
send amplifier power-off.

Certification can inspect and exercise the complete simulated UI without an
amplifier, radio, RF source, credentials or external network access. Detailed
simulation instructions are provided in the reviewer notes.

## Evidence for the explanation

- Manifest: packagedClassicApp, mediumIL, one runFullTrust capability; no
  auto-start extension or hardware launch arguments.
- EXE execution manifest: asInvoker, uiAccess=false, PerMonitorV2.
- Source: windows_app.py, windows_dpi.py, instance_lock.py, settings.py,
  live.py, session_protocol.py and dxc_feed.py.
- Offline packaged standard-user/UI/DPI/simulation checks passed.
- Final-candidate package-file WACK passed, including DPI. The optional runtime
  finding remains visible and is assessed in WINDOWS-STORE-RUNTIME-REVIEW.md.
- Store-user selection/self-relaunch passed offline Store-identity simulation
  tests on the final signed main 510d985 candidate; this does not imply Store approval.
