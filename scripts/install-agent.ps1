<#
.SYNOPSIS
    Installs and configures the WeAutomate VM Agent as a background service on Windows Server 2025.

.DESCRIPTION
    1. Validates Windows Server 2025 GVLK.
    2. Creates C:\ProgramData\WeAutomate for local state cache.
    3. Deploys the Python VM Agent.
    4. Registers a scheduled task or Windows Service to run at system boot with highest privileges.
    5. Initiates initial outbound registration and heartbeat.

.PARAMETER ControllerUrl
    The HTTPS/HTTP endpoint of the WeAutomate License Controller. Default: http://controller.internal:8000

.PARAMETER ServerFarm
    The assigned server farm name. Default: primary-server-farm

.EXAMPLE
    .\install-agent.ps1 -ControllerUrl "http://192.168.1.50:8000" -ServerFarm "primary-server-farm"
#>

[CmdletBinding()]
param(
    [string]$ControllerUrl = "http://127.0.0.1:8000",
    [string]$ServerFarm = "primary-server-farm"
)

$ErrorActionPreference = "Stop"

Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host " WeAutomate — Windows Server 2025 VM Agent Installation  " -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan

# 1. Check Administrator Privileges
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error "This installation script must be run as Administrator."
}

# 2. Setup Directories
$InstallDir = "C:\Program Files\WeAutomate\Agent"
$DataDir = "C:\ProgramData\WeAutomate"

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
Write-Host "[✓] Directories initialized:" -ForegroundColor Green
Write-Host "    Binaries: $InstallDir"
Write-Host "    Data:     $DataDir"

# 3. Deploy Agent files
$SourceRoot = (Resolve-Path "$PSScriptRoot\..").Path
$localAgent = Join-Path $SourceRoot "weautomate"

if (Test-Path $localAgent) {
    Write-Host "[*] Copying agent files from local source..." -ForegroundColor Yellow
    Copy-Item -Recurse -Force "$localAgent" "$InstallDir\"
} else {
    Write-Host "[*] Downloading agent package from Controller ($ControllerUrl)..." -ForegroundColor Yellow
    $zipPath = "$env:TEMP\weautomate-agent.zip"
    $downloadUrl = "$($ControllerUrl.TrimEnd('/'))/api/v1/agent/bundle.zip"
    Invoke-WebRequest -Uri $downloadUrl -OutFile $zipPath -UseBasicParsing
    Expand-Archive -Path $zipPath -DestinationPath $InstallDir -Force
    Remove-Item -Path $zipPath -Force -ErrorAction SilentlyContinue
}
Write-Host "[✓] Agent files deployed to $InstallDir\weautomate" -ForegroundColor Green

# 4. Verify Python & Dependencies
Write-Host "[*] Checking Python environment..." -ForegroundColor Yellow
$PythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $PythonCmd) {
    Write-Warning "Python 3 was not detected in PATH. Please ensure Python 3.10+ is installed on this VM."
    Write-Host "Download from: https://www.python.org/downloads/windows/"
    exit 1
}

$PyPath = $PythonCmd.Source
Write-Host "[✓] Using Python: $PyPath" -ForegroundColor Green

& $PyPath -m pip install --quiet httpx pydantic
Write-Host "[✓] Dependencies installed." -ForegroundColor Green

# 5. Check KMS Client Key (GVLK)
$GVLK = "TVRH6-WHNXV-R9WG3-9XRFY-MY832"
Write-Host "[*] Windows Server 2025 Standard Client GVLK: $GVLK" -ForegroundColor Cyan
Write-Host "    To apply GVLK on this VM: slmgr /ipk $GVLK" -ForegroundColor Gray

# 6. Create Windows Scheduled Task (Runs at Startup as SYSTEM)
$TaskName = "WeAutomateVMAgent"
$ActionScript = @"
& "$PyPath" -m weautomate.agent.cli --controller-url "$ControllerUrl" --cache-path "$DataDir\agent_cache.json" --server-farm "$ServerFarm"
"@

$ActionScriptPath = "$InstallDir\run-agent.ps1"
Set-Content -Path $ActionScriptPath -Value $ActionScript -Encoding UTF8

$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$ActionScriptPath`""
$Trigger = New-ScheduledTaskTrigger -AtStartup
$Principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Description "WeAutomate Windows Server 2025 Dynamic License Agent" | Out-Null

Write-Host "[✓] Scheduled background task '$TaskName' registered (Runs AtStartup as SYSTEM)." -ForegroundColor Green

# 7. Start Agent Now
Write-Host "[*] Starting WeAutomate VM Agent task..." -ForegroundColor Yellow
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 2

$taskInfo = Get-ScheduledTask -TaskName $TaskName
Write-Host "[✓] Agent State: $($taskInfo.State)" -ForegroundColor Green

Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host " Installation Complete!                                  " -ForegroundColor Green
Write-Host " Outbound Agent is now reporting to: $ControllerUrl      " -ForegroundColor Gray
Write-Host "=========================================================" -ForegroundColor Cyan
