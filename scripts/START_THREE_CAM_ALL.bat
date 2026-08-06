@echo off
set "ROOT=%~dp0"
set "REPO=%ROOT%.."
pushd "%ROOT%"
set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not exist "%PYTHON%" set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if exist "%PYTHON%" goto run
set "PYTHON=python"
where python >nul 2>nul
if errorlevel 1 set "PYTHON=py"
:run
start "Three Cam APK Server" cmd /k ""%PYTHON%" "%REPO%\scripts\serve_three_cam_apk.py""
"%PYTHON%" "%REPO%\dashboard\three_cam_controller.py"
popd
pause
