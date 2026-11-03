# ============================================================
#  YouTube Downloader - deployable web image
#  Works on: Hugging Face Spaces, Render, Koyeb, Railway,
#            Fly.io, any Docker host, any VPS.
# ============================================================
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=7860 \
    DOWNLOAD_DIR=/tmp/ytdl_downloads \
    MAX_CONCURRENT=2 \
    FILE_TTL=0 \
    MAX_STORAGE_MB=20000

# ffmpeg is required to merge video + audio and to cut clips.
# tini makes sure background threads/child processes die cleanly.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        ca-certificates \
        curl \
        unzip \
        tini \
    && rm -rf /var/lib/apt/lists/*

# Deno: yt-dlp needs a JavaScript runtime to solve YouTube's signature
# challenges. Without it many videos show up with no formats.
RUN curl -fsSL https://deno.land/install.sh | DENO_INSTALL=/usr/local sh \
    && /usr/local/bin/deno --version

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py ./
COPY templates ./templates
COPY static ./static

# Non-root friendly: the app only writes to DOWNLOAD_DIR (inside /tmp).
RUN mkdir -p /tmp/ytdl_downloads && chmod 1777 /tmp/ytdl_downloads

EXPOSE 7860

ENTRYPOINT ["tini", "--"]

# IMPORTANT: keep --workers 1. Jobs live in memory, so multiple workers
# would not see each other's tasks. Threads handle the concurrency instead.
CMD ["sh", "-c", "exec gunicorn app:app --bind 0.0.0.0:${PORT} --workers 1 --threads 16 --timeout 1200 --graceful-timeout 30 --access-logfile - --error-logfile -"]
