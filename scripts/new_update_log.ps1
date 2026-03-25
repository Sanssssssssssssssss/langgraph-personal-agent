param(
    [Parameter(Mandatory = $true)]
    [string]$Version,
    [Parameter(Mandatory = $true)]
    [string]$Title
)

$ErrorActionPreference = "Stop"
$workspace = Split-Path -Parent $PSScriptRoot
$logsDir = Join-Path $workspace "logs"
$date = Get-Date -Format "yyyy-MM-dd"
$safeTitle = ($Title.ToLower() -replace "[^a-z0-9_-]", "_").Trim("_")
if ([string]::IsNullOrWhiteSpace($safeTitle)) {
    $safeTitle = "update"
}

$fileName = "${date}_v${Version}_${safeTitle}.txt"
$targetPath = Join-Path $logsDir $fileName

if (Test-Path $targetPath) {
    Write-Host $targetPath
    exit 0
}

$template = @"
Version: v$Version
Date: $date
Title: $Title

Completed:
- 

Files Updated:
- 

Notes:
- 
"@

Set-Content -Path $targetPath -Value $template -Encoding UTF8
Write-Host $targetPath

