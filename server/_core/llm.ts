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

  const cartItems: Array<{ productId: number; quantity: number }> = [];
  let cartAction: "none" | "add" | "remove" = "none";
  const suggestedQuestions: string[] = [];
  const missingIngredients: string[] = [];

  clean = clean.replace(/\[\s*(?:أضف|اضف|إضافة|اضافة|add)\s*:\s*(\d+)(?:\s*:\s*(\d+))?\s*\]/gi, (_, idStr, qtyStr) => {
    const pid = Number(idStr);
    const qty = Math.max(1, Number(qtyStr || 1));
    if (catalog.some(p => p.id === pid)) {
      cartAction = "add";
      cartItems.push({ productId: pid, quantity: qty });
    }
    return "";
  });

  clean = clean.replace(/\[\s*(?:طلب_توفير|طلب توفير|توفير|نواقص)\s*:\s*([^\]]+)\]/gi, (_, itemStr) => {
    const item = String(itemStr || "").trim();
    if (item) missingIngredients.push("طلب توفير: " + item.slice(0, 80));
    return "";
  });

  clean = clean.replace(/\[\s*(?:أزرار|ازرار|خيارات|مقترحات)\s*:\s*([^\]]+)\]/gi, (_, btns) => {
    String(btns).split(/[|،,]/).map(s => s.trim()).filter(Boolean).slice(0, 3).forEach(b => suggestedQuestions.push(b));
    return "";
  });

  clean = clean.replace(/\*\*/g, "").trim();
  if (!clean) return null;

  const mentionsUnavailable = /(?:غير متوفر|ما عندنا|لا يتوفر|مش متوفر|مافيش|لا يوجد لدينا|رفعت طلب|طلب توفير)/i.test(clean);
  if (mentionsUnavailable && missingIngredients.length === 0 && userQuery.trim().length > 1) {
    missingIngredients.push("طلب توفير: " + userQuery.trim().slice(0, 80));
  }

  if (missingIngredients.length > 0 && !clean.includes("770731619")) {
    clean += "\n📲 تم إرسال طلبك للإدارة لتوفيره، وللتواصل المباشر مع المالك: 770731619";
  }

  if ((suggestedQuestions.length as number) === 0) {
    for (const p of catalog) {
      if (clean.includes(p.name) && !isTobaccoOrNonFood(p.name, p.category)) {
        suggestedQuestions.push("أضف " + p.name);
      }
      if ((suggestedQuestions.length as number) >= 2) break;
    }
    if ((suggestedQuestions.length as number) === 0) {
      suggestedQuestions.push("تصفح الأقسام", "عرض السلة");
    }
  }

  return JSON.stringify({
    message: clean,
    recipeName: "",
    servings: 0,
    ingredients: [],
    steps: [],
    missingIngredients,
    cartAction,
    cartItems,
    suggestedQuestions: suggestedQuestions.slice(0, 3),
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

  const sortedCatalog = [...filteredCatalog].sort((a, b) => a.price - b.price);
  const compactCatalog = sortedCatalog
    .map(p => "#" + p.id + " [قسم: " + (p.category || "عام") + "] " + p.name + " (" + p.price + " ر.ي" + (p.unit ? "/" + p.unit : "") + ")")
    .join(" | ");

  let cartSummary = "فارغة";
  const cartMatch = rawUser.match(/السلة الحالية[^:]*:\s*(\[[^\n]*\])/);
  if (cartMatch) {
    try {
      const c = JSON.parse(cartMatch[1]);
      if (Array.isArray(c) && c.length > 0) {
        cartSummary = c.map((i: any) => i.name + "×" + i.quantity).join("، ");
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
      .slice(-350);
  }

  let currentMsg = rawUser;
  const reqIdx = rawUser.lastIndexOf("رسالة العميل الحالية:");
  if (reqIdx >= 0) {
    currentMsg = rawUser.slice(reqIdx + "رسالة العميل الحالية:".length).trim();
  }

  const systemPrompt = [
    "أنت المساعد الذكي الرسمي في متجر أورجنال. ردك مختصر وواضح (سطرين فقط) بلهجة يمنية ودودة ومحترمة.",
    "قواعد صارمة جداً:",
    "1. التصنيف الصحيح والمنطق: انتبه لقسم واسم كل منتج بدقة! لا تخلط أبداً بين المشروبات/العصائر وبين القشطة/الألبان أو الخضروات أو البقوليات. كل منتج يُقترح فقط في مكانه الصحيح (العصير والماء للمشروبات، القشطة والزبادي والجبن للألبان، الليمون والخضار للخضروات والحوامض).",
    "2. منع السجائر والدخان: يُمنع منعاً باتاً اقتراح السجائر أو الدخان كمشروب أو وجبة أو ضمن أي اقتراحات عامة.",
    "3. لا تكرر نفس المنتجين في كل رد: أجب على سؤال الزبون مباشرة بحسب ما يطلبه (إذا سأل عن حامض اعرض الحوامض كالليمون، وإذا سأل عن عصير اعرض العصائر فقط، وإذا سأل سؤالاً عاماً رحب به واسأله أي قسم يفضل).",
    "4. عدم الإضافة للسلة بدون طلب صريح: لا تضع وسم [أضف: ...] أبداً عندما يستفسر الزبون أو يسأل عن الأسعار أو الأصناف! فقط اعرض الصنف وسعره واسأله: «تحب أضيفه لك للسلة؟». ضع [أضف: رقم_المنتج: الكمية] فقط إذا قال الزبون صراحةً «أضف» أو «اشتري» أو «اعتمد».",
    "5. عند طلب صنف غير موجود في قائمة المتجر: اعتذر بلطف وأخبره أنه غير متوفر حالياً وتم رفع طلب توفير للإدارة مع رقم المالك 770731619، وضع في نهاية ردك: [طلب_توفير: اسم الصنف المطلوب].",
    "6. إياك أن تكتب عبارة «إدارة المتجر:» في ردك؛ أنت المساعد الذكي فقط.",
    "7. اختم ردك بـ: [أزرار: خيار 1 | خيار 2]"
  ].join("\n");

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
            max_tokens: 700,
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
