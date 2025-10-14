\
@echo off
setlocal enabledelayedexpansion
call :start mcp-slack PORT_SLACK 8401
call :start mcp-zoom PORT_ZOOM 8402
call :start mcp-github PORT_GITHUB 8403
call :start mcp-gdrive PORT_GDRIVE 8404
call :start mcp-servicenow PORT_SNOW 8405
call :start mcp-search PORT_SEARCH 8406
echo All MCP servers launched (mock). Press any key to exit window.
pause >nul
exit /b 0

:start
set NAME=%1
set ENVVAR=%2
set DEFPORT=%3
pushd "%~dp0\..\..\mcp-tools\%NAME%"
if not exist node_modules (
  echo Installing deps for %NAME%...
  npm i --silent
)
if not exist ".env" (
  echo %ENVVAR%=%DEFPORT%> .env
)
start "MCP %NAME%" cmd /c "set %ENVVAR%=%DEFPORT% && node server.js"
popd
exit /b 0
