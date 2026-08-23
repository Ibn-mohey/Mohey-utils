"""
YouTube Toolkit — unified Colab utility for:
  • Extracting playlist/video metadata to CSV/JSON
  • Downloading audio-only and converting to Opus
  • Downloading video and converting to MKV with Opus audio

Usage (Colab):
  Put your URLs in `youtube_inputs`, pick a MODE, and run.
"""

# ── Colab installs ──────────────────────────────────────────────────────────
# !apt-get update -qq && apt-get install -y -qq ffmpeg
# !curl -fsSL https://deno.land/install.sh | sh && echo 'export PATH="$HOME/.deno/bin:$PATH"' >> ~/.bashrc && export PATH="$HOME/.deno/bin:$PATH"
# !pip install -q -U yt-dlp pandas libsql

import os
import re
import json
import glob
import time
import shutil
import subprocess
import threading
import atexit
import libsql
import pandas as pd
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from yt_dlp import YoutubeDL

# ═══════════════════════════════════════════════════════════════════════════
# CONFIG — edit these before running
# ═══════════════════════════════════════════════════════════════════════════

youtube_inputs = """
https://www.youtube.com/playlist?list=PLgtqMzuQ7viodeYrAiZa1NUba_e0zNLpl
""".strip().splitlines()
youtube_inputs = [u.strip() for u in youtube_inputs if u.strip()]

# "info"      → metadata only (CSV + JSON)
# "audio"     → download audio, convert with custom codec/bitrate
# "video"     → download video, re-encode audio to Opus in MKV
# "broadcast" → download audio, convert to Opus @ 22k (speech-optimized)
MODE = "video"

OUTPUT_DIR = "/content/downloaded_videos"
AUDIO_DIR = "/content/downloaded_audio"
BROADCAST_DIR = "/content/downloaded_broadcast"
INFO_DIR = "/content/playlist_info"

# ── Video settings ──────────────────────────────────────────────────────────
VIDEO_QUALITY = "720"          # 360 / 480 / 720 / 1080
VIDEO_CODEC = "copy"           # See codec comparison below
VIDEO_BITRATE = None           # None = auto | "2M" | "1500k" | "3M" etc.

# ┌─────────────────────────────────────────────────────────────────────────┐
# │  VIDEO CODEC COMPARISON  (approximate for 10 min 720p video)           │
# ├───────────────┬──────────┬────────┬────────────┬───────────────────────┤
# │ Codec         │ Size     │ Speed  │ Quality    │ Notes                 │
# ├───────────────┼──────────┼────────┼────────────┼───────────────────────┤
# │ copy          │ ~150 MB  │ ⚡ instant│ original│ No re-encode, just    │
# │               │ (as-is)  │        │            │ remux. Fastest.       │
# ├───────────────┼──────────┼────────┼────────────┼───────────────────────┤
# │ libx264 (H264)│ ~80 MB   │ 🟢 fast │ great    │ Universal support.    │
# │   @ 2M br     │ ~40 MB   │        │ good      │ Best compat/speed     │
# │   @ 1M br     │ ~20 MB   │        │ decent    │ trade-off.            │
# ├───────────────┼──────────┼────────┼────────────┼───────────────────────┤
# │ libx265 (HEVC)│ ~40 MB   │ 🟡 slow │ great    │ ~50% smaller than     │
# │   @ 1M br     │ ~20 MB   │        │ good      │ H264 at same quality. │
# │   @ 500k br   │ ~10 MB   │        │ decent    │ Slower encode.        │
# ├───────────────┼──────────┼────────┼────────────┼───────────────────────┤
# │ libvpx-vp9    │ ~40 MB   │ 🟡 slow │ great    │ ~50% smaller than     │
# │   @ 1M br     │ ~20 MB   │        │ good      │ H264. Open/royalty-   │
# │   @ 500k br   │ ~10 MB   │        │ decent    │ free. WebM native.    │
# ├───────────────┼──────────┼────────┼────────────┼───────────────────────┤
# │ libaom-av1    │ ~30 MB   │ 🔴 v.slow│ excellent│ ~30% smaller than    │
# │   @ 800k br   │ ~15 MB   │        │ great     │ HEVC/VP9. Best        │
# │   @ 400k br   │ ~8 MB    │        │ good      │ compression. Very     │
# │               │          │        │           │ slow encode on CPU.   │
# └───────────────┴──────────┴────────┴────────────┴───────────────────────┘
#
# RECOMMENDATIONS:
#   • Storage priority  → libaom-av1  (smallest, but very slow encode)
#   • Balanced          → libx265     (good compression, moderate speed)
#   • Speed priority    → copy        (no re-encode) or libx264 (fast)
#   • Compatibility     → libx264     (plays everywhere)
#   • WebM/web playback → libvpx-vp9  (royalty-free, browser-native)

# ── Audio settings ──────────────────────────────────────────────────────────
AUDIO_CODEC = "libopus"        # See audio codec comparison below
AUDIO_BITRATE = "48k"          # opus/aac/mp3 bitrate
AUDIO_SAMPLE_RATE = "48000"    # sample rate in Hz

# ┌──────────────────────────────────────────────────────────────────────────┐
# │  AUDIO CODEC COMPARISON  (approximate for 10 min audio)                 │
# ├──────────────┬─────────┬────────┬────────────┬─────────────────────────┤
# │ Codec        │ Size    │ Speed  │ Quality    │ Notes                   │
# ├──────────────┼─────────┼────────┼────────────┼─────────────────────────┤
# │ libopus      │         │ 🟢 fast │            │ Best quality/size ratio │
# │   @ 128k     │ ~9.4 MB │        │ excellent  │ Transparent quality.    │
# │   @ 48k      │ ~3.5 MB │        │ great      │ Great for speech+music. │
# │   @ 22k      │ ~1.6 MB │        │ good       │ Good for speech.        │
# │   @ 11k      │ ~0.8 MB │        │ usable     │ Min for speech. Mono.   │
# │   @ 6k       │ ~0.4 MB │        │ low        │ Barely intelligible.    │
# ├──────────────┼─────────┼────────┼────────────┼─────────────────────────┤
# │ aac          │         │ 🟢 fast │            │ Universal compat.       │
# │   @ 128k     │ ~9.4 MB │        │ great      │ Standard quality.       │
# │   @ 64k      │ ~4.7 MB │        │ good       │ Decent for speech.      │
# │   @ 32k      │ ~2.3 MB │        │ fair       │ Noticeable artifacts.   │
# │   (no 11k)   │   —     │        │  —         │ Min usable ~32k.        │
# ├──────────────┼─────────┼────────┼────────────┼─────────────────────────┤
# │ libmp3lame   │         │ 🟢 fast │            │ Legacy support.         │
# │   @ 128k     │ ~9.4 MB │        │ good       │ Standard MP3 quality.   │
# │   @ 64k      │ ~4.7 MB │        │ fair       │ Audible compression.    │
# │   @ 32k      │ ~2.3 MB │        │ poor       │ Very compressed.        │
# │   (no 11k)   │   —     │        │  —         │ Min usable ~32k.        │
# ├──────────────┼─────────┼────────┼────────────┼─────────────────────────┤
# │ copy         │ varies  │ ⚡ instant│ original │ No re-encode, as-is.   │
# └──────────────┴─────────┴────────┴────────────┴─────────────────────────┘
#
# KEY TAKEAWAY: Opus crushes everything at low bitrates.
#   @ 48k Opus  ≈  @ 96k AAC  ≈  @ 128k MP3  (similar perceived quality)
#   @ 22k Opus  = good speech — AAC/MP3 can't go this low usably.
#   @ 11k Opus  = minimum viable speech (mono, telephone quality)
#
# RECOMMENDATIONS:
#   • Music             → libopus @ 128k  or  aac @ 128k
#   • Speech + music    → libopus @ 48k
#   • Speech/podcasts   → libopus @ 22k   (tiny files, clear speech)
#   • Ultra-compact     → libopus @ 11k   (0.8 MB per 10 min!)
#   • Max compatibility → aac @ 128k      (plays on everything)
#   • Legacy devices    → libmp3lame @ 128k

# ── General ─────────────────────────────────────────────────────────────────
OUTPUT_FORMAT = "mkv"          # container: "mkv" | "mp4" | "webm"
MAX_WORKERS = 4                # parallel download threads
MAX_CONVERT_WORKERS = 2        # parallel ffmpeg conversion threads (background)
MAX_RETRIES = 3
RETRY_DELAY = 5                # seconds between retries

# Optional: path to a Netscape-format cookies file (set to None to skip)
COOKIE_FILE = "/content/aa.txt"

# SQLite progress database (set to None to disable tracking)
# If the file doesn't exist it will be created automatically.
PROGRESS_DB = "/content/youtubeprogress.db"

# ── Turso Cloud DB (optional — overrides local PROGRESS_DB) ────────────────
# Sign up free: https://turso.tech  →  turso db create youtube-progress
# Get URL:   turso db show --url youtube-progress
# Get token: turso db tokens create youtube-progress
# Store as Colab Secrets: TURSO_DB_URL and TURSO_AUTH_TOKEN
try:
    from google.colab import userdata
    TURSO_DB_URL = userdata.get('TURSO_DB_URL')
    TURSO_AUTH_TOKEN = userdata.get('TURSO_AUTH_TOKEN')
except (ImportError, Exception):
    # Not running on Colab or secrets not set — disable Turso
    TURSO_DB_URL = ""
    TURSO_AUTH_TOKEN = ""


# ═══════════════════════════════════════════════════════════════════════════
# PROGRESS DATABASE  (SQLite)
# ═══════════════════════════════════════════════════════════════════════════

_DB_INIT_SQL = """
CREATE TABLE IF NOT EXISTS progress (
    video_id      TEXT    NOT NULL,
    title         TEXT,
    playlist_id   TEXT,
    playlist_title TEXT,
    url           TEXT    NOT NULL,
    mode          TEXT    NOT NULL,          -- 'video' | 'audio' | 'info'
    status        TEXT    NOT NULL DEFAULT 'pending',
                                            -- pending → downloaded → converted → done | error
    quality       TEXT,
    video_codec   TEXT,
    video_bitrate TEXT,
    audio_codec   TEXT,
    audio_bitrate TEXT,
    output_file   TEXT,
    error_msg     TEXT,
    created_at    TEXT    NOT NULL,
    updated_at    TEXT    NOT NULL,
    PRIMARY KEY (video_id, mode)
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# Global lock for SQLite — ensures only one thread writes at a time
_db_lock = threading.Lock()
# Global connection — reused across calls, auto-closed on kernel exit
_db_conn: libsql.Connection | None = None


def _close_db():
    """Close the global DB connection (called by atexit)."""
    global _db_conn
    if _db_conn is not None:
        try:
            _db_conn.close()
        except Exception:
            pass
        _db_conn = None

atexit.register(_close_db)


def db_connect(db_path: str | None) -> libsql.Connection | None:
    """Open (and initialise) the progress DB.
    If TURSO_DB_URL is set, connects to Turso Cloud (remote).
    Otherwise falls back to a local SQLite file via libsql.
    Reuses a single global connection. Returns None if tracking is off.
    """
    global _db_conn
    if not db_path and not TURSO_DB_URL:
        return None
    # If we already have a working connection, reuse it
    if _db_conn is not None:
        try:
            _db_conn.execute("SELECT 1")  # ping — is it still alive?
            return _db_conn
        except Exception:
            # Stale/broken connection — close and reconnect
            try:
                _db_conn.close()
            except Exception:
                pass
            _db_conn = None
    try:
        if TURSO_DB_URL and TURSO_AUTH_TOKEN:
            # ── Turso Cloud (remote over HTTP) ──
            print(f"☁ Connecting to Turso Cloud: {TURSO_DB_URL}")
            conn = libsql.connect(database=TURSO_DB_URL, auth_token=TURSO_AUTH_TOKEN)
        else:
            # ── Local SQLite file via libsql ──
            if not os.path.exists(db_path):
                print(f"📁 Creating new progress DB: {db_path}")
            conn = libsql.connect(database=db_path)
            conn.execute("PRAGMA journal_mode=WAL;")
        conn.executescript(_DB_INIT_SQL)
        _db_conn = conn
        return conn
    except Exception as e:
        print(f"⚠ Could not open progress DB ({db_path}): {e}  — continuing without tracking")
        return None


def db_is_done(conn: libsql.Connection | None, video_id: str, mode: str) -> bool:
    """Return True if this video_id+mode is already fully done."""
    if conn is None:
        return False
    try:
        with _db_lock:
            row = conn.execute(
                "SELECT status FROM progress WHERE video_id=? AND mode=?",
                (video_id, mode),
            ).fetchone()
        return row is not None and row[0] == 'done'
    except Exception:
        return False


def db_upsert(conn: libsql.Connection | None, **kw):
    """Insert or update a progress row.  Pass any column as keyword arg."""
    if conn is None:
        return
    now = _now()
    kw.setdefault('created_at', now)
    kw['updated_at'] = now

    cols = list(kw.keys())
    placeholders = ', '.join('?' for _ in cols)
    updates = ', '.join(f'{c}=excluded.{c}' for c in cols if c != 'created_at')
    # keep original created_at on conflict
    updates += ', created_at=progress.created_at'

    sql = (
        f"INSERT INTO progress ({', '.join(cols)}) VALUES ({placeholders}) "
        f"ON CONFLICT(video_id, mode) DO UPDATE SET {updates}"
    )
    with _db_lock:
        conn.execute(sql, [kw[c] for c in cols])
        conn.commit()


# ═══════════════════════════════════════════════════════════════════════════
# SHARED UTILITIES
# ═══════════════════════════════════════════════════════════════════════════

# Map audio codecs to their typical file extensions
_AUDIO_EXT = {
    'libopus': 'opus',
    'aac': 'm4a',
    'libmp3lame': 'mp3',
    'copy': 'opus',    # fallback — original stream extension varies
}


def audio_ext() -> str:
    """Return the file extension matching the configured AUDIO_CODEC."""
    return _AUDIO_EXT.get(AUDIO_CODEC, 'ogg')


def safe_name(name: str) -> str:
    """Sanitize a string for use as a filename."""
    name = re.sub(r'[\\/*?:"<>|]', '_', name)
    return name.strip().rstrip('.')


def get_cookie_opt() -> dict:
    """Return cookiefile option only if the file exists."""
    if COOKIE_FILE and os.path.exists(COOKIE_FILE):
        return {'cookiefile': COOKIE_FILE}
    return {}


def video_id_from_url(url: str) -> str:
    """Extract the 11-char YouTube video ID from a URL."""
    m = re.search(r'(?:v=|youtu\.be/)([\w-]{11})', url)
    return m.group(1) if m else url


def playlist_id_from_url(url: str) -> str | None:
    """Extract playlist ID from a URL, or None."""
    m = re.search(r'list=([\w-]+)', url)
    return m.group(1) if m else None


def retry(fn, *args, retries=MAX_RETRIES, delay=RETRY_DELAY, label=""):
    """Call *fn* up to *retries* times, with a delay between failures."""
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            return fn(*args)
        except Exception as e:
            last_err = e
            if attempt < retries:
                print(f"  ⚠ {label} attempt {attempt} failed: {e}  — retrying in {delay}s")
                time.sleep(delay)
    raise last_err


def list_formats(url: str) -> str:
    """List available formats for a video URL. Returns formatted string."""
    opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        **get_cookie_opt(),
    }
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    if not info or 'formats' not in info:
        return "  (no formats found)"
    lines = []
    lines.append(f"  {'ID':<12} {'EXT':<6} {'RES':<10} {'VCODEC':<14} {'ACODEC':<14} {'SIZE':<10} {'NOTE'}")
    lines.append(f"  {'─'*12} {'─'*6} {'─'*10} {'─'*14} {'─'*14} {'─'*10} {'─'*20}")
    for f in info['formats']:
        fid = f.get('format_id', '?')
        ext = f.get('ext', '?')
        res = f.get('resolution') or f"{f.get('width', '?')}x{f.get('height', '?')}"
        vcodec = (f.get('vcodec') or 'none')[:13]
        acodec = (f.get('acodec') or 'none')[:13]
        fsize = f.get('filesize') or f.get('filesize_approx')
        size_str = f"{fsize / 1024 / 1024:.1f}MB" if fsize else '?'
        note = (f.get('format_note') or '')[:20]
        lines.append(f"  {fid:<12} {ext:<6} {res:<10} {vcodec:<14} {acodec:<14} {size_str:<10} {note}")
    return '\n'.join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# ENTRY EXTRACTION  (shared by all modes)
# ═══════════════════════════════════════════════════════════════════════════

def extract_entries_from_url(url: str) -> list[dict]:
    """
    Expand a URL into a list of {'title', 'webpage_url'} dicts.
    Works for single videos, playlists, and mixes.
    """
    opts = {
        'extract_flat': True,
        'skip_download': True,
        'ignoreerrors': True,
        'quiet': True,
        **get_cookie_opt(),
    }

    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if not info:
        return []

    collected = []

    pl_id = info.get('id') if info.get('_type') == 'playlist' else playlist_id_from_url(url)
    pl_title = info.get('title') if pl_id else None

    if 'entries' in info and info['entries']:
        for entry in info['entries']:
            if not entry:
                continue
            vid = entry.get('id')
            title = entry.get('title') or vid or 'unknown_video'
            entry_url = entry.get('url') or entry.get('webpage_url')
            if entry_url and not str(entry_url).startswith('http'):
                entry_url = f'https://www.youtube.com/watch?v={entry_url}'
            elif not entry_url and vid:
                entry_url = f'https://www.youtube.com/watch?v={vid}'
            if entry_url:
                collected.append({
                    'title': title,
                    'webpage_url': entry_url,
                    'video_id': vid or video_id_from_url(entry_url),
                    'playlist_id': pl_id,
                    'playlist_title': pl_title,
                })
    else:
        title = info.get('title') or info.get('id') or 'unknown_video'
        webpage_url = info.get('webpage_url') or url
        collected.append({
            'title': title,
            'webpage_url': webpage_url,
            'video_id': info.get('id') or video_id_from_url(webpage_url),
            'playlist_id': pl_id,
            'playlist_title': pl_title,
        })

    return collected


def collect_all_entries(inputs: list[str]) -> list[dict]:
    """Deduplicate and collect entries from a list of URLs."""
    all_entries = []
    seen = set()
    for url in inputs:
        try:
            for entry in retry(extract_entries_from_url, url, label=url):
                if entry['webpage_url'] not in seen:
                    seen.add(entry['webpage_url'])
                    all_entries.append(entry)
        except Exception as e:
            print(f"ERROR reading {url}: {e}")
    return all_entries


# ═══════════════════════════════════════════════════════════════════════════
# MODE: INFO — extract metadata to CSV + JSON
# ═══════════════════════════════════════════════════════════════════════════

def extract_full_metadata(url: str) -> tuple[str, list[dict]]:
    """Return (playlist_name, [video_info_dicts]) with full metadata."""
    opts = {
        'quiet': True,
        'extract_flat': False,
        'skip_download': True,
        'ignoreerrors': True,
        **get_cookie_opt(),
    }
    with YoutubeDL(opts) as ydl:
        result = ydl.extract_info(url, download=False)

    if not result or 'entries' not in result:
        return ('unknown', [])

    playlist_name = safe_name(
        f"{result.get('title', 'playlist')}_{result.get('id', 'unknown')}"
    )

    videos = []
    for idx, entry in enumerate(result['entries'], 1):
        if entry is None:
            print(f"  Warning: skipping None entry at position {idx}")
            continue
        videos.append({
            'index': idx,
            'title': entry.get('title', 'N/A'),
            'duration': entry.get('duration_string')
                        or f"{(entry.get('duration') or 0) // 60} min",
            'published': entry.get('upload_date'),
            'views': entry.get('view_count'),
        })

    return playlist_name, videos


def run_info_mode(inputs: list[str], out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    for url in inputs:
        try:
            name, videos = retry(extract_full_metadata, url, label=url)
        except Exception as e:
            print(f"ERROR extracting info for {url}: {e}")
            continue

        if not videos:
            print(f"No entries found for {url}")
            continue

        json_path = os.path.join(out_dir, f"{name}.json")
        csv_path = os.path.join(out_dir, f"{name}.csv")

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(videos, f, ensure_ascii=False, indent=4)

        pd.DataFrame(videos).to_csv(csv_path, index=False)
        print(f"✓ Saved {len(videos)} videos → {csv_path}")


# ═══════════════════════════════════════════════════════════════════════════
# MODE: AUDIO — download + convert to Opus
# ═══════════════════════════════════════════════════════════════════════════

def _download_audio(entry: dict, out_dir: str, conn) -> tuple[str, str, str]:
    """Download only. Returns (title, vid, raw_file_path). Blocks on network I/O."""
    title = safe_name(entry['title'])
    vid = entry['video_id']

    db_upsert(conn, video_id=vid, title=title, url=entry['webpage_url'],
              playlist_id=entry.get('playlist_id'), playlist_title=entry.get('playlist_title'),
              mode='audio', status='pending')

    temp_dir = os.path.join(out_dir, '_temp_wav')
    os.makedirs(temp_dir, exist_ok=True)

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(temp_dir, f'{title}.%(ext)s'),
        'noplaylist': True,
        'quiet': True,
        **get_cookie_opt(),
    }

    def _do():
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(entry['webpage_url'], download=True)
            return ydl.prepare_filename(info)

    raw_file = retry(_do, label=title)
    db_upsert(conn, video_id=vid, mode='audio', status='downloaded')
    print(f"  ↓ Downloaded: {title}")
    return title, vid, raw_file


def _convert_audio(title: str, vid: str, raw_file: str, out_dir: str, conn) -> str:
    """Convert raw audio to final format. Runs in background pool."""
    ext = audio_ext()
    final_path = os.path.join(out_dir, f"{title}.{ext}")

    cmd = [
        'ffmpeg', '-y', '-i', raw_file,
        '-c:a', AUDIO_CODEC, '-b:a', AUDIO_BITRATE,
        final_path
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if os.path.exists(raw_file):
        os.remove(raw_file)

    db_upsert(conn, video_id=vid, mode='audio', status='done',
              audio_codec=AUDIO_CODEC, audio_bitrate=AUDIO_BITRATE, output_file=final_path)
    return f"DONE: {title}"


def run_audio_mode(inputs: list[str], out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    conn = db_connect(PROGRESS_DB)
    all_entries = collect_all_entries(inputs)
    entries = [e for e in all_entries if not db_is_done(conn, e['video_id'], 'audio')]
    skipped = len(all_entries) - len(entries)
    print(f"Audio mode: {len(entries)} to process ({skipped} already done)")

    ext = audio_ext()
    results = []
    convert_pool = ThreadPoolExecutor(max_workers=MAX_CONVERT_WORKERS)
    convert_futures = []

    # Download pool — blocks only on download, then hands off to convert pool
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as dl_pool:
        dl_futures = {
            dl_pool.submit(_download_audio, e, out_dir, conn): e
            for e in entries
            if not (os.path.exists(os.path.join(out_dir, f"{safe_name(e['title'])}.{ext}"))
                    and os.path.getsize(os.path.join(out_dir, f"{safe_name(e['title'])}.{ext}")) > 0)
        }

        # Skip entries that already have final files
        for e in entries:
            fp = os.path.join(out_dir, f"{safe_name(e['title'])}.{ext}")
            if os.path.exists(fp) and os.path.getsize(fp) > 0:
                db_upsert(conn, video_id=e['video_id'], title=safe_name(e['title']),
                          url=e['webpage_url'], mode='audio', status='done',
                          output_file=fp)
                msg = f"SKIP: {safe_name(e['title'])}"
                print(msg)
                results.append(msg)

        for future in as_completed(dl_futures):
            entry = dl_futures[future]
            try:
                title, vid, raw_file = future.result()
                # Hand off to background conversion — does NOT block
                cf = convert_pool.submit(_convert_audio, title, vid, raw_file, out_dir, conn)
                convert_futures.append((cf, entry))
            except Exception as e:
                msg = f"ERROR: {entry['title']} → {e}"
                db_upsert(conn, video_id=entry['video_id'], title=entry['title'],
                          url=entry['webpage_url'], mode='audio',
                          status='error', error_msg=str(e))
                print(msg)
                results.append(msg)

    # Wait for all conversions to finish
    print("  ⏳ Waiting for background conversions...")
    for cf, entry in convert_futures:
        try:
            msg = cf.result()
        except Exception as e:
            msg = f"ERROR (convert): {entry['title']} → {e}"
            db_upsert(conn, video_id=entry['video_id'], title=entry['title'],
                      url=entry['webpage_url'], mode='audio',
                      status='error', error_msg=str(e))
        print(msg)
        results.append(msg)

    convert_pool.shutdown(wait=True)
    _print_summary(results, out_dir)


# ═══════════════════════════════════════════════════════════════════════════
# MODE: BROADCAST — download audio, Opus @ 22k (speech-optimized)
# ═══════════════════════════════════════════════════════════════════════════

BROADCAST_CODEC = "libopus"
BROADCAST_BITRATE = "22k"
BROADCAST_SAMPLE_RATE = "48000"


def _download_broadcast(entry: dict, out_dir: str, conn) -> tuple[str, str, str]:
    """Download only for broadcast. Returns (title, vid, raw_file_path)."""
    title = safe_name(entry['title'])
    vid = entry['video_id']

    db_upsert(conn, video_id=vid, title=title, url=entry['webpage_url'],
              playlist_id=entry.get('playlist_id'), playlist_title=entry.get('playlist_title'),
              mode='broadcast', status='pending')

    temp_dir = os.path.join(out_dir, '_temp_raw')
    os.makedirs(temp_dir, exist_ok=True)

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(temp_dir, f'{title}.%(ext)s'),
        'noplaylist': True,
        'quiet': True,
        **get_cookie_opt(),
    }

    def _do():
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(entry['webpage_url'], download=True)
            return ydl.prepare_filename(info)

    raw_file = retry(_do, label=title)
    db_upsert(conn, video_id=vid, mode='broadcast', status='downloaded')
    print(f"  ↓ Downloaded: {title}")
    return title, vid, raw_file


def _convert_broadcast(title: str, vid: str, raw_file: str, out_dir: str, conn) -> str:
    """Convert to broadcast Opus. Runs in background pool."""
    final_path = os.path.join(out_dir, f"{title}.opus")

    cmd = [
        'ffmpeg', '-y', '-i', raw_file,
        '-c:a', BROADCAST_CODEC,
        '-b:a', BROADCAST_BITRATE,
        '-ar', BROADCAST_SAMPLE_RATE,
        '-ac', '1',
        final_path
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if os.path.exists(raw_file):
        os.remove(raw_file)

    db_upsert(conn, video_id=vid, mode='broadcast', status='done',
              audio_codec=BROADCAST_CODEC, audio_bitrate=BROADCAST_BITRATE,
              output_file=final_path)
    return f"DONE: {title}"


def run_broadcast_mode(inputs: list[str], out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    conn = db_connect(PROGRESS_DB)
    entries = collect_all_entries(inputs)
    entries = [e for e in entries if not db_is_done(conn, e['video_id'], 'broadcast')]
    print(f"Broadcast mode: {len(entries)} to process (Opus mono @ {BROADCAST_BITRATE})")

    results = []
    convert_pool = ThreadPoolExecutor(max_workers=MAX_CONVERT_WORKERS)
    convert_futures = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as dl_pool:
        dl_futures = {
            dl_pool.submit(_download_broadcast, e, out_dir, conn): e
            for e in entries
            if not (os.path.exists(os.path.join(out_dir, f"{safe_name(e['title'])}.opus"))
                    and os.path.getsize(os.path.join(out_dir, f"{safe_name(e['title'])}.opus")) > 0)
        }

        for e in entries:
            fp = os.path.join(out_dir, f"{safe_name(e['title'])}.opus")
            if os.path.exists(fp) and os.path.getsize(fp) > 0:
                db_upsert(conn, video_id=e['video_id'], title=safe_name(e['title']),
                          url=e['webpage_url'], mode='broadcast', status='done',
                          output_file=fp)
                msg = f"SKIP: {safe_name(e['title'])}"
                print(msg)
                results.append(msg)

        for future in as_completed(dl_futures):
            entry = dl_futures[future]
            try:
                title, vid, raw_file = future.result()
                cf = convert_pool.submit(_convert_broadcast, title, vid, raw_file, out_dir, conn)
                convert_futures.append((cf, entry))
            except Exception as e:
                msg = f"ERROR: {entry['title']} → {e}"
                db_upsert(conn, video_id=entry['video_id'], title=entry['title'],
                          url=entry['webpage_url'], mode='broadcast',
                          status='error', error_msg=str(e))
                print(msg)
                results.append(msg)

    print("  ⏳ Waiting for background conversions...")
    for cf, entry in convert_futures:
        try:
            msg = cf.result()
        except Exception as e:
            msg = f"ERROR (convert): {entry['title']} → {e}"
            db_upsert(conn, video_id=entry['video_id'], title=entry['title'],
                      url=entry['webpage_url'], mode='broadcast',
                      status='error', error_msg=str(e))
        print(msg)
        results.append(msg)

    convert_pool.shutdown(wait=True)
    _print_summary(results, out_dir)


# ═══════════════════════════════════════════════════════════════════════════
# MODE: VIDEO — download + re-encode in configurable format
# ═══════════════════════════════════════════════════════════════════════════

def find_existing_variants(title: str, output_path: str) -> list[str]:
    safe_title = safe_name(title)
    patterns = [
        safe_title + ext
        for ext in ('.mkv', '.webm', '.mp4', '.f*.mp4', '.f*.webm', '.f*.mkv')
    ]
    found = set()
    for pat in patterns:
        for f in glob.glob(os.path.join(output_path, pat)):
            found.add(f)
    return sorted(found)


def run_ffmpeg_video_convert(input_file: str, final_file: str):
    """Re-encode with configurable video codec/bitrate and audio codec/bitrate."""
    temp_file = final_file + f'.tmp.{OUTPUT_FORMAT}'
    cmd = [
        'ffmpeg', '-y', '-i', input_file,
        '-c:v', VIDEO_CODEC,
    ]
    if VIDEO_CODEC != 'copy' and VIDEO_BITRATE:
        cmd += ['-b:v', VIDEO_BITRATE]
    cmd += [
        '-c:a', AUDIO_CODEC,
        '-b:a', AUDIO_BITRATE,
        '-ar', AUDIO_SAMPLE_RATE,
        temp_file,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(final_file):
        os.remove(final_file)
    os.replace(temp_file, final_file)


def _download_video(entry: dict, output_path: str, quality: str, conn) -> tuple[str, str, str]:
    """Download video only. Returns (title, vid, input_file_path)."""
    title = safe_name(entry['title'])
    vid = entry['video_id']
    final_file = os.path.join(output_path, f'{title}.{OUTPUT_FORMAT}')

    db_upsert(conn, video_id=vid, title=title, url=entry['webpage_url'],
              playlist_id=entry.get('playlist_id'), playlist_title=entry.get('playlist_title'),
              mode='video', status='pending', quality=quality)

    # clean up partial downloads
    for f in find_existing_variants(title, output_path):
        try:
            os.remove(f)
        except Exception:
            pass

    ydl_opts = {
        'format': (
            f'bestvideo[height<={quality}][vcodec^=vp9]+bestaudio[acodec^=opus]/'
            f'bestvideo[height<={quality}]+bestaudio/'
            f'best[height<={quality}]'
        ),
        'outtmpl': os.path.join(output_path, f'{title}.%(ext)s'),
        'merge_output_format': OUTPUT_FORMAT,
        'noplaylist': True,
        'quiet': True,
        **get_cookie_opt(),
    }

    def _do():
        with YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(entry['webpage_url'], download=True)

    try:
        retry(_do, label=title)
    except Exception as e:
        if 'Requested format is not available' in str(e):
            print(f"  ⚠ Format not available for {title} @ {quality}p — listing available formats:")
            try:
                print(list_formats(entry['webpage_url']))
            except Exception:
                print("  (could not list formats)")
            # Fallback: try 'best' (any quality)
            print(f"  ↻ Retrying with fallback format 'best'...")
            ydl_opts['format'] = 'best'
            def _do_fallback():
                with YoutubeDL(ydl_opts) as ydl:
                    ydl.extract_info(entry['webpage_url'], download=True)
            retry(_do_fallback, label=f"{title} (fallback)")
        else:
            raise
    db_upsert(conn, video_id=vid, mode='video', status='downloaded')
    print(f"  ↓ Downloaded: {title}")

    # locate downloaded file
    candidates = find_existing_variants(title, output_path)
    raw = [c for c in candidates if os.path.abspath(c) != os.path.abspath(final_file)]

    if raw:
        input_file = raw[0]
    elif os.path.exists(final_file):
        input_file = final_file
    else:
        raise FileNotFoundError(f"{title} — downloaded file not found")

    return title, vid, input_file


def _convert_video(title: str, vid: str, input_file: str, output_path: str, quality: str, conn) -> str:
    """Convert video with ffmpeg. Runs in background pool."""
    final_file = os.path.join(output_path, f'{title}.{OUTPUT_FORMAT}')

    if os.path.abspath(input_file) == os.path.abspath(final_file):
        tmp = final_file + f'.source.{OUTPUT_FORMAT}'
        shutil.move(final_file, tmp)
        try:
            run_ffmpeg_video_convert(tmp, final_file)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
    else:
        run_ffmpeg_video_convert(input_file, final_file)
        if os.path.exists(input_file):
            os.remove(input_file)

    db_upsert(conn, video_id=vid, mode='video', status='done',
              quality=quality,
              video_codec=VIDEO_CODEC, video_bitrate=VIDEO_BITRATE or 'auto',
              audio_codec=AUDIO_CODEC, audio_bitrate=AUDIO_BITRATE,
              output_file=final_file)
    return f"DONE: {title}"


def run_video_mode(inputs: list[str], out_dir: str, quality: str):
    os.makedirs(out_dir, exist_ok=True)
    conn = db_connect(PROGRESS_DB)
    entries = collect_all_entries(inputs)
    entries = [e for e in entries if not db_is_done(conn, e['video_id'], 'video')]
    print(f"Video mode: {len(entries)} videos to process")

    results = []
    convert_pool = ThreadPoolExecutor(max_workers=MAX_CONVERT_WORKERS)
    convert_futures = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as dl_pool:
        dl_futures = {}
        for e in entries:
            final = os.path.join(out_dir, f"{safe_name(e['title'])}.{OUTPUT_FORMAT}")
            if os.path.exists(final) and os.path.getsize(final) > 0:
                db_upsert(conn, video_id=e['video_id'], title=safe_name(e['title']),
                          url=e['webpage_url'], mode='video', status='done',
                          output_file=final)
                msg = f"SKIP: {safe_name(e['title'])}"
                print(msg)
                results.append(msg)
            else:
                dl_futures[dl_pool.submit(_download_video, e, out_dir, quality, conn)] = e

        for future in as_completed(dl_futures):
            entry = dl_futures[future]
            try:
                title, vid, input_file = future.result()
                cf = convert_pool.submit(_convert_video, title, vid, input_file, out_dir, quality, conn)
                convert_futures.append((cf, entry))
            except Exception as e:
                msg = f"ERROR: {entry['title']} → {e}"
                db_upsert(conn, video_id=entry['video_id'], title=entry['title'],
                          url=entry['webpage_url'], mode='video',
                          status='error', error_msg=str(e))
                print(msg)
                results.append(msg)

    print("  ⏳ Waiting for background conversions...")
    for cf, entry in convert_futures:
        try:
            msg = cf.result()
        except Exception as e:
            msg = f"ERROR (convert): {entry['title']} → {e}"
            db_upsert(conn, video_id=entry['video_id'], title=entry['title'],
                      url=entry['webpage_url'], mode='video',
                      status='error', error_msg=str(e))
        print(msg)
        results.append(msg)

    convert_pool.shutdown(wait=True)
    _print_summary(results, out_dir)


# ═══════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════

def _print_summary(results: list[str], out_dir: str):
    done = sum(1 for r in results if r.startswith("DONE"))
    skipped = sum(1 for r in results if r.startswith("SKIP"))
    errors = sum(1 for r in results if r.startswith("ERROR"))
    print(f"\n{'='*50}")
    print(f"Finished — ✓ {done} done, ⏭ {skipped} skipped, ✗ {errors} errors")
    print(f"Files in: {out_dir}")
    if errors:
        print("\nFailed:")
        for r in results:
            if r.startswith("ERROR"):
                print(f"  {r}")


# # ═══════════════════════════════════════════════════════════════════════════
# # MAIN
# # ═══════════════════════════════════════════════════════════════════════════

# if MODE == "info":
#     run_info_mode(youtube_inputs, INFO_DIR)
# elif MODE == "audio":
#     run_audio_mode(youtube_inputs, AUDIO_DIR)
# elif MODE == "broadcast":
#     run_broadcast_mode(youtube_inputs, BROADCAST_DIR)
# elif MODE == "video":
#     run_video_mode(youtube_inputs, OUTPUT_DIR, VIDEO_QUALITY)
# else:
#     print(f"Unknown MODE: {MODE!r}  — use 'info', 'audio', 'broadcast', or 'video'")


# # ═══════════════════════════════════════════════════════════════════════════
# # EXAMPLES — uncomment one block at a time to use
# # ═══════════════════════════════════════════════════════════════════════════

# # ── Example 1: INFO — extract playlist metadata to CSV + JSON ───────────
# youtube_inputs = """
# https://www.youtube.com/playlist?list=PLgtqMzuQ7viodeYrAiZa1NUba_e0zNLpl
# """.strip().splitlines()
# youtube_inputs = [u.strip() for u in youtube_inputs if u.strip()]
# MODE = "info"
# run_info_mode(youtube_inputs, "/content/playlist_info")
# # Output: /content/playlist_info/<playlist_name>.csv + .json

# # ── Example 2: AUDIO — download audio, custom codec & bitrate ──────────
# youtube_inputs = """
# https://www.youtube.com/watch?v=dQw4w9WgXcQ
# https://www.youtube.com/watch?v=jNQXAC9IVRw
# """.strip().splitlines()
# youtube_inputs = [u.strip() for u in youtube_inputs if u.strip()]
# AUDIO_CODEC = "libopus"
# AUDIO_BITRATE = "48k"
# MODE = "audio"
# run_audio_mode(youtube_inputs, "/content/downloaded_audio")
# # Output: /content/downloaded_audio/*.opus

# # ── Example 3: BROADCAST — speech-optimized mono Opus @ 22k ────────────
# youtube_inputs = """
# https://www.youtube.com/playlist?list=PLgtqMzuQ7viodeYrAiZa1NUba_e0zNLpl
# """.strip().splitlines()
# youtube_inputs = [u.strip() for u in youtube_inputs if u.strip()]
# MODE = "broadcast"
# run_broadcast_mode(youtube_inputs, "/content/downloaded_broadcast")
# # Output: /content/downloaded_broadcast/*.opus  (~1 MB per 10 min)

# # ── Example 4: VIDEO — download 720p, keep original video codec ────────
# youtube_inputs = """
# https://www.youtube.com/watch?v=dQw4w9WgXcQ
# """.strip().splitlines()
# youtube_inputs = [u.strip() for u in youtube_inputs if u.strip()]
# VIDEO_QUALITY = "720"
# VIDEO_CODEC = "copy"          # no re-encode, fastest
# AUDIO_CODEC = "libopus"
# AUDIO_BITRATE = "48k"
# OUTPUT_FORMAT = "mkv"
# MODE = "video"
# run_video_mode(youtube_inputs, "/content/downloaded_videos", VIDEO_QUALITY)
# # Output: /content/downloaded_videos/*.mkv

# # ── Example 5: VIDEO — re-encode to H264 @ 1.5M for smaller files ─────
# youtube_inputs = """
# https://www.youtube.com/playlist?list=PLgtqMzuQ7viodeYrAiZa1NUba_e0zNLpl
# """.strip().splitlines()
# youtube_inputs = [u.strip() for u in youtube_inputs if u.strip()]
# VIDEO_QUALITY = "480"
# VIDEO_CODEC = "libx264"
# VIDEO_BITRATE = "1500k"
# AUDIO_CODEC = "aac"
# AUDIO_BITRATE = "128k"
# OUTPUT_FORMAT = "mp4"         # mp4 for max compatibility
# MODE = "video"
# run_video_mode(youtube_inputs, "/content/downloaded_videos", VIDEO_QUALITY)
# # Output: /content/downloaded_videos/*.mp4  (small, plays everywhere)

# # ── Example 6: VIDEO — max compression with HEVC for storage ───────────
# youtube_inputs = """
# https://www.youtube.com/playlist?list=PLgtqMzuQ7viodeYrAiZa1NUba_e0zNLpl
# """.strip().splitlines()
# youtube_inputs = [u.strip() for u in youtube_inputs if u.strip()]
# VIDEO_QUALITY = "720"
# VIDEO_CODEC = "libx265"
# VIDEO_BITRATE = "1M"
# AUDIO_CODEC = "libopus"
# AUDIO_BITRATE = "48k"
# OUTPUT_FORMAT = "mkv"
# MODE = "video"
# run_video_mode(youtube_inputs, "/content/downloaded_videos", VIDEO_QUALITY)
# # Output: /content/downloaded_videos/*.mkv  (~50% smaller than H264)

# # ── Example 7: Mixed URLs — playlists + individual videos together ─────
# youtube_inputs = """
# https://www.youtube.com/playlist?list=PLgtqMzuQ7viodeYrAiZa1NUba_e0zNLpl
# https://www.youtube.com/watch?v=dQw4w9WgXcQ
# https://www.youtube.com/watch?v=jNQXAC9IVRw
# """.strip().splitlines()
# youtube_inputs = [u.strip() for u in youtube_inputs if u.strip()]
# # Duplicates are auto-removed. All processed in parallel.
# MODE = "video"
# run_video_mode(youtube_inputs, "/content/downloaded_videos", "720")
