REM RFPY - Copyright (c) 2026 Olivier RENAULT - Apache-2.0
@echo off
setlocal EnableExtensions
set "RFPY_ROOT=__RFPY_ROOT__"
if "%RFPY_ROOT%"=="__RFPY_ROOT__" set "RFPY_ROOT=%~dp0.."
set "RFPY_HOME=%RFPY_ROOT%"
set "RFPY_CORE_PY=%RFPY_ROOT%\.appvenv\Scripts\python.exe"
set "RFPY_CORE=%RFPY_ROOT%\app\rfpy.py"
if not exist "%RFPY_CORE_PY%" (echo [ERREUR] Runtime RFPY introuvable.& exit /b 2)
endlocal & set "RFPY_HOME=%RFPY_ROOT%" & "%RFPY_CORE_PY%" "%RFPY_CORE%" web %*
exit /b %ERRORLEVEL%
