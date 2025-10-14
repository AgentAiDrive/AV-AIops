@echo off
setlocal
set "PY=C:\Users\Nutanix DS\AppData\Local\Programs\Python\Python311\python.exe"
set "DIR=C:\Users\Nutanix DS\Desktop\AV Ops Files\AV_AI_OPS\apps\av-wizard"
set "PORT=5173"

if not exist "%PY%" (
  echo Python not found at: %PY%
  echo Edit the PY= line in this .bat if needed.
  pause
  exit /b 1
)

if not exist "%DIR%\index.html" (
  echo index.html not found in: %DIR%
  pause
  exit /b 1
)

echo Launching local server on http://localhost:%PORT% ...
rem Start the Python server in a new window, serving the exact folder (spaces handled)
start "AV Wizard Server" "%PY%" -u -m http.server %PORT% -d "%DIR%"

rem Give it a moment to start
ping -n 3 127.0.0.1 >nul

rem Open the wizard directly to the first tab
start "" "http://localhost:%PORT%/index.html#/welcome"
exit /b 0
