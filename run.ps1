# -------------------------------
# run.ps1
# Full environment reset + run
# -------------------------------

Write-Host "🧹 Cleaning old virtual environments..." -ForegroundColor Yellow

# Remove old venv folders if exist
if (Test-Path ".\.venv") { Remove-Item -Recurse -Force .\.venv }
if (Test-Path ".\venv") { Remove-Item -Recurse -Force .\venv }

Write-Host "🐍 Checking Python installation..." -ForegroundColor Cyan
$python = (Get-Command python -ErrorAction SilentlyContinue)

if (-not $python) {
    Write-Host "❌ Python not found. Install Python 3.10+ from python.org" -ForegroundColor Red
    exit
}

Write-Host "⚙️ Creating fresh virtual environment..." -ForegroundColor Cyan
python -m venv .venv

Write-Host "🔑 Activating environment..." -ForegroundColor Cyan
.\.venv\Scripts\Activate.ps1

Write-Host "📦 Installing dependencies..." -ForegroundColor Magenta
pip install --upgrade pip
pip install -r requirements.txt

Write-Host "🚀 Starting FastAPI backend..." -ForegroundColor Green
uvicorn app.main:app --reload
