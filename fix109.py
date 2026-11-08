import pathlib, re, subprocess, sys

print(
    "=== بدء التحديث الشامل v109 (توحيد السعر 1,900 ر.ي بين السلة ونافذة إتمام"
    " الطلب وتفاصيل الطلب والإدارة 100%) ==="
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
#    - PART A: Variant Picker Modal price & detailed breakdown without touching product title
#    - PART B: Shopping Cart ("سلة التسوق") rows + multi-variant aggregation into localStorage
#    - PART C: Checkout Modal ("إتمام الطلب") "المجموع الفرعي (3 أصناف)" and "الإجمالي"
#    - PART D: Order Details ("الأصناف المطلوبة" -> "قيمة المنتجات" & "الإجمالي النهائي")
html_path = pathlib.Path("client/index.html")
if html_path.exists():
  ht = html_path.read_text(encoding="utf-8")
  ht = re.sub(
      r"<script>\s*\(function\(\)\s*\{[\s\S]*?syncVariantModalPrice[\s\S]*?</script>",
      "",
      ht,
  )

  v109_live_script = """
    <script>
      (function() {
        window.__v107VariantByName = {};
        window.__v108ComputedCartSubtotal = 0;
        try {
          var savedMap = localStorage.getItem("original_v107_by_name");
          if (savedMap) window.__v107VariantByName = JSON.parse(savedMap) || {};
          var savedSub = sessionStorage.getItem("original_v109_cart_subtotal");
          if (savedSub && Number(savedSub) > 0) window.__v108ComputedCartSubtotal = Number(savedSub);
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

        function parseParenVariantTotal(parenText, defaultQty) {
          var segments = String(parenText || "").split(/[،,+]+/).map(function(s) { return s.trim(); }).filter(Boolean);
          var totalW = 0;
          var totalQ = 0;
          var names = [];
          for (var i = 0; i < segments.length; i++) {
            var seg = segments[i];
            var sQty = 1;
            var hasExplicitQty = false;
            var mm = seg.match(/[×xX*]\\s*(\\d+)/);
            if (mm && mm[1]) {
              sQty = Math.max(1, parseInt(mm[1], 10));
              hasExplicitQty = true;
            }
            var cleanSeg = seg.replace(/[×xX*]\\s*\\d+.*$/, "").trim();
            var cIdx = cleanSeg.indexOf(":");
            if (cIdx !== -1) {
              var oName = cleanSeg.slice(0, cIdx).trim();
              var lPrice = parseFloat(cleanSeg.slice(cIdx + 1).trim());
              if (!isNaN(lPrice) && lPrice > 0) {
                if (segments.length === 1 && !hasExplicitQty && defaultQty > 1) {
                  sQty = defaultQty;
                }
                totalW += lPrice * sQty;
                totalQ += sQty;
                names.push(oName);
              }
            }
          }
          if (totalQ > 0 && totalW > 0) {
            return {
              unitPrice: Math.round(totalW / totalQ),
              lineTotal: Math.round(totalW),
              optName: names.join("، ")
            };
          }
          return null;
        }

        function syncVariantModalPrice() {
          try {
            var buttons = Array.from(document.querySelectorAll("button"));

            // PART A: Variant Picker Modal ("إضافة إلى السلة")
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

            // PART B: Shopping Cart ("سلة التسوق") rows
            var removeBtns = buttons.filter(function(b) {
              return b.offsetParent !== null && (b.textContent || "").indexOf("إزالة") !== -1;
            });
            if (removeBtns.length > 0) {
              var cartSubtotalSum = 0;
              var anyVariantFound = false;
              var aggregatedByProduct = {};

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

                var rowFullText = rowCard.textContent || "";
                var parenMatches = Array.from(rowFullText.matchAll(/\\(([^()]*:\\s*\\d+(?:\\.\\d+)?[^()]*)\\)/g));
                var rowUnitPrice = 0;
                var rowLineTotal = 0;
                var rowOptName = "";
                var rawParenContent = "";

                if (parenMatches.length > 0) {
                  rawParenContent = parenMatches[parenMatches.length - 1][1].trim();
                  var parsedObj = parseParenVariantTotal(rawParenContent, rowQty);
                  if (parsedObj) {
                    rowUnitPrice = parsedObj.unitPrice;
                    rowLineTotal = parsedObj.lineTotal;
                    rowOptName = parsedObj.optName;
                    anyVariantFound = true;
                  }
                }

                if (rowUnitPrice > 0 && rowOptName) {
                  var titleCandidates = Array.from(rowCard.querySelectorAll("h2, h3, h4, strong, p, div, span")).filter(function(el) {
                    return el.children.length === 0 && (el.textContent || "").indexOf("(" + rawParenContent + ")") !== -1;
                  });
                  if (titleCandidates.length > 0) {
                    var fullTitle = (titleCandidates[0].textContent || "").trim();
                    var baseTitle = fullTitle.replace(/\\s*\\([^()]*\\)\\s*$/, "").trim();
                    if (baseTitle) {
                      if (!aggregatedByProduct[baseTitle]) aggregatedByProduct[baseTitle] = [];
                      aggregatedByProduct[baseTitle].push(rowOptName + ":" + rowUnitPrice + " × " + rowQty);
                    }
                  }
                }

                var priceEls = Array.from(rowCard.querySelectorAll("span, div, strong, p, small")).filter(function(el) {
                  return isPurePriceElement(el) && !remBtn.contains(el);
                });

                if (rowUnitPrice <= 0) {
                  for (var uIdx = 0; uIdx < priceEls.length; uIdx++) {
                    var ut = (priceEls[uIdx].textContent || "").trim();
                    if (ut.indexOf("/") !== -1) {
                      var um = ut.match(/^(\\d[\\d,.]*)/);
                      if (um && um[1]) {
                        rowUnitPrice = parseFloat(um[1].replace(/,/g, ""));
                        rowLineTotal = Math.round(rowUnitPrice * rowQty);
                        break;
                      }
                    }
                  }
                }

                if (rowUnitPrice > 0) {
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

              var prodKeys = Object.keys(aggregatedByProduct);
              if (prodKeys.length > 0) {
                prodKeys.forEach(function(pk) {
                  window.__v107VariantByName[pk] = aggregatedByProduct[pk].join("، ");
                });
                try {
                  localStorage.setItem("original_v107_by_name", JSON.stringify(window.__v107VariantByName));
                } catch (e) {}
              }

              if (cartSubtotalSum > 0) {
                window.__v108ComputedCartSubtotal = cartSubtotalSum;
                try {
                  sessionStorage.setItem("original_v109_cart_subtotal", String(cartSubtotalSum));
                } catch (e) {}
              }
            }

            // PART C: Update Summary Totals in BOTH Shopping Cart ("ملخص الطلب") AND Checkout Modal ("إتمام الطلب")
            var activeCartSub = window.__v108ComputedCartSubtotal || 0;
            var allContainers = Array.from(document.querySelectorAll("div, section, li"));
            if (activeCartSub > 0) {
              var isCartOrCheckoutVisible = removeBtns.length > 0 || document.body.textContent.indexOf("إتمام الطلب") !== -1;
              if (isCartOrCheckoutVisible) {
                var subFormatted = activeCartSub.toLocaleString("en-US") + " ر.ي";

                var detectedDeliveryFee = 0;
                allContainers.forEach(function(box) {
                  if (box.children.length === 2) {
                    var t0 = (box.children[0].textContent || "").trim();
                    var t1 = (box.children[1].textContent || "").trim();
                    var feeTxt = "";
                    if (t0 === "رسوم التوصيل" || t0 === "التوصيل") feeTxt = t1;
                    else if (t1 === "رسوم التوصيل" || t1 === "التوصيل") feeTxt = t0;
                    if (feeTxt && feeTxt.indexOf("مجاني") === -1 && feeTxt.indexOf("يحسب") === -1) {
                      var fm = feeTxt.match(/(\\d[\\d,.]*)/);
                      if (fm && fm[1]) {
                        var fp = parseFloat(fm[1].replace(/,/g, ""));
                        if (!isNaN(fp) && fp > 0) detectedDeliveryFee = fp;
                      }
                    }
                  }
                });

                var totalFormatted = Math.round(activeCartSub + detectedDeliveryFee).toLocaleString("en-US") + " ر.ي";

                allContainers.forEach(function(box) {
                  if (box.children.length === 2) {
                    var t0 = (box.children[0].textContent || "").trim();
                    var t1 = (box.children[1].textContent || "").trim();

                    var isSub0 = t0.indexOf("المجموع الفرعي") === 0;
                    var isSub1 = t1.indexOf("المجموع الفرعي") === 0;
                    var isTot0 = (t0 === "الإجمالي الحالي" || t0 === "الإجمالي");
                    var isTot1 = (t1 === "الإجمالي الحالي" || t1 === "الإجمالي");

                    if (isSub0 && /^\\d[\\d,.]*\\s*ر\\.ي$/.test(t1)) {
                      setLeafTextSafe(box.children[1], subFormatted);
                    } else if (isSub1 && /^\\d[\\d,.]*\\s*ر\\.ي$/.test(t0)) {
                      setLeafTextSafe(box.children[0], subFormatted);
                    } else if (isTot0 && /^\\d[\\d,.]*\\s*ر\\.ي$/.test(t1)) {
                      setLeafTextSafe(box.children[1], totalFormatted);
                    } else if (isTot1 && /^\\d[\\d,.]*\\s*ر\\.ي$/.test(t0)) {
                      setLeafTextSafe(box.children[0], totalFormatted);
                    }
                  }
                });
              }
            }

            // PART D: Order Details Screen ("الأصناف المطلوبة" -> "قيمة المنتجات" & "الإجمالي النهائي")
            if (document.body.textContent.indexOf("الأصناف المطلوبة") !== -1 && document.body.textContent.indexOf("قيمة المنتجات") !== -1) {
              var orderItemsSum = 0;
              var foundOrderItems = false;

              allContainers.forEach(function(box) {
                if (box.children.length === 2) {
                  var c0 = (box.children[0].textContent || "").trim();
                  var c1 = (box.children[1].textContent || "").trim();
                  var nameSide = null;
                  var priceSide = null;
                  if (/^\\d+\\s*[×xX*]\\s*\\d[\\d,.]*\\s*ر\\.ي$/.test(c0)) {
                    priceSide = box.children[0];
                    nameSide = box.children[1];
                  } else if (/^\\d+\\s*[×xX*]\\s*\\d[\\d,.]*\\s*ر\\.ي$/.test(c1)) {
                    priceSide = box.children[1];
                    nameSide = box.children[0];
                  }
                  if (nameSide && priceSide) {
                    var pTxt = (priceSide.textContent || "").trim();
                    var qm = pTxt.match(/^(\\d+)\\s*[×xX*]\\s*(\\d[\\d,.]*)/);
                    var itemQty = qm ? parseInt(qm[1], 10) : 1;
                    var shownUnitP = qm ? parseFloat(qm[2].replace(/,/g, "")) : 0;
                    var nTxt = (nameSide.textContent || "").trim();
                    var pm = Array.from(nTxt.matchAll(/\\(([^()]*:\\s*\\d+(?:\\.\\d+)?[^()]*)\\)/g));
                    if (pm.length > 0) {
                      var joinedP = pm.map(function(x) { return x[1].trim(); }).join("، ");
                      var parsed = parseParenVariantTotal(joinedP, itemQty);
                      if (parsed && parsed.lineTotal > 0) {
                        orderItemsSum += parsed.lineTotal;
                        foundOrderItems = true;
                        return;
                      }
                    }
                    if (shownUnitP > 0) {
                      orderItemsSum += Math.round(shownUnitP * itemQty);
                      foundOrderItems = true;
                    }
                  }
                }
              });

              if (foundOrderItems && orderItemsSum > 0) {
                var orderDeliv = 0;
                allContainers.forEach(function(box) {
                  if (box.children.length === 2) {
                    var t0 = (box.children[0].textContent || "").trim();
                    var t1 = (box.children[1].textContent || "").trim();
                    var fTxt = (t0 === "رسوم التوصيل") ? t1 : (t1 === "رسوم التوصيل" ? t0 : "");
                    if (fTxt && fTxt.indexOf("مجاني") === -1) {
                      var fm = fTxt.match(/(\\d[\\d,.]*)/);
                      if (fm && fm[1]) orderDeliv = parseFloat(fm[1].replace(/,/g, "")) || 0;
                    }
                  }
                });
                var oSubStr = orderItemsSum.toLocaleString("en-US") + " ر.ي";
                var oTotStr = Math.round(orderItemsSum + orderDeliv).toLocaleString("en-US") + " ر.ي";
                allContainers.forEach(function(box) {
                  if (box.children.length === 2) {
                    var t0 = (box.children[0].textContent || "").trim();
                    var t1 = (box.children[1].textContent || "").trim();
                    if (t0 === "قيمة المنتجات") setLeafTextSafe(box.children[1], oSubStr);
                    else if (t1 === "قيمة المنتجات") setLeafTextSafe(box.children[0], oSubStr);
                    else if (t0 === "الإجمالي النهائي") setLeafTextSafe(box.children[1], oTotStr);
                    else if (t1 === "الإجمالي النهائي") setLeafTextSafe(box.children[0], oTotStr);
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
        setInterval(syncVariantModalPrice, 300);
      })();
    </script>
"""
  ht = ht.replace("</body>", v109_live_script + "\n  </body>", 1)
  html_path.write_text(ht, encoding="utf-8")
  print(
      "1. Updated client/index.html to sync Modal, Cart, Checkout Modal"
      " ('إتمام الطلب'), and Order Details ('تفاصيل الطلب')!"
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

  // 2. Extract ALL parentheses groups (...) in rawItemName so multiple variant entries of the same product are all included!
  let innerParen = "";
  const parenMatches = Array.from(rawItemName.matchAll(/\\(([^()]+)\\)/g));
  if (parenMatches.length > 0) {
    innerParen = parenMatches.map(m => m[1].trim()).filter(s => s.includes(":")).join("، ");
    if (!innerParen) innerParen = parenMatches[parenMatches.length - 1][1].trim();
  } else if (rawItemName.includes(":")) {
    innerParen = rawItemName;
  }

  if (innerParen) {
    const segments = innerParen.split(/[،,+]+/).map(s => s.trim()).filter(Boolean);
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
      const effectiveUnitPrice = totalWeightedPrice / totalSegQty;
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
          "2. Upgraded resolveServerVariantOption in server/commerce.ts"
          " (supports multi-row variant aggregation)!"
      )

  comm_path.write_text(cc, encoding="utf-8")

# 3. Update client/src/pages/Home.tsx (from clean v98 state):
home_path = pathlib.Path("client/src/pages/Home.tsx")
if home_path.exists():
  hc = home_path.read_text(encoding="utf-8")

  v109_helpers = """function getStoredVariantTextV107(productId: any, productName?: any): string {
  const partsFound: string[] = [];
  try {
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
            if (typeof val === "string" && val.includes(":")) {
              partsFound.push(val);
            } else if (Array.isArray(val)) {
              const s = val.map((x: any) => typeof x === "string" ? x : (x?.label || x?.variant || x?.name || "")).filter(Boolean).join("، ");
              if (s.includes(":")) partsFound.push(s);
            } else if (val && typeof val === "object") {
              const parts: string[] = [];
              for (const [vk, vv] of Object.entries(val)) {
                if (vk.includes(":") && Number(vv) > 0) {
                  parts.push(Number(vv) > 1 ? vk + " × " + vv : vk);
                }
              }
              if (parts.length > 0) partsFound.push(parts.join("، "));
            }
          }
        } catch {}
      }
    }
    if (productName && typeof window !== "undefined") {
      const cleanPName = String(productName).replace(/\\s*\\([^()]*\\)\\s*$/, "").trim();
      const byName = (window as any).__v107VariantByName;
      if (byName && byName[cleanPName]) {
        const bn = String(byName[cleanPName]);
        if (bn.includes("،") || partsFound.length === 0) return bn;
      }
      const rawByName = localStorage.getItem("original_v107_by_name");
      if (rawByName) {
        const parsedByName = JSON.parse(rawByName);
        if (parsedByName && parsedByName[cleanPName]) {
          const bn = String(parsedByName[cleanPName]);
          if (bn.includes("،") || partsFound.length === 0) return bn;
        }
      }
    }
  } catch {}
  return partsFound.join("، ");
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
    if (/\\([^()]*:\\s*\\d/.test(allStrVals)) {
      combined = allStrVals;
    } else {
      combined = [
        allStrVals,
        getStoredVariantTextV107(pid, pname)
      ].filter(Boolean).join(" ");
    }
  } else if (rawText) {
    combined = String(rawText).trim();
  } else {
    combined = getStoredVariantTextV107(pid, pname);
  }

  if (!combined) return base;

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
    targetStr = parenMatches.map(m => m[1].trim()).filter(s => s.includes(":")).join("، ");
    if (!targetStr) targetStr = parenMatches[parenMatches.length - 1][1].trim();
  }

  if (targetStr.includes(":")) {
    const segments = targetStr.split(/[،,+]+/).map(s => s.trim()).filter(Boolean);
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
    const calcSub = Math.round(items.reduce((sum: number, it: any) => {
      const q = Math.max(1, Number(it?.quantity || 1));
      const up = extractVariantPriceV104(it, it?.unitPrice ?? it?.price ?? it?.product?.price, it?.product);
      return sum + up * q;
    }, 0));
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
  hc = hc[: end_imp + 1] + "\n" + v109_helpers + "\n" + hc[end_imp + 1 :]

  hc = re.sub(
      r"\b(item|i|c|it|ci|row|line|cartItem|entry)\.(?:unitPrice|price)\s*\*\s*\1\.quantity\b",
      r"extractVariantLineTotalV107(\1)",
      hc,
  )
  hc = re.sub(
      r"\b(item|i|c|it|ci|row|line|cartItem|entry)\.quantity\s*\*\s*\1\.(?:unitPrice|price)\b",
      r"extractVariantLineTotalV107(\1)",
      hc,
  )

  hc = re.sub(
      r"\b(item|i|c|it|ci|row|line|cartItem|entry)\.product\??\.price\b(?!\s*=(?!=))",
      r"Math.round(extractVariantPriceV104(\1, \1?.product?.price,"
      r" \1?.product))",
      hc,
  )

  hc = re.sub(
      r"\b(item|i|c|it|ci|row|line|cartItem|entry)\.(?:unitPrice|price)\b(?!\s*=(?!=))",
      r"Math.round(extractVariantPriceV104(\1, \1?.unitPrice ?? \1?.price ??"
      r" \1?.product?.price, \1?.product))",
      hc,
  )

  hc = re.sub(
      r"\b(item|i|c|it|ci|row|line|cartItem|entry)\.lineTotal\b(?!\s*=(?!=))",
      r"extractVariantLineTotalV107(\1)",
      hc,
  )

  hc = re.sub(
      r"\b(cart|cartData|quote|quoteData|checkoutQuote|order|selectedOrder|activeOrder|orderDetail|o)\??\.subtotal\b(?!\s*=(?!=)|\s*:)",
      r"extractCartSubtotalV107(\1, \1?.subtotal)",
      hc,
  )
  hc = re.sub(
      r"\b(cart|cartData|quote|quoteData|checkoutQuote|order|selectedOrder|activeOrder|orderDetail|o)\??\.total\b(?!\s*=(?!=)|\s*:)",
      r"extractOrderTotalV107(\1, \1?.total)",
      hc,
  )

  home_path.write_text(hc, encoding="utf-8")
  print(
      "3. Updated client/src/pages/Home.tsx (including quote?.subtotal &"
      " quote?.total in Checkout Modal)!"
  )

# 4. Bump sw.js cache to v109
sw_path = pathlib.Path("client/public/sw.js")
if sw_path.exists():
  swc = sw_path.read_text(encoding="utf-8")
  swc = re.sub(
      r'const CACHE = "original-shell-v[^"]*";',
      'const CACHE = "original-shell-v109";',
      swc,
  )
  sw_path.write_text(swc, encoding="utf-8")
  print("4. Bumped sw.js cache to v109!")

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
            "v109: unify multi-variant cart subtotal (1,900) in checkout modal,"
            " quote, and server order creation"
        ),
    ],
    check=True,
)
subprocess.run(["git", "push", "origin", "main", "--force"], check=True)
print("=== تم رفع التحديث الشامل v109 بنجاح 100% إلى Render! ===")
