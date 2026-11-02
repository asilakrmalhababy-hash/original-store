const fs = require("fs");
const path = require("path");

const files = {
  schema: "drizzle/schema.ts",
  commerce: "server/commerce.ts",
  customer: "client/src/contexts/CustomerContext.tsx",
};

function read(key) {
  return fs.readFileSync(files[key], "utf8");
}
function save(key, content) {
  const file = files[key];
  fs.copyFileSync(file, file + ".backup-order-numbering");
  fs.writeFileSync(file, content);
}
function replaceOnce(text, from, to, label) {
  const first = text.indexOf(from);
  if (first < 0 || text.indexOf(from, first + from.length) >= 0) {
    throw new Error("تعذر تحديد موضع التعديل بأمان: " + label);
  }
  return text.slice(0, first) + to + text.slice(first + from.length);
}

try {
  let schema = read("schema");
  let commerce = read("commerce");
  let customer = read("customer");

  schema = replaceOnce(
    schema,
    'export const orderItems = mysqlTable("order_items", {',
    `export const orderNumberSequences = mysqlTable("order_number_sequences", {
  id: int("id").autoincrement().primaryKey(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export const orderItems = mysqlTable("order_items", {`,
    "جدول عداد الطلبات"
  );

  commerce = replaceOnce(
    commerce,
    "  orders,",
    "  orders,\n  orderNumberSequences,",
    "استيراد جدول العداد"
  );

  commerce = replaceOnce(
    commerce,
    'const orderNumber = "OR-" + Date.now().toString(36).toUpperCase() + "-" + nanoid(5).toUpperCase();',
    `const orderNumber = process.env.ORDER_NUMBER_MODE === "production"
          ? await (async () => {
              const sequence = await tx.insert(orderNumberSequences).values({});
              const number = Number(sequence[0].insertId);
              if (!Number.isSafeInteger(number) || number < 1) {
                throw new Error("تعذر إنشاء الرقم التسلسلي للطلب");
              }
              return "OR-" + String(number).padStart(6, "0");
            })()
          : "TEST-" + Date.now().toString(36).toUpperCase() + "-" + nanoid(5).toUpperCase();`,
    "توليد رقم الطلب"
  );

  customer = replaceOnce(
    customer,
    'const ORDER_NUMBER_PATTERN = /^OR-[A-Z0-9]+-[A-Z0-9]{5}$/;',
    'const ORDER_NUMBER_PATTERN = /^(?:OR-\\\\d{6,}|OR-[A-Z0-9]+-[A-Z0-9]{5}|TEST-[A-Z0-9-]+)$/;',
    "التحقق من أرقام الطلبات"
  );

  save("schema", schema);
  save("commerce", commerce);
  save("customer", customer);

  console.log("تم تعديل الملفات وحفظ النسخ الاحتياطية.");
} catch (error) {
  console.error("توقف التعديل:", error.message);
  process.exit(1);
}
