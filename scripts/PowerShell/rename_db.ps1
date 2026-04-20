# PowerShell: .\scripts\rename-db.ps1 -OldName "[old name]" -NewName "[new name]"
# OR .\scripts\rename-db.ps1 -OldName (Read-Host "Old DB name") -NewName (Read-Host "New DB name")

param (
    [string]$OldName = "teaprofiles",
    [string]$NewName = "tea_profiles",
    [string]$User = "postgres",
    [string]$Host = "localhost"
)

Write-Host "Connecting to '$Host' as user '$User' to rename database '$OldName' to '$NewName'..."

# Check if old database exists
$checkOld = psql -U $User -h $Host -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$OldName';"
if (-not $checkOld) {
    Write-Host "Database '$OldName' does not exist. Nothing to rename."
    exit 1
}

# Check if new database name already exists
$checkNew = psql -U $User -h $Host -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$NewName';"
if ($checkNew) {
    Write-Host "Database '$NewName' already exists. Rename aborted to avoid conflict."
    exit 1
}

# Attempt the rename
$renameResult = psql -U $User -h $Host -d postgres -c "ALTER DATABASE $OldName RENAME TO $NewName;"

if ($LASTEXITCODE -eq 0) {
    Write-Host "Successfully renamed '$OldName' → '$NewName'"
} else {
    Write-Host "Rename failed. Are you connected to '$OldName'? Disconnect and try again."
}

# Manual equivalent: 
# To rename a database,
#
# 1. Open a new PowerShell terminal. If venv is activated, do 
#
# 	     deactivate 
#	
#    first to deactivate it.
#
# 2. Connect to the default postgres database to establish a 
#    different connection to a database you are NOT renaming.
#
# 	     psql -U [username] -h localhost -d postgres
#	
# 3. When you see postgres=# after entering your password, do
#
# 	     SELECT current_database();
#	
#    It should list postgres as the database.
#
# 4. Rename the database you want to rename by doing; 
#
# 	     ALTER DATABASE [old name] RENAME TO [new name]; 
#	
#    If you see ALTER DATABASE, then it worked. Type \l for extra confirmation, then \q to quit.
#
# 5. Reactivate your venv and run the backend.