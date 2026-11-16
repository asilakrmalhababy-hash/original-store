import os, sys, pathlib

print("=" * 72)
print("✨ التحديث v159: إزالة تكرار صفحة حسابي + تأكيد تسجيل الخروج الفعلي + نافذة معلومات التطبيق الأنيقة")
print("=" * 72)

html_path = pathlib.Path("client/index.html")
if not html_path.exists():
    print("❌ لم يتم العثور على client/index.html")
    sys.exit(1)

html = html_path.read_text(encoding="utf-8")

for s_m, e_m in [
    ("<!-- ORIGINAL_ACCOUNT_POLISH_V157_START -->", "<!-- ORIGINAL_ACCOUNT_POLISH_V157_END -->"),
    ("<!-- ORIGINAL_ACCOUNT_V158_START -->", "<!-- ORIGINAL_ACCOUNT_V158_END -->"),
    ("<!-- ORIGINAL_ACCOUNT_V159_START -->", "<!-- ORIGINAL_ACCOUNT_V159_END -->"),
]:
    while s_m in html and e_m in html:
        html = html[:html.index(s_m)] + html[html.index(e_m) + len(e_m):]

v159_block = r"""<!-- ORIGINAL_ACCOUNT_V159_START -->
<style>
  /* توحيد ألوان الهيدر العلوي والسفلي بألوان المتجر الرسمية */
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

  /* إخفاء جميع الأقسام القديمة المكررة داخل صفحة حسابي عند تفعيل الواجهة الجديدة */
  .original-account-page.orig-v159-active > *:not(#orig-acc-v159-root) {
    display: none !important;
  }

  #orig-acc-v159-root {
    direction: rtl;
    font-family: 'Tajawal', 'Cairo', sans-serif;
    padding: 4px 0 24px 0;
  }

  .orig-acc-hero-v159 {
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
  .orig-acc-avatar-ring-v159 {
    width: 62px;
    height: 62px;
    min-width: 62px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.08);
    border: 2px solid #d8b454;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .orig-acc-hero-info-v159 {
    flex: 1;
    text-align: right;
  }
  .orig-acc-hero-greet-v159 {
    font-size: 12.5px;
    color: #e7c972;
    font-weight: 700;
    margin-bottom: 2px;
  }
  .orig-acc-hero-name-v159 {
    font-size: 19px;
    font-weight: 800;
    color: #ffffff;
    margin: 0 0 5px 0;
    line-height: 1.2;
  }
  .orig-acc-hero-phone-v159 {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    font-weight: 700;
    color: #e5e7eb;
    direction: ltr;
  }

  .orig-acc-grid4-v159 {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px;
    margin-bottom: 14px;
  }
  .orig-acc-tile-v159 {
    background: #ffffff;
    border: 1px solid rgba(216, 180, 84, 0.45);
    border-radius: 16px;
    padding: 11px 4px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 6px;
    box-shadow: 0 4px 12px rgba(19, 70, 47, 0.05);
    cursor: pointer;
    transition: transform 0.14s ease;
  }
  .orig-acc-tile-v159:active { transform: scale(0.95); }
  .orig-acc-tile-ico-v159 {
    width: 35px;
    height: 35px;
    border-radius: 11px;
    background: #f8f7f2;
    border: 1px solid rgba(216, 180, 84, 0.42);
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .orig-acc-tile-txt-v159 {
    font-size: 11.5px;
    font-weight: 800;
    color: #13462f;
    white-space: nowrap;
  }

  .orig-acc-list-v159 {
    display: flex;
    flex-direction: column;
    gap: 9px;
    margin-bottom: 16px;
  }
  .orig-acc-row-v159 {
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
    transition: transform 0.14s ease;
  }
  .orig-acc-row-v159:active { transform: scale(0.985); }
  .orig-acc-row-right-v159 {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .orig-acc-row-ico-v159 {
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
  .orig-acc-row-title-v159 {
    font-size: 14px;
    font-weight: 800;
    color: #13462f;
  }
  .orig-acc-row-sub-v159 {
    font-size: 12px;
    font-weight: 600;
    color: #6b7280;
    margin-top: 2px;
    direction: ltr;
    text-align: right;
  }

  .orig-acc-logout-v159 {
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

  /* النوافذ الأنيقة (تأكيد الخروج + معلومات التطبيق) */
  #orig-modal-overlay-v159 {
    position: fixed;
    inset: 0;
    z-index: 2147483646;
    background: rgba(11, 43, 29, 0.55);
    backdrop-filter: blur(5px);
    display: none;
    align-items: center;
    justify-content: center;
    padding: 18px;
    direction: rtl;
    font-family: 'Tajawal', 'Cairo', sans-serif;
  }
  #orig-modal-overlay-v159.open { display: flex; }
  .orig-modal-box-v159 {
    width: 100%;
    max-width: 360px;
    background: #ffffff;
    border: 1.5px solid #d8b454;
    border-radius: 22px;
    padding: 20px 18px;
    box-shadow: 0 18px 42px rgba(0, 0, 0, 0.28);
    text-align: center;
    box-sizing: border-box;
  }
  .orig-modal-title-v159 {
    font-size: 18px;
    font-weight: 900;
    color: #13462f;
    margin: 0 0 8px 0;
  }
  .orig-modal-desc-v159 {
    font-size: 13.5px;
    line-height: 1.6;
    color: #4b5563;
    margin: 0 0 16px 0;
  }
  .orig-modal-actions-v159 {
    display: flex;
    gap: 10px;
  }
  .orig-modal-btn-primary-v159 {
    flex: 1;
    height: 42px;
    border-radius: 13px;
    border: 1px solid #d8b454;
    background: #13462f;
    color: #ffffff;
    font-family: inherit;
    font-size: 13.5px;
    font-weight: 800;
    cursor: pointer;
  }
  .orig-modal-btn-cancel-v159 {
    flex: 1;
    height: 42px;
    border-radius: 13px;
    border: 1px solid rgba(19, 70, 47, 0.2);
    background: #f8f7f2;
    color: #13462f;
    font-family: inherit;
    font-size: 13.5px;
    font-weight: 800;
    cursor: pointer;
  }
</style>

<script>
(function() {
  var XML_NS = ["http", "://www.w3.org/2000/svg"].join("");

  function svgIcon(pathHtml) {
    return '<svg xmlns="' + XML_NS + '" width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="#13462f" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' + pathHtml + '</svg>';
  }

  function openCleanModalV159(innerHtml) {
    var ov = document.getElementById("orig-modal-overlay-v159");
    if (!ov) {
      ov = document.createElement("div");
      ov.id = "orig-modal-overlay-v159";
      ov.onclick = function(e) {
        if (e.target === ov) ov.classList.remove("open");
      };
      document.body.appendChild(ov);
    }
    ov.innerHTML = '<div class="orig-modal-box-v159">' + innerHtml + '</div>';
    ov.classList.add("open");
    return ov;
  }

  function closeCleanModalV159() {
    var ov = document.getElementById("orig-modal-overlay-v159");
    if (ov) ov.classList.remove("open");
  }

  // مسح جلسة العميل فعلياً عند تأكيد تسجيل الخروج
  function performRealLogoutV159() {
    try {
      var keysToRemove = [];
      for (var i = 0; i < localStorage.length; i++) {
        var k = localStorage.key(i);
        if (!k) continue;
        var kl = k.toLowerCase();
        if (kl.indexOf("cart") !== -1) continue; // الحفاظ على السلة اختيارياً أو مسح بيانات الحساب فقط
        if (kl.indexOf("customer") !== -1 || kl.indexOf("account") !== -1 ||
            kl.indexOf("profile") !== -1 || kl.indexOf("user") !== -1 ||
            kl.indexOf("phone") !== -1 || kl.indexOf("auth") !== -1 ||
            kl.indexOf("session") !== -1 || kl.indexOf("orig_cust") !== -1) {
          keysToRemove.push(k);
        }
      }
      for (var j = 0; j < keysToRemove.length; j++) {
        localStorage.removeItem(keysToRemove[j]);
      }
      sessionStorage.clear();
    } catch (_e) {}

    fetch("/api/auth/logout", { method: "POST" }).catch(function() {}).finally(function() {
      window.location.href = "/";
    });
  }

  function showLogoutConfirmV159() {
    openCleanModalV159(
      '<div style="width:48px;height:48px;margin:0 auto 10px;border-radius:15px;background:#f8f7f2;border:1.5px solid #d8b454;display:flex;align-items:center;justify-content:center;">' +
        svgIcon('<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>') +
      '</div>' +
      '<h3 class="orig-modal-title-v159">تأكيد تسجيل الخروج</h3>' +
      '<p class="orig-modal-desc-v159">هل أنت متأكد أنك تريد تسجيل الخروج من حسابك في متجر أورجنال؟</p>' +
      '<div class="orig-modal-actions-v159">' +
        '<button type="button" class="orig-modal-btn-primary-v159" id="orig-confirm-logout-yes">نعم، تسجيل الخروج</button>' +
        '<button type="button" class="orig-modal-btn-cancel-v159" id="orig-confirm-logout-no">إلغاء</button>' +
      '</div>'
    );
    document.getElementById("orig-confirm-logout-yes").onclick = performRealLogoutV159;
    document.getElementById("orig-confirm-logout-no").onclick = closeCleanModalV159;
  }

  function showAboutAppModalV159() {
    openCleanModalV159(
      '<div style="width:52px;height:52px;margin:0 auto 10px;border-radius:16px;background:#13462f;border:1.5px solid #d8b454;display:flex;align-items:center;justify-content:center;color:#e7c972;font-weight:900;font-size:22px;">O</div>' +
      '<h3 class="orig-modal-title-v159">متجر أورجنال (ORIGINAL)</h3>' +
      '<p class="orig-modal-desc-v159">بقالة ذكية متكاملة في صنعاء لتوصيل كافة احتياجاتك المنزلية والغذائية الطازجة لباب بيتك بسرعة وجودة مضمونة.</p>' +
      '<div style="background:#f8f7f2;border:1px solid rgba(216,180,84,0.45);border-radius:14px;padding:10px 12px;margin-bottom:14px;text-align:right;font-size:12.5px;color:#13462f;font-weight:700;line-height:1.7;">' +
        '<div>⏰ أوقات التوصيل: يومياً 8:30 ص – 1:00 ص</div>' +
        '<div>📍 النطاق: صنعاء — توصيل سريع لباب البيت</div>' +
      '</div>' +
      '<button type="button" class="orig-modal-btn-primary-v159" style="width:100%;" id="orig-about-close-v159">حسناً</button>'
    );
    document.getElementById("orig-about-close-v159").onclick = closeCleanModalV159;
  }

  function readAccountInfoV159(accPage) {
    var name = "عميل أورجنال";
    var phone = "";
    try {
      var els = accPage.querySelectorAll(".original-account-info-grid > div, .original-account-card h2, .original-account-card h3, .original-account-card p, .original-account-card span");
      for (var i = 0; i < els.length; i++) {
        var t = (els[i].textContent || "").trim();
        if (!t || t.length > 50) continue;
        if (/^7[0-9]{8}$/.test(t.replace(/\s+/g, ""))) {
          phone = t.replace(/\s+/g, "");
        } else if (t !== "الاسم" && t !== "رقم الجوال" && t !== "رقم الهاتف" && t !== "تعديل" && t !== "تعديل البيانات" && t !== "حسابي" && t !== "تسجيل الخروج" && t.indexOf("مكتملة") === -1 && name === "عميل أورجنال") {
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

  function openOriginalSectionTemporarilyV159(accPage, triggerSelectorText) {
    accPage.classList.remove("orig-v159-active");
    var root = document.getElementById("orig-acc-v159-root");
    if (root) root.style.display = "none";

    var backBar = document.getElementById("orig-back-to-acc-v159");
    if (!backBar) {
      backBar = document.createElement("button");
      backBar.id = "orig-back-to-acc-v159";
      backBar.type = "button";
      backBar.style.cssText = "margin-bottom:10px;padding:8px 14px;border-radius:12px;border:1px solid #d8b454;background:#13462f;color:#e7c972;font-weight:800;font-size:13px;cursor:pointer;";
      backBar.textContent = "→ العودة لواجهة حسابي";
      backBar.onclick = function() {
        backBar.remove();
        if (root) root.style.display = "block";
        accPage.classList.add("orig-v159-active");
      };
      accPage.insertBefore(backBar, accPage.firstChild);
    }

    var btns = accPage.querySelectorAll("button");
    for (var i = 0; i < btns.length; i++) {
      if ((btns[i].textContent || "").indexOf(triggerSelectorText) !== -1) {
        btns[i].click();
        break;
      }
    }
  }

  function buildAccountScreenV159() {
    if (window.location.pathname.indexOf("/admin") === 0) return;
    var accPage = document.querySelector(".original-account-page");
    if (!accPage) return;
    if (document.getElementById("orig-acc-v159-root")) return;
    if (document.getElementById("orig-back-to-acc-v159")) return;
    if (accPage.querySelector("form input[type='text'], form input[type='tel']")) return;

    var info = readAccountInfoV159(accPage);
    accPage.classList.add("orig-v159-active");

    var root = document.createElement("div");
    root.id = "orig-acc-v159-root";

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
      '<div class="orig-acc-hero-v159">' +
        '<div class="orig-acc-avatar-ring-v159">' +
          '<svg xmlns="' + XML_NS + '" width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#e7c972" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' + userPath + '</svg>' +
        '</div>' +
        '<div class="orig-acc-hero-info-v159">' +
          '<div class="orig-acc-hero-greet-v159">أهلاً بك في متجر أورجنال</div>' +
          '<div class="orig-acc-hero-name-v159">' + info.name + '</div>' +
          '<div class="orig-acc-hero-phone-v159">📞 ' + info.phone + '</div>' +
        '</div>' +
      '</div>' +

      '<div class="orig-acc-grid4-v159">' +
        '<button type="button" class="orig-acc-tile-v159" id="orig-tile-notif-v159"><div class="orig-acc-tile-ico-v159">' + svgIcon(bellPath) + '</div><span class="orig-acc-tile-txt-v159">إشعاراتي</span></button>' +
        '<button type="button" class="orig-acc-tile-v159" id="orig-tile-orders-v159"><div class="orig-acc-tile-ico-v159">' + svgIcon(boxPath) + '</div><span class="orig-acc-tile-txt-v159">طلباتي</span></button>' +
        '<button type="button" class="orig-acc-tile-v159" id="orig-tile-favs-v159"><div class="orig-acc-tile-ico-v159">' + svgIcon(heartPath) + '</div><span class="orig-acc-tile-txt-v159">المفضلة</span></button>' +
        '<button type="button" class="orig-acc-tile-v159" id="orig-tile-addr-v159"><div class="orig-acc-tile-ico-v159">' + svgIcon(pinPath) + '</div><span class="orig-acc-tile-txt-v159">عناويني</span></button>' +
      '</div>' +

      '<div class="orig-acc-list-v159">' +
        '<button type="button" class="orig-acc-row-v159" id="orig-row-notif-v159"><div class="orig-acc-row-right-v159"><div class="orig-acc-row-ico-v159">' + svgIcon(bellPath) + '</div><div class="orig-acc-row-title-v159">إشعارات الطلبات والعروض</div></div>' + chevLeft + '</button>' +
        '<button type="button" class="orig-acc-row-v159" id="orig-row-profile-v159"><div class="orig-acc-row-right-v159"><div class="orig-acc-row-ico-v159">' + svgIcon(userPath) + '</div><div><div class="orig-acc-row-title-v159">' + info.name + '</div><div class="orig-acc-row-sub-v159">رقم الجوال: ' + info.phone + '</div></div></div>' + chevLeft + '</button>' +
        '<button type="button" class="orig-acc-row-v159" id="orig-row-settings-v159"><div class="orig-acc-row-right-v159"><div class="orig-acc-row-ico-v159">' + svgIcon(gearPath) + '</div><div class="orig-acc-row-title-v159">إعدادات الحساب</div></div>' + chevLeft + '</button>' +
        '<button type="button" class="orig-acc-row-v159" id="orig-row-support-v159"><div class="orig-acc-row-right-v159"><div class="orig-acc-row-ico-v159">' + svgIcon(headsetPath) + '</div><div class="orig-acc-row-title-v159">التواصل مع خدمة العملاء</div></div>' + chevLeft + '</button>' +
        '<button type="button" class="orig-acc-row-v159" id="orig-row-about-v159"><div class="orig-acc-row-right-v159"><div class="orig-acc-row-ico-v159">' + svgIcon(infoPath) + '</div><div class="orig-acc-row-title-v159">معلومات التطبيق</div></div>' + chevLeft + '</button>' +
      '</div>' +

      '<button type="button" class="orig-acc-logout-v159" id="orig-acc-logout-v159">تسجيل الخروج</button>';

    accPage.insertBefore(root, accPage.firstChild);

    var openNotif = function() {
      var topBell = document.getElementById("orig-header-bell-v141");
      if (topBell) topBell.click();
    };
    document.getElementById("orig-tile-notif-v159").onclick = openNotif;
    document.getElementById("orig-row-notif-v159").onclick = openNotif;

    document.getElementById("orig-tile-orders-v159").onclick = function() {
      var o = document.querySelector("header a[href*='orders']");
      if (o) o.click(); else window.location.href = "/orders";
    };
    document.getElementById("orig-tile-favs-v159").onclick = function() {
      var f = document.querySelector("header a[href*='favorites']");
      if (f) f.click(); else window.location.href = "/favorites";
    };
    document.getElementById("orig-tile-addr-v159").onclick = function() { openOriginalSectionTemporarilyV159(accPage, "إضافة عنوان"); };
    document.getElementById("orig-row-profile-v159").onclick = function() { openOriginalSectionTemporarilyV159(accPage, "تعديل"); };
    document.getElementById("orig-row-settings-v159").onclick = function() { openOriginalSectionTemporarilyV159(accPage, "تعديل"); };

    document.getElementById("orig-row-support-v159").onclick = function() {
      var wa = document.querySelector("a[href*='wa.me']");
      if (wa && wa.getAttribute("href")) {
        window.open(wa.getAttribute("href"), "_blank");
      } else {
        window.open("https://wa.me/967779542219", "_blank");
      }
    };

    document.getElementById("orig-row-about-v159").onclick = showAboutAppModalV159;
    document.getElementById("orig-acc-logout-v159").onclick = showLogoutConfirmV159;
  }

  setInterval(buildAccountScreenV159, 350);
})();
</script>
<!-- ORIGINAL_ACCOUNT_V159_END -->"""

if "</body>" in html:
    html = html.replace("</body>", v159_block + "\n</body>", 1)
else:
    html = html + "\n" + v159_block

html_path.write_text(html, encoding="utf-8")
print("✅ تم تركيب النسخة v159: صفحة حسابي موحدة بدون أي تكرار + تأكيد تسجيل الخروج الفعلي + نافذة معلومات التطبيق الأنيقة!")

os.system("git add client/index.html && git commit -m 'Fix v159: eliminate duplicate account sections, add real logout confirmation modal, and clean About App modal' && git push origin main")
print("🚀 تم رفع التحديث v159 إلى Render بنجاح!")
