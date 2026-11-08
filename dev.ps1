[CmdletBinding()]
param(
    [switch]$NoBrowser,
    [ValidateRange(15, 600)]
    [int]$PostgresTimeoutSeconds = 120,
    [ValidateRange(10, 180)]
    [int]$ApplicationTimeoutSeconds = 45
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$runtimeDirectory = Join-Path $repoRoot '.dev-runtime'
$statePath = Join-Path $runtimeDirectory 'services.json'
$startedServices = [System.Collections.Generic.List[object]]::new()

function Get-NodeExecutable {
    $nodeCommand = Get-Command 'node.exe' -ErrorAction SilentlyContinue
    if ($null -ne $nodeCommand) {
        return $nodeCommand.Source
    }

    $standardPath = Join-Path $env:ProgramFiles 'nodejs\node.exe'
    if (Test-Path -LiteralPath $standardPath -PathType Leaf) {
        return $standardPath
    }

    $wingetPattern = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages\OpenJS.NodeJS.LTS_*\node-v*-win-*\node.exe'
    $wingetNode = Get-ChildItem -Path $wingetPattern -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if ($null -ne $wingetNode) {
        return $wingetNode.FullName
    }

    throw 'Node.js was not found. Install Node.js 22.12+ or add node.exe to PATH, then retry.'
}

function Get-DockerExecutable {
    $dockerCommand = Get-Command 'docker.exe' -ErrorAction SilentlyContinue
    if ($null -ne $dockerCommand) {
        return $dockerCommand.Source
    }

    $dockerPath = Join-Path $env:ProgramFiles 'Docker\Docker\resources\bin\docker.exe'
    if (Test-Path -LiteralPath $dockerPath -PathType Leaf) {
        return $dockerPath
    }

    throw 'Docker CLI was not found. Install Docker Desktop and ensure its CLI is available.'
}

function Get-ListeningProcessIds([int]$Port) {
    $ids = @()
    try {
        $connections = @(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction Stop)
        $ids += @($connections | Select-Object -ExpandProperty OwningProcess -Unique)
    }
    catch {
        $netstatOutput = & netstat.exe -ano -p tcp 2>$null
        foreach ($line in $netstatOutput) {
            if ($line -match "^\s*TCP\s+\S+:$Port\s+\S+\s+LISTENING\s+(\d+)") {
                $ids += [int]$Matches[1]
            }
        }
    }
    return @($ids | Sort-Object -Unique)
}

function Get-ProcessRecord([int]$ProcessId) {
    $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue
    if ($null -eq $processInfo) {
        return $null
    }
    $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if ($null -eq $process) {
        return $null
    }
    return [pscustomobject]@{
        Id = $ProcessId
        StartTimeUtc = $process.StartTime.ToUniversalTime().ToString('o')
        Path = $processInfo.ExecutablePath
        CommandLine = $processInfo.CommandLine
    }
}

function Test-TrackedProcess($Entry) {
    $current = Get-ProcessRecord -ProcessId ([int]$Entry.id)
    if ($null -eq $current -or [string]::IsNullOrWhiteSpace($current.Path)) {
        return $false
    }
    if (-not [string]::Equals($current.Path, [string]$Entry.path, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $false
    }
    if (-not [string]::Equals($current.StartTimeUtc, [string]$Entry.start_time_utc, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $false
    }
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

function Save-LauncherState {
    $state = [pscustomobject]@{
        created_at_utc = [DateTime]::UtcNow.ToString('o')
        processes = @($startedServices.ToArray())
    }
    $state | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $statePath -Encoding UTF8
}

function Stop-TrackedProcesses($Entries) {
    $orderedEntries = @($Entries)
    [array]::Reverse($orderedEntries)
    foreach ($entry in $orderedEntries) {
        if (-not (Test-TrackedProcess $entry)) {
            Write-Host "  SKIPPED $($entry.name): process identity no longer matches its launch record." -ForegroundColor Yellow
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
            if (Get-Process -Id ([int]$entry.id) -ErrorAction SilentlyContinue) {
                Write-Host "  WARNING $($entry.name): process $($entry.id) is still running." -ForegroundColor Yellow
            }
            else {
                Write-Host "  STOPPED $($entry.name) (PID $($entry.id))." -ForegroundColor Green
            }
        }
        catch {
            Write-Host "  ERROR stopping $($entry.name): $($_.Exception.Message)" -ForegroundColor Red
        }
    }
}

function Show-ProcessLog([string]$Name) {
    $entry = $startedServices | Where-Object { $_.name -eq $Name } | Select-Object -First 1
    if ($null -eq $entry) { return }
    foreach ($logPath in @($entry.stdout_log, $entry.stderr_log)) {
        if (Test-Path -LiteralPath $logPath -PathType Leaf) {
            Write-Host "--- $Name log: $logPath ---" -ForegroundColor DarkGray
            Get-Content -LiteralPath $logPath -Tail 20
        }
    }
}

function Wait-ForHttp([string]$Name, [string]$Uri, [int]$TimeoutSeconds, [scriptblock]$ValidateResponse) {
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        $entry = $startedServices | Where-Object { $_.name -eq $Name } | Select-Object -First 1
        if ($null -eq $entry -or -not (Test-TrackedProcess $entry)) {
            Show-ProcessLog -Name $Name
            throw "$Name exited during startup. See the log output above."
        }
        try {
            $response = Invoke-RestMethod -Uri $Uri -TimeoutSec 3
            if (& $ValidateResponse $response) { return }
        }
        catch {
            # The app may still be importing modules or binding its port.
        }
        Start-Sleep -Seconds 1
    }
    Show-ProcessLog -Name $Name
    throw "$Name did not become healthy within $TimeoutSeconds seconds."
}

Push-Location $repoRoot
try {
    Write-Host 'Forever BIS Development Environment' -ForegroundColor Cyan

    $docker = Get-DockerExecutable
    $dockerVersion = & $docker info --format '{{.ServerVersion}}' 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw 'Docker Desktop is not running or the Docker daemon is unavailable. Start Docker Desktop manually, wait for it to finish starting, then retry .\dev.ps1.'
    }
    Write-Host "Docker: AVAILABLE (Engine $dockerVersion)" -ForegroundColor Green

    $python = Join-Path $repoRoot '.venv\Scripts\python.exe'
    $viteScript = Join-Path $repoRoot 'frontend\node_modules\vite\bin\vite.js'
    if (-not (Test-Path -LiteralPath '.env' -PathType Leaf)) {
        throw 'Missing .env. Create it once with: Copy-Item .env.example .env'
    }
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        throw 'Backend virtual environment is missing. Follow the README first-time setup to create .venv and install dependencies.'
    }
    if (-not (Test-Path -LiteralPath $viteScript -PathType Leaf)) {
        throw 'Frontend dependencies are missing. Run npm ci from the frontend directory, then retry.'
    }
    if (Test-Path -LiteralPath $statePath -PathType Leaf) {
        $oldState = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
        $validOld = @($oldState.processes | Where-Object { Test-TrackedProcess $_ })
        if ($validOld.Count -gt 0) {
            throw "Managed app process(es) are already running ($($validOld.name -join ', ')). Run .\stop-dev.ps1 before restarting."
        }
        $liveOld = @($oldState.processes | Where-Object { Get-Process -Id ([int]$_.id) -ErrorAction SilentlyContinue })
        if ($liveOld.Count -eq 0) {
            Remove-Item -LiteralPath $statePath -Force
        }
        else {
            Write-Host 'A recorded PID is still in use but its identity does not match. It will not be stopped; port checks will fail safely if it owns a service port.' -ForegroundColor Yellow
        }
    }

    foreach ($port in @(8000, 5173)) {
        $owners = @(Get-ListeningProcessIds -Port $port)
        if ($owners.Count -gt 0) {
            $details = foreach ($ownerId in $owners) {
                $owner = Get-Process -Id ([int]$ownerId) -ErrorAction SilentlyContinue
                if ($null -ne $owner) { "$($owner.ProcessName) (PID $ownerId)" } else { "PID $ownerId" }
            }
            throw "Port $port is already occupied by $($details -join ', '). No process was stopped; free the port or use the existing service."
        }
    }
    $node = Get-NodeExecutable

    Write-Host 'PostgreSQL: starting existing Compose service db...' -ForegroundColor Gray
    & $docker compose --env-file .env up -d db
    if ($LASTEXITCODE -ne 0) { throw 'Docker Compose could not start the db service.' }

    $healthy = $false
    $deadline = [DateTime]::UtcNow.AddSeconds($PostgresTimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        $containerId = (& $docker compose --env-file .env ps -q db 2>$null | Select-Object -First 1).Trim()
        if ($containerId) {
            $health = (& $docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' $containerId 2>$null | Select-Object -First 1).Trim()
            if ($health -eq 'healthy') { $healthy = $true; break }
            if ($health -eq 'unhealthy' -or $health -eq 'exited') { throw "PostgreSQL container reported '$health'. Existing database volume was left untouched." }
        }
        Start-Sleep -Seconds 2
    }
    if (-not $healthy) { throw "PostgreSQL did not report healthy within $PostgresTimeoutSeconds seconds. The existing volume was not removed or recreated." }
    Write-Host 'PostgreSQL: HEALTHY' -ForegroundColor Green

    & $python -c "from backend.app.core.config import get_settings; from backend.app.db.session import create_database_engine, check_database_connection; engine=create_database_engine(get_settings()); check_database_connection(engine); engine.dispose(); print('DATABASE_OK')"
    if ($LASTEXITCODE -ne 0) { throw 'SQLAlchemy could not verify PostgreSQL connectivity using the existing .env configuration.' }
    Write-Host 'Database connection: VERIFIED' -ForegroundColor Green

    New-Item -ItemType Directory -Path $runtimeDirectory -Force | Out-Null
    $pythonLog = Join-Path $runtimeDirectory 'fastapi.stdout.log'
    $pythonErrorLog = Join-Path $runtimeDirectory 'fastapi.stderr.log'
    $fastApiProcess = Start-Process -FilePath $python -ArgumentList @('-m', 'uvicorn', 'backend.app.main:app', '--host', '127.0.0.1', '--port', '8000') -WorkingDirectory $repoRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput $pythonLog -RedirectStandardError $pythonErrorLog
    Start-Sleep -Milliseconds 250
    $fastApiIdentity = Get-ProcessRecord -ProcessId $fastApiProcess.Id
    if ($null -eq $fastApiIdentity) { throw 'Could not verify FastAPI process identity after startup.' }
    $startedServices.Add([pscustomobject]@{ name = 'FastAPI'; id = $fastApiIdentity.Id; start_time_utc = $fastApiIdentity.StartTimeUtc; path = $fastApiIdentity.Path; command_marker = 'uvicorn backend.app.main:app'; stdout_log = $pythonLog; stderr_log = $pythonErrorLog })
    Save-LauncherState
    Wait-ForHttp -Name 'FastAPI' -Uri 'http://127.0.0.1:8000/api/v1/health' -TimeoutSeconds $ApplicationTimeoutSeconds -ValidateResponse { param($response) $response.status -eq 'healthy' -and $response.database -eq 'healthy' }
    $fastApiListeners = @(Get-ListeningProcessIds -Port 8000)
    foreach ($listenerId in $fastApiListeners) {
        if ([int]$listenerId -eq $fastApiIdentity.Id) { continue }
        if (-not (Test-IsDescendantProcess -ProcessId ([int]$listenerId) -AncestorProcessId $fastApiIdentity.Id)) {
            throw "FastAPI port 8000 is owned by an unexpected process (PID $listenerId); it will not be stopped."
        }
        $workerIdentity = Get-ProcessRecord -ProcessId ([int]$listenerId)
        if ($null -eq $workerIdentity) { throw 'Could not verify the FastAPI worker process identity.' }
        $startedServices.Add([pscustomobject]@{ name = 'FastAPI worker'; id = $workerIdentity.Id; start_time_utc = $workerIdentity.StartTimeUtc; path = $workerIdentity.Path; command_marker = 'uvicorn backend.app.main:app'; stdout_log = $pythonLog; stderr_log = $pythonErrorLog })
    }
    Save-LauncherState
    Write-Host 'FastAPI: RUNNING (database healthy)' -ForegroundColor Green

    $viteLog = Join-Path $runtimeDirectory 'vite.stdout.log'
    $viteErrorLog = Join-Path $runtimeDirectory 'vite.stderr.log'
    $viteArguments = '"{0}" --host 127.0.0.1 --port 5173 --strictPort' -f $viteScript
    $viteProcess = Start-Process -FilePath $node -ArgumentList $viteArguments -WorkingDirectory (Join-Path $repoRoot 'frontend') -WindowStyle Hidden -PassThru -RedirectStandardOutput $viteLog -RedirectStandardError $viteErrorLog
    Start-Sleep -Milliseconds 250
    $viteIdentity = Get-ProcessRecord -ProcessId $viteProcess.Id
    if ($null -eq $viteIdentity) { throw 'Could not verify Vite process identity after startup.' }
    $startedServices.Add([pscustomobject]@{ name = 'Vite'; id = $viteIdentity.Id; start_time_utc = $viteIdentity.StartTimeUtc; path = $viteIdentity.Path; command_marker = 'vite.js'; stdout_log = $viteLog; stderr_log = $viteErrorLog })
    Save-LauncherState
    Wait-ForHttp -Name 'Vite' -Uri 'http://127.0.0.1:5173/' -TimeoutSeconds $ApplicationTimeoutSeconds -ValidateResponse { param($response) $null -ne $response }
    Write-Host 'Vite: RUNNING' -ForegroundColor Green

    if (-not $NoBrowser) {
        try { Start-Process 'http://localhost:5173' | Out-Null }
        catch { Write-Host "Browser could not be opened automatically: $($_.Exception.Message)" -ForegroundColor Yellow }
    }

    Write-Host ''
    Write-Host 'Forever BIS Development Environment' -ForegroundColor Cyan
    Write-Host 'PostgreSQL: HEALTHY' -ForegroundColor Green
    Write-Host 'FastAPI:    RUNNING' -ForegroundColor Green
    Write-Host 'Vite:       RUNNING' -ForegroundColor Green
    Write-Host ''
    Write-Host 'Frontend: http://localhost:5173'
    Write-Host 'API Docs: http://localhost:8000/docs'
    Write-Host 'Stop app services with: .\stop-dev.ps1'
    Write-Host 'PostgreSQL remains running when app services are stopped.'
}
catch {
    Write-Host "Startup failed: $($_.Exception.Message)" -ForegroundColor Red
    if ($startedServices.Count -gt 0) {
        Write-Host 'Cleaning up only app processes started by this invocation...' -ForegroundColor Yellow
        Stop-TrackedProcesses -Entries $startedServices.ToArray()
    }
    if ($startedServices.Count -gt 0 -and (Test-Path -LiteralPath $statePath -PathType Leaf)) {
        $survivors = @($startedServices | Where-Object { Test-TrackedProcess $_ })
        if ($survivors.Count -eq 0) { Remove-Item -LiteralPath $statePath -Force }
    }
    exit 1
}
finally {
    Pop-Location
}
