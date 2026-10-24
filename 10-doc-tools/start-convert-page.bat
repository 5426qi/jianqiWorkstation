@echo off
title Convert Web Server
cd /d "%~dp0convert-web"
"%~dp0inkdoc-src\.venv\Scripts\python.exe" app.py
pause
