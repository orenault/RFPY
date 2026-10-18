# RFPY — Copyright © 2026 Olivier RENAULT — Apache-2.0
# Direct shortcut to the local RFPY Web console.
param(
    [Alias('p')][int]$Port = 0,
    [Alias('n')][switch]$NoBrowser,
    [Parameter(ValueFromRemainingArguments=$true)][string[]]$Tail
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
$RfpyRoot = '__RFPY_ROOT__'
$RfpyPython = Join-Path $RfpyRoot '.appvenv\Scripts\python.exe'
$RfpyApp = Join-Path $RfpyRoot 'app\rfpy.py'
$env:RFPY_HOME = $RfpyRoot

if (-not (Test-Path -LiteralPath $RfpyPython)) { throw "Runtime RFPY introuvable : $RfpyPython" }
if (-not (Test-Path -LiteralPath $RfpyApp)) { throw "Application RFPY introuvable : $RfpyApp" }

$argsCore = @('web')
if ($Port -gt 0) { $argsCore += @('--port', [string]$Port) }
if ($NoBrowser) { $argsCore += '--no-browser' }
if ($Tail) { $argsCore += @($Tail) }
& $RfpyPython $RfpyApp @argsCore
$global:LASTEXITCODE = $LASTEXITCODE
