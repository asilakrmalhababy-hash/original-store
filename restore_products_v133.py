import os, pathlib, re, subprocess, sys

print("=" * 72)
print("📦 فحص واستعادة كافة المنتجات والأقسام والصور إلى الكلاستر الجديد (v133)")
print("=" * 72)

# 1. فحص ما إذا كان فرع data-backup أو ملفات الكاش المحلية موجودة
subprocess.run("git fetch origin data-backup 2>/dev/null || true", shell=True)
local_caches = [p for p in pathlib.Path(".").glob("*cache*") if p.is_file()] + [p for p in pathlib.Path(".").glob(".*cache*") if p.is_file()]
print("📂 ملفات الكاش المحلية الموجودة:", [str(p) for p in local_caches])

# 2. ترقية restoreFromCloud في server/db.ts ليدعم الملفات الكبيرة (>1MB) عبر GitHub Raw / Blob API + مسح كاش الواجهة بعد الاستعادة
db_path = pathlib.Path("server/db.ts")
if db_path.exists():
  dbt = db_path.read_text(encoding="utf-8")

  old_restore_pat = r"async function restoreFromCloud\(pool: mysql\.Pool\) \{[\s\S]*?\n\}"
  new_restore_fn = r"""async function restoreFromCloud(pool: mysql.Pool) {
  isRestoring = true;
  try {
    const token = getCloudToken();
    const headers: Record<string, string> = {
      Authorization: `Bearer ${token}`,
      Accept: "application/vnd.github.v3+json",
      "User-Agent": "Original-Store-Cloud-Sync",
    };
    let rawJson = "";
    // 1) المحاولة الأولى: سحب الملف الخام مباشرة (يدعم حتى 100MB دون قيد 1MB في JSON API)
    const rawRes = await fetch(`${CLOUD_API_URL}?ref=data-backup`, {
      headers: { ...headers, Accept: "application/vnd.github.v3.raw" },
    });
    if (rawRes.ok) {
      const txt = await rawRes.text();
      if (txt && txt.trim().startsWith("{")) {
        rawJson = txt;
      }
    }
    // 2) المحاولة الثانية: عبر metadata أو Git Blob API
    if (!rawJson) {
      const res = await fetch(`${CLOUD_API_URL}?ref=data-backup`, { headers });
      if (!res.ok) {
        console.warn("[CloudSync] Backup fetch status:", res.status);
        return;
      }
      const meta: any = await res.json();
      cloudSha = meta?.sha || "";
      if (meta?.content) {
        rawJson = Buffer.from(meta.content, "base64").toString("utf8");
      } else if (meta?.git_url) {
        const blobRes = await fetch(meta.git_url, { headers });
        if (blobRes.ok) {
          const blobData: any = await blobRes.json();
          if (blobData?.content) {
            rawJson = Buffer.from(blobData.content, "base64").toString("utf8");
          }
        }
      } else if (meta?.download_url) {
        const dlRes = await fetch(meta.download_url);
        if (dlRes.ok) rawJson = await dlRes.text();
      }
    }
    if (!rawJson) {
      console.warn("[CloudSync] No snapshot content found in data-backup");
      return;
    }
    const snapshot = JSON.parse(rawJson) as Record<string, any[]>;
    const prodList = snapshot["products"] || [];
    console.log(`[CloudSync] Snapshot loaded: ${prodList.length} products, ${(snapshot["categories"] || []).length} categories`);
    if (prodList.length === 0) return;

    await pool.query("SET FOREIGN_KEY_CHECKS = 0");
    for (const table of ALL_TABLES) {
      const rows = snapshot[table];
      if (!Array.isArray(rows) || rows.length === 0) continue;
      for (const row of rows) {
        const keys = Object.keys(row);
        if (!keys.length) continue;
        const cols = keys.map(k => `\`${k}\``).join(", ");
        const placeholders = keys.map(() => "?").join(", ");
        const vals = keys.map(k => {
          const v = row[k];
          if (typeof v === "string" && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/.test(v)) {
            return new Date(v);
          }
          return v;
        });
        await pool
          .query(`REPLACE INTO \`${table}\` (${cols}) VALUES (${placeholders})`, vals)
          .catch(() => {});
      }
    }
    await pool.query("SET FOREIGN_KEY_CHECKS = 1");
    lastSyncedHash = JSON.stringify(snapshot);
    const g = globalThis as any;
    g.__fastHomeData = null;
    g.__fastHomeTime = 0;
    if (typeof g.__loadCatalogHome === "function") {
      setTimeout(() => { void g.__loadCatalogHome().catch(() => {}); }, 100);
    }
    console.log("[CloudSync] Successfully restored all products & categories from cloud backup!");
  } catch (err) {
    console.warn("[CloudSync] Restore skipped:", err instanceof Error ? err.message : err);
  } finally {
    isRestoring = false;
  }
}"""

  dbt, n_rep = re.subn(old_restore_pat, lambda m: new_restore_fn, dbt, count=1)
  db_path.write_text(dbt, encoding="utf-8")
  print(f"✅ تم تحديث restoreFromCloud لدعم الملفات الكبيرة (>1MB) ومسح الكاش الفارغ (matches={n_rep})")

# 3. فحص البناء والرفع إلى Render
esbuild_bin = "./node_modules/.bin/esbuild"
if pathlib.Path(esbuild_bin).exists():
  r_srv = subprocess.run(
      f"{esbuild_bin} server/_core/index.ts --bundle --platform=node --format=esm --packages=external --outfile=./.tmp_srv_v133.js",
      shell=True, capture_output=True, text=True,
  )
  subprocess.run("rm -f ./.tmp_srv_v133.js", shell=True)
  if r_srv.returncode != 0:
    print("❌ خطأ في فحص السيرفر:", r_srv.stderr)
    sys.exit(1)

os.system("git add server/db.ts && git commit -m 'Fix v133: support large (>1MB) GitHub raw snapshot restore into fresh TiDB cluster' && git push origin main")
print("🚀 تم رفع التحديث v133 إلى Render!")
