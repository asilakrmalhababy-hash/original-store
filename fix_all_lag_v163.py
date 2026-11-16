import re, subprocess

index_path = "client/index.html"
with open(index_path, "r", encoding="utf-8") as f:
    html = f.read()

# 1. إزالة أي حارس أداء سابق أو نسخ سابقة من كود حسابي (v157 - v163)
html = re.sub(
    r'<!-- ORIGINAL PERF GUARD V163 START -->.*?<!-- ORIGINAL PERF GUARD V163 END -->\s*',
    '',
    html,
    flags=re.DOTALL
)
html = re.sub(
    r'<!-- ORIGINAL ACCOUNT (?:POLISH V157|REDESIGN V158|REDESIGN V159|FULL POLISH V160|PERFECT V161|FAST V162|ULTRA V163) START -->.*?<!-- ORIGINAL ACCOUNT (?:POLISH V157|REDESIGN V158|REDESIGN V159|FULL POLISH V160|PERFECT V161|FAST V162|ULTRA V163) END -->\s*',
    '',
    html,
    flags=re.DOTALL
)

# 2. حقن حارس الأداء العام في أعلى <head> لمنع أي MutationObserver قديم من تعليق التمرير أو الدخول في حلقة لا نهائية
perf_guard = r"""<!-- ORIGINAL PERF GUARD V163 START -->
<script>
(function() {
  if (window.__origPerfGuardV163) return;
  window.__origPerfGuardV163 = true;

  let isScrolling = false;
  let scrollTimer = null;
  const pendingRunners = new Set();

  function markScrolling() {
    isScrolling = true;
    if (scrollTimer) clearTimeout(scrollTimer);
    scrollTimer = setTimeout(() => {
      isScrolling = false;
      pendingRunners.forEach(fn => {
        try { fn(); } catch (_) {}
      });
      pendingRunners.clear();
    }, 180);
  }

  window.addEventListener("scroll", markScrolling, { passive: true });
  window.addEventListener("touchmove", markScrolling, { passive: true });

  const NativeMO = window.MutationObserver;
  if (NativeMO) {
    window.MutationObserver = function(callback) {
      let timer = null;
      let running = false;
      let lastRecords = [];
      let moInstance = null;

      const invoke = () => {
        if (running) return;
        running = true;
        const recs = lastRecords.length ? lastRecords.splice(0, lastRecords.length) : [];
        try {
          callback(recs, moInstance);
        } catch (_) {}
        setTimeout(() => { running = false; }, 120);
      };

      moInstance = new NativeMO(function(records) {
        if (running) return;
        lastRecords = records;
        if (timer) return;
        timer = setTimeout(() => {
          timer = null;
          if (isScrolling) {
            pendingRunners.add(invoke);
          } else {
            requestAnimationFrame(invoke);
          }
        }, 220);
      });
      return moInstance;
    };
    window.MutationObserver.prototype = NativeMO.prototype;
  }
})();
</script>
<!-- ORIGINAL PERF GUARD V163 END -->"""

if "<head>" in html:
    html = html.replace("<head>", "<head>\n" + perf_guard, 1)
else:
    html = perf_guard + "\n" + html

# 3. كود التحديث الشامل والخفيف v163 (شريط البحث + إيقاف سبينر نهاية المنتجات + واجهة حسابي السلسة بدون أي تعليق)
block_v163 = r"""<!-- ORIGINAL ACCOUNT ULTRA V163 START -->
<style id="orig-account-ultra-v163">
  :root {
    --orig-em-dark: #0b2b1d;
    --orig-em-main: #13462f;
    --orig-em-mid: #1a5c3e;
    --orig-gold: #d8b454;
    --orig-gold-light: #e7c972;
    --orig-cream: #f8f7f2;
  }

  /* 1. إصلاح شريط البحث في جميع الصفحات بإطار واحد نظيف وثابت */
  header.store-header .header-search {
    flex: 1 0 100% !important;
    order: 3 !important;
    width: 100% !important;
    margin: 4px 0 0 0 !important;
    padding: 0 14px !important;
    height: 42px !important;
    min-height: 42px !important;
    background: #ffffff !important;
    border: 1.5px solid rgba(216, 180, 84, 0.65) !important;
    border-radius: 999px !important;
    box-shadow: 0 2px 8px rgba(19, 70, 47, 0.05) !important;
    display: flex !important;
    align-items: center !important;
    box-sizing: border-box !important;
  }
  header.store-header .header-search > div,
  header.store-header .header-search input {
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
    background: transparent !important;
    width: 100% !important;
    height: 100% !important;
    padding: 0 6px !important;
    margin: 0 !important;
  }

  /* 2. إخفاء سطر "جارٍ عرض المزيد من المنتجات..." عند ظهور "وصلت إلى نهاية المنتجات" */
  .orig-hide-stuck-loader {
    display: none !important;
  }

  /* 3. حاوية صفحة حسابي */
  .original-account-page {
    background: var(--orig-cream) !important;
    min-height: calc(100vh - 130px) !important;
    padding: 12px 14px 105px 14px !important;
    direction: rtl !important;
    font-family: 'Cairo', 'Tajawal', sans-serif !important;
    position: relative !important;
    overflow-x: hidden !important;
  }

  .original-account-page > .page-title-row,
  #orig-vip-loyalty-section-v140 {
    display: none !important;
  }

  /* إخفاء فقاعة الواتساب العائمة داخل صفحة حسابي حتى لا تغطي نصوص العناوين */
  body.orig-on-account-page a[href*="wa.me"]:not(#orig-acc-v163-root a),
  body.orig-on-account-page .floating-whatsapp,
  body.orig-on-account-page [class*="whatsapp-float"],
  body.orig-on-account-page [id*="whatsapp"] {
    display: none !important;
  }

  /* 4. وضع الواجهة الرئيسية (Hub) */
  .original-account-page.orig-mode-hub > *:not(#orig-acc-v163-root) {
    display: none !important;
  }
  .original-account-page.orig-mode-hub > #orig-acc-v163-root {
    display: block !important;
  }

  /* 5. وضع النوافذ الفرعية (إعدادات الحساب / عناويني) */
  .original-account-page.orig-mode-sub > #orig-acc-v163-root,
  .original-account-page.orig-mode-sub > [data-orig-sec="legacy-hero"],
  .original-account-page.orig-mode-sub > [data-orig-sec="legacy-links"],
  .original-account-page.orig-mode-sub > [data-orig-sec="profile-readonly"] {
    display: none !important;
  }

  .original-account-page.orig-sub-profile > [data-orig-sec="addresses"] {
    display: none !important;
  }
  .original-account-page.orig-sub-profile > [data-orig-sec="profile-form"] {
    display: block !important;
  }

  .original-account-page.orig-sub-addresses > [data-orig-sec="profile-form"] {
    display: none !important;
  }
  .original-account-page.orig-sub-addresses > [data-orig-sec="addresses"] {
    display: block !important;
  }

  /* حركات الانزلاق السلسة */
  .original-account-page.orig-anim-enter > #orig-subview-sheet-head-v163,
  .original-account-page.orig-anim-enter > [data-orig-sec="profile-form"],
  .original-account-page.orig-anim-enter > [data-orig-sec="addresses"] {
    opacity: 0 !important;
    transform: translate3d(0, 36px, 0) scale(0.98) !important;
  }

  .original-account-page.orig-anim-active > #orig-subview-sheet-head-v163,
  .original-account-page.orig-anim-active > [data-orig-sec="profile-form"],
  .original-account-page.orig-anim-active > [data-orig-sec="addresses"] {
    opacity: 1 !important;
    transform: translate3d(0, 0, 0) scale(1) !important;
    transition: transform 0.32s cubic-bezier(0.22, 1, 0.36, 1), opacity 0.24s ease !important;
  }

  .original-account-page.orig-anim-exit > #orig-subview-sheet-head-v163,
  .original-account-page.orig-anim-exit > [data-orig-sec="profile-form"],
  .original-account-page.orig-anim-exit > [data-orig-sec="addresses"] {
    opacity: 0 !important;
    transform: translate3d(0, 36px, 0) scale(0.98) !important;
    transition: transform 0.2s ease, opacity 0.18s ease !important;
  }

  /* 6. هيدر النافذة الفرعية مع مقبض السحب */
  #orig-subview-sheet-head-v163 {
    display: none;
    background: linear-gradient(135deg, #13462f 0%, #0b2b1d 100%) !important;
    border: 1.5px solid var(--orig-gold) !important;
    border-radius: 20px !important;
    padding: 10px 16px 14px 16px !important;
    margin-bottom: 14px !important;
    box-shadow: 0 8px 20px rgba(11, 43, 29, 0.14) !important;
    touch-action: pan-y !important;
    user-select: none !important;
  }
  .original-account-page.orig-mode-sub > #orig-subview-sheet-head-v163 {
    display: block !important;
  }
  .orig-sheet-pill-v163 {
    width: 42px;
    height: 4px;
    border-radius: 999px;
    background: rgba(216, 180, 84, 0.55);
    margin: 0 auto 10px auto;
  }
  .orig-sheet-toprow-v163 {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }
  .orig-sheet-title-v163 {
    color: #ffffff;
    font-size: 15.5px;
    font-weight: 800;
    margin: 0 0 2px 0;
  }
  .orig-sheet-sub-v163 {
    color: rgba(231, 201, 114, 0.9);
    font-size: 11.5px;
    font-weight: 600;
    margin: 0;
  }
  .orig-sheet-back-btn-v163 {
    background: rgba(216, 180, 84, 0.16);
    border: 1px solid rgba(216, 180, 84, 0.6);
    color: var(--orig-gold-light);
    height: 36px;
    padding: 0 14px;
    border-radius: 12px;
    font-size: 13px;
    font-weight: 800;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
    flex-shrink: 0;
  }

  /* 7. موازنة حقول الإدخال والنماذج ومربع صح الافتراضي */
  .original-account-page [data-orig-sec="profile-form"] svg,
  .original-account-page [data-orig-sec="addresses"] svg {
    width: 18px !important;
    height: 18px !important;
    max-width: 20px !important;
    max-height: 20px !important;
    flex-shrink: 0 !important;
  }

  .orig-vertical-fields-v163 {
    display: flex !important;
    flex-direction: column !important;
    grid-template-columns: 1fr !important;
    gap: 14px !important;
    width: 100% !important;
  }

  .orig-field-unit-v163 {
    display: flex !important;
    flex-direction: column !important;
    gap: 6px !important;
    width: 100% !important;
    margin: 0 !important;
  }

  .orig-label-head-v163 {
    display: flex !important;
    flex-direction: row !important;
    align-items: center !important;
    justify-content: space-between !important;
    flex-wrap: nowrap !important;
    width: 100% !important;
    gap: 8px !important;
    font-size: 13.5px !important;
    font-weight: 800 !important;
    color: #1c2e24 !important;
  }

  .original-account-page input:not([type="checkbox"]):not([type="radio"]),
  .original-account-page select,
  .original-account-page textarea {
    width: 100% !important;
    height: 48px !important;
    min-height: 48px !important;
    padding: 0 16px !important;
    border-radius: 14px !important;
    border: 1.5px solid rgba(216, 180, 84, 0.5) !important;
    background: #fcfbf7 !important;
    color: #132a1f !important;
    font-size: 15px !important;
    font-weight: 700 !important;
    box-sizing: border-box !important;
    margin: 0 !important;
  }
  .original-account-page textarea {
    height: auto !important;
    min-height: 84px !important;
    padding: 12px 16px !important;
  }

  .original-account-page input[type="checkbox"],
  .original-account-page input[type="radio"] {
    width: 20px !important;
    height: 20px !important;
    min-width: 20px !important;
    max-width: 20px !important;
    min-height: 20px !important;
    max-height: 20px !important;
    flex: 0 0 20px !important;
    margin: 0 !important;
    padding: 0 !important;
    accent-color: var(--orig-em-main) !important;
    cursor: pointer !important;
  }

  .orig-default-check-row-v163 {
    display: flex !important;
    flex-direction: row !important;
    align-items: center !important;
    justify-content: flex-start !important;
    gap: 10px !important;
    width: 100% !important;
    min-height: 48px !important;
    padding: 10px 14px !important;
    margin: 6px 0 !important;
    background: #f5f2e8 !important;
    border: 1.5px solid rgba(216, 180, 84, 0.45) !important;
    border-radius: 14px !important;
    box-sizing: border-box !important;
    font-size: 14px !important;
    font-weight: 800 !important;
    color: var(--orig-em-main) !important;
  }

  .orig-btn-row-v163 {
    display: grid !important;
    grid-template-columns: 2fr 1fr !important;
    gap: 10px !important;
    width: 100% !important;
    margin-top: 14px !important;
  }
  .orig-btn-row-v163 > button {
    height: 48px !important;
    border-radius: 14px !important;
    font-size: 14.5px !important;
    font-weight: 800 !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 8px !important;
    margin: 0 !important;
    cursor: pointer !important;
  }
  .orig-btn-primary-v163 {
    background: linear-gradient(135deg, #13462f 0%, #0b2b1d 100%) !important;
    color: #ffffff !important;
    border: 1.5px solid var(--orig-gold) !important;
  }
  .orig-btn-secondary-v163 {
    background: #f2efe4 !important;
    color: #374a3f !important;
    border: 1.5px solid rgba(216, 180, 84, 0.4) !important;
  }

  /* 8. تصميم واجهة حسابي الرئيسية (Hub) */
  #orig-acc-v163-root {
    width: 100%;
    max-width: 540px;
    margin: 0 auto;
  }
  .orig-hero-banner-v163 {
    position: relative;
    background: linear-gradient(135deg, #13462f 0%, #1a5c3e 52%, #0b2b1d 100%);
    border-radius: 22px;
    border: 2px solid var(--orig-gold);
    padding: 20px 18px;
    color: #ffffff;
    box-shadow: 0 10px 26px rgba(11, 43, 29, 0.22);
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
    margin-bottom: 14px;
  }
  .orig-hero-watermark-v163 {
    position: absolute;
    left: -14px;
    bottom: -18px;
    width: 135px !important;
    height: 135px !important;
    opacity: 0.13;
    pointer-events: none;
  }
  .orig-hero-avatar-v163 {
    width: 68px;
    height: 68px;
    border-radius: 50%;
    border: 2.5px solid var(--orig-gold);
    background: radial-gradient(circle at 30% 30%, #1f6b49, #0b2b1d);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .orig-hero-avatar-v163 svg {
    width: 36px !important;
    height: 36px !important;
    fill: #ffffff;
  }
  .orig-hero-info-v163 {
    flex: 1;
    text-align: right;
    z-index: 1;
  }
  .orig-hero-welcome-v163 {
    font-size: 14px;
    color: var(--orig-gold-light);
    font-weight: 600;
    margin: 0 0 2px 0;
  }
  .orig-hero-name-v163 {
    font-size: 21px;
    font-weight: 800;
    color: #ffffff;
    margin: 0 0 6px 0;
  }
  .orig-hero-phone-v163 {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 14.5px;
    font-weight: 700;
    color: #f3efe3;
    direction: ltr;
  }
  .orig-hero-phone-v163 svg {
    width: 15px !important;
    height: 15px !important;
    fill: var(--orig-gold);
  }

  .orig-quick-grid-v163 {
    display: grid !important;
    grid-template-columns: repeat(4, 1fr) !important;
    gap: 9px !important;
    margin-bottom: 14px !important;
  }
  .orig-quick-card-v163 {
    background: #ffffff;
    border: 1.5px solid rgba(216, 180, 84, 0.38);
    border-radius: 18px;
    padding: 13px 6px 11px 6px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 7px;
    box-shadow: 0 4px 14px rgba(19, 70, 47, 0.05);
    cursor: pointer;
  }
  .orig-quick-card-v163 svg {
    width: 26px !important;
    height: 26px !important;
  }
  .orig-quick-label-v163 {
    font-size: 13px;
    font-weight: 800;
    color: var(--orig-em-main);
  }

  .orig-menu-stack-v163 {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-bottom: 14px;
  }
  .orig-menu-item-v163 {
    background: #ffffff;
    border: 1.5px solid rgba(216, 180, 84, 0.32);
    border-radius: 18px;
    padding: 13px 15px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    box-shadow: 0 4px 12px rgba(19, 70, 47, 0.04);
    cursor: pointer;
  }
  .orig-menu-right-v163 {
    display: flex;
    align-items: center;
    gap: 12px;
    flex: 1;
    min-width: 0;
  }
  .orig-menu-icon-v163 {
    width: 38px;
    height: 38px;
    border-radius: 12px;
    background: rgba(19, 70, 47, 0.07);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .orig-menu-icon-v163 svg {
    width: 22px !important;
    height: 22px !important;
  }
  .orig-menu-text-v163 {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    text-align: right;
  }
  .orig-menu-title-v163 {
    font-size: 15.5px;
    font-weight: 800;
    color: #152b20;
  }
  .orig-menu-sub-v163 {
    font-size: 12.5px;
    font-weight: 600;
    color: #5a6b61;
    margin-top: 2px;
  }
  .orig-menu-arrow-v163 {
    width: 20px !important;
    height: 20px !important;
    flex-shrink: 0;
    stroke: #1f3a2c;
  }

  .orig-logout-btn-v163 {
    width: 100%;
    height: 50px;
    background: #ffffff;
    border: 1.5px solid var(--orig-em-main);
    border-radius: 999px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    color: var(--orig-em-main);
    font-size: 16px;
    font-weight: 800;
    cursor: pointer;
  }
  .orig-logout-btn-v163 svg {
    width: 22px !important;
    height: 22px !important;
  }

  .orig-modal-backdrop-v163 {
    position: fixed;
    inset: 0;
    background: rgba(8, 24, 16, 0.62);
    backdrop-filter: blur(5px);
    -webkit-backdrop-filter: blur(5px);
    z-index: 99999;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 18px;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.22s ease;
    direction: rtl;
    font-family: 'Cairo', 'Tajawal', sans-serif;
  }
  .orig-modal-backdrop-v163.open {
    opacity: 1;
    pointer-events: auto;
  }
  .orig-modal-card-v163 {
    width: 100%;
    max-width: 370px;
    background: #ffffff;
    border: 2px solid var(--orig-gold);
    border-radius: 24px;
    padding: 22px 20px 18px 20px;
    text-align: center;
    box-shadow: 0 18px 42px rgba(0, 0, 0, 0.28);
  }
  .orig-modal-emblem-v163 {
    width: 58px;
    height: 58px;
    border-radius: 18px;
    background: linear-gradient(135deg, #13462f, #0b2b1d);
    border: 2px solid var(--orig-gold);
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 12px auto;
    color: var(--orig-gold-light);
    font-size: 24px;
    font-weight: 900;
  }
  .orig-modal-title-v163 {
    font-size: 18px;
    font-weight: 800;
    color: var(--orig-em-main);
    margin: 0 0 8px 0;
  }
  .orig-modal-desc-v163 {
    font-size: 13.5px;
    color: #495a50;
    line-height: 1.6;
    margin: 0 0 16px 0;
    font-weight: 600;
  }
  .orig-modal-actions-v163 {
    display: flex;
    gap: 10px;
  }
  .orig-modal-btn-v163 {
    flex: 1;
    height: 44px;
    border-radius: 13px;
    font-size: 14px;
    font-weight: 800;
    cursor: pointer;
    border: none;
  }
  .orig-modal-btn-v163.confirm {
    background: #b91c1c;
    color: #ffffff;
  }
  .orig-modal-btn-v163.primary {
    background: linear-gradient(135deg, #13462f, #0b2b1d);
    color: var(--orig-gold-light);
    border: 1.5px solid var(--orig-gold);
  }
  .orig-modal-btn-v163.cancel {
    background: #f1efe6;
    color: #2c3e34;
    border: 1px solid rgba(216, 180, 84, 0.4);
  }
</style>

<script>
(function() {
  if (window.__origAccV163Loaded) return;
  window.__origAccV163Loaded = true;

  let currentSubMode = null;

  // إخفاء سطر "جارٍ عرض المزيد من المنتجات..." إذا ظهرت عبارة "وصلت إلى نهاية المنتجات"
  function cleanStuckProductLoader() {
    if (window.location.pathname.includes("/account")) return;
    const bodyTxt = document.body ? (document.body.innerText || "") : "";
    if (!bodyTxt.includes("وصلت إلى نهاية المنتجات")) return;
    document.querySelectorAll("div, p, span").forEach(el => {
      if (el.children.length <= 3 && (el.innerText || "").trim() === "جارٍ عرض المزيد من المنتجات...") {
        el.classList.add("orig-hide-stuck-loader");
      }
    });
  }

  function getCustomerInfo() {
    let name = "أصيل الحبابي";
    let phone = "770731619";
    try {
      const page = document.querySelector(".original-account-page");
      if (page) {
        const inputs = page.querySelectorAll('input:not([type="checkbox"]):not([type="radio"])');
        if (inputs.length >= 2) {
          const v0 = (inputs[0].value || "").trim();
          const v1 = (inputs[1].value || "").trim();
          if (v0 && !/^\d+$/.test(v0)) name = v0;
          if (v1 && /^\d{7,15}$/.test(v1.replace(/\s+/g, ""))) phone = v1.replace(/\s+/g, "");
        }
        const m = (page.innerText || "").match(/7\d{8}/);
        if (m) phone = m[0];
      }
      for (let i = 0; i < localStorage.length; i++) {
        const k = localStorage.key(i);
        const raw = localStorage.getItem(k);
        if (!raw || raw.length > 4000) continue;
        if (raw.includes("77") || raw.includes("name") || raw.includes("phone")) {
          try {
            const obj = JSON.parse(raw);
            if (obj && typeof obj === "object") {
              if (obj.name && typeof obj.name === "string" && obj.name.trim().length > 1) name = obj.name.trim();
              if (obj.customerName && typeof obj.customerName === "string" && obj.customerName.trim().length > 1) name = obj.customerName.trim();
              if (obj.phone && typeof obj.phone === "string" && obj.phone.trim().length >= 7) phone = obj.phone.trim();
              if (obj.customerPhone && typeof obj.customerPhone === "string" && obj.customerPhone.trim().length >= 7) phone = obj.customerPhone.trim();
            }
          } catch (_) {}
        }
      }
    } catch (_) {}
    return { name, phone };
  }

  function safeSetText(id, val) {
    const el = document.getElementById(id);
    if (el && el.textContent !== val) {
      el.textContent = val;
    }
  }

  function refreshHubText() {
    const info = getCustomerInfo();
    safeSetText("orig-hub-name-v163", info.name);
    safeSetText("orig-hub-phone-v163", info.phone);
    safeSetText("orig-row-name-v163", info.name);
    safeSetText("orig-row-phone-v163", "رقم الجوال:  " + info.phone);
  }

  function normalizeFormsAndCards(page) {
    if (!page) return;
    const children = Array.from(page.children);
    let hitAddresses = false;

    children.forEach(ch => {
      if (ch.id === "orig-acc-v163-root" || ch.id === "orig-subview-sheet-head-v163" || ch.classList.contains("page-title-row")) return;
      const txt = (ch.innerText || "").trim();
      if (txt.includes("عناوين التوصيل المحفوظة") || txt.includes("إضافة عنوان")) {
        hitAddresses = true;
      }
      const targetSec = hitAddresses
        ? "addresses"
        : (ch.classList.contains("original-account-card") && (txt.includes("بيانات مكتملة") || txt.includes("تعديل البيانات") || ch.querySelector(".original-account-avatar")))
        ? "legacy-hero"
        : (txt.includes("تحديث البيانات الشخصية") || (ch.querySelector("input") && (txt.includes("الاسم الكامل") || txt.includes("حفظ البيانات"))))
        ? "profile-form"
        : (txt.includes("الاسم الكامل للمستلم") || txt.includes("رقم الجوال المعتمد"))
        ? "profile-readonly"
        : "legacy-links";

      if (ch.getAttribute("data-orig-sec") !== targetSec) {
        ch.setAttribute("data-orig-sec", targetSec);
      }
    });

    const inputs = page.querySelectorAll('[data-orig-sec="profile-form"] input:not([type="checkbox"]):not([type="radio"]), [data-orig-sec="addresses"] input:not([type="checkbox"]):not([type="radio"]), [data-orig-sec="addresses"] select, [data-orig-sec="addresses"] textarea');
    inputs.forEach(inp => {
      if (inp.dataset.origNorm === "1") return;
      inp.dataset.origNorm = "1";
      const unit = inp.closest("label") || inp.parentElement;
      if (unit && unit !== page) {
        unit.classList.add("orig-field-unit-v163");
        const rowParent = unit.parentElement;
        if (rowParent && rowParent !== page) {
          const siblingInputs = rowParent.querySelectorAll('input:not([type="checkbox"]):not([type="radio"]), select, textarea');
          if (siblingInputs.length >= 2) {
            rowParent.classList.add("orig-vertical-fields-v163");
          }
        }
        Array.from(unit.children).forEach(child => {
          if (child !== inp && child.tagName !== "INPUT" && child.tagName !== "SELECT" && child.tagName !== "TEXTAREA") {
            child.classList.add("orig-label-head-v163");
          }
        });
      }
    });

    page.querySelectorAll('input[type="checkbox"], input[type="radio"]').forEach(chk => {
      if (chk.dataset.origNorm === "1") return;
      chk.dataset.origNorm = "1";
      const wrap = chk.closest("label") || chk.parentElement;
      if (wrap && wrap !== page) {
        wrap.classList.add("orig-default-check-row-v163");
      }
    });

    page.querySelectorAll('[data-orig-sec="profile-form"] button, [data-orig-sec="addresses"] button').forEach(btn => {
      if (btn.dataset.origNorm === "1") return;
      btn.dataset.origNorm = "1";
      const t = (btn.innerText || "").trim();
      if (t.includes("حفظ") || t.includes("تأكيد") || t.includes("تحديث")) {
        btn.classList.add("orig-btn-primary-v163");
        const p = btn.parentElement;
        if (p && p.querySelectorAll("button").length === 2) {
          p.classList.add("orig-btn-row-v163");
        }
        btn.addEventListener("click", () => {
          if (currentSubMode === "profile") {
            setTimeout(() => closeSubViewSmoothly(), 200);
          } else {
            setTimeout(() => normalizeFormsAndCards(page), 150);
          }
        });
      } else if (t.includes("إلغاء")) {
        btn.classList.add("orig-btn-secondary-v163");
        btn.addEventListener("click", () => {
          if (currentSubMode === "profile") {
            setTimeout(() => closeSubViewSmoothly(), 120);
          } else {
            setTimeout(() => normalizeFormsAndCards(page), 150);
          }
        });
      } else if (t.includes("إضافة عنوان") || t.includes("تعديل")) {
        btn.addEventListener("click", () => {
          setTimeout(() => normalizeFormsAndCards(page), 120);
        });
      }
    });
  }

  function ensureSubSheetHeader(page) {
    let head = document.getElementById("orig-subview-sheet-head-v163");
    if (!head) {
      head = document.createElement("div");
      head.id = "orig-subview-sheet-head-v163";
      head.innerHTML = `
        <div class="orig-sheet-pill-v163"></div>
        <div class="orig-sheet-toprow-v163">
          <div>
            <h3 class="orig-sheet-title-v163" id="orig-sheet-title-txt-v163">إعدادات الحساب</h3>
            <p class="orig-sheet-sub-v163" id="orig-sheet-sub-txt-v163">اسحب للأسفل أو اضغط رجوع للعودة لحسابك</p>
          </div>
          <button type="button" class="orig-sheet-back-btn-v163" id="orig-sheet-back-btn-v163">
            <span>رجوع</span>
            <span>←</span>
          </button>
        </div>
      `;
      page.prepend(head);

      head.querySelector("#orig-sheet-back-btn-v163").addEventListener("click", () => {
        closeSubViewSmoothly();
      });

      let startY = 0, currentY = 0, dragging = false;
      head.addEventListener("touchstart", (e) => {
        if (!e.touches || !e.touches[0]) return;
        startY = e.touches[0].clientY;
        currentY = 0;
        dragging = true;
      }, { passive: true });

      head.addEventListener("touchmove", (e) => {
        if (!dragging || !e.touches || !e.touches[0]) return;
        const dy = e.touches[0].clientY - startY;
        if (dy > 10) currentY = dy;
      }, { passive: true });

      head.addEventListener("touchend", () => {
        if (dragging && currentY > 55) closeSubViewSmoothly();
        dragging = false;
        currentY = 0;
      }, { passive: true });
    }
    return head;
  }

  function openSubViewSmoothly(mode) {
    const page = document.querySelector(".original-account-page");
    if (!page) return;
    currentSubMode = mode;

    ensureSubSheetHeader(page);
    if (mode === "profile") {
      safeSetText("orig-sheet-title-txt-v163", "إعدادات الحساب والبيانات الشخصية");
      safeSetText("orig-sheet-sub-txt-v163", "تعديل الاسم الكامل ورقم الجوال المعتمد للتوصيل");
      const editBtn = page.querySelector(".original-account-edit-btn");
      if (editBtn) editBtn.click();
    } else {
      safeSetText("orig-sheet-title-txt-v163", "عناويني المحفوظة");
      safeSetText("orig-sheet-sub-txt-v163", "إدارة عناوين التوصيل أو إضافة عنوان جديد");
    }

    setTimeout(() => {
      normalizeFormsAndCards(page);
      page.classList.remove("orig-mode-hub", "orig-sub-profile", "orig-sub-addresses", "orig-anim-active", "orig-anim-exit");
      page.classList.add("orig-mode-sub", mode === "profile" ? "orig-sub-profile" : "orig-sub-addresses", "orig-anim-enter");

      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          normalizeFormsAndCards(page);
          page.classList.remove("orig-anim-enter");
          page.classList.add("orig-anim-active");
          window.scrollTo({ top: 0, behavior: "smooth" });
        });
      });
    }, 80);
  }

  function closeSubViewSmoothly() {
    const page = document.querySelector(".original-account-page");
    if (!page) return;
    page.classList.remove("orig-anim-active");
    page.classList.add("orig-anim-exit");

    setTimeout(() => {
      currentSubMode = null;
      page.classList.remove("orig-mode-sub", "orig-sub-profile", "orig-sub-addresses", "orig-anim-exit", "orig-anim-enter");
      page.classList.add("orig-mode-hub");
      refreshHubText();
      window.scrollTo({ top: 0, behavior: "smooth" });
    }, 200);
  }

  function ensureModals() {
    if (document.getElementById("orig-logout-modal-v163")) return;

    const logoutModal = document.createElement("div");
    logoutModal.id = "orig-logout-modal-v163";
    logoutModal.className = "orig-modal-backdrop-v163";
    logoutModal.innerHTML = `
      <div class="orig-modal-card-v163">
        <div class="orig-modal-emblem-v163">!</div>
        <h3 class="orig-modal-title-v163">تأكيد تسجيل الخروج</h3>
        <p class="orig-modal-desc-v163">هل أنت متأكد من رغبتك في تسجيل الخروج من حسابك في متجر أورجنال؟</p>
        <div class="orig-modal-actions-v163">
          <button type="button" class="orig-modal-btn-v163 confirm" id="orig-confirm-logout-v163">نعم، تسجيل الخروج</button>
          <button type="button" class="orig-modal-btn-v163 cancel" id="orig-cancel-logout-v163">إلغاء</button>
        </div>
      </div>
    `;
    document.body.appendChild(logoutModal);

    logoutModal.addEventListener("click", (e) => {
      if (e.target === logoutModal) logoutModal.classList.remove("open");
    });
    document.getElementById("orig-cancel-logout-v163").addEventListener("click", () => {
      logoutModal.classList.remove("open");
    });
    document.getElementById("orig-confirm-logout-v163").addEventListener("click", () => {
      try {
        const keysToRemove = [];
        for (let i = 0; i < localStorage.length; i++) {
          const k = localStorage.key(i);
          if (k && (k.includes("profile") || k.includes("customer") || k.includes("user") || k.includes("account") || k.includes("auth") || k.includes("phone"))) {
            keysToRemove.push(k);
          }
        }
        keysToRemove.forEach(k => localStorage.removeItem(k));
        sessionStorage.clear();
      } catch (_) {}
      logoutModal.classList.remove("open");
      window.location.href = "/";
    });

    const aboutModal = document.createElement("div");
    aboutModal.id = "orig-about-modal-v163";
    aboutModal.className = "orig-modal-backdrop-v163";
    aboutModal.innerHTML = `
      <div class="orig-modal-card-v163">
        <div class="orig-modal-emblem-v163">O</div>
        <h3 class="orig-modal-title-v163">ORIGINAL – أورجنال</h3>
        <p class="orig-modal-desc-v163">
          متجرك المفضل لتوصيل كافة مقاضي البيت والمواد الغذائية الطازجة في صنعاء بسرعة وعناية فائقة.<br>
          <strong style="color:#13462f;display:inline-block;margin-top:6px;">الإصدار الرسمي • خدمة عملاء: 779542219</strong>
        </p>
        <div class="orig-modal-actions-v163">
          <button type="button" class="orig-modal-btn-v163 primary" id="orig-close-about-v163">إغلاق</button>
        </div>
      </div>
    `;
    document.body.appendChild(aboutModal);

    aboutModal.addEventListener("click", (e) => {
      if (e.target === aboutModal) aboutModal.classList.remove("open");
    });
    document.getElementById("orig-close-about-v163").addEventListener("click", () => {
      aboutModal.classList.remove("open");
    });
  }

  function openNotificationsDrawer() {
    const bell = document.querySelector("#orig-top-bell-btn");
    if (bell) {
      bell.click();
      return;
    }
    const allBtns = Array.from(document.querySelectorAll("header button, header a"));
    const notifBtn = allBtns.find(b => (b.innerHTML || "").includes("M18 8A6 6 0 0 0 6 8") || (b.getAttribute("aria-label") || "").includes("إشعار"));
    if (notifBtn) {
      notifBtn.click();
      return;
    }
    window.location.href = "/orders";
  }

  function runRouteCheck() {
    cleanStuckProductLoader();
    const isAccount = window.location.pathname.includes("/account");
    if (document.body.classList.contains("orig-on-account-page") !== isAccount) {
      document.body.classList.toggle("orig-on-account-page", isAccount);
    }
    if (!isAccount) {
      currentSubMode = null;
      return;
    }

    const page = document.querySelector(".original-account-page");
    if (!page) return;

    ensureModals();
    ensureSubSheetHeader(page);
    normalizeFormsAndCards(page);

    if (!currentSubMode && !page.classList.contains("orig-mode-sub") && !page.classList.contains("orig-mode-hub")) {
      page.classList.add("orig-mode-hub");
    }

    if (document.getElementById("orig-acc-v163-root")) {
      refreshHubText();
      return;
    }

    const info = getCustomerInfo();
    const root = document.createElement("div");
    root.id = "orig-acc-v163-root";
    root.innerHTML = `
      <div class="orig-hero-banner-v163">
        <div class="orig-hero-info-v163">
          <p class="orig-hero-welcome-v163">أهلاً بك</p>
          <h2 class="orig-hero-name-v163" id="orig-hub-name-v163">${info.name}</h2>
          <div class="orig-hero-phone-v163">
            <svg viewBox="0 0 24 24"><path d="M6.62 10.79a15.05 15.05 0 006.59 6.59l2.2-2.2a1 1 0 011.01-.24c1.12.37 2.33.57 3.58.57a1 1 0 011 1V20a1 1 0 01-1 1C10.61 21 3 13.39 3 4a1 1 0 011-1h3.5a1 1 0 011 1c0 1.25.2 2.46.57 3.58a1 1 0 01-.25 1.01l-2.2 2.2z"/></svg>
            <span id="orig-hub-phone-v163">${info.phone}</span>
          </div>
        </div>
        <div class="orig-hero-avatar-v163">
          <svg viewBox="0 0 24 24"><path d="M12 12c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm0 2.5c-3.34 0-10 1.67-10 5v2.5h20v-2.5c0-3.33-6.66-5-10-5z"/></svg>
        </div>
        <svg class="orig-hero-watermark-v163" viewBox="0 0 100 100" fill="none">
          <path d="M10 90 C10 40, 50 10, 90 10 C90 50, 60 90, 10 90 Z" fill="#d8b454"/>
          <path d="M25 75 C25 45, 55 25, 85 25" stroke="#ffffff" stroke-width="3"/>
        </svg>
      </div>

      <div class="orig-quick-grid-v163">
        <button type="button" class="orig-quick-card-v163" data-act="notifications">
          <svg viewBox="0 0 24 24" fill="#13462f"><path d="M12 22c1.1 0 2-.9 2-2h-4a2 2 0 002 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z"/></svg>
          <span class="orig-quick-label-v163">إشعاراتي</span>
        </button>
        <button type="button" class="orig-quick-card-v163" data-act="orders">
          <svg viewBox="0 0 24 24" fill="none" stroke="#13462f" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>
          <span class="orig-quick-label-v163">طلباتي</span>
        </button>
        <button type="button" class="orig-quick-card-v163" data-act="favorites">
          <svg viewBox="0 0 24 24" fill="#13462f"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>
          <span class="orig-quick-label-v163">المفضلة</span>
        </button>
        <button type="button" class="orig-quick-card-v163" data-act="addresses">
          <svg viewBox="0 0 24 24" fill="#13462f"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5a2.5 2.5 0 010-5 2.5 2.5 0 010 5z"/></svg>
          <span class="orig-quick-label-v163">عناويني</span>
        </button>
      </div>

      <div class="orig-menu-stack-v163">
        <div class="orig-menu-item-v163" data-act="notifications">
          <div class="orig-menu-right-v163">
            <div class="orig-menu-icon-v163">
              <svg viewBox="0 0 24 24" fill="#13462f"><path d="M12 22c1.1 0 2-.9 2-2h-4a2 2 0 002 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z"/></svg>
            </div>
            <div class="orig-menu-text-v163">
              <span class="orig-menu-title-v163">إشعارات الطلبات والعروض</span>
            </div>
          </div>
          <svg class="orig-menu-arrow-v163" viewBox="0 0 24 24" fill="none" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
        </div>

        <div class="orig-menu-item-v163" data-act="profile">
          <div class="orig-menu-right-v163">
            <div class="orig-menu-icon-v163">
              <svg viewBox="0 0 24 24" fill="#13462f"><path d="M12 12c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm0 2.5c-3.34 0-10 1.67-10 5v2.5h20v-2.5c0-3.33-6.66-5-10-5z"/></svg>
            </div>
            <div class="orig-menu-text-v163">
              <span class="orig-menu-title-v163" id="orig-row-name-v163">${info.name}</span>
              <span class="orig-menu-sub-v163" id="orig-row-phone-v163">رقم الجوال:  ${info.phone}</span>
            </div>
          </div>
          <svg class="orig-menu-arrow-v163" viewBox="0 0 24 24" fill="none" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
        </div>

        <div class="orig-menu-item-v163" data-act="profile">
          <div class="orig-menu-right-v163">
            <div class="orig-menu-icon-v163">
              <svg viewBox="0 0 24 24" fill="#13462f"><path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58a.49.49 0 00.12-.61l-1.92-3.32a.488.488 0 00-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54a.484.484 0 00-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58a.49.49 0 00-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/></svg>
            </div>
            <div class="orig-menu-text-v163">
              <span class="orig-menu-title-v163">إعدادات الحساب</span>
            </div>
          </div>
          <svg class="orig-menu-arrow-v163" viewBox="0 0 24 24" fill="none" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
        </div>

        <div class="orig-menu-item-v163" data-act="support">
          <div class="orig-menu-right-v163">
            <div class="orig-menu-icon-v163">
              <svg viewBox="0 0 24 24" fill="#13462f"><path d="M12 1a9 9 0 00-9 9v7c0 1.66 1.34 3 3 3h3v-8H5v-2c0-3.87 3.13-7 7-7s7 3.13 7 7v2h-4v8h4v1h-7v2h6c1.66 0 3-1.34 3-3V10a9 9 0 00-9-9z"/></svg>
            </div>
            <div class="orig-menu-text-v163">
              <span class="orig-menu-title-v163">التواصل مع خدمة العملاء</span>
            </div>
          </div>
          <svg class="orig-menu-arrow-v163" viewBox="0 0 24 24" fill="none" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
        </div>

        <div class="orig-menu-item-v163" data-act="about">
          <div class="orig-menu-right-v163">
            <div class="orig-menu-icon-v163">
              <svg viewBox="0 0 24 24" fill="#13462f"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>
            </div>
            <div class="orig-menu-text-v163">
              <span class="orig-menu-title-v163">معلومات التطبيق</span>
            </div>
          </div>
          <svg class="orig-menu-arrow-v163" viewBox="0 0 24 24" fill="none" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
        </div>
      </div>

      <button type="button" class="orig-logout-btn-v163" data-act="logout">
        <svg viewBox="0 0 24 24" fill="none" stroke="#13462f" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
          <polyline points="16 17 21 12 16 7"/>
          <line x1="21" y1="12" x2="9" y2="12"/>
        </svg>
        <span>تسجيل الخروج</span>
      </button>
    `;

    page.prepend(root);

    root.querySelectorAll("[data-act]").forEach(el => {
      el.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        const act = el.getAttribute("data-act");
        if (act === "orders") window.location.href = "/orders";
        else if (act === "favorites") window.location.href = "/favorites";
        else if (act === "notifications") openNotificationsDrawer();
        else if (act === "profile") openSubViewSmoothly("profile");
        else if (act === "addresses") openSubViewSmoothly("addresses");
        else if (act === "support") window.open("https://wa.me/967779542219", "_blank");
        else if (act === "about") {
          const m = document.getElementById("orig-about-modal-v163");
          if (m) m.classList.add("open");
        } else if (act === "logout") {
          const m = document.getElementById("orig-logout-modal-v163");
          if (m) m.classList.add("open");
        }
      });
    });
  }

  window.addEventListener("popstate", () => setTimeout(runRouteCheck, 60));
  document.addEventListener("click", () => setTimeout(runRouteCheck, 90), { passive: true });
  setInterval(runRouteCheck, 800);

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", runRouteCheck);
  } else {
    runRouteCheck();
  }
})();
</script>
<!-- ORIGINAL ACCOUNT ULTRA V163 END -->"""

if "</body>" in html:
    html = html.replace("</body>", block_v163 + "\n</body>", 1)
else:
    html += "\n" + block_v163

with open(index_path, "w", encoding="utf-8") as f:
    f.write(html)

subprocess.run(["git", "add", "client/index.html"], check=True)
subprocess.run(["git", "commit", "-m", "Fix v163: add global scroll-guard & MutationObserver throttle, restore search bar border, hide stuck end-of-products spinner, and zero-lag account UI"], check=False)
subprocess.run(["git", "push", "origin", "main"], check=True)
print("\n✅ تم رفع التحديث الفائق السرعة v163 إلى Render!")
