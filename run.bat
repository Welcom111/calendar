@echo off
cd /d "%~dp0"
where python >nul 2>nul
if not errorlevel 1 (python app.py & exit /b)
where py >nul 2>nul
if not errorlevel 1 (py -3 app.py & exit /b)
echo Python 3 is not installed. Run install.bat after installing Python.
pause
