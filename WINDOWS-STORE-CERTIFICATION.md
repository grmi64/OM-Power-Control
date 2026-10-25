# Store-identity certification-kit check — 2026-10-24

Status: package-file workflow completed with overall **PASS**, including DPI.
The original installed-identity workflow produced WARNING, retained below as
diagnostic history. One optional blocked-executables finding remains visible
and has been reviewed as informational for this candidate; see
WINDOWS-STORE-RUNTIME-REVIEW.md for the release disposition and support limits.
No amplifier connection, Store upload, submission or publication occurred.

## Environment and artifact

- Exact installed identity:
  `GregoryMiller.OMPowerControl_1.0.31.0_x64__ry0zqgvak7bfy`.
- Application: signed 0.1.31 Windows bundle from main a914b5e.
- Unsigned Store candidate SHA-256:
  `ff4c5c04c7db144df73d2bc1cc58985919f46f28db8e0c99714d06b0c6bb346e`.
- WACK version: 10.0.26100.9457, x64, Desktop Bridge/Centennial workflow.
- Existing Windows 11 Sandbox with Networking disabled and zero network adapters.
  The app defaults to offline simulation, as separately verified by a no-argument
  packaged launch. No hardware flags were used.
- The user explicitly approved online download/staging of the SDK installer.
  Microsoft-signed installer SHA-256:
  `b0bdbad38ae74c40ccae8cdbcf229807627fba2bc3100be28301c4ba884f755e`.
  SDK feature `OptionId.WindowsSoftwareLogoToolkit`, including its dependencies,
  was installed inside the offline Sandbox; nothing was installed on the host.
  All eight setup packages succeeded. An initial three-minute monitoring timeout
  was followed by continued observation of the same installer, which completed
  with exit code zero; installation was not restarted.
- A matching two-day test certificate was trusted only inside the Sandbox.
  The private test-signed copy used for WACK had SHA-256
  `95f488d82d5cd461bff6cf68020bc4a8a76fa3d3a6b25607236a9007ca9dbcd6`.
  This is local test signing, not Microsoft Store signing.

## Initial installed-identity execution and results

Ran `appcert.exe reset`, followed by
`appcert.exe test -packagefullname GregoryMiller.OMPowerControl_1.0.31.0_x64__ry0zqgvak7bfy -reportoutputpath C:\OMStoreTest\wack-report.xml`
in the active Sandbox user session. No tests were manually deselected.
Both commands exited zero, but the report's result is authoritative:

| Result | Count |
|---|---:|
| PASS | 22 |
| FAIL, optional | 1 |
| WARNING, nonoptional | 1 |

The XML records `OVERALL_RESULT="WARNING"` and `PARTIAL_RUN="FALSE"`.
The run took about two minutes. Passed checks include manifest, resources,
branding, signatures, UAC, debug configuration, restricted/enterprise capability
checks, metadata, archive usage and banned-file analysis. A successful task
execution or appcert process exit does not override an individual test result.

### Optional blocked-executables failure

WACK flags CreateProcessW/ShellExecuteW imports in the Python runtime and
PyInstaller launcher, plus command-like strings in the EXE and bundled
Python/OpenSSL/UCRT/Python.Runtime libraries. The strings include cmd, cmd.exe,
CSI, BASH and reg. This static finding does not establish that those commands
were executed. It is distinct from the banned-file-analyzer test, which passed.

Microsoft describes optional Desktop Bridge checks as informational for Store
onboarding and the blocked-executables check as relevant to Windows S restrictions.
The subsequent review found runtime capabilities and non-command string contexts;
one observed offline packaged run launched only expected WebView2 descendants.
This finding does not block this candidate's local Store preflight, but does not
establish S mode compatibility or guarantee Store approval. See
WINDOWS-STORE-RUNTIME-REVIEW.md. No binary was patched or stripped merely to
suppress the scanner.

### Nonoptional DPI warning

WACK reports that it failed to process `App\OM Power Control.exe`, then labels
the package not DPI aware. Independent PE-resource extraction from the unchanged
signed EXE confirms the embedded manifest contains both `dpiAware=true/pm` and
`dpiAwareness=PerMonitorV2` with their Microsoft XML namespaces.

The real installed Store-identity app was launched again after WACK using
`--simulate --smoke-test`. It passed WebView2/UI and DPI checks, reported
PerMonitorV2 and HWND DPI 120, and exited zero. Its native process package
identity matched the exact reserved Store identity. This evidence conflicts
with the scanner's initial conclusion. The subsequent investigation below
resolved the warning by changing the validation workflow, without changing the
EXE or manifest.

## DPI investigation and resolution

Microsoft's staged manifest tool successfully extracted the signed EXE's
embedded manifest. The installed WACK DPI checker's managed call sequence
showed that it calls BinaryInfoClass.LoadBinary followed by
IsPerMonitorV2DPIAwarenessSet. Direct calls to that same installed parser returned
true for ordinary-folder copies of the unchanged EXE, including a filename
containing spaces. On the installed WindowsApps path, LoadBinary succeeded but
the DPI query returned COM E_FAIL, reproducing the report's analysis error.
This isolates an installed-path analysis problem; it does not establish which
internal WindowsApps/parser interaction causes E_FAIL. Exploratory extended-path
and expanded path probes stalled and were terminated; they are not counted as
passes or used as acceptance evidence.

Retested the unchanged private test-signed MSIX using Microsoft's documented
package-file workflow, `appcert.exe test -appxpackagepath <MSIX file>`, after
resetting WACK. The complete report records overall PASS, PARTIAL_RUN FALSE,
23 passing tests and the same one optional blocked-executables failure.
DPIAwarenessValidation now passes with no messages. No app code, embedded
manifest, package identity or package bytes were changed to obtain this result.
No tests were manually deselected or analyzer configuration modified.

Use the package file, rather than the installed package identity, for release
acceptance checks. `scripts/run-windows-msix-wack.ps1` requires a network-disabled
test environment, verifies Microsoft's WACK executable signature, copies the
input MSIX to local temporary storage with matching SHA-256, and records a
unique run's XML/logs/hash. Run it inside the offline Sandbox with the private
test-signed copy; it does not create/trust certificates or submit anything:

```powershell
.\run-windows-msix-wack.ps1 -PackagePath C:\OMStoreTest\store-candidate-test.msix -ReportDirectory C:\OMTestResults\wack-dpi-fixed
```

After copying reports back, run the host-side acceptance check:

```powershell
.\.venv\Scripts\python.exe scripts/check-wack-report.py <report.xml>
```

The validator requires overall PASS, a complete run and an explicit passing
nonoptional DPI test, rejects unsuccessful required checks, and retains optional
findings in its summary. Eight offline regression cases pass. It rejects the
original installed-identity WARNING report and accepts the package-file report.
Do not infer acceptance from appcert exit code zero alone.

Private evidence for the first successful run is
`.tmp/clean-pc-test/results/wack-packagepath-report.xml` and its console/run logs;
native parser probes are `dpi-probe.json`, `dpi-spaces-probe.json` and
`dpi-installed-probe.json`. The original report is retained separately.

The new runner was then exercised in a second full offline run
with the same input SHA-256. It again returned overall PASS, 23 PASS tests,
the single optional blocked-executables FAIL and no DPI warning; the acceptance
validator passed. Its evidence is under
`.tmp/clean-pc-test/results/wack-dpi-fixed/098ddc152f694651a8e3ae014c9cad59/`
(`report.xml`, `run.json`, `console.log`, `reset.log`). The run record confirms
zero network adapters and the unchanged test-package hash.

## Cleanup, evidence and remaining scope

The test package was uninstalled and the temporary certificate removed from
both Sandbox certificate stores. Zero network adapters were confirmed again.
The original portable EXE, ZIP and unsigned Store candidate hashes are unchanged.
No application/source behavior was changed for these checks.

Private raw evidence, including detailed local paths, is retained in
`.tmp/clean-pc-test/results/wack-report.xml`, `wack-console.log`,
`wack-run.json`, `wack-install-complete.json`, `wack-cleanup.json` and
`store-msix-smoke.json`/`.log`. Parsed test results and installer provenance are
in `.tmp/store-certification/wack-summary.json` and `provenance.json`.
These local evidence files are not release payloads or Store uploads.

Next: complete remaining Store listing/privacy/support and
release review work. Physical multi-monitor testing, exact-identity upgrade
testing and actual Store-managed delivery remain separate. WACK's local result
does not guarantee Store approval or settle the portable ZIP's SmartScreen result.

References: [WACK command-line workflow](https://learn.microsoft.com/en-us/windows/uwp/debug-test-perf/windows-app-certification-kit),
[Desktop Bridge required and optional tests](https://learn.microsoft.com/en-us/windows/uwp/debug-test-perf/windows-desktop-bridge-app-tests),
[official SDK downloads](https://learn.microsoft.com/en-us/windows/apps/windows-sdk/downloads).
