#!/bin/bash
set -eu
cd "$(dirname "$0")/.."
APP="${OM_BUILD_APP:-$PWD/dist/OM Power Control.app}"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources" /tmp/om3501a-swift-cache
swiftc -target arm64-apple-macos14.0 -module-cache-path /tmp/om3501a-swift-cache -O Sources/App.swift Sources/WindowPlacement.swift -framework Cocoa -framework WebKit -o "$APP/Contents/MacOS/OM3501AControl"
BUILD_PYTHON="${OM_BUILD_PYTHON:-python3}"
PYINSTALLER_CONFIG_DIR=/tmp/om3501a-pyinstaller "$BUILD_PYTHON" -m PyInstaller --noconfirm --onedir --name amp-engine --distpath /tmp/om3501a-frozen --workpath /tmp/om3501a-freeze-work --specpath /tmp/om3501a-freeze-spec --add-data "$PWD/live.html:." --add-data "$PWD/presentation.js:." live.py
rm -rf "$APP/Contents/Resources/amp-engine"
ditto /tmp/om3501a-frozen/amp-engine "$APP/Contents/Resources/amp-engine"
/usr/bin/python3 - "$APP" <<'PY'
import plistlib,sys
from pathlib import Path
p=Path(sys.argv[1])/'Contents/Info.plist'
p.write_bytes(plistlib.dumps(dict(CFBundleIdentifier='com.grmi64.OM3501AControl',CFBundleName='OM Power Control',CFBundleDisplayName='OM Power Control',CFBundleExecutable='OM3501AControl',CFBundlePackageType='APPL',CFBundleShortVersionString='0.1.26',CFBundleVersion='27',LSMinimumSystemVersion='14.0',NSHighResolutionCapable=True,NSPrincipalClass='NSApplication',NSLocalNetworkUsageDescription='Connect to your OM-3501A amplifier for readings and operating controls on your local network.',NSAppTransportSecurity={'NSAllowsLocalNetworking':True})))
PY
cp Assets/AppIcon.icns "$APP/Contents/Resources/AppIcon.icns"
/usr/libexec/PlistBuddy -c 'Add :CFBundleIconFile string AppIcon.icns' "$APP/Contents/Info.plist"
ditto ThirdPartyNotices "$APP/Contents/Resources/ThirdPartyNotices"
cp LICENSE "$APP/Contents/Resources/LICENSE.txt"
codesign --force --deep --sign "${OM_SIGN_IDENTITY:--}" "$APP"
echo "$APP"
