@echo off
echo Starting ARGUS Headless Mode...

:: Navigate to the project directory
cd /d "%~dp0"

:: Run headless mode using the virtual environment if it exists
if exist "venv\Scripts\python.exe" (
    echo Virtual environment found. Launching headless mode...
    venv\Scripts\python.exe main_headless.py
) else (
    echo No virtual environment found. Running with global Python...
    python main_headless.py
)

pause
