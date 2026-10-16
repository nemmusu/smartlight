# Smartlight prerequisite checker and guided bootstrap.
# All third-party downloads come from official vendor URLs. Run -DryRun to inspect
# the actions without downloading, installing, opening pages, or writing files.
[CmdletBinding()]
param(
    [switch]$InstallWebView2,
    [switch]$InstallOpenRGB,
    [switch]$InstallICUE,
    [switch]$DryRun,
    [ValidateSet('en', 'it', '1033', '1040')]
    [string]$Language = 'en'
)

$ErrorActionPreference = 'Stop'
function Get-SetupText([string]$English, [string]$Italian) {
    if ($Language -in @('it', '1040')) { return $Italian }
    return $English
}

$webviewPage = 'https://developer.microsoft.com/en-us/microsoft-edge/webview2/'
$webviewBootstrapper = 'https://go.microsoft.com/fwlink/p/?LinkId=2124703'
$openRgbPage = 'https://openrgb.org/releases.html'
$openRgbMsi = 'https://codeberg.org/OpenRGB/OpenRGB/releases/download/release_candidate_1.0rc2/OpenRGB_1.0rc2_Windows_64_0fca93e.msi'
$openRgbSha256 = '6C656FCA447B9BC0F360F13EC67691D685E35455EE7933E30ED5D09F8F06CF8F'
$corsairPage = 'https://www.corsair.com/us/en/s/downloads'
$corsairInstaller = 'https://www3.corsair.com/software/CUE_V5/public/modules/windows/installer/Install%20iCUE.exe'

function Test-WebView2 {
    $guid = '{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}'
    $locations = @(
        "HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\$guid",
        "HKCU:\Software\Microsoft\EdgeUpdate\Clients\$guid",
        "HKLM:\SOFTWARE\Microsoft\EdgeUpdate\Clients\$guid"
    )
    foreach ($location in $locations) {
        try {
            $version = (Get-ItemProperty -LiteralPath $location -Name pv -ErrorAction Stop).pv
            if ($version -and $version -ne '0.0.0.0') { return $true }
        } catch { }
    }
    return $false
}

function Test-OpenRGB {
    $locations = @(
        "$env:ProgramW6432\OpenRGB\OpenRGB.exe",
        "$env:ProgramFiles\OpenRGB\OpenRGB.exe",
        "${env:ProgramFiles(x86)}\OpenRGB\OpenRGB.exe",
        "$env:LOCALAPPDATA\Programs\OpenRGB\OpenRGB.exe"
    )
    $entries = Get-UninstallEntries '^OpenRGB$'
    foreach ($entry in $entries) {
        if ($entry.InstallLocation) { $locations += (Join-Path $entry.InstallLocation 'OpenRGB.exe') }
        if ($entry.DisplayIcon) { $locations += ($entry.DisplayIcon -replace ',\d+$', '').Trim('"') }
    }
    try {
        $running = Get-Process -Name OpenRGB -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($running -and $running.Path) { $locations += $running.Path }
    } catch { }
    return [bool]($locations | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Leaf) } | Select-Object -First 1)
}

function Test-ICUE {
    $locations = @(
        "$env:ProgramW6432\Corsair\Corsair iCUE5 Software\iCUE.exe",
        "$env:ProgramFiles\Corsair\Corsair iCUE5 Software\iCUE.exe",
        "${env:ProgramFiles(x86)}\Corsair\Corsair iCUE5 Software\iCUE.exe"
    )
    foreach ($entry in (Get-UninstallEntries '^Corsair iCUE5 Software$')) {
        if ($entry.InstallLocation) { $locations += (Join-Path $entry.InstallLocation 'iCUE.exe') }
        if ($entry.DisplayIcon) { $locations += ($entry.DisplayIcon -replace ',\d+$', '').Trim('"') }
    }
    return [bool]($locations | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Leaf) } | Select-Object -First 1)
}

function Get-UninstallEntries([string]$DisplayNamePattern) {
    $subpath = 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'
    foreach ($hive in @([Microsoft.Win32.RegistryHive]::LocalMachine, [Microsoft.Win32.RegistryHive]::CurrentUser)) {
        foreach ($view in @([Microsoft.Win32.RegistryView]::Registry64, [Microsoft.Win32.RegistryView]::Registry32)) {
            $registryRoot = $null
            $uninstallKey = $null
            try {
                $registryRoot = [Microsoft.Win32.RegistryKey]::OpenBaseKey($hive, $view)
                $uninstallKey = $registryRoot.OpenSubKey($subpath)
                if (-not $uninstallKey) { continue }
                foreach ($name in $uninstallKey.GetSubKeyNames()) {
                    $appKey = $null
                    try {
                        $appKey = $uninstallKey.OpenSubKey($name)
                        if (-not $appKey) { continue }
                        $displayName = [string]$appKey.GetValue('DisplayName')
                        if ($displayName -match $DisplayNamePattern) {
                            [pscustomobject]@{
                                DisplayName = $displayName
                                InstallLocation = [string]$appKey.GetValue('InstallLocation')
                                DisplayIcon = [string]$appKey.GetValue('DisplayIcon')
                            }
                        }
                    } finally { if ($appKey) { $appKey.Close() } }
                }
            } catch { } finally {
                if ($uninstallKey) { $uninstallKey.Close() }
                if ($registryRoot) { $registryRoot.Close() }
            }
        }
    }
}

function Wait-ForPrerequisite([scriptblock]$Probe, [string]$Name) {
    for ($attempt = 0; $attempt -lt 12; $attempt++) {
        if (& $Probe) { Write-Host (Get-SetupText "$Name detected after installation." "$Name rilevato dopo l'installazione."); return }
        if ($attempt -lt 11) { Start-Sleep -Seconds 2 }
    }
    throw (Get-SetupText "$Name was not detected after the installer closed. Installation may have been cancelled or incomplete." "$Name non rilevato dopo la chiusura dell'installer. L'installazione potrebbe essere stata annullata o non completata.")
}

function Save-VendorDownload([string]$Url, [string]$Path) {
    $uri = [Uri]$Url
    if ($uri.Scheme -ne 'https') { throw (Get-SetupText "HTTPS is required: $Url" "È richiesto HTTPS: $Url") }
    Invoke-WebRequest -Uri $uri -OutFile $Path -MaximumRedirection 5 -UseBasicParsing
    if ((Get-Item -LiteralPath $Path).Length -lt 100000) {
        throw (Get-SetupText "Incomplete download: $Url" "Download incompleto: $Url")
    }
}

function Install-WebView2Runtime {
    if (Test-WebView2) { Write-Host (Get-SetupText 'WebView2: already installed.' 'WebView2: già installato.'); return }
    if ($DryRun) { Write-Host (Get-SetupText "DRY RUN: would download WebView2 from $webviewBootstrapper" "DRY RUN: scaricherei WebView2 da $webviewBootstrapper"); return }
    $file = Join-Path ([IO.Path]::GetTempPath()) ("Smartlight-WebView2-{0}.exe" -f [Guid]::NewGuid())
    try {
        Save-VendorDownload $webviewBootstrapper $file
        $signature = Get-AuthenticodeSignature -LiteralPath $file
        if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Microsoft') {
            throw (Get-SetupText 'Microsoft signature on the WebView2 bootstrapper could not be verified.' 'Firma Microsoft del bootstrapper WebView2 non verificata.')
        }
        $process = Start-Process -FilePath $file -ArgumentList '/silent', '/install' -Wait -PassThru
        if ($process.ExitCode -notin @(0, 3010)) { throw (Get-SetupText "WebView2 installation ended with code $($process.ExitCode)." "Installazione WebView2 terminata con codice $($process.ExitCode).") }
        Wait-ForPrerequisite ${function:Test-WebView2} 'WebView2'
        Write-Host (Get-SetupText 'WebView2 installed.' 'WebView2 installato.')
    } catch {
        Write-Warning $_.Exception.Message
        throw
    } finally {
        Remove-Item -LiteralPath $file -Force -ErrorAction SilentlyContinue
    }
}

function Install-OpenRGBGuided {
    if (Test-OpenRGB) { Write-Host (Get-SetupText 'OpenRGB: already installed.' 'OpenRGB: già presente.'); return }
    if ($DryRun) { Write-Host (Get-SetupText "DRY RUN: would download OpenRGB 1.0rc2 from $openRgbMsi and open its interactive installer" "DRY RUN: scaricherei OpenRGB 1.0rc2 da $openRgbMsi e aprirei l'installer interattivo"); return }
    if (-not [Environment]::Is64BitOperatingSystem) {
        throw (Get-SetupText 'This setup prepares OpenRGB x64; select the correct version from the official page.' 'Questa procedura prepara OpenRGB x64; seleziona la versione corretta dalla pagina ufficiale.')
    }
    $file = Join-Path ([IO.Path]::GetTempPath()) ("Smartlight-OpenRGB-{0}.msi" -f [Guid]::NewGuid())
    try {
        Save-VendorDownload $openRgbMsi $file
        $downloadHash = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash
        if ($downloadHash -ne $openRgbSha256) { throw (Get-SetupText 'Invalid OpenRGB hash: the download is incomplete or differs from the verified release.' 'Hash OpenRGB non valido: download interrotto o diverso dalla release verificata.') }
        $signature = Get-AuthenticodeSignature -LiteralPath $file
        if ($signature.Status -notin @('Valid', 'NotSigned')) {
            throw (Get-SetupText "Invalid OpenRGB MSI signature: $($signature.Status)" "Firma MSI OpenRGB non valida: $($signature.Status)")
        }
        Write-Host (Get-SetupText "OpenRGB 1.0rc2 MSI SHA-256 verified: $downloadHash" "OpenRGB 1.0rc2 MSI SHA-256 verificato: $downloadHash")
        Write-Host (Get-SetupText 'Opening the official OpenRGB installer. Complete the steps shown.' 'Apertura installer ufficiale OpenRGB. Completa i passaggi visualizzati.')
        $process = Start-Process -FilePath 'msiexec.exe' -ArgumentList @('/i', ('"{0}"' -f $file)) -Wait -PassThru
        if ($process.ExitCode -notin @(0, 3010)) {
            throw (Get-SetupText "OpenRGB installation ended with code $($process.ExitCode)." "Installazione OpenRGB terminata con codice $($process.ExitCode).")
        }
        Wait-ForPrerequisite ${function:Test-OpenRGB} 'OpenRGB'
    } catch {
        Write-Warning $_.Exception.Message
        throw
    } finally {
        Remove-Item -LiteralPath $file -Force -ErrorAction SilentlyContinue
    }
}

function Install-ICUEGuided {
    if (Test-ICUE) { Write-Host (Get-SetupText 'iCUE 5: already installed.' 'iCUE 5: già presente.'); return }
    if ($DryRun) { Write-Host (Get-SetupText "DRY RUN: would download and run the official iCUE 5 installer from $corsairInstaller" "DRY RUN: scaricherei e avvierei l'installer iCUE 5 ufficiale da $corsairInstaller"); return }
    $file = Join-Path ([IO.Path]::GetTempPath()) ("Smartlight-iCUE-{0}.exe" -f [Guid]::NewGuid())
    try {
        Save-VendorDownload $corsairInstaller $file
        $signature = Get-AuthenticodeSignature -LiteralPath $file
        if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Corsair Memory') {
            throw (Get-SetupText 'Corsair signature on the iCUE installer could not be verified.' "Firma Corsair dell'installer iCUE non verificata.")
        }
        Write-Host (Get-SetupText 'Opening the official iCUE 5 installer. Accept the Corsair terms in its window.' 'Apertura installer iCUE 5 ufficiale. Accetta le condizioni Corsair nella finestra mostrata.')
        $process = Start-Process -FilePath $file -Wait -PassThru
        if ($process.ExitCode -notin @(0, 3010)) {
            throw (Get-SetupText "iCUE installation ended with code $($process.ExitCode)." "Installazione iCUE terminata con codice $($process.ExitCode).")
        }
        Wait-ForPrerequisite ${function:Test-ICUE} 'iCUE 5'
        Write-Host (Get-SetupText 'iCUE 5 installed.' 'iCUE 5 installato.')
    } catch {
        Write-Warning $_.Exception.Message
        throw
    } finally {
        Remove-Item -LiteralPath $file -Force -ErrorAction SilentlyContinue
    }
}

try {
    Write-Host "WebView2: $(if (Test-WebView2) { (Get-SetupText 'present' 'presente') } else { (Get-SetupText 'missing' 'mancante') })"
    Write-Host "OpenRGB: $(if (Test-OpenRGB) { (Get-SetupText 'present' 'presente') } else { (Get-SetupText 'missing' 'mancante') })"
    Write-Host "iCUE 5: $(if (Test-ICUE) { (Get-SetupText 'present' 'presente') } else { (Get-SetupText 'missing' 'mancante') })"
    if ($InstallWebView2) { Install-WebView2Runtime }
    if ($InstallOpenRGB) { Install-OpenRGBGuided }
    if ($InstallICUE) { Install-ICUEGuided }
    exit 0
} catch {
    Write-Error $_.Exception.Message
    exit 1
}
