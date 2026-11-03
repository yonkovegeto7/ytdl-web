"""
YouTube Downloader - Web Edition
================================

A hosted (multi-user) version of the desktop app.

What changed compared to the local/EXE build:
  * binds to 0.0.0.0:$PORT instead of 127.0.0.1
  * no Windows-only features (folder picker, "open folder", shell commands)
  * the /api/run_terminal endpoint was REMOVED. On a public server it would let
    anyone run commands on the machine (remote code execution).
  * no server filesystem paths are accepted from the client
  * every download is streamed back to the visitor's browser
  * jobs run in a bounded thread pool so a free instance does not get hammered
  * finished files are kept (FILE_TTL=0 by default) so slow connections are
    never cut off; only a disk cap (MAX_STORAGE_MB) removes the oldest files
  * downloads support HTTP Range, so a broken connection can be resumed
  * chapter download returns a single .zip
  * optional cookies / proxy / impersonation so YouTube does not block the
    server's datacenter IP
  * /healthz endpoint for hosting platforms

Environment variables (all optional):
  PORT                 port to listen on (default 7860)
  DOWNLOAD_DIR         where temporary files are written (default <tmp>/ytdl_downloads)
  MAX_CONCURRENT       simultaneous downloads (default 2)
  FILE_TTL             seconds before a finished file is deleted (0 = never, default)
  MAX_STORAGE_MB       disk cap in MB, oldest files removed first (0 = no cap)
  MAX_HEIGHT           refuse videos taller than this (0 = no limit)
  MAX_DURATION         refuse videos longer than this in seconds (0 = no limit)
  RATE_FETCH           format requests per IP per hour (default 120)
  RATE_DOWNLOAD        downloads per IP per hour (default 60)
  COOKIES_B64          base64 of a Netscape cookies.txt (helps bypass bot checks)
  COOKIES_FILE         path to cookies.txt (used instead of COOKIES_B64)
  YTDLP_PROXY          http://user:pass@host:port proxy for yt-dlp
  YTDLP_IMPERSONATE    e.g. "chrome" (needs yt-dlp[default] / curl_cffi)
  YTDLP_EXTRACTOR_ARGS e.g. "youtube:player_client=web_safari"
"""

import base64
import datetime
import json
import os
import re
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import traceback
import uuid
import zipfile
from urllib.parse import urlparse

import yt_dlp
from flask import Flask, jsonify, render_template, request, send_file

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DOWNLOAD_DIR = os.environ.get("DOWNLOAD_DIR") or os.path.join(
    tempfile.gettempdir(), "ytdl_downloads"
)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def _int_env(name, default):
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


PORT = _int_env("PORT", 7860)
MAX_CONCURRENT = max(1, _int_env("MAX_CONCURRENT", 2))
# 0 = never delete because of age. Files are only removed when the disk cap
# below is reached (oldest first), so slow connections are never cut off.
FILE_TTL = max(0, _int_env("FILE_TTL", 0))
# Hard cap for stored downloads. 0 = no cap. 20 GB fits a 50 GB free disk.
MAX_STORAGE_MB = max(0, _int_env("MAX_STORAGE_MB", 20000))
MAX_HEIGHT = max(0, _int_env("MAX_HEIGHT", 0))
MAX_DURATION = max(0, _int_env("MAX_DURATION", 0))

# Abuse protection, per client IP per hour. Raise them on a bigger server.
RATE_FETCH = max(1, _int_env("RATE_FETCH", 120))
RATE_DOWNLOAD = max(1, _int_env("RATE_DOWNLOAD", 60))

YTDLP_PROXY = os.environ.get("YTDLP_PROXY", "").strip()
YTDLP_IMPERSONATE = os.environ.get("YTDLP_IMPERSONATE", "").strip()
YTDLP_EXTRACTOR_ARGS = os.environ.get("YTDLP_EXTRACTOR_ARGS", "").strip()

COOKIE_FILE = None


def _prepare_cookies():
    """Turn COOKIES_B64 / COOKIES_FILE into a path yt-dlp can use."""
    global COOKIE_FILE
    path = os.environ.get("COOKIES_FILE", "").strip()
    if path and os.path.isfile(path):
        COOKIE_FILE = path
        return
    raw = os.environ.get("COOKIES_B64", "").strip()
    if not raw:
        return
    try:
        data = base64.b64decode(raw)
        dest = os.path.join(tempfile.gettempdir(), "cookies.txt")
        with open(dest, "wb") as fh:
            fh.write(data)
        COOKIE_FILE = dest
    except Exception:
        traceback.print_exc()


_prepare_cookies()

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024  # JSON bodies only

# --------------------------------------------------------------------------- #
# Job storage
# --------------------------------------------------------------------------- #

TASKS = {}
TASKS_LOCK = threading.Lock()
SLOTS = threading.Semaphore(MAX_CONCURRENT)

ALLOWED_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
}

FORMAT_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,32}$")
TIME_RE = re.compile(r"^\d{1,2}:\d{1,2}(?::\d{1,2})?$")


def is_ffmpeg_available():
    return shutil.which("ffmpeg") is not None


def detect_js_runtimes():
    """yt-dlp needs a JS runtime for YouTube's signature challenges."""
    for runtime in ("deno", "node", "bun"):
        if shutil.which(runtime):
            return {runtime: {}}
    return {}


JS_RUNTIMES = detect_js_runtimes()


def parse_extractor_args(raw):
    out = {}
    for chunk in raw.split(";"):
        chunk = chunk.strip()
        if not chunk or ":" not in chunk:
            continue
        name, rest = chunk.split(":", 1)
        values = {}
        for pair in rest.split(","):
            if "=" in pair:
                key, val = pair.split("=", 1)
                values.setdefault(key.strip(), []).append(val.strip())
        if values:
            out[name.strip()] = values
    return out


def base_ydl_opts():
    opts = {
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "socket_timeout": 20,
        "retries": 5,
        "fragment_retries": 5,
        "extractor_retries": 5,
        "file_access_retries": 5,
        "concurrent_fragments": 4,
        "restrictfilenames": False,
        "overwrites": True,
    }
    if COOKIE_FILE:
        opts["cookiefile"] = COOKIE_FILE
    if YTDLP_PROXY:
        opts["proxy"] = YTDLP_PROXY
    if JS_RUNTIMES:
        opts["js_runtimes"] = JS_RUNTIMES
    if YTDLP_EXTRACTOR_ARGS:
        try:
            args = parse_extractor_args(YTDLP_EXTRACTOR_ARGS)
            if args:
                opts["extractor_args"] = args
        except Exception:
            pass
    if YTDLP_IMPERSONATE:
        try:
            from yt_dlp.networking.impersonate import ImpersonateTarget

            opts["impersonate"] = ImpersonateTarget.from_str(YTDLP_IMPERSONATE)
        except Exception:
            pass
    return opts


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #


def normalize_url(raw):
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("empty")
    if not re.match(r"^https?://", raw, re.I):
        raw = "https://" + raw
    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("bad scheme")
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if host not in {h.replace("www.", "") for h in ALLOWED_HOSTS}:
        raise ValueError("unsupported host")
    return raw


def sanitize_filename(name, default="video.mp4"):
    name = os.path.basename((name or "").replace("\\", "/")).strip()
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    name = name.strip(". ")
    if not name:
        return default
    stem, ext = os.path.splitext(name)
    if ext.lower() not in (".mp4", ".mkv", ".webm", ".m4a"):
        stem, ext = name, ".mp4"
    return (stem[:110] or "video") + ext


def format_time(seconds):
    seconds = int(seconds or 0)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def time_to_seconds(text):
    parts = str(text).strip().split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    if len(parts) == 1:
        return int(parts[0])
    raise ValueError("bad time")


def human_size(num):
    if not num:
        return ""
    num = float(num)
    for unit in ("B", "KB", "MB", "GB"):
        if num < 1024 or unit == "GB":
            return f"{num:.1f} {unit}"
        num /= 1024
    return ""


def friendly_error(exc):
    msg = str(exc) or exc.__class__.__name__
    low = msg.lower()
    if "sign in to confirm" in low or "not a bot" in low:
        return (
            "YouTube is asking this server to sign in (datacenter IP block). "
            "The site owner must add cookies (COOKIES_B64) or use a proxy."
        )
    if "403" in msg or "forbidden" in low:
        return "YouTube refused the request (HTTP 403). Please retry in a minute."
    if "private video" in low:
        return "This video is private."
    if "video unavailable" in low or "removed" in low:
        return "This video is unavailable or was removed."
    if "age" in low and "restrict" in low:
        return "This video is age-restricted and needs cookies from a signed-in account."
    if "timed out" in low or "timeout" in low:
        return "The connection to YouTube timed out. Please retry."
    if len(msg) > 300:
        msg = msg[:300] + "..."
    return msg


def _format_rank(f):
    """Bigger is better: a real file size beats an estimate, then bitrate."""
    return (f.get("filesize") or 0, f.get("tbr") or 0)


def dedupe_video_formats(formats):
    """One entry per (height, fps). YouTube ships the same quality under several
    format ids (progressive, HLS, different codecs) which looked like duplicates."""
    best = {}
    for f in formats:
        key = (f.get("height") or 0, int(round(f.get("fps") or 30)))
        current = best.get(key)
        if current is None or _format_rank(f) > _format_rank(current):
            best[key] = f
    out = []
    for f in best.values():
        clean = dict(f)
        clean.pop("tbr", None)
        out.append(clean)
    return out


def dedupe_audio_formats(formats):
    """One entry per bitrate, preferring the normal stream over the "-drc" twin."""
    best = {}
    for f in formats:
        key = int(round(f.get("abr") or 0)) or f.get("format_id")
        current = best.get(key)
        if current is None or _audio_rank(f) > _audio_rank(current):
            best[key] = f
    out = []
    for f in best.values():
        clean = dict(f)
        clean.pop("tbr", None)
        out.append(clean)
    return out


def _audio_rank(f):
    return ("-drc" not in str(f.get("format_id")), f.get("filesize") or 0, f.get("tbr") or 0)


def free_disk_mb():
    try:
        return shutil.disk_usage(DOWNLOAD_DIR).free / (1024 * 1024)
    except Exception:
        return 999999


def new_task():
    task_id = uuid.uuid4().hex
    with TASKS_LOCK:
        TASKS[task_id] = {
            "id": task_id,
            "status": "queued",
            "progress": 0,
            "error": None,
            "stopped": False,
            "logs": [],
            "created": time.time(),
            "speed_display": "",
            "downloaded": 0,
            "total": 0,
            "eta": 0,
            "output_file": None,
            "output_filename": None,
        }
    return TASKS[task_id]


def log(task, message):
    logs = task.setdefault("logs", [])
    if len(logs) < 300:
        logs.append(message)


class TaskLogger:
    """Adapter so yt-dlp's own messages show up in the UI console."""

    def __init__(self, task):
        self.task = task

    def debug(self, msg):
        if not msg.startswith("[debug] "):
            log(self.task, msg)

    def info(self, msg):
        log(self.task, msg)

    def warning(self, msg):
        log(self.task, "[WARN] " + msg)

    def error(self, msg):
        log(self.task, "[ERROR] " + msg)


def progress_hook(task, phase_start, phase_end):
    last = [phase_start]

    def hook(d):
        if task.get("stopped"):
            raise yt_dlp.utils.DownloadError("stopped by user")
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes") or 0
            frag_i = d.get("fragment_index") or 0
            frag_n = d.get("fragment_count") or 0

            pct = 0.0
            if total and done:
                pct = done * 100.0 / total
            elif frag_n and frag_i:
                pct = frag_i * 100.0 / frag_n

            overall = phase_start + (pct / 100.0) * (phase_end - phase_start)
            if overall > last[0]:
                last[0] = overall
                task["progress"] = int(round(overall))

            speed = d.get("speed")
            if speed:
                if speed > 1024 * 1024:
                    task["speed_display"] = f"{speed / 1024 / 1024:.1f} MB/s"
                elif speed > 1024:
                    task["speed_display"] = f"{speed / 1024:.0f} KB/s"
                else:
                    task["speed_display"] = f"{speed:.0f} B/s"
            task["eta"] = d.get("eta") or 0
            task["downloaded"] = done or frag_i
            task["total"] = total or frag_n
        elif d.get("status") == "finished":
            task["progress"] = int(round(phase_end))
            task["speed_display"] = ""

    return hook


def watchdog(task, start_progress, max_progress, interval=10):
    """Nudge progress forward so the UI never looks frozen."""
    current = start_progress
    while not task.get("stopped") and current < max_progress:
        time.sleep(interval)
        current = task.get("progress", current)
        if current < max_progress:
            current += 1
            task["progress"] = current


def download_stream(task, url, fmt_id, out_path, phase_start, phase_end, label):
    opts = base_ydl_opts()
    opts.update(
        {
            "format": fmt_id,
            "outtmpl": out_path,
            "logger": TaskLogger(task),
            "progress_hooks": [progress_hook(task, phase_start, phase_end)],
        }
    )
    log(task, label)
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
    if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
        raise RuntimeError(f"{label} failed (empty file)")


def run_ffmpeg(args, timeout=3600):
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "ffmpeg failed: " + proc.stderr.decode("utf-8", "replace")[-400:]
        )


# --------------------------------------------------------------------------- #
# Background jobs
# --------------------------------------------------------------------------- #


def job_single(task, url, video_id, audio_id, start_sec, end_sec, filename):
    video_ext = ".mp4"
    out_name = sanitize_filename(filename, f"download_{task['id'][:8]}.mp4")
    out_path = os.path.join(DOWNLOAD_DIR, f"{task['id']}_{out_name}")

    with tempfile.TemporaryDirectory(dir=DOWNLOAD_DIR) as tmp:
        temp_video = os.path.join(tmp, "video.mp4")
        temp_audio = os.path.join(tmp, "audio.m4a")

        task["status"] = "downloading_video"
        task["progress"] = 1
        threading.Thread(
            target=watchdog, args=(task, 2, 38, 10), daemon=True
        ).start()

        download_stream(task, url, video_id, temp_video, 2, 40, "Downloading video...")
        if task["stopped"]:
            return

        task["status"] = "downloading_audio"
        task["progress"] = 40
        audio_try = [audio_id, "139", "140", "bestaudio[ext=m4a]/bestaudio"]
        done = False
        last_error = None
        for candidate in dict.fromkeys(a for a in audio_try if a):
            try:
                download_stream(
                    task, url, candidate, temp_audio, 40, 70, f"Downloading audio ({candidate})..."
                )
                done = True
                break
            except Exception as exc:  # try the next audio format
                last_error = exc
                log(task, f"Audio format {candidate} failed: {friendly_error(exc)}")
                if os.path.exists(temp_audio):
                    try:
                        os.remove(temp_audio)
                    except OSError:
                        pass
        if not done:
            raise RuntimeError(friendly_error(last_error) if last_error else "Audio download failed")
        if task["stopped"]:
            return

        task["status"] = "merging"
        task["progress"] = 70
        log(task, "Merging video and audio...")

        args = [
            "-i", temp_video,
            "-i", temp_audio,
            "-map", "0:v:0",
            "-map", "1:a:0",
        ]
        if start_sec is not None and end_sec is not None:
            duration = max(0, end_sec - start_sec)
            args = [
                "-ss", str(start_sec), "-i", temp_video,
                "-ss", str(start_sec), "-i", temp_audio,
                "-map", "0:v:0", "-map", "1:a:0",
                "-t", str(duration),
            ]
        args += ["-c", "copy", "-shortest", "-y", out_path]
        run_ffmpeg(args)
        task["progress"] = 100

    size = os.path.getsize(out_path)
    task["output_file"] = out_path
    task["output_filename"] = out_name
    task["downloaded"] = size
    task["total"] = size
    task["status"] = "complete"
    log(task, "Ready!")


def job_chapters(task, url, video_id, chapters, filename):
    base_name = sanitize_filename(filename, "chapters")
    base_stem = os.path.splitext(base_name)[0]
    zip_path = os.path.join(DOWNLOAD_DIR, f"{task['id']}_{base_stem}.zip")

    with tempfile.TemporaryDirectory(dir=DOWNLOAD_DIR) as tmp:
        temp_video = os.path.join(tmp, "video.mp4")
        temp_audio = os.path.join(tmp, "audio.m4a")

        task["status"] = "downloading_video"
        threading.Thread(target=watchdog, args=(task, 2, 55, 10), daemon=True).start()

        download_stream(task, url, video_id, temp_video, 2, 60, "Downloading video...")
        if task["stopped"]:
            return

        task["status"] = "downloading_audio"
        task["progress"] = 60
        done = False
        last_error = None
        for candidate in ("140", "139", "bestaudio[ext=m4a]/bestaudio"):
            try:
                download_stream(
                    task, url, candidate, temp_audio, 60, 70, f"Downloading audio ({candidate})..."
                )
                done = True
                break
            except Exception as exc:
                last_error = exc
                log(task, f"Audio format {candidate} failed: {friendly_error(exc)}")
                if os.path.exists(temp_audio):
                    try:
                        os.remove(temp_audio)
                    except OSError:
                        pass
        if not done:
            raise RuntimeError(friendly_error(last_error) if last_error else "Audio download failed")

        task["status"] = "cutting"
        total = len(chapters)
        parts = []
        for index, chapter in enumerate(chapters):
            if task["stopped"]:
                return
            start = chapter["start_time"]
            end = chapter["end_time"] + (1 if index == total - 1 else 0)
            duration = max(1, end - start)
            title = re.sub(r"[^A-Za-z0-9\u0600-\u06FF _-]", "", chapter.get("title") or "")
            title = (title.strip() or f"part{index + 1}")[:60]
            part_path = os.path.join(tmp, f"{index + 1:02d} - {title}.mp4")
            log(task, f"Cutting chapter {index + 1}/{total}: {chapter.get('title', '')}")
            run_ffmpeg(
                [
                    "-ss", str(start), "-i", temp_video,
                    "-ss", str(start), "-i", temp_audio,
                    "-map", "0:v:0", "-map", "1:a:0",
                    "-t", str(duration),
                    "-c", "copy", "-shortest", "-y", part_path,
                ]
            )
            parts.append(part_path)
            task["progress"] = 70 + int((index + 1) / total * 25)

        log(task, "Packing chapters into a zip...")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as zf:
            for part in parts:
                zf.write(part, os.path.basename(part))

    size = os.path.getsize(zip_path)
    task["output_file"] = zip_path
    task["output_filename"] = f"{base_stem}.zip"
    task["downloaded"] = size
    task["total"] = size
    task["status"] = "complete"
    task["progress"] = 100
    log(task, "Ready!")


def start_job(task, target, *args, **kwargs):
    def runner():
        try:
            target(task, *args, **kwargs)
        except Exception as exc:
            if task.get("stopped"):
                task["status"] = "stopped"
                log(task, "Stopped.")
            else:
                task["status"] = "error"
                task["error"] = friendly_error(exc)
                log(task, "Error: " + friendly_error(exc))
                log(task, traceback.format_exc()[-600:])
        finally:
            task["finished"] = time.time()
            SLOTS.release()

    threading.Thread(target=runner, daemon=True).start()


# --------------------------------------------------------------------------- #
# Cleanup thread
# --------------------------------------------------------------------------- #


def cleanup_loop():
    while True:
        time.sleep(60)
        now = time.time()

        # 1) age based cleanup. Disabled by default (FILE_TTL = 0) so a visitor
        #    on a slow connection can take as long as needed.
        if FILE_TTL > 0:
            with TASKS_LOCK:
                stale = [
                    tid
                    for tid, t in TASKS.items()
                    if now - t.get("created", now) > FILE_TTL and not t.get("expired")
                ]
            expire_tasks(stale)

        # 2) disk cap - oldest files go first so the server never runs out
        enforce_storage_cap()

        # 3) keep memory flat: old task records only need status + filename
        with TASKS_LOCK:
            for task in TASKS.values():
                if (
                    task.get("status") in ("complete", "error", "stopped")
                    and now - task.get("created", now) > 7200
                    and task.get("logs")
                ):
                    task["logs"] = []

        # 4) unreachable leftovers (crashed jobs) that no task points to
        with TASKS_LOCK:
            referenced = {
                t.get("output_file") for t in TASKS.values() if t.get("output_file")
            }
        for name in os.listdir(DOWNLOAD_DIR):
            full = os.path.join(DOWNLOAD_DIR, name)
            if full in referenced or os.path.isdir(full):
                continue
            try:
                if now - os.path.getmtime(full) > 6 * 3600:
                    os.remove(full)
            except OSError:
                pass


def expire_tasks(task_ids):
    """Remove the file but keep the task so the visitor gets a clear message."""
    for tid in task_ids:
        with TASKS_LOCK:
            task = TASKS.get(tid)
            if not task:
                continue
            path = task.get("output_file")
            task["expired"] = True
            task["output_file"] = None
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass


def purge_orphans_on_start():
    """Files left by a previous run can never be downloaded again (jobs live in
    memory), so free the disk instead of letting them pile up. Only touch files
    older than 15 minutes so a second local instance is never wiped."""
    if os.environ.get("PURGE_ON_START", "1") != "1":
        return
    cutoff = time.time() - 900
    removed = 0
    for name in os.listdir(DOWNLOAD_DIR):
        full = os.path.join(DOWNLOAD_DIR, name)
        try:
            if os.path.getmtime(full) > cutoff:
                continue
            if os.path.isdir(full):
                shutil.rmtree(full, ignore_errors=True)
            else:
                os.remove(full)
            removed += 1
        except OSError:
            pass
    if removed:
        print(f"[startup] cleared {removed} orphaned file(s) from {DOWNLOAD_DIR}")


def enforce_storage_cap():
    if MAX_STORAGE_MB <= 0:
        return
    cap = MAX_STORAGE_MB * 1024 * 1024
    entries = []
    with TASKS_LOCK:
        for tid, task in TASKS.items():
            path = task.get("output_file")
            if not path or not os.path.exists(path):
                continue
            try:
                entries.append((os.path.getmtime(path), tid, path, os.path.getsize(path)))
            except OSError:
                continue
    total = sum(e[3] for e in entries)
    if total <= cap:
        return
    entries.sort()  # oldest access first
    to_remove = []
    for _mtime, tid, _path, size in entries:
        if total <= cap:
            break
        to_remove.append(tid)
        total -= size
    if to_remove:
        print(
            f"[cleanup] storage over {MAX_STORAGE_MB} MB - "
            f"removing {len(to_remove)} old file(s)"
        )
        expire_tasks(to_remove)


threading.Thread(target=cleanup_loop, daemon=True).start()
purge_orphans_on_start()

# --------------------------------------------------------------------------- #
# Rate limiting (very small, in-memory, per IP)
# --------------------------------------------------------------------------- #

RATE = {}
RATE_LOCK = threading.Lock()


def rate_limited(ip, bucket, limit, window):
    now = time.time()
    key = (ip, bucket)
    with RATE_LOCK:
        hits = [t for t in RATE.get(key, []) if now - t < window]
        if len(hits) >= limit:
            RATE[key] = hits
            return True
        hits.append(now)
        RATE[key] = hits
    return False


def client_ip():
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "?"


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #


@app.after_request
def add_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    # Adsterra needs the origin in the Referer to validate the site. "same-origin"
    # sent nothing at all, which is why the popunder never fired.
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    if request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/")
def index():
    return render_template(
        "index.html",
        ffmpeg_ok=is_ffmpeg_available(),
        js_ok=bool(JS_RUNTIMES),
        max_height=MAX_HEIGHT,
        ttl_minutes=0 if FILE_TTL == 0 else max(1, FILE_TTL // 60),
        storage_gb=round(MAX_STORAGE_MB / 1024, 1) if MAX_STORAGE_MB else 0,
    )


@app.route("/healthz")
def healthz():
    return jsonify(
        {
            "ok": True,
            "ffmpeg": is_ffmpeg_available(),
            "js_runtime": JS_RUNTIMES,
            "cookies": bool(COOKIE_FILE),
            "active_tasks": len(TASKS),
            "file_ttl": FILE_TTL,
            "max_storage_mb": MAX_STORAGE_MB,
            "free_disk_mb": int(free_disk_mb()),
        }
    )


@app.route("/api/fetch", methods=["POST"])
def api_fetch():
    if rate_limited(client_ip(), "fetch", RATE_FETCH, 3600):
        return jsonify({"error": "Too many requests. Please wait a while."}), 429

    data = request.get_json(silent=True) or {}
    try:
        url = normalize_url(data.get("url"))
    except ValueError:
        return jsonify({"error": "Please enter a valid YouTube link."}), 400

    try:
        opts = base_ydl_opts()
        opts.update({"listformats": True, "skip_download": True})
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if info.get("_type") == "playlist":
            entries = info.get("entries") or []
            if entries:
                info = entries[0]

        height_limit = MAX_HEIGHT
        duration = info.get("duration") or 0
        if MAX_DURATION and duration and duration > MAX_DURATION:
            return (
                jsonify(
                    {
                        "error": f"This video is longer than the {MAX_DURATION // 60} minute limit of this server."
                    }
                ),
                400,
            )

        video_formats = []
        audio_formats = []
        for f in info.get("formats") or []:
            ext = (f.get("ext") or "").lower()
            vcodec = (f.get("vcodec") or "none").lower()
            acodec = f.get("acodec") or "none"
            height = f.get("height") or 0
            protocol = (f.get("protocol") or "").lower()
            if height_limit and height > height_limit:
                continue
            # YouTube lists every stream twice: a direct https file and an HLS
            # (m3u8) variant with the same quality. Keeping both is what made
            # the list show "1080p" twice, and the HLS one has no file size.
            if protocol not in ("https", "http"):
                continue
            if f.get("has_drm"):
                continue
            if ext == "mp4" and vcodec.startswith("avc1") and acodec == "none":
                video_formats.append(
                    {
                        "format_id": f.get("format_id"),
                        "format_note": f.get("format_note") or f"{height}p",
                        "ext": ext,
                        "vcodec": vcodec,
                        "height": height,
                        "fps": f.get("fps"),
                        "filesize": f.get("filesize") or f.get("filesize_approx"),
                        "tbr": f.get("tbr") or 0,
                    }
                )
            elif ext in ("mp4", "m4a") and vcodec == "none" and acodec != "none":
                abr = f.get("abr") or 0
                audio_formats.append(
                    {
                        "format_id": f.get("format_id"),
                        "format_note": f.get("format_note") or f"{int(abr)}kbps",
                        "ext": ext,
                        "acodec": acodec,
                        "abr": abr,
                        "quality": "HIGH" if abr >= 128 else "LOW",
                        "filesize": f.get("filesize") or f.get("filesize_approx"),
                        "tbr": f.get("tbr") or 0,
                    }
                )

        video_formats = dedupe_video_formats(video_formats)
        audio_formats = dedupe_audio_formats(audio_formats)
        video_formats.sort(key=lambda f: (f["height"] or 0, f["fps"] or 0), reverse=True)
        audio_formats.sort(key=lambda f: f["abr"], reverse=True)

        if not video_formats:
            return (
                jsonify(
                    {
                        "error": "This video has no H.264 (MP4) stream available. Try another video."
                    }
                ),
                400,
            )

        chapters = []
        for ch in info.get("chapters") or []:
            chapters.append(
                {
                    "title": ch.get("title") or "Chapter",
                    "start_time": round(ch.get("start_time") or 0, 2),
                    "end_time": round(ch.get("end_time") or 0, 2),
                    "start_display": format_time(ch.get("start_time") or 0),
                    "end_display": format_time(ch.get("end_time") or 0),
                }
            )

        return jsonify(
            {
                "title": info.get("title") or "Unknown",
                "duration": duration,
                "thumbnail": info.get("thumbnail") or "",
                "uploader": info.get("uploader") or "",
                "video_formats": video_formats,
                "audio_formats": audio_formats,
                "chapters": chapters,
            }
        )
    except Exception as exc:
        return jsonify({"error": friendly_error(exc)}), 400


@app.route("/api/download", methods=["POST"])
def api_download():
    if not is_ffmpeg_available():
        return jsonify({"error": "Server is missing ffmpeg."}), 500
    if free_disk_mb() < 700:
        return jsonify({"error": "Server storage is full. Try again later."}), 503
    if not SLOTS.acquire(blocking=False):
        return jsonify({"error": "Server is busy. Please try again in a moment."}), 429
    if rate_limited(client_ip(), "download", RATE_DOWNLOAD, 3600):
        SLOTS.release()
        return jsonify({"error": "Too many downloads from your network. Try later."}), 429

    data = request.get_json(silent=True) or {}
    try:
        url = normalize_url(data.get("url"))
    except ValueError:
        SLOTS.release()
        return jsonify({"error": "Please enter a valid YouTube link."}), 400

    video_id = str(data.get("video_format_id") or "")
    audio_id = str(data.get("audio_format_id") or "")
    if not FORMAT_RE.match(video_id) or not FORMAT_RE.match(audio_id):
        SLOTS.release()
        return jsonify({"error": "Please pick a video and an audio format."}), 400

    mode = (data.get("mode") or "full").lower()
    filename = data.get("filename") or ""
    start_sec = end_sec = None
    if mode == "trim":
        start_raw = str(data.get("start_time") or "").strip()
        end_raw = str(data.get("end_time") or "").strip()
        if not TIME_RE.match(start_raw) or not TIME_RE.match(end_raw):
            SLOTS.release()
            return jsonify({"error": "Use HH:MM:SS for the start and end time."}), 400
        try:
            start_sec = time_to_seconds(start_raw)
            end_sec = time_to_seconds(end_raw)
        except ValueError:
            SLOTS.release()
            return jsonify({"error": "Invalid time."}), 400
        if end_sec <= start_sec:
            SLOTS.release()
            return jsonify({"error": "End time must be after start time."}), 400
        if filename:
            stem = os.path.splitext(sanitize_filename(filename))[0]
            filename = stem + ".mp4"

    task = new_task()
    start_job(task, job_single, url, video_id, audio_id, start_sec, end_sec, filename)
    return jsonify({"task_id": task["id"]})


@app.route("/api/chapters", methods=["POST"])
def api_chapters():
    if not is_ffmpeg_available():
        return jsonify({"error": "Server is missing ffmpeg."}), 500
    if free_disk_mb() < 700:
        return jsonify({"error": "Server storage is full. Try again later."}), 503
    if not SLOTS.acquire(blocking=False):
        return jsonify({"error": "Server is busy. Please try again in a moment."}), 429

    data = request.get_json(silent=True) or {}
    try:
        url = normalize_url(data.get("url"))
    except ValueError:
        SLOTS.release()
        return jsonify({"error": "Please enter a valid YouTube link."}), 400

    video_id = str(data.get("video_format_id") or "")
    if not FORMAT_RE.match(video_id):
        SLOTS.release()
        return jsonify({"error": "Please pick a video format."}), 400

    chapters = data.get("chapters") or []
    if not isinstance(chapters, list) or not chapters:
        SLOTS.release()
        return jsonify({"error": "No chapters selected."}), 400
    if len(chapters) > 50:
        SLOTS.release()
        return jsonify({"error": "Too many chapters (max 50)."}), 400

    clean = []
    for ch in chapters:
        try:
            start = max(0.0, float(ch.get("start_time")))
            end = float(ch.get("end_time"))
        except (TypeError, ValueError):
            SLOTS.release()
            return jsonify({"error": "Invalid chapter data."}), 400
        if end <= start:
            SLOTS.release()
            return jsonify({"error": "Invalid chapter range."}), 400
        clean.append(
            {"title": str(ch.get("title") or "Chapter")[:80], "start_time": start, "end_time": end}
        )

    task = new_task()
    start_job(task, job_chapters, url, video_id, clean, data.get("filename") or "")
    return jsonify({"task_id": task["id"]})


@app.route("/api/status/<task_id>")
def api_status(task_id):
    with TASKS_LOCK:
        task = TASKS.get(task_id)
        if not task:
            return jsonify({"error": "Task not found"}), 404
        eta = task.get("eta") or 0
        if eta > 3600:
            eta_str = f"{eta // 3600}h {(eta % 3600) // 60}m"
        elif eta > 60:
            eta_str = f"{eta // 60}m {eta % 60}s"
        elif eta:
            eta_str = f"{eta}s"
        else:
            eta_str = ""

        size = ""
        if task.get("downloaded"):
            size = human_size(task["downloaded"])
            if task.get("total"):
                size += " / " + human_size(task["total"])

        return jsonify(
            {
                "status": task["status"],
                "progress": task["progress"],
                "error": task.get("error"),
                "speed": task.get("speed_display") or "",
                "eta": eta_str,
                "size": size,
                "output_filename": task.get("output_filename"),
                "logs": task.get("logs", [])[-60:],
                "can_download": task["status"] == "complete"
                and not task.get("expired")
                and bool(task.get("output_file")),
                "expired": bool(task.get("expired")),
            }
        )


@app.route("/api/stop/<task_id>", methods=["POST"])
def api_stop(task_id):
    with TASKS_LOCK:
        task = TASKS.get(task_id)
        if task:
            task["stopped"] = True
            if task["status"] not in ("complete", "error"):
                task["status"] = "stopped"
    return jsonify({"ok": True})


@app.route("/api/result/<task_id>")
def api_result(task_id):
    with TASKS_LOCK:
        task = TASKS.get(task_id)
        if not task:
            return jsonify({"error": "Task not found"}), 404
        if task["status"] != "complete":
            return jsonify({"error": "Not ready"}), 400
        path = task.get("output_file")
        name = task.get("output_filename") or "download.mp4"

    if not path or not os.path.exists(path):
        return jsonify({"error": "This file was removed to free disk space. Please download again."}), 410

    # mark as recently used so the storage cap removes other (older) files first
    try:
        os.utime(path)
    except OSError:
        pass

    return send_file(path, as_attachment=True, download_name=name, conditional=True)


if __name__ == "__main__":
    print(f"Listening on http://0.0.0.0:{PORT}  (ffmpeg={is_ffmpeg_available()}, js={JS_RUNTIMES})")
    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)
