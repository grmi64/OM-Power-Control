# OM Power Control

Windows development preview: see [WINDOWS.md](WINDOWS.md) for setup, the native
WebView2 desktop host, portable packaging and offline simulation. Windows starts
in simulation; real amplifier access requires separate explicit operator approval.

Both desktop hosts use the same Python backend and HTML/JavaScript interface.
`Sources/` and `scripts/build.sh` provide the macOS host/build; `windows_app.py`
and `scripts/build-windows.ps1` provide the Windows host/build. Keep shared
protocol fixes in this repository so both builds receive them. The Mac host
explicitly selects hardware mode and retains its saved auto-connect preference;
direct backend launches default to offline simulation. New Mac builds from this
checkout still require macOS build and reconnect validation.

An independent, open-source macOS controller for the OM Power OM-3501A amplifier over its Ethernet interface. It is not an official OM Power product and is not affiliated with or endorsed by the manufacturer.

The first public build is intended as a beta. Hardware verification so far covers one OM-3501A; compatibility with other models or firmware revisions is not claimed.

## Features

- Forward power, reflected power and calculated SWR.
- Reported antenna name, frequency and temperature in full and compact views, plus a screen-current meter with aligned reference labels.
- Expandable measurements: input power, plate current/voltage, screen current/voltage, grid voltage, heater voltages, mains voltage, temperature and calculated gain. Unavailable or stale telemetry is shown as a dash.
- Saved display selector under Measurements: replace the reflected-power panel with input power, plate current or calculated gain, each with its own units and bar scale. The current choice is disabled in the menu.
- SWR and reflected readings share a blended green/amber/red mismatch color; idle or unavailable readings are neutral.
- Editable amplifier model label. OM-3501A is tested. OM-4001A is supported for monitoring only: it uses the vendor client's meter ranges (5000 W forward, 250 W reflected, 100 W input, ±80 mA screen current) and its scale marks and tube naming follow the vendor client (grid and heater voltages shown separately as f and b), and its operating commands stay blocked until validated on a real amplifier. Other model names use the 3500 W scale, also monitoring only. The model label selects display scale and control gating (see profiles.py); it does not select a different protocol.
- Operate/Standby, normal shutdown/cooling, and power-on/warm-up.
- Automatic tuning with amplifier-confirmed readiness, live measurements, successful completion/automatic saving, Exit and Stop. The operator sets drive power and supplies/stops RF; the app never keys or adjusts the radio.
- Separate results for RF-interrupted/default-settings recovery and settings saved after Stop. Unexpected replies, delayed status and unconfirmed commands never count as successful tuning.
- Successful-tune banner stays visible until Dismiss is clicked; a new successful tune shows it again.
- Amplifier alerts: warnings (WGx) and second-limit alerts (FAx) appear in a banner and expire after 30 s; soft-start errors (FERROR) after 60 s. A hard fault (HF) or high-voltage fault (HVF) replaces the operating state and blocks operating commands (Stop during auto-tune is still allowed). HF clears when the amplifier stops reporting it; HVF stays until you reconnect. Faults are tracked separately from warnings, so a warning that arrives during a fault is shown alongside it and never clears it or lifts the command block. The app never sends a fault reset. While cooling above 40 °C the amplifier's reported temperature (CTx) is shown. These messages follow the manufacturer's protocol document and have not been provoked on hardware.
- Amplifier-confirmed state, transmission guards and no automatic operating-command retries.
- Full and compact views, saved stay-on-top and optional callsign badge. The compact view adds a row of key readings: plate current, plate voltage, screen voltage and grid voltage (grid f and b separately on the OM-4001A).
- Fixed 3500 W bar scale: green low-power region, amber at 1500 W, orange at 2500 W, red at 3500 W, with blended transitions. These are display colors, not calibrated protection limits or recommendations to transmit at a particular power.
- Optional sharing with DX Caliber, off by default: the embedded panel uses this app’s existing amplifier connection. Standalone use does not require DX Caliber. With DXC DEV 0.6.116 or later, its embedded meter follows the measurement selected here. The shared feed includes `om.fault` (kind, title and message, or null) while a hard or high-voltage fault is in force; shared controls are refused during a fault.
- Model check before commands: after connecting, operating commands wait up to 5 s for the amplifier's INFO reply to identify the model. A queued command is cancelled, not sent, if the reported model's controls are unverified (for example an OM-4001A behind an OM-3501A label). Without an INFO reply, the model label applies after the wait.
- Save settings shows immediate saving and success/error feedback.
- Optional auto-connect, off by default. One local reader process; disconnect other remote-control clients before connecting.

## Requirements and setup

The initial binary targets Apple Silicon Macs and macOS 14 or later. Older macOS versions, Intel Macs, Windows, other amplifier models and additional firmware revisions need separate builds/testing. Set the amplifier IP address and TCP port in Connection & station, save, then Connect. No USB connection is used. Configure the amplifier's network interface using its manufacturer instructions. Your callsign, address and preferences stay on your computer; they are not part of the download.

Use the amplifier within its manufacturer operating requirements and your station limits. The software preserves the normal cooling and warm-up sequences. Disconnecting or quitting closes remote communication; it does not turn the amplifier off. The amplifier's own protections remain responsible for hardware protection. The app does not implement antenna switching or fault-reset controls. Auto-tune is verified on the tested OM-3501A; other models remain monitoring only.

## Protocol status

The driver was independently implemented from local hardware traffic. Exact status codes ST1110 and ST1100 were verified against front-panel Operate and Standby. Unknown status codes remain unconfirmed. SWR is calculated from measured forward/reflected power. Two live RF comparisons matched the amplifier display; forward power/SWR were also checked against a separate PowerMaster II. Full-range measurement calibration and extensive fault testing are not claimed. Additional telemetry scaling remains under validation. The selectable secondary bars use display ranges (reflected: 0–500 W; input: 0–100 W; plate current: 0–3 A; gain: 0–30 dB), not operating limits. Readouts retain values beyond the bar endpoints.

## Offline simulator

`python3 live.py --simulate` (the default when no mode flag is given) opens the page at http://127.0.0.1:51851 with synthetic data and no network access. Pick the simulated model in the simulation panel, or start with `--model OM-4001A`. The OM-4001A simulator follows the manufacturer's protocol document and a real warm-up capture (no antenna switch, per-second warm-up countdown, `#` replies about every 3.2 s) and adds Simulated PA on/off and a menu of injected alerts and faults. Only the Off, warm-up and Standby values come from the capture; everything else is synthetic.

## Building from source

Install Xcode command-line tools, a Python 3.12 environment and PyInstaller 6.22.3. No non-stdlib Python packages are needed to run the server itself. The bundled distribution does not require users to install Python.

```
python3 -m venv .venv
.venv/bin/python -m pip install pyinstaller==6.22.3
OM_BUILD_PYTHON="$PWD/.venv/bin/python" scripts/build.sh
```

The current Mac release is 0.1.33 beta. Its DMG is Developer ID signed, notarized and stapled.

The default local signature is ad hoc. To sign your own build, set OM_SIGN_IDENTITY to your Developer ID Application identity. Public binary distribution additionally needs a timestamped hardened-runtime signing pass, notarization, stapling and clean-machine installation testing. The build script is a local development build, not the complete public-release pipeline.

```
python3 -m unittest discover -s . -v
node test_presentation.cjs
node test_ui_actions.cjs
```

Optional private capture tests require OM_CAPTURE_DIRECTORY pointing to your own capture directory. No packet captures, station preferences, developer keys or live diagnostic traces are included in the public source package.

## Compatibility reports

Report model, firmware version and test results at https://github.com/grmi64/OM-Power-Control/issues. Do not upload unfiltered network captures or personal station settings. Other-model monitoring still uses the OM-3501A protocol and 3500 W scale; readings require independent verification.

## License

Project source: MIT (see LICENSE). Bundled runtime components retain their own licenses; see ThirdPartyNotices. Do not treat the project license as replacing third-party notices or manufacturer rights.

## Automatic tuning

Select Operate and stop transmitting before choosing Auto-tune. Confirm, wait for WAITING FOR INPUT POWER, then supply a steady carrier at the manufacturer-prescribed tuning drive level. Stop transmitting when tuning completes or stops. A green SUCCESSFUL AUTOTUNE banner requires the amplifier’s completion message; automatic saving is reported separately. Dismiss hides the success banner without sending any amplifier command.

Exit works while waiting. Stop can interrupt an active tune, but the operator must stop RF from the radio. After an interruption, stop transmitting before clicking Exit auto-tune. The confirmation explains that exiting after RF release restores defaults, while exiting after Stop may save the current settings. The app waits for the corresponding amplifier acknowledgment and never labels either outcome a successful tune.

An unanswered Exit was observed in the Windows client during one Stop test. The Mac app sends a command once, reports uncertainty on timeout, and does not retry automatically. Unknown replies and delayed communication require operator review; do not assume tuning succeeded.

Live checks covered successful tuning and saving, waiting-state Exit, RF-release abort/default restoration, and Stop/Exit/user-settings acknowledgment on one OM-3501A. Other failure conditions have not been deliberately induced. Local packet captures are optional tests and are not distributed.
