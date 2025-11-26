param(
    [string]$DatabaseName = $env:DB_NAME
)

# Connects to postgreSQL database. Run this script like this:
# .\scripts\connect_postgres.ps1 -DatabaseName tea_profiles     

Write-Host "Connecting to PostgreSQL..."

# Load environment variables from .env file in project root
$envPath = Join-Path $PSScriptRoot "..\.env"
if (!(Test-Path $envPath)) {
    Write-Error "Could not find .env at $envPath"
    exit 1
}

Get-Content $envPath | ForEach-Object {
    $line = $_.Trim()
    if ($line -eq "" -or $line.StartsWith("#")) { return }
    if ($line -match "^(?<key>[^=]+)=(?<value>.+)$") {
        $key = $matches['key'].Trim()
        $val = $matches['value'].Trim()

        # Strip quotes if present
        if (($val.StartsWith('"') -and $val.EndsWith('"')) -or
            ($val.StartsWith("'") -and $val.EndsWith("'"))) {
            $val = $val.Substring(1, $val.Length - 2)
        }

        Set-Item -Path "env:$key" -Value $val
    }
}

# If no database name was passed, use the one from .env
if (-not $DatabaseName -or $DatabaseName -eq "") {
    $DatabaseName = $env:DB_NAME
}

# Set PGPASSWORD so psql uses it automatically
$env:PGPASSWORD = $env:DB_PASS

# Show what we're about to use
Write-Host ("User: {0}, Host: {1}, Port: {2}, DB: {3}" -f $env:DB_USER, $env:DB_HOST, $env:DB_PORT, $DatabaseName)

# Sanity check
foreach ($name in @("DB_USER","DB_HOST","DB_PORT","DB_PASS")) {
    $val = (Get-Item "env:$name").Value
    if (-not $val -or $val -eq "") {
        Write-Error "$name is not set. Check your .env file."
        exit 1
    }
}

# Connect to Postgres
psql -U $env:DB_USER -h $env:DB_HOST -p $env:DB_PORT -d $DatabaseName

Write-Host "Connected to PostgreSQL..."