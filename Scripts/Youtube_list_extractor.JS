async function scrapeYouTubePlaylistToCSV({
  fileName = null, // Will be auto-generated from page header
  autoScroll = true,
  maxScrollRounds = 100, // Reduced from 200
  delayMs = 1000, // Increased from 700ms for better stability
  timeoutMs = 300000 // 5 minute timeout
} = {}) {
  console.log("🚀 Starting YouTube playlist extraction...");
  
  // Extract playlist name from page header
  function getPlaylistNameFromPage() {
    // Debug function to see what's available
    function debugAvailableElements() {
      console.log("🔍 Debugging available elements:");
      
      // Check all h1 elements
      const h1s = document.querySelectorAll('h1');
      h1s.forEach((h1, i) => {
        console.log(`H1 ${i}: "${h1.textContent.trim()}" - Classes: ${h1.className} - Parent: ${h1.parentElement?.tagName}`);
      });
      
      // Check the exact element from your HTML
      const exactElement = document.evaluate(
        '/html/body/ytd-app/div[1]/ytd-page-manager/ytd-browse[2]/yt-page-header-renderer/yt-page-header-view-model/div[2]/div[1]/div[1]/div/yt-dynamic-text-view-model/h1/span',
        document,
        null,
        XPathResult.FIRST_ORDERED_NODE_TYPE,
        null
      ).singleNodeValue;
      
      if (exactElement) {
        console.log(`XPath Element: "${exactElement.textContent.trim()}"`);
      }
      
      // Check specific YouTube elements
      const ytElements = document.querySelectorAll('yt-dynamic-text-view-model.ytPageHeaderViewModelTitle h1 span');
      ytElements.forEach((el, i) => {
        if (el.textContent.trim()) {
          console.log(`YT Dynamic Element ${i}: "${el.textContent.trim()}" - Classes: ${el.className}`);
        }
      });
    }
    
    // Run debug first
    debugAvailableElements();
    
    // First try the exact XPath from your HTML
    try {
      const xpathElement = document.evaluate(
        '/html/body/ytd-app/div[1]/ytd-page-manager/ytd-browse[2]/yt-page-header-renderer/yt-page-header-view-model/div[2]/div[1]/div[1]/div/yt-dynamic-text-view-model/h1/span',
        document,
        null,
        XPathResult.FIRST_ORDERED_NODE_TYPE,
        null
      ).singleNodeValue;
      
      if (xpathElement && xpathElement.textContent.trim() && xpathElement.textContent.trim() !== 'Playlist') {
        const name = xpathElement.textContent.trim();
        console.log(`🎯 Found playlist name with XPath: "${name}"`);
        return name;
      }
    } catch (error) {
      console.log("XPath failed:", error);
    }
    
    // Try multiple selectors to find the playlist name
    const selectors = [
      // Most specific based on your HTML structure
      'yt-dynamic-text-view-model.ytPageHeaderViewModelTitle h1 span[dir="auto"][role="text"]',
      'yt-dynamic-text-view-model.ytPageHeaderViewModelTitle h1 .ytAttributedStringHost',
      'yt-dynamic-text-view-model h1 span[role="text"]',
      '.ytPageHeaderViewModelTitle h1 span[dir="auto"]',
      '.dynamicTextViewModelH1 span[role="text"]',
      // Fallback selectors
      'yt-dynamic-text-view-model h1 .ytAttributedStringHost', 
      '.ytPageHeaderViewModelTitle .ytAttributedStringHost',
      'ytd-playlist-header-renderer h1.ytd-playlist-header-renderer',
      'ytd-playlist-header-renderer .playlist-title',
      'h1#title.ytd-playlist-header-renderer',
      '.playlist-header-content h1'
    ];
    
    for (const selector of selectors) {
      const element = document.querySelector(selector);
      if (element && element.textContent.trim() && element.textContent.trim() !== 'Playlist') {
        const name = element.textContent.trim();
        console.log(`🎯 Found playlist name with selector "${selector}": "${name}"`);
        return name;
      }
    }
    
    // Enhanced fallback - look for any span with role="text" that contains meaningful content
    const textSpans = document.querySelectorAll('span[role="text"]');
    for (const span of textSpans) {
      const text = span.textContent.trim();
      if (text && 
          text !== 'Playlist' && 
          !text.includes('YouTube') && 
          !text.includes('views') &&
          !text.includes('•') &&
          !text.includes('episodes') &&
          !text.includes('updated') &&
          !text.includes('videos') &&
          !text.includes('Private') &&
          !text.includes('Play all') &&
          text.length > 2 && 
          text.length < 50) { // Reasonable title length
        console.log(`🎯 Found playlist name in span[role="text"]: "${text}"`);
        return text;
      }
    }
    
    console.log("⚠️ Could not find playlist name, using document title as fallback");
    // Fallback to document title if no playlist name found
    return document.title.replace(/\s*-\s*YouTube\s*$/i, "").trim();
  }
  
  // Generate filename if not provided
  if (!fileName) {
    const playlistName = getPlaylistNameFromPage();
    fileName = `${playlistName.replace(/[<>:"/\\|?*]/g, "_").replace(/\s+/g, " ").trim()}.csv`;
    console.log(`📝 Using playlist name: "${playlistName}"`);
    console.log(`📄 Generated filename: "${fileName}"`);
  }
  
  const startTime = Date.now();
  const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

  async function autoScrollPlaylist() {
    console.log("📜 Starting auto-scroll to load all videos...");
    let lastCount = 0;
    let stableRounds = 0;
    const maxStableRounds = 5; // Reduced from 6

    for (let i = 0; i < maxScrollRounds && stableRounds < maxStableRounds; i++) {
      // Check timeout
      if (Date.now() - startTime > timeoutMs) {
        console.log("⏰ Timeout reached, stopping scroll");
        break;
      }

      window.scrollTo(0, document.documentElement.scrollHeight);
      await sleep(delayMs);

      const count = Math.max(
        document.querySelectorAll("ytd-playlist-video-renderer").length,
        document.querySelectorAll("yt-lockup-view-model").length
      );

      if (count === lastCount) {
        stableRounds++;
        console.log(`⏳ No new videos found (${stableRounds}/${maxStableRounds}) - Current count: ${count}`);
      } else {
        stableRounds = 0;
        lastCount = count;
        console.log(`📈 Progress: ${count} videos loaded (Round ${i + 1}/${maxScrollRounds})`);
      }
    }
    
    console.log(`✅ Scroll complete! Found ${lastCount} videos total`);
  }

  function cleanText(value) {
    return (value || "")
      .replace(/\s+/g, " ")
      .trim();
  }

  function getFullUrl(href) {
    if (!href) return "";
    return new URL(href, location.origin).href;
  }

  function getVideoId(url) {
    try {
      return new URL(url).searchParams.get("v") || "";
    } catch {
      return "";
    }
  }

  function getPlaylistId(url) {
    try {
      return new URL(url).searchParams.get("list") || "";
    } catch {
      return "";
    }
  }

  function getStartTime(url) {
    try {
      return new URL(url).searchParams.get("t") || "";
    } catch {
      return "";
    }
  }

  function escapeCSV(value) {
    const str = String(value ?? "");
    return `"${str.replace(/"/g, '""')}"`;
  }

  if (autoScroll) {
    await autoScrollPlaylist();
  }

  console.log("🔍 Extracting video data...");
  const rowSelectors = [
    "ytd-playlist-video-renderer",       // classic playlist page
    "yt-lockup-view-model",              // new YouTube UI (2025+)
    "ytd-playlist-panel-video-renderer"  // mini-player playlist
  ];

  let rows = [];
  let detectedSelector = null;

  for (const sel of rowSelectors) {
    const found = document.querySelectorAll(sel);
    if (found.length > 0) {
      rows = [...found];
      detectedSelector = sel;
      console.log(`✅ Using selector "${sel}" — found ${rows.length} items`);
      break;
    }
  }

  if (rows.length === 0) {
    console.error("❌ No playlist videos found! Make sure you're on a YouTube playlist page.");
    console.log("💡 Tried selectors:", rowSelectors.join(", "));
    return;
  }

  console.log(`📊 Processing ${rows.length} videos...`);

  const data = rows.map((row, index) => {
    if (index % 50 === 0) {
      console.log(`🔄 Processing video ${index + 1}/${rows.length}`);
    }

    try {
    const isLockup = row.tagName.toLowerCase() === 'yt-lockup-view-model';

    const playlistIndex = isLockup
      ? cleanText(row.querySelector("[class*='sequence-number'], .yt-thumbnail-view-model-wiz__sequenced-overlay-badge")?.textContent)
      : cleanText(row.querySelector("#index")?.textContent);

    const titleEl = isLockup
      ? (row.querySelector("h3 a, .yt-lockup-metadata-view-model-wiz__title a") || row.querySelector("a[href*='/watch']"))
      : row.querySelector("a#video-title");
    const title = cleanText(
      titleEl?.getAttribute("title") || titleEl?.getAttribute("aria-label") || titleEl?.textContent
    );

    const href = isLockup
      ? (titleEl?.getAttribute("href") || row.querySelector("a[href*='/watch']")?.getAttribute("href") || "")
      : (titleEl?.getAttribute("href") || row.querySelector("a#thumbnail")?.getAttribute("href") || "");

    const videoUrl = getFullUrl(href);

    const channelEl = isLockup
      ? (row.querySelector("yt-content-metadata-view-model a[href*='/@'], yt-content-metadata-view-model a[href*='/channel'], [class*='metadata'] a") ||
         row.querySelector("yt-content-metadata-view-model a"))
      : row.querySelector("ytd-channel-name #text a, ytd-channel-name #text");

    const channel = cleanText(channelEl?.textContent);
    const channelUrl = getFullUrl(channelEl?.getAttribute("href"));

    const durationEl = isLockup
      ? (row.querySelector("badge-shape .yt-spec-badge-shape__text") ||
         row.querySelector(".yt-thumbnail-overlay-time-status-view-model-wiz__text") ||
         row.querySelector("badge-shape"))
      : (row.querySelector("ytd-thumbnail-overlay-time-status-renderer .ytBadgeShapeText") ||
         row.querySelector("ytd-thumbnail-overlay-time-status-renderer #text"));

    const duration = cleanText(durationEl?.textContent);

    const durationLabel = isLockup
      ? (row.querySelector("badge-shape")?.getAttribute("aria-label") || duration)
      : (row.querySelector("badge-shape")?.getAttribute("aria-label") ||
         row.querySelector("ytd-thumbnail-overlay-time-status-renderer #text")?.getAttribute("aria-label") || "");

    let viewsText = "", publishedText = "";
    if (isLockup) {
      const metaSpans = [...row.querySelectorAll("yt-content-metadata-view-model span, [class*='metadata-row'] span")]
        .map(s => cleanText(s.textContent)).filter(t => t && t.length > 1);
      viewsText = metaSpans.find(t => /view|مشاهد/i.test(t)) || metaSpans[1] || "";
      publishedText = metaSpans.find(t => /ago|منذ|year|month|day|week|hour|ساعة|يوم|أسبوع|شهر|سنة/i.test(t)) || metaSpans[metaSpans.length - 1] || "";
    } else {
      const videoInfoSpans = [...row.querySelectorAll("#video-info span")].map(x => cleanText(x.textContent)).filter(Boolean);
      viewsText = videoInfoSpans[0] || "";
      publishedText = videoInfoSpans[videoInfoSpans.length - 1] || "";
    }

    const thumbnailUrl = row.querySelector("yt-image img")?.src || "";

    const h3AriaLabel = isLockup
      ? (titleEl?.getAttribute("aria-label") || row.querySelector("h3")?.getAttribute("aria-label") || "")
      : (row.querySelector("h3")?.getAttribute("aria-label") || "");

    const watched = isLockup
      ? cleanText(row.querySelector("[class*='playback-status'], [class*='watched']")?.textContent)
      : cleanText(row.querySelector("ytd-thumbnail-overlay-playback-status-renderer")?.textContent);

    const progress = isLockup
      ? (row.querySelector("[class*='resume-playback'] [class*='progress'], [class*='progress-bar']")?.style?.width || "")
      : (row.querySelector("ytd-thumbnail-overlay-resume-playback-renderer #progress")?.style?.width || "");

    return {
      playlist_index: playlistIndex,
      title,
      video_id: getVideoId(videoUrl),
      video_url: videoUrl,
      playlist_id: getPlaylistId(videoUrl),
      start_time: getStartTime(videoUrl),
      channel,
      channel_url: channelUrl,
      duration,
      duration_label: durationLabel,
      views_text: viewsText,
      published_text: publishedText,
      watched_status: watched,
      watch_progress: progress,
      thumbnail_url: thumbnailUrl,
      aria_label: h3AriaLabel
    };
    } catch (error) {
      console.warn(`⚠️ Error processing video ${index + 1}:`, error);
      return {
        playlist_index: index,
        title: "Error extracting data",
        video_id: "",
        video_url: "",
        playlist_id: "",
        start_time: "",
        channel: "",
        channel_url: "",
        duration: "",
        duration_label: "",
        views_text: "",
        published_text: "",
        watched_status: "",
        watch_progress: "",
        thumbnail_url: "",
        aria_label: ""
      };
    }
  }).filter(Boolean); // Remove any null/undefined entries

  console.log("📝 Generating CSV file...");
  
  const headers = Object.keys(data[0] || {
    playlist_index: "",
    title: "",
    video_id: "",
    video_url: "",
    playlist_id: "",
    start_time: "",
    channel: "",
    channel_url: "",
    duration: "",
    duration_label: "",
    views_text: "",
    published_text: "",
    watched_status: "",
    watch_progress: "",
    thumbnail_url: "",
    aria_label: ""
  });

  const csv = [
    headers.join(","),
    ...data.map(row => headers.map(header => escapeCSV(row[header])).join(","))
  ].join("\n");

  const blob = new Blob(["\uFEFF" + csv], {
    type: "text/csv;charset=utf-8;"
  });

  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  const endTime = Date.now();
  const duration = ((endTime - startTime) / 1000).toFixed(1);
  
  console.log(`✅ Successfully exported ${data.length} videos to "${fileName}"`);
  console.log(`⏱️ Total time: ${duration} seconds`);
  console.log(`📁 File downloaded: ${fileName}`);
  
  return data;
}

scrapeYouTubePlaylistToCSV();

// Alternative: Run with custom settings for faster execution
// scrapeYouTubePlaylistToCSV({
//   fileName: 'my-custom-name.csv', // Override auto-generated name
//   maxScrollRounds: 50,            // Limit scrolling rounds
//   delayMs: 500,                   // Faster scrolling
//   autoScroll: false               // Skip auto-scroll if playlist is already loaded
// });

// To stop the script if it's running, execute this in console:
// window.stop();