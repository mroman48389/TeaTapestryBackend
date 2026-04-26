# Restores a database into data\backups\snapshots.
# PowerShell: .\scripts\PowerShell\restore-db.ps1 -BackupFile [data/backups/snapshots/old name.dump]

param(
    [string]$DatabaseName = "tea_tapestry",
    [string]$BackupFile = ""
)

# Determine script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Build path to snapshots directory
$SnapshotDir = Join-Path $ScriptDir "../../data/backups/snapshots"

Write-Host "Looking for backups in: $SnapshotDir"

# If no backup file was provided, prompt the user with available options
if (-not $BackupFile) {
    $files = Get-ChildItem -Path $SnapshotDir -Filter *.dump | Sort-Object LastWriteTime -Descending

    if ($files.Count -eq 0) {
        Write-Error "No .dump files found in $SnapshotDir"
        exit 1
    }

    Write-Host "Available backups:"
    $i = 1
    foreach ($file in $files) {
        Write-Host "[$i] $($file.Name)"
        $i++
    }

    $selection = Read-Host "Enter the number of the backup you want to restore"
    $index = [int]$selection - 1

    if ($index -lt 0 -or $index -ge $files.Count) {
        Write-Error "Invalid selection."
        exit 1
    }

    $BackupFile = $files[$index].FullName
}

Write-Host "Restoring database '$DatabaseName' from backup:"
Write-Host "  $BackupFile"

# Ensure pg_restore is available
$pgRestore = "pg_restore"
if (-not (Get-Command $pgRestore -ErrorAction SilentlyContinue)) {
    Write-Error "pg_restore not found. Make sure PostgreSQL is installed and pg_restore is in your PATH."
    exit 1
}

# Drop and recreate the database
Write-Host "Dropping existing database (if it exists)..."
& psql -c "DROP DATABASE IF EXISTS $DatabaseName;"

Write-Host "Creating new empty database..."
& psql -c "CREATE DATABASE $DatabaseName;"

# Restore the backup
Write-Host "Restoring backup..."
& $pgRestore -d $DatabaseName $BackupFile

if ($LASTEXITCODE -eq 0) {
    Write-Host "Database restored successfully."
} 
else {
    Write-Error "Restore failed with exit code $LASTEXITCODE."
}
