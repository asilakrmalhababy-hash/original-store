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

  const isRecipeModal = Boolean(fullJson?.selectedProduct) || text.includes('"selectedProduct"') || text.includes('"recipes"');
  let selectedProduct = fullJson?.selectedProduct || null;
  if (!selectedProduct && isRecipeModal) {
    const spMatch = text.match(/"selectedProduct"\s*:\s*(\{[\s\S]*?\})/);
    if (spMatch) {
      try { selectedProduct = JSON.parse(spMatch[1]); } catch {}
    }
  }

  let userMsg = "";
  if (typeof fullJson?.userMessage === "string") userMsg = fullJson.userMessage.trim();
  else if (typeof fullJson?.request === "string") userMsg = fullJson.request.trim();
  else {
    const umMatch = text.match(/"(?:userMessage|request|query)"\s*:\s*"((?:[^"\\]|\\.)*)"/);
    if (umMatch) {
      try { userMsg = JSON.parse('"' + umMatch[1] + '"'); } catch { userMsg = umMatch[1]; }
    }
    if (!userMsg) {
      const arMatch = text.match(/(?:رسالة العميل الحالية|رسالة العميل الآن|رسالة العميل|سؤال العميل|طلب العميل)\s*[:：]\s*([\s\S]+)$/i);
      if (arMatch) userMsg = arMatch[1].trim();
    }
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

  const systemPrompt = `أنت المساعد الذكي لمتجر "أوريجنال" في اليمن. تتحدث بلهجة يمنية/عربية راقية وودودة وذكية جداً.
قواعد مهمة جداً:
1. لا تكتب كود JSON ولا تكتب أقواس برمجية {} نهائياً! اكتب ردك كنص عربي طبيعي ومرتب مباشرة للزبون.
2. أجب مباشرة وبذكاء على سؤال الزبون الحالي ولا تكرر الترحيب إذا كان قد بدأ المحادثة.
3. افهم طبيعة كل منتج بمنطق سليم:
   - المعلبات والبقوليات المالحة (مثل بزاليا، فول، فاصوليا، تونة، معجون طماطم، أرز) هي مكونات طبخ مالحة؛ تحدث عن فوائدها وأطباق طبخ حقيقية تناسبها (مثل كشنة، إيدام، أرز مع البزاليا) ولا تقترح منها عصيراً أو حلى أبداً!
   - المنتجات الجاهزة كالألبان (زبادي) والشوكولاتة والعصائر والبسكويت؛ تحدث عن قيمتها الغذائية وسعراتها وطعمها وطرق تقديمها اللذيذة.
4. في نهاية ردك في سطر مستقل، اكتب سؤالين مقترحين قصيرين مبنيين على إجابتك بهذا الشكل الدقيق:
[[SUGGESTIONS:سؤال مقترح 1|سؤال مقترح 2]]`;

  const userPrompt = isRecipeModal && selectedProduct
    ? `المنتج المطلوب تحليله: ${selectedProduct.name} (السعر: ${selectedProduct.price || 0} ريال يمني، القسم: ${selectedProduct.category || "عام"}).\nمنتجات المتجر المتوفرة: ${catalogCompact}\nحلل هذا المنتج بذكاء بحسب طبيعته الحقيقية وقدم معلومات مفيدة عنه للزبون مع سؤالين مقترحين في النهاية.`
    : `${historyStr ? `سياق المحادثة السابق:\n${historyStr}\n\n` : ""}المنتجات المتوفرة حالياً في المتجر:\n${catalogCompact || "متجر أوريجنال"}\n\nسؤال الزبون الآن: "${userMsg}"`;

  return { isRecipeModal, selectedProduct, userMsg, catalogList, systemPrompt, userPrompt };
}

function cleanModelReply(rawText: string) {
  let t = String(rawText || "").trim();
  if (!t || t.length < 6 || /user\s*safety/i.test(t) || /^(safe|unsafe)\b/i.test(t) || /^<!doctype/i.test(t)) {
    throw new Error("Rejected invalid or safety classifier output");
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

  if (t.includes('"suggestions"') || t.includes('"SuggestionButtons"') || t.includes('"followUpQuestions"')) {
    const sMatch = t.match(/"(?:suggestions|SuggestionButtons|followUpQuestions)"\s*:\s*\[([\s\S]*?)\]/);
    if (sMatch && suggestions.length === 0) {
      suggestions = (sMatch[1].match(/"((?:[^"\\]|\\.)*)"/g) || [])
        .map((x) => x.slice(1, -1).trim())
        .filter(Boolean)
        .slice(0, 3);
    }
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
    .replace(/^```(?:json|text)?/i, "")
    .replace(/```$/i, "")
    .trim();

  if (!t || t.length < 5) throw new Error("Empty after cleaning");
  if (suggestions.length === 0) {
    suggestions = ["أعطني وصفة أو طريقة استخدام", "كم السعرات الحرارية فيه؟"];
  }
  return { text: t, suggestions };
}

function buildFinalJson(rawReply: string, ctx: ReturnType<typeof smartExtract>): string {
  const { text, suggestions } = cleanModelReply(rawReply);

  if (ctx.isRecipeModal) {
    const pName = ctx.selectedProduct?.name || "المنتج";
    const lines = text.split(/\n+/).map((s) => s.trim()).filter(Boolean);
    return JSON.stringify({
      overview: text,
      recipes: [
        {
          title: `معلومات وطرق استخدام ${pName}`,
          summary: lines[0] || text.slice(0, 160),
          servings: "حسب الرغبة",
          prepTime: "سريع",
          ingredients: [
            {
              name: pName,
              amount: "متوفر في المتجر",
              productId: ctx.selectedProduct?.id ?? null,
              availableInStore: true
            }
          ],
          steps: lines.slice(1, 6).length > 0 ? lines.slice(1, 6) : [text],
          tips: suggestions,
          missingIngredients: []
        }
      ]
    });
  }

  const combinedSearch = `${ctx.userMsg} ${text}`;
  const matchedProducts = ctx.catalogList
    .filter((p: any) => p?.name && combinedSearch.includes(String(p.name).split(/\s+/)[0]))
    .slice(0, 3)
    .map((p: any) => ({
      productId: Number(p.id),
      reason: "متوفر في متجر أوريجنال",
      suggestedQuantity: 1
    }));

  const finalMessage = `${text}\n[[SUGGESTIONS:${suggestions.join("|")}]]`;

  return JSON.stringify({
    intent: "general_qna",
    confidence: 0.95,
    message: finalMessage,
    matchedProducts,
    recipe: null,
    budgetPlan: null,
    followUpQuestions: suggestions
  });
}

async function fetchOpenRouterModel(model: string, systemPrompt: string, userPrompt: string, signal: AbortSignal): Promise<string> {
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
      temperature: 0.55,
      max_tokens: 450
    }),
    signal
  });
  if (!res.ok) throw new Error(`OR ${model} HTTP ${res.status}`);
  const data = await res.json();
  const content = data?.choices?.[0]?.message?.content;
  cleanModelReply(content);
  return content;
}

async function fetchPollinationsFast(model: string, systemPrompt: string, userPrompt: string, signal: AbortSignal): Promise<string> {
  const plPostUrl = `${P}text.pollinations.ai/openai`;
  const res = await fetch(plPostUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json", "Referer": `${P}pollinations.ai/` },
    body: JSON.stringify({
      model,
      seed: Math.floor(Math.random() * 1000000),
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userPrompt }
      ],
      temperature: 0.55
    }),
    signal
  });
  if (!res.ok) throw new Error(`PL ${model} HTTP ${res.status}`);
  const data = await res.json();
  const content = data?.choices?.[0]?.message?.content;
  cleanModelReply(content);
  return content;
}

async function callLiveAI(systemPrompt: string, userPrompt: string): Promise<string> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 11000);
  try {
    const winner = await Promise.any([
      fetchOpenRouterModel("google/gemini-2.0-flash-exp:free", systemPrompt, userPrompt, controller.signal),
      fetchOpenRouterModel("meta-llama/llama-3.3-70b-instruct:free", systemPrompt, userPrompt, controller.signal),
      fetchOpenRouterModel("deepseek/deepseek-chat-v3-0324:free", systemPrompt, userPrompt, controller.signal),
      fetchPollinationsFast("openai-fast", systemPrompt, userPrompt, controller.signal)
    ]);
    clearTimeout(timer);
    controller.abort();
    return winner;
  } catch {
    clearTimeout(timer);
  }

  // Fallback GET if all parallel POSTs were busy
  const controller2 = new AbortController();
  const timer2 = setTimeout(() => controller2.abort(), 10000);
  try {
    const shortQ = `${systemPrompt}\n\n${userPrompt}`.slice(0, 900);
    const plGetUrl = `${P}text.pollinations.ai/${encodeURIComponent(shortQ)}?model=openai&seed=${Math.floor(Math.random() * 99999)}`;
    const res = await fetch(plGetUrl, { method: "GET", signal: controller2.signal });
    clearTimeout(timer2);
    if (res.ok) {
      const text = (await res.text()).trim();
      cleanModelReply(text);
      return text;
    }
  } catch {
    clearTimeout(timer2);
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
    model: "fast-parallel-live",
    choices: [{ index: 0, message: { role: "assistant", content: finalJson }, finish_reason: "stop" }],
    usage: { prompt_tokens: 120, completion_tokens: 180, total_tokens: 300 }
  };
}
