# 🌐 Share Tool Lyric by lekimlamcode to the Public Web via Free Cloudflare Tunnel
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$CloudflaredExe = Join-Path $ScriptDir "cloudflared.exe"

if (!(Test-Path $CloudflaredExe)) {
    Write-Host "==========================================================" -ForegroundColor Cyan
    Write-Host "[INFO] Đang tải công cụ Cloudflare Tunnel (miễn phí, ~20MB)..." -ForegroundColor Yellow
    Write-Host "==========================================================" -ForegroundColor Cyan
    $DownloadUrl = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
    Invoke-WebRequest -Uri $DownloadUrl -OutFile $CloudflaredExe
    Write-Host "[INFO] Tải thành công!" -ForegroundColor Green
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "🌐 Đang mở cổng kết nối Tool Lyric by lekimlamcode qua Cloudflare Tunnel..." -ForegroundColor Green
Write-Host "   Sau vài giây, bạn sẽ nhận được đường link HTTPS công khai:" -ForegroundColor Yellow
Write-Host "   Ví dụ: https://xxxx.trycloudflare.com" -ForegroundColor Cyan
Write-Host "   Bất kỳ ai (hoặc điện thoại) cũng có thể truy cập link này!" -ForegroundColor Green
Write-Host "   Nhấn Ctrl+C để đóng chia sẻ web khi không dùng nữa." -ForegroundColor Gray
Write-Host "==========================================================" -ForegroundColor Cyan

& $CloudflaredExe tunnel --url http://127.0.0.1:7864

