param(
    [string]$DatabaseName
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

# Parse DATABASE_URL
if (-not $env:DATABASE_URL) {
    Write-Error "DATABASE_URL is not set in .env"
    exit 1
}

# Example: postgresql+psycopg2://user:pass@host:5432/dbname
$regex = '^postgresql\+\w+://(?<user>[^:]+):(?<pass>[^@]+)@(?<host>[^:]+):(?<port>\d+)/(?<db>.+)$'
if ($env:DATABASE_URL -notmatch $regex) {
    Write-Error "DATABASE_URL is not in a recognized format."
    exit 1
}

$user = $matches['user']
$pass = $matches['pass']
$host = $matches['host']
$port = $matches['port']
$db   = $matches['db']

# Override DB name if passed as param
if ($DatabaseName) {
    $db = $DatabaseName
}

# Set PGPASSWORD for psql
$env:PGPASSWORD = $pass

Write-Host ("User: {0}, Host: {1}, Port: {2}, DB: {3}" -f $user, $host, $port, $db)

# Connect
psql -U $user -h $host -p $port -d $db

Write-Host "Connected to PostgreSQL..."