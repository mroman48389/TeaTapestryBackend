# .\scripts\PowerShell\seed_tea_profiles_staging.ps1
Write-Host "Seeding tea_profiles database in STAGING..."

# Ensure we're running from repo root so Python can resolve src.*
Set-Location "$PSScriptRoot\..\.."

# Load staging environment variables
& "$PSScriptRoot\load_env.ps1" -EnvFilePath "$PSScriptRoot\..\..\.env.staging"

# Activate venv if needed
& ".\venv\Scripts\Activate.ps1"

# Run the Python seeding module
python -m src.app.seed_tea_profiles

if ($LASTEXITCODE -ne 0) {
    Write-Host "Seeding failed. Python exited with code $LASTEXITCODE"
    exit $LASTEXITCODE
}

Write-Host "Seeding complete in STAGING"