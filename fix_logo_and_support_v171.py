import os, re, subprocess

home_path = "client/src/pages/Home.tsx"
html_path = "client/index.html"

# 1. ربط شعار الهيدر العلوي في Home.tsx بـ data?.settings?.logo
with open(home_path, "r", encoding="utf-8") as f:
    home = f.read()

old_logo_img = '<img src="/app-icon-192-v85.png" alt="ORIGINAL" className="brand-mark"'
new_logo_img = '<img src={(data?.settings?.logo || "").trim() || "/app-icon-192-v85.png"} onError={(e) => { e.currentTarget.src = "/app-icon-192-v85.png"; }} alt={storeName} className="brand-mark"'

if old_logo_img in home:
    home = home.replace(old_logo_img, new_logo_img, 1)
    with open(home_path, "w", encoding="utf-8") as f:
        f.write(home)
    print("✅ تم ربط شعار الهيدر العلوي في Home.tsx بإعدادات المتجر (data.settings.logo)!")
else:
    print("ℹ️ شعار الهيدر مرتبط مسبقاً أو بصيغة مختلفة.")

# 2. إزالة رقم شهيزو (779542219) من client/index.html وربط خدمة العملاء برقم إعدادات المتجر
with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

# إضافة دالة قراءة رقم الدعم الحقيقي من /api/trpc/store.getData
support_helper = r"""
      let storeSupportPhone = localStorage.getItem("orig_store_support_phone_v171") || "774577334";
      function normalizeWaPhone(raw) {
        const digits = String(raw || "").replace(/\D+/g, "");
        if (!digits) return "967774577334";
        if (digits.startsWith("967")) return digits;
        if (digits.startsWith("00967")) return digits.slice(2);
        if (digits.length === 9 && digits.startsWith("7")) return "967" + digits;
        return digits;
      }
      fetch("/api/trpc/store.getData")
        .then(r => r.ok ? r.json() : null)
        .then(res => {
          const settings = res?.result?.data?.json?.settings || res?.result?.data?.settings;
          if (!settings) return;
          const rawPhone = String(settings.whatsappPhone || settings.contactPhone || "").trim();
          if (rawPhone) {
            storeSupportPhone = rawPhone;
            try { localStorage.setItem("orig_store_support_phone_v171", rawPhone); } catch (_) {}
            const el = document.getElementById("orig-about-phone-v171");
            if (el) el.textContent = "الإصدار الرسمي • خدمة عملاء: " + rawPhone;
          }
        })
        .catch(() => {});
"""

if "orig_store_support_phone_v171" not in html:
    html = html.replace("let currentSubMode = null;", "let currentSubMode = null;\n" + support_helper, 1)

# استبدال رقم خدمة العملاء في زر التواصل وفي نافذة معلومات التطبيق
html = html.replace(
    'window.open("https://wa.me/967779542219", "_blank")',
    'window.open("https://wa.me/" + normalizeWaPhone(storeSupportPhone), "_blank")'
)
html = html.replace(
    '<strong style="color:#13462f;display:inline-block;margin-top:6px;">الإصدار الرسمي • خدمة عملاء: 779542219</strong>',
    '<strong id="orig-about-phone-v171" style="color:#13462f;display:inline-block;margin-top:6px;">الإصدار الرسمي • خدمة عملاء: ' + "' + storeSupportPhone + '" + '</strong>'
)

# التأكد أن النص داخل template literal مكتوب بشكل صحيح
html = html.replace("' + storeSupportPhone + '", "${storeSupportPhone}")

with open(html_path, "w", encoding="utf-8") as f:
    f.write(html)

print("✅ تم ربط زر خدمة العملاء ومعلومات التطبيق برقم إعدادات المتجر الحقيقي!")

subprocess.run(["git", "add", "client/src/pages/Home.tsx", "client/index.html"], check=True)
subprocess.run(["git", "commit", "-m", "Fix v171: bind header logo to data.settings.logo in Home.tsx and use dynamic store whatsappPhone/contactPhone for customer support"], check=False)

res = subprocess.run(["git", "push", "origin", "main"])
if res.returncode != 0:
    env = os.environ.copy()
    env["GIT_SSH_COMMAND"] = "ssh -p 443 -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new"
    subprocess.run(["git", "push", "ssh://git@ssh.github.com:443/asilakrmalhababy-hash/original-store.git", "main"], env=env, check=True)

print("🚀 تم رفع التحديث v171 إلى Render بنجاح!")
