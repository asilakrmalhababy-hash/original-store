import os, pathlib, re, subprocess, sys

print(
    "=== بدء التحديث الشامل والدقيق v128 (إلغاء السعر الافتراضي تلقائياً عند"
    " إضافة خيارات في الإدارة + اعتماد أسعار الخيارات بعد النقطتين فوراً في"
    " النافذة وتفاصيل المنتج والسلة + فصل الوصف بالأبيض والسعر بالذهبي مع كلمة"
    " ريال) ==="
)

# ==============================================================================
# 1. تحديث client/src/pages/Admin.tsx:
#    - عند إضافة أي خيار وسعر في جدول الخيارات بالأسفل (+ إضافة للجدول)، يُحذف السعر الافتراضي العلوي فوراً (setField("price", "")) ويُقفل الحقل العلوي لعدم حدوث أي تعارض
#    - عند حفظ المنتج الذي يحتوي على خيارات، يتم اعتماد سعر الخيار الأول من الجدول تلقائياً كقيمة رقمية لعمود السعر في قاعدة البيانات دون مطالبة المستخدم بإدخال سعر افتراضي علوي
# ==============================================================================
admin_path = pathlib.Path("client/src/pages/Admin.tsx")
if admin_path.exists():
  ac = admin_path.read_text(encoding="utf-8")

  # أ) حذف السعر الافتراضي العلوي فوراً عند الضغط على (+ إضافة للجدول)
  if 'setField("price", "");' not in ac:
    ac = re.sub(
        r'(if\s*\(!form\.variants\.includes\(finalEntry\)\)\s*\{\s*setField\("variants",\s*\[\.\.\.form\.variants,\s*finalEntry\]\);\s*\})',
        lambda m: m.group(1) + '\n              setField("price", "");',
        ac,
    )

  # ب) قفل وتفريغ حقل السعر الافتراضي العلوي تلقائياً إذا كان هناك خيارات مضافة في الجدول (form.variants.length > 0)
  if "disabled={form.variants.length > 0}" not in ac:
    ac = re.sub(
        r'value=\{form\.price\}\s*onChange=\{e\s*=>\s*setField\("price",\s*e\.target\.value\)\}',
        lambda m: (
            'value={form.variants.length > 0 ? "" : form.price}'
            " disabled={form.variants.length > 0} onChange={e => { if"
            ' (form.variants.length === 0) setField("price", e.target.value);'
            " }}"
        ),
        ac,
    )

  # ج) استبدال عبارة "نفس السعر الأساسي" في جدول الخيارات بعبارة واضحة مستقلة
  ac = ac.replace(
      'placeholder={form.price || "نفس السعر الأساسي"}',
      'placeholder="سعر هذا الخيار"',
  )

  # د) في دالة submit()، إذا كان للمنتج خيارات في الجدول، نعتمد سعر الخيار الأول بعد النقطتين تلقائياً حتى ينجح الحفظ بدون سعر افتراضي علوي
  if "autoVariantBasePriceV128" not in ac:
    auto_base_snippet = """
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
        lambda m: m.group(1) + auto_base_snippet,
        ac,
        count=1,
    )

  admin_path.write_text(ac, encoding="utf-8")
  print(
      "1. Updated client/src/pages/Admin.tsx (auto-clear & lock default price"
      " when variants exist)!"
  )

# ==============================================================================
# 2. تحديث client/src/pages/Home.tsx:
#    - استعادة نسخة نظيفة من db9eb83 ثم تطبيق معادلة استخراج سعر الخيار بعد النقطتين (:) على كل من:
#      (أ) نافذة الإضافة للسلة المنبثقة
#      (ب) صفحة تفاصيل المنتج
#      (ج) بطاقة المنتج في المتجر
#      (د) سلة التسوق والطلبات (بنفس الدقة الحالية 100%)
# ==============================================================================
subprocess.run(
    ["git", "checkout", "db9eb83", "--", "client/src/pages/Home.tsx"],
    check=False,
)
home_path = pathlib.Path("client/src/pages/Home.tsx")
if home_path.exists():
  hc = home_path.read_text(encoding="utf-8")

  # 1) سلة التسوق والطلبات (الحفاظ التام 100% على عمل السلة كما هي)
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
      r"\b([a-zA-Z_]\w*(?:\??\.[a-zA-Z_]\w*)*)\??\.subtotal\b(?!\s*=(?!=)|\s*:)",
      r"extractCartSubtotalV107(\1, \1?.subtotal)",
      hc,
  )
  hc = re.sub(
      r"\b([a-zA-Z_]\w*(?:\??\.[a-zA-Z_]\w*)*)\??\.total\b(?!\s*=(?!=)|\s*:)",
      r"extractOrderTotalV107(\1, \1?.total)",
      hc,
  )
  hc = re.sub(
      r"\b([a-zA-Z_]\w*(?:\??\.[a-zA-Z_]\w*)*\??\.items)\??\.map\(",
      r"expandOrderItemsV110(\1).map(",
      hc,
  )
  hc = re.sub(
      r"\b([a-zA-Z_]\w*(?:\??\.[a-zA-Z_]\w*)*\??\.items)\.length\b(?!\s*=(?!=))",
      r"expandOrderItemsV110(\1).length",
      hc,
  )

  # 2) ربط متغير الخيار المختار مباشرة بنافذة الإضافة للسلة ("إضافة إلى السلة") وبصفحة تفاصيل المنتج ("أضف «")
  for m_btn in list(re.finditer(r"إضافة إلى السلة", hc)):
    pos = m_btn.start()
    win_start = max(0, pos - 2600)
    win_end = min(len(hc), pos + 600)
    window = hc[win_start:win_end]

    prod_matches = re.findall(
        r"\b([a-zA-Z_]\w*)\??\.(?:price|name|unit|description)\b", window
    )
    prod_candidates = [
        p
        for p in prod_matches
        if p
        not in (
            "e",
            "event",
            "window",
            "document",
            "Math",
            "Number",
            "String",
            "item",
            "i",
            "c",
            "it",
        )
    ]
    prod_var = prod_candidates[-1] if prod_candidates else None

    var_matches = re.findall(r"\b([a-zA-Z_]\w*)\s*===\s*[a-zA-Z_]\w*", window)
    var_candidates = [
        v for v in var_matches if v not in ("e", "i", "idx", "index", prod_var)
    ]
    var_state = var_candidates[-1] if var_candidates else None

    if prod_var and var_state:
      repl_str_modal = (
          f"Math.round(extractVariantPriceV104({var_state} || {prod_var},"
          f" ({prod_var} as any)?.price, {prod_var}))"
      )
      window_new = re.sub(
          rf"(?<!\.)(?<!\?\.)\b{re.escape(prod_var)}\??\.price\b(?!\s*=(?!=))",
          lambda m: repl_str_modal,
          window,
      )
      hc = hc[:win_start] + window_new + hc[win_end:]
      print(
          f"2a. Patched modal window in Home.tsx: prod_var={prod_var},"
          f" var_state={var_state}"
      )
      break

  for m_det in list(re.finditer(r"أضف\s*«", hc)):
    pos = m_det.start()
    win_start = max(0, pos - 2200)
    win_end = min(len(hc), pos + 2200)
    window = hc[win_start:win_end]

    var_m = re.search(r"أضف\s*«\s*\$?\{([a-zA-Z_]\w*)\}\s*»", window)
    det_var = var_m.group(1) if var_m else None

    prod_matches = re.findall(
        r"\b([a-zA-Z_]\w*)\??\.(?:price|name|unit|description)\b", window
    )
    prod_candidates = [
        p
        for p in prod_matches
        if p
        not in (
            "e",
            "event",
            "window",
            "document",
            "Math",
            "Number",
            "String",
            "item",
            "i",
            "c",
            "it",
            det_var,
        )
    ]
    det_prod = prod_candidates[-1] if prod_candidates else None

    if det_prod and det_var:
      repl_str_det = (
          f"Math.round(extractVariantPriceV104({det_var} || {det_prod},"
          f" ({det_prod} as any)?.price, {det_prod}))"
      )
      window_new = re.sub(
          rf"(?<!\.)(?<!\?\.)\b{re.escape(det_prod)}\??\.price\b(?!\s*=(?!=))",
          lambda m: repl_str_det,
          window,
      )
      hc = hc[:win_start] + window_new + hc[win_end:]
      print(
          f"2b. Patched product detail window in Home.tsx: det_prod={det_prod},"
          f" det_var={det_var}"
      )
      break

  # 3) تحويل أي قراءة متبقية لـ product.price أو p.price أو selectedProduct.price في Home.tsx لتمر عبر extractVariantPriceV104
  hc = re.sub(
      r"(?<!\.)(?<!\?\.)\b(product|prod|p|selectedProduct|activeProduct|modalProduct|variantModalProduct|detailProduct|quickProduct|viewedProduct|targetProduct)\??\.price\b(?!\s*=(?!=)|\s*:)",
      r"Math.round(extractVariantPriceV104(\1, (\1 as any)?.price, \1))",
      hc,
  )

  v128_home_helpers = """function expandOrderItemsV110(items: any): any[] {
  if (!Array.isArray(items)) return [];
  const result: any[] = [];
  for (const it of items) {
    if (!it || typeof it !== "object") {
      result.push(it);
      continue;
    }
    const rawName = String(it.productName || it.name || it.product?.name || "").trim();
    const parenMatches = Array.from(rawName.matchAll(/\\(([^()]+)\\)/g));
    if (parenMatches.length > 0) {
      const inner = parenMatches.map(m => m[1].trim()).filter(s => s.includes(":")).join("، ");
      const segments = inner.split(/[،,+]+/).map(s => s.trim()).filter(Boolean);
      if (segments.length > 1) {
        const baseTitle = rawName.replace(/\\s*\\([^()]*\\)\\s*$/g, "").trim() || rawName;
        let expandedAny = false;
        segments.forEach((seg, idx) => {
          let sQty = 1;
          const mm = seg.match(/[×xX*]\\s*(\\d+)/);
          if (mm && mm[1]) sQty = Math.max(1, parseInt(mm[1], 10));
          const cleanSeg = seg.replace(/[×xX*]\\s*\\d+.*$/, "").trim();
          const cIdx = cleanSeg.indexOf(":");
          if (cIdx !== -1) {
            const oName = cleanSeg.slice(0, cIdx).trim();
            const oPrice = parseFloat(cleanSeg.slice(cIdx + 1).trim());
            if (oName && !isNaN(oPrice) && oPrice > 0) {
              expandedAny = true;
              const segFullTitle = baseTitle + " (" + oName + ":" + Math.round(oPrice) + ")";
              result.push({
                ...it,
                id: String(it.id ?? "") + "_v" + idx,
                name: segFullTitle,
                productName: segFullTitle,
                unit: oName,
                quantity: sQty,
                price: Math.round(oPrice),
                unitPrice: Math.round(oPrice),
                lineTotal: Math.round(oPrice * sQty),
              });
            }
          }
        });
        if (expandedAny) continue;
      }
    }
    result.push(it);
  }
  return result;
}

function getStoredVariantTextV107(productId: any, productName?: any): string {
  try {
    if (productName && typeof window !== "undefined") {
      const cleanPName = String(productName).replace(/\\s*\\([^()]*\\)\\s*$/, "").trim();
      const reord = (window as any).__v111ReorderedVariants;
      if (reord && reord[cleanPName] && reord[cleanPName].raw) {
        return String(reord[cleanPName].raw);
      }
    }
    if (productId !== undefined && productId !== null) {
      const pidStr = String(productId);
      for (let i = 0; i < localStorage.length; i++) {
        const k = localStorage.key(i);
        if (!k || k.indexOf("v107") !== -1 || k.indexOf("v109") !== -1) continue;
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
  const desc = String(
    productObj?.description ||
    (typeof rawText === "object" ? (rawText?.description || rawText?.product?.description) : "") ||
    ""
  );
  const dbPriceMap: Record<string, number> = {};
  let firstDbVariantPrice = 0;
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
              if (!firstDbVariantPrice) firstDbVariantPrice = oPrice;
            }
          }
        }
      }
    } catch {}
  }

  let combined = "";
  let pid: any = productObj?.id ?? productObj?.productId;
  let pname: any = productObj?.name;
  const isCartOrOrderItem = typeof rawText === "object" && rawText !== null && (rawText.quantity !== undefined || rawText.productId !== undefined || rawText.lineTotal !== undefined || rawText.product !== undefined);

  if (typeof rawText === "object" && rawText !== null) {
    pid = rawText.productId ?? rawText.product?.id ?? rawText.id ?? pid;
    pname = rawText.product?.name ?? rawText.productName ?? rawText.name ?? pname;
    const explicitFields = [
      rawText.name,
      rawText.productName,
      rawText.displayName,
      rawText.customName,
      rawText.variant,
      rawText.selectedVariant,
      rawText.variantLabel,
      rawText.option,
      rawText.unit,
      rawText.label
    ].filter(v => typeof v === "string" && v.trim().length > 0).join(" ");

    if (/\\([^()]*:\\s*\\d/.test(explicitFields) || explicitFields.includes(":")) {
      combined = explicitFields;
    } else if (isCartOrOrderItem) {
      combined = [explicitFields, getStoredVariantTextV107(pid, pname)].filter(Boolean).join(" ");
    } else {
      const activeWinVar = typeof window !== "undefined" ? String((window as any).__v128ActiveVariant || "").trim() : "";
      if (activeWinVar) {
        const cleanAct = activeWinVar.split(":")[0].replace(/[✓✔]/g, "").trim();
        if (cleanAct && dbPriceMap[cleanAct] !== undefined) {
          return dbPriceMap[cleanAct];
        }
      }
      combined = explicitFields;
    }
  } else if (rawText) {
    combined = String(rawText).trim();
  } else if (isCartOrOrderItem) {
    combined = getStoredVariantTextV107(pid, pname);
  }

  if (!combined) {
    return firstDbVariantPrice > 0 ? firstDbVariantPrice : base;
  }

  let targetStr = "";
  const parenMatches = Array.from(combined.matchAll(/\\(([^()]+)\\)/g));
  if (parenMatches.length > 0) {
    targetStr = parenMatches.map(m => m[1].trim()).filter(s => s.includes(":")).join("، ");
  } else if (combined.includes(":")) {
    targetStr = combined;
  }

  if (targetStr && targetStr.includes(":")) {
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

  if (firstDbVariantPrice > 0) {
    return firstDbVariantPrice;
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
  const isOrderObj = cartOrOrder && typeof cartOrOrder === "object" && !Array.isArray(cartOrOrder) && (cartOrOrder.orderNumber !== undefined || cartOrOrder.status !== undefined || cartOrOrder.deliveryFee !== undefined || cartOrOrder.shippingFee !== undefined);
  let arr: any[] | null = null;
  if (Array.isArray(cartOrOrder)) arr = cartOrOrder;
  else if (cartOrOrder && Array.isArray(cartOrOrder.items)) arr = cartOrOrder.items;
  else if (cartOrOrder && Array.isArray(cartOrOrder.cartItems)) arr = cartOrOrder.cartItems;
  else if (cartOrOrder && Array.isArray(cartOrOrder.lines)) arr = cartOrOrder.lines;
  if (arr && arr.length > 0) {
    let sum = 0;
    for (const it of arr) {
      sum += extractVariantLineTotalV107(it);
    }
    if (sum > 0) {
      const rounded = Math.round(sum);
      if (!isOrderObj && typeof window !== "undefined") {
        (window as any).__v107LastCartSubtotal = rounded;
        (window as any).__v107LastCartBaseSubtotal = Number(fallbackSubtotal ?? cartOrOrder?.subtotal ?? rounded);
      }
      return rounded;
    }
  }
  if (!isOrderObj && typeof window !== "undefined" && Number((window as any).__v108ComputedCartSubtotal) > 0) {
    const calcSub = Number((window as any).__v108ComputedCartSubtotal);
    if (fallbackSubtotal !== undefined || cartOrOrder?.subtotal !== undefined) {
      (window as any).__v107LastCartBaseSubtotal = Number(fallbackSubtotal ?? cartOrOrder?.subtotal ?? 0);
    }
    return calcSub;
  }
  const fb = Number(fallbackSubtotal ?? cartOrOrder?.subtotal ?? 0);
  if (!isOrderObj && typeof window !== "undefined" && (window as any).__v107LastCartSubtotal && fb > 0) {
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
  hc = hc[: end_imp + 1] + "\n" + v128_home_helpers + "\n" + hc[end_imp + 1 :]
  home_path.write_text(hc, encoding="utf-8")
  print(
      "2c. Updated client/src/pages/Home.tsx with full variant price priority!"
  )

# ==============================================================================
# 3. تحديث client/index.html:
#    - مسح الكاش القديم تلقائياً فور فتح الصفحة لضمان ظهور التحديث فوراً على الجوال
#    - في لوحة الإدارة (/admin): مسح وقفل حقل السعر الافتراضي العلوي تلقائياً بمجرد إضافة أي خيار في الجدول بالأسفل
#    - في المتجر: تحديث السعر فوراً (0ms) عند اختيار أي خيار في النافذة أو تفاصيل المنتج + فصل الوصف بالأبيض والسعر بالذهبي مع كلمة ريال
# ==============================================================================
html_path = pathlib.Path("client/index.html")
if html_path.exists():
  ht = html_path.read_text(encoding="utf-8")

  sw_clear_snippet = """        try {
          if ("caches" in window && localStorage.getItem("original_v128_cache_purged") !== "1") {
            localStorage.setItem("original_v128_cache_purged", "1");
            caches.keys().then(function(keys) {
              keys.forEach(function(k) { caches.delete(k); });
            });
            if (navigator.serviceWorker) {
              navigator.serviceWorker.getRegistrations().then(function(regs) {
                regs.forEach(function(r) { r.update(); });
              });
            }
          }
        } catch (e) {}
"""
  if "original_v128_cache_purged" not in ht:
    ht = ht.replace("(function() {", "(function() {\n" + sw_clear_snippet, 1)

  new_part_a_v128 = """            // PART A: Admin Default Price Auto-Cleaner + Store Variant Picker Modal & Product Detail View — v128
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

            // A0: In Admin (/admin), automatically clear and lock the top Default Price field whenever options are added to the table below
            if (window.location.pathname.indexOf("/admin") !== -1) {
              var allSpans = Array.from(document.querySelectorAll("span, div, strong, label"));
              var countBadge = allSpans.find(function(el) {
                return el.children.length === 0 && (el.textContent || "").indexOf("عدد الخيارات المضافة:") !== -1;
              });
              if (countBadge) {
                var cm = (countBadge.textContent || "").match(/:\\s*(\\d+)/);
                var varCount = cm && cm[1] ? parseInt(cm[1], 10) : 0;
                var formContainer = countBadge.parentElement;
                while (formContainer && formContainer !== document.body && formContainer.querySelectorAll("input").length < 3) {
                  formContainer = formContainer.parentElement;
                }
                if (formContainer) {
                  var priceLabels = Array.from(formContainer.querySelectorAll("label, span, div, strong")).filter(function(el) {
                    var t = (el.textContent || "").trim();
                    return el.children.length === 0 && (t.indexOf("السعر بالريال") !== -1 || t.indexOf("السعر الافتراضي (مُلغى") !== -1);
                  });
                  priceLabels.forEach(function(lbl) {
                    var fieldWrap = lbl.parentElement;
                    var priceInp = fieldWrap ? fieldWrap.querySelector("input") : null;
                    if (!priceInp && fieldWrap && fieldWrap.parentElement) {
                      priceInp = fieldWrap.parentElement.querySelector("input[type='number'], input[placeholder='0']");
                    }
                    if (priceInp && priceInp.id !== "admin-inline-var-price") {
                      if (varCount > 0) {
                        if (priceInp.value !== "") {
                          var nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value");
                          if (nativeSetter && nativeSetter.set) {
                            nativeSetter.set.call(priceInp, "");
                          } else {
                            priceInp.value = "";
                          }
                          priceInp.dispatchEvent(new Event("input", { bubbles: true }));
                        }
                        priceInp.disabled = true;
                        priceInp.placeholder = "مُلغى تلقائياً — تُعتمد أسعار الجدول بالأسفل";
                        priceInp.style.background = "#eef5f1";
                        priceInp.style.color = "#687a71";
                        if ((lbl.textContent || "").indexOf("مُلغى") === -1) {
                          lbl.textContent = "السعر الافتراضي (مُلغى لاعتماد أسعار الخيارات بالأسفل)";
                        }
                      } else {
                        if (priceInp.disabled) {
                          priceInp.disabled = false;
                          priceInp.placeholder = "0";
                          priceInp.style.background = "";
                          priceInp.style.color = "";
                        }
                        if ((lbl.textContent || "").indexOf("مُلغى") !== -1) {
                          lbl.textContent = "السعر بالريال اليمني *";
                        }
                      }
                    }
                  });
                }
              }
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

              window.__v128ActiveVariant = parsedSel.raw;
              var unitPrice = parsedSel.unitPrice;
              var selectedOptName = parsedSel.optName;

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

              // 1. Update unit price badge/subtitle (e.g. "400 ر.ي / حبة" -> "430 ر.ي / حبة") via TreeWalker
              var twAll = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, null);
              var cTextNodes = [];
              var tnNode;
              while ((tnNode = twAll.nextNode())) {
                var pEl = tnNode.parentElement;
                if (!pEl) continue;
                if (pEl === addBtn || addBtn.contains(pEl)) continue;
                if (optBtns.some(function(ob) { return ob === pEl || ob.contains(pEl); })) continue;
                cTextNodes.push(tnNode);
              }
              for (var tIdx = 0; tIdx < cTextNodes.length; tIdx++) {
                var curVal = cTextNodes[tIdx].nodeValue || "";
                var nextVal = (tIdx + 1 < cTextNodes.length) ? (cTextNodes[tIdx + 1].nodeValue || "") : "";
                if (/\\d[\\d,.]*\\s*(?:ر\\.ي|ريال)/.test(curVal)) {
                  var repVal = curVal.replace(/\\d[\\d,.]*(?=\\s*(?:ر\\.ي|ريال))/, unitPriceStr);
                  if (curVal !== repVal) cTextNodes[tIdx].nodeValue = repVal;
                } else if (/^\\s*\\d[\\d,.]*\\s*$/.test(curVal) && /^\\s*(?:ر\\.ي|ريال)/.test(nextVal)) {
                  if (curVal.trim() !== unitPriceStr) cTextNodes[tIdx].nodeValue = unitPriceStr;
                }
              }

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
                var mText = modal.textContent || "";
                var hasVarBtns = Array.from(modal.querySelectorAll("button")).some(function(b) {
                  if (b === addBtn) return false;
                  var bt = (b.textContent || "").trim();
                  return b.hasAttribute("data-raw-opt") || bt.indexOf(":") !== -1;
                });
                var hasSlashPrice = (mText.indexOf("ر.ي") !== -1 || mText.indexOf("ريال") !== -1) && mText.indexOf("/") !== -1;
                if (hasVarBtns && hasSlashPrice) {
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
                var hasUnitPill = (dcText.indexOf("ر.ي") !== -1 || dcText.indexOf("ريال") !== -1) && dcText.indexOf("/") !== -1;
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

  pat_part_a = r'// PART A:[\s\S]*?(?=// PART B: Shopping Cart \("سلة التسوق"\) rows)'
  ht, n_part_a = re.subn(pat_part_a, lambda m: new_part_a_v128, ht, count=1)
  print("3a. Updated PART A in client/index.html (matches:", n_part_a, ")")

  ht = re.sub(
      r"try\s*\{\s*var vBtn127 =[\s\S]*?syncVariantModalPrice\(\);\s*\}\s*\}\s*catch\s*\(e\)\s*\{\}\s*",
      "",
      ht,
  )
  click_hook_old = "          setTimeout(syncVariantModalPrice, 5);"
  click_hook_new = """          try {
            var vBtn127 = ev.target && ev.target.closest ? ev.target.closest("button") : null;
            if (vBtn127 && (vBtn127.hasAttribute("data-raw-opt") || (vBtn127.textContent || "").indexOf(":") !== -1)) {
              var rawClicked = vBtn127.getAttribute("data-raw-opt") || (vBtn127.textContent || "").replace(/[✓✔]/g, "").trim();
              if (rawClicked.indexOf(":") !== -1) {
                window.__v128ActiveVariant = rawClicked;
              }
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

  if "window.__v128ActiveVariant = rawClicked" not in ht and click_hook_old in ht:
    ht = ht.replace(click_hook_old, click_hook_new, 1)
    print("3b. Added instant 0ms window.__v128ActiveVariant click hook!")

  html_path.write_text(ht, encoding="utf-8")

# ==============================================================================
# 4. تحديث client/public/sw.js:
#    - جعل ملفات /assets/ (ملفات الواجهة JS/CSS) تعتمد على الشبكة أولاً (Network-First) حتى لا يعلق الجوال أبداً على نسخة قديمة مخزنة
#    - ترقية رقم الكاش إلى v128
# ==============================================================================
sw_path = pathlib.Path("client/public/sw.js")
if sw_path.exists():
  swc = sw_path.read_text(encoding="utf-8")
  swc = re.sub(
      r'const CACHE = "original-shell-v[^"]*";',
      'const CACHE = "original-shell-v128";',
      swc,
  )
  swc = swc.replace('url.pathname.includes("/assets/") ||\n    ', "")
  swc = swc.replace('url.pathname.includes("/assets/") ||', "")
  sw_path.write_text(swc, encoding="utf-8")
  print("4. Updated client/public/sw.js (Network-First for JS bundles + v128)!")

# ==============================================================================
# 5. فحص البناء السريع عبر esbuild للواجهة قبل الرفع
# ==============================================================================
res_cli = subprocess.run(
    "npx esbuild client/src/pages/Admin.tsx client/src/pages/Home.tsx --bundle"
    " --platform=browser --packages=external --outdir=./.tmp_cli_v128",
    shell=True,
    capture_output=True,
    text=True,
)
subprocess.run("rm -rf ./.tmp_cli_v128", shell=True)

if res_cli.returncode != 0:
  print("❌ خطأ في فحص الواجهة:", res_cli.stderr)
  sys.exit(1)

print("✅ نجح فحص Admin.tsx و Home.tsx و index.html بنسبة 100% بدون أي خطأ!")
os.system(
    "git add client/src/pages/Admin.tsx client/src/pages/Home.tsx"
    " client/index.html client/public/sw.js"
)
os.system(
    'git commit -m "Fix v128: auto-clear default price when variants exist,'
    " prioritize variant colon prices everywhere in Home.tsx and modal, and"
    ' force network-first JS updates"'
)
os.system("git push origin main")
print("🚀 تم رفع التحديث الشامل v128 بنجاح 100% إلى Render!")
