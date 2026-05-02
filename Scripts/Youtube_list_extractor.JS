async function scrapeYouTubePlaylistToCSV({
  fileName = `${document.title
    .replace(/\s*-\s*YouTube\s*$/i, "")
    .replace(/[<>:"/\\|?*]/g, "_")
    .replace(/\s+/g, " ")
    .trim()}.csv`,
  autoScroll = true,
  maxScrollRounds = 200,
  delayMs = 700
} = {}) {
  const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

  async function autoScrollPlaylist() {
    let lastCount = 0;
    let stableRounds = 0;

    for (let i = 0; i < maxScrollRounds && stableRounds < 6; i++) {
      window.scrollTo(0, document.documentElement.scrollHeight);
      await sleep(delayMs);

      const count = document.querySelectorAll("ytd-playlist-video-renderer").length;

      if (count === lastCount) {
        stableRounds++;
      } else {
        stableRounds = 0;
        lastCount = count;
        console.log(`Loaded videos: ${count}`);
      }
    }
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

  const rows = [...document.querySelectorAll("ytd-playlist-video-renderer")];

  const data = rows.map(row => {
    const index = cleanText(row.querySelector("#index")?.textContent);

    const titleEl = row.querySelector("a#video-title");
    const title = cleanText(
      titleEl?.getAttribute("title") || titleEl?.textContent
    );

    const href =
      titleEl?.getAttribute("href") ||
      row.querySelector("a#thumbnail")?.getAttribute("href") ||
      "";

    const videoUrl = getFullUrl(href);

    const channelEl = row.querySelector(
      "ytd-channel-name #text a, ytd-channel-name #text"
    );

    const channel = cleanText(channelEl?.textContent);
    const channelUrl = getFullUrl(channelEl?.getAttribute("href"));

    const durationEl =
      row.querySelector("ytd-thumbnail-overlay-time-status-renderer .ytBadgeShapeText") ||
      row.querySelector("ytd-thumbnail-overlay-time-status-renderer #text");

    const duration = cleanText(durationEl?.textContent);

    const durationLabel =
      row.querySelector("badge-shape")?.getAttribute("aria-label") ||
      row.querySelector("ytd-thumbnail-overlay-time-status-renderer #text")?.getAttribute("aria-label") ||
      "";

    const videoInfoSpans = [
      ...row.querySelectorAll("#video-info span")
    ].map(x => cleanText(x.textContent)).filter(Boolean);

    const viewsText = videoInfoSpans[0] || "";
    const publishedText = videoInfoSpans[videoInfoSpans.length - 1] || "";

    const thumbnailUrl = row.querySelector("yt-image img")?.src || "";

    const h3AriaLabel = row.querySelector("h3")?.getAttribute("aria-label") || "";

    const watched = cleanText(
      row.querySelector("ytd-thumbnail-overlay-playback-status-renderer")?.textContent
    );

    const progress =
      row.querySelector("ytd-thumbnail-overlay-resume-playback-renderer #progress")
        ?.style?.width || "";

    return {
      playlist_index: index,
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
  });

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

`
}
`

scrapeYouTubePlaylistToCSV();