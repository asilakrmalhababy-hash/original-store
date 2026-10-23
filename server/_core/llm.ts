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

function repairAndValidateLlmJson(raw: string): string | null {
  if (!raw || !raw.trim()) return null;
  const unfenced = raw.replace(/^\s*```(?:json)?\s*/i, "").replace(/\s*```\s*$/, "").trim();
  const s = unfenced.indexOf("{");
  const e = unfenced.lastIndexOf("}");
  if (s >= 0 && e > s) {
    const slice = unfenced.slice(s, e + 1);
    const repaired = slice.replace(/"(?:[^"\\]|\\.)*"/gs, m =>
      m.replace(/\r?\n/g, "\\n").replace(/\t/g, " ")
    );
    for (const candidate of [slice, repaired]) {
      try {
        const obj = JSON.parse(candidate);
        if (obj && typeof obj === "object" && (obj.message || obj.reply || obj.response || obj.steps)) {
          return JSON.stringify(obj);
        }
      } catch {}
    }
  }
  if (unfenced.length > 8 && !unfenced.startsWith("<")) {
    return JSON.stringify({
      message: unfenced.replace(/\*\*/g, "").slice(0, 1200),
      recipeName: "",
      servings: 0,
      ingredients: [],
      steps: [],
      missingIngredients: [],
      cartAction: "none",
      cartItems: [],
      suggestedQuestions: ["كيف أحضرها بأسهل طريقة؟", "كم كمية السعرات الحرارية؟"],
    });
  }
  return null;
}

const YEMENI_SMART_GUIDANCE = [
  "تعليمات هامة جداً لتحليل المنتجات والرد:",
  "- تحدث بلهجة يمنية طبيعية، ودودة، وراقية.",
  "- حلل طبيعة الصنف الذي يسأل عنه الزبون بذكاء حقيقي قبل الرد:",
  "  1) إذا كان الصنف شوكولاتة أو حلى أو بسكويت أو عصير أو مشروب أو سناك جاهز للأكل أو منظفات (ولم يطلب الزبون وصفة محددة بعد): لا تعطه وصفات طبخ! بل اشرح له معلومات حقيقية وجذابة عن هذا المنتج نفسه (طعمه، جودته، فوائده، أو استخدامه)، وفي آخر جملة من message اعرض عليه اقتراحين مناسبين لطبيعة المنتج (مثلاً للشوكولاتة: بس هذي الشوكولاتة تقدر تحضر منها حلى حلو إذا تريد أقول لك، أو إذا تريد أشرح لك كمية السعرات اللي ممكن تحصلها من هذي الشوكولاتة)، واجعل recipeName فارغاً و steps فارغة، وضع السؤالين القصيرين في مصفوفة suggestedQuestions مثل [\"كيف أحضر حلى حلو؟\", \"كم كمية السعرات؟\"].",
  "  2) أما إذا سأل الزبون سؤالاً محدداً (مثل: كيف أحضر حلى حلو؟ أو كم كمية السعرات؟ أو طلب طبخة مثل فول أو مرقة أو كبسة): فأجب على سؤاله بدقة وتفصيل حقيقي من تحليلك، وضع أسئلة متابعة جديدة في suggestedQuestions.",
  "- أعد دائماً كائن JSON صالحاً فقط بالحقول: message, recipeName, servings, ingredients, steps, missingIngredients, cartAction, cartItems, suggestedQuestions."
].join("\n");

const POLLINATIONS_HEADERS = {
  "Content-Type": "application/json",
  "Accept": "application/json",
  "Referer": "https://pollinations.ai/",
  "Origin": "https://pollinations.ai",
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
};

async function callPollinationsOpenAI(
  model: string,
  messages: Array<{ role: string; content: string }>,
  timeoutMs: number
): Promise<string> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch("https://text.pollinations.ai/openai", {
      method: "POST",
      headers: POLLINATIONS_HEADERS,
      body: JSON.stringify({
        model,
        messages,
        temperature: 0.6,
        seed: Math.floor(Math.random() * 1000000),
      }),
      signal: controller.signal,
    });
    clearTimeout(timer);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const raw = await res.text();
    let content = raw.trim();
    try {
      const d = JSON.parse(raw);
      if (typeof d?.choices?.[0]?.message?.content === "string") {
        content = d.choices[0].message.content.trim();
      }
    } catch {}
    const valid = repairAndValidateLlmJson(content);
    if (!valid) throw new Error("Invalid JSON");
    return valid;
  } catch (err) {
    clearTimeout(timer);
    throw err;
  }
}

async function callPollinationsGet(
  messages: Array<{ role: string; content: string }>,
  timeoutMs: number
): Promise<string> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const userMsg = messages.filter(m => m.role === "user").map(m => m.content).join("\n");
    const reqIdx = userMsg.lastIndexOf("رسالة العميل الحالية:");
    const coreQuestion = reqIdx >= 0 ? userMsg.slice(reqIdx) : userMsg.slice(-600);
    const prompt = `أجب بلهجة يمنية ودودة بصيغة JSON فقط بالحقول (message, recipeName, servings, ingredients, steps, missingIngredients, cartAction, cartItems, suggestedQuestions):\n${coreQuestion}`;
    const url = `https://text.pollinations.ai/${encodeURIComponent(prompt)}?model=openai&json=true&seed=${Math.floor(Math.random() * 100000)}`;
    const res = await fetch(url, {
      method: "GET",
      headers: POLLINATIONS_HEADERS,
      signal: controller.signal,
    });
    clearTimeout(timer);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const raw = await res.text();
    const valid = repairAndValidateLlmJson(raw);
    if (!valid) throw new Error("Invalid GET JSON");
    return valid;
  } catch (err) {
    clearTimeout(timer);
    throw err;
  }
}

export async function invokeLLM(params: InvokeParams): Promise<InvokeResult> {
  const normalizedMessages = params.messages.map((m, idx) => {
    const role = m.role === "assistant" ? "assistant" : m.role === "system" ? "system" : "user";
    const text = extractText(m.content);
    if (role === "system" && idx === 0) {
      return { role, content: `${text}\n\n${YEMENI_SMART_GUIDANCE}` };
    }
    return { role, content: text };
  });

  try {
    const fastestLive = await Promise.any([
      callPollinationsOpenAI("openai", normalizedMessages, 11000),
      callPollinationsOpenAI("openai-fast", normalizedMessages, 10000),
      callPollinationsGet(normalizedMessages, 11000),
    ]);
    return {
      id: "live-ai-" + Date.now(),
      created: Date.now(),
      model: "openai-live",
      choices: [{ index: 0, message: { role: "assistant", content: fastestLive }, finish_reason: "stop" }],
    };
  } catch {}

  try {
    const retryLive = await callPollinationsOpenAI("openai", normalizedMessages, 14000);
    return {
      id: "live-retry-" + Date.now(),
      created: Date.now(),
      model: "openai-live",
      choices: [{ index: 0, message: { role: "assistant", content: retryLive }, finish_reason: "stop" }],
    };
  } catch {}

  // Never show an internet error toast to the customer if the external provider is momentarily busy
  const userText = normalizedMessages.filter(m => m.role === "user").map(m => m.content).join("\n");
  const reqIdx = userText.lastIndexOf("رسالة العميل الحالية:");
  const ask = (reqIdx >= 0 ? userText.slice(reqIdx + "رسالة العميل الحالية:".length) : userText).trim().slice(0, 80);
  const gracefulJson = JSON.stringify({
    message: `حياك الله يا غالي! بالنسبة لطلبك «${ask || "وصفتك"}»، أبشر بعزك، حدد لي هل تفضل الطريقة اليمنية الشعبية الأصيلة أم الطريقة السريعة الاقتصادية، أو تشتي نحسب السعرات الحرارية؟`,
    recipeName: "",
    servings: 0,
    ingredients: [],
    steps: [],
    missingIngredients: [],
    cartAction: "none",
    cartItems: [],
    suggestedQuestions: [`الطريقة اليمنية الشعبية لـ ${ask.slice(0, 25)}`, "طريقة سريعة واقتصادية", "كم كمية السعرات الحرارية؟"],
  });

  return {
    id: "graceful-" + Date.now(),
    created: Date.now(),
    model: "assistant",
    choices: [{ index: 0, message: { role: "assistant", content: gracefulJson }, finish_reason: "stop" }],
  };
}
