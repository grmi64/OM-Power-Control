# Store listing — final local copy

Prepared 2026-10-25 for publisher review and entry into Partner Center. Nothing
has been uploaded, submitted or published. Pricing/markets below were selected
by the publisher; publication timing and the portal questionnaires remain pending.

## Product metadata

| Item | Final local value |
|---|---|
| Reserved product name | OM Power Control |
| Publisher display name | Gregory Miller |
| Language | English (United States) |
| Category | Utilities & tools (use the matching portal category) |
| Package | Windows 11 x64; package 1.0.31.0, application 0.1.31 |
| Pricing | Free; no in-app purchases or advertisements |
| Markets | All available Store markets, as selected by the publisher |
| Publication timing | Hold until the publisher approves submission/publication |
| Website | https://github.com/grmi64/OM-Power-Control |
| Support | https://github.com/grmi64/OM-Power-Control/issues — operator-selected channel |
| Privacy URL | https://github.com/grmi64/OM-Power-Control/blob/main/PRIVACY.md — verify finalized contents after merge |
| License | MIT project source; bundled components retain their own licenses/notices |

The repository is public. See links.json for anonymous link checks and the
publication gate: the current public privacy file is the earlier draft. Merge
the finalized policy and verify its public contents before Store submission.

## Short description

OM-3501A amplifier monitoring and operator-controlled tuning, with offline simulation.

## Description

OM Power Control is an independent, open-source desktop app for the OM Power
OM-3501A amateur-radio amplifier. View forward and reflected power, calculated
SWR, frequency, temperature and additional amplifier readings in a full dashboard
or compact window. Choose the secondary meter and keep the display on top.

The app supports amplifier Operate/Standby, normal cooling and warm-up sequences,
and automatic tuning with amplifier-confirmed results. You supply and stop tuning
RF and set the radio's drive power. The app never keys the radio or adjusts its
drive power. Use the amplifier within the manufacturer's requirements and your
station's limits.

The app opens in clearly labeled offline simulation, so you can explore
the interface and simulated tuning without connecting equipment. Real amplifier
access requires an explicit choice in Connection mode and a configured amplifier
address. Disconnect, choose read-only telemetry or amplifier controls, confirm
Apply mode and reopen, then click Connect separately when authorized. A normal
Start-menu launch remains simulation.

Optional integration with DX Caliber can share readings and selected controls
locally on the same PC. It is off by default; DX Caliber is not required for
standalone use.

Requires Windows 11 x64 and the Microsoft Edge WebView2 Evergreen Runtime.
Python is bundled. Real equipment validation covers the OM-3501A; other model
labels provide monitoring only and do not establish compatibility. This is an
independent project, not an official OM Power product or manufacturer endorsement.

## Feature bullets

- Forward/reflected power, calculated SWR, frequency and temperature.
- Additional measurements and a selectable secondary meter.
- Full and compact displays with saved stay-on-top preference.
- Clearly labeled offline simulation, including successful and interrupted tunes.
- Operator-controlled amplifier modes and automatic tuning in hardware mode.
- Optional local DX Caliber integration; disabled by default.

## Suggested search phrases

OM Power Control; OM-3501A; amateur radio; ham radio; amplifier monitoring;
Ethernet amplifier; automatic tuning. Adapt to the portal's actual keyword fields.

## Release notes

First Windows release of OM Power Control, using the shared Python backend and
HTML/JavaScript interface with a native WebView2 desktop host. Includes offline
simulation, compact/stay-on-top preferences, automatic-tuning state handling,
reconnect improvements, RF-state guards and native DPI support. OM-3501A hardware
testing and offline Store-package checks are documented in the project.

## Screenshots and remaining portal entries

Use the reviewed PNGs and captions in screenshots/. Every capture comes from
the signed Windows candidate in offline simulation with blank station settings.
Do not describe synthetic readings as live RF. No hardware is connected.

Complete the portal content/age questionnaire accurately; this document assigns
no rating. Select Free and all available markets. Do not enable automatic
publication until the publisher approves it. Promotional art and trailers are
optional and are not included in this delivery.

Physical multiple-monitor/mixed-DPI tests remain deferred. S mode, Windows 10,
ARM64 and other amplifier models are not claimed as validated configurations.
The exact release candidate is main 510d985, Store package 1.0.31.0; required
WACK tests passed and the optional bundled-runtime finding remains disclosed in
reviewer-notes.md. The final Windows RF-output and auto-tune tests passed.
