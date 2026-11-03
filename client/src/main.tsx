// --- GLOBAL_INSTANT_CATALOG_GUARD_START ---
(globalThis as any).INSTANT_CACHE_KEY = "original-catalog-instant-v2";
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
