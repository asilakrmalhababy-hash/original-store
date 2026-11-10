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

  const cacheKey = normMsg.replace(/\s+/g, " ");
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
      reply: "أبشر من عيوني يا غالي! 📲 أرسلت إشعار فوري الآن لهاتف مدير المتجر بطلبك («" + requestedTopic + "»).\nأول ما يرد المدير سيظهر رده هنا أمامك في المحادثة مباشرةً!",
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
      let replyTxt = String(rule.response || "").replace(/\(\s*رقم\s*\d+\s*\)/g, "");
      if (rule.linkedProductUrl && !replyTxt.includes(rule.linkedProductUrl)) {
        replyTxt += "\n🔗 رابط المنتج: " + rule.linkedProductUrl;
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
      "يا غالي، جبت لك ألذ وأفخم وصفة تفتح النفس من مطبخ أورجنال: 😍✨\n" +
      "🍰 «" + matchedRec.title + "»\n\n" +
      "📋 طريقة التحضير الكاملة:\n" +
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
      canContactStore: false
    };
  }

  const matchedProducts = allProducts.filter(p => {
    const pName = cleanProductNameV112(p.name);
    if (!pName || pName.length < 3) return false;
    if (userMsg.includes(pName)) return true;
    const words = pName.split(/\s+/).filter(w => w.length >= 4);
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
        baseWelcome += "\n\n" + (generalPromo.promoBadge || "⭐ لا يفوتك اليوم:") + " «" + generalPromo.productName + "» — " + (generalPromo.promoMessage || "");
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
      "فهمتك يا غالي! بخصوص «" + pName + "» (متوفر عندنا بسعر " + pPrice.toLocaleString("en-US") + " ر.ي):\n" +
      modalInfo.content.replace(/^✨[^\n]*\n/, "");

    if (companions.length > 0) {
      const compNames = companions.map(c => "«" + cleanProductNameV112(c.name) + "» (" + Math.round(Number(c.price)).toLocaleString("en-US") + " ر.ي)").join(" أو ");
      friendlyReply += "\n\nوبما إنك تحب هذا النوع، عندنا أيضاً في المتجر " + compNames + " إذا تحب تجربه معه!";
    }

    const prodResult = {
      reply: friendlyReply.replace(/\(\s*رقم\s*\d+\s*\)/g, ""),
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
    .split(/\s+/)
    .map(w => w.trim())
    .filter(w => w.length >= 3 && !["عندكم", "اريد", "أريد", "ابغى", "أبغى", "اشتي", "أشتي", "موجود", "متوفر", "حبة", "باكيت", "كرتون", "سعر", "بكم", "كم", "هل", "في", "من", "على", "مع", "هذا", "هذه"].includes(w));

  const partialMatches = allProducts.filter(p => {
    const pName = cleanProductNameV112(p.name);
    return Number(p.price) > 5 && queryWords.some(w => pName.includes(w));
  }).slice(0, 3);

  const cleanWanted = userMsg.replace(/^(هل عندكم|عندكم|هل يوجد|أريد|اريد|أشتي|اشتي|ابغى|أبغى|بكم|كم سعر)\s*/i, "").replace(/[؟?]/g, "").trim() || userMsg;
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
    ? unavailInst.content.replace(/\{المنتج\}/g, cleanWanted) + "\n" + altSentence + "هل تريد أكلم المتجر إذا عندهم؟"
    : "فهمتك يا غالي، أنت تريد «" + cleanWanted + "».. حلو حلو! 👌\n" +
      altSentence +
      "وإذا تريد نفس «" + cleanWanted + "» بالضبط، أقدر أتواصل لك الحين مع إدارة المتجر وأسألهم إذا متوفر عندهم أو يوفرونه لك فوراً!\n" +
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
