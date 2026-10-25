# Store submission content — final local preparation, 2026-10-25

The listing, support text, restricted-capability explanation and privacy policy
are ready for publisher review. No Partner Center fields, submission or remote
publication settings were changed. App screenshot work uses offline simulation
only; no amplifier connection or RF is involved.

## Submission files

- listing.md: listing text, feature bullets, release notes and publisher choices.
- listing.en-US.json: copy-ready field values and selected pricing/markets.
- screenshots/: authentic candidate captures, captions and integrity manifest.
- reviewer-notes.md: certification instructions requiring no equipment or account.
- run-full-trust.md: restricted-capability justification for the desktop host.
- support.md: public GitHub Issues channel and reporting instructions.
- ../../../PRIVACY.md: finalized local policy; the public main URL still contains
  the earlier draft until a separately authorized commit/review/merge.
- links.json: anonymous HTTP status checks of the selected public URLs.

## Publisher decisions

Free in all available Store markets; English (United States); Windows 11 x64;
Utilities & tools. Support: https://github.com/grmi64/OM-Power-Control/issues.
Website: https://github.com/grmi64/OM-Power-Control.
Privacy: https://github.com/grmi64/OM-Power-Control/blob/main/PRIVACY.md.
No personal account email, address or Azure identity is used as a public contact.

## Candidate evidence

Main 510d985; app 0.1.31; Store package 1.0.31.0. Signed portable EXE/ZIP and
Store-identity MSIX passed offline regression, Sandbox UI/DPI/simulated tuning,
self-relaunch, preferences, reinstall/uninstall and complete package-file WACK.
All required WACK tests passed; the optional bundled-runtime finding is unchanged.
Final Windows RF-output and auto-tune acceptance passed separately with operator
RF/drive control, explicit PTTOFF, return to Standby and clean session release.
The missing-PTTOFF fallback retains offline replay verification only.

The exact artifact hashes and acceptance record are local at
`dist/msix/main-510d985/validation.json`. Content edits do not rebuild, re-sign or
change those binaries. Physical multiple-monitor tests remain deferred; S mode,
Windows 10, ARM64 and other amplifier models are not claimed as validated.

## Final publication gates

1. Review and authorize committing/pushing/merging these content files. Recheck
   the public privacy URL afterward: HTTP 200 alone is insufficient while it
   still displays the earlier draft. The finalized policy must be public before
   Store submission.
2. Complete the Partner Center content/age questionnaire accurately. No age
   rating is assigned here. Confirm the matching category and all-market/free
   settings in the actual portal. Do not choose automatic publication without
   publisher approval.
3. Upload only the exact tested MSIX and reviewed screenshots when authorized.
   Upload, submission and publication have not been authorized by this task.

Microsoft screenshot guidance checked 2026-10-25:
https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/msix/screenshots-and-images
Desktop PNGs must be at least 1366 x 768 (portrait also permitted), under 50 MB.
Captions are at most 200 characters. Keep simulation labeling visible and do
not add logos or marketing overlays to the captures.
