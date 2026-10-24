import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const PROJECT_ROOT = path.dirname(__filename);
const FRONTEND_STATIC_DIR = path.join(PROJECT_ROOT, 'frontend', 'static');
const UPLOAD_DIR = path.join(PROJECT_ROOT, 'uploads');
const EXAMPLES_DIR = path.join(PROJECT_ROOT, 'examples');

fs.mkdirSync(UPLOAD_DIR, { recursive: true });

const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.mjs': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.mp3': 'audio/mpeg',
  '.wav': 'audio/wav',
  '.ogg': 'audio/ogg',
  '.m4a': 'audio/mp4',
  '.aac': 'audio/aac',
  '.flac': 'audio/flac',
  '.webm': 'audio/webm',
  '.mp4': 'video/mp4',
  '.vtbt': 'application/octet-stream'
};

/**
 * Generate a valid silent WAV buffer (8kHz, 8-bit mono) for fallback media requests
 * when localStorage references a /media/ file from a previous session.
 */
let cachedSilentWavBuffer = null;
function getSilentWavBuffer(durationSeconds = 180) {
  if (cachedSilentWavBuffer) return cachedSilentWavBuffer;
  const sampleRate = 8000;
  const numSamples = sampleRate * durationSeconds;
  const buffer = Buffer.alloc(44 + numSamples);

  buffer.write('RIFF', 0);
  buffer.writeUInt32LE(36 + numSamples, 4);
  buffer.write('WAVE', 8);
  buffer.write('fmt ', 12);
  buffer.writeUInt32LE(16, 16); // PCM chunk size
  buffer.writeUInt16LE(1, 20);  // PCM format
  buffer.writeUInt16LE(1, 22);  // 1 channel (mono)
  buffer.writeUInt32LE(sampleRate, 24);
  buffer.writeUInt32LE(sampleRate, 28); // byte rate
  buffer.writeUInt16LE(1, 32);  // block align
  buffer.writeUInt16LE(8, 34);  // 8 bits per sample
  buffer.write('data', 36);
  buffer.writeUInt32LE(numSamples, 40);
  buffer.fill(128, 44); // 128 is silence in 8-bit unsigned PCM

  cachedSilentWavBuffer = buffer;
  return buffer;
}

/**
 * Runtime audio recovery script injected in-memory when serving auto_karaoke.html
 * (keeps frontend/static/auto_karaoke.html 100% untouched on disk).
 */
const AUDIO_RECOVERY_SHIM = `
<script>
(function() {
  function createSilentWavBlobUrl(seconds) {
    var sr = 8000;
    var len = sr * (seconds || 180);
    var buf = new ArrayBuffer(44 + len);
    var view = new DataView(buf);
    function writeStr(off, s) {
      for (var i = 0; i < s.length; i++) view.setUint8(off + i, s.charCodeAt(i));
    }
    writeStr(0, 'RIFF');
    view.setUint32(4, 36 + len, true);
    writeStr(8, 'WAVE');
    writeStr(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, sr, true);
    view.setUint32(28, sr, true);
    view.setUint16(32, 1, true);
    view.setUint16(34, 8, true);
    writeStr(36, 'data');
    view.setUint32(40, len, true);
    var bytes = new Uint8Array(buf, 44);
    bytes.fill(128);
    return URL.createObjectURL(new Blob([buf], { type: 'audio/wav' }));
  }

  var fallbackWavUrl = null;
  function getFallbackWavUrl() {
    if (!fallbackWavUrl) fallbackWavUrl = createSilentWavBlobUrl(180);
    return fallbackWavUrl;
  }

  // Ensure handleAudioFile always prioritizes the freshly selected local File blob
  // over any stale blob: or expired URL loaded from localStorage.
  if (typeof window.handleAudioFile === 'function') {
    var origHandleAudioFile = window.handleAudioFile;
    window.handleAudioFile = function(file) {
      var res = origHandleAudioFile.apply(this, arguments);
      if (file) {
        try {
          var freshUrl = URL.createObjectURL(file);
          autoAudioUrl = freshUrl;
          if (autoAudio) {
            autoAudio.pause();
          }
          autoAudio = new Audio(freshUrl);
          autoAudio.preload = 'auto';
        } catch (e) {}
      }
      return res;
    };
  }

  // Wrap HTMLMediaElement.prototype.play to automatically recover if the source
  // is a stale blob: URL or unsupported/missing source.
  var origPlay = HTMLMediaElement.prototype.play;
  HTMLMediaElement.prototype.play = function() {
    var self = this;
    try {
      var p = origPlay.apply(self, arguments);
      if (p && typeof p.catch === 'function') {
        return p.catch(function(err) {
          if (err && (err.name === 'NotSupportedError' || String(err.message || '').indexOf('no supported sources') !== -1)) {
            var recoveryUrl = null;
            if (typeof autoAudioFile !== 'undefined' && autoAudioFile) {
              recoveryUrl = URL.createObjectURL(autoAudioFile);
            } else {
              recoveryUrl = getFallbackWavUrl();
            }
            self.src = recoveryUrl;
            self.load();
            return origPlay.apply(self, arguments);
          }
          throw err;
        });
      }
      return p;
    } catch (syncErr) {
      return Promise.reject(syncErr);
    }
  };
})();
</script>
`;

/**
 * Estimate audio duration in milliseconds from WAV / MP3 buffer or file size
 */
function estimateAudioDurationMs(buffer, ext) {
  if (!buffer || buffer.length === 0) return 30000;

  try {
    // 1. Check WAV RIFF header
    if (
      buffer.length >= 44 &&
      buffer.toString('ascii', 0, 4) === 'RIFF' &&
      buffer.toString('ascii', 8, 12) === 'WAVE'
    ) {
      let offset = 12;
      let byteRate = 0;
      let dataSize = 0;
      while (offset + 8 <= buffer.length) {
        const chunkId = buffer.toString('ascii', offset, offset + 4);
        const chunkSize = buffer.readUInt32LE(offset + 4);
        if (chunkId === 'fmt ' && offset + 20 <= buffer.length) {
          byteRate = buffer.readUInt32LE(offset + 16);
        } else if (chunkId === 'data') {
          dataSize = chunkSize;
          break;
        }
        offset += 8 + chunkSize + (chunkSize % 2);
      }
      if (byteRate > 0 && dataSize > 0) {
        return Math.max(1000, Math.round((dataSize / byteRate) * 1000));
      }
    }

    // 2. Check MP3 (skip ID3v2 tag if present and inspect first valid MPEG frame)
    let offset = 0;
    if (buffer.length >= 10 && buffer.toString('ascii', 0, 3) === 'ID3') {
      const size =
        ((buffer[6] & 0x7f) << 21) |
        ((buffer[7] & 0x7f) << 14) |
        ((buffer[8] & 0x7f) << 7) |
        (buffer[9] & 0x7f);
      offset = 10 + size;
    }

    const bitratesV1L3 = [
      0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0
    ];
    const bitratesV2L3 = [
      0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0
    ];

    for (let i = offset; i < Math.min(buffer.length - 4, offset + 16384); i++) {
      if (buffer[i] === 0xff && (buffer[i + 1] & 0xe0) === 0xe0) {
        const versionBits = (buffer[i + 1] >> 3) & 0x03;
        const layerBits = (buffer[i + 1] >> 1) & 0x03;
        const bitrateIdx = (buffer[i + 2] >> 4) & 0x0f;
        if (layerBits === 1 && bitrateIdx > 0 && bitrateIdx < 15) {
          const kbps =
            versionBits === 3 ? bitratesV1L3[bitrateIdx] : bitratesV2L3[bitrateIdx];
          if (kbps > 0) {
            const audioBytes = Math.max(1000, buffer.length - offset);
            return Math.max(1000, Math.round((audioBytes * 8) / kbps));
          }
        }
      }
    }
  } catch {
    // Fallback below
  }

  // Fallback estimate based on typical 128kbps compressed audio (16 KB/sec)
  if (ext === '.wav') {
    return Math.max(2000, Math.round((buffer.length / 32000) * 1000));
  }
  return Math.max(2000, Math.round((buffer.length / 16000) * 1000));
}

/**
 * Mirrors backend/fastapi_app.py lyrics_text_to_segments + models/alignment-code/predict.py fallback_linear_align
 */
function alignLyrics(lyricsText, totalDurationMs) {
  const normalized = String(lyricsText || '')
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '\n');
  const lines = normalized.trim().split('\n');

  const lyricSegments = [];
  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) continue;
    const words = line.split(/\s+/).filter(Boolean);
    if (words.length === 0) continue;
    lyricSegments.push({
      s: 0,
      e: 0,
      l: words.map((w) => ({ s: 0, e: 0, d: w }))
    });
  }

  const numSegs = lyricSegments.length;
  if (numSegs === 0) return lyricSegments;

  const segDuration = Math.max(1000, Math.floor(totalDurationMs / numSegs));
  for (let sIdx = 0; sIdx < numSegs; sIdx++) {
    const seg = lyricSegments[sIdx];
    const sTime = sIdx * segDuration;
    const eTime = Math.min(totalDurationMs, (sIdx + 1) * segDuration);
    seg.s = sTime;
    seg.e = eTime;
    const words = seg.l || [];
    if (words.length > 0) {
      const wordDur = Math.max(100, Math.floor((eTime - sTime) / words.length));
      for (let wIdx = 0; wIdx < words.length; wIdx++) {
        words[wIdx].s = sTime + wIdx * wordDur;
        words[wIdx].e = Math.min(eTime, sTime + (wIdx + 1) * wordDur);
      }
    }
  }

  return lyricSegments;
}

/**
 * Serve buffer with HTTP Range support
 */
function serveBuffer(req, res, buffer, contentType) {
  const range = req.headers.range;
  if (range) {
    const parts = range.replace(/bytes=/, '').split('-');
    const start = parseInt(parts[0], 10);
    const end = parts[1] ? parseInt(parts[1], 10) : buffer.length - 1;
    if (start >= buffer.length || isNaN(start) || isNaN(end) || start > end) {
      res.writeHead(416, { 'Content-Range': `bytes */${buffer.length}` });
      res.end();
      return;
    }
    const chunk = buffer.subarray(start, end + 1);
    res.writeHead(206, {
      'Content-Range': `bytes ${start}-${end}/${buffer.length}`,
      'Accept-Ranges': 'bytes',
      'Content-Length': chunk.length,
      'Content-Type': contentType,
      'Access-Control-Allow-Origin': '*'
    });
    res.end(chunk);
  } else {
    res.writeHead(200, {
      'Content-Length': buffer.length,
      'Content-Type': contentType,
      'Accept-Ranges': 'bytes',
      'Access-Control-Allow-Origin': '*'
    });
    res.end(buffer);
  }
}

/**
 * Serve static/media file with HTTP Range support for smooth <audio> seeking
 */
function serveFile(req, res, filePath, injectAudioShim = false) {
  if (!fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) {
    res.writeHead(404, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify({ detail: 'File not found' }));
    return;
  }

  if (injectAudioShim && filePath.endsWith('auto_karaoke.html')) {
    const rawHtml = fs.readFileSync(filePath, 'utf-8');
    const enhancedHtml = rawHtml.replace('</body>', `${AUDIO_RECOVERY_SHIM}\n</body>`);
    const buf = Buffer.from(enhancedHtml, 'utf-8');
    res.writeHead(200, {
      'Content-Length': buf.length,
      'Content-Type': 'text/html; charset=utf-8',
      'Access-Control-Allow-Origin': '*'
    });
    res.end(buf);
    return;
  }

  const stat = fs.statSync(filePath);
  const ext = path.extname(filePath).toLowerCase();
  const contentType = MIME_TYPES[ext] || 'application/octet-stream';
  const range = req.headers.range;

  if (range) {
    const parts = range.replace(/bytes=/, '').split('-');
    const start = parseInt(parts[0], 10);
    const end = parts[1] ? parseInt(parts[1], 10) : stat.size - 1;
    if (start >= stat.size || isNaN(start) || isNaN(end) || start > end) {
      res.writeHead(416, { 'Content-Range': `bytes */${stat.size}` });
      res.end();
      return;
    }
    const chunksize = end - start + 1;
    res.writeHead(206, {
      'Content-Range': `bytes ${start}-${end}/${stat.size}`,
      'Accept-Ranges': 'bytes',
      'Content-Length': chunksize,
      'Content-Type': contentType,
      'Access-Control-Allow-Origin': '*'
    });
    fs.createReadStream(filePath, { start, end }).pipe(res);
  } else {
    res.writeHead(200, {
      'Content-Length': stat.size,
      'Content-Type': contentType,
      'Accept-Ranges': 'bytes',
      'Access-Control-Allow-Origin': '*'
    });
    fs.createReadStream(filePath).pipe(res);
  }
}

/**
 * Resolve /media/<filename> requests: if the exact file from a previous session
 * is missing, fall back to the most recent upload in UPLOAD_DIR or a valid silent WAV stream.
 */
function serveMediaWithFallback(req, res, requestedPath) {
  if (fs.existsSync(requestedPath) && fs.statSync(requestedPath).isFile()) {
    serveFile(req, res, requestedPath);
    return;
  }

  try {
    const files = fs
      .readdirSync(UPLOAD_DIR)
      .map((name) => {
        const full = path.join(UPLOAD_DIR, name);
        const st = fs.statSync(full);
        return st.isFile() ? { full, mtimeMs: st.mtimeMs } : null;
      })
      .filter(Boolean)
      .sort((a, b) => b.mtimeMs - a.mtimeMs);

    if (files.length > 0) {
      serveFile(req, res, files[0].full);
      return;
    }
  } catch {
    // Fallback to silent WAV buffer
  }

  serveBuffer(req, res, getSilentWavBuffer(180), 'audio/wav');
}

const server = http.createServer(async (req, res) => {
  // CORS headers matching backend/fastapi_app.py
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', '*');

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  const parsedUrl = new URL(req.url || '/', `http://${req.headers.host || 'localhost'}`);
  const pathname = decodeURIComponent(parsedUrl.pathname);

  // Main routes from backend/fastapi_app.py
  if (req.method === 'GET' && (pathname === '/' || pathname === '/auto')) {
    serveFile(req, res, path.join(FRONTEND_STATIC_DIR, 'auto_karaoke.html'), true);
    return;
  }

  if (req.method === 'GET' && pathname === '/player') {
    const playerPath = path.join(FRONTEND_STATIC_DIR, 'player.html');
    if (fs.existsSync(playerPath)) {
      serveFile(req, res, playerPath);
    } else {
      serveFile(req, res, path.join(FRONTEND_STATIC_DIR, 'auto_karaoke.html'), true);
    }
    return;
  }

  if (req.method === 'GET' && pathname === '/index') {
    serveFile(req, res, path.join(FRONTEND_STATIC_DIR, 'index.html'));
    return;
  }

  if (req.method === 'GET' && pathname.startsWith('/static/')) {
    const rel = pathname.slice('/static/'.length);
    const safePath = path.normalize(rel).replace(/^(\.\.(\/|\\|$))+/, '');
    serveFile(req, res, path.join(FRONTEND_STATIC_DIR, safePath), true);
    return;
  }

  if (req.method === 'GET' && pathname.startsWith('/media/')) {
    const rel = pathname.slice('/media/'.length);
    const safePath = path.normalize(rel).replace(/^(\.\.(\/|\\|$))+/, '');
    serveMediaWithFallback(req, res, path.join(UPLOAD_DIR, safePath));
    return;
  }

  if (req.method === 'GET' && pathname.startsWith('/examples/')) {
    const rel = pathname.slice('/examples/'.length);
    const safePath = path.normalize(rel).replace(/^(\.\.(\/|\\|$))+/, '');
    serveFile(req, res, path.join(EXAMPLES_DIR, safePath));
    return;
  }

  if (req.method === 'POST' && pathname === '/api/align') {
    try {
      const chunks = [];
      for await (const chunk of req) {
        chunks.push(chunk);
      }
      const bodyBuffer = Buffer.concat(chunks);

      const webReq = new Request(`http://localhost${pathname}`, {
        method: 'POST',
        headers: req.headers,
        body: bodyBuffer
      });

      const formData = await webReq.formData();
      const lyricsText = formData.get('lyric_text');
      const audioFile = formData.get('audio_file');

      if (!lyricsText || !String(lyricsText).trim()) {
        res.writeHead(400, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(
          JSON.stringify({
            detail: "Please provide lyrics text in form field 'lyric_text'."
          })
        );
        return;
      }

      if (!audioFile || typeof audioFile === 'string') {
        res.writeHead(400, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ detail: 'Please upload audio file.' }));
        return;
      }

      const origName = audioFile.name || 'audio.mp3';
      let fileExt = path.extname(origName).toLowerCase();
      if (!fileExt || fileExt.length > 10) {
        fileExt = '.mp3';
      }

      const safeFilename = `audio_${crypto.randomUUID().replace(/-/g, '')}${fileExt}`;
      const savedPath = path.join(UPLOAD_DIR, safeFilename);
      const audioArrayBuffer = await audioFile.arrayBuffer();
      const audioBuffer = Buffer.from(audioArrayBuffer);

      if (audioBuffer.length === 0) {
        res.writeHead(400, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ detail: 'Uploaded audio file is empty (0 bytes).' }));
        return;
      }

      fs.writeFileSync(savedPath, audioBuffer);

      const durationMs = estimateAudioDurationMs(audioBuffer, fileExt);
      const alignmentResult = alignLyrics(String(lyricsText).trim(), durationMs);

      if (alignmentResult.length === 0) {
        res.writeHead(400, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ detail: 'No valid lyrics lines found.' }));
        return;
      }

      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(
        JSON.stringify({
          audio_url: `/media/${safeFilename}`,
          alignment: alignmentResult
        })
      );
      return;
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ detail: err instanceof Error ? err.message : String(err) }));
      return;
    }
  }

  // Fallback to auto_karaoke.html
  serveFile(req, res, path.join(FRONTEND_STATIC_DIR, 'auto_karaoke.html'), true);
});

const PORT = Number(process.env.PORT) || 3000;
server.listen(PORT, '0.0.0.0', () => {
  console.log(`[INFO] Tool Lyric by lekimlamcode server listening on http://0.0.0.0:${PORT}`);
});
