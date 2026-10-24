# Windows preview validation — October 23, 2026

Local source: df916b9, based on public release v0.1.31. The release tag resolves
to 64bfb6d122135f3c6faddbd4e5ec6f310d310336; the default branch differs only in
five screenshot files. Application code matches that release before this port.

Environment: Windows 11 x64, Python 3.12.14 in the project .venv,
pywebview 6.2.1, pythonnet 3.2.1, PyInstaller 6.22.3,
WebView2 Evergreen 156.0.4314.42. Git and Node were already available through
the development toolchain; no global/system package installation was performed.

## Completed checks

- Python discovery: 116 tests, 110 passed, six optional private-capture tests skipped.
- Restricted no-RF readiness coverage verifies the exact ordered mode/entry/
  preparation/Exit/mode bytes, no power or Stop commands, no retries after an
  unexpected acknowledgment, idle/fresh-state guards and no false tuning success.
  UI tests verify disabled controls and explicit instructions not to transmit.
- Restricted power-cycle coverage verifies shutdown-before-power-on ordering,
  rejection of Operate/tuning and extra commands, simulated cooling -> Off ->
  warm-up -> Standby, RF/stale-data guards, no early power-on, and rejection of
  an injected mode command before it reaches the socket.
- Restricted mode-test coverage verifies two mode bytes maximum, rejection of
  power/tuning bytes, ordered Standby -> Operate -> Standby requests, duplicate
  suppression, RF guards and a command allowance not reset by reconnecting.
- Windows reader guard now uses a named OS mutex as well as the file lock.
  Offline regression tests reject a second process even with a different
  application-data folder and verify cleanup after initialization failure.
  This addresses a second desktop instance getting connection refused while
  the original instance still owns the amplifier session.
- Read-only mode: offline tests verify rejection of every operating/tuning byte,
  combined or unknown requests, backend and localhost API controls, shared-control
  calls and an injected pending command. UI tests verify all operating/tuning
  buttons remain disabled, including Stop during reported tuning.
- UTF-8 regression: UI assets load correctly even when the default file encoding
  is Windows-1252. Native smoke testing also checks unavailable-reading dashes
  and temperature degree symbols after disconnecting the simulator.
- Five JavaScript suites passed, including the original presentation/UI tests,
  auto-tune presentation/UI tests, and Windows bridge/simulation UI tests.
- Simulated worker tests forbid real socket creation and exercise the original
  decoder and control state machine: two-stage tuning entry, waiting Exit,
  success/save, RF release/default restoration, Stop/RF-off/Exit/user settings,
  unknown tuning replies, lost connection, RF command guards and no retries.
- Localhost HTTP tests check CSRF tokens and rejection of simulation inputs in
  hardware mode. Hardware connection is blocked without explicit startup opt-in.
- Windows lock test verifies a second process is rejected and the lock is released.
- Native WebView2 smoke test passed from source and the frozen Windows EXE.
  It checks rendered Standby, compact/full view, native stay-on-top, Operate,
  auto-tune readiness, synthetic operator RF, completion/save, RF still active
  after completion, simulated operator RF off, Dismiss and application shutdown.
- Frozen EXE test exited with code 0. Diagnostic log recorded
  `OFFLINE WEBVIEW2 SMOKE TEST PASSED`.
- PyInstaller produced the portable folder and approximately 14 MB ZIP, with a
  SHA-256 sidecar. `git diff --check` passed.

## Boundaries

The initial offline validation made no real amplifier connection. After the
operator explicitly authorized read-only telemetry, a single real connection was
established with the rebuilt Windows EXE using `--read-only`. It confirmed a CON
session acknowledgment and fresh Standby, antenna, frequency and temperature
telemetry. The session request history contains only C, ?, # and F; operating and
tuning command history is empty. Unavailable power/SWR remain unavailable rather
than being invented as zero. No RF transmission was requested for this check.

The operator subsequently authorized exactly one Operate -> Standby test and
confirmed the radio was idle with no RF. The restricted Windows test session
verified fresh Standby/no-transmit telemetry, sent one Operate mode toggle,
received the exact amplifier acknowledgment and reported Operate, then sent
one Standby mode toggle and received its acknowledgment. The command trace
contains exactly two sends and two confirmations, with no retries. Both observed
transitions reported no RF. The exhausted test session was closed and the normal
read-only desktop session restored with fresh Standby/no-transmit telemetry and
an empty command history. The operator independently confirmed the final
front-panel Standby indication and subsequently verified disconnect/reconnect
and desktop-shortcut restart without changing the amplifier's state.

The operator then explicitly authorized one normal shutdown/cooling and power-on/
warm-up cycle, ending in Standby, with no Operate, tuning or RF. The restricted
`--power-test` session sent exactly one shutdown and received its acknowledgment.
The amplifier reported Cooling down and counted down to confirmed Off; the
operator independently confirmed physical cooling completion and shutdown.
Only after fresh Off telemetry, one power-on command was sent and acknowledged.
The amplifier reported a 180-second warm-up, counted down, and then confirmed
Standby. The operator confirmed the timer finished. Sampled telemetry remained
connected and reported no RF. Both power commands were sent once with no retries;
the cycle trace contains only off/on. The normal read-only desktop session was
restored and confirmed fresh Standby with no RF and an empty command history.
The operator independently confirmed the final front-panel Standby indication.

Before this cycle, one idle read-only telemetry timeout was observed. A single
read-only reconnect restored fresh Standby/no-RF data before the test began.
The cause of that idle timeout is not established; it remains a separate
reliability observation for further investigation.

The operator next authorized one no-RF readiness/Exit test, including Operate
and return to Standby, and prohibited power commands. The restricted desktop
session confirmed fresh Standby/no RF, sent Operate once, and received its exact
acknowledgment. Auto-tune selection and preparation were each sent once after
the expected response, and the amplifier reported WAITING FOR INPUT POWER.
No RF was supplied or reported. A single waiting-state Exit received AUTOESC;
the app reported cancelled with no tuning-save indication. One final mode
command received the Standby acknowledgment, independently confirmed by the
operator. The trace contains exactly five command sends and four completed
requests, with no retries, power commands or Stop commands. The normal read-only
desktop session was restored with fresh Standby/no-RF telemetry and no commands.

An RF-assisted tune has not been authorized or performed for this Windows port.
The operator separately authorized an RF-output-only test using existing tuning,
with one Operate and return-to-Standby pair, no tuning or power commands, and RF
supplied/stopped entirely by the operator. Restricted mode confirmed Operate,
then 22 telemetry snapshots captured 1178-1217 W forward, 46 W reflected,
19-20 W input and calculated SWR 1.4827-1.4925. The operator reported matching
station/front-panel meter values. RF release was explicitly confirmed: TX cleared,
forward/reflected/input returned to zero, and SWR became unavailable. Standby
was acknowledged afterward. The trace contains exactly two mode sends and two
confirmations, with no retries and no tuning/power commands.

The initial read-only restart after that RF test received no amplifier data and
timed out. One read-only session reconnect restored fresh Standby/no-RF telemetry
with an empty command history. This is another reconnect-reliability observation;
its cause is unconfirmed and should be investigated before RF-assisted tuning.

No radio was keyed and no radio drive setting was changed. Simulation remains
entirely in memory; the browser uses only the app's numeric loopback server.

## Reconnect investigation

After the operator closed the disconnected Mac client, five baseline read-only
connection cycles all returned fresh Standby telemetry and confirmed COFF on
release. The original intermittent timeout did not reproduce. Closing the Mac
client does not establish that it caused the earlier failures.

Offline regressions exposed shared-backend defects: the session parser accepted
the first acknowledgment even when a later acknowledgment in the same batch
reported a closed session, and could overlook a fragmented later acknowledgment.
It now uses the latest complete acknowledgment and waits for an incomplete later
session reply. Setup time no longer consumes the ten-second telemetry timeout;
session acknowledgments alone cannot count as live telemetry. A later COFF ends
monitoring with an explicit session-closed error. No automatic reconnect or
operating-command retry was added. Six initial regression cases failed against
the old implementation; all eight new cases pass with the correction.

The corrected actual app worker passed five more read-only connection cycles,
each observed beyond ten seconds, with fresh Standby/no-RF telemetry, confirmed
session release and an empty operating-command history. The rebuilt EXE also
connected in read-only mode with fresh Standby telemetry. Private traces remain
in ignored `.tmp/`; they are excluded from source and portable packages.
Two packaged-desktop disconnect/reconnect cycles also passed, each observed for
16 seconds with fresh Standby telemetry and no commands. A graceful desktop
close/restart restored the read-only session; a subsequent 25-second sampled
check stayed connected in Standby, without RF or operating commands.
These results verify the corrections but do not prove the cause of the original
intermittent hardware timeout.

Both platforms use these Python modules. The Mac launcher now explicitly selects
hardware mode so that the new backend simulation default does not silently
change its behavior. Its Swift wrapper has not been compiled or hardware-tested
on this Windows PC; the existing Mac installation has not been changed.

This is an unsigned local development preview. Hardware acceptance, clean-machine
installation, mixed-DPI/multiple-monitor testing, redistribution-notice review,
signing and public distribution remain separate release work. Further operating
commands, power-sequence tests and real auto-tune acceptance require separate
explicit operator approval.

## Files and commands

Run the desktop app from `dist/windows/OM Power Control/OM Power Control.exe`.
Ordinary launches are always simulated. Keep its `_internal` folder alongside it.
Portable archive: `dist/OM-Power-Control-0.1.31-windows-x64-preview.zip`.

Development commands are in WINDOWS.md. Build scripts handle the read-only
attributes OneDrive assigns to generated directories; cleanup is confined to
the two named generated build/output directories under this repository.

This source is proposed for review before merging. The Mac build and reconnect
checks remain pending; the existing Mac release has not been updated. Local
binaries, station settings and private diagnostic traces are excluded from Git.
