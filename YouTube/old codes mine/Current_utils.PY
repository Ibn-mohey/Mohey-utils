!apt-get update -qq && apt-get install -y -qq nodejs
!pip install -q -U yt-dlp pydub

import os
import re
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from yt_dlp import YoutubeDL

os.makedirs('collected_opus', exist_ok=True)
os.makedirs('temp_opus', exist_ok=True)
os.makedirs('temp_wav', exist_ok=True)

MAX_CONCURRENT_DOWNLOADS = 5 # Set the maximum number of concurrent downloads/conversions

def safe_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = name.strip().rstrip('.')
    return name

def convert_and_download(temp_file: str):
    input_path = os.path.join('temp_wav', temp_file)
    temp_opus = os.path.join('temp_opus', temp_file.rsplit('.', 1)[0] + '.opus')
    final_output = os.path.join('collected_opus', os.path.basename(temp_opus))
    process = subprocess.Popen(
        ["ffmpeg", "-i", input_path, "-c:a", "libopus", "-b:a", "22k", "-y", temp_opus],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
    )
    stdout, stderr = process.communicate()
    if process.returncode == 0:
        if os.path.exists(input_path): os.remove(input_path)
        os.replace(temp_opus, final_output)
        print(f"Success: {final_output}")
    else:
        print(f"FFmpeg Error: {stderr}")

def download_single_video_audio(video_url: str, cookiefile: str = '/content/aa.txt'):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join('temp_wav', '%(title)s.%(ext)s'),
        'cookiefile': cookiefile if os.path.exists(cookiefile) else None,
        'quiet': False,
        'noplaylist': True,
        'javascript_filter': 'node', # Explicitly use node
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=True)
        filename = ydl.prepare_filename(info)

    # Conversion is still in a separate thread, but overall video processing is managed by ThreadPoolExecutor
    t = threading.Thread(target=convert_and_download, args=(os.path.basename(filename),))
    t.start()
    return t

def download_youtube_audio(url: str, cookiefile: str = '/content/aa.txt'):
    ydl_extract_opts = {
        'extract_flat': False,
        'cookiefile': cookiefile if os.path.exists(cookiefile) else None,
        'javascript_filter': 'node'
    }
    with YoutubeDL(ydl_extract_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    video_urls_to_process = []
    if info.get('_type') == 'playlist':
        for entry in info['entries']:
            if not entry: continue
            video_url = entry.get('webpage_url') or entry.get('url')
            if video_url:
                video_urls_to_process.append(video_url)
    else:
        video_urls_to_process.append(url)

    # Use ThreadPoolExecutor to limit concurrent downloads/conversions
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_DOWNLOADS) as executor:
        futures = [executor.submit(download_single_video_audio, v_url, cookiefile) for v_url in video_urls_to_process]
        # The main thread won't wait for these, as per previous instructions.
        # However, the executor itself will manage the `max_workers` concurrency.
