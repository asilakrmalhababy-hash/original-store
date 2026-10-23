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
  return null;
}

async function callGoogleGeminiLive(apiKey: string, fullPrompt: string): Promise<string | null> {
  const cleanKey = apiKey.replace(/^["'`]+|["'`]+$/g, "").trim();
  if (!cleanKey) return null;

  const isVertex = cleanKey.startsWith("AQ.");
  const urls = isVertex
    ? [
        `https://aiplatform.googleapis.com/v1/publishers/google/models/gemini-2.0-flash:generateContent?key=${encodeURIComponent(cleanKey)}`,
        `https://aiplatform.googleapis.com/v1beta1/publishers/google/models/gemini-1.5-flash:generateContent?key=${encodeURIComponent(cleanKey)}`,
      ]
    : [
        `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${encodeURIComponent(cleanKey)}`,
        `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${encodeURIComponent(cleanKey)}`,
      ];

  for (const url of urls) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 9000);
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-goog-api-key": cleanKey,
        },
        body: JSON.stringify({
          contents: [{ role: "user", parts: [{ text: fullPrompt }] }],
          generationConfig: {
            temperature: 0.6,
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
      const valid = repairAndValidateLlmJson(text);
      if (valid) return valid;
    } catch {
      clearTimeout(timer);
    }
  }
  return null;
}

async function callSingleLiveModel(
  model: string,
  messages: Array<{ role: string; content: string }>,
  timeoutMs: number
): Promise<string> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch("https://text.pollinations.ai/openai", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36",
      },
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
    if (!valid) throw new Error("Invalid JSON from model");
    return valid;
  } catch (err) {
    clearTimeout(timer);
    throw err;
  }
}

async function callDirectPollinationsRoot(
  messages: Array<{ role: string; content: string }>,
  timeoutMs: number
): Promise<string> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch("https://text.pollinations.ai/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36",
      },
      body: JSON.stringify({
        messages,
        model: "openai-fast",
        jsonMode: true,
        seed: Math.floor(Math.random() * 1000000),
      }),
      signal: controller.signal,
    });
    clearTimeout(timer);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const raw = await res.text();
    const valid = repairAndValidateLlmJson(raw);
    if (!valid) throw new Error("Invalid JSON from root endpoint");
    return valid;
  } catch (err) {
    clearTimeout(timer);
    throw err;
  }
}

export async function invokeLLM(params: InvokeParams): Promise<InvokeResult> {
  const normalizedMessages = params.messages.map(m => ({
    role: m.role === "assistant" ? "assistant" : m.role === "system" ? "system" : "user",
    content: extractText(m.content),
  }));

  // 1. Race the fastest live models in parallel so the fastest real AI wins immediately
  try {
    const fastestLiveResponse = await Promise.any([
      callSingleLiveModel("openai-fast", normalizedMessages, 12000),
      callSingleLiveModel("openai", normalizedMessages, 14000),
      callDirectPollinationsRoot(normalizedMessages, 13000),
    ]);
    return {
      id: "live-ai-" + Date.now(),
      created: Date.now(),
      model: "openai-fast-live",
      choices: [{ index: 0, message: { role: "assistant", content: fastestLiveResponse }, finish_reason: "stop" }],
    };
  } catch {}

  // 2. Try Google Gemini live if key is configured
  const apiKey = (process.env.GEMINI_API_KEY || process.env.MANUS_API_KEY || ENV.forgeApiKey || "").trim();
  if (apiKey) {
    const fullPrompt = normalizedMessages
      .map(m => (m.role === "system" ? `تعليمات النظام:\n${m.content}` : m.content))
      .join("\n\n");
    const geminiLive = await callGoogleGeminiLive(apiKey, fullPrompt);
    if (geminiLive) {
      return {
        id: "gemini-live-" + Date.now(),
        created: Date.now(),
        model: "gemini-2.0-flash",
        choices: [{ index: 0, message: { role: "assistant", content: geminiLive }, finish_reason: "stop" }],
      };
    }
  }

  // 3. Final live retry with mistral model
  const mistralLive = await callSingleLiveModel("mistral", normalizedMessages, 15000);
  return {
    id: "mistral-live-" + Date.now(),
    created: Date.now(),
    model: "mistral-live",
    choices: [{ index: 0, message: { role: "assistant", content: mistralLive }, finish_reason: "stop" }],
  };
}
