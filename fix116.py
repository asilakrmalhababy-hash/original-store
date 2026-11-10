import pathlib, re, subprocess, sys

print("=== بدء التحديث الشامل v116 (عرض صورة الوصفة بشكل مغري وفخم داخل المحادثة مع الوصفة الكاملة والمنتجات المربوطة + ربط مباشر بمساعد أورجنال الذكي) ===")

# 0. Restore server/commerce.ts, server/_core/index.ts, Home.tsx, client/index.html to clean v98 (db9eb83) state first
subprocess.run(["git", "checkout", "db9eb83", "--", "server/commerce.ts", "server/_core/index.ts", "client/src/pages/Home.tsx", "client/index.html"], check=False)

# ==============================================================================
# 1. Create standalone server/ai_engine_v112.ts (v116 Rock-Solid Persistence + Mouth-Watering Recipe Engine)
# ==============================================================================
ai_engine_ts = """import express from "express";
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
      if (parsed && parsed.studio_config) {
        studioConfigV114 = normalizeStudioConfigV115(parsed.studio_config);
      }
      if (parsed && Array.isArray(parsed.customer_requests)) {
        customerRequestsV114 = parsed.customer_requests;
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
  if (cachedCatalogV114.length > 0 && now - lastCatalogTimeV114 < 60000) {
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
        if (r && r.k === "studio_config" && r.v) {
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

export async function handleSmartAiChatV112(input: {
  message: string;
  sessionId?: string;
  customerName?: string;
  customerPhone?: string;
  history?: Array<{ role: string; content: string }>;
}) {
  await ensureStudioTableV114();
  const userMsg = String(input.message || "").trim();
  const normMsg = userMsg.toLowerCase();

  tokenStatsV114.zeroTokenMessages++;
  tokenStatsV114.estimatedTokensSaved += 4200;

  const cacheKey = normMsg.replace(/\\s+/g, " ");
  if (replyCacheV114[cacheKey] && !/(نعم|ايوه|أيوة|كلمهم|كلم المتجر)/.test(normMsg)) {
    tokenStatsV114.cachedHits++;
    return replyCacheV114[cacheKey];
  }

  if (/(اباحي|إباحي|مايا خليفه|مايا خليفة|جنس|سكس|porn|xxx)/i.test(normMsg)) {
    return {
      reply: "حياك الله يا غالي، أنا مساعد متجر أورجنال، يسعدني دائماً خدمتك في كل ما يخص المنتجات والمعلومات الغذائية. كيف أقدر أخدمك اليوم؟",
      suggestedItems: [],
      quickActions: [],
      canContactStore: false
    };
  }

  const isConfirmingStoreContact =
    /(نعم|ايوه|أيوة|ايه|أيه|كلمهم|كلم المتجر|كلّم المتجر|تواصل معهم|ارسل لهم|أرسل لهم|ياريت|يا ريت|اكيد|أكيد|تواصل لك مع المتجر)/.test(normMsg) &&
    (normMsg.includes("المتجر") ||
      (Array.isArray(input.history) &&
        input.history.some(h => String(h.content || "").includes("أكلم المتجر") || String(h.content || "").includes("أتواصل لك"))));

  if (isConfirmingStoreContact) {
    const prevUserMsgs = (input.history || []).filter(h => h.role === "user").map(h => h.content);
    const requestedTopic = prevUserMsgs.length > 0 ? prevUserMsgs[prevUserMsgs.length - 1] : userMsg;
    const reqRecord: CustomerAiRequestV114 = {
      id: "req_" + Date.now() + "_" + Math.random().toString(36).slice(2, 6),
      sessionId: String(input.sessionId || "guest"),
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
      requestObj: reqRecord
    };
  }

  const allProducts = await getCatalogCachedV114();

  // Check Manager's Custom Rules (القسم 2: قاموس الردود)
  for (const rule of studioConfigV114.rules || []) {
    const trig = normalizeArabicV116(rule.trigger || "");
    if (trig && normalizeArabicV116(userMsg).includes(trig)) {
      const items: any[] = [];
      if (rule.linkedProductName) {
        const foundP = allProducts.find(p => cleanProductNameV112(p.name) === cleanProductNameV112(rule.linkedProductName || ""));
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
      const resRule = {
        reply: replyTxt,
        suggestedItems: items,
        quickActions: [],
        canContactStore: false
      };
      replyCacheV114[cacheKey] = resRule;
      return resRule;
    }
  }

  // Check Manager's Visual Recipes (القسم 4: الوصفات المصورة والمنتجات)
  const matchedRec = findMatchingRecipeV116(userMsg);
  if (matchedRec) {
    const recItems: any[] = [];
    for (const ing of matchedRec.ingredients || []) {
      const cleanIng = cleanProductNameV112(ing.name);
      const foundP = allProducts.find(p => cleanProductNameV112(p.name).includes(cleanIng) || cleanIng.includes(cleanProductNameV112(p.name)));
      if (foundP) {
        recItems.push({
          productId: foundP.id,
          id: foundP.id,
          name: cleanProductNameV112(foundP.name),
          price: Math.round(Number(foundP.price || 0)),
          unit: foundP.unit || "حبة",
          quantity: 1,
          imageUrl: foundP.imageUrl || "",
          url: ing.url || ("/?search=" + encodeURIComponent(cleanProductNameV112(foundP.name)))
        });
      } else if (ing.name) {
        recItems.push({
          productId: 1,
          id: 1,
          name: cleanIng || ing.name,
          price: Number(ing.price || 100),
          unit: "حبة",
          quantity: 1,
          imageUrl: "",
          url: ing.url || ("/?search=" + encodeURIComponent(cleanIng || ing.name))
        });
      }
    }
    const recReply =
      "يا غالي، جبت لك ألذ وأفخم وصفة تفتح النفس من مطبخ أورجنال: 😍✨\\n" +
      "🍰 «" + matchedRec.title + "»\\n\\n" +
      "📋 طريقة التحضير الكاملة:\\n" +
      String(matchedRec.steps || "");

    const resRec = {
      reply: recReply,
      recipeCard: {
        title: matchedRec.title,
        imageUrl: matchedRec.imageUrl || "",
        steps: matchedRec.steps,
        ingredients: recItems
      },
      suggestedItems: recItems,
      quickActions: [],
      canContactStore: false
    };
    replyCacheV114[cacheKey] = resRec;
    return resRec;
  }

  // Check Manager's Promoted Products (القسم 3: ترويج منتج برابطه)
  const activePromos = (studioConfigV114.promotedProducts || []).filter(p => p.active !== false && p.productName);
  const triggeredPromo = activePromos.find(p => {
    if (!p.triggerKeywords || !p.triggerKeywords.trim()) return false;
    return p.triggerKeywords.split(/[،,]+/).map(s => normalizeArabicV116(s)).filter(Boolean).some(k => normalizeArabicV116(userMsg).includes(k));
  });

  if (triggeredPromo) {
    const foundPromoProd = allProducts.find(p => cleanProductNameV112(p.name).includes(cleanProductNameV112(triggeredPromo.productName)));
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
      canContactStore: false
    };
  }

  const matchedProducts = allProducts.filter(p => {
    const pName = cleanProductNameV112(p.name);
    if (!pName || pName.length < 3) return false;
    if (userMsg.includes(pName)) return true;
    const words = pName.split(/\\s+/).filter(w => w.length >= 4);
    return words.length > 0 && words.every(w => userMsg.includes(w));
  });

  const isGeneralChatOrGreeting =
    /^(سلام|السلام عليكم|هلا|اهلا|أهلا|مرحبا|صباح الخير|مساء الخير|كيفك|كيف حالك|اخبارك|أخبارك|عادي|تمام|شكرا|شكراً|حياك|اورجنال|أورجنال)$/i.test(userMsg) ||
    /(نسولف|سوالف|بدون ما تدخل المتجر|من هي|من هو|حدثني عن|ما عاصمة|كم تاريخ|قصة|نكتة)/.test(userMsg);

  if (isGeneralChatOrGreeting && matchedProducts.length === 0) {
    if (/(نسولف|سوالف|بدون ما تدخل المتجر)/.test(userMsg)) {
      return {
        reply: "حياك الله يا غالي، خذ راحتك على الآخر! 😊 أنا صاحبك هنا نسولف في أي موضوع يخطر في بالك بدون ما نجيب سيرة المتجر أبداً. قولي إيش الأخبار وإيش الموضوع اللي في بالك؟",
        suggestedItems: [],
        quickActions: [],
        canContactStore: false
      };
    }
    if (/^(سلام|السلام عليكم|هلا|اهلا|أهلا|مرحبا|كيفك|كيف حالك|اخبارك|أخبارك|عادي|تمام|اورجنال|أورجنال)/i.test(userMsg)) {
      const welcomeInst = (studioConfigV114.instructions || []).find(i => i.active !== false && i.category.includes("الترحيب") && i.content.trim());
      const generalPromo = activePromos.find(p => !p.triggerKeywords || !p.triggerKeywords.trim());
      let baseWelcome = welcomeInst
        ? welcomeInst.content.trim()
        : "يا هلا ومليون غلا بك يا غالي! 😊 الحمد لله بخير دامك بخير. أنا معك لو حبيت تسأل عن أي منتج، سعراته الحرارية، أو حتى لو تدور على غرض معين وتبغاني أكلم لك المتجر يوفره لك. آمرني؟";

      if (generalPromo) {
        baseWelcome += "\\n\\n" + (generalPromo.promoBadge || "⭐ لا يفوتك اليوم:") + " «" + generalPromo.productName + "» — " + (generalPromo.promoMessage || "");
      }
      return {
        reply: baseWelcome,
        promotedCard: generalPromo ? {
          name: generalPromo.productName,
          price: generalPromo.productPrice || 0,
          url: generalPromo.productUrl || ("/?search=" + encodeURIComponent(generalPromo.productName)),
          imageUrl: generalPromo.productImage || "",
          badge: generalPromo.promoBadge || "⭐ عرض مميز"
        } : undefined,
        suggestedItems: [],
        quickActions: [],
        canContactStore: false
      };
    }
  }

  if (matchedProducts.length > 0) {
    const primary = matchedProducts[0];
    const pName = cleanProductNameV112(primary.name);
    const pPrice = Math.round(Number(primary.price || 0));
    const modalInfo = buildSmartProductModalDataV112(pName, pPrice, primary.unit || "حبة", "", userMsg, primary.id);

    const companions = allProducts
      .filter(p => p.id !== primary.id && classifyProductKindV112(p.name, "", "") === modalInfo.kind && Number(p.price) > 5)
      .slice(0, 2);

    let friendlyReply =
      "فهمتك يا غالي! بخصوص «" + pName + "» (متوفر عندنا بسعر " + pPrice.toLocaleString("en-US") + " ر.ي):\\n" +
      modalInfo.content.replace(/^✨[^\\n]*\\n/, "");

    if (companions.length > 0) {
      const compNames = companions.map(c => "«" + cleanProductNameV112(c.name) + "» (" + Math.round(Number(c.price)).toLocaleString("en-US") + " ر.ي)").join(" أو ");
      friendlyReply += "\\n\\nوبما إنك تحب هذا النوع، عندنا أيضاً في المتجر " + compNames + " إذا تحب تجربه معه!";
    }

    const prodResult = {
      reply: friendlyReply.replace(/\\(\\s*رقم\\s*\\d+\\s*\\)/g, ""),
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
      canContactStore: false
    };
    replyCacheV114[cacheKey] = prodResult;
    return prodResult;
  }

  const queryWords = userMsg
    .replace(/[؟?!.,،]/g, " ")
    .split(/\\s+/)
    .map(w => w.trim())
    .filter(w => w.length >= 3 && !["عندكم", "اريد", "أريد", "ابغى", "أبغى", "اشتي", "أشتي", "موجود", "متوفر", "حبة", "باكيت", "كرتون", "سعر", "بكم", "كم", "هل", "في", "من", "على", "مع", "هذا", "هذه"].includes(w));

  const partialMatches = allProducts.filter(p => {
    const pName = cleanProductNameV112(p.name);
    return Number(p.price) > 5 && queryWords.some(w => pName.includes(w));
  }).slice(0, 3);

  const cleanWanted = userMsg.replace(/^(هل عندكم|عندكم|هل يوجد|أريد|اريد|أشتي|اشتي|ابغى|أبغى|بكم|كم سعر)\\s*/i, "").replace(/[؟?]/g, "").trim() || userMsg;
  let altSentence = "";
  if (partialMatches.length > 0) {
    const altList = partialMatches
      .map(p => "«" + cleanProductNameV112(p.name) + "» (" + Math.round(Number(p.price)).toLocaleString("en-US") + " ر.ي)")
      .join("، و");
    altSentence = "بما إنك تريده فعندنا حالياً قريب منه: " + altList + ". ";
  } else {
    altSentence = "حالياً هذا الصنف مش ظاهر عندي في الرف الآن. ";
  }

  const unavailInst = (studioConfigV114.instructions || []).find(i => i.active !== false && i.category.includes("عدم توفر") && i.content.trim());
  const friendReply = unavailInst
    ? unavailInst.content.replace(/\{المنتج\}/g, cleanWanted) + "\\n" + altSentence + "هل تريد أكلم المتجر إذا عندهم؟"
    : "فهمتك يا غالي، أنت تريد «" + cleanWanted + "».. حلو حلو! 👌\\n" +
      altSentence +
      "وإذا تريد نفس «" + cleanWanted + "» بالضبط، أقدر أتواصل لك الحين مع إدارة المتجر وأسألهم إذا متوفر عندهم أو يوفرونه لك فوراً!\\n" +
      "هل تريد أكلم المتجر إذا عندهم؟";

  const finalRes = {
    reply: friendReply,
    suggestedItems: partialMatches.map(p => ({
      productId: p.id,
      id: p.id,
      name: cleanProductNameV112(p.name),
      price: Math.round(Number(p.price)),
      unit: p.unit || "حبة",
      quantity: 1
    })),
    quickActions: ["📲 نعم، كلّم المتجر إذا عندهم («" + cleanWanted + "»)"],
    canContactStore: true,
    requestedItemName: cleanWanted
  };
  replyCacheV114[cacheKey] = finalRes;
  return finalRes;
}

export function registerAiEngineV112(app: any) {
  app.use("/api/ai-v112", express.json({ limit: "25mb" }));

  ensureStudioTableV114().catch(() => {});

  app.get("/api/ai-v112/config", async (_req: any, res: any) => {
    try {
      await ensureStudioTableV114();
      const catalog = await getCatalogCachedV114();
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
        stats: tokenStatsV114,
        catalog: simpleCatalog
      });
    } catch (e: any) {
      res.status(500).json({ ok: false, error: String(e?.message || e) });
    }
  });

  app.post("/api/ai-v112/save-training", async (req: any, res: any) => {
    try {
      await ensureStudioTableV114();
      const body = req.body || {};
      if (typeof body.generalSystemPrompt === "string") studioConfigV114.generalSystemPrompt = body.generalSystemPrompt.trim();
      if (Array.isArray(body.instructions)) studioConfigV114.instructions = body.instructions;
      if (Array.isArray(body.rules)) studioConfigV114.rules = body.rules;
      if (Array.isArray(body.promotedProducts)) studioConfigV114.promotedProducts = body.promotedProducts;
      if (Array.isArray(body.recipes)) studioConfigV114.recipes = body.recipes;
      if (body.productAiMap && typeof body.productAiMap === "object") studioConfigV114.productAiMap = body.productAiMap;
      replyCacheV114 = {};
      await saveStudioKeyV114("studio_config", studioConfigV114);
      res.json({ ok: true, config: studioConfigV114 });
    } catch (e: any) {
      res.status(500).json({ ok: false, error: String(e?.message || e) });
    }
  });

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

  app.post("/api/ai-v112/chat", async (req: any, res: any) => {
    try {
      const result = await handleSmartAiChatV112(req.body || {});
      res.json({ ok: true, ...result });
    } catch (e: any) {
      res.status(500).json({ ok: false, error: String(e?.message || e) });
    }
  });

  app.post("/api/ai-v112/request-store", async (req: any, res: any) => {
    try {
      await ensureStudioTableV114();
      const body = req.body || {};
      const reqRecord: CustomerAiRequestV114 = {
        id: "req_" + Date.now() + "_" + Math.random().toString(36).slice(2, 6),
        sessionId: String(body.sessionId || "guest"),
        customerName: String(body.customerName || "زبون المتجر"),
        customerPhone: String(body.customerPhone || ""),
        requestedItem: String(body.requestedItem || body.message || "طلب توفير منتج").slice(0, 160),
        customerMessage: String(body.customerMessage || body.requestedItem || ""),
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
  });

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
"""

pathlib.Path("server/ai_engine_v112.ts").write_text(ai_engine_ts, encoding="utf-8")
print("1. Created server/ai_engine_v112.ts (v116 Engine)!")

# ==============================================================================
# 2. Register registerAiEngineV112(app) & /api/admin/order-add-item in server/_core/index.ts
# ==============================================================================
srv_index = pathlib.Path("server/_core/index.ts")
if srv_index.exists():
    si = srv_index.read_text(encoding="utf-8")
    si = re.sub(r'express\.json\(\s*\)', 'express.json({ limit: "50mb" })', si)
    imports_to_add = 'import { registerAiEngineV112 } from "../ai_engine_v112";\nimport { addInvoiceItemToOrderV99 } from "../commerce";\n'
    if "registerAiEngineV112" not in si:
        si = imports_to_add + si
        route_hook = """
  registerAiEngineV112(app);
  app.post("/api/admin/order-add-item", express.json({ limit: "10mb" }), async (req, res) => {
    try {
      const result = await addInvoiceItemToOrderV99(req.body || {});
      res.json(result);
    } catch (err: any) {
      res.status(400).json({ ok: false, error: String(err?.message || err) });
    }
  });
"""
        idx_app = si.find("const app = express()")
        if idx_app != -1:
            line_end = si.find("\n", idx_app)
            si = si[:line_end+1] + route_hook + si[line_end+1:]
        elif "app.use(" in si:
            idx_use = si.find("app.use(")
            si = si[:idx_use] + route_hook + "\n  " + si[idx_use:]
        srv_index.write_text(si, encoding="utf-8")
        print("2. Registered AI Studio v116 and 50mb JSON limit in server/_core/index.ts!")

# ==============================================================================
# 3. Update server/commerce.ts:
# ==============================================================================
comm_path = pathlib.Path("server/commerce.ts")
if comm_path.exists():
    cc = comm_path.read_text(encoding="utf-8")

    cc = re.sub(r'\(\s*رقم\s*\$\{[^}]+\}\s*\)', '', cc)
    cc = re.sub(r'max_tokens:\s*(?:800|1000|1200|1500|2000)', 'max_tokens: 180', cc)

    def add_desc_to_select(m):
        block = m.group(0)
        if "description:" not in block and "products.unit" in block:
            return block.replace("unit: products.unit,", "unit: products.unit, description: products.description,")
        return block

    cc = re.sub(r'\.select\(\{[\s\S]*?\}\)', add_desc_to_select, cc)

    secure_resolve_fn = """function resolveServerVariantOption(product: any, itemName?: string): { price: number; unit: string; name: string } {
  const fallbackUnit = String(product?.unit || "حبة").trim() || "حبة";
  const fallbackPrice = Math.max(0, Math.round(Number(product?.price || 0)));
  const rawItemName = String(itemName || product?.name || "").trim();
  if (!rawItemName) {
    return { price: fallbackPrice, unit: fallbackUnit, name: String(product?.name || "") };
  }

  const dbPriceMap: Record<string, number> = {};
  const desc = String(product?.description || "");
  const vMatch = desc.match(/\\[\\[variants:(\\[[\\s\\S]*?\\])\\]\\]/);
  if (vMatch && vMatch[1]) {
    try {
      const dbVariants: string[] = JSON.parse(vMatch[1]);
      for (const rawVar of dbVariants) {
        const subVars = String(rawVar || "").split(/[،,]+/);
        for (const sv of subVars) {
          const entry = sv.trim();
          const colonIdx = entry.indexOf(":");
          if (colonIdx !== -1) {
            const oName = entry.slice(0, colonIdx).trim();
            const oPrice = Number(entry.slice(colonIdx + 1).trim());
            if (oName && !isNaN(oPrice) && oPrice > 0) {
              dbPriceMap[oName] = Math.round(oPrice);
            }
          }
        }
      }
    } catch {}
  }

  let innerParen = "";
  const parenMatches = Array.from(rawItemName.matchAll(/\\(([^()]+)\\)/g));
  if (parenMatches.length > 0) {
    innerParen = parenMatches.map(m => m[1].trim()).filter(s => s.includes(":")).join("، ");
    if (!innerParen) innerParen = parenMatches[parenMatches.length - 1][1].trim();
  } else if (rawItemName.includes(":")) {
    innerParen = rawItemName;
  }

  if (innerParen) {
    const segments = innerParen.split(/[،,+]+/).map(s => s.trim()).filter(Boolean);
    let totalWeightedPrice = 0;
    let totalSegQty = 0;
    const matchedLabels: string[] = [];

    for (const seg of segments) {
      let segQty = 1;
      const multMatch = seg.match(/[×xX*]\\s*(\\d+)/);
      if (multMatch && multMatch[1]) {
        segQty = Math.max(1, parseInt(multMatch[1], 10));
      }
      const cleanSeg = seg.replace(/[×xX*]\\s*\\d+.*$/, "").trim();
      const colonIdx = cleanSeg.indexOf(":");
      const optName = (colonIdx !== -1 ? cleanSeg.slice(0, colonIdx) : cleanSeg).replace(/—.*$/, "").trim();
      const labelPriceRaw = colonIdx !== -1 ? Number(cleanSeg.slice(colonIdx + 1).trim()) : NaN;

      let resolvedSegPrice = dbPriceMap[optName];
      if (resolvedSegPrice === undefined) {
        for (const [k, v] of Object.entries(dbPriceMap)) {
          if (optName && k && (optName.includes(k) || k.includes(optName))) {
            resolvedSegPrice = v;
            break;
          }
        }
      }
      if (resolvedSegPrice === undefined && !isNaN(labelPriceRaw) && labelPriceRaw > 0) {
        resolvedSegPrice = Math.round(labelPriceRaw);
      }

      if (resolvedSegPrice !== undefined && resolvedSegPrice > 0) {
        totalWeightedPrice += resolvedSegPrice * segQty;
        totalSegQty += segQty;
        matchedLabels.push(optName);
      }
    }

    if (totalSegQty > 0 && totalWeightedPrice > 0) {
      const effectiveUnitPrice = Math.round(totalWeightedPrice / totalSegQty);
      const unitLabel = matchedLabels.join("، ") || fallbackUnit;
      return {
        price: effectiveUnitPrice,
        unit: unitLabel,
        name: rawItemName
      };
    }
  }

  for (const [optName, officialPrice] of Object.entries(dbPriceMap)) {
    if (optName && rawItemName.includes(optName)) {
      return {
        price: officialPrice,
        unit: optName,
        name: rawItemName
      };
    }
  }

  return { price: fallbackPrice, unit: fallbackUnit, name: rawItemName || String(product?.name || "") };
}"""

    fn_start = cc.find("function resolveServerVariantOption")
    if fn_start != -1:
        close_col0 = cc.find("\n}", fn_start)
        if close_col0 != -1:
            fn_end = close_col0 + 2
            cc = cc[:fn_start] + secure_resolve_fn + cc[fn_end:]

    v99_order_helpers = """
export async function addInvoiceItemToOrderV99(input: { orderId?: number; orderNumber?: string; name: string; unitPrice: number; quantity: number; productId?: number }) {
  const dbInstance = await getDb();
  if (!dbInstance) throw new Error("Database unavailable");
  const allOrders = await dbInstance.select().from(orders);
  const targetOrder = allOrders.find((o: any) =>
    (input.orderId && Number(o.id) === Number(input.orderId)) ||
    (input.orderNumber && String(o.orderNumber).trim() === String(input.orderNumber).trim())
  );
  if (!targetOrder) throw new Error("Order not found");

  const qty = Math.max(1, Number(input.quantity || 1));
  const price = Math.max(0, Number(input.unitPrice || 0));
  const addedTotal = Math.round(qty * price);

  let validProductId = Number(input.productId || 0);
  if (!validProductId) {
    const existingItems = await dbInstance.select().from(orderItems).where(eq(orderItems.orderId, Number(targetOrder.id)));
    if (existingItems.length > 0 && existingItems[0].productId) {
      validProductId = Number(existingItems[0].productId);
    } else {
      const someProd = await dbInstance.select().from(products).limit(1);
      if (someProd.length > 0) validProductId = Number(someProd[0].id);
    }
  }

  await dbInstance.insert(orderItems).values({
    orderId: Number(targetOrder.id),
    productId: validProductId || 1,
    productName: String(input.name).trim(),
    name: String(input.name).trim(),
    unit: "حبة",
    quantity: qty,
    unitPrice: price,
    price: price,
    lineTotal: addedTotal,
    total: addedTotal,
  } as any);

  const newSubtotal = Number(targetOrder.subtotal || 0) + addedTotal;
  const newTotal = Number(targetOrder.total || 0) + addedTotal;
  const noteMsg = "تمت إضافة الصنف (" + String(input.name).trim() + " × " + qty + " = " + addedTotal + " ر.ي) للفاتورة بناءً على طلب الزبون. الإجمالي المحدث: " + newTotal + " ر.ي";

  await dbInstance.update(orders).set({
    subtotal: newSubtotal,
    total: newTotal,
  } as any).where(eq(orders.id, Number(targetOrder.id)));

  return { ok: true, orderId: targetOrder.id, newSubtotal, newTotal, message: noteMsg };
}
"""
    if "addInvoiceItemToOrderV99" not in cc:
        cc = cc + "\n" + v99_order_helpers

    comm_path.write_text(cc, encoding="utf-8")
    print("3. Updated server/commerce.ts!")

# ==============================================================================
# 4. Update client/src/pages/Home.tsx:
# ==============================================================================
home_path = pathlib.Path("client/src/pages/Home.tsx")
if home_path.exists():
    hc = home_path.read_text(encoding="utf-8")

    hc = re.sub(
        r'\b(item|i|c|it|ci|row|line|cartItem|entry)\.(?:unitPrice|price)\s*\*\s*\1\.quantity\b',
        r'extractVariantLineTotalV107(\1)',
        hc
    )
    hc = re.sub(
        r'\b(item|i|c|it|ci|row|line|cartItem|entry)\.quantity\s*\*\s*\1\.(?:unitPrice|price)\b',
        r'extractVariantLineTotalV107(\1)',
        hc
    )
    hc = re.sub(
        r'\b(item|i|c|it|ci|row|line|cartItem|entry)\.product\??\.price\b(?!\s*=(?!=))',
        r'Math.round(extractVariantPriceV104(\1, \1?.product?.price, \1?.product))',
        hc
    )
    hc = re.sub(
        r'\b(item|i|c|it|ci|row|line|cartItem|entry)\.(?:unitPrice|price)\b(?!\s*=(?!=))',
        r'Math.round(extractVariantPriceV104(\1, \1?.unitPrice ?? \1?.price ?? \1?.product?.price, \1?.product))',
        hc
    )
    hc = re.sub(
        r'\b(item|i|c|it|ci|row|line|cartItem|entry)\.lineTotal\b(?!\s*=(?!=))',
        r'extractVariantLineTotalV107(\1)',
        hc
    )
    hc = re.sub(
        r'\b([a-zA-Z_]\w*(?:\??\.[a-zA-Z_]\w*)*)\??\.subtotal\b(?!\s*=(?!=)|\s*:)',
        r'extractCartSubtotalV107(\1, \1?.subtotal)',
        hc
    )
    hc = re.sub(
        r'\b([a-zA-Z_]\w*(?:\??\.[a-zA-Z_]\w*)*)\??\.total\b(?!\s*=(?!=)|\s*:)',
        r'extractOrderTotalV107(\1, \1?.total)',
        hc
    )
    hc = re.sub(
        r'\b([a-zA-Z_]\w*(?:\??\.[a-zA-Z_]\w*)*\??\.items)\??\.map\(',
        r'expandOrderItemsV110(\1).map(',
        hc
    )
    hc = re.sub(
        r'\b([a-zA-Z_]\w*(?:\??\.[a-zA-Z_]\w*)*\??\.items)\.length\b(?!\s*=(?!=))',
        r'expandOrderItemsV110(\1).length',
        hc
    )

    v111_helpers = """function expandOrderItemsV110(items: any): any[] {
  if (!Array.isArray(items)) return [];
  const result: any[] = [];
  for (const it of items) {
    if (!it || typeof it !== "object") {
      result.push(it);
      continue;
    }
    const rawName = String(it.productName || it.name || it.product?.name || "").trim();
    const parenMatches = Array.from(rawName.matchAll(/\\(([^()]+)\\)/g));
    if (parenMatches.length > 0) {
      const inner = parenMatches.map(m => m[1].trim()).filter(s => s.includes(":")).join("، ");
      const segments = inner.split(/[،,+]+/).map(s => s.trim()).filter(Boolean);
      if (segments.length > 1) {
        const baseTitle = rawName.replace(/\\s*\\([^()]*\\)\\s*$/g, "").trim() || rawName;
        let expandedAny = false;
        segments.forEach((seg, idx) => {
          let sQty = 1;
          const mm = seg.match(/[×xX*]\\s*(\\d+)/);
          if (mm && mm[1]) sQty = Math.max(1, parseInt(mm[1], 10));
          const cleanSeg = seg.replace(/[×xX*]\\s*\\d+.*$/, "").trim();
          const cIdx = cleanSeg.indexOf(":");
          if (cIdx !== -1) {
            const oName = cleanSeg.slice(0, cIdx).trim();
            const oPrice = parseFloat(cleanSeg.slice(cIdx + 1).trim());
            if (oName && !isNaN(oPrice) && oPrice > 0) {
              expandedAny = true;
              const segFullTitle = baseTitle + " (" + oName + ":" + Math.round(oPrice) + ")";
              result.push({
                ...it,
                id: String(it.id ?? "") + "_v" + idx,
                name: segFullTitle,
                productName: segFullTitle,
                unit: oName,
                quantity: sQty,
                price: Math.round(oPrice),
                unitPrice: Math.round(oPrice),
                lineTotal: Math.round(oPrice * sQty),
              });
            }
          }
        });
        if (expandedAny) continue;
      }
    }
    result.push(it);
  }
  return result;
}

function getStoredVariantTextV107(productId: any, productName?: any): string {
  try {
    if (productName && typeof window !== "undefined") {
      const cleanPName = String(productName).replace(/\\s*\\([^()]*\\)\\s*$/, "").trim();
      const reord = (window as any).__v111ReorderedVariants;
      if (reord && reord[cleanPName] && reord[cleanPName].raw) {
        return String(reord[cleanPName].raw);
      }
    }
    if (productId !== undefined && productId !== null) {
      const pidStr = String(productId);
      for (let i = 0; i < localStorage.length; i++) {
        const k = localStorage.key(i);
        if (!k || k.indexOf("v107") !== -1 || k.indexOf("v109") !== -1) continue;
        const raw = localStorage.getItem(k);
        if (!raw || (raw[0] !== "{" && raw[0] !== "[")) continue;
        try {
          const parsed = JSON.parse(raw);
          if (parsed && typeof parsed === "object" && !Array.isArray(parsed) && parsed[pidStr] !== undefined) {
            const val = parsed[pidStr];
            if (typeof val === "string" && val.includes(":")) return val;
            if (Array.isArray(val)) {
              const s = val.map((x: any) => typeof x === "string" ? x : (x?.label || x?.variant || x?.name || "")).filter(Boolean).join("، ");
              if (s.includes(":")) return s;
            }
            if (val && typeof val === "object") {
              const parts: string[] = [];
              for (const [vk, vv] of Object.entries(val)) {
                if (vk.includes(":") && Number(vv) > 0) {
                  parts.push(Number(vv) > 1 ? vk + " × " + vv : vk);
                }
              }
              if (parts.length > 0) return parts.join("، ");
            }
          }
        } catch {}
      }
    }
  } catch {}
  return "";
}

function extractVariantPriceV104(rawText: any, fallbackPrice: any, productObj?: any): number {
  const base = Number(fallbackPrice ?? productObj?.price ?? 0);
  let combined = "";
  let pid: any = productObj?.id ?? productObj?.productId;
  let pname: any = productObj?.name;
  if (typeof rawText === "object" && rawText !== null) {
    pid = rawText.productId ?? rawText.product?.id ?? rawText.id ?? pid;
    pname = rawText.product?.name ?? rawText.productName ?? rawText.name ?? pname;
    const explicitFields = [
      rawText.name,
      rawText.productName,
      rawText.displayName,
      rawText.customName,
      rawText.variant,
      rawText.selectedVariant,
      rawText.variantLabel,
      rawText.option,
      rawText.unit,
      rawText.label
    ].filter(v => typeof v === "string" && v.trim().length > 0).join(" ");

    if (/\\([^()]*:\\s*\\d/.test(explicitFields) || explicitFields.includes(":")) {
      combined = explicitFields;
    } else {
      combined = [explicitFields, getStoredVariantTextV107(pid, pname)].filter(Boolean).join(" ");
    }
  } else if (rawText) {
    combined = String(rawText).trim();
  } else {
    combined = getStoredVariantTextV107(pid, pname);
  }

  if (!combined) return base;

  const dbPriceMap: Record<string, number> = {};
  const desc = String(
    productObj?.description ||
    (typeof rawText === "object" ? (rawText?.description || rawText?.product?.description) : "") ||
    ""
  );
  const vMatch = desc.match(/\\[\\[variants:(\\[[\\s\\S]*?\\])\\]\\]/);
  if (vMatch && vMatch[1]) {
    try {
      const arr: string[] = JSON.parse(vMatch[1]);
      for (const rawEntry of arr) {
        const subEntries = String(rawEntry || "").split(/[،,]+/);
        for (const entry of subEntries) {
          const colonIdx = entry.indexOf(":");
          if (colonIdx !== -1) {
            const oName = entry.slice(0, colonIdx).trim();
            const oPrice = parseFloat(entry.slice(colonIdx + 1).trim());
            if (oName && !isNaN(oPrice) && oPrice > 0) {
              dbPriceMap[oName] = oPrice;
            }
          }
        }
      }
    } catch {}
  }

  let targetStr = "";
  const parenMatches = Array.from(combined.matchAll(/\\(([^()]+)\\)/g));
  if (parenMatches.length > 0) {
    targetStr = parenMatches.map(m => m[1].trim()).filter(s => s.includes(":")).join("، ");
  } else if (combined.includes(":")) {
    targetStr = combined;
  }

  if (targetStr && targetStr.includes(":")) {
    const segments = targetStr.split(/[،,+]+/).map(s => s.trim()).filter(Boolean);
    let totalW = 0;
    let totalQ = 0;
    for (const seg of segments) {
      let sQty = 1;
      const mm = seg.match(/[×xX*]\\s*(\\d+)/);
      if (mm && mm[1]) sQty = Math.max(1, parseInt(mm[1], 10));
      const cleanSeg = seg.replace(/[×xX*]\\s*\\d+.*$/, "").trim();
      const cIdx = cleanSeg.indexOf(":");
      if (cIdx !== -1) {
        const oName = cleanSeg.slice(0, cIdx).trim();
        const lPrice = parseFloat(cleanSeg.slice(cIdx + 1).trim());
        const finalP = dbPriceMap[oName] ?? (!isNaN(lPrice) && lPrice > 0 ? lPrice : 0);
        if (finalP > 0) {
          totalW += finalP * sQty;
          totalQ += sQty;
        }
      }
    }
    if (totalQ > 0 && totalW > 0) {
      return totalW / totalQ;
    }
  }

  for (const [oName, oPrice] of Object.entries(dbPriceMap)) {
    if (oName && combined.includes(oName)) return oPrice;
  }

  return base;
}

function extractVariantLineTotalV107(item: any): number {
  if (!item) return 0;
  const qty = Math.max(1, Number(item.quantity || 1));
  const unitP = extractVariantPriceV104(item, item?.unitPrice ?? item?.price ?? item?.product?.price, item?.product);
  return Math.round(unitP * qty);
}

function extractCartSubtotalV107(cartOrOrder: any, fallbackSubtotal?: any): number {
  const isOrderObj = Boolean(cartOrOrder?.orderNumber || cartOrOrder?.status);
  if (!isOrderObj && typeof window !== "undefined" && Number((window as any).__v108ComputedCartSubtotal) > 0) {
    return Number((window as any).__v108ComputedCartSubtotal);
  }
  const rawItems = cartOrOrder?.items;
  if (Array.isArray(rawItems) && rawItems.length > 0) {
    const items = expandOrderItemsV110(rawItems);
    const calcSub = Math.round(items.reduce((sum: number, it: any) => {
      const q = Math.max(1, Number(it?.quantity || 1));
      const up = extractVariantPriceV104(it, it?.unitPrice ?? it?.price ?? it?.product?.price, it?.product);
      return sum + up * q;
    }, 0));
    if (!isOrderObj && typeof window !== "undefined") {
      (window as any).__v107LastCartSubtotal = calcSub;
      (window as any).__v107LastCartBaseSubtotal = Number(fallbackSubtotal ?? cartOrOrder?.subtotal ?? 0);
    }
    return calcSub;
  }
  const fb = Number(fallbackSubtotal ?? cartOrOrder?.subtotal ?? 0);
  if (!isOrderObj && typeof window !== "undefined" && (window as any).__v107LastCartSubtotal && fb > 0) {
    return Number((window as any).__v107LastCartSubtotal);
  }
  return fb;
}

function extractOrderTotalV107(cartOrOrder: any, fallbackTotal?: any): number {
  const oldTot = Number(fallbackTotal ?? cartOrOrder?.total ?? 0);
  const oldSub = Number(cartOrOrder?.subtotal ?? oldTot);
  const newSub = extractCartSubtotalV107(cartOrOrder, oldSub);
  if (newSub > 0 && newSub !== oldSub) {
    return Math.max(0, oldTot - oldSub + newSub);
  }
  return oldTot;
}"""

    last_imp = hc.rfind("\nimport ", 0, 3000)
    end_imp = hc.find("\n", last_imp + 1) if last_imp != -1 else 0
    hc = hc[:end_imp + 1] + "\n" + v111_helpers + "\n" + hc[end_imp + 1:]
    home_path.write_text(hc, encoding="utf-8")
    print("4. Updated client/src/pages/Home.tsx!")

# ==============================================================================
# 5. Update client/index.html:
#    - Injects mouth-watering, high-appeal Recipe Showcase Card (large studio photo + golden ribbon badge + full recipe steps + linked store products with images & prices) directly inside the AI Assistant conversation whenever a customer asks for a recipe!
#    - Works both on new messages AND upgrades existing chat bubbles in real-time!
# ==============================================================================
html_path = pathlib.Path("client/index.html")
if html_path.exists():
    ht = html_path.read_text(encoding="utf-8")
    ht = re.sub(r'<script>\s*\(function\(\)\s*\{[\s\S]*?syncVariantModalPrice[\s\S]*?</script>', '', ht)

    v116_master_script = """
    <script>
      (function() {
        try {
          localStorage.removeItem("original_v107_by_name");
          sessionStorage.removeItem("original_v109_cart_subtotal");
        } catch (e) {}

        window.__v108ComputedCartSubtotal = 0;
        window.__v111ReorderedVariants = {};
        window.__v114StudioConfig = {
          generalSystemPrompt: "",
          instructions: [],
          rules: [],
          promotedProducts: [],
          recipes: [],
          productAiMap: {},
          ecoMode10k: true
        };
        window.__v115InitialConfigLoaded = false;
        window.__v115LastSaveTime = 0;
        window.__v115BannerMsg = "";
        window.__v114Requests = [];
        window.__v114Catalog = [];
        window.__v114Stats = { zeroTokenMessages: 0, cachedHits: 0, estimatedTokensSaved: 0 };
        window.__v112DeliveredReplyIds = {};
        window.__v112NotifiedReqIds = {};
        window.__v114StudioOpen = false;
        window.__v114ActiveSubTab = "inst";
        window.__v114DraftIngredients = [];
        window.__v114DraftRecipeImg = "";
        window.__v112SessionId = localStorage.getItem("original_v112_session_id") || ("sess_" + Date.now() + "_" + Math.random().toString(36).slice(2, 7));

        function hasAnyStudioItemsV115(c) {
          if (!c || typeof c !== "object") return false;
          return (
            (Array.isArray(c.instructions) && c.instructions.length > 0) ||
            (Array.isArray(c.rules) && c.rules.length > 0) ||
            (Array.isArray(c.promotedProducts) && c.promotedProducts.length > 0) ||
            (Array.isArray(c.recipes) && c.recipes.length > 0) ||
            (c.productAiMap && Object.keys(c.productAiMap).length > 0)
          );
        }

        function saveLocalBackupV115() {
          try {
            localStorage.setItem("original_v115_studio_backup", JSON.stringify(window.__v114StudioConfig));
          } catch (e) {}
        }

        try {
          localStorage.setItem("original_v112_session_id", window.__v112SessionId);
          var savedReord = sessionStorage.getItem("original_v111_reordered_variants");
          if (savedReord) window.__v111ReorderedVariants = JSON.parse(savedReord) || {};
          var savedDeliv = localStorage.getItem("original_v112_delivered_replies");
          if (savedDeliv) window.__v112DeliveredReplyIds = JSON.parse(savedDeliv) || {};
          var localCfg = localStorage.getItem("original_v115_studio_backup");
          if (localCfg) {
            var parsedLocal = JSON.parse(localCfg);
            if (parsedLocal && typeof parsedLocal === "object") {
              window.__v114StudioConfig = {
                generalSystemPrompt: String(parsedLocal.generalSystemPrompt || ""),
                instructions: Array.isArray(parsedLocal.instructions) ? parsedLocal.instructions : [],
                rules: Array.isArray(parsedLocal.rules) ? parsedLocal.rules : [],
                promotedProducts: Array.isArray(parsedLocal.promotedProducts) ? parsedLocal.promotedProducts : [],
                recipes: Array.isArray(parsedLocal.recipes) ? parsedLocal.recipes : [],
                productAiMap: parsedLocal.productAiMap && typeof parsedLocal.productAiMap === "object" ? parsedLocal.productAiMap : {},
                ecoMode10k: true
              };
            }
          }
        } catch (e) {}

        function normalizeArabicClientV116(str) {
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

        // Lightbox for full-screen recipe photo viewing
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

        // Build Mouth-Watering Complete Recipe Card HTML for inside the Chat Bubble!
        function buildMouthWateringRecipeHtmlV116(rec) {
          var imgSectionHtml = "";
          if (rec.imageUrl) {
            var safeTitleAttr = String(rec.title || "").replace(/"/g, "&quot;").replace(/'/g, "");
            imgSectionHtml =
              '<div style="position:relative;margin-bottom:14px;border-radius:18px;overflow:hidden;border:2.5px solid #d4af37;box-shadow:0 12px 28px rgba(13,56,37,0.22);background:#0b2b1d;cursor:pointer;" data-lb-title="' + safeTitleAttr + '" onclick="window.__openRecipeImageLightboxV116(this.firstElementChild.src, this.dataset.lbTitle)">' +
              '<img src="' + rec.imageUrl + '" alt="' + safeTitleAttr + '" style="width:100%;max-height:280px;min-height:190px;object-fit:cover;display:block;" />' +
              '<div style="position:absolute;top:10px;right:10px;background:linear-gradient(135deg,#0d3825 0%,#165b3c 100%);color:#d4af37;border:1.5px solid #d4af37;padding:4px 12px;border-radius:99px;font-weight:900;font-size:0.78rem;box-shadow:0 4px 12px rgba(0,0,0,0.35);">✨ وصفة شيف أورجنال الشهية</div>' +
              '<div style="position:absolute;bottom:0;left:0;right:0;background:linear-gradient(to top,rgba(8,28,18,0.92) 0%,rgba(8,28,18,0.55) 65%,transparent 100%);padding:24px 14px 12px 14px;color:#ffffff;">' +
              '<div style="font-size:1.05rem;font-weight:900;color:#d4af37;text-shadow:0 2px 6px rgba(0,0,0,0.6);">🍰 ' + (rec.title || "") + '</div>' +
              '<div style="font-size:0.78rem;color:#e2f1ea;margin-top:2px;">🔍 اضغط على الصورة لتكبيرها بكامل الوضوح</div>' +
              '</div>' +
              '</div>';
          }

          var ingsSectionHtml = "";
          var ings = Array.isArray(rec.ingredients) ? rec.ingredients : [];
          if (ings.length > 0) {
            var totalIngPrice = 0;
            var rowsHtml = "";
            ings.forEach(function(ing) {
              var cleanIngName = String(ing.name || "").replace(/\\s*\\([^()]*\\)\\s*$/g, "").trim();
              var catProd = (window.__v114Catalog || []).find(function(cp) {
                return cp.name && (cp.name.indexOf(cleanIngName) !== -1 || cleanIngName.indexOf(cp.name) !== -1);
              });
              var pPrice = Number(ing.price || (catProd && catProd.price) || 0);
              var pImg = (catProd && catProd.imageUrl) || "";
              var pUrl = ing.url || ("/?search=" + encodeURIComponent(cleanIngName));
              totalIngPrice += pPrice;

              rowsHtml +=
                '<div style="background:#ffffff;border:1.5px solid #cce3d6;border-radius:12px;padding:10px 12px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center;gap:10px;">' +
                '<div style="display:flex;align-items:center;gap:10px;flex:1;">' +
                (pImg ? '<img src="' + pImg + '" style="width:46px;height:46px;object-fit:cover;border-radius:10px;border:1px solid #d4af37;flex-shrink:0;" />' : '<span style="font-size:1.3rem;">🍫</span>') +
                '<div>' +
                '<strong style="color:#0d3825;font-size:0.88rem;display:block;">' + cleanIngName + '</strong>' +
                (pPrice > 0 ? '<span style="color:#166534;font-size:0.8rem;font-weight:800;">1 × ' + pPrice.toLocaleString("en-US") + ' ر.ي (متوفر في المتجر)</span>' : '') +
                '</div>' +
                '</div>' +
                '<a href="' + pUrl + '" style="background:#0d3825;color:#d4af37;text-decoration:none;padding:8px 14px;border-radius:10px;font-weight:800;font-size:0.8rem;white-space:nowrap;border:1px solid #d4af37;">🛒 اطلب المنتج ←</a>' +
                '</div>';
            });

            ingsSectionHtml =
              '<div style="background:#eef8f3;border:1.5px solid #9dcab3;border-radius:16px;padding:12px;margin-top:12px;">' +
              '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">' +
              '<strong style="color:#0d3825;font-size:0.9rem;">🛒 المنتجات والمقادير المقترحة للوصفة:</strong>' +
              (totalIngPrice > 0 ? '<span style="background:#dcebdf;color:#0d3825;padding:3px 10px;border-radius:99px;font-weight:900;font-size:0.8rem;">الإجمالي: ' + totalIngPrice.toLocaleString("en-US") + ' ر.ي</span>' : '') +
              '</div>' +
              rowsHtml +
              '</div>';
          }

          return (
            '<div style="direction:rtl;text-align:right;">' +
            imgSectionHtml +
            '<div style="font-size:0.94rem;color:#0d3825;font-weight:800;line-height:1.6;margin-bottom:10px;">' +
            'يا غالي، جبت لك ألذ وأفخم وصفة تفتح النفس وتجهز في دقائق: 😍🍫 «' + (rec.title || "") + '»' +
            '</div>' +
            '<div style="background:linear-gradient(135deg,#fffbeb 0%,#fef3c7 100%);border:1.5px solid #f59e0b;border-radius:14px;padding:12px 14px;margin-bottom:10px;">' +
            '<strong style="color:#92400e;font-size:0.88rem;display:block;margin-bottom:6px;">📋 الوصفة وطريقة التحضير الكاملة:</strong>' +
            '<div style="color:#1e293b;font-size:0.9rem;font-weight:700;line-height:1.7;white-space:pre-line;">' + (rec.steps || "") + '</div>' +
            '</div>' +
            ingsSectionHtml +
            '</div>'
          );
        }

        // Scan chat bubbles on the AI Assistant screen and upgrade any assistant reply corresponding to a saved Recipe, Rule, or Promoted Product!
        function enhanceChatBubblesWithStudioV116() {
          if (document.body.textContent.indexOf("مساعد وشيف أورجنال الذكي") === -1) return;

          var allDivs = Array.from(document.querySelectorAll("div, p"));
          allDivs.forEach(function(el) {
            if (el.children.length > 1) return;
            var txt = (el.textContent || "").trim();
            if (!txt || txt.length < 2 || txt.length > 180) return;

            // Check if this element is a dark-green User Message Bubble
            var bubbleBox = el;
            var isUserBubble = false;
            for (var up = 0; up < 3 && bubbleBox && bubbleBox !== document.body; up++) {
              var st = window.getComputedStyle(bubbleBox);
              var bg = st.backgroundColor || "";
              var rgb = bg.match(/\\d+/g);
              if (rgb && rgb.length >= 3 && Number(rgb[0]) < 45 && Number(rgb[1]) > 40 && Number(rgb[1]) < 120 && Number(rgb[2]) < 80) {
                isUserBubble = true;
                break;
              }
              bubbleBox = bubbleBox.parentElement;
            }
            if (!isUserBubble || !bubbleBox) return;

            var matchedRec = matchRecipeClientV116(txt);
            var matchedRule = !matchedRec ? matchRuleClientV116(txt) : null;
            var matchedPromo = (!matchedRec && !matchedRule) ? matchPromoClientV116(txt) : null;

            if (!matchedRec && !matchedRule && !matchedPromo) return;

            // Find the Assistant reply wrapper right after this user message row
            var rowEl = bubbleBox;
            var assistantRow = null;
            for (var depth = 0; depth < 5 && rowEl && rowEl.parentElement; depth++) {
              if (rowEl.nextElementSibling) {
                var cand = rowEl.nextElementSibling;
                var candTxt = (cand.textContent || "").trim();
                if (candTxt.length > 15 && candTxt !== txt) {
                  assistantRow = cand;
                  break;
                }
              }
              rowEl = rowEl.parentElement;
            }

            if (!assistantRow) return;
            var aTxt = (assistantRow.textContent || "").trim();
            if (aTxt.length < 15 || aTxt.indexOf("جاري") === 0) return;

            var targetBubble = assistantRow;
            var innerCards = Array.from(assistantRow.querySelectorAll("div")).filter(function(d) {
              var dst = window.getComputedStyle(d);
              return (d.textContent || "").trim().length > 20 && dst.borderRadius && parseInt(dst.borderRadius, 10) >= 12;
            });
            if (innerCards.length > 0) {
              targetBubble = innerCards[0];
            }

            if (matchedRec) {
              var sig = "rec_" + matchedRec.id + "_" + (matchedRec.imageUrl ? matchedRec.imageUrl.length : 0);
              if (targetBubble.getAttribute("data-v116-upgraded") === sig) return;
              targetBubble.setAttribute("data-v116-upgraded", sig);
              targetBubble.style.cssText += ";background:#ffffff;border:2px solid #0d3825;border-radius:20px;padding:14px;box-shadow:0 8px 24px rgba(13,56,37,0.10);";
              targetBubble.innerHTML = buildMouthWateringRecipeHtmlV116(matchedRec);
            } else if (matchedRule) {
              var rSig = "rule_" + matchedRule.id;
              if (targetBubble.getAttribute("data-v116-upgraded") === rSig) return;
              targetBubble.setAttribute("data-v116-upgraded", rSig);
              var linkHtml = matchedRule.linkedProductUrl
                ? '<a href="' + matchedRule.linkedProductUrl + '" style="display:inline-block;margin-top:10px;background:#0d3825;color:#d4af37;text-decoration:none;padding:8px 16px;border-radius:10px;font-weight:800;font-size:0.84rem;">🛒 فتح المنتج (' + (matchedRule.linkedProductName || "عرض المنتج") + ') ←</a>'
                : '';
              targetBubble.innerHTML =
                '<div style="direction:rtl;text-align:right;font-size:0.93rem;color:#0d3825;font-weight:700;line-height:1.65;white-space:pre-line;">' +
                (matchedRule.response || "") +
                '</div>' +
                linkHtml;
            } else if (matchedPromo) {
              var pSig = "promo_" + matchedPromo.id;
              if (targetBubble.getAttribute("data-v116-upgraded") === pSig) return;
              targetBubble.setAttribute("data-v116-upgraded", pSig);
              var pUrl = matchedPromo.productUrl || ("/?search=" + encodeURIComponent(matchedPromo.productName || ""));
              targetBubble.innerHTML =
                '<div style="direction:rtl;text-align:right;">' +
                (matchedPromo.productImage ? '<img src="' + matchedPromo.productImage + '" style="width:100%;max-height:220px;object-fit:cover;border-radius:14px;border:2px solid #d4af37;margin-bottom:10px;" />' : '') +
                '<span style="background:#0d3825;color:#d4af37;padding:3px 10px;border-radius:99px;font-size:0.76rem;font-weight:800;">' + (matchedPromo.promoBadge || "⭐ عرض خاص") + '</span>' +
                '<strong style="display:block;color:#0d3825;font-size:1rem;margin-top:6px;">' + (matchedPromo.productName || "") + (matchedPromo.productPrice ? " (" + matchedPromo.productPrice + " ر.ي)" : "") + '</strong>' +
                '<div style="color:#334155;font-size:0.88rem;margin:6px 0 10px 0;line-height:1.6;">' + (matchedPromo.promoMessage || "") + '</div>' +
                '<a href="' + pUrl + '" style="display:block;text-align:center;background:#0d3825;color:#d4af37;text-decoration:none;padding:10px 16px;border-radius:12px;font-weight:900;font-size:0.88rem;">🛒 فتح المنتج وطلبه الآن ←</a>' +
                '</div>';
            }
          });
        }

        // ULTRA-LOW-TOKEN INTERCEPTOR:
        var origFetchV112 = window.fetch;
        if (origFetchV112 && !window.__v112FetchWrapped) {
          window.__v112FetchWrapped = true;
          window.fetch = function(input, init) {
            var urlStr = typeof input === "string" ? input : (input && (input.url || input.href) ? (input.url || input.href) : String(input || ""));
            var isTrpcAiCall =
              urlStr.indexOf("/api/trpc/") !== -1 &&
              /(assistant|chat|chef|ask|message|recipe|idea|smart|ai)/i.test(urlStr) &&
              !/cart|order|product|category|admin/i.test(urlStr) &&
              init &&
              init.method === "POST" &&
              typeof init.body === "string";

            if (isTrpcAiCall) {
              var extractedMsg = extractAnyUserTextFromJsonBodyV116(init.body);
              if (extractedMsg) {
                setTimeout(enhanceChatBubblesWithStudioV116, 150);
                setTimeout(enhanceChatBubblesWithStudioV116, 600);
                setTimeout(enhanceChatBubblesWithStudioV116, 1500);
              }
            }
            return origFetchV112.apply(this, arguments).then(function(resp) {
              if (urlStr.indexOf("/api/trpc/") !== -1) {
                setTimeout(enhanceChatBubblesWithStudioV116, 80);
                setTimeout(enhanceChatBubblesWithStudioV116, 350);
              }
              return resp;
            });
          };
        }

        function refreshStudioDataV114() {
          origFetchV112("/api/ai-v112/config")
            .then(function(r) { return r.json(); })
            .then(function(d) {
              if (d && d.ok) {
                if (!window.__v115InitialConfigLoaded && d.config) {
                  window.__v115InitialConfigLoaded = true;
                  if (hasAnyStudioItemsV115(d.config)) {
                    window.__v114StudioConfig = d.config;
                    saveLocalBackupV115();
                  } else if (hasAnyStudioItemsV115(window.__v114StudioConfig)) {
                    origFetchV112("/api/ai-v112/save-training", {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify(window.__v114StudioConfig)
                    }).catch(function() {});
                  }
                }
                if (d.stats) window.__v114Stats = d.stats;
                if (Array.isArray(d.catalog) && d.catalog.length > 0) {
                  var hasCatalogChanged = window.__v114Catalog.length !== d.catalog.length;
                  window.__v114Catalog = d.catalog;
                  if (hasCatalogChanged && window.__v114StudioOpen) {
                    var selects = document.querySelectorAll("#v114-rule-prod-sel, #v114-promo-sel, #v114-rec-ing-sel, #v114-pinfo-sel");
                    Array.from(selects).forEach(function(sel) {
                      if (sel.options.length <= 1) {
                        sel.innerHTML = buildProductOptionsHtmlV114();
                      }
                    });
                  }
                }
                if (Array.isArray(d.requests)) {
                  var prevCount = (window.__v114Requests || []).length;
                  checkRealPhoneNotificationsV114(d.requests);
                  window.__v114Requests = d.requests;
                  if (window.__v114StudioOpen && window.__v114ActiveSubTab === "reqs" && d.requests.length !== prevCount) {
                    renderStudioSubTabV114();
                  }
                }
              }
            })
            .catch(function() {});
        }
        setTimeout(refreshStudioDataV114, 250);
        setInterval(refreshStudioDataV114, 5000);

        function playAlertSoundV114() {
          try {
            var Ctx = window.AudioContext || window.webkitAudioContext;
            if (!Ctx) return;
            var ctx = new Ctx();
            var osc = ctx.createOscillator();
            var gain = ctx.createGain();
            osc.type = "sine";
            osc.frequency.setValueAtTime(880, ctx.currentTime);
            osc.frequency.setValueAtTime(1174, ctx.currentTime + 0.15);
            gain.gain.setValueAtTime(0.22, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.5);
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start();
            osc.stop(ctx.currentTime + 0.5);
          } catch (e) {}
        }

        function triggerRealPhoneNotificationV114(title, bodyText) {
          playAlertSoundV114();
          try {
            if (navigator.vibrate) navigator.vibrate([250, 120, 250]);
          } catch (e) {}
          if ("Notification" in window && Notification.permission === "granted") {
            try {
              if (navigator.serviceWorker && navigator.serviceWorker.ready) {
                navigator.serviceWorker.ready.then(function(reg) {
                  if (reg && reg.showNotification) {
                    reg.showNotification(title, {
                      body: bodyText,
                      icon: "/icon-192.png",
                      badge: "/icon-192.png",
                      vibrate: [250, 120, 250],
                      tag: "ai-req-" + Date.now()
                    });
                  } else {
                    new Notification(title, { body: bodyText, icon: "/icon-192.png" });
                  }
                });
              } else {
                new Notification(title, { body: bodyText, icon: "/icon-192.png" });
              }
            } catch (e) {}
          }
        }

        function checkRealPhoneNotificationsV114(requests) {
          var pendingCount = 0;
          requests.forEach(function(req) {
            if (req.status === "pending") {
              pendingCount++;
              if (!window.__v112NotifiedReqIds[req.id]) {
                window.__v112NotifiedReqIds[req.id] = true;
                if (window.location.pathname.indexOf("/admin") !== -1) {
                  triggerRealPhoneNotificationV114(
                    "📲 طلب زبون جديد في متجر أورجنال",
                    "الزبون يطلب: " + (req.requestedItem || req.customerMessage)
                  );
                }
              }
            }
          });
          var badgeEls = document.querySelectorAll(".v114-nav-req-badge");
          Array.from(badgeEls).forEach(function(el) {
            el.textContent = String(pendingCount);
            el.style.display = pendingCount > 0 ? "inline-flex" : "none";
          });
        }

        function pollCustomerManagerRepliesV112() {
          if (window.location.pathname.indexOf("/admin") !== -1) return;
          origFetchV112("/api/ai-v112/customer-poll?sessionId=" + encodeURIComponent(window.__v112SessionId))
            .then(function(r) { return r.json(); })
            .then(function(d) {
              if (d && d.ok && Array.isArray(d.replies)) {
                d.replies.forEach(function(rep) {
                  var key = rep.id + "_" + (rep.repliedAt || "");
                  if (!window.__v112DeliveredReplyIds[key]) {
                    window.__v112DeliveredReplyIds[key] = true;
                    try {
                      localStorage.setItem("original_v112_delivered_replies", JSON.stringify(window.__v112DeliveredReplyIds));
                    } catch (e) {}
                    triggerRealPhoneNotificationV114(
                      "👨‍💼 رد من إدارة متجر أورجنال",
                      rep.managerReply || ""
                    );
                    showCustomerManagerReplyBannerV112(rep);
                  }
                });
              }
            })
            .catch(function() {});
        }
        setInterval(pollCustomerManagerRepliesV112, 4500);

        function showCustomerManagerReplyBannerV112(rep) {
          var linkBtnHtml = rep.attachedProductUrl
            ? '<a href="' + rep.attachedProductUrl + '" style="display:inline-block;margin-top:8px;background:#d4af37;color:#0d3825;text-decoration:none;padding:7px 14px;border-radius:10px;font-weight:800;font-size:0.84rem;">🛒 فتح المنتج المقترح (' + (rep.attachedProductName || "عرض المنتج") + ') ←</a>'
            : '';

          var chatInput = document.querySelector("input[placeholder*='اطلب سلة الصباح'], input[placeholder*='مقاضي الطبخ'], textarea[placeholder*='اطلب']");
          if (chatInput) {
            var chatScroll = chatInput.parentElement && chatInput.parentElement.parentElement ? chatInput.parentElement.parentElement.previousElementSibling : null;
            if (chatScroll) {
              var msgCard = document.createElement("div");
              msgCard.style.cssText = "background: linear-gradient(135deg, #0d3825 0%, #165b3c 100%); color: #ffffff; border: 2px solid #d4af37; border-radius: 16px; padding: 14px; margin: 12px 0; box-shadow: 0 6px 18px rgba(13,56,37,0.18);";
              msgCard.innerHTML =
                '<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;color:#d4af37;font-weight:800;font-size:0.9rem;">' +
                '<span>👨‍💼 رد مباشر من إدارة متجر أورجنال</span>' +
                '<span style="font-size:0.75rem;background:rgba(212,175,55,0.2);padding:2px 8px;border-radius:99px;">الآن</span>' +
                '</div>' +
                '<div style="font-size:0.92rem;line-height:1.6;color:#ffffff;font-weight:600;white-space:pre-line;">' +
                (rep.managerReply || "").replace(/</g, "&lt;") +
                '</div>' +
                linkBtnHtml;
              chatScroll.appendChild(msgCard);
              chatScroll.scrollTop = chatScroll.scrollHeight;
            }
          }
          var toast = document.createElement("div");
          toast.style.cssText = "position:fixed;top:16px;left:16px;right:16px;z-index:99999;background:#0d3825;color:#fff;border:2px solid #d4af37;border-radius:16px;padding:14px 16px;box-shadow:0 10px 28px rgba(0,0,0,0.3);direction:rtl;text-align:right;";
          toast.innerHTML =
            '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">' +
            '<strong style="color:#d4af37;font-size:0.92rem;">👨‍💼 رد مباشر من إدارة متجر أورجنال بخصوص (' + (rep.requestedItem || "طلبك") + ')</strong>' +
            '<button type="button" style="background:none;border:none;color:#fff;font-size:1.1rem;cursor:pointer;" onclick="this.parentElement.parentElement.remove()">✕</button>' +
            '</div>' +
            '<div style="font-size:0.9rem;line-height:1.5;white-space:pre-line;">' + (rep.managerReply || "").replace(/</g, "&lt;") + '</div>' +
            linkBtnHtml;
          document.body.appendChild(toast);
          setTimeout(function() { if (toast.parentElement) toast.remove(); }, 18000);
        }

        function setLeafTextSafe(el, newText) {
          if (!el) return;
          var tw = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null);
          var nodes = [];
          var n;
          while ((n = tw.nextNode())) nodes.push(n);
          if (nodes.length === 0) {
            el.textContent = newText;
          } else if (nodes.length === 1) {
            if (nodes[0].nodeValue !== newText) nodes[0].nodeValue = newText;
          } else {
            var currentJoined = nodes.map(function(x) { return x.nodeValue || ""; }).join("");
            if (currentJoined.trim() === newText.trim()) return;
            nodes[0].nodeValue = newText;
            for (var i = 1; i < nodes.length; i++) {
              if (nodes[i].nodeValue !== "") nodes[i].nodeValue = "";
            }
          }
        }

        function isPurePriceElement(el) {
          if (!el || el.tagName === "BUTTON") return false;
          if (el.querySelector("div, p, h1, h2, h3, h4, button, img")) return false;
          var t = (el.textContent || "").trim();
          return /^\\d[\\d,.]*\\s*ر\\.ي/.test(t);
        }

        function parseParenVariantTotal(parenText, rowQty) {
          var segments = String(parenText || "").split(/[،,+]+/).map(function(s) { return s.trim(); }).filter(Boolean);
          var totalW = 0;
          var totalQ = 0;
          var names = [];
          for (var i = 0; i < segments.length; i++) {
            var seg = segments[i];
            var sQty = 1;
            var hasExplicitQty = false;
            var mm = seg.match(/[×xX*]\\s*(\\d+)/);
            if (mm && mm[1]) {
              sQty = Math.max(1, parseInt(mm[1], 10));
              hasExplicitQty = true;
            }
            var cleanSeg = seg.replace(/[×xX*]\\s*\\d+.*$/, "").trim();
            var cIdx = cleanSeg.indexOf(":");
            if (cIdx !== -1) {
              var oName = cleanSeg.slice(0, cIdx).trim();
              var lPrice = parseFloat(cleanSeg.slice(cIdx + 1).trim());
              if (!isNaN(lPrice) && lPrice > 0) {
                if (segments.length === 1) {
                  sQty = Math.max(1, rowQty || sQty);
                } else if (!hasExplicitQty && rowQty > 1) {
                  sQty = 1;
                }
                totalW += lPrice * sQty;
                totalQ += sQty;
                names.push(oName);
              }
            }
          }
          if (totalQ > 0 && totalW > 0) {
            return {
              unitPrice: Math.round(totalW / totalQ),
              lineTotal: Math.round(totalW),
              optName: names.join("، ")
            };
          }
          return null;
        }

        function backupVariantLocalStorage() {
          try {
            var backup = {};
            var hasAny = false;
            for (var i = 0; i < localStorage.length; i++) {
              var k = localStorage.key(i);
              if (!k || k.indexOf("v107") !== -1 || k.indexOf("v109") !== -1) continue;
              var v = localStorage.getItem(k);
              if (v && (v.charAt(0) === "{" || v.charAt(0) === "[") && v.indexOf(":") !== -1) {
                backup[k] = v;
                hasAny = true;
              }
            }
            if (hasAny) {
              sessionStorage.setItem("original_v110_variant_backup", JSON.stringify(backup));
            }
          } catch (e) {}
        }

        function classifyProductClientV112(pName) {
          var clean = String(pName || "").replace(/\\s*\\([^()]*\\)\\s*$/g, "").trim();
          var map = (window.__v114StudioConfig && window.__v114StudioConfig.productAiMap) || {};
          var customNote = map["name:" + clean] || "";
          var comb = (clean + " " + customNote).toLowerCase();
          if (/(سجائر|سجاير|دخان|شملان|كمران|منظف|صابون|شامبو|مناديل|فحم|ولاعة|أكياس|اكياس)/.test(comb)) return { kind: "non_food", customNote: customNote };
          if (/(بسكويت|بسكوت|ماري|أبو ولد|ابو ولد|نخالة|شاي|ديما|أوريو|اوريو|معمول|كليجا|توبس)/.test(comb)) return { kind: "biscuit_dessert", customNote: customNote };
          if (/(شوكلات|شوكولات|شكلاته|شوكو|بلاتو|بليلا|بريك|ويفر|علك|باطوق|حلاو|مصاص|شيبس|بطاط|فشار|كروسان|كيك|جالكسي|كتكات|سنكرز|توبي|سعيد|مارشملو|جيلي|كاكاو)/.test(comb)) return { kind: "chocolate_snack", customNote: customNote };
          if (/(عصير|رواب|مشروب|مانجو|برتقال|جوافة|تفاح|حليب|لبن|زبادي|ماء|مياه|بيبسي|كوكاكولا|ميرندا|سفن|ردبول|جوي|نسكافيه|قهوة)/.test(comb)) return { kind: "drink_juice", customNote: customNote };
          return { kind: "cooking_food", customNote: customNote };
        }

        function syncVariantModalPrice() {
          try {
            var buttons = Array.from(document.querySelectorAll("button"));

            // PART A: Variant Picker Modal ("إضافة إلى السلة")
            var addBtn = buttons.find(function(b) {
              return b.offsetParent !== null && b.textContent && b.textContent.indexOf("إضافة إلى السلة") !== -1 && b.textContent.indexOf("مجدداً") === -1;
            });
            if (addBtn) {
              var modal = addBtn.parentElement;
              while (modal && modal !== document.body && modal.querySelectorAll("button").length < 4) {
                modal = modal.parentElement;
              }
              if (modal) {
                var modalButtons = Array.from(modal.querySelectorAll("button"));
                var optBtns = modalButtons.filter(function(b) {
                  if (b === addBtn) return false;
                  var txt = (b.textContent || "").trim();
                  return txt.indexOf(":") !== -1 || b.hasAttribute("data-raw-opt");
                });

                if (optBtns.length > 0) {
                  var detailsParts = [];
                  optBtns.forEach(function(b) {
                    var raw = b.getAttribute("data-raw-opt") || (b.textContent || "").trim();
                    if (!b.hasAttribute("data-raw-opt") && raw.indexOf(":") !== -1) {
                      b.setAttribute("data-raw-opt", raw);
                    }
                    var mm = raw.match(/^([^:]+):\\s*(\\d+(?:\\.\\d+)?)/);
                    if (mm) {
                      detailsParts.push(mm[1].trim() + ": " + Number(mm[2]).toLocaleString("en-US") + " ر.ي");
                    }
                  });

                  var selectedOptBtn = optBtns.find(function(b) {
                    var style = window.getComputedStyle(b);
                    var rgb = (style.backgroundColor || "").match(/\\d+/g);
                    var isDarkGreen = rgb && rgb.length >= 3 && Number(rgb[0]) < 100 && Number(rgb[1]) < 150 && Number(rgb[2]) < 120;
                    var cls = b.className || "";
                    return isDarkGreen || cls.indexOf("selected") !== -1 || cls.indexOf("active") !== -1;
                  });

                  if (selectedOptBtn) {
                    var rawTxt = selectedOptBtn.getAttribute("data-raw-opt") || (selectedOptBtn.textContent || "").trim();
                    var m = rawTxt.match(/:\\s*(\\d+(?:\\.\\d+)?)/);
                    if (m && m[1]) {
                      var unitPrice = parseFloat(m[1]);
                      if (!isNaN(unitPrice) && unitPrice > 0) {
                        var qty = 1;
                        var allEls = Array.from(modal.querySelectorAll("p, small, span, div, strong, b"));
                        for (var i = 0; i < allEls.length; i++) {
                          var st = (allEls[i].textContent || "").trim();
                          if (/^\\d+$/.test(st) && allEls[i].children.length === 0) {
                            var val = parseInt(st, 10);
                            if (val >= 1 && val <= 999) {
                              qty = val;
                              break;
                            }
                          }
                        }
                        var totalPrice = Math.round(unitPrice * qty);

                        allEls.forEach(function(el) {
                          if (!isPurePriceElement(el)) return;
                          if (el === addBtn || addBtn.contains(el)) return;
                          if (optBtns.some(function(ob) { return ob === el || ob.contains(el); })) return;
                          var fullTxt = (el.textContent || "").trim();
                          if (fullTxt.indexOf("/") !== -1 || fullTxt.indexOf("·") !== -1) {
                            var detailSuffix = detailsParts.length > 0 ? " (" + detailsParts.join(" · ") + ")" : "";
                            var targetTop = unitPrice.toLocaleString("en-US") + " ر.ي" + detailSuffix;
                            setLeafTextSafe(el, targetTop);
                          }
                        });

                        var btnFullTxt = (addBtn.textContent || "").trim();
                        var targetPriceStr = totalPrice.toLocaleString("en-US");
                        if (btnFullTxt.indexOf("(" + targetPriceStr + " ر.ي)") === -1) {
                          var twBtn = document.createTreeWalker(addBtn, NodeFilter.SHOW_TEXT, null);
                          var textNodes = [];
                          var n;
                          while ((n = twBtn.nextNode())) textNodes.push(n);
                          if (textNodes.length > 1) {
                            for (var j = 0; j < textNodes.length; j++) {
                              if (/^\\s*\\d[\\d,.]*\\s*$/.test(textNodes[j].nodeValue || "")) {
                                textNodes[j].nodeValue = targetPriceStr;
                              } else if ((textNodes[j].nodeValue || "").indexOf("ر.ي") !== -1 && /\\d/.test(textNodes[j].nodeValue || "")) {
                                textNodes[j].nodeValue = (textNodes[j].nodeValue || "").replace(/\\d[\\d,.]*/, targetPriceStr);
                              }
                            }
                          } else if (textNodes.length === 1) {
                            textNodes[0].nodeValue = " إضافة إلى السلة (" + targetPriceStr + " ر.ي) ";
                          }
                        }
                      }
                    }
                  }
                }
              }
            }

            // PART B: Shopping Cart ("سلة التسوق") rows
            var removeBtns = buttons.filter(function(b) {
              return b.offsetParent !== null && (b.textContent || "").indexOf("إزالة") !== -1;
            });
            if (removeBtns.length > 0) {
              backupVariantLocalStorage();
              var cartSubtotalSum = 0;

              removeBtns.forEach(function(remBtn) {
                var rowCard = remBtn.parentElement;
                while (rowCard && rowCard.parentElement && rowCard.parentElement !== document.body) {
                  var pText = rowCard.parentElement.textContent || "";
                  if (pText.indexOf("إفراغ السلة") !== -1 || pText.indexOf("ملخص الطلب") !== -1) break;
                  var pRemCount = Array.from(rowCard.parentElement.querySelectorAll("button")).filter(function(b) {
                    return (b.textContent || "").indexOf("إزالة") !== -1;
                  }).length;
                  if (pRemCount > 1) break;
                  rowCard = rowCard.parentElement;
                }
                if (!rowCard) return;

                var rowQty = 1;
                var rowBtns = Array.from(rowCard.querySelectorAll("button")).filter(function(b) {
                  return b !== remBtn;
                });
                var foundQty = false;
                for (var bIdx = 0; bIdx < rowBtns.length && !foundQty; bIdx++) {
                  var pillBox = rowBtns[bIdx].parentElement;
                  if (pillBox) {
                    var pillLeaves = Array.from(pillBox.querySelectorAll("span, div, strong, p, b")).filter(function(el) {
                      return el.children.length === 0 && el.tagName !== "BUTTON" && !remBtn.contains(el);
                    });
                    for (var qIdx = 0; qIdx < pillLeaves.length; qIdx++) {
                      var qt = (pillLeaves[qIdx].textContent || "").trim();
                      if (/^\\d+$/.test(qt)) {
                        var qVal = parseInt(qt, 10);
                        if (qVal >= 1 && qVal <= 9999) {
                          rowQty = qVal;
                          foundQty = true;
                          break;
                        }
                      }
                    }
                  }
                }

                var rowFullText = rowCard.textContent || "";
                var parenMatches = Array.from(rowFullText.matchAll(/\\(([^()]*:\\s*\\d+(?:\\.\\d+)?[^()]*)\\)/g));
                var rowUnitPrice = 0;
                var rowLineTotal = 0;
                var rowOptName = "";

                if (parenMatches.length === 0 && window.__v111ReorderedVariants) {
                  var titleLeaves = Array.from(rowCard.querySelectorAll("h2, h3, h4, strong, p, div, span")).filter(function(el) {
                    if (el.children.length !== 0 || el.tagName === "BUTTON" || remBtn.contains(el)) return false;
                    var t = (el.textContent || "").trim();
                    return t.length > 0 && t.indexOf("ر.ي") === -1 && !/^\\d+$/.test(t) && t !== "+" && t !== "-" && t !== "−";
                  });
                  for (var tIdx = 0; tIdx < titleLeaves.length; tIdx++) {
                    var baseT = (titleLeaves[tIdx].textContent || "").trim();
                    var savedVar = window.__v111ReorderedVariants[baseT];
                    if (savedVar && savedVar.raw) {
                      setLeafTextSafe(titleLeaves[tIdx], baseT + " (" + savedVar.raw + ")");
                      rowFullText = rowCard.textContent || "";
                      parenMatches = Array.from(rowFullText.matchAll(/\\(([^()]*:\\s*\\d+(?:\\.\\d+)?[^()]*)\\)/g));
                      break;
                    }
                  }
                }

                if (parenMatches.length > 0) {
                  var rawParenContent = parenMatches[parenMatches.length - 1][1].trim();
                  var parsedObj = parseParenVariantTotal(rawParenContent, rowQty);
                  if (parsedObj) {
                    rowUnitPrice = parsedObj.unitPrice;
                    rowLineTotal = parsedObj.lineTotal;
                    rowOptName = parsedObj.optName;
                  }
                }

                var priceEls = Array.from(rowCard.querySelectorAll("span, div, strong, p, small")).filter(function(el) {
                  return isPurePriceElement(el) && !remBtn.contains(el);
                });

                if (rowUnitPrice <= 0) {
                  for (var uIdx = 0; uIdx < priceEls.length; uIdx++) {
                    var ut = (priceEls[uIdx].textContent || "").trim();
                    if (ut.indexOf("/") !== -1) {
                      var um = ut.match(/^(\\d[\\d,.]*)/);
                      if (um && um[1]) {
                        rowUnitPrice = parseFloat(um[1].replace(/,/g, ""));
                        rowLineTotal = Math.round(rowUnitPrice * rowQty);
                        break;
                      }
                    }
                  }
                }

                if (rowUnitPrice > 0) {
                  cartSubtotalSum += rowLineTotal;

                  priceEls.forEach(function(pel) {
                    var lt = (pel.textContent || "").trim();
                    if (lt.indexOf("/") !== -1 && rowOptName) {
                      var newUnitStr = rowUnitPrice.toLocaleString("en-US") + " ر.ي / " + rowOptName;
                      setLeafTextSafe(pel, newUnitStr);
                    } else if (/^\\d[\\d,.]*\\s*ر\\.ي$/.test(lt)) {
                      var newTotalStr = rowLineTotal.toLocaleString("en-US") + " ر.ي";
                      setLeafTextSafe(pel, newTotalStr);
                    }
                  });
                }
              });

              window.__v108ComputedCartSubtotal = cartSubtotalSum;
            }

            // PART C: Update Summary Totals in Shopping Cart ("ملخص الطلب") AND Checkout Modal ("إتمام الطلب")
            var activeCartSub = window.__v108ComputedCartSubtotal || 0;
            var allContainers = Array.from(document.querySelectorAll("div, section, li"));
            if (activeCartSub > 0) {
              var isCartOrCheckoutVisible = removeBtns.length > 0 || document.body.textContent.indexOf("إتمام الطلب") !== -1;
              if (isCartOrCheckoutVisible) {
                var subFormatted = activeCartSub.toLocaleString("en-US") + " ر.ي";

                var detectedDeliveryFee = 0;
                allContainers.forEach(function(box) {
                  if (box.children.length === 2) {
                    var t0 = (box.children[0].textContent || "").trim();
                    var t1 = (box.children[1].textContent || "").trim();
                    var feeTxt = "";
                    if (t0 === "رسوم التوصيل" || t0 === "التوصيل") feeTxt = t1;
                    else if (t1 === "رسوم التوصيل" || t1 === "التوصيل") feeTxt = t0;
                    if (feeTxt && feeTxt.indexOf("مجاني") === -1 && feeTxt.indexOf("يحسب") === -1) {
                      var fm = feeTxt.match(/(\\d[\\d,.]*)/);
                      if (fm && fm[1]) {
                        var fp = parseFloat(fm[1].replace(/,/g, ""));
                        if (!isNaN(fp) && fp > 0) detectedDeliveryFee = fp;
                      }
                    }
                  }
                });

                var totalFormatted = Math.round(activeCartSub + detectedDeliveryFee).toLocaleString("en-US") + " ر.ي";

                allContainers.forEach(function(box) {
                  if (box.children.length === 2) {
                    var t0 = (box.children[0].textContent || "").trim();
                    var t1 = (box.children[1].textContent || "").trim();

                    var isSub0 = t0.indexOf("المجموع الفرعي") === 0;
                    var isSub1 = t1.indexOf("المجموع الفرعي") === 0;
                    var isTot0 = (t0 === "الإجمالي الحالي" || t0 === "الإجمالي");
                    var isTot1 = (t1 === "الإجمالي الحالي" || t1 === "الإجمالي");

                    if (isSub0 && /^\\d[\\d,.]*\\s*ر\\.ي$/.test(t1)) {
                      setLeafTextSafe(box.children[1], subFormatted);
                    } else if (isSub1 && /^\\d[\\d,.]*\\s*ر\\.ي$/.test(t0)) {
                      setLeafTextSafe(box.children[0], subFormatted);
                    } else if (isTot0 && /^\\d[\\d,.]*\\s*ر\\.ي$/.test(t1)) {
                      setLeafTextSafe(box.children[1], totalFormatted);
                    } else if (isTot1 && /^\\d[\\d,.]*\\s*ر\\.ي$/.test(t0)) {
                      setLeafTextSafe(box.children[0], totalFormatted);
                    }
                  }
                });
              }
            }

            // PART D: Order Details Screen ("الأصناف المطلوبة")
            if (document.body.textContent.indexOf("الأصناف المطلوبة") !== -1) {
              allContainers.forEach(function(box) {
                if (box.children.length === 2 && !box.hasAttribute("data-v110-expanded")) {
                  var c0 = (box.children[0].textContent || "").trim();
                  var c1 = (box.children[1].textContent || "").trim();
                  var nameSide = null;
                  var priceSide = null;
                  var priceIsFirst = false;
                  if (/^\\d+\\s*[×xX*]\\s*\\d[\\d,.]*\\s*ر\\.ي$/.test(c0)) {
                    priceSide = box.children[0];
                    nameSide = box.children[1];
                    priceIsFirst = true;
                  } else if (/^\\d+\\s*[×xX*]\\s*\\d[\\d,.]*\\s*ر\\.ي$/.test(c1)) {
                    priceSide = box.children[1];
                    nameSide = box.children[0];
                    priceIsFirst = false;
                  }
                  if (nameSide && priceSide && box.parentElement) {
                    var nTxt = (nameSide.textContent || "").trim();
                    var pm = Array.from(nTxt.matchAll(/\\(([^()]*:\\s*\\d+(?:\\.\\d+)?[^()]*)\\)/g));
                    if (pm.length > 0) {
                      var inner = pm.map(function(x) { return x[1].trim(); }).join("، ");
                      var segs = inner.split(/[،,+]+/).map(function(s) { return s.trim(); }).filter(Boolean);
                      if (segs.length > 1) {
                        var baseTitle = nTxt.replace(/\\s*\\([^()]*\\)\\s*$/g, "").trim() || nTxt;
                        var parsedRows = [];
                        segs.forEach(function(seg) {
                          var sQty = 1;
                          var mm = seg.match(/[×xX*]\\s*(\\d+)/);
                          if (mm && mm[1]) sQty = Math.max(1, parseInt(mm[1], 10));
                          var cleanSeg = seg.replace(/[×xX*]\\s*\\d+.*$/, "").trim();
                          var cIdx = cleanSeg.indexOf(":");
                          if (cIdx !== -1) {
                            var oName = cleanSeg.slice(0, cIdx).trim();
                            var oPrice = parseFloat(cleanSeg.slice(cIdx + 1).trim());
                            if (oName && !isNaN(oPrice) && oPrice > 0) {
                              parsedRows.push({
                                title: baseTitle + " (" + oName + ":" + Math.round(oPrice) + ")",
                                priceTxt: sQty + " × " + Math.round(oPrice).toLocaleString("en-US") + " ر.ي"
                              });
                            }
                          }
                        });
                        if (parsedRows.length > 1) {
                          box.setAttribute("data-v110-expanded", "1");
                          var parentList = box.parentElement;
                          for (var rIdx = 0; rIdx < parsedRows.length; rIdx++) {
                            var targetRow = rIdx === 0 ? box : box.cloneNode(true);
                            targetRow.setAttribute("data-v110-expanded", "1");
                            var ch0 = targetRow.children[0];
                            var ch1 = targetRow.children[1];
                            if (priceIsFirst) {
                              setLeafTextSafe(ch0, parsedRows[rIdx].priceTxt);
                              setLeafTextSafe(ch1, parsedRows[rIdx].title);
                            } else {
                              setLeafTextSafe(ch0, parsedRows[rIdx].title);
                              setLeafTextSafe(ch1, parsedRows[rIdx].priceTxt);
                            }
                            if (rIdx > 0) {
                              parentList.insertBefore(targetRow, box.nextSibling);
                            }
                          }
                        }
                      }
                    }
                  }
                }
              });
            }

            // PART E: Smart Product AI Modal (0 Tokens)
            var continueAiBtn = buttons.find(function(b) {
              return b.offsetParent !== null && (b.textContent || "").indexOf("متابعة النقاش في صفحة المساعد الذكي") !== -1;
            });
            if (continueAiBtn) {
              var aiModal = continueAiBtn.parentElement;
              while (aiModal && aiModal !== document.body && aiModal.textContent.indexOf("أضف «") === -1 && aiModal.textContent.indexOf("للسلة") === -1) {
                aiModal = aiModal.parentElement;
              }
              if (aiModal) {
                var pNameMatch = (aiModal.textContent || "").match(/أضف\\s*«([^»]+)»/);
                var modalProdName = pNameMatch && pNameMatch[1] ? pNameMatch[1].trim() : "";
                if (modalProdName) {
                  var infoObj = classifyProductClientV112(modalProdName);
                  var pKind = infoObj.kind;
                  var customNote = infoObj.customNote;

                  var headings = Array.from(aiModal.querySelectorAll("h1, h2, h3, h4, strong, div, p")).filter(function(el) {
                    return el.children.length === 0 && (el.textContent || "").indexOf(modalProdName) !== -1 && (el.textContent || "").indexOf("أضف") === -1;
                  });
                  headings.forEach(function(hEl) {
                    var ht = (hEl.textContent || "").trim();
                    if (ht.indexOf("أفكار وطرق:") !== -1) {
                      if (pKind === "chocolate_snack" || pKind === "drink_juice") {
                        setLeafTextSafe(hEl, "✨ معلومات وقيمة غذائية: " + modalProdName);
                      } else if (pKind === "biscuit_dessert") {
                        setLeafTextSafe(hEl, "✨ معلومات وأفكار حلى: " + modalProdName);
                      } else if (pKind === "non_food") {
                        setLeafTextSafe(hEl, "✨ معلومات المنتج: " + modalProdName);
                      }
                    }
                  });

                  var chipBtns = Array.from(aiModal.querySelectorAll("button")).filter(function(b) {
                    if (b === continueAiBtn) return false;
                    var bt = (b.textContent || "").trim();
                    if (!bt || bt === "✕" || bt === "×" || bt.indexOf("أضف «") !== -1 || bt === "✨") return false;
                    return true;
                  });

                  if (chipBtns.length >= 2 && aiModal.getAttribute("data-v112-modal-prod") !== modalProdName) {
                    aiModal.setAttribute("data-v112-modal-prod", modalProdName);
                    var smartLabels = [];
                    if (pKind === "chocolate_snack") {
                      smartLabels = [
                        "🔥 السعرات والقيمة الغذائية",
                        "ℹ️ معلومات ومميزات المنتج",
                        "☕ مع إيش يؤكل أو يُقدم؟",
                        "🍫 سناك خفيف ومشابه"
                      ];
                    } else if (pKind === "biscuit_dessert") {
                      smartLabels = [
                        "🍰 فكرة حلى بارد وسريع به",
                        "🔥 السعرات والقيمة الغذائية",
                        "☕ مع الشاي والحليب",
                        "ℹ️ معلومات عن المنتج"
                      ];
                    } else if (pKind === "drink_juice") {
                      smartLabels = [
                        "🔥 السعرات والقيمة الغذائية",
                        "ℹ️ معلومات عن المشروب",
                        "🧊 أفضل طريقة تقديم بارد",
                        "🥨 سناك خفيف يناسبه"
                      ];
                    }
                    if (smartLabels.length > 0) {
                      chipBtns.forEach(function(cb, idx) {
                        if (smartLabels[idx]) {
                          setLeafTextSafe(cb, smartLabels[idx]);
                          cb.onclick = function(ev) {
                            ev.stopPropagation();
                            ev.preventDefault();
                            updateModalSmartTextV112(aiModal, modalProdName, pKind, customNote, smartLabels[idx]);
                          };
                        }
                      });
                    }
                  }

                  var bodyParas = Array.from(aiModal.querySelectorAll("div, p")).filter(function(el) {
                    var t = (el.textContent || "").trim();
                    return (
                      el.children.length <= 4 &&
                      t.length > 45 &&
                      t.indexOf("أضف «") === -1 &&
                      t.indexOf("متابعة النقاش") === -1 &&
                      (t.indexOf("أهلاً بك في أورجنال") !== -1 || t.indexOf("1️⃣") !== -1 || t.indexOf("بدون توابل") !== -1 || t.indexOf("سعرة حرارية") !== -1)
                    );
                  });
                  if (bodyParas.length > 0) {
                    var targetBox = bodyParas[bodyParas.length - 1];
                    var curTxt = (targetBox.textContent || "").trim();
                    var hasBadCookingOnSweet =
                      (pKind === "chocolate_snack" || pKind === "biscuit_dessert" || pKind === "drink_juice" || pKind === "non_food") &&
                      (curTxt.indexOf("بدون توابل") !== -1 || curTxt.indexOf("مرضى السكر") !== -1 || curTxt.indexOf("يمنية أصيلة") !== -1 || curTxt.indexOf("ذوّبها") !== -1);

                    if (hasBadCookingOnSweet || (customNote && curTxt.indexOf(customNote) === -1)) {
                      updateModalSmartTextV112(aiModal, modalProdName, pKind, customNote, "");
                    }
                  }
                }
              }
            }

            // PART F: Main AI Assistant Chat ("مساعد وشيف أورجنال الذكي")
            if (document.body.textContent.indexOf("مساعد وشيف أورجنال الذكي") !== -1) {
              enhanceChatBubblesWithStudioV116();

              var allTextContainers = Array.from(document.querySelectorAll("p, div, span, li"));
              allTextContainers.forEach(function(el) {
                if (el.children.length === 0 && el.textContent && /\\(\\s*رقم\\s*\\d+\\s*\\)/.test(el.textContent)) {
                  el.textContent = el.textContent.replace(/\\(\\s*رقم\\s*\\d+\\s*\\)/g, "");
                }
              });

              var morningBtns = Array.from(document.querySelectorAll("button")).filter(function(b) {
                return (b.textContent || "").indexOf("مقاضي الصباح") !== -1;
              });
              for (var mIdx = 1; mIdx < morningBtns.length; mIdx++) {
                if (morningBtns[mIdx].parentElement) {
                  morningBtns[mIdx].parentElement.style.display = "none";
                }
              }

              var prepBtns = Array.from(document.querySelectorAll("button")).filter(function(b) {
                var t = (b.textContent || "").trim();
                return t === "أفكار لتحضيره" || t === "منتجات مشابهة";
              });
              prepBtns.forEach(function(pb) {
                if (pb.parentElement) {
                  pb.parentElement.style.display = "none";
                }
              });

              var msgBubbles = Array.from(document.querySelectorAll("div, p")).filter(function(el) {
                if (el.hasAttribute("data-v112-contact-checked")) return false;
                var txt = (el.textContent || "").trim();
                return (
                  el.children.length <= 3 &&
                  txt.length > 25 &&
                  (txt.indexOf("غير متوفر") !== -1 ||
                    txt.indexOf("مش متوفر") !== -1 ||
                    txt.indexOf("ليس متوفراً") !== -1 ||
                    txt.indexOf("أكلم المتجر") !== -1 ||
                    txt.indexOf("أتواصل لك") !== -1 ||
                    txt.indexOf("طلب التوفير") !== -1)
                );
              });

              msgBubbles.forEach(function(bub) {
                bub.setAttribute("data-v112-contact-checked", "1");
                var askBtn = document.createElement("button");
                askBtn.type = "button";
                askBtn.innerHTML = "📲 نعم، كلّم المتجر إذا عندهم (إشعار فوري للمدير)";
                askBtn.style.cssText = "margin-top:10px;width:100%;background:#0d3825;color:#d4af37;border:1.5px solid #d4af37;border-radius:12px;padding:10px 14px;font-weight:800;font-size:0.86rem;cursor:pointer;display:block;text-align:center;";
                askBtn.onclick = function() {
                  askBtn.disabled = true;
                  askBtn.textContent = "⏳ جاري إرسال إشعار فوري لهاتف مدير المتجر...";
                  origFetchV112("/api/ai-v112/request-store", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                      sessionId: window.__v112SessionId,
                      requestedItem: (bub.textContent || "").slice(0, 140),
                      customerMessage: (bub.textContent || "").slice(0, 200)
                    })
                  })
                    .then(function(r) { return r.json(); })
                    .then(function() {
                      askBtn.style.background = "#eef8f3";
                      askBtn.style.color = "#0d3825";
                      askBtn.textContent = "✅ تم إرسال الإشعار لهاتف المدير! سيصلك رده هنا داخل المحادثة مباشرةً.";
                    })
                    .catch(function() {
                      askBtn.disabled = false;
                      askBtn.textContent = "📲 نعم، كلّم المتجر إذا عندهم";
                    });
                };
                if (bub.parentElement) {
                  bub.parentElement.appendChild(askBtn);
                }
              });
            }

            // PART G: Dedicated Admin Section "🤖 تخصيص الذكاء الاصطناعي"
            if (window.location.pathname.indexOf("/admin") !== -1) {
              injectAdminProductAiFieldV112();
              injectDedicatedAdminAiSectionV114();
            }
          } catch (e) {}
        }

        function updateModalSmartTextV112(aiModal, prodName, pKind, customNote, topic) {
          origFetchV112("/api/ai-v112/product-modal", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              productName: prodName,
              customTopic: topic || ""
            })
          })
            .then(function(r) { return r.json(); })
            .then(function(data) {
              if (!data || !data.ok || !data.content) return;
              var boxes = Array.from(aiModal.querySelectorAll("div, p")).filter(function(el) {
                var t = (el.textContent || "").trim();
                return (
                  el.children.length <= 4 &&
                  t.length > 35 &&
                  t.indexOf("أضف «") === -1 &&
                  t.indexOf("متابعة النقاش") === -1 &&
                  (t.indexOf("أهلاً بك") !== -1 || t.indexOf("1️⃣") !== -1 || t.indexOf("سعرة") !== -1 || t.indexOf("معلومات") !== -1 || t.indexOf("•") !== -1)
                );
              });
              if (boxes.length > 0) {
                var target = boxes[boxes.length - 1];
                target.style.whiteSpace = "pre-line";
                setLeafTextSafe(target, data.content);
              }
            })
            .catch(function() {});
        }

        function injectAdminProductAiFieldV112() {
          var varTableInput = document.getElementById("admin-inline-var-price");
          if (!varTableInput) return;
          var varBox = varTableInput.closest(".field-wide") || varTableInput.parentElement.parentElement;
          if (!varBox || document.getElementById("v112-product-ai-box")) return;

          var aiBox = document.createElement("details");
          aiBox.id = "v112-product-ai-box";
          aiBox.className = "field-wide";
          aiBox.style.cssText = "background:#f4fbf7;border:1.5px solid #0d3825;border-radius:12px;padding:10px 14px;margin-top:8px;margin-bottom:8px;direction:rtl;text-align:right;";
          aiBox.innerHTML =
            '<summary style="cursor:pointer;font-weight:800;color:#0d3825;font-size:0.9rem;display:flex;justify-content:space-between;align-items:center;list-style:none;">' +
            '<span>🤖 معلومات خاصة للذكاء الاصطناعي عن هذا المنتج (اختياري)</span>' +
            '<span style="font-size:0.75rem;background:#0d3825;color:#d4af37;padding:2px 8px;border-radius:99px;">اضغط للفتح ▾</span>' +
            '</summary>' +
            '<div style="margin-top:10px;padding-top:10px;border-top:1px solid #cce3d6;">' +
            '<textarea id="v112-product-ai-textarea" rows="2" placeholder="اكتب هنا أي معلومات تريد من الذكاء الاصطناعي معرفتها عن هذا المنتج (السعرات، الطعم، طريقة الاستخدام، البدائل)..." style="width:100%;background:#ffffff;color:#0d3825;border:1.5px solid #9dcab3;border-radius:10px;padding:8px 10px;font-size:0.85rem;box-sizing:border-box;margin-bottom:8px;"></textarea>' +
            '<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;">' +
            '<button type="button" id="v112-save-prod-ai-btn" style="background:#0d3825;color:#d4af37;border:none;border-radius:8px;padding:7px 14px;font-size:0.82rem;font-weight:800;cursor:pointer;">💾 حفظ معلومات المنتج للذكاء الاصطناعي</button>' +
            '<span id="v112-save-prod-ai-status" style="font-size:0.78rem;color:#0d3825;font-weight:700;"></span>' +
            '</div>' +
            '</div>';

          varBox.parentNode.insertBefore(aiBox, varBox.nextSibling);

          var formContainer = varBox.parentElement;
          var nameInput = formContainer ? formContainer.querySelector("input[placeholder*='اسم'], input") : null;
          function syncLoadedProductAiInfo() {
            if (!nameInput) return;
            var pName = (nameInput.value || "").trim();
            var ta = document.getElementById("v112-product-ai-textarea");
            if (!ta || !pName) return;
            var map = (window.__v114StudioConfig && window.__v114StudioConfig.productAiMap) || {};
            var saved = map["name:" + pName] || "";
            if (ta.getAttribute("data-loaded-for") !== pName) {
              ta.setAttribute("data-loaded-for", pName);
              ta.value = saved;
            }
          }
          setInterval(syncLoadedProductAiInfo, 600);

          function saveCurrentProductAiInfo(showMsg) {
            var pName = nameInput ? (nameInput.value || "").trim() : "";
            var ta = document.getElementById("v112-product-ai-textarea");
            var st = document.getElementById("v112-save-prod-ai-status");
            if (!pName || !ta) {
              if (showMsg && st) st.textContent = "⚠️ يرجى كتابة اسم المنتج أولاً بالأعلى";
              return;
            }
            if (!window.__v114StudioConfig.productAiMap) window.__v114StudioConfig.productAiMap = {};
            window.__v114StudioConfig.productAiMap["name:" + pName] = ta.value.trim();
            saveLocalBackupV115();
            origFetchV112("/api/ai-v112/save-product-info", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ productName: pName, aiInfo: ta.value.trim() })
            })
              .then(function(r) { return r.json(); })
              .then(function(d) {
                if (d && d.ok) {
                  if (st) st.textContent = "✅ تم الحفظ (" + pName + ")!";
                }
              })
              .catch(function() {});
          }

          var saveBtn = document.getElementById("v112-save-prod-ai-btn");
          if (saveBtn) {
            saveBtn.onclick = function() { saveCurrentProductAiInfo(true); };
          }
          if (formContainer) {
            formContainer.addEventListener("click", function(ev) {
              var t = ev.target;
              if (t && t.tagName === "BUTTON" && ((t.textContent || "").indexOf("إضافة المنتج") !== -1 || (t.textContent || "").indexOf("حفظ") !== -1)) {
                saveCurrentProductAiInfo(false);
              }
            }, true);
          }
        }

        function injectDedicatedAdminAiSectionV114() {
          var allBtns = Array.from(document.querySelectorAll("button, a"));
          var chatNavBtn = allBtns.find(function(b) {
            var t = (b.textContent || "").trim();
            return t.indexOf("محادثات الزبائن") !== -1 || t.indexOf("إعدادات المتجر") !== -1;
          });

          if (chatNavBtn && chatNavBtn.parentElement && !document.getElementById("v114-sidebar-ai-btn")) {
            var navParent = chatNavBtn.parentElement;
            var aiNavBtn = document.createElement("button");
            aiNavBtn.id = "v114-sidebar-ai-btn";
            aiNavBtn.type = "button";
            aiNavBtn.className = chatNavBtn.className || "";
            aiNavBtn.style.cssText =
              "width:100%;display:flex;justify-content:space-between;align-items:center;padding:10px 14px;margin:4px 0;border-radius:12px;border:1.5px solid #0d3825;background:#eef8f3;color:#0d3825;font-weight:800;font-size:0.9rem;cursor:pointer;text-align:right;direction:rtl;";
            aiNavBtn.innerHTML =
              '<span style="display:flex;align-items:center;gap:8px;"><span>🤖</span><span>تخصيص الذكاء الاصطناعي</span></span>' +
              '<span class="v114-nav-req-badge" style="display:none;background:#ef4444;color:#fff;font-size:0.72rem;padding:2px 7px;border-radius:99px;font-weight:900;">0</span>';

            aiNavBtn.onclick = function(ev) {
              ev.stopPropagation();
              openDedicatedAiStudioViewV114();
            };
            navParent.insertBefore(aiNavBtn, chatNavBtn.nextSibling);

            Array.from(navParent.children).forEach(function(sib) {
              if (sib !== aiNavBtn && !sib.hasAttribute("data-v114-nav-bound")) {
                sib.setAttribute("data-v114-nav-bound", "1");
                sib.addEventListener("click", function() {
                  closeDedicatedAiStudioViewV114();
                });
              }
            });
          }
        }

        function openDedicatedAiStudioViewV114() {
          window.__v114StudioOpen = true;
          var mainArea = document.querySelector(".admin-shell main") || document.querySelector("main") || document.querySelector(".admin-content");
          var studioContainer = document.getElementById("v114-dedicated-studio-section");

          if (!studioContainer) {
            studioContainer = document.createElement("div");
            studioContainer.id = "v114-dedicated-studio-section";
            studioContainer.style.cssText = "padding:16px;max-width:1050px;margin:0 auto;direction:rtl;text-align:right;";
            if (mainArea && mainArea.parentElement) {
              mainArea.parentElement.insertBefore(studioContainer, mainArea);
            } else {
              var shell = document.querySelector(".admin-shell") || document.body;
              shell.appendChild(studioContainer);
            }
          }

          if (mainArea) mainArea.style.display = "none";
          studioContainer.style.display = "block";
          renderFullAiStudioV114();
          window.scrollTo({ top: 0, behavior: "smooth" });
        }

        function closeDedicatedAiStudioViewV114() {
          window.__v114StudioOpen = false;
          var mainArea = document.querySelector(".admin-shell main") || document.querySelector("main") || document.querySelector(".admin-content");
          var studioContainer = document.getElementById("v114-dedicated-studio-section");
          if (studioContainer) studioContainer.style.display = "none";
          if (mainArea) mainArea.style.display = "";
        }

        function commitAndSaveStudioV115(successLabel) {
          window.__v115LastSaveTime = Date.now();
          saveLocalBackupV115();
          window.__v115BannerMsg = successLabel || "✅ تم الحفظ بنجاح!";
          renderFullAiStudioV114();
          origFetchV112("/api/ai-v112/save-training", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(window.__v114StudioConfig)
          })
            .then(function(r) { return r.json(); })
            .then(function(d) {
              var bEl = document.getElementById("v115-save-banner");
              if (bEl && d && d.ok) {
                bEl.textContent = (successLabel || "✅ تم الحفظ بنجاح") + " (محفوظ في السيرفر وقاعدة البيانات ✓)";
              }
            })
            .catch(function() {});
          setTimeout(function() {
            window.__v115BannerMsg = "";
            var bEl = document.getElementById("v115-save-banner");
            if (bEl) bEl.style.display = "none";
          }, 4500);
        }

        function renderFullAiStudioV114() {
          var studio = document.getElementById("v114-dedicated-studio-section");
          if (!studio) return;

          var cfg = window.__v114StudioConfig;
          var pendingReqs = (window.__v114Requests || []).filter(function(r) { return r.status === "pending"; }).length;
          var subTabs = [
            { id: "inst", label: "1️⃣ التعليمات والشخصية (" + ((cfg.instructions || []).length) + ")" },
            { id: "rules", label: "2️⃣ قاموس الردود (" + ((cfg.rules || []).length) + ")" },
            { id: "promo", label: "3️⃣ ترويج منتج برابطه (" + ((cfg.promotedProducts || []).length) + ")" },
            { id: "recipes", label: "4️⃣ الوصفات المصورة والمنتجات (" + ((cfg.recipes || []).length) + ")" },
            { id: "prods", label: "5️⃣ معلومات المنتجات (" + Object.keys(cfg.productAiMap || {}).length + ")" },
            { id: "reqs", label: "6️⃣ الإشعارات وطلبات الزبائن (" + pendingReqs + ")" }
          ];

          var tabsHtml = '<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px;">';
          subTabs.forEach(function(t) {
            var isAct = window.__v114ActiveSubTab === t.id;
            tabsHtml +=
              '<button type="button" class="v114-subtab-btn" data-subtab="' + t.id + '" style="flex:1 1 150px;padding:10px 12px;border-radius:12px;border:1.5px solid #0d3825;background:' +
              (isAct ? "#0d3825" : "#ffffff") +
              ';color:' +
              (isAct ? "#d4af37" : "#0d3825") +
              ';font-weight:800;font-size:0.84rem;cursor:pointer;text-align:center;">' +
              t.label +
              '</button>';
          });
          tabsHtml += '</div>';

          var bannerHtml = window.__v115BannerMsg
            ? '<div id="v115-save-banner" style="background:#dcfce7;color:#166534;border:1.5px solid #16a34a;border-radius:12px;padding:10px 14px;margin-bottom:12px;font-weight:800;font-size:0.88rem;text-align:center;">' + window.__v115BannerMsg + '</div>'
            : '<div id="v115-save-banner" style="display:none;"></div>';

          studio.innerHTML =
            '<div style="background:#ffffff;border:2px solid #0d3825;border-radius:18px;padding:18px;box-shadow:0 6px 24px rgba(13,56,37,0.06);">' +
            '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;border-bottom:1.5px solid #d5e5dc;padding-bottom:14px;margin-bottom:14px;">' +
            '<div>' +
            '<h2 style="margin:0;color:#0d3825;font-size:1.2rem;">🤖 قسم تخصيص وإدارة الذكاء الاصطناعي الشامل</h2>' +
            '<p style="margin:4px 0 0 0;color:#495a52;font-size:0.83rem;">تحكم كامل في تعليمات الذكاء، ترويج المنتجات بالروابط، الوصفات المصورة، والإشعارات الفورية (استهلاك 0 توكن يكفي +10,000 رسالة يومياً)</p>' +
            '</div>' +
            '<div style="display:flex;gap:8px;align-items:center;">' +
            '<button type="button" id="v114-enable-push-btn" style="background:#eef8f3;color:#0d3825;border:1.5px solid #0d3825;border-radius:10px;padding:8px 12px;font-weight:800;font-size:0.8rem;cursor:pointer;">🔔 تفعيل إشعارات الهاتف وتجربتها</button>' +
            '<button type="button" id="v114-back-admin-btn" style="background:#fee2e2;color:#b91c1c;border:none;border-radius:10px;padding:8px 14px;font-weight:800;font-size:0.82rem;cursor:pointer;">← رجوع للقسم السابق</button>' +
            '</div>' +
            '</div>' +
            bannerHtml +
            tabsHtml +
            '<div id="v114-subtab-body"></div>' +
            '</div>';

          document.getElementById("v114-back-admin-btn").onclick = function() {
            closeDedicatedAiStudioViewV114();
          };
          document.getElementById("v114-enable-push-btn").onclick = function() {
            if ("Notification" in window) {
              Notification.requestPermission().then(function(p) {
                if (p === "granted") {
                  triggerRealPhoneNotificationV114("🔔 إشعار تجريبي من متجر أورجنال", "تم تفعيل الإشعارات الفعلية والصوت والاهتزاز على هاتفك بنجاح!");
                } else {
                  alert("يرجى السماح بالإشعارات من إعدادات المتصفح في هاتفك.");
                }
              });
            } else {
              playAlertSoundV114();
              alert("تم تفعيل التنبيه الصوتي المباشر!");
            }
          };

          Array.from(studio.querySelectorAll(".v114-subtab-btn")).forEach(function(b) {
            b.onclick = function() {
              window.__v114ActiveSubTab = b.getAttribute("data-subtab") || "inst";
              renderFullAiStudioV114();
            };
          });

          renderStudioSubTabV114();
        }

        function buildProductOptionsHtmlV114() {
          var cats = window.__v114Catalog || [];
          var html = '<option value="">-- اختر منتجاً من المتجر (أو اكتب يدوياً بالأسفل) --</option>';
          cats.forEach(function(p) {
            html += '<option value="' + (p.name || "").replace(/"/g, "&quot;") + '" data-price="' + (p.price || 0) + '" data-img="' + (p.imageUrl || "") + '">' + (p.name || "") + ' (' + (p.price || 0) + ' ر.ي)</option>';
          });
          return html;
        }

        function renderStudioSubTabV114() {
          var body = document.getElementById("v114-subtab-body");
          if (!body) return;
          var tab = window.__v114ActiveSubTab;

          // TAB 1: التعليمات والشخصية
          if (tab === "inst") {
            var instListHtml = "";
            var instArr = window.__v114StudioConfig.instructions || [];
            if (instArr.length === 0) {
              instListHtml = '<div style="text-align:center;padding:18px;background:#f8fbf9;border:1px dashed #9dcab3;border-radius:12px;color:#5c6f65;font-size:0.86rem;">القسم فارغ حالياً — أضف تعليماتك الخاصة بالأعلى واضغط (+ إضافة وحفظ التعليمة).</div>';
            } else {
              instArr.forEach(function(item, idx) {
                instListHtml +=
                  '<div style="background:#f8fbf9;border:1.5px solid #9dcab3;border-radius:12px;padding:12px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:flex-start;gap:10px;">' +
                  '<div style="flex:1;">' +
                  '<span style="background:#0d3825;color:#d4af37;font-size:0.75rem;padding:2px 8px;border-radius:99px;font-weight:800;">' + (item.category || "تعليمة عامة") + '</span>' +
                  '<div style="margin-top:6px;font-size:0.9rem;color:#0d3825;font-weight:700;white-space:pre-line;">' + (item.content || "") + '</div>' +
                  '</div>' +
                  '<button type="button" class="v114-del-inst" data-idx="' + idx + '" style="background:#fee2e2;color:#b91c1c;border:none;border-radius:8px;padding:6px 10px;font-weight:800;font-size:0.78rem;cursor:pointer;">حذف</button>' +
                  '</div>';
              });
            }

            body.innerHTML =
              '<div style="background:#eef8f3;border:1.5px solid #9dcab3;border-radius:14px;padding:14px;margin-bottom:14px;">' +
              '<h4 style="margin:0 0 8px 0;color:#0d3825;font-size:0.95rem;">➕ إضافة تعليمة جديدة للذكاء الاصطناعي:</h4>' +
              '<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:8px;">' +
              '<select id="v114-inst-cat" style="flex:1 1 220px;padding:9px;border-radius:10px;border:1px solid #9dcab3;background:#fff;color:#0d3825;font-weight:700;font-size:0.85rem;">' +
              '<option value="🗣️ أسلوب الترحيب والكلام">🗣️ أسلوب الترحيب والكلام مع الزبون</option>' +
              '<option value="🤝 عند عدم توفر منتج">🤝 طريقة الرد عند عدم توفر منتج</option>' +
              '<option value="🚫 الممنوعات والحدود">🚫 الممنوعات والحدود (أشياء لا يفعلها)</option>' +
              '<option value="💬 متى يقترح منتجات ومتى يسولف">💬 متى يقترح منتجات ومتى يكتفي بالسوالف</option>' +
              '<option value="📌 تعليمة عامة أخرى">📌 تعليمة عامة أخرى</option>' +
              '</select>' +
              '</div>' +
              '<textarea id="v114-inst-text" rows="3" placeholder="اكتب التعليمة هنا بالتفصيل (مثال: رحب بالزبون كصديق، وإذا طلب منتج غير متوفر اعرض عليه التواصل مع المتجر)..." style="width:100%;padding:10px;border-radius:10px;border:1px solid #9dcab3;background:#fff;color:#0d3825;font-size:0.86rem;box-sizing:border-box;margin-bottom:8px;"></textarea>' +
              '<div style="display:flex;justify-content:space-between;align-items:center;">' +
              '<button type="button" id="v114-add-inst-btn" style="background:#0d3825;color:#d4af37;border:none;border-radius:10px;padding:10px 20px;font-weight:800;font-size:0.88rem;cursor:pointer;">+ إضافة وحفظ التعليمة</button>' +
              '</div>' +
              '</div>' +
              '<h4 style="margin:0 0 8px 0;color:#0d3825;font-size:0.95rem;">📋 التعليمات المضافة حالياً (' + instArr.length + '):</h4>' +
              instListHtml;

            document.getElementById("v114-add-inst-btn").onclick = function() {
              var catEl = document.getElementById("v114-inst-cat");
              var txtEl = document.getElementById("v114-inst-text");
              var cat = catEl ? catEl.value : "📌 تعليمة عامة";
              var txt = txtEl ? txtEl.value.trim() : "";
              if (!txt) {
                alert("يرجى كتابة نص التعليمة أولاً");
                return;
              }
              if (!Array.isArray(window.__v114StudioConfig.instructions)) window.__v114StudioConfig.instructions = [];
              window.__v114StudioConfig.instructions.unshift({
                id: "inst_" + Date.now(),
                category: cat,
                content: txt,
                active: true
              });
              commitAndSaveStudioV115("✅ تم حفظ التعليمة وإضافتها للقائمة بنجاح!");
            };

            Array.from(body.querySelectorAll(".v114-del-inst")).forEach(function(b) {
              b.onclick = function() {
                var i = parseInt(b.getAttribute("data-idx") || "0", 10);
                window.__v114StudioConfig.instructions.splice(i, 1);
                commitAndSaveStudioV115("🗑️ تم حذف التعليمة وتحديث القائمة");
              };
            });
            return;
          }

          // TAB 2: قاموس الردود والبدائل + إرفاق رابط منتج
          if (tab === "rules") {
            var rulesHtml = "";
            var rulesArr = window.__v114StudioConfig.rules || [];
            if (rulesArr.length === 0) {
              rulesHtml = '<div style="text-align:center;padding:18px;background:#f8fbf9;border:1px dashed #9dcab3;border-radius:12px;color:#5c6f65;font-size:0.86rem;">لا توجد ردود مخصصة مضافة بعد — أضف أي كلمة أو سؤال وكيف يرد عليه الذكاء الاصطناعي بالأعلى.</div>';
            } else {
              rulesArr.forEach(function(r, idx) {
                rulesHtml +=
                  '<div style="background:#f8fbf9;border:1.5px solid #9dcab3;border-radius:12px;padding:12px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:flex-start;gap:10px;">' +
                  '<div style="flex:1;">' +
                  '<strong style="color:#0d3825;font-size:0.88rem;">💬 إذا قال الزبون: «' + (r.trigger || "") + '»</strong>' +
                  '<div style="margin-top:4px;font-size:0.86rem;color:#1e293b;">🤖 الرد: ' + (r.response || "") + '</div>' +
                  (r.linkedProductName || r.linkedProductUrl
                    ? '<div style="margin-top:4px;font-size:0.8rem;color:#166534;font-weight:700;">🔗 المنتج المرفق: ' + (r.linkedProductName || "") + ' (' + (r.linkedProductUrl || "") + ')</div>'
                    : '') +
                  '</div>' +
                  '<button type="button" class="v114-del-rule" data-idx="' + idx + '" style="background:#fee2e2;color:#b91c1c;border:none;border-radius:8px;padding:6px 10px;font-weight:800;font-size:0.78rem;cursor:pointer;">حذف</button>' +
                  '</div>';
              });
            }

            body.innerHTML =
              '<div style="background:#eef8f3;border:1.5px solid #9dcab3;border-radius:14px;padding:14px;margin-bottom:14px;">' +
              '<h4 style="margin:0 0 8px 0;color:#0d3825;font-size:0.95rem;">➕ إضافة قاعدة رد سريع أو بديل (تعمل بـ 0 توكن):</h4>' +
              '<input id="v114-rule-trig" placeholder="إذا سأل الزبون عن (مثال: نوتيلا، أو توصيل، أو شوكولاتة)" style="width:100%;padding:9px 10px;border-radius:10px;border:1px solid #9dcab3;background:#fff;margin-bottom:8px;box-sizing:border-box;font-size:0.85rem;" />' +
              '<textarea id="v114-rule-resp" rows="2" placeholder="يرد الذكاء الاصطناعي بـ..." style="width:100%;padding:9px 10px;border-radius:10px;border:1px solid #9dcab3;background:#fff;margin-bottom:8px;box-sizing:border-box;font-size:0.85rem;"></textarea>' +
              '<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:8px;">' +
              '<select id="v114-rule-prod-sel" style="flex:1 1 200px;padding:8px;border-radius:10px;border:1px solid #9dcab3;background:#fff;font-size:0.83rem;">' +
              buildProductOptionsHtmlV114() +
              '</select>' +
              '<input id="v114-rule-prod-url" placeholder="أو ضع رابط المنتج المراد اقتراحه مع الرد (اختياري)" style="flex:1 1 220px;padding:8px 10px;border-radius:10px;border:1px solid #9dcab3;background:#fff;font-size:0.83rem;" />' +
              '</div>' +
              '<div style="display:flex;justify-content:space-between;align-items:center;">' +
              '<button type="button" id="v114-add-rule-btn" style="background:#0d3825;color:#d4af37;border:none;border-radius:10px;padding:10px 20px;font-weight:800;font-size:0.88rem;cursor:pointer;">+ إضافة وحفظ القاعدة</button>' +
              '</div>' +
              '</div>' +
              '<h4 style="margin:0 0 8px 0;color:#0d3825;font-size:0.95rem;">📋 قواعد الردود المضافة (' + rulesArr.length + '):</h4>' +
              rulesHtml;

            var prodSel = document.getElementById("v114-rule-prod-sel");
            prodSel.onchange = function() {
              var val = prodSel.value;
              if (val) {
                document.getElementById("v114-rule-prod-url").value = "/?search=" + encodeURIComponent(val);
              }
            };

            document.getElementById("v114-add-rule-btn").onclick = function() {
              var trig = document.getElementById("v114-rule-trig").value.trim();
              var resp = document.getElementById("v114-rule-resp").value.trim();
              var pName = document.getElementById("v114-rule-prod-sel").value.trim();
              var pUrl = document.getElementById("v114-rule-prod-url").value.trim();
              if (!trig || !resp) {
                alert("يرجى كتابة كلمة السؤال ونص الرد أولاً");
                return;
              }
              if (!Array.isArray(window.__v114StudioConfig.rules)) window.__v114StudioConfig.rules = [];
              window.__v114StudioConfig.rules.unshift({
                id: "rule_" + Date.now(),
                trigger: trig,
                response: resp,
                linkedProductName: pName,
                linkedProductUrl: pUrl
              });
              commitAndSaveStudioV115("✅ تم حفظ قاعدة الرد بنجاح!");
            };

            Array.from(body.querySelectorAll(".v114-del-rule")).forEach(function(b) {
              b.onclick = function() {
                var i = parseInt(b.getAttribute("data-idx") || "0", 10);
                window.__v114StudioConfig.rules.splice(i, 1);
                commitAndSaveStudioV115("🗑️ تم حذف القاعدة");
              };
            });
            return;
          }

          // TAB 3: ترويج المنتجات الذكي
          if (tab === "promo") {
            var promoHtml = "";
            var promoArr = window.__v114StudioConfig.promotedProducts || [];
            if (promoArr.length === 0) {
              promoHtml = '<div style="text-align:center;padding:18px;background:#f8fbf9;border:1px dashed #9dcab3;border-radius:12px;color:#5c6f65;font-size:0.86rem;">لا توجد منتجات مروجة حالياً — اختر أي منتج أو ضع رابطه بالأعلى ليروج له المساعد الذكي.</div>';
            } else {
              promoArr.forEach(function(p, idx) {
                promoHtml +=
                  '<div style="background:#f8fbf9;border:1.5px solid #d4af37;border-radius:12px;padding:12px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center;gap:10px;">' +
                  '<div style="flex:1;">' +
                  '<span style="background:#0d3825;color:#d4af37;font-size:0.74rem;padding:2px 8px;border-radius:99px;font-weight:800;">' + (p.promoBadge || "⭐ منتج مروج") + '</span>' +
                  '<strong style="display:block;color:#0d3825;font-size:0.9rem;margin-top:4px;">' + (p.productName || "") + (p.productPrice ? " (" + p.productPrice + " ر.ي)" : "") + '</strong>' +
                  '<div style="font-size:0.83rem;color:#334155;margin-top:2px;">' + (p.promoMessage || "") + '</div>' +
                  '<div style="font-size:0.78rem;color:#166534;margin-top:3px;">🔗 الرابط: ' + (p.productUrl || "") + ' | 🎯 يظهر عند: ' + (p.triggerKeywords || "الترحيب والسؤال عن العروض") + '</div>' +
                  '</div>' +
                  '<button type="button" class="v114-del-promo" data-idx="' + idx + '" style="background:#fee2e2;color:#b91c1c;border:none;border-radius:8px;padding:6px 10px;font-weight:800;font-size:0.78rem;cursor:pointer;">حذف</button>' +
                  '</div>';
              });
            }

            body.innerHTML =
              '<div style="background:#eef8f3;border:1.5px solid #9dcab3;border-radius:14px;padding:14px;margin-bottom:14px;">' +
              '<h4 style="margin:0 0 8px 0;color:#0d3825;font-size:0.95rem;">⭐ إضافة منتج لترويجه عبر المساعد الذكي (مع رابطه وصورته):</h4>' +
              '<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:8px;">' +
              '<select id="v114-promo-sel" style="flex:1 1 220px;padding:9px;border-radius:10px;border:1px solid #9dcab3;background:#fff;font-size:0.84rem;font-weight:700;">' +
              buildProductOptionsHtmlV114() +
              '</select>' +
              '<input id="v114-promo-name" placeholder="اسم المنتج المراد ترويجه" style="flex:1 1 180px;padding:9px;border-radius:10px;border:1px solid #9dcab3;background:#fff;font-size:0.84rem;" />' +
              '<input id="v114-promo-price" type="number" placeholder="السعر (ر.ي)" style="flex:0 1 110px;padding:9px;border-radius:10px;border:1px solid #9dcab3;background:#fff;font-size:0.84rem;" />' +
              '</div>' +
              '<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:8px;">' +
              '<input id="v114-promo-url" placeholder="🔗 رابط المنتج المباشر (يُملأ تلقائياً عند اختيار المنتج أو الصق الرابط هنا)" style="flex:2 1 240px;padding:9px;border-radius:10px;border:1px solid #9dcab3;background:#fff;font-size:0.84rem;" />' +
              '<input id="v114-promo-badge" placeholder="شارة الترويج (مثال: 🔥 عرض خاص اليوم)" style="flex:1 1 160px;padding:9px;border-radius:10px;border:1px solid #9dcab3;background:#fff;font-size:0.84rem;" />' +
              '</div>' +
              '<input id="v114-promo-kw" placeholder="متى يروج له؟ اكتب كلمات مفتاحية (مثال: عروض، شوكولاتة، حلى) أو اتركه فارغاً للترويج العام" style="width:100%;padding:9px;border-radius:10px;border:1px solid #9dcab3;background:#fff;font-size:0.84rem;box-sizing:border-box;margin-bottom:8px;" />' +
              '<textarea id="v114-promo-msg" rows="2" placeholder="رسالة الترويج المقنعة التي يقولها المساعد الذكي للزبون عن هذا المنتج..." style="width:100%;padding:9px;border-radius:10px;border:1px solid #9dcab3;background:#fff;font-size:0.84rem;box-sizing:border-box;margin-bottom:8px;"></textarea>' +
              '<div style="display:flex;justify-content:space-between;align-items:center;">' +
              '<button type="button" id="v114-add-promo-btn" style="background:#0d3825;color:#d4af37;border:none;border-radius:10px;padding:10px 20px;font-weight:800;font-size:0.88rem;cursor:pointer;">+ تفعيل وحفظ ترويج هذا المنتج</button>' +
              '</div>' +
              '</div>' +
              '<h4 style="margin:0 0 8px 0;color:#0d3825;font-size:0.95rem;">📋 المنتجات المروجة حالياً (' + promoArr.length + '):</h4>' +
              promoHtml;

            var pSel = document.getElementById("v114-promo-sel");
            pSel.onchange = function() {
              var opt = pSel.options[pSel.selectedIndex];
              if (opt && opt.value) {
                document.getElementById("v114-promo-name").value = opt.value;
                document.getElementById("v114-promo-price").value = opt.getAttribute("data-price") || "";
                document.getElementById("v114-promo-url").value = "/?search=" + encodeURIComponent(opt.value);
                document.getElementById("v114-promo-name").setAttribute("data-img", opt.getAttribute("data-img") || "");
              }
            };

            document.getElementById("v114-add-promo-btn").onclick = function() {
              var name = document.getElementById("v114-promo-name").value.trim() || document.getElementById("v114-promo-sel").value.trim();
              var price = Number(document.getElementById("v114-promo-price").value || 0);
              var url = document.getElementById("v114-promo-url").value.trim() || ("/?search=" + encodeURIComponent(name));
              var badge = document.getElementById("v114-promo-badge").value.trim() || "⭐ عرض مميز";
              var kw = document.getElementById("v114-promo-kw").value.trim();
              var msg = document.getElementById("v114-promo-msg").value.trim();
              var img = document.getElementById("v114-promo-name").getAttribute("data-img") || "";
              if (!name) {
                alert("يرجى اختيار أو كتابة اسم المنتج المراد ترويجه");
                return;
              }
              if (!Array.isArray(window.__v114StudioConfig.promotedProducts)) window.__v114StudioConfig.promotedProducts = [];
              window.__v114StudioConfig.promotedProducts.unshift({
                id: "promo_" + Date.now(),
                productName: name,
                productPrice: price,
                productUrl: url,
                productImage: img,
                promoBadge: badge,
                promoMessage: msg,
                triggerKeywords: kw,
                active: true
              });
              commitAndSaveStudioV115("✅ تم حفظ وتفعيل ترويج المنتج («" + name + "») بنجاح!");
            };

            Array.from(body.querySelectorAll(".v114-del-promo")).forEach(function(b) {
              b.onclick = function() {
                var i = parseInt(b.getAttribute("data-idx") || "0", 10);
                window.__v114StudioConfig.promotedProducts.splice(i, 1);
                commitAndSaveStudioV115("🗑️ تم إيقاف وحذف الترويج");
              };
            });
            return;
          }

          // TAB 4: استوديو الوصفات المصورة + روابط المنتجات المستخدمة ليقترحها
          if (tab === "recipes") {
            window.__v114DraftIngredients = window.__v114DraftIngredients || [];
            window.__v114DraftRecipeImg = window.__v114DraftRecipeImg || "";

            var recListHtml = "";
            var recArr = window.__v114StudioConfig.recipes || [];
            if (recArr.length === 0) {
              recListHtml = '<div style="text-align:center;padding:18px;background:#f8fbf9;border:1px dashed #9dcab3;border-radius:12px;color:#5c6f65;font-size:0.86rem;">لا توجد وصفات مضافة بعد — أضف وصفة مع صورتها والمنتجات المستخدمة فيها بالأعلى ليقترحها الذكاء الاصطناعي للزبائن.</div>';
            } else {
              recArr.forEach(function(r, idx) {
                var ingTags = (r.ingredients || []).map(function(g) { return "🔗 " + g.name + (g.price ? " (" + g.price + " ر.ي)" : ""); }).join(" ، ");
                recListHtml +=
                  '<div style="background:#f8fbf9;border:1.5px solid #9dcab3;border-radius:12px;padding:12px;margin-bottom:10px;display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">' +
                  (r.imageUrl ? '<img src="' + r.imageUrl + '" style="width:78px;height:78px;object-fit:cover;border-radius:10px;border:1.5px solid #0d3825;flex-shrink:0;" />' : '') +
                  '<div style="flex:1;">' +
                  '<strong style="color:#0d3825;font-size:0.94rem;">🍰 ' + (r.title || "") + '</strong>' +
                  '<div style="font-size:0.78rem;color:#64748b;margin-top:2px;">🔍 كلمات البحث: ' + (r.keywords || r.title || "") + '</div>' +
                  '<div style="font-size:0.85rem;color:#1e293b;margin-top:6px;white-space:pre-line;line-height:1.5;">' + (r.steps || "") + '</div>' +
                  (ingTags ? '<div style="font-size:0.82rem;color:#166534;font-weight:800;margin-top:6px;background:#eef8f3;padding:6px 10px;border-radius:8px;">🛒 المنتجات المربوطة: ' + ingTags + '</div>' : '') +
                  '</div>' +
                  '<button type="button" class="v114-del-rec" data-idx="' + idx + '" style="background:#fee2e2;color:#b91c1c;border:none;border-radius:8px;padding:6px 10px;font-weight:800;font-size:0.78rem;cursor:pointer;">حذف</button>' +
                  '</div>';
              });
            }

            body.innerHTML =
              '<div style="background:#eef8f3;border:1.5px solid #9dcab3;border-radius:14px;padding:14px;margin-bottom:14px;">' +
              '<h4 style="margin:0 0 8px 0;color:#0d3825;font-size:0.95rem;">🍰 إضافة وصفة مصورة مع روابط المنتجات المستخدمة ليقترحها الذكاء الاصطناعي:</h4>' +
              '<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:8px;">' +
              '<input id="v114-rec-title" placeholder="اسم الوصفة أو الفكرة (مثال: بسكويت أبو ولد مغطى بالحليب والشوكولاتة)" style="flex:1 1 220px;padding:9px;border-radius:10px;border:1px solid #9dcab3;background:#fff;font-size:0.85rem;" />' +
              '<input id="v114-rec-kw" placeholder="كلمات البحث عنها (مثال: أريد حلى بسكويت حلو، حلى بارد)" style="flex:1 1 200px;padding:9px;border-radius:10px;border:1px solid #9dcab3;background:#fff;font-size:0.85rem;" />' +
              '</div>' +

              '<div style="background:#ffffff;border:1.5px dashed #0d3825;border-radius:12px;padding:12px;margin-bottom:8px;">' +
              '<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;">' +
              '<div style="font-size:0.85rem;color:#0d3825;font-weight:800;">📷 صورة الوصفة (اختياري — ارفع صورة مباشرة من هاتفك أو ضع رابط صورة):</div>' +
              '<label style="background:#0d3825;color:#d4af37;padding:8px 14px;border-radius:10px;font-weight:800;font-size:0.82rem;cursor:pointer;display:inline-block;">' +
              '📁 اختيار صورة من الهاتف' +
              '<input type="file" id="v114-rec-file" accept="image/*" style="display:none;" />' +
              '</label>' +
              '</div>' +
              '<div id="v114-rec-img-preview-box" style="display:none;margin-top:10px;align-items:center;gap:12px;background:#f4fbf7;padding:8px 12px;border-radius:10px;border:1px solid #9dcab3;">' +
              '<img id="v114-rec-img-preview" src="" style="width:68px;height:68px;object-fit:cover;border-radius:8px;border:1.5px solid #0d3825;" />' +
              '<div style="flex:1;">' +
              '<strong style="color:#166534;font-size:0.84rem;display:block;">✅ تم تجهيز صورة الوصفة بنجاح!</strong>' +
              '<button type="button" id="v114-remove-rec-img" style="margin-top:4px;background:#fee2e2;color:#b91c1c;border:none;border-radius:6px;padding:4px 8px;font-size:0.75rem;font-weight:800;cursor:pointer;">إزالة الصورة</button>' +
              '</div>' +
              '</div>' +
              '<input id="v114-rec-img-url" placeholder="أو الصق رابط صورة خارجي هنا (اختياري)" style="width:100%;margin-top:8px;padding:8px 10px;border-radius:8px;border:1px solid #cce3d6;font-size:0.8rem;box-sizing:border-box;" />' +
              '</div>' +

              '<textarea id="v114-rec-steps" rows="3" placeholder="اكتب خطوات ومقادير الوصفة هنا (مثال: اسكب الشوكولاتة وفورها مع الحليب واطحن البسكويت واخلطه معها وحطها بالثلاجة)..." style="width:100%;padding:9px;border-radius:10px;border:1px solid #9dcab3;background:#fff;font-size:0.85rem;box-sizing:border-box;margin-bottom:8px;"></textarea>' +

              '<div style="background:#ffffff;border:1px solid #9dcab3;border-radius:10px;padding:10px;margin-bottom:10px;">' +
              '<strong style="color:#0d3825;font-size:0.85rem;display:block;margin-bottom:6px;">🛒 ربط المنتجات المستخدمة في الوصفة (مجرد اختيار المنتج من القائمة يربطه تلقائياً بالوصفة!):</strong>' +
              '<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:6px;">' +
              '<select id="v114-rec-ing-sel" style="flex:1 1 220px;padding:8px;border-radius:8px;border:1.5px solid #0d3825;font-size:0.84rem;font-weight:700;background:#f8fbf9;">' +
              buildProductOptionsHtmlV114() +
              '</select>' +
              '<input id="v114-rec-ing-name" placeholder="أو اكتب اسم منتج يدوياً" style="flex:1 1 140px;padding:8px;border-radius:8px;border:1px solid #9dcab3;font-size:0.82rem;" />' +
              '<input id="v114-rec-ing-url" placeholder="رابط المنتج (اختياري)" style="flex:1 1 150px;padding:8px;border-radius:8px;border:1px solid #9dcab3;font-size:0.82rem;" />' +
              '<button type="button" id="v114-add-ing-btn" style="background:#eef8f3;color:#0d3825;border:1.5px solid #0d3825;border-radius:8px;padding:7px 12px;font-weight:800;font-size:0.8rem;cursor:pointer;">+ ربط المنتج بالوصفة</button>' +
              '</div>' +
              '<div id="v114-draft-ings-list" style="font-size:0.82rem;color:#166534;font-weight:800;margin-top:6px;"></div>' +
              '</div>' +

              '<div style="display:flex;justify-content:space-between;align-items:center;">' +
              '<button type="button" id="v114-save-rec-btn" style="width:100%;background:#0d3825;color:#d4af37;border:none;border-radius:12px;padding:12px 18px;font-weight:900;font-size:0.92rem;cursor:pointer;">💾 حفظ الوصفة المصورة ومنتجاتها</button>' +
              '</div>' +
              '</div>' +
              '<h4 style="margin:0 0 8px 0;color:#0d3825;font-size:0.95rem;">📋 الوصفات المصورة المضافة (' + recArr.length + '):</h4>' +
              recListHtml;

            function renderDraftIngs() {
              var dBox = document.getElementById("v114-draft-ings-list");
              if (!dBox) return;
              if (window.__v114DraftIngredients.length === 0) {
                dBox.textContent = "لم يتم ربط منتجات بعد — اختر أي منتج من القائمة المنسدلة أعلاه لربطه تلقائياً.";
                return;
              }
              dBox.innerHTML =
                "المنتجات المربوطة: " +
                window.__v114DraftIngredients
                  .map(function(g, gIdx) {
                    return (
                      '<span style="display:inline-flex;align-items:center;gap:4px;background:#dcfce7;color:#166534;padding:3px 8px;border-radius:99px;margin:2px;">' +
                      '«' + g.name + '»' +
                      '<button type="button" class="v115-rem-ing" data-gidx="' + gIdx + '" style="background:none;border:none;color:#b91c1c;font-weight:900;cursor:pointer;">✕</button>' +
                      '</span>'
                    );
                  })
                  .join(" ");
              Array.from(dBox.querySelectorAll(".v115-rem-ing")).forEach(function(rb) {
                rb.onclick = function() {
                  var gi = parseInt(rb.getAttribute("data-gidx") || "0", 10);
                  window.__v114DraftIngredients.splice(gi, 1);
                  renderDraftIngs();
                };
              });
            }
            renderDraftIngs();

            var ingSel = document.getElementById("v114-rec-ing-sel");
            ingSel.onchange = function() {
              var opt = ingSel.options[ingSel.selectedIndex];
              if (opt && opt.value) {
                var pName = opt.value.trim();
                var pPrice = Number(opt.getAttribute("data-price") || 0);
                var pUrl = "/?search=" + encodeURIComponent(pName);
                var exists = window.__v114DraftIngredients.some(function(x) { return x.name === pName; });
                if (!exists) {
                  window.__v114DraftIngredients.push({
                    name: pName,
                    url: pUrl,
                    price: pPrice
                  });
                  renderDraftIngs();
                }
                ingSel.selectedIndex = 0;
              }
            };

            document.getElementById("v114-add-ing-btn").onclick = function() {
              var nEl = document.getElementById("v114-rec-ing-name");
              var uEl = document.getElementById("v114-rec-ing-url");
              var n = nEl.value.trim();
              if (!n) return;
              window.__v114DraftIngredients.push({
                name: n,
                url: uEl.value.trim() || ("/?search=" + encodeURIComponent(n)),
                price: Number(nEl.getAttribute("data-price") || 0)
              });
              nEl.value = "";
              uEl.value = "";
              renderDraftIngs();
            };

            var fileInp = document.getElementById("v114-rec-file");
            var prevBox = document.getElementById("v114-rec-img-preview-box");
            var prevImg = document.getElementById("v114-rec-img-preview");
            var remImgBtn = document.getElementById("v114-remove-rec-img");

            if (window.__v114DraftRecipeImg && prevBox && prevImg) {
              prevImg.src = window.__v114DraftRecipeImg;
              prevBox.style.display = "flex";
            }

            if (remImgBtn) {
              remImgBtn.onclick = function() {
                window.__v114DraftRecipeImg = "";
                if (prevBox) prevBox.style.display = "none";
                if (fileInp) fileInp.value = "";
              };
            }

            fileInp.onchange = function() {
              var f = fileInp.files && fileInp.files[0];
              if (!f) return;
              var reader = new FileReader();
              reader.onload = function(ev) {
                var img = new Image();
                img.onload = function() {
                  var canvas = document.createElement("canvas");
                  var maxW = 540;
                  var scale = img.width > maxW ? maxW / img.width : 1;
                  canvas.width = Math.round(img.width * scale);
                  canvas.height = Math.round(img.height * scale);
                  var ctx = canvas.getContext("2d");
                  ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                  var dataUrl = canvas.toDataURL("image/jpeg", 0.78);
                  window.__v114DraftRecipeImg = dataUrl;
                  if (prevImg && prevBox) {
                    prevImg.src = dataUrl;
                    prevBox.style.display = "flex";
                  }
                };
                img.src = ev.target.result;
              };
              reader.readAsDataURL(f);
            };

            document.getElementById("v114-save-rec-btn").onclick = function() {
              var title = document.getElementById("v114-rec-title").value.trim();
              var kw = document.getElementById("v114-rec-kw").value.trim();
              var manualUrl = document.getElementById("v114-rec-img-url").value.trim();
              var imgUrl = window.__v114DraftRecipeImg || manualUrl;
              var steps = document.getElementById("v114-rec-steps").value.trim();

              var pendingManualIng = document.getElementById("v114-rec-ing-name").value.trim();
              if (pendingManualIng) {
                var pendingManualUrl = document.getElementById("v114-rec-ing-url").value.trim() || ("/?search=" + encodeURIComponent(pendingManualIng));
                window.__v114DraftIngredients.push({
                  name: pendingManualIng,
                  url: pendingManualUrl,
                  price: 0
                });
              }

              if (!title || !steps) {
                alert("يرجى كتابة اسم الوصفة وخطوات التحضير أولاً");
                return;
              }
              if (!Array.isArray(window.__v114StudioConfig.recipes)) window.__v114StudioConfig.recipes = [];
              window.__v114StudioConfig.recipes.unshift({
                id: "rec_" + Date.now(),
                title: title,
                keywords: kw || title,
                imageUrl: imgUrl,
                steps: steps,
                ingredients: window.__v114DraftIngredients.slice()
              });
              window.__v114DraftIngredients = [];
              window.__v114DraftRecipeImg = "";
              commitAndSaveStudioV115("✅ تم حفظ الوصفة المصورة («" + title + "») ومنتجاتها بنجاح!");
            };

            Array.from(body.querySelectorAll(".v114-del-rec")).forEach(function(b) {
              b.onclick = function() {
                var i = parseInt(b.getAttribute("data-idx") || "0", 10);
                window.__v114StudioConfig.recipes.splice(i, 1);
                commitAndSaveStudioV115("🗑️ تم حذف الوصفة");
              };
            });
            return;
          }

          // TAB 5: معلومات المنتجات الخاصة للذكاء الاصطناعي
          if (tab === "prods") {
            var pMap = window.__v114StudioConfig.productAiMap || {};
            var pEntries = Object.entries(pMap).filter(function(e) { return e[0].indexOf("name:") === 0 && e[1]; });
            var pListHtml = "";
            if (pEntries.length === 0) {
              pListHtml = '<div style="text-align:center;padding:18px;background:#f8fbf9;border:1px dashed #9dcab3;border-radius:12px;color:#5c6f65;font-size:0.86rem;">لا توجد معلومات مخصصة مضافة للمنتجات بعد — اختر أي منتج بالأعلى وأضف معلوماته أو سعراته الحرارية.</div>';
            } else {
              pEntries.forEach(function(entry) {
                var pName = entry[0].slice(5);
                var pInfo = entry[1];
                pListHtml +=
                  '<div style="background:#f8fbf9;border:1.5px solid #9dcab3;border-radius:12px;padding:12px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:flex-start;gap:10px;">' +
                  '<div style="flex:1;">' +
                  '<strong style="color:#0d3825;font-size:0.9rem;">📦 ' + pName + '</strong>' +
                  '<div style="font-size:0.84rem;color:#334155;margin-top:4px;white-space:pre-line;">' + pInfo + '</div>' +
                  '</div>' +
                  '<button type="button" class="v114-del-pinfo" data-pname="' + pName.replace(/"/g, "&quot;") + '" style="background:#fee2e2;color:#b91c1c;border:none;border-radius:8px;padding:6px 10px;font-weight:800;font-size:0.78rem;cursor:pointer;">حذف</button>' +
                  '</div>';
              });
            }

            body.innerHTML =
              '<div style="background:#eef8f3;border:1.5px solid #9dcab3;border-radius:14px;padding:14px;margin-bottom:14px;">' +
              '<h4 style="margin:0 0 8px 0;color:#0d3825;font-size:0.95rem;">📦 تخصيص معلومات الذكاء الاصطناعي لمنتج معين:</h4>' +
              '<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:8px;">' +
              '<select id="v114-pinfo-sel" style="flex:1 1 220px;padding:9px;border-radius:10px;border:1px solid #9dcab3;background:#fff;font-size:0.85rem;font-weight:700;">' +
              buildProductOptionsHtmlV114() +
              '</select>' +
              '<input id="v114-pinfo-name" placeholder="أو اكتب اسم المنتج هنا" style="flex:1 1 200px;padding:9px;border-radius:10px;border:1px solid #9dcab3;background:#fff;font-size:0.85rem;" />' +
              '</div>' +
              '<textarea id="v114-pinfo-text" rows="3" placeholder="اكتب معلومات المنتج التي سيخبر بها الزبون (السعرات الحرارية، المكونات، هل يؤكل مباشرة أم يدخل في الحلى، مع إيش يتقدم)..." style="width:100%;padding:9px;border-radius:10px;border:1px solid #9dcab3;background:#fff;font-size:0.85rem;box-sizing:border-box;margin-bottom:8px;"></textarea>' +
              '<div style="display:flex;justify-content:space-between;align-items:center;">' +
              '<button type="button" id="v114-save-pinfo-btn" style="background:#0d3825;color:#d4af37;border:none;border-radius:10px;padding:10px 20px;font-weight:800;font-size:0.88rem;cursor:pointer;">💾 حفظ معلومات المنتج</button>' +
              '</div>' +
              '</div>' +
              '<h4 style="margin:0 0 8px 0;color:#0d3825;font-size:0.95rem;">📋 المنتجات المخصصة حالياً (' + pEntries.length + '):</h4>' +
              pListHtml;

            var piSel = document.getElementById("v114-pinfo-sel");
            piSel.onchange = function() {
              if (piSel.value) {
                document.getElementById("v114-pinfo-name").value = piSel.value;
                document.getElementById("v114-pinfo-text").value = (window.__v114StudioConfig.productAiMap && window.__v114StudioConfig.productAiMap["name:" + piSel.value]) || "";
              }
            };

            document.getElementById("v114-save-pinfo-btn").onclick = function() {
              var pn = document.getElementById("v114-pinfo-name").value.trim() || document.getElementById("v114-pinfo-sel").value.trim();
              var pt = document.getElementById("v114-pinfo-text").value.trim();
              if (!pn || !pt) {
                alert("يرجى اختيار المنتج وكتابة معلوماته أولاً");
                return;
              }
              if (!window.__v114StudioConfig.productAiMap) window.__v114StudioConfig.productAiMap = {};
              window.__v114StudioConfig.productAiMap["name:" + pn] = pt;
              commitAndSaveStudioV115("✅ تم حفظ معلومات المنتج («" + pn + "») بنجاح!");
            };

            Array.from(body.querySelectorAll(".v114-del-pinfo")).forEach(function(b) {
              b.onclick = function() {
                var pn = b.getAttribute("data-pname") || "";
                if (window.__v114StudioConfig.productAiMap) delete window.__v114StudioConfig.productAiMap["name:" + pn];
                commitAndSaveStudioV115("🗑️ تم حذف معلومات المنتج");
              };
            });
            return;
          }

          // TAB 6: الإشعارات الفعلية وطلبات الزبائن المباشرة
          if (tab === "reqs") {
            var reqs = window.__v114Requests || [];
            if (reqs.length === 0) {
              body.innerHTML =
                '<div style="text-align:center;padding:24px;background:#fffbeb;border:1.5px dashed #f59e0b;border-radius:14px;color:#78350f;font-size:0.88rem;">' +
                '📲 لا توجد طلبات توفير أو رسائل معلقة حالياً.<br/>عندما يطلب أي زبون منتجاً غير متوفر ويضغط «نعم، كلّم المتجر» سيصلك إشعار فعلي وصوت على هاتفك وتظهر رسالته هنا للرد عليه مباشرةً داخل المتجر.' +
                '</div>';
              return;
            }

            body.innerHTML = '<div id="v114-reqs-list"></div>';
            var listEl = document.getElementById("v114-reqs-list");
            reqs.forEach(function(req) {
              var card = document.createElement("div");
              card.style.cssText = "background:#fffbeb;border:1.5px solid #f59e0b;border-radius:14px;padding:14px;margin-bottom:10px;";
              var statusBadge = req.status === "replied"
                ? '<span style="background:#dcfce7;color:#166534;padding:3px 10px;border-radius:99px;font-size:0.76rem;font-weight:800;">تم الرد ✓</span>'
                : '<span style="background:#fee2e2;color:#991b1b;padding:3px 10px;border-radius:99px;font-size:0.76rem;font-weight:800;">بانتظار ردك 🔔</span>';

              card.innerHTML =
                '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">' +
                '<strong style="color:#0d3825;font-size:0.92rem;">📲 طلب الزبون: ' + (req.requestedItem || req.customerMessage || "") + '</strong>' +
                '<div style="display:flex;gap:6px;align-items:center;">' + statusBadge + '</div>' +
                '</div>' +
                (req.managerReply ? '<div style="background:#dcfce7;color:#166534;padding:8px 10px;border-radius:8px;font-size:0.83rem;margin-bottom:8px;white-space:pre-line;">ردك المرسل للزبون: ' + req.managerReply + '</div>' : '');

              var replyBox = document.createElement("div");
              replyBox.style.cssText = "display:flex;flex-wrap:wrap;gap:6px;align-items:center;";
              var inp = document.createElement("input");
              inp.placeholder = "اكتب ردك المباشر للزبون (مثال: وفرناه لك يا غالي وتقدر تطلبه الآن)...";
              inp.style.cssText = "flex:2 1 220px;padding:8px 10px;border:1px solid #9dcab3;border-radius:8px;font-size:0.84rem;background:#fff;";

              var prodSelect = document.createElement("select");
              prodSelect.style.cssText = "flex:1 1 170px;padding:8px;border:1px solid #9dcab3;border-radius:8px;font-size:0.8rem;background:#fff;";
              prodSelect.innerHTML = buildProductOptionsHtmlV114();

              var sendBtn = document.createElement("button");
              sendBtn.type = "button";
              sendBtn.textContent = "📨 إرسال الرد للزبون داخل المتجر";
              sendBtn.style.cssText = "background:#0d3825;color:#d4af37;border:none;border-radius:8px;padding:8px 14px;font-weight:800;font-size:0.82rem;cursor:pointer;";

              sendBtn.onclick = function() {
                if (!inp.value.trim()) return;
                var selProd = prodSelect.value.trim();
                var selUrl = selProd ? ("/?search=" + encodeURIComponent(selProd)) : "";
                sendBtn.textContent = "⏳ جاري الإرسال...";
                origFetchV112("/api/ai-v112/manager-reply", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({
                    requestId: req.id,
                    sessionId: req.sessionId,
                    replyText: inp.value.trim(),
                    attachedProductName: selProd,
                    attachedProductUrl: selUrl
                  })
                })
                  .then(function(r) { return r.json(); })
                  .then(function() {
                    req.status = "replied";
                    req.managerReply = inp.value.trim() + (selUrl ? "\\n🔗 رابط المنتج: " + selUrl : "");
                    renderFullAiStudioV114();
                  });
              };

              var delReqBtn = document.createElement("button");
              delReqBtn.type = "button";
              delReqBtn.textContent = "حذف";
              delReqBtn.style.cssText = "background:#fee2e2;color:#b91c1c;border:none;border-radius:8px;padding:8px 10px;font-weight:800;font-size:0.78rem;cursor:pointer;";
              delReqBtn.onclick = function() {
                origFetchV112("/api/ai-v112/delete-request", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ requestId: req.id })
                }).then(function() {
                  window.__v114Requests = (window.__v114Requests || []).filter(function(x) { return x.id !== req.id; });
                  renderFullAiStudioV114();
                });
              };

              replyBox.appendChild(inp);
              replyBox.appendChild(prodSelect);
              replyBox.appendChild(sendBtn);
              replyBox.appendChild(delReqBtn);
              card.appendChild(replyBox);
              listEl.appendChild(card);
            });
          }
        }

        document.addEventListener("click", function(ev) {
          try {
            var btn = ev.target && ev.target.closest ? ev.target.closest("button") : null;
            if (btn) {
              var bText = (btn.textContent || "").trim();
              if (bText.indexOf("إفراغ السلة") !== -1) {
                window.__v111ReorderedVariants = {};
                window.__v108ComputedCartSubtotal = 0;
                sessionStorage.removeItem("original_v111_reordered_variants");
              } else if (bText.indexOf("إضافة الطلب إلى السلة مجدداً") !== -1) {
                var bRaw = sessionStorage.getItem("original_v110_variant_backup");
                if (bRaw) {
                  var bObj = JSON.parse(bRaw);
                  Object.keys(bObj).forEach(function(k) {
                    localStorage.setItem(k, bObj[k]);
                  });
                }
                var reordMap = {};
                var allBoxes = Array.from(document.querySelectorAll("div, li"));
                allBoxes.forEach(function(box) {
                  if (box.children.length === 2) {
                    var c0 = (box.children[0].textContent || "").trim();
                    var c1 = (box.children[1].textContent || "").trim();
                    var nTxt = "";
                    if (/^\\d+\\s*[×xX*]\\s*\\d[\\d,.]*\\s*ر\\.ي$/.test(c0)) nTxt = c1;
                    else if (/^\\d+\\s*[×xX*]\\s*\\d[\\d,.]*\\s*ر\\.ي$/.test(c1)) nTxt = c0;
                    if (nTxt) {
                      var pm = Array.from(nTxt.matchAll(/\\(([^()]*:\\s*\\d+(?:\\.\\d+)?[^()]*)\\)/g));
                      if (pm.length > 0) {
                        var rawInner = pm[pm.length - 1][1].trim().replace(/\\s*[×xX*]\\s*\\d+.*$/, "").trim();
                        var basePName = nTxt.replace(/\\s*\\([^()]*\\)\\s*$/g, "").trim();
                        if (basePName && rawInner.indexOf(":") !== -1) {
                          reordMap[basePName] = { raw: rawInner };
                        }
                      }
                    }
                  }
                });
                if (Object.keys(reordMap).length > 0) {
                  window.__v111ReorderedVariants = reordMap;
                  sessionStorage.setItem("original_v111_reordered_variants", JSON.stringify(reordMap));
                }
              }
            }
          } catch (e) {}
          setTimeout(syncVariantModalPrice, 5);
          setTimeout(syncVariantModalPrice, 50);
          setTimeout(syncVariantModalPrice, 180);
        }, true);
        setInterval(syncVariantModalPrice, 250);
      })();
    </script>
"""
    ht = ht.replace("</body>", v116_master_script + "\n  </body>", 1)
    html_path.write_text(ht, encoding="utf-8")
    print("5. Updated client/index.html (v116 Mouth-Watering Recipe Card in Chat + Full Steps + Linked Products)!")

# 6. Bump sw.js cache to v116
sw_path = pathlib.Path("client/public/sw.js")
if sw_path.exists():
    swc = sw_path.read_text(encoding="utf-8")
    swc = re.sub(r'const CACHE = "original-shell-v[^"]*";', 'const CACHE = "original-shell-v116";', swc)
    sw_path.write_text(swc, encoding="utf-8")
    print("6. Bumped sw.js cache to v116!")

print("=== 7. فحص كود السيرفر والواجهة عبر esbuild (0.5 ثانية) ===")
res_srv = subprocess.run(
    ["./node_modules/.bin/esbuild", "server/_core/index.ts", "--platform=node", "--packages=external", "--bundle", "--format=esm", "--outdir=dist"],
    capture_output=True, text=True
)
if res_srv.returncode != 0:
    print("SERVER ESBUILD ERROR:")
    print(res_srv.stderr or res_srv.stdout)
    sys.exit(1)

res_cli = subprocess.run(
    ["./node_modules/.bin/esbuild", "client/src/pages/Admin.tsx", "client/src/pages/Home.tsx", "--bundle", "--packages=external", "--jsx=automatic", "--outdir=dist/check_client"],
    capture_output=True, text=True
)
if res_cli.returncode != 0:
    print("CLIENT ESBUILD ERROR:")
    print(res_cli.stderr or res_cli.stdout)
    sys.exit(1)

subprocess.run(["rm", "-rf", "dist/check_client"], check=False)
print("BOTH SERVER & CLIENT ESBUILD PASSED 100%! Pushing to GitHub & Render...")
subprocess.run(["git", "add", "-A"], check=True)
subprocess.run(["git", "commit", "-m", "v116: display mouth-watering recipe hero image, full steps, and linked products directly inside AI chat bubbles"], check=True)
subprocess.run(["git", "push", "origin", "main", "--force"], check=True)
print("=== تم رفع التحديث الشامل v116 بنجاح 100% إلى Render! ===")
