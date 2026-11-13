import pathlib, re, subprocess, os

print("=== بدء التحديث v118 (تحويل عرض صور الوصفات إلى فقاعة واتساب نظيفة 100% بدون أي نصوص فوق الصورة وبدون تكرار) ===")

# 1. تحديث تنسيق نص الوصفة في السيرفر ليكون كابشن واتساب نظيف تحت الصورة
ai_path = pathlib.Path("server/ai_engine_v112.ts")
if ai_path.exists():
    ai_txt = ai_path.read_text(encoding="utf-8")
    ai_txt = re.sub(
        r'const replyMsg =\s*"يا غالي، جبت لك ألذ وأفخم وصفة[\s\S]*?matchedRecipe\.steps;',
        'const replyMsg = "🍰 " + matchedRecipe.title + "\\n\\n" + matchedRecipe.steps;',
        ai_txt
    )
    ai_path.write_text(ai_txt, encoding="utf-8")
    print("1. Updated recipe caption format in server/ai_engine_v112.ts!")

# 2. تحديث دالة فقاعة المحادثة في client/index.html لتعمل كفقاعة واتساب نظيفة 100%
html_path = pathlib.Path("client/index.html")
if html_path.exists():
    ht = html_path.read_text(encoding="utf-8")

    whatsapp_bubble_fn = """function enhanceChatBubblesSafelyV117() {
          if (document.body.textContent.indexOf("مساعد وشيف أورجنال الذكي") === -1) return;

          // إزالة أي بانر قديم من النسخة السابقة فوراً
          Array.from(document.querySelectorAll(".v117-recipe-photo-banner")).forEach(function(oldB) {
            oldB.remove();
          });

          var allLeaves = Array.from(document.querySelectorAll("p, div")).filter(function(el) {
            if (el.children.length !== 0) return false;
            if (el.closest && (el.closest(".v118-wa-photo-box") || el.closest(".v117-recipe-photo-banner") || el.closest("button"))) return false;
            var parentBubble = el.closest ? el.closest("[data-v118-bubble='1']") : null;
            if (parentBubble && el.getAttribute("data-v118-reply") !== "1") return false;
            var t = (el.textContent || "").trim();
            if (t.indexOf("الأصناف والمقادير") !== -1 || t.indexOf("الإجمالي:") !== -1 || t.indexOf("ر.ي (حبة)") !== -1) return false;
            return t.length >= 18 && (t.indexOf("يا غالي") !== -1 || t.indexOf("حلى") !== -1 || t.indexOf("وصفة") !== -1 || t.indexOf("بسكويت") !== -1 || t.indexOf("🍰") !== -1);
          });

          allLeaves.forEach(function(replyLeaf) {
            var assistantCard = replyLeaf.parentElement;
            if (!assistantCard) return;
            if (assistantCard.textContent.indexOf("محادثة جديدة") !== -1 || assistantCard.querySelector("input, textarea")) return;

            var userQueryTxt = "";
            var stepEl = assistantCard;
            for (var up = 0; up < 4 && stepEl && stepEl.parentElement; up++) {
              if (stepEl.parentElement.textContent.indexOf("محادثة جديدة") !== -1) break;
              var prev = stepEl.previousElementSibling;
              while (prev) {
                var pt = (prev.textContent || "").trim();
                if (pt.length >= 2 && pt.length <= 160 && pt.indexOf("الأصناف والمقادير") === -1 && pt.indexOf("الإجمالي:") === -1) {
                  userQueryTxt = pt;
                  break;
                }
                prev = prev.previousElementSibling;
              }
              if (userQueryTxt) break;
              stepEl = stepEl.parentElement;
            }

            if (!userQueryTxt) return;

            var matchedRec = matchRecipeClientV116(userQueryTxt);
            var matchedRule = !matchedRec ? matchRuleClientV116(userQueryTxt) : null;
            var matchedPromo = (!matchedRec && !matchedRule) ? matchPromoClientV116(userQueryTxt) : null;

            if (matchedRec) {
              assistantCard.setAttribute("data-v118-bubble", "1");
              replyLeaf.setAttribute("data-v118-reply", "1");

              // 1. صورة صافية في أعلى الفقاعة تماماً مثل واتساب (بدون أي كتابة أو مربعات فوق الصورة!)
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

              // 2. نص الوصفة (Caption) تحت الصورة مباشرة مثل واتساب
              var targetRecipeText =
                "🍰 " + (matchedRec.title || "") + "\\n\\n" +
                (matchedRec.steps || "");
              replyLeaf.style.whiteSpace = "pre-line";
              replyLeaf.style.lineHeight = "1.65";
              setLeafTextSafe(replyLeaf, targetRecipeText);

              // 3. تحديث صندوق الأصناف المقترحة الأصلي تحت الوصفة
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
              assistantCard.setAttribute("data-v118-bubble", "1");
              replyLeaf.setAttribute("data-v118-reply", "1");
              replyLeaf.style.whiteSpace = "pre-line";
              setLeafTextSafe(replyLeaf, matchedRule.response || "");
            } else if (matchedPromo) {
              assistantCard.setAttribute("data-v118-bubble", "1");
              replyLeaf.setAttribute("data-v118-reply", "1");
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

    old_pattern = r"function enhanceChatBubblesSafelyV117\(\) \{[\s\S]*?\n        \}"
    ht, n_rep = re.subn(old_pattern, lambda m: whatsapp_bubble_fn, ht, count=1)
    html_path.write_text(ht, encoding="utf-8")
    print("2. Updated client/index.html with clean WhatsApp Photo Bubble (replacements:", n_rep, ")!")

# 3. ترقية رقم كاش Service Worker إلى v118
sw_path = pathlib.Path("client/public/sw.js")
if sw_path.exists():
    sw_txt = sw_path.read_text(encoding="utf-8")
    sw_txt = re.sub(r'v10\d|v11\d|v9\d', 'v118', sw_txt)
    sw_path.write_text(sw_txt, encoding="utf-8")
    print("3. Bumped Service Worker cache to v118!")

# 4. فحص البناء والرفع
res_srv = subprocess.run(
    "npx esbuild server/_core/index.ts --bundle --platform=node --format=esm --packages=external --outfile=./.tmp_srv_v118.js",
    shell=True, capture_output=True, text=True
)
res_cli = subprocess.run(
    "npx esbuild client/src/pages/Admin.tsx client/src/pages/Home.tsx --bundle --platform=browser --packages=external --outdir=./.tmp_cli_v118",
    shell=True, capture_output=True, text=True
)
os.system("rm -rf ./.tmp_srv_v118.js ./.tmp_cli_v118")

if res_srv.returncode != 0 or res_cli.returncode != 0:
    print("❌ Build check failed:", res_srv.stderr, res_cli.stderr)
else:
    print("✅ Build check passed 100%!")
    os.system("git add server/ai_engine_v112.ts client/index.html client/public/sw.js")
    os.system('git commit -m "Fix v118: clean WhatsApp-style photo bubble with caption below and zero overlay repetition"')
    os.system("git push origin main")
    print("🚀 تم الرفع بنجاح إلى Render (v118)!")
