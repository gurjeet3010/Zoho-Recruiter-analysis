@echo off
cd /d "%~dp0"
echo ======================================================
echo Starting Zoho Recruit Command Center Dashboard...
echo Open your browser at: http://localhost:8123
echo ======================================================
if exist "..\Timelogs-Dashboard-main\.venv\Scripts\python.exe" (
    "..\Timelogs-Dashboard-main\.venv\Scripts\python.exe" server.py
) else if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" server.py
) else (
    python server.py
)
pause
