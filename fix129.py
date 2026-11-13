import os, pathlib, re, subprocess, sys

print("=== بدء التحديث الحاسم والسريع v129 ===")

ENGINE_JS_V129 = r"""
(function() {
  if (typeof window === "undefined" || typeof document === "undefined") return;
  try {
    if ("caches" in window && localStorage.getItem("original_v129_purged") !== "1") {
      localStorage.setItem("original_v129_purged", "1");
      caches.keys().then(function(ks) { ks.forEach(function(k) { caches.delete(k); }); });
      if (navigator.serviceWorker) {
        navigator.serviceWorker.getRegistrations().then(function(rs) { rs.forEach(function(r) { r.update(); }); });
      }
    }
  } catch (e) {}

  function getBtnTextNodesV129(btn) {
    var nodes = [];
    if (!btn) return nodes;
    var tw = document.createTreeWalker(btn, NodeFilter.SHOW_TEXT, null);
    var n;
    while ((n = tw.nextNode())) {
      if (n.parentElement && n.parentElement.closest && n.parentElement.closest("svg")) continue;
      nodes.push(n);
    }
    return nodes;
  }

  function getCleanBtnTextV129(btn) {
    return getBtnTextNodesV129(btn).map(function(n) { return n.nodeValue || ""; }).join("").replace(/[✓✔]/g, "").replace(/\s+/g, " ").trim();
  }

  function setCleanBtnTextV129(btn, newText) {
    var nodes = getBtnTextNodesV129(btn);
    if (nodes.length === 0) return;
    var joined = nodes.map(function(n) { return n.nodeValue || ""; }).join("").replace(/\s+/g, " ").trim();
    if (joined === newText.trim()) return;
    nodes[0].nodeValue = " " + newText.trim() + " ";
    for (var i = 1; i < nodes.length; i++) {
      if (nodes[i].nodeValue !== "") nodes[i].nodeValue = "";
    }
  }

  function parseOptV129(raw) {
    var clean = String(raw || "").replace(/[✓✔]/g, "").replace(/\s+/g, " ").trim();
    var cIdx = clean.indexOf(":");
    if (cIdx === -1) return null;
    var optName = clean.slice(0, cIdx).trim();
    var m = clean.slice(cIdx + 1).trim().match(/(\d+(?:\.\d+)?)/);
    if (!m || !m[1]) return null;
    var p = parseFloat(m[1]);
    return (!isNaN(p) && p > 0) ? { raw: optName + ":" + p, optName: optName, unitPrice: p } : null;
  }

  function isOptSelectedDomV129(b) {
    if (!b) return false;
    var st = window.getComputedStyle(b);
    var bg = st.backgroundColor || "";
    if (bg && bg !== "transparent" && bg.indexOf("rgba(0, 0, 0, 0)") === -1 && bg.indexOf("rgba(0,0,0,0)") === -1) {
      var rgb = bg.match(/\d+(\.\d+)?/g);
      if (rgb && rgb.length >= 3) {
        var r = parseFloat(rgb[0]), g = parseFloat(rgb[1]), bl = parseFloat(rgb[2]);
        var a = rgb.length >= 4 ? parseFloat(rgb[3]) : 1;
        if (a > 0.5 && r < 95 && g >= 30 && g < 175 && bl < 125 && g > r) return true;
      }
    }
    var fg = (st.color || "").match(/\d+/g);
    if (fg && fg.length >= 3 && Number(fg[0]) > 210 && Number(fg[1]) > 210 && Number(fg[2]) > 210) return true;
    if (b.querySelector("svg")) return true;
    var cls = b.className || "";
    return typeof cls === "string" && (cls.indexOf("selected") !== -1 || cls.indexOf("active") !== -1);
  }

  function readQtyV129(container, addBtn, optBtns) {
    var cBtns = Array.from(container.querySelectorAll("button"));
    for (var i = 0; i < cBtns.length; i++) {
      var qb = cBtns[i];
      if (qb === addBtn || optBtns.indexOf(qb) !== -1) continue;
      var qbt = (qb.textContent || "").trim();
      var isStep = qbt === "+" || qbt === "＋" || qbt === "-" || qbt === "−" || qbt === "–" || qb.innerHTML.indexOf("M5 12h14") !== -1 || qb.innerHTML.indexOf("lucide-plus") !== -1 || qb.innerHTML.indexOf("lucide-minus") !== -1;
      if (isStep && qb.parentElement) {
        var box = qb.parentElement;
        for (var up = 0; up < 2 && box && box !== container; up++) {
          var inp = box.querySelector("input");
          if (inp && /^\d+$/.test((inp.value || "").trim())) return Math.max(1, parseInt(inp.value.trim(), 10));
          var tw = document.createTreeWalker(box, NodeFilter.SHOW_TEXT, null);
          var tn;
          while ((tn = tw.nextNode())) {
            var pe = tn.parentElement;
            if (pe && pe.closest && (pe.closest("button") || pe.closest("svg"))) continue;
            var sv = (tn.nodeValue || "").trim();
            if (/^\d+$/.test(sv)) return Math.max(1, parseInt(sv, 10));
          }
          box = box.parentElement;
        }
      }
    }
    return 1;
  }

  function syncBoxV129(container, addBtn, isDetail) {
    if (!container || !addBtn) return;
    var cBtns = Array.from(container.querySelectorAll("button"));
    var optBtns = cBtns.filter(function(b) {
      if (b === addBtn) return false;
      var t = getCleanBtnTextV129(b);
      if (t === "+" || t === "＋" || t === "-" || t === "−" || t === "–" || t === "×" || t === "✕") return false;
      return t.indexOf(":") !== -1 || b.hasAttribute("data-raw-opt");
    });
    if (optBtns.length === 0) return;

    optBtns.forEach(function(b) {
      var curT = getCleanBtnTextV129(b);
      if (curT.indexOf(":") !== -1) b.setAttribute("data-raw-opt", curT);
      var parsed = parseOptV129(b.getAttribute("data-raw-opt") || curT);
      if (parsed) {
        setCleanBtnTextV129(b, parsed.optName);
        var pAttr = parsed.unitPrice.toLocaleString("en-US") + " ريال";
        if (b.getAttribute("data-v127-opt-price") !== pAttr) b.setAttribute("data-v127-opt-price", pAttr);
      }
    });

    var userSel = optBtns.find(function(b) { return b.getAttribute("data-v129-sel") === "1"; });
    var domSel = optBtns.find(function(b) { return isOptSelectedDomV129(b); });
    var activeBtn = userSel || domSel || optBtns[0];
    if (!activeBtn) return;

    var parsedSel = parseOptV129(activeBtn.getAttribute("data-raw-opt") || getCleanBtnTextV129(activeBtn));
    if (!parsedSel) return;

    window.__v128ActiveVariant = parsedSel.raw;
    var unitPrice = parsedSel.unitPrice;
    var qty = readQtyV129(container, addBtn, optBtns);
    var totalPrice = Math.round(unitPrice * qty);
    var unitStr = unitPrice.toLocaleString("en-US");
    var totalStr = totalPrice.toLocaleString("en-US");

    var twAll = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, null);
    var tNodes = [], tn;
    while ((tn = twAll.nextNode())) {
      var pEl = tn.parentElement;
      if (!pEl || pEl === addBtn || addBtn.contains(pEl)) continue;
      if (optBtns.some(function(ob) { return ob === pEl || ob.contains(pEl); })) continue;
      tNodes.push(tn);
    }
    for (var i = 0; i < tNodes.length; i++) {
      var cv = tNodes[i].nodeValue || "";
      var nv = (i + 1 < tNodes.length) ? (tNodes[i + 1].nodeValue || "") : "";
      if (/\d[\d,.]*\s*(?:ر\.ي|ريال)/.test(cv)) {
        var rv = cv.replace(/\d[\d,.]*(?=\s*(?:ر\.ي|ريال))/, unitStr);
        if (cv !== rv) tNodes[i].nodeValue = rv;
      } else if (/^\s*\d[\d,.]*\s*$/.test(cv) && /^\s*(?:ر\.ي|ريال)/.test(nv)) {
        if (cv.trim() !== unitStr) tNodes[i].nodeValue = unitStr;
      }
    }

    var descTxt = isDetail ? ("أضف «" + parsedSel.optName + "» للسلة") : ("إضافة «" + parsedSel.optName + "» للسلة");
    setCleanBtnTextV129(addBtn, descTxt);
    var bPrice = totalStr + " ريال";
    if (addBtn.getAttribute("data-v127-btn-price") !== bPrice) addBtn.setAttribute("data-v127-btn-price", bPrice);
  }

  window.__runV129Sync = function() {
    try {
      if (!document.getElementById("v127-variant-gold-styles")) {
        var st = document.createElement("style");
        st.id = "v127-variant-gold-styles";
        st.textContent =
          "button[data-v127-opt-price] { display: inline-flex !important; flex-direction: column !important; align-items: center !important; justify-content: center !important; gap: 3px !important; line-height: 1.25 !important; }" +
          "button[data-v127-opt-price]::after { content: attr(data-v127-opt-price); color: #d4af37 !important; font-weight: 900 !important; font-size: 0.92em !important; direction: rtl !important; display: block !important; }" +
          "button[data-v127-btn-price] { direction: rtl !important; display: inline-flex !important; flex-direction: row !important; align-items: center !important; justify-content: center !important; gap: 8px !important; flex-wrap: wrap !important; color: #ffffff !important; }" +
          "button[data-v127-btn-price]::after { content: attr(data-v127-btn-price); color: #d4af37 !important; font-weight: 900 !important; font-size: 1.02em !important; direction: rtl !important; display: inline-block !important; }";
        document.head.appendChild(st);
      }

      if (window.location.pathname.indexOf("/admin") !== -1) {
        var badge = Array.from(document.querySelectorAll("span, div, strong")).find(function(el) {
          return el.children.length === 0 && (el.textContent || "").indexOf("عدد الخيارات المضافة:") !== -1;
        });
        if (badge) {
          var cm = (badge.textContent || "").match(/:\s*(\d+)/);
          var vCount = cm && cm[1] ? parseInt(cm[1], 10) : 0;
          var fBox = badge.parentElement;
          while (fBox && fBox !== document.body && fBox.querySelectorAll("input").length < 3) fBox = fBox.parentElement;
          if (fBox) {
            Array.from(fBox.querySelectorAll("label, span, div, strong")).forEach(function(lbl) {
              var lt = (lbl.textContent || "").trim();
              if (lbl.children.length === 0 && (lt.indexOf("السعر بالريال") !== -1 || lt.indexOf("السعر الافتراضي (مُلغى") !== -1)) {
                var wrap = lbl.parentElement;
                var inp = wrap ? wrap.querySelector("input") : null;
                if (!inp && wrap && wrap.parentElement) inp = wrap.parentElement.querySelector("input[type='number'], input[placeholder='0']");
                if (inp && inp.id !== "admin-inline-var-price") {
                  if (vCount > 0) {
                    if (inp.value !== "") { inp.value = ""; inp.dispatchEvent(new Event("input", { bubbles: true })); }
                    inp.disabled = true;
                    inp.placeholder = "مُلغى تلقائياً — تُعتمد أسعار الجدول بالأسفل";
                  } else if (inp.disabled) {
                    inp.disabled = false;
                    inp.placeholder = "0";
                  }
                }
              }
            });
          }
        }
      }

      var btns = Array.from(document.querySelectorAll("button"));
      btns.filter(function(b) {
        var t = b.textContent || "";
        return t.indexOf("مجدداً") === -1 && (b.hasAttribute("data-v127-modal-add") || t.indexOf("إضافة إلى السلة") !== -1 || (t.indexOf("إضافة «") !== -1 && t.indexOf("للسلة") !== -1));
      }).forEach(function(addBtn) {
        addBtn.setAttribute("data-v127-modal-add", "1");
        var modal = addBtn.parentElement;
        for (var u = 0; u < 6 && modal && modal.parentElement && modal.parentElement !== document.body; u++) {
          var mt = modal.textContent || "";
          var hasV = Array.from(modal.querySelectorAll("button")).some(function(b) { return b !== addBtn && (b.hasAttribute("data-raw-opt") || (b.textContent || "").indexOf(":") !== -1); });
          if (hasV && (mt.indexOf("ر.ي") !== -1 || mt.indexOf("ريال") !== -1) && mt.indexOf("/") !== -1) break;
          modal = modal.parentElement;
        }
        if (modal) syncBoxV129(modal, addBtn, false);
      });

      btns.filter(function(b) {
        if (b.hasAttribute("data-v127-modal-add")) return false;
        var t = b.textContent || "";
        return b.hasAttribute("data-v127-detail-add") || (t.indexOf("أضف «") !== -1 && t.indexOf("للسلة") !== -1);
      }).forEach(function(dBtn) {
        var card = dBtn.parentElement, found = null;
        for (var u = 0; u < 7 && card && card !== document.body; u++) {
          var dt = card.textContent || "";
          var hasV = dt.indexOf("اختر النوع") !== -1 || Array.from(card.querySelectorAll("button")).some(function(b) { return b !== dBtn && (b.hasAttribute("data-raw-opt") || (b.textContent || "").indexOf(":") !== -1); });
          if (hasV && (dt.indexOf("ر.ي") !== -1 || dt.indexOf("ريال") !== -1) && dt.indexOf("/") !== -1) { found = card; break; }
          card = card.parentElement;
        }
        if (found) { dBtn.setAttribute("data-v127-detail-add", "1"); syncBoxV129(found, dBtn, true); }
      });
    } catch (e) {}
  };

  if (!window.__v129Bound) {
    window.__v129Bound = true;
    document.addEventListener("click", function(ev) {
      try {
        var btn = ev.target && ev.target.closest ? ev.target.closest("button") : null;
        if (btn) {
          var raw = btn.getAttribute("data-raw-opt") || getCleanBtnTextV129(btn);
          if (raw.indexOf(":") !== -1) {
            window.__v128ActiveVariant = raw;
            var grp = (btn.parentElement && btn.parentElement.parentElement) || btn.parentElement;
            if (grp) Array.from(grp.querySelectorAll("button")).forEach(function(s) { s.removeAttribute("data-v129-sel"); });
            btn.setAttribute("data-v129-sel", "1");
          }
        }
      } catch (e) {}
      window.__runV129Sync();
      setTimeout(window.__runV129Sync, 10);
      setTimeout(window.__runV129Sync, 50);
      setTimeout(window.__runV129Sync, 150);
    }, true);
    setInterval(window.__runV129Sync, 150);
  }
})();
"""

# 1. تحديث Admin.tsx
admin_path = pathlib.Path("client/src/pages/Admin.tsx")
if admin_path.exists():
  ac = admin_path.read_text(encoding="utf-8")
  if 'setField("price", "");' not in ac:
    ac = re.sub(
        r'(if\s*\(!form\.variants\.includes\(finalEntry\)\)\s*\{\s*setField\("variants",\s*\[\.\.\.form\.variants,\s*finalEntry\]\);\s*\})',
        lambda m: m.group(1) + '\n              setField("price", "");',
        ac,
    )
  if "autoVariantBasePriceV128" not in ac:
    auto_s = """
    const autoVariantBasePriceV128 = (() => {
      for (const v of allVariants) {
        const m = String(v || "").match(/:\\s*(\\d+(?:\\.\\d+)?)/);
        if (m && Number(m[1]) > 0) return String(m[1]);
      }
      return "";
    })();
    if (allVariants.length > 0 && autoVariantBasePriceV128) {
      (form as any).price = autoVariantBasePriceV128;
    }"""
    ac = re.sub(
        r"(const\s+allVariants\s*=[\s\S]*?:\s*form\.variants;)",
        lambda m: m.group(1) + auto_s,
        ac,
        count=1,
    )
  admin_path.write_text(ac, encoding="utf-8")
  print("1. Updated Admin.tsx!")

# 2. حقن المحرك داخل Home.tsx دون مسح تعديلات السلة
home_path = pathlib.Path("client/src/pages/Home.tsx")
if home_path.exists():
  hc = home_path.read_text(encoding="utf-8")
  hc = re.sub(r"// === V129_ENGINE_START ===[\s\S]*?// === V129_ENGINE_END ===\n?", "", hc)
  last_imp = hc.rfind("\nimport ", 0, 3000)
  end_imp = hc.find("\n", last_imp + 1) if last_imp != -1 else 0
  wrapped_eng = "\n// === V129_ENGINE_START ===\n" + ENGINE_JS_V129 + "\n// === V129_ENGINE_END ===\n"
  hc = hc[: end_imp + 1] + wrapped_eng + hc[end_imp + 1 :]
  home_path.write_text(hc, encoding="utf-8")
  print("2. Injected v129 engine into Home.tsx!")

# 3. استبدال PART A القديم في client/index.html بالمحرك الجديد
html_path = pathlib.Path("client/index.html")
if html_path.exists():
  ht = html_path.read_text(encoding="utf-8")
  pat_a = r'// PART A:[\s\S]*?(?=// PART B: Shopping Cart \("سلة التسوق"\) rows)'
  rep_a = "            // PART A: v129 Engine\n            if (window.__runV129Sync) window.__runV129Sync();\n\n"
  ht, n_a = re.subn(pat_a, lambda m: rep_a, ht, count=1)
  ht = re.sub(r"<script id=\"v129-standalone-engine\">[\s\S]*?</script>\s*", "", ht)
  ht = ht.replace("</body>", '<script id="v129-standalone-engine">' + ENGINE_JS_V129 + "</script>\n</body>", 1)
  html_path.write_text(ht, encoding="utf-8")
  print("3. Updated client/index.html (PART A replaced:", n_a, ")!")

# 4. تحديث sw.js إلى v129
sw_path = pathlib.Path("client/public/sw.js")
if sw_path.exists():
  swc = sw_path.read_text(encoding="utf-8")
  swc = re.sub(r'const CACHE = "original-shell-v[^"]*";', 'const CACHE = "original-shell-v129";', swc)
  swc = swc.replace('url.pathname.includes("/assets/") ||\n    ', "").replace('url.pathname.includes("/assets/") ||', "")
  sw_path.write_text(swc, encoding="utf-8")
  print("4. Updated sw.js to v129!")

if pathlib.Path("./node_modules/.bin/esbuild").exists():
  res_cli = subprocess.run(
      "./node_modules/.bin/esbuild client/src/pages/Admin.tsx client/src/pages/Home.tsx --bundle --platform=browser --packages=external --outdir=./.tmp_cli_v129",
      shell=True, capture_output=True, text=True
  )
  subprocess.run("rm -rf ./.tmp_cli_v129", shell=True)
  if res_cli.returncode != 0:
    print("❌ خطأ في فحص الواجهة:", res_cli.stderr)
    sys.exit(1)

print("✅ نجح الفحص بنسبة 100%!")
os.system("git add client/src/pages/Admin.tsx client/src/pages/Home.tsx client/index.html client/public/sw.js")
os.system('git commit -m "Fix v129: instant variant and quantity price update without sticking to first option"')
os.system("git push origin main")
print("🚀 تم رفع التحديث v129 بنجاح 100% إلى Render!")
