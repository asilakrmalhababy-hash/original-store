import express from "express";
import fs from "fs";
import path from "path";
import { sql } from "drizzle-orm";
import { getDb } from "./db";
import { products } from "../drizzle/schema";

export interface CustomInstructionV114 {
  id: string;
  category: string;
  content: string;
  active: boolean;
}

export interface CustomRuleV114 {
  id: string;
  trigger: string;
  response: string;
  linkedProductId?: string;
  linkedProductName?: string;
  linkedProductUrl?: string;
}

export interface PromotedProductV114 {
  id: string;
  productId?: string;
  productName: string;
  productUrl: string;
  productPrice?: number;
  productImage?: string;
  promoBadge: string;
  promoMessage: string;
  triggerKeywords: string;
  active: boolean;
}

export interface AiRecipeV114 {
  id: string;
  title: string;
  imageUrl: string;
  keywords: string;
  steps: string;
  ingredients: Array<{
    productId?: string;
    name: string;
    price?: number;
    url?: string;
  }>;
}

export interface AiStudioConfigV114 {
  generalSystemPrompt: string;
  instructions: CustomInstructionV114[];
  rules: CustomRuleV114[];
  promotedProducts: PromotedProductV114[];
  recipes: AiRecipeV114[];
  productAiMap: Record<string, string>;
  ecoMode10k: boolean;
}

export interface CustomerAiRequestV114 {
  id: string;
  sessionId: string;
  customerName: string;
  customerPhone: string;
  requestedItem: string;
  customerMessage: string;
  status: "pending" | "replied";
  managerReply: string;
  attachedProductName?: string;
  attachedProductUrl?: string;
  repliedAt?: number;
  createdAt: number;
}

const EMPTY_STUDIO_CONFIG_V114: AiStudioConfigV114 = {
  generalSystemPrompt: "",
  instructions: [],
  rules: [],
  promotedProducts: [],
  recipes: [],
  productAiMap: {},
  ecoMode10k: true
};

const BACKUP_FILE_PATH = path.resolve(process.cwd(), "ai_studio_v115_backup.json");

let studioConfigV114: AiStudioConfigV114 = JSON.parse(JSON.stringify(EMPTY_STUDIO_CONFIG_V114));
let customerRequestsV114: CustomerAiRequestV114[] = [];
let replyCacheV114: Record<string, any> = {};
let tokenStatsV114 = {
  zeroTokenMessages: 0,
  cachedHits: 0,
  estimatedTokensSaved: 0
};
let cachedCatalogV114: any[] = [];
let lastCatalogTimeV114 = 0;
let tableLoadedFromDbV115 = false;

function normalizeStudioConfigV115(p: any): AiStudioConfigV114 {
  if (!p || typeof p !== "object") {
    return JSON.parse(JSON.stringify(EMPTY_STUDIO_CONFIG_V114));
  }
  return {
    generalSystemPrompt: String(p.generalSystemPrompt || ""),
    instructions: Array.isArray(p.instructions) ? p.instructions : [],
    rules: Array.isArray(p.rules) ? p.rules : [],
    promotedProducts: Array.isArray(p.promotedProducts) ? p.promotedProducts : [],
    recipes: Array.isArray(p.recipes) ? p.recipes : [],
    productAiMap: p.productAiMap && typeof p.productAiMap === "object" ? p.productAiMap : {},
    ecoMode10k: p.ecoMode10k !== false
  };
}

function loadDiskBackupV115() {
  try {
    if (fs.existsSync(BACKUP_FILE_PATH)) {
      const raw = fs.readFileSync(BACKUP_FILE_PATH, "utf-8");
      const parsed = JSON.parse(raw);
      if (parsed && (parsed.studio_config || parsed.config)) {
        studioConfigV114 = normalizeStudioConfigV115(parsed.studio_config || parsed.config);
      }
      if (parsed && Array.isArray(parsed.customer_requests || parsed.requests)) {
        customerRequestsV114 = parsed.customer_requests || parsed.requests;
      }
    }
  } catch {}
}
loadDiskBackupV115();

function saveDiskBackupV115() {
  try {
    fs.writeFileSync(
      BACKUP_FILE_PATH,
      JSON.stringify({
        studio_config: studioConfigV114,
        customer_requests: customerRequestsV114,
        updatedAt: Date.now()
      }),
      "utf-8"
    );
  } catch {}
}

async function runRawSqlV115(db: any, queryStr: string, params: any[] = []): Promise<any> {
  const client = db?.$client || db?.session?.client;
  if (client && typeof client.execute === "function") {
    const [rows] = await client.execute(queryStr, params);
    return rows;
  }
  if (client && typeof client.query === "function") {
    const [rows] = await client.query(queryStr, params);
    return rows;
  }
  const parts = queryStr.split("?");
  const tpl: any = parts.slice();
  tpl.raw = parts.slice();
  const res: any = await db.execute(sql(tpl as TemplateStringsArray, ...params));
  return Array.isArray(res) && Array.isArray(res[0]) ? res[0] : res;
}

let dbCircuitOpenUntilV131 = 0;
let lastStudioTableAttemptV131 = 0;

export function invalidateAiCatalogCacheV131() {
  lastCatalogTimeV114 = 0;
}

export function invalidateAiOrdersCacheV131() {
  lastOrdersTimeV126 = 0;
}

async function getCatalogCachedV114(): Promise<any[]> {
  const now = Date.now();
  if (now < dbCircuitOpenUntilV131) return cachedCatalogV114;
  if (lastCatalogTimeV114 > 0 && now - lastCatalogTimeV114 < 1800000) {
    return cachedCatalogV114;
  }
  lastCatalogTimeV114 = now;
  try {
    const db: any = await getDb();
    if (db) {
      const rows = await db.select().from(products);
      if (Array.isArray(rows)) cachedCatalogV114 = rows;
    }
  } catch (err: any) {
    const msg = String(err?.message || err || "");
    if (msg.includes("1105") || msg.includes("quota") || msg.includes("restricted")) {
      dbCircuitOpenUntilV131 = Date.now() + 60000;
    }
  }
  return cachedCatalogV114;
}

let cachedLatestOrdersV126: any[] = [];
let lastOrdersTimeV126 = 0;

async function getLatestOrdersCachedV126(): Promise<any[]> {
  const now = Date.now();
  if (now < dbCircuitOpenUntilV131) return cachedLatestOrdersV126;
  if (lastOrdersTimeV126 > 0 && now - lastOrdersTimeV126 < 30000) {
    return cachedLatestOrdersV126;
  }
  lastOrdersTimeV126 = now;
  try {
    const db: any = await getDb();
    if (db) {
      const rows: any = await runRawSqlV115(
        db,
        "SELECT id, orderNumber, customerName, customerPhone, total, status, createdAt FROM orders ORDER BY id DESC LIMIT 10"
      );
      if (Array.isArray(rows)) {
        cachedLatestOrdersV126 = rows;
      }
    }
  } catch (err: any) {
    const msg = String(err?.message || err || "");
    if (msg.includes("1105") || msg.includes("quota") || msg.includes("restricted")) {
      dbCircuitOpenUntilV131 = Date.now() + 60000;
    }
  }
  return cachedLatestOrdersV126;
}

async function ensureStudioTableV114() {
  if (tableLoadedFromDbV115) return;
  const now = Date.now();
  if (now < dbCircuitOpenUntilV131 || (lastStudioTableAttemptV131 > 0 && now - lastStudioTableAttemptV131 < 60000)) {
    return;
  }
  lastStudioTableAttemptV131 = now;
  try {
    const db: any = await getDb();
    if (!db) return;
    await runRawSqlV115(
      db,
      "CREATE TABLE IF NOT EXISTS ai_studio_v115 (" +
      "k VARCHAR(190) PRIMARY KEY, " +
      "v LONGTEXT NOT NULL, " +
      "updatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP" +
      ")"
    );
    tableLoadedFromDbV115 = true;

    const rows: any = await runRawSqlV115(db, "SELECT k, v FROM ai_studio_v115");
    if (Array.isArray(rows)) {
      for (const r of rows) {
        if (r && (r.k === "studio_config" || r.k === "config") && r.v) {
          try {
            const p = JSON.parse(String(r.v));
            studioConfigV114 = normalizeStudioConfigV115(p);
          } catch {}
        } else if (r && r.k === "customer_requests" && r.v) {
          try {
            const pr = JSON.parse(String(r.v));
            if (Array.isArray(pr)) customerRequestsV114 = pr;
          } catch {}
        }
      }
      saveDiskBackupV115();
    }
  } catch (err: any) {
    const msg = String(err?.message || err || "");
    if (msg.includes("1105") || msg.includes("quota") || msg.includes("restricted")) {
      dbCircuitOpenUntilV131 = Date.now() + 60000;
    }
  }
}

async function saveStudioKeyV114(key: string, valObj: any) {
  saveDiskBackupV115();
  if (Date.now() < dbCircuitOpenUntilV131) return;
  try {
    await ensureStudioTableV114();
    const db: any = await getDb();
    if (!db) return;
    const jsonStr = JSON.stringify(valObj);
    await runRawSqlV115(
      db,
      "INSERT INTO ai_studio_v115 (k, v) VALUES (?, ?) ON DUPLICATE KEY UPDATE v = VALUES(v)",
      [key, jsonStr]
    );
  } catch {}
}

export function cleanProductNameV112(raw: string): string {
  return String(raw || "")
    .replace(/\(\s*رقم\s*\d+\s*\)/g, "")
    .replace(/\s*\([^()]*\)\s*$/g, "")
    .trim();
}

export function getProductCustomAiInfoV112(productId?: any, productName?: any): string {
  const map = studioConfigV114.productAiMap || {};
  if (productId !== undefined && productId !== null && map["id:" + String(productId)]) {
    return String(map["id:" + String(productId)]).trim();
  }
  const cName = cleanProductNameV112(String(productName || ""));
  if (cName && map["name:" + cName]) {
    return String(map["name:" + cName]).trim();
  }
  for (const [k, v] of Object.entries(map)) {
    if (k.startsWith("name:") && cName && (k.slice(5) === cName || cName.includes(k.slice(5)))) {
      return String(v || "").trim();
    }
  }
  return "";
}

export type ProductAiKindV112 = "chocolate_snack" | "biscuit_dessert" | "drink_juice" | "non_food" | "cooking_food";

export function classifyProductKindV112(name: string, categoryName = "", customAiInfo = ""): ProductAiKindV112 {
  const combined = (name + " " + categoryName + " " + customAiInfo).toLowerCase();
  if (/(سجائر|سجاير|دخان|شملان|كمران|منظف|صابون|شامبو|مناديل|فحم|ولاعة|أكياس|اكياس)/.test(combined)) {
    return "non_food";
  }
  if (/(بسكويت|بسكوت|ماري|أبو ولد|ابو ولد|نخالة|شاي|ديما|أوريو|اوريو|معمول|كليجا|توبس)/.test(combined)) {
    return "biscuit_dessert";
  }
  if (/(شوكلات|شوكولات|شكلاته|شوكو|بلاتو|بليلا|بريك|ويفر|علك|باطوق|حلاو|مصاص|شيبس|بطاط|فشار|كروسان|كيك|جالكسي|كتكات|سنكرز|توبي|سعيد|مارشملو|جيلي|كاكاو)/.test(combined)) {
    return "chocolate_snack";
  }
  if (/(عصير|رواب|مشروب|مانجو|برتقال|جوافة|تفاح|حليب|لبن|زبادي|ماء|مياه|بيبسي|كوكاكولا|ميرندا|سفن|ردبول|جوي|نسكافيه|قهوة)/.test(combined)) {
    return "drink_juice";
  }
  return "cooking_food";
}

function normalizeArabicV116(str: string): string {
  return String(str || "")
    .toLowerCase()
    .replace(/[أإآ]/g, "ا")
    .replace(/ة/g, "ه")
    .replace(/ى/g, "ي")
    .replace(/[؟?!.,،]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function findMatchingRecipeV116(userMsg: string, recipesList?: AiRecipeV114[]): AiRecipeV114 | null {
  const list = Array.isArray(recipesList) ? recipesList : (studioConfigV114.recipes || []);
  if (list.length === 0) return null;
  const normUser = normalizeArabicV116(userMsg);
  if (!normUser) return null;

  const stopWords = ["اريد", "ابغي", "اشتي", "هل", "عندكم", "ممكن", "كيف", "اسوي", "طريقه", "عمل", "وصفه", "حلو", "لذيذ", "سريع", "في", "من", "مع", "على", "عن"];

  for (const rec of list) {
    const normTitle = normalizeArabicV116(rec.title || "");
    const normKw = normalizeArabicV116(rec.keywords || "");
    if (normTitle && (normUser.includes(normTitle) || normTitle.includes(normUser))) return rec;
    if (normKw && (normUser.includes(normKw) || normKw.includes(normUser))) return rec;

    const kwParts = String(rec.keywords || "")
      .split(/[،,]+/)
      .map(s => normalizeArabicV116(s))
      .filter(s => s.length >= 3);
    if (kwParts.some(k => normUser.includes(k) || k.includes(normUser))) return rec;

    const combinedTarget = normTitle + " " + normKw;
    const userWords = normUser.split(" ").filter(w => w.length >= 3 && !stopWords.includes(w));
    const matchedWords = userWords.filter(w => combinedTarget.includes(w));
    if (matchedWords.length >= 2) return rec;
    if (matchedWords.length >= 1 && (normUser.includes("حلي") || normUser.includes("وصفه")) && (combinedTarget.includes("حلي") || combinedTarget.includes("بسكويت") || combinedTarget.includes("شوكولاته") || combinedTarget.includes("شكلاته"))) {
      return rec;
    }
  }
  return null;
}

export function buildSmartProductModalDataV112(productName: string, price: number, unit: string, categoryName = "", customTopic = "", productId?: any) {
  tokenStatsV114.zeroTokenMessages++;
  tokenStatsV114.estimatedTokensSaved += 2800;

  const cleanName = cleanProductNameV112(productName) || productName;
  const customAi = getProductCustomAiInfoV112(productId, cleanName);
  const kind = classifyProductKindV112(cleanName, categoryName, customAi);
  const priceStr = price > 0 ? price.toLocaleString("en-US") + " ريال" : "";

  const matchedRecipe = findMatchingRecipeV116(cleanName);

  if (customAi && !customTopic) {
    const chips =
      kind === "chocolate_snack"
        ? ["🔥 السعرات والقيمة الغذائية", "ℹ️ معلومات المنتج", "☕ مع إيش يُقدم؟"]
        : kind === "biscuit_dessert"
        ? ["🍰 فكرة حلى به", "🔥 السعرات الحرارية", "☕ مع الشاي والحليب"]
        : ["ℹ️ معلومات المنتج", "🔥 القيمة الغذائية"];
    let content = "✨ معلومات «" + cleanName + "»" + (priceStr ? " (" + priceStr + ")" : "") + ":\n" + customAi;
    if (matchedRecipe) {
      content += "\n\n🍰 وصفة مقترحة («" + matchedRecipe.title + "»):\n" + matchedRecipe.steps;
    }
    return {
      modalTitle: "✨ معلومات المنتج: " + cleanName,
      chips,
      content,
      kind,
      recipe: matchedRecipe || null
    };
  }

  const customNoteBlock = customAi ? "\n💡 معلومة إضافية: " + customAi : "";
  const recipeBlock = matchedRecipe ? "\n\n🍰 وصفة «" + matchedRecipe.title + "»:\n" + matchedRecipe.steps : "";

  if (kind === "chocolate_snack") {
    const chips = [
      "🔥 السعرات والقيمة الغذائية",
      "ℹ️ معلومات ومميزات المنتج",
      "☕ مع إيش يؤكل أو يُقدم؟",
      "🍫 سناك خفيف ومشابه"
    ];
    let text = "";
    if (customTopic && customTopic.includes("سعرات")) {
      text =
        "🔥 القيمة الغذائية والسعرات الحرارية لـ «" + cleanName + "»:\n" +
        "• السعرات التقريبية: حوالي 110 إلى 150 سعرة حرارية للحصة الواحدة تمنح طاقة سريعة.\n" +
        "• جاهز للأكل مباشرة كسناك لذيذ بدون أي تحضير." +
        customNoteBlock;
    } else {
      text =
        "✨ معلومات «" + cleanName + "»" + (priceStr ? " (السعر: " + priceStr + ")" : "") + ":\n" +
        "• منتج جاهز للأكل مباشرة بطعم لذيذ، لا يحتاج إلى أي طبخ أو تحضير.\n" +
        "• السعرات الحرارية التقريبية: حوالي 120 – 150 سعرة حرارية.\n" +
        "• مثالي مع فنجان قهوة، شاي، أو كسناك خفيف في أي وقت." +
        customNoteBlock +
        recipeBlock;
    }
    return {
      modalTitle: "✨ معلومات وقيمة غذائية: " + cleanName,
      chips,
      content: text,
      kind,
      recipe: matchedRecipe || null
    };
  }

  if (kind === "biscuit_dessert") {
    const chips = [
      "🍰 فكرة حلى بارد وسريع به",
      "🔥 السعرات والقيمة الغذائية",
      "☕ مع الشاي والحليب",
      "ℹ️ معلومات عن المنتج"
    ];
    const text =
      "✨ معلومات وأفكار «" + cleanName + "»" + (priceStr ? " (السعر: " + priceStr + ")" : "") + ":\n" +
      "• يصلح للتقديم مع الشاي والحليب، أو لعمل حلى بارد سريع بطبقات القشطة والشوكولاتة.\n" +
      "• السعرات الحرارية التقريبية: حوالي 25 – 35 سعرة حرارية للحبة الواحدة." +
      customNoteBlock +
      recipeBlock;
    return {
      modalTitle: "✨ معلومات وأفكار حلى: " + cleanName,
      chips,
      content: text,
      kind,
      recipe: matchedRecipe || null
    };
  }

  if (kind === "drink_juice") {
    const chips = [
      "🔥 السعرات والقيمة الغذائية",
      "ℹ️ معلومات عن المشروب",
      "🧊 أفضل طريقة تقديم بارد"
    ];
    const text =
      "✨ معلومات «" + cleanName + "»" + (priceStr ? " (السعر: " + priceStr + ")" : "") + ":\n" +
      "• السعرات التقريبية: حوالي 90 – 130 سعرة حرارية للعبوة.\n" +
      "• يُقدم بارداً للانتعاش، ومناسب بجانب البسكويت أو السناك الخفيف." +
      customNoteBlock +
      recipeBlock;
    return {
      modalTitle: "✨ معلومات وقيمة غذائية: " + cleanName,
      chips,
      content: text,
      kind,
      recipe: matchedRecipe || null
    };
  }

  if (kind === "non_food") {
    const chips = ["ℹ️ مواصفات المنتج", "📦 التوفر والخيارات"];
    const text =
      "✨ معلومات «" + cleanName + "»" + (priceStr ? " (السعر: " + priceStr + ")" : "") + ":\n" +
      "• متوفر في متجر أورجنال، يمكنك اختيار الكمية أو الخيار المطلوب وإضافته للسلة." +
      customNoteBlock;
    return {
      modalTitle: "✨ معلومات المنتج: " + cleanName,
      chips,
      content: text,
      kind,
      recipe: null
    };
  }

  const chips = [
    "🍳 استخداماته في المطبخ",
    "🔥 القيمة الغذائية",
    "💡 نصيحة حفظ وجودة"
  ];
  const text =
    "✨ معلومات «" + cleanName + "»" + (priceStr ? " (السعر: " + priceStr + ")" : "") + ":\n" +
    "• مكون غذائي ممتاز لتحضير الوجبات اليومية بجودة عالية." +
    customNoteBlock +
    recipeBlock;
  return {
    modalTitle: "✨ استخدامات ومعلومات: " + cleanName,
    chips,
    content: text,
    kind,
    recipe: matchedRecipe || null
  };
}

export interface IngredientTableRowV126 {
  name: string;
  amount: string;
  available: boolean;
  price?: number;
  productId?: number;
  unit?: string;
}

interface ChefRecipeVariantV126 {
  title: string;
  prepTime: string;
  steps: string[];
  ingredients: { name: string; amount: string; searchTerms: string[] }[];
}

interface ChefDishEntryV126 {
  id: string;
  keywords: RegExp;
  variants: ChefRecipeVariantV126[];
}

const sessionMemoryMapV126 = new Map<string, { lastDishId: string; variantIdx: number; updatedAt: number }>();

const MULTI_METHOD_CHEF_DISHES_V126: ChefDishEntryV126[] = [
  {
    id: "indomie",
    keywords: /(اندومي|إندومي|نودلز|شعيريه|شعيرية|رامين)/,
    variants: [
      {
        title: "إندومي الشيف الملكي المحموس بالخضار والصلصة",
        prepTime: "7 دقائق",
        steps: [
          "اسلق الإندومي في ماء مغلي لمدة دقيقتين فقط (نصف استواء) ثم صفّها واحتفظ بربع كوب من ماء السلق.",
          "في مقلاة على النار، سخّن ملعقة زيت مع فص ثوم مهروس وبصل أخضر وفلفل رومي مفروم وقلّبها دقيقتين.",
          "أضف ملعقة معجون طماطم (صلصة) وبهارات الإندومي وربع كوب ماء السلق واتركها تتسبك ثواني.",
          "أضف الإندومي المصفاة وقلّبها على نار عالية لمدة دقيقة حتى تتشرب الصوص بالكامل، وقدمها ساخنة!"
        ],
        ingredients: [
          { name: "إندومي", amount: "2 كيس", searchTerms: ["اندومي", "شعيريه"] },
          { name: "معجون طماطم (صلصة)", amount: "1 ملعقة كبيرة", searchTerms: ["صلصه", "معجون طماطم", "طماطم"] },
          { name: "زيت نباتي", amount: "1 ملعقة كبيرة", searchTerms: ["زيت"] },
          { name: "بصل أخضر وفلفل رومي طازج", amount: "1 حبة مفرومة", searchTerms: ["بصل", "فلفل رومي", "خضار"] }
        ]
      },
      {
        title: "إندومي كريمي بالجبن السائل على الطريقة الكورية السريعة",
        prepTime: "5 دقائق",
        steps: [
          "اسلق الإندومي في كمية قليلة من الماء لمدة 3 دقائق حتى تنضج مع بقاء قليل جداً من الماء.",
          "خفّض النار، وأضف ملعقتين كبيرتين من الجبن السائل وربع كوب حليب سائل.",
          "أضف بهارات الإندومي مع رشة فلفل أو شطة، وقلّبها جيداً حتى تذوب الجبنة وتتحول لصوص كريمي غني يغلف الإندومي بالكامل!"
        ],
        ingredients: [
          { name: "إندومي", amount: "2 كيس", searchTerms: ["اندومي", "شعيريه"] },
          { name: "جبن سائل أو مثلثات", amount: "2 ملعقة كبيرة", searchTerms: ["جبن", "جبنه"] },
          { name: "حليب سائل", amount: "ربع كوب", searchTerms: ["حليب"] },
          { name: "شطة أو فلفل حار", amount: "حسب الرغبة", searchTerms: ["شطه", "فلفل"] }
        ]
      },
      {
        title: "إندومي مقرمش بالليمون والكمون (طريقة مبتكرة ولذيذة جداً)",
        prepTime: "6 دقائق",
        steps: [
          "خذ مقدار ربع كيس من الإندومي النيئة وكسّرها ناعماً وحمّصها في ملعقة زيت حتى تصبح ذهبية ومقرمشة ثم ارفعها جانباً.",
          "اسلق باقي الإندومي لمدة 3 دقائق وصفّها، ثم اخلطها في المقلاة مع عصير ليمون طازج، رشة كمون، وبهارات الإندومي.",
          "اسكبها في طبق التقديم، وانثر فوقها الإندومي المحمصة المقرمشة لتعطيك قرمشة رهيبة مع كل لقمة!"
        ],
        ingredients: [
          { name: "إندومي ليمون أو خضار", amount: "2 كيس", searchTerms: ["اندومي"] },
          { name: "كمون مطحون", amount: "نصف ملعقة صغيرة", searchTerms: ["كمون"] },
          { name: "زيت للتحميص", amount: "1 ملعقة كبيرة", searchTerms: ["زيت"] },
          { name: "ليمون طازج", amount: "1 حبة", searchTerms: ["ليمون"] }
        ]
      }
    ]
  },
  {
    id: "kabsa",
    keywords: /(كبسه|كبسة|مندي|مضغوط|زربيان|رز بالدجاج|ارز بالدجاج)/,
    variants: [
      {
        title: "كبسة الدجاج الأصلية المفلفلة خطوة بخطوة",
        prepTime: "45 دقيقة",
        steps: [
          "اغسل الأرز البسمتي وانقعه في ماء دافئ لمدة 20 دقيقة ثم صفّه.",
          "في قدر، شوّح البصل المفروم في الزيت حتى يصبح ذهبياً، ثم أضف الثوم، الطماطم، معجون الطماطم، والبهارات المشكلة والكمون.",
          "أضف الدجاج وقلّبه مع الكشنة 5 دقائق، ثم أضف الماء المغلي واتركه يغلي لمدة 25 دقيقة حتى ينضج الدجاج.",
          "أضف الأرز المصفى فوق المرق، وعندما يتشرب الماء هدّئ النار تماماً وغطّ القدر 15 دقيقة."
        ],
        ingredients: [
          { name: "أرز بسمتي", amount: "2 كوب", searchTerms: ["ارز", "رز"] },
          { name: "معجون طماطم (صلصة)", amount: "2 ملعقة كبيرة", searchTerms: ["صلصه", "معجون طماطم"] },
          { name: "زيت طبخ", amount: "3 ملاعق كبيرة", searchTerms: ["زيت"] },
          { name: "بهارات كبسة وكمون", amount: "1 ملعقة كبيرة", searchTerms: ["بهارات", "كمون", "بسباس"] },
          { name: "دجاج طازج أو مبرد", amount: "1 حبة مقطعة", searchTerms: ["دجاج"] },
          { name: "بصل وطماطم طازجة", amount: "2 حبة", searchTerms: ["بصل", "طماطم"] }
        ]
      },
      {
        title: "مضغوط الدجاج السريع في قدر الضغط (نكهة المطاعم)",
        prepTime: "25 دقيقة",
        steps: [
          "في قدر الضغط، حمّر البصل مع الزيت والبهارات الصحيحة حتى تفوح رائحتها.",
          "أضف الدجاج وقلّبه حتى يتغير لونه، ثم أضف الطماطم المفرومة وملعقة معجون طماطم والكمون.",
          "اسكب الماء المغلي وأغلق قدر الضغط لمدة 12 دقيقة فقط، ثم افتحه وأضف الأرز المغسول وأغلق القدر 10 دقائق على نار هادئة."
        ],
        ingredients: [
          { name: "أرز بسمتي", amount: "2 كوب", searchTerms: ["ارز", "رز"] },
          { name: "معجون طماطم", amount: "1 ملعقة كبيرة", searchTerms: ["صلصه", "معجون طماطم"] },
          { name: "كمون وبهارات", amount: "1 ملعقة كبيرة", searchTerms: ["كمون", "بهارات"] },
          { name: "دجاج", amount: "1 حبة", searchTerms: ["دجاج"] }
        ]
      }
    ]
  },
  {
    id: "pasta",
    keywords: /(مكرونه|مكرونة|معكرونه|باستا|اسباجتي|بشاميل)/,
    variants: [
      {
        title: "مكرونة بالصلصة الحمراء والجبن السريع",
        prepTime: "20 دقيقة",
        steps: [
          "اسلق المكرونة في ماء مغلي مملح مع ملعقة زيت لمدة 8 دقائق ثم صفّها.",
          "في مقلاة عميقة، شوّح البصل والثوم المفروم في ملعقتين زيت، ثم أضف معجون الطماطم والطماطم المعصورة.",
          "تبّل الصلصة بالملح والكمون والفلفل، واتركها تتسبك 7 دقائق على نار هادئة.",
          "أضف المكرونة المسلوقة إلى الصلصة وقلّبها دقيقتين على النار، وقدمها مع رشة جبن على الوجه!"
        ],
        ingredients: [
          { name: "مكرونة", amount: "1 كيس (400 جرام)", searchTerms: ["مكرونه", "معكرونه", "باستا"] },
          { name: "معجون طماطم (صلصة)", amount: "2 ملعقة كبيرة", searchTerms: ["صلصه", "معجون طماطم"] },
          { name: "زيت نباتي", amount: "2 ملعقة كبيرة", searchTerms: ["زيت"] },
          { name: "جبن مبشور أو سائل", amount: "نصف كوب", searchTerms: ["جبن", "جبنه"] }
        ]
      },
      {
        title: "باستا كريمية سريعة (بينك صوص) بدون كريمة طبخ",
        prepTime: "15 دقيقة",
        steps: [
          "اسلق المكرونة وصفّها مع الاحتفاظ بنصف كوب من ماء السلق.",
          "في القدر، اخلط كوب حليب سائل مع ملعقتين كبيرتين جبن سائل وملعقة معجون طماطم على نار هادئة.",
          "أضف رشة كمون وفلفل أسود، ثم أضف المكرونة وماء السلق وقلّبها حتى يثقل الصوص الوردي الكريمي!"
        ],
        ingredients: [
          { name: "مكرونة", amount: "1 كيس", searchTerms: ["مكرونه", "باستا"] },
          { name: "حليب سائل", amount: "1 كوب", searchTerms: ["حليب"] },
          { name: "جبن سائل", amount: "2 ملعقة كبيرة", searchTerms: ["جبن"] },
          { name: "معجون طماطم", amount: "1 ملعقة كبيرة", searchTerms: ["صلصه", "طماطم"] }
        ]
      }
    ]
  },
  {
    id: "saltah",
    keywords: /(سلته|سلتة|فحسه|فحسة)/,
    variants: [
      {
        title: "السلتة اليمنية الصنعانية الأصلية بالحلبة",
        prepTime: "30 دقيقة",
        steps: [
          "انقع الحلبة المطحونة في الماء البارد لمدة ساعة، ثم صفّ الماء الزائد واخفقها جيداً مع الكراث والكزبرة والفلفل الأخضر حتى تصبح بيضاء هشة.",
          "في المقلى الحجري (المدرة)، شوّح البصل والثوم والطماطم مع معجون الطماطم والكمون.",
          "أضف المرق واللحم المفروم أو التونة والبطاطس المسلوقة المهروسة واتركها تغلي بقوة.",
          "وزّع رغوة الحلبة المخفوقة على وجه المقلى الساخن وقدمها فوراً مع الخبز الحار!"
        ],
        ingredients: [
          { name: "حلبة مطحونة", amount: "3 ملاعق كبيرة", searchTerms: ["حلبه", "بهارات"] },
          { name: "معجون طماطم", amount: "2 ملعقة كبيرة", searchTerms: ["صلصه", "معجون طماطم"] },
          { name: "كمون بلدي", amount: "1 ملعقة صغيرة", searchTerms: ["كمون"] },
          { name: "تونة أو لحم مفروم", amount: "1 علبة / 250 جرام", searchTerms: ["تونه", "لحم"] },
          { name: "بطاطس وكراث وبصل", amount: "2 حبة", searchTerms: ["بطاطس", "بصل", "كراث"] }
        ]
      }
    ]
  },
  {
    id: "shakshuka",
    keywords: /(شكشوكه|شكشوكة|بيض بالطماطم|فطور سريع|عشاء سريع)/,
    variants: [
      {
        title: "شكشوكة عدنية محموسة بالجبن",
        prepTime: "10 دقائق",
        steps: [
          "شوّح البصل المفروم والفلفل في الزيت حتى يذبل.",
          "أضف الطماطم المفرومة ناعماً وملعقة صغيرة معجون طماطم ورشة كمون وملح، واتركها 4 دقائق حتى تذوب الطماطم.",
          "أضف البيض وحرّكه بهدوء على نار هادئة حتى يستوي نصف استواء، ثم أضف ملعقة جبن سائل على الوجه!"
        ],
        ingredients: [
          { name: "بيض طازج", amount: "4 حبات", searchTerms: ["بيض"] },
          { name: "معجون طماطم", amount: "1 ملعقة صغيرة", searchTerms: ["صلصه", "معجون طماطم"] },
          { name: "جبن سائل أو مثلثات", amount: "1 ملعقة كبيرة", searchTerms: ["جبن"] },
          { name: "كمون مطحون", amount: "نصف ملعقة صغيرة", searchTerms: ["كمون"] },
          { name: "زيت طبخ", amount: "2 ملعقة كبيرة", searchTerms: ["زيت"] }
        ]
      }
    ]
  },
  {
    id: "basbousa",
    keywords: /(بسبوسه|بسبوسة|كيكه|كيكة|كنافه|كنافة|لقيمات)/,
    variants: [
      {
        title: "حلى البسبوسة الذهبية المحشية بالقشطة",
        prepTime: "30 دقيقة",
        steps: [
          "اخلط السميد مع السكر، الحليب، البيكنج باودر، والزيت، وقلّب الخليط جيداً.",
          "اسكب نصف الخليط في صينية مدهونة، ووزع طبقة من القشطة في المنتصف، ثم غطّها بالنصف المتبقي.",
          "اخبزها في فرن متوسط الحرارة (180 درجة) لمدة 25 دقيقة حتى تتحمر، واسقها بالشيرة الدافئة فور خروجها!"
        ],
        ingredients: [
          { name: "حليب", amount: "1 كوب", searchTerms: ["حليب"] },
          { name: "زيت نباتي", amount: "نصف كوب", searchTerms: ["زيت"] },
          { name: "قشطة", amount: "2 علبة", searchTerms: ["قشطه", "قشطة"] },
          { name: "سميد ناعم وسكر", amount: "2 كوب", searchTerms: ["سميد", "سكر"] }
        ]
      }
    ]
  },
  {
    id: "biscuit_sweet",
    keywords: /(حلا|حلى|وصفه حلوه|وصفة حلوة|حلا بارد|حلى بارد|تحليه|تحلية|بسكويت بالشوكولاته)/,
    variants: [
      {
        title: "حلى طبقات البسكويت البارد بالشوكولاتة والحليب",
        prepTime: "15 دقيقة",
        steps: [
          "اطحن نصف كمية البسكويت خشناً، وغمّس النصف الآخر سريعاً في الحليب الدافئ ورتبه كطبقة أولى في الكاسات.",
          "ذوّب الشوكولاتة مع الحليب على نار هادئة حتى تصبح صوصاً ناعماً وكثيفاً.",
          "اسكب طبقة من صوص الشوكولاتة فوق البسكويت، ثم رش البسكويت المطحون على الوجه.",
          "ضعها في الثلاجة لمدة 20 دقيقة لتبرد وتتماسك، وقدمها باردة مع القهوة!"
        ],
        ingredients: [
          { name: "بسكويت (ماري أو أبو ولد أو ديما)", amount: "2 باكت", searchTerms: ["بسكويت", "ابو ولد", "ماري", "ديما"] },
          { name: "شوكولاتة", amount: "2 حبة", searchTerms: ["شوكولاته", "شوكولاتة", "سعيد", "بريك"] },
          { name: "حليب", amount: "1 عبوة", searchTerms: ["حليب", "الربيع", "المراعي"] }
        ]
      },
      {
        title: "كرات الترافل الفاخرة بالبسكويت والشوكولاتة (بدون فرن)",
        prepTime: "10 دقائق",
        steps: [
          "اطحن البسكويت ناعماً جداً في وعاء عميق.",
          "ذوّب الشوكولاتة مع ربع كوب حليب دافئ، واسكبها فوق البسكويت المطحون واعجنها حتى تتكون عجينة متماسكة.",
          "شكّلها على هيئة كرات صغيرة متساوية، ودحرجها في فتات البسكويت، وضعها في الثلاجة 15 دقيقة وقدمها مع القهوة!"
        ],
        ingredients: [
          { name: "بسكويت", amount: "2 باكت", searchTerms: ["بسكويت", "ابو ولد", "ديما"] },
          { name: "شوكولاتة بالحليب", amount: "2 حبة", searchTerms: ["شوكولاته", "شوكولاتة", "سعيد"] },
          { name: "حليب سائل", amount: "1 عبوة", searchTerms: ["حليب"] }
        ]
      }
    ]
  }
];

const FUNNY_CLEAN_JOKES_V126: string[] = [
  "😄 نكتة خفيفة على السريع:\nواحد راح للبقالة قال لصاحب المحل: عندك سكر؟ قاله: أيوه! قاله: الله يشفيك! 😂\nبشرني يا غالي، إيش نجهز لك اليوم من مقاضي أو وصفات؟",
  "😄 خذ هذي النكتة يا غالي:\nواحد سأل صاحبه: ليش تحط التلفون في الثلاجة؟ قاله: عشان لا تذوب الشوكولاتة اللي في الصورة! 😂🍫\nقول لي، جاي على بالك حلى بارد ولا طبخة سريعة اليوم؟",
  "😄 ابتسم يا غالي:\nالأم تسأل ولدها: لو أعطيتك تفاحتين وأعطيت أخوك تفاحتين، كم يصير معكم؟ قال: 4 تفاحات عندي وتفاحتين في بطني! 😂🍎\nآمرني يا غالي، إيش بخاطرك نطبخ أو نطلب اليوم؟"
];

function buildVariantPayloadV126(variant: ChefRecipeVariantV126, allProducts: any[], isAlternative: boolean) {
  const tableRows: IngredientTableRowV126[] = [];
  const availableItems: any[] = [];
  const missingNames: string[] = [];

  for (const ing of variant.ingredients) {
    let foundProd: any = null;
    for (const term of ing.searchTerms) {
      const normTerm = normalizeArabicV116(term);
      foundProd = allProducts.find(p => normalizeArabicV116(cleanProductNameV112(p.name)).includes(normTerm));
      if (foundProd) break;
    }
    if (foundProd) {
      const cleanName = cleanProductNameV112(foundProd.name);
      const pPrice = Math.round(Number(foundProd.price || 100));
      tableRows.push({
        name: cleanName,
        amount: ing.amount,
        available: true,
        price: pPrice,
        productId: foundProd.id,
        unit: foundProd.unit || "حبة"
      });
      availableItems.push({
        productId: foundProd.id,
        id: foundProd.id,
        name: cleanName,
        price: pPrice,
        unit: foundProd.unit || "حبة",
        quantity: 1,
        url: "/?search=" + encodeURIComponent(cleanName)
      });
    } else {
      tableRows.push({
        name: ing.name,
        amount: ing.amount,
        available: false
      });
      missingNames.push(ing.name + " (" + ing.amount + ")");
    }
  }

  const stepsFormatted = variant.steps.map((s, idx) => (idx + 1) + ". " + s).join("\n");
  const introLine = isAlternative
    ? "✨ ولا يهمك يا غالي! جبت لك طريقة ثانية ألذ وأحلى لتحضير «" + variant.title + "» (⏱️ " + variant.prepTime + "):"
    : " أبشر يا غالي! إليك الطريقة الاحترافية لتحضير «" + variant.title + "» (⏱️ " + variant.prepTime + "):";

  const replyText =
    introLine + "\n\n" +
    "📋 خطوات التحضير:\n" +
    stepsFormatted + "\n\n" +
    "📊 جدول المقادير وحالة التوفر بالأسفل:";

  return {
    reply: replyText,
    recipeTitle: variant.title,
    recipeCard: {
      title: variant.title,
      imageUrl: "",
      steps: stepsFormatted,
      ingredients: availableItems
    },
    ingredientsTable: tableRows,
    missingItemsText: missingNames.join(" + "),
    suggestedItems: availableItems,
    quickActions: [],
    canContactStore: false,
    matchedCustom: true,
    matchedOverride: true
  };
}

export async function handleSmartAiChatV112(input: {
  message: string;
  prevMessage?: string;
  sessionId?: string;
  customerName?: string;
  customerPhone?: string;
  history?: Array<{ role: string; content: string }>;
}) {
  await ensureStudioTableV114();
  const userMsg = String(input.message || "").trim();
  const prevMsg = String(input.prevMessage || "").trim();
  const sessionId = String(input.sessionId || "guest");
  const normMsg = normalizeArabicV116(userMsg);

  if (!userMsg) {
    return { ok: true, passThrough: true };
  }

  tokenStatsV114.zeroTokenMessages++;
  tokenStatsV114.estimatedTokensSaved += 4200;

  if (/(اباحي|إباحي|مايا خليفه|مايا خليفة|جنس|سكس|porn|xxx)/i.test(normMsg)) {
    return {
      reply: "حياك الله يا غالي، أنا مساعد متجر أورجنال، يسعدني دائماً خدمتك في كل ما يخص المنتجات والوصفات والمعلومات الغذائية. كيف أقدر أخدمك اليوم؟",
      suggestedItems: [],
      quickActions: [],
      canContactStore: false,
      matchedCustom: true,
      matchedOverride: true
    };
  }

  const allProducts = await getCatalogCachedV114();

  // 0. Context-Aware Follow-up Detection ("يااخي اريد طريقة افضل", "طريقة ثانية", "غير هذي")
  const isFollowUpBetterMethod = /(طريقه افضل|طريقة افضل|طريقه احسن|طريقه ثانيه|طريقة ثانية|طريقه اخرى|وصفه افضل|وصفه ثانيه|غير هذي|غير هذه|عدله|عدلها|بشكل افضل|شي افضل|شي احسن|احلى من كذا)/.test(normMsg);
  if (isFollowUpBetterMethod) {
    let mem = sessionMemoryMapV126.get(sessionId);
    let targetDish: ChefDishEntryV126 | undefined;
    if (mem) {
      targetDish = MULTI_METHOD_CHEF_DISHES_V126.find(d => d.id === mem!.lastDishId);
    }
    if (!targetDish && prevMsg) {
      const normPrev = normalizeArabicV116(prevMsg);
      targetDish = MULTI_METHOD_CHEF_DISHES_V126.find(d => d.keywords.test(normPrev));
    }
    if (!targetDish) {
      targetDish = MULTI_METHOD_CHEF_DISHES_V126[0];
    }
    const nextIdx = mem ? (mem.variantIdx + 1) % targetDish.variants.length : 1 % targetDish.variants.length;
    sessionMemoryMapV126.set(sessionId, {
      lastDishId: targetDish.id,
      variantIdx: nextIdx,
      updatedAt: Date.now()
    });
    return buildVariantPayloadV126(targetDish.variants[nextIdx], allProducts, true);
  }

  // 1. Confirming store contact
  const isConfirmingStoreContact =
    /(نعم|ايوه|أيوة|ايه|أيه|كلمهم|كلم المتجر|كلّم المتجر|تواصل معهم|ارسل لهم|أرسل لهم|ياريت|يا ريت|اكيد|أكيد|تواصل لك مع المتجر)/.test(userMsg) &&
    (userMsg.includes("المتجر") ||
      (Array.isArray(input.history) &&
        input.history.some(h => String(h.content || "").includes("أكلم المتجر") || String(h.content || "").includes("أتواصل لك"))));

  if (isConfirmingStoreContact) {
    const prevUserMsgs = (input.history || []).filter(h => h.role === "user").map(h => h.content);
    const requestedTopic = prevUserMsgs.length > 0 ? prevUserMsgs[prevUserMsgs.length - 1] : (prevMsg || userMsg);
    const reqRecord: CustomerAiRequestV114 = {
      id: "req_" + Date.now() + "_" + Math.random().toString(36).slice(2, 6),
      sessionId,
      customerName: String(input.customerName || "زبون المتجر"),
      customerPhone: String(input.customerPhone || ""),
      requestedItem: String(requestedTopic).slice(0, 140),
      customerMessage: userMsg,
      status: "pending",
      managerReply: "",
      createdAt: Date.now()
    };
    customerRequestsV114.unshift(reqRecord);
    if (customerRequestsV114.length > 200) customerRequestsV114 = customerRequestsV114.slice(0, 200);
    await saveStudioKeyV114("customer_requests", customerRequestsV114);

    return {
      reply: "أبشر من عيوني يا غالي! 📲 أرسلت إشعار فوري الآن لهاتف مدير المتجر بطلبك («" + requestedTopic + "»).\nأول ما يرد المدير سيظهر رده هنا أمامك في المحادثة مباشرةً!",
      suggestedItems: [],
      quickActions: [],
      canContactStore: false,
      requestSent: true,
      requestObj: reqRecord,
      matchedCustom: true,
      matchedOverride: true
    };
  }

  // 2. Check Manager's Custom Rules (القسم 2: قاموس الردود)
  for (const rule of studioConfigV114.rules || []) {
    const trig = normalizeArabicV116(rule.trigger || "");
    if (trig && normMsg.includes(trig)) {
      const items: any[] = [];
      if (rule.linkedProductName) {
        const cleanRuleProd = cleanProductNameV112(rule.linkedProductName);
        const foundP = allProducts.find(p => cleanProductNameV112(p.name) === cleanRuleProd);
        if (foundP) {
          items.push({
            productId: foundP.id,
            id: foundP.id,
            name: cleanProductNameV112(foundP.name),
            price: Math.round(Number(foundP.price || 0)),
            unit: foundP.unit || "حبة",
            quantity: 1,
            url: rule.linkedProductUrl || ("/?search=" + encodeURIComponent(cleanProductNameV112(foundP.name)))
          });
        }
      }
      let replyTxt = String(rule.response || "").replace(/\(\s*رقم\s*\d+\s*\)/g, "");
      if (rule.linkedProductUrl && !replyTxt.includes(rule.linkedProductUrl)) {
        replyTxt += "\n🔗 رابط المنتج: " + rule.linkedProductUrl;
      }
      return {
        reply: replyTxt,
        suggestedItems: items,
        quickActions: [],
        canContactStore: false,
        matchedCustom: true,
        matchedOverride: true
      };
    }
  }

  // 3. Check Manager's Visual Recipes (القسم 4: الوصفات المصورة والمنتجات)
  const matchedRec = findMatchingRecipeV116(userMsg);
  if (matchedRec) {
    const recItems: any[] = [];
    const tableRows: IngredientTableRowV126[] = [];
    const missingNames: string[] = [];

    for (const ing of matchedRec.ingredients || []) {
      const cleanIng = cleanProductNameV112(ing.name);
      let foundP = allProducts.find(p => cleanProductNameV112(p.name) === cleanIng);
      if (!foundP) {
        foundP = allProducts.find(p => {
          const pn = cleanProductNameV112(p.name);
          return pn.length >= 5 && cleanIng.length >= 5 && (pn.includes(cleanIng) || (cleanIng.includes(pn) && pn.length >= cleanIng.length * 0.7));
        });
      }
      if (foundP) {
        const cName = cleanProductNameV112(foundP.name);
        const pPrice = Math.round(Number(foundP.price || 0));
        recItems.push({
          productId: foundP.id,
          id: foundP.id,
          name: cName,
          price: pPrice,
          unit: foundP.unit || "حبة",
          quantity: 1,
          imageUrl: foundP.imageUrl || "",
          url: ing.url || ("/?search=" + encodeURIComponent(cName))
        });
        tableRows.push({
          name: cName,
          amount: "1 " + (foundP.unit || "حبة"),
          available: true,
          price: pPrice,
          productId: foundP.id,
          unit: foundP.unit || "حبة"
        });
      } else if (ing.name) {
        tableRows.push({
          name: cleanIng || ing.name,
          amount: "حسب الوصفة",
          available: false
        });
        missingNames.push(cleanIng || ing.name);
      }
    }
    const recReply =
      "🍰 «" + matchedRec.title + "»\n\n" +
      "📋 طريقة التحضير والخطوات الكاملة:\n" +
      String(matchedRec.steps || "");

    return {
      reply: recReply,
      recipeTitle: matchedRec.title,
      recipeImage: matchedRec.imageUrl || "",
      recipeCard: {
        title: matchedRec.title,
        imageUrl: matchedRec.imageUrl || "",
        steps: matchedRec.steps,
        ingredients: recItems
      },
      ingredientsTable: tableRows,
      missingItemsText: missingNames.join(" + "),
      suggestedItems: recItems,
      quickActions: [],
      canContactStore: false,
      matchedCustom: true,
      matchedOverride: true
    };
  }

  // 4. Check Manager's Promoted Products (القسم 3: ترويج منتج برابطه)
  const activePromos = (studioConfigV114.promotedProducts || []).filter(p => p.active !== false && p.productName);
  const triggeredPromo = activePromos.find(p => {
    if (!p.triggerKeywords || !p.triggerKeywords.trim()) return false;
    return p.triggerKeywords.split(/[،,]+/).map(s => normalizeArabicV116(s)).filter(Boolean).some(k => normMsg.includes(k));
  });

  if (triggeredPromo) {
    const cleanPromoName = cleanProductNameV112(triggeredPromo.productName);
    const foundPromoProd = allProducts.find(p => cleanProductNameV112(p.name) === cleanPromoName) ||
      allProducts.find(p => cleanProductNameV112(p.name).includes(cleanPromoName));
    const pPrice = foundPromoProd ? Math.round(Number(foundPromoProd.price || 0)) : Number(triggeredPromo.productPrice || 0);
    const pUrl = triggeredPromo.productUrl || ("/?search=" + encodeURIComponent(triggeredPromo.productName));
    const promoReply =
      (triggeredPromo.promoBadge ? triggeredPromo.promoBadge + " — " : "⭐ ترشيح خاص لك: ") +
      "«" + triggeredPromo.productName + "»" + (pPrice > 0 ? " (بسعر " + pPrice.toLocaleString("en-US") + " ر.ي)" : "") + "\n" +
      (triggeredPromo.promoMessage || "");

    return {
      reply: promoReply.trim(),
      promotedCard: {
        name: triggeredPromo.productName,
        price: pPrice,
        url: pUrl,
        imageUrl: triggeredPromo.productImage || (foundPromoProd ? foundPromoProd.imageUrl : ""),
        badge: triggeredPromo.promoBadge || "⭐ عرض مميز",
        productId: foundPromoProd ? foundPromoProd.id : undefined
      },
      suggestedItems: foundPromoProd ? [{
        productId: foundPromoProd.id,
        id: foundPromoProd.id,
        name: cleanProductNameV112(foundPromoProd.name),
        price: pPrice,
        unit: foundPromoProd.unit || "حبة",
        quantity: 1
      }] : [],
      quickActions: [],
      canContactStore: false,
      matchedCustom: true,
      matchedOverride: true
    };
  }

  // 5. Jokes & Friendly Banter
  if (/(نكته|نكتة|ضحكني|فرفش|امزح|مزحه|مزحة)/.test(normMsg)) {
    const joke = FUNNY_CLEAN_JOKES_V126[Math.floor(Math.random() * FUNNY_CLEAN_JOKES_V126.length)];
    return {
      reply: joke,
      suggestedItems: [],
      quickActions: [],
      canContactStore: false,
      matchedCustom: true,
      matchedOverride: true
    };
  }

  // 6. Multi-Method Chef Encyclopedia (Indomie, Kabsa, Pasta, Saltah, Shakshuka, Basbousa, Biscuit Sweets)
  const matchedChefDish = MULTI_METHOD_CHEF_DISHES_V126.find(d => d.keywords.test(normMsg));
  if (matchedChefDish) {
    const prevMem = sessionMemoryMapV126.get(sessionId);
    const vIdx = (prevMem && prevMem.lastDishId === matchedChefDish.id)
      ? (prevMem.variantIdx + 1) % matchedChefDish.variants.length
      : 0;
    sessionMemoryMapV126.set(sessionId, {
      lastDishId: matchedChefDish.id,
      variantIdx: vIdx,
      updatedAt: Date.now()
    });
    return buildVariantPayloadV126(matchedChefDish.variants[vIdx], allProducts, vIdx > 0);
  }

  // 7. Specific Product Inquiry in Store
  const matchedProducts = allProducts.filter(p => {
    const pName = cleanProductNameV112(p.name);
    if (!pName || pName.length < 3) return false;
    if (userMsg.includes(pName)) return true;
    const words = pName.split(/\s+/).filter(w => w.length >= 4);
    return words.length > 0 && words.every(w => userMsg.includes(w));
  });

  if (matchedProducts.length > 0) {
    const primary = matchedProducts[0];
    const pName = cleanProductNameV112(primary.name);
    const pPrice = Math.round(Number(primary.price || 0));
    const customInfo = getProductCustomAiInfoV112(primary.id, pName);
    if (customInfo) {
      const modalInfo = buildSmartProductModalDataV112(pName, pPrice, primary.unit || "حبة", "", userMsg, primary.id);
      return {
        reply: modalInfo.content.replace(/\(\s*رقم\s*\d+\s*\)/g, ""),
        suggestedItems: [
          {
            productId: primary.id,
            id: primary.id,
            name: pName,
            price: pPrice,
            unit: primary.unit || "حبة",
            quantity: 1
          }
        ],
        quickActions: [],
        canContactStore: false,
        matchedCustom: true,
        matchedOverride: true
      };
    }
  }

  // 8. Custom Welcome Greeting if configured
  if (/^(سلام|السلام عليكم|هلا|اهلا|أهلا|مرحبا|كيفك|كيف حالك|اخبارك|أخبارك)$/i.test(userMsg)) {
    const welcomeInst = (studioConfigV114.instructions || []).find(i => i.active !== false && (i.category === "welcome" || i.category.includes("الترحيب")) && i.content && i.content.trim());
    if (welcomeInst) {
      return {
        reply: welcomeInst.content.trim(),
        suggestedItems: [],
        quickActions: [],
        canContactStore: false,
        matchedCustom: true,
        matchedOverride: true
      };
    }
  }

  // 9. Explicit Product Availability Request when item is NOT in store -> Show in 4-column table + 1-click Order Notes button!
  const asksAvailability = /(عندكم|معاكم|معكم|متوفر|تبيعون|احصل|القي|اشتي|ابغي|موجود)/.test(normMsg);
  const queryWords = userMsg
    .replace(/[؟?!.,،]/g, " ")
    .split(/\s+/)
    .map(w => w.trim())
    .filter(w => w.length >= 3 && !["عندكم", "اريد", "أريد", "ابغى", "أبغى", "اشتي", "أشتي", "موجود", "متوفر", "حبة", "باكيت", "كرتون", "سعر", "بكم", "كم", "هل", "في", "من", "على", "مع", "هذا", "هذه", "معاكم", "معكم"].includes(w));

  if (asksAvailability && matchedProducts.length === 0 && queryWords.length > 0) {
    const partialMatches = allProducts.filter(p => {
      const pName = cleanProductNameV112(p.name);
      return Number(p.price) > 5 && queryWords.some(w => pName.includes(w));
    }).slice(0, 3);

    if (partialMatches.length === 0) {
      const cleanWanted = queryWords.join(" ");
      const unavailInst = (studioConfigV114.instructions || []).find(i => i.active !== false && (i.category === "missing_item" || i.category.includes("عدم توفر")) && i.content && i.content.trim());
      const friendReply = unavailInst
        ? unavailInst.content.replace(/\{المنتج\}/g, cleanWanted)
        : "فهمتك يا غالي! أنت تطلب «" + cleanWanted + "».. حلو حلو! 👌\nحالياً هذا الصنف غير ظاهر في قائمة المتجر، لكن ولا يهمك! جهزته لك في الجدول بالأسفل كصنف قابل للطلب: اضغط على زر (📋 نسخ وإضافة تلقائياً في ملاحظة الطلب) ليُضاف مع طلبك، أو اضغط إرسال إشعار فوري لهاتف مدير المتجر وسيرد عليك فوراً!";

      return {
        reply: friendReply,
        recipeTitle: "طلب توفير: " + cleanWanted,
        ingredientsTable: [
          {
            name: cleanWanted,
            amount: "حسب الطلب",
            available: false
          }
        ],
        missingItemsText: cleanWanted,
        suggestedItems: [],
        quickActions: ["📲 نعم، كلّم المتجر إذا عندهم («" + cleanWanted + "»)"],
        canContactStore: true,
        requestedItemName: cleanWanted,
        matchedCustom: true,
        matchedOverride: true
      };
    }
  }

  // Otherwise pass through to the store's native AI assistant so it responds naturally without repeating a static phrase!
  return {
    ok: true,
    passThrough: true
  };
}

export function registerAiEngineV112(app: any) {
  app.use("/api/ai-v112", express.json({ limit: "50mb" }));
  app.use("/api/ai-studio", express.json({ limit: "50mb" }));

  ensureStudioTableV114().catch(() => {});

  const handleGetConfig = async (req: any, res: any) => {
    try {
      await ensureStudioTableV114();
      const isAdminPoll = req?.query?.admin === "1" || String(req?.headers?.referer || "").includes("/admin");
      const wantCatalog = req?.query?.includeCatalog === "1";
      const latestOrders = isAdminPoll ? await getLatestOrdersCachedV126() : [];
      let simpleCatalog: any[] = [];
      if (wantCatalog) {
        const catalog = await getCatalogCachedV114();
        simpleCatalog = catalog.map(p => ({
          id: p.id,
          name: cleanProductNameV112(p.name),
          price: Math.round(Number(p.price || 0)),
          unit: p.unit || "حبة",
          imageUrl: ""
        }));
      }
      res.json({
        ok: true,
        config: studioConfigV114,
        requests: isAdminPoll ? customerRequestsV114 : [],
        latestOrders,
        stats: tokenStatsV114,
        catalog: simpleCatalog
      });
    } catch (e: any) {
      res.status(500).json({ ok: false, error: String(e?.message || e) });
    }
  };

  app.get("/api/ai-v112/config", handleGetConfig);
  app.get("/api/ai-studio/config", handleGetConfig);
  app.get("/api/ai-studio/state", handleGetConfig);

  const handleSaveTraining = async (req: any, res: any) => {
    try {
      await ensureStudioTableV114();
      const body = req.body || {};
      const src = body.config && typeof body.config === "object" ? body.config : body;
      if (typeof src.generalSystemPrompt === "string") studioConfigV114.generalSystemPrompt = src.generalSystemPrompt.trim();
      if (Array.isArray(src.instructions)) studioConfigV114.instructions = src.instructions;
      if (Array.isArray(src.rules)) studioConfigV114.rules = src.rules;
      if (Array.isArray(src.promotedProducts)) studioConfigV114.promotedProducts = src.promotedProducts;
      if (Array.isArray(src.recipes)) studioConfigV114.recipes = src.recipes;
      if (src.productAiMap && typeof src.productAiMap === "object") studioConfigV114.productAiMap = src.productAiMap;
      replyCacheV114 = {};
      await saveStudioKeyV114("studio_config", studioConfigV114);
      res.json({ ok: true, config: studioConfigV114 });
    } catch (e: any) {
      res.status(500).json({ ok: false, error: String(e?.message || e) });
    }
  };

  app.post("/api/ai-v112/save-training", handleSaveTraining);
  app.post("/api/ai-studio/config", handleSaveTraining);
  app.post("/api/ai-studio/save-config", handleSaveTraining);

  app.post("/api/ai-v112/save-product-info", async (req: any, res: any) => {
    try {
      await ensureStudioTableV114();
      const { productId, productName, aiInfo } = req.body || {};
      if (!studioConfigV114.productAiMap) studioConfigV114.productAiMap = {};
      const cleanInfo = String(aiInfo || "").trim();
      if (productId !== undefined && productId !== null && String(productId).trim() !== "") {
        if (cleanInfo) studioConfigV114.productAiMap["id:" + String(productId).trim()] = cleanInfo;
        else delete studioConfigV114.productAiMap["id:" + String(productId).trim()];
      }
      const cName = cleanProductNameV112(String(productName || ""));
      if (cName) {
        if (cleanInfo) studioConfigV114.productAiMap["name:" + cName] = cleanInfo;
        else delete studioConfigV114.productAiMap["name:" + cName];
      }
      replyCacheV114 = {};
      await saveStudioKeyV114("studio_config", studioConfigV114);
      res.json({ ok: true, productAiMap: studioConfigV114.productAiMap });
    } catch (e: any) {
      res.status(500).json({ ok: false, error: String(e?.message || e) });
    }
  });

  app.post("/api/ai-v112/product-modal", async (req: any, res: any) => {
    try {
      await ensureStudioTableV114();
      const { productName, price, unit, categoryName, customTopic, productId } = req.body || {};
      const data = buildSmartProductModalDataV112(
        String(productName || ""),
        Number(price || 0),
        String(unit || "حبة"),
        String(categoryName || ""),
        String(customTopic || ""),
        productId
      );
      res.json({ ok: true, ...data });
    } catch (e: any) {
      res.status(500).json({ ok: false, error: String(e?.message || e) });
    }
  });

  const handleChatRoute = async (req: any, res: any) => {
    try {
      const result = await handleSmartAiChatV112(req.body || {});
      res.json({ ok: true, ...result });
    } catch (e: any) {
      res.status(500).json({ ok: false, error: String(e?.message || e) });
    }
  };

  app.post("/api/ai-v112/chat", handleChatRoute);
  app.post("/api/ai-studio/smart-chat", handleChatRoute);

  const handleRequestStoreRoute = async (req: any, res: any) => {
    try {
      await ensureStudioTableV114();
      const body = req.body || {};
      const reqRecord: CustomerAiRequestV114 = {
        id: "req_" + Date.now() + "_" + Math.random().toString(36).slice(2, 6),
        sessionId: String(body.sessionId || "guest"),
        customerName: String(body.customerName || "زبون المتجر"),
        customerPhone: String(body.customerPhone || ""),
        requestedItem: String(body.requestedItem || body.message || "طلب توفير منتج").slice(0, 160),
        customerMessage: String(body.customerMessage || body.userMessage || body.requestedItem || ""),
        status: "pending",
        managerReply: "",
        createdAt: Date.now()
      };
      customerRequestsV114.unshift(reqRecord);
      if (customerRequestsV114.length > 200) customerRequestsV114 = customerRequestsV114.slice(0, 200);
      await saveStudioKeyV114("customer_requests", customerRequestsV114);
      res.json({
        ok: true,
        requestObj: reqRecord,
        message: "تم إرسال طلبك وإشعار هاتف مدير المتجر بنجاح! سيصلك الرد هنا في المحادثة مباشرةً."
      });
    } catch (e: any) {
      res.status(500).json({ ok: false, error: String(e?.message || e) });
    }
  };

  app.post("/api/ai-v112/request-store", handleRequestStoreRoute);
  app.post("/api/ai-studio/request-item", handleRequestStoreRoute);

  app.post("/api/ai-v112/manager-reply", async (req: any, res: any) => {
    try {
      await ensureStudioTableV114();
      const { requestId, sessionId, replyText, attachedProductName, attachedProductUrl } = req.body || {};
      const cleanReply = String(replyText || "").trim();
      if (!cleanReply) {
        return res.status(400).json({ ok: false, error: "يرجى كتابة نص الرد" });
      }
      let target = customerRequestsV114.find(r => r.id === requestId);
      if (!target && sessionId) {
        target = customerRequestsV114.find(r => r.sessionId === sessionId);
      }
      const fullReply = cleanReply + (attachedProductUrl ? "\n🔗 رابط المنتج: " + attachedProductUrl : "");
      if (!target) {
        target = {
          id: "req_" + Date.now(),
          sessionId: String(sessionId || "all"),
          customerName: "زبون المتجر",
          customerPhone: "",
          requestedItem: "رد مباشر من الإدارة",
          customerMessage: "",
          status: "replied",
          managerReply: fullReply,
          attachedProductName: String(attachedProductName || ""),
          attachedProductUrl: String(attachedProductUrl || ""),
          repliedAt: Date.now(),
          createdAt: Date.now()
        };
        customerRequestsV114.unshift(target);
      } else {
        target.status = "replied";
        target.managerReply = fullReply;
        target.attachedProductName = String(attachedProductName || "");
        target.attachedProductUrl = String(attachedProductUrl || "");
        target.repliedAt = Date.now();
      }
      await saveStudioKeyV114("customer_requests", customerRequestsV114);
      res.json({ ok: true, requestObj: target });
    } catch (e: any) {
      res.status(500).json({ ok: false, error: String(e?.message || e) });
    }
  });

  app.post("/api/ai-v112/delete-request", async (req: any, res: any) => {
    try {
      await ensureStudioTableV114();
      const { requestId } = req.body || {};
      customerRequestsV114 = customerRequestsV114.filter(r => r.id !== requestId);
      await saveStudioKeyV114("customer_requests", customerRequestsV114);
      res.json({ ok: true });
    } catch (e: any) {
      res.status(500).json({ ok: false, error: String(e?.message || e) });
    }
  });

  app.get("/api/ai-v112/customer-poll", async (req: any, res: any) => {
    try {
      await ensureStudioTableV114();
      const sessionId = String(req.query?.sessionId || "").trim();
      const matching = customerRequestsV114.filter(
        r => r.status === "replied" && r.managerReply && (r.sessionId === sessionId || r.sessionId === "all")
      );
      res.json({ ok: true, replies: matching });
    } catch (e: any) {
      res.status(500).json({ ok: false, error: String(e?.message || e) });
    }
  });
}

export const registerAiStudioV112Routes = registerAiEngineV112;


// === ORIGINAL_DB_PUSH_PERSIST_V139_START ===
import * as __dbPushModV139 from "./db";
import fsV139 from "fs";
import pathV139 from "path";

const __PUSH_FILES_V139 = [
  ".ai-v112-store.json",
  ".push-subscriptions.json",
  ".vapid-keys.json",
  "server/.ai-v112-store.json"
];

export async function syncPushStoreFromTiDBV139(): Promise<void> {
  try {
    const pool = (__dbPushModV139 as any).getPool ? await (__dbPushModV139 as any).getPool() : null;
    if (!pool) return;
    // تصحيح أي أرقام طلبات قديمة TEST- أو ORD- إلى 1، 2، 3...
    try {
      const [ordRows]: any = await pool.query("SELECT id, orderNumber FROM orders ORDER BY id ASC");
      if (Array.isArray(ordRows)) {
        let seq = 0;
        for (const r of ordRows) {
          seq += 1;
          const exp = String(seq);
          if (String(r.orderNumber || "").trim() !== exp) {
            await pool.query("UPDATE orders SET orderNumber = ? WHERE id = ?", [exp, r.id]);
          }
        }
      }
    } catch (_e) {}

    const [rows]: any = await pool.query(
      "SELECT `key`, `value` FROM store_settings WHERE `key` LIKE 'v139_push_file_%'"
    );
    if (Array.isArray(rows)) {
      for (const r of rows) {
        const k = String(r.key || "").replace("v139_push_file_", "");
        const val = String(r.value || "");
        if (k && val && val.length > 2) {
          const targetPath = pathV139.resolve(process.cwd(), k);
          if (!fsV139.existsSync(targetPath)) {
            fsV139.writeFileSync(targetPath, val, "utf-8");
            console.log("[PushSyncV139] Restored push file from TiDB:", k);
          } else {
            // دمج اشتراكات المشرفين من القاعدة مع الملف المحلي حتى لا يضيع أي اشتراك بعد 12 ساعة
            try {
              const dbObj = JSON.parse(val);
              const locObj = JSON.parse(fsV139.readFileSync(targetPath, "utf-8"));
              let changed = false;
              for (const prop of ["pushSubscriptions", "adminSubscriptions", "subscriptions", "customerSubscriptions"]) {
                if (Array.isArray(dbObj[prop])) {
                  locObj[prop] = Array.isArray(locObj[prop]) ? locObj[prop] : [];
                  const existingEndpoints = new Set(locObj[prop].map((x: any) => x && (x.endpoint || (x.sub && x.sub.endpoint))));
                  for (const item of dbObj[prop]) {
                    const ep = item && (item.endpoint || (item.sub && item.sub.endpoint));
                    if (ep && !existingEndpoints.has(ep)) {
                      locObj[prop].push(item);
                      existingEndpoints.add(ep);
                      changed = true;
                    }
                  }
                }
              }
              if (dbObj.vapidKeys && !locObj.vapidKeys) {
                locObj.vapidKeys = dbObj.vapidKeys;
                changed = true;
              }
              if (changed) {
                fsV139.writeFileSync(targetPath, JSON.stringify(locObj, null, 2), "utf-8");
              }
            } catch (_e) {}
          }
        }
      }
    }
  } catch (err) {
    console.warn("[PushSyncV139] Restore warning:", err);
  }
}

export async function savePushStoreToTiDBV139(): Promise<void> {
  try {
    const pool = (__dbPushModV139 as any).getPool ? await (__dbPushModV139 as any).getPool() : null;
    if (!pool) return;
    for (const fname of __PUSH_FILES_V139) {
      const fpath = pathV139.resolve(process.cwd(), fname);
      if (fsV139.existsSync(fpath)) {
        const raw = fsV139.readFileSync(fpath, "utf-8");
        if (raw && raw.length > 2 && raw.length < 1500000) {
          const settingKey = "v139_push_file_" + pathV139.basename(fname);
          await pool.query(
            "INSERT INTO store_settings (`key`, `value`) VALUES (?, ?) ON DUPLICATE KEY UPDATE `value` = VALUES(`value`)",
            [settingKey, raw]
          );
        }
      }
    }
  } catch (_err) {}
}

setTimeout(() => { syncPushStoreFromTiDBV139(); }, 1500);
// === ORIGINAL_DB_PUSH_PERSIST_V139_END ===


// === ORIGINAL_BROADCAST_PUSH_V140_START ===
import webpushV140 from "web-push";

export async function sendCustomPushBroadcastV140(payload: {
  title: string;
  body: string;
  targetType?: string;
  targetValue?: string;
  url?: string;
}): Promise<{ sent: number; total: number }> {
  let sent = 0;
  let total = 0;
  try {
    if (typeof syncPushStoreFromTiDBV139 === "function") {
      await syncPushStoreFromTiDBV139();
    }
    const storeFile = pathV139.resolve(process.cwd(), ".ai-v112-store.json");
    if (!fsV139.existsSync(storeFile)) return { sent: 0, total: 0 };
    const data = JSON.parse(fsV139.readFileSync(storeFile, "utf-8"));
    if (data.vapidKeys && data.vapidKeys.publicKey && data.vapidKeys.privateKey) {
      try {
        webpushV140.setVapidDetails(
          "mailto:admin@original-store.com",
          data.vapidKeys.publicKey,
          data.vapidKeys.privateKey
        );
      } catch (_e) {}
    }

    const allSubs: any[] = [];
    const seen = new Set<string>();
    for (const key of ["pushSubscriptions", "customerSubscriptions", "adminSubscriptions", "subscriptions"]) {
      if (Array.isArray(data[key])) {
        for (const item of data[key]) {
          const sub = item && (item.subscription || item.sub || (item.endpoint ? item : null));
          if (sub && sub.endpoint && !seen.has(sub.endpoint)) {
            seen.add(sub.endpoint);
            allSubs.push({
              sub,
              phone: String(item.phone || item.customerPhone || "").trim(),
              orderNumber: String(item.orderNumber || item.orderId || "").trim(),
              role: String(item.role || "")
            });
          }
        }
      }
    }

    const tType = String(payload.targetType || "all").trim();
    const tVal = String(payload.targetValue || "").trim().replace(/^#/, "");

    const pushJson = JSON.stringify({
      title: payload.title || "متجر أورجنال",
      body: payload.body || "",
      icon: "/icon-orig-v139.png",
      badge: "/icon-orig-v139.png",
      url: payload.url || "/",
      tag: "orig-bcast-" + Date.now()
    });

    for (const entry of allSubs) {
      if (tType === "phone" && tVal) {
        if (entry.phone && !entry.phone.includes(tVal) && !tVal.includes(entry.phone)) {
          continue;
        }
      } else if (tType === "order" && tVal) {
        if (entry.orderNumber && entry.orderNumber !== tVal) {
          continue;
        }
      }
      total += 1;
      try {
        await webpushV140.sendNotification(entry.sub, pushJson);
        sent += 1;
      } catch (_err) {}
    }
  } catch (err) {
    console.warn("[BroadcastPushV140] warning:", err);
  }
  return { sent, total };
}
// === ORIGINAL_BROADCAST_PUSH_V140_END ===
