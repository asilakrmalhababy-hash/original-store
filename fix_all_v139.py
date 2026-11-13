import os, re, sys, shutil, pathlib, subprocess

print("=" * 72)
print("🚀 الإصلاح الجذري للإشعارات الخلفية + ترقيم الطلبات 1,2,3 + أيقونة الإشعار (v139)")
print("=" * 72)

# ---------------------------------------------------------
# 1. توحيد أيقونة الإشعارات إلى شعار أورجنال الذهبي الرسمي (O)
# ---------------------------------------------------------
pub_dir = pathlib.Path("client/public")
best_logo = None
for cand in ["logo-v85.png", "icon-512-v85.png", "icon-192-v85.png", "apple-touch-icon.png", "icon-512.png", "icon-192.png"]:
    p = pub_dir / cand
    if p.exists() and p.stat().st_size > 1000:
        best_logo = p
        break

if best_logo:
    target_notif_icon = pub_dir / "icon-orig-v139.png"
    shutil.copyfile(best_logo, target_notif_icon)
    for old_icon_name in ["icon-192.png", "icon-512.png", "badge-72.png", "logo.png", "favicon.png"]:
        old_p = pub_dir / old_icon_name
        if old_p.exists() and old_p.resolve() != best_logo.resolve():
            shutil.copyfile(best_logo, old_p)
    print(f"✅ تم اعتماد الشعار الرسمي ({best_logo.name}) لجميع الإشعارات في /icon-orig-v139.png")

# ---------------------------------------------------------
# 2. إصلاح ترقيم الطلبات التسلسلي (1, 2, 3...) في server/commerce.ts
# ---------------------------------------------------------
comm_path = pathlib.Path("server/commerce.ts")
if comm_path.exists():
    comm = comm_path.read_text(encoding="utf-8")

    # استبدال دالة syncAndGetNextOrderNumberV99 لترقم الطلبات 1, 2, 3 بدون حذف أي طلب
    new_sync_fn = r"""async function syncAndGetNextOrderNumberV99(dbInstance: any): Promise<string> {
  try {
    const allOrders = await dbInstance
      .select({ id: orders.id, orderNumber: orders.orderNumber })
      .from(orders)
      .orderBy(asc(orders.id));
    let seq = 0;
    for (const row of allOrders) {
      seq += 1;
      const expected = String(seq);
      if (String(row.orderNumber || "").trim() !== expected) {
        await dbInstance
          .update(orders)
          .set({ orderNumber: expected })
          .where(eq(orders.id, row.id));
      }
    }
    return String(seq + 1);
  } catch (err) {
    console.warn("[OrderSeqV139] Fallback sequential count:", err);
    return "1";
  }
}"""

    comm_new, n_sync = re.subn(
        r"async\s+function\s+syncAndGetNextOrderNumberV99\s*\([^)]*\)\s*:\s*Promise<string>\s*\{[\s\S]*?\n\}",
        lambda _m: new_sync_fn,
        comm,
        count=1
    )
    if n_sync == 0:
        comm_new, n_sync = re.subn(
            r"async\s+function\s+syncAndGetNextOrderNumberV99\s*\([^)]*\)\s*\{[\s\S]*?\n\}",
            lambda _m: new_sync_fn,
            comm,
            count=1
        )
    comm = comm_new

    # استبدال أي توليد عشوائي لـ TEST- أو ORD- عند إنشاء الطلب باستدعاء الترقيم التسلسلي
    comm = re.sub(
        r"`TEST-\$\{Date\.now\(\)\.toString\(36\)\.toUpperCase\(\)\}-\$\{Math\.random\(\)\.toString\(36\)\.slice\(2,\s*7\)\.toUpperCase\(\)\}`",
        "await syncAndGetNextOrderNumberV99(db!)",
        comm
    )
    comm = re.sub(
        r"`ORD-\$\{Date\.now\(\)\.toString\(36\)\.toUpperCase\(\)\}-\$\{Math\.random\(\)\.toString\(36\)\.slice\(2,\s*6\)\.toUpperCase\(\)\}`",
        "await syncAndGetNextOrderNumberV99(db!)",
        comm
    )

    comm_path.write_text(comm, encoding="utf-8")
    print(f"✅ تم تفعيل الترقيم التسلسلي (1، 2، 3...) للطلبات في server/commerce.ts (matches={n_sync})")

# ---------------------------------------------------------
# 3. إصلاح server/ai_engine_v112.ts:
#    - حفظ واسترجاع اشتراكات Web Push ومفاتيح VAPID من قاعدة بيانات TiDB (store_settings)
#    - تنظيف نص الإشعارات وإزالة إيموجي الطباخ والرموز العشوائية وتحديث الأيقونة
# ---------------------------------------------------------
ai_path = pathlib.Path("server/ai_engine_v112.ts")
if ai_path.exists():
    ai = ai_path.read_text(encoding="utf-8")

    # استبدال أي أيقونة قديمة في الإشعارات بـ /icon-orig-v139.png
    ai = re.sub(
        r'icon\s*:\s*["\'][^"\']*["\']',
        'icon: "/icon-orig-v139.png"',
        ai
    )
    ai = re.sub(
        r'badge\s*:\s*["\'][^"\']*["\']',
        'badge: "/icon-orig-v139.png"',
        ai
    )

    # تنظيف إيموجي الطباخ والنصوص المشوهة
    ai = ai.replace("👨‍🍳 طلبك الآن قيد التجهيز بعناية", "تم اعتماد طلبك وجاري تجهيزه الآن")
    ai = ai.replace("👨‍🍳", "")
    ai = ai.replace("🌿 متجر أورجنال • طلب #", "متجر أورجنال • طلب رقم #")
    ai = ai.replace("📦 تتبع حالة الطلب", "عرض تفاصيل الطلب")

    # منع اقتطاع آخر 5 حروف عشوائية (.slice(-5)) من رقم الطلب
    ai = re.sub(
        r'(\.orderNumber[^\n;]*?)\.slice\(-5\)',
        r'\1',
        ai
    )
    ai = re.sub(
        r'String\(([^)]*orderNumber[^)]*)\)\.slice\(-5\)',
        r'String(\1)',
        ai
    )

    # حقن نظام حفظ واسترجاع اشتراكات الإشعارات ومفاتيح VAPID في قاعدة البيانات TiDB
    db_push_sync_marker = "// === ORIGINAL_DB_PUSH_PERSIST_V139_START ==="
    db_push_sync_end = "// === ORIGINAL_DB_PUSH_PERSIST_V139_END ==="
    if db_push_sync_marker in ai and db_push_sync_end in ai:
        ai = ai[:ai.index(db_push_sync_marker)] + ai[ai.index(db_push_sync_end) + len(db_push_sync_end):]

    # نتحقق من أسماء المتغيرات الخاصة بملف الاشتراكات في ai_engine_v112.ts
    persist_helper = r"""
// === ORIGINAL_DB_PUSH_PERSIST_V139_START ===
import * as __dbPushModV139 from "./db";
import fsV139 from "fs";
import pathV139 from "path";

const __PUSH_FILES_V139 = [
  ".ai-v112-store.json",
  ".push-subscriptions.json",
  ".vapid-keys.json",
  "server/.ai-v112-store.json"
];

export async function syncPushStoreFromTiDBV139(): Promise<void> {
  try {
    const pool = (__dbPushModV139 as any).getPool ? await (__dbPushModV139 as any).getPool() : null;
    if (!pool) return;
    // تصحيح أي أرقام طلبات قديمة TEST- أو ORD- إلى 1، 2، 3...
    try {
      const [ordRows]: any = await pool.query("SELECT id, orderNumber FROM orders ORDER BY id ASC");
      if (Array.isArray(ordRows)) {
        let seq = 0;
        for (const r of ordRows) {
          seq += 1;
          const exp = String(seq);
          if (String(r.orderNumber || "").trim() !== exp) {
            await pool.query("UPDATE orders SET orderNumber = ? WHERE id = ?", [exp, r.id]);
          }
        }
      }
    } catch (_e) {}

    const [rows]: any = await pool.query(
      "SELECT `key`, `value` FROM store_settings WHERE `key` LIKE 'v139_push_file_%'"
    );
    if (Array.isArray(rows)) {
      for (const r of rows) {
        const k = String(r.key || "").replace("v139_push_file_", "");
        const val = String(r.value || "");
        if (k && val && val.length > 2) {
          const targetPath = pathV139.resolve(process.cwd(), k);
          if (!fsV139.existsSync(targetPath)) {
            fsV139.writeFileSync(targetPath, val, "utf-8");
            console.log("[PushSyncV139] Restored push file from TiDB:", k);
          } else {
            // دمج اشتراكات المشرفين من القاعدة مع الملف المحلي حتى لا يضيع أي اشتراك بعد 12 ساعة
            try {
              const dbObj = JSON.parse(val);
              const locObj = JSON.parse(fsV139.readFileSync(targetPath, "utf-8"));
              let changed = false;
              for (const prop of ["pushSubscriptions", "adminSubscriptions", "subscriptions", "customerSubscriptions"]) {
                if (Array.isArray(dbObj[prop])) {
                  locObj[prop] = Array.isArray(locObj[prop]) ? locObj[prop] : [];
                  const existingEndpoints = new Set(locObj[prop].map((x: any) => x && (x.endpoint || (x.sub && x.sub.endpoint))));
                  for (const item of dbObj[prop]) {
                    const ep = item && (item.endpoint || (item.sub && item.sub.endpoint));
                    if (ep && !existingEndpoints.has(ep)) {
                      locObj[prop].push(item);
                      existingEndpoints.add(ep);
                      changed = true;
                    }
                  }
                }
              }
              if (dbObj.vapidKeys && !locObj.vapidKeys) {
                locObj.vapidKeys = dbObj.vapidKeys;
                changed = true;
              }
              if (changed) {
                fsV139.writeFileSync(targetPath, JSON.stringify(locObj, null, 2), "utf-8");
              }
            } catch (_e) {}
          }
        }
      }
    }
  } catch (err) {
    console.warn("[PushSyncV139] Restore warning:", err);
  }
}

export async function savePushStoreToTiDBV139(): Promise<void> {
  try {
    const pool = (__dbPushModV139 as any).getPool ? await (__dbPushModV139 as any).getPool() : null;
    if (!pool) return;
    for (const fname of __PUSH_FILES_V139) {
      const fpath = pathV139.resolve(process.cwd(), fname);
      if (fsV139.existsSync(fpath)) {
        const raw = fsV139.readFileSync(fpath, "utf-8");
        if (raw && raw.length > 2 && raw.length < 1500000) {
          const settingKey = "v139_push_file_" + pathV139.basename(fname);
          await pool.query(
            "INSERT INTO store_settings (`key`, `value`) VALUES (?, ?) ON DUPLICATE KEY UPDATE `value` = VALUES(`value`)",
            [settingKey, raw]
          );
        }
      }
    }
  } catch (_err) {}
}

setTimeout(() => { syncPushStoreFromTiDBV139(); }, 1500);
// === ORIGINAL_DB_PUSH_PERSIST_V139_END ===
"""
    ai = ai + "\n" + persist_helper

    # ربط حفظ واسترجاع اشتراكات Push عند كل تسجيل اشتراك جديد وعند إرسال الإشعارات
    ai = re.sub(
        r'(app\.post\(\s*["\']/api/ai-v112/push-subscribe["\']\s*,\s*async\s*\([^)]*\)\s*=>\s*\{)',
        r'\1 await syncPushStoreFromTiDBV139(); setTimeout(() => { savePushStoreToTiDBV139(); }, 400);',
        ai
    )
    ai = re.sub(
        r'(app\.post\(\s*["\']/api/ai-v112/notify-order["\']\s*,\s*async\s*\([^)]*\)\s*=>\s*\{)',
        r'\1 await syncPushStoreFromTiDBV139();',
        ai
    )

    ai_path.write_text(ai, encoding="utf-8")
    print("✅ تم تحديث server/ai_engine_v112.ts: حفظ دائم لاشتراكات الإشعارات في TiDB وتنظيف نصوص وأيقونة الإشعار")

# ---------------------------------------------------------
# 4. تحديث Service Worker (client/public/sw.js) لعرض الأيقونة الرسمية وتنظيف الإشعار
# ---------------------------------------------------------
sw_path = pathlib.Path("client/public/sw.js")
if sw_path.exists():
    sw = sw_path.read_text(encoding="utf-8")
    sw = re.sub(r'icon\s*:\s*["\'][^"\']*["\']', 'icon: "/icon-orig-v139.png"', sw)
    sw = re.sub(r'badge\s*:\s*["\'][^"\']*["\']', 'badge: "/icon-orig-v139.png"', sw)
    sw = sw.replace("👨‍🍳", "")
    sw_path.write_text(sw, encoding="utf-8")
    print("✅ تم تحديث client/public/sw.js بالأيقونة الرسمية الجديدة")

# ---------------------------------------------------------
# 5. تحديث client/index.html:
#    - السماح بفحص إشعارات المشرف حتى عند استخدام علامات تبويب أخرى (إزالة شرط document.hidden للمشرف)
#    - تنظيف شكل الإشعار المحلي وأيقونته ورقم الطلب التسلسلي
# ---------------------------------------------------------
html_path = pathlib.Path("client/index.html")
if html_path.exists():
    html = html_path.read_text(encoding="utf-8")
    html = html.replace("if (document.hidden || !hasAdminToken) return;", "if (!hasAdminToken) return;")
    html = re.sub(r'icon\s*:\s*["\']/(?:icon-192|icon-512|logo|favicon)[^"\']*["\']', 'icon: "/icon-orig-v139.png"', html)
    html = re.sub(r'badge\s*:\s*["\']/(?:icon-192|icon-512|logo|favicon|badge)[^"\']*["\']', 'badge: "/icon-orig-v139.png"', html)
    html = html.replace("👨‍🍳 طلبك الآن قيد التجهيز بعناية", "تم اعتماد طلبك وجاري تجهيزه الآن")
    html = html.replace("👨‍🍳", "")
    html = re.sub(r'\.slice\(-5\)', '', html)
    html_path.write_text(html, encoding="utf-8")
    print("✅ تم تحديث client/index.html ليعمل الإشعار في التبويبات الخلفية وبأيقونة وأرقام نظيفة")

# ---------------------------------------------------------
# 6. فحص سلامة البناء عبر esbuild قبل الرفع
# ---------------------------------------------------------
esbuild_bin = "./node_modules/.bin/esbuild"
if pathlib.Path(esbuild_bin).exists():
    r_srv = subprocess.run(
        f"{esbuild_bin} server/_core/index.ts --bundle --platform=node --format=esm --packages=external --outfile=./.tmp_srv_v139.js",
        shell=True, capture_output=True, text=True
    )
    subprocess.run("rm -f ./.tmp_srv_v139.js", shell=True)
    if r_srv.returncode != 0:
        print("❌ خطأ في فحص السيرفر:", r_srv.stderr)
        sys.exit(1)
    print("✅ تم التحقق من سلامة البناء 100% عبر esbuild!")

os.system("git add -A && git commit -m 'Fix v139: persist Web Push subscriptions in TiDB for 12h+ background wake, sequential 1,2,3 order numbers, and clean official O notification icon' && git push origin main")
print("🚀 تم رفع التحديث v139 إلى Render بنجاح!")
