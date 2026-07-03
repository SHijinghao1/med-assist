@echo off
title Med-Assist - 智能医疗设备运维助手
cd /d "%~dp0"

echo ================================================
echo   Med-Assist - 智能医疗设备运维助手
echo   手术床 / C臂 故障诊断 · 维修指导 · 备件查询
echo ================================================
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python not found. Please install Python 3.11+.
  pause
  exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
  echo [ERROR] npm not found. Please install Node.js.
  pause
  exit /b 1
)

echo [1/3] Installing backend dependencies...
cd /d "%~dp0backend"
if not exist "node_modules\" (
  echo       pip install -r requirements.txt ...
  pip install -r requirements.txt -q
  if errorlevel 1 (
    echo [ERROR] Backend dependency install failed.
    pause
    exit /b 1
  )
) else (
  echo       Backend dependencies found, skipping.
)

echo.
echo [2/3] Installing frontend dependencies...
cd /d "%~dp0frontend"
if not exist "node_modules\" (
  echo       npm install ...
  call npm install
  if errorlevel 1 (
    echo [ERROR] Frontend dependency install failed.
    pause
    exit /b 1
  )
) else (
  echo       Frontend dependencies found, skipping.
)

echo.
echo [3/3] Starting services...
echo -----------------------------------------------
echo   Frontend : http://localhost:5173
echo   Backend  : http://localhost:8000
echo   API Docs : http://localhost:8000/docs
echo   Health   : http://localhost:8000/health
echo -----------------------------------------------
echo.

echo Starting backend (port 8000)...
cd /d "%~dp0backend"
start "Med-Backend" cmd /k "cd /d %~dp0backend && python -m uvicorn main:app --port 8000 --reload"

timeout /t 4 /nobreak >nul

echo Starting frontend (port 5173)...
cd /d "%~dp0frontend"
call npm run dev

echo.
echo Frontend stopped. Press any key to close...
pause
exit /b 0
