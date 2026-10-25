# OM Power Control for Windows — privacy policy

Last updated: October 25, 2026.

This policy describes OM Power Control for Windows 0.1.31 (Store package
1.0.31.0), published by Gregory Miller.

## Information used by the application

OM Power Control uses connection settings you enter, including an amplifier
network address/port, model label, optional callsign and preferences. In an
explicit hardware mode it receives amplifier readings/status and sends the
requests or permitted control commands needed for the selected functions.
Ordinary launches of this candidate use offline simulation instead.

The interface and backend communicate through a local 127.0.0.1 HTTP service on
your computer. The bundled interface uses local HTML/JavaScript assets. It does
not need an OM Power Control account or a developer-operated cloud service.

## Local storage and diagnostics

The app stores settings, separate simulation settings, window preferences,
startup/error logs and WebView2 browser-profile data on your computer. The UI
also uses local browser storage for display preferences. Brief connection and
command histories are held in memory during a session.

For a Store installation, app files are normally under:
`%LOCALAPPDATA%\Packages\GregoryMiller.OMPowerControl_ry0zqgvak7bfy\LocalCache\Local\OM Power Control\`.
Portable builds use `%LOCALAPPDATA%\OM Power Control\`.

Optional raw tracing is off by default. When explicitly enabled, it saves
timestamped amplifier receive/transmit bytes and decoded diagnostic events
locally. Such files may reveal station/device information and control activity.
Each trace file is capped at 10 MiB; that is not a global retention limit for
all files. Startup logs and existing trace files are not automatically uploaded
or removed on a fixed retention schedule. The app does not itself encrypt these
local settings or diagnostics.

## Network communication and optional integration

In hardware mode, the app communicates with the amplifier endpoint you configure
using its TCP protocol. This is distinct from sending data to the developer.
Connection/session behavior follows the selected mode and saved preferences.
Simulation does not open an amplifier connection and ignores hardware auto-connect.

Optional DX Caliber integration is off by default and disabled in simulation and
read-only mode. If enabled in a supported hardware mode, a loopback feed makes
selected amplifier readings, state and display information available to local
software on the same PC. It can also accept selected amplifier control requests
from that software. The feed excludes the configured amplifier address, callsign,
raw packets and connection history. Other software's subsequent use or sharing
of information is governed by that software; this policy does not describe it.

The reviewed app code contains no advertising service, developer analytics
service or automatic diagnostic-upload feature. Settings, readings and logs are
not sent to Gregory Miller by the app. Microsoft Windows, Microsoft Store and
the WebView2 Runtime are separate products that may process information under
Microsoft's policies and your system settings.

## Support information you choose to provide

Support and privacy questions may be raised at:
https://github.com/grmi64/OM-Power-Control/issues

GitHub issues are public and subject to GitHub's policies. Posting an issue or
attaching a file shares that information with the project and other people who
can view it. Include only information you intend to make public. Do not post
unfiltered station settings, addresses, credentials, control tokens, raw captures
or wire traces. For privacy questions, begin with a general description without
private details. This app does not provide a private support-upload channel.

## Your choices and removal

You can leave the callsign blank, keep optional sharing and tracing disabled,
disconnect hardware communication, or use offline simulation. Close the app
before removing its local data; removing settings resets preferences.
Uninstall removed the tested Store package's local application data in our
Sandbox checks. Files you copy/export elsewhere, externally overridden settings
locations, OS backups and public support posts are separate and are not removed
by that uninstall. GitHub controls what you can edit or delete in public reports;
the app cannot erase other people's copies.

## Scope and changes

This policy describes OM Power Control for Windows, not the
manufacturer's hardware, DX Caliber, GitHub or Microsoft's independent services.
This policy will be updated when the application's data handling changes. The
current policy is maintained at https://github.com/grmi64/OM-Power-Control/blob/main/PRIVACY.md.
