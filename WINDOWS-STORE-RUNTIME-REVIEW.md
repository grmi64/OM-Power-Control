# Optional WACK runtime finding — 2026-10-24

Disposition: **informational; not a blocker for this candidate's local Store
preflight**. Retain the finding and its rationale. This is not Store approval
and does not establish Windows S mode compatibility.

The complete package-file WACK reports returned overall PASS, with all required
checks passing. The sole remaining result is `Blocked executables`, marked
`OPTIONAL="TRUE"` and `FAIL`: 12 messages across eight bundled binaries.
Microsoft's Desktop Bridge guidance, reviewed earlier in this session, says
optional tests are informational for Store onboarding and describes this check
in relation to Windows S restrictions. No online fetch was made for this review.

## Scope and exact candidate

- Application 0.1.31, Windows bundle built from main a914b5e.
- Store package identity:
  `GregoryMiller.OMPowerControl_1.0.31.0_x64__ry0zqgvak7bfy`.
- Unsigned production candidate SHA-256:
  `ff4c5c04c7db144df73d2bc1cc58985919f46f28db8e0c99714d06b0c6bb346e`.
- Private, locally test-signed copy used for WACK and the process trace:
  `95f488d82d5cd461bff6cf68020bc4a8a76fa3d3a6b25607236a9007ca9dbcd6`.
- Pinned stack includes CPython 3.12.14, PyInstaller 6.22.3, pywebview 6.2.1,
  pythonnet 3.2.1 and clr_loader 0.3.1; native dependency fingerprints are recorded
  in ThirdPartyNotices/windows/inventory.json.

The static review inspected the actual flagged binaries' strings/PE sections,
the Windows application source, and the installed pinned Python dependency
source. It did not patch binaries, remove runtime functionality, change analyzer
rules or suppress the optional result.

## Findings and interpretation

| Binary | WACK references | Evidence and interpretation |
|---|---|---|
| OM Power Control.exe | CreateProcessW; CMd | The PyInstaller launcher genuinely imports the process API. Its case-insensitive cmd matches occur in the appended archive/overlay, with binary contexts rather than an identified shell command. The build uses onedir. No extra app/helper process was observed during the traced smoke run. |
| python312.dll | CreateProcessW; ShellExecuteW; cmd | CPython retains general process/file-launch capabilities. String contexts include show_cmd, command-line help, module names and shell-extension data. These capabilities are real; this is not a claim that the runtime cannot launch commands. No application call sites using them were found. |
| libcrypto-3-x64.dll | cmd | Local contexts include ENGINE_ctrl_cmd and ENGINE_cmd_is_executable: OpenSSL control-operation names, not evidence of cmd.exe execution. |
| libssl-3-x64.dll | cmd | Local contexts include SSL_CONF_cmd and configuration diagnostics such as cmd=%s. |
| ucrtbase.dll | cmd.exe | The C runtime contains actual shell-support strings, including COMSPEC and /c. The application source review found no system/popen calls and the traced run did not launch a shell. Retain this runtime capability in the assessment. |
| unicodedata.pyd | CSI; BASH | Matches occur in generated Unicode-name data, alongside tokens such as BASHKI, BASSA and CUATRILLO; they do not identify shell invocation code. |
| _socket.pyd | cmd | Matches are in ioctl(cmd, option) documentation and its supported-command descriptions. |
| Python.Runtime.dll | reg | Matches appear in managed metadata/identifiers such as reg, RegisterDecoder, RegisterEncoder and GetAggregateException. No reg.exe invocation was identified. |

The only EXE shipped in the portable payload is OM Power Control.exe. No cmd,
PowerShell, bash, reg or other command-interpreter EXE is bundled. API imports and
substring matches alone do not prove a program executes the named command, and
not all findings should be called false positives: some identify genuine general
runtime capabilities that this app does not use in the reviewed paths.

## Application and dependency paths

The Windows entry point, shared Python backend and UI were searched for direct
subprocess/system/popen/startfile/ShellExecute/CreateProcess/webbrowser calls.
No application shell/helper launch calls were found. macOS signing scripts and
test harness subprocess calls are development tools, not Windows app entry paths.

The wrapper sets OPEN_EXTERNAL_LINKS_IN_BROWSER=False and ALLOW_DOWNLOADS=False.
The pinned Edge backend contains a webbrowser.open branch, guarded by that
disabled external-link setting. WebView2's own browser subprocesses are expected
runtime behavior, and its installed runtime remains a prerequisite.

Pythonnet defaults to .NET Framework on Windows. Dependency source also contains
alternate runtime-discovery paths that can invoke dotnet --list-runtimes;
pywebview has a CoreCLR fallback if loading clr fails. These are distinct from
the flagged shell strings, were not observed in this test, and are not covered
by a promise that every environment override or fallback avoids helper launches.

## Offline process observation

One additional exact-identity packaged run was observed with
Win32_ProcessStartTrace in the network-disabled Sandbox. The subscription was
active before package activation and captured the app's root process event.
The app ran --simulate --smoke-test, passed real UI/DPI smoke and exited zero.
The observed process tree contained the app and six descendants named
msedgewebview2.exe, with no unexpected descendants. No cmd.exe, powershell.exe,
bash, csi, reg.exe or dotnet.exe descendant was observed during this run.

This is bounded startup/simulation-smoke evidence, not exhaustive tracing of
every feature, error path, environment override or hardware operation. Existing
simulated tuning/save/RF-release/reopen tests add functional evidence but are not
all covered by this new process trace. No amplifier connection or RF occurred.

Afterward, the test package was uninstalled, the temporary Sandbox certificate
was removed, and zero network adapters were confirmed again. No host trust
settings or release artifacts were changed.

All eight inspected binaries were compared byte-for-byte by SHA-256 with their
entries in the production MSIX. The seven DLL/PYD files also matched the pinned
dependency inventory. Portable EXE, ZIP and unsigned MSIX hashes remain unchanged.

Private evidence: `.tmp/runtime-review/string-contexts.json`,
`.tmp/runtime-review/optional-finding.json`,
`.tmp/runtime-review/artifact-verification.json`, and
`.tmp/clean-pc-test/results/runtime-process-review.json`. Full WACK evidence is
listed in WINDOWS-STORE-CERTIFICATION.md. These files are not release payloads.

## Effect on release decisions

Proceed with the remaining Store preparation without rebuilding or stripping
the runtimes merely to remove this optional scan finding. Keep its FAIL visible
in WACK summaries and provide the context if certification reviewers ask.
Continue to require passing mandatory checks; the existing report validator
retains optional findings rather than silently discarding them.

Support scope remains the tested normal Windows 11 x64 configuration. Do not
advertise S mode or other restricted execution-policy compatibility from this
result. Restricted-capability justification, listing/privacy/support information,
final operator approval and actual Microsoft certification remain separate.
New dependency versions, packaging modes or launch behavior require renewed
review. No Store submission or publication was performed.

Reference: [Microsoft Desktop Bridge required/optional tests and blocked-executables guidance](https://learn.microsoft.com/en-us/windows/uwp/debug-test-perf/windows-desktop-bridge-app-tests).

## Follow-on connection-mode change

The later source/review build deliberately reopens only its own packaged
executable for an explicit mode change, using validated argv, shell=False and
disconnected startup. Offline tests verified parent/child Store identities and
clean simulation handoff. This is an app-owned executable, not a shell or
downloaded helper. See WINDOWS-STORE-LAUNCH.md. The earlier no-application-launch
finding describes the old candidate, not this implementation. Rebuild/sign and
repeat WACK for the new candidate; the earlier artifact results remain historical.
