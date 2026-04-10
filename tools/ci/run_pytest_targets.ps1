param(
    [string[]]$Targets = @(),

    [string[]]$GroupNames = @(),

    [string]$GroupFile = "",

    [string[]]$PytestArgs = @("-q")
)

$ErrorActionPreference = "Stop"
$scriptRoot = Split-Path -Parent $PSCommandPath
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $scriptRoot "..\.."))

function Resolve-RepoPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PathValue
    )

    if ([System.IO.Path]::IsPathRooted($PathValue)) {
        return [System.IO.Path]::GetFullPath($PathValue)
    }

    return [System.IO.Path]::GetFullPath((Join-Path $repoRoot $PathValue))
}

function Resolve-PytestTarget {
    param(
        [Parameter(Mandatory = $true)]
        [string]$TargetValue
    )

    $pathPart = $TargetValue
    $nodePart = ""

    if ($TargetValue -match "^(.*?)(::.*)$") {
        $pathPart = $Matches[1]
        $nodePart = $Matches[2]
    }

    $resolvedPath = Resolve-RepoPath -PathValue $pathPart
    if (-not (Test-Path $resolvedPath)) {
        throw "Pytest target not found: $TargetValue"
    }

    $fullPath = (Get-Item $resolvedPath).FullName
    return "$fullPath$nodePart"
}

if ([string]::IsNullOrWhiteSpace($GroupFile)) {
    $GroupFile = Join-Path $scriptRoot "pytest-target-groups.psd1"
} else {
    $GroupFile = Resolve-RepoPath -PathValue $GroupFile
}

if (-not $env:UV_CACHE_DIR) {
    $env:UV_CACHE_DIR = Join-Path $repoRoot ".uv-cache"
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
    $pytestTarget = Resolve-PytestTarget -TargetValue $target
    Write-Host "=== RUNNING $target ==="
    uv run pytest $pytestTarget @PytestArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Pytest target failed: $target"
    }
}
