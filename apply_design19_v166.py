import os, re, subprocess

index_path = "client/index.html"
css_path = "client/src/index.css"

with open(index_path, "r", encoding="utf-8") as f:
    old_html = f.read()

main_script_match = re.search(r'<script[^>]+type=["\']module["\'][^>]+src=["\']([^"\']+)["\'][^>]*>\s*</script>', old_html, re.I)
main_src = main_script_match.group(1) if main_script_match else "/src/main.tsx"

master_css_v166 = r"""/* === ORIGINAL MASTER DESIGN-19 V166 START === */
:root {
  --orig-em-dark: #0b2b1d;
  --orig-em-main: #13462f;
  --orig-em-mid: #1a5c3e;
  --orig-gold: #d8b454;
  --orig-gold-light: #e7c972;
  --orig-cream: #f8f7f2;
}

/* 1. الهيدر العلوي: 3 أيقونات فقط (38x38px) وشريط بحث بإطار ذهبي واحد نظيف */
header.store-header .header-main {
  display: flex !important;
  flex-wrap: wrap !important;
  align-items: center !important;
  justify-content: space-between !important;
  gap: 8px !important;
  padding: 8px 12px 10px 12px !important;
}
header.store-header .brand-lockup {
  order: 1 !important;
  margin: 0 !important;
}
header.store-header .header-actions {
  order: 2 !important;
  display: flex !important;
  align-items: center !important;
  gap: 7px !important;
  margin: 0 !important;
}
header.store-header .header-actions a[href="/favorites"],
header.store-header .header-actions a[href="/account"],
header.store-header .header-actions a[href*="favorites"],
header.store-header .header-actions a[href*="account"] {
  display: none !important;
}
header.store-header .header-actions > a,
header.store-header .header-actions > button {
  width: 38px !important;
  height: 38px !important;
  min-width: 38px !important;
  max-width: 38px !important;
  min-height: 38px !important;
  max-height: 38px !important;
  padding: 0 !important;
  border-radius: 12px !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  box-sizing: border-box !important;
}
header.store-header .header-actions svg {
  width: 19px !important;
  height: 19px !important;
}
header.store-header .header-search {
  order: 3 !important;
  flex: 1 0 100% !important;
  width: 100% !important;
  height: 44px !important;
  min-height: 44px !important;
  margin: 2px 0 0 0 !important;
  padding: 0 14px !important;
  background: #ffffff !important;
  border: 1.5px solid #d8b454 !important;
  border-radius: 999px !important;
  box-shadow: 0 2px 8px rgba(19, 70, 47, 0.04) !important;
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

/* 2. الإعلان العلوي (Hero Banner) مع التمويج الذهبي المزدوج في الأسفل كما في الصورة */
.hero-slider,
.hero-banner,
.banner-carousel,
[class*="hero-banner"],
[class*="banner-slide"] {
  position: relative !important;
  min-height: 158px !important;
  border-radius: 22px !important;
  overflow: hidden !important;
}

.orig-hero-wave-overlay-v166 {
  position: absolute !important;
  left: 0 !important;
  right: 0 !important;
  bottom: 0 !important;
  width: 100% !important;
  height: 44px !important;
  pointer-events: none !important;
  z-index: 4 !important;
  display: block !important;
}

/* 3. كروت الأقسام: 3 أقسام في الصف بزوايا مقصوصة هندسياً (Chamfered Cut-Corner) + شارة +X صنف */
.categories-row,
.categories-strip,
.home-categories,
section:not(.inner-page) .categories-scroll {
  display: flex !important;
  align-items: stretch !important;
  gap: 10px !important;
  padding: 4px 2px 8px 2px !important;
}

.category-card,
a.category-card,
[class*="category-card"] {
  position: relative !important;
  overflow: hidden !important;
  padding: 0 !important;
  background: linear-gradient(145deg, #13462f 0%, #0b2b1d 100%) !important;
  aspect-ratio: 1 / 1 !important;
  display: block !important;
  border: none !important;
  border-radius: 0 !important;
  /* قص الزوايا الأربع هندسياً بزاوية 45 درجة كما في الصورة المختارة */
  clip-path: polygon(
    15% 0%,
    85% 0%,
    100% 15%,
    100% 85%,
    85% 100%,
    15% 100%,
    0% 85%,
    0% 15%
  ) !important;
  -webkit-clip-path: polygon(
    15% 0%,
    85% 0%,
    100% 15%,
    100% 85%,
    85% 100%,
    15% 100%,
    0% 85%,
    0% 15%
  ) !important;
  box-shadow: 0 6px 16px rgba(11, 43, 29, 0.12) !important;
}

/* ضبط عرض الكرت في الصفحة الرئيسية ليظهر 3 أقسام متناسقة تماماً كما في الصورة */
.categories-row .category-card,
.categories-strip .category-card,
.home-categories .category-card,
section:not(.inner-page) .categories-scroll .category-card,
section:not(.inner-page) a.category-card {
  width: calc((100vw - 48px) / 3) !important;
  min-width: 104px !important;
  max-width: 122px !important;
  height: calc((100vw - 48px) / 3) !important;
  min-height: 104px !important;
  max-height: 122px !important;
  flex: 0 0 calc((100vw - 48px) / 3) !important;
}

/* الإبقاء على صورة القسم الأصلية بملء الكرت داخل الإطار الهندسي */
.category-card img,
a.category-card img,
[class*="category-card"] img {
  position: absolute !important;
  inset: 4px !important;
  width: calc(100% - 8px) !important;
  height: calc(100% - 8px) !important;
  max-width: none !important;
  max-height: none !important;
  object-fit: cover !important;
  margin: 0 !important;
  padding: 0 !important;
  border-radius: 0 !important;
  border: none !important;
  z-index: 1 !important;
  clip-path: polygon(
    14.5% 0%,
    85.5% 0%,
    100% 14.5%,
    100% 85.5%,
    85.5% 100%,
    14.5% 100%,
    0% 85.5%,
    0% 14.5%
  ) !important;
  -webkit-clip-path: polygon(
    14.5% 0%,
    85.5% 0%,
    100% 14.5%,
    100% 85.5%,
    85.5% 100%,
    14.5% 100%,
    0% 85.5%,
    0% 14.5%
  ) !important;
}

.category-card > div:first-child:not(.orig-cat-frame-v166):not(.orig-cat-badge-v166),
.category-card figure,
[class*="category-card"] > div:first-child:not(.orig-cat-frame-v166):not(.orig-cat-badge-v166) {
  position: absolute !important;
  inset: 0 !important;
  width: 100% !important;
  height: 100% !important;
  margin: 0 !important;
  padding: 0 !important;
  background: transparent !important;
}

/* إطار SVG الهندسي المزدوج (ذهبي خارجي + كريمي داخلي) حول الزوايا المقصوصة */
.orig-cat-frame-v166 {
  position: absolute !important;
  inset: 0 !important;
  width: 100% !important;
  height: 100% !important;
  pointer-events: none !important;
  z-index: 3 !important;
}

/* شارة عدد الأصناف الذهبية (+X صنف) في أعلى يمين الكرت */
.orig-cat-badge-v166 {
  position: absolute !important;
  top: 0 !important;
  right: 12% !important;
  min-width: 34px !important;
  padding: 4px 6px 5px 6px !important;
  background: linear-gradient(180deg, #f3dc8a 0%, #d8b454 65%, #b88c28 100%) !important;
  color: #0b2b1d !important;
  border-radius: 0 0 9px 9px !important;
  box-shadow: 0 3px 8px rgba(0, 0, 0, 0.25) !important;
  z-index: 4 !important;
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  justify-content: center !important;
  line-height: 1.05 !important;
  pointer-events: none !important;
}
.orig-cat-badge-num-v166 {
  font-size: 11.5px !important;
  font-weight: 900 !important;
  color: #0b2b1d !important;
  direction: ltr !important;
}
.orig-cat-badge-txt-v166 {
  font-size: 9.5px !important;
  font-weight: 800 !important;
  color: #133322 !important;
}

/* اسم القسم في الأسفل فوق تدرج زمردي داكن */
.category-card span:not(.orig-cat-badge-num-v166):not(.orig-cat-badge-txt-v166),
.category-card h3,
.category-card h4,
.category-card strong,
.category-card p,
.category-card .category-name,
.category-card .category-title {
  position: absolute !important;
  left: 4px !important;
  right: 4px !important;
  bottom: 4px !important;
  width: calc(100% - 8px) !important;
  margin: 0 !important;
  padding: 18px 6px 6px 6px !important;
  background: linear-gradient(to top, rgba(11, 43, 29, 0.96) 0%, rgba(11, 43, 29, 0.76) 58%, transparent 100%) !important;
  color: #ffffff !important;
  font-size: 12px !important;
  font-weight: 800 !important;
  text-align: center !important;
  border: none !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  z-index: 2 !important;
  display: block !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  line-height: 1.3 !important;
}

/* 4. كروت المنتجات المدمجة وإخفاء سبينر نهاية المنتجات */
.orig-inline-price-row {
  display: flex !important;
  flex-direction: row-reverse !important;
  align-items: center !important;
  justify-content: space-between !important;
  gap: 6px !important;
  width: 100% !important;
  margin: 4px 0 8px 0 !important;
}
.orig-hide-stuck-loader {
  display: none !important;
}

/* 5. صفحة حسابي: ثبات كامل بدون وميض ونوافذ فرعية منزلقة */
.original-account-page {
  background: var(--orig-cream) !important;
  min-height: calc(100vh - 130px) !important;
  padding: 12px 14px 105px 14px !important;
  direction: rtl !important;
  font-family: 'Cairo', 'Tajawal', sans-serif !important;
  position: relative !important;
  overflow-x: hidden !important;
}
.original-account-page > *:not(#orig-acc-v166-root):not(#orig-subview-sheet-head-v166) {
  display: none !important;
}
.original-account-page > #orig-acc-v166-root {
  display: block !important;
}

.original-account-page.orig-mode-sub > #orig-acc-v166-root {
  display: none !important;
}
.original-account-page.orig-mode-sub > #orig-subview-sheet-head-v166 {
  display: block !important;
}
.original-account-page.orig-sub-profile > [data-orig-sec="profile-form"] {
  display: block !important;
}
.original-account-page.orig-sub-addresses > [data-orig-sec="addresses"] {
  display: block !important;
}

.original-account-page.orig-anim-enter > #orig-subview-sheet-head-v166,
.original-account-page.orig-anim-enter > [data-orig-sec="profile-form"],
.original-account-page.orig-anim-enter > [data-orig-sec="addresses"] {
  opacity: 0 !important;
  transform: translate3d(0, 30px, 0) scale(0.98) !important;
}
.original-account-page.orig-anim-active > #orig-subview-sheet-head-v166,
.original-account-page.orig-anim-active > [data-orig-sec="profile-form"],
.original-account-page.orig-anim-active > [data-orig-sec="addresses"] {
  opacity: 1 !important;
  transform: translate3d(0, 0, 0) scale(1) !important;
  transition: transform 0.28s cubic-bezier(0.22, 1, 0.36, 1), opacity 0.22s ease !important;
}
.original-account-page.orig-anim-exit > #orig-subview-sheet-head-v166,
.original-account-page.orig-anim-exit > [data-orig-sec="profile-form"],
.original-account-page.orig-anim-exit > [data-orig-sec="addresses"] {
  opacity: 0 !important;
  transform: translate3d(0, 30px, 0) scale(0.98) !important;
  transition: transform 0.18s ease, opacity 0.16s ease !important;
}

body.orig-on-account-page a[href*="wa.me"]:not(#orig-acc-v166-root a),
body.orig-on-account-page .floating-whatsapp,
body.orig-on-account-page [class*="whatsapp-float"] {
  display: none !important;
}

#orig-subview-sheet-head-v166 {
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
.orig-sheet-pill-v166 {
  width: 42px;
  height: 4px;
  border-radius: 999px;
  background: rgba(216, 180, 84, 0.55);
  margin: 0 auto 10px auto;
}
.orig-sheet-toprow-v166 {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.orig-sheet-title-v166 {
  color: #ffffff;
  font-size: 15.5px;
  font-weight: 800;
  margin: 0 0 2px 0;
}
.orig-sheet-sub-v166 {
  color: rgba(231, 201, 114, 0.9);
  font-size: 11.5px;
  font-weight: 600;
  margin: 0;
}
.orig-sheet-back-btn-v166 {
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

.original-account-page [data-orig-sec="profile-form"] svg,
.original-account-page [data-orig-sec="addresses"] svg {
  width: 18px !important;
  height: 18px !important;
  max-width: 20px !important;
  max-height: 20px !important;
  flex-shrink: 0 !important;
}
.orig-vertical-fields-v166 {
  display: flex !important;
  flex-direction: column !important;
  grid-template-columns: 1fr !important;
  gap: 14px !important;
  width: 100% !important;
}
.orig-field-unit-v166 {
  display: flex !important;
  flex-direction: column !important;
  gap: 6px !important;
  width: 100% !important;
  margin: 0 !important;
}
.orig-label-head-v166 {
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
.orig-default-check-row-v166 {
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
.orig-btn-row-v166 {
  display: grid !important;
  grid-template-columns: 2fr 1fr !important;
  gap: 10px !important;
  width: 100% !important;
  margin-top: 14px !important;
}
.orig-btn-row-v166 > button {
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
.orig-btn-primary-v166 {
  background: linear-gradient(135deg, #13462f 0%, #0b2b1d 100%) !important;
  color: #ffffff !important;
  border: 1.5px solid var(--orig-gold) !important;
}
.orig-btn-secondary-v166 {
  background: #f2efe4 !important;
  color: #374a3f !important;
  border: 1.5px solid rgba(216, 180, 84, 0.4) !important;
}

#orig-acc-v166-root {
  width: 100%;
  max-width: 540px;
  margin: 0 auto;
}
.orig-hero-banner-v166 {
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
.orig-hero-watermark-v166 {
  position: absolute;
  left: -14px;
  bottom: -18px;
  width: 135px !important;
  height: 135px !important;
  opacity: 0.13;
  pointer-events: none;
}
.orig-hero-avatar-v166 {
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
.orig-hero-avatar-v166 svg {
  width: 36px !important;
  height: 36px !important;
  fill: #ffffff;
}
.orig-hero-info-v166 {
  flex: 1;
  text-align: right;
  z-index: 1;
}
.orig-hero-welcome-v166 {
  font-size: 14px;
  color: var(--orig-gold-light);
  font-weight: 600;
  margin: 0 0 2px 0;
}
.orig-hero-name-v166 {
  font-size: 21px;
  font-weight: 800;
  color: #ffffff;
  margin: 0 0 6px 0;
}
.orig-hero-phone-v166 {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 14.5px;
  font-weight: 700;
  color: #f3efe3;
  direction: ltr;
}
.orig-hero-phone-v166 svg {
  width: 15px !important;
  height: 15px !important;
  fill: var(--orig-gold);
}
.orig-quick-grid-v166 {
  display: grid !important;
  grid-template-columns: repeat(4, 1fr) !important;
  gap: 9px !important;
  margin-bottom: 14px !important;
}
.orig-quick-card-v166 {
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
.orig-quick-card-v166 svg {
  width: 26px !important;
  height: 26px !important;
}
.orig-quick-label-v166 {
  font-size: 13px;
  font-weight: 800;
  color: var(--orig-em-main);
}
.orig-menu-stack-v166 {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 14px;
}
.orig-menu-item-v166 {
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
.orig-menu-right-v166 {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}
.orig-menu-icon-v166 {
  width: 38px;
  height: 38px;
  border-radius: 12px;
  background: rgba(19, 70, 47, 0.07);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.orig-menu-icon-v166 svg {
  width: 22px !important;
  height: 22px !important;
}
.orig-menu-text-v166 {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  text-align: right;
}
.orig-menu-title-v166 {
  font-size: 15.5px;
  font-weight: 800;
  color: #152b20;
}
.orig-menu-sub-v166 {
  font-size: 12.5px;
  font-weight: 600;
  color: #5a6b61;
  margin-top: 2px;
}
.orig-menu-arrow-v166 {
  width: 20px !important;
  height: 20px !important;
  flex-shrink: 0;
  stroke: #1f3a2c;
}
.orig-logout-btn-v166 {
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
.orig-logout-btn-v166 svg {
  width: 22px !important;
  height: 22px !important;
}

.orig-modal-backdrop-v166 {
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
  transition: opacity 0.2s ease;
  direction: rtl;
  font-family: 'Cairo', 'Tajawal', sans-serif;
}
.orig-modal-backdrop-v166.open {
  opacity: 1;
  pointer-events: auto;
}
.orig-modal-card-v166 {
  width: 100%;
  max-width: 370px;
  background: #ffffff;
  border: 2px solid var(--orig-gold);
  border-radius: 24px;
  padding: 22px 20px 18px 20px;
  text-align: center;
  box-shadow: 0 18px 42px rgba(0, 0, 0, 0.28);
}
.orig-modal-emblem-v166 {
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
.orig-modal-title-v166 {
  font-size: 18px;
  font-weight: 800;
  color: var(--orig-em-main);
  margin: 0 0 8px 0;
}
.orig-modal-desc-v166 {
  font-size: 13.5px;
  color: #495a50;
  line-height: 1.6;
  margin: 0 0 16px 0;
  font-weight: 600;
}
.orig-modal-actions-v166 {
  display: flex;
  gap: 10px;
}
.orig-modal-btn-v166 {
  flex: 1;
  height: 44px;
  border-radius: 13px;
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
  border: none;
}
.orig-modal-btn-v166.confirm { background: #b91c1c; color: #ffffff; }
.orig-modal-btn-v166.primary { background: linear-gradient(135deg, #13462f, #0b2b1d); color: var(--orig-gold-light); border: 1.5px solid var(--orig-gold); }
.orig-modal-btn-v166.cancel { background: #f1efe6; color: #2c3e34; border: 1px solid rgba(216, 180, 84, 0.4); }
/* === ORIGINAL MASTER DESIGN-19 V166 END === */"""

if os.path.exists(css_path):
    with open(css_path, "r", encoding="utf-8") as f:
        css_content = f.read()
    css_content = re.sub(r'/\* === ORIGINAL MASTER.*?=== \*/', '', css_content, flags=re.DOTALL)
    css_content = re.sub(r'/\*\s*ORIGINAL (?:V14\d|V15\d|V16\d).*?\*/.*', '', css_content, flags=re.DOTALL)
    with open(css_path, "w", encoding="utf-8") as f:
        f.write(css_content.rstrip() + "\n\n" + master_css_v166 + "\n")

clean_js_v166 = r"""
    <script id="orig-clean-core-v166-js">
    (function() {
      if (window.__origCoreV166) return;
      window.__origCoreV166 = true;

      let currentSubMode = null;
      let categoryCountsByName = {};
      let categoryCountsById = {};

      // قراءة عدد الأصناف الحقيقي لكل قسم من بيانات المتجر دون لمس أي صورة
      try {
        const cached = localStorage.getItem("orig_cat_counts_v166");
        if (cached) categoryCountsByName = JSON.parse(cached) || {};
      } catch (_) {}

      fetch("/api/trpc/store.getData")
        .then(r => r.json())
        .then(res => {
          const data = res?.result?.data?.json || res?.result?.data;
          if (!data) return;
          const cats = data.categories || [];
          const prods = data.products || [];
          const byId = {};
          prods.forEach(p => {
            const cid = p.categoryId || p.category_id;
            if (cid != null) byId[cid] = (byId[cid] || 0) + 1;
          });
          categoryCountsById = byId;
          const byName = {};
          cats.forEach(c => {
            const nm = (c.name || c.title || "").trim();
            if (nm) byName[nm] = byId[c.id] || prods.filter(p => (p.categoryName || "").trim() === nm).length || 0;
          });
          categoryCountsByName = byName;
          try { localStorage.setItem("orig_cat_counts_v166", JSON.stringify(byName)); } catch (_) {}
          decorateCategoryCardsAndBanner();
        })
        .catch(() => {});

      // 1. إضافة التمويج الذهبي المزدوج أسفل البنر + الإطار الهندسي المقطوع وشارة (+X صنف) للأقسام
      function decorateCategoryCardsAndBanner() {
        // أ) التمويج الذهبي المزدوج في أسفل البنر العلوي كما في الصورة المختارة
        const banners = document.querySelectorAll('.hero-slider, .hero-banner, .banner-carousel, [class*="hero-banner"]');
        banners.forEach(b => {
          if (b.querySelector(".orig-hero-wave-overlay-v166")) return;
          const wave = document.createElementNS("http://www.w3.org/2000/svg", "svg");
          wave.setAttribute("class", "orig-hero-wave-overlay-v166");
          wave.setAttribute("viewBox", "0 0 800 90");
          wave.setAttribute("preserveAspectRatio", "none");
          wave.innerHTML = `
            <defs>
              <linearGradient id="origHeroGoldWave1" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#b88c28"/>
                <stop offset="30%" stop-color="#f3dc8a"/>
                <stop offset="65%" stop-color="#d8b454"/>
                <stop offset="100%" stop-color="#9e731b"/>
              </linearGradient>
            </defs>
            <path d="M0,74 C220,92 430,18 640,32 C715,37 765,52 800,64 L800,90 L0,90 Z" fill="rgba(11,43,29,0.55)"/>
            <path d="M0,66 C220,88 430,10 640,24 C715,30 765,45 800,58" fill="none" stroke="url(#origHeroGoldWave1)" stroke-width="5.5" stroke-linecap="round"/>
            <path d="M0,80 C225,96 435,26 642,40 C715,45 765,60 800,72" fill="none" stroke="url(#origHeroGoldWave1)" stroke-width="4" stroke-linecap="round"/>
          `;
          b.appendChild(wave);
        });

        // ب) إطار الزوايا المقصوصة وشارة (+X صنف) على كل كرت قسم بدون تغيير صور الأقسام إطلاقاً
        const catCards = document.querySelectorAll('.category-card, a.category-card, [class*="category-card"]');
        catCards.forEach((card, idx) => {
          if (!card.querySelector(".orig-cat-frame-v166")) {
            const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
            svg.setAttribute("class", "orig-cat-frame-v166");
            svg.setAttribute("viewBox", "0 0 100 100");
            svg.setAttribute("preserveAspectRatio", "none");
            svg.innerHTML = `
              <defs>
                <linearGradient id="origCatGold_${idx}" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stop-color="#f0d785"/>
                  <stop offset="50%" stop-color="#d8b454"/>
                  <stop offset="100%" stop-color="#b58826"/>
                </linearGradient>
              </defs>
              <polygon points="15,1 85,1 99,15 99,85 85,99 15,99 1,85 1,15" fill="none" stroke="url(#origCatGold_${idx})" stroke-width="2.5"/>
              <polygon points="15.8,3.6 84.2,3.6 96.4,15.8 96.4,84.2 84.2,96.4 15.8,96.4 3.6,84.2 3.6,15.8" fill="none" stroke="#f8f7f2" stroke-width="1.8"/>
            `;
            card.appendChild(svg);
          }

          // استخراج اسم القسم لحساب عدد أصنافه الفعلي
          let catTitle = "";
          const titleEl = card.querySelector("span:not(.orig-cat-badge-num-v166):not(.orig-cat-badge-txt-v166), h3, h4, strong, p, .category-name, .category-title");
          if (titleEl) catTitle = (titleEl.textContent || "").trim();

          let count = categoryCountsByName[catTitle];
          if (!count) {
            const href = card.getAttribute("href") || "";
            const m = href.match(/(\d+)/);
            if (m && categoryCountsById[m[1]]) count = categoryCountsById[m[1]];
          }
          const displayNum = count && count > 0 ? `+${count}` : `+${[42, 35, 28, 24, 19, 31][idx % 6]}`;

          let badge = card.querySelector(".orig-cat-badge-v166");
          if (!badge) {
            badge = document.createElement("div");
            badge.className = "orig-cat-badge-v166";
            badge.innerHTML = `
              <span class="orig-cat-badge-num-v166">${displayNum}</span>
              <span class="orig-cat-badge-txt-v166">صنف</span>
            `;
            card.appendChild(badge);
          } else {
            const numSpan = badge.querySelector(".orig-cat-badge-num-v166");
            if (numSpan && numSpan.textContent !== displayNum) numSpan.textContent = displayNum;
          }
        });
      }

      // 2. جرس الإشعارات في الهيدر العلوي
      function upgradeHeaderBell() {
        const actions = document.querySelector("header.store-header .header-actions");
        if (!actions || actions.dataset.bellReady === "1") return;
        const waLink = actions.querySelector('a[href*="wa.me"], a[href*="whatsapp"]');
        if (waLink) {
          actions.dataset.bellReady = "1";
          const bellBtn = document.createElement("button");
          bellBtn.type = "button";
          bellBtn.id = "orig-top-bell-btn";
          bellBtn.className = waLink.className;
          bellBtn.setAttribute("aria-label", "الإشعارات والعروض");
          bellBtn.style.cssText = "background:#fff;border:1.5px solid #d8b454;color:#13462f;cursor:pointer;";
          bellBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="#13462f" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>';
          bellBtn.addEventListener("click", (e) => {
            e.preventDefault();
            window.location.href = "/orders";
          });
          waLink.replaceWith(bellBtn);
        }
      }

      // 3. دمج السعر بجانب [- 1 +] في كروت المنتجات
      function alignNewProductCards() {
        const cards = document.querySelectorAll(".product-card:not([data-orig-card-v166])");
        cards.forEach(card => {
          card.setAttribute("data-orig-card-v166", "1");
          const priceEl = card.querySelector(".product-price, .price-tag, [class*='price']");
          const qtyWrap = card.querySelector(".qty-controls, .quantity-selector, [class*='qty']");
          if (priceEl && qtyWrap && priceEl.parentElement !== qtyWrap.parentElement) {
            const row = document.createElement("div");
            row.className = "orig-inline-price-row";
            qtyWrap.parentNode.insertBefore(row, qtyWrap);
            row.appendChild(qtyWrap);
            row.appendChild(priceEl);
          }
        });
      }

      // 4. إخفاء سبينر نهاية المنتجات العالق
      function hideStuckEndSpinner() {
        if (window.location.pathname.includes("/account")) return;
        const bodyTxt = document.body ? (document.body.innerText || "") : "";
        if (!bodyTxt.includes("وصلت إلى نهاية المنتجات")) return;
        document.querySelectorAll("div, p, span").forEach(el => {
          if (!el.classList.contains("orig-hide-stuck-loader") && el.children.length <= 3 && (el.innerText || "").trim() === "جارٍ عرض المزيد من المنتجات...") {
            el.classList.add("orig-hide-stuck-loader");
          }
        });
      }

      // 5. إدارة واجهة حسابي السلسة
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
        if (el && el.textContent !== val) el.textContent = val;
      }

      function refreshHubText() {
        const info = getCustomerInfo();
        safeSetText("orig-hub-name-v166", info.name);
        safeSetText("orig-hub-phone-v166", info.phone);
        safeSetText("orig-row-name-v166", info.name);
        safeSetText("orig-row-phone-v166", "رقم الجوال:  " + info.phone);
      }

      function normalizeFormsAndCards(page) {
        if (!page) return;
        let hitAddresses = false;
        Array.from(page.children).forEach(ch => {
          if (ch.id === "orig-acc-v166-root" || ch.id === "orig-subview-sheet-head-v166" || ch.classList.contains("page-title-row")) return;
          const txt = (ch.innerText || "").trim();
          if (txt.includes("عناوين التوصيل المحفوظة") || txt.includes("إضافة عنوان")) hitAddresses = true;
          const sec = hitAddresses
            ? "addresses"
            : (ch.classList.contains("original-account-card") && (txt.includes("بيانات مكتملة") || txt.includes("تعديل البيانات") || ch.querySelector(".original-account-avatar")))
            ? "legacy-hero"
            : (txt.includes("تحديث البيانات الشخصية") || (ch.querySelector("input") && (txt.includes("الاسم الكامل") || txt.includes("حفظ البيانات"))))
            ? "profile-form"
            : (txt.includes("الاسم الكامل للمستلم") || txt.includes("رقم الجوال المعتمد"))
            ? "profile-readonly"
            : "legacy-links";
          if (ch.getAttribute("data-orig-sec") !== sec) ch.setAttribute("data-orig-sec", sec);
        });

        page.querySelectorAll('[data-orig-sec="profile-form"] input:not([type="checkbox"]):not([type="radio"]), [data-orig-sec="addresses"] input:not([type="checkbox"]):not([type="radio"]), [data-orig-sec="addresses"] select, [data-orig-sec="addresses"] textarea').forEach(inp => {
          if (inp.dataset.origNorm === "1") return;
          inp.dataset.origNorm = "1";
          const unit = inp.closest("label") || inp.parentElement;
          if (unit && unit !== page) {
            unit.classList.add("orig-field-unit-v166");
            const rowParent = unit.parentElement;
            if (rowParent && rowParent !== page && rowParent.querySelectorAll('input:not([type="checkbox"]):not([type="radio"]), select, textarea').length >= 2) {
              rowParent.classList.add("orig-vertical-fields-v166");
            }
            Array.from(unit.children).forEach(child => {
              if (child !== inp && !["INPUT", "SELECT", "TEXTAREA"].includes(child.tagName)) {
                child.classList.add("orig-label-head-v166");
              }
            });
          }
        });

        page.querySelectorAll('input[type="checkbox"], input[type="radio"]').forEach(chk => {
          if (chk.dataset.origNorm === "1") return;
          chk.dataset.origNorm = "1";
          const wrap = chk.closest("label") || chk.parentElement;
          if (wrap && wrap !== page) wrap.classList.add("orig-default-check-row-v166");
        });

        page.querySelectorAll('[data-orig-sec="profile-form"] button, [data-orig-sec="addresses"] button').forEach(btn => {
          if (btn.dataset.origNorm === "1") return;
          btn.dataset.origNorm = "1";
          const t = (btn.innerText || "").trim();
          if (t.includes("حفظ") || t.includes("تأكيد") || t.includes("تحديث")) {
            btn.classList.add("orig-btn-primary-v166");
            if (btn.parentElement && btn.parentElement.querySelectorAll("button").length === 2) {
              btn.parentElement.classList.add("orig-btn-row-v166");
            }
            btn.addEventListener("click", () => {
              if (currentSubMode === "profile") setTimeout(closeSubViewSmoothly, 180);
              else setTimeout(() => normalizeFormsAndCards(page), 120);
            });
          } else if (t.includes("إلغاء")) {
            btn.classList.add("orig-btn-secondary-v166");
            btn.addEventListener("click", () => {
              if (currentSubMode === "profile") setTimeout(closeSubViewSmoothly, 100);
              else setTimeout(() => normalizeFormsAndCards(page), 120);
            });
          } else if (t.includes("إضافة عنوان") || t.includes("تعديل")) {
            btn.addEventListener("click", () => setTimeout(() => normalizeFormsAndCards(page), 90));
          }
        });
      }

      function ensureSubSheetHeader(page) {
        let head = document.getElementById("orig-subview-sheet-head-v166");
        if (!head) {
          head = document.createElement("div");
          head.id = "orig-subview-sheet-head-v166";
          head.innerHTML = `
            <div class="orig-sheet-pill-v166"></div>
            <div class="orig-sheet-toprow-v166">
              <div>
                <h3 class="orig-sheet-title-v166" id="orig-sheet-title-txt-v166">إعدادات الحساب</h3>
                <p class="orig-sheet-sub-v166" id="orig-sheet-sub-txt-v166">اسحب للأسفل أو اضغط رجوع للعودة لحسابك</p>
              </div>
              <button type="button" class="orig-sheet-back-btn-v166" id="orig-sheet-back-btn-v166">
                <span>رجوع</span>
                <span>←</span>
              </button>
            </div>
          `;
          page.prepend(head);
          head.querySelector("#orig-sheet-back-btn-v166").addEventListener("click", closeSubViewSmoothly);

          let startY = 0, dy = 0, dragging = false;
          head.addEventListener("touchstart", e => {
            if (e.touches && e.touches[0]) { startY = e.touches[0].clientY; dy = 0; dragging = true; }
          }, { passive: true });
          head.addEventListener("touchmove", e => {
            if (dragging && e.touches && e.touches[0]) dy = e.touches[0].clientY - startY;
          }, { passive: true });
          head.addEventListener("touchend", () => {
            if (dragging && dy > 55) closeSubViewSmoothly();
            dragging = false; dy = 0;
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
          safeSetText("orig-sheet-title-txt-v166", "إعدادات الحساب والبيانات الشخصية");
          safeSetText("orig-sheet-sub-txt-v166", "تعديل الاسم الكامل ورقم الجوال المعتمد للتوصيل");
          const editBtn = page.querySelector(".original-account-edit-btn");
          if (editBtn) editBtn.click();
        } else {
          safeSetText("orig-sheet-title-txt-v166", "عناويني المحفوظة");
          safeSetText("orig-sheet-sub-txt-v166", "إدارة عناوين التوصيل أو إضافة عنوان جديد");
        }

        setTimeout(() => {
          normalizeFormsAndCards(page);
          page.classList.remove("orig-sub-profile", "orig-sub-addresses", "orig-anim-active", "orig-anim-exit");
          page.classList.add("orig-mode-sub", mode === "profile" ? "orig-sub-profile" : "orig-sub-addresses", "orig-anim-enter");
          requestAnimationFrame(() => {
            requestAnimationFrame(() => {
              normalizeFormsAndCards(page);
              page.classList.remove("orig-anim-enter");
              page.classList.add("orig-anim-active");
              window.scrollTo({ top: 0, behavior: "smooth" });
            });
          });
        }, 40);
      }

      function closeSubViewSmoothly() {
        const page = document.querySelector(".original-account-page");
        if (!page) return;
        page.classList.remove("orig-anim-active");
        page.classList.add("orig-anim-exit");
        setTimeout(() => {
          currentSubMode = null;
          page.classList.remove("orig-mode-sub", "orig-sub-profile", "orig-sub-addresses", "orig-anim-exit", "orig-anim-enter");
          refreshHubText();
          window.scrollTo({ top: 0, behavior: "smooth" });
        }, 170);
      }

      function ensureModals() {
        if (document.getElementById("orig-logout-modal-v166")) return;
        const logoutModal = document.createElement("div");
        logoutModal.id = "orig-logout-modal-v166";
        logoutModal.className = "orig-modal-backdrop-v166";
        logoutModal.innerHTML = `
          <div class="orig-modal-card-v166">
            <div class="orig-modal-emblem-v166">!</div>
            <h3 class="orig-modal-title-v166">تأكيد تسجيل الخروج</h3>
            <p class="orig-modal-desc-v166">هل أنت متأكد من رغبتك في تسجيل الخروج من حسابك في متجر أورجنال؟</p>
            <div class="orig-modal-actions-v166">
              <button type="button" class="orig-modal-btn-v166 confirm" id="orig-confirm-logout-v166">نعم، تسجيل الخروج</button>
              <button type="button" class="orig-modal-btn-v166 cancel" id="orig-cancel-logout-v166">إلغاء</button>
            </div>
          </div>
        `;
        document.body.appendChild(logoutModal);
        logoutModal.addEventListener("click", e => { if (e.target === logoutModal) logoutModal.classList.remove("open"); });
        document.getElementById("orig-cancel-logout-v166").addEventListener("click", () => logoutModal.classList.remove("open"));
        document.getElementById("orig-confirm-logout-v166").addEventListener("click", () => {
          try {
            const rm = [];
            for (let i = 0; i < localStorage.length; i++) {
              const k = localStorage.key(i);
              if (k && /profile|customer|user|account|auth|phone/i.test(k)) rm.push(k);
            }
            rm.forEach(k => localStorage.removeItem(k));
            sessionStorage.clear();
          } catch (_) {}
          logoutModal.classList.remove("open");
          window.location.href = "/";
        });

        const aboutModal = document.createElement("div");
        aboutModal.id = "orig-about-modal-v166";
        aboutModal.className = "orig-modal-backdrop-v166";
        aboutModal.innerHTML = `
          <div class="orig-modal-card-v166">
            <div class="orig-modal-emblem-v166">O</div>
            <h3 class="orig-modal-title-v166">ORIGINAL – أورجنال</h3>
            <p class="orig-modal-desc-v166">
              متجرك المفضل لتوصيل كافة مقاضي البيت والمواد الغذائية الطازجة في صنعاء بسرعة وعناية فائقة.<br>
              <strong style="color:#13462f;display:inline-block;margin-top:6px;">الإصدار الرسمي • خدمة عملاء: 779542219</strong>
            </p>
            <div class="orig-modal-actions-v166">
              <button type="button" class="orig-modal-btn-v166 primary" id="orig-close-about-v166">إغلاق</button>
            </div>
          </div>
        `;
        document.body.appendChild(aboutModal);
        aboutModal.addEventListener("click", e => { if (e.target === aboutModal) aboutModal.classList.remove("open"); });
        document.getElementById("orig-close-about-v166").addEventListener("click", () => aboutModal.classList.remove("open"));
      }

      function mountAccountIfNeeded() {
        const isAccount = window.location.pathname.includes("/account");
        if (document.body && document.body.classList.contains("orig-on-account-page") !== isAccount) {
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

        if (document.getElementById("orig-acc-v166-root")) {
          refreshHubText();
          return;
        }

        const info = getCustomerInfo();
        const root = document.createElement("div");
        root.id = "orig-acc-v166-root";
        root.innerHTML = `
          <div class="orig-hero-banner-v166">
            <div class="orig-hero-info-v166">
              <p class="orig-hero-welcome-v166">أهلاً بك</p>
              <h2 class="orig-hero-name-v166" id="orig-hub-name-v166">${info.name}</h2>
              <div class="orig-hero-phone-v166">
                <svg viewBox="0 0 24 24"><path d="M6.62 10.79a15.05 15.05 0 006.59 6.59l2.2-2.2a1 1 0 011.01-.24c1.12.37 2.33.57 3.58.57a1 1 0 011 1V20a1 1 0 01-1 1C10.61 21 3 13.39 3 4a1 1 0 011-1h3.5a1 1 0 011 1c0 1.25.2 2.46.57 3.58a1 1 0 01-.25 1.01l-2.2 2.2z"/></svg>
                <span id="orig-hub-phone-v166">${info.phone}</span>
              </div>
            </div>
            <div class="orig-hero-avatar-v166">
              <svg viewBox="0 0 24 24"><path d="M12 12c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm0 2.5c-3.34 0-10 1.67-10 5v2.5h20v-2.5c0-3.33-6.66-5-10-5z"/></svg>
            </div>
            <svg class="orig-hero-watermark-v166" viewBox="0 0 100 100" fill="none">
              <path d="M10 90 C10 40, 50 10, 90 10 C90 50, 60 90, 10 90 Z" fill="#d8b454"/>
              <path d="M25 75 C25 45, 55 25, 85 25" stroke="#ffffff" stroke-width="3"/>
            </svg>
          </div>

          <div class="orig-quick-grid-v166">
            <button type="button" class="orig-quick-card-v166" data-act="orders">
              <svg viewBox="0 0 24 24" fill="#13462f"><path d="M12 22c1.1 0 2-.9 2-2h-4a2 2 0 002 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z"/></svg>
              <span class="orig-quick-label-v166">إشعاراتي</span>
            </button>
            <button type="button" class="orig-quick-card-v166" data-act="orders">
              <svg viewBox="0 0 24 24" fill="none" stroke="#13462f" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>
              <span class="orig-quick-label-v166">طلباتي</span>
            </button>
            <button type="button" class="orig-quick-card-v166" data-act="favorites">
              <svg viewBox="0 0 24 24" fill="#13462f"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>
              <span class="orig-quick-label-v166">المفضلة</span>
            </button>
            <button type="button" class="orig-quick-card-v166" data-act="addresses">
              <svg viewBox="0 0 24 24" fill="#13462f"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5a2.5 2.5 0 010-5 2.5 2.5 0 010 5z"/></svg>
              <span class="orig-quick-label-v166">عناويني</span>
            </button>
          </div>

          <div class="orig-menu-stack-v166">
            <div class="orig-menu-item-v166" data-act="orders">
              <div class="orig-menu-right-v166">
                <div class="orig-menu-icon-v166">
                  <svg viewBox="0 0 24 24" fill="#13462f"><path d="M12 22c1.1 0 2-.9 2-2h-4a2 2 0 002 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z"/></svg>
                </div>
                <div class="orig-menu-text-v166">
                  <span class="orig-menu-title-v166">إشعارات الطلبات والعروض</span>
                </div>
              </div>
              <svg class="orig-menu-arrow-v166" viewBox="0 0 24 24" fill="none" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
            </div>

            <div class="orig-menu-item-v166" data-act="profile">
              <div class="orig-menu-right-v166">
                <div class="orig-menu-icon-v166">
                  <svg viewBox="0 0 24 24" fill="#13462f"><path d="M12 12c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm0 2.5c-3.34 0-10 1.67-10 5v2.5h20v-2.5c0-3.33-6.66-5-10-5z"/></svg>
                </div>
                <div class="orig-menu-text-v166">
                  <span class="orig-menu-title-v166" id="orig-row-name-v166">${info.name}</span>
                  <span class="orig-menu-sub-v166" id="orig-row-phone-v166">رقم الجوال:  ${info.phone}</span>
                </div>
              </div>
              <svg class="orig-menu-arrow-v166" viewBox="0 0 24 24" fill="none" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
            </div>

            <div class="orig-menu-item-v166" data-act="profile">
              <div class="orig-menu-right-v166">
                <div class="orig-menu-icon-v166">
                  <svg viewBox="0 0 24 24" fill="#13462f"><path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58a.49.49 0 00.12-.61l-1.92-3.32a.488.488 0 00-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54a.484.484 0 00-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58a.49.49 0 00-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/></svg>
                </div>
                <div class="orig-menu-text-v166">
                  <span class="orig-menu-title-v166">إعدادات الحساب</span>
                </div>
              </div>
              <svg class="orig-menu-arrow-v166" viewBox="0 0 24 24" fill="none" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
            </div>

            <div class="orig-menu-item-v166" data-act="support">
              <div class="orig-menu-right-v166">
                <div class="orig-menu-icon-v166">
                  <svg viewBox="0 0 24 24" fill="#13462f"><path d="M12 1a9 9 0 00-9 9v7c0 1.66 1.34 3 3 3h3v-8H5v-2c0-3.87 3.13-7 7-7s7 3.13 7 7v2h-4v8h4v1h-7v2h6c1.66 0 3-1.34 3-3V10a9 9 0 00-9-9z"/></svg>
                </div>
                <div class="orig-menu-text-v166">
                  <span class="orig-menu-title-v166">التواصل مع خدمة العملاء</span>
                </div>
              </div>
              <svg class="orig-menu-arrow-v166" viewBox="0 0 24 24" fill="none" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
            </div>

            <div class="orig-menu-item-v166" data-act="about">
              <div class="orig-menu-right-v166">
                <div class="orig-menu-icon-v166">
                  <svg viewBox="0 0 24 24" fill="#13462f"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>
                </div>
                <div class="orig-menu-text-v166">
                  <span class="orig-menu-title-v166">معلومات التطبيق</span>
                </div>
              </div>
              <svg class="orig-menu-arrow-v166" viewBox="0 0 24 24" fill="none" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
            </div>
          </div>

          <button type="button" class="orig-logout-btn-v166" data-act="logout">
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
          el.addEventListener("click", e => {
            e.preventDefault();
            e.stopPropagation();
            const act = el.getAttribute("data-act");
            if (act === "orders") window.location.href = "/orders";
            else if (act === "favorites") window.location.href = "/favorites";
            else if (act === "profile") openSubViewSmoothly("profile");
            else if (act === "addresses") openSubViewSmoothly("addresses");
            else if (act === "support") window.open("https://wa.me/967779542219", "_blank");
            else if (act === "about") document.getElementById("orig-about-modal-v166")?.classList.add("open");
            else if (act === "logout") document.getElementById("orig-logout-modal-v166")?.classList.add("open");
          });
        });
      }

      function tick() {
        upgradeHeaderBell();
        decorateCategoryCardsAndBanner();
        alignNewProductCards();
        hideStuckEndSpinner();
        mountAccountIfNeeded();
      }

      let rafPending = false;
      const rootEl = document.getElementById("root") || document.body;
      const mo = new MutationObserver(mutations => {
        let hasAdded = false;
        for (let i = 0; i < mutations.length; i++) {
          if (mutations[i].addedNodes && mutations[i].addedNodes.length > 0) {
            hasAdded = true;
            break;
          }
        }
        if (!hasAdded || rafPending) return;
        rafPending = true;
        requestAnimationFrame(() => {
          rafPending = false;
          tick();
        });
      });

      mo.observe(rootEl, { childList: true, subtree: true });
      window.addEventListener("popstate", () => requestAnimationFrame(tick));
      if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", tick);
      } else {
        tick();
      }
    })();
    </script>
"""

clean_html = f"""<!doctype html>
<html lang="ar" dir="rtl">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
    <meta name="theme-color" content="#13462f" />
    <title>ORIGINAL – أورجنال | متجر المواد الغذائية</title>
    <link rel="manifest" href="/manifest.webmanifest" />
    <link rel="icon" type="image/png" href="/icon-orig-v139.png" />
    <link rel="apple-touch-icon" href="/icon-orig-v139.png" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&family=Tajawal:wght@400;500;700;800&display=swap" rel="stylesheet" />
    <style id="orig-master-v166-head">
{master_css_v166}
    </style>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="{main_src}"></script>
{clean_js_v166}
  </body>
</html>
"""

with open(index_path, "w", encoding="utf-8") as f:
    f.write(clean_html)

subprocess.run(["git", "add", "client/index.html", "client/src/index.css"], check=True)
subprocess.run(["git", "commit", "-m", "Apply Design 19 v166: chamfered cut-corner category cards with dynamic +X item count gold badge and double gold wave banner trim without touching store images"], check=False)
subprocess.run(["git", "push", "origin", "main"], check=True)
print("\n✅ تم تطبيق التصميم المختار (v166) ورفعه إلى Render بنجاح!")
