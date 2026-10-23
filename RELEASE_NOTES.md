OM Power Control 0.1.24 beta

Apple Silicon · macOS 14 or later.

New since 0.1.23:
- Added About OM Power Control to the application menu, showing the release version, build number and NY6C attribution.

Included from earlier releases:
- Added expandable amplifier measurements, frequency and temperature in both views, and a signed screen-current meter.
- Added a saved Measurements selector for reflected power, input power, anode/plate current or calculated gain. Labels, units and bar scales change together; the selected item is disabled in the menu.
- Aligned the screen-current marker with the scale labels, including zero and ±30 mA.
- Tidied the compact layout, standardized expanders to +/−, and added NY6C attribution.
- Added freshness checks for additional telemetry and recognition of the verified powered-off listener status.

The app and DMG are Developer ID signed, Apple-notarized and stapled. No Python installation is required.

Installation: download the DMG, open it, drag OM Power Control to Applications, eject the DMG, then launch from Applications. Quit the previous version before replacing it. Close other amplifier clients before connecting. Existing local settings are retained; new installs have no station address and auto-connect is off.

Tested with one OM-3501A. Other models remain unverified and monitoring only. Additional telemetry scaling and full-range reflected-power calibration remain under validation. The bar scales are display ranges, not operating limits. No Intel or Windows binary is included.

No station settings or network captures are distributed.
