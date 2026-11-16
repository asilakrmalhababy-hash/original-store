import os, re, sys, pathlib

print("=" * 72)
print("👑 إصلاح الهيدر العلوي على فرع main: 3 أيقونات كبيرة (44x44) + شريط بحث منسق (v155)")
print("=" * 72)

html_path = pathlib.Path("client/index.html")
if not html_path.exists():
    print("❌ لم يتم العثور على client/index.html")
    sys.exit(1)

html = html_path.read_text(encoding="utf-8")

# 1. إزالة قاعدة display: block المخرّبة للهيدر من V153
html = re.sub(
    r"header\s*,\s*header\s*>\s*div\s*\{[^}]*display\s*:\s*block\s*!important\s*;[^}]*\}",
    "/* v155: removed broken block override on header */",
    html
)

# 2. إيقاف حقن بطاقة حسابي القديمة المكررة لتعمل واجهة حسابي الجديدة بسلاسة
html = re.sub(
    r"injectVipAccountViewV140\(\)\s*;",
    "/* v155: disabled legacy VIP injection */",
    html
)

# 3. إزالة أي نسخة سابقة لـ V155
s_m = "<!-- ORIGINAL_CLEAN_HEADER_V155_START -->"
e_m = "<!-- ORIGINAL_CLEAN_HEADER_V155_END -->"
while s_m in html and e_m in html:
    html = html[:html.index(s_m)] + html[html.index(e_m) + len(e_m):]

v155_header_block = r"""<!-- ORIGINAL_CLEAN_HEADER_V155_START -->
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
    gap: 10px !important;
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

  /* إخفاء أيقونتي حسابي والمفضلة من الهيدر العلوي فقط وإبقاء 3 أيقونات: الإشعارات، طلباتي، السلة */
  header .header-actions a[href="/account"],
  header .header-actions a[href*="account"],
  header .header-actions a[href="/favorites"],
  header .header-actions a[href*="favorites"],
  header .header-actions button[aria-label*="حسابي"],
  header .header-actions button[aria-label*="المفضلة"] {
    display: none !important;
  }

  header .header-actions > a,
  header .header-actions > button,
  header .header-actions #orig-header-bell-v141 {
    width: 44px !important;
    height: 44px !important;
    min-width: 44px !important;
    min-height: 44px !important;
    max-width: 44px !important;
    max-height: 44px !important;
    border-radius: 14px !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    border: 1.5px solid #d8b454 !important;
    box-shadow: 0 4px 12px rgba(19, 70, 47, 0.12) !important;
    padding: 0 !important;
    margin: 0 !important;
    position: relative !important;
    box-sizing: border-box !important;
  }

  header .header-actions > a svg,
  header .header-actions > button svg,
  header .header-actions #orig-header-bell-v141 svg {
    width: 21px !important;
    height: 21px !important;
  }

  header .header-actions a[href="/orders"],
  header .header-actions a[href*="orders"] {
    background: #ffffff !important;
    color: #13462f !important;
  }
  header .header-actions a[href="/cart"],
  header .header-actions a[href*="cart"] {
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

  header .header-search {
    order: 3 !important;
    flex: 1 0 100% !important;
    width: 100% !important;
    margin: 0 !important;
  }
  header .header-search input {
    width: 100% !important;
    height: 40px !important;
    border-radius: 14px !important;
    border: 1.5px solid rgba(216, 180, 84, 0.45) !important;
    background: #ffffff !important;
    box-shadow: 0 2px 10px rgba(19, 70, 47, 0.05) !important;
  }
</style>
<!-- ORIGINAL_CLEAN_HEADER_V155_END -->"""

if "</body>" in html:
    html = html.replace("</body>", v155_header_block + "\n</body>", 1)
else:
    html = html + "\n" + v155_header_block

html_path.write_text(html, encoding="utf-8")
print("✅ تم ضبط الهيدر العلوي بـ 3 أيقونات كبيرة (44x44px) وشريط بحث منسق!")

os.system("git add client/index.html && git commit -m 'Fix v155: clean top header on main with 3 larger icons (Notifications, Orders, Cart) & full-width search bar' && git push origin main")
print("🚀 تم رفع التحديث v155 إلى فرع main على Render!")
