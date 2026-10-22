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
  maxTokens?: number;
  max_tokens?: number;
  maxCompletionTokens?: number;
  max_completion_tokens?: number;
  outputSchema?: OutputSchema;
  output_schema?: OutputSchema;
  responseFormat?: ResponseFormat;
  response_format?: ResponseFormat;
  model?: string;
  thinking?: Record<string, unknown>;
  reasoning?: Record<string, unknown>;
  [key: string]: unknown;
};

export type InvokeResult = {
  id: string;
  created: number;
  model: string;
  choices: Array<{
    index: number;
    message: { role: Role; content: string };
    finish_reason: string | null;
  }>;
};

function extractText(content: MessageContent | MessageContent[]): string {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return content.map(c => (typeof c === "string" ? c : "text" in c ? c.text : "")).join("\n");
  }
  return "text" in content ? content.text : "";
}

let geminiSkipUntil = 0;

async function tryGeminiOnce(apiKey: string, fullPrompt: string, wantsJson: boolean): Promise<string | null> {
  if (Date.now() < geminiSkipUntil) return null;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 4500);
  try {
    const payload = {
      contents: [{ role: "user", parts: [{ text: fullPrompt }] }],
      generationConfig: {
        temperature: 0.55,
        maxOutputTokens: 1200,
        ...(wantsJson ? { responseMimeType: "application/json" } : {}),
      },
    };
    const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${encodeURIComponent(apiKey)}`;
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    clearTimeout(timer);
    if (!res.ok) {
      geminiSkipUntil = Date.now() + 10 * 60 * 1000;
      return null;
    }
    const data: any = await res.json();
    const text = (data?.candidates?.[0]?.content?.parts?.map((p: any) => p.text || "").join("") || "").trim();
    return text || null;
  } catch {
    clearTimeout(timer);
    geminiSkipUntil = Date.now() + 5 * 60 * 1000;
    return null;
  }
}

async function callCloudOpenAI(messages: Array<{ role: string; content: string }>): Promise<string | null> {
  for (let attempt = 0; attempt < 2; attempt++) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 11000);
    try {
      const res = await fetch("https://text.pollinations.ai/openai", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "openai",
          messages,
          temperature: 0.55,
        }),
        signal: controller.signal,
      });
      clearTimeout(timer);
      if (!res.ok) continue;
      const raw = await res.text();
      if (!raw || !raw.trim()) continue;
      try {
        const data = JSON.parse(raw);
        const content = data?.choices?.[0]?.message?.content;
        if (typeof content === "string" && content.trim()) return content.trim();
      } catch {}
      return raw.trim();
    } catch {
      clearTimeout(timer);
    }
  }
  return null;
}

export async function invokeLLM(params: InvokeParams): Promise<InvokeResult> {
  const apiKey = (
    process.env.GEMINI_API_KEY ||
    process.env.MANUS_API_KEY ||
    ENV.forgeApiKey ||
    ""
  ).trim();

  const normalizedMessages = params.messages.map(m => ({
    role: m.role === "assistant" ? "assistant" : m.role === "system" ? "system" : "user",
    content: extractText(m.content),
  }));

  const fullPrompt = normalizedMessages
    .map(m => (m.role === "system" ? `تعليمات النظام:\n${m.content}` : m.content))
    .join("\n\n");

  const fmt = params.responseFormat || params.response_format;
  const wantsJson = fmt?.type === "json_object" || fmt?.type === "json_schema";

  const geminiText = await tryGeminiOnce(apiKey, fullPrompt, wantsJson);
  if (geminiText) {
    return {
      id: "gemini-" + Date.now(),
      created: Date.now(),
      model: "gemini-2.0-flash",
      choices: [{ index: 0, message: { role: "assistant", content: geminiText }, finish_reason: "stop" }],
    };
  }

  const cloudText = await callCloudOpenAI(normalizedMessages);
  if (cloudText) {
    return {
      id: "cloud-" + Date.now(),
      created: Date.now(),
      model: "openai",
      choices: [{ index: 0, message: { role: "assistant", content: cloudText }, finish_reason: "stop" }],
    };
  }

  throw new Error("AI request failed");
}
