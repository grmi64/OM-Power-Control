param([string]$Python = 'py')
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
if ($Python -eq 'py') { & $Python -3.12 -m venv .venv } else { & $Python -m venv .venv }
if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 is required. Install it or pass -Python with its full executable path.' }
& .\.venv\Scripts\python.exe -m pip install -r requirements-windows.lock.txt
if ($LASTEXITCODE -ne 0) { throw 'Windows dependency installation failed.' }
Write-Output 'Ready. Run .\.venv\Scripts\python.exe windows_app.py for offline simulation.'
