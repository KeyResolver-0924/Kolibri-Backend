Write-Host "Activating Python virtual environment..." -ForegroundColor Green
& ".\venv\Scripts\Activate.ps1"
Write-Host "Virtual environment activated!" -ForegroundColor Green
Write-Host ""
Write-Host "To start the backend server, run:" -ForegroundColor Yellow
Write-Host "  python main.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "To install dependencies, run:" -ForegroundColor Yellow
Write-Host "  pip install -r requirements.txt" -ForegroundColor Cyan
Write-Host "" 