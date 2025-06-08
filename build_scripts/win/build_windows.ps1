<#
.SYNOPSIS
    Comprehensive build script for GestureSesh on Windows.

.DESCRIPTION
    This PowerShell script:
      1. Optionally creates and activates a Python virtual environment.
      2. Installs Python dependencies from requirements.txt (if it exists).
      3. Cleans previous build artifacts: build/, dist/, __pycache__, spec files, and logs.
      4. Runs PyInstaller with --clean to build GestureSesh.
      5. Performs error handling: any failure in the process aborts the script and returns a nonzero exit code.

.NOTES
    - This script is intended to run on Windows PowerShell (version 5.1 or later).
    - To run with a virtual environment, pass the –UseVirtualEnv switch:
          .\build_gesture_sesh.ps1 -UseVirtualEnv
    - If you do not need a virtual environment, omit the switch.
    - Place this script in the root directory of your GestureSesh project, alongside GestureSesh_Win.spec.

.EXAMPLE
    # Run with virtual environment creation/activation:
    PS C:\Projects\GestureSesh> .\build_gesture_sesh.ps1 -UseVirtualEnv

    # Run without virtual environment:
    PS C:\Projects\GestureSesh> .\build_gesture_sesh.ps1
#>

# Always use the venv unless --NoVirtualEnv is passed
param(
    [switch]$NoVirtualEnv
)

# ------------------------------------------------------------
# Set strict error handling so that any command failure stops execution
# ------------------------------------------------------------
$ErrorActionPreference = 'Stop'

# ------------------------------------------------------------
# Display header
# ------------------------------------------------------------
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "       Building GestureSesh for Windows      " -ForegroundColor Cyan
Write-Host "=============================================`n" -ForegroundColor Cyan

try {
    # --------------------------------------------------------
    # 1. Create and/or activate a virtual environment unless --NoVirtualEnv is set
    # --------------------------------------------------------
    if (-not $NoVirtualEnv) {
        if (-not (Test-Path -LiteralPath ".\venv")) {
            Write-Host "[1/5] Creating Python virtual environment in '.\venv'..." -ForegroundColor Yellow
            python -m venv venv
        }
        Write-Host "[1/5] Activating virtual environment..." -ForegroundColor Yellow
        $activateScript = ".\venv\Scripts\Activate.ps1"
        if (Test-Path $activateScript) {
            # Relaunch the script inside the venv and exit the parent
            Write-Host "[1/5] Relaunching script inside the virtual environment..." -ForegroundColor Yellow
            & powershell -NoProfile -ExecutionPolicy Bypass -File $MyInvocation.MyCommand.Path @($args) -NoVirtualEnv
            exit $LASTEXITCODE
        } else {
            throw "Could not find venv activation script at $activateScript."
        }
    }
    $pythonExe = "python"
    $pipExe = "pip"
    if ($NoVirtualEnv) {
        Write-Host "[1/5] Skipping virtual environment creation/activation." -ForegroundColor Gray
    }

    # --------------------------------------------------------
    # 2. Install Python dependencies (if requirements.txt exists)
    # --------------------------------------------------------
    if (Test-Path -LiteralPath ".\requirements.txt") {
        Write-Host "[2/5] Installing Python dependencies from 'requirements.txt'..." -ForegroundColor Yellow
        & $pythonExe -m pip install --upgrade pip
        & $pipExe install -r .\requirements.txt
        Write-Host "[2/5] Dependencies installed.`n" -ForegroundColor Green
    } else {
        Write-Host "[2/5] No 'requirements.txt' found. Skipping dependency installation." -ForegroundColor Gray
    }

    # --------------------------------------------------------
    # 3. Clean previous build artifacts
    # --------------------------------------------------------
    Write-Host "[3/5] Cleaning previous build artifacts..." -ForegroundColor Yellow

    # Remove build/ directory
    if (Test-Path -LiteralPath ".\build") {
        Remove-Item -Recurse -Force .\build
        Write-Host "      -> Removed 'build' directory." -ForegroundColor Gray
    }

    # Remove dist/ directory
    if (Test-Path -LiteralPath ".\dist") {
        Remove-Item -Recurse -Force .\dist
        Write-Host "      -> Removed 'dist' directory." -ForegroundColor Gray
    }

    # Remove __pycache__ directories recursively
    $pycacheDirs = Get-ChildItem -Path . -Filter "__pycache__" -Recurse -Directory -ErrorAction SilentlyContinue
    foreach ($dir in $pycacheDirs) {
        Remove-Item -Recurse -Force $dir.FullName
        Write-Host "      -> Removed '$($dir.FullName)'." -ForegroundColor Gray
    }

    # Remove any .log files in the project root and subdirectories
    $logFiles = Get-ChildItem -Path . -Include *.log -Recurse -File -ErrorAction SilentlyContinue
    foreach ($file in $logFiles) {
        Remove-Item -Force $file.FullName
        Write-Host "      -> Deleted log file: '$($file.FullName)'." -ForegroundColor Gray
    }

    Write-Host "[3/5] Clean complete.`n" -ForegroundColor Green

    # --------------------------------------------------------
    # 4. Run PyInstaller with --clean and handle errors
    # --------------------------------------------------------
    Write-Host "[4/5] Running PyInstaller (with --clean)..." -ForegroundColor Yellow

    # Ensure GestureSesh_Win.spec exists in the working directory. If you have only a spec for Windows, rename accordingly.
    if (-not (Test-Path -LiteralPath ".\GestureSesh_Win.spec")) {
        throw "Cannot find 'GestureSesh_Win.spec' in the current directory. Aborting build."
    }

    # Build command: adjust spec name or options here if needed
    $pyInstallerArgs = @(
        "GestureSesh_Win.spec"
        "--noconfirm"
    )

    # Use venv Python to run PyInstaller if venv is used
    if ($UseVirtualEnv) {
        & $pythonExe -m PyInstaller @($pyInstallerArgs)
    } else {
        & pyinstaller @($pyInstallerArgs)
    }

    # Check PyInstaller’s exit code
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE."
    }

    Write-Host "[4/5] PyInstaller completed successfully.`n" -ForegroundColor Green

    # --------------------------------------------------------
    # 5. Run Windows smoke test
    # --------------------------------------------------------
    Write-Host "[5/5] Running Windows smoke test..." -ForegroundColor Yellow
    $testScript = Join-Path $PSScriptRoot "..\..\tests\test_windows_build.ps1"
    if (Test-Path $testScript) {
        Write-Host "Running: $testScript" -ForegroundColor Gray
        & powershell -NoProfile -ExecutionPolicy Bypass -File $testScript
        if ($LASTEXITCODE -ne 0) {
            throw "Smoke test failed with exit code $LASTEXITCODE."
        }
    } else {
        Write-Host "Smoke test script not found: $testScript" -ForegroundColor Red
    }

    # --------------------------------------------------------
    # 6. Final Success Message
    # --------------------------------------------------------
    Write-Host "[6/6] Build process finished without errors!" -ForegroundColor Cyan
    Write-Host "       The generated executables and supporting files are located in '.\dist\GestureSesh'." -ForegroundColor Cyan
    Write-Host "       You can now sign, package, or distribute as needed.`n" -ForegroundColor Cyan

    # Optionally, pause so the console remains open if run by double-click
    if ($Host.Name -eq "ConsoleHost") {
        Write-Host "Press any key to exit..." -NoNewline
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    }

} catch {
    # --------------------------------------------------------
    # ERROR HANDLING: catch any exception, display it, and exit with code 1
    # --------------------------------------------------------
    Write-Host "`n==================================================" -ForegroundColor Red
    Write-Host "ERROR: Build failed." -ForegroundColor Red
    Write-Host "Details: $_" -ForegroundColor Red
    Write-Host "==================================================`n" -ForegroundColor Red
    exit 1
}
