import os, sys, pathlib

print("=" * 72)
print("👑 تطبيق تصميم صفحة حسابي الكامل بألوان المتجر الرسمية وربط كل الأزرار (v158)")
print("=" * 72)

html_path = pathlib.Path("client/index.html")
if not html_path.exists():
    print("❌ لم يتم العثور على client/index.html")
    sys.exit(1)

html = html_path.read_text(encoding="utf-8")

# إزالة أي نسخة سابقة لـ V157 أو V158
for s_m, e_m in [
    ("<!-- ORIGINAL_ACCOUNT_POLISH_V157_START -->", "<!-- ORIGINAL_ACCOUNT_POLISH_V157_END -->"),
    ("<!-- ORIGINAL_ACCOUNT_V158_START -->", "<!-- ORIGINAL_ACCOUNT_V158_END -->"),
]:
    while s_m in html and e_m in html:
        html = html[:html.index(s_m)] + html[html.index(e_m) + len(e_m):]

v158_block = r"""<!-- ORIGINAL_ACCOUNT_V158_START -->
<style>
  /* إبقاء الهيدر العلوي والسفلي بألوان المتجر الرسمية الهادئة */
  header .header-actions > a,
  header .header-actions > button,
  header .header-actions #orig-header-bell-v141 {
    background: #ffffff !important;
    color: #13462f !important;
    border: 1px solid rgba(216, 180, 84, 0.55) !important;
  }
  header .header-actions a[href="/cart"],
  header .header-actions a[href*="cart"] {
    background: #13462f !important;
    color: #ffffff !important;
    border: 1px solid #d8b454 !important;
  }

  /* حاوية التصميم الجديد لصفحة حسابي */
  #orig-acc-v158-root {
    direction: rtl;
    font-family: 'Tajawal', 'Cairo', sans-serif;
    padding: 4px 0 24px 0;
  }

  /* 1. بطاقة الترحيب العلوية بألوان أورجنال الرسمية (الزمردي العميق #13462f إلى #0b2b1d مع إطار ذهبي ناعم) */
  .orig-acc-hero-v158 {
    background: linear-gradient(135deg, #13462f 0%, #0b2b1d 100%);
    border: 1.5px solid #d8b454;
    border-radius: 22px;
    padding: 18px 16px;
    color: #ffffff;
    box-shadow: 0 12px 28px rgba(19, 70, 47, 0.18);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
    position: relative;
    overflow: hidden;
    margin-bottom: 14px;
  }
  .orig-acc-hero-v158::after {
    content: "";
    position: absolute;
    left: -20px;
    bottom: -20px;
    width: 130px;
    height: 130px;
    background: radial-gradient(circle, rgba(216, 180, 84, 0.14) 0%, transparent 70%);
    pointer-events: none;
  }
  .orig-acc-avatar-ring-v158 {
    width: 64px;
    height: 64px;
    min-width: 64px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.08);
    border: 2px solid #d8b454;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 0 16px rgba(216, 180, 84, 0.25);
  }
  .orig-acc-hero-info-v158 {
    flex: 1;
    text-align: right;
  }
  .orig-acc-hero-greet-v158 {
    font-size: 13px;
    color: #e7c972;
    font-weight: 700;
    margin-bottom: 2px;
  }
  .orig-acc-hero-name-v158 {
    font-size: 20px;
    font-weight: 800;
    color: #ffffff;
    margin: 0 0 6px 0;
    line-height: 1.2;
  }
  .orig-acc-hero-phone-v158 {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 13.5px;
    font-weight: 700;
    color: #e5e7eb;
    direction: ltr;
  }

  /* 2. صف المربعات الأربعة السريعة (إشعاراتي، طلباتي، المفضلة، عناويني) */
  .orig-acc-grid4-v158 {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px;
    margin-bottom: 16px;
  }
  .orig-acc-tile-v158 {
    background: #ffffff;
    border: 1px solid rgba(216, 180, 84, 0.45);
    border-radius: 16px;
    padding: 12px 4px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 7px;
    box-shadow: 0 4px 12px rgba(19, 70, 47, 0.05);
    cursor: pointer;
    transition: transform 0.15s ease, border-color 0.15s ease;
  }
  .orig-acc-tile-v158:active {
    transform: scale(0.95);
    border-color: #13462f;
  }
  .orig-acc-tile-ico-v158 {
    width: 36px;
    height: 36px;
    border-radius: 11px;
    background: #f8f7f2;
    border: 1px solid rgba(216, 180, 84, 0.4);
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .orig-acc-tile-txt-v158 {
    font-size: 11.5px;
    font-weight: 800;
    color: #13462f;
    text-align: center;
    white-space: nowrap;
  }

  /* 3. قائمة الصفوف الأنيقة */
  .orig-acc-list-v158 {
    display: flex;
    flex-direction: column;
    gap: 9px;
    margin-bottom: 16px;
  }
  .orig-acc-row-v158 {
    width: 100%;
    background: #ffffff;
    border: 1px solid rgba(19, 70, 47, 0.08);
    border-radius: 16px;
    padding: 11px 14px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    box-shadow: 0 3px 10px rgba(19, 70, 47, 0.04);
    cursor: pointer;
    text-align: right;
    box-sizing: border-box;
    transition: transform 0.14s ease, border-color 0.14s ease;
  }
  .orig-acc-row-v158:active {
    transform: scale(0.985);
    border-color: #d8b454;
  }
  .orig-acc-row-right-v158 {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .orig-acc-row-ico-v158 {
    width: 38px;
    height: 38px;
    border-radius: 12px;
    background: #f8f7f2;
    border: 1px solid rgba(216, 180, 84, 0.45);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .orig-acc-row-title-v158 {
    font-size: 14px;
    font-weight: 800;
    color: #13462f;
  }
  .orig-acc-row-sub-v158 {
    font-size: 12px;
    font-weight: 600;
    color: #6b7280;
    margin-top: 2px;
    direction: ltr;
    text-align: right;
  }

  /* 4. زر تسجيل الخروج الأنيق */
  .orig-acc-logout-v158 {
    width: 100%;
    height: 46px;
    border-radius: 15px;
    border: 1.5px solid #13462f;
    background: #ffffff;
    color: #13462f;
    font-family: inherit;
    font-size: 14.5px;
    font-weight: 800;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    cursor: pointer;
    box-shadow: 0 4px 12px rgba(19, 70, 47, 0.06);
  }
  .orig-acc-logout-v158:active {
    background: #f8f7f2;
  }

  /* إخفاء البطاقة الافتراضية المكررة عند تفعيل التصميم الجديد (مع بقاء أزرارها قابلة للاستدعاء) */
  .original-account-page.orig-v158-active > .original-account-card {
    display: none !important;
  }
</style>

<script>
(function() {
  var XML_NS = ["http", "://www.w3.org/2000/svg"].join("");

  function svgIcon(pathHtml) {
    return '<svg xmlns="' + XML_NS + '" width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="#13462f" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' + pathHtml + '</svg>';
  }

  function readAccountInfoV158(accPage) {
    var name = "عميل أورجنال";
    var phone = "";
    try {
      var gridItems = accPage.querySelectorAll(".original-account-info-grid > div, .original-account-card h2, .original-account-card h3, .original-account-card p, .original-account-card span");
      for (var i = 0; i < gridItems.length; i++) {
        var t = (gridItems[i].textContent || "").trim();
        if (!t || t.length > 50) continue;
        if (/^7[0-9]{8}$/.test(t.replace(/\s+/g, ""))) {
          phone = t.replace(/\s+/g, "");
        } else if (t !== "الاسم" && t !== "رقم الجوال" && t !== "رقم الهاتف" && t !== "تعديل" && t !== "حسابي" && t !== "تسجيل الخروج" && t.indexOf("مزود") === -1 && name === "عميل أورجنال") {
          if (t.length >= 2 && !/^\d+$/.test(t)) name = t;
        }
      }
      if (!phone) {
        var m = (accPage.textContent || "").match(/7\d{8}/);
        if (m) phone = m[0];
      }
    } catch (_e) {}
    return { name: name, phone: phone || "غير مسجل" };
  }

  function openOriginalEditModeV158(accPage) {
    accPage.classList.remove("orig-v158-active");
    var editBtn = accPage.querySelector(".original-account-edit-btn, button[aria-label*='تعديل'], button");
    if (editBtn && (editBtn.textContent || "").indexOf("تعديل") !== -1) {
      editBtn.click();
    }
    var card = accPage.querySelector(".original-account-card");
    if (card) card.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function buildAccountScreenV158() {
    if (window.location.pathname.indexOf("/admin") === 0) return;
    var accPage = document.querySelector(".original-account-page");
    if (!accPage) return;
    if (document.getElementById("orig-acc-v158-root")) return;

    // إذا كان المستخدم فاتح نموذج التعديل أو تسجيل الدخول، لا نغطي الشاشة
    if (accPage.querySelector("form input[type='text'], form input[type='tel']")) return;

    var info = readAccountInfoV158(accPage);
    accPage.classList.add("orig-v158-active");

    var root = document.createElement("div");
    root.id = "orig-acc-v158-root";

    var bellPath = '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path>';
    var boxPath = '<path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"></path><path d="m3.3 7 8.7 5 8.7-5"></path><path d="M12 22V12"></path>';
    var heartPath = '<path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"></path>';
    var pinPath = '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"></path><circle cx="12" cy="10" r="3"></circle>';
    var userPath = '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle>';
    var gearPath = '<circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1Z"></path>';
    var headsetPath = '<path d="M3 18v-6a9 9 0 0 1 18 0v6"></path><path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z"></path>';
    var infoPath = '<circle cx="12" cy="12" r="10"></circle><path d="M12 16v-4"></path><path d="M12 8h.01"></path>';
    var chevLeft = '<svg xmlns="' + XML_NS + '" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>';

    root.innerHTML =
      '<div class="orig-acc-hero-v158">' +
        '<div class="orig-acc-avatar-ring-v158">' +
          '<svg xmlns="' + XML_NS + '" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#e7c972" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' + userPath + '</svg>' +
        '</div>' +
        '<div class="orig-acc-hero-info-v158">' +
          '<div class="orig-acc-hero-greet-v158">أهلاً بك في متجر أورجنال</div>' +
          '<div class="orig-acc-hero-name-v158">' + info.name + '</div>' +
          '<div class="orig-acc-hero-phone-v158">📞 ' + info.phone + '</div>' +
        '</div>' +
      '</div>' +

      '<div class="orig-acc-grid4-v158">' +
        '<button type="button" class="orig-acc-tile-v158" id="orig-tile-notif-v158"><div class="orig-acc-tile-ico-v158">' + svgIcon(bellPath) + '</div><span class="orig-acc-tile-txt-v158">إشعاراتي</span></button>' +
        '<button type="button" class="orig-acc-tile-v158" id="orig-tile-orders-v158"><div class="orig-acc-tile-ico-v158">' + svgIcon(boxPath) + '</div><span class="orig-acc-tile-txt-v158">طلباتي</span></button>' +
        '<button type="button" class="orig-acc-tile-v158" id="orig-tile-favs-v158"><div class="orig-acc-tile-ico-v158">' + svgIcon(heartPath) + '</div><span class="orig-acc-tile-txt-v158">المفضلة</span></button>' +
        '<button type="button" class="orig-acc-tile-v158" id="orig-tile-addr-v158"><div class="orig-acc-tile-ico-v158">' + svgIcon(pinPath) + '</div><span class="orig-acc-tile-txt-v158">عناويني</span></button>' +
      '</div>' +

      '<div class="orig-acc-list-v158">' +
        '<button type="button" class="orig-acc-row-v158" id="orig-row-notif-v158"><div class="orig-acc-row-right-v158"><div class="orig-acc-row-ico-v158">' + svgIcon(bellPath) + '</div><div class="orig-acc-row-title-v158">إشعارات الطلبات والعروض</div></div>' + chevLeft + '</button>' +
        '<button type="button" class="orig-acc-row-v158" id="orig-row-profile-v158"><div class="orig-acc-row-right-v158"><div class="orig-acc-row-ico-v158">' + svgIcon(userPath) + '</div><div><div class="orig-acc-row-title-v158">' + info.name + '</div><div class="orig-acc-row-sub-v158">رقم الجوال: ' + info.phone + '</div></div></div>' + chevLeft + '</button>' +
        '<button type="button" class="orig-acc-row-v158" id="orig-row-settings-v158"><div class="orig-acc-row-right-v158"><div class="orig-acc-row-ico-v158">' + svgIcon(gearPath) + '</div><div class="orig-acc-row-title-v158">إعدادات الحساب</div></div>' + chevLeft + '</button>' +
        '<button type="button" class="orig-acc-row-v158" id="orig-row-support-v158"><div class="orig-acc-row-right-v158"><div class="orig-acc-row-ico-v158">' + svgIcon(headsetPath) + '</div><div class="orig-acc-row-title-v158">التواصل مع خدمة العملاء</div></div>' + chevLeft + '</button>' +
        '<button type="button" class="orig-acc-row-v158" id="orig-row-about-v158"><div class="orig-acc-row-right-v158"><div class="orig-acc-row-ico-v158">' + svgIcon(infoPath) + '</div><div class="orig-acc-row-title-v158">معلومات التطبيق</div></div>' + chevLeft + '</button>' +
      '</div>' +

      '<button type="button" class="orig-acc-logout-v158" id="orig-acc-logout-v158">تسجيل الخروج 🚪</button>';

    accPage.insertBefore(root, accPage.firstChild);

    // ربط جميع الأزرار بوظائفها الحقيقية
    var openNotif = function() {
      var topBell = document.getElementById("orig-header-bell-v141");
      if (topBell) topBell.click();
    };
    document.getElementById("orig-tile-notif-v158").onclick = openNotif;
    document.getElementById("orig-row-notif-v158").onclick = openNotif;

    document.getElementById("orig-tile-orders-v158").onclick = function() {
      var o = document.querySelector("header a[href*='orders']");
      if (o) o.click(); else window.location.href = "/orders";
    };
    document.getElementById("orig-tile-favs-v158").onclick = function() {
      var f = document.querySelector("header a[href*='favorites']");
      if (f) f.click(); else window.location.href = "/favorites";
    };
    document.getElementById("orig-tile-addr-v158").onclick = function() { openOriginalEditModeV158(accPage); };
    document.getElementById("orig-row-profile-v158").onclick = function() { openOriginalEditModeV158(accPage); };
    document.getElementById("orig-row-settings-v158").onclick = function() { openOriginalEditModeV158(accPage); };

    document.getElementById("orig-row-support-v158").onclick = function() {
      var wa = document.querySelector("a[href*='wa.me']");
      if (wa && wa.getAttribute("href")) {
        window.open(wa.getAttribute("href"), "_blank");
      } else {
        window.open("https://wa.me/967779542219", "_blank");
      }
    };

    document.getElementById("orig-row-about-v158").onclick = function() {
      alert("🌿 متجر أورجنال (ORIGINAL)\nبقالة ذكية متكاملة في صنعاء للتوصيل السريع لباب بيتك.\nالإصدار الحالي: v158");
    };

    document.getElementById("orig-acc-logout-v158").onclick = function() {
      var btns = accPage.querySelectorAll("button");
      for (var i = 0; i < btns.length; i++) {
        if (btns[i].id === "orig-acc-logout-v158") continue;
        if ((btns[i].textContent || "").indexOf("خروج") !== -1) {
          btns[i].click();
          return;
        }
      }
      localStorage.removeItem("orig_cust_phone");
      window.location.reload();
    };
  }

  setInterval(buildAccountScreenV158, 400);
})();
</script>
<!-- ORIGINAL_ACCOUNT_V158_END -->"""

if "</body>" in html:
    html = html.replace("</body>", v158_block + "\n</body>", 1)
else:
    html = html + "\n" + v158_block

html_path.write_text(html, encoding="utf-8")
print("✅ تم تركيب تصميم صفحة حسابي الكامل بألوان المتجر الرسمية في client/index.html!")

os.system("git add client/index.html && git commit -m 'Feat v158: implement clean Account page matching reference layout with official store colors & wired actions' && git push origin main")
print("🚀 تم رفع التحديث v158 إلى Render بنجاح!")
