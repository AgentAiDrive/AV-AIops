@echo off
setlocal
cd /d %~dp0\..\..\mcp-tools\mcp-gdrive
if not exist node_modules npm i --silent
if not exist ".env" ( echo PORT_GDRIVE=8404> .env )
node server.js
