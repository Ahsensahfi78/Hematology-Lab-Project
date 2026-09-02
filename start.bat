@echo off
REM Start the Hematology Lab system.
REM   start.bat            -> backend + frontend (no device listener)
REM   start.bat --listener -> also start the analyzer device listener (TCP port 5000)

echo ============================================
echo  Starting Hematology Lab servers...
echo ============================================

cd /d "%~dp0"

echo.
echo [1/3] Starting FastAPI backend on http://127.0.0.1:8000 ...
start "Hematology Backend" cmd /k "cd /d %~dp0backend && ..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

echo [2/3] Starting Next.js frontend on http://localhost:3000 ...
start "Hematology Frontend" cmd /k "cd /d %~dp0frontend && npx next dev -p 3000"

if "%1"=="--listener" (
  echo [3/3] Starting device listener on %LISTENER_HOST%:%LISTENER_PORT% ...
  start "Hematology Device Listener" cmd /k "cd /d %~dp0backend && ..\.venv\Scripts\python.exe listener\listener.py"
) else (
  echo [3/3] Skipping device listener (pass --listener to enable).
)

echo.
echo Backend:      http://127.0.0.1:8000
echo Frontend:     http://localhost:3000
echo Device Listener: tcp://localhost:5000
echo.
echo Demo login: technician / lab123
echo.
echo To ingest analyzer messages, run backend/simulate_device.py (hl7 | astm).
echo.
timeout /t 5 >nul