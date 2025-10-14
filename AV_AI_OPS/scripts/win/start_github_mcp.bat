@echo off
setlocal
cd /d %~dp0\..\..\mcp-tools\mcp-github
if not exist node_modules npm i --silent
if not exist ".env" ( echo PORT_GITHUB=8403> .env )
node server.js
