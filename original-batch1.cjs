const fs = require("fs");
const path = "server/commerce.ts";
const source = fs.readFileSync(path, "utf8");

const oldBlock = `    listProducts: publicProcedure.input(z.object({
      search: z.string().trim().max(120).optional(),
      categoryId: safeId.optional(),
      sort: z.enum(["featured", "price-asc", "price-desc", "name"]).default("featured"),
      limit: z.number().int().min(1).max(500).default(250),
    }).optional()).query(async ({ input }) => {
      const g = globalThis as any;
      let base: any[] = g.__fastHomeData?.products;
      if (!Array.isArray(base)) {
        const homeData = await refreshHomeCatalogCache();
        base = homeData?.products || [];
      }
      let list = [...base];
      if (input?.categoryId) list = list.filter(p => p.categoryId === input.categoryId);
      if (input?.search) {
        const q = input.search.toLowerCase();
        list = list.filter(p => String(p.name || "").toLowerCase().includes(q) || String(p.description || "").toLowerCase().includes(q));
      }
      if (input?.sort === "price-asc") list.sort((a, b) => a.price - b.price);
      else if (input?.sort === "price-desc") list.sort((a, b) => b.price - a.price);
      else if (input?.sort === "name") list.sort((a, b) => String(a.name).localeCompare(String(b.name), "ar"));
      return list.slice(0, input?.limit ?? 250);
    }),`;

const newBlock = `    listProducts: publicProcedure.input(z.object({
      search: z.string().trim().max(120).optional(),
      categoryId: safeId.optional(),
      sort: z.enum(["featured", "price-asc", "price-desc", "name"]).default("featured"),
      limit: z.number().int().min(1).max(40).default(40),
      offset: z.number().int().min(0).default(0),
    }).optional()).query(async ({ input }) => {
      const db = await database();
      const filters: any[] = [
        eq(products.isPublished, true),
        eq(products.isAvailable, true),
      ];
      if (input?.categoryId) filters.push(eq(products.categoryId, input.categoryId));
      if (input?.search) {
        const term = "%" + input.search + "%";
        filters.push(or(like(products.name, term), like(products.description, term))!);
      }

      let ordering: any[];
      if (input?.sort === "price-asc") ordering = [asc(products.price), asc(products.id)];
      else if (input?.sort === "price-desc") ordering = [desc(products.price), desc(products.id)];
      else if (input?.sort === "name") ordering = [asc(products.name), asc(products.id)];
      else ordering = [asc(products.sortOrder), desc(products.createdAt), desc(products.id)];

      const limit = input?.limit ?? 40;
      const offset = input?.offset ?? 0;
      const rows = await db.select().from(products)
        .where(and(...filters))
        .orderBy(...ordering)
        .limit(limit)
        .offset(offset);

      return rows.map(row => toFastImg("product", row));
    }),`;

const count = source.split(oldBlock).length - 1;
if (count !== 1) {
  console.error("لم يتم تعديل أي ملف: المقطع المتوقع ليس مطابقًا.");
  process.exit(1);
}

const backup = path + ".backup-pagination-" + Date.now();
fs.copyFileSync(path, backup);
fs.writeFileSync(path, source.replace(oldBlock, newBlock));
console.log("نجح تعديل الخادم. النسخة الاحتياطية:", backup);
