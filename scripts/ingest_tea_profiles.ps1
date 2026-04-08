# .\scripts\ingest_tea_profiles.ps1
Write-Host "Ingesting data for tea_profiles database..."

# Activate venv if needed
& "$PSScriptRoot\..\venv\Scripts\Activate.ps1"

# Run the Python ingestion module
python -m src.app.ingest_tea_profiles

# Check exit code
if ($LASTEXITCODE -ne 0) {
    Write-Host "Ingestion failed. Python exited with code $LASTEXITCODE"
    exit $LASTEXITCODE
}

Write-Host "Ingestion complete"