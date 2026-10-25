param([switch]$SkipTests)
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
if (-not $SkipTests) { & (Join-Path $PSScriptRoot 'test-windows.ps1') }
$project = (Get-Location).Path
$targetExe = Join-Path $project 'dist\windows\OM Power Control\OM Power Control.exe'
if (Get-Process -Name 'OM Power Control' -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $targetExe }) { throw 'Close the running packaged app before rebuilding its folder.' }
# Force handles OneDrive's read-only directory attributes, which shutil.rmtree
# in PyInstaller does not clear. Only these two generated folders are removed.
foreach ($relative in @('build\windows\OM Power Control','dist\windows\OM Power Control')) {
    $generatedPath = [IO.Path]::GetFullPath((Join-Path $project $relative))
    if (-not $generatedPath.StartsWith($project + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Generated path escaped project.' }
    if (Test-Path -LiteralPath $generatedPath) { Remove-Item -LiteralPath $generatedPath -Recurse -Force }
}
& .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onedir --windowed --manifest "$project\windows_app.manifest" --name 'OM Power Control' --distpath dist/windows --workpath build/windows --specpath build --add-data "$project\live.html;." --add-data "$project\presentation.js;." --add-data "$project\LICENSE;." --add-data "$project\ThirdPartyNotices;ThirdPartyNotices" --collect-all webview --hidden-import clr_loader --hidden-import pythonnet --copy-metadata pywebview --copy-metadata pythonnet windows_app.py
if ($LASTEXITCODE -ne 0) { throw 'Windows packaging failed.' }
& .\.venv\Scripts\python.exe scripts/check-windows-notices.py
if ($LASTEXITCODE -ne 0) { throw 'Windows dependency notice audit failed.' }
Copy-Item -LiteralPath WINDOWS.md -Destination 'dist/windows/OM Power Control/README-Windows.txt'
Copy-Item -LiteralPath WINDOWS-VALIDATION.md -Destination 'dist/windows/OM Power Control/'
Copy-Item -LiteralPath WINDOWS-RELEASE-NOTES.md -Destination 'dist/windows/OM Power Control/'
Copy-Item -LiteralPath requirements-windows.lock.txt -Destination 'dist/windows/OM Power Control/'
$archive = Join-Path (Get-Location) 'dist/OM-Power-Control-0.1.31-windows-x64-preview.zip'
Compress-Archive -Path 'dist/windows/OM Power Control' -DestinationPath $archive -Force
$hash = Get-FileHash -LiteralPath $archive -Algorithm SHA256
"$($hash.Hash.ToLower())  $([IO.Path]::GetFileName($archive))" | Set-Content -LiteralPath "$archive.sha256" -Encoding ascii
Write-Output $archive
