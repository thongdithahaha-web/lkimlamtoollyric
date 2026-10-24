FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install PyTorch CPU and Python packages
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Pre-download model weights into container for instant startup on Cloud Run
RUN python -c "from huggingface_hub import snapshot_download; snapshot_download('nguyenvulebinh/lyric-alignment', local_dir='models/lyric-alignment')"

# Port for Google Cloud Run (default 8080)
ENV PORT=8080
EXPOSE 8080

CMD ["python", "backend/fastapi_app.py"]
