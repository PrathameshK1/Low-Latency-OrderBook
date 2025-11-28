# Build Python Bindings for Low-Latency OrderBook
# This script builds the C++ Python module (lob_py)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Building Python Bindings (lob_py)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check for Python
Write-Host "[1/4] Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonExe = (Get-Command python).Source
    $pythonVersion = python --version
    Write-Host "  Found: $pythonExe" -ForegroundColor Green
    Write-Host "  Version: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Python not found in PATH!" -ForegroundColor Red
    Write-Host "  Please install Python 3.12+ and add it to PATH" -ForegroundColor Red
    exit 1
}

# Check for CMake
Write-Host ""
Write-Host "[2/4] Checking CMake installation..." -ForegroundColor Yellow
try {
    $cmakeVersion = cmake --version | Select-Object -First 1
    Write-Host "  Found: $cmakeVersion" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: CMake not found in PATH!" -ForegroundColor Red
    Write-Host "  Please install CMake 3.20+ from: https://cmake.org/download/" -ForegroundColor Red
    Write-Host "  Or use: winget install Kitware.CMake" -ForegroundColor Yellow
    exit 1
}

# Check for C++ compiler
Write-Host ""
Write-Host "[3/4] Checking C++ compiler..." -ForegroundColor Yellow
$compilerFound = $false
$generator = ""
$mingwBinPath = $null

# Check for MinGW in PATH first
try {
    $gppCmd = Get-Command g++ -ErrorAction Stop
    $mingwBinPath = Split-Path -Parent $gppCmd.Source
    Write-Host "  Found: MinGW-w64 (g++) in PATH" -ForegroundColor Green
    $compilerFound = $true
    $generator = "MinGW Makefiles"
} catch {
    # Search for MinGW in common winget installation locations
    Write-Host "  Searching for MinGW in common locations..." -ForegroundColor Gray
    $wingetPaths = @(
        "$env:LOCALAPPDATA\Microsoft\WinGet\Packages",
        "$env:ProgramFiles"
    )
    
    foreach ($basePath in $wingetPaths) {
        if (Test-Path $basePath) {
            $gppPath = Get-ChildItem -Path $basePath -Recurse -Filter "g++.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($gppPath) {
                $mingwBinPath = $gppPath.DirectoryName
                Write-Host "  Found: MinGW-w64 at $mingwBinPath" -ForegroundColor Green
                # Add to PATH for this session
                $env:PATH = "$mingwBinPath;$env:PATH"
                $compilerFound = $true
                $generator = "MinGW Makefiles"
                break
            }
        }
    }
    
    if (-not $compilerFound) {
        # Check for MSVC
        try {
            $null = Get-Command cl -ErrorAction Stop
            Write-Host "  Found: MSVC (cl.exe)" -ForegroundColor Green
            $compilerFound = $true
            $generator = "Visual Studio 17 2022"  # Adjust version as needed
        } catch {
            Write-Host "  WARNING: No C++ compiler found!" -ForegroundColor Red
            Write-Host "  Please install MinGW-w64 or Visual Studio Build Tools" -ForegroundColor Red
            Write-Host "  MinGW: https://www.mingw-w64.org/downloads/" -ForegroundColor Yellow
            Write-Host "  Or use: winget install BrechtSanders.WinLibs.POSIX.UCRT" -ForegroundColor Yellow
            Write-Host "  After installation, you may need to restart your terminal" -ForegroundColor Yellow
            exit 1
        }
    }
}

# Build
Write-Host ""
Write-Host "[4/4] Building Python bindings..." -ForegroundColor Yellow
Write-Host "  Generator: $generator" -ForegroundColor Cyan
Write-Host "  Python: $pythonExe" -ForegroundColor Cyan
Write-Host ""

# Configure
Write-Host "  Configuring CMake..." -ForegroundColor Yellow
$configureCmd = "cmake -G `"$generator`" -B build -S . -DPython3_EXECUTABLE=`"$pythonExe`" -DBUILD_PYTHON_BINDINGS=ON"
Write-Host "  Running: $configureCmd" -ForegroundColor Gray
Invoke-Expression $configureCmd

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "  ERROR: CMake configuration failed!" -ForegroundColor Red
    Write-Host "  Check the error messages above" -ForegroundColor Red
    exit 1
}

# Build
Write-Host ""
Write-Host "  Building module..." -ForegroundColor Yellow
$buildCmd = "cmake --build build --target lob_py --config Release"
Write-Host "  Running: $buildCmd" -ForegroundColor Gray
Invoke-Expression $buildCmd

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "  ERROR: Build failed!" -ForegroundColor Red
    Write-Host "  Check the error messages above" -ForegroundColor Red
    exit 1
}

# Copy MinGW DLLs to build/python directory (Windows only)
if ($IsWindows -or $env:OS -eq "Windows_NT") {
    Write-Host ""
    Write-Host "  Copying MinGW runtime DLLs..." -ForegroundColor Yellow
    $pythonDir = "build\python"
    
    if ($mingwBinPath -and (Test-Path $mingwBinPath)) {
        $dllsToCopy = @("libgcc_s_seh-1.dll", "libstdc++-6.dll", "libwinpthread-1.dll")
        $copiedCount = 0
        
        foreach ($dll in $dllsToCopy) {
            $srcDll = Join-Path $mingwBinPath $dll
            if (Test-Path $srcDll) {
                $dstDll = Join-Path $pythonDir $dll
                Copy-Item -Path $srcDll -Destination $dstDll -Force -ErrorAction SilentlyContinue
                if (Test-Path $dstDll) {
                    $copiedCount++
                }
            }
        }
        
        if ($copiedCount -gt 0) {
            Write-Host "  Copied $copiedCount DLL(s) to $pythonDir" -ForegroundColor Green
        } else {
            Write-Host "  WARNING: Could not copy MinGW DLLs (module may still work if DLLs are in PATH)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  WARNING: MinGW bin path not found (module may still work if DLLs are in PATH)" -ForegroundColor Yellow
    }
}

# Check output
Write-Host ""
Write-Host "  Checking output..." -ForegroundColor Yellow
$modulePath = Get-ChildItem -Path "build\python" -Filter "lob_py*.pyd" -ErrorAction SilentlyContinue
if ($modulePath) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  Build Successful!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Module location: $($modulePath.FullName)" -ForegroundColor Green
    Write-Host ""
    Write-Host "  The module will be automatically found by websocket_server.py" -ForegroundColor Cyan
    Write-Host "  Restart the server to use the C++ backend!" -ForegroundColor Cyan
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "  WARNING: Module file not found in build/python/" -ForegroundColor Yellow
    Write-Host "  Check build/python/ directory for output files" -ForegroundColor Yellow
}

