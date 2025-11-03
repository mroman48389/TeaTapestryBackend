Write-Host "Running autopep8 with custom rules..."

# E201: Ignore whitespace after [ and (.
# E202: Ignore whitespace before ) and ].
autopep8 . --in-place --recursive --aggressive --ignore E201,E202 --exclude venv,__pycache__,.git

Write-Host "Done cleaning code."