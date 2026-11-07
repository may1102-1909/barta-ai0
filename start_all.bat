@echo off
echo Starting BARTA AI Servers...
start "BARTA AI Backend" /min cmd.exe /c "%~dp0run_backend.bat"
start "BARTA AI Frontend" /min cmd.exe /c "%~dp0run_frontend.bat"
echo Both servers have been launched in background.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000

