@echo off
title Med-Assist

echo ================================================
echo   Med-Assist - Medical Device AI Assistant
echo ================================================
echo.

where python >nul 2>&1
if errorlevel 1 (echo [ERROR] Python not found && pause && exit /b 1)
where npm >nul 2>&1
if errorlevel 1 (echo [ERROR] npm not found && pause && exit /b 1)

echo [1/3] Backend (port 8000) ...
start "" cmd /c "pushd backend && python -m uvicorn main:app --port 8000 --reload"

echo [2/3] 3D Viewer (port 3001) ...
if not exist "..\iobs-unified-app\node_modules\" (
    echo       npm install ...
    pushd "..\iobs-unified-app" && call npm install && popd
)
start "" cmd /c "pushd ..\iobs-unified-app && npm run dev"

echo [3/3] Chat UI (port 5173) ...
if not exist "frontend\node_modules\" (
    echo       npm install ...
    pushd frontend && call npm install && popd
)

echo.
echo -----------------------------------------------
echo   3D Viewer : http://localhost:3001
echo   Chat UI   : http://localhost:5173
echo   Backend   : http://localhost:8000
echo -----------------------------------------------
echo.

pushd frontend && call npm run dev
pause
