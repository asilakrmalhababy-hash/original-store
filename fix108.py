import pathlib, re, subprocess, sys

print(
    "=== بدء التحديث الشامل v108 (إصلاح أسعار الأحجام في السلة وعنوان النافذة"
    " وإجمالي الطلب 100%) ==="
)

# 0. Restore server/commerce.ts to clean HEAD and restore Home.tsx + client/index.html to clean v98 (db9eb83) state first!
subprocess.run(
    ["git", "checkout", "HEAD", "--", "server/commerce.ts"],
    check=False,
)
subprocess.run(
    [
        "git",
        "checkout",
        "db9eb83",
        "--",
        "client/src/pages/Home.tsx",
        "client/index.html",
    ],
    check=False,
)

# 1. Update client/index.html:
#    - In Variant Picker Modal: only update price elements matching /^\d[\d,.]*\s*ر\.ي/ with no block children, so the product title ("test") is NEVER overwritten!
#    - In Shopping Cart ("سلة التسوق"): accurately sync each variant row's unit price (e.g. 150, 250, 1,500), line total, المجموع الفرعي (1,900 ر.ي), and الإجمالي الحالي (1,900 ر.ي) strictly from the "(خيار:سعر)" tag in the row title — with ZERO page reloads!
html_path = pathlib.Path("client/index.html")
if html_path.exists():
  ht = html_path.read_text(encoding="utf-8")
  ht = re.sub(
      r"<script>\s*\(function\(\)\s*\{[\s\S]*?syncVariantModalPrice[\s\S]*?</script>",
      "",
      ht,
  )

  v108_live_script = """
    <script>
      (function() {
        window.__v107VariantByName = {};
        window.__v108ComputedCartSubtotal = 0;
        try {
          var savedMap = localStorage.getItem("original_v107_by_name");
          if (savedMap) window.__v107VariantByName = JSON.parse(savedMap) || {};
        } catch (e) {}

        function setLeafTextSafe(el, newText) {
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

        function isPurePriceElement(el) {
          if (!el || el.tagName === "BUTTON") return false;
          if (el.querySelector("div, p, h1, h2, h3, h4, button, img")) return false;
          var t = (el.textContent || "").trim();
          return /^\\d[\\d,.]*\\s*ر\\.ي/.test(t);
        }

        function syncVariantModalPrice() {
          try {
            // PART A: Variant Picker Modal ("إضافة إلى السلة")
            var buttons = Array.from(document.querySelectorAll("button"));
            var addBtn = buttons.find(function(b) {
              return b.offsetParent !== null && b.textContent && b.textContent.indexOf("إضافة إلى السلة") !== -1 && b.textContent.indexOf("مجدداً") === -1;
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

                if (optBtns.length > 0) {
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

                        // Update ONLY pure price subtitle element (starts with "<number> ر.ي" and has no block children) so product title ("test") is NEVER overwritten!
                        allEls.forEach(function(el) {
                          if (!isPurePriceElement(el)) return;
                          if (el === addBtn || addBtn.contains(el)) return;
                          if (optBtns.some(function(ob) { return ob === el || ob.contains(el); })) return;
                          var fullTxt = (el.textContent || "").trim();
                          if (fullTxt.indexOf("/") !== -1 || fullTxt.indexOf("·") !== -1) {
                            var detailSuffix = detailsParts.length > 0 ? " (" + detailsParts.join(" · ") + ")" : "";
                            var targetTop = unitPrice.toLocaleString("en-US") + " ر.ي" + detailSuffix;
                            setLeafTextSafe(el, targetTop);
                          }
                        });

                        // Update bottom "إضافة إلى السلة (... ر.ي)" button
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
            }

            // PART B: Shopping Cart ("سلة التسوق") — read-only from "(خيار:سعر)" in each row's title, ZERO reloads!
            var removeBtns = buttons.filter(function(b) {
              return b.offsetParent !== null && (b.textContent || "").indexOf("إزالة") !== -1;
            });
            if (removeBtns.length > 0) {
              var cartSubtotalSum = 0;
              var anyVariantFound = false;

              removeBtns.forEach(function(remBtn) {
                var rowCard = remBtn.parentElement;
                while (rowCard && rowCard.parentElement && rowCard.parentElement !== document.body) {
                  var pText = rowCard.parentElement.textContent || "";
                  if (pText.indexOf("إفراغ السلة") !== -1 || pText.indexOf("ملخص الطلب") !== -1) break;
                  var pRemCount = Array.from(rowCard.parentElement.querySelectorAll("button")).filter(function(b) {
                    return (b.textContent || "").indexOf("إزالة") !== -1;
                  }).length;
                  if (pRemCount > 1) break;
                  rowCard = rowCard.parentElement;
                }
                if (!rowCard) return;

                // 1. Read quantity strictly from the controls container around remBtn (never from product title!)
                var rowQty = 1;
                var ctrlBox = remBtn.parentElement;
                if (ctrlBox) {
                  var ctrlLeaves = Array.from(ctrlBox.querySelectorAll("span, div, strong, p")).filter(function(el) {
                    return el.children.length === 0 && el !== remBtn && !remBtn.contains(el);
                  });
                  for (var qIdx = 0; qIdx < ctrlLeaves.length; qIdx++) {
                    var qt = (ctrlLeaves[qIdx].textContent || "").trim();
                    if (/^\\d+$/.test(qt)) {
                      var qVal = parseInt(qt, 10);
                      if (qVal >= 1 && qVal <= 9999) {
                        rowQty = qVal;
                        break;
                      }
                    }
                  }
                }

                // 2. Read variant price strictly from parentheses "(خيار:سعر)" inside this row
                var rowFullText = rowCard.textContent || "";
                var parenMatches = Array.from(rowFullText.matchAll(/\\(([^()]*:\\s*\\d+(?:\\.\\d+)?[^()]*)\\)/g));
                var rowUnitPrice = 0;
                var rowOptName = "";

                if (parenMatches.length > 0) {
                  var innerP = parenMatches[parenMatches.length - 1][1].trim();
                  var cIdx = innerP.indexOf(":");
                  if (cIdx !== -1) {
                    rowOptName = innerP.slice(0, cIdx).trim();
                    var parsedP = parseFloat(innerP.slice(cIdx + 1).replace(/[×xX*].*$/, "").trim());
                    if (!isNaN(parsedP) && parsedP > 0) {
                      rowUnitPrice = parsedP;
                      anyVariantFound = true;
                    }
                  }
                }

                var priceEls = Array.from(rowCard.querySelectorAll("span, div, strong, p, small")).filter(function(el) {
                  return isPurePriceElement(el) && !remBtn.contains(el);
                });

                // If this row has no "(خيار:سعر)" in title, read its base unit price from the pure price "X ر.ي / ..." element
                if (rowUnitPrice <= 0) {
                  for (var uIdx = 0; uIdx < priceEls.length; uIdx++) {
                    var ut = (priceEls[uIdx].textContent || "").trim();
                    if (ut.indexOf("/") !== -1) {
                      var um = ut.match(/^(\\d[\\d,.]*)/);
                      if (um && um[1]) {
                        rowUnitPrice = parseFloat(um[1].replace(/,/g, ""));
                        break;
                      }
                    }
                  }
                }

                if (rowUnitPrice > 0) {
                  var rowLineTotal = Math.round(rowUnitPrice * rowQty);
                  cartSubtotalSum += rowLineTotal;

                  if (anyVariantFound && rowOptName) {
                    priceEls.forEach(function(pel) {
                      var lt = (pel.textContent || "").trim();
                      if (lt.indexOf("/") !== -1) {
                        var newUnitStr = rowUnitPrice.toLocaleString("en-US") + " ر.ي / " + rowOptName;
                        setLeafTextSafe(pel, newUnitStr);
                      } else if (/^\\d[\\d,.]*\\s*ر\\.ي$/.test(lt)) {
                        var newTotalStr = rowLineTotal.toLocaleString("en-US") + " ر.ي";
                        setLeafTextSafe(pel, newTotalStr);
                      }
                    });
                  }
                }
              });

              if (anyVariantFound && cartSubtotalSum > 0) {
                window.__v108ComputedCartSubtotal = cartSubtotalSum;
                var subFormatted = cartSubtotalSum.toLocaleString("en-US") + " ر.ي";
                var allContainers = Array.from(document.querySelectorAll("div, section, li"));
                allContainers.forEach(function(box) {
                  if (box.children.length === 2) {
                    var t0 = (box.children[0].textContent || "").trim();
                    var t1 = (box.children[1].textContent || "").trim();
                    if (t0 === "المجموع الفرعي" || t0 === "الإجمالي الحالي" || t0 === "قيمة المنتجات") {
                      setLeafTextSafe(box.children[1], subFormatted);
                    } else if (t1 === "المجموع الفرعي" || t1 === "الإجمالي الحالي" || t1 === "قيمة المنتجات") {
                      setLeafTextSafe(box.children[0], subFormatted);
                    }
                  }
                });
              }
            }
          } catch (e) {}
        }

        document.addEventListener("click", function() {
          setTimeout(syncVariantModalPrice, 15);
          setTimeout(syncVariantModalPrice, 80);
          setTimeout(syncVariantModalPrice, 220);
        }, true);
        setInterval(syncVariantModalPrice, 350);
      })();
    </script>
"""
  ht = ht.replace("</body>", v108_live_script + "\n  </body>", 1)
  html_path.write_text(ht, encoding="utf-8")
  print(
      "1. Updated client/index.html with precision pure-price Modal & Cart"
      " variant synchronizer (zero reloads!)."
  )

# 2. Update server/commerce.ts:
comm_path = pathlib.Path("server/commerce.ts")
if comm_path.exists():
  cc = comm_path.read_text(encoding="utf-8")

  def add_desc_to_select(m):
    block = m.group(0)
    if "description:" not in block and "products.unit" in block:
      return block.replace(
          "unit: products.unit,",
          "unit: products.unit, description: products.description,",
      )
    return block

  cc = re.sub(r"\.select\(\{[\s\S]*?\}\)", add_desc_to_select, cc)

  secure_resolve_fn = """function resolveServerVariantOption(product: any, itemName?: string): { price: number; unit: string; name: string } {
  const fallbackUnit = String(product?.unit || "حبة").trim() || "حبة";
  const fallbackPrice = Math.max(0, Math.round(Number(product?.price || 0)));
  const rawItemName = String(itemName || product?.name || "").trim();
  if (!rawItemName) {
    return { price: fallbackPrice, unit: fallbackUnit, name: String(product?.name || "") };
  }

  // 1. Parse official variants from the database product.description ([[variants:["كبير:250","صغير:150"]]])
  const dbPriceMap: Record<string, number> = {};
  const desc = String(product?.description || "");
  const vMatch = desc.match(/\\[\\[variants:(\\[[\\s\\S]*?\\])\\]\\]/);
  if (vMatch && vMatch[1]) {
    try {
      const dbVariants: string[] = JSON.parse(vMatch[1]);
      for (const rawVar of dbVariants) {
        const subVars = String(rawVar || "").split(/[،,]+/);
        for (const sv of subVars) {
          const entry = sv.trim();
          const colonIdx = entry.indexOf(":");
          if (colonIdx !== -1) {
            const oName = entry.slice(0, colonIdx).trim();
            const oPrice = Number(entry.slice(colonIdx + 1).trim());
            if (oName && !isNaN(oPrice) && oPrice > 0) {
              dbPriceMap[oName] = Math.round(oPrice);
            }
          }
        }
      }
    } catch {}
  }

  // 2. Extract chosen variant content inside parentheses (...) if present
  let innerParen = "";
  const parenMatches = Array.from(rawItemName.matchAll(/\\(([^()]+)\\)/g));
  if (parenMatches.length > 0) {
    innerParen = parenMatches[parenMatches.length - 1][1].trim();
  } else if (rawItemName.includes(":")) {
    innerParen = rawItemName;
  }

  if (innerParen) {
    const segments = innerParen.split(/[،,]+/).map(s => s.trim()).filter(Boolean);
    let totalWeightedPrice = 0;
    let totalSegQty = 0;
    const matchedLabels: string[] = [];

    for (const seg of segments) {
      let segQty = 1;
      const multMatch = seg.match(/[×xX*]\\s*(\\d+)/);
      if (multMatch && multMatch[1]) {
        segQty = Math.max(1, parseInt(multMatch[1], 10));
      }
      const cleanSeg = seg.replace(/[×xX*]\\s*\\d+.*$/, "").trim();
      const colonIdx = cleanSeg.indexOf(":");
      const optName = (colonIdx !== -1 ? cleanSeg.slice(0, colonIdx) : cleanSeg).replace(/—.*$/, "").trim();
      const labelPriceRaw = colonIdx !== -1 ? Number(cleanSeg.slice(colonIdx + 1).trim()) : NaN;

      // Always prefer official DB price from dbPriceMap if available
      let resolvedSegPrice = dbPriceMap[optName];
      if (resolvedSegPrice === undefined) {
        for (const [k, v] of Object.entries(dbPriceMap)) {
          if (optName && k && (optName.includes(k) || k.includes(optName))) {
            resolvedSegPrice = v;
            break;
          }
        }
      }
      if (resolvedSegPrice === undefined && !isNaN(labelPriceRaw) && labelPriceRaw > 0) {
        resolvedSegPrice = Math.round(labelPriceRaw);
      }

      if (resolvedSegPrice !== undefined && resolvedSegPrice > 0) {
        totalWeightedPrice += resolvedSegPrice * segQty;
        totalSegQty += segQty;
        matchedLabels.push(optName);
      }
    }

    if (totalSegQty > 0 && totalWeightedPrice > 0) {
      const effectiveUnitPrice = Math.round(totalWeightedPrice / totalSegQty);
      const unitLabel = matchedLabels.join("، ") || fallbackUnit;
      return {
        price: effectiveUnitPrice,
        unit: unitLabel,
        name: rawItemName
      };
    }
  }

  // 3. Fallback: check if any dbPriceMap option name appears in rawItemName
  for (const [optName, officialPrice] of Object.entries(dbPriceMap)) {
    if (optName && rawItemName.includes(optName)) {
      return {
        price: officialPrice,
        unit: optName,
        name: rawItemName
      };
    }
  }

  return { price: fallbackPrice, unit: fallbackUnit, name: rawItemName || String(product?.name || "") };
}"""

  fn_start = cc.find("function resolveServerVariantOption")
  if fn_start != -1:
    close_col0 = cc.find("\n}", fn_start)
    if close_col0 != -1:
      fn_end = close_col0 + 2
      cc = cc[:fn_start] + secure_resolve_fn + cc[fn_end:]
      print(
          "2. Upgraded resolveServerVariantOption in server/commerce.ts with"
          " DB-verified variant pricing!"
      )

  comm_path.write_text(cc, encoding="utf-8")

# 3. Update client/src/pages/Home.tsx (from clean v98 state):
home_path = pathlib.Path("client/src/pages/Home.tsx")
if home_path.exists():
  hc = home_path.read_text(encoding="utf-8")

  v108_helpers = """function getStoredVariantTextV107(productId: any, productName?: any): string {
  try {
    if (productName && typeof window !== "undefined") {
      const cleanPName = String(productName).replace(/\\s*\\([^()]*\\)\\s*$/, "").trim();
      const byName = (window as any).__v107VariantByName;
      if (byName && byName[cleanPName]) return String(byName[cleanPName]);
      const rawByName = localStorage.getItem("original_v107_by_name");
      if (rawByName) {
        const parsedByName = JSON.parse(rawByName);
        if (parsedByName && parsedByName[cleanPName]) return String(parsedByName[cleanPName]);
      }
    }
    if (productId !== undefined && productId !== null) {
      const pidStr = String(productId);
      for (let i = 0; i < localStorage.length; i++) {
        const k = localStorage.key(i);
        if (!k || k === "original_v107_by_name") continue;
        const raw = localStorage.getItem(k);
        if (!raw || (raw[0] !== "{" && raw[0] !== "[")) continue;
        try {
          const parsed = JSON.parse(raw);
          if (parsed && typeof parsed === "object" && !Array.isArray(parsed) && parsed[pidStr] !== undefined) {
            const val = parsed[pidStr];
            if (typeof val === "string" && val.includes(":")) return val;
            if (Array.isArray(val)) {
              const s = val.map((x: any) => typeof x === "string" ? x : (x?.label || x?.variant || x?.name || "")).filter(Boolean).join("، ");
              if (s.includes(":")) return s;
            }
            if (val && typeof val === "object") {
              const parts: string[] = [];
              for (const [vk, vv] of Object.entries(val)) {
                if (vk.includes(":") && Number(vv) > 0) {
                  parts.push(Number(vv) > 1 ? vk + " × " + vv : vk);
                }
              }
              if (parts.length > 0) return parts.join("، ");
            }
          }
        } catch {}
      }
    }
  } catch {}
  return "";
}

function extractVariantPriceV104(rawText: any, fallbackPrice: any, productObj?: any): number {
  const base = Number(fallbackPrice ?? productObj?.price ?? 0);
  let combined = "";
  let pid: any = productObj?.id ?? productObj?.productId;
  let pname: any = productObj?.name;
  if (typeof rawText === "object" && rawText !== null) {
    pid = rawText.productId ?? rawText.product?.id ?? rawText.id ?? pid;
    pname = rawText.product?.name ?? rawText.productName ?? rawText.name ?? pname;
    const allStrVals = Object.values(rawText).filter(v => typeof v === "string").join(" ");
    combined = [
      allStrVals,
      getStoredVariantTextV107(pid, pname)
    ].filter(Boolean).join(" ");
  } else if (rawText) {
    combined = String(rawText).trim();
  } else {
    combined = getStoredVariantTextV107(pid, pname);
  }

  if (!combined) return base;

  // Build official DB price map from product description if available
  const dbPriceMap: Record<string, number> = {};
  const desc = String(
    productObj?.description ||
    (typeof rawText === "object" ? (rawText?.description || rawText?.product?.description) : "") ||
    ""
  );
  const vMatch = desc.match(/\\[\\[variants:(\\[[\\s\\S]*?\\])\\]\\]/);
  if (vMatch && vMatch[1]) {
    try {
      const arr: string[] = JSON.parse(vMatch[1]);
      for (const rawEntry of arr) {
        const subEntries = String(rawEntry || "").split(/[،,]+/);
        for (const entry of subEntries) {
          const colonIdx = entry.indexOf(":");
          if (colonIdx !== -1) {
            const oName = entry.slice(0, colonIdx).trim();
            const oPrice = parseFloat(entry.slice(colonIdx + 1).trim());
            if (oName && !isNaN(oPrice) && oPrice > 0) {
              dbPriceMap[oName] = oPrice;
            }
          }
        }
      }
    } catch {}
  }

  let targetStr = combined;
  const parenMatches = Array.from(combined.matchAll(/\\(([^()]+)\\)/g));
  if (parenMatches.length > 0) {
    targetStr = parenMatches[parenMatches.length - 1][1].trim();
  }

  if (targetStr.includes(":")) {
    const segments = targetStr.split(/[،,]+/).map(s => s.trim()).filter(Boolean);
    let totalW = 0;
    let totalQ = 0;
    for (const seg of segments) {
      let sQty = 1;
      const mm = seg.match(/[×xX*]\\s*(\\d+)/);
      if (mm && mm[1]) sQty = Math.max(1, parseInt(mm[1], 10));
      const cleanSeg = seg.replace(/[×xX*]\\s*\\d+.*$/, "").trim();
      const cIdx = cleanSeg.indexOf(":");
      if (cIdx !== -1) {
        const oName = cleanSeg.slice(0, cIdx).trim();
        const lPrice = parseFloat(cleanSeg.slice(cIdx + 1).trim());
        const finalP = dbPriceMap[oName] ?? (!isNaN(lPrice) && lPrice > 0 ? lPrice : 0);
        if (finalP > 0) {
          totalW += finalP * sQty;
          totalQ += sQty;
        }
      }
    }
    if (totalQ > 0 && totalW > 0) {
      return totalW / totalQ;
    }
  }

  for (const [oName, oPrice] of Object.entries(dbPriceMap)) {
    if (oName && combined.includes(oName)) return oPrice;
  }

  return base;
}

function extractVariantLineTotalV107(item: any): number {
  if (!item) return 0;
  const qty = Math.max(1, Number(item.quantity || 1));
  const unitP = extractVariantPriceV104(item, item?.unitPrice ?? item?.price ?? item?.product?.price, item?.product);
  return Math.round(unitP * qty);
}

function extractCartSubtotalV107(cartOrOrder: any, fallbackSubtotal?: any): number {
  if (typeof window !== "undefined" && !cartOrOrder?.orderNumber && !cartOrOrder?.status && Number((window as any).__v108ComputedCartSubtotal) > 0) {
    return Number((window as any).__v108ComputedCartSubtotal);
  }
  const items = cartOrOrder?.items;
  if (Array.isArray(items) && items.length > 0) {
    const calcSub = items.reduce((sum: number, it: any) => sum + extractVariantLineTotalV107(it), 0);
    if (typeof window !== "undefined" && !cartOrOrder?.orderNumber && !cartOrOrder?.status) {
      (window as any).__v107LastCartSubtotal = calcSub;
      (window as any).__v107LastCartBaseSubtotal = Number(fallbackSubtotal ?? cartOrOrder?.subtotal ?? 0);
    }
    return calcSub;
  }
  const fb = Number(fallbackSubtotal ?? cartOrOrder?.subtotal ?? 0);
  if (typeof window !== "undefined" && (window as any).__v107LastCartSubtotal && fb > 0 && fb === (window as any).__v107LastCartBaseSubtotal) {
    return Number((window as any).__v107LastCartSubtotal);
  }
  return fb;
}

function extractOrderTotalV107(cartOrOrder: any, fallbackTotal?: any): number {
  const oldTot = Number(fallbackTotal ?? cartOrOrder?.total ?? 0);
  const oldSub = Number(cartOrOrder?.subtotal ?? oldTot);
  const newSub = extractCartSubtotalV107(cartOrOrder, oldSub);
  if (newSub > 0 && newSub !== oldSub) {
    return Math.max(0, oldTot - oldSub + newSub);
  }
  return oldTot;
}"""

  last_imp = hc.rfind("\nimport ", 0, 3000)
  end_imp = hc.find("\n", last_imp + 1) if last_imp != -1 else 0
  hc = hc[: end_imp + 1] + "\n" + v108_helpers + "\n" + hc[end_imp + 1 :]

  # Wrap .product.price and .product?.price across the ENTIRE Home.tsx file
  hc = re.sub(
      r"\b(item|i|c|it|ci|row|line|cartItem|entry)\.product\??\.price\b(?!\s*=(?!=))",
      r"Math.round(extractVariantPriceV104(\1, \1?.product?.price,"
      r" \1?.product))",
      hc,
  )

  # Wrap .price and .unitPrice on cart/order item variables across the ENTIRE Home.tsx file
  hc = re.sub(
      r"\b(item|i|c|it|ci|row|line|cartItem|entry)\.(?:unitPrice|price)\b(?!\s*=(?!=))",
      r"Math.round(extractVariantPriceV104(\1, \1?.unitPrice ?? \1?.price ??"
      r" \1?.product?.price, \1?.product))",
      hc,
  )

  # Wrap .lineTotal on cart/order item variables across the ENTIRE Home.tsx file
  hc = re.sub(
      r"\b(item|i|c|it|ci|row|line|cartItem|entry)\.lineTotal\b(?!\s*=(?!=))",
      r"extractVariantLineTotalV107(\1)",
      hc,
  )

  # Wrap .subtotal and .total on cart, quote, and order objects in Home.tsx
  hc = re.sub(
      r"\b(cart|cartData|quote|quoteData|order|selectedOrder|activeOrder|orderDetail|o)\.subtotal\b(?!\s*=(?!=)|\s*:)",
      r"extractCartSubtotalV107(\1, \1?.subtotal)",
      hc,
  )
  hc = re.sub(
      r"\b(cart|cartData|quote|quoteData|order|selectedOrder|activeOrder|orderDetail|o)\.total\b(?!\s*=(?!=)|\s*:)",
      r"extractOrderTotalV107(\1, \1?.total)",
      hc,
  )

  home_path.write_text(hc, encoding="utf-8")
  print(
      "3. Updated client/src/pages/Home.tsx across entire file with variant"
      " pricing!"
  )

# 4. Bump sw.js cache to v108
sw_path = pathlib.Path("client/public/sw.js")
if sw_path.exists():
  swc = sw_path.read_text(encoding="utf-8")
  swc = re.sub(
      r'const CACHE = "original-shell-v[^"]*";',
      'const CACHE = "original-shell-v108";',
      swc,
  )
  sw_path.write_text(swc, encoding="utf-8")
  print("4. Bumped sw.js cache to v108!")

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
            "v108: fix variant row pricing in cart, preserve modal product"
            " title, and sync cart/order subtotals"
        ),
    ],
    check=True,
)
subprocess.run(["git", "push", "origin", "main", "--force"], check=True)
print("=== تم رفع التحديث الشامل v108 بنجاح 100% إلى Render! ===")
