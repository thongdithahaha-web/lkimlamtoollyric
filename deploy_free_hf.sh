#!/usr/bin/env bash
set -e

echo "============================================================================"
echo "  TRIEN KHAI MIEN PHI 100% (0 DONG - 16GB RAM) LEN HUGGING FACE SPACES"
echo "  Du an: Tool Lyric by lekimlamcode (Giu nguyen 100% code goc)"
echo "============================================================================"
echo ""
echo "Huong dan nhanh truoc khi chay:"
echo "  1. Tao Space moi tai: https://huggingface.co/new-space"
echo "     - Chon SDK: Docker (Blank)"
echo "     - Chon Hardware: CPU basic (2 vCPU - 16GB RAM - FREE)"
echo "  2. Lay Write Token tai: https://huggingface.co/settings/tokens"
echo "  3. Dam bao app_port o dau file README.md khop voi PORT trong Dockerfile (8080 hoac 7860)"
echo ""

read -r -p "Nhap Hugging Face Username cua ban: " HF_USER
if [ -z "$HF_USER" ]; then
  echo "[LOI] Ban chua nhap Username!"
  exit 1
fi

read -r -p "Nhap Ten Space (vi du: tool-lyric-lekimlamcode): " HF_SPACE
if [ -z "$HF_SPACE" ]; then
  echo "[LOI] Ban chua nhap Ten Space!"
  exit 1
fi

read -r -s -p "Nhap Hugging Face Write Token (hf_...): " HF_TOKEN
echo ""
if [ -z "$HF_TOKEN" ]; then
  echo "[LOI] Ban chua nhap Token!"
  exit 1
fi

HF_REMOTE="https://${HF_USER}:${HF_TOKEN}@huggingface.co/spaces/${HF_USER}/${HF_SPACE}"
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

echo "[INFO] Dang day nhanh ${CURRENT_BRANCH} -> main tren Space ${HF_USER}/${HF_SPACE}..."
git remote remove hf_space 2>/dev/null || true
git remote add hf_space "$HF_REMOTE"

if git push hf_space "${CURRENT_BRANCH}:main" --force; then
  echo ""
  echo "============================================================================"
  echo "[THANH CONG] Da day du an len Hugging Face Spaces!"
  echo "- Xem qua trinh build tai: https://huggingface.co/spaces/${HF_USER}/${HF_SPACE}"
  echo "- Link Web truc tiep sau khi Running: https://${HF_USER}-${HF_SPACE}.hf.space"
  echo "============================================================================"
else
  echo ""
  echo "[LOI] Khong the push len Hugging Face Spaces. Vui long kiem tra lai thong tin."
fi

git remote remove hf_space 2>/dev/null || true
