// ==UserScript==
// @name         YouTube Playlist Extractor
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Extract YouTube playlist data to CSV with floating button, menu command, and GM_download
// @author       Ibn-mohey
// @match        https://www.youtube.com/*
// @grant        GM_registerMenuCommand
// @grant        GM_download
// @grant        GM_addStyle
// ==/UserScript==

(function () {
  "use strict";

  // ─── Option 2: Menu Command ───────────────────────────────────────────
  GM_registerMenuCommand("📥 Export Playlist to CSV", () => {
    scrapeYouTubePlaylistToCSV();
  });

  GM_registerMenuCommand("📥 Export Playlist (No Scroll)", () => {
    scrapeYouTubePlaylistToCSV({ autoScroll: false });
  });

  // ─── Option 3: Floating Button ────────────────────────────────────────
  GM_addStyle(`
    #yt-playlist-export-btn {
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 99999;
      background: #cc0000;
      color: #fff;
      border: none;
      border-radius: 28px;
      padding: 12px 20px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
      transition: all 0.2s ease;
      display: none;
      font-family: 'YouTube Sans', 'Roboto', Arial, sans-serif;
    }
    #yt-playlist-export-btn:hover {
      background: #aa0000;
      transform: scale(1.05);
      box-shadow: 0 6px 16px rgba(0,0,0,0.4);
    }
    #yt-playlist-export-btn:active {
      transform: scale(0.97);
    }
    #yt-playlist-export-btn.running {
      background: #555;
      cursor: wait;
    }
  `);

  function createFloatingButton() {
    if (document.getElementById("yt-playlist-export-btn")) return;

    const btn = document.createElement("button");
    btn.id = "yt-playlist-export-btn";
    btn.textContent = "📥 Export Playlist CSV";
    btn.addEventListener("click", async () => {
      if (btn.classList.contains("running")) return;
      btn.classList.add("running");
      btn.textContent = "⏳ Extracting...";
      try {
        await scrapeYouTubePlaylistToCSV();
        btn.textContent = "✅ Done!";
        setTimeout(() => {
          btn.textContent = "📥 Export Playlist CSV";
          btn.classList.remove("running");
        }, 3000);
      } catch (err) {
        console.error("Export failed:", err);
        btn.textContent = "❌ Failed";
        setTimeout(() => {
          btn.textContent = "📥 Export Playlist CSV";
          btn.classList.remove("running");
        }, 3000);
      }
    });

    document.body.appendChild(btn);
  }

  function toggleButtonVisibility() {
    const btn = document.getElementById("yt-playlist-export-btn");
    if (!btn) return;
    const isPlaylist = location.pathname === "/playlist";
    btn.style.display = isPlaylist ? "block" : "none";
  }

  // Watch for page navigation (YouTube is SPA)
  function watchNavigation() {
    createFloatingButton();
    toggleButtonVisibility();

    const observer = new MutationObserver(() => {
      createFloatingButton();
      toggleButtonVisibility();
    });

    observer.observe(document.body, { childList: true, subtree: true });

    // Also listen for YouTube SPA navigation
    window.addEventListener("yt-navigate-finish", () => {
      createFloatingButton();
      toggleButtonVisibility();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", watchNavigation);
  } else {
    watchNavigation();
  }

  // ─── Core Extraction Logic ────────────────────────────────────────────
  async function scrapeYouTubePlaylistToCSV({
    fileName = null,
    autoScroll = true,
    maxScrollRounds = 100,
    delayMs = 1000,
    timeoutMs = 300000,
  } = {}) {
    console.log("🚀 Starting YouTube playlist extraction...");

    if (location.pathname !== "/playlist") {
      alert("⚠️ Please navigate to a YouTube playlist page first.");
      return;
    }

    const startTime = Date.now();
    const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

    // ── Extract playlist name ──
    function getPlaylistNameFromPage() {
      const selectors = [
        'yt-dynamic-text-view-model.ytPageHeaderViewModelTitle h1 span[dir="auto"][role="text"]',
        'yt-dynamic-text-view-model.ytPageHeaderViewModelTitle h1 .ytAttributedStringHost',
        'yt-dynamic-text-view-model h1 span[role="text"]',
        '.ytPageHeaderViewModelTitle h1 span[dir="auto"]',
        "ytd-playlist-header-renderer h1.ytd-playlist-header-renderer",
        'h1#title.ytd-playlist-header-renderer',
      ];

      for (const selector of selectors) {
        const el = document.querySelector(selector);
        if (el && el.textContent.trim() && el.textContent.trim() !== "Playlist") {
          return el.textContent.trim();
        }
      }

      // Fallback: span[role="text"] heuristic
      for (const span of document.querySelectorAll('span[role="text"]')) {
        const text = span.textContent.trim();
        if (
          text &&
          text !== "Playlist" &&
          !text.includes("YouTube") &&
          !text.includes("views") &&
          !text.includes("•") &&
          text.length > 2 &&
          text.length < 50
        ) {
          return text;
        }
      }

      return document.title.replace(/\s*-\s*YouTube\s*$/i, "").trim();
    }

    if (!fileName) {
      const playlistName = getPlaylistNameFromPage();
      fileName = `${playlistName.replace(/[<>:"/\\|?*]/g, "_").replace(/\s+/g, " ").trim()}.csv`;
      console.log(`📄 Filename: "${fileName}"`);
    }

    // ── Auto-scroll ──
    if (autoScroll) {
      console.log("📜 Auto-scrolling to load all videos...");
      let lastCount = 0;
      let stableRounds = 0;
      const maxStableRounds = 5;

      for (let i = 0; i < maxScrollRounds && stableRounds < maxStableRounds; i++) {
        if (Date.now() - startTime > timeoutMs) {
          console.log("⏰ Timeout reached");
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
        } else {
          stableRounds = 0;
          lastCount = count;
          console.log(`📈 ${count} videos loaded (round ${i + 1})`);
        }
      }
    }

    // ── Helpers ──
    const cleanText = (v) => (v || "").replace(/\s+/g, " ").trim();
    const getFullUrl = (href) => (href ? new URL(href, location.origin).href : "");
    const getParam = (url, key) => {
      try { return new URL(url).searchParams.get(key) || ""; } catch { return ""; }
    };
    const escapeCSV = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;

    // ── Extract data ──
    console.log("🔍 Extracting video data...");

    const rowSelectors = [
      "ytd-playlist-video-renderer",
      "yt-lockup-view-model",
      "ytd-playlist-panel-video-renderer",
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
      alert("❌ No playlist videos found on this page.");
      return;
    }

    const data = rows.map((row, idx) => {
      try {
        const isLockup = row.tagName.toLowerCase() === "yt-lockup-view-model";

        const playlistIndex = isLockup
          ? cleanText(row.querySelector("[class*='sequence-number'], .yt-thumbnail-view-model-wiz__sequenced-overlay-badge")?.textContent)
          : cleanText(row.querySelector("#index")?.textContent);

        const titleEl = isLockup
          ? (row.querySelector("h3 a, .yt-lockup-metadata-view-model-wiz__title a") || row.querySelector("a[href*='/watch']"))
          : row.querySelector("a#video-title");
        const title = cleanText(titleEl?.getAttribute("title") || titleEl?.getAttribute("aria-label") || titleEl?.textContent);

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
            .map((s) => cleanText(s.textContent)).filter((t) => t && t.length > 1);
          viewsText = metaSpans.find((t) => /view|مشاهد/i.test(t)) || metaSpans[1] || "";
          publishedText = metaSpans.find((t) => /ago|منذ|year|month|day|week|hour|ساعة|يوم|أسبوع|شهر|سنة/i.test(t)) || metaSpans[metaSpans.length - 1] || "";
        } else {
          const videoInfoSpans = [...row.querySelectorAll("#video-info span")]
            .map((x) => cleanText(x.textContent)).filter(Boolean);
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
          video_id: getParam(videoUrl, "v"),
          video_url: videoUrl,
          playlist_id: getParam(videoUrl, "list"),
          start_time: getParam(videoUrl, "t"),
          channel,
          channel_url: channelUrl,
          duration,
          duration_label: durationLabel,
          views_text: viewsText,
          published_text: publishedText,
          watched_status: watched,
          watch_progress: progress,
          thumbnail_url: thumbnailUrl,
          aria_label: h3AriaLabel,
        };
      } catch (err) {
        console.warn(`⚠️ Error on video ${idx + 1}:`, err);
        return null;
      }
    }).filter(Boolean);

    // ── Build CSV ──
    const headers = Object.keys(data[0]);
    const csv =
      [headers.join(","), ...data.map((r) => headers.map((h) => escapeCSV(r[h])).join(","))].join("\n");

    // ── Option 4: Download using GM_download with Blob URL fallback ──
    const blobUrl = URL.createObjectURL(
      new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" })
    );

    try {
      GM_download({
        url: blobUrl,
        name: fileName,       // e.g. "My Playlist.csv"
        onerror: (err) => {}, // if it fails → fallback
        onload: () => {},     // if it succeeds → cleanup
      });
    } catch {
      fallbackDownload(blobUrl, fileName);
    }

    function fallbackDownload(url, name) {
      const a = document.createElement("a");
      a.href = url;
      a.download = name;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 5000);
    }

    const duration = ((Date.now() - startTime) / 1000).toFixed(1);
    console.log(`✅ Exported ${data.length} videos to "${fileName}" in ${duration}s`);
    return data;
  }
})();
