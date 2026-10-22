# OM Power Control

An independent, open-source macOS controller for the OM Power OM-3501A amplifier over its Ethernet interface. It is not an official OM Power product and is not affiliated with or endorsed by the manufacturer.

The first public build is intended as a beta. Hardware verification so far covers one OM-3501A; compatibility with other models or firmware revisions is not claimed.

## Features

- Forward power, reflected power and calculated SWR.
- SWR and reflected readings share a blended green/amber/red mismatch color; idle or unavailable readings are neutral.
- Editable amplifier model label. OM-3501A is tested; other model names enable monitoring only and block operating commands. The model label does not select a different protocol.
- Operate/Standby, normal shutdown/cooling, and power-on/warm-up.
- Amplifier-confirmed state, transmission guards and no automatic operating-command retries.
- Full and compact views, saved stay-on-top and optional callsign badge.
- Fixed 3500 W bar scale: green low-power region, amber at 1500 W, orange at 2500 W, red at 3500 W, with blended transitions. These are display colors, not calibrated protection limits or recommendations to transmit at a particular power.
- Optional auto-connect, off by default. One local reader process; disconnect other remote-control clients before connecting.

## Requirements and setup

The initial binary targets Apple Silicon Macs and macOS 14 or later. Older macOS versions, Intel Macs, Windows, other amplifier models and additional firmware revisions need separate builds/testing. Set the amplifier IP address and TCP port in Connection & station, save, then Connect. No USB connection is used. Configure the amplifier's network interface using its manufacturer instructions. Your callsign, address and preferences stay on your computer; they are not part of the download.

Use the amplifier within its manufacturer operating requirements and your station limits. The software preserves the normal cooling and warm-up sequences. Disconnecting or quitting closes remote communication; it does not turn the amplifier off. The amplifier's own protections remain responsible for hardware protection. The app does not implement antenna/tuning/fault-reset controls.

## Protocol status

The driver was independently implemented from local hardware traffic. Exact status codes ST1110 and ST1100 were verified against front-panel Operate and Standby. Unknown status codes remain unconfirmed. SWR is calculated from measured forward/reflected power. Two live RF comparisons matched the amplifier display; forward power/SWR were also checked against a separate PowerMaster II. Full-range measurement calibration and extensive fault testing are not claimed.

## Building from source

Install Xcode command-line tools, a Python 3.12 environment and PyInstaller 6.22.3. No non-stdlib Python packages are needed to run the server itself. The bundled distribution does not require users to install Python.

```
python3 -m venv .venv
.venv/bin/python -m pip install pyinstaller==6.22.3
OM_BUILD_PYTHON="$PWD/.venv/bin/python" scripts/build.sh
```

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
