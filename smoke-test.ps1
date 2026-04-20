$ErrorActionPreference = "Stop"

$workspaceRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "== MyWorkspace Smoke Test ==" -ForegroundColor Cyan

function Test-PortOpen {
    param(
        [Parameter(Mandatory = $true)][int]$Port
    )

    $connection = Test-NetConnection -ComputerName "localhost" -Port $Port -WarningAction SilentlyContinue
    return [bool]$connection.TcpTestSucceeded
}

function Wait-ForPort {
    param(
        [Parameter(Mandatory = $true)][int]$Port,
        [Parameter(Mandatory = $true)][string]$ServiceName,
        [int]$TimeoutSeconds = 90
    )

    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    while ($stopwatch.Elapsed.TotalSeconds -lt $TimeoutSeconds) {
        if (Test-PortOpen -Port $Port) {
            Write-Host "$ServiceName is reachable on port $Port." -ForegroundColor Green
            return
        }
        Start-Sleep -Seconds 2
    }

    throw "$ServiceName did not start on port $Port within $TimeoutSeconds seconds."
}

function Get-ListeningProcessId {
    param(
        [Parameter(Mandatory = $true)][int]$Port
    )

    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $conn) {
        return $null
    }
    return $conn.OwningProcess
}

function Stop-ProcessOnPort {
    param(
        [Parameter(Mandatory = $true)][int]$Port,
        [Parameter(Mandatory = $true)][string]$ServiceName
    )

    $pidValue = Get-ListeningProcessId -Port $Port
    if ($null -eq $pidValue) {
        return
    }

    try {
        $proc = Get-Process -Id $pidValue -ErrorAction Stop
        Write-Host "Stopping conflicting process on port $Port for $($ServiceName): PID $pidValue ($($proc.ProcessName))" -ForegroundColor Yellow
        Stop-Process -Id $pidValue -Force
        # When uvicorn is started with --reload, a parent process may survive and respawn children.
        # Kill any remaining python processes bound to the same uvicorn port command line.
        $matchingPython = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue |
            Where-Object {
                $_.CommandLine -and
                $_.CommandLine -match "uvicorn" -and
                $_.CommandLine -match "--port\s+$Port(\s|$)"
            }
        foreach ($pyProc in $matchingPython) {
            if ($pyProc.ProcessId -ne $pidValue) {
                Write-Host "Stopping related uvicorn process for port ${Port}: PID $($pyProc.ProcessId)" -ForegroundColor Yellow
                Stop-Process -Id $pyProc.ProcessId -Force -ErrorAction SilentlyContinue
            }
        }
        Start-Sleep -Seconds 1
    }
    catch {
        throw "Failed to stop conflicting process on port $Port (PID $pidValue): $($_.Exception.Message)"
    }
}

function Test-ServiceIdentity {
    param(
        [Parameter(Mandatory = $true)][string]$HealthUrl,
        [Parameter(Mandatory = $true)][string]$ExpectedServiceName
    )

    try {
        $response = Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 5
        return ($null -ne $response.service -and ($response.service -eq $ExpectedServiceName))
    }
    catch {
        return $false
    }
}

function Restart-ServiceOnPort {
    param(
        [Parameter(Mandatory = $true)][string]$ServiceName,
        [Parameter(Mandatory = $true)][int]$Port,
        [Parameter(Mandatory = $true)][string]$Command,
        [Parameter(Mandatory = $true)][string]$HealthUrl,
        [Parameter(Mandatory = $true)][string]$ExpectedHealthService
    )

    if (Test-PortOpen -Port $Port) {
        Write-Host "$ServiceName already running on port $Port. Restarting it..." -ForegroundColor Yellow
        Stop-ProcessOnPort -Port $Port -ServiceName $ServiceName
    }

    Write-Host "Starting $ServiceName in a new PowerShell window..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-ExecutionPolicy", "Bypass",
        "-Command", $Command
    ) | Out-Null

    Wait-ForPort -Port $Port -ServiceName $ServiceName
    if (-not (Test-ServiceIdentity -HealthUrl $HealthUrl -ExpectedServiceName $ExpectedHealthService)) {
        throw "$ServiceName started on port $Port but health endpoint does not match expected service '$ExpectedHealthService'."
    }
}

function Invoke-JsonPost {
    param(
        [Parameter(Mandatory = $true)][string]$Uri,
        [Parameter(Mandatory = $true)][object]$Body
    )

    return Invoke-RestMethod `
        -Uri $Uri `
        -Method POST `
        -ContentType "application/json" `
        -Body ($Body | ConvertTo-Json -Depth 10)
}

function Invoke-JsonPostWithRetry {
    param(
        [Parameter(Mandatory = $true)][string]$Uri,
        [Parameter(Mandatory = $true)][object]$Body,
        [int]$MaxAttempts = 3,
        [int]$RetryDelaySeconds = 2
    )

    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        try {
            return Invoke-JsonPost -Uri $Uri -Body $Body
        }
        catch {
            if ($attempt -eq $MaxAttempts) {
                throw
            }
            Write-Host "Request failed (attempt $attempt/$MaxAttempts): $($_.Exception.Message). Retrying in $RetryDelaySeconds sec..." -ForegroundColor Yellow
            Start-Sleep -Seconds $RetryDelaySeconds
        }
    }
}

function Get-RestErrorDetail {
    param(
        [Parameter(Mandatory = $true)]$ErrorRecord
    )

    $detail = $ErrorRecord.Exception.Message
    try {
        if ($null -ne $ErrorRecord.Exception.Response) {
            $stream = $ErrorRecord.Exception.Response.GetResponseStream()
            if ($null -ne $stream) {
                $reader = New-Object System.IO.StreamReader($stream)
                $body = $reader.ReadToEnd()
                if (-not [string]::IsNullOrWhiteSpace($body)) {
                    $detail = $body
                }
            }
        }
    }
    catch {
        # Fall back to exception message if response body cannot be read.
    }

    return $detail
}

function Set-EnvVariableValue {
    param(
        [Parameter(Mandatory = $true)][string]$EnvFilePath,
        [Parameter(Mandatory = $true)][string]$Key,
        [Parameter(Mandatory = $true)][string]$Value
    )

    $lines = @()
    if (Test-Path $EnvFilePath) {
        $lines = Get-Content -Path $EnvFilePath
    }

    $keyPattern = "^\s*{0}\s*=" -f [regex]::Escape($Key)
    $updated = $false

    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match $keyPattern) {
            $lines[$i] = "$Key=$Value"
            $updated = $true
            break
        }
    }

    if (-not $updated) {
        $lines += "$Key=$Value"
    }

    Set-Content -Path $EnvFilePath -Value $lines -Encoding UTF8
}

function Ensure-LocalhostServiceUrls {
    param(
        [Parameter(Mandatory = $true)][string]$McpPath,
        [Parameter(Mandatory = $true)][string]$SlackPath
    )

    $mcpEnv = Join-Path $McpPath ".env"
    $mcpEnvExample = Join-Path $McpPath ".env.example"
    if (-not (Test-Path $mcpEnv) -and (Test-Path $mcpEnvExample)) {
        Copy-Item $mcpEnvExample $mcpEnv
    }

    $slackEnv = Join-Path $SlackPath ".env"
    $slackEnvExample = Join-Path $SlackPath ".env.example"
    if (-not (Test-Path $slackEnv) -and (Test-Path $slackEnvExample)) {
        Copy-Item $slackEnvExample $slackEnv
    }

    Set-EnvVariableValue -EnvFilePath $mcpEnv -Key "PROJECT_SERVICE_URL" -Value "http://localhost:8001"
    Set-EnvVariableValue -EnvFilePath $mcpEnv -Key "SLACK_SERVICE_URL" -Value "http://localhost:8002"
    Set-EnvVariableValue -EnvFilePath $slackEnv -Key "MCP_SERVER_URL" -Value "http://localhost:8000"

    Write-Host "Updated local service URLs in .env files for non-Docker smoke testing." -ForegroundColor DarkYellow
}

$mcpPath = Join-Path $workspaceRoot "mcp-server"
$projectPath = Join-Path $workspaceRoot "project-service"
$slackPath = Join-Path $workspaceRoot "slack-service"
$frontendPath = Join-Path $workspaceRoot "frontend"

$mcpStartCommand = "Set-Location '$mcpPath'; if (-not (Test-Path '.\.venv\Scripts\Activate.ps1')) { python -m venv .venv }; & '.\.venv\Scripts\Activate.ps1'; pip install -r requirements.txt; if (-not (Test-Path '.env')) { Copy-Item .env.example .env }; uvicorn app.main:app --host 0.0.0.0 --port 8000"
$projectStartCommand = "Set-Location '$projectPath'; if (-not (Test-Path '.\.venv\Scripts\Activate.ps1')) { python -m venv .venv }; & '.\.venv\Scripts\Activate.ps1'; pip install -r requirements.txt; if (-not (Test-Path '.env')) { Copy-Item .env.example .env }; uvicorn app.main:app --host 0.0.0.0 --port 8001"
$slackStartCommand = "Set-Location '$slackPath'; if (-not (Test-Path '.\.venv\Scripts\Activate.ps1')) { python -m venv .venv }; & '.\.venv\Scripts\Activate.ps1'; pip install -r requirements.txt; if (-not (Test-Path '.env')) { Copy-Item .env.example .env }; uvicorn app.main:app --host 0.0.0.0 --port 8002"
$frontendStartCommand = "Set-Location '$frontendPath'; if (-not (Test-Path '.env')) { Copy-Item .env.example .env }; if (-not (Test-Path '.\node_modules')) { npm install }; npm run dev"

# Ensure-LocalhostServiceUrls -McpPath $mcpPath -SlackPath $slackPath

Write-Host "`n[0/4] Restarting services (fresh start)..." -ForegroundColor Yellow
Restart-ServiceOnPort -ServiceName "MCP Server" -Port 8000 -Command $mcpStartCommand -HealthUrl "http://localhost:8000/health" -ExpectedHealthService "mcp-server"
# Restart-ServiceOnPort -ServiceName "Project Service" -Port 8001 -Command $projectStartCommand -HealthUrl "http://localhost:8001/health" -ExpectedHealthService "project-service"
# Restart-ServiceOnPort -ServiceName "Slack Service" -Port 8002 -Command $slackStartCommand -HealthUrl "http://localhost:8002/health" -ExpectedHealthService "slack-service"

if (Test-PortOpen -Port 5173) {
    Write-Host "Frontend (Vite) already running on port 5173. Restarting it..." -ForegroundColor Yellow
    Stop-ProcessOnPort -Port 5173 -ServiceName "Frontend (Vite)"
}

Write-Host "Starting Frontend (Vite) in a new PowerShell window..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-Command", $frontendStartCommand
) | Out-Null
Wait-ForPort -Port 5173 -ServiceName "Frontend (Vite)"

Write-Host "`n[1/4] Health checks..." -ForegroundColor Yellow
$mcpHealth = Invoke-RestMethod "http://localhost:8000/health"
# $projectHealth = Invoke-RestMethod "http://localhost:8001/health"
# $slackHealth = Invoke-RestMethod "http://localhost:8002/health"

$mcpHealth
# $projectHealth
# $slackHealth

Write-Host "`n[2/4] MCP -> Project Service (get_projects)..." -ForegroundColor Yellow
$mcpProjects = Invoke-JsonPostWithRetry -Uri "http://localhost:8000/mcp/tools" -Body @{
    name  = "get_projects"
    input = @{}
}
$mcpProjects
Write-Host "Project count via MCP: $($mcpProjects.data.count)" -ForegroundColor Green

$stepFailures = @()

<# Write-Host "`n[3/4] Slack Service -> MCP -> Project Service (/projects)..." -ForegroundColor Yellow
try {
    $slashResult = Invoke-JsonPostWithRetry -Uri "http://localhost:8002/slack/events" -Body @{
        event_type = "slash_command"
        payload    = @{
            command = "/projects"
        }
    }
    $slashResult
}
catch {
    $detail = Get-RestErrorDetail -ErrorRecord $_
    Write-Host "Step [3/4] failed: $detail" -ForegroundColor Red
    $stepFailures += "Step [3/4] failed: $detail"
}

Write-Host "`n[4/4] MCP -> Slack Service (slack_send_message)..." -ForegroundColor Yellow
try {
    $slackToolResult = Invoke-JsonPostWithRetry -Uri "http://localhost:8000/mcp/tools" -Body @{
        name  = "slack_send_message"
        input = @{
            text = "Smoke test from PowerShell via MCP"
        }
    }
    $slackToolResult
}
catch {
    $detail = Get-RestErrorDetail -ErrorRecord $_
    Write-Host "Step [4/4] failed: $detail" -ForegroundColor Red
    $stepFailures += "Step [4/4] failed: $detail"
} #>

Write-Host "`nSmoke test completed." -ForegroundColor Cyan
Write-Host "Note: If SLACK_WEBHOOK_URL is not configured, Slack delivery may be reported as not delivered (expected)." -ForegroundColor DarkYellow

if ($stepFailures.Count -gt 0) {
    throw ("Smoke test completed with failures:`n - " + ($stepFailures -join "`n - "))
}
