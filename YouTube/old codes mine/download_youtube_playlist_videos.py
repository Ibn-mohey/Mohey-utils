!pip install -q yt_dlp
import os
import re
import glob
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from yt_dlp import YoutubeDL

# Accept:
# 1) a single video URL
# 2) a playlist URL
# 3) a Python list of URLs mixed together
youtube_inputs = '''
https://www.youtube.com/playlist?list=PLgtqMzuQ7viodeYrAiZa1NUba_e0zNLpl
'''.splitlines()
youtube_inputs = [x.strip() for x in youtube_inputs if x.strip()]
# youtube_inputs

# output_dir = '/content/downloaded_videos'
output_dir = '/content/drive/MyDrive/Download/downloaded_videos'

os.makedirs(output_dir, exist_ok=True)

MAX_WORKERS = 4


def safe_name(name: str) -> str:
    name = re.sub(r'[\\/*?:"<>|]', '_', name)
    return name.strip()


def run_ffmpeg_convert(input_file: str, final_file: str):
    """
    Keep video as-is, re-encode audio to Opus 48 kHz, write final MKV.
    """
    temp_file = final_file + '.tmp.mkv'

    cmd = [
        'ffmpeg', '-y',
        '-i', input_file,
        '-c:v', 'copy',
        '-c:a', 'libopus',
        '-ar', '48000',
        temp_file
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if os.path.exists(final_file):
        os.remove(final_file)
    os.replace(temp_file, final_file)


def find_existing_variants(title: str, output_path: str):
    safe_title = safe_name(title)
    patterns = [
        os.path.join(output_path, safe_title + '.mkv'),
        os.path.join(output_path, safe_title + '.webm'),
        os.path.join(output_path, safe_title + '.mp4'),
        os.path.join(output_path, safe_title + '.f*.mp4'),
        os.path.join(output_path, safe_title + '.f*.webm'),
        os.path.join(output_path, safe_title + '.f*.mkv'),
    ]

    found = set()
    for pattern in patterns:
        for f in glob.glob(pattern):
            found.add(f)

    return sorted(found)


def is_already_converted(final_file: str) -> bool:
    return os.path.exists(final_file) and os.path.getsize(final_file) > 0


def cleanup_variants(files):
    for f in files:
        try:
            if os.path.exists(f):
                os.remove(f)
        except Exception:
            pass


def process_video(entry, output_path, quality='720'):
    """
    Rules:
    - if final converted mkv exists => skip
    - if partial/raw exists but final mkv missing => delete and redownload
    - then convert to final mkv
    """
    try:
        video_url = entry['webpage_url']
        title = safe_name(entry['title'])
        final_file = os.path.join(output_path, f'{title}.mkv')

        if is_already_converted(final_file):
            return f'SKIP: {title} already converted'

        existing = find_existing_variants(title, output_path)
        if existing:
            cleanup_variants(existing)

        temp_template = os.path.join(output_path, f'{title}.%(ext)s')

        ydl_opts = {
            'format': (
                f'bestvideo[height<={quality}][vcodec^=vp9]+bestaudio[acodec^=opus]/'
                f'bestvideo[height<={quality}]+bestaudio/'
                f'best[height<={quality}]'
            ),
            'outtmpl': temp_template,
            'cookiefile': '/content/aa.txt',
            'merge_output_format': 'mkv',
            'ignoreerrors': False,
            'noplaylist': True,
            'quiet': True,
            'verbose': False,
        }

        with YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(video_url, download=True)

        candidates = find_existing_variants(title, output_path)
        raw_candidates = [
            c for c in candidates
            if os.path.abspath(c) != os.path.abspath(final_file)
        ]

        input_file = None
        if raw_candidates:
            input_file = raw_candidates[0]
        elif os.path.exists(final_file):
            input_file = final_file
        else:
            return f'ERROR: {title} downloaded file not found'

        if os.path.abspath(input_file) == os.path.abspath(final_file):
            temp_input = final_file + '.source_copy.mkv'
            shutil.move(final_file, temp_input)
            try:
                run_ffmpeg_convert(temp_input, final_file)
            finally:
                if os.path.exists(temp_input):
                    os.remove(temp_input)
        else:
            run_ffmpeg_convert(input_file, final_file)
            if os.path.exists(input_file):
                os.remove(input_file)

        return f'DONE: {title}'

    except Exception as e:
        return f'ERROR: {entry.get("title", "unknown")} -> {e}'


def normalize_inputs(inputs):
    """
    Accept string or list of strings.
    """
    if isinstance(inputs, str):
        return [inputs]
    if isinstance(inputs, (list, tuple, set)):
        return [x for x in inputs if isinstance(x, str) and x.strip()]
    raise ValueError("youtube_inputs must be a string or a list of strings")


def extract_entries_from_url(url):
    """
    If URL is a playlist => expand all videos.
    If URL is a single video => return one entry.
    """
    opts = {
        'extract_flat': True,
        'skip_download': True,
        'ignoreerrors': True,
        'quiet': True,
    }

    collected = []

    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if not info:
        return collected

    # Playlist / multi-entry result
    if 'entries' in info and info['entries'] is not None:
        for entry in info['entries']:
            if not entry:
                continue

            video_id = entry.get('id')
            title = entry.get('title') or video_id or 'unknown_video'

            entry_url = entry.get('url')
            if entry_url and not str(entry_url).startswith('http'):
                entry_url = f'https://www.youtube.com/watch?v={entry_url}'
            elif not entry_url and video_id:
                entry_url = f'https://www.youtube.com/watch?v={video_id}'

            if entry_url:
                collected.append({
                    'title': title,
                    'webpage_url': entry_url
                })
    else:
        # Single video result
        title = info.get('title') or info.get('id') or 'unknown_video'
        webpage_url = info.get('webpage_url') or url

        collected.append({
            'title': title,
            'webpage_url': webpage_url
        })

    return collected


def collect_all_entries(youtube_inputs):
    """
    Expand mixed inputs into one deduplicated video list.
    """
    urls = normalize_inputs(youtube_inputs)
    all_entries = []
    seen_urls = set()

    for url in urls:
        try:
            entries = extract_entries_from_url(url)
            for entry in entries:
                video_url = entry['webpage_url']
                if video_url not in seen_urls:
                    seen_urls.add(video_url)
                    all_entries.append(entry)
        except Exception as e:
            print(f'ERROR reading input {url} -> {e}')

    return all_entries


# ---- collect entries from all inputs ----
entries = collect_all_entries(youtube_inputs)

print(f'Found {len(entries)} videos total')

# ---- threaded processing ----
results = []
with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = [
        executor.submit(process_video, entry, output_dir, '480')
        for entry in entries
    ]

    for future in as_completed(futures):
        msg = future.result()
        print(msg)
        results.append(msg)

print('\nFinished.')
print(f'Files saved in: {output_dir}')


!pip install -q yt_dlp
import os
import re
import glob
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from yt_dlp import YoutubeDL

youtube_playlist_url = 'https://www.youtube.com/watch?v=x8DE4DprAzY'

output_dir = '/content/downloaded_videos'
os.makedirs(output_dir, exist_ok=True)

MAX_WORKERS = 4   # increase carefully in Colab if needed


def safe_name(name: str) -> str:
    """
    Match yt-dlp/Windows-ish filename sanitization enough for lookup.
    Not perfect, but good enough for skipping/redownloading logic.
    """
    name = re.sub(r'[\\/*?:"<>|]', '_', name)
    return name.strip()


def run_ffmpeg_convert(input_file: str, final_file: str):
    """
    Keep video as-is, re-encode audio to Opus 48 kHz, write final MKV.
    """
    temp_file = final_file + '.tmp.mkv'

    cmd = [
        'ffmpeg', '-y',
        '-i', input_file,
        '-c:v', 'copy',
        '-c:a', 'libopus',
        '-ar', '48000',
        temp_file
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if os.path.exists(final_file):
        os.remove(final_file)
    os.replace(temp_file, final_file)


def find_existing_variants(title: str, output_path: str):
    """
    Return possible existing files for a title.
    """
    safe_title = safe_name(title)
    patterns = [
        os.path.join(output_path, safe_title + '.mkv'),
        os.path.join(output_path, safe_title + '.webm'),
        os.path.join(output_path, safe_title + '.mp4'),
        os.path.join(output_path, safe_title + '.f*.mp4'),
        os.path.join(output_path, safe_title + '.f*.webm'),
        os.path.join(output_path, safe_title + '.f*.mkv'),
    ]

    found = set()
    for pattern in patterns:
        for f in glob.glob(pattern):
            found.add(f)

    return sorted(found)


def is_already_converted(final_file: str) -> bool:
    """
    We treat the final MKV as 'done'.
    """
    return os.path.exists(final_file) and os.path.getsize(final_file) > 0


def cleanup_variants(files):
    for f in files:
        try:
            if os.path.exists(f):
                os.remove(f)
        except Exception:
            pass


def process_video(entry, output_path,quality='720'):
    """
    Rules:
    - if final converted mkv exists => skip
    - if partial/raw exists but final mkv missing => delete and redownload
    - then convert to final mkv
    """
    try:
        video_url = entry['webpage_url']
        title = safe_name(entry['title'])
        final_file = os.path.join(output_path, f'{title}.mkv')

        # 1) already converted => skip
        if is_already_converted(final_file):
            return f'SKIP: {title} already converted'

        # 2) raw exists but not converted => delete and redownload
        existing = find_existing_variants(title, output_path)
        if existing:
            cleanup_variants(existing)

        temp_template = os.path.join(output_path, f'{title}.%(ext)s')

        ydl_opts = {
            'format': (
                f'bestvideo[height<={quality}][vcodec^=vp9]+bestaudio[acodec^=opus]/'
                f'bestvideo[height<={quality}]+bestaudio/'
                f'best[height<={quality}]'
            ),
            'outtmpl': temp_template,
            'cookiefile': '/content/aa.txt',
            'merge_output_format': 'mkv',
            'ignoreerrors': False,
            'noplaylist': True,
            'quiet': True,
            'verbose': False,
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)

        # after download, locate the downloaded file
        candidates = find_existing_variants(title, output_path)

        # exclude final_file if somehow already there empty/corrupt logic weirdness
        raw_candidates = [c for c in candidates if os.path.abspath(c) != os.path.abspath(final_file)]

        # if yt-dlp already produced final mkv, use it as input too
        input_file = None
        if raw_candidates:
            input_file = raw_candidates[0]
        elif os.path.exists(final_file):
            input_file = final_file
            # convert in-place safely through temp naming
        else:
            return f'ERROR: {title} downloaded file not found'

        # convert to final mkv with 48k audio
        if os.path.abspath(input_file) == os.path.abspath(final_file):
            temp_input = final_file + '.source_copy.mkv'
            shutil.move(final_file, temp_input)
            try:
                run_ffmpeg_convert(temp_input, final_file)
            finally:
                if os.path.exists(temp_input):
                    os.remove(temp_input)
        else:
            run_ffmpeg_convert(input_file, final_file)
            if os.path.exists(input_file):
                os.remove(input_file)

        return f'DONE: {title}'

    except Exception as e:
        return f'ERROR: {entry.get("title", "unknown")} -> {e}'


# ---- get playlist entries with title + full URL ----
playlist_opts = {
    'extract_flat': True,
    'skip_download': True,
    'ignoreerrors': True,
    'quiet': True,
}

entries = []
with YoutubeDL(playlist_opts) as ydl:
    info = ydl.extract_info(youtube_playlist_url, download=False)
    if 'entries' in info:
        for entry in info['entries']:
            if not entry:
                continue

            video_id = entry.get('id')
            title = entry.get('title') or video_id or 'unknown_video'

            url = entry.get('url')
            if url and not str(url).startswith('http'):
                url = f'https://www.youtube.com/watch?v={url}'
            elif not url and video_id:
                url = f'https://www.youtube.com/watch?v={video_id}'

            if url:
                entries.append({
                    'title': title,
                    'webpage_url': url
                })

print(f'Found {len(entries)} videos')

# ---- threaded processing ----
results = []
with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = [executor.submit(process_video, entry, output_dir,'480') for entry in entries]

    for future in as_completed(futures):
        msg = future.result()
        print(msg)
        results.append(msg)

print('\nFinished.')
print(f'Files saved in: {output_dir}')