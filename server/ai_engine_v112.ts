import type { Express } from "express";
import fs from "fs";
import path from "path";
import { getDb } from "./db";
import { products } from "../drizzle/schema";

export interface CustomInstructionItemV114 {
  id: string;
  category: "welcome" | "missing_item" | "tone" | "general";
  text: string;
  active: boolean;
  createdAt: string;
}

export interface CustomPromptRuleV112 {
  id: string;
  trigger: string;
  response: string;
  active: boolean;
}

export interface PromotedProductItemV114 {
  id: string;
  productId?: number;
  productName: string;
  productUrl: string;
  productPrice?: number;
  productImage?: string;
  triggerKeywords: string;
  promoPitch: string;
  promoBadge: string;
  active: boolean;
}

export interface CustomRecipeIngredientV114 {
  productId?: number;
  name: string;
  url: string;
  price?: number;
}

export interface CustomRecipeItemV112 {
  id: string;
  title: string;
  keywords: string;
  imageUrl: string;
  steps: string;
  ingredients: CustomRecipeIngredientV114[];
}

export interface ProductAiMetadataV112 {
  usageType: "auto" | "recipe" | "snacks_and_drinks" | "calories_and_info" | "custom";
  calories: string;
  customInfo: string;
  pairings: string;
  prepIdeas: string;
}

export interface AiCustomerRequestV112 {
  id: string;
  sessionId: string;
  customerName: string;
  customerPhone: string;
  requestedItem: string;
  userMessage: string;
  status: "pending" | "replied" | "available";
  adminReply: string;
  createdAt: string;
  repliedAt?: string;
}

export interface AiStudioConfigV112 {
  generalSystemPrompt: string;
  instructions: CustomInstructionItemV114[];
  rules: CustomPromptRuleV112[];
  promotedProducts: PromotedProductItemV114[];
  recipes: CustomRecipeItemV112[];
  productAiMap: Record<string, ProductAiMetadataV112>;
  ecoMode10k: boolean;
}

const DEFAULT_STUDIO_CONFIG: AiStudioConfigV112 = {
  generalSystemPrompt: "",
  instructions: [],
  rules: [],
  promotedProducts: [],
  recipes: [],
  productAiMap: {},
  ecoMode10k: true
};

const LOCAL_BACKUP_FILE = path.join(process.cwd(), "ai_studio_v115_backup.json");

let memoryConfig: AiStudioConfigV112 = JSON.parse(JSON.stringify(DEFAULT_STUDIO_CONFIG));
let memoryRequests: AiCustomerRequestV112[] = [];
let dbLoadedOnce = false;
let dbTableCreated = false;

const responseCache = new Map<string, { data: any; expiresAt: number }>();
let zeroTokenCounter = 0;
let cachedHitCounter = 0;

function sanitizeConfigObject(parsed: any): AiStudioConfigV112 {
  if (!parsed || typeof parsed !== "object") {
    return JSON.parse(JSON.stringify(DEFAULT_STUDIO_CONFIG));
  }
  return {
    generalSystemPrompt: typeof parsed.generalSystemPrompt === "string" ? parsed.generalSystemPrompt : "",
    instructions: Array.isArray(parsed.instructions) ? parsed.instructions : [],
    rules: Array.isArray(parsed.rules) ? parsed.rules : [],
    promotedProducts: Array.isArray(parsed.promotedProducts) ? parsed.promotedProducts : [],
    recipes: Array.isArray(parsed.recipes)
      ? parsed.recipes.map((r: any) => ({
          id: String(r?.id || "rec_" + Date.now() + "_" + Math.random().toString(36).slice(2, 6)),
          title: String(r?.title || ""),
          keywords: String(r?.keywords || ""),
          imageUrl: String(r?.imageUrl || ""),
          steps: String(r?.steps || ""),
          ingredients: Array.isArray(r?.ingredients)
            ? r.ingredients.map((ing: any) =>
                typeof ing === "string"
                  ? { name: ing, url: "/products?search=" + encodeURIComponent(ing) }
                  : {
                      productId: ing?.productId ? Number(ing.productId) : undefined,
                      name: String(ing?.name || ""),
                      url: String(ing?.url || ("/products?search=" + encodeURIComponent(String(ing?.name || "")))),
                      price: ing?.price ? Number(ing.price) : undefined
                    }
              )
            : []
        }))
      : [],
    productAiMap: parsed.productAiMap && typeof parsed.productAiMap === "object" ? parsed.productAiMap : {},
    ecoMode10k: parsed.ecoMode10k !== false
  };
}

function hasAnyStudioData(cfg: AiStudioConfigV112): boolean {
  if (!cfg) return false;
  return (
    Boolean(cfg.generalSystemPrompt && cfg.generalSystemPrompt.trim()) ||
    (Array.isArray(cfg.instructions) && cfg.instructions.length > 0) ||
    (Array.isArray(cfg.rules) && cfg.rules.length > 0) ||
    (Array.isArray(cfg.promotedProducts) && cfg.promotedProducts.length > 0) ||
    (Array.isArray(cfg.recipes) && cfg.recipes.length > 0) ||
    (cfg.productAiMap && Object.keys(cfg.productAiMap).length > 0)
  );
}

function saveToLocalFileSync(cfg: AiStudioConfigV112, reqs: AiCustomerRequestV112[]) {
  try {
    fs.writeFileSync(
      LOCAL_BACKUP_FILE,
      JSON.stringify({ config: cfg, requests: reqs, updatedAt: Date.now() }),
      "utf-8"
    );
  } catch {}
}

function loadFromLocalFileSync(): { config?: AiStudioConfigV112; requests?: AiCustomerRequestV112[] } | null {
  try {
    if (fs.existsSync(LOCAL_BACKUP_FILE)) {
      const raw = fs.readFileSync(LOCAL_BACKUP_FILE, "utf-8");
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === "object") {
        return {
          config: parsed.config ? sanitizeConfigObject(parsed.config) : undefined,
          requests: Array.isArray(parsed.requests) ? parsed.requests : undefined
        };
      }
    }
  } catch {}
  return null;
}

const initialLocal = loadFromLocalFileSync();
if (initialLocal?.config && hasAnyStudioData(initialLocal.config)) {
  memoryConfig = initialLocal.config;
}
if (initialLocal?.requests && initialLocal.requests.length > 0) {
  memoryRequests = initialLocal.requests;
}

async function runRawSqlV115(db: any, queryStr: string): Promise<any> {
  if (!db) return null;
  const sessionClient = (db as any)?.session?.client || (db as any)?.$client;
  if (sessionClient && typeof sessionClient.execute === "function") {
    return await sessionClient.execute(queryStr);
  }
  if (sessionClient && typeof sessionClient.query === "function") {
    return await sessionClient.query(queryStr);
  }
  if (typeof (db as any).execute === "function") {
    return await (db as any).execute(queryStr);
  }
  return null;
}

function extractRowsFromResultV115(res: any): any[] {
  if (!res) return [];
  if (Array.isArray(res)) {
    if (Array.isArray(res[0])) return res[0];
    return res;
  }
  if (Array.isArray(res.rows)) return res.rows;
  return [];
}

function sqlEscapeHexOrBase64(jsonStr: string): string {
  return Buffer.from(jsonStr, "utf-8").toString("base64");
}

function decodeStoredValueV115(rawVal: string): any {
  if (!rawVal) return null;
  const trimmed = String(rawVal).trim();
  if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
    return JSON.parse(trimmed);
  }
  const decoded = Buffer.from(trimmed, "base64").toString("utf-8");
  return JSON.parse(decoded);
}

async function ensureDbTableV115(db: any) {
  if (dbTableCreated || !db) return;
  try {
    await runRawSqlV115(
      db,
      "CREATE TABLE IF NOT EXISTS ai_studio_v115 (id VARCHAR(64) PRIMARY KEY, payload LONGTEXT NOT NULL, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP)"
    );
    dbTableCreated = true;
  } catch {}
}

async function loadStateFromDbOnce() {
  if (dbLoadedOnce) return;
  try {
    const db = await getDb();
    if (!db) return;
    await ensureDbTableV115(db);
    const res = await runRawSqlV115(
      db,
      "SELECT id, payload FROM ai_studio_v115 WHERE id IN ('config_v115', 'requests_v115')"
    );
    const list = extractRowsFromResultV115(res);
    for (const row of list) {
      const rowId = row?.id || row?.ID;
      const rowVal = row?.payload || row?.PAYLOAD;
      if (rowId === "config_v115" && rowVal) {
        try {
          const parsed = decodeStoredValueV115(String(rowVal));
          const sanitized = sanitizeConfigObject(parsed);
          if (hasAnyStudioData(sanitized) || !hasAnyStudioData(memoryConfig)) {
            memoryConfig = sanitized;
          }
        } catch {}
      } else if (rowId === "requests_v115" && rowVal) {
        try {
          const parsed = decodeStoredValueV115(String(rowVal));
          if (Array.isArray(parsed) && parsed.length > 0) {
            memoryRequests = parsed;
          }
        } catch {}
      }
    }
    saveToLocalFileSync(memoryConfig, memoryRequests);
    dbLoadedOnce = true;
  } catch {}
}

async function persistConfigToDb(cfg: AiStudioConfigV112) {
  memoryConfig = sanitizeConfigObject(cfg);
  responseCache.clear();
  saveToLocalFileSync(memoryConfig, memoryRequests);
  try {
    const db = await getDb();
    if (!db) return;
    await ensureDbTableV115(db);
    const b64 = sqlEscapeHexOrBase64(JSON.stringify(memoryConfig));
    await runRawSqlV115(
      db,
      "INSERT INTO ai_studio_v115 (id, payload) VALUES ('config_v115', '" + b64 + "') ON DUPLICATE KEY UPDATE payload = '" + b64 + "'"
    );
  } catch {}
}

async function persistRequestsToDb() {
  saveToLocalFileSync(memoryConfig, memoryRequests);
  try {
    const db = await getDb();
    if (!db) return;
    await ensureDbTableV115(db);
    const b64 = sqlEscapeHexOrBase64(JSON.stringify(memoryRequests.slice(0, 250)));
    await runRawSqlV115(
      db,
      "INSERT INTO ai_studio_v115 (id, payload) VALUES ('requests_v115', '" + b64 + "') ON DUPLICATE KEY UPDATE payload = '" + b64 + "'"
    );
  } catch {}
}

function normalizeArabicV112(str: string): string {
  return String(str || "")
    .toLowerCase()
    .replace(/[أإآ]/g, "ا")
    .replace(/ة/g, "ه")
    .replace(/ى/g, "ي")
    .replace(/[؟?!.,،]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function cleanProductNameV112(rawName: string): string {
  return String(rawName || "")
    .replace(/\(\s*رقم\s*\d+\s*\)/g, "")
    .replace(/\[\[variants:[\s\S]*?\]\]/g, "")
    .replace(/\s*\([^()]*:\s*\d+[^()]*\)\s*/g, "")
    .trim();
}

export function classifyProductSmartV112(productName: string, customMeta?: ProductAiMetadataV112): {
  mode: "recipe" | "snacks_and_drinks" | "calories_and_info" | "custom";
  chips: { icon: string; label: string; prompt: string }[];
  defaultInfo: string;
} {
  const cleanName = cleanProductNameV112(productName);
  const norm = normalizeArabicV112(cleanName);

  if (customMeta && customMeta.usageType && customMeta.usageType !== "auto") {
    if (customMeta.usageType === "custom" && customMeta.customInfo) {
      return {
        mode: "custom",
        chips: [
          { icon: "✨", label: "معلومات خاصة ومميزات المنتج", prompt: "اعطني معلومات ومميزات " + cleanName },
          { icon: "🔥", label: "السعرات والقيمة الغذائية", prompt: "كم السعرات الحرارية والمعلومات الغذائية في " + cleanName },
          { icon: "🛒", label: "أفضل الإضافات معه", prompt: "ايش افضل المنتجات اللي تناسب " + cleanName }
        ],
        defaultInfo: customMeta.customInfo
      };
    }
    if (customMeta.usageType === "recipe") {
      return {
        mode: "recipe",
        chips: [
          { icon: "🍰", label: "حلى ووصفة سريعة به", prompt: "اعطني وصفة حلى او طريقة عمل لذيذة باستخدام " + cleanName },
          { icon: "☕", label: "مشروب يناسبه", prompt: "ايش افضل مشروب يقدم مع " + cleanName },
          { icon: "🔥", label: "السعرات والمعلومات", prompt: "كم السعرات الحرارية في " + cleanName }
        ],
        defaultInfo: customMeta.prepIdeas || ""
      };
    }
    if (customMeta.usageType === "snacks_and_drinks") {
      return {
        mode: "snacks_and_drinks",
        chips: [
          { icon: "☕", label: "أفضل مشروب أو سناك معه", prompt: "ايش افضل مشروب او سناك يؤكل مع " + cleanName },
          { icon: "🔥", label: "السعرات الحرارية والمعلومات", prompt: "كم السعرات الحرارية والمعلومات عن " + cleanName },
          { icon: "⭐", label: "منتجات مشابهة بالمتجر", prompt: "اعطني منتجات مشابهة او بديلة لـ " + cleanName }
        ],
        defaultInfo: customMeta.pairings || ""
      };
    }
    if (customMeta.usageType === "calories_and_info") {
      return {
        mode: "calories_and_info",
        chips: [
          { icon: "🔥", label: "السعرات والقيمة الغذائية", prompt: "كم السعرات الحرارية والمعلومات الغذائية لـ " + cleanName },
          { icon: "💡", label: "معلومات وفوائد المنتج", prompt: "اعطني معلومات وفوائد " + cleanName },
          { icon: "🛒", label: "منتجات تكمله في السلة", prompt: "ايش اضيف مع " + cleanName + " في السلة" }
        ],
        defaultInfo: customMeta.calories || ""
      };
    }
  }

  const isRecipeBiscuitOrBase = /(ماري|بسكويت شاي|سميد|شوفان|قشطه|قشطة|حليب مكثف|دقيق|طحين|توست|كريم كراميل|جيلي|جالكسي|اوريو|أوريو|ابو ولد|أبو ولد)/.test(norm);
  if (isRecipeBiscuitOrBase) {
    return {
      mode: "recipe",
      chips: [
        { icon: "🍰", label: "طريقة عمل حلى سريع به", prompt: "اعطني وصفة حلى سريع ولذيذ باستخدام " + cleanName },
        { icon: "☕", label: "تغميسة أو مشروب معه", prompt: "ايش افضل مشروب او تغميسة مع " + cleanName },
        { icon: "🔥", label: "السعرات الحرارية والمعلومات", prompt: "كم السعرات الحرارية والمعلومات عن " + cleanName }
      ],
      defaultInfo: customMeta?.prepIdeas || "يدخل في تحضير ألذ الحلويات الباردة وطبقات البسكويت مع القشطة أو الحليب والشوكولاتة، كما يؤكل مباشرة مع الشاي أو القهوة."
    };
  }

  const isReadyChocolateOrCandy = /(شوكلاته|شوكولاته|شوكولاتة|بليلا|ويفر|بريك|توبس|كيت كات|سنيكرز|مارس|باونتي|تويكس|كندر|حلاوه|حلاوة|مصاص|علك|لبان|شيبس|بطاطس|فشار|مكسرات|كيك|كرواسون|ديمه|ديما)/.test(norm);
  if (isReadyChocolateOrCandy) {
    return {
      mode: "snacks_and_drinks",
      chips: [
        { icon: "☕", label: "أفضل مشروب معه (قهوة/عصير)", prompt: "ايش افضل مشروب يناسب " + cleanName },
        { icon: "🔥", label: "السعرات الحرارية والمعلومات", prompt: "كم السعرات الحرارية والمعلومات الغذائية عن " + cleanName },
        { icon: "🍫", label: "سناكات مشابهة في المتجر", prompt: "رشح لي سناكات او حلويات مشابهة لـ " + cleanName }
      ],
      defaultInfo: customMeta?.calories || "سناك جاهز للأكل مباشرة (لا يحتاج طبخ أو تحضير)، طعمه رائع مع القهوة العربية أو التركية أو العصائر الباردة، ويمد الجسم بطاقة سريعة."
    };
  }

  const isBeverage = /(عصير|شراب|رواب|ماء|مياه|بيبسي|كولا|سفن|ميرندا|حليب|لبن|شاي|قهوه|قهوة|نسكافيه|كابتشينو)/.test(norm);
  if (isBeverage) {
    return {
      mode: "snacks_and_drinks",
      chips: [
        { icon: "🥨", label: "أفضل سناك أو بسكويت معه", prompt: "ايش افضل سناك او بسكويت يؤكل مع " + cleanName },
        { icon: "🧊", label: "أفضل طريقة تقديم ومنعشة", prompt: "كيف اقدم " + cleanName + " بطريقة منعشة ومميزة" },
        { icon: "🔥", label: "السعرات والمعلومات الغذائية", prompt: "كم السعرات الحرارية والمعلومات عن " + cleanName }
      ],
      defaultInfo: customMeta?.calories || "مشروب منعش يفضل تقديمه بارداً، ويناسب جداً تناوله مع البسكويت أو الشوكولاتة الخفيفة أو المكسرات."
    };
  }

  const isCookingIngredient = /(ارز|أرز|مكرونه|مكرونة|تونه|تونة|صلصه|صلصة|زيت|سمن|فول|فاصوليا|عدس|بازلاء|بهارات|ملح|سكر|مرقه|مرقة|ماجي|جبن|جبنه|جبنة|بيض|دجاج|لحم)/.test(norm);
  if (isCookingIngredient) {
    return {
      mode: "recipe",
      chips: [
        { icon: "🍲", label: "وجبة سريعة واقتصادية به", prompt: "اعطني طريقة عمل وجبة سريعة ولذيذة باستخدام " + cleanName },
        { icon: "🥗", label: "المكونات المكملة له للطبخ", prompt: "ايش المكونات اللي احتاجها عشان اطبخ " + cleanName },
        { icon: "🔥", label: "القيمة الغذائية والسعرات", prompt: "ما هي القيمة الغذائية والسعرات في " + cleanName }
      ],
      defaultInfo: customMeta?.prepIdeas || "مكون أساسي للطبخ وتحضير الوجبات اليومية السريعة والاقتصادية."
    };
  }

  return {
    mode: "calories_and_info",
    chips: [
      { icon: "💡", label: "معلومات ومميزات المنتج", prompt: "اعطني معلومات ومميزات واستخدامات " + cleanName },
      { icon: "🛒", label: "منتجات مشابهة أو مكملة", prompt: "ايش المنتجات المشابهة او المكملة لـ " + cleanName }
    ],
    defaultInfo: customMeta?.customInfo || "منتج أصلي متوفر في متجر أورجنال بجودة عالية وسعر منافس."
  };
}

function findMatchingSavedRecipeV117(userMessage: string, recipes: CustomRecipeItemV112[]): CustomRecipeItemV112 | null {
  if (!Array.isArray(recipes) || recipes.length === 0) return null;
  const normMsg = normalizeArabicV112(userMessage);
  if (!normMsg) return null;

  const stopWords = new Set(["اريد", "ابغي", "اشتي", "هل", "عندكم", "ممكن", "كيف", "اسوي", "طريقه", "عمل", "وصفه", "حلو", "لذيذ", "سريع", "في", "من", "مع", "على", "عن"]);

  for (const rec of recipes) {
    const normTitle = normalizeArabicV112(rec.title || "");
    const normKw = normalizeArabicV112(rec.keywords || "");

    if (normTitle && (normMsg.includes(normTitle) || normTitle.includes(normMsg))) return rec;
    if (normKw && (normMsg.includes(normKw) || normKw.includes(normMsg))) return rec;

    const kwList = String(rec.keywords || "")
      .split(/[،,]+/)
      .map(s => normalizeArabicV112(s))
      .filter(s => s.length >= 3);
    for (const kw of kwList) {
      if (normMsg.includes(kw) || kw.includes(normMsg)) return rec;
    }

    const combinedTarget = normTitle + " " + normKw;
    const msgWords = normMsg.split(" ").filter(w => w.length >= 3 && !stopWords.has(w));
    const matchedWords = msgWords.filter(w => combinedTarget.includes(w));
    if (matchedWords.length >= 2) return rec;
    if (matchedWords.length >= 1 && (normMsg.includes("حلي") || normMsg.includes("وصفه"))) return rec;
  }
  return null;
}

export function registerAiEngineV112(app: Express) {
  app.get("/api/ai-studio/state", async (_req, res) => {
    try {
      await loadStateFromDbOnce();
      const db = await getDb();
      let allProds: any[] = [];
      if (db) {
        allProds = await db
          .select({
            id: products.id,
            name: products.name,
            price: products.price,
            unit: products.unit,
            description: products.description
          })
          .from(products);
      }
      const catalog = allProds.map(p => {
        const pid = String(p.id);
        const cleanName = cleanProductNameV112(p.name);
        const meta = memoryConfig.productAiMap[pid] || memoryConfig.productAiMap[cleanName] || {
          usageType: "auto",
          calories: "",
          customInfo: "",
          pairings: "",
          prepIdeas: ""
        };
        const smart = classifyProductSmartV112(cleanName, meta);
        return {
          id: p.id,
          name: cleanName,
          price: p.price,
          unit: p.unit || "حبة",
          url: "/products?search=" + encodeURIComponent(cleanName),
          meta,
          smartMode: smart.mode,
          smartChips: smart.chips
        };
      });

      res.json({
        ok: true,
        config: memoryConfig,
        requests: memoryRequests,
        catalog,
        stats: {
          zeroTokenMessages: zeroTokenCounter,
          cachedHits: cachedHitCounter,
          estimatedTokensSaved: (zeroTokenCounter + cachedHitCounter) * 450
        }
      });
    } catch (e: any) {
      res.status(500).json({ ok: false, error: String(e?.message || e) });
    }
  });

  app.post("/api/ai-studio/save-config", async (req, res) => {
    try {
      await loadStateFromDbOnce();
      const body = req.body || {};
      const next: AiStudioConfigV112 = sanitizeConfigObject({
        generalSystemPrompt:
          typeof body.generalSystemPrompt === "string" ? body.generalSystemPrompt : memoryConfig.generalSystemPrompt,
        instructions: Array.isArray(body.instructions) ? body.instructions : memoryConfig.instructions,
        rules: Array.isArray(body.rules) ? body.rules : memoryConfig.rules,
        promotedProducts: Array.isArray(body.promotedProducts) ? body.promotedProducts : memoryConfig.promotedProducts,
        recipes: Array.isArray(body.recipes) ? body.recipes : memoryConfig.recipes,
        productAiMap:
          body.productAiMap && typeof body.productAiMap === "object" ? body.productAiMap : memoryConfig.productAiMap,
        ecoMode10k: body.ecoMode10k !== undefined ? Boolean(body.ecoMode10k) : memoryConfig.ecoMode10k
      });
      await persistConfigToDb(next);
      res.json({ ok: true, config: memoryConfig });
    } catch (e: any) {
      res.status(500).json({ ok: false, error: String(e?.message || e) });
    }
  });

  app.post("/api/ai-studio/request-item", async (req, res) => {
    try {
      await loadStateFromDbOnce();
      const body = req.body || {};
      const requestedItem = String(body.requestedItem || "").trim();
      if (!requestedItem) {
        return res.status(400).json({ ok: false, error: "يرجى تحديد اسم المنتج المطلوب" });
      }
      const newReq: AiCustomerRequestV112 = {
        id: "req_" + Date.now() + "_" + Math.random().toString(36).slice(2, 6),
        sessionId: String(body.sessionId || "guest"),
        customerName: String(body.customerName || "زبون المتجر").trim(),
        customerPhone: String(body.customerPhone || "").trim(),
        requestedItem,
        userMessage: String(body.userMessage || requestedItem).trim(),
        status: "pending",
        adminReply: "",
        createdAt: new Date().toISOString()
      };
      memoryRequests.unshift(newReq);
      await persistRequestsToDb();
      res.json({ ok: true, request: newReq });
    } catch (e: any) {
      res.status(500).json({ ok: false, error: String(e?.message || e) });
    }
  });

  app.post("/api/ai-studio/admin-reply", async (req, res) => {
    try {
      await loadStateFromDbOnce();
      const body = req.body || {};
      const reqId = String(body.requestId || "");
      const replyText = String(body.adminReply || "").trim();
      const status = body.status === "available" ? "available" : "replied";
      const target = memoryRequests.find(r => r.id === reqId);
      if (!target) {
        return res.status(404).json({ ok: false, error: "الطلب غير موجود" });
      }
      target.adminReply = replyText;
      target.status = status;
      target.repliedAt = new Date().toISOString();
      await persistRequestsToDb();
      res.json({ ok: true, request: target });
    } catch (e: any) {
      res.status(500).json({ ok: false, error: String(e?.message || e) });
    }
  });

  app.get("/api/ai-studio/customer-notifications", async (req, res) => {
    try {
      await loadStateFromDbOnce();
      const sessionId = String(req.query.sessionId || "");
      const matched = sessionId
        ? memoryRequests.filter(r => r.sessionId === sessionId && r.adminReply)
        : memoryRequests.filter(r => r.adminReply).slice(0, 5);
      res.json({ ok: true, notifications: matched });
    } catch (e: any) {
      res.status(500).json({ ok: false, error: String(e?.message || e) });
    }
  });

  app.post("/api/ai-studio/smart-chat", async (req, res) => {
    try {
      await loadStateFromDbOnce();
      const body = req.body || {};
      const userMessage = String(body.message || "").trim();
      const productContextName = cleanProductNameV112(String(body.productName || ""));
      const normMsg = normalizeArabicV112(userMessage);

      if (!userMessage) {
        return res.json({ ok: true, zeroToken: true, reply: "يا هلا بك يا غالي! آمرني، ايش تبحث عنه اليوم؟" });
      }

      const cacheKey = normMsg + "|" + normalizeArabicV112(productContextName);
      const cached = responseCache.get(cacheKey);
      if (cached && cached.expiresAt > Date.now()) {
        cachedHitCounter++;
        return res.json({ ...cached.data, fromCache: true });
      }

      const db = await getDb();
      const allProds = db
        ? await db
            .select({
              id: products.id,
              name: products.name,
              price: products.price,
              unit: products.unit,
              description: products.description
            })
            .from(products)
        : [];

      // 1. Check Custom Admin Rules first (0 Tokens)
      for (const rule of memoryConfig.rules) {
        if (!rule.active || !rule.trigger) continue;
        const triggers = rule.trigger.split(/[،,|]+/).map(t => normalizeArabicV112(t)).filter(Boolean);
        if (triggers.some(t => normMsg.includes(t))) {
          zeroTokenCounter++;
          const payload = {
            ok: true,
            zeroToken: true,
            reply: rule.response,
            suggestedItems: []
          };
          responseCache.set(cacheKey, { data: payload, expiresAt: Date.now() + 10 * 60 * 1000 });
          return res.json(payload);
        }
      }

      // 2. Check Custom Illustrated Recipes with Product Links (0 Tokens)
      const matchedRecipe = findMatchingSavedRecipeV117(userMessage + " " + productContextName, memoryConfig.recipes);
      if (matchedRecipe) {
        zeroTokenCounter++;
        const matchedItems: any[] = [];
        for (const ing of matchedRecipe.ingredients || []) {
          const ingObj = typeof ing === "string" ? { name: ing, url: "/products?search=" + encodeURIComponent(ing) } : ing;
          const cleanIng = cleanProductNameV112(ingObj.name || "");
          // Priority 1: Exact product ID or Exact product name match (prevents "بسكويت ديما كريمة بنكهة البرتقال" from matching "البرتقال"!)
          const foundProd =
            (ingObj.productId ? allProds.find(p => Number(p.id) === Number(ingObj.productId)) : undefined) ||
            allProds.find(p => cleanProductNameV112(p.name) === cleanIng) ||
            allProds.find(p => normalizeArabicV112(cleanProductNameV112(p.name)) === normalizeArabicV112(cleanIng)) ||
            allProds.find(p => {
              const cn = normalizeArabicV112(cleanProductNameV112(p.name));
              const ci = normalizeArabicV112(cleanIng);
              return cn.length >= 6 && ci.length >= 6 && (cn.includes(ci) || ci.includes(cn)) && Math.abs(cn.length - ci.length) <= 6;
            });

          if (foundProd) {
            matchedItems.push({
              id: foundProd.id,
              productId: foundProd.id,
              name: cleanProductNameV112(foundProd.name),
              price: foundProd.price,
              unit: foundProd.unit || "حبة",
              url: ingObj.url || ("/products?search=" + encodeURIComponent(cleanProductNameV112(foundProd.name)))
            });
          } else if (ingObj.name) {
            matchedItems.push({
              id: ingObj.productId || 1,
              productId: ingObj.productId || 1,
              name: cleanIng,
              price: ingObj.price || 100,
              unit: "حبة",
              url: ingObj.url || ("/products?search=" + encodeURIComponent(cleanIng))
            });
          }
        }
        const replyMsg = "🍰 " + matchedRecipe.title + "\n\n" + matchedRecipe.steps;
        const payload = {
          ok: true,
          zeroToken: true,
          reply: replyMsg,
          recipeTitle: matchedRecipe.title,
          recipeImage: matchedRecipe.imageUrl || "",
          recipeSteps: matchedRecipe.steps || "",
          suggestedItems: matchedItems
        };
        responseCache.set(cacheKey, { data: payload, expiresAt: Date.now() + 10 * 60 * 1000 });
        return res.json(payload);
      }

      // 3. Check Promoted Products with Direct Links (0 Tokens)
      for (const promo of memoryConfig.promotedProducts || []) {
        if (!promo.active || !promo.triggerKeywords) continue;
        const kws = promo.triggerKeywords.split(/[،,|]+/).map(s => normalizeArabicV112(s)).filter(Boolean);
        if (kws.some(k => normMsg.includes(k) || normalizeArabicV112(productContextName).includes(k))) {
          zeroTokenCounter++;
          const foundProd = allProds.find(
            p =>
              (promo.productId && Number(p.id) === Number(promo.productId)) ||
              cleanProductNameV112(p.name) === cleanProductNameV112(promo.productName)
          );
          const payload = {
            ok: true,
            zeroToken: true,
            reply:
              (promo.promoBadge ? promo.promoBadge + " — " : "⭐ ترشيح خاص لك: ") +
              "«" + promo.productName + "»" +
              (promo.productPrice ? " (" + promo.productPrice + " ر.ي)" : "") +
              "\n" + (promo.promoPitch || ""),
            promotedProduct: promo,
            suggestedItems: foundProd
              ? [
                  {
                    id: foundProd.id,
                    productId: foundProd.id,
                    name: cleanProductNameV112(foundProd.name),
                    price: foundProd.price,
                    unit: foundProd.unit || "حبة",
                    url: promo.productUrl || ("/products?search=" + encodeURIComponent(cleanProductNameV112(foundProd.name)))
                  }
                ]
              : [
                  {
                    id: promo.productId || 1,
                    productId: promo.productId || 1,
                    name: promo.productName,
                    price: promo.productPrice || 100,
                    unit: "حبة",
                    url: promo.productUrl || ("/products?search=" + encodeURIComponent(promo.productName))
                  }
                ]
          };
          responseCache.set(cacheKey, { data: payload, expiresAt: Date.now() + 10 * 60 * 1000 });
          return res.json(payload);
        }
      }

      // 4. Product Modal / Specific Product Question (0 Tokens)
      const targetProd = allProds.find(p => {
        const cn = normalizeArabicV112(cleanProductNameV112(p.name));
        return cn && ((productContextName && cn === normalizeArabicV112(productContextName)) || (cn.length >= 4 && normMsg.includes(cn)));
      });

      if (targetProd) {
        const cleanName = cleanProductNameV112(targetProd.name);
        const pid = String(targetProd.id);
        const meta = memoryConfig.productAiMap[pid] || memoryConfig.productAiMap[cleanName];
        const smart = classifyProductSmartV112(cleanName, meta);

        zeroTokenCounter++;
        let replyText = "";
        if (meta && (meta.customInfo || meta.calories || meta.pairings || meta.prepIdeas)) {
          const parts: string[] = [];
          parts.push("يا غالي، بخصوص «" + cleanName + "» (سعره " + targetProd.price + " ر.ي):");
          if (meta.customInfo) parts.push("✨ معلومات المنتج: " + meta.customInfo);
          if (meta.calories) parts.push("🔥 السعرات والقيمة الغذائية: " + meta.calories);
          if (meta.pairings) parts.push("☕ أفضل ما يؤكل أو يشرب معه: " + meta.pairings);
          if (meta.prepIdeas) parts.push("🍰 أفكار ووصفات به: " + meta.prepIdeas);
          replyText = parts.join("\n");
        } else if (smart.mode === "snacks_and_drinks") {
          replyText =
            "يا غالي، «" + cleanName + "» متوفر بسعر " + targetProd.price + " ر.ي فقط! 😍\n" +
            "💡 معلومات عنه: " + smart.defaultInfo + "\n" +
            "✨ نصيحة سريعة: جربه مع قهوة ساخنة أو عصير بارد من المتجر واستمتع بالطعم الأصلي.";
        } else if (smart.mode === "recipe") {
          replyText =
            "يا هلا بك يا غالي! «" + cleanName + "» (سعره " + targetProd.price + " ر.ي) ممتاز جداً للتحضير:\n" +
            "🍰 فكرة سريعة ولذيذة: " + smart.defaultInfo;
        } else {
          replyText =
            "حياك الله يا غالي! «" + cleanName + "» متوفر في المتجر بسعر " + targetProd.price + " ر.ي.\n" +
            "💡 " + smart.defaultInfo;
        }

        const payload = {
          ok: true,
          zeroToken: true,
          reply: replyText,
          smartChips: smart.chips,
          suggestedItems: [
            {
              id: targetProd.id,
              productId: targetProd.id,
              name: cleanName,
              price: targetProd.price,
              unit: targetProd.unit || "حبة",
              url: "/products?search=" + encodeURIComponent(cleanName)
            }
          ]
        };
        responseCache.set(cacheKey, { data: payload, expiresAt: Date.now() + 10 * 60 * 1000 });
        return res.json(payload);
      }

      // 5. Missing item friendly offer
      const stopWords = new Set(["هل", "عندكم", "في", "متوفر", "اريد", "ابغي", "اشتي", "بكم", "سعر", "وين", "وش", "ايش", "كيف", "طريقه", "عمل", "وصفه", "معلومات", "سعرات"]);
      const words = normMsg.split(" ").filter(w => w.length >= 3 && !stopWords.has(w));
      const matchedProds = allProds.filter(p => {
        const cn = normalizeArabicV112(cleanProductNameV112(p.name));
        return words.some(w => cn.includes(w));
      });

      const asksAvailability = /(عندكم|متوفر|تبيعون|احصل|القي|اشتي|ابغي|اريد|موجود)/.test(normMsg);
      if (asksAvailability && matchedProds.length === 0 && words.length > 0) {
        zeroTokenCounter++;
        const requestedName = words.join(" ");
        const customMissingInst = (memoryConfig.instructions || []).find(i => i.active && i.category === "missing_item");
        const friendlyReply = customMissingInst?.text
          ? customMissingInst.text.replace(/\{المنتج\}/g, requestedName)
          : "فهمتك يا غالي! تقصد «" + requestedName + "».. حلو حلو 👌 حالياً هذا الصنف مو ظاهر قدامي على الرف، بس ولا يهمك! إذا تريده أقدر أتواصل لك مع إدارة المتجر فوراً وأرسل لهم إشعار لهاتفهم يسجلوه لك أو يشوفون لو متوفر بالمخزن. هل تريد أكلم المتجر يوفرونه لك؟ اضغط الزر بالأسفل ويوصلهم طلبك فوراً 👇";
        const payload = {
          ok: true,
          zeroToken: true,
          missingItemOffer: true,
          requestedItemName: requestedName,
          reply: friendlyReply,
          suggestedItems: []
        };
        return res.json(payload);
      }

      zeroTokenCounter++;
      const topMatches = matchedProds.slice(0, 3).map(p => ({
        id: p.id,
        productId: p.id,
        name: cleanProductNameV112(p.name),
        price: p.price,
        unit: p.unit || "حبة",
        url: "/products?search=" + encodeURIComponent(cleanProductNameV112(p.name))
      }));

      if (topMatches.length > 0) {
        const namesList = topMatches.map(m => "«" + m.name + "» (" + m.price + " ر.ي)").join("، و");
        const payload = {
          ok: true,
          zeroToken: true,
          reply: "أبشر يا غالي! فهمت طلبك، وهذي أفضل الأصناف المتوفرة عندنا وتناسبك تماماً: " + namesList + ". تقدر تضيفها للسلة بضغطة زر، وإذا كنت تقصد صنف ثاني غيرها تقدر تطلب مني أكلم المتجر يوفره لك فوراً! ❤️",
          suggestedItems: topMatches,
          canRequestCustomItem: true,
          requestedItemName: userMessage
        };
        responseCache.set(cacheKey, { data: payload, expiresAt: Date.now() + 10 * 60 * 1000 });
        return res.json(payload);
      }

      const customWelcomeInst = (memoryConfig.instructions || []).find(i => i.active && i.category === "welcome");
      const fallbackPayload = {
        ok: true,
        zeroToken: true,
        missingItemOffer: true,
        requestedItemName: userMessage,
        reply: customWelcomeInst?.text
          ? customWelcomeInst.text
          : "حياك الله يا غالي! فهمتك تماماً 👌 بخصوص «" + userMessage + "»، إذا كنت تبحث عن منتج معين غير ظاهر بالمتجر، أقدر أتواصل لك مع إدارة المتجر الآن وأرسل إشعار مباشر لهاتفهم عشان يوفرونه لك ويردون عليك هنا بالمحادثة! هل تريد أكلم المتجر لك؟ 👇",
        suggestedItems: []
      };
      return res.json(fallbackPayload);
    } catch (e: any) {
      res.status(500).json({ ok: false, error: String(e?.message || e) });
    }
  });
}
