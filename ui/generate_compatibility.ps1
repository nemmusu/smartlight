# Regenerate the offline OpenRGB 1.0rc2 catalog from the official CSV snapshot.
# Source: https://openrgb.org/data/supported_devices_1.0rc2.csv
# The original CSV is retained next to the generated JS for source verification.
[CmdletBinding()]
param([switch]$Refresh)

$ErrorActionPreference = 'Stop'
$source = 'https://openrgb.org/data/supported_devices_1.0rc2.csv'
$csvPath = Join-Path $PSScriptRoot 'openrgb_devices_1.0rc2.csv'
$outputPath = Join-Path $PSScriptRoot 'compatibility_data.js'
if ($Refresh) { Invoke-WebRequest -Uri $source -OutFile $csvPath -UseBasicParsing }
if (-not (Test-Path -LiteralPath $csvPath -PathType Leaf)) { throw "CSV mancante: $csvPath" }

$rows = @(Import-Csv -LiteralPath $csvPath -Encoding utf8)
if ($rows.Count -lt 1000) { throw "Catalogo OpenRGB incompleto: $($rows.Count) righe" }
$brandPatterns = @(
    @{ Prefix = 'Cooler Master'; Brand = 'Cooler Master' },
    @{ Prefix = 'Lian Li'; Brand = 'Lian Li' },
    @{ Prefix = 'Steel Series'; Brand = 'SteelSeries' },
    @{ Prefix = 'SteelSeries'; Brand = 'SteelSeries' },
    @{ Prefix = 'Das Keyboard'; Brand = 'Das Keyboard' },
    @{ Prefix = 'Bloody'; Brand = 'A4Tech Bloody' }
)
$devices = foreach ($row in $rows) {
    $name = if ([string]::IsNullOrWhiteSpace($row.Name)) { $row.RGBController } else { $row.Name }
    if ([string]::IsNullOrWhiteSpace($name)) { continue }
    $brand = $null
    foreach ($pattern in $brandPatterns) {
        if ($name.StartsWith($pattern.Prefix, [StringComparison]::OrdinalIgnoreCase)) {
            $brand = $pattern.Brand
            break
        }
    }
    if (-not $brand) { $brand = ($name -split '[ /-]', 2)[0] }
    $categories = @($row.Category -split '[\r\n]+' | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    if (-not $categories.Count) { $categories = @('Unknown') }
    [ordered]@{
        n = $name.Trim()
        b = $brand
        c = $categories
        r = $row.RGBController.Trim()
        t = $row.Type.Trim()
        s = $row.Save.Trim()
        d = $row.Direct.Trim()
        e = $row.Effects.Trim()
        x = $row.Comments.Trim()
    }
}
$catalog = [ordered]@{
    source = $source
    page = 'https://openrgb.org/devices_1.0rc2.html'
    version = 'OpenRGB 1.0rc2'
    snapshotDate = '2026-10-01'
    csvSha256 = (Get-FileHash -LiteralPath $csvPath -Algorithm SHA256).Hash
    count = @($devices).Count
    devices = @($devices)
}
$json = ConvertTo-Json -InputObject $catalog -Depth 6 -Compress
$body = "// Catalogo locale da CSV ufficiale OpenRGB 1.0rc2; rigenerare con generate_compatibility.ps1.`nwindow.SMARTLIGHT_OPENRGB_CATALOG = $json;`n"
[IO.File]::WriteAllText($outputPath, $body, [Text.UTF8Encoding]::new($false))
Write-Host "Generati $($catalog.count) record in $outputPath"
