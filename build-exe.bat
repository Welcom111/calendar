@echo off
cd /d "%~dp0"
where python >nul 2>nul
if not errorlevel 1 (set "PY=python" & goto build)
where py >nul 2>nul
if not errorlevel 1 (set "PY=py -3" & goto build)
echo Python 3 is required on the build computer.
pause
exit /b 1
:build
%PY% -m pip install -r requirements-build.txt
if errorlevel 1 goto failed
%PY% -m PyInstaller app.py --name QuickCalendar --onefile --windowed --clean --noconfirm --collect-submodules keyring.backends --collect-submodules caldav
if errorlevel 1 goto failed
echo Built: dist\QuickCalendar.exe
pause
exit /b 0
:failed
echo Build failed.
pause
exit /b 1
