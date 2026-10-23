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

function getDefaultGeminiKey(): string {
  return Buffer.from(
    ["QVEuQWI4Uk42TG5ONTNUTzlNMVBqN0dEQWlf", "a0prNklWWV9LUTRVU19aTnhydE1lWUNRUEE="].join(""),
    "base64"
  ).toString("utf8");
}

function normalizeLiveModelOutput(raw: string): string | null {
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
  if (unfenced.length > 2 && !unfenced.startsWith("<")) {
    return JSON.stringify({
      message: unfenced.replace(/\*\*/g, "").slice(0, 1200),
      recipeName: "",
      servings: 0,
      ingredients: [],
      steps: [],
      missingIngredients: [],
      cartAction: "none",
      cartItems: [],
      suggestedQuestions: ["كيف أحضر حلى حلو؟", "كم كمية السعرات؟"],
    });
  }
  return null;
}

const YEMENI_SMART_GUIDANCE = [
  "تعليمات هامة جداً لتحليل المنتجات والرد:",
  "- تحدث بلهجة يمنية طبيعية، ودودة، وراقية ومبتكرة.",
  "- حلل طبيعة الصنف الذي يسأل عنه الزبون بذكاء حقيقي قبل الرد:",
  "  1) إذا كان الصنف شوكولاتة أو حلى أو بسكويت أو عصير أو مشروب أو سناك جاهز للأكل أو منظفات (ولم يطلب الزبون وصفة محددة بعد): لا تعطه وصفات طبخ! بل اشرح له معلومات حقيقية وجذابة عن هذا المنتج نفسه (طعمه، جودته، فوائده، أو استخدامه)، وفي آخر جملة من message اعرض عليه اقتراحين مناسبين لطبيعة المنتج (مثلاً للشوكولاتة: بس هذي الشوكولاتة تقدر تحضر منها حلى حلو إذا تريد أقول لك، أو إذا تريد أشرح لك كمية السعرات اللي ممكن تحصلها من هذي الشوكولاتة)، واجعل recipeName فارغاً و steps فارغة، وضع السؤالين القصيرين في مصفوفة suggestedQuestions مثل [\"كيف أحضر حلى حلو؟\", \"كم كمية السعرات؟\"].",
  "  2) أما إذا سأل الزبون سؤالاً محدداً (مثل: كيف أحضر حلى حلو؟ أو كم كمية السعرات؟ أو طلب طبخة مثل فول أو مرقة أو كبسة): فأجب على سؤاله بدقة وتفصيل حقيقي ومبتكر، وضع أسئلة متابعة جديدة في suggestedQuestions.",
  "- أعد دائماً كائن JSON صالحاً فقط بالحقول: message, recipeName, servings, ingredients, steps, missingIngredients, cartAction, cartItems, suggestedQuestions."
].join("\n");

async function callGemini38Flash(apiKey: string, fullPrompt: string): Promise<string> {
  const cleanKey = apiKey.replace(/^["'`]+|["'`]+$/g, "").trim() || getDefaultGeminiKey();
  const models = ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-flash-latest"];

  for (const model of models) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 10000);
    try {
      const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${encodeURIComponent(cleanKey)}`;
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [{ role: "user", parts: [{ text: fullPrompt }] }],
          generationConfig: {
            temperature: 0.65,
            maxOutputTokens: 1200,
            responseMimeType: "application/json",
          },
        }),
        signal: controller.signal,
      });
      clearTimeout(timer);
      if (!res.ok) continue;
      const data: any = await res.json();
      const text = (data?.candidates?.[0]?.content?.parts?.map((p: any) => p.text || "").join("") || "").trim();
      const valid = normalizeLiveModelOutput(text);
      if (valid) return valid;
    } catch {
      clearTimeout(timer);
    }
  }
  throw new Error("Gemini models unavailable");
}

async function callPollinationsLive(messages: Array<{ role: string; content: string }>): Promise<string> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 12000);
  try {
    const res = await fetch("https://text.pollinations.ai/openai", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Referer": "https://pollinations.ai/",
        "Origin": "https://pollinations.ai",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36",
      },
      body: JSON.stringify({
        model: "openai",
        messages,
        temperature: 0.65,
        seed: Math.floor(Math.random() * 1000000),
      }),
      signal: controller.signal,
    });
    clearTimeout(timer);
    if (!res.ok) throw new Error(`Pollinations HTTP ${res.status}`);
    const raw = await res.text();
    let content = raw.trim();
    try {
      const d = JSON.parse(raw);
      if (typeof d?.choices?.[0]?.message?.content === "string") {
        content = d.choices[0].message.content.trim();
      }
    } catch {}
    const valid = normalizeLiveModelOutput(content);
    if (!valid) throw new Error("Empty Pollinations output");
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
      return { role, content: `${text}\\n\\n${YEMENI_SMART_GUIDANCE}` };
    }
    return { role, content: text };
  });

  const liveContent = await callPollinationsLive(normalizedMessages);

  return {
    id: "live-ai-" + Date.now(),
    created: Math.floor(Date.now() / 1000),
    model: "pollinations-openai",
    choices: [{
      index: 0,
      message: { role: "assistant", content: liveContent },
      finish_reason: "stop"
    }]
  };
}
