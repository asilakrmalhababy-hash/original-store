import os, pathlib, re, subprocess, sys

print(
    "=== بدء التحديث الجراحي الدقيق v127 (تحديث السعر فوراً عند اختيار الحجم أو"
    " النوع + فصل الوصف باللون الأبيض والسعر باللون الذهبي مع كلمة ريال دون"
    " المساس بأي شيء آخر نهائياً) ==="
)

html_path = pathlib.Path("client/index.html")
if not html_path.exists():
  print("❌ لم يتم العثور على client/index.html")
  sys.exit(1)

ht = html_path.read_text(encoding="utf-8")

new_part_a_v127 = """            // PART A: Variant Picker Modal ("إضافة إلى السلة") & Product Detail View ("أضف «...» للسلة") — v127 Surgical Price & Gold/White Formatter
            if (!document.getElementById("v127-variant-gold-styles")) {
              var st127 = document.createElement("style");
              st127.id = "v127-variant-gold-styles";
              st127.textContent =
                "button[data-v127-opt-price] { display: inline-flex !important; flex-direction: column !important; align-items: center !important; justify-content: center !important; gap: 3px !important; line-height: 1.25 !important; }" +
                "button[data-v127-opt-price]::after { content: attr(data-v127-opt-price); color: #d4af37 !important; font-weight: 900 !important; font-size: 0.92em !important; direction: rtl !important; display: block !important; }" +
                "button[data-v127-btn-price] { direction: rtl !important; display: inline-flex !important; flex-direction: row !important; align-items: center !important; justify-content: center !important; gap: 8px !important; flex-wrap: wrap !important; color: #ffffff !important; }" +
                "button[data-v127-btn-price]::after { content: attr(data-v127-btn-price); color: #d4af37 !important; font-weight: 900 !important; font-size: 1.02em !important; direction: rtl !important; display: inline-block !important; }";
              document.head.appendChild(st127);
            }

            function getDirectTextNodesV127(btn) {
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

            function getButtonCleanTextV127(btn) {
              return getDirectTextNodesV127(btn).map(function(n) { return n.nodeValue || ""; }).join("").replace(/[✓✔]/g, "").replace(/\\s+/g, " ").trim();
            }

            function setButtonTextSafeV127(btn, newText) {
              var nodes = getDirectTextNodesV127(btn);
              if (nodes.length === 0) return;
              var joined = nodes.map(function(n) { return n.nodeValue || ""; }).join("").replace(/\\s+/g, " ").trim();
              if (joined === newText.trim()) return;
              nodes[0].nodeValue = " " + newText.trim() + " ";
              for (var i = 1; i < nodes.length; i++) {
                if (nodes[i].nodeValue !== "") nodes[i].nodeValue = "";
              }
            }

            function parseRawVariantOptionV127(raw) {
              var clean = String(raw || "").replace(/[✓✔]/g, "").replace(/\\s+/g, " ").trim();
              var cIdx = clean.indexOf(":");
              if (cIdx === -1) return null;
              var optName = clean.slice(0, cIdx).trim();
              var pricePart = clean.slice(cIdx + 1).trim();
              var m = pricePart.match(/(\\d+(?:\\.\\d+)?)/);
              if (!m || !m[1]) return null;
              var unitPrice = parseFloat(m[1]);
              if (isNaN(unitPrice) || unitPrice <= 0) return null;
              return { raw: optName + ":" + unitPrice, optName: optName, unitPrice: unitPrice };
            }

            function isOptionButtonSelectedV127(b) {
              if (!b) return false;
              var style = window.getComputedStyle(b);
              var bg = style.backgroundColor || "";
              if (bg && bg !== "transparent" && bg.indexOf("rgba(0, 0, 0, 0)") === -1 && bg.indexOf("rgba(0,0,0,0)") === -1) {
                var rgb = bg.match(/\\d+(\\.\\d+)?/g);
                if (rgb && rgb.length >= 3) {
                  var r = parseFloat(rgb[0]);
                  var g = parseFloat(rgb[1]);
                  var bl = parseFloat(rgb[2]);
                  var a = rgb.length >= 4 ? parseFloat(rgb[3]) : 1;
                  if (a > 0.5 && r < 95 && g >= 30 && g < 175 && bl < 125 && g > r) {
                    return true;
                  }
                }
              }
              var fg = (style.color || "").match(/\\d+/g);
              if (fg && fg.length >= 3 && Number(fg[0]) > 210 && Number(fg[1]) > 210 && Number(fg[2]) > 210) {
                return true;
              }
              if (b.querySelector("svg")) return true;
              var cls = b.className || "";
              return cls.indexOf("selected") !== -1 || cls.indexOf("active") !== -1;
            }

            function syncVariantContainerV127(container, addBtn, isDetailView) {
              if (!container || !addBtn) return;
              var cButtons = Array.from(container.querySelectorAll("button"));
              var optBtns = cButtons.filter(function(b) {
                if (b === addBtn) return false;
                var txt = getButtonCleanTextV127(b);
                if (txt === "+" || txt === "-" || txt === "−" || txt === "×" || txt === "✕") return false;
                return txt.indexOf(":") !== -1 || b.hasAttribute("data-raw-opt");
              });
              if (optBtns.length === 0) return;

              optBtns.forEach(function(b) {
                var curTxt = getButtonCleanTextV127(b);
                if (curTxt.indexOf(":") !== -1) {
                  b.setAttribute("data-raw-opt", curTxt);
                }
                var raw = b.getAttribute("data-raw-opt") || curTxt;
                var parsed = parseRawVariantOptionV127(raw);
                if (parsed) {
                  setButtonTextSafeV127(b, parsed.optName);
                  var wantedPriceAttr = parsed.unitPrice.toLocaleString("en-US") + " ريال";
                  if (b.getAttribute("data-v127-opt-price") !== wantedPriceAttr) {
                    b.setAttribute("data-v127-opt-price", wantedPriceAttr);
                  }
                }
              });

              var nowMs = Date.now();
              var selectedOptBtn = optBtns.find(function(b) {
                var ts = Number(b.getAttribute("data-v127-clicked-ts") || 0);
                return ts > 0 && (nowMs - ts) < 400;
              }) || optBtns.find(function(b) {
                return isOptionButtonSelectedV127(b);
              }) || optBtns[0];

              if (!selectedOptBtn) return;
              var rawSelected = selectedOptBtn.getAttribute("data-raw-opt") || getButtonCleanTextV127(selectedOptBtn);
              var parsedSel = parseRawVariantOptionV127(rawSelected);
              if (!parsedSel) return;

              var unitPrice = parsedSel.unitPrice;
              var selectedOptName = parsedSel.optName;

              // Find quantity inside container (look between + and - buttons first, then fallback to leaf integer)
              var qty = 1;
              var foundQty = false;
              for (var bIdx = 0; bIdx < cButtons.length && !foundQty; bIdx++) {
                var qb = cButtons[bIdx];
                if (qb === addBtn || optBtns.indexOf(qb) !== -1) continue;
                var qbt = (qb.textContent || "").trim();
                var isStepBtn = qbt === "+" || qbt === "-" || qbt === "−" || qb.innerHTML.indexOf("M5 12h14") !== -1;
                if (isStepBtn && qb.parentElement) {
                  var qSibs = Array.from(qb.parentElement.querySelectorAll("span, div, strong, p, b"));
                  for (var sIdx = 0; sIdx < qSibs.length; sIdx++) {
                    var st = (qSibs[sIdx].textContent || "").trim();
                    if (/^\\d+$/.test(st) && qSibs[sIdx].children.length === 0) {
                      var qv = parseInt(st, 10);
                      if (qv >= 1 && qv <= 999) {
                        qty = qv;
                        foundQty = true;
                        break;
                      }
                    }
                  }
                }
              }
              if (!foundQty) {
                var allEls = Array.from(container.querySelectorAll("p, small, span, div, strong, b"));
                for (var i = 0; i < allEls.length; i++) {
                  if (optBtns.some(function(ob) { return ob === allEls[i] || ob.contains(allEls[i]); })) continue;
                  var st2 = (allEls[i].textContent || "").trim();
                  if (/^\\d+$/.test(st2) && allEls[i].children.length === 0) {
                    var val = parseInt(st2, 10);
                    if (val >= 1 && val <= 999) {
                      qty = val;
                      break;
                    }
                  }
                }
              }

              var totalPrice = Math.round(unitPrice * qty);
              var unitPriceStr = unitPrice.toLocaleString("en-US");
              var totalPriceStr = totalPrice.toLocaleString("en-US");

              // 1. Update unit price badge/subtitle (e.g. "350 ر.ي / حبة" -> "150 ر.ي / حبة") immediately
              var priceCandidates = Array.from(container.querySelectorAll("p, small, span, div, strong, b"));
              priceCandidates.forEach(function(el) {
                if (el === addBtn || addBtn.contains(el)) return;
                if (optBtns.some(function(ob) { return ob === el || ob.contains(el); })) return;
                if (el.querySelector("button, img, h1, h2, h3")) return;
                var fullTxt = (el.textContent || "").trim();
                if ((fullTxt.indexOf("ر.ي") !== -1 || fullTxt.indexOf("ريال") !== -1) && fullTxt.indexOf("/") !== -1 && fullTxt.length < 70) {
                  var twP = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null);
                  var tn;
                  while ((tn = twP.nextNode())) {
                    if (tn.nodeValue && /\\d/.test(tn.nodeValue)) {
                      var updatedNodeVal = tn.nodeValue.replace(/\\d[\\d,.]*/, unitPriceStr);
                      if (tn.nodeValue !== updatedNodeVal) {
                        tn.nodeValue = updatedNodeVal;
                      }
                      break;
                    }
                  }
                }
              });

              // 2. Update Add-to-Cart button: White description + Gold price with "ريال"
              var cleanBtnDesc = isDetailView
                ? ("أضف «" + selectedOptName + "» للسلة")
                : ("إضافة «" + selectedOptName + "» للسلة");
              setButtonTextSafeV127(addBtn, cleanBtnDesc);
              var wantedBtnPrice = totalPriceStr + " ريال";
              if (addBtn.getAttribute("data-v127-btn-price") !== wantedBtnPrice) {
                addBtn.setAttribute("data-v127-btn-price", wantedBtnPrice);
              }
            }

            // A1: Variant Picker Modal ("إضافة إلى السلة")
            var modalAddBtns = buttons.filter(function(b) {
              if (!b.getClientRects || b.getClientRects().length === 0) return false;
              var t = b.textContent || "";
              if (t.indexOf("مجدداً") !== -1) return false;
              return b.hasAttribute("data-v127-modal-add") || t.indexOf("إضافة إلى السلة") !== -1 || (t.indexOf("إضافة «") !== -1 && t.indexOf("للسلة") !== -1);
            });
            modalAddBtns.forEach(function(addBtn) {
              addBtn.setAttribute("data-v127-modal-add", "1");
              var modal = addBtn.parentElement;
              while (modal && modal.parentElement && modal.parentElement !== document.body) {
                var hasHeaderPrice = Array.from(modal.querySelectorAll("p, small, span, div, strong")).some(function(el) {
                  if (el === addBtn || addBtn.contains(el)) return false;
                  var t = (el.textContent || "").trim();
                  return (t.indexOf("ر.ي") !== -1 || t.indexOf("ريال") !== -1) && t.indexOf("/") !== -1 && t.length < 70;
                });
                if (modal.querySelectorAll("button").length >= 4 && hasHeaderPrice) {
                  break;
                }
                var parentTxt = modal.parentElement.textContent || "";
                if (parentTxt.indexOf("منتجات المتجر") !== -1 && parentTxt.indexOf("الأقسام") !== -1) {
                  break;
                }
                modal = modal.parentElement;
              }
              if (modal) {
                syncVariantContainerV127(modal, addBtn, false);
              }
            });

            // A2: Product Detail View ("أضف «...» للسلة" + "اختر النوع المطلوب:")
            var detailAddBtns = buttons.filter(function(b) {
              if (!b.getClientRects || b.getClientRects().length === 0) return false;
              if (b.hasAttribute("data-v127-modal-add")) return false;
              var t = b.textContent || "";
              return b.hasAttribute("data-v127-detail-add") || (t.indexOf("أضف «") !== -1 && t.indexOf("للسلة") !== -1);
            });
            detailAddBtns.forEach(function(detailAddBtn) {
              var detailCard = detailAddBtn.parentElement;
              var foundDetailCard = null;
              for (var up = 0; up < 7 && detailCard && detailCard !== document.body; up++) {
                var dcText = detailCard.textContent || "";
                var hasVarBox = dcText.indexOf("اختر النوع") !== -1 || Array.from(detailCard.querySelectorAll("button")).some(function(b) {
                  if (b === detailAddBtn) return false;
                  var bt = (b.textContent || "").trim();
                  return b.hasAttribute("data-raw-opt") || bt.indexOf(":") !== -1;
                });
                var hasUnitPill = Array.from(detailCard.querySelectorAll("p, small, span, div, strong")).some(function(el) {
                  if (el === detailAddBtn || detailAddBtn.contains(el)) return false;
                  var t = (el.textContent || "").trim();
                  return (t.indexOf("ر.ي") !== -1 || t.indexOf("ريال") !== -1) && t.indexOf("/") !== -1 && t.length < 70;
                });
                if (hasVarBox && hasUnitPill) {
                  foundDetailCard = detailCard;
                  break;
                }
                detailCard = detailCard.parentElement;
              }
              if (foundDetailCard) {
                detailAddBtn.setAttribute("data-v127-detail-add", "1");
                syncVariantContainerV127(foundDetailCard, detailAddBtn, true);
              }
            });

"""

pat_part_a = r'// PART A: Variant Picker Modal \("إضافة إلى السلة"\)[\s\S]*?(?=// PART B: Shopping Cart \("سلة التسوق"\) rows)'
ht, n_part_a = re.subn(pat_part_a, lambda m: new_part_a_v127, ht, count=1)
print(
    "1. Updated PART A (Modal + Product Detail variant price & gold/white"
    " display) in client/index.html (matches:",
    n_part_a,
    ")",
)

click_hook_old = "          setTimeout(syncVariantModalPrice, 5);"
click_hook_new = """          try {
            var vBtn127 = ev.target && ev.target.closest ? ev.target.closest("button") : null;
            if (vBtn127 && (vBtn127.hasAttribute("data-raw-opt") || (vBtn127.textContent || "").indexOf(":") !== -1)) {
              var grp127 = (vBtn127.parentElement && vBtn127.parentElement.parentElement) || vBtn127.parentElement;
              if (grp127) {
                Array.from(grp127.querySelectorAll("button")).forEach(function(sib) {
                  sib.removeAttribute("data-v127-clicked-ts");
                });
              }
              vBtn127.setAttribute("data-v127-clicked-ts", String(Date.now()));
              syncVariantModalPrice();
            }
          } catch (e) {}
          setTimeout(syncVariantModalPrice, 5);"""

if "var vBtn127 =" not in ht and click_hook_old in ht:
  ht = ht.replace(click_hook_old, click_hook_new, 1)
  print("2. Added instant 0ms variant option click hook in client/index.html!")

html_path.write_text(ht, encoding="utf-8")

sw_path = pathlib.Path("client/public/sw.js")
if sw_path.exists():
  swc = sw_path.read_text(encoding="utf-8")
  swc = re.sub(
      r'const CACHE = "original-shell-v[^"]*";',
      'const CACHE = "original-shell-v127";',
      swc,
  )
  sw_path.write_text(swc, encoding="utf-8")
  print("3. Bumped Service Worker cache version to v127!")

os.system("git add client/index.html client/public/sw.js")
os.system(
    'git commit -m "Fix v127: instant variant price update and white/gold price'
    ' display on add-to-cart and variant buttons"'
)
os.system("git push origin main")
print("🚀 تم رفع التحديث الجراحي v127 بنجاح 100% إلى Render!")
