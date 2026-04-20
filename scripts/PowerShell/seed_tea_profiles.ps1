# .\scripts\seed_tea_profiles.ps1
Write-Host "Seeding tea_profiles database..."

# Activate venv if needed
& "$PSScriptRoot\..\venv\Scripts\Activate.ps1"

# Run the Python seeding module
python -m src.seed.seed_tea_profiles

Write-Host "Seeding complete"