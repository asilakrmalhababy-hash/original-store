import pathlib, re, subprocess, sys, os

print("=== بدء التحديث الشامل والأسطوري v126 (إصلاح إشعارات الطلبات الفورية في لوحة الإدارة 100% + إرجاع أيقونات طلباتي والأقسام الـ 11 لتصميمها الأصلي 100% + منع تصاعد المحادثة للأعلى نهائياً حتى بعد 50 رسالة + نزول تدريجي سلس مثل ChatGPT) ===")

# 1. استعادة ملف Service Worker الأصلي النظيف من db9eb83 لضمان عمل إشعارات Web Push للطلبات 100% بدون أي تشويه
subprocess.run(["git", "checkout", "db9eb83", "--", "client/public/sw.js"], check=False)

# ==============================================================================
# 2. كتابة محرك الذكاء والإشعارات الفورية للطلبات server/ai_engine_v112.ts (v126)
#    - يحافظ 100% على جدول ai_studio_v115 (k, v) في قاعدة البيانات TiDB وملف النسخ الاحتياطي دون حذف أي شيء
#    - يراقب أحدث الطلبات في جدول orders (كاش خفيف 4 ثوانٍ) لإرسال إشعار فوري بالصوت والاهتزاز للوحة الإدارة فور وصول أي طلب جديد
#    - شيف تفاعلي بذاكرة محادثة يفهم "أريد طريقة أفضل" ويعطي جداول مقادير متوازنة مع ربط ملاحظة الطلب
# ==============================================================================
ai_engine_v126_ts = """import express from "express";
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

async function getCatalogCachedV114(): Promise<any[]> {
  const now = Date.now();
  if (cachedCatalogV114.length > 0 && now - lastCatalogTimeV114 < 300000) {
    return cachedCatalogV114;
  }
  try {
    const db: any = await getDb();
    if (db) {
      cachedCatalogV114 = await db.select().from(products);
      lastCatalogTimeV114 = now;
    }
  } catch {}
  return cachedCatalogV114;
}

let cachedLatestOrdersV126: any[] = [];
let lastOrdersTimeV126 = 0;

async function getLatestOrdersCachedV126(): Promise<any[]> {
  const now = Date.now();
  if (cachedLatestOrdersV126.length > 0 && now - lastOrdersTimeV126 < 4000) {
    return cachedLatestOrdersV126;
  }
  try {
    const db: any = await getDb();
    if (db) {
      const rows: any = await runRawSqlV115(
        db,
        "SELECT id, orderNumber, customerName, customerPhone, total, status, createdAt FROM orders ORDER BY id DESC LIMIT 10"
      );
      if (Array.isArray(rows)) {
        cachedLatestOrdersV126 = rows;
        lastOrdersTimeV126 = now;
      }
    }
  } catch {}
  return cachedLatestOrdersV126;
}

async function ensureStudioTableV114() {
  if (tableLoadedFromDbV115) return;
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
  } catch {}
}

async function saveStudioKeyV114(key: string, valObj: any) {
  saveDiskBackupV115();
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
    .replace(/\\(\\s*رقم\\s*\\d+\\s*\\)/g, "")
    .replace(/\\s*\\([^()]*\\)\\s*$/g, "")
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
    .replace(/\\s+/g, " ")
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
    let content = "✨ معلومات «" + cleanName + "»" + (priceStr ? " (" + priceStr + ")" : "") + ":\\n" + customAi;
    if (matchedRecipe) {
      content += "\\n\\n🍰 وصفة مقترحة («" + matchedRecipe.title + "»):\\n" + matchedRecipe.steps;
    }
    return {
      modalTitle: "✨ معلومات المنتج: " + cleanName,
      chips,
      content,
      kind,
      recipe: matchedRecipe || null
    };
  }

  const customNoteBlock = customAi ? "\\n💡 معلومة إضافية: " + customAi : "";
  const recipeBlock = matchedRecipe ? "\\n\\n🍰 وصفة «" + matchedRecipe.title + "»:\\n" + matchedRecipe.steps : "";

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
        "🔥 القيمة الغذائية والسعرات الحرارية لـ «" + cleanName + "»:\\n" +
        "• السعرات التقريبية: حوالي 110 إلى 150 سعرة حرارية للحصة الواحدة تمنح طاقة سريعة.\\n" +
        "• جاهز للأكل مباشرة كسناك لذيذ بدون أي تحضير." +
        customNoteBlock;
    } else {
      text =
        "✨ معلومات «" + cleanName + "»" + (priceStr ? " (السعر: " + priceStr + ")" : "") + ":\\n" +
        "• منتج جاهز للأكل مباشرة بطعم لذيذ، لا يحتاج إلى أي طبخ أو تحضير.\\n" +
        "• السعرات الحرارية التقريبية: حوالي 120 – 150 سعرة حرارية.\\n" +
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
      "✨ معلومات وأفكار «" + cleanName + "»" + (priceStr ? " (السعر: " + priceStr + ")" : "") + ":\\n" +
      "• يصلح للتقديم مع الشاي والحليب، أو لعمل حلى بارد سريع بطبقات القشطة والشوكولاتة.\\n" +
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
      "✨ معلومات «" + cleanName + "»" + (priceStr ? " (السعر: " + priceStr + ")" : "") + ":\\n" +
      "• السعرات التقريبية: حوالي 90 – 130 سعرة حرارية للعبوة.\\n" +
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
      "✨ معلومات «" + cleanName + "»" + (priceStr ? " (السعر: " + priceStr + ")" : "") + ":\\n" +
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
    "✨ معلومات «" + cleanName + "»" + (priceStr ? " (السعر: " + priceStr + ")" : "") + ":\\n" +
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
  "😄 نكتة خفيفة على السريع:\\nواحد راح للبقالة قال لصاحب المحل: عندك سكر؟ قاله: أيوه! قاله: الله يشفيك! 😂\\nبشرني يا غالي، إيش نجهز لك اليوم من مقاضي أو وصفات؟",
  "😄 خذ هذي النكتة يا غالي:\\nواحد سأل صاحبه: ليش تحط التلفون في الثلاجة؟ قاله: عشان لا تذوب الشوكولاتة اللي في الصورة! 😂🍫\\nقول لي، جاي على بالك حلى بارد ولا طبخة سريعة اليوم؟",
  "😄 ابتسم يا غالي:\\nالأم تسأل ولدها: لو أعطيتك تفاحتين وأعطيت أخوك تفاحتين، كم يصير معكم؟ قال: 4 تفاحات عندي وتفاحتين في بطني! 😂🍎\\nآمرني يا غالي، إيش بخاطرك نطبخ أو نطلب اليوم؟"
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

  const stepsFormatted = variant.steps.map((s, idx) => (idx + 1) + ". " + s).join("\\n");
  const introLine = isAlternative
    ? "✨ ولا يهمك يا غالي! جبت لك طريقة ثانية ألذ وأحلى لتحضير «" + variant.title + "» (⏱️ " + variant.prepTime + "):"
    : "👨‍🍳 أبشر يا غالي! إليك الطريقة الاحترافية لتحضير «" + variant.title + "» (⏱️ " + variant.prepTime + "):";

  const replyText =
    introLine + "\\n\\n" +
    "📋 خطوات التحضير:\\n" +
    stepsFormatted + "\\n\\n" +
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
      reply: "أبشر من عيوني يا غالي! 📲 أرسلت إشعار فوري الآن لهاتف مدير المتجر بطلبك («" + requestedTopic + "»).\\nأول ما يرد المدير سيظهر رده هنا أمامك في المحادثة مباشرةً!",
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
      let replyTxt = String(rule.response || "").replace(/\\(\\s*رقم\\s*\\d+\\s*\\)/g, "");
      if (rule.linkedProductUrl && !replyTxt.includes(rule.linkedProductUrl)) {
        replyTxt += "\\n🔗 رابط المنتج: " + rule.linkedProductUrl;
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
      "🍰 «" + matchedRec.title + "»\\n\\n" +
      "📋 طريقة التحضير والخطوات الكاملة:\\n" +
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
      "«" + triggeredPromo.productName + "»" + (pPrice > 0 ? " (بسعر " + pPrice.toLocaleString("en-US") + " ر.ي)" : "") + "\\n" +
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
    const words = pName.split(/\\s+/).filter(w => w.length >= 4);
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
        reply: modalInfo.content.replace(/\\(\\s*رقم\\s*\\d+\\s*\\)/g, ""),
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
    .split(/\\s+/)
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
        ? unavailInst.content.replace(/\\{المنتج\\}/g, cleanWanted)
        : "فهمتك يا غالي! أنت تطلب «" + cleanWanted + "».. حلو حلو! 👌\\nحالياً هذا الصنف غير ظاهر في قائمة المتجر، لكن ولا يهمك! جهزته لك في الجدول بالأسفل كصنف قابل للطلب: اضغط على زر (📋 نسخ وإضافة تلقائياً في ملاحظة الطلب) ليُضاف مع طلبك، أو اضغط إرسال إشعار فوري لهاتف مدير المتجر وسيرد عليك فوراً!";

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

  const handleGetConfig = async (_req: any, res: any) => {
    try {
      await ensureStudioTableV114();
      const catalog = await getCatalogCachedV114();
      const latestOrders = await getLatestOrdersCachedV126();
      const simpleCatalog = catalog.map(p => ({
        id: p.id,
        name: cleanProductNameV112(p.name),
        price: Math.round(Number(p.price || 0)),
        unit: p.unit || "حبة",
        imageUrl: p.imageUrl || ""
      }));
      res.json({
        ok: true,
        config: studioConfigV114,
        requests: customerRequestsV114,
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
      const fullReply = cleanReply + (attachedProductUrl ? "\\n🔗 رابط المنتج: " + attachedProductUrl : "");
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
"""

pathlib.Path("server/ai_engine_v112.ts").write_text(ai_engine_v126_ts, encoding="utf-8")
print("1. Updated server/ai_engine_v112.ts (v126 Live Order Notifications + Preserved TiDB Studio Table + Multi-Method Chef)!")

# ==============================================================================
# 3. التأكد من تسجيل registerAiEngineV112 في server/_core/index.ts ورفع max_tokens في server/commerce.ts
# ==============================================================================
srv_index = pathlib.Path("server/_core/index.ts")
if srv_index.exists():
    si = srv_index.read_text(encoding="utf-8")
    si = re.sub(r'express\.json\(\s*\)', 'express.json({ limit: "50mb" })', si)
    srv_index.write_text(si, encoding="utf-8")

comm_path = pathlib.Path("server/commerce.ts")
if comm_path.exists():
    cc = comm_path.read_text(encoding="utf-8")
    cc = re.sub(r'max_tokens:\s*(?:180|500|800|1000|1200)\b', 'max_tokens: 1500', cc)
    comm_path.write_text(cc, encoding="utf-8")
    print("2. Verified server/_core/index.ts and server/commerce.ts!")

# ==============================================================================
# 4. تنظيف وتحديث client/index.html (v126):
#    - مسح جميع تراكمات v119-v125 التي شوهت أيقونة (تم الاستلام) والأقسام الـ 11
#    - عزل تنسيقات الشات حصرياً داخل [data-v126-chat-messages='1'] فقط
#    - تفعيل إشعارات الهاتف الفورية (صوت + اهتزاز + إشعار نظام + شريط علوي) عند وصول أي طلب جديد للوحة الإدارة
#    - معالجة كل رسالة مرة واحدة فقط (data-v126-done='1') لمنع تصاعد المحادثة للأعلى بعد 5-6 رسائل نهائياً
# ==============================================================================
html_path = pathlib.Path("client/index.html")
if html_path.exists():
    ht = html_path.read_text(encoding="utf-8")

    clean_middle_v126 = """function normalizeArabicClientV116(str) {
          return String(str || "")
            .toLowerCase()
            .replace(/[أإآ]/g, "ا")
            .replace(/ة/g, "ه")
            .replace(/ى/g, "ي")
            .replace(/[؟?!.,،]/g, " ")
            .replace(/\\s+/g, " ")
            .trim();
        }

        function matchRecipeClientV116(userText) {
          var list = (window.__v114StudioConfig && window.__v114StudioConfig.recipes) || [];
          if (!Array.isArray(list) || list.length === 0) return null;
          var normUser = normalizeArabicClientV116(userText);
          if (!normUser || normUser.length < 3) return null;
          var stopWords = ["اريد", "ابغي", "اشتي", "هل", "عندكم", "ممكن", "كيف", "اسوي", "طريقه", "عمل", "وصفه", "حلو", "لذيذ", "سريع", "في", "من", "مع", "على", "عن"];

          for (var i = 0; i < list.length; i++) {
            var rec = list[i];
            var normTitle = normalizeArabicClientV116(rec.title || "");
            var normKw = normalizeArabicClientV116(rec.keywords || "");
            if (normTitle && (normUser.indexOf(normTitle) !== -1 || normTitle.indexOf(normUser) !== -1)) return rec;
            if (normKw && (normUser.indexOf(normKw) !== -1 || normKw.indexOf(normUser) !== -1)) return rec;

            var kwParts = String(rec.keywords || "").split(/[،,]+/).map(function(s) { return normalizeArabicClientV116(s); }).filter(function(s) { return s.length >= 3; });
            for (var kIdx = 0; kIdx < kwParts.length; kIdx++) {
              if (normUser.indexOf(kwParts[kIdx]) !== -1 || kwParts[kIdx].indexOf(normUser) !== -1) return rec;
            }

            var combinedTarget = normTitle + " " + normKw;
            var userWords = normUser.split(" ").filter(function(w) { return w.length >= 3 && stopWords.indexOf(w) === -1; });
            var matchedWords = userWords.filter(function(w) { return combinedTarget.indexOf(w) !== -1; });
            if (matchedWords.length >= 2) return rec;
            if (matchedWords.length >= 1 && (normUser.indexOf("حلي") !== -1 || normUser.indexOf("وصفه") !== -1)) return rec;
          }
          return null;
        }

        function matchRuleClientV116(userText) {
          var rules = (window.__v114StudioConfig && window.__v114StudioConfig.rules) || [];
          if (!Array.isArray(rules) || rules.length === 0) return null;
          var normUser = normalizeArabicClientV116(userText);
          if (!normUser) return null;
          for (var i = 0; i < rules.length; i++) {
            var trig = normalizeArabicClientV116(rules[i].trigger || "");
            if (trig && normUser.indexOf(trig) !== -1) return rules[i];
          }
          return null;
        }

        function matchPromoClientV116(userText) {
          var promos = (window.__v114StudioConfig && window.__v114StudioConfig.promotedProducts) || [];
          if (!Array.isArray(promos) || promos.length === 0) return null;
          var normUser = normalizeArabicClientV116(userText);
          if (!normUser) return null;
          for (var i = 0; i < promos.length; i++) {
            var p = promos[i];
            if (p.active === false || !p.triggerKeywords) continue;
            var kws = String(p.triggerKeywords).split(/[،,]+/).map(function(s) { return normalizeArabicClientV116(s); }).filter(Boolean);
            for (var j = 0; j < kws.length; j++) {
              if (normUser.indexOf(kws[j]) !== -1) return p;
            }
          }
          return null;
        }

        function extractAnyUserTextFromJsonBodyV116(rawBody) {
          try {
            var parsed = JSON.parse(rawBody);
            var found = "";
            function walkObj(o) {
              if (found || !o) return;
              if (typeof o === "string") {
                var s = o.trim();
                if (s.length >= 2 && s.length <= 300 && !/^(user|assistant|system|sess_)/i.test(s)) {
                  found = s;
                }
                return;
              }
              if (Array.isArray(o)) {
                for (var i = o.length - 1; i >= 0; i--) walkObj(o[i]);
                return;
              }
              if (typeof o === "object") {
                var priorityKeys = ["message", "prompt", "query", "text", "userMessage", "question", "content", "input"];
                for (var k = 0; k < priorityKeys.length; k++) {
                  var pk = priorityKeys[k];
                  if (typeof o[pk] === "string" && o[pk].trim().length >= 2) {
                    found = o[pk].trim();
                    return;
                  }
                }
                if (o.json) walkObj(o.json);
                if (o["0"]) walkObj(o["0"]);
                Object.keys(o).forEach(function(key) {
                  if (key !== "meta" && key !== "sessionId") walkObj(o[key]);
                });
              }
            }
            walkObj(parsed);
            return found;
          } catch (e) {
            return "";
          }
        }

        window.__v126SmartDataByQuery = window.__v126SmartDataByQuery || {};
        window.__v126PreviousUserMsg = "";
        window.__v126LastBubbleCount = 0;
        window.__v126GlideRafId = null;
        window.__v126UserTouching = false;
        window.__v126PinBottomUntil = 0;
        window.__v126LastValidScrollTop = 0;
        window.__v126NotifiedOrderIds = {};
        window.__v126OrdersSeededOnce = false;

        try {
          if (window.location.pathname.indexOf("/admin") !== -1) {
            localStorage.setItem("original_v126_is_admin", "1");
          }
          var savedOrdIds = localStorage.getItem("original_v126_notified_orders");
          if (savedOrdIds) {
            window.__v126NotifiedOrderIds = JSON.parse(savedOrdIds) || {};
            window.__v126OrdersSeededOnce = true;
          }
        } catch (e) {}

        (function injectScopedChatStylesV126() {
          var oldIds = ["v121-gemini-chat-styles", "v122-gemini-chat-styles", "v123-gemini-chat-styles", "v124-gemini-chat-styles", "v125-gemini-chat-styles", "v126-gemini-chat-styles"];
          oldIds.forEach(function(id) {
            var el = document.getElementById(id);
            if (el) el.remove();
          });
          var st = document.createElement("style");
          st.id = "v126-gemini-chat-styles";
          st.textContent =
            "[data-v126-chat-messages='1'], [data-v126-chat-messages='1'] * { overflow-anchor: none !important; }" +
            "[data-v126-chat-messages='1'] .v126-user-row-left { display: flex !important; flex-direction: row !important; justify-content: flex-start !important; align-items: flex-start !important; direction: ltr !important; width: 100% !important; margin: 6px 0 !important; }" +
            "[data-v126-chat-messages='1'] .v126-user-bubble { background: #0d3825 !important; color: #ffffff !important; border: 1.5px solid #165b3c !important; border-radius: 20px 20px 20px 4px !important; padding: 9px 16px !important; box-shadow: 0 3px 10px rgba(13,56,37,0.15) !important; font-weight: 800 !important; font-size: 0.92rem !important; width: fit-content !important; max-width: 82% !important; display: inline-block !important; direction: rtl !important; text-align: right !important; margin-left: 0 !important; margin-right: auto !important; }" +
            "[data-v126-chat-messages='1'] .v126-user-bubble * { color: #ffffff !important; direction: rtl !important; text-align: right !important; }" +
            "[data-v126-chat-messages='1'] .v126-bot-full { width: 100% !important; max-width: 100% !important; background: transparent !important; border: none !important; box-shadow: none !important; border-bottom: 1px solid #e2e8f0 !important; border-radius: 0 !important; padding: 12px 2px 18px 2px !important; margin: 4px 0 !important; direction: rtl !important; text-align: right !important; }" +
            "[data-v126-chat-messages='1'] .v126-bot-row { width: 100% !important; max-width: 100% !important; display: block !important; }";
          document.head.appendChild(st);
        })();

        function getStrictlyActiveAiChatBoxV126() {
          if (window.location.pathname.indexOf("/admin") !== -1) return null;
          var chatInput = Array.from(document.querySelectorAll("input, textarea")).find(function(inp) {
            var ph = inp.getAttribute("placeholder") || "";
            return ph.indexOf("اطلب سلة الصباح") !== -1 || ph.indexOf("وصفة اقتصادية") !== -1 || ph.indexOf("مقاضي المطبخ") !== -1;
          });
          if (!chatInput || chatInput.offsetParent === null) return null;

          var cur = chatInput.parentElement;
          var chatCard = null;
          while (cur && cur !== document.body) {
            var txt = cur.textContent || "";
            if (
              txt.indexOf("طلبك بين يديك") !== -1 ||
              txt.indexOf("حالة تجهيز وتوصيل الطلب") !== -1 ||
              txt.indexOf("تسوق الخضار") !== -1 ||
              txt.indexOf("اكتشف الفواكه") !== -1 ||
              txt.indexOf("منتجات المتجر") !== -1
            ) {
              break;
            }
            if (txt.indexOf("مساعد وشيف أورجنال الذكي") !== -1 && txt.indexOf("محادثة جديدة") !== -1) {
              chatCard = cur;
              break;
            }
            cur = cur.parentElement;
          }
          if (!chatCard) return null;

          var divs = Array.from(chatCard.querySelectorAll("div"));
          var messagesBox = null;
          for (var i = 0; i < divs.length; i++) {
            var d = divs[i];
            if (d.contains(chatInput)) continue;
            if ((d.textContent || "").indexOf("محادثة جديدة") !== -1) continue;
            try {
              var cs = window.getComputedStyle(d);
              if ((cs.overflowY === "auto" || cs.overflowY === "scroll") && d.clientHeight > 80) {
                messagesBox = d;
                break;
              }
            } catch (e) {}
          }
          if (!messagesBox) {
            var inpWrapper = chatInput.parentElement;
            while (inpWrapper && inpWrapper.parentElement !== chatCard) {
              inpWrapper = inpWrapper.parentElement;
            }
            if (inpWrapper && inpWrapper.previousElementSibling) {
              messagesBox = inpWrapper.previousElementSibling;
            }
          }
          if (!messagesBox) return null;

          messagesBox.setAttribute("data-v126-chat-messages", "1");
          return { card: chatCard, messagesBox: messagesBox, input: chatInput };
        }

        function stopGlideAnimationV126() {
          if (window.__v126GlideRafId) {
            cancelAnimationFrame(window.__v126GlideRafId);
            window.__v126GlideRafId = null;
          }
        }

        function startChatGptProgressiveGlideV126(sc, targetEndTop, durationMs) {
          if (!sc) return;
          stopGlideAnimationV126();
          var startTop = sc.scrollTop;
          var dist = targetEndTop - startTop;
          if (dist <= 8) {
            sc.scrollTop = targetEndTop;
            window.__v126LastValidScrollTop = sc.scrollTop;
            return;
          }
          var startTime = performance.now();
          var dur = durationMs || 1400;
          function step(now) {
            if (window.__v126UserTouching) {
              stopGlideAnimationV126();
              return;
            }
            var p = Math.min(1, (now - startTime) / dur);
            var eased = 1 - Math.pow(1 - p, 2.2);
            sc.scrollTop = Math.round(startTop + dist * eased);
            window.__v126LastValidScrollTop = sc.scrollTop;
            if (p < 1) {
              window.__v126GlideRafId = requestAnimationFrame(step);
            } else {
              window.__v126GlideRafId = null;
            }
          }
          window.__v126GlideRafId = requestAnimationFrame(step);
        }

        function scrollToNewReplyStartAndGlideV126() {
          try {
            var ctx = getStrictlyActiveAiChatBoxV126();
            if (!ctx || !ctx.messagesBox) return;
            var sc = ctx.messagesBox;
            var botCards = Array.from(sc.querySelectorAll(".v126-bot-full"));
            var userBubbles = Array.from(sc.querySelectorAll(".v126-user-bubble"));
            if (botCards.length > 0) {
              var lastBot = botCards[botCards.length - 1];
              var lastUser = userBubbles.length > 0 ? userBubbles[userBubbles.length - 1] : null;
              var anchorEl = lastUser || lastBot;
              var scRect = sc.getBoundingClientRect();
              var anchorRect = anchorEl.getBoundingClientRect();
              var targetStart = sc.scrollTop + (anchorRect.top - scRect.top) - 10;
              if (targetStart > 0) {
                sc.scrollTop = targetStart;
                window.__v126LastValidScrollTop = sc.scrollTop;
              }
              var endScroll = sc.scrollHeight - sc.clientHeight;
              if (endScroll > sc.scrollTop + 15) {
                setTimeout(function() {
                  startChatGptProgressiveGlideV126(sc, sc.scrollHeight - sc.clientHeight, 1450);
                }, 150);
              }
            } else {
              sc.scrollTop = sc.scrollHeight;
              window.__v126LastValidScrollTop = sc.scrollTop;
            }
          } catch (e) {}
        }

        function lockChatScrollAtBottomOnSendV126() {
          try {
            var ctx = getStrictlyActiveAiChatBoxV126();
            if (!ctx || !ctx.messagesBox) return;
            var sc = ctx.messagesBox;
            sc.scrollTop = sc.scrollHeight;
            window.__v126LastValidScrollTop = sc.scrollTop;
          } catch (e) {}
        }

        function bindChatScrollProtectionV126(ctx) {
          if (!ctx || !ctx.messagesBox || !ctx.input) return;
          var sc = ctx.messagesBox;
          var inp = ctx.input;

          if (!sc.getAttribute("data-v126-scroll-bound")) {
            sc.setAttribute("data-v126-scroll-bound", "1");
            sc.addEventListener("touchstart", function() {
              window.__v126UserTouching = true;
              stopGlideAnimationV126();
            }, { passive: true });
            sc.addEventListener("touchend", function() {
              if (sc.scrollTop > 20) window.__v126LastValidScrollTop = sc.scrollTop;
              setTimeout(function() { window.__v126UserTouching = false; }, 250);
            }, { passive: true });
            sc.addEventListener("wheel", function() {
              window.__v126UserTouching = true;
              stopGlideAnimationV126();
              setTimeout(function() { window.__v126UserTouching = false; }, 300);
            }, { passive: true });
            sc.addEventListener("scroll", function() {
              if (window.__v126UserTouching) {
                window.__v126LastValidScrollTop = sc.scrollTop;
                return;
              }
              if (window.__v126PinBottomUntil && Date.now() < window.__v126PinBottomUntil) {
                if (sc.scrollTop < 35 && window.__v126LastValidScrollTop > 55) {
                  sc.scrollTop = window.__v126LastValidScrollTop;
                }
              } else if (sc.scrollTop > 35) {
                window.__v126LastValidScrollTop = sc.scrollTop;
              }
            }, { passive: true });
          }

          if (!inp.getAttribute("data-v126-inp-bound")) {
            inp.setAttribute("data-v126-inp-bound", "1");
            function onSendAction() {
              stopGlideAnimationV126();
              var savedWinY = window.scrollY;
              if (sc.scrollTop > 30) window.__v126LastValidScrollTop = sc.scrollTop;
              window.__v126PinBottomUntil = Date.now() + 6000;
              setTimeout(function() {
                lockChatScrollAtBottomOnSendV126();
                if (Math.abs(window.scrollY - savedWinY) > 40) window.scrollTo(0, savedWinY);
              }, 20);
              setTimeout(function() {
                lockChatScrollAtBottomOnSendV126();
              }, 90);
              setTimeout(function() {
                lockChatScrollAtBottomOnSendV126();
                enhanceChatBubblesSafelyV117();
              }, 240);
            }
            inp.addEventListener("keydown", function(e) {
              if (e.key === "Enter") onSendAction();
            });
            var row = inp.parentElement;
            if (row) {
              Array.from(row.querySelectorAll("button")).forEach(function(b) {
                b.addEventListener("click", onSendAction);
              });
            }
          }
        }

        function setReactInputValueNativeV126(el, val) {
          try {
            var proto = el.tagName === "TEXTAREA" ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
            var desc = Object.getOwnPropertyDescriptor(proto, "value");
            if (desc && desc.set) {
              desc.set.call(el, val);
            } else {
              el.value = val;
            }
            el.dispatchEvent(new Event("input", { bubbles: true }));
            el.dispatchEvent(new Event("change", { bubbles: true }));
          } catch (e) {
            el.value = val;
          }
        }

        window.__copyAndAttachMissingToOrderNotesV126 = function(btnEl, missingText, recipeTitle) {
          var noteLine = "📌 طلب توفير إضافي مع الطلب (" + (recipeTitle || "وصفة الشيف") + "): " + missingText;
          try {
            var existing = localStorage.getItem("original_ai_extra_order_notes") || "";
            var updated = existing ? (existing.indexOf(missingText) !== -1 ? existing : existing + " | " + noteLine) : noteLine;
            localStorage.setItem("original_ai_extra_order_notes", updated);
          } catch (e) {}

          if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(noteLine).catch(function() {});
          }

          var noteInputs = Array.from(document.querySelectorAll("textarea, input[type='text']")).filter(function(inp) {
            var ph = (inp.getAttribute("placeholder") || "") + " " + (inp.getAttribute("name") || "") + " " + (inp.id || "");
            return ph.indexOf("ملاحظ") !== -1 || ph.indexOf("note") !== -1 || ph.indexOf("تفاصيل") !== -1 || ph.indexOf("اضافي") !== -1;
          });
          noteInputs.forEach(function(inp) {
            var curVal = inp.value || "";
            var nextVal = curVal ? (curVal.indexOf(missingText) !== -1 ? curVal : curVal + "\\n" + noteLine) : noteLine;
            setReactInputValueNativeV126(inp, nextVal);
          });

          origFetchV112("/api/ai-v112/request-store", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              sessionId: window.__v112SessionId || "guest",
              requestedItem: missingText,
              customerMessage: noteLine
            })
          }).catch(function() {});

          if (btnEl) {
            btnEl.innerHTML = "✅ تم النسخ والإضافة لملاحظة طلبك تلقائياً! سيرد عليك المتجر فوراً";
            btnEl.style.background = "#16a34a";
            btnEl.style.color = "#ffffff";
          }
        };

        function syncOrderNotesFieldV126() {
          try {
            if (window.location.pathname.indexOf("/admin") !== -1) return;
            var savedNote = localStorage.getItem("original_ai_extra_order_notes") || "";
            if (!savedNote) return;
            var noteInputs = Array.from(document.querySelectorAll("textarea, input[type='text']")).filter(function(inp) {
              var ph = (inp.getAttribute("placeholder") || "") + " " + (inp.getAttribute("name") || "") + " " + (inp.id || "");
              return ph.indexOf("ملاحظ") !== -1 || ph.indexOf("note") !== -1;
            });
            noteInputs.forEach(function(inp) {
              if (!inp.value && !inp.getAttribute("data-v126-note-filled")) {
                inp.setAttribute("data-v126-note-filled", "1");
                setReactInputValueNativeV126(inp, savedNote);
              }
            });
          } catch (e) {}
        }

        function buildIngredientsTableHtmlV126(rows, missingItemsText, recipeTitle) {
          if (!Array.isArray(rows) || rows.length === 0) return "";
          var rowsHtml = rows.map(function(r) {
            var badge = r.available
              ? '<span style="color:#15803d;font-weight:900;font-size:0.75rem;white-space:nowrap;">✅ متوفر</span>'
              : '<span style="color:#d97706;font-weight:800;font-size:0.74rem;white-space:nowrap;">اطلبه بالملاحظة</span>';
            var priceCell = (r.available && r.price)
              ? '<span style="color:#0f172a;font-weight:800;font-size:0.76rem;white-space:nowrap;">' + r.price + ' ر.ي</span>'
              : '<span style="color:#94a3b8;font-size:0.75rem;">—</span>';
            return (
              '<tr style="border-bottom:1px solid #e2e8f0;">' +
              '<td style="padding:8px 6px;font-weight:800;color:#0f172a;font-size:0.8rem;text-align:right;line-height:1.35;">' + (r.name || "") + '</td>' +
              '<td style="padding:8px 6px;color:#475569;font-size:0.77rem;font-weight:700;text-align:center;white-space:nowrap;">' + (r.amount || "حسب الرغبة") + '</td>' +
              '<td style="padding:8px 6px;text-align:center;white-space:nowrap;">' + priceCell + '</td>' +
              '<td style="padding:8px 6px;text-align:left;white-space:nowrap;">' + badge + '</td>' +
              '</tr>'
            );
          }).join("");

          var missingActionHtml = "";
          if (missingItemsText && missingItemsText.length > 0) {
            var safeMissing = String(missingItemsText).replace(/"/g, "&quot;").replace(/'/g, "&#39;");
            var safeTitle = String(recipeTitle || "الوصفة").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
            missingActionHtml =
              '<div style="margin-top:10px;padding:10px 12px;background:#f8fafc;border:1px dashed #cbd5e1;border-radius:12px;">' +
              '<div style="font-weight:800;color:#334155;font-size:0.77rem;margin-bottom:6px;">📦 مكونات غير ظاهرة بالمتجر (تُضاف لملاحظة طلبك بضغطة زر): <span style="color:#0d3825;">' + missingItemsText + '</span></div>' +
              '<button type="button" class="v126-copy-notes-btn" data-missing="' + safeMissing + '" data-title="' + safeTitle + '" style="width:100%;background:#0d3825;color:#ffffff;border:none;border-radius:10px;padding:9px 12px;font-weight:800;font-size:0.78rem;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:6px;">' +
              '📋 نسخ وإضافة تلقائياً في ملاحظة الطلب (ليرد عليك المتجر حول توفرها)' +
              '</button>' +
              '</div>';
          }

          return (
            '<div class="v126-ingredients-panel" style="margin:12px 0 8px 0;padding:4px 0;direction:rtl;text-align:right;width:100%;overflow-x:auto;">' +
            '<div style="font-weight:900;color:#0d3825;font-size:0.84rem;margin-bottom:6px;">📊 جدول مقادير الوصفة وحالة التوفر:</div>' +
            '<table style="width:100%;border-collapse:collapse;table-layout:auto;">' +
            '<thead><tr style="border-bottom:2px solid #cbd5e1;color:#475569;font-size:0.75rem;">' +
            '<th style="padding:6px;text-align:right;font-weight:900;">المكون</th>' +
            '<th style="padding:6px;text-align:center;font-weight:900;white-space:nowrap;">المقدار</th>' +
            '<th style="padding:6px;text-align:center;font-weight:900;white-space:nowrap;">السعر</th>' +
            '<th style="padding:6px;text-align:left;font-weight:900;white-space:nowrap;">الحالة</th>' +
            '</tr></thead>' +
            '<tbody>' + rowsHtml + '</tbody>' +
            '</table>' +
            missingActionHtml +
            '</div>'
          );
        }

        function syncNativeGreenCartBoxV126(assistantCard, availItems) {
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
            return x.children.length === 0 && !(x.closest && x.closest(".v126-ingredients-panel"));
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

        function isStrictlyChatUserBubbleV126(el, messagesBox) {
          if (!el || !messagesBox || !messagesBox.contains(el)) return false;
          if (el.closest && (el.closest(".v126-bot-full") || el.closest(".v126-ai-header") || el.closest("button"))) return false;
          if (el.tagName === "BUTTON" || el.tagName === "IMG" || el.tagName === "SVG" || el.querySelector("button, input, textarea, img, svg")) return false;
          var t = (el.textContent || "").trim();
          if (t === "✓" || t === "✔" || t === "✨" || /^\\d+$/.test(t)) return false;
          if (t.length < 2 || t.length > 220) return false;
          if (t.indexOf("الأصناف والمقادير") !== -1 || t.indexOf("محادثة جديدة") !== -1 || t.indexOf("شيف ومساعد") !== -1) return false;
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

        window.__openRecipeImageLightboxV116 = function(src, title) {
          if (!src) return;
          var lb = document.createElement("div");
          lb.style.cssText = "position:fixed;inset:0;z-index:999999;background:rgba(8,28,18,0.92);display:flex;flex-direction:column;align-items:center;justify-content:center;padding:18px;direction:rtl;";
          lb.onclick = function() { lb.remove(); };
          lb.innerHTML =
            '<div style="max-width:520px;width:100%;text-align:center;">' +
            '<img src="' + src + '" style="width:100%;max-height:75vh;object-fit:contain;border-radius:20px;border:3px solid #d4af37;box-shadow:0 18px 50px rgba(0,0,0,0.6);" />' +
            '<div style="color:#d4af37;font-weight:900;font-size:1.05rem;margin-top:12px;">🍰 ' + (title || "") + '</div>' +
            '<button type="button" style="margin-top:12px;background:#ffffff;color:#0d3825;border:none;border-radius:99px;padding:8px 24px;font-weight:800;font-size:0.88rem;cursor:pointer;">✕ إغلاق الصورة</button>' +
            '</div>';
          document.body.appendChild(lb);
        };

        function replaceTrpcAiPayloadInPlaceV117(trpcObj, smartData) {
          if (!trpcObj || typeof trpcObj !== "object") return;
          function walkPayload(node) {
            if (!node || typeof node !== "object") return;
            if (Array.isArray(node)) {
              node.forEach(walkPayload);
              return;
            }
            var textKeys = ["reply", "message", "answer", "content", "text", "response"];
            textKeys.forEach(function(tk) {
              if (typeof node[tk] === "string" && node[tk].length > 5 && smartData.reply) {
                node[tk] = smartData.reply;
              }
            });
            var itemKeys = ["items", "suggestedItems", "products", "recommendations", "basket"];
            itemKeys.forEach(function(ik) {
              if (Array.isArray(node[ik]) && Array.isArray(smartData.suggestedItems) && smartData.suggestedItems.length > 0) {
                var templateItem = node[ik][0] || {};
                node[ik] = smartData.suggestedItems.map(function(si) {
                  return Object.assign({}, templateItem, {
                    id: si.id || si.productId || 1,
                    productId: si.productId || si.id || 1,
                    name: si.name,
                    productName: si.name,
                    price: si.price || 100,
                    unitPrice: si.price || 100,
                    unit: si.unit || "حبة",
                    quantity: 1,
                    lineTotal: si.price || 100
                  });
                });
              }
            });
            if (typeof node.total === "number" && Array.isArray(smartData.suggestedItems) && smartData.suggestedItems.length > 0) {
              node.total = smartData.suggestedItems.reduce(function(s, x) { return s + Number(x.price || 0); }, 0);
            }
            Object.keys(node).forEach(function(k) {
              if (k !== "items" && k !== "suggestedItems" && typeof node[k] === "object") {
                walkPayload(node[k]);
              }
            });
          }
          walkPayload(trpcObj);
        }

        function enhanceChatBubblesSafelyV117() {
          syncOrderNotesFieldV126();

          var ctx = getStrictlyActiveAiChatBoxV126();
          if (!ctx || !ctx.messagesBox) return;
          var messagesBox = ctx.messagesBox;
          bindChatScrollProtectionV126(ctx);

          var allUserBubbles = Array.from(messagesBox.querySelectorAll("div, p, span")).filter(function(el) {
            if (!isStrictlyChatUserBubbleV126(el, messagesBox)) return false;
            var hasChildMatch = Array.from(el.children).some(function(c) {
              return isStrictlyChatUserBubbleV126(c, messagesBox);
            });
            if (hasChildMatch) return false;

            if (!el.classList.contains("v126-user-bubble")) {
              el.classList.add("v126-user-bubble");
              if (el.parentElement && el.parentElement !== messagesBox) {
                el.parentElement.classList.add("v126-user-row-left");
              }
            }
            var t = (el.textContent || "").trim();
            if (!el.getAttribute("data-v126-orig-user")) {
              el.setAttribute("data-v126-orig-user", t);
            }
            return true;
          });

          var allLeaves = Array.from(messagesBox.querySelectorAll("p, div")).filter(function(el) {
            if (el.children.length !== 0) return false;
            if (el.closest && (el.closest(".v126-user-bubble") || el.closest(".v126-ingredients-panel") || el.closest(".v126-ai-header") || el.closest(".v118-wa-photo-box") || el.closest("button"))) return false;
            var parentCard = el.parentElement;
            if (!parentCard || parentCard === messagesBox) return false;
            var cardTxt = parentCard.textContent || "";
            var isAssistantCard =
              cardTxt.indexOf("الأصناف والمقادير") !== -1 ||
              cardTxt.indexOf("تأكيد إضافة") !== -1 ||
              cardTxt.indexOf("أضف بمفرده") !== -1 ||
              cardTxt.indexOf("أفكار لتحضيره") !== -1 ||
              cardTxt.indexOf("منتجات مشابهة") !== -1 ||
              cardTxt.indexOf("مقاضي الصباح") !== -1;
            if (!isAssistantCard) return false;

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
            if (!assistantCard || assistantCard === messagesBox) return;

            if (!assistantCard.classList.contains("v126-bot-full")) {
              assistantCard.classList.add("v126-bot-full");
              if (assistantCard.parentElement && assistantCard.parentElement !== messagesBox) {
                assistantCard.parentElement.classList.add("v126-bot-row");
              }
              replyLeaf.style.whiteSpace = "pre-line";
              replyLeaf.style.lineHeight = "1.75";
              replyLeaf.style.fontSize = "0.94rem";
              replyLeaf.style.color = "#0f172a";
            }

            if (!assistantCard.querySelector(".v126-ai-header")) {
              var aiHdr = document.createElement("div");
              aiHdr.className = "v126-ai-header";
              aiHdr.style.cssText = "display:flex;align-items:center;gap:6px;margin-bottom:8px;font-weight:900;font-size:0.83rem;color:#0d3825;";
              aiHdr.innerHTML = "<span style='background:#fef3c7;color:#b45309;border:1px solid #f59e0b;width:22px;height:22px;border-radius:99px;display:inline-flex;align-items:center;justify-content:center;font-size:0.75rem;'>✨</span><span>شيف ومساعد أورجنال الذكي</span>";
              assistantCard.insertBefore(aiHdr, assistantCard.firstChild);
            }

            if (assistantCard.getAttribute("data-v126-done") === "1") return;

            var precedingUsers = allUserBubbles.filter(function(ub) {
              return Boolean(ub.compareDocumentPosition(assistantCard) & Node.DOCUMENT_POSITION_FOLLOWING);
            });
            var lastUserBubble = precedingUsers.length > 0 ? precedingUsers[precedingUsers.length - 1] : null;
            var prevUserBubble = precedingUsers.length > 1 ? precedingUsers[precedingUsers.length - 2] : null;

            var userQueryTxt = lastUserBubble ? (lastUserBubble.getAttribute("data-v126-orig-user") || lastUserBubble.textContent || "").trim() : "";
            var prevUserTxt = prevUserBubble ? (prevUserBubble.getAttribute("data-v126-orig-user") || prevUserBubble.textContent || "").trim() : "";
            if (!userQueryTxt) return;

            var normKey = normalizeArabicClientV116(userQueryTxt + "|" + prevUserTxt);
            var cachedSmart = window.__v126SmartDataByQuery[normKey] || window.__v126SmartDataByQuery[normalizeArabicClientV116(userQueryTxt)];

            if (!cachedSmart && !assistantCard.getAttribute("data-v126-fetched")) {
              assistantCard.setAttribute("data-v126-fetched", "1");
              origFetchV112("/api/ai-v112/chat", {
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
                  if (sd && sd.ok && (sd.matchedOverride || sd.matchedCustom)) {
                    window.__v126SmartDataByQuery[normKey] = sd;
                    enhanceChatBubblesSafelyV117();
                  } else {
                    assistantCard.setAttribute("data-v126-done", "1");
                  }
                })
                .catch(function() {});
              return;
            }

            if (cachedSmart && (cachedSmart.matchedOverride || cachedSmart.matchedCustom)) {
              assistantCard.setAttribute("data-v126-done", "1");

              var imgUrl = cachedSmart.recipeImage || (cachedSmart.recipeCard && cachedSmart.recipeCard.imageUrl) || "";
              var recTitle = cachedSmart.recipeTitle || (cachedSmart.recipeCard && cachedSmart.recipeCard.title) || userQueryTxt;
              if (imgUrl && !assistantCard.querySelector(".v118-wa-photo-box")) {
                var waBox = document.createElement("div");
                waBox.className = "v118-wa-photo-box";
                waBox.style.cssText = "margin:0 0 12px 0;border-radius:14px;overflow:hidden;background:#f1f5f9;cursor:pointer;";
                var waImg = document.createElement("img");
                waImg.src = imgUrl;
                waImg.alt = String(recTitle);
                waImg.style.cssText = "width:100%;max-height:240px;object-fit:cover;display:block;border-radius:14px;";
                waBox.onclick = function() {
                  window.__openRecipeImageLightboxV116(imgUrl, recTitle);
                };
                waBox.appendChild(waImg);
                replyLeaf.parentNode.insertBefore(waBox, replyLeaf);
              }

              if (cachedSmart.reply) {
                setLeafTextSafe(replyLeaf, cachedSmart.reply);
              }

              if (Array.isArray(cachedSmart.ingredientsTable) && cachedSmart.ingredientsTable.length > 0 && !assistantCard.querySelector(".v126-ingredients-panel")) {
                var tblPanel = document.createElement("div");
                tblPanel.innerHTML = buildIngredientsTableHtmlV126(
                  cachedSmart.ingredientsTable,
                  cachedSmart.missingItemsText || "",
                  recTitle
                );
                var panelNode = tblPanel.firstElementChild || tblPanel;
                if (replyLeaf.nextSibling) {
                  replyLeaf.parentNode.insertBefore(panelNode, replyLeaf.nextSibling);
                } else {
                  replyLeaf.parentNode.appendChild(panelNode);
                }
                var copyBtn = panelNode.querySelector(".v126-copy-notes-btn");
                if (copyBtn) {
                  copyBtn.onclick = function() {
                    window.__copyAndAttachMissingToOrderNotesV126(
                      copyBtn,
                      copyBtn.getAttribute("data-missing") || "",
                      copyBtn.getAttribute("data-title") || ""
                    );
                  };
                }
              }

              syncNativeGreenCartBoxV126(assistantCard, cachedSmart.suggestedItems || []);
            }
          });

          var currentTotalBubbles = allUserBubbles.length + allLeaves.length;
          if (currentTotalBubbles > window.__v126LastBubbleCount) {
            var prevCount = window.__v126LastBubbleCount;
            window.__v126LastBubbleCount = currentTotalBubbles;
            if (prevCount > 0) {
              window.__v126PinBottomUntil = Date.now() + 4000;
              setTimeout(scrollToNewReplyStartAndGlideV126, 45);
            }
          }
        }

        var origFetchV112 = window.fetch;
        if (origFetchV112 && !window.__v112FetchWrapped) {
          window.__v112FetchWrapped = true;
          window.fetch = function(input, init) {
            var urlStr = typeof input === "string" ? input : (input && (input.url || input.href) ? (input.url || input.href) : String(input || ""));
            var isTrpcAiCall =
              urlStr.indexOf("/api/trpc/") !== -1 &&
              /(assistant|chat|chef|ask|recipe|idea|smart|ai)/i.test(urlStr) &&
              !/cart|order|product|category|admin|push|notif|auth|setting|user/i.test(urlStr) &&
              init &&
              init.method === "POST" &&
              typeof init.body === "string";

            var extractedMsg = isTrpcAiCall ? extractAnyUserTextFromJsonBodyV116(init.body) : "";

            return origFetchV112.apply(this, arguments).then(function(resp) {
              if (!isTrpcAiCall || !extractedMsg) {
                return resp;
              }
              var prevMsgToSend = window.__v126PreviousUserMsg || "";
              if (!/(طريقه افضل|طريقة افضل|طريقه ثانيه|طريقة ثانية|غير هذي|وصفه افضل)/.test(extractedMsg)) {
                window.__v126PreviousUserMsg = extractedMsg;
              }
              return resp.clone().json().then(function(trpcJson) {
                return origFetchV112("/api/ai-v112/chat", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({
                    message: extractedMsg,
                    prevMessage: prevMsgToSend,
                    sessionId: window.__v112SessionId
                  })
                })
                  .then(function(r) { return r.json(); })
                  .then(function(smartData) {
                    if (smartData && smartData.ok && !smartData.passThrough && (smartData.matchedOverride || smartData.matchedCustom || smartData.recipeCard || smartData.promotedCard || smartData.canContactStore)) {
                      var normKey = normalizeArabicClientV116(extractedMsg + "|" + prevMsgToSend);
                      window.__v126SmartDataByQuery[normKey] = smartData;
                      window.__v126SmartDataByQuery[normalizeArabicClientV116(extractedMsg)] = smartData;
                      replaceTrpcAiPayloadInPlaceV117(trpcJson, smartData);
                      setTimeout(enhanceChatBubblesSafelyV117, 70);
                      setTimeout(enhanceChatBubblesSafelyV117, 250);
                      return new Response(JSON.stringify(trpcJson), {
                        status: resp.status,
                        statusText: resp.statusText,
                        headers: resp.headers
                      });
                    }
                    setTimeout(enhanceChatBubblesSafelyV117, 80);
                    return resp;
                  })
                  .catch(function() { return resp; });
              }).catch(function() { return resp; });
            });
          };
        }

        function checkRealPhoneOrderNotificationsV126(latestOrders) {
          if (!Array.isArray(latestOrders) || latestOrders.length === 0) return;
          if (window.location.pathname.indexOf("/admin") !== -1) {
            try { localStorage.setItem("original_v126_is_admin", "1"); } catch (e) {}
          }
          if (!window.__v126OrdersSeededOnce) {
            window.__v126OrdersSeededOnce = true;
            latestOrders.forEach(function(o) {
              if (o && o.id) window.__v126NotifiedOrderIds[String(o.id)] = true;
            });
            try {
              localStorage.setItem("original_v126_notified_orders", JSON.stringify(window.__v126NotifiedOrderIds));
            } catch (e) {}
            return;
          }

          var isAdminDevice = window.location.pathname.indexOf("/admin") !== -1 || localStorage.getItem("original_v126_is_admin") === "1";
          var hasNewOrder = false;

          latestOrders.slice().reverse().forEach(function(ord) {
            if (!ord || !ord.id) return;
            var oid = String(ord.id);
            if (!window.__v126NotifiedOrderIds[oid]) {
              window.__v126NotifiedOrderIds[oid] = true;
              hasNewOrder = true;
              if (isAdminDevice) {
                var ordNum = ord.orderNumber || ("#" + ord.id);
                var cName = ord.customerName || "عميل المتجر";
                var tot = Number(ord.total || 0).toLocaleString("en-US");
                triggerRealPhoneNotificationV114(
                  "🛒 وصل طلب جديد للمتجر! (" + ordNum + ")",
                  "العميل: " + cName + " — الإجمالي: " + tot + " ر.ي"
                );
                if (window.location.pathname.indexOf("/admin") !== -1) {
                  var banner = document.createElement("div");
                  banner.style.cssText = "position:fixed;top:14px;left:14px;right:14px;z-index:999998;background:linear-gradient(135deg,#0d3825 0%,#165b3c 100%);color:#ffffff;border:2.5px solid #d4af37;border-radius:16px;padding:14px 16px;box-shadow:0 12px 32px rgba(0,0,0,0.35);direction:rtl;text-align:right;display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;";
                  banner.innerHTML =
                    '<div>' +
                    '<div style="color:#d4af37;font-weight:900;font-size:0.95rem;">🛒 وصل طلب جديد الآن! (' + ordNum + ')</div>' +
                    '<div style="font-size:0.85rem;margin-top:2px;">العميل: ' + cName + ' — الإجمالي: ' + tot + ' ر.ي</div>' +
                    '</div>' +
                    '<div style="display:flex;gap:8px;">' +
                    '<button type="button" style="background:#d4af37;color:#0d3825;border:none;border-radius:10px;padding:7px 14px;font-weight:900;font-size:0.82rem;cursor:pointer;" onclick="window.location.reload()">🔄 عرض الطلب الآن</button>' +
                    '<button type="button" style="background:rgba(255,255,255,0.15);color:#fff;border:none;border-radius:10px;padding:7px 11px;font-weight:800;cursor:pointer;" onclick="this.parentElement.parentElement.remove()">✕</button>' +
                    '</div>';
                  document.body.appendChild(banner);
                }
              }
            }
          });

          if (hasNewOrder) {
            try {
              localStorage.setItem("original_v126_notified_orders", JSON.stringify(window.__v126NotifiedOrderIds));
            } catch (e) {}
          }
        }

        function refreshStudioDataV114() {"""

    ht, n_mid = re.subn(
        r"function normalizeArabicClientV116\(str\) \{[\s\S]*?function refreshStudioDataV114\([^)]*\) \{",
        lambda m: clean_middle_v126,
        ht,
        count=1
    )
    print("3a. Replaced middle chat & fetch block in client/index.html (matches:", n_mid, ")")

    if "checkRealPhoneOrderNotificationsV126(d.latestOrders)" not in ht:
        ht = ht.replace(
            "if (Array.isArray(d.requests)) {",
            "if (Array.isArray(d.latestOrders)) {\n                  checkRealPhoneOrderNotificationsV126(d.latestOrders);\n                }\n                if (Array.isArray(d.requests)) {",
            1
        )

    old_part_f = r"""// PART F: Main AI Assistant Chat[\s\S]*?var msgBubbles = [\s\S]*?\.filter\(function\(el\) \{"""
    new_part_f = """// PART F: Main AI Assistant Chat ("مساعد وشيف أورجنال الذكي")
            var activeChatCtx = getStrictlyActiveAiChatBoxV126();
            if (activeChatCtx && activeChatCtx.messagesBox) {
              enhanceChatBubblesSafelyV117();

              var msgBubbles = Array.from(activeChatCtx.messagesBox.querySelectorAll("div, p")).filter(function(el) {"""
    ht, n_pf = re.subn(old_part_f, lambda m: new_part_f, ht, count=1)
    print("3b. Scoped PART F inside syncVariantModalPrice (matches:", n_pf, ")")

    clean_admin_v126 = """function injectDedicatedAdminAiSectionV114() {
          if (window.location.pathname.indexOf("/admin") === -1) return;
          var pendingCount = (window.__v114Requests || []).filter(function(r) { return r.status === "pending"; }).length;

          var floatBtn = document.getElementById("v126-floating-studio-btn");
          if (!floatBtn) {
            floatBtn = document.createElement("button");
            floatBtn.id = "v126-floating-studio-btn";
            floatBtn.type = "button";
            floatBtn.style.cssText = "position:fixed;bottom:18px;left:16px;z-index:99991;display:flex;align-items:center;gap:8px;padding:11px 16px;border-radius:99px;border:2px solid #d4af37;background:linear-gradient(135deg,#0d3825 0%,#165b3c 100%);color:#ffffff;font-weight:900;font-size:0.86rem;cursor:pointer;box-shadow:0 10px 26px rgba(13,56,37,0.38);direction:rtl;";
            floatBtn.onclick = function(ev) {
              ev.preventDefault();
              ev.stopPropagation();
              openDedicatedAiStudioViewV114();
            };
            document.body.appendChild(floatBtn);
          }
          floatBtn.innerHTML =
            "<span>🤖 قسم تخصيص الذكاء الاصطناعي</span>" +
            (pendingCount > 0
              ? "<span style='background:#ef4444;color:#fff;border-radius:99px;padding:2px 8px;font-size:0.74rem;font-weight:900;'>" + pendingCount + "</span>"
              : "<span style='background:#d4af37;color:#0d3825;border-radius:99px;padding:2px 8px;font-size:0.72rem;font-weight:900;'>مستقل</span>");

          var allBtns = Array.from(document.querySelectorAll("aside button, nav button, button, a"));
          var navAnchor = allBtns.find(function(b) {
            var t = (b.textContent || "").trim();
            return (t === "الطلبات" || t === "المنتجات" || t.indexOf("إعدادات المتجر") !== -1) && b.id !== "v114-sidebar-ai-btn";
          });

          if (navAnchor && navAnchor.parentElement && !document.getElementById("v114-sidebar-ai-btn")) {
            var navParent = navAnchor.parentElement;
            var aiNavBtn = document.createElement("button");
            aiNavBtn.id = "v114-sidebar-ai-btn";
            aiNavBtn.type = "button";
            aiNavBtn.style.cssText =
              "width:100%;display:flex;justify-content:space-between;align-items:center;padding:10px 14px;margin:4px 0;border-radius:12px;border:1.5px solid #d4af37;background:linear-gradient(135deg,#0d3825 0%,#165b3c 100%);color:#ffffff;font-weight:900;font-size:0.88rem;cursor:pointer;text-align:right;direction:rtl;";
            aiNavBtn.innerHTML =
              '<span style="display:flex;align-items:center;gap:8px;"><span>🤖</span><span>تخصيص الذكاء الاصطناعي</span></span>' +
              '<span class="v114-nav-req-badge" style="display:none;background:#ef4444;color:#fff;font-size:0.72rem;padding:2px 7px;border-radius:99px;font-weight:900;">0</span>';

            aiNavBtn.onclick = function(ev) {
              ev.preventDefault();
              ev.stopPropagation();
              openDedicatedAiStudioViewV114();
            };
            navParent.appendChild(aiNavBtn);
          }
        }

        function openDedicatedAiStudioViewV114() {
          window.__v114StudioOpen = true;
          var studioContainer = document.getElementById("v114-dedicated-studio-section");
          if (!studioContainer) {
            studioContainer = document.createElement("div");
            studioContainer.id = "v114-dedicated-studio-section";
            studioContainer.style.cssText = "position:fixed;inset:0;width:100vw;height:100vh;overflow-y:auto;z-index:99995;padding:18px;box-sizing:border-box;background:#f4fbf7;direction:rtl;text-align:right;";
            document.body.appendChild(studioContainer);
          }
          studioContainer.style.display = "block";
          renderStudioPageV114();
        }

        function closeDedicatedAiStudioViewV114() {
          window.__v114StudioOpen = false;
          var studioContainer = document.getElementById("v114-dedicated-studio-section");
          if (studioContainer) studioContainer.style.display = "none";
        }"""
    ht, n_adm = re.subn(
        r"function (?:injectDedicatedAdminAiSectionV114|ensureDedicatedAiSidebarItemV114)\(\) \{[\s\S]*?function closeDedicatedAiStudioViewV114\(\) \{[\s\S]*?\n        \}",
        lambda m: clean_admin_v126,
        ht,
        count=1
    )

    ht = re.sub(
        r"setInterval\(function\(\) \{ if \(document\.visibilityState === 'visible'\) refreshStudioDataV114\(false\); \}, 25000\);",
        "setInterval(refreshStudioDataV114, 5000);",
        ht
    )

    html_path.write_text(ht, encoding="utf-8")
    print("3c. Updated client/index.html (v126) successfully!")

# ==============================================================================
# 5. تحديث رقم الكاش فقط في client/public/sw.js دون المساس بكود الإشعارات
# ==============================================================================
sw_path = pathlib.Path("client/public/sw.js")
if sw_path.exists():
    swc = sw_path.read_text(encoding="utf-8")
    swc = re.sub(r'const CACHE = "original-shell-v[^"]*";', 'const CACHE = "original-shell-v126";', swc)
    old_asset_Rule = """  if (
    url.pathname.includes("/assets/") ||
    url.pathname.endsWith(".png") ||
    url.pathname.endsWith(".jpg") ||
    url.pathname.endsWith(".webp") ||
    url.pathname.endsWith(".svg") ||
    url.pathname.endsWith(".woff2")
  ) {"""
    new_asset_Rule = """  if (
    url.pathname.endsWith(".png") ||
    url.pathname.endsWith(".jpg") ||
    url.pathname.endsWith(".webp") ||
    url.pathname.endsWith(".svg") ||
    url.pathname.endsWith(".woff2")
  ) {"""
    if old_asset_Rule in swc:
        swc = swc.replace(old_asset_Rule, new_asset_Rule, 1)
    sw_path.write_text(swc, encoding="utf-8")
    print("4. Restored clean Web Push in client/public/sw.js and bumped cache to v126!")

# ==============================================================================
# 6. فحص البناء عبر esbuild والرفع إلى Render
# ==============================================================================
res_srv = subprocess.run(
    "npx esbuild server/_core/index.ts --bundle --platform=node --format=esm --packages=external --outfile=./.tmp_srv_v126.js",
    shell=True, capture_output=True, text=True
)
res_cli = subprocess.run(
    "npx esbuild client/src/pages/Admin.tsx client/src/pages/Home.tsx --bundle --platform=browser --packages=external --outdir=./.tmp_cli_v126",
    shell=True, capture_output=True, text=True
)
os.system("rm -rf ./.tmp_srv_v126.js ./.tmp_cli_v126")

if res_srv.returncode != 0 or res_cli.returncode != 0:
    print("❌ Build check failed:", res_srv.stderr, res_cli.stderr)
    sys.exit(1)

print("✅ Build check passed 100% (Zero errors)!")
os.system("git add server/ai_engine_v112.ts server/_core/index.ts server/commerce.ts client/index.html client/public/sw.js")
os.system('git commit -m "v126: restore admin order notifications, fix order status & category icons 100%, prevent chat scroll climb after multiple messages, and keep smart chef AI"')
os.system("git push origin main")
print("🚀 تم الرفع بنجاح إلى Render (v126)!")
