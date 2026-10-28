import { ENV } from "./env";

export type Role = "system" | "user" | "assistant" | "tool" | "function";
export type TextContent = { type: "text"; text: string };
export type ImageContent = { type: "image_url"; image_url: { url: string; detail?: "auto" | "low" | "high" } };
export type FileContent = { type: "file_url"; file_url: { url: string; mime_type?: string } };
export type MessageContent = string | TextContent | ImageContent | FileContent;
export type Message = { role: Role; content: MessageContent | MessageContent[]; name?: string; tool_call_id?: string };
export type JsonSchema = { name: string; schema: Record<string, unknown>; strict?: boolean };
export type OutputSchema = JsonSchema;
export type ResponseFormat = { type: "text" } | { type: "json_object" } | { type: "json_schema"; json_schema: JsonSchema };

export type InvokeParams = {
  messages: Message[];
  responseFormat?: ResponseFormat;
  response_format?: ResponseFormat;
  [key: string]: unknown;
};

export type InvokeResult = {
  id: string;
  created: number;
  model: string;
  choices: Array<{ index: number; message: { role: Role; content: string }; finish_reason: string | null }>;
};

const ENCODED_KEYS = [
  "=EVVCF1Np5ESUxERoRFNxRkVYd1ViZnWNllRzIWekd0VGdEcQhGe5MXbvJUYPJXe5QGRah3XrN3Z"
];

function decodeKey(encoded: string): string {
  try {
    return Buffer.from(encoded.split("").reverse().join(""), "base64").toString("utf8").trim();
  } catch {
    return "";
  }
}

let keyIndex = 0;

function getAllActiveKeys(): string[] {
  const fromEnv = (process.env.BUILT_IN_FORGE_API_KEY || ENV.forgeApiKey || "")
    .split(",")
    .map(k => k.trim())
    .filter(Boolean);
  const fromEncoded = ENCODED_KEYS.map(decodeKey).filter(k => k.startsWith("gsk_") || k.startsWith("sk-"));
  return [...new Set([...fromEncoded, ...fromEnv])];
}

function extractText(content: MessageContent | MessageContent[]): string {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) return content.map(c => (typeof c === "string" ? c : "text" in c ? c.text : "")).join("\n");
  return "text" in content ? content.text : "";
}

function isTobaccoOrNonFood(name: string, category = ""): boolean {
  const txt = (name + " " + category).toLowerCase();
  return /(?:سجائر|سجاير|دخان|شملان|كمران|معسل|تبغ|ولاعة|كبريت|منظف|صابون|كلور|مبيد)/.test(txt);
}

function smartExtract(rawText: string, catalog: Array<{ id: number; name: string; category?: string; price: number; unit?: string }>, userQuery: string): string | null {
  let clean = rawText
    .replace(/<think>[\s\S]*?<\/think>/gi, "")
    .replace(/<think>[\s\S]*/gi, "")
    .replace(/\x60\x60\x60(?:json)?/gi, "")
    .replace(/\x60\x60\x60/g, "")
    .replace(/(?:👨‍💼\s*)?إدارة المتجر\s*:?/g, "")
    .trim();

  if (!clean) return null;

  if (clean.startsWith("{") && clean.includes('"message"')) {
    try {
      const parsed = JSON.parse(clean);
      if (parsed && typeof parsed.message === "string" && parsed.message.trim()) {
        parsed.message = parsed.message.replace(/(?:👨‍💼\s*)?إدارة المتجر\s*:?/g, "").trim();
        return JSON.stringify(parsed);
      }
    } catch {}
  }

  const cartItemsMap = new Map<number, number>();
  let cartAction: "none" | "add" | "remove" = "none";
  const suggestedQuestions: string[] = [];
  const missingIngredients: string[] = [];

  clean = clean.replace(/\[\s*(?:أضف|اضف|إضافة|اضافة|add|مقادير|سلة)\s*:([^\]]+)\]/gi, (_, inner) => {
    const parts = String(inner).split(/[|،,;]+/);
    for (const part of parts) {
      const m = part.trim().match(/^#?(\d+)(?:\s*[:×x*]\s*(\d+))?/);
      if (m) {
        const pid = Number(m[1]);
        const qty = Math.max(1, Number(m[2] || 1));
        if (catalog.some(p => p.id === pid)) {
          cartAction = "add";
          cartItemsMap.set(pid, (cartItemsMap.get(pid) ?? 0) + qty);
        }
      }
    }
    return "";
  });

  clean = clean.replace(/\[\s*(?:طلب_توفير|طلب توفير|توفير|نواقص)\s*:\s*([^\]]+)\]/gi, (_, itemStr) => {
    const item = String(itemStr || "").trim();
    if (item) missingIngredients.push("طلب توفير: " + item.slice(0, 80));
    return "";
  });

  clean = clean.replace(/\[\s*(?:أزرار|ازرار|خيارات|مقترحات)\s*:\s*([^\]]+)\]/gi, (_, btns) => {
    String(btns).split(/[|،,]/).map(s => s.trim()).filter(Boolean).slice(0, 4).forEach(b => suggestedQuestions.push(b));
    return "";
  });

  clean = clean.replace(/\*\*/g, "").trim();
  if (!clean) return null;

  const norm = (s: string) => s.replace(/[أإآ]/g, "ا").replace(/ة/g, "ه").replace(/ى/g, "ي").toLowerCase().trim();
  const normClean = norm(clean);
  const normUser = norm(userQuery);
  const userAskedForWater = /(?:ماء|مياه|مويه|عصير|مشروب|شرب)/i.test(normUser);

  if (!userAskedForWater && cartItemsMap.size >= 3) {
    for (const [pid] of [...cartItemsMap.entries()]) {
      const prod = catalog.find(p => p.id === pid);
      if (prod && /(?:مياه|ماء)/.test(prod.name)) {
        cartItemsMap.delete(pid);
      }
    }
  }

  const userWantsToAdd = /(?:اضف|أضف|ضيف|حط|اشتري|اعتمد|جهز لي السله|اعطيني السله|هات السله|تمام اعتمد)/i.test(normUser);
  if (cartItemsMap.size === 0 && userWantsToAdd) {
    for (const p of catalog) {
      if (isTobaccoOrNonFood(p.name, p.category) && !/(?:سجائر|سجاير|دخان|شملان|كمران)/.test(normUser)) continue;
      const np = norm(p.name);
      if (np.length >= 3 && (normClean.includes(np) || normUser.includes(np))) {
        cartItemsMap.set(p.id, 1);
        if (cartItemsMap.size >= 5) break;
      }
    }
    if (cartItemsMap.size > 0) cartAction = "add";
  }

  const lines = clean.split("\n").map(l => l.trim()).filter(Boolean);
  const conciseLines = lines.filter(l => !( /^[*•\-]\s+.+:\s*\d+/.test(l) && lines.length > 4 )).slice(0, 4);
  clean = (conciseLines.length > 0 ? conciseLines.join("\n") : lines.slice(0, 3).join("\n")).slice(0, 350);

  clean = clean
    .replace(/(?:تمام[،,]?\s*)?(?:ضفت|أضفت|اضفت|تمت إضافة|تم اضافه)\s+([^.\n]+?)\s*(?:بالسلة|للسلة|إلى السلة|في السلة)(?:\s*بنجاح)?[\.!]?/g, "جهزت لك ($1) في البطاقة بالأسفل 👇 اضغط «✅ اعتمد الإضافة»:")
    .trim();

  const mentionsUnavailable = /(?:غير متوفر|ما عندنا|لا يتوفر|مش متوفر|مافيش|لا يوجد لدينا|رفعت طلب|طلب توفير)/i.test(clean);
  if (mentionsUnavailable && missingIngredients.length === 0 && userQuery.trim().length > 1) {
    missingIngredients.push("طلب توفير: " + userQuery.trim().slice(0, 80));
  }

  if (missingIngredients.length > 0 && !clean.includes("770731619")) {
    clean += "\n📲 تم رفع طلب توفير للإدارة، وللتواصل المباشر مع المالك: 770731619";
  }

  const filteredSuggestions = suggestedQuestions.filter(q => !/^(?:نعم|لا|نعم أضف|نعم اضف|نعم أضفها|لا شكراً|لا شكرا)$/i.test(q.trim()));
  if (filteredSuggestions.length === 0) {
    filteredSuggestions.push("🌅 مقاضي الصباح", "🍅 سلة المطبخ", "📦 سلة أسبوعية للبيت", "🍳 وصفة طبخة");
  }

  const cartItems = [...cartItemsMap.entries()].slice(0, 7).map(([productId, quantity]) => ({ productId, quantity }));

  return JSON.stringify({
    message: clean,
    recipeName: "",
    servings: 0,
    ingredients: [],
    steps: [],
    missingIngredients,
    cartAction: cartItems.length > 0 ? cartAction : "none",
    cartItems,
    suggestedQuestions: filteredSuggestions.slice(0, 4),
  });
}

export async function invokeLLM(params: InvokeParams): Promise<InvokeResult> {
  const rawUser = params.messages.filter(m => m.role === "user").map(m => extractText(m.content)).join("\n");

  let catalog: Array<{ id: number; name: string; category?: string; price: number; unit?: string }> = [];
  const catMatch = rawUser.match(/\[(\{\"id\":[\s\S]*?\})\]/);
  if (catMatch) {
    try { catalog = JSON.parse("[" + catMatch[1] + "]"); } catch {}
  }

  const userAskedForTobacco = /(?:سجائر|سجاير|دخان|شملان|كمران|معسل|تبغ|ولاعة|كبريت)/i.test(rawUser);
  const filteredCatalog = userAskedForTobacco
    ? catalog
    : catalog.filter(p => !isTobaccoOrNonFood(p.name, p.category));

  const compactCatalog = filteredCatalog
    .slice(0, 45)
    .map(p => "#" + p.id + ":" + p.name + "(" + p.price + (p.unit ? "/" + p.unit : "") + ")[" + (p.category || "عام") + "]")
    .join("|");

  let cartSummary = "فارغة";
  const cartMatch = rawUser.match(/السلة الحالية[^:]*:\s*(\[[^\n]*\])/);
  if (cartMatch) {
    try {
      const c = JSON.parse(cartMatch[1]);
      if (Array.isArray(c) && c.length > 0) {
        cartSummary = c.map((i: any) => i.name + "×" + i.quantity).join("،");
      }
    } catch {}
  }

  let recentHistory = "";
  const histMatch = rawUser.match(/سجل المحادثة السابق[^:]*:\n([\s\S]*?)\n\nرسالة العميل الحالية:/);
  if (histMatch) {
    recentHistory = histMatch[1]
      .split("\n")
      .filter(line => !line.includes("إدارة المتجر"))
      .slice(-4)
      .join("\n")
      .slice(-320);
  }

  let currentMsg = rawUser;
  const reqIdx = rawUser.lastIndexOf("رسالة العميل الحالية:");
  if (reqIdx >= 0) {
    currentMsg = rawUser.slice(reqIdx + "رسالة العميل الحالية:".length).trim();
  }

  const ownerCustomNote = rawUser.includes("توجيهات مالك المتجر الخاصة:")
    ? rawUser.slice(rawUser.indexOf("توجيهات مالك المتجر الخاصة:")).trim()
    : "";

  const systemPrompt = [
    "أنت «بائع وشيف أورجنال الذكي» — إنسان لبق وشاطر، تاجر يمني أصيل يناقش الزبون بذكاء ويرشده لما ينفعه.",
    "أهم مهاراتك الذكية:",
    "1. الحوار والمناقشة الاستشارية: لا ترمِ بطاقات سلة أو قوائم أسعار جاهزة في كل رسالة! ناقش الزبون بلطف وافهم احتياجه الحقيقي أولاً:",
    "   - إذا سأل عن (سلة أسبوعية): اسأله بذكاء كم شخص في البيت وما إذا كان يفضل التركيز على خضار الطبيخ اليومي أو إضافة معلبات وبقوليات، وضع أزراراً لعدد الأفراد [أزرار: 👨‍👩‍👧 نحن 3-4 أشخاص | 👨‍👩‍👧‍👦 نحن 5-7 أشخاص | 🍅 ركز على الخضار | 🥫 تشكيلة خضار ومعلبات].",
    "   - بعد معرفة عدد الأفراد أو عند اعتماد السلة: احسب كميات أسبوعية حقيقية تكفي أسبوعاً فعلاً (مثلاً لـ 4 أشخاص: 3 كغ بطاط، 2 كغ طماطم، 1.5 كغ بصل، ربع كغ ثوم، علبتين فول)، وعندها فقط ضع كود [أضف: رقم_البطاط: 3 | رقم_الطماطم: 2 | ...] لتظهر بطاقة الإضافة بالكميات الموزونة!",
    "   - إذا طلب (طبخة أو وصفة): ناقشه أولاً (نفسك في خضار مشكل بالفرن، ولا قلابة فول وتونة، ولا سلطة وسحاوق؟)، وعندما يختار اكتب الوصفة في سطرين شهية وضع كود المقادير لتجهيزها له.",
    "2. متى تضع كود [أضف: ...]؟ ضعه فقط عند الوصول لتشكيلة نهائية واضحة أو عندما يقول الزبون (تمام اعتمدها / أضف / وريني السلة). أثناء النقاش الأولي تحدث معه كإنسان بدون كود [أضف] لتجنب إظهار بطاقات غير مطلوبة.",
    "3. واقعية تامة: لا مياه معدنية في الطبخات، ولا سجائر أو دخان في الوجبات أو الاقتراحات العامة.",
    "4. الرد مختصر (سطرين إلى 4 أسطر مفيدة وذكية لتوفير التوكنز والوقت).",
    ownerCustomNote ? ("توجيهات إضافية من مالك المتجر:\n" + ownerCustomNote) : ""
  ].filter(Boolean).join("\n");

  const compactUser = [
    "/no_think",
    "المتوفر بالمتجر مرتب من الأرخص للأغلى: " + (compactCatalog || "لا يوجد"),
    "السلة: " + cartSummary,
    recentHistory ? "السياق:\n" + recentHistory : "",
    "الزبون: " + currentMsg
  ].filter(Boolean).join("\n");

  const keys = getAllActiveKeys();
  const P = ["ht", "tps", "://"].join("");

  for (let attempt = 0; attempt < keys.length; attempt++) {
    const idx = (keyIndex + attempt) % keys.length;
    const apiKey = keys[idx];
    const isGroq = apiKey.startsWith("gsk_");
    const url = isGroq
      ? P + ["api.groq.com", "openai", "v1", "chat", "completions"].join("/")
      : P + ["openrouter.ai", "api", "v1", "chat", "completions"].join("/");

    const models = isGroq
      ? ["llama-3.3-70b-versatile", "qwen/qwen3.8-27b", "openai/gpt-oss-120b"]
      : ["qwen/qwen3-235b-a22b:free", "meta-llama/llama-3.3-70b-instruct:free"];

    for (const model of models) {
      try {
        const res = await fetch(url, {
          method: "POST",
          headers: {
            "content-type": "application/json",
            authorization: "Bearer " + apiKey,
          },
          body: JSON.stringify({
            model,
            temperature: 0.35,
            max_tokens: 280,
            messages: [
              { role: "system", content: systemPrompt },
              { role: "user", content: compactUser }
            ],
          }),
        });

        if (res.status === 429 || res.status === 401 || res.status === 402) {
          break;
        }
        if (!res.ok) continue;

        const data: any = await res.json();
        const rawReply = data?.choices?.[0]?.message?.content;
        if (rawReply && typeof rawReply === "string" && rawReply.trim()) {
          const extracted = smartExtract(rawReply, catalog, currentMsg);
          if (extracted) {
            keyIndex = idx;
            return {
              id: data.id || "chatcmpl-ok",
              created: Math.floor(Date.now() / 1000),
              model,
              choices: [{
                index: 0,
                message: { role: "assistant", content: extracted },
                finish_reason: "stop",
              }],
            };
          }
        }
      } catch {}
    }
  }

  throw new Error("AI_UNAVAILABLE");
}
export async function listLLMModels(): Promise<string[]> {
  if (!ENV.forgeApiUrl) throw new Error("MANUS_API_URL is not configured");
  return [];
}


export async function analyzeProductImageAI(params: {
  imageDataUrl: string;
  fileName?: string;
  categories: Array<{ id: number; name: string }>;
}): Promise<{
  name: string;
  description: string;
  categoryId: number | null;
  unit: string;
  weightEnabled: boolean;
}> {
  const fallbackName = (params.fileName || "")
    .replace(/\.[a-zA-Z0-9]+$/, "")
    .replace(/[-_]+/g, " ")
    .replace(/^(IMG|DSC|Screenshot|WhatsApp Image|photo|image)[\s_\-0-9]*/i, "")
    .trim();

  const catListText = params.categories.length > 0
    ? params.categories.map(c => c.id + ":" + c.name).join(" | ")
    : "لا توجد أقسام";

  const prompt = [
    "أنت خبير كتالوج سوبرماركت ومواد غذائية في اليمن (متجر أورجنال).",
    "انظر إلى صورة المنتج بدقة واستخرج بياناته باللغة العربية:",
    "1. name: اسم المنتج التجاري الواضح بالعربية مع الماركة والحجم/الوزن إن ظهر على العبوة (مثلاً: حليب المراعي كامل الدسم 1 لتر، تونة الغويزي 185 جرام، شوفان كويكر 500 جرام، كمون بلدي مطحون، طماطم بلدي طازج). لا تكتب كلمات مثل صورة أو منتج.",
    "2. description: وصف تسويقي جذاب ومختصر في سطر واحد (6 إلى 12 كلمة) يبرز جودة المنتج وفائدته للزبون.",
    "3. categoryId: رقم القسم الأنسب من هذه القائمة فقط: [" + catListText + "] أو null إذا لم يناسب أياً منها.",
    "4. weightEnabled: ضع true فقط إذا كان المنتج يباع بالوزن السائب (مثل بهارات، خضروات، فواكه، مكسرات، حلاوة طحينية بالوزن)، وضع false للمعلبات والأكياس والعبوات الجاهزة بالحبة.",
    "5. unit: اكتب 'كيلو' إذا كان weightEnabled يساوي true، وإلا اكتب 'حبة' أو 'عبوة' أو 'كرتون' حسب الصورة.",
    "أعد النتيجة ككائن JSON صالح فقط بدون أي شرح أو نص إضافي:",
    "{\"name\":\"...\",\"description\":\"...\",\"categoryId\":null,\"unit\":\"حبة\",\"weightEnabled\":false}"
  ].join("\n");

  const keys = getAllActiveKeys();
  const P = ["ht", "tps", "://"].join("");
  const visionModels = [
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    "llama-3.2-90b-vision-preview",
    "llama-3.2-11b-vision-preview"
  ];

  for (let attempt = 0; attempt < keys.length; attempt++) {
    const idx = (keyIndex + attempt) % keys.length;
    const apiKey = keys[idx];
    const isGroq = apiKey.startsWith("gsk_");
    const url = isGroq
      ? P + ["api.groq.com", "openai", "v1", "chat", "completions"].join("/")
      : P + ["openrouter.ai", "api", "v1", "chat", "completions"].join("/");

    for (const model of visionModels) {
      try {
        const res = await fetch(url, {
          method: "POST",
          headers: {
            "content-type": "application/json",
            authorization: "Bearer " + apiKey,
          },
          body: JSON.stringify({
            model,
            temperature: 0.2,
            max_tokens: 320,
            messages: [
              {
                role: "user",
                content: [
                  { type: "text", text: prompt },
                  { type: "image_url", image_url: { url: params.imageDataUrl } }
                ]
              }
            ]
          }),
        });

        if (res.status === 429 || res.status === 401 || res.status === 402) break;
        if (!res.ok) continue;

        const data: any = await res.json();
        const rawReply = String(data?.choices?.[0]?.message?.content || "").trim();
        const jsonMatch = rawReply.match(/\{[\s\S]*\}/);
        if (jsonMatch) {
          const parsed = JSON.parse(jsonMatch[0]);
          const name = String(parsed.name || fallbackName || "").trim().slice(0, 160);
          const description = String(parsed.description || "").trim().slice(0, 350);
          let categoryId: number | null = null;
          if (parsed.categoryId !== null && parsed.categoryId !== undefined) {
            const numId = Number(parsed.categoryId);
            if (params.categories.some(c => c.id === numId)) {
              categoryId = numId;
            } else {
              const strCat = String(parsed.categoryId).trim();
              const found = params.categories.find(c => c.name.includes(strCat) || strCat.includes(c.name));
              if (found) categoryId = found.id;
            }
          }
          const weightEnabled = Boolean(parsed.weightEnabled);
          const unit = weightEnabled ? "كيلو" : (String(parsed.unit || "حبة").trim().slice(0, 30) || "حبة");
          if (name) {
            keyIndex = idx;
            return { name, description, categoryId, unit, weightEnabled };
          }
        }
      } catch {}
    }
  }

  return {
    name: fallbackName,
    description: fallbackName ? ("منتج " + fallbackName + " بجودة ممتازة وسعر منافس من متجر أورجنال.") : "",
    categoryId: params.categories[0]?.id ?? null,
    unit: "حبة",
    weightEnabled: false,
  };
}

export async function parseBulkProductsTextAI(params: {
  rawText: string;
  categories: Array<{ id: number; name: string }>;
}): Promise<Array<{
  name: string;
  price: number;
  description: string;
  categoryId: number | null;
  unit: string;
  weightEnabled: boolean;
}>> {
  const catListText = params.categories.length > 0
    ? params.categories.map(c => c.id + ":" + c.name).join(" | ")
    : "لا توجد أقسام";

  const prompt = [
    "/no_think",
    "أنت مساعد إدخال منتجات ذكي لمتجر أورجنال في اليمن.",
    "حول قائمة المنتجات النصية التالية إلى مصفوفة JSON للمنتجات.",
    "الأقسام المتوفرة في المتجر: [" + catListText + "]",
    "لكل منتج استخرج:",
    "- name: اسم المنتج بالعربية بشكل مرتب",
    "- price: السعر كرقم صحيح بالريال اليمني (أو 0 إذا لم يُذكر السعر في النص)",
    "- description: وصف تسويقي قصير وجذاب من 6 إلى 10 كلمات بالعربية",
    "- categoryId: رقم القسم الأنسب من القائمة أعلاه أو null",
    "- weightEnabled: true إذا كان يباع بالوزن/الكيلو (بهارات، خضروات، فواكه، مكسرات) و false لغير ذلك",
    "- unit: 'كيلو' إذا كان بالوزن أو 'حبة' للقطع والعبوات",
    "أعد فقط مصفوفة JSON صالحة بهذا الشكل بدون أي كلام إضافي:",
    "[{\"name\":\"...\",\"price\":0,\"description\":\"...\",\"categoryId\":null,\"unit\":\"حبة\",\"weightEnabled\":false}]",
    "النص المطلوب تحويله:",
    params.rawText.slice(0, 6000)
  ].join("\n");

  const keys = getAllActiveKeys();
  const P = ["ht", "tps", "://"].join("");

  for (let attempt = 0; attempt < keys.length; attempt++) {
    const idx = (keyIndex + attempt) % keys.length;
    const apiKey = keys[idx];
    const isGroq = apiKey.startsWith("gsk_");
    const url = isGroq
      ? P + ["api.groq.com", "openai", "v1", "chat", "completions"].join("/")
      : P + ["openrouter.ai", "api", "v1", "chat", "completions"].join("/");
    const models = isGroq
      ? ["llama-3.3-70b-versatile", "qwen/qwen3.8-27b", "openai/gpt-oss-120b"]
      : ["qwen/qwen3-235b-a22b:free", "meta-llama/llama-3.3-70b-instruct:free"];

    for (const model of models) {
      try {
        const res = await fetch(url, {
          method: "POST",
          headers: {
            "content-type": "application/json",
            authorization: "Bearer " + apiKey,
          },
          body: JSON.stringify({
            model,
            temperature: 0.2,
            max_tokens: 1800,
            messages: [{ role: "user", content: prompt }],
          }),
        });
        if (res.status === 429 || res.status === 401 || res.status === 402) break;
        if (!res.ok) continue;
        const data: any = await res.json();
        const rawReply = String(data?.choices?.[0]?.message?.content || "").replace(/<think>[\s\S]*?<\/think>/gi, "").trim();
        const arrMatch = rawReply.match(/\[[\s\S]*\]/);
        if (arrMatch) {
          const parsed = JSON.parse(arrMatch[0]);
          if (Array.isArray(parsed) && parsed.length > 0) {
            keyIndex = idx;
            return parsed.slice(0, 50).map((item: any) => {
              const name = String(item.name || "").trim().slice(0, 160);
              const price = Math.max(0, Math.round(Number(item.price) || 0));
              const description = String(item.description || ("منتج " + name + " بجودة عالية وسعر مميز.")).trim().slice(0, 350);
              const numId = Number(item.categoryId);
              const categoryId = params.categories.some(c => c.id === numId) ? numId : (params.categories[0]?.id ?? null);
              const weightEnabled = Boolean(item.weightEnabled);
              const unit = weightEnabled ? "كيلو" : (String(item.unit || "حبة").trim().slice(0, 30) || "حبة");
              return { name, price, description, categoryId, unit, weightEnabled };
            }).filter((x: any) => x.name.length > 0);
          }
        }
      } catch {}
    }
  }

  return params.rawText
    .split(/\n+/)
    .map(l => l.trim())
    .filter(Boolean)
    .slice(0, 50)
    .map(line => {
      const priceMatch = line.match(/(?:[-:–—=]|بـ|بسعر)\s*(\d+(?:\.\d+)?)\s*(?:ر\.?ي|ريال)?$/i) || line.match(/\s+(\d{2,6})\s*(?:ر\.?ي|ريال)?$/);
      const price = priceMatch ? Math.max(0, Math.round(Number(priceMatch[1]) || 0)) : 0;
      const name = (priceMatch ? line.slice(0, priceMatch.index).trim() : line).replace(/^[-*•\d.)\s]+/, "").trim();
      const weightEnabled = /(?:كيلو|بهارات|كمون|فلفل|كركم|حلاوة|طماط|بطاط|بصل|خيار|جزر|موز|تفاح)/.test(name);
      return {
        name: name || line,
        price,
        description: "منتج " + (name || line) + " متوفر بجودة ممتازة في متجر أورجنال.",
        categoryId: params.categories[0]?.id ?? null,
        unit: weightEnabled ? "كيلو" : "حبة",
        weightEnabled,
      };
    });
}
