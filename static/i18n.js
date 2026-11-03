/* ============================================================
   Translations — add a new language by adding one more object.
   Keys missing in a language fall back to English.
   ============================================================ */

const I18N = {
  en: {
    page_title: "YouTube Downloader — Download Videos Fast",
    app_title: "YouTube Downloader",
    app_subtitle: "Download any YouTube video as MP4 — fast and free",

    warn_ffmpeg: "FFmpeg is missing on this server, downloads will not work.",
    warn_js: "No JavaScript runtime (Deno/Node) found. Some YouTube formats may not be available.",

    step_url: "Paste a YouTube link",
    url_placeholder: "https://www.youtube.com/watch?v=...",
    filename_label: "File name (optional)",
    filename_placeholder: "Leave empty to use the video title",
    fetch_btn: "Get formats",
    fetching: "Fetching…",
    fetch_hint: "Works with videos, Shorts and YouTube Music.",

    step_video: "Video quality",
    step_audio: "Audio quality",
    step_trim: "Trim (optional)",
    start_label: "Start time (HH:MM:SS)",
    end_label: "End time (HH:MM:SS)",

    download_full: "Download full video",
    download_trim: "Cut & download",
    download_chapters: "Chapters",

    chapters_title: "Pick chapters",
    download_selected: "Download selected (zip)",
    back: "Back",

    progress_title: "Progress",
    show_console: "Show console",
    hide_console: "Hide console",
    stop: "Stop",

    footer_note: "Not affiliated with YouTube. Download only content you have the right to use.",
    ttl_note: "Files are deleted automatically after {min} minutes.",
    keep_note: "Finished files stay on the server until disk space runs low — slow connections have plenty of time.",
    expired_msg: "This file was removed to free space. Please run the download again.",
    ad_label: "Advertisement",
    sponsored: "Sponsored offer",

    /* ---- dynamic ---- */
    duration: "Duration",
    unknown: "Unknown",
    no_audio: "No audio track found",
    no_video: "No MP4 (H.264) video found for this link",
    no_chapters: "This video has no chapters.",
    need_url: "Please paste a YouTube link first.",
    need_formats: "Pick a video and an audio quality first.",
    need_times: "Set a start and an end time.",
    bad_times: "End time must be after the start time.",
    network_error: "Network error. Check your connection and try again.",
    server_error: "Something went wrong. Please try again.",

    status_queued: "Queued…",
    status_downloading_video: "Downloading video…",
    status_downloading_audio: "Downloading audio…",
    status_merging: "Merging…",
    status_cutting: "Cutting chapters…",
    status_complete: "Done!",
    status_error: "Failed",
    status_stopped: "Stopped",

    ready_msg: "Your file is ready.",
    download_file: "Download file",
    new_download: "New download",
    try_again: "Try again",
    stopped_msg: "Stopped.",
  },

  ar: {
    page_title: "تحميل فيديوهات يوتيوب — سريع ومجاني",
    app_title: "تحميل فيديوهات يوتيوب",
    app_subtitle: "حمّل أي فيديو من يوتيوب بصيغة MP4 — بسرعة ومجانًا",

    warn_ffmpeg: "برنامج FFmpeg غير مثبّت على السيرفر، التحميل مش هيشتغل.",
    warn_js: "مفيش JavaScript runtime (Deno/Node) على السيرفر، بعض الصيغ ممكن متكونش متاحة.",

    step_url: "الصق رابط يوتيوب",
    url_placeholder: "https://www.youtube.com/watch?v=...",
    filename_label: "اسم الملف (اختياري)",
    filename_placeholder: "سيبه فاضي لاستخدام عنوان الفيديو",
    fetch_btn: "جيب الصيغ",
    fetching: "بيجيب…",
    fetch_hint: "بيشتغل مع الفيديوهات والـ Shorts وYouTube Music.",

    step_video: "جودة الفيديو",
    step_audio: "جودة الصوت",
    step_trim: "قص المقطع (اختياري)",
    start_label: "وقت البداية (HH:MM:SS)",
    end_label: "وقت النهاية (HH:MM:SS)",

    download_full: "تحميل الفيديو كامل",
    download_trim: "قص وتحميل",
    download_chapters: "الفصول",

    chapters_title: "اختار الفصول",
    download_selected: "تحميل المختار (ZIP)",
    back: "رجوع",

    progress_title: "التقدم",
    show_console: "إظهار السجل",
    hide_console: "إخفاء السجل",
    stop: "إيقاف",

    footer_note: "الموقع غير تابع ليوتيوب. نزّل بس المحتوى اللي من حقك استخدامه.",
    ttl_note: "الملفات بتتمسح تلقائيًا بعد {min} دقيقة.",
    keep_note: "الملفات بتفضل على السيرفر لحد ما المساحة تقرب تخلص — النت الضعيف عنده وقت كافي.",
    expired_msg: "الملف ده اتمسح عشان نفضّي مساحة. اعمل التحميل تاني.",
    ad_label: "إعلان",
    sponsored: "عرض ممول",

    /* ---- dynamic ---- */
    duration: "المدة",
    unknown: "غير معروف",
    no_audio: "مفيش مسار صوت",
    no_video: "مفيش فيديو MP4 (H.264) متاح للرابط ده",
    no_chapters: "الفيديو ده ملهوش فصول.",
    need_url: "الصق رابط يوتيوب الأول.",
    need_formats: "اختار جودة فيديو وجودة صوت الأول.",
    need_times: "حدد وقت البداية ووقت النهاية.",
    bad_times: "وقت النهاية لازم يكون بعد البداية.",
    network_error: "مشكلة في الاتصال. راجع النت وجرب تاني.",
    server_error: "حصل خطأ. جرب تاني.",

    status_queued: "في الانتظار…",
    status_downloading_video: "بيحمّل الفيديو…",
    status_downloading_audio: "بيحمّل الصوت…",
    status_merging: "بيدمج…",
    status_cutting: "بيقص الفصول…",
    status_complete: "تم!",
    status_error: "فشل",
    status_stopped: "اتوقف",

    ready_msg: "ملفك جاهز.",
    download_file: "تحميل الملف",
    new_download: "تحميل فيديو تاني",
    try_again: "جرب تاني",
    stopped_msg: "اتوقف.",
  },
};

const LANG_KEY = "ytd_lang";
let currentLang = "en";

function detectLang() {
  try {
    const saved = localStorage.getItem(LANG_KEY);
    if (saved && I18N[saved]) return saved;
  } catch (e) {}
  const nav = (navigator.language || "en").toLowerCase();
  return nav.startsWith("ar") ? "ar" : "en";
}

function t(key, vars) {
  const dict = I18N[currentLang] || I18N.en;
  let text = dict[key] ?? I18N.en[key] ?? key;
  if (vars) {
    Object.keys(vars).forEach(function (k) {
      text = text.replace(new RegExp("\\{" + k + "\\}", "g"), vars[k]);
    });
  }
  return text;
}

function applyLang(lang) {
  if (!I18N[lang]) lang = "en";
  currentLang = lang;
  const html = document.documentElement;
  html.lang = lang;
  html.dir = lang === "ar" ? "rtl" : "ltr";

  document.querySelectorAll("[data-i18n]").forEach(function (el) {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-ph]").forEach(function (el) {
    el.placeholder = t(el.dataset.i18nPh);
  });
  document.querySelectorAll(".lang-switch button").forEach(function (btn) {
    btn.classList.toggle("active", btn.dataset.lang === lang);
  });
  if (document.title) document.title = t("page_title");

  try {
    localStorage.setItem(LANG_KEY, lang);
  } catch (e) {}

  document.dispatchEvent(new CustomEvent("langchange"));
}

document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".lang-switch button").forEach(function (btn) {
    btn.addEventListener("click", function () {
      applyLang(btn.dataset.lang);
    });
  });
  applyLang(detectLang());
});
