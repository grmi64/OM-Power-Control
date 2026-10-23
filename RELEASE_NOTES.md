OM Power Control 0.1.30 beta

Apple Silicon · macOS 14 or later · by NY6C

New since 0.1.26:
- Automatic tuning on the verified OM-3501A: confirmed entry/readiness, live readings, Stop, and Exit.
- Operator supplies and controls RF; the app does not key the radio or adjust drive power.
- Green SUCCESSFUL AUTOTUNE banner with amplifier-reported automatic saving. The banner remains until Dismiss; each new successful tune shows it again.
- Clear distinction between successful tuning, defaults restored after RF interruption, and settings saved after Stop. Interrupted/stopped tuning is never reported as successful.
- Unexpected replies, delayed tuning status, connection loss and unanswered commands display warnings without automatic retries.
- Clear instruction: “Stop transmitting before clicking Exit auto-tune.”

Includes the existing configurable measurements, antenna display, compact/stay-on-top view, About menu, callsign badge and optional DX Caliber sharing through one amplifier connection. DXC’s embedded panel continues to provide its existing readings and power/mode controls; auto-tune controls are in the standalone app.

Validation: live operator checks of successful tune/save, entry/Exit, RF interruption/default recovery, and Stop/Exit acknowledgment. All six local auto-tune captures replayed in regression tests; 72 Python tests completed (70 passed, two unrelated optional capture tests skipped), plus JavaScript presentation and actual UI-handler checks.

Compatibility is established only for the tested OM-3501A. Other models remain monitoring only. Some abnormal amplifier responses and firmware behaviors remain unverified. An unanswered Stop/Exit sequence observed in the Windows client is handled as uncertain rather than automatically retried.

The app and DMG are Developer ID signed, Apple-notarized and stapled. No Python installation is required. Close other amplifier clients before connecting; one client owns the amplifier connection.
