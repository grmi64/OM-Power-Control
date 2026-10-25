# Local MSIX feasibility layout

This is a reference template for the successful local feasibility test, not a
Store-ready identity or a turnkey production build. No package was submitted.

The tested staging layout was:

```
payload/
  AppxManifest.xml
  App/                 # Exact existing portable app folder, including _internal
  Assets/Logo44.png
  Assets/Logo50.png
  Assets/Logo150.png
```

The PNGs were resized from Assets/AppIcon.iconset/icon_256x256.png. Substitute
`@PUBLISHER@` with the signing certificate subject and `@VERSION@` with a local
four-part version before validating the manifest. The test used the separate
identity OMPowerControl.Feasibility and Azure-signed sideload packages. Do not
assume this identity/publisher matches a future Partner Center reservation.

Use the matching MakeAppx and SignTool binaries and dependencies from the Windows
SDK. The successful tools came from Microsoft.Windows.SDK.BuildTools
10.0.28000.2705; the earlier SignTool-only installation could sign EXEs but did
not recognize the MSIX format. No Windows security policy or certificate trust
store was changed to install these tests.

```
makeappx.exe pack /d payload /p LocalFeasibility.msix /o
```

Sign the local test MSIX with the existing Artifact Signing plugin/metadata and
SHA-256/RFC 3161 timestamp, then verify with `signtool verify /pa /all /tw`.
Install only in a disposable network-disabled Windows Sandbox for these tests.
The default app entry has no hardware arguments; test activation used the Windows
package activation API and confirmed the actual process package identity.

Current assets, signed prototypes, tool provenance, activation/lifecycle helpers
and results remain private under ignored `.tmp/msix-feasibility/` and
`.tmp/clean-pc-test/`. See WINDOWS-MSIX-FEASIBILITY.md for results and remaining
Store preparation. Keep the original signed portable EXE/ZIP unchanged.
