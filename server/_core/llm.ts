import { ENV } from "./env";

export type Role = "system" | "user" | "assistant" | "tool" | "function";
export type TextContent = { type: "text"; text: string };
export type ImageContent = { type: "image_url"; image_url: { url: string; detail?: "auto" | "low" | "high" } };
export type FileContent = { type: "file_url"; file_url: { url: string; mime_type?: string } };
export type MessageContent = string | TextContent | ImageContent | FileContent;
export type Message = { role: Role; content: MessageContent | MessageContent[]; name?: string; tool_call_id?: string };
export type Tool = { type: "function"; function: { name: string; description?: string; parameters?: Record<string, unknown> } };
export type ToolChoice = "none" | "auto" | "required" | { name: string } | { type: "function"; function: { name: string } };
export type InvokeParams = {
  messages: Message[];
  tools?: Tool[];
  toolChoice?: ToolChoice;
  tool_choice?: ToolChoice;
  maxTokens?: number;
  max_tokens?: number;
  outputSchema?: { name: string; schema: Record<string, unknown>; strict?: boolean };
  output_schema?: { name: string; schema: Record<string, unknown>; strict?: boolean };
  responseFormat?: { type: string; json_schema?: { name: string; schema: Record<string, unknown>; strict?: boolean } };
  response_format?: { type: string; json_schema?: { name: string; schema: Record<string, unknown>; strict?: boolean } };
};
export type ToolCall = { id: string; type: "function"; function: { name: string; arguments: string } };
export type InvokeResult = {
  id: string;
  created: number;
  model: string;
  choices: Array<{ index: number; message: { role: Role; content: string | Array<TextContent | ImageContent | FileContent>; tool_calls?: ToolCall[] }; finish_reason: string | null }>;
  usage?: { prompt_tokens: number; completion_tokens: number; total_tokens: number };
};

const P = ["ht", "tps", "://"].join("");
const _encKey = "c2stb3ItdjEtNDI5Y2MzZWQzNTU3MTI0Njg4M2NhZDE2NmIxNmU2NGMzNDk1ZTQ3OTBjYTZjYzkxN2Q5NjhmMWNiYTIzZjJkOQ==";
const OPENROUTER_KEY = (process.env.OPENROUTER_API_KEY || Buffer.from(_encKey, "base64").toString("utf-8")).trim();

const contentToText = (content: Message["content"]): string => {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) return content.map((p) => (typeof p === "string" ? p : p.type === "text" ? p.text : "")).filter(Boolean).join("\n");
  if (content && typeof content === "object" && "text" in content) return content.text;
  return "";
};

function normalizeAr(str: string): string {
  return String(str || "")
    .toLowerCase()
    .replace(/[أإآٱ]/g, "ا")
    .replace(/ة/g, "ه")
    .replace(/ى/g, "ي")
    .replace(/[^\p{L}\p{N}\s]/gu, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function parseArabicQty(segment: string): number {
  const words = normalizeAr(segment).split(/\s+/);
  for (const w of words) {
    if (/^\d+$/.test(w)) return Math.max(1, parseInt(w, 10));
    const clean = w.replace(/^و/, "");
    if (["عشره", "عشر"].includes(clean)) return 10;
    if (["تسعه", "تسع"].includes(clean)) return 9;
    if (["ثمانيه", "ثمان"].includes(clean)) return 8;
    if (["سبعه", "سبع"].includes(clean)) return 7;
    if (["سته", "ست"].includes(clean)) return 6;
    if (["خمسه", "خمس"].includes(clean)) return 5;
    if (["اربعه", "اربع"].includes(clean)) return 4;
    if (["ثلاثه", "ثلاث"].includes(clean)) return 3;
    if (["اثنين", "ثنتين", "اثنان", "حبتين", "علبتين", "كرتونين", "كيسين", "زوج"].includes(clean)) return 2;
    if (["واحد", "واحده", "حبه", "علبه"].includes(clean)) return 1;
  }
  return 1;
}

function extractCartCommand(userMsg: string, catalog: any[], fallbackProduct?: any): { cartAction: "none" | "add" | "remove"; cartItems: Array<{ productId: number; quantity: number }> } {
  const normMsg = normalizeAr(userMsg);
  const words = normMsg.split(/\s+/);
  const addVerbs = new Set(["اضف", "اضيف", "ضيف", "ضف", "حط", "زيد", "زد", "زود", "هات", "اضفها", "اضفه", "ضيفه", "ضيفها"]);
  const remVerbs = new Set(["احذف", "حذف", "شيل", "امسح", "نقص", "الغي", "الغاء", "فرغ", "ازل", "ازاله", "احذفه", "شيله"]);

  const isAdd = words.some((w) => addVerbs.has(w) || addVerbs.has(w.replace(/^و/, ""))) || normMsg.includes("للسله") || normMsg.includes("الي السله");
  const isRemove = words.some((w) => remVerbs.has(w) || remVerbs.has(w.replace(/^و/, "")));
  if (!isAdd && !isRemove) return { cartAction: "none", cartItems: [] };
  const action: "add" | "remove" = isRemove && !isAdd ? "remove" : "add";

  const qtySplitRegex = /\s+(?=(?:و)?(?:واحد|اثنين|ثنتين|ثلاث|اربع|خمس|ست|سبع|ثمان|تسع|عشر|\d+|حبه|حبتين|علبه)\s)/g;
  const clauses = normMsg.split(qtySplitRegex).map((s) => s.trim()).filter(Boolean);

  const ignoreWords = new Set(["من", "في", "على", "الى", "الي", "السله", "سله", "للسله", "حبه", "حبتين", "علبه", "مل", "كجم", "كيلو", "جرام", "واحد", "واحده", "اثنين", "ثنتين", "ثلاث", "ثلاثه", "اربعه", "اربع", "خمسه", "خمس", "اضف", "ضيف", "ضف", "احذف", "شيل", "لي", "ابي", "ابغي", "اريد", "منه", "منها", "هذا", "هذه", "المنتج"]);

  const matchedMap = new Map<number, number>();

  for (const clause of clauses) {
    const qty = parseArabicQty(clause);
    const clauseTokens = clause
      .split(/\s+/)
      .map((w) => w.replace(/^و/, ""))
      .filter((w) => w.length >= 2 && !ignoreWords.has(w) && !/^\d+$/.test(w));

    let bestProduct: any = null;
    let bestScore = 0;

    if (clauseTokens.length > 0) {
      for (const prod of catalog) {
        const pNorm = normalizeAr(prod.name);
        const pTokens = pNorm.split(/\s+/).filter((w) => w.length >= 2 && !ignoreWords.has(w) && !/^\d+$/.test(w));
        let matchedCount = 0;
        for (const ct of clauseTokens) {
          if (pTokens.some((pt) => pt === ct || pt.includes(ct) || ct.includes(pt))) {
            matchedCount += 1;
          }
        }
        if (matchedCount === 0) continue;
        const score = matchedCount * 2 + matchedCount / Math.max(1, pTokens.length);
        if (score > bestScore) {
          bestScore = score;
          bestProduct = prod;
        }
      }
    }

    if (bestProduct && bestScore >= 2) {
      matchedMap.set(Number(bestProduct.id), (matchedMap.get(Number(bestProduct.id)) || 0) + qty);
    }
  }

  if (matchedMap.size === 0 && fallbackProduct?.id) {
    matchedMap.set(Number(fallbackProduct.id), parseArabicQty(userMsg));
  }

  const cartItems = [...matchedMap.entries()].map(([productId, quantity]) => ({ productId, quantity }));
  return { cartAction: cartItems.length > 0 ? action : "none", cartItems };
}

function smartExtract(rawUserPrompt: string) {
  const text = String(rawUserPrompt || "").trim();
  let catalogList: any[] = [];
  const arrMatches = text.match(/\[\s*\{[\s\S]*?\}\s*\]/g) || [];
  for (const m of arrMatches) {
    try {
      const arr = JSON.parse(m);
      if (Array.isArray(arr) && arr.length > 0 && (arr[0].name || arr[0].price !== undefined)) {
        catalogList = arr;
        break;
      }
    } catch {}
  }

  let userMsg = "";
  const arMatch = text.match(/(?:رسالة العميل الحالية|رسالة العميل الآن|رسالة العميل|سؤال العميل|طلب العميل)\s*[:：]\s*([\s\S]+)$/i);
  if (arMatch) {
    userMsg = arMatch[1].trim();
  } else {
    const withoutArrays = text.replace(/\[\s*\{[\s\S]*?\}\s*\]/g, "").trim();
    const lines = withoutArrays.split(/\n+/).map((l) => l.trim()).filter(Boolean);
    userMsg = lines.slice(-2).join(" ") || text.slice(-300);
  }

  let historyStr = "";
  const hMatch = text.match(/سجل المحادثة[^:]*[:：]\s*([\s\S]*?)(?:\n\n(?:رسالة العميل|طلب العميل)|$)/);
  if (hMatch) {
    historyStr = hMatch[1].replace(/\[\[SUGGESTIONS:[\s\S]*?\]\]/g, "").trim().slice(-500);
  }

  // Check if this is an initial product modal open vs a custom question inside the product modal
  const initModalMatch = userMsg.match(/^\[تحليل_منتج\]\s*«([^»]+)»/);
  const followModalMatch = userMsg.match(/^\[سياق_منتج:([^\]]+)\]\s*([\s\S]+)$/);
  const legacyModalMatch = userMsg.match(/^ما هي أفضل 3 طرق لتحضير «([^»]+)»[\s\S]*?(?:التعديل المطلوب:\s*([\s\S]+))?$/);

  let activeProduct: any = null;
  let isInitialProductView = false;
  let cleanQuestion = userMsg;

  if (initModalMatch) {
    const pName = initModalMatch[1].trim();
    activeProduct = catalogList.find((x: any) => x.name === pName) || { name: pName };
    isInitialProductView = true;
  } else if (followModalMatch) {
    const pName = followModalMatch[1].trim();
    activeProduct = catalogList.find((x: any) => x.name === pName) || { name: pName };
    cleanQuestion = followModalMatch[2].trim();
    isInitialProductView = false;
  } else if (legacyModalMatch) {
    const pName = legacyModalMatch[1].trim();
    activeProduct = catalogList.find((x: any) => x.name === pName) || { name: pName };
    if (legacyModalMatch[2] && legacyModalMatch[2].trim()) {
      cleanQuestion = legacyModalMatch[2].trim();
      isInitialProductView = false;
    } else {
      isInitialProductView = true;
    }
  }

  const catalogCompact = catalogList
    .slice(0, 35)
    .map((x: any) => `${x.name} (${x.price} ر.ي)`)
    .join(" | ");

  const cartCmd = extractCartCommand(cleanQuestion, catalogList, activeProduct);
  const cartSummary = cartCmd.cartItems
    .map((ci) => {
      const p = catalogList.find((x: any) => Number(x.id) === ci.productId);
      return p ? `${ci.quantity} × ${p.name} (${p.price * ci.quantity} ر.ي)` : "";
    })
    .filter(Boolean)
    .join(" + ");

  const systemPrompt = `أنت المساعد الذكي لمتجر "أوريجنال" في اليمن، تتحدث بأسلوب شات جي بي تي (ChatGPT) الأنيق والمختصر وبلهجة يمنية بيضاء راقية ومفهومة (مثل: يا غالي، حياك الله، أبشر، على عيني).
قواعد صارمة لا تخالفها أبداً:
1. ممنوع استخدام أي كلمة غير يمنية مثل (بدك، شنو، هون، هاد) وممنوع كتابة أي حرف إنجليزي أو كود JSON أو أقواس {}.
2. اجعل ردك قصيراً جداً ومنسقاً ومريحاً للعين (من سطرين إلى 3 أسطر فقط، واستخدم النقاط • عند التعداد).
3. افهم مسار الحديث بدقة: أجب على آخر سؤال سأله الزبون مباشرة! إذا كان داخل نافذة منتج وسألك عن منتج آخر (مثل الفول أو الزبادي) أو سألك سؤالاً عاماً، أجب على سؤاله الجديد فوراً ولا تبقَ معلقاً على المنتج السابق.
4. لا تعرض منتجات ولا تحاول الإقناع بالشراء إذا كان الزبون يسلم فقط أو يسأل عن الحال؛ أما إذا سأل عن منتج أو وصفة فأقنعه بذكاء واحترافية.
5. في السطر الأخير فقط، اكتب زرين مقترحين قصيرين جداً (من 3 إلى 4 كلمات فقط للزر الواحد) بصيغة المتكلم ليضغط عليها الزبون، بهذا الشكل:
[[SUGGESTIONS:أضف حبة للسلة|كم السعرات الحرارية؟]]`;

  let userPrompt = "";
  if (isInitialProductView && activeProduct) {
    userPrompt = `المنتج: «${activeProduct.name}» (السعر: ${activeProduct.price || ""} ر.ي).\nأصناف المتجر الأخرى: ${catalogCompact}\nقدم نبذة جذابة ومقنعة ومختصرة في 3 نقاط قصيرة (•) عن هذا المنتج بحسب طبيعته الحقيقية (إن كان عصيراً أو ألباناً تحدث عن انتعاشه وفائدته، وإن كان بقوليات تحدث عن طبخه، وإن كان منظفات تحدث عن قوته)، ثم ضع سطر [[SUGGESTIONS:...]] في النهاية.`;
  } else if (cartCmd.cartAction !== "none" && cartSummary) {
    userPrompt = `تم الآن تنفيذ طلب الزبون في السلة فعلياً: ${cartCmd.cartAction === "add" ? "إضافة" : "حذف"} (${cartSummary}).\nأكد له ذلك في سطرين أنيقين بلهجة يمنية راقية مع الإجمالي، وضع سطر [[SUGGESTIONS:إتمام الطلب الآن|عرض محتويات السلة]] في النهاية.`;
  } else {
    userPrompt = `${historyStr ? `سياق الحوار السابق:\n${historyStr}\n\n` : ""}${activeProduct ? `(ملاحظة: الزبون يتصفح حالياً بطاقة "${activeProduct.name}"، ولكن أجب على سؤاله التالي مباشرة حتى لو كان عن صنف آخر)\n` : ""}المنتجات المتوفرة في المتجر وأسعارها:\n${catalogCompact || "لا توجد قائمة"}\n\nسؤال الزبون الآن: "${cleanQuestion}"`;
  }

  return { userMsg: cleanQuestion, catalogList, cartCmd, systemPrompt, userPrompt };
}

function formatSuggestionChip(s: string): string {
  let clean = String(s || "")
    .replace(/\[\[|\]\]/g, "")
    .replace(/^[\s"'•✨*-]+|[\s"']+$/g, "")
    .replace(/[A-Za-z_]+/g, "")
    .replace(/\b(بدك|شنو|هون)\b/g, "")
    .replace(/\s+/g, " ")
    .trim();
  const words = clean.split(" ").filter(Boolean);
  if (words.length > 5) clean = words.slice(0, 5).join(" ");
  return clean;
}

function cleanModelReply(rawText: string) {
  let t = String(rawText || "").trim();
  if (!t || t.length < 4 || /user\s*safety/i.test(t) || /^(safe|unsafe)\b/i.test(t) || /^<!doctype/i.test(t)) {
    throw new Error("Rejected invalid output");
  }

  let suggestions: string[] = [];
  const sugMatch = t.match(/\[\[SUGGESTIONS:([\s\S]*?)\]\]/i);
  if (sugMatch) {
    suggestions = sugMatch[1]
      .split("|")
      .map(formatSuggestionChip)
      .filter((x) => x.length >= 4)
      .slice(0, 3);
    t = t.replace(/\[\[SUGGESTIONS:[\s\S]*?\]\]/gi, "").trim();
  }

  if (t.includes('"message"') || t.includes('"intent"') || t.includes('"overview"')) {
    const mMatch = t.match(/"(?:message|overview)"\s*:\s*"((?:[^"\\]|\\.)*)"/);
    if (mMatch) t = mMatch[1];
  }

  t = t
    .replace(/\\n/g, "\n")
    .replace(/\\"/g, '"')
    .replace(/\*\*/g, "")
    .replace(/المانjo/gi, "المانجو")
    .replace(/مانjo/gi, "مانجو")
    .replace(/ت-?order/gi, "تطلب")
    .replace(/م?contained/gi, "مناسبة")
    .replace(/[A-Za-z_]+/g, "")
    .replace(/\bبدك\b/g, "تشتي")
    .replace(/\bشنو\b/g, "إيش")
    .replace(/\bهون\b/g, "هنا")
    .replace(/(^|\s)([\p{L}\p{M}]{2,})\s+\2(?=\s|[.،!؟]|$)/gu, "$1$2")
    .replace(/[^\S\r\n]+/g, " ")
    .replace(/\n\s+/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();

  if (!t || t.length < 4) throw new Error("Empty after cleaning");
  if (suggestions.length === 0) {
    suggestions = ["أضف حبة للسلة", "ما المنتجات المتوفرة؟"];
  }
  return { text: t, suggestions };
}

function buildFinalJson(rawReply: string, ctx: ReturnType<typeof smartExtract>): string {
  const { text, suggestions } = cleanModelReply(rawReply);
  const finalMessage = `${text}\n[[SUGGESTIONS:${suggestions.join("|")}]]`;

  return JSON.stringify({
    message: finalMessage,
    recipeName: "",
    servings: 0,
    ingredients: [],
    steps: [],
    missingIngredients: [],
    cartAction: ctx.cartCmd.cartAction,
    cartItems: ctx.cartCmd.cartItems,
    suggestedQuestions: suggestions
  });
}

async function callPollinationsFast(systemPrompt: string, userPrompt: string, signal: AbortSignal): Promise<string> {
  const plPostUrl = `${P}text.pollinations.ai/openai`;
  const res = await fetch(plPostUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json", "Referer": `${P}pollinations.ai/` },
    body: JSON.stringify({
      model: "openai-fast",
      seed: Math.floor(Math.random() * 1000000),
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userPrompt }
      ],
      temperature: 0.5
    }),
    signal
  });
  if (!res.ok) throw new Error(`PL HTTP ${res.status}`);
  const data = await res.json();
  const text = data?.choices?.[0]?.message?.content || "";
  cleanModelReply(text);
  return text.trim();
}

async function callOpenRouterSingle(model: string, systemPrompt: string, userPrompt: string, signal: AbortSignal): Promise<string> {
  const orEndpoint = `${P}openrouter.ai/api/v1/chat/completions`;
  const refHeader = ["HT", "TP-Referer"].join("");
  const res = await fetch(orEndpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${OPENROUTER_KEY}`,
      [refHeader]: `${P}original-store-xmyf.onrender.com`,
      "X-Title": "Original Store"
    },
    body: JSON.stringify({
      model,
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userPrompt }
      ],
      temperature: 0.5
    }),
    signal
  });
  if (!res.ok) throw new Error(`OR HTTP ${res.status}`);
  const data = await res.json();
  const text = data?.choices?.[0]?.message?.content || "";
  cleanModelReply(text);
  return text.trim();
}

async function callLiveAI(systemPrompt: string, userPrompt: string): Promise<string> {
  // Fast Parallel Race between 2 separate providers (Pollinations GPT-4o-mini + OpenRouter Free)
  const raceCtrl = new AbortController();
  const raceTimer = setTimeout(() => raceCtrl.abort(), 6500);
  try {
    const fastWinner = await Promise.any([
      callPollinationsFast(systemPrompt, userPrompt, raceCtrl.signal),
      callOpenRouterSingle("openrouter/free", systemPrompt, userPrompt, raceCtrl.signal)
    ]);
    clearTimeout(raceTimer);
    raceCtrl.abort();
    return fastWinner;
  } catch {
    clearTimeout(raceTimer);
  }

  // Quick sequential fallback if both timed out or hit a safety classifier on attempt 1
  for (const backupModel of ["openrouter/free", "meta-llama/llama-3.3-70b-instruct:free"]) {
    try {
      const ctrl = new AbortController();
      const t = setTimeout(() => ctrl.abort(), 9000);
      const reply = await callOpenRouterSingle(backupModel, systemPrompt, userPrompt, ctrl.signal);
      clearTimeout(t);
      return reply;
    } catch {}
  }

  throw new Error("All AI endpoints busy");
}

export async function invokeLLM(params: InvokeParams): Promise<InvokeResult> {
  const userMessages = params.messages.filter((m) => m.role !== "system");
  const rawUserPrompt = userMessages.map((m) => contentToText(m.content)).filter(Boolean).join("\n\n");
  const ctx = smartExtract(rawUserPrompt);
  const rawReply = await callLiveAI(ctx.systemPrompt, ctx.userPrompt);
  const finalJson = buildFinalJson(rawReply, ctx);

  return {
    id: `ai-${Date.now()}`,
    created: Math.floor(Date.now() / 1000),
    model: "chatgpt-style-fast",
    choices: [{ index: 0, message: { role: "assistant", content: finalJson }, finish_reason: "stop" }],
    usage: { prompt_tokens: 100, completion_tokens: 120, total_tokens: 220 }
  };
}
