# PowerShell: .\scripts\coverage.ps1

Write-Host "Running coverage report for app/ via Pytest..."

$env:PYTHONPATH = '.'
pytest --cov=src --cov-report=term-missing

Write-Host "Done producing coverage report."