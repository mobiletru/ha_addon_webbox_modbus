param(
    [switch]$DebugLog
)

$ErrorActionPreference = "Stop"
$AddonRoot = Join-Path $PSScriptRoot "webbox_modbus"
Set-Location $AddonRoot

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

& .\.venv\Scripts\Activate.ps1
pip install -q -r requirements.txt

$env:WEBBOX_DATA_DIR = Join-Path $PSScriptRoot "data"
$env:MODBUS_PROFILE_PATH = Join-Path $AddonRoot "profiles\SI6048MBP.xml"
if ($DebugLog) { $env:WEBBOX_LOG_LEVEL = "debug" }

Write-Host "Starting dashboard at http://127.0.0.1:8765"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8765 --app-dir $AddonRoot
