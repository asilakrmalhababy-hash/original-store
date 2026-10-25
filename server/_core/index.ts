import "dotenv/config";
import express from "express";
import { createServer } from "http";
import { createExpressMiddleware } from "@trpc/server/adapters/express";
import { registerOAuthRoutes } from "./oauth";
import { publicPlatformScript } from "./publicConfig";
import { appRouter } from "../routers";
import { getDb } from "../db";
import { storeSettings, orders, orderEvents } from "../../drizzle/schema";
import { desc, eq as dEq, gt, inArray } from "drizzle-orm";
import { matchesGuestOrderKey } from "../guest-orders";
import { eq } from "drizzle-orm";
import { createContext } from "./context";
import { serveStatic, setupVite } from "./vite";

async function startServer() {
  const app = express();
  const server = createServer(app);
  // Configure body parser with larger size limit for file uploads
  app.use(express.json({ limit: "50mb" }));
  app.use(express.urlencoded({ limit: "50mb", extended: true }));
  app.use("/uploads", express.static("client/public/uploads", { maxAge: "365d", immutable: true }));
  
  let _swAdminCache = { exp: 0, latestId: 0, recent: [] as Array<{ id: number; orderNumber: string; total: number }> };
  app.post("/api/sw-poll", async (req, res) => {
    try {
      const { isAdmin, afterId, refs } = req.body || {};
      const result: any = { ok: true };
      const db = await getDb();
      if (!db) return res.json({ ok: false });
      if (isAdmin) {
        if (Date.now() > _swAdminCache.exp) {
          const recent = await db
            .select({ id: orders.id, orderNumber: orders.orderNumber, total: orders.total })
            .from(orders)
            .orderBy(desc(orders.id))
            .limit(10);
          _swAdminCache = { exp: Date.now() + 8000, latestId: recent[0]?.id ?? 0, recent };
        }
        result.latestId = _swAdminCache.latestId;
        result.newOrders = typeof afterId === "number" && afterId > 0
          ? _swAdminCache.recent.filter(o => o.id > afterId)
          : [];
      }
      if (Array.isArray(refs) && refs.length > 0) {
        const cleanRefs = refs.slice(0, 20).filter(r => r && typeof r.orderNumber === "string" && typeof r.idempotencyKey === "string");
        if (cleanRefs.length > 0) {
          const refMap = new Map(cleanRefs.map(r => [r.orderNumber, r.idempotencyKey]));
          const rows = await db
            .select({ id: orders.id, orderNumber: orders.orderNumber, status: orders.status, idempotencyKey: orders.idempotencyKey })
            .from(orders)
            .where(inArray(orders.orderNumber, [...refMap.keys()]))
            .limit(20);
          const valid = rows.filter(o => {
            const k = refMap.get(o.orderNumber);
            return k ? matchesGuestOrderKey(k, o.idempotencyKey) : false;
          });
          result.orders = valid.map(o => ({ orderId: o.id, orderNumber: o.orderNumber, status: o.status, note: "" }));
        }
      }
      res.json(result);
    } catch {
      res.json({ ok: false });
    }
  });

  app.get("/api/health", (_req, res) => res.json({ status: "ok" }));
  // --- FAST_IMG_ROUTE_START ---
  app.get("/api/fast-img/:kind/:id", async (req, res) => {
    try {
      const kind = req.params.kind;
      const id = Number(req.params.id);
      if (!Number.isInteger(id) || id <= 0) return res.status(404).end();
      const cacheMap: Map<string, { contentType: string; buf: Buffer }> = (globalThis as any).__fastImgCache || ((globalThis as any).__fastImgCache = new Map());
      const cacheKey = kind + ":" + id;
      let entry = cacheMap.get(cacheKey);
      if (!entry) {
        const db = await getDb();
        if (!db) return res.status(404).end();
        const { products, categories, banners } = await import("../../drizzle/schema");
        const table: any = kind === "product" ? products : kind === "category" ? categories : kind === "banner" ? banners : null;
        if (!table) return res.status(404).end();
        const rows = await db.select({ imageUrl: table.imageUrl }).from(table).where(eq(table.id, id)).limit(1);
        const raw = String(rows[0]?.imageUrl || "");
        const m = raw.match(/^data:(image\/[a-zA-Z0-9.+-]+);base64,([\s\S]+)$/);
        if (!m) {
          if (raw.startsWith("/")) return res.redirect(302, raw);
          return res.status(404).end();
        }
        entry = { contentType: m[1], buf: Buffer.from(m[2], "base64") };
        cacheMap.set(cacheKey, entry);
      }
      res.set("Content-Type", entry.contentType);
      res.set("Cache-Control", "public, max-age=31536000, immutable");
      return res.send(entry.buf);
    } catch {
      return res.status(500).end();
    }
  });
  // --- FAST_IMG_ROUTE_END ---

  let _brandCache = { exp: 0, data: { name: "ORIGINAL – أوريجنال", icon: "" }, refreshing: false };
  const refreshBrand = () => {
    if (_brandCache.refreshing) return;
    _brandCache.refreshing = true;
    getDb().then(async db => {
      if (!db) { _brandCache.refreshing = false; return; }
      const rows = await db.select({ key: storeSettings.key, value: storeSettings.value }).from(storeSettings).where(eq(storeSettings.key, "storeIconUrl")).limit(1);
      const nameRows = await db.select({ value: storeSettings.value }).from(storeSettings).where(eq(storeSettings.key, "storeName")).limit(1);
      const candidate = rows[0]?.value ?? "";
      const icon = candidate.startsWith("/uploads/") || candidate.startsWith("/manus-storage/") || candidate.startsWith("https://") ? candidate : "";
      _brandCache = { exp: Date.now() + 120_000, data: { name: nameRows[0]?.value || "ORIGINAL – أوريجنال", icon }, refreshing: false };
    }).catch(() => { _brandCache.refreshing = false; });
  };
  setTimeout(refreshBrand, 1000);
  const publicBrand = async () => {
    if (Date.now() > _brandCache.exp) refreshBrand();
    return _brandCache.data;
  };
  app.get("/api/app-manifest.webmanifest", async (_req, res) => {
    const brand = await publicBrand();
    const imagePath = brand.icon ? new URL(brand.icon, "https://app.invalid").pathname : "";
    const type = imagePath.endsWith(".png") ? "image/png" : imagePath.endsWith(".jpg") || imagePath.endsWith(".jpeg") ? "image/jpeg" : imagePath.endsWith(".webp") ? "image/webp" : "image/svg+xml";
    const icons = brand.icon ? [{ src: brand.icon, sizes: "any", type, purpose: "any" }] : [
      { src: "/app-icon-192-v2.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/app-icon-512-v2.png", sizes: "512x512", type: "image/png", purpose: "any maskable" },
    ];
    res.set("Cache-Control", "no-store").type("application/manifest+json").send(JSON.stringify({ id: "/", name: brand.name, short_name: "أوريجنال", description: "متجر ORIGINAL – أوريجنال", lang: "ar", dir: "rtl", start_url: "/", scope: "/", display: "standalone", background_color: "#f8f8f2", theme_color: "#174b36", icons }));
  });
  app.get("/api/store-icon", async (_req, res) => {
    const brand = await publicBrand();
    res.set("Cache-Control", "no-store").redirect(302, brand.icon || "/app-icon-180-v2.png");
  });
  app.get("/api/platform/config.js", (_req, res) => {
    res.set("Cache-Control", "no-store").type("application/javascript").send(publicPlatformScript());
  });
  registerOAuthRoutes(app);
  // tRPC API
  app.use(
    "/api/trpc",
    createExpressMiddleware({
      router: appRouter,
      createContext,
    })
  );
  // development mode uses Vite, production mode uses static files
  if (process.env.NODE_ENV === "development") {
    await setupVite(app, server);
  } else {
    serveStatic(app);
  }

  const port = Number(process.env.PORT || "3000");
  if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error("Invalid PORT");
  server.on("error", error => { console.error("Server failed:", error.message); process.exit(1); });
  server.listen(port, "0.0.0.0", () => console.log(`Server listening on port ${port}`));
}

startServer().catch(error => { console.error(error); process.exit(1); });
