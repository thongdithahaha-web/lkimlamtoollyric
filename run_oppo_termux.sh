#!/usr/bin/env bash
# Script khoi chay Server tren dien thoai OPPO (qua ung dung Termux) - Chi ton ~20-25MB RAM!

echo "======================================================================"
echo "  KHOI CHAY SERVER TREN DIEN THOAI OPPO (SIÊU NHẸ - KHÔNG TRÀN RAM)"
echo "  Du an: Tool Lyric by lekimlamcode"
echo "======================================================================"

PORT="${PORT:-7864}"

if command -v node >/dev/null 2>&1; then
  echo "[OK] Phat hien Node.js! Dang chay server sieu nhe (~25MB RAM) tren cong $PORT..."
  echo "-> Mo trinh duyet tren dien thoai vao: http://127.0.0.1:$PORT"
  PORT="$PORT" node server.mjs
elif command -v python3 >/dev/null 2>&1; then
  echo "[OK] Phat hien Python3! Dang chay server_oppo_lite.py (~20MB RAM) tren cong $PORT..."
  echo "-> Mo trinh duyet tren dien thoai vao: http://127.0.0.1:$PORT"
  PORT="$PORT" python3 server_oppo_lite.py
elif command -v python >/dev/null 2>&1; then
  echo "[OK] Phat hien Python! Dang chay server_oppo_lite.py (~20MB RAM) tren cong $PORT..."
  PORT="$PORT" python server_oppo_lite.py
else
  echo "[!] Tren Termux dien thoai OPPO, hay chay lenh sau de cai Node.js sieu nhe:"
  echo "    pkg update && pkg install nodejs git cloudflared -y"
  exit 1
fi
