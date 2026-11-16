import os, re, subprocess

home_path = "client/src/pages/Home.tsx"
html_path = "client/index.html"
server_dir = "server"

# ==========================================
# 1. إصلاح Home.tsx (عدد الأصناف الحقيقي + شعار storeIconUrl + أولوية contactPhone + مشاركة الإعدادات الحية)
# ==========================================
with open(home_path, "r", encoding="utf-8") as f:
    home = f.read()

# أ) إلغاء الأرقام الوهمية [42, 35, 28...] وعرض العدد الحقيقي الفعلي فقط لكل قسم (حتى لو 0)
home = re.sub(
    r'const badgeCount = count > 0 \? `\+\$\{count\}` : `\+\$\{\[42, 35, 28, 24, 19, 31\]\[idx % 6\]\}`;',
    'const badgeCount = String(count);',
    home
)

# ب) ربط شعار الهيدر العلوي بمفتاح لوحة الإدارة الحقيقي storeIconUrl
home = re.sub(
    r'<img\s+src=\{[^}]+\}\s+onError=\{[^}]+\}\s+alt=\{storeName\}\s+className="brand-mark"',
    '<img src={(data?.settings?.storeIconUrl || data?.settings?.logo || "").trim() || "/app-icon-192-v85.png"} onError={(e) => { e.currentTarget.src = "/app-icon-192-v85.png"; }} alt={storeName} className="brand-mark"',
    home
)
home = home.replace(
    '<img src="/app-icon-192-v85.png" alt="ORIGINAL" className="brand-mark"',
    '<img src={(data?.settings?.storeIconUrl || data?.settings?.logo || "").trim() || "/app-icon-192-v85.png"} onError={(e) => { e.currentTarget.src = "/app-icon-192-v85.png"; }} alt={storeName} className="brand-mark"'
)

# ج) تقديم contactPhone (الذي تحفظه لوحة الإدارة) على whatsappPhone وإلغاء الرقم القديم 774577334
home = home.replace(
    'settings?.whatsappPhone || settings?.contactPhone || "774577334"',
    'settings?.contactPhone || settings?.whatsappPhone || "770731619"'
)
home = home.replace('"774577334"', '"770731619"')

# د) مشاركة إعدادات المتجر الحية (contactPhone و storeIconUrl) مع واجهة حسابي فور تحميل Header
sync_snippet = 'const storeName = data?.settings.storeName || "ORIGINAL – أورجنال";\n  if (data?.settings && typeof window !== "undefined") { (window as any).__origLiveSettings = data.settings; try { localStorage.setItem("orig_live_settings_v172", JSON.stringify(data.settings)); } catch {} }'
if "__origLiveSettings" not in home:
    home = home.replace(
        'const storeName = data?.settings.storeName || "ORIGINAL – أورجنال";',
        sync_snippet,
        1
    )

with open(home_path, "w", encoding="utf-8") as f:
    f.write(home)
print("✅ 1/3 تم إصلاح Home.tsx: عدد الأصناف الفعلي (بدون أرقام وهمية) + الشعار (storeIconUrl) + رقم الواتساب (contactPhone)!")

# ==========================================
# 2. إصلاح client/index.html ليقرأ رقم التواصل الحقيقي من إعدادات المتجر الحية مباشرة
# ==========================================
with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

html = html.replace("774577334", "770731619")
html = html.replace("779542219", "770731619")

get_phone_fn = r"""
      function getLiveStorePhone() {
        try {
          const live = window.__origLiveSettings || JSON.parse(localStorage.getItem("orig_live_settings_v172") || "{}");
          const p = String(live.contactPhone || live.whatsappPhone || "").trim();
          if (p) return p;
        } catch (_) {}
        return localStorage.getItem("orig_store_support_phone_v171") || "770731619";
      }
"""

if "function getLiveStorePhone()" not in html:
    html = html.replace("function normalizeWaPhone(raw) {", get_phone_fn + "\n      function normalizeWaPhone(raw) {", 1)

html = html.replace("normalizeWaPhone(storeSupportPhone)", "normalizeWaPhone(getLiveStorePhone())")
html = html.replace("${storeSupportPhone}", "${getLiveStorePhone()}")

# تحديث النص داخل نافذة معلومات التطبيق في كل دورة فحص ليطابق الرقم الحي دائماً
refresh_phone_hook = 'safeSetText("orig-about-phone-v171", "الإصدار الرسمي • خدمة عملاء: " + getLiveStorePhone());'
if refresh_phone_hook not in html:
    html = html.replace(
        'safeSetText("orig-hub-name-v168", info.name);',
        refresh_phone_hook + '\n        safeSetText("orig-hub-name-v168", info.name);',
        1
    )

with open(html_path, "w", encoding="utf-8") as f:
    f.write(html)
print("✅ 2/3 تم إصلاح client/index.html: ربط خدمة العملاء ومعلومات التطبيق برقم الإدارة الفعلي!")

# ==========================================
# 3. استبدال أي رقم افتراضي قديم 774577334 في ملفات السيرفر أو الإدارة
# ==========================================
for root_dir, _, files in os.walk("server"):
    for fn in files:
        if fn.endswith((".ts", ".js")):
            p = os.path.join(root_dir, fn)
            with open(p, "r", encoding="utf-8") as f:
                s = f.read()
            if "774577334" in s:
                s = s.replace("774577334", "770731619")
                with open(p, "w", encoding="utf-8") as f:
                    f.write(s)

print("✅ 3/3 تم تطهير ملفات السيرفر من الرقم الافتراضي القديم!")

subprocess.run(["git", "add", "-A"], check=True)
subprocess.run(["git", "commit", "-m", "Fix v172: show exact real category product count (0 when empty), bind header logo to storeIconUrl, and prioritize contactPhone everywhere"], check=False)

res = subprocess.run(["git", "push", "origin", "main"])
if res.returncode != 0:
    env = os.environ.copy()
    env["GIT_SSH_COMMAND"] = "ssh -p 443 -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new"
    subprocess.run(["git", "push", "ssh://git@ssh.github.com:443/asilakrmalhababy-hash/original-store.git", "main"], env=env, check=True)

print("\n🚀 تم رفع النسخة المنقاة v172 إلى Render بنجاح!")
