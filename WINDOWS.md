# OM Power Control for Windows â€” development preview

Port baseline: public v0.1.31 source, commit df916b9. This preview reuses the
original HTML/JavaScript interface, decoder, single socket worker and automatic
tuning state machine. The Swift/WebKit host is replaced by Python/pywebview and
Microsoft Edge WebView2. The macOS host remains in Sources/.

## Run the packaged desktop app

Extract the entire ZIP to a writable local folder and run `OM Power Control.exe`.
Keep the `_internal` directory beside the executable. Python is included.
Windows x64 and the Microsoft Edge WebView2 Evergreen Runtime are required.
PerMonitorV2 startup requires Windows 10 version 1703 or newer APIs; validation
has been performed on Windows 11. Other Windows builds are not yet validated.
Source builds are unsigned unless separately signed after building. The local
release candidate has been signed with Azure Artifact Signing as Gregory Miller.
Trusted publisher signing is required before public release. Windows reputation
warnings can still appear for new downloads. See WINDOWS-RELEASE-NOTES.md for
publication gates; do not bypass protection warnings during acceptance tests.

**Every ordinary launch is OFFLINE SIMULATION.** No amplifier socket is opened,
saved hardware auto-connect is ignored, and DX Caliber sharing is disabled in
simulation. The amber simulation panel and window title identify synthetic data.
Simulation settings use a separate file from real station settings.

1. Start in simulated Standby. Choose Go to Operate.
2. Choose Auto-tune and confirm. Wait for WAITING FOR INPUT POWER.
3. Click Simulated RF on. A successful simulated tune completes in four seconds.
4. Click Simulated RF off after completion or Stop. RF never stops automatically.
5. Test waiting-state Exit, RF-off interruption/default restoration, or Stop,
   RF off, then Exit/settings saved. Neither interruption is successful tuning.
6. Select Unexpected tuning reply, Lost telemetry, or Connection lost before
   supplying simulated RF to explore faults. For lost telemetry, wait ten seconds
   for disconnect. Reconnect starts a new simulator in Standby with RF off.

The simulator is deliberately synthetic. It tests protocol handling and UI
behavior; it cannot validate timing, calibration or protections of real equipment.

## Development on a Windows PC

Install Python 3.12 x64, Git and Node.js, and the WebView2 Evergreen Runtime if
missing. No Swift, Xcode or Visual Studio compiler is required for this host.
From PowerShell in the repository folder:

```powershell
.\scripts\setup-windows.ps1
# Or supply a known Python 3.12 executable:
.\scripts\setup-windows.ps1 -Python 'C:\path\to\python.exe'
.\.venv\Scripts\python.exe windows_app.py
.\scripts\test-windows.ps1
.\scripts\build-windows.ps1
```

`requirements-windows.lock.txt` records all Python dependency versions used for
the preview. The shorter requirements file lists the direct dependencies.
Build output is `dist/windows/OM Power Control/OM Power Control.exe`; the portable
ZIP and SHA-256 sidecar are in `dist/`. PyInstaller must run on Windows to build
the Windows executable. Source-only offline HTTP mode is also available:

```powershell
.\.venv\Scripts\python.exe live.py --simulate --port 0
```

Open the numeric loopback URL printed by that command. The desktop wrapper runs
the same server in-process on a random loopback port. Closing the window stops
the worker and HTTP server, releases the instance lock and closes communication.
It never sends amplifier power-off on application exit.

## Hardware access requires separate operator approval

For an approved telemetry-only session, launch with `--read-only`. It permits
only session lifecycle (`C`) and status/measurement/frequency queries (`?`, `#`,
`F`); operating and tuning commands are blocked in the UI, backend and socket
writer. DX Caliber sharing is disabled for this mode. An approved endpoint can
be supplied without changing saved settings:

```powershell
.\.venv\Scripts\python.exe windows_app.py --read-only --host AMPLIFIER-IP --amp-port 10001
```

The approved endpoint connects once at startup. There is no automatic reconnect.
Ordinary launches still default to offline simulation. Switching to operating
commands requires a separate process launch and separate operator authorization.

`--mode-test` is a separate, explicitly authorized acceptance-test mode for
Standby -> Operate -> Standby with the radio idle. It permits only two single
mode commands in that order; power and tuning bytes remain blocked at the socket.
The test uses the existing command queue, fresh-telemetry/RF guards and exact
mode acknowledgments. Commands are driven by the test; the UI buttons remain
disabled. Reconnecting cannot reset a used command allowance. On completion,
close this test process and return to the desktop read-only shortcut.

`--power-test` is a separately authorized normal shutdown/cooling and power-on/
warm-up acceptance test. It allows exactly one shutdown from fresh Standby, then
one power-on only after confirmed Off. It rejects Operate, tuning, retries and
power-on while cooling. The amplifier controls its own cooling/warm-up timing;
no command bypasses a countdown. The test is complete only when the amplifier
reports Standby after warm-up. UI controls remain disabled while the test drives
the two commands; return to the read-only shortcut afterward.

`--readiness-test` is an explicitly authorized no-RF acceptance test: Standby ->
Operate -> auto-tune selection/readiness -> waiting-state Exit -> Standby. The
socket permits exactly the ordered mode/entry/prepare/Exit/mode bytes, once each;
power and Stop commands are blocked. Each step requires the expected amplifier
state, fresh telemetry and no transmit indication. Unexpected acknowledgments
stop progress without retries, and reconnecting cannot reset the command budget.
Keep the radio idle throughout. This test must not report successful tuning or
saved tuning settings; it checks readiness and cancellation only. Return to the
normal read-only desktop shortcut after completion.

`--tune-test` is an explicitly authorized operator-driven RF acceptance test.
The normal mode/tuning buttons are enabled; power buttons are disabled and power
bytes are blocked by both backend and socket policy. The session allows one
Operate/Standby pair, one two-stage automatic-tuning entry, and at most one Stop
and Exit for recovery. Fresh-state, RF, acknowledgment and no-retry guards still
apply. The operator supplies/stops RF; no RF is generated or adjusted by the app.
DX Caliber sharing is disabled. Reconnecting cannot reset a used test allowance.
After completion, close this process and return to the read-only shortcut.

Do not launch `windows_app.py --hardware`, `live.py --hardware`, or the packaged
executable with `--hardware` until the operator has explicitly approved connecting
to the amplifier. That option permits real Ethernet access and saved auto-connect.
There is no in-app switch from simulation to hardware.

After approval, configure and save the amplifier address and TCP port, then
Connect. OM-3501A remains the only command-enabled model; other model labels
remain monitoring only. Existing transmission guards, one outstanding command,
acknowledgment requirements and no automatic operating-command retries remain.
Only amplifier-confirmed completion counts as successful automatic tuning.

The operator supplies and stops tuning RF at the manufacturer-prescribed drive.
The app has no radio/CAT interface, never keys a radio and never changes its drive
power. Stop stops amplifier tuning only. Exiting or disconnecting is not a way to
stop RF or turn off the amplifier. Preserve the manufacturer's operating limits,
warm-up/cooling sequences and equipment protections.

## Settings and diagnostics

For an operator-authorized read-only reconnect investigation, close the desktop
app and run the bounded diagnostic from the project folder:

```powershell
.\.venv\Scripts\python.exe scripts/diagnose_reconnect.py --host AMPLIFIER-IP --port 10001 --cycles 5 --observe 13 --worker --output .tmp/reconnect-diagnostic.json
```

It acquires the same single-reader guard, requires Standby/no RF, and permits only
session lifecycle and telemetry requests. Without `--worker`, it records raw
protocol replies for diagnosis. Keep all traces private in ignored `.tmp/`;
do not upload them to GitHub or include them in portable packages. See
WINDOWS-VALIDATION.md for results and limits of the reconnect investigation.

Windows files live under `%LOCALAPPDATA%\OM Power Control\`:

- `settings.json`: real station settings; auto-connect defaults off.
- `simulation-settings.json`: separate simulated station preferences.
- `window.json`: compact mode, stay-on-top and full window size.
- `instance.lock`: process lock; its presence does not mean the app is running.
- `windows.log`: startup and wrapper diagnostics.
- `WebView2/`: embedded browser runtime data.

For an authorized diagnostic session, add `--trace-telemetry` to the existing
launch arguments. This saves exact amplifier receive/transmit bytes and decoded
events in a timestamped `telemetry-trace-*.jsonl` file in this private application
data directory. Tracing does not grant hardware access or change command policy;
`--read-only --trace-telemetry` still permits only session and telemetry requests.
Each trace is capped at 10 MiB; logging then stops without retrying commands or
ending the amplifier session. Tracing is off by default. Logs can contain station
telemetry; keep them private and exclude them from GitHub and portable packages.

`OM_SETTINGS_PATH` overrides the settings file for isolated tests. The current
development environment was created with the Python 3.12.14 runtime already
available on this PC; recreating the venv with a standalone Python installation
makes development independent of that runtime's location. The frozen EXE is
independent of the development venv.

## Validation and release limits

Run `scripts/test-windows.ps1` for decoder, protocol, command, auto-tune, simulated
worker, localhost API, process-lock, preferences and JavaScript UI tests. Private
capture tests skip when their optional files are absent. A real WebView2 smoke
test is available with `windows_app.py --smoke-test` or the EXE `--smoke-test`;
it is always offline and closes its window after checking UI/native controls,
automatic tuning, simulated operator RF, saving and result dismissal.

Read-only amplifier telemetry has been authorized and checked; see
WINDOWS-VALIDATION.md. A single explicitly authorized Operate -> Standby pair
has also been confirmed by the amplifier. One separately authorized normal
shutdown/cooling and power-on/180-second warm-up cycle also returned to confirmed
Standby, with exactly one off/on pair and no retries. One separately authorized
no-RF readiness/Exit test also confirmed WAITING FOR INPUT POWER, acknowledged
Exit without a tune/save, and returned to operator-confirmed Standby without
power commands. One later operator-driven RF-assisted tune confirmed successful
completion and automatic saving, operator RF release, and acknowledged Standby.
Exactly one mode pair and one two-stage tune were sent, without power commands
or retries. The passive monitor observed a separate brief 3.1-second telemetry-age
excursion after completion; fresh data returned without reconnecting. See the
validation report for details.
The subsequent Ethernet RF retest completed tuning and saving but exposed an
expired transmit indication that blocked the app's Standby button; the operator
returned the amplifier to Standby from its front panel. That retest is not a
full acceptance pass. Expired RF-active indications now show RF state unconfirmed
and retain the command guard. Successful tuning does not itself confirm RF-off;
keep RF off and check the amplifier when its RF state is unconfirmed. The cause
of the missing RF-off indication still needs event capture before another RF test.
The later raw-traced retest received PTTON but no PTTOFF. Static inspection of
the official vendor client established its post-save compatibility rule: a fresh
plate-current change from nonzero to zero ends the transmit indication after a
saved tune. The shared decoder now implements this narrow rule and successfully
replays the failed capture. Ordinary zero current and a timer do not clear RF;
the guard stays active while RF state is unconfirmed. A subsequent authorized
Ethernet test passed tuning, saving, explicit PTTOFF detection and app-driven
return to Standby. That run did not exercise the compatibility fallback live;
its evidence remains the offline replay of the earlier failed capture.
An RF-output-only check using existing tuning produced approximately 1.2 kW
forward at 19-20 W input, with 46 W reflected and about 1.49 calculated SWR;
the operator confirmed matching meters. TX cleared and power returned to zero
after RF release. Only the Operate/Standby pair was sent, and read-only monitoring
was restored. A startup telemetry timeout required one session reconnect; see
the validation report's unresolved reliability observations.
A clean Windows Sandbox test of merged main passed offline packaged startup,
simulated auto-tune, full/compact views, second-instance rejection, clean exit
and restored compact/always-on-top preferences. The guest had no Python command
and no network adapters. Mac and Windows normal auto-tune acceptance passed with
explicit PTTOFF; the missing-message fallback remains offline-replay verified
only. See WINDOWS-VALIDATION.md for evidence and limits.
Standard-user execution also passed in the offline Sandbox: the app ran from a
read-only program folder, completed simulated tuning, saved per-user settings,
exited cleanly and restored the meter preference on reopening.
Missing-WebView2 handling passed an offline Sandbox test using a process-only
empty-runtime override. The local Windows host now checks the bundled loader
before starting the backend and shows install/repair guidance instead of a blank
window. Removing the override restored normal simulation. WebView2 was not
uninstalled and no runtime was downloaded. The preflight/dialog changes and
their regressions are included in the current Windows release-readiness review.
Actual Windows 100%, 125%, 150% and 200% full/compact checks passed in a separate
host simulation profile after a local fix to keep windows inside the current
monitor's work area. The original Windows scale was restored. The fix and six
geometry regressions are included in that review. Only one physical monitor
was available; physical multiple-monitor/mixed-DPI checks remain pending.
PR #3's follow-up fixes verify PerMonitorV2 before GUI/backend startup, obtain
minimum-size DPI from the actual HWND, and use native DPI notifications instead
of the disabled WinForms event. The packaged offline smoke test checks the real
context, minimum size and native callback before running simulated tuning.
PR #3 is merged into main. Dependency-notice review for the pinned Windows
bundle is complete; see ThirdPartyNotices/windows/README.txt and inventory.json.
Physical multiple-monitor checks remain deferred; trusted signing is required
before publication, and the local candidate EXE is signed.
Sandbox does not establish support for other Windows builds.
Packaged Sandbox tests of unexpected tuning replies, lost telemetry and
disconnection also passed, including guarded controls and no false success or
retries. A local simulator-only cleanup fix preserves the original error reason;
it and its regressions are included in that review. These changes do not require
additional live RF testing to validate their intended behavior.
The initial distribution is a portable ZIP, not an installer.

Dependency references: https://pywebview.flowrl.com/guide/installation.html and
https://pyinstaller.org/en/stable/ . See LICENSE and ThirdPartyNotices.
