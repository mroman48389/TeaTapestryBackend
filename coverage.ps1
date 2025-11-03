Write-Host "Running coverage report for app/..."
$env:PYTHONPATH = '.'
pytest --cov=app --cov-report=term-missing