# PowerShell: .\scripts\test.ps1

Write-Host "Running tests via Pytest..."

# Tell Python the root of all imports. Lets us run .\test.ps1 instead of 
# $env:PYTHONPATH="." ; pytest
$env:PYTHONPATH = "."
pytest

Write-Host "Done running tests."