# Store listing — local draft

Status: review text only. No fields have been entered or submitted to Partner
Center. Review field names, available categories and limits there before use;
this offline preparation does not assume the current portal schema.

## Product metadata

| Item | Draft value / decision |
|---|---|
| Reserved product name | OM Power Control |
| Publisher display name | Gregory Miller |
| Language | English (United States) |
| Suggested category | Utilities & tools; confirm available choice in portal |
| Package | Windows 11 x64; package 1.0.31.0, application 0.1.31 |
| Pricing, markets, availability | Not selected; operator decision before submission |
| Website | https://github.com/grmi64/OM-Power-Control |
| Support | https://github.com/grmi64/OM-Power-Control/issues — operator-selected channel |
| Proposed privacy URL | https://github.com/grmi64/OM-Power-Control/blob/main/PRIVACY.md — not live from this local draft |
| License | MIT project source; bundled components retain their own licenses/notices |

Public URLs have not been rechecked online during this offline task. The privacy
file must be approved, separately published and checked at its public URL before
that field is used. This draft does not authorize publication.

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

This candidate opens in clearly labeled offline simulation, so you can explore
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

**Pre-release dependency:** the new in-app workflow passed isolated Store-identity
simulation tests (WINDOWS-STORE-LAUNCH.md), but older signed release artifacts
have not been rebuilt with it. Rebuild/sign and validate the exact new candidate
before using these instructions in a public listing. No amplifier connection
was made to test the new workflow.

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

## Release notes draft

First Windows preview of OM Power Control, using the shared Python backend and
HTML/JavaScript interface with a native WebView2 desktop host. Includes offline
simulation, compact/stay-on-top preferences, automatic-tuning state handling,
reconnect improvements, RF-state guards and native DPI support. OM-3501A hardware
testing and offline Store-package checks are documented in the project.

## Required assets and final choices

- Prepare actual screenshots from this candidate: full simulated dashboard,
  compact simulated dashboard, simulated tune readiness and successful save.
  Keep SIMULATION visible; do not imply screenshots are live RF readings.
- Use blank/sample station identity; omit IP addresses, private logs and tokens.
- Existing package icons are available. Store promotional artwork and screenshot
  dimensions/field requirements still need confirmation in the portal.
- Complete the age/content questionnaire accurately; no age rating is assigned
  by this document. Pricing, countries/regions and publication timing are open.
- Physical multiple-monitor/mixed-DPI tests remain deferred. S mode, Windows 10,
  ARM64 and other amplifier models are not claimed as validated configurations.
- No screenshots, ratings, remote listings or publication settings were changed.
