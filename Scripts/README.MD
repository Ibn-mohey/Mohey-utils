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

## YouTube Playlist Extractor (Tampermonkey)

**File:** `youtube_playlist_extractor.user.js`

A Tampermonkey userscript version of the YouTube Playlist Extractor. Provides multiple ways to trigger playlist export without manually pasting code in the console.

### Features

- **Menu Commands** — Two Tampermonkey menu entries:
  - *Export Playlist to CSV* — full export with auto-scrolling
  - *Export Playlist (No Scroll)* — quick export of already-loaded videos
- **Floating Button** — A red `📥 Export Playlist CSV` button appears in the bottom-right corner on playlist pages, with visual loading/success/error states
- **GM_download** — Uses Tampermonkey's native download API with automatic fallback to the standard browser download method
- Same comprehensive metadata extraction as the console version

### Installation

1. Install [Tampermonkey](https://www.tampermonkey.net/) browser extension
2. Click the Tampermonkey icon → **Create a new script**
3. Delete the default content and paste the contents of [`youtube_playlist_extractor.user.js`](https://github.com/Ibn-mohey/Mohey-utils/blob/main/Scripts/youtube_playlist_extractor.user.js)
4. Press **Ctrl+S** to save
5. Navigate to any YouTube playlist — the export button appears automatically

### Usage

- **Floating button:** Click the red button on any playlist page
- **Menu command:** Click the Tampermonkey icon → choose an export option
- Works on any `youtube.com` page; button only shows on playlist pages

---

## Facebook Reels Scroll Blocker

**File:** `facebook_reels_blocker.user.js`

A Tampermonkey/Greasemonkey userscript that prevents automatic navigation between Facebook Reels. Stops you from accidentally scrolling, clicking, or swiping to the next reel. Works both when opening reels via direct link and from the Facebook feed.

### Features

- **Blocks programmatic scrolling** – intercepts `scrollTo`, `scrollBy`, and `scrollTop` on reel containers so Facebook cannot navigate between reels
- **Blocks keyboard navigation** – disables Arrow keys, PageUp/PageDown on reels
- **Blocks touch swipe** – prevents mobile-style swipe navigation
- **Disables navigation arrows** – neutralizes the Next/Previous Card buttons
- **Stops auto-loop** – video plays once then pauses; click the video or press Space to replay
- **Removes preloaded reels** – prevents Facebook from loading extra reels in the background
- **SPA-aware** – hooks into `history.pushState`/`replaceState` so it works when navigating from the Facebook feed without a full page reload
- **Non-intrusive** – all other controls (sound, like, comment, share) remain fully functional

### Installation

#### From Greasy Fork (recommended)
1. Install [Tampermonkey](https://www.tampermonkey.net/) browser extension
2. Visit the script page on [Greasy Fork](https://greasyfork.org/en/scripts/578323-facebook-reels-scroll-blocker) and click **Install**

#### Manual Install
1. Install [Tampermonkey](https://www.tampermonkey.net/) browser extension
2. Click the Tampermonkey icon → **Create a new script**
3. Go to my GitHub page [here](https://github.com/Ibn-mohey/Mohey-utils/blob/main/Scripts/facebook_reels_blocker.user.js)
4. Delete the default content and paste the contents of [`facebook_reels_blocker.user.js`](https://github.com/Ibn-mohey/Mohey-utils/blob/main/Scripts/facebook_reels_blocker.user.js)
5. Press **Ctrl+S** to save
6. The script activates automatically on Facebook Reels pages

### How It Works

- **Intercepts programmatic scroll methods** (`scrollTo`, `scrollBy`, `scrollTop` setter) on containers with video elements — this is how Facebook actually moves between reels regardless of whether you clicked an arrow, an edge zone, or used keyboard
- **Hooks `history.pushState`/`replaceState`** to detect SPA navigation from the Facebook feed and re-attach all observers
- Uses `MutationObserver` to continuously detect and neutralize navigation arrow buttons as Facebook re-renders them
- Replaces arrow elements with inert clones that have no event listeners
- Detects reels by URL (`/reel/`, `/reels/`), presence of arrow buttons, or a dialog overlay containing video
- Removes extra preloaded reel children from the DOM to keep only the current reel

### Notes

- Works on all `facebook.com/*` pages — activates only when a reel is detected
- You can still pause/play, mute/unmute, like, comment, and share
- The navigation arrows appear dimmed to indicate they are disabled