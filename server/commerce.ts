
let __cachedLiveHomeData: any = null;
let __lastLiveHomeDataTime = 0;
function clearLiveHomeCache() {
  __cachedLiveHomeData = null;
  __lastLiveHomeDataTime = 0;
}

import fs from "node:fs";
import { createHash } from "node:crypto";
import { and, asc, desc, eq, gt, inArray, like, or, sql } from "drizzle-orm";
import { z } from "zod";
import { storagePut } from "./storage";
import { getDb, resetDbPool } from "./db";
import {
  addresses,
  banners,
  categories,
  customerPushSubscriptions,
  favorites,
  orderEvents,
  orderItems,
  orders,
  offers,
  ownerPushSubscriptions,
  productRecommendations,
  products,
  storeSettings,
  users,
} from "../drizzle/schema";
import { adminAuditLogs, adminStaff } from "../drizzle/schema";
import { adminProcedure, protectedProcedure, publicProcedure, requireAnyPermission, requirePermission, router } from "./_core/trpc";
import { PERMISSION_KEYS, ROLE_DEFINITIONS, ROLE_KEYS, canManageTargetStaff, hasPermission, parsePermissionsJson, type AdminRoleKey, type PermissionKey } from "@shared/rbac";
import { ensureRbacTables, getClientIp, hashAdminPassword, verifyAdminPassword, writeAdminAuditLog } from "./_core/adminAuth";
import { COOKIE_NAME } from "@shared/const";
import { getSessionCookieOptions } from "./_core/cookies";
import { sdk } from "./_core/sdk";
import { TRPCError } from "@trpc/server";
import { nanoid } from "nanoid";
import { invokeLLM } from "./_core/llm";
import { hashGuestOrderKey, isValidGuestPhone, matchesGuestOrderKey } from "./guest-orders";
import {
  getWebPushPublicKey,
  isAllowedPushEndpoint,
  protectPushSubscription,
  sendWebPush,
  unprotectPushSubscription,
  type PushMessage,
} from "./_core/webPush";
import {
  assistantResponseJsonSchema,
  parseAssistantModelContent,
  prepareAssistantResponse,
  type AssistantCatalogProduct,
  type AssistantModelOutput,
} from "./assistant";

async function database() {
  const db = await getDb();
  if (!db) throw new TRPCError({ code: "SERVICE_UNAVAILABLE", message: "قاعدة البيانات غير متاحة مؤقتًا." });
  return db;
}

const CACHE_FILE = ".catalog-cache.json";
const __catalogCache = new Map<string, { exp: number; data: any; refreshing?: boolean }>();
try {
  if (fs.existsSync(CACHE_FILE)) {
    const raw = JSON.parse(fs.readFileSync(CACHE_FILE, "utf8"), (k, val) =>
      (k === "createdAt" || k === "updatedAt" || k === "startsAt" || k === "endsAt" || k === "lastOrderAt" || k === "lastSignedIn") && typeof val === "string" ? new Date(val) : val
    );
    for (const [k, v] of Object.entries(raw)) __catalogCache.set(k, { exp: 0, data: v, refreshing: false });
  }
} catch {}
function saveDiskCache() {
  try {
    const obj: Record<string, any> = {};
    for (const [k, v] of __catalogCache.entries()) obj[k] = v.data;
    fs.writeFileSync(CACHE_FILE, JSON.stringify(obj));
  } catch {}
}
async function withFastRetry<T>(fetcher: () => Promise<T>): Promise<T> {
  let timer: NodeJS.Timeout | null = null;
  try {
    return await Promise.race([
      fetcher(),
      new Promise<T>((_, reject) => { timer = setTimeout(() => reject(new Error("QUERY_TIMEOUT")), 5500); }),
    ]);
  } catch (err) {
    resetDbPool();
    return await fetcher();
  } finally {
    if (timer) clearTimeout(timer);
  }
}
function getCached<T>(key: string, ttlMs: number, fetcher: () => Promise<T>): Promise<T> {
  const now = Date.now();
  const hit = __catalogCache.get(key);
  if (hit) {
    if (hit.exp <= now && !hit.refreshing) {
      hit.refreshing = true;
      withFastRetry(fetcher)
        .then(data => {
          __catalogCache.set(key, { exp: Date.now() + ttlMs, data, refreshing: false });
          saveDiskCache();
        })
        .catch(() => { hit.refreshing = false; });
    }
    return Promise.resolve(hit.data as T);
  }
  return withFastRetry(fetcher).then(data => {
    __catalogCache.set(key, { exp: Date.now() + ttlMs, data, refreshing: false });
    saveDiskCache();
    return data;
  });
}
function clearCatalogCache() {
  try { const g = globalThis as any; g.__fastHomeData = null; g.__fastHomeTime = 0; g.__catalogVer = Date.now(); if (typeof g.__loadCatalogHome === "function") { setTimeout(() => { void g.__loadCatalogHome().catch(() => {}); }, 10); } } catch {}
  __catalogCache.clear();
  try { if (fs.existsSync(CACHE_FILE)) fs.unlinkSync(CACHE_FILE); } catch {}
}


const AI_PRODUCT_CACHE_FILE = ".ai-product-recipes.json";
let __aiProductRecipes: Record<string, AssistantModelOutput> = {};
try {
  if (fs.existsSync(AI_PRODUCT_CACHE_FILE)) {
    __aiProductRecipes = JSON.parse(fs.readFileSync(AI_PRODUCT_CACHE_FILE, "utf8"));
  }
} catch {}

function saveAiProductRecipe(cacheKey: string, output: AssistantModelOutput) {
  const key = cacheKey.trim().toLowerCase();
  __aiProductRecipes[key] = output;
  try {
    fs.writeFileSync(AI_PRODUCT_CACHE_FILE, JSON.stringify(__aiProductRecipes, null, 2));
  } catch {}
}

async function generateAndCacheProductAiRecipe(
  productName: string,
  catalog: AssistantCatalogProduct[],
  customModification?: string,
): Promise<AssistantModelOutput | null> {
  const cacheKey = customModification
    ? `${productName.trim().toLowerCase()}::${customModification.trim().toLowerCase()}`
    : `${productName.trim().toLowerCase()}::init-v3`;

  if (__aiProductRecipes[cacheKey]) return __aiProductRecipes[cacheKey];

  const compactCatalog = catalog.slice(0, 50).map(p => ({ id: p.id, name: p.name, price: p.price, unit: p.unit }));
  const sys = "أنت المساعد الذكي لمتجر أوريجنال في اليمن. حلل طبيعة المنتج أولاً بلهجة يمنية راقية وودودة، وإذا لم يكن منتج طبخ قدم معلومات ذكية عنه ولا تفرض وصفات طبخ، ثم اعرض في النهاية اقتراحات تفاعلية في حقل suggestedQuestions.";
  const usr = [
    `الصنف الأساسي: «${productName}»`,
    customModification ? `طلب التعديل الخاص من الزبون: ${customModification}` : "المطلوب: تحليل ذكي للمنتج ومعلومات عنه مع اقتراحات تفاعلية.",
    `كتالوج المتجر الحالي: ${JSON.stringify(compactCatalog)}`,
  ].join("\n\n");

  const res = await invokeLLM({
    messages: [
      { role: "system", content: sys },
      { role: "user", content: usr },
    ],
    response_format: { type: "json_object" },
  });

  const parsed = parseAssistantModelContent(res.choices?.[0]?.message?.content);
  if (parsed && parsed.message) {
    saveAiProductRecipe(cacheKey, parsed);
    return parsed;
  }
  return null;
}

const pushSubscriptionSchema = z.object({
  endpoint: z.string().url().max(2048),
  keys: z.object({
    p256dh: z.string().min(20).max(200).regex(/^[A-Za-z0-9_+/=-]+$/),
    auth: z.string().min(10).max(100).regex(/^[A-Za-z0-9_+/=-]+$/),
  }),
});

async function deliverPushRows(
  rows: Array<{ id: number; encryptedPayload: string }>,
  message: PushMessage,
  remove: (id: number) => Promise<void>,
) {
  await Promise.allSettled(rows.map(async row => {
    let subscription;
    try {
      subscription = unprotectPushSubscription(row.encryptedPayload);
    } catch {
      await remove(row.id);
      return;
    }
    try {
      await sendWebPush(subscription, message);
      console.log("[Push] Web Push sent:", message.title);
    } catch (error) {
      const statusCode = error && typeof error === "object" && "statusCode" in error
        ? Number(error.statusCode)
        : undefined;
      if (statusCode === 404 || statusCode === 410) await remove(row.id);
      console.warn("[Push] Delivery failed", statusCode ?? "network");
    }
  }));
}

async function notifyOwnerNewOrder(orderId: number, orderNumber: string, total: number) {
  const db = await database();
  const subscriptions = await db.select({ id: ownerPushSubscriptions.id, encryptedPayload: ownerPushSubscriptions.encryptedPayload })
    .from(ownerPushSubscriptions);
  await deliverPushRows(subscriptions, {
    title: "طلب جديد في أوريجنال",
    body: `وصل الطلب ${orderNumber} بإجمالي ${total.toLocaleString("en-US")} ر.ي.`,
    url: "/admin/orders",
    tag: `original-new-order-${orderId}`,
  }, async id => { await db.delete(ownerPushSubscriptions).where(eq(ownerPushSubscriptions.id, id)); });
}

async function notifyCustomerOrderStatus(orderId: number, orderNumber: string, status: string, note?: string) {
  const db = await database();
  const subscriptions = await db.select({ id: customerPushSubscriptions.id, encryptedPayload: customerPushSubscriptions.encryptedPayload })
    .from(customerPushSubscriptions).where(eq(customerPushSubscriptions.orderId, orderId));
  const labels: Record<string, string> = {
    new: "تم استلام الطلب",
    preparing: "طلبك قيد التجهيز",
    ready: "طلبك جاهز للتوصيل",
    out_for_delivery: "خرج طلبك للتوصيل",
    delivered: "تم تسليم طلبك",
    cancelled: "تم إلغاء الطلب",
  };
  await deliverPushRows(subscriptions, {
    title: `تحديث الطلب ${orderNumber}`,
    body: `${labels[status] ?? "تغيرت حالة طلبك"}${note ? ` · ${note.slice(0, 220)}` : ""}`,
    url: "/orders",
    tag: `original-order-status-${orderId}-${status}`,
  }, async id => { await db.delete(customerPushSubscriptions).where(eq(customerPushSubscriptions.id, id)); });
}

const orderStatus = z.enum(["new", "preparing", "ready", "out_for_delivery", "delivered", "cancelled"]);
const safeId = z.number().int().positive();
const settingSchema = z.object({
  storeName: z.string().trim().max(100).optional(),
  storeDescription: z.string().trim().max(500).optional(),
  contactPhone: z.string().trim().max(32).optional(),
  currency: z.string().trim().max(20).optional(),
  storeIconUrl: z.string().max(8500000).nullable().optional(),
  deliveryEnabled: z.boolean().optional(),
  deliveryFee: z.number().int().min(0).max(100000000).nullable().optional(),
  minOrderAmount: z.number().int().min(0).max(100000000).nullable().optional(),
  deliveryZones: z.array(z.object({ name: z.string().trim().min(1).max(100), fee: z.number().int().min(0).max(100000000), enabled: z.boolean() })).max(100).optional(),
  orderPaused: z.boolean().optional(),
  pausedMessage: z.string().trim().max(300).optional(),
  rewardsThreshold: z.number().int().min(0).max(100000000).nullable().optional(),
  rewardsMessage: z.string().trim().max(300).optional(),
  rewardEnabled: z.boolean().optional(),
  rewardType: z.enum(["free_delivery", "discount_percent"]).optional(),
  rewardValue: z.number().int().min(0).max(100).optional(),
});

function slugify(value: string) {
  const slug = value.trim().toLowerCase().replace(/[^\p{L}\p{N}]+/gu, "-").replace(/^-|-$/g, "").slice(0, 160);
  return `${slug || "item"}-${nanoid(5).toLowerCase()}`;
}

async function readSettings(db: NonNullable<Awaited<ReturnType<typeof getDb>>>) {
  const rows = await db.select({ key: storeSettings.key, value: storeSettings.value }).from(storeSettings).catch(err => { console.error("[store_settings error]:", err); return []; });
  const settings: Record<string, string> = {};
  for (const row of rows) { if (row.key === "live_ai_chats_v1") continue; settings[row.key] = row.value; }
  return settings;
}

function deliveryFeeForCity(settings: Record<string, string>, city: string): number | null {
  if (settings.deliveryEnabled === "false") return null;
  if (settings.deliveryZones) {
    try {
      const zones = JSON.parse(settings.deliveryZones) as Array<{ name: string; fee: number; enabled: boolean }>;
      const zone = zones.find(item => item.enabled && item.name.trim().toLocaleLowerCase() === city.trim().toLocaleLowerCase());
      if (zone && Number.isInteger(zone.fee) && zone.fee >= 0) return zone.fee;
    } catch { /* malformed zone data falls through to a configured base fee */ }
  }
  if (settings.deliveryFee === undefined || settings.deliveryFee === "") return 0;
  const baseFee = Number(settings.deliveryFee);
  return Number.isInteger(baseFee) && baseFee >= 0 ? baseFee : 0;
}

function orderTotals(subtotal: number, deliveryFee: number, offer: typeof offers.$inferSelect | null, settings: Record<string, string>) {
  let discount = 0;
  if (offer) {
    if (subtotal < offer.minimumOrder) throw new TRPCError({ code: "PRECONDITION_FAILED", message: `الحد الأدنى لهذا العرض ${offer.minimumOrder.toLocaleString("en-US")} ر.ي.` });
    discount = offer.discountType === "percent" ? Math.floor(subtotal * offer.discountValue / 100) : offer.discountValue;
    discount = Math.min(discount, subtotal);
  }
  let effectiveDeliveryFee = deliveryFee;
  const threshold = Number(settings.rewardsThreshold ?? "");
  if (settings.rewardEnabled === "true" && Number.isFinite(threshold) && threshold > 0 && subtotal >= threshold) {
    if (settings.rewardType === "free_delivery") effectiveDeliveryFee = 0;
    if (settings.rewardType === "discount_percent") {
      const percent = Number(settings.rewardValue ?? "");
      if (Number.isFinite(percent) && percent > 0) discount = Math.min(subtotal, discount + Math.floor(subtotal * Math.min(percent, 100) / 100));
    }
  }
  return { subtotal, deliveryFee: effectiveDeliveryFee, discount, total: subtotal + effectiveDeliveryFee - discount };
}

function aggregateItems(items: Array<{ productId: number; quantity: number }>) {
  const quantities = new Map<number, number>();
  for (const item of items) quantities.set(item.productId, (quantities.get(item.productId) ?? 0) + item.quantity);
  return [...quantities.entries()].map(([productId, quantity]) => ({ productId, quantity })).sort((a, b) => a.productId - b.productId);
}

function quoteFingerprint(lines: Array<{ productId: number; name: string; quantity: number; unit: string; price: number; lineTotal: number }>, totals: { subtotal: number; deliveryFee: number; discount: number; total: number }, currency: string, offerId: number | null) {
  return createHash("sha256").update(JSON.stringify({ lines, totals, currency, offerId })).digest("hex");
}

const assistantRateWindows = new Map<string, { startedAt: number; count: number }>();
function enforceAssistantRateLimit(key: string) {
  const now = Date.now();
  if (assistantRateWindows.size > 5000) {
    for (const [entryKey, entry] of assistantRateWindows) if (now - entry.startedAt >= 60_000) assistantRateWindows.delete(entryKey);
  }
  const current = assistantRateWindows.get(key);
  if (!current || now - current.startedAt >= 60_000) { assistantRateWindows.set(key, { startedAt: now, count: 1 }); return; }
  if (current.count >= 200) throw new TRPCError({ code: "TOO_MANY_REQUESTS", message: "وصلت إلى حد المحادثة المؤقت. حاول مجددًا بعد دقيقة؛ ويمكنك متابعة التسوق من الأقسام." });
  current.count += 1;
}
function isDuplicateEntry(error: unknown) {
  if (!error || typeof error !== "object") return false;
  const dbError = error as { code?: unknown; errno?: unknown };
  return dbError.code === "ER_DUP_ENTRY" || dbError.errno === 1062;
}

const categoryInput = z.object({
  name: z.string().trim().min(1).max(120),
  description: z.string().trim().max(2000).optional().nullable(),
  imageUrl: z.string().max(8500000).optional().nullable(),
  color: z.string().regex(/^#[0-9a-fA-F]{6}$/).default("#397a54"),
  isActive: z.boolean().default(true),
  sortOrder: z.number().int().min(-10000).max(10000).default(0),
});

const productInput = z.object({
  name: z.string().trim().min(1).max(180),
  description: z.string().trim().max(5000).optional().nullable(),
  imageUrl: z.string().max(8500000).optional().nullable(),
  categoryId: safeId.nullable().optional(),
  price: z.number().int().min(0).max(100000000),
  unit: z.string().trim().min(1).max(40),
  stock: z.number().int().min(0).max(100000000).nullable().optional(),
  minQuantity: z.number().int().min(1).max(1000000).default(1),
  quantityStep: z.number().int().min(1).max(1000000).default(1),
  isPublished: z.boolean().default(false),
  isAvailable: z.boolean().default(true),
  sortOrder: z.number().int().min(-10000).max(10000).default(0),
});

// --- LIVE_CHAT_STORE_START ---
export type LiveChatMsg = { id: string; role: "user" | "assistant" | "owner"; sender: string; text: string; createdAt: string };
export type LiveChatSession = { sessionId: string; customerName: string; customerPhone: string; aiPaused: boolean; updatedAt: string; messages: LiveChatMsg[] };
const liveChatsMemory = new Map<string, LiveChatSession>();
let liveChatsLoaded = false;

async function loadLiveChats(db: any) {
  if (liveChatsLoaded || !db) return;
  liveChatsLoaded = true;
  try {
    const rows = await db.select().from(storeSettings).where(eq(storeSettings.key, "live_ai_chats_v1")).limit(1);
    if (rows[0]?.value) {
      const parsed = JSON.parse(rows[0].value) as LiveChatSession[];
      if (Array.isArray(parsed)) {
        for (const s of parsed) if (s?.sessionId) liveChatsMemory.set(s.sessionId, s);
      }
    }
  } catch {}
}

async function saveLiveChats(db: any) {
  if (!db) return;
  try {
    const arr = [...liveChatsMemory.values()]
      .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())
      .slice(0, 60)
      .map(s => ({ ...s, messages: s.messages.slice(-50) }));
    const stored = JSON.stringify(arr);
    await db.insert(storeSettings).values({ key: "live_ai_chats_v1", value: stored }).onDuplicateKeyUpdate({ set: { value: stored } });
  } catch {}
}
// --- LIVE_CHAT_STORE_END ---
// --- FAST_IMG_HELPER_START ---
const HTTP_PRE = ["ht", "tp"].join("");
function toFastImg<T extends { id: number; imageUrl?: string | null; updatedAt?: Date | string | null }>(kind: "product" | "category" | "banner", row: T): T {
  if (!row || !row.imageUrl) return row;
  const raw = String(row.imageUrl).trim();
  if (!raw || raw.startsWith("/api/fast-img/")) return row;
  try {
    const cacheMap: Map<string, { contentType: string; buf: Buffer }> = (globalThis as any).__fastImgCache || ((globalThis as any).__fastImgCache = new Map());
    const cacheKey = kind + ":" + row.id;
    const ver = row.updatedAt ? new Date(row.updatedAt).getTime() : ((globalThis as any).__catalogVer || 1);
    if (raw.startsWith("data:image/")) {
      const m = raw.match(/^data:(image\/[a-zA-Z0-9.+-]+);base64,([\s\S]+)$/);
      if (m) cacheMap.set(cacheKey, { contentType: m[1], buf: Buffer.from(m[2], "base64") });
      return { ...row, imageUrl: "/api/fast-img/" + kind + "/" + row.id + "?v=" + ver };
    }
    if (raw.startsWith(HTTP_PRE)) {
      if (!cacheMap.has(cacheKey)) {
        void fetch(raw).then(async r => {
          if (r.ok) {
            const ct = r.headers.get("content-type") || "image/webp";
            const ab = await r.arrayBuffer();
            cacheMap.set(cacheKey, { contentType: ct, buf: Buffer.from(ab) });
          }
        }).catch(() => {});
      }
      return { ...row, imageUrl: "/api/fast-img/" + kind + "/" + row.id + "?v=" + ver };
    }
    return row;
  } catch {
    return row;
  }
}

let __refreshingHomePromise: Promise<any> | null = null;
async function refreshHomeCatalogCache() {
  if (__refreshingHomePromise) return __refreshingHomePromise;
  __refreshingHomePromise = (async () => {
    try {
      const db = await database();
      const [categoryRows, productRows, bannerRows, offerRows, settings] = await Promise.all([
        db.select().from(categories).where(eq(categories.isActive, true)).orderBy(asc(categories.sortOrder), asc(categories.id)),
        db.select().from(products).where(and(eq(products.isPublished, true), eq(products.isAvailable, true))).orderBy(asc(products.sortOrder), desc(products.createdAt)).limit(120),
        db.select().from(banners).where(and(eq(banners.isActive, true))).orderBy(asc(banners.sortOrder), desc(banners.createdAt)),
        db.select().from(offers).where(and(eq(offers.isActive, true))).orderBy(desc(offers.createdAt)),
        readSettings(db),
      ]);
      const validBanners = bannerRows.filter(b => Boolean(b.imageUrl && b.imageUrl.trim()));
      const g = globalThis as any;
      g.__fastHomeData = {
        categories: categoryRows.map(r => toFastImg("category", r)),
        products: productRows.map(r => toFastImg("product", r)),
        banners: validBanners.map(r => toFastImg("banner", r)),
        offers: offerRows,
        settings,
      };
      g.__fastHomeTime = Date.now();
      return g.__fastHomeData;
    } finally {
      __refreshingHomePromise = null;
    }
  })();
  return __refreshingHomePromise;
}
(globalThis as any).__loadCatalogHome = refreshHomeCatalogCache;
setTimeout(() => { void refreshHomeCatalogCache().catch(() => {}); }, 80);
// --- FAST_IMG_HELPER_END ---
export const commerceRouter = router({
    access: publicProcedure.query(({ ctx }) => {
    const isAdminActive = ctx.user?.role === "admin" && !ctx.user.suspended;
    const isOwner = Boolean(ctx.user?.isOwner ?? (isAdminActive && !ctx.user?.adminRole));
    const adminRole = (ctx.user?.adminRole ?? (isOwner ? "owner" : null)) as AdminRoleKey | null;
    const permissions = (ctx.user?.permissions ?? (isOwner ? [...PERMISSION_KEYS] : [])) as PermissionKey[];
    return {
      authenticated: Boolean(ctx.user),
      isAdmin: isAdminActive,
      isOwner,
      adminRole,
      permissions,
      mustChangePassword: Boolean(ctx.user?.mustChangePassword),
      staffId: ctx.user?.staffId ?? null,
      staffUsername: ctx.user?.staffUsername ?? null,
      displayName: ctx.user?.name ?? null,
      isSuspended: Boolean(ctx.user?.suspended),
    };
  }),

  notifications: router({
    publicKey: publicProcedure.query(() => getWebPushPublicKey()),
  }),

  catalog: router({
    home: publicProcedure.query(async () => {
      const now = Date.now();
      const g = globalThis as any;
      if (g.__fastHomeData) {
        if (now - (g.__fastHomeTime || 0) > 25000) {
          void refreshHomeCatalogCache().catch(() => {});
        }
        return g.__fastHomeData;
      }
      return await refreshHomeCatalogCache();
    }),
    listProducts: publicProcedure.input(z.object({
      search: z.string().trim().max(120).optional(),
      categoryId: safeId.optional(),
      sort: z.enum(["featured", "price-asc", "price-desc", "name"]).default("featured"),
      limit: z.number().int().min(1).max(60).default(30),
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
      return list.slice(0, input?.limit ?? 30);
    }),
    listCategories: publicProcedure.query(async () => {
      const g = globalThis as any;
      if (Array.isArray(g.__fastHomeData?.categories)) return g.__fastHomeData.categories;
      const homeData = await refreshHomeCatalogCache();
      return homeData?.categories || [];
    }),
    product: publicProcedure.input(z.object({ id: safeId.optional(), slug: z.string().max(220).optional() })).query(async ({ input }) => getCached("product:" + JSON.stringify(input), 60_000, async () => {
      const db = await database();
      const product = (await db.select().from(products).where(and(
        input.id ? eq(products.id, input.id) : eq(products.slug, input.slug ?? ""),
        eq(products.isPublished, true), eq(products.isAvailable, true),
      )).limit(1))[0];
      if (!product) throw new TRPCError({ code: "NOT_FOUND", message: "المنتج غير متاح." });
      const linked = await db.select({ product: products }).from(productRecommendations)
        .innerJoin(products, eq(productRecommendations.recommendedProductId, products.id))
        .where(and(eq(productRecommendations.productId, product.id), eq(products.isPublished, true), eq(products.isAvailable, true)));
      return { ...toFastImg("product", product), recommendations: linked.map(row => toFastImg("product", row.product)) };
    })),
    productsForReorder: publicProcedure.input(z.object({ ids: z.array(safeId).min(1).max(500) })).query(async ({ input }) => {
      const db = await database();
      return db.select().from(products).where(and(inArray(products.id, [...new Set(input.ids)]), eq(products.isPublished, true), eq(products.isAvailable, true)));
    }),
  }),

  profile: router({
    updateName: protectedProcedure.input(z.object({ name: z.string().trim().min(2).max(120) })).mutation(async ({ ctx, input }) => {
      const db = await database();
      await db.update(users).set({ name: input.name }).where(eq(users.id, ctx.user.id));
      clearCatalogCache(); return { success: true };
    }),
    updatePhone: protectedProcedure.input(z.object({ phone: z.string().trim().min(7).max(32) })).mutation(async ({ ctx, input }) => {
      const db = await database();
      await db.update(users).set({ phone: input.phone }).where(eq(users.id, ctx.user.id));
      clearCatalogCache(); return { success: true };
    }),
    addresses: protectedProcedure.query(async ({ ctx }) => {
      const db = await database();
      return db.select().from(addresses).where(eq(addresses.userId, ctx.user.id)).orderBy(desc(addresses.isDefault), desc(addresses.id));
    }),
    saveAddress: protectedProcedure.input(z.object({
      id: safeId.optional(), label: z.string().trim().min(1).max(80), recipientName: z.string().trim().min(2).max(160),
      phone: z.string().trim().min(7).max(32), city: z.string().trim().min(1).max(100), district: z.string().trim().min(1).max(120),
      details: z.string().trim().max(1000).optional().nullable(), isDefault: z.boolean().default(false),
    })).mutation(async ({ ctx, input }) => {
      const db = await database();
      await db.transaction(async tx => {
        if (input.isDefault) await tx.update(addresses).set({ isDefault: false }).where(eq(addresses.userId, ctx.user.id));
        const values = { userId: ctx.user.id, label: input.label, recipientName: input.recipientName, phone: input.phone, city: input.city, district: input.district, details: input.details ?? null, isDefault: input.isDefault };
        if (input.id) {
          const owned = (await tx.select({ id: addresses.id }).from(addresses).where(and(eq(addresses.id, input.id), eq(addresses.userId, ctx.user.id))).limit(1))[0];
          if (!owned) throw new TRPCError({ code: "NOT_FOUND", message: "العنوان غير موجود في حسابك." });
          await tx.update(addresses).set(values).where(and(eq(addresses.id, input.id), eq(addresses.userId, ctx.user.id)));
        }
        else await tx.insert(addresses).values(values);
      });
      clearCatalogCache(); return { success: true };
    }),
    deleteAddress: protectedProcedure.input(z.object({ id: safeId })).mutation(async ({ ctx, input }) => {
      const db = await database();
      await db.delete(addresses).where(and(eq(addresses.id, input.id), eq(addresses.userId, ctx.user.id)));
      clearCatalogCache(); return { success: true };
    }),
  }),

  favorites: router({
    list: protectedProcedure.query(async ({ ctx }) => {
      const db = await database();
      const rows = await db.select({ product: products }).from(favorites).innerJoin(products, eq(favorites.productId, products.id))
        .where(and(eq(favorites.userId, ctx.user.id), eq(products.isPublished, true), eq(products.isAvailable, true)));
      return rows.map(row => row.product);
    }),
    toggle: protectedProcedure.input(z.object({ productId: safeId })).mutation(async ({ ctx, input }) => {
      const db = await database();
      const product = (await db.select({ id: products.id }).from(products).where(and(eq(products.id, input.productId), eq(products.isPublished, true), eq(products.isAvailable, true))).limit(1))[0];
      if (!product) throw new TRPCError({ code: "NOT_FOUND", message: "المنتج غير متاح." });
      const existing = (await db.select().from(favorites).where(and(eq(favorites.userId, ctx.user.id), eq(favorites.productId, input.productId))).limit(1))[0];
      if (existing) await db.delete(favorites).where(eq(favorites.id, existing.id));
      else await db.insert(favorites).values({ userId: ctx.user.id, productId: input.productId });
      return { saved: !existing };
    }),
  }),

  orders: router({
    quote: publicProcedure.input(z.object({
      items: z.array(z.object({ productId: safeId, quantity: z.number().int().min(1).max(10000), variant: z.string().trim().max(100).optional() })).min(1).max(100),
      city: z.string().trim().min(1).max(100), offerCode: z.string().trim().max(40).optional(),
    })).mutation(async ({ input }) => {
      const db = await database();
      const settings = await readSettings(db);
      if (settings.orderPaused === "true") throw new TRPCError({ code: "PRECONDITION_FAILED", message: settings.pausedMessage || "استقبال الطلبات متوقف مؤقتًا." });
      const deliveryFee = deliveryFeeForCity(settings, input.city);
      if (deliveryFee === null) throw new TRPCError({ code: "PRECONDITION_FAILED", message: settings.deliveryEnabled === "true" ? "منطقة التوصيل أو رسومها غير محددة بعد." : "لم يفعّل المتجر التوصيل بعد." });
      const requested = aggregateItems(input.items);
      if (requested.some(item => item.quantity > 10000)) throw new TRPCError({ code: "BAD_REQUEST", message: "الكمية الإجمالية لأحد المنتجات تتجاوز الحد المسموح." });
      const productIds = requested.map(item => item.productId);
      const currentProducts = await db.select().from(products).where(and(inArray(products.id, productIds), eq(products.isPublished, true), eq(products.isAvailable, true)));
      if (currentProducts.length !== productIds.length) throw new TRPCError({ code: "PRECONDITION_FAILED", message: "أحد المنتجات لم يعد متاحًا. حدّث السلة ثم حاول مجددًا." });
      const lines = requested.map(item => {
        const product = currentProducts.find(row => row.id === item.productId)!;
        if (item.quantity < product.minQuantity || (item.quantity - product.minQuantity) % product.quantityStep !== 0) throw new TRPCError({ code: "BAD_REQUEST", message: `الكمية المطلوبة من «${product.name}» لا توافق وحدة البيع.` });
        if (product.stock !== null && product.stock < item.quantity) throw new TRPCError({ code: "PRECONDITION_FAILED", message: `الكمية المتوفرة من «${product.name}» لا تكفي.` });
        return { productId: product.id, name: product.name, quantity: item.quantity, unit: product.unit, price: product.price, lineTotal: product.price * item.quantity };
      });
      const subtotal = lines.reduce((sum, line) => sum + line.lineTotal, 0);
      if (!Number.isSafeInteger(subtotal) || subtotal > 100000000000) throw new TRPCError({ code: "BAD_REQUEST", message: "إجمالي السلة يتجاوز الحد المسموح." });
      let appliedOffer: typeof offers.$inferSelect | null = null;
      if (input.offerCode) {
        appliedOffer = (await db.select().from(offers).where(and(eq(offers.code, input.offerCode.trim().toUpperCase()), eq(offers.isActive, true), sql`(${offers.startsAt} is null or ${offers.startsAt} <= now())`, sql`(${offers.endsAt} is null or ${offers.endsAt} >= now())`)).limit(1))[0] ?? null;
        if (!appliedOffer) throw new TRPCError({ code: "BAD_REQUEST", message: "رمز العرض غير صالح أو غير نشط." });
      }
      const totals = orderTotals(subtotal, deliveryFee, appliedOffer, settings);
      const currency = settings.currency || "ر.ي";
      return { lines, ...totals, currency, quoteHash: quoteFingerprint(lines, totals, currency, appliedOffer?.id ?? null), offerTitle: appliedOffer?.title ?? null };
    }),
    trackMany: publicProcedure.input(z.object({
      refs: z.array(z.object({
        orderNumber: z.string().trim().min(6).max(40).regex(/^OR-[A-Z0-9]+-[A-Z0-9]{5}$/i),
        idempotencyKey: z.string().uuid(),
      })).min(1).max(50),
    })).query(async ({ input }) => {
      const db = await database();
      const referenceByNumber = new Map(input.refs.map(reference => [reference.orderNumber, reference.idempotencyKey]));
      const candidates = await db.select().from(orders)
        .where(inArray(orders.orderNumber, [...referenceByNumber.keys()])).limit(50);
      const authorized = candidates.filter(order => {
        const key = referenceByNumber.get(order.orderNumber);
        return key ? matchesGuestOrderKey(key, order.idempotencyKey) : false;
      });
      if (!authorized.length) return [];
      const orderIds = authorized.map(order => order.id);
      const [items, events] = await Promise.all([
        db.select().from(orderItems).where(inArray(orderItems.orderId, orderIds)),
        db.select({ id: orderEvents.id, orderId: orderEvents.orderId, status: orderEvents.status, note: orderEvents.note, createdAt: orderEvents.createdAt })
          .from(orderEvents).where(inArray(orderEvents.orderId, orderIds)).orderBy(asc(orderEvents.createdAt)),
      ]);
      return authorized.map(order => ({
        orderNumber: order.orderNumber,
        status: order.status,
        total: order.total,
        createdAt: order.createdAt,
        items: items.filter(item => item.orderId === order.id),
        events: events.filter(event => event.orderId === order.id).map(({ id, status, note, createdAt }) => ({ id, status, note, createdAt })),
      }));
    }),
    subscribeToStatus: publicProcedure.input(z.object({
      refs: z.array(z.object({
        orderNumber: z.string().trim().min(6).max(40).regex(/^OR-[A-Z0-9]+-[A-Z0-9]{5}$/i),
        idempotencyKey: z.string().uuid(),
      })).min(1).max(50),
      subscription: pushSubscriptionSchema,
    })).mutation(async ({ input }) => {
      if (!isAllowedPushEndpoint(input.subscription.endpoint)) {
        throw new TRPCError({ code: "BAD_REQUEST", message: "خدمة الإشعارات في هذا المتصفح غير مدعومة." });
      }
      const db = await database();
      const referenceByNumber = new Map(input.refs.map(reference => [reference.orderNumber, reference.idempotencyKey]));
      const candidates = await db.select({ id: orders.id, orderNumber: orders.orderNumber, idempotencyKey: orders.idempotencyKey })
        .from(orders).where(inArray(orders.orderNumber, [...referenceByNumber.keys()])).limit(50);
      const authorized = candidates.filter(order => {
        const key = referenceByNumber.get(order.orderNumber);
        return key ? matchesGuestOrderKey(key, order.idempotencyKey) : false;
      });
      if (!authorized.length) return { subscribed: 0 };
      const protectedSubscription = protectPushSubscription(input.subscription);
      await db.transaction(async tx => {
        for (const order of authorized) {
          await tx.insert(customerPushSubscriptions).values({
            orderId: order.id,
            ...protectedSubscription,
          }).onDuplicateKeyUpdate({ set: { encryptedPayload: protectedSubscription.encryptedPayload, updatedAt: new Date() } });
        }
      });
      return { subscribed: authorized.length };
    }),
    mine: protectedProcedure.query(async ({ ctx }) => {
      const db = await database();
      const rows = await db.select().from(orders).where(eq(orders.userId, ctx.user.id)).orderBy(desc(orders.createdAt)).limit(100);
      if (!rows.length) return [];
      const orderIds = rows.map(row => sql`${row.id}`);
      const [items, events] = await Promise.all([
        db.select().from(orderItems).where(sql`${orderItems.orderId} in (${sql.join(orderIds, sql`, `)})`),
        db.select().from(orderEvents).where(sql`${orderEvents.orderId} in (${sql.join(orderIds, sql`, `)})`).orderBy(asc(orderEvents.createdAt)),
      ]);
      return rows.map(order => ({ ...order, items: items.filter(item => item.orderId === order.id), events: events.filter(event => event.orderId === order.id) }));
    }),
    place: publicProcedure.input(z.object({
      idempotencyKey: z.string().uuid(),
      expectedTotal: z.number().int().min(0).max(100000000000),
      expectedQuoteHash: z.string().length(64).regex(/^[a-f0-9]+$/),
      items: z.array(z.object({ productId: safeId, quantity: z.number().int().min(1).max(10000), variant: z.string().trim().max(100).optional() })).min(1).max(100),
      offerCode: z.string().trim().max(40).optional(),
      recipientName: z.string().trim().min(2).max(160), phone: z.string().trim().min(7).max(32).refine(isValidGuestPhone, "أدخل رقم هاتف صحيحًا ليتمكن المتجر من الاتصال بك."),
      city: z.string().trim().min(1).max(100), district: z.string().trim().min(1).max(120), addressDetails: z.string().trim().max(1000).optional(), customerNote: z.string().trim().max(1000).optional(),
    })).mutation(async ({ ctx, input }) => {
      const db = await database();
      const requested = aggregateItems(input.items);
      if (requested.some(item => item.quantity > 10000)) throw new TRPCError({ code: "BAD_REQUEST", message: "الكمية الإجمالية لأحد المنتجات تتجاوز الحد المسموح." });
      const storedIdempotencyKey = hashGuestOrderKey(input.idempotencyKey);
      const existing = (await db.select().from(orders).where(inArray(orders.idempotencyKey, [storedIdempotencyKey, input.idempotencyKey])).limit(1))[0];
      if (existing) return { id: existing.id, orderNumber: existing.orderNumber, total: existing.total, duplicate: true };
      const settings = await readSettings(db);
      if (settings.orderPaused === "true") throw new TRPCError({ code: "PRECONDITION_FAILED", message: settings.pausedMessage || "استقبال الطلبات متوقف مؤقتًا." });
      const deliveryFee = deliveryFeeForCity(settings, input.city);
      if (deliveryFee === null) throw new TRPCError({ code: "PRECONDITION_FAILED", message: "منطقة التوصيل أو رسومها غير محددة بعد." });

      let appliedOffer: typeof offers.$inferSelect | null = null;
      if (input.offerCode) {
        const code = input.offerCode.trim().toUpperCase();
        appliedOffer = (await db.select().from(offers).where(and(eq(offers.code, code), eq(offers.isActive, true), sql`(${offers.startsAt} is null or ${offers.startsAt} <= now())`, sql`(${offers.endsAt} is null or ${offers.endsAt} >= now())`)).limit(1))[0] ?? null;
        if (!appliedOffer) throw new TRPCError({ code: "BAD_REQUEST", message: "رمز العرض غير صالح أو غير نشط." });
      }

      const result = await db.transaction(async tx => {
        const orderLines: Array<{ product: typeof products.$inferSelect; quantity: number }> = [];
        let subtotal = 0;
        for (const item of requested) {
          const product = (await tx.select().from(products).where(and(eq(products.id, item.productId), eq(products.isPublished, true), eq(products.isAvailable, true))).limit(1).for("update"))[0];
          if (!product) throw new TRPCError({ code: "PRECONDITION_FAILED", message: "أحد المنتجات لم يعد متاحًا. حدّث السلة ثم حاول مجددًا." });
          if (item.quantity < product.minQuantity || (item.quantity - product.minQuantity) % product.quantityStep !== 0) {
            throw new TRPCError({ code: "BAD_REQUEST", message: `الكمية المطلوبة من «${product.name}» لا توافق وحدة البيع.` });
          }
          if (product.stock !== null && product.stock < item.quantity) throw new TRPCError({ code: "PRECONDITION_FAILED", message: `الكمية المتوفرة من «${product.name}» لا تكفي.` });
          subtotal += product.price * item.quantity;
          if (!Number.isSafeInteger(subtotal) || subtotal > 100000000000) throw new TRPCError({ code: "BAD_REQUEST", message: "إجمالي السلة يتجاوز الحد المسموح." });
          orderLines.push({ product, quantity: item.quantity });
        }
        const totals = orderTotals(subtotal, deliveryFee, appliedOffer, settings);
        const currency = settings.currency || "ر.ي";
        const currentLines = orderLines.map(line => ({ productId: line.product.id, name: line.product.name, quantity: line.quantity, unit: line.product.unit, price: line.product.price, lineTotal: line.product.price * line.quantity }));
        const currentQuoteHash = quoteFingerprint(currentLines, totals, currency, appliedOffer?.id ?? null);
        if (totals.total !== input.expectedTotal || currentQuoteHash !== input.expectedQuoteHash) throw new TRPCError({ code: "PRECONDITION_FAILED", message: "تغيّر السعر أو التوفر أو رسوم التوصيل بعد المعاينة. اعرض الملخص المحدّث قبل تأكيد الطلب." });
        const orderNumber = `OR-${Date.now().toString(36).toUpperCase()}-${nanoid(5).toUpperCase()}`;
        const inserted = await tx.insert(orders).values({
          orderNumber, idempotencyKey: storedIdempotencyKey, userId: null, offerId: appliedOffer?.id ?? null,
          recipientName: input.recipientName, phone: input.phone, city: input.city, district: input.district,
          addressDetails: input.addressDetails ?? null, customerNote: input.customerNote ?? null,
          subtotal, deliveryFee: totals.deliveryFee, discount: totals.discount, total: totals.total, status: "new",
        });
        const orderId = Number(inserted[0].insertId);
        for (const line of orderLines) {
          const vParts = input.items.filter(i => i.productId === line.product.id && i.variant && i.variant.trim()).map(i => i.quantity > 1 ? (i.variant!.trim() + " × " + i.quantity) : i.variant!.trim());
          const finalProdName = vParts.length > 0 ? (line.product.name + " (" + vParts.join("، ") + ")").slice(0, 180) : line.product.name;
          await tx.insert(orderItems).values({
            orderId, productId: line.product.id, productName: finalProdName, productImage: line.product.imageUrl,
            unit: line.product.unit, unitPrice: line.product.price, quantity: line.quantity, lineTotal: line.product.price * line.quantity,
          });
          if (line.product.stock !== null) {
            await tx.update(products).set({ stock: line.product.stock - line.quantity }).where(eq(products.id, line.product.id));
          }
        }
        await tx.insert(orderEvents).values({ orderId, status: "new", note: "تم استلام الطلب", changedByUserId: null });
        return { id: orderId, orderNumber, total: totals.total, duplicate: false };
      }).catch(async error => {
        if (!isDuplicateEntry(error)) throw error;
        const concurrent = (await db.select().from(orders).where(inArray(orders.idempotencyKey, [storedIdempotencyKey, input.idempotencyKey])).limit(1))[0];
        if (!concurrent) throw error;
        return { id: concurrent.id, orderNumber: concurrent.orderNumber, total: concurrent.total, duplicate: true };
      });
      clearCatalogCache();
      if (!result.duplicate) {
        void notifyOwnerNewOrder(result.id, result.orderNumber, result.total)
          .catch(() => console.warn("[Push] Could not notify owner of a new order"));
      }
      return result;
    }),
  }),

  assistant: router({
    pollMessages: publicProcedure.input(z.object({
      sessionId: z.string().trim().min(1).max(80),
    })).query(async ({ input, ctx }) => {
      const db = await getDb();
      await loadLiveChats(db);
      // Security: only return messages from this exact customer's session.
      const session = liveChatsMemory.get(input.sessionId);
      return {
        aiPaused: session?.aiPaused ?? false,
        ownerMessages: (session?.messages ?? []).filter(m => m.role === "owner"),
      };
    }),
    recipe: publicProcedure.input(z.object({
      request: z.string().trim().min(1).max(1200),
      history: z.array(z.object({ role: z.enum(["user", "assistant"]), text: z.string().max(1800) })).max(20).optional(),
      cart: z.array(z.object({ productId: safeId, quantity: z.number().int().min(1).max(10000) })).max(100).optional(),
      favoriteProductIds: z.array(safeId).max(500).optional(),
      sessionId: z.string().max(80).optional(),
      customerName: z.string().max(160).optional(),
      customerPhone: z.string().max(40).optional(),
    })).mutation(async ({ input, ctx }) => {
      const clientKey = ctx.user ? "user:" + ctx.user.id : "ip:" + (ctx.req.ip || "unknown-client");
      enforceAssistantRateLimit(clientKey.slice(0, 120));
      const db = await getDb();
      await loadLiveChats(db);

      const sid = (input.sessionId?.trim() || clientKey).slice(0, 80);
      const customerNameClean = input.customerName?.trim() || "زبون المتجر";
      const customerPhoneClean = input.customerPhone?.trim() || "غير مسجل بالموقع";
      const nowIso = new Date().toISOString();

      let chatSession = liveChatsMemory.get(sid);
      if (!chatSession) {
        chatSession = {
          sessionId: sid,
          customerName: customerNameClean,
          customerPhone: customerPhoneClean,
          aiPaused: false,
          updatedAt: nowIso,
          messages: [],
        };
        liveChatsMemory.set(sid, chatSession);
      } else {
        if (input.customerName?.trim()) chatSession.customerName = customerNameClean;
        if (input.customerPhone?.trim()) chatSession.customerPhone = customerPhoneClean;
        chatSession.updatedAt = nowIso;
      }

      chatSession.messages.push({
        id: nanoid(10),
        role: "user",
        sender: chatSession.customerName,
        text: input.request,
        createdAt: nowIso,
      });
      await saveLiveChats(db);

      if (chatSession.aiPaused) {
        return {
          message: "تم إرسال رسالتك إلى إدارة المتجر مباشرة، وسيرد عليك المالك هنا في المحادثة خلال لحظات...",
          recipe: null,
          ingredients: [],
          missingIngredients: [],
          cartAction: null,
          suggestedQuestions: ["عرض السلة", "تصفح المنتجات"],
        };
      }

      const catalogRows = db ? await db.select({ id: products.id, name: products.name, description: products.description, price: products.price, unit: products.unit, stock: products.stock, minQuantity: products.minQuantity, quantityStep: products.quantityStep }).from(products).where(and(eq(products.isPublished, true), eq(products.isAvailable, true))).limit(150).catch(() => []) : [];
      const catalog = catalogRows.filter(product => product.stock === null || product.stock > 0) as AssistantCatalogProduct[];
      const catalogById = new Map(catalog.map(product => [product.id, product]));
      const currentCart = (input.cart ?? []).flatMap(line => {
        const product = catalogById.get(line.productId);
        return product ? [{ productId: product.id, quantity: line.quantity, name: product.name, unit: product.unit }] : [];
      });
      const favoriteIds = [...new Set(input.favoriteProductIds ?? [])].filter(id => catalogById.has(id)).slice(0, 100);
      const customerFavorites = (favoriteIds.length && db)
        ? await db.select({ id: products.id, name: products.name }).from(products)
          .where(and(inArray(products.id, favoriteIds), eq(products.isPublished, true), eq(products.isAvailable, true)))
          .limit(100)
        : [];

      const history = (input.history ?? []).slice(-8).map(turn =>
        (turn.role === "user" ? "العميل" : "المساعد") + ": " + turn.text.trim().slice(0, 400),
      ).join("\n");

      const userPrompt = [
        "المنتجات المتاحة (مصدر الحقيقة الوحيد): " + JSON.stringify(catalog.slice(0, 50).map(p => ({ id: p.id, name: p.name, price: p.price, unit: p.unit }))),
        "مفضلات العميل: " + JSON.stringify(customerFavorites),
        "السلة الحالية: " + JSON.stringify(currentCart),
        history ? "سجل المحادثة السابق:\n" + history : "لا يوجد سياق سابق.",
        "رسالة العميل الحالية:\n" + input.request,
      ].join("\n\n");

      let output: AssistantModelOutput | null = null;
      try {
        const response = await invokeLLM({
          messages: [
            { role: "system", content: "أنت بائع يمني ذكي وأمين في متجر أوريجنال." },
            { role: "user", content: userPrompt },
          ],
          response_format: { type: "json_object" },
        });
        const structuredContent = response.choices?.[0]?.message?.content;
        output = parseAssistantModelContent(structuredContent);
      } catch (err) {
        console.error("[AI Assistant Error]", err);
      }

      if (!output) {
        throw new TRPCError({ code: "SERVICE_UNAVAILABLE", message: "يرجى التحقق من اتصال الإنترنت والمحاولة مرة أخرى." });
      }

      const prepared = (prepareAssistantResponse as any)(output, catalog, input.cart ?? [], input.request, input.history ?? []);

      chatSession.messages.push({
        id: nanoid(10),
        role: "assistant",
        sender: "المساعد الذكي",
        text: prepared.message,
        createdAt: new Date().toISOString(),
      });
      chatSession.updatedAt = new Date().toISOString();
      void saveLiveChats(db);

      const missingItems = output.missingIngredients ?? [];
      if (missingItems.length > 0 && db) {
        const requestedItemText = missingItems.join("، ").replace(/^طلب توفير:\s*/i, "").trim().slice(0, 180);
        void (async () => {
          try {
            const orderNumber = "REQ-" + Date.now().toString(36).toUpperCase().slice(-4) + "-" + nanoid(4).toUpperCase();
            const inserted = await db.insert(orders).values({
              orderNumber,
              idempotencyKey: "req-" + nanoid(22),
              userId: ctx.user?.id ?? null,
              offerId: null,
              recipientName: "🔔 طلب توفير (" + customerNameClean + ")",
              phone: customerPhoneClean,
              city: "طلب توفير خاص",
              district: "المساعد الذكي",
              addressDetails: "طلب الزبون توفير: " + requestedItemText,
              customerNote: "رسالة الزبون: \"" + input.request + "\" | رقم الزبون: " + customerPhoneClean,
              subtotal: 0,
              deliveryFee: 0,
              discount: 0,
              total: 0,
              status: "new",
            });
            const orderId = Number(inserted[0].insertId);
            await db.insert(orderItems).values({
              orderId,
              productId: null,
              productName: "🔔 مطلوب توفير: " + requestedItemText,
              productImage: null,
              unit: "طلب",
              unitPrice: 0,
              quantity: 1,
              lineTotal: 0,
            });
            await db.insert(orderEvents).values({
              orderId,
              status: "new",
              note: "طلب توفير تلقائي من المساعد الذكي — هاتف الزبون: " + customerPhoneClean,
              changedByUserId: null,
            });
            const subscriptions = await db.select({ id: ownerPushSubscriptions.id, encryptedPayload: ownerPushSubscriptions.encryptedPayload })
              .from(ownerPushSubscriptions);
            await deliverPushRows(subscriptions, {
              title: "🔔 طلب توفير منتج غير متوفر!",
              body: "طلب (" + requestedItemText + ") · هاتف الزبون: " + customerPhoneClean,
              url: "/admin/orders",
              tag: "original-missing-item-" + orderId,
            }, async id => { await db.delete(ownerPushSubscriptions).where(eq(ownerPushSubscriptions.id, id)); });
          } catch (e) {
            console.warn("[Missing Item Notify Error]", e);
          }
        })();
      }

      return prepared;
    }),
  }),

  admin: router({
    // --- ADMIN_STAFF_ROUTER_START ---
    staff: router({
      list: requirePermission("staff.manage").query(async () => {
        const db = await database();
        await ensureRbacTables(db);
        const rows = await db.select().from(adminStaff).orderBy(desc(adminStaff.createdAt));
        const items = rows.map(row => {
          const roleKey = (ROLE_KEYS.includes(row.roleKey as any) ? row.roleKey : "staff") as AdminRoleKey;
          return {
            id: row.id,
            username: row.username,
            displayName: row.displayName,
            roleKey,
            roleLabel: ROLE_DEFINITIONS[roleKey]?.label || row.roleKey,
            permissions: parsePermissionsJson(row.permissionsJson, roleKey),
            isActive: row.isActive,
            mustChangePassword: row.mustChangePassword,
            createdBy: row.createdBy,
            lastLoginAt: row.lastLoginAt,
            createdAt: row.createdAt,
            updatedAt: row.updatedAt,
          };
        });
        return {
          items,
          summary: {
            total: items.length,
            active: items.filter(i => i.isActive).length,
            disabled: items.filter(i => !i.isActive).length,
          },
        };
      }),
      auditLogs: requirePermission("staff.manage").query(async () => {
        const db = await database();
        await ensureRbacTables(db);
        return db.select().from(adminAuditLogs).orderBy(desc(adminAuditLogs.createdAt)).limit(150);
      }),
      create: requirePermission("staff.manage").input(z.object({
        displayName: z.string().trim().min(2).max(160),
        username: z.string().trim().min(3).max(120),
        password: z.string().min(6).max(128),
        roleKey: z.enum(["general_manager", "product_manager", "order_manager", "content_manager", "staff"]),
        permissions: z.array(z.enum(PERMISSION_KEYS)).max(30),
        mustChangePassword: z.boolean().default(true),
      })).mutation(async ({ ctx, input }) => {
        const normalizedUsername = input.username.trim().toLowerCase();
        if (["owner", "admin", "root"].includes(normalizedUsername)) {
          throw new TRPCError({ code: "BAD_REQUEST", message: "اسم المستخدم هذا محجوز لمالك المتجر." });
        }
        if (["123456", "12345678", "password", "admin123"].includes(input.password.trim().toLowerCase())) {
          throw new TRPCError({ code: "BAD_REQUEST", message: "لا يُسمح باستخدام كلمة مرور ضعيفة أو افتراضية مثل 123456." });
        }
        const guard = canManageTargetStaff(
          { isOwner: ctx.user.isOwner, permissions: ctx.user.permissions, staffId: ctx.user.staffId },
          input.roleKey,
          input.permissions,
        );
        if (!guard.allowed) {
          throw new TRPCError({ code: "FORBIDDEN", message: guard.reason || "غير مسموح." });
        }
        const db = await database();
        await ensureRbacTables(db);
        const existing = await db.select({ id: adminStaff.id }).from(adminStaff).where(eq(adminStaff.username, normalizedUsername)).limit(1);
        if (existing.length > 0) {
          throw new TRPCError({ code: "CONFLICT", message: "اسم المستخدم أو البريد مسجل مسبقاً لمدير آخر." });
        }
        const passwordHash = hashAdminPassword(input.password);
        const uniquePerms = [...new Set(input.permissions)];
        const result = await db.insert(adminStaff).values({
          username: normalizedUsername,
          displayName: input.displayName.trim(),
          passwordHash,
          roleKey: input.roleKey,
          permissionsJson: JSON.stringify(uniquePerms),
          isActive: true,
          mustChangePassword: input.mustChangePassword,
          sessionVersion: 1,
          createdBy: ctx.user.name || "مالك المتجر",
        });
        await writeAdminAuditLog({
          actorId: ctx.user.staffId ?? ctx.user.id,
          actorName: ctx.user.name || "مالك المتجر",
          actorRole: ctx.user.adminRole || "owner",
          action: "CREATE_STAFF",
          targetName: input.displayName + " (" + normalizedUsername + ")",
          details: "إنشاء حساب بدور: " + (ROLE_DEFINITIONS[input.roleKey]?.label || input.roleKey) + " | الصلاحيات: " + uniquePerms.join(", "),
          ipAddress: getClientIp(ctx.req),
        });
        return { id: Number(result[0].insertId), success: true };
      }),
      update: requirePermission("staff.manage").input(z.object({
        id: safeId,
        displayName: z.string().trim().min(2).max(160),
        username: z.string().trim().min(3).max(120),
        roleKey: z.enum(["general_manager", "product_manager", "order_manager", "content_manager", "staff"]),
        permissions: z.array(z.enum(PERMISSION_KEYS)).max(30),
      })).mutation(async ({ ctx, input }) => {
        const db = await database();
        await ensureRbacTables(db);
        const target = (await db.select().from(adminStaff).where(eq(adminStaff.id, input.id)).limit(1))[0];
        if (!target) throw new TRPCError({ code: "NOT_FOUND", message: "الحساب الإداري غير موجود." });
        if (target.roleKey === "owner") throw new TRPCError({ code: "FORBIDDEN", message: "لا يمكن تعديل حساب المالك." });
        const guard = canManageTargetStaff(
          { isOwner: ctx.user.isOwner, permissions: ctx.user.permissions, staffId: ctx.user.staffId },
          input.roleKey,
          input.permissions,
          target.id,
        );
        if (!guard.allowed) throw new TRPCError({ code: "FORBIDDEN", message: guard.reason || "غير مسموح." });
        const normalizedUsername = input.username.trim().toLowerCase();
        if (["owner", "admin", "root"].includes(normalizedUsername)) {
          throw new TRPCError({ code: "BAD_REQUEST", message: "اسم المستخدم هذا محجوز لمالك المتجر." });
        }
        const duplicateRows = await db.select({ id: adminStaff.id }).from(adminStaff).where(eq(adminStaff.username, normalizedUsername)).limit(5);
        const duplicate = duplicateRows.filter(r => r.id !== input.id);
        if (duplicate.length > 0) {
          throw new TRPCError({ code: "CONFLICT", message: "اسم المستخدم مستخدم بالفعل لحساب آخر." });
        }
        const uniquePerms = [...new Set(input.permissions)];
        await db.update(adminStaff).set({
          displayName: input.displayName.trim(),
          username: normalizedUsername,
          roleKey: input.roleKey,
          permissionsJson: JSON.stringify(uniquePerms),
          sessionVersion: target.sessionVersion + 1,
        }).where(eq(adminStaff.id, input.id));
        await writeAdminAuditLog({
          actorId: ctx.user.staffId ?? ctx.user.id,
          actorName: ctx.user.name || "مالك المتجر",
          actorRole: ctx.user.adminRole || "owner",
          action: "UPDATE_STAFF",
          targetName: input.displayName + " (" + normalizedUsername + ")",
          details: "تحديث الدور إلى: " + (ROLE_DEFINITIONS[input.roleKey]?.label || input.roleKey) + " | الصلاحيات: " + uniquePerms.join(", "),
          ipAddress: getClientIp(ctx.req),
        });
        return { success: true };
      }),
      setStatus: requirePermission("staff.manage").input(z.object({
        id: safeId,
        isActive: z.boolean(),
      })).mutation(async ({ ctx, input }) => {
        const db = await database();
        await ensureRbacTables(db);
        const target = (await db.select().from(adminStaff).where(eq(adminStaff.id, input.id)).limit(1))[0];
        if (!target) throw new TRPCError({ code: "NOT_FOUND", message: "الحساب الإداري غير موجود." });
        if (target.roleKey === "owner") throw new TRPCError({ code: "FORBIDDEN", message: "لا يمكن تعطيل حساب مالك المتجر." });
        if (ctx.user.staffId && ctx.user.staffId === target.id) {
          throw new TRPCError({ code: "FORBIDDEN", message: "لا يمكنك تعطيل حسابك الشخصي." });
        }
        if (!ctx.user.isOwner) {
          const targetPerms = parsePermissionsJson(target.permissionsJson, target.roleKey as AdminRoleKey);
          const guard = canManageTargetStaff({ isOwner: false, permissions: ctx.user.permissions, staffId: ctx.user.staffId }, target.roleKey as AdminRoleKey, targetPerms, target.id);
          if (!guard.allowed) throw new TRPCError({ code: "FORBIDDEN", message: guard.reason });
        }
        await db.update(adminStaff).set({
          isActive: input.isActive,
          sessionVersion: target.sessionVersion + 1,
        }).where(eq(adminStaff.id, input.id));
        await writeAdminAuditLog({
          actorId: ctx.user.staffId ?? ctx.user.id,
          actorName: ctx.user.name || "مالك المتجر",
          actorRole: ctx.user.adminRole || "owner",
          action: input.isActive ? "ACTIVATE_STAFF" : "DISABLE_STAFF",
          targetName: target.displayName + " (" + target.username + ")",
          details: input.isActive ? "تم تفعيل الحساب الإداري" : "تم تعطيل الحساب الإداري وإبطال جلسته الفورية",
          ipAddress: getClientIp(ctx.req),
        });
        return { success: true };
      }),
      resetPassword: requirePermission("staff.manage").input(z.object({
        id: safeId,
        newPassword: z.string().min(6).max(128),
        mustChangePassword: z.boolean().default(true),
      })).mutation(async ({ ctx, input }) => {
        if (["123456", "12345678", "password", "admin123"].includes(input.newPassword.trim().toLowerCase())) {
          throw new TRPCError({ code: "BAD_REQUEST", message: "لا يُسمح بتعيين كلمة مرور ضعيفة أو افتراضية مثل 123456." });
        }
        const db = await database();
        await ensureRbacTables(db);
        const target = (await db.select().from(adminStaff).where(eq(adminStaff.id, input.id)).limit(1))[0];
        if (!target) throw new TRPCError({ code: "NOT_FOUND", message: "الحساب الإداري غير موجود." });
        if (target.roleKey === "owner") throw new TRPCError({ code: "FORBIDDEN", message: "لا يمكن إعادة تعيين كلمة مرور المالك من هنا." });
        if (!ctx.user.isOwner && ctx.user.staffId === target.id) {
          throw new TRPCError({ code: "FORBIDDEN", message: "استخدم نافذة تغيير كلمة المرور الخاصة بك." });
        }
        const passwordHash = hashAdminPassword(input.newPassword);
        await db.update(adminStaff).set({
          passwordHash,
          mustChangePassword: input.mustChangePassword,
          sessionVersion: target.sessionVersion + 1,
        }).where(eq(adminStaff.id, input.id));
        await writeAdminAuditLog({
          actorId: ctx.user.staffId ?? ctx.user.id,
          actorName: ctx.user.name || "مالك المتجر",
          actorRole: ctx.user.adminRole || "owner",
          action: "RESET_STAFF_PASSWORD",
          targetName: target.displayName + " (" + target.username + ")",
          details: "إعادة تعيين كلمة المرور" + (input.mustChangePassword ? " مع فرض تغييرها عند الدخول القادم" : ""),
          ipAddress: getClientIp(ctx.req),
        });
        return { success: true };
      }),
      delete: requirePermission("staff.manage").input(z.object({ id: safeId })).mutation(async ({ ctx, input }) => {
        if (!ctx.user.isOwner) {
          throw new TRPCError({ code: "FORBIDDEN", message: "حذف الحسابات الإدارية نهائياً متاح لمالك المتجر فقط؛ يمكنك تعطيل الحساب بدلاً من ذلك." });
        }
        const db = await database();
        await ensureRbacTables(db);
        const target = (await db.select().from(adminStaff).where(eq(adminStaff.id, input.id)).limit(1))[0];
        if (!target) throw new TRPCError({ code: "NOT_FOUND", message: "الحساب غير موجود." });
        if (target.roleKey === "owner") throw new TRPCError({ code: "FORBIDDEN", message: "لا يمكن حذف حساب المالك." });
        await db.update(users).set({ role: "user", suspended: true }).where(eq(users.openId, "staff_user_" + target.id));
        await db.delete(adminStaff).where(eq(adminStaff.id, input.id));
        await writeAdminAuditLog({
          actorId: ctx.user.id,
          actorName: ctx.user.name || "مالك المتجر",
          actorRole: "owner",
          action: "DELETE_STAFF",
          targetName: target.displayName + " (" + target.username + ")",
          details: "حذف الحساب الإداري نهائياً مع الحفاظ على سجلات الطلبات المرتبطة",
          ipAddress: getClientIp(ctx.req),
        });
        return { success: true };
      }),
      changeOwnPassword: protectedProcedure.input(z.object({
        currentPassword: z.string().min(1).max(128),
        newPassword: z.string().min(6).max(128),
      })).mutation(async ({ ctx, input }) => {
        if (!ctx.user.staffId) {
          throw new TRPCError({ code: "BAD_REQUEST", message: "تغيير كلمة مرور مالك المتجر يتم عبر متغير البيئة ADMIN_PASSWORD في الاستضافة." });
        }
        if (["123456", "12345678", "password", "admin123"].includes(input.newPassword.trim().toLowerCase())) {
          throw new TRPCError({ code: "BAD_REQUEST", message: "يرجى اختيار كلمة مرور قوية وغير افتراضية." });
        }
        const db = await database();
        await ensureRbacTables(db);
        const staff = (await db.select().from(adminStaff).where(eq(adminStaff.id, ctx.user.staffId)).limit(1))[0];
        if (!staff || !verifyAdminPassword(input.currentPassword, staff.passwordHash)) {
          throw new TRPCError({ code: "UNAUTHORIZED", message: "كلمة المرور الحالية غير صحيحة." });
        }
        const nextVersion = staff.sessionVersion + 1;
        const passwordHash = hashAdminPassword(input.newPassword);
        await db.update(adminStaff).set({
          passwordHash,
          mustChangePassword: false,
          sessionVersion: nextVersion,
        }).where(eq(adminStaff.id, staff.id));
        const newToken = await sdk.createSessionToken("staff_" + staff.id + "_v" + nextVersion, {
          name: staff.displayName,
          expiresInMs: 7 * 24 * 60 * 60 * 1000,
        });
        const cookieOptions = getSessionCookieOptions(ctx.req);
        ctx.res.cookie(COOKIE_NAME, newToken, { ...cookieOptions, maxAge: 7 * 24 * 60 * 60 * 1000 });
        await writeAdminAuditLog({
          actorId: staff.id,
          actorName: staff.displayName,
          actorRole: staff.roleKey,
          action: "CHANGE_OWN_PASSWORD",
          targetName: staff.username,
          details: "قام المدير بتحديث كلمة مروره المؤقتة بنجاح",
          ipAddress: getClientIp(ctx.req),
        });
        return { success: true };
      }),
    }),
    // --- ADMIN_STAFF_ROUTER_END ---
    chats: router({
      list: requirePermission("chats.manage").query(async () => {
        const db = await database();
        await loadLiveChats(db);
        return [...liveChatsMemory.values()].sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());
      }),
      reply: requirePermission("chats.manage").input(z.object({
        sessionId: z.string().trim().min(1).max(80),
        text: z.string().trim().min(1).max(1200),
      })).mutation(async ({ input }) => {
        const db = await database();
        await loadLiveChats(db);
        const session = liveChatsMemory.get(input.sessionId);
        if (!session) throw new TRPCError({ code: "NOT_FOUND", message: "المحادثة غير موجودة." });
        const msgObj: LiveChatMsg = {
          id: nanoid(10),
          role: "owner",
          sender: "إدارة المتجر",
          text: input.text.trim(),
          createdAt: new Date().toISOString(),
        };
        session.messages.push(msgObj);
        session.updatedAt = msgObj.createdAt;
        await saveLiveChats(db);
        return { success: true };
      }),
      toggleAi: requirePermission("chats.manage").input(z.object({
        sessionId: z.string().trim().min(1).max(80),
        aiPaused: z.boolean(),
      })).mutation(async ({ input }) => {
        const db = await database();
        await loadLiveChats(db);
        const session = liveChatsMemory.get(input.sessionId);
        if (session) {
          session.aiPaused = input.aiPaused;
          session.updatedAt = new Date().toISOString();
          await saveLiveChats(db);
        }
        return { success: true };
      }),
      delete: requirePermission("chats.manage").input(z.object({
        sessionId: z.string().trim().min(1).max(80),
      })).mutation(async ({ input }) => {
        const db = await database();
        await loadLiveChats(db);
        liveChatsMemory.delete(input.sessionId);
        await saveLiveChats(db);
        return { success: true };
      }),
    }),
    overview: requirePermission("overview.view").query(async () => getCached("admin:overview", 30_000, async () => {
      const db = await database();
      const [productRows, categoryRows, orderRows, customerRows, orderMetrics, settings] = await Promise.all([
        db.select({ count: sql<number>`count(*)` }).from(products),
        db.select({ count: sql<number>`count(*)` }).from(categories),
        db.select({ count: sql<number>`count(*)` }).from(orders),
        db.select({ count: sql<number>`count(distinct ${orders.phone})` }).from(orders).where(sql`${orders.phone} <> ''`),
        db.select({ orderValue: sql<number>`coalesce(sum(case when ${orders.status} <> 'cancelled' then ${orders.total} else 0 end), 0)`, openOrders: sql<number>`coalesce(sum(case when ${orders.status} in ('new', 'preparing', 'ready', 'out_for_delivery') then 1 else 0 end), 0)` }).from(orders),
        readSettings(db),
      ]);
      const recentOrders = await db.select().from(orders).orderBy(desc(orders.createdAt)).limit(6);
      return { products: Number(productRows[0]?.count ?? 0), categories: Number(categoryRows[0]?.count ?? 0), orders: Number(orderRows[0]?.count ?? 0), customers: Number(customerRows[0]?.count ?? 0), orderValue: Number(orderMetrics[0]?.orderValue ?? 0), openOrders: Number(orderMetrics[0]?.openOrders ?? 0), recentOrders, settings };
    })),
    notifications: router({
      subscribe: adminProcedure.input(pushSubscriptionSchema).mutation(async ({ ctx, input }) => {
        if (!isAllowedPushEndpoint(input.endpoint)) {
          throw new TRPCError({ code: "BAD_REQUEST", message: "خدمة الإشعارات في هذا المتصفح غير مدعومة." });
        }
        const db = await database();
        let targetUserId = ctx.user?.id || 1;
        const existingUser = await db.select({ id: users.id }).from(users).where(eq(users.id, targetUserId)).limit(1);
        if (!existingUser.length) {
          const anyUser = await db.select({ id: users.id }).from(users).limit(1);
          if (anyUser.length) {
            targetUserId = anyUser[0].id;
          } else {
            const ins = await db.insert(users).values({
              openId: "admin-owner-local",
              name: "المدير",
              role: "admin",
            });
            targetUserId = Number(ins[0].insertId || 1);
          }
        }
        const protectedSubscription = protectPushSubscription(input);
        await db.insert(ownerPushSubscriptions).values({ userId: targetUserId, ...protectedSubscription })
          .onDuplicateKeyUpdate({ set: { encryptedPayload: protectedSubscription.encryptedPayload, updatedAt: new Date() } });
        console.log("[Push] Admin device registered for background Web Push (userId:", targetUserId, ")");
        clearCatalogCache();
        return { success: true };
      }),
    }),
    products: router({
      // --- PRODUCT_DELETE_ENDPOINT ---
      delete: requirePermission("products.manage").use(async ({ next }) => { clearCatalogCache(); return next(); }).input(z.object({ id: safeId })).mutation(async ({ input }) => {
        const db = await database();
        await db.transaction(async tx => {
          await tx.delete(productRecommendations).where(or(eq(productRecommendations.productId, input.id), eq(productRecommendations.recommendedProductId, input.id)));
          await tx.delete(favorites).where(eq(favorites.productId, input.id));
          await tx.update(orderItems).set({ productId: null }).where(eq(orderItems.productId, input.id));
          await tx.delete(products).where(eq(products.id, input.id));
        });
        return { success: true };
      }),
      list: requireAnyPermission(["products.view", "products.manage", "inventory.manage"]).query(async () => getCached("admin:products", 30_000, async () => {
        const db = await database();
        const rows = await db.select().from(products).orderBy(desc(products.updatedAt)).limit(500); return rows.map(r => toFastImg("product", r));
      })),
      create: adminProcedure.use(async ({ next }) => { clearLiveHomeCache(); return next(); }).input(productInput).mutation(async ({ input }) => {
        const db = await database();
        const result = await db.insert(products).values({ ...input, slug: slugify(input.name), description: input.description ?? null, imageUrl: input.imageUrl ?? null, categoryId: input.categoryId ?? null, stock: input.stock ?? null });
        void (async () => {
          try {
            const allRows = await db.select({ id: products.id, name: products.name, description: products.description, price: products.price, unit: products.unit, stock: products.stock, minQuantity: products.minQuantity, quantityStep: products.quantityStep }).from(products).where(and(eq(products.isPublished, true), eq(products.isAvailable, true))).limit(60);
            await generateAndCacheProductAiRecipe(input.name, allRows as AssistantCatalogProduct[]);
          } catch {}
        })();
        clearCatalogCache(); return { id: Number(result[0].insertId) };
      }),
      update: adminProcedure.use(async ({ next }) => { clearLiveHomeCache(); return next(); }).input(z.object({ id: safeId, values: productInput.partial() })).mutation(async ({ input }) => {
        const db = await database();
        const cleanVals = { ...input.values }; if (typeof cleanVals.imageUrl === "string" && cleanVals.imageUrl.startsWith("/api/fast-img/")) delete cleanVals.imageUrl; (globalThis as any).__fastImgCache?.delete("product:" + input.id); await db.update(products).set(cleanVals).where(eq(products.id, input.id));
        clearCatalogCache(); return { success: true };
      }),
      archive: adminProcedure.use(async ({ next }) => { clearLiveHomeCache(); return next(); }).input(z.object({ id: safeId })).mutation(async ({ input }) => {
        const db = await database();
        await db.update(products).set({ isPublished: false, isAvailable: false }).where(eq(products.id, input.id));
        clearCatalogCache(); return { success: true };
      }),
      setRecommendations: requirePermission("products.manage").input(z.object({ productId: safeId, recommendedIds: z.array(safeId).max(30) })).mutation(async ({ input }) => {
        if (input.recommendedIds.includes(input.productId)) throw new TRPCError({ code: "BAD_REQUEST", message: "لا يمكن اقتراح المنتج نفسه." });
        const db = await database();
        await db.transaction(async tx => {
          await tx.delete(productRecommendations).where(eq(productRecommendations.productId, input.productId));
          if (input.recommendedIds.length) await tx.insert(productRecommendations).values(input.recommendedIds.map(recommendedProductId => ({ productId: input.productId, recommendedProductId })));
        });
        clearCatalogCache(); return { success: true };
      }),
    }),
    categories: router({
      // --- CATEGORY_DELETE_ENDPOINT ---
      delete: requirePermission("categories.manage").use(async ({ next }) => { clearCatalogCache(); return next(); }).input(z.object({ id: safeId })).mutation(async ({ input }) => {
        const db = await database();
        await db.transaction(async tx => {
          await tx.update(products).set({ categoryId: null }).where(eq(products.categoryId, input.id));
          await tx.delete(categories).where(eq(categories.id, input.id));
        });
        return { success: true };
      }),
      list: requireAnyPermission(["categories.manage", "products.view", "products.manage"]).query(async () => getCached("admin:categories", 30_000, async () => {
        const db = await database();
        const rows = await db.select().from(categories).orderBy(asc(categories.sortOrder), asc(categories.id)); return rows.map(r => toFastImg("category", r));
      })),
      create: adminProcedure.use(async ({ next }) => { clearLiveHomeCache(); return next(); }).input(categoryInput).mutation(async ({ input }) => {
        const db = await database();
        const result = await db.insert(categories).values({ ...input, slug: slugify(input.name), description: input.description ?? null, imageUrl: input.imageUrl ?? null });
        clearCatalogCache(); return { id: Number(result[0].insertId) };
      }),
      update: adminProcedure.use(async ({ next }) => { clearLiveHomeCache(); return next(); }).input(z.object({ id: safeId, values: categoryInput.partial() })).mutation(async ({ input }) => {
        const db = await database();
        const cleanCatVals = { ...input.values }; if (typeof cleanCatVals.imageUrl === "string" && cleanCatVals.imageUrl.startsWith("/api/fast-img/")) delete cleanCatVals.imageUrl; (globalThis as any).__fastImgCache?.delete("category:" + input.id); await db.update(categories).set(cleanCatVals).where(eq(categories.id, input.id));
        clearCatalogCache(); return { success: true };
      }),
      archive: adminProcedure.use(async ({ next }) => { clearLiveHomeCache(); return next(); }).input(z.object({ id: safeId })).mutation(async ({ input }) => {
        const db = await database();
        await db.update(categories).set({ isActive: false }).where(eq(categories.id, input.id));
        clearCatalogCache(); return { success: true };
      }),
    }),
    banners: router({
      list: requirePermission("banners.manage").query(async () => {
        const db = await database();
        const rows = await db.select().from(banners).orderBy(asc(banners.sortOrder), desc(banners.createdAt)); return rows.map(r => toFastImg("banner", r));
      }),
      create: adminProcedure.use(async ({ next }) => { clearLiveHomeCache(); return next(); }).input(z.object({ title: z.string().trim().min(1).max(160), body: z.string().trim().max(1000).optional(), imageUrl: z.string().max(8500000).optional(), actionText: z.string().trim().max(60).optional(), actionUrl: z.string().trim().max(2000).optional(), isActive: z.boolean().default(false), sortOrder: z.number().int().min(-10000).max(10000).default(0) })).mutation(async ({ input }) => {
        const db = await database();
        const result = await db.insert(banners).values({ ...input, body: input.body ?? null, imageUrl: input.imageUrl ?? null, actionText: input.actionText ?? null, actionUrl: input.actionUrl ?? null });
        clearCatalogCache(); return { id: Number(result[0].insertId) };
      }),
      update: adminProcedure.use(async ({ next }) => { clearLiveHomeCache(); return next(); }).input(z.object({ id: safeId, values: z.object({ title: z.string().trim().min(1).max(160).optional(), body: z.string().max(1000).nullable().optional(), imageUrl: z.string().max(8500000).nullable().optional(), actionText: z.string().max(60).nullable().optional(), actionUrl: z.string().max(2000).nullable().optional(), isActive: z.boolean().optional(), sortOrder: z.number().int().min(-10000).max(10000).optional() }) })).mutation(async ({ input }) => {
        const db = await database();
        const cleanBanVals = { ...input.values }; if (typeof cleanBanVals.imageUrl === "string" && cleanBanVals.imageUrl.startsWith("/api/fast-img/")) delete cleanBanVals.imageUrl; (globalThis as any).__fastImgCache?.delete("banner:" + input.id); await db.update(banners).set(cleanBanVals).where(eq(banners.id, input.id));
        clearCatalogCache(); return { success: true };
      }),
      delete: adminProcedure.input(z.object({ id: safeId })).mutation(async ({ input }) => {
        const db = await database();
        await db.delete(banners).where(eq(banners.id, input.id));
        clearCatalogCache(); return { success: true };
      }),
    }),
    offers: router({
      list: requirePermission("offers.manage").query(async () => {
        const db = await database();
        return db.select().from(offers).orderBy(desc(offers.createdAt));
      }),
      create: adminProcedure.use(async ({ next }) => { clearLiveHomeCache(); return next(); }).input(z.object({
        title: z.string().trim().min(1).max(160),
        description: z.string().trim().max(1000).nullable().optional(),
        code: z.string().trim().min(1).max(40),
        discountType: z.enum(["fixed", "percent"]),
        discountValue: z.number().int().min(1).max(100000000),
        minimumOrder: z.number().int().min(0).max(100000000).default(0),
        startsAt: z.string().nullable().optional(),
        endsAt: z.string().nullable().optional(),
        isActive: z.boolean().default(true),
      })).mutation(async ({ input }) => {
        if (input.discountType === "percent" && input.discountValue > 100) {
          throw new TRPCError({ code: "BAD_REQUEST", message: "نسبة الخصم يجب ألا تتجاوز 100%." });
        }
        const db = await database();
        const cleanCode = input.code.trim().toUpperCase();
        const values = {
          title: input.title,
          description: input.description ?? null,
          code: cleanCode,
          discountType: input.discountType,
          discountValue: input.discountValue,
          minimumOrder: input.minimumOrder ?? 0,
          startsAt: input.startsAt ? new Date(input.startsAt) : null,
          endsAt: input.endsAt ? new Date(input.endsAt) : null,
          isActive: input.isActive,
        };
        const result = await db.insert(offers).values(values).onDuplicateKeyUpdate({ set: values });
        clearCatalogCache();
        return { id: Number(result[0].insertId || 1) };
      }),
      update: adminProcedure.use(async ({ next }) => { clearLiveHomeCache(); return next(); }).input(z.object({
        id: safeId,
        values: z.object({
          title: z.string().trim().min(1).max(160).optional(),
          description: z.string().max(1000).nullable().optional(),
          code: z.string().trim().min(1).max(40).optional(),
          discountType: z.enum(["fixed", "percent"]).optional(),
          discountValue: z.number().int().min(1).max(100000000).optional(),
          minimumOrder: z.number().int().min(0).max(100000000).optional(),
          startsAt: z.string().nullable().optional(),
          endsAt: z.string().nullable().optional(),
          isActive: z.boolean().optional(),
        }),
      })).mutation(async ({ input }) => {
        if (input.values.discountType === "percent" && input.values.discountValue !== undefined && input.values.discountValue > 100) {
          throw new TRPCError({ code: "BAD_REQUEST", message: "نسبة الخصم يجب ألا تتجاوز 100%." });
        }
        const db = await database();
        await db.update(offers).set({
          ...input.values,
          code: input.values.code?.trim().toUpperCase(),
          startsAt: input.values.startsAt === undefined ? undefined : input.values.startsAt === null || input.values.startsAt === "" ? null : new Date(input.values.startsAt),
          endsAt: input.values.endsAt === undefined ? undefined : input.values.endsAt === null || input.values.endsAt === "" ? null : new Date(input.values.endsAt),
        }).where(eq(offers.id, input.id));
        clearCatalogCache();
        return { success: true };
      }),
      delete: adminProcedure.input(z.object({ id: safeId })).mutation(async ({ input }) => {
        const db = await database();
        await db.delete(offers).where(eq(offers.id, input.id));
        clearCatalogCache();
        return { success: true };
      }),
    }),
    settings: router({
      get: requireAnyPermission(["settings.manage", "overview.view"]).query(async () => readSettings(await database())),
      save: requirePermission("settings.manage").input(settingSchema).mutation(async ({ input }) => { clearCatalogCache();
        const db = await database();
        await db.transaction(async tx => {
          for (const [key, value] of Object.entries(input)) {
            const stored = value === null ? "" : typeof value === "string" ? value : JSON.stringify(value);
            await tx.insert(storeSettings).values({ key, value: stored }).onDuplicateKeyUpdate({ set: { value: stored } });
          }
        });
        clearCatalogCache(); return { success: true };
      }),
    }),
    orders: router({
      // --- ORDER_DELETE_ENDPOINT ---
      delete: requirePermission("orders.manage").use(async ({ next }) => { clearCatalogCache(); return next(); }).input(z.object({ id: safeId })).mutation(async ({ input }) => {
        const db = await database();
        await db.transaction(async tx => {
          await tx.delete(customerPushSubscriptions).where(eq(customerPushSubscriptions.orderId, input.id));
          await tx.delete(orderEvents).where(eq(orderEvents.orderId, input.id));
          await tx.delete(orderItems).where(eq(orderItems.orderId, input.id));
          await tx.delete(orders).where(eq(orders.id, input.id));
        });
        return { success: true };
      }),
      createdAfter: requireAnyPermission(["orders.view", "orders.manage"]).input(z.object({ afterId: z.number().int().min(0).max(Number.MAX_SAFE_INTEGER) })).query(async ({ input }) => getCached("createdAfter:" + input.afterId, 10_000, async () => {
        const db = await database();
        if (input.afterId === 0) {
          const latest = (await db.select({ id: orders.id }).from(orders).orderBy(desc(orders.id)).limit(1))[0];
          return { latestId: latest?.id ?? 0, orders: [] };
        }
        const rows = await db.select({ id: orders.id, orderNumber: orders.orderNumber, createdAt: orders.createdAt })
          .from(orders).where(gt(orders.id, input.afterId)).orderBy(asc(orders.id)).limit(25);
        return { latestId: rows.at(-1)?.id ?? input.afterId, orders: rows };
      })),
      list: requireAnyPermission(["orders.view", "orders.manage"]).query(async () => {
        const db = await database();
        const rows = await db.select().from(orders).orderBy(desc(orders.createdAt)).limit(500);
        if (!rows.length) return [];
        const ids = rows.map(order => sql`${order.id}`);
        const [items, events] = await Promise.all([
          db.select().from(orderItems).where(sql`${orderItems.orderId} in (${sql.join(ids, sql`, `)})`),
          db.select().from(orderEvents).where(sql`${orderEvents.orderId} in (${sql.join(ids, sql`, `)})`).orderBy(asc(orderEvents.createdAt)),
        ]);
        return rows.map(order => ({ ...order, items: items.filter(item => item.orderId === order.id), events: events.filter(event => event.orderId === order.id) }));
      }),
      setStatus: requirePermission("orders.manage").input(z.object({ id: safeId, status: orderStatus, note: z.string().trim().max(500).optional() })).mutation(async ({ ctx, input }) => {
        const db = await database();
        const orderNumber = await db.transaction(async tx => {
          const current = (await tx.select({ id: orders.id, status: orders.status, orderNumber: orders.orderNumber }).from(orders).where(eq(orders.id, input.id)).limit(1).for("update"))[0];
          if (!current) throw new TRPCError({ code: "NOT_FOUND", message: "لم يتم العثور على الطلب." });
          if (current.status === "delivered" || current.status === "cancelled") throw new TRPCError({ code: "PRECONDITION_FAILED", message: "لا يمكن تغيير حالة طلب مغلق." });
          const allowed: Record<string, string[]> = { new: ["preparing", "cancelled"], preparing: ["ready", "cancelled"], ready: ["out_for_delivery", "cancelled"], out_for_delivery: ["delivered"] };
          if (!allowed[current.status]?.includes(input.status)) throw new TRPCError({ code: "PRECONDITION_FAILED", message: current.status === "out_for_delivery" && input.status === "cancelled" ? "لا يمكن إلغاء الطلب بعد خروجه للتوصيل؛ عالجه عبر إجراء إرجاع بعد استلامه." : "اتبع تسلسل حالات الطلب: جديد، تجهيز، جاهز، توصيل، ثم تسليم؛ أو ألغِ الطلب قبل خروجه." });
          if (input.status === "cancelled") {
            const lines = await tx.select({ productId: orderItems.productId, quantity: orderItems.quantity }).from(orderItems).where(eq(orderItems.orderId, input.id));
            for (const line of lines) {
              if (line.productId === null) continue;
              const product = (await tx.select({ stock: products.stock }).from(products).where(eq(products.id, line.productId)).limit(1).for("update"))[0];
              if (product && product.stock !== null) await tx.update(products).set({ stock: product.stock + line.quantity }).where(eq(products.id, line.productId));
            }
          }
          await tx.update(orders).set({ status: input.status }).where(eq(orders.id, input.id));
          await tx.insert(orderEvents).values({ orderId: input.id, status: input.status, note: input.note ?? null, changedByUserId: null });
          return current.orderNumber;
        });
        void notifyCustomerOrderStatus(input.id, orderNumber, input.status, input.note)
          .catch(() => console.warn("[Push] Could not notify customer of an order update"));
        clearCatalogCache(); return { success: true };
      }),
    }),
    customers: router({
      list: requirePermission("customers.view").query(async () => {
        const db = await database();
        return db.select({
          phone: orders.phone,
          orderCount: sql<number>`count(*)`,
          totalSpent: sql<number>`coalesce(sum(case when ${orders.status} <> 'cancelled' then ${orders.total} else 0 end), 0)`,
          lastOrderAt: sql<Date>`max(${orders.createdAt})`,
        }).from(orders).where(sql`${orders.phone} <> ''`).groupBy(orders.phone).orderBy(desc(sql`max(${orders.createdAt})`)).limit(500);
      }),
    }),
    users: router({
      list: requirePermission("customers.view").query(async () => {
        const db = await database();
        const rows = await db.select({ id: users.id, name: users.name, email: users.email, phone: users.phone, role: users.role, suspended: users.suspended, createdAt: users.createdAt, lastSignedIn: users.lastSignedIn }).from(users).orderBy(desc(users.createdAt)).limit(1000);
        if (!rows.length) return [];
        const ids = rows.map(user => user.id);
        const [stats, savedAddresses] = await Promise.all([
          db.select({ userId: orders.userId, orderCount: sql<number>`count(*)`, totalSpent: sql<number>`coalesce(sum(case when ${orders.status} <> 'cancelled' then ${orders.total} else 0 end), 0)` }).from(orders).where(inArray(orders.userId, ids)).groupBy(orders.userId),
          db.select({ userId: addresses.userId, id: addresses.id, label: addresses.label, recipientName: addresses.recipientName, phone: addresses.phone, city: addresses.city, district: addresses.district, details: addresses.details, isDefault: addresses.isDefault }).from(addresses).where(inArray(addresses.userId, ids)).orderBy(desc(addresses.isDefault), desc(addresses.id)),
        ]);
        return rows.map(user => {
          const stat = stats.find(row => row.userId === user.id);
          return { ...user, orderCount: Number(stat?.orderCount ?? 0), totalSpent: Number(stat?.totalSpent ?? 0), addresses: savedAddresses.filter(address => address.userId === user.id) };
        });
      }),
      setSuspended: requirePermission("staff.manage").input(z.object({ id: safeId, suspended: z.boolean() })).mutation(async ({ ctx, input }) => {
        const db = await database();
        const target = (await db.select({ id: users.id, role: users.role, openId: users.openId }).from(users).where(eq(users.id, input.id)).limit(1))[0];
        if (!target) throw new TRPCError({ code: "NOT_FOUND", message: "الحساب غير موجود." });
        if (target.id === ctx.user.id || target.role === "admin") throw new TRPCError({ code: "FORBIDDEN", message: "لا يمكن حظر حساب مالك/مدير." });
        await db.update(users).set({ suspended: input.suspended }).where(eq(users.id, input.id));
        clearCatalogCache(); return { success: true };
      }),
    }),
    uploadImage: requireAnyPermission(["products.manage", "categories.manage", "banners.manage", "settings.manage"]).input(z.object({ dataUrl: z.string().min(30).max(8_500_000), kind: z.enum(["product", "category", "banner", "icon"]) })).mutation(async ({ input }) => {
      const match = input.dataUrl.match(/^data:(image\/(?:webp|png|jpeg));base64,([A-Za-z0-9+/=]+)$/);
      if (!match) throw new TRPCError({ code: "BAD_REQUEST", message: "صيغة الصورة غير مدعومة. استخدم WEBP أو PNG أو JPEG." });
      return { imageUrl: input.dataUrl };
    }),
  }),
});


// Pre-warm catalog cache on startup and every 45s in background
async function __prewarmCatalog() {
  try {
    const caller = commerceRouter.createCaller({ req: { headers: {}, ip: "127.0.0.1" } as any, res: {} as any, user: null });
    await Promise.allSettled([
      caller.catalog.home(),
      caller.catalog.listCategories(),
      caller.catalog.listProducts({ sort: "featured", limit: 24 }),
      caller.catalog.listProducts({ sort: "featured", limit: 60 }),
    ]);
  } catch {}
}
setTimeout(__prewarmCatalog, 800);
setInterval(__prewarmCatalog, 45000).unref();
