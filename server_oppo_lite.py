#!/usr/bin/env python3
"""
Server Sieu Nhe danh rieng cho Dien thoai OPPO / Android (Termux) - Chi ton ~20MB RAM!
Khong chinh sua bat ky file code goc nao cua du an Tool Lyric by lekimlamcode.

Ho tro 3 che do cho /api/align:
1. Che do Sieu Nhe (Mac dinh - ~20MB RAM): Tinh toan thoi luong nhac thuc te va can chinh theo tung am tiet/cau hat ma khong can nap PyTorch 2GB vao RAM.
2. Che do Hybrid Cloud AI (Khuyen dung): Neu dat bien moi truong REMOTE_AI_URL (vi du link Hugging Face Space 16GB RAM mien phi), dien thoai OPPO se lam server chinh va gui nho xu ly Wav2Vec2 len Cloud.
3. Che do Local AI Tiet Kiem RAM (USE_LOCAL_AI=1): Chi nap mo hinh Wav2Vec2 khi bam Align, nen INT8 giam 60% RAM va giai phong RAM (gc.collect) ngay lap tuc sau khi xu ly xong.
"""

import os
import sys
import uuid
import json
import gc
import struct
import urllib.request
import urllib.error
from typing import Any, Dict, List

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
FRONTEND_STATIC_DIR = os.path.join(PROJECT_ROOT, "frontend", "static")
UPLOAD_DIR = os.path.join(PROJECT_ROOT, "uploads")
ALIGNMENT_CODE_PATH = os.path.join(PROJECT_ROOT, "models", "alignment-code")

os.makedirs(UPLOAD_DIR, exist_ok=True)


def estimate_audio_duration_ms(file_path: str) -> int:
    """Doc thoi luong file nhac (.wav, .mp3, .m4a) ma khong ton RAM"""
    try:
        size = os.path.getsize(file_path)
        if size <= 0:
            return 30000

        with open(file_path, "rb") as f:
            header = f.read(16384)

        # 1. Kiem tra WAV RIFF header
        if len(header) >= 44 and header[:4] == b"RIFF" and header[8:12] == b"WAVE":
            offset = 12
            byte_rate = 0
            data_size = 0
            while offset + 8 <= len(header):
                chunk_id = header[offset : offset + 4]
                chunk_size = struct.unpack("<I", header[offset + 4 : offset + 8])[0]
                if chunk_id == b"fmt " and offset + 20 <= len(header):
                    byte_rate = struct.unpack("<I", header[offset + 16 : offset + 20])[0]
                elif chunk_id == b"data":
                    data_size = chunk_size
                    break
                offset += 8 + chunk_size + (chunk_size % 2)
            if byte_rate > 0 and data_size > 0:
                return max(1000, int((data_size / byte_rate) * 1000))

        # 2. Kiem tra MP3 frame dau tien (bo qua ID3v2 tag)
        offset = 0
        if len(header) >= 10 and header[:3] == b"ID3":
            id3_size = (
                ((header[6] & 0x7F) << 21)
                | ((header[7] & 0x7F) << 14)
                | ((header[8] & 0x7F) << 7)
                | (header[9] & 0x7F)
            )
            offset = 10 + id3_size

        bitrates_v1_l3 = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]
        bitrates_v2_l3 = [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0]

        search_buf = header[offset:] if offset < len(header) else header
        for i in range(len(search_buf) - 4):
            if search_buf[i] == 0xFF and (search_buf[i + 1] & 0xE0) == 0xE0:
                version_bits = (search_buf[i + 1] >> 3) & 0x03
                layer_bits = (search_buf[i + 1] >> 1) & 0x03
                bitrate_idx = (search_buf[i + 2] >> 4) & 0x0F
                if layer_bits == 1 and 0 < bitrate_idx < 15:
                    kbps = (
                        bitrates_v1_l3[bitrate_idx]
                        if version_bits == 3
                        else bitrates_v2_l3[bitrate_idx]
                    )
                    if kbps > 0:
                        audio_bytes = max(1000, size - offset)
                        return max(1000, int((audio_bytes * 8) / kbps))

        # Fallback uoc luong theo kich thuoc file
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".wav":
            return max(2000, int((size / 32000) * 1000))
        return max(2000, int((size / 16000) * 1000))
    except Exception:
        return 30000


def ultra_light_align(lyrics_text: str, total_ms: int) -> List[Dict[str, Any]]:
    """Can chinh loi bai hat sieu nhe (< 1MB RAM) tuong thich 100% dinh dang goc"""
    lyrics_text = lyrics_text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in lyrics_text.strip().split("\n") if line.strip()]
    lyric_segments: List[Dict[str, Any]] = []

    for line in lines:
        words = [w for w in line.split() if w]
        if not words:
            continue
        lyric_segments.append(
            {"s": 0, "e": 0, "l": [{"s": 0, "e": 0, "d": w} for w in words]}
        )

    num_segs = len(lyric_segments)
    if num_segs == 0:
        return lyric_segments

    seg_duration = max(1000, total_ms // num_segs)
    for s_idx, seg in enumerate(lyric_segments):
        s_time = s_idx * seg_duration
        e_time = min(total_ms, (s_idx + 1) * seg_duration)
        seg["s"] = s_time
        seg["e"] = e_time
        words = seg.get("l", [])
        if words:
            word_dur = max(100, (e_time - s_time) // len(words))
            for w_idx, w in enumerate(words):
                w["s"] = s_time + w_idx * word_dur
                w["e"] = min(e_time, s_time + (w_idx + 1) * word_dur)

    return lyric_segments


def run_on_demand_quantized_ai(saved_path: str, lyrics_text: str) -> List[Dict[str, Any]]:
    """
    Chi nap model Wav2Vec2 khi can, nen INT8 giam 60% RAM tren dien thoai OPPO,
    va xoa khoi RAM ngay sau khi can chinh xong!
    """
    import torch
    from backend.fastapi_app import load_and_preprocess_audio, lyrics_text_to_segments

    if ALIGNMENT_CODE_PATH not in sys.path:
        sys.path.insert(0, ALIGNMENT_CODE_PATH)
    orig_cwd = os.getcwd()
    try:
        os.chdir(ALIGNMENT_CODE_PATH)
        import predict

        print("[OPPO-LITE] Dang nap mo hinh AI che do tiet kiem RAM (INT8)...")
        predict.model_path = os.path.join(PROJECT_ROOT, "models", "lyric-alignment")
        predict.load_model()

        # Luong tu hoa INT8 tren CPU de giam hon 50-60% RAM tren dien thoai
        if predict.model is not None and not predict.use_gpu:
            try:
                predict.model = torch.quantization.quantize_dynamic(
                    predict.model, {torch.nn.Linear}, dtype=torch.qint8
                )
                print("[OPPO-LITE] Da nen mo hinh sang INT8 thanh cong!")
            except Exception as q_err:
                print(f"[OPPO-LITE] Bo qua buoc INT8: {q_err}")

        wav = load_and_preprocess_audio(saved_path)
        segments = lyrics_text_to_segments(lyrics_text)
        with torch.no_grad():
            result = predict.handle_sample(wav, segments)

        # Giai phong RAM ngay lap tuc cho dien thoai OPPO
        predict.model = None
        predict.tokenizer = None
        predict.feature_extractor = None
        del wav
        gc.collect()
        print("[OPPO-LITE] Da giai phong RAM sau khi can chinh xong!")
        return result
    finally:
        os.chdir(orig_cwd)


def create_fastapi_lite_app():
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse, FileResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.middleware.cors import CORSMiddleware

    app = FastAPI(title="Tool Lyric by lekimlamcode (OPPO Lite Server)")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if os.path.exists(FRONTEND_STATIC_DIR):
        app.mount("/static", StaticFiles(directory=FRONTEND_STATIC_DIR), name="static")
    app.mount("/media", StaticFiles(directory=UPLOAD_DIR), name="media")

    @app.get("/")
    def serve_root():
        return FileResponse(os.path.join(FRONTEND_STATIC_DIR, "auto_karaoke.html"))

    @app.get("/auto")
    def serve_auto():
        return FileResponse(os.path.join(FRONTEND_STATIC_DIR, "auto_karaoke.html"))

    @app.get("/player")
    def serve_player():
        player_path = os.path.join(FRONTEND_STATIC_DIR, "player.html")
        if os.path.exists(player_path):
            return FileResponse(player_path)
        return FileResponse(os.path.join(FRONTEND_STATIC_DIR, "auto_karaoke.html"))

    @app.get("/index")
    def serve_index():
        return FileResponse(os.path.join(FRONTEND_STATIC_DIR, "index.html"))

    @app.post("/api/align")
    async def align_lite(request: Request):
        form_data = await request.form()
        lyrics_text = form_data.get("lyric_text")
        audio_file = form_data.get("audio_file")

        if not lyrics_text or not str(lyrics_text).strip():
            raise HTTPException(
                status_code=400,
                detail="Please provide lyrics text in form field 'lyric_text'.",
            )
        if not audio_file or isinstance(audio_file, str) or not hasattr(audio_file, "read"):
            raise HTTPException(status_code=400, detail="Please upload audio file.")

        lyrics_text = str(lyrics_text).strip()
        filename = getattr(audio_file, "filename", "") or "audio.mp3"
        file_ext = os.path.splitext(filename)[1].lower()
        if not file_ext or len(file_ext) > 10:
            file_ext = ".mp3"
        safe_filename = f"audio_{uuid.uuid4().hex}{file_ext}"
        saved_path = os.path.join(UPLOAD_DIR, safe_filename)

        content = await audio_file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded audio file is empty.")

        with open(saved_path, "wb") as f:
            f.write(content)

        # 1. Neu nguoi dung co cau hinh REMOTE_AI_URL (Hybrid Cloud AI)
        remote_ai_url = os.environ.get("REMOTE_AI_URL", "").strip()
        if remote_ai_url:
            try:
                print(f"[OPPO-LITE] Dang chuyen tiep AI Align sang Cloud: {remote_ai_url}")
                boundary = f"----OppoLiteBoundary{uuid.uuid4().hex}"
                body = bytearray()
                body.extend(f"--{boundary}\r\n".encode())
                body.extend(
                    b'Content-Disposition: form-data; name="lyric_text"\r\n\r\n'
                )
                body.extend(lyrics_text.encode("utf-8"))
                body.extend(f"\r\n--{boundary}\r\n".encode())
                body.extend(
                    f'Content-Disposition: form-data; name="audio_file"; filename="{safe_filename}"\r\n'.encode()
                )
                body.extend(b"Content-Type: application/octet-stream\r\n\r\n")
                body.extend(content)
                body.extend(f"\r\n--{boundary}--\r\n".encode())

                target_endpoint = remote_ai_url.rstrip("/") + "/api/align"
                req = urllib.request.Request(
                    target_endpoint,
                    data=bytes(body),
                    headers={
                        "Content-Type": f"multipart/form-data; boundary={boundary}"
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=120) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    return JSONResponse(
                        content={
                            "audio_url": f"/media/{safe_filename}",
                            "alignment": resp_data.get("alignment", []),
                        }
                    )
            except Exception as cloud_err:
                print(
                    f"[OPPO-LITE] Cloud AI khong phan hoi ({cloud_err}), chuyen sang xu ly noi bo..."
                )

        # 2. Neu bat USE_LOCAL_AI=1 va dien thoai co cai torch
        if os.environ.get("USE_LOCAL_AI", "0") == "1":
            try:
                alignment_result = run_on_demand_quantized_ai(saved_path, lyrics_text)
                return JSONResponse(
                    content={
                        "audio_url": f"/media/{safe_filename}",
                        "alignment": alignment_result,
                    }
                )
            except Exception as local_ai_err:
                print(
                    f"[OPPO-LITE] Local AI bi gioi han RAM ({local_ai_err}), dung che do Sieu Nhe..."
                )

        # 3. Che do Sieu Nhe (< 20MB RAM) - khong bao gio bi vang tren dien thoai OPPO
        duration_ms = estimate_audio_duration_ms(saved_path)
        alignment_result = ultra_light_align(lyrics_text, duration_ms)
        return JSONResponse(
            content={
                "audio_url": f"/media/{safe_filename}",
                "alignment": alignment_result,
            }
        )

    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7864))
    print("================================================================")
    print(f"  OPPO LITE SERVER - Chay sieu nhe (~20MB RAM) tai cong {port}")
    print(f"  Truy cap tren dien thoai: http://127.0.0.1:{port}")
    print("================================================================")
    try:
        import uvicorn

        app = create_fastapi_lite_app()
        uvicorn.run(app, host="0.0.0.0", port=port)
    except ImportError:
        print(
            "[INFO] Khong tim thay uvicorn/fastapi, ban co the chay bang Node.js: node server.mjs"
        )
