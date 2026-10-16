param(
    [Parameter(Mandatory = $true)][string]$InstallDir,
    [string]$SetupDir,
    [Parameter(Mandatory = $true)][ValidateSet('check', 'stop')][string]$Action
)

# The installer must release DLLs from its own previous installation before
# NSIS starts copying files. Match full paths so a portable Smartlight or a
# process with a coincidentally similar name is never stopped.
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath($InstallDir).TrimEnd([IO.Path]::DirectorySeparatorChar)
$targetPaths = @(
    [IO.Path]::GetFullPath((Join-Path $root 'Smartlight\Smartlight.exe')),
    [IO.Path]::GetFullPath((Join-Path $root 'Smartlight-MCP\Smartlight-MCP.exe'))
)
if ($SetupDir) {
    # When the setup is launched beside the portable build, close that copy
    # too: otherwise it keeps the single-instance lock and the installed app
    # cannot open on the finish page.
    $setupRoot = [IO.Path]::GetFullPath($SetupDir)
    $targetPaths += [IO.Path]::GetFullPath((Join-Path $setupRoot 'Smartlight\Smartlight.exe'))
    $targetPaths += [IO.Path]::GetFullPath((Join-Path $setupRoot 'Smartlight-MCP\Smartlight-MCP.exe'))
}

function Get-SmartlightProcesses {
    @(
        Get-Process -Name Smartlight, Smartlight-MCP -ErrorAction SilentlyContinue |
            Where-Object {
                $path = $null
                try { $path = $_.Path } catch { }
                $path -and ($targetPaths | Where-Object {
                    [string]::Equals($_, $path, [StringComparison]::OrdinalIgnoreCase)
                })
            }
    )
}

try {
    $running = @(Get-SmartlightProcesses)
    if ($Action -eq 'check') {
        if ($running.Count) {
            Write-Output ("Smartlight in esecuzione: " + (($running | ForEach-Object { $_.Id }) -join ', '))
            exit 10
        }
        exit 0
    }

    foreach ($process in $running) {
        try { [void]$process.CloseMainWindow() } catch { }
    }
    if ($running.Count) { Start-Sleep -Seconds 2 }
    foreach ($process in @(Get-SmartlightProcesses)) {
        Stop-Process -InputObject $process -Force -ErrorAction Stop
    }
    if ($running.Count) { Start-Sleep -Milliseconds 500 }
    if (@(Get-SmartlightProcesses).Count) {
        Write-Error 'Smartlight e ancora in esecuzione; i file non sono stati sostituiti.'
        exit 20
    }
    exit 0
} catch {
    Write-Error $_
    exit 30
}
