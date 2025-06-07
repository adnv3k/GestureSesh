# tests/test_windows_build.ps1
# PowerShell script to test the Windows build of GestureSesh

$ErrorActionPreference = 'Stop'

Write-Host "=== Testing GestureSesh Windows Build ===" -ForegroundColor Cyan

# 1. Check that the EXE exists
$exePath = ".\dist\GestureSesh\GestureSesh.exe"
if (-not (Test-Path $exePath)) {
    Write-Host "ERROR: GestureSesh.exe not found in dist/GestureSesh!" -ForegroundColor Red
    exit 1
}
Write-Host "[PASS] EXE exists: $exePath" -ForegroundColor Green

# 2. Check that the EXE is not zero bytes
$exeInfo = Get-Item $exePath
if ($exeInfo.Length -eq 0) {
    Write-Host "ERROR: GestureSesh.exe is zero bytes!" -ForegroundColor Red
    exit 1
}
Write-Host "[PASS] EXE is not empty." -ForegroundColor Green

# 3. Run the EXE with --help or /? and check for a window or output (headless test)
# (PyQt apps may not support --help, so just try to start and kill after a short time)
Write-Host "[INFO] Launching GestureSesh.exe for a smoke test..." -ForegroundColor Yellow
$proc = Start-Process -FilePath $exePath -PassThru
Start-Sleep -Seconds 5
if ($proc.HasExited) {
    Write-Host "ERROR: GestureSesh.exe exited immediately (crash?)" -ForegroundColor Red
    exit 1
}
Stop-Process -Id $proc.Id -Force
Start-Sleep -Milliseconds 500
# Ensure the process is closed after testing
try {
    $p = Get-Process -Id $proc.Id -ErrorAction SilentlyContinue
    $retries = 0
    while ($p -and $retries -lt 5) {
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 500
        $p = Get-Process -Id $proc.Id -ErrorAction SilentlyContinue
        $retries++
    }
    if ($p) {
        Write-Host "[WARN] Main process still running, killing all GestureSesh.exe with taskkill..." -ForegroundColor Yellow
        taskkill /F /IM GestureSesh.exe /T | Out-Null
    }
    Write-Host "[INFO] GestureSesh.exe closed after testing." -ForegroundColor Gray
} catch {
    Write-Host "[INFO] GestureSesh.exe already closed." -ForegroundColor Gray
}

Write-Host "=== All Windows build tests passed! ===" -ForegroundColor Cyan
