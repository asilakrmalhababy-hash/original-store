import pathlib, re, subprocess, os

print("=== بدء التحديث v119 (منع تحويل فقاعة رسالة المستخدم الخضراء نهائياً + وضع الصورة والوصفة في فقاعة رد المساعد البيضاء فقط + مطابقة حلا/حلى) ===")

# 1. تحديث normalizeArabicV112 ومطابقة الكلمات في server/ai_engine_v112.ts
ai_path = pathlib.Path("server/ai_engine_v112.ts")
if ai_path.exists():
    ai_txt = ai_path.read_text(encoding="utf-8")
    ai_txt = ai_txt.replace(
        '.replace(/ى/g, "ي")',
        '.replace(/ى/g, "ي").replace(/\\bحلا\\b/g, "حلي")'
    )
    ai_txt = ai_txt.replace(
        'if (matchedWords.length >= 2) return rec;',
        'if (matchedWords.length >= 1) return rec;'
    )
    ai_path.write_text(ai_txt, encoding="utf-8")
    print("1. Updated Arabic normalization (حلا = حلى) and keyword matching in server/ai_engine_v112.ts!")

# 2. تحديث client/index.html لحماية فقاعة المستخدم الخضراء 100% وحصر الصورة والوصفة في فقاعة المساعد البيضاء فقط
html_path = pathlib.Path("client/index.html")
if html_path.exists():
    ht = html_path.read_text(encoding="utf-8")

    old_block_pattern = r"function normalizeArabicClientV116\(str\) \{[\s\S]*?function enhanceChatBubblesSafelyV117\(\) \{[\s\S]*?\n        \}"

    new_block = """function normalizeArabicClientV116(str) {
          return String(str || "")
            .toLowerCase()
            .replace(/[أإآ]/g, "ا")
            .replace(/ة/g, "ه")
            .replace(/ى/g, "ي")
            .replace(/\\bحلا\\b/g, "حلي")
            .replace(/حلاوة/g, "حلاوه")
            .replace(/[؟?!.,،]/g, " ")
            .replace(/\\s+/g, " ")
            .trim();
        }

        function matchRecipeClientV116(userText) {
          var list = (window.__v114StudioConfig && window.__v114StudioConfig.recipes) || [];
          if (!Array.isArray(list) || list.length === 0) return null;
          var normUser = normalizeArabicClientV116(userText);
          if (!normUser || normUser.length < 2) return null;
          var stopWords = ["اريد", "ابغي", "اشتي", "هل", "عندكم", "ممكن", "كيف", "اسوي", "طريقه", "عمل", "سريع", "في", "من", "مع", "على", "عن"];

          for (var i = 0; i < list.length; i++) {
            var rec = list[i];
            var normTitle = normalizeArabicClientV116(rec.title || "");
            var normKw = normalizeArabicClientV116(rec.keywords || "");
            if (normTitle && (normUser.indexOf(normTitle) !== -1 || normTitle.indexOf(normUser) !== -1)) return rec;
            if (normKw && (normUser.indexOf(normKw) !== -1 || normKw.indexOf(normUser) !== -1)) return rec;

            var kwParts = String(rec.keywords || "").split(/[،,]+/).map(function(s) { return normalizeArabicClientV116(s); }).filter(function(s) { return s.length >= 3; });
            for (var kIdx = 0; kIdx < kwParts.length; kIdx++) {
              if (normUser.indexOf(kwParts[kIdx]) !== -1 || kwParts[kIdx].indexOf(normUser) !== -1) return rec;
            }

            var combinedTarget = normTitle + " " + normKw;
            var userWords = normUser.split(" ").filter(function(w) { return w.length >= 3 && stopWords.indexOf(w) === -1; });
            var matchedWords = userWords.filter(function(w) { return combinedTarget.indexOf(w) !== -1; });
            if (matchedWords.length >= 1) return rec;
          }
          return null;
        }

        function matchRuleClientV116(userText) {
          var rules = (window.__v114StudioConfig && window.__v114StudioConfig.rules) || [];
          if (!Array.isArray(rules) || rules.length === 0) return null;
          var normUser = normalizeArabicClientV116(userText);
          if (!normUser) return null;
          for (var i = 0; i < rules.length; i++) {
            var trig = normalizeArabicClientV116(rules[i].trigger || "");
            if (trig && normUser.indexOf(trig) !== -1) return rules[i];
          }
          return null;
        }

        function matchPromoClientV116(userText) {
          var promos = (window.__v114StudioConfig && window.__v114StudioConfig.promotedProducts) || [];
          if (!Array.isArray(promos) || promos.length === 0) return null;
          var normUser = normalizeArabicClientV116(userText);
          if (!normUser) return null;
          for (var i = 0; i < promos.length; i++) {
            var p = promos[i];
            if (p.active === false || !p.triggerKeywords) continue;
            var kws = String(p.triggerKeywords).split(/[،,]+/).map(function(s) { return normalizeArabicClientV116(s); }).filter(Boolean);
            for (var j = 0; j < kws.length; j++) {
              if (normUser.indexOf(kws[j]) !== -1) return p;
            }
          }
          return null;
        }

        function extractAnyUserTextFromJsonBodyV116(rawBody) {
          try {
            var parsed = JSON.parse(rawBody);
            var found = "";
            function walkObj(o) {
              if (found || !o) return;
              if (typeof o === "string") {
                var s = o.trim();
                if (s.length >= 2 && s.length <= 300 && !/^(user|assistant|system|sess_)/i.test(s)) {
                  found = s;
                }
                return;
              }
              if (Array.isArray(o)) {
                for (var i = o.length - 1; i >= 0; i--) walkObj(o[i]);
                return;
              }
              if (typeof o === "object") {
                var priorityKeys = ["message", "prompt", "query", "text", "userMessage", "question", "content", "input"];
                for (var k = 0; k < priorityKeys.length; k++) {
                  var pk = priorityKeys[k];
                  if (typeof o[pk] === "string" && o[pk].trim().length >= 2) {
                    found = o[pk].trim();
                    return;
                  }
                }
                if (o.json) walkObj(o.json);
                if (o["0"]) walkObj(o["0"]);
                Object.keys(o).forEach(function(key) {
                  if (key !== "meta" && key !== "sessionId") walkObj(o[key]);
                });
              }
            }
            walkObj(parsed);
            return found;
          } catch (e) {
            return "";
          }
        }

        window.__openRecipeImageLightboxV116 = function(src, title) {
          if (!src) return;
          var lb = document.createElement("div");
          lb.style.cssText = "position:fixed;inset:0;z-index:999999;background:rgba(8,28,18,0.92);display:flex;flex-direction:column;align-items:center;justify-content:center;padding:18px;direction:rtl;";
          lb.onclick = function() { lb.remove(); };
          lb.innerHTML =
            '<div style="max-width:520px;width:100%;text-align:center;">' +
            '<img src="' + src + '" style="width:100%;max-height:75vh;object-fit:contain;border-radius:20px;border:3px solid #d4af37;box-shadow:0 18px 50px rgba(0,0,0,0.6);" />' +
            '<div style="color:#d4af37;font-weight:900;font-size:1.05rem;margin-top:12px;">🍰 ' + (title || "") + '</div>' +
            '<button type="button" style="margin-top:12px;background:#ffffff;color:#0d3825;border:none;border-radius:99px;padding:8px 24px;font-weight:800;font-size:0.88rem;cursor:pointer;">✕ إغلاق الصورة</button>' +
            '</div>';
          document.body.appendChild(lb);
        };

        // تعديل رد المساعد فقط في tRPC مع حماية رسائل المستخدم 100%
        function replaceTrpcAiPayloadInPlaceV117(trpcObj, smartData) {
          if (!trpcObj || typeof trpcObj !== "object") return;
          function walkPayload(node) {
            if (!node || typeof node !== "object") return;
            if (Array.isArray(node)) {
              node.forEach(walkPayload);
              return;
            }
            if (node.role === "user" || node.sender === "user" || node.from === "user" || node.isUser === true) {
              return;
            }
            var textKeys = ["reply", "answer", "response", "assistantMessage", "message", "content", "text"];
            textKeys.forEach(function(tk) {
              if (typeof node[tk] === "string" && node[tk].length > 8 && smartData.reply) {
                if (window.__v119LastUserSentText && node[tk].trim() === window.__v119LastUserSentText.trim()) return;
                node[tk] = smartData.reply;
              }
            });
            var itemKeys = ["items", "suggestedItems", "products", "recommendations", "basket"];
            itemKeys.forEach(function(ik) {
              if (Array.isArray(node[ik]) && Array.isArray(smartData.suggestedItems) && smartData.suggestedItems.length > 0) {
                var templateItem = node[ik][0] || {};
                node[ik] = smartData.suggestedItems.map(function(si) {
                  return Object.assign({}, templateItem, {
                    id: si.id || si.productId || 1,
                    productId: si.productId || si.id || 1,
                    name: si.name,
                    productName: si.name,
                    price: si.price || 100,
                    unitPrice: si.price || 100,
                    unit: si.unit || "حبة",
                    quantity: 1,
                    lineTotal: si.price || 100
                  });
                });
              }
            });
            if (typeof node.total === "number" && Array.isArray(smartData.suggestedItems) && smartData.suggestedItems.length > 0) {
              node.total = smartData.suggestedItems.reduce(function(s, x) { return s + Number(x.price || 0); }, 0);
            }
            Object.keys(node).forEach(function(k) {
              if (k !== "items" && k !== "suggestedItems" && typeof node[k] === "object") {
                walkPayload(node[k]);
              }
            });
          }
          walkPayload(trpcObj);
        }

        function isDarkGreenBgV119(el) {
          if (!el || el === document.body) return false;
          try {
            var cs = window.getComputedStyle(el);
            var bg = cs.backgroundColor || "";
            var m = bg.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)/);
            if (m) {
              var r = parseInt(m[1], 10);
              var g = parseInt(m[2], 10);
              var b = parseInt(m[3], 10);
              if (r < 45 && g > 35 && g < 115 && b > 20 && b < 85) return true;
            }
          } catch (e) {}
          return false;
        }

        function isInsideDarkGreenUserBubbleV119(el) {
          var cur = el;
          for (var i = 0; i < 4 && cur && cur !== document.body; i++) {
            if (isDarkGreenBgV119(cur)) return true;
            cur = cur.parentElement;
          }
          return false;
        }

        function enhanceChatBubblesSafelyV117() {
          if (document.body.textContent.indexOf("مساعد وشيف أورجنال الذكي") === -1) return;

          // 1. إزالة أي صورة وُضعت بالخطأ داخل فقاعة المستخدم الخضراء فوراً!
          Array.from(document.querySelectorAll(".v117-recipe-photo-banner, .v118-wa-photo-box")).forEach(function(box) {
            if (box.classList.contains("v117-recipe-photo-banner") || isInsideDarkGreenUserBubbleV119(box)) {
              box.remove();
            }
          });

          // 2. تحديد جميع فقاعات رسائل المستخدم الخضراء وحمايتها 100% من أي تعديل
          var allUserBubbles = Array.from(document.querySelectorAll("div, p, span")).filter(function(el) {
            if (!isDarkGreenBgV119(el)) return false;
            if (el.tagName === "BUTTON" || el.querySelector("button, input, textarea")) return false;
            var hasDarkGreenChild = Array.from(el.children).some(function(c) { return isDarkGreenBgV119(c); });
            if (hasDarkGreenChild) return false;
            var t = (el.textContent || "").trim();
            if (t.indexOf("محادثة جديدة") !== -1 || t.indexOf("الأصناف والمقادير") !== -1) return false;
            if (t.indexOf("🍰") !== -1 && el.getAttribute("data-v119-orig-user")) {
              setLeafTextSafe(el, el.getAttribute("data-v119-orig-user"));
            } else if (t.indexOf("🍰") === -1 && t.length >= 2 && t.length <= 160 && !el.getAttribute("data-v119-orig-user")) {
              el.setAttribute("data-v119-orig-user", t);
            }
            return t.length >= 2;
          });

          // 3. اختيار فقاعة رد المساعد البيضاء فقط (ومنع لمس فقاعة المستخدم الخضراء نهائياً)
          var allLeaves = Array.from(document.querySelectorAll("p, div")).filter(function(el) {
            if (el.children.length !== 0) return false;
            if (el.closest && (el.closest(".v118-wa-photo-box") || el.closest("button"))) return false;
            if (isInsideDarkGreenUserBubbleV119(el)) return false;

            var parentCard = el.parentElement;
            if (!parentCard) return false;
            var cardTxt = parentCard.textContent || "";
            if (cardTxt.indexOf("محادثة جديدة") !== -1 || parentCard.querySelector("input, textarea")) return false;

            var isAssistantCard =
              cardTxt.indexOf("الأصناف والمقادير") !== -1 ||
              cardTxt.indexOf("تأكيد إضافة") !== -1 ||
              cardTxt.indexOf("أضف بمفرده") !== -1 ||
              cardTxt.indexOf("أفكار لتحضيره") !== -1 ||
              cardTxt.indexOf("منتجات مشابهة") !== -1;
            if (!isAssistantCard) return false;

            var parentBubble = el.closest ? el.closest("[data-v119-bubble='1']") : null;
            if (parentBubble && el.getAttribute("data-v119-reply") !== "1") return false;

            var t = (el.textContent || "").trim();
            if (
              t.indexOf("الأصناف والمقادير") !== -1 ||
              t.indexOf("تأكيد إضافة") !== -1 ||
              t.indexOf("الإجمالي:") !== -1 ||
              t.indexOf("ر.ي (حبة)") !== -1 ||
              t.indexOf("أضف بمفرده") !== -1 ||
              t.indexOf("اعتمد وإضافة") !== -1 ||
              t.indexOf("إلغاء") !== -1
            ) {
              return false;
            }
            return t.length >= 12;
          });

          allLeaves.forEach(function(replyLeaf) {
            var assistantCard = replyLeaf.parentElement;
            if (!assistantCard || isInsideDarkGreenUserBubbleV119(assistantCard)) return;

            var precedingUsers = allUserBubbles.filter(function(ub) {
              return Boolean(ub.compareDocumentPosition(assistantCard) & Node.DOCUMENT_POSITION_FOLLOWING);
            });
            var lastUserBubble = precedingUsers.length > 0 ? precedingUsers[precedingUsers.length - 1] : null;
            var userQueryTxt = "";
            if (lastUserBubble) {
              userQueryTxt = (lastUserBubble.getAttribute("data-v119-orig-user") || lastUserBubble.textContent || "").trim();
            }
            if (!userQueryTxt) return;

            var matchedRec = matchRecipeClientV116(userQueryTxt);
            var matchedRule = !matchedRec ? matchRuleClientV116(userQueryTxt) : null;
            var matchedPromo = (!matchedRec && !matchedRule) ? matchPromoClientV116(userQueryTxt) : null;

            if (matchedRec) {
              assistantCard.setAttribute("data-v119-bubble", "1");
              replyLeaf.setAttribute("data-v119-reply", "1");

              // 1. إدراج صورة الوصفة كفقاعة واتساب في أعلى البطاقة البيضاء للمساعد فقط
              if (matchedRec.imageUrl && !assistantCard.querySelector(".v118-wa-photo-box")) {
                var waBox = document.createElement("div");
                waBox.className = "v118-wa-photo-box";
                waBox.style.cssText = "margin:0 0 10px 0;border-radius:12px;overflow:hidden;background:#f1f5f9;cursor:pointer;";
                var waImg = document.createElement("img");
                waImg.src = matchedRec.imageUrl;
                waImg.alt = String(matchedRec.title || "");
                waImg.style.cssText = "width:100%;max-height:240px;object-fit:cover;display:block;border-radius:12px;";
                waBox.onclick = function() {
                  window.__openRecipeImageLightboxV116(matchedRec.imageUrl, matchedRec.title || "");
                };
                waBox.appendChild(waImg);
                replyLeaf.parentNode.insertBefore(waBox, replyLeaf);
              }

              // 2. نص الوصفة تحت الصورة داخل بطاقة المساعد البيضاء فقط
              var targetRecipeText =
                "🍰 " + (matchedRec.title || "") + "\\n\\n" +
                (matchedRec.steps || "");
              replyLeaf.style.whiteSpace = "pre-line";
              replyLeaf.style.lineHeight = "1.65";
              setLeafTextSafe(replyLeaf, targetRecipeText);

              // 3. تحديث المنتجات المقترحة للسلة داخل بطاقة المساعد البيضاء
              var ings = Array.isArray(matchedRec.ingredients) ? matchedRec.ingredients : [];
              if (ings.length > 0) {
                var singleAddBtns = Array.from(assistantCard.querySelectorAll("button")).filter(function(b) {
                  return (b.textContent || "").indexOf("أضف بمفرده") !== -1;
                });

                singleAddBtns.forEach(function(sBtn, sIdx) {
                  var itemRow = sBtn.parentElement;
                  if (!itemRow) return;
                  var targetIng = ings[sIdx];
                  if (!targetIng) {
                    if (sIdx > 0) itemRow.style.display = "none";
                    return;
                  }
                  var tName = String(targetIng.name || "").replace(/\\s*\\([^()]*\\)\\s*$/g, "").trim();
                  var tCat = (window.__v114Catalog || []).find(function(cp) { return cp.name === tName; });
                  var tPrice = Number(targetIng.price || (tCat && tCat.price) || 100);

                  var rowLeaves = Array.from(itemRow.querySelectorAll("span, strong, p, div")).filter(function(rl) {
                    return rl.children.length === 0 && rl.tagName !== "BUTTON" && !sBtn.contains(rl);
                  });
                  rowLeaves.forEach(function(rl) {
                    var rt = (rl.textContent || "").trim();
                    if (rt.indexOf("ر.ي") !== -1 && /\\d/.test(rt)) {
                      setLeafTextSafe(rl, "1 × " + tPrice.toLocaleString("en-US") + " ر.ي (حبة)");
                    } else if (rt.length >= 3 && rt.indexOf("أضف") === -1) {
                      setLeafTextSafe(rl, tName);
                    }
                  });
                });

                var totalSum = ings.reduce(function(acc, g) {
                  var gn = String(g.name || "").replace(/\\s*\\([^()]*\\)\\s*$/g, "").trim();
                  var gc = (window.__v114Catalog || []).find(function(cp) { return cp.name === gn; });
                  return acc + Number(g.price || (gc && gc.price) || 100);
                }, 0);

                var cardLeaves = Array.from(assistantCard.querySelectorAll("span, strong, p, div, button")).filter(function(x) {
                  return x.children.length === 0 && x !== replyLeaf && !(x.closest && x.closest(".v118-wa-photo-box"));
                });
                cardLeaves.forEach(function(cl) {
                  var ct = (cl.textContent || "").trim();
                  if (ct.indexOf("الإجمالي:") !== -1) {
                    setLeafTextSafe(cl, "الإجمالي: " + totalSum.toLocaleString("en-US") + " ر.ي");
                  } else if (ct.indexOf("اعتمد وإضافة الكل للسلة") !== -1) {
                    setLeafTextSafe(cl, "✅ اعتمد وإضافة الكل للسلة (" + totalSum.toLocaleString("en-US") + " ر.ي)");
                  }
                });
              }
            } else if (matchedRule) {
              assistantCard.setAttribute("data-v119-bubble", "1");
              replyLeaf.setAttribute("data-v119-reply", "1");
              replyLeaf.style.whiteSpace = "pre-line";
              setLeafTextSafe(replyLeaf, matchedRule.response || "");
            } else if (matchedPromo) {
              assistantCard.setAttribute("data-v119-bubble", "1");
              replyLeaf.setAttribute("data-v119-reply", "1");
              var promoTxt =
                (matchedPromo.promoBadge ? matchedPromo.promoBadge + " — " : "⭐ ترشيح خاص لك: ") +
                "«" + (matchedPromo.productName || "") + "»" +
                (matchedPromo.productPrice ? " (" + matchedPromo.productPrice + " ر.ي)" : "") +
                "\\n" + (matchedPromo.promoPitch || "");
              replyLeaf.style.whiteSpace = "pre-line";
              setLeafTextSafe(replyLeaf, promoTxt);
            }
          });
        }"""

    ht, n_rep = re.subn(old_block_pattern, lambda m: new_block, ht, count=1)
    ht = ht.replace(
        "var detectedMsg = extractAnyUserTextFromJsonBodyV116(init.body);",
        "var detectedMsg = extractAnyUserTextFromJsonBodyV116(init.body);\n              if (detectedMsg) window.__v119LastUserSentText = detectedMsg;"
    )
    html_path.write_text(ht, encoding="utf-8")
    print("2. Updated client/index.html (replacements:", n_rep, ")!")

# 3. ترقية رقم كاش Service Worker إلى v119
sw_path = pathlib.Path("client/public/sw.js")
if sw_path.exists():
    sw_txt = sw_path.read_text(encoding="utf-8")
    sw_txt = re.sub(r'v10\d|v11\d|v9\d', 'v119', sw_txt)
    sw_path.write_text(sw_txt, encoding="utf-8")
    print("3. Bumped Service Worker cache to v119!")

# 4. فحص البناء والرفع
res_srv = subprocess.run(
    "npx esbuild server/_core/index.ts --bundle --platform=node --format=esm --packages=external --outfile=./.tmp_srv_v119.js",
    shell=True, capture_output=True, text=True
)
res_cli = subprocess.run(
    "npx esbuild client/src/pages/Admin.tsx client/src/pages/Home.tsx --bundle --platform=browser --packages=external --outdir=./.tmp_cli_v119",
    shell=True, capture_output=True, text=True
)
os.system("rm -rf ./.tmp_srv_v119.js ./.tmp_cli_v119")

if res_srv.returncode != 0 or res_cli.returncode != 0:
    print("❌ Build check failed:", res_srv.stderr, res_cli.stderr)
else:
    print("✅ Build check passed 100%!")
    os.system("git add server/ai_engine_v112.ts client/index.html client/public/sw.js")
    os.system('git commit -m "Fix v119: protect user green bubble 100% and show WhatsApp recipe photo only inside assistant white bubble"')
    os.system("git push origin main")
    print("🚀 تم الرفع بنجاح إلى Render (v119)!")
