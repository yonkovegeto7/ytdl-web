/* ============================================================
   YouTube Downloader — front-end logic
   ============================================================ */

const state = {
  url: "",
  videoFormats: [],
  audioFormats: [],
  chapters: [],
  selectedVideo: null,
  selectedAudio: null,
  selectedChapters: new Set(),
  taskId: null,
  polling: null,
  mode: "full",
};

const CFG = window.APP_CONFIG || { ttlMinutes: 30 };

const $ = (id) => document.getElementById(id);

/* ---------- helpers ---------- */

function humanSize(bytes) {
  if (!bytes) return "";
  const units = ["B", "KB", "MB", "GB"];
  let n = bytes;
  let i = 0;
  while (n >= 1024 && i < units.length - 1) {
    n /= 1024;
    i++;
  }
  return n.toFixed(n >= 10 || i === 0 ? 0 : 1) + " " + units[i];
}

function showError(message) {
  const box = $("error-box");
  box.textContent = message;
  box.classList.remove("hidden");
  box.scrollIntoView({ behavior: "smooth", block: "center" });
}

function clearError() {
  $("error-box").classList.add("hidden");
  $("error-box").textContent = "";
}

function showCard(id) {
  $(id).classList.remove("hidden");
}

function hideCard(id) {
  $(id).classList.add("hidden");
}

async function api(path, body) {
  const options = { method: body === undefined ? "GET" : "POST" };
  if (body !== undefined) {
    options.headers = { "Content-Type": "application/json" };
    options.body = JSON.stringify(body);
  }
  let response;
  try {
    response = await fetch(path, options);
  } catch (e) {
    throw new Error(t("network_error"));
  }
  let data = {};
  try {
    data = await response.json();
  } catch (e) {}
  if (!response.ok) {
    throw new Error(data.error || t("server_error"));
  }
  return data;
}

function statusLabel(status) {
  const key = "status_" + status;
  const text = t(key);
  return text === key ? status : text;
}

function ttlNoteText() {
  if (CFG.ttlMinutes > 0) return t("ttl_note", { min: CFG.ttlMinutes });
  return t("keep_note");
}

/* ---------- step 1: fetch formats ---------- */

async function fetchFormats() {
  const url = $("url-input").value.trim();
  if (!url) {
    showError(t("need_url"));
    return;
  }

  clearError();
  state.url = url;
  hideCard("formats-card");
  hideCard("chapters-card");
  hideCard("progress-card");

  const btn = $("fetch-btn");
  btn.disabled = true;
  btn.textContent = t("fetching");

  try {
    const data = await api("/api/fetch", { url });

    state.videoFormats = data.video_formats || [];
    state.audioFormats = data.audio_formats || [];
    state.chapters = data.chapters || [];

    if (!state.videoFormats.length) {
      showError(t("no_video"));
      return;
    }
    if (!state.audioFormats.length) {
      showError(t("no_audio"));
      return;
    }

    $("video-title").textContent = data.title || t("unknown");

    const sub = [];
    if (data.uploader) sub.push(data.uploader);
    if (data.duration) sub.push(t("duration") + ": " + formatDuration(data.duration));
    $("video-sub").textContent = sub.join("  •  ");

    const thumb = $("thumb");
    if (data.thumbnail) {
      thumb.src = data.thumbnail;
      thumb.classList.remove("hidden");
    } else {
      thumb.classList.add("hidden");
    }

    $("duration-line").textContent = data.duration
      ? t("duration") + ": " + formatDuration(data.duration)
      : "";

    // prefill the trim fields with the whole video
    if (data.duration) {
      $("start-time").value = "00:00:00";
      $("end-time").value = formatDuration(data.duration);
    }

    $("chapters-btn").hidden = state.chapters.length === 0;

    renderVideoFormats();
    renderAudioFormats();
    showCard("formats-card");
    $("formats-card").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (e) {
    showError(e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = t("fetch_btn");
  }
}

function formatDuration(totalSeconds) {
  const s = Math.max(0, Math.round(totalSeconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  return [h, m, sec].map((v) => String(v).padStart(2, "0")).join(":");
}

/* ---------- step 2 & 3: render formats ---------- */

function renderVideoFormats() {
  const list = $("video-list");
  list.innerHTML = "";
  state.selectedVideo = null;

  state.videoFormats.forEach((f, index) => {
    const row = document.createElement("div");
    row.className = "format-item";
    row.setAttribute("role", "radio");

    const name = document.createElement("span");
    name.className = "name";
    name.textContent =
      (f.format_note || f.height + "p" || "?") +
      (f.fps ? " · " + f.fps + "fps" : "") +
      " · " + f.ext;

    const size = document.createElement("span");
    size.className = "size";
    size.textContent = humanSize(f.filesize);

    row.append(name, size);
    row.addEventListener("click", () => selectVideo(index));
    list.appendChild(row);
  });

  if (state.videoFormats.length) selectVideo(0);
}

function selectVideo(index) {
  state.selectedVideo = state.videoFormats[index];
  document.querySelectorAll("#video-list .format-item").forEach((el, i) => {
    el.classList.toggle("selected", i === index);
    el.setAttribute("aria-checked", i === index ? "true" : "false");
  });
}

function renderAudioFormats() {
  const list = $("audio-list");
  list.innerHTML = "";
  state.selectedAudio = null;

  state.audioFormats.forEach((f, index) => {
    const row = document.createElement("div");
    row.className = "format-item";
    row.setAttribute("role", "radio");

    const badge = document.createElement("span");
    badge.className = "badge " + (f.quality === "HIGH" ? "badge-high" : "badge-low");
    badge.textContent = f.quality;

    const name = document.createElement("span");
    name.className = "name";
    name.textContent =
      (f.abr ? Math.round(f.abr) + " kbps" : f.format_note || "?") + " · " + f.ext;

    const size = document.createElement("span");
    size.className = "size";
    size.textContent = humanSize(f.filesize);

    row.append(badge, name, size);
    row.addEventListener("click", () => selectAudio(index));
    list.appendChild(row);
  });

  if (state.audioFormats.length) selectAudio(0);
}

function selectAudio(index) {
  state.selectedAudio = state.audioFormats[index];
  document.querySelectorAll("#audio-list .format-item").forEach((el, i) => {
    el.classList.toggle("selected", i === index);
    el.setAttribute("aria-checked", i === index ? "true" : "false");
  });
}

/* ---------- step 4: start download ---------- */

async function startDownload(mode) {
  if (!state.selectedVideo || !state.selectedAudio) {
    showError(t("need_formats"));
    return;
  }

  const payload = {
    url: state.url,
    video_format_id: state.selectedVideo.format_id,
    audio_format_id: state.selectedAudio.format_id,
    mode: mode,
    filename: $("filename-input").value.trim() || undefined,
  };

  if (mode === "trim") {
    const start = $("start-time").value.trim();
    const end = $("end-time").value.trim();
    if (!start || !end) {
      showError(t("need_times"));
      return;
    }
    payload.start_time = start;
    payload.end_time = end;
  }

  clearError();
  openProgress(mode);
  $("stop-btn").disabled = false;

  try {
    const data = await api("/api/download", payload);
    state.taskId = data.task_id;
    startPolling();
  } catch (e) {
    stopPolling();
    $("status-text").textContent = t("status_error");
    $("download-actions").innerHTML = "";
    showError(e.message);
  }
}

function openProgress(mode) {
  state.mode = mode;
  hideCard("formats-card");
  hideCard("chapters-card");
  showCard("progress-card");
  $("progress-bar").style.width = "0%";
  $("progress-text").textContent = "0%";
  $("status-text").textContent = t("status_queued");
  $("dl-info").textContent = "";
  $("log-box").textContent = "";
  $("download-actions").innerHTML = "";
  $("progress-card").scrollIntoView({ behavior: "smooth", block: "start" });
  [$("full-btn"), $("trim-btn"), $("chapters-dl-btn")].forEach((b) => (b.disabled = true));
}

/* ---------- chapters ---------- */

function renderChapters() {
  const list = $("chapters-list");
  list.innerHTML = "";
  state.selectedChapters = new Set();

  state.chapters.forEach((chapter, index) => {
    const row = document.createElement("label");
    row.className = "format-item";

    const box = document.createElement("input");
    box.type = "checkbox";
    box.className = "checkbox";
    box.value = String(index);
    box.checked = true;
    box.addEventListener("change", () => {
      if (box.checked) state.selectedChapters.add(index);
      else state.selectedChapters.delete(index);
      updateSelectedChaptersButton();
    });
    state.selectedChapters.add(index);

    const name = document.createElement("span");
    name.className = "name";
    name.textContent = index + 1 + ". " + chapter.title;

    const time = document.createElement("span");
    time.className = "size";
    time.textContent = chapter.start_display + " – " + chapter.end_display;

    row.append(box, name, time);
    list.appendChild(row);
  });

  updateSelectedChaptersButton();
}

function updateSelectedChaptersButton() {
  const count = state.selectedChapters.size;
  const btn = $("chapters-dl-btn");
  btn.textContent = t("download_selected") + " (" + count + ")";
  btn.disabled = count === 0;
}

function showChapters() {
  if (!state.chapters.length) {
    showError(t("no_chapters"));
    return;
  }
  if (!state.selectedVideo) {
    showError(t("need_formats"));
    return;
  }
  hideCard("formats-card");
  showCard("chapters-card");
  renderChapters();
  $("chapters-card").scrollIntoView({ behavior: "smooth", block: "start" });
}

function showFormats() {
  hideCard("chapters-card");
  showCard("formats-card");
}

async function startChapters() {
  if (!state.selectedVideo) {
    showError(t("need_formats"));
    return;
  }
  const indexes = Array.from(state.selectedChapters).sort((a, b) => a - b);
  if (!indexes.length) {
    showError(t("no_chapters"));
    return;
  }
  const chosen = indexes.map((i) => state.chapters[i]);
  const first = chosen[0].start_display.replace(/:/g, "");

  clearError();
  openProgress("chapters");
  $("stop-btn").disabled = false;

  try {
    const data = await api("/api/chapters", {
      url: state.url,
      video_format_id: state.selectedVideo.format_id,
      chapters: chosen,
      filename: ($("filename-input").value.trim() || "chapters") + "_" + first,
    });
    state.taskId = data.task_id;
    startPolling();
  } catch (e) {
    stopPolling();
    $("status-text").textContent = t("status_error");
    showError(e.message);
  }
}

/* ---------- polling ---------- */

function startPolling() {
  stopPolling();
  state.polling = setInterval(pollStatus, 800);
}

function stopPolling() {
  if (state.polling) {
    clearInterval(state.polling);
    state.polling = null;
  }
}

async function pollStatus() {
  if (!state.taskId) return;
  let data;
  try {
    data = await api("/api/status/" + state.taskId);
  } catch (e) {
    return; // transient, keep polling
  }

  $("progress-bar").style.width = data.progress + "%";
  $("progress-text").textContent = data.progress + "%";
  $("status-text").textContent = statusLabel(data.status);
  state.lastStatus = data.status;

  const info = [];
  if (data.speed) info.push(data.speed);
  if (data.eta) info.push("ETA " + data.eta);
  if (data.size) info.push(data.size);
  $("dl-info").textContent = info.join(" · ");

  if (data.logs && data.logs.length) {
    const box = $("log-box");
    const atBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 40;
    box.textContent = data.logs.join("\n");
    if (atBottom) box.scrollTop = box.scrollHeight;
  }

  if (data.status === "complete") stopPolling();
  if (data.status === "error" || data.status === "stopped") stopPolling();

  if (data.status === "complete" && data.expired) {
    state.lastStatus = "error";
    state.lastError = t("expired_msg");
    finishError(state.lastError);
    return;
  }

  if (data.status === "complete") {
    state.lastStatus = "complete";
    state.lastFilename = data.output_filename;
    finishSuccess(data);
  } else if (data.status === "error") {
    state.lastStatus = "error";
    state.lastError = data.error || t("server_error");
    finishError(state.lastError);
  } else if (data.status === "stopped") {
    state.lastStatus = "stopped";
    finishStopped();
  }
}

function finishSuccess(data) {
  $("stop-btn").disabled = true;
  const actions = $("download-actions");
  actions.innerHTML = "";

  const note = document.createElement("p");
  note.className = "alert alert-ok";
  note.style.margin = "0";
  note.textContent = t("ready_msg") + " " + (data.output_filename || "");
  actions.appendChild(note);

  const link = document.createElement("a");
  link.className = "btn btn-primary";
  link.href = "/api/result/" + state.taskId;
  link.download = data.output_filename || "";
  link.textContent = t("download_file");
  actions.appendChild(link);

  const again = document.createElement("button");
  again.type = "button";
  again.className = "btn btn-ghost";
  again.textContent = t("new_download");
  again.addEventListener("click", resetAll);
  actions.appendChild(again);

  if (window.ADS && window.ADS.enabled && typeof window.openDirectLink === "function") {
    const sponsored = document.createElement("button");
    sponsored.type = "button";
    sponsored.className = "btn btn-ghost btn-sm";
    sponsored.textContent = "🎁 " + t("sponsored");
    sponsored.addEventListener("click", window.openDirectLink);
    actions.appendChild(sponsored);
  }

  restoreButtons();
  updateSelectedChaptersButton();
}

function finishError(message) {
  $("stop-btn").disabled = true;
  const actions = $("download-actions");
  actions.innerHTML = "";

  const note = document.createElement("p");
  note.className = "alert alert-error";
  note.style.margin = "0";
  note.textContent = message;
  actions.appendChild(note);

  const again = document.createElement("button");
  again.type = "button";
  again.className = "btn btn-ghost";
  again.textContent = t("try_again");
  again.addEventListener("click", resetAll);
  actions.appendChild(again);

  restoreButtons();
  updateSelectedChaptersButton();
}

function finishStopped() {
  $("stop-btn").disabled = true;
  $("download-actions").innerHTML = "";
  const note = document.createElement("p");
  note.className = "alert alert-warn";
  note.style.margin = "0";
  note.textContent = t("stopped_msg");
  $("download-actions").appendChild(note);
  restoreButtons();
  updateSelectedChaptersButton();
}

function restoreButtons() {
  [$("full-btn"), $("trim-btn")].forEach((b) => (b.disabled = false));
}

function resetAll() {
  stopPolling();
  hideCard("progress-card");
  hideCard("chapters-card");
  hideCard("formats-card");
  $("progress-bar").style.width = "0%";
  $("progress-text").textContent = "0%";
  $("status-text").textContent = "";
  $("dl-info").textContent = "";
  $("log-box").textContent = "";
  $("download-actions").innerHTML = "";
  $("video-list").innerHTML = "";
  $("audio-list").innerHTML = "";
  $("chapters-list").innerHTML = "";
  $("video-title").textContent = "";
  $("video-sub").textContent = "";
  state.taskId = null;
  state.videoFormats = [];
  state.audioFormats = [];
  state.chapters = [];
  state.selectedVideo = null;
  state.selectedAudio = null;
  restoreButtons();
  clearError();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function stopTask() {
  if (!state.taskId) return;
  $("stop-btn").disabled = true;
  try {
    await api("/api/stop/" + state.taskId, {});
  } catch (e) {}
}

/* ---------- console toggle ---------- */

function toggleConsole() {
  const box = $("log-box");
  box.classList.toggle("hidden");
  $("console-toggle").textContent = box.classList.contains("hidden")
    ? t("show_console")
    : t("hide_console");
}

/* ---------- wiring ---------- */

document.addEventListener("DOMContentLoaded", function () {
  $("fetch-btn").addEventListener("click", fetchFormats);
  $("full-btn").addEventListener("click", () => startDownload("full"));
  $("trim-btn").addEventListener("click", () => startDownload("trim"));
  $("chapters-btn").addEventListener("click", showChapters);
  $("chapters-dl-btn").addEventListener("click", startChapters);
  $("stop-btn").addEventListener("click", stopTask);
  $("console-toggle").addEventListener("click", toggleConsole);

  $("url-input").addEventListener("keydown", function (event) {
    if (event.key === "Enter") fetchFormats();
  });

  $("ttl-note").textContent = ttlNoteText();
});

document.addEventListener("langchange", function () {
  $("console-toggle").textContent = $("log-box").classList.contains("hidden")
    ? t("show_console")
    : t("hide_console");
  $("ttl-note").textContent = ttlNoteText();
  updateSelectedChaptersButton();

  if (state.lastStatus === "complete") {
    finishSuccess({ output_filename: state.lastFilename });
  } else if (state.lastStatus === "error") {
    finishError(state.lastError || t("server_error"));
  } else if (state.lastStatus === "stopped") {
    finishStopped();
  } else if (state.lastStatus) {
    $("status-text").textContent = statusLabel(state.lastStatus);
  }
});
