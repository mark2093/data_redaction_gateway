# Quick Start Script for PII/PCI Data Redaction Gateway
# Run this script to set up and test the application

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PII/PCI Data Redaction Gateway" -ForegroundColor Cyan
Write-Host "Quick Start Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python version
Write-Host "1. Checking Python version..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
Write-Host "   $pythonVersion" -ForegroundColor Green

# Create virtual environment if it doesn't exist
if (-not (Test-Path "venv")) {
    Write-Host ""
    Write-Host "2. Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    Write-Host "   Virtual environment created" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "2. Virtual environment already exists" -ForegroundColor Green
}

# Activate virtual environment
Write-Host ""
Write-Host "3. Activating virtual environment..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1
Write-Host "   Virtual environment activated" -ForegroundColor Green

# Install dependencies
Write-Host ""
Write-Host "4. Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt --quiet
Write-Host "   Dependencies installed" -ForegroundColor Green

# Download spaCy model
Write-Host ""
Write-Host "5. Downloading spaCy model..." -ForegroundColor Yellow
python -m spacy download en_core_web_sm --quiet
Write-Host "   spaCy model downloaded" -ForegroundColor Green

# Copy .env file if it doesn't exist
if (-not (Test-Path ".env")) {
    Write-Host ""
    Write-Host "6. Creating .env file..." -ForegroundColor Yellow
    Copy-Item ".env.sample" ".env"
    Write-Host "   .env file created" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "6. .env file already exists" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Start the server:" -ForegroundColor White
Write-Host "   python -m src.cli serve --port 8000 --reload" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. In a new terminal, run the data stream simulator:" -ForegroundColor White
Write-Host "   .\venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host "   python utils/data_stream_simulator.py --mode mixed --count 10" -ForegroundColor Cyan
Write-Host ""
Write-Host "3. View API documentation:" -ForegroundColor White
Write-Host "   http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "4. Check health:" -ForegroundColor White
Write-Host "   python -m src.cli health" -ForegroundColor Cyan
Write-Host ""
Write-Host "5. View metrics:" -ForegroundColor White
Write-Host "   python -m src.cli metrics" -ForegroundColor Cyan
Write-Host ""

Write-Host "For more information, see USAGE_GUIDE.md" -ForegroundColor Yellow
Write-Host ""
