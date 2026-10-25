param(
    [Parameter(Mandatory=$true)][string]$SdkBin,
    [string]$IdentityFile,
    [string]$PortableApp,
    [string]$OutputDirectory,
    [string]$PackageVersion
)
$ErrorActionPreference='Stop'
$project=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if(-not $IdentityFile){$IdentityFile=Join-Path $project 'packaging/windows-store/identity.json'}
if(-not $PortableApp){$PortableApp=Join-Path $project 'dist/windows/OM Power Control'}
if(-not $OutputDirectory){$OutputDirectory=Join-Path $project 'dist/msix'}
$identity=Get-Content -LiteralPath $IdentityFile -Raw | ConvertFrom-Json
if(-not $PackageVersion){$PackageVersion=$identity.package_version}
if($PackageVersion -notmatch '^\d+\.\d+\.\d+\.\d+$'){throw 'Use a four-part MSIX version'}
$version=[Version]$PackageVersion
if($version.Major -lt 1 -or $version.Revision -ne 0 -or $version.Major -gt 65535 -or $version.Minor -gt 65535 -or $version.Build -gt 65535){throw 'Store version must start above zero and end in .0; components must be 0..65535'}
if($identity.name -notmatch '^[A-Za-z0-9.-]{3,50}$'){throw 'Invalid package identity name'}
if($identity.publisher -notmatch '^CN=[0-9A-Fa-f-]{36}$'){throw 'Expected the exact Store GUID publisher identity'}
if($identity.architecture -ne 'x64'){throw 'Only x64 is validated for this build'}
if($identity.package_family_name -notmatch ('^'+[regex]::Escape($identity.name)+'_[a-z0-9]{13}$')){throw 'Package family name does not match the identity name'}
$makeappx=Join-Path $SdkBin 'makeappx.exe'
if(-not (Test-Path -LiteralPath $makeappx)){throw 'Supply a Windows SDK directory containing MakeAppx and its dependencies'}
if((Get-AuthenticodeSignature -LiteralPath $makeappx).Status -ne 'Valid'){throw 'MakeAppx signature is not valid'}
$sourceExe=Join-Path $PortableApp 'OM Power Control.exe'
if((Get-AuthenticodeSignature -LiteralPath $sourceExe).Status -ne 'Valid'){throw 'Build/sign the portable app before staging the Store candidate'}
$sourceHash=(Get-FileHash -LiteralPath $sourceExe -Algorithm SHA256).Hash
$output=Join-Path $OutputDirectory "OM-Power-Control-Store-$version-x64-unsigned.msix"
if(Test-Path -LiteralPath $output){throw 'Output already exists; choose a fresh output directory or version'}
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$stage=Join-Path $project ('build/msix/store-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path (Join-Path $stage 'Assets') -Force | Out-Null
Copy-Item -LiteralPath $PortableApp -Destination (Join-Path $stage 'App') -Recurse
& (Join-Path $project '.venv/Scripts/python.exe') (Join-Path $project 'scripts/check-windows-notices.py') --package (Join-Path $stage 'App')
if($LASTEXITCODE -ne 0){throw 'Store payload notice audit failed'}
Add-Type -AssemblyName System.Drawing
$icon=[Drawing.Image]::FromFile((Join-Path $project 'Assets/AppIcon.iconset/icon_256x256.png'))
try {
    foreach($size in @(44,50,150)){
        $bitmap=New-Object Drawing.Bitmap($size,$size)
        $graphics=[Drawing.Graphics]::FromImage($bitmap)
        try {
            $graphics.InterpolationMode=[Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
            $graphics.DrawImage($icon,0,0,$size,$size)
            $bitmap.Save((Join-Path $stage "Assets/Logo$size.png"),[Drawing.Imaging.ImageFormat]::Png)
        } finally {$graphics.Dispose();$bitmap.Dispose()}
    }
} finally {$icon.Dispose()}
$manifest=Get-Content -LiteralPath (Join-Path $project 'packaging/windows-store/AppxManifest.xml.in') -Raw -Encoding UTF8
$values=@{NAME=$identity.name;PUBLISHER=$identity.publisher;VERSION=$version.ToString();DISPLAY_NAME=$identity.display_name;PUBLISHER_DISPLAY_NAME=$identity.publisher_display_name;MIN_VERSION=$identity.min_windows_version;MAX_VERSION=$identity.max_version_tested}
foreach($key in $values.Keys){$manifest=$manifest.Replace("@$key@",[Security.SecurityElement]::Escape([string]$values[$key]))}
if($manifest -match '@[A-Z_]+@'){throw 'Unresolved manifest placeholder'}
$manifest | Set-Content -LiteralPath (Join-Path $stage 'AppxManifest.xml') -Encoding UTF8
Copy-Item -LiteralPath (Join-Path $project 'packaging/windows-store/README.md') -Destination (Join-Path $stage 'README-Store.txt')
& $makeappx pack /d $stage /p $output /no
if($LASTEXITCODE -ne 0){throw 'MSIX semantic validation/packing failed'}
if((Get-FileHash -LiteralPath $sourceExe -Algorithm SHA256).Hash -ne $sourceHash){throw 'Original portable EXE changed unexpectedly'}
$hash=(Get-FileHash -LiteralPath $output -Algorithm SHA256).Hash.ToLower()
"$hash  $([IO.Path]::GetFileName($output))" | Set-Content -LiteralPath "$output.sha256" -Encoding ascii
@{package=$output;package_sha256=$hash;version=$version.ToString();identity=$identity.name;publisher=$identity.publisher;expected_family_name=$identity.package_family_name;source_exe_sha256=$sourceHash.ToLower();stage=$stage;signature='unsigned Store candidate; do not sideload as a signed release'} | ConvertTo-Json | Set-Content -LiteralPath "$output.build.json" -Encoding UTF8
Write-Output $output
