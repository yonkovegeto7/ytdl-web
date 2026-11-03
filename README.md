---
title: YouTube Downloader
emoji: ⬇️
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# YouTube Downloader — نسخة الويب (جاهزة للاستضافة المجانية)

> السطور اللي فوق (بين `---`) مطلوبة بس لو هترفع المشروع على **Hugging Face Spaces**، ومالهاش أي تأثير في أي مكان تاني.

نسخة معدّلة من تطبيقك المكتبي تشتغل على سيرفر، وكل واحد في العالم يقدر يفتح الرابط ويستخدمها من المتصفح — **من غير VPS مدفوع**.

```
webapp/
├─ app.py               ← السيرفر (Flask) بعد إصلاح كل حاجة خاصة بالويندوز
├─ templates/index.html ← الواجهة
├─ static/              ← CSS + JS + ملف الترجمات (عربي/إنجليزي)
├─ Dockerfile           ← الصورة اللي بتترفع على أي استضافة
├─ requirements.txt
├─ render.yaml          ← نشر بضغطة على Render
├─ docker-compose.yml   ← تجربة محلية بنفس الصورة
├─ run.ps1              ← تشغيل على جهازك + رابط عام مجاني
└─ .env.example         ← كل الإعدادات الاختيارية
```

---

## أول حاجة: إيه اللي كان مانع الموقع من الشغل أونلاين؟

| المشكلة في النسخة القديمة | الحل هنا |
|---|---|
| `app.run(host='127.0.0.1')` — يشتغل على جهازك بس | بيقرأ `PORT` ويسمع على `0.0.0.0` |
| `/api/run_terminal` بينفّذ أي أمر على الجهاز | **اتشال بالكامل** (كان ثغرة خطيرة: أي حد ينفّذ أوامر على سيرفرك) |
| اختيار فولدر ويندوز + `explorer` + `ctypes.windll` | اتشالوا، الملف بينزل في متصفح الزائر مباشرة |
| التحميل بيتحفظ في فولدر على جهازك | بيتحفظ على السيرفر لحد ما المساحة تقرب تخلص (مفيش حذف بالوقت) |
| ffmpeg/yt-dlp لازم يكونوا على جهاز المستخدم | متثبتين جوه الـ Docker image |
| مفيش حد أقصى للتحميلات | حد أقصى للتحميل المتزامن + Rate limit لكل IP |
| فصل الفصول كان بيرجّع آخر فصل بس | بيرجّع كل الفصول في ملف ZIP واحد |
| واجهة إنجليزي بس | عربي + إنجليزي مع RTL وتلقائي حسب لغة المتصفح |

---

## الطريقة الأسرع (5 دقايق): رابط عام من جهازك — مجانًا وبدون أي حساب

دي أفضل طريقة لو عايز أعلى جودة وسرعة، لأن يوتيوب بيحجب سيرفرات الاستضافة (Data centers) كتير، لكن **IP البيت بتاعك شغال عادي**.

```powershell
cd "F:\new anime\python to exe\test web\webapp"
.\run.ps1 -Public
```

السكربت بيعمل كل حاجة لوحده:
1. يعمل بيئة Python وينزّل المكتبات
2. يستخدم ffmpeg الموجود عندك في `New folder (2)\ffmpeg`
3. يشغّل السيرفر
4. ينزّل `cloudflared` ويعطيك لينك زي `https://xxxx-xxxx.trycloudflare.com`

ابعت اللينك لأي حد في العالم ويفتحه من أي موبايل أو لابتوب.

> **العيب الوحيد:** لازم الكمبيوتر والنت يفضلوا شغالين، والرابط بيتغير كل مرة تشغّل السكربت. **لو عايز الرابط ما يكونش ليه علاقة بجهازك خالص → استخدم Oracle أو Hugging Face تحت.**

---

## استضافة دائمة (السيرفر شغال 24 ساعة بدون جهازك)

### الخيار 1 — Hugging Face Spaces (مجاني، بدون بطاقة ائتمان)

- 2 vCPU + 16 GB RAM + 50 GB قرص — مجاني
- رابط ثابت زي `https://username-app.hf.space` بيشتغل 24 ساعة من غير جهازك
- الـ Space المجاني بينام بعد **48 ساعة** من غير زيارات — سطر واحد في cron-job.org بيخلّيه صاحي للأبد (تحت)

**خطوات الرفع (5 دقايق):**

1. اعمل حساب على [huggingface.co](https://huggingface.co)
2. **New → Space** → اكتب الاسم → **SDK: Docker** → **Blank** → **Public** → Create
3. من تبويب **Files** اضغط **Add file → Upload files** وارفع **كل** الملفات دي (اسحب الفولدرات زي ما هي):
   ```
   README.md            ← مهم جدًا: فيه إعدادات الـ Space (sdk: docker, app_port: 7860)
   app.py
   requirements.txt
   Dockerfile
   templates/index.html
   static/style.css
   static/app.js
   static/i18n.js
   static/ads.js
   ```
4. اضغط **Commit changes to main** واستنى البيلد (5–10 دقايق). أول ما يخلص هتلاقي الرابط شغال فوق في تبويب **App**.
5. **خلّيه ما ينامش:** اعمل حساب مجاني على [cron-job.org](https://cron-job.org) → **Create cronjob** → الرابط:
   ```
   https://USERNAME-SPACENAME.hf.space/healthz
   ```
   → كل **6 ساعات** → Save. كده أول زيارة بتبقى خلال أقل من دقيقة، وبيصحّى تلقائيًا.

> **بديل أسرع لو مش عايز ترفع ملف ملف:** استخدم Git.
> ```powershell
> git clone https://huggingface.co/spaces/USERNAME/SPACENAME
> Copy-Item "F:\new anime\python to exe\test web\webapp\*" ".\SPACENAME" -Recurse -Force
> cd SPACENAME ; git add . ; git commit -m "deploy" ; git push
> ```
> (لازم `git` يكون متثبت، وهيطلب منك username و access token من **Settings → Access Tokens**.)

> لو الـ Space قال "CPU Basic غير متاح" لحسابك، جرّب Oracle تحت — ده الحل الأقوى أصلًا.
> ⚠️ Hugging Face بتمنع الاستخدام التجاري/الإعلانات على الـ Spaces المجانية، فممكن يوقفوه لو اكتشفوا إعلانات. Oracle بتاعك لوحدك ومحدش بيمنعك من حاجة.

### الخيار 2 — Oracle Cloud Always Free (الأنسب للترافيك والإعلانات)

سيرفر ARM بـ 4 أنوية و24 GB رام **مجاني للأبد** وباندويث 10 TB شهريًا — يعني الموقع يشتغل لكل الناس بسرعة حقيقية، ومحدش بيقدر يوقفه بسبب الإعلانات.
محتاج بطاقة للتحقق فقط (بيتحجز مبلغ بسيط وبيترجع، مش بيتخصم منه).

```bash
# 1) اعمل VM: Oracle Console → Compute → Instances → Create
#    Image: Ubuntu 22.04 أو 24.04   |   Shape: VM.Standard.A1.Flex (Always Free)
#    نزّل الـ SSH key

# 2) من جهازك ارفع المشروع (استبدل IP والمفتاح)
scp -i key.pem -r "webapp" ubuntu@<IP>:/tmp/ytdl

# 3) على السيرفر: أمر واحد بس
ssh -i key.pem ubuntu@<IP>
sudo mv /tmp/ytdl /opt/ytdl
sudo DOMAIN=yourdomain.com bash /opt/ytdl/deploy/oracle-setup.sh
```

السكربت بيعمل كل حاجة: Docker + فتح البورتات 80/443 (Oracle بيقفلها افتراضيًا) + بناء الصورة + تشغيل بـ `--restart always` (يعني بعد أي reboot بيرجع لوحده) + Caddy لشهادة SSL مجانية.

**متنساش خطوتين في لوحة Oracle:**
- **Networking → VCN → Security Lists → Default Security List → Add Ingress Rule**: Source `0.0.0.0/0`، TCP، Port `80` وكمان `443`.
- **Reserved Public IP**: اربط IP ثابت بالـ VM عشان ما يتغيرش بعد reboot.

**الدومين:** أي دومين رخيص (~$1–10/سنة) من Namecheap/Cloudflare، واعمل A record بيشاور على IP السيرفر. الدومين ده هو اللي تضيفه في Adsterra.

### الخيار 3 — Render / Koyeb (للتجربة بس)

- **Render**: 512 MB RAM، بينام بعد 15 دقيقة، وباندويث ~5 GB/شهر (فيديوين تلاتة). ينفع تجربة سريعة مش موقع حقيقي.
- **Koyeb**: 512 MB / 0.1 vCPU — أضعف من Render.

### مقارنة سريعة

| | مجاني | دائم | بينام | باندويث | إعلانات | مناسب لـ |
|---|---|---|---|---|---|---|
| Cloudflare Tunnel من جهازك | ✅ | ❌ | ❌ | نتك | ❌ | تجربة سريعة |
| Hugging Face Spaces | ✅ بدون بطاقة | ✅ | بعد 48 س (بيتحل بالـ cron) | مشترك | ⚠️ ممنوع تجاريًا | إطلاق أول |
| Render | ✅ | ✅ | بعد 15 د | ~5 GB/شهر | ✅ | تجربة |
| Koyeb | ✅ | ✅ | ❌ | محدود | ✅ | تجربة |
| **Oracle Always Free** | ✅ | ✅ | ❌ | **10 TB/شهر** | ✅ | **ترافيك حقيقي** |


### الواقع بتاع «مئات الآلاف في نفس اللحظة»

مفيش استضافة مجانية تقدر على ده، والسبب رياضة بسيطة:

| الاستخدام | الباندويث الشهري |
|---|---|
| 100 مستخدم/يوم × فيديو 50MB | ~150 GB |
| 1,000 مستخدم/يوم | ~1.5 TB |
| 10,000 مستخدم/يوم | ~15 TB |
| 100,000 مستخدم/يوم | ~150 TB |

- **Oracle Always Free**: 10 TB/شهر → يناسب تقريبًا 500–700 تحميل يوميًا.
- **Render**: ~5 GB/شهر → فيديوهين تلاتة.
- **Hugging Face Spaces**: مش معمول للترافيك ده أصلًا، والاستخدام التجاري/الإعلانات ممكن يعرّض الـ Space للإيقاف.

يعني: Oracle هو الأنسب ويستحمل **عشرات التحميلات المتزامنة**، لكن «مئات الآلاف في نفس اللحظة» محتاج سيرفر مدفوع أو CDN + تخزين ملفات (S3/R2) — وده مش مجاني.

---

## النشر على Oracle Always Free (الأنسب للترافيك + الإعلانات)
# 1. من جهازك: ارفع المشروع للسيرفر
scp -r webapp ubuntu@<IP-السيرفر>:/tmp/ytdl

# 2. على السيرفر
sudo mv /tmp/ytdl /opt/ytdl
sudo bash /opt/ytdl/deploy/oracle-setup.sh

# 3. لو عندك دومين (مهم للإعلانات)
sudo DOMAIN=ytdownload.example.com bash /opt/ytdl/deploy/oracle-setup.sh
```

السكربت بيعمل لوحده: Docker + فتح البورتات (Oracle بيقفلها افتراضيًا) + بناء الصورة + تشغيل بـ auto-restart + Caddy لشهادة SSL مجانية.
**متنساش** إضافة Ingress Rule في لوحة Oracle للبورتات 80 و443 (الشرح مطبوع في آخر السكربت).

---

## الإعلانات (Adsterra) — وإزاي تتفادى مشاكل إعادة التوجيه

كل الإعلانات في ملف واحد: **`static/ads.js`** (عدّل المفاتيح من هناك بس).

| النوع | مكانه | ملاحظة |
|---|---|---|
| Banner 728×90 | فوق الصفحة | بيتصغّر تلقائيًا على الموبايل بدل ما يطلع بره الشاشة |
| Native | تحت زرار التحميل | جوه الصفحة، مفيش تحويل |
| Popunder | `<script>` مباشر في `templates/index.html` (الـ head) | **لازم** يكون tag حقيقي جوه الصفحة، مش متضاف بالجافاسكريبت |
| Direct link | تاب جديد فقط | في الفوتر + زرار «عرض ممول» بعد ما التحميل يخلص |

### ليه الـ popunder مكنش شغال؟ (اتصلح 3 حاجات)

1. **كان بيتحمّل بالجافاسكريبت بعد الصفحة.** سكريبت Adsterra بيربط نفسه على **أول كليك**، فلو اتضاف بعد ما الصفحة حمّلت بيفوّت الكليك ومش بيفتح حاجة. دلوقتي هو `<script>` حقيقي في الـ `<head>`.
2. **كان فيه `Referrer-Policy: same-origin`.** ده كان بيمنع إرسال اسم الدومين لـ Adsterra خالص، والسيرفر بتاعهم بيرفض الطلب من غير Referer. اتغيّر لـ `strict-origin-when-cross-origin`.
3. **التكرار في الجودات** مكنش له علاقة بالإعلانات — يوتيوب بيرجّع كل جودة مرتين (ملف مباشر + نسخة HLS)، ودلوقتي بقى فيه جودة واحدة لكل دقة.

### حاجات لسه بره الكود (لازم تعملها بنفسك)

- **أضف الدومين في Adsterra**: Websites → Add website. على `trycloudflare.com` أو `hf.space` السكريبت بيحمّل (200) بس **مش بيفتح إعلان ومش بيتحسب**.
- **الـ popunder بيتفتح مرة واحدة لكل زائر كل ~24 ساعة** — لو جرّبت كذا مرة ومحصلش حاجة، ده طبيعي. جرّب من متصفح تاني أو بعد مسح الكوكيز.
- **حاجب الإعلانات / popup blocker** بيمنعوه. جرّب في Chrome نضيف بدون إضافات.
- للتأكد: افتح Console واكتب `ADS.debug()` — لازم تلاقي `popunderTag: true` و`adsterraWillCount: true` (الأخيرة بتقول `false` على أي دومين مجاني أو localhost).


### قواعد لازم تلتزم بيها (دي اللي بتمنع مشاكل إعادة التوجيه والحظر)

1. **عمرك ما تحط الـ direct link على زرار التحميل نفسه.** لو الزائر دوس «تحميل» وطلع له إعلان، مش هيعرف ينزّل حاجة والموقع هيبان مكسور — وده كمان مخالف لشروط Adsterra (misleading).
2. **متشغّلش popunder و direct link على نفس الضغطة.** النتيجة: تابين + تجربة سيئة + احتمال تعليق الحساب.
3. **الـ direct link في تاب جديد** (`window.open(..., '_blank')`) — الصفحة الأصلية والتحميل مش بيتأثروا خالص. ده اللي معمول في `ads.js`.
4. **أضف الدومين في لوحة Adsterra** (Websites → Add website) قبل ما تنشر. الإعلانات مش بتتحسب على دومين مش مسجّل.
5. **الدومينات المجانية** (`trycloudflare.com`, `hf.space`, `duckdns.org`) غالبًا مرفوضة أو بتحصل مشاكل في الحساب — عشان كده Oracle + دومين رخيص هو الحل الصح لو هدفك الربح.
6. **الـ popunder على الموبايل بيزعّج جدًا** وChrome بيحظره كتير. لو لقيت نسبة خروج عالية، شيله وسيب البانر والـ native.

> نصيحة: ابدأ بالبانر + native بس لمدة أسبوع، وشوف الأرباح والـ bounce rate، وبعدها ضيف popunder لو الأرقام تستاهل.

---

## ⚠️ أهم مشكلة هتقابلك: «Sign in to confirm you're not a bot»

يوتيوب بيمنع أي IP تابع لشركة استضافة (Hugging Face / Render / AWS...) ويطلب تسجيل دخول. الحل من الاتنين دول:

**1) كوكيز من حساب Google (الأسهل)**
- من متصفح مسجّل فيه دخول، صدّر الكوكيز بصيغة Netscape باستخدام إضافة زي *Get cookies.txt LOCALLY*
- حوّلها base64:
  ```powershell
  [Convert]::ToBase64String([IO.File]::ReadAllBytes("cookies.txt")) > cookies.b64
  ```
- حطّ الناتج في متغير بيئة `COOKIES_B64` في لوحة الاستضافة

> استخدم حساب Google احتياطي، لأن الكوكيز دي بتدي وصول كامل للحساب.

**2) بروكسي سكني**
حط `YTDLP_PROXY=http://user:pass@host:port` — ده بيتخطى الحجب نهائيًا، بس البروكسي السكني بفلوس غالبًا.

في الحالتين فيه متغير `YTDLP_IMPERSONATE=chrome` (مفعّل في `.env.example`) بيقلل الحجب بشكل ملحوظ.

---

## الإعدادات (كلها اختيارية)

| المتغير | الافتراضي | الوظيفة |
|---|---|---|
| `PORT` | 7860 | بورت السيرفر (الاستضافات بتحدده لوحدها) |
| `MAX_CONCURRENT` | 2 | عدد التحميلات في نفس اللحظة (512 MB → 1) |
| `FILE_TTL` | 0 | ثواني قبل حذف الملف. **0 = متحذفش بالوقت خالص** (النت الضعيف له وقت مفتوح) |
| `MAX_STORAGE_MB` | 20000 | أقصى مساحة للملفات (20GB). لما تتملى، بيحذف الأقدم استخدامًا الأول |
| `MAX_HEIGHT` | 0 | أقصى ارتفاع للفيديو (مثال 1080) |
| `MAX_DURATION` | 0 | أقصى مدة بالثواني (مثال 3600) |
| `RATE_FETCH` | 120 | عدد طلبات جلب الصيغ لكل IP في الساعة |
| `RATE_DOWNLOAD` | 60 | عدد التحميلات لكل IP في الساعة |
| `COOKIES_B64` | — | كوكيز base64 لتخطي حجب يوتيوب |
| `YTDLP_PROXY` | — | بروكسي لـ yt-dlp |
| `YTDLP_IMPERSONATE` | — | تقليد متصفح (`chrome`) |
| `YTDLP_EXTRACTOR_ARGS` | — | إعدادات إضافية لـ yt-dlp |

---

## تجربة الصورة بنفسها قبل النشر

```powershell
cd webapp
docker compose up --build
# افتح http://localhost:7860
```

أو من غير Docker: `.\run.ps1`

---

## ملاحظات مهمة

- **القانون:** تنزيل فيديوهات يوتيوب مخالف لشروط استخدام يوتيوب، ونشر أداة عامة بيعمل كده ممكن يعرّض الاستضافة للحظر أو شكاوى حقوق ملكية. استخدمها بمسؤوليتك، وخلّي في بالك إن في ناس بتستخدم استضافات مجانية بترفض المحتوى ده.
- **التحديث:** يوتيوب بيغيّر حاجاته كل فترة. أعد بناء الصورة (Redeploy) كل أسبوعين عشان تجيب آخر إصدار من yt-dlp.
- **الأمان:** متضيفش أي endpoint بينفّذ أوامر من المتصفح تاني. اللي كان موجود كان هيدّي أي زائر تحكّم كامل في السيرفر.
- **الأداء:** ffmpeg بيشتغل بـ `-c copy` (من غير إعادة ترميز) فالدمج سريع جدًا وقليل الاستهلاك للبروسيسور.

---

# English summary

A hardened, deployable version of the local Flask app.

**What was fixed:** no `127.0.0.1` binding, the remote-code-execution endpoint `/api/run_terminal` is gone, no Windows-only APIs, no server paths from the client, concurrency + rate limits, chapter downloads return one ZIP, bilingual UI (EN/AR with RTL).

**Files are never deleted because of age** (`FILE_TTL=0`). They only go away when `MAX_STORAGE_MB` is reached, and then the least recently downloaded file goes first. Downloads also support HTTP Range, so a dropped connection can be resumed instead of starting over.

**Run locally / publish instantly (free, no account):**

```powershell
.\run.ps1 -Public     # local server + https://xxx.trycloudflare.com
```

**Deploy permanently (no PC involved):** upload `webapp/` to any Docker host, or:
- **Oracle Cloud Always Free** — 4 ARM cores / 24 GB / 10 TB egress, free forever. `deploy/oracle-setup.sh` does the whole install.
- Hugging Face Spaces (Docker, Blank) — free, needs a `README.md` with `sdk: docker` (already included); keep it awake with cron-job.org hitting `/healthz`
- Render Blueprint (`render.yaml`) — free, 512 MB, sleeps, ~5 GB/month bandwidth
- Koyeb — free, 512 MB
- Any Docker host: `docker build -t ytd . && docker run -p 7860:7860 ytd`

**YouTube bot checks:** datacenter IPs often need `COOKIES_B64` (Netscape cookies, base64) or `YTDLP_PROXY`. Running from a home connection through Cloudflare Tunnel avoids the problem entirely.

**Keep `--workers 1`**: jobs live in memory, so more than one gunicorn worker breaks task polling.
