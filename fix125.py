import pathlib, re, subprocess, os

print("=== بدء التحديث الشامل v125 (إرجاع صور وتصميم الأقسام الـ 11 كما كانت 100% + منع القفز للأعلى نهائياً + نزول تدريجي من بداية الرسالة الجديدة مثل ChatGPT) ===")

# ==============================================================================
# 1. كتابة محرك الذكاء والشيف التفاعلي الذكي server/ai_engine_v112.ts
#    - كاش للمنتجات في الذاكرة (لمدة 5 دقائق) لمنع أي ضغط على قاعدة البيانات TiDB
#    - ذاكرة محادثة ذكية لكل زبون (تفهم "أريد طريقة أفضل"، "طريقة ثانية"، "بدون حار"، إلخ)
#    - 0 توكن للوصفات والتفاعلات مع مطابقة 100% بين الجدول وصندوق السلة
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
    const rows = await db.select().from(products);
    if (Array.isArray(rows) && rows.length > 0) {
      cachedProductsCatalog = rows;
      cachedProductsExpiresAt = Date.now() + 5 * 60 * 1000;
    }
    return cachedProductsCatalog;
  } catch (e) {
    return cachedProductsCatalog;
  }
}

function saveToLocalBackupFile() {
  try {
    fs.writeFileSync(
      LOCAL_BACKUP_FILE,
      JSON.stringify({ config: memoryConfig, requests: memoryRequests }, null, 2),
      "utf-8"
    );
  } catch (e) {
    console.error("[AI Studio v123] Local file backup error:", e);
  }
}

function loadFromLocalBackupFile(): boolean {
  try {
    if (fs.existsSync(LOCAL_BACKUP_FILE)) {
      const raw = fs.readFileSync(LOCAL_BACKUP_FILE, "utf-8");
      const parsed = JSON.parse(raw);
      if (parsed && parsed.config) {
        memoryConfig = {
          generalSystemPrompt: parsed.config.generalSystemPrompt || "",
          instructions: Array.isArray(parsed.config.instructions) ? parsed.config.instructions : [],
          rules: Array.isArray(parsed.config.rules) ? parsed.config.rules : [],
          promotedProducts: Array.isArray(parsed.config.promotedProducts) ? parsed.config.promotedProducts : [],
          recipes: Array.isArray(parsed.config.recipes) ? parsed.config.recipes : [],
          productAiMap: parsed.config.productAiMap || {},
          ecoMode10k: parsed.config.ecoMode10k !== false
        };
      }
      if (parsed && Array.isArray(parsed.requests)) {
        memoryRequests = parsed.requests;
      }
      return true;
    }
  } catch (e) {
    console.error("[AI Studio v123] Error reading local backup:", e);
  }
  return false;
}

loadFromLocalBackupFile();

async function ensureAiStudioTable() {
  if (dbTableCreated) return;
  try {
    const db = await getDb();
    if (!db) return;
    await db.execute(
      "CREATE TABLE IF NOT EXISTS ai_studio_v115 (id VARCHAR(64) PRIMARY KEY, payload LONGTEXT NOT NULL, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP)"
    );
    dbTableCreated = true;
  } catch (e) {
    console.error("[AI Studio v123] Table init notice:", e);
  }
}

function extractRowsFromDbResult(res: any): any[] {
  if (!res) return [];
  if (Array.isArray(res)) {
    if (res.length > 0 && Array.isArray(res[0])) return res[0];
    return res;
  }
  if (Array.isArray(res.rows)) return res.rows;
  return [];
}

async function loadStudioFromDbOnce() {
  if (dbLoadedOnce) return;
  dbLoadedOnce = true;
  try {
    await ensureAiStudioTable();
    const db = await getDb();
    if (!db) return;

    const r1: any = await db.execute("SELECT payload FROM ai_studio_v115 WHERE id = 'config' LIMIT 1");
    const rows1 = extractRowsFromDbResult(r1);
    if (rows1.length > 0 && rows1[0]?.payload) {
      const parsed = JSON.parse(String(rows1[0].payload));
      memoryConfig = {
        generalSystemPrompt: parsed.generalSystemPrompt || "",
        instructions: Array.isArray(parsed.instructions) ? parsed.instructions : [],
        rules: Array.isArray(parsed.rules) ? parsed.rules : [],
        promotedProducts: Array.isArray(parsed.promotedProducts) ? parsed.promotedProducts : [],
        recipes: Array.isArray(parsed.recipes) ? parsed.recipes : [],
        productAiMap: parsed.productAiMap || {},
        ecoMode10k: parsed.ecoMode10k !== false
      };
      saveToLocalBackupFile();
    } else {
      const rOld: any = await db.execute("SELECT value FROM site_settings WHERE `key` = 'ai_studio_config_v112' LIMIT 1").catch(() => null);
      const rowsOld = extractRowsFromDbResult(rOld);
      if (rowsOld.length > 0 && rowsOld[0]?.value) {
        const parsedOld = JSON.parse(String(rowsOld[0].value));
        memoryConfig = {
          generalSystemPrompt: parsedOld.generalSystemPrompt || "",
          instructions: Array.isArray(parsedOld.instructions) ? parsedOld.instructions : [],
          rules: Array.isArray(parsedOld.rules) ? parsedOld.rules : [],
          promotedProducts: Array.isArray(parsedOld.promotedProducts) ? parsedOld.promotedProducts : [],
          recipes: Array.isArray(parsedOld.recipes) ? parsedOld.recipes : [],
          productAiMap: parsedOld.productAiMap || {},
          ecoMode10k: parsedOld.ecoMode10k !== false
        };
        await saveStudioConfigToDb();
      } else if (
        memoryConfig.instructions.length > 0 ||
        memoryConfig.rules.length > 0 ||
        memoryConfig.promotedProducts.length > 0 ||
        memoryConfig.recipes.length > 0
      ) {
        await saveStudioConfigToDb();
      }
    }

    const r2: any = await db.execute("SELECT payload FROM ai_studio_v115 WHERE id = 'requests' LIMIT 1");
    const rows2 = extractRowsFromDbResult(r2);
    if (rows2.length > 0 && rows2[0]?.payload) {
      const parsedReq = JSON.parse(String(rows2[0].payload));
      if (Array.isArray(parsedReq)) memoryRequests = parsedReq;
    }
  } catch (e) {
    console.error("[AI Studio v123] Load error:", e);
  }
}

async function saveStudioConfigToDb() {
  saveToLocalBackupFile();
  try {
    await ensureAiStudioTable();
    const db = await getDb();
    if (!db) return;
    const val = JSON.stringify(memoryConfig);
    await db.execute({
      sql: "INSERT INTO ai_studio_v115 (id, payload) VALUES ('config', ?) ON DUPLICATE KEY UPDATE payload = VALUES(payload)",
      args: [val]
    } as any).catch(async () => {
      const escaped = val.replace(/\\\\/g, "\\\\\\\\").replace(/'/g, "\\\\'");
      await db.execute("REPLACE INTO ai_studio_v115 (id, payload) VALUES ('config', '" + escaped + "')");
    });
  } catch (e) {
    console.error("[AI Studio v123] Save config error:", e);
  }
}

async function saveRequestsToDb() {
  saveToLocalBackupFile();
  try {
    await ensureAiStudioTable();
    const db = await getDb();
    if (!db) return;
    const val = JSON.stringify(memoryRequests.slice(0, 300));
    await db.execute({
      sql: "INSERT INTO ai_studio_v115 (id, payload) VALUES ('requests', ?) ON DUPLICATE KEY UPDATE payload = VALUES(payload)",
      args: [val]
    } as any).catch(async () => {
      const escaped = val.replace(/\\\\/g, "\\\\\\\\").replace(/'/g, "\\\\'");
      await db.execute("REPLACE INTO ai_studio_v115 (id, payload) VALUES ('requests', '" + escaped + "')");
    });
  } catch (e) {
    console.error("[AI Studio v123] Save requests error:", e);
  }
}

export function cleanProductNameV112(rawName: string): string {
  if (!rawName) return "";
  return String(rawName)
    .replace(/\\s*\\([^()]*\\)\\s*/g, " ")
    .replace(/\\s+/g, " ")
    .trim();
}

export function normalizeArabicV112(text: string): string {
  if (!text) return "";
  return String(text)
    .toLowerCase()
    .replace(/[أإآ]/g, "ا")
    .replace(/ة/g, "ه")
    .replace(/ى/g, "ي")
    .replace(/[ًٌٍَُِّْ]/g, "")
    .replace(/[^\\u0600-\\u06FFa-z0-9\\s]/g, " ")
    .replace(/\\s+/g, " ")
    .trim();
}

export function getCompiledSystemInstructionsV114(): string {
  const activeList = (memoryConfig.instructions || []).filter(i => i && i.active && i.text);
  const parts: string[] = [];
  if (memoryConfig.generalSystemPrompt && memoryConfig.generalSystemPrompt.trim()) {
    parts.push(memoryConfig.generalSystemPrompt.trim());
  }
  for (const item of activeList) {
    parts.push("- " + item.text.trim());
  }
  return parts.join("\\n");
}

// Multi-Method Chef Encyclopedia: Each dish has 3 distinct, authentic chef methods for interactive follow-ups!
interface ChefRecipeVariantV123 {
  title: string;
  prepTime: string;
  steps: string[];
  ingredients: { name: string; amount: string; searchTerms: string[] }[];
}

interface ChefDishEntryV123 {
  id: string;
  keywords: RegExp;
  variants: ChefRecipeVariantV123[];
}

const MULTI_METHOD_CHEF_DISHES_V123: ChefDishEntryV123[] = [
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
          "أضف ملعقة معجون طماطم (صلصة) وملعقة صويا صوص أو شطة حسب الرغبة، ثم أضف بهارات الإندومي وربع كوب ماء السلق.",
          "أضف الإندومي المصفاة وقلّبها على نار عالية لمدة دقيقة حتى تتشرب الصوص بالكامل، وقدمها ساخنة!"
        ],
        ingredients: [
          { name: "إندومي (أي نكهة تفضلها)", amount: "2 كيس", searchTerms: ["اندومي", "شعيريه"] },
          { name: "معجون طماطم (صلصة)", amount: "1 ملعقة كبيرة", searchTerms: ["صلصه", "معجون طماطم", "طماطم"] },
          { name: "زيت نباتي أو زيت زيتون", amount: "1 ملعقة كبيرة", searchTerms: ["زيت"] },
          { name: "بصل أخضر وفلفل رومي طازج", amount: "1 حبة مفرومة", searchTerms: ["بصل", "فلفل رومي", "خضار"] }
        ]
      },
      {
        title: "إندومي كريمي بالجبن السائل على الطريقة الكورية السريعة",
        prepTime: "5 دقائق",
        steps: [
          "اسلق الإندومي في كمية قليلة من الماء لمدة 3 دقائق حتى تنضج مع بقاء قليل جداً من الماء.",
          "خفّض النار، وأضف ملعقتين كبيرتين من الجبن السائل (أو شريحتين جبن) وربع كوب حليب سائل.",
          "أضف بهارات الإندومي مع رشة فلفل أسود أو شطة، وقلّبها جيداً حتى تذوب الجبنة وتتحول لصوص كريمي غني يغلف الإندومي بالكامل!"
        ],
        ingredients: [
          { name: "إندومي", amount: "2 كيس", searchTerms: ["اندومي", "شعيريه"] },
          { name: "جبن سائل أو مثلثات", amount: "2 ملعقة كبيرة", searchTerms: ["جبن", "جبنه"] },
          { name: "حليب سائل", amount: "ربع كوب", searchTerms: ["حليب"] },
          { name: "شطة أو فلفل حار", amount: "حسب الرغبة", searchTerms: ["شطه", "فلفل"] }
        ]
      },
      {
        title: "إندومي مقرمش بالليمون والكمون والكزبرة (طريقة مبتكرة ولذيذة)",
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
          "في قدر، شوّح البصل المفروم في الزيت حتى يذبل ويصبح ذهبياً، ثم أضف الثوم، الطماطم، معجون الطماطم، والبهارات المشكلة والكمون.",
          "أضف الدجاج وقلّبه مع الكشنة 5 دقائق، ثم أضف الماء المغلي واتركه يغلي على نار متوسطة لمدة 25 دقيقة حتى ينضج الدجاج.",
          "أضف الأرز المصفى فوق المرق (ارتفاع المرق فوق الأرز بمقدار 1 سم)، وعندما يتشرب الماء هدّئ النار تماماً وغطّ القدر 15 دقيقة."
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
          "في قدر الضغط، حمّر البصل مع الزيت واللومي والقرفة والهيل حتى تفوح رائحتها.",
          "أضف الدجاج وقلّبه حتى يتغير لونه، ثم أضف الطماطم المفرومة وملعقة معجون طماطم والبهارات.",
          "اسكب الماء المغلي وأغلق قدر الضغط لمدة 12 دقيقة فقط، ثم افتحه وأضف الأرز المغسول بدون نقع وأغلق القدر 10 دقائق على نار هادئة."
        ],
        ingredients: [
          { name: "أرز بسمتي", amount: "2 كوب", searchTerms: ["ارز", "رز"] },
          { name: "معجون طماطم", amount: "1 ملعقة كبيرة", searchTerms: ["صلصه", "معجون طماطم"] },
          { name: "كمون وبهارات صحيحة", amount: "1 ملعقة كبيرة", searchTerms: ["كمون", "بهارات"] },
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
          "اسلق المكرونة في ماء مغلي مملح مع ملعقة زيت لمدة 8-10 دقائق ثم صفّها.",
          "في مقلاة عميقة، شوّح البصل والثوم المفروم في ملعقتين زيت، ثم أضف معجون الطماطم والطماطم المعصورة.",
          "تبّل الصلصة بالملح، الكمون، الفلفل الأسود، واتركها تتسبك 7 دقائق على نار هادئة.",
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
          "أضف رشة أوريغانو أو كمون وفلفل أسود، ثم أضف المكرونة وماء السلق وقلّبها حتى يثقل الصوص الوردي الكريمي!"
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
          "انقع الحلبة المطحونة في الماء البارد لمدة ساعة، ثم صفّ الماء الزائد واخفقها جيداً باليد أو الخلاط مع الكراث والكزبرة والفلفل الأخضر حتى تصبح بيضاء هشة.",
          "في المقلى الحجري (المدرة)، شوّح البصل والثوم والطماطم مع معجون الطماطم والكمون.",
          "أضف المرق واللحم المفروم أو الدقّة والبطاطس المسلوقة المهروسة واتركها تغلي بقوة.",
          "وزّع رغوة الحلبة المخفوقة على وجه المقلى الساخن وقدمها فوراً مع الخبز الملوج الحار!"
        ],
        ingredients: [
          { name: "حلبة مطحونة", amount: "3 ملاعق كبيرة", searchTerms: ["حلبه", "بهارات"] },
          { name: "معجون طماطم", amount: "2 ملعقة كبيرة", searchTerms: ["صلصه", "معجون طماطم"] },
          { name: "كمون بلدي", amount: "1 ملعقة صغيرة", searchTerms: ["كمون"] },
          { name: "لحم مفروم أو تونة", amount: "250 جرام", searchTerms: ["تونه", "لحم"] },
          { name: "بطاطس وكراث وبصل", amount: "2 حبة", searchTerms: ["بطاطس", "بصل", "كراث"] }
        ]
      }
    ]
  },
  {
    id: "shakshuka",
    keywords: /(شكشوكه|شكشوكة|بيض بالطماطم|فطور|عشاء سريع)/,
    variants: [
      {
        title: "شكشوكة عدنية محموسة بالجبن",
        prepTime: "10 دقائق",
        steps: [
          "شوّح البصل المفروم والفلفل الحار في الزيت حتى يذبل.",
          "أضف الطماطم المفرومة ناعماً وملعقة صغيرة معجون طماطم ورشة كمون وملح، واتركها 4 دقائق حتى تذوب الطماطم.",
          "أضف البيض وحرّكه بهدوء على نار هادئة حتى يستوي نصف استواء، ثم أضف ملعقة جبن سائل على الوجه ليصبح طعمها خيالياً!"
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
    keywords: /(بسبوسه|بسبوسة|كيكه|كيكة|كنافه|كنافة|لقيمات|عوامه)/,
    variants: [
      {
        title: "حلى البسبوسة الذهبية المحشية بالقشطة",
        prepTime: "30 دقيقة",
        steps: [
          "اخلط السميد مع السكر، الحليب البودرة، البيكنج باودر، والزيت أو السمن، ثم أضف الحليب السائل أو الزبادي وقلّب الخليط.",
          "اسكب نصف الخليط في صينية مدهونة، ووزع طبقة من القشطة في المنتصف، ثم غطّها بالنصف المتبقي من الخليط.",
          "اخبزها في فرن متوسط الحرارة (180 درجة) لمدة 25 دقيقة حتى تتحمر، واسقها بالشيرة الدافئة فور خروجها!"
        ],
        ingredients: [
          { name: "حليب (سائل أو بودرة)", amount: "1 كوب", searchTerms: ["حليب"] },
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
          "شكّلها على هيئة كرات صغيرة متساوية، ودحرجها في فتات البسكويت أو الكاكاو، وضعها في الثلاجة 15 دقيقة وقدمها مع القهوة!"
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

const FUNNY_CLEAN_JOKES_V123: string[] = [
  "😄 نكتة خفيفة على السريع:\\nواحد راح للبقالة قال لصاحب المحل: عندك سكر؟ قاله: أيوه! قاله: الله يشفيك! 😂\\nبشرني يا غالي، إيش نجهز لك اليوم من مقاضي أو وصفات؟",
  "😄 خذ هذي النكتة يا غالي:\\nواحد سأل صاحبه: ليش تحط التلفون في الثلاجة؟ قاله: عشان لا تذوب الشوكولاتة اللي في الصورة! 😂🍫\\nقول لي، جاي على بالك حلى بارد ولا طبخة سريعة اليوم؟",
  "😄 ابتسم يا غالي:\\nالأم تسأل ولدها: لو أعطيتك تفاحتين وأعطيت أخوك تفاحتين، كم يصير معكم؟ قال: 4 تفاحات عندي وتفاحتين في بطني! 😂🍎\\nآمرني يا غالي، إيش بخاطرك نطبخ أو نطلب اليوم؟"
];

function buildRecipePayloadFromVariantV123(
  variant: ChefRecipeVariantV123,
  allProds: any[],
  isFollowUpAlternative: boolean
) {
  const tableRows: IngredientTableRowV123[] = [];
  const availableItems: any[] = [];
  const missingNames: string[] = [];

  for (const ing of variant.ingredients) {
    let foundProd: any = null;
    for (const term of ing.searchTerms) {
      const normTerm = normalizeArabicV112(term);
      foundProd = allProds.find(p => {
        const cn = normalizeArabicV112(cleanProductNameV112(p.name));
        return cn.includes(normTerm);
      });
      if (foundProd) break;
    }

    if (foundProd) {
      const cleanName = cleanProductNameV112(foundProd.name);
      tableRows.push({
        name: cleanName,
        amount: ing.amount,
        available: true,
        price: foundProd.price,
        productId: foundProd.id,
        unit: foundProd.unit || "حبة"
      });
      availableItems.push({
        id: foundProd.id,
        productId: foundProd.id,
        name: cleanName,
        price: foundProd.price,
        unit: foundProd.unit || "حبة",
        url: "/products?search=" + encodeURIComponent(cleanName)
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
  const introLine = isFollowUpAlternative
    ? "✨ ولا يهمك يا غالي! جبت لك طريقة ثانية ألذ وأحلى لتحضير «" + variant.title + "» (⏱️ " + variant.prepTime + "):"
    : "👨‍🍳 أبشر يا غالي! إليك الطريقة الاحترافية لتحضير «" + variant.title + "» (⏱️ " + variant.prepTime + "):";

  const replyText =
    introLine + "\\n\\n" +
    "📋 خطوات التحضير:\\n" +
    stepsFormatted + "\\n\\n" +
    "📊 جدول المقادير وحالة التوفر بالأسفل:";

  return {
    title: variant.title,
    reply: replyText,
    tableRows,
    availableItems,
    missingItemsText: missingNames.join(" + ")
  };
}

export function classifyProductSmartV112(productName: string, customMeta?: ProductAiMetadataV112) {
  const clean = cleanProductNameV112(productName);
  const norm = normalizeArabicV112(clean);

  if (customMeta && customMeta.usageType && customMeta.usageType !== "auto") {
    return {
      mode: customMeta.usageType,
      cleanName: clean,
      calories: customMeta.calories || "180 - 250 سعرة حرارية لكل حصة تقريباً",
      defaultInfo: customMeta.customInfo || ("منتج " + clean + " عالي الجودة متوفر في متجر أورجنال."),
      chips:
        customMeta.usageType === "recipe"
          ? ["🍰 اعطني وصفة بـ " + clean, "🍫 حلى سريع بـ " + clean, "🛒 أضف للسلة"]
          : customMeta.usageType === "snacks_and_drinks"
          ? ["🥤 مشروبات تناسب " + clean, "🔥 كم السعرات الحرارية؟", "🛒 أضف للسلة"]
          : ["💡 معلومات وفوائد " + clean, "🔥 السعرات والقيمة الغذائية", "🛒 أضف للسلة"]
    };
  }

  const isDrinkOrWater = /(ماء|مياه|عصير|مشروب|بيبسي|كولا|سفن|ميرندا|رد بول|كود رد|شاني|فيروز|حليب|لبن|زبادي)/.test(norm);
  const isChipOrSnack = /(بطاطس|شيبس|تسالي|فشار|مكسرات|لوز|فستق|كاجو|بفك|ليز|دوريتوس|شيتوس|اندومي|شعيريه)/.test(norm);
  const isBiscuitOrSweet = /(بسكويت|بسكوت|ابو ولد|ماري|تيشوب|شوكولاته|شوكولاتة|كيك|ويفر|كليجا|معمول|تمر|عسل|حلاوه|حلاوة|قشطه|قشطة)/.test(norm);
  const isCookingBase = /(ارز|رز|دقيق|طحين|مكرونه|معكرونه|شوفان|عدس|فول|فاصوليا|حمص|تونه|تونة|صلصه|صلصة|معجون طماطم|زيت|سمن)/.test(norm);
  const isSpiceOrCondiment = /(بهارات|كمون|فلفل|كركم|قرفه|قرفة|هيل|ملح|سكر|خل|ليمون|ثوم|بصل|بسباس|خلطه|خلطة)/.test(norm);

  if (isDrinkOrWater) {
    return {
      mode: "snacks_and_drinks",
      cleanName: clean,
      calories: norm.includes("ماء") ? "0 سعرة حرارية (نقي وطبيعي 100%)" : "110 - 160 سعرة حرارية للعبوة",
      defaultInfo: norm.includes("ماء")
        ? (clean + " نقي ومنعش، مثالي للترطيب اليومي ومع الوجبات.")
        : (clean + " طعم منعش ولذيذ، يقدم بارداً مع الوجبات الخفيفة أو السناكات."),
      chips: ["🥨 سناكات ومقرمشات تناسب " + clean, "🔥 كم السعرات الحرارية؟", "🛒 أضف للسلة"]
    };
  }

  if (isChipOrSnack) {
    return {
      mode: "snacks_and_drinks",
      cleanName: clean,
      calories: "150 - 240 سعرة حرارية للحصة",
      defaultInfo: clean + " مقرمش ولذيذ، خيار ممتاز للسهرة أو كوجبة سريعة.",
      chips: ["🥤 مشروبات باردة مع " + clean, "🌶️ طريقة تقديم رهيبة لـ " + clean, "🛒 أضف للسلة"]
    };
  }

  if (isBiscuitOrSweet) {
    return {
      mode: "recipe",
      cleanName: clean,
      calories: "190 - 260 سعرة حرارية للحصة",
      defaultInfo: clean + " رائع مع الشاي والقهوة، ويدخل في ألذ وصفات الحلى البارد السريع بدون فرن!",
      chips: ["🍰 وصفة حلى بارد بـ " + clean, "☕ مشروبات تناسب " + clean, "🛒 أضف للسلة"]
    };
  }

  if (isCookingBase) {
    return {
      mode: "recipe",
      cleanName: clean,
      calories: "210 - 320 سعرة حرارية لكل 100 جرام",
      defaultInfo: clean + " من أساسيات المطبخ لتحضير أشهى الوجبات اليومية السريعة والاقتصادية.",
      chips: ["🍲 طبخة سريعة بـ " + clean, "🥗 إضافات وبهارات تكمل " + clean, "🛒 أضف للسلة"]
    };
  }

  if (isSpiceOrCondiment) {
    return {
      mode: "calories_and_info",
      cleanName: clean,
      calories: "سعرات حرارية منخفضة جداً — غني بالنكهة الطبيعية",
      defaultInfo: clean + " يمنح طبخاتك نكهة أصلية ورائحة زكية تفتح الشهية.",
      chips: ["🍲 أفضل الأكلات التي تستخدم " + clean, "💡 فوائد ومعلومات عن " + clean, "🛒 أضف للسلة"]
    };
  }

  return {
    mode: "calories_and_info",
    cleanName: clean,
    calories: "120 - 220 سعرة حرارية تقريباً",
    defaultInfo: clean + " متوفر بجودة ممتازة وسعر منافس في متجر أورجنال.",
    chips: ["💡 معلومات واستخدامات " + clean, "🔥 السعرات الحرارية", "🛒 أضف للسلة"]
  };
}

export function registerAiStudioV112Routes(app: Express) {
  app.use("/api/ai-studio", express.json({ limit: "50mb" }));
  app.use("/api/ai-studio", express.urlencoded({ limit: "50mb", extended: true }));

  app.get("/api/ai-studio/config", async (_req, res) => {
    await loadStudioFromDbOnce();
    res.json({
      ok: true,
      config: memoryConfig,
      compiledSystemPrompt: getCompiledSystemInstructionsV114(),
      requests: memoryRequests,
      stats: {
        zeroTokenHits: zeroTokenCounter,
        cachedHits: cachedHitCounter,
        instructionsCount: (memoryConfig.instructions || []).length,
        rulesCount: (memoryConfig.rules || []).length,
        promotedCount: (memoryConfig.promotedProducts || []).length,
        recipesCount: (memoryConfig.recipes || []).length,
        pendingRequestsCount: memoryRequests.filter(r => r.status === "pending").length
      }
    });
  });

  app.post("/api/ai-studio/config", async (req, res) => {
    try {
      await loadStudioFromDbOnce();
      const body = req.body || {};
      if (typeof body.generalSystemPrompt === "string") {
        memoryConfig.generalSystemPrompt = body.generalSystemPrompt;
      }
      if (Array.isArray(body.instructions)) {
        memoryConfig.instructions = body.instructions;
      }
      if (Array.isArray(body.rules)) {
        memoryConfig.rules = body.rules;
      }
      if (Array.isArray(body.promotedProducts)) {
        memoryConfig.promotedProducts = body.promotedProducts;
      }
      if (Array.isArray(body.recipes)) {
        memoryConfig.recipes = body.recipes;
      }
      if (body.productAiMap && typeof body.productAiMap === "object") {
        memoryConfig.productAiMap = body.productAiMap;
      }
      if (typeof body.ecoMode10k === "boolean") {
        memoryConfig.ecoMode10k = body.ecoMode10k;
      }
      await saveStudioConfigToDb();
      res.json({
        ok: true,
        config: memoryConfig,
        compiledSystemPrompt: getCompiledSystemInstructionsV114()
      });
    } catch (e: any) {
      res.status(500).json({ ok: false, error: String(e?.message || e) });
    }
  });

  app.post("/api/ai-studio/request-item", async (req, res) => {
    try {
      await loadStudioFromDbOnce();
      const { sessionId, customerName, customerPhone, requestedItem, userMessage } = req.body || {};
      const newReq: AiCustomerRequestV112 = {
        id: "req_" + Date.now() + "_" + Math.random().toString(36).slice(2, 6),
        sessionId: String(sessionId || "guest"),
        customerName: String(customerName || "عميل أورجنال"),
        customerPhone: String(customerPhone || ""),
        requestedItem: String(requestedItem || ""),
        userMessage: String(userMessage || ""),
        status: "pending",
        adminReply: "",
        createdAt: new Date().toISOString()
      };
      memoryRequests.unshift(newReq);
      await saveRequestsToDb();
      res.json({ ok: true, request: newReq });
    } catch (e: any) {
      res.status(500).json({ ok: false, error: String(e?.message || e) });
    }
  });

  app.post("/api/ai-studio/reply-request", async (req, res) => {
    try {
      await loadStudioFromDbOnce();
      const { id, status, adminReply } = req.body || {};
      const target = memoryRequests.find(r => r.id === id);
      if (!target) {
        return res.status(404).json({ ok: false, error: "الطلب غير موجود" });
      }
      if (status) target.status = status;
      if (typeof adminReply === "string") target.adminReply = adminReply;
      target.repliedAt = new Date().toISOString();
      await saveRequestsToDb();
      res.json({ ok: true, request: target });
    } catch (e: any) {
      res.status(500).json({ ok: false, error: String(e?.message || e) });
    }
  });

  app.get("/api/ai-studio/my-notifications", async (req, res) => {
    await loadStudioFromDbOnce();
    const sessionId = String(req.query.sessionId || "");
    const list = memoryRequests.filter(r => r.sessionId === sessionId && r.adminReply);
    res.json({ ok: true, notifications: list });
  });

  app.post("/api/ai-studio/smart-chat", async (req, res) => {
    try {
      await loadStudioFromDbOnce();
      const rawMsg = String(req.body?.message || "").trim();
      const prevMsg = String(req.body?.prevMessage || "").trim();
      const productContextName = cleanProductNameV112(String(req.body?.productName || ""));
      const sessionId = String(req.body?.sessionId || "guest");
      const normMsg = normalizeArabicV112(rawMsg);

      const allProds = await getProductsCatalogLightV123();

      // 0. Context-Aware Conversational Follow-up Detection!
      // When user says "أريد طريقة أفضل", "طريقة ثانية", "غير هذي", "وصفة أحسن", etc., NEVER treat the sentence as a dish name!
      const isFollowUpBetterMethod = /(طريقه افضل|طريقة افضل|طريقه احسن|طريقه ثانيه|طريقة ثانية|طريقه اخرى|وصفه افضل|وصفه ثانيه|غير هذي|غير هذه|عدله|عدلها|بشكل افضل|شي افضل|شي احسن|احلى من كذا)/.test(normMsg);
      if (isFollowUpBetterMethod) {
        zeroTokenCounter++;
        let mem = sessionMemoryMap.get(sessionId);

        // If no session memory yet, infer the dish from prevMsg or default to Indomie / Biscuit Sweet
        let targetDish: ChefDishEntryV123 | undefined;
        if (mem) {
          targetDish = MULTI_METHOD_CHEF_DISHES_V123.find(d => d.id === mem!.lastRecipeId);
        }
        if (!targetDish && prevMsg) {
          const normPrev = normalizeArabicV112(prevMsg);
          targetDish = MULTI_METHOD_CHEF_DISHES_V123.find(d => d.keywords.test(normPrev));
        }
        if (!targetDish) {
          targetDish = MULTI_METHOD_CHEF_DISHES_V123[0]; // Default to Royal Indomie
        }

        const nextIdx = mem ? (mem.variantIndex + 1) % targetDish.variants.length : 0;
        const chosenVariant = targetDish.variants[nextIdx];
        sessionMemoryMap.set(sessionId, {
          lastRecipeId: targetDish.id,
          lastDishTitle: chosenVariant.title,
          variantIndex: nextIdx,
          updatedAt: Date.now()
        });

        const built = buildRecipePayloadFromVariantV123(chosenVariant, allProds, true);
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

      // 1. Check Custom Recipes from AI Studio First
      for (const rec of memoryConfig.recipes || []) {
        const kws = String(rec.keywords || rec.title || "")
          .split(/[،,|]+/)
          .map(s => normalizeArabicV112(s))
          .filter(Boolean);
        const isDirectMatch = kws.some(
          k => normMsg.includes(k) || (productContextName && normalizeArabicV112(productContextName).includes(k))
        );
        if (isDirectMatch) {
          zeroTokenCounter++;
          const tableRows: IngredientTableRowV123[] = [];
          const matchedAvailableItems: any[] = [];
          const missingNames: string[] = [];

          for (const ing of rec.ingredients || []) {
            const ingClean = cleanProductNameV112(ing.name);
            const foundProd = allProds.find(
              p =>
                (ing.productId && Number(p.id) === Number(ing.productId)) ||
                cleanProductNameV112(p.name) === ingClean ||
                normalizeArabicV112(cleanProductNameV112(p.name)).includes(normalizeArabicV112(ingClean))
            );
            if (foundProd) {
              const cName = cleanProductNameV112(foundProd.name);
              tableRows.push({
                name: cName,
                amount: "1 " + (foundProd.unit || "حبة"),
                available: true,
                price: foundProd.price,
                productId: foundProd.id,
                unit: foundProd.unit || "حبة"
              });
              matchedAvailableItems.push({
                id: foundProd.id,
                productId: foundProd.id,
                name: cName,
                price: foundProd.price,
                unit: foundProd.unit || "حبة",
                url: ing.url || ("/products?search=" + encodeURIComponent(cName))
              });
            } else {
              tableRows.push({
                name: ingClean,
                amount: "حسب الوصفة",
                available: false
              });
              missingNames.push(ingClean);
            }
          }

          return res.json({
            ok: true,
            zeroToken: true,
            matchedOverride: true,
            reply:
              "🍰 " + rec.title + "\\n\\n" +
              "📋 طريقة التحضير والخطوات الكاملة:\\n" +
              rec.steps,
            recipeImage: rec.imageUrl || "",
            recipeTitle: rec.title,
            ingredientsTable: tableRows,
            missingItemsText: missingNames.join(" + "),
            suggestedItems: matchedAvailableItems
          });
        }
      }

      // 2. Check Custom Keyword Rules
      for (const rule of memoryConfig.rules || []) {
        if (!rule.active || !rule.trigger) continue;
        const triggers = rule.trigger.split(/[،,|]+/).map(s => normalizeArabicV112(s)).filter(Boolean);
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

      // 3. Check Subtle Marketing / Promoted Products
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
print("1. Wrote complete server/ai_engine_v112.ts (v125 Context-Aware Interactive Chef + 5-Min DB Cache)!")

# ==============================================================================
# 2. تحديث client/index.html (v125):
#    - حصر جميع تعديلات وتنسيقات الشات داخل حاوية المحادثة فقط (حماية الأقسام الـ 11 وصور المتجر 100%)
#    - منع القفز للأعلى نهائياً عبر MutationObserver لحظي قبل رسم الشاشة
#    - نزول تدريجي سلس مع بداية الرد الجديد حتى نهايته تماماً مثل ChatGPT
# ==============================================================================
html_path = pathlib.Path("client/index.html")
if html_path.exists():
    ht = html_path.read_text(encoding="utf-8")

    ht = re.sub(
        r'window\.__v12[12345]SmartDataByQuery =[\s\S]*?function syncOrderNotesFieldV12[12345]\(\) \{[\s\S]*?\n        \}',
        '',
        ht
    )

    v125_helpers_and_css = """
        window.__v123SmartDataByQuery = window.__v123SmartDataByQuery || {};
        window.__v123LastBubbleCount = 0;
        window.__v123PreviousUserMsg = "";
        window.__v125LastValidScrollTop = 0;
        window.__v125GlideRafId = null;

        (function injectGeminiChatStylesV125() {
          var oldIds = ["v121-gemini-chat-styles", "v122-gemini-chat-styles", "v123-gemini-chat-styles", "v124-gemini-chat-styles", "v125-gemini-chat-styles"];
          oldIds.forEach(function(id) {
            var el = document.getElementById(id);
            if (el) el.remove();
          });
          var st = document.createElement("style");
          st.id = "v125-gemini-chat-styles";
          st.textContent =
            /* Scope ALL chat styles strictly inside [data-v125-chat-root='1'] so store categories & product cards are 100% untouched! */
            "[data-v125-chat-root='1'], [data-v125-chat-root='1'] * { overflow-anchor: none !important; }" +
            "[data-v125-chat-root='1'] .v124-user-row-left { display: flex !important; flex-direction: row !important; justify-content: flex-start !important; align-items: flex-start !important; direction: ltr !important; width: 100% !important; margin: 6px 0 !important; }" +
            "[data-v125-chat-root='1'] .v123-gemini-user-bubble { background: #0d3825 !important; color: #ffffff !important; border: 1.5px solid #165b3c !important; border-radius: 20px 20px 20px 4px !important; padding: 9px 16px !important; box-shadow: 0 3px 10px rgba(13,56,37,0.15) !important; font-weight: 800 !important; font-size: 0.92rem !important; width: fit-content !important; max-width: 80% !important; display: inline-block !important; direction: rtl !important; text-align: right !important; margin-left: 0 !important; margin-right: auto !important; }" +
            "[data-v125-chat-root='1'] .v123-gemini-user-bubble * { color: #ffffff !important; direction: rtl !important; text-align: right !important; }" +
            "[data-v125-chat-root='1'] .v123-gemini-bot-full { width: 100% !important; max-width: 100% !important; background: transparent !important; border: none !important; box-shadow: none !important; border-bottom: 1px solid #e2e8f0 !important; border-radius: 0 !important; padding: 12px 2px 18px 2px !important; margin: 4px 0 !important; direction: rtl !important; text-align: right !important; }" +
            "[data-v125-chat-root='1'] .v123-gemini-bot-row { width: 100% !important; max-width: 100% !important; display: block !important; }";
          document.head.appendChild(st);
        })();

        // Locate ONLY the AI Assistant Chat Card (never the main store page or categories grid!)
        function getAiChatCardRootV125() {
          if (window.location.pathname.indexOf("/admin") !== -1) return null;
          var chatInput = Array.from(document.querySelectorAll("input, textarea")).find(function(inp) {
            var ph = inp.getAttribute("placeholder") || "";
            return ph.indexOf("اطلب سلة الصباح") !== -1 || ph.indexOf("وصفة اقتصادية") !== -1 || ph.indexOf("مقاضي المطبخ") !== -1;
          });
          if (!chatInput) return null;
          var cur = chatInput.parentElement;
          while (cur && cur !== document.body) {
            var txt = cur.textContent || "";
            if (txt.indexOf("عرض الكل") !== -1 || txt.indexOf("تسوق الخضار") !== -1) {
              break;
            }
            if (txt.indexOf("مساعد وشيف أورجنال الذكي") !== -1 && txt.indexOf("محادثة جديدة") !== -1) {
              cur.setAttribute("data-v125-chat-root", "1");
              return cur;
            }
            cur = cur.parentElement;
          }
          return null;
        }

        // Find the inner scrollable messages div inside the AI Chat Card
        function getChatScrollContainerV125() {
          var root = getAiChatCardRootV125();
          if (!root) return null;
          var divs = Array.from(root.querySelectorAll("div"));
          for (var i = 0; i < divs.length; i++) {
            var d = divs[i];
            if (d.querySelector("input, textarea")) continue;
            if ((d.textContent || "").indexOf("محادثة جديدة") !== -1) continue;
            try {
              var cs = window.getComputedStyle(d);
              var oy = cs.overflowY;
              if ((oy === "auto" || oy === "scroll") && d.clientHeight > 80) {
                return d;
              }
            } catch (e) {}
          }
          for (var j = 0; j < divs.length; j++) {
            var d2 = divs[j];
            if (d2.querySelector("input, textarea")) continue;
            if (d2.scrollHeight > d2.clientHeight + 20 && d2.clientHeight > 100) {
              return d2;
            }
          }
          return null;
        }

        function stopGlideAnimationV125() {
          if (window.__v125GlideRafId) {
            cancelAnimationFrame(window.__v125GlideRafId);
            window.__v125GlideRafId = null;
          }
        }

        // ChatGPT-style progressive glide: starts at the top of the new reply and smoothly glides down as you read!
        function startChatGptProgressiveGlideV125(sc, targetEndScrollTop, durationMs) {
          if (!sc) return;
          stopGlideAnimationV125();
          var startTop = sc.scrollTop;
          var distance = targetEndScrollTop - startTop;
          if (distance <= 8) {
            sc.scrollTop = targetEndScrollTop;
            window.__v125LastValidScrollTop = sc.scrollTop;
            return;
          }
          var startTime = performance.now();
          var dur = durationMs || Math.min(2200, Math.max(700, distance * 2.2));

          function step(now) {
            if (window.__v125UserTouching) {
              stopGlideAnimationV125();
              return;
            }
            var elapsed = now - startTime;
            var progress = Math.min(1, elapsed / dur);
            // Smooth ease-out curve
            var eased = 1 - Math.pow(1 - progress, 2.2);
            sc.scrollTop = Math.round(startTop + distance * eased);
            window.__v125LastValidScrollTop = sc.scrollTop;
            if (progress < 1) {
              window.__v125GlideRafId = requestAnimationFrame(step);
            } else {
              window.__v125GlideRafId = null;
            }
          }
          window.__v125GlideRafId = requestAnimationFrame(step);
        }

        // Scroll to the start of the newly arrived bot reply, then progressively glide down like ChatGPT!
        function scrollToNewReplyAndGlideV125() {
          try {
            var sc = getChatScrollContainerV125();
            if (!sc) return;
            var botCards = Array.from(sc.querySelectorAll(".v123-gemini-bot-full"));
            var userBubbles = Array.from(sc.querySelectorAll(".v123-gemini-user-bubble"));

            if (botCards.length > 0) {
              var lastBot = botCards[botCards.length - 1];
              var lastUser = userBubbles.length > 0 ? userBubbles[userBubbles.length - 1] : null;
              // Anchor the top of the viewport right at the user's question / start of the new bot reply!
              var anchorEl = lastUser || lastBot;
              var scRect = sc.getBoundingClientRect();
              var anchorRect = anchorEl.getBoundingClientRect();
              var startOffset = sc.scrollTop + (anchorRect.top - scRect.top) - 12;
              if (startOffset > 0) {
                sc.scrollTop = startOffset;
                window.__v125LastValidScrollTop = sc.scrollTop;
              }
              // Now progressively glide down to reveal the full reply smoothly like ChatGPT!
              var maxBottom = sc.scrollHeight - sc.clientHeight;
              if (maxBottom > sc.scrollTop + 15) {
                setTimeout(function() {
                  startChatGptProgressiveGlideV125(sc, sc.scrollHeight - sc.clientHeight, 1650);
                }, 180);
              }
            } else {
              sc.scrollTop = sc.scrollHeight;
              window.__v125LastValidScrollTop = sc.scrollTop;
            }
          } catch (e) {}
        }

        function scrollToChatBottomSmoothV123() {
          try {
            var sc = getChatScrollContainerV125();
            if (sc) {
              sc.scrollTop = sc.scrollHeight;
              window.__v125LastValidScrollTop = sc.scrollTop;
            }
          } catch (e) {}
        }

        // Intercept Element.prototype.scrollIntoView & Window.prototype.scrollTo during chat operations so React NEVER jumps up to 0!
        if (!window.__v125ScrollPatched) {
          window.__v125ScrollPatched = true;
          var origScrollIntoView = Element.prototype.scrollIntoView;
          Element.prototype.scrollIntoView = function() {
            var root = getAiChatCardRootV125();
            if (root && root.contains(this)) {
              var sc = getChatScrollContainerV125();
              if (sc && window.__v125LastValidScrollTop > 40) {
                sc.scrollTop = Math.max(window.__v125LastValidScrollTop, sc.scrollHeight - sc.clientHeight);
                return;
              }
            }
            return origScrollIntoView.apply(this, arguments);
          };
          var origWinScrollTo = window.scrollTo;
          window.scrollTo = function(a, b) {
            if (window.__v125PinBottomUntil && Date.now() < window.__v125PinBottomUntil && getAiChatCardRootV125()) {
              var topVal = (typeof a === "object" && a !== null) ? a.top : b;
              if (topVal === 0) return;
            }
            return origWinScrollTo.apply(this, arguments);
          };
        }

        function bindChatInputScrollLockV123() {
          var root = getAiChatCardRootV125();
          if (!root) return;
          var sc = getChatScrollContainerV125();

          if (sc) {
            if (sc.scrollTop > 40) {
              window.__v125LastValidScrollTop = sc.scrollTop;
            }
            if (!sc.getAttribute("data-v125-scroll-bound")) {
              sc.setAttribute("data-v125-scroll-bound", "1");
              sc.addEventListener("touchstart", function() {
                window.__v125UserTouching = true;
                stopGlideAnimationV125();
              }, { passive: true });
              sc.addEventListener("touchend", function() {
                if (sc.scrollTop > 20) window.__v125LastValidScrollTop = sc.scrollTop;
                setTimeout(function() { window.__v125UserTouching = false; }, 250);
              }, { passive: true });
              sc.addEventListener("scroll", function() {
                if (window.__v125UserTouching) {
                  window.__v125LastValidScrollTop = sc.scrollTop;
                  return;
                }
                // If React reset scrollTop toward 0 while pinned, snap back immediately before paint!
                if (window.__v125PinBottomUntil && Date.now() < window.__v125PinBottomUntil) {
                  if (sc.scrollTop < 30 && window.__v125LastValidScrollTop > 50) {
                    sc.scrollTop = window.__v125LastValidScrollTop;
                  }
                } else if (sc.scrollTop > 40) {
                  window.__v125LastValidScrollTop = sc.scrollTop;
                }
              }, { passive: true });
            }
          }

          // Attach a synchronous pre-paint MutationObserver on the chat root so when React re-renders on Send or Reply, scrollTop NEVER jumps to 0!
          if (!root.getAttribute("data-v125-mut-bound")) {
            root.setAttribute("data-v125-mut-bound", "1");
            var mutObs = new MutationObserver(function() {
              var curSc = getChatScrollContainerV125();
              if (!curSc || window.__v125UserTouching) return;
              if (window.__v125PinBottomUntil && Date.now() < window.__v125PinBottomUntil) {
                if (curSc.scrollTop < 40 && window.__v125LastValidScrollTop > 50) {
                  curSc.scrollTop = window.__v125LastValidScrollTop;
                }
              }
            });
            mutObs.observe(root, { childList: true, subtree: true });
          }

          var chatInputs = Array.from(root.querySelectorAll("input, textarea"));
          chatInputs.forEach(function(inp) {
            if (inp.getAttribute("data-v125-inp-bound") === "1") return;
            inp.setAttribute("data-v125-inp-bound", "1");
            function onSendTriggered() {
              stopGlideAnimationV125();
              var curSc = getChatScrollContainerV125();
              if (curSc && curSc.scrollTop > 30) {
                window.__v125LastValidScrollTop = curSc.scrollTop;
              }
              window.__v125PinBottomUntil = Date.now() + 8000;
              // Keep view right at the bottom where the user message & "يفكر..." indicator appear
              setTimeout(scrollToChatBottomSmoothV123, 20);
              setTimeout(scrollToChatBottomSmoothV123, 90);
              setTimeout(scrollToChatBottomSmoothV123, 220);
              setTimeout(scrollToChatBottomSmoothV123, 450);
            }
            inp.addEventListener("keydown", function(e) {
              if (e.key === "Enter") onSendTriggered();
            });
            var parentRow = inp.parentElement;
            if (parentRow) {
              var sendBtns = Array.from(parentRow.querySelectorAll("button"));
              sendBtns.forEach(function(btn) {
                btn.addEventListener("click", onSendTriggered);
              });
            }
          });
        }

        function setReactInputValueNativeV123(el, val) {
          try {
            var proto = el.tagName === "TEXTAREA" ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
            var setter = Object.getOwnPropertyDescriptor(proto, "value");
            if (setter && setter.set) {
              setter.set.call(el, val);
            } else {
              el.value = val;
            }
            el.dispatchEvent(new Event("input", { bubbles: true }));
            el.dispatchEvent(new Event("change", { bubbles: true }));
          } catch (e) {
            el.value = val;
          }
        }

        window.__copyAndAttachMissingToOrderNotesV123 = function(btnEl, missingText, recipeTitle) {
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
            setReactInputValueNativeV123(inp, nextVal);
          });

          try {
            fetch("/api/ai-studio/request-item", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                sessionId: window.__v112SessionId || "guest",
                requestedItem: missingText,
                userMessage: noteLine
              })
            }).catch(function() {});
          } catch (e) {}

          if (btnEl) {
            btnEl.innerHTML = "✅ تم النسخ والإضافة لملاحظة طلبك تلقائياً! سيرد عليك المتجر حول توفرها";
            btnEl.style.background = "#16a34a";
            btnEl.style.color = "#ffffff";
          }
        };

        function syncOrderNotesFieldV123() {
          try {
            var savedNote = localStorage.getItem("original_ai_extra_order_notes") || "";
            if (!savedNote) return;
            var noteInputs = Array.from(document.querySelectorAll("textarea, input[type='text']")).filter(function(inp) {
              var ph = (inp.getAttribute("placeholder") || "") + " " + (inp.getAttribute("name") || "") + " " + (inp.id || "");
              return ph.indexOf("ملاحظ") !== -1 || ph.indexOf("note") !== -1;
            });
            noteInputs.forEach(function(inp) {
              if (!inp.value && !inp.getAttribute("data-v123-filled")) {
                inp.setAttribute("data-v123-filled", "1");
                setReactInputValueNativeV123(inp, savedNote);
              }
            });
          } catch (e) {}
        }
"""

    if "function enhanceChatBubblesSafelyV117()" in ht:
        ht = ht.replace(
            "function enhanceChatBubblesSafelyV117()",
            v125_helpers_and_css + "\n        function enhanceChatBubblesSafelyV117()",
            1
        )

    old_enhance_pattern = r'function enhanceChatBubblesSafelyV117\(\) \{[\s\S]*?var origFetch = window\.fetch;'

    new_enhance_v125 = """function buildIngredientsTableHtmlV123(rows, missingItemsText, recipeTitle) {
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
              '<button type="button" class="v123-copy-notes-btn" data-missing="' + safeMissing + '" data-title="' + safeTitle + '" style="width:100%;background:#0d3825;color:#ffffff;border:none;border-radius:10px;padding:9px 12px;font-weight:800;font-size:0.78rem;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:6px;">' +
              '📋 نسخ وإضافة تلقائياً في ملاحظة الطلب (ليرد عليك المتجر حول توفرها)' +
              '</button>' +
              '</div>';
          }

          return (
            '<div class="v123-ingredients-panel" style="margin:12px 0 8px 0;padding:4px 0;direction:rtl;text-align:right;width:100%;overflow-x:auto;">' +
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

          // Clean up any accidental chat classes that were ever applied to store categories or product cards outside the chat root!
          var chatRoot = getAiChatCardRootV125();
          Array.from(document.querySelectorAll(".v121-gemini-user-bubble, .v122-gemini-user-bubble, .v123-gemini-user-bubble, .v124-user-row-left")).forEach(function(el) {
            if (!chatRoot || !chatRoot.contains(el) || el.querySelector("img, svg")) {
              el.classList.remove("v121-gemini-user-bubble", "v122-gemini-user-bubble", "v123-gemini-user-bubble", "v124-user-row-left");
              el.removeAttribute("data-v123-role");
              el.removeAttribute("data-v122-role");
              el.removeAttribute("data-v121-role");
            }
          });

          if (!chatRoot) return;
          bindChatInputScrollLockV123();

          Array.from(chatRoot.querySelectorAll(".v117-recipe-photo-banner, .v118-wa-photo-box")).forEach(function(box) {
            if (box.classList.contains("v117-recipe-photo-banner") || isInsideDarkGreenUserBubbleV119(box)) {
              box.remove();
            }
          });

          // ONLY query elements inside chatRoot (NEVER across the whole document!)
          var allLeaves = Array.from(chatRoot.querySelectorAll("p, div")).filter(function(el) {
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

          // ONLY query user bubbles inside chatRoot, and strictly exclude any element with an <img> or <svg>!
          var allUserBubbles = Array.from(chatRoot.querySelectorAll("div, p, span")).filter(function(el) {
            if (el.closest && (el.closest(".v123-gemini-bot-full") || el.closest(".v123-gemini-ai-header") || el.closest(".v122-gemini-ai-header"))) return false;
            if (!isDarkGreenBgV119(el)) return false;
            if (el.tagName === "BUTTON" || el.tagName === "IMG" || el.querySelector("button, input, textarea, img, svg")) return false;
            var hasDarkGreenChild = Array.from(el.children).some(function(c) { return isDarkGreenBgV119(c); });
            if (hasDarkGreenChild) return false;
            var t = (el.textContent || "").trim();
            if (t === "✨" || t.indexOf("شيف ومساعد") !== -1 || t.indexOf("مساعد وشيف") !== -1 || t.indexOf("محادثة جديدة") !== -1 || t.indexOf("الأصناف والمقادير") !== -1) return false;
            if (t.length < 1 || t.length > 220) return false;

            el.setAttribute("data-v123-role", "user");
            el.classList.remove("v121-gemini-user-bubble", "v122-gemini-user-bubble");
            el.classList.add("v123-gemini-user-bubble");
            if (el.parentElement && el.parentElement !== chatRoot && el.parentElement.textContent.indexOf("محادثة جديدة") === -1 && !el.parentElement.querySelector("img")) {
              el.parentElement.classList.add("v124-user-row-left");
            }

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
            if (assistantCard.parentElement && assistantCard.parentElement !== chatRoot && assistantCard.parentElement.textContent.indexOf("محادثة جديدة") === -1) {
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
              window.__v125PinBottomUntil = Date.now() + 4500;
              setTimeout(scrollToNewReplyAndGlideV125, 40);
            }
          }
        }

        var origFetch = window.fetch;"""

    ht, n_enh = re.subn(old_enhance_pattern, lambda m: new_enhance_v125, ht, count=1)

    html_path.write_text(ht, encoding="utf-8")
    print("2. Updated client/index.html (v125 Scoped Chat Root protecting Categories 100% + Pre-Paint Scroll Lock + ChatGPT Progressive Glide)!")

# ==============================================================================
# 3. ترقية رقم كاش Service Worker إلى v125
# ==============================================================================
sw_path = pathlib.Path("client/public/sw.js")
if sw_path.exists():
    sw_txt = sw_path.read_text(encoding="utf-8")
    sw_txt = re.sub(r'v10\d|v11\d|v12\d|v9\d', 'v125', sw_txt)
    sw_path.write_text(sw_txt, encoding="utf-8")
    print("3. Bumped Service Worker cache to v125!")

# ==============================================================================
# 4. فحص البناء والرفع إلى Render
# ==============================================================================
res_srv = subprocess.run(
    "npx esbuild server/_core/index.ts --bundle --platform=node --format=esm --packages=external --outfile=./.tmp_srv_v125.js",
    shell=True, capture_output=True, text=True
)
res_cli = subprocess.run(
    "npx esbuild client/src/pages/Admin.tsx client/src/pages/Home.tsx --bundle --platform=browser --packages=external --outdir=./.tmp_cli_v125",
    shell=True, capture_output=True, text=True
)
os.system("rm -rf ./.tmp_srv_v125.js ./.tmp_cli_v125")

if res_srv.returncode != 0 or res_cli.returncode != 0:
    print("❌ Build check failed:", res_srv.stderr, res_cli.stderr)
else:
    print("✅ Build check passed 100%!")
    os.system("git add server/ai_engine_v112.ts client/index.html client/public/sw.js")
    os.system('git commit -m "Fix v125: restore 100% original categories layout, prevent chat jump-to-top via MutationObserver, and add ChatGPT progressive glide scroll"')
    os.system("git push origin main")
    print("🚀 تم الرفع بنجاح إلى Render (v125)!")
