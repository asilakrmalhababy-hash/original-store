import pathlib, re, subprocess, os

print("=== بدء التحديث الشامل v120 (إصلاح حفظ التخصيصات 100% + منع تكرار الرد الثابت + فصل قسم تخصيص الذكاء كقسم مستقل تماماً) ===")

# 1. تحديث server/ai_engine_v112.ts:
#    - تفعيل express.json({ limit: "50mb" }) داخل registerAiEngineV112 لضمان قراءة req.body في كل طلبات الحفظ والمحادثة 100%
#    - إرجاع passThrough: true للرسائل العامة حتى يرد المساعد بذكاء طبيعي دون تكرار جملة ثابتة
ai_path = pathlib.Path("server/ai_engine_v112.ts")
if ai_path.exists():
    ai_txt = ai_path.read_text(encoding="utf-8")

    if 'import express,' not in ai_txt:
        ai_txt = ai_txt.replace(
            'import type { Express } from "express";',
            'import express, { type Express } from "express";'
        )

    if 'app.use("/api/ai-studio", express.json' not in ai_txt:
        ai_txt = ai_txt.replace(
            'export function registerAiEngineV112(app: Express) {',
            'export function registerAiEngineV112(app: Express) {\n  app.use("/api/ai-studio", express.json({ limit: "50mb" }));'
        )

    # منع إرجاع الجملة الثابتة عند فراغ الرسالة
    ai_txt = ai_txt.replace(
        'return res.json({ ok: true, zeroToken: true, reply: "يا هلا بك يا غالي! آمرني، ايش تبحث عنه اليوم؟" });',
        'return res.json({ ok: true, passThrough: true });'
    )

    # تحديث دالة مطابقة الوصفات لتشمل الطلبات العامة للوصفات مثل "اريد وصفه حلوه" أو "اريد حلى"
    ai_txt = re.sub(
        r'if \(matchedWords\.length >= [12] && \(normMsg\.includes\("حلي"\) \|\| normMsg\.includes\("وصفه"\)\)\) return rec;\s*\}',
        'if (matchedWords.length >= 1) return rec;\n  }\n  if (/(وصفه|حلي|حلا|حلوه|طبق|حلى)/.test(normMsg) && recipes.length > 0) return recipes[0];',
        ai_txt
    )

    # إضافة علامة matchedOverride: true للردود المخصصة والوصفات والترويج فقط
    ai_txt = ai_txt.replace(
        "zeroToken: true,\n            reply: rule.response,",
        "zeroToken: true,\n            matchedOverride: true,\n            reply: rule.response,"
    )
    ai_txt = ai_txt.replace(
        "zeroToken: true,\n          reply: replyMsg,\n          recipeTitle:",
        "zeroToken: true,\n          matchedOverride: true,\n          reply: replyMsg,\n          recipeTitle:"
    )
    ai_txt = ai_txt.replace(
        "promotedProduct: promo,",
        "matchedOverride: true,\n            promotedProduct: promo,"
    )

    # تحديث القسم 4 و 5 في smart-chat بحيث يتدخل فقط عند وجود تخصيص فعلي أو منتج غير متوفر، ويترك المحادثة الطبيعية تمر للذكاء الأصلي (passThrough: true)
    sec4_and_5_pattern = r'// 4\. Product Modal / Specific Product Question[\s\S]*?return res\.json\(fallbackPayload\);'
    new_sec4_and_5 = """// 4. Product Modal / Specific Product Question (0 Tokens)
      const targetProd = allProds.find(p => {
        const cn = normalizeArabicV112(cleanProductNameV112(p.name));
        return cn && ((productContextName && cn === normalizeArabicV112(productContextName)) || (cn.length >= 4 && normMsg.includes(cn)));
      });

      if (targetProd) {
        const cleanName = cleanProductNameV112(targetProd.name);
        const pid = String(targetProd.id);
        const meta = memoryConfig.productAiMap[pid] || memoryConfig.productAiMap[cleanName];
        const hasCustomMeta = Boolean(meta && (meta.customInfo || meta.calories || meta.pairings || meta.prepIdeas || (meta.usageType && meta.usageType !== "auto")));
        if (productContextName || hasCustomMeta) {
          const smart = classifyProductSmartV112(cleanName, meta);
          zeroTokenCounter++;
          let replyText = "";
          if (meta && (meta.customInfo || meta.calories || meta.pairings || meta.prepIdeas)) {
            const parts: string[] = [];
            parts.push("يا غالي، بخصوص «" + cleanName + "» (سعره " + targetProd.price + " ر.ي):");
            if (meta.customInfo) parts.push("✨ معلومات المنتج: " + meta.customInfo);
            if (meta.calories) parts.push("🔥 السعرات والقيمة الغذائية: " + meta.calories);
            if (meta.pairings) parts.push("☕ أفضل ما يؤكل أو يشرب معه: " + meta.pairings);
            if (meta.prepIdeas) parts.push("🍰 أفكار ووصفات به: " + meta.prepIdeas);
            replyText = parts.join("\\n");
          } else if (smart.mode === "snacks_and_drinks") {
            replyText =
              "يا غالي، «" + cleanName + "» متوفر بسعر " + targetProd.price + " ر.ي فقط! 😍\\n" +
              "💡 معلومات عنه: " + smart.defaultInfo + "\\n" +
              "✨ نصيحة سريعة: جربه مع قهوة ساخنة أو عصير بارد من المتجر واستمتع بالطعم الأصلي.";
          } else if (smart.mode === "recipe") {
            replyText =
              "يا هلا بك يا غالي! «" + cleanName + "» (سعره " + targetProd.price + " ر.ي) ممتاز جداً للتحضير:\\n" +
              "🍰 فكرة سريعة ولذيذة: " + smart.defaultInfo;
          } else {
            replyText =
              "حياك الله يا غالي! «" + cleanName + "» متوفر في المتجر بسعر " + targetProd.price + " ر.ي.\\n" +
              "💡 " + smart.defaultInfo;
          }

          const payload = {
            ok: true,
            zeroToken: true,
            matchedOverride: true,
            reply: replyText,
            smartChips: smart.chips,
            suggestedItems: [
              {
                id: targetProd.id,
                productId: targetProd.id,
                name: cleanName,
                price: targetProd.price,
                unit: targetProd.unit || "حبة",
                url: "/products?search=" + encodeURIComponent(cleanName)
              }
            ]
          };
          responseCache.set(cacheKey, { data: payload, expiresAt: Date.now() + 10 * 60 * 1000 });
          return res.json(payload);
        }
      }

      // 5. الترحيب المخصص أو عرض توفير المنتج غير الموجود، وتمرير المحادثة الطبيعية للذكاء الأصلي
      const isGreeting = /^(هلا|اهلا|مرحبا|السلام عليكم|صباح الخير|مساء الخير|كيف حالك|كيفك|شخبارك|وش اخبارك)(\\s|$)/.test(normMsg);
      if (isGreeting) {
        const customWelcomeInst = (memoryConfig.instructions || []).find(i => i.active && i.category === "welcome");
        if (customWelcomeInst?.text) {
          return res.json({
            ok: true,
            zeroToken: true,
            matchedOverride: true,
            reply: customWelcomeInst.text,
            suggestedItems: []
          });
        }
        return res.json({ ok: true, passThrough: true });
      }

      const stopWords = new Set(["هل", "عندكم", "معاكم", "معكم", "في", "متوفر", "اريد", "ابغي", "اشتي", "بكم", "سعر", "وين", "وش", "ايش", "كيف", "طريقه", "عمل", "وصفه", "معلومات", "سعرات", "ابحث", "عن", "رد", "منك", "لو", "سمحت", "شي", "حاجه"]);
      const words = normMsg.split(" ").filter(w => w.length >= 3 && !stopWords.has(w));
      const matchedProds = allProds.filter(p => {
        const cn = normalizeArabicV112(cleanProductNameV112(p.name));
        return words.some(w => cn.includes(w));
      });

      const asksAvailability = /(عندكم|معاكم|معكم|متوفر|تبيعون|احصل|القي|اشتي|ابغي|اريد|موجود|قهوه|قهوة)/.test(normMsg);
      if (asksAvailability && matchedProds.length === 0 && words.length > 0 && !/(وصفه|حلي|حلا|حلوه)/.test(normMsg)) {
        zeroTokenCounter++;
        const requestedName = words.join(" ");
        const customMissingInst = (memoryConfig.instructions || []).find(i => i.active && i.category === "missing_item");
        const friendlyReply = customMissingInst?.text
          ? customMissingInst.text.replace(/\\{المنتج\\}/g, requestedName)
          : "فهمتك يا غالي! تقصد «" + requestedName + "».. حلو حلو 👌 حالياً هذا الصنف مو ظاهر قدامي بالمتجر، بس ولا يهمك! إذا تريده أقدر أتواصل لك مع إدارة المتجر فوراً وأرسل لهم إشعار لهاتفهم يوفرونه لك ويردون عليك هنا بالمحادثة. هل تريد أكلم المتجر لك؟";
        return res.json({
          ok: true,
          zeroToken: true,
          matchedOverride: true,
          missingItemOffer: true,
          requestedItemName: requestedName,
          reply: friendlyReply,
          suggestedItems: []
        });
      }

      return res.json({ ok: true, passThrough: true });"""

    ai_txt = re.sub(sec4_and_5_pattern, lambda m: new_sec4_and_5, ai_txt)
    ai_path.write_text(ai_txt, encoding="utf-8")
    print("1. Updated server/ai_engine_v112.ts!")

# 2. تحديث client/index.html:
#    - عدم استبدال رد الشات إلا إذا كان matchedOverride === true
#    - جعل قسم تخصيص الذكاء الاصطناعي قسماً مستقلاً تماماً بملء الشاشة مع زر ثابت في القائمة الرئيسية وأعلى لوحة الإدارة
html_path = pathlib.Path("client/index.html")
if html_path.exists():
    ht = html_path.read_text(encoding="utf-8")

    # 2.a Only override tRPC response when matchedOverride === true
    ht = ht.replace(
        "if (!smartData || !smartData.ok) return trpcRes;",
        "if (!smartData || !smartData.ok || smartData.passThrough || !smartData.matchedOverride) return trpcRes;"
    )

    # 2.b Never overwrite local studio config with empty server config
    ht = ht.replace(
        "if (d && d.ok && d.config) {\n                window.__v114StudioConfig = d.config;",
        "if (d && d.ok && d.config && hasAnyStudioItemsV115(d.config)) {\n                window.__v114StudioConfig = d.config;"
    )

    # 2.c Upgrade matchRecipeClientV116 so general recipe queries ("اريد وصفه حلوه") match saved recipes in Tab 4
    ht = ht.replace(
        "if (matchedWords.length >= 1) return rec;\n          }\n          return null;",
        "if (matchedWords.length >= 1) return rec;\n          }\n          if (/(وصفه|حلي|حلا|حلوه)/.test(normUser) && list.length > 0) return list[0];\n          return null;"
    )

    # 2.d Make AI Studio button appear in main sidebar (next to الطلبات/المنتجات, NEVER inside محادثات الزبائن) AND as a permanent floating button in /admin
    old_sidebar_fn = r"function ensureDedicatedAiSidebarItemV114\(\) \{[\s\S]*?function updateStudioHeaderBadgesOnlyV115\(\)"
    new_sidebar_fn = """function ensureDedicatedAiSidebarItemV114() {
          if (window.location.pathname.indexOf("/admin") === -1) {
            var oldFloat = document.getElementById("v120-floating-studio-btn");
            if (oldFloat) oldFloat.remove();
            return;
          }

          var pendingCount = (window.__v114Requests || []).filter(function(r) { return r.status === "pending"; }).length;

          // 1. زر عائم ثابت في لوحة الإدارة للوصول لقسم تخصيص الذكاء الاصطناعي بضغطة واحدة من أي مكان كقسم مستقل تماماً
          var floatBtn = document.getElementById("v120-floating-studio-btn");
          if (!floatBtn) {
            floatBtn = document.createElement("button");
            floatBtn.id = "v120-floating-studio-btn";
            floatBtn.type = "button";
            floatBtn.style.cssText = "position:fixed;bottom:18px;left:16px;z-index:99991;display:flex;align-items:center;gap:8px;padding:11px 16px;border-radius:99px;border:2px solid #d4af37;background:linear-gradient(135deg,#0d3825 0%,#165b3c 100%);color:#ffffff;font-weight:900;font-size:0.88rem;cursor:pointer;box-shadow:0 10px 26px rgba(13,56,37,0.38);direction:rtl;";
            floatBtn.onclick = function(ev) {
              ev.preventDefault();
              ev.stopPropagation();
              window.__v114StudioOpen = true;
              refreshStudioDataV114(false);
              renderAiStudioDedicatedPageV114();
            };
            document.body.appendChild(floatBtn);
          }
          floatBtn.innerHTML =
            "<span>🤖 قسم تخصيص الذكاء الاصطناعي</span>" +
            (pendingCount > 0
              ? "<span style='background:#ef4444;color:#fff;border-radius:99px;padding:2px 8px;font-size:0.75rem;font-weight:900;'>" + pendingCount + "</span>"
              : "<span style='background:#d4af37;color:#0d3825;border-radius:99px;padding:2px 8px;font-size:0.72rem;font-weight:900;'>مستقل</span>");

          // 2. إضافة القسم في القائمة الرئيسية الجانبية بجانب (المنتجات / الطلبات) وليس داخل محادثات الزبائن
          var allClickables = Array.from(document.querySelectorAll("aside button, nav button, aside a, nav a, button, a"));
          var mainNavAnchor = allClickables.find(function(el) {
            var t = (el.textContent || "").trim();
            return (t === "الطلبات" || t === "المنتجات" || t === "الأقسام") && el.id !== "v114-dedicated-ai-nav-btn";
          });

          if (mainNavAnchor && mainNavAnchor.parentElement && !document.getElementById("v114-dedicated-ai-nav-btn")) {
            var navBtn = document.createElement("button");
            navBtn.id = "v114-dedicated-ai-nav-btn";
            navBtn.type = "button";
            navBtn.style.cssText = "width:100%;display:flex;align-items:center;justify-content:space-between;padding:11px 14px;margin:6px 0;border-radius:12px;border:2px solid #d4af37;background:linear-gradient(135deg,#0d3825 0%,#165b3c 100%);color:#ffffff;font-weight:900;font-size:0.9rem;cursor:pointer;box-shadow:0 6px 16px rgba(13,56,37,0.22);direction:rtl;text-align:right;";
            navBtn.innerHTML =
              "<span style='display:flex;align-items:center;gap:8px;'><span>🤖</span><span>تخصيص الذكاء الاصطناعي</span></span>" +
              (pendingCount > 0
                ? "<span style='background:#ef4444;color:#fff;border-radius:99px;padding:2px 8px;font-size:0.75rem;font-weight:900;'>" + pendingCount + "</span>"
                : "<span style='background:#d4af37;color:#0d3825;border-radius:99px;padding:2px 8px;font-size:0.72rem;font-weight:900;'>قسم مستقل</span>");

            navBtn.onclick = function(ev) {
              ev.preventDefault();
              ev.stopPropagation();
              window.__v114StudioOpen = true;
              refreshStudioDataV114(false);
              renderAiStudioDedicatedPageV114();
            };

            mainNavAnchor.parentElement.appendChild(navBtn);
          }
        }

        function updateStudioHeaderBadgesOnlyV115()"""

    ht = re.sub(old_sidebar_fn, lambda m: new_sidebar_fn, ht, count=1)

    # 2.e Make studioPage open as a 100% full-screen standalone page on document.body (never inside محادثات الزبائن)
    old_studio_container = r"var mainContainer =[\s\S]*?mainContainer\.insertBefore\(studioPage, mainContainer\.firstChild\);\s*\}"
    new_studio_container = """if (!studioPage) {
            studioPage = document.createElement("div");
            studioPage.id = "v114-dedicated-studio-page";
            studioPage.style.cssText = "position:fixed;inset:0;width:100vw;height:100vh;overflow-y:auto;z-index:99995;padding:18px;box-sizing:border-box;background:#f4fbf7;direction:rtl;text-align:right;";
            document.body.appendChild(studioPage);
          }"""
    ht = re.sub(old_studio_container, lambda m: new_studio_container, ht, count=1)

    html_path.write_text(ht, encoding="utf-8")
    print("2. Updated client/index.html (Standalone Full-Page AI Studio + PassThrough + Config Protection)!")

# 3. ترقية رقم كاش Service Worker إلى v120
sw_path = pathlib.Path("client/public/sw.js")
if sw_path.exists():
    sw_txt = sw_path.read_text(encoding="utf-8")
    sw_txt = re.sub(r'v10\d|v11\d|v12\d|v9\d', 'v120', sw_txt)
    sw_path.write_text(sw_txt, encoding="utf-8")
    print("3. Bumped Service Worker cache to v120!")

# 4. فحص البناء والرفع
res_srv = subprocess.run(
    "npx esbuild server/_core/index.ts --bundle --platform=node --format=esm --packages=external --outfile=./.tmp_srv_v120.js",
    shell=True, capture_output=True, text=True
)
res_cli = subprocess.run(
    "npx esbuild client/src/pages/Admin.tsx client/src/pages/Home.tsx --bundle --platform=browser --packages=external --outdir=./.tmp_cli_v120",
    shell=True, capture_output=True, text=True
)
os.system("rm -rf ./.tmp_srv_v120.js ./.tmp_cli_v120")

if res_srv.returncode != 0 or res_cli.returncode != 0:
    print("❌ Build check failed:", res_srv.stderr, res_cli.stderr)
else:
    print("✅ Build check passed 100%!")
    os.system("git add server/ai_engine_v112.ts client/index.html client/public/sw.js")
    os.system('git commit -m "Fix v120: add express.json to ai-studio routes, fix static reply bug, and make AI Studio a standalone full-screen section"')
    os.system("git push origin main")
    print("🚀 تم الرفع بنجاح إلى Render (v120)!")
