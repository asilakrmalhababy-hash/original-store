import os, sys, pathlib

print("=" * 72)
print("✨ توحيد مقاس أزرار الهيدر (38x38px) + تنعيم شريط البحث (v156)")
print("=" * 72)

html_path = pathlib.Path("client/index.html")
if not html_path.exists():
    print("❌ لم يتم العثور على client/index.html")
    sys.exit(1)

html = html_path.read_text(encoding="utf-8")

s_m = "<!-- ORIGINAL_CLEAN_HEADER_V155_START -->"
e_m = "<!-- ORIGINAL_CLEAN_HEADER_V155_END -->"
while s_m in html and e_m in html:
    html = html[:html.index(s_m)] + html[html.index(e_m) + len(e_m):]

v156_header_block = r"""<!-- ORIGINAL_CLEAN_HEADER_V155_START -->
<style>
  header.store-header,
  header {
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
    background: rgba(248, 247, 242, 0.97) !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
    border-bottom: 1.5px solid rgba(216, 180, 84, 0.28) !important;
    padding: 8px 12px 10px 12px !important;
    box-sizing: border-box !important;
  }

  header .header-main {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: wrap !important;
    align-items: center !important;
    justify-content: space-between !important;
    gap: 8px !important;
    width: 100% !important;
    box-sizing: border-box !important;
  }

  header .brand-lockup {
    order: 1 !important;
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
    flex: 0 0 auto !important;
  }

  header .header-actions {
    order: 2 !important;
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    align-items: center !important;
    justify-content: flex-end !important;
    gap: 8px !important;
    flex: 0 0 auto !important;
    margin: 0 !important;
  }

  /* إبقاء 3 أيقونات فقط: الإشعارات، طلباتي، السلة */
  header .header-actions a[href="/account"],
  header .header-actions a[href*="account"],
  header .header-actions a[href="/favorites"],
  header .header-actions a[href*="favorites"],
  header .header-actions button[aria-label*="حسابي"],
  header .header-actions button[aria-label*="المفضلة"] {
    display: none !important;
  }

  /* توحيد حجم الأيقونات الثلاث بنفس حجم زر طلباتي (38x38px) */
  header .header-actions > a,
  header .header-actions > button,
  header .header-actions #orig-header-bell-v141 {
    width: 38px !important;
    height: 38px !important;
    min-width: 38px !important;
    min-height: 38px !important;
    max-width: 38px !important;
    max-height: 38px !important;
    border-radius: 12px !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    border: 1.5px solid #d8b454 !important;
    box-shadow: 0 3px 10px rgba(19, 70, 47, 0.1) !important;
    padding: 0 !important;
    margin: 0 !important;
    position: relative !important;
    box-sizing: border-box !important;
  }

  header .header-actions > a svg,
  header .header-actions > button svg,
  header .header-actions #orig-header-bell-v141 svg {
    width: 19px !important;
    height: 19px !important;
  }

  header .header-actions a[href="/orders"],
  header .header-actions a[href*="orders"],
  header .header-actions button[aria-label*="طلب"] {
    background: #ffffff !important;
    color: #13462f !important;
  }
  header .header-actions a[href="/cart"],
  header .header-actions a[href*="cart"],
  header .header-actions button[aria-label*="سلة"] {
    background: linear-gradient(135deg, #165237 0%, #0b2b1d 100%) !important;
    color: #e7c972 !important;
  }
  header .header-actions #orig-header-bell-v141 {
    background: #ffffff !important;
    color: #13462f !important;
  }
  header .header-actions #orig-header-bell-v141 svg {
    stroke: #13462f !important;
  }

  /* شريط البحث المنسق بدون إطار مزدوج */
  header .header-search {
    order: 3 !important;
    flex: 1 0 100% !important;
    width: 100% !important;
    margin: 0 !important;
    background: #ffffff !important;
    border: 1.5px solid rgba(216, 180, 84, 0.45) !important;
    border-radius: 14px !important;
    box-shadow: 0 2px 10px rgba(19, 70, 47, 0.05) !important;
    overflow: hidden !important;
  }
  header .header-search input {
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
    height: 38px !important;
    outline: none !important;
  }
</style>
<!-- ORIGINAL_CLEAN_HEADER_V155_END -->"""

if "</body>" in html:
    html = html.replace("</body>", v156_header_block + "\n</body>", 1)
else:
    html = html + "\n" + v156_header_block

html_path.write_text(html, encoding="utf-8")
print("✅ تم توحيد مقاس الأيقونات الثلاث (38x38px) وإزالة الإطار المزدوج في شريط البحث!")

os.system("git add client/index.html && git commit -m 'Polish v156: unify top header 3 icons to 38x38px and clean single-border search bar' && git push origin main")
print("🚀 تم رفع التحديث v156 إلى Render!")
