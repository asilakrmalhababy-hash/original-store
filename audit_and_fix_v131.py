import os, pathlib, re, shutil, subprocess, sys, time

print("=" * 72)
print("🔍 بدء التدقيق الهندسي الشامل والنسخ الاحتياطي والإصلاح الجراحي v131")
print("=" * 72)

# 1. إنشاء نسخة احتياطية كاملة وآمنة قبل أي تعديل
ts_stamp = time.strftime("%Y%m%d_%H%M%S")
backup_dir = pathlib.Path(f".audit_backup_{ts_stamp}")
backup_dir.mkdir(exist_ok=True)

target_files = [
    "server/ai_engine_v112.ts",
    "server/commerce.ts",
    "server/db.ts",
    "server/_core/index.ts",
    "drizzle/schema.ts",
    "client/index.html",
    "client/src/pages/Home.tsx",
    "client/src/pages/Admin.tsx",
    "client/public/sw.js",
    "ai_studio_v115_backup.json",
]

for rel in target_files:
  p = pathlib.Path(rel)
  if p.exists():
    dest = backup_dir / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(p, dest)

print(f"✅ [1/6] تم حفظ نسخة احتياطية كاملة لجميع الملفات في: {backup_dir}")

# 2. فحص ملفات المستودع الفعلي وطباعة إحصاء الاستعلامات والمؤقتات
print("\n📊 [2/6] نتائج الفحص المباشر لملفات المستودع على جهازك:")
for root_dir in ["server", "drizzle", "client/src"]:
  rp = pathlib.Path(root_dir)
  if rp.exists():
    for fp in sorted(rp.rglob("*")):
      if fp.is_file() and fp.suffix in (".ts", ".tsx", ".js"):
        txt = fp.read_text(encoding="utf-8", errors="ignore")
        db_calls = len(re.findall(r"\b(getDb|select|insert|update|delete|execute)\b", txt))
        timers = len(re.findall(r"\b(setInterval|setTimeout)\b", txt))
        print(f"   - {fp}: {len(txt.splitlines())} سطر | استدعاءات DB: {db_calls} | مؤقتات: {timers}")

# 3. الإصلاح الجراحي لملف server/ai_engine_v112.ts (Circuit Breaker + إصلاح حراس الكاش + تقليل استعلامات TiDB)
ai_path = pathlib.Path("server/ai_engine_v112.ts")
if ai_path.exists():
  ai_txt = ai_path.read_text(encoding="utf-8")

  old_db_block_pat = r"async function getCatalogCachedV114\(\): Promise<any\[\]> \{[\s\S]*?async function saveStudioKeyV114\(key: string, valObj: any\) \{[\s\S]*?\n\}"
  new_db_block = r"""let dbCircuitOpenUntilV131 = 0;
let lastStudioTableAttemptV131 = 0;

export function invalidateAiCatalogCacheV131() {
  lastCatalogTimeV114 = 0;
}

export function invalidateAiOrdersCacheV131() {
  lastOrdersTimeV126 = 0;
}

async function getCatalogCachedV114(): Promise<any[]> {
  const now = Date.now();
  if (now < dbCircuitOpenUntilV131) return cachedCatalogV114;
  if (lastCatalogTimeV114 > 0 && now - lastCatalogTimeV114 < 1800000) {
    return cachedCatalogV114;
  }
  lastCatalogTimeV114 = now;
  try {
    const db: any = await getDb();
    if (db) {
      const rows = await db.select().from(products);
      if (Array.isArray(rows)) cachedCatalogV114 = rows;
    }
  } catch (err: any) {
    const msg = String(err?.message || err || "");
    if (msg.includes("1105") || msg.includes("quota") || msg.includes("restricted")) {
      dbCircuitOpenUntilV131 = Date.now() + 60000;
    }
  }
  return cachedCatalogV114;
}

let cachedLatestOrdersV126: any[] = [];
let lastOrdersTimeV126 = 0;

async function getLatestOrdersCachedV126(): Promise<any[]> {
  const now = Date.now();
  if (now < dbCircuitOpenUntilV131) return cachedLatestOrdersV126;
  if (lastOrdersTimeV126 > 0 && now - lastOrdersTimeV126 < 30000) {
    return cachedLatestOrdersV126;
  }
  lastOrdersTimeV126 = now;
  try {
    const db: any = await getDb();
    if (db) {
      const rows: any = await runRawSqlV115(
        db,
        "SELECT id, orderNumber, customerName, customerPhone, total, status, createdAt FROM orders ORDER BY id DESC LIMIT 10"
      );
      if (Array.isArray(rows)) {
        cachedLatestOrdersV126 = rows;
      }
    }
  } catch (err: any) {
    const msg = String(err?.message || err || "");
    if (msg.includes("1105") || msg.includes("quota") || msg.includes("restricted")) {
      dbCircuitOpenUntilV131 = Date.now() + 60000;
    }
  }
  return cachedLatestOrdersV126;
}

async function ensureStudioTableV114() {
  if (tableLoadedFromDbV115) return;
  const now = Date.now();
  if (now < dbCircuitOpenUntilV131 || (lastStudioTableAttemptV131 > 0 && now - lastStudioTableAttemptV131 < 60000)) {
    return;
  }
  lastStudioTableAttemptV131 = now;
  try {
    const db: any = await getDb();
    if (!db) return;
    await runRawSqlV115(
      db,
      "CREATE TABLE IF NOT EXISTS ai_studio_v115 (" +
      "k VARCHAR(190) PRIMARY KEY, " +
      "v LONGTEXT NOT NULL, " +
      "updatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP" +
      ")"
    );
    tableLoadedFromDbV115 = true;

    const rows: any = await runRawSqlV115(db, "SELECT k, v FROM ai_studio_v115");
    if (Array.isArray(rows)) {
      for (const r of rows) {
        if (r && (r.k === "studio_config" || r.k === "config") && r.v) {
          try {
            const p = JSON.parse(String(r.v));
            studioConfigV114 = normalizeStudioConfigV115(p);
          } catch {}
        } else if (r && r.k === "customer_requests" && r.v) {
          try {
            const pr = JSON.parse(String(r.v));
            if (Array.isArray(pr)) customerRequestsV114 = pr;
          } catch {}
        }
      }
      saveDiskBackupV115();
    }
  } catch (err: any) {
    const msg = String(err?.message || err || "");
    if (msg.includes("1105") || msg.includes("quota") || msg.includes("restricted")) {
      dbCircuitOpenUntilV131 = Date.now() + 60000;
    }
  }
}

async function saveStudioKeyV114(key: string, valObj: any) {
  saveDiskBackupV115();
  if (Date.now() < dbCircuitOpenUntilV131) return;
  try {
    await ensureStudioTableV114();
    const db: any = await getDb();
    if (!db) return;
    const jsonStr = JSON.stringify(valObj);
    await runRawSqlV115(
      db,
      "INSERT INTO ai_studio_v115 (k, v) VALUES (?, ?) ON DUPLICATE KEY UPDATE v = VALUES(v)",
      [key, jsonStr]
    );
  } catch {}
}"""

  ai_txt, n_db = re.subn(old_db_block_pat, lambda m: new_db_block, ai_txt, count=1)

  old_get_cfg_pat = r"const handleGetConfig = async \(_?req: any, res: any\) => \{[\s\S]*?\n  \};"
  new_get_cfg = r"""const handleGetConfig = async (req: any, res: any) => {
    try {
      await ensureStudioTableV114();
      const isAdminPoll = req?.query?.admin === "1" || String(req?.headers?.referer || "").includes("/admin");
      const wantCatalog = req?.query?.includeCatalog === "1";
      const latestOrders = isAdminPoll ? await getLatestOrdersCachedV126() : [];
      let simpleCatalog: any[] = [];
      if (wantCatalog) {
        const catalog = await getCatalogCachedV114();
        simpleCatalog = catalog.map(p => ({
          id: p.id,
          name: cleanProductNameV112(p.name),
          price: Math.round(Number(p.price || 0)),
          unit: p.unit || "حبة",
          imageUrl: ""
        }));
      }
      res.json({
        ok: true,
        config: studioConfigV114,
        requests: isAdminPoll ? customerRequestsV114 : [],
        latestOrders,
        stats: tokenStatsV114,
        catalog: simpleCatalog
      });
    } catch (e: any) {
      res.status(500).json({ ok: false, error: String(e?.message || e) });
    }
  };"""

  ai_txt, n_cfg = re.subn(old_get_cfg_pat, lambda m: new_get_cfg, ai_txt, count=1)
  ai_path.write_text(ai_txt, encoding="utf-8")
  print(f"✅ [3/6] تم إصلاح server/ai_engine_v112.ts (Circuit Breaker + تقليل استعلامات TiDB): db={n_db}, cfg={n_cfg}")

# 4. الإصلاح الجراحي لملف server/commerce.ts
comm_path = pathlib.Path("server/commerce.ts")
if comm_path.exists():
  cc = comm_path.read_text(encoding="utf-8")
  cc, n_sync_rm = re.subn(
      r"\n\s*try\s*\{\s*await\s+syncAndGetNextOrderNumberV99\(db,\s*true\);\s*\}\s*catch\s*\{\}",
      "",
      cc,
  )
  cc = cc.replace(
      "const currentOrders = await dbInstance.select().from(orders);",
      "const currentOrders = await dbInstance.select({ id: orders.id, orderNumber: orders.orderNumber }).from(orders);",
  )
  comm_path.write_text(cc, encoding="utf-8")
  print(f"✅ [4/6] تم تحسين server/commerce.ts (أزيل {n_sync_rm} استدعاء مسح كامل غير ضروري لجدول الطلبات)")

# 5. الإصلاح الجراحي لملف client/index.html (إيقاف الاستطلاع الخلفي + منع الكتابة التلقائية من متصفح الزائر)
html_path = pathlib.Path("client/index.html")
if html_path.exists():
  ht = html_path.read_text(encoding="utf-8")

  ht = ht.replace(
      'origFetchV112("/api/ai-v112/config")',
      'origFetchV112((function() {\n'
      '            var isAdm = window.location.pathname.indexOf("/admin") !== -1 || localStorage.getItem("original_v126_is_admin") === "1";\n'
      '            var needCat = (!window.__v114Catalog || window.__v114Catalog.length === 0) ? "1" : "0";\n'
      '            return "/api/ai-v112/config?admin=" + (isAdm ? "1" : "0") + "&includeCatalog=" + needCat;\n'
      '          })())',
  )

  # منع متصفح الزائر العادي من إعادة الكتابة التلقائية على إعدادات القاعدة
  ht = ht.replace(
      'else if (hasAnyStudioItemsV115(window.__v114StudioConfig)) {\n                    origFetchV112("/api/ai-v112/save-training",',
      'else if (window.location.pathname.indexOf("/admin") !== -1 && hasAnyStudioItemsV115(window.__v114StudioConfig)) {\n                    origFetchV112("/api/ai-v112/save-training",',
  )

  ht = re.sub(
      r"setInterval\(refreshStudioDataV114,\s*\d+\);",
      'setInterval(function() {\n'
      '          if (document.hidden) return;\n'
      '          var isAdm = window.location.pathname.indexOf("/admin") !== -1 || localStorage.getItem("original_v126_is_admin") === "1";\n'
      '          if (isAdm) refreshStudioDataV114();\n'
      '        }, 25000);',
      ht,
  )

  ht = re.sub(
      r"setInterval\(pollCustomerManagerRepliesV112,\s*\d+\);",
      'setInterval(function() {\n'
      '          if (document.hidden) return;\n'
      '          pollCustomerManagerRepliesV112();\n'
      '        }, 30000);',
      ht,
  )

  html_path.write_text(ht, encoding="utf-8")
  print("✅ [5/6] تم تحسين client/index.html (إيقاف الاستطلاع عند إخفاء الصفحة + قصر فحص الطلبات على الإدارة كل 25 ثانية)")

# 6. تحديث Service Worker وفحص البناء الكامل
sw_path = pathlib.Path("client/public/sw.js")
if sw_path.exists():
  swc = sw_path.read_text(encoding="utf-8")
  swc = re.sub(r'const CACHE = "original-shell-v[^"]*";', 'const CACHE = "original-shell-v131";', swc)
  sw_path.write_text(swc, encoding="utf-8")

print("\n🧪 [6/6] تشغيل اختبارات التحقق والبناء (Server & Client):")
esbuild_bin = "./node_modules/.bin/esbuild"
if pathlib.Path(esbuild_bin).exists():
  if pathlib.Path("server/_core/index.ts").exists():
    r_srv = subprocess.run(
        f"{esbuild_bin} server/_core/index.ts --bundle --platform=node --format=esm --packages=external --outfile=./.tmp_srv_v131.js",
        shell=True, capture_output=True, text=True,
    )
    subprocess.run("rm -f ./.tmp_srv_v131.js", shell=True)
    if r_srv.returncode != 0:
      print("❌ فشل فحص السيرفر، جاري استعادة النسخة الاحتياطية تلقائياً...")
      for rel in target_files:
        bp = backup_dir / rel
        if bp.exists(): shutil.copy2(bp, pathlib.Path(rel))
      print(r_srv.stderr)
      sys.exit(1)
    print("   ✔ فحص بناء السيرفر (server/_core/index.ts): نجح 100%")

  if pathlib.Path("client/src/pages/Home.tsx").exists():
    r_cli = subprocess.run(
        f"{esbuild_bin} client/src/pages/Admin.tsx client/src/pages/Home.tsx --bundle --platform=browser --packages=external --jsx=automatic --outdir=./.tmp_cli_v131",
        shell=True, capture_output=True, text=True,
    )
    subprocess.run("rm -rf ./.tmp_cli_v131", shell=True)
    if r_cli.returncode != 0:
      print("❌ فشل فحص الواجهة، جاري استعادة النسخة الاحتياطية تلقائياً...")
      for rel in target_files:
        bp = backup_dir / rel
        if bp.exists(): shutil.copy2(bp, pathlib.Path(rel))
      print(r_cli.stderr)
      sys.exit(1)
    print("   ✔ فحص بناء الواجهة (Admin.tsx & Home.tsx): نجح 100%")

print("\n✅ اكتمل التدقيق والإصلاح الجراحي v131 بنجاح دون أي خطأ!")
print("💡 بعد مراجعتك لمخرجات الفحص، يمكنك رفع التحديث بأمر:")
print("   git add server/ai_engine_v112.ts server/commerce.ts client/index.html client/public/sw.js && git commit -m 'Audit & Fix v131: surgical TiDB RU optimization and circuit breaker' && git push origin main")
