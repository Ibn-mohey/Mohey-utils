# YouTube Toolkit

A unified Google Colab utility for downloading and converting YouTube videos, audio, and playlist metadata — all from a single script.

> **Note:** This toolkit was created with the help of AI (GitHub Copilot), by merging and refactoring 3 original scripts I wrote:
> - `Current_utils.PY` — video download utility
> - `download_youtube_playlist_videos.py` — playlist video downloader
> - `Youtube Playlist Info extractor.py` — playlist metadata extractor
>
> The original files are preserved in the `old codes mine/` folder for reference.

## Features

- **4 Modes** in one script:
  - `info` — Extract playlist/video metadata to CSV + JSON
  - `audio` — Download audio and convert with configurable codec/bitrate
  - `video` — Download video and re-encode with configurable codec/quality
  - `broadcast` — Download audio, convert to Opus @ 22k mono (speech-optimized, ~1 MB per 10 min)

- **Configurable Codecs & Bitrates** with built-in comparison tables:
  - Video: `copy`, `libx264`, `libx265`, `libvpx-vp9`, `libaom-av1`
  - Audio: `libopus`, `aac`, `libmp3lame`, `copy`

- **Progress Tracking** via SQLite (local) or [Turso](https://turso.tech) (cloud):
  - Resumes where you left off — skips already-completed downloads
  - Tracks status: `pending → downloaded → converted → done | error`
  - Turso Cloud option for persistent tracking across Colab sessions (free tier)

- **Parallel Pipeline**:
  - Separate download pool (`MAX_WORKERS=4`) and conversion pool (`MAX_CONVERT_WORKERS=2`)
  - Downloads hand off to background ffmpeg conversion without blocking

- **Playlist & Single Video Support** — mix URLs freely, duplicates auto-removed

- **Cookie Support** — optional Netscape-format cookies file for age-restricted content

## Quick Start (Colab)

### 1. Install dependencies (first cell)
```python
!apt-get update -qq && apt-get install -y -qq nodejs ffmpeg
!pip install -q -U yt-dlp pandas libsql
```

### 2. Configure & run (second cell)
```python
youtube_inputs = """
https://www.youtube.com/playlist?list=YOUR_PLAYLIST_ID
https://www.youtube.com/watch?v=YOUR_VIDEO_ID
""".strip().splitlines()
youtube_inputs = [u.strip() for u in youtube_inputs if u.strip()]

MODE = "audio"  # "info" | "audio" | "video" | "broadcast"

# Then call the appropriate function:
run_audio_mode(youtube_inputs, "/content/downloaded_audio")
```

## Turso Cloud Setup (Optional)

For persistent progress tracking across Colab sessions:

1. Create a free account at [turso.tech](https://turso.tech)
2. Create a database and get your URL + auth token
3. Add them as **Colab Secrets** (🔑 in the left sidebar):
   - `TURSO_DB_URL` — your database URL (e.g. `libsql://your-db.turso.io`)
   - `TURSO_AUTH_TOKEN` — your auth token

The script auto-detects these secrets on Colab. If not set, it falls back to a local SQLite file.

## Codec Recommendations

| Goal | Video Codec | Audio Codec |
|------|-------------|-------------|
| Fastest (no re-encode) | `copy` | `copy` |
| Best compatibility | `libx264` | `aac @ 128k` |
| Smallest files | `libx265` or `libaom-av1` | `libopus @ 48k` |
| Speech/podcasts | — | `libopus @ 22k` (or use broadcast mode) |
| Ultra-compact speech | — | `libopus @ 11k` (~0.8 MB per 10 min) |

## Requirements

- Google Colab (or any Linux environment with Python 3.10+)
- `yt-dlp`, `pandas`, `ffmpeg`, `libsql`
- Optional: [Turso](https://turso.tech) account (free) for cloud progress tracking
