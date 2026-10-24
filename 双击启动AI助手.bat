@echo off
chcp 936 >nul
cd /d "%~dp0"
start "" "C:\open-webui-venv\Scripts\pythonw.exe" launcher.py
exit