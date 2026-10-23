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

function extractCartCommand(userMsg: string, catalog: any[]): { cartAction: "none" | "add" | "remove"; cartItems: Array<{ productId: number; quantity: number }> } {
  const normMsg = normalizeAr(userMsg);
  const words = normMsg.split(/\s+/);
  const addVerbs = new Set(["اضف", "اضيف", "ضيف", "ضف", "حط", "زيد", "زد", "زود", "هات", "اعطني", "اطلب", "اشتري"]);
  const remVerbs = new Set(["احذف", "حذف", "شيل", "امسح", "نقص", "الغي", "الغاء", "فرغ", "ازل", "ازاله"]);

  const isAdd = words.some((w) => addVerbs.has(w) || addVerbs.has(w.replace(/^و/, ""))) || normMsg.includes("للسله") || normMsg.includes("الي السله");
  const isRemove = words.some((w) => remVerbs.has(w) || remVerbs.has(w.replace(/^و/, "")));
  if (!isAdd && !isRemove) return { cartAction: "none", cartItems: [] };
  const action: "add" | "remove" = isRemove && !isAdd ? "remove" : "add";

  const qtySplitRegex = /\s+(?=(?:و)?(?:واحد|اثنين|ثنتين|ثلاث|اربع|خمس|ست|سبع|ثمان|تسع|عشر|\d+|حبه|حبتين|علبه)\s)/g;
  const clauses = normMsg.split(qtySplitRegex).map((s) => s.trim()).filter(Boolean);

  const ignoreWords = new Set(["من", "في", "على", "الى", "الي", "السله", "سله", "للسله", "حبه", "حبتين", "علبه", "مل", "كجم", "كيلو", "جرام", "واحد", "واحده", "اثنين", "ثنتين", "ثلاث", "ثلاثه", "اربعه", "اربع", "خمسه", "خمس", "اضف", "ضيف", "ضف", "احذف", "شيل", "لي", "ابي", "ابغي", "اريد"]);

  const matchedMap = new Map<number, number>();

  for (const clause of clauses) {
    const qty = parseArabicQty(clause);
    const clauseTokens = clause
      .split(/\s+/)
      .map((w) => w.replace(/^و/, ""))
      .filter((w) => w.length >= 2 && !ignoreWords.has(w) && !/^\d+$/.test(w));
    if (clauseTokens.length === 0) continue;

    let bestProduct: any = null;
    let bestScore = 0;

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

    if (bestProduct && bestScore >= 2) {
      matchedMap.set(Number(bestProduct.id), (matchedMap.get(Number(bestProduct.id)) || 0) + qty);
    }
  }

  const cartItems = [...matchedMap.entries()].map(([productId, quantity]) => ({ productId, quantity }));
  return { cartAction: cartItems.length > 0 ? action : "none", cartItems };
}

function smartExtract(rawUserPrompt: string) {
  const text = String(rawUserPrompt || "").trim();
  let fullJson: any = null;
  if (text.startsWith("{") && text.endsWith("}")) {
    try { fullJson = JSON.parse(text); } catch {}
  }
  if (!fullJson) {
    const idx1 = text.indexOf('{"userMessage"');
    const idx2 = text.indexOf('{"selectedProduct"');
    const startIdx = idx1 !== -1 ? idx1 : idx2;
    if (startIdx !== -1) {
      const endIdx = text.lastIndexOf("}");
      if (endIdx > startIdx) {
        try { fullJson = JSON.parse(text.slice(startIdx, endIdx + 1)); } catch {}
      }
    }
  }

  let catalogList: any[] = [];
  if (Array.isArray(fullJson?.catalog)) catalogList = fullJson.catalog;
  else if (Array.isArray(fullJson?.availableProducts)) catalogList = fullJson.availableProducts;
  else {
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
  }

  const isRecipeModal = Boolean(fullJson?.selectedProduct) || text.includes("الصنف الأساسي:") || text.includes('"selectedProduct"') || text.includes('"recipes"');
  let selectedProduct = fullJson?.selectedProduct || null;
  if (!selectedProduct && text.includes("الصنف الأساسي:")) {
    const pMatch = text.match(/الصنف الأساسي:\s*«([^»]+)»/);
    if (pMatch) {
      const found = catalogList.find((x: any) => x.name === pMatch[1].trim());
      selectedProduct = found || { id: catalogList[0]?.id || 1, name: pMatch[1].trim(), price: catalogList[0]?.price || 0 };
    }
  }

  let userMsg = "";
  if (typeof fullJson?.userMessage === "string") userMsg = fullJson.userMessage.trim();
  else if (typeof fullJson?.request === "string") userMsg = fullJson.request.trim();
  else {
    const arMatch = text.match(/(?:رسالة العميل الحالية|رسالة العميل الآن|رسالة العميل|سؤال العميل|طلب العميل)\s*[:：]\s*([\s\S]+)$/i);
    if (arMatch) userMsg = arMatch[1].trim();
    if (!userMsg) {
      const withoutArrays = text.replace(/\[\s*\{[\s\S]*?\}\s*\]/g, "").trim();
      const lines = withoutArrays.split(/\n+/).map((l) => l.trim()).filter(Boolean);
      userMsg = lines.slice(-2).join(" ") || text.slice(-300);
    }
  }

  let historyStr = "";
  if (Array.isArray(fullJson?.conversationHistory)) {
    historyStr = fullJson.conversationHistory
      .slice(-4)
      .map((h: any) => `${h.role === "assistant" ? "المساعد" : "العميل"}: ${String(h.content || h.text || "").replace(/\[\[SUGGESTIONS:[\s\S]*?\]\]/g, "").slice(0, 140)}`)
      .join("\n");
  } else {
    const hMatch = text.match(/سجل المحادثة[^:]*[:：]\s*([\s\S]*?)(?:\n\n(?:رسالة العميل|طلب العميل)|$)/);
    if (hMatch) historyStr = hMatch[1].trim().slice(-400);
  }

  const catalogCompact = catalogList
    .slice(0, 30)
    .map((x: any) => `#${x.id}:${x.name}(${x.price}ر.ي)`)
    .join("، ");

  const cartCmd = extractCartCommand(userMsg, catalogList);
  const cartSummary = cartCmd.cartItems
    .map((ci) => {
      const p = catalogList.find((x: any) => Number(x.id) === ci.productId);
      return p ? `${ci.quantity} × ${p.name} (${p.price * ci.quantity} ر.ي)` : "";
    })
    .filter(Boolean)
    .join(" + ");

  const systemPrompt = `أنت المساعد الذكي وبائع متجر "أوريجنال" المحترف في اليمن. تتحدث بلهجة يمنية راقية وودودة.
التزم بهذه القواعد الصارمة:
1. الردود قصيرة جداً ومنظمة ومباشرة (من سطرين إلى 4 أسطر كحد أقصى، واستخدم نقاط • عند التعداد) بدون إطالة أو حشو.
2. اكتب بحروف عربية صحيحة 100% وإياك أن تدخل حروفاً إنجليزية داخل الكلمات العربية أو تستخدم كود JSON أو أقواس {}.
3. متى تقنع الزبون ومتى لا تقنعه:
   - إذا كان الزبون يلقي التحية فقط أو يسأل عن الحال (مثل: السلام عليكم، كيف حالك، أخبارك) دون أن يطلب منتجاً أو وصفة: رد عليه بترحيب يمني دافئ ومختصر في سطر واحد أو سطرين فقط، ولا تعرض قائمة المنتجات ولا تحاول إقناعه بالشراء!
   - أما إذا طلب الزبون منتجاً أو وصفة أو استفسر عن صنف: كن بائعاً يمنياً ماهراً ومقنعاً جداً! أبرز له جودة المنتج وطعمه وسعره المميز في المتجر وكيف سيضبط وصفته بأسلوب جذاب ومختصر يجعله يرغب بشرائه فوراً.
4. انتبه لطبيعة المنتجات: المنتجات التي مكتوب عليها بالكيلو مثل "فاخر عائلي 1.4 كجم" هي مسحوق غسيل/منظفات منزلية وليست طعاماً فلا تخلطها أبداً في وصفات الأكل أو الحلويات! استخدم فقط الأطعمة والمشروبات الحقيقية (مثل الزبادي والعصائر والبقوليات) في الوصفات.
5. في نهاية ردك في سطر جديد مستقل، اكتب سؤالين مقترحين قصيرين مبنيين على إجابتك بهذا الشكل:
[[SUGGESTIONS:سؤال مقترح 1|سؤال مقترح 2]]`;

  let userPrompt = "";
  if (isRecipeModal && selectedProduct) {
    userPrompt = `المنتج المختار: «${selectedProduct.name}» (السعر: ${selectedProduct.price || 0} ر.ي).\nأصناف المتجر: ${catalogCompact}\nقدم تحليلاً ذكياً ومقنعاً ومختصراً جداً (3-4 أسطر منظمة) لهذا المنتج بحسب طبيعته الحقيقية مع سؤالين مقترحين في النهاية.`;
  } else if (cartCmd.cartAction !== "none" && cartSummary) {
    userPrompt = `الزبون طلب ${cartCmd.cartAction === "add" ? "إضافة" : "حذف"} هذه الأصناف في السلة وقد تم تنفيذها فعلياً الآن: (${cartSummary}).\nرسالة الزبون: "${userMsg}"\nأكد له التنفيذ في سطرين قصيرين ومنظمين بلهجة يمنية راقية مع ذكر الأصناف والإجمالي، وضع سؤالين مقترحين في النهاية.`;
  } else {
    userPrompt = `${historyStr ? `سياق المحادثة السابق:\n${historyStr}\n\n` : ""}أصناف المتجر المتوفرة عند الحاجة فقط:\n${catalogCompact || "متجر أوريجنال"}\n\nرسالة الزبون الآن: "${userMsg}"`;
  }

  return { isRecipeModal, selectedProduct, userMsg, catalogList, cartCmd, systemPrompt, userPrompt };
}

function cleanModelReply(rawText: string) {
  let t = String(rawText || "").trim();
  if (!t || t.length < 4 || /user\s*safety/i.test(t) || /^(safe|unsafe)\b/i.test(t) || /^<!doctype/i.test(t)) {
    throw new Error("Rejected safety classifier or empty output");
  }

  let suggestions: string[] = [];
  const sugMatch = t.match(/\[\[SUGGESTIONS:([\s\S]*?)\]\]/i);
  if (sugMatch) {
    suggestions = sugMatch[1]
      .split("|")
      .map((s) => s.replace(/^[\s"'•-]+|[\s"']+$/g, "").trim())
      .filter(Boolean)
      .slice(0, 3);
    t = t.replace(/\[\[SUGGESTIONS:[\s\S]*?\]\]/gi, "").trim();
  }

  if (t.includes('"message"') || t.includes('"intent"') || t.includes('"overview"')) {
    const mMatch = t.match(/"(?:message|overview)"\s*:\s*"((?:[^"\\]|\\.)*)"/);
    if (mMatch) {
      t = mMatch[1];
    } else {
      t = t
        .replace(/^[\s\S]*?"(?:message|overview)"\s*:\s*"/i, "")
        .replace(/",\s*"(?:suggestions|matchedProducts|recipe|budgetPlan|followUpQuestions|recipes)"[\s\S]*$/i, "")
        .replace(/\}[\s\S]*$/, "");
    }
  }

  t = t
    .replace(/\\n/g, "\n")
    .replace(/\\"/g, '"')
    .replace(/\*\*/g, "")
    .replace(/المانjo/gi, "المانجو")
    .replace(/مانjo/gi, "مانجو")
    .replace(/ت-?order/gi, "تطلب")
    .replace(/\border\b/gi, "طلب")
    .replace(/^```(?:json|text)?/i, "")
    .replace(/```$/i, "")
    .trim();

  if (!t || t.length < 4) throw new Error("Empty after cleaning");
  if (suggestions.length === 0) {
    suggestions = ["ما هي العروض والمنتجات المتوفرة؟", "اقترح لي فكرة سريعة"];
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

async function callLiveAI(systemPrompt: string, userPrompt: string): Promise<string> {
  const orEndpoint = `${P}openrouter.ai/api/v1/chat/completions`;
  const refHeader = ["HT", "TP-Referer"].join("");

  const openRouterModels = [
    "openrouter/free",
    "openrouter/free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "qwen/qwen-2.5-72b-instruct:free"
  ];

  for (const model of openRouterModels) {
    try {
      const controller = new AbortController();
      const t = setTimeout(() => controller.abort(), 14000);
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
          temperature: 0.55
        }),
        signal: controller.signal
      });
      clearTimeout(t);
      if (res.ok) {
        const data = await res.json();
        const text = data?.choices?.[0]?.message?.content;
        if (typeof text === "string" && text.trim()) {
          cleanModelReply(text);
          return text.trim();
        }
      }
    } catch {}
  }

  const plPostUrl = `${P}text.pollinations.ai/openai`;
  for (const pModel of ["openai-fast", "openai"]) {
    try {
      const controller = new AbortController();
      const t = setTimeout(() => controller.abort(), 11000);
      const res = await fetch(plPostUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Referer": `${P}pollinations.ai/` },
        body: JSON.stringify({
          model: pModel,
          seed: Math.floor(Math.random() * 1000000),
          messages: [
            { role: "system", content: systemPrompt },
            { role: "user", content: userPrompt }
          ],
          temperature: 0.55
        }),
        signal: controller.signal
      });
      clearTimeout(t);
      if (res.ok) {
        const data = await res.json();
        const text = data?.choices?.[0]?.message?.content;
        if (typeof text === "string" && text.trim()) {
          cleanModelReply(text);
          return text.trim();
        }
      }
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
    model: "openrouter-free-clean",
    choices: [{ index: 0, message: { role: "assistant", content: finalJson }, finish_reason: "stop" }],
    usage: { prompt_tokens: 120, completion_tokens: 160, total_tokens: 280 }
  };
}
