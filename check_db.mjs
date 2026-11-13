const URL = "https://original-store-xmyf.onrender.com/api/db-status?json=1";

(async () => {
  console.log("==========================================================");
  console.log("📊 فحص حالة واستهلاك قاعدة البيانات الحية (original-store-2)");
  console.log("==========================================================");
  const res = await fetch(URL);
  if (!res.ok) {
    throw new Error("تأكد من اكتمال رفع التحديث على Render (HTTP " + res.status + ")");
  }
  const data = await res.json();
  if (!data.ok) {
    throw new Error(data.error || "خطأ غير معروف");
  }
  for (const row of data.stats) {
    console.log(
      " ✅ " +
        row.table.padEnd(16) +
        " : " +
        String(row.rows).padStart(5) +
        " صف فعلي | الحجم: " +
        row.sizeMb.toFixed(4) +
        " MB"
    );
  }
  console.log("----------------------------------------------------------");
  console.log("📦 إجمالي المساحة المستهلكة : " + data.usedMb + " MB من أصل " + data.maxMb + " MB (" + data.usedPct + "%)");
  console.log("🟢 المساحة المجانية المتبقية : " + data.remainMb + " MB");
  console.log("🌐 رابط المراقبة من المتصفح  : https://original-store-xmyf.onrender.com/api/db-status");
  console.log("==========================================================");
})().catch((e) => {
  console.error("⚠️ تنبيه:", e.message);
});
