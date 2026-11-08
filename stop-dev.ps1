[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$runtimeDirectory = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) '.dev-runtime'
$statePath = Join-Path $runtimeDirectory 'services.json'

function Get-ProcessRecord([int]$ProcessId) {
    $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue
    if ($null -eq $processInfo) { return $null }
    $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if ($null -eq $process) { return $null }
    return [pscustomobject]@{
        Id = $ProcessId
        StartTimeUtc = $process.StartTime.ToUniversalTime().ToString('o')
        Path = $processInfo.ExecutablePath
        CommandLine = $processInfo.CommandLine
    }
}

function Test-TrackedProcess($Entry) {
    $current = Get-ProcessRecord -ProcessId ([int]$Entry.id)
    if ($null -eq $current -or [string]::IsNullOrWhiteSpace($current.Path)) { return $false }
    if (-not [string]::Equals($current.Path, [string]$Entry.path, [System.StringComparison]::OrdinalIgnoreCase)) { return $false }
    if (-not [string]::Equals($current.StartTimeUtc, [string]$Entry.start_time_utc, [System.StringComparison]::OrdinalIgnoreCase)) { return $false }
    return $current.CommandLine.Contains([string]$Entry.command_marker)
}

function Test-IsDescendantProcess([int]$ProcessId, [int]$AncestorProcessId) {
    $currentId = $ProcessId
    for ($depth = 0; $depth -lt 12; $depth++) {
        $current = Get-CimInstance Win32_Process -Filter "ProcessId = $currentId" -ErrorAction SilentlyContinue
        if ($null -eq $current) { return $false }
        $parentId = [int]$current.ParentProcessId
        if ($parentId -eq $AncestorProcessId) { return $true }
        if ($parentId -le 0 -or $parentId -eq $currentId) { return $false }
        $currentId = $parentId
    }
    return $false
}

if (-not (Test-Path -LiteralPath $statePath -PathType Leaf)) {
    Write-Host 'No Forever BIS app-process record was found; no processes were stopped.' -ForegroundColor Yellow
    Write-Host 'PostgreSQL was left untouched.'
    Write-Host 'To stop PostgreSQL separately while preserving its volume: docker compose --env-file .env stop db'
    exit 0
}

$state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
$remaining = [System.Collections.Generic.List[object]]::new()
$entries = @($state.processes)
[array]::Reverse($entries)
foreach ($entry in $entries) {
    $process = Get-Process -Id ([int]$entry.id) -ErrorAction SilentlyContinue
    if ($null -eq $process) {
        Write-Host "NOT RUNNING $($entry.name) (PID $($entry.id))." -ForegroundColor DarkGray
        continue
    }
    if (-not (Test-TrackedProcess $entry)) {
        Write-Host "SKIPPED $($entry.name) (PID $($entry.id)): process identity did not match the recorded launcher process." -ForegroundColor Yellow
        continue
    }

    try {
        if ($entry.name -eq 'FastAPI') {
            $descendants = @(Get-CimInstance Win32_Process | Where-Object {
                $_.CommandLine -and $_.CommandLine.Contains([string]$entry.command_marker) -and
                (Test-IsDescendantProcess -ProcessId ([int]$_.ProcessId) -AncestorProcessId ([int]$entry.id))
            })
            foreach ($descendant in $descendants) {
                Stop-Process -Id ([int]$descendant.ProcessId) -ErrorAction SilentlyContinue
            }
        }
        Stop-Process -Id ([int]$entry.id) -ErrorAction Stop
        $deadline = [DateTime]::UtcNow.AddSeconds(8)
        while ([DateTime]::UtcNow -lt $deadline -and (Get-Process -Id ([int]$entry.id) -ErrorAction SilentlyContinue)) {
            Start-Sleep -Milliseconds 200
        }
        if (Test-TrackedProcess $entry) {
            Write-Host "WARNING $($entry.name) (PID $($entry.id)) is still running; its record was retained." -ForegroundColor Yellow
            $remaining.Add($entry)
        }
        else {
            Write-Host "STOPPED $($entry.name) (PID $($entry.id))." -ForegroundColor Green
        }
    }
    catch {
        Write-Host "ERROR stopping $($entry.name) (PID $($entry.id)): $($_.Exception.Message)" -ForegroundColor Red
        $remaining.Add($entry)
    }
}

if ($remaining.Count -gt 0) {
    [pscustomobject]@{ created_at_utc = $state.created_at_utc; processes = @($remaining.ToArray()) } |
        ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $statePath -Encoding UTF8
}
else {
    Remove-Item -LiteralPath $statePath -Force
}

Write-Host 'PostgreSQL was left running; its data volume was not changed.' -ForegroundColor Cyan
Write-Host 'To stop PostgreSQL separately while preserving its volume: docker compose --env-file .env stop db'
