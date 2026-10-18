# RFPY — Copyright © 2026 Olivier RENAULT — Apache-2.0
# RFPY shell bridge. Keeps activation in the current PowerShell process.
param(
    [Parameter(Position=0)][string]$Action = 'on',
    [Parameter(Position=1)][string]$Target,
    [Parameter(ValueFromRemainingArguments=$true)][string[]]$Tail,
    [Alias('m')][switch]$Menu,
    [Alias('h','?')][switch]$Help
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

$RfpyRoot = '__RFPY_ROOT__'
$RfpyBin = Join-Path $RfpyRoot 'bin'
$RfpyStacks = Join-Path $RfpyRoot 'stacks'
$RfpyPython = Join-Path $RfpyRoot '.appvenv\Scripts\python.exe'
$RfpyApp = Join-Path $RfpyRoot 'app\rfpy.py'
$RfpyConfig = Join-Path $RfpyRoot 'config\rfpy.json'
$env:RFPY_HOME = $RfpyRoot

if ($Help) { $Action = 'help' }
if ($Menu) { $Action = 'menu' }
if ($Action -in @('--help','-h','/?')) { $Action = 'help' }
if ($Action -ieq 'activate') { $Action = 'on' }
if ($Action -ieq 'deactivate') { $Action = 'off' }

$language = 'fr'
try {
    if (Test-Path -LiteralPath $RfpyConfig) {
        $rawCfg = Get-Content -LiteralPath $RfpyConfig -Raw | ConvertFrom-Json
        $uiProp = $rawCfg.PSObject.Properties['ui']
        if ($null -ne $uiProp -and $null -ne $rawCfg.ui) {
            $langProp = $rawCfg.ui.PSObject.Properties['language']
            if ($null -ne $langProp -and [string]$langProp.Value -in @('fr','en','de','es','zh')) {
                $language = [string]$langProp.Value
            }
        }
    }
} catch { }
$env:RFPY_LANG = $language

$words = @{
    fr=@{ title='RFPY - Sélection / activation'; keys='↑/↓ : sélectionner | Entrée : valider | Échap : quitter'; none='Aucun environnement RFPY installé.'; first='Ouverture de la console Web pour créer le premier environnement...'; project='Projet'; shared='Partagé'; active='actif'; menu='RFPY - Gestion'; activate='Activer'; rename='Renommer'; delete='Supprimer'; back='Retour'; newname='Nouveau nom'; deactivateFirst='Désactivez d abord avec rfpy off.'; confirm='Supprimer'; yes='o/N'; inactive='RFPY inactif.'; deactivated='Environnement désactivé.'; unknown='Environnement RFPY inconnu'; help='Commandes RFPY'; current='RFPY actif'; venv='Environnement virtuel' }
    en=@{ title='RFPY - Select / activate'; keys='Up/Down: select | Enter: validate | Esc: quit'; none='No RFPY environment installed.'; first='Opening the Web console to create the first environment...'; project='Project'; shared='Shared'; active='active'; menu='RFPY - Management'; activate='Activate'; rename='Rename'; delete='Delete'; back='Back'; newname='New name'; deactivateFirst='Deactivate first with rfpy off.'; confirm='Delete'; yes='y/N'; inactive='RFPY inactive.'; deactivated='Environment deactivated.'; unknown='Unknown RFPY environment'; help='RFPY commands'; current='RFPY active'; venv='Virtual environment' }
    de=@{ title='RFPY - Auswahl / Aktivierung'; keys='Hoch/Runter: auswählen | Enter: bestätigen | Esc: beenden'; none='Keine RFPY-Umgebung installiert.'; first='Web-Konsole wird geöffnet...'; project='Projekt'; shared='Geteilt'; active='aktiv'; menu='RFPY - Verwaltung'; activate='Aktivieren'; rename='Umbenennen'; delete='Löschen'; back='Zurück'; newname='Neuer Name'; deactivateFirst='Zuerst mit rfpy off deaktivieren.'; confirm='Löschen'; yes='j/N'; inactive='RFPY inaktiv.'; deactivated='Umgebung deaktiviert.'; unknown='Unbekannte RFPY-Umgebung'; help='RFPY-Befehle'; current='RFPY aktiv'; venv='Virtuelle Umgebung' }
    es=@{ title='RFPY - Selección / activación'; keys='Arriba/Abajo: seleccionar | Enter: validar | Esc: salir'; none='No hay entornos RFPY instalados.'; first='Abriendo la consola Web...'; project='Proyecto'; shared='Compartido'; active='activo'; menu='RFPY - Gestión'; activate='Activar'; rename='Renombrar'; delete='Eliminar'; back='Volver'; newname='Nuevo nombre'; deactivateFirst='Desactive primero con rfpy off.'; confirm='Eliminar'; yes='s/N'; inactive='RFPY inactivo.'; deactivated='Entorno desactivado.'; unknown='Entorno RFPY desconocido'; help='Comandos RFPY'; current='RFPY activo'; venv='Entorno virtual' }
    zh=@{ title='RFPY - 选择 / 激活'; keys='上下键：选择 | Enter：确认 | Esc：退出'; none='尚未安装 RFPY 环境。'; first='正在打开 Web 控制台…'; project='项目'; shared='共享'; active='活动'; menu='RFPY - 管理'; activate='激活'; rename='重命名'; delete='删除'; back='返回'; newname='新名称'; deactivateFirst='请先使用 rfpy off 停用。'; confirm='删除'; yes='是/N'; inactive='RFPY 未激活。'; deactivated='环境已停用。'; unknown='未知 RFPY 环境'; help='RFPY 命令'; current='RFPY 已激活'; venv='虚拟环境' }
}
function Msg([string]$Key) {
    $bucket = $words[$language]
    if ($null -ne $bucket -and $bucket.ContainsKey($Key)) { return [string]$bucket[$Key] }
    return [string]$words.fr[$Key]
}

function Read-ManifestField([object]$Object,[string[]]$Candidates,[string]$Fallback='') {
    foreach ($candidate in $Candidates) {
        $p = $Object.PSObject.Properties[$candidate]
        if ($null -eq $p -or $null -eq $p.Value) { continue }
        $text = [string]$p.Value
        if (-not [string]::IsNullOrWhiteSpace($text)) { return $text }
    }
    return $Fallback
}

function Find-ManagedEnvironments {
    if (-not (Test-Path -LiteralPath $RfpyStacks)) { return @() }
    $result = [System.Collections.Generic.List[object]]::new()
    foreach ($folder in @(Get-ChildItem -LiteralPath $RfpyStacks -Directory -ErrorAction SilentlyContinue | Sort-Object Name)) {
        $manifestFile = Join-Path $folder.FullName 'rfpy.json'
        if (-not (Test-Path -LiteralPath $manifestFile)) { continue }
        try {
            $manifest = Get-Content -LiteralPath $manifestFile -Raw | ConvertFrom-Json
            $venvPath = Read-ManifestField $manifest @('venv') ''
            if (-not $venvPath) { continue }
            $python = Join-Path $venvPath 'Scripts\python.exe'
            if (-not (Test-Path -LiteralPath $python)) { continue }
            $result.Add([pscustomobject]@{ Name=$folder.Name; Manifest=$manifest; ManifestPath=$manifestFile })
        } catch { }
    }
    return @($result)
}

function Describe-Environment([object]$Record) {
    $m = $Record.Manifest
    $kindRaw = Read-ManifestField $m @('environment_type','type') 'shared'
    $kind = if ($kindRaw -eq 'project') { Msg 'project' } else { Msg 'shared' }
    $python = Read-ManifestField $m @('python_resolved','python_requested','python_version','python') '?'
    $robot = Read-ManifestField $m @('robot_resolved','robot_requested','robot_version','robot') '-'
    $profile = Read-ManifestField $m @('profile','stack_profile') 'python'
    $suffix = if ($env:RFPY_ENV -and $env:RFPY_ENV -ieq $Record.Name) { ' [' + (Msg 'active') + ']' } else { '' }
    return "{0}{1} | [{2}] | {3} | Python {4} | RF {5}" -f $Record.Name,$suffix,$kind,$profile,$python,$robot
}

function Pick-FromList([object[]]$Items,[string]$Heading,[scriptblock]$Formatter) {
    if ($Items.Count -eq 0) { return $null }
    $cursor = 0
    for ($i=0; $i -lt $Items.Count; $i++) {
        $name = if ($Items[$i].PSObject.Properties['Name']) { [string]$Items[$i].Name } else { '' }
        if ($env:RFPY_ENV -and $name -ieq $env:RFPY_ENV) { $cursor=$i; break }
    }
    try {
        while ($true) {
            Clear-Host
            Write-Host ('='*72) -ForegroundColor Cyan
            Write-Host (' ' + $Heading) -ForegroundColor Cyan
            Write-Host ('='*72) -ForegroundColor Cyan
            Write-Host ''
            for ($i=0; $i -lt $Items.Count; $i++) {
                $line = & $Formatter $Items[$i]
                if ($i -eq $cursor) { Write-Host ('> ' + $line) -ForegroundColor Cyan }
                else { Write-Host ('  ' + $line) }
            }
            Write-Host ''
            Write-Host (Msg 'keys') -ForegroundColor DarkGray
            $key = [Console]::ReadKey($true).Key
            if ($key -eq [ConsoleKey]::UpArrow) { $cursor=($cursor-1+$Items.Count)%$Items.Count; continue }
            if ($key -eq [ConsoleKey]::DownArrow) { $cursor=($cursor+1)%$Items.Count; continue }
            if ($key -eq [ConsoleKey]::Enter) { return $Items[$cursor] }
            if ($key -eq [ConsoleKey]::Escape) { return $null }
        }
    } catch {
        for ($i=0; $i -lt $Items.Count; $i++) { Write-Host ("  {0}. {1}" -f ($i+1),(& $Formatter $Items[$i])) }
        $raw = Read-Host '>'
        $n=0
        if ([int]::TryParse($raw,[ref]$n) -and $n -ge 1 -and $n -le $Items.Count) { return $Items[$n-1] }
        return $null
    }
}

function Call-RfpyCore([string[]]$Arguments) {
    if (-not (Test-Path -LiteralPath $RfpyPython)) { throw "Runtime RFPY introuvable : $RfpyPython" }
    if (-not (Test-Path -LiteralPath $RfpyApp)) { throw "Application RFPY introuvable : $RfpyApp" }
    $env:RFPY_HOME = $RfpyRoot
    & $RfpyPython $RfpyApp @Arguments
    $global:LASTEXITCODE = $LASTEXITCODE
}

function Save-ShellBaseline {
    if (-not $env:RFPY_ORIGINAL_PATH) { $env:RFPY_ORIGINAL_PATH = $env:Path }
    $savedPrompt = Get-Variable -Name RFPY_PROMPT_BEFORE -Scope Global -ErrorAction SilentlyContinue
    if ($null -eq $savedPrompt) {
        try { $global:RFPY_PROMPT_BEFORE = (Get-Command prompt -CommandType Function).ScriptBlock } catch { $global:RFPY_PROMPT_BEFORE = $null }
    }
    if ($null -eq $env:RFPY_ORIGINAL_VIRTUAL_ENV) { $env:RFPY_ORIGINAL_VIRTUAL_ENV = $env:VIRTUAL_ENV }
    if ($null -eq $env:RFPY_ORIGINAL_UV_PROJECT) { $env:RFPY_ORIGINAL_UV_PROJECT = $env:UV_PROJECT }
}

function Enter-ManagedEnvironment([object]$Record) {
    $m = $Record.Manifest
    $venv = Read-ManifestField $m @('venv') ''
    $scripts = Join-Path $venv 'Scripts'
    $python = Join-Path $scripts 'python.exe'
    if (-not (Test-Path -LiteralPath $python)) { throw "Venv invalide : $venv" }
    Save-ShellBaseline
    $base = $env:RFPY_ORIGINAL_PATH
    $env:Path = "$RfpyBin;$scripts;$base"
    $env:VIRTUAL_ENV = $venv
    $env:RFPY_ENV = $Record.Name
    $env:RFPY_VENV = $venv
    $env:RFPY_HOME = $RfpyRoot
    $mode = Read-ManifestField $m @('environment_type','type') 'shared'
    $project = Read-ManifestField $m @('project_path','project') ''
    if ($mode -eq 'project' -and $project) {
        $env:RFPY_ENV_TYPE='project'; $env:RFPY_PROJECT=$project; $env:UV_PROJECT=$project
    } elseif ($mode -eq 'project') {
        $env:RFPY_ENV_TYPE='project-pending'; $env:RFPY_PROJECT=''; Remove-Item Env:UV_PROJECT -ErrorAction SilentlyContinue
    } else {
        $env:RFPY_ENV_TYPE='shared'; $env:RFPY_PROJECT=''; Remove-Item Env:UV_PROJECT -ErrorAction SilentlyContinue
    }
    $savedPrompt = Get-Variable -Name RFPY_PROMPT_BEFORE -Scope Global -ErrorAction SilentlyContinue
    if ($null -ne $savedPrompt -and $null -ne $savedPrompt.Value) {
        function global:prompt { "[RFPY - $env:RFPY_ENV] " + (& $global:RFPY_PROMPT_BEFORE) }
    }
    Write-Host ("[RFPY] {0} actif [{1}]." -f $Record.Name,$env:RFPY_ENV_TYPE) -ForegroundColor Green
}

function Leave-ManagedEnvironment {
    if (-not $env:RFPY_ENV) { Write-Host (Msg 'inactive') -ForegroundColor Yellow; return }
    if ($env:RFPY_ORIGINAL_PATH) { $env:Path=$env:RFPY_ORIGINAL_PATH }
    if ($null -ne $env:RFPY_ORIGINAL_VIRTUAL_ENV) { $env:VIRTUAL_ENV=$env:RFPY_ORIGINAL_VIRTUAL_ENV } else { Remove-Item Env:VIRTUAL_ENV -ErrorAction SilentlyContinue }
    if ($null -ne $env:RFPY_ORIGINAL_UV_PROJECT -and $env:RFPY_ORIGINAL_UV_PROJECT) { $env:UV_PROJECT=$env:RFPY_ORIGINAL_UV_PROJECT } else { Remove-Item Env:UV_PROJECT -ErrorAction SilentlyContinue }
    $savedPrompt = Get-Variable -Name RFPY_PROMPT_BEFORE -Scope Global -ErrorAction SilentlyContinue
    if ($null -ne $savedPrompt -and $null -ne $savedPrompt.Value) { Set-Item -Path Function:\global:prompt -Value $savedPrompt.Value }
    foreach ($name in @('RFPY_ENV','RFPY_VENV','RFPY_ENV_TYPE','RFPY_PROJECT','RFPY_ORIGINAL_PATH','RFPY_ORIGINAL_VIRTUAL_ENV','RFPY_ORIGINAL_UV_PROJECT')) { Remove-Item ("Env:"+$name) -ErrorAction SilentlyContinue }
    $global:RFPY_PROMPT_BEFORE = $null
    $env:RFPY_HOME = $RfpyRoot
    Write-Host (Msg 'deactivated') -ForegroundColor Green
}

function Open-FirstRun {
    Write-Host ''
    Write-Host ('[RFPY] ' + (Msg 'none')) -ForegroundColor Yellow
    Write-Host ('[RFPY] ' + (Msg 'first')) -ForegroundColor Cyan
    Call-RfpyCore @('web')
}

function Resolve-Environment([string]$Name) {
    $all = @(Find-ManagedEnvironments)
    if ($Name) {
        $hits=@($all | Where-Object { $_.Name -ieq $Name })
        if ($hits.Count -ne 1) { throw ((Msg 'unknown') + ': ' + $Name) }
        return $hits[0]
    }
    if ($all.Count -eq 0) { return $null }
    return Pick-FromList $all (Msg 'title') { param($x) Describe-Environment $x }
}

function Show-ManagementMenu {
    while ($true) {
        $all=@(Find-ManagedEnvironments)
        if ($all.Count -eq 0) { Open-FirstRun; return }
        $selected=Pick-FromList $all (Msg 'menu') { param($x) Describe-Environment $x }
        if ($null -eq $selected) { return }
        $actions=@(
            [pscustomobject]@{Name=(Msg 'activate'); Code='activate'},
            [pscustomobject]@{Name=(Msg 'rename'); Code='rename'},
            [pscustomobject]@{Name=(Msg 'delete'); Code='delete'},
            [pscustomobject]@{Name=(Msg 'back'); Code='back'}
        )
        $picked=Pick-FromList $actions ((Msg 'menu') + ' - ' + $selected.Name) { param($x) $x.Name }
        if ($null -eq $picked -or $picked.Code -eq 'back') { continue }
        if ($picked.Code -eq 'activate') { Enter-ManagedEnvironment $selected; return }
        if ($picked.Code -eq 'rename') {
            $new=(Read-Host ((Msg 'newname') + " [$($selected.Name)]")).Trim()
            if ($new -and $new -ne $selected.Name) { Call-RfpyCore @('rename',$selected.Name,$new) }
            continue
        }
        if ($picked.Code -eq 'delete') {
            if ($env:RFPY_ENV -and $env:RFPY_ENV -ieq $selected.Name) { Write-Host ('[ERREUR] ' + (Msg 'deactivateFirst')) -ForegroundColor Red; continue }
            $confirm=Read-Host ((Msg 'confirm') + " $($selected.Name) ? (" + (Msg 'yes') + ')')
            if ($confirm -match '^(o|oui|y|yes|ja|j|si|sí|s|是)$') { Call-RfpyCore @('delete',$selected.Name) }
        }
    }
}

try {
    switch ($Action.ToLowerInvariant()) {
        'on' {
            $record=Resolve-Environment $Target
            if ($null -eq $record) { Open-FirstRun } else { Enter-ManagedEnvironment $record }
        }
        'off' { Leave-ManagedEnvironment }
        'menu' { Show-ManagementMenu }
        'list' { Call-RfpyCore @('list') }
        'status' {
            if ($env:RFPY_ENV) { Write-Host ((Msg 'current') + " : $env:RFPY_ENV") -ForegroundColor Green; Write-Host ((Msg 'venv') + " : $env:VIRTUAL_ENV") }
            else { Write-Host (Msg 'inactive') -ForegroundColor Yellow }
        }
        'help' {
            Write-Host (Msg 'help') -ForegroundColor Cyan
            Write-Host '  rfpy                         sélection / activation rapide'
            Write-Host '  rfpy -m                      menu de gestion'
            Write-Host '  rfpy on|activate [ENV]       activer'
            Write-Host '  rfpy off|deactivate          désactiver'
            Write-Host '  rfpy list|status|doctor|web  informations / console Web'
            Write-Host '  rfpy install|project|...     commandes avancées'
        }
        default {
            $forward=@($Action)
            if ($Target) { $forward += $Target }
            if ($Tail) { $forward += @($Tail) }
            Call-RfpyCore $forward
        }
    }
} catch {
    $message=[string]$_.Exception.Message
    if (-not $message) { $message='Erreur RFPY inattendue.' }
    Write-Host ("[ERREUR] {0}" -f $message) -ForegroundColor Red
    $global:LASTEXITCODE=1
}
