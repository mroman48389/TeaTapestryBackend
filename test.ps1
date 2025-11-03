# Tell Python the root of all imports. Lets us run .\test.ps1 instead of 
# $env:PYTHONPATH="." ; pytest
$env:PYTHONPATH = "."
pytest