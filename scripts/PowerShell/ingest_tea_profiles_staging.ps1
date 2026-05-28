# .\scripts\PowerShell\ingest_tea_profiles_staging.ps1
Write-Host "Ingesting tea_profiles data in STAGING..."

# Ensure we're running from repo root so Python can resolve src.*
Set-Location "$PSScriptRoot\..\.."

# Load staging environment variables
& "$PSScriptRoot\load_env.ps1" -EnvFilePath "$PSScriptRoot\..\..\.env.staging"

# Activate venv if needed
& ".\venv\Scripts\Activate.ps1"

# Run the Python ingestion module
python -m src.app.ingest_tea_profiles

# Check exit code
if ($LASTEXITCODE -ne 0) {
    Write-Host "Ingestion failed. Python exited with code $LASTEXITCODE"
    exit $LASTEXITCODE
}

Write-Host "Ingestion complete in STAGING"
