param(
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$workspace = Split-Path -Parent $PSScriptRoot
$venvPath = Join-Path $workspace ".venv"
$pythonExe = Join-Path $venvPath "Scripts\\python.exe"

function Invoke-WithRetry {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$Action,
        [int]$MaxAttempts = 3,
        [int]$DelaySeconds = 3
    )

    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        try {
            & $Action
            return
        } catch {
            if ($attempt -eq $MaxAttempts) {
                throw
            }
            Write-Host "[bootstrap] attempt $attempt failed, retrying in $DelaySeconds seconds"
            Start-Sleep -Seconds $DelaySeconds
        }
    }
}

Write-Host "[bootstrap] workspace: $workspace"

if (-not (Test-Path $venvPath)) {
    Write-Host "[bootstrap] creating virtual environment"
    py -3 -m venv $venvPath
}

if (-not (Test-Path $pythonExe)) {
    throw "Virtual environment python not found: $pythonExe"
}

Invoke-WithRetry -Action {
    & $pythonExe -m pip install --upgrade pip
}

if (-not $SkipInstall) {
    Write-Host "[bootstrap] installing project dependencies"
    Invoke-WithRetry -Action {
        & $pythonExe -m pip install -e $workspace
    }
}

Write-Host "[bootstrap] done"
Write-Host "[bootstrap] interpreter: $pythonExe"
Write-Host "[bootstrap] next: copy .env.example to .env if needed, then use VS Code tasks or launch configs"
