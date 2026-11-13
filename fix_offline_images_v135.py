import os, sys, pathlib

print("=" * 72)
print("🛡️ تركيب نظام حماية الصور والتنبيه الذكي عند انقطاع الإنترنت (v135)")
print("=" * 72)

html_path = pathlib.Path("client/index.html")
if not html_path.exists():
    print("❌ لم يتم العثور على client/index.html")
    sys.exit(1)

html = html_path.read_text(encoding="utf-8")

# إزالة أي نسخة سابقة إن وجدت
start_marker = "<!-- ORIGINAL_OFFLINE_IMAGE_GUARD_V135_START -->"
end_marker = "<!-- ORIGINAL_OFFLINE_IMAGE_GUARD_V135_END -->"
if start_marker in html and end_marker in html:
    s_idx = html.index(start_marker)
    e_idx = html.index(end_marker) + len(end_marker)
    html = html[:s_idx] + html[e_idx:]

guard_snippet = r"""<!-- ORIGINAL_OFFLINE_IMAGE_GUARD_V135_START -->
<style>
  #orig-offline-toast-v135 {
    position: fixed;
    top: 12px;
    left: 50%;
    transform: translateX(-50%) translateY(-150%);
    z-index: 999999;
    background: linear-gradient(135deg, #13462f 0%, #0b2b1d 100%);
    color: #ffffff;
    border: 1.5px solid #d8b454;
    border-radius: 999px;
    padding: 10px 18px;
    box-shadow: 0 10px 28px rgba(0, 0, 0, 0.35);
    display: flex;
    align-items: center;
    gap: 10px;
    font-family: 'Tajawal', 'Cairo', sans-serif;
    font-size: 13px;
    font-weight: 700;
    direction: rtl;
    max-width: 92vw;
    transition: transform 0.35s cubic-bezier(0.22, 1, 0.36, 1), opacity 0.3s ease;
    opacity: 0;
    pointer-events: none;
  }
  #orig-offline-toast-v135.orig-toast-visible {
    transform: translateX(-50%) translateY(0);
    opacity: 1;
    pointer-events: auto;
  }
  #orig-offline-toast-v135 button {
    background: linear-gradient(135deg, #e5c467 0%, #c9a03d 100%);
    color: #0b2b1d;
    border: none;
    border-radius: 999px;
    padding: 4px 12px;
    font-family: inherit;
    font-size: 12px;
    font-weight: 800;
    cursor: pointer;
    white-space: nowrap;
  }
  img[data-orig-fallback="1"] {
    object-fit: cover !important;
    background: #13462f !important;
  }
</style>
<script>
(function() {
  var XML_NS = ["http", "://www.w3.org/2000/svg"].join("");
  var toastEl = null;
  var hadImageNetworkError = false;

  function ensureToast() {
    if (toastEl) return toastEl;
    if (!document.body) return null;
    toastEl = document.createElement("div");
    toastEl.id = "orig-offline-toast-v135";
    var msgSpan = document.createElement("span");
    msgSpan.id = "orig-offline-msg-v135";
    msgSpan.textContent = "لا يوجد لديك إنترنت حالياً — ستظهر الصور تلقائياً فور عودة الشبكة";
    var retryBtn = document.createElement("button");
    retryBtn.type = "button";
    retryBtn.textContent = "إعادة المحاولة";
    retryBtn.onclick = function() {
      retryAllBrokenImages();
    };
    toastEl.appendChild(msgSpan);
    toastEl.appendChild(retryBtn);
    document.body.appendChild(toastEl);
    return toastEl;
  }

  function showOfflineToast(customText) {
    var el = ensureToast();
    if (!el) return;
    var msg = document.getElementById("orig-offline-msg-v135");
    if (msg && customText) msg.textContent = customText;
    el.classList.add("orig-toast-visible");
  }

  function hideOfflineToast() {
    if (!toastEl) return;
    toastEl.classList.remove("orig-toast-visible");
  }

  function cleanXmlText(str) {
    return String(str || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&apos;")
      .trim();
  }

  function extractItemTitle(img) {
    var alt = (img.getAttribute("alt") || "").trim();
    if (alt && alt !== "image" && alt !== "img" && alt !== "product" && alt !== "banner") {
      return alt;
    }
    var card = img.closest("article, button, a, [class*='card'], [class*='item'], div");
    if (card) {
      var heading = card.querySelector("h1, h2, h3, h4, [class*='title'], [class*='name']");
      if (heading && heading.textContent) {
        var t = heading.textContent.trim();
        if (t.length > 1 && t.length < 70) return t;
      }
    }
    return "متجر أورجنال";
  }

  function splitTitleLines(title, maxLen) {
    var words = title.split(/\s+/);
    var line1 = "";
    var line2 = "";
    for (var i = 0; i < words.length; i++) {
      if ((line1 + " " + words[i]).trim().length <= maxLen || !line1) {
        line1 = (line1 + " " + words[i]).trim();
      } else {
        line2 = (line2 + " " + words[i]).trim();
      }
    }
    if (line2.length > maxLen) {
      line2 = line2.slice(0, maxLen - 1) + "…";
    }
    return [line1, line2];
  }

  function buildFallbackSvg(img, title, isOffline) {
    var w = img.clientWidth || img.width || 300;
    var h = img.clientHeight || img.height || 300;
    var isBanner = (w > h * 1.45);
    var vw = isBanner ? 640 : 340;
    var vh = isBanner ? 270 : 340;
    var lines = splitTitleLines(title, isBanner ? 34 : 20);
    var line1 = cleanXmlText(lines[0] || "متجر أورجنال");
    var line2 = cleanXmlText(lines[1] || "");
    var statusText = isOffline ? "لا يوجد لديك إنترنت" : "الصورة قيد التحديث";

    var centerY = isBanner ? (line2 ? 105 : 118) : (line2 ? 142 : 158);
    var line2Y = centerY + 34;
    var pillY = isBanner ? 172 : 212;
    var pillW = isBanner ? 210 : 196;
    var pillX = (vw - pillW) / 2;

    var svg = '<svg xmlns="' + XML_NS + '" viewBox="0 0 ' + vw + ' ' + vh + '" width="100%" height="100%" dir="rtl">' +
      '<defs>' +
        '<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">' +
          '<stop offset="0%" stop-color="#185438"/>' +
          '<stop offset="100%" stop-color="#0b2b1d"/>' +
        '</linearGradient>' +
        '<linearGradient id="gold" x1="0" y1="0" x2="1" y2="0">' +
          '<stop offset="0%" stop-color="#e5c467"/>' +
          '<stop offset="100%" stop-color="#c89e3a"/>' +
        '</linearGradient>' +
      '</defs>' +
      '<rect width="' + vw + '" height="' + vh + '" rx="18" fill="url(#bg)"/>' +
      '<rect x="10" y="10" width="' + (vw - 20) + '" height="' + (vh - 20) + '" rx="14" fill="none" stroke="#d8b454" stroke-opacity="0.35" stroke-width="1.5"/>' +
      '<circle cx="' + (vw / 2) + '" cy="' + (isBanner ? 54 : 82) + '" r="18" fill="#d8b454" fill-opacity="0.15" stroke="#d8b454" stroke-width="1.4"/>' +
      '<text x="' + (vw / 2) + '" y="' + (isBanner ? 60 : 88) + '" text-anchor="middle" fill="#d8b454" font-family="Tajawal, Cairo, sans-serif" font-size="16" font-weight="800">O</text>' +
      '<text x="' + (vw / 2) + '" y="' + centerY + '" text-anchor="middle" fill="#ffffff" font-family="Tajawal, Cairo, sans-serif" font-size="' + (isBanner ? 24 : 21) + '" font-weight="800">' + line1 + '</text>' +
      (line2 ? '<text x="' + (vw / 2) + '" y="' + line2Y + '" text-anchor="middle" fill="#f3f4f6" font-family="Tajawal, Cairo, sans-serif" font-size="' + (isBanner ? 21 : 19) + '" font-weight="700">' + line2 + '</text>' : '') +
      '<rect x="' + pillX + '" y="' + pillY + '" width="' + pillW + '" height="36" rx="18" fill="url(#gold)"/>' +
      '<text x="' + (vw / 2) + '" y="' + (pillY + 24) + '" text-anchor="middle" fill="#0b2b1d" font-family="Tajawal, Cairo, sans-serif" font-size="15" font-weight="800">' + statusText + '</text>' +
    '</svg>';

    return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
  }

  function handleBrokenImage(img) {
    if (!img || img.tagName !== "IMG") return;
    var currentSrc = img.getAttribute("src") || "";
    if (currentSrc.indexOf("data:image/svg+xml") === 0) return;

    if (!img.getAttribute("data-orig-src") && currentSrc) {
      img.setAttribute("data-orig-src", currentSrc);
    }

    var isOffline = !navigator.onLine;
    var title = extractItemTitle(img);
    img.setAttribute("data-orig-fallback", "1");
    img.src = buildFallbackSvg(img, title, true);

    hadImageNetworkError = true;
    if (isOffline) {
      showOfflineToast("لا يوجد لديك إنترنت حالياً — ستظهر الصور تلقائياً فور عودة الشبكة");
    } else {
      showOfflineToast("ضعف في الشبكة تعذر معه تحميل بعض الصور — اضغط إعادة المحاولة");
    }
  }

  function retryAllBrokenImages() {
    var brokenList = document.querySelectorAll('img[data-orig-fallback="1"]');
    if (!brokenList.length) {
      if (navigator.onLine) hideOfflineToast();
      return;
    }
    if (!navigator.onLine) {
      showOfflineToast("لا يزال الإنترنت مقطوعاً — يرجى التحقق من اتصالك بالشبكة");
      return;
    }
    hideOfflineToast();
    for (var i = 0; i < brokenList.length; i++) {
      (function(imgEl) {
        var orig = imgEl.getAttribute("data-orig-src");
        if (!orig) return;
        var sep = orig.indexOf("?") === -1 ? "?" : "&";
        var retryUrl = orig.indexOf("data:") === 0 ? orig : (orig + sep + "_r=" + Date.now());
        var tester = new Image();
        tester.onload = function() {
          imgEl.removeAttribute("data-orig-fallback");
          imgEl.src = orig;
        };
        tester.onerror = function() {
          // تبقى البطاقة الأنيقة كما هي بدون أيقونة مكسورة
        };
        tester.src = retryUrl;
      })(brokenList[i]);
    }
  }

  // التقاط أخطاء الصور في مرحلة Capture قبل ظهور أيقونة المتصفح المكسورة
  window.addEventListener("error", function(ev) {
    var target = ev.target || ev.srcElement;
    if (target && target.tagName === "IMG") {
      handleBrokenImage(target);
    }
  }, true);

  window.addEventListener("offline", function() {
    showOfflineToast("انقطع الاتصال بالإنترنت — يرجى التحقق من الشبكة");
    var imgs = document.querySelectorAll('img[data-orig-fallback="1"]');
    for (var i = 0; i < imgs.length; i++) {
      var title = extractItemTitle(imgs[i]);
      imgs[i].src = buildFallbackSvg(imgs[i], title, true);
    }
  });

  window.addEventListener("online", function() {
    retryAllBrokenImages();
  });

  // فحص دوري كل 6 ثوانٍ لإعادة تحميل الصور تلقائياً عند عودة الشبكة
  setInterval(function() {
    if (navigator.onLine && document.querySelector('img[data-orig-fallback="1"]')) {
      retryAllBrokenImages();
    }
  }, 6000);
})();
</script>
<!-- ORIGINAL_OFFLINE_IMAGE_GUARD_V135_END -->"""

if "</body>" in html:
    html = html.replace("</body>", guard_snippet + "\n</body>", 1)
else:
    html = html + "\n" + guard_snippet

html_path.write_text(html, encoding="utf-8")
print("✅ تم تركيب نظام البطاقة البديلة الأنيقة والتنبيه الفوري لانقطاع الإنترنت في client/index.html")

os.system("git add client/index.html && git commit -m 'Feat v135: graceful offline banner & centered product name fallback for broken images' && git push origin main")
print("🚀 تم رفع التحديث v135 إلى Render بنجاح!")
