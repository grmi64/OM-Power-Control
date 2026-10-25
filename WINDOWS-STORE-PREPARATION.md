# Store-identity MSIX preparation — 2026-10-24

Status: locally built review candidate; exact Store identity passed offline
Sandbox deployment tests using a temporary test signature. Windows App
Certification Kit (WACK) package-file workflow completed with PASS, including
DPI, with one optional bundled-runtime finding retained; see
WINDOWS-STORE-CERTIFICATION.md. Not submitted or published.

## Reserved identity

The operator supplied the Partner Center values in an RTF attachment. Only the
four public package-identity values were extracted. The attachment and any
unrelated credentials were not copied into the project or package.

| Field | Exact value |
|---|---|
| Name | GregoryMiller.OMPowerControl |
| Publisher | CN=01B6B2D5-A706-4EC7-9AC8-54F1A68995B4 |
| Publisher display name | Gregory Miller |
| Package family name | GregoryMiller.OMPowerControl_ry0zqgvak7bfy |

`packaging/windows-store/identity.json` records these values, the reserved
display name OM Power Control, x64, and package version 1.0.31.0. The application
code/version remains the signed 0.1.31 app from a914b5e. The Store version uses
a positive first field and a zero final field. The first candidate's minimum
OS is Windows 11 (10.0.22000.0); only build 26300 has been validated so far.

## Build and verification

`scripts/build-windows-msix.ps1` stages a copy of the already signed portable app,
checks notices and binary fingerprints, generates logos from the existing app
icon, substitutes the reserved identity into the manifest, and invokes MakeAppx
semantic validation. It produces an MSIX, checksum and local build record.
It never launches hardware mode, signs with a mismatched identity, installs a
package, or submits/publishes it. Production package data uses the Store PFN.

The successful local build used SDK BuildTools 10.0.28000.2705 from the prior
feasibility test. The command was:

```powershell
.\scripts\build-windows-msix.ps1 -SdkBin '.tmp\msix-feasibility\tools'
```

Output: `dist/msix/OM-Power-Control-Store-1.0.31.0-x64-unsigned.msix`.
SHA-256: `ff4c5c04c7db144df73d2bc1cc58985919f46f28db8e0c99714d06b0c6bb346e`.

Independent archive checks passed:

- Exact Store name/publisher/display name, package version and architecture.
- Unchanged inner EXE, matching the signed portable artifact.
- All 55 required notice/source hashes and 78 binary fingerprints.
- All 680 block-map SHA-256 blocks, with correct uncompressed file sizes.
- ASCII filenames and no private telemetry, settings, instance lock or metadata.
- No outer package signature, as intended for this Store preparation.

The builder also rejected invalid Store versions 0.1.31.0 and 1.0.31.1 before
staging. This version guard is distinct from MakeAppx schema validation.

The existing portable EXE/ZIP hashes remain unchanged:
`344b9dd684aea9a92b598d11a220bfb3aeb30d965421de5be467769ad7933ef1` and
`14b7b5108c3a785e4cba29cf3ef06af889b539119d1de73c1a29946a0446fdfb`.
Private build/verification evidence is under `.tmp/msix-feasibility/` and the
build record beside the ignored output package.

## Signing and remaining validation

The outer Store identity's GUID publisher is different from the Azure public
certificate's legal-name subject. The existing certificate must not be used to
misrepresent or replace the assigned Store publisher. Microsoft supports Store
MSIX preparation without a CA-trusted outer signature and applies Store signing
after certification. The inner EXE retains its valid existing Azure signature.

The earlier, separately signed feasibility identity passed offline installed
startup, real WebView2/DPI and simulated tuning, settings, updates and uninstall.
Those earlier passes remain separate from the exact-identity checks below.

## Exact Store-identity offline deployment — 2026-10-24

The unsigned candidate with SHA-256
`ff4c5c04c7db144df73d2bc1cc58985919f46f28db8e0c99714d06b0c6bb346e`
was copied into the existing network-disabled Windows Sandbox. A two-day
self-signed certificate with the exact Store-assigned publisher was created
and trusted in that Sandbox only. The test copy was signed with the staged
Microsoft SDK SignTool, without an online timestamp request. Neither the host
certificate stores nor the unsigned candidate were changed.

Installed package identity was
`GregoryMiller.OMPowerControl_1.0.31.0_x64__ry0zqgvak7bfy`, status Ok and
SignatureKind Developer (local test signing, not Store signing). The activated
process's native package identity matched. The following checks passed:

- Real WebView2 UI smoke and DPI checks, with process exit code zero.
- Simulated auto-tune, save, RF release and return to simulated Standby.
- Saved meter preference restored after closing and reopening; both exits zero.
- Uninstall removed registration and virtualized application data.
- Clean reinstall and launch with no arguments defaulted to simulation,
  Standby, RF off and sharing disabled, with default meter preference restored.
- Reader mutex was visible outside the package; clean exit and second uninstall.
- Zero network adapters throughout; no amplifier connection.

After testing, the temporary certificate was removed from both Sandbox stores.
Private evidence is in `.tmp/clean-pc-test/results/store-msix-*.json` and the
matching smoke log. The signed test copy remains private inside the disposable
Sandbox; it is not a distribution artifact. Original EXE, ZIP and unsigned
candidate hashes were rechecked and remain unchanged.

After explicit permission for downloading and staging the kit, WACK was installed
only in the offline Sandbox. The initial installed-identity report warned about
DPI analysis. Investigation reproduced a parser error for the WindowsApps path;
the identical EXE was recognized as PerMonitorV2 in ordinary-folder copies.
The unchanged MSIX passed the complete package-file WACK workflow: 23 tests
passed, including DPI, and one optional blocked-executables test failed.
See WINDOWS-STORE-CERTIFICATION.md for evidence and remaining optional findings.
These deployment checks do not establish Store certification, Store-managed
delivery, SmartScreen acceptance, exact-identity upgrade behavior or physical
multi-monitor behavior.

The optional WACK finding has been reviewed: it is informational for this
candidate's local Store preflight, with no S mode compatibility claim. See
WINDOWS-STORE-RUNTIME-REVIEW.md for per-binary evidence and process-trace limits.
Local runFullTrust, listing, reviewer and support drafts are prepared under
packaging/windows-store/content/, with the privacy policy draft at PRIVACY.md.
The operator selected GitHub Issues as the public support channel. These drafts
are not submitted or published; see content/README.md for remaining decisions,
public-URL/asset work and the Store-user hardware launch workflow review.
The Connection mode workflow is implemented and tested in source and an isolated
Store-identity simulation build; see WINDOWS-STORE-LAUNCH.md. Older signed
artifacts remain unchanged. Next work includes source review, a new signed
candidate's WACK/artifact acceptance, final content/URL/assets and approval.
The physical monitor and live-hardware limitations remain unchanged. No new
hardware test, radio operation, Store upload, submission or publication occurred.
New configuration, script and documentation remain local and uncommitted.

Reference: [Microsoft MSIX requirements, identity and signing guidance](https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/msix/app-package-requirements).
