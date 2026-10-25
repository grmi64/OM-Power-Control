$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
& .\.venv\Scripts\python.exe -m unittest discover -s . -v
if ($LASTEXITCODE -ne 0) { throw 'Python tests failed.' }
foreach ($test in @('test_presentation.cjs','test_ui_actions.cjs','test_autotune_presentation.cjs','test_autotune_ui.cjs','test_windows_ui.cjs','test_windows_access.cjs')) {
    & node $test
    if ($LASTEXITCODE -ne 0) { throw "UI test failed: $test" }
}
