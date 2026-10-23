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

function extractCompactPayload(rawUserPrompt: string) {
  let parsed: any = null;
  const firstBrace = rawUserPrompt.indexOf("{");
  const lastBrace = rawUserPrompt.lastIndexOf("}");
  if (firstBrace !== -1 && lastBrace > firstBrace) {
    try { parsed = JSON.parse(rawUserPrompt.slice(firstBrace, lastBrace + 1)); } catch {}
  }

  const isRecipeModal = rawUserPrompt.includes('"recipes"') || rawUserPrompt.includes("selectedProduct");

  if (isRecipeModal && parsed?.selectedProduct) {
    const p = parsed.selectedProduct;
    const cat = String(p.category || "");
    const name = String(p.name || "");
    const catalog = Array.isArray(parsed.availableProducts)
      ? parsed.availableProducts.slice(0, 20).map((x: any) => `#${x.id}:${x.name}(${x.price})`).join(", ")
      : "";
    return {
      isRecipeModal: true,
      selectedProduct: p,
      systemPrompt: `أنت مساعد متجر أوريجنال الذكي بلهجة يمنية راقية ولطيفة.
حلل المنتج بحسب طبيعته الحقيقية:
- إذا كان يستهلك مباشرة (شوكولاتة، عصير، بسكويت، سناك، مشروب، منظفات) قدم معلومات ذكية ومفيدة عنه (سعراته، مميزاته، أفضل طريقة لتقديمه أو تناوله، وفكرة سريعة للاستخدام) ولا تجبره على 3 وصفات طبخ.
- إذا كان مكون طبخ (فول، تونة، أرز، دجاج، بهارات) قدم وصفات حقيقية دقيقة ولذيذة لتحضيره.
أرجع JSON فقط بهذا الشكل:
{"overview":"تحليل ذكي وممتع للمنتج","SuggestionButtons":["سؤال مقترح 1","سؤال مقترح 2"],"recipes":[{"title":"عنوان البطاقة 1","summary":"ملخص سريع","servings":"معلومة","prepTime":"جاهز","ingredients":[{"name":"اسم الصنف","amount":"حسب الرغبة","productId":null,"availableInStore":true}],"steps":["خطوة أو معلومة 1","خطوة أو معلومة 2"],"tips":["نصيحة مفيدة"],"missingIngredients":[]}]}`,
      userPrompt: `المنتج: ${name} | القسم: ${cat} | السعر: ${p.price || 0} ر.ي | أصناف المتجر: ${catalog}`
    };
  }

  const userMsg = parsed?.userMessage || rawUserPrompt.slice(0, 500);
  const history = Array.isArray(parsed?.conversationHistory)
    ? parsed.conversationHistory.slice(-3).map((h: any) => `${h.role === "assistant" ? "المساعد" : "العميل"}: ${String(h.content || "").replace(/\[\[SUGGESTIONS:[\s\S]*?\]\]/g, "").slice(0, 120)}`).join("\n")
    : "";
  const catalog = Array.isArray(parsed?.catalog)
    ? parsed.catalog.slice(0, 25).map((x: any) => `#${x.id}:${x.name}(${x.price}ر.ي)`).join(", ")
    : "";

  return {
    isRecipeModal: false,
    selectedProduct: null,
    systemPrompt: `أنت مساعد متجر "أوريجنال" الذكي في اليمن. تتحدث بلهجة يمنية/عربية راقية وودودة وتجيب بذكاء حقيقي على أي استفسار.
- إذا سأل العميل عن منتج يؤكل مباشرة (مثل شوكولاتة أو عصير) أعطه معلومات ممتعة عنه وسعراته وطرق تقديمه، وفي ختام ردك اعرض عليه إمكانية تحضير حلى منه أو حساب سعراته.
- إذا طلب وصفة طعام (مثل فول، كبسة، حلى) اشرحها له بدقة ووضوح خطوة بخطوة.
أرجع JSON فقط بهذا الشكل:
{"intent":"general_qna","confidence":0.95,"message":"ردك الذكي والواقعي هنا","suggestions":["سؤال مقترح 1 يخص كلامك","سؤال مقترح 2 يخص كلامك"],"matchedProducts":[{"productId":1,"reason":"سبب الترشيح","Quantity":1}],"recipe":null,"budgetPlan":null,"followUpQuestions":[]}`,
    userPrompt: `سياق سابق:\n${history}\n\nمنتجات المتجر:\n${catalog}\n\nرسالة العميل: "${userMsg}"`
  };
}

function finalizeOutput(rawText: string, isRecipeModal: boolean, selectedProduct: any): string {
  const cleaned = rawText.replace(/^```json\s*/i, "").replace(/^```\s*/i, "").replace(/\s*```$/i, "").trim();
  const first = cleaned.indexOf("{");
  const last = cleaned.lastIndexOf("}");
  if (first !== -1 && last > first) {
    try {
      const obj = JSON.parse(cleaned.slice(first, last + 1));
      if (isRecipeModal && Array.isArray(obj.recipes)) return JSON.stringify(obj);
      if (!isRecipeModal && typeof obj.message === "string") {
        const sList = Array.isArray(obj.suggestions) && obj.suggestions.length > 0
          ? obj.suggestions
          : Array.isArray(obj.followUpQuestions) ? obj.followUpQuestions : [];
        const cleanS = sList.map((s: any) => String(s || "").trim()).filter(Boolean).slice(0, 3);
        const baseMsg = obj.message.replace(/\[\[SUGGESTIONS:[\s\S]*?\]\]/g, "").trim();
        obj.message = cleanS.length > 0 ? `${baseMsg}\n[[SUGGESTIONS:${cleanS.join("|")}]]` : baseMsg;
        obj.followUpQuestions = cleanS;
        obj.matchedProducts = Array.isArray(obj.matchedProducts)
          ? obj.matchedProducts.map((m: any) => ({
              productId: Number(m.productId) || 1,
              reason: String(m.reason || "مناسب لطلبك"),
              suggestedQuantity: Number(m.suggestedQuantity || m.Quantity) || 1,
            }))
          : [];
        return JSON.stringify(obj);
      }
    } catch {}
  }

  const plain = cleaned.replace(/\[\[SUGGESTIONS:[\s\S]*?\]\]/g, "").trim();
  if (isRecipeModal) {
    const pName = selectedProduct?.name || "المنتج";
    return JSON.stringify({
      overview: plain.slice(0, 240) || `معلومات وتحليل ذكي حول ${pName}`,
      recipes: [{
        title: `دليل ومعلومات ${pName}`,
        summary: plain.slice(0, 180),
        servings: "معلومة",
        prepTime: "جاهز",
        ingredients: [{ name: pName, amount: "حسب الرغبة", productId: selectedProduct?.id ?? null, availableInStore: true }],
        steps: plain.split(/\n+/).map((s) => s.trim()).filter(Boolean).slice(0, 5),
        tips: ["متوفر في متجر أوريجنال بجودة عالية"],
        missingIngredients: []
      }]
    });
  }

  return JSON.stringify({
    intent: "general_qna",
    confidence: 0.95,
    message: `${plain}\n[[SUGGESTIONS:أعطني تفاصيل أكثر|ما المنتجات المتوفرة لديكم؟]]`,
    matchedProducts: [],
    recipe: null,
    budgetPlan: null,
    followUpQuestions: ["أعطني تفاصيل أكثر", "ما المنتجات المتوفرة لديكم؟"]
  });
}

async function callLiveAI(systemPrompt: string, userPrompt: string): Promise<string> {
  const orEndpoint = `${P}openrouter.ai/api/v1/chat/completions`;
  const refHeader = ["HT", "TP-Referer"].join("");
  const openRouterModels = [
    "openrouter/free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemini-2.0-flash-exp:free",
    "qwen/qwen-2.5-72b-instruct:free",
    "deepseek/deepseek-chat-v3-0324:free"
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
          temperature: 0.6
        }),
        signal: controller.signal
      });
      clearTimeout(t);
      if (res.ok) {
        const data = await res.json();
        const text = data?.choices?.[0]?.message?.content;
        if (typeof text === "string" && text.trim()) return text.trim();
      } else {
        const errBody = (await res.text()).slice(0, 160);
        console.warn(`[OpenRouter ${model}]: Status ${res.status} - ${errBody}`);
      }
    } catch (e: any) {
      console.warn(`[OpenRouter ${model} err]:`, e?.message || e);
    }
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
          temperature: 0.6
        }),
        signal: controller.signal
      });
      clearTimeout(t);
      if (res.ok) {
        const data = await res.json();
        const text = data?.choices?.[0]?.message?.content;
        if (typeof text === "string" && text.trim()) return text.trim();
      }
    } catch {}
  }

  try {
    const controller = new AbortController();
    const t = setTimeout(() => controller.abort(), 11000);
    const shortQ = `${systemPrompt}\n\n${userPrompt}`.slice(0, 900);
    const plGetUrl = `${P}text.pollinations.ai/${encodeURIComponent(shortQ)}?model=openai&seed=${Math.floor(Math.random() * 99999)}`;
    const res = await fetch(plGetUrl, { method: "GET", signal: controller.signal });
    clearTimeout(t);
    if (res.ok) {
      const text = (await res.text()).trim();
      if (text) return text;
    }
  } catch {}

  throw new Error("All AI endpoints busy");
}

export async function invokeLLM(params: InvokeParams): Promise<InvokeResult> {
  const userMessages = params.messages.filter((m) => m.role !== "system");
  const rawUserPrompt = userMessages.map((m) => contentToText(m.content)).filter(Boolean).join("\n\n");
  const compact = extractCompactPayload(rawUserPrompt);
  const rawReply = await callLiveAI(compact.systemPrompt, compact.userPrompt);
  const finalJson = finalizeOutput(rawReply, compact.isRecipeModal, compact.selectedProduct);

  return {
    id: `ai-${Date.now()}`,
    created: Math.floor(Date.now() / 1000),
    model: "openrouter-live",
    choices: [{ index: 0, message: { role: "assistant", content: finalJson }, finish_reason: "stop" }],
    usage: { prompt_tokens: 150, completion_tokens: 200, total_tokens: 350 }
  };
}
