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

function extractText(content: MessageContent | MessageContent[]): string {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) return content.map(c => (typeof c === "string" ? c : "text" in c ? c.text : "")).join("\n");
  return "text" in content ? content.text : "";
}

let geminiSkipUntil = 0;

function isValidAssistantJson(raw: string): boolean {
  const u = raw.replace(/^\s*```(?:json)?\s*/i, "").replace(/\s*```\s*$/, "").trim();
  const s = u.indexOf("{"), e = u.lastIndexOf("}");
  if (s < 0 || e <= s) return false;
  try {
    const p = JSON.parse(u.slice(s, e + 1));
    return Boolean(p && typeof p === "object" && (p.message || p.reply || p.steps));
  } catch { return false; }
}

async function tryGeminiOnce(apiKey: string, fullPrompt: string, wantsJson: boolean): Promise<string | null> {
  if (!apiKey || Date.now() < geminiSkipUntil) return null;
  const cleanKey = apiKey.replace(/^["'`]+|["'`]+$/g, "").trim();
  if (!cleanKey) return null;
  for (const model of ["gemini-2.0-flash", "gemini-1.5-flash"]) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 5500);
    try {
      const res = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${encodeURIComponent(cleanKey)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [{ role: "user", parts: [{ text: fullPrompt }] }],
          generationConfig: { temperature: 0.55, maxOutputTokens: 1200, ...(wantsJson ? { responseMimeType: "application/json" } : {}) },
        }),
        signal: controller.signal,
      });
      clearTimeout(timer);
      if (!res.ok) continue;
      const data: any = await res.json();
      const text = (data?.candidates?.[0]?.content?.parts?.map((p: any) => p.text || "").join("") || "").trim();
      if (text && (!wantsJson || isValidAssistantJson(text))) return text;
    } catch { clearTimeout(timer); }
  }
  geminiSkipUntil = Date.now() + 5 * 60 * 1000;
  return null;
}

async function callCloudOpenAI(messages: Array<{ role: string; content: string }>, wantsJson: boolean): Promise<string | null> {
  for (const model of ["openai-fast", "openai", "mistral"]) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 9000);
    try {
      const res = await fetch("https://text.pollinations.ai/openai", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
          "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36",
          "Referer": "https://original-store.onrender.com/",
        },
        body: JSON.stringify({ model, messages, temperature: 0.55, ...(wantsJson ? { response_format: { type: "json_object" } } : {}) }),
        signal: controller.signal,
      });
      clearTimeout(timer);
      if (!res.ok) continue;
      const raw = await res.text();
      if (!raw || !raw.trim()) continue;
      let content = raw.trim();
      try {
        const d = JSON.parse(raw);
        if (typeof d?.choices?.[0]?.message?.content === "string") content = d.choices[0].message.content.trim();
      } catch {}
      if (content && (!wantsJson || isValidAssistantJson(content))) return content;
    } catch { clearTimeout(timer); }
  }
  return null;
}

function normalizeAr(s: string): string {
  return s.toLowerCase().replace(/[أإآٱ]/g, "ا").replace(/ة/g, "ه").replace(/ى/g, "ي").replace(/[\u064B-\u065Fـ]/g, "").trim();
}

function buildSmartYemeniChefFallback(messages: Array<{ role: string; content: string }>): string {
  const userText = messages.filter(m => m.role === "user").map(m => m.content).join("\n");
  let catalog: Array<{ id: number; name: string; price: number; unit: string }> = [];
  const catMatch = userText.match(/\[(\{"id":[\s\S]*?\})\]/);
  if (catMatch) { try { catalog = JSON.parse(`[${catMatch[1]}]`); } catch {} }

  let request = userText;
  const reqMarker = userText.lastIndexOf("رسالة العميل الحالية:");
  const prodMarker = userText.indexOf("الصنف الأساسي:");
  if (reqMarker >= 0) request = userText.slice(reqMarker + "رسالة العميل الحالية:".length).trim();
  else if (prodMarker >= 0) { const m = userText.match(/«([^»]+)»/); request = m ? m[1] : userText; }

  const normReq = normalizeAr(request);
  const findProducts = (keywords: string[], maxCount = 4) => {
    const matched: Array<{ productId: number; quantity: number }> = [];
    const normKeys = keywords.map(normalizeAr);
    for (const item of catalog) {
      const nName = normalizeAr(item.name);
      if (normKeys.some(k => k.length >= 2 && nName.includes(k))) {
        matched.push({ productId: item.id, quantity: 1 });
        if (matched.length >= maxCount) break;
      }
    }
    return matched;
  };

  if (prodMarker >= 0 || (request.includes("«") && request.includes("»"))) {
    const prodName = userText.match(/«([^»]+)»/)?.[1]?.trim() || request.trim();
    return JSON.stringify({
      message: `يا هلا بك يا غالي! الصنف «${prodName}» ممتاز جداً ونقدر نحضر منه 3 خيارات شهية:\n1️⃣ الطريقة الاقتصادية السريعة: تحضير منزلي خفيف وموفر في 10 دقائق.\n2️⃣ الطريقة اليمنية الشعبية: كشنة يمنية أصيلة مع البصل والطماطم والحوائج.\n3️⃣ الطريقة المميزة: تقديم فاخر مع الإضافات الطازجة.\n\nإيش رأيك؟ تفضل الطريقة الاقتصادية أو الشعبية، أو تحب نعدل الوصفة؟`,
      recipeName: `وصفة يمنية شهية بـ ${prodName}`,
      servings: 3,
      ingredients: findProducts([prodName, ...prodName.split(/\s+/)], 3),
      steps: [
        `نجهز «${prodName}» مع المكونات الأساسية.`,
        "نحمر البصل والثوم قليلًا في الزيت حتى يذبل ويأخذ لوناً ذهبياً.",
        `نضيف «${prodName}» مع رشة خفيفة من البهارات اليمنية ونقلب بهدوء.`,
        "نتركه يتسبك على نار هادئة لدقائق ويقدم ساخناً مع الخبز اليمني وبالعافية!",
      ],
      missingIngredients: ["بصل طازج", "ثوم", "بهارات يمنية مشكلة"],
      cartAction: "none",
      cartItems: [],
    });
  }

  if (normReq.includes("مرق") || normReq.includes("سلت") || normReq.includes("فحس")) {
    const dishTitle = normReq.includes("سلت") ? "سلتة يمنية صنعانية أصيلة" : normReq.includes("فحس") ? "فحسة يمنية بالحرضة" : "مرقة يمنية أصيلة ومسبكة";
    return JSON.stringify({
      message: `يا هلا ومسهلا بك يا غالي! أبشر بأحلى وصفة «${dishTitle}» تطيب خاطرك وتدفّي القلب على الطريقة اليمنية الأصيلة:\n\n1️⃣ الخيار الشعبي الأصيل: مرقة مسبكة مع الحوائج اليمنية والبطاط والبصل.\n2️⃣ الخيار الاقتصادي السريع: مرقة خفيفة وسريعة التحضير في 20 دقيقة.\n\nجهزت لك المقادير والخطوات بالتفصيل بالأسفل، ولو تحبها بدون توابل قوية أو لعدد أشخاص أكثر آمرني وأعدلها لك فوراً!`,
      recipeName: dishTitle,
      servings: 4,
      ingredients: findProducts(["لحم", "دجاج", "مرق", "بهار", "حوائج", "ملح", "زيت", "بصل", "بطاط", "طماط", "صلص"], 4),
      steps: [
        "نغسل اللحم أو الدجاج جيداً ونضعه في القدر مع ماء مغلي ونزيل الريم تماماً حتى تصبح المرقة صافية.",
        "نضيف بصلة مفرومة، فصوص ثوم، حب هيل، وملعقة من الحوائج اليمنية الخاصة بالمرق (كركم، كمون، فلفل أسود، كزبرة).",
        "نترك المرق يغلي على نار هادئة حتى ينضج تماماً ويتركز طعمه اللذيذ، ثم نضيف الملح ومكعبات البطاطا.",
        "تقدم المرقة ساخنة مع عصر ليمونة ورشة كزبرة خضراء إلى جانب الأرز أو الخبز اليمني الساخن، وبالهناء والشفاء!",
      ],
      missingIngredients: ["لحم أو دجاج طازج", "بصل وثوم", "حوائج مرق يمنية", "ليمون طازج"],
      cartAction: "none",
      cartItems: [],
    });
  }

  if (normReq.includes("كبس") || normReq.includes("مندي") || normReq.includes("زربيان") || normReq.includes("رز") || normReq.includes("ارز") || normReq.includes("غدا")) {
    return JSON.stringify({
      message: "يا حيّا الله الغالي! للغداء اليمني الأصيل جهزت لك وصفة «كبسة يمنية شهية ومضبوطة» تفتح النفس. شوف المقادير والخطوات بالأسفل، وقل لي لو تحب نعدل عليها!",
      recipeName: "كبسة يمنية أصيلة بالبهارات العطرية",
      servings: 4,
      ingredients: findProducts(["ارز", "رز", "بسمتي", "دجاج", "تونه", "زيت", "صلص", "طماط", "بهار", "ملح"], 4),
      steps: [
        "نغسل الأرز البسمتي وننقعه في ماء فاتر لمدة 20 دقيقة ثم نصفيه.",
        "في القدر نحمر البصل في الزيت مع الثوم والبهارات الصحيحة (هيل، قرنفل، قرفة).",
        "نضيف الطماطم المفرومة وملعقة معجون طماطم مع الدجاج أو اللحم أو التونة ونقلب حتى تتسبك الكشنة.",
        "نضيف الماء المغلي والملح ثم الأرز، ونهدئ النار تماماً لمدة 15 دقيقة حتى ينضج ويقدم بالعافية!",
      ],
      missingIngredients: ["بصل وطماطم طازجة", "بهارات كبسة صحيحة"],
      cartAction: "none",
      cartItems: [],
    });
  }

  if (normReq.includes("حلا") || normReq.includes("حلى") || normReq.includes("حلو") || normReq.includes("معصوب") || normReq.includes("عريك")) {
    return JSON.stringify({
      message: "يا سلام عليك! جهزت لك وصفة «حلى القشطة والعسل على الطريقة اليمنية» سهل جداً ومكوناته اقتصادية ومتوفرة. شوف المقادير والخطوات بالأسفل!",
      recipeName: "حلى القشطة والعسل اليمني الفاخر",
      servings: 4,
      ingredients: findProducts(["قشط", "عسل", "حليب", "بسكويت", "سكر", "تاج", "جبن", "شوكول", "تمر"], 4),
      steps: [
        "نفتت البسكويت أو الخبز الأسمر ناعماً ونرتبه كطبقة أولى في طبق التقديم.",
        "نخلط القشطة مع الحليب المكثف أو السكر ورشة هيل مطحون ونوزعها فوق الطبقة الأولى.",
        "نزين الوجه بالعسل والمكسرات المتوفرة ويقدم بالعافية!",
      ],
      missingIngredients: ["موز طازج أو مكسرات للتزيين", "رشة هيل مطحون"],
      cartAction: "none",
      cartItems: [],
    });
  }

  const words = normReq.split(/\s+/).filter(w => w.length >= 2);
  let matched = findProducts(words, 4);
  if (!matched.length && catalog.length > 0) matched = catalog.slice(0, 3).map(p => ({ productId: p.id, quantity: 1 }));

  return JSON.stringify({
    message: `حياك الله يا غالي في متجر أوريجنال! بالنسبة لطلبك «${request.slice(0, 80)}»، جهزت لك اقتراح طبخة يمنية منزلية رائعة واقتصادية مع أفضل الأصناف المتوفرة في المتجر حالياً.\n\nتقدر تضيف المقادير المتوفرة للسلة بضغطة زر، أو قل لي إيش الطبخة اللي تحبها (مثل: مرقة، كبسة، سلتة، فطور سريع، أو حلى) وأرتبها لك فوراً!`,
    recipeName: "كشنة وطبخة يمنية منزلية سريعة",
    servings: 4,
    ingredients: matched,
    steps: [
      "نجهز المكونات الأساسية المتوفرة ونغسل الخضار جيداً.",
      "نحمر البصل والثوم في الزيت حتى يأخذ لوناً ذهبياً ثم نضيف الطماطم والبهارات اليمنية (كمون، كزبرة، كركم).",
      "نضيف المكونات الرئيسية ونتركها تتسبك على نار هادئة حتى تنضج تماماً.",
      "تقدم ساخنة مع الخبز اليمني أو الأرز، وبالهناء والعافية!",
    ],
    missingIngredients: ["بصل وطماطم طازجة", "بهارات يمنية مشكلة"],
    cartAction: "none",
    cartItems: [],
  });
}

export async function invokeLLM(params: InvokeParams): Promise<InvokeResult> {
  const apiKey = (process.env.GEMINI_API_KEY || process.env.MANUS_API_KEY || ENV.forgeApiKey || "").trim();
  const normalizedMessages = params.messages.map(m => ({
    role: m.role === "assistant" ? "assistant" : m.role === "system" ? "system" : "user",
    content: extractText(m.content),
  }));
  const fullPrompt = normalizedMessages.map(m => (m.role === "system" ? `تعليمات النظام:\n${m.content}` : m.content)).join("\n\n");
  const fmt = params.responseFormat || params.response_format;
  const wantsJson = fmt?.type === "json_object" || fmt?.type === "json_schema";

  const geminiText = await tryGeminiOnce(apiKey, fullPrompt, wantsJson);
  if (geminiText) {
    return { id: "gemini-" + Date.now(), created: Date.now(), model: "gemini-2.0-flash", choices: [{ index: 0, message: { role: "assistant", content: geminiText }, finish_reason: "stop" }] };
  }
  const cloudText = await callCloudOpenAI(normalizedMessages, wantsJson);
  if (cloudText) {
    return { id: "cloud-" + Date.now(), created: Date.now(), model: "openai", choices: [{ index: 0, message: { role: "assistant", content: cloudText }, finish_reason: "stop" }] };
  }
  const fallbackJson = buildSmartYemeniChefFallback(normalizedMessages);
  return { id: "yemeni-chef-" + Date.now(), created: Date.now(), model: "original-yemeni-chef", choices: [{ index: 0, message: { role: "assistant", content: fallbackJson }, finish_reason: "stop" }] };
}
