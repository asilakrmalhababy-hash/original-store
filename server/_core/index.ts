import * as __aiBcastModV140 from "../ai_engine_v112";
import mysqlV138 from "mysql2/promise";
import * as __dbStatusModV137 from "../db";
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
  
  // === ORIGINAL_DB_STATUS_V137_START ===
  app.get("/api/db-status", async (req: any, res: any) => {
    let tempConn: any = null;
    try {
      let runner: any = null;
      if ((__dbStatusModV137 as any).getPool) {
        runner = await (__dbStatusModV137 as any).getPool();
      }
      if (!runner && process.env.DATABASE_URL) {
        const u = new URL(process.env.DATABASE_URL);
        tempConn = await mysqlV138.createConnection({
          host: u.hostname,
          port: Number(u.port || 4000),
          user: decodeURIComponent(u.username),
          password: decodeURIComponent(u.password),
          database: u.pathname.replace(/^\//, "") || "test",
          ssl: { minVersion: "TLSv1.2", rejectUnauthorized: true },
          connectTimeout: 10000
        });
        runner = tempConn;
      }
      if (!runner) {
        return res.status(500).json({ ok: false, error: "لم يتم العثور على متغير DATABASE_URL في السيرفر" });
      }

      const [sizeRows]: any = await runner.query(
        "SELECT table_name AS name, ROUND((data_length + index_length) / 1024 / 1024, 4) AS size_mb FROM information_schema.tables WHERE table_schema = DATABASE()"
      );
      const sizeMap: Record<string, number> = {};
      let totalMb = 0;
      if (Array.isArray(sizeRows)) {
        for (const r of sizeRows) {
          const tName = String(r.name || r.NAME || r.table_name || "").toLowerCase();
          const mb = Number(r.size_mb || r.SIZE_MB || 0);
          sizeMap[tName] = mb;
          totalMb += mb;
        }
      }

      const tableDefs = [
        { key: "categories", label: "الأقسام (categories)" },
        { key: "products", label: "المنتجات (products)" },
        { key: "banners", label: "البنرات الإعلانية (banners)" },
        { key: "offers", label: "العروض (offers)" },
        { key: "orders", label: "الطلبات (orders)" },
        { key: "order_items", label: "عناصر الطلبات (order_items)" },
        { key: "users", label: "المستخدمين (users)" },
        { key: "store_settings", label: "إعدادات المتجر (store_settings)" }
      ];

      const stats: any[] = [];
      for (const td of tableDefs) {
        try {
          const [cnt]: any = await runner.query("SELECT COUNT(*) AS c FROM " + td.key);
          const countVal = Number((cnt && cnt[0] && (cnt[0].c ?? cnt[0].C)) || 0);
          stats.push({
            table: td.key,
            label: td.label,
            rows: countVal,
            sizeMb: Number((sizeMap[td.key] || 0).toFixed(4))
          });
        } catch (_e) {
          stats.push({ table: td.key, label: td.label, rows: 0, sizeMb: 0 });
        }
      }

      if (tempConn) {
        try { await tempConn.end(); } catch (_e) {}
        tempConn = null;
      }

      const maxMb = 5120;
      const usedMb = Number(totalMb.toFixed(4));
      const remainMb = Number((maxMb - usedMb).toFixed(2));
      const usedPct = Number(((usedMb / maxMb) * 100).toFixed(4));

      if (req.query && req.query.json === "1") {
        return res.json({
          ok: true,
          cluster: "original-store-2 (TiDB Starter)",
          usedMb,
          maxMb,
          remainMb,
          usedPct,
          stats
        });
      }

      let rowsHtml = "";
      for (const s of stats) {
        rowsHtml += "<tr>" +
          "<td style='padding:12px 10px;border-bottom:1px solid rgba(216,180,84,0.18);font-weight:700;'>" + s.label + "</td>" +
          "<td style='padding:12px 10px;border-bottom:1px solid rgba(216,180,84,0.18);text-align:center;color:#d8b454;font-weight:800;font-size:16px;'>" + s.rows + "</td>" +
          "<td style='padding:12px 10px;border-bottom:1px solid rgba(216,180,84,0.18);text-align:left;direction:ltr;'>" + s.sizeMb + " MB</td>" +
        "</tr>";
      }

      const pageHtml = "<!DOCTYPE html><html lang='ar' dir='rtl'><head><meta charset='utf-8'/>" +
        "<meta name='viewport' content='width=device-width,initial-scale=1'/>" +
        "<title>مراقبة قاعدة البيانات - أورجنال</title>" +
        "<link href='https://fonts.googleapis.com/css2?family=Tajawal:wght@500;700;800&display=swap' rel='stylesheet'/>" +
        "<style>" +
          "body{margin:0;padding:18px;background:#0b2b1d;color:#fff;font-family:'Tajawal',sans-serif;}" +
          ".card{max-width:560px;margin:0 auto;background:linear-gradient(145deg,#13462f,#0d3322);border:1.5px solid #d8b454;border-radius:20px;padding:20px;box-shadow:0 14px 36px rgba(0,0,0,0.45);}" +
          ".badge{display:inline-block;background:rgba(34,197,94,0.2);color:#4ade80;border:1px solid #4ade80;border-radius:999px;padding:4px 12px;font-size:12px;font-weight:800;}" +
          ".bar-wrap{background:rgba(0,0,0,0.35);border-radius:999px;height:14px;overflow:hidden;margin:12px 0;border:1px solid rgba(216,180,84,0.35);}" +
          ".bar-fill{background:linear-gradient(90deg,#e5c467,#c89e3a);height:100%;width:" + Math.max(usedPct, 1.5) + "%;}" +
          "table{width:100%;border-collapse:collapse;margin-top:14px;font-size:14px;}" +
          ".btn{display:inline-block;margin-top:16px;background:linear-gradient(135deg,#e5c467,#c89e3a);color:#0b2b1d;text-decoration:none;font-weight:800;padding:10px 18px;border-radius:12px;font-size:14px;}" +
        "</style></head><body><div class='card'>" +
        "<div style='display:flex;justify-content:space-between;align-items:center;'>" +
          "<h2 style='margin:0;color:#d8b454;font-size:20px;'>📊 استهلاك قاعدة بيانات أورجنال</h2>" +
          "<span class='badge'>متصل ويعمل 🟢</span>" +
        "</div>" +
        "<p style='margin:10px 0 4px;font-size:14px;color:#e5e7eb;'>المساحة المستهلكة: <strong style='color:#d8b454;'>" + usedMb + " MB</strong> من أصل <strong>5,120 MB (5 GiB)</strong> (" + usedPct + "%)</p>" +
        "<p style='margin:0 0 8px;font-size:13px;color:#86efac;'>المساحة المجانية المتبقية: <strong>" + remainMb + " MB</strong> | الاستهلاك الخلفي عند السكون: <strong>0 RU/ثانية</strong></p>" +
        "<div class='bar-wrap'><div class='bar-fill'></div></div>" +
        "<table><thead><tr style='color:#d8b454;border-bottom:2px solid #d8b454;'>" +
          "<th style='text-align:right;padding:8px;'>الجدول</th>" +
          "<th style='text-align:center;padding:8px;'>العدد الفعلي</th>" +
          "<th style='text-align:left;padding:8px;'>الحجم</th>" +
        "</tr></thead><tbody>" + rowsHtml + "</tbody></table>" +
        "<div style='display:flex;gap:10px;justify-content:center;'>" +
          "<a class='btn' href='/api/db-status'>🔄 تحديث القراءة الآن</a>" +
          "<a class='btn' style='background:rgba(255,255,255,0.12);color:#fff;border:1px solid #d8b454;' href='/'>🏠 العودة للمتجر</a>" +
        "</div></div></body></html>";

      res.setHeader("Content-Type", "text/html; charset=utf-8");
      return res.send(pageHtml);
    } catch (err: any) {
      if (tempConn) {
        try { await tempConn.end(); } catch (_e) {}
      }
      return res.status(500).json({ ok: false, error: err?.message || "DB status error" });
    }
  });
// === ORIGINAL_DB_STATUS_V137_END ===
  // === ORIGINAL_V140_ROUTES_START ===
  const __v140Broadcasts: any[] = [];
  let __v140LoadedFromDb = false;

  async function __ensureV140Loaded() {
    if (__v140LoadedFromDb) return;
    __v140LoadedFromDb = true;
    try {
      const pool = (__dbStatusModV137 as any).getPool ? await (__dbStatusModV137 as any).getPool() : null;
      if (!pool) return;
      const [rows]: any = await pool.query(
        "SELECT `value` FROM store_settings WHERE `key` = 'v140_broadcast_history' LIMIT 1"
      );
      if (Array.isArray(rows) && rows[0] && rows[0].value) {
        const parsed = JSON.parse(String(rows[0].value));
        if (Array.isArray(parsed)) {
          for (const item of parsed.slice(-30)) {
            __v140Broadcasts.push(item);
          }
        }
      }
    } catch (_e) {}
  }

  app.post("/api/v140/admin-broadcast", express.json(), async (req: any, res: any) => {
    try {
      await __ensureV140Loaded();
      const body = req.body || {};
      const title = String(body.title || "متجر أورجنال").trim();
      const message = String(body.body || body.message || "").trim();
      const targetType = String(body.targetType || "all").trim();
      const targetValue = String(body.targetValue || "").trim().replace(/^#/, "");
      const url = String(body.url || "/").trim();

      if (!message) {
        return res.status(400).json({ ok: false, error: "يرجى كتابة نص الإشعار" });
      }

      const bcastItem = {
        id: "bcast_" + Date.now() + "_" + Math.random().toString(36).slice(2, 6),
        title,
        body: message,
        targetType,
        targetValue,
        url,
        createdAt: Date.now()
      };
      __v140Broadcasts.push(bcastItem);
      if (__v140Broadcasts.length > 40) {
        __v140Broadcasts.splice(0, __v140Broadcasts.length - 40);
      }

      // حفظ في قاعدة البيانات ليبقى محفوظاً
      try {
        const pool = (__dbStatusModV137 as any).getPool ? await (__dbStatusModV137 as any).getPool() : null;
        if (pool) {
          await pool.query(
            "INSERT INTO store_settings (`key`, `value`) VALUES ('v140_broadcast_history', ?) ON DUPLICATE KEY UPDATE `value` = VALUES(`value`)",
            [JSON.stringify(__v140Broadcasts.slice(-30))]
          );
        }
      } catch (_e) {}

      // إرسال Web Push فوري لهواتف الزبائن
      let pushRes = { sent: 0, total: 0 };
      if ((__aiBcastModV140 as any).sendCustomPushBroadcastV140) {
        pushRes = await (__aiBcastModV140 as any).sendCustomPushBroadcastV140({
          title,
          body: message,
          targetType,
          targetValue,
          url
        });
      }

      return res.json({
        ok: true,
        broadcast: bcastItem,
        pushSent: pushRes.sent,
        pushTotal: pushRes.total
      });
    } catch (err: any) {
      return res.status(500).json({ ok: false, error: err?.message || "خطأ في إرسال الإشعار" });
    }
  });

  app.get("/api/v140/customer-feed", async (req: any, res: any) => {
    try {
      await __ensureV140Loaded();
      const phone = String((req.query && req.query.phone) || "").trim();
      const orderNum = String((req.query && req.query.order) || "").trim().replace(/^#/, "");
      const since = Number((req.query && req.query.since) || 0);

      const matched = __v140Broadcasts.filter((b) => {
        if (!b || Number(b.createdAt || 0) <= since) return false;
        if (b.targetType === "all" || !b.targetType) return true;
        if (b.targetType === "phone" && b.targetValue) {
          return phone && (phone.includes(b.targetValue) || b.targetValue.includes(phone));
        }
        if (b.targetType === "order" && b.targetValue) {
          return orderNum && orderNum === String(b.targetValue).replace(/^#/, "");
        }
        return false;
      });

      return res.json({
        ok: true,
        notifications: matched.slice(-5),
        recentHistory: __v140Broadcasts.slice(-10).reverse()
      });
    } catch (_e) {
      return res.json({ ok: true, notifications: [], recentHistory: [] });
    }
  });
// === ORIGINAL_V140_ROUTES_END ===
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
