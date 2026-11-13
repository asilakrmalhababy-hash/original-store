import pathlib, re, subprocess, os

print("=== بدء التحديث الشامل v121 (واجهة شات احترافية بأسلوب Gemini/ChatGPT + شيف شامل يعطي أي وصفة مع جدول المكونات المتوفرة وغير المتوفرة وزر نسخها لملاحظة الطلب) ===")

# ==============================================================================
# 1. كتابة محرك الذكاء والشيف الشامل server/ai_engine_v112.ts (v121)
# ==============================================================================
ai_engine_v121_ts = """import express, { type Express } from "express";
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

export interface IngredientTableRowV121 {
  name: string;
  amount: string;
  available: boolean;
  price?: number;
  productId?: number;
  unit?: string;
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

function findMatchingSavedRecipeV117(userMessage: string, recipes: CustomRecipeItemV112[]): CustomRecipeItemV112 | null {
  if (!Array.isArray(recipes) || recipes.length === 0) return null;
  const normMsg = normalizeArabicV112(userMessage);
  if (!normMsg) return null;

  const stopWords = new Set(["اريد", "ابغي", "اشتي", "هل", "عندكم", "ممكن", "كيف", "اسوي", "طريقه", "عمل", "سريع", "في", "من", "مع", "على", "عن"]);

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
    if (matchedWords.length >= 1) return rec;
  }

  if (/(وصفه حلوه|حلي بارد|حلي بسكويت|حلا بسكويت|اريد حلي|اريد حلا)/.test(normMsg)) {
    return recipes[0];
  }
  return null;
}

// ============================================================================
// MASTER CHEF ENCYCLOPEDIA & DYNAMIC RECIPE GENERATOR (EVEN IF ITEMS MISSING!)
// ============================================================================
interface BuiltInChefRecipeV121 {
  keywords: RegExp;
  title: string;
  prepTime: string;
  steps: string;
  rawIngredients: { name: string; searchTerms: string[]; amount: string }[];
}

const BUILTIN_CHEF_RECIPES_V121: BuiltInChefRecipeV121[] = [
  {
    keywords: /(كبسه|كبسة|رز بالدجاج|ارز بالدجاج|غداء دجاج)/,
    title: "كبسة الدجاج العربية الأصيلة والملكية",
    prepTime: "45 دقيقة",
    steps:
      "1. في قدر على النار، شوّح البصل المفروم مع الزيت أو السمن حتى يذبل ويأخذ لوناً ذهبياً شهياً.\\n" +
      "2. أضف قطع الدجاج وقلّبها مع البهارات الصحيحة والمطحونة (هيل، قرفة، كركم، بهارات كبسة) لمدة 5 دقائق.\\n" +
      "3. أضف الطماطم المفرومة وملعقتين من صلصة الطماطم، ثم اسكب الماء الساخن واترك الدجاج ينضج لمدة 25 دقيقة.\\n" +
      "4. أخرج الدجاج لتحميره، وأضف الأرز المغسول والمنقوع إلى مرق الكبسة، واتركه على نار هادئة حتى ينضج ويتشرب النكهة بالكامل.\\n" +
      "5. قدّم الكبسة ساخنة وزينها بالمكسرات والزبيب وبالعافية!",
    rawIngredients: [
      { name: "أرز بسمتي فاخر", searchTerms: ["ارز", "أرز", "رز"], amount: "3 أكواب" },
      { name: "صلصة طماطم", searchTerms: ["صلصه", "صلصة", "معجون طماطم"], amount: "2 ملعقة كبيرة" },
      { name: "زيت طبخ أو سمن", searchTerms: ["زيت", "سمن"], amount: "3 ملاعق كبيرة" },
      { name: "دجاج طازج مقطع", searchTerms: ["دجاج"], amount: "1 حبة (1000 جرام)" },
      { name: "بصل وطماطم وثوم طازج", searchTerms: ["بصل", "طماطم"], amount: "2 حبة لكل نوع" },
      { name: "بهارات كبسة مشكلة وهيل", searchTerms: ["بهارات", "هيل", "كركم"], amount: "1 ملعقة كبيرة" }
    ]
  },
  {
    keywords: /(مندي|زربيان|مضغوط|حنيذ)/,
    title: "مندي يمني أصيل بنكهة التدخين الفاخرة",
    prepTime: "55 دقيقة",
    steps:
      "1. تبّل الدجاج أو اللحم بخليط الزعفران، الكركم، البهارات اليمنية، الملح، وقليل من الزيت.\\n" +
      "2. في قدر المندي، ضع الأرز المغسول مع البهارات الصحيحة (قرفة، قرنفل، هيل، ورق غار) والماء الساخن.\\n" +
      "3. ضع شبك المندي فوق القدر ورتب عليه قطع الدجاج المتبلة، ثم أحكم إغلاق القدر بالقصدير والغطاء على نار هادئة لمدة 45 دقيقة.\\n" +
      "4. للتبخير: ضع جمرة مشتعلة في فنجان صغير وسط الأرز مع قطرات زيت وأغلق القدر دقيقتين ليأخذ نكهة المندي الأصلية!",
    rawIngredients: [
      { name: "أرز بسمتي طويل الحبة", searchTerms: ["ارز", "أرز", "رز"], amount: "3 أكواب" },
      { name: "زيت نباتي أو سمن", searchTerms: ["زيت", "سمن"], amount: "3 ملاعق" },
      { name: "دجاج أو لحم طازج للمندي", searchTerms: ["دجاج", "لحم"], amount: "1 كيلو" },
      { name: "بهارات مندي يمنية وزعفران", searchTerms: ["بهارات", "كركم", "زعفران"], amount: "2 ملعقة كبيرة" },
      { name: "فحم للتبخير والتدخين", searchTerms: ["فحم"], amount: "قطعة واحدة" }
    ]
  },
  {
    keywords: /(سلته|سلتة|فحسه|فحسة)/,
    title: "السلتة والفحسة اليمنية الصنعانية على أصولها",
    prepTime: "30 دقيقة",
    steps:
      "1. في المقلى الحجري (الحرضة)، شوّح البصل والثوم المفروم مع الطماطم والصلصة والبهارات اليمنية.\\n" +
      "2. أضف المرق الساخن واللحم المفروم أو قطع اللحم الناضجة والبطاطس المسلوقة المهروسة قليلاً واتركها تتسبك وتغلي.\\n" +
      "3. اخفق الحلبة المنقوعة جيداً حتى تصبح بيضاء هشة، ثم أضف لها الكراث والكزبرة الخضراء والسحاوق.\\n" +
      "4. اسكب طبقة الحلبة المخفوقة فوق الحرضة وهي تغلي وقدمها فوراً مع الخبز اليمني الساخن!",
    rawIngredients: [
      { name: "صلصة طماطم", searchTerms: ["صلصه", "صلصة"], amount: "2 ملعقة كبيرة" },
      { name: "حلبة يمنية مطحونة", searchTerms: ["حلبه", "حلبة"], amount: "3 ملاعق كبيرة" },
      { name: "لحم بقري أو غنمي طازج", searchTerms: ["لحم"], amount: "نصف كيلو" },
      { name: "بطاطس وبصل وطماطم وكراث", searchTerms: ["بطاطس", "بصل"], amount: "تشكيلة طازجة" },
      { name: "كمون وكزبرة وبهارات يمنية", searchTerms: ["بهارات", "كمون"], amount: "ملعقة كبيرة" }
    ]
  },
  {
    keywords: /(بسبوسه|بسبوسة|هريسه|هريسة|حلي سميد)/,
    title: "بسبوسة ذهبية بالقشطة تذوب في الفم",
    prepTime: "30 دقيقة",
    steps:
      "1. اخلط السميد مع السكر، جوز الهند، البيكنج باودر، الحليب، والزيت أو السمن المذاب حتى يتكون خليط متجانس.\\n" +
      "2. افرد نصف الخليط في صينية مدهونة، ثم وزّع طبقة غنية من القشطة على الوجه، وغطّها بالنصف الثاني من خليط البسبوسة.\\n" +
      "3. اخبزها في فرن متوسط الحرارة (180 درجة) لمدة 20-25 دقيقة حتى تتحمر الأطراف والوجه.\\n" +
      "4. اسقها فور خروجها من الفرن بالشيرة (القطر) أو الحليب المكثف المحلى، وزينها بالفستق أو البسكويت المطحون!",
    rawIngredients: [
      { name: "حليب سائل أو بودرة", searchTerms: ["حليب", "لبن"], amount: "1 كوب" },
      { name: "زيت أو سمن", searchTerms: ["زيت", "سمن"], amount: "نصف كوب" },
      { name: "سكر أبيض", searchTerms: ["سكر"], amount: "نصف كوب" },
      { name: "سميد ناعم للبسبوسة", searchTerms: ["سميد"], amount: "2 كوب" },
      { name: "قشطة طازجة للحشوة", searchTerms: ["قشطه", "قشطة"], amount: "2 علبة" },
      { name: "جوز هند وبيكنج باودر", searchTerms: ["جوز هند", "بيكنج"], amount: "ملعقة كبيرة" }
    ]
  },
  {
    keywords: /(مكرونه|مكرونة|باستا|بشاميل|معكرونه|معكرونة)/,
    title: "مكرونة بالصلصة الغنية والجبن السائح (أو البشاميل)",
    prepTime: "25 دقيقة",
    steps:
      "1. اسلق المكرونة في ماء مغلي مملح مع ملعقة زيت لمدة 8-10 دقائق ثم صفّها.\\n" +
      "2. في مقلاة عميقة، شوّح البصل والثوم مع الزيت، ثم أضف التونة أو الدجاج أو اللحم المفروم وقلّب جيداً.\\n" +
      "3. أضف صلصة الطماطم والبهارات وقليل من ماء سلق المكرونة واترك الصوص يتسبك.\\n" +
      "4. لتحضير طبقة كريمية: امزج الحليب مع ملعقتين دقيق وجبن سائل على النار، ثم اخلط المكرونة بالصوص وضع الكريمة والجبن على الوجه وحمّرها!",
    rawIngredients: [
      { name: "مكرونة فاخرة", searchTerms: ["مكرونه", "مكرونة", "باستا"], amount: "1 كيس (400 جرام)" },
      { name: "صلصة طماطم", searchTerms: ["صلصه", "صلصة"], amount: "3 ملاعق كبيرة" },
      { name: "تونة أو دجاج", searchTerms: ["تونه", "تونة", "دجاج"], amount: "1 علبة كبيرة" },
      { name: "حليب سائل للصوص الكريمي", searchTerms: ["حليب", "لبن"], amount: "2 كوب" },
      { name: "زيت طبخ", searchTerms: ["زيت"], amount: "2 ملعقة كبيرة" },
      { name: "جبن موزاريلا مبشور أو جبن كاسات", searchTerms: ["جبن", "جبنه", "موزاريلا"], amount: "1 كوب" }
    ]
  },
  {
    keywords: /(كنافه|كنافة|قطايف|لقيمات|عوامه)/,
    title: "كنافة منزلية مقرمشة بالقشطة والجبن",
    prepTime: "30 دقيقة",
    steps:
      "1. افرك عجينة الكنافة مع السمن أو الزبدة المذابة وملعقة سكر بودرة حتى تتغلف كل الشعيرات.\\n" +
      "2. اضغط نصف كمية الكنافة في صينية مدهونة جيداً، ووزع فوقها طبقة من القشطة والجبن الحلو بعيداً عن الحواف.\\n" +
      "3. غطّ الحشوة بباقي الكنافة واضغط برفق، ثم اخبزها حتى تصبح ذهبية مقرمشة.\\n" +
      "4. اقلبها واسقها فوراً بالشيرة الباردة وزينها بالمكسرات!",
    rawIngredients: [
      { name: "حليب", searchTerms: ["حليب"], amount: "1 كوب" },
      { name: "سمن أو زبدة مذابة", searchTerms: ["سمن", "زبده", "زيت"], amount: "نصف كوب" },
      { name: "عجينة كنافة طازجة", searchTerms: ["كنافه", "كنافة"], amount: "500 جرام" },
      { name: "قشطة وجبن عكاوي/موزاريلا حلو", searchTerms: ["قشطه", "قشطة", "جبن"], amount: "2 علبة" },
      { name: "سكر وماء الورد للشيرة", searchTerms: ["سكر"], amount: "1 كوب" }
    ]
  },
  {
    keywords: /(شكشوكه|شكشوكة|فطور|عشاء خفيف|فول|قلابه|فاصوليا|تونه|تونة)/,
    title: "وجبة فطور وعشاء يمني سريع (فاصوليا وتونة وشكشوكة بالجبن)",
    prepTime: "15 دقيقة",
    steps:
      "1. في مقلاة ساخنة، شوّح البصل المفروم مع الفلفل الأخضر والطماطم في قليل من الزيت.\\n" +
      "2. أضف ملعقة صلصة طماطم ورشة كمون وفلفل أسود وملح.\\n" +
      "3. أضف التونة المصفاة أو الفول/الفاصوليا (أو البيض للشكشوكة) وقلّب على نار هادئة لمدة 5 دقائق.\\n" +
      "4. ضع ملعقة جبن سائل على الوجه وقدّمها ساخنة مع الخبز وكوب شاي بحليب يماني مضبوط!",
    rawIngredients: [
      { name: "تونة أو فول/فاصوليا", searchTerms: ["تونه", "تونة", "فول", "فاصوليا"], amount: "1 علبة" },
      { name: "صلصة طماطم", searchTerms: ["صلصه", "صلصة"], amount: "1 ملعقة كبيرة" },
      { name: "زيت نباتي", searchTerms: ["زيت"], amount: "2 ملعقة كبيرة" },
      { name: "حليب شاي", searchTerms: ["حليب"], amount: "1 علبة" },
      { name: "بيض طازج وبصل وطماطم وفلفل أخضر", searchTerms: ["بيض", "بصل", "طماطم"], amount: "3 حبات" },
      { name: "جبن سائل أو مثلثات", searchTerms: ["جبن", "جبنه"], amount: "2 ملعقة" }
    ]
  },
  {
    keywords: /(حلي|حلا|وصفه حلوه|وصفة حلوة|حلي بارد|حلي سريع|حلي قهوه|حلي بسكويت|تراميسو|تشيز كيك|كيك|كيكه|كيكة)/,
    title: "حلى طبقات البسكويت البارد بالشوكولاتة والكريمة الفاخرة",
    prepTime: "15 دقيقة",
    steps:
      "1. غمّس قطع البسكويت سريعاً في الحليب الدافئ ورتّبها كطبقة أولى في صينية أو كاسات التقديم.\\n" +
      "2. في وعاء، ذوّب الشوكولاتة مع قليل من الحليب الساخن والقشطة حتى يتكون صوص شوكولاتة كريمي ناعم وغني.\\n" +
      "3. اسكب طبقة من كريمة الشوكولاتة فوق البسكويت، ثم كرر الطبقات، ورش على الوجه بسكويت مطحون خشناً.\\n" +
      "4. ضعها في الثلاجة لمدة 20 دقيقة لتبرد وتتماسك، وقدمها باردة مع القهوة أو العصير وبالعافية!",
    rawIngredients: [
      { name: "بسكويت شاي أو بسكويت كريمة", searchTerms: ["بسكويت", "ماري", "ابو ولد", "ديما", "توبس"], amount: "2 باكيت" },
      { name: "شوكولاتة بالحليب أو البندق", searchTerms: ["شوكلاته", "شوكولاته", "شوكولاتة", "بريك", "بلاتو", "بليلا", "ويفر"], amount: "3 حبات" },
      { name: "حليب سائل أو مبخر", searchTerms: ["حليب", "لبن"], amount: "1 علبة" },
      { name: "قشطة طازجة وكريمة خفق", searchTerms: ["قشطه", "قشطة", "كريمه"], amount: "1 علبة" }
    ]
  }
];

function matchStoreProductByTermsV121(allProds: any[], searchTerms: string[]): any | null {
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

function buildDynamicRecipeResponseV121(userMessage: string, allProds: any[]): {
  title: string;
  prepTime: string;
  steps: string;
  tableRows: IngredientTableRowV121[];
  availableItems: any[];
  missingItemsText: string;
} | null {
  const normMsg = normalizeArabicV112(userMessage);
  const asksRecipeOrDish =
    /(وصفه|وصفة|طريقه عمل|طريقة عمل|كيف اسوي|كيف اطبخ|كيف اعمل|مقادير|حلي|حلا|كبسه|كبسة|مندي|زربيان|سلته|سلتة|فحسه|فحسة|بسبوسه|بسبوسة|مكرونه|مكرونة|بشاميل|كنافه|كنافة|شكشوكه|شكشوكة|فطور|عشاء|غداء|كيك|كيكه|تراميسو|تشيز كيك|بيتزا|شاورما|فطائر|معجنات|سمبوسه|سمبوسة|شفوت|بنت الصحن|لقيمات|مهلبيه|مهلبية)/.test(normMsg);

  if (!asksRecipeOrDish) return null;

  let chosen: BuiltInChefRecipeV121 | null = null;
  for (const r of BUILTIN_CHEF_RECIPES_V121) {
    if (r.keywords.test(normMsg)) {
      chosen = r;
      break;
    }
  }

  if (!chosen) {
    const cleanDishName = userMessage
      .replace(/^(اعطني|اريد|أريد|ابغى|اشتي|ما هي|كيف|طريقة عمل|طريقه عمل|وصفة|وصفه)\\s*/i, "")
      .trim() || "الطبق الشهي";

    chosen = {
      title: "وصفة وطريقة تحضير «" + cleanDishName + "» خطوة بخطوة",
      prepTime: "30 دقيقة",
      steps:
        "1. جهّز المكونات الأساسية لـ «" + cleanDishName + "» واغسل المكونات الطازجة جيداً.\\n" +
        "2. امزج المكونات الأساسية مع البهارات أو الإضافات المناسبة على نار متوسطة مع التقليب المستمر حتى تتجانس النكهات.\\n" +
        "3. اترك الخليط ينضج أو يتماسك على درجة حرارة هادئة لمدة 15-20 دقيقة حتى يصل للقوام المثالي.\\n" +
        "4. قدّم «" + cleanDishName + "» في طبق التقديم وزينه حسب الرغبة، وبالهناء والشفاء!",
      rawIngredients: [
        { name: "بسكويت أو مكون أساسي من المتجر", searchTerms: ["بسكويت", "مكرونه", "ارز", "تونه"], amount: "حسب الوصفة" },
        { name: "حليب أو شوكولاتة أو صلصة", searchTerms: ["حليب", "شوكلاته", "صلصه", "زيت"], amount: "حسب الوصفة" },
        { name: "مكونات «" + cleanDishName + "» الطازجة والإضافية", searchTerms: ["__non_existent__"], amount: "كمية كاملة للوصفة" },
        { name: "قشطة / جبن / بهارات خاصة بالوصفة", searchTerms: ["قشطه", "جبن", "بهارات"], amount: "حسب الرغبة" }
      ]
    };
  }

  const tableRows: IngredientTableRowV121[] = [];
  const availableItems: any[] = [];
  const missingNames: string[] = [];
  const usedProdIds = new Set<number>();

  for (const rawIng of chosen.rawIngredients) {
    const matchedProd = matchStoreProductByTermsV121(allProds, rawIng.searchTerms);
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

  return {
    title: chosen.title,
    prepTime: chosen.prepTime,
    steps: chosen.steps,
    tableRows,
    availableItems,
    missingItemsText: missingNames.join(" + ")
  };
}

const FUNNY_CLEAN_JOKES_V121 = [
  "😄 مرة واحد راح السوبر ماركت قال للبائع: عندكم سكر؟ قال له: أيوه! قال له: الله يخليك لا تقوله إني جيت لأنه زعلان مني عشان الدكتور منعني منه! 😂❤️\\n\\nقولي يا غالي، إيش نفسك نجهز اليوم؟ حلى بارد ولا وجبة سريعة؟",
  "😂 واحد سأل صاحبه: ليش تحط البسكويت في الثلاجة وبابها مفتوح؟ قال له: عشان أشوف النور يطفي ولا شغال! 🤣✨\\n\\nيلا يا غالي، آمرني بأي وصفة تخطر على بالك وأنا أضبطك بالمقادير والخطوات فوراً!",
  "😄 واحد قال لزوجته: سوي لنا حلى سريع! جابت له بسكويت ماري وكوب حليب وقالت له: غمس وأنت ساكت، هذا أسرع حلى في التاريخ! 😂🍪\\n\\nولو تبي حلى فخم بجد، بس قولي وأنا أعطيك الوصفة الكاملة الحين!"
];

export function registerAiEngineV112(app: Express) {
  app.use("/api/ai-studio", express.json({ limit: "50mb" }));

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
        return res.json({ ok: true, passThrough: true });
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

      // 1. Check Custom Admin Rules first (Tab 2)
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
      const matchedRecipe = findMatchingSavedRecipeV117(userMessage + " " + productContextName, memoryConfig.recipes);
      if (matchedRecipe) {
        zeroTokenCounter++;
        const matchedItems: any[] = [];
        const tableRows: IngredientTableRowV121[] = [];
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

        const replyMsg =
          "🍰 " + matchedRecipe.title + "\\n\\n" +
          "📋 طريقة التحضير والخطوات الكاملة:\\n" +
          matchedRecipe.steps +
          (missingList.length > 0
            ? "\\n\\n💡 ملاحظة للزبون: المكونات المتوفرة بالمتجر يمكنك إضافتها للسلة مباشرة بالأسفل، أما المكونات الإضافية غير الظاهرة بالمتجر فيمكنك نسخها بضغطة زر من الجدول أدناه لتوضع تلقائياً في (ملاحظة الطلب) وسيرد عليك المتجر فوراً حول حالة توفرها!"
            : "");

        return res.json({
          ok: true,
          zeroToken: true,
          matchedOverride: true,
          reply: replyMsg,
          recipeTitle: matchedRecipe.title,
          recipeImage: matchedRecipe.imageUrl || "",
          recipeSteps: matchedRecipe.steps || "",
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
        const joke = FUNNY_CLEAN_JOKES_V121[Math.floor(Math.random() * FUNNY_CLEAN_JOKES_V121.length)];
        return res.json({
          ok: true,
          zeroToken: true,
          matchedOverride: true,
          reply: joke,
          suggestedItems: []
        });
      }

      // 5. ANY Recipe / Dish Request (Even if ingredients are NOT in the store!)
      const builtInRecipe = buildDynamicRecipeResponseV121(userMessage, allProds);
      if (builtInRecipe && !productContextName) {
        zeroTokenCounter++;
        const fullRecipeReply =
          "👨‍🍳 أبشر يا غالي! جبت لك الوصفة الكاملة لـ «" + builtInRecipe.title + "» (⏱️ وقت التحضير: " + builtInRecipe.prepTime + "):\\n\\n" +
          "📋 خطوات التحضير بالتفصيل:\\n" +
          builtInRecipe.steps +
          "\\n\\n📊 بالأسفل جهزت لك جدولاً كاملاً يوضح المكونات المتوفرة حالياً في متجر أورجنال (تقدر تضيفها للسلة فوراً)، والمكونات الإضافية غير الظاهرة بالمتجر (تقدر تنسخها وتضعها تلقائياً في ملاحظة الطلب بضغطة زر، وسيرد عليك المتجر فوراً لتأكيد توفيرها مع طلبك!).";

        return res.json({
          ok: true,
          zeroToken: true,
          matchedOverride: true,
          reply: fullRecipeReply,
          recipeTitle: builtInRecipe.title,
          ingredientsTable: builtInRecipe.tableRows,
          missingItemsText: builtInRecipe.missingItemsText,
          suggestedItems: builtInRecipe.availableItems
        });
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

      const stopWords = new Set(["هل", "عندكم", "معاكم", "معكم", "في", "متوفر", "اريد", "ابغي", "اشتي", "بكم", "سعر", "وين", "وش", "ايش", "كيف", "طريقه", "عمل", "وصفه", "معلومات", "سعرات", "ابحث", "عن", "رد", "منك", "لو", "سمحت", "شي", "حاجه"]);
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
          : "فهمتك يا غالي! أنت تطلب «" + requestedName + "».. حلو حلو 👌\\nحالياً هذا الصنف غير ظاهر في قائمة المتجر، لكن ولا يهمك! جهزته لك في الجدول بالأسفل كصنف قابل للطلب: اضغط على زر (📋 نسخ ووضع الصنف في ملاحظة الطلب) ليُضاف تلقائياً مع طلبك، وسيتواصل معك المتجر ويرد عليك فوراً حول حالة توفره!";
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

pathlib.Path("server/ai_engine_v112.ts").write_text(ai_engine_v121_ts, encoding="utf-8")
print("1. Wrote complete server/ai_engine_v112.ts (v121 Master Chef + Split Ingredients Table Engine)!")

# ==============================================================================
# 2. تحديث server/commerce.ts لإعادة max_tokens: 1500 حتى لا تنقطع ردود الذكاء الاصطناعي
# ==============================================================================
comm_path = pathlib.Path("server/commerce.ts")
if comm_path.exists():
    cc = comm_path.read_text(encoding="utf-8")
    cc = re.sub(r'max_tokens:\s*180\b', 'max_tokens: 1500', cc)
    comm_path.write_text(cc, encoding="utf-8")
    print("2. Restored max_tokens: 1500 in server/commerce.ts!")

# ==============================================================================
# 3. تحديث client/index.html:
#    - واجهة شات احترافية بأسلوب Gemini / ChatGPT (رسالة المستخدم محاطة بإطار أبيض أنيق، ورد البوت يملأ العرض بالكامل بدون بالون ضيق)
#    - عرض جدول المكونات المتوفرة وغير المتوفرة لأي وصفة مع زر نسخ المكونات غير المتوفرة ووضعها تلقائياً في ملاحظة الطلب
#    - إبقاء قسم تخصيص الذكاء الاصطناعي قسماً مستقلاً تماماً بملء الشاشة
# ==============================================================================
html_path = pathlib.Path("client/index.html")
if html_path.exists():
    ht = html_path.read_text(encoding="utf-8")

    gemini_helper_and_css = """
        window.__v121SmartDataByQuery = window.__v121SmartDataByQuery || {};

        (function injectGeminiChatStylesV121() {
          if (document.getElementById("v121-gemini-chat-styles")) return;
          var st = document.createElement("style");
          st.id = "v121-gemini-chat-styles";
          st.textContent =
            ".v121-gemini-user-bubble { background: #ffffff !important; color: #0f172a !important; border: 1.5px solid #cbd5e1 !important; border-radius: 20px 20px 4px 20px !important; padding: 10px 16px !important; box-shadow: 0 2px 8px rgba(15,23,42,0.06) !important; font-weight: 700 !important; }" +
            ".v121-gemini-user-bubble * { color: #0f172a !important; }" +
            ".v121-gemini-bot-full { width: 100% !important; max-width: 100% !important; background: transparent !important; border: none !important; box-shadow: none !important; border-bottom: 1px solid #e2e8f0 !important; border-radius: 0 !important; padding: 14px 4px 18px 4px !important; margin: 4px 0 !important; }" +
            ".v121-gemini-bot-row { width: 100% !important; max-width: 100% !important; display: block !important; }";
          document.head.appendChild(st);
        })();

        window.__copyAndAttachMissingToOrderNotesV121 = function(btnEl, missingText, recipeTitle) {
          var fullNote = "📋 مكونات إضافية مطلوبة (" + (recipeTitle || "وصفة الشيف") + "): " + missingText + " — يرجى إفادتي بحالة توفرها وإضافتها مع طلبي.";
          try {
            localStorage.setItem("original_v121_order_note", fullNote);
          } catch (e) {}
          if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(fullNote).catch(function() {});
          } else {
            try {
              var ta = document.createElement("textarea");
              ta.value = fullNote;
              document.body.appendChild(ta);
              ta.select();
              document.execCommand("copy");
              ta.remove();
            } catch (e) {}
          }
          syncOrderNotesFieldV121();
          fetch("/api/ai-studio/request-item", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              sessionId: window.__v112SessionId,
              requestedItem: missingText,
              userMessage: fullNote
            })
          }).catch(function() {});
          if (btnEl) {
            btnEl.style.background = "#15803d";
            btnEl.style.color = "#ffffff";
            btnEl.textContent = "✅ تم النسخ ووضع المكونات في ملاحظة الطلب! سيرد عليك المتجر بحالة توفرها";
          }
        };

        function syncOrderNotesFieldV121() {
          var savedNote = "";
          try {
            savedNote = localStorage.getItem("original_v121_order_note") || "";
          } catch (e) {}
          if (!savedNote) return;

          var noteFields = Array.from(document.querySelectorAll("textarea, input[type='text']")).filter(function(el) {
            var ph = (el.getAttribute("placeholder") || "") + " " + (el.getAttribute("name") || "") + " " + (el.getAttribute("aria-label") || "");
            var parentTxt = el.parentElement ? (el.parentElement.textContent || "") : "";
            return (
              ph.indexOf("ملاحظ") !== -1 ||
              ph.indexOf("توجيهات") !== -1 ||
              ph.indexOf("note") !== -1 ||
              (parentTxt.indexOf("ملاحظات") !== -1 && parentTxt.length < 120)
            );
          });

          noteFields.forEach(function(field) {
            if (window.location.pathname.indexOf("/admin") !== -1) return;
            var curVal = field.value || "";
            if (curVal.indexOf(savedNote) === -1 && field.getAttribute("data-v121-note-filled") !== savedNote) {
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
                field.setAttribute("data-v121-note-filled", savedNote);
              } catch (e) {
                field.value = nextVal;
              }
            }
          });
        }
"""

    if "window.__copyAndAttachMissingToOrderNotesV121" not in ht:
        ht = ht.replace(
            "window.__openRecipeImageLightboxV116 = function(src, title) {",
            gemini_helper_and_css + "\n        window.__openRecipeImageLightboxV116 = function(src, title) {"
        )

    ht = ht.replace(
        "replaceTrpcAiPayloadInPlaceV117(trpcJson, smartData);",
        "if (detectedMsg) { window.__v121SmartDataByQuery[normalizeArabicClientV116(detectedMsg)] = smartData; }\n                        replaceTrpcAiPayloadInPlaceV117(trpcJson, smartData);"
    )

    ht = ht.replace(
        "if (!smartData || !smartData.ok) return trpcRes;",
        "if (!smartData || !smartData.ok || smartData.passThrough || !smartData.matchedOverride) return trpcRes;"
    )

    old_enhance_pattern = r"function (?:isDarkGreenBgV119|enhanceChatBubblesSafelyV117)\([\s\S]*?\n        \}\n\n        var origFetch = window\.fetch;"
    if not re.search(old_enhance_pattern, ht):
        old_enhance_pattern = r"function enhanceChatBubblesSafelyV117\(\) \{[\s\S]*?\n        \}\n\n        var origFetch = window\.fetch;"

    new_enhance_v121 = """function isDarkGreenBgV119(el) {
          if (!el || el === document.body) return false;
          if (el.getAttribute && el.getAttribute("data-v121-role") === "user") return true;
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
          var cur = el;
          for (var i = 0; i < 4 && cur && cur !== document.body; i++) {
            if (cur.getAttribute && cur.getAttribute("data-v121-role") === "user") return true;
            if (isDarkGreenBgV119(cur)) return true;
            cur = cur.parentElement;
          }
          return false;
        }

        function buildIngredientsTableHtmlV121(tableRows, missingItemsText, recipeTitle) {
          if (!Array.isArray(tableRows) || tableRows.length === 0) return "";
          var rowsHtml = tableRows.map(function(row) {
            var statusHtml = row.available
              ? '<span style="display:inline-block;background:#dcfce7;color:#15803d;padding:3px 9px;border-radius:99px;font-weight:800;font-size:0.76rem;">✅ متوفر بالمتجر (' + (row.price || 100) + ' ر.ي)</span>'
              : '<span style="display:inline-block;background:#fef3c7;color:#b45309;padding:3px 9px;border-radius:99px;font-weight:800;font-size:0.76rem;">📌 غير ظاهر بالمتجر (يُطلب في الملاحظة)</span>';
            return (
              '<tr style="border-bottom:1px solid #e2e8f0;">' +
              '<td style="padding:8px 10px;font-weight:800;color:#0f172a;font-size:0.84rem;">' + (row.name || "") + '</td>' +
              '<td style="padding:8px 10px;color:#475569;font-size:0.82rem;font-weight:700;">' + (row.amount || "حسب الرغبة") + '</td>' +
              '<td style="padding:8px 10px;">' + statusHtml + '</td>' +
              '</tr>'
            );
          }).join("");

          var safeMissing = String(missingItemsText || "").replace(/"/g, "&quot;").replace(/'/g, "\\'");
          var safeTitle = String(recipeTitle || "وصفة الشيف").replace(/"/g, "&quot;").replace(/'/g, "\\'");

          var missingActionHtml = "";
          if (missingItemsText) {
            missingActionHtml =
              '<div style="margin-top:10px;padding:12px;background:#fffbeb;border:1.5px solid #f59e0b;border-radius:12px;">' +
              '<div style="font-weight:900;color:#92400e;font-size:0.86rem;margin-bottom:4px;">📦 منتجات ومكونات إضافية قابلة للطلب مع فاتورتك:</div>' +
              '<div style="font-size:0.82rem;color:#78350f;font-weight:700;margin-bottom:8px;">«' + missingItemsText + '»</div>' +
              '<button type="button" class="v121-copy-notes-btn" data-missing="' + safeMissing + '" data-title="' + safeTitle + '" style="width:100%;padding:10px 14px;border-radius:10px;border:none;background:linear-gradient(135deg,#0d3825 0%,#165b3c 100%);color:#d4af37;font-weight:900;font-size:0.85rem;cursor:pointer;box-shadow:0 4px 12px rgba(13,56,37,0.2);">📋 نسخ المكونات غير المتوفرة ووضعها تلقائياً في ملاحظة الطلب</button>' +
              '<div style="font-size:0.77rem;color:#475569;margin-top:7px;line-height:1.5;font-weight:700;">💡 <b>توضيح للزبون:</b> عند الضغط على الزر أعلاه، يتم نسخ هذه المكونات ووضعها تلقائياً في خانة (ملاحظة الطلب) لترسلها مع طلبك، وسيتواصل معك المتجر ويرد عليك فوراً حول حالة توفر المنتجات اللازمة أو الإضافية!</div>' +
              '</div>';
          }

          return (
            '<div style="margin:12px 0;border:1.5px solid #cbd5e1;border-radius:14px;overflow:hidden;background:#ffffff;box-shadow:0 4px 14px rgba(15,23,42,0.05);direction:rtl;text-align:right;">' +
            '<div style="background:#f8fafc;padding:10px 14px;border-bottom:1.5px solid #cbd5e1;font-weight:900;color:#0d3825;font-size:0.88rem;">📊 جدول مكونات الوصفة (المتوفر بالمتجر والمكونات الإضافية للطلب)</div>' +
            '<div style="overflow-x:auto;">' +
            '<table style="width:100%;border-collapse:collapse;text-align:right;direction:rtl;">' +
            '<thead><tr style="background:#f1f5f9;border-bottom:1.5px solid #cbd5e1;">' +
            '<th style="padding:8px 10px;font-size:0.8rem;color:#334155;font-weight:900;">المكون / الصنف</th>' +
            '<th style="padding:8px 10px;font-size:0.8rem;color:#334155;font-weight:900;">المقدار</th>' +
            '<th style="padding:8px 10px;font-size:0.8rem;color:#334155;font-weight:900;">حالة التوفر في المتجر</th>' +
            '</tr></thead>' +
            '<tbody>' + rowsHtml + '</tbody>' +
            '</table>' +
            '</div>' +
            (missingActionHtml ? '<div style="padding:0 12px 12px 12px;">' + missingActionHtml + '</div>' : '') +
            '</div>'
          );
        }

        function enhanceChatBubblesSafelyV117() {
          syncOrderNotesFieldV121();
          if (document.body.textContent.indexOf("مساعد وشيف أورجنال الذكي") === -1) return;

          // 1. Clean up any accidental photo boxes inside user bubbles
          Array.from(document.querySelectorAll(".v117-recipe-photo-banner, .v118-wa-photo-box")).forEach(function(box) {
            if (box.classList.contains("v117-recipe-photo-banner") || isInsideDarkGreenUserBubbleV119(box)) {
              box.remove();
            }
          });

          // 2. Find all USER message bubbles and style them with clean white Gemini/ChatGPT bordered pill!
          var allUserBubbles = Array.from(document.querySelectorAll("div, p, span")).filter(function(el) {
            if (!isDarkGreenBgV119(el)) return false;
            if (el.tagName === "BUTTON" || el.querySelector("button, input, textarea")) return false;
            var hasDarkGreenChild = Array.from(el.children).some(function(c) { return isDarkGreenBgV119(c); });
            if (hasDarkGreenChild) return false;
            var t = (el.textContent || "").trim();
            if (t.indexOf("محادثة جديدة") !== -1 || t.indexOf("الأصناف والمقادير") !== -1) return false;
            if (t.length < 1 || t.length > 220) return false;

            el.setAttribute("data-v121-role", "user");
            el.classList.add("v121-gemini-user-bubble");

            if (t.indexOf("🍰") !== -1 && el.getAttribute("data-v119-orig-user")) {
              setLeafTextSafe(el, el.getAttribute("data-v119-orig-user"));
            } else if (t.indexOf("🍰") === -1 && !el.getAttribute("data-v119-orig-user")) {
              el.setAttribute("data-v119-orig-user", t);
            }
            return true;
          });

          // 3. Find all AI Assistant reply paragraphs and style their container as full-width Gemini/ChatGPT layout!
          var allLeaves = Array.from(document.querySelectorAll("p, div")).filter(function(el) {
            if (el.children.length !== 0) return false;
            if (el.closest && (el.closest(".v118-wa-photo-box") || el.closest(".v121-ingredients-panel") || el.closest(".v121-gemini-ai-header") || el.closest("button"))) return false;
            if (isInsideDarkGreenUserBubbleV119(el)) return false;

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

          allLeaves.forEach(function(replyLeaf) {
            var assistantCard = replyLeaf.parentElement;
            if (!assistantCard || isInsideDarkGreenUserBubbleV119(assistantCard)) return;

            assistantCard.classList.add("v121-gemini-bot-full");
            if (assistantCard.parentElement && assistantCard.parentElement.textContent.indexOf("محادثة جديدة") === -1) {
              assistantCard.parentElement.classList.add("v121-gemini-bot-row");
            }

            if (!assistantCard.querySelector(".v121-gemini-ai-header")) {
              var aiHdr = document.createElement("div");
              aiHdr.className = "v121-gemini-ai-header";
              aiHdr.style.cssText = "display:flex;align-items:center;gap:6px;margin-bottom:8px;font-weight:900;font-size:0.82rem;color:#0d3825;";
              aiHdr.innerHTML = "<span style='background:#0d3825;color:#d4af37;width:22px;height:22px;border-radius:99px;display:inline-flex;align-items:center;justify-content:center;font-size:0.72rem;'>✨</span><span>شيف ومساعد أورجنال الذكي</span>";
              assistantCard.insertBefore(aiHdr, assistantCard.firstChild);
            }

            replyLeaf.style.whiteSpace = "pre-line";
            replyLeaf.style.lineHeight = "1.75";
            replyLeaf.style.fontSize = "0.95rem";
            replyLeaf.style.color = "#0f172a";

            var precedingUsers = allUserBubbles.filter(function(ub) {
              return Boolean(ub.compareDocumentPosition(assistantCard) & Node.DOCUMENT_POSITION_FOLLOWING);
            });
            var lastUserBubble = precedingUsers.length > 0 ? precedingUsers[precedingUsers.length - 1] : null;
            var userQueryTxt = "";
            if (lastUserBubble) {
              userQueryTxt = (lastUserBubble.getAttribute("data-v119-orig-user") || lastUserBubble.textContent || "").trim();
            }
            if (!userQueryTxt) return;

            var normQ = normalizeArabicClientV116(userQueryTxt);
            var cachedSmart = window.__v121SmartDataByQuery[normQ];

            if (!cachedSmart && !assistantCard.getAttribute("data-v121-fetched")) {
              assistantCard.setAttribute("data-v121-fetched", "1");
              origFetch("/api/ai-studio/smart-chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: userQueryTxt, sessionId: window.__v112SessionId })
              })
                .then(function(r) { return r.json(); })
                .then(function(sd) {
                  if (sd && sd.ok && sd.matchedOverride) {
                    window.__v121SmartDataByQuery[normQ] = sd;
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

              if (Array.isArray(cachedSmart.ingredientsTable) && cachedSmart.ingredientsTable.length > 0 && !assistantCard.querySelector(".v121-ingredients-panel")) {
                var tblPanel = document.createElement("div");
                tblPanel.className = "v121-ingredients-panel";
                tblPanel.innerHTML = buildIngredientsTableHtmlV121(
                  cachedSmart.ingredientsTable,
                  cachedSmart.missingItemsText || "",
                  cachedSmart.recipeTitle || userQueryTxt
                );
                if (replyLeaf.nextSibling) {
                  replyLeaf.parentNode.insertBefore(tblPanel, replyLeaf.nextSibling);
                } else {
                  replyLeaf.parentNode.appendChild(tblPanel);
                }
                var copyBtn = tblPanel.querySelector(".v121-copy-notes-btn");
                if (copyBtn) {
                  copyBtn.onclick = function() {
                    window.__copyAndAttachMissingToOrderNotesV121(
                      copyBtn,
                      copyBtn.getAttribute("data-missing") || "",
                      copyBtn.getAttribute("data-title") || ""
                    );
                  };
                }
              }
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
        }

        var origFetch = window.fetch;"""

    ht, n_enh = re.subn(old_enhance_pattern, lambda m: new_enhance_v121, ht, count=1)

    ht = ht.replace(
        "if (d && d.ok && d.config) {\n                window.__v114StudioConfig = d.config;",
        "if (d && d.ok && d.config && hasAnyStudioItemsV115(d.config)) {\n                window.__v114StudioConfig = d.config;"
    )
    old_sidebar_fn = r"function ensureDedicatedAiSidebarItemV114\(\) \{[\s\S]*?function updateStudioHeaderBadgesOnlyV115\(\)"
    new_sidebar_fn = """function ensureDedicatedAiSidebarItemV114() {
          if (window.location.pathname.indexOf("/admin") === -1) {
            var oldFloat = document.getElementById("v120-floating-studio-btn");
            if (oldFloat) oldFloat.remove();
            return;
          }

          var pendingCount = (window.__v114Requests || []).filter(function(r) { return r.status === "pending"; }).length;

          var floatBtn = document.getElementById("v120-floating-studio-btn");
          if (!floatBtn) {
            floatBtn = document.createElement("button");
            floatBtn.id = "v120-floating-studio-btn";
            floatBtn.type = "button";
            floatBtn.style.cssText = "position:fixed;bottom:18px;left:16px;z-index:99991;display:flex;align-items:center;gap:8px;padding:11px 16px;border-radius:99px;border:2px solid #d4af37;background:linear-gradient(135deg,#0d3825 0%,#165b3c 100%);color:#ffffff;font-weight:900;font-size:0.88rem;cursor:pointer;box-shadow:0 10px 26px rgba(13,56,37,0.38);direction:rtl;";
            floatBtn.onclick = function(ev) {
              ev.preventDefault();
              ev.stopPropagation();
              window.__v114StudioOpen = true;
              refreshStudioDataV114(false);
              renderAiStudioDedicatedPageV114();
            };
            document.body.appendChild(floatBtn);
          }
          floatBtn.innerHTML =
            "<span>🤖 قسم تخصيص الذكاء الاصطناعي</span>" +
            (pendingCount > 0
              ? "<span style='background:#ef4444;color:#fff;border-radius:99px;padding:2px 8px;font-size:0.75rem;font-weight:900;'>" + pendingCount + "</span>"
              : "<span style='background:#d4af37;color:#0d3825;border-radius:99px;padding:2px 8px;font-size:0.72rem;font-weight:900;'>مستقل</span>");

          var allClickables = Array.from(document.querySelectorAll("aside button, nav button, aside a, nav a, button, a"));
          var mainNavAnchor = allClickables.find(function(el) {
            var t = (el.textContent || "").trim();
            return (t === "الطلبات" || t === "المنتجات" || t === "الأقسام") && el.id !== "v114-dedicated-ai-nav-btn";
          });

          if (mainNavAnchor && mainNavAnchor.parentElement && !document.getElementById("v114-dedicated-ai-nav-btn")) {
            var navBtn = document.createElement("button");
            navBtn.id = "v114-dedicated-ai-nav-btn";
            navBtn.type = "button";
            navBtn.style.cssText = "width:100%;display:flex;align-items:center;justify-content:space-between;padding:11px 14px;margin:6px 0;border-radius:12px;border:2px solid #d4af37;background:linear-gradient(135deg,#0d3825 0%,#165b3c 100%);color:#ffffff;font-weight:900;font-size:0.9rem;cursor:pointer;box-shadow:0 6px 16px rgba(13,56,37,0.22);direction:rtl;text-align:right;";
            navBtn.innerHTML =
              "<span style='display:flex;align-items:center;gap:8px;'><span>🤖</span><span>تخصيص الذكاء الاصطناعي</span></span>" +
              (pendingCount > 0
                ? "<span style='background:#ef4444;color:#fff;border-radius:99px;padding:2px 8px;font-size:0.75rem;font-weight:900;'>" + pendingCount + "</span>"
                : "<span style='background:#d4af37;color:#0d3825;border-radius:99px;padding:2px 8px;font-size:0.72rem;font-weight:900;'>قسم مستقل</span>");

            navBtn.onclick = function(ev) {
              ev.preventDefault();
              ev.stopPropagation();
              window.__v114StudioOpen = true;
              refreshStudioDataV114(false);
              renderAiStudioDedicatedPageV114();
            };

            mainNavAnchor.parentElement.appendChild(navBtn);
          }
        }

        function updateStudioHeaderBadgesOnlyV115()"""
    ht = re.sub(old_sidebar_fn, lambda m: new_sidebar_fn, ht, count=1)

    old_studio_container = r"var mainContainer =[\s\S]*?mainContainer\.insertBefore\(studioPage, mainContainer\.firstChild\);\s*\}"
    new_studio_container = """if (!studioPage) {
            studioPage = document.createElement("div");
            studioPage.id = "v114-dedicated-studio-page";
            studioPage.style.cssText = "position:fixed;inset:0;width:100vw;height:100vh;overflow-y:auto;z-index:99995;padding:18px;box-sizing:border-box;background:#f4fbf7;direction:rtl;text-align:right;";
            document.body.appendChild(studioPage);
          }"""
    ht = re.sub(old_studio_container, lambda m: new_studio_container, ht, count=1)

    html_path.write_text(ht, encoding="utf-8")
    print("3. Updated client/index.html with Gemini/ChatGPT UI + Ingredients Table + Auto Order Notes (replacements:", n_enh, ")!")

# ==============================================================================
# 4. ترقية رقم كاش Service Worker إلى v121
# ==============================================================================
sw_path = pathlib.Path("client/public/sw.js")
if sw_path.exists():
    sw_txt = sw_path.read_text(encoding="utf-8")
    sw_txt = re.sub(r'v10\d|v11\d|v12\d|v9\d', 'v121', sw_txt)
    sw_path.write_text(sw_txt, encoding="utf-8")
    print("4. Bumped Service Worker cache to v121!")

# ==============================================================================
# 5. فحص البناء والرفع إلى Render
# ==============================================================================
res_srv = subprocess.run(
    "npx esbuild server/_core/index.ts --bundle --platform=node --format=esm --packages=external --outfile=./.tmp_srv_v121.js",
    shell=True, capture_output=True, text=True
)
res_cli = subprocess.run(
    "npx esbuild client/src/pages/Admin.tsx client/src/pages/Home.tsx --bundle --platform=browser --packages=external --outdir=./.tmp_cli_v121",
    shell=True, capture_output=True, text=True
)
os.system("rm -rf ./.tmp_srv_v121.js ./.tmp_cli_v121")

if res_srv.returncode != 0 or res_cli.returncode != 0:
    print("❌ Build check failed:", res_srv.stderr, res_cli.stderr)
else:
    print("✅ Build check passed 100%!")
    os.system("git add server/ai_engine_v112.ts server/commerce.ts client/index.html client/public/sw.js")
    os.system('git commit -m "Feat v121: Gemini/ChatGPT chat layout, full recipes even when items missing, available vs missing ingredients table, and 1-click copy to order notes"')
    os.system("git push origin main")
    print("🚀 تم الرفع بنجاح إلى Render (v121)!")
