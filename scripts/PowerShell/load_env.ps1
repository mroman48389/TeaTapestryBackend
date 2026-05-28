# Used by other scripts to load the proper .env file before running the scripts.

param(
    [string]$EnvFilePath
)

if (-Not (Test-Path $EnvFilePath)) {
    Write-Host "Env file not found: $EnvFilePath"
    exit 1
}

Get-Content $EnvFilePath | ForEach-Object {
    if ($_ -match "^\s*#") { return }
    if ($_ -match "^\s*$") { return }

    $parts = $_.Split("=", 2)
    $key = $parts[0].Trim()
    $value = $parts[1].Trim()

    # Universal, safe, PowerShell-compatible environment variable assignment
    [System.Environment]::SetEnvironmentVariable($key, $value, "Process")
}
