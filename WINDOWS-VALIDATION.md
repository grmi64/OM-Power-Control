# Windows preview validation — October 23, 2026

Local source: df916b9, based on public release v0.1.31. The release tag resolves
to 64bfb6d122135f3c6faddbd4e5ec6f310d310336; the default branch differs only in
five screenshot files. Application code matches that release before this port.

Environment: Windows 11 x64, Python 3.12.14 in the project .venv,
pywebview 6.2.1, pythonnet 3.2.1, PyInstaller 6.22.3,
WebView2 Evergreen 156.0.4314.42. Git and Node were already available through
the development toolchain; no global/system package installation was performed.

## Completed checks

- Python discovery: 142 tests, 136 passed, six optional private-capture tests skipped.
- Operator-driven RF-tune scope: offline tests verify one mode pair and one
  two-stage tune, socket/backend rejection of power and extra commands,
  no command-budget reset on reconnect, simulated operator RF ownership,
  confirmed completion/save and final Standby. UI checks verify disabled power
  controls, available tuning controls and exhausted command allowances.
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

Before the later operator-driven RF-tune check below, RF-assisted tuning had
not been authorized or performed for this Windows port.
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
its cause was unconfirmed and was investigated before RF-assisted tuning.

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

The operator subsequently reported that the Mac agent passed three telemetry-only
connection cycles: approximately one-second startup, 13 seconds healthy per cycle,
clean disconnects, no operating/power/tuning/radio commands, and no changes to the
installed app or production settings. PR #1 was merged with operator approval.

## Longer Windows stability and first operator-driven RF tune

The packaged Windows EXE passed a ten-minute read-only Standby check: 594 samples,
maximum telemetry age 2.0 seconds, no RF, no operating commands, no timeouts or
reconnects, and a confirmed clean remote-session close. Private capture:
`.tmp/windows-stability-10min.json`.

The operator then chose to perform a single RF-assisted tune using the Windows
app buttons while the agent passively monitored the localhost state endpoint.
The new `--tune-test` policy enabled mode/tuning controls, blocked all power
commands at the UI/backend/socket, and disabled DX Caliber sharing. The rebuilt
EXE connected in fresh Standby/no RF with an empty command history. The operator
selected Operate, then Auto-tune; each stage was acknowledged and WAITING FOR
INPUT POWER was confirmed. The operator supplied RF. Monitoring captured tuning
in progress, AUTOTUNE DONE and `autotune_saved=true`, then operator RF release:
TX cleared, forward/reflected/input returned to zero, and SWR was unavailable.
The observed tuning phase lasted approximately 8.5 seconds. During RF, sampled
values ranged from 951-2173 W forward, 30-94 W reflected, 20-21 W input and
calculated SWR 1.2663-1.5252. These are sampled app readings, not a new independent
meter calibration check.

The operator intentionally remained in Operate after RF stopped and selected
Standby after the agent's reminder. That command was sent once and acknowledged;
the operator independently confirmed the final Standby action. The command trace
contains exactly `O L & O`: four sends, three completed requests, no retries,
no power commands and no Stop/Exit commands. The monitoring script sent no
operating commands and never controlled RF or drive power.

Separately, roughly 45 seconds after the tune completed, one sample reached a
telemetry age of 3.1 seconds and triggered the passive monitor's freshness limit.
Subsequent inspection found fresh data without any reconnect or retry. This
brief data delay is distinct from the operator's timing of the Standby action;
its cause is unconfirmed. The tune completion/save and final Standby acknowledgments
were all confirmed. Normal read-only monitoring was restored with fresh Standby,
no RF, no error and an empty operating-command history. Private captures remain
in `.tmp/operator-rf-tune*.json*` and are excluded from Git and packages.

## Read-only investigation of the brief data delay

The original trace showed uninterrupted localhost sampling (largest interval
0.24 seconds) and ongoing telemetry polls (largest interval about 1.20 seconds).
Decoded-data age grew past three seconds while those activities continued.

A later instrumented Standby-only worker recorded raw socket reads, decoder
timing and independent state samples. Its first run was interrupted by Windows
Modern Standby: Kernel-Power events 506/507 recorded idle entry at 21:22 and
touchpad-triggered exit at 21:30, America/Los_Angeles. Both worker and sampler
paused for about 451 seconds, and session release was unconfirmed after resume.
That interrupted run is not a successful stability check. There were no power
transition events near the original 21:13 data gap.

A separate five-minute repeat used a temporary process-lifetime Windows awake
request, released when the diagnostic exited. It reproduced a data gap while
the amplifier remained in Standby: maximum socket receive gap 6.187 seconds,
maximum decoded-data gap 7.328 seconds and one stale interval lasting about
4.422 seconds. The longest decoder call was 16 ms and the largest sampler
interval was 0.219 seconds. Queries continued and data recovered without a
reconnect. The run completed and confirmed clean COFF, with no operating,
tuning or power commands. Its completion must not be described as zero-stale
stability acceptance. Only C, ?, # and F were transmitted.

The active route to the amplifier used Wi-Fi. Windows WLAN-AutoConfig events
11004, 11010 and 11005 (wireless security stopped/started/succeeded) occurred
at 21:13:41 during the original gap and at 21:34:55 during the reproduced gap.
This correlation across both events strongly points to Wi-Fi interruption;
it does not establish the underlying adapter/access-point cause. Adapter packet
error/discard counters were zero before and after the investigation. No network
settings or freshness thresholds were changed. Wired Ethernet read-only testing
is the next useful comparison. Raw captures and sanitized event correlation
remain private under ignored `.tmp/telemetry-delay-*` and
`.tmp/wifi-delay-event-correlation.json`.

Normal packaged read-only monitoring was restored after the diagnostic.

The operator then connected Ethernet and disconnected Wi-Fi. Windows confirmed
the amplifier route through Ethernet 2 (100 Mbps). The old Wi-Fi telemetry
session had timed out during the network change; one read-only reconnect
restored fresh Standby/no-RF readings. A five-minute packaged-desktop comparison,
with a temporary awake request, captured 1,391 samples with no stale episodes,
errors, reconnects or state changes. Maximum telemetry age was 1.1 seconds;
maximum sampler interval was 0.235 seconds. Operating-command history remained
empty. Ethernet was verified again after the run, and the normal read-only app
was left connected in Standby. The temporary awake request ended with the check;
saved Windows power settings were not changed. Private results are in
`.tmp/ethernet-readonly-stability*.json*`. This supports the Wi-Fi-path
explanation for the earlier gaps without proving the underlying wireless cause.

## Ethernet RF-tune test: stale transmit indication

The operator separately authorized one RF-assisted tune over Ethernet, using
the Windows app buttons and controlling all RF/drive power, with no power
commands. A fresh `--tune-test` session confirmed Standby, Operate, two-stage
readiness, tuning in progress, AUTOTUNE DONE and automatic saving. The operator
reported that RF was off, but the app retained `transmitting=true` after the
last RF measurement expired. Other telemetry continued to refresh. The mode
button remained blocked by the RF guard. This is not a full acceptance pass.

The operator selected Standby on the amplifier front panel and confirmed it.
Telemetry then reported Standby while the RF latch still remained true. The
trace contains only `O L &`: three sends, two completed requests, no final mode
byte, no Stop/Exit, no retries and no power commands. The agent did not override
the RF guard or send an operating command. The test app was deliberately closed
after the physical RF-off/Standby confirmation, and normal read-only monitoring
was restored with fresh Standby/no-transmit telemetry and no command history.
The passive monitor's final disconnect observation belongs to that intentional
cleanup, not a preceding Ethernet telemetry failure. Private evidence and a
separate assessment remain in `.tmp/operator-ethernet-rf-tune*.json*` and
`.tmp/ethernet-tune-*.json`.

The code held its last RF-active indication until an explicit PTTOFF. Fresh
temperatures/status refreshed the connection, while old RF measurements were
correctly removed. The local correction gives explicit PTT events and binary
RF measurements their own freshness and exposes an expired active indication
as `transmitting=null`, `rf_state_unknown=true`. The UI says RF state unconfirmed
and keeps mode/power/start/Exit paused. The internal transmit latch remains set;
no timeout, non-RF reading or operator assertion silently clears it. Verified
Stop remains available during tuning. Offline regressions verify these rules
and that a fresh explicit PTTOFF clears the indication normally. The underlying
missing/unrecognized RF-off event is not resolved by this display correction;
another RF test requires separate operator approval and additional event capture.

## RF-off framing correction and diagnostic capture

The failed Ethernet RF run saved state snapshots rather than raw wire bytes.
It cannot prove whether PTTOFF was absent or arrived in a form the decoder missed.
The existing read-only receive capture does contain leading NUL bytes attached
to the following ASCII token (`IP0`). Reproducing that observed framing around
a synthetic PTTOFF made the old decoder miss RF-off at every tested TCP split;
NUL padding before a binary measurement also caused ASCII decoding errors.

The decoder now skips NUL bytes only between protocol messages. It preserves all
binary payload bytes and rejects no embedded ASCII bytes silently. Tests cover
every split of a saved-tune/stop sequence, one-byte delivery, padding adjacent to
binary frames, embedded NULs, and guard release only after a recognized PTTOFF.
Padding or fresh temperature messages alone never confirm RF-off. All six new
framing tests pass. Both private Standby receive captures (822 and 544 chunks)
also replay successfully with the corrected decoder.

Opt-in `--trace-telemetry` captures exact socket bytes and decoder events to a
bounded private file under local application data. Five offline trace tests
verify exact byte preservation, raw and decoded RF-off visibility, the existing
read-only socket policy, size limits and logging-I/O failure without command
injection or retries. This fixes a confirmed RF-off parsing failure path; the
specific cause of the prior Ethernet failure remains unproven until raw evidence
is available. No new operating, tuning, RF or power test was performed during
this investigation. The corrections and tracing remain local pending review.

The rebuilt packaged app then passed 30 seconds of read-only Standby validation:
30 samples, maximum telemetry age 1.0 second, no RF/unknown-RF indication, no
errors and an empty operating-command history. Its opt-in trace contained both
exact receive bytes and decoder events; every transmitted request was C, ?, #
or F. The app remains in read-only mode with private bounded tracing enabled.

## Raw-traced Ethernet RF retest: RF-off message absent

The operator separately authorized one further Ethernet auto-tune, including
Operate and return to Standby, using the app buttons and controlling all RF and
drive power, with no power commands. The new session used `--tune-test` and
`--trace-telemetry`. Readiness, tuning in progress, AUTOTUNE DONE and SAVE USER
were confirmed. When RF measurements expired, the corrected UI showed RF state
unconfirmed and retained the command guard. The operator confirmed RF off and
returned the amplifier to Standby from its front panel. Standby was received in
telemetry while RF remained unconfirmed. The full app acceptance test failed.

The closed raw capture contains exactly one PTTON and zero PTTOFF byte sequences
across all received chunks, including session cleanup. Thus the framing fix did
not resolve this reproduced failure: no RF-off token reached the socket to be
decoded. No alternative RF-off token was identified. The largest socket receive
gap was 2.515 seconds; ordinary status/measurement replies continued after
completion. Only `O L &` operating/tuning bytes were sent, once each, with no
Standby byte, Stop/Exit, power commands or retries. The monitor sent no commands.
The session closed with COFF after physical RF-off/Standby confirmation, and the
normal read-only app was restored with fresh Standby/no-transmit telemetry.

The raw-trace test assessment is private in
`.tmp/operator-ethernet-rf-tune-traced-assessment.json`; its raw source remains
in the local application-data trace directory and is excluded from packages.
The monitor's final disconnect is the deliberate test cleanup. NUL framing and
honest RF freshness presentation are corrected, but reliable RF-off recovery
after tuning was still unresolved at that point. Broad inferences from temperature,
plate current, tune completion, elapsed time or operator assertions must not clear
the guard. The subsequent vendor-client investigation below establishes one
narrowly scoped saved-tune exception. No further RF test is authorized by this run.

## Vendor-client compatibility rule and offline recovery proof

The operator reports amplifier software/firmware 3.21. Their recollection that
the front-panel TX indication cleared is tentative, so it is not treated as a
separate measured PTT-off confirmation. No firmware, keying, radio or network
configuration was changed during this investigation.

The manufacturer's official HF PA Manager 3.41 installer was downloaded from
https://www.om-power.com/downloads/file/HF_PA_Manager_v3.41-setup.exe for static
inspection. The client was extracted as data, checksum-verified, and inspected
through .NET metadata/IL; neither the installer nor amplifier client was run.
Only temporary archive/metadata tools were used under ignored `.tmp/`, outside
the app environment. Static inspection identified a saved-tune compatibility
rule: after SAVE USER, an active PTT latch and a fresh plate-current transition
from nonzero to zero cause the vendor client to invoke its own internal PTT-off
handler. It is an internal receive-state update, not a command sent to the amp.
The vendor client clears this one-shot recovery context on new PTTON or Standby.
Package hashes and the semantic findings are private in
`.tmp/vendor-protocol-evidence.json`; proprietary client binaries/code are not
included in this repository or the portable preview.

The common decoder now independently implements that rule only after confirmed
successful automatic tuning and SAVE USER, in Operate, with an actual fresh
positive-to-zero IP reading. It records `rf_idle_source` as
`post-tune-current-transition`; it does not fabricate a received PTTOFF token.
Explicit PTTOFF handling remains available. Ordinary zero current, missing save,
aborted/stopped/unknown tuning, a mode change, a new transmission and duplicate
save messages cannot authorize this recovery. Timers, temperature and operator
assertions still cannot clear RF state. New RF reactivates the command guard.

Offline replay of the actual failed raw capture confirms the fix: the old decoder
finishes with its transmit latch set, while the corrected decoder confirms RF-off
on the IP0 received at trace time 93.812 seconds, after SAVE USER and IP1401.
The amplifier is still in Operate at that point, and a guarded Standby request is
accepted in an offline Monitor with no socket/thread started. The actual amp
remains untouched in Standby. Eight new regression tests cover this compatibility
path and its restrictions. Private replay evidence is
`.tmp/post-tune-rf-off-replay.json`. Live RF acceptance of the corrected build
still requires separate operator approval.

The corrected packaged app passed a 15-second read-only Standby check with
maximum telemetry age 1.0 second and no operating commands. Ordinary Standby
IP0 replies did not arm saved-tune recovery. The final build reran all 142 Python
tests (136 passed, six expected skips) and all five JavaScript suites; the final
rebuilt app was restored in traced read-only mode with fresh Standby telemetry.

### Authorized Ethernet auto-tune retest after RF-off correction

One operator-driven auto-tune passed with raw tracing enabled. The app confirmed
Operate, tuning, SAVE USER, RF-off and return to Standby. The wire trace contains
exactly O, L, &, O for operating/tuning commands, with no power commands or
retries. The session released cleanly; its largest receive gap was 2.422 seconds.
The operator controlled all RF and drive power.

This run received one explicit PTTOFF, so the live RF-off source was
`ptt-off-message`. It did not exercise `post-tune-current-transition` live.
The earlier failed-capture replay remains the compatibility-path evidence.
As an additional offline check, removing PTTOFF from this new capture correctly
does not recover: a second PTTON after SAVE USER clears the one-shot recovery
context. This restriction prevents an old saved tune from clearing a new
transmission. It is not a failure of this actual hardware run.

The operating test session was closed and the packaged app restored in traced
read-only mode. It reports Standby, transmitting false and an empty command
history. Private capture and assessment files remain outside Git.

This is an unsigned local development preview. Hardware acceptance, clean-machine
installation, mixed-DPI/multiple-monitor testing, redistribution-notice review,
signing and public distribution remain separate release work. Further operating
commands, power-sequence tests and real auto-tune acceptance require separate
explicit operator approval.

## Mac review of PR #2 and compact simulation follow-up

The Mac operator's agent reports exact commit 4b2a4c17deed90083e2044c19bf11e58bfd92154
built successfully as a separate Apple Silicon test app. All 142 Python tests
completed (138 passed, four expected private-capture/Windows-only skips) and all
five JavaScript suites passed. Frozen simulation passed tuning/save, RF-active
command blocking, RF release and return to Standby. The agent reports no hardware
connection and unchanged production app/settings. These are operator-supplied
Mac results, not a Mac run performed on this Windows PC.

The agent found compact view hid the simulation warning and RF controls while
leaving a LIVE badge. The shared compact CSS now exempts simulation and restricted
mode notices from panel collapsing, retaining their ordinary hidden behavior.
The connection badge explicitly says SIMULATION for simulated data in every
connection state. Presentation and UI regressions pass on Windows. A local
headless Edge attempt returned no DOM output, so rendered compact/full-view
confirmation remains for the Mac agent's follow-up. No hardware was used for
this UI change.

## Files and commands

Run the desktop app from `dist/windows/OM Power Control/OM Power Control.exe`.
Ordinary launches are always simulated. Keep its `_internal` folder alongside it.
Portable archive: `dist/OM-Power-Control-0.1.31-windows-x64-preview.zip`.

Development commands are in WINDOWS.md. Build scripts handle the read-only
attributes OneDrive assigns to generated directories; cleanup is confined to
the two named generated build/output directories under this repository.

The initial Windows port and shared reconnect changes were merged in PR #1.
The operator-driven tune-test policy and these additional results remain local
pending review. The existing Mac release has not been updated. Local binaries,
station settings and private diagnostic traces are excluded from Git.
