const fs = require("fs");
const input = process.argv.slice(2).join(",");
const newKeys = input.split(/[\s,]+/).map(k => k.trim()).filter(k => k.length > 15);
if (newKeys.length === 0) {
  console.log("الاستخدام: node add-keys.cjs \"مفتاح1,مفتاح2,مفتاح3\"");
  process.exit(1);
}
let llm = fs.readFileSync("server/_core/llm.ts", "utf8");
const match = llm.match(/const ENCODED_KEYS: string\[\] = (\[[\s\S]*?\]);/);
let currentEncoded = match ? JSON.parse(match[1]) : [];
const currentDecoded = new Set(currentEncoded.map(b => Buffer.from(b, "base64").toString("utf8")));
for (const k of newKeys) currentDecoded.add(k);
const updatedEncoded = [...currentDecoded].map(k => Buffer.from(k).toString("base64"));
llm = llm.replace(/const ENCODED_KEYS: string\[\] = \[[\s\S]*?\];/, "const ENCODED_KEYS: string[] = " + JSON.stringify(updatedEncoded, null, 2) + ";");
fs.writeFileSync("server/_core/llm.ts", llm, "utf8");
console.log("✅ تم تشفير وحفظ إجمالي (" + updatedEncoded.length + ") مفاتيح بنجاح في نظام التناوب!");
