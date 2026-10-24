@echo off
chcp 65001 >nul
echo ============================================================================
echo   TRIEN KHAI MIEN PHI 100%% (0 DONG - 16GB RAM) LEN HUGGING FACE SPACES
echo   Du an: Tool Lyric by lekimlamcode (Giu nguyen 100%% code goc)
echo ============================================================================
echo.
echo Huong dan nhanh truoc khi chay:
echo   1. Tao Space moi tai: https://huggingface.co/new-space
echo      - Chon SDK: Docker (Blank)
echo      - Chon Hardware: CPU basic (2 vCPU - 16GB RAM - FREE)
echo   2. Lay Write Token tai: https://huggingface.co/settings/tokens
echo   3. Dam bao app_port o dau file README.md khop voi PORT trong Dockerfile (8080 hoac 7860)
echo.

set /p HF_USER="Nhap Hugging Face Username cua ban: "
if "%HF_USER%"=="" (
    echo [LOI] Ban chua nhap Username!
    pause
    exit /b 1
)

set /p HF_SPACE="Nhap Ten Space (vi du: tool-lyric-lekimlamcode): "
if "%HF_SPACE%"=="" (
    echo [LOI] Ban chua nhap Ten Space!
    pause
    exit /b 1
)

set /p HF_TOKEN="Nhap Hugging Face Write Token (hf_...): "
if "%HF_TOKEN%"=="" (
    echo [LOI] Ban chua nhap Token!
    pause
    exit /b 1
)

set HF_REMOTE=https://%HF_USER%:%HF_TOKEN%@huggingface.co/spaces/%HF_USER%/%HF_SPACE%

echo.
echo [INFO] Dang cau hinh Git remote va day du an len Hugging Face Spaces...
git remote remove hf_space 2>nul
git remote add hf_space %HF_REMOTE%

for /f "tokens=*" %%i in ('git rev-parse --abbrev-ref HEAD') do set CURRENT_BRANCH=%%i
echo [INFO] Dang day nhanh %CURRENT_BRANCH% -> main tren Space %HF_USER%/%HF_SPACE%...
git push hf_space %CURRENT_BRANCH%:main --force

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================================================
    echo [THANH CONG] Da day du an len Hugging Face Spaces!
    echo - Xem qua trinh build tai: https://huggingface.co/spaces/%HF_USER%/%HF_SPACE%
    echo - Link Web truc tiep sau khi Running: https://%HF_USER%-%HF_SPACE%.hf.space
    echo ============================================================================
) else (
    echo.
    echo [LOI] Khong the push len Hugging Face Spaces. Vui long kiem tra lai Username, Ten Space hoac Token.
)

git remote remove hf_space 2>nul
pause
