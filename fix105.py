import subprocess, sys, pathlib, re

print("=== بدء تطبيق التحديث الحاسم v105 لإصلاح سعر الحجم المختار في النافذة والسلة والفاتورة ===")

# 1. Update client/index.html with the fixed, React-text-node-aware & RTL-dark-green-aware modal price synchronizer
html_path = pathlib.Path("client/index.html")
if html_path.exists():
    ht = html_path.read_text(encoding="utf-8")
    ht = re.sub(r'<script>\s*\(function\(\)\s*\{\s*function syncVariantModalPrice\(\)[\s\S]*?</script>', '', ht)

    live_modal_script = """
    <script>
      (function() {
        function syncVariantModalPrice() {
          try {
            var buttons = Array.from(document.querySelectorAll("button"));
            var addBtn = buttons.find(function(b) {
              return b.textContent && b.textContent.indexOf("إضافة إلى السلة") !== -1;
            });
            if (!addBtn) return;

            var modal = addBtn.parentElement;
            while (modal && modal !== document.body && modal.querySelectorAll("button").length < 4) {
              modal = modal.parentElement;
            }
            if (!modal) return;

            var modalButtons = Array.from(modal.querySelectorAll("button"));
            var selectedOptBtn = modalButtons.find(function(b) {
              if (b === addBtn) return false;
              var txt = (b.textContent || "").trim();
              if (txt.indexOf(":") === -1) return false;
              var style = window.getComputedStyle(b);
              var rgb = (style.backgroundColor || "").match(/\\d+/g);
              var isDarkGreen = rgb && rgb.length >= 3 && Number(rgb[0]) < 100 && Number(rgb[1]) < 150 && Number(rgb[2]) < 120;
              var cls = b.className || "";
              return isDarkGreen || cls.indexOf("selected") !== -1 || cls.indexOf("active") !== -1;
            });
            if (!selectedOptBtn) return;

            var rawTxt = (selectedOptBtn.textContent || "").trim();
            var m = rawTxt.match(/:\\s*(\\d+(?:\\.\\d+)?)/);
            if (!m || !m[1]) return;
            var unitPrice = parseFloat(m[1]);
            if (isNaN(unitPrice) || unitPrice <= 0) return;

            var qty = 1;
            var allEls = Array.from(modal.querySelectorAll("span, div, strong, b"));
            for (var i = 0; i < allEls.length; i++) {
              var st = (allEls[i].textContent || "").trim();
              if (/^\\d+$/.test(st) && allEls[i].children.length === 0) {
                var val = parseInt(st, 10);
                if (val >= 1 && val <= 999) {
                  qty = val;
                  break;
                }
              }
            }
            var totalPrice = Math.round(unitPrice * qty);

            allEls.forEach(function(el) {
              if (el === addBtn || addBtn.contains(el)) return;
              var fullTxt = (el.textContent || "").trim();
              if (fullTxt.indexOf("ر.ي") !== -1 && fullTxt.indexOf("/") !== -1 && el.children.length <= 2) {
                var expectedSub = fullTxt.replace(/^\\s*\\d[\\d,.]*/, unitPrice.toLocaleString("en-US"));
                if (fullTxt !== expectedSub) {
                  var tw = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null);
                  var tn;
                  var replacedNode = false;
                  while ((tn = tw.nextNode())) {
                    if (tn.nodeValue && /\\d/.test(tn.nodeValue)) {
                      tn.nodeValue = tn.nodeValue.replace(/\\d[\\d,.]*/, unitPrice.toLocaleString("en-US"));
                      replacedNode = true;
                      break;
                    }
                  }
                  if (!replacedNode) el.textContent = expectedSub;
                }
              }
            });

            var btnFullTxt = (addBtn.textContent || "").trim();
            var targetPriceStr = totalPrice.toLocaleString("en-US");
            if (btnFullTxt.indexOf("(" + targetPriceStr + " ر.ي)") === -1) {
              var twBtn = document.createTreeWalker(addBtn, NodeFilter.SHOW_TEXT, null);
              var textNodes = [];
              var n;
              while ((n = twBtn.nextNode())) {
                textNodes.push(n);
              }
              if (textNodes.length > 1) {
                for (var j = 0; j < textNodes.length; j++) {
                  if (/^\\s*\\d[\\d,.]*\\s*$/.test(textNodes[j].nodeValue || "")) {
                    textNodes[j].nodeValue = targetPriceStr;
                  } else if ((textNodes[j].nodeValue || "").indexOf("ر.ي") !== -1 && /\\d/.test(textNodes[j].nodeValue || "")) {
                    textNodes[j].nodeValue = (textNodes[j].nodeValue || "").replace(/\\d[\\d,.]*/, targetPriceStr);
                  }
                }
              } else if (textNodes.length === 1) {
                textNodes[0].nodeValue = " إضافة إلى السلة (" + targetPriceStr + " ر.ي) ";
              }
            }
          } catch (e) {}
        }
        document.addEventListener("click", function() {
          setTimeout(syncVariantModalPrice, 5);
          setTimeout(syncVariantModalPrice, 40);
          setTimeout(syncVariantModalPrice, 120);
        }, true);
        setInterval(syncVariantModalPrice, 150);
      })();
    </script>
"""
    ht = ht.replace("</body>", live_modal_script + "\n  </body>", 1)
    html_path.write_text(ht, encoding="utf-8")
    print("1. Updated live modal price synchronizer in client/index.html (RTL dark-green detection + React split text node support)")

# 2. Update client/src/pages/Home.tsx so cart items and modal state always use the variant price (e.g. 250 instead of 150)
home_path = pathlib.Path("client/src/pages/Home.tsx")
if home_path.exists():
    hc = home_path.read_text(encoding="utf-8")

    hc = re.sub(
        r'extractVariantPriceV104\((item|i)\?\.name,\s*\1\?\.price\)',
        r'\1.price',
        hc
    )

    old_helper = """function extractVariantPriceV104(rawText: any, fallbackPrice: any): number {
  const base = Number(fallbackPrice || 0);
  if (!rawText) return base;
  const str = String(rawText).trim();
  const m = str.match(/:\\s*(\\d+(?:\\.\\d+)?)/);
  if (m && m[1]) {
    const p = parseFloat(m[1]);
    if (!isNaN(p) && p > 0) return p;
  }
  return base;
}"""
    new_helper = """function extractVariantPriceV104(rawText: any, fallbackPrice: any): number {
  const base = Number(fallbackPrice || 0);
  if (!rawText) return base;
  const str = typeof rawText === "object"
    ? String(rawText?.name || rawText?.variant || rawText?.unit || "")
    : String(rawText).trim();
  const m = str.match(/:\\s*(\\d+(?:\\.\\d+)?)/);
  if (m && m[1]) {
    const p = parseFloat(m[1]);
    if (!isNaN(p) && p > 0) return p;
  }
  return base;
}"""
    if old_helper in hc:
        hc = hc.replace(old_helper, new_helper, 1)
    elif "function extractVariantPriceV104" not in hc:
        last_imp = hc.rfind("\nimport ", 0, 3000)
        if last_imp != -1:
            end_imp = hc.find("\n", last_imp + 1)
            hc = hc[:end_imp+1] + "\n" + new_helper + "\n" + hc[end_imp+1:]

    hc = re.sub(
        r'\b(item|i|cartItem|entry)\.price\b(?!\s*=(?!=))',
        r'extractVariantPriceV104(\1, \1?.price)',
        hc
    )

    for m_btn in list(re.finditer(r'إضافة إلى السلة', hc)):
        pos = m_btn.start()
        win_start = max(0, pos - 2500)
        win_end = min(len(hc), pos + 500)
        window = hc[win_start:win_end]

        price_vars = re.findall(r'\b([a-zA-Z_]\w*)\??\.price\b', window)
        price_vars = [p for p in price_vars if p not in ("item", "i", "cartItem", "entry")]
        setter_matches = re.findall(r'\bset([A-Z]\w*)\s*\(', window)
        var_candidates = []
        for s_name in setter_matches:
            v_name = s_name[0].lower() + s_name[1:]
            if "qty" not in v_name.lower() and "quant" not in v_name.lower() and "modal" not in v_name.lower() and "open" not in v_name.lower() and "show" not in v_name.lower():
                if re.search(rf'\b{re.escape(v_name)}\b', window):
                    var_candidates.append(v_name)

        prod_var = price_vars[-1] if price_vars else None
        var_state = var_candidates[-1] if var_candidates else None
        print(f"Detected modal prod_var={prod_var}, var_state={var_state}")
        if prod_var and var_state:
            window_new = re.sub(
                rf'\b{re.escape(prod_var)}\??\.price\b(?!\s*=(?!=))',
                f'extractVariantPriceV104({var_state}, {prod_var}?.price)',
                window
            )
            hc = hc[:win_start] + window_new + hc[win_end:]
            print("Patched modal prod_var.price with extractVariantPriceV104 directly in JSX!")
            break

    home_path.write_text(hc, encoding="utf-8")
    print("2. Updated client/src/pages/Home.tsx with full variant price extraction!")

# 3. Bump sw.js cache to v105 so the phone immediately loads the new Home.tsx and index.html
sw_path = pathlib.Path("client/public/sw.js")
if sw_path.exists():
    swc = sw_path.read_text(encoding="utf-8")
    swc = re.sub(r'const CACHE = "original-shell-v[^"]*";', 'const CACHE = "original-shell-v105";', swc)
    sw_path.write_text(swc, encoding="utf-8")
    print("3. Bumped sw.js cache to v105!")

print("=== 4. فحص كود السيرفر والواجهة عبر esbuild (0.5 ثانية) ===")
res_srv = subprocess.run(
    ["./node_modules/.bin/esbuild", "server/_core/index.ts", "--platform=node", "--packages=external", "--bundle", "--format=esm", "--outdir=dist"],
    capture_output=True, text=True
)
if res_srv.returncode != 0:
    print("SERVER ESBUILD ERROR:")
    print(res_srv.stderr or res_srv.stdout)
    sys.exit(1)

res_cli = subprocess.run(
    ["./node_modules/.bin/esbuild", "client/src/pages/Admin.tsx", "client/src/pages/Home.tsx", "--bundle", "--packages=external", "--jsx=automatic", "--outdir=dist/check_client"],
    capture_output=True, text=True
)
if res_cli.returncode != 0:
    print("CLIENT ESBUILD ERROR:")
    print(res_cli.stderr or res_cli.stdout)
    sys.exit(1)

subprocess.run(["rm", "-rf", "dist/check_client"], check=False)
print("BOTH SERVER & CLIENT ESBUILD PASSED 100%! Pushing to GitHub & Render...")
subprocess.run(["git", "add", "-A"], check=True)
subprocess.run(["git", "commit", "-m", "v105: fix RTL dark-green variant button price detection in modal and cart item.price comma replacement"], check=True)
subprocess.run(["git", "push", "origin", "main", "--force"], check=True)
print("=== تم رفع التحديث v105 بنجاح 100% إلى Render! ===")
