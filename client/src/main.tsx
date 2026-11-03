// --- GLOBAL_INSTANT_CATALOG_GUARD_START ---
(globalThis as any).INSTANT_CACHE_KEY = "original-catalog-instant-v2";
(globalThis as any).DEFAULT_APP_INFO = "تطبيق أورجنال (ORIGINAL) هو وجهتك الأولى للتسوق الذكي وتوصيل كافة احتياجات المنزل والمقاضي الغذائية والخضروات والفواكه الطازجة إلى باب بيتك بأعلى جودة وأسعار منافسة، وهدفنا توفير وقتك وجهدك بخدمة سريعة وموثوقة.\n\n📌 تعليمات وطريقة استخدام التطبيق:\n1️⃣ تصفح واختيار المنتجات: تصفح الأقسام أو ابحث عن أي منتج وأضفه للسلة بضغطة زر، مع إمكانية تحديد الوزن أو النوع للأصناف الموزونة.\n2️⃣ حفظ بياناتك وعنوانك: من صفحة «حسابي» احفظ اسمك ورقم جوالك وعنوان التوصيل لمرة واحدة ليتم تعبئتها تلقائياً في جميع طلباتك القادمة.\n3️⃣ إتمام الطلب ومتابعته: راجع سلة المشتريات واضغط «إتمام الطلب»، ثم تابع حالة طلبك خطوة بخطوة من صفحة «طلباتي» حتى يصل لباب منزلك.\n4️⃣ المساعد الذكي وشريط الهدايا: استمتع بالهدايا والخصومات التلقائية عند إكمال مبلغ شريط المكافآت، واستعن بمساعد أورجنال الذكي لاقتراح الوصفات الاقتصادية أو طلب توفير أي منتج.";
(globalThis as any).DEFAULT_CONTACT_WHY = "عزيزنا العميل، نسعد بتواصلك معنا في أي وقت في الحالات التالية:\n• إذا لم تجد منتجاً معيناً في المتجر وترغب بأن نوفره لك.\n• إذا كان لديك أي استفسار حول المنتجات أو الأسعار أو مناطق التوصيل.\n• إذا واجهت أي خطأ تقني في التطبيق أو مشكلة أو تأخير في طلبك.\n• إذا كانت لديك أي ملاحظة أو اقتراح لتطوير خدمات متجر أورجنال.\n\nلا تتردد في مراسلتنا أو الاتصال بنا، وفريقنا في خدمتك دائماً مع خالص الشكر والتقدير!";
(globalThis as any).readLocalInstantCatalog = function readLocalInstantCatalog() {
  try {
    const k = "original-catalog-instant-v2";
    if (typeof window !== "undefined" && (window as any).__INITIAL_CATALOG__) {
      const ic = (window as any).__INITIAL_CATALOG__;
      if (ic && Array.isArray(ic.products)) {
        try { localStorage.setItem(k, JSON.stringify(ic)); } catch {}
        return ic;
      }
    }
    const saved = typeof localStorage !== "undefined" ? localStorage.getItem(k) : null;
    if (saved) {
      const p = JSON.parse(saved);
      if (p && Array.isArray(p.products)) return p;
    }
  } catch {}
  return { categories: [], products: [], banners: [], offers: [], settings: {} };
};
(globalThis as any).checkClientAutoPause = function checkClientAutoPause(settings?: Record<string, string>) {
  if (!settings) return { paused: false, msg: "" };
  if (settings.orderPaused === "true") return { paused: true, msg: settings.pausedMessage || "استقبال الطلبات متوقف مؤقتًا" };
  if (settings.autoScheduleEnabled === "true") {
    const cStr = String(settings.autoCloseTime || "").trim();
    const oStr = String(settings.autoOpenTime || "").trim();
    const cm = cStr.match(/^(\d{1,2}):(\d{2})$/);
    const om = oStr.match(/^(\d{1,2}):(\d{2})$/);
    if (cm && om) {
      const cMins = Number(cm[1]) * 60 + Number(cm[2]);
      const oMins = Number(om[1]) * 60 + Number(om[2]);
      if (cMins !== oMins) {
        const yemenNow = new Date(Date.now() + 3 * 3600 * 1000);
        const curMins = yemenNow.getUTCHours() * 60 + yemenNow.getUTCMinutes();
        const isClosed = cMins > oMins ? (curMins >= cMins || curMins < oMins) : (curMins >= cMins && curMins < oMins);
        if (isClosed) {
          const oh = Number(om[1]);
          const omStr = om[2];
          const period = oh >= 12 ? "مساءً" : "صباحاً";
          const h12 = oh % 12 === 0 ? 12 : oh % 12;
          return { paused: true, msg: settings.pausedMessage || ("🌙 المتجر مغلق حالياً — يفتح تلقائياً الساعة " + h12 + ":" + omStr + " " + period) };
        }
      }
    }
  }
  return { paused: false, msg: "" };
};
// --- GLOBAL_INSTANT_CATALOG_GUARD_END ---
// __SAFE_TOAST_PATCH__
import { toast as __sonnerToast } from "sonner";
const __origToastError = __sonnerToast.error.bind(__sonnerToast);
(__sonnerToast as any).error = (msg: unknown, opts?: any) => {
  const s = String(msg ?? "");
  if (s.includes("invalid_format") || s.includes("must match pattern") || s.includes("OR-[A-Z0-9]") || (s.trim().startsWith("[") && s.includes("origin"))) {
    return;
  }
  return __origToastError(msg as any, opts);
};
import { trpc } from "@/lib/trpc";
import { COOKIE_NAME } from "@shared/const";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { httpBatchLink } from "@trpc/client";
import { createRoot } from "react-dom/client";
import superjson from "superjson";
import App from "./App";
import "./index.css";
import "./theme-tokens.css";
import "./pwa.css";
// --- NATIVE_APP_LOCK_START ---
if (typeof window !== "undefined" && typeof document !== "undefined") {
  const isEditableInput = (target: EventTarget | null): boolean => {
    if (!target || !(target instanceof HTMLElement)) return false;
    return Boolean(target.closest("input, textarea, [contenteditable='true']"));
  };
  document.addEventListener("contextmenu", e => {
    if (!isEditableInput(e.target)) e.preventDefault();
  }, { capture: true });
  document.addEventListener("selectstart", e => {
    if (!isEditableInput(e.target)) e.preventDefault();
  }, { capture: true });
  document.addEventListener("copy", e => {
    if (!isEditableInput(e.target) && !isEditableInput(document.activeElement)) e.preventDefault();
  }, { capture: true });
  document.addEventListener("cut", e => {
    if (!isEditableInput(e.target) && !isEditableInput(document.activeElement)) e.preventDefault();
  }, { capture: true });
  document.addEventListener("dragstart", e => {
    if (!isEditableInput(e.target)) e.preventDefault();
  }, { capture: true });
  document.addEventListener("gesturestart", e => e.preventDefault(), { passive: false });
  document.addEventListener("gesturechange", e => e.preventDefault(), { passive: false });
  document.addEventListener("gestureend", e => e.preventDefault(), { passive: false });
  document.addEventListener("touchmove", e => {
    if (e.touches && e.touches.length > 1) e.preventDefault();
  }, { passive: false });
  document.addEventListener("wheel", e => {
    if (e.ctrlKey) e.preventDefault();
  }, { passive: false });
}
// --- NATIVE_APP_LOCK_END ---


if (typeof window !== "undefined") {
  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    (window as any).__deferredPwaPrompt = event;
    window.dispatchEvent(new Event("pwa-prompt-ready"));
  });
}

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(error => {
      console.warn("[PWA] Service worker registration unavailable", error instanceof Error ? error.message : "unknown error");
    });
  });
}

const queryClient = new QueryClient({ defaultOptions: { queries: { staleTime: 60_000, gcTime: 300_000, refetchOnWindowFocus: false, retry: 1 } } });

function isOwnerAdminRoute() {
  return /^\/admin(?:\/|$)/i.test(window.location.pathname);
}

queryClient.getQueryCache().subscribe(event => {
  if (event.type === "updated" && event.action.type === "error") {
    const error = event.query.state.error;
    console.error("[API Query Error]", error);
  }
});

queryClient.getMutationCache().subscribe(event => {
  if (event.type === "updated" && event.action.type === "error") {
    const error = event.mutation.state.error;
    console.error("[API Mutation Error]", error);
  }
});

const trpcClient = trpc.createClient({
  links: [
    httpBatchLink({
      url: "/api/trpc",
      transformer: superjson,
      headers() {
        if (!isOwnerAdminRoute()) return {};
        // Preview auto-login fallback: when the browser blocks iframe cookies
        // (Safari ITP / private browsing / WebView), the runtime mirrors the
        // session into sessionStorage so we can forward it as a Bearer token.
        // The regular OAuth cookie flow keeps working and takes priority server-side.
        try {
          const raw = sessionStorage.getItem("manus-cookie");
          if (raw) {
            const prefix = `${COOKIE_NAME}=`;
            const pair = raw.split(";").find(s => s.trim().startsWith(prefix));
            const token = pair?.trim().slice(prefix.length);
            if (token) {
              return { Authorization: `Bearer ${token}` };
            }
          }
        } catch {
          // sessionStorage unavailable
        }
        return {};
      },
      fetch(input, init) {
        return globalThis.fetch(input, {
          ...(init ?? {}),
          credentials: isOwnerAdminRoute() ? "include" : "omit",
        });
      },
    }),
  ],
});

createRoot(document.getElementById("root")!).render(
  <trpc.Provider client={trpcClient} queryClient={queryClient}>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </trpc.Provider>
);
