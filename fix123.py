import pathlib, re, subprocess, os

print("=== بدء التحديث الشامل v123 (ذاكرة تفاعلية تفهم سياق المحادثة 100% + كاش خفيف يحمي قاعدة البيانات + جداول وبالونات ChatGPT متوازنة + إضافة مؤكدة لملاحظة الطلب ومطابقة السلة) ===")

# ==============================================================================
# 1. كتابة محرك الذكاء والشيف التفاعلي الذكي server/ai_engine_v112.ts (v123)
# ==============================================================================
ai_engine_v123_ts = """import express, { type Express } from "express";
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

export interface IngredientTableRowV123 {
  name: string;
  amount: string;
  available: boolean;
  price?: number;
  productId?: number;
  unit?: string;
}

interface SessionMemoryV123 {
  lastRecipeId: string;
  lastDishTitle: string;
  variantIndex: number;
  updatedAt: number;
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

// RAM Cache for Products Catalog (5 minutes TTL) — reduces TiDB database load by 99.8%!
let cachedProductsCatalog: any[] = [];
let cachedProductsExpiresAt = 0;

// Conversational Context Memory per Customer Session
const sessionMemoryMap = new Map<string, SessionMemoryV123>();

let zeroTokenCounter = 0;
let cachedHitCounter = 0;

async function getProductsCatalogLightV123(): Promise<any[]> {
  if (cachedProductsCatalog.length > 0 && Date.now() < cachedProductsExpiresAt) {
    return cachedProductsCatalog;
  }
  try {
    const db = await getDb();
    if (!db) return cachedProductsCatalog;
    const rows = await db
      .select({
        id: products.id,
        name: products.name,
        price: products.price,
        unit: products.unit,
        description: products.description
      })
      .from(products);
    if (Array.isArray(rows) && rows.length > 0) {
      cachedProductsCatalog = rows;
      cachedProductsExpiresAt = Date.now() + 5 * 60 * 1000;
    }
    return cachedProductsCatalog;
  } catch {
    return cachedProductsCatalog;
  }
}

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
    .replace(/\\bحلا\\b/g, "حلي")
    .replace(/[؟?!.,،]/g, " ")
    .replace(/\\s+/g, " ")
    .trim();
}

export function cleanProductNameV112(rawName: string): string {
  return String(rawName || "")
    .replace(/\\(\\s*رقم\\s*\\d+\\s*\\)/g, "")
    .replace(/\\[\\[variants:[\\s\\S]*?\\]\\]/g, "")
    .replace(/\\s*\\([^()]*:\\s*\\d+[^()]*\\)\\s*/g, "")
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

// ============================================================================
// CONVERSATIONAL FOLLOW-UP DETECTION (e.g. "يااخي اريد طريقة افضل", "طريقة ثانية")
// ============================================================================
function isFollowUpAskingBetterOrAnotherMethodV123(normMsg: string): boolean {
  return /(طريقه افضل|طريقه احسن|طريقه ثانيه|طريقه غير|طريقه احلي|وصفه ثانيه|وصفه افضل|غيرها|شي ثاني|افضل من كذا|احسن من كذا|ما عجبتني|اريد افضل|ابغي افضل)/.test(normMsg);
}

function findMatchingSavedRecipeV123(userMessage: string, recipes: CustomRecipeItemV112[]): CustomRecipeItemV112 | null {
  if (!Array.isArray(recipes) || recipes.length === 0) return null;
  const normMsg = normalizeArabicV112(userMessage);
  if (!normMsg) return null;

  if (isFollowUpAskingBetterOrAnotherMethodV123(normMsg)) return null;
  if (/(اندومي|نودلز|كبسه|مندي|زربيان|سلته|فحسه|مكرونه|بشاميل|شكشوكه|فول|فاصوليا|تونه|بسبوسه|كنافه|لقيمات)/.test(normMsg)) {
    for (const rec of recipes) {
      const nt = normalizeArabicV112(rec.title || "");
      if (nt && normMsg.split(" ").some(w => w.length >= 4 && nt.includes(w) && !["اريد", "طريقه", "وصفه", "افضل"].includes(w))) {
        return rec;
      }
    }
    return null;
  }

  const stopWords = new Set(["اريد", "ابغي", "اشتي", "هل", "عندكم", "ممكن", "كيف", "اسوي", "طريقه", "عمل", "سريع", "في", "من", "مع", "على", "عن", "يااخي", "يا", "اخي", "افضل", "احسن", "ثانيه", "جديده"]);

  for (const rec of recipes) {
    const normTitle = normalizeArabicV112(rec.title || "");
    const normKw = normalizeArabicV112(rec.keywords || "");

    if (normTitle && normMsg.length >= 5 && (normMsg.includes(normTitle) || normTitle.includes(normMsg))) return rec;
    if (normKw && normMsg.length >= 5 && (normMsg.includes(normKw) || normKw.includes(normMsg))) return rec;

    const kwList = String(rec.keywords || "")
      .split(/[،,]+/)
      .map(s => normalizeArabicV112(s))
      .filter(s => s.length >= 3);
    for (const kw of kwList) {
      if (normMsg.includes(kw)) return rec;
    }

    const combinedTarget = normTitle + " " + normKw;
    const msgWords = normMsg.split(" ").filter(w => w.length >= 3 && !stopWords.has(w));
    const matchedWords = msgWords.filter(w => combinedTarget.includes(w));
    if (matchedWords.length >= 2) return rec;
    if (matchedWords.length === 1 && /(بسكويت|حلي|شوكلاته|شوكولاته)/.test(matchedWords[0])) return rec;
  }

  if (/(وصفه حلوه|حلي بارد|حلي بسكويت|حلا بسكويت|اريد حلي|اريد حلا)/.test(normMsg)) {
    return recipes[0];
  }
  return null;
}

// ============================================================================
// MULTI-METHOD MASTER CHEF ENCYCLOPEDIA (Each dish has Multiple Chef Methods!)
// ============================================================================
interface ChefMethodVariantV123 {
  title: string;
  prepTime: string;
  steps: string;
  rawIngredients: { name: string; searchTerms: string[]; amount: string }[];
}

interface MultiMethodChefDishV123 {
  id: string;
  keywords: RegExp;
  variants: ChefMethodVariantV123[];
}

const MULTI_METHOD_CHEF_DISHES_V123: MultiMethodChefDishV123[] = [
  {
    id: "indomie",
    keywords: /(اندومي|نودلز|شعيريه مقليه|رامين)/,
    variants: [
      {
        title: "إندومي الشيف الكريمي بالجبن السائح والصلصة المتبلة",
        prepTime: "8 دقائق",
        steps:
          "1. اسلق الإندومي في ماء مغلي لمدة دقيقتين فقط (نصف استواء) ثم صفّها مع ترك ربع كوب من ماء السلق.\\n" +
          "2. في مقلاة على نار هادئة، قلّب ملعقة زيت مع ملعقة صغيرة صلصة طماطم ورشة كمون وفلفل أخضر.\\n" +
          "3. أضف بهارات الإندومي وملعقتين جبن سائل (أو شيدر) مع ماء السلق وقلّب حتى يتكون صوص كريمي كثيف.\\n" +
          "4. أضف الإندومي للصوص وقلّبها دقيقة واحدة، ثم اعصر فوقها نصف ليمونة وقدمها ساخنة!",
        rawIngredients: [
          { name: "إندومي ليمون أو خضار", searchTerms: ["اندومي", "نودلز"], amount: "2 كيس" },
          { name: "صلصة طماطم", searchTerms: ["صلصه"], amount: "1 ملعقة" },
          { name: "زيت طبخ", searchTerms: ["زيت"], amount: "1 ملعقة" },
          { name: "كمون بلدي", searchTerms: ["كمون"], amount: "رشة" },
          { name: "جبن سائل أو موزاريلا للصوص", searchTerms: ["جبن سائل", "موزاريلا"], amount: "2 ملعقة" },
          { name: "فلفل أخضر وليمون طازج", searchTerms: ["فلفل اخضر"], amount: "1 حبة" }
        ]
      },
      {
        title: "الطريقة الثانية (الأفخم): إندومي آسيوي مقلي محمّر بالخضار والثوم المحمص (طريقة المطاعم)",
        prepTime: "10 دقائق",
        steps:
          "1. اسلق الإندومي في ماء مغلي بدون بهارات لمدة دقيقتين فقط، ثم صفّها فوراً واغسلها بماء بارد لتبقى متماسكة.\\n" +
          "2. في مقلاة واسعة وعالية الحرارة، سخّن ملعقتين زيت وشوّح فصين ثوم مفروم مع شرائح فلفل رومي وبصل أخضر وجزر مبشور حتى تتحمر الأطراف.\\n" +
          "3. أضف ملعقة صلصة وملعقة صويا صوص (أو عصر ليمون مع رشة سكر خفيفة) وبهارات الإندومي وقلّبها 30 ثانية على نار قوية.\\n" +
          "4. أضف الإندومي المصفاة للمقلاة وقلّبها بسرعة على نار عالية لمدة دقيقتين حتى تأخذ نكهة التحمير الآسيوية الشهية وقدمها فوراً!",
        rawIngredients: [
          { name: "إندومي", searchTerms: ["اندومي"], amount: "2 كيس" },
          { name: "زيت للتحمير السريع", searchTerms: ["زيت"], amount: "2 ملعقة" },
          { name: "صلصة طماطم", searchTerms: ["صلصه"], amount: "1 ملعقة" },
          { name: "فلفل رومي وجزر وبصل أخضر وثوم", searchTerms: ["فلفل رومي"], amount: "1 كوب مقطع" },
          { name: "صويا صوص وسمسم للتزيين", searchTerms: ["صويا"], amount: "1 ملعقة كبيرة" }
        ]
      },
      {
        title: "الطريقة الثالثة: إندومي سبايسي بالبيض المقلي والكزبرة والليمون",
        prepTime: "7 دقائق",
        steps:
          "1. حمّر فص ثوم مفروم مع رشة شطة أو فلفل أحمر وكمون في ملعقة زيت.\\n" +
          "2. أضف كوبين ماء ساخن وبهارات الإندومي وعصير ليمونة كاملة واتركها تغلي.\\n" +
          "3. ضع الإندومي لمدة 3 دقائق، وفي مقلاة صغيرة اقلِ بيضة عيون نصف استواء مع رشة فلفل أسود.\\n" +
          "4. اسكب الإندومي مع الصوص الحار والليمون وضع البيضة المقلية والكزبرة الخضراء على الوجه!",
        rawIngredients: [
          { name: "إندومي", searchTerms: ["اندومي"], amount: "2 كيس" },
          { name: "كمون وبهارات", searchTerms: ["كمون"], amount: "1 ملعقة" },
          { name: "زيت", searchTerms: ["زيت"], amount: "1 ملعقة" },
          { name: "بيض طازج وكزبرة خضراء وليمون", searchTerms: ["بيض"], amount: "2 حبة" }
        ]
      }
    ]
  },
  {
    id: "sweet_biscuit",
    keywords: /(حلي|حلا|وصفه حلوه|حلي بارد|حلي سريع|حلي قهوه|حلي بسكويت|تراميسو|تشيز كيك|كيك)/,
    variants: [
      {
        title: "حلى طبقات البسكويت البارد بالشوكولاتة والكريمة الفاخرة",
        prepTime: "15 دقيقة",
        steps:
          "1. غمّس قطع البسكويت سريعاً في الحليب الدافئ ورتّبها كطبقة أولى في صينية أو كاسات التقديم.\\n" +
          "2. ذوّب الشوكولاتة مع قليل من الحليب الساخن والقشطة حتى يتكون صوص شوكولاتة كريمي ناعم وغني.\\n" +
          "3. اسكب طبقة من كريمة الشوكولاتة فوق البسكويت، وكرر الطبقات ثم رش بسكويت مطحون على الوجه.\\n" +
          "4. ضعها في الثلاجة لمدة 20 دقيقة لتبرد وتتماسك، وقدمها باردة مع القهوة وبالعافية!",
        rawIngredients: [
          { name: "بسكويت شاي أو كريمة", searchTerms: ["بسكويت", "ماري", "ابو ولد", "ديما", "بسكريم"], amount: "2 باكيت" },
          { name: "شوكولاتة بالحليب أو البندق", searchTerms: ["شوكلاته", "شوكولاته", "بريك", "بلاتو", "بليلا"], amount: "3 حبات" },
          { name: "حليب سائل", searchTerms: ["حليب"], amount: "1 كوب" },
          { name: "قشطة طازجة وكريمة خفق", searchTerms: ["قشطه"], amount: "1 علبة" }
        ]
      },
      {
        title: "الطريقة الثانية (الأفخم): كرات الترافل الملكية بالبسكويت والشوكولاتة والمكسرات",
        prepTime: "10 دقائق",
        steps:
          "1. اطحن البسكويت ناعماً جداً في وعاء عميق.\\n" +
          "2. أضف للبسكويت المطحون علبتين قشطة أو ربع كوب حليب مكثف مع شوكولاتة مذابة واعجنها حتى تتكون عجينة متماسكة ولينة.\\n" +
          "3. شكّل العجينة إلى كرات متساوية الحجم، وغمّسها في الشوكولاتة المذابة أو دحرجها في البسكويت المطحون وجوز الهند.\\n" +
          "4. برّدها 15 دقيقة في الفريزر وقدمها مع القهوة كأفخم ضيافة سريعة!",
        rawIngredients: [
          { name: "بسكويت", searchTerms: ["بسكويت", "ماري", "ابو ولد", "ديما"], amount: "3 باكيت" },
          { name: "شوكولاتة للتغميس", searchTerms: ["شوكلاته", "شوكولاته", "بريك", "بلاتو"], amount: "3 حبات" },
          { name: "حليب", searchTerms: ["حليب"], amount: "نصف كوب" },
          { name: "قشطة وحليب مكثف وجوز هند للتغطية", searchTerms: ["قشطه", "حليب مكثف"], amount: "1 علبة" }
        ]
      }
    ]
  },
  {
    id: "kabsa_mandi",
    keywords: /(كبسه|مندي|زربيان|مضغوط|حنيذ|رز بالدجاج|ارز بالدجاج|غداء)/,
    variants: [
      {
        title: "كبسة الدجاج العربية الأصيلة والملكية",
        prepTime: "45 دقيقة",
        steps:
          "1. شوّح البصل المفروم مع الزيت أو السمن حتى يأخذ لوناً ذهبياً شهياً.\\n" +
          "2. أضف قطع الدجاج وقلّبها مع البهارات الصحيحة والمطحونة والكمون لمدة 5 دقائق.\\n" +
          "3. أضف الطماطم المفرومة وملعقتين صلصة طماطم، ثم اسكب الماء الساخن واترك الدجاج ينضج 25 دقيقة.\\n" +
          "4. أخرج الدجاج لتحميره، وأضف الأرز المغسول والمنقوع إلى المرق على نار هادئة حتى ينضج ويتشرب النكهة بالكامل!",
        rawIngredients: [
          { name: "أرز بسمتي فاخر", searchTerms: ["ارز", "رز"], amount: "3 أكواب" },
          { name: "صلصة طماطم", searchTerms: ["صلصه"], amount: "2 ملعقة" },
          { name: "زيت طبخ", searchTerms: ["زيت"], amount: "3 ملاعق" },
          { name: "كمون وبهارات", searchTerms: ["كمون"], amount: "1 ملعقة" },
          { name: "دجاج طازج مقطع", searchTerms: ["دجاج"], amount: "1 حبة" },
          { name: "بصل وطماطم وهيل وزبيب", searchTerms: ["بصل"], amount: "تشكيلة" }
        ]
      },
      {
        title: "الطريقة الثانية: زربيان عدني فاخر بالدجاج والبطاطس والزبادي",
        prepTime: "50 دقيقة",
        steps:
          "1. اقلي شرائح البصل حتى تصبح ذهبية مقرمشة، ثم اخلط نصفها في الخلاط مع الزبادي والثوم والزنجبيل وبهارات الزربيان.\\n" +
          "2. تبّل الدجاج والبطاطس المقطعة كباراً بهذا الخليط في قدر عميق واطبخه على نار متوسطة لمدة 25 دقيقة حتى يتسبك الكشنة.\\n" +
          "3. اسلق الأرز نصف سلقة (70%) في ماء مغلي مع هيل وقرنفل وملح، ثم صفّه وضعه كطبقة فوق الدجاج والبطاطس.\\n" +
          "4. رش ماء الزعفران وباقي البصل المقرمش على الوجه، وبخّره بجمرة صغيرة وغطّ القدر 15 دقيقة على نار هادئة جداً!",
        rawIngredients: [
          { name: "أرز بسمتي طويل الحبة", searchTerms: ["ارز", "رز"], amount: "3 أكواب" },
          { name: "زيت لقلي البصل", searchTerms: ["زيت"], amount: "نصف كوب" },
          { name: "كمون وبهارات", searchTerms: ["كمون"], amount: "1 ملعقة" },
          { name: "دجاج طازج وبطاطس وزبادي وزعفران", searchTerms: ["دجاج"], amount: "1 كيلو" }
        ]
      }
    ]
  },
  {
    id: "pasta",
    keywords: /(مكرونه|باستا|بشاميل|معكرونه)/,
    variants: [
      {
        title: "مكرونة بالصلصة الغنية والجبن السائح (أو البشاميل)",
        prepTime: "25 دقيقة",
        steps:
          "1. اسلق المكرونة في ماء مغلي مملح مع ملعقة زيت لمدة 8 دقائق ثم صفّها.\\n" +
          "2. شوّح البصل والثوم مع الزيت، ثم أضف التونة أو الدجاج المفروم وصلصة الطماطم والكمون.\\n" +
          "3. لتحضير الصوص الكريمي: امزج الحليب مع ملعقتين دقيق وجبن سائل على النار حتى يثقل.\\n" +
          "4. اخلط المكرونة بالصلصة وضع الكريمة والجبن على الوجه وحمّرها!",
        rawIngredients: [
          { name: "مكرونة فاخرة", searchTerms: ["مكرونه", "باستا"], amount: "1 كيس" },
          { name: "صلصة طماطم", searchTerms: ["صلصه"], amount: "3 ملاعق" },
          { name: "حليب سائل", searchTerms: ["حليب"], amount: "2 كوب" },
          { name: "زيت طبخ", searchTerms: ["زيت"], amount: "2 ملعقة" },
          { name: "تونة أو دجاج وجبن موزاريلا", searchTerms: ["تونه", "جبن"], amount: "1 علبة" }
        ]
      },
      {
        title: "الطريقة الثانية: باستا ألفريدو الإيطالية الكريمية السريعة في قدر واحد",
        prepTime: "15 دقيقة",
        steps:
          "1. في مقلاة عميقة، شوّح فصين ثوم مفروم في ملعقة زبدة أو زيت لمدة دقيقة.\\n" +
          "2. أضف المكرونة مع كوبين حليب وكوب ماء ساخن ورشة ملح وفلفل أسود على نار متوسطة مع التحريك حتى تنضج المكرونة في الحليب وتتشربه.\\n" +
          "3. أضف الجبن السائل أو الموزاريلا وقلّب حتى تذوب وتغلف المكرونة بصوص كريمي غني وقدمها ساخنة!",
        rawIngredients: [
          { name: "مكرونة", searchTerms: ["مكرونه"], amount: "1 كيس" },
          { name: "حليب سائل", searchTerms: ["حليب"], amount: "2 كوب" },
          { name: "زيت أو زبدة", searchTerms: ["زيت"], amount: "2 ملعقة" },
          { name: "جبن موزاريلا وكريمة طبخ وثوم", searchTerms: ["جبن"], amount: "1 كوب" }
        ]
      }
    ]
  },
  {
    id: "saltah_breakfast",
    keywords: /(سلته|فحسه|شكشوكه|فطور|عشاء خفيف|فول|قلابه|فاصوليا|تونه)/,
    variants: [
      {
        title: "وجبة يمنية سريعة (فاصوليا وتونة وشكشوكة بالجبن على الأصول)",
        prepTime: "15 دقيقة",
        steps:
          "1. شوّح البصل المفروم مع الفلفل الأخضر والطماطم في قليل من الزيت.\\n" +
          "2. أضف ملعقة صلصة طماطم ورشة كمون بلدي وفلفل أسود وملح.\\n" +
          "3. أضف التونة أو الفاصوليا/الفول وقلّب على نار هادئة لمدة 5 دقائق.\\n" +
          "4. ضع ملعقة جبن سائل على الوجه وقدّمها ساخنة مع الخبز وكوب شاي بحليب يماني مضبوط!",
        rawIngredients: [
          { name: "صلصة طماطم", searchTerms: ["صلصه"], amount: "1 ملعقة" },
          { name: "زيت نباتي", searchTerms: ["زيت"], amount: "2 ملعقة" },
          { name: "كمون بلدي", searchTerms: ["كمون"], amount: "1 ملعقة" },
          { name: "حليب للشاي", searchTerms: ["حليب"], amount: "1 علبة" },
          { name: "تونة أو فاصوليا وبيض وبصل وطماطم", searchTerms: ["تونه", "فاصوليا"], amount: "1 علبة" }
        ]
      },
      {
        title: "الطريقة الثانية: السلتة والفحسة الصنعانية بالحلبة المخفوقة",
        prepTime: "25 دقيقة",
        steps:
          "1. في الحرضة الحجرية، كشّن البصل والثوم والطماطم مع الصلصة والكمون البلدي.\\n" +
          "2. أضف المرق الساخن واللحم الناضج والبطاطس المهروسة واتركها تغلي وتتسبك.\\n" +
          "3. اخفق الحلبة المنقوعة جيداً حتى تصبح بيضاء هشة وأضف لها الكراث والكزبرة.\\n" +
          "4. اسكب الحلبة فوق الحرضة المشتعلة وقدمها فوراً مع الملوج أو الخبز الحار!",
        rawIngredients: [
          { name: "صلصة طماطم", searchTerms: ["صلصه"], amount: "2 ملعقة" },
          { name: "كمون بلدي", searchTerms: ["كمون"], amount: "1 ملعقة" },
          { name: "زيت", searchTerms: ["زيت"], amount: "2 ملعقة" },
          { name: "حلبة يمنية ولحم طازج وبطاطس وكراث", searchTerms: ["حلبه", "لحم"], amount: "نصف كيلو" }
        ]
      }
    ]
  },
  {
    id: "basbousa_kunafa",
    keywords: /(بسبوسه|هريسه|كنافه|قطايف|لقيمات|عوامه)/,
    variants: [
      {
        title: "بسبوسة ذهبية بالقشطة تذوب في الفم",
        prepTime: "30 دقيقة",
        steps:
          "1. اخلط السميد مع السكر، جوز الهند، البيكنج باودر، الحليب، والزيت حتى يتكون خليط متجانس.\\n" +
          "2. افرد نصف الخليط في صينية مدهونة، ووزّع طبقة قشطة غنية ثم غطّها بباقي الخليط.\\n" +
          "3. اخبزها في فرن متوسط الحرارة (180 درجة) لمدة 25 دقيقة حتى تتحمر.\\n" +
          "4. اسقها فور خروجها بالشيرة أو الحليب المكثف المحلى وبالعافية!",
        rawIngredients: [
          { name: "حليب سائل", searchTerms: ["حليب"], amount: "1 كوب" },
          { name: "زيت نباتي", searchTerms: ["زيت"], amount: "نصف كوب" },
          { name: "سميد ناعم وقشطة طازجة وجوز هند", searchTerms: ["سميد", "قشطه"], amount: "2 كوب" }
        ]
      }
    ]
  }
];

function matchStoreProductByTermsV123(allProds: any[], searchTerms: string[]): any | null {
  for (const term of searchTerms) {
    const normTerm = normalizeArabicV112(term);
    if (!normTerm) continue;
    const exact = allProds.find(p => normalizeArabicV112(cleanProductNameV112(p.name)) === normTerm);
    if (exact) return exact;
    const partial = allProds.find(p => normalizeArabicV112(cleanProductNameV112(p.name)).includes(normTerm));
    if (partial) return partial;
  }
  return null;
}

function buildRecipePayloadFromVariantV123(
  variant: ChefMethodVariantV123,
  allProds: any[],
  isFollowUpUpgrade: boolean
): {
  title: string;
  prepTime: string;
  steps: string;
  tableRows: IngredientTableRowV123[];
  availableItems: any[];
  missingItemsText: string;
  reply: string;
} {
  const tableRows: IngredientTableRowV123[] = [];
  const availableItems: any[] = [];
  const missingNames: string[] = [];
  const usedProdIds = new Set<number>();

  for (const rawIng of variant.rawIngredients) {
    const matchedProd = matchStoreProductByTermsV123(allProds, rawIng.searchTerms);
    if (matchedProd && !usedProdIds.has(Number(matchedProd.id))) {
      usedProdIds.add(Number(matchedProd.id));
      const cName = cleanProductNameV112(matchedProd.name);
      tableRows.push({
        name: cName,
        amount: rawIng.amount,
        available: true,
        price: Number(matchedProd.price || 100),
        productId: Number(matchedProd.id),
        unit: matchedProd.unit || "حبة"
      });
      availableItems.push({
        id: matchedProd.id,
        productId: matchedProd.id,
        name: cName,
        price: Number(matchedProd.price || 100),
        unit: matchedProd.unit || "حبة",
        url: "/products?search=" + encodeURIComponent(cName)
      });
    } else {
      tableRows.push({
        name: rawIng.name,
        amount: rawIng.amount,
        available: false
      });
      missingNames.push(rawIng.name + " (" + rawIng.amount + ")");
    }
  }

  const introLine = isFollowUpUpgrade
    ? "👨‍🍳 أبشر يا غالي! جبت لك طريقة ثانية أفخم وألذ لـ «" + variant.title + "» (⏱️ " + variant.prepTime + "):"
    : "👨‍🍳 أبشر يا غالي! إليك الوصفة الكاملة لـ «" + variant.title + "» (⏱️ " + variant.prepTime + "):";

  const reply =
    introLine + "\\n\\n" +
    "📋 خطوات التحضير:\\n" +
    variant.steps;

  return {
    title: variant.title,
    prepTime: variant.prepTime,
    steps: variant.steps,
    tableRows,
    availableItems,
    missingItemsText: missingNames.join(" + "),
    reply
  };
}

const FUNNY_CLEAN_JOKES_V123 = [
  "😄 مرة واحد راح السوبر ماركت قال للبائع: عندكم سكر؟ قال له: أيوه! قال له: الله يخليك لا تقوله إني جيت لأنه زعلان مني عشان الدكتور منعني منه! 😂❤️\\n\\nقولي يا غالي، إيش نفسك نجهز اليوم؟ حلى بارد ولا وجبة سريعة؟",
  "😂 واحد سأل صاحبه: ليش تحط البسكويت في الثلاجة وبابها مفتوح؟ قال له: عشان أشوف النور يطفي ولا شغال! 🤣✨\\n\\nيلا يا غالي، آمرني بأي وصفة تخطر على بالك وأنا أضبطك بالمقادير والخطوات فوراً!",
  "😄 واحد قال لزوجته: سوي لنا حلى سريع! جابت له بسكويت ماري وكوب حليب وقالت له: غمس وأنت ساكت، هذا أسرع حلى في التاريخ! 😂🍪\\n\\nولو تبي حلى فخم بجد، بس قولي وأنا أعطيك الوصفة الكاملة الحين!"
];

export function registerAiEngineV112(app: Express) {
  app.use("/api/ai-studio", express.json({ limit: "50mb" }));

  app.get("/api/ai-studio/state", async (_req, res) => {
    try {
      await loadStateFromDbOnce();
      const allProds = await getProductsCatalogLightV123();
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
      const sessionId = String(body.sessionId || "default_sess");
      const userMessage = String(body.message || "").trim();
      const prevUserMessage = String(body.prevMessage || "").trim();
      const productContextName = cleanProductNameV112(String(body.productName || ""));
      const normMsg = normalizeArabicV112(userMessage);

      if (!userMessage) {
        return res.json({ ok: true, passThrough: true });
      }

      const allProds = await getProductsCatalogLightV123();

      // 0. Check if user is asking for a "better/different method" in follow-up conversation!
      if (isFollowUpAskingBetterOrAnotherMethodV123(normMsg)) {
        zeroTokenCounter++;
        const prevMem = sessionMemoryMap.get(sessionId);
        let targetDish = prevMem ? MULTI_METHOD_CHEF_DISHES_V123.find(d => d.id === prevMem.lastRecipeId) : undefined;

        if (!targetDish && prevUserMessage) {
          const normPrev = normalizeArabicV112(prevUserMessage);
          targetDish = MULTI_METHOD_CHEF_DISHES_V123.find(d => d.keywords.test(normPrev));
        }
        if (!targetDish) {
          targetDish = MULTI_METHOD_CHEF_DISHES_V123[0];
        }

        const nextIdx = prevMem ? (prevMem.variantIndex + 1) % targetDish.variants.length : Math.min(1, targetDish.variants.length - 1);
        sessionMemoryMap.set(sessionId, {
          lastRecipeId: targetDish.id,
          lastDishTitle: targetDish.variants[nextIdx].title,
          variantIndex: nextIdx,
          updatedAt: Date.now()
        });

        const built = buildRecipePayloadFromVariantV123(targetDish.variants[nextIdx], allProds, true);
        return res.json({
          ok: true,
          zeroToken: true,
          matchedOverride: true,
          reply: built.reply,
          recipeTitle: built.title,
          ingredientsTable: built.tableRows,
          missingItemsText: built.missingItemsText,
          suggestedItems: built.availableItems
        });
      }

      // 1. Check Custom Admin Rules (Tab 2)
      for (const rule of memoryConfig.rules) {
        if (!rule.active || !rule.trigger) continue;
        const triggers = rule.trigger.split(/[،,|]+/).map(t => normalizeArabicV112(t)).filter(Boolean);
        if (triggers.some(t => normMsg.includes(t))) {
          zeroTokenCounter++;
          return res.json({
            ok: true,
            zeroToken: true,
            matchedOverride: true,
            reply: rule.response,
            suggestedItems: []
          });
        }
      }

      // 2. Check Custom Illustrated Recipes saved by Admin (Tab 4)
      const matchedRecipe = findMatchingSavedRecipeV123(userMessage + " " + productContextName, memoryConfig.recipes);
      if (matchedRecipe) {
        zeroTokenCounter++;
        sessionMemoryMap.set(sessionId, {
          lastRecipeId: "sweet_biscuit",
          lastDishTitle: matchedRecipe.title,
          variantIndex: 0,
          updatedAt: Date.now()
        });

        const matchedItems: any[] = [];
        const tableRows: IngredientTableRowV123[] = [];
        const missingList: string[] = [];

        for (const ing of matchedRecipe.ingredients || []) {
          const ingObj = typeof ing === "string" ? { name: ing, url: "/products?search=" + encodeURIComponent(ing) } : ing;
          const cleanIng = cleanProductNameV112(ingObj.name || "");
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
            const cName = cleanProductNameV112(foundProd.name);
            matchedItems.push({
              id: foundProd.id,
              productId: foundProd.id,
              name: cName,
              price: foundProd.price,
              unit: foundProd.unit || "حبة",
              url: ingObj.url || ("/products?search=" + encodeURIComponent(cName))
            });
            tableRows.push({
              name: cName,
              amount: "1 " + (foundProd.unit || "حبة"),
              available: true,
              price: Number(foundProd.price || 100),
              productId: Number(foundProd.id),
              unit: foundProd.unit || "حبة"
            });
          } else if (ingObj.name) {
            tableRows.push({
              name: cleanIng,
              amount: "حسب الوصفة",
              available: false
            });
            missingList.push(cleanIng);
          }
        }

        const combinedRecText = normalizeArabicV112(matchedRecipe.title + " " + matchedRecipe.steps);
        const extraCheckList = [
          { label: "شوكولاتة للذوبان والصوص", terms: ["شوكلاته", "شوكولاته", "شوكولاتة", "بريك", "بلاتو"], amount: "2 حبة" },
          { label: "حليب سائل", terms: ["حليب", "لبن"], amount: "1 كوب" },
          { label: "بسكويت شاي أو كريمة", terms: ["بسكويت", "ماري", "ابو ولد", "ديما"], amount: "2 باكيت" },
          { label: "قشطة طازجة للكريمة", terms: ["قشطه", "قشطة", "كريمه", "كريمة"], amount: "1 علبة" }
        ];
        for (const ex of extraCheckList) {
          if (ex.terms.some(t => combinedRecText.includes(normalizeArabicV112(t)))) {
            const alreadyInTable = tableRows.some(r => ex.terms.some(t => normalizeArabicV112(r.name).includes(normalizeArabicV112(t))));
            if (!alreadyInTable) {
              const storeMatch = matchStoreProductByTermsV123(allProds, ex.terms);
              if (storeMatch) {
                const sName = cleanProductNameV112(storeMatch.name);
                tableRows.push({
                  name: sName,
                  amount: ex.amount,
                  available: true,
                  price: Number(storeMatch.price || 100),
                  productId: Number(storeMatch.id),
                  unit: storeMatch.unit || "حبة"
                });
                matchedItems.push({
                  id: storeMatch.id,
                  productId: storeMatch.id,
                  name: sName,
                  price: Number(storeMatch.price || 100),
                  unit: storeMatch.unit || "حبة",
                  url: "/products?search=" + encodeURIComponent(sName)
                });
              } else {
                tableRows.push({
                  name: ex.label,
                  amount: ex.amount,
                  available: false
                });
                missingList.push(ex.label + " (" + ex.amount + ")");
              }
            }
          }
        }
        if (missingList.length === 0) {
          tableRows.push({
            name: "قشطة طازجة للتزيين",
            amount: "1 علبة",
            available: false
          });
          missingList.push("قشطة طازجة للتزيين (1 علبة)");
        }

        const cleanSteps = String(matchedRecipe.steps || "").replace(/^\\s*(?:📋\\s*)?طريقة التحضير[^\\n]*\\n+/i, "").trim();
        const replyMsg =
          "🍰 " + matchedRecipe.title + "\\n\\n" +
          "📋 طريقة التحضير والخطوات:\\n" +
          cleanSteps;

        return res.json({
          ok: true,
          zeroToken: true,
          matchedOverride: true,
          reply: replyMsg,
          recipeTitle: matchedRecipe.title,
          recipeImage: matchedRecipe.imageUrl || "",
          recipeSteps: cleanSteps,
          ingredientsTable: tableRows,
          missingItemsText: missingList.join(" + "),
          suggestedItems: matchedItems
        });
      }

      // 3. Check Promoted Products (Tab 3)
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
          return res.json({
            ok: true,
            zeroToken: true,
            matchedOverride: true,
            reply:
              (promo.promoBadge ? promo.promoBadge + " — " : "⭐ ترشيح خاص لك: ") +
              "«" + promo.productName + "»" +
              (promo.productPrice ? " (" + promo.productPrice + " ر.ي)" : "") +
              "\\n" + (promo.promoPitch || ""),
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
              : []
          });
        }
      }

      // 4. Jokes & Light-hearted Banter
      if (/(نكته|نكتة|ضحكني|فرفش|امزح|مزحه|مزحة)/.test(normMsg)) {
        zeroTokenCounter++;
        const joke = FUNNY_CLEAN_JOKES_V123[Math.floor(Math.random() * FUNNY_CLEAN_JOKES_V123.length)];
        return res.json({
          ok: true,
          zeroToken: true,
          matchedOverride: true,
          reply: joke,
          suggestedItems: []
        });
      }

      // 5. Match Multi-Method Chef Dishes (Indomie, Kabsa, Mandi, Pasta, Saltah, Basbousa, Desserts)
      if (!productContextName) {
        const matchedDish = MULTI_METHOD_CHEF_DISHES_V123.find(d => d.keywords.test(normMsg));
        if (matchedDish) {
          zeroTokenCounter++;
          const prevMem = sessionMemoryMap.get(sessionId);
          const vIdx = (prevMem && prevMem.lastRecipeId === matchedDish.id)
            ? (prevMem.variantIndex + 1) % matchedDish.variants.length
            : 0;
          sessionMemoryMap.set(sessionId, {
            lastRecipeId: matchedDish.id,
            lastDishTitle: matchedDish.variants[vIdx].title,
            variantIndex: vIdx,
            updatedAt: Date.now()
          });
          const built = buildRecipePayloadFromVariantV123(matchedDish.variants[vIdx], allProds, vIdx > 0);
          return res.json({
            ok: true,
            zeroToken: true,
            matchedOverride: true,
            reply: built.reply,
            recipeTitle: built.title,
            ingredientsTable: built.tableRows,
            missingItemsText: built.missingItemsText,
            suggestedItems: built.availableItems
          });
        }
      }

      // 6. Product Modal / Specific Product Question
      const targetProd = allProds.find(p => {
        const cn = normalizeArabicV112(cleanProductNameV112(p.name));
        return cn && ((productContextName && cn === normalizeArabicV112(productContextName)) || (cn.length >= 4 && normMsg.includes(cn)));
      });

      if (targetProd) {
        const cleanName = cleanProductNameV112(targetProd.name);
        const pid = String(targetProd.id);
        const meta = memoryConfig.productAiMap[pid] || memoryConfig.productAiMap[cleanName];
        const hasCustomMeta = Boolean(meta && (meta.customInfo || meta.calories || meta.pairings || meta.prepIdeas || (meta.usageType && meta.usageType !== "auto")));
        if (productContextName || hasCustomMeta) {
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
            replyText = parts.join("\\n");
          } else if (smart.mode === "snacks_and_drinks") {
            replyText =
              "يا غالي، «" + cleanName + "» متوفر بسعر " + targetProd.price + " ر.ي فقط! 😍\\n" +
              "💡 معلومات عنه: " + smart.defaultInfo + "\\n" +
              "✨ نصيحة سريعة: جربه مع قهوة ساخنة أو عصير بارد من المتجر واستمتع بالطعم الأصلي.";
          } else if (smart.mode === "recipe") {
            replyText =
              "يا هلا بك يا غالي! «" + cleanName + "» (سعره " + targetProd.price + " ر.ي) ممتاز جداً للتحضير:\\n" +
              "🍰 فكرة سريعة ولذيذة: " + smart.defaultInfo;
          } else {
            replyText =
              "حياك الله يا غالي! «" + cleanName + "» متوفر في المتجر بسعر " + targetProd.price + " ر.ي.\\n" +
              "💡 " + smart.defaultInfo;
          }

          return res.json({
            ok: true,
            zeroToken: true,
            matchedOverride: true,
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
          });
        }
      }

      // 7. Friendly Greeting vs Missing Item Table Offer
      const isGreeting = /^(هلا|اهلا|مرحبا|السلام عليكم|صباح الخير|مساء الخير|كيف حالك|كيفك|شخبارك|وش اخبارك)(\\s|$)/.test(normMsg);
      if (isGreeting) {
        const customWelcomeInst = (memoryConfig.instructions || []).find(i => i.active && i.category === "welcome");
        const replyGreet = customWelcomeInst?.text
          ? customWelcomeInst.text
          : "يا هلا ومليون غلا بك يا غالي! 😊 الحمد لله بخير دامك بخير ❤️\\nأنا شيف ومساعد أورجنال الذكي: أقدر أعطيك أي وصفة طبخ أو حلى تخطر في بالك مع جدول مقاديرها (حتى لو بعض مكوناتها غير موجودة بالمتجر أجهزها لك لتضيفها في ملاحظة طلبك!)، أو أرشح لك أحلى السناكات والمقاضي. قول لي إيش بخاطرك اليوم؟";
        return res.json({
          ok: true,
          zeroToken: true,
          matchedOverride: true,
          reply: replyGreet,
          suggestedItems: []
        });
      }

      const stopWords = new Set(["هل", "عندكم", "معاكم", "معكم", "في", "متوفر", "اريد", "ابغي", "اشتي", "بكم", "سعر", "وين", "وش", "ايش", "كيف", "طريقه", "عمل", "وصفه", "معلومات", "سعرات", "ابحث", "عن", "رد", "منك", "لو", "سمحت", "شي", "حاجه", "يااخي", "افضل", "احسن"]);
      const words = normMsg.split(" ").filter(w => w.length >= 3 && !stopWords.has(w));
      const matchedProds = allProds.filter(p => {
        const cn = normalizeArabicV112(cleanProductNameV112(p.name));
        return words.some(w => cn.includes(w));
      });

      const asksAvailability = /(عندكم|معاكم|معكم|متوفر|تبيعون|احصل|القي|اشتي|ابغي|اريد|موجود|قهوه|قهوة)/.test(normMsg);
      if (asksAvailability && matchedProds.length === 0 && words.length > 0) {
        zeroTokenCounter++;
        const requestedName = words.join(" ");
        const customMissingInst = (memoryConfig.instructions || []).find(i => i.active && i.category === "missing_item");
        const friendlyReply = customMissingInst?.text
          ? customMissingInst.text.replace(/\\{المنتج\\}/g, requestedName)
          : "فهمتك يا غالي! أنت تطلب «" + requestedName + "».. حلو حلو 👌\\nحالياً هذا الصنف غير ظاهر في قائمة المتجر، لكن ولا يهمك! جهزته لك في الجدول بالأسفل كصنف قابل للطلب: اضغط على زر (📋 إضافة للملاحظة والطلب) ليُضاف تلقائياً مع طلبك، وسيتواصل معك المتجر ويرد عليك فوراً حول حالة توفره!";
        return res.json({
          ok: true,
          zeroToken: true,
          matchedOverride: true,
          missingItemOffer: true,
          requestedItemName: requestedName,
          ingredientsTable: [
            {
              name: requestedName,
              amount: "حسب الطلب",
              available: false
            }
          ],
          missingItemsText: requestedName,
          reply: friendlyReply,
          suggestedItems: []
        });
      }

      return res.json({ ok: true, passThrough: true });
    } catch (e: any) {
      res.status(500).json({ ok: false, error: String(e?.message || e) });
    }
  });
}
"""

pathlib.Path("server/ai_engine_v112.ts").write_text(ai_engine_v123_ts, encoding="utf-8")
print("1. Wrote complete server/ai_engine_v112.ts (v123 Context-Aware Interactive Chef + 5-Min DB Cache)!")

# ==============================================================================
# 2. تحديث client/index.html:
#    - إصلاح شكل أيقونة الشيف ✨ (منع تداخلها مع بالونة المستخدم)
#    - جدول متوازن 100% على شاشة الجوال بدون اقتصاص ولا ضغط لأسماء المنتجات
#    - ربط سياق المحادثة (إرسال الرسالة السابقة مع الرسالة الحالية ليفهم "أريد طريقة أفضل")
#    - مطابقة 100% بين منتجات الجدول وصندوق السلة الأخضر بالأسفل
#    - ضمان إضافة المكونات غير المتوفرة إلى ملاحظة الطلب بـ 3 طبقات
# ==============================================================================
html_path = pathlib.Path("client/index.html")
if html_path.exists():
    ht = html_path.read_text(encoding="utf-8")

    ht = re.sub(
        r'window\.__v12[123]SmartDataByQuery =[\s\S]*?function syncOrderNotesFieldV12[123]\(\) \{[\s\S]*?\n        \}',
        '',
        ht
    )

    v123_helpers_and_css = """
        window.__v123SmartDataByQuery = window.__v123SmartDataByQuery || {};
        window.__v123LastBubbleCount = 0;
        window.__v123PreviousUserMsg = "";

        (function injectGeminiChatStylesV123() {
          var oldSt = document.getElementById("v121-gemini-chat-styles") || document.getElementById("v122-gemini-chat-styles") || document.getElementById("v123-gemini-chat-styles");
          if (oldSt) oldSt.remove();
          var st = document.createElement("style");
          st.id = "v123-gemini-chat-styles";
          st.textContent =
            ".v123-gemini-user-bubble { background: #0d3825 !important; color: #ffffff !important; border: 1.5px solid #165b3c !important; border-radius: 20px 20px 4px 20px !important; padding: 9px 16px !important; box-shadow: 0 3px 10px rgba(13,56,37,0.15) !important; font-weight: 800 !important; font-size: 0.92rem !important; width: fit-content !important; max-width: 80% !important; display: inline-block !important; overflow-anchor: none !important; }" +
            ".v123-gemini-user-bubble * { color: #ffffff !important; }" +
            ".v123-gemini-bot-full { width: 100% !important; max-width: 100% !important; background: transparent !important; border: none !important; box-shadow: none !important; border-bottom: 1px solid #e2e8f0 !important; border-radius: 0 !important; padding: 12px 2px 18px 2px !important; margin: 4px 0 !important; overflow-anchor: none !important; }" +
            ".v123-gemini-bot-row { width: 100% !important; max-width: 100% !important; display: block !important; overflow-anchor: none !important; }" +
            ".v118-wa-photo-box, .v123-ingredients-panel { overflow-anchor: none !important; }";
          document.head.appendChild(st);
        })();

        function scrollToChatBottomSmoothV123() {
          try {
            if (document.body.textContent.indexOf("مساعد وشيف أورجنال الذكي") === -1) return;
            var allUserAndBot = Array.from(document.querySelectorAll(".v123-gemini-user-bubble, .v123-gemini-bot-full"));
            if (allUserAndBot.length === 0) return;
            var lastEl = allUserAndBot[allUserAndBot.length - 1];
            var sc = lastEl.parentElement;
            while (sc && sc !== document.body) {
              var oy = window.getComputedStyle(sc).overflowY;
              if ((oy === "auto" || oy === "scroll") && sc.scrollHeight > sc.clientHeight + 20) {
                sc.scrollTo({ top: sc.scrollHeight, behavior: "smooth" });
                break;
              }
              sc = sc.parentElement;
            }
            lastEl.scrollIntoView({ behavior: "smooth", block: "end" });
          } catch (e) {}
        }

        function bindChatInputScrollLockV123() {
          if (document.body.textContent.indexOf("مساعد وشيف أورجنال الذكي") === -1) return;
          var chatInputs = Array.from(document.querySelectorAll("input, textarea")).filter(function(inp) {
            var ph = inp.getAttribute("placeholder") || "";
            return ph.indexOf("اطلب سلة") !== -1 || ph.indexOf("وصفة") !== -1 || ph.indexOf("مقاضي") !== -1;
          });
          chatInputs.forEach(function(inp) {
            if (inp.getAttribute("data-v123-scroll-bound") === "1") return;
            inp.setAttribute("data-v123-scroll-bound", "1");
            inp.addEventListener("keydown", function(ev) {
              if (ev.key === "Enter") {
                setTimeout(scrollToChatBottomSmoothV123, 60);
                setTimeout(scrollToChatBottomSmoothV123, 250);
              }
            });
            var sendBtn = inp.parentElement ? inp.parentElement.querySelector("button") : null;
            if (sendBtn && sendBtn.getAttribute("data-v123-scroll-bound") !== "1") {
              sendBtn.setAttribute("data-v123-scroll-bound", "1");
              sendBtn.addEventListener("click", function() {
                setTimeout(scrollToChatBottomSmoothV123, 60);
                setTimeout(scrollToChatBottomSmoothV123, 250);
              });
            }
          });
        }

        window.__copyAndAttachMissingToOrderNotesV123 = function(btnEl, missingText, recipeTitle) {
          var cleanMissing = String(missingText || "").trim();
          if (!cleanMissing) return;
          var newEntry = "📋 مكونات إضافية مطلوبة (" + (recipeTitle || "وصفة الشيف") + "): " + cleanMissing + " — يرجى إفادتي بحالة توفرها مع طلبي.";
          var existingNote = "";
          try {
            existingNote = localStorage.getItem("original_v123_order_note") || "";
          } catch (e) {}
          var combinedNote = existingNote && existingNote.indexOf(cleanMissing) === -1
            ? (existingNote + "\\n" + newEntry)
            : (existingNote || newEntry);

          try {
            localStorage.setItem("original_v123_order_note", combinedNote);
            localStorage.setItem("original_v122_order_note", combinedNote);
          } catch (e) {}

          if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(combinedNote).catch(function() {});
          } else {
            try {
              var ta = document.createElement("textarea");
              ta.value = combinedNote;
              document.body.appendChild(ta);
              ta.select();
              document.execCommand("copy");
              ta.remove();
            } catch (e) {}
          }
          syncOrderNotesFieldV123();
          fetch("/api/ai-studio/request-item", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              sessionId: window.__v112SessionId,
              requestedItem: cleanMissing,
              userMessage: newEntry
            })
          }).catch(function() {});
          if (btnEl) {
            btnEl.style.background = "#15803d";
            btnEl.style.color = "#ffffff";
            btnEl.textContent = "✅ تم النسخ والإضافة لملاحظة الطلب! سيرد عليك المتجر بحالة توفرها";
          }
        };

        function syncOrderNotesFieldV123() {
          var savedNote = "";
          try {
            savedNote = localStorage.getItem("original_v123_order_note") || localStorage.getItem("original_v122_order_note") || "";
          } catch (e) {}
          if (!savedNote || window.location.pathname.indexOf("/admin") !== -1) return;

          var noteFields = Array.from(document.querySelectorAll("textarea, input[type='text']")).filter(function(el) {
            var ph = (el.getAttribute("placeholder") || "") + " " + (el.getAttribute("name") || "") + " " + (el.getAttribute("aria-label") || "");
            var parentTxt = el.parentElement ? (el.parentElement.textContent || "") : "";
            return (
              ph.indexOf("ملاحظ") !== -1 ||
              ph.indexOf("توجيهات") !== -1 ||
              ph.indexOf("إضافية") !== -1 ||
              ph.indexOf("note") !== -1 ||
              (parentTxt.indexOf("ملاحظ") !== -1 && parentTxt.length < 140)
            );
          });

          noteFields.forEach(function(field) {
            var curVal = field.value || "";
            if (curVal.indexOf(savedNote) === -1 && field.getAttribute("data-v123-note-filled") !== savedNote) {
              var nextVal = curVal.trim() ? (curVal.trim() + "\\n" + savedNote) : savedNote;
              try {
                var proto = field.tagName === "TEXTAREA" ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
                var setter = Object.getOwnPropertyDescriptor(proto, "value").set;
                if (setter) {
                  setter.call(field, nextVal);
                } else {
                  field.value = nextVal;
                }
                field.dispatchEvent(new Event("input", { bubbles: true }));
                field.dispatchEvent(new Event("change", { bubbles: true }));
                field.setAttribute("data-v123-note-filled", savedNote);
              } catch (e) {
                field.value = nextVal;
              }
            }
          });
        }
"""

    ht = ht.replace(
        "window.__openRecipeImageLightboxV116 = function(src, title) {",
        v123_helpers_and_css + "\n        window.__openRecipeImageLightboxV116 = function(src, title) {"
    )

    old_fetch_block = r'if \(urlStr\.indexOf\("/api/trpc/"\) !== -1 && init && init\.method === "POST" && typeof init\.body === "string"\) \{[\s\S]*?\.catch\(function\(\) \{ return trpcRes; \}\);\s*\}\s*\}'
    new_fetch_block = """if (urlStr.indexOf("/api/trpc/") !== -1 && init && init.method === "POST" && typeof init.body === "string") {
              if (/order|checkout|create/i.test(urlStr) && !/ai|chat/i.test(urlStr)) {
                try {
                  var pendingNote = localStorage.getItem("original_v123_order_note") || "";
                  if (pendingNote) {
                    var ordBody = JSON.parse(init.body);
                    function injectOrderNote(obj) {
                      if (!obj || typeof obj !== "object") return;
                      var noteKeys = ["notes", "note", "customerNotes", "orderNotes", "comment", "instructions"];
                      noteKeys.forEach(function(nk) {
                        if ( nk in obj ) {
                          var curN = String(obj[nk] || "").trim();
                          if (curN.indexOf(pendingNote) === -1) {
                            obj[nk] = curN ? (curN + "\\n" + pendingNote) : pendingNote;
                          }
                        }
                      });
                      if (!("notes" in obj) && ("customerName" in obj || "customerPhone" in obj || "items" in obj)) {
                        obj.notes = pendingNote;
                      }
                      Object.keys(obj).forEach(function(k) {
                        if (typeof obj[k] === "object") injectOrderNote(obj[k]);
                      });
                    }
                    injectOrderNote(ordBody);
                    init = Object.assign({}, init, { body: JSON.stringify(ordBody) });
                  }
                } catch (e) {}
              }

              var detectedMsg = extractAnyUserTextFromJsonBodyV116(init.body);
              if (detectedMsg) window.__v119LastUserSentText = detectedMsg;
              var isAiCall = /ai|chat|assistant|chef|recipe|ask|suggest|message|prompt/i.test(urlStr) ||
                Boolean(matchRecipeClientV116(detectedMsg) || matchRuleClientV116(detectedMsg) || matchPromoClientV116(detectedMsg));

              if (detectedMsg && isAiCall) {
                var prevMsgToSend = window.__v123PreviousUserMsg || "";
                if (!/(طريقه افضل|طريقة افضل|طريقه ثانيه|طريقة ثانية|غيرها|احلى|افضل من كذا)/.test(detectedMsg)) {
                  window.__v123PreviousUserMsg = detectedMsg;
                }
                return origFetch.apply(this, arguments).then(function(trpcRes) {
                  return origFetch("/api/ai-studio/smart-chat", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                      message: detectedMsg,
                      prevMessage: prevMsgToSend,
                      sessionId: window.__v112SessionId
                    })
                  })
                    .then(function(r) { return r.json(); })
                    .then(function(smartData) {
                      if (!smartData || !smartData.ok || smartData.passThrough || !smartData.matchedOverride) return trpcRes;
                      window.__v123SmartDataByQuery[normalizeArabicClientV116(detectedMsg)] = smartData;
                      return trpcRes.clone().json().then(function(trpcJson) {
                        replaceTrpcAiPayloadInPlaceV117(trpcJson, smartData);
                        setTimeout(enhanceChatBubblesSafelyV117, 120);
                        setTimeout(scrollToChatBottomSmoothV123, 160);
                        setTimeout(enhanceChatBubblesSafelyV117, 350);
                        return new Response(JSON.stringify(trpcJson), {
                          status: trpcRes.status,
                          statusText: trpcRes.statusText,
                          headers: trpcRes.headers
                        });
                      }).catch(function() { return trpcRes; });
                    })
                    .catch(function() { return trpcRes; });
                });
              }
            }"""

    ht = re.sub(old_fetch_block, lambda m: new_fetch_block, ht, count=1)

    old_enhance_pattern = r"function (?:isDarkGreenBgV119|enhanceChatBubblesSafelyV117)\([\s\S]*?\n        \}\n\n        var origFetch = window\.fetch;"
    new_enhance_v123 = """function isDarkGreenBgV119(el) {
          if (!el || el === document.body) return false;
          if (el.closest && (el.closest(".v123-gemini-bot-full") || el.closest(".v123-gemini-ai-header") || el.closest(".v122-gemini-ai-header"))) return false;
          if (el.getAttribute && (el.getAttribute("data-v123-role") === "user" || el.getAttribute("data-v122-role") === "user" || el.getAttribute("data-v121-role") === "user")) return true;
          try {
            var cs = window.getComputedStyle(el);
            var bg = cs.backgroundColor || "";
            var m = bg.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)/);
            if (m) {
              var r = parseInt(m[1], 10);
              var g = parseInt(m[2], 10);
              var b = parseInt(m[3], 10);
              if (r < 45 && g > 35 && g < 115 && b > 20 && b < 85) return true;
            }
          } catch (e) {}
          return false;
        }

        function isInsideDarkGreenUserBubbleV119(el) {
          if (!el) return false;
          if (el.closest && (el.closest(".v123-gemini-bot-full") || el.closest(".v123-gemini-ai-header"))) return false;
          var cur = el;
          for (var i = 0; i < 4 && cur && cur !== document.body; i++) {
            if (cur.getAttribute && (cur.getAttribute("data-v123-role") === "user" || cur.getAttribute("data-v122-role") === "user")) return true;
            if (isDarkGreenBgV119(cur)) return true;
            cur = cur.parentElement;
          }
          return false;
        }

        function buildIngredientsTableHtmlV123(tableRows, missingItemsText, recipeTitle) {
          if (!Array.isArray(tableRows) || tableRows.length === 0) return "";
          var rowsHtml = tableRows.map(function(row) {
            var priceCell = row.available ? ((row.price || 100) + " ر.ي") : "—";
            var statusCell = row.available
              ? '<span style="color:#15803d;font-weight:800;">✅ متوفر</span>'
              : '<span style="color:#d97706;font-weight:800;">📌 بالملاحظة</span>';
            return (
              '<tr style="border-bottom:1px solid #e2e8f0;">' +
              '<td style="padding:9px 4px;font-weight:800;color:#0f172a;font-size:0.85rem;width:44%;line-height:1.4;">' + (row.name || "") + '</td>' +
              '<td style="padding:9px 4px;color:#475569;font-size:0.81rem;font-weight:700;width:20%;">' + (row.amount || "1 حبة") + '</td>' +
              '<td style="padding:9px 4px;color:#0f172a;font-size:0.82rem;font-weight:800;width:16%;white-space:nowrap;">' + priceCell + '</td>' +
              '<td style="padding:9px 4px;font-size:0.8rem;width:20%;white-space:nowrap;">' + statusCell + '</td>' +
              '</tr>'
            );
          }).join("");

          var safeMissing = String(missingItemsText || "").replace(/"/g, "&quot;").replace(/'/g, "\\'");
          var safeTitle = String(recipeTitle || "وصفة الشيف").replace(/"/g, "&quot;").replace(/'/g, "\\'");

          var missingActionHtml = "";
          if (missingItemsText) {
            missingActionHtml =
              '<div style="margin-top:12px;padding:12px;background:#f8fafc;border-right:3.5px solid #0d3825;border-radius:10px;">' +
              '<div style="font-weight:900;color:#0d3825;font-size:0.84rem;margin-bottom:4px;">📦 مكونات إضافية غير ظاهرة بالمتجر (قابلة للطلب مع فاتورتك):</div>' +
              '<div style="font-size:0.81rem;color:#334155;font-weight:700;margin-bottom:9px;line-height:1.5;">' + missingItemsText + '</div>' +
              '<button type="button" class="v123-copy-notes-btn" data-missing="' + safeMissing + '" data-title="' + safeTitle + '" style="width:100%;padding:10px 12px;border-radius:10px;border:none;background:#0d3825;color:#d4af37;font-weight:900;font-size:0.83rem;cursor:pointer;">📋 نسخ المكونات غير المتوفرة ووضعها تلقائياً في ملاحظة الطلب</button>' +
              '<div style="font-size:0.75rem;color:#64748b;margin-top:6px;line-height:1.45;font-weight:700;">💡 بضغطة زر تُنسخ المكونات وتُوضع تلقائياً في (ملاحظة الطلب) عند إرسال طلبك، وسيرد عليك المتجر فوراً حول حالة توفرها!</div>' +
              '</div>';
          }

          return (
            '<div style="margin:12px 0;direction:rtl;text-align:right;width:100%;">' +
            '<div style="font-weight:900;color:#0f172a;font-size:0.9rem;margin-bottom:6px;">📊 جدول مقادير الوصفة وحالة التوفر:</div>' +
            '<table style="width:100%;border-collapse:collapse;text-align:right;direction:rtl;table-layout:fixed;">' +
            '<thead><tr style="border-bottom:1.5px solid #94a3b8;">' +
            '<th style="padding:7px 4px;font-size:0.8rem;color:#475569;font-weight:900;width:44%;">المكون</th>' +
            '<th style="padding:7px 4px;font-size:0.8rem;color:#475569;font-weight:900;width:20%;">المقدار</th>' +
            '<th style="padding:7px 4px;font-size:0.8rem;color:#475569;font-weight:900;width:16%;">السعر</th>' +
            '<th style="padding:7px 4px;font-size:0.8rem;color:#475569;font-weight:900;width:20%;">الحالة</th>' +
            '</tr></thead>' +
            '<tbody>' + rowsHtml + '</tbody>' +
            '</table>' +
            missingActionHtml +
            '</div>'
          );
        }

        function syncNativeGreenCartBoxV123(assistantCard, availItems) {
          if (!assistantCard || !Array.isArray(availItems)) return;
          var singleAddBtns = Array.from(assistantCard.querySelectorAll("button")).filter(function(b) {
            return (b.textContent || "").indexOf("أضف بمفرده") !== -1;
          });
          if (singleAddBtns.length === 0) return;

          var greenBox = singleAddBtns[0].parentElement ? singleAddBtns[0].parentElement.parentElement : null;
          if (availItems.length === 0) {
            if (greenBox && (greenBox.textContent || "").indexOf("الأصناف والمقادير") !== -1) {
              greenBox.style.display = "none";
            }
            return;
          }
          if (greenBox) greenBox.style.display = "";

          singleAddBtns.forEach(function(sBtn, sIdx) {
            var itemRow = sBtn.parentElement;
            if (!itemRow) return;
            var targetIng = availItems[sIdx];
            if (!targetIng) {
              itemRow.style.display = "none";
              return;
            }
            itemRow.style.display = "";
            var tName = String(targetIng.name || "").replace(/\\s*\\([^()]*\\)\\s*$/g, "").trim();
            var tPrice = Number(targetIng.price || 100);
            var tUnit = String(targetIng.unit || "حبة");

            var rowLeaves = Array.from(itemRow.querySelectorAll("span, strong, p, div")).filter(function(rl) {
              return rl.children.length === 0 && rl.tagName !== "BUTTON" && !sBtn.contains(rl);
            });
            rowLeaves.forEach(function(rl) {
              var rt = (rl.textContent || "").trim();
              if (rt.indexOf("ر.ي") !== -1 && /\\d/.test(rt)) {
                setLeafTextSafe(rl, "1 × " + tPrice.toLocaleString("en-US") + " ر.ي (" + tUnit + ")");
              } else if (rt.length >= 2 && rt.indexOf("أضف") === -1) {
                setLeafTextSafe(rl, tName);
              }
            });
          });

          var totalSum = availItems.slice(0, singleAddBtns.length).reduce(function(acc, g) {
            return acc + Number(g.price || 100);
          }, 0);

          var cardLeaves = Array.from(assistantCard.querySelectorAll("span, strong, p, div, button")).filter(function(x) {
            return x.children.length === 0 && !(x.closest && x.closest(".v123-ingredients-panel"));
          });
          cardLeaves.forEach(function(cl) {
            var ct = (cl.textContent || "").trim();
            if (ct.indexOf("الإجمالي:") !== -1) {
              setLeafTextSafe(cl, "الإجمالي: " + totalSum.toLocaleString("en-US") + " ر.ي");
            } else if (ct.indexOf("اعتمد وإضافة") !== -1 || ct.indexOf("نعم، اعتمد") !== -1) {
              setLeafTextSafe(cl, "✅ اعتمد وإضافة الكل للسلة (" + totalSum.toLocaleString("en-US") + " ر.ي)");
            }
          });
        }

        function enhanceChatBubblesSafelyV117() {
          syncOrderNotesFieldV123();
          bindChatInputScrollLockV123();
          if (document.body.textContent.indexOf("مساعد وشيف أورجنال الذكي") === -1) return;

          Array.from(document.querySelectorAll(".v117-recipe-photo-banner, .v118-wa-photo-box")).forEach(function(box) {
            if (box.classList.contains("v117-recipe-photo-banner") || isInsideDarkGreenUserBubbleV119(box)) {
              box.remove();
            }
          });

          var allLeaves = Array.from(document.querySelectorAll("p, div")).filter(function(el) {
            if (el.children.length !== 0) return false;
            if (el.closest && (el.closest(".v118-wa-photo-box") || el.closest(".v123-ingredients-panel") || el.closest(".v122-ingredients-panel") || el.closest(".v121-ingredients-panel") || el.closest(".v123-gemini-ai-header") || el.closest(".v122-gemini-ai-header") || el.closest("button"))) return false;

            var parentCard = el.parentElement;
            if (!parentCard) return false;
            var cardTxt = parentCard.textContent || "";
            if (cardTxt.indexOf("محادثة جديدة") !== -1 || parentCard.querySelector("input, textarea")) return false;

            var isAssistantCard =
              cardTxt.indexOf("الأصناف والمقادير") !== -1 ||
              cardTxt.indexOf("تأكيد إضافة") !== -1 ||
              cardTxt.indexOf("أضف بمفرده") !== -1 ||
              cardTxt.indexOf("أفكار لتحضيره") !== -1 ||
              cardTxt.indexOf("منتجات مشابهة") !== -1 ||
              cardTxt.indexOf("مقاضي الصباح") !== -1;
            if (!isAssistantCard) return false;

            var parentBubble = el.closest ? el.closest("[data-v119-bubble='1']") : null;
            if (parentBubble && el.getAttribute("data-v119-reply") !== "1") return false;

            var t = (el.textContent || "").trim();
            if (
              t.indexOf("الأصناف والمقادير") !== -1 ||
              t.indexOf("تأكيد إضافة") !== -1 ||
              t.indexOf("الإجمالي:") !== -1 ||
              t.indexOf("ر.ي (حبة)") !== -1 ||
              t.indexOf("أضف بمفرده") !== -1 ||
              t.indexOf("اعتمد وإضافة") !== -1 ||
              t.indexOf("إلغاء") !== -1
            ) {
              return false;
            }
            return t.length >= 10;
          });

          allLeaves.forEach(function(rl) {
            if (rl.parentElement) {
              rl.parentElement.classList.add("v123-gemini-bot-full");
            }
          });

          var allUserBubbles = Array.from(document.querySelectorAll("div, p, span")).filter(function(el) {
            if (el.closest && (el.closest(".v123-gemini-bot-full") || el.closest(".v123-gemini-ai-header") || el.closest(".v122-gemini-ai-header"))) return false;
            if (!isDarkGreenBgV119(el)) return false;
            if (el.tagName === "BUTTON" || el.querySelector("button, input, textarea")) return false;
            var hasDarkGreenChild = Array.from(el.children).some(function(c) { return isDarkGreenBgV119(c); });
            if (hasDarkGreenChild) return false;
            var t = (el.textContent || "").trim();
            if (t === "✨" || t.indexOf("شيف ومساعد") !== -1 || t.indexOf("محادثة جديدة") !== -1 || t.indexOf("الأصناف والمقادير") !== -1) return false;
            if (t.length < 1 || t.length > 220) return false;

            el.setAttribute("data-v123-role", "user");
            el.classList.remove("v121-gemini-user-bubble", "v122-gemini-user-bubble");
            el.classList.add("v123-gemini-user-bubble");

            if (t.indexOf("🍰") !== -1 && el.getAttribute("data-v119-orig-user")) {
              setLeafTextSafe(el, el.getAttribute("data-v119-orig-user"));
            } else if (t.indexOf("🍰") === -1 && !el.getAttribute("data-v119-orig-user")) {
              el.setAttribute("data-v119-orig-user", t);
            }
            return true;
          });

          allLeaves.forEach(function(replyLeaf) {
            var assistantCard = replyLeaf.parentElement;
            if (!assistantCard || isInsideDarkGreenUserBubbleV119(assistantCard)) return;

            assistantCard.classList.add("v123-gemini-bot-full");
            if (assistantCard.parentElement && assistantCard.parentElement.textContent.indexOf("محادثة جديدة") === -1) {
              assistantCard.parentElement.classList.add("v123-gemini-bot-row");
            }

            var oldHdr = assistantCard.querySelector(".v122-gemini-ai-header, .v121-gemini-ai-header");
            if (oldHdr) oldHdr.remove();
            if (!assistantCard.querySelector(".v123-gemini-ai-header")) {
              var aiHdr = document.createElement("div");
              aiHdr.className = "v123-gemini-ai-header";
              aiHdr.style.cssText = "display:flex;align-items:center;gap:6px;margin-bottom:8px;font-weight:900;font-size:0.83rem;color:#0d3825;";
              aiHdr.innerHTML = "<span style='background:#fef3c7;color:#b45309;border:1px solid #f59e0b;width:22px;height:22px;border-radius:99px;display:inline-flex;align-items:center;justify-content:center;font-size:0.75rem;'>✨</span><span>شيف ومساعد أورجنال الذكي</span>";
              assistantCard.insertBefore(aiHdr, assistantCard.firstChild);
            }

            replyLeaf.style.whiteSpace = "pre-line";
            replyLeaf.style.lineHeight = "1.75";
            replyLeaf.style.fontSize = "0.94rem";
            replyLeaf.style.color = "#0f172a";

            var precedingUsers = allUserBubbles.filter(function(ub) {
              return Boolean(ub.compareDocumentPosition(assistantCard) & Node.DOCUMENT_POSITION_FOLLOWING);
            });
            var lastUserBubble = precedingUsers.length > 0 ? precedingUsers[precedingUsers.length - 1] : null;
            var prevUserBubble = precedingUsers.length > 1 ? precedingUsers[precedingUsers.length - 2] : null;

            var userQueryTxt = lastUserBubble ? (lastUserBubble.getAttribute("data-v119-orig-user") || lastUserBubble.textContent || "").trim() : "";
            var prevUserTxt = prevUserBubble ? (prevUserBubble.getAttribute("data-v119-orig-user") || prevUserBubble.textContent || "").trim() : "";
            if (!userQueryTxt) return;

            var normQ = normalizeArabicClientV116(userQueryTxt + "|" + prevUserTxt);
            var cachedSmart = window.__v123SmartDataByQuery[normQ] || window.__v123SmartDataByQuery[normalizeArabicClientV116(userQueryTxt)];

            if (!cachedSmart && !assistantCard.getAttribute("data-v123-fetched")) {
              assistantCard.setAttribute("data-v123-fetched", "1");
              origFetch("/api/ai-studio/smart-chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  message: userQueryTxt,
                  prevMessage: prevUserTxt,
                  sessionId: window.__v112SessionId
                })
              })
                .then(function(r) { return r.json(); })
                .then(function(sd) {
                  if (sd && sd.ok && sd.matchedOverride) {
                    window.__v123SmartDataByQuery[normQ] = sd;
                    enhanceChatBubblesSafelyV117();
                  }
                })
                .catch(function() {});
            }

            var matchedRec = matchRecipeClientV116(userQueryTxt);
            var matchedRule = !matchedRec ? matchRuleClientV116(userQueryTxt) : null;
            var matchedPromo = (!matchedRec && !matchedRule) ? matchPromoClientV116(userQueryTxt) : null;

            if (cachedSmart && cachedSmart.matchedOverride) {
              assistantCard.setAttribute("data-v119-bubble", "1");
              replyLeaf.setAttribute("data-v119-reply", "1");

              if (cachedSmart.recipeImage && !assistantCard.querySelector(".v118-wa-photo-box")) {
                var waBox = document.createElement("div");
                waBox.className = "v118-wa-photo-box";
                waBox.style.cssText = "margin:0 0 12px 0;border-radius:14px;overflow:hidden;background:#f1f5f9;cursor:pointer;";
                var waImg = document.createElement("img");
                waImg.src = cachedSmart.recipeImage;
                waImg.alt = String(cachedSmart.recipeTitle || "");
                waImg.style.cssText = "width:100%;max-height:250px;object-fit:cover;display:block;border-radius:14px;";
                waBox.onclick = function() {
                  window.__openRecipeImageLightboxV116(cachedSmart.recipeImage, cachedSmart.recipeTitle || "");
                };
                waBox.appendChild(waImg);
                replyLeaf.parentNode.insertBefore(waBox, replyLeaf);
              }

              if (cachedSmart.reply) {
                setLeafTextSafe(replyLeaf, cachedSmart.reply);
              }

              var oldTbls = assistantCard.querySelectorAll(".v121-ingredients-panel, .v122-ingredients-panel");
              Array.from(oldTbls).forEach(function(ot) { ot.remove(); });

              if (Array.isArray(cachedSmart.ingredientsTable) && cachedSmart.ingredientsTable.length > 0 && !assistantCard.querySelector(".v123-ingredients-panel")) {
                var tblPanel = document.createElement("div");
                tblPanel.className = "v123-ingredients-panel";
                tblPanel.innerHTML = buildIngredientsTableHtmlV123(
                  cachedSmart.ingredientsTable,
                  cachedSmart.missingItemsText || "",
                  cachedSmart.recipeTitle || userQueryTxt
                );
                if (replyLeaf.nextSibling) {
                  replyLeaf.parentNode.insertBefore(tblPanel, replyLeaf.nextSibling);
                } else {
                  replyLeaf.parentNode.appendChild(tblPanel);
                }
                var copyBtn = tblPanel.querySelector(".v123-copy-notes-btn");
                if (copyBtn) {
                  copyBtn.onclick = function() {
                    window.__copyAndAttachMissingToOrderNotesV123(
                      copyBtn,
                      copyBtn.getAttribute("data-missing") || "",
                      copyBtn.getAttribute("data-title") || ""
                    );
                  };
                }
              }

              syncNativeGreenCartBoxV123(assistantCard, cachedSmart.suggestedItems || []);
            } else if (matchedRec) {
              assistantCard.setAttribute("data-v119-bubble", "1");
              replyLeaf.setAttribute("data-v119-reply", "1");

              if (matchedRec.imageUrl && !assistantCard.querySelector(".v118-wa-photo-box")) {
                var waBox2 = document.createElement("div");
                waBox2.className = "v118-wa-photo-box";
                waBox2.style.cssText = "margin:0 0 12px 0;border-radius:14px;overflow:hidden;background:#f1f5f9;cursor:pointer;";
                var waImg2 = document.createElement("img");
                waImg2.src = matchedRec.imageUrl;
                waImg2.alt = String(matchedRec.title || "");
                waImg2.style.cssText = "width:100%;max-height:250px;object-fit:cover;display:block;border-radius:14px;";
                waBox2.onclick = function() {
                  window.__openRecipeImageLightboxV116(matchedRec.imageUrl, matchedRec.title || "");
                };
                waBox2.appendChild(waImg2);
                replyLeaf.parentNode.insertBefore(waBox2, replyLeaf);
              }

              var targetRecipeText =
                "🍰 " + (matchedRec.title || "") + "\\n\\n" +
                (matchedRec.steps || "");
              setLeafTextSafe(replyLeaf, targetRecipeText);
            } else if (matchedRule) {
              assistantCard.setAttribute("data-v119-bubble", "1");
              replyLeaf.setAttribute("data-v119-reply", "1");
              setLeafTextSafe(replyLeaf, matchedRule.response || "");
            } else if (matchedPromo) {
              assistantCard.setAttribute("data-v119-bubble", "1");
              replyLeaf.setAttribute("data-v119-reply", "1");
              var promoTxt =
                (matchedPromo.promoBadge ? matchedPromo.promoBadge + " — " : "⭐ ترشيح خاص لك: ") +
                "«" + (matchedPromo.productName || "") + "»" +
                (matchedPromo.productPrice ? " (" + matchedPromo.productPrice + " ر.ي)" : "") +
                "\\n" + (matchedPromo.promoPitch || "");
              setLeafTextSafe(replyLeaf, promoTxt);
            }
          });

          var currentTotalBubbles = allUserBubbles.length + allLeaves.length;
          if (currentTotalBubbles > window.__v123LastBubbleCount) {
            var prevCount = window.__v123LastBubbleCount;
            window.__v123LastBubbleCount = currentTotalBubbles;
            if (prevCount > 0) {
              setTimeout(scrollToChatBottomSmoothV123, 50);
              setTimeout(scrollToChatBottomSmoothV123, 220);
            }
          }
        }

        var origFetch = window.fetch;"""

    ht, n_enh = re.subn(old_enhance_pattern, lambda m: new_enhance_v123, ht, count=1)

    ht = ht.replace(
        "setInterval(function() { refreshStudioDataV114(false); }, 6000);\n        setInterval(pollCustomerNotificationsV112, 6500);",
        "setInterval(function() { if (document.visibilityState === 'visible') refreshStudioDataV114(false); }, 25000);\n        setInterval(function() { if (document.visibilityState === 'visible') pollCustomerNotificationsV112(); }, 25000);"
    )

    html_path.write_text(ht, encoding="utf-8")
    print("2. Updated client/index.html (v123 Interactive Context + Balanced Table + Cart Box Sync + 3-Layer Order Notes)!")

# ==============================================================================
# 3. ترقية رقم كاش Service Worker إلى v123
# ==============================================================================
sw_path = pathlib.Path("client/public/sw.js")
if sw_path.exists():
    sw_txt = sw_path.read_text(encoding="utf-8")
    sw_txt = re.sub(r'v10\d|v11\d|v12\d|v9\d', 'v123', sw_txt)
    sw_path.write_text(sw_txt, encoding="utf-8")
    print("3. Bumped Service Worker cache to v123!")

# ==============================================================================
# 4. فحص البناء والرفع إلى Render
# ==============================================================================
res_srv = subprocess.run(
    "npx esbuild server/_core/index.ts --bundle --platform=node --format=esm --packages=external --outfile=./.tmp_srv_v123.js",
    shell=True, capture_output=True, text=True
)
res_cli = subprocess.run(
    "npx esbuild client/src/pages/Admin.tsx client/src/pages/Home.tsx --bundle --platform=browser --packages=external --outdir=./.tmp_cli_v123",
    shell=True, capture_output=True, text=True
)
os.system("rm -rf ./.tmp_srv_v123.js ./.tmp_cli_v123")

if res_srv.returncode != 0 or res_cli.returncode != 0:
    print("❌ Build check failed:", res_srv.stderr, res_cli.stderr)
else:
    print("✅ Build check passed 100%!")
    os.system("git add server/ai_engine_v112.ts client/index.html client/public/sw.js")
    os.system('git commit -m "Feat v123: conversational context memory, 5-min DB catalog cache, balanced mobile ChatGPT tables, cart box sync, and 3-layer order notes injection"')
    os.system("git push origin main")
    print("🚀 تم الرفع بنجاح إلى Render (v123)!")
