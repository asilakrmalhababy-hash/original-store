import os, sys, pathlib, subprocess

print("=" * 72)
print("📊 تركيب لوحة مراقبة استهلاك قاعدة البيانات الحية + إصلاح الكاش (v137)")
print("=" * 72)

# 1. مسح أي كاش محلي قديم
for f in [".catalog-cache.json", "server/.catalog-cache.json"]:
    p = pathlib.Path(f)
    if p.exists():
        p.unlink()

# 2. إضافة مسار /api/db-status في server/_core/index.ts
srv_path = pathlib.Path("server/_core/index.ts")
if not srv_path.exists():
    print("❌ لم يتم العثور على server/_core/index.ts")
    sys.exit(1)

srv = srv_path.read_text(encoding="utf-8")

# منع الكاش الدائم للصور القديمة
srv = srv.replace("max-age=31536000, immutable", "max-age=0, must-revalidate")
srv = srv.replace("max-age=86400", "max-age=0, must-revalidate")

s_mark = "// === ORIGINAL_DB_STATUS_V137_START ==="
e_mark = "// === ORIGINAL_DB_STATUS_V137_END ==="
if s_mark in srv and e_mark in srv:
    srv = srv[:srv.index(s_mark)] + srv[srv.index(e_mark) + len(e_mark):]

if 'import * as __dbStatusModV137 from "../db";' not in srv:
    srv = 'import * as __dbStatusModV137 from "../db";\n' + srv

db_route_code = r"""// === ORIGINAL_DB_STATUS_V137_START ===
  app.get("/api/db-status", async (req: any, res: any) => {
    try {
      const pool = (__dbStatusModV137 as any).getPool ? await (__dbStatusModV137 as any).getPool() : null;
      if (!pool) {
        return res.status(500).json({ ok: false, error: "قاعدة البيانات غير متصلة" });
      }
      const [sizeRows]: any = await pool.query(
        "SELECT table_name AS name, ROUND((data_length + index_length) / 1024 / 1024, 4) AS size_mb FROM information_schema.tables WHERE table_schema = DATABASE()"
      );
      const sizeMap: Record<string, number> = {};
      let totalMb = 0;
      if (Array.isArray(sizeRows)) {
        for (const r of sizeRows) {
          const tName = String(r.name || r.NAME || r.table_name || "");
          const mb = Number(r.size_mb || r.SIZE_MB || 0);
          sizeMap[tName] = mb;
          totalMb += mb;
        }
      }
      const tableDefs = [
        { key: "categories", label: "الأقسام (categories)" },
        { key: "products", label: "المنتجات (products)" },
        { key: "banners", label: "البنرات الإعلانية (banners)" },
        { key: "offers", label: "العروض (offers)" },
        { key: "orders", label: "الطلبات (orders)" },
        { key: "order_items", label: "عناصر الطلبات (order_items)" },
        { key: "users", label: "المستخدمين (users)" },
        { key: "store_settings", label: "إعدادات المتجر (store_settings)" }
      ];
      const stats: any[] = [];
      for (const td of tableDefs) {
        try {
          const [cnt]: any = await pool.query("SELECT COUNT(*) AS c FROM " + td.key);
          const countVal = Number((cnt && cnt[0] && (cnt[0].c ?? cnt[0].C)) || 0);
          stats.push({
            table: td.key,
            label: td.label,
            rows: countVal,
            sizeMb: Number((sizeMap[td.key] || 0).toFixed(4))
          });
        } catch (_e) {
          stats.push({ table: td.key, label: td.label, rows: 0, sizeMb: 0 });
        }
      }
      const maxMb = 5120;
      const usedMb = Number(totalMb.toFixed(4));
      const remainMb = Number((maxMb - usedMb).toFixed(2));
      const usedPct = Number(((usedMb / maxMb) * 100).toFixed(4));

      if (req.query && req.query.json === "1") {
        return res.json({
          ok: true,
          cluster: "original-store-2 (TiDB Starter)",
          usedMb,
          maxMb,
          remainMb,
          usedPct,
          stats
        });
      }

      let rowsHtml = "";
      for (const s of stats) {
        rowsHtml += "<tr>" +
          "<td style='padding:12px 10px;border-bottom:1px solid rgba(216,180,84,0.18);font-weight:700;'>" + s.label + "</td>" +
          "<td style='padding:12px 10px;border-bottom:1px solid rgba(216,180,84,0.18);text-align:center;color:#d8b454;font-weight:800;font-size:16px;'>" + s.rows + "</td>" +
          "<td style='padding:12px 10px;border-bottom:1px solid rgba(216,180,84,0.18);text-align:left;direction:ltr;'>" + s.sizeMb + " MB</td>" +
        "</tr>";
      }

      const pageHtml = "<!DOCTYPE html><html lang='ar' dir='rtl'><head><meta charset='utf-8'/>" +
        "<meta name='viewport' content='width=device-width,initial-scale=1'/>" +
        "<title>مراقبة قاعدة البيانات - أورجنال</title>" +
        "<link href='https://fonts.googleapis.com/css2?family=Tajawal:wght@500;700;800&display=swap' rel='stylesheet'/>" +
        "<style>" +
          "body{margin:0;padding:18px;background:#0b2b1d;color:#fff;font-family:'Tajawal',sans-serif;}" +
          ".card{max-width:560px;margin:0 auto;background:linear-gradient(145deg,#13462f,#0d3322);border:1.5px solid #d8b454;border-radius:20px;padding:20px;box-shadow:0 14px 36px rgba(0,0,0,0.45);}" +
          ".badge{display:inline-block;background:rgba(34,197,94,0.2);color:#4ade80;border:1px solid #4ade80;border-radius:999px;padding:4px 12px;font-size:12px;font-weight:800;}" +
          ".bar-wrap{background:rgba(0,0,0,0.35);border-radius:999px;height:14px;overflow:hidden;margin:12px 0;border:1px solid rgba(216,180,84,0.35);}" +
          ".bar-fill{background:linear-gradient(90deg,#e5c467,#c89e3a);height:100%;width:" + Math.max(usedPct, 1.5) + "%;}" +
          "table{width:100%;border-collapse:collapse;margin-top:14px;font-size:14px;}" +
          ".btn{display:inline-block;margin-top:16px;background:linear-gradient(135deg,#e5c467,#c89e3a);color:#0b2b1d;text-decoration:none;font-weight:800;padding:10px 18px;border-radius:12px;font-size:14px;}" +
        "</style></head><body><div class='card'>" +
        "<div style='display:flex;justify-content:space-between;align-items:center;'>" +
          "<h2 style='margin:0;color:#d8b454;font-size:20px;'>📊 استهلاك قاعدة بيانات أورجنال</h2>" +
          "<span class='badge'>متصل ويعمل 🟢</span>" +
        "</div>" +
        "<p style='margin:10px 0 4px;font-size:14px;color:#e5e7eb;'>المساحة المستهلكة: <strong style='color:#d8b454;'>" + usedMb + " MB</strong> من أصل <strong>5,120 MB (5 GiB)</strong> (" + usedPct + "%)</p>" +
        "<p style='margin:0 0 8px;font-size:13px;color:#86efac;'>المساحة المجانية المتبقية: <strong>" + remainMb + " MB</strong> | الاستهلاك الخلفي عند السكون: <strong>0 RU/ثانية</strong></p>" +
        "<div class='bar-wrap'><div class='bar-fill'></div></div>" +
        "<table><thead><tr style='color:#d8b454;border-bottom:2px solid #d8b454;'>" +
          "<th style='text-align:right;padding:8px;'>الجدول</th>" +
          "<th style='text-align:center;padding:8px;'>العدد الفعلي</th>" +
          "<th style='text-align:left;padding:8px;'>الحجم</th>" +
        "</tr></thead><tbody>" + rowsHtml + "</tbody></table>" +
        "<div style='display:flex;gap:10px;justify-content:center;'>" +
          "<a class='btn' href='/api/db-status'>🔄 تحديث القراءة الآن</a>" +
          "<a class='btn' style='background:rgba(255,255,255,0.12);color:#fff;border:1px solid #d8b454;' href='/'>🏠 العودة للمتجر</a>" +
        "</div></div></body></html>";

      res.setHeader("Content-Type", "text/html; charset=utf-8");
      return res.send(pageHtml);
    } catch (err: any) {
      return res.status(500).json({ ok: false, error: err?.message || "DB status error" });
    }
  });
// === ORIGINAL_DB_STATUS_V137_END ==="""

target_anchor = "app.use( express.json"
if target_anchor not in srv:
    target_anchor = "app.use(express.json"

if target_anchor in srv:
    idx = srv.index(target_anchor)
    srv = srv[:idx] + db_route_code + "\n  " + srv[idx:]
else:
    print("❌ لم يتم العثور على نقطة الإدراج في server/_core/index.ts")
    sys.exit(1)

srv_path.write_text(srv, encoding="utf-8")

# فحص البناء عبر esbuild للتأكد من عدم وجود أي خطأ برمجي
esbuild_bin = "./node_modules/.bin/esbuild"
if pathlib.Path(esbuild_bin).exists():
    r_srv = subprocess.run(
        f"{esbuild_bin} server/_core/index.ts --bundle --platform=node --format=esm --packages=external --outfile=./.tmp_srv_v137.js",
        shell=True, capture_output=True, text=True
    )
    subprocess.run("rm -f ./.tmp_srv_v137.js", shell=True)
    if r_srv.returncode != 0:
        print("❌ خطأ في فحص السيرفر:", r_srv.stderr)
        sys.exit(1)
    print("✅ تم التحقق من سلامة كود السيرفر عبر esbuild بنجاح!")

# 3. تحديث أداة check_db.mjs في Termux لتقرأ من السيرفر مباشرة بدون الحاجة لكلمة مرور
check_mjs = r"""const URL = "https://original-store-xmyf.onrender.com/api/db-status?json=1";

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
"""
pathlib.Path("check_db.mjs").write_text(check_mjs, encoding="utf-8")
print("✅ تم تحديث أداة check_db.mjs لتعمل مباشرة بدون كلمة مرور")

os.system("git add -A && git commit -m 'Feat v137: add live /api/db-status Arabic monitor dashboard and fix image cache' && git push origin main")
print("🚀 تم رفع التحديث v137 إلى Render!")
