Write-Host "Activating venv and starting Tea Tapestry backend via uvicorn..."

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Run FastAPI server with auto-reload
python -m uvicorn app.main:app --reload

Write-Host "Tea Tapestry backend has been launched."