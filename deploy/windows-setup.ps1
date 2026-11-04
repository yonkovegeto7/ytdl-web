# ============================================================
#  YouTube Downloader - one-shot deploy on a WINDOWS VPS
# ============================================================
#  Run this in PowerShell **as Administrator** on the server,
#  after copying the webapp folder there, e.g. to C:\ytdl
#
#  Normal install (no domain, HTTP on port 7860):
#     cd C:\ytdl
#     Set-ExecutionPolicy Bypass -Scope Process -Force
#     .\deploy\windows-setup.ps1
#
#  With a domain (free HTTPS via Caddy):
#     .\deploy\windows-setup.ps1 -Domain "mytube.duckdns.org" -Email "me@mail.com"
#
#  What it does:
#    * installs Python 3.12, ffmpeg and Deno (winget)
#    * creates a virtualenv and installs the requirements
#    * opens the firewall port
#    * registers two auto-start Scheduled Tasks (app + optional HTTPS proxy)
# ============================================================

param(
  [string]$Domain = "",
  [string]$Email  = "admin@example.com",
  [int]$Port      = 7860,
  [int]$Concurrent = 10,
  [int]$Threads   = 64,
  [int]$StorageMb = 60000
)

$ErrorActionPreference = "Stop"
$AppDir = Split-Path -Parent $PSScriptRoot
$TaskApp = "YTDL-Web"
$TaskProxy = "YTDL-HTTPS"

function Info($m) { Write-Host "`n==> $m" -ForegroundColor Cyan }
function Fail($m) { Write-Host "!!  $m" -ForegroundColor Red; exit 1 }

# ---------------------------------------------------------------- checks ----
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) { Fail "Run PowerShell as Administrator." }
if (-not (Test-Path (Join-Path $AppDir "app.py"))) { Fail "app.py not found in $AppDir - copy the webapp folder there first." }

Info "Installing winget packages (Python, FFmpeg)"
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
  Fail "winget is missing. Install 'App Installer' from the Microsoft Store, then run this script again."
}

function Winget-Install($id) {
  winget install --id $id --silent --accept-package-agreements --accept-source-agreements --disable-interactivity 2>$null | Out-Null
}
Winget-Install "Python.Python.3.12"
Winget-Install "Gyan.FFmpeg"

# refresh PATH for the current session
$machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
$userPath    = [Environment]::GetEnvironmentVariable("Path", "User")
$env:Path    = "$machinePath;$userPath"

$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $python) { Fail "Python was not found after install. Reboot the VPS and run the script again." }

Info "Installing Deno (needed by yt-dlp for YouTube signatures)"
try {
  Invoke-RestMethod https://deno.land/install.ps1 | Invoke-Expression
} catch {
  Write-Host "   Deno install failed - the app still runs, but some videos may show fewer formats."
}
$denoDir = Join-Path $env:USERPROFILE ".deno\bin"
if (Test-Path $denoDir) { $env:Path = "$denoDir;$env:Path" }

Info "Creating the virtualenv and installing Python packages"
Set-Location $AppDir
if (-not (Test-Path ".venv")) { & $python -m venv .venv }
$venvPy = Join-Path $AppDir ".venv\Scripts\python.exe"
& $venvPy -m pip install --upgrade pip | Out-Null
& $venvPy -m pip install -r requirements.txt

# ------------------------------------------------------------- settings ----
Info "Writing server settings"
$envFile = Join-Path $AppDir ".env"
$settings = @(
  "PORT=$Port",
  "MAX_CONCURRENT=$Concurrent",
  "MAX_QUEUE=300",
  "FILE_TTL=0",
  "MAX_STORAGE_MB=$StorageMb",
  "PURGE_ON_START=1"
)
Set-Content -Path $envFile -Value ($settings -join "`r`n") -Encoding ASCII

# make the same values available to the service at machine level
[Environment]::SetEnvironmentVariable("PORT", "$Port", "Machine")
[Environment]::SetEnvironmentVariable("MAX_CONCURRENT", "$Concurrent", "Machine")
[Environment]::SetEnvironmentVariable("MAX_QUEUE", "300", "Machine")
[Environment]::SetEnvironmentVariable("FILE_TTL", "0", "Machine")
[Environment]::SetEnvironmentVariable("MAX_STORAGE_MB", "$StorageMb", "Machine")
[Environment]::SetEnvironmentVariable("PURGE_ON_START", "1", "Machine")

Info "Opening firewall port $Port"
New-NetFirewallRule -DisplayName "YTDL Web $Port" -Direction Inbound -Protocol TCP `
  -LocalPort $Port -Action Allow -ErrorAction SilentlyContinue | Out-Null
if ($Domain) {
  New-NetFirewallRule -DisplayName "YTDL HTTP 80" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow -ErrorAction SilentlyContinue | Out-Null
  New-NetFirewallRule -DisplayName "YTDL HTTPS 443" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow -ErrorAction SilentlyContinue | Out-Null
}

# --------------------------------------------------------------- 1. app ----
Info "Registering the app as an auto-start Scheduled Task"
$waitress = Join-Path $AppDir ".venv\Scripts\waitress-serve.exe"
$appCmd = "`"$waitress`" --listen=0.0.0.0:$Port --threads=$Threads --channel-timeout=1200 app:app"

schtasks /Delete /TN $TaskApp /F 2>$null | Out-Null
schtasks /Create /TN $TaskApp /TR "cmd /c cd /d `"$AppDir`" && $appCmd" `
  /SC ONSTART /RU "SYSTEM" /RL HIGHEST /F | Out-Null
schtasks /Run /TN $TaskApp | Out-Null

Start-Sleep -Seconds 6
try {
  $h = Invoke-RestMethod "http://127.0.0.1:$Port/healthz" -TimeoutSec 10
  Info "App is healthy: $($h | ConvertTo-Json -Compress)"
} catch {
  Write-Host "!!  The app did not answer yet. Check: schtasks /query /tn $TaskApp" -ForegroundColor Yellow
}

# ------------------------------------------------------------- 2. HTTPS ----
if ($Domain) {
  Info "Setting up Caddy for https://$Domain"
  $caddyDir = Join-Path $AppDir "caddy"
  New-Item -ItemType Directory -Force -Path $caddyDir | Out-Null
  $caddyExe = Join-Path $caddyDir "caddy.exe"
  if (-not (Test-Path $caddyExe)) {
    Invoke-WebRequest "https://caddyserver.com/api/download?os=windows&arch=amd64" -OutFile $caddyExe
  }

  $caddyfile = @"
{
  email $Email
}
$Domain {
    encode gzip zstd
    reverse_proxy 127.0.0.1:$Port {
        transport http {
            read_timeout 20m
            write_timeout 20m
        }
    }
}
"@
  Set-Content -Path (Join-Path $caddyDir "Caddyfile") -Value $caddyfile -Encoding ASCII

  schtasks /Delete /TN $TaskProxy /F 2>$null | Out-Null
  schtasks /Create /TN $TaskProxy /TR "cmd /c cd /d `"$caddyDir`" && `"$caddyExe`" run --config `"$caddyDir\Caddyfile`"" `
    /SC ONSTART /RU "SYSTEM" /RL HIGHEST /F | Out-Null
  schtasks /Run /TN $TaskProxy | Out-Null

  Write-Host ""
  Write-Host "  HTTPS is being issued for https://$Domain" -ForegroundColor Green
  Write-Host "  Make sure the domain's A record points to this VPS public IP." -ForegroundColor Green
} else {
  $ip = (Invoke-RestMethod "https://api.ipify.org" -TimeoutSec 10)
  Write-Host ""
  Write-Host "  App is public now:  http://${ip}:$Port" -ForegroundColor Green
  Write-Host "  For a domain + free HTTPS, re-run:" -ForegroundColor Yellow
  Write-Host "     .\deploy\windows-setup.ps1 -Domain your.domain -Email you@mail.com" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Done." -ForegroundColor Green
Write-Host "  Health : http://127.0.0.1:$Port/healthz"
Write-Host "  Tasks  : schtasks /query /tn $TaskApp"
Write-Host "  Logs   : Get-Content $AppDir\server.log -Tail 50  (if you enable logging)"
