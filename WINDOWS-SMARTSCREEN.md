# SmartScreen investigation — 2026-10-24

Status: investigation only. No publication, file submission, security bypass,
certificate change, rebuild or amplifier connection was performed.

## Evidence for this candidate

- Main commit: a914b5ea030725da825c96629afa405252c4dd81.
- Signed EXE SHA-256:
  344b9dd684aea9a92b598d11a220bfb3aeb30d965421de5be467769ad7933ef1.
- ZIP SHA-256:
  14b7b5108c3a785e4cba29cf3ef06af889b539119d1de73c1a29946a0446fdfb.
- SignTool verification and fresh-guest Authenticode checks passed: publisher
  Gregory Miller, SHA-256 signing, valid Microsoft RFC 3161 timestamp.
- Explorer preserved Internet-zone marking on extraction. The fresh guest
  reached Microsoft's public HTTPS website before launch. SmartScreen displayed
  an unrecognized-app warning, rather than the offline service-unreachable error.
- No application process started. The operator selected Don't run. The test used
  synthetic Internet marking, not a published download URL; the latter is untested.
- The EXE has no version-information resource. This is a release-metadata
  observation, not evidence of the warning's cause or a demonstrated remedy.

## Assessment

The observations are consistent with insufficient reputation for a new signed
build/publisher, rather than an invalid signature. This is an inference; Microsoft
does not expose the exact reputation score or threshold. Its current guidance
says valid signed apps can warn, reputation develops through distribution, and
EV certificates no longer provide an automatic bypass. There is no documented
consumer reputation fast-track. Merely waiting before any distribution cannot
be promised to clear the warning.

Source: [Microsoft SmartScreen reputation guidance](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation).

## Available paths

| Path | What it can achieve | Constraint |
|---|---|---|
| Keep signed GitHub ZIP distribution | Retains current portable packaging and consistent publisher identity | Initial warnings can persist; no guaranteed clearance date or install count |
| Prepare Microsoft Store MSIX distribution | Store re-signs MSIX after certification, avoiding Store-install SmartScreen download warnings | Requires new packaging validation and Store approval; applies to Store delivery, not the existing GitHub ZIP |
| Detection review / technical support | Can investigate an incorrect detection or signing-service issue | Not a guaranteed consumer-reputation allowlist; do not describe this unrecognized-app result as a confirmed malware false positive |

Sources: [Microsoft signing/distribution comparison](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options),
[Security Intelligence submission purpose](https://www.microsoft.com/en-us/wdsi/filesubmission),
and [Artifact Signing support options](https://learn.microsoft.com/en-us/azure/artifact-signing/faq).
The submission portal lists SmartScreen as a product, but that does not establish
a promised fast-track for an ordinary new-app reputation warning.

## Recommended next decision

Keep the existing Artifact Signing identity and freeze this candidate's bytes
while deciding distribution. Rebuilding/re-signing would create a different
file hash without establishing a fix. Neither removing Internet marks nor
disabling Windows protection resolves the public distribution problem.

If avoiding this warning on first install is a release requirement, investigate
Store/MSIX packaging next. If portable GitHub distribution is the priority,
record the initial reputation warning as a known limitation and require explicit
approval of that limitation before release. Continue to distinguish a recognized
publisher from a warning-free launch; no warning-free pass has been obtained.

Any future app validation must remain in simulation unless the operator separately
authorizes amplifier access. Any Microsoft file upload, support message or Store
submission requires separate authorization; none was sent during this review.
