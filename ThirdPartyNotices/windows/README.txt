Windows runtime notices — audited 2026-10-24

Scope: portable Windows x64 bundle, application code main f5451a3. The parent
README describes the upstream Mac distribution. inventory.json records this
Windows bundle's components, versions, notice/source hashes and binary hashes.
Third-party components retain their own licenses; the application's MIT license
does not replace them. Keep this complete notice directory with the app.

Python/runtime
--------------
Python-Windows-LICENSE.txt is the exact Windows Python 3.12.14 runtime license,
including Microsoft Distributable Code restrictions and bzip2 notices.
Python-3.12.14-history-and-license.rst contains the complete upstream versioned
license documentation, including incorporated third-party code.
Source: https://github.com/python/cpython/tree/v3.12.14
OpenSSL 3.5.8 and Expat 2.8.3 were checked against loaded runtime versions;
their exact upstream licenses are included separately. Parent notices retain
libffi, liblzma, zlib, mpdecimal and bzip2 terms. Python's Microsoft runtime DLLs
and API-set/UCRT compatibility DLLs retain Microsoft's notices. These components
are distributed for use with this application on Microsoft Windows only; do not
alter their notices or imply Microsoft endorsement.

Python modules
--------------
Licenses for pywebview 6.2.1, pythonnet 3.2.1, clr_loader 0.3.1, cffi 2.1.1,
pycparser 3.12, bottle 0.13.4, typing_extensions 4.16.0, packaging 26.3,
altgraph 0.17.5, pefile 2024.8.26 and pywin32-ctypes 0.2.3 come from their
exact installed metadata. This includes helpers pulled into the frozen app by
packaging analysis. Parent PyInstaller-COPYING.txt includes its bundling exception.

proxy_tools 0.1.0
-----------------
Its wheel and release source archive omit a license file. The installed module
is byte-identical to the release source and explicitly declares BSD licensing
and Ronacher/Tushman copyrights. proxy_tools-LICENSE.txt retains the upstream
BSD license verbatim. proxy_tools-METADATA.txt also preserves the conflicting
MIT metadata; we do not rewrite it or label the BSD source exclusively MIT.
Distribution retains the BSD copyright, conditions and disclaimer required by
the source license.
Source: https://github.com/jtushman/proxy_tools/blob/master/LICENSE.txt
Release source archive SHA-256:
ccb3751f529c047e2d8a58440d86b205303cf0fe8146f784d1cbcd94f0a28010

setuptools 84.2.1 and vendors
----------------------------
setuptools-vendor/ retains vendor-specific licenses (including packaging's
Apache/BSD alternatives and the PSF/MIT/BSD licenses of other vendors).
setuptools-validation-source/ supplies complete unmodified corresponding source
for the bundled validation modules and schemas. Their NOTICE files identify
validate-pyproject (MPL-2.0) and fastjsonschema (BSD-3-Clause); full licenses
accompany this source. You may use, modify and redistribute these source files
under their respective licenses, independently of the application's MIT license.
Sources: https://github.com/pypa/setuptools/tree/v84.2.1/setuptools/config
https://github.com/abravalheri/validate-pyproject
https://github.com/horejsek/python-fastjsonschema

WebView2 SDK and system prerequisites
-------------------------------------
The five shipped SDK DLLs match bytes from the exact official
Microsoft.Web.WebView2 1.0.3856.49 NuGet package (two .NET assemblies and three
architecture-specific loaders). That package supplies a BSD-style Microsoft
license and a NOTICE containing ANTLR/StringTemplate terms. Both are included
verbatim: WebView2-1.0.3856.49-LICENSE.txt and WebView2-1.0.3856.49-NOTICE.txt.
Package: https://www.nuget.org/packages/Microsoft.Web.WebView2/1.0.3856.49
pywebview's WebBrowserInterop DLLs and unused Android helper JAR remain under
pywebview's MIT license; the JAR contains com.pywebview classes only.

The Evergreen browser Runtime and .NET Framework are system prerequisites, not
redistributed or installed by this ZIP. SDK loaders/assemblies are distinct from
the browser Runtime. Missing Runtime guidance directs users to Microsoft.
https://learn.microsoft.com/microsoft-edge/webview2/concepts/distribution

Audit/checking
--------------
scripts/check-windows-notices.py runs offline during packaging. It verifies
notice/source hashes (accepting Git LF/CRLF conversion), frozen module-root coverage, dependency versions, and
all bundled DLL/PYD/JAR names and bytes. Changed dependencies/binaries require
renewed notice/provenance review; do not blindly refresh inventory hashes.
Signing the main EXE does not alter these third-party files. No amplifier
access is involved.
