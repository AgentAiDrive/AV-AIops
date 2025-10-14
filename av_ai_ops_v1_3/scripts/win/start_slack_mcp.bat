@echo off
setlocal
cd /d %~dp0\..\..\mcp-tools\mcp-slack
if not exist node_modules npm i --silent
if not exist ".env" ( echo PORT_SLACK=8401> .env )
node server.js
