# Mac review: shared RF-off compatibility fix

Prepare and test the review branch without replacing the installed Mac app or
changing its production preferences. Do not merge or publish a release yet.

Branch: `review/rf-off-compatibility` in
https://github.com/grmi64/OM-Power-Control. Clone it into a new directory outside
cloud-synced folders; do not reset or overwrite an existing checkout:

```sh
git clone --branch review/rf-off-compatibility --single-branch \
  https://github.com/grmi64/OM-Power-Control.git OM-Power-Control-RF-Review
cd OM-Power-Control-RF-Review
git log -1 --oneline
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install pyinstaller==6.22.3
mkdir -p .tmp
```

Record the tested commit hash in the results. If Python 3.12, Node.js or Xcode
command-line tools are missing, report that before changing system-wide tools.

The shared `decoder.py` now handles idle NUL framing and a narrow saved-tune
RF-off compatibility rule. After successful tuning and SAVE USER, a fresh
positive-to-zero plate-current transition can clear the transmit latch in
Operate. New PTTON or mode changes cancel that context. Timers and ordinary
zero readings cannot clear it. The shared UI displays expired RF-active state
as unconfirmed and retains command guards. Windows-only test policies and raw
tracing support are also included in the pending changes.

The earlier failed hardware capture now passes offline replay. The subsequent
Windows Ethernet test passed tuning, saving, explicit PTTOFF and app-driven
Standby. That successful run did not exercise the fallback live. See
`WINDOWS-VALIDATION.md` for the evidence and limits. The Mac previously passed
read-only reconnect tests; it has not yet tested these newer changes.

## Offline work first

Use a separate checkout of the review branch and an isolated Python 3.12 virtual
environment. Review the diff from main. Run:

```sh
python -m unittest discover -s . -v
for test in test_presentation.cjs test_ui_actions.cjs test_autotune_presentation.cjs test_autotune_ui.cjs test_windows_ui.cjs; do
  node "$test" || exit 1
done
```

Windows validation: 142 Python tests, 136 passed and six optional capture skips;
all five JavaScript suites passed. Investigate any platform-specific difference.

For the existing Apple Silicon/macOS 14+ build target, install the README's
build dependencies into the isolated environment. Choose a new output path:

```sh
OM_BUILD_PYTHON="$VIRTUAL_ENV/bin/python" \
OM_BUILD_APP="$PWD/dist/OM Power Control RF Review.app" bash scripts/build.sh
```

Do not copy this bundle into /Applications. The wrapper selects hardware mode
and may auto-connect using saved settings, so do not launch it as an offline
check. Instead smoke-test its bundled backend in simulation with a new private
settings file:

```sh
OM_SETTINGS_PATH="$PWD/.tmp/mac-rf-review-settings.json" \
  "dist/OM Power Control RF Review.app/Contents/Resources/amp-engine/amp-engine" \
  --simulate --port 0
```

Open the printed localhost URL. Confirm simulation labels, tuning/save flow,
RF-off presentation and guards. Stop the process cleanly afterward. Do not
change production settings or the installed app. Review native-wrapper launch
separately with isolated preferences before opening the test bundle.

## Hardware gate

No new hardware connection or operating test is authorized by this handoff.
Report offline/build results first. Ask the operator before connecting, and
obtain separate explicit approval for any Operate/tuning test. Close the Windows
reader before an approved Mac connection. The operator alone supplies/stops RF
and adjusts drive; the app must never key the radio or adjust its drive power.
No power commands are authorized. Preserve private traces outside Git.
