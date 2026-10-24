Windows preview runtime notices

The parent README describes the upstream macOS distribution. This folder adds
licenses for the Windows Python/WebView2 host. Python 3.12.14 and PyInstaller
6.22.3 notices remain in the parent folder. Exact installed dependency versions
are recorded in requirements-windows.lock.txt.

pywebview 6.2.1, pythonnet 3.2.1, clr_loader 0.3.1, cffi 2.1.1,
pycparser 3.12, bottle 0.13.4 and typing_extensions 4.16.0 licenses were copied
from their installed distribution metadata. Additional packaging/setuptools
notices cover components pulled in by packaging hooks.

proxy_tools 0.1.0 omits its license file from the wheel. The BSD license here
was obtained from https://github.com/jtushman/proxy_tools/blob/master/LICENSE.txt
and matches its source header. The wheel's metadata says MIT; the upstream
source and included BSD text are retained for review before public release.

The Microsoft Edge WebView2 Evergreen Runtime and .NET Framework are system
prerequisites, not installed or redistributed by this ZIP. The WebView2 SDK
interop/loader DLLs supplied by pywebview are included in _internal/webview/lib.
They retain Microsoft's licensing terms; see
https://www.nuget.org/packages/Microsoft.Web.WebView2/1.0.3856.49/License
and https://learn.microsoft.com/microsoft-edge/webview2/concepts/distribution .
Complete the redistribution notices review before publishing a public build.
