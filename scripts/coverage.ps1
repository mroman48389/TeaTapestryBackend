Write-Host "Running coverage report for app/ via Pytest..."

$env:PYTHONPATH = '.'
pytest --cov=app --cov-report=term-missing

Write-Host "Done producing coverage report."