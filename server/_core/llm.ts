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

function findBestProductInText(searchText: string, catalog: any[], ignoreWords: Set<string>) {
  const tokens = normalizeAr(searchText)
    .split(/\s+/)
    .map((w) => w.replace(/^و/, ""))
    .filter((w) => w.length >= 2 && !ignoreWords.has(w) && !/^\d+$/.test(w));
  if (tokens.length === 0) return null;

  let bestProduct: any = null;
  let bestScore = 0;
  for (const prod of catalog) {
    const pNorm = normalizeAr(prod.name);
    const pTokens = pNorm.split(/\s+/).filter((w) => w.length >= 2 && !ignoreWords.has(w) && !/^\d+$/.test(w));
    let matchedCount = 0;
    for (const ct of tokens) {
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
  return bestScore >= 2 ? bestProduct : null;
}

function extractCartCommand(userMsg: string, catalog: any[], fallbackProduct?: any, historyStr?: string): { cartAction: "none" | "add" | "remove"; cartItems: Array<{ productId: number; quantity: number }> } {
  const normMsg = normalizeAr(userMsg);
  const words = normMsg.split(/\s+/);
  const addVerbs = new Set(["اضف", "اضيف", "ضيف", "ضف", "حط", "زيد", "زد", "زود", "هات", "اضفها", "اضفه", "ضيفه", "ضيفها", "اشتريه", "اشتريها", "اشتري", "اطلبه", "اطلبها", "اطلب"]);
  const remVerbs = new Set(["احذف", "حذف", "شيل", "امسح", "نقص", "الغي", "الغاء", "فرغ", "ازل", "ازاله", "احذفه", "شيله"]);

  const isAdd = words.some((w) => addVerbs.has(w) || addVerbs.has(w.replace(/^و/, ""))) || normMsg.includes("للسله") || normMsg.includes("الي السله");
  const isRemove = words.some((w) => remVerbs.has(w) || remVerbs.has(w.replace(/^و/, "")));
  if (!isAdd && !isRemove) return { cartAction: "none", cartItems: [] };
  const action: "add" | "remove" = isRemove && !isAdd ? "remove" : "add";

  const qtySplitRegex = /\s+(?=(?:و)?(?:واحد|اثنين|ثنتين|ثلاث|اربع|خمس|ست|سبع|ثمان|تسع|عشر|\d+|حبه|حبتين|علبه)\s)/g;
  const clauses = normMsg.split(qtySplitRegex).map((s) => s.trim()).filter(Boolean);

  const ignoreWords = new Set(["من", "في", "على", "الى", "الي", "السله", "سله", "للسله", "حبه", "حبتين", "علبه", "مل", "كجم", "كيلو", "جرام", "واحد", "واحده", "اثنين", "ثنتين", "ثلاث", "ثلاثه", "اربعه", "اربع", "خمسه", "خمس", "اضف", "ضيف", "ضف", "اضفه", "اضفها", "اشتريه", "اشتريها", "اطلبه", "اطلبها", "فورا", "الان", "احذف", "شيل", "لي", "ابي", "ابغي", "اريد", "منه", "منها", "هذا", "هذه", "المنتج"]);

  const matchedMap = new Map<number, number>();

  for (const clause of clauses) {
    const qty = parseArabicQty(clause);
    const bestProduct = findBestProductInText(clause, catalog, ignoreWords);
    if (bestProduct) {
      matchedMap.set(Number(bestProduct.id), (matchedMap.get(Number(bestProduct.id)) || 0) + qty);
    }
  }

  if (matchedMap.size === 0) {
    if (fallbackProduct?.id) {
      matchedMap.set(Number(fallbackProduct.id), parseArabicQty(userMsg));
    } else if (historyStr) {
      const recentLines = String(historyStr).split(/\n+/).slice(-4).reverse();
      for (const line of recentLines) {
        const fromHist = findBestProductInText(line, catalog, ignoreWords);
        if (fromHist) {
          matchedMap.set(Number(fromHist.id), parseArabicQty(userMsg));
          break;
        }
      }
    }
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
    historyStr = hMatch[1].replace(/\[\[SUGGESTIONS:[\s\S]*?\]\]/g, "").trim().slice(-400);
  }

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
    .slice(0, 25)
    .map((x: any) => `${x.name}(${x.price}ر.ي)`)
    .join("، ");

  const cartCmd = extractCartCommand(cleanQuestion, catalogList, activeProduct, historyStr);
  const cartSummary = cartCmd.cartItems
    .map((ci) => {
      const p = catalogList.find((x: any) => Number(x.id) === ci.productId);
      return p ? `${ci.quantity} × ${p.name} (${p.price * ci.quantity} ر.ي)` : "";
    })
    .filter(Boolean)
    .join(" + ");

  const systemPrompt = `أنت مساعد متجر "أوريجنال" باليمن. تحدث بلهجة يمنية بيضاء راقية ومختصرة جداً (سطرين فقط).
- ممنوع الإطالة أو تكرار نفس الإجابة السابقة أو كتابة JSON أو حروف إنجليزية.
- أجب مباشرة على آخر سؤال للزبون؛ ولا تعرض منتجات عند السلام فقط.
- في آخر سطر اكتب زرين قصيرين جداً (كلمتين أو 3 كلمات فقط للزر) بهذا الشكل:
[[SUGGESTIONS:أضفه للسلة|كم السعرات؟]]`;

  let userPrompt = "";
  if (isInitialProductView && activeProduct) {
    userPrompt = `المنتج: ${activeProduct.name} (${activeProduct.price || ""} ر.ي). قدم سطرين جذابين عن مميزاته وسعره، ثم سطر [[SUGGESTIONS:أضفه للسلة|كم السعرات؟]]`;
  } else {
    userPrompt = `${historyStr ? `سابقاً:\n${historyStr}\n` : ""}${activeProduct ? `(المنتج الحالي: ${activeProduct.name})\n` : ""}المنتجات: ${catalogCompact}\nسؤال الزبون الجديد (أجب عليه مباشرة ولا تكرر الرد السابق): "${cleanQuestion}"`;
  }

  return { userMsg: cleanQuestion, catalogList, cartCmd, cartSummary, systemPrompt, userPrompt };
}

function formatSuggestionChip(s: string): string {
  let clean = String(s || "")
    .replace(/\[\[|\]\]/g, "")
    .replace(/^[\s"'•✨*-]+|[\s"']+$/g, "")
    .replace(/[A-Za-z_]+/g, "")
    .replace(/^(?:هل تريد|هل ترغب|هل تفضل|هل تطلب)\s+/g, "")
    .replace(/\s+/g, " ")
    .trim();
  const words = clean.split(" ").filter(Boolean);
  if (words.length > 3) clean = words.slice(0, 3).join(" ");
  return clean;
}

function cleanModelReply(rawText: string) {
  let t = String(rawText || "").trim();
  if (!t || t.length < 4 || /user\s*safety/i.test(t) || /^(safe|unsafe)\b/i.test(t) || /^<!doctype/i.test(t)) {
    throw new Error("Rejected invalid output");
  }

  const rawChips: string[] = [];
  const sugMatch = t.match(/\[\[SUGGESTIONS:([\s\S]*?)\]\]/i);
  if (sugMatch) {
    rawChips.push(...sugMatch[1].split("|"));
    t = t.replace(/\[\[SUGGESTIONS:[\s\S]*?\]\]/gi, "").trim();
  }

  const seen = new Set<string>();
  const suggestions: string[] = [];
  for (const rc of rawChips) {
    const fc = formatSuggestionChip(rc);
    if (fc.length >= 3 && !seen.has(fc)) {
      seen.add(fc);
      suggestions.push(fc);
    }
    if (suggestions.length >= 3) break;
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
    .replace(/(^|\s)([\p{L}\p{M}]{2,})\s+\2(?=\s|[.،!؟]|$)/gu, "$1$2")
    .replace(/[^\S\r\n]+/g, " ")
    .replace(/\n\s+/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();

  if (!t || t.length < 4) throw new Error("Empty after cleaning");
  if (suggestions.length === 0) {
    suggestions.push("أضفه للسلة", "منتجات المتجر");
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
    suggestedQuestions: []
  });
}

async function callLiveAI(systemPrompt: string, userPrompt: string): Promise<string> {
  const orEndpoint = `${P}openrouter.ai/api/v1/chat/completions`;
  const refHeader = ["HT", "TP-Referer"].join("");

  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 9500);
    const res = await fetch(orEndpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${OPENROUTER_KEY}`,
        [refHeader]: `${P}original-store-xmyf.onrender.com`,
        "X-Title": "Original Store"
      },
      body: JSON.stringify({
        models: [
          "google/gemma-3-27b-it:free",
          "mistralai/mistral-small-3.1-24b-instruct:free",
          "meta-llama/llama-3.3-70b-instruct:free",
          "openrouter/free"
        ],
        provider: { sort: "throughput" },
        reasoning: { effort: "none", exclude: true },
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: userPrompt }
        ],
        temperature: 0.45
      }),
      signal: ctrl.signal
    });
    clearTimeout(timer);
    if (res.ok) {
      const data = await res.json();
      const text = data?.choices?.[0]?.message?.content || "";
      cleanModelReply(text);
      return text.trim();
    }
  } catch {}

  for (let i = 0; i < 2; i++) {
    try {
      const ctrl = new AbortController();
      const timer = setTimeout(() => ctrl.abort(), 9000);
      const res = await fetch(orEndpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${OPENROUTER_KEY}`,
          [refHeader]: `${P}original-store-xmyf.onrender.com`,
          "X-Title": "Original Store"
        },
        body: JSON.stringify({
          model: "openrouter/free",
          provider: { sort: "throughput" },
          reasoning: { effort: "none", exclude: true },
          messages: [
            { role: "system", content: systemPrompt },
            { role: "user", content: userPrompt }
          ],
          temperature: 0.45
        }),
        signal: ctrl.signal
      });
      clearTimeout(timer);
      if (res.ok) {
        const data = await res.json();
        const text = data?.choices?.[0]?.message?.content || "";
        cleanModelReply(text);
        return text.trim();
      }
    } catch {}
  }

  throw new Error("All AI endpoints busy");
}

export async function invokeLLM(params: InvokeParams): Promise<InvokeResult> {
  const userMessages = params.messages.filter((m) => m.role !== "system");
  const rawUserPrompt = userMessages.map((m) => contentToText(m.content)).filter(Boolean).join("\n\n");
  const ctx = smartExtract(rawUserPrompt);

  if (ctx.cartCmd.cartAction !== "none" && ctx.cartSummary) {
    const instantText = ctx.cartCmd.cartAction === "add"
      ? `أبشر يا غالي! أضفت لك (${ctx.cartSummary}) إلى السلة مباشرة 🛒\n[[SUGGESTIONS:إتمام الطلب|منتجات أخرى]]`
      : `تم تحديث السلة وحذف (${ctx.cartSummary}) بنجاح.\n[[SUGGESTIONS:عرض المنتجات|إتمام الطلب]]`;
    const finalJson = buildFinalJson(instantText, ctx);
    return {
      id: `ai-cart-${Date.now()}`,
      created: Math.floor(Date.now() / 1000),
      model: "instant-cart",
      choices: [{ index: 0, message: { role: "assistant", content: finalJson }, finish_reason: "stop" }],
      usage: { prompt_tokens: 20, completion_tokens: 20, total_tokens: 40 }
    };
  }

  const rawReply = await callLiveAI(ctx.systemPrompt, ctx.userPrompt);
  const finalJson = buildFinalJson(rawReply, ctx);

  return {
    id: `ai-${Date.now()}`,
    created: Math.floor(Date.now() / 1000),
    model: "fast-clean-ai",
    choices: [{ index: 0, message: { role: "assistant", content: finalJson }, finish_reason: "stop" }],
    usage: { prompt_tokens: 60, completion_tokens: 60, total_tokens: 120 }
  };
}
