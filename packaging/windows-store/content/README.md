# Local Store content preparation — 2026-10-24

All files here are drafts for operator review. No portal fields, remote files,
Store submission, public privacy policy or publication settings were changed.
This preparation used source/local test evidence only, with no amplifier access
or Internet requests.

| Deliverable | Local file | Status |
|---|---|---|
| Restricted capability explanation | [run-full-trust.md](run-full-trust.md) | Prepared; matches packagedClassicApp/mediumIL/runFullTrust architecture |
| Listing text and metadata | [listing.md](listing.md) | Prepared; open choices and hardware-launch dependency labeled |
| Offline certification instructions | [reviewer-notes.md](reviewer-notes.md) | Prepared; normal launch is simulation, no equipment/credentials required |
| Public support text | [support.md](support.md) | Prepared; GitHub Issues explicitly chosen by operator |
| Privacy policy | [PRIVACY.md](../../../PRIVACY.md) | Prepared as a local draft, not an effective published policy |

## Decisions and work still needed

1. Approve the draft wording and privacy effective date. The proposed future URL
   is https://github.com/grmi64/OM-Power-Control/blob/main/PRIVACY.md.
   That file is local only; do not enter the URL as a live policy until separate
   publication is authorized and its unauthenticated availability is checked.
2. Review the Connection mode workflow in WINDOWS-STORE-LAUNCH.md. Isolated
   Store-identity simulation tests passed; rebuild/sign and validate a new release
   candidate containing it. Normal launches remain simulation and every mode
   handoff starts disconnected. No amplifier connection was tested.
3. Choose pricing, markets and availability. Complete the portal's content/age
   questionnaire; this offline draft assigns no rating or price.
4. Capture and review real simulation screenshots and any required listing art;
   confirm the portal's current fields, character limits and asset dimensions.
5. Recheck the selected repository/support URLs online when authorized. No account
   email, home address or Azure account identifiers were used as public contacts.
6. Complete final release review. Physical monitor tests remain deferred and
   actual Store certification/delivery remain untested. S mode is not claimed.

## Source review behind the drafts

windows_app.py and windows_runtime.py establish simulation defaults, explicit
hardware modes, WebView2 hosting/navigation restrictions, runtime requirements
and per-user diagnostics. settings.py establishes station fields and local files.
live.py, session_protocol.py and dxc_feed.py establish local HTTP, amplifier TCP,
optional local sharing/control and mode restrictions. wire_trace.py establishes
raw local diagnostics and per-file bounds. live.html uses local assets/fetches
and browser preference storage. README.md documents independent project status,
OM-3501A scope, RF/drive responsibility, existing support URL and licensing.

The local WACK/UI/runtime reviews are in WINDOWS-STORE-CERTIFICATION.md and
WINDOWS-STORE-RUNTIME-REVIEW.md. Draft text does not expand those test claims.
These content files are not automatically added to the existing MSIX by this task;
the signed EXE, ZIP and unsigned Store candidate remain unchanged.
