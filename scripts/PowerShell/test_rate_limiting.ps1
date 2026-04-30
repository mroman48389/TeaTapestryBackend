# =============================================================================
#
# Starts the backend with DEV_RATE_LIMIT = true, tests all per-route rate limits,
# then stops the server. Run from the project root with no other server running:
#
#   scripts\PowerShell\test_rate_limiting.ps1 -TeaId 24
#
# Parameters:
#   -TeaId   : A valid tea profile ID for the /{id} endpoint (default: 24)
# =============================================================================

param(
    [int]$TeaId = 24
)

$BaseUrl = "http://127.0.0.1:8000"
$passed  = 0
$failed  = 0

# ---------------------------------------------------------------------------
# Ensure that the venv is active. Exit if not.
# ---------------------------------------------------------------------------

if (-not $env:VIRTUAL_ENV) {
    Write-Host ""
    Write-Host "Virtual environment is not active. Please run:" -ForegroundColor Red
    Write-Host "  scripts\PowerShell\activate_venv.ps1" -ForegroundColor Yellow
    Write-Host "Then re-run this script." -ForegroundColor Red
    Write-Host ""
    exit 1
}

# ---------------------------------------------------------------------------
# Also ensure that nothing is already on port 8000.
# ---------------------------------------------------------------------------

try {
    Invoke-WebRequest -Uri "$BaseUrl/" -UseBasicParsing -ErrorAction Stop | Out-Null
    Write-Host ""
    Write-Host "A server is already running on port 8000. Stop it first, then re-run this script." -ForegroundColor Red
    Write-Host ""
    exit 1
} catch {}

# ---------------------------------------------------------------------------
# Start server
# ---------------------------------------------------------------------------

Write-Host ""
Write-Host "Starting server with DEV_RATE_LIMIT=true..." -ForegroundColor Cyan

# Switch to lower rate limits for the test so we don't need to wait forever.
$env:DEV_RATE_LIMIT = "true"

$serverProcess = Start-Process -FilePath "python" `
    -ArgumentList "-m", "uvicorn", "src.app.main:app", "--port", "8000" `
    -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput "server_stdout.log" `
    -RedirectStandardError "server_stderr.log"

# Wait for server to be ready (up to 15 seconds)
$ready = $false
for ($i = 0; $i -lt 15; $i++) {
    Start-Sleep -Seconds 1

    try {
        Invoke-WebRequest -Uri "$BaseUrl/" -UseBasicParsing -ErrorAction Stop | Out-Null
        $ready = $true
        break
    } 
    catch {

    }
}

if (-not $ready) {
    Write-Host "Server did not start in time. Exiting." -ForegroundColor Red
    Stop-Process -Id $serverProcess.Id -Force -ErrorAction SilentlyContinue
    exit 1
}

Write-Host "Server ready." -ForegroundColor Green

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function Invoke-Burst {
    param([string]$Url, [int]$Count)

    $codes = @()

    for ($i = 1; $i -le $Count; $i++) {
        try {
            $r = Invoke-WebRequest -Uri $Url -Method GET -UseBasicParsing -ErrorAction Stop
            $codes += [int]$r.StatusCode
        } 
        catch {
            $s = $_.Exception.Response.StatusCode.value__
            $codes += if ($null -eq $s) { 0 } else { [int]$s }
        }
    }

    return $codes
}

function Test-Limit {
    param([string]$Label, [string]$Url, [int]$Limit)

    Write-Host ""
    Write-Host "Testing $Label ($Limit/min)..." -NoNewline

    $codes = Invoke-Burst -Url $Url -Count ($Limit + 5)
    $hits  = ($codes | Where-Object { $_ -eq 429 }).Count
    $oks   = ($codes | Where-Object { $_ -eq 200 }).Count

    if ($hits -gt 0 -and $oks -gt 0) {
        Write-Host " PASS" -ForegroundColor Green
        Write-Host "  $oks x 200, $hits x 429 (limit tripped correctly)"
        $script:passed++

    } elseif ($hits -eq 0) {
        Write-Host " FAIL" -ForegroundColor Red
        Write-Host "  No 429s after $($Limit + 5) requests - limit not tripping"
        $script:failed++

    } 
    else {
        Write-Host " FAIL" -ForegroundColor Red
        Write-Host "  All requests rejected ($hits x 429, $oks x 200)"
        $script:failed++
    }

    Write-Host "  Waiting 65s for bucket refill..." -ForegroundColor DarkGray
    Start-Sleep -Seconds 65
}

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

Write-Host ""
Write-Host "--- Rate Limit Tests (TeaId: $TeaId) ---" -ForegroundColor Cyan

Test-Limit -Label "LOW  (GET /api/v1/tea_profiles/)"          -Url "$BaseUrl/api/v1/tea_profiles/"       -Limit 5
Test-Limit -Label "HIGH (GET /)"                              -Url "$BaseUrl/"                           -Limit 20
Test-Limit -Label "HIGH (GET /api/v1/tea_profiles/$TeaId)"    -Url "$BaseUrl/api/v1/tea_profiles/$TeaId" -Limit 20

# ---------------------------------------------------------------------------
# Stop server
# ---------------------------------------------------------------------------

Write-Host ""
Write-Host "Stopping server..." -ForegroundColor Cyan
Stop-Process -Id $serverProcess.Id -Force -ErrorAction SilentlyContinue
$env:DEV_RATE_LIMIT = "false"
Remove-Item "server_stdout.log" -ErrorAction SilentlyContinue
Remove-Item "server_stderr.log" -ErrorAction SilentlyContinue

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

$total = $passed + $failed
$color = if ($failed -eq 0) { "Green" } else { "Red" }
Write-Host ""
Write-Host "--- Results: $passed/$total passed ---" -ForegroundColor $color
Write-Host ""