# Scripts

This directory contains utility scripts for various tasks.

## YouTube Playlist Extractor

**File:** `Youtube_list_extractor.JS`

A JavaScript script that extracts YouTube playlist data and exports it to CSV format. This script is designed to be run directly in the browser console while viewing a YouTube playlist.

### Features

- Automatically scrolls through the entire playlist to load all videos
- Extracts comprehensive metadata for each video including:
  - Playlist index
  - Video title and URL
  - Video ID
  - Channel name and URL
  - Duration
  - View count and publish date
  - Watch status and progress
  - Thumbnail URL
- Exports data to CSV format with proper escaping
- Auto-generates filename based on playlist title

### Usage

1. Navigate to a YouTube playlist in your browser
2. Open the browser developer console (F12)
3. Copy and paste the entire script content
4. Press Enter to execute
5. The script will automatically scroll through the playlist and download a CSV file

### Configuration Options

You can customize the script behavior by passing options:

```javascript
scrapeYouTubePlaylistToCSV({
  fileName: 'my-playlist.csv',    // Custom filename
  autoScroll: true,               // Enable auto-scrolling (default: true)
  maxScrollRounds: 200,           // Maximum scroll attempts (default: 200)
  delayMs: 700                    // Delay between scrolls in ms (default: 700)
});
```

### Output Format

The CSV file contains the following columns:
- `playlist_index` - Position in playlist
- `title` - Video title
- `video_id` - YouTube video ID
- `video_url` - Full video URL
- `playlist_id` - YouTube playlist ID
- `start_time` - Timestamp parameter if present
- `channel` - Channel name
- `channel_url` - Channel URL
- `duration` - Video duration
- `duration_label` - Accessibility duration label
- `views_text` - View count text
- `published_text` - Publication date text
- `watched_status` - Watch completion status
- `watch_progress` - Watch progress percentage
- `thumbnail_url` - Video thumbnail URL
- `aria_label` - Accessibility label

### Notes

- The script uses auto-scrolling to load all videos in large playlists
- CSV output includes UTF-8 BOM for proper Unicode support
- All text fields are properly escaped for CSV format
- Works with both public and private playlists (if you have access)

### Requirements

- Modern web browser with JavaScript enabled
- Access to YouTube playlist page
- Developer console access

---

## Facebook Reels Scroll Blocker

**File:** `facebook_reels_blocker.user.js`

A Tampermonkey/Greasemonkey userscript that prevents automatic navigation between Facebook Reels. Stops you from accidentally scrolling or clicking to the next reel.

### Features

- **Blocks scroll/wheel** – prevents moving to the next/previous reel by scrolling
- **Blocks keyboard navigation** – disables Arrow keys, Space, PageUp/PageDown on reels
- **Blocks touch swipe** – prevents mobile-style swipe navigation
- **Disables navigation arrows** – neutralizes the Next/Previous Card buttons
- **Stops auto-loop** – video plays once then pauses; click or press Space to replay
- **Non-intrusive** – all other controls (sound, like, comment, share) remain fully functional

### Installation

#### From Greasy Fork (recommended)
1. Install [Tampermonkey](https://www.tampermonkey.net/) browser extension
2. Visit the script page on [Greasy Fork](https://greasyfork.org/en/scripts/578323-facebook-reels-scroll-blocker) and click **Install**

#### Manual Install
1. Install [Tampermonkey](https://www.tampermonkey.net/) browser extension
2. Click the Tampermonkey icon → **Create a new script**
3. go to my github Page [here](https://github.com/Ibn-mohey/Mohey-utils/blob/main/Scripts/facebook_reels_blocker.user.js)
3. Delete the default content and paste the contents of [`facebook_reels_blocker.user.js`](https://github.com/Ibn-mohey/Mohey-utils/blob/main/Scripts/facebook_reels_blocker.user.js)
4. Press **Ctrl+S** to save
5. The script activates automatically on Facebook Reels pages

### How It Works

- Intercepts scroll, keyboard, and pointer events in the **capture phase** before Facebook can handle them
- Uses a `MutationObserver` to continuously detect and neutralize navigation arrow buttons as Facebook re-renders them
- Replaces arrow elements with inert clones that have no event listeners
- Only targets navigation-specific elements — other interactive buttons are unaffected

### Notes

- Works on `facebook.com/reel/*` and `facebook.com/reels/*` URLs
- You can still pause/play, mute/unmute, like, comment, and share
- The navigation arrows appear dimmed to indicate they are disabled