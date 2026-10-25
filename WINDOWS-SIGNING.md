# Windows release signing

Azure Artifact Signing Basic is configured for individual publisher Gregory
Miller. Account: `ny6comsigning`; Public Trust profile: `ompowerrelease`;
region: West US 2; endpoint: `https://wus2.codesigning.azure.net/`.
The signed application code is merged main `f5451a3`.

## Local prerequisites

Microsoft Artifact Signing Client Tools and Azure CLI were installed through
their official WinGet packages. Local paths on this PC:

- SignTool: `C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe`
- Signing plugin: `%LOCALAPPDATA%\Microsoft\MicrosoftArtifactSigningClientTools\Azure.CodeSigning.Dlib.dll`
- Azure CLI: `C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd`

Authenticate interactively using the publisher account. Never place access
tokens, passwords or CLI credential caches in source control or release ZIPs.
Private local metadata is in ignored `.tmp/signing/metadata.json`; it contains
the endpoint/account/profile and selects Azure CLI credentials. No token is
embedded in that JSON.

## Release sequence

1. Build and test the final source. The build script produces an unsigned EXE.
2. Sign the final EXE using SignTool with `/fd SHA256`, the signing plugin
   (`/dlib`), the metadata file (`/dmdf`), and timestamp parameters
   `/tr http://timestamp.acs.microsoft.com /td SHA256`.
3. Run `signtool verify /pa /all /v /tw` on that EXE. Confirm the intended
   publisher, trusted chain and timestamp. Also check `Get-AuthenticodeSignature`.
4. Recreate the ZIP and SHA-256 sidecar after signing; verify its extracted EXE
   exactly matches the signed file. Rebuilding the EXE invalidates this step and
   requires signing again.
5. Repeat offline acceptance on this exact ZIP in a fresh network-disabled
   Sandbox. Keep a record of signature verification, checksum and test results.
6. Resolve the remaining publication gates before uploading or creating a tag.

The short signing-certificate validity is expected. The verified timestamp
allows signature validation after certificate expiration, subject to revocation
and Windows trust policy. It does not impose an application expiration date.
Signing does not guarantee that SmartScreen reputation warnings disappear.

References: [Microsoft signing integration](https://learn.microsoft.com/en-us/azure/artifact-signing/how-to-signing-integrations),
[SignTool](https://learn.microsoft.com/en-us/windows/win32/seccrypto/signtool),
and [Artifact Signing FAQ](https://learn.microsoft.com/en-us/azure/artifact-signing/faq).

This document records the local workflow; it does not grant amplifier access or
authorize release publication. App acceptance remains offline in simulation.
