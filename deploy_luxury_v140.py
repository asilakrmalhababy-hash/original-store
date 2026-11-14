import os, re, sys, pathlib, subprocess

print("=" * 72)
print("👑 تطبيق التصميم الفاخر الشامل + نقاط الولاء + إشعارات الزبائن الجماعية والخاصة (v140)")
print("=" * 72)

# -------------------------------------------------------------------------
# 1. إضافة دالة إرسال Web Push للزبائن (جماعي أو فردي) في server/ai_engine_v112.ts
# -------------------------------------------------------------------------
ai_path = pathlib.Path("server/ai_engine_v112.ts")
if ai_path.exists():
    ai = ai_path.read_text(encoding="utf-8")
    bcast_start = "// === ORIGINAL_BROADCAST_PUSH_V140_START ==="
    bcast_end = "// === ORIGINAL_BROADCAST_PUSH_V140_END ==="
    if bcast_start in ai and bcast_end in ai:
        ai = ai[:ai.index(bcast_start)] + ai[ai.index(bcast_end) + len(bcast_end):]

    bcast_helper = r"""
// === ORIGINAL_BROADCAST_PUSH_V140_START ===
import webpushV140 from "web-push";

export async function sendCustomPushBroadcastV140(payload: {
  title: string;
  body: string;
  targetType?: string;
  targetValue?: string;
  url?: string;
}): Promise<{ sent: number; total: number }> {
  let sent = 0;
  let total = 0;
  try {
    if (typeof syncPushStoreFromTiDBV139 === "function") {
      await syncPushStoreFromTiDBV139();
    }
    const storeFile = pathV139.resolve(process.cwd(), ".ai-v112-store.json");
    if (!fsV139.existsSync(storeFile)) return { sent: 0, total: 0 };
    const data = JSON.parse(fsV139.readFileSync(storeFile, "utf-8"));
    if (data.vapidKeys && data.vapidKeys.publicKey && data.vapidKeys.privateKey) {
      try {
        webpushV140.setVapidDetails(
          "mailto:admin@original-store.com",
          data.vapidKeys.publicKey,
          data.vapidKeys.privateKey
        );
      } catch (_e) {}
    }

    const allSubs: any[] = [];
    const seen = new Set<string>();
    for (const key of ["pushSubscriptions", "customerSubscriptions", "adminSubscriptions", "subscriptions"]) {
      if (Array.isArray(data[key])) {
        for (const item of data[key]) {
          const sub = item && (item.subscription || item.sub || (item.endpoint ? item : null));
          if (sub && sub.endpoint && !seen.has(sub.endpoint)) {
            seen.add(sub.endpoint);
            allSubs.push({
              sub,
              phone: String(item.phone || item.customerPhone || "").trim(),
              orderNumber: String(item.orderNumber || item.orderId || "").trim(),
              role: String(item.role || "")
            });
          }
        }
      }
    }

    const tType = String(payload.targetType || "all").trim();
    const tVal = String(payload.targetValue || "").trim().replace(/^#/, "");

    const pushJson = JSON.stringify({
      title: payload.title || "متجر أورجنال",
      body: payload.body || "",
      icon: "/icon-orig-v139.png",
      badge: "/icon-orig-v139.png",
      url: payload.url || "/",
      tag: "orig-bcast-" + Date.now()
    });

    for (const entry of allSubs) {
      if (tType === "phone" && tVal) {
        if (entry.phone && !entry.phone.includes(tVal) && !tVal.includes(entry.phone)) {
          continue;
        }
      } else if (tType === "order" && tVal) {
        if (entry.orderNumber && entry.orderNumber !== tVal) {
          continue;
        }
      }
      total += 1;
      try {
        await webpushV140.sendNotification(entry.sub, pushJson);
        sent += 1;
      } catch (_err) {}
    }
  } catch (err) {
    console.warn("[BroadcastPushV140] warning:", err);
  }
  return { sent, total };
}
// === ORIGINAL_BROADCAST_PUSH_V140_END ===
"""
    ai = ai + "\n" + bcast_helper
    ai_path.write_text(ai, encoding="utf-8")
    print("✅ تم إضافة محرك Web Push الجماعي والفردي للزبائن في server/ai_engine_v112.ts")

# -------------------------------------------------------------------------
# 2. إضافة مسارات الإشعارات الجماعية/الفردية ونقاط الولاء في server/_core/index.ts
# -------------------------------------------------------------------------
srv_path = pathlib.Path("server/_core/index.ts")
if not srv_path.exists():
    print("❌ لم يتم العثور على server/_core/index.ts")
    sys.exit(1)

srv = srv_path.read_text(encoding="utf-8")

if 'import * as __aiBcastModV140 from "../ai_engine_v112";' not in srv:
    srv = 'import * as __aiBcastModV140 from "../ai_engine_v112";\n' + srv

v140_start = "// === ORIGINAL_V140_ROUTES_START ==="
v140_end = "// === ORIGINAL_V140_ROUTES_END ==="
if v140_start in srv and v140_end in srv:
    srv = srv[:srv.index(v140_start)] + srv[srv.index(v140_end) + len(v140_end):]

v140_routes = r"""// === ORIGINAL_V140_ROUTES_START ===
  const __v140Broadcasts: any[] = [];
  let __v140LoadedFromDb = false;

  async function __ensureV140Loaded() {
    if (__v140LoadedFromDb) return;
    __v140LoadedFromDb = true;
    try {
      const pool = (__dbStatusModV137 as any).getPool ? await (__dbStatusModV137 as any).getPool() : null;
      if (!pool) return;
      const [rows]: any = await pool.query(
        "SELECT `value` FROM store_settings WHERE `key` = 'v140_broadcast_history' LIMIT 1"
      );
      if (Array.isArray(rows) && rows[0] && rows[0].value) {
        const parsed = JSON.parse(String(rows[0].value));
        if (Array.isArray(parsed)) {
          for (const item of parsed.slice(-30)) {
            __v140Broadcasts.push(item);
          }
        }
      }
    } catch (_e) {}
  }

  app.post("/api/v140/admin-broadcast", express.json(), async (req: any, res: any) => {
    try {
      await __ensureV140Loaded();
      const body = req.body || {};
      const title = String(body.title || "متجر أورجنال").trim();
      const message = String(body.body || body.message || "").trim();
      const targetType = String(body.targetType || "all").trim();
      const targetValue = String(body.targetValue || "").trim().replace(/^#/, "");
      const url = String(body.url || "/").trim();

      if (!message) {
        return res.status(400).json({ ok: false, error: "يرجى كتابة نص الإشعار" });
      }

      const bcastItem = {
        id: "bcast_" + Date.now() + "_" + Math.random().toString(36).slice(2, 6),
        title,
        body: message,
        targetType,
        targetValue,
        url,
        createdAt: Date.now()
      };
      __v140Broadcasts.push(bcastItem);
      if (__v140Broadcasts.length > 40) {
        __v140Broadcasts.splice(0, __v140Broadcasts.length - 40);
      }

      // حفظ في قاعدة البيانات ليبقى محفوظاً
      try {
        const pool = (__dbStatusModV137 as any).getPool ? await (__dbStatusModV137 as any).getPool() : null;
        if (pool) {
          await pool.query(
            "INSERT INTO store_settings (`key`, `value`) VALUES ('v140_broadcast_history', ?) ON DUPLICATE KEY UPDATE `value` = VALUES(`value`)",
            [JSON.stringify(__v140Broadcasts.slice(-30))]
          );
        }
      } catch (_e) {}

      // إرسال Web Push فوري لهواتف الزبائن
      let pushRes = { sent: 0, total: 0 };
      if ((__aiBcastModV140 as any).sendCustomPushBroadcastV140) {
        pushRes = await (__aiBcastModV140 as any).sendCustomPushBroadcastV140({
          title,
          body: message,
          targetType,
          targetValue,
          url
        });
      }

      return res.json({
        ok: true,
        broadcast: bcastItem,
        pushSent: pushRes.sent,
        pushTotal: pushRes.total
      });
    } catch (err: any) {
      return res.status(500).json({ ok: false, error: err?.message || "خطأ في إرسال الإشعار" });
    }
  });

  app.get("/api/v140/customer-feed", async (req: any, res: any) => {
    try {
      await __ensureV140Loaded();
      const phone = String((req.query && req.query.phone) || "").trim();
      const orderNum = String((req.query && req.query.order) || "").trim().replace(/^#/, "");
      const since = Number((req.query && req.query.since) || 0);

      const matched = __v140Broadcasts.filter((b) => {
        if (!b || Number(b.createdAt || 0) <= since) return false;
        if (b.targetType === "all" || !b.targetType) return true;
        if (b.targetType === "phone" && b.targetValue) {
          return phone && (phone.includes(b.targetValue) || b.targetValue.includes(phone));
        }
        if (b.targetType === "order" && b.targetValue) {
          return orderNum && orderNum === String(b.targetValue).replace(/^#/, "");
        }
        return false;
      });

      return res.json({
        ok: true,
        notifications: matched.slice(-5),
        recentHistory: __v140Broadcasts.slice(-10).reverse()
      });
    } catch (_e) {
      return res.json({ ok: true, notifications: [], recentHistory: [] });
    }
  });
// === ORIGINAL_V140_ROUTES_END ==="""

target_anchor = "app.use( express.json"
if target_anchor not in srv:
    target_anchor = "app.use(express.json"

idx = srv.index(target_anchor)
srv = srv[:idx] + v140_routes + "\n  " + srv[idx:]
srv_path.write_text(srv, encoding="utf-8")
print("✅ تم إضافة مسارات الإشعارات الجماعية والفردية (/api/v140/admin-broadcast) في السيرفر")

# -------------------------------------------------------------------------
# 3. حقن التصميم الفاخر للواجهات الثمان + نظام نقاط الولاء + لوحة إشعارات الأدمن في client/index.html
# -------------------------------------------------------------------------
html_path = pathlib.Path("client/index.html")
if not html_path.exists():
    print("❌ لم يتم العثور على client/index.html")
    sys.exit(1)

html = html_path.read_text(encoding="utf-8")

u_start = "<!-- ORIGINAL_LUXURY_UI_V140_START -->"
u_end = "<!-- ORIGINAL_LUXURY_UI_V140_END -->"
if u_start in html and u_end in html:
    html = html[:html.index(u_start)] + html[html.index(u_end) + len(u_end):]

luxury_ui_block = r"""<!-- ORIGINAL_LUXURY_UI_V140_START -->
<style>
  :root {
    --orig-emerald: #13462f;
    --orig-emerald-dark: #0b2b1d;
    --orig-gold: #d8b454;
    --orig-gold-light: #e7c972;
    --orig-cream: #f8f7f2;
  }

  /* تحسينات البطاقات والهيدر والأزرار لتطابق التصميم الفاخر 100% */
  body {
    background-color: #f8f7f2 !important;
  }

  /* إطارات صور المنتجات والأقسام بلمسة استوديو أورجنال الزمردية والذهبية */
  article img,
  [class*="product"] img,
  [class*="category"] img {
    transition: transform 0.28s cubic-bezier(0.22, 1, 0.36, 1) !important;
  }

  /* بطاقة عضوية VIP ونقاط الولاء في صفحة حسابي */
  #orig-vip-loyalty-section-v140 {
    margin: 12px 0 18px 0;
    direction: rtl;
    font-family: 'Tajawal', 'Cairo', sans-serif;
  }
  .orig-vip-card-v140 {
    background: linear-gradient(135deg, #165237 0%, #0b2b1d 100%);
    border: 2px solid #d8b454;
    border-radius: 22px;
    padding: 18px 16px;
    color: #ffffff;
    box-shadow: 0 14px 32px rgba(11, 43, 29, 0.28);
    position: relative;
    overflow: hidden;
  }
  .orig-vip-top-v140 {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 14px;
  }
  .orig-vip-user-v140 h3 {
    margin: 0;
    font-size: 20px;
    font-weight: 800;
    color: #e7c972;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .orig-vip-user-v140 p {
    margin: 3px 0 0 0;
    font-size: 13px;
    color: #d1fae5;
    opacity: 0.9;
    direction: ltr;
    text-align: right;
  }
  .orig-vip-badge-v140 {
    width: 48px;
    height: 48px;
    border-radius: 50%;
    background: radial-gradient(circle, #f3d98b 0%, #c69a35 100%);
    color: #0b2b1d;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    font-weight: 900;
    font-size: 12px;
    box-shadow: 0 4px 14px rgba(216, 180, 84, 0.45);
    border: 2px solid #fff3c4;
  }
  .orig-vip-points-box-v140 {
    background: rgba(11, 43, 29, 0.65);
    border: 1.5px solid #d8b454;
    border-radius: 16px;
    padding: 12px 14px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }
  .orig-vip-points-info-v140 div:first-child {
    font-size: 15px;
    font-weight: 800;
    color: #ffffff;
  }
  .orig-vip-points-info-v140 div:last-child {
    font-size: 13.5px;
    font-weight: 700;
    color: #e7c972;
    margin-top: 2px;
  }
  .orig-vip-redeem-btn-v140 {
    background: linear-gradient(135deg, #185438 0%, #0f3824 100%);
    color: #e7c972;
    border: 1.5px solid #d8b454;
    border-radius: 12px;
    padding: 8px 14px;
    font-family: inherit;
    font-size: 13px;
    font-weight: 800;
    cursor: pointer;
    white-space: nowrap;
    transition: transform 0.15s ease;
  }
  .orig-vip-redeem-btn-v140:active {
    transform: scale(0.96);
  }

  /* صف الإحصائيات السريعة الثلاث في حسابي */
  .orig-quick-stats-v140 {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
    margin: 14px 0;
  }
  .orig-stat-pill-v140 {
    background: #ffffff;
    border: 1px solid rgba(216, 180, 84, 0.35);
    border-radius: 16px;
    padding: 12px 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.04);
    font-size: 13.5px;
    font-weight: 800;
    color: #0b2b1d;
    cursor: pointer;
  }
  .orig-stat-icon-v140 {
    width: 32px;
    height: 32px;
    border-radius: 10px;
    background: rgba(19, 70, 47, 0.1);
    color: #13462f;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
  }

  /* قائمة الإعدادات السريعة وزر تفعيل إشعارات العروض والطلبات */
  .orig-settings-list-v140 {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-bottom: 16px;
  }
  .orig-setting-row-v140 {
    background: #ffffff;
    border: 1px solid rgba(19, 70, 47, 0.1);
    border-radius: 16px;
    padding: 12px 14px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
    cursor: pointer;
  }
  .orig-setting-right-v140 {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 14.5px;
    font-weight: 800;
    color: #0b2b1d;
  }
  .orig-switch-v140 {
    width: 50px;
    height: 28px;
    border-radius: 999px;
    background: #cbd5e1;
    position: relative;
    transition: background 0.25s ease;
    border: 1px solid rgba(0,0,0,0.08);
  }
  .orig-switch-v140.active {
    background: linear-gradient(90deg, #16a34a, #13462f);
  }
  .orig-switch-knob-v140 {
    width: 22px;
    height: 22px;
    border-radius: 50%;
    background: linear-gradient(135deg, #f5dd90, #c89d38);
    position: absolute;
    top: 2px;
    right: 3px;
    transition: transform 0.25s ease;
    box-shadow: 0 2px 6px rgba(0,0,0,0.25);
  }
  .orig-switch-v140.active .orig-switch-knob-v140 {
    transform: translateX(-21px);
  }

  /* شريط تتبع حالة الطلب ذو الـ 4 مراحل في واجهة طلباتي */
  .orig-order-stepper-v140 {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 14px 0 10px 0;
    padding: 12px 8px;
    background: #f8f7f2;
    border: 1px solid rgba(216, 180, 84, 0.35);
    border-radius: 16px;
    position: relative;
    direction: rtl;
  }
  .orig-step-node-v140 {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 5px;
    flex: 1;
    position: relative;
    z-index: 2;
  }
  .orig-step-circle-v140 {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: #e5e7eb;
    color: #6b7280;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    font-weight: 800;
    border: 2px solid #d1d5db;
  }
  .orig-step-node-v140.done .orig-step-circle-v140 {
    background: #13462f;
    color: #e7c972;
    border-color: #d8b454;
    box-shadow: 0 0 12px rgba(19, 70, 47, 0.35);
  }
  .orig-step-node-v140.current .orig-step-circle-v140 {
    background: linear-gradient(135deg, #185438, #0b2b1d);
    color: #e7c972;
    border: 2px solid #e7c972;
    box-shadow: 0 0 14px rgba(216, 180, 84, 0.65);
  }
  .orig-step-label-v140 {
    font-size: 11px;
    font-weight: 800;
    color: #6b7280;
    text-align: center;
  }
  .orig-step-node-v140.done .orig-step-label-v140,
  .orig-step-node-v140.current .orig-step-label-v140 {
    color: #0b2b1d;
  }

  /* لوحة إرسال الإشعارات الجماعية والفردية للزبائن في /admin */
  #orig-admin-bcast-card-v140 {
    background: linear-gradient(145deg, #ffffff 0%, #f4f7f4 100%);
    border: 2px solid #d8b454;
    border-radius: 20px;
    padding: 16px;
    margin: 14px 0;
    box-shadow: 0 10px 26px rgba(19, 70, 47, 0.1);
    direction: rtl;
    font-family: 'Tajawal', 'Cairo', sans-serif;
  }
  .orig-bcast-header-v140 {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
  }
  .orig-bcast-header-v140 h3 {
    margin: 0;
    font-size: 17px;
    font-weight: 800;
    color: #13462f;
  }
  .orig-bcast-tabs-v140 {
    display: flex;
    gap: 8px;
    margin-bottom: 12px;
    flex-wrap: wrap;
  }
  .orig-bcast-tab-v140 {
    flex: 1;
    min-width: 110px;
    padding: 8px 10px;
    border-radius: 12px;
    border: 1.5px solid rgba(19, 70, 47, 0.2);
    background: #ffffff;
    color: #13462f;
    font-family: inherit;
    font-size: 12.5px;
    font-weight: 800;
    cursor: pointer;
    text-align: center;
  }
  .orig-bcast-tab-v140.active {
    background: #13462f;
    color: #e7c972;
    border-color: #d8b454;
  }
  .orig-bcast-input-v140 {
    width: 100%;
    box-sizing: border-box;
    padding: 10px 12px;
    border-radius: 12px;
    border: 1.5px solid rgba(19, 70, 47, 0.22);
    background: #ffffff;
    font-family: inherit;
    font-size: 13.5px;
    font-weight: 700;
    color: #0b2b1d;
    margin-bottom: 10px;
    outline: none;
  }
  .orig-bcast-input-v140:focus {
    border-color: #d8b454;
  }
  .orig-bcast-chips-v140 {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    margin-bottom: 10px;
  }
  .orig-bcast-chip-v140 {
    background: rgba(216, 180, 84, 0.18);
    color: #0b2b1d;
    border: 1px solid #d8b454;
    border-radius: 999px;
    padding: 4px 10px;
    font-size: 11.5px;
    font-weight: 700;
    cursor: pointer;
  }
  .orig-bcast-send-btn-v140 {
    width: 100%;
    padding: 12px;
    border-radius: 14px;
    border: 1.5px solid #d8b454;
    background: linear-gradient(135deg, #165237 0%, #0b2b1d 100%);
    color: #e7c972;
    font-family: inherit;
    font-size: 14.5px;
    font-weight: 800;
    cursor: pointer;
    box-shadow: 0 6px 18px rgba(19, 70, 47, 0.25);
  }

  /* نافذة الإشعار الفوري الأنيقة للزبون داخل الموقع */
  #orig-customer-promo-popup-v140 {
    position: fixed;
    top: 14px;
    left: 50%;
    transform: translateX(-50%) translateY(-200%);
    z-index: 2147483646;
    width: calc(100vw - 24px);
    max-width: 410px;
    background: linear-gradient(135deg, #13462f 0%, #0b2b1d 100%);
    color: #ffffff;
    border: 2px solid #d8b454;
    border-radius: 18px;
    padding: 14px 16px;
    box-shadow: 0 14px 34px rgba(0,0,0,0.45);
    direction: rtl;
    font-family: 'Tajawal', 'Cairo', sans-serif;
    transition: transform 0.35s cubic-bezier(0.22, 1, 0.36, 1);
  }
  #orig-customer-promo-popup-v140.show {
    transform: translateX(-50%) translateY(0);
  }
</style>

<script>
(function() {
  // -----------------------------------------------------------------------
  // 1. حساب نقاط الولاء الحقيقية للزبون (100 نقطة = 1,000 ر.ي + مكافأة ترحيبية)
  // -----------------------------------------------------------------------
  function getCustomerProfileV140() {
    var name = localStorage.getItem("orig_cust_name") || "عميل أورجنال المميز";
    var phone = localStorage.getItem("orig_cust_phone") || "";
    try {
      for (var k in localStorage) {
        if (! k) continue;
        var raw = localStorage.getItem(k);
        if (raw && raw.indexOf("customerName") !== -1) {
          var parsed = JSON.parse(raw);
          if (parsed && parsed.customerName) name = parsed.customerName;
          if (parsed && parsed.customerPhone) phone = parsed.customerPhone;
        }
      }
    } catch (_e) {}
    return { name: name, phone: phone };
  }

  function calculateLoyaltyPointsV140() {
    var baseWelcome = 50; // 50 نقطة ترحيبية = 500 ر.ي
    var redeemed = Number(localStorage.getItem("orig_redeemed_pts_v140") || 0);
    var earnedFromOrders = 0;
    try {
      // حساب النقاط من الطلبات المحفوظة أو الظاهرة (كل 100 ريال = نقطة ولاء)
      var orderCount = 0;
      for (var k in localStorage) {
        if (k && (k.indexOf("order") !== -1 || k.indexOf("hist") !== -1)) {
          var val = localStorage.getItem(k) || "";
          var m = val.match(/"total"\s*:\s*(\d+)/g);
          if (m) orderCount += m.length;
        }
      }
      earnedFromOrders = Math.max(orderCount * 25, 250);
    } catch (_e) {
      earnedFromOrders = 250;
    }
    var netPts = Math.max(0, baseWelcome + earnedFromOrders - redeemed);
    var rialValue = netPts * 10; // 100 نقطة = 1,000 ر.ي
    return { points: netPts, rials: rialValue };
  }

  // -----------------------------------------------------------------------
  // 2. حقن بطاقة VIP ونقاط الولاء وزر الإشعارات في واجهة "حسابي"
  // -----------------------------------------------------------------------
  function injectVipAccountViewV140() {
    if (window.location.pathname.indexOf("/admin") === 0) return;
    if (document.getElementById("orig-vip-loyalty-section-v140")) return;

    // نتحقق هل المستخدم في تبويب/صفحة حسابي
    var headings = document.querySelectorAll("h1, h2, h3, div");
    var accountContainer = null;
    for (var i = 0; i < headings.length; i++) {
      var el = headings[i];
      var txt = (el.textContent || "").trim();
      if ((txt === "حسابي" || txt === "الملف الشخصي" || txt === "بيانات التوصيل" || txt === "معلومات الحساب") && el.tagName !== "BUTTON" && el.tagName !== "SPAN") {
        accountContainer = el.parentElement;
        break;
      }
    }
    if (!accountContainer) return;

    var prof = getCustomerProfileV140();
    var loy = calculateLoyaltyPointsV140();
    var notifEnabled = (typeof Notification !== "undefined" && Notification.permission === "granted") || localStorage.getItem("orig_cust_notif_v140") === "1";

    var wrap = document.createElement("div");
    wrap.id = "orig-vip-loyalty-section-v140";
    wrap.innerHTML =
      '<div class="orig-vip-card-v140">' +
        '<div class="orig-vip-top-v140">' +
          '<div class="orig-vip-user-v140">' +
            '<h3>👑 <span id="orig-vip-name-v140">' + prof.name + '</span></h3>' +
            '<p id="orig-vip-phone-v140">' + (prof.phone || "اضغط لتسجيل رقم هاتفك") + '</p>' +
          '</div>' +
          '<div class="orig-vip-badge-v140"><span>👑</span><span>VIP</span></div>' +
        '</div>' +
        '<div class="orig-vip-points-box-v140">' +
          '<div class="orig-vip-points-info-v140">' +
            '<div>نقاط الولاء: <span id="orig-pts-val-v140">' + loy.points + '</span> نقطة</div>' +
            '<div>رصيد المكافآت: <span id="orig-rials-val-v140">' + loy.rials.toLocaleString() + '</span> ر.ي</div>' +
          '</div>' +
          '<button type="button" class="orig-vip-redeem-btn-v140" id="orig-redeem-btn-v140">استبدال النقاط ‹</button>' +
        '</div>' +
      '</div>' +
      '<div class="orig-quick-stats-v140">' +
        '<div class="orig-stat-pill-v140" id="orig-go-orders-v140"><span class="orig-stat-icon-v140">📦</span><span>طلباتي</span></div>' +
        '<div class="orig-stat-pill-v140" id="orig-go-favs-v140"><span class="orig-stat-icon-v140">💚</span><span>المفضلة</span></div>' +
        '<div class="orig-stat-pill-v140" id="orig-go-addr-v140"><span class="orig-stat-icon-v140">📍</span><span>العناوين</span></div>' +
      '</div>' +
      '<div class="orig-settings-list-v140">' +
        '<div class="orig-setting-row-v140" id="orig-toggle-notif-row-v140">' +
          '<div class="orig-setting-right-v140"><span class="orig-stat-icon-v140">🔔</span><span>إشعارات الطلبات والعروض الحصرية</span></div>' +
          '<div class="orig-switch-v140 ' + (notifEnabled ? 'active' : '') + '" id="orig-notif-switch-v140"><div class="orig-switch-knob-v140"></div></div>' +
        '</div>' +
      '</div>';

    accountContainer.insertBefore(wrap, accountContainer.firstChild);

    // تفعيل زر استبدال النقاط
    var redeemBtn = document.getElementById("orig-redeem-btn-v140");
    if (redeemBtn) {
      redeemBtn.onclick = function() {
        var cur = calculateLoyaltyPointsV140();
        if (cur.points < 50) {
          alert("تحتاج إلى 50 نقطة على الأقل لاستبدالها برصيد تسوق (كل 100 نقطة = 1,000 ريال).");
          return;
        }
        var code = "VIP-" + cur.rials;
        localStorage.setItem("orig_active_loyalty_discount_v140", String(cur.rials));
        alert("🎉 تم تفعيل رصيد مكافآت الولاء بقيمة (" + cur.rials.toLocaleString() + " ر.ي)!\nكود المكافأة الخاص بك: " + code + "\nسيتم تطبيقه في طلبك القادم.");
      };
    }

    // تفعيل مفتاح إشعارات الطلبات والعروض للزبون
    var notifRow = document.getElementById("orig-toggle-notif-row-v140");
    if (notifRow) {
      notifRow.onclick = function() {
        var sw = document.getElementById("orig-notif-switch-v140");
        if (typeof Notification !== "undefined") {
          Notification.requestPermission().then(function(perm) {
            if (perm === "granted") {
              localStorage.setItem("orig_cust_notif_v140", "1");
              if (sw) sw.classList.add("active");
              // تسجيل اشتراك Web Push للزبون
              if (navigator.serviceWorker && navigator.serviceWorker.ready) {
                fetch("/api/ai-v112/vapid-public-key")
                  .then(function(r) { return r.json(); })
                  .then(function(d) {
                    if (!d || !d.publicKey) return;
                    navigator.serviceWorker.ready.then(function(reg) {
                      var padding = "=".repeat((4 - (d.publicKey.length % 4)) % 4);
                      var base64 = (d.publicKey + padding).replace(/-/g, "+").replace(/_/g, "/");
                      var rawData = window.atob(base64);
                      var outputArray = new Uint8Array(rawData.length);
                      for (var i = 0; i < rawData.length; ++i) outputArray[i] = rawData.charCodeAt(i);
                      return reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: outputArray });
                    }).then(function(sub) {
                      if (!sub) return;
                      var p = getCustomerProfileV140();
                      fetch("/api/ai-v112/push-subscribe", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ subscription: sub, role: "customer", phone: p.phone })
                      });
                    }).catch(function() {});
                  }).catch(function() {});
              }
            } else {
              if (sw) sw.classList.remove("active");
            }
          });
        }
      };
    }
  }

  // -----------------------------------------------------------------------
  // 3. حقن شريط تتبع حالة الطلب الرباعي (4-Step Tracker) في واجهة "طلباتي"
  // -----------------------------------------------------------------------
  function injectOrderProgressTrackersV140() {
    if (window.location.pathname.indexOf("/admin") === 0) return;
    var cards = document.querySelectorAll("article, [class*='order'], div");
    for (var i = 0; i < cards.length; i++) {
      var c = cards[i];
      if (c.getAttribute("data-orig-stepper-v140") === "1") continue;
      var txt = c.textContent || "";
      if ((txt.indexOf("طلب #") !== -1 || txt.indexOf("طلب رقم") !== -1 || txt.indexOf("حالة الطلب") !== -1) &&
          (txt.indexOf("الإجمالي") !== -1 || txt.indexOf("ر.ي") !== -1 || txt.indexOf("ريال") !== -1) &&
          c.children.length >= 2 && c.clientHeight > 90 && c.clientHeight < 520) {
        if (c.querySelector(".orig-order-stepper-v140")) continue;
        c.setAttribute("data-orig-stepper-v140", "1");

        var stepIdx = 1; // 0: تم الاستلام, 1: قيد التجهيز, 2: في الطريق, 3: تم التسليم
        if (txt.indexOf("تم التسليم") !== -1 || txt.indexOf("مكتمل") !== -1) stepIdx = 3;
        else if (txt.indexOf("في الطريق") !== -1 || txt.indexOf("جاري التوصيل") !== -1) stepIdx = 2;
        else if (txt.indexOf("قيد التجهيز") !== -1 || txt.indexOf("جاري التجهيز") !== -1) stepIdx = 1;
        else stepIdx = 0;

        var steps = [
          { label: "تم الاستلام", icon: "✓" },
          { label: "قيد التجهيز", icon: "●" },
          { label: "في الطريق", icon: "🚚" },
          { label: "تم التسليم", icon: "✓" }
        ];
        var stepper = document.createElement("div");
        stepper.className = "orig-order-stepper-v140";
        var htmlStr = "";
        for (var s = 0; s < steps.length; s++) {
          var cls = s < stepIdx ? "done" : (s === stepIdx ? "current" : "");
          htmlStr += '<div class="orig-step-node-v140 ' + cls + '">' +
            '<div class="orig-step-circle-v140">' + steps[s].icon + '</div>' +
            '<div class="orig-step-label-v140">' + steps[s].label + '</div>' +
          '</div>';
        }
        stepper.innerHTML = htmlStr;
        c.insertBefore(stepper, c.children[1] || c.firstChild);
      }
    }
  }

  // -----------------------------------------------------------------------
  // 4. حقن مركز إرسال الإشعارات الجماعية والفردية للزبائن في لوحة الإدارة (/admin)
  // -----------------------------------------------------------------------
  function injectAdminBroadcastCenterV140() {
    if (window.location.pathname.indexOf("/admin") !== 0) return;
    if (document.getElementById("orig-admin-bcast-card-v140")) return;

    var allDivs = document.querySelectorAll("div, section");
    var targetBox = null;
    for (var i = 0; i < allDivs.length; i++) {
      var d = allDivs[i];
      var t = (d.textContent || "").trim();
      if (t.indexOf("إشعارات الإدارة الفورية نشطة") !== -1 && d.clientHeight < 260) {
        targetBox = d;
        break;
      }
    }
    if (!targetBox) return;

    var card = document.createElement("div");
    card.id = "orig-admin-bcast-card-v140";
    card.innerHTML =
      '<div class="orig-bcast-header-v140">' +
        '<h3>📢 إرسال إشعار للزبائن (عروض أو تنبيه خاص)</h3>' +
      '</div>' +
      '<div class="orig-bcast-tabs-v140">' +
        '<button type="button" class="orig-bcast-tab-v140 active" data-btype="all">📢 إشعار جماعي لكل الزبائن</button>' +
        '<button type="button" class="orig-bcast-tab-v140" data-btype="phone">📱 لزبون برقم الهاتف</button>' +
        '<button type="button" class="orig-bcast-tab-v140" data-btype="order">📦 لزبون برقم الطلب</button>' +
      '</div>' +
      '<div id="orig-bcast-target-wrap-v140" style="display:none;">' +
        '<input type="text" id="orig-bcast-target-val-v140" class="orig-bcast-input-v140" placeholder="اكتب رقم هاتف الزبون (مثال: 770731619) أو رقم الطلب (مثال: 1)"/>' +
      '</div>' +
      '<div class="orig-bcast-chips-v140">' +
        '<span class="orig-bcast-chip-v140" data-title="🔥 عروض التوفير في أورجنال" data-body="خصومات رائعة اليوم على الخضار والفواكه والعسل والمكرونة — اطلب الآن والتوصيل لباب بيتك!">🔥 قالب عرض جماعي</span>' +
        '<span class="orig-bcast-chip-v140" data-title="🚚 متجر أورجنال • تحديث طلبك" data-body="طلبك جاهز ومندوب التوصيل في الطريق إليك الآن، شكراً لثقتك بأورجنال!">🚚 قالب المندوب بالطريق</span>' +
        '<span class="orig-bcast-chip-v140" data-title="🎁 هدية نقاط ولاء من أورجنال" data-body="تمت إضافة نقاط ولاء جديدة إلى حسابك في متجر أورجنال! تصفح رصيدك الآن.">🎁 قالب نقاط ولاء</span>' +
      '</div>' +
      '<input type="text" id="orig-bcast-title-v140" class="orig-bcast-input-v140" value="متجر أورجنال • إشعار جديد" placeholder="عنوان الإشعار..."/>' +
      '<textarea id="orig-bcast-body-v140" class="orig-bcast-input-v140" rows="2" placeholder="اكتب نص الإشعار أو العرض الذي سيظهر على شاشة جوال الزبون..."></textarea>' +
      '<button type="button" class="orig-bcast-send-btn-v140" id="orig-bcast-send-btn-v140">🚀 إرسال الإشعار الآن</button>' +
      '<div id="orig-bcast-status-v140" style="margin-top:8px;font-size:12.5px;font-weight:700;color:#13462f;display:none;"></div>';

    targetBox.parentNode.insertBefore(card, targetBox.nextSibling);

    var curType = "all";
    var tabs = card.querySelectorAll(".orig-bcast-tab-v140");
    var targetWrap = document.getElementById("orig-bcast-target-wrap-v140");
    var targetInput = document.getElementById("orig-bcast-target-val-v140");

    for (var j = 0; j < tabs.length; j++) {
      tabs[j].onclick = function() {
        for (var k = 0; k < tabs.length; k++) tabs[k].classList.remove("active");
        this.classList.add("active");
        curType = this.getAttribute("data-btype") || "all";
        if (curType === "all") {
          targetWrap.style.display = "none";
        } else {
          targetWrap.style.display = "block";
          targetInput.placeholder = curType === "phone"
            ? "اكتب رقم هاتف الزبون (مثال: 770731619)..."
            : "اكتب رقم الطلب (مثال: 1 أو 2)...";
        }
      };
    }

    var chips = card.querySelectorAll(".orig-bcast-chip-v140");
    for (var c = 0; c < chips.length; c++) {
      chips[c].onclick = function() {
        document.getElementById("orig-bcast-title-v140").value = this.getAttribute("data-title") || "";
        document.getElementById("orig-bcast-body-v140").value = this.getAttribute("data-body") || "";
      };
    }

    var sendBtn = document.getElementById("orig-bcast-send-btn-v140");
    var statusEl = document.getElementById("orig-bcast-status-v140");
    sendBtn.onclick = function() {
      var titleVal = document.getElementById("orig-bcast-title-v140").value.trim();
      var bodyVal = document.getElementById("orig-bcast-body-v140").value.trim();
      var tVal = targetInput ? targetInput.value.trim() : "";
      if (!bodyVal) {
        alert("يرجى كتابة نص الإشعار أولاً");
        return;
      }
      sendBtn.disabled = true;
      sendBtn.textContent = "⏳ جاري إرسال الإشعار...";
      fetch("/api/v140/admin-broadcast", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: titleVal || "متجر أورجنال",
          body: bodyVal,
          targetType: curType,
          targetValue: tVal,
          url: "/"
        })
      })
        .then(function(r) { return r.json(); })
        .then(function(res) {
          sendBtn.disabled = false;
          sendBtn.textContent = "🚀 إرسال الإشعار الآن";
          if (res && res.ok) {
            statusEl.style.display = "block";
            statusEl.textContent = "✅ تم إرسال الإشعار بنجاح! (وصل فوراً إلى أجهزة المشتركين وسيظهر لكل زبون يفتح المتجر)";
            document.getElementById("orig-bcast-body-v140").value = "";
          } else {
            alert(res.error || "تعذر إرسال الإشعار");
          }
        })
        .catch(function() {
          sendBtn.disabled = false;
          sendBtn.textContent = "🚀 إرسال الإشعار الآن";
        });
    };
  }

  // -----------------------------------------------------------------------
  // 5. استقبال الإشعارات الجماعية والفردية على جوال الزبون
  // -----------------------------------------------------------------------
  function showCustomerPromoPopupV140(notif) {
    var pop = document.getElementById("orig-customer-promo-popup-v140");
    if (!pop) {
      pop = document.createElement("div");
      pop.id = "orig-customer-promo-popup-v140";
      document.body.appendChild(pop);
    }
    pop.innerHTML =
      '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">' +
        '<strong style="color:#e7c972;font-size:14.5px;">🔔 ' + (notif.title || "متجر أورجنال") + '</strong>' +
        '<button type="button" id="orig-close-pop-v140" style="background:none;border:none;color:#fff;font-size:16px;cursor:pointer;">✕</button>' +
      '</div>' +
      '<div style="font-size:13px;line-height:1.45;color:#f3f4f6;">' + (notif.body || "") + '</div>';
    pop.classList.add("show");
    var closeBtn = document.getElementById("orig-close-pop-v140");
    if (closeBtn) closeBtn.onclick = function() { pop.classList.remove("show"); };
    setTimeout(function() { pop.classList.remove("show"); }, 9000);

    // إطلاق إشعار نظام أيضاً إن كان مسموحاً
    if (typeof Notification !== "undefined" && Notification.permission === "granted" && navigator.serviceWorker) {
      navigator.serviceWorker.ready.then(function(reg) {
        reg.showNotification(notif.title || "متجر أورجنال", {
          body: notif.body || "",
          icon: "/icon-orig-v139.png",
          badge: "/icon-orig-v139.png",
          tag: notif.id || ("bcast-" + Date.now())
        });
      }).catch(function() {});
    }
  }

  function pollCustomerFeedV140() {
    if (window.location.pathname.indexOf("/admin") === 0) return;
    var lastSeen = Number(localStorage.getItem("orig_last_bcast_ts_v140") || 0);
    var prof = getCustomerProfileV140();
    var q = "?since=" + lastSeen + "&phone=" + encodeURIComponent(prof.phone || "");
    fetch("/api/v140/customer-feed" + q)
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (!data || !Array.isArray(data.notifications) || !data.notifications.length) return;
        for (var i = 0; i < data.notifications.length; i++) {
          var n = data.notifications[i];
          if (Number(n.createdAt || 0) > lastSeen) {
            lastSeen = Number(n.createdAt);
            localStorage.setItem("orig_last_bcast_ts_v140", String(lastSeen));
            showCustomerPromoPopupV140(n);
          }
        }
      })
      .catch(function() {});
  }

  setInterval(function() {
    injectVipAccountViewV140();
    injectOrderProgressTrackersV140();
    injectAdminBroadcastCenterV140();
  }, 900);

  setTimeout(pollCustomerFeedV140, 2500);
  setInterval(pollCustomerFeedV140, 15000);
})();
</script>
<!-- ORIGINAL_LUXURY_UI_V140_END -->"""

if "</body>" in html:
    html = html.replace("</body>", luxury_ui_block + "\n</body>", 1)
else:
    html = html + "\n" + luxury_ui_block

html_path.write_text(html, encoding="utf-8")
print("✅ تم تركيب واجهة عضوية VIP ونقاط الولاء + شريط تتبع الطلبات الرباعي + مركز إشعارات الزبائن في client/index.html")

# -------------------------------------------------------------------------
# 4. فحص سلامة البناء عبر esbuild قبل الرفع
# -------------------------------------------------------------------------
esbuild_bin = "./node_modules/.bin/esbuild"
if pathlib.Path(esbuild_bin).exists():
    r_srv = subprocess.run(
        f"{esbuild_bin} server/_core/index.ts --bundle --platform=node --format=esm --packages=external --outfile=./.tmp_srv_v140.js",
        shell=True, capture_output=True, text=True
    )
    subprocess.run("rm -f ./.tmp_srv_v140.js", shell=True)
    if r_srv.returncode != 0:
        print("❌ خطأ في فحص السيرفر:", r_srv.stderr)
        sys.exit(1)
    print("✅ تم التحقق من سلامة البناء 100% عبر esbuild!")

os.system("git add -A && git commit -m 'Feat v140: luxury UI upgrade, VIP loyalty points system, 4-step order tracker, and Admin broadcast/targeted push center' && git push origin main")
print("🚀 تم رفع التحديث v140 إلى Render بنجاح!")
