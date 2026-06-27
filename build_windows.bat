@echo off
REM ─────────────────────────────────────────────────────────────────────────
REM  miktag — Windows build script
REM  Run this from the project root in a terminal.
REM  Requires: Python 3.11+, pip, Inno Setup 6 (optional, for installer)
REM ─────────────────────────────────────────────────────────────────────────

echo.
echo  [1/4] Installing Python dependencies...
pip install -r requirements.txt --quiet
if errorlevel 1 ( echo ERROR: pip install failed & pause & exit /b 1 )

echo  [2/4] Building with PyInstaller...
pyinstaller miktag.spec --clean --noconfirm
if errorlevel 1 ( echo ERROR: PyInstaller failed & pause & exit /b 1 )

echo  [3/4] Build complete!  Output: dist\miktag\miktag.exe

REM ── Optional: create installer with Inno Setup ──────────────────────────
where iscc >nul 2>&1
if %errorlevel% == 0 (
    echo  [4/4] Creating installer with Inno Setup...
    mkdir installer 2>nul
    iscc miktag_installer.iss
    echo  Installer saved to: installer\miktag-setup-windows.exe
) else (
    echo  [4/4] Inno Setup not found — skipping installer creation.
    echo        Download from https://jrsoftware.org/isinfo.php
    echo        Then run:  iscc miktag_installer.iss
)

echo.
echo  Done!  You can now run:  dist\miktag\miktag.exe
pause
