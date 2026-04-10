param(
    [string[]]$Targets,

    [string[]]$GroupNames,

    [string]$GroupFile = "tools\ci\pytest-target-groups.psd1",

    [string[]]$PytestArgs = @("-q")
)

$ErrorActionPreference = "Stop"

if (-not $env:UV_CACHE_DIR) {
    $env:UV_CACHE_DIR = Join-Path (Get-Location) ".uv-cache"
}

if (-not (Test-Path $env:UV_CACHE_DIR)) {
    New-Item -ItemType Directory -Path $env:UV_CACHE_DIR -Force | Out-Null
}

$resolvedTargets = @()

if ($GroupNames.Count -gt 0) {
    if (-not (Test-Path $GroupFile)) {
        throw "Pytest target group file not found: $GroupFile"
    }

    $groupMap = Import-PowerShellDataFile -Path $GroupFile
    foreach ($groupName in $GroupNames) {
        if (-not $groupMap.ContainsKey($groupName)) {
            throw "Unknown pytest target group: $groupName"
        }
        $resolvedTargets += $groupMap[$groupName]
    }
}

if ($Targets.Count -gt 0) {
    $resolvedTargets += $Targets
}

if ($resolvedTargets.Count -eq 0) {
    throw "Provide at least one pytest target or group name."
}

$seenTargets = @{}
$orderedTargets = foreach ($target in $resolvedTargets) {
    if (-not $seenTargets.ContainsKey($target)) {
        $seenTargets[$target] = $true
        $target
    }
}

foreach ($target in $orderedTargets) {
    $pytestTarget = $target
    if ($target -notmatch "::") {
        if (-not (Test-Path $target)) {
            throw "Pytest target not found: $target"
        }

        $pytestTarget = (Get-Item $target).FullName
    }

    Write-Host "=== RUNNING $target ==="
    uv run pytest $pytestTarget @PytestArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Pytest target failed: $target"
    }
}
