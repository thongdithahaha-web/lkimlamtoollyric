import sys
import os
import uuid
from typing import Any, Dict, List
from contextlib import asynccontextmanager

# Cache directories - prioritize Drive D on Windows if available to conserve Drive C space
if os.path.exists("D:\\"):
    os.environ.setdefault("HF_HOME", r"D:\hf_cache")
    os.environ.setdefault("TRANSFORMERS_CACHE", r"D:\hf_cache")
    os.environ.setdefault("TORCH_HOME", r"D:\torch_cache")

# UTF-8 encoding for Windows stdout/stderr
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import torch
import torchaudio
import torchaudio.transforms as T
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
ALIGNMENT_CODE_PATH = os.path.join(PROJECT_ROOT, "models", "alignment-code")
FRONTEND_PATH = os.path.join(PROJECT_ROOT, "frontend")
UPLOAD_DIR = os.path.join(PROJECT_ROOT, "uploads")

# Import alignment module
os.chdir(ALIGNMENT_CODE_PATH)
sys.path.insert(0, ALIGNMENT_CODE_PATH)
sys.path.insert(0, SCRIPT_DIR)
import predict

is_model_loaded = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    global is_model_loaded
    if not is_model_loaded:
        print("[INFO] Loading AI Model (Wav2Vec2)...")
        model_path = os.path.join(PROJECT_ROOT, "models", "lyric-alignment")
        predict.model_path = model_path
        predict.load_model()
        is_model_loaded = True
        print("[INFO] AI Model loaded successfully!")
    yield

app = FastAPI(title="Tool Lyric by lekimlamcode", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup directories and static routes
os.makedirs(UPLOAD_DIR, exist_ok=True)
static_dir = os.path.join(FRONTEND_PATH, "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
app.mount("/media", StaticFiles(directory=UPLOAD_DIR), name="media")

def load_and_preprocess_audio(audio_path: str) -> torch.Tensor:
    print(f"[INFO] Loading audio: {audio_path}")
    sr = 16000
    wav = None
    
    # 1. Try soundfile first
    try:
        import soundfile as sf
        data, sr = sf.read(audio_path, dtype="float32")
        wav = torch.from_numpy(data)
        if len(wav.shape) == 1:
            wav = wav.unsqueeze(0)
        else:
            wav = wav.transpose(0, 1)  # shape: (channels, samples)
    except Exception as sf_err:
        print(f"[DEBUG] soundfile read failed: {sf_err}")

    # 2. Try FFmpeg via imageio_ffmpeg for tricky formats (e.g., m4a, aac)
    if wav is None:
        try:
            import imageio_ffmpeg
            import subprocess
            import numpy as np
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            cmd = [
                ffmpeg_exe, "-v", "error", "-i", audio_path,
                "-f", "s16le", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", "-"
            ]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            raw_audio, err = proc.communicate()
            if proc.returncode == 0 and len(raw_audio) > 0:
                data = np.frombuffer(raw_audio, dtype=np.int16).astype(np.float32) / 32768.0
                wav = torch.from_numpy(data).unsqueeze(0)
                sr = 16000
                print("[INFO] Audio decoded successfully using embedded FFmpeg.")
        except Exception as ffmpeg_err:
            print(f"[DEBUG] imageio_ffmpeg decode failed: {ffmpeg_err}")

    # 3. Fallback to torchaudio
    if wav is None:
        try:
            wav, sr = torchaudio.load(audio_path)
        except Exception as ta_err:
            raise RuntimeError(f"Could not load audio file '{audio_path}': {ta_err}")
    
    # Convert stereo to mono
    if len(wav.shape) > 1 and wav.shape[0] > 1:
        wav = wav.mean(dim=0, keepdim=True)
    elif len(wav.shape) == 1:
        wav = wav.unsqueeze(0)
        
    # Resample to 16kHz if needed
    if sr != 16000:
        resampler = T.Resample(sr, 16000)
        wav = resampler(wav)
        
    return wav

def lyrics_text_to_segments(lyrics_text: str) -> List[Dict[str, Any]]:
    lyrics_text = lyrics_text.replace('\r\n', '\n').replace('\r', '\n')
    lines = lyrics_text.strip().split('\n')
    lyric_segments: List[Dict[str, Any]] = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        words = line.split()
        if not words:
            continue
        segment = {
            "s": 0, "e": 0,
            "l": [{"s": 0, "e": 0, "d": w} for w in words]
        }
        lyric_segments.append(segment)
        
    return lyric_segments

@app.get("/")
def serve_frontend():
    return FileResponse(os.path.join(FRONTEND_PATH, "static", "auto_karaoke.html"))

@app.get("/player")
def serve_player():
    player_path = os.path.join(FRONTEND_PATH, "static", "player.html")
    if os.path.exists(player_path):
        return FileResponse(player_path)
    return FileResponse(os.path.join(FRONTEND_PATH, "static", "auto_karaoke.html"))

@app.get("/auto")
def serve_auto_karaoke():
    return FileResponse(os.path.join(FRONTEND_PATH, "static", "auto_karaoke.html"))

@app.post("/api/align")
async def align_service(request: Request):
    """Handle alignment with multipart form data"""
    try:
        form_data = await request.form()
        lyrics_text = form_data.get("lyric_text")
        audio_file = form_data.get("audio_file")
        
        print(f"[DEBUG] Form keys: {list(form_data.keys())}")
        print(f"[DEBUG] lyrics text exists: {lyrics_text is not None}")
        print(f"[DEBUG] audio_file exists: {audio_file is not None}")
        
        if not lyrics_text or not str(lyrics_text).strip():
            raise HTTPException(
                status_code=400,
                detail="Please provide lyrics text in form field 'lyric_text'."
            )
        
        if not audio_file:
            raise HTTPException(status_code=400, detail="Please upload audio file.")
            
        if isinstance(audio_file, str) or not hasattr(audio_file, 'read'):
            raise HTTPException(status_code=400, detail="Invalid audio file upload format.")
        
        lyrics_text = str(lyrics_text).strip()
        
        # Save file safely
        filename = getattr(audio_file, 'filename', '') or 'audio.mp3'
        file_ext = os.path.splitext(filename)[1].lower()
        if not file_ext or len(file_ext) > 10:
            file_ext = ".mp3"
        safe_filename = f"audio_{uuid.uuid4().hex}{file_ext}"
        saved_path = os.path.join(UPLOAD_DIR, safe_filename)
        
        content = await audio_file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded audio file is empty (0 bytes).")
            
        with open(saved_path, "wb") as f:
            f.write(content)
        print(f"[DEBUG] File saved: {saved_path}, size: {len(content)} bytes")
        
        # Process audio
        wav = load_and_preprocess_audio(saved_path)
        
        # Format lyrics
        lyric_segments = lyrics_text_to_segments(lyrics_text)
        print(f"[DEBUG] lyric segments: {len(lyric_segments)}")
        if not lyric_segments:
            raise HTTPException(status_code=400, detail="No valid lyrics lines found.")
        
        # Align
        print("[INFO] Processing alignment...")
        alignment_result = predict.handle_sample(wav, lyric_segments)
        print("[INFO] Alignment complete!")
        
        return JSONResponse(content={
            "audio_url": f"/media/{safe_filename}",
            "alignment": alignment_result
        })
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import socket
    port = int(os.environ.get("PORT", 7864))

    # Check if port is occupied on Windows; release it automatically if 7864
    if os.name == "nt" and port == 7864:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("0.0.0.0", port))
            sock.close()
        except OSError:
            print(f"[WARN] Cổng {port} đang bị chiếm dụng. Đang tự động giải phóng cổng...")
            try:
                import subprocess
                subprocess.run(
                    f'for /f "tokens=5" %a in (\'netstat -aon ^| findstr :{port} ^| findstr LISTENING\') do taskkill /F /PID %a',
                    shell=True, capture_output=True
                )
                import time
                time.sleep(1)
            except Exception:
                pass

    uvicorn.run(app, host="0.0.0.0", port=port)
