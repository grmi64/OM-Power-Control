# OM Power Control support — local draft

Public support channel selected by the operator:
https://github.com/grmi64/OM-Power-Control/issues

OM Power Control is an independent, open-source project by Gregory Miller and
contributors. It is not official manufacturer support. For amplifier operating
requirements or equipment faults, consult the manufacturer and its documentation.

## What to include in a software issue

- App version and package type: Store MSIX, portable Windows build, or source.
- Windows version/build, x64 architecture and WebView2 Runtime version, if known.
- Whether the problem occurred in simulation, read-only or another hardware mode.
- Steps, expected result and observed result; note whether restarting reproduces it.
- For display issues: scaling percentage, screen resolution and monitor count.
- For an already-authorized hardware observation: amplifier model and firmware,
  without making a new connection or transmission just to collect a report.

Start with offline simulation where possible. Do not perform additional RF,
operating, tuning or power tests merely to open an issue. Use manufacturer
instructions and your station's limits for any separately chosen equipment use.

## Keep public reports free of private data

GitHub issues are public. Do not attach unfiltered settings, raw packet captures,
wire traces, session/control tokens, private IP addresses, credentials or station
identifiers you do not intend to publish. Redact screenshots and diagnostic
excerpts before posting. A private diagnostic upload service is not provided by
this application. Reports are not uploaded automatically.

The Store package's local data is normally under:
`%LOCALAPPDATA%\Packages\GregoryMiller.OMPowerControl_ry0zqgvak7bfy\LocalCache\Local\OM Power Control\`.
Startup information is in windows.log. Optional wire traces are more sensitive,
off by default, and should not be posted publicly without careful review.

## Common checks

- Missing WebView2: follow the app's runtime message; install/repair the Microsoft
  Edge WebView2 Evergreen Runtime separately, then reopen the app.
- Default simulated readings: expected for an ordinary launch of this candidate.
  The next build's Connection mode panel supports explicit selection and a
  disconnected restart (WINDOWS-STORE-LAUNCH.md). Older signed artifacts do not
  yet contain it. Do not infer a live connection
  from synthetic values or simulation controls.
- Stale/unconfirmed readings: treat them as unconfirmed. Do not repeat operating
  commands blindly; the app does not automatically retry them.

There is no response-time commitment in this draft. No support email address,
private upload channel, public website change or issue submission was created.
