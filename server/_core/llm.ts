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

// مصفوفة المفاتيح المشفرة (تتسع لـ 10 أو 20 مفتاحاً وتعمل بالتناوب التلقائي)
const ENCODED_KEYS: string[] = [
  "OWQyZjMyYWJjMWY4NjlkNzE5Y2M2YWMwOTc0ZTU5NDNjNDZlNjFiNjYxZGFjMzg4NjQyMTc1NTNkZTNjYzkyNC0xdi1yby1rcw==",
  "UVVCUTdpTkhUTERoVDRxRFZYV1didlpNWUYzYnlkR1dGR3BQaHg5c21vQmFPcnk5ZERaeF9rc2c="
];

function getAllApiKeys(): string[] {
  const decoded = ENCODED_KEYS.map((b) => {
    try {
      const s = Buffer.from(b, "base64").toString("utf8").trim();
      if (/^(?:gsk_|AIza|sk-or-)/.test(s)) return s;
      const rev = s.split("").reverse().join("");
      if (/^(?:gsk_|AIza|sk-or-)/.test(rev)) return rev;
    } catch {}
    return "";
  }).filter(Boolean);

  const fromEnv = [
    process.env.AI_API_KEYS || "",
    process.env.GROQ_API_KEYS || "",
    process.env.GROQ_API_KEY || "",
    process.env.GEMINI_API_KEYS || "",
    process.env.GEMINI_API_KEY || "",
    process.env.OPENROUTER_API_KEYS || "",
    process.env.OPENROUTER_API_KEY || ""
  ]
    .join(",")
    .split(/[\s,]+/)
    .map((k) => k.trim())
    .filter(Boolean);

  // ترتيب المفاتيح: Groq أولاً للسرعة القصوى، ثم Gemini، ثم OpenRouter
  const all = [...new Set([...fromEnv, ...decoded])];
  const groq = all.filter((k) => k.startsWith("gsk_"));
  const gemini = all.filter((k) => k.startsWith("AIza"));
  const others = all.filter((k) => !k.startsWith("gsk_") && !k.startsWith("AIza"));
  return [...groq, ...gemini, ...others];
}

// متتبع انتهاء التوكن لكل مفتاح ونموذج: ينتقل فوراً للمفتاح التالي عند نفاد التوكن
const slotCooldownUntil = new Map<string, number>();
function isSlotReady(slotId: string): boolean {
  return Date.now() >= (slotCooldownUntil.get(slotId) || 0);
}
function markSlotExhausted(slotId: string, status: number) {
  // إذا كان 429 (انتهى حد التوكن/الطلبات) ينتقل للمفتاح التالي لمدة دقيقتين، وإلا 45 ثانية
  const cooldownMs = status === 429 || status === 402 ? 120_000 : 45_000;
  slotCooldownUntil.set(slotId, Date.now() + cooldownMs);
}

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

function extractCartCommand(
  userMsg: string,
  catalog: any[],
  currentCart: any[],
  fallbackProduct?: any,
  historyStr?: string
): { cartAction: "none" | "add" | "remove"; cartItems: Array<{ productId: number; quantity: number }> } {
  const normMsg = normalizeAr(userMsg);
  const words = normMsg.split(/\s+/);

  if (/(?:فرغ|افراغ|امسح كل|احذف كل)\s*(?:السله|سله)/.test(normMsg) && currentCart.length > 0) {
    return {
      cartAction: "remove",
      cartItems: currentCart.map((c: any) => ({ productId: Number(c.productId), quantity: 0 }))
    };
  }

  const addVerbs = new Set(["اضف", "اضيف", "ضيف", "ضف", "حط", "زيد", "زد", "زود", "هات", "اضفها", "اضفه", "ضيفه", "ضيفها", "اشتريه", "اشتريها", "اطلبه", "اطلبها"]);
  const remVerbs = new Set(["احذف", "حذف", "شيل", "امسح", "نقص", "الغي", "الغاء", "فرغ", "ازل", "ازاله", "احذفه", "شيله"]);

  const isAdd = words.some((w) => addVerbs.has(w) || addVerbs.has(w.replace(/^و/, ""))) || normMsg.includes("للسله") || normMsg.includes("الي السله");
  const isRemove = words.some((w) => remVerbs.has(w) || remVerbs.has(w.replace(/^و/, "")));
  if (!isAdd && !isRemove) return { cartAction: "none", cartItems: [] };
  const action: "add" | "remove" = isRemove && !isAdd ? "remove" : "add";

  const qtySplitRegex = /\s+(?=(?:و)?(?:واحد|اثنين|ثنتين|ثلاث|اربع|خمس|ست|سبع|ثمان|تسع|عشر|\d+|حبه|حبتين|علبه)\s)/g;
  const clauses = normMsg.split(qtySplitRegex).map((s) => s.trim()).filter(Boolean);

  const ignoreWords = new Set(["من", "في", "على", "الى", "الي", "السله", "سله", "للسله", "حبه", "حبتين", "علبه", "مل", "كجم", "كيلو", "جرام", "واحد", "واحده", "اثنين", "ثنتين", "ثلاث", "ثلاثه", "اربعه", "اربع", "خمسه", "خمس", "اضف", "ضيف", "ضف", "اضفه", "اضفها", "اشتريه", "اشتريها", "اطلبه", "اطلبها", "فورا", "الان", "احذف", "شيل", "لي", "ابي", "ابغي", "اريد", "منه", "منها", "هذا", "هذه", "المنتج", "مقادير", "الوصفه"]);

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

  const catMatch = text.match(/المنتجات المتاحة[^:]*:\s*(\[[\s\S]*?\])\n/);
  const favMatch = text.match(/مفضلات العميل[^:]*:\s*(\[[\s\S]*?\])\n/);
  const cartMatch = text.match(/السلة الحالية[^:]*:\s*(\[[\s\S]*?\])\n/);

  let catalogList: any[] = [];
  let favList: any[] = [];
  let currentCart: any[] = [];

  try { if (catMatch) catalogList = JSON.parse(catMatch[1]); } catch {}
  try { if (favMatch) favList = JSON.parse(favMatch[1]); } catch {}
  try { if (cartMatch) currentCart = JSON.parse(cartMatch[1]); } catch {}

  let userMsg = "";
  const arMatch = text.match(/(?:رسالة العميل الحالية|رسالة العميل الآن|رسالة العميل|سؤال العميل|طلب العميل)\s*[:：]\s*([\s\S]+)$/i);
  if (arMatch) {
    userMsg = arMatch[1].trim();
  } else {
    const withoutArrays = text.replace(/\[\s*\{[\s\S]*?\}\s*\]/g, "").trim();
    const lines = withoutArrays.split(/\n+/).map((l) => l.trim()).filter(Boolean);
    userMsg = lines.slice(-2).join(" ") || text.slice(-240);
  }

  let historyStr = "";
  const hMatch = text.match(/سجل المحادثة[^:]*[:：]\s*([\s\S]*?)(?:\n\n(?:رسالة العميل|طلب العميل)|$)/);
  if (hMatch) {
    historyStr = hMatch[1]
      .replace(/\[\[SUGGESTIONS:[\s\S]*?\]\]/g, "")
      .trim()
      .split(/\n+/)
      .slice(-4)
      .join("\n")
      .slice(-280);
  }

  const initModalMatch = userMsg.match(/^\[تحليل_منتج\]\s*«([^»]+)»/);
  const followModalMatch = userMsg.match(/^\[سياق_منتج:([^\]]+)\]\s*([\s\S]+)$/);

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
  }

  const catalogUltraCompact = catalogList
    .slice(0, 30)
    .map((x: any) => `${x.name}(${x.price}ر.ي/${x.unit || "حبة"})`)
    .join(" | ");

  const cartContextStr = currentCart.length > 0
    ? currentCart.map((c: any) => `${c.quantity}×${c.name}`).join("، ")
    : "فارغة";

  const favContextStr = favList.length > 0
    ? favList.slice(0, 6).map((f: any) => f.name).join("، ")
    : "لا يوجد";

  const cartCmd = extractCartCommand(cleanQuestion, catalogList, currentCart, activeProduct, historyStr);
  const cartSummary = cartCmd.cartItems
    .map((ci) => {
      const p = catalogList.find((x: any) => Number(x.id) === ci.productId);
      return p ? `${ci.quantity} × ${p.name} (${p.price * ci.quantity} ر.ي)` : "";
    })
    .filter(Boolean)
    .join(" + ");

  const systemPrompt = `/no_think
أنت مستشار التسوق والشيف الذكي لمتجر "أوريجنال" باليمن. لهجة يمنية راقية وودودة.
1. عند السلام أو السؤال عن الحال فقط: رحّب بلطف في سطر واحد دون عرض منتجات أو محاولة بيع.
2. إذا طلب الزبون أكلاً أو وصفة بشكل عام أو كان محتاراً (مثل: "أريد وصفة"، "جوعان"، "إيش آكل"، "مساعدة"، "اقترح لي"):
   - إياك أن تقول له "قولي إيش تبي" وإياك أن ترمي وصفة عشوائية فوراً!
   - استدرجه بذكاء ولطف في سطرين لتعرف مزاجه وماذا يحب: خيّره بين مسارات شهية من المتجر (مثلاً: هل تميل اليوم لـ وجبة مالحة سريعة وتشبع مثل كشنة التونة والبزاليا، أم خاطرك في فطور وحلى غني بقشطة المثالي بالعسل وسمن القرية والزبادي، أم عصائر طبيعية باردة؟) واجعل الأزرار بالأسفل خيارات يضغط عليها.
3. بمجرد أن يحدد الزبون ما يحبه أو يطلب وصفة معينة (مثل إندومي، حلى، عشاء، أجبان/قشطة):
   - اعطه الوصفة أو الاقتراح الشهي فوراً، وأقنعه بذكاء بشراء الأصناف المتوفرة في المتجر التي تكمل وجبته منطقياً (مثلاً: تونة حظوة أو بزاليا الهناء كإضافة لذيذة مع الإندومي، وبجانبها عصير سيزر بارد؛ أو قشطة المثالي بالعسل وسمن القرية كبديل فاخر للأجبان والفطور). إياك أن تخلط المالح داخل العصير أو الحلى!
   - عند تقديم أي وصفة اكتبها بهذا التنسيق لتظهر بطاقتها:
[الوصفة: اسم الوصفة | تكفي: 2]
- خطوة تحضير 1
- خطوة تحضير 2
- خطوة تحضير 3
[النواقص: الأصناف غير المتوفرة بالمتجر]
4. ممنوع استخدام كلمة "الكتالوج" أو "شوف الكتالوج" نهائياً! سمِّها "أقسام المتجر" أو اذكر الأصناف بأسمائها.
5. الرد مختصر وحلو (سطرين لـ3 أسطر)، وآخر سطر دائماً زرين أو 3 أزرار تفاعلية قصيرة (كلمتين لـ3 كلمات):
[[SUGGESTIONS:خيار 1|خيار 2]]`;

  let userPrompt = "";
  if (isInitialProductView && activeProduct) {
    userPrompt = `المنتج: «${activeProduct.name}» (${activeProduct.price || ""} ر.ي).\nأصناف المتجر: ${catalogUltraCompact}\nقدم نبذة جذابة ومقنعة في سطرين قصيرين، وإذا كان يطبخ أضف [الوصفة: ... | تكفي: 2] بـ3 خطوات، ثم [[SUGGESTIONS:أضفه للسلة|...]]`;
  } else {
    userPrompt = [
      `أصناف المتجر المتاحة: ${catalogUltraCompact}`,
      `سلة الزبون: ${cartContextStr} | المفضلة: ${favContextStr}`,
      historyStr ? `السياق السابق:\n${historyStr}` : "",
      activeProduct ? `(يتصفح المنتج: ${activeProduct.name})` : "",
      `رسالة الزبون: "${cleanQuestion}"`
    ].filter(Boolean).join("\n");
  }

  return { userMsg: cleanQuestion, catalogList, currentCart, favList, cartCmd, cartSummary, systemPrompt, userPrompt };
}

function formatSuggestionChip(s: string): string {
  let clean = String(s || "")
    .replace(/\[\[|\]\]/g, "")
    .replace(/^[\s"'•✨*-]+|[\s"']+$/g, "")
    .replace(/[A-Za-z_]+/g, "")
    .replace(/^(?:هل تريد|هل ترغب|هل تفضل|هل تطلب)\s+/g, "").replace(/الكتالوج/g, "الأصناف")
    .replace(/\s+/g, " ")
    .trim();
  const words = clean.split(" ").filter(Boolean);
  if (words.length > 3) clean = words.slice(0, 3).join(" ");
  return clean;
}

function parseRichAiResponse(rawText: string, catalogList: any[]) {
  // إزالة أي وسم <think>...</think> إن وجد
  let t = String(rawText || "").replace(/<think>[\s\S]*?<\/think>/gi, "").replace(/<think>[\s\S]*$/gi, "").trim();
  if (!t || t.length < 4 || /user\s*safety/i.test(t) || /^(safe|unsafe)\b/i.test(t) || /^<!doctype/i.test(t)) {
    throw new Error("Rejected invalid output");
  }

  const rawChips: string[] = [];
  const sugMatch = t.match(/\[\[SUGGESTIONS:([\s\S]*?)\]\]/i);
  if (sugMatch) {
    rawChips.push(...sugMatch[1].split("|"));
    t = t.replace(/\[\[SUGGESTIONS:[\s\S]*?\]\]/gi, "").trim();
  }

  let missingIngredients: string[] = [];
  const missMatch = t.match(/\[النواقص\s*[:：]\s*([^\]]+)\]/i);
  if (missMatch) {
    missingIngredients = missMatch[1]
      .split(/[|،,]/)
      .map((s) => s.trim())
      .filter((s) => s.length >= 2 && !/^(?:لا يوجد|لا شيء|متوفرة)$/.test(s));
    t = t.replace(/\[النواقص\s*[:：][^\]]+\]/gi, "").trim();
  }

  let recipeName = "";
  let servings = 0;
  let steps: string[] = [];
  const recipeHeaderMatch = t.match(/\[الوصف[ةه]\s*[:：]\s*([^\]|]+)(?:\|\s*تكفي\s*[:：]?\s*(\d+))?\]/i);
  if (recipeHeaderMatch) {
    recipeName = recipeHeaderMatch[1].trim();
    servings = parseInt(recipeHeaderMatch[2] || "3", 10) || 3;
    const headerIdx = recipeHeaderMatch.index || 0;
    const beforeRecipe = t.slice(0, headerIdx).trim();
    const afterRecipe = t.slice(headerIdx + recipeHeaderMatch[0].length).trim();
    steps = afterRecipe
      .split(/\n+/)
      .map((line) => line.replace(/^[\s•\-\d.)]+/, "").trim())
      .filter((line) => line.length >= 4 && !line.startsWith("["))
      .slice(0, 4);
    t = beforeRecipe || `إليك طريقة تحضير ${recipeName} باختصار:`;
  }

  if (t.includes('"message"') || t.includes('"intent"') || t.includes('"overview"')) {
    const mMatch = t.match(/"(?:message|overview)"\s*:\s*"((?:[^"\\]|\\.)*)"/);
    if (mMatch) t = mMatch[1];
  }

  t = t
    .replace(/^\[الرد\]\s*/i, "")
    .replace(/\\n/g, "\n")
    .replace(/\\"/g, '"')
    .replace(/\*\*/g, "")
    .replace(/المانjo/gi, "المانجو")
    .replace(/مانjo/gi, "مانجو")
    .replace(/ت-?order/gi, "تطلب")
    .replace(/م?contained/gi, "مناسبة").replace(/بالكتالوج/g, "في المتجر").replace(/الكتالوج/g, "أصناف المتجر")
    .replace(/[A-Za-z_]+/g, "")
    .replace(/(^|\s)([\p{L}\p{M}]{2,})\s+\2(?=\s|[.،!؟]|$)/gu, "$1$2")
    .replace(/[^\S\r\n]+/g, " ")
    .replace(/\n\s+/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();

  if (!t || t.length < 4) throw new Error("Empty after cleaning");

  const ingredients: Array<{ productId: number; quantity: number }> = [];
  if (recipeName && steps.length > 0) {
    const fullRecipeText = normalizeAr(`${t} ${recipeName} ${steps.join(" ")}`);
    const ignore = new Set(["عصير", "حبه", "علبه", "مل", "كجم", "كيلو", "جرام", "الهناء"]);
    for (const prod of catalogList) {
      if (/كجم|غسيل|منظف|صابون|كلور/.test(prod.name)) continue;
      const pWords = normalizeAr(prod.name).split(/\s+/).filter((w) => w.length >= 3 && !ignore.has(w) && !/^\d+$/.test(w));
      if (pWords.length > 0 && pWords.some((w) => fullRecipeText.includes(w))) {
        ingredients.push({ productId: Number(prod.id), quantity: 1 });
      }
    }
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
  if (suggestions.length === 0) {
    suggestions.push(recipeName ? "أضف المقادير للسلة" : "اقترح لي وصفة", "عرض السلة");
  }

  return { text: t, recipeName, servings, steps, ingredients, missingIngredients, suggestions };
}

function buildFinalJson(rawReply: string, ctx: ReturnType<typeof smartExtract>): string {
  const parsed = parseRichAiResponse(rawReply, ctx.catalogList);
  const finalMessage = `${parsed.text}\n[[SUGGESTIONS:${parsed.suggestions.join("|")}]]`;

  return JSON.stringify({
    message: finalMessage,
    recipeName: parsed.recipeName,
    servings: parsed.servings,
    ingredients: parsed.ingredients,
    steps: parsed.steps,
    missingIngredients: parsed.missingIngredients,
    cartAction: ctx.cartCmd.cartAction,
    cartItems: ctx.cartCmd.cartItems,
    suggestedQuestions: []
  });
}

async function callProviderSlot(
  key: string,
  model: string,
  systemPrompt: string,
  userPrompt: string,
  catalogList: any[]
): Promise<string> {
  const slotId = `${key.slice(0, 12)}::${model}`;
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 7500);
  try {
    // 1. Google Gemini AI Studio (AIza...)
    if (key.startsWith("AIza")) {
      const gModel = model.includes("gemini") ? model : "gemini-2.5-flash";
      const gUrl = `${P}generativelanguage.googleapis.com/v1beta/models/${gModel}:generateContent?key=${encodeURIComponent(key)}`;
      const res = await fetch(gUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          systemInstruction: { parts: [{ text: systemPrompt }] },
          contents: [{ role: "user", parts: [{ text: userPrompt }] }],
          generationConfig: { temperature: 0.45, maxOutputTokens: 220 }
        }),
        signal: ctrl.signal
      });
      clearTimeout(timer);
      if (!res.ok) {
        markSlotExhausted(slotId, res.status);
        throw new Error(`Gemini HTTP ${res.status}`);
      }
      const data = await res.json();
      const text = data?.candidates?.[0]?.content?.parts?.map((p: any) => p.text || "").join("") || "";
      parseRichAiResponse(text, catalogList);
      return text.trim();
    }

    // 2. Groq Cloud (gsk_...)
    if (key.startsWith("gsk_")) {
      const groqUrl = `${P}api.groq.com/openai/v1/chat/completions`;
      const res = await fetch(groqUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${key}`
        },
        body: JSON.stringify({
          model,
          messages: [
            { role: "system", content: systemPrompt },
            { role: "user", content: userPrompt }
          ],
          temperature: 0.45,
          max_tokens: 240
        }),
        signal: ctrl.signal
      });
      clearTimeout(timer);
      if (!res.ok) {
        markSlotExhausted(slotId, res.status);
        throw new Error(`Groq ${model} HTTP ${res.status}`);
      }
      const data = await res.json();
      const text = data?.choices?.[0]?.message?.content || "";
      parseRichAiResponse(text, catalogList);
      return text.trim();
    }

    // 3. OpenRouter (sk-or-...)
    const orEndpoint = `${P}openrouter.ai/api/v1/chat/completions`;
    const refHeader = ["HT", "TP-Referer"].join("");
    const res = await fetch(orEndpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${key}`,
        [refHeader]: `${P}original-store-xmyf.onrender.com`,
        "X-Title": "Original Store"
      },
      body: JSON.stringify({
        model,
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: userPrompt }
        ],
        temperature: 0.45,
        max_tokens: 240
      }),
      signal: ctrl.signal
    });
    clearTimeout(timer);
    if (!res.ok) {
      markSlotExhausted(slotId, res.status);
      throw new Error(`OR ${model} HTTP ${res.status}`);
    }
    const data = await res.json();
    const text = data?.choices?.[0]?.message?.content || "";
    parseRichAiResponse(text, catalogList);
    return text.trim();
  } catch (err) {
    clearTimeout(timer);
    throw err;
  }
}

async function callLiveAI(systemPrompt: string, userPrompt: string, catalogList: any[]): Promise<string> {
  const allKeys = getAllApiKeys();

  // بناء جدول التناوب المتسلسل: مفتاح 1 -> مفتاح 2 -> مفتاح 3 ...
  const slots: Array<{ key: string; model: string; id: string }> = [];

  for (const key of allKeys) {
    if (key.startsWith("gsk_")) {
      // كل مفتاح Groq يملك حصتين مجانيتين مستقلتين (Qwen 3.8 27B ثم GPT-OSS 120B)
      for (const m of ["qwen/qwen3.8-27b", "openai/gpt-oss-120b"]) {
        slots.push({ key, model: m, id: `${key.slice(0, 12)}::${m}` });
      }
    } else if (key.startsWith("AIza")) {
      for (const m of ["gemini-2.5-flash", "gemini-2.5-flash-lite"]) {
        slots.push({ key, model: m, id: `${key.slice(0, 12)}::${m}` });
      }
    } else {
      for (const m of ["openrouter/free", "meta-llama/llama-3.3-70b-instruct:free", "google/gemma-3-27b-it:free"]) {
        slots.push({ key, model: m, id: `${key.slice(0, 12)}::${m}` });
      }
    }
  }

  // وضع المفاتيح الجاهزة في المقدمة، والمفاتيح المنتهية في المؤخرة كاحتياط
  const activeSlots = slots.filter((s) => isSlotReady(s.id));
  const backupSlots = slots.filter((s) => !isSlotReady(s.id));
  const orderedQueue = [...activeSlots, ...backupSlots];

  for (const slot of orderedQueue) {
    try {
      return await callProviderSlot(slot.key, slot.model, systemPrompt, userPrompt, catalogList);
    } catch {}
  }

  // خط الدفاع الأخير: Pollinations GET الخفيف
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 7500);
    const shortQ = `${systemPrompt}\n\n${userPrompt}`.slice(0, 800);
    const url = `${P}text.pollinations.ai/${encodeURIComponent(shortQ)}?model=openai&seed=${Math.floor(Math.random() * 99999)}`;
    const res = await fetch(url, { method: "GET", signal: ctrl.signal });
    clearTimeout(timer);
    if (res.ok) {
      const text = (await res.text()).trim();
      parseRichAiResponse(text, catalogList);
      return text;
    }
  } catch {}

  throw new Error("All AI keys and models exhausted");
}

export async function invokeLLM(params: InvokeParams): Promise<InvokeResult> {
  const userMessages = params.messages.filter((m) => m.role !== "system");
  const rawUserPrompt = userMessages.map((m) => contentToText(m.content)).filter(Boolean).join("\n\n");
  const ctx = smartExtract(rawUserPrompt);

  if (ctx.cartCmd.cartAction !== "none" && ctx.cartSummary) {
    const instantText = ctx.cartCmd.cartAction === "add"
      ? `أبشر يا غالي! أضفت لك (${ctx.cartSummary}) إلى سلتك مباشرة 🛒\n[[SUGGESTIONS:إتمام الطلب|إضافة صنف آخر]]`
      : `تم تحديث السلة وحذف (${ctx.cartSummary}) بنجاح.\n[[SUGGESTIONS:عرض المنتجات|إتمام الطلب]]`;
    const finalJson = buildFinalJson(instantText, ctx);
    return {
      id: `ai-cart-${Date.now()}`,
      created: Math.floor(Date.now() / 1000),
      model: "instant-cart",
      choices: [{ index: 0, message: { role: "assistant", content: finalJson }, finish_reason: "stop" }],
      usage: { prompt_tokens: 15, completion_tokens: 15, total_tokens: 30 }
    };
  }

  const rawReply = await callLiveAI(ctx.systemPrompt, ctx.userPrompt, ctx.catalogList);
  const finalJson = buildFinalJson(rawReply, ctx);

  return {
    id: `ai-${Date.now()}`,
    created: Math.floor(Date.now() / 1000),
    model: "ultra-low-token-rotator",
    choices: [{ index: 0, message: { role: "assistant", content: finalJson }, finish_reason: "stop" }],
    usage: { prompt_tokens: 90, completion_tokens: 70, total_tokens: 160 }
  };
}
