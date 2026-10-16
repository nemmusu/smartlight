# Build a self-contained Windows installer. Run on Windows with Python 3.12+,
# pip, and NSIS 3.11+. The target PC does not need Python or NSIS.
[CmdletBinding()]
param(
    [string]$PythonExe = 'py',
    [string]$EntryPoint = 'app.py',
    [string]$McpEntryPoint = 'mcp_server.py',
    [string]$IconPath = 'ui\smartlight.ico',
    [string]$Version = '',
    [switch]$DryRun,
    [switch]$SkipDependencyInstall
)

$ErrorActionPreference = 'Stop'
$project = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
if (-not $Version) {
    $Version = (Get-Content -LiteralPath (Join-Path $project 'version.txt') -Raw).Trim()
}
if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw 'version.txt deve contenere X.Y.Z' }
$entry = Join-Path $project $EntryPoint
$mcpEntry = Join-Path $project $McpEntryPoint
$icon = Join-Path $project $IconPath
$requirements = Join-Path $project 'requirements.txt'
$buildVenv = Join-Path $project '.build\venv'
$pythonInVenv = if ($SkipDependencyInstall -and (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
    (Resolve-Path -LiteralPath $PythonExe).Path
} else { Join-Path $buildVenv 'Scripts\python.exe' }
$dist = Join-Path $project 'dist'
$nsi = Join-Path $PSScriptRoot 'Smartlight.nsi'
$makeNsisCommand = Get-Command makensis.exe -ErrorAction SilentlyContinue
$makeNsis = if ($makeNsisCommand) { $makeNsisCommand.Source } else { $null }
if (-not $makeNsis) {
    $localCompiler = Join-Path $project '.build\nsis\nsis-3.11\makensis.exe'
    if (Test-Path -LiteralPath $localCompiler -PathType Leaf) { $makeNsis = $localCompiler }
}
if (-not $makeNsis) {
    foreach ($candidate in @("${env:ProgramFiles(x86)}\NSIS\makensis.exe", "$env:ProgramFiles\NSIS\makensis.exe")) {
        if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            $makeNsis = $candidate
            break
        }
    }
}

Write-Host "Project: $project"
Write-Host "Desktop entry: $entry"
Write-Host "MCP entry: $mcpEntry"
Write-Host "Icon: $icon"
Write-Host "NSIS: $(if ($makeNsis) { $makeNsis } else { 'non installato' })"

$missing = @($entry, $mcpEntry, $icon, $requirements, $nsi) | Where-Object { -not (Test-Path -LiteralPath $_ -PathType Leaf) }
if ($missing.Count) {
    Write-Warning "File mancanti: $($missing -join ', ')"
    if (-not $DryRun) { throw 'Il progetto non è ancora pronto per il build.' }
}
if ($DryRun) {
    Write-Host 'DRY RUN: nessun pacchetto scaricato o scritto.'
    exit 0
}
if (-not $makeNsis) { throw 'NSIS 3.11+ non trovato. Installa NSIS dalla pagina ufficiale e riprova.' }

if (-not (Test-Path -LiteralPath $pythonInVenv -PathType Leaf)) {
    & $PythonExe -m venv $buildVenv
    if ($LASTEXITCODE -ne 0) { throw 'Creazione ambiente Python fallita.' }
}
if (-not $SkipDependencyInstall) {
    & $pythonInVenv -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw 'Aggiornamento pip fallito.' }
    & $pythonInVenv -m pip install -r $requirements 'pyinstaller==6.22.3'
    if ($LASTEXITCODE -ne 0) { throw 'Installazione dipendenze fallita.' }
}

# Each executable bundles its own Python runtime. This keeps the MCP stdio
# process independent of the desktop process, while hardware is owned only by
# the desktop service over its private loopback bridge.
$common = @('--noconfirm', '--clean', '--onedir', '--distpath', $dist,
            '--workpath', (Join-Path $project '.build\pyinstaller'),
            '--specpath', (Join-Path $project '.build'), '--paths', $project)
& $pythonInVenv -m PyInstaller @common '--windowed' '--name' 'Smartlight' '--icon' $icon '--add-data' "$(Join-Path $project 'ui');ui" '--collect-all' 'webview' '--collect-all' 'kasa' '--collect-all' 'keyring' '--collect-all' 'cuesdk' $entry
if ($LASTEXITCODE -ne 0) { throw 'Build GUI fallito.' }
& $pythonInVenv -m PyInstaller @common '--console' '--name' 'Smartlight-MCP' $mcpEntry
if ($LASTEXITCODE -ne 0) { throw 'Build MCP fallito.' }

foreach ($binary in @((Join-Path $dist 'Smartlight\Smartlight.exe'),
                      (Join-Path $dist 'Smartlight-MCP\Smartlight-MCP.exe'),
                      (Join-Path $dist 'Smartlight\_internal\ui\help.html'))) {
    if (-not (Test-Path -LiteralPath $binary -PathType Leaf)) { throw "EXE mancante: $binary" }
}

$defines = @("/DDIST_DIR=$dist", "/DPROJECT_DIR=$project", "/DVERSION=$Version", "/DICON_PATH=$icon")
& $makeNsis @defines $nsi
if ($LASTEXITCODE -ne 0) { throw 'Compilazione NSIS fallita.' }
$installer = Join-Path $dist "Smartlight-Setup-$Version.exe"
if (-not (Test-Path -LiteralPath $installer -PathType Leaf)) { throw 'Installer EXE non generato.' }
Write-Host "Installer pronto: $installer"
Get-FileHash -LiteralPath $installer -Algorithm SHA256 | Format-List
