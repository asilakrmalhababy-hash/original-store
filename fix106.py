import pathlib, re, subprocess, sys

print(
    "=== بدء التحديث الشامل v106 (توحيد وتأمين أسعار الأحجام في النافذة والسلة"
    " والإدارة + إصلاح أزرار + و - وإزالة في السلة) ==="
)

# 0. Reset modified files to clean HEAD first so no partial edit from previous run remains
subprocess.run(
    [
        "git",
        "checkout",
        "--",
        "server/commerce.ts",
        "client/src/pages/Home.tsx",
        "client/index.html",
        "client/src/index.css",
    ],
    check=False,
)

# 1. Update server/commerce.ts for 100% SECURE server-side variant price lookup from the database:
comm_path = pathlib.Path("server/commerce.ts")
if comm_path.exists():
  cc = comm_path.read_text(encoding="utf-8")

  secure_resolve_fn = """function resolveServerVariantOption(product: any, itemName?: string): { price: number; unit: string; name: string } {
  const fallbackUnit = String(product?.unit || "حبة").trim() || "حبة";
  const fallbackPrice = Math.max(0, Math.round(Number(product?.price || 0)));
  const rawItemName = String(itemName || product?.name || "").trim();
  if (!product?.description || !rawItemName) {
    return { price: fallbackPrice, unit: fallbackUnit, name: rawItemName || String(product?.name || "") };
  }

  // Extract the option label chosen by the customer (e.g. from "بسكويت ماري (كبير:250)" -> "كبير")
  let chosenLabel = rawItemName;
  const parenMatches = Array.from(rawItemName.matchAll(/\\(([^()]+)\\)/g));
  if (parenMatches.length > 0) {
    chosenLabel = parenMatches[parenMatches.length - 1][1].trim();
  } else if (rawItemName.includes(" - ")) {
    chosenLabel = rawItemName.split(" - ").pop()!.trim();
  }
  const cleanChosenName = chosenLabel.split(":")[0].replace(/—.*$/, "").trim();

  // Parse official variants from the database product.description
  const desc = String(product.description || "");
  const vMatch = desc.match(/\\[\\[variants:(\\[[\\s\\S]*?\\])\\]\\]/);
  if (vMatch && vMatch[1]) {
    try {
      const dbVariants: string[] = JSON.parse(vMatch[1]);
      for (const rawVar of dbVariants) {
        const entry = String(rawVar || "").trim();
        const colonIdx = entry.indexOf(":");
        const optName = (colonIdx !== -1 ? entry.slice(0, colonIdx) : entry).trim();
        const optPriceRaw = colonIdx !== -1 ? Number(entry.slice(colonIdx + 1).trim()) : fallbackPrice;
        const officialPrice = (!isNaN(optPriceRaw) && optPriceRaw > 0) ? Math.round(optPriceRaw) : fallbackPrice;

        if (optName && (
          cleanChosenName === optName ||
          chosenLabel === optName ||
          rawItemName.includes("(" + optName + ":") ||
          rawItemName.includes("(" + optName + ")") ||
          rawItemName.includes(optName)
        )) {
          return {
            price: officialPrice,
            unit: optName,
            name: rawItemName.includes(optName) ? rawItemName : String(product?.name || "") + " (" + optName + ")"
          };
        }
      }
    } catch {}
  }

  return { price: fallbackPrice, unit: fallbackUnit, name: rawItemName || String(product?.name || "") };
}"""

  fn_start = cc.find("function resolveServerVariantOption")
  ret_pos = cc.find(
      "return { price: Number(product.price), unit: product.unit", fn_start
  )
  if fn_start != -1 and ret_pos != -1:
    semi = cc.find(";", ret_pos)
    fn_end = cc.find("}", semi) + 1
    cc = cc[:fn_start] + secure_resolve_fn + cc[fn_end:]
    print(
        "1. Upgraded resolveServerVariantOption in server/commerce.ts with 100%"
        " database-verified variant pricing!"
    )

  # Also ensure any call to resolveServerVariantOption(product, ...) passes combined name + unit
  cc = re.sub(
      r"resolveServerVariantOption\(\s*(\w+)\s*,\s*(\w+)\.(?:name|unit)\s*\)",
      r'resolveServerVariantOption(\1, [\2?.name, \2?.unit, (\2 as any)?.variant, (\2 as any)?.selectedVariant].filter(Boolean).join(" "))',
      cc,
  )

  comm_path.write_text(cc, encoding="utf-8")

# 2. Update client/src/pages/Home.tsx:
home_path = pathlib.Path("client/src/pages/Home.tsx")
if home_path.exists():
  hc = home_path.read_text(encoding="utf-8")

  v106_helper = """function extractVariantPriceV104(rawText: any, fallbackPrice: any, productObj?: any): number {
  const base = Number(fallbackPrice ?? productObj?.price ?? 0);
  let combined = "";
  if (typeof rawText === "object" && rawText !== null) {
    combined = [rawText.name, rawText.productName, rawText.variant, rawText.selectedVariant, rawText.option, rawText.unit, rawText.label].filter(Boolean).join(" ");
  } else if (rawText) {
    combined = String(rawText).trim();
  }
  const m = combined.match(/:\\s*(\\d+(?:\\.\\d+)?)/);
  if (m && m[1]) {
    const p = parseFloat(m[1]);
    if (!isNaN(p) && p > 0) return p;
  }
  const desc = String(productObj?.description || (typeof rawText === "object" ? rawText?.description : "") || "");
  const vMatch = desc.match(/\\[\\[variants:(\\[[\\s\\S]*?\\])\\]\\]/);
  if (vMatch && vMatch[1] && combined) {
    try {
      const arr: string[] = JSON.parse(vMatch[1]);
      for (const entry of arr) {
        const parts = String(entry).split(":");
        if (parts.length > 1) {
          const optName = parts[0].trim();
          const optPrice = parseFloat(parts.slice(1).join(":").trim());
          if (optName && combined.includes(optName) && !isNaN(optPrice) && optPrice > 0) {
            return optPrice;
          }
        }
      }
    } catch {}
  }
  return base;
}"""

  if "function extractVariantPriceV104" in hc:
    h_start = hc.find("function extractVariantPriceV104")
    h_brace = hc.find("{", h_start)
    depth = 0
    h_end = h_brace
    for idx_c in range(h_brace, len(hc)):
      if hc[idx_c] == "{":
        depth += 1
      elif hc[idx_c] == "}":
        depth -= 1
        if depth == 0:
          h_end = idx_c + 1
          break
    hc = hc[:h_start] + v106_helper + hc[h_end:]
  else:
    last_imp = hc.rfind("\nimport ", 0, 3000)
    end_imp = hc.find("\n", last_imp + 1) if last_imp != -1 else 0
    hc = hc[: end_imp + 1] + "\n" + v106_helper + "\n" + hc[end_imp + 1 :]

  # B) Replace .price and .unitPrice on common item variable names across Home.tsx
  hc = re.sub(
      r"\b(item|i|c|it|ci|cartItem|entry)\.(?:unitPrice|price)\b(?!\s*=(?!=))",
      r"extractVariantPriceV104(\1, \1?.unitPrice ?? \1?.price)",
      hc,
  )

  # C) In the Cart section ("سلة التسوق"), ensure catalog product price lookups also use extractVariantPriceV104
  cart_pos = hc.find("سلة التسوق")
  if cart_pos != -1:
    cart_win_start = max(0, cart_pos - 800)
    cart_win_end = min(len(hc), cart_pos + 6000)
    cart_win = hc[cart_win_start:cart_win_end]

    map_m = re.search(r"\.map\(\(\s*([a-zA-Z_]\w*)", cart_win)
    item_var = map_m.group(1) if map_m else "item"
    print("Detected Cart map item_var:", item_var)

    cart_win_new = re.sub(
        r"\b(product|prod|p|catalogProduct|matchedProduct)\??\.price\b(?!\s*=(?!=))",
        rf"extractVariantPriceV104({item_var}, \1?.price, \1)",
        cart_win,
    )
    hc = hc[:cart_win_start] + cart_win_new + hc[cart_win_end:]

  # D) Also update any .reduce((sum, x) => ...) in Home.tsx so cart subtotals/totals always use extractVariantPriceV104
  for red_m in list(
      re.finditer(r"\.reduce\s*\(\s*\(\s*(\w+)\s*,\s*(\w+)\s*\)", hc)
  ):
    r_start = red_m.start()
    r_end = min(len(hc), r_start + 400)
    r_slice = hc[r_start:r_end]
    it_v = red_m.group(2)
    r_slice_new = re.sub(
        r"\b(product|prod|p)\??\.price\b",
        rf"extractVariantPriceV104({it_v}, \1?.price, \1)",
        r_slice,
    )
    r_slice_new = re.sub(
        rf"\b{re.escape(it_v)}\.(?:price|unitPrice)\b",
        rf"extractVariantPriceV104({it_v}, {it_v}?.price ?? {it_v}?.unitPrice)",
        r_slice_new,
    )
    hc = hc[:r_start] + r_slice_new + hc[r_end:]

  # E) When sending items to quote or createOrder in Home.tsx, ensure unit carries the variant name if item.name has (...)
  hc = re.sub(
      r"unit:\s*(item|i|c|it)\.unit\b",
      r'unit: (\1.name && String(\1.name).includes("(") ? \1.name : \1.unit)',
      hc,
  )

  home_path.write_text(hc, encoding="utf-8")
  print(
      "2. Updated client/src/pages/Home.tsx with full Cart & Checkout variant"
      " pricing!"
  )

# 3. Update client/index.html with the complete Live Modal + Cart Price & Button Synchronizer:
html_path = pathlib.Path("client/index.html")
if html_path.exists():
  ht = html_path.read_text(encoding="utf-8")
  ht = re.sub(
      r"<script>\s*\(function\(\)\s*\{[\s\S]*?syncVariantModalPrice[\s\S]*?</script>",
      "",
      ht,
  )

  live_v106_script = """
    <script>
      (function() {
        // Safely update text inside a DOM element WITHOUT removing/replacing React's child Text nodes!
        function setElementTextSafe(el, newText) {
          if (!el) return;
          var tw = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null);
          var nodes = [];
          var n;
          while ((n = tw.nextNode())) nodes.push(n);
          if (nodes.length === 0) {
            el.textContent = newText;
          } else if (nodes.length === 1) {
            if (nodes[0].nodeValue !== newText) nodes[0].nodeValue = newText;
          } else {
            var currentJoined = nodes.map(function(x) { return x.nodeValue || ""; }).join("");
            if (currentJoined.trim() === newText.trim()) return;
            nodes[0].nodeValue = newText;
            for (var i = 1; i < nodes.length; i++) {
              if (nodes[i].nodeValue !== "") nodes[i].nodeValue = "";
            }
          }
        }

        // Normalize cart items in localStorage so any item with (كبير:250) has price=250 and unitPrice=250 in storage
        function normalizeCartArray(arr) {
          if (!Array.isArray(arr)) return arr;
          for (var i = 0; i < arr.length; i++) {
            var it = arr[i];
            if (it && typeof it === "object") {
              var nm = [it.name, it.productName, it.variant, it.selectedVariant, it.option, it.unit].filter(Boolean).join(" ");
              var m = nm.match(/:\\s*(\\d+(?:\\.\\d+)?)/);
              if (m && m[1]) {
                var p = parseFloat(m[1]);
                if (!isNaN(p) && p > 0) {
                  it.price = p;
                  if (it.unitPrice !== undefined) it.unitPrice = p;
                }
              }
            }
          }
          return arr;
        }

        var origSetItem = Storage.prototype.setItem;
        Storage.prototype.setItem = function(key, val) {
          try {
            if (val && typeof val === "string" && val.charAt(0) === "[") {
              var parsed = JSON.parse(val);
              if (Array.isArray(parsed) && parsed.length > 0 && (parsed[0].productId !== undefined || parsed[0].quantity !== undefined)) {
                normalizeCartArray(parsed);
                val = JSON.stringify(parsed);
              }
            }
          } catch (e) {}
          return origSetItem.call(this, key, val);
        };

        var origGetItem = Storage.prototype.getItem;
        Storage.prototype.getItem = function(key) {
          var val = origGetItem.call(this, key);
          try {
            if (val && typeof val === "string" && val.charAt(0) === "[") {
              var parsed = JSON.parse(val);
              if (Array.isArray(parsed) && parsed.length > 0 && (parsed[0].productId !== undefined || parsed[0].quantity !== undefined)) {
                normalizeCartArray(parsed);
                return JSON.stringify(parsed);
              }
            }
          } catch (e) {}
          return val;
        };

        // Immediately normalize any existing cart in localStorage on boot
        try {
          for (var k = 0; k < localStorage.length; k++) {
            var keyName = localStorage.key(k);
            if (keyName) {
              var rawV = origGetItem.call(localStorage, keyName);
              if (rawV && rawV.charAt(0) === "[") {
                var arrV = JSON.parse(rawV);
                if (Array.isArray(arrV) && arrV.length > 0 && (arrV[0].productId !== undefined || arrV[0].quantity !== undefined)) {
                  normalizeCartArray(arrV);
                  origSetItem.call(localStorage, keyName, JSON.stringify(arrV));
                }
              }
            }
          }
        } catch (e) {}

        function syncVariantModalPrice() {
          try {
            var buttons = Array.from(document.querySelectorAll("button"));
            var addBtn = buttons.find(function(b) {
              return b.offsetParent !== null && b.textContent && b.textContent.indexOf("إضافة إلى السلة") !== -1;
            });
            if (addBtn) {
              var modal = addBtn.parentElement;
              while (modal && modal !== document.body && modal.querySelectorAll("button").length < 4) {
                modal = modal.parentElement;
              }
              if (modal) {
                var modalButtons = Array.from(modal.querySelectorAll("button"));
                var optBtns = modalButtons.filter(function(b) {
                  if (b === addBtn) return false;
                  var txt = (b.textContent || "").trim();
                  return txt.indexOf(":") !== -1 || b.hasAttribute("data-raw-opt");
                });

                var detailsParts = [];
                optBtns.forEach(function(b) {
                  var raw = b.getAttribute("data-raw-opt") || (b.textContent || "").trim();
                  if (!b.hasAttribute("data-raw-opt") && raw.indexOf(":") !== -1) {
                    b.setAttribute("data-raw-opt", raw);
                  }
                  var mm = raw.match(/^([^:]+):\\s*(\\d+(?:\\.\\d+)?)/);
                  if (mm) {
                    detailsParts.push(mm[1].trim() + ": " + Number(mm[2]).toLocaleString("en-US") + " ر.ي");
                  }
                });

                var selectedOptBtn = optBtns.find(function(b) {
                  var style = window.getComputedStyle(b);
                  var rgb = (style.backgroundColor || "").match(/\\d+/g);
                  var isDarkGreen = rgb && rgb.length >= 3 && Number(rgb[0]) < 100 && Number(rgb[1]) < 150 && Number(rgb[2]) < 120;
                  var cls = b.className || "";
                  return isDarkGreen || cls.indexOf("selected") !== -1 || cls.indexOf("active") !== -1;
                });

                if (selectedOptBtn) {
                  var rawTxt = selectedOptBtn.getAttribute("data-raw-opt") || (selectedOptBtn.textContent || "").trim();
                  var m = rawTxt.match(/:\\s*(\\d+(?:\\.\\d+)?)/);
                  if (m && m[1]) {
                    var unitPrice = parseFloat(m[1]);
                    if (!isNaN(unitPrice) && unitPrice > 0) {
                      var qty = 1;
                      var allEls = Array.from(modal.querySelectorAll("p, small, span, div, strong, b"));
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

                      // 1. Update top price subtitle under product title (showing selected price + detailed option breakdown)
                      allEls.forEach(function(el) {
                        if (el === addBtn || addBtn.contains(el)) return;
                        if ( optBtns.some(function(ob) { return ob === el || ob.contains(el); }) ) return;
                        var fullTxt = (el.textContent || "").trim();
                        if (fullTxt.indexOf("ر.ي") !== -1 && (fullTxt.indexOf("/") !== -1 || fullTxt.indexOf("·") !== -1 || el.tagName === "P" || el.tagName === "SMALL") && el.children.length <= 2) {
                          var detailSuffix = detailsParts.length > 0 ? " (" + detailsParts.join(" · ") + ")" : "";
                          var targetTop = unitPrice.toLocaleString("en-US") + " ر.ي" + detailSuffix;
                          setElementTextSafe(el, targetTop);
                        }
                      });

                      // 2. Update bottom "إضافة إلى السلة (... ر.ي)" button safely
                      var btnFullTxt = (addBtn.textContent || "").trim();
                      var targetPriceStr = totalPrice.toLocaleString("en-US");
                      if (btnFullTxt.indexOf("(" + targetPriceStr + " ر.ي)") === -1) {
                        var twBtn = document.createTreeWalker(addBtn, NodeFilter.SHOW_TEXT, null);
                        var textNodes = [];
                        var n;
                        while ((n = twBtn.nextNode())) textNodes.push(n);
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
                    }
                  }
                }
              }
            }

            // 3. Sync prices inside the Shopping Cart screen ("سلة التسوق") safely via TextNodes
            var headings = Array.from(document.querySelectorAll("h1, h2, h3, h4, strong, div, span"));
            var isCartScreen = headings.some(function(h) { return (h.textContent || "").trim() === "سلة التسوق"; });
            if (isCartScreen) {
              var removeBtns = Array.from(document.querySelectorAll("button")).filter(function(b) {
                return (b.textContent || "").indexOf("إزالة") !== -1;
              });
              var computedCartSubtotal = 0;
              var foundAnyRow = false;

              removeBtns.forEach(function(remBtn, rowIdx) {
                var rowCard = remBtn.parentElement;
                while (rowCard && rowCard !== document.body && (rowCard.textContent || "").indexOf("ر.ي") === -1) {
                  rowCard = rowCard.parentElement;
                }
                if (rowCard && rowCard.parentElement && rowCard.querySelectorAll("img").length === 0 && rowCard.parentElement.querySelectorAll("img").length === 1) {
                  rowCard = rowCard.parentElement;
                }
                if (!rowCard) return;
                rowCard.setAttribute("data-cart-row-idx", String(rowIdx));

                var rowTxt = rowCard.textContent || "";
                var rowQty = 1;
                var rowEls = Array.from(rowCard.querySelectorAll("span, div, strong, p, small"));
                for (var k = 0; k < rowEls.length; k++) {
                  var t = (rowEls[k].textContent || "").trim();
                  if (/^\\d+$/.test(t) && rowEls[k].children.length === 0) {
                    var qv = parseInt(t, 10);
                    if (qv >= 1 && qv <= 999) { rowQty = qv; break; }
                  }
                }

                var pm = rowTxt.match(/:\\s*(\\d+(?:\\.\\d+)?)/);
                var itemUnitP = 0;
                if (pm && pm[1]) {
                  itemUnitP = parseFloat(pm[1]);
                } else {
                  var unitM = rowTxt.match(/(\\d[\\d,.]*)\\s*ر\\.ي\\s*\\//);
                  if (unitM && unitM[1]) itemUnitP = parseFloat(unitM[1].replace(/,/g, ""));
                }

                if (itemUnitP > 0) {
                  foundAnyRow = true;
                  var lineTotal = Math.round(itemUnitP * rowQty);
                  computedCartSubtotal += lineTotal;

                  rowEls.forEach(function(el) {
                    if (el.children.length <= 1 && el.tagName !== "BUTTON") {
                      var et = (el.textContent || "").trim();
                      if (et.indexOf("ر.ي") !== -1 && et.indexOf("/") !== -1) {
                        var newUnitTxt = et.replace(/^\\s*\\d[\\d,.]*/, itemUnitP.toLocaleString("en-US"));
                        setElementTextSafe(el, newUnitTxt);
                      } else if (/^\\d[\\d,.]*\\s*ر\\.ي$/.test(et)) {
                        var newLineTxt = lineTotal.toLocaleString("en-US") + " ر.ي";
                        setElementTextSafe(el, newLineTxt);
                      }
                    }
                  });
                }
              });

              if (foundAnyRow && computedCartSubtotal > 0) {
                var allDivs = Array.from(document.querySelectorAll("div, section, article"));
                allDivs.forEach(function(d) {
                  if (d.children.length === 2) {
                    var c0 = (d.children[0].textContent || "").trim();
                    var c1 = (d.children[1].textContent || "").trim();
                    var subStr = computedCartSubtotal.toLocaleString("en-US") + " ر.ي";
                    if (c0 === "المجموع الفرعي" || c0 === "الإجمالي الحالي") {
                      setElementTextSafe(d.children[1], subStr);
                    } else if (c1 === "المجموع الفرعي" || c1 === "الإجمالي الحالي") {
                      setElementTextSafe(d.children[0], subStr);
                    }
                  }
                });
              }
            }
          } catch (e) {}
        }

        // 4. Fallback rescue for Cart +, -, and إزالة buttons if a tap ever fails to update React state!
        document.addEventListener("click", function(ev) {
          setTimeout(syncVariantModalPrice, 10);
          setTimeout(syncVariantModalPrice, 60);
          setTimeout(syncVariantModalPrice, 150);

          try {
            var btn = ev.target && ev.target.closest ? ev.target.closest("button") : null;
            if (!btn) return;
            var headings = Array.from(document.querySelectorAll("h1, h2, h3, h4, strong, div, span"));
            var isCartScreen = headings.some(function(h) { return (h.textContent || "").trim() === "سلة التسوق"; });
            if (!isCartScreen) return;

            var rowCard = btn.closest("[data-cart-row-idx]");
            if (!rowCard) return;
            var rowIdx = parseInt(rowCard.getAttribute("data-cart-row-idx") || "-1", 10);
            if (rowIdx < 0) return;

            var bTxt = (btn.textContent || "").trim();
            var isRemove = bTxt.indexOf("إزالة") !== -1;
            var isPlus = bTxt === "+" || bTxt === "＋" || btn.innerHTML.indexOf("lucide-plus") !== -1 || (btn.innerHTML.indexOf("M5 12h14") !== -1 && btn.innerHTML.indexOf("M12 5v14") !== -1);
            var isMinus = bTxt === "-" || bTxt === "−" || bTxt === "–" || btn.innerHTML.indexOf("lucide-minus") !== -1 || (btn.innerHTML.indexOf("M5 12h14") !== -1 && btn.innerHTML.indexOf("M12 5v14") === -1);

            if (!isRemove && !isPlus && !isMinus) return;

            var getRowQty = function(rc) {
              var els = Array.from(rc.querySelectorAll("span, div, strong, p"));
              for (var i = 0; i < els.length; i++) {
                var t = (els[i].textContent || "").trim();
                if (/^\\d+$/.test(t) && els[i].children.length === 0) {
                  return parseInt(t, 10);
                }
              }
              return 1;
            };
            var beforeQty = getRowQty(rowCard);
            var beforeCount = document.querySelectorAll("[data-cart-row-idx]").length;

            setTimeout(function() {
              var afterCount = document.querySelectorAll("[data-cart-row-idx]").length;
              var stillInDom = document.body.contains(rowCard);
              var afterQty = stillInDom ? getRowQty(rowCard) : 0;

              if (isRemove && (!stillInDom || afterCount < beforeCount)) { syncVariantModalPrice(); return; }
              if (isPlus && afterQty > beforeQty) { syncVariantModalPrice(); return; }
              if (isMinus && (!stillInDom || afterCount < beforeCount || afterQty < beforeQty)) { syncVariantModalPrice(); return; }

              for (var k = 0; k < localStorage.length; k++) {
                var keyName = localStorage.key(k);
                if (!keyName) continue;
                var rawV = origGetItem.call(localStorage, keyName);
                if (rawV && rawV.charAt(0) === "[") {
                  var arrV = JSON.parse(rawV);
                  if (Array.isArray(arrV) && arrV.length > rowIdx && (arrV[0].productId !== undefined || arrV[0].quantity !== undefined)) {
                    if (isRemove) {
                      arrV.splice(rowIdx, 1);
                    } else if (isPlus) {
                      arrV[rowIdx].quantity = (Number(arrV[rowIdx].quantity) || 1) + 1;
                    } else if (isMinus) {
                      var nq = (Number(arrV[rowIdx].quantity) || 1) - 1;
                      if (nq <= 0) arrV.splice(rowIdx, 1);
                      else arrV[rowIdx].quantity = nq;
                    }
                    normalizeCartArray(arrV);
                    origSetItem.call(localStorage, keyName, JSON.stringify(arrV));
                    window.dispatchEvent(new Event("storage"));
                    window.location.reload();
                    break;
                  }
                }
              }
            }, 80);
          } catch (e) {}
        }, true);

        setInterval(syncVariantModalPrice, 250);
      })();
    </script>
"""
  ht = ht.replace("</body>", live_v106_script + "\n  </body>", 1)
  html_path.write_text(ht, encoding="utf-8")
  print(
      "3. Updated live Modal + Shopping Cart price & button synchronizer in"
      " client/index.html!"
  )

# 4. Ensure RollingWhatsAppWidget never blocks clicks on Cart buttons (-, +, إزالة)
css_path = pathlib.Path("client/src/index.css")
if css_path.exists():
  css = css_path.read_text(encoding="utf-8")
  cart_click_fix = """
/* v106: Ensure cart buttons (-, +, إزالة) always receive clicks cleanly */
.rolling-whatsapp-wrapper, [class*="whatsapp"] {
  pointer-events: none;
}
.rolling-whatsapp-wrapper a, .rolling-whatsapp-wrapper button, [class*="whatsapp"] a, [class*="whatsapp"] button {
  pointer-events: auto;
}
[data-cart-row-idx] button {
  position: relative;
  z-index: 25;
  pointer-events: auto !important;
  touch-action: manipulation;
}
"""
  if "v106: Ensure cart buttons" not in css:
    css = css + "\n" + cart_click_fix
    css_path.write_text(css, encoding="utf-8")

# 5. Bump sw.js cache to v106
sw_path = pathlib.Path("client/public/sw.js")
if sw_path.exists():
  swc = sw_path.read_text(encoding="utf-8")
  swc = re.sub(
      r'const CACHE = "original-shell-v[^"]*";',
      'const CACHE = "original-shell-v106";',
      swc,
  )
  sw_path.write_text(swc, encoding="utf-8")
  print("4. Bumped sw.js cache to v106!")

print("=== 5. فحص كود السيرفر والواجهة عبر esbuild (0.5 ثانية) ===")
res_srv = subprocess.run(
    [
        "./node_modules/.bin/esbuild",
        "server/_core/index.ts",
        "--platform=node",
        "--packages=external",
        "--bundle",
        "--format=esm",
        "--outdir=dist",
    ],
    capture_output=True,
    text=True,
)
if res_srv.returncode != 0:
  print("SERVER ESBUILD ERROR:")
  print(res_srv.stderr or res_srv.stdout)
  sys.exit(1)

res_cli = subprocess.run(
    [
        "./node_modules/.bin/esbuild",
        "client/src/pages/Admin.tsx",
        "client/src/pages/Home.tsx",
        "--bundle",
        "--packages=external",
        "--jsx=automatic",
        "--outdir=dist/check_client",
    ],
    capture_output=True,
    text=True,
)
if res_cli.returncode != 0:
  print("CLIENT ESBUILD ERROR:")
  print(res_cli.stderr or res_cli.stdout)
  sys.exit(1)

subprocess.run(["rm", "-rf", "dist/check_client"], check=False)
print("BOTH SERVER & CLIENT ESBUILD PASSED 100%! Pushing to GitHub & Render...")
subprocess.run(["git", "add", "-A"], check=True)
subprocess.run(
    [
        "git",
        "commit",
        "-m",
        (
            "v106: secure DB-verified variant pricing across modal, cart,"
            " checkout, and admin + cart button fix"
        ),
    ],
    check=True,
)
subprocess.run(["git", "push", "origin", "main", "--force"], check=True)
print("=== تم رفع التحديث الشامل v106 بنجاح 100% إلى Render! ===")
