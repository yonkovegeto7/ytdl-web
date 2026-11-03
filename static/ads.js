/* ============================================================
   إعدادات إعلانات Adsterra
   ============================================================

   المفاتيح هي مفاتيح حسابك على Adsterra (Profitableratecpmnetwork /
   HighRevenueFormat). لا تغيّرها إلا إذا أنشأت وحدات جديدة.

   مهم جدًا: Adsterra لا تحتسب الظهور (impressions) إلا على نطاق (domain)
   تمت إضافته والتحقق منه داخل لوحة Adsterra (Websites ← Add website).
   النطاقات المجانية مثل trycloudflare.com أو hf.space لا يمكن التحقق منها،
   لذلك أضفنا "popunder بديل" يعمل بالضغط الفعلي للمستخدم حتى على هذه
   النطاقات، لأنه يفتح الرابط المباشر (Direct Link) الخاص بك.
   ============================================================ */

const ADS = {
  /* --- بانر 728x90 --- */
  banner: {
    key: "e5da48d26c01dcf8a98fb296fa9ec12d",
    width: 728,
    height: 90,
    src: "https://www.highrevenueformat.com/e5da48d26c01dcf8a98fb296fa9ec12d/invoke.js",
  },

  /* --- الإعلان الأصلي (native) — الحاوية موجودة في index.html --- */
  native: {
    src: "https://pl17278678.profitableratecpmnetwork.com/218b09d4a2a0ad568ab84cd2387c2ddd/invoke.js",
    containerId: "container-218b09d4a2a0ad568ab84cd2387c2ddd",
  },

  /* --- popunder الرسمي من Adsterra --- */
  // الوسم موجود كـ <script> حقيقي داخل templates/index.html (في الـ head)
  // لأن كود Adsterra يرتبط بأول ضغطة على الصفحة؛ لو حقناه بالجافاسكربت
  // بعد التحميل يفوت أول ضغطة ولا يفتح شيئًا.
  // يعمل فقط على نطاق موثّق في Adsterra، وبحد أقصى مرة كل ~24 ساعة للزائر.
  popunder: {
    src: "https://pl17279396.profitableratecpmnetwork.com/fa/cd/7d/facd7d024aaaf4b84e319af1e7e040db.js",
  },

  /* --- الرابط المباشر (Direct Link) --- */
  // يُفتح في تاب جديد فقط، ولا يلمس زر التحميل إطلاقًا.
  directLink: "https://www.profitableratecpmnetwork.com/v47gmsz1?key=38c1ea38b26c0fc8b713756e1e541717",

  /* --- popunder بديل (Fallback) --- */
  // يعمل على أي نطاق (hf.space / trycloudflare / localhost) لأن Direct Link
  // لا يحتاج موافقة نطاق. يُفتح مرة واحدة فقط كل POPUNDER_COOLDOWN_HOURS
  // ساعة لكل زائر، وبضغطة حقيقية من المستخدم (حتى لا يحجبه المتصفح).
  fallbackPopunder: {
    enabled: true,
    cooldownHours: 6,
    // لا تفتح الإعلان أبدًا عند الضغط على زر التحميل أو أي عنصر داخله
    blockSelector: [
      ".dl-btn",
      ".download-btn",
      "a[download]",
      "[data-no-pop]",
      "#results a",
      "#results button",
    ].join(","),
    storageKey: "ytdl_pp_last",
  },

  enabled: true,
};

/* ============================================================ */

(function () {
  if (!ADS.enabled) return;

  /* ---------- 1. البانر ---------- */
  function mountBanner() {
    const host = document.getElementById("ad-banner-inner");
    if (!host) return;

    const config = document.createElement("script");
    config.text =
      "atOptions = " +
      JSON.stringify({
        key: ADS.banner.key,
        format: "iframe",
        height: ADS.banner.height,
        width: ADS.banner.width,
        params: {},
      }) +
      ";";
    host.appendChild(config);

    const loader = document.createElement("script");
    loader.src = ADS.banner.src;
    loader.async = true;
    loader.onerror = hideBanner;
    host.appendChild(loader);

    fitBanner();
    window.addEventListener("resize", fitBanner);

    // لو الإعلان لم يظهر (مانع إعلانات أو نطاق غير موثّق) اخفِ المساحة الفارغة
    setTimeout(function () {
      if (!host.querySelector("iframe")) hideBanner();
    }, 6000);
  }

  function fitBanner() {
    const wrap = document.getElementById("ad-banner");
    const inner = document.getElementById("ad-banner-inner");
    if (!wrap || !inner) return;
    const available = wrap.clientWidth;
    if (!available) return;
    const scale = Math.min(1, available / ADS.banner.width);
    inner.style.transformOrigin = "top left";
    inner.style.transform = "scale(" + scale + ")";
    inner.style.marginLeft = Math.max(0, (available - ADS.banner.width * scale) / 2) + "px";
    wrap.style.height = ADS.banner.height * scale + "px";
  }

  function hideBanner() {
    const wrap = document.getElementById("ad-banner");
    if (wrap) wrap.style.display = "none";
  }

  /* ---------- 2. الإعلان الأصلي ---------- */
  function mountNative() {
    if (!document.getElementById(ADS.native.containerId)) return;
    const script = document.createElement("script");
    script.type = "text/javascript";
    script.async = true;
    script.setAttribute("data-cfasync", "false");
    script.src = ADS.native.src;
    document.body.appendChild(script);
  }

  /* ---------- 3. popunder الرسمي ---------- */
  // الوسم داخل index.html — لا نضيفه هنا حتى لا يتحمّل مرتين.

  /* ---------- 4. الرابط المباشر ---------- */
  function openDirectLink() {
    // تاب جديد + noopener: لا يغيّر صفحة الموقع ولا يعطّل التحميل
    const win = window.open(ADS.directLink, "_blank", "noopener,noreferrer");
    if (win) {
      try { win.opener = null; } catch (e) {}
    }
  }

  /* ---------- 5. popunder بديل (يعمل على أي نطاق) ---------- */
  function isFreeHost() {
    return /(^|\.)(trycloudflare\.com|hf\.space|localhost|127\.0\.0\.1)$/.test(
      location.hostname
    );
  }

  function popunderAllowedNow() {
    try {
      const last = parseInt(localStorage.getItem(ADS.fallbackPopunder.storageKey) || "0", 10);
      if (!last) return true;
      const ms = ADS.fallbackPopunder.cooldownHours * 60 * 60 * 1000;
      return Date.now() - last > ms;
    } catch (e) {
      return true;
    }
  }

  function markPopunderShown() {
    try {
      localStorage.setItem(ADS.fallbackPopunder.storageKey, String(Date.now()));
    } catch (e) {}
  }

  function openPopunderFallback() {
    // ضغطة حقيقية = المتصفح يسمح بفتح النافذة، ثم نرجّع التركيز للموقع
    // فتظهر النافذة "تحت" الصفحة (popunder) وليس أمامها (popup).
    const win = window.open(
      ADS.directLink,
      "sponsored_win",
      "noopener,noreferrer,width=1024,height=720,top=40,left=40"
    );
    if (!win) return false;
    try { win.opener = null; } catch (e) {}
    try {
      win.blur();
      window.focus();
    } catch (e) {}
    return true;
  }

  function armPopunderFallback() {
    const cfg = ADS.fallbackPopunder;
    if (!cfg.enabled || !popunderAllowedNow()) return;

    let armed = true;
    const onFirstClick = function (event) {
      if (!armed) return;
      if (event.button !== 0 && event.pointerType === "mouse") return;
      if (event.target && event.target.closest && event.target.closest(cfg.blockSelector)) {
        return; // ضغطة تحميل: لا نستهلك الإعلان ولا نفتح شيئًا
      }
      const ok = openPopunderFallback();
      if (ok) {
        markPopunderShown();
        armed = false;
        document.removeEventListener("pointerdown", onFirstClick, true);
        document.removeEventListener("click", onFirstClick, true);
      }
    };

    document.addEventListener("pointerdown", onFirstClick, true);
    document.addEventListener("click", onFirstClick, true);
  }

  window.ADS = ADS;
  window.openDirectLink = openDirectLink;
  window.ADS.debug = function () {
    const host = location.hostname;
    return {
      domain: host,
      adsterraWillCount: !isFreeHost(),
      banner: !!document.querySelector("#ad-banner-inner iframe"),
      nativeItems: (document.getElementById(ADS.native.containerId) || {}).childElementCount || 0,
      popunderTag: !!document.querySelector('script[src*="pl17279396"]'),
      fallbackArmed: ADS.fallbackPopunder.enabled && popunderAllowedNow(),
      directLink: ADS.directLink,
    };
  };

  document.addEventListener("DOMContentLoaded", function () {
    mountBanner();
    mountNative();

    const link = document.getElementById("sponsored-link");
    if (link) {
      link.href = ADS.directLink;
      link.addEventListener("click", function (event) {
        event.preventDefault();
        openDirectLink();
      });
    }

    // على النطاقات غير الموثّقة فقط: فعّل الـ popunder البديل.
    // على نطاق موثّق، كود Adsterra الرسمي هو الذي يتولّى المهمة.
    if (isFreeHost()) {
      armPopunderFallback();
    }
  });
})();
