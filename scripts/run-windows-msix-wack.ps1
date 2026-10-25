param(
    [Parameter(Mandatory=$true)][string]$PackagePath,
    [Parameter(Mandatory=$true)][string]$ReportDirectory,
    [string]$KitDirectory='C:\Program Files (x86)\Windows Kits\10\App Certification Kit'
)
$ErrorActionPreference='Stop'
# Run inside a network-disabled disposable Windows test environment only.
if(@(Get-NetAdapter -ErrorAction Stop).Count){throw 'Network-disabled test environment required'}
$source=(Resolve-Path -LiteralPath $PackagePath).Path
if([IO.Path]::GetExtension($source) -ne '.msix'){throw 'Supply the MSIX package file, not an installed package identity'}
$appcert=Join-Path $KitDirectory 'appcert.exe'
$signature=Get-AuthenticodeSignature -LiteralPath $appcert
if($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notlike 'CN=Microsoft Corporation,*'){throw 'WACK executable signature invalid'}
$runId=[guid]::NewGuid().ToString('N')
$work=Join-Path $env:TEMP ('om-wack-'+$runId)
$output=Join-Path $ReportDirectory $runId
New-Item -ItemType Directory -Path $work,$output -Force | Out-Null
$localPackage=Join-Path $work 'candidate.msix'
Copy-Item -LiteralPath $source -Destination $localPackage
$hash=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
if((Get-FileHash -LiteralPath $localPackage -Algorithm SHA256).Hash -ne $hash){throw 'Staged package hash mismatch'}
$record=[ordered]@{workflow='appxpackagepath';package_sha256=$hash;network_adapters=0;completed=$false;started_utc=[DateTime]::UtcNow.ToString('o')}
try {
    & $appcert reset *> (Join-Path $work 'reset.log')
    $record.reset_exit_code=$LASTEXITCODE
    if($LASTEXITCODE -ne 0){throw 'WACK reset failed'}
    $report=Join-Path $work 'report.xml'
    # Installed-identity analysis produced a DPI parser error for the same EXE.
    & $appcert test -appxpackagepath $localPackage -reportoutputpath $report *> (Join-Path $work 'console.log')
    $record.exit_code=$LASTEXITCODE
    if(-not(Test-Path -LiteralPath $report)){throw 'WACK did not produce a report'}
    $record.completed=$true
} finally {
    $record.finished_utc=[DateTime]::UtcNow.ToString('o')
    $record | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $work 'run.json')
    Get-ChildItem -LiteralPath $work -File | Where-Object Extension -ne '.msix' | Copy-Item -Destination $output
    Write-Output "Reports: $output"
    Write-Output 'Check report.xml with scripts/check-wack-report.py; exit code alone is insufficient.'
}
