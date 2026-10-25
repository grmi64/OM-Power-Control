# Store-user connection modes — offline review, 2026-10-24

Implemented in source and an isolated Store-identity review build; offline tests
passed. Existing signed EXE/ZIP and unsigned Store candidate were preserved and
do not yet contain this feature. No amplifier connection or publication occurred.

## Instructions for the next build

1. Open OM Power Control from Start. It opens in OFFLINE SIMULATION, even after
   a previous hardware session. No terminal command or package path is needed.
2. Disconnect the current session. Under Connection mode, choose Offline
   simulation, Read-only amplifier telemetry, or Amplifier controls and tuning.
   The panel remains visible in compact view; use Full view if you need the
   existing Disconnect button.
3. For an amplifier mode, enter its address and TCP port (default 10001).
   Keep physical RF off while changing modes. Read-only blocks operating,
   tuning and power commands. Hardware controls permit them subject to existing
   model/state guards.
4. Select Apply mode and reopen. Amplifier modes require explicit confirmation;
   Cancel leaves the existing policy unchanged.
5. The app reopens **disconnected**, ignoring saved auto-connect for this
   handoff. Check its title and connection state. Connect is a separate action;
   do not click it in a hardware mode during offline acceptance testing.
6. Disconnect before changing mode again. A normal new Start-menu launch always
   returns to simulation; the hardware mode choice is not saved.

Connection settings can be saved through the existing Connection & station form
in the chosen session. Simulation settings remain separate. The operator supplies
and stops RF and sets drive power; the app never keys a radio or adjusts drive.
Changing mode sends no operating, tuning or power command. Closing never sends
amplifier power-off. If reopening fails, start normally to return to simulation.

## Implementation and guards

The Windows host injects windows_access.html/js into its copy of the shared UI;
Mac UI/backend behavior is unchanged. windows_access.py validates mode, endpoint,
explicit confirmation, disconnected state and absence of pending/RF activity.
The native bridge rechecks state independently of the JavaScript disabled button.
Restricted mode/power/readiness/tune and ordinary smoke sessions cannot upgrade.

The bridge returns its request before JavaScript asks WebView2 to close. The
native close handler accepts that only with an armed request. Reader/server/lock
cleanup finishes before restarting the same executable with structured argv,
shell=False and PyInstaller environment reset. Every UI handoff includes
--start-disconnected, which overrides a supplied endpoint and saved auto-connect.
Existing explicit CLI behavior is preserved when this flag is absent.
main restores the previous OM_SETTINGS_PATH before relaunch, preventing the
temporary simulation override from following a subsequent hardware launch.
No alias, elevated process, service or extra capability was added.

## Offline evidence and limits

Final suite: 197 Python tests, 191 passed and six expected skips; all six
JavaScript suites passed. New tests cover confirmation/cancel/error handling,
invalid endpoints, disconnected/pending/RF gates, restricted sessions, duplicate
requests, structured self-launch, environment restoration and startup with an
explicit endpoint plus saved auto-connect. Native/network/feed components are
mocked for hardware-policy startup tests.

The isolated review EXE was packaged with the exact Store identity and signed
only with a disposable Sandbox certificate. Unsigned review MSIX SHA-256:
`9e466b30cd4084f63a0d690b83fee84b63b019ee2ac42aa303db51806d2f47e6`.
The 55 notice/source files and pinned dependency binaries passed their audit.
This is not a production signed artifact.

The real packaged --access-smoke-test exercised the mode panel, compact visibility,
connected-state blocking and cancellation of read-only/hardware choices. It then
switched **only to simulation**. Parent and child both retained native identity
`GregoryMiller.OMPowerControl_1.0.31.0_x64__ry0zqgvak7bfy` and exited zero.
The child verified disconnected startup before explicit simulated Connect and
passed real WebView2/DPI plus simulated tune/save/RF-release smoke checks.
Read-only/hardware choice construction was tested with mocks; no amplifier or
live hardware-mode connection was used to test the new workflow.

The first packaged attempt exposed a bridge-reply/disposal race, fixed and
retested without disposed-WebView2 errors. An early headless test needed its
companion feed mocked to avoid a loopback shutdown wait; the final test does so.
Neither involved an amplifier connection; neither counts as final pass evidence.

Test package and temporary certificate were removed; zero network adapters were
confirmed. Private evidence is under .tmp/access-mode-review/ and
.tmp/clean-pc-test/results/access-review-{install,test,cleanup}.json plus
access-review-windows.log.

Review the source, rebuild/sign a new release candidate and repeat package-file
WACK/final artifact acceptance before publication. Earlier WACK passes apply to
the old unchanged candidate. Update listing screenshots and remaining content
decisions. Hardware testing of this workflow needs separate authorization.

## Pre-commit review fixes — 2026-10-24

The two launch-workflow review findings are fixed in source:

- Invalid hostname labels and option-like addresses such as --hardware are
  rejected before arming a handoff, leaving the current window open. Normal
  IPv4 addresses, local names, internal hyphens and qualified names remain
  supported. Valid endpoints use --host=value so endpoint text cannot be parsed
  as another option by the replacement process.
- Native validation errors persist across the 500 ms UI refresh. They clear on
  address/port edits, a mode change or a retry. A rejected request never asks the
  window to close; a successful retry waits for the bridge reply before closing.

Added regressions cover malformed/option-like addresses, no armed handoff on
failure, accepted endpoint forms, actual argument parsing through mocked startup,
error persistence across timer ticks, each edit path and successful retry.
Final offline suite after these fixes: 199 Python tests, 193 passed and six
expected skips; all six JavaScript suites passed. Private output is in
.tmp/launch-fixes/tests.log.

These fixes have not been rebuilt into an EXE/MSIX during this step. The previous
packaged handoff test remains evidence for that earlier isolated review build;
new signed-candidate/package acceptance is still required. Existing release
EXE/ZIP/MSIX hashes are unchanged. No amplifier connection, commit, push, merge,
submission or publication occurred.
