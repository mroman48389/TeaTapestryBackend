# PowerShell: .\scripts\test.ps1

Write-Host "Running tests via Pytest..."

# Compute absolute project root
$projectRoot = Join-Path $PSScriptRoot "..\.."

# Compute absolute src path
$srcPath = Join-Path $projectRoot "src"

# Set PYTHONPATH for this process only
$env:PYTHONPATH = $srcPath

# Run pytest with explicit rootdir
pytest --rootdir $projectRoot

Write-Host "Done running tests."