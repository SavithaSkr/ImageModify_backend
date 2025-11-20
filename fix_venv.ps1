Write-Host "===== ImageModify Backend VENV FIX SCRIPT =====" -ForegroundColor Cyan

# Move to project root (folder where fix_venv.ps1 is placed)
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $SCRIPT_DIR

Write-Host "Project directory: $SCRIPT_DIR" -ForegroundColor Yellow

# ----------------------------------------------------
# 1. Remove existing .venv
# ----------------------------------------------------
if (Test-Path ".\.venv") {
    Write-Host "Deleting old virtual environment..." -ForegroundColor Magenta
    Remove-Item -Recurse -Force ".\.venv"
} else {
    Write-Host "No old .venv found. Continuing..." -ForegroundColor DarkYellow
}

# ----------------------------------------------------
# 2. Create new .venv with Python 3.12
# ----------------------------------------------------
Write-Host "Creating new Python 3.12 virtual environment..." -ForegroundColor Green
py -3.12 -m venv .venv

# ----------------------------------------------------
# 3. Activate .venv
# ----------------------------------------------------
Write-Host "Activating virtual environment..." -ForegroundColor Green
& ".\.venv\Scripts\Activate.ps1"

# ----------------------------------------------------
# 4. Upgrade pip inside venv
# ----------------------------------------------------
Write-Host "Upgrading pip..." -ForegroundColor Green
.\.venv\Scripts\python.exe -m pip install --upgrade pip

# ----------------------------------------------------
# 5. Install backend requirements
# ----------------------------------------------------
if (Test-Path ".\requirements.txt") {
    Write-Host "Installing backend requirements..." -ForegroundColor Green
    pip install -r requirements.txt
} else {
    Write-Host "requirements.txt not found!" -ForegroundColor Red
}

# ----------------------------------------------------
# 6. Start Backend Server
# ----------------------------------------------------
Write-Host "Starting backend server at http://127.0.0.1:8000 ..." -ForegroundColor Cyan
uvicorn app.main:app --reload
