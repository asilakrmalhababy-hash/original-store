const fs = require("fs");
const file = "server/commerce.ts";
let source = fs.readFileSync(file, "utf8");

const oldText = `.orderBy(asc(products.sortOrder), desc(products.createdAt)).limit(500),`;
const newText = `.orderBy(asc(products.sortOrder), desc(products.createdAt)).limit(40),`;

if (!source.includes(oldText)) {
  console.error("لم أجد استعلام ذاكرة الصفحة الرئيسية. لم يتم تعديل الملف.");
  process.exit(1);
}

const backup = file + ".backup-home40-" + Date.now();
fs.copyFileSync(file, backup);
source = source.replace(oldText, newText);
fs.writeFileSync(file, source);

console.log("تم تقليل ذاكرة الصفحة الرئيسية إلى 40 منتجًا.");
console.log("النسخة الاحتياطية:", backup);
