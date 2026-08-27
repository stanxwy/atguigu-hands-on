@echo off
setlocal EnableExtensions

REM ============================================================
REM  code-sec-evaluator - frontend local test runner (Windows)
REM
REM  Usage:
REM    start-dev.bat      install deps if needed, ensure backend is
REM                       running (start it in a new window when down),
REM                       then start the Vite dev server (foreground)
REM
REM  Deps: Node.js >= 18 + npm; backend deps are handled by root run.bat
REM  Note: console output is English to avoid codepage (GBK/UTF-8) issues.
REM ============================================================

set "FRONTEND=%~dp0"
set "FRONTEND=%FRONTEND:~0,-1%"
set "ROOT=%FRONTEND%\.."
set "BACKEND_URL=http://127.0.0.1:8000"
set "FRONTEND_PORT=5173"

echo ===[1/4] Checking Node.js ===
where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found. Install Node.js 18+ and add it to PATH, then rerun.
    pause
    exit /b 1
)

echo ===[2/4] Installing frontend dependencies (if needed) ===
pushd "%FRONTEND%"
if not exist node_modules (
    call npm install
    if errorlevel 1 (
        echo [ERROR] npm install failed. Check network connectivity and retry.
        popd
        pause
        exit /b 1
    )
)

echo ===[3/4] Checking backend on %BACKEND_URL% ===
powershell -NoProfile -Command "try { (Invoke-WebRequest -UseBasicParsing -Uri '%BACKEND_URL%/openapi.json' -TimeoutSec 2) | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 goto ensure_backend
echo [INFO] Backend already running.
goto backend_ready

:ensure_backend
echo [INFO] Backend not running. Starting it in a new window via root run.bat ...
start "cse-backend" cmd /c "cd /d %ROOT% && call run.bat"
set /a tries=0

:wait_loop
set /a tries+=1
if %tries% gtr 120 goto wait_fail
powershell -NoProfile -Command "try { (Invoke-WebRequest -UseBasicParsing -Uri '%BACKEND_URL%/openapi.json' -TimeoutSec 2) | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
    timeout /t 2 /nobreak >nul
    goto wait_loop
)
echo [INFO] Backend ready.

:backend_ready
echo ===[4/4] Starting frontend dev server (foreground) ===
echo.
echo   Frontend : http://localhost:%FRONTEND_PORT%/
echo   Backend  : %BACKEND_URL%/docs
echo   Admin    : admin / Admin@123456
echo   Press Ctrl+C to stop.
echo.
call npm run dev
popd
exit /b 0

:wait_fail
echo [ERROR] Backend did not become ready within ~240s. Check the backend window output.
pause
exit /b 1
