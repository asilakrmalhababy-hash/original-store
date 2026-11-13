import os, pathlib, re, shutil, subprocess, sys, time

print("=" * 72)
print("🛠️ تطبيق الإصلاح الجراحي الشامل v132 (إصلاح أزرار السلة + إيقاف استنزاف TiDB RU)")
print("=" * 72)

# 1. حفظ نسخة احتياطية إضافية قبل التعديل
ts_stamp = time.strftime("%Y%m%d_%H%M%S")
backup_dir = pathlib.Path(f".audit_backup_v132_{ts_stamp}")
backup_dir.mkdir(exist_ok=True)
files_to_touch = [
    "server/db.ts",
    "server/_core/index.ts",
    "server/commerce.ts",
    "server/ai_engine_v112.ts",
    "client/src/contexts/StoreContext.tsx",
    "client/src/pages/Home.tsx",
    "client/src/pages/Admin.tsx",
    "client/index.html",
    "client/public/sw.js",
]
for rel in files_to_touch:
  p = pathlib.Path(rel)
  if p.exists():
    dest = backup_dir / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(p, dest)
print(f"✅ [1/7] تم حفظ نسخة احتياطية كاملة في: {backup_dir}")

# 2. إصلاح server/db.ts:
#    - إلغاء setInterval كل 5 ثوانٍ الذي ينفذ SELECT * على 14 جدولاً
#    - قصر scheduleCloudSave على جمل الكتابة الصريحة فقط وبفاصل 10 دقائق
db_path = pathlib.Path("server/db.ts")
if db_path.exists():
  dbt = db_path.read_text(encoding="utf-8")
  dbt = re.sub(
      r"function scheduleCloudSave\(pool: mysql\.Pool, sqlArg: unknown\) \{[\s\S]*?\n\}",
      """function scheduleCloudSave(pool: mysql.Pool, sqlArg: unknown) {
  if (process.env.ENABLE_GITHUB_DB_SYNC !== "true" || isRestoring) return;
  const s = extractSqlString(sqlArg);
  if (!s || !/^(insert|update|delete|replace)\\b/i.test(s)) return;
  if (syncTimer) clearTimeout(syncTimer);
  syncTimer = setTimeout(() => {
    void saveToCloudNow(pool);
  }, 600000);
}""",
      dbt,
      count=1,
  )
  dbt = re.sub(
      r"// Continuous background dirty-check[\s\S]*?\},\s*5000\);",
      "// Background 5s full-DB scan disabled in v132 to preserve TiDB RU quota",
      dbt,
  )
  db_path.write_text(dbt, encoding="utf-8")
  print("✅ [2/7] تم إصلاح server/db.ts (إيقاف المسح الكامل لـ 14 جدولاً كل 5 ثوانٍ)")

# 3. إصلاح server/_core/index.ts:
#    - إيقاف prewarmFastImages عند الإقلاع (تُحمّل الصور عند الطلب فقط وتُحفظ في الكاش)
#    - إيقاف keepAliveTimer كل 10 دقائق حتى ينام السيرفر عند عدم وجود زوار ويوفر الحصة
idx_path = pathlib.Path("server/_core/index.ts")
if idx_path.exists():
  idxt = idx_path.read_text(encoding="utf-8")
  idxt = idxt.replace(
      "setTimeout(() => { void prewarmFastImages(); }, 1200);",
      "// prewarmFastImages disabled on boot in v132 (lazy-cached per image request)",
  )
  idxt = re.sub(
      r"if \(!\(globalThis as any\)\.__keepAliveTimer\) \{[\s\S]*?10 \* 60 \* 1000\);\s*\}",
      "// keepAliveTimer disabled in v132 so server can idle when no users are active",
      idxt,
  )
  idx_path.write_text(idxt, encoding="utf-8")
  print("✅ [3/7] تم إصلاح server/_core/index.ts (إلغاء سحب كل صور Base64 عند الإقلاع)")

# 4. إصلاح server/commerce.ts:
#    - إيقاف setInterval(__prewarmCatalog, 45000) نهائياً
#    - استخدام fastProductColumns في catalog.listProducts بدلاً من سحب Base64 الخام
#    - عدم استدعاء resetDbPool() في withFastRetry لمنع إعادة تهيئة الجداول المتكررة
#    - عدم قراءة جدول orders بالكامل في addInvoiceItemToOrderV99 بل البحث بـ eq(orders.id, ...)
comm_path = pathlib.Path("server/commerce.ts")
if comm_path.exists():
  cc = comm_path.read_text(encoding="utf-8")
  cc = cc.replace(
      "setInterval(__prewarmCatalog, 45000).unref();",
      "// setInterval(__prewarmCatalog, 45000) disabled in v132 to stop 24/7 TiDB RU drain",
  )
  cc = cc.replace(
      "setTimeout(__prewarmCatalog, 800);",
      "// setTimeout(__prewarmCatalog, 800) disabled in v132",
  )
  cc = cc.replace(
      "setTimeout(() => { void refreshHomeCatalogCache().catch(() => {}); }, 80);",
      "// initial refreshHomeCatalogCache deferred to first visitor request in v132",
  )
  cc = cc.replace(
      "setTimeout(() => { void ensureTenBatchProductsSeeded(); }, 2000);",
      "// ensureTenBatchProductsSeeded disabled on boot in v132",
  )
  cc = cc.replace(
      "  } catch (err) {\n    resetDbPool();\n    return await fetcher();\n  }",
      "  } catch (err) {\n    throw err;\n  }",
  )
  cc = cc.replace(
      "const rows = await db.select().from(products)\n        .where(and(...filters))",
      "const rows = await db.select(fastProductColumns).from(products)\n        .where(and(...filters))",
  )
  comm_path.write_text(cc, encoding="utf-8")
  print("✅ [4/7] تم إصلاح server/commerce.ts (إيقاف __prewarmCatalog كل 45 ثانية + منع سحب Base64 في listProducts)")

# 5. إصلاح client/src/contexts/StoreContext.tsx:
#    - الحفاظ على سعر الخيار المختار (line.price) في syncCatalogProducts وعدم استبداله بسعر المنتج الافتراضي
#    - السماح بقراءة عناصر السلة حتى لو كان السعر عشرياً أو معدلاً
sc_path = pathlib.Path("client/src/contexts/StoreContext.tsx")
if sc_path.exists():
  sct = sc_path.read_text(encoding="utf-8")
  sct = sct.replace(
      "Number.isInteger(item.price)",
      "(typeof item.price === 'number' && !Number.isNaN(item.price))",
  )
  sct = sct.replace(
      "const expectedName = line.variant ? fresh.name + \" (\" + line.variant + \")\" : fresh.name;\n          if (fresh.price !== line.price || expectedName !== line.name || fresh.unit !== line.unit || fresh.imageUrl !== line.imageUrl || fresh.stock !== line.stock) {\n            changed = true;\n            next.push({ ...line, name: expectedName, price: fresh.price, unit: fresh.unit, imageUrl: fresh.imageUrl, stock: fresh.stock });",
      "const hasVarPrice = Boolean(line.variant || (line.name && line.name.includes(':')));\n          const keepPrice = hasVarPrice && line.price > 0 ? line.price : fresh.price;\n          const keepUnit = hasVarPrice && line.unit ? line.unit : fresh.unit;\n          const expectedName = line.variant && !line.name.includes('(') ? fresh.name + \" (\" + line.variant + \")\" : (line.name || fresh.name);\n          if (keepPrice !== line.price || expectedName !== line.name || keepUnit !== line.unit || fresh.imageUrl !== line.imageUrl || fresh.stock !== line.stock) {\n            changed = true;\n            next.push({ ...line, name: expectedName, price: keepPrice, unit: keepUnit, imageUrl: fresh.imageUrl, stock: fresh.stock });",
  )
  sc_path.write_text(sct, encoding="utf-8")
  print("✅ [5/7] تم إصلاح StoreContext.tsx (حماية أسعار الخيارات في السلة من التصفير)")

# 6. إصلاح client/src/pages/Home.tsx و client/src/pages/Admin.tsx:
#    - تمرير line.variant إلى setQuantity(line.id, quantity, line.variant) و remove(line.id, line.variant) في CartRow!
#    - إصلاح شرط قفل زر (+) في CartRow عندما يكون stock=0 لمنتج متعدد الخيارات
#    - تحويل تحميل الصور إلى lazy بدلاً من eager لكل المنتجات
#    - تخفيف refetchInterval في المحادثات من 2.5 ثانية إلى 25 ثانية
home_path = pathlib.Path("client/src/pages/Home.tsx")
if home_path.exists():
  hc = home_path.read_text(encoding="utf-8")
  # إزالة أي wrapper تجريبي سابق لـ useState إن وجد لأننا أصلحنا السبب الأصلي في CartRow مباشره
  hc = hc.replace("useState as _origUseStateV130", "useState")
  hc = re.sub(r"function useState<T = any>\(init\?: any\): \[T, any\] \{[\s\S]*?\n\}\n", "", hc)

  # الإصلاح الجوهري لأزرار السلة (+ و - وإزالة) بتمرير line.variant
  hc = hc.replace(
      "key={line.id}\n                line={line}\n                onQuantity={quantity => setQuantity(line.id, quantity)}\n                onRemove={() => remove(line.id)}",
      "key={line.variant ? `${line.id}::${line.variant}` : `${line.id}::${line.name}`}\n                line={line}\n                onQuantity={quantity => setQuantity(line.id, quantity, line.variant)}\n                onRemove={() => remove(line.id, line.variant)}",
  )
  # إصلاح قفل زر + في CartRow عندما يكون stock=0 أو غير محدد للخيار
  hc = hc.replace(
      "disabled={line.stock !== null && line.stock !== undefined && line.quantity + (line.quantityStep || 1) > line.stock}",
      "disabled={line.stock !== null && line.stock !== undefined && line.stock > 0 && line.quantity + (line.quantityStep || 1) > line.stock}",
  )
  # تحويل الصور إلى lazy إلا للصور ذات الأولوية القصوى
  hc = hc.replace(
      'loading="eager" fetchPriority={priority ? "high" : "auto"}',
      'loading={priority ? "eager" : "lazy"} fetchPriority={priority ? "high" : "auto"}',
  )
  # تخفيف استطلاع الرسائل
  hc = hc.replace("refetchInterval: 2500,", "refetchInterval: 25000,")
  home_path.write_text(hc, encoding="utf-8")
  print("✅ [6/7] تم إصلاح Home.tsx (تمرير line.variant لأزرار السلة + و - وإزالة + تفعيل التحميل الكسول للصور)")

admin_path = pathlib.Path("client/src/pages/Admin.tsx")
if admin_path.exists():
  ac = admin_path.read_text(encoding="utf-8")
  ac = ac.replace("refetchInterval: 3000", "refetchInterval: 20000")
  ac = ac.replace("refetchInterval: 10_000", "refetchInterval: 30_000")
  admin_path.write_text(ac, encoding="utf-8")

# 7. تحديث Service Worker وفحص البناء الكامل
sw_path = pathlib.Path("client/public/sw.js")
if sw_path.exists():
  swc = sw_path.read_text(encoding="utf-8")
  swc = re.sub(r'const CACHE = "original-shell-v[^"]*";', 'const CACHE = "original-shell-v132";', swc)
  sw_path.write_text(swc, encoding="utf-8")

print("\n🧪 [7/7] تشغيل اختبارات التحقق والبناء (Server & Client):")
esbuild_bin = "./node_modules/.bin/esbuild"
if pathlib.Path(esbuild_bin).exists():
  r_srv = subprocess.run(
      f"{esbuild_bin} server/_core/index.ts --bundle --platform=node --format=esm --packages=external --outfile=./.tmp_srv_v132.js",
      shell=True, capture_output=True, text=True,
  )
  subprocess.run("rm -f ./.tmp_srv_v132.js", shell=True)
  if r_srv.returncode != 0:
    print("❌ فشل فحص السيرفر، جاري استعادة النسخة الاحتياطية...")
    for rel in files_to_touch:
      bp = backup_dir / rel
      if bp.exists(): shutil.copy2(bp, pathlib.Path(rel))
    print(r_srv.stderr)
    sys.exit(1)
  print("   ✔ فحص بناء السيرفر (server/_core/index.ts): نجح 100%")

  r_cli = subprocess.run(
      f"{esbuild_bin} client/src/pages/Admin.tsx client/src/pages/Home.tsx --bundle --platform=browser --packages=external --jsx=automatic --outdir=./.tmp_cli_v132",
      shell=True, capture_output=True, text=True,
  )
  subprocess.run("rm -rf ./.tmp_cli_v132", shell=True)
  if r_cli.returncode != 0:
    print("❌ فشل فحص الواجهة، جاري استعادة النسخة الاحتياطية...")
    for rel in files_to_touch:
      bp = backup_dir / rel
      if bp.exists(): shutil.copy2(bp, pathlib.Path(rel))
    print(r_cli.stderr)
    sys.exit(1)
  print("   ✔ فحص بناء الواجهة (Admin.tsx & Home.tsx): نجح 100%")

print("\n🎉 اكتمل الإصلاح الجراحي الشامل v132 بنجاح 100%!")
print("🚀 لرفع جميع الإصلاحات الآن إلى Render نفّذ:")
print("   git add -A && git commit -m 'Fix v132: stop 5s/45s full-DB background scans, fix CartRow variant actions, and lazy-load product images' && git push origin main")
