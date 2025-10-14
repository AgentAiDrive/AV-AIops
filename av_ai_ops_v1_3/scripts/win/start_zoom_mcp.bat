@echo off
setlocal
cd /d %~dp0\..\..\mcp-tools\mcp-zoom
if not exist node_modules npm i --silent
if not exist ".env" ( echo PORT_ZOOM=8402> .env )
node server.js
