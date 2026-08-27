@echo off
setlocal EnableExtensions

REM ============================================================
REM  code-sec-evaluator - local test runner (Windows)
REM
REM  Usage:
REM    run.bat            setup env + start backend (foreground; Ctrl+C to stop)
REM    run.bat demo       setup env + start backend + run E2E demo + stop backend
REM
REM  Deps: uv (auto-installed via pip if missing), Python >= 3.11
REM  Note: console output is English to avoid codepage (GBK/UTF-8) issues.
REM ============================================================

set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
set "BACKEND=%ROOT%\backend"
set "PORT=8000"

echo ===[1/7] Checking Python ===
set "PY=python"
where python >nul 2>&1
if errorlevel 1 (
    where py >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python not found. Install Python 3.11+ and add it to PATH, then rerun.
        pause
        exit /b 1
    )
    set "PY=py -3"
)

echo ===[2/7] Checking uv ===
where uv >nul 2>&1
if errorlevel 1 (
    echo [INFO] uv not found. Installing via pip...
    %PY% -m pip install uv
    where uv >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Failed to install uv. Install it manually:  pip install uv
        pause
        exit /b 1
    )
)

echo ===[3/7] Preparing backend\.env ===
if not exist "%BACKEND%\.env" (
    echo [INFO] Creating backend\.env with a random SECRET_KEY...
    powershell -NoProfile -Command "$key=[Convert]::ToBase64String((1..48|ForEach-Object{Get-Random -Minimum 0 -Maximum 256})); $lines=@('SECRET_KEY='+$key,'DATABASE_URL=sqlite+aiosqlite:///./data/app.db','ACCESS_TOKEN_EXPIRE_MINUTES=1440','WORKSPACE_ROOT=./workspace','REPORT_ROOT=./reports','LOG_ROOT=./runtime_logs','ISOLATION_DEFAULT_IMAGE=sec-evaluator:latest','ISOLATION_MOUNT_READONLY=true','ISOLATION_NETWORK_MODE=none','ISOLATION_FALLBACK_LOCAL=true','TASK_DEFAULT_TIMEOUT_SECONDS=1800','TASK_MAX_CONCURRENCY=2','RETENTION_DAYS=30'); Set-Content -Path '%BACKEND%\.env' -Value $lines -Encoding ascii"
)
if not exist "%BACKEND%\data" mkdir "%BACKEND%\data"

echo ===[4/7] Installing dependencies (uv sync) ===
pushd "%BACKEND%"
if not defined UV_INDEX_URL set "UV_INDEX_URL=https://pypi.org/simple"
if not exist uv.lock (
    echo [INFO] Generating uv.lock...
    uv lock
)
uv sync
if errorlevel 1 (
    echo [ERROR] uv sync failed. Check network connectivity to PyPI ^(default index: https://pypi.org/simple^) and retry.
    popd
    pause
    exit /b 1
)

echo ===[5/7] Initializing database ===
uv run python scripts/init_db.py

echo ===[6/7] Initializing admin account (admin / Admin@123456) ===
uv run python scripts/init_admin.py --username admin --password Admin@123456

if /I "%~1"=="demo" goto demo_mode

echo ===[7/7] Starting backend (foreground) ===
echo.
echo   Swagger UI : http://127.0.0.1:%PORT%/docs
echo   ReDoc      : http://127.0.0.1:%PORT%/redoc
echo   Admin      : admin / Admin@123456
echo   E2E demo   : open another terminal and run:  python scripts/demo.py
echo   Press Ctrl+C to stop.
echo.
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port %PORT%
popd
exit /b 0

:demo_mode
echo ===[7/7] Running E2E demo (start server -^> demo -^> stop server) ===
set "OUT=%ROOT%\scripts\output"
if not exist "%OUT%" mkdir "%OUT%"
set "SERVER_LOG=%OUT%\server.log"

REM kill leftover process on the port, if any
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /C:":%PORT%"') do taskkill /F /PID %%p >nul 2>&1

echo [INFO] Starting backend in background...
start "cse-server" /b cmd /c "cd /d %BACKEND% && uv run uvicorn app.main:app --host 127.0.0.1 --port %PORT% > %SERVER_LOG% 2>&1"

echo [INFO] Waiting for backend readiness...
set /a tries=0
:wait_loop
set /a tries+=1
if %tries% gtr 60 goto wait_fail
powershell -NoProfile -Command "try { (Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:%PORT%/openapi.json' -TimeoutSec 2) | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
    timeout /t 2 /nobreak >nul
    goto wait_loop
)

echo [INFO] Backend ready. Running E2E demo...
popd
%PY% "%ROOT%\scripts\demo.py"
set "DEMO_EXIT=%errorlevel%"

echo [INFO] Stopping backend server...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /C:":%PORT%"') do taskkill /F /PID %%p >nul 2>&1
echo [INFO] Demo finished (exit=%DEMO_EXIT%). Server log: %SERVER_LOG%
pause
exit /b %DEMO_EXIT%

:wait_fail
echo [ERROR] Backend did not become ready within 120s. See log: %SERVER_LOG%
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /C:":%PORT%"') do taskkill /F /PID %%p >nul 2>&1
popd
pause
exit /b 1
