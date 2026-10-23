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

const CLEAN_POLLINATIONS_SYSTEM_PROMPT = [
  "أنت المساعد الذكي الخبير لمتجر أوريجنال (ORIGINAL) في اليمن. تحدث دائماً بلهجة يمنية طبيعية، ودودة، ومبتكرة.",
  "قواعد التحليل الذكي:",
  "1. إذا سأل الزبون عن منتج معين بين علامتي «...» دون تحديد سؤال فرعي (تحليل أولي للمنتج):",
  "   - افهم طبيعة المنتج أولاً: إذا كان منتجاً جاهزاً للأكل أو الشرب أو الاستخدام (مثل: شوكولاتة، بسكويت، حلى، عصير، مشروب، شيبس، مكسرات، أو منظفات): لا تعطه وصفات طبخ! بل قدم له معلومات حقيقية وجذابة ومفيدة عن هذا المنتج نفسه (طعمه، جودته، فوائده، أو استخدامه).",
  "   - في نهاية رسالتك (message)، اعرض عليه بلطف فكرتين مناسبتين لهذا المنتج تحديداً (مثال للشوكولاتة: بس هذي الشوكولاتة تقدر تحضر منها حلى حلو إذا تريد أقول لك، أو إذا تريد أشرح لك كمية السعرات اللي ممكن تحصلها من هذي الشوكولاتة). وفي هذا التحليل الأولي اجعل recipeName فارغاً \"\" و steps فارغة [].",
  "   - أما إذا كان المنتج مكون طبخ أساسي (مثل: أرز، تونة، دجاج، فاصوليا، بهارات) فعرّف بجودته في المطبخ اليمني أولاً واعرض عليه تحضير طبخة يمنية شعبية أو وصفة سريعة أو معرفة السعرات.",
  "2. إذا سأل الزبون سؤالاً محدداً (مثل: كيف أحضر حلى حلو؟ أو كم كمية السعرات؟ أو طلب وصفة فول أو مرقة أو كبسة):",
  "   - أجب على سؤاله مباشرة بإجابة حقيقية ومبتكرة ومفصلة!",
  "   - إذا كانت الإجابة تتضمن وصفة أو طريقة تحضير، اكتب اسمها في recipeName وخطواتها في steps والمقادير المتوفرة من كتالوج المتجر في ingredients.",
  "3. دائماً ضع سؤالين أو 3 أسئلة قصيرة مقترحة تابعة لإجابتك في مصفوفة suggestedQuestions (مثال: [\"كيف أحضر حلى حلو؟\", \"كم كمية السعرات؟\"]).",
  "أعد دائماً كائن JSON صالحاً فقط بهذا الشكل تماماً بدون علامات **:",
  "{\"message\":\"...\",\"recipeName\":\"\",\"servings\":0,\"ingredients\":[],\"steps\":[],\"missingIngredients\":[],\"cartAction\":\"none\",\"cartItems\":[],\"suggestedQuestions\":[\"سؤال 1\",\"سؤال 2\"]}"
].join("\n");

function cleanUserPrompt(rawUserText: string): string {
  return rawUserText
    .replace(/ما هي أفضل 3 طرق لتحضير «([^»]+)»[^؟]*؟/g, "حلل المنتج «$1» بذكاء حسب طبيعته")
    .replace(/المطلوب: أفضل 3 طرق تحضير[^\n]*/g, "المطلوب: تحليل ذكي للمنتج ومعلومات عنه مع اقتراحات تفاعلية.");
}

function parsePollinationsResponse(rawBody: string): string | null {
  if (!rawBody || !rawBody.trim()) return null;
  let content = rawBody.trim();
  try {
    const outer = JSON.parse(rawBody);
    const msgContent = outer?.choices?.[0]?.message?.content;
    if (typeof msgContent === "string" && msgContent.trim()) {
      content = msgContent.trim();
    }
  } catch {}

  const unfenced = content.replace(/^\s*```(?:json)?\s*/i, "").replace(/\s*```\s*$/, "").trim();
  const s = unfenced.indexOf("{");
  const e = unfenced.lastIndexOf("}");

  if (s >= 0 && e > s) {
    const slice = unfenced.slice(s, e + 1);
    const repaired = slice.replace(/"(?:[^"\\]|\\.)*"/gs, m =>
      m.replace(/\r?\n/g, "\\n").replace(/\t/g, " ")
    );
    for (const candidate of [slice, repaired]) {
      try {
        const obj: any = JSON.parse(candidate);
        if (obj && typeof obj === "object") {
          let msgText = String(obj.message || obj.reply || obj.response || "").replace(/\*\*/g, "").trim();
          if (!msgText && Array.isArray(obj.steps) && obj.steps.length > 0) {
            msgText = `إليك طريقة تحضير ${obj.recipeName || "الوصفة"} بالتفصيل:`;
          }
          if (msgText) {
            const sugs = Array.isArray(obj.suggestedQuestions)
              ? obj.suggestedQuestions.filter((x: any) => typeof x === "string" && x.trim()).map((x: string) => x.trim().slice(0, 60)).slice(0, 3)
              : [];
            const cleanBaseMsg = msgText.replace(/\s*\[\[SUGGESTIONS:[^\]]+\]\]/g, "").slice(0, 950);
            obj.message = sugs.length > 0 ? `${cleanBaseMsg}\n[[SUGGESTIONS:${sugs.join("|")}]]` : cleanBaseMsg;
            return JSON.stringify(obj);
          }
        }
      } catch {}
    }
  }

  if (unfenced.length > 2 && !unfenced.startsWith("<")) {
    const cleanPlain = unfenced.replace(/\*\*/g, "").slice(0, 950);
    return JSON.stringify({
      message: `${cleanPlain}\n[[SUGGESTIONS:كيف أحضر حلى حلو؟|كم كمية السعرات؟]]`,
      recipeName: "",
      servings: 0,
      ingredients: [],
      steps: [],
      missingIngredients: [],
      cartAction: "none",
      cartItems: [],
    });
  }

  return null;
}

async function callPollinationsModel(
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
        "Referer": "https://pollinations.ai/",
        "Origin": "https://pollinations.ai",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36",
      },
      body: JSON.stringify({
        model,
        messages,
        temperature: 0.65,
        seed: Math.floor(Math.random() * 1000000),
      }),
      signal: controller.signal,
    });
    clearTimeout(timer);
    if (!res.ok) throw new Error(`Pollinations HTTP ${res.status}`);
    const raw = await res.text();
    const parsed = parsePollinationsResponse(raw);
    if (!parsed) throw new Error("Unparseable Pollinations response");
    return parsed;
  } catch (err) {
    clearTimeout(timer);
    throw err;
  }
}

export async function invokeLLM(params: InvokeParams): Promise<InvokeResult> {
  const userMessages = params.messages
    .filter(m => m.role !== "system")
    .map(m => ({
      role: m.role === "assistant" ? "assistant" : "user",
      content: cleanUserPrompt(extractText(m.content)),
    }));

  const cleanMessages = [
    { role: "system", content: CLEAN_POLLINATIONS_SYSTEM_PROMPT },
    ...userMessages,
  ];

  // Call Pollinations ("openai" / "openai-fast")
  for (const model of ["openai", "openai-fast", "openai"]) {
    try {
      const content = await callPollinationsModel(model, cleanMessages, 15000);
      return {
        id: "pllns-" + Date.now(),
        created: Date.now(),
        model: "pollinations-" + model,
        choices: [{ index: 0, message: { role: "assistant", content }, finish_reason: "stop" }],
      };
    } catch (err) {
      console.warn(`[Pollinations ${model} attempt]:`, err instanceof Error ? err.message : err);
    }
  }

  throw new Error("Pollinations service busy");
}
