# RFPY — Copyright © 2026 Olivier RENAULT — Apache-2.0
param([Parameter(ValueFromRemainingArguments=$true)][string[]]$ArgsRest)
$Root=Split-Path -Parent $PSScriptRoot
$RealUv=Join-Path $Root 'tools\uv\uv.exe'
if(-not(Test-Path -LiteralPath $RealUv)){Write-Host "[RFPY] uv introuvable : $RealUv" -ForegroundColor Red;exit 2}
$args2=@($ArgsRest)
if($env:RFPY_ENV_TYPE -in @('shared','project-pending') -and $args2.Count -gt 0){$cmd=$args2[0].ToLowerInvariant();$blocked=@('add','remove','sync','lock','tree','export','build','publish','version');if($blocked -contains $cmd){Write-Host "[RFPY] 'uv $cmd' est une commande de projet." -ForegroundColor Yellow;Write-Host "       L environnement actif '$env:RFPY_ENV' est de type Partage." -ForegroundColor Yellow;Write-Host '       Utilisez uv pip install/list/... ou activez un environnement de type Projet.' -ForegroundColor Yellow;exit 2};if($cmd -eq 'run'){$rest=@();if($args2.Count -gt 1){$rest=@($args2[1..($args2.Count-1)])};& $RealUv run --active --no-project @rest;exit $LASTEXITCODE}}
& $RealUv @args2
exit $LASTEXITCODE
