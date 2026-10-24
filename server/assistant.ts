import { z } from "zod";

export const assistantModelOutputSchema = z.object({
  message: z.string().trim().min(1).max(1200),
  recipeName: z.string().trim().max(160),
  servings: z.number().int().min(0).max(50),
  ingredients: z.array(z.object({
    productId: z.number().int().positive(),
    quantity: z.number().int().positive().max(10000),
  }).strict()).max(40),
  steps: z.array(z.string().trim().min(1).max(500)).max(20),
  missingIngredients: z.array(z.string().trim().min(1).max(120)).max(30),
  cartAction: z.enum(["none", "add", "remove"]),
  suggestedQuestions: z.array(z.string().trim().min(1).max(120)).max(6).optional(),
  cartItems: z.array(z.object({
    productId: z.number().int().positive(),
    quantity: z.number().int().min(0).max(10000),
  }).strict()).max(20),
}).strict();

export type AssistantModelOutput = z.infer<typeof assistantModelOutputSchema>;

export type AssistantCatalogProduct = {
  id: number;
  name: string;
  description: string | null;
  price: number;
  unit: string;
  stock: number | null;
  minQuantity: number;
  quantityStep: number;
};

export type AssistantCartInputLine = { productId: number; quantity: number };
export type AssistantHistoryTurn = { role: "user" | "assistant"; text: string };
export type AssistantProductLine = Omit<AssistantCatalogProduct, "id" | "description"> & { productId: number; quantity: number };
export type PreparedAssistantResponse = {
  message: string;
  recipe: { name: string; servings: number; steps: string[] } | null;
  ingredients: AssistantProductLine[];
  missingIngredients: string[];
  cartAction: { type: "add" | "remove"; items: AssistantProductLine[] } | null;
  suggestedQuestions?: string[];
};

export const assistantResponseJsonSchema = {
  type: "object",
  properties: {
    message: { type: "string" },
    recipeName: { type: "string" },
    servings: { type: "integer", minimum: 0, maximum: 50 },
    ingredients: { type: "array", items: { type: "object" } },
    steps: { type: "array", items: { type: "string" } },
    missingIngredients: { type: "array", items: { type: "string" } },
    cartAction: { type: "string", enum: ["none", "add", "remove"] },
    cartItems: { type: "array", items: { type: "object" } },
  },
  required: ["message", "recipeName", "servings", "ingredients", "steps", "missingIngredients", "cartAction", "cartItems"],
} as const;

export function contentToText(content: unknown): string | null {
  if (typeof content === "string") return content.trim() || null;
  if (!Array.isArray(content)) return null;
  const text = content.flatMap(part => {
    if (part && typeof part === "object" && "text" in part && typeof part.text === "string") return [part.text];
    return [];
  }).join("\n").trim();
  return text || null;
}

export function parseAssistantModelContent(content: unknown): AssistantModelOutput | null {
  const text = contentToText(content);
  if (!text) return null;
  const unfenced = text.replace(/^\s*```(?:json)?\s*/i, "").replace(/\s*```\s*$/, "").trim();
  const start = unfenced.indexOf("{");
  const end = unfenced.lastIndexOf("}");
  if (start >= 0 && end > start) {
    try {
      const raw: any = JSON.parse(unfenced.slice(start, end + 1));
      if (raw && typeof raw === "object" && typeof raw.message === "string") {
        return {
          message: raw.message.slice(0, 1200),
          recipeName: typeof raw.recipeName === "string" ? raw.recipeName.trim().slice(0, 160) : "",
          servings: typeof raw.servings === "number" ? Math.max(0, Math.min(50, Math.floor(raw.servings))) : 0,
          ingredients: Array.isArray(raw.ingredients)
            ? raw.ingredients
                .filter((i: any) => i && Number.isInteger(Number(i.productId)) && Number(i.productId) > 0)
                .map((i: any) => ({ productId: Number(i.productId), quantity: Math.max(1, Math.min(10000, Math.floor(Number(i.quantity) || 1))) }))
            : [],
          steps: Array.isArray(raw.steps) ? raw.steps.map((s: any) => String(s || "").trim()).filter(Boolean).slice(0, 20) : [],
          missingIngredients: Array.isArray(raw.missingIngredients) ? raw.missingIngredients.map((s: any) => String(s || "").trim()).filter(Boolean).slice(0, 30) : [],
          cartAction: raw.cartAction === "add" || raw.cartAction === "remove" ? raw.cartAction : "none",
          suggestedQuestions: Array.isArray(raw.suggestedQuestions) ? raw.suggestedQuestions : [],
          cartItems: Array.isArray(raw.cartItems)
            ? raw.cartItems
                .filter((i: any) => i && Number.isInteger(Number(i.productId)) && Number(i.productId) > 0)
                .map((i: any) => ({ productId: Number(i.productId), quantity: Math.max(0, Math.min(10000, Math.floor(Number(i.quantity) ?? 1))) }))
            : [],
        };
      }
    } catch {}
  }
  return null;
}

function normalizeProductQuantity(product: AssistantCatalogProduct, quantity: number) {
  const minimum = Math.max(1, product.minQuantity || 1);
  const step = Math.max(1, product.quantityStep || 1);
  return minimum + Math.ceil(Math.max(0, quantity - minimum) / step) * step;
}

function maximumValidQuantity(product: AssistantCatalogProduct, available: number) {
  const minimum = Math.max(1, product.minQuantity || 1);
  const step = Math.max(1, product.quantityStep || 1);
  if (available < minimum) return 0;
  return minimum + Math.floor((available - minimum) / step) * step;
}

function productLine(product: AssistantCatalogProduct, quantity: number): AssistantProductLine {
  return {
    productId: product.id,
    name: product.name,
    price: product.price,
    unit: product.unit,
    stock: product.stock,
    minQuantity: product.minQuantity,
    quantityStep: product.quantityStep,
    quantity,
  };
}

function uniqueNames(values: string[]) {
  const seen = new Set<string>();
  return values.map(v => v.trim()).filter(v => {
    if (!v) return false;
    const key = v.toLocaleLowerCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  }).slice(0, 30);
}

export function prepareAssistantResponse(
  output: AssistantModelOutput,
  catalog: AssistantCatalogProduct[],
  cartLines: AssistantCartInputLine[],
): PreparedAssistantResponse {
  const catalogById = new Map(catalog.map(product => [product.id, product]));
  const cartQuantityById = new Map<number, number>();
  for (const line of cartLines) {
    if (!Number.isSafeInteger(line.productId) || !Number.isSafeInteger(line.quantity) || line.quantity <= 0) continue;
    if (!catalogById.has(line.productId)) continue;
    cartQuantityById.set(line.productId, Math.min(100000, (cartQuantityById.get(line.productId) ?? 0) + line.quantity));
  }

  const missing = [...output.missingIngredients];
  const ingredientQuantities = new Map<number, number>();
  for (const ingredient of output.ingredients) {
    ingredientQuantities.set(ingredient.productId, Math.min(10000, (ingredientQuantities.get(ingredient.productId) ?? 0) + ingredient.quantity));
  }
  const ingredients: AssistantProductLine[] = [];
  for (const [productId, requestedQuantity] of ingredientQuantities) {
    const product = catalogById.get(productId);
    if (!product) continue;
    const quantity = normalizeProductQuantity(product, requestedQuantity);
    if (product.stock !== null && quantity > product.stock) {
      const availableQuantity = maximumValidQuantity(product, product.stock);
      if (availableQuantity > 0) ingredients.push(productLine(product, availableQuantity));
      missing.push(availableQuantity > 0
        ? `${product.name} — المطلوب ${quantity} ${product.unit}، والمتوفر الآن ${availableQuantity} ${product.unit}`
        : product.name);
      continue;
    }
    ingredients.push(productLine(product, quantity));
  }

  const missingIngredients = uniqueNames(missing);
  const hasRecipe = Boolean(output.recipeName && (output.steps.length > 0 || ingredients.length > 0 || missingIngredients.length > 0));
  const message = output.message;

  let cartAction: PreparedAssistantResponse["cartAction"] = null;
  if (output.cartAction !== "none" && output.cartItems.length > 0) {
    const requestedById = new Map<number, number>();
    for (const item of output.cartItems) {
      if (!catalogById.has(item.productId)) continue;
      requestedById.set(item.productId, Math.min(10000, (requestedById.get(item.productId) ?? 0) + item.quantity));
    }

    const preparedItems: AssistantProductLine[] = [];
    for (const [productId, requestedQuantity] of requestedById) {
      const product = catalogById.get(productId)!;
      const inCart = cartQuantityById.get(productId) ?? 0;
      if (output.cartAction === "remove") {
        if (inCart <= 0) continue;
        const quantity = requestedQuantity === 0 ? inCart : Math.min(requestedQuantity, inCart);
        preparedItems.push(productLine(product, quantity));
        continue;
      }
      if (requestedQuantity <= 0) continue;
      const normalized = normalizeProductQuantity(product, requestedQuantity);
      const remaining = product.stock === null ? Number.POSITIVE_INFINITY : Math.max(0, product.stock - inCart);
      const allowed = maximumValidQuantity(product, remaining);
      if (allowed <= 0) continue;
      preparedItems.push(productLine(product, Math.min(normalized, allowed)));
    }

    if (preparedItems.length > 0) cartAction = { type: output.cartAction, items: preparedItems };
  }

  return {
    message,
    recipe: hasRecipe ? { name: output.recipeName, servings: output.servings, steps: output.steps } : null,
    ingredients,
    missingIngredients: hasRecipe ? missingIngredients : [],
    cartAction,
    suggestedQuestions: output.suggestedQuestions ?? [],
  };
}
