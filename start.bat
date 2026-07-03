@echo off
title Med-Assist
cd /d "%~dp0"

echo ================================================
echo   Med-Assist - Medical Device AI Assistant
echo ================================================
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python not found
  pause
  exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
  echo [ERROR] npm not found
  pause
  exit /b 1
)

echo [1/2] Starting backend (port 8000)...
cd /d "%~dp0backend"
start "Med-Backend" cmd /c "cd /d %~dp0backend && python -m uvicorn main:app --port 8000 --reload"

echo [2/2] Starting frontend (port 5173)...
cd /d "%~dp0frontend"
if not exist "node_modules\" (
    echo       npm install ...
    call npm install
)

echo.
echo -----------------------------------------------
echo   Frontend : http://localhost:5173
echo   Backend  : http://localhost:8000
echo   API Docs : http://localhost:8000/docs
echo -----------------------------------------------
echo.

call npm run dev
pause
