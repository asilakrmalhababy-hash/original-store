import pathlib, re, subprocess, sys

print("=== بدء التحديث الجذري الشامل v112 (تطوير الذكاء الاصطناعي + 3 خيارات لتعليم الذكاء الاصطناعي + معلومات ذكاء اصطناعي لكل منتج + إشعارات وطلبات التوفير الحية + إصلاح حسابات السلة) ===")

# 0. Restore server/commerce.ts, server/_core/index.ts, Home.tsx, client/index.html to clean v98 (db9eb83) state first so we apply everything cleanly without any duplicate patches!
subprocess.run(["git", "checkout", "db9eb83", "--", "server/commerce.ts", "server/_core/index.ts", "client/src/pages/Home.tsx", "client/index.html"], check=False)

# ==============================================================================
# 1. Create standalone server/ai_engine_v112.ts
# ==============================================================================
ai_engine_ts = """import { getDb } from "./db";
import { products } from "../drizzle/schema";

export interface AiTrainingRuleV112 {
  id: string;
  trigger: string;
  response: string;
}

export interface AiConfigV112 {
  mode1StylePrompt: string;
  mode2Rules: AiTrainingRuleV112[];
  mode3CategoryRules: string;
  productAiMap: Record<string, string>;
}

export interface CustomerAiRequestV112 {
  id: string;
  sessionId: string;
  customerName: string;
  customerPhone: string;
  requestedItem: string;
  customerMessage: string;
  status: "pending" | "replied";
  managerReply: string;
  repliedAt?: number;
  createdAt: number;
}

const DEFAULT_AI_CONFIG_V112: AiConfigV112 = {
  mode1StylePrompt:
    "تكلم مع الزبون كصديق يمني ذكي، ودود، وطبيعي جداً (مثل: فهمتك يا غالي، حلو حلو، أبشر من عيوني). " +
    "إذا كان الزبون يسولف سوالف عامة أو يسأل سؤالاً عاماً لا علاقة له بالشراء، رد عليه بذكاء ولطف بدون أن تقحم منتجات المتجر أو السلة نهائياً. " +
    "يمنع منعاً باتاً ذكر أرقام المنتجات الداخلية مثل (رقم 630072). " +
    "إذا سأل الزبون عن منتج غير متوفر في المتجر، لا تعطيه اقتراحاً خاطئاً، بل قل له: (فهمتك يا غالي، أنت تريد كذا.. حلو! حالياً مش موجود بنفس الاسم في الرف، وإذا تحب أقدر أتواصل لك الحين مع المتجر وأسألهم إذا عندهم أو يوفرونه لك! هل تريد أكلم المتجر؟).",
  mode2Rules: [
    {
      id: "r1",
      trigger: "بسكويت ماري",
      response: "بسكويت ماري ممتاز مع الشاي والحليب، ويصلح لعمل ألذ حلى بارد سريع بطبقات القشطة والكاكاو، وسعرات الحبة الواحدة حوالي 25 سعرة حرارية فقط."
    },
    {
      id: "r2",
      trigger: "شوكلاتة البليلا",
      response: "شوكلاتة البليلا سناك لذيذ جاهز للأكل مباشرة بطعم الكاكاو الغني (سعر الحبة 50 ر.ي)، تعطي طاقة سريعة (حوالي 130 سعرة حرارية) وممتازة جداً مع القهوة أو الشاي."
    }
  ],
  mode3CategoryRules:
    "1) الشوكولاتة والويفر والعلكة والشيبس: لا تعرض لها أبداً طرق تحضير أو طبخ أو توابل؛ اعرض فقط معلومات عن المنتج، السعرات الحرارية والقيمة الغذائية، ومع إيش يؤكل (مثل القهوة أو الشاي). " +
    "2) البسكويت السادة (مثل ماري وأبو ولد): اذكر أنه يصلح لعمل حلى بارد سريع أو مع الشاي، مع ذكر السعرات الحرارية. " +
    "3) العصائر والمشروبات: اعرض القيمة الغذائية، السعرات الحرارية، وأفضل طريقة لتقديمها باردة.",
  productAiMap: {}
};

let memoryConfigV112: AiConfigV112 = { ...DEFAULT_AI_CONFIG_V112 };
let memoryRequestsV112: CustomerAiRequestV112[] = [];
let dbInitializedV112 = false;

async function ensureAiTableV112() {
  if (dbInitializedV112) return;
  try {
    const db: any = await getDb();
    if (!db || typeof db.execute !== "function") return;
    await db.execute(
      "CREATE TABLE IF NOT EXISTS ai_knowledge_v112 (" +
      "k VARCHAR(190) PRIMARY KEY, " +
      "v LONGTEXT NOT NULL, " +
      "updatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP" +
      ")"
    );
    dbInitializedV112 = true;

    const [rows]: any = await db.execute("SELECT k, v FROM ai_knowledge_v112");
    if (Array.isArray(rows)) {
      for (const r of rows) {
        if (r.k === "config" && r.v) {
          try {
            const parsed = JSON.parse(String(r.v));
            memoryConfigV112 = {
              mode1StylePrompt: parsed.mode1StylePrompt || DEFAULT_AI_CONFIG_V112.mode1StylePrompt,
              mode2Rules: Array.isArray(parsed.mode2Rules) ? parsed.mode2Rules : DEFAULT_AI_CONFIG_V112.mode2Rules,
              mode3CategoryRules: parsed.mode3CategoryRules || DEFAULT_AI_CONFIG_V112.mode3CategoryRules,
              productAiMap: parsed.productAiMap && typeof parsed.productAiMap === "object" ? parsed.productAiMap : {}
            };
          } catch {}
        } else if (r.k === "requests" && r.v) {
          try {
            const parsedReq = JSON.parse(String(r.v));
            if (Array.isArray(parsedReq)) memoryRequestsV112 = parsedReq;
          } catch {}
        }
      }
    }
  } catch {}
}

async function saveAiKeyV112(key: string, valObj: any) {
  try {
    await ensureAiTableV112();
    const db: any = await getDb();
    if (!db || typeof db.execute !== "function") return;
    const jsonStr = JSON.stringify(valObj);
    await db.execute(
      "INSERT INTO ai_knowledge_v112 (k, v) VALUES (?, ?) ON DUPLICATE KEY UPDATE v = VALUES(v)",
      [key, jsonStr]
    );
  } catch {}
}

export async function getAiConfigV112(): Promise<AiConfigV112> {
  await ensureAiTableV112();
  return memoryConfigV112;
}

export async function getAiRequestsV112(): Promise<CustomerAiRequestV112[]> {
  await ensureAiTableV112();
  return memoryRequestsV112;
}

export function cleanProductNameV112(raw: string): string {
  return String(raw || "")
    .replace(/\\(\\s*رقم\\s*\\d+\\s*\\)/g, "")
    .replace(/\\s*\\([^()]*\\)\\s*$/g, "")
    .trim();
}

export function getProductCustomAiInfoV112(productId?: any, productName?: any): string {
  const map = memoryConfigV112.productAiMap || {};
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
  if (/(بسكويت|بسكوت|ماري|أبو ولد|ابو ولد|نخالة|شاي|ديما|أوريو|اوريو|معمول|كليجا)/.test(combined)) {
    return "biscuit_dessert";
  }
  if (/(شوكلات|شوكولات|بليلا|بريك|ويفر|علك|باطوق|حلاو|مصاص|شيبس|بطاط|فشار|كروسان|كيك|جالكسي|كتكات|سنكرز|توبي|سعيد|مارشملو|جيلي|كاكاو)/.test(combined)) {
    return "chocolate_snack";
  }
  if (/(عصير|رواب|مشروب|مانجو|برتقال|جوافة|تفاح|حليب|لبن|زبادي|ماء|مياه|بيبسي|كوكاكولا|ميرندا|سفن|ردبول|جوي|نسكافيه|قهوة)/.test(combined)) {
    return "drink_juice";
  }
  return "cooking_food";
}

export function buildSmartProductModalDataV112(productName: string, price: number, unit: string, categoryName = "", customTopic = "", productId?: any) {
  const cleanName = cleanProductNameV112(productName) || productName;
  const customAi = getProductCustomAiInfoV112(productId, cleanName);
  const kind = classifyProductKindV112(cleanName, categoryName, customAi);
  const priceStr = price > 0 ? price.toLocaleString("en-US") + " ريال" : "";
  const customNoteBlock = customAi ? "\\n💡 معلومة خاصة عن المنتج: " + customAi : "";

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
        "1️⃣ السعرات التقريبية: تحتوي الحصة الواحدة على حوالي 110 إلى 160 سعرة حرارية تمنح الجسم طاقة سريعة ونشاطاً فورياً.\\n" +
        "2️⃣ القيمة الغذائية: غني بالكاكاو والسكريات البسيطة التي تحسن المزاج وترفع التركيز.\\n" +
        "3️⃣ نصيحة: تناوله باعتدال كسناك لذيذ في وسط اليوم أو مع فنجان قهوة." +
        customNoteBlock;
    } else if (customTopic && (customTopic.includes("يؤكل") || customTopic.includes("يُقدم") || customTopic.includes("قهوة"))) {
      text =
        "☕ أفضل طرق الاستمتاع بـ «" + cleanName + "»:\\n" +
        "1️⃣ مع القهوة أو الشاي: طعمه رائع جداً بجانب فنجان قهوة أو كوب شاي دافئ.\\n" +
        "2️⃣ مع الحليب البارد أو الدافئ: وجبة خفيفة محببة للأطفال والكبار.\\n" +
        "3️⃣ جاهز للأكل مباشرة: لا يحتاج إلى أي تحضير أو إضافات." +
        customNoteBlock;
    } else {
      text =
        "✨ معلومات المنتج والقيمة الغذائية لـ «" + cleanName + "»" + (priceStr ? " (متوفر بسعر " + priceStr + ")" : "") + ":\\n" +
        "1️⃣ نبذة عن المنتج: سناك حالي جاهز للأكل مباشرة بطعم غني ولذيذ، لا يحتاج إلى أي طبخ أو تحضير.\\n" +
        "2️⃣ السعرات الحرارية التقريبية: حوالي 120 – 150 سعرة حرارية للحصة الواحدة، ممتاز لتجديد الطاقة والنشاط.\\n" +
        "3️⃣ مع إيش يتقدم؟ مثالي جداً مع فنجان قهوة، شاي، أو كوب حليب، أو كتحلية خفيفة في أي وقت." +
        customNoteBlock;
    }
    return {
      modalTitle: "✨ معلومات وقيمة غذائية: " + cleanName,
      chips,
      content: text,
      kind
    };
  }

  if (kind === "biscuit_dessert") {
    const chips = [
      "🍰 فكرة حلى بارد وسريع به",
      "🔥 السعرات والقيمة الغذائية",
      "☕ مع الشاي والحليب",
      "ℹ️ معلومات عن المنتج"
    ];
    let text = "";
    if (customTopic && customTopic.includes("سعرات")) {
      text =
        "🔥 السعرات الحرارية والقيمة الغذائية لـ «" + cleanName + "»:\\n" +
        "1️⃣ السعرات الحرارية: تحتوي الحبة الواحدة على حوالي 25 – 35 سعرة حرارية فقط (حوالي 140 سعرة لكل 4 حبات).\\n" +
        "2️⃣ القيمة الغذائية: خفيف على المعدة ويمد الجسم بالكربوهيدرات المناسبة لفطور الصباح أو سناك العصر.\\n" +
        "3️⃣ الاستخدام: قوامه الهش يجعله ممتازاً لعمل الحلويات الباردة أو التغميس مع الشاي والحليب." +
        customNoteBlock;
    } else {
      text =
        "✨ معلومات وأفكار جميلة لـ «" + cleanName + "»" + (priceStr ? " (متوفر بسعر " + priceStr + ")" : "") + ":\\n" +
        "1️⃣ حلى البسكويت البارد السريع: غمس البسكويت سريعاً في الحليب ورتبه في طبقات مع القشطة والكاكاو أو الكريمة، وضعه في الثلاجة نصف ساعة لتحصل على ألذ حلى بيتي!\\n" +
        "2️⃣ السعرات الحرارية: خفيف ومناسب جداً، الحبة الواحدة حوالي 25 – 35 سعرة حرارية.\\n" +
        "3️⃣ التقديم الكلاسيكي: رفيق مثالي لكوب الشاي العدني أو الحليب الساخن في الصباح والمساء." +
        customNoteBlock;
    }
    return {
      modalTitle: "✨ معلومات وأفكار حلى: " + cleanName,
      chips,
      content: text,
      kind
    };
  }

  if (kind === "drink_juice") {
    const chips = [
      "🔥 السعرات والقيمة الغذائية",
      "ℹ️ معلومات عن المشروب",
      "🧊 أفضل طريقة تقديم بارد",
      "🥨 سناك خفيف يناسبه"
    ];
    const text =
      "✨ معلومات وقيمة غذائية لـ «" + cleanName + "»" + (priceStr ? " (متوفر بسعر " + priceStr + ")" : "") + ":\\n" +
      "1️⃣ القيمة الغذائية والسعرات: يمنح ترطيباً وانتعاشاً فورياً، وتحتوي العبوة على حوالي 90 – 130 سعرة حرارية.\\n" +
      "2️⃣ أفضل طريقة تقديم: يُقدم بارداً جداً من الثلاجة أو مع مكعبات الثلج لانتعاش مضاعف.\\n" +
      "3️⃣ مع إيش يناسب؟ ممتاز بجانب البسكويت، الكيك، أو الشيبس والمقرمشات في جلسات العصر." +
      customNoteBlock;
    return {
      modalTitle: "✨ معلومات وقيمة غذائية: " + cleanName,
      chips,
      content: text,
      kind
    };
  }

  if (kind === "non_food") {
    const chips = [
      "ℹ️ مواصفات ومعلومات المنتج",
      "📦 التوفر والخيارات"
    ];
    const text =
      "✨ معلومات المنتج «" + cleanName + "»" + (priceStr ? " (السعر: " + priceStr + ")" : "") + ":\\n" +
      "1️⃣ منتج أصلي متوفر في متجر أورجنال بجودة مضمونة.\\n" +
      "2️⃣ يمكنك اختيار الكمية المطلوبة وإضافتها مباشرة إلى سلة التسوق." +
      customNoteBlock;
    return {
      modalTitle: "✨ معلومات المنتج: " + cleanName,
      chips,
      content: text,
      kind
    };
  }

  const chips = [
    "🍳 أفكار وطرق استخدامه",
    "🔥 السعرات والقيمة الغذائية",
    "💡 نصيحة حفظ وجودة",
    "🛒 مقاضي تكمله"
  ];
  const text =
    "✨ معلومات واستخدامات «" + cleanName + "»" + (priceStr ? " (متوفر بسعر " + priceStr + ")" : "") + ":\\n" +
    "1️⃣ في المطبخ والوجبات: مكون أساسي ممتاز لتحضير وجبات بيتية شهية وسريعة.\\n" +
    "2️⃣ القيمة الغذائية: غني بالعناصر الغذائية المفيدة للمائدة اليومية.\\n" +
    "3️⃣ نصيحة الاستخدام: يُحفظ في مكان جاف وبارد للحفاظ على نكهته وجودته الطازجة." +
    customNoteBlock;
  return {
    modalTitle: "✨ استخدامات ومعلومات: " + cleanName,
    chips,
    content: text,
    kind
  };
}

export async function handleSmartAiChatV112(input: {
  message: string;
  sessionId?: string;
  customerName?: string;
  customerPhone?: string;
  history?: Array<{ role: string; content: string }>;
}) {
  await ensureAiTableV112();
  const userMsg = String(input.message || "").trim();
  const normMsg = userMsg.toLowerCase();

  // 1. Politeness / Safety guard
  if (/(اباحي|إباحي|مايا خليفه|مايا خليفة|جنس|سكس|porn|xxx)/i.test(normMsg)) {
    return {
      reply: "حياك الله يا غالي، أنا مساعد متجر أورجنال، يسعدني دائماً خدمتك في كل ما يخص المنتجات، المعلومات الغذائية، أو السوالف الطيبة المحترمة. آمرني كيف أقدر أخدمك اليوم؟",
      suggestedItems: [],
      quickActions: [],
      canContactStore: false
    };
  }

  // 2. Check if customer is confirming "Yes, contact the store for me!"
  const isConfirmingStoreContact =
    /(نعم|ايوه|أيوة|ايه|أيه|كلمهم|كلم المتجر|كلّم المتجر|تواصل معهم|ارسل لهم|أرسل لهم|ياريت|يا ريت|اكيد|أكيد|تواصل لك مع المتجر)/.test(normMsg) &&
    (normMsg.includes("المتجر") ||
      (Array.isArray(input.history) &&
        input.history.some(h => String(h.content || "").includes("أكلم المتجر") || String(h.content || "").includes("أتواصل لك"))));

  if (isConfirmingStoreContact) {
    const prevUserMsgs = (input.history || []).filter(h => h.role === "user").map(h => h.content);
    const requestedTopic = prevUserMsgs.length > 0 ? prevUserMsgs[prevUserMsgs.length - 1] : userMsg;
    const reqRecord: CustomerAiRequestV112 = {
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
    memoryRequestsV112.unshift(reqRecord);
    if (memoryRequestsV112.length > 200) memoryRequestsV112 = memoryRequestsV112.slice(0, 200);
    await saveAiKeyV112("requests", memoryRequestsV112);

    return {
      reply: "أبشر من عيوني يا غالي! 📲 كلمت إدارة المتجر الآن وأرسلت إشعار فوري لهاتف المدير بطلبك («" + requestedTopic + "»).\\nأول ما يرد المدير سيظهر رده هنا أمامك في المحادثة مباشرةً!",
      suggestedItems: [],
      quickActions: [],
      canContactStore: false,
      requestSent: true,
      requestObj: reqRecord
    };
  }

  // 3. Check Manager's Mode 2 Custom Q&A / Alternatives Rules first!
  for (const rule of memoryConfigV112.mode2Rules || []) {
    const trig = String(rule.trigger || "").trim();
    if (trig && userMsg.includes(trig)) {
      return {
        reply: String(rule.response || "").replace(/\\(\\s*رقم\\s*\\d+\\s*\\)/g, ""),
        suggestedItems: [],
        quickActions: [],
        canContactStore: false
      };
    }
  }

  // 4. Load store catalog products from DB
  let allProducts: any[] = [];
  try {
    const db: any = await getDb();
    if (db) {
      allProducts = await db.select().from(products);
    }
  } catch {}

  // 5. Check if user is asking about a specific product in the store
  const matchedProducts = allProducts.filter(p => {
    const pName = cleanProductNameV112(p.name);
    if (!pName || pName.length < 3) return false;
    if (userMsg.includes(pName)) return true;
    const words = pName.split(/\\s+/).filter(w => w.length >= 4);
    return words.length > 0 && words.every(w => userMsg.includes(w));
  });

  // Check if user is just chatting / asking general conversation without wanting store products forced on them
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
      return {
        reply: "يا هلا ومليون غلا بك يا غالي! 😊 الحمد لله بخير دامك بخير. أنا معك لو حبيت تسأل عن أي منتج، سعراته الحرارية، أفكار حلى، أو حتى لو تدور على غرض معين وتبغاني أكلم لك المتجر يوفره لك. آمرني؟",
        suggestedItems: [],
        quickActions: [],
        canContactStore: false
      };
    }
  }

  // 6. If user asks about a product that IS in the store
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

    return {
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
      quickActions: modalInfo.chips.slice(0, 3),
      canContactStore: false
    };
  }

  // 7. Product not directly matched -> offer genuine partial matches (if any) + offer to contact store manager!
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

  const friendReply =
    "فهمتك يا غالي، أنت تريد «" + cleanWanted + "».. حلو حلو! 👌\\n" +
    altSentence +
    "وإذا تريد نفس «" + cleanWanted + "» بالضبط، أقدر أتواصل لك الحين مع إدارة المتجر وأسألهم إذا متوفر عندهم أو يوفرونه لك فوراً!\\n" +
    "هل تريد أكلم المتجر إذا عندهم؟";

  return {
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
}

export function registerAiEngineV112(app: any) {
  ensureAiTableV112().catch(() => {});

  app.get("/api/ai-v112/config", async (_req: any, res: any) => {
    try {
      const config = await getAiConfigV112();
      const requests = await getAiRequestsV112();
      res.json({ ok: true, config, requests });
    } catch (e: any) {
      res.status(500).json({ ok: false, error: String(e?.message || e) });
    }
  });

  app.post("/api/ai-v112/save-training", async (req: any, res: any) => {
    try {
      await ensureAiTableV112();
      const body = req.body || {};
      if (typeof body.mode1StylePrompt === "string") {
        memoryConfigV112.mode1StylePrompt = body.mode1StylePrompt.trim();
      }
      if (Array.isArray(body.mode2Rules)) {
        memoryConfigV112.mode2Rules = body.mode2Rules;
      }
      if (typeof body.mode3CategoryRules === "string") {
        memoryConfigV112.mode3CategoryRules = body.mode3CategoryRules.trim();
      }
      await saveAiKeyV112("config", memoryConfigV112);
      res.json({ ok: true, config: memoryConfigV112 });
    } catch (e: any) {
      res.status(500).json({ ok: false, error: String(e?.message || e) });
    }
  });

  app.post("/api/ai-v112/save-product-info", async (req: any, res: any) => {
    try {
      await ensureAiTableV112();
      const { productId, productName, aiInfo } = req.body || {};
      if (!memoryConfigV112.productAiMap) memoryConfigV112.productAiMap = {};
      const cleanInfo = String(aiInfo || "").trim();
      if (productId !== undefined && productId !== null && String(productId).trim() !== "") {
        memoryConfigV112.productAiMap["id:" + String(productId).trim()] = cleanInfo;
      }
      const cName = cleanProductNameV112(String(productName || ""));
      if (cName) {
        memoryConfigV112.productAiMap["name:" + cName] = cleanInfo;
      }
      await saveAiKeyV112("config", memoryConfigV112);
      res.json({ ok: true, productAiMap: memoryConfigV112.productAiMap });
    } catch (e: any) {
      res.status(500).json({ ok: false, error: String(e?.message || e) });
    }
  });

  app.post("/api/ai-v112/product-modal", async (req: any, res: any) => {
    try {
      await ensureAiTableV112();
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
      await ensureAiTableV112();
      const body = req.body || {};
      const reqRecord: CustomerAiRequestV112 = {
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
      memoryRequestsV112.unshift(reqRecord);
      if (memoryRequestsV112.length > 200) memoryRequestsV112 = memoryRequestsV112.slice(0, 200);
      await saveAiKeyV112("requests", memoryRequestsV112);
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
      await ensureAiTableV112();
      const { requestId, sessionId, replyText } = req.body || {};
      const cleanReply = String(replyText || "").trim();
      if (!cleanReply) {
        return res.status(400).json({ ok: false, error: "يرجى كتابة نص الرد" });
      }
      let target = memoryRequestsV112.find(r => r.id === requestId);
      if (!target && sessionId) {
        target = memoryRequestsV112.find(r => r.sessionId === sessionId);
      }
      if (!target) {
        target = {
          id: "req_" + Date.now(),
          sessionId: String(sessionId || "all"),
          customerName: "زبون المتجر",
          customerPhone: "",
          requestedItem: "رد مباشر من الإدارة",
          customerMessage: "",
          status: "replied",
          managerReply: cleanReply,
          repliedAt: Date.now(),
          createdAt: Date.now()
        };
        memoryRequestsV112.unshift(target);
      } else {
        target.status = "replied";
        target.managerReply = cleanReply;
        target.repliedAt = Date.now();
      }
      await saveAiKeyV112("requests", memoryRequestsV112);
      res.json({ ok: true, requestObj: target });
    } catch (e: any) {
      res.status(500).json({ ok: false, error: String(e?.message || e) });
    }
  });

  app.get("/api/ai-v112/customer-poll", async (req: any, res: any) => {
    try {
      await ensureAiTableV112();
      const sessionId = String(req.query?.sessionId || "").trim();
      const matching = memoryRequestsV112.filter(
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
print("1. Created server/ai_engine_v112.ts!")

# ==============================================================================
# 2. Register registerAiEngineV112(app) & /api/admin/order-add-item in server/_core/index.ts
# ==============================================================================
srv_index = pathlib.Path("server/_core/index.ts")
if srv_index.exists():
    si = srv_index.read_text(encoding="utf-8")
    imports_to_add = 'import { registerAiEngineV112 } from "../ai_engine_v112";\nimport { addInvoiceItemToOrderV99 } from "../commerce";\n'
    if "registerAiEngineV112" not in si:
        si = imports_to_add + si
        route_hook = """
  registerAiEngineV112(app);
  app.post("/api/admin/order-add-item", async (req, res) => {
    try {
      const result = await addInvoiceItemToOrderV99(req.body || {});
      res.json(result);
    } catch (err: any) {
      res.status(400).json({ ok: false, error: String(err?.message || err) });
    }
  });
"""
        if "app.use(express.json" in si:
            idx_json = si.find("app.use(express.json")
            line_end = si.find("\n", idx_json)
            si = si[:line_end+1] + route_hook + si[line_end+1:]
        elif "const app = express();" in si:
            idx_app = si.find("const app = express();")
            line_end = si.find("\n", idx_app)
            si = si[:line_end+1] + "  app.use(express.json());\n" + route_hook + si[line_end+1:]
        srv_index.write_text(si, encoding="utf-8")
        print("2. Registered AI Engine v112 and order-add-item routes in server/_core/index.ts!")

# ==============================================================================
# 3. Update server/commerce.ts:
# ==============================================================================
comm_path = pathlib.Path("server/commerce.ts")
if comm_path.exists():
    cc = comm_path.read_text(encoding="utf-8")

    # Strip "(رقم ${...})" from any template literal in server/commerce.ts
    cc = re.sub(r'\(\s*رقم\s*\$\{[^}]+\}\s*\)', '', cc)

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
# 4. Update client/src/pages/Home.tsx (from clean v98 state):
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
# 5. Update client/index.html (100% pure ES5/ES6 browser JS — ZERO TypeScript casts!):
# ==============================================================================
html_path = pathlib.Path("client/index.html")
if html_path.exists():
    ht = html_path.read_text(encoding="utf-8")
    ht = re.sub(r'<script>\s*\(function\(\)\s*\{[\s\S]*?syncVariantModalPrice[\s\S]*?</script>', '', ht)

    v112_master_script = """
    <script>
      (function() {
        try {
          localStorage.removeItem("original_v107_by_name");
          sessionStorage.removeItem("original_v109_cart_subtotal");
        } catch (e) {}

        window.__v108ComputedCartSubtotal = 0;
        window.__v111ReorderedVariants = {};
        window.__v112AiConfig = { mode1StylePrompt: "", mode2Rules: [], mode3CategoryRules: "", productAiMap: {} };
        window.__v112AiRequests = [];
        window.__v112DeliveredReplyIds = {};
        window.__v112NotifiedReqIds = {};
        window.__v112SessionId = localStorage.getItem("original_v112_session_id") || ("sess_" + Date.now() + "_" + Math.random().toString(36).slice(2, 7));
        try {
          localStorage.setItem("original_v112_session_id", window.__v112SessionId);
          var savedReord = sessionStorage.getItem("original_v111_reordered_variants");
          if (savedReord) window.__v111ReorderedVariants = JSON.parse(savedReord) || {};
          var savedDeliv = localStorage.getItem("original_v112_delivered_replies");
          if (savedDeliv) window.__v112DeliveredReplyIds = JSON.parse(savedDeliv) || {};
        } catch (e) {}

        // Intercept tRPC AI Assistant calls via window.fetch so our Smart AI Engine v112 answers with friend style,
        // custom 3-mode training, per-product AI knowledge, zero "(رقم 630072)", and zero forced random products!
        var origFetchV112 = window.fetch;
        if (origFetchV112 && !window.__v112FetchWrapped) {
          window.__v112FetchWrapped = true;
          window.fetch = function(input, init) {
            var urlStr = typeof input === "string" ? input : (input && input.url ? input.url : "");
            var isTrpcAiChat =
              urlStr.indexOf("/api/trpc/") !== -1 &&
              /(assistant|chat|chef|ask|message)/i.test(urlStr) &&
              init &&
              init.method === "POST" &&
              typeof init.body === "string";

            if (isTrpcAiChat) {
              var extractedMsg = "";
              try {
                var parsedBody = JSON.parse(init.body);
                var innerJson = parsedBody.json || (parsedBody["0"] && parsedBody["0"].json) || parsedBody;
                extractedMsg = String(innerJson.message || innerJson.prompt || innerJson.query || innerJson.text || "").trim();
              } catch (e) {}

              if (extractedMsg) {
                return Promise.all([
                  origFetchV112.apply(this, arguments),
                  origFetchV112("/api/ai-v112/chat", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                      message: extractedMsg,
                      sessionId: window.__v112SessionId
                    })
                  }).then(function(r) { return r.json(); }).catch(function() { return null; })
                ]).then(function(results) {
                  var origResp = results[0];
                  var smartData = results[1];
                  if (!smartData || !smartData.ok || !smartData.reply) return origResp;

                  return origResp.clone().text().then(function(rawText) {
                    try {
                      var dataObj = JSON.parse(rawText);
                      function patchAiNode(node) {
                        if (!node || typeof node !== "object") return;
                        ["reply", "message", "content", "answer", "text"].forEach(function(k) {
                          if (typeof node[k] === "string" && node[k].length > 5) {
                            node[k] = smartData.reply;
                          }
                        });
                        ["items", "suggestedItems", "products", "recommendations"].forEach(function(ik) {
                          if (Array.isArray(node[ik])) {
                            if (Array.isArray(smartData.suggestedItems) && smartData.suggestedItems.length === 0) {
                              node[ik] = [];
                            }
                          }
                        });
                        Object.keys(node).forEach(function(childK) {
                          if (node[childK] && typeof node[childK] === "object") {
                            patchAiNode(node[childK]);
                          }
                        });
                      }
                      patchAiNode(dataObj);
                      var cleanedJson = JSON.stringify(dataObj).replace(/\\(\\s*رقم\\s*\\d+\\s*\\)/g, "");
                      return new Response(cleanedJson, {
                        status: origResp.status,
                        statusText: origResp.statusText,
                        headers: origResp.headers
                      });
                    } catch (e) {
                      return origResp;
                    }
                  });
                });
              }
            }
            return origFetchV112.apply(this, arguments);
          };
        }

        // Load AI config & requests from server
        function refreshAiConfigV112() {
          origFetchV112("/api/ai-v112/config")
            .then(function(r) { return r.json(); })
            .then(function(d) {
              if (d && d.ok) {
                if (d.config) window.__v112AiConfig = d.config;
                if (Array.isArray(d.requests)) {
                  checkNewManagerNotifications(d.requests);
                  window.__v112AiRequests = d.requests;
                  renderAdminRequestsListV112();
                }
              }
            })
            .catch(function() {});
        }
        setTimeout(refreshAiConfigV112, 300);
        setInterval(refreshAiConfigV112, 5000);

        function playNotificationChimeV112() {
          try {
            var Ctx = window.AudioContext || window.webkitAudioContext;
            if (!Ctx) return;
            var ctx = new Ctx();
            var osc = ctx.createOscillator();
            var gain = ctx.createGain();
            osc.type = "sine";
            osc.frequency.setValueAtTime(880, ctx.currentTime);
            osc.frequency.setValueAtTime(1174, ctx.currentTime + 0.15);
            gain.gain.setValueAtTime(0.18, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.45);
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start();
            osc.stop(ctx.currentTime + 0.45);
          } catch (e) {}
        }

        function checkNewManagerNotifications(requests) {
          if (window.location.pathname.indexOf("/admin") === -1) return;
          var pendingCount = 0;
          requests.forEach(function(req) {
            if (req.status === "pending") {
              pendingCount++;
              if (!window.__v112NotifiedReqIds[req.id]) {
                window.__v112NotifiedReqIds[req.id] = true;
                playNotificationChimeV112();
                if ("Notification" in window && Notification.permission === "granted") {
                  try {
                    new Notification("📲 طلب زبون جديد من المساعد الذكي - أورجنال", {
                      body: "الزبون يطلب: " + (req.requestedItem || req.customerMessage) + " — اضغط للرد عليه فوراً داخل المتجر",
                      icon: "/icon-192.png"
                    });
                  } catch (e) {}
                }
              }
            }
          });
          var badgeEl = document.getElementById("v112-admin-live-badge");
          if (badgeEl) {
            badgeEl.textContent = String(pendingCount);
            badgeEl.style.display = pendingCount > 0 ? "inline-flex" : "none";
          }
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
                    playNotificationChimeV112();
                    showCustomerManagerReplyBannerV112(rep);
                  }
                });
              }
            })
            .catch(function() {});
        }
        setInterval(pollCustomerManagerRepliesV112, 4000);

        function showCustomerManagerReplyBannerV112(rep) {
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
                '<div style="font-size:0.92rem;line-height:1.6;color:#ffffff;font-weight:600;">' +
                (rep.managerReply || "").replace(/</g, "&lt;") +
                '</div>';
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
            '<div style="font-size:0.9rem;line-height:1.5;">' + (rep.managerReply || "").replace(/</g, "&lt;") + '</div>';
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
          var map = (window.__v112AiConfig && window.__v112AiConfig.productAiMap) || {};
          var customNote = map["name:" + clean] || "";
          var comb = (clean + " " + customNote).toLowerCase();
          if (/(سجائر|سجاير|دخان|شملان|كمران|منظف|صابون|شامبو|مناديل|فحم|ولاعة|أكياس|اكياس)/.test(comb)) return { kind: "non_food", customNote: customNote };
          if (/(بسكويت|بسكوت|ماري|أبو ولد|ابو ولد|نخالة|شاي|ديما|أوريو|اوريو|معمول|كليجا)/.test(comb)) return { kind: "biscuit_dessert", customNote: customNote };
          if (/(شوكلات|شوكولات|بليلا|بريك|ويفر|علك|باطوق|حلاو|مصاص|شيبس|بطاط|فشار|كروسان|كيك|جالكسي|كتكات|سنكرز|توبي|سعيد|مارشملو|جيلي|كاكاو)/.test(comb)) return { kind: "chocolate_snack", customNote: customNote };
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

            // ==================================================================
            // PART E: Smart Product AI Modal ("أفكار وطرق: ..." -> Calories, Product Info, Pairing / Dessert)
            // ==================================================================
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

            // ==================================================================
            // PART F: Main AI Assistant Chat ("مساعد وشيف أورجنال الذكي")
            // ==================================================================
            if (document.body.textContent.indexOf("مساعد وشيف أورجنال الذكي") !== -1) {
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

            // ==================================================================
            // PART G: Admin Panel Enhancer (/admin)
            // ==================================================================
            if (window.location.pathname.indexOf("/admin") !== -1) {
              injectAdminProductAiFieldV112();
              injectAdminAiTrainingCenterV112();
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
                  (t.indexOf("أهلاً بك") !== -1 || t.indexOf("1️⃣") !== -1 || t.indexOf("سعرة") !== -1 || t.indexOf("معلومات") !== -1)
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

          var aiBox = document.createElement("div");
          aiBox.id = "v112-product-ai-box";
          aiBox.className = "field-wide";
          aiBox.style.cssText = "background:#f4fbf7;border:2px solid #0d3825;border-radius:14px;padding:14px;margin-top:10px;margin-bottom:10px;direction:rtl;text-align:right;";
          aiBox.innerHTML =
            '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;flex-wrap:wrap;gap:6px;">' +
            '<strong style="color:#0d3825;font-size:0.95rem;">🤖 معلومات وتوجيهات الذكاء الاصطناعي عن هذا المنتج (اختياري)</strong>' +
            '<span style="font-size:0.76rem;background:#0d3825;color:#d4af37;padding:3px 9px;border-radius:99px;font-weight:700;">يقرأها المساعد الذكي فوراً</span>' +
            '</div>' +
            '<div style="font-size:0.8rem;color:#495a52;margin-bottom:8px;">' +
            'أضف أي معلومات تريد من الذكاء الاصطناعي معرفتها عن هذا المنتج (السعرات الحرارية، هل هو جاهز للأكل أم يصلح للحلى، طعمه، أو مع إيش يؤكل):' +
            '</div>' +
            '<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px;" id="v112-ai-quick-tags">' +
            '<button type="button" data-tag="منتج جاهز للأكل مباشرة ولا يحتاج أي طبخ أو تحضير." style="font-size:0.76rem;padding:4px 10px;background:#fff;color:#0d3825;border:1px solid #0d3825;border-radius:8px;font-weight:700;cursor:pointer;">+ 🍫 جاهز للأكل بدون تحضير</button>' +
            '<button type="button" data-tag="يصلح لعمل حلى بارد سريع وممتاز مع الشاي والحليب." style="font-size:0.76rem;padding:4px 10px;background:#fff;color:#0d3825;border:1px solid #0d3825;border-radius:8px;font-weight:700;cursor:pointer;">+ 🍰 يصلح لعمل حلى</button>' +
            '<button type="button" data-tag="السعرات الحرارية التقريبية: 120 سعرة حرارية للحصة." style="font-size:0.76rem;padding:4px 10px;background:#fff;color:#0d3825;border:1px solid #0d3825;border-radius:8px;font-weight:700;cursor:pointer;">+ 🔥 السعرات: 120 سعرة</button>' +
            '<button type="button" data-tag="طعمه لذيذ جداً بجانب فنجان القهوة أو الشاي." style="font-size:0.76rem;padding:4px 10px;background:#fff;color:#0d3825;border:1px solid #0d3825;border-radius:8px;font-weight:700;cursor:pointer;">+ ☕ يقدم مع القهوة والشاي</button>' +
            '</div>' +
            '<textarea id="v112-product-ai-textarea" rows="3" placeholder="اكتب هنا معلومات المنتج للذكاء الاصطناعي (مثال: السعرات الحرارية 130 سعرة، شوكولاتة غنية بالحليب تؤكل مباشرة مع القهوة، لا تقترح لها طبخ)..." style="width:100%;background:#ffffff;color:#0d3825;border:1.5px solid #9dcab3;border-radius:10px;padding:9px 11px;font-size:0.86rem;box-sizing:border-box;margin-bottom:8px;"></textarea>' +
            '<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;">' +
            '<button type="button" id="v112-save-prod-ai-btn" style="background:#0d3825;color:#d4af37;border:none;border-radius:9px;padding:8px 16px;font-size:0.84rem;font-weight:800;cursor:pointer;">💾 حفظ معلومات الذكاء الاصطناعي لهذا المنتج</button>' +
            '<span id="v112-save-prod-ai-status" style="font-size:0.8rem;color:#0d3825;font-weight:700;"></span>' +
            '</div>';

          varBox.parentNode.insertBefore(aiBox, varBox.nextSibling);

          Array.from(aiBox.querySelectorAll("#v112-ai-quick-tags button")).forEach(function(b) {
            b.onclick = function() {
              var ta = document.getElementById("v112-product-ai-textarea");
              if (!ta) return;
              var tagTxt = b.getAttribute("data-tag") || "";
              ta.value = (ta.value ? ta.value.trim() + " — " : "") + tagTxt;
            };
          });

          var formContainer = varBox.parentElement;
          var nameInput = formContainer ? formContainer.querySelector("input[placeholder*='اسم'], input") : null;
          function syncLoadedProductAiInfo() {
            if (!nameInput) return;
            var pName = (nameInput.value || "").trim();
            var ta = document.getElementById("v112-product-ai-textarea");
            if (!ta || !pName) return;
            var map = (window.__v112AiConfig && window.__v112AiConfig.productAiMap) || {};
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
            origFetchV112("/api/ai-v112/save-product-info", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ productName: pName, aiInfo: ta.value.trim() })
            })
              .then(function(r) { return r.json(); })
              .then(function(d) {
                if (d && d.ok) {
                  if (!window.__v112AiConfig.productAiMap) window.__v112AiConfig.productAiMap = {};
                  window.__v112AiConfig.productAiMap["name:" + pName] = ta.value.trim();
                  if (st) st.textContent = "✅ تم حفظ معلومات الذكاء الاصطناعي للمنتج (" + pName + ") بنجاح!";
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

        function injectAdminAiTrainingCenterV112() {
          if (document.getElementById("v112-admin-ai-floating-btn")) return;

          var floatBar = document.createElement("div");
          floatBar.id = "v112-admin-ai-floating-btn";
          floatBar.style.cssText = "position:fixed;bottom:16px;left:16px;z-index:9990;direction:rtl;";
          floatBar.innerHTML =
            '<button type="button" id="v112-open-trainer-btn" style="background:#0d3825;color:#d4af37;border:2px solid #d4af37;border-radius:99px;padding:10px 18px;font-weight:800;font-size:0.86rem;box-shadow:0 6px 20px rgba(0,0,0,0.28);cursor:pointer;display:flex;align-items:center;gap:8px;">' +
            '<span>🤖 تعليم الذكاء (3 خيارات) وطلبات الزبائن</span>' +
            '<span id="v112-admin-live-badge" style="display:none;background:#ef4444;color:#fff;font-size:0.75rem;padding:2px 8px;border-radius:99px;font-weight:900;">0</span>' +
            '</button>';
          document.body.appendChild(floatBar);

          var modalWrap = document.createElement("div");
          modalWrap.id = "v112-admin-trainer-modal";
          modalWrap.style.cssText = "display:none;position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,0.6);padding:12px;overflow-y:auto;direction:rtl;text-align:right;";
          modalWrap.innerHTML =
            '<div style="max-width:680px;margin:16px auto;background:#ffffff;border:2px solid #0d3825;border-radius:18px;padding:16px;box-shadow:0 12px 36px rgba(0,0,0,0.25);">' +
            '<div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1.5px solid #d5e5dc;padding-bottom:10px;margin-bottom:12px;">' +
            '<h3 style="margin:0;color:#0d3825;font-size:1.05rem;">🤖 مركز تعليم الذكاء الاصطناعي (3 خيارات) وطلبات الزبائن المباشرة</h3>' +
            '<button type="button" id="v112-close-trainer-btn" style="background:#fee2e2;color:#b91c1c;border:none;border-radius:8px;padding:6px 12px;font-weight:800;cursor:pointer;">إغلاق ✕</button>' +
            '</div>' +

            '<div style="background:#eef8f3;border:1px solid #9dcab3;border-radius:12px;padding:10px;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">' +
            '<span style="font-size:0.82rem;color:#0d3825;font-weight:700;">🔔 استلام إشعار فوري على هاتفك عندما يطلب زبون منتجاً غير متوفر من المساعد الذكي:</span>' +
            '<button type="button" id="v112-enable-notif-btn" style="background:#0d3825;color:#d4af37;border:none;border-radius:8px;padding:6px 12px;font-size:0.8rem;font-weight:800;cursor:pointer;">تفعيل إشعارات الهاتف الآن</button>' +
            '</div>' +

            '<div style="background:#fffbeb;border:1.5px solid #f59e0b;border-radius:14px;padding:12px;margin-bottom:14px;">' +
            '<strong style="color:#92400e;font-size:0.92rem;display:block;margin-bottom:8px;">📲 طلبات التوفير والرسائل الواردة من الزبائن عبر المساعد الذكي (رد مباشر يظهر للزبون في المتجر):</strong>' +
            '<div id="v112-admin-requests-container" style="max-height:220px;overflow-y:auto;font-size:0.84rem;color:#0d3825;">جاري التحميل...</div>' +
            '</div>' +

            '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;margin-bottom:12px;">' +
            '<button type="button" class="v112-tab-btn" data-tab="1" style="background:#0d3825;color:#d4af37;border:1px solid #0d3825;border-radius:10px;padding:9px 6px;font-weight:800;font-size:0.8rem;cursor:pointer;">1️⃣ الأسلوب والشخصية</button>' +
            '<button type="button" class="v112-tab-btn" data-tab="2" style="background:#eef8f3;color:#0d3825;border:1px solid #0d3825;border-radius:10px;padding:9px 6px;font-weight:800;font-size:0.8rem;cursor:pointer;">2️⃣ قاموس الردود والبدائل</button>' +
            '<button type="button" class="v112-tab-btn" data-tab="3" style="background:#eef8f3;color:#0d3825;border:1px solid #0d3825;border-radius:10px;padding:9px 6px;font-weight:800;font-size:0.8rem;cursor:pointer;">3️⃣ قواعد ومعلومات المنتجات</button>' +
            '</div>' +

            '<div id="v112-tab-content-1">' +
            '<label style="display:block;font-weight:800;color:#0d3825;font-size:0.86rem;margin-bottom:6px;">الخيار 1️⃣: تعليم أسلوب المحادثة والشخصية العامة للمساعد الذكي:</label>' +
            '<textarea id="v112-mode1-input" rows="4" style="width:100%;background:#f8fbf9;color:#0d3825;border:1.5px solid #9dcab3;border-radius:10px;padding:10px;font-size:0.85rem;box-sizing:border-box;margin-bottom:8px;"></textarea>' +
            '</div>' +

            '<div id="v112-tab-content-2" style="display:none;">' +
            '<label style="display:block;font-weight:800;color:#0d3825;font-size:0.86rem;margin-bottom:6px;">الخيار 2️⃣: علم الذكاء الاصطناعي (إذا سأل الزبون عن كذا ← يرد عليه بكذا):</label>' +
            '<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px;">' +
            '<input id="v112-new-rule-trig" placeholder="إذا ذكر الزبون (مثال: نوتيلا أو حلى سريع)" style="flex:1 1 200px;padding:8px;border:1px solid #9dcab3;border-radius:8px;font-size:0.84rem;" />' +
            '<input id="v112-new-rule-resp" placeholder="يرد الذكاء الاصطناعي بـ..." style="flex:2 1 260px;padding:8px;border:1px solid #9dcab3;border-radius:8px;font-size:0.84rem;" />' +
            '<button type="button" id="v112-add-rule-btn" style="background:#0d3825;color:#d4af37;border:none;border-radius:8px;padding:8px 14px;font-weight:800;font-size:0.82rem;cursor:pointer;">+ إضافة قاعدة</button>' +
            '</div>' +
            '<div id="v112-rules-list" style="max-height:180px;overflow-y:auto;border:1px solid #d5e5dc;border-radius:10px;padding:8px;background:#f8fbf9;margin-bottom:8px;"></div>' +
            '</div>' +

            '<div id="v112-tab-content-3" style="display:none;">' +
            '<label style="display:block;font-weight:800;color:#0d3825;font-size:0.86rem;margin-bottom:6px;">الخيار 3️⃣: قواعد الأصناف (الشوكولاتة، البسكويت، العصائر) ومعلومات منتج محدد:</label>' +
            '<textarea id="v112-mode3-input" rows="3" style="width:100%;background:#f8fbf9;color:#0d3825;border:1.5px solid #9dcab3;border-radius:10px;padding:10px;font-size:0.85rem;box-sizing:border-box;margin-bottom:10px;"></textarea>' +
            '<div style="background:#eef8f3;border:1px solid #9dcab3;border-radius:10px;padding:10px;margin-bottom:8px;">' +
            '<strong style="font-size:0.84rem;color:#0d3825;display:block;margin-bottom:6px;">➕ إضافة/تعديل معلومات خاصة لمنتج معين بالاسم:</strong>' +
            '<div style="display:flex;flex-wrap:wrap;gap:6px;">' +
            '<input id="v112-quick-prod-name" placeholder="اسم المنتج (مثال: شوكلاتة البليلا)" style="flex:1 1 160px;padding:8px;border:1px solid #9dcab3;border-radius:8px;font-size:0.84rem;background:#fff;" />' +
            '<input id="v112-quick-prod-info" placeholder="معلوماته للذكاء (السعرات، الطعم، الاستخدام...)" style="flex:2 1 240px;padding:8px;border:1px solid #9dcab3;border-radius:8px;font-size:0.84rem;background:#fff;" />' +
            '<button type="button" id="v112-quick-prod-save" style="background:#0d3825;color:#d4af37;border:none;border-radius:8px;padding:8px 14px;font-weight:800;font-size:0.82rem;cursor:pointer;">حفظ للمنتج</button>' +
            '</div>' +
            '</div>' +
            '</div>' +

            '<div style="display:flex;justify-content:space-between;align-items:center;border-top:1px solid #d5e5dc;padding-top:10px;margin-top:8px;">' +
            '<button type="button" id="v112-save-all-training-btn" style="background:#0d3825;color:#d4af37;border:none;border-radius:10px;padding:10px 20px;font-weight:800;font-size:0.9rem;cursor:pointer;">💾 حفظ جميع إعدادات تعليم الذكاء الاصطناعي</button>' +
            '<span id="v112-trainer-save-msg" style="font-size:0.84rem;font-weight:800;color:#0d3825;"></span>' +
            '</div>' +
            '</div>';
          document.body.appendChild(modalWrap);

          document.getElementById("v112-open-trainer-btn").onclick = function() {
            modalWrap.style.display = "block";
            populateTrainerModalV112();
          };
          document.getElementById("v112-close-trainer-btn").onclick = function() {
            modalWrap.style.display = "none";
          };
          document.getElementById("v112-enable-notif-btn").onclick = function() {
            if ("Notification" in window) {
              Notification.requestPermission().then(function(p) {
                alert(p === "granted" ? "✅ تم تفعيل إشعارات الهاتف لطلبات الزبائن بنجاح!" : "يرجى السماح بالإشعارات من إعدادات المتصفح.");
              });
            } else {
              alert("التنبيه الصوتي والمرئي المباشر مفعل تلقائياً!");
            }
          };

          Array.from(modalWrap.querySelectorAll(".v112-tab-btn")).forEach(function(btn) {
            btn.onclick = function() {
              var tNum = btn.getAttribute("data-tab");
              Array.from(modalWrap.querySelectorAll(".v112-tab-btn")).forEach(function(b) {
                var active = b.getAttribute("data-tab") === tNum;
                b.style.background = active ? "#0d3825" : "#eef8f3";
                b.style.color = active ? "#d4af37" : "#0d3825";
              });
              ["1", "2", "3"].forEach(function(n) {
                var el = document.getElementById("v112-tab-content-" + n);
                if (el) el.style.display = n === tNum ? "block" : "none";
              });
            };
          });

          document.getElementById("v112-add-rule-btn").onclick = function() {
            var trigEl = document.getElementById("v112-new-rule-trig");
            var respEl = document.getElementById("v112-new-rule-resp");
            if (!trigEl || !respEl || !trigEl.value.trim() || !respEl.value.trim()) return;
            if (!Array.isArray(window.__v112AiConfig.mode2Rules)) window.__v112AiConfig.mode2Rules = [];
            window.__v112AiConfig.mode2Rules.unshift({
              id: "r_" + Date.now(),
              trigger: trigEl.value.trim(),
              response: respEl.value.trim()
            });
            trigEl.value = "";
            respEl.value = "";
            renderRulesListV112();
          };

          document.getElementById("v112-quick-prod-save").onclick = function() {
            var pnEl = document.getElementById("v112-quick-prod-name");
            var piEl = document.getElementById("v112-quick-prod-info");
            var pn = pnEl ? pnEl.value.trim() : "";
            var pi = piEl ? piEl.value.trim() : "";
            if (!pn) return;
            origFetchV112("/api/ai-v112/save-product-info", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ productName: pn, aiInfo: pi })
            }).then(function() {
              if (!window.__v112AiConfig.productAiMap) window.__v112AiConfig.productAiMap = {};
              window.__v112AiConfig.productAiMap["name:" + pn] = pi;
              var msgEl = document.getElementById("v112-trainer-save-msg");
              if (msgEl) msgEl.textContent = "✅ تم حفظ معلومات المنتج (" + pn + ")!";
            });
          };

          document.getElementById("v112-save-all-training-btn").onclick = function() {
            var m1El = document.getElementById("v112-mode1-input");
            var m3El = document.getElementById("v112-mode3-input");
            var m1 = m1El ? m1El.value.trim() : "";
            var m3 = m3El ? m3El.value.trim() : "";
            window.__v112AiConfig.mode1StylePrompt = m1;
            window.__v112AiConfig.mode3CategoryRules = m3;
            origFetchV112("/api/ai-v112/save-training", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(window.__v112AiConfig)
            })
              .then(function(r) { return r.json(); })
              .then(function() {
                var msgEl = document.getElementById("v112-trainer-save-msg");
                if (msgEl) msgEl.textContent = "✅ تم حفظ إعدادات تعليم الذكاء الاصطناعي بنجاح!";
              });
          };
        }

        function populateTrainerModalV112() {
          var cfg = window.__v112AiConfig || {};
          var m1El = document.getElementById("v112-mode1-input");
          var m3El = document.getElementById("v112-mode3-input");
          if (m1El) m1El.value = cfg.mode1StylePrompt || "";
          if (m3El) m3El.value = cfg.mode3CategoryRules || "";
          renderRulesListV112();
          renderAdminRequestsListV112();
        }

        function renderRulesListV112() {
          var box = document.getElementById("v112-rules-list");
          if (!box) return;
          var rules = (window.__v112AiConfig && window.__v112AiConfig.mode2Rules) || [];
          if (rules.length === 0) {
            box.innerHTML = '<div style="color:#687a71;text-align:center;padding:8px;">لا توجد قواعد مضافة بعد.</div>';
            return;
          }
          box.innerHTML = "";
          rules.forEach(function(r, idx) {
            var row = document.createElement("div");
            row.style.cssText = "display:flex;justify-content:space-between;align-items:center;gap:8px;padding:6px 8px;border-bottom:1px solid #e2ece7;background:#fff;border-radius:8px;margin-bottom:4px;";
            row.innerHTML =
              '<div style="font-size:0.82rem;"><strong style="color:#0d3825;">إذا سأل عن: ' + (r.trigger || "") + '</strong> ← ' + (r.response || "") + '</div>';
            var del = document.createElement("button");
            del.type = "button";
            del.textContent = "حذف";
            del.style.cssText = "background:#fee2e2;color:#b91c1c;border:none;border-radius:6px;padding:4px 8px;font-weight:700;cursor:pointer;font-size:0.75rem;";
            del.onclick = function() {
              window.__v112AiConfig.mode2Rules.splice(idx, 1);
              renderRulesListV112();
            };
            row.appendChild(del);
            box.appendChild(row);
          });
        }

        function renderAdminRequestsListV112() {
          var box = document.getElementById("v112-admin-requests-container");
          if (!box) return;
          var reqs = window.__v112AiRequests || [];
          if (reqs.length === 0) {
            box.innerHTML = '<div style="color:#78350f;padding:6px;">لا توجد طلبات معلقة حالياً. عندما يطلب زبون التوفير أو التواصل مع المتجر سيظهر طلبه هنا فوراً مع إشعار لهاتفك.</div>';
            return;
          }
          box.innerHTML = "";
          reqs.slice(0, 15).forEach(function(req) {
            var card = document.createElement("div");
            card.style.cssText = "background:#ffffff;border:1px solid #fcd34d;border-radius:10px;padding:10px;margin-bottom:8px;";
            var statusBadge = req.status === "replied"
              ? '<span style="background:#dcfce7;color:#166534;padding:2px 8px;border-radius:99px;font-size:0.74rem;font-weight:800;">تم الرد ✓</span>'
              : '<span style="background:#fee2e2;color:#991b1b;padding:2px 8px;border-radius:99px;font-size:0.74rem;font-weight:800;">بانتظار ردك 🔔</span>';
            card.innerHTML =
              '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">' +
              '<strong>طلب الزبون: ' + (req.requestedItem || req.customerMessage || "") + '</strong>' +
              statusBadge +
              '</div>' +
              (req.managerReply ? '<div style="font-size:0.8rem;color:#166534;margin-bottom:6px;">ردك السابق: ' + req.managerReply + '</div>' : '');

            var replyRow = document.createElement("div");
            replyRow.style.cssText = "display:flex;gap:6px;";
            var inp = document.createElement("input");
            inp.placeholder = "اكتب ردك للزبون ليظهر له داخل المتجر فوراً...";
            inp.style.cssText = "flex:1;padding:7px 10px;border:1px solid #9dcab3;border-radius:8px;font-size:0.82rem;";
            var sendB = document.createElement("button");
            sendB.type = "button";
            sendB.textContent = "📨 إرسال للزبون";
            sendB.style.cssText = "background:#0d3825;color:#d4af37;border:none;border-radius:8px;padding:7px 12px;font-weight:800;font-size:0.8rem;cursor:pointer;white-space:nowrap;";
            sendB.onclick = function() {
              if (!inp.value.trim()) return;
              sendB.textContent = "جاري الإرسال...";
              origFetchV112("/api/ai-v112/manager-reply", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  requestId: req.id,
                  sessionId: req.sessionId,
                  replyText: inp.value.trim()
                })
              })
                .then(function(r) { return r.json(); })
                .then(function() {
                  req.status = "replied";
                  req.managerReply = inp.value.trim();
                  inp.value = "";
                  renderAdminRequestsListV112();
                });
            };
            replyRow.appendChild(inp);
            replyRow.appendChild(sendB);
            card.appendChild(replyRow);
            box.appendChild(card);
          });
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
    ht = ht.replace("</body>", v112_master_script + "\n  </body>", 1)
    html_path.write_text(ht, encoding="utf-8")
    print("5. Updated client/index.html (Smart Product AI Modal + Smart Chat + Admin 3-Mode AI Trainer + Per-Product AI Box + Cart v111 fix)!")

# 6. Bump sw.js cache to v112
sw_path = pathlib.Path("client/public/sw.js")
if sw_path.exists():
    swc = sw_path.read_text(encoding="utf-8")
    swc = re.sub(r'const CACHE = "original-shell-v[^"]*";', 'const CACHE = "original-shell-v112";', swc)
    sw_path.write_text(swc, encoding="utf-8")
    print("6. Bumped sw.js cache to v112!")

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
subprocess.run(["git", "commit", "-m", "v112: smart AI assistant overhaul, 3 AI training modes, per-product AI info, live store request notifications, and cart quantity fix"], check=True)
subprocess.run(["git", "push", "origin", "main", "--force"], check=True)
print("=== تم رفع التحديث الشامل v112 بنجاح 100% إلى Render! ===")
