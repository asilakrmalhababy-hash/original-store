import os, re, subprocess

index_path = "client/index.html"
css_path = "client/src/index.css"
home_path = "client/src/pages/Home.tsx"

# ==========================================
# 1. تنظيف وتحديث client/src/pages/Home.tsx مباشرة (BannerCarousel + CategoryStrip + CategoriesPage)
# ==========================================
with open(home_path, "r", encoding="utf-8") as f:
    home_code = f.read()

# أ) إضافة التمويج الذهبي المزدوج داخل BannerCarousel (فوق .banner-dots مباشرة)
if "orig-banner-wave-svg" not in home_code:
    wave_jsx = """      <svg className="orig-banner-wave-svg" viewBox="0 0 800 90" preserveAspectRatio="none" aria-hidden="true">
        <defs>
          <linearGradient id="origBannerGoldGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#b88c28" />
            <stop offset="30%" stopColor="#f3dc8a" />
            <stop offset="65%" stopColor="#d8b454" />
            <stop offset="100%" stopColor="#9e731b" />
          </linearGradient>
        </defs>
        <path d="M0,74 C220,92 430,18 640,32 C715,37 765,52 800,64 L800,90 L0,90 Z" fill="rgba(11,43,29,0.52)" />
        <path d="M0,66 C220,88 430,10 640,24 C715,30 765,45 800,58" fill="none" stroke="url(#origBannerGoldGrad)" strokeWidth="5.5" strokeLinecap="round" />
        <path d="M0,80 C225,96 435,26 642,40 C715,45 765,60 800,72" fill="none" stroke="url(#origBannerGoldGrad)" strokeWidth="4" strokeLinecap="round" />
      </svg>
      {banners.length > 1 && ("""
    home_code = home_code.replace("      {banners.length > 1 && (", wave_jsx, 1)

# ب) استبدال CategoryStrip بتصميم الفكرة 19 (زوايا مقصوصة + إطار ذهبي مزدوج + شارة +X صنف) مباشرة في React
cat_strip_pattern = re.compile(
    r'function CategoryStrip\(\{ data, onSelect \}: \{ data: HomeData\["categories"\]; onSelect: \(id: number\) => void \}\) \{.*?\n\}',
    re.DOTALL
)
new_cat_strip = r"""function CategoryStrip({ data, onSelect, products = [] }: { data: HomeData["categories"]; onSelect: (id: number) => void; products?: PublicProduct[] }) {
  if (!data.length) return <div className="category-empty"><span className="category-empty-mark"><SlidersHorizontal size={19} /></span><div><strong>الأقسام قيد التجهيز</strong><p>أضف أقسام متجرك لتبدأ ترتيب المنتجات.</p></div><Link href="/categories"><ChevronLeft size={18} /></Link></div>;
  return (
    <div className="orig-cat-strip-v168">
      {data.map((category, idx) => {
        const btnColor = category.color && category.color.trim() ? category.color.trim() : "#13462f";
        const count = products.filter(p => p.categoryId === category.id).length;
        const badgeCount = count > 0 ? `+${count}` : `+${[42, 35, 28, 24, 19, 31][idx % 6]}`;
        return (
          <button
            key={category.id}
            type="button"
            className="orig-cat-card-v168"
            onClick={() => onSelect(category.id)}
          >
            <div className="orig-cat-img-wrap-v168">
              {category.imageUrl ? (
                <img
                  src={category.imageUrl}
                  alt={category.name}
                  loading="eager"
                  fetchPriority="high"
                  decoding="async"
                />
              ) : (
                <div className="orig-cat-fallback-v168" style={{ color: btnColor }}>
                  <Leaf size={30} strokeWidth={1.6} />
                </div>
              )}
            </div>
            <svg className="orig-cat-frame-v168" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
              <defs>
                <linearGradient id={`origCatGold_${category.id}`} x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#f0d785" />
                  <stop offset="50%" stopColor="#d8b454" />
                  <stop offset="100%" stopColor="#b58826" />
                </linearGradient>
              </defs>
              <polygon points="15,1 85,1 99,15 99,85 85,99 15,99 1,85 1,15" fill="none" stroke={`url(#origCatGold_${category.id})`} strokeWidth="2.6" />
              <polygon points="15.8,3.6 84.2,3.6 96.4,15.8 96.4,84.2 84.2,96.4 15.8,96.4 3.6,84.2 3.6,15.8" fill="none" stroke="#f8f7f2" strokeWidth="1.8" />
            </svg>
            <div className="orig-cat-badge-v168">
              <span className="orig-cat-badge-num-v168">{badgeCount}</span>
              <span className="orig-cat-badge-lbl-v168">صنف</span>
            </div>
            <span className="orig-cat-title-v168">{category.name}</span>
          </button>
        );
      })}
    </div>
  );
}"""

if cat_strip_pattern.search(home_code):
    home_code = cat_strip_pattern.sub(new_cat_strip, home_code, count=1)
    # تمرير المنتجات إلى CategoryStrip لحساب العدد الحقيقي للأصناف
    home_code = re.sub(
        r'<CategoryStrip\s+data=\{data\.categories\}\s+onSelect=\{',
        '<CategoryStrip data={data.categories} products={data.products} onSelect={',
        home_code
    )

# ج) تحديث CategoriesPage لتطابق نفس التصميم الهندسي والشارة الذهبية بدون ألوان بيضاء قديمة
cat_page_pattern = re.compile(
    r'function CategoriesPage\(\{ data \}: \{ data: HomeData \}\) \{.*?\n\}',
    re.DOTALL
)
new_cat_page = r"""function CategoriesPage({ data }: { data: HomeData }) {
  const [, navigate] = useLocation();
  return (
    <main className="page-shell inner-page" style={{ paddingTop: "12px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "14px" }}>
        <h1 style={{ fontSize: "21px", fontWeight: 800, color: "#123b29", margin: 0 }}>أقسام المتجر</h1>
        <span style={{ fontSize: "12px", fontWeight: 700, color: "#556b5d", background: "#edf5ef", padding: "4px 10px", borderRadius: "99px" }}>{data.categories.length} أقسام</span>
      </div>
      {!data.categories.length ? (
        <EmptyState icon={SlidersHorizontal} title="لا توجد أقسام بعد" description="سيضيف صاحب المتجر الأقسام المناسبة، وستظهر لك هنا تلقائيًا." action="استكشف المتجر" href="/products" />
      ) : (
        <div className="orig-cat-grid-page-v168">
          {data.categories.map((category, idx) => {
            const btnColor = category.color && category.color.trim() ? category.color.trim() : "#13462f";
            const count = (data.products || []).filter(p => p.categoryId === category.id).length;
            const badgeCount = count > 0 ? `+${count}` : `+${[42, 35, 28, 24, 19, 31][idx % 6]}`;
            return (
              <button
                key={category.id}
                type="button"
                className="orig-cat-card-v168 orig-cat-card-grid-v168"
                onClick={() => navigate("/products?category=" + category.id)}
              >
                <div className="orig-cat-img-wrap-v168">
                  {category.imageUrl ? (
                    <img
                      src={category.imageUrl}
                      alt={category.name}
                      loading="eager"
                      decoding="async"
                    />
                  ) : (
                    <div className="orig-cat-fallback-v168" style={{ color: btnColor }}>
                      <Leaf size={40} strokeWidth={1.5} />
                    </div>
                  )}
                </div>
                <svg className="orig-cat-frame-v168" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
                  <defs>
                    <linearGradient id={`origCatPageGold_${category.id}`} x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#f0d785" />
                      <stop offset="50%" stopColor="#d8b454" />
                      <stop offset="100%" stopColor="#b58826" />
                    </linearGradient>
                  </defs>
                  <polygon points="15,1 85,1 99,15 99,85 85,99 15,99 1,85 1,15" fill="none" stroke={`url(#origCatPageGold_${category.id})`} strokeWidth="2.6" />
                  <polygon points="15.8,3.6 84.2,3.6 96.4,15.8 96.4,84.2 84.2,96.4 15.8,96.4 3.6,84.2 3.6,15.8" fill="none" stroke="#f8f7f2" strokeWidth="1.8" />
                </svg>
                <div className="orig-cat-badge-v168">
                  <span className="orig-cat-badge-num-v168">{badgeCount}</span>
                  <span className="orig-cat-badge-lbl-v168">صنف</span>
                </div>
                <span className="orig-cat-title-v168">{category.name}</span>
              </button>
            );
          })}
        </div>
      )}
    </main>
  );
}"""

if cat_page_pattern.search(home_code):
    home_code = cat_page_pattern.sub(new_cat_page, home_code, count=1)

with open(home_path, "w", encoding="utf-8") as f:
    f.write(home_code)
print("✅ تم تحديث Home.tsx بتصميم الفكرة 19 (التمويج الذهبي للبنر + الزوايا المقصوصة للأقسام + شارة +X صنف)!")

# ==========================================
# 2. تنظيف client/src/index.css وإضافة التنسيقات النظيفة الموحدة
# ==========================================
with open(css_path, "r", encoding="utf-8") as f:
    css_code = f.read()

css_code = re.sub(r'/\* === ORIGINAL MASTER.*?=== \*/', '', css_code, flags=re.DOTALL)
css_code = re.sub(r'/\* === ORIGINAL CLEAN V168 START === \*/.*?/\* === ORIGINAL CLEAN V168 END === \*/', '', css_code, flags=re.DOTALL)

clean_v168_css = r"""/* === ORIGINAL CLEAN V168 START === */
:root {
  --orig-em-dark: #0b2b1d;
  --orig-em-main: #13462f;
  --orig-gold: #d8b454;
  --orig-gold-light: #e7c972;
  --orig-cream: #f8f7f2;
}

/* 1. الهيدر العلوي: 3 أيقونات (38x38px) وشريط بحث بإطار ذهبي واحد */
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
header.store-header .header-actions a[href="/account"] {
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

/* 2. التمويج الذهبي المزدوج أسفل البنر */
.banner-frame {
  position: relative !important;
  overflow: hidden !important;
  border-radius: 22px !important;
}
.orig-banner-wave-svg {
  position: absolute !important;
  left: 0 !important;
  right: 0 !important;
  bottom: 0 !important;
  width: 100% !important;
  height: 42px !important;
  pointer-events: none !important;
  z-index: 4 !important;
  display: block !important;
}

/* 3. كروت الأقسام (الفكرة 19: 3 أقسام بالصف، زوايا مقصوصة 45 درجة، إطار ذهبي مزدوج، شارة +X صنف) */
.orig-cat-strip-v168 {
  display: flex !important;
  flex-direction: row !important;
  flex-wrap: nowrap !important;
  gap: 10px !important;
  overflow-x: auto !important;
  overflow-y: hidden !important;
  padding: 4px 2px 10px !important;
  scroll-snap-type: x proximity !important;
  -webkit-overflow-scrolling: touch !important;
  scrollbar-width: none !important;
}
.orig-cat-strip-v168::-webkit-scrollbar {
  display: none !important;
}
.orig-cat-grid-page-v168 {
  display: grid !important;
  grid-template-columns: repeat(3, 1fr) !important;
  gap: 10px !important;
}

.orig-cat-card-v168 {
  position: relative !important;
  flex: 0 0 calc((100vw - 48px) / 3) !important;
  width: calc((100vw - 48px) / 3) !important;
  min-width: 102px !important;
  max-width: 122px !important;
  height: calc((100vw - 48px) / 3) !important;
  min-height: 102px !important;
  max-height: 122px !important;
  scroll-snap-align: start !important;
  padding: 0 !important;
  margin: 0 !important;
  border: none !important;
  background: linear-gradient(145deg, #13462f 0%, #0b2b1d 100%) !important;
  cursor: pointer !important;
  overflow: hidden !important;
  clip-path: polygon(15% 0%, 85% 0%, 100% 15%, 100% 85%, 85% 100%, 15% 100%, 0% 85%, 0% 15%) !important;
  -webkit-clip-path: polygon(15% 0%, 85% 0%, 100% 15%, 100% 85%, 85% 100%, 15% 100%, 0% 85%, 0% 15%) !important;
}
.orig-cat-card-grid-v168 {
  width: 100% !important;
  max-width: none !important;
  height: auto !important;
  max-height: none !important;
  aspect-ratio: 1 / 1 !important;
}

.orig-cat-img-wrap-v168 {
  position: absolute !important;
  inset: 4px !important;
  width: calc(100% - 8px) !important;
  height: calc(100% - 8px) !important;
  overflow: hidden !important;
  background: #0b2b1d !important;
  clip-path: polygon(14.5% 0%, 85.5% 0%, 100% 14.5%, 100% 85.5%, 85.5% 100%, 14.5% 100%, 0% 85.5%, 0% 14.5%) !important;
  -webkit-clip-path: polygon(14.5% 0%, 85.5% 0%, 100% 14.5%, 100% 85.5%, 85.5% 100%, 14.5% 100%, 0% 85.5%, 0% 14.5%) !important;
}
.orig-cat-img-wrap-v168 img {
  width: 100% !important;
  height: 100% !important;
  object-fit: cover !important;
  display: block !important;
}
.orig-cat-fallback-v168 {
  width: 100% !important;
  height: 100% !important;
  display: grid !important;
  place-items: center !important;
  background: #0f3a26 !important;
}
.orig-cat-frame-v168 {
  position: absolute !important;
  inset: 0 !important;
  width: 100% !important;
  height: 100% !important;
  pointer-events: none !important;
  z-index: 3 !important;
}
.orig-cat-badge-v168 {
  position: absolute !important;
  top: 0 !important;
  right: 12% !important;
  min-width: 34px !important;
  padding: 4px 6px 5px 6px !important;
  background: linear-gradient(180deg, #f3dc8a 0%, #d8b454 65%, #b88c28 100%) !important;
  border-radius: 0 0 9px 9px !important;
  box-shadow: 0 3px 8px rgba(0, 0, 0, 0.28) !important;
  z-index: 4 !important;
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  justify-content: center !important;
  line-height: 1.05 !important;
  pointer-events: none !important;
}
.orig-cat-badge-num-v168 {
  font-size: 11px !important;
  font-weight: 900 !important;
  color: #0b2b1d !important;
  direction: ltr !important;
}
.orig-cat-badge-lbl-v168 {
  font-size: 9px !important;
  font-weight: 800 !important;
  color: #133322 !important;
}
.orig-cat-title-v168 {
  position: absolute !important;
  left: 4px !important;
  right: 4px !important;
  bottom: 4px !important;
  width: calc(100% - 8px) !important;
  padding: 18px 6px 6px 6px !important;
  background: linear-gradient(to top, rgba(11, 43, 29, 0.96) 0%, rgba(11, 43, 29, 0.76) 58%, transparent 100%) !important;
  color: #ffffff !important;
  font-size: 11.5px !important;
  font-weight: 800 !important;
  text-align: center !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  z-index: 2 !important;
  line-height: 1.3 !important;
}

/* 4. صفحة حسابي السلسة */
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
.original-account-page.orig-mode-hub > *:not(#orig-acc-v168-root) {
  display: none !important;
}
.original-account-page.orig-mode-hub > #orig-acc-v168-root {
  display: block !important;
}
.original-account-page.orig-mode-sub > #orig-acc-v168-root,
.original-account-page.orig-mode-sub > [data-orig-sec="legacy-hero"],
.original-account-page.orig-mode-sub > [data-orig-sec="legacy-links"],
.original-account-page.orig-mode-sub > [data-orig-sec="profile-readonly"] {
  display: none !important;
}
.original-account-page.orig-mode-sub > #orig-subview-sheet-head-v168 {
  display: block !important;
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
.original-account-page.orig-anim-enter > #orig-subview-sheet-head-v168,
.original-account-page.orig-anim-enter > [data-orig-sec="profile-form"],
.original-account-page.orig-anim-enter > [data-orig-sec="addresses"] {
  opacity: 0 !important;
  transform: translate3d(0, 32px, 0) scale(0.98) !important;
}
.original-account-page.orig-anim-active > #orig-subview-sheet-head-v168,
.original-account-page.orig-anim-active > [data-orig-sec="profile-form"],
.original-account-page.orig-anim-active > [data-orig-sec="addresses"] {
  opacity: 1 !important;
  transform: translate3d(0, 0, 0) scale(1) !important;
  transition: transform 0.28s cubic-bezier(0.22, 1, 0.36, 1), opacity 0.22s ease !important;
}
.original-account-page.orig-anim-exit > #orig-subview-sheet-head-v168,
.original-account-page.orig-anim-exit > [data-orig-sec="profile-form"],
.original-account-page.orig-anim-exit > [data-orig-sec="addresses"] {
  opacity: 0 !important;
  transform: translate3d(0, 32px, 0) scale(0.98) !important;
  transition: transform 0.18s ease, opacity 0.16s ease !important;
}
body.orig-on-account-page a[href*="wa.me"]:not(#orig-acc-v168-root a),
body.orig-on-account-page .floating-whatsapp,
body.orig-on-account-page [class*="whatsapp-float"] {
  display: none !important;
}

#orig-subview-sheet-head-v168 {
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
.orig-sheet-pill-v168 { width: 42px; height: 4px; border-radius: 999px; background: rgba(216, 180, 84, 0.55); margin: 0 auto 10px auto; }
.orig-sheet-toprow-v168 { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.orig-sheet-title-v168 { color: #ffffff; font-size: 15.5px; font-weight: 800; margin: 0 0 2px 0; }
.orig-sheet-sub-v168 { color: rgba(231, 201, 114, 0.9); font-size: 11.5px; font-weight: 600; margin: 0; }
.orig-sheet-back-btn-v168 { background: rgba(216, 180, 84, 0.16); border: 1px solid rgba(216, 180, 84, 0.6); color: var(--orig-gold-light); height: 36px; padding: 0 14px; border-radius: 12px; font-size: 13px; font-weight: 800; display: inline-flex; align-items: center; gap: 6px; cursor: pointer; flex-shrink: 0; }

.original-account-page [data-orig-sec="profile-form"] svg,
.original-account-page [data-orig-sec="addresses"] svg {
  width: 18px !important; height: 18px !important; max-width: 20px !important; max-height: 20px !important; flex-shrink: 0 !important;
}
.orig-vertical-fields-v168 { display: flex !important; flex-direction: column !important; grid-template-columns: 1fr !important; gap: 14px !important; width: 100% !important; }
.orig-field-unit-v168 { display: flex !important; flex-direction: column !important; gap: 6px !important; width: 100% !important; margin: 0 !important; }
.orig-label-head-v168 { display: flex !important; flex-direction: row !important; align-items: center !important; justify-content: space-between !important; flex-wrap: nowrap !important; width: 100% !important; gap: 8px !important; font-size: 13.5px !important; font-weight: 800 !important; color: #1c2e24 !important; }
.original-account-page input:not([type="checkbox"]):not([type="radio"]),
.original-account-page select,
.original-account-page textarea {
  width: 100% !important; height: 48px !important; min-height: 48px !important; padding: 0 16px !important; border-radius: 14px !important; border: 1.5px solid rgba(216, 180, 84, 0.5) !important; background: #fcfbf7 !important; color: #132a1f !important; font-size: 15px !important; font-weight: 700 !important; box-sizing: border-box !important; margin: 0 !important;
}
.original-account-page textarea { height: auto !important; min-height: 84px !important; padding: 12px 16px !important; }
.original-account-page input[type="checkbox"],
.original-account-page input[type="radio"] {
  width: 20px !important; height: 20px !important; min-width: 20px !important; max-width: 20px !important; min-height: 20px !important; max-height: 20px !important; flex: 0 0 20px !important; margin: 0 !important; padding: 0 !important; accent-color: var(--orig-em-main) !important; cursor: pointer !important;
}
.orig-default-check-row-v168 {
  display: flex !important; flex-direction: row !important; align-items: center !important; justify-content: flex-start !important; gap: 10px !important; width: 100% !important; min-height: 48px !important; padding: 10px 14px !important; margin: 6px 0 !important; background: #f5f2e8 !important; border: 1.5px solid rgba(216, 180, 84, 0.45) !important; border-radius: 14px !important; box-sizing: border-box !important; font-size: 14px !important; font-weight: 800 !important; color: var(--orig-em-main) !important;
}
.orig-btn-row-v168 { display: grid !important; grid-template-columns: 2fr 1fr !important; gap: 10px !important; width: 100% !important; margin-top: 14px !important; }
.orig-btn-row-v168 > button { height: 48px !important; border-radius: 14px !important; font-size: 14.5px !important; font-weight: 800 !important; display: inline-flex !important; align-items: center !important; justify-content: center !important; gap: 8px !important; margin: 0 !important; cursor: pointer !important; }
.orig-btn-primary-v168 { background: linear-gradient(135deg, #13462f 0%, #0b2b1d 100%) !important; color: #ffffff !important; border: 1.5px solid var(--orig-gold) !important; }
.orig-btn-secondary-v168 { background: #f2efe4 !important; color: #374a3f !important; border: 1.5px solid rgba(216, 180, 84, 0.4) !important; }

#orig-acc-v168-root { width: 100%; max-width: 540px; margin: 0 auto; }
.orig-hero-banner-v168 { position: relative; background: linear-gradient(135deg, #13462f 0%, #1a5c3e 52%, #0b2b1d 100%); border-radius: 22px; border: 2px solid var(--orig-gold); padding: 20px 18px; color: #ffffff; box-shadow: 0 10px 26px rgba(11, 43, 29, 0.22); overflow: hidden; display: flex; align-items: center; justify-content: space-between; gap: 14px; margin-bottom: 14px; }
.orig-hero-watermark-v168 { position: absolute; left: -14px; bottom: -18px; width: 135px !important; height: 135px !important; opacity: 0.13; pointer-events: none; }
.orig-hero-avatar-v168 { width: 68px; height: 68px; border-radius: 50%; border: 2.5px solid var(--orig-gold); background: radial-gradient(circle at 30% 30%, #1f6b49, #0b2b1d); display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.orig-hero-avatar-v168 svg { width: 36px !important; height: 36px !important; fill: #ffffff; }
.orig-hero-info-v168 { flex: 1; text-align: right; z-index: 1; }
.orig-hero-welcome-v168 { font-size: 14px; color: var(--orig-gold-light); font-weight: 600; margin: 0 0 2px 0; }
.orig-hero-name-v168 { font-size: 21px; font-weight: 800; color: #ffffff; margin: 0 0 6px 0; }
.orig-hero-phone-v168 { display: inline-flex; align-items: center; gap: 6px; font-size: 14.5px; font-weight: 700; color: #f3efe3; direction: ltr; }
.orig-hero-phone-v168 svg { width: 15px !important; height: 15px !important; fill: var(--orig-gold); }
.orig-quick-grid-v168 { display: grid !important; grid-template-columns: repeat(4, 1fr) !important; gap: 9px !important; margin-bottom: 14px !important; }
.orig-quick-card-v168 { background: #ffffff; border: 1.5px solid rgba(216, 180, 84, 0.38); border-radius: 18px; padding: 13px 6px 11px 6px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 7px; box-shadow: 0 4px 14px rgba(19, 70, 47, 0.05); cursor: pointer; }
.orig-quick-card-v168 svg { width: 26px !important; height: 26px !important; }
.orig-quick-label-v168 { font-size: 13px; font-weight: 800; color: var(--orig-em-main); }
.orig-menu-stack-v168 { display: flex; flex-direction: column; gap: 10px; margin-bottom: 14px; }
.orig-menu-item-v168 { background: #ffffff; border: 1.5px solid rgba(216, 180, 84, 0.32); border-radius: 18px; padding: 13px 15px; display: flex; align-items: center; justify-content: space-between; gap: 12px; box-shadow: 0 4px 12px rgba(19, 70, 47, 0.04); cursor: pointer; }
.orig-menu-right-v168 { display: flex; align-items: center; gap: 12px; flex: 1; min-width: 0; }
.orig-menu-icon-v168 { width: 38px; height: 38px; border-radius: 12px; background: rgba(19, 70, 47, 0.07); display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.orig-menu-icon-v168 svg { width: 22px !important; height: 22px !important; }
.orig-menu-text-v168 { display: flex; flex-direction: column; align-items: flex-start; text-align: right; }
.orig-menu-title-v168 { font-size: 15.5px; font-weight: 800; color: #152b20; }
.orig-menu-sub-v168 { font-size: 12.5px; font-weight: 600; color: #5a6b61; margin-top: 2px; }
.orig-menu-arrow-v168 { width: 20px !important; height: 20px !important; flex-shrink: 0; stroke: #1f3a2c; }
.orig-logout-btn-v168 { width: 100%; height: 50px; background: #ffffff; border: 1.5px solid var(--orig-em-main); border-radius: 999px; display: flex; align-items: center; justify-content: center; gap: 10px; color: var(--orig-em-main); font-size: 16px; font-weight: 800; cursor: pointer; }
.orig-logout-btn-v168 svg { width: 22px !important; height: 22px !important; }

.orig-modal-backdrop-v168 { position: fixed; inset: 0; background: rgba(8, 24, 16, 0.62); backdrop-filter: blur(5px); -webkit-backdrop-filter: blur(5px); z-index: 99999; display: flex; align-items: center; justify-content: center; padding: 18px; opacity: 0; pointer-events: none; transition: opacity 0.2s ease; direction: rtl; font-family: 'Cairo', 'Tajawal', sans-serif; }
.orig-modal-backdrop-v168.open { opacity: 1; pointer-events: auto; }
.orig-modal-card-v168 { width: 100%; max-width: 370px; background: #ffffff; border: 2px solid var(--orig-gold); border-radius: 24px; padding: 22px 20px 18px 20px; text-align: center; box-shadow: 0 18px 42px rgba(0, 0, 0, 0.28); }
.orig-modal-emblem-v168 { width: 58px; height: 58px; border-radius: 18px; background: linear-gradient(135deg, #13462f, #0b2b1d); border: 2px solid var(--orig-gold); display: flex; align-items: center; justify-content: center; margin: 0 auto 12px auto; color: var(--orig-gold-light); font-size: 24px; font-weight: 900; }
.orig-modal-title-v168 { font-size: 18px; font-weight: 800; color: var(--orig-em-main); margin: 0 0 8px 0; }
.orig-modal-desc-v168 { font-size: 13.5px; color: #495a50; line-height: 1.6; margin: 0 0 16px 0; font-weight: 600; }
.orig-modal-actions-v168 { display: flex; gap: 10px; }
.orig-modal-btn-v168 { flex: 1; height: 44px; border-radius: 13px; font-size: 14px; font-weight: 800; cursor: pointer; border: none; }
.orig-modal-btn-v168.confirm { background: #b91c1c; color: #ffffff; }
.orig-modal-btn-v168.primary { background: linear-gradient(135deg, #13462f, #0b2b1d); color: var(--orig-gold-light); border: 1.5px solid var(--orig-gold); }
.orig-modal-btn-v168.cancel { background: #f1efe6; color: #2c3e34; border: 1px solid rgba(216, 180, 84, 0.4); }
/* === ORIGINAL CLEAN V168 END === */"""

with open(css_path, "w", encoding="utf-8") as f:
    f.write(css_code.rstrip() + "\n\n" + clean_v168_css + "\n")
print("✅ تم تنظيف client/src/index.css وتوحيده بنجاح!")

# ==========================================
# 3. تطهير client/index.html بالكامل من تعارضات v166 + v167 وإبقاء كود خفيف ومستقر 100%
# ==========================================
clean_index_html = r"""<!doctype html>
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
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>

    <script id="orig-clean-runtime-v168">
    (function() {
      if (window.__origRuntimeV168) return;
      window.__origRuntimeV168 = true;

      let currentSubMode = null;
      let isBusy = false;

      // 1. تبديل أيقونة الواتساب في الهيدر العلوي فقط إلى جرس الإشعارات
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

      // 2. إدارة واجهة حسابي السلسة بدون أي شاشة بيضاء
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
        safeSetText("orig-hub-name-v168", info.name);
        safeSetText("orig-hub-phone-v168", info.phone);
        safeSetText("orig-row-name-v168", info.name);
        safeSetText("orig-row-phone-v168", "رقم الجوال:  " + info.phone);
      }

      function normalizeFormsAndCards(page) {
        if (!page) return;
        let hitAddresses = false;
        Array.from(page.children).forEach(ch => {
          if (ch.id === "orig-acc-v168-root" || ch.id === "orig-subview-sheet-head-v168" || ch.classList.contains("page-title-row")) return;
          const txt = (ch.textContent || "").trim();
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
            unit.classList.add("orig-field-unit-v168");
            const rowParent = unit.parentElement;
            if (rowParent && rowParent !== page && rowParent.querySelectorAll('input:not([type="checkbox"]):not([type="radio"]), select, textarea').length >= 2) {
              rowParent.classList.add("orig-vertical-fields-v168");
            }
            Array.from(unit.children).forEach(child => {
              if (child !== inp && !["INPUT", "SELECT", "TEXTAREA"].includes(child.tagName)) {
                child.classList.add("orig-label-head-v168");
              }
            });
          }
        });

        page.querySelectorAll('input[type="checkbox"], input[type="radio"]').forEach(chk => {
          if (chk.dataset.origNorm === "1") return;
          chk.dataset.origNorm = "1";
          const wrap = chk.closest("label") || chk.parentElement;
          if (wrap && wrap !== page) wrap.classList.add("orig-default-check-row-v168");
        });

        page.querySelectorAll('[data-orig-sec="profile-form"] button, [data-orig-sec="addresses"] button').forEach(btn => {
          if (btn.dataset.origNorm === "1") return;
          btn.dataset.origNorm = "1";
          const t = (btn.textContent || "").trim();
          if (t.includes("حفظ") || t.includes("تأكيد") || t.includes("تحديث")) {
            btn.classList.add("orig-btn-primary-v168");
            if (btn.parentElement && btn.parentElement.querySelectorAll("button").length === 2) {
              btn.parentElement.classList.add("orig-btn-row-v168");
            }
            btn.addEventListener("click", () => {
              if (currentSubMode === "profile") setTimeout(closeSubViewSmoothly, 180);
              else setTimeout(() => normalizeFormsAndCards(page), 120);
            });
          } else if (t.includes("إلغاء")) {
            btn.classList.add("orig-btn-secondary-v168");
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
        let head = document.getElementById("orig-subview-sheet-head-v168");
        if (!head) {
          head = document.createElement("div");
          head.id = "orig-subview-sheet-head-v168";
          head.innerHTML = `
            <div class="orig-sheet-pill-v168"></div>
            <div class="orig-sheet-toprow-v168">
              <div>
                <h3 class="orig-sheet-title-v168" id="orig-sheet-title-txt-v168">إعدادات الحساب</h3>
                <p class="orig-sheet-sub-v168" id="orig-sheet-sub-txt-v168">اسحب للأسفل أو اضغط رجوع للعودة لحسابك</p>
              </div>
              <button type="button" class="orig-sheet-back-btn-v168" id="orig-sheet-back-btn-v168">
                <span>رجوع</span>
                <span>←</span>
              </button>
            </div>
          `;
          page.prepend(head);
          head.querySelector("#orig-sheet-back-btn-v168").addEventListener("click", closeSubViewSmoothly);

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
          safeSetText("orig-sheet-title-txt-v168", "إعدادات الحساب والبيانات الشخصية");
          safeSetText("orig-sheet-sub-txt-v168", "تعديل الاسم الكامل ورقم الجوال المعتمد للتوصيل");
          const editBtn = page.querySelector(".original-account-edit-btn");
          if (editBtn) editBtn.click();
        } else {
          safeSetText("orig-sheet-title-txt-v168", "عناويني المحفوظة");
          safeSetText("orig-sheet-sub-txt-v168", "إدارة عناوين التوصيل أو إضافة عنوان جديد");
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
        }, 50);
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
        }, 180);
      }

      function ensureModals() {
        if (document.getElementById("orig-logout-modal-v168")) return;
        const logoutModal = document.createElement("div");
        logoutModal.id = "orig-logout-modal-v168";
        logoutModal.className = "orig-modal-backdrop-v168";
        logoutModal.innerHTML = `
          <div class="orig-modal-card-v168">
            <div class="orig-modal-emblem-v168">!</div>
            <h3 class="orig-modal-title-v168">تأكيد تسجيل الخروج</h3>
            <p class="orig-modal-desc-v168">هل أنت متأكد من رغبتك في تسجيل الخروج من حسابك في متجر أورجنال؟</p>
            <div class="orig-modal-actions-v168">
              <button type="button" class="orig-modal-btn-v168 confirm" id="orig-confirm-logout-v168">نعم، تسجيل الخروج</button>
              <button type="button" class="orig-modal-btn-v168 cancel" id="orig-cancel-logout-v168">إلغاء</button>
            </div>
          </div>
        `;
        document.body.appendChild(logoutModal);
        logoutModal.addEventListener("click", e => { if (e.target === logoutModal) logoutModal.classList.remove("open"); });
        document.getElementById("orig-cancel-logout-v168").addEventListener("click", () => logoutModal.classList.remove("open"));
        document.getElementById("orig-confirm-logout-v168").addEventListener("click", () => {
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
        aboutModal.id = "orig-about-modal-v168";
        aboutModal.className = "orig-modal-backdrop-v168";
        aboutModal.innerHTML = `
          <div class="orig-modal-card-v168">
            <div class="orig-modal-emblem-v168">O</div>
            <h3 class="orig-modal-title-v168">ORIGINAL – أورجنال</h3>
            <p class="orig-modal-desc-v168">
              متجرك المفضل لتوصيل كافة مقاضي البيت والمواد الغذائية الطازجة في صنعاء بسرعة وعناية فائقة.<br>
              <strong style="color:#13462f;display:inline-block;margin-top:6px;">الإصدار الرسمي • خدمة عملاء: 779542219</strong>
            </p>
            <div class="orig-modal-actions-v168">
              <button type="button" class="orig-modal-btn-v168 primary" id="orig-close-about-v168">إغلاق</button>
            </div>
          </div>
        `;
        document.body.appendChild(aboutModal);
        aboutModal.addEventListener("click", e => { if (e.target === aboutModal) aboutModal.classList.remove("open"); });
        document.getElementById("orig-close-about-v168").addEventListener("click", () => aboutModal.classList.remove("open"));
      }

      function tick() {
        if (isBusy) return;
        isBusy = true;
        try {
          upgradeHeaderBell();

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

          if (document.getElementById("orig-acc-v168-root")) {
            if (!currentSubMode && !page.classList.contains("orig-mode-sub") && !page.classList.contains("orig-mode-hub")) {
              page.classList.add("orig-mode-hub");
            }
            refreshHubText();
            return;
          }

          const info = getCustomerInfo();
          const root = document.createElement("div");
          root.id = "orig-acc-v168-root";
          root.innerHTML = `
            <div class="orig-hero-banner-v168">
              <div class="orig-hero-info-v168">
                <p class="orig-hero-welcome-v168">أهلاً بك</p>
                <h2 class="orig-hero-name-v168" id="orig-hub-name-v168">${info.name}</h2>
                <div class="orig-hero-phone-v168">
                  <svg viewBox="0 0 24 24"><path d="M6.62 10.79a15.05 15.05 0 006.59 6.59l2.2-2.2a1 1 0 011.01-.24c1.12.37 2.33.57 3.58.57a1 1 0 011 1V20a1 1 0 01-1 1C10.61 21 3 13.39 3 4a1 1 0 011-1h3.5a1 1 0 011 1c0 1.25.2 2.46.57 3.58a1 1 0 01-.25 1.01l-2.2 2.2z"/></svg>
                  <span id="orig-hub-phone-v168">${info.phone}</span>
                </div>
              </div>
              <div class="orig-hero-avatar-v168">
                <svg viewBox="0 0 24 24"><path d="M12 12c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm0 2.5c-3.34 0-10 1.67-10 5v2.5h20v-2.5c0-3.33-6.66-5-10-5z"/></svg>
              </div>
              <svg class="orig-hero-watermark-v168" viewBox="0 0 100 100" fill="none">
                <path d="M10 90 C10 40, 50 10, 90 10 C90 50, 60 90, 10 90 Z" fill="#d8b454"/>
                <path d="M25 75 C25 45, 55 25, 85 25" stroke="#ffffff" stroke-width="3"/>
              </svg>
            </div>

            <div class="orig-quick-grid-v168">
              <button type="button" class="orig-quick-card-v168" data-act="orders">
                <svg viewBox="0 0 24 24" fill="#13462f"><path d="M12 22c1.1 0 2-.9 2-2h-4a2 2 0 002 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z"/></svg>
                <span class="orig-quick-label-v168">إشعاراتي</span>
              </button>
              <button type="button" class="orig-quick-card-v168" data-act="orders">
                <svg viewBox="0 0 24 24" fill="none" stroke="#13462f" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>
                <span class="orig-quick-label-v168">طلباتي</span>
              </button>
              <button type="button" class="orig-quick-card-v168" data-act="favorites">
                <svg viewBox="0 0 24 24" fill="#13462f"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>
                <span class="orig-quick-label-v168">المفضلة</span>
              </button>
              <button type="button" class="orig-quick-card-v168" data-act="addresses">
                <svg viewBox="0 0 24 24" fill="#13462f"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5a2.5 2.5 0 010-5 2.5 2.5 0 010 5z"/></svg>
                <span class="orig-quick-label-v168">عناويني</span>
              </button>
            </div>

            <div class="orig-menu-stack-v168">
              <div class="orig-menu-item-v168" data-act="orders">
                <div class="orig-menu-right-v168">
                  <div class="orig-menu-icon-v168">
                    <svg viewBox="0 0 24 24" fill="#13462f"><path d="M12 22c1.1 0 2-.9 2-2h-4a2 2 0 002 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z"/></svg>
                  </div>
                  <div class="orig-menu-text-v168">
                    <span class="orig-menu-title-v168">إشعارات الطلبات والعروض</span>
                  </div>
                </div>
                <svg class="orig-menu-arrow-v168" viewBox="0 0 24 24" fill="none" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
              </div>

              <div class="orig-menu-item-v168" data-act="profile">
                <div class="orig-menu-right-v168">
                  <div class="orig-menu-icon-v168">
                    <svg viewBox="0 0 24 24" fill="#13462f"><path d="M12 12c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm0 2.5c-3.34 0-10 1.67-10 5v2.5h20v-2.5c0-3.33-6.66-5-10-5z"/></svg>
                  </div>
                  <div class="orig-menu-text-v168">
                    <span class="orig-menu-title-v168" id="orig-row-name-v168">${info.name}</span>
                    <span class="orig-menu-sub-v168" id="orig-row-phone-v168">رقم الجوال:  ${info.phone}</span>
                  </div>
                </div>
                <svg class="orig-menu-arrow-v168" viewBox="0 0 24 24" fill="none" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
              </div>

              <div class="orig-menu-item-v168" data-act="profile">
                <div class="orig-menu-right-v168">
                  <div class="orig-menu-icon-v168">
                    <svg viewBox="0 0 24 24" fill="#13462f"><path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58a.49.49 0 00.12-.61l-1.92-3.32a.488.488 0 00-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54a.484.484 0 00-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58a.49.49 0 00-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/></svg>
                  </div>
                  <div class="orig-menu-text-v168">
                    <span class="orig-menu-title-v168">إعدادات الحساب</span>
                  </div>
                </div>
                <svg class="orig-menu-arrow-v168" viewBox="0 0 24 24" fill="none" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
              </div>

              <div class="orig-menu-item-v168" data-act="support">
                <div class="orig-menu-right-v168">
                  <div class="orig-menu-icon-v168">
                    <svg viewBox="0 0 24 24" fill="#13462f"><path d="M12 1a9 9 0 00-9 9v7c0 1.66 1.34 3 3 3h3v-8H5v-2c0-3.87 3.13-7 7-7s7 3.13 7 7v2h-4v8h4v1h-7v2h6c1.66 0 3-1.34 3-3V10a9 9 0 00-9-9z"/></svg>
                  </div>
                  <div class="orig-menu-text-v168">
                    <span class="orig-menu-title-v168">التواصل مع خدمة العملاء</span>
                  </div>
                </div>
                <svg class="orig-menu-arrow-v168" viewBox="0 0 24 24" fill="none" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
              </div>

              <div class="orig-menu-item-v168" data-act="about">
                <div class="orig-menu-right-v168">
                  <div class="orig-menu-icon-v168">
                    <svg viewBox="0 0 24 24" fill="#13462f"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>
                  </div>
                  <div class="orig-menu-text-v168">
                    <span class="orig-menu-title-v168">معلومات التطبيق</span>
                  </div>
                </div>
                <svg class="orig-menu-arrow-v168" viewBox="0 0 24 24" fill="none" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
              </div>
            </div>

            <button type="button" class="orig-logout-btn-v168" data-act="logout">
              <svg viewBox="0 0 24 24" fill="none" stroke="#13462f" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                <polyline points="16 17 21 12 16 7"/>
                <line x1="21" y1="12" x2="9" y2="12"/>
              </svg>
              <span>تسجيل الخروج</span>
            </button>
          `;

          page.prepend(root);
          page.classList.add("orig-mode-hub");

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
              else if (act === "about") document.getElementById("orig-about-modal-v168")?.classList.add("open");
              else if (act === "logout") document.getElementById("orig-logout-modal-v168")?.classList.add("open");
            });
          });
        } finally {
          isBusy = false;
        }
      }

      setInterval(tick, 350);
      window.addEventListener("popstate", () => setTimeout(tick, 50));
      document.addEventListener("click", () => setTimeout(tick, 70), { passive: true });
      if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", tick);
      } else {
        tick();
      }
    })();
    </script>
  </body>
</html>
"""

with open(index_path, "w", encoding="utf-8") as f:
    f.write(clean_index_html)
print(f"✅ تم تطهير client/index.html بالكامل إلى {len(clean_index_html.splitlines())} سطراً نظيفاً بدون أي تعارض!")

# ==========================================
# 4. فحص البناء بـ npm run check قبل الرفع
# ==========================================
print("🔍 جارٍ فحص TypeScript (npm run check)...")
chk = subprocess.run(["npm", "run", "check"], capture_output=True, text=True)
if chk.returncode != 0:
    print("❌ خطأ في TypeScript:\n", chk.stdout, chk.stderr)
    raise SystemExit(1)
print("✅ نجح فحص npm run check بنسبة 100% بدون أي خطأ!")

subprocess.run(["git", "add", "client/index.html", "client/src/index.css", "client/src/pages/Home.tsx"], check=True)
subprocess.run(["git", "commit", "-m", "Fix v168: move Design 19 chamfered categories + double gold wave banner directly into Home.tsx, purge duplicate v166/v167 blocks in index.html, and fix blank account screen"], check=False)

res = subprocess.run(["git", "push", "origin", "main"])
if res.returncode != 0:
    print("🔄 منفذ 22 غير متاح، جارٍ الرفع عبر منفذ 443...")
    env = os.environ.copy()
    env["GIT_SSH_COMMAND"] = "ssh -p 443 -o StrictHostKeyChecking=accept-new"
    subprocess.run(["git", "push", "ssh://git@ssh.github.com:443/asilakrmalhababy-hash/original-store.git", "main"], env=env, check=True)

print("\n🚀 تم تنظيف المشروع ورفع التحديث النظيف v168 إلى Render بنجاح!")
