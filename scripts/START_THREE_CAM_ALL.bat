@echo off
set "ROOT=%~dp0"
set "REPO=%ROOT%.."
pushd "%ROOT%"
set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if exist "%PYTHON%" goto run
set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not exist "%PYTHON%" set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if exist "%PYTHON%" goto run
set "PYTHON=python"
where python 2>nul | findstr /I /V "\\WindowsApps\\" >nul
if errorlevel 1 set "PYTHON=py"
:run
if /I "%PYTHON%"=="py" (
    where py >nul 2>nul
    if errorlevel 1 goto no_python
)
if /I "%PYTHON%"=="python" (
    for /f "delims=" %%P in ('where python 2^>nul ^| findstr /I /V "\\WindowsApps\\"') do (
        set "PYTHON=%%P"
        goto run
    )
    goto no_python
)
start "Three Cam APK Server" cmd /k ""%PYTHON%" "%REPO%\scripts\serve_three_cam_apk.py""
"%PYTHON%" "%REPO%\dashboard\three_cam_controller.py"
popd
pause
exit /b

:no_python
echo Python 3.11 was not found.
echo Install Python 3.11.9 or check PATH, then run this file again.
popd
pause
exit /b 1
