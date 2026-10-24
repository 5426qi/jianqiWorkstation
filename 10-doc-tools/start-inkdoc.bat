@echo off
cd /d G:\???\10-doc-tools\inkdoc-src
call .venv\Scripts\activate.bat
python main.py --headless --port 13118
pause
