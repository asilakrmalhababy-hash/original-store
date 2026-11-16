import os, re, subprocess

index_path = "client/index.html"
with open(index_path, "r", encoding="utf-8") as f:
    html = f.read()

html = re.sub(
    r'<!-- ORIGINAL ACCOUNT (?:POLISH V157|REDESIGN V158|REDESIGN V159|FULL POLISH V160|PERFECT V161) START -->.*?<!-- ORIGINAL ACCOUNT (?:POLISH V157|REDESIGN V158|REDESIGN V159|FULL POLISH V160|PERFECT V161) END -->\s*',
    '',
    html,
    flags=re.DOTALL
)

block_v161 = r"""<!-- ORIGINAL ACCOUNT PERFECT V161 START -->
<style id="orig-account-perfect-v161">
  :root {
    --orig-em-dark: #0b2b1d;
    --orig-em-main: #13462f;
    --orig-em-mid: #1a5c3e;
    --orig-gold: #d8b454;
    --orig-gold-light: #e7c972;
    --orig-cream: #f8f7f2;
    --orig-card: #ffffff;
  }

  /* 1. توحيد إطار شريط البحث العلوي ومنع ازدواجيته */
  header.store-header .header-search {
    flex: 1 0 100% !important;
    order: 3 !important;
    width: 100% !important;
    margin: 2px 0 0 0 !important;
    padding: 0 !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
  }
  header.store-header .header-search > div,
  header.store-header .header-search input {
    border-radius: 999px !important;
  }

  /* 2. إعداد حاوية صفحة حسابي وإخفاء العناصر المكررة */
  .original-account-page {
    background: var(--orig-cream) !important;
    min-height: calc(100vh - 130px) !important;
    padding: 12px 14px 105px 14px !important;
    direction: rtl !important;
    font-family: 'Cairo', 'Tajawal', sans-serif !important;
    position: relative !important;
    overflow-x: hidden !important;
  }

  .original-account-page > .page-title-row,
  #orig-vip-loyalty-section-v140 {
    display: none !important;
  }

  /* إخفاء فقاعة الواتساب العائمة داخل صفحة حسابي حتى لا تغطي نصوص العناوين */
  body.orig-on-account-page a[href*="wa.me"]:not(#orig-acc-v161-root a),
  body.orig-on-account-page .floating-whatsapp,
  body.orig-on-account-page [class*="whatsapp-float"],
  body.orig-on-account-page [id*="whatsapp"] {
    display: none !important;
  }

  /* 3. وضع الواجهة الرئيسية (Account Hub): إخفاء كل العناصر القديمة تحت زر تسجيل الخروج */
  .original-account-page.orig-mode-hub > *:not(#orig-acc-v161-root) {
    display: none !important;
  }
  .original-account-page.orig-mode-hub > #orig-acc-v161-root {
    display: block !important;
  }

  /* 4. وضع النوافذ الفرعية المنزلقة (إعدادات الحساب / عناويني) */
  .original-account-page.orig-mode-sub > #orig-acc-v161-root {
    display: none !important;
  }

  /* إخفاء البطاقة الخضراء المكررة وروابط الملخص دائماً في النوافذ الفرعية */
  .original-account-page.orig-mode-sub > [data-orig-sec="legacy-hero"],
  .original-account-page.orig-mode-sub > [data-orig-sec="legacy-links"],
  .original-account-page.orig-mode-sub > [data-orig-sec="profile-readonly"] {
    display: none !important;
  }

  /* عند فتح إعدادات الحساب: إظهار نموذج تعديل البيانات فقط وإخفاء العناوين تماماً */
  .original-account-page.orig-sub-profile > [data-orig-sec="addresses"] {
    display: none !important;
  }
  .original-account-page.orig-sub-profile > [data-orig-sec="profile-form"] {
    display: block !important;
  }

  /* عند فتح عناويني: إظهار قسم العناوين فقط وإخفاء البيانات الشخصية تماماً */
  .original-account-page.orig-sub-addresses > [data-orig-sec="profile-form"] {
    display: none !important;
  }
  .original-account-page.orig-sub-addresses > [data-orig-sec="addresses"] {
    display: block !important;
  }

  /* حركات الانزلاق السلسة عند الفتح والإغلاق */
  .original-account-page.orig-anim-enter > #orig-subview-sheet-head-v161,
  .original-account-page.orig-anim-enter > [data-orig-sec="profile-form"],
  .original-account-page.orig-anim-enter > [data-orig-sec="addresses"] {
    opacity: 0 !important;
    transform: translate3d(0, 44px, 0) scale(0.97) !important;
  }

  .original-account-page.orig-anim-active > #orig-subview-sheet-head-v161,
  .original-account-page.orig-anim-active > [data-orig-sec="profile-form"],
  .original-account-page.orig-anim-active > [data-orig-sec="addresses"] {
    opacity: 1 !important;
    transform: translate3d(0, 0, 0) scale(1) !important;
    transition: transform 0.38s cubic-bezier(0.22, 1, 0.36, 1), opacity 0.3s ease !important;
  }

  .original-account-page.orig-anim-exit > #orig-subview-sheet-head-v161,
  .original-account-page.orig-anim-exit > [data-orig-sec="profile-form"],
  .original-account-page.orig-anim-exit > [data-orig-sec="addresses"] {
    opacity: 0 !important;
    transform: translate3d(0, 48px, 0) scale(0.97) !important;
    transition: transform 0.25s cubic-bezier(0.4, 0, 1, 1), opacity 0.22s ease !important;
  }

  #orig-acc-v161-root {
    transition: transform 0.28s cubic-bezier(0.22, 1, 0.36, 1), opacity 0.24s ease !important;
  }
  #orig-acc-v161-root.orig-hub-hiding {
    opacity: 0 !important;
    transform: scale(0.96) translateY(10px) !important;
  }

  /* 5. تصميم هيدر النافذة الفرعية مع مقبض السحب (Drag Handle) */
  #orig-subview-sheet-head-v161 {
    display: none;
    background: linear-gradient(135deg, #13462f 0%, #0b2b1d 100%) !important;
    border: 1.5px solid var(--orig-gold) !important;
    border-radius: 20px !important;
    padding: 10px 16px 14px 16px !important;
    margin-bottom: 14px !important;
    box-shadow: 0 10px 26px rgba(11, 43, 29, 0.16) !important;
    touch-action: pan-y !important;
    user-select: none !important;
  }
  .original-account-page.orig-mode-sub > #orig-subview-sheet-head-v161 {
    display: block !important;
  }
  .orig-sheet-pill-v161 {
    width: 42px;
    height: 4px;
    border-radius: 999px;
    background: rgba(216, 180, 84, 0.55);
    margin: 0 auto 10px auto;
  }
  .orig-sheet-toprow-v161 {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }
  .orig-sheet-title-wrap-v161 {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .orig-sheet-title-v161 {
    color: #ffffff;
    font-size: 16px;
    font-weight: 800;
    margin: 0;
  }
  .orig-sheet-sub-v161 {
    color: rgba(231, 201, 114, 0.9);
    font-size: 11.5px;
    font-weight: 600;
    margin: 0;
  }
  .orig-sheet-back-btn-v161 {
    background: rgba(216, 180, 84, 0.16);
    border: 1px solid rgba(216, 180, 84, 0.6);
    color: var(--orig-gold-light);
    height: 36px;
    padding: 0 14px;
    border-radius: 12px;
    font-size: 13px;
    font-weight: 800;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
    flex-shrink: 0;
    transition: transform 0.15s ease, background 0.15s ease;
  }
  .orig-sheet-back-btn-v161:active {
    transform: scale(0.95);
    background: rgba(216, 180, 84, 0.28);
  }

  /* 6. إصلاح شامل ومتوازن لجميع الحقول والنماذج داخل إعدادات الحساب والعناوين */
  .original-account-page [data-orig-sec="profile-form"],
  .original-account-page [data-orig-sec="addresses"] {
    width: 100% !important;
    box-sizing: border-box !important;
  }

  /* تقييد أي أيقونة SVG داخل النماذج والبطاقات لمنع ظهور علامة صح عملاقة */
  .original-account-page [data-orig-sec="profile-form"] svg,
  .original-account-page [data-orig-sec="addresses"] svg {
    width: 18px !important;
    height: 18px !important;
    min-width: 18px !important;
    max-width: 20px !important;
    min-height: 18px !important;
    max-height: 20px !important;
    flex-shrink: 0 !important;
  }

  /* تحويل أي شبكة متعددة الأعمدة في النماذج إلى عمود واحد متوازن 100% */
  .orig-vertical-fields-v161 {
    display: flex !important;
    flex-direction: column !important;
    grid-template-columns: 1fr !important;
    gap: 14px !important;
    width: 100% !important;
  }

  .orig-field-unit-v161 {
    display: flex !important;
    flex-direction: column !important;
    gap: 6px !important;
    width: 100% !important;
    margin: 0 !important;
  }

  /* ضبط عنوان الحقل وشارة الشبكة (يمن موبايل) في سطر واحد متوازن */
  .orig-label-head-v161 {
    display: flex !important;
    flex-direction: row !important;
    align-items: center !important;
    justify-content: space-between !important;
    flex-wrap: nowrap !important;
    width: 100% !important;
    gap: 8px !important;
    font-size: 13.5px !important;
    font-weight: 800 !important;
    color: #1c2e24 !important;
    line-height: 1.3 !important;
  }

  /* توحيد جميع حقول النص والجوال والقوائم */
  .original-account-page input:not([type="checkbox"]):not([type="radio"]),
  .original-account-page select,
  .original-account-page textarea {
    width: 100% !important;
    height: 48px !important;
    min-height: 48px !important;
    padding: 0 16px !important;
    border-radius: 14px !important;
    border: 1.5px solid rgba(216, 180, 84, 0.5) !important;
    background: #fcfbf7 !important;
    color: #132a1f !important;
    font-size: 15px !important;
    font-weight: 700 !important;
    box-sizing: border-box !important;
    box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.03) !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease, background 0.2s ease !important;
    margin: 0 !important;
  }
  .original-account-page textarea {
    height: auto !important;
    min-height: 86px !important;
    padding: 12px 16px !important;
    line-height: 1.5 !important;
  }
  .original-account-page input:not([type="checkbox"]):not([type="radio"]):focus,
  .original-account-page select:focus,
  .original-account-page textarea:focus {
    outline: none !important;
    border-color: var(--orig-em-main) !important;
    background: #ffffff !important;
    box-shadow: 0 0 0 3px rgba(19, 70, 47, 0.12) !important;
  }

  /* إصلاح جذري لمربع الاختيار (تعيين كافتراضي) لمنع تضخمه */
  .original-account-page input[type="checkbox"],
  .original-account-page input[type="radio"] {
    width: 20px !important;
    height: 20px !important;
    min-width: 20px !important;
    max-width: 20px !important;
    min-height: 20px !important;
    max-height: 20px !important;
    flex: 0 0 20px !important;
    margin: 0 !important;
    padding: 0 !important;
    accent-color: var(--orig-em-main) !important;
    border-radius: 6px !important;
    cursor: pointer !important;
    appearance: auto !important;
    -webkit-appearance: checkbox !important;
  }

  .orig-default-check-row-v161 {
    display: flex !important;
    flex-direction: row !important;
    align-items: center !important;
    justify-content: flex-start !important;
    gap: 10px !important;
    width: 100% !important;
    min-height: 48px !important;
    padding: 10px 14px !important;
    margin: 6px 0 !important;
    background: #f5f2e8 !important;
    border: 1.5px solid rgba(216, 180, 84, 0.45) !important;
    border-radius: 14px !important;
    box-sizing: border-box !important;
    cursor: pointer !important;
    font-size: 14px !important;
    font-weight: 800 !important;
    color: var(--orig-em-main) !important;
  }

  /* شريط أزرار الحفظ والإلغاء المتوازن */
  .orig-btn-row-v161 {
    display: grid !important;
    grid-template-columns: 2fr 1fr !important;
    gap: 10px !important;
    width: 100% !important;
    margin-top: 14px !important;
    align-items: center !important;
  }
  .orig-btn-row-v161 > button {
    height: 48px !important;
    border-radius: 14px !important;
    font-size: 14.5px !important;
    font-weight: 800 !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 8px !important;
    margin: 0 !important;
    cursor: pointer !important;
    transition: transform 0.15s ease, opacity 0.15s ease !important;
  }
  .orig-btn-row-v161 > button:active {
    transform: scale(0.97) !important;
  }
  .orig-btn-primary-v161 {
    background: linear-gradient(135deg, #13462f 0%, #0b2b1d 100%) !important;
    color: #ffffff !important;
    border: 1.5px solid var(--orig-gold) !important;
    box-shadow: 0 6px 16px rgba(19, 70, 47, 0.2) !important;
  }
  .orig-btn-secondary-v161 {
    background: #f2efe4 !important;
    color: #374a3f !important;
    border: 1.5px solid rgba(216, 180, 84, 0.4) !important;
  }

  /* أزرار اختيار سريع لاسم العنوان داخل نموذج العنوان */
  .orig-addr-chips-v161 {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 4px;
    margin-bottom: 4px;
  }
  .orig-addr-chip-v161 {
    background: #f5f2e8;
    border: 1px solid rgba(216, 180, 84, 0.55);
    color: var(--orig-em-main);
    padding: 5px 12px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.15s ease;
  }
  .orig-addr-chip-v161:active,
  .orig-addr-chip-v161.active {
    background: var(--orig-em-main);
    color: var(--orig-gold-light);
    border-color: var(--orig-gold);
  }

  /* تنسيق بطاقة هيدر العناوين وبطاقات العناوين المحفوظة */
  .orig-addr-hero-card-v161 {
    background: linear-gradient(135deg, #13462f 0%, #0b2b1d 100%) !important;
    border: 1.5px solid var(--orig-gold) !important;
    border-radius: 20px !important;
    padding: 16px !important;
    margin-bottom: 14px !important;
    box-shadow: 0 8px 22px rgba(11, 43, 29, 0.14) !important;
  }
  .orig-saved-addr-card-v161 {
    background: #ffffff !important;
    border: 1.5px solid rgba(216, 180, 84, 0.55) !important;
    border-radius: 18px !important;
    padding: 15px 16px !important;
    margin-bottom: 12px !important;
    box-shadow: 0 6px 18px rgba(19, 70, 47, 0.06) !important;
  }
  .orig-saved-addr-card-v161 button {
    height: 34px !important;
    min-height: 34px !important;
    padding: 0 12px !important;
    border-radius: 10px !important;
    font-size: 12.5px !important;
    font-weight: 700 !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 5px !important;
  }

  /* 7. تصميم واجهة حسابي الرئيسية (Hub) المطابقة للصورة 250104.png بألوان المتجر */
  #orig-acc-v161-root {
    width: 100%;
    max-width: 540px;
    margin: 0 auto;
  }

  .orig-hero-banner-v161 {
    position: relative;
    background: linear-gradient(135deg, #13462f 0%, #1a5c3e 52%, #0b2b1d 100%);
    border-radius: 22px;
    border: 2px solid var(--orig-gold);
    padding: 20px 18px;
    color: #ffffff;
    box-shadow: 0 10px 26px rgba(11, 43, 29, 0.22);
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
    margin-bottom: 14px;
  }
  .orig-hero-watermark-v161 {
    position: absolute;
    left: -14px;
    bottom: -18px;
    width: 135px !important;
    height: 135px !important;
    max-width: 135px !important;
    max-height: 135px !important;
    opacity: 0.13;
    pointer-events: none;
  }
  .orig-hero-avatar-v161 {
    width: 68px;
    height: 68px;
    border-radius: 50%;
    border: 2.5px solid var(--orig-gold);
    background: radial-gradient(circle at 30% 30%, #1f6b49, #0b2b1d);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
  }
  .orig-hero-avatar-v161 svg {
    width: 36px !important;
    height: 36px !important;
    fill: #ffffff;
  }
  .orig-hero-info-v161 {
    flex: 1;
    text-align: right;
    z-index: 1;
  }
  .orig-hero-welcome-v161 {
    font-size: 14px;
    color: var(--orig-gold-light);
    font-weight: 600;
    margin: 0 0 2px 0;
  }
  .orig-hero-name-v161 {
    font-size: 21px;
    font-weight: 800;
    color: #ffffff;
    margin: 0 0 6px 0;
    line-height: 1.25;
  }
  .orig-hero-phone-v161 {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 14.5px;
    font-weight: 700;
    color: #f3efe3;
    direction: ltr;
  }
  .orig-hero-phone-v161 svg {
    width: 15px !important;
    height: 15px !important;
    fill: var(--orig-gold);
  }

  /* الأزرار الـ 4 المربعة السريعة */
  .orig-quick-grid-v161 {
    display: grid !important;
    grid-template-columns: repeat(4, 1fr) !important;
    gap: 9px !important;
    margin-bottom: 14px !important;
  }
  .orig-quick-card-v161 {
    background: #ffffff;
    border: 1.5px solid rgba(216, 180, 84, 0.38);
    border-radius: 18px;
    padding: 13px 6px 11px 6px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 7px;
    box-shadow: 0 4px 14px rgba(19, 70, 47, 0.05);
    cursor: pointer;
    transition: transform 0.16s ease, border-color 0.16s ease;
  }
  .orig-quick-card-v161:active {
    transform: scale(0.95);
    border-color: var(--orig-gold);
  }
  .orig-quick-card-v161 svg {
    width: 26px !important;
    height: 26px !important;
  }
  .orig-quick-label-v161 {
    font-size: 13px;
    font-weight: 800;
    color: var(--orig-em-main);
  }

  /* صفوف القائمة الـ 5 */
  .orig-menu-stack-v161 {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-bottom: 14px;
  }
  .orig-menu-item-v161 {
    background: #ffffff;
    border: 1.5px solid rgba(216, 180, 84, 0.32);
    border-radius: 18px;
    padding: 13px 15px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    box-shadow: 0 4px 12px rgba(19, 70, 47, 0.04);
    cursor: pointer;
    transition: transform 0.15s ease, border-color 0.15s ease;
  }
  .orig-menu-item-v161:active {
    transform: scale(0.985);
    border-color: var(--orig-gold);
  }
  .orig-menu-right-v161 {
    display: flex;
    align-items: center;
    gap: 12px;
    flex: 1;
    min-width: 0;
  }
  .orig-menu-icon-v161 {
    width: 38px;
    height: 38px;
    border-radius: 12px;
    background: rgba(19, 70, 47, 0.07);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .orig-menu-icon-v161 svg {
    width: 22px !important;
    height: 22px !important;
  }
  .orig-menu-text-v161 {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    text-align: right;
    min-width: 0;
  }
  .orig-menu-title-v161 {
    font-size: 15.5px;
    font-weight: 800;
    color: #152b20;
    line-height: 1.3;
  }
  .orig-menu-sub-v161 {
    font-size: 12.5px;
    font-weight: 600;
    color: #5a6b61;
    margin-top: 2px;
  }
  .orig-menu-arrow-v161 {
    width: 20px !important;
    height: 20px !important;
    flex-shrink: 0;
    stroke: #1f3a2c;
  }

  /* زر تسجيل الخروج */
  .orig-logout-btn-v161 {
    width: 100%;
    height: 50px;
    background: #ffffff;
    border: 1.5px solid var(--orig-em-main);
    border-radius: 999px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    color: var(--orig-em-main);
    font-size: 16px;
    font-weight: 800;
    cursor: pointer;
    box-shadow: 0 4px 12px rgba(19, 70, 47, 0.06);
    transition: all 0.16s ease;
  }
  .orig-logout-btn-v161:active {
    transform: scale(0.98);
    background: rgba(19, 70, 47, 0.06);
  }
  .orig-logout-btn-v161 svg {
    width: 22px !important;
    height: 22px !important;
  }

  /* النوافذ المنبثقة (تأكيد الخروج + معلومات التطبيق) */
  .orig-modal-backdrop-v161 {
    position: fixed;
    inset: 0;
    background: rgba(8, 24, 16, 0.62);
    backdrop-filter: blur(5px);
    -webkit-backdrop-filter: blur(5px);
    z-index: 99999;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 18px;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.24s ease;
    direction: rtl;
    font-family: 'Cairo', 'Tajawal', sans-serif;
  }
  .orig-modal-backdrop-v161.open {
    opacity: 1;
    pointer-events: auto;
  }
  .orig-modal-card-v161 {
    width: 100%;
    max-width: 370px;
    background: #ffffff;
    border: 2px solid var(--orig-gold);
    border-radius: 24px;
    padding: 22px 20px 18px 20px;
    text-align: center;
    box-shadow: 0 18px 42px rgba(0, 0, 0, 0.28);
    transform: translateY(20px) scale(0.95);
    transition: transform 0.26s cubic-bezier(0.22, 1, 0.36, 1);
  }
  .orig-modal-backdrop-v161.open .orig-modal-card-v161 {
    transform: translateY(0) scale(1);
  }
  .orig-modal-emblem-v161 {
    width: 58px;
    height: 58px;
    border-radius: 18px;
    background: linear-gradient(135deg, #13462f, #0b2b1d);
    border: 2px solid var(--orig-gold);
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 12px auto;
    color: var(--orig-gold-light);
    font-size: 24px;
    font-weight: 900;
  }
  .orig-modal-title-v161 {
    font-size: 18px;
    font-weight: 800;
    color: var(--orig-em-main);
    margin: 0 0 8px 0;
  }
  .orig-modal-desc-v161 {
    font-size: 13.5px;
    color: #495a50;
    line-height: 1.6;
    margin: 0 0 16px 0;
    font-weight: 600;
  }
  .orig-modal-actions-v161 {
    display: flex;
    gap: 10px;
  }
  .orig-modal-btn-v161 {
    flex: 1;
    height: 44px;
    border-radius: 13px;
    font-size: 14px;
    font-weight: 800;
    cursor: pointer;
    border: none;
  }
  .orig-modal-btn-v161.confirm {
    background: #b91c1c;
    color: #ffffff;
  }
  .orig-modal-btn-v161.primary {
    background: linear-gradient(135deg, #13462f, #0b2b1d);
    color: var(--orig-gold-light);
    border: 1.5px solid var(--orig-gold);
  }
  .orig-modal-btn-v161.cancel {
    background: #f1efe6;
    color: #2c3e34;
    border: 1px solid rgba(216, 180, 84, 0.4);
  }
</style>

<script>
(function() {
  if (window.__origAccV161Loaded) return;
  window.__origAccV161Loaded = true;

  let currentSubMode = null; // null | 'profile' | 'addresses'

  function getCustomerInfo() {
    let name = "أصيل الحبابي";
    let phone = "770731619";
    try {
      const page = document.querySelector(".original-account-page");
      if (page) {
        const inputs = page.querySelectorAll('input:not([type="checkbox"]):not([type="radio"])');
        if (inputs.length >= 2) {
          const v0 = (inputs[0].value || "").trim();
          const v1 = (inputs[1].value || "").trim();
          if (v0 && !/^\d+$/.test(v0)) name = v0;
          if (v1 && /^\d{7,15}$/.test(v1.replace(/\s+/g, ""))) phone = v1.replace(/\s+/g, "");
        }
        const h3s = page.querySelectorAll(".original-account-identity h3, .original-account-card h3, .original-account-card strong");
        h3s.forEach(el => {
          const t = (el.textContent || "").trim();
          if (t && t.length > 2 && t.length < 35 && !t.includes("بيانات") && !t.includes("عناوين") && !t.includes("الاسم") && !t.includes("رقم")) {
            name = t;
          }
        });
        const m = (page.innerText || "").match(/7\d{8}/);
        if (m) phone = m[0];
      }
      for (let i = 0; i < localStorage.length; i++) {
        const k = localStorage.key(i);
        const raw = localStorage.getItem(k);
        if (!raw || raw.length > 5000) continue;
        if (raw.includes("77") || raw.includes("name") || raw.includes("phone")) {
          try {
            const obj = JSON.parse(raw);
            if (obj && typeof obj === "object") {
              if (obj.name && typeof obj.name === "string" && obj.name.trim().length > 1) name = obj.name.trim();
              if (obj.customerName && typeof obj.customerName === "string" && obj.customerName.trim().length > 1) name = obj.customerName.trim();
              if (obj.phone && typeof obj.phone === "string" && obj.phone.trim().length >= 7) phone = obj.phone.trim();
              if (obj.customerPhone && typeof obj.customerPhone === "string" && obj.customerPhone.trim().length >= 7) phone = obj.customerPhone.trim();
            }
          } catch (_) {}
        }
      }
    } catch (_) {}
    return { name, phone };
  }

  function tagAccountSections(page) {
    if (!page) return;
    const children = Array.from(page.children);
    let hitAddresses = false;

    children.forEach(ch => {
      if (ch.id === "orig-acc-v161-root" || ch.id === "orig-subview-sheet-head-v161") return;
      if (ch.classList.contains("page-title-row")) return;

      const txt = (ch.innerText || "").trim();
      if (txt.includes("عناوين التوصيل المحفوظة") || txt.includes("إضافة عنوان")) {
        hitAddresses = true;
      }

      if (hitAddresses) {
        ch.setAttribute("data-orig-sec", "addresses");
      } else if (ch.classList.contains("original-account-card") && (txt.includes("بيانات مكتملة") || txt.includes("تعديل البيانات") || ch.querySelector(".original-account-avatar"))) {
        ch.setAttribute("data-orig-sec", "legacy-hero");
      } else if (txt.includes("تحديث البيانات الشخصية") || (ch.querySelector('input') && (txt.includes("الاسم الكامل") || txt.includes("حفظ البيانات")))) {
        ch.setAttribute("data-orig-sec", "profile-form");
      } else if (txt.includes("الاسم الكامل للمستلم") || txt.includes("رقم الجوال المعتمد")) {
        ch.setAttribute("data-orig-sec", "profile-readonly");
      } else {
        ch.setAttribute("data-orig-sec", "legacy-links");
      }
    });
  }

  function normalizeFormsAndCards(page) {
    if (!page) return;
    tagAccountSections(page);

    // 1. تقييد جميع أيقونات SVG داخل النماذج والعناوين لمنع ظهور علامة صح كبيرة
    page.querySelectorAll('[data-orig-sec="profile-form"] svg, [data-orig-sec="addresses"] svg').forEach(svg => {
      svg.style.setProperty("width", "18px", "important");
      svg.style.setProperty("height", "18px", "important");
      svg.style.setProperty("max-width", "20px", "important");
      svg.style.setProperty("max-height", "20px", "important");
      svg.style.setProperty("flex-shrink", "0", "important");
    });

    // 2. موازنة جميع الحقول النصية وتحويل أي شبكة من عمودين إلى عمود واحد متناسق
    const inputs = page.querySelectorAll('[data-orig-sec="profile-form"] input:not([type="checkbox"]):not([type="radio"]), [data-orig-sec="addresses"] input:not([type="checkbox"]):not([type="radio"]), [data-orig-sec="addresses"] select, [data-orig-sec="addresses"] textarea');
    inputs.forEach(inp => {
      const unit = inp.closest("label") || inp.parentElement;
      if (unit && unit !== page) {
        unit.classList.add("orig-field-unit-v161");
        // إذا كان الأب المباشر يحتوي على أكثر من حقل جنب بعض، نحوله إلى عمود عمودي متوازن
        const rowParent = unit.parentElement;
        if (rowParent && rowParent !== page && !rowParent.classList.contains("orig-vertical-fields-v161")) {
          const siblingInputs = rowParent.querySelectorAll('input:not([type="checkbox"]):not([type="radio"]), select, textarea');
          if (siblingInputs.length >= 2) {
            rowParent.classList.add("orig-vertical-fields-v161");
          }
        }
        // موازنة سطر العنوان مع شارة الشبكة (مثل: ✓ يمن موبايل)
        Array.from(unit.children).forEach(child => {
          if (child !== inp && child.tagName !== "INPUT" && child.tagName !== "SELECT" && child.tagName !== "TEXTAREA") {
            child.classList.add("orig-label-head-v161");
          }
        });
      }

      // إضافة أزرار اختيار سريع لاسم العنوان (البيت / العمل / العائلة)
      const ph = (inp.getAttribute("placeholder") || "") + " " + ((unit && unit.innerText) || "");
      if ((ph.includes("اسم العنوان") || ph.includes("مسمى العنوان") || ph.includes("المنزل") || ph.includes("الرقاص")) && !unit.querySelector(".orig-addr-chips-v161")) {
        const chips = document.createElement("div");
        chips.className = "orig-addr-chips-v161";
        ["🏠 البيت", "🏢 العمل", "👨‍👩‍👧‍👦 العائلة", "📍 استلام خاص"].forEach(label => {
          const cleanVal = label.replace(/^[^\s]+\s/, "");
          const chip = document.createElement("button");
          chip.type = "button";
          chip.className = "orig-addr-chip-v161";
          chip.textContent = label;
          chip.addEventListener("click", () => {
            const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value")?.set;
            if (nativeSetter) nativeSetter.call(inp, cleanVal);
            else inp.value = cleanVal;
            inp.dispatchEvent(new Event("input", { bubbles: true }));
            inp.dispatchEvent(new Event("change", { bubbles: true }));
            chips.querySelectorAll(".orig-addr-chip-v161").forEach(c => c.classList.remove("active"));
            chip.classList.add("active");
          });
          chips.appendChild(chip);
        });
        unit.appendChild(chips);
      }
    });

    // 3. إصلاح مربع الاختيار (تعيين كافتراضي) وعلامة الصح
    page.querySelectorAll('input[type="checkbox"], input[type="radio"]').forEach(chk => {
      chk.style.setProperty("width", "20px", "important");
      chk.style.setProperty("height", "20px", "important");
      chk.style.setProperty("min-width", "20px", "important");
      chk.style.setProperty("max-width", "20px", "important");
      chk.style.setProperty("flex", "0 0 20px", "important");
      const wrap = chk.closest("label") || chk.parentElement;
      if (wrap && wrap !== page) {
        wrap.classList.add("orig-default-check-row-v161");
      }
    });

    // 4. تنسيق شريط أزرار (حفظ البيانات / حفظ العنوان + إلغاء)
    page.querySelectorAll('[data-orig-sec="profile-form"] button, [data-orig-sec="addresses"] button').forEach(btn => {
      const t = (btn.innerText || "").trim();
      if (t.includes("حفظ") || t.includes("تأكيد") || t.includes("تحديث")) {
        btn.classList.add("orig-btn-primary-v161");
        const p = btn.parentElement;
        if (p && p.querySelectorAll("button").length === 2) {
          p.classList.add("orig-btn-row-v161");
        }
        if (!btn.dataset.origSaveHooked) {
          btn.dataset.origSaveHooked = "1";
          btn.addEventListener("click", () => {
            if (currentSubMode === "profile") {
              setTimeout(() => closeSubViewSmoothly(), 220);
            }
          });
        }
      } else if (t === "إلغاء" || t.includes("إلغاء")) {
        btn.classList.add("orig-btn-secondary-v161");
        if (!btn.dataset.origCancelHooked) {
          btn.dataset.origCancelHooked = "1";
          btn.addEventListener("click", () => {
            if (currentSubMode === "profile") {
              setTimeout(() => closeSubViewSmoothly(), 120);
            }
          });
        }
      }
    });

    // 5. تمييز بطاقة هيدر العناوين وبطاقات العناوين المحفوظة
    page.querySelectorAll('[data-orig-sec="addresses"]').forEach(sec => {
      const txt = (sec.innerText || "").trim();
      if (txt.includes("عناوين التوصيل المحفوظة") && sec.children.length <= 4 && !sec.querySelector("input")) {
        sec.classList.add("orig-addr-hero-card-v161");
      } else if ((txt.includes("تعديل") || txt.includes("الافتراضي")) && !txt.includes("عناوين التوصيل المحفوظة") && !sec.querySelector("input")) {
        sec.classList.add("orig-saved-addr-card-v161");
      }
      sec.querySelectorAll("div, section, article").forEach(sub => {
        const st = (sub.innerText || "").trim();
        if ((st.includes("تعديل") || st.includes("الافتراضي")) && !st.includes("عناوين التوصيل المحفوظة") && !sub.querySelector("input") && sub.children.length >= 2 && sub.children.length <= 6) {
          sub.classList.add("orig-saved-addr-card-v161");
        }
      });
    });
  }

  function ensureSubSheetHeader(page) {
    let head = document.getElementById("orig-subview-sheet-head-v161");
    if (!head) {
      head = document.createElement("div");
      head.id = "orig-subview-sheet-head-v161";
      head.innerHTML = `
        <div class="orig-sheet-pill-v161"></div>
        <div class="orig-sheet-toprow-v161">
          <div class="orig-sheet-title-wrap-v161">
            <h3 class="orig-sheet-title-v161" id="orig-sheet-title-txt-v161">إعدادات الحساب</h3>
            <p class="orig-sheet-sub-v161" id="orig-sheet-sub-txt-v161">اسحب للأسفل أو اضغط رجوع للعودة لحسابك</p>
          </div>
          <button type="button" class="orig-sheet-back-btn-v161" id="orig-sheet-back-btn-v161">
            <span>رجوع</span>
            <span>←</span>
          </button>
        </div>
      `;
      page.prepend(head);

      head.querySelector("#orig-sheet-back-btn-v161").addEventListener("click", () => {
        closeSubViewSmoothly();
      });

      // دعم السحب بالإصبع للأسفل أو لليمين لإغلاق النافذة بنعومة
      let startY = 0, startX = 0, currentY = 0, dragging = false;
      head.addEventListener("touchstart", (e) => {
        if (!e.touches || !e.touches[0]) return;
        startY = e.touches[0].clientY;
        startX = e.touches[0].clientX;
        currentY = 0;
        dragging = true;
      }, { passive: true });

      head.addEventListener("touchmove", (e) => {
        if (!dragging || !e.touches || !e.touches[0]) return;
        const dy = e.touches[0].clientY - startY;
        const dx = e.touches[0].clientX - startX;
        if (dy > 8 || Math.abs(dx) > 15) {
          currentY = Math.max(0, dy);
          const targets = page.querySelectorAll('#orig-subview-sheet-head-v161, [data-orig-sec="profile-form"], [data-orig-sec="addresses"]');
          targets.forEach(el => {
            el.style.transition = "none";
            el.style.transform = `translate3d(0, ${Math.min(currentY, 160)}px, 0)`;
            el.style.opacity = String(Math.max(0.35, 1 - currentY / 260));
          });
        }
      }, { passive: true });

      head.addEventListener("touchend", () => {
        if (!dragging) return;
        dragging = false;
        const targets = page.querySelectorAll('#orig-subview-sheet-head-v161, [data-orig-sec="profile-form"], [data-orig-sec="addresses"]');
        targets.forEach(el => {
          el.style.transition = "";
          el.style.transform = "";
          el.style.opacity = "";
        });
        if (currentY > 60) {
          closeSubViewSmoothly();
        }
      }, { passive: true });
    }
    return head;
  }

  function openSubViewSmoothly(mode) {
    const page = document.querySelector(".original-account-page");
    if (!page) return;
    currentSubMode = mode;

    const hub = document.getElementById("orig-acc-v161-root");
    if (hub) hub.classList.add("orig-hub-hiding");

    ensureSubSheetHeader(page);
    const titleEl = document.getElementById("orig-sheet-title-txt-v161");
    const subEl = document.getElementById("orig-sheet-sub-txt-v161");
    if (mode === "profile") {
      if (titleEl) titleEl.textContent = "إعدادات الحساب والبيانات الشخصية";
      if (subEl) subEl.textContent = "تعديل الاسم الكامل ورقم الجوال المعتمد للتوصيل";
      const editBtn = page.querySelector(".original-account-edit-btn");
      if (editBtn) editBtn.click();
    } else {
      if (titleEl) titleEl.textContent = "عناويني المحفوظة";
      if (subEl) subEl.textContent = "إدارة عناوين التوصيل أو إضافة عنوان جديد";
    }

    setTimeout(() => {
      normalizeFormsAndCards(page);
      page.classList.remove("orig-mode-hub", "orig-sub-profile", "orig-sub-addresses", "orig-anim-active", "orig-anim-exit");
      page.classList.add("orig-mode-sub", mode === "profile" ? "orig-sub-profile" : "orig-sub-addresses", "orig-anim-enter");
      if (hub) hub.classList.remove("orig-hub-hiding");

      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          normalizeFormsAndCards(page);
          page.classList.remove("orig-anim-enter");
          page.classList.add("orig-anim-active");
          window.scrollTo({ top: 0, behavior: "smooth" });
        });
      });
    }, 150);
  }

  function closeSubViewSmoothly() {
    const page = document.querySelector(".original-account-page");
    if (!page) return;
    page.classList.remove("orig-anim-active");
    page.classList.add("orig-anim-exit");

    setTimeout(() => {
      currentSubMode = null;
      page.classList.remove("orig-mode-sub", "orig-sub-profile", "orig-sub-addresses", "orig-anim-exit", "orig-anim-enter");
      page.classList.add("orig-mode-hub");
      refreshHubText();
      window.scrollTo({ top: 0, behavior: "smooth" });
    }, 240);
  }

  function refreshHubText() {
    const info = getCustomerInfo();
    const n1 = document.getElementById("orig-hub-name-v161");
    const p1 = document.getElementById("orig-hub-phone-v161");
    const n2 = document.getElementById("orig-row-name-v161");
    const p2 = document.getElementById("orig-row-phone-v161");
    if (n1) n1.textContent = info.name;
    if (p1) p1.textContent = info.phone;
    if (n2) n2.textContent = info.name;
    if (p2) p2.textContent = "رقم الجوال:  " + info.phone;
  }

  function ensureModals() {
    if (document.getElementById("orig-logout-modal-v161")) return;

    const logoutModal = document.createElement("div");
    logoutModal.id = "orig-logout-modal-v161";
    logoutModal.className = "orig-modal-backdrop-v161";
    logoutModal.innerHTML = `
      <div class="orig-modal-card-v161">
        <div class="orig-modal-emblem-v161">!</div>
        <h3 class="orig-modal-title-v161">تأكيد تسجيل الخروج</h3>
        <p class="orig-modal-desc-v161">هل أنت متأكد من رغبتك في تسجيل الخروج من حسابك في متجر أورجنال؟</p>
        <div class="orig-modal-actions-v161">
          <button type="button" class="orig-modal-btn-v161 confirm" id="orig-confirm-logout-v161">نعم، تسجيل الخروج</button>
          <button type="button" class="orig-modal-btn-v161 cancel" id="orig-cancel-logout-v161">إلغاء</button>
        </div>
      </div>
    `;
    document.body.appendChild(logoutModal);

    logoutModal.addEventListener("click", (e) => {
      if (e.target === logoutModal) logoutModal.classList.remove("open");
    });
    document.getElementById("orig-cancel-logout-v161").addEventListener("click", () => {
      logoutModal.classList.remove("open");
    });
    document.getElementById("orig-confirm-logout-v161").addEventListener("click", () => {
      try {
        const keysToKeep = [];
        for (let i = 0; i < localStorage.length; i++) {
          const k = localStorage.key(i);
          if (k && (k.includes("profile") || k.includes("customer") || k.includes("user") || k.includes("account") || k.includes("auth") || k.includes("phone"))) {
            keysToKeep.push(k);
          }
        }
        keysToKeep.forEach(k => localStorage.removeItem(k));
        sessionStorage.clear();
      } catch (_) {}
      logoutModal.classList.remove("open");
      window.location.href = "/";
    });

    const aboutModal = document.createElement("div");
    aboutModal.id = "orig-about-modal-v161";
    aboutModal.className = "orig-modal-backdrop-v161";
    aboutModal.innerHTML = `
      <div class="orig-modal-card-v161">
        <div class="orig-modal-emblem-v161">O</div>
        <h3 class="orig-modal-title-v161">ORIGINAL – أورجنال</h3>
        <p class="orig-modal-desc-v161">
          متجرك المفضل لتوصيل كافة مقاضي البيت والمواد الغذائية الطازجة في صنعاء بسرعة وعناية فائقة.<br>
          <strong style="color:#13462f;display:inline-block;margin-top:6px;">الإصدار الرسمي • خدمة عملاء: 779542219</strong>
        </p>
        <div class="orig-modal-actions-v161">
          <button type="button" class="orig-modal-btn-v161 primary" id="orig-close-about-v161">إغلاق</button>
        </div>
      </div>
    `;
    document.body.appendChild(aboutModal);

    aboutModal.addEventListener("click", (e) => {
      if (e.target === aboutModal) aboutModal.classList.remove("open");
    });
    document.getElementById("orig-close-about-v161").addEventListener("click", () => {
      aboutModal.classList.remove("open");
    });
  }

  function openNotificationsDrawer() {
    const bell = document.querySelector("#orig-top-bell-btn, header .header-actions button, header .header-actions a");
    if (bell && typeof bell.click === "function" && bell.id === "orig-top-bell-btn") {
      bell.click();
      return;
    }
    const allBtns = Array.from(document.querySelectorAll("header button, header a"));
    const notifBtn = allBtns.find(b => (b.innerHTML || "").includes("M18 8A6 6 0 0 0 6 8") || (b.getAttribute("aria-label") || "").includes("إشعار"));
    if (notifBtn) {
      notifBtn.click();
      return;
    }
    window.location.href = "/orders";
  }

  function mountAccountHub() {
    const isAccount = window.location.pathname.includes("/account");
    document.body.classList.toggle("orig-on-account-page", isAccount);

    const page = document.querySelector(".original-account-page");
    if (!page) return;

    ensureModals();
    ensureSubSheetHeader(page);
    normalizeFormsAndCards(page);

    if (!currentSubMode && !page.classList.contains("orig-mode-sub")) {
      page.classList.add("orig-mode-hub");
    }

    if (document.getElementById("orig-acc-v161-root")) {
      refreshHubText();
      return;
    }

    const info = getCustomerInfo();
    const root = document.createElement("div");
    root.id = "orig-acc-v161-root";
    root.innerHTML = `
      <!-- البطاقة الترحيبية العلوية -->
      <div class="orig-hero-banner-v161">
        <div class="orig-hero-info-v161">
          <p class="orig-hero-welcome-v161">أهلاً بك</p>
          <h2 class="orig-hero-name-v161" id="orig-hub-name-v161">${info.name}</h2>
          <div class="orig-hero-phone-v161">
            <svg viewBox="0 0 24 24"><path d="M6.62 10.79a15.05 15.05 0 006.59 6.59l2.2-2.2a1 1 0 011.01-.24c1.12.37 2.33.57 3.58.57a1 1 0 011 1V20a1 1 0 01-1 1C10.61 21 3 13.39 3 4a1 1 0 011-1h3.5a1 1 0 011 1c0 1.25.2 2.46.57 3.58a1 1 0 01-.25 1.01l-2.2 2.2z"/></svg>
            <span id="orig-hub-phone-v161">${info.phone}</span>
          </div>
        </div>
        <div class="orig-hero-avatar-v161">
          <svg viewBox="0 0 24 24"><path d="M12 12c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm0 2.5c-3.34 0-10 1.67-10 5v2.5h20v-2.5c0-3.33-6.66-5-10-5z"/></svg>
        </div>
        <svg class="orig-hero-watermark-v161" viewBox="0 0 100 100" fill="none">
          <path d="M10 90 C10 40, 50 10, 90 10 C90 50, 60 90, 10 90 Z" fill="#d8b454"/>
          <path d="M25 75 C25 45, 55 25, 85 25" stroke="#ffffff" stroke-width="3"/>
        </svg>
      </div>

      <!-- الأزرار الـ 4 السريعة -->
      <div class="orig-quick-grid-v161">
        <button type="button" class="orig-quick-card-v161" data-act="notifications">
          <svg viewBox="0 0 24 24" fill="#13462f"><path d="M12 22c1.1 0 2-.9 2-2h-4a2 2 0 002 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z"/></svg>
          <span class="orig-quick-label-v161">إشعاراتي</span>
        </button>
        <button type="button" class="orig-quick-card-v161" data-act="orders">
          <svg viewBox="0 0 24 24" fill="none" stroke="#13462f" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>
          <span class="orig-quick-label-v161">طلباتي</span>
        </button>
        <button type="button" class="orig-quick-card-v161" data-act="favorites">
          <svg viewBox="0 0 24 24" fill="#13462f"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>
          <span class="orig-quick-label-v161">المفضلة</span>
        </button>
        <button type="button" class="orig-quick-card-v161" data-act="addresses">
          <svg viewBox="0 0 24 24" fill="#13462f"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5a2.5 2.5 0 010-5 2.5 2.5 0 010 5z"/></svg>
          <span class="orig-quick-label-v161">عناويني</span>
        </button>
      </div>

      <!-- صفوف القائمة الـ 5 -->
      <div class="orig-menu-stack-v161">
        <div class="orig-menu-item-v161" data-act="notifications">
          <div class="orig-menu-right-v161">
            <div class="orig-menu-icon-v161">
              <svg viewBox="0 0 24 24" fill="#13462f"><path d="M12 22c1.1 0 2-.9 2-2h-4a2 2 0 002 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z"/></svg>
            </div>
            <div class="orig-menu-text-v161">
              <span class="orig-menu-title-v161">إشعارات الطلبات والعروض</span>
            </div>
          </div>
          <svg class="orig-menu-arrow-v161" viewBox="0 0 24 24" fill="none" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
        </div>

        <div class="orig-menu-item-v161" data-act="profile">
          <div class="orig-menu-right-v161">
            <div class="orig-menu-icon-v161">
              <svg viewBox="0 0 24 24" fill="#13462f"><path d="M12 12c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm0 2.5c-3.34 0-10 1.67-10 5v2.5h20v-2.5c0-3.33-6.66-5-10-5z"/></svg>
            </div>
            <div class="orig-menu-text-v161">
              <span class="orig-menu-title-v161" id="orig-row-name-v161">${info.name}</span>
              <span class="orig-menu-sub-v161" id="orig-row-phone-v161">رقم الجوال:  ${info.phone}</span>
            </div>
          </div>
          <svg class="orig-menu-arrow-v161" viewBox="0 0 24 24" fill="none" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
        </div>

        <div class="orig-menu-item-v161" data-act="profile">
          <div class="orig-menu-right-v161">
            <div class="orig-menu-icon-v161">
              <svg viewBox="0 0 24 24" fill="#13462f"><path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58a.49.49 0 00.12-.61l-1.92-3.32a.488.488 0 00-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54a.484.484 0 00-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58a.49.49 0 00-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/></svg>
            </div>
            <div class="orig-menu-text-v161">
              <span class="orig-menu-title-v161">إعدادات الحساب</span>
            </div>
          </div>
          <svg class="orig-menu-arrow-v161" viewBox="0 0 24 24" fill="none" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
        </div>

        <div class="orig-menu-item-v161" data-act="support">
          <div class="orig-menu-right-v161">
            <div class="orig-menu-icon-v161">
              <svg viewBox="0 0 24 24" fill="#13462f"><path d="M12 1a9 9 0 00-9 9v7c0 1.66 1.34 3 3 3h3v-8H5v-2c0-3.87 3.13-7 7-7s7 3.13 7 7v2h-4v8h4v1h-7v2h6c1.66 0 3-1.34 3-3V10a9 9 0 00-9-9z"/></svg>
            </div>
            <div class="orig-menu-text-v161">
              <span class="orig-menu-title-v161">التواصل مع خدمة العملاء</span>
            </div>
          </div>
          <svg class="orig-menu-arrow-v161" viewBox="0 0 24 24" fill="none" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
        </div>

        <div class="orig-menu-item-v161" data-act="about">
          <div class="orig-menu-right-v161">
            <div class="orig-menu-icon-v161">
              <svg viewBox="0 0 24 24" fill="#13462f"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>
            </div>
            <div class="orig-menu-text-v161">
              <span class="orig-menu-title-v161">معلومات التطبيق</span>
            </div>
          </div>
          <svg class="orig-menu-arrow-v161" viewBox="0 0 24 24" fill="none" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
        </div>
      </div>

      <!-- زر تسجيل الخروج -->
      <button type="button" class="orig-logout-btn-v161" data-act="logout">
        <svg viewBox="0 0 24 24" fill="none" stroke="#13462f" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
          <polyline points="16 17 21 12 16 7"/>
          <line x1="21" y1="12" x2="9" y2="12"/>
        </svg>
        <span>تسجيل الخروج</span>
      </button>
    `;

    page.prepend(root);

    root.querySelectorAll("[data-act]").forEach(el => {
      el.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        const act = el.getAttribute("data-act");
        if (act === "orders") {
          window.location.href = "/orders";
        } else if (act === "favorites") {
          window.location.href = "/favorites";
        } else if (act === "notifications") {
          openNotificationsDrawer();
        } else if (act === "profile") {
          openSubViewSmoothly("profile");
        } else if (act === "addresses") {
          openSubViewSmoothly("addresses");
        } else if (act === "support") {
          window.open("https://wa.me/967779542219", "_blank");
        } else if (act === "about") {
          const m = document.getElementById("orig-about-modal-v161");
          if (m) m.classList.add("open");
        } else if (act === "logout") {
          const m = document.getElementById("orig-logout-modal-v161");
          if (m) m.classList.add("open");
        }
      });
    });
  }

  const obs = new MutationObserver(() => {
    mountAccountHub();
  });
  obs.observe(document.documentElement, { childList: true, subtree: true });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mountAccountHub);
  } else {
    mountAccountHub();
  }
})();
</script>
<!-- ORIGINAL ACCOUNT PERFECT V161 END -->"""

if "</body>" in html:
    html = html.replace("</body>", block_v161 + "\n</body>", 1)
else:
    html += "\n" + block_v161

with open(index_path, "w", encoding="utf-8") as f:
    f.write(html)

subprocess.run(["git", "add", "client/index.html"], check=True)
subprocess.run(["git", "commit", "-m", "Fix v161: smooth slide subviews for account settings & addresses, 1-column balanced inputs, and compact 20px default checkbox"], check=False)
subprocess.run(["git", "push", "origin", "main"], check=True)
print("\n✅ تم تطبيق ورفع التحديث v161 بنجاح إلى Render!")
