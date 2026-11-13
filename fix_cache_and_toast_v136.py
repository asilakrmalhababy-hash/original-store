import os, re, sys, pathlib, subprocess

print("=" * 72)
print("🚀 إصلاح كاش الصور القديمة + ضبط شريط تنبيه الإنترنت النحيف (v136)")
print("=" * 72)

# 1. مسح أي ملفات كاش قديمة محلياً
for f in [".catalog-cache.json", "server/.catalog-cache.json"]:
    p = pathlib.Path(f)
    if p.exists():
        p.unlink()
        print(f"🗑️ تم مسح ملف الكاش القديم: {f}")

# 2. تحديث server/_core/index.ts لمنع تخزين الصور القديمة للأبد (immutable)
srv_path = pathlib.Path("server/_core/index.ts")
if srv_path.exists():
    srv = srv_path.read_text(encoding="utf-8")
    srv_new = srv.replace(
        "max-age=31536000, immutable",
        "max-age=0, must-revalidate"
    ).replace(
        "max-age=86400",
        "max-age=0, must-revalidate"
    )
    if srv_new != srv:
        srv_path.write_text(srv_new, encoding="utf-8")
        print("✅ تم تحديث ترويسة الكاش في server/_core/index.ts لمنع الصور القديمة")

# 3. تحديث client/index.html: شريط إنترنت أفقي نحيف + كاسر كاش تلقائي لصور الأقسام والمنتجات
html_path = pathlib.Path("client/index.html")
if not html_path.exists():
    print("❌ لم يتم العثور على client/index.html")
    sys.exit(1)

html = html_path.read_text(encoding="utf-8")

for marker_pair in [
    ("<!-- ORIGINAL_OFFLINE_IMAGE_GUARD_V135_START -->", "<!-- ORIGINAL_OFFLINE_IMAGE_GUARD_V135_END -->"),
    ("<!-- ORIGINAL_OFFLINE_IMAGE_GUARD_V136_START -->", "<!-- ORIGINAL_OFFLINE_IMAGE_GUARD_V136_END -->"),
]:
    if marker_pair[0] in html and marker_pair[1] in html:
        s_idx = html.index(marker_pair[0])
        e_idx = html.index(marker_pair[1]) + len(marker_pair[1])
        html = html[:s_idx] + html[e_idx:]

guard_v136 = r"""<!-- ORIGINAL_OFFLINE_IMAGE_GUARD_V136_START -->
<style>
  #orig-offline-bar-v136 {
    position: fixed !important;
    top: 10px !important;
    left: 50% !important;
    transform: translateX(-50%) translateY(-180%) !important;
    z-index: 2147483647 !important;
    width: calc(100vw - 24px) !important;
    max-width: 410px !important;
    height: 44px !important;
    min-height: 44px !important;
    max-height: 44px !important;
    background: linear-gradient(135deg, #13462f 0%, #0b2b1d 100%) !important;
    color: #ffffff !important;
    border: 1.5px solid #d8b454 !important;
    border-radius: 12px !important;
    padding: 0 12px !important;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35) !important;
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    align-items: center !important;
    justify-content: space-between !important;
    gap: 10px !important;
    font-family: 'Tajawal', 'Cairo', sans-serif !important;
    direction: rtl !important;
    box-sizing: border-box !important;
    transition: transform 0.3s ease, opacity 0.25s ease !important;
    opacity: 0 !important;
    pointer-events: none !important;
  }
  #orig-offline-bar-v136.orig-bar-show {
    transform: translateX(-50%) translateY(0) !important;
    opacity: 1 !important;
    pointer-events: auto !important;
  }
  #orig-offline-bar-v136 .orig-bar-txt {
    flex: 1 1 auto !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    font-size: 12.5px !important;
    font-weight: 700 !important;
    color: #ffffff !important;
    text-align: right !important;
    line-height: 44px !important;
    margin: 0 !important;
    padding: 0 !important;
  }
  #orig-offline-bar-v136 .orig-bar-btn {
    flex: 0 0 auto !important;
    width: auto !important;
    height: 28px !important;
    min-height: 28px !important;
    background: linear-gradient(135deg, #e5c467 0%, #c9a03d 100%) !important;
    color: #0b2b1d !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0 10px !important;
    font-family: 'Tajawal', 'Cairo', sans-serif !important;
    font-size: 11.5px !important;
    font-weight: 800 !important;
    line-height: 28px !important;
    cursor: pointer !important;
    white-space: nowrap !important;
    margin: 0 !important;
  }
  img[data-orig-fallback="1"] {
    object-fit: cover !important;
    background: #13462f !important;
  }
</style>
<script>
(function() {
  var XML_NS = ["http", "://www.w3.org/2000/svg"].join("");
  var CACHE_EPOCH_KEY = "orig_cluster2_epoch_v136";
  var sessionStamp = localStorage.getItem(CACHE_EPOCH_KEY);

  // 1. تطهير كاش المتصفح القديم لمرة واحدة عند الانتقال للكلاستر الجديد
  if (!sessionStamp) {
    sessionStamp = String(Date.now());
    try {
      for (var k in localStorage) {
        if (k && k.indexOf("cart") === -1 && k.indexOf("auth") === -1 && k.indexOf("admin") === -1) {
          if (k.indexOf("catalog") !== -1 || k.indexOf("cache") !== -1 || k.indexOf("img") !== -1 || k.indexOf("store") !== -1) {
            localStorage.removeItem(k);
          }
        }
      }
      localStorage.setItem(CACHE_EPOCH_KEY, sessionStamp);
      if (window.caches && window.caches.keys) {
        window.caches.keys().then(function(names) {
          for (var i = 0; i < names.length; i++) {
            window.caches.delete(names[i]);
          }
        });
      }
    } catch (e) {}
  }

  // تحديث البصمة عند حفظ أي منتج أو قسم في لوحة التحكم
  var origFetch = window.fetch;
  if (origFetch) {
    window.fetch = function() {
      var urlArg = arguments[0];
      var urlStr = typeof urlArg === "string" ? urlArg : (urlArg && urlArg.url ? urlArg.url : "");
      if (urlStr.indexOf("admin.") !== -1 || urlStr.indexOf("create") !== -1 || urlStr.indexOf("update") !== -1 || urlStr.indexOf("upload") !== -1) {
        sessionStamp = String(Date.now());
        try { localStorage.setItem(CACHE_EPOCH_KEY, sessionStamp); } catch (e) {}
      }
      return origFetch.apply(this, arguments);
    };
  }

  // 2. كسر الكاش القديم لأي رابط صورة /api/fast-img/ أو /api/img/
  function bustStaleImageCache(root) {
    var imgs = (root || document).querySelectorAll ? (root || document).querySelectorAll("img") : [];
    for (var i = 0; i < imgs.length; i++) {
      var img = imgs[i];
      var src = img.getAttribute("src") || "";
      if ((src.indexOf("/api/fast-img/") !== -1 || src.indexOf("/api/img/") !== -1) && src.indexOf("_v136=") === -1) {
        var sep = src.indexOf("?") === -1 ? "?" : "&";
        img.setAttribute("src", src + sep + "_v136=" + sessionStamp);
      }
    }
  }

  var obs = new MutationObserver(function(mutations) {
    for (var i = 0; i < mutations.length; i++) {
      var added = mutations[i].addedNodes;
      for (var j = 0; j < added.length; j++) {
        var node = added[j];
        if (node && node.nodeType === 1) {
          if (node.tagName === "IMG") {
            bustStaleImageCache(node.parentNode || document);
          } else if (node.querySelectorAll) {
            bustStaleImageCache(node);
          }
        }
      }
    }
  });
  if (document.documentElement) {
    obs.observe(document.documentElement, { childList: true, subtree: true });
  }
  window.addEventListener("DOMContentLoaded", function() { bustStaleImageCache(document); });

  // 3. شريط التنبيه الأفقي النحيف عند انقطاع الإنترنت
  var barEl = null;
  function ensureBar() {
    if (barEl) return barEl;
    if (!document.body) return null;
    barEl = document.createElement("div");
    barEl.id = "orig-offline-bar-v136";
    var txt = document.createElement("span");
    txt.className = "orig-bar-txt";
    txt.id = "orig-offline-txt-v136";
    txt.textContent = "📡 لا يوجد اتصال بالإنترنت حالياً";
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "orig-bar-btn";
    btn.textContent = "إعادة المحاولة";
    btn.onclick = function() { retryAllBrokenImages(); };
    barEl.appendChild(txt);
    barEl.appendChild(btn);
    document.body.appendChild(barEl);
    return barEl;
  }

  function showBar(msg) {
    var el = ensureBar();
    if (!el) return;
    var t = document.getElementById("orig-offline-txt-v136");
    if (t && msg) t.textContent = msg;
    el.classList.add("orig-bar-show");
  }

  function hideBar() {
    if (barEl) barEl.classList.remove("orig-bar-show");
  }

  function cleanXml(str) {
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
    var l1 = "", l2 = "";
    for (var i = 0; i < words.length; i++) {
      if ((l1 + " " + words[i]).trim().length <= maxLen || !l1) {
        l1 = (l1 + " " + words[i]).trim();
      } else {
        l2 = (l2 + " " + words[i]).trim();
      }
    }
    if (l2.length > maxLen) l2 = l2.slice(0, maxLen - 1) + "…";
    return [l1, l2];
  }

  function buildFallbackSvg(img, title) {
    var w = img.clientWidth || img.width || 300;
    var h = img.clientHeight || img.height || 300;
    var isBanner = (w > h * 1.45);
    var vw = isBanner ? 640 : 340;
    var vh = isBanner ? 270 : 340;
    var lines = splitTitleLines(title, isBanner ? 34 : 18);
    var line1 = cleanXml(lines[0] || "متجر أورجنال");
    var line2 = cleanXml(lines[1] || "");
    var centerY = isBanner ? (line2 ? 110 : 122) : (line2 ? 145 : 162);
    var pillY = isBanner ? 174 : 214;
    var pillW = 196;
    var pillX = (vw - pillW) / 2;

    var svg = '<svg xmlns="' + XML_NS + '" viewBox="0 0 ' + vw + ' ' + vh + '" width="100%" height="100%" dir="rtl">' +
      '<defs>' +
        '<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">' +
          '<stop offset="0%" stop-color="#185438"/><stop offset="100%" stop-color="#0b2b1d"/>' +
        '</linearGradient>' +
        '<linearGradient id="gold" x1="0" y1="0" x2="1" y2="0">' +
          '<stop offset="0%" stop-color="#e5c467"/><stop offset="100%" stop-color="#c89e3a"/>' +
        '</linearGradient>' +
      '</defs>' +
      '<rect width="' + vw + '" height="' + vh + '" rx="18" fill="url(#bg)"/>' +
      '<rect x="10" y="10" width="' + (vw - 20) + '" height="' + (vh - 20) + '" rx="14" fill="none" stroke="#d8b454" stroke-opacity="0.35" stroke-width="1.5"/>' +
      '<text x="' + (vw / 2) + '" y="' + centerY + '" text-anchor="middle" fill="#ffffff" font-family="Tajawal, Cairo, sans-serif" font-size="' + (isBanner ? 24 : 21) + '" font-weight="800">' + line1 + '</text>' +
      (line2 ? '<text x="' + (vw / 2) + '" y="' + (centerY + 32) + '" text-anchor="middle" fill="#f3f4f6" font-family="Tajawal, Cairo, sans-serif" font-size="' + (isBanner ? 20 : 18) + '" font-weight="700">' + line2 + '</text>' : '') +
      '<rect x="' + pillX + '" y="' + pillY + '" width="' + pillW + '" height="34" rx="17" fill="url(#gold)"/>' +
      '<text x="' + (vw / 2) + '" y="' + (pillY + 23) + '" text-anchor="middle" fill="#0b2b1d" font-family="Tajawal, Cairo, sans-serif" font-size="14" font-weight="800">لا يوجد لديك إنترنت</text>' +
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
    var title = extractItemTitle(img);
    img.setAttribute("data-orig-fallback", "1");
    img.src = buildFallbackSvg(img, title);
    showBar(!navigator.onLine ? "📡 لا يوجد لديك إنترنت حالياً" : "📡 ضعف في الشبكة — اضغط إعادة المحاولة");
  }

  function retryAllBrokenImages() {
    var list = document.querySelectorAll('img[data-orig-fallback="1"]');
    if (!list.length) {
      if (navigator.onLine) hideBar();
      return;
    }
    if (!navigator.onLine) {
      showBar("📡 لا يزال الإنترنت مقطوعاً");
      return;
    }
    hideBar();
    for (var i = 0; i < list.length; i++) {
      (function(imgEl) {
        var orig = imgEl.getAttribute("data-orig-src");
        if (!orig) return;
        var sep = orig.indexOf("?") === -1 ? "?" : "&";
        var retryUrl = orig.indexOf("data:") === 0 ? orig : (orig + sep + "_r=" + Date.now());
        var tester = new Image();
        tester.onload = function() {
          imgEl.removeAttribute("data-orig-fallback");
          imgEl.src = retryUrl;
        };
        tester.src = retryUrl;
      })(list[i]);
    }
  }

  window.addEventListener("error", function(ev) {
    var target = ev.target || ev.srcElement;
    if (target && target.tagName === "IMG") handleBrokenImage(target);
  }, true);

  window.addEventListener("offline", function() {
    showBar("📡 لا يوجد لديك إنترنت حالياً");
  });

  window.addEventListener("online", function() {
    retryAllBrokenImages();
  });

  setInterval(function() {
    if (navigator.onLine && document.querySelector('img[data-orig-fallback="1"]')) {
      retryAllBrokenImages();
    }
  }, 6000);
})();
</script>
<!-- ORIGINAL_OFFLINE_IMAGE_GUARD_V136_END -->"""

if "</body>" in html:
    html = html.replace("</body>", guard_v136 + "\n</body>", 1)
else:
    html = html + "\n" + guard_v136

html_path.write_text(html, encoding="utf-8")
print("✅ تم تحديث client/index.html: شريط تنبيه نحيف + منع ظهور أي صورة قديمة مخزنة في المتصفح")

os.system("git add -A && git commit -m 'Fix v136: bust stale browser image cache on new cluster and fix slim horizontal offline bar' && git push origin main")
print("🚀 تم رفع التحديث v136 إلى Render!")
