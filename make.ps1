param (
    [string]$Target = "help",
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgsList
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (Test-Path "D:\") {
    $env:HF_HOME = "D:\hf_cache"
    $env:TRANSFORMERS_CACHE = "D:\hf_cache"
    $env:TORCH_HOME = "D:\torch_cache"
}

function Show-Help {
    Write-Host "Tool Lyric by lekimlamcode - Makefile Commands (Windows)" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Setup & Installation:" -ForegroundColor Yellow
    Write-Host "  .\make.bat env            Create virtual environment (.venv) or conda"
    Write-Host "  .\make.bat install        Install core dependencies (requirements.txt)"
    Write-Host "  .\make.bat install-dev    Install dev dependencies (testing, linting)"
    Write-Host "  .\make.bat install-ml     Install ML dependencies (demucs, moviepy, etc.)"
    Write-Host "  .\make.bat download-model Download AI model weights from HuggingFace"
    Write-Host ""
    Write-Host "Running:" -ForegroundColor Yellow
    Write-Host "  .\make.bat run            Start FastAPI server (http://127.0.0.1:7864)"
    Write-Host ""
    Write-Host "Development:" -ForegroundColor Yellow
    Write-Host "  .\make.bat test           Run tests"
    Write-Host "  .\make.bat lint           Run code linting (flake8)"
    Write-Host "  .\make.bat format         Format code with black & isort"
    Write-Host "  .\make.bat clean          Clean cache & temporary files"
    Write-Host "  .\make.bat docs           View documentation"
    Write-Host ""
}

function Invoke-Env {
    Write-Host "Setting up Python virtual environment..." -ForegroundColor Green
    Set-Location $ScriptDir
    if (Get-Command conda -ErrorAction SilentlyContinue) {
        Write-Host "Creating conda environment 'lyric_env'..."
        conda env create -f environment.yml -y
        Write-Host "Done! Activate with: conda activate lyric_env" -ForegroundColor Green
    } else {
        Write-Host "Conda not found. Creating Python venv in '.venv'..."
        python -m venv .venv
        Write-Host "Virtual environment created at '.venv'." -ForegroundColor Green
        Write-Host "Activate with: .\.venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    }
}

function Invoke-Install {
    Write-Host "Installing core dependencies..." -ForegroundColor Green
    Set-Location $ScriptDir
    python -m pip install --upgrade pip setuptools wheel
    python -m pip install -r requirements.txt
    Write-Host "Core dependencies installed." -ForegroundColor Green
}

function Invoke-InstallDev {
    Write-Host "Installing dev dependencies..." -ForegroundColor Green
    Set-Location $ScriptDir
    python -m pip install -r requirements-dev.txt
    Write-Host "Dev dependencies installed." -ForegroundColor Green
}

function Invoke-InstallMl {
    Write-Host "Installing ML dependencies..." -ForegroundColor Green
    Set-Location $ScriptDir
    python -m pip install -r requirements-ml.txt
    Write-Host "ML dependencies installed." -ForegroundColor Green
}

function Invoke-DownloadModel {
    Write-Host "Downloading AI model from Hugging Face..." -ForegroundColor Green
    Set-Location $ScriptDir
    python -m pip install -U huggingface-hub
    $modelDir = Join-Path $ScriptDir "models\lyric-alignment"
    if (!(Test-Path $modelDir)) {
        New-Item -ItemType Directory -Path $modelDir -Force | Out-Null
    }
    python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='nguyenvulebinh/lyric-alignment', local_dir=r'$modelDir')"
    Write-Host "Model downloaded to $modelDir" -ForegroundColor Green
}

function Invoke-Run {
    Write-Host "Starting Tool Lyric by lekimlamcode Server..." -ForegroundColor Cyan
    Set-Location $ScriptDir
    $backendFile = Join-Path $ScriptDir "backend\fastapi_app.py"
    $modelsDir = Join-Path $ScriptDir "models\alignment-code"
    
    if (!(Test-Path $modelsDir)) {
        Write-Host "models/alignment-code directory is missing! Restoring..." -ForegroundColor Yellow
        git checkout c66fc6f -- models/alignment-code frontend/static/player.html frontend/static/index.html
    }
    
    Write-Host "   Server:   http://127.0.0.1:7864" -ForegroundColor Green
    Write-Host "   Frontend: http://127.0.0.1:7864/auto" -ForegroundColor Green
    Write-Host "   API Docs: http://127.0.0.1:7864/docs" -ForegroundColor Green
    Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
    Write-Host "================================" -ForegroundColor Gray
    
    $env:PYTHONPATH = "$ScriptDir;$modelsDir"
    python $backendFile
}

function Invoke-Test {
    Set-Location $ScriptDir
    pytest tests/ -v --cov=.
}

function Invoke-Lint {
    Set-Location $ScriptDir
    flake8 backend/ models/alignment-code/ --max-line-length=120
    Write-Host "Linting complete" -ForegroundColor Green
}

function Invoke-Format {
    Set-Location $ScriptDir
    black backend/ models/alignment-code/ --line-length=120
    isort backend/ models/alignment-code/
    Write-Host "Code formatted" -ForegroundColor Green
}

function Invoke-Clean {
    Set-Location $ScriptDir
    Write-Host "Cleaning pycache and temporary files..." -ForegroundColor Yellow
    Get-ChildItem -Path $ScriptDir -Recurse -Filter "__pycache__" -Directory -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
    Get-ChildItem -Path $ScriptDir -Recurse -Filter "*.pyc" -File -ErrorAction SilentlyContinue | Remove-Item -Force
    Get-ChildItem -Path $ScriptDir -Recurse -Filter ".pytest_cache" -Directory -ErrorAction SilentlyContinue | Remove-Item -Force
    Write-Host "Cleaned up" -ForegroundColor Green
}

function Invoke-Docs {
    Set-Location $ScriptDir
    $docFile = Join-Path $ScriptDir "docs\INSTALLATION.md"
    if (Test-Path $docFile) {
        Start-Process $docFile
    } else {
        Get-Content (Join-Path $ScriptDir "README.md")
    }
}

switch ($Target.ToLower()) {
    "help"           { Show-Help }
    "env"            { Invoke-Env }
    "install"        { Invoke-Install }
    "install-dev"    { Invoke-InstallDev }
    "install-ml"     { Invoke-InstallMl }
    "download-model" { Invoke-DownloadModel }
    "run"            { Invoke-Run }
    "test"           { Invoke-Test }
    "lint"           { Invoke-Lint }
    "format"         { Invoke-Format }
    "clean"          { Invoke-Clean }
    "docs"           { Invoke-Docs }
    default {
        Write-Host "Unknown command: $Target" -ForegroundColor Red
        Show-Help
    }
}

