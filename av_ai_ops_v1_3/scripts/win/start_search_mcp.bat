@echo off
setlocal
cd /d %~dp0\..\..\mcp-tools\mcp-search
if not exist node_modules npm i --silent
if not exist ".env" ( echo PORT_SEARCH=8406> .env )
node server.js
