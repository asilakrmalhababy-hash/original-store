import sys, re

print("🛠️ [1/3] جاري حقن وتثبيت الأعمدة الصحيحة في commerce.ts...")

perfect_block = """function normalizeOrderItemImage<T extends { productId?: number | null; productImage?: string | null }>(item: T): T {
  if (!item || !item.productImage) return item;
  if (item.productImage.startsWith("data:image/")) {
    return { ...item, productImage: item.productId ? ("/api/fast-img/product/" + item.productId) : null };
  }
  return item;
}

const fastProductColumns = {
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
};

"""

with open("server/commerce.ts", "r", encoding="utf-8") as f:
    comm = f.read()

pos_batch = comm.find("let __allBatchProductsSeeded")
pos_start = comm.find("function normalizeOrderItemImage")
if pos_start == -1:
    pos_start = comm.find("const fastProductColumns")

if pos_batch != -1 and pos_start != -1 and pos_batch > pos_start:
    comm = comm[:pos_start] + perfect_block + comm[pos_batch:]
    with open("server/commerce.ts", "w", encoding="utf-8") as f:
        f.write(comm)

# فحص المطابقة النهائية
with open("client/src/pages/Home.tsx", "r", encoding="utf-8") as f:
    h = f.read()
with open("server/commerce.ts", "r", encoding="utf-8") as f:
    c = f.read()

rc = h.count("function readLocalInstantCatalog")
kc = h.count("const INSTANT_CACHE_KEY")
fpc = c.count("const fastProductColumns = {")
fcc = c.count("const fastCategoryColumns = {")
fbc = c.count("const fastBannerColumns = {")

print("🔍 [2/3] نتائج الفحص الذاتي الدقيق:")
print(f"  • دالة readLocalInstantCatalog: {rc} (المطلوب: 1)")
print(f"  • ثابت INSTANT_CACHE_KEY: {kc} (المطلوب: 1)")
print(f"  • أعمدة fastProductColumns: {fpc} (المطلوب: 1)")
print(f"  • أعمدة fastCategoryColumns: {fcc} (المطلوب: 1)")
print(f"  • أعمدة fastBannerColumns: {fbc} (المطلوب: 1)")

if rc != 1 or kc != 1 or fpc != 1 or fcc != 1 or fbc != 1:
    print("❌ خطأ: الفحص لم يكتمل!")
    sys.exit(1)

print("✅ [3/3] نجحت جميع الفحوصات بنسبة 100%! جاري الرفع الآن...")
