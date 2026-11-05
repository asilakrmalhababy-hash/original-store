import os, sys, re, json

print("🛠️ [1/3] جاري ضبط وتثبيت الأعمدة والدوال بنسخة واحدة صحيحة...")

columns_block = """const fastProductColumns = {
  id: products.id,
  name: products.name,
  slug: products.slug,
  description: products.description,
  imageUrl: sql<string | null>`CASE WHEN ${products.imageUrl} IS NULL OR ${products.imageUrl} = '' THEN NULL WHEN ${products.imageUrl} LIKE 'data:image/%' THEN CONCAT('/api/fast-img/product/', ${products.id}, '?v=', COALESCE(UNIX_TIMESTAMP(${products.updatedAt}), 1)) ELSE ${products.imageUrl} END`,
  categoryId: products.categoryId,
  price: products.price,
  unit: products.unit,
  stock: products.stock,
  minQuantity: products.minQuantity,
  quantityStep: products.quantityStep,
  isPublished: products.isPublished,
  isAvailable: products.isAvailable,
  sortOrder: products.sortOrder,
  createdAt: products.createdAt,
  updatedAt: products.updatedAt,
};
const fastCategoryColumns = {
  id: categories.id,
  name: categories.name,
  slug: categories.slug,
  description: categories.description,
  imageUrl: sql<string | null>`CASE WHEN ${categories.imageUrl} IS NULL OR ${categories.imageUrl} = '' THEN NULL WHEN ${categories.imageUrl} LIKE 'data:image/%' THEN CONCAT('/api/fast-img/category/', ${categories.id}, '?v=', COALESCE(UNIX_TIMESTAMP(${categories.updatedAt}), 1)) ELSE ${categories.imageUrl} END`,
  color: categories.color,
  isActive: categories.isActive,
  sortOrder: categories.sortOrder,
  createdAt: categories.createdAt,
  updatedAt: categories.updatedAt,
};
const fastBannerColumns = {
  id: banners.id,
  title: banners.title,
  body: banners.body,
  imageUrl: sql<string | null>`CASE WHEN ${banners.imageUrl} IS NULL OR ${banners.imageUrl} = '' THEN NULL WHEN ${banners.imageUrl} LIKE 'data:image/%' THEN CONCAT('/api/fast-img/banner/', ${banners.id}, '?v=', COALESCE(UNIX_TIMESTAMP(${banners.updatedAt}), 1)) ELSE ${banners.imageUrl} END`,
  actionText: banners.actionText,
  actionUrl: banners.actionUrl,
  isActive: banners.isActive,
  sortOrder: banners.sortOrder,
  createdAt: banners.createdAt,
  updatedAt: banners.updatedAt,
};"""

with open("server/commerce.ts", "r", encoding="utf-8") as f:
    comm = f.read()

idx1 = comm.find("function normalizeOrderItemImage")
idx2 = comm.find("let __allBatchProductsSeeded")
if idx1 != -1 and idx2 != -1 and idx2 > idx1:
    brace_start = comm.find("{", idx1)
    depth = 0
    fn_end = -1
    for i in range(brace_start, idx2):
        if comm[i] == '{': depth += 1
        elif comm[i] == '}':
            depth -= 1
            if depth == 0:
                fn_end = i + 1
                break
    if fn_end != -1:
        comm = comm[:fn_end] + "\n\n" + columns_block.strip() + "\n\n" + comm[idx2:]

comm = re.sub(r'if \(!\(globalThis as any\)\.__periodicRamSweep\) \{[\s\S]*?10 \* 60 \* 1000\);\s*\}', '', comm)
comm = comm.rstrip() + """

// Safe periodic RAM sweep for rate limits
if (!(globalThis as any).__periodicRamSweep) {
  (globalThis as any).__periodicRamSweep = setInterval(() => {
    try {
      const now = Date.now();
      for (const [k, v] of __orderRateBuckets) { if (now > v.resetAt) __orderRateBuckets.delete(k); }
      for (const [k, v] of __missingItemRateBuckets) { if (now > v.resetAt) __missingItemRateBuckets.delete(k); }
      for (const [k, v] of assistantRateWindows) { if (now - v.startedAt >= 60000) assistantRateWindows.delete(k); }
    } catch {}
  }, 10 * 60 * 1000);
}
"""
with open("server/commerce.ts", "w", encoding="utf-8") as f:
    f.write(comm)

with open("client/src/pages/Home.tsx", "r", encoding="utf-8") as f:
    text = f.read()

def strip_all_read_catalog_declarations(s):
    while True:
        pos = s.find("function readLocalInstantCatalog")
        if pos == -1: break
        start = pos
        key_pos = s.rfind("const INSTANT_CACHE_KEY", 0, pos)
        if key_pos != -1 and (pos - key_pos) < 250:
            start = key_pos
        brace_start = s.find("{", pos)
        if brace_start == -1: break
        depth = 0
        end = brace_start
        for i in range(brace_start, len(s)):
            if s[i] == '{': depth += 1
            elif s[i] == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        s = s[:start] + s[end:]
    return s

cleaned_home = strip_all_read_catalog_declarations(text)

while True:
    p_pos = cleaned_home.find("function computeStorePauseStatus")
    if p_pos == -1: break
    b_start = cleaned_home.find("{", p_pos)
    if b_start == -1: break
    depth = 0
    p_end = b_start
    for i in range(b_start, len(cleaned_home)):
        if cleaned_home[i] == '{': depth += 1
        elif cleaned_home[i] == '}':
            depth -= 1
            if depth == 0:
                p_end = i + 1
                break
    cleaned_home = cleaned_home[:p_pos] + cleaned_home[p_end:]

clean_helper = """const INSTANT_CACHE_KEY = "original-catalog-instant-v2";
function readLocalInstantCatalog(): HomeData {
  try {
    if (typeof window !== "undefined" && (window as any).__INITIAL_CATALOG__) {
      const initCat = (window as any).__INITIAL_CATALOG__;
      if (initCat && Array.isArray(initCat.products)) return initCat as HomeData;
    }
    const raw = typeof localStorage !== "undefined" ? localStorage.getItem(INSTANT_CACHE_KEY) : null;
    if (raw) {
      const p = JSON.parse(raw);
      if (p && Array.isArray(p.products)) return p as HomeData;
    }
  } catch {}
  return { categories: [], products: [], banners: [], offers: [], settings: {} };
}
"""

export_pos = cleaned_home.find("export default function Home()")
if export_pos != -1:
    cleaned_home = cleaned_home[:export_pos].rstrip() + "\n\n" + clean_helper + "\n" + cleaned_home[export_pos:]
    with open("client/src/pages/Home.tsx", "w", encoding="utf-8") as f:
        f.write(cleaned_home)

with open("client/src/pages/Home.tsx", "r", encoding="utf-8") as f:
    h_c = f.read()
with open("server/commerce.ts", "r", encoding="utf-8") as f:
    c_c = f.read()

rc = h_c.count("function readLocalInstantCatalog")
kc = h_c.count("const INSTANT_CACHE_KEY")
fpc = c_c.count("const fastProductColumns = {")
fcc = c_c.count("const fastCategoryColumns = {")
fbc = c_c.count("const fastBannerColumns = {")

print("🔍 [2/3] نتائج الفحص الذاتي الدقيق:")
print(f"  • دالة readLocalInstantCatalog: {rc} (المطلوب: 1)")
print(f"  • ثابت INSTANT_CACHE_KEY: {kc} (المطلوب: 1)")
print(f"  • أعمدة fastProductColumns: {fpc} (المطلوب: 1)")
print(f"  • أعمدة fastCategoryColumns: {fcc} (المطلوب: 1)")
print(f"  • أعمدة fastBannerColumns: {fbc} (المطلوب: 1)")

if rc != 1 or kc != 1 or fpc != 1 or fcc != 1 or fbc != 1:
    print("❌ فشل الفحص! تم إيقاف العملية.")
    sys.exit(1)

print("✅ [3/3] نجحت جميع الفحوصات بنسبة 100%! جاهز للرفع...")
