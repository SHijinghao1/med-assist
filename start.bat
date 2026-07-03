@echo off
title Med-Assist

set "ROOT=D:\compilation tool\Yiming\operating table"
set "BACKEND=%ROOT%\med-assist\backend"
set "FRONTEND=%ROOT%\med-assist\frontend"
set "VIEWER=%ROOT%\iobs-unified-app"

echo ================================================
echo   Med-Assist - Medical Device AI Assistant
echo ================================================
echo.

where python >nul 2>&1
if errorlevel 1 (echo [ERROR] Python not found && pause && exit /b 1)

where npm >nul 2>&1
if errorlevel 1 (echo [ERROR] npm not found && pause && exit /b 1)

echo [1/3] Starting backend + Agent (port 8000)...
start "Med-Backend" cmd /k "cd /d "%BACKEND%" && python -m uvicorn main:app --port 8000 --reload"

echo [2/3] Starting 3D Viewer (port 3001)...
if not exist "%VIEWER%\node_modules\" (
    echo       npm install ...
    cd /d "%VIEWER%" && call npm install
)
start "Med-3D" cmd /k "cd /d "%VIEWER%" && npm run dev"

echo [3/3] Starting Chat UI (port 5173)...
if not exist "%FRONTEND%\node_modules\" (
    echo       npm install ...
    cd /d "%FRONTEND%" && call npm install
)

echo.
echo -----------------------------------------------
echo   3D Viewer : http://localhost:3001
echo   Chat UI   : http://localhost:5173
echo   Backend   : http://localhost:8000
echo   API Docs  : http://localhost:8000/docs
echo -----------------------------------------------
echo.

cd /d "%FRONTEND%" && call npm run dev
pause
