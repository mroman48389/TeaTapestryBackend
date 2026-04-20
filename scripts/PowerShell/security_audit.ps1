# Runs the backend security audit Node script

Write-Host "Running backend security audit..." -ForegroundColor Cyan

# Resolve the path to the Node script
$scriptPath = Join-Path $PSScriptRoot "..\Node\security_audit.mjs"

# Execute the Node script
node $scriptPath

if ($LASTEXITCODE -ne 0) {
    Write-Host "Security audit failed." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "Security audit passed successfully." -ForegroundColor Green
