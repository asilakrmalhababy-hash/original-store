import os, re, subprocess

css_path = "client/src/index.css"
html_path = "client/index.html"

# 1. ضبط ارتفاع هيدر النافذة الفرعية في CSS ومنع تمدده
with open(css_path, "r", encoding="utf-8") as f:
    css = f.read()

if "#orig-subview-sheet-head-v168 {" in css and "height: auto !important;" not in css:
    css = css.replace(
        "#orig-subview-sheet-head-v168 {",
        "#orig-subview-sheet-head-v168 {\n  flex: 0 0 auto !important;\n  height: auto !important;\n  min-height: 0 !important;"
    )

# إضافة تنسيق نافذة الإشعارات والعروض الأنيقة
notif_css = r"""
/* === NOTIF DRAWER V170 START === */
#orig-notif-drawer-v170 {
  position: fixed;
  inset: 0;
  background: rgba(8, 24, 16, 0.6);
  backdrop-filter: blur(5px);
  -webkit-backdrop-filter: blur(5px);
  z-index: 99998;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.24s ease;
  direction: rtl;
  font-family: 'Cairo', 'Tajawal', sans-serif;
}
#orig-notif-drawer-v170.open {
  opacity: 1;
  pointer-events: auto;
}
.orig-notif-sheet-v170 {
  width: 100%;
  max-width: 540px;
  max-height: 82vh;
  background: #f8f7f2;
  border-top: 2px solid #d8b454;
  border-radius: 26px 26px 0 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transform: translateY(100%);
  transition: transform 0.3s cubic-bezier(0.22, 1, 0.36, 1);
  box-shadow: 0 -10px 35px rgba(0, 0, 0, 0.25);
}
#orig-notif-drawer-v170.open .orig-notif-sheet-v170 {
  transform: translateY(0);
}
.orig-notif-head-v170 {
  background: linear-gradient(135deg, #13462f 0%, #0b2b1d 100%);
  padding: 12px 18px 16px 18px;
  color: #ffffff;
  border-bottom: 1.5px solid #d8b454;
}
.orig-notif-pill-v170 {
  width: 42px;
  height: 4px;
  border-radius: 999px;
  background: rgba(216, 180, 84, 0.55);
  margin: 0 auto 10px auto;
}
.orig-notif-head-row-v170 {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.orig-notif-title-v170 {
  font-size: 16.5px;
  font-weight: 800;
  margin: 0;
}
.orig-notif-close-v170 {
  background: rgba(216, 180, 84, 0.18);
  border: 1px solid rgba(216, 180, 84, 0.6);
  color: #e7c972;
  height: 32px;
  padding: 0 12px;
  border-radius: 10px;
  font-size: 12.5px;
  font-weight: 800;
  cursor: pointer;
}
.orig-notif-body-v170 {
  padding: 14px 16px 26px 16px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.orig-notif-card-v170 {
  background: #ffffff;
  border: 1.5px solid rgba(216, 180, 84, 0.4);
  border-radius: 16px;
  padding: 13px 14px;
  box-shadow: 0 4px 12px rgba(19, 70, 47, 0.05);
}
.orig-notif-card-title-v170 {
  font-size: 14.5px;
  font-weight: 800;
  color: #13462f;
  margin: 0 0 4px 0;
}
.orig-notif-card-msg-v170 {
  font-size: 13px;
  color: #4a5c52;
  margin: 0;
  line-height: 1.55;
  font-weight: 600;
}
.orig-promo-copy-btn-v170 {
  margin-top: 8px;
  background: linear-gradient(135deg, #13462f, #0b2b1d);
  color: #e7c972;
  border: 1px solid #d8b454;
  border-radius: 10px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
/* === NOTIF DRAWER V170 END === */
"""
css = re.sub(r'/\* === NOTIF DRAWER V170 START === \*/.*?/\* === NOTIF DRAWER V170 END === \*/\s*', '', css, flags=re.DOTALL)
css = css.rstrip() + "\n" + notif_css
with open(css_path, "w", encoding="utf-8") as f:
    f.write(css)

# 2. تحديث منطق الجرس ووسم نموذج تعديل البيانات في client/index.html
with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

# أ) إصلاح توجيه زر الجرس العلوي ليفتح نافذة الإشعارات والعروض بدل /orders
html = html.replace(
    'bellBtn.addEventListener("click", (e) => {\n            e.preventDefault();\n            window.location.href = "/orders";\n          });',
    'bellBtn.addEventListener("click", (e) => {\n            e.preventDefault();\n            e.stopPropagation();\n            openNotificationsDrawer();\n          });'
)

# ب) إصلاح توجيه أزرار إشعاراتي في صفحة حسابي لتفتح نافذة الإشعارات والعروض بدل /orders
html = html.replace(
    '<button type="button" class="orig-quick-card-v168" data-act="orders">\n                <svg viewBox="0 0 24 24" fill="#13462f"><path d="M12 22c1.1 0 2-.9 2-2h-4a2 2 0 002 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z"/></svg>\n                <span class="orig-quick-label-v168">إشعاراتي</span>',
    '<button type="button" class="orig-quick-card-v168" data-act="notifications">\n                <svg viewBox="0 0 24 24" fill="#13462f"><path d="M12 22c1.1 0 2-.9 2-2h-4a2 2 0 002 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z"/></svg>\n                <span class="orig-quick-label-v168">إشعاراتي</span>'
)
html = html.replace(
    '<div class="orig-menu-item-v168" data-act="orders">\n              <div class="orig-menu-right-v168">\n                <div class="orig-menu-icon-v168">\n                  <svg viewBox="0 0 24 24" fill="#13462f"><path d="M12 22c1.1 0 2-.9 2-2h-4a2 2 0 002 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z"/></svg>',
    '<div class="orig-menu-item-v168" data-act="notifications">\n              <div class="orig-menu-right-v168">\n                <div class="orig-menu-icon-v168">\n                  <svg viewBox="0 0 24 24" fill="#13462f"><path d="M12 22c1.1 0 2-.9 2-2h-4a2 2 0 002 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z"/></svg>'
)

# ج) إصلاح أولوية وسم profile-form (الذي يظهر داخل .original-account-card عند التعديل) حتى لا يتم إخفاؤه
old_tag_logic = """const sec = hitAddresses
            ? "addresses"
            : (ch.classList.contains("original-account-card") && (txt.includes("بيانات مكتملة") || txt.includes("تعديل البيانات") || ch.querySelector(".original-account-avatar")))
            ? "legacy-hero"
            : (txt.includes("تحديث البيانات الشخصية") || (ch.querySelector("input") && (txt.includes("الاسم الكامل") || txt.includes("حفظ البيانات"))))
            ? "profile-form"
            : (txt.includes("الاسم الكامل للمستلم") || txt.includes("رقم الجوال المعتمد"))
            ? "profile-readonly"
            : "legacy-links";"""

new_tag_logic = """const hasProfileInputs = Boolean(ch.querySelector('input:not([type="checkbox"]):not([type="radio"])')) || txt.includes("تحديث البيانات الشخصية") || txt.includes("حفظ البيانات");
          const sec = hitAddresses
            ? "addresses"
            : hasProfileInputs
            ? "profile-form"
            : (ch.classList.contains("original-account-card") && (txt.includes("بيانات مكتملة") || txt.includes("تعديل البيانات") || ch.querySelector(".original-account-avatar")))
            ? "legacy-hero"
            : (txt.includes("الاسم الكامل للمستلم") || txt.includes("رقم الجوال المعتمد"))
            ? "profile-readonly"
            : "legacy-links";"""

if old_tag_logic in html:
    html = html.replace(old_tag_logic, new_tag_logic, 1)

# د) إضافة دالة openNotificationsDrawer وربط action === "notifications"
drawer_fn = r"""
      function openNotificationsDrawer() {
        let drawer = document.getElementById("orig-notif-drawer-v170");
        if (!drawer) {
          drawer = document.createElement("div");
          drawer.id = "orig-notif-drawer-v170";
          drawer.innerHTML = `
            <div class="orig-notif-sheet-v170">
              <div class="orig-notif-head-v170">
                <div class="orig-notif-pill-v170"></div>
                <div class="orig-notif-head-row-v170">
                  <h3 class="orig-notif-title-v170">إشعارات الطلبات والعروض</h3>
                  <button type="button" class="orig-notif-close-v170" id="orig-notif-close-btn-v170">إغلاق</button>
                </div>
              </div>
              <div class="orig-notif-body-v170" id="orig-notif-body-v170">
                <div class="orig-notif-card-v170">
                  <p class="orig-notif-card-msg-v170">جارٍ تحميل أحدث الإشعارات والعروض...</p>
                </div>
              </div>
            </div>
          `;
          document.body.appendChild(drawer);
          drawer.addEventListener("click", (e) => { if (e.target === drawer) drawer.classList.remove("open"); });
          document.getElementById("orig-notif-close-btn-v170").addEventListener("click", () => drawer.classList.remove("open"));
        }
        drawer.classList.add("open");

        const bodyEl = document.getElementById("orig-notif-body-v170");
        Promise.allSettled([
          fetch("/api/v140/customer-feed").then(r => r.ok ? r.json() : null).catch(() => null),
          fetch("/api/trpc/store.getData").then(r => r.ok ? r.json() : null).catch(() => null)
        ]).then(([feedRes, storeRes]) => {
          const cards = [];
          const feed = feedRes.status === "fulfilled" && feedRes.value ? (feedRes.value.items || feedRes.value.notifications || []) : [];
          if (Array.isArray(feed)) {
            feed.forEach(item => {
              cards.push(`
                <div class="orig-notif-card-v170">
                  <h4 class="orig-notif-card-title-v170">🔔 ${item.title || "إشعار من متجر أورجنال"}</h4>
                  <p class="orig-notif-card-msg-v170">${item.body || item.message || ""}</p>
                </div>
              `);
            });
          }
          const storeData = storeRes.status === "fulfilled" && storeRes.value ? (storeRes.value?.result?.data?.json || storeRes.value?.result?.data) : null;
          const offers = storeData?.offers || [];
          if (Array.isArray(offers)) {
            offers.forEach(of => {
              const code = (of.code || "").trim();
              cards.push(`
                <div class="orig-notif-card-v170">
                  <h4 class="orig-notif-card-title-v170">🎁 ${of.title || "عرض خاص"}</h4>
                  <p class="orig-notif-card-msg-v170">${of.description || "استفد من هذا العرض عند تأكيد طلبك."}</p>
                  ${code ? `<button type="button" class="orig-promo-copy-btn-v170" onclick="navigator.clipboard?.writeText('${code}');this.textContent='✓ تم نسخ الكود: ${code}';">نسخ الكود: ${code}</button>` : ""}
                </div>
              `);
            });
          }
          if (!cards.length) {
            cards.push(`
              <div class="orig-notif-card-v170">
                <h4 class="orig-notif-card-title-v170">أهلاً بك في إشعارات أورجنال</h4>
                <p class="orig-notif-card-msg-v170">ستظهر هنا فورياً جميع تحديثات طلباتك وعروض الخصم الحصرية.</p>
              </div>
            `);
          }
          if (bodyEl) bodyEl.innerHTML = cards.join("");
        });
      }
"""

if "function openNotificationsDrawer()" not in html:
    html = html.replace("function upgradeHeaderBell() {", drawer_fn + "\n      function upgradeHeaderBell() {", 1)

html = html.replace(
    'if (act === "orders") window.location.href = "/orders";',
    'if (act === "notifications") openNotificationsDrawer();\n              else if (act === "orders") window.location.href = "/orders";'
)

with open(html_path, "w", encoding="utf-8") as f:
    f.write(html)

print("✅ تم إصلاح نموذج تعديل البيانات + إضافة نافذة الإشعارات والعروض v170!")

subprocess.run(["git", "add", "client/index.html", "client/src/index.css"], check=True)
subprocess.run(["git", "commit", "-m", "Fix v170: show profile edit form inside subview sheet, fix header height, and restore Offers & Notifications drawer for bell/notifications buttons"], check=False)

res = subprocess.run(["git", "push", "origin", "main"])
if res.returncode != 0:
    env = os.environ.copy()
    env["GIT_SSH_COMMAND"] = "ssh -p 443 -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new"
    subprocess.run(["git", "push", "ssh://git@ssh.github.com:443/asilakrmalhababy-hash/original-store.git", "main"], env=env, check=True)

print("🚀 تم رفع الإصلاح v170 إلى Render بنجاح!")
