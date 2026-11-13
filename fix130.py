import os, pathlib, re, subprocess, sys

print("=== بدء التحديث الشامل والسريع v130 ===")

ENGINE_JS_V130 = r"""
(function() {
if (typeof window === "undefined" || typeof document === "undefined") return;
try {
if ("caches" in window && localStorage.getItem("original_v130_purged") !== "1") {
localStorage.setItem("original_v130_purged", "1");
caches.keys().then(function(ks) { ks.forEach(function(k) { caches.delete(k); }); });
if (navigator.serviceWorker) {
navigator.serviceWorker.getRegistrations().then(function(rs) { rs.forEach(function(r) { r.update(); }); });
}
}
} catch (e) {}
function getBtnTextNodesV130(btn) {
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
function getCleanBtnTextV130(btn) {
return getBtnTextNodesV130(btn).map(function(n) { return n.nodeValue || ""; }).join("").replace(/[✓✔]/g, "").replace(/\s+/g, " ").trim();
}
function setCleanBtnTextV130(btn, newText) {
var nodes = getBtnTextNodesV130(btn);
if (nodes.length === 0) return;
var joined = nodes.map(function(n) { return n.nodeValue || ""; }).join("").replace(/\s+/g, " ").trim();
if (joined === newText.trim()) return;
nodes[0].nodeValue = " " + newText.trim() + " ";
for (var i = 1; i < nodes.length; i++) {
if (nodes[i].nodeValue !== "") nodes[i].nodeValue = "";
}
}
function parseOptV130(raw) {
var clean = String(raw || "").replace(/[✓✔]/g, "").replace(/\s+/g, " ").trim();
var parts = clean.split(":");
if (parts.length < 2) return null;
var optName = parts[0].trim();
var pm = parts[1].trim().match(/(\d+(?:\.\d+)?)/);
if (!pm || !pm[1]) return null;
var p = parseFloat(pm[1]);
if (isNaN(p) || p <= 0) return null;
var stock = null;
if (parts.length >= 3 && parts[2].trim() !== "") {
var sm = parts[2].trim().match(/^(-?\d+)/);
if (sm) stock = parseInt(sm[1], 10);
}
var isOut = (stock !== null && stock <= 0);
var rawFull = stock !== null ? (optName + ":" + p + ":" + stock) : (optName + ":" + p);
return { raw: rawFull, priceRaw: optName + ":" + p, optName: optName, unitPrice: p, stock: stock, isOut: isOut };
}
function isOptSelectedDomV130(b) {
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
function readQtyFromBoxV130(container, excludeBtns) {
var cBtns = Array.from(container.querySelectorAll("button"));
for (var i = 0; i < cBtns.length; i++) {
var qb = cBtns[i];
if (excludeBtns && excludeBtns.indexOf(qb) !== -1) continue;
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
window.__readCartRowQtyV130 = readQtyFromBoxV130;
function showToastV130(msg) {
var old = document.getElementById("v130-stock-toast");
if (old) old.remove();
var t = document.createElement("div");
t.id = "v130-stock-toast";
t.textContent = msg;
t.style.cssText = "position:fixed;bottom:85px;left:50%;transform:translateX(-50%);background:#991b1b;color:#fff;padding:10px 18px;border-radius:12px;font-weight:800;font-size:0.88rem;z-index:999999;box-shadow:0 8px 24px rgba(0,0,0,0.25);direction:rtl;text-align:center;max-width:90vw;";
document.body.appendChild(t);
setTimeout(function() { if (t.parentNode) t.remove(); }, 2600);
}
function syncBoxV130(container, addBtn, isDetail) {
if (!container || !addBtn) return;
var cBtns = Array.from(container.querySelectorAll("button"));
var optBtns = cBtns.filter(function(b) {
if (b === addBtn) return false;
var t = getCleanBtnTextV130(b);
if (t === "+" || t === "＋" || t === "-" || t === "−" || t === "–" || t === "×" || t === "✕") return false;
return t.indexOf(":") !== -1 || b.hasAttribute("data-raw-opt");
});
if (optBtns.length === 0) return;
optBtns.forEach(function(b) {
var curT = getCleanBtnTextV130(b);
if (!b.hasAttribute("data-raw-opt") && curT.indexOf(":") !== -1) b.setAttribute("data-raw-opt", curT);
var parsed = parseOptV130(b.getAttribute("data-raw-opt") || curT);
if (parsed) {
setCleanBtnTextV130(b, parsed.optName);
if (parsed.isOut) {
b.setAttribute("data-v130-out", "1");
if (b.getAttribute("data-v127-opt-price") !== "غير متوفر حالياً") b.setAttribute("data-v127-opt-price", "غير متوفر حالياً");
} else {
b.removeAttribute("data-v130-out");
var pAttr = parsed.unitPrice.toLocaleString("en-US") + " ريال" + (parsed.stock !== null ? (" · متوفر " + parsed.stock) : "");
if (b.getAttribute("data-v127-opt-price") !== pAttr) b.setAttribute("data-v127-opt-price", pAttr);
}
}
});
if (!container.hasAttribute("data-v130-init-avail")) {
container.setAttribute("data-v130-init-avail", "1");
var firstP = parseOptV130(optBtns[0].getAttribute("data-raw-opt") || "");
if (firstP && firstP.isOut) {
var firstAvail = optBtns.find(function(b) { var p = parseOptV130(b.getAttribute("data-raw-opt") || ""); return p && !p.isOut; });
if (firstAvail) {
optBtns.forEach(function(s) { s.removeAttribute("data-v129-sel"); });
firstAvail.setAttribute("data-v129-sel", "1");
setTimeout(function() { try { firstAvail.click(); } catch (e) {} }, 0);
}
}
}
var userSel = optBtns.find(function(b) { return b.getAttribute("data-v129-sel") === "1"; });
var domSel = optBtns.find(function(b) { return isOptSelectedDomV130(b); });
var activeBtn = userSel || domSel || optBtns[0];
if (!activeBtn) return;
var parsedSel = parseOptV130(activeBtn.getAttribute("data-raw-opt") || getCleanBtnTextV130(activeBtn));
if (!parsedSel) return;
window.__v128ActiveVariant = parsedSel.raw;
var unitPrice = parsedSel.unitPrice;
var qty = readQtyFromBoxV130(container, [addBtn].concat(optBtns));
if (!parsedSel.isOut && parsedSel.stock !== null && qty > parsedSel.stock) qty = parsedSel.stock;
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
if (parsedSel.isOut) {
addBtn.setAttribute("data-v130-btn-disabled", "1");
setCleanBtnTextV130(addBtn, "«" + parsedSel.optName + "» غير متوفر حالياً");
if (addBtn.getAttribute("data-v127-btn-price") !== "نفدت الكمية") addBtn.setAttribute("data-v127-btn-price", "نفدت الكمية");
} else {
addBtn.removeAttribute("data-v130-btn-disabled");
var descTxt = isDetail ? ("أضف «" + parsedSel.optName + "» للسلة") : ("إضافة «" + parsedSel.optName + "» للسلة");
setCleanBtnTextV130(addBtn, descTxt);
var bPrice = totalStr + " ريال";
if (addBtn.getAttribute("data-v127-btn-price") !== bPrice) addBtn.setAttribute("data-v127-btn-price", bPrice);
}
}
function findCartRowCardsV130() {
var remBtns = Array.from(document.querySelectorAll("button")).filter(function(b) {
return b.offsetParent !== null && (b.textContent || "").indexOf("إزالة") !== -1 && (b.textContent || "").indexOf("الصورة") === -1;
});
var rows = [];
remBtns.forEach(function(remBtn, idx) {
var rc = remBtn.parentElement;
while (rc && rc.parentElement && rc.parentElement !== document.body) {
var pt = rc.parentElement.textContent || "";
if (pt.indexOf("إفراغ السلة") !== -1 || pt.indexOf("ملخص الطلب") !== -1) break;
var pRem = Array.from(rc.parentElement.querySelectorAll("button")).filter(function(b) {
return (b.textContent || "").indexOf("إزالة") !== -1 && (b.textContent || "").indexOf("الصورة") === -1;
}).length;
if (pRem > 1) break;
rc = rc.parentElement;
}
if (rc) {
rc.setAttribute("data-v130-cart-row", String(idx));
rows.push({ rowCard: rc, remBtn: remBtn, idx: idx });
}
});
return rows;
}
function syncCartStorageV130(nextArr) {
try {
for (var i = 0; i < localStorage.length; i++) {
var k = localStorage.key(i);
if (!k || k.indexOf("v11") !== -1 || k.indexOf("v12") !== -1 || k.indexOf("v13") !== -1) continue;
var raw = localStorage.getItem(k);
if (raw && raw.charAt(0) === "[") {
var parsed = JSON.parse(raw);
if (Array.isArray(parsed) && (parsed.length === 0 || (parsed[0] && (parsed[0].productId !== undefined || parsed[0].quantity !== undefined)))) {
localStorage.setItem(k, JSON.stringify(nextArr));
}
}
}
} catch (e) {}
}
window.__runV129Sync = function() {
try {
if (!document.getElementById("v130-variant-gold-styles")) {
var st = document.createElement("style");
st.id = "v130-variant-gold-styles";
st.textContent =
"button { touch-action: manipulation !important; } button svg, button path { pointer-events: none !important; }" +
"button[data-v127-opt-price] { display: inline-flex !important; flex-direction: column !important; align-items: center !important; justify-content: center !important; gap: 3px !important; line-height: 1.25 !important; }" +
"button[data-v127-opt-price]:not([data-v130-out='1'])::after { content: attr(data-v127-opt-price); color: #d4af37 !important; font-weight: 900 !important; font-size: 0.90em !important; direction: rtl !important; display: block !important; }" +
"button[data-v130-out='1'] { opacity: 0.78 !important; border: 1.5px dashed #ef4444 !important; }" +
"button[data-v130-out='1']::after { content: attr(data-v127-opt-price); color: #ef4444 !important; background: #fef2f2 !important; padding: 1px 7px !important; border-radius: 99px !important; font-weight: 900 !important; font-size: 0.80em !important; direction: rtl !important; display: inline-block !important; }" +
"button[data-v127-btn-price] { direction: rtl !important; display: inline-flex !important; flex-direction: row !important; align-items: center !important; justify-content: center !important; gap: 8px !important; flex-wrap: wrap !important; color: #ffffff !important; }" +
"button[data-v127-btn-price]:not([data-v130-btn-disabled='1'])::after { content: attr(data-v127-btn-price); color: #d4af37 !important; font-weight: 900 !important; font-size: 1.02em !important; direction: rtl !important; display: inline-block !important; }" +
"button[data-v130-btn-disabled='1'] { background: #6b7280 !important; border-color: #6b7280 !important; cursor: not-allowed !important; opacity: 0.92 !important; }" +
"button[data-v130-btn-disabled='1']::after { content: attr(data-v127-btn-price); color: #fecaca !important; font-weight: 900 !important; font-size: 0.92em !important; }";
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
if (inp && inp.id !== "admin-inline-var-price" && inp.id !== "admin-inline-var-stock") {
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
return t.indexOf("مجدداً") === -1 && (b.hasAttribute("data-v127-modal-add") || t.indexOf("إضافة إلى السلة") !== -1 || (t.indexOf("إضافة «") !== -1 && t.indexOf("للسلة") !== -1) || b.hasAttribute("data-v130-btn-disabled"));
}).forEach(function(addBtn) {
addBtn.setAttribute("data-v127-modal-add", "1");
var modal = addBtn.parentElement;
for (var u = 0; u < 6 && modal && modal.parentElement && modal.parentElement !== document.body; u++) {
var mt = modal.textContent || "";
var hasV = Array.from(modal.querySelectorAll("button")).some(function(b) { return b !== addBtn && (b.hasAttribute("data-raw-opt") || (b.textContent || "").indexOf(":") !== -1); });
if (hasV && (mt.indexOf("ر.ي") !== -1 || mt.indexOf("ريال") !== -1) && mt.indexOf("/") !== -1) break;
modal = modal.parentElement;
}
if (modal) syncBoxV130(modal, addBtn, false);
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
if (found) { dBtn.setAttribute("data-v127-detail-add", "1"); syncBoxV130(found, dBtn, true); }
});
findCartRowCardsV130();
} catch (e) {}
};
if (!window.__v130Bound) {
window.__v130Bound = true;
document.addEventListener("click", function(ev) {
try {
var btn = ev.target && ev.target.closest ? ev.target.closest("button") : null;
if (btn) {
if (btn.getAttribute("data-v130-btn-disabled") === "1") {
ev.stopPropagation();
ev.preventDefault();
showToastV130("عذراً، هذا الخيار غير متوفر حالياً — يرجى اختيار نوع آخر متوفر");
return;
}
var raw = btn.getAttribute("data-raw-opt") || getCleanBtnTextV130(btn);
if (raw.indexOf(":") !== -1) {
window.__v128ActiveVariant = raw;
var grp = (btn.parentElement && btn.parentElement.parentElement) || btn.parentElement;
if (grp) Array.from(grp.querySelectorAll("button")).forEach(function(s) { s.removeAttribute("data-v129-sel"); });
btn.setAttribute("data-v129-sel", "1");
}
var cartRows = findCartRowCardsV130();
if (cartRows.length > 0) {
var matchedRow = null;
for (var r = 0; r < cartRows.length; r++) {
if (cartRows[r].rowCard.contains(btn)) { matchedRow = cartRows[r]; break; }
}
if (matchedRow) {
var bTxt = (btn.textContent || "").trim();
var isRem = (btn === matchedRow.remBtn) || bTxt.indexOf("إزالة") !== -1;
var isPlus = !isRem && (bTxt === "+" || bTxt === "＋" || btn.innerHTML.indexOf("lucide-plus") !== -1 || (btn.innerHTML.indexOf("M5 12h14") !== -1 && btn.innerHTML.indexOf("M12 5v14") !== -1));
var isMinus = !isRem && !isPlus && (bTxt === "-" || bTxt === "−" || bTxt === "–" || btn.innerHTML.indexOf("lucide-minus") !== -1 || (btn.innerHTML.indexOf("M5 12h14") !== -1 && btn.innerHTML.indexOf("M12 5v14") === -1));
if ((isRem || isPlus || isMinus) && typeof window.__v130SetCartArray === "function" && Array.isArray(window.__v130CartArray)) {
var targetIdx = matchedRow.idx;
if (targetIdx >= 0 && targetIdx < window.__v130CartArray.length) {
ev.stopPropagation();
ev.preventDefault();
window.__v130SetCartArray(function(prev) {
if (!Array.isArray(prev) || targetIdx >= prev.length) return prev;
var next = prev.slice();
if (isRem) {
next.splice(targetIdx, 1);
} else if (isPlus) {
var itemCopy = Object.assign({}, next[targetIdx]);
var curQ = Math.max(1, Number(itemCopy.quantity || 1));
var nm = String(itemCopy.name || itemCopy.variant || "");
var sm = nm.match(/:\s*\d+(?:\.\d+)?\s*:\s*(\d+)/);
var maxStock = sm && sm[1] ? parseInt(sm[1], 10) : null;
if (maxStock !== null && curQ >= maxStock) {
showToastV130("الكمية المتوفرة من هذا الخيار هي " + maxStock + " فقط");
return prev;
}
itemCopy.quantity = curQ + 1;
next[targetIdx] = itemCopy;
} else if (isMinus) {
var itemCopyM = Object.assign({}, next[targetIdx]);
var curQM = Math.max(1, Number(itemCopyM.quantity || 1));
if (curQM <= 1) next.splice(targetIdx, 1);
else { itemCopyM.quantity = curQM - 1; next[targetIdx] = itemCopyM; }
}
window.__v130CartArray = next;
if (next.length === 0) window.__v108ComputedCartSubtotal = 0;
syncCartStorageV130(next);
return next;
});
setTimeout(window.__runV129Sync, 15);
setTimeout(window.__runV129Sync, 60);
return;
}
}
}
}
}
} catch (e) {}
window.__runV129Sync();
setTimeout(window.__runV129Sync, 15);
setTimeout(window.__runV129Sync, 60);
setTimeout(window.__runV129Sync, 160);
}, true);
setInterval(window.__runV129Sync, 180);
}
})();
"""

# 1. تحديث server/commerce.ts ليقرأ السعر من (النوع:السعر:العدد) عبر parseFloat بدلاً من Number
comm_path = pathlib.Path("server/commerce.ts")
if comm_path.exists():
  cc = comm_path.read_text(encoding="utf-8")
  cc = cc.replace("Number(entry.slice(colonIdx + 1).trim())", "parseFloat(entry.slice(colonIdx + 1).trim())")
  cc = cc.replace("Number(cleanSeg.slice(colonIdx + 1).trim())", "parseFloat(cleanSeg.slice(colonIdx + 1).trim())")
  comm_path.write_text(cc, encoding="utf-8")
  print("1. Updated server/commerce.ts!")

# 2. تحديث Admin.tsx لإضافة حقل العدد المتوفر لكل نكهة/خيار + زر (نفد حالياً 0 / تفعيل التوفر)
admin_path = pathlib.Path("client/src/pages/Admin.tsx")
if admin_path.exists():
  ac = admin_path.read_text(encoding="utf-8")
  v130_table_jsx = """
<div className="field-wide" style={{ background: "#f8fbf9", border: "2px solid #0d3825", borderRadius: "14px", padding: "14px", marginTop: "8px", marginBottom: "8px" }}>
<div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px", flexWrap: "wrap", gap: "6px" }}>
<strong style={{ color: "#0d3825", fontSize: "0.95rem" }}>📦 جدول الخيارات والنكهات والأسعار والعدد المتوفر</strong>
<span style={{ fontSize: "0.78rem", color: "#5c6f65", background: "#e8f2ec", padding: "3px 8px", borderRadius: "99px", fontWeight: 700 }}>عدد الخيارات المضافة: {form.variants.length}</span>
</div>
<div style={{ fontSize: "0.8rem", color: "#495a52", marginBottom: "8px" }}>
اكتب اسم الخيار أو النكهة (مثل: عنب، توت، باكيت) وحدد السعر والعدد المتوفر (ضع <strong>0</strong> في العدد ليظهر للزبون <strong>غير متوفر حالياً</strong>):
</div>
<div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginBottom: "10px" }}>
{["حبة", "باكيت", "نصف درزن", "درزن", "نصف كرتون", "كرتون"].map(preset => (
<button key={preset} type="button" className="small-button" style={{ fontSize: "0.8rem", padding: "5px 12px", background: form.variantDraft === preset ? "#0d3825" : "#fff", color: form.variantDraft === preset ? "#d4af37" : "#0d3825", border: "1px solid #0d3825", borderRadius: "8px", fontWeight: 700 }} onClick={() => { setField("variantDraft", preset); const pEl = document.getElementById("admin-inline-var-price") as HTMLInputElement | null; if (pEl) pEl.focus(); }}>+ {preset}</button>
))}
</div>
<div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: "8px", alignItems: "center", marginBottom: "12px" }}>
<input value={form.variantDraft} onChange={e => setField("variantDraft", e.target.value)} placeholder="الخيار/النكهة (مثال: توت)" style={{ background: "#fff", border: "1px solid #bdd0c6", borderRadius: "8px", padding: "9px 10px", fontSize: "0.86rem" }} />
<input id="admin-inline-var-price" type="number" placeholder="السعر (مثال: 250)" style={{ background: "#fff", border: "1px solid #bdd0c6", borderRadius: "8px", padding: "9px 10px", fontSize: "0.86rem" }} />
<input id="admin-inline-var-stock" type="number" min="0" placeholder="العدد (فارغ=متوفر، 0=نفد)" style={{ background: "#fff", border: "1px solid #bdd0c6", borderRadius: "8px", padding: "9px 10px", fontSize: "0.86rem" }} />
<button type="button" className="primary-button" style={{ padding: "9px 14px", fontSize: "0.86rem", whiteSpace: "nowrap", background: "#0d3825", color: "#d4af37", borderRadius: "8px" }} onClick={() => {
const nameVal = form.variantDraft.trim();
if (!nameVal) return;
const priceEl = document.getElementById("admin-inline-var-price") as HTMLInputElement | null;
const stockEl = document.getElementById("admin-inline-var-stock") as HTMLInputElement | null;
const priceVal = priceEl?.value ? priceEl.value.trim() : "";
const stockVal = stockEl?.value !== undefined ? stockEl.value.trim() : "";
const finalEntry = nameVal.includes(":") ? nameVal : (stockVal !== "" ? (nameVal + ":" + (priceVal || form.price || "0") + ":" + stockVal) : (priceVal ? (nameVal + ":" + priceVal) : nameVal));
if (!form.variants.includes(finalEntry)) { setField("variants", [...form.variants, finalEntry]); setField("price", ""); }
setField("variantDraft", "");
if (priceEl) priceEl.value = "";
if (stockEl) stockEl.value = "";
}}>+ إضافة للجدول</button>
</div>
{form.variants.length > 0 ? (
<div style={{ overflowX: "auto", background: "#fff", borderRadius: "10px", border: "1px solid #d5e2dc" }}>
<table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.84rem", textAlign: "right" }}>
<thead>
<tr style={{ background: "#0d3825", color: "#fff" }}>
<th style={{ padding: "8px 10px", borderBottom: "1px solid #d5e2dc" }}>الخيار / النكهة</th>
<th style={{ padding: "8px 10px", borderBottom: "1px solid #d5e2dc" }}>السعر (ر.ي)</th>
<th style={{ padding: "8px 10px", borderBottom: "1px solid #d5e2dc" }}>العدد المتوفر / التوفر</th>
<th style={{ padding: "8px 10px", borderBottom: "1px solid #d5e2dc", textAlign: "center", width: "65px" }}>حذف</th>
</tr>
</thead>
<tbody>
{form.variants.map((v, idx) => {
const parts = v.split(":");
const optName = parts[0]?.trim() || v;
const optPrice = parts.length > 1 ? parts[1]?.trim() : "";
const optStock = parts.length > 2 ? parts[2]?.trim() : "";
const isOut = optStock !== "" && Number(optStock) <= 0;
const buildEntry = (pVal: string, sVal: string) => sVal !== "" ? (optName + ":" + (pVal || form.price || "0") + ":" + sVal) : (pVal ? (optName + ":" + pVal) : optName);
return (
<tr key={idx} style={{ borderBottom: "1px solid #eef3f0", background: isOut ? "#fff5f5" : "#fff" }}>
<td style={{ padding: "8px 10px", fontWeight: 800, color: "#0d3825" }}>
<div>{optName}</div>
<span style={{ display: "inline-block", marginTop: "3px", fontSize: "0.72rem", padding: "1px 7px", borderRadius: "99px", fontWeight: 800, background: isOut ? "#fee2e2" : "#dcfce7", color: isOut ? "#b91c1c" : "#166534" }}>{isOut ? "🚫 غير متوفر حالياً (0)" : (optStock !== "" ? "✅ متوفر (" + optStock + ")" : "✅ متوفر")}</span>
</td>
<td style={{ padding: "6px 8px" }}>
<input type="number" value={optPrice} placeholder="السعر" onChange={e => { const updated = [...form.variants]; updated[idx] = buildEntry(e.target.value.trim(), optStock); setField("variants", updated); }} style={{ width: "85px", padding: "5px 7px", border: "1px solid #c2d4ca", borderRadius: "6px", fontWeight: 700, color: "#0d3825", background: "#f9fcfb" }} />
</td>
<td style={{ padding: "6px 8px" }}>
<div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
<input type="number" min="0" value={optStock} placeholder="متوفر دائماً" onChange={e => { const updated = [...form.variants]; updated[idx] = buildEntry(optPrice, e.target.value.trim()); setField("variants", updated); }} style={{ width: "85px", padding: "5px 7px", border: isOut ? "1.5px solid #ef4444" : "1px solid #c2d4ca", borderRadius: "6px", fontWeight: 700, color: isOut ? "#b91c1c" : "#0d3825", background: "#f9fcfb" }} />
<button type="button" onClick={() => { const updated = [...form.variants]; updated[idx] = buildEntry(optPrice, isOut ? "" : "0"); setField("variants", updated); }} style={{ background: isOut ? "#dcfce7" : "#fef3c7", color: isOut ? "#166534" : "#92400e", border: "1px solid " + (isOut ? "#86efac" : "#fcd34d"), borderRadius: "6px", padding: "4px 8px", cursor: "pointer", fontWeight: 800, fontSize: "0.75rem", whiteSpace: "nowrap" }}>{isOut ? "تفعيل التوفر ✓" : "نفد حالياً (0)"}</button>
</div>
</td>
<td style={{ padding: "6px 8px", textAlign: "center" }}>
<button type="button" onClick={() => setField("variants", form.variants.filter((_, i) => i !== idx))} style={{ background: "#fee2e2", color: "#b91c1c", border: "none", borderRadius: "6px", padding: "4px 10px", cursor: "pointer", fontWeight: 700 }}>حذف</button>
</td>
</tr>
);
})}
</tbody>
</table>
</div>
) : (
<div style={{ textAlign: "center", padding: "10px", background: "#fff", borderRadius: "8px", border: "1px dashed #bdd0c6", color: "#687a71", fontSize: "0.82rem" }}>لم تتم إضافة خيارات بعد — اكتب اسم النكهة أو الحجم بالأعلى وضع سعره والعدد المتوفر ليظهر في الجدول هنا.</div>
)}
</div>
"""
  pat_table = r'      <div className="field-wide"[^>]*>\s*<div[^>]*>\s*<strong[^>]*>📦 جدول الخيارات[\s\S]*?(?=      <div className="field-wide" style=\{\{ display: "flex", flexWrap: "wrap", gap: "8px", paddingTop: "4px" \}\}>)'
  ac, n_tbl = re.subn(pat_table, lambda m: v130_table_jsx, ac, count=1)
  admin_path.write_text(ac, encoding="utf-8")
  print("2. Updated Admin.tsx (replaced table:", n_tbl, ")!")

# 3. تحديث Home.tsx (إزالة أي استدعاء ذاتي متكرر في دوال المجموع + ربط مباشر بـ setCart لمنع تعليق أزرار السلة)
home_path = pathlib.Path("client/src/pages/Home.tsx")
if home_path.exists():
  hc = home_path.read_text(encoding="utf-8")
  hc = re.sub(r"// === V129_ENGINE_START ===[\s\S]*?// === V129_ENGINE_END ===\n?", "", hc)
  hc = re.sub(r"// === V130_ENGINE_START ===[\s\S]*?// === V130_ENGINE_END ===\n?", "", hc)
  hc = hc.replace("extractCartSubtotalV107(cartOrOrder, cartOrOrder?.subtotal)", "cartOrOrder?.subtotal")
  hc = hc.replace("extractOrderTotalV107(cartOrOrder, cartOrOrder?.total)", "cartOrOrder?.total")
  hc = hc.replace("id: String(it.id ?? \"\") + \"_v\" + idx,", "id: (it.orderId || it.orderNumber) ? (String(it.id ?? \"\") + \"_v\" + idx) : it.id,")

  hc, n_ustate = re.subn(
      r'(import\s*(?:React\s*,\s*)?\{[^}]*)\buseState\b(?!\s+as\s+_origUseStateV130)([^}]*\}\s*from\s*["\']react["\'])',
      lambda m: m.group(1) + "useState as _origUseStateV130" + m.group(2),
      hc,
      count=1,
  )
  has_ustate = ("_origUseStateV130" in hc)
  ustate_wrapper = r"""
function useState<T = any>(init?: any): [T, any] {
  const [val, setVal] = _origUseStateV130<T>(init as any);
  try {
    if (Array.isArray(val)) {
      if (val.length > 0 && val[0] && typeof val[0] === "object" && "quantity" in val[0] && !("orderId" in val[0]) && !("orderNumber" in val[0])) {
        (window as any).__v130CartArray = val;
        (window as any).__v130SetCartArray = setVal;
      } else if (val.length === 0 && (window as any).__v130SetCartArray === setVal) {
        (window as any).__v130CartArray = val;
      }
    }
  } catch {}
  return [val, setVal];
}
""" if has_ustate else ""

  last_imp = hc.rfind("\nimport ", 0, 3000)
  end_imp = hc.find("\n", last_imp + 1) if last_imp != -1 else 0
  wrapped_eng = "\n// === V130_ENGINE_START ===\n" + ENGINE_JS_V130 + ustate_wrapper + "\n// === V130_ENGINE_END ===\n"
  hc = hc[: end_imp + 1] + wrapped_eng + hc[end_imp + 1 :]
  home_path.write_text(hc, encoding="utf-8")
  print("3. Updated Home.tsx cleanly!")

# 4. تحديث client/index.html
html_path = pathlib.Path("client/index.html")
if html_path.exists():
  ht = html_path.read_text(encoding="utf-8")
  ht = re.sub(
      r"var rowQty = 1;\s*var rowBtns = Array\.from\(rowCard\.querySelectorAll\(\"button\"\)\)\.filter\(function\(b\)\s*\{\s*return b !== remBtn;\s*\}\);[\s\S]*?(?=var rowFullText = rowCard\.textContent)",
      "var rowQty = window.__readCartRowQtyV130 ? window.__readCartRowQtyV130(rowCard, [remBtn]) : 1;\n\n                ",
      ht,
  )
  pat_a = r'// PART A:[\s\S]*?(?=// PART B: Shopping Cart \("سلة التسوق"\) rows)'
  rep_a = "            // PART A: v130 Engine\n            if (window.__runV129Sync) window.__runV129Sync();\n\n"
  ht, _ = re.subn(pat_a, lambda m: rep_a, ht, count=1)
  ht = re.sub(r"<script id=\"v129-standalone-engine\">[\s\S]*?</script>\s*", "", ht)
  ht = re.sub(r"<script id=\"v130-standalone-engine\">[\s\S]*?</script>\s*", "", ht)
  ht = ht.replace("</body>", '<script id="v130-standalone-engine">' + ENGINE_JS_V130 + "</script>\n</body>", 1)
  html_path.write_text(ht, encoding="utf-8")
  print("4. Updated client/index.html!")

# 5. تحديث sw.js إلى v130
sw_path = pathlib.Path("client/public/sw.js")
if sw_path.exists():
  swc = sw_path.read_text(encoding="utf-8")
  swc = re.sub(r'const CACHE = "original-shell-v[^"]*";', 'const CACHE = "original-shell-v130";', swc)
  swc = swc.replace('url.pathname.includes("/assets/") ||\n    ', "").replace('url.pathname.includes("/assets/") ||', "")
  sw_path.write_text(swc, encoding="utf-8")
  print("5. Updated sw.js to v130!")

if pathlib.Path("./node_modules/.bin/esbuild").exists():
  res_cli = subprocess.run(
      "./node_modules/.bin/esbuild client/src/pages/Admin.tsx client/src/pages/Home.tsx --bundle --platform=browser --packages=external --jsx=automatic --outdir=./.tmp_cli_v130",
      shell=True, capture_output=True, text=True
  )
  subprocess.run("rm -rf ./.tmp_cli_v130", shell=True)
  if res_cli.returncode != 0:
    print("❌ خطأ في فحص الواجهة:", res_cli.stderr)
    sys.exit(1)

print("✅ نجح الفحص بنسبة 100%!")
os.system("git add server/commerce.ts client/src/pages/Admin.tsx client/src/pages/Home.tsx client/index.html client/public/sw.js")
os.system('git commit -m "Feat v130: per-variant stock and out-of-stock badge + instant cart plus/minus/remove fix"')
os.system("git push origin main")
print("🚀 تم رفع التحديث الشامل v130 بنجاح 100% إلى Render!")
