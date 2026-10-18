REM RFPY - Copyright (c) 2026 Olivier RENAULT - Apache-2.0
@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "RFPY_ROOT=__RFPY_ROOT__"
if "%RFPY_ROOT%"=="__RFPY_ROOT__" set "RFPY_ROOT=%~dp0.."
set "RFPY_HOME=%RFPY_ROOT%"
set "RFPY_BIN=%RFPY_ROOT%\bin"
set "RFPY_CORE_PY=%RFPY_ROOT%\.appvenv\Scripts\python.exe"
set "RFPY_CORE=%RFPY_ROOT%\app\rfpy.py"
set "RFPY_PS=%RFPY_BIN%\rfpy.ps1"
if not exist "%RFPY_CORE_PY%" (echo [RFPY ERROR] Runtime not found.& exit /b 2)

if "%~1"=="" goto :quick
if /I "%~1"=="-m" goto :menu
if /I "%~1"=="--menu" goto :menu
if /I "%~1"=="menu" goto :menu
if /I "%~1"=="on" goto :activate_arg
if /I "%~1"=="activate" goto :activate_arg
if /I "%~1"=="off" goto :deactivate
if /I "%~1"=="deactivate" goto :deactivate
if /I "%~1"=="language" goto :language
if /I "%~1"=="lang" goto :language
endlocal & set "RFPY_HOME=%RFPY_ROOT%" & "%RFPY_CORE_PY%" "%RFPY_CORE%" %*
exit /b %ERRORLEVEL%

:language
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%RFPY_PS%" language
endlocal & exit /b %ERRORLEVEL%

:quick
call :pick_env quick
if defined RFPY_PICK_FAILED (endlocal&exit /b 2)
if "%RFPY_SELECTED%"=="__NO_ENVS__" goto :first_run
if not defined RFPY_SELECTED (endlocal&exit /b 0)
goto :activate_selected

:menu
call :pick_env menu
if defined RFPY_PICK_FAILED (endlocal&exit /b 2)
if "%RFPY_SELECTED%"=="__NO_ENVS__" goto :first_run
if not defined RFPY_SELECTED (endlocal&exit /b 0)
goto :activate_selected

:pick_env
set "RFPY_SELECTED="
set "RFPY_PICK_FAILED="
set "RFPY_PICK_TMP=%TEMP%\rfpy-pick-%RANDOM%-%RANDOM%.txt"
if /I "%~1"=="menu" (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%RFPY_PS%" cmd-menu "!RFPY_PICK_TMP!"
) else (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%RFPY_PS%" cmd-pick "!RFPY_PICK_TMP!"
)
set "RFPY_PICK_RC=!ERRORLEVEL!"
if not "!RFPY_PICK_RC!"=="0" (
  if exist "!RFPY_PICK_TMP!" del /q "!RFPY_PICK_TMP!" >nul 2>&1
  set "RFPY_PICK_FAILED=1"
  exit /b !RFPY_PICK_RC!
)
if exist "!RFPY_PICK_TMP!" set /p "RFPY_SELECTED="<"!RFPY_PICK_TMP!"
if exist "!RFPY_PICK_TMP!" del /q "!RFPY_PICK_TMP!" >nul 2>&1
exit /b 0

:first_run
endlocal & set "RFPY_HOME=%RFPY_ROOT%" & "%RFPY_CORE_PY%" "%RFPY_CORE%" web
exit /b %ERRORLEVEL%

:activate_arg
if "%~2"=="" (echo [RFPY ERROR] Missing environment name.&endlocal&exit /b 2)
set "RFPY_SELECTED=%~2"

:activate_selected
set "RFPY_META_TMP=%TEMP%\rfpy-meta-%RANDOM%-%RANDOM%.txt"
"%RFPY_CORE_PY%" "%RFPY_CORE%" env-shell-tsv "%RFPY_SELECTED%" >"!RFPY_META_TMP!" 2>&1
set "RFPY_META_RC=!ERRORLEVEL!"
if not "!RFPY_META_RC!"=="0" (
  type "!RFPY_META_TMP!"
  del /q "!RFPY_META_TMP!" >nul 2>&1
  endlocal&exit /b !RFPY_META_RC!
)
set /p "RFPY_META="<"!RFPY_META_TMP!"
del /q "!RFPY_META_TMP!" >nul 2>&1
for /f "tokens=1-3 delims=|" %%A in ("!RFPY_META!") do (
  set "NEW_VENV=%%A"
  set "NEW_TYPE=%%B"
  set "NEW_PROJECT=%%C"
)
if not exist "!NEW_VENV!\Scripts\python.exe" (echo [RFPY ERROR] Incomplete venv.&endlocal&exit /b 2)
if not defined RFPY_ORIGINAL_PATH set "RFPY_ORIGINAL_PATH=%PATH%"
if not defined RFPY_PROMPT_SAVED (
  set "RFPY_PROMPT_SAVED=1"
  if defined PROMPT (set "RFPY_ORIGINAL_PROMPT=%PROMPT%") else set "RFPY_ORIGINAL_PROMPT=$P$G"
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%RFPY_PS%" cmd-activated "!RFPY_SELECTED!" "!NEW_TYPE!"
REM Compatibility regression marker: cmd-activated "%RFPY_ENV%" "%RFPY_ENV_TYPE%"
if errorlevel 1 (endlocal&exit /b 2)
endlocal & (
  set "RFPY_HOME=%RFPY_ROOT%"
  set "RFPY_ORIGINAL_PATH=%RFPY_ORIGINAL_PATH%"
  set "RFPY_PROMPT_SAVED=%RFPY_PROMPT_SAVED%"
  set "RFPY_ORIGINAL_PROMPT=%RFPY_ORIGINAL_PROMPT%"
  set "RFPY_ENV=%RFPY_SELECTED%"
  set "RFPY_VENV=%NEW_VENV%"
  set "VIRTUAL_ENV=%NEW_VENV%"
  set "RFPY_ENV_TYPE=%NEW_TYPE%"
  set "RFPY_PROJECT=%NEW_PROJECT%"
  set "PATH=%RFPY_BIN%;%NEW_VENV%\Scripts;%RFPY_ORIGINAL_PATH%"
  if /I "%NEW_TYPE%"=="project" (set "UV_PROJECT=%NEW_PROJECT%") else set "UV_PROJECT="
  set "PROMPT=[RFPY - %RFPY_SELECTED%] %RFPY_ORIGINAL_PROMPT%"
)
exit /b 0

:deactivate
if not defined RFPY_ENV (endlocal&exit /b 0)
endlocal & (
  if defined RFPY_ORIGINAL_PATH set "PATH=%RFPY_ORIGINAL_PATH%"
  set "VIRTUAL_ENV="
  set "UV_PROJECT="
  set "RFPY_ENV="
  set "RFPY_VENV="
  set "RFPY_ENV_TYPE="
  set "RFPY_PROJECT="
  if defined RFPY_PROMPT_SAVED set "PROMPT=%RFPY_ORIGINAL_PROMPT%"
  set "RFPY_ORIGINAL_PATH="
  set "RFPY_PROMPT_SAVED="
  set "RFPY_ORIGINAL_PROMPT="
  set "RFPY_HOME=%RFPY_ROOT%"
)
exit /b 0
