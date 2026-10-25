# Windows dependency-notice audit â€” 2026-10-24

Scope: the portable Windows x64 candidate, application code from merged main
`f5451a3`, with local release documentation and notices. No application code or
third-party binary was changed. This audit covers this pinned bundle; dependency
upgrades require renewed review.

## Resolved items

| Component | Evidence and distribution action |
|---|---|
| proxy_tools 0.1.0 | Installed module exactly matches the SHA-256-verified PyPI source release and declares BSD with Ronacher/Tushman copyrights. Preserve upstream BSD license verbatim and retain its conflicting MIT distribution metadata; do not relabel BSD code as MIT. |
| WebView2 SDK 1.0.3856.49 | All five shipped SDK DLLs match bytes from the exact official NuGet package. Include its full Microsoft BSD-style license and third-party NOTICE, including ANTLR/StringTemplate terms. |
| Windows Python | Include the actual Windows runtime LICENSE.txt and versioned CPython license documentation; qualify the existing parent notice overview as Mac-specific. Include exact OpenSSL 3.5.8 and Expat 2.8.3 notices alongside existing native-library terms. |
| Frozen packaging helpers | Include missing altgraph, pefile and pywin32-ctypes licenses. PyInstaller's retained COPYING includes its bundling exception. |
| setuptools vendors | Preserve vendor-specific license files, plus the complete MPL-2.0 and fastjsonschema BSD licenses. Supply unmodified corresponding validation-module/schema source with original NOTICE files. |

The Evergreen WebView2 browser Runtime and .NET Framework are prerequisites,
not part of this ZIP. The SDK loaders/assemblies are separately redistributed.
pywebview's own WebBrowserInterop DLLs and Android helper classes are covered
by its retained MIT license. Microsoft Windows compatibility/runtime DLLs retain
their notices and are included for Windows use; no libheif program/library is
bundled merely because some compatibility DLLs were resolved from that tool's
directory by PyInstaller.

## Repeatable checks

`ThirdPartyNotices/windows/inventory.json` records 55 required notice/source
files and 78 DLL/PYD/JAR files with SHA-256 values and component mappings.
`scripts/check-windows-notices.py` runs offline during builds and rejects missing
or changed notices, an unmapped frozen module root, installed-version drift,
or a changed binary inventory. Six focused regressions cover positive and
negative cases. The complete offline suite passed: 170 Python tests, six expected
skips (176 total), and all five JavaScript suites. Binary upgrades must be reviewed, not automatically rehashed.

The final ZIP's contents were independently checked against the inventory and
the signed local EXE. The EXE remains byte-identical to the prior Azure-signed
candidate; SignTool verifies its Authenticode signature and RFC 3161 timestamp.
No private runtime settings, station traces, or instance locks are in the ZIP.

ZIP SHA-256:
`4b711e4950ae0d787d3055523d4c5bcde0ca7fc8bd114bb9cc418834a2359819`.
The network-disabled Sandbox verified this checksum and passed the packaged
DPI/UI/simulated tune-save/RF-release smoke with exit code 0. These results do
not establish download reputation or physical multiple-monitor behavior.

Private evidence: `.tmp/license-audit/` and
`.tmp/clean-pc-test/results/notice-audit-smoke.json`. This report was written
after packaging and is not inside that exact ZIP; the distributed notice
overview and inventory are inside it.

The dependency-notice release gate is resolved for this pinned candidate.
Physical monitor checks remain deferred. No publication, tag, push, amplifier
connection, operating command, tuning command or power command occurred.

## Primary references

- [Exact WebView2 SDK package](https://www.nuget.org/packages/Microsoft.Web.WebView2/1.0.3856.49)
- [Microsoft WebView2 distribution guidance](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution)
- [proxy_tools upstream license](https://github.com/jtushman/proxy_tools/blob/master/LICENSE.txt)
- [CPython 3.12.14 license documentation](https://github.com/python/cpython/blob/v3.12.14/Doc/license.rst)
- [setuptools 84.2.1 validation sources and notices](https://github.com/pypa/setuptools/tree/v84.2.1/setuptools/config)
- [Mozilla Public License 2.0](https://www.mozilla.org/MPL/2.0/)
