@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ===================================================
echo 🎤 Tool Lyric by lekimlamcode
echo ===================================================
echo.

:: Set cache to Drive D if available to save Drive C space
if exist D:\ (
    set HF_HOME=D:\hf_cache
    set TRANSFORMERS_CACHE=D:\hf_cache
    set TORCH_HOME=D:\torch_cache
)
set PYTHONIOENCODING=utf-8

:: Free port 7864 if occupied by previous run
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :7864 ^| findstr LISTENING') do (
    echo [INFO] Đang giải phóng cổng 7864 (PID: %%a)...
    taskkill /F /PID %%a >nul 2>&1
)

echo [INFO] Khởi động FastAPI Server...
echo [INFO] Giao diện Web: http://127.0.0.1:7864/auto
echo [INFO] Tài liệu API:  http://127.0.0.1:7864/docs
echo.
echo Nhấn Ctrl+C để dừng server.
echo ===================================================
echo.

:: Tự động mở trình duyệt sau 3 giây
start "" cmd /c "timeout /t 3 /nobreak >nul & start http://127.0.0.1:7864/auto"

:: Chạy server trực tiếp bằng Python
python backend\fastapi_app.py

pause
