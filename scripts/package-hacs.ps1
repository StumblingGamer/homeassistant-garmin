param(
    [string] $OutputPath = "dist/homeassistant-garmin.zip"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$stageRoot = Join-Path $repoRoot "dist/hacs-package"
$componentSource = Join-Path $repoRoot "custom_components/homeassistant_garmin"
$componentTarget = Join-Path $stageRoot "custom_components/homeassistant_garmin"
$zipPath = Join-Path $repoRoot $OutputPath

if (Test-Path $stageRoot) {
    Remove-Item -LiteralPath $stageRoot -Recurse -Force
}

New-Item -ItemType Directory -Force -Path $componentTarget | Out-Null
Copy-Item -Path (Join-Path $componentSource "*") -Destination $componentTarget -Recurse -Force

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $zipPath) | Out-Null
if (Test-Path $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}

Compress-Archive -Path (Join-Path $stageRoot "*") -DestinationPath $zipPath
Write-Host "Created $zipPath"
