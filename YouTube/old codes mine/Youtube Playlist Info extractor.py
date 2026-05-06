import json
from yt_dlp import YoutubeDL
import pandas as pd
from google.colab import files

playlists = '''
https://www.youtube.com/playlist?list=PLZN_joVjvT6SSFfgNa4LV5eZKFb1gAzzj
'''.splitlines()

for playlist_url in playlists:
    ydl_opts = {
        'quiet': True,
        'extract_flat': False,
        'skip_download': True,
        'ignoreerrors': True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        try:
            pass
            result = ydl.extract_info(playlist_url, download=False)
        except Exception as e:
            print(f"Error extracting playlist info: {e}")
            continue

    if result is None or 'entries' not in result:
        print(f"No entries found for playlist: {playlist_url}")
        continue

    videos_data = []
    for idx, entry in enumerate(result['entries'], 1):
        if entry is None:
            print(f"Warning: Skipping None entry at position {idx}")
            continue

        title = entry.get('title', 'N/A')
        duration_seconds = entry.get('duration', 0)
        duration = entry.get('duration_string') or f"{duration_seconds//60} min"
        upload_date = entry.get('upload_date')
        views = entry.get('view_count')

        videos_data.append({
            'index': idx,
            'title': title,
            'duration': duration,
            'published': upload_date,
            'views': views
        })

    name = f"{result.get('title', 'playlist')}_{result.get('id', 'unknown')}"

    with open(f"{name}.json", 'w', encoding='utf-8') as f:
        json.dump(videos_data, f, ensure_ascii=False, indent=4)

    print(f"Saved {len(videos_data)} videos to {name}.json")
    df = pd.DataFrame(videos_data)
    df.to_csv(f"{name}.csv", index=False)
    files.download(f"{name}.csv")
