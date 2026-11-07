@echo off
title BARTA AI Backend
cd /d "%~dp0backend"
set PYTHONPATH=%~dp0backend
set PYTHONIOENCODING=utf-8
call venv\Scripts\activate.bat
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause

