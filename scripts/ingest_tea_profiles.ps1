# .\scripts\ingest_tea_profiles.ps1
Write-Host "Ingesting data for tea_profiles database..."

# Activate venv if needed
& "$PSScriptRoot\..\venv\Scripts\Activate.ps1"

# Run the Python ingestion module
python -m src.ingest.ingest_tea_profiles

Write-Host "Ingestion complete"