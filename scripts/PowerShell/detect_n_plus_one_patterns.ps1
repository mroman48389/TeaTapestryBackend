# Detect N+1 SQL Query Patterns


Write-Host "=== Tea Tapestry N+1 Detector ==="

# 1. Compute project root (two levels up from this script)
$projectRoot = Resolve-Path "$PSScriptRoot\..\.."

# 2. Path to backend log
$logPath = Join-Path $projectRoot "logs\backend.log"

Write-Host "Project root: $projectRoot"
Write-Host "Log path:     $logPath"

# 3. Clear old logs
if (Test-Path $logPath) {
    Clear-Content $logPath
    Write-Host "Cleared existing backend.log."
} 
else {
    Write-Host "backend.log does not exist yet; it will be created automatically."
}

# 4. Trigger the request
$endpoint = "http://127.0.0.1:8000/api/v1/tea_profiles?limit=50"
Write-Host "Sending request to $endpoint ..."
Invoke-WebRequest $endpoint -UseBasicParsing | Out-Null

# 5. Read logs
Start-Sleep -Milliseconds 200  # tiny delay to ensure logs flush
$log = Get-Content $logPath

# 6. Extract SQL SELECT statements
$selects = $log | Select-String -Pattern "SELECT" | ForEach-Object { $_.Line }

Write-Host ""
Write-Host "Total SELECT statements found: $($selects.Count)"

# 7. Group identical queries
$grouped = $selects | Group-Object

Write-Host ""
Write-Host "Repeated SELECT patterns:"
$repeats = $grouped | Where-Object { $_.Count -gt 1 }

if ($repeats.Count -eq 0) {
    Write-Host "No repeated SELECT patterns detected"
} 
else {
    foreach ($g in $repeats) {
        Write-Host "Count: $($g.Count)  Query: $($g.Name)"
    }
}

Write-Host ""
# 8. Final N+1 verdict
if ($repeats | Where-Object { $_.Count -gt 5 }) {
    Write-Host "Possible N+1 query pattern detected!"
} 
else {
    Write-Host "No N+1 issues detected"
}

Write-Host ""
Write-Host "=== Done ==="
