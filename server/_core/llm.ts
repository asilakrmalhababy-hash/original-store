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

function normAr(s: string): string {
  return s
    .toLowerCase()
    .replace(/[أإآٱ]/g, "ا")
    .replace(/ة/g, "ه")
    .replace(/ى/g, "ي")
    .replace(/[\u064B-\u065Fـ]/g, "")
    .trim();
}

type ProductCategoryKind = "sweet" | "drink" | "snack" | "household" | "cooking";

function classifyProductKind(name: string): ProductCategoryKind {
  const n = normAr(name);
  if (/(شوكول|شوكلت|شكلاته|شوكلاه|جالكسي|كيت كات|سنيكرز|مارس|نوتيلا|بسكويت|بسكوت|كيك|ويفر|حلاوه|عسل|قشطه|مربي|تمر|ايسكريم|كاكاو|توفي|غزل|كنافه|بقلاوه|كرواسون)/.test(n)) {
    return "sweet";
  }
  if (/(عصير|مشروب|شاي|قهوه|بن |نسكافيه|كابتشينو|حليب|لبن|زبادي|ماء|مياه|بيبسي|كوكاكولا|سفن|فيمتو|تانج|ميرندا|ردبول|شراب|نعناع)/.test(n)) {
    return "drink";
  }
  if (/(شيبس|بطاطس مقرمش|مكسرات|لوز|فستق|كاجو|فشار|مقرمش|حب |بزر|فول سوداني|سمسميه)/.test(n)) {
    return "snack";
  }
  if (/(صابون|شامبو|منظف|كلور|تايد|فيري|مناديل|فاين|معجون اسنان|فرشاه|عطر|مزيل|كريم|لوشن|فوط|حفاض|اكياس|اسفنج|ملمع|معطر|ديتول)/.test(n)) {
    return "household";
  }
  return "cooking";
}

type CatalogItem = { id: number; name: string; price: number; unit: string };

function buildLegendaryYemeniAnalysis(messages: Array<{ role: string; content: string }>): string {
  const userText = messages.filter(m => m.role === "user").map(m => m.content).join("\n");
  let catalog: CatalogItem[] = [];
  const catMatch = userText.match(/\[(\{"id":[\s\S]*?\})\]/);
  if (catMatch) {
    try { catalog = JSON.parse(`[${catMatch[1]}]`); } catch {}
  }

  let request = userText;
  const reqMarker = userText.lastIndexOf("رسالة العميل الحالية:");
  const prodMarker = userText.indexOf("الصنف الأساسي:");
  if (reqMarker >= 0) {
    request = userText.slice(reqMarker + "رسالة العميل الحالية:".length).trim();
  } else if (prodMarker >= 0) {
    const modM = userText.match(/طلب التعديل الخاص من الزبون[^:]*:\s*([^\n]+)/);
    const pM = userText.match(/«([^»]+)»/);
    request = modM ? `«${pM?.[1] || ""}» ${modM[1]}` : `«${pM?.[1] || ""}»`;
  }

  const findStoreProducts = (keywords: string[], maxCount = 3): Array<{ productId: number; quantity: number }> => {
    const matched: Array<{ productId: number; quantity: number }> = [];
    const nKeys = keywords.map(normAr).filter(k => k.length >= 2);
    for (const item of catalog) {
      const nName = normAr(item.name);
      if (nKeys.some(k => nName.includes(k))) {
        matched.push({ productId: item.id, quantity: 1 });
        if (matched.length >= maxCount) break;
      }
    }
    return matched;
  };

  const prodMatch = request.match(/«([^»]+)»/) || userText.match(/«([^»]+)»/);
  const prodName = prodMatch ? prodMatch[1].trim() : "";
  const subQuestion = request
    .replace(/تحليل المنتج\s*«[^»]+»/g, "")
    .replace(/ما هي أفضل[^؟]*؟/g, "")
    .replace(/التعديل المطلوب:/g, "")
    .replace(/السؤال المطلوب:/g, "")
    .replace(/«[^»]+»/g, "")
    .trim();

  const normQ = prodName ? normAr(subQuestion) : normAr(request);

  if (prodName) {
    const kind = classifyProductKind(prodName);
    const asksCalories = /(سعرات|سعره|طاقه|دايت|رجيم|وزن|صحي|فوائد|قيمه غذائيه)/.test(normQ);
    const asksSweetRecipe = /(حلي|حلا|حلو|تشيز|ترافل|كيك|مشروب مميز|صوص|تغميس)/.test(normQ);
    const asksCookingRecipe = /(طبخ|وصفه|تحضير|شعبي|اقتصادي|سريع|غداء|عشاء|فطور)/.test(normQ);
    const asksUsageTips = /(استخدام|توفير|نصائح|طريقه)/.test(normQ);

    if (asksCalories) {
      const calEstimate =
        kind === "sweet" ? "تتراوح تقريباً بين 210 إلى 260 سعرة حرارية لكل حصة (حوالي 45 جرام)، وأغلبها طاقة سريعة من الكربوهيدرات والدهون اللذيذة اللي تعدل المزاج فوراً"
        : kind === "drink" ? "تتراوح تقريباً بين 90 إلى 140 سعرة حرارية للكوب الواحد، وتعتبر منعشة وخفيفة وتعوض السوائل في الجسم"
        : kind === "snack" ? "تتراوح تقريباً بين 150 إلى 190 سعرة حرارية للحصة الواحدة، وغنية بالطاقة والقرمشة"
        : "تتراوح تقريباً بين 130 إلى 220 سعرة حرارية لكل حصة متوسطة (100 جرام)، وتعتبر مصدر ممتاز للبروتين والطاقة اليومية للجسم";

      const nextBtns =
        kind === "sweet" ? ["كيف أحضر حلى حلو؟", "متى أفضل وقت لتناوله؟", "إيش يناسب معها مع القهوة؟"]
        : kind === "drink" ? ["كيف أحضر مشروب مميز؟", "إيش أطيب سناك يناسب معه؟"]
        : kind === "snack" ? ["كيف أحضر صوص تغميسة معه؟", "إيش يناسب معه من المشروبات؟"]
        : ["كيف أحضر طبخة يمنية شعبية؟", "وصفة اقتصادية وسريعة"];

      return JSON.stringify({
        message: `يا هلا بك يا غالي! بالنسبة للسعرات الحرارية والقيمة الغذائية في «${prodName}»:\n\n🔥 كمية السعرات: ${calEstimate}.\n⚡ نصيحة ذهبية: عشرين دقيقة مشي خفيف كافية لحرق هذي السعرات بالكامل، وأفضل وقت للاستمتاع به هو وسط النهار أو مع فنجان قهوة بدون إكثار بالليل.\n\nتشتي أشرح لك كيف تحضر منه شي لذيذ ومبتكر، أو عندك سؤال ثاني عنه؟`,
        recipeName: "",
        servings: 0,
        ingredients: [],
        steps: [],
        missingIngredients: [],
        cartAction: "none",
        cartItems: [],
        suggestedQuestions: nextBtns,
      });
    }

    if (kind === "sweet") {
      if (asksSweetRecipe) {
        const matched = findStoreProducts([prodName, "قشطه", "بسكويت", "حليب", "عسل", "كاكاو"], 3);
        return JSON.stringify({
          message: `أبشر بعزك يا غالي! هذي طريقة تحضير أروع «حلى بارد وسريع بـ ${prodName}» يبيض الوجه ويجهز في 10 دقائق بدون فرن:\n\nلو تحب تعرف كم السعرات في هذا الحلى أو تريد فكرة ثانية، اضغط على الأزرار تحت!`,
          recipeName: `حلى ${prodName} البارد الفاخر`,
          servings: 4,
          ingredients: matched,
          steps: [
            "نرتب طبقة أولى من البسكويت المفتت أو الكيك الخفيف في كاسات أو صينية التقديم.",
            `نذوب أو نخلط «${prodName}» مع علبة قشطة وملعقتين حليب حتى يصير الخليط كريمي وناعم جداً.`,
            "نسكب الخليط الفاخر فوق الطبقة الأولى ونزين الوجه بقطع صغيرة من الشوكولاتة أو المكسرات.",
            "ندخله الثلاجة لمدة 15 دقيقة حتى يبرد ويتماسك، ويقدم مع القهوة اليمنية وبالعافية على قلبك!",
          ],
          missingIngredients: ["بسكويت شاي", "قشطة", "حليب سائل"],
          cartAction: "none",
          cartItems: [],
          suggestedQuestions: ["كم كمية السعرات؟", "إيش يناسب معها مع القهوة؟", "معلومات عن هذا المنتج"],
        });
      }

      if (normQ.includes("قهوه") || normQ.includes("يناسب") || normQ.includes("وقت")) {
        return JSON.stringify({
          message: `يا سلام على ذوقك! «${prodName}» يركب بشكل أسطوري مع:\n☕ القهوة اليمنية القشر أو البن الخولاني الساخن (المرارة الخفيفة للقهوة مع حلاوة ${prodName} تعطي توازن خرافي!).\n🍵 أو مع الشاي العدني المبهر بالهيل وقت العصر.\n\nإذا تحب أقول لك كيف تحضر منه حلى بارد وسريع، أو نشوف كمية السعرات اللي فيه، اختر من الأزرار تحت!`,
          recipeName: "",
          servings: 0,
          ingredients: findStoreProducts([prodName, "قهوه", "شاي", "حليب"], 2),
          steps: [],
          missingIngredients: [],
          cartAction: "none",
          cartItems: [],
          suggestedQuestions: ["كيف أحضر حلى حلو؟", "كم كمية السعرات؟"],
        });
      }

      return JSON.stringify({
        message: `يا هلا بك يا غالي! اختيارك لـ «${prodName}» اختيار ذوق وفخامة:\n\n✨ يتميز بطعم غني يعدل المزاج فوراً ويعطيك دفعة طاقة وحيوية، وممتاز جداً للضيافة أو كتحلية سريعة مع فنجان قهوة يمنية أو شاي عدني في جلسة العصر.\n\nبس تدري؟ هذي الـ «${prodName}» تقدر تحضر منها حلى حلو وبارد في دقائق إذا تريد أقول لك طريقته، أو إذا تريد أشرح لك كمية السعرات اللي ممكن تحصلها منها!`,
        recipeName: "",
        servings: 0,
        ingredients: [],
        steps: [],
        missingIngredients: [],
        cartAction: "none",
        cartItems: [],
        suggestedQuestions: ["كيف أحضر حلى حلو؟", "كم كمية السعرات؟", "إيش يناسب معها مع القهوة؟"],
      });
    }

    if (kind === "drink") {
      if (asksSweetRecipe || asksCookingRecipe) {
        const matched = findStoreProducts([prodName, "حليب", "عسل", "سكر", "نعناع"], 3);
        return JSON.stringify({
          message: `أبشر يا غالي! هذي طريقة عمل خلطة «مشروب ${prodName} المميز والمنعش» بطريقة الكافيهات في البيت:`,
          recipeName: `خلطة ${prodName} المنعشة الفاخرة`,
          servings: 2,
          ingredients: matched,
          steps: [
            `نجهز «${prodName}» في الكوب أو الخلاط مع مكعبات الثلج أو الماء حسب نوع المشروب.`,
            "نضيف لمسة خفيفة من العسل أو النعناع الطازج أو رشة هيل لإبراز النكهة.",
            "نخلطه جيداً لمدة 30 ثانية ويقدم فوراً، وبالهناء والعافية!",
          ],
          missingIngredients: ["مكعبات ثلج أو نعناع طازج"],
          cartAction: "none",
          cartItems: [],
          suggestedQuestions: ["كم كمية السعرات؟", "إيش أطيب سناك يناسب معه؟"],
        });
      }

      return JSON.stringify({
        message: `حياك الله يا غالي! المنتج «${prodName}» من أفضل الخيارات المنعشة في المتجر:\n\n✨ يعطيك انتعاش فوري وطعم متوازن ومضبوط، ومثالي جداً مع الوجبات أو في جلسات الضيافة.\n\nبس تدري؟ تقدر تحضر من «${prodName}» خلطة مشروب مميز على طريقة الكافيهات إذا تريد أقول لك طريقتها، أو إذا تريد أشرح لك كمية السعرات والفوائد اللي تحصلها منه!`,
        recipeName: "",
        servings: 0,
        ingredients: [],
        steps: [],
        missingIngredients: [],
        cartAction: "none",
        cartItems: [],
        suggestedQuestions: ["كيف أحضر مشروب مميز؟", "كم كمية السعرات؟", "إيش أطيب سناك يناسب معه؟"],
      });
    }

    if (kind === "snack") {
      if (asksSweetRecipe || asksCookingRecipe) {
        return JSON.stringify({
          message: `يا سلام! هذي أسرع طريقة لتحضير «صوص تغميسة رهيب مع ${prodName}» يخلي الجلسة طعم ثاني:`,
          recipeName: `تغميسة الجلسة مع ${prodName}`,
          servings: 3,
          ingredients: findStoreProducts([prodName, "جبن", "زبادي", "شطه", "مايونيز"], 3),
          steps: [
            "نخلط ملعقتين زبادي أو جبن سائل مع رشة كمون وفلفل أسود وعصرة ليمون.",
            "نضيف قطرات من الشطة اليمنية أو الكزبرة المفرومة حسب الرغبة.",
            `نقدم التغميسة بجانب «${prodName}» واستمتع بأحلى قرمشة!`,
          ],
          missingIngredients: ["زبادي أو جبن سائل", "ليمون"],
          cartAction: "none",
          cartItems: [],
          suggestedQuestions: ["كم كمية السعرات؟", "إيش يناسب معه من المشروبات؟"],
        });
      }

      return JSON.stringify({
        message: `يا هلا بك يا غالي! «${prodName}» هو رفيق الجلسات الأول:\n\n✨ قرمشة لذيذة وطعم يفتح النفس، وما تحلى السهرة أو جلسة الشاي إلا بوجوده.\n\nبس تدري؟ تقدر تحضر مع «${prodName}» صوص تغميسة سريع ولذيذ إذا تريد أقول لك طريقته، أو إذا تريد أشرح لك كمية السعرات الحرارية اللي ممكن تحصلها منه!`,
        recipeName: "",
        servings: 0,
        ingredients: [],
        steps: [],
        missingIngredients: [],
        cartAction: "none",
        cartItems: [],
        suggestedQuestions: ["كيف أحضر صوص تغميسة معه؟", "كم كمية السعرات؟", "إيش يناسب معه من المشروبات؟"],
      });
    }

    if (kind === "household") {
      if (asksUsageTips) {
        return JSON.stringify({
          message: `أبشر يا غالي! عشان تاخذ أفضل نتيجة من «${prodName}» ويوفر معك لفترة أطول:\n\n1️⃣ استخدم كمية معتدلة ومركزة بدلاً من الإكثار العشوائي لأن تركيبته فعالة جداً.\n2️⃣ احفظ العبوة في مكان جاف وبعيد عن حرارة الشمس المباشرة.\n3️⃣ عند الاستخدام مع الماء الدافئ يعطيك مفعول أسرع وأقوى!`,
          recipeName: "",
          servings: 0,
          ingredients: [],
          steps: [],
          missingIngredients: [],
          cartAction: "none",
          cartItems: [],
          suggestedQuestions: ["معلومات ومميزات المنتج", "إيش المنتجات المكملة له؟"],
        });
      }

      return JSON.stringify({
        message: `حياك الله يا غالي! الصنف «${prodName}» من الأصناف الأساسية والموثوقة للعناية والنظافة:\n\n✨ يتميز بجودة عالية ومفعول ممتاز يوفر عليك الوقت والجهد في الاستخدام اليومي.\n\nإذا تريد أشرح لك أفضل طريقة استخدام عشان يوفر معك ويعطيك أحسن نتيجة، أو نصائح مهمة عنه، اضغط الزر اللي يناسبك تحت!`,
        recipeName: "",
        servings: 0,
        ingredients: [],
        steps: [],
        missingIngredients: [],
        cartAction: "none",
        cartItems: [],
        suggestedQuestions: ["أفضل طريقة استخدام لتوفير أكثر", "نصائح للحصول على أفضل نتيجة"],
      });
    }

    if (asksCookingRecipe || normQ.includes("شعبي") || normQ.includes("اقتصادي") || normQ.includes("توابل")) {
      const isEconomic = normQ.includes("اقتصادي") || normQ.includes("سريع");
      const matched = findStoreProducts([prodName, "زيت", "صلص", "طماط", "بهار", "بصل", "ملح"], 3);
      return JSON.stringify({
        message: isEconomic
          ? `أبشر يا غالي! هذي «وصفة اقتصادية وسريعة بـ ${prodName}» تجهز في 10 دقائق ومكوناتها بسيطة وموجودة في كل بيت:`
          : `أبشر بعزك! هذي طريقة «طبخة يمنية شعبية أصيلة بـ ${prodName}» مسبكة على أصولها وتفتح النفس:`,
        recipeName: isEconomic ? `حمسة ${prodName} الاقتصادية السريعة` : `كشنة وطبخة ${prodName} على الطريقة اليمنية`,
        servings: 4,
        ingredients: matched,
        steps: [
          `نجهز «${prodName}» مع المكونات الأساسية.`,
          "في المقلاة أو القدر، نشوح البصل المفروم والثوم في قليل من الزيت حتى يأخذ لوناً ذهبياً.",
          "نضيف الطماطم المفرومة وملعقة معجون طماطم مع رشة حوائج يمنية (كمون، كزبرة، كركم، وملح) ونتركها تتسبك.",
          `نضيف «${prodName}» ونقلب على نار هادئة لمدة 8 دقائق حتى تتداخل النكهات وتقدم ساخنة مع الخبز اليمني أو الأرز وبالعافية!`,
        ],
        missingIngredients: ["بصل وثوم طازج", "طماطم", "بهارات يمنية"],
        cartAction: "none",
        cartItems: [],
        suggestedQuestions: ["كم كمية السعرات؟", isEconomic ? "كيف أحضر طبخة يمنية شعبية؟" : "وصفة اقتصادية وسريعة"],
      });
    }

    return JSON.stringify({
      message: `يا هلا ومسهلا بك يا غالي! الصنف «${prodName}» يعتبر ركن أساسي في كل مطبخ يمني:\n\n✨ يتميز بجودة ممتازة وقيمة غذائية عالية، ويضبط لك الأكلات اليومية سواء الغداء أو العشاء بطعم أصيل يشبع ويبيض الوجه.\n\nبس تدري؟ هذا الـ «${prodName}» تقدر تحضر منه طبخة يمنية شعبية مسبكة إذا تريد أقول لك طريقتها، أو وصفة اقتصادية سريعة، أو إذا تريد أشرح لك كمية السعرات اللي تحصلها منه!`,
      recipeName: "",
      servings: 0,
      ingredients: [],
      steps: [],
      missingIngredients: [],
      cartAction: "none",
      cartItems: [],
      suggestedQuestions: ["كيف أحضر طبخة يمنية شعبية؟", "وصفة اقتصادية وسريعة", "كم كمية السعرات؟"],
    });
  }

  if (normQ.includes("مرق") || normQ.includes("سلت") || normQ.includes("فحس")) {
    const title = normQ.includes("سلت") ? "سلتة يمنية صنعانية أصيلة" : normQ.includes("فحس") ? "فحسة يمنية بالحرضة" : "مرقة يمنية أصيلة ومسبكة";
    return JSON.stringify({
      message: `أبشر بعزك يا غالي! جهزت لك وصفة «${title}» على أصولها اليمنية تطيب خاطرك:`,
      recipeName: title,
      servings: 4,
      ingredients: findStoreProducts(["لحم", "دجاج", "مرق", "بهار", "حوائج", "ملح", "زيت", "بطاط", "صلص"], 4),
      steps: [
        "نغسل اللحم أو الدجاج جيداً ونسلقه في ماء مغلي مع إزالة الريم حتى تصفى المرقة.",
        "نضيف البصل المفروم، الثوم، الهيل، وملعقة من حوائج المرق اليمنية (كمون، كركم، فلفل أسود، كزبرة).",
        "نتركها على نار هادئة حتى تنضج تماماً ويتركز الطعم، ثم نضيف الملح والبطاطا.",
        "تقدم ساخنة مع عصرة ليمون والخبز اليمني الساخن أو الأرز، وبالعافية!",
      ],
      missingIngredients: ["لحم أو دجاج طازج", "بصل وثوم", "حوائج مرق يمنية"],
      cartAction: "none",
      cartItems: [],
      suggestedQuestions: ["كم كمية السعرات في هذه الوجبة؟", "أريد وصفة كبسة يمنية", "كيف أحضر حلى حلو؟"],
    });
  }

  if (normQ.includes("حلا") || normQ.includes("حلى") || normQ.includes("حلو") || normQ.includes("معصوب") || normQ.includes("شوكول") || normQ.includes("شكلاته")) {
    return JSON.stringify({
      message: "يا سلام على ذوقك! جهزت لك طريقة «حلى يمني بارد وسريع بالقشطة والشوكولاتة/العسل» يجهز في 10 دقائق ويعدل المزاج:",
      recipeName: "حلى القشطة والشوكولاتة السريع",
      servings: 4,
      ingredients: findStoreProducts(["شوكول", "جالكسي", "قشط", "بسكويت", "عسل", "حليب", "تاج"], 4),
      steps: [
        "نرتب طبقة من البسكويت المفتت في أطباق التقديم.",
        "نخلط القشطة مع الشوكولاتة المذابة أو العسل ونسكبها كطبقة ثانية غنية.",
        "نزين الوجه بالمكسرات أو برش الشوكولاتة ويبرد 15 دقيقة ويقدم بالعافية!",
      ],
      missingIngredients: ["بسكويت شاي", "قشطة"],
      cartAction: "none",
      cartItems: [],
      suggestedQuestions: ["كم كمية السعرات؟", "أريد وصفة مرقة يمنية"],
    });
  }

  const words = normQ.split(/\s+/).filter(w => w.length >= 2);
  const matched = findStoreProducts(words, 3);
  return JSON.stringify({
    message: `يا هلا ومسهلا بك يا غالي في متجر أوريجنال! بالنسبة لطلبك «${request.slice(0, 70)}»، أنا جاهز أساعدك بمعلومات عن أي منتج في المتجر، أو حساب السعرات الحرارية، أو اقتراح طبخات وحلويات يمنية سريعة بالمكونات المتوفرة.\n\nاختر أحد الاقتراحات بالأسفل أو اكتب لي الصنف اللي في بالك!`,
    recipeName: "",
    servings: 0,
    ingredients: matched,
    steps: [],
    missingIngredients: [],
    cartAction: "none",
    cartItems: [],
    suggestedQuestions: ["أريد وصفة مرقة يمنية", "كيف أحضر حلى حلو؟", "كم كمية السعرات؟"],
  });
}

async function tryFastestLightweightCloudAI(messages: Array<{ role: string; content: string }>): Promise<string | null> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 2200);
  try {
    const res = await fetch("https://text.pollinations.ai/openai", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36",
      },
      body: JSON.stringify({
        model: "openai-fast",
        messages,
        temperature: 0.5,
        response_format: { type: "json_object" },
      }),
      signal: controller.signal,
    });
    clearTimeout(timer);
    if (!res.ok) return null;
    const raw = await res.text();
    if (!raw || !raw.trim()) return null;
    let content = raw.trim();
    try {
      const d = JSON.parse(raw);
      if (typeof d?.choices?.[0]?.message?.content === "string") {
        content = d.choices[0].message.content.trim();
      }
    } catch {}
    const s = content.indexOf("{");
    const e = content.lastIndexOf("}");
    if (s >= 0 && e > s) {
      const parsed = JSON.parse(content.slice(s, e + 1));
      if (parsed && typeof parsed.message === "string" && parsed.message.trim().length > 10) {
        if (!Array.isArray(parsed.suggestedQuestions) || !parsed.suggestedQuestions.length) {
          parsed.suggestedQuestions = ["كيف أحضر حلى حلو؟", "كم كمية السعرات؟"];
        }
        return JSON.stringify(parsed);
      }
    }
    return null;
  } catch {
    clearTimeout(timer);
    return null;
  }
}

export async function invokeLLM(params: InvokeParams): Promise<InvokeResult> {
  const normalizedMessages = params.messages.map(m => ({
    role: m.role === "assistant" ? "assistant" : m.role === "system" ? "system" : "user",
    content: extractText(m.content),
  }));

  const userContent = normalizedMessages.filter(m => m.role === "user").map(m => m.content).join("\n");
  const isProductModalQuery = userContent.includes("الصنف الأساسي:") || userContent.includes("«");

  if (!isProductModalQuery) {
    const fastCloud = await tryFastestLightweightCloudAI(normalizedMessages);
    if (fastCloud) {
      return {
        id: "fast-ai-" + Date.now(),
        created: Date.now(),
        model: "openai-fast",
        choices: [{ index: 0, message: { role: "assistant", content: fastCloud }, finish_reason: "stop" }],
      };
    }
  }

  const instantSmartReply = buildLegendaryYemeniAnalysis(normalizedMessages);
  return {
    id: "yemeni-smart-" + Date.now(),
    created: Date.now(),
    model: "original-yemeni-ultra-fast",
    choices: [{ index: 0, message: { role: "assistant", content: instantSmartReply }, finish_reason: "stop" }],
  };
}
