@echo off
setlocal
cd /d %~dp0\..\..\mcp-tools\mcp-servicenow
if not exist node_modules npm i --silent
if not exist ".env" ( echo PORT_SNOW=8405> .env )
node server.js
