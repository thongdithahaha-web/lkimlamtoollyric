# 🎤 Auto Lyrics Align - Windows PowerShell Launcher
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Set-Location $PSScriptRoot

if (Test-Path "D:\") {
    $env:HF_HOME = "D:\hf_cache"
    $env:TRANSFORMERS_CACHE = "D:\hf_cache"
    $env:TORCH_HOME = "D:\torch_cache"
}
$env:PYTHONIOENCODING = "utf-8"

# Free port 7864 if in use
$conn = Get-NetTCPConnection -LocalPort 7864 -ErrorAction SilentlyContinue
if ($conn) {
    foreach ($c in $conn) {
        Write-Host "[INFO] Giải phóng cổng 7864 (PID: $($c.OwningProcess))..." -ForegroundColor Yellow
        Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "🎤 Tool Lyric by lekimlamcode" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "   Web App:  http://127.0.0.1:7864/auto" -ForegroundColor Green
Write-Host "   API Docs: http://127.0.0.1:7864/docs" -ForegroundColor Green
Write-Host "Nhấn Ctrl+C để dừng server" -ForegroundColor Yellow
Write-Host "===================================================" -ForegroundColor Gray

# Open browser
Start-Process "http://127.0.0.1:7864/auto"

python backend\fastapi_app.py
