# Backs up a database into data\backups\snapshots and verifies the backup.
# PowerShell: .\scripts\PowerShell\backup_db.ps1 -DatabaseName [name] SkipFullVerify [value]

param(
    [string]$DatabaseName = "my_db",
    [switch]$SkipFullVerify
)

# Prompt for password securely (not echoed, not stored in history)
$SecurePassword = Read-Host "Enter PostgreSQL password" -AsSecureString

# Convert to plain text ONLY in memory for PGPASSWORD
$PasswordPtr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecurePassword)
$Password = [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($PasswordPtr)

# Set environment variable for all pg_* commands
$env:PGPASSWORD = $Password

Write-Host "Starting PostgreSQL backup for database '$DatabaseName'..."

# Determine script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Build path to snapshots directory
$BackupDir = Join-Path $ScriptDir "../../data/backups/snapshots"

# Ensure snapshots directory exists
if (-not (Test-Path $BackupDir)) {
    Write-Host "Creating backup directory at $BackupDir"
    New-Item -ItemType Directory -Path $BackupDir | Out-Null
}

# Timestamped filename (do NOT create file yet)
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$OutputFile = Join-Path $BackupDir "${DatabaseName}_backup_$Timestamp.dump"

Write-Host "Backup will be saved to: $OutputFile"

# Ensure pg_dump is available
$pgDump = "pg_dump"
if (-not (Get-Command $pgDump -ErrorAction SilentlyContinue)) {
    Write-Error "pg_dump not found. Make sure PostgreSQL is installed and pg_dump is in your PATH."
    exit 1
}

# Run the backup
& $pgDump -U postgres -Fc -f $OutputFile $DatabaseName

if ($LASTEXITCODE -ne 0) {
    if (Test-Path $OutputFile) {
        Remove-Item $OutputFile -Force
        Write-Host "Removed incomplete backup file: $OutputFile"
    }
    Write-Error "Backup failed with exit code $LASTEXITCODE."
    exit 1
}

Write-Host "Backup completed successfully."

# --------------------------------------
# Verification Step 1: List contents
# --------------------------------------

Write-Host "Verifying backup integrity..."

$pgRestore = "pg_restore"
if (-not (Get-Command $pgRestore -ErrorAction SilentlyContinue)) {
    Write-Error "pg_restore not found. Cannot verify backup."
    exit 1
}

# Try listing contents
$ListOutput = & $pgRestore -l $OutputFile 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Error "Backup verification failed: pg_restore could not read the file."
    exit 1
}

# Split into non-empty lines
$NonEmptyLines = $ListOutput -split "`r?`n" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }

if ($NonEmptyLines.Count -eq 0) {
    Write-Error "Backup verification failed: dump appears to contain no objects."
    exit 1
}

Write-Host "Backup structure verified (dump is readable and contains objects)."

# -------------------------------
# Full Verification (default ON)
# -------------------------------

if (-not $SkipFullVerify) {
    $TempDb = "${DatabaseName}_verify_tmp"

    Write-Host "Performing full test-restore into temporary database '$TempDb'..."

    # Drop temp DB if it exists
    & psql -U postgres -c "DROP DATABASE IF EXISTS $TempDb;" | Out-Null

    # Create temp DB
    & psql -U postgres -c "CREATE DATABASE $TempDb;" | Out-Null

    # Restore into temp DB
    & $pgRestore -U postgres -d $TempDb $OutputFile

    if ($LASTEXITCODE -ne 0) {
        Write-Error "Full verification failed: could not restore into temporary database."
        exit 1
    }

    Write-Host "Full verification succeeded. Dropping temporary database..."
    & psql -U postgres -c "DROP DATABASE $TempDb;" | Out-Null
}

# Clean up password from environment and memory
Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
[System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($PasswordPtr)

Write-Host "Backup verified and saved to: $OutputFile"
