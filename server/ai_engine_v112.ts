import { getDb } from "./db";
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
    .replace(/\(\s*رقم\s*\d+\s*\)/g, "")
    .replace(/\s*\([^()]*\)\s*$/g, "")
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
  const customNoteBlock = customAi ? "\n💡 معلومة خاصة عن المنتج: " + customAi : "";

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
        "1️⃣ السعرات التقريبية: تحتوي الحصة الواحدة على حوالي 110 إلى 160 سعرة حرارية تمنح الجسم طاقة سريعة ونشاطاً فورياً.\n" +
        "2️⃣ القيمة الغذائية: غني بالكاكاو والسكريات البسيطة التي تحسن المزاج وترفع التركيز.\n" +
        "3️⃣ نصيحة: تناوله باعتدال كسناك لذيذ في وسط اليوم أو مع فنجان قهوة." +
        customNoteBlock;
    } else if (customTopic && (customTopic.includes("يؤكل") || customTopic.includes("يُقدم") || customTopic.includes("قهوة"))) {
      text =
        "☕ أفضل طرق الاستمتاع بـ «" + cleanName + "»:\n" +
        "1️⃣ مع القهوة أو الشاي: طعمه رائع جداً بجانب فنجان قهوة أو كوب شاي دافئ.\n" +
        "2️⃣ مع الحليب البارد أو الدافئ: وجبة خفيفة محببة للأطفال والكبار.\n" +
        "3️⃣ جاهز للأكل مباشرة: لا يحتاج إلى أي تحضير أو إضافات." +
        customNoteBlock;
    } else {
      text =
        "✨ معلومات المنتج والقيمة الغذائية لـ «" + cleanName + "»" + (priceStr ? " (متوفر بسعر " + priceStr + ")" : "") + ":\n" +
        "1️⃣ نبذة عن المنتج: سناك حالي جاهز للأكل مباشرة بطعم غني ولذيذ، لا يحتاج إلى أي طبخ أو تحضير.\n" +
        "2️⃣ السعرات الحرارية التقريبية: حوالي 120 – 150 سعرة حرارية للحصة الواحدة، ممتاز لتجديد الطاقة والنشاط.\n" +
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
        "🔥 السعرات الحرارية والقيمة الغذائية لـ «" + cleanName + "»:\n" +
        "1️⃣ السعرات الحرارية: تحتوي الحبة الواحدة على حوالي 25 – 35 سعرة حرارية فقط (حوالي 140 سعرة لكل 4 حبات).\n" +
        "2️⃣ القيمة الغذائية: خفيف على المعدة ويمد الجسم بالكربوهيدرات المناسبة لفطور الصباح أو سناك العصر.\n" +
        "3️⃣ الاستخدام: قوامه الهش يجعله ممتازاً لعمل الحلويات الباردة أو التغميس مع الشاي والحليب." +
        customNoteBlock;
    } else {
      text =
        "✨ معلومات وأفكار جميلة لـ «" + cleanName + "»" + (priceStr ? " (متوفر بسعر " + priceStr + ")" : "") + ":\n" +
        "1️⃣ حلى البسكويت البارد السريع: غمس البسكويت سريعاً في الحليب ورتبه في طبقات مع القشطة والكاكاو أو الكريمة، وضعه في الثلاجة نصف ساعة لتحصل على ألذ حلى بيتي!\n" +
        "2️⃣ السعرات الحرارية: خفيف ومناسب جداً، الحبة الواحدة حوالي 25 – 35 سعرة حرارية.\n" +
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
      "✨ معلومات وقيمة غذائية لـ «" + cleanName + "»" + (priceStr ? " (متوفر بسعر " + priceStr + ")" : "") + ":\n" +
      "1️⃣ القيمة الغذائية والسعرات: يمنح ترطيباً وانتعاشاً فورياً، وتحتوي العبوة على حوالي 90 – 130 سعرة حرارية.\n" +
      "2️⃣ أفضل طريقة تقديم: يُقدم بارداً جداً من الثلاجة أو مع مكعبات الثلج لانتعاش مضاعف.\n" +
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
      "✨ معلومات المنتج «" + cleanName + "»" + (priceStr ? " (السعر: " + priceStr + ")" : "") + ":\n" +
      "1️⃣ منتج أصلي متوفر في متجر أورجنال بجودة مضمونة.\n" +
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
    "✨ معلومات واستخدامات «" + cleanName + "»" + (priceStr ? " (متوفر بسعر " + priceStr + ")" : "") + ":\n" +
    "1️⃣ في المطبخ والوجبات: مكون أساسي ممتاز لتحضير وجبات بيتية شهية وسريعة.\n" +
    "2️⃣ القيمة الغذائية: غني بالعناصر الغذائية المفيدة للمائدة اليومية.\n" +
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
      reply: "أبشر من عيوني يا غالي! 📲 كلمت إدارة المتجر الآن وأرسلت إشعار فوري لهاتف المدير بطلبك («" + requestedTopic + "»).\nأول ما يرد المدير سيظهر رده هنا أمامك في المحادثة مباشرةً!",
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
        reply: String(rule.response || "").replace(/\(\s*رقم\s*\d+\s*\)/g, ""),
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
    const words = pName.split(/\s+/).filter(w => w.length >= 4);
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
      "فهمتك يا غالي! بخصوص «" + pName + "» (متوفر عندنا بسعر " + pPrice.toLocaleString("en-US") + " ر.ي):\n" +
      modalInfo.content.replace(/^✨[^\n]*\n/, "");

    if (companions.length > 0) {
      const compNames = companions.map(c => "«" + cleanProductNameV112(c.name) + "» (" + Math.round(Number(c.price)).toLocaleString("en-US") + " ر.ي)").join(" أو ");
      friendlyReply += "\n\nوبما إنك تحب هذا النوع، عندنا أيضاً في المتجر " + compNames + " إذا تحب تجربه معه!";
    }

    return {
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
      quickActions: modalInfo.chips.slice(0, 3),
      canContactStore: false
    };
  }

  // 7. Product not directly matched -> offer genuine partial matches (if any) + offer to contact store manager!
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

  const friendReply =
    "فهمتك يا غالي، أنت تريد «" + cleanWanted + "».. حلو حلو! 👌\n" +
    altSentence +
    "وإذا تريد نفس «" + cleanWanted + "» بالضبط، أقدر أتواصل لك الحين مع إدارة المتجر وأسألهم إذا متوفر عندهم أو يوفرونه لك فوراً!\n" +
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
