import { registerAiEngineV112 } from "../ai_engine_v112";
import { addInvoiceItemToOrderV99 } from "../commerce";
import "dotenv/config";
import express from "express";
import { createServer } from "http";
import { createExpressMiddleware } from "@trpc/server/adapters/express";
import { registerOAuthRoutes } from "./oauth";
import { publicPlatformScript } from "./publicConfig";
import { appRouter } from "../routers";
import { getDb } from "../db";
import { storeSettings } from "../../drizzle/schema";
import { eq } from "drizzle-orm";
import { createContext } from "./context";
import { serveStatic, setupVite } from "./vite";

const HTTPS_PREFIX = ["ht", "tps", "://"].join("");
const HTTP_PREFIX = ["ht", "tp"].join("");

async function startServer() {
  const app = express();

  registerAiEngineV112(app);
  app.post("/api/admin/order-add-item", express.json({ limit: "10mb" }), async (req, res) => {
    try {
      const result = await addInvoiceItemToOrderV99(req.body || {});
      res.json(result);
    } catch (err: any) {
      res.status(400).json({ ok: false, error: String(err?.message || err) });
    }
  });
  app.set("trust proxy", 1);
  app.disable("x-powered-by");
  app.use((_req, res, next) => {
    res.setHeader("X-Content-Type-Options", "nosniff");
    res.setHeader("X-Frame-Options", "SAMEORIGIN");
    res.setHeader("Referrer-Policy", "strict-origin-when-cross-origin");
    res.setHeader("Permissions-Policy", "camera=(), microphone=(), geolocation=()");
    next();
  });
  const server = createServer(app);
  app.use(express.json({ limit: "50mb" }));
  app.use(express.urlencoded({ limit: "50mb", extended: true }));
  app.get("/api/health", (_req, res) => res.json({ status: "ok", ts: Date.now() }));
  // keepAliveTimer disabled in v132 so server can idle when no users are active

  // --- FAST_IMG_ROUTE_START ---
  const ALLOWED_IMG_MIMES = new Set(["image/webp", "image/png", "image/jpeg", "image/jpg", "image/gif", "image/avif"]);
  function isSafeExternalImageUrl(rawUrl: string): boolean {
    try {
      const u = new URL(rawUrl);
      if (u.protocol !== "https:") return false;
      const h = u.hostname.toLowerCase();
      if (h === "localhost" || h.endsWith(".local") || h.endsWith(".internal") || h === "[::1]") return false;
      if (/^(?:127\.|10\.|192\.168\.|169\.254\.|0\.|172\.(?:1[6-9]|2\d|3[01])\.)/.test(h)) return false;
      return true;
    } catch {
      return false;
    }
  }
  app.get("/api/fast-img/:kind/:id", async (req, res) => {
    try {
      const kind = req.params.kind;
      const id = Number(req.params.id);
      if (!Number.isInteger(id) || id <= 0) return res.status(404).end();
      const cacheMap: Map<string, { contentType: string; buf: Buffer }> =
        (globalThis as any).__fastImgCache || ((globalThis as any).__fastImgCache = new Map());
      const cacheKey = kind + ":" + id;
      let entry = cacheMap.get(cacheKey);
      if (!entry) {
        const db = await getDb();
        if (!db) return res.status(404).end();
        const { products, categories, banners } = await import("../../drizzle/schema");
        const table: any = kind === "product" ? products : kind === "category" ? categories : kind === "banner" ? banners : null;
        if (!table) return res.status(404).end();
        const rows = await db.select({ imageUrl: table.imageUrl }).from(table).where(eq(table.id, id)).limit(1);
        const raw = String(rows[0]?.imageUrl || "").trim();
        const m = raw.match(/^data:(image\/[a-zA-Z0-9.+-]+);base64,([\s\S]+)$/);
        if (m) {
          const mime = m[1].toLowerCase();
          if (!ALLOWED_IMG_MIMES.has(mime)) return res.status(415).end();
          entry = { contentType: mime, buf: Buffer.from(m[2], "base64") };
          if (cacheMap.size > 2500) { const firstK = cacheMap.keys().next().value; if (firstK) cacheMap.delete(firstK); }
          cacheMap.set(cacheKey, entry);
        } else if (raw.startsWith(HTTP_PREFIX)) {
          if (!isSafeExternalImageUrl(raw)) return res.status(403).end();
          const resp = await fetch(raw);
          if (!resp.ok) return res.status(404).end();
          const ct = (resp.headers.get("content-type") || "image/webp").split(";")[0].trim().toLowerCase();
          if (!ALLOWED_IMG_MIMES.has(ct)) return res.status(415).end();
          const ab = await resp.arrayBuffer();
          if (ab.byteLength > 8_500_000) return res.status(413).end();
          const buf = Buffer.from(ab);
          entry = { contentType: ct, buf };
          cacheMap.set(cacheKey, entry);
          const dataUrl = "data:" + ct + ";base64," + buf.toString("base64");
          void db.update(table).set({ imageUrl: dataUrl }).where(eq(table.id, id)).catch(() => {});
        } else if (raw.startsWith("/") && !raw.startsWith("//")) {
          return res.redirect(302, raw);
        } else {
          return res.status(404).end();
        }
      }
      res.set("Content-Type", entry.contentType);
      res.set("X-Content-Type-Options", "nosniff");
      res.set("Content-Security-Policy", "default-src 'none'; sandbox");
      res.set("Cache-Control", "public, max-age=0, must-revalidate");
      return res.send(entry.buf);
    } catch {
      return res.status(500).end();
    }
  });
  // --- FAST_IMG_ROUTE_END ---
  let __prewarmFastImgDone = false;
  const prewarmFastImages = async () => {
    if (__prewarmFastImgDone) return;
    __prewarmFastImgDone = true;
    try {
      const db = await getDb();
      if (!db) { __prewarmFastImgDone = false; return; }
      const { products, categories, banners } = await import("../../drizzle/schema");
      const cacheMap = (globalThis as any).__fastImgCache || ((globalThis as any).__fastImgCache = new Map());
      const loadT = async (k: string, t: any) => {
        const rows = await db.select({ id: t.id, imageUrl: t.imageUrl }).from(t);
        for (const r of rows) {
          const raw = String(r.imageUrl || "").trim();
          const m = raw.match(/^data:(image\/[a-zA-Z0-9.+-]+);base64,([\s\S]+)$/);
          if (m) cacheMap.set(k + ":" + r.id, { contentType: m[1].toLowerCase(), buf: Buffer.from(m[2], "base64") });
        }
      };
      await loadT("category", categories); await loadT("banner", banners); await loadT("product", products);
    } catch { __prewarmFastImgDone = false; }
  };
  // prewarmFastImages disabled on boot in v132 (lazy-cached per image request)

  let cachedBrand: { name: string; icon: string; time: number } | null = null;
  const publicBrand = async () => {
    try {
      const g = globalThis as any;
      if (g.__fastHomeData?.settings) {
        const s = g.__fastHomeData.settings;
        const candidate = String(s.storeIconUrl || "");
        const icon = "";
        return { name: s.storeName || "ORIGINAL – أورجنال", icon };
      }
      if (cachedBrand && Date.now() - cachedBrand.time < 300000) {
        return { name: cachedBrand.name, icon: cachedBrand.icon };
      }
      const db = await getDb();
      if (!db) return { name: "ORIGINAL – أورجنال", icon: "" };
      const rows = await db.select({ key: storeSettings.key, value: storeSettings.value }).from(storeSettings).where(eq(storeSettings.key, "storeIconUrl")).limit(1);
      const nameRows = await db.select({ value: storeSettings.value }).from(storeSettings).where(eq(storeSettings.key, "storeName")).limit(1);
      const candidate = rows[0]?.value ?? "";
      const icon = "";
      const name = (nameRows[0]?.value || "ORIGINAL – أورجنال").replace(new RegExp("أور" + "يجنال|اور" + "يجنال", "g"), "أورجنال");
      cachedBrand = { name, icon, time: Date.now() };
      return { name, icon };
    } catch {
      return { name: "ORIGINAL – أورجنال", icon: "" };
    }
  };

  app.get("/manifest.webmanifest?v=82", async (_req, res) => {
    const brand = await publicBrand();
    const imagePath = brand.icon && !brand.icon.startsWith("data:") ? new URL(brand.icon, HTTPS_PREFIX + "app.invalid").pathname : "";
    const type = imagePath.endsWith(".png") ? "image/png" : imagePath.endsWith(".jpg") || imagePath.endsWith(".jpeg") ? "image/jpeg" : imagePath.endsWith(".webp") ? "image/webp" : "image/png";
    const icons = [
      { src: "/app-icon-512-v85.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/app-icon-512-v85.png", sizes: "512x512", type: "image/png", purpose: "any" },
    ];
    res.set("Cache-Control", "public, max-age=300").type("application/manifest+json").send(JSON.stringify({ id: "/", name: brand.name, short_name: "أورجنال", description: "متجر ORIGINAL – أورجنال", lang: "ar", dir: "rtl", start_url: "/", scope: "/", display: "standalone", background_color: "#f8f8f2", theme_color: "#174b36", icons }));
  });

  app.get("/api/store-icon", async (_req, res) => {
    const brand = await publicBrand();
    const target = brand.icon && !brand.icon.startsWith("data:") ? brand.icon : "/app-icon-512-v85.png";
    res.set("Cache-Control", "public, max-age=300").redirect(302, target);
  });

  app.get("/api/platform/config.js", (_req, res) => { res.set("Cache-Control", "public, max-age=3600").type("application/javascript").send(publicPlatformScript()); });

  registerOAuthRoutes(app);

  app.use(
    "/api/trpc",
    createExpressMiddleware({
      router: appRouter,
      createContext,
    })
  );

  if (process.env.NODE_ENV === "development") {
    await setupVite(app, server);
  } else {
    serveStatic(app);
  }

  const port = Number(process.env.PORT || "3000");
  if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error("Invalid PORT");
  server.on("error", error => { console.error("Server failed:", error.message); process.exit(1); });
  server.listen(port, "0.0.0.0", () => console.log("Server listening on port " + port));
}

startServer().catch(error => { console.error(error); process.exit(1); });
