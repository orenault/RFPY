REM RFPY - Copyright (c) 2026 Olivier RENAULT - Apache-2.0
@echo off
set "RFPY_REAL_UV=%~dp0..\tools\uv\uv.exe"
if not exist "%RFPY_REAL_UV%" (echo [RFPY] uv introuvable : %RFPY_REAL_UV%&exit /b 2)
if /I "%RFPY_ENV_TYPE%"=="project-pending" goto :sharedmode
if /I "%RFPY_ENV_TYPE%"=="shared" goto :sharedmode
goto :run
:sharedmode
(
  if /I "%~1"=="add" goto :blocked
  if /I "%~1"=="remove" goto :blocked
  if /I "%~1"=="sync" goto :blocked
  if /I "%~1"=="lock" goto :blocked
  if /I "%~1"=="tree" goto :blocked
  if /I "%~1"=="export" goto :blocked
  if /I "%~1"=="build" goto :blocked
  if /I "%~1"=="publish" goto :blocked
  if /I "%~1"=="version" goto :blocked
  if /I "%~1"=="run" (shift&"%RFPY_REAL_UV%" run --active --no-project %*&exit /b %ERRORLEVEL%)
)
:run
"%RFPY_REAL_UV%" %*
exit /b %ERRORLEVEL%
:blocked
echo [RFPY] 'uv %~1' est une commande de projet.
echo        L environnement actif '%RFPY_ENV%' est de type Partage.
echo        Utilisez uv pip ... ou activez un environnement de type Projet.
exit /b 2
