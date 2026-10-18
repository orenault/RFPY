REM RFPY - Copyright (c) 2026 Olivier RENAULT - Apache-2.0
@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "RFPY_ROOT=__RFPY_ROOT__"
if "%RFPY_ROOT%"=="__RFPY_ROOT__" set "RFPY_ROOT=%~dp0.."
set "RFPY_HOME=%RFPY_ROOT%"
set "RFPY_BIN=%RFPY_ROOT%\bin"
set "RFPY_CORE_PY=%RFPY_ROOT%\.appvenv\Scripts\python.exe"
set "RFPY_CORE=%RFPY_ROOT%\app\rfpy.py"
if not exist "%RFPY_CORE_PY%" (echo [ERREUR] Runtime RFPY introuvable.& exit /b 2)

if "%~1"=="" goto :quick
if /I "%~1"=="-m" goto :menu
if /I "%~1"=="--menu" goto :menu
if /I "%~1"=="menu" goto :menu
if /I "%~1"=="on" goto :activate_arg
if /I "%~1"=="activate" goto :activate_arg
if /I "%~1"=="off" goto :deactivate
if /I "%~1"=="deactivate" goto :deactivate
endlocal & set "RFPY_HOME=%RFPY_ROOT%" & "%RFPY_CORE_PY%" "%RFPY_CORE%" %*
exit /b %ERRORLEVEL%

:quick
call :choose_env
if defined RFPY_NO_ENVS goto :first_run
if not defined RFPY_SELECTED (endlocal&exit /b 0)
goto :activate_selected

:first_run
echo [RFPY] Aucun environnement. Ouverture de la console Web...
endlocal & set "RFPY_HOME=%RFPY_ROOT%" & "%RFPY_CORE_PY%" "%RFPY_CORE%" web
exit /b %ERRORLEVEL%

:menu
call :choose_env
if defined RFPY_NO_ENVS goto :first_run
if not defined RFPY_SELECTED (endlocal&exit /b 0)
echo.&echo 1. Activer&echo 2. Renommer&echo 3. Supprimer&echo 4. Retour
set /p "RFPY_CHOICE=Action [1-4] : "
if "%RFPY_CHOICE%"=="1" goto :activate_selected
if "%RFPY_CHOICE%"=="2" (
  set /p "RFPY_NEW=Nom : "
  if defined RFPY_NEW "%RFPY_CORE_PY%" "%RFPY_CORE%" rename "%RFPY_SELECTED%" "!RFPY_NEW!"
  goto :menu
)
if "%RFPY_CHOICE%"=="3" (
  "%RFPY_CORE_PY%" "%RFPY_CORE%" delete "%RFPY_SELECTED%"
  goto :menu
)
goto :menu

:choose_env
set "RFPY_SELECTED="
set "RFPY_NO_ENVS="
set /a RFPY_COUNT=0
for /f "usebackq delims=" %%E in (`"%RFPY_CORE_PY%" "%RFPY_CORE%" env-names`) do (
  set /a RFPY_COUNT+=1
  set "RFPY_ITEM_!RFPY_COUNT!=%%E"
)
if !RFPY_COUNT! EQU 0 (set "RFPY_NO_ENVS=1"&exit /b 0)
echo ============================================================
echo  RFPY - Selection / activation
echo ============================================================
for /L %%N in (1,1,!RFPY_COUNT!) do call echo   %%N. %%RFPY_ITEM_%%N%%
set /p "RFPY_PICK=Numero (vide=annuler) : "
if not defined RFPY_PICK exit /b 0
for /f "delims=0123456789" %%X in ("%RFPY_PICK%") do exit /b 0
if %RFPY_PICK% LSS 1 exit /b 0
if %RFPY_PICK% GTR !RFPY_COUNT! exit /b 0
for %%N in (%RFPY_PICK%) do set "RFPY_SELECTED=!RFPY_ITEM_%%N!"
exit /b 0

:activate_arg
if "%~2"=="" (echo [ERREUR] Nom d environnement manquant.&endlocal&exit /b 2)
set "RFPY_SELECTED=%~2"

:activate_selected
set "RFPY_MANIFEST=%RFPY_ROOT%\stacks\%RFPY_SELECTED%\rfpy.json"
if not exist "%RFPY_MANIFEST%" (echo [ERREUR] Environnement inconnu : %RFPY_SELECTED%.&endlocal&exit /b 2)
for /f "usebackq tokens=1,2,3 delims=|" %%A in (`"%RFPY_CORE_PY%" -c "import json;d=json.load(open(r'%RFPY_MANIFEST%',encoding='utf-8-sig'));print(str(d.get('venv',''))+'|'+str(d.get('environment_type','shared'))+'|'+str(d.get('project_path','')))"`) do (
  set "NEW_VENV=%%A"&set "NEW_TYPE=%%B"&set "NEW_PROJECT=%%C"
)
if not exist "%NEW_VENV%\Scripts\python.exe" (echo [ERREUR] Venv incomplet.&endlocal&exit /b 2)
if not defined RFPY_ORIGINAL_PATH set "RFPY_ORIGINAL_PATH=%PATH%"
endlocal & (
  set "RFPY_HOME=%RFPY_ROOT%"
  set "RFPY_ORIGINAL_PATH=%RFPY_ORIGINAL_PATH%"
  set "RFPY_ENV=%RFPY_SELECTED%"
  set "RFPY_VENV=%NEW_VENV%"
  set "VIRTUAL_ENV=%NEW_VENV%"
  set "RFPY_ENV_TYPE=%NEW_TYPE%"
  set "RFPY_PROJECT=%NEW_PROJECT%"
  set "PATH=%RFPY_BIN%;%NEW_VENV%\Scripts;%RFPY_ORIGINAL_PATH%"
  if /I "%NEW_TYPE%"=="project" (set "UV_PROJECT=%NEW_PROJECT%") else set "UV_PROJECT="
)
echo [RFPY] %RFPY_SELECTED% actif.
exit /b 0

:deactivate
if not defined RFPY_ENV (echo [RFPY] Aucun environnement actif.&endlocal&exit /b 0)
endlocal & (
  if defined RFPY_ORIGINAL_PATH set "PATH=%RFPY_ORIGINAL_PATH%"
  set "VIRTUAL_ENV="
  set "UV_PROJECT="
  set "RFPY_ENV="
  set "RFPY_VENV="
  set "RFPY_ENV_TYPE="
  set "RFPY_PROJECT="
  set "RFPY_ORIGINAL_PATH="
  set "RFPY_HOME=%RFPY_ROOT%"
)
echo [RFPY] Environnement desactive.
exit /b 0
